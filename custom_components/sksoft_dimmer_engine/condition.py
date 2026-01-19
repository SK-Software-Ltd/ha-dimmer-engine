"""Condition for SKSoft Dimmer Engine integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.condition import (
    Condition,
    ConditionChecker,
    ConditionConfig,
)
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_LIGHTS, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

# Condition schema requires a list of lights
_OPTIONS_SCHEMA_DICT: dict[vol.Marker, Any] = {
    vol.Required(ATTR_LIGHTS): cv.entity_ids,
}

_CONDITION_SCHEMA = vol.Schema(
    {
        vol.Required("options"): _OPTIONS_SCHEMA_DICT,
    }
)


def is_cycle_dimming(hass: HomeAssistant, entity_ids: list[str]) -> bool:
    """Check if any of the given light entities are in cycle dimming.

    Args:
        hass: Home Assistant instance.
        entity_ids: List of entity IDs to check.

    Returns:
        True if at least one of the entities is currently in cycle dimming.

    """
    engine = hass.data.get(DOMAIN)
    if engine is None:
        LOGGER.debug(
            "Dimmer engine not found in hass.data, returning False for is_cycle_dimming"
        )
        return False

    return engine.is_cycle_dimming(entity_ids)


class IsCycleDimmingCondition(Condition):
    """Is Cycle Dimming condition."""

    _options: dict[str, Any]

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate config."""
        return cast(ConfigType, _CONDITION_SCHEMA(config))

    def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
        """Initialize condition."""
        super().__init__(hass, config)
        if config.options is None:
            raise ValueError("Condition config options cannot be None")
        self._options = config.options

    async def async_get_checker(self) -> ConditionChecker:
        """Return the condition checker function."""
        lights = self._options.get(ATTR_LIGHTS, [])

        def check_is_cycle_dimming(**kwargs: Any) -> bool:
            """Check if any light is in cycle dimming."""
            return is_cycle_dimming(self._hass, lights)

        return check_is_cycle_dimming


CONDITIONS: dict[str, type[Condition]] = {
    "is_cycle_dimming": IsCycleDimmingCondition,
}


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type[Condition]]:
    """Return the available conditions for this integration."""
    return CONDITIONS
