"""Watering model. Pure functions, no Home Assistant state.

Each plant has a *base interval*: days between waterings under reference
conditions (see ``species_db``). The effective interval is the base interval
scaled by independent factors for pot, light, climate, season and placement,
and by a learned per-plant correction from feedback.

Instead of fixing a due date when the plant is watered, the manager integrates
"dryness": every tick adds ``elapsed_days / current_interval``. A freshly
watered plant is at 0 and needs water at 1, so a heat wave or a dry, heated
room pulls the due date forward while it lasts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
import math
from statistics import mean
from typing import Any

from .const import (
    P_BASE_INTERVAL,
    P_FERTILIZE_INTERVAL,
    P_MAX_HUMIDITY,
    P_MAX_LUX,
    P_MAX_MOISTURE,
    P_MAX_TEMP,
    P_MIN_HUMIDITY,
    P_MIN_LUX,
    P_MIN_MOISTURE,
    P_MIN_TEMP,
    P_WINTER_DORMANCY,
    STATUS_NEEDS_WATER,
    STATUS_OK,
    STATUS_OVERDUE,
    STATUS_WATER_SOON,
)

REFERENCE_TEMP = 21.0
REFERENCE_HUMIDITY = 50.0
REFERENCE_POT_CM = 15.0

MIN_INTERVAL = 0.5
MAX_INTERVAL = 120.0
MAX_DRYNESS = 5.0
OVERDUE_AT = 1.25

EMA_TIME_CONSTANT_H = 24.0
MOISTURE_JUMP = 10.0  # % rise between ticks that counts as a watering
LEARN_MIN, LEARN_MAX = 0.4, 2.5
SNOOZE_DRYNESS = 0.8

# Dryness removed per hour of rain, for plants outside without cover.
RAIN_PER_HOUR = {"rainy": 0.3, "pouring": 1.0, "lightning-rainy": 0.5}

POT_MATERIAL_FACTOR = {
    "plastic": 1.0,
    "ceramic": 1.0,
    "terracotta": 0.8,  # porous walls evaporate water
    "fabric": 0.7,
    "self_watering": 2.0,
    "no_drainage": 1.15,
}

LIGHT_FACTOR = {
    "low": 1.35,
    "medium": 1.0,
    "bright_indirect": 0.85,
    "direct": 0.7,
}

PLACEMENT_FACTOR = {
    "indoor": 1.0,
    "outdoor_covered": 0.85,
    "outdoor": 0.75,  # wind and sun dry pots faster outside
}

PROBLEM_TEXT = {
    "watering_overdue": "watering is overdue",
    "temperature_low": "too cold",
    "temperature_high": "too hot",
    "humidity_low": "air too dry",
    "humidity_high": "air too humid",
    "soil_too_wet": "soil too wet",
    "light_low": "too dark",
    "light_high": "too much direct light",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def saturation_vapor_pressure(temp_c: float) -> float:
    """Tetens equation, kPa."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def vapor_pressure_deficit(temp_c: float, humidity: float) -> float:
    """Vapour pressure deficit in kPa; drives evaporation and transpiration."""
    return saturation_vapor_pressure(temp_c) * (1 - _clamp(humidity, 0, 100) / 100)


REFERENCE_VPD = vapor_pressure_deficit(REFERENCE_TEMP, REFERENCE_HUMIDITY)


def pot_factor(diameter_cm: float | None) -> float:
    """Bigger pots hold more water per unit of evaporating surface."""
    if not diameter_cm or diameter_cm <= 0:
        return 1.0
    return _clamp((diameter_cm / REFERENCE_POT_CM) ** 0.6, 0.45, 2.5)


def climate_factor(temp_c: float | None, humidity: float | None) -> float:
    """Scale by how much drier or wetter the air is than the reference climate."""
    if temp_c is None and humidity is None:
        return 1.0
    temp = REFERENCE_TEMP if temp_c is None else temp_c
    hum = REFERENCE_HUMIDITY if humidity is None else humidity
    vpd = max(vapor_pressure_deficit(temp, hum), 0.05)
    factor = (REFERENCE_VPD / vpd) ** 0.5
    # Near freezing plants barely take up water regardless of VPD.
    if temp < 10:
        factor *= 1 + (10 - max(temp, 0)) * 0.08
    return _clamp(factor, 0.5, 2.5)


def growth_level(now: datetime, latitude: float) -> float:
    """1.0 at the height of summer, down to 0.0 in mid-winter.

    The amplitude shrinks towards the equator, where there are no real seasons.
    """
    amplitude = _clamp((abs(latitude) - 10) / 25, 0.0, 1.0)
    day = now.timetuple().tm_yday
    peak = 196 if latitude >= 0 else 15  # mid July / mid January
    seasonal = 0.5 + 0.5 * math.cos(2 * math.pi * (day - peak) / 365.25)
    return 1 - amplitude * (1 - seasonal)


