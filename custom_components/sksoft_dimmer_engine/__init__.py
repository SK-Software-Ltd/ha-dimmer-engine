"""SKSoft Dimmer Engine integration for Home Assistant.

This integration provides a sine-wave, time-based brightness cycling engine
for one or more Light entities, running a single shared async loop.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.const import (
    ATTR_BRIGHTNESS,
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_LIGHTS,
    ATTR_MAX_BRIGHTNESS,
    ATTR_MIN_BRIGHTNESS,
    ATTR_MIN_DELTA,
    ATTR_PERIOD_S,
    ATTR_PHASE_MODE,
    ATTR_PHASE_OFFSET,
    ATTR_SYNC_GROUP,
    ATTR_TICK_S,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MIN_DELTA,
    DEFAULT_PERIOD_S,
    DEFAULT_PHASE_MODE,
    DEFAULT_PHASE_OFFSET,
    DEFAULT_SYNC_GROUP,
    DEFAULT_TICK_S,
    DOMAIN,
    PHASE_MODE_ABSOLUTE,
    PHASE_MODE_SYNC_TO_CURRENT,
    PHASE_MODES,
    REG_MAX_B,
    REG_MIN_B,
    REG_MIN_DELTA,
    REG_PERIOD,
    REG_PHASE_MODE,
    REG_PHASE_OFFSET,
    REG_STARTED_AT_TS,
    REG_SYNC_GROUP,
    REG_TICK,
    SERVICE_START,
    SERVICE_STATUS,
    SERVICE_STOP,
    SERVICE_STOP_ALL,
)
from .storage import DimmerEngineStore

if TYPE_CHECKING:
    pass

LOGGER = logging.getLogger(__name__)

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


class DimmerEngine:
    """Class to manage the dimmer engine loop and registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the dimmer engine."""
        self.hass = hass
        self._registry: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._store = DimmerEngineStore(hass)
        self._running = False

    async def async_load(self) -> None:
        """Load registry from storage and start loop if needed."""
        async with self._lock:
            self._registry = await self._store.async_load()
            if self._registry:
                LOGGER.info(
                    "Restored %d lights from storage: %s",
                    len(self._registry),
                    list(self._registry.keys()),
                )
                self._ensure_loop_running()

    async def async_save(self) -> None:
        """Save registry to storage."""
        await self._store.async_save(self._registry)

    async def async_shutdown(self) -> None:
        """Shutdown the engine cleanly."""
        async with self._lock:
            self._running = False
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            await self.async_save()
            LOGGER.info("Dimmer engine shutdown complete")

    def _compute_phase_offset_for_brightness(
        self, current_brightness: int, min_b: int, max_b: int, period: float
    ) -> float:
        """Compute phase offset so sine matches current brightness at t=0."""
        mid = (min_b + max_b) / 2
        amp = (max_b - min_b) / 2

        if amp == 0:
            return 0.0

        # Clamp to valid range for asin
        normalized = (current_brightness - mid) / amp
        normalized = max(-1.0, min(1.0, normalized))

        # asin gives us the phase where sin(phase) = normalized
        # We want the phase at t=0, so offset = asin(normalized)
        return math.asin(normalized)

    async def async_start(
        self,
        lights: list[str],
        period_s: float,
        tick_s: float,
        min_brightness: int,
        max_brightness: int,
        phase_mode: str,
        phase_offset: float,
        sync_group: bool,
        min_delta: int,
    ) -> None:
        """Start dimming for the specified lights."""
        async with self._lock:
            now = time.time()
            computed_offset: float | None = None

            for i, entity_id in enumerate(lights):
                # Determine phase offset based on mode
                if phase_mode == PHASE_MODE_SYNC_TO_CURRENT:
                    if sync_group and computed_offset is not None:
                        # Reuse computed offset from first light
                        offset = computed_offset
                    else:
                        # Compute offset from current brightness
                        state = self.hass.states.get(entity_id)
                        current_brightness = DEFAULT_MIN_BRIGHTNESS
                        if state and state.attributes.get(ATTR_BRIGHTNESS):
                            current_brightness = int(
                                state.attributes.get(ATTR_BRIGHTNESS)
                            )
                        offset = self._compute_phase_offset_for_brightness(
                            current_brightness,
                            min_brightness,
                            max_brightness,
                            period_s,
                        )
                        if sync_group and i == 0:
                            computed_offset = offset
                elif phase_mode == PHASE_MODE_ABSOLUTE:
                    offset = phase_offset
                else:  # PHASE_MODE_RELATIVE
                    offset = phase_offset

                self._registry[entity_id] = {
                    REG_PERIOD: period_s,
                    REG_TICK: tick_s,
                    REG_MIN_B: min_brightness,
                    REG_MAX_B: max_brightness,
                    REG_PHASE_OFFSET: offset,
                    REG_MIN_DELTA: min_delta,
                    REG_STARTED_AT_TS: now,
                    REG_PHASE_MODE: phase_mode,
                    REG_SYNC_GROUP: sync_group,
                }
                LOGGER.info(
                    "Started dimmer engine for %s: period=%.2fs, brightness=[%d,%d], "
                    "phase_mode=%s, offset=%.4f",
                    entity_id,
                    period_s,
                    min_brightness,
                    max_brightness,
                    phase_mode,
                    offset,
                )

            await self.async_save()
            self._ensure_loop_running()

    async def async_stop(self, lights: list[str]) -> None:
        """Stop dimming for the specified lights."""
        async with self._lock:
            for entity_id in lights:
                if entity_id in self._registry:
                    del self._registry[entity_id]
                    LOGGER.info("Stopped dimmer engine for %s", entity_id)
                else:
                    LOGGER.warning(
                        "Light %s was not in dimmer engine registry", entity_id
                    )

            await self.async_save()

            # Stop the loop immediately if registry is now empty
            if not self._registry:
                self._stop_loop()

    async def async_stop_all(self) -> None:
        """Stop dimming for all lights."""
        async with self._lock:
            count = len(self._registry)
            self._registry.clear()
            await self.async_save()
            LOGGER.info("Stopped dimmer engine for all %d lights", count)

            # Stop the loop immediately
            self._stop_loop()

    def _stop_loop(self) -> None:
        """Stop the background loop task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            LOGGER.debug("Cancelled dimmer engine loop task")

    def get_status(self) -> dict[str, Any]:
        """Get the current registry status."""
        return {
            "active_lights": len(self._registry),
            "loop_running": self._task is not None and not self._task.done(),
            "registry": {k: dict(v) for k, v in self._registry.items()},
        }

    @callback
    def _ensure_loop_running(self) -> None:
        """Ensure the background loop task is running."""
        if self._task is None or self._task.done():
            self._running = True
            self._task = self.hass.async_create_task(
                self._run_loop(), "sksoft_dimmer_engine_loop"
            )
            LOGGER.debug("Started dimmer engine loop task")

    async def _run_loop(self) -> None:
        """Main loop that updates all lights."""
        LOGGER.debug("Dimmer engine loop started")

        while self._running:
            async with self._lock:
                if not self._registry:
                    LOGGER.debug("Registry empty, stopping loop")
                    break

                # Find the minimum tick interval
                min_tick = min(
                    entry[REG_TICK] for entry in self._registry.values()
                )

                now = time.time()

                # Process all lights
                for entity_id, entry in list(self._registry.items()):
                    await self._update_light(entity_id, entry, now)

            # Sleep for the minimum tick interval
            await asyncio.sleep(min_tick)

        LOGGER.debug("Dimmer engine loop ended")

    async def _update_light(
        self, entity_id: str, entry: dict[str, Any], now: float
    ) -> None:
        """Update a single light's brightness."""
        period = entry[REG_PERIOD]
        min_b = entry[REG_MIN_B]
        max_b = entry[REG_MAX_B]
        phase_offset = entry[REG_PHASE_OFFSET]
        min_delta = entry[REG_MIN_DELTA]
        started_at = entry[REG_STARTED_AT_TS]

        # Calculate elapsed time
        elapsed = now - started_at

        # Calculate phase
        time_phase = (2 * math.pi * elapsed) / period

        # All phase modes use the same formula: phase = time_phase + offset
        # The difference is how the offset was computed when the light was registered:
        # - sync_to_current: offset computed from current brightness using asin
        # - absolute: offset provided directly by user
        # - relative: offset provided by user, added to time-based phase
        phase = time_phase + phase_offset

        # Calculate target brightness using sine wave
        mid = (min_b + max_b) / 2
        amp = (max_b - min_b) / 2
        target = round(mid + amp * math.sin(phase))

        # Clamp to valid range
        target = max(min_b, min(max_b, target))

        # Get current brightness
        state = self.hass.states.get(entity_id)
        if state is None:
            LOGGER.warning("Entity %s not found, removing from registry", entity_id)
            if entity_id in self._registry:
                del self._registry[entity_id]
            return

        current_brightness = state.attributes.get(ATTR_BRIGHTNESS, 0)
        if current_brightness is None:
            current_brightness = 0

        # Only update if delta is significant enough
        if abs(target - current_brightness) >= min_delta:
            LOGGER.debug(
                "Updating %s: brightness %d -> %d (phase=%.2f)",
                entity_id,
                current_brightness,
                target,
                phase,
            )
            await self.hass.services.async_call(
                "light",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: target},
                blocking=False,
            )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SKSoft Dimmer Engine integration."""
    engine = DimmerEngine(hass)
    hass.data[DOMAIN] = engine

    # Load persisted registry
    await engine.async_load()

    # Register shutdown handler
    async def async_shutdown_handler(event: Any) -> None:
        """Handle shutdown."""
        await engine.async_shutdown()

    hass.bus.async_listen_once("homeassistant_stop", async_shutdown_handler)

    # Register services
    async def handle_start(call: ServiceCall) -> None:
        """Handle the start service call."""
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
        await engine.async_stop(lights=call.data[ATTR_LIGHTS])

    async def handle_stop_all(call: ServiceCall) -> None:
        """Handle the stop_all service call."""
        await engine.async_stop_all()

    async def handle_status(call: ServiceCall) -> None:
        """Handle the status service call."""
        status = engine.get_status()
        LOGGER.info("Dimmer Engine Status: %s", status)

    hass.services.async_register(
        DOMAIN, SERVICE_START, handle_start, schema=SERVICE_START_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, handle_stop, schema=SERVICE_STOP_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_ALL, handle_stop_all)
    hass.services.async_register(DOMAIN, SERVICE_STATUS, handle_status)

    LOGGER.info("SKSoft Dimmer Engine integration loaded")
    return True
