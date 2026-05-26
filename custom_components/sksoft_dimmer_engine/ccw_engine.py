"""CCW (Color Temperature) cycle engine for the SKSoft Dimmer Engine integration.

Provides the :class:`CCWCycleEngine`, which runs a single shared async loop
that drives sine-wave color-temperature cycling for one or more Light entities.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from time import monotonic
from typing import Any

from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN, ATTR_TRANSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_ON
from homeassistant.core import HomeAssistant, callback

from .const import (
    DEFAULT_MIN_COLOR_TEMP,
    PHASE_MODE_ABSOLUTE,
    PHASE_MODE_SYNC_TO_CURRENT,
    REG_MAX_CT,
    REG_MIN_CT,
    REG_MIN_DELTA,
    REG_PERIOD,
    REG_PHASE_MODE,
    REG_PHASE_OFFSET,
    REG_STARTED_AT_TS,
    REG_SYNC_GROUP,
    REG_TICK,
)
from .storage import CCWCycleStore

LOGGER = logging.getLogger(__name__)


class CCWCycleEngine:
    """Class to manage the CCW (Color Temperature) cycle engine loop and registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the CCW cycle engine."""
        self.hass = hass
        self._registry: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._store = CCWCycleStore(hass)
        self._running = False

    async def async_load(self) -> None:
        """Load registry from storage and start loop if needed."""
        async with self._lock:
            self._registry = await self._store.async_load()
            if self._registry:
                LOGGER.info(
                    "Restored %d lights from CCW storage: %s",
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
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            await self.async_save()
            LOGGER.info("CCW cycle engine shutdown complete")

    def _compute_phase_offset_for_color_temp(
        self, current_ct: int, min_ct: int, max_ct: int, period: float
    ) -> float:
        """Compute phase offset so sine matches current color temp at t=0."""
        mid = (min_ct + max_ct) / 2
        amp = (max_ct - min_ct) / 2

        if amp == 0:
            return 0.0

        # Clamp to valid range for asin
        normalized = (current_ct - mid) / amp
        normalized = max(-1.0, min(1.0, normalized))

        # asin gives us the phase where sin(phase) = normalized
        # We want the phase at t=0, so offset = asin(normalized)
        return math.asin(normalized)

    async def async_start(
        self,
        lights: list[str],
        period_s: float,
        tick_s: float,
        min_color_temp: int,
        max_color_temp: int,
        phase_mode: str,
        phase_offset: float,
        sync_group: bool,
        min_delta: int,
    ) -> None:
        """Start CCW cycling for the specified lights."""
        async with self._lock:
            now = monotonic()
            computed_offset: float | None = None

            for i, entity_id in enumerate(lights):
                # Determine phase offset based on mode
                if phase_mode == PHASE_MODE_SYNC_TO_CURRENT:
                    if sync_group and computed_offset is not None:
                        # Reuse computed offset from first light
                        offset = computed_offset
                    else:
                        # Compute offset from current color temperature
                        state = self.hass.states.get(entity_id)
                        current_ct = DEFAULT_MIN_COLOR_TEMP
                        if state is not None:
                            ct_attr = state.attributes.get(ATTR_COLOR_TEMP_KELVIN)
                            if ct_attr is not None:
                                current_ct = int(ct_attr)
                        offset = self._compute_phase_offset_for_color_temp(
                            current_ct,
                            min_color_temp,
                            max_color_temp,
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
                    REG_MIN_CT: min_color_temp,
                    REG_MAX_CT: max_color_temp,
                    REG_PHASE_OFFSET: offset,
                    REG_MIN_DELTA: min_delta,
                    REG_STARTED_AT_TS: now,
                    REG_PHASE_MODE: phase_mode,
                    REG_SYNC_GROUP: sync_group,
                }
                LOGGER.info(
                    "Started CCW cycle engine for %s: period=%.2fs, color_temp=[%d,%d], "
                    "phase_mode=%s, offset=%.4f",
                    entity_id,
                    period_s,
                    min_color_temp,
                    max_color_temp,
                    phase_mode,
                    offset,
                )

            await self.async_save()
            self._ensure_loop_running()

    async def async_stop(self, lights: list[str]) -> None:
        """Stop CCW cycling for the specified lights."""
        async with self._lock:
            for entity_id in lights:
                if entity_id in self._registry:
                    del self._registry[entity_id]
                    LOGGER.info("Stopped CCW cycle engine for %s", entity_id)
                else:
                    LOGGER.warning(
                        "Light %s was not in CCW cycle engine registry", entity_id
                    )

            await self.async_save()

            # Stop the loop immediately if registry is now empty
            if not self._registry:
                self._stop_loop()

    async def async_stop_all(self) -> None:
        """Stop CCW cycling for all lights."""
        async with self._lock:
            count = len(self._registry)
            self._registry.clear()
            await self.async_save()
            LOGGER.info("Stopped CCW cycle engine for all %d lights", count)

            # Stop the loop immediately
            self._stop_loop()

    def _stop_loop(self) -> None:
        """Stop the background loop task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            LOGGER.debug("Cancelled CCW cycle engine loop task")

    def get_status(self) -> dict[str, Any]:
        """Get the current registry status."""
        return {
            "active_lights": len(self._registry),
            "loop_running": self._task is not None and not self._task.done(),
            "registry": {k: dict(v) for k, v in self._registry.items()},
        }

    def is_ccw_cycling(self, entity_ids: list[str]) -> bool:
        """Check if any of the given light entities are in CCW cycling.

        Args:
            entity_ids: List of entity IDs to check.

        Returns:
            True if at least one of the entities is currently in CCW cycling.

        """
        for entity_id in entity_ids:
            if entity_id in self._registry:
                LOGGER.debug("Entity %s is in CCW cycling", entity_id)
                return True
        LOGGER.debug("No entities in CCW cycling from: %s", entity_ids)
        return False

    @callback
    def _ensure_loop_running(self) -> None:
        """Ensure the background loop task is running."""
        if self._task is None or self._task.done():
            self._running = True
            self._task = self.hass.async_create_task(
                self._run_loop(), "sksoft_ccw_cycle_engine_loop"
            )
            LOGGER.debug("Started CCW cycle engine loop task")

    async def _run_loop(self) -> None:
        """Run the main loop that updates all lights."""
        LOGGER.debug("CCW cycle engine loop started")

        while self._running:
            # Collect registry snapshot and min tick while holding the lock
            async with self._lock:
                if not self._registry:
                    LOGGER.debug("CCW registry empty, stopping loop")
                    break

                # Find the minimum tick interval
                min_tick = min(entry[REG_TICK] for entry in self._registry.values())

                # Take a snapshot of the registry to avoid holding lock during updates
                registry_snapshot = {k: dict(v) for k, v in self._registry.items()}

            # Get current time after releasing lock (monotonic for accurate timing)
            now = monotonic()

            # Build update coroutines for all lights and execute in parallel
            update_tasks = [
                self._update_light(entity_id, entry, now)
                for entity_id, entry in registry_snapshot.items()
            ]
            if update_tasks:
                results = await asyncio.gather(*update_tasks)
                # Collect entities that need to be removed (missing entities)
                entities_to_remove = [r for r in results if r is not None]

                # Remove missing entities from registry while holding the lock
                if entities_to_remove:
                    async with self._lock:
                        for entity_id in entities_to_remove:
                            if self._registry.pop(entity_id, None) is not None:
                                LOGGER.info(
                                    "Removed missing entity %s from CCW registry",
                                    entity_id,
                                )
                        await self.async_save()

            # Sleep for the minimum tick interval
            await asyncio.sleep(min_tick)

        LOGGER.debug("CCW cycle engine loop ended")

    async def _update_light(
        self, entity_id: str, entry: dict[str, Any], now: float
    ) -> str | None:
        """Update a single light's color temperature.

        Returns the entity_id if the entity was not found and should be removed,
        otherwise returns None.
        """
        period = entry[REG_PERIOD]
        min_ct = entry[REG_MIN_CT]
        max_ct = entry[REG_MAX_CT]
        phase_offset = entry[REG_PHASE_OFFSET]
        min_delta = entry[REG_MIN_DELTA]
        started_at = entry[REG_STARTED_AT_TS]

        # Calculate elapsed time
        elapsed = now - started_at

        # Calculate phase
        time_phase = (2 * math.pi * elapsed) / period

        # All phase modes use the same formula: phase = time_phase + offset
        phase = time_phase + phase_offset

        # Calculate target color temperature using sine wave
        mid = (min_ct + max_ct) / 2
        amp = (max_ct - min_ct) / 2
        target = round(mid + amp * math.sin(phase))

        # Clamp to valid range
        target = max(min_ct, min(max_ct, target))

        # Get current state
        state = self.hass.states.get(entity_id)
        if state is None:
            LOGGER.warning(
                "Entity %s not found, will remove from CCW registry", entity_id
            )
            return entity_id

        # Skip lights that are not currently on
        if state.state != STATE_ON:
            LOGGER.debug(
                "Skipping %s: light is not on (state=%s)", entity_id, state.state
            )
            return None

        current_ct = state.attributes.get(ATTR_COLOR_TEMP_KELVIN) or 0

        # Only update if delta is significant enough
        if abs(target - current_ct) >= min_delta:
            LOGGER.debug(
                "Updating %s: color_temp %d -> %d (phase=%.2f)",
                entity_id,
                current_ct,
                target,
                phase,
            )
            # Use transition time (in seconds) equal to tick interval for smooth changes
            tick = entry[REG_TICK]
            await self.hass.services.async_call(
                "light",
                SERVICE_TURN_ON,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_COLOR_TEMP_KELVIN: target,
                    ATTR_TRANSITION: tick,
                },
                blocking=False,
            )

        return None
