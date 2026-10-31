"""Integration tests for Plant Manager."""

from __future__ import annotations

from datetime import timedelta

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.plant_manager.const import DOMAIN, PANEL_URL_PATH

from .conftest import JPEG, entity_state

MONSTERA = {
    "name": "Monty",
    "species": "Monstera deliciosa",
    "pot_diameter_cm": 15,
    "pot_material": "plastic",
    "light": "medium",
    "placement": "indoor",
    "temperature_sensor": "sensor.living_temp",
    "humidity_sensor": "sensor.living_hum",
}


def _climate(hass: HomeAssistant, temp: str = "21", humidity: str = "50") -> None:
    hass.states.async_set("sensor.living_temp", temp, {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.living_hum", humidity, {"unit_of_measurement": "%"})


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    # The schedule runs as a background task.
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_setup_and_unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The entry loads, registers the panel and hub sensors, and unloads."""
    assert entry.state is ConfigEntryState.LOADED
    assert PANEL_URL_PATH in hass.data["frontend_panels"]
    assert entity_state(hass, f"{entry.entry_id}_plants").state == "0"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert PANEL_URL_PATH not in hass.data["frontend_panels"]


async def test_create_plant_and_water(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, entry: MockConfigEntry, ws
) -> None:
    """A plant gets a profile, a device with entities, and a schedule."""
    _climate(hass)
    today = dt_util.now().date().isoformat()
    plant = await ws.cmd("plants/create", plant={**MONSTERA, "last_watered": today})
    assert plant["common_name"] == "Swiss cheese plant"
    assert plant["profile"]["base_interval_days"] == 7
    assert "built-in database (monstera deliciosa)" in plant["profile_sources"]
    assert plant["care"]["status"] in ("ok", "water_soon")
    assert "dryness" not in plant
    await hass.async_block_till_done()

    pid = plant["id"]
    assert entity_state(hass, f"{pid}_status").state in ("ok", "water_soon")
    assert 3 < float(entity_state(hass, f"{pid}_watering_interval").state) < 12
    assert entity_state(hass, f"{pid}_needs_water", "binary_sensor").state == "off"
    assert entity_state(hass, f"{entry.entry_id}_plants").state == "1"

    # Three weeks later it is overdue and on the to-do list.
    events = []
    hass.bus.async_listen(f"{DOMAIN}_watering_due", events.append)
    await _tick(hass, freezer, timedelta(days=21))
    assert entity_state(hass, f"{pid}_status").state == "overdue"
    assert entity_state(hass, f"{pid}_needs_water", "binary_sensor").state == "on"
    assert entity_state(hass, f"{entry.entry_id}_needs_water").state == "1"
    todo = entity_state(hass, f"{entry.entry_id}_care_tasks", "todo")
    assert todo.state == "1"  # water; fertilizing rests in November
    assert len(events) == 1
    alerts = await ws.cmd("alerts")
    assert [alert["kind"] for alert in alerts] == ["water"]

    # Watering from the panel resets it, and can be undone.
    result = await ws.cmd("plants/water", plant_id=pid)
    assert entity_state(hass, f"{pid}_status").state == "ok"
    assert float(entity_state(hass, f"{pid}_water_reserve").state) == 100
    assert (await ws.cmd("undo", undo_id=result["undo_id"]))["undone"]
    assert entity_state(hass, f"{pid}_status").state == "overdue"

    # The button and the to-do list log waterings too.
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_state(hass, f"{pid}_water", "button").entity_id},
        blocking=True,
    )
    assert entity_state(hass, f"{pid}_status").state == "ok"
    await _tick(hass, freezer, timedelta(days=21))
    todo_id = todo.entity_id
    items = await hass.services.async_call(
        "todo", "get_items", {"entity_id": todo_id}, blocking=True, return_response=True
    )
    water_item = next(i for i in items[todo_id]["items"] if i["summary"].startswith("💧"))
    await hass.services.async_call(
        "todo",
        "update_item",
        {"entity_id": todo_id, "item": water_item["uid"], "status": "completed"},
        blocking=True,
    )
    assert entity_state(hass, f"{pid}_needs_water", "binary_sensor").state == "off"

    # Feedback through the action tunes the interval.
    await hass.services.async_call(
        DOMAIN, "water", {"plant_id": pid, "feedback": "too_wet"}, blocking=True
    )
    detail = await ws.cmd("plants/get", plant_id=pid)
    assert detail["care"]["learned_factor"] == 1.15
    kinds = [event["kind"] for event in detail["events"]]
    assert kinds.count("water") == 4  # created, button, to-do, action

    # The calendar and schedule project the next waterings.
    schedule = await ws.cmd("schedule", days=30)
    assert len([e for e in schedule if e["kind"] == "water"]) >= 2
    calendar_id = entity_state(hass, f"{entry.entry_id}_care_calendar", "calendar").entity_id
    events = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": calendar_id, "duration": {"days": 30}},
        blocking=True,
        return_response=True,
    )
    assert len(events[calendar_id]["events"]) >= 2


async def test_dry_air_waters_sooner(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """Room sensors change the interval, in °F too."""
    hass.states.async_set("sensor.humid", "70", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.dry", "25", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.temp", "77", {"unit_of_measurement": "°F"})
    humid = await ws.cmd(
        "plants/create",
        plant={"name": "Humid", "species": "Epipremnum aureum",
               "temperature_sensor": "sensor.temp", "humidity_sensor": "sensor.humid"},
    )  # fmt: skip
    dry = await ws.cmd(
        "plants/create",
        plant={"name": "Dry", "species": "Epipremnum aureum",
               "temperature_sensor": "sensor.temp", "humidity_sensor": "sensor.dry"},
    )  # fmt: skip
    assert dry["care"]["interval_days"] < humid["care"]["interval_days"]
    assert round(dry["care"]["temperature"]) == 25


async def test_update_and_delete(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """Edits update the device; deleting removes it."""
    plant = await ws.cmd("plants/create", plant={"name": "Figgy", "species": "Ficus lyrata"})
    before = plant["care"]["interval_days"]
    updated = await ws.cmd(
        "plants/update",
        plant_id=plant["id"],
        changes={"name": "Fig", "pot_diameter_cm": 40, "pot_material": "terracotta"},
    )
    assert updated["care"]["interval_days"] > before * 0.8  # bigger pot, but terracotta
    registry = dr.async_get(hass)
    device = next(
        d
        for d in dr.async_entries_for_config_entry(registry, entry.entry_id)
        if (DOMAIN, plant["id"]) in d.identifiers
    )
    assert device.name == "Fig"

    error = await ws.error(
        "plants/update", plant_id=plant["id"], changes={"profile": {"min_temp": 30, "max_temp": 10}}
    )
    assert "max temp" in error["message"]

    await ws.cmd("plants/delete", plant_id=plant["id"])
    assert registry.async_get(device.id) is None
    assert (await ws.error("plants/get", plant_id=plant["id"]))["code"] == "not_found"


async def test_care_log(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """Fertilizing, snoozing and notes go into the care log."""
    plant = await ws.cmd("plants/create", plant={"name": "Peace", "species": "Spathiphyllum"})
    pid = plant["id"]
    await ws.cmd("plants/log", plant_id=pid, kind="fertilize")
    await ws.cmd("plants/log", plant_id=pid, kind="repot", notes="18 cm pot")
    await ws.cmd("plants/snooze", plant_id=pid)
    detail = await ws.cmd("plants/get", plant_id=pid)
    assert [e["kind"] for e in detail["events"]] == ["snooze", "repot", "fertilize"]
    assert detail["care"]["learned_factor"] == 1.1
    assert detail["last_fertilized"] is not None
    await ws.cmd("events/delete", event_id=detail["events"][0]["id"])
    detail = await ws.cmd("plants/get", plant_id=pid)
    assert detail["care"]["learned_factor"] == 1.0
    await hass.services.async_call(
        DOMAIN, "log_care", {"plant_id": pid, "kind": "mist"}, blocking=True
    )
    assert (await ws.cmd("plants/get", plant_id=pid))["events"][0]["kind"] == "mist"


async def test_photos(hass: HomeAssistant, entry: MockConfigEntry, ws, hass_client) -> None:
    """Upload, serve with a signed URL, and delete photos."""
    plant = await ws.cmd("plants/create", plant={"name": "Aloe", "species": "Aloe vera"})
    client = await hass_client()
    form = aiohttp.FormData()
    form.add_field("file", JPEG, filename="a.jpg", content_type="image/jpeg")
    response = await client.post(f"/api/{DOMAIN}/plants/{plant['id']}/photos", data=form)
    assert response.status == 200
    plant = await ws.cmd("plants/get", plant_id=plant["id"])
    url = plant["photos"][0]["url"]
    assert "authSig" in url
    response = await client.get(url)
    assert response.status == 200
    assert await response.read() == JPEG

    form = aiohttp.FormData()
    form.add_field("file", b"not an image", filename="a.txt")
    response = await client.post(f"/api/{DOMAIN}/plants/{plant['id']}/photos", data=form)
    assert response.status == 415

    await ws.cmd("photos/delete", photo_id=plant["photos"][0]["id"])
    assert (await ws.cmd("plants/get", plant_id=plant["id"]))["photos"] == []


async def test_config(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """The panel gets its vocabulary."""
    config = await ws.cmd("config")
    assert "terracotta" in config["pot_materials"]
    assert config["identification"] is False
    assert any(s["value"] == "Monstera deliciosa" for s in config["species"])
    resolved = await ws.cmd("profile/resolve", species="Unknownus plantus")
    assert resolved["sources"] == ["generic defaults"]
