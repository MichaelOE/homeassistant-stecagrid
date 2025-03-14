"""Platform for Stecagrid sensor integration."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import StecaGridCoordinator
from .const import DEFAULT_INVERTER_POLLRATE, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_INVERTER_POLLRATE)


@dataclass
class StecaGridEntityDescription(SensorEntityDescription):
    """Describes Stecagrid sensor entity."""

    def __init__(
        self,
        key,
        name,
        icon,
        device_class,
        native_unit_of_measurement,
        value,
        format=None,
    ):
        super().__init__(key)
        self.key = key
        self.name = name
        self.icon = icon
        if device_class is not None:
            self.device_class = device_class
        self.native_unit_of_measurement = native_unit_of_measurement
        self.value = value
        self.format = format


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Set up the sensor platform."""
    stecagrid = hass.data[DOMAIN][config.entry_id]

    entities: list[StecagridSensor] = [
        StecagridSensor(stecagrid._coordinator, sensor, stecagrid)
        for sensor in SENSORS_INVERTER
    ]

    async_add_entities(entities)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Code for setting up your platform inside of the event loop
    _LOGGER.debug("async_setup_platform")


class StecagridSensor(CoordinatorEntity, SensorEntity):
    """Representation of a meter reading sensor."""

    def __init__(
        self,
        coordinator: StecaGridCoordinator,
        sensor: StecaGridEntityDescription,
        client,
    ):
        """Initialize the sensor."""
        self._data = client
        self.coordinator = coordinator
        self.entity_description: StecaGridEntityDescription = sensor
        self._attr_unique_id = f"{self.coordinator._alias}_{sensor.key}"
        self._attr_name = f"{self.coordinator._alias} {sensor.name}"

        _LOGGER.info(self._attr_unique_id)
        self._attr_native_value = None  # Initialize the native value

    @property
    def device_info(self):
        """Return device information about this entity."""
        _LOGGER.debug("StecaGrid: device_info")

        return {
            "identifiers": {(DOMAIN, self.coordinator._alias)},
            "manufacturer": "Steca",
            "model": "StecaGrid 8000+ 3ph",
            "name": self.coordinator._alias,
        }

    @property
    def should_poll(self):
        return False

    @property
    def friendly_name(self):
        return self.entity_description.name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attr_native_value

    async def async_added_to_hass(self):
        """Handle entity addition to hass."""
        # Add the coordinator listener for data updates
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        # Ensure that data is fetched initially
        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data_available = False

        try:
            # Handle power
            if "output" in self.entity_description.key:
                self._attr_native_value = self.coordinator.data["power"]
                data_available = True

            # Handle time
            if "time" in self.entity_description.key:
                self._attr_native_value = self.coordinator.data["time"]
                data_available = True

            self._attr_available = data_available

            # Only call async_write_ha_state if the state has changed
            if data_available:
                self.async_write_ha_state()

        except KeyError as ex:
            _LOGGER.debug(
                f"KeyError: {str(ex)} while handling {self.entity_description.key}"
            )
        except ValueError as ex:
            _LOGGER.debug(
                f"ValueError: {str(ex)} while handling {self.entity_description.key}"
            )
        except Exception as ex:
            _LOGGER.debug(
                f"Unexpected error: {str(ex)} while handling {self.entity_description.key}"
            )


SENSORS_INVERTER: tuple[SensorEntityDescription, ...] = (
    StecaGridEntityDescription(
        key="output",
        name="Output power",
        icon="mdi:power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        value=lambda data, key: data[key],
    ),
    StecaGridEntityDescription(
        key="time",
        name="timestamp",
        icon="mdi:clock-digital",
        device_class=None,
        native_unit_of_measurement=None,
        value=lambda data, key: data[key],
    ),
)
