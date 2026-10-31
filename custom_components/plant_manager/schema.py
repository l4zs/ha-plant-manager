"""Validation schemas for plants, used by the websocket API."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    LIGHT_LEVELS,
    P_BASE_INTERVAL,
    P_FERTILIZE_INTERVAL,
    P_LIGHT_PREFERENCE,
    P_MAX_HUMIDITY,
    P_MAX_LUX,
    P_MAX_MOISTURE,
    P_MAX_TEMP,
    P_MIN_HUMIDITY,
    P_MIN_LUX,
    P_MIN_MOISTURE,
    P_MIN_TEMP,
    P_NOTES,
    P_TOXIC_TO_PETS,
    P_WINTER_DORMANCY,
    PLACEMENTS,
    POT_MATERIALS,
)

_optional_text = vol.Any(None, vol.All(str, vol.Strip, vol.Length(max=500)))
_name = vol.All(str, vol.Strip, vol.Length(min=1, max=200))
_sensor = vol.Any(None, "", cv.entity_domain("sensor"))


def _number(low: float, high: float) -> vol.All:
    return vol.All(vol.Coerce(float), vol.Range(min=low, max=high))


PROFILE_SCHEMA = vol.Schema(
    {
        vol.Optional(P_BASE_INTERVAL): _number(0.5, 120),
        vol.Optional(P_WINTER_DORMANCY): bool,
        vol.Optional(P_FERTILIZE_INTERVAL): _number(0, 365),
        vol.Optional(P_MIN_TEMP): _number(-30, 50),
        vol.Optional(P_MAX_TEMP): _number(-30, 60),
        vol.Optional(P_MIN_HUMIDITY): _number(0, 100),
        vol.Optional(P_MAX_HUMIDITY): _number(0, 100),
        vol.Optional(P_MIN_MOISTURE): _number(0, 100),
        vol.Optional(P_MAX_MOISTURE): _number(0, 100),
        vol.Optional(P_MIN_LUX): _number(0, 200000),
        vol.Optional(P_MAX_LUX): _number(0, 200000),
        vol.Optional(P_LIGHT_PREFERENCE): vol.Any(None, vol.In(LIGHT_LEVELS)),
        vol.Optional(P_TOXIC_TO_PETS): vol.Any(None, bool),
        vol.Optional(P_NOTES): vol.Any(None, vol.All(str, vol.Length(max=2000))),
    }
)

PLANT_FIELDS_SCHEMA = {
    vol.Optional("name"): _name,
    vol.Optional("species"): _optional_text,
    vol.Optional("common_name"): _optional_text,
    vol.Optional("family"): _optional_text,
    vol.Optional("area_id"): vol.Any(None, str),
    vol.Optional("placement"): vol.In(PLACEMENTS),
    vol.Optional("light"): vol.In(LIGHT_LEVELS),
    vol.Optional("pot_diameter_cm"): _number(2, 300),
    vol.Optional("pot_material"): vol.In(POT_MATERIALS),
    vol.Optional("temperature_sensor"): _sensor,
    vol.Optional("humidity_sensor"): _sensor,
    vol.Optional("moisture_sensor"): _sensor,
    vol.Optional("illuminance_sensor"): _sensor,
    vol.Optional("profile"): PROFILE_SCHEMA,
    vol.Optional("profile_sources"): [str],
    vol.Optional("notes"): vol.Any(None, vol.All(str, vol.Length(max=5000))),
    vol.Optional("acquired_date"): vol.Any(None, "", cv.date),
}

PLANT_CREATE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): _name,
        **{key: value for key, value in PLANT_FIELDS_SCHEMA.items() if key != "name"},
        # Creates a watering in the care log.
        vol.Optional("last_watered"): vol.Any(None, "", cv.string),
    }
)


VACATION_SCHEMA = vol.Schema(
    {
        vol.Required("start_date"): cv.date,
        vol.Required("end_date"): cv.date,
        vol.Optional("sitter"): _optional_text,
        vol.Optional("sitter_notify"): vol.Any(None, "", cv.string),
        vol.Optional("notes"): vol.Any(None, vol.All(str, vol.Length(max=2000))),
    }
)
MAX_VACATION_DAYS = 365


def normalize_vacation(data: dict[str, Any]) -> dict[str, Any]:
    """Check the dates and turn them into ISO strings."""
    start, end = data["start_date"], data["end_date"]
    if end <= start:
        raise ValueError("The day you are back must be after the day you leave")
    if (end - start).days > MAX_VACATION_DAYS:
        raise ValueError(f"A vacation can be at most {MAX_VACATION_DAYS} days long")
    return normalize_plant(dict(data))


def normalize_plant(data: dict[str, Any]) -> dict[str, Any]:
    """Turn empty strings into None and dates into ISO strings."""
    for key, value in list(data.items()):
        if value == "":
            data[key] = None
        elif isinstance(value, date):
            data[key] = value.isoformat()
    profile = data.get("profile")
    if profile is not None:
        for low, high in (
            (P_MIN_TEMP, P_MAX_TEMP),
            (P_MIN_HUMIDITY, P_MAX_HUMIDITY),
            (P_MIN_MOISTURE, P_MAX_MOISTURE),
            (P_MIN_LUX, P_MAX_LUX),
        ):
            if low in profile and high in profile and profile[low] >= profile[high]:
                raise ValueError(f"{high.replace('_', ' ')} must be higher than the minimum")
    return data
