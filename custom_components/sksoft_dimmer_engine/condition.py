"""Condition for SKSoft Dimmer Engine integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.helpers import config_validation as cv

from .const import ATTR_LIGHTS, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

CONDITION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIGHTS): cv.entity_ids,
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


async def async_condition_from_config(
    hass: HomeAssistant, config: dict
) -> bool:
    """Create a condition checker from config.

    Args:
        hass: Home Assistant instance.
        config: The condition configuration.

    Returns:
        True if at least one entity is in cycle dimming.

    """
    entity_ids = config[ATTR_LIGHTS]
    return is_cycle_dimming(hass, entity_ids)
