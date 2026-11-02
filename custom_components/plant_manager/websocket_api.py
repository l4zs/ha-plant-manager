"""Websocket API used by the panel and the Lovelace card."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from functools import wraps
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util
import voluptuous as vol

from . import i18n, species_db
from .alerts import alert_message
from .care import PROBLEM_TEXT
from .const import (
    BACKUP_URL,
    CARE_KINDS,
    CONF_ID_PROVIDER,
    DOMAIN,
    FEEDBACK,
    KIND_SNOOZE,
    KIND_WATER,
    LIGHT_LEVELS,
    PHOTO_URL,
    PLACEMENTS,
    POT_MATERIALS,
    PROVIDER_NONE,
    SENSOR_FIELDS,
    SIGNAL_UPDATED,
    STATUSES,
)
from .db import NotFoundError
from .manager import PlantManager, get_manager
from .schema import (
    PLANT_CREATE_SCHEMA,
    PLANT_FIELDS_SCHEMA,
    VACATION_SCHEMA,
    normalize_plant,
    normalize_vacation,
)
from .vacation import TIP_TEXT

PHOTO_URL_LIFETIME = timedelta(days=1)


def _command(schema: dict[Any, Any]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """A websocket command. Every command takes the UI's ``language`` for the texts it returns."""
    return websocket_api.websocket_command({**schema, vol.Optional("language"): cv.string})


Handler = Callable[
    [HomeAssistant, websocket_api.ActiveConnection, dict[str, Any], PlantManager],
    Awaitable[None],
]


def _with_manager(func: Handler) -> Callable[..., Awaitable[None]]:
    """Look up the manager and map errors to websocket errors."""

    @wraps(func)
    async def wrapper(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        if (manager := get_manager(hass)) is None:
            lang = i18n.language(msg.get("language") or hass.config.language)
            message = i18n.tr(lang, "Plant Manager is not loaded")
            connection.send_error(msg["id"], "not_loaded", message)
            return
        lang = msg["lang"] = manager.ui_language(msg.get("language"))
        try:
            await func(hass, connection, msg, manager)
        except NotFoundError as err:
            message = i18n.translate_message(lang, str(err))
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, message)
        except ValueError as err:
            message = i18n.translate_message(lang, str(err))
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, message)

    return wrapper


def _signed(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    plant: dict[str, Any],
    names: dict[str, str],
) -> dict[str, Any]:
    """Add the name to show and signed photo URLs to a plant."""
    plant["display_name"] = names.get(plant["id"], plant["name"])
    plant["photos"] = [
        {
            **photo,
            "url": async_sign_path(
                hass,
                PHOTO_URL.format(photo_id=photo["id"]),
                PHOTO_URL_LIFETIME,
                refresh_token_id=connection.refresh_token_id,
            ),
        }
        for photo in plant["photos"]
    ]
    return plant


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register all websocket commands."""
    for command in (
        ws_config,
        ws_language,
        ws_summary,
        ws_subscribe,
        ws_plants_list,
        ws_plants_get,
        ws_plants_create,
        ws_plants_update,
        ws_plants_delete,
        ws_plants_water,
        ws_plants_snooze,
        ws_plants_log,
        ws_events_delete,
        ws_undo,
        ws_profile_resolve,
        ws_photos_attach_staged,
        ws_photos_delete,
        ws_photos_reorder,
        ws_schedule,
        ws_alerts,
        ws_vacation_get,
        ws_vacation_preview,
        ws_vacation_set,
        ws_vacation_end,
        ws_vacation_send_plan,
        ws_export_json,
        ws_export_csv,
        ws_backup_create,
        ws_notifications_get,
        ws_notifications_set,
        ws_notifications_test,
    ):
        websocket_api.async_register_command(hass, command)


# -- general -------------------------------------------------------------


@_command({vol.Required("type"): f"{DOMAIN}/language"})
@websocket_api.async_response
@_with_manager
async def ws_language(hass, connection, msg, manager: PlantManager) -> None:
    """The language set for this instance, if any; the cards and the panel ask before they show."""
    connection.send_result(msg["id"], {"fixed": manager.fixed_language})


@_command({vol.Required("type"): f"{DOMAIN}/config"})
@websocket_api.async_response
@_with_manager
async def ws_config(hass, connection, msg, manager: PlantManager) -> None:
    """Return the static vocabulary and options the UI needs."""
    lang = msg["lang"]
    connection.send_result(
        msg["id"],
        {
            "statuses": STATUSES,
            "placements": PLACEMENTS,
            "light_levels": LIGHT_LEVELS,
            "pot_materials": POT_MATERIALS,
            "sensor_fields": SENSOR_FIELDS,
            "care_kinds": CARE_KINDS,
            "feedback": FEEDBACK,
            "problems": {code: i18n.tr(lang, text) for code, text in PROBLEM_TEXT.items()},
            "species": species_db.species_options(lang),
            "identification": manager.options[CONF_ID_PROVIDER] != PROVIDER_NONE,
            "provider": manager.options[CONF_ID_PROVIDER],
            "vacation_tips": {code: i18n.tr(lang, text) for code, text in TIP_TEXT.items()},
        },
    )


@_command({vol.Required("type"): f"{DOMAIN}/summary"})
@websocket_api.async_response
@_with_manager
async def ws_summary(hass, connection, msg, manager: PlantManager) -> None:
    """Return counts and the plants that need care (used by the card)."""
    summary = manager.summary
    names = species_db.display_names(manager.plants, msg["lang"])
    attention = [
        _signed(hass, connection, manager.plant_view(plant), names)
        for plant in manager.plants
        if (status := manager.status.get(plant["id"]))
        and (status["needs_water"] or status["status"] == "water_soon" or status["fertilize_due"])
    ]
    attention.sort(key=lambda plant: plant["care"]["next_watering"])
    connection.send_result(
        msg["id"],
        {
            "total": summary["total"],
            "counts": summary["counts"],
            "needs_water": len(summary["needs_water"]),
            "problems": len(summary["problems"]),
            "next_watering": summary["next_watering"],
            "attention": attention,
        },
    )


@_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Push a message whenever data changes."""

    @callback
    def forward_update() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "updated"}))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_UPDATED, forward_update
    )
    connection.send_result(msg["id"])


