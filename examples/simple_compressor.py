"""Simple compressor — m4l_builder example.

A peak-following stereo compressor with threshold, ratio, attack/release,
makeup gain, and dry/wet mix.

Layout (width=410, height=220):
  +--------------------------------------------------+
  | +--------------------------------------------+   |
  | |   GR SCOPE (live.scope~)                   |   |
  | |   Shows gain reduction envelope            | [GR] [L][R]
  | +--------------------------------------------+   |
  | [Thresh] [Ratio] [Atk] [Rel] [Makeup] [Mix]      |
  +--------------------------------------------------+

DSP signal flow (proper dB-domain compression):
  plugin~ L/R
    -> abs~ L + abs~ R -> +~ -> *~ 0.5 (mono peak average)
    -> slide~ (attack/release envelope follower)
    -> atodb~ (linear to dB)
    -> -~ threshold_dB (overdB = level - threshold)
    -> *~ ratio_coeff (gain_reduction_dB = overdB * (1 - 1/ratio))
    -> clip~ -200. 0. (only reduce, never boost at this stage)
    -> dbtoa~ (back to linear gain factor)
    -> *~ L/R (apply gain)
    -> *~ makeup_gain -> dry/wet -> plugout~

Parameter smoothing:
  All float-to-signal paths use pack f 20 -> line~
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path

device = AudioEffect("Simple Compressor", width=410, height=220, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, 410, 220])

# GR scope — full-width hero display, shows compression gain envelope
device.add_scope("gr_scope", [8, 8, 310, 105],
                 bgcolor=[0.05, 0.05, 0.06, 1.0],
                 activelinecolor=[0.85, 0.35, 0.25, 1.0],
                 gridcolor=[0.15, 0.15, 0.17, 0.4],
                 range_vals=[0.0, 1.2],
                 calccount=128, smooth=2, line_width=1.5)

# GR meter label
device.add_comment("gr_meter_label", [324, 6, 20, 16], "GR",
                   textcolor=[0.85, 0.35, 0.25, 0.8], fontsize=8.5)

# Gain reduction meter
device.add_meter("gr_meter", [326, 24, 14, 89],
                 coldcolor=[0.85, 0.35, 0.25, 1.0],
                 warmcolor=[0.85, 0.55, 0.2, 1.0],
                 hotcolor=[0.9, 0.7, 0.15, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# Output meter labels
device.add_comment("out_label", [372, 6, 30, 16], "OUT",
                   textcolor=[0.5, 0.5, 0.5, 0.8], fontsize=8.5)

# Stereo output meters
device.add_meter("meter_l", [370, 24, 14, 89],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.60, 0.20, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [387, 24, 14, 89],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.60, 0.20, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Dials row — more vertical space now that waveform display is gone
device.add_dial("thresh_dial", "Threshold", [4, 120, 58, 92],
                min_val=-60.0, max_val=0.0, initial=-20.0,
                unitstyle=4, appearance=1,
                annotation_name="Compression Threshold")

device.add_dial("ratio_dial", "Ratio", [66, 120, 58, 92],
                min_val=1.0, max_val=20.0, initial=4.0,
                unitstyle=1, appearance=1,
                annotation_name="Compression Ratio")

device.add_dial("attack_dial", "Attack", [128, 120, 58, 92],
                min_val=0.1, max_val=100.0, initial=10.0,
                unitstyle=2, appearance=1,
                annotation_name="Envelope Attack")

device.add_dial("release_dial", "Release", [190, 120, 58, 92],
                min_val=10.0, max_val=1000.0, initial=100.0,
                unitstyle=2, appearance=1,
                annotation_name="Envelope Release")

device.add_dial("makeup_dial", "Makeup", [252, 120, 58, 92],
                min_val=0.0, max_val=24.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Makeup Gain")

device.add_dial("mix_dial", "Mix", [314, 120, 58, 92],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet Mix")

# =========================================================================
# DSP objects
# =========================================================================

# --- Envelope follower ---
device.add_newobj("abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 250, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 250, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 275, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 300, 45, 20])

# Attack/release in samples (ms * 44.1)
device.add_newobj("attack_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 175, 60, 20])
device.add_newobj("release_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 175, 60, 20])

# Smoothing for slide~ inlets
device.add_newobj("attack_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 195, 60, 20])
device.add_newobj("attack_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 220, 40, 20])
device.add_newobj("release_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 195, 60, 20])
device.add_newobj("release_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[150, 220, 40, 20])

# Envelope follower with adjustable attack/release
device.add_newobj("envelope", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 325, 45, 20])

# --- dB-domain gain computation ---
# Convert linear envelope to dB
device.add_newobj("env_db", "atodb~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 355, 50, 20])

# Threshold: dial dB value -> smoothed signal for subtraction
device.add_newobj("thresh_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 120, 60, 20])
device.add_newobj("thresh_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 145, 40, 20])

# overdB = level_dB - threshold_dB (positive when louder than threshold)
device.add_newobj("over_db", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 380, 30, 20])

# ratio_coeff = 1 - 1/ratio (the compression slope)
device.add_newobj("ratio_coeff", "expr 1. - 1. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 100, 110, 20])
device.add_newobj("ratio_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 120, 60, 20])
device.add_newobj("ratio_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[150, 145, 40, 20])

# gain_reduction_dB = overdB * ratio_coeff (positive = amount to cut)
device.add_newobj("gr_db", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 405, 30, 20])

# Negate: we need to subtract this from signal, so negate to get negative dB gain
device.add_newobj("gr_neg", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 430, 50, 20])

# Clip: only apply reduction (negative dB), never boost here
device.add_newobj("gr_clip", "clip~ -200. 0.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 455, 75, 20])

# Convert gain reduction dB back to linear
device.add_newobj("gr_linear", "dbtoa~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 480, 55, 20])

# --- Apply gain to audio ---
device.add_newobj("comp_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 510, 30, 20])
device.add_newobj("comp_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 510, 30, 20])

# --- Makeup gain ---
device.add_newobj("makeup_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 540, 50, 20])
device.add_newobj("makeup_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 560, 60, 20])
device.add_newobj("makeup_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 585, 40, 20])
device.add_newobj("makeup_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 610, 40, 20])
device.add_newobj("makeup_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 610, 40, 20])

# --- Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 90, 55, 20])
device.add_newobj("mix_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 120, 45, 20])

device.add_newobj("wet_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 450, 60, 20])
device.add_newobj("wet_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 475, 40, 20])
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[340, 450, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[340, 475, 40, 20])
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 450, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[460, 475, 40, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 510, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 510, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 510, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 510, 30, 20])
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 550, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 550, 30, 20])

# GR display: invert gr_linear so meter shows reduction amount
device.add_newobj("gr_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 480, 50, 20])

# =========================================================================
# Connections
# =========================================================================

# Threshold smoothing: dial -> pack -> line~ -> over_db inlet 1 (signal)
device.add_line("thresh_dial", 0, "thresh_pk", 0)
device.add_line("thresh_pk", 0, "thresh_ln", 0)
device.add_line("thresh_ln", 0, "over_db", 1)

# Ratio coefficient + smoothing
device.add_line("ratio_dial", 0, "ratio_coeff", 0)
device.add_line("ratio_coeff", 0, "ratio_pk", 0)
device.add_line("ratio_pk", 0, "ratio_ln", 0)
device.add_line("ratio_ln", 0, "gr_db", 1)

# Attack/Release smoothing -> slide~ inlets
device.add_line("attack_dial", 0, "attack_samp", 0)
device.add_line("attack_samp", 0, "attack_pk", 0)
device.add_line("attack_pk", 0, "attack_ln", 0)
device.add_line("attack_ln", 0, "envelope", 1)

device.add_line("release_dial", 0, "release_samp", 0)
device.add_line("release_samp", 0, "release_pk", 0)
device.add_line("release_pk", 0, "release_ln", 0)
device.add_line("release_ln", 0, "envelope", 2)

# Envelope follower
device.add_line("obj-plugin", 0, "abs_l", 0)
device.add_line("obj-plugin", 1, "abs_r", 0)
device.add_line("abs_l", 0, "env_sum", 0)
device.add_line("abs_r", 0, "env_sum", 1)
device.add_line("env_sum", 0, "env_avg", 0)
device.add_line("env_avg", 0, "envelope", 0)

# dB-domain gain chain
device.add_line("envelope", 0, "env_db", 0)         # linear -> dB
device.add_line("env_db", 0, "over_db", 0)          # level_dB -> subtract threshold
device.add_line("over_db", 0, "gr_db", 0)           # overdB * ratio_coeff
device.add_line("gr_db", 0, "gr_neg", 0)            # negate -> negative dB reduction
device.add_line("gr_neg", 0, "gr_clip", 0)          # clip to (-inf, 0]
device.add_line("gr_clip", 0, "gr_linear", 0)       # dB -> linear gain factor

# Apply gain to audio
device.add_line("obj-plugin", 0, "comp_l", 0)
device.add_line("obj-plugin", 1, "comp_r", 0)
device.add_line("gr_linear", 0, "comp_l", 1)
device.add_line("gr_linear", 0, "comp_r", 1)

# Makeup gain
device.add_line("makeup_dial", 0, "makeup_dbtoa", 0)
device.add_line("makeup_dbtoa", 0, "makeup_pk", 0)
device.add_line("makeup_pk", 0, "makeup_ln", 0)
device.add_line("comp_l", 0, "makeup_l", 0)
device.add_line("comp_r", 0, "makeup_r", 0)
device.add_line("makeup_ln", 0, "makeup_l", 1)
device.add_line("makeup_ln", 0, "makeup_r", 1)

# Dry/wet mix
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
device.add_line("mix_trig", 0, "wet_l_pk", 0)
device.add_line("wet_l_pk", 0, "wet_l_ln", 0)
device.add_line("wet_l_ln", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r_pk", 0)
device.add_line("wet_r_pk", 0, "wet_r_ln", 0)
device.add_line("wet_r_ln", 0, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_pk", 0)
device.add_line("dry_pk", 0, "dry_ln", 0)
device.add_line("dry_ln", 0, "dry_l", 1)
device.add_line("dry_ln", 0, "dry_r", 1)

device.add_line("makeup_l", 0, "wet_l", 0)
device.add_line("makeup_r", 0, "wet_r", 0)
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

device.add_line("wet_l", 0, "sum_l", 0)
device.add_line("dry_l", 0, "sum_l", 1)
device.add_line("wet_r", 0, "sum_r", 0)
device.add_line("dry_r", 0, "sum_r", 1)

device.add_line("sum_l", 0, "obj-plugout", 0)
device.add_line("sum_r", 0, "obj-plugout", 1)

# GR scope: show gr_linear (0=full reduction, 1=unity)
device.add_line("gr_linear", 0, "gr_scope", 0)

# GR meter: invert so meter shows amount of reduction
device.add_line("gr_linear", 0, "gr_inv", 0)
device.add_line("gr_inv", 0, "gr_meter", 0)

# Output meters
device.add_line("sum_l", 0, "meter_l", 0)
device.add_line("sum_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Simple Compressor")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
