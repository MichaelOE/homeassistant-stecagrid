"""Platform for Stecagrid sensor integration."""
from datetime import datetime, timedelta
import logging
import socket
import struct
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
from pystecagrid.models import TimeSeries
from .__init__ import HassStecagrid, MIN_TIME_BETWEEN_UPDATES
from .const import DOMAIN, KILO

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    stecagrid = hass.data[DOMAIN][config.entry_id]

    sensors = []
    sensors.append(StecagridEnergy("Stecagrid power", 'power', stecagrid))

    async_add_entities(sensors)

class StecagridEnergy(Entity):
    """Representation of an energy sensor."""

    def __init__(self, name):
        """Initialize the sensor."""
        self._state = None
        self._data = client
        self._name = name

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
    def extra_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        attributes['metering_date'] = self._data_date

        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT 

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update_energy()
