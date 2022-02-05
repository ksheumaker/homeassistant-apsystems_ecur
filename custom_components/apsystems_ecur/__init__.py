import logging

import voluptuous as vol
import traceback
from datetime import timedelta

from .APSystemsECUR import APSystemsECUR, APSystemsInvalidData, APSystemsInvalidInverter
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant import config_entries, exceptions
from homeassistant.helpers import device_registry as dr

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN

PLATFORMS = [ "sensor", "binary_sensor", "switch" ]

## handle all the communications with the ECUR class and deal with our need for caching, etc
class ECUR():

    def __init__(self, ipaddr):
        self.ecu = APSystemsECUR(ipaddr)
        self.cache_count = 0
        self.cache_max = 5
        self.data_from_cache = False
        self.querying = True
        self.error_messge = ""
        self.cached_data = {}

    async def stop_query(self):
        self.querying = False

    async def start_query(self):
        self.querying = True

    def use_cached_data(self, msg):
        # we got invalid data, so we need to pull from cache
        self.error_msg = msg
        self.cache_count += 1
        self.data_from_cache = True

        if self.cache_count > self.cache_max:
            raise UpdateFailed(f"Error using cached data for more than {self.cache_max} times.")

        if self.cached_data.get("ecu_id", None) == None:
            _LOGGER.debug(f"Cached data {self.cached_data}")
            raise UpdateFailed(f"Cached data doesn't contain a valid ecu_id")

        return self.cached_data

    async def update(self):
        data = {}

        # if we aren't actively quering data, pull data form the cache
        # this is so we can stop querying after sunset
        if not self.querying:

            _LOGGER.debug("Not querying ECU due to query=False")
            data = self.cached_data
            self.data_from_cache = True

            data["data_from_cache"] = self.data_from_cache
            data["querying"] = self.querying
            return self.cached_data

        _LOGGER.debug("Querying ECU")
        try:
            data = await self.ecu.async_query_ecu()
            _LOGGER.debug("Got data from ECU")

            # we got good results, so we store it and set flags about our
            # cache state
            if data["ecu_id"] != None:
                self.cached_data = data
                self.cache_count = 0
                self.data_from_cache = False
                self.error_message = ""
            else:
                msg = f"Using cached data from last successful communication from ECU. Error: no ecu_id returned"
                _LOGGER.warning(msg)
                data = self.use_cached_data(msg)

        except APSystemsInvalidData as err:

            msg = f"Using cached data from last successful communication from ECU. Error: {err}"
            _LOGGER.warning(msg)
            data = self.use_cached_data(msg)

        except Exception as err:

            msg = f"Using cached data from last successful communication from ECU. Error: {err}"
            _LOGGER.warning(msg)
            data = self.use_cached_data(msg)

        data["data_from_cache"] = self.data_from_cache
        data["querying"] = self.querying
        _LOGGER.debug(f"Returning {data}")

        if data.get("ecu_id", None) == None:
            raise UpdateFailed(f"Somehow data doesn't contain a valid ecu_id")
            
        return data

async def async_setup(hass, config):

    # the integration has already moved to config flow
    if config.get(DOMAIN) is None:
        return True

    config_file_host = config[DOMAIN].get(CONF_HOST, None)
    config_file_scan_interval = config[DOMAIN].get(CONF_SCAN_INTERVAL, 60)

    _LOGGER.debug(f"Config: {config[DOMAIN]}")

    # a host hasn't been defined in the config file
    if not config_file_host:
        return False

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == config_entries.SOURCE_IMPORT:
            _LOGGER.error("apsystems_ecur already imported config, remove it from configuration.yaml")
            return True

    import_config = { CONF_HOST : config_file_host, CONF_SCAN_INTERVAL : config_file_scan_interval }
    _LOGGER.debug(f"Importing config from configuration.yaml {import_config}")

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=import_config
        )
    )

    _LOGGER.debug(f"Task spawned")
    return True


async def async_setup_entry(hass, config):
    """ Setup the APsystems platform """
    
    _LOGGER.debug(f"config={config.data}")

    hass.data.setdefault(DOMAIN, {})

    host = config.data[CONF_HOST]
    interval = timedelta(seconds=config.data[CONF_SCAN_INTERVAL])

    ecu = ECUR(host)

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=ecu.update,
            update_interval=interval,
    )

    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }
    await coordinator.async_config_entry_first_refresh()

    #async def handle_stop_query(call):
        #await ecu.stop_query()
        #coordinator.async_refresh()

    #async def handle_start_query(call):
        #await ecu.start_query()
        #coordinator.async_refresh()


    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=config.entry_id,
        identifiers={(DOMAIN, f"ecu_{ecu.ecu.ecu_id}")},
        manufacturer="APSystems",
        suggested_area="Roof",
        name=f"ECU {ecu.ecu.ecu_id}",
        model=ecu.ecu.firmware,
        sw_version=ecu.ecu.firmware,
    )

    inverters = coordinator.data.get("inverters", {})
    for uid,inv_data in inverters.items():
        model = inv_data.get("model", "Inverter")
        device_registry.async_get_or_create(
            config_entry_id=config.entry_id,
            identifiers={(DOMAIN, f"inverter_{uid}")},
            manufacturer="APSystems",
            suggested_area="Roof",
            name=f"Inverter {uid}",
            model=inv_data.get("model")
        )

    hass.config_entries.async_setup_platforms(config, PLATFORMS)

    return True

async def async_unload_entry(hass, config):
    unload_ok = await hass.config_entries.async_unload_platforms(config, PLATFORMS)
    coordinator = hass.data[DOMAIN].get("coordinator")
    ecu = hass.data[DOMAIN].get("ecu")

    await ecu.stop_query()

    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)

    return unload_ok
