"""m4l_builder: Programmatically build Max for Live (.amxd) devices."""

from .device import Device, AudioEffect, Instrument, MidiEffect
from .subpatcher import Subpatcher
from .container import build_amxd, write_amxd
from .layout import Row, Column, Grid
from .objects import newobj, patchline
from .ui import (panel, dial, tab, toggle, comment, scope, meter, menu,
                 number_box, slider, button, live_text, fpic, live_gain,
                 multislider, jsui, adsrui, live_drop, bpatcher, swatch,
                 textedit, live_step, live_grid, live_line, live_arrows,
                 rslider, kslider, textbutton, umenu, radiogroup, nodes,
                 matrixctrl, ubutton, nslider)
from .theme import Theme, MIDNIGHT, WARM, COOL, LIGHT, FOREST, VIOLET, SOLAR
from .dsp import (stereo_io, gain_stage, dry_wet_mix, ms_encode_decode,
                   dc_block, saturation, selector, highpass_filter,
                   lowpass_filter, onepole_filter, signal_divide, tilt_eq,
                   crossover_3band, envelope_follower, delay_line, lfo,
                   comb_resonator, feedback_delay, tremolo,
                   param_smooth, bandpass_filter, notch_filter,
                   highshelf_filter, lowshelf_filter,
                   compressor, limiter, noise_source, tempo_sync,
                   live_remote, live_param_signal, adsr_envelope,
                   peaking_eq, allpass_filter,
                   gate_expander, sidechain_detect, sample_and_hold,
                   multiband_compressor, reverb_network,
                   notein, noteout, ctlin, ctlout, velocity_curve,
                   transpose, midi_thru,
                   wavetable_osc, buffer_load, arpeggiator, chord,
                   pitch_quantize, lookahead_envelope_follower, fdn_reverb,
                   spectral_gate, spectral_gate_subpatcher, vocoder,
                   mc_expand, mc_collapse, note_expression_decode,
                   transport_lfo, pitchbend_in, modwheel_in, aftertouch_in,
                   xfade_matrix, midi_learn_chain, convolver,
                   program_change_in, bank_select_in,
                   sample_and_hold_triggered, bitcrusher,
                   poly_voices, spectral_crossover,
                   spectral_crossover_subpatcher, grain_cloud,
                   auto_gain, midi_clock_out, macromap,
                   stft_phase_vocoder, phase_vocoder_subpatcher,
                   spectrum_band_extract, morphing_lfo,
                   midi_clock_in, sidechain_routing, random_walk,
                   matrix_mixer, cv_recorder, quantize_time,
                   macro_modulation_matrix, analog_oscillator_bank,
                   lfsr_generator, cv_smooth_lag,
                   send_signal, receive_signal, send_msg, receive_msg,
                   loadbang, scale_range, groove_player,
                   coll_store, dict_store, pattr_system,
                   midi_channel_filter)
from .engines.xy_pad import xy_pad_js, XY_PAD_INLETS, XY_PAD_OUTLETS
from .engines.piano_roll import piano_roll_js, PIANO_ROLL_INLETS, PIANO_ROLL_OUTLETS
from .engines.velocity_curve_display import (velocity_curve_display_js,
                                              VELOCITY_CURVE_INLETS,
                                              VELOCITY_CURVE_OUTLETS)
from .engines.wavetable_display import (wavetable_display_js,
                                         WAVETABLE_DISPLAY_INLETS,
                                         WAVETABLE_DISPLAY_OUTLETS)
from .engines.resonance_bank_display import (resonance_bank_display_js,
                                              RESONANCE_BANK_INLETS,
                                              RESONANCE_BANK_OUTLETS)
from .engines.sidechain_display import (sidechain_display_js,
                                         SIDECHAIN_DISPLAY_INLETS,
                                         SIDECHAIN_DISPLAY_OUTLETS)
from .engines.spectral_display import (spectral_display_js,
                                        SPECTRAL_DISPLAY_INLETS,
                                        SPECTRAL_DISPLAY_OUTLETS)
from .engines.peaking_eq_display import (peaking_eq_display_js,
                                          PEAKING_EQ_DISPLAY_INLETS,
                                          PEAKING_EQ_DISPLAY_OUTLETS)
from .engines.step_grid_display import (step_grid_display_js,
                                         STEP_GRID_DISPLAY_INLETS,
                                         STEP_GRID_DISPLAY_OUTLETS)
from .engines.grain_display import (grain_display_js,
                                     GRAIN_DISPLAY_INLETS,
                                     GRAIN_DISPLAY_OUTLETS)
from .engines.grid_sequencer_display import (grid_sequencer_display_js,
                                              GRID_SEQ_INLETS,
                                              GRID_SEQ_OUTLETS)
from .engines.wavetable_editor import (wavetable_editor_js,
                                        WAVETABLE_EDITOR_INLETS,
                                        WAVETABLE_EDITOR_OUTLETS)
