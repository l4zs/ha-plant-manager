"""Tests for the config and options flows."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_manager.const import DEFAULT_OPTIONS, DOMAIN
from custom_components.plant_manager.i18n import LANGUAGES


async def test_user_flow(hass: HomeAssistant, tmp_path) -> None:
    """Setup has no questions and only one entry is allowed."""
    hass.config.config_dir = str(tmp_path)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == DEFAULT_OPTIONS
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_identification_options(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A provider that needs a key asks for it."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "identification"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"identification_provider": "plantnet"}
    )
    assert result["errors"] == {"plantnet_api_key": "api_key_required"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"identification_provider": "plantnet", "openplantbook_client_id": "x"}
    )
    assert result["errors"]["base"] == "openplantbook_incomplete"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"identification_provider": "plantnet", "plantnet_api_key": "key"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["plantnet_api_key"] == "key"
    assert entry.options["reminder_time"] == "09:00:00"


async def test_reminder_options(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The notify action must exist."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "reminders"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"notify_alerts": True, "notify_service": "notify.nope"}
    )
    assert result["errors"] == {"notify_service": "notify_not_found"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"notify_alerts": False, "reminder_time": "08:30:00"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["notify_alerts"] is False


async def test_language_option(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A fixed language is a choice per instance, each user's by default."""
    assert entry.options["language"] == "user"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "language"}
    )
    assert result["step_id"] == "language"
    field = next(iter(result["data_schema"].schema.values()))
    assert field.config["options"] == ["user", *LANGUAGES]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"language": "de"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["language"] == "de"
    assert entry.options["sidebar_title"] == ""


async def test_sidebar_title_option(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A title of your own wins over the translated one; emptying it brings that back."""

    async def save(title: str) -> str:
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "language"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"language": "de", "sidebar_title": title}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        return hass.data["frontend_panels"]["plant-manager"].sidebar_title

    assert await save("  Dschungel ") == "Dschungel"
    assert entry.options["sidebar_title"] == "Dschungel"
    assert await save("") == "Pflanzen"
    # Leaving the field out of the form clears it too.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "language"}
    )
    await hass.config_entries.options.async_configure(result["flow_id"], {"language": "en"})
    await hass.async_block_till_done()
    assert hass.data["frontend_panels"]["plant-manager"].sidebar_title == "Plants"
