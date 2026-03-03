"""Device types, default colors, and common values for M4L devices."""

# Binary device type codes for .amxd container header
AUDIO_EFFECT = b"aaaa"
INSTRUMENT = b"iiii"
MIDI_EFFECT = b"mmmm"

# amxdtype integer values for the project section
AMXD_TYPE = {
    "audio_effect": 1633771873,   # aaaa as uint32 LE
    "instrument": 1768515945,     # iiii as uint32 LE
    "midi_effect": 1835887981,    # mmmm as uint32 LE
}

# Map device type string to binary type code
DEVICE_TYPE_CODES = {
    "audio_effect": AUDIO_EFFECT,
    "instrument": INSTRUMENT,
    "midi_effect": MIDI_EFFECT,
}

# Default appversion matching Max 8.6.5
DEFAULT_APPVERSION = {
    "major": 8,
    "minor": 6,
    "revision": 5,
    "architecture": "x64",
    "modernui": 1,
}

# Default patcher colors
DEFAULT_BG_COLOR = [0.15, 0.15, 0.17, 1.0]
DEFAULT_TEXT_COLOR = [0.95, 0.92, 0.85, 1.0]
DEFAULT_ACCENT_COLOR = [0.45, 0.75, 0.65, 1.0]

# live.dial unitstyle values
UNITSTYLE_INT = 0
UNITSTYLE_FLOAT = 1
UNITSTYLE_TIME = 2
UNITSTYLE_HZ = 3
UNITSTYLE_DB = 4
UNITSTYLE_PERCENT = 5
UNITSTYLE_PAN = 6
UNITSTYLE_SEMITONE = 7
UNITSTYLE_MIDI = 8
UNITSTYLE_CUSTOM = 9
UNITSTYLE_NATIVE = 10
