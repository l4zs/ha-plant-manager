"""Buttons for Plant Manager."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlantEntity, async_track_plants
from .manager import PlantManager


@dataclass(frozen=True, kw_only=True)
class PlantButtonDescription(ButtonEntityDescription):
    """Describes a plant care button."""

    press: Callable[[PlantManager, str], Awaitable[Any]]


BUTTONS = (
    PlantButtonDescription(key="water", press=lambda m, pid: m.async_water(pid, source="button")),
    PlantButtonDescription(key="snooze", press=lambda m, pid: m.async_snooze(pid, source="button")),
    PlantButtonDescription(
        key="fertilize", press=lambda m, pid: m.async_log(pid, "fertilize", source="button")
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[PlantManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons."""
    async_track_plants(
        entry,
        async_add_entities,
        lambda plant: [PlantButton(entry, plant, description) for description in BUTTONS],
    )


class PlantButton(PlantEntity, ButtonEntity):
    """A plant care action."""

    entity_description: PlantButtonDescription

    def __init__(
        self,
        entry: ConfigEntry[PlantManager],
        plant: dict[str, Any],
        description: PlantButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(entry, plant, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Log the care action."""
        await self.entity_description.press(self._manager, self.plant_id)
