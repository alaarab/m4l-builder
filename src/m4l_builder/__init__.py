"""m4l_builder — Programmatically build Max for Live (.amxd) devices."""

from .device import Device, AudioEffect, Instrument, MidiEffect
from .container import build_amxd, write_amxd
from .objects import newobj, patchline
from .ui import (panel, dial, tab, toggle, comment, scope, meter, menu,
                 number_box, slider, button, live_text, fpic, live_gain,
                 multislider, jsui)
from .theme import Theme, MIDNIGHT, WARM, COOL, LIGHT
from .dsp import (stereo_io, gain_stage, dry_wet_mix, ms_encode_decode,
                   dc_block, saturation, selector, highpass_filter,
                   lowpass_filter, onepole_filter, signal_divide, tilt_eq,
                   crossover_3band, envelope_follower, delay_line, lfo,
                   comb_resonator, feedback_delay, tremolo)
from .constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT

__all__ = [
    "Device", "AudioEffect", "Instrument", "MidiEffect",
    "build_amxd", "write_amxd",
    "newobj", "patchline",
    "panel", "dial", "tab", "toggle", "comment", "scope", "meter", "menu",
    "number_box", "slider", "button",
    "live_text", "fpic", "live_gain", "multislider", "jsui",
    "Theme", "MIDNIGHT", "WARM", "COOL", "LIGHT",
    "stereo_io", "gain_stage", "dry_wet_mix", "ms_encode_decode",
    "dc_block", "saturation", "selector", "highpass_filter",
    "lowpass_filter", "onepole_filter", "signal_divide", "tilt_eq",
    "crossover_3band", "envelope_follower", "delay_line", "lfo",
    "comb_resonator", "feedback_delay", "tremolo",
    "AUDIO_EFFECT", "INSTRUMENT", "MIDI_EFFECT",
]
