"""Simple compressor — m4l_builder example.

A peak-following stereo compressor with threshold, ratio, attack/release,
makeup gain, dry/wet mix, gain reduction meter, and output meters.

Layout (width=410, height=220):
  +--------------------------------------------------+
  | COMPRESSOR                                       |
  | +-------------------------------+  [GR]  [L][R]  |
  | |   WAVEFORM DISPLAY (jsui)    |  meter  meters  |
  | |  Shows output signal         |                 |
  | +-------------------------------+                 |
  | +-------------------------------+                 |
  | |   GR SCOPE (live.scope~)     |                 |
  | +-------------------------------+                 |
  | [Thresh] [Ratio] [Atk] [Rel] [Makeup] [Mix]      |
  +--------------------------------------------------+

DSP signal flow:
  plugin~ L/R
    -> abs~ L + abs~ R -> +~ -> *~ 0.5 (mono peak average)
    -> slide~ (attack/release envelope follower)
    -> gain reduction: !/~ 1. (1/envelope) -> *~ threshold_lin -> clip~ 0. 1.
    -> blend toward unity via ratio
    -> *~ compressed L/R -> *~ makeup gain
    -> dry/wet crossfade -> plugout~ L/R

  Gain reduction signal -> live.meter~ (GR meter)
  Output L/R -> live.meter~ (output meters)
  Output signal -> snapshot~ -> zl.group -> waveform jsui display

Parameter smoothing:
  All float-to-signal parameter connections use pack f 20 -> line~
  to eliminate zipper noise from abrupt value changes.

CRITICAL RULES:
  - No sig~ (floats sent directly to *~ inlet 1)
  - No dcblock~ (doesn't exist in Max 8)
  - No /~ for signal division (use !/~ 1.)
  - selector~ always has initial arg
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT
from m4l_builder.engines.waveform_display import waveform_display_js, waveform_display_dsp

# --- Device setup ---
device = AudioEffect("Simple Compressor", width=410, height=220, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

# Background
device.add_panel("bg", [0, 0, 410, 220])

# Title
device.add_comment("title", [8, 5, 180, 16], "COMPRESSOR",
                   fontname="Ableton Sans Bold", fontsize=13.0)

# Hero waveform display
device.add_jsui("wave_display", [8, 24, 264, 55],
                js_code=waveform_display_js(
                    line_color="0.45, 0.75, 0.65, 1.0",
                    fill_color="0.45, 0.75, 0.65, 0.2",
                    bg_color="0.05, 0.05, 0.06, 1.0",
                ),
                numinlets=2)

# Gain reduction scope — shows compression envelope in real-time
device.add_scope("gr_scope", [8, 82, 264, 35],
                 bgcolor=[0.05, 0.05, 0.06, 1.0],
                 activelinecolor=[0.85, 0.35, 0.25, 1.0],
                 gridcolor=[0.15, 0.15, 0.17, 0.4],
                 range_vals=[0.0, 1.2],
                 calccount=128, smooth=2, line_width=1.5)

device.add_comment("gr_label", [275, 82, 40, 12], "GR",
                   textcolor=[0.85, 0.35, 0.25, 0.8], fontsize=8.5)

# Gain reduction meter — shows GR amount prominently
device.add_meter("gr_meter", [285, 24, 14, 93],
                 coldcolor=[0.85, 0.35, 0.25, 1.0],
                 warmcolor=[0.85, 0.55, 0.2, 1.0],
                 hotcolor=[0.9, 0.7, 0.15, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

device.add_comment("gr_meter_label", [282, 5, 20, 16], "GR",
                   textcolor=[0.85, 0.35, 0.25, 0.8], fontsize=8.5)

# Stereo output meters (right edge)
device.add_meter("meter_l", [370, 24, 12, 93],
                 coldcolor=[0.3, 0.7, 0.55, 1.0],
                 warmcolor=[0.65, 0.75, 0.3, 1.0],
                 hotcolor=[0.9, 0.5, 0.15, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [386, 24, 12, 93],
                 coldcolor=[0.3, 0.7, 0.55, 1.0],
                 warmcolor=[0.65, 0.75, 0.3, 1.0],
                 hotcolor=[0.9, 0.5, 0.15, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

device.add_comment("out_label", [372, 5, 30, 16], "OUT",
                   textcolor=[0.5, 0.5, 0.5, 0.8], fontsize=8.5)

# Single row of tiny dials: Thresh, Ratio, Attack, Release, Makeup, Mix
device.add_dial("thresh_dial", "Threshold", [4, 126, 58, 86],
                min_val=-60.0, max_val=0.0, initial=-20.0,
                unitstyle=4, appearance=1,
                annotation_name="Compression Threshold")

device.add_dial("ratio_dial", "Ratio", [66, 126, 58, 86],
                min_val=1.0, max_val=20.0, initial=4.0,
                unitstyle=1, appearance=1,
                annotation_name="Compression Ratio")

device.add_dial("attack_dial", "Attack", [128, 126, 58, 86],
                min_val=0.1, max_val=100.0, initial=10.0,
                unitstyle=2, appearance=1,
                annotation_name="Envelope Attack")

device.add_dial("release_dial", "Release", [190, 126, 58, 86],
                min_val=10.0, max_val=1000.0, initial=100.0,
                unitstyle=2, appearance=1,
                annotation_name="Envelope Release")

device.add_dial("makeup_dial", "Makeup", [252, 126, 58, 86],
                min_val=0.0, max_val=24.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Makeup Gain")

device.add_dial("mix_dial", "Mix", [314, 126, 58, 86],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet Mix")

# =========================================================================
# DSP objects
# =========================================================================

# --- Threshold: dB -> linear ---
device.add_newobj("thresh_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 100, 50, 20])

# Threshold smoothing: pack f 20 -> line~
device.add_newobj("thresh_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 120, 60, 20])
device.add_newobj("thresh_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 145, 40, 20])

# --- Ratio coefficient: 1 - 1/ratio ---
device.add_newobj("ratio_coeff", "expr 1. - 1. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 100, 110, 20])

# Ratio smoothing for gain_scaled: pack f 20 -> line~
device.add_newobj("ratio_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 120, 60, 20])
device.add_newobj("ratio_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[150, 145, 40, 20])

# Ratio inverse smoothing for gain_blend: coeff_inv -> pack f 20 -> line~
device.add_newobj("coeff_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[220, 120, 50, 20])
device.add_newobj("ratio_inv_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[220, 145, 60, 20])
device.add_newobj("ratio_inv_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[220, 170, 40, 20])

# --- Attack/Release: ms -> samples ---
device.add_newobj("attack_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 175, 60, 20])
device.add_newobj("release_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 175, 60, 20])

# Attack/release smoothing for slide~ inlets
device.add_newobj("attack_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 195, 60, 20])
device.add_newobj("attack_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 220, 40, 20])
device.add_newobj("release_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 195, 60, 20])
device.add_newobj("release_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[150, 220, 40, 20])

# --- Envelope follower ---
device.add_newobj("abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 250, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 250, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 275, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 300, 45, 20])
device.add_newobj("envelope", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 325, 45, 20])

# --- Gain computation ---
device.add_newobj("env_recip", "!/~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 355, 50, 20])
device.add_newobj("gain_raw", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 380, 40, 20])
device.add_newobj("gain_clip", "clip~ 0. 1.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 405, 65, 20])

# Ratio blend: gain_clip * ratio_coeff + (1 - ratio_coeff)
device.add_newobj("coeff_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[150, 125, 45, 20])
device.add_newobj("gain_scaled", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 430, 30, 20])
device.add_newobj("gain_blend", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 455, 30, 20])

# --- Apply gain ---
device.add_newobj("comp_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 485, 30, 20])
device.add_newobj("comp_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 485, 30, 20])

# --- Makeup gain ---
device.add_newobj("makeup_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 515, 50, 20])

# Makeup smoothing: pack f 20 -> line~
device.add_newobj("makeup_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 535, 60, 20])
device.add_newobj("makeup_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 560, 40, 20])

device.add_newobj("makeup_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 585, 40, 20])
device.add_newobj("makeup_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 585, 40, 20])

# --- Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 90, 55, 20])
device.add_newobj("mix_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 120, 45, 20])

# Mix wet L smoothing
device.add_newobj("wet_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 450, 60, 20])
device.add_newobj("wet_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 475, 40, 20])
# Mix wet R smoothing
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[340, 450, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[340, 475, 40, 20])
# Mix dry smoothing
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

# --- GR meter signal: gain_blend is 0-1 (unity=1, compressed<1) ---
# Invert so meter shows amount of reduction: 1 - gain_blend
device.add_newobj("gr_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 480, 50, 20])

# =========================================================================
# Connections
# =========================================================================

# Threshold (smoothed)
device.add_line("thresh_dial", 0, "thresh_dbtoa", 0)
device.add_line("thresh_dbtoa", 0, "thresh_pk", 0)
device.add_line("thresh_pk", 0, "thresh_ln", 0)
device.add_line("thresh_ln", 0, "gain_raw", 1)

# Ratio (smoothed, with fan to gain_scaled and coeff_inv)
device.add_line("ratio_dial", 0, "ratio_coeff", 0)
device.add_line("ratio_coeff", 0, "coeff_fan", 0)
# Fan outlet 0 -> ratio smoothing for gain_scaled
device.add_line("coeff_fan", 0, "ratio_pk", 0)
device.add_line("ratio_pk", 0, "ratio_ln", 0)
device.add_line("ratio_ln", 0, "gain_scaled", 1)
# Fan outlet 1 -> coeff_inv -> ratio inverse smoothing for gain_blend
device.add_line("coeff_fan", 1, "coeff_inv", 0)
device.add_line("coeff_inv", 0, "ratio_inv_pk", 0)
device.add_line("ratio_inv_pk", 0, "ratio_inv_ln", 0)
device.add_line("ratio_inv_ln", 0, "gain_blend", 1)

# Attack/Release (smoothed)
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

# Gain chain
device.add_line("envelope", 0, "env_recip", 0)
device.add_line("env_recip", 0, "gain_raw", 0)
device.add_line("gain_raw", 0, "gain_clip", 0)
device.add_line("gain_clip", 0, "gain_scaled", 0)
device.add_line("gain_scaled", 0, "gain_blend", 0)

# Apply gain
device.add_line("obj-plugin", 0, "comp_l", 0)
device.add_line("obj-plugin", 1, "comp_r", 0)
device.add_line("gain_blend", 0, "comp_l", 1)
device.add_line("gain_blend", 0, "comp_r", 1)

# Makeup (smoothed)
device.add_line("makeup_dial", 0, "makeup_dbtoa", 0)
device.add_line("makeup_dbtoa", 0, "makeup_pk", 0)
device.add_line("makeup_pk", 0, "makeup_ln", 0)
device.add_line("comp_l", 0, "makeup_l", 0)
device.add_line("comp_r", 0, "makeup_r", 0)
device.add_line("makeup_ln", 0, "makeup_l", 1)
device.add_line("makeup_ln", 0, "makeup_r", 1)

# Mix (smoothed)
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# Wet L smoothing
device.add_line("mix_trig", 0, "wet_l_pk", 0)
device.add_line("wet_l_pk", 0, "wet_l_ln", 0)
device.add_line("wet_l_ln", 0, "wet_l", 1)
# Wet R smoothing
device.add_line("mix_trig", 1, "wet_r_pk", 0)
device.add_line("wet_r_pk", 0, "wet_r_ln", 0)
device.add_line("wet_r_ln", 0, "wet_r", 1)
# Dry smoothing (inverted)
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

# --- GR scope: show gain envelope trace ---
device.add_line("gain_blend", 0, "gr_scope", 0)

# --- GR meter: invert gain_blend so meter shows reduction amount ---
device.add_line("gain_blend", 0, "gr_inv", 0)
device.add_line("gr_inv", 0, "gr_meter", 0)

# --- Output meters: tap final output ---
device.add_line("sum_l", 0, "meter_l", 0)
device.add_line("sum_r", 0, "meter_r", 0)

# --- Waveform display: tap output signal for visualization ---
waveform_display_dsp(device, "wave_display", "sum_l", source_outlet=0,
                     id_prefix="wave")

# =========================================================================
# Build
# =========================================================================
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Simple Compressor.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
