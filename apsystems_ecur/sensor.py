"""Example integration using DataUpdateCoordinator."""

from datetime import timedelta
import logging

import async_timeout

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    SOLAR_ICON,
    FREQ_ICON,
    SIGNAL_ICON
)

from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_ENERGY,
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
    VOLT,
    TEMP_CELSIUS,
    PERCENTAGE,
    FREQUENCY_HERTZ
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, add_entities, discovery_info=None):

    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")


    sensors = [
        APSystemsECUSensor(coordinator, ecu, "current_power", 
            label="Current Power", unit=POWER_WATT, 
            devclass=DEVICE_CLASS_POWER, icon=SOLAR_ICON),
        APSystemsECUSensor(coordinator, ecu, "daily_max_power",
            label="Daily Maximum Power", unit=POWER_WATT, 
            devclass=DEVICE_CLASS_POWER, icon=SOLAR_ICON),
        APSystemsECUSensor(coordinator, ecu, "today_energy", 
            label="Today Energy", unit=ENERGY_KILO_WATT_HOUR, 
            devclass=DEVICE_CLASS_ENERGY, icon=SOLAR_ICON),
        APSystemsECUSensor(coordinator, ecu, "lifetime_energy", 
            label="Lifetime Energy", unit=ENERGY_KILO_WATT_HOUR, 
            devclass=DEVICE_CLASS_ENERGY, icon=SOLAR_ICON),
    ]

    inverters = coordinator.data.get("inverters", {})
    for uid,inv_data in inverters.items():
        #_LOGGER.warning(f"Inverter {uid} {inv_data.get('channel_qty')}")
        sensors.extend([
                APSystemsECUInverterSensor(coordinator, ecu, uid, 
                    "temperature", label="Temperature", 
                    devclass=DEVICE_CLASS_TEMPERATURE, unit=TEMP_CELSIUS),
                APSystemsECUInverterSensor(coordinator, ecu, uid, 
                    "frequency", label="Frequency", unit=FREQUENCY_HERTZ, 
                    devclass=None, icon=FREQ_ICON),
                APSystemsECUInverterSensor(coordinator, ecu, uid, 
                    "voltage", label="Voltage", unit=VOLT, 
                    devclass=DEVICE_CLASS_VOLTAGE),
                APSystemsECUInverterSensor(coordinator, ecu, uid, 
                    "signal", label="Signal", unit=PERCENTAGE, 
                    icon=SIGNAL_ICON)

        ])
        for i in range(0, inv_data.get("channel_qty", 0)):
            sensors.append(
                APSystemsECUInverterSensor(coordinator, ecu, uid, f"power", 
                    index=i, label=f"Power Ch {i+1}", unit=POWER_WATT, 
                    devclass=DEVICE_CLASS_POWER, icon=SOLAR_ICON)
            )

    add_entities(sensors)


class APSystemsECUInverterSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, ecu, uid, field, index=0, label=None, icon=None, unit=None, devclass=None):

        super().__init__(coordinator)

        self.coordinator = coordinator

        self._index = index
        self._uid = uid
        self._ecu = ecu
        self._field = field
        self._devclass = devclass
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._unit = unit

        self._name = f"Inverter {self._uid} {self._label}"
        self._state = None

    @property
    def unique_id(self):
        field = self._field
        if self._index != None:
            field = f"{field}_{self._index}"
        return f"{self._ecu.ecu.ecu_id}_{self._uid}_{field}"

    @property
    def device_class(self):
        return self._devclass

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        #_LOGGER.warning(f"State called for {self._field}")
        if self._field == "voltage":
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get("voltage", [])[0]
        elif self._field == "power":
            #_LOGGER.warning(f"POWER  {self._uid} {self._index}")
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get("power", [])[self._index]
        else:
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get(self._field)

    @property
    def icon(self):
        return self._icon

    @property
    def unit_of_measurement(self):
        return self._unit


    @property
    def device_state_attributes(self):

        attrs = {
            "ecu_id" : self._ecu.ecu.ecu_id,
            "last_update" : self._ecu.ecu.last_update,
        }
        return attrs

    

class APSystemsECUSensor(CoordinatorEntity, Entity):

    def __init__(self, coordinator, ecu, field, label=None, icon=None, unit=None, devclass=None):

        super().__init__(coordinator)

        self.coordinator = coordinator

        self._ecu = ecu
        self._field = field
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._unit = unit
        self._devclass = devclass

        self._name = f"ECU {self._label}"
        self._state = None

    @property
    def unique_id(self):
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        return self._devclass

    @property
    def state(self):
        #_LOGGER.warning(f"State called for {self._field}")
        return self.coordinator.data.get(self._field)

    @property
    def icon(self):
        return self._icon

    @property
    def unit_of_measurement(self):
        return self._unit


    @property
    def device_state_attributes(self):

        attrs = {
            "ecu_id" : self._ecu.ecu.ecu_id,
            "firmware" : self._ecu.ecu.firmware,
            "last_update" : self._ecu.ecu.last_update
        }
        return attrs


    
