"""Ducking Delay — a clean stereo delay that clears space while the source plays."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path


device = AudioEffect("Ducking Delay", width=430, height=170, theme=MIDNIGHT)

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 430, 170], bgcolor=[0.11, 0.11, 0.13, 1.0])

device.add_comment("title", [8, 6, 88, 12], "DUCK DELAY",
                   fontname="Ableton Sans Bold", fontsize=10.0,
                   textcolor=[0.88, 0.88, 0.90, 1.0])
device.add_comment("subtitle", [8, 18, 220, 11],
                   "Input level ducks the wet repeats, then they bloom back.",
                   fontsize=7.5, textcolor=MIDNIGHT.text_dim)

device.add_comment("lbl_time", [8, 38, 40, 10], "TIME",
                   fontsize=8.5, textcolor=MIDNIGHT.accent)
device.add_comment("lbl_shape", [140, 38, 64, 10], "CHARACTER",
                   fontsize=8.5, textcolor=MIDNIGHT.accent)
device.add_comment("lbl_duck", [272, 38, 44, 10], "DUCK",
                   fontsize=8.5, textcolor=[0.90, 0.62, 0.28, 1.0])

device.add_dial("time_dial", "Time", [8, 48, 58, 78],
                min_val=1.0, max_val=2000.0, initial=420.0,
                unitstyle=2, appearance=1,
                annotation_name="Delay time in milliseconds")
device.add_dial("feedback_dial", "Feedback", [72, 48, 58, 78],
                min_val=0.0, max_val=95.0, initial=35.0,
                unitstyle=5, appearance=1,
                annotation_name="Feedback amount")
device.add_dial("tone_dial", "Tone", [140, 48, 58, 78],
                min_val=500.0, max_val=18000.0, initial=7000.0,
                unitstyle=3, appearance=1,
                annotation_name="Feedback damping tone")
device.add_dial("mix_dial", "Mix", [204, 48, 58, 78],
                min_val=0.0, max_val=100.0, initial=28.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry wet mix")
device.add_dial("duck_dial", "Duck", [272, 48, 58, 78],
                min_val=0.0, max_val=100.0, initial=55.0,
                unitstyle=5, appearance=1,
                annotation_name="How hard the input ducks the repeats")
device.add_dial("recover_dial", "Recover", [336, 48, 58, 78],
                min_val=20.0, max_val=1500.0, initial=240.0,
                unitstyle=2, appearance=1,
                annotation_name="How quickly repeats recover after a hit")

device.add_meter("meter_l", [404, 8, 10, 154],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.90, 0.80, 0.22, 1.0],
                 hotcolor=[0.90, 0.42, 0.12, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [418, 8, 10, 154],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.90, 0.80, 0.22, 1.0],
                 hotcolor=[0.90, 0.42, 0.12, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# ---------------------------------------------------------------------------
# Delay core
# ---------------------------------------------------------------------------
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 220, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 220, 30, 20])

device.add_newobj("tapin_l", "tapin~ 2000", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[30, 250, 80, 20])
device.add_newobj("tapin_r", "tapin~ 2000", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[180, 250, 80, 20])
device.add_newobj("tapout_l", "tapout~ 420", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 280, 80, 20])
device.add_newobj("tapout_r", "tapout~ 420", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 280, 80, 20])

device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 312, 50, 20])
device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 312, 50, 20])
device.add_newobj("fb_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 344, 40, 20])
device.add_newobj("fb_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 344, 40, 20])

# ---------------------------------------------------------------------------
# Detector and ducking gain
# ---------------------------------------------------------------------------
device.add_newobj("det_abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 220, 35, 20])
device.add_newobj("det_abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[344, 220, 35, 20])
device.add_newobj("det_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[322, 250, 30, 20])
device.add_newobj("det_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[322, 280, 45, 20])
device.add_newobj("duck_env", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[322, 344, 45, 20])
device.add_newobj("duck_attack_init", "loadmess 88.2", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 312, 80, 20])

device.add_newobj("recover_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[390, 312, 60, 20])
device.add_newobj("recover_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[390, 340, 60, 20])
device.add_newobj("recover_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[390, 368, 40, 20])

device.add_newobj("duck_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 394, 120, 20])
device.add_newobj("duck_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 422, 60, 20])
device.add_newobj("duck_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 450, 40, 20])
device.add_newobj("duck_depth_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 482, 30, 20])
device.add_newobj("duck_gain_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[336, 482, 50, 20])
device.add_newobj("duck_gain", "clip~ 0. 1.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[392, 482, 75, 20])

device.add_newobj("wet_duck_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 394, 30, 20])
device.add_newobj("wet_duck_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 394, 30, 20])

# ---------------------------------------------------------------------------
# Mix and smoothing
# ---------------------------------------------------------------------------
device.add_newobj("time_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 430, 60, 20])
device.add_newobj("time_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 458, 40, 20])
device.add_newobj("fb_scale", "scale 0. 95. 0. 0.95", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 430, 120, 20])
device.add_newobj("fb_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 458, 60, 20])
device.add_newobj("fb_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[100, 486, 40, 20])
device.add_newobj("tone_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[180, 430, 60, 20])
device.add_newobj("tone_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[180, 458, 40, 20])

device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 518, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[30, 546, 55, 20])
device.add_newobj("mix_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 574, 45, 20])

device.add_newobj("wet_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[120, 546, 60, 20])
device.add_newobj("wet_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[120, 574, 40, 20])
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[166, 546, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[166, 574, 40, 20])
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[240, 546, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[240, 574, 40, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[120, 612, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[166, 612, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 612, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[286, 612, 30, 20])
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 648, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[220, 648, 30, 20])

# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
device.add_line("obj-plugin", 0, "sum_l", 0)
device.add_line("obj-plugin", 1, "sum_r", 0)
device.add_line("fb_l", 0, "sum_l", 1)
device.add_line("fb_r", 0, "sum_r", 1)

device.add_line("sum_l", 0, "tapin_l", 0)
device.add_line("sum_r", 0, "tapin_r", 0)
device.add_line("tapin_l", 0, "tapout_l", 0)
device.add_line("tapin_r", 0, "tapout_r", 0)

device.add_line("tapout_l", 0, "tone_l", 0)
device.add_line("tapout_r", 0, "tone_r", 0)
device.add_line("tone_l", 0, "fb_l", 0)
device.add_line("tone_r", 0, "fb_r", 0)

device.add_line("obj-plugin", 0, "det_abs_l", 0)
device.add_line("obj-plugin", 1, "det_abs_r", 0)
device.add_line("det_abs_l", 0, "det_sum", 0)
device.add_line("det_abs_r", 0, "det_sum", 1)
device.add_line("det_sum", 0, "det_avg", 0)
device.add_line("duck_attack_init", 0, "duck_env", 1)
device.add_line("det_avg", 0, "duck_env", 0)

device.add_line("recover_dial", 0, "recover_samp", 0)
device.add_line("recover_samp", 0, "recover_pk", 0)
device.add_line("recover_pk", 0, "recover_ln", 0)
device.add_line("recover_ln", 0, "duck_env", 2)

device.add_line("duck_dial", 0, "duck_scale", 0)
device.add_line("duck_scale", 0, "duck_pk", 0)
device.add_line("duck_pk", 0, "duck_ln", 0)
device.add_line("duck_env", 0, "duck_depth_mul", 0)
device.add_line("duck_ln", 0, "duck_depth_mul", 1)
device.add_line("duck_depth_mul", 0, "duck_gain_inv", 0)
device.add_line("duck_gain_inv", 0, "duck_gain", 0)

device.add_line("tapout_l", 0, "wet_duck_l", 0)
device.add_line("tapout_r", 0, "wet_duck_r", 0)
device.add_line("duck_gain", 0, "wet_duck_l", 1)
device.add_line("duck_gain", 0, "wet_duck_r", 1)

device.add_line("time_dial", 0, "time_pk", 0)
device.add_line("time_pk", 0, "time_ln", 0)
device.add_line("time_ln", 0, "tapout_l", 1)
device.add_line("time_ln", 0, "tapout_r", 1)

device.add_line("feedback_dial", 0, "fb_scale", 0)
device.add_line("fb_scale", 0, "fb_pk", 0)
device.add_line("fb_pk", 0, "fb_ln", 0)
device.add_line("fb_ln", 0, "fb_l", 1)
device.add_line("fb_ln", 0, "fb_r", 1)

device.add_line("tone_dial", 0, "tone_pk", 0)
device.add_line("tone_pk", 0, "tone_ln", 0)
device.add_line("tone_ln", 0, "tone_l", 1)
device.add_line("tone_ln", 0, "tone_r", 1)

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

device.add_line("wet_duck_l", 0, "wet_l", 0)
device.add_line("wet_duck_r", 0, "wet_r", 0)
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)


output = device_output_path("Ducking Delay")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
