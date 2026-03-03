"""m4l_builder — Programmatically build Max for Live (.amxd) devices."""

from .device import Device, AudioEffect, Instrument, MidiEffect
from .container import build_amxd, write_amxd
from .objects import newobj, patchline
from .ui import (panel, dial, tab, toggle, comment, scope, meter, menu,
                 number_box, slider, button, live_text, fpic, live_gain,
                 multislider, jsui, adsrui, live_drop, bpatcher, swatch,
                 textedit, live_step, live_grid, live_line, live_arrows,
                 rslider, kslider, textbutton, umenu, radiogroup, nodes,
                 matrixctrl, ubutton, nslider)
from .theme import Theme, MIDNIGHT, WARM, COOL, LIGHT
from .dsp import (stereo_io, gain_stage, dry_wet_mix, ms_encode_decode,
                   dc_block, saturation, selector, highpass_filter,
                   lowpass_filter, onepole_filter, signal_divide, tilt_eq,
                   crossover_3band, envelope_follower, delay_line, lfo,
                   comb_resonator, feedback_delay, tremolo,
                   param_smooth, bandpass_filter, notch_filter,
                   highshelf_filter, lowshelf_filter,
                   compressor, limiter, noise_source, tempo_sync,
                   live_remote, live_param_signal, adsr_envelope,
                   peaking_eq, allpass_filter)
from .constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .paths import user_library, device_output_path

__all__ = [
    "Device", "AudioEffect", "Instrument", "MidiEffect",
    "build_amxd", "write_amxd",
    "newobj", "patchline",
    "panel", "dial", "tab", "toggle", "comment", "scope", "meter", "menu",
    "number_box", "slider", "button",
    "live_text", "fpic", "live_gain", "multislider", "jsui",
    "adsrui", "live_drop", "bpatcher", "swatch", "textedit",
    "live_step", "live_grid", "live_line", "live_arrows",
    "rslider", "kslider", "textbutton", "umenu", "radiogroup",
    "nodes", "matrixctrl", "ubutton", "nslider",
    "Theme", "MIDNIGHT", "WARM", "COOL", "LIGHT",
    "stereo_io", "gain_stage", "dry_wet_mix", "ms_encode_decode",
    "dc_block", "saturation", "selector", "highpass_filter",
    "lowpass_filter", "onepole_filter", "signal_divide", "tilt_eq",
    "crossover_3band", "envelope_follower", "delay_line", "lfo",
    "comb_resonator", "feedback_delay", "tremolo",
    "param_smooth", "bandpass_filter", "notch_filter",
    "highshelf_filter", "lowshelf_filter",
    "compressor", "limiter", "noise_source", "tempo_sync",
    "live_remote", "live_param_signal", "adsr_envelope",
    "peaking_eq", "allpass_filter",
    "AUDIO_EFFECT", "INSTRUMENT", "MIDI_EFFECT",
    "user_library", "device_output_path",
]
