import logging

import voluptuous as vol
from datetime import timedelta

from .APSystemsECUR import APSystemsECUR, APSystemsInvalidData
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

CONF_INTERVAL = "interval"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN : vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_INTERVAL) : cv.time_period_seconds
    })
}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [ "sensor" ]

async def async_setup(hass, config):
    """ Setup the APsystems platform """
    hass.data.setdefault(DOMAIN, {})

    host = config[DOMAIN].get(CONF_HOST)
    interval = config[DOMAIN].get(CONF_INTERVAL)
    if not interval:
        interval = timedelta(seconds=60)

    ecu = APSystemsECUR(host)

    async def async_update_data():
        _LOGGER.debug(f"Querying ECU data")
        try:
            data = await hass.async_add_executor_job(ecu.query_ecu)
        except APSystemsInvalidData as err:
            msg = f"Using cached data from last successful communication from ECU. Error: {err})"
            _LOGGER.warning(msg)
            data = ecu.last_data
        except Exception as err:
            msg = f"Using cached data from last successful communication from ECU. Error: {err})"
            _LOGGER.warning(msg)
            data = ecu.last_data

        return data

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=async_update_data,
            update_interval=interval,
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }

    for component in PLATFORMS:
        load_platform(hass, component, DOMAIN, {}, config)

    return True
