"""Tests for the German texts and the language per user."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.plant_manager import i18n

COMPONENT = Path(__file__).parent.parent / "custom_components" / "plant_manager"


def _keys(data: dict, prefix: str = "") -> set[str]:
    keys = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        keys |= _keys(value, path) if isinstance(value, dict) else {path}
    return keys


def test_translation_files_match() -> None:
    """de.json has exactly the keys of strings.json, and en.json is strings.json."""
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
    german = json.loads((COMPONENT / "translations" / "de.json").read_text(encoding="utf-8"))
    assert english == strings
    assert _keys(german) == _keys(strings)


def test_texts() -> None:
    """Texts are looked up by their English version; unknown languages stay English."""
    assert i18n.language("de-CH") == "de"
    assert i18n.language("fr") == "en"
    assert i18n.tr("de", "{name} needs water", name="Monty") == "Monty braucht Wasser"
    assert i18n.tr("fr", "{name} needs water", name="Monty") == "Monty needs water"
    assert i18n.format_day(date(2026, 3, 7), "de") == "Sa. 7. März"
    assert i18n.format_day(date(2026, 3, 7), "en") == "Sat 7 Mar"
    # Errors are raised in English and translated with their values.
    assert i18n.translate_message("de", "Plant abc not found") == "Pflanze abc nicht gefunden"
    assert (
        i18n.translate_message("de", "A vacation can be at most 365 days long")
        == "Ein Urlaub darf höchstens 365 Tage dauern"
    )
    assert i18n.translate_message("de", "Something else") == "Something else"


async def test_panel_texts_in_german(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """The panel gets plants, problems, plans and errors in the user's language."""
    config = await ws.cmd("config", language="de")
    assert config["problems"]["temperature_low"] == "zu kalt"
    assert {"value": "Monstera deliciosa", "label": "Monstera (Monstera deliciosa)"} in config[
        "species"
    ]

    plant = await ws.cmd(
        "plants/create", language="de", plant={"name": "Monty", "species": "Monstera deliciosa"}
    )
    assert plant["common_name"] == "Monstera"
    assert plant["profile"]["notes"].startswith("Die oberen 3-5 cm")
    # A German common name finds the species too.
    resolved = await ws.cmd("profile/resolve", language="de", species="Bogenhanf")
    assert resolved["sources"] == ["built-in database (dracaena trifasciata)"]

    hass.states.async_set("sensor.temp", "5", {"unit_of_measurement": "°C"})
    await ws.cmd(
        "plants/update",
        plant_id=plant["id"],
        changes={"temperature_sensor": "sensor.temp"},
    )
    await hass.async_block_till_done()
    alerts = await ws.cmd("alerts", language="de")
    assert "Monty: zu kalt" in [alert["message"] for alert in alerts]

    start = dt_util.now().date() + timedelta(days=2)
    preview = await ws.cmd(
        "vacation/preview",
        language="de",
        start_date=start.isoformat(),
        end_date=(start + timedelta(days=30)).isoformat(),
    )
    assert preview["text"].startswith("🪴 Pflanzenpflege vom ")
    assert "Bitte an diesen Tagen gießen:" in preview["text"]

    error = await ws.error("vacation/end", language="de")
    assert error["message"] == "Es ist kein Urlaub geplant"
    error = await ws.error("vacation/end")
    assert error["message"] == "No vacation is planned"


async def test_notifications_in_the_users_language(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, entry: MockConfigEntry, ws, hass_admin_user
) -> None:
    """A user's phones get German, the integration's own notify action Home Assistant's."""
    freezer.move_to(dt_util.start_of_local_day() + timedelta(hours=6))
    MockConfigEntry(
        domain="mobile_app", data={"device_name": "Pixel 8", "user_id": hass_admin_user.id}
    ).add_to_hass(hass)
    mine = async_mock_service(hass, "notify", "mobile_app_pixel_8")
    shared = async_mock_service(hass, "notify", "family")
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "notify_service": "notify.family"}
    )
    await hass.async_block_till_done()
    await ws.cmd(
        "notifications/set",
        language="de",
        targets=["notify.mobile_app_pixel_8"],
        daily=True,
        time="07:30",
        problems=True,
    )
    await ws.cmd("notifications/test")
    assert mine[-1].data["message"].startswith("🌿 Benachrichtigungen von Plant Manager")

    long_ago = (dt_util.now().date() - timedelta(days=30)).isoformat()
    hass.states.async_set("sensor.temp", "5", {"unit_of_measurement": "°C"})
    await ws.cmd(
        "plants/create",
        plant={"name": "Monty", "species": "Monstera deliciosa",
               "temperature_sensor": "sensor.temp", "last_watered": long_ago},
    )  # fmt: skip
    await hass.async_block_till_done()
    assert mine[-1].data["message"] == "Monty: zu kalt"
    assert shared[-1].data["message"] == "Monty: too cold"

    tomorrow = dt_util.start_of_local_day() + timedelta(days=1)
    for at in (timedelta(hours=7, minutes=29, seconds=59), timedelta(hours=7, minutes=30)):
        freezer.move_to(tomorrow + at)
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert mine[-1].data["message"].startswith("💧 Gießen: Monty")


@pytest.mark.parametrize(("fixed", "profile"), [("de", "en"), ("en", "de")])
async def test_fixed_language_overrides_every_language(
    hass: HomeAssistant, entry: MockConfigEntry, ws, fixed: str, profile: str
) -> None:
    """With a language set, requests and background texts use it for everyone."""
    assert (await ws.cmd("language")) == {"fixed": None}
    hass.config.language = profile
    plant = {"name": "ZZ Plant", "species": "Zamioculcas zamiifolia", "common_name": "ZZ Plant"}
    names = {"en": "ZZ Plant", "de": "Glücksfeder"}
    created = await ws.cmd("plants/create", plant=plant, language=profile)
    assert created["display_name"] == names[profile]

    hass.config_entries.async_update_entry(entry, options={**entry.options, "language": fixed})
    await hass.async_block_till_done()
    manager = entry.runtime_data
    assert manager.language == fixed
    assert manager.ui_language(profile) == fixed
    assert manager._user_language({"language": profile}) == fixed
    assert (await ws.cmd("language")) == {"fixed": fixed}
    listed = await ws.cmd("plants/list", language=profile)
    assert listed[0]["display_name"] == names[fixed]


@pytest.mark.parametrize(
    ("system", "chosen", "title"),
    [
        ("de", "user", "Pflanzen"),
        ("en", "user", "Plants"),
        ("en", "de", "Pflanzen"),
        ("de", "en", "Plants"),
    ],
)
async def test_sidebar_title(
    hass: HomeAssistant, entry: MockConfigEntry, system: str, chosen: str, title: str
) -> None:
    """The set language decides the title, otherwise Home Assistant's language does."""
    hass.config.language = system
    hass.config_entries.async_update_entry(entry, options={**entry.options, "language": chosen})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data["frontend_panels"]["plant-manager"].sidebar_title == title