def season_factor(growth: float, winter_dormancy: bool) -> float:
    """Plants drink more in summer; dormant plants much less in winter."""
    winter_penalty = 0.7 if winter_dormancy else 0.35
    return 0.9 + (1 - growth) * winter_penalty


def is_dormant(growth: float, winter_dormancy: bool) -> bool:
    """Whether the plant is in its winter rest (no fertilizing)."""
    return winter_dormancy and growth < 0.25


def compute_interval(
    plant: dict[str, Any],
    *,
    temperature: float | None,
    humidity: float | None,
    growth: float,
) -> tuple[float, dict[str, float]]:
    """Return the current watering interval in days and the factors behind it."""
    profile = plant.get("profile") or {}
    factors = {
        "pot_size": pot_factor(plant.get("pot_diameter_cm")),
        "pot_material": POT_MATERIAL_FACTOR.get(plant.get("pot_material") or "plastic", 1.0),
        "light": LIGHT_FACTOR.get(plant.get("light") or "medium", 1.0),
        "climate": climate_factor(temperature, humidity),
        "season": season_factor(growth, bool(profile.get(P_WINTER_DORMANCY, True))),
        "placement": PLACEMENT_FACTOR.get(plant.get("placement") or "indoor", 1.0),
        "learned": plant.get("learned_factor") or 1.0,
    }
    interval = float(profile.get(P_BASE_INTERVAL) or 7.0)
    for value in factors.values():
        interval *= value
    rounded = {key: round(value, 3) for key, value in factors.items()}
    return _clamp(interval, MIN_INTERVAL, MAX_INTERVAL), rounded


@dataclass(slots=True)
class Readings:
    """Sensor values for one plant at one tick (temperatures in °C)."""

    temperature: float | None = None
    humidity: float | None = None
    moisture: float | None = None
    lux: float | None = None
    weather: str | None = None
    local_day: str = ""


def _ema(previous: float | None, value: float | None, alpha: float) -> float | None:
    if value is None:
        return previous
    if previous is None:
        return value
    return previous + alpha * (value - previous)


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def advance(
    plant: dict[str, Any], readings: Readings, now: datetime, growth: float
) -> tuple[dict[str, Any], bool]:
    """Integrate the plant's state up to ``now``.

    Returns the new model state (the plant's ``dryness``, ``last_tick``, moving
    averages and daily light) and whether a soil moisture jump means the plant
    was just watered.
    """
    profile = plant.get("profile") or {}
    last_tick = _parse(plant.get("last_tick"))
    hours = max(0.0, (now - last_tick).total_seconds() / 3600) if last_tick else 0.0
    alpha = 1 - math.exp(-hours / EMA_TIME_CONSTANT_H)
    temp_ema = _ema(plant.get("temp_ema"), readings.temperature, alpha)
    humidity_ema = _ema(plant.get("humidity_ema"), readings.humidity, alpha)
    interval, _ = compute_interval(
        plant, temperature=temp_ema, humidity=humidity_ema, growth=growth
    )

    dryness = plant.get("dryness")
    if dryness is None or last_tick is None:
        if last_watered := _parse(plant.get("last_watered")):
            dryness = (now - last_watered).total_seconds() / 86400 / interval
        else:
            dryness = 0.5  # unknown: assume half-way
    else:
        dryness += hours / 24 / interval
    if plant.get("placement") == "outdoor" and readings.weather in RAIN_PER_HOUR:
        dryness = max(0.0, dryness - RAIN_PER_HOUR[readings.weather] * hours)

    watered = False
    if readings.moisture is not None:
        previous = plant.get("last_moisture")
        watered = previous is not None and readings.moisture - previous >= MOISTURE_JUMP
        # A soil moisture sensor overrides the estimate.
        low = float(profile.get(P_MIN_MOISTURE, 20))
        high = float(profile.get(P_MAX_MOISTURE, 60))
        if high > low:
            dryness = (high - readings.moisture) / (high - low)

    lux_day = plant.get("lux_day")
    lux_today = plant.get("lux_max_today")
    lux_yesterday = plant.get("lux_max_yesterday")
    if readings.local_day and lux_day != readings.local_day:
        if lux_day is not None:
            lux_yesterday = lux_today
        lux_day, lux_today = readings.local_day, None
    if readings.lux is not None:
        lux_today = max(readings.lux, lux_today or 0.0)

    state = {
        "dryness": _clamp(dryness, 0.0, MAX_DRYNESS),
        "last_tick": now.isoformat(),
        "temp_ema": temp_ema,
        "humidity_ema": humidity_ema,
        "last_moisture": (
            readings.moisture if readings.moisture is not None else plant.get("last_moisture")
        ),
        "lux_day": lux_day,
        "lux_max_today": lux_today,
        "lux_max_yesterday": lux_yesterday,
    }
    return state, watered


