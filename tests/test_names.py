"""Tests for the plant names shown in the panel and the cards."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_manager.species_db import display_names


def _plant(plant_id: str, name: str, species: str, created: str = "2026-01-01") -> dict:
    return {
        "id": plant_id,
        "name": name,
        "species": species,
        "common_name": name,
        "created_at": created,
    }


def test_names_are_translated_from_the_species() -> None:
    """A name from the species is translated; other names stay."""
    plants = [
        _plant("a", "Peace lily", "Spathiphyllum floribundum"),
        _plant("b", "Arabian coffee", "Coffea arabica"),
        _plant("c", "Nerveplant", "Fittonia albivenis"),
        _plant("d", "Philodendron Green Congo", "Philodendron martianum"),
        _plant("e", "Unknown thing", "Nonexistus plantus"),
        {**_plant("f", "Monty", "Monstera deliciosa"), "common_name": "Monstera"},
    ]
    assert display_names(plants, "de") == {
        "a": "Einblatt",
        "b": "Kaffeestrauch",
        "c": "Fittonie",
        "d": "Philodendron Green Congo",
        "e": "Unknown thing",
        "f": "Monty",
    }
    assert display_names(plants, "en")["a"] == "Peace lily"


def test_only_shared_names_are_numbered_by_creation_date() -> None:
    """Numbers count per name, and do not depend on id or list order."""
    older = _plant("z", "ZZ Plant", "Zamioculcas zamiifolia", "2026-01-01")
    newer = _plant("a", "ZZ Plant", "Zamioculcas zamiifolia", "2026-01-02")
    # The same name in German, from another English name.
    lily = _plant("l", "Peace lily", "Spathiphyllum wallisii", "2026-01-03")
    lily2 = _plant("m", "Einblatt", "Spathiphyllum wallisii", "2026-01-04")
    coffee = _plant("c", "Arabian coffee", "Coffea arabica")
    assert display_names([newer, lily2, coffee, older, lily], "de") == {
        "z": "Glücksfeder · 1",
        "a": "Glücksfeder · 2",
        "l": "Einblatt · 1",
        "m": "Einblatt · 2",
        "c": "Kaffeestrauch",
    }
    # Names of your own that match are numbered too.
    assert display_names(
        [
            {**_plant("x", "Bob", "Ficus lyrata"), "common_name": None},
            {**_plant("y", "bob", "Monstera deliciosa", "2026-02-01"), "common_name": None},
        ]
    ) == {"x": "Bob · 1", "y": "bob · 2"}


async def test_every_view_has_the_display_name(
    hass: HomeAssistant, entry: MockConfigEntry, ws
) -> None:
    """The list, a single plant and the card's summary agree on the name."""
    plant = {"name": "ZZ Plant", "species": "Zamioculcas zamiifolia", "common_name": "ZZ Plant"}
    first = await ws.cmd("plants/create", plant=plant, language="de")
    second = await ws.cmd("plants/create", plant=plant, language="de")
    assert second["display_name"] == "Glücksfeder · 2"

    listed = {p["id"]: p["display_name"] for p in await ws.cmd("plants/list", language="de")}
    assert listed == {first["id"]: "Glücksfeder · 1", second["id"]: "Glücksfeder · 2"}
    got = await ws.cmd("plants/get", plant_id=first["id"], language="de")
    assert got["display_name"] == "Glücksfeder · 1"

    await ws.cmd("plants/update", plant_id=second["id"], changes={"name": "Bob"}, language="de")
    listed = {p["id"]: p["display_name"] for p in await ws.cmd("plants/list", language="de")}
    assert listed == {first["id"]: "Glücksfeder", second["id"]: "Bob"}

    await ws.cmd("plants/water", plant_id=first["id"], language="de")
    summary = await ws.cmd("summary", language="de")
    assert all("display_name" in p for p in summary["attention"])
