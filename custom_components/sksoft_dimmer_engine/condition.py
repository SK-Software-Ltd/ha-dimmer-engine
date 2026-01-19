"""Condition for SKSoft Dimmer Engine integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


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
