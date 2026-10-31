"""Base entities for Plant Manager."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, NAME, SIGNAL_UPDATED
from .manager import PlantManager


class PlantManagerEntity(Entity):
    """An entity of the Plant Manager service device, updated on changes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry[PlantManager], key: str) -> None:
        """Initialize the entity."""
        self._manager = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Listen for updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class PlantEntity(PlantManagerEntity):
    """An entity of one plant's device."""

    def __init__(self, entry: ConfigEntry[PlantManager], plant: dict[str, Any], key: str) -> None:
        """Initialize the entity."""
        super().__init__(entry, key)
        self.plant_id: str = plant["id"]
        self._attr_unique_id = f"{plant['id']}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, plant["id"])},
            name=plant["name"],
            manufacturer=plant.get("common_name"),
            model=plant.get("species"),
            suggested_area=self._area_name(entry.runtime_data.hass, plant.get("area_id")),
        )

    @staticmethod
    def _area_name(hass: HomeAssistant, area_id: str | None) -> str | None:
        area = ar.async_get(hass).async_get_area(area_id) if area_id else None
        return area.name if area else None

    @property
    def plant(self) -> dict[str, Any] | None:
        """The plant, if it still exists."""
        return next((p for p in self._manager.plants if p["id"] == self.plant_id), None)

    @property
    def care(self) -> dict[str, Any] | None:
        """The plant's current care status."""
        return self._manager.status.get(self.plant_id)

    @property
    def available(self) -> bool:
        """Unavailable once the plant is deleted."""
        return self.care is not None


@callback
def async_track_plants(
    entry: ConfigEntry[PlantManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[dict[str, Any]], Iterable[Entity]],
) -> None:
    """Add entities for every plant, now and whenever one is created."""
    manager = entry.runtime_data
    known: set[str] = set()

    @callback
    def add_new() -> None:
        # Forget deleted plants, so they get entities again if a backup brings them back.
        known.intersection_update(plant["id"] for plant in manager.plants)
        new = [plant for plant in manager.plants if plant["id"] not in known]
        if not new:
            return
        known.update(plant["id"] for plant in new)
        async_add_entities([entity for plant in new for entity in factory(plant)])

    add_new()
    entry.async_on_unload(async_dispatcher_connect(manager.hass, SIGNAL_UPDATED, add_new))
