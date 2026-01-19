"""Constants for the SKSoft Dimmer Engine integration."""

DOMAIN = "sksoft_dimmer_engine"

# Storage
STORAGE_KEY = "sksoft_dimmer_engine.registry"
STORAGE_KEY_CCW = "sksoft_dimmer_engine.ccw_registry"
STORAGE_VERSION = 1

# Service names
SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_STOP_ALL = "stop_all"
SERVICE_STATUS = "status"

# CCW (Color Temperature) cycling service names
SERVICE_START_CCW = "start_ccw"
SERVICE_STOP_CCW = "stop_ccw"
SERVICE_STOP_ALL_CCW = "stop_all_ccw"

# Default values
DEFAULT_PERIOD_S = 10.0
DEFAULT_TICK_S = 0.25
DEFAULT_MIN_BRIGHTNESS = 3
DEFAULT_MAX_BRIGHTNESS = 255
DEFAULT_PHASE_OFFSET = 0.0
DEFAULT_SYNC_GROUP = True
DEFAULT_MIN_DELTA = 1
DEFAULT_PHASE_MODE = "sync_to_current"

# CCW (Color Temperature) default values (in Kelvin)
DEFAULT_MIN_COLOR_TEMP = 2700  # Warm white
DEFAULT_MAX_COLOR_TEMP = 6500  # Cool white

# Phase modes
PHASE_MODE_SYNC_TO_CURRENT = "sync_to_current"
PHASE_MODE_ABSOLUTE = "absolute"
PHASE_MODE_RELATIVE = "relative"
PHASE_MODES = [PHASE_MODE_SYNC_TO_CURRENT, PHASE_MODE_ABSOLUTE, PHASE_MODE_RELATIVE]

# Attribute names for service calls
ATTR_LIGHTS = "lights"
ATTR_PERIOD_S = "period_s"
ATTR_TICK_S = "tick_s"
ATTR_MIN_BRIGHTNESS = "min_brightness"
ATTR_MAX_BRIGHTNESS = "max_brightness"
ATTR_PHASE_MODE = "phase_mode"
ATTR_PHASE_OFFSET = "phase_offset"
ATTR_SYNC_GROUP = "sync_group"
ATTR_MIN_DELTA = "min_delta"

# CCW (Color Temperature) cycling attribute names
ATTR_MIN_COLOR_TEMP = "min_color_temp"
ATTR_MAX_COLOR_TEMP = "max_color_temp"

# Registry entry keys
REG_PERIOD = "period"
REG_TICK = "tick"
REG_MIN_B = "min_b"
REG_MAX_B = "max_b"
REG_PHASE_OFFSET = "phase_offset"
REG_MIN_DELTA = "min_delta"
REG_STARTED_AT_TS = "started_at_ts"
REG_PHASE_MODE = "phase_mode"
REG_SYNC_GROUP = "sync_group"

# CCW (Color Temperature) registry entry keys
REG_MIN_CT = "min_ct"
REG_MAX_CT = "max_ct"

# Condition types
CONDITION_IS_CYCLE_DIMMING = "is_cycle_dimming"
CONDITION_IS_CCW_CYCLING = "is_ccw_cycling"
