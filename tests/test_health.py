"""Tests for the photo health check."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.plant_manager.const import DEFAULT_OPTIONS, DOMAIN, PLANTNET_API
from custom_components.plant_manager.health import CheckError, candidates_from, free_quota

from .conftest import JPEG

FRONTEND = Path(__file__).parent.parent / "custom_components" / "plant_manager" / "frontend"
RESTRICTED = {"contract_restricted": True}


def _daily(remaining: Any, total: Any) -> dict[str, Any]:
    return {"quota": {"identify": {"remaining": remaining, "total": total}}}


@pytest.fixture
def options() -> dict[str, Any]:
    """Check photos with Pl@ntNet."""
    return {**DEFAULT_OPTIONS, "plantnet_api_key": "key"}


@pytest.mark.parametrize("total", [500, 1000])
def test_limit_comes_from_the_account(total: int) -> None:
    """Any limit Pl@ntNet reports for a free account is accepted."""
    quota = free_quota(RESTRICTED, _daily(12, total))
    assert quota == {"remaining": 12, "total": total, "plan": "free"}
    assert free_quota({"contract": {"plan": "free"}}, _daily(1, total))["remaining"] == 1


@pytest.mark.parametrize(
    ("subscription", "daily"),
    [
        ({"contract": {"plan": "pro"}}, _daily(100, 5000)),  # a paid plan
        ({}, _daily(100, 500)),  # the plan is unknown
        (RESTRICTED, _daily(0, 500)),  # used up
        (RESTRICTED, _daily(None, 500)),
        (RESTRICTED, _daily(1, 0)),
        (RESTRICTED, {"quota": "unexpected"}),
        (RESTRICTED, {}),
    ],
)
def test_no_photo_is_sent_when_in_doubt(subscription: dict, daily: dict) -> None:
    """A paid, unknown or used-up account stops the check."""
    with pytest.raises(CheckError):
        free_quota(subscription, daily)


def test_candidates_are_bounded() -> None:
    """Invalid rows are dropped; the best suggestions come first."""
    rows = [{"name": f"c{i}", "description": "x", "score": i / 10} for i in range(9)]
    assert [c["code"] for c in candidates_from({"results": rows})] == [
        "c4",
        "c3",
        "c2",
        "c1",
        "c0",
    ]
    assert candidates_from({"results": [{"name": "a", "score": "nan"}, "x"]}) == []
    with pytest.raises(CheckError):
        candidates_from({"results": "x"})


async def test_check_a_photo(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    ws,
    hass_client,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A check reads the limit, keeps the result, and adds a photo and a note."""
    aioclient_mock.get(f"{PLANTNET_API}/subscription", status=403)
    aioclient_mock.get(f"{PLANTNET_API}/quota/daily", json=_daily(700, 1000))
    aioclient_mock.post(
        f"{PLANTNET_API}/diseases/identify",
        json={
            "results": [{"name": "ABCDEF", "description": "Blattflecken", "score": 0.8}],
            "remainingIdentificationRequests": 699,
        },
    )
    plant = await ws.cmd("plants/create", plant={"name": "Monty", "species": "Monstera deliciosa"})
    client = await hass_client()
    url = f"/api/{DOMAIN}/health/{plant['id']}"

    response = await client.get(url)
    assert response.status == 200
    ready = await response.json()
    assert ready["ready"] is True
    assert ready["quota"] == {"remaining": 700, "total": 1000, "plan": "free"}
    assert "coverage" not in ready

    form = aiohttp.FormData()
    form.add_field("file", JPEG, filename="plant.jpg", content_type="image/jpeg")
    response = await client.post(url, data=form)
    assert response.status == 200
    record = await response.json()
    assert record["candidates"][0]["label"] == "Blattflecken"
    assert record["remaining"] == 699

    response = await client.get(url)
    assert [check["id"] for check in (await response.json())["checks"]] == [record["id"]]
    got = await ws.cmd("plants/get", plant_id=plant["id"])
    assert len(got["photos"]) == 1
    assert any("Blattflecken" in (event.get("notes") or "") for event in got["events"])


def test_frontend_modules_have_no_fixed_version() -> None:
    """Modules load under the version the integration gives the entry file."""
    for path in FRONTEND.glob("*.js"):
        assert not re.search(r"\.js\?v=", path.read_text(encoding="utf-8")), path.name


async def test_errors_follow_the_language(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    ws,
    hass_client,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """The check's messages are English or German, like the rest."""
    aioclient_mock.get(f"{PLANTNET_API}/subscription", status=401)
    plant = await ws.cmd("plants/create", plant={"name": "Monty", "species": "Monstera deliciosa"})
    client = await hass_client()
    url = f"/api/{DOMAIN}/health/{plant['id']}"
    english = await (await client.get(url, params={"language": "en"})).json()
    assert english["message"] == "Pl@ntNet rejected the existing access."
    german = await (await client.get(url, params={"language": "de"})).json()
    assert german["message"] == "Pl@ntNet hat den vorhandenen Zugang abgelehnt."


def test_frontend_colours_come_from_the_theme() -> None:
    """Only the print page, which has no theme, has colours of its own."""
    for path in FRONTEND.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"<!doctype html>.*?</html>", "", text, flags=re.DOTALL)
        assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", text), path.name
        assert not re.findall(r"(?:color|background):\s*(?:white|black)\b", text), path.name
