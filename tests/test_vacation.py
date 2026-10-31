"""Tests for vacation planning."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.persistent_notification import _async_get_or_create_notifications
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.plant_manager import care, vacation
from custom_components.plant_manager.const import DOMAIN

from .conftest import entity_state

NOW = datetime(2026, 7, 1, 10, tzinfo=UTC)


def _plant(plant_id: str, base: float, dryness: float, **fields: Any) -> dict[str, Any]:
    return {
        "id": plant_id,
        "name": plant_id.title(),
        "profile": {"base_interval_days": base, "winter_dormancy": False},
        "dryness": dryness,
        "created_at": NOW.isoformat(),
        **fields,
    }


def _plan(plants: list[dict[str, Any]], days_ahead: int, nights: int) -> dict[str, Any]:
    # At the equator there are no seasons: every interval is base * 0.9 * the other factors.
    statuses = {p["id"]: care.status(p, care.Readings(), NOW, 1.0) for p in plants}
    start = NOW.date() + timedelta(days=days_ahead)
    leave, back = vacation.trip_times(start, start + timedelta(days=nights), UTC)
    return vacation.plan(plants, statuses, leave, back, NOW, 0.0)


def _entry(trip: dict[str, Any], plant_id: str) -> dict[str, Any]:
    return next(e for e in trip["plants"] if e["plant_id"] == plant_id)


def test_plan_before_leaving() -> None:
    """Plants that last need nothing, the others are watered or get the sitter."""
    trip = _plan(
        [
            _plant("cactus", 30, 0.1),
            _plant("monstera", 14, 0.5),
            _plant("fern", 5, 0.5, light="bright_indirect"),
        ],
        days_ahead=1,
        nights=10,
    )
    assert trip["days"] == 10.4
    assert not trip["active"]

    cactus = _entry(trip, "cactus")
    assert (cactus["risk"], cactus["prepare"], cactus["visits"]) == ("ok", False, [])
    monstera = _entry(trip, "monstera")
    assert (monstera["risk"], monstera["prepare"]) == ("ok", True)
    assert monstera["back_dryness"] < 1
    fern = _entry(trip, "fern")
    assert (fern["risk"], fern["prepare"]) == ("sitter", True)
    assert fern["tips"] == ["shade"]
    assert 2 <= len(fern["visits"]) <= 3
    assert fern["back_dryness"] < 1
    assert set(trip["prepare"]) == {"monstera", "fern"}
    assert [v["plant_ids"] for v in trip["visits"]] == [["fern"]] * len(fern["visits"])
    # The plants that need help come first.
    assert trip["plants"][0]["plant_id"] == "fern"


def test_plan_measures_and_recent_watering() -> None:
    """Out of the sun is enough for a week; a freshly watered plant isn't watered again."""
    trip = _plan(
        [_plant("ficus", 10, 0.5, light="direct"), _plant("calathea", 7, 0.05)],
        days_ahead=1,
        nights=7,
    )
    ficus = _entry(trip, "ficus")
    assert (ficus["risk"], ficus["tips"], ficus["visits"]) == ("measures", ["shade"], [])
    assert ficus["lasts_with_measures_days"] > trip["days"] > ficus["lasts_days"]
    calathea = _entry(trip, "calathea")
    assert not calathea["prepare"]
    assert calathea["risk"] == "sitter"


def test_shared_visits() -> None:
    """The sitter waters everything that is dry enough on the same visit."""
    plants = [_plant("basil", 3, 0.0), _plant("mint", 3.3, 0.2)]
    trip = _plan(plants, days_ahead=0, nights=14)
    together = len(trip["visits"])
    alone = sum(len(_plan([p], days_ahead=0, nights=14)["visits"]) for p in plants)
    assert together < alone
    assert all(e["back_dryness"] < 1 for e in trip["plants"])


