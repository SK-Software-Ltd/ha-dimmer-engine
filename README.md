# SKSoft Dimmer Engine for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SK-Software-Ltd&repository=ha-dimmer-engine&category=integration)

A custom Home Assistant integration that provides a sine-wave, time-based brightness cycling engine for one or more Light entities. It runs a single shared async loop for all active lights, making it efficient and lightweight.

> **Minimum Home Assistant version: 2024.12**
> This integration uses the modern conditions framework introduced in HA 2024.12. Earlier versions are not supported.

## Features

- **Sine-wave brightness cycling**: Smoothly cycles light brightness using a sine wave pattern
- **Multi-light support**: Control multiple lights with a single service call
- **Phase synchronization**: Keep multiple lights in sync or offset them
- **Persistence**: Registry is saved and restored across Home Assistant restarts
- **Efficient**: Single async loop for all lights, minimal resource usage
- **Configurable**: Adjust period, brightness range, tick interval, and more
- **Modern conditions**: Native integration with HA 2024.12+ conditions framework

## Installation

### HACS Installation (Recommended)

1. Click the button at the top of this page to open HACS in your Home Assistant instance
2. Click **Download** to install the integration
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration**
5. Search for **SKSoft Dimmer Engine** and click to add it

### Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/sksoft_dimmer_engine` folder into your Home Assistant `custom_components` directory:
   ```
   <config>/custom_components/sksoft_dimmer_engine/
   ```
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration**
5. Search for **SKSoft Dimmer Engine** and click to add it

## Services

### sksoft_dimmer_engine.start

Start the dimmer engine for one or more lights.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| lights | list | Yes | - | List of light entity IDs to cycle |
| period_s | float | No | 10 | Duration of one complete brightness cycle in seconds |
| tick_s | float | No | 0.25 | How often to update brightness in seconds |
| min_brightness | int | No | 3 | Minimum brightness level (1-255) |
| max_brightness | int | No | 255 | Maximum brightness level (1-255) |
| phase_mode | string | No | sync_to_current | Phase calculation mode: sync_to_current, absolute, relative |
| phase_offset | float | No | 0 | Phase offset in radians |
| sync_group | boolean | No | true | Sync all lights to first light's phase (when using sync_to_current) |
| min_delta | int | No | 1 | Minimum brightness change required before updating |

### sksoft_dimmer_engine.stop

Stop the dimmer engine for one or more lights.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lights | list | Yes | List of light entity IDs to stop |

### sksoft_dimmer_engine.stop_all

Stop the dimmer engine for all currently registered lights.

No fields required.

### sksoft_dimmer_engine.start_ccw

Start color temperature (CCW) cycling for one or more lights.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| lights | list | Yes | - | List of light entity IDs to cycle |
| period_s | float | No | 60 | Duration of one complete color temperature cycle in seconds |
| tick_s | float | No | 0.5 | How often to update color temperature in seconds |
| min_color_temp | int | No | 2700 | Minimum color temperature in Kelvin |
| max_color_temp | int | No | 5000 | Maximum color temperature in Kelvin |
| phase_mode | string | No | sync_to_current | Phase calculation mode: sync_to_current, absolute, relative |
| phase_offset | float | No | 0 | Phase offset in radians |
| min_delta | int | No | 10 | Minimum color temperature change required before updating |

### sksoft_dimmer_engine.stop_ccw

Stop color temperature cycling for one or more lights.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lights | list | Yes | List of light entity IDs to stop |

### sksoft_dimmer_engine.stop_all_ccw

Stop color temperature cycling for all currently registered lights.

No fields required.

### sksoft_dimmer_engine.status

Log the current status of the dimmer engine (active lights, cycle parameters) to the Home Assistant log at INFO level.

No fields required.

## Conditions

This integration provides native conditions for use in automations and scripts. These use the modern HA conditions framework (requires HA 2024.12+).

### is_cycle_dimming

Check if any of the specified light entities are currently in brightness cycle dimming. Returns `true` if at least one light is actively cycling.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lights | list | Yes | List of light entity IDs to check |

Example usage in an automation:

