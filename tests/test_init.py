from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sksoft_dimmer_engine import DimmerEngineData
from custom_components.sksoft_dimmer_engine.ccw_engine import CCWCycleEngine
from custom_components.sksoft_dimmer_engine.const import (
    DOMAIN,
    SERVICE_START,
    SERVICE_START_CCW,
    SERVICE_STATUS,
    SERVICE_STOP,
    SERVICE_STOP_ALL,
    SERVICE_STOP_ALL_CCW,
    SERVICE_STOP_CCW,
)
from custom_components.sksoft_dimmer_engine.engine import DimmerEngine

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def _setup_integration(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_async_setup_entry_creates_engines_on_runtime_data(
    hass: HomeAssistant,
) -> None:
    entry = await _setup_integration(hass)

    runtime_data: DimmerEngineData = entry.runtime_data
    assert "engine" in runtime_data
    assert "ccw_engine" in runtime_data
    assert isinstance(runtime_data["engine"], DimmerEngine)
    assert isinstance(runtime_data["ccw_engine"], CCWCycleEngine)


async def test_async_setup_registers_all_services(hass: HomeAssistant) -> None:
    await _setup_integration(hass)

    for service in (
        SERVICE_START,
        SERVICE_STOP,
        SERVICE_STOP_ALL,
        SERVICE_STATUS,
        SERVICE_START_CCW,
        SERVICE_STOP_CCW,
        SERVICE_STOP_ALL_CCW,
    ):
        assert hass.services.has_service(DOMAIN, service), (
            f"service {service} should be registered"
        )


async def test_async_unload_entry_shuts_down_engines(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]
    ccw_engine = entry.runtime_data["ccw_engine"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not engine._running
    assert engine._task is None or engine._task.done()
    assert not ccw_engine._running
    assert ccw_engine._task is None or ccw_engine._task.done()


async def test_services_persist_after_unload(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    for service in (
        SERVICE_START,
        SERVICE_STOP,
        SERVICE_STOP_ALL,
        SERVICE_START_CCW,
    ):
        assert hass.services.has_service(DOMAIN, service)


async def test_reload_recreates_runtime_data(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    original_engine = entry.runtime_data["engine"]

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data["engine"] is not original_engine
    assert isinstance(entry.runtime_data["engine"], DimmerEngine)
    assert isinstance(entry.runtime_data["ccw_engine"], CCWCycleEngine)
