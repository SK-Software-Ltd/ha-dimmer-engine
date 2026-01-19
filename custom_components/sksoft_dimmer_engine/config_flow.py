"""Config flow for SKSoft Dimmer Engine integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class SKSoftDimmerEngineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SKSoft Dimmer Engine."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="SKSoft Dimmer Engine", data={})

        return self.async_show_form(step_id="user")
