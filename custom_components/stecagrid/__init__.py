"""The StecaGrid integration."""
import asyncio
import logging
import requests

#import socket
#import struct

from datetime import timedelta, datetime
import voluptuous as vol
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .steca import StecaConnector

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the StecaGrid component."""

    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up StecaGrid from a config entry."""
    inverter_host = entry.data['inverter_host']
    inverter_port = entry.data['inverter_port']
    
    hass.data[DOMAIN][entry.entry_id] = HassStecaGrid(inverter_host, inverter_port)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class HassStecaGrid:
    def __init__(self, inverter_host, inverter_port):
        self._inverter_host = inverter_host
        self._inverter_port = inverter_port
        _LOGGER.debug("Stecagrid __init__" + self._inverter_host)

    def get_name(self):
        return f"steca_grid_{self._inverter_host}_{str(self._inverter_port)}"

    def get_unique_id(self):
        return f"steca_grid_power_{self._inverter_host}_{str(self._inverter_port)}"

    def update_power(self):
        # create an instance of StecaConnector
        steca_connector = steca.StecaConnector(self._inverter_host, self._inverter_port)

        _LOGGER.debug("Requesting timestamp from Stecagrid")
        inverterTime = steca_connector.GetInverterTime()
        _LOGGER.debug(f"Inverter time: {inverterTime}")

        _LOGGER.debug("Requesting current power_output from Stecagrid")
        power_output = steca_connector.GetPowerOutput()
        if isinstance(power_output, float):
            _LOGGER.debug("power_output er en float")
        else:
            _LOGGER.debug("power_output er ikke en float")
            power_output = 0.0

        _LOGGER.debug(f"Done fetching info from Stecagrid, {power_output}W")
        return power_output