def test_plan_text() -> None:
    """The plan for the sitter lists the days and plants."""
    trip = _plan([_plant("fern", 5, 0.5)], days_ahead=1, nights=10)
    text = vacation.plan_text(
        {"sitter": "Anna", "notes": "Key is under the mat"}, trip, {"fern": "Fern (Bathroom)"}
    )
    assert "Thank you, Anna!" in text
    assert "Fern (Bathroom)" in text
    assert text.endswith("Key is under the mat")


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_vacation_flow(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, entry: MockConfigEntry, ws
) -> None:
    """Plan, start, remind the sitter, and come back early."""
    freezer.move_to(dt_util.start_of_local_day() + timedelta(hours=9, minutes=30))
    sitter = async_mock_service(hass, "notify", "anna")
    today = dt_util.now().date()
    fern = await ws.cmd(
        "plants/create",
        plant={"name": "Fern", "species": "Nephrolepis exaltata", "light": "bright_indirect",
               "last_watered": today.isoformat()},
    )  # fmt: skip
    cactus = await ws.cmd(
        "plants/create",
        plant={"name": "Cactus", "species": "Cactaceae", "last_watered": today.isoformat()},
    )
    assert entity_state(hass, f"{entry.entry_id}_vacation", "binary_sensor").state == "off"

    start, end = today + timedelta(days=2), today + timedelta(days=16)
    preview = await ws.cmd(
        "vacation/preview", start_date=start.isoformat(), end_date=end.isoformat()
    )
    assert preview["vacation"] is None
    assert preview["plan"]["visits"]
    assert (await ws.cmd("vacation/get"))["plan"] is None

    error = await ws.error(
        "vacation/set",
        vacation={"start_date": end.isoformat(), "end_date": start.isoformat()},
    )
    assert "after the day you leave" in error["message"]
    error = await ws.error(
        "vacation/set",
        vacation={"start_date": start.isoformat(), "end_date": end.isoformat(),
                  "sitter_notify": "notify.nobody"},
    )  # fmt: skip
    assert "does not exist" in error["message"]

    result = await ws.cmd(
        "vacation/set",
        vacation={"start_date": start.isoformat(), "end_date": end.isoformat(), "sitter": "Anna",
                  "sitter_notify": "notify.anna", "notes": "Watering can on the balcony"},
    )  # fmt: skip
    plan = result["plan"]
    assert result["vacation"]["sitter"] == "Anna"
    assert fern["id"] in plan["prepare"]
    entries = {e["plant_id"]: e for e in plan["plants"]}
    assert entries[fern["id"]]["risk"] == "sitter"
    assert entries[cactus["id"]]["risk"] == "ok"
    assert "Watering can on the balcony" in result["text"]
    attributes = entity_state(hass, f"{entry.entry_id}_vacation", "binary_sensor").attributes
    assert attributes["planned"] is True
    assert attributes["next_visit"] == plan["visits"][0]["date"]

    # The schedule shows the sitter's visits instead of waterings while away.
    schedule = await ws.cmd("schedule", days=28)
    leave, back = (datetime.fromisoformat(plan[key]) for key in ("leave", "back"))
    at = {id(e): datetime.fromisoformat(e["at"]) for e in schedule}
    away = [e for e in schedule if e["kind"] != "vacation" and leave <= at[id(e)] < back]
    assert away and {e["kind"] for e in away} <= {"sitter", "fertilize"}
    assert any(e["kind"] == "prepare" and e["plant_id"] == fern["id"] for e in schedule)
    assert sum(e["kind"] == "vacation" for e in schedule) == 1
    assert any(e["kind"] == "water" and at[id(e)] >= back for e in schedule)

    # The checklist shows up before leaving.
    notifications = _async_get_or_create_notifications(hass)
    assert f"{DOMAIN}_vacation" in notifications
    assert "Fern" in notifications[f"{DOMAIN}_vacation"]["message"]

    await ws.cmd("vacation/send_plan")
    await hass.async_block_till_done()
    assert "Fern" in sitter[-1].data["message"]

    # Leaving: the vacation starts, and the sitter is reminded on visit days.
    events = []
    hass.bus.async_listen(f"{DOMAIN}_vacation_started", events.append)
    hass.bus.async_listen(f"{DOMAIN}_vacation_ended", events.append)
    await _tick(hass, freezer, timedelta(days=2))
    assert entity_state(hass, f"{entry.entry_id}_vacation", "binary_sensor").state == "on"
    assert [e.event_type for e in events] == [f"{DOMAIN}_vacation_started"]
    assert f"{DOMAIN}_vacation" not in notifications

    first_visit = date.fromisoformat(plan["visits"][0]["date"])
    sent = len(sitter)
    await _tick(hass, freezer, first_visit - dt_util.now().date())
    await hass.services.async_call(DOMAIN, "send_reminder", {}, blocking=True)
    assert len(sitter) > sent
    assert sitter[-1].data["message"].startswith("🪴 Please water today: Fern")

    # Back early.
    await hass.services.async_call(DOMAIN, "end_vacation", {}, blocking=True)
    assert entity_state(hass, f"{entry.entry_id}_vacation", "binary_sensor").state == "off"
    assert events[-1].event_type == f"{DOMAIN}_vacation_ended"
    assert entry.runtime_data.vacation is None  # the websocket timed out over the days
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "end_vacation", {}, blocking=True)


async def test_set_vacation_action(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """The action plans a vacation; a planned one that is cancelled is removed."""
    today = dt_util.now().date()
    await hass.services.async_call(
        DOMAIN,
        "set_vacation",
        {"start_date": today + timedelta(days=5), "end_date": today + timedelta(days=9)},
        blocking=True,
    )
    result = await ws.cmd("vacation/get")
    assert result["vacation"]["start_date"] == (today + timedelta(days=5)).isoformat()
    assert result["plan"]["days"] == 4.4
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "set_vacation", {"start_date": today, "end_date": today}, blocking=True
        )
    await ws.cmd("vacation/end")
    assert (await ws.cmd("vacation/get"))["vacation"] is None
