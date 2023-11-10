"""The StecaGrid integration."""
import asyncio
import logging
import requests
from datetime import timedelta, datetime
import voluptuous as vol
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=15)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the StecaGrid component."""
    hass.data[DOMAIN] = {}
    return True




async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up StecaGrid from a config entry."""
    inverter_host = entry.data['inverter_host'] #inverter_host
    inverter_port = entry.data['inverter_port'] #inverter_port
    
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

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_energy(self):
        _LOGGER.debug("Fetching energy data from Stecagrid")

        #host = '10.0.10.159'
        #port = 2323
        msgRequest = b'\x02\x01\x00\x10\x01\xC9\x65\x40\x03\x00\x01\x29\x7E\x29\xBE\x03'

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self._inverter_host, self._inverter_port))
        client.send(msgRequest)

        msgResponse = client.recv(30)
        #msgResponse = b'\x02\x01\x00\x1e\xc9\x01\xFF\xFF\x00\x00\x0f\xFF\x00\x00\x07\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x0b\x0b\x90\x00\x85\xFF\xFF\x03'
        power_output = 0.0

        #print (msgResponse)

        if (msgResponse[22] == 0x0B):
            temp = ((msgResponse[25] << 8 | msgResponse[23]) << 8 | msgResponse[24]) << 7
            power_output = struct.unpack('!f', bytes.fromhex(str(hex(temp)).split('0x')[1]))[0]
        else:
            _LOGGER.debug("Ingen solproduktion fra Steca inverter")

        #print(power_output, 'W')

        #day_data = self._client.get_latest(self._metering_point)
        return power_output
       
        _LOGGER.debug("Done fetching energy data from Stecagrid")