def problems(plant: dict[str, Any], readings: Readings, overdue: bool) -> list[str]:
    """Environment problems, as codes (see ``PROBLEM_TEXT``)."""
    profile = plant.get("profile") or {}
    found = ["watering_overdue"] if overdue else []
    if (temp := readings.temperature) is not None:
        if temp < float(profile.get(P_MIN_TEMP, -100)):
            found.append("temperature_low")
        elif temp > float(profile.get(P_MAX_TEMP, 100)):
            found.append("temperature_high")
    if (humidity := readings.humidity) is not None:
        if humidity < float(profile.get(P_MIN_HUMIDITY, 0)):
            found.append("humidity_low")
        elif humidity > float(profile.get(P_MAX_HUMIDITY, 100)):
            found.append("humidity_high")
    if readings.moisture is not None and readings.moisture > float(
        profile.get(P_MAX_MOISTURE, 100)
    ):
        found.append("soil_too_wet")
    if (lux := plant.get("lux_max_yesterday")) is not None:
        if lux < float(profile.get(P_MIN_LUX, 0)):
            found.append("light_low")
        elif lux > float(profile.get(P_MAX_LUX, 1e9)):
            found.append("light_high")
    return found


def status(
    plant: dict[str, Any], readings: Readings, now: datetime, growth: float
) -> dict[str, Any]:
    """Everything the panel and the entities show about a plant's care."""
    profile = plant.get("profile") or {}
    interval, factors = compute_interval(
        plant, temperature=plant.get("temp_ema"), humidity=plant.get("humidity_ema"), growth=growth
    )
    dryness = plant.get("dryness") or 0.0
    days_until = max(0.0, (1 - dryness) * interval)
    if dryness >= OVERDUE_AT:
        state = STATUS_OVERDUE
    elif dryness >= 1:
        state = STATUS_NEEDS_WATER
    elif days_until <= 1:
        state = STATUS_WATER_SOON
    else:
        state = STATUS_OK

    fertilize_days = float(profile.get(P_FERTILIZE_INTERVAL) or 0)
    paused = is_dormant(growth, bool(profile.get(P_WINTER_DORMANCY, True)))
    next_fertilize = None
    if fertilize_days > 0:
        base = _parse(plant.get("last_fertilized")) or _parse(plant["created_at"])
        next_fertilize = base + timedelta(days=fertilize_days)

    waterings = [_parse(at) for at in plant.get("watering_dates") or []]
    gaps = [(b - a).total_seconds() / 86400 for a, b in pairwise(waterings)]

    return {
        "status": state,
        "needs_water": state in (STATUS_NEEDS_WATER, STATUS_OVERDUE),
        "interval_days": round(interval, 2),
        "factors": factors,
        "dryness": round(dryness, 3),
        "water_reserve": round(max(0.0, 1 - dryness) * 100, 1),
        "days_until_watering": round(days_until, 2),
        "next_watering": (now + timedelta(days=days_until)).isoformat(),
        "average_interval_days": round(mean(gaps[-8:]), 1) if gaps else None,
        "next_fertilization": next_fertilize.isoformat() if next_fertilize else None,
        "fertilizing_paused": paused,
        "fertilize_due": bool(next_fertilize and not paused and next_fertilize <= now),
        "problems": problems(plant, readings, state == STATUS_OVERDUE),
        "temperature": readings.temperature,
        "humidity": readings.humidity,
        "moisture": readings.moisture,
        "lux_max_yesterday": plant.get("lux_max_yesterday"),
        "learned_factor": round(plant.get("learned_factor") or 1.0, 3),
    }


def learned_after(factor: float, feedback: str | None) -> float:
    """Adjust the learned correction from watering feedback."""
    if feedback == "too_dry":
        factor *= 0.85
    elif feedback == "too_wet":
        factor *= 1.15
    return _clamp(factor, LEARN_MIN, LEARN_MAX)


def snoozed(factor: float, dryness: float) -> tuple[float, float]:
    """Soil still moist: a longer interval, and push the current reminder back."""
    return _clamp(factor * 1.1, LEARN_MIN, LEARN_MAX), min(dryness, SNOOZE_DRYNESS)


def forecast(status_: dict[str, Any], start: datetime, end: datetime) -> list[datetime]:
    """Projected watering dates, assuming current conditions persist."""
    current = datetime.fromisoformat(status_["next_watering"])
    step = timedelta(days=max(status_["interval_days"], 0.5))
    dates: list[datetime] = []
    while current < end and len(dates) < 100:
        if current >= start:
            dates.append(current)
        current += step
    return dates
