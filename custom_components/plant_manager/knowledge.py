"""Resolve a care profile for a species.

Sources, in order of precedence (later sources fill or refine earlier ones):
1. Generic defaults
2. Built-in species/genus database (watering interval, dormancy, fertilizing)
3. OpenPlantbook (measured temperature, humidity, soil moisture and light ranges)
4. AI Task (only when the species is not in the built-in database)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from . import species_db
from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ID_PROVIDER,
    CONF_OPB_CLIENT_ID,
    CONF_OPB_CLIENT_SECRET,
    DOMAIN,
    P_BASE_INTERVAL,
    P_FERTILIZE_INTERVAL,
    P_LIGHT_PREFERENCE,
    P_MAX_HUMIDITY,
    P_MAX_LUX,
    P_MAX_MOISTURE,
    P_MAX_TEMP,
    P_MIN_HUMIDITY,
    P_MIN_LUX,
    P_MIN_MOISTURE,
    P_MIN_TEMP,
    P_NOTES,
    P_TOXIC_TO_PETS,
    P_WINTER_DORMANCY,
    PROVIDER_AI_TASK,
)
from .i18n import language

_LOGGER = logging.getLogger(__name__)

_LANGUAGE_NAMES = {"en": "English", "de": "German"}

OPB_URL = "https://open.plantbook.io/api/v1"
TIMEOUT = aiohttp.ClientTimeout(total=20)


@dataclass(slots=True)
class ResolvedProfile:
    """A care profile plus where it came from."""

    profile: dict[str, Any]
    sources: list[str] = field(default_factory=list)
    common_name: str | None = None


class OpenPlantbookError(HomeAssistantError):
    """OpenPlantbook request failed."""


class OpenPlantbook:
    """Minimal OpenPlantbook client (OAuth2 client credentials)."""

    def __init__(self, hass: HomeAssistant, client_id: str, client_secret: str) -> None:
        self._session = async_get_clientsession(hass)
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry = 0.0

    async def _async_token(self) -> str:
        if self._token and time.monotonic() < self._token_expiry:
            return self._token
        try:
            async with self._session.post(
                f"{OPB_URL}/token/",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=TIMEOUT,
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise OpenPlantbookError("invalid_auth")
                resp.raise_for_status()
                payload = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OpenPlantbookError("cannot_connect") from err
        self._token = payload["access_token"]
        self._token_expiry = time.monotonic() + float(payload.get("expires_in", 3600)) - 60
        return self._token

    async def async_validate(self) -> None:
        """Raise OpenPlantbookError if the credentials do not work."""
        await self._async_token()

    async def _async_get(self, path: str, params: dict[str, str] | None = None) -> Any:
        token = await self._async_token()
        try:
            async with self._session.get(
                f"{OPB_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OpenPlantbookError("cannot_connect") from err

    async def async_lookup(self, scientific_name: str) -> dict[str, Any] | None:
        """Get the detail record for a species, searching by alias if needed."""
        pid = scientific_name.strip().lower()
        if detail := await self._async_get(f"/plant/detail/{pid}/"):
            return detail
        search = await self._async_get("/plant/search", {"alias": pid})
        results = (search or {}).get("results") or []
        if not results:
            return None
        return await self._async_get(f"/plant/detail/{results[0]['pid']}/")


def get_openplantbook(hass: HomeAssistant, config: dict[str, Any]) -> OpenPlantbook | None:
    """Shared OpenPlantbook client for the configured credentials."""
    client_id = config.get(CONF_OPB_CLIENT_ID)
    secret = config.get(CONF_OPB_CLIENT_SECRET)
    if not client_id or not secret:
        return None
    cache: dict[tuple[str, str], OpenPlantbook] = hass.data.setdefault(f"{DOMAIN}_opb", {})
    if (client_id, secret) not in cache:
        cache[(client_id, secret)] = OpenPlantbook(hass, client_id, secret)
    return cache[(client_id, secret)]


_OPB_MAP = {
    "min_temp": P_MIN_TEMP,
    "max_temp": P_MAX_TEMP,
    "min_env_humid": P_MIN_HUMIDITY,
    "max_env_humid": P_MAX_HUMIDITY,
    "min_soil_moist": P_MIN_MOISTURE,
    "max_soil_moist": P_MAX_MOISTURE,
    "min_light_lux": P_MIN_LUX,
    "max_light_lux": P_MAX_LUX,
}


async def _async_ai_profile(
    hass: HomeAssistant, entity_id: str | None, scientific_name: str, lang: str = "en"
) -> dict[str, Any] | None:
    try:
        from homeassistant.components import ai_task
    except ImportError:
        return None

    fields: dict[Any, Any] = {}
    for key, desc, low, high in (
        (
            P_BASE_INTERVAL,
            "Days between waterings in a 15 cm plastic pot, medium indirect light, "
            "21 °C, 50 % humidity, growing season",
            0.5,
            60,
        ),
        (
            P_FERTILIZE_INTERVAL,
            "Days between fertilizing in the growing season, 0 if never",
            0,
            180,
        ),
        (P_MIN_TEMP, "Minimum tolerated air temperature in °C", -20, 30),
        (P_MAX_TEMP, "Maximum tolerated air temperature in °C", 15, 50),
        (P_MIN_HUMIDITY, "Minimum relative air humidity in %", 0, 100),
        (P_MAX_HUMIDITY, "Maximum relative air humidity in %", 0, 100),
        (P_MIN_MOISTURE, "Soil moisture % at which it should be watered", 0, 100),
        (P_MAX_MOISTURE, "Soil moisture % above which the soil is too wet", 0, 100),
    ):
        fields[vol.Required(key, description=desc)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=low, max=high, step=0.5)
        )
    fields[
        vol.Required(
            P_WINTER_DORMANCY, description="Whether it rests in winter and needs much less water"
        )
    ] = selector.BooleanSelector()
    fields[vol.Required(P_LIGHT_PREFERENCE, description="Preferred light")] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(options=["low", "medium", "bright_indirect", "direct"])
        )
    )
    fields[vol.Optional(P_TOXIC_TO_PETS, description="Toxic to cats or dogs")] = (
        selector.BooleanSelector()
    )
    fields[
        vol.Optional("common_name", description=f"Common name in {_LANGUAGE_NAMES[language(lang)]}")
    ] = selector.TextSelector()
    fields[
        vol.Optional(
            P_NOTES,
            description=(
                "One short sentence of the most important care tip, in "
                f"{_LANGUAGE_NAMES[language(lang)]}"
            ),
        )
    ] = selector.TextSelector()

    try:
        result = await ai_task.async_generate_data(
            hass,
            task_name="Plant care profile",
            entity_id=entity_id or None,
            instructions=(
                f"Provide typical houseplant/garden care values for the plant species "
                f"'{scientific_name}'. Use realistic horticultural values."
            ),
            structure=vol.Schema(fields),
        )
    except HomeAssistantError as err:
        _LOGGER.debug("AI care profile for %s failed: %s", scientific_name, err)
        return None
    return result.data if isinstance(result.data, dict) else None


async def async_resolve_profile(
    hass: HomeAssistant,
    config: dict[str, Any],
    scientific_name: str,
    family: str | None = None,
    lang: str | None = None,
) -> ResolvedProfile:
    """Build the best available care profile for a species."""
    resolved = ResolvedProfile(profile=dict(species_db.DEFAULT_PROFILE))

    if entry := species_db.lookup(scientific_name, family):
        resolved.profile.update(species_db.profile(entry, lang))
        resolved.common_name = species_db.common_name(entry, lang)
        resolved.sources.append(f"built-in database ({entry.key})")

    if opb := get_openplantbook(hass, config):
        try:
            detail = await opb.async_lookup(scientific_name)
        except OpenPlantbookError as err:
            _LOGGER.warning("OpenPlantbook lookup for %s failed: %s", scientific_name, err)
            detail = None
        if detail:
            for opb_key, key in _OPB_MAP.items():
                if detail.get(opb_key) is not None:
                    resolved.profile[key] = float(detail[opb_key])
            resolved.sources.append(f"OpenPlantbook ({detail.get('display_pid', '')})")

    use_ai = (
        bool(config.get(CONF_AI_TASK_ENTITY)) or config.get(CONF_ID_PROVIDER) == PROVIDER_AI_TASK
    )
    if (
        entry is None
        and use_ai
        and (
            ai := await _async_ai_profile(
                hass, config.get(CONF_AI_TASK_ENTITY), scientific_name, language(lang)
            )
        )
    ):
        common = ai.pop("common_name", None)
        had_opb = any(s.startswith("OpenPlantbook") for s in resolved.sources)
        for key, value in ai.items():
            if value is None:
                continue
            # Prefer measured OpenPlantbook ranges over AI estimates.
            if had_opb and key in _OPB_MAP.values():
                continue
            resolved.profile[key] = value
        resolved.common_name = resolved.common_name or common
        resolved.sources.append("AI estimate")

    if not resolved.sources:
        resolved.sources.append("generic defaults")
    return resolved
