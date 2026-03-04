"""Poly Synth — 8-voice polyphonic instrument using poly~.

Demonstrates: poly_voices DSP block, notein, adsr_envelope (per-voice inside
poly~), lowpass_filter for tone shaping, live_gain for output.

Signal flow:
  notein → poly~ (8 voices of sine_voice) → *~ (envelope) → svf~ → live.gain~ → plugout~

Note: poly~ manages voice allocation internally. The patch referenced by
patch_name ('sine_voice') is a separate Max subpatch — this device shows
how to set up the host-side routing.
"""

from m4l_builder import Instrument, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, poly_voices, adsr_envelope, lowpass_filter

WIDTH = 360
HEIGHT = 200
device = Instrument("Poly Synth", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)


device.add_comment("lbl_env", [8, 22, 80, 12], "ENVELOPE",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("atk_dial", "Attack", [8, 32, 45, 60],
                min_val=1.0, max_val=2000.0, initial=5.0,
                unitstyle=2, parameter_exponent=3.0, appearance=1)

device.add_dial("dec_dial", "Decay", [58, 32, 45, 60],
                min_val=1.0, max_val=2000.0, initial=80.0,
                unitstyle=2, parameter_exponent=3.0, appearance=1)

device.add_dial("sus_dial", "Sustain", [108, 32, 45, 60],
                min_val=0.0, max_val=100.0, initial=60.0,
                unitstyle=5, appearance=1)

device.add_dial("rel_dial", "Release", [158, 32, 45, 60],
                min_val=1.0, max_val=4000.0, initial=150.0,
                unitstyle=2, parameter_exponent=3.0, appearance=1)

device.add_comment("lbl_filter", [8, 100, 60, 12], "FILTER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("cutoff_dial", "Cutoff", [8, 110, 50, 65],
                min_val=20.0, max_val=20000.0, initial=3000.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1)

device.add_dial("res_dial", "Res", [68, 110, 50, 65],
                min_val=0.0, max_val=100.0, initial=15.0,
                unitstyle=5, appearance=1)

device.add_comment("lbl_out", [220, 22, 60, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_live_gain("gain", "Volume", [220, 32, 120, 155],
                     min_val=-70.0, max_val=6.0, initial=0.0,
                     orientation=1, shortname="Vol")

# =========================================================================
# DSP
# =========================================================================

# MIDI note input
ni_boxes, ni_lines = notein("ni")
for b in ni_boxes:
    device.add_box(b)

pv_boxes, pv_lines = poly_voices("pv", num_voices=8, patch_name='sine_voice')
for b in pv_boxes:
    device.add_box(b)

# ADSR envelope (host side drives the poly~ with note on/off)
adsr_boxes, adsr_lines = adsr_envelope("env", attack_ms=5, decay_ms=80,
                                        sustain=0.6, release_ms=150)
for b in adsr_boxes:
    device.add_box(b)

# Lowpass filter on the poly~ audio output
lp_boxes, lp_lines = lowpass_filter("lp")
for b in lp_boxes:
    device.add_box(b)
for l in lp_lines:
    device.lines.append(l)

# Envelope × poly~ output
device.add_newobj("env_mul_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 400, 30, 20])
device.add_newobj("env_mul_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 400, 30, 20])

# Cutoff and resonance smoothing
device.add_newobj("cut_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 300, 60, 20])
device.add_newobj("cut_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 330, 40, 20])
device.add_newobj("res_scale", "scale 0. 100. 0. 0.9", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 360, 150, 20])
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 390, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 420, 40, 20])

device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[30, 500, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# MIDI note → poly~
device.add_line("ni_notein", 0, "pv_poly", 0)   # pitch
device.add_line("ni_notein", 1, "pv_poly", 1)   # velocity

# MIDI note on/off → envelope (velocity as trigger)
device.add_line("ni_notein", 1, "env_adsr", 0)
device.add_line("atk_dial", 0, "env_adsr", 1)
device.add_line("dec_dial", 0, "env_adsr", 2)
device.add_line("sus_dial", 0, "env_adsr", 3)
device.add_line("rel_dial", 0, "env_adsr", 4)

# poly~ audio output → envelope mul → lowpass filter
device.add_line("pv_poly", 0, "env_mul_l", 0)
device.add_line("pv_poly", 0, "env_mul_r", 0)
device.add_line("env_adsr", 0, "env_mul_l", 1)
device.add_line("env_adsr", 0, "env_mul_r", 1)

device.add_line("env_mul_l", 0, "lp_l", 0)
device.add_line("env_mul_r", 0, "lp_r", 0)

# Cutoff smoothing
device.add_line("cutoff_dial", 0, "cut_pk", 0)
device.add_line("cut_pk", 0, "cut_ln", 0)
device.add_line("cut_ln", 0, "lp_l", 1)
device.add_line("cut_ln", 0, "lp_r", 1)

# Resonance smoothing
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "lp_l", 2)
device.add_line("res_ln", 0, "lp_r", 2)

# Filter output → live.gain~
device.add_line("lp_out_l", 0, "gain", 0)
device.add_line("lp_out_r", 0, "gain", 1)

# live.gain~ → plugout~
device.add_line("gain", 0, "plugout", 0)
device.add_line("gain", 1, "plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Poly Synth", device_type="instrument")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
