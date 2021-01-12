import logging

import voluptuous as vol
import traceback
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

PLATFORMS = [ "sensor", "binary_sensor" ]


## handle all the communications with the ECUR class and deal with our need for caching, etc
class ECUR():

    def __init__(self, ipaddr):
        self.ecu = APsystemsECUR(ipaddr)
        self.cache_count = 0
        self.cache_max = 5
        self.data_from_cache = False
        self.querying = True
        self.error_messge = ""
        self.cached_data = {}

    def stop_query(self):
        self.querying = False

    def start_query(self):
        self.querying = True

    async def update(self):
        data = {}

        # if we aren't actively quering data, pull data form the cache
        # this is so we can stop querying after sunset
        if not self.querying:

            _LOGGER.warning("Not querying ECU due to stopped")
            data = self.cached_data
            self.data_from_cache = True

            data["data_from_cache"] = self.data_from_cache
            data["querying"] = self.querying
            return self.cached_data

        _LOGGER.warning("Querying ECU")
        try:
            data = await ecu.async_query_ecu()

            # we got good results, so we store it and set flags about our
            # cache state
            self.cached_data = data
            self.cache_count = 0
            self.data_from_cache = False
            self.error_message = ""

        except APSystemsInvalidData as err:

            msg = f"Using cached data from last successful communication from ECU. Error: {err}"
            _LOGGER.warning(msg)

            # we got invalid data, so we need to pull from cache
            self.error_msg = msg
            self.cache_count += 1
            self.data_from_cache = True
            data = self.cached_data

            if self.cache_count > self.cache_max:
                raise Exception(f"Error using cached data for more than {self.cache_max} times.")

        except Exception as err:

            msg = f"Using cached data from last successful communication from ECU. Error: {err}"
            _LOGGER.warning(msg)

            # we got invalid data, so we need to pull from cache
            self.error_msg = msg
            self.cache_count += 1
            self.data_from_cache = True
            data = self.cached_data

            if self.cache_count > self.cache_max:
                raise Exception(f"Error using cached data for more than {self.cache_max} times.")

        data["data_from_cache"] = self.data_from_cache
        data["querying"] = self.querying
        return data

async def async_setup(hass, config):
    """ Setup the APsystems platform """
    hass.data.setdefault(DOMAIN, {})

    host = config[DOMAIN].get(CONF_HOST)
    interval = config[DOMAIN].get(CONF_INTERVAL)
    if not interval:
        interval = timedelta(seconds=60)

    ecu = ECUR(host)

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=ecu.update,
            update_interval=interval,
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }

    def handle_stop_query(call):
        ecu.stop_query()
        await coordinator.async_request_refresh()

    def handle_start_query(call):
        ecu.start_query()
        await coordinator.async_request_refresh()

    hass.services.register(DOMAIN, "start_query", handle_start_query)
    hass.services.register(DOMAIN, "stop_query", handle_stop_query)

    for component in PLATFORMS:
        load_platform(hass, component, DOMAIN, {}, config)

    return True
