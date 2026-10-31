"""Fixtures for Plant Manager tests."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_manager.const import DEFAULT_OPTIONS, DOMAIN

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom_components in every test."""


@pytest.fixture
def options() -> dict[str, Any]:
    """Options for the config entry; override in a test module to change them."""
    return dict(DEFAULT_OPTIONS)


@pytest.fixture
async def entry(hass: HomeAssistant, tmp_path, options: dict[str, Any]) -> MockConfigEntry:
    """Set up the integration with its data in a temporary directory."""
    hass.config.config_dir = str(tmp_path)
    hass.config.latitude = 52.5
    config_entry = MockConfigEntry(domain=DOMAIN, title="Plant Manager", options=options)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
async def ws(hass: HomeAssistant, hass_ws_client, entry):
    """Return a websocket client with a helper to send commands."""
    client = await hass_ws_client(hass)

    async def send(command: str, **data: Any) -> Any:
        await client.send_json_auto_id({"type": f"{DOMAIN}/{command}", **data})
        response = await client.receive_json()
        assert response["success"], response
        return response["result"]

    async def error(command: str, **data: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"{DOMAIN}/{command}", **data})
        response = await client.receive_json()
        assert not response["success"], response
        return response["error"]

    client.cmd = send
    client.error = error
    return client


def entity_state(hass: HomeAssistant, unique_id: str, platform: str = "sensor"):
    """Return the state of one of the integration's entities by unique id."""
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, unique_id
    return hass.states.get(entity_id)
