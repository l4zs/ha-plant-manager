"""Plant Manager runtime: ties the database and the watering model to Home Assistant."""

from __future__ import annotations

from collections.abc import Callable
import contextlib
from datetime import date, datetime, time, timedelta
from io import BytesIO
import logging
import os
import shutil
import sqlite3
import tempfile
from typing import Any, TypeVar
import uuid
import zipfile

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify
from homeassistant.util.unit_conversion import TemperatureConverter

from . import care, vacation as trips
from .alerts import KIND_FERTILIZE, KIND_PROBLEM, KIND_WATER, compute_alerts, summary_message
from .const import (
    CONF_ID_PROVIDER,
    CONF_NOTIFY_ALERTS,
    CONF_NOTIFY_SERVICE,
    CONF_REMINDER_TIME,
    CONF_WEATHER_ENTITY,
    DB_FILENAME,
    DEFAULT_OPTIONS,
    DOMAIN,
    EVENT_ALERT,
    EVENT_ALERT_CLEARED,
    EVENT_CARE_LOGGED,
    EVENT_VACATION_ENDED,
    EVENT_VACATION_STARTED,
    EVENT_WATERING_DUE,
    KIND_SNOOZE,
    KIND_WATER as CARE_WATER,
    NAME,
    PANEL_URL_PATH,
    PHOTO_DIR,
    PROVIDER_NONE,
    SIGNAL_UPDATED,
    STAGING_DIR,
    STORAGE_DIR,
    UNDO_WINDOW_MINUTES,
)
from .db import MIGRATIONS, STATE_FIELDS, NotFoundError, PlantDatabase
from .identify import IdentificationError, async_identify
from .knowledge import async_resolve_profile
from .transfer import parse_plants_csv, plants_to_csv

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")

TICK_INTERVAL = timedelta(minutes=10)
STAGING_LIFETIME = timedelta(hours=1)
BACKUP_LIFETIME = timedelta(minutes=30)
# The vacation checklist shows up this long before you leave.
PREPARE_AHEAD = timedelta(days=2)

_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
]

MIME_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "heic": "image/heic",
    "avif": "image/avif",
}


def image_extension(data: bytes) -> str | None:
    """Detect the image type from its first bytes."""
    for signature, extension in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:12] in (b"ftypavif", b"ftypavis"):
        return "avif"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1", b"msf1"):
        return "heic"
    return None


def mime_type(filename: str) -> str:
    """MIME type of a stored image file."""
    return MIME_TYPES.get(filename.rsplit(".", 1)[-1], "application/octet-stream")


