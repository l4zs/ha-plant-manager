"""Calendar of projected plant care."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import PlantManagerEntity
from .manager import PlantManager

ICONS = {
    "water": "💧 Water",
    "fertilize": "🌱 Fertilize",
    "prepare": "🧳 Water before leaving:",
    "sitter": "🧑‍🌾 Plant sitter waters",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[PlantManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the care calendar."""
    async_add_entities([PlantCareCalendar(entry)])


def _day(value: str):
    return dt_util.as_local(dt_util.parse_datetime(value)).date()


class PlantCareCalendar(PlantManagerEntity, CalendarEntity):
    """Upcoming waterings and fertilizing, projected from current conditions."""

    def __init__(self, entry: ConfigEntry[PlantManager]) -> None:
        """Initialize the calendar."""
        super().__init__(entry, "care_calendar")

    def _events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        events = []
        for item in self._manager.schedule(start, end):
            day = _day(item["at"])
            if item["kind"] == "vacation":
                events.append(
                    CalendarEvent(
                        start=day,
                        end=_day(item["end"]) + timedelta(days=1),
                        summary="🧳 Vacation",
                        uid=f"vacation_{day.isoformat()}",
                    )
                )
                continue
            events.append(
                CalendarEvent(
                    start=day,
                    end=day + timedelta(days=1),
                    summary=f"{ICONS[item['kind']]} {item['name']}",
                    uid=f"{item['plant_id']}_{item['kind']}_{day.isoformat()}",
                )
            )
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """The next care event."""
        start = dt_util.start_of_local_day()
        events = self._events(start, start + timedelta(days=120))
        return events[0] if events else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Care events in a time range."""
        return self._events(start_date, end_date)
