import logging

import voluptuous as vol
import traceback
from datetime import timedelta

from .APSystemsECUR import APSystemsECUR, APSystemsInvalidData
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({
        vol.Required(CONF_HOST): str,
        vol.Optional(
            CONF_SCAN_INTERVAL, 
            default=60
        ) : int
    })

@config_entries.HANDLERS.register(DOMAIN)
class APSsystemsFlowHandler(config_entries.ConfigFlow):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        _LOGGER.debug("Starting config flow class...")

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Starting step_user")
        errors = {}
        if user_input is not None:
            _LOGGER.debug("User Input is not none")
            try:
                ap_ecu = APSystemsECUR(user_input["host"])
                test_query = await ap_ecu.async_query_ecu()
                ecu_id = test_query.get("ecu_id", None)
                if ecu_id != None:
                    return self.async_create_entry(title=f"ECU: {ecu_id}", data=user_input)
                else:
                    errors["host"] = "no_ecuid"

            except APSystemsInvalidData as err:
                _LOGGER.exception(f"APSystemsInvalidData exception: {err}")
                errors["host"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception(f"Unhandled exception: {err}")
                errors["host"] = "unknown"

        _LOGGER.debug("Returning to show form")
        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    async def async_step_import(self, user_input):
        _LOGGER.debug(f"Importing config for {user_input}")
        return await self.async_step_user(user_input)

