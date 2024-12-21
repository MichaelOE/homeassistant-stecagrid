"""Config flow for StecaGrid integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_ALIAS
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_INVERTER_HOST, CONF_INVERTER_POLL, CONF_INVERTER_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_INVERTER_HOST, default=None): str,
        vol.Required(CONF_INVERTER_PORT, default=23): int,
        vol.Optional(CONF_INVERTER_POLL, default=5): int,
    }
)
STEP_DATA_ALIAS = vol.Schema(
    {
        vol.Required(CONF_ALIAS): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for StecaGrid."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                self._userInput = user_input
                return await self.async_step_alias()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_DATA_SCHEMA, errors=errors
        )

    async def async_step_alias(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the alias step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._userInput[CONF_ALIAS] = user_input[CONF_ALIAS]
                _LOGGER.info(user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"{self._userInput[CONF_ALIAS]}  ({self._userInput[CONF_INVERTER_HOST]}:{self._userInput[CONF_INVERTER_PORT]})",
                    data=self._userInput,
                )

        return self.async_show_form(
            step_id="alias", data_schema=STEP_DATA_ALIAS, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
