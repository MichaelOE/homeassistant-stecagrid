"""The StecaGrid integration."""
import asyncio
import logging
import requests
import socket
import struct
from datetime import timedelta, datetime
import voluptuous as vol
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)


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

    #@Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_power(self):
        _LOGGER.debug("Fetching energy data from Stecagrid")

        power_output = 0.0

        host = self._inverter_host # '10.0.10.159'
        port = self._inverter_port # 2323
        msgRequest = b'\x02\x01\x00\x10\x01\xC9\x65\x40\x03\x00\x01\x29\x7E\x29\xBE\x03'

        tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpClient.connect((host, port))
        tcpClient.send(msgRequest)

        msgResponse = tcpClient.recv(30)
        power_output = 0.0

        #print (msgResponse)

        try:
            if (msgResponse[22] == 0x0B):
                temp = ((msgResponse[25] << 8 | msgResponse[23]) << 8 | msgResponse[24]) << 7
                power_output = struct.unpack('!f', bytes.fromhex(str(hex(temp)).split('0x')[1]))[0]
                _LOGGER.debug(f"Steca grid power_output: {str(power_output)} W")
            else:
                _LOGGER.info("Steca grid - Ingen solproduktion")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.info(f"Fejl ved parsing af inverterdata! - der er sikkert overskyet, output: {str(power_output)}")

        return power_output

        _LOGGER.debug("Done fetching energy data from Stecagrid")
