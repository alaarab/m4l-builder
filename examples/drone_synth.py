"""Drone pad synthesizer — Instrument example.

Demonstrates: Instrument class, add_live_gain, add_number_box, add_slider,
multi-oscillator synthesis with manual plugin~/plugout~.

Four cycle~ oscillators at different interval offsets create a lush pad:
  - Voice 0: root (unison)
  - Voice 1: one octave down (-12 semitones)
  - Voice 2: perfect fifth up (+7 semitones)
  - Voice 3: one octave up (+12 semitones)

Signal flow:
  midiin → midiparse → mtof → base frequency
  base_freq × semitone_ratios → 4x cycle~ (with detune)
  4x cycle~ → mix slider controls voice 2/3 level → sum → lowpass svf~
  svf~ → live.gain~ → plugout~

Controls:
  detune_dial:  random detune per voice (0-50 cents spread)
  cutoff_dial:  lowpass filter cutoff (20-20000 Hz)
  res_dial:     filter resonance (0-100%)
  mix_slider:   blend between root/fifth voices and octave voices
  freq_numbox:  displays current base frequency in Hz (read-only)
  gain:         live.gain~ master volume with built-in meter
  scope:        output waveform display
"""

from m4l_builder import Instrument, MIDNIGHT, device_output_path

WIDTH = 350
HEIGHT = 200
device = Instrument("Drone Synth", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])


# Section labels
device.add_comment("lbl_osc", [8, 22, 60, 12], "OSCILLATOR",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_filter", [8, 92, 50, 12], "FILTER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_output", [220, 22, 60, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("detune_dial", "Detune", [8, 32, 50, 55],
                min_val=0.0, max_val=50.0, initial=8.0,
                unitstyle=0, appearance=1,
                annotation_name="Oscillator detune spread in cents")

device.add_slider("mix_slider", "Voice Mix", [70, 32, 130, 20],
                  min_val=0.0, max_val=1.0, initial=0.5,
                  unitstyle=1, orientation=0,
                  shortname="Mix")
device.add_comment("lbl_mix_l", [70, 54, 40, 12], "ROOT",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])
device.add_comment("lbl_mix_r", [160, 54, 40, 12], "5TH",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Base frequency display (shows current MIDI note as Hz, read-only)
device.add_number_box("freq_numbox", "Freq", [70, 66, 60, 18],
                      min_val=20.0, max_val=20000.0, initial=220.0,
                      unitstyle=3,    # Hz display
                      shortname="Hz")

# Filter dials
device.add_dial("cutoff_dial", "Cutoff", [8, 104, 50, 60],
                min_val=20.0, max_val=20000.0, initial=800.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1,
                annotation_name="Lowpass filter cutoff frequency")

device.add_dial("res_dial", "Res", [70, 104, 50, 60],
                min_val=0.0, max_val=100.0, initial=20.0,
                unitstyle=5, appearance=1,
                annotation_name="Filter resonance")

device.add_scope("scope", [140, 104, 70, 60],
                 smooth=2, line_width=1.5, calccount=128)

# only example using add_live_gain (has meter built in)
device.add_live_gain("gain", "Volume", [220, 32, 120, 155],
                     min_val=-70.0, max_val=6.0, initial=0.0,
                     orientation=1,   # vertical
                     shortname="Vol")

# =========================================================================
# DSP objects
# =========================================================================

# MIDI input chain: midiin → midiparse → note pitch → mtof
device.add_newobj("midiin", "midiin", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"],
                  patching_rect=[30, 30, 50, 20])

device.add_newobj("midiparse", "midiparse", numinlets=1, numoutlets=7,
                  outlettype=["int", "int", "int", "int", "int", "int", "int"],
                  patching_rect=[30, 60, 70, 20])

# mtof: converts MIDI note to Hz
device.add_newobj("mtof", "mtof", numinlets=1, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 90, 40, 20])

