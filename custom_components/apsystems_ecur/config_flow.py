import logging
import voluptuous as vol
import traceback
from datetime import timedelta
from homeassistant.core import callback
from .APSystemsSocket import APSystemsSocket, APSystemsInvalidData
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, CONF_SSID, CONF_WPA_PSK, CONF_CACHE, CONF_STOP_GRAPHS

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str,
                                    vol.Required(CONF_SCAN_INTERVAL, default=300): int,
                                    vol.Optional(CONF_CACHE, default=5): int,
                                    vol.Optional(CONF_SSID, default="ECU-WIFI_local"): str,
                                    vol.Optional(CONF_WPA_PSK, default="default"): str,
                                    vol.Optional(CONF_STOP_GRAPHS): bool,
                                    })

@config_entries.HANDLERS.register(DOMAIN)
class APSsystemsFlowHandler(config_entries.ConfigFlow):

    VERSION = 1
    def __init__(self):
        _LOGGER.debug("Starting config flow class...")

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Starting user step")
        errors = {}
        if user_input is None:
            _LOGGER.debug("Show form because user input is empty")
            return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )
        _LOGGER.debug("User input is not empty, processing input")
        try:
            _LOGGER.debug("Initial attempt to query ECU")
            ap_ecu = APSystemsSocket(user_input["host"], user_input["stop_graphs"])
            test_query = await self.hass.async_add_executor_job(ap_ecu.query_ecu)
            ecu_id = test_query.get("ecu_id", None)
            if ecu_id != None:
                return self.async_create_entry(title=f"ECU: {ecu_id}", data=user_input)
            else:
                errors["host"] = "no_ecuid"
        except APSystemsInvalidData as err:
            _LOGGER.exception(f"APSystemsInvalidData exception: {err}")
            errors["host"] = "cannot_connect"
        except Exception as err:
            _LOGGER.exception(f"Unknown error occurred during setup: {err}")
            errors["host"] = "unknown"
        
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        _LOGGER.debug("get options flow")
        return APSsystemsOptionsFlowHandler(config_entry)

class APSsystemsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        _LOGGER.debug("Starting options flow step class")
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is None:
            return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema({
                    vol.Required(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
                    vol.Optional(CONF_SCAN_INTERVAL, default=300, 
                        description={"suggested_value": self.config_entry.data.get(CONF_SCAN_INTERVAL)}): int,
                    vol.Optional(CONF_CACHE, default=5, 
                        description={"suggested_value": self.config_entry.data.get(CONF_CACHE)}): int,
                    vol.Optional(CONF_SSID, default="ECU-WiFi_SSID", 
                        description={"suggested_value": self.config_entry.data.get(CONF_SSID)}): str,
                    vol.Optional(CONF_WPA_PSK, default="myWiFipassword", 
                        description={"suggested_value": self.config_entry.data.get(CONF_WPA_PSK)}): str,
                    vol.Optional(CONF_STOP_GRAPHS, default=self.config_entry.data.get(CONF_STOP_GRAPHS)): bool
                    })
            )
        try:
            ap_ecu = APSystemsSocket(user_input["host"], user_input["stop_graphs"])
            _LOGGER.debug("Attempt to query ECU")
            test_query = await self.hass.async_add_executor_job(ap_ecu.query_ecu)
            ecu_id = test_query.get("ecu_id", None)
            if ecu_id != None:
                self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
                )
                coordinator = self.hass.data[DOMAIN].get("coordinator")
                coordinator.update_interval = timedelta(seconds=self.config_entry.data.get(CONF_SCAN_INTERVAL))
                return self.async_create_entry(title=f"ECU: {ecu_id}", data={})
            else:
                errors["host"] = "no_ecuid"
        except APSystemsInvalidData as err:
            errors["host"] = "cannot_connect"
        except Exception as err:
            _LOGGER.debug(f"Unknown error occurred during setup: {err}")
            errors["host"] = "unknown"
