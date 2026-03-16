"""Analog Supersaw - Instrument example.

Demonstrates: analog_oscillator_bank (8 oscillators), notein for MIDI input,
lowpass_filter for tone shaping, adsr_envelope for amplitude,
live_gain for output level.

Architecture:
  notein → mtof → analog_oscillator_bank (8 phasors, spread detune)
  → lowpass_filter (tone) → adsr_envelope (amplitude) → live.gain~ → plugout~
"""

from m4l_builder import Instrument, MIDNIGHT, device_output_path
from m4l_builder.dsp import analog_oscillator_bank, notein, lowpass_filter, adsr_envelope

WIDTH = 400
HEIGHT = 240
device = Instrument("Analog Supersaw", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

# Oscilloscope at the top -- shows the output waveform
device.add_scope("osc_scope", [8, 8, WIDTH - 16, 55],
                 bgcolor=[0.05, 0.05, 0.06, 1.0],
                 gridcolor=[0.15, 0.15, 0.17, 0.3],
                 fgcolor=MIDNIGHT.accent)

# Section labels
device.add_comment("lbl_osc", [8, 68, 60, 12], "OSCILLATOR",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_filter", [140, 68, 50, 12], "FILTER",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_env", [240, 68, 60, 12], "ENVELOPE",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_out", [350, 68, 50, 12], "OUTPUT",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Detune spread dial
device.add_dial("detune_dial", "Detune", [8, 80, 50, 70],
                min_val=0.0, max_val=50.0, initial=12.0,
                unitstyle=0, appearance=1,
                annotation_name="Supersaw detune spread in cents (0-50)")

# Frequency display
device.add_number_box("freq_numbox", "Freq", [70, 80, 60, 18],
                      min_val=20.0, max_val=20000.0, initial=440.0,
                      unitstyle=3, shortname="Hz")

# Filter dials
device.add_dial("cutoff_dial", "Cutoff", [140, 80, 50, 70],
                min_val=20.0, max_val=20000.0, initial=3000.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1,
                annotation_name="Lowpass filter cutoff frequency")
device.add_dial("res_dial", "Res", [200, 80, 30, 70],
                min_val=0.0, max_val=100.0, initial=15.0,
                unitstyle=5, appearance=1,
                annotation_name="Filter resonance")

# ADSR dials
device.add_dial("attack_dial", "A", [240, 80, 24, 70],
                min_val=1.0, max_val=2000.0, initial=10.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Attack time in ms")
device.add_dial("decay_dial", "D", [268, 80, 24, 70],
                min_val=1.0, max_val=2000.0, initial=150.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Decay time in ms")
device.add_dial("sustain_dial", "S", [296, 80, 24, 70],
                min_val=0.0, max_val=100.0, initial=60.0,
                unitstyle=5, appearance=1,
                annotation_name="Sustain level 0-100%")
device.add_dial("release_dial", "R", [324, 80, 24, 70],
                min_val=1.0, max_val=4000.0, initial=300.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Release time in ms")

# Master volume with live.gain~
device.add_live_gain("gain", "Volume", [360, 80, 30, 155],
                     min_val=-70.0, max_val=6.0, initial=0.0,
                     orientation=1, shortname="Vol")

# =========================================================================
# DSP objects
# =========================================================================

# MIDI input → mtof
ni_boxes, ni_lines = notein("midi")
for b in ni_boxes:
    device.add_box(b)

device.add_newobj("mtof", "mtof", numinlets=1, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 320, 40, 20])
device.add_newobj("freq_store", "f 440.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 350, 40, 20])

# Detune store: receives dial value, used for per-voice detuning
device.add_newobj("detune_store", "f 12.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[100, 350, 40, 20])

# Trigger: fans base freq to all 8 oscillator detune exprs
device.add_newobj("freq_trig", "t f f f f f f f f", numinlets=1, numoutlets=8,
                  outlettype=["", "", "", "", "", "", "", ""],
                  patching_rect=[30, 380, 140, 20])

# analog_oscillator_bank: 8 phasors with spread detune
osc_boxes, osc_lines = analog_oscillator_bank("osc", num_oscs=8)
for b in osc_boxes:
    device.add_box(b)
for l in osc_lines:
    device.lines.append(l)

# Scale sum by 1/8 to prevent clipping
device.add_newobj("osc_scale", "*~ 0.125", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 560, 55, 20])

# Lowpass filter
lp_boxes, lp_lines = lowpass_filter("lp")
for b in lp_boxes:
    device.add_box(b)
for l in lp_lines:
    device.lines.append(l)

# Cutoff and resonance smoothing
device.add_newobj("cut_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 560, 60, 20])
device.add_newobj("cut_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 590, 40, 20])
device.add_newobj("res_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[260, 560, 120, 20])
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[260, 590, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[260, 620, 40, 20])

# ADSR envelope
adsr_boxes, adsr_lines = adsr_envelope("env", attack_ms=10, decay_ms=150,
                                        sustain=0.6, release_ms=300)
for b in adsr_boxes:
    device.add_box(b)

# Sustain scale: 0-100% → 0-1
device.add_newobj("sus_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 560, 120, 20])

# Amplitude multiplier: filtered signal * envelope
device.add_newobj("amp_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 660, 40, 20])
device.add_newobj("amp_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 660, 40, 20])

# plugout~ (Instrument class doesn't auto-add I/O)
device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[30, 720, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# MIDI: notein → mtof → freq_store → freq_trig
device.add_line("midi_notein", 0, "mtof", 0)
device.add_line("mtof", 0, "freq_store", 0)
device.add_line("freq_store", 0, "freq_trig", 0)
device.add_line("freq_store", 0, "freq_numbox", 0)

# Detune dial → detune_store
device.add_line("detune_dial", 0, "detune_store", 1)

# freq_trig → each oscillator detune expr (8 voices)
for i in range(8):
    device.add_line("freq_trig", i, f"osc_detune_{i}", 0)
    device.add_line("detune_store", 0, f"osc_detune_{i}", 0)

# Oscillator sum → scale → filter
device.add_line("osc_sum", 0, "osc_scale", 0)
device.add_line("osc_scale", 0, "lp_l", 0)
device.add_line("osc_scale", 0, "lp_r", 0)

# Cutoff and resonance smoothing
device.add_line("cutoff_dial", 0, "cut_pk", 0)
device.add_line("cut_pk", 0, "cut_ln", 0)
device.add_line("cut_ln", 0, "lp_l", 1)
device.add_line("cut_ln", 0, "lp_r", 1)
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "lp_l", 2)
device.add_line("res_ln", 0, "lp_r", 2)

# ADSR: velocity from notein → envelope trigger
# notein outlet 1 = velocity, outlet 0 = note number
device.add_line("midi_notein", 1, "env_adsr", 0)

# ADSR parameter controls
device.add_line("attack_dial", 0, "env_adsr", 1)
device.add_line("decay_dial", 0, "env_adsr", 2)
device.add_line("sus_scale", 0, "env_adsr", 3)
device.add_line("release_dial", 0, "env_adsr", 4)
device.add_line("sustain_dial", 0, "sus_scale", 0)

# Filter output * envelope → amplitude multipliers
device.add_line("lp_out_l", 0, "amp_l", 0)
device.add_line("lp_out_r", 0, "amp_r", 0)
device.add_line("env_adsr", 0, "amp_l", 1)
device.add_line("env_adsr", 0, "amp_r", 1)

# Amplitude → live.gain~ → plugout~
device.add_line("amp_l", 0, "gain", 0)
device.add_line("amp_r", 0, "gain", 1)
device.add_line("gain", 0, "plugout", 0)
device.add_line("gain", 1, "plugout", 1)

# Scope wiring -- show output waveform
device.add_line("amp_l", 0, "osc_scope", 0)
device.add_line("amp_r", 0, "osc_scope", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Analog Supersaw", device_type="instrument", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