@_command({vol.Required("type"): f"{DOMAIN}/alerts"})
@websocket_api.async_response
@_with_manager
async def ws_alerts(hass, connection, msg, manager: PlantManager) -> None:
    """Return the active alerts."""
    alerts = [{**alert, "message": alert_message(alert, msg["lang"])} for alert in manager.alerts]
    connection.send_result(msg["id"], alerts)


@_command({vol.Required("type"): f"{DOMAIN}/schedule", vol.Optional("days", default=28): int})
@websocket_api.async_response
@_with_manager
async def ws_schedule(hass, connection, msg, manager: PlantManager) -> None:
    """Projected care for the next days."""
    start = dt_util.start_of_local_day()
    connection.send_result(
        msg["id"], manager.schedule(start, start + timedelta(days=min(msg["days"], 120)))
    )


# -- plants --------------------------------------------------------------


@_command({vol.Required("type"): f"{DOMAIN}/plants/list"})
@websocket_api.async_response
@_with_manager
async def ws_plants_list(hass, connection, msg, manager: PlantManager) -> None:
    """List all plants with their status."""
    names = species_db.display_names(manager.plants, msg["lang"])
    connection.send_result(
        msg["id"],
        [
            _signed(hass, connection, manager.plant_view(plant), names)
            for plant in manager.plants
        ],
    )


@_command({vol.Required("type"): f"{DOMAIN}/plants/get", vol.Required("plant_id"): str})
@websocket_api.async_response
@_with_manager
async def ws_plants_get(hass, connection, msg, manager: PlantManager) -> None:
    """Return one plant with its care log."""
    plant = await manager.async_plant(msg["plant_id"])
    names = species_db.display_names(manager.plants, msg["lang"])
    connection.send_result(msg["id"], _signed(hass, connection, plant, names))


@_command(
    {vol.Required("type"): f"{DOMAIN}/plants/create", vol.Required("plant"): PLANT_CREATE_SCHEMA}
)
@websocket_api.async_response
@_with_manager
async def ws_plants_create(hass, connection, msg, manager: PlantManager) -> None:
    """Create a plant."""
    plant = await manager.async_create_plant(normalize_plant(msg["plant"]), msg["lang"])
    names = species_db.display_names(manager.plants, msg["lang"])
    connection.send_result(msg["id"], _signed(hass, connection, plant, names))


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/plants/update",
        vol.Required("plant_id"): str,
        vol.Required("changes"): vol.Schema(PLANT_FIELDS_SCHEMA),
    }
)
@websocket_api.async_response
@_with_manager
async def ws_plants_update(hass, connection, msg, manager: PlantManager) -> None:
    """Update a plant."""
    plant = await manager.async_update_plant(msg["plant_id"], normalize_plant(msg["changes"]))
    names = species_db.display_names(manager.plants, msg["lang"])
    connection.send_result(msg["id"], _signed(hass, connection, plant, names))


@_command({vol.Required("type"): f"{DOMAIN}/plants/delete", vol.Required("plant_id"): str})
@websocket_api.async_response
@_with_manager
async def ws_plants_delete(hass, connection, msg, manager: PlantManager) -> None:
    """Delete a plant."""
    await manager.async_delete_plant(msg["plant_id"])
    connection.send_result(msg["id"])


