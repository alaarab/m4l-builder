"""Parallel Compressor -- NY-style fattener.

Blends dry signal with a heavily compressed copy for thickness and punch.
One main "Compress" knob controls both threshold and ratio together.
Two meters show dry vs compressed levels side by side.

Signal flow:
  plugin~ L/R -> dry path (straight through)
  plugin~ L/R -> heavy compression path:
    abs~ L+R avg -> slide~ -> atodb~ -> -~ threshold -> *~ ratio_coeff
    -> clip~ -> dbtoa~ -> *~ L/R
  Compressed signal + dry signal blended via Blend knob -> plugout~
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path

WIDTH = 280
HEIGHT = 150
device = AudioEffect("Parallel Compressor", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])

# Dry meter
device.add_comment("dry_label", [8, 4, 30, 12], "DRY",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_meter("dry_meter", [10, 18, 14, 80],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.60, 0.20, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Compressed meter
device.add_comment("comp_label", [30, 4, 40, 12], "COMP",
                   fontsize=8.0, textcolor=[0.85, 0.45, 0.30, 0.8])
device.add_meter("comp_meter", [34, 18, 14, 80],
                 coldcolor=[0.85, 0.45, 0.30, 1.0],
                 warmcolor=[0.90, 0.60, 0.20, 1.0],
                 hotcolor=[0.90, 0.40, 0.15, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Main compress knob -- the star control
device.add_dial("compress_dial", "Compress", [55, 6, 70, 92],
                min_val=0.0, max_val=100.0, initial=50.0,
                unitstyle=5, appearance=1,
                annotation_name="Compression amount (threshold + ratio)")

# Attack and release
device.add_dial("attack_dial", "Attack", [130, 6, 40, 60],
                min_val=0.1, max_val=50.0, initial=5.0,
                unitstyle=2, appearance=1,
                annotation_name="Attack time (ms)")

device.add_dial("release_dial", "Release", [175, 6, 40, 60],
                min_val=10.0, max_val=500.0, initial=80.0,
                unitstyle=2, appearance=1,
                annotation_name="Release time (ms)")

# Blend and output
device.add_dial("blend_dial", "Blend", [220, 6, 50, 70],
                min_val=0.0, max_val=100.0, initial=50.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/compressed blend")

device.add_dial("output_dial", "Output", [130, 80, 50, 65],
                min_val=-24.0, max_val=12.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Output level (dB)")

# Output meters
device.add_meter("out_meter_l", [WIDTH - 28, 8, 10, HEIGHT - 20],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("out_meter_r", [WIDTH - 14, 8, 10, HEIGHT - 20],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# =========================================================================
# DSP
# =========================================================================

# Compress dial -> threshold and ratio mapping
# 0% compress = threshold 0dB, ratio 1:1 (no compression)
# 100% compress = threshold -40dB, ratio 10:1 (heavy smash)
device.add_newobj("comp_to_thresh", "scale 0. 100. 0. -40.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 200, 120, 20])
device.add_newobj("comp_to_ratio", "scale 0. 100. 1. 10.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 200, 120, 20])
device.add_newobj("comp_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[30, 180, 40, 20])

# Threshold smoothing
device.add_newobj("thresh_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 230, 60, 20])
device.add_newobj("thresh_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 255, 40, 20])

# Ratio -> coeff -> smoothing
device.add_newobj("ratio_coeff", "expr 1. - 1. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 230, 110, 20])
device.add_newobj("ratio_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 255, 60, 20])
device.add_newobj("ratio_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[160, 280, 40, 20])

# Envelope follower
device.add_newobj("abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 320, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 320, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 345, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 370, 45, 20])

# Attack/release in samples
device.add_newobj("atk_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 310, 60, 20])
device.add_newobj("rel_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[270, 310, 60, 20])
device.add_newobj("atk_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 335, 60, 20])
device.add_newobj("atk_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 360, 40, 20])
device.add_newobj("rel_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[270, 335, 60, 20])
device.add_newobj("rel_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[270, 360, 40, 20])

device.add_newobj("envelope", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 395, 45, 20])

# dB gain computation
device.add_newobj("env_db", "atodb~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 420, 50, 20])
device.add_newobj("over_db", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 445, 30, 20])
device.add_newobj("gr_db", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 470, 30, 20])
device.add_newobj("gr_neg", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 495, 50, 20])
device.add_newobj("gr_clip", "clip~ -200. 0.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 520, 75, 20])
device.add_newobj("gr_linear", "dbtoa~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 545, 55, 20])

# Apply compression to signal
device.add_newobj("comp_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 575, 30, 20])
device.add_newobj("comp_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 575, 30, 20])

# Blend: dry * (1-blend) + compressed * blend
device.add_newobj("blend_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 400, 120, 20])
device.add_newobj("blend_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[300, 425, 55, 20])
device.add_newobj("blend_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 450, 45, 20])

device.add_newobj("wet_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 475, 60, 20])
device.add_newobj("wet_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 500, 40, 20])
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 475, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[360, 500, 40, 20])
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[430, 475, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[430, 500, 40, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 540, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 540, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[430, 540, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[470, 540, 30, 20])

device.add_newobj("blend_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[370, 575, 30, 20])
device.add_newobj("blend_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[410, 575, 30, 20])

# Output gain
device.add_newobj("out_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 600, 50, 20])
device.add_newobj("out_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 625, 60, 20])
device.add_newobj("out_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 650, 40, 20])
device.add_newobj("out_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[370, 660, 30, 20])
device.add_newobj("out_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[410, 660, 30, 20])

# =========================================================================
# Connections
# =========================================================================

# Compress dial -> trigger -> threshold + ratio
device.add_line("compress_dial", 0, "comp_trig", 0)
device.add_line("comp_trig", 0, "comp_to_thresh", 0)
device.add_line("comp_trig", 1, "comp_to_ratio", 0)

# Threshold smoothing
device.add_line("comp_to_thresh", 0, "thresh_pk", 0)
device.add_line("thresh_pk", 0, "thresh_ln", 0)
device.add_line("thresh_ln", 0, "over_db", 1)

# Ratio coeff smoothing
device.add_line("comp_to_ratio", 0, "ratio_coeff", 0)
device.add_line("ratio_coeff", 0, "ratio_pk", 0)
device.add_line("ratio_pk", 0, "ratio_ln", 0)
device.add_line("ratio_ln", 0, "gr_db", 1)

# Attack/release
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

# dB gain chain
device.add_line("envelope", 0, "env_db", 0)
device.add_line("env_db", 0, "over_db", 0)
device.add_line("over_db", 0, "gr_db", 0)
device.add_line("gr_db", 0, "gr_neg", 0)
device.add_line("gr_neg", 0, "gr_clip", 0)
device.add_line("gr_clip", 0, "gr_linear", 0)

# Apply compression
device.add_line("obj-plugin", 0, "comp_l", 0)
device.add_line("obj-plugin", 1, "comp_r", 0)
device.add_line("gr_linear", 0, "comp_l", 1)
device.add_line("gr_linear", 0, "comp_r", 1)

# Blend: compressed * blend + dry * (1-blend)
device.add_line("blend_dial", 0, "blend_scale", 0)
device.add_line("blend_scale", 0, "blend_trig", 0)
device.add_line("blend_trig", 0, "wet_l_pk", 0)
device.add_line("wet_l_pk", 0, "wet_l_ln", 0)
device.add_line("wet_l_ln", 0, "wet_l", 1)
device.add_line("blend_trig", 1, "wet_r_pk", 0)
device.add_line("wet_r_pk", 0, "wet_r_ln", 0)
device.add_line("wet_r_ln", 0, "wet_r", 1)
device.add_line("blend_trig", 2, "blend_inv", 0)
device.add_line("blend_inv", 0, "dry_pk", 0)
device.add_line("dry_pk", 0, "dry_ln", 0)
device.add_line("dry_ln", 0, "dry_l", 1)
device.add_line("dry_ln", 0, "dry_r", 1)

device.add_line("comp_l", 0, "wet_l", 0)
device.add_line("comp_r", 0, "wet_r", 0)
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

device.add_line("wet_l", 0, "blend_l", 0)
device.add_line("dry_l", 0, "blend_l", 1)
device.add_line("wet_r", 0, "blend_r", 0)
device.add_line("dry_r", 0, "blend_r", 1)

# Output gain
device.add_line("output_dial", 0, "out_dbtoa", 0)
device.add_line("out_dbtoa", 0, "out_pk", 0)
device.add_line("out_pk", 0, "out_ln", 0)
device.add_line("blend_l", 0, "out_l", 0)
device.add_line("blend_r", 0, "out_r", 0)
device.add_line("out_ln", 0, "out_l", 1)
device.add_line("out_ln", 0, "out_r", 1)

device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# Meters
device.add_line("obj-plugin", 0, "dry_meter", 0)
device.add_line("comp_l", 0, "comp_meter", 0)
device.add_line("out_l", 0, "out_meter_l", 0)
device.add_line("out_r", 0, "out_meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Parallel Compressor", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
