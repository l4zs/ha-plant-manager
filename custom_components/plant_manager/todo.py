"""To-do list of due plant care.

Items appear when a plant needs water (today) or fertilizer; checking one off
logs the care.
"""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import PlantManagerEntity
from .i18n import tr
from .manager import PlantManager

WATER = "water"
FERTILIZE = "fertilize"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[PlantManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the care to-do list."""
    async_add_entities([PlantCareTodo(entry)])


def _day(value: str):
    return dt_util.as_local(dt_util.parse_datetime(value)).date()


class PlantCareTodo(PlantManagerEntity, TodoListEntity):
    """Plant care that is due."""

    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, entry: ConfigEntry[PlantManager]) -> None:
        """Initialize the list."""
        super().__init__(entry, "care_tasks")

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the due care."""
        items: list[TodoItem] = []
        lang = self._manager.language
        for plant in self._manager.plants:
            care = self._manager.status.get(plant["id"])
            if care is None:
                continue
            if care["needs_water"] or care["days_until_watering"] < 1:
                items.append(
                    TodoItem(
                        summary=tr(lang, "💧 Water {name}", name=plant["name"]),
                        uid=f"{plant['id']}:{WATER}",
                        status=TodoItemStatus.NEEDS_ACTION,
                        due=_day(care["next_watering"]),
                    )
                )
            if care["fertilize_due"]:
                items.append(
                    TodoItem(
                        summary=tr(lang, "🌱 Fertilize {name}", name=plant["name"]),
                        uid=f"{plant['id']}:{FERTILIZE}",
                        status=TodoItemStatus.NEEDS_ACTION,
                        due=_day(care["next_fertilization"]),
                    )
                )
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Checking an item off logs the care."""
        if item.status != TodoItemStatus.COMPLETED or not item.uid:
            return
        plant_id, _, task = item.uid.partition(":")
        if task == WATER:
            await self._manager.async_water(plant_id, source="todo")
        elif task == FERTILIZE:
            await self._manager.async_log(plant_id, "fertilize", source="todo")
