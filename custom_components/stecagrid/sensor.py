"""Platform for Stecagrid sensor integration."""
from datetime import datetime, timedelta
import logging
from homeassistant.const import UnitOfPower
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    DOMAIN as RECORDER_DOMAIN,
    async_import_statistics,
    get_last_statistics,
)
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
from .__init__ import HassStecaGrid, MIN_TIME_BETWEEN_UPDATES
from .const import DOMAIN, WATT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    stecagrid = hass.data[DOMAIN][config.entry_id]

    sensors = []
    sensors.append(StecagridEnergy('Stecagrid power', stecagrid))
    
    async_add_entities(sensors)

class StecagridEnergy(Entity):
    """Representation of a meter reading sensor."""

    def __init__(self, name, client):
        """Initialize the sensor."""
        self._state = None
        self._name = name
        self._data = client
        self._unique_id = self._data.get_unique_id()

    @property
    def device_info(self):
        """Return device information about this entity."""
        _LOGGER.debug("Stecagrid: device_info")

        return {
            "identifiers": {
                # Unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "manufacturer": "Oernsholt (Steca)",
            "model": "StecaGrid inverter i fyrrum",
            "name": self._data.get_name()
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """The unique id of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.ENERGY

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
    
        _LOGGER.info(f"Steca updating power...")

        power_output = self._data.update_power()       

        self._state = power_output
        
