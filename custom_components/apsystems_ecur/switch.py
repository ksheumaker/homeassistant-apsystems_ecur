import logging

from homeassistant.util import dt as dt_util
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity
)

from .const import (
    DOMAIN,
    RELOAD_ICON
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config, add_entities, discovery_info=None):

    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")

    switches = [
        APSystemsECUQuerySwitch(coordinator, ecu, "query_device", 
            label="Query Device", icon=RELOAD_ICON),
    ]
    add_entities(switches)


class APSystemsECUQuerySwitch(CoordinatorEntity, SwitchEntity):

    def __init__(self, coordinator, ecu, field, label=None, icon=None):

        super().__init__(coordinator)

        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label
        if not label:
            self._label = field
        self._icon = icon

        self._name = f"ECU {self._label}"
        self._state = None

    @property
    def unique_id(self):
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def device_info(self):
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def is_on(self):
        return self._ecu.querying

    async def async_turn_off(self, **kwargs):
        self._ecu.stop_query()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        self._ecu.start_query()
        await self.coordinator.async_request_refresh()


