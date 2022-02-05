from __future__ import annotations

import logging
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_TOKEN}

from .const import (
    DOMAIN
)


_LOGGER = logging.getLogger(__name__)

async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: DeviceEntry
) -> dict:
    """Return diagnostics for a config entry."""

    _LOGGER.debug("Diagnostics being called")

    ecu = hass.data[DOMAIN].get("ecu")
    _LOGGER.debug(f"Diagnostics being called {ecu}")

    diag_data = {"entry": async_redact_data(ecu.ecu.dump_data(), TO_REDACT)}

    return diag_data

