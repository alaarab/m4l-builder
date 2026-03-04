"""Glue Compressor -- SSL-style bus/mix glue compression.

VCA-style compressor designed for the mix bus. Slower attack options,
smooth gain reduction, and a large horizontal GR meter as the visual
centerpiece. Stepped ratio like the SSL (2:1, 4:1, 10:1).

Signal flow (dB-domain compression):
  plugin~ L/R
    -> abs~ L + abs~ R -> +~ -> *~ 0.5 (mono peak average)
    -> slide~ (attack/release envelope)
    -> atodb~ (linear to dB)
    -> -~ threshold (overdB = level - threshold)
    -> *~ ratio_coeff (GR = overdB * (1 - 1/ratio))
    -> clip~ -200. 0. (only reduce)
    -> dbtoa~ (back to linear)
    -> *~ L/R (apply gain)
    -> *~ makeup_gain -> plugout~
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.engines.compressor_display import compressor_display_js

WIDTH = 320
HEIGHT = 160
device = AudioEffect("Glue Compressor", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])

# Compressor transfer curve -- the star visual
device.add_jsui("comp_display", [8, 6, 220, 80],
                js_code=compressor_display_js(
                    bg_color="0.05, 0.05, 0.06, 1.0",
                    curve_color="0.55, 0.75, 0.90, 1.0",
                    dot_color="0.9, 0.7, 0.15, 1.0",
                    grid_color="0.15, 0.15, 0.17, 0.4",
                ),
                numinlets=3)

# GR meter (right of display)
device.add_comment("gr_label", [234, 4, 20, 14], "GR",
                   textcolor=[0.55, 0.75, 0.90, 0.8], fontsize=8.0)

device.add_meter("gr_meter", [236, 18, 14, 68],
                 coldcolor=[0.55, 0.75, 0.90, 1.0],
                 warmcolor=[0.80, 0.65, 0.25, 1.0],
                 hotcolor=[0.90, 0.50, 0.15, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Output meters
device.add_comment("out_label", [272, 4, 30, 14], "OUT",
                   textcolor=MIDNIGHT.text_dim, fontsize=8.0)

device.add_meter("meter_l", [272, 18, 14, 68],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.60, 0.20, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [289, 18, 14, 68],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.60, 0.20, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Controls row
device.add_dial("thresh_dial", "Threshold", [4, 90, 52, 65],
                min_val=-60.0, max_val=0.0, initial=-16.0,
                unitstyle=4, appearance=1,
                annotation_name="Compression Threshold")

device.add_tab("ratio_tab", "Ratio", [60, 92, 80, 18],
               options=["2:1", "4:1", "10:1"],
               rounded=3.0, spacing_x=1.0)

device.add_dial("attack_dial", "Attack", [60, 114, 36, 50],
                min_val=0.1, max_val=30.0, initial=10.0,
                unitstyle=2, appearance=1,
                annotation_name="Attack time (ms)")

device.add_dial("release_dial", "Release", [100, 114, 36, 50],
                min_val=50.0, max_val=1200.0, initial=300.0,
                unitstyle=2, appearance=1,
                annotation_name="Release time (ms)")

device.add_dial("makeup_dial", "Makeup", [148, 90, 52, 65],
                min_val=0.0, max_val=24.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Makeup Gain (dB)")

device.add_dial("mix_dial", "Mix", [208, 90, 52, 65],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet Mix")

# Auto gain toggle
device.add_toggle("auto_gain", "Auto", [268, 92, 30, 16],
                  shortname="Auto", labels=("off", "on"))
device.add_comment("auto_label", [268, 110, 40, 10], "AUTO",
                   fontsize=7.5, textcolor=MIDNIGHT.text_dim)

# =========================================================================
# DSP
# =========================================================================

# Envelope follower: abs L + abs R -> average -> slide~
device.add_newobj("abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 250, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 250, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 275, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 300, 45, 20])

# Attack/release in samples
device.add_newobj("atk_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 175, 60, 20])
device.add_newobj("rel_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 175, 60, 20])

device.add_newobj("atk_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 195, 60, 20])
device.add_newobj("atk_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 220, 40, 20])
device.add_newobj("rel_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 195, 60, 20])
device.add_newobj("rel_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[150, 220, 40, 20])

device.add_newobj("envelope", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 325, 45, 20])

# dB-domain gain computation
device.add_newobj("env_db", "atodb~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 355, 50, 20])

# Threshold smoothing
device.add_newobj("thresh_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 120, 60, 20])
device.add_newobj("thresh_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 145, 40, 20])

# overdB = level_dB - threshold_dB
device.add_newobj("over_db", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 380, 30, 20])

# Ratio: tab index -> sel -> float boxes for ratio values
device.add_newobj("ratio_sel", "sel 0 1 2", numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", ""],
                  patching_rect=[250, 120, 60, 20])
device.add_newobj("ratio_2", "f 2.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[250, 150, 30, 20])
device.add_newobj("ratio_4", "f 4.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[285, 150, 30, 20])
device.add_newobj("ratio_10", "f 10.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[320, 150, 35, 20])

# ratio_coeff = 1 - 1/ratio
device.add_newobj("ratio_coeff", "expr 1. - 1. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 180, 110, 20])
device.add_newobj("ratio_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 210, 60, 20])
device.add_newobj("ratio_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[250, 240, 40, 20])

# Store current ratio value for display
device.add_newobj("ratio_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[350, 180, 30, 20])

# GR = overdB * ratio_coeff
device.add_newobj("gr_db", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 405, 30, 20])

# Negate and clip
device.add_newobj("gr_neg", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 430, 50, 20])
device.add_newobj("gr_clip", "clip~ -200. 0.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 455, 75, 20])

# Convert back to linear gain
device.add_newobj("gr_linear", "dbtoa~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 480, 55, 20])

# Apply gain
device.add_newobj("comp_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 510, 30, 20])
device.add_newobj("comp_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 510, 30, 20])

# Makeup gain
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

# Auto gain: compensate GR by inverting the gain reduction as makeup
# gr_linear is 0-1 (1=no reduction). 1/gr_linear = makeup. atodb -> negate = auto makeup dB
device.add_newobj("auto_inv", "!/ 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 540, 40, 20])
device.add_newobj("auto_db", "atodb", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 560, 45, 20])
device.add_newobj("auto_clip", "clip 0. 24.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 580, 60, 20])
device.add_newobj("auto_gate", "gate", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 610, 40, 20])
# snapshot for auto gain computation
device.add_newobj("gr_snap_auto", "snapshot~ 50", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 510, 70, 20])

# Dry/wet mix
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 80, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 100, 55, 20])
device.add_newobj("mix_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 130, 45, 20])

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

# GR display
device.add_newobj("gr_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 480, 50, 20])
device.add_newobj("gr_snap", "snapshot~ 1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 450, 70, 20])

# =========================================================================
# Connections
# =========================================================================

# Threshold smoothing
device.add_line("thresh_dial", 0, "thresh_pk", 0)
device.add_line("thresh_pk", 0, "thresh_ln", 0)
device.add_line("thresh_ln", 0, "over_db", 1)

# Ratio tab -> sel -> float values -> coeff
device.add_line("ratio_tab", 0, "ratio_sel", 0)
device.add_line("ratio_sel", 0, "ratio_2", 0)
device.add_line("ratio_sel", 1, "ratio_4", 0)
device.add_line("ratio_sel", 2, "ratio_10", 0)
device.add_line("ratio_2", 0, "ratio_coeff", 0)
device.add_line("ratio_4", 0, "ratio_coeff", 0)
device.add_line("ratio_10", 0, "ratio_coeff", 0)
device.add_line("ratio_2", 0, "ratio_store", 1)
device.add_line("ratio_4", 0, "ratio_store", 1)
device.add_line("ratio_10", 0, "ratio_store", 1)
device.add_line("ratio_coeff", 0, "ratio_pk", 0)
device.add_line("ratio_pk", 0, "ratio_ln", 0)
device.add_line("ratio_ln", 0, "gr_db", 1)

# Attack/release smoothing
device.add_line("attack_dial", 0, "atk_samp", 0)
device.add_line("atk_samp", 0, "atk_pk", 0)
device.add_line("atk_pk", 0, "atk_ln", 0)
device.add_line("atk_ln", 0, "envelope", 1)

device.add_line("release_dial", 0, "rel_samp", 0)
device.add_line("rel_samp", 0, "rel_pk", 0)
device.add_line("rel_pk", 0, "rel_ln", 0)
device.add_line("rel_ln", 0, "envelope", 2)

# Envelope follower
device.add_line("obj-plugin", 0, "abs_l", 0)
device.add_line("obj-plugin", 1, "abs_r", 0)
device.add_line("abs_l", 0, "env_sum", 0)
device.add_line("abs_r", 0, "env_sum", 1)
device.add_line("env_sum", 0, "env_avg", 0)
device.add_line("env_avg", 0, "envelope", 0)

# dB-domain gain chain
device.add_line("envelope", 0, "env_db", 0)
device.add_line("env_db", 0, "over_db", 0)
device.add_line("over_db", 0, "gr_db", 0)
device.add_line("gr_db", 0, "gr_neg", 0)
device.add_line("gr_neg", 0, "gr_clip", 0)
device.add_line("gr_clip", 0, "gr_linear", 0)

# Apply gain
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

# Auto gain: gr_linear -> snapshot -> 1/x -> atodb -> clip -> gate -> makeup_dbtoa override
device.add_line("gr_linear", 0, "gr_snap_auto", 0)
device.add_line("gr_snap_auto", 0, "auto_inv", 0)
device.add_line("auto_inv", 0, "auto_db", 0)
device.add_line("auto_db", 0, "auto_clip", 0)
device.add_line("auto_clip", 0, "auto_gate", 1)
device.add_line("auto_gain", 0, "auto_gate", 0)
device.add_line("auto_gate", 0, "makeup_dbtoa", 0)

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

# Display connections
device.add_line("thresh_dial", 0, "comp_display", 0)
device.add_line("ratio_store", 0, "comp_display", 1)
device.add_line("gr_linear", 0, "gr_snap", 0)
device.add_line("gr_snap", 0, "comp_display", 2)

# GR meter
device.add_line("gr_linear", 0, "gr_inv", 0)
device.add_line("gr_inv", 0, "gr_meter", 0)

# Output meters
device.add_line("sum_l", 0, "meter_l", 0)
device.add_line("sum_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Glue Compressor")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
