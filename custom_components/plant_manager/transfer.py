"""CSV import/export of the plants.

The CSV export and import use the same columns, so an export is also a
template for adding many plants from a spreadsheet.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from homeassistant.util import dt as dt_util
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
    SENSOR_FIELDS,
)
from .schema import PLANT_CREATE_SCHEMA, normalize_plant

# CSV column -> care profile key
PROFILE_COLUMNS = {
    P_BASE_INTERVAL: P_BASE_INTERVAL,
    P_WINTER_DORMANCY: P_WINTER_DORMANCY,
    P_FERTILIZE_INTERVAL: P_FERTILIZE_INTERVAL,
    P_MIN_TEMP: P_MIN_TEMP,
    P_MAX_TEMP: P_MAX_TEMP,
    P_MIN_HUMIDITY: P_MIN_HUMIDITY,
    P_MAX_HUMIDITY: P_MAX_HUMIDITY,
    P_MIN_MOISTURE: P_MIN_MOISTURE,
    P_MAX_MOISTURE: P_MAX_MOISTURE,
    P_MIN_LUX: P_MIN_LUX,
    P_MAX_LUX: P_MAX_LUX,
    P_LIGHT_PREFERENCE: P_LIGHT_PREFERENCE,
    P_TOXIC_TO_PETS: P_TOXIC_TO_PETS,
    "care_notes": P_NOTES,
}
CSV_COLUMNS = [
    "name",
    "species",
    "common_name",
    "family",
    "area",
    "placement",
    "light",
    "pot_diameter_cm",
    "pot_material",
    *SENSOR_FIELDS,
    "last_watered",
    "acquired_date",
    "notes",
    *PROFILE_COLUMNS,
]
_BOOL_PROFILE = (P_WINTER_DORMANCY, P_TOXIC_TO_PETS)
_TEXT_PROFILE = (P_LIGHT_PREFERENCE, P_NOTES)
_CHOICES = {
    "placement": PLACEMENTS,
    "light": LIGHT_LEVELS,
    "pot_material": POT_MATERIALS,
    P_LIGHT_PREFERENCE: LIGHT_LEVELS,
}
_ALIASES = {
    "direct_sun": "direct",
    "sun": "direct",
    "bright": "bright_indirect",
    "indirect": "bright_indirect",
    "inside": "indoor",
    "outside": "outdoor",
    "covered": "outdoor_covered",
    "balcony": "outdoor_covered",
    "clay": "terracotta",
    "glazed": "ceramic",
}
_TRUE = ("1", "yes", "y", "true", "x", "ja")
_FALSE = ("0", "no", "n", "false", "nein")


def plants_to_csv(plants: list[dict[str, Any]], area_names: dict[str, str]) -> str:
    """Export plants as CSV (one row per plant)."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for plant in plants:
        row = {key: plant.get(key) for key in CSV_COLUMNS}
        row["area"] = area_names.get(plant.get("area_id") or "", plant.get("area_id"))
        profile = plant.get("profile") or {}
        for column, key in PROFILE_COLUMNS.items():
            value = profile.get(key)
            row[column] = ("yes" if value else "no") if isinstance(value, bool) else value
        writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return out.getvalue()


def _choice(key: str, value: str) -> str:
    slug = value.strip().lower().replace("-", "_").replace(" ", "_").replace(",", "")
    slug = _ALIASES.get(slug, slug)
    if slug not in _CHOICES[key]:
        raise vol.Invalid(f"{key} must be one of {', '.join(_CHOICES[key])}")
    return slug


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def _row_to_plant(row: dict[str, str], areas: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """Turn a CSV row into plant data (validated) and warnings."""
    clean = {
        (key or "").strip().lower(): (value or "").strip()
        for key, value in row.items()
        if key is not None and isinstance(value, str)
    }
    data: dict[str, Any] = {}
    warnings: list[str] = []
    for key in CSV_COLUMNS:
        value = clean.get(key, "")
        if value == "" or key in PROFILE_COLUMNS:
            continue
        if key == "area":
            if (area_id := areas.get(value.lower())) is None:
                warnings.append(f"area {value} not found, imported without an area")
            else:
                data["area_id"] = area_id
        elif key in _CHOICES:
            data[key] = _choice(key, value)
        elif key == "pot_diameter_cm":
            data[key] = _number(value)
        elif key == "last_watered":
            if dt_util.parse_date(value) is None and dt_util.parse_datetime(value) is None:
                raise vol.Invalid(f"last_watered {value} is not a date")
            data[key] = value
        else:
            data[key] = value

    profile: dict[str, Any] = {}
    for column, key in PROFILE_COLUMNS.items():
        if (value := clean.get(column, "")) == "":
            continue
        if key in _BOOL_PROFILE:
            if value.lower() not in (*_TRUE, *_FALSE):
                raise vol.Invalid(f"{column} must be yes or no")
            profile[key] = value.lower() in _TRUE
        elif key == P_LIGHT_PREFERENCE:
            profile[key] = _choice(key, value)
        elif key in _TEXT_PROFILE:
            profile[key] = value
        else:
            profile[key] = _number(value)
    if profile:
        data["profile"] = profile
    if not data.get("species") and P_BASE_INTERVAL not in profile:
        raise vol.Invalid("needs a species or a base_interval_days")
    return normalize_plant(PLANT_CREATE_SCHEMA(data)), warnings


def parse_plants_csv(
    text: str, areas: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse CSV text into plant data, row errors (skipped) and warnings.

    ``areas`` maps lower-case area names and ids to area ids.
    """
    text = text.lstrip("﻿")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    plants, errors, warnings = [], [], []
    for index, row in enumerate(reader, start=2):  # row 1 is the header
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue
        name = next((v for k, v in row.items() if (k or "").strip().lower() == "name"), "")
        name = (name or "").strip()
        try:
            plant, row_warnings = _row_to_plant(row, areas)
        except (vol.Invalid, ValueError) as err:
            errors.append({"row": index, "name": name, "error": str(err)})
            continue
        plants.append(plant)
        warnings.extend({"row": index, "name": name, "error": w} for w in row_warnings)
    return plants, errors, warnings
