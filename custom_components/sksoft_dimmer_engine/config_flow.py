"""Config flow for SKSoft Dimmer Engine integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

# Log at module load time to help debug config flow issues
LOGGER.debug("SKSoft Dimmer Engine config_flow module loaded, DOMAIN=%s", DOMAIN)


class SKSoftDimmerEngineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SKSoft Dimmer Engine."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        LOGGER.debug(
            "async_step_user called, user_input_provided=%s",
            user_input is not None,
        )
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            LOGGER.info("Creating config entry for SKSoft Dimmer Engine")
            return self.async_create_entry(title="SKSoft Dimmer Engine", data={})

        LOGGER.debug("Showing config form for SKSoft Dimmer Engine")
        return self.async_show_form(step_id="user")