```yaml
automation:
  - alias: "Do something if lights are dimming"
    trigger:
      - platform: state
        entity_id: input_boolean.trigger
        to: "on"
    condition:
      - condition: sksoft_dimmer_engine.is_cycle_dimming
        options:
          lights:
            - light.living_room
            - light.bedroom
    action:
      - action: notify.notify
        data:
          message: "Lights are currently in cycle dimming mode!"
```

### is_ccw_cycling

Check if any of the specified light entities are currently in color temperature (CCW) cycling. Returns `true` if at least one light is in CCW cycling.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lights | list | Yes | List of light entity IDs to check |

Example usage in an automation:

```yaml
automation:
  - alias: "Do something if lights are CCW cycling"
    trigger:
      - platform: state
        entity_id: input_boolean.trigger
        to: "on"
    condition:
      - condition: sksoft_dimmer_engine.is_ccw_cycling
        options:
          lights:
            - light.living_room
            - light.bedroom
    action:
      - action: notify.notify
        data:
          message: "Lights are currently in CCW cycling mode!"
```

> **Note on condition syntax**: As of v2.0.0, conditions use the `options:` key to pass parameters, matching the HA 2024.12+ conditions framework. The old flat syntax (e.g., `lights:` directly under `condition:`) is no longer supported.

## Phase Modes

### sync_to_current (default)

Computes the phase offset so that the sine wave output matches the light's current brightness at the start time. If `sync_group` is true, the offset is computed from the first light and applied to all lights in the call.

### absolute

Uses the `phase_offset` value directly as the phase offset. Useful for precise control over where in the cycle the light starts.

### relative

Adds the `phase_offset` value to the time-based phase. Useful for creating lights that are offset from each other.

## Example Automations

### Basic Usage - Start Cycling

```yaml
automation:
  - alias: "Start Dimming at Sunset"
    trigger:
      - platform: sun
        event: sunset
    action:
      - action: sksoft_dimmer_engine.start
        data:
          lights:
            - light.living_room
          period_s: 30
          min_brightness: 10
          max_brightness: 200
```

### Stop Cycling When Leaving Home

```yaml
automation:
  - alias: "Stop All Dimming When Away"
    trigger:
      - platform: state
        entity_id: person.me
        to: "not_home"
    action:
      - action: sksoft_dimmer_engine.stop_all
```

### Conditional Action - Only Notify When Not Cycling

```yaml
automation:
  - alias: "Notify only when lights are not cycling"
    trigger:
      - platform: state
        entity_id: input_boolean.movie_mode
        to: "on"
    condition:
      - condition: not
        conditions:
          - condition: sksoft_dimmer_engine.is_cycle_dimming
            options:
              lights:
                - light.living_room
    action:
      - action: notify.notify
        data:
          message: "Movie mode activated — lights are steady."
```

### Wave Effect with Multiple Lights

```yaml
script:
  wave_effect:
    alias: "Wave Light Effect"
    sequence:
      # Start first light
      - action: sksoft_dimmer_engine.start
        data:
          lights:
            - light.lamp_1
          period_s: 10
          phase_mode: absolute
          phase_offset: 0
      # Start second light with offset
      - action: sksoft_dimmer_engine.start
        data:
          lights:
            - light.lamp_2
          period_s: 10
          phase_mode: absolute
          phase_offset: 1.57  # pi/2 = 90 degrees behind
      # Start third light with offset
      - action: sksoft_dimmer_engine.start
        data:
          lights:
            - light.lamp_3
          period_s: 10
          phase_mode: absolute
          phase_offset: 3.14  # pi = 180 degrees behind
```

### Check Status

```yaml
script:
  check_dimmer_status:
    alias: "Check Dimmer Engine Status"
    sequence:
      - action: sksoft_dimmer_engine.status
```

The status will be logged to the Home Assistant log at INFO level.

### Color Temperature Cycling

```yaml
script:
  color_temp_cycle:
    alias: "Color Temperature Cycle Effect"
    sequence:
      - action: sksoft_dimmer_engine.start_ccw
        data:
          lights:
            - light.living_room
          period_s: 60
          min_color_temp: 2700
          max_color_temp: 5000
          phase_mode: sync_to_current
```

### Stop CCW Cycling at Night

