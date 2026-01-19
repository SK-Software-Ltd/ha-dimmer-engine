"""Constants for the SKSoft Dimmer Engine integration."""

DOMAIN = "sksoft_dimmer_engine"

# Storage
STORAGE_KEY = "sksoft_dimmer_engine.registry"
STORAGE_VERSION = 1

# Service names
SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_STOP_ALL = "stop_all"
SERVICE_STATUS = "status"

# Default values
DEFAULT_PERIOD_S = 10.0
DEFAULT_TICK_S = 0.25
DEFAULT_MIN_BRIGHTNESS = 3
DEFAULT_MAX_BRIGHTNESS = 255
DEFAULT_PHASE_OFFSET = 0.0
DEFAULT_SYNC_GROUP = True
DEFAULT_MIN_DELTA = 1
DEFAULT_PHASE_MODE = "sync_to_current"

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
