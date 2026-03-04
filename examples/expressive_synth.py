"""Expressive Synth — Instrument with pitchbend, mod wheel, and aftertouch.

Demonstrates: pitchbend_in, modwheel_in, aftertouch_in, adsr_envelope,
lowpass_filter. Expressive MIDI controllers mapped to musically useful targets.

Signal flow:
  notein → mtof + pitchbend → cycle~ → *~ (envelope) → svf~ (cutoff+res) → plugout~
  modwheel → filter cutoff
  aftertouch → filter resonance
"""

from m4l_builder import Instrument, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, pitchbend_in, modwheel_in, aftertouch_in, adsr_envelope

WIDTH = 360
HEIGHT = 200
device = Instrument("Expressive Synth", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

device.add_comment("title", [8, 5, 100, 16], "EXPRESSIVE",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

device.add_comment("lbl_env", [8, 22, 80, 12], "ENVELOPE",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("atk_dial", "Attack", [8, 32, 45, 60],
                min_val=1.0, max_val=2000.0, initial=10.0,
                unitstyle=2, parameter_exponent=3.0, appearance=1,
                annotation_name="Attack time in ms")

device.add_dial("dec_dial", "Decay", [58, 32, 45, 60],
                min_val=1.0, max_val=2000.0, initial=100.0,
                unitstyle=2, parameter_exponent=3.0, appearance=1,
                annotation_name="Decay time in ms")

device.add_dial("sus_dial", "Sustain", [108, 32, 45, 60],
                min_val=0.0, max_val=100.0, initial=70.0,
                unitstyle=5, appearance=1,
                annotation_name="Sustain level 0-100%")

device.add_dial("rel_dial", "Release", [158, 32, 45, 60],
                min_val=1.0, max_val=4000.0, initial=200.0,
                unitstyle=2, parameter_exponent=3.0, appearance=1,
                annotation_name="Release time in ms")

device.add_comment("lbl_filter", [8, 100, 60, 12], "FILTER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("cutoff_dial", "Cutoff", [8, 110, 50, 65],
                min_val=20.0, max_val=20000.0, initial=2000.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1,
                annotation_name="Base filter cutoff — mod wheel adds to this")

device.add_comment("lbl_pb", [220, 22, 80, 12], "PITCHBEND",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_number_box("pb_display", "PB", [220, 34, 55, 18],
                      min_val=-2.0, max_val=2.0, initial=0.0,
                      unitstyle=1, shortname="PB")

device.add_comment("lbl_mw", [220, 60, 80, 12], "MOD WHEEL",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_number_box("mw_display", "MW", [220, 72, 55, 18],
                      min_val=0.0, max_val=127.0, initial=0.0,
                      unitstyle=0, shortname="MW")

device.add_comment("lbl_at", [220, 98, 80, 12], "AFTERTOUCH",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_number_box("at_display", "AT", [220, 110, 55, 18],
                      min_val=0.0, max_val=127.0, initial=0.0,
                      unitstyle=0, shortname="AT")

# =========================================================================
# DSP
# =========================================================================

# MIDI note input
ni_boxes, ni_lines = notein("ni")
for b in ni_boxes:
    device.add_box(b)

# Pitchbend: ±2 semitones
pb_boxes, pb_lines = pitchbend_in("pb", semitones=2)
for b in pb_boxes:
    device.add_box(b)
for l in pb_lines:
    device.lines.append(l)

# Mod wheel
mw_boxes, mw_lines = modwheel_in("mw")
for b in mw_boxes:
    device.add_box(b)

# Aftertouch
at_boxes, at_lines = aftertouch_in("at")
for b in at_boxes:
    device.add_box(b)

# ADSR envelope
adsr_boxes, adsr_lines = adsr_envelope("env", attack_ms=10, decay_ms=100,
                                        sustain=0.7, release_ms=200)
for b in adsr_boxes:
    device.add_box(b)

# MIDI pitch → mtof, add pitchbend semitones
device.add_newobj("mtof_note", "mtof", numinlets=1, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 280, 40, 20])
# Add pitchbend (semitones) to note number before mtof
device.add_newobj("pb_add", "+", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 250, 30, 20])
device.add_newobj("pb_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[80, 220, 40, 20])

# Base oscillator
device.add_newobj("osc", "cycle~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[30, 320, 50, 20])

# Envelope × oscillator
device.add_newobj("osc_env", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 360, 30, 20])

# Lowpass filter
device.add_newobj("svf_l", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[30, 400, 40, 20])

# Mod wheel scales to extra cutoff Hz (0-127 → 0-8000 Hz added to base cutoff)
device.add_newobj("mw_scale", "scale 0. 127. 0. 8000.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 280, 150, 20])
device.add_newobj("mw_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 310, 40, 20])
device.add_newobj("cutoff_add", "+", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 340, 40, 20])
device.add_newobj("cutoff_pk", "pack f 10", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 370, 60, 20])
device.add_newobj("cutoff_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 400, 40, 20])

# Aftertouch → resonance (0-127 → 0.0-0.95)
device.add_newobj("at_scale", "scale 0. 127. 0. 0.95", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 280, 155, 20])
device.add_newobj("at_pk", "pack f 10", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 310, 60, 20])
device.add_newobj("at_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 340, 40, 20])

# Output gain & plugout~
device.add_newobj("out_gain", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 450, 50, 20])
device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[30, 490, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# MIDI note → pitch + pitchbend → mtof → osc
device.add_line("ni_notein", 0, "pb_add", 0)
device.add_line("pb_store", 0, "pb_add", 1)
device.add_line("pb_add", 0, "mtof_note", 0)
device.add_line("mtof_note", 0, "osc", 0)

# Pitchbend scale → store and display
device.add_line("pb_scale", 0, "pb_store", 1)
device.add_line("pb_scale", 0, "pb_display", 0)

# ADSR: note on/off (velocity > 0 = on, 0 = off)
device.add_line("ni_notein", 1, "env_adsr", 0)
# Envelope dials
device.add_line("atk_dial", 0, "env_adsr", 1)
device.add_line("dec_dial", 0, "env_adsr", 2)
device.add_line("sus_dial", 0, "env_adsr", 3)
device.add_line("rel_dial", 0, "env_adsr", 4)

# Oscillator × envelope
device.add_line("osc", 0, "osc_env", 0)
device.add_line("env_adsr", 0, "osc_env", 1)

# Filter routing
device.add_line("osc_env", 0, "svf_l", 0)

# Mod wheel → extra cutoff
device.add_line("mw_ctlin", 0, "mw_display", 0)
device.add_line("mw_ctlin", 0, "mw_scale", 0)
device.add_line("mw_scale", 0, "mw_store", 1)
device.add_line("cutoff_dial", 0, "cutoff_add", 0)
device.add_line("mw_store", 0, "cutoff_add", 1)
device.add_line("cutoff_add", 0, "cutoff_pk", 0)
device.add_line("cutoff_pk", 0, "cutoff_ln", 0)
device.add_line("cutoff_ln", 0, "svf_l", 1)

# Aftertouch → resonance
device.add_line("at_touchin", 0, "at_display", 0)
device.add_line("at_touchin", 0, "at_scale", 0)
device.add_line("at_scale", 0, "at_pk", 0)
device.add_line("at_pk", 0, "at_ln", 0)
device.add_line("at_ln", 0, "svf_l", 2)

# Filter LP output → gain → plugout~
device.add_line("svf_l", 0, "out_gain", 0)
device.add_line("out_gain", 0, "plugout", 0)
device.add_line("out_gain", 0, "plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Expressive Synth", device_type="instrument")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
