"""Lookup tables and operator specs for the legacy-device reverse tool.

Extracted from _reverse_legacy.py (god-file split); re-exported by it."""
from __future__ import annotations

import copy
import os
import pprint
import re
from pathlib import Path
from typing import Any

from .constants import AMXD_TYPE, AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .device import Device
from .live_api import (
    device_active_state,
    live_object_path,
    live_observer,
    live_parameter_probe,
    live_set_control,
    live_state_observer,
    live_thisdevice,
)
from .recipes import (
    dry_wet_stage,
    gain_controlled_stage,
    midi_note_gate,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)

TYPE_CODE_TO_DEVICE_TYPE = {
    AUDIO_EFFECT: "audio_effect",
    INSTRUMENT: "instrument",
    MIDI_EFFECT: "midi_effect",
}

DEVICE_TYPE_TO_CODE_CONSTANT = {
    "audio_effect": "AUDIO_EFFECT",
    "instrument": "INSTRUMENT",
    "midi_effect": "MIDI_EFFECT",
}

DEVICE_TYPE_TO_CLASS = {
    "audio_effect": "AudioEffect",
    "instrument": "Instrument",
    "midi_effect": "MidiEffect",
}

AMXD_INT_TO_DEVICE_TYPE = {value: key for key, value in AMXD_TYPE.items()}

UI_MAXCLASSES = {
    "panel",
    "live.comment",
    "live.dial",
    "live.drop",
    "live.grid",
    "live.line",
    "live.menu",
    "live.meter~",
    "live.numbox",
    "live.scope~",
    "live.step",
    "live.slider",
    "live.tab",
    "live.text",
    "live.toggle",
    "live.adsrui",
    "live.arrows",
    "multislider",
    "fpic",
    "jsui",
    "v8ui",
    "bpatcher",
    "swatch",
    "textedit",
    "textbutton",
    "umenu",
    "radiogroup",
    "rslider",
    "kslider",
    "nodes",
    "matrixctrl",
    "ubutton",
    "nslider",
}

PARAMETER_MAXCLASSES = {
    "live.dial",
    "live.menu",
    "live.numbox",
    "live.slider",
    "live.tab",
    "live.text",
    "live.toggle",
}

BRIDGE_TEXT_MARKERS = (
    "livemcp_bridge_runtime.js",
    "livemcp_bridge_server.js",
)

BUS_OPERATOR_SPECS = {
    "s": {"signal": False, "direction": "send"},
    "send": {"signal": False, "direction": "send"},
    "r": {"signal": False, "direction": "receive"},
    "receive": {"signal": False, "direction": "receive"},
    "s~": {"signal": True, "direction": "send"},
    "send~": {"signal": True, "direction": "send"},
    "r~": {"signal": True, "direction": "receive"},
    "receive~": {"signal": True, "direction": "receive"},
}

LIVE_API_CORE_OPERATORS = {
    "live.thisdevice",
    "live.path",
    "live.object",
    "live.observer",
    "live.remote~",
    "live.banks",
}

LIVE_API_HELPER_OPERATORS = {
    "route",
    "prepend",
    "deferlow",
    "sel",
    "gate",
    "pack",
    "unpack",
    "trigger",
    "t",
}

CONTROLLER_DISPATCH_OPERATORS = {
    "route",
    "sel",
    "gate",
    "switch",
    "gswitch",
    "split",
    "trigger",
    "t",
}

SCHEDULER_OPERATORS = {
    "loadbang",
    "loadmess",
    "deferlow",
    "delay",
    "del",
    "pipe",
    "onebang",
    "trigger",
    "t",
}

STATE_BUNDLE_OPERATORS = {
    "pack",
    "pak",
    "unpack",
    "buddy",
    "join",
}

EMBEDDED_PATCHER_OPERATORS = {
    "p",
    "poly~",
    "gen~",
    "pfft~",
}

SAMPLE_BUFFER_CORE_OPERATORS = {
    "buffer~",
    "info~",
    "peek~",
    "poke~",
    "play~",
    "record~",
    "groove~",
    "waveform~",
    "polybuffer~",
}

SAMPLE_BUFFER_HELPER_OPERATORS = {
    "b",
    "date",
    "defer",
    "deferlow",
    "delay",
    "del",
    "gate",
    "i",
    "info~",
    "join",
    "metro",
    "pack",
    "prepend",
    "regexp",
    "relativepath",
    "route",
    "sel",
    "sprintf",
    "strippath",
    "t",
    "trigger",
    "unpack",
    "uzi",
    "zl",
    "zl.compare",
    "zl.join",
    "zl.reg",
    "zl.slice",
}

GEN_PROCESSING_CORE_OPERATORS = {
    "gen~",
    "mc.gen~",
}

GEN_PROCESSING_HELPER_OPERATORS = {
    "buffer~",
    "click~",
    "defer",
    "deferlow",
    "delay",
    "del",
    "gate",
    "i",
    "in",
    "info~",
    "metro",
    "out",
    "p",
    "pack",
    "peek~",
    "prepend",
    "route",
    "sel",
    "t",
    "trigger",
    "unpack",
    "uzi",
}

DEFAULT_AUDIO_IO_BOXES = {
    "obj-plugin": {
        "text": "plugin~",
        "patching_rect": [30, 30, 60, 20],
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["signal", "signal"],
    },
    "obj-plugout": {
        "text": "plugout~",
        "patching_rect": [30, 200, 60, 20],
        "numinlets": 2,
        "numoutlets": 2,
    },
}

# (valueof key, factory kwarg) for the extended param-metadata fields the
# parameter factories (will) accept. Each guarded by `if key in valueof`, so an
# entry is inert until both the device emits the valueof field AND the factory
# accepts the kwarg — pre-wiring the A2/E1/E4 round-trip without rippling today.
_EXTENDED_PARAM_VALUEOF_KWARGS = (
    ("parameter_annotation_name", "annotation_name"),
    ("parameter_info", "info"),
    ("parameter_units", "units"),
    ("parameter_steps", "steps"),
)

__all__ = [
    "TYPE_CODE_TO_DEVICE_TYPE",
    "DEVICE_TYPE_TO_CODE_CONSTANT",
    "DEVICE_TYPE_TO_CLASS",
    "AMXD_INT_TO_DEVICE_TYPE",
    "UI_MAXCLASSES",
    "PARAMETER_MAXCLASSES",
    "BRIDGE_TEXT_MARKERS",
    "BUS_OPERATOR_SPECS",
    "LIVE_API_CORE_OPERATORS",
    "LIVE_API_HELPER_OPERATORS",
    "CONTROLLER_DISPATCH_OPERATORS",
    "SCHEDULER_OPERATORS",
    "STATE_BUNDLE_OPERATORS",
    "EMBEDDED_PATCHER_OPERATORS",
    "SAMPLE_BUFFER_CORE_OPERATORS",
    "SAMPLE_BUFFER_HELPER_OPERATORS",
    "GEN_PROCESSING_CORE_OPERATORS",
    "GEN_PROCESSING_HELPER_OPERATORS",
    "DEFAULT_AUDIO_IO_BOXES",
    "_EXTENDED_PARAM_VALUEOF_KWARGS",
]

