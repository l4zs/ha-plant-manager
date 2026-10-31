"""Tests for notifications to phones, per Home Assistant user."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.plant_manager.const import DOMAIN


def _phone(hass: HomeAssistant, name: str, user_id: str) -> list:
    """A phone with the Home Assistant app: a mobile_app entry and its notify action."""
    MockConfigEntry(
        domain="mobile_app", data={"device_name": name, "user_id": user_id}
    ).add_to_hass(hass)
    return async_mock_service(hass, "notify", f"mobile_app_{name.lower().replace(' ', '_')}")


async def test_per_user_notifications(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, entry: MockConfigEntry, ws, hass_admin_user
) -> None:
    """Each user picks phones, a time for the summary, and whether to get problems."""
    freezer.move_to(dt_util.start_of_local_day() + timedelta(hours=6))
    mine = _phone(hass, "Pixel 8", hass_admin_user.id)
    _phone(hass, "Tablet", "someone-else")

    data = await ws.cmd("notifications/get")
    assert [(p["name"], p["mine"]) for p in data["phones"]] == [
        ("Pixel 8", True),
        ("Tablet", False),
    ]
    assert data["settings"] == {"targets": [], "daily": True, "time": "09:00", "problems": True}

    error = await ws.error(
        "notifications/set", targets=["notify.nope"], daily=True, time="07:30", problems=True
    )
    assert "does not exist" in error["message"]
    settings = await ws.cmd(
        "notifications/set",
        targets=["notify.mobile_app_pixel_8"],
        daily=True,
        time="07:30",
        problems=False,
    )
    assert settings["time"] == "07:30"
    assert (await ws.cmd("notifications/test"))["sent"] == 1
    assert "work on this phone" in mine[-1].data["message"]

    # Too cold, but this user doesn't want problems right away.
    hass.states.async_set("sensor.temp", "5", {"unit_of_measurement": "°C"})
    long_ago = (dt_util.now().date() - timedelta(days=30)).isoformat()
    await ws.cmd(
        "plants/create",
        plant={"name": "Monty", "species": "Monstera deliciosa",
               "temperature_sensor": "sensor.temp", "last_watered": long_ago},
    )  # fmt: skip
    await hass.async_block_till_done()
    assert len(mine) == 1

    # The summary comes at the user's own time, not at the integration's 09:00.
    tomorrow = dt_util.start_of_local_day() + timedelta(days=1)
    for at in (timedelta(hours=7, minutes=29, seconds=59), timedelta(hours=7, minutes=30)):
        freezer.move_to(tomorrow + at)
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert len(mine) == 2
    assert mine[-1].data["message"].startswith("💧 Water: Monty")

    # Without phones, the settings are forgotten.
    await ws.cmd("notifications/set", targets=[], daily=True, time="07:30", problems=True)
    assert entry.runtime_data.notify_users == {}


async def test_problems_and_no_duplicates(
    hass: HomeAssistant, entry: MockConfigEntry, ws, hass_admin_user
) -> None:
    """A phone picked by a user follows their settings, also if it is the global action."""
    mine = _phone(hass, "Pixel 8", hass_admin_user.id)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "notify_service": "notify.mobile_app_pixel_8"}
    )
    await hass.async_block_till_done()
    await ws.cmd(
        "notifications/set",
        targets=["notify.mobile_app_pixel_8"],
        daily=True,
        time="07:30",
        problems=True,
    )
    hass.states.async_set("sensor.temp", "5", {"unit_of_measurement": "°C"})
    await ws.cmd(
        "plants/create",
        plant={
            "name": "Monty",
            "species": "Monstera deliciosa",
            "temperature_sensor": "sensor.temp",
        },
    )
    await hass.async_block_till_done()
    assert [call.data["message"] for call in mine] == ["Monty: too cold"]

    await hass.services.async_call(DOMAIN, "send_reminder", {}, blocking=True)
    assert len(mine) == 2


async def test_phone_dropdown_in_options(
    hass: HomeAssistant, entry: MockConfigEntry, hass_admin_user
) -> None:
    """The reminders options offer the phones by name."""
    _phone(hass, "Pixel 8", hass_admin_user.id)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "reminders"}
    )
    selector = result["data_schema"].schema["notify_service"].config
    assert {"value": "notify.mobile_app_pixel_8", "label": "📱 Pixel 8"} in selector["options"]
    assert selector["custom_value"] is True
