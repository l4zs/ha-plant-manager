"""Plant Manager: watering reminders tuned to each plant."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
import voluptuous as vol

from . import websocket_api
from .const import (
    CARD_FILENAME,
    CARE_KINDS,
    DOMAIN,
    FEEDBACK,
    KIND_SNOOZE,
    KIND_WATER,
    NAME,
    PANEL_COMPONENT,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
    STATIC_URL,
)
from .db import NotFoundError
from .http import (
    BackupView,
    IdentifyView,
    PhotoUploadView,
    PhotoView,
    StagedPhotoView,
    UploadView,
)
from .manager import PlantManager, get_manager
from .health import HealthView
from .schema import VACATION_SCHEMA, normalize_vacation

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.TODO,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type PlantConfigEntry = ConfigEntry[PlantManager]

DATA_CARD_URL = f"{DOMAIN}_card_url"


def _require_manager(hass: HomeAssistant) -> PlantManager:
    if (manager := get_manager(hass)) is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
    return manager


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the parts that live for the whole runtime."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
    )
    hass.http.register_view(PhotoView())
    hass.http.register_view(StagedPhotoView())
    hass.http.register_view(PhotoUploadView())
    hass.http.register_view(IdentifyView())
    hass.http.register_view(HealthView())
    hass.http.register_view(BackupView())
    hass.http.register_view(UploadView())
    websocket_api.async_register(hass)
    _register_services(hass)
    return True


def _register_services(hass: HomeAssistant) -> None:
    async def care(call: ServiceCall) -> None:
        manager = _require_manager(hass)
        at = call.data["at"].isoformat() if "at" in call.data else None
        try:
            for plant_id in call.data["plant_id"]:
                if call.service == "water":
                    await manager.async_water(
                        plant_id, at, call.data.get("feedback"), source="service"
                    )
                elif call.service == "snooze":
                    await manager.async_snooze(plant_id, source="service")
                elif call.service == "fertilize":
                    await manager.async_log(plant_id, "fertilize", at, source="service")
                else:
                    await manager.async_log(
                        plant_id, call.data["kind"], at, call.data.get("notes"), source="service"
                    )
        except NotFoundError as err:
            raise ServiceValidationError(str(err)) from err

    async def send_reminder(call: ServiceCall) -> None:
        await _require_manager(hass).async_send_reminder(force=True)

    async def identify(call: ServiceCall) -> ServiceResponse:
        manager = _require_manager(hass)
        if camera := call.data.get("camera_entity_id"):
            from homeassistant.components.camera import async_get_image

            data = (await async_get_image(hass, camera)).content
        else:
            path = call.data["image_path"]
            if not hass.config.is_allowed_path(path):
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="path_not_allowed",
                    translation_placeholders={"path": path},
                )
            data = await hass.async_add_executor_job(Path(path).read_bytes)
        try:
            result = await manager.async_identify(data)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        return {"candidates": result["candidates"], "error": result["error"]}

    plant_ids = vol.All(cv.ensure_list, [cv.string])
    hass.services.async_register(
        DOMAIN,
        "water",
        care,
        vol.Schema(
            {
                vol.Required("plant_id"): plant_ids,
                vol.Optional("at"): cv.datetime,
                vol.Optional("feedback"): vol.In(FEEDBACK),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN, "snooze", care, vol.Schema({vol.Required("plant_id"): plant_ids})
    )
    hass.services.async_register(
        DOMAIN,
        "fertilize",
        care,
        vol.Schema({vol.Required("plant_id"): plant_ids, vol.Optional("at"): cv.datetime}),
    )
    hass.services.async_register(
        DOMAIN,
        "log_care",
        care,
        vol.Schema(
            {
                vol.Required("plant_id"): plant_ids,
                vol.Required("kind"): vol.In(
                    [kind for kind in CARE_KINDS if kind not in (KIND_WATER, KIND_SNOOZE)]
                ),
                vol.Optional("at"): cv.datetime,
                vol.Optional("notes"): cv.string,
            }
        ),
    )
    hass.services.async_register(DOMAIN, "send_reminder", send_reminder, vol.Schema({}))
    hass.services.async_register(
        DOMAIN,
        "identify",
        identify,
        vol.All(
            vol.Schema(
                {
                    vol.Exclusive("camera_entity_id", "source"): cv.entity_domain("camera"),
                    vol.Exclusive("image_path", "source"): cv.string,
                }
            ),
            cv.has_at_least_one_key("camera_entity_id", "image_path"),
        ),
        supports_response=SupportsResponse.ONLY,
    )

    async def set_vacation(call: ServiceCall) -> None:
        try:
            await _require_manager(hass).async_set_vacation(normalize_vacation(dict(call.data)))
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def end_vacation(call: ServiceCall) -> None:
        try:
            await _require_manager(hass).async_end_vacation()
        except NotFoundError as err:
            raise ServiceValidationError(str(err)) from err

    hass.services.async_register(DOMAIN, "set_vacation", set_vacation, VACATION_SCHEMA)
    hass.services.async_register(DOMAIN, "end_vacation", end_vacation, vol.Schema({}))


async def async_setup_entry(hass: HomeAssistant, entry: PlantConfigEntry) -> bool:
    """Set up Plant Manager from a config entry."""
    manager = PlantManager(hass, entry)
    await manager.async_setup()
    entry.runtime_data = manager

    # Plant devices hang off the service device, so it has to exist first.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=NAME,
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    manager.async_remove_stale_devices()

    version = (await async_get_integration(hass, DOMAIN)).version
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        module_url=f"{STATIC_URL}/{PANEL_FILENAME}?v={version}&garden=20261101-1",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        config={},
    )
    card_url = f"{STATIC_URL}/{CARD_FILENAME}?v={version}&garden=20261101-1"
    frontend.add_extra_js_url(hass, card_url)
    hass.data[DATA_CARD_URL] = card_url

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: PlantConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PlantConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    if card_url := hass.data.pop(DATA_CARD_URL, None):
        frontend.remove_extra_js_url(hass, card_url)
    await entry.runtime_data.async_close()
    return True