# -- care ----------------------------------------------------------------


def _event_result(event: dict[str, Any]) -> dict[str, Any]:
    return {"event_id": event["id"], "undo_id": event["id"], "kind": event["kind"]}


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/plants/water",
        vol.Required("plant_id"): str,
        vol.Optional("feedback"): vol.Any(None, vol.In(FEEDBACK)),
        vol.Optional("at"): vol.Any(None, str),
    }
)
@websocket_api.async_response
@_with_manager
async def ws_plants_water(hass, connection, msg, manager: PlantManager) -> None:
    """Log a watering."""
    event = await manager.async_water(msg["plant_id"], msg.get("at"), msg.get("feedback"))
    connection.send_result(msg["id"], _event_result(event))


@_command({vol.Required("type"): f"{DOMAIN}/plants/snooze", vol.Required("plant_id"): str})
@websocket_api.async_response
@_with_manager
async def ws_plants_snooze(hass, connection, msg, manager: PlantManager) -> None:
    """Soil is still moist: postpone the reminder."""
    event = await manager.async_snooze(msg["plant_id"])
    connection.send_result(msg["id"], _event_result(event))


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/plants/log",
        vol.Required("plant_id"): str,
        vol.Required("kind"): vol.In([k for k in CARE_KINDS if k not in (KIND_WATER, KIND_SNOOZE)]),
        vol.Optional("at"): vol.Any(None, str),
        vol.Optional("notes"): vol.Any(None, vol.All(str, vol.Length(max=2000))),
    }
)
@websocket_api.async_response
@_with_manager
async def ws_plants_log(hass, connection, msg, manager: PlantManager) -> None:
    """Log fertilizing, repotting, pruning, misting or a note."""
    event = await manager.async_log(msg["plant_id"], msg["kind"], msg.get("at"), msg.get("notes"))
    connection.send_result(msg["id"], _event_result(event))


@_command({vol.Required("type"): f"{DOMAIN}/events/delete", vol.Required("event_id"): int})
@websocket_api.async_response
@_with_manager
async def ws_events_delete(hass, connection, msg, manager: PlantManager) -> None:
    """Remove an entry from a plant's care log."""
    await manager.async_delete_event(msg["event_id"])
    connection.send_result(msg["id"])


@_command({vol.Required("type"): f"{DOMAIN}/undo", vol.Required("undo_id"): int})
@websocket_api.async_response
@_with_manager
async def ws_undo(hass, connection, msg, manager: PlantManager) -> None:
    """Undo a care action from the last few minutes."""
    connection.send_result(msg["id"], {"undone": await manager.async_undo(msg["undo_id"])})


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/profile/resolve",
        vol.Required("species"): vol.All(str, vol.Strip, vol.Length(min=1, max=200)),
        vol.Optional("family"): vol.Any(None, str),
    }
)
@websocket_api.async_response
@_with_manager
async def ws_profile_resolve(hass, connection, msg, manager: PlantManager) -> None:
    """Look up the care profile for a species."""
    connection.send_result(
        msg["id"],
        await manager.async_resolve_profile(msg["species"], msg.get("family"), msg["lang"]),
    )


# -- photos --------------------------------------------------------------


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/photos/attach_staged",
        vol.Required("plant_id"): str,
        vol.Required("staged_id"): str,
    }
)
@websocket_api.async_response
@_with_manager
async def ws_photos_attach_staged(hass, connection, msg, manager: PlantManager) -> None:
    """Save the photo used for identification with the plant."""
    photo = await manager.async_attach_staged(msg["plant_id"], msg["staged_id"])
    connection.send_result(msg["id"], {"id": photo["id"]})


@_command({vol.Required("type"): f"{DOMAIN}/photos/delete", vol.Required("photo_id"): str})
@websocket_api.async_response
@_with_manager
async def ws_photos_delete(hass, connection, msg, manager: PlantManager) -> None:
    """Delete a photo."""
    await manager.async_delete_photo(msg["photo_id"])
    connection.send_result(msg["id"])


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/photos/reorder",
        vol.Required("plant_id"): str,
        vol.Required("photo_ids"): [str],
    }
)
@websocket_api.async_response
@_with_manager
async def ws_photos_reorder(hass, connection, msg, manager: PlantManager) -> None:
    """Set the photo order (the first one is the cover)."""
    await manager.async_reorder_photos(msg["plant_id"], msg["photo_ids"])
    connection.send_result(msg["id"])


# -- vacation ------------------------------------------------------------


