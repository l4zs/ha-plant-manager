"""Config flow for Plant Manager.

Setup has no questions; plants are added in the panel. Identification and
reminder settings are in the options.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.util import slugify
import voluptuous as vol

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ID_PROVIDER,
    CONF_LANGUAGE,
    CONF_NOTIFY_ALERTS,
    CONF_NOTIFY_SERVICE,
    CONF_OPB_CLIENT_ID,
    CONF_OPB_CLIENT_SECRET,
    CONF_PLANTID_API_KEY,
    CONF_PLANTNET_API_KEY,
    CONF_REMINDER_TIME,
    CONF_SIDEBAR_TITLE,
    CONF_WEATHER_ENTITY,
    DEFAULT_OPTIONS,
    DOMAIN,
    LANGUAGE_PER_USER,
    NAME,
    PROVIDER_PLANTID,
    PROVIDER_PLANTNET,
    PROVIDERS,
)
from .i18n import LANGUAGES
from .knowledge import OpenPlantbook, OpenPlantbookError

_PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def _notify_selector(hass: HomeAssistant) -> selector.SelectSelector:
    """Phones with the Home Assistant app first (by device name), then other notify actions."""
    phones = {
        f"mobile_app_{slugify(name)}": name
        for entry in hass.config_entries.async_entries("mobile_app")
        if (name := entry.data.get("device_name"))
    }
    services = sorted(hass.services.async_services_for_domain("notify"))
    options = [
        selector.SelectOptionDict(value=f"notify.{s}", label=f"📱 {phones[s]}")
        for s in services
        if s in phones
    ] + [
        selector.SelectOptionDict(value=f"notify.{s}", label=f"notify.{s}")
        for s in services
        if s not in phones and s not in ("notify", "persistent_notification", "send_message")
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, custom_value=True, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


class PlantManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create the single entry."""
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={}, options=dict(DEFAULT_OPTIONS))
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return PlantManagerOptionsFlow()


class PlantManagerOptionsFlow(OptionsFlow):
    """Edit the options."""

    @property
    def _options(self) -> dict[str, Any]:
        return {**DEFAULT_OPTIONS, **self.config_entry.options}

    def _suggested(self) -> dict[str, Any]:
        return {key: value for key, value in self._options.items() if value != ""}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose what to change."""
        return self.async_show_menu(
            step_id="init", menu_options=["identification", "reminders", "language"]
        )

    async def async_step_identification(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Plant identification and care data sources."""
        errors: dict[str, str] = {}
        if user_input is not None:
            for key in (
                CONF_PLANTNET_API_KEY,
                CONF_PLANTID_API_KEY,
                CONF_AI_TASK_ENTITY,
                CONF_OPB_CLIENT_ID,
                CONF_OPB_CLIENT_SECRET,
            ):
                user_input.setdefault(key, "")
            provider = user_input[CONF_ID_PROVIDER]
            if provider == PROVIDER_PLANTNET and not user_input[CONF_PLANTNET_API_KEY]:
                errors[CONF_PLANTNET_API_KEY] = "api_key_required"
            if provider == PROVIDER_PLANTID and not user_input[CONF_PLANTID_API_KEY]:
                errors[CONF_PLANTID_API_KEY] = "api_key_required"
            client_id = user_input[CONF_OPB_CLIENT_ID]
            secret = user_input[CONF_OPB_CLIENT_SECRET]
            if bool(client_id) != bool(secret):
                errors["base"] = "openplantbook_incomplete"
            elif client_id:
                try:
                    await OpenPlantbook(self.hass, client_id, secret).async_validate()
                except OpenPlantbookError as err:
                    errors["base"] = f"openplantbook_{err}"
            if not errors:
                return self.async_create_entry(data={**self._options, **user_input})
        schema = vol.Schema(
            {
                vol.Required(CONF_ID_PROVIDER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=PROVIDERS,
                        translation_key="provider",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_PLANTNET_API_KEY): _PASSWORD,
                vol.Optional(CONF_PLANTID_API_KEY): _PASSWORD,
                vol.Optional(CONF_AI_TASK_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="ai_task")
                ),
                vol.Optional(CONF_OPB_CLIENT_ID): selector.TextSelector(),
                vol.Optional(CONF_OPB_CLIENT_SECRET): _PASSWORD,
            }
        )
        return self.async_show_form(
            step_id="identification",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self._suggested()
            ),
            errors=errors,
        )

    async def async_step_language(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Each user's language or one for everyone, and the title in the sidebar."""
        if user_input is not None:
            user_input[CONF_SIDEBAR_TITLE] = user_input.get(CONF_SIDEBAR_TITLE, "").strip()
            return self.async_create_entry(data={**self._options, **user_input})
        schema = vol.Schema(
            {
                vol.Required(CONF_LANGUAGE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[LANGUAGE_PER_USER, *LANGUAGES],
                        translation_key="language",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_SIDEBAR_TITLE): selector.TextSelector(),
            }
        )
        return self.async_show_form(
            step_id="language",
            data_schema=self.add_suggested_values_to_schema(schema, self._suggested()),
        )

    async def async_step_reminders(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Notifications, the daily reminder, and weather for outdoor plants."""
        errors: dict[str, str] = {}
        if user_input is not None:
            for key in (CONF_NOTIFY_SERVICE, CONF_REMINDER_TIME, CONF_WEATHER_ENTITY):
                user_input.setdefault(key, "")
            service = user_input[CONF_NOTIFY_SERVICE].strip()
            domain, _, name = service.rpartition(".")
            if service and not self.hass.services.has_service(domain or "notify", name):
                errors[CONF_NOTIFY_SERVICE] = "notify_not_found"
            if not errors:
                return self.async_create_entry(data={**self._options, **user_input})
        schema = vol.Schema(
            {
                vol.Required(CONF_NOTIFY_ALERTS): selector.BooleanSelector(),
                vol.Optional(CONF_NOTIFY_SERVICE): _notify_selector(self.hass),
                vol.Optional(CONF_REMINDER_TIME): selector.TimeSelector(),
                vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
            }
        )
        return self.async_show_form(
            step_id="reminders",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self._suggested()
            ),
            errors=errors,
        )
