"""Tests for plant identification."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.plant_manager.const import DEFAULT_OPTIONS, DOMAIN
from custom_components.plant_manager.identify import PLANTNET_URL

from .conftest import JPEG

PLANTNET_RESULT = {
    "results": [
        {
            "score": 0.91,
            "species": {
                "scientificNameWithoutAuthor": "Ficus lyrata",
                "commonNames": ["Fiddle-leaf fig"],
                "family": {"scientificNameWithoutAuthor": "Moraceae"},
            },
        },
        {
            "score": 0.04,
            "species": {
                "scientificNameWithoutAuthor": "Ficus elastica",
                "commonNames": ["Rubber plant"],
                "family": {"scientificNameWithoutAuthor": "Moraceae"},
            },
        },
    ]
}


@pytest.fixture
def options() -> dict[str, Any]:
    """Identify with Pl@ntNet."""
    return {**DEFAULT_OPTIONS, "identification_provider": "plantnet", "plantnet_api_key": "key"}


async def _identify(client, data: bytes = JPEG) -> tuple[int, dict[str, Any]]:
    form = aiohttp.FormData()
    form.add_field("file", data, filename="plant.jpg", content_type="image/jpeg")
    response = await client.post(f"/api/{DOMAIN}/identify", data=form)
    return response.status, await response.json()


async def test_identify_and_save_photo(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    ws,
    hass_client,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A photo is identified, staged, and saved with the new plant."""
    aioclient_mock.post(PLANTNET_URL, json=PLANTNET_RESULT)
    client = await hass_client()
    status, result = await _identify(client)
    assert status == 200
    assert result["error"] is None
    assert [c["scientific_name"] for c in result["candidates"]] == [
        "Ficus lyrata",
        "Ficus elastica",
    ]
    assert result["candidates"][0]["family"] == "Moraceae"

    staged = await client.get(f"/api/{DOMAIN}/staged/{result['staged_id']}")
    assert staged.status == 200

    best = result["candidates"][0]
    profile = await ws.cmd(
        "profile/resolve", species=best["scientific_name"], family=best["family"]
    )
    plant = await ws.cmd(
        "plants/create",
        plant={"name": "Figgy", "species": best["scientific_name"], "family": best["family"],
               "common_name": best["common_names"][0], "profile": profile["profile"],
               "profile_sources": profile["sources"]},
    )  # fmt: skip
    assert plant["common_name"] == "Fiddle-leaf fig"
    await ws.cmd("photos/attach_staged", plant_id=plant["id"], staged_id=result["staged_id"])
    plant = await ws.cmd("plants/get", plant_id=plant["id"])
    assert len(plant["photos"]) == 1
    error = await ws.error(
        "photos/attach_staged", plant_id=plant["id"], staged_id=result["staged_id"]
    )
    assert error["code"] == "not_found"


async def test_identify_errors(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client, aioclient_mock: AiohttpClientMocker
) -> None:
    """Provider errors are reported; the photo is still staged."""
    aioclient_mock.post(PLANTNET_URL, status=401)
    client = await hass_client()
    status, result = await _identify(client)
    assert status == 200
    assert result["error"] == "invalid_auth"
    assert result["staged_id"]

    aioclient_mock.clear_requests()
    aioclient_mock.post(PLANTNET_URL, status=404, json={"message": "Species not found"})
    _, result = await _identify(client)
    assert result["error"] == "no_match"

    form = aiohttp.FormData()
    form.add_field("file", b"nope", filename="x.txt")
    response = await client.post(f"/api/{DOMAIN}/identify", data=form)
    assert response.status == 415


async def test_identify_action(
    hass: HomeAssistant, entry: MockConfigEntry, tmp_path, aioclient_mock: AiohttpClientMocker
) -> None:
    """The identify action works on image files."""
    aioclient_mock.post(PLANTNET_URL, json=PLANTNET_RESULT)
    path = tmp_path / "plant.jpg"
    path.write_bytes(JPEG)
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    response = await hass.services.async_call(
        DOMAIN, "identify", {"image_path": str(path)}, blocking=True, return_response=True
    )
    assert response["candidates"][0]["scientific_name"] == "Ficus lyrata"
