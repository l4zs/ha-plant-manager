"""Sensors for Plant Manager."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import STATUSES
from .entity import PlantEntity, PlantManagerEntity, async_track_plants
from .manager import PlantManager

MAX_LISTED = 50


def _time(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _names(plants: list[dict[str, Any]]) -> dict[str, Any]:
    return {"plants": [{"id": p["id"], "name": p["name"]} for p in plants[:MAX_LISTED]]}


@dataclass(frozen=True, kw_only=True)
class HubSensorDescription(SensorEntityDescription):
    """Describes a sensor about all plants."""

    value: Callable[[dict[str, Any]], Any]
    attributes: Callable[[dict[str, Any]], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class PlantSensorDescription(SensorEntityDescription):
    """Describes a sensor of one plant."""

    value: Callable[[dict[str, Any], dict[str, Any]], Any]
    attributes: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None


HUB_SENSORS = (
    HubSensorDescription(key="plants", value=lambda s: s["total"]),
    HubSensorDescription(
        key="needs_water",
        value=lambda s: len(s["needs_water"]),
        attributes=lambda s: _names(s["needs_water"]),
    ),
    HubSensorDescription(
        key="problems",
        value=lambda s: len(s["problems"]),
        attributes=lambda s: _names(s["problems"]),
    ),
    HubSensorDescription(
        key="next_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda s: _time(s["next_watering"]),
    ),
)

PLANT_SENSORS = (
    PlantSensorDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        value=lambda plant, care: care["status"],
        attributes=lambda plant, care: {
            "problems": care["problems"],
            "species": plant.get("species"),
            "care_profile": plant.get("profile"),
        },
    ),
    PlantSensorDescription(
        key="next_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda plant, care: _time(care["next_watering"]).replace(second=0, microsecond=0),
    ),
    PlantSensorDescription(
        key="water_reserve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value=lambda plant, care: care["water_reserve"],
    ),
    PlantSensorDescription(
        key="watering_interval",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value=lambda plant, care: care["interval_days"],
        attributes=lambda plant, care: {
            "factors": care["factors"],
            "average_actual_interval_days": care["average_interval_days"],
        },
    ),
    PlantSensorDescription(
        key="last_watered",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda plant, care: _time(plant.get("last_watered")),
    ),
    PlantSensorDescription(
        key="next_fertilization",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda plant, care: _time(care["next_fertilization"]),
        attributes=lambda plant, care: {"paused_for_winter": care["fertilizing_paused"]},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[PlantManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities(HubSensor(entry, description) for description in HUB_SENSORS)
    async_track_plants(
        entry,
        async_add_entities,
        lambda plant: [PlantSensor(entry, plant, description) for description in PLANT_SENSORS],
    )


class HubSensor(PlantManagerEntity, SensorEntity):
    """A sensor about all plants."""

    entity_description: HubSensorDescription

    def __init__(self, entry: ConfigEntry[PlantManager], description: HubSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the value."""
        return self.entity_description.value(self._manager.summary)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the plant list."""
        if self.entity_description.attributes is None:
            return None
        return self.entity_description.attributes(self._manager.summary)


class PlantSensor(PlantEntity, SensorEntity):
    """A sensor of one plant."""

    entity_description: PlantSensorDescription

    def __init__(
        self,
        entry: ConfigEntry[PlantManager],
        plant: dict[str, Any],
        description: PlantSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(entry, plant, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the value."""
        plant, care = self.plant, self.care
        if plant is None or care is None:
            return None
        return self.entity_description.value(plant, care)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra details."""
        plant, care = self.plant, self.care
        if plant is None or care is None or self.entity_description.attributes is None:
            return None
        return self.entity_description.attributes(plant, care)
