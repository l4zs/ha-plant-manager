"""Tests for the watering model and species database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.plant_manager import alerts, care, species_db

NOW = datetime(2026, 7, 15, 12, tzinfo=UTC)


def _plant(**overrides):
    return {
        "id": "p1",
        "name": "Monty",
        "pot_diameter_cm": 15,
        "pot_material": "plastic",
        "light": "medium",
        "placement": "indoor",
        "learned_factor": 1.0,
        "profile": {
            "base_interval_days": 7,
            "winter_dormancy": True,
            "fertilize_interval_days": 14,
        },
        "created_at": (NOW - timedelta(days=30)).isoformat(),
        **overrides,
    }


def test_reference_conditions_keep_base_interval() -> None:
    interval, factors = care.compute_interval(_plant(), temperature=21, humidity=50, growth=1.0)
    # Only the summer season factor (0.9) applies.
    assert round(interval, 2) == 6.3
    assert factors["season"] == 0.9


def test_pot_climate_and_light_factors() -> None:
    assert care.pot_factor(30) > care.pot_factor(15) > care.pot_factor(8)
    assert care.climate_factor(21, 80) > 1 > care.climate_factor(28, 30)
    small, _ = care.compute_interval(_plant(), temperature=None, humidity=None, growth=1)
    large, _ = care.compute_interval(
        _plant(pot_diameter_cm=30), temperature=None, humidity=None, growth=1
    )
    assert large > small
    assert care.POT_MATERIAL_FACTOR["terracotta"] < 1
    assert care.LIGHT_FACTOR["direct"] < care.LIGHT_FACTOR["low"]


def test_seasons_by_hemisphere() -> None:
    january = datetime(2026, 1, 15)
    july = datetime(2026, 7, 15)
    assert care.growth_level(july, 52) > 0.95
    assert care.growth_level(january, 52) < 0.05
    assert care.growth_level(january, -34) > 0.95
    assert care.growth_level(january, 1) == 1  # no seasons at the equator
    assert care.season_factor(0, True) > care.season_factor(0, False) > care.season_factor(1, True)
    assert care.is_dormant(0.1, True)
    assert not care.is_dormant(0.1, False)


def test_dryness_integrates_over_time() -> None:
    plant = _plant(last_watered=(NOW - timedelta(days=3)).isoformat())
    readings = care.Readings(temperature=21, humidity=50, local_day="2026-07-15")
    state, watered = care.advance(plant, readings, NOW, growth=1.0)
    assert not watered
    assert round(state["dryness"], 2) == round(3 / 6.3, 2)

    # Two days of hot, dry air dry the soil faster than two normal days.
    later = NOW + timedelta(days=2)
    normal, _ = care.advance({**plant, **state}, readings, later, growth=1.0)
    hot = care.Readings(temperature=30, humidity=25, local_day="2026-07-17")
    dry, _ = care.advance({**plant, **state}, hot, later, growth=1.0)
    assert dry["dryness"] > normal["dryness"]

    status = care.status({**plant, **normal}, readings, later, growth=1.0)
    assert status["status"] == "ok"
    assert 0 < status["water_reserve"] < 100


def test_status_thresholds_and_problems() -> None:
    plant = _plant(
        dryness=1.3,
        profile={"base_interval_days": 7, "min_temp": 16, "max_temp": 30, "max_soil_moisture": 60},
    )
    readings = care.Readings(temperature=12, moisture=70)
    status = care.status(plant, readings, NOW, growth=1.0)
    assert status["status"] == "overdue"
    assert status["needs_water"]
    assert status["problems"] == ["watering_overdue", "temperature_low", "soil_too_wet"]
    assert care.status(_plant(dryness=1.0), readings, NOW, 1.0)["status"] == "needs_water"
    assert care.status(_plant(dryness=0.9), readings, NOW, 1.0)["status"] == "water_soon"


def test_moisture_sensor_overrides_and_detects_watering() -> None:
    plant = _plant(
        dryness=0.2,
        last_tick=NOW.isoformat(),
        last_moisture=22.0,
        profile={"base_interval_days": 7, "min_soil_moisture": 20, "max_soil_moisture": 60},
    )
    state, watered = care.advance(plant, care.Readings(moisture=22), NOW, 1.0)
    assert round(state["dryness"], 2) == 0.95
    assert not watered
    state, watered = care.advance({**plant, **state}, care.Readings(moisture=55), NOW, 1.0)
    assert watered
    assert state["dryness"] < 0.2


def test_rain_waters_outdoor_plants() -> None:
    plant = _plant(
        placement="outdoor", dryness=0.9, last_tick=(NOW - timedelta(hours=2)).isoformat()
    )
    state, _ = care.advance(plant, care.Readings(weather="pouring"), NOW, 1.0)
    assert state["dryness"] == 0
    covered = {**plant, "placement": "outdoor_covered"}
    state, _ = care.advance(covered, care.Readings(weather="pouring"), NOW, 1.0)
    assert state["dryness"] > 0.9


def test_learning() -> None:
    assert care.learned_after(1.0, "too_dry") == 0.85
    assert care.learned_after(1.0, "too_wet") == 1.15
    assert care.learned_after(1.0, None) == 1.0
    assert care.learned_after(0.41, "too_dry") == care.LEARN_MIN
    factor, dryness = care.snoozed(1.0, 1.1)
    assert factor == 1.1
    assert dryness == care.SNOOZE_DRYNESS


def test_fertilizing_pauses_in_winter() -> None:
    status = care.status(_plant(dryness=0), care.Readings(), NOW, growth=1.0)
    assert status["fertilize_due"]
    winter = care.status(_plant(dryness=0), care.Readings(), NOW, growth=0.0)
    assert winter["fertilizing_paused"]
    assert not winter["fertilize_due"]


def test_forecast() -> None:
    status = care.status(_plant(dryness=0.5), care.Readings(), NOW, growth=1.0)
    dates = care.forecast(status, NOW, NOW + timedelta(days=14))
    assert len(dates) == 2  # in 3.15 and 9.45 days
    assert dates[1] - dates[0] == timedelta(days=status["interval_days"])


def test_alerts() -> None:
    plants = [_plant(), _plant(id="p2", name="Figgy")]
    cold = _plant(dryness=1.1, profile={"base_interval_days": 7, "min_temp": 15})
    statuses = {
        "p1": care.status(cold, care.Readings(temperature=10), NOW, 1.0),
        "p2": care.status(_plant(id="p2", dryness=0.1), care.Readings(), NOW, 1.0),
    }
    statuses["p1"]["fertilize_due"] = False
    found = {alert["key"]: alert for alert in alerts.compute_alerts(plants, statuses)}
    assert found["water_p1"]["message"] == "Monty needs water"
    assert found["problem_p1_temperature_low"]["message"] == "Monty: too cold"
    assert "fertilize_p2" in found
    assert alerts.summary_message(plants, statuses) == "💧 Water: Monty\n🌱 Fertilize: Figgy"


def test_species_lookup() -> None:
    assert species_db.lookup("Monstera deliciosa").common_name == "Swiss cheese plant"
    assert species_db.lookup("Sansevieria trifasciata").key == "dracaena trifasciata"
    assert species_db.lookup("Monstera deliciosa 'Thai Constellation'").key == "monstera deliciosa"
    assert species_db.lookup("Philodendron birkin").key == "philodendron"
    assert species_db.lookup("Mammillaria elongata", family="Cactaceae").key == "cactaceae"
    assert species_db.lookup("snake plant").key == "dracaena trifasciata"
    assert species_db.lookup("Unknownus plantus") is None
    profile = species_db.lookup("Aglaonema commutatum").profile
    assert profile["light_preference"] == "medium"
    assert profile["min_light_lux"] == 700.0
