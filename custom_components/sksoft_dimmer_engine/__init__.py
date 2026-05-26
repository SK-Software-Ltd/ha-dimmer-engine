"""SKSoft Dimmer Engine integration for Home Assistant.

This integration provides a sine-wave, time-based brightness cycling engine
for one or more Light entities, running a single shared async loop, plus a
parallel CCW (color temperature) cycling engine.

Module layout:
- ``engine.py``     : :class:`DimmerEngine` (brightness cycling)
- ``ccw_engine.py`` : :class:`CCWCycleEngine` (color temperature cycling)
- ``__init__.py``   : setup/teardown, service registration, runtime_data wiring
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .ccw_engine import CCWCycleEngine
from .const import (
    ATTR_LIGHTS,
    ATTR_MAX_BRIGHTNESS,
    ATTR_MAX_COLOR_TEMP,
    ATTR_MIN_BRIGHTNESS,
    ATTR_MIN_COLOR_TEMP,
    ATTR_MIN_DELTA,
    ATTR_PERIOD_S,
    ATTR_PHASE_MODE,
    ATTR_PHASE_OFFSET,
    ATTR_SYNC_GROUP,
    ATTR_TICK_S,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MAX_COLOR_TEMP,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MIN_COLOR_TEMP,
    DEFAULT_MIN_DELTA,
    DEFAULT_PERIOD_S,
    DEFAULT_PHASE_MODE,
    DEFAULT_PHASE_OFFSET,
    DEFAULT_SYNC_GROUP,
    DEFAULT_TICK_S,
    DOMAIN,
    PHASE_MODES,
    SERVICE_START,
    SERVICE_START_CCW,
    SERVICE_STATUS,
    SERVICE_STOP,
    SERVICE_STOP_ALL,
    SERVICE_STOP_ALL_CCW,
    SERVICE_STOP_CCW,
)
from .engine import DimmerEngine

LOGGER = logging.getLogger(__name__)

# Log at module load time to help debug integration loading issues
LOGGER.debug("SKSoft Dimmer Engine __init__ module loaded, DOMAIN=%s", DOMAIN)


class DimmerEngineData(TypedDict):
    """Runtime data attached to the config entry."""

    engine: DimmerEngine
    ccw_engine: CCWCycleEngine


# Typed alias for our config entry — its ``runtime_data`` is a
# :class:`DimmerEngineData` once :func:`async_setup_entry` has run.
type DimmerEngineConfigEntry = ConfigEntry[DimmerEngineData]


def _validate_brightness_range(data: dict) -> dict:
    """Validate that min_brightness is less than max_brightness."""
    min_b = data.get(ATTR_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS)
    max_b = data.get(ATTR_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS)
    if min_b >= max_b:
        raise vol.Invalid(
            f"min_brightness ({min_b}) must be less than max_brightness ({max_b})"
        )
    return data


# Service schemas
SERVICE_START_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_LIGHTS): cv.entity_ids,
            vol.Optional(ATTR_PERIOD_S, default=DEFAULT_PERIOD_S): vol.Coerce(float),
            vol.Optional(ATTR_TICK_S, default=DEFAULT_TICK_S): vol.Coerce(float),
            vol.Optional(ATTR_MIN_BRIGHTNESS, default=DEFAULT_MIN_BRIGHTNESS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=255)
            ),
            vol.Optional(ATTR_MAX_BRIGHTNESS, default=DEFAULT_MAX_BRIGHTNESS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=255)
            ),
            vol.Optional(ATTR_PHASE_MODE, default=DEFAULT_PHASE_MODE): vol.In(
                PHASE_MODES
            ),
            vol.Optional(ATTR_PHASE_OFFSET, default=DEFAULT_PHASE_OFFSET): vol.Coerce(
                float
            ),
            vol.Optional(ATTR_SYNC_GROUP, default=DEFAULT_SYNC_GROUP): cv.boolean,
            vol.Optional(ATTR_MIN_DELTA, default=DEFAULT_MIN_DELTA): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=255)
            ),
        }
    ),
    _validate_brightness_range,
)

SERVICE_STOP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIGHTS): cv.entity_ids,
    }
)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


def _validate_color_temp_range(data: dict) -> dict:
    """Validate that min_color_temp is less than max_color_temp."""
    min_ct = data.get(ATTR_MIN_COLOR_TEMP, DEFAULT_MIN_COLOR_TEMP)
    max_ct = data.get(ATTR_MAX_COLOR_TEMP, DEFAULT_MAX_COLOR_TEMP)
    if min_ct >= max_ct:
        raise vol.Invalid(
            f"min_color_temp ({min_ct}) must be less than max_color_temp ({max_ct})"
        )
    return data


# CCW (Color Temperature) cycling service schemas
SERVICE_START_CCW_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_LIGHTS): cv.entity_ids,
            vol.Optional(ATTR_PERIOD_S, default=DEFAULT_PERIOD_S): vol.Coerce(float),
            vol.Optional(ATTR_TICK_S, default=DEFAULT_TICK_S): vol.Coerce(float),
            vol.Optional(ATTR_MIN_COLOR_TEMP, default=DEFAULT_MIN_COLOR_TEMP): vol.All(
                vol.Coerce(int), vol.Range(min=1000, max=10000)
            ),
            vol.Optional(ATTR_MAX_COLOR_TEMP, default=DEFAULT_MAX_COLOR_TEMP): vol.All(
                vol.Coerce(int), vol.Range(min=1000, max=10000)
            ),
            vol.Optional(ATTR_PHASE_MODE, default=DEFAULT_PHASE_MODE): vol.In(
                PHASE_MODES
            ),
            vol.Optional(ATTR_PHASE_OFFSET, default=DEFAULT_PHASE_OFFSET): vol.Coerce(
                float
            ),
            vol.Optional(ATTR_SYNC_GROUP, default=DEFAULT_SYNC_GROUP): cv.boolean,
            vol.Optional(ATTR_MIN_DELTA, default=DEFAULT_MIN_DELTA): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=255)
            ),
        }
    ),
    _validate_color_temp_range,
)


def _get_engines(hass: HomeAssistant) -> tuple[DimmerEngine | None, CCWCycleEngine | None]:
    """Return ``(engine, ccw_engine)`` from the (single) loaded config entry.

    Returns ``(None, None)`` when no config entry is loaded yet — service calls
    in that window are no-ops with a warning.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        data = getattr(entry, "runtime_data", None)
        if data is not None:
            return data["engine"], data["ccw_engine"]
    return None, None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SKSoft Dimmer Engine integration.

    Registers domain-scoped services exactly once. The engines themselves are
    created per config entry in :func:`async_setup_entry` and exposed via
    ``entry.runtime_data``.
    """

    async def handle_start(call: ServiceCall) -> None:
        """Handle the start service call."""
        engine, _ = _get_engines(hass)
        if engine is None:
            LOGGER.warning("sksoft_dimmer_engine.start called but no entry is loaded")
            return
        await engine.async_start(
            lights=call.data[ATTR_LIGHTS],
            period_s=call.data[ATTR_PERIOD_S],
            tick_s=call.data[ATTR_TICK_S],
            min_brightness=call.data[ATTR_MIN_BRIGHTNESS],
            max_brightness=call.data[ATTR_MAX_BRIGHTNESS],
            phase_mode=call.data[ATTR_PHASE_MODE],
            phase_offset=call.data[ATTR_PHASE_OFFSET],
            sync_group=call.data[ATTR_SYNC_GROUP],
            min_delta=call.data[ATTR_MIN_DELTA],
        )

    async def handle_stop(call: ServiceCall) -> None:
        """Handle the stop service call."""
        engine, _ = _get_engines(hass)
        if engine is None:
            LOGGER.warning("sksoft_dimmer_engine.stop called but no entry is loaded")
            return
        await engine.async_stop(lights=call.data[ATTR_LIGHTS])

    async def handle_stop_all(call: ServiceCall) -> None:
        """Handle the stop_all service call."""
        engine, _ = _get_engines(hass)
        if engine is None:
            LOGGER.warning(
                "sksoft_dimmer_engine.stop_all called but no entry is loaded"
            )
            return
        await engine.async_stop_all()

    async def handle_status(call: ServiceCall) -> None:
        """Handle the status service call."""
        engine, ccw_engine = _get_engines(hass)
        if engine is None or ccw_engine is None:
            LOGGER.warning("sksoft_dimmer_engine.status called but no entry is loaded")
            return
        LOGGER.info("Dimmer Engine Status: %s", engine.get_status())
        LOGGER.info("CCW Cycle Engine Status: %s", ccw_engine.get_status())

    async def handle_start_ccw(call: ServiceCall) -> None:
        """Handle the start_ccw service call."""
        _, ccw_engine = _get_engines(hass)
        if ccw_engine is None:
            LOGGER.warning(
                "sksoft_dimmer_engine.start_ccw called but no entry is loaded"
            )
            return
        await ccw_engine.async_start(
            lights=call.data[ATTR_LIGHTS],
            period_s=call.data[ATTR_PERIOD_S],
            tick_s=call.data[ATTR_TICK_S],
            min_color_temp=call.data[ATTR_MIN_COLOR_TEMP],
            max_color_temp=call.data[ATTR_MAX_COLOR_TEMP],
            phase_mode=call.data[ATTR_PHASE_MODE],
            phase_offset=call.data[ATTR_PHASE_OFFSET],
            sync_group=call.data[ATTR_SYNC_GROUP],
            min_delta=call.data[ATTR_MIN_DELTA],
        )

    async def handle_stop_ccw(call: ServiceCall) -> None:
        """Handle the stop_ccw service call."""
        _, ccw_engine = _get_engines(hass)
        if ccw_engine is None:
            LOGGER.warning(
                "sksoft_dimmer_engine.stop_ccw called but no entry is loaded"
            )
            return
        await ccw_engine.async_stop(lights=call.data[ATTR_LIGHTS])

    async def handle_stop_all_ccw(call: ServiceCall) -> None:
        """Handle the stop_all_ccw service call."""
        _, ccw_engine = _get_engines(hass)
        if ccw_engine is None:
            LOGGER.warning(
                "sksoft_dimmer_engine.stop_all_ccw called but no entry is loaded"
            )
            return
        await ccw_engine.async_stop_all()

    # Register brightness dimmer services (idempotent — async_setup is one-time)
    hass.services.async_register(
        DOMAIN, SERVICE_START, handle_start, schema=SERVICE_START_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, handle_stop, schema=SERVICE_STOP_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_ALL, handle_stop_all)
    hass.services.async_register(DOMAIN, SERVICE_STATUS, handle_status)

    # Register CCW services
    hass.services.async_register(
        DOMAIN, SERVICE_START_CCW, handle_start_ccw, schema=SERVICE_START_CCW_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_CCW, handle_stop_ccw, schema=SERVICE_STOP_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_ALL_CCW, handle_stop_all_ccw)

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: DimmerEngineConfigEntry
) -> bool:
    """Set up SKSoft Dimmer Engine from a config entry."""
    # Initialize brightness dimmer engine
    engine = DimmerEngine(hass)
    # Initialize CCW (Color Temperature) cycle engine
    ccw_engine = CCWCycleEngine(hass)

    # Store both engines on the entry's runtime_data (replaces hass.data[DOMAIN])
    entry.runtime_data = DimmerEngineData(engine=engine, ccw_engine=ccw_engine)

    # Load persisted registries
    await engine.async_load()
    await ccw_engine.async_load()

    # Register shutdown handler tied to this entry
    async def async_shutdown_handler(event: Any) -> None:
        """Handle Home Assistant stop event."""
        await engine.async_shutdown()
        await ccw_engine.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once("homeassistant_stop", async_shutdown_handler)
    )

    LOGGER.info("SKSoft Dimmer Engine integration loaded")
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: DimmerEngineConfigEntry
) -> bool:
    """Unload a config entry."""
    data: DimmerEngineData | None = getattr(entry, "runtime_data", None)
    if data is not None:
        await data["engine"].async_shutdown()
        await data["ccw_engine"].async_shutdown()

    # Services are owned by async_setup and survive entry reloads — do not
    # unregister them here.
    return True
