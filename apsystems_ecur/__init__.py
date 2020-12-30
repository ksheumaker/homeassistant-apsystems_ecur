import logging

import voluptuous as vol
from datetime import timedelta

from .APSystemsECUR import APSystemsECUR
from homeassistant.helpers.discovery import load_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_HOST
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({
    DOMAIN : vol.Schema({
        vol.Required(CONF_HOST): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [ "sensor" ]

async def async_setup(hass, config):
    """ Setup the APsystems platform """
    hass.data.setdefault(DOMAIN, {})

    host = config[DOMAIN].get(CONF_HOST)

    ecu = APSystemsECUR(host)

    async def async_update_data():
        #_LOGGER.warning(f"Calling Update data... {ecu.current_power}")
        return await ecu.async_query_ecu()

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=async_update_data,
            update_interval=timedelta(minutes=1),
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }

    for component in PLATFORMS:
        load_platform(hass, component, DOMAIN, {}, config)

    return True
