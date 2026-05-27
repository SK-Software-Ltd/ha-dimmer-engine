"""Smoke tests for HA version compatibility matrix.

These tests run against EVERY HA version in the CI matrix to catch API
breakage early. They intentionally avoid heavy integration-setup paths
(which differ across HA versions) and exercise just the surfaces that
historically broke:

- Imports resolve on the target HA version
- Both condition classes are *concrete* (no missing abstract methods)
- Both condition classes can be instantiated without an HA event loop
- The `async_get_conditions` registry returns both classes
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    pass


def test_module_imports() -> None:
    """All package modules must import cleanly on the target HA version."""
    import custom_components.sksoft_dimmer_engine  # noqa: F401
    from custom_components.sksoft_dimmer_engine import (  # noqa: F401
        ccw_engine,
        condition,
        config_flow,
        const,
        engine,
        storage,
    )


def test_condition_classes_are_concrete() -> None:
    """No abstract methods may be left on our condition classes.

    Regression: HA 2026.3 renamed the abstract from `async_get_checker`
    to `_async_check`. v2.0.0 implemented only the former and crashed
    on 2026.3+ with: "Can't instantiate abstract class … without an
    implementation for abstract method '_async_check'".
    """
    from custom_components.sksoft_dimmer_engine.condition import (
        IsCCWCyclingCondition,
        IsCycleDimmingCondition,
    )

    assert IsCycleDimmingCondition.__abstractmethods__ == frozenset(), (
        f"IsCycleDimmingCondition has unimplemented abstract methods: "
        f"{IsCycleDimmingCondition.__abstractmethods__}"
    )
    assert IsCCWCyclingCondition.__abstractmethods__ == frozenset(), (
        f"IsCCWCyclingCondition has unimplemented abstract methods: "
        f"{IsCCWCyclingCondition.__abstractmethods__}"
    )


def test_condition_classes_can_be_instantiated() -> None:
    """Conditions must be instantiable — the symptom of the 2.0.0 regression."""
    from custom_components.sksoft_dimmer_engine.condition import (
        IsCCWCyclingCondition,
        IsCycleDimmingCondition,
    )
    from homeassistant.helpers.condition import ConditionConfig

    hass = MagicMock()
    config = ConditionConfig(options={"lights": ["light.x"]})

    IsCycleDimmingCondition(hass, config)
    IsCCWCyclingCondition(hass, config)


@pytest.mark.asyncio
async def test_async_get_conditions_registry() -> None:
    """HA discovers conditions via this entry point — must return both classes."""
    from custom_components.sksoft_dimmer_engine.condition import async_get_conditions

    hass = MagicMock()
    conditions = await async_get_conditions(hass)

    assert "is_cycle_dimming" in conditions
    assert "is_ccw_cycling" in conditions
    assert len(conditions) == 2


def test_manifest_minimum_ha_version_in_hacs_json() -> None:
    """hacs.json must declare the HA minimum version we actually support."""
    import json
    from pathlib import Path

    hacs_path = Path(__file__).parent.parent / "hacs.json"
    data = json.loads(hacs_path.read_text())
    assert "homeassistant" in data, "hacs.json must declare homeassistant minimum"
