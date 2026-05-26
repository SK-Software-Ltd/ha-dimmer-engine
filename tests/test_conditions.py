from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.sksoft_dimmer_engine.condition import (
    CONDITIONS,
    IsCCWCyclingCondition,
    IsCycleDimmingCondition,
    async_get_conditions,
    is_ccw_cycling,
    is_cycle_dimming,
)
from custom_components.sksoft_dimmer_engine.const import (
    ATTR_LIGHTS,
    DOMAIN,
    REG_MAX_B,
    REG_MAX_CT,
    REG_MIN_B,
    REG_MIN_CT,
    REG_MIN_DELTA,
    REG_PERIOD,
    REG_PHASE_MODE,
    REG_PHASE_OFFSET,
    REG_STARTED_AT_TS,
    REG_SYNC_GROUP,
    REG_TICK,
)
from homeassistant.helpers.condition import ConditionConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _brightness_registry_entry() -> dict:
    return {
        REG_PERIOD: 10.0,
        REG_TICK: 0.5,
        REG_MIN_B: 3,
        REG_MAX_B: 255,
        REG_PHASE_OFFSET: 0.0,
        REG_MIN_DELTA: 1,
        REG_STARTED_AT_TS: monotonic(),
        REG_PHASE_MODE: "absolute",
        REG_SYNC_GROUP: False,
    }


def _ccw_registry_entry() -> dict:
    return {
        REG_PERIOD: 10.0,
        REG_TICK: 0.5,
        REG_MIN_CT: 2700,
        REG_MAX_CT: 6500,
        REG_PHASE_OFFSET: 0.0,
        REG_MIN_DELTA: 1,
        REG_STARTED_AT_TS: monotonic(),
        REG_PHASE_MODE: "absolute",
        REG_SYNC_GROUP: False,
    }


async def _setup_integration(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_is_cycle_dimming_false_when_no_entry(hass: HomeAssistant) -> None:
    assert is_cycle_dimming(hass, ["light.a"]) is False


async def test_is_ccw_cycling_false_when_no_entry(hass: HomeAssistant) -> None:
    assert is_ccw_cycling(hass, ["light.a"]) is False


async def test_is_cycle_dimming_true_when_light_registered(
    hass: HomeAssistant,
) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]
    engine._registry["light.kitchen"] = _brightness_registry_entry()

    assert is_cycle_dimming(hass, ["light.kitchen"]) is True
    assert is_cycle_dimming(hass, ["light.other", "light.kitchen"]) is True
    assert is_cycle_dimming(hass, ["light.other"]) is False
    assert is_cycle_dimming(hass, []) is False


async def test_is_ccw_cycling_true_when_light_registered(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]
    ccw_engine._registry["light.bedroom"] = _ccw_registry_entry()

    assert is_ccw_cycling(hass, ["light.bedroom"]) is True
    assert is_ccw_cycling(hass, ["light.other", "light.bedroom"]) is True
    assert is_ccw_cycling(hass, ["light.other"]) is False
    assert is_ccw_cycling(hass, []) is False


async def test_is_cycle_dimming_and_ccw_independent(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]
    ccw_engine = entry.runtime_data["ccw_engine"]

    engine._registry["light.bright"] = _brightness_registry_entry()
    ccw_engine._registry["light.warm"] = _ccw_registry_entry()

    assert is_cycle_dimming(hass, ["light.bright"]) is True
    assert is_cycle_dimming(hass, ["light.warm"]) is False
    assert is_ccw_cycling(hass, ["light.warm"]) is True
    assert is_ccw_cycling(hass, ["light.bright"]) is False


async def test_async_get_conditions_returns_both(hass: HomeAssistant) -> None:
    conditions = await async_get_conditions(hass)
    assert set(conditions.keys()) == {"is_cycle_dimming", "is_ccw_cycling"}
    assert conditions["is_cycle_dimming"] is IsCycleDimmingCondition
    assert conditions["is_ccw_cycling"] is IsCCWCyclingCondition
    assert conditions == CONDITIONS


async def test_is_cycle_dimming_condition_validate_config(
    hass: HomeAssistant,
) -> None:
    config = {"options": {ATTR_LIGHTS: ["light.a"]}}
    validated = await IsCycleDimmingCondition.async_validate_config(hass, config)
    assert validated["options"][ATTR_LIGHTS] == ["light.a"]

    with pytest.raises(vol.Invalid):
        await IsCycleDimmingCondition.async_validate_config(hass, {"options": {}})


async def test_is_ccw_cycling_condition_validate_config(hass: HomeAssistant) -> None:
    config = {"options": {ATTR_LIGHTS: ["light.x"]}}
    validated = await IsCCWCyclingCondition.async_validate_config(hass, config)
    assert validated["options"][ATTR_LIGHTS] == ["light.x"]


async def test_cycle_dimming_condition_check(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    engine = entry.runtime_data["engine"]
    engine._registry["light.living"] = _brightness_registry_entry()

    config = ConditionConfig(options={ATTR_LIGHTS: ["light.living"]})
    condition = IsCycleDimmingCondition(hass, config)

    checker = await condition.async_get_checker()
    assert checker() is True

    other_config = ConditionConfig(options={ATTR_LIGHTS: ["light.absent"]})
    other_condition = IsCycleDimmingCondition(hass, other_config)
    other_checker = await other_condition.async_get_checker()
    assert other_checker() is False


async def test_ccw_cycling_condition_check(hass: HomeAssistant) -> None:
    entry = await _setup_integration(hass)
    ccw_engine = entry.runtime_data["ccw_engine"]
    ccw_engine._registry["light.window"] = _ccw_registry_entry()

    config = ConditionConfig(options={ATTR_LIGHTS: ["light.window"]})
    condition = IsCCWCyclingCondition(hass, config)
    checker = await condition.async_get_checker()
    assert checker() is True

    other_config = ConditionConfig(options={ATTR_LIGHTS: ["light.absent"]})
    other_condition = IsCCWCyclingCondition(hass, other_config)
    other_checker = await other_condition.async_get_checker()
    assert other_checker() is False


async def test_condition_init_rejects_none_options(hass: HomeAssistant) -> None:
    config = ConditionConfig(options=None)
    with pytest.raises(ValueError):
        IsCycleDimmingCondition(hass, config)
    with pytest.raises(ValueError):
        IsCCWCyclingCondition(hass, config)
