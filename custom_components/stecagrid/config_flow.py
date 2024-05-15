"""Config flow for StecaGrid integration."""

import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions

# from .const import DOMAIN  # pylint:disable=unused-import
from .const import CONF_INVERTER_HOST, CONF_INVERTER_POLL, CONF_INVERTER_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# DATA_SCHEMA = vol.Schema({"inverter_host": str, "inverter_port": int})
DATA_SCHEMA = vol.Schema({})
DATA_SCHEMA = DATA_SCHEMA.extend(
    {
        vol.Required(CONF_INVERTER_HOST, default=None): str,
        vol.Required(CONF_INVERTER_PORT, default=23): int,
        vol.Optional(CONF_INVERTER_POLL, default=5): int,
    }
)

# async def validate_input(hass: core.HomeAssistant, data):
#     """Validate the user input allows us to connect.

#     Data has the keys from DATA_SCHEMA with values provided by the user.
#     """

#     # Return info that you want to store in the config entry.
#     inverter_host = data["inverter_host"]
#     inverter_port = data["inverter_port"]
#     return {"title": f"StecaGrid #{inverter_host}:{inverter_port}#"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for StecaGrid."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                inverter_host = user_input[CONF_INVERTER_HOST]
                inverter_port = user_input[CONF_INVERTER_PORT]
                scan_interval = user_input[CONF_INVERTER_POLL]

                info = f"StecaGrid {inverter_host}:{inverter_port} (poll rate {scan_interval}s)"
                return self.async_create_entry(title=info, data=user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
