"""Condition platform for SKSoft Dimmer Engine integration.

Provides two conditions implemented against the Home Assistant 2026.x
condition API (``homeassistant.helpers.condition``):
``is_cycle_dimming`` and ``is_ccw_cycling``. Each condition is configured
with a list of light entity ids and returns True when at least one of those
lights is currently being driven by the corresponding engine.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Unpack, cast

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.condition import (
    Condition,
    ConditionChecker,
    ConditionCheckParams,
    ConditionConfig,
)
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_LIGHTS, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .ccw_engine import CCWCycleEngine
    from .engine import DimmerEngine

LOGGER = logging.getLogger(__name__)

_OPTIONS_SCHEMA_DICT: dict[vol.Marker, Any] = {
    vol.Required(ATTR_LIGHTS): cv.entity_ids,
}

_CONDITION_SCHEMA = vol.Schema(
    {
        vol.Required("options"): _OPTIONS_SCHEMA_DICT,
    }
)


def _find_engines(
    hass: HomeAssistant,
) -> tuple[DimmerEngine | None, CCWCycleEngine | None]:
    """Locate the dimmer and CCW engines from any loaded config entry.

    The integration stores both engines on ``ConfigEntry.runtime_data`` in
    :func:`custom_components.sksoft_dimmer_engine.async_setup_entry`. This
    helper walks the loaded entries for our domain and returns the first
    pair it finds, or ``(None, None)`` when no entry is loaded yet.
    """
    for entry in hass.config_entries.async_entries(DOMAIN):
        data = getattr(entry, "runtime_data", None)
        if data is not None:
            return data["engine"], data["ccw_engine"]
    return None, None


def is_cycle_dimming(hass: HomeAssistant, entity_ids: list[str]) -> bool:
    """Return True when at least one of ``entity_ids`` is in cycle dimming."""
    engine, _ = _find_engines(hass)
    if engine is None:
        LOGGER.debug("Dimmer engine not loaded; returning False for is_cycle_dimming")
        return False
    return engine.is_cycle_dimming(entity_ids)


def is_ccw_cycling(hass: HomeAssistant, entity_ids: list[str]) -> bool:
    """Return True when at least one of ``entity_ids`` is in CCW cycling."""
    _, ccw_engine = _find_engines(hass)
    if ccw_engine is None:
        LOGGER.debug("CCW engine not loaded; returning False for is_ccw_cycling")
        return False
    return ccw_engine.is_ccw_cycling(entity_ids)


class IsCycleDimmingCondition(Condition):
    """Condition: any configured light is currently in cycle dimming."""

    _options: dict[str, Any]
    _entity_ids: list[str]

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate condition config."""
        return cast(ConfigType, _CONDITION_SCHEMA(config))

    def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
        """Initialize the condition from its parsed config."""
        super().__init__(hass, config)
        if config.options is None:
            raise ValueError("Condition config options cannot be None")
        self._options = config.options
        self._entity_ids = list(self._options.get(ATTR_LIGHTS, []))

    async def async_get_checker(self) -> ConditionChecker:
        """Return the condition checker callable."""
        entity_ids = self._entity_ids
        hass = self._hass

        def check_is_cycle_dimming(
            **kwargs: Unpack[ConditionCheckParams],
        ) -> bool:
            return is_cycle_dimming(hass, entity_ids)

        return check_is_cycle_dimming


class IsCCWCyclingCondition(Condition):
    """Condition: any configured light is currently in CCW cycling."""

    _options: dict[str, Any]
    _entity_ids: list[str]

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate condition config."""
        return cast(ConfigType, _CONDITION_SCHEMA(config))

    def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
        """Initialize the condition from its parsed config."""
        super().__init__(hass, config)
        if config.options is None:
            raise ValueError("Condition config options cannot be None")
        self._options = config.options
        self._entity_ids = list(self._options.get(ATTR_LIGHTS, []))

    async def async_get_checker(self) -> ConditionChecker:
        """Return the condition checker callable."""
        entity_ids = self._entity_ids
        hass = self._hass

        def check_is_ccw_cycling(
            **kwargs: Unpack[ConditionCheckParams],
        ) -> bool:
            return is_ccw_cycling(hass, entity_ids)

        return check_is_ccw_cycling


CONDITIONS: dict[str, type[Condition]] = {
    "is_cycle_dimming": IsCycleDimmingCondition,
    "is_ccw_cycling": IsCCWCyclingCondition,
}


async def async_get_conditions(
    hass: HomeAssistant,
) -> dict[str, type[Condition]]:
    """Return the conditions provided by this integration."""
    return CONDITIONS
