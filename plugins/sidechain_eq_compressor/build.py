"""Sidechain EQ Compressor — detector shaping for cleaner, more intentional compression.

Detector modes:
  - FULL: broadband detector
  - HP: detector ignores more low end before gain reduction
  - BAND: detector focuses around the chosen sidechain frequency
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path


device = AudioEffect("Sidechain EQ Compressor", width=470, height=220, theme=MIDNIGHT)

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 470, 220])

device.add_scope("gr_scope", [8, 8, 310, 104],
                 bgcolor=[0.05, 0.05, 0.06, 1.0],
                 activelinecolor=[0.88, 0.42, 0.28, 1.0],
                 gridcolor=[0.16, 0.16, 0.18, 0.4],
                 range_vals=[0.0, 1.2],
                 calccount=128, smooth=2, line_width=1.5)

device.add_comment("title", [12, 12, 120, 12], "SC EQ COMP",
                   fontname="Ableton Sans Bold", fontsize=10.0,
                   textcolor=[0.88, 0.88, 0.90, 1.0])
device.add_comment("subtitle", [12, 24, 220, 11],
                   "Detector EQ changes what triggers the compression.",
                   fontsize=7.5, textcolor=MIDNIGHT.text_dim)

device.add_comment("gr_label", [326, 6, 24, 14], "GR",
                   textcolor=[0.88, 0.42, 0.28, 0.8], fontsize=8.5)
device.add_meter("gr_meter", [328, 24, 14, 88],
                 coldcolor=[0.88, 0.42, 0.28, 1.0],
                 warmcolor=[0.90, 0.60, 0.24, 1.0],
                 hotcolor=[0.92, 0.76, 0.18, 1.0],
                 overloadcolor=[0.90, 0.16, 0.16, 1.0])

device.add_comment("out_label", [374, 6, 34, 14], "OUT",
                   textcolor=MIDNIGHT.text_dim, fontsize=8.5)
device.add_meter("meter_l", [372, 24, 14, 88],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.62, 0.22, 1.0],
                 overloadcolor=[0.90, 0.16, 0.16, 1.0])
device.add_meter("meter_r", [389, 24, 14, 88],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.62, 0.22, 1.0],
                 overloadcolor=[0.90, 0.16, 0.16, 1.0])

device.add_comment("mode_label", [327, 116, 50, 10], "SC MODE",
                   textcolor=[0.88, 0.62, 0.28, 0.8], fontsize=8.0)
device.add_tab("sc_mode", "SC Mode", [326, 126, 78, 18],
               options=["FULL", "HP", "BAND"],
               bgcolor=[0.18, 0.18, 0.20, 1.0],
               bgoncolor=[0.62, 0.38, 0.20, 1.0],
               textcolor=[0.72, 0.72, 0.74, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0],
               rounded=3.0, spacing_x=1.0)

device.add_dial("thresh_dial", "Threshold", [4, 120, 56, 92],
                min_val=-60.0, max_val=0.0, initial=-18.0,
                unitstyle=4, appearance=1,
                annotation_name="Compression threshold")
device.add_dial("ratio_dial", "Ratio", [64, 120, 56, 92],
                min_val=1.0, max_val=20.0, initial=4.0,
                unitstyle=1, appearance=1,
                annotation_name="Compression ratio")
device.add_dial("attack_dial", "Attack", [124, 120, 56, 92],
                min_val=0.1, max_val=100.0, initial=8.0,
                unitstyle=2, appearance=1,
                annotation_name="Attack time")
device.add_dial("release_dial", "Release", [184, 120, 56, 92],
                min_val=10.0, max_val=1200.0, initial=140.0,
                unitstyle=2, appearance=1,
                annotation_name="Release time")
device.add_dial("sc_freq_dial", "SC Freq", [244, 120, 56, 92],
                min_val=40.0, max_val=12000.0, initial=160.0,
                unitstyle=3, appearance=1, parameter_exponent=2.2,
                annotation_name="Detector filter frequency")
device.add_dial("makeup_dial", "Makeup", [326, 150, 38, 62],
                min_val=0.0, max_val=24.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Makeup gain")
device.add_dial("mix_dial", "Mix", [366, 150, 38, 62],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry wet mix")

# ---------------------------------------------------------------------------
# Detector path
# ---------------------------------------------------------------------------
device.add_newobj("det_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 250, 30, 20])
device.add_newobj("det_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 278, 45, 20])

device.add_newobj("sc_filter", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[30, 310, 40, 20])
device.add_newobj("sc_q_init", "loadmess 0.25", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[78, 310, 72, 20])

device.add_newobj("sc_freq_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 250, 60, 20])
device.add_newobj("sc_freq_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[160, 278, 40, 20])

device.add_newobj("mode_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[230, 250, 40, 20])
device.add_newobj("det_sel", "selector~ 3 1", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 278, 78, 20])

device.add_newobj("det_abs", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 310, 35, 20])
device.add_newobj("attack_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[310, 250, 60, 20])
device.add_newobj("release_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[380, 250, 60, 20])
device.add_newobj("attack_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[310, 278, 60, 20])
device.add_newobj("attack_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[310, 306, 40, 20])
device.add_newobj("release_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[380, 278, 60, 20])
device.add_newobj("release_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[380, 306, 40, 20])
device.add_newobj("envelope", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 342, 45, 20])

# ---------------------------------------------------------------------------
# Gain computer
# ---------------------------------------------------------------------------
device.add_newobj("env_db", "atodb~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 374, 50, 20])
device.add_newobj("thresh_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 374, 60, 20])
device.add_newobj("thresh_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 402, 40, 20])
device.add_newobj("over_db", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 406, 30, 20])
device.add_newobj("ratio_coeff", "expr 1. - 1. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 374, 110, 20])
device.add_newobj("ratio_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 402, 60, 20])
device.add_newobj("ratio_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[100, 430, 40, 20])
device.add_newobj("gr_db", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 438, 30, 20])
device.add_newobj("gr_neg", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 470, 50, 20])
device.add_newobj("gr_clip", "clip~ -200. 0.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 502, 75, 20])
device.add_newobj("gr_linear", "dbtoa~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[230, 534, 55, 20])
device.add_newobj("gr_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[294, 534, 50, 20])

# ---------------------------------------------------------------------------
# Audio path
# ---------------------------------------------------------------------------
device.add_newobj("comp_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 566, 30, 20])
device.add_newobj("comp_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[70, 566, 30, 20])

device.add_newobj("makeup_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[120, 566, 50, 20])
device.add_newobj("makeup_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[120, 594, 60, 20])
device.add_newobj("makeup_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[120, 622, 40, 20])
device.add_newobj("makeup_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 622, 40, 20])
device.add_newobj("makeup_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[70, 622, 40, 20])

device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 566, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[360, 594, 55, 20])
device.add_newobj("mix_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 622, 45, 20])

device.add_newobj("wet_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[220, 622, 60, 20])
device.add_newobj("wet_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[220, 650, 40, 20])
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[266, 622, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[266, 650, 40, 20])
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[410, 650, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[410, 678, 40, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[220, 706, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[266, 706, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[410, 706, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[456, 706, 30, 20])
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[332, 744, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[372, 744, 30, 20])

# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
device.add_line("obj-plugin", 0, "det_sum", 0)
device.add_line("obj-plugin", 1, "det_sum", 1)
device.add_line("det_sum", 0, "det_avg", 0)
device.add_line("det_avg", 0, "sc_filter", 0)
device.add_line("sc_q_init", 0, "sc_filter", 2)

device.add_line("sc_freq_dial", 0, "sc_freq_pk", 0)
device.add_line("sc_freq_pk", 0, "sc_freq_ln", 0)
device.add_line("sc_freq_ln", 0, "sc_filter", 1)

device.add_line("sc_mode", 0, "mode_offset", 0)
device.add_line("mode_offset", 0, "det_sel", 0)
device.add_line("det_avg", 0, "det_sel", 1)
device.add_line("sc_filter", 1, "det_sel", 2)
device.add_line("sc_filter", 2, "det_sel", 3)
device.add_line("det_sel", 0, "det_abs", 0)

device.add_line("attack_dial", 0, "attack_samp", 0)
device.add_line("attack_samp", 0, "attack_pk", 0)
device.add_line("attack_pk", 0, "attack_ln", 0)
device.add_line("attack_ln", 0, "envelope", 1)
device.add_line("release_dial", 0, "release_samp", 0)
device.add_line("release_samp", 0, "release_pk", 0)
device.add_line("release_pk", 0, "release_ln", 0)
device.add_line("release_ln", 0, "envelope", 2)
device.add_line("det_abs", 0, "envelope", 0)

device.add_line("thresh_dial", 0, "thresh_pk", 0)
device.add_line("thresh_pk", 0, "thresh_ln", 0)
device.add_line("thresh_ln", 0, "over_db", 1)
device.add_line("ratio_dial", 0, "ratio_coeff", 0)
device.add_line("ratio_coeff", 0, "ratio_pk", 0)
device.add_line("ratio_pk", 0, "ratio_ln", 0)
device.add_line("ratio_ln", 0, "gr_db", 1)

device.add_line("envelope", 0, "env_db", 0)
device.add_line("env_db", 0, "over_db", 0)
device.add_line("over_db", 0, "gr_db", 0)
device.add_line("gr_db", 0, "gr_neg", 0)
device.add_line("gr_neg", 0, "gr_clip", 0)
device.add_line("gr_clip", 0, "gr_linear", 0)
device.add_line("gr_linear", 0, "gr_inv", 0)

device.add_line("obj-plugin", 0, "comp_l", 0)
device.add_line("obj-plugin", 1, "comp_r", 0)
device.add_line("gr_linear", 0, "comp_l", 1)
device.add_line("gr_linear", 0, "comp_r", 1)

device.add_line("makeup_dial", 0, "makeup_dbtoa", 0)
device.add_line("makeup_dbtoa", 0, "makeup_pk", 0)
device.add_line("makeup_pk", 0, "makeup_ln", 0)
device.add_line("comp_l", 0, "makeup_l", 0)
device.add_line("comp_r", 0, "makeup_r", 0)
device.add_line("makeup_ln", 0, "makeup_l", 1)
device.add_line("makeup_ln", 0, "makeup_r", 1)

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
device.add_line("sum_l", 0, "meter_l", 0)
device.add_line("sum_r", 0, "meter_r", 0)
device.add_line("gr_linear", 0, "gr_scope", 0)
device.add_line("gr_inv", 0, "gr_meter", 0)


output = device_output_path("Sidechain EQ Compressor")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
