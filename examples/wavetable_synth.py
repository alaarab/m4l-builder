"""Wavetable synthesizer — Instrument example.

Two wavetable~ oscillators with cross-fade, detune, lowpass filter,
ADSR envelope, and a jsui waveform preview display.

Signal flow:
  MIDI in -> mtof -> osc1 freq, osc2 freq (with detune)
  osc1 + osc2 -> xfade -> lowpass filter -> ADSR amplitude -> live.gain~ -> plugout~
"""

from m4l_builder import Instrument, MIDNIGHT, device_output_path, wavetable_display_js
from m4l_builder import WAVETABLE_DISPLAY_INLETS, WAVETABLE_DISPLAY_OUTLETS
from m4l_builder.dsp import wavetable_osc, buffer_load, lowpass_filter, adsr_envelope

WIDTH = 420
HEIGHT = 220
device = Instrument("Wavetable Synth", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])

device.add_comment("title", [8, 5, 100, 16], "WAVETABLE",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Section labels
device.add_comment("lbl_osc", [8, 22, 60, 12], "OSCILLATORS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_filt", [8, 112, 50, 12], "FILTER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_env", [130, 112, 50, 12], "ENVELOPE",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_out", [310, 22, 60, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Wavetable selection menus
device.add_menu("wt1_menu", "Wt1 Shape", [8, 32, 80, 20],
                ["Sine", "Triangle", "Saw", "Square", "Noise"])
device.add_menu("wt2_menu", "Wt2 Shape", [8, 58, 80, 20],
                ["Sine", "Triangle", "Saw", "Square", "Noise"])

# Detune dial: -50 to +50 cents
device.add_dial("detune_dial", "Detune", [96, 32, 50, 60],
                min_val=-50.0, max_val=50.0, initial=0.0,
                unitstyle=7, appearance=1,
                annotation_name="Detune osc2 relative to osc1 in cents")

# Crossfade slider: osc1 <-> osc2
device.add_slider("xfade_slider", "Mix", [152, 32, 120, 18],
                  min_val=0.0, max_val=1.0, initial=0.5,
                  unitstyle=1, orientation=0, shortname="Xfade")
device.add_comment("lbl_xf_l", [152, 52, 30, 12], "OSC1",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])
device.add_comment("lbl_xf_r", [242, 52, 30, 12], "OSC2",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Waveform preview (jsui)
device.add_jsui("wt_display", [152, 62, 120, 42],
                js_code=wavetable_display_js(),
                numinlets=WAVETABLE_DISPLAY_INLETS,
                numoutlets=WAVETABLE_DISPLAY_OUTLETS)

# Filter dials
device.add_dial("cutoff_dial", "Cutoff", [8, 124, 50, 60],
                min_val=20.0, max_val=20000.0, initial=2000.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1,
                annotation_name="Lowpass filter cutoff frequency")
device.add_dial("res_dial", "Res", [68, 124, 50, 60],
                min_val=0.0, max_val=100.0, initial=15.0,
                unitstyle=5, appearance=1,
                annotation_name="Filter resonance")

# ADSR dials
device.add_dial("atk_dial", "Attack", [130, 124, 40, 60],
                min_val=1.0, max_val=5000.0, initial=10.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Envelope attack time in ms")
device.add_dial("dec_dial", "Decay", [176, 124, 40, 60],
                min_val=1.0, max_val=5000.0, initial=200.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Envelope decay time in ms")
device.add_dial("sus_dial", "Sustain", [222, 124, 40, 60],
                min_val=0.0, max_val=100.0, initial=70.0,
                unitstyle=5, appearance=1,
                annotation_name="Envelope sustain level")
device.add_dial("rel_dial", "Release", [268, 124, 40, 60],
                min_val=1.0, max_val=8000.0, initial=300.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Envelope release time in ms")

# Master gain
device.add_live_gain("gain", "Volume", [310, 32, 100, 175],
                     min_val=-70.0, max_val=6.0, initial=0.0,
                     orientation=1, shortname="Vol")

# =========================================================================
# DSP objects
# =========================================================================

# MIDI input chain
device.add_newobj("midiin", "midiin", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[30, 30, 50, 20])
device.add_newobj("midiparse", "midiparse", numinlets=1, numoutlets=7,
                  outlettype=["int", "int", "int", "int", "int", "int", "int"],
                  patching_rect=[30, 60, 70, 20])
device.add_newobj("mtof", "mtof", numinlets=1, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 90, 40, 20])

# Detune: osc2 frequency = base_hz * pow(2, detune_cents / 1200)
device.add_newobj("detune_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[150, 90, 40, 20])
device.add_newobj("freq_store", "f 220.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[90, 90, 40, 20])
device.add_newobj("freq_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[90, 120, 45, 20])
device.add_newobj("osc2_freq", "expr $f1 * pow(2.0, $f2 / 1200.0)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 120, 200, 20])

# Wavetable oscillators
wt1_boxes, wt1_lines = wavetable_osc("osc1")
wt2_boxes, wt2_lines = wavetable_osc("osc2")
for b in wt1_boxes + wt2_boxes:
    device.add_box(b)
for l in wt1_lines + wt2_lines:
    device.lines.append(l)

# Buffers for each oscillator
buf1_boxes, _ = buffer_load("buf1", "wt_buf1", 2048)
buf2_boxes, _ = buffer_load("buf2", "wt_buf2", 2048)
for b in buf1_boxes + buf2_boxes:
    device.add_box(b)

# Cross-fade: osc1 and osc2 -> xfade with *~ and +~
device.add_newobj("xf_store", "f 0.5", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[450, 150, 40, 20])
device.add_newobj("xf_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 180, 45, 20])
device.add_newobj("xf_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[450, 120, 45, 20])
device.add_newobj("vol_osc1", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[510, 180, 50, 20])
device.add_newobj("vol_osc2", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[570, 180, 50, 20])
device.add_newobj("osc_mix", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[530, 210, 30, 20])

# Lowpass filter
lp_boxes, lp_lines = lowpass_filter("lp")
for b in lp_boxes:
    device.add_box(b)
for l in lp_lines:
    device.lines.append(l)

# Resonance scaling: 0-100% -> 0-1
device.add_newobj("res_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[600, 240, 120, 20])

# ADSR envelope
adsr_boxes, adsr_lines = adsr_envelope("env", attack_ms=10, decay_ms=200,
                                        sustain=0.7, release_ms=300)
for b in adsr_boxes:
    device.add_box(b)
for l in adsr_lines:
    device.lines.append(l)

# Sustain scaling: 0-100% -> 0-1
device.add_newobj("sus_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[650, 300, 120, 20])

# VCA: multiply filter output by envelope
device.add_newobj("vca_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[620, 350, 30, 20])
device.add_newobj("vca_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[660, 350, 30, 20])

# plugout~
device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[640, 420, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# MIDI chain
device.add_line("midiin", 0, "midiparse", 0)
device.add_line("midiparse", 0, "mtof", 0)
device.add_line("mtof", 0, "freq_store", 0)
device.add_line("freq_store", 0, "freq_trig", 0)

# Detune dial -> detune_store
device.add_line("detune_dial", 0, "detune_store", 1)

# Freq triggers: osc1 gets direct freq, osc2 gets detuned
device.add_line("freq_trig", 0, "osc1_wt", 0)        # outlet 0 -> osc1
device.add_line("freq_trig", 1, "osc2_freq", 0)       # outlet 1 -> osc2 expr
device.add_line("detune_store", 0, "osc2_freq", 1)
device.add_line("osc2_freq", 0, "osc2_wt", 0)

# Wavetable menus -> wavetable~ index inlet (inlet 1)
device.add_line("wt1_menu", 0, "osc1_wt", 1)
device.add_line("wt2_menu", 0, "osc2_wt", 1)

# Cross-fade
device.add_line("xfade_slider", 0, "xf_trig", 0)
device.add_line("xf_trig", 0, "vol_osc2", 1)      # right outlet fires first
device.add_line("xf_trig", 1, "xf_inv", 0)
device.add_line("xf_inv", 0, "vol_osc1", 1)
device.add_line("osc1_wt", 0, "vol_osc1", 0)
device.add_line("osc2_wt", 0, "vol_osc2", 0)
device.add_line("vol_osc1", 0, "osc_mix", 0)
device.add_line("vol_osc2", 0, "osc_mix", 1)

# Filter: osc_mix -> both LP filter inlets
device.add_line("osc_mix", 0, "lp_l", 0)
device.add_line("osc_mix", 0, "lp_r", 0)

# Cutoff dial -> filter inlets 1
device.add_line("cutoff_dial", 0, "lp_l", 1)
device.add_line("cutoff_dial", 0, "lp_r", 1)

# Resonance dial -> scale -> filter inlets 2
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "lp_l", 2)
device.add_line("res_scale", 0, "lp_r", 2)

# ADSR controls: note on from midiparse outlet 0 and 1 (note, velocity)
device.add_line("midiparse", 1, "env_adsr", 0)   # velocity gates envelope
device.add_line("atk_dial", 0, "env_adsr", 1)
device.add_line("dec_dial", 0, "env_adsr", 2)
device.add_line("sus_dial", 0, "sus_scale", 0)
device.add_line("sus_scale", 0, "env_adsr", 3)
device.add_line("rel_dial", 0, "env_adsr", 4)

# VCA: filter output * envelope
device.add_line("lp_out_l", 0, "vca_l", 0)
device.add_line("lp_out_r", 0, "vca_r", 0)
device.add_line("env_adsr", 0, "vca_l", 1)
device.add_line("env_adsr", 0, "vca_r", 1)

# live.gain~ then plugout~
device.add_line("vca_l", 0, "gain", 0)
device.add_line("vca_r", 0, "gain", 1)
device.add_line("gain", 0, "plugout", 0)
device.add_line("gain", 1, "plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Wavetable Synth", device_type="instrument")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
