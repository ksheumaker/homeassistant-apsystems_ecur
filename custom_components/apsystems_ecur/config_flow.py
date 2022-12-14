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

from .const import DOMAIN, CONF_SSID, CONF_WPA_PSK, CONF_CACHE

@config_entries.HANDLERS.register(DOMAIN)
class APSsystemsFlowHandler(config_entries.ConfigFlow):

    VERSION = 1
    #connection classes are deprecated since 2021.6.0
    #CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        _LOGGER.debug("Starting config flow class...")

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Starting step_user")
        errors = {}
        if user_input is not None:
            _LOGGER.debug("User Input is not none")
            try:
                ap_ecu = APSystemsSocket(user_input["host"])

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

        _LOGGER.debug("Returning to show form")
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_SCAN_INTERVAL, default=300): int,
                    vol.Optional(CONF_CACHE, default=5): int,
                    vol.Optional(CONF_SSID, default=ECU-WIFI_local): str,
                    vol.Optional(CONF_WPA_PSK, default=default): str,
                }
            )
        )

    async def async_step_import(self, user_input):
        _LOGGER.debug(f"Importing config for {user_input}")
        return await self.async_step_user(user_input)
        
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return APSsystemsOptionsFlowHandler(config_entry)


class APSsystemsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                ap_ecu = APSystemsSocket(user_input["host"])
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
                _LOGGER.warning(f"Unknown error occurred during setup: {err}")
                errors["host"] = "unknown"

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
                    vol.Optional(CONF_SCAN_INTERVAL, default=300, 
                        description={"suggested_value": self.config_entry.data.get(CONF_SCAN_INTERVAL)}): int,
                    vol.Optional(CONF_CACHE, default=5, 
                        description={"suggested_value": self.config_entry.data.get(CONF_CACHE)}): int,
                    vol.Optional(CONF_SSID, default="ECU-WiFi_SSID", 
                        description={"suggested_value": self.config_entry.data.get(CONF_SSID)}): str,
                    vol.Optional(CONF_WPA_PSK, default="myWiFipassword", 
                    description={"suggested_value": self.config_entry.data.get(CONF_WPA_PSK)}): str,
                }
            )
        )