@_command({vol.Required("type"): f"{DOMAIN}/vacation/get"})
@websocket_api.async_response
@_with_manager
async def ws_vacation_get(hass, connection, msg, manager: PlantManager) -> None:
    """Return the planned or ongoing vacation with its plan."""
    connection.send_result(msg["id"], manager.vacation_view(lang=msg["lang"]))


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/vacation/preview",
        vol.Required("start_date"): cv.date,
        vol.Required("end_date"): cv.date,
    }
)
@websocket_api.async_response
@_with_manager
async def ws_vacation_preview(hass, connection, msg, manager: PlantManager) -> None:
    """Plan a trip without saving it."""
    dates = normalize_vacation({"start_date": msg["start_date"], "end_date": msg["end_date"]})
    connection.send_result(
        msg["id"],
        manager.preview_vacation(
            date.fromisoformat(dates["start_date"]),
            date.fromisoformat(dates["end_date"]),
            msg["lang"],
        ),
    )


@_command(
    {vol.Required("type"): f"{DOMAIN}/vacation/set", vol.Required("vacation"): VACATION_SCHEMA}
)
@websocket_api.async_response
@_with_manager
async def ws_vacation_set(hass, connection, msg, manager: PlantManager) -> None:
    """Plan a vacation, or change the current one."""
    result = await manager.async_set_vacation(normalize_vacation(msg["vacation"]), msg["lang"])
    connection.send_result(msg["id"], result)


@_command({vol.Required("type"): f"{DOMAIN}/vacation/end"})
@websocket_api.async_response
@_with_manager
async def ws_vacation_end(hass, connection, msg, manager: PlantManager) -> None:
    """End the vacation early, or cancel it."""
    await manager.async_end_vacation()
    connection.send_result(msg["id"])


@_command({vol.Required("type"): f"{DOMAIN}/vacation/send_plan"})
@websocket_api.async_response
@_with_manager
async def ws_vacation_send_plan(hass, connection, msg, manager: PlantManager) -> None:
    """Send the plan to the plant sitter."""
    await manager.async_send_plan(msg["lang"])
    connection.send_result(msg["id"])


# -- export & backup -----------------------------------------------------


@_command({vol.Required("type"): f"{DOMAIN}/export/json"})
@websocket_api.async_response
@_with_manager
async def ws_export_json(hass, connection, msg, manager: PlantManager) -> None:
    """Everything as JSON."""
    connection.send_result(msg["id"], await manager.async_export_json())


@_command({vol.Required("type"): f"{DOMAIN}/export/csv"})
@websocket_api.async_response
@_with_manager
async def ws_export_csv(hass, connection, msg, manager: PlantManager) -> None:
    """The plants as CSV."""
    connection.send_result(msg["id"], {"csv": await manager.async_export_csv()})


@_command({vol.Required("type"): f"{DOMAIN}/backup/create"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_backup_create(hass, connection, msg, manager: PlantManager) -> None:
    """Create a backup zip and return a download link."""
    backup_id = await manager.async_create_backup()
    url = async_sign_path(
        hass,
        BACKUP_URL.format(backup_id=backup_id),
        timedelta(minutes=30),
        refresh_token_id=connection.refresh_token_id,
    )
    connection.send_result(msg["id"], {"url": url})


# -- notifications (per user) --------------------------------------------


@_command({vol.Required("type"): f"{DOMAIN}/notifications/get"})
@websocket_api.async_response
@_with_manager
async def ws_notifications_get(hass, connection, msg, manager: PlantManager) -> None:
    """The current user's notification settings and the phones to choose from."""
    user_id = connection.user.id
    connection.send_result(
        msg["id"],
        {
            "settings": manager.notification_settings(user_id),
            "phones": manager.phones(user_id),
        },
    )


@_command(
    {
        vol.Required("type"): f"{DOMAIN}/notifications/set",
        vol.Required("targets"): [cv.string],
        vol.Required("daily"): bool,
        vol.Required("time"): cv.string,
        vol.Required("problems"): bool,
    }
)
@websocket_api.async_response
@_with_manager
async def ws_notifications_set(hass, connection, msg, manager: PlantManager) -> None:
    """Save the current user's notification settings."""
    settings = {key: msg[key] for key in ("targets", "daily", "time", "problems")}
    await manager.async_set_notifications(connection.user.id, settings, msg["lang"])
    connection.send_result(msg["id"], manager.notification_settings(connection.user.id))


@_command({vol.Required("type"): f"{DOMAIN}/notifications/test"})
@websocket_api.async_response
@_with_manager
async def ws_notifications_test(hass, connection, msg, manager: PlantManager) -> None:
    """Send a test notification to the current user's phones."""
    connection.send_result(
        msg["id"], {"sent": await manager.async_test_notification(connection.user.id)}
    )
