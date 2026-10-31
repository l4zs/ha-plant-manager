"""Binary sensors for Plant Manager."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .care import PROBLEM_TEXT
from .entity import PlantEntity, PlantManagerEntity, async_track_plants
from .i18n import tr
from .manager import PlantManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[PlantManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_add_entities([VacationSensor(entry)])
    async_track_plants(
        entry,
        async_add_entities,
        lambda plant: [NeedsWaterSensor(entry, plant), ProblemSensor(entry, plant)],
    )


class NeedsWaterSensor(PlantEntity, BinarySensorEntity):
    """On when the plant should be watered now."""

    def __init__(self, entry: ConfigEntry[PlantManager], plant: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(entry, plant, "needs_water")

    @property
    def is_on(self) -> bool | None:
        """Return whether the plant needs water."""
        return self.care["needs_water"] if self.care else None


class ProblemSensor(PlantEntity, BinarySensorEntity):
    """On when the plant's environment is out of its comfort range."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, entry: ConfigEntry[PlantManager], plant: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(entry, plant, "problem")

    @property
    def is_on(self) -> bool | None:
        """Return whether there is a problem."""
        return bool(self.care["problems"]) if self.care else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the problems and the readings."""
        if (care := self.care) is None:
            return None
        return {
            "problems": care["problems"],
            "messages": [
                tr(self._manager.language, PROBLEM_TEXT[code]) for code in care["problems"]
            ],
            "temperature": care["temperature"],
            "humidity": care["humidity"],
            "soil_moisture": care["moisture"],
            "max_illuminance_yesterday": care["lux_max_yesterday"],
        }


class VacationSensor(PlantManagerEntity, BinarySensorEntity):
    """On while you are away, with the plan as attributes."""

    def __init__(self, entry: ConfigEntry[PlantManager]) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "vacation")

    @property
    def is_on(self) -> bool:
        """Return whether a vacation is going on."""
        return self._manager.away

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the dates, the sitter, and the next visit."""
        manager = self._manager
        vacation, trip = manager.vacation, manager.trip
        if vacation is None or trip is None:
            return {"planned": False}
        visit = trip["visits"][0] if trip["visits"] else None
        return {
            "planned": True,
            "start_date": vacation["start_date"],
            "end_date": vacation["end_date"],
            "sitter": vacation["sitter"],
            "water_before_leaving": [manager.label(pid) for pid in trip["prepare"]],
            "sitter_visits": len(trip["visits"]),
            "next_visit": visit["date"] if visit else None,
            "next_visit_plants": [manager.label(pid) for pid in visit["plant_ids"]]
            if visit
            else [],
        }
