# Changelog

All notable changes to SKSoft Dimmer Engine are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-26

### Breaking Changes

- **Conditions now require the `options:` key** — condition parameters (`lights`) must be nested under `options:` to comply with the HA 2024.12+ conditions framework. The old flat syntax is no longer supported.

  ```yaml
  # Before (v1.x)
  condition:
    - condition: sksoft_dimmer_engine.is_cycle_dimming
      lights:
        - light.living_room

  # After (v2.0.0+)
  condition:
    - condition: sksoft_dimmer_engine.is_cycle_dimming
      options:
        lights:
          - light.living_room
  ```

- **Minimum Home Assistant version is now 2024.12** — the new class-based conditions framework (`homeassistant.helpers.condition.Condition`) is required.

### Added

- `condition.py` — new module implementing class-based `IsCycleDimmingCondition` and `IsCCWCyclingCondition` using the `Condition` base class from `homeassistant.helpers.condition`
- `conditions.yaml` — declarative condition schema with entity selectors for `is_cycle_dimming` and `is_ccw_cycling`
- `storage.py` — dedicated storage module for registry persistence, replacing inline storage logic in `__init__.py`
- `async_get_conditions` entry point registered in `__init__.py` for HA to discover integration conditions

### Changed

- Conditions are now registered via the modern `async_get_conditions` / `Condition` class pattern instead of the legacy `condition` platform
- All example automations and scripts updated to use `action:` instead of the deprecated `service:` key
- README updated with HA minimum version requirement, modernized installation steps, updated condition syntax examples, and an expanded Troubleshooting section

### Removed

- Legacy flat condition syntax support (parameters directly under `condition:` without `options:`)

## [1.2.0] - 2024-xx-xx

- Added CCW (color temperature) cycling: `start_ccw`, `stop_ccw`, `stop_all_ccw` services and `is_ccw_cycling` condition

## [1.1.4] - 2024-xx-xx

- Fixed cycle dimming to only update lights that are currently on

## [1.0.0] - 2024-xx-xx

- Initial release with sine-wave brightness cycling, multi-light support, phase synchronization, and persistence