```yaml
automation:
  - alias: "Stop CCW Cycling at Night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - action: sksoft_dimmer_engine.stop_all_ccw
```

## Behavior Notes

1. **Single Loop**: The integration runs a single background async task for all lights, not one per light.

2. **Auto-shutdown**: The loop automatically stops when no lights are registered.

3. **Persistence**: The registry is saved to Home Assistant's `.storage` directory and restored on startup.

4. **Min Delta**: The `min_delta` parameter prevents excessive service calls by only updating when the brightness difference exceeds the threshold.

5. **Entity Removal**: If a light entity is not found during update, it is automatically removed from the registry.

## Logging

The integration uses standard Home Assistant logging:

- **INFO**: Start/stop actions, status queries, config entry creation
- **DEBUG**: Tick updates, config flow steps, module loading
- **WARNING**: Entity not found, light not in registry

To enable debug logging, add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sksoft_dimmer_engine: debug
```

After modifying `configuration.yaml`, restart Home Assistant for the changes to take effect.

## Troubleshooting

### "Invalid handler specified" Error

If you see "Config flow could not be loaded: Invalid handler specified" when trying to add the integration:

1. **Enable debug logging** by adding the following to your `configuration.yaml`:

   ```yaml
   logger:
     default: info
     logs:
       custom_components.sksoft_dimmer_engine: debug
       homeassistant.config_entries: debug
       homeassistant.loader: debug
   ```

2. **Restart Home Assistant** to apply the logging configuration.

3. **Check the logs** by navigating to **Settings → System → Logs**, or by checking the `home-assistant.log` file in your config directory.

4. **Look for these log entries** to identify the issue:
   - `SKSoft Dimmer Engine config_flow module loaded` — Confirms the config_flow module is being loaded
   - `async_step_user called` — Confirms the config flow is being initiated
   - Any error messages from `homeassistant.loader` about the integration

5. **Common causes and solutions**:
   - **Integration not properly installed**: Ensure the `sksoft_dimmer_engine` folder is in your `custom_components` directory with all required files
   - **Missing files**: Verify all files exist: `__init__.py`, `condition.py`, `conditions.yaml`, `config_flow.py`, `const.py`, `manifest.json`, `services.yaml`, `storage.py`, `strings.json`, and `translations/en.json`
   - **Cache issues**: Try restarting Home Assistant twice, or clear the browser cache
   - **Syntax errors**: Check the logs for Python syntax errors in the integration files

### Condition Not Working / "Unknown condition" Error

If a condition like `sksoft_dimmer_engine.is_cycle_dimming` fails with an unknown condition error:

1. **Check your HA version**: This integration requires **Home Assistant 2024.12 or later**. Upgrade if needed.

2. **Verify the `options:` key is present**: As of v2.0.0, condition parameters must be nested under `options:`:

   ```yaml
   # ✅ Correct (v2.0.0+)
   condition:
     - condition: sksoft_dimmer_engine.is_cycle_dimming
       options:
         lights:
           - light.living_room

   # ❌ Old syntax (no longer supported)
   condition:
     - condition: sksoft_dimmer_engine.is_cycle_dimming
       lights:
         - light.living_room
   ```

3. **Restart Home Assistant** after updating the integration to ensure the new condition classes are loaded.

### Checking Installed Files

To verify the integration is properly installed, check that these files exist in your `custom_components/sksoft_dimmer_engine/` directory:

```
custom_components/
  sksoft_dimmer_engine/
    __init__.py
    condition.py
    conditions.yaml
    config_flow.py
    const.py
    manifest.json
    services.yaml
    storage.py
    strings.json
    translations/
      en.json
```

### Lights Not Updating

If lights are registered but not updating:

- Check that the light entities are **currently on** — the engine skips lights that are off
- Verify `tick_s` is not set too low (below 0.1 may cause issues on slower hardware)
- Check the logs for `WARNING` messages about entity not found

### Persistence Not Restoring

If the registry is not restored after a restart:

- Check that Home Assistant has write access to its `.storage` directory
- Look for errors in the log related to `sksoft_dimmer_engine` storage
- The storage file is located at `<config>/.storage/sksoft_dimmer_engine`
