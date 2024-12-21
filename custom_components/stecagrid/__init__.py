"""The StecaGrid integration."""

import asyncio
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .steca import StecaConnector

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the StecaGrid component."""

    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up StecaGrid from a config entry."""
    inverter_host = entry.data["inverter_host"]
    inverter_port = entry.data["inverter_port"]
    inverter_scaninterval = entry.data["scan_interval"]
    inverter_alias = entry.data["alias"]

    stecaApi = StecaConnector(inverter_host, inverter_port)

    # Fetch initial data so we have data when entities subscribe
    coordinator = StecaGridCoordinator(
        hass, stecaApi, inverter_alias, inverter_scaninterval
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = HassStecaGrid(
        coordinator, inverter_host, inverter_port
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
    def __init__(
        self, coordinator: DataUpdateCoordinator, inverter_host: str, inverter_port: int
    ):
        self._inverter_host = inverter_host
        self._inverter_port = inverter_port
        _LOGGER.debug("Stecagrid __init__" + self._inverter_host)

        # create an instance of StecaConnector
        self._coordinator = coordinator

    def get_name(self):
        return f"steca_grid_{self._inverter_host}_{str(self._inverter_port)}"

    def get_unique_id(self):
        return f"steca_grid_power_{self._inverter_host}_{str(self._inverter_port)}"


class StecaGridCoordinator(DataUpdateCoordinator):
    """StecaGrid coordinator."""

    def __init__(self, hass, stecaAPI: StecaConnector, alias: str, pollinterval: int):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=f"StecaGrid coordinator for '{alias}'",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=pollinterval),
        )
        self.stecaApi = stecaAPI
        self._alias = alias

    async def _async_update_data(self):
        # Fetch data from API endpoint. This is the place to pre-process the data to lookup tables so entities can quickly look up their data.

        try:
            retData = {}
            async with asyncio.timeout(3):
                retData["power"] = self.stecaApi.GetPowerOutput()
                retData["time"] = self.stecaApi.GetInverterTime()

                return retData
        except:
            _LOGGER.error("StecaGridCoordinator _async_update_data failed")
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")
