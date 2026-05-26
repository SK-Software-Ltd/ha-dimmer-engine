from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sksoft_dimmer_engine.const import (
    ATTR_LIGHTS,
    ATTR_MAX_BRIGHTNESS,
    ATTR_MAX_COLOR_TEMP,
    ATTR_MIN_BRIGHTNESS,
    ATTR_MIN_COLOR_TEMP,
    ATTR_PERIOD_S,
    ATTR_TICK_S,
    DOMAIN,
    PHASE_MODE_ABSOLUTE,
    SERVICE_START,
    SERVICE_START_CCW,
    SERVICE_STATUS,
    SERVICE_STOP,
    SERVICE_STOP_ALL,
    SERVICE_STOP_ALL_CCW,
    SERVICE_STOP_CCW,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def _setup_integration(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_start_service_registers_lights(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]

    with patch.object(engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START,
            {
                ATTR_LIGHTS: ["light.kitchen", "light.living_room"],
                ATTR_PERIOD_S: 10.0,
                ATTR_TICK_S: 0.5,
                ATTR_MIN_BRIGHTNESS: 10,
                ATTR_MAX_BRIGHTNESS: 200,
            },
            blocking=True,
        )

    assert "light.kitchen" in engine._registry
    assert "light.living_room" in engine._registry
    assert engine._registry["light.kitchen"]["period"] == 10.0
    assert engine._registry["light.kitchen"]["min_b"] == 10
    assert engine._registry["light.kitchen"]["max_b"] == 200


async def test_stop_service_removes_light(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]

    with patch.object(engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START,
            {ATTR_LIGHTS: ["light.a", "light.b"]},
            blocking=True,
        )

    assert "light.a" in engine._registry
    assert "light.b" in engine._registry

    await hass.services.async_call(
        DOMAIN,
        SERVICE_STOP,
        {ATTR_LIGHTS: ["light.a"]},
        blocking=True,
    )

    assert "light.a" not in engine._registry
    assert "light.b" in engine._registry


async def test_stop_all_clears_registry(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]

    with patch.object(engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START,
            {ATTR_LIGHTS: ["light.a", "light.b", "light.c"]},
            blocking=True,
        )

    assert len(engine._registry) == 3

    await hass.services.async_call(DOMAIN, SERVICE_STOP_ALL, {}, blocking=True)

    assert engine._registry == {}


async def test_start_ccw_service_registers_lights(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]

    with patch.object(ccw_engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_CCW,
            {
                ATTR_LIGHTS: ["light.bedroom"],
                ATTR_PERIOD_S: 30.0,
                ATTR_MIN_COLOR_TEMP: 2700,
                ATTR_MAX_COLOR_TEMP: 6500,
            },
            blocking=True,
        )

    assert "light.bedroom" in ccw_engine._registry
    assert ccw_engine._registry["light.bedroom"]["period"] == 30.0
    assert ccw_engine._registry["light.bedroom"]["min_ct"] == 2700
    assert ccw_engine._registry["light.bedroom"]["max_ct"] == 6500


async def test_stop_ccw_service_removes_light(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]

    with patch.object(ccw_engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_CCW,
            {ATTR_LIGHTS: ["light.x", "light.y"]},
            blocking=True,
        )

    assert "light.x" in ccw_engine._registry
    assert "light.y" in ccw_engine._registry

    await hass.services.async_call(
        DOMAIN,
        SERVICE_STOP_CCW,
        {ATTR_LIGHTS: ["light.x"]},
        blocking=True,
    )

    assert "light.x" not in ccw_engine._registry
    assert "light.y" in ccw_engine._registry


async def test_stop_all_ccw_clears_registry(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]

    with patch.object(ccw_engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_CCW,
            {ATTR_LIGHTS: ["light.a", "light.b"]},
            blocking=True,
        )

    assert len(ccw_engine._registry) == 2

    await hass.services.async_call(DOMAIN, SERVICE_STOP_ALL_CCW, {}, blocking=True)

    assert ccw_engine._registry == {}


async def test_status_service_runs_without_error(hass: HomeAssistant) -> None:
    await _setup_integration(hass)

    await hass.services.async_call(DOMAIN, SERVICE_STATUS, {}, blocking=True)


async def test_brightness_range_validation_rejects_inverted(
    hass: HomeAssistant,
) -> None:
    import voluptuous as vol

    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]

    try:
        with patch.object(engine, "_ensure_loop_running"):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_START,
                {
                    ATTR_LIGHTS: ["light.a"],
                    ATTR_MIN_BRIGHTNESS: 200,
                    ATTR_MAX_BRIGHTNESS: 50,
                },
                blocking=True,
            )
    except vol.Invalid:
        pass
    else:
        raise AssertionError("Expected vol.Invalid for inverted brightness range")


async def test_color_temp_range_validation_rejects_inverted(
    hass: HomeAssistant,
) -> None:
    import voluptuous as vol

    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]

    try:
        with patch.object(ccw_engine, "_ensure_loop_running"):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_START_CCW,
                {
                    ATTR_LIGHTS: ["light.a"],
                    ATTR_MIN_COLOR_TEMP: 6000,
                    ATTR_MAX_COLOR_TEMP: 3000,
                },
                blocking=True,
            )
    except vol.Invalid:
        pass
    else:
        raise AssertionError("Expected vol.Invalid for inverted color temp range")


async def test_absolute_phase_mode_uses_given_offset(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]

    with patch.object(engine, "_ensure_loop_running"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START,
            {
                ATTR_LIGHTS: ["light.a"],
                "phase_mode": PHASE_MODE_ABSOLUTE,
                "phase_offset": 1.5,
            },
            blocking=True,
        )

    assert engine._registry["light.a"]["phase_offset"] == 1.5


async def test_start_service_without_entry_warns(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_START,
        {ATTR_LIGHTS: ["light.a"]},
        blocking=True,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_STOP_ALL,
        {},
        blocking=True,
    )


async def test_engine_run_loop_processes_registered_light(
    hass: HomeAssistant,
) -> None:
    import asyncio

    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]

    update_event = asyncio.Event()
    update_calls: list[str] = []

    async def fake_update(entity_id: str, *args, **kwargs) -> str | None:
        update_calls.append(entity_id)
        update_event.set()
        return None

    with patch.object(engine, "_update_light", side_effect=fake_update):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START,
            {
                ATTR_LIGHTS: ["light.loop_target"],
                ATTR_PERIOD_S: 1.0,
                ATTR_TICK_S: 0.01,
            },
            blocking=True,
        )
        await asyncio.wait_for(update_event.wait(), timeout=2.0)
        await engine.async_stop_all()

    assert "light.loop_target" in update_calls


async def test_ccw_engine_run_loop_processes_registered_light(
    hass: HomeAssistant,
) -> None:
    import asyncio

    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]

    update_event = asyncio.Event()
    update_calls: list[str] = []

    async def fake_update(entity_id: str, *args, **kwargs) -> str | None:
        update_calls.append(entity_id)
        update_event.set()
        return None

    with patch.object(ccw_engine, "_update_light", side_effect=fake_update):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_CCW,
            {
                ATTR_LIGHTS: ["light.ccw_target"],
                ATTR_PERIOD_S: 1.0,
                ATTR_TICK_S: 0.01,
            },
            blocking=True,
        )
        await asyncio.wait_for(update_event.wait(), timeout=2.0)
        await ccw_engine.async_stop_all()

    assert "light.ccw_target" in update_calls


_ = AsyncMock