from .engines.spectral_vocoder_display import (spectral_vocoder_display_js,
                                                SPECTRAL_VOCODER_INLETS,
                                                SPECTRAL_VOCODER_OUTLETS)
from .constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .paths import user_library, device_output_path
from .live_api import live_object_path, live_observer, live_set_control
from .presets import preset_manager, add_preset_buttons
from .recipes import (gain_controlled_stage, dry_wet_stage,
                      tempo_synced_delay, midi_note_gate)

__all__ = [
    "Device", "AudioEffect", "Instrument", "MidiEffect", "Subpatcher",
    "Row", "Column", "Grid",
    "build_amxd", "write_amxd",
    "newobj", "patchline",
    "panel", "dial", "tab", "toggle", "comment", "scope", "meter", "menu",
    "number_box", "slider", "button",
    "live_text", "fpic", "live_gain", "multislider", "jsui",
    "adsrui", "live_drop", "bpatcher", "swatch", "textedit",
    "live_step", "live_grid", "live_line", "live_arrows",
    "rslider", "kslider", "textbutton", "umenu", "radiogroup",
    "nodes", "matrixctrl", "ubutton", "nslider",
    "Theme", "MIDNIGHT", "WARM", "COOL", "LIGHT", "FOREST", "VIOLET", "SOLAR",
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
    "gate_expander", "sidechain_detect", "sample_and_hold",
    "multiband_compressor", "reverb_network",
    "notein", "noteout", "ctlin", "ctlout", "velocity_curve",
    "transpose", "midi_thru",
    "wavetable_osc", "buffer_load", "arpeggiator", "chord",
    "pitch_quantize", "lookahead_envelope_follower", "fdn_reverb",
    "spectral_gate", "spectral_gate_subpatcher", "vocoder",
    "mc_expand", "mc_collapse", "note_expression_decode",
    "transport_lfo", "pitchbend_in", "modwheel_in", "aftertouch_in",
    "xfade_matrix", "midi_learn_chain", "convolver",
    "program_change_in", "bank_select_in",
    "sample_and_hold_triggered", "bitcrusher",
    "poly_voices", "spectral_crossover",
    "spectral_crossover_subpatcher", "grain_cloud",
    "auto_gain", "midi_clock_out", "macromap",
    "stft_phase_vocoder", "phase_vocoder_subpatcher",
    "spectrum_band_extract", "morphing_lfo",
    "midi_clock_in", "sidechain_routing", "random_walk",
    "matrix_mixer", "cv_recorder", "quantize_time",
    "macro_modulation_matrix", "analog_oscillator_bank",
    "lfsr_generator", "cv_smooth_lag",
    "send_signal", "receive_signal", "send_msg", "receive_msg",
    "loadbang", "scale_range", "groove_player",
    "coll_store", "dict_store", "pattr_system",
    "midi_channel_filter",
    "xy_pad_js", "XY_PAD_INLETS", "XY_PAD_OUTLETS",
    "piano_roll_js", "PIANO_ROLL_INLETS", "PIANO_ROLL_OUTLETS",
    "velocity_curve_display_js", "VELOCITY_CURVE_INLETS", "VELOCITY_CURVE_OUTLETS",
    "wavetable_display_js", "WAVETABLE_DISPLAY_INLETS", "WAVETABLE_DISPLAY_OUTLETS",
    "resonance_bank_display_js", "RESONANCE_BANK_INLETS", "RESONANCE_BANK_OUTLETS",
    "sidechain_display_js", "SIDECHAIN_DISPLAY_INLETS", "SIDECHAIN_DISPLAY_OUTLETS",
    "spectral_display_js", "SPECTRAL_DISPLAY_INLETS", "SPECTRAL_DISPLAY_OUTLETS",
    "peaking_eq_display_js", "PEAKING_EQ_DISPLAY_INLETS", "PEAKING_EQ_DISPLAY_OUTLETS",
    "step_grid_display_js", "STEP_GRID_DISPLAY_INLETS", "STEP_GRID_DISPLAY_OUTLETS",
    "grain_display_js", "GRAIN_DISPLAY_INLETS", "GRAIN_DISPLAY_OUTLETS",
    "grid_sequencer_display_js", "GRID_SEQ_INLETS", "GRID_SEQ_OUTLETS",
    "wavetable_editor_js", "WAVETABLE_EDITOR_INLETS", "WAVETABLE_EDITOR_OUTLETS",
    "spectral_vocoder_display_js", "SPECTRAL_VOCODER_INLETS", "SPECTRAL_VOCODER_OUTLETS",
    "AUDIO_EFFECT", "INSTRUMENT", "MIDI_EFFECT",
    "user_library", "device_output_path",
    "live_object_path", "live_observer", "live_set_control",
    "preset_manager", "add_preset_buttons",
    "gain_controlled_stage", "dry_wet_stage",
    "tempo_synced_delay", "midi_note_gate",
]
