"""Tests for import, export, backup and restore."""

from __future__ import annotations

import csv
import io
import os
import zipfile

import aiohttp
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_manager.const import DOMAIN
from custom_components.plant_manager.transfer import CSV_COLUMNS

from .conftest import JPEG, entity_state


async def _upload(client, kind: str, data: bytes, filename: str):
    form = aiohttp.FormData()
    form.add_field("file", data, filename=filename)
    return await client.post(f"/api/{DOMAIN}/upload/{kind}", data=form)


async def test_csv_round_trip(hass: HomeAssistant, entry: MockConfigEntry, ws, hass_client) -> None:
    """An export can be imported again, with areas, profiles and the last watering."""
    area = ar.async_get(hass).async_create("Living room")
    await ws.cmd(
        "plants/create",
        plant={"name": "Monty", "species": "Monstera deliciosa", "area_id": area.id,
               "light": "bright_indirect", "pot_diameter_cm": 21, "last_watered": "2026-10-01"},
    )  # fmt: skip
    exported = (await ws.cmd("export/csv"))["csv"]
    rows = list(csv.DictReader(io.StringIO(exported)))
    assert list(rows[0]) == CSV_COLUMNS
    assert rows[0]["area"] == "Living room"
    assert rows[0]["base_interval_days"] == "7"
    assert rows[0]["last_watered"].startswith("2026-10-01")

    client = await hass_client()
    response = await _upload(client, "csv", exported.encode(), "plants.csv")
    assert response.status == 200
    result = await response.json()
    assert result == {"created": 1, "errors": [], "warnings": []}
    plants = await ws.cmd("plants/list")
    assert len(plants) == 2
    for copy in plants:
        assert copy["area_id"] == area.id
        assert copy["pot_diameter_cm"] == 21
        assert copy["last_watered"].startswith("2026-10-01")


async def test_csv_import_spreadsheet(
    hass: HomeAssistant, entry: MockConfigEntry, ws, hass_client
) -> None:
    """Semicolons, labels instead of keys, partial profiles, and bad rows."""
    text = (
        "Name;Species;Area;Light;Pot_material;base_interval_days;toxic_to_pets\n"
        "Figgy;Ficus lyrata;Office;Direct sun;Clay;12;yes\n"
        "Mystery;;;;;;\n"
        "Bad;Monstera deliciosa;;very dark;;;\n"
        ";;;;;;\n"
        "Rubber;Ficus elastica;;bright indirect;;;\n"
    )
    client = await hass_client()
    result = await (await _upload(client, "csv", text.encode("utf-8-sig"), "p.csv")).json()
    assert result["created"] == 2
    assert [(e["row"], e["name"]) for e in result["errors"]] == [(3, "Mystery"), (4, "Bad")]
    assert "light must be one of" in result["errors"][1]["error"]
    assert [w["name"] for w in result["warnings"]] == ["Figgy"]

    plants = {p["name"]: p for p in await ws.cmd("plants/list")}
    figgy = plants["Figgy"]
    assert (figgy["light"], figgy["pot_material"], figgy["area_id"]) == (
        "direct",
        "terracotta",
        None,
    )
    # The given values win, the rest of the profile comes from the species.
    assert figgy["profile"]["base_interval_days"] == 12
    assert figgy["profile"]["toxic_to_pets"] is True
    assert "min_temp" in figgy["profile"]
    assert "CSV import" in figgy["profile_sources"]
    assert plants["Rubber"]["light"] == "bright_indirect"


async def test_json_export(hass: HomeAssistant, entry: MockConfigEntry, ws) -> None:
    """The JSON export has every table."""
    await ws.cmd("plants/create", plant={"name": "Fern", "species": "Nephrolepis exaltata"})
    data = await ws.cmd("export/json")
    assert data["schema"] == 2
    assert set(data) >= {"plants", "photos", "care_events", "vacations", "exported_at"}
    assert data["plants"][0]["profile"]["base_interval_days"] == 3


async def test_backup_and_restore(
    hass: HomeAssistant, entry: MockConfigEntry, ws, hass_client
) -> None:
    """A backup has the database and photos; restoring brings deleted plants back."""
    plant = await ws.cmd("plants/create", plant={"name": "Fern", "species": "Nephrolepis exaltata"})
    client = await hass_client()
    form = aiohttp.FormData()
    form.add_field("file", JPEG, filename="p.jpg", content_type="image/jpeg")
    await client.post(f"/api/{DOMAIN}/plants/{plant['id']}/photos", data=form)

    url = (await ws.cmd("backup/create"))["url"]
    response = await client.get(url)
    assert response.status == 200
    backup = await response.read()
    with zipfile.ZipFile(io.BytesIO(backup)) as archive:
        names = archive.namelist()
    assert "plants.db" in names
    assert sum(name.startswith("photos/") for name in names) == 1

    await ws.cmd("plants/delete", plant_id=plant["id"])
    await ws.cmd("plants/create", plant={"name": "Cactus", "species": "Cactaceae"})
    response = await _upload(client, "backup", b"not a zip", "x.zip")
    assert response.status == 400
    response = await _upload(client, "backup", backup, "backup.zip")
    assert response.status == 200
    assert await response.json() == {"plants": 1, "photos": 1}
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state is ConfigEntryState.LOADED
    manager = entry.runtime_data
    assert [p["name"] for p in manager.plants] == ["Fern"]
    assert len(manager.plants[0]["photos"]) == 1
    assert os.path.exists(hass.config.path("plant_manager", "plants.db.before-restore"))
    # The Cactus device is gone, the Fern one is back.
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert sorted(d.name for d in devices) == ["Fern", "Plant Manager"]
    # Without a reload, the restored plant gets its entities back, and the panel keeps working.
    assert entity_state(hass, f"{plant['id']}_status").state != "unavailable"
    assert [p["name"] for p in await ws.cmd("plants/list")] == ["Fern"]