def get_manager(hass: HomeAssistant) -> PlantManager | None:
    """Return the manager of the loaded config entry, if any."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    return None


class PlantManager:
    """Owns the database and keeps every plant's watering schedule up to date."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        base = hass.config.path(STORAGE_DIR)
        self.photo_dir = os.path.join(base, PHOTO_DIR)
        self.staging_dir = os.path.join(self.photo_dir, STAGING_DIR)
        # staged id -> (filename, expiry) for photos taken to identify a plant, not yet saved
        self._staged: dict[str, tuple[str, datetime]] = {}
        self.db = PlantDatabase(os.path.join(base, DB_FILENAME))
        self.plants: list[dict[str, Any]] = []
        self.status: dict[str, dict[str, Any]] = {}
        self.summary: dict[str, Any] = {}
        self.alerts: list[dict[str, Any]] = []
        # Alerts that were already announced, kept across restarts so they are sent once.
        self._alert_store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.alerts")
        self._announced: set[str] = set()
        # The planned or ongoing vacation, and its plan (see vacation.py).
        self.vacation: dict[str, Any] | None = None
        self.trip: dict[str, Any] | None = None
        self._away: dict[str, Any] | None = None
        self._tracking = False
        self._prepare_note: str | None = None
        self._backups: dict[str, tuple[str, datetime]] = {}
        # Per Home Assistant user: which phones get what (see notification_settings).
        self._notify_store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.notifications")
        self.notify_users: dict[str, dict[str, Any]] = {}
        self._unsubs: list[CALLBACK_TYPE] = []

    # -- lifecycle ---------------------------------------------------------

    @property
    def options(self) -> dict[str, Any]:
        """Return the options merged with defaults."""
        return {**DEFAULT_OPTIONS, **self.entry.options}

    async def async_setup(self) -> None:
        """Open the database and start the schedule."""
        await self._run(self._setup_files)
        stored = await self._alert_store.async_load() or {}
        self._announced = set(stored.get("announced", []))
        self.notify_users = (await self._notify_store.async_load() or {}).get("users", {})
        self._unsubs.append(async_track_time_interval(self.hass, self._async_tick, TICK_INTERVAL))
        # Everyone picks their own time for the daily summary.
        self._unsubs.append(
            async_track_time_change(self.hass, self._async_user_reminders, second=0)
        )
        if reminder := dt_util.parse_time(self.options[CONF_REMINDER_TIME] or ""):
            self._unsubs.append(
                async_track_time_change(
                    self.hass,
                    self._async_reminder_job,
                    hour=reminder.hour,
                    minute=reminder.minute,
                    second=reminder.second,
                )
            )
        await self.async_refresh(tick=True)

    def _setup_files(self) -> None:
        os.makedirs(self.staging_dir, exist_ok=True)
        for leftover in os.listdir(self.staging_dir):
            with contextlib.suppress(OSError):
                os.remove(os.path.join(self.staging_dir, leftover))
        self.db.open()

    async def async_close(self) -> None:
        """Stop the schedule and close the database."""
        while self._unsubs:
            self._unsubs.pop()()
        # A reload doesn't flush delayed saves like a shutdown does.
        await self._alert_store.async_save({"announced": sorted(self._announced)})
        await self._run(self.db.close)

    async def _run(self, func: Callable[..., _T], *args: Any) -> _T:
        return await self.hass.async_add_executor_job(func, *args)

    @staticmethod
    def _now() -> str:
        return dt_util.utcnow().isoformat()

    @property
    def growth(self) -> float:
        """How much the plants are growing right now (season, 0..1)."""
        return care.growth_level(dt_util.now(), self.hass.config.latitude)

    # -- sensors -----------------------------------------------------------

    def _number(self, entity_id: str | None) -> tuple[float | None, str | None]:
        if not entity_id or (state := self.hass.states.get(entity_id)) is None:
            return None, None
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None, None
        try:
            return float(state.state), state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        except ValueError:
            return None, None

    @staticmethod
    def _celsius(value: float | None, unit: str | None) -> float | None:
        if value is not None and unit in (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.KELVIN):
            return TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
        return value

    def _readings(self, plant: dict[str, Any]) -> care.Readings:
        temperature = self._celsius(*self._number(plant.get("temperature_sensor")))
        humidity, _ = self._number(plant.get("humidity_sensor"))
        weather = None
        # Outdoor plants without their own sensors use the weather entity.
        if plant.get("placement") != "indoor" and (
            state := self.hass.states.get(self.options[CONF_WEATHER_ENTITY] or "")
        ):
            weather = state.state
            if temperature is None and (temp := state.attributes.get("temperature")) is not None:
                temperature = self._celsius(float(temp), state.attributes.get("temperature_unit"))
            if humidity is None and (hum := state.attributes.get("humidity")) is not None:
                humidity = float(hum)
        moisture, _ = self._number(plant.get("moisture_sensor"))
        lux, _ = self._number(plant.get("illuminance_sensor"))
        return care.Readings(
            temperature=temperature,
            humidity=humidity,
            moisture=moisture,
            lux=lux,
            weather=weather,
            local_day=dt_util.now().date().isoformat(),
        )

    # -- schedule ----------------------------------------------------------

    async def _async_tick(self, _now: datetime) -> None:
        now = dt_util.utcnow()
        expired = [key for key, (_, expires) in self._staged.items() if expires < now]
        await self._run(self._remove_staged, [self._staged.pop(key)[0] for key in expired])
        old = [key for key, (_, expires) in self._backups.items() if expires < now]
        await self._run(self._remove_paths, [self._backups.pop(key)[0] for key in old])
        await self.async_refresh(tick=True)

    async def async_refresh(self, *, tick: bool = False) -> None:
        """Reload the plants, advance their water balance if ``tick``, and notify listeners."""
        plants = await self._run(self.db.list_plants)
        now = dt_util.utcnow()
        growth = self.growth
        readings = {plant["id"]: self._readings(plant) for plant in plants}
        if tick and plants:
            states: dict[str, dict[str, Any]] = {}
            watered: list[str] = []
            for plant in plants:
                state, by_sensor = care.advance(plant, readings[plant["id"]], now, growth)
                states[plant["id"]] = state
                plant.update(state)
                if by_sensor:
                    watered.append(plant["id"])
            await self._run(self.db.save_states, states)
            for plant_id in watered:
                await self._run(
                    lambda pid=plant_id: self.db.add_event(
                        pid, CARE_WATER, now.isoformat(), now.isoformat(), source="sensor"
                    )
                )
                self._fire_care(plant_id, CARE_WATER, "sensor")
            if watered:
                plants = await self._run(self.db.list_plants)
        previous = self.status
        self.status = {
            plant["id"]: care.status(plant, readings[plant["id"]], now, growth) for plant in plants
        }
        self.plants = plants
        for plant in plants:
            status = self.status[plant["id"]]
            before = previous.get(plant["id"])
            if status["needs_water"] and before is not None and not before["needs_water"]:
                self.hass.bus.async_fire(
                    EVENT_WATERING_DUE,
                    {"plant_id": plant["id"], "name": plant["name"], "status": status["status"]},
                )
        self.vacation = await self._run(self.db.current_vacation, dt_util.now().date().isoformat())
        self.trip = self._plan(self.vacation) if self.vacation else None
        if self.trip is None:
            self.vacation = None
        self._track_vacation()
        self.alerts = compute_alerts(plants, self.status)
        self._announce_alerts()
        self.summary = self._summary()
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    def _summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for status in self.status.values():
            by_status[status["status"]] = by_status.get(status["status"], 0) + 1
        upcoming = sorted(
            (status["next_watering"], plant_id) for plant_id, status in self.status.items()
        )
        return {
            "total": len(self.plants),
            "counts": by_status,
            "needs_water": [p for p in self.plants if self.status[p["id"]]["needs_water"]],
            "fertilize_due": [p for p in self.plants if self.status[p["id"]]["fertilize_due"]],
            "problems": [
                p
                for p in self.plants
                if any(c != "watering_overdue" for c in self.status[p["id"]]["problems"])
            ],
            "next_watering": upcoming[0][0] if upcoming else None,
        }

    def plant_view(self, plant: dict[str, Any]) -> dict[str, Any]:
        """A plant with its current care status, without internal model state."""
        view = {key: value for key, value in plant.items() if key not in STATE_FIELDS}
        view["care"] = self.status.get(plant["id"])
        return view

    def schedule(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        """Projected waterings and due fertilizing between two times.

        During a vacation, the waterings are the plant sitter's visits, and the
        schedule resumes from how dry each plant is expected to be when you are back.
        """
        now = dt_util.utcnow()
        tz = dt_util.get_default_time_zone()
        trip = self.trip
        leave = datetime.fromisoformat(trip["leave"]) if trip else None
        back = datetime.fromisoformat(trip["back"]) if trip else None
        planned = {entry["plant_id"]: entry for entry in trip["plants"]} if trip else {}
        events: list[dict[str, Any]] = []

        def add(plant: dict[str, Any], kind: str, at: datetime) -> None:
            if start <= at < end:
                events.append(
                    {
                        "plant_id": plant["id"],
                        "name": plant["name"],
                        "kind": kind,
                        "at": dt_util.as_utc(at).isoformat(),
                    }
                )

        for plant in self.plants:
            status = self.status.get(plant["id"])
            if status is None:
                continue
            waterings = care.forecast(status, start, end)
            if (entry := planned.get(plant["id"])) and leave and back:
                waterings = [when for when in waterings if when < leave]
                if entry["prepare"]:
                    add(plant, "prepare", leave - timedelta(hours=14))
                for day in entry["visits"]:
                    noon = datetime.combine(date.fromisoformat(day), time(trips.VISIT_HOUR), tz)
                    add(plant, "sitter", noon)
                remaining = max(0.0, 1 - entry["back_dryness"]) * entry["interval_days"]
                resume = {
                    **status,
                    "next_watering": (back + timedelta(days=remaining)).isoformat(),
                }
                waterings += care.forecast(resume, start, end)
            for when in waterings:
                add(plant, "water", when)
            if (fertilize := status["next_fertilization"]) and not status["fertilizing_paused"]:
                at = max(datetime.fromisoformat(fertilize), now)
                if leave and back and leave <= at < back:
                    at = back
                add(plant, "fertilize", at)
        if leave and back and leave < end and back > start:
            events.append(
                {
                    "plant_id": None,
                    "name": "Away",
                    "kind": "vacation",
                    "at": dt_util.as_utc(leave).isoformat(),
                    "end": dt_util.as_utc(back).isoformat(),
                }
            )
        return sorted(events, key=lambda event: event["at"])

    # -- vacation ----------------------------------------------------------

    def _trip_times(self, vacation: dict[str, Any]) -> tuple[datetime, datetime]:
        """When you leave and are back, in local time (visit days are local days)."""
        return trips.trip_times(
            date.fromisoformat(vacation["start_date"]),
            date.fromisoformat(vacation["end_date"]),
            dt_util.get_default_time_zone(),
        )

    def _plan(self, vacation: dict[str, Any]) -> dict[str, Any] | None:
        """The plan for a vacation, or None once it is over."""
        leave, back = self._trip_times(vacation)
        now = dt_util.utcnow()
        if back <= now:
            return None
        return trips.plan(self.plants, self.status, leave, back, now, self.hass.config.latitude)

    @property
    def away(self) -> bool:
        """Whether a vacation is going on."""
        return bool(self.trip and self.trip["active"])

    def label(self, plant_id: str) -> str:
        """A plant's name with its area, for messages."""
        plant = next((p for p in self.plants if p["id"] == plant_id), None)
        if plant is None:
            return plant_id
        area = ar.async_get(self.hass).async_get_area(plant["area_id"] or "")
        return f"{plant['name']} ({area.name})" if area else plant["name"]

    def vacation_view(self, plan: dict[str, Any] | None = None) -> dict[str, Any]:
        """The vacation, its plan, and the plan as text for the sitter."""
        vacation, trip = (self.vacation, self.trip) if plan is None else (None, plan)
        return {
            "vacation": vacation,
            "plan": trip,
            "text": trips.plan_text(
                vacation or {}, trip, {p["id"]: self.label(p["id"]) for p in self.plants}
            )
            if trip
            else None,
        }

    def preview_vacation(self, start: date, end: date) -> dict[str, Any]:
        """The plan for a trip that is not saved."""
        plan = self._plan({"start_date": start.isoformat(), "end_date": end.isoformat()})
        if plan is None:
            raise ValueError("This trip is already over")
        return self.vacation_view(plan)

    def _check_notify(self, service: str | None) -> None:
        if not service:
            return
        domain, _, name = service.rpartition(".")
        if not self.hass.services.has_service(domain or "notify", name):
            raise ValueError(f"The notify action {service} does not exist")

    async def async_set_vacation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Plan a vacation, or change the one that is planned or going on."""
        self._check_notify(data.get("sitter_notify"))
        if data["end_date"] < dt_util.now().date().isoformat():
            raise ValueError("This trip is already over")
        current = self.vacation
        await self._run(
            self.db.save_vacation, current["id"] if current else None, data, self._now()
        )
        await self.async_refresh()
        return self.vacation_view()

    async def async_end_vacation(self) -> None:
        """Back early, or cancel the planned vacation."""
        if self.vacation is None:
            raise NotFoundError("No vacation is planned")
        vacation_id, started = self.vacation["id"], self.away
        await self._run(lambda: self.db.end_vacation(vacation_id, self._now(), started=started))
        await self.async_refresh()

    async def async_send_plan(self) -> None:
        """Send the plan to the plant sitter's notify action."""
        if self.vacation is None or self.trip is None:
            raise NotFoundError("No vacation is planned")
        if not (service := (self.vacation.get("sitter_notify") or "").strip()):
            raise ValueError("Set a notify action for the plant sitter first")
        await self._async_notify(service, self.vacation_view()["text"], title="Plant care")

    def _prepare_message(self) -> str:
        """What to do before leaving."""
        trip = self.trip or {}
        lines = []
        if water := [self.label(pid) for pid in trip.get("prepare", [])]:
            lines.append("💧 Water right before you leave: " + ", ".join(water))
        measures = [
            f"{self.label(entry['plant_id'])}: {trips.TIP_TEXT[code].lower()}"
            for entry in trip.get("plants", [])
            if entry["risk"] != trips.RISK_OK
            for code in entry["tips"]
            if code != "sensor"
        ]
        if measures:
            lines.append("🌤 " + "; ".join(measures))
        if visits := trip.get("visits"):
            first = date.fromisoformat(visits[0]["date"]).strftime("%a %d %b")
            lines.append(
                f"🧑‍🌾 The plant sitter needs to come {len(visits)} "
                f"time{'s' if len(visits) > 1 else ''}, first on {first}"
            )
        return "\n".join(lines) or "All plants last until you are back 🌿"

    @callback
    def _track_vacation(self) -> None:
        """Fire start and end events and keep the checklist notification up to date."""
        away = self.vacation if self.away else None
        # Not on the first refresh: a restart during a vacation doesn't start it again.
        if self._tracking and away and not self._away:
            self.hass.bus.async_fire(EVENT_VACATION_STARTED, away)
        elif self._tracking and self._away and not away:
            self.hass.bus.async_fire(EVENT_VACATION_ENDED, self._away)
        self._away = away
        self._tracking = True

        note = None
        if self.trip and not self.trip["active"] and self.options[CONF_NOTIFY_ALERTS]:
            leave = datetime.fromisoformat(self.trip["leave"])
            if leave - dt_util.utcnow() <= PREPARE_AHEAD:
                note = self._prepare_message()
        if note == self._prepare_note:
            return
        self._prepare_note = note
        if note:
            persistent_notification.async_create(
                self.hass,
                f"{note}\n\n[Open the vacation plan](/{PANEL_URL_PATH}/vacation)",
                title=f"{NAME}: Before you leave",
                notification_id=f"{DOMAIN}_vacation",
            )
        else:
            persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_vacation")

    # -- alerts ------------------------------------------------------------

    @callback
    def _announce_alerts(self) -> None:
        """Notify about new alerts once and clear resolved ones."""
        active = {alert["key"]: alert for alert in self.alerts}
        new = [alert for key, alert in active.items() if key not in self._announced]
        resolved = self._announced - active.keys()
        notify = self.options[CONF_NOTIFY_ALERTS]
        for alert in new:
            self.hass.bus.async_fire(EVENT_ALERT, alert)
            if alert["kind"] != KIND_PROBLEM:
                continue
            if notify:
                persistent_notification.async_create(
                    self.hass,
                    f"{alert['message']}. [Open the plant](/{PANEL_URL_PATH}/plants)",
                    title=NAME,
                    notification_id=f"{DOMAIN}_alert_{alert['key']}",
                )
            for service in self._targets(problems=True):
                self.hass.async_create_task(self._async_notify(service, alert["message"]))
        for key in resolved:
            self.hass.bus.async_fire(EVENT_ALERT_CLEARED, {"key": key})
            persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_alert_{key}")
        # Watering and fertilizing share one notification each instead of one per plant.
        for kind, title in ((KIND_WATER, "Needs water"), (KIND_FERTILIZE, "Fertilize")):
            names = [a["message"] for a in self.alerts if a["kind"] == kind]
            notification_id = f"{DOMAIN}_{kind}"
            if names and notify:
                if new or resolved:
                    persistent_notification.async_create(
                        self.hass,
                        "\n".join(f"- {name}" for name in names)
                        + f"\n\n[Open today's care](/{PANEL_URL_PATH}/today)",
                        title=f"{NAME}: {title}",
                        notification_id=notification_id,
                    )
            else:
                persistent_notification.async_dismiss(self.hass, notification_id)
        if new or resolved:
            self._announced = set(active)
            self._alert_store.async_delay_save(lambda: {"announced": sorted(self._announced)}, 2)

    async def _async_notify(self, service: str, message: str, title: str = NAME) -> None:
        domain, _, name = service.rpartition(".")
        try:
            await self.hass.services.async_call(
                domain or "notify", name, {"title": title, "message": message}, blocking=True
            )
        except Exception:
            _LOGGER.warning("Could not send the notification with %s", service, exc_info=True)

    # -- reminders ---------------------------------------------------------

    def _user_targets(self) -> set[str]:
        return {t for settings in self.notify_users.values() for t in settings["targets"]}

    def _targets(self, *, problems: bool = False, daily: bool = False) -> set[str]:
        """Notify actions that get problems or the daily summary.

        The integration's notify action, unless a user picked that phone in the panel
        (then their own settings decide), plus every user's phones that want it.
        """
        targets = set()
        if own := (self.options[CONF_NOTIFY_SERVICE] or "").strip():
            targets.add(own)
        targets -= self._user_targets()
        for settings in self.notify_users.values():
            if (problems and settings["problems"]) or (daily and settings["daily"]):
                targets.update(settings["targets"])
        return targets

    def _visit_today(self) -> dict[str, Any] | None:
        if not (self.away and self.trip):
            return None
        today = dt_util.now().date().isoformat()
        return next((v for v in self.trip["visits"] if v["date"] == today), None)

    def _daily_message(self, *, force: bool = False) -> str:
        """Today's summary for the plants' owners."""
        if self.away and self.vacation:
            if visit := self._visit_today():
                names = ", ".join(self.label(p) for p in visit["plant_ids"])
                if self.vacation.get("sitter_notify"):
                    sitter = self.vacation.get("sitter") or "The plant sitter"
                    return f"🧳 {sitter} waters today: {names}"
                return f"🪴 Please water today: {names}"
            return "Nothing to water today 🌿" if force else ""
        lines = [summary_message(self.plants, self.status)]
        if self.trip:
            leave = dt_util.as_local(datetime.fromisoformat(self.trip["leave"])).date()
            if leave == dt_util.now().date() + timedelta(days=1):
                lines.append("🧳 Leaving tomorrow:\n" + self._prepare_message())
        message = "\n".join(line for line in lines if line)
        return message or ("All plants are happy 🌿" if force else "")

    async def _async_send_daily(self, targets: set[str], *, force: bool = False) -> bool:
        if not targets or not (message := self._daily_message(force=force)):
            return False
        title = "Plant care" if self.away else NAME
        for service in sorted(targets):
            await self._async_notify(service, message, title=title)
        return True

    async def _async_sitter_reminder(self, *, force: bool = False) -> bool:
        """While away, tell the plant sitter what to water today."""
        if not (self.away and self.vacation):
            return False
        if not (service := (self.vacation.get("sitter_notify") or "").strip()):
            return False
        visit = self._visit_today()
        if visit is None and not force:
            return False
        message = (
            "🪴 Please water today: " + ", ".join(self.label(p) for p in visit["plant_ids"])
            if visit
            else "Nothing to water today 🌿"
        )
        await self._async_notify(service, message, title="Plant care")
        return True

    async def _async_reminder_job(self, _now: datetime) -> None:
        """At the integration's reminder time: the sitter and the notify action."""
        await self._async_sitter_reminder()
        await self._async_send_daily(self._targets())

    async def _async_user_reminders(self, now: datetime) -> None:
        """Every minute: the daily summary for users whose time it is."""
        minute = dt_util.as_local(now).strftime("%H:%M")
        for settings in self.notify_users.values():
            if settings["daily"] and settings["targets"] and settings["time"][:5] == minute:
                await self._async_send_daily(set(settings["targets"]))

    async def async_send_reminder(self, *, force: bool = False) -> bool:
        """Send today's care summary now to everyone. Returns whether anything was sent."""
        sitter = await self._async_sitter_reminder(force=force)
        owners = await self._async_send_daily(self._targets(daily=True), force=force)
        return sitter or owners

    # -- notification settings per user ------------------------------------

    def phones(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """Phones with the Home Assistant app that can get notifications, the user's first."""
        phones = []
        for entry in self.hass.config_entries.async_entries("mobile_app"):
            if not (device := entry.data.get("device_name")):
                continue
            name = f"mobile_app_{slugify(device)}"
            if self.hass.services.has_service("notify", name):
                phones.append(
                    {
                        "service": f"notify.{name}",
                        "name": device,
                        "mine": bool(user_id) and entry.data.get("user_id") == user_id,
                    }
                )
        return sorted(phones, key=lambda p: (not p["mine"], p["name"].lower()))

    def notification_settings(self, user_id: str) -> dict[str, Any]:
        """A user's settings; new users get the summary at the integration's time."""
        default_time = (self.options[CONF_REMINDER_TIME] or "09:00")[:5]
        defaults = {"targets": [], "daily": True, "time": default_time, "problems": True}
        return {**defaults, **self.notify_users.get(user_id, {})}

    async def async_set_notifications(self, user_id: str, settings: dict[str, Any]) -> None:
        """Save which phones of a user get what."""
        for service in settings["targets"]:
            self._check_notify(service)
        if dt_util.parse_time(settings["time"]) is None:
            raise ValueError(f"Invalid time {settings['time']}")
        if settings["targets"]:
            self.notify_users[user_id] = {**self.notification_settings(user_id), **settings}
        else:
            self.notify_users.pop(user_id, None)
        await self._notify_store.async_save({"users": self.notify_users})

    async def async_test_notification(self, user_id: str) -> int:
        """Send a test to a user's phones. Returns how many."""
        targets = self.notification_settings(user_id)["targets"]
        for service in targets:
            await self._async_notify(
                service, "🌿 Plant Manager notifications work on this phone.", title=NAME
            )
        return len(targets)

    # -- plants ------------------------------------------------------------

    async def async_plant(self, plant_id: str) -> dict[str, Any]:
        """Return one plant with status and care log."""
        plant = await self._run(self.db.get_plant, plant_id)
        view = self.plant_view(plant)
        view["events"] = await self._run(self.db.events, plant_id)
        return view

    async def async_create_plant(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a plant. Without a profile, one is looked up for the species."""
        plant_id = await self._async_create(data)
        await self.async_refresh(tick=True)
        return self.plant_view(await self._run(self.db.get_plant, plant_id))

    async def _async_create(
        self, data: dict[str, Any], *, source: str = "created", fill_profile: bool = False
    ) -> str:
        """Create a plant without refreshing. ``fill_profile`` completes a partial profile."""
        data = dict(data)
        last_watered = data.pop("last_watered", None)
        if not data.get("profile") or (fill_profile and data.get("species")):
            resolved = await self.async_resolve_profile(
                data.get("species") or "", data.get("family")
            )
            given = data.get("profile") or {}
            data["profile"] = {**resolved["profile"], **given}
            data["profile_sources"] = [*resolved["sources"], *(["CSV import"] if given else [])]
            data["common_name"] = data.get("common_name") or resolved["common_name"]
        now = self._now()
        plant = await self._run(self.db.create_plant, data, now)
        if last_watered:
            at = self._watered_at(last_watered)
            await self._run(
                lambda: self.db.add_event(plant["id"], CARE_WATER, at, now, source=source)
            )
        return plant["id"]

    @staticmethod
    def _watered_at(value: str) -> str:
        """A date or datetime as a UTC timestamp. A plain date means noon, or now if earlier."""
        if day := dt_util.parse_date(value) if len(value) == 10 else None:
            noon = dt_util.start_of_local_day(day) + timedelta(hours=12)
            return dt_util.as_utc(min(noon, dt_util.now())).isoformat()
        if parsed := dt_util.parse_datetime(value):
            return dt_util.as_utc(parsed).isoformat()
        raise ValueError(f"Invalid date {value}")

    async def async_update_plant(self, plant_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Update a plant."""
        plant = await self._run(self.db.update_plant, plant_id, changes, self._now())
        self._sync_device(plant)
        await self.async_refresh()
        return self.plant_view(plant)

    def _sync_device(self, plant: dict[str, Any]) -> None:
        if device := self._device(plant["id"]):
            dr.async_get(self.hass).async_update_device(
                device.id,
                name=plant["name"],
                manufacturer=plant.get("common_name"),
                model=plant.get("species"),
                area_id=plant.get("area_id"),
            )

    def _device(self, plant_id: str) -> dr.DeviceEntry | None:
        registry = dr.async_get(self.hass)
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            if (DOMAIN, plant_id) in device.identifiers:
                return device
        return None

    @callback
    def async_remove_stale_devices(self) -> None:
        """Remove the devices of plants that no longer exist (e.g. after a restore)."""
        registry = dr.async_get(self.hass)
        plant_ids = {plant["id"] for plant in self.plants}
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            ids = {value for domain, value in device.identifiers if domain == DOMAIN}
            if ids and self.entry.entry_id not in ids and not ids & plant_ids:
                registry.async_remove_device(device.id)

    async def async_delete_plant(self, plant_id: str) -> None:
        """Delete a plant, its photos and its device."""
        filenames = await self._run(self.db.delete_plant, plant_id)
        await self._run(self._remove_files, filenames)
        if device := self._device(plant_id):
            dr.async_get(self.hass).async_remove_device(device.id)
        await self.async_refresh()

    async def async_resolve_profile(
        self, species: str, family: str | None = None
    ) -> dict[str, Any]:
        """Look up a care profile for a species."""
        resolved = await async_resolve_profile(self.hass, self.options, species, family)
        return {
            "profile": resolved.profile,
            "sources": resolved.sources,
            "common_name": resolved.common_name,
        }

    # -- care --------------------------------------------------------------

    def _fire_care(self, plant_id: str, kind: str, source: str) -> None:
        name = next((p["name"] for p in self.plants if p["id"] == plant_id), None)
        self.hass.bus.async_fire(
            EVENT_CARE_LOGGED, {"plant_id": plant_id, "name": name, "kind": kind, "source": source}
        )

    async def async_water(
        self,
        plant_id: str,
        at: str | None = None,
        feedback: str | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Log a watering, optionally with feedback on how dry the soil was."""
        plant = await self._run(self.db.get_plant, plant_id)
        now = dt_util.utcnow()
        when = dt_util.parse_datetime(self._watered_at(at)) if at else now
        state = None
        last = dt_util.parse_datetime(plant["last_watered"]) if plant["last_watered"] else None
        # Logging an older watering after a newer one only adds it to the history.
        if last is None or when >= last:
            learned = care.learned_after(plant["learned_factor"], feedback)
            interval, _ = care.compute_interval(
                {**plant, "learned_factor": learned},
                temperature=plant["temp_ema"],
                humidity=plant["humidity_ema"],
                growth=self.growth,
            )
            dryness = max(0.0, (now - when).total_seconds() / 86400 / interval)
            state = {"dryness": dryness, "learned_factor": learned, "last_tick": now.isoformat()}
        event = await self._run(
            lambda: self.db.add_event(
                plant_id,
                CARE_WATER,
                when.isoformat(),
                now.isoformat(),
                feedback=feedback,
                source=source,
                state=state,
            )
        )
        self._fire_care(plant_id, CARE_WATER, source)
        await self.async_refresh()
        return event

    async def async_snooze(self, plant_id: str, source: str = "manual") -> dict[str, Any]:
        """Soil still moist: push the reminder back and learn a longer interval."""
        plant = await self._run(self.db.get_plant, plant_id)
        learned, dryness = care.snoozed(plant["learned_factor"], plant["dryness"] or 0.0)
        now = self._now()
        event = await self._run(
            lambda: self.db.add_event(
                plant_id,
                KIND_SNOOZE,
                now,
                now,
                source=source,
                state={"dryness": dryness, "learned_factor": learned},
            )
        )
        self._fire_care(plant_id, KIND_SNOOZE, source)
        await self.async_refresh()
        return event

    async def async_log(
        self,
        plant_id: str,
        kind: str,
        at: str | None = None,
        notes: str | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Log fertilizing, repotting, pruning, misting or a note."""
        now = self._now()
        when = self._watered_at(at) if at else now
        event = await self._run(
            lambda: self.db.add_event(plant_id, kind, when, now, notes=notes, source=source)
        )
        self._fire_care(plant_id, kind, source)
        await self.async_refresh()
        return event

    async def async_delete_event(self, event_id: int) -> None:
        """Remove a care log entry. Undoing the latest watering also restores the schedule."""
        event = await self._run(self.db.get_event, event_id)
        last = await self._run(self.db.last_event, event["plant_id"])
        restore = event["kind"] in (CARE_WATER, KIND_SNOOZE) and last and last["id"] == event_id
        await self._run(lambda: self.db.delete_event(event_id, restore_state=bool(restore)))
        await self.async_refresh(tick=True)

    async def async_undo(self, event_id: int) -> bool:
        """Undo a care event logged in the last few minutes."""
        try:
            event = await self._run(self.db.get_event, event_id)
        except NotFoundError:
            return False
        created = dt_util.parse_datetime(event["created_at"])
        if created is None or dt_util.utcnow() - created > timedelta(minutes=UNDO_WINDOW_MINUTES):
            return False
        await self.async_delete_event(event_id)
        return True

    # -- photos ------------------------------------------------------------

    def photo_path(self, filename: str) -> str:
        """Return the absolute path of a stored photo."""
        return os.path.join(self.photo_dir, os.path.basename(filename))

    async def async_photo_file(self, photo_id: str) -> str:
        """Return the file path of a photo."""
        photo = await self._run(self.db.get_photo, photo_id)
        return self.photo_path(photo["filename"])

    async def async_add_photo(self, plant_id: str, data: bytes, source: str) -> dict[str, Any]:
        """Store image bytes as a photo of a plant."""
        extension = image_extension(data)
        if extension is None:
            raise ValueError("Unsupported image format")
        await self._run(self.db.get_plant, plant_id)
        filename = f"{uuid.uuid4().hex}.{extension}"
        await self._run(self._write_file, self.photo_path(filename), data)
        photo = await self._run(self.db.add_photo, plant_id, filename, source, self._now())
        await self.async_refresh()
        return photo

    async def async_delete_photo(self, photo_id: str) -> None:
        """Delete a photo."""
        filename = await self._run(self.db.delete_photo, photo_id)
        await self._run(self._remove_files, [filename])
        await self.async_refresh()

    async def async_reorder_photos(self, plant_id: str, photo_ids: list[str]) -> None:
        """Reorder a plant's photos."""
        await self._run(self.db.reorder_photos, plant_id, photo_ids)
        await self.async_refresh()

    @staticmethod
    def _write_file(path: str, data: bytes) -> None:
        with open(path, "wb") as file:
            file.write(data)

    def _remove_files(self, filenames: list[str]) -> None:
        for filename in filenames:
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.photo_path(filename))

    # -- identification (staged photos) ------------------------------------

    def staged_path(self, staged_id: str) -> str | None:
        """Return the file of a staged photo, if it is still staged."""
        if (entry := self._staged.get(staged_id)) is None:
            return None
        return os.path.join(self.staging_dir, entry[0])

    def staged_media_id(self, staged_id: str) -> str:
        """Media source id of a staged photo (for AI Task attachments)."""
        return f"media-source://{DOMAIN}/staged/{staged_id}"

    async def async_stage_photo(self, data: bytes) -> str:
        """Keep a photo for an hour, until it is saved with a plant."""
        extension = image_extension(data)
        if extension is None:
            raise ValueError("Unsupported image format")
        staged_id = uuid.uuid4().hex
        filename = f"{staged_id}.{extension}"
        await self._run(self._write_file, os.path.join(self.staging_dir, filename), data)
        self._staged[staged_id] = (filename, dt_util.utcnow() + STAGING_LIFETIME)
        return staged_id

    async def async_identify(self, data: bytes) -> dict[str, Any]:
        """Stage a photo and identify the plant in it."""
        staged_id = await self.async_stage_photo(data)
        result: dict[str, Any] = {"staged_id": staged_id, "candidates": [], "error": None}
        if self.options[CONF_ID_PROVIDER] == PROVIDER_NONE:
            result["error"] = "no_provider"
            return result
        filename = self._staged[staged_id][0]
        try:
            candidates = await async_identify(
                self.hass, self.options, data, mime_type(filename), self.staged_media_id(staged_id)
            )
        except IdentificationError as err:
            _LOGGER.warning("Plant identification failed: %s", err)
            result["error"] = err.reason
            return result
        result["candidates"] = [candidate.as_dict() for candidate in candidates]
        if not candidates:
            result["error"] = "no_match"
        return result

    async def async_attach_staged(self, plant_id: str, staged_id: str) -> dict[str, Any]:
        """Save a staged photo as a photo of a plant."""
        if (path := self.staged_path(staged_id)) is None:
            raise NotFoundError("The photo is no longer available, take it again")
        await self._run(self.db.get_plant, plant_id)
        filename = self._staged.pop(staged_id)[0]
        await self._run(shutil.move, path, self.photo_path(filename))
        photo = await self._run(self.db.add_photo, plant_id, filename, "camera", self._now())
        await self.async_refresh()
        return photo

    def _remove_staged(self, filenames: list[str]) -> None:
        for filename in filenames:
            with contextlib.suppress(FileNotFoundError):
                os.remove(os.path.join(self.staging_dir, filename))

    # -- import, export, backup --------------------------------------------

    def _area_names(self) -> dict[str, str]:
        return {area.id: area.name for area in ar.async_get(self.hass).async_list_areas()}

    async def async_export_json(self) -> dict[str, Any]:
        """Everything as JSON (for other tools; restore uses a backup instead)."""
        data = await self._run(self.db.export_all)
        return {"schema": self.db.schema_version, "exported_at": self._now(), **data}

    async def async_export_csv(self) -> str:
        """The plants as CSV."""
        return plants_to_csv(self.plants, self._area_names())

    async def async_import_csv(self, text: str) -> dict[str, Any]:
        """Create plants from CSV rows. Returns what was created and what was skipped."""
        areas: dict[str, str] = {}
        for area_id, name in self._area_names().items():
            areas[name.lower()] = area_id
            areas[area_id.lower()] = area_id
        plants, errors, warnings = await self._run(parse_plants_csv, text, areas)
        for data in plants:
            await self._async_create(data, source="import", fill_profile=True)
        await self.async_refresh(tick=True)
        return {"created": len(plants), "errors": errors, "warnings": warnings}

    async def async_create_backup(self) -> str:
        """Create a backup zip (database and photos). Returns its id."""
        backup_id = uuid.uuid4().hex
        path = os.path.join(self.staging_dir, f"backup_{backup_id}.zip")
        await self._run(self._write_backup, path)
        self._backups[backup_id] = (path, dt_util.utcnow() + BACKUP_LIFETIME)
        return backup_id

    def backup_path(self, backup_id: str) -> str | None:
        """Return the file of a backup that was created recently."""
        entry = self._backups.get(backup_id)
        return entry[0] if entry else None

    def _write_backup(self, path: str) -> None:
        with tempfile.TemporaryDirectory(dir=self.staging_dir) as tmp:
            db_copy = os.path.join(tmp, DB_FILENAME)
            self.db.backup_to(db_copy)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(db_copy, DB_FILENAME)
                for name in os.listdir(self.photo_dir):
                    full = os.path.join(self.photo_dir, name)
                    if os.path.isfile(full):
                        archive.write(full, f"{PHOTO_DIR}/{name}")

    @staticmethod
    def _remove_paths(paths: list[str]) -> None:
        for path in paths:
            with contextlib.suppress(FileNotFoundError):
                os.remove(path)

    async def async_restore_backup(self, data: bytes) -> dict[str, Any]:
        """Replace everything with a backup zip, keeping the current data as *.before-restore."""
        info = await self._run(self._prepare_restore, data)
        await self._run(self.db.close)
        try:
            await self._run(self._swap_restore, info["folder"])
        finally:
            # Reopen (and migrate) the database. The staging folder was moved away with the
            # old photos, so staged photos and backups are gone too.
            self._staged.clear()
            self._backups.clear()
            await self._run(self._setup_files)
        # No reload: that would take the panel away from whoever is restoring.
        await self.async_refresh(tick=True)
        self.async_remove_stale_devices()
        for plant in self.plants:
            self._sync_device(plant)
        return {"plants": info["plants"], "photos": info["photos"]}

    def _prepare_restore(self, data: bytes) -> dict[str, Any]:
        folder = tempfile.mkdtemp(prefix="restore_", dir=self.staging_dir)
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                names = archive.namelist()
                if DB_FILENAME not in names:
                    raise ValueError("This is not a Plant Manager backup")
                for name in names:
                    if name == DB_FILENAME or (
                        name.startswith(f"{PHOTO_DIR}/")
                        and "/" not in name[len(PHOTO_DIR) + 1 :]
                        and ".." not in name
                        and name != f"{PHOTO_DIR}/"
                    ):
                        archive.extract(name, folder)
            conn = sqlite3.connect(os.path.join(folder, DB_FILENAME))
            try:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                plants = conn.execute("SELECT COUNT(*) FROM plants").fetchone()[0]
            except sqlite3.DatabaseError as err:
                raise ValueError("The backup's database is damaged") from err
            finally:
                conn.close()
            if not 1 <= version <= len(MIGRATIONS):
                raise ValueError("The backup is from a newer version of Plant Manager")
        except zipfile.BadZipFile as err:
            shutil.rmtree(folder, ignore_errors=True)
            raise ValueError("This is not a zip file") from err
        except ValueError:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        photos_dir = os.path.join(folder, PHOTO_DIR)
        photos = len(os.listdir(photos_dir)) if os.path.isdir(photos_dir) else 0
        return {"folder": folder, "plants": plants, "photos": photos}

    def _swap_restore(self, folder: str) -> None:
        base = os.path.dirname(self.photo_dir)
        db_path = os.path.join(base, DB_FILENAME)
        for suffix in ("-wal", "-shm"):
            with contextlib.suppress(FileNotFoundError):
                os.remove(db_path + suffix)
        old_db = db_path + ".before-restore"
        old_photos = self.photo_dir + ".before-restore"
        with contextlib.suppress(FileNotFoundError):
            os.remove(old_db)
        shutil.rmtree(old_photos, ignore_errors=True)
        # The staging folder lives inside the photo folder; take the restore files out first.
        moved = os.path.join(base, f"restore_{uuid.uuid4().hex}")
        shutil.move(folder, moved)
        if os.path.exists(db_path):
            os.replace(db_path, old_db)
        os.replace(os.path.join(moved, DB_FILENAME), db_path)
        os.replace(self.photo_dir, old_photos)
        new_photos = os.path.join(moved, PHOTO_DIR)
        if os.path.isdir(new_photos):
            os.replace(new_photos, self.photo_dir)
        else:
            os.makedirs(self.photo_dir)
        shutil.rmtree(moved, ignore_errors=True)
