"""Plant identification from photos."""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ID_PROVIDER,
    CONF_PLANTID_API_KEY,
    CONF_PLANTNET_API_KEY,
    PROVIDER_AI_TASK,
    PROVIDER_PLANTID,
    PROVIDER_PLANTNET,
)

_LOGGER = logging.getLogger(__name__)

PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
PLANTID_URL = "https://plant.id/api/v3/identification"
TIMEOUT = aiohttp.ClientTimeout(total=60)


class IdentificationError(HomeAssistantError):
    """Identification failed. ``reason`` is a translation key for the flow."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        super().__init__(message or reason)
        self.reason = reason


@dataclass(slots=True)
class Candidate:
    """A possible species for a photo."""

    scientific_name: str
    score: float
    common_names: list[str] = field(default_factory=list)
    family: str | None = None
    source: str = ""

    @property
    def common_name(self) -> str | None:
        return self.common_names[0] if self.common_names else None

    def label(self) -> str:
        common = f" - {self.common_name}" if self.common_name else ""
        return f"{self.scientific_name}{common} ({self.score:.0%})"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


async def async_identify(
    hass: HomeAssistant, config: dict[str, Any], image: bytes, mime: str, media_id: str
) -> list[Candidate]:
    """Identify the plant in an image with the configured provider.

    ``media_id`` is the media source id of the same image, used for AI Task attachments.
    """
    provider = config.get(CONF_ID_PROVIDER)

    if provider == PROVIDER_PLANTNET:
        candidates = await _plantnet(hass, config[CONF_PLANTNET_API_KEY], image, mime)
    elif provider == PROVIDER_PLANTID:
        candidates = await _plantid(hass, config[CONF_PLANTID_API_KEY], image, mime)
    elif provider == PROVIDER_AI_TASK:
        candidates = await _ai_task(hass, config.get(CONF_AI_TASK_ENTITY), media_id, mime)
    else:
        raise IdentificationError("no_provider")

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:5]


def _language(hass: HomeAssistant) -> str:
    return (hass.config.language or "en").split("-")[0]


async def _plantnet(hass: HomeAssistant, api_key: str, image: bytes, mime: str) -> list[Candidate]:
    session = async_get_clientsession(hass)
    form = aiohttp.FormData()
    form.add_field("images", image, filename="plant", content_type=mime)
    form.add_field("organs", "auto")
    params = {
        "api-key": api_key,
        "lang": _language(hass),
        "nb-results": "5",
        "include-related-images": "false",
    }
    try:
        async with session.post(PLANTNET_URL, params=params, data=form, timeout=TIMEOUT) as resp:
            if resp.status == 404:  # "Species not found"
                return []
            if resp.status in (401, 403):
                raise IdentificationError("invalid_auth")
            if resp.status == 429:
                raise IdentificationError("quota_exceeded")
            if resp.status >= 400:
                text = await resp.text()
                raise IdentificationError("provider_error", f"Pl@ntNet {resp.status}: {text[:200]}")
            payload = await resp.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise IdentificationError("cannot_connect", str(err)) from err

    candidates = []
    for result in payload.get("results", []):
        species = result.get("species") or {}
        name = species.get("scientificNameWithoutAuthor")
        if not name:
            continue
        candidates.append(
            Candidate(
                scientific_name=name,
                score=float(result.get("score") or 0),
                common_names=list(species.get("commonNames") or []),
                family=(species.get("family") or {}).get("scientificNameWithoutAuthor"),
                source="Pl@ntNet",
            )
        )
    return candidates


async def _plantid(hass: HomeAssistant, api_key: str, image: bytes, mime: str) -> list[Candidate]:
    session = async_get_clientsession(hass)
    body = {
        "images": [f"data:{mime};base64,{base64.b64encode(image).decode()}"],
        "similar_images": False,
    }
    params = {"details": "common_names,taxonomy", "language": _language(hass)}
    try:
        async with session.post(
            PLANTID_URL,
            params=params,
            json=body,
            headers={"Api-Key": api_key},
            timeout=TIMEOUT,
        ) as resp:
            if resp.status == 401:
                raise IdentificationError("invalid_auth")
            if resp.status == 429:
                raise IdentificationError("quota_exceeded")
            if resp.status >= 400:
                text = await resp.text()
                raise IdentificationError("provider_error", f"Plant.id {resp.status}: {text[:200]}")
            payload = await resp.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise IdentificationError("cannot_connect", str(err)) from err

    result = payload.get("result") or {}
    if (result.get("is_plant") or {}).get("binary") is False:
        raise IdentificationError("not_a_plant")
    candidates = []
    for suggestion in (result.get("classification") or {}).get("suggestions", []):
        details = suggestion.get("details") or {}
        candidates.append(
            Candidate(
                scientific_name=suggestion.get("name", ""),
                score=float(suggestion.get("probability") or 0),
                common_names=list(details.get("common_names") or []),
                family=(details.get("taxonomy") or {}).get("family"),
                source="Plant.id",
            )
        )
    return [c for c in candidates if c.scientific_name]


async def _ai_task(
    hass: HomeAssistant, entity_id: str | None, media_id: str, mime: str
) -> list[Candidate]:
    try:
        from homeassistant.components import ai_task
    except ImportError as err:
        raise IdentificationError("ai_task_unavailable") from err

    structure = vol.Schema(
        {
            vol.Required(
                "is_plant", description="Whether the photo shows a plant"
            ): selector.BooleanSelector(),
            vol.Optional(
                "scientific_name", description="Accepted botanical name, e.g. 'Monstera deliciosa'"
            ): selector.TextSelector(),
            vol.Optional(
                "common_name", description="Most widely used common name"
            ): selector.TextSelector(),
            vol.Optional("family", description="Botanical family"): selector.TextSelector(),
            vol.Optional("confidence", description="Confidence 0-100"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100)
            ),
            vol.Optional(
                "alternative_1", description="Second most likely scientific name"
            ): selector.TextSelector(),
            vol.Optional(
                "alternative_2", description="Third most likely scientific name"
            ): selector.TextSelector(),
        }
    )
    try:
        result = await ai_task.async_generate_data(
            hass,
            task_name="Identify plant",
            entity_id=entity_id or None,
            instructions=(
                "Identify the plant species in the attached photo. Use the currently "
                "accepted botanical name. If unsure about the species, give the genus. "
                f"Answer common names in the language '{_language(hass)}'."
            ),
            structure=structure,
            attachments=[{"media_content_id": media_id, "media_content_type": mime}],
        )
    except HomeAssistantError as err:
        raise IdentificationError("provider_error", str(err)) from err

    data = result.data if isinstance(result.data, dict) else {}
    if data.get("is_plant") is False:
        raise IdentificationError("not_a_plant")
    if not data.get("scientific_name"):
        return []
    confidence = float(data.get("confidence") or 70) / 100
    candidates = [
        Candidate(
            scientific_name=data["scientific_name"],
            score=confidence,
            common_names=[data["common_name"]] if data.get("common_name") else [],
            family=data.get("family"),
            source="AI",
        )
    ]
    for rank, key in enumerate(("alternative_1", "alternative_2"), start=1):
        if alt := data.get(key):
            candidates.append(Candidate(alt, max(0.0, (1 - confidence) / (rank + 1)), source="AI"))
    return candidates