# Store base freq for display and oscillator calculation
device.add_newobj("freq_store", "f 220.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 120, 40, 20])

# Detune: spread in cents → convert to ratio per voice
# Each oscillator gets a slightly different frequency via mtof + small offset
# Direct Hz approach: freq = base_freq * pow(2, cents/1200) per voice
# Simpler: use cycle~ with frequency inlet, compute freq = base_freq * pow(2, cents/1200)
# For 4 voices: offsets are -detune, +detune, -detune*0.7, +detune*0.7 (cents)
# Use expr to compute Hz from base freq and cent offset:
#   Hz = base_hz * pow(2, cents/1200)
# Semitone offsets: 0 (root), -12 (octave down), +7 (fifth), +12 (octave up)
# Detune spread: voice 0 = +detune/2, voice 1 = -detune/2, voice 2 = +detune, voice 3 = -detune

# Base frequency trigger: fans to all 4 oscillator frequency calculators
device.add_newobj("freq_trig", "t f f f f", numinlets=1, numoutlets=4,
                  outlettype=["", "", "", ""],
                  patching_rect=[80, 120, 60, 20])

# Detune store (cents, 0-50)
device.add_newobj("detune_store", "f 8.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[150, 120, 40, 20])

# Per-voice frequency expressions:
# Voice 0: root + detune*0.5 cents
# Voice 1: -12 semitones = base/2, -detune*0.5 cents
# Voice 2: +7 semitones = base*1.4983, +detune cents
# Voice 3: +12 semitones = base*2, -detune cents

# expr objects compute: base_hz * pow(2.0, (semitones*100 + detune_offset) / 1200.0)
# inlet 0 = base_hz, inlet 1 = detune cents (0-50)
# $f1 = base_hz, $f2 = detune
device.add_newobj("freq_v0", "expr $f1 * pow(2.0, (0.0 * 100.0 + $f2 * 0.5) / 1200.0)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 130, 220, 20])
device.add_newobj("freq_v1", "expr $f1 * pow(2.0, (-12.0 * 100.0 - $f2 * 0.5) / 1200.0)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 160, 220, 20])
device.add_newobj("freq_v2", "expr $f1 * pow(2.0, (7.0 * 100.0 + $f2) / 1200.0)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 190, 220, 20])
device.add_newobj("freq_v3", "expr $f1 * pow(2.0, (12.0 * 100.0 - $f2) / 1200.0)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 220, 220, 20])

# cycle~ oscillators: one per voice
# cycle~ takes frequency at inlet 0
device.add_newobj("osc_v0", "cycle~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[200, 270, 45, 20])
device.add_newobj("osc_v1", "cycle~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[260, 270, 45, 20])
device.add_newobj("osc_v2", "cycle~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[320, 270, 45, 20])
device.add_newobj("osc_v3", "cycle~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[380, 270, 45, 20])

# Voice level control via mix_slider:
# mix_slider 0→1: at 0 = root+octave-down only, at 1 = fifth+octave-up only
# voices 0+1 level = (1 - mix), voices 2+3 level = mix
# Use *~ for each pair and sum
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[440, 250, 45, 20])

device.add_newobj("vol_v01", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[440, 290, 40, 20])
device.add_newobj("vol_v23", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 290, 40, 20])

# Sum all 4 oscillators (scale by 0.25 to avoid clipping)
device.add_newobj("osc_sum01", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[220, 310, 30, 20])
device.add_newobj("osc_sum23", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 310, 30, 20])

# Scale each pair by 0.25
device.add_newobj("scale_01", "*~ 0.25", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[440, 310, 50, 20])
device.add_newobj("scale_23", "*~ 0.25", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 310, 50, 20])

device.add_newobj("osc_mix", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 340, 30, 20])

# svf~ outlet 0 = LP
device.add_newobj("svf", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[460, 380, 40, 20])
device.add_newobj("lp_pass", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 410, 40, 20])

# Parameter smoothing for cutoff and resonance
device.add_newobj("cut_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 380, 60, 20])
device.add_newobj("cut_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[550, 410, 40, 20])

device.add_newobj("res_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 430, 120, 20])
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 460, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[550, 490, 40, 20])

# Mix slider smoothing
device.add_newobj("mix_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 250, 60, 20])
device.add_newobj("mix_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[550, 280, 40, 20])

# Instrument has no auto I/O; add manually
device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[460, 500, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# MIDI chain: midiin → midiparse → note pitch (outlet 0) → mtof
device.add_line("midiin", 0, "midiparse", 0)
device.add_line("midiparse", 0, "mtof", 0)       # outlet 0 = note number
device.add_line("mtof", 0, "freq_store", 0)
device.add_line("freq_store", 0, "freq_trig", 0)
# Also update freq numbox for display
device.add_line("freq_store", 0, "freq_numbox", 0)

# Detune dial → detune_store
device.add_line("detune_dial", 0, "detune_store", 1)

# freq_trig outlets fire R→L: outlet 3 first, outlet 0 last
# Each outlet fans base freq to a voice expression
device.add_line("freq_trig", 0, "freq_v0", 0)
device.add_line("freq_trig", 1, "freq_v1", 0)
device.add_line("freq_trig", 2, "freq_v2", 0)
device.add_line("freq_trig", 3, "freq_v3", 0)

# Detune store → all voice expr inlet 1
device.add_line("detune_store", 0, "freq_v0", 1)
device.add_line("detune_store", 0, "freq_v1", 1)
device.add_line("detune_store", 0, "freq_v2", 1)
device.add_line("detune_store", 0, "freq_v3", 1)

# Voice frequencies → cycle~ oscillators
device.add_line("freq_v0", 0, "osc_v0", 0)
device.add_line("freq_v1", 0, "osc_v1", 0)
device.add_line("freq_v2", 0, "osc_v2", 0)
device.add_line("freq_v3", 0, "osc_v3", 0)

# Sum oscillator pairs
device.add_line("osc_v0", 0, "osc_sum01", 0)
device.add_line("osc_v1", 0, "osc_sum01", 1)
device.add_line("osc_v2", 0, "osc_sum23", 0)
device.add_line("osc_v3", 0, "osc_sum23", 1)

# Scale pairs to 0.25
device.add_line("osc_sum01", 0, "scale_01", 0)
device.add_line("osc_sum23", 0, "scale_23", 0)

# Mix slider smoothing: slider → pack → line~
device.add_line("mix_slider", 0, "mix_pk", 0)
device.add_line("mix_pk", 0, "mix_ln", 0)

# Mix control: line~ → vol_v23 (fifth+octave pair), !-~ → vol_v01 (root pair)
device.add_line("mix_ln", 0, "vol_v23", 1)
device.add_line("mix_ln", 0, "mix_inv", 0)
device.add_line("mix_inv", 0, "vol_v01", 1)

# Apply mix gains
device.add_line("scale_01", 0, "vol_v01", 0)
device.add_line("scale_23", 0, "vol_v23", 0)

# Sum mixed voice pairs → filter
device.add_line("vol_v01", 0, "osc_mix", 0)
device.add_line("vol_v23", 0, "osc_mix", 1)

# Lowpass filter chain
device.add_line("osc_mix", 0, "svf", 0)
device.add_line("svf", 0, "lp_pass", 0)    # outlet 0 = LP

# Cutoff smoothing: cutoff_dial → pack → line~ → svf inlet 1
device.add_line("cutoff_dial", 0, "cut_pk", 0)
device.add_line("cut_pk", 0, "cut_ln", 0)
device.add_line("cut_ln", 0, "svf", 1)

# Resonance smoothing: res_dial → scale → pack → line~ → svf inlet 2
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "svf", 2)

# Scope: tap from lp_pass (mono signal, connect to both scope inputs)
device.add_line("lp_pass", 0, "scope", 0)
device.add_line("lp_pass", 0, "scope", 1)

# live.gain~ inlets: 0=L signal, 1=R signal; outlets 0=L out, 1=R out
device.add_line("lp_pass", 0, "gain", 0)
device.add_line("lp_pass", 0, "gain", 1)

# stereo out from live.gain~
device.add_line("gain", 0, "plugout", 0)
device.add_line("gain", 1, "plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Drone Synth", device_type="instrument", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
