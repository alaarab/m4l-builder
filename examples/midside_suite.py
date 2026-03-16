"""Mid/Side Processing Suite — per-channel gain, tilt EQ, and saturation.

Signal flow:
  plugin~ L/R
    -> M/S encode: (L+R)*0.5 = Mid, (L-R)*0.5 = Side
    -> Mid chain: gain (*~ dbtoa) -> tilt EQ (onepole~ crossover) -> saturation (selector~ 4 1)
    -> Side chain: same, independent controls
    -> M/S decode: Mid'+Side' = L, Mid'-Side' = R
    -> DC block: biquad~ 1. -1. 0. -0.9997 0. on each channel
    -> dry/wet mix
    -> plugout~

Tilt EQ per channel:
  signal -> onepole~ freq (LP) -> *~ lo_gain (lo_tilt scale)
  signal - LP = HP via -~ -> *~ hi_gain (hi_tilt scale)
  lo + hi via +~ = EQ output

Saturation per channel (selector~ 4 1):
  inlet 1 = tanh~ (TAPE)
  inlet 2 = overdrive~ (TUBE)
  inlet 3 = clip~ -1. 1. (CLIP)
  inlet 4 = *~ 1. bypass (OFF)
  live.tab 0-indexed + 1 -> selector~ 1-indexed

Drive per channel: *~ drive_scale before saturation
Drive dial 0-100 -> scale 0. 100. 0.0 2.0 -> pack -> line~ -> *~ inlet 1

CRITICAL RULES:
  - No sig~
  - No dcblock~ (use biquad~)
  - selector~ 4 1 (init=1)
  - live.tab +1 offset for selector~
  - panels background:1
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path

W, H = 410, 200
device = AudioEffect("MidSide Suite", width=W, height=H, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

# Background panel
device.add_panel("bg", [0, 0, W, H])

# MID section background panel — subtle teal tint
device.add_panel("panel_mid", [0, 0, 162, H],
                 bgcolor=[0.04, 0.07, 0.06, 1.0])

# SIDE section background panel — subtle blue tint
device.add_panel("panel_side", [166, 0, 162, H],
                 bgcolor=[0.04, 0.05, 0.08, 1.0])

# Section labels
device.add_comment("lbl_mid_sec", [8, 8, 40, 14], "MID",
                   textcolor=[0.45, 0.85, 0.65, 1.0], fontsize=10.5)
device.add_comment("lbl_side_sec", [174, 8, 40, 14], "SIDE",
                   textcolor=[0.45, 0.65, 0.95, 1.0], fontsize=10.5)

# --- MID section controls ---
device.add_dial("mid_gain_dial", "Mid Gain", [8, 26, 50, 60],
                min_val=-12.0, max_val=12.0, initial=0.0,
                shortname="M Gain", unitstyle=4,
                annotation_name="Mid Channel Gain")
device.add_comment("lbl_mid_gain", [8, 88, 50, 12], "GAIN",
                   textcolor=[0.45, 0.75, 0.65, 0.7], fontsize=8.0,
                   justification=1)

# Tilt EQ: negative = bass boost, positive = treble boost
device.add_dial("mid_tilt_dial", "Mid Tilt EQ", [62, 26, 50, 60],
                min_val=-100.0, max_val=100.0, initial=0.0,
                shortname="M Lo/Hi", unitstyle=5,
                annotation_name="Mid Tilt EQ — left = bass, right = treble")
device.add_comment("lbl_mid_tilt", [62, 88, 50, 12], "LO — HI",
                   textcolor=[0.45, 0.75, 0.65, 0.7], fontsize=8.0,
                   justification=1)

device.add_dial("mid_drive_dial", "Mid Drive", [116, 26, 50, 60],
                min_val=0.0, max_val=100.0, initial=0.0,
                shortname="M Drive", unitstyle=5,
                annotation_name="Mid Saturation Drive")
device.add_comment("lbl_mid_drive", [116, 88, 50, 12], "DRIVE",
                   textcolor=[0.45, 0.75, 0.65, 0.7], fontsize=8.0,
                   justification=1)

device.add_tab("mid_sat_tab", "Mid Sat", [8, 104, 154, 20],
               options=["TAPE", "TUBE", "CLIP", "OFF"],
               bgcolor=[0.06, 0.08, 0.07, 1.0],
               bgoncolor=[0.25, 0.50, 0.35, 1.0],
               textcolor=[0.55, 0.55, 0.55, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# --- SIDE section controls ---
device.add_dial("side_gain_dial", "Side Gain", [174, 26, 50, 60],
                min_val=-12.0, max_val=12.0, initial=0.0,
                shortname="S Gain", unitstyle=4,
                annotation_name="Side Channel Gain")
device.add_comment("lbl_side_gain", [174, 88, 50, 12], "GAIN",
                   textcolor=[0.45, 0.60, 0.90, 0.7], fontsize=8.0,
                   justification=1)

device.add_dial("side_tilt_dial", "Side Tilt EQ", [228, 26, 50, 60],
                min_val=-100.0, max_val=100.0, initial=0.0,
                shortname="S Lo/Hi", unitstyle=5,
                annotation_name="Side Tilt EQ — left = bass, right = treble")
device.add_comment("lbl_side_tilt", [228, 88, 50, 12], "LO — HI",
                   textcolor=[0.45, 0.60, 0.90, 0.7], fontsize=8.0,
                   justification=1)

device.add_dial("side_drive_dial", "Side Drive", [282, 26, 50, 60],
                min_val=0.0, max_val=100.0, initial=0.0,
                shortname="S Drive", unitstyle=5,
                annotation_name="Side Saturation Drive")
device.add_comment("lbl_side_drive", [282, 88, 50, 12], "DRIVE",
                   textcolor=[0.45, 0.60, 0.90, 0.7], fontsize=8.0,
                   justification=1)

device.add_tab("side_sat_tab", "Side Sat", [174, 104, 154, 20],
               options=["TAPE", "TUBE", "CLIP", "OFF"],
               bgcolor=[0.05, 0.06, 0.09, 1.0],
               bgoncolor=[0.20, 0.30, 0.60, 1.0],
               textcolor=[0.55, 0.55, 0.55, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# --- Output L/R Meters (right edge) ---
device.add_meter("meter_out_l", [333, 8, 12, 130],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

device.add_meter("meter_out_r", [350, 8, 12, 130],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# --- Output mix dial ---
device.add_comment("lbl_output_sec", [333, 144, 32, 12], "MIX",
                   textcolor=[0.45, 0.75, 0.65, 0.6], fontsize=9.0)
device.add_dial("mix_dial", "Mix", [333, 156, 38, 38],
                min_val=0.0, max_val=100.0, initial=100.0,
                shortname="Mix", unitstyle=5,
                annotation_name="Dry/Wet Mix")

# =========================================================================
# DSP objects  (patching_rect x/y layout — grouped by function)
# =========================================================================

# ── M/S Encode ───────────────────────────────────────────────────────────
# mid = (L + R) * 0.5
device.add_newobj("enc_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 100, 30, 20])
device.add_newobj("enc_mul_mid", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 130, 50, 20])
# side = (L - R) * 0.5
device.add_newobj("enc_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 100, 30, 20])
device.add_newobj("enc_mul_side", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 130, 50, 20])

# ── MID channel gain ─────────────────────────────────────────────────────
# Gain dial (-12..+12 dB) -> dbtoa -> pack/line~ -> *~ signal
device.add_newobj("mid_gain_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 170, 50, 20])
# Smoothing for mid gain
device.add_newobj("mid_gain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 195, 60, 20])
device.add_newobj("mid_gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 225, 40, 20])
device.add_newobj("mid_gain_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 255, 40, 20])

# ── MID tilt EQ ──────────────────────────────────────────────────────────
device.add_newobj("mid_tilt_norm", "scale -100. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 290, 130, 20])
device.add_newobj("mid_tilt_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[30, 320, 45, 20])
# lo_gain = (1 - tilt_norm) * 2
device.add_newobj("mid_lo_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 350, 45, 20])
device.add_newobj("mid_lo_scale", "* 2.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 380, 40, 20])
# hi_gain = tilt_norm * 2
device.add_newobj("mid_hi_scale", "* 2.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 350, 40, 20])

# Smoothing for mid lo_gain
device.add_newobj("mid_lo_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 405, 60, 20])
device.add_newobj("mid_lo_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 435, 40, 20])
# Smoothing for mid hi_gain
device.add_newobj("mid_hi_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 380, 60, 20])
device.add_newobj("mid_hi_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[100, 410, 40, 20])

# onepole~ for LP at 1000 Hz crossover
device.add_newobj("mid_lp", "onepole~ 1000.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 460, 80, 20])
# HP = signal - LP
device.add_newobj("mid_hp_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[130, 460, 30, 20])
# Apply lo_gain to LP band
device.add_newobj("mid_lo_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 490, 40, 20])
# Apply hi_gain to HP band
device.add_newobj("mid_hi_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[130, 490, 40, 20])
# Sum lo + hi
device.add_newobj("mid_tilt_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 520, 30, 20])

# ── MID saturation ───────────────────────────────────────────────────────
# Drive dial 0..100 -> scale 0.5..4.0 -> pack/line~ -> pre-sat gain *~
# 0.5 at drive=0 means light saturation, not silence
device.add_newobj("mid_drive_scale", "scale 0. 100. 0.5 4.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 550, 120, 20])
# Smoothing for mid drive
device.add_newobj("mid_drive_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 575, 60, 20])
device.add_newobj("mid_drive_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 605, 40, 20])
device.add_newobj("mid_drive_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 635, 40, 20])

# Saturation modes fed into selector~
device.add_newobj("mid_tanh", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 665, 45, 20])
device.add_newobj("mid_overdrive", "overdrive~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[85, 665, 70, 20])
device.add_newobj("mid_clip", "clip~ -1. 1.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[165, 665, 70, 20])
device.add_newobj("mid_bypass", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[245, 665, 40, 20])

# selector~ 4 1: inlet 0=int select, inlets 1-4=signal inputs; init=1 (TAPE)
device.add_newobj("mid_sel", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 700, 85, 20])
# live.tab 0-indexed -> + 1 -> selector~ 1-indexed
device.add_newobj("mid_sat_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 550, 35, 20])

# ── SIDE channel gain ────────────────────────────────────────────────────
device.add_newobj("side_gain_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 170, 50, 20])
# Smoothing for side gain
device.add_newobj("side_gain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 195, 60, 20])
device.add_newobj("side_gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 225, 40, 20])
device.add_newobj("side_gain_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 255, 40, 20])

# ── SIDE tilt EQ ─────────────────────────────────────────────────────────
device.add_newobj("side_tilt_norm", "scale -100. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 290, 130, 20])
device.add_newobj("side_tilt_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[400, 320, 45, 20])
device.add_newobj("side_lo_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 350, 45, 20])
device.add_newobj("side_lo_scale", "* 2.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 380, 40, 20])
device.add_newobj("side_hi_scale", "* 2.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[470, 350, 40, 20])

# Smoothing for side lo_gain
device.add_newobj("side_lo_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 405, 60, 20])
device.add_newobj("side_lo_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 435, 40, 20])
# Smoothing for side hi_gain
device.add_newobj("side_hi_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[470, 380, 60, 20])
device.add_newobj("side_hi_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[470, 410, 40, 20])

device.add_newobj("side_lp", "onepole~ 1000.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 460, 80, 20])
device.add_newobj("side_hp_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 460, 30, 20])
device.add_newobj("side_lo_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 490, 40, 20])
device.add_newobj("side_hi_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 490, 40, 20])
device.add_newobj("side_tilt_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 520, 30, 20])

# ── SIDE saturation ──────────────────────────────────────────────────────
device.add_newobj("side_drive_scale", "scale 0. 100. 0.5 4.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 550, 120, 20])
# Smoothing for side drive
device.add_newobj("side_drive_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 575, 60, 20])
device.add_newobj("side_drive_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 605, 40, 20])
device.add_newobj("side_drive_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 635, 40, 20])

device.add_newobj("side_tanh", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 665, 45, 20])
device.add_newobj("side_overdrive", "overdrive~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[455, 665, 70, 20])
device.add_newobj("side_clip", "clip~ -1. 1.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[535, 665, 70, 20])
device.add_newobj("side_bypass", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[615, 665, 40, 20])

device.add_newobj("side_sel", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 700, 85, 20])
device.add_newobj("side_sat_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[400, 550, 35, 20])

# ── M/S Decode ───────────────────────────────────────────────────────────
# L = Mid' + Side'
device.add_newobj("dec_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 740, 30, 20])
# R = Mid' - Side'
device.add_newobj("dec_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[270, 740, 30, 20])

# ── DC block (biquad~) ───────────────────────────────────────────────────
# biquad~ 1. -1. 0. -0.9997 0. = DC block highpass
device.add_newobj("dc_l", "biquad~ 1. -1. 0. -0.9997 0.", numinlets=6, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 770, 160, 20])
device.add_newobj("dc_r", "biquad~ 1. -1. 0. -0.9997 0.", numinlets=6, numoutlets=1,
                  outlettype=["signal"], patching_rect=[370, 770, 160, 20])

# ── Dry/wet mix ──────────────────────────────────────────────────────────
# mix_dial 0..100 -> scale 0..1.0
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[600, 60, 120, 20])
# t f f f fires RIGHT to LEFT: outlet 2 first, then 1, then 0
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[600, 90, 55, 20])
# !-~ 1. = (1 - mix) for dry gain
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[600, 120, 45, 20])
device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 810, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[540, 810, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[660, 810, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[700, 810, 30, 20])
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[580, 850, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[620, 850, 30, 20])

# =========================================================================
# Connections
# =========================================================================

# ── M/S Encode ───────────────────────────────────────────────────────────
# plugin~ L -> enc_add inlet 0, enc_sub inlet 0
device.add_line("obj-plugin", 0, "enc_add", 0)
device.add_line("obj-plugin", 0, "enc_sub", 0)
# plugin~ R -> enc_add inlet 1, enc_sub inlet 1
device.add_line("obj-plugin", 1, "enc_add", 1)
device.add_line("obj-plugin", 1, "enc_sub", 1)
# enc_add -> *0.5 = mid
device.add_line("enc_add", 0, "enc_mul_mid", 0)
# enc_sub -> *0.5 = side
device.add_line("enc_sub", 0, "enc_mul_side", 0)

# ── MID gain ─────────────────────────────────────────────────────────────
device.add_line("mid_gain_dial", 0, "mid_gain_dbtoa", 0)
device.add_line("enc_mul_mid", 0, "mid_gain_mul", 0)        # mid signal -> *~ signal inlet
# dbtoa -> pack -> line~ -> *~ multiplier (smoothed)
device.add_line("mid_gain_dbtoa", 0, "mid_gain_pk", 0)
device.add_line("mid_gain_pk", 0, "mid_gain_ln", 0)
device.add_line("mid_gain_ln", 0, "mid_gain_mul", 1)

# ── MID tilt EQ ──────────────────────────────────────────────────────────
device.add_line("mid_tilt_dial", 0, "mid_tilt_norm", 0)
device.add_line("mid_tilt_norm", 0, "mid_tilt_fan", 0)
# t f f fires outlet 1 first (cold), then outlet 0 (hot)
device.add_line("mid_tilt_fan", 0, "mid_lo_inv", 0)         # tilt_norm -> !- 1.
device.add_line("mid_tilt_fan", 1, "mid_hi_scale", 0)       # tilt_norm -> * 2. (hi gain)
device.add_line("mid_lo_inv", 0, "mid_lo_scale", 0)         # (1-tilt_norm) -> * 2.
# lo_gain -> pack -> line~ -> *~ inlet 1 (smoothed)
device.add_line("mid_lo_scale", 0, "mid_lo_pk", 0)
device.add_line("mid_lo_pk", 0, "mid_lo_ln", 0)
device.add_line("mid_lo_ln", 0, "mid_lo_mul", 1)
# hi_gain -> pack -> line~ -> *~ inlet 1 (smoothed)
device.add_line("mid_hi_scale", 0, "mid_hi_pk", 0)
device.add_line("mid_hi_pk", 0, "mid_hi_ln", 0)
device.add_line("mid_hi_ln", 0, "mid_hi_mul", 1)

# onepole~ LP: mid_gain_mul -> onepole~ signal
device.add_line("mid_gain_mul", 0, "mid_lp", 0)             # signal -> onepole~ inlet 0
# HP: signal - LP
device.add_line("mid_gain_mul", 0, "mid_hp_sub", 0)         # signal -> -~ inlet 0
device.add_line("mid_lp", 0, "mid_hp_sub", 1)               # LP -> -~ inlet 1 (signal - LP = HP)
# Apply gains
device.add_line("mid_lp", 0, "mid_lo_mul", 0)               # LP signal -> *~ inlet 0
device.add_line("mid_hp_sub", 0, "mid_hi_mul", 0)           # HP signal -> *~ inlet 0
# Sum
device.add_line("mid_lo_mul", 0, "mid_tilt_sum", 0)
device.add_line("mid_hi_mul", 0, "mid_tilt_sum", 1)

# ── MID saturation ───────────────────────────────────────────────────────
device.add_line("mid_drive_dial", 0, "mid_drive_scale", 0)
device.add_line("mid_tilt_sum", 0, "mid_drive_mul", 0)      # tilt output -> *~ signal
# drive_scale -> pack -> line~ -> *~ multiplier (smoothed)
device.add_line("mid_drive_scale", 0, "mid_drive_pk", 0)
device.add_line("mid_drive_pk", 0, "mid_drive_ln", 0)
device.add_line("mid_drive_ln", 0, "mid_drive_mul", 1)

# Drive output fans to all saturation stages
device.add_line("mid_drive_mul", 0, "mid_tanh", 0)
device.add_line("mid_drive_mul", 0, "mid_overdrive", 0)
device.add_line("mid_drive_mul", 0, "mid_clip", 0)
device.add_line("mid_drive_mul", 0, "mid_bypass", 0)

# Saturation outputs -> selector~ signal inlets (1-indexed)
device.add_line("mid_tanh", 0, "mid_sel", 1)                # TAPE -> inlet 1
device.add_line("mid_overdrive", 0, "mid_sel", 2)           # TUBE -> inlet 2
device.add_line("mid_clip", 0, "mid_sel", 3)                # CLIP -> inlet 3
device.add_line("mid_bypass", 0, "mid_sel", 4)              # OFF  -> inlet 4

# live.tab -> + 1 -> selector~ int inlet 0
device.add_line("mid_sat_tab", 0, "mid_sat_offset", 0)
device.add_line("mid_sat_offset", 0, "mid_sel", 0)

# ── SIDE gain ────────────────────────────────────────────────────────────
device.add_line("side_gain_dial", 0, "side_gain_dbtoa", 0)
device.add_line("enc_mul_side", 0, "side_gain_mul", 0)
# dbtoa -> pack -> line~ -> *~ multiplier (smoothed)
device.add_line("side_gain_dbtoa", 0, "side_gain_pk", 0)
device.add_line("side_gain_pk", 0, "side_gain_ln", 0)
device.add_line("side_gain_ln", 0, "side_gain_mul", 1)

# ── SIDE tilt EQ ─────────────────────────────────────────────────────────
device.add_line("side_tilt_dial", 0, "side_tilt_norm", 0)
device.add_line("side_tilt_norm", 0, "side_tilt_fan", 0)
device.add_line("side_tilt_fan", 0, "side_lo_inv", 0)
device.add_line("side_tilt_fan", 1, "side_hi_scale", 0)
device.add_line("side_lo_inv", 0, "side_lo_scale", 0)
# lo_gain -> pack -> line~ -> *~ inlet 1 (smoothed)
device.add_line("side_lo_scale", 0, "side_lo_pk", 0)
device.add_line("side_lo_pk", 0, "side_lo_ln", 0)
device.add_line("side_lo_ln", 0, "side_lo_mul", 1)
# hi_gain -> pack -> line~ -> *~ inlet 1 (smoothed)
device.add_line("side_hi_scale", 0, "side_hi_pk", 0)
device.add_line("side_hi_pk", 0, "side_hi_ln", 0)
device.add_line("side_hi_ln", 0, "side_hi_mul", 1)

device.add_line("side_gain_mul", 0, "side_lp", 0)
device.add_line("side_gain_mul", 0, "side_hp_sub", 0)
device.add_line("side_lp", 0, "side_hp_sub", 1)
device.add_line("side_lp", 0, "side_lo_mul", 0)
device.add_line("side_hp_sub", 0, "side_hi_mul", 0)
device.add_line("side_lo_mul", 0, "side_tilt_sum", 0)
device.add_line("side_hi_mul", 0, "side_tilt_sum", 1)

# ── SIDE saturation ──────────────────────────────────────────────────────
device.add_line("side_drive_dial", 0, "side_drive_scale", 0)
device.add_line("side_tilt_sum", 0, "side_drive_mul", 0)
# drive_scale -> pack -> line~ -> *~ multiplier (smoothed)
device.add_line("side_drive_scale", 0, "side_drive_pk", 0)
device.add_line("side_drive_pk", 0, "side_drive_ln", 0)
device.add_line("side_drive_ln", 0, "side_drive_mul", 1)

device.add_line("side_drive_mul", 0, "side_tanh", 0)
device.add_line("side_drive_mul", 0, "side_overdrive", 0)
device.add_line("side_drive_mul", 0, "side_clip", 0)
device.add_line("side_drive_mul", 0, "side_bypass", 0)

device.add_line("side_tanh", 0, "side_sel", 1)
device.add_line("side_overdrive", 0, "side_sel", 2)
device.add_line("side_clip", 0, "side_sel", 3)
device.add_line("side_bypass", 0, "side_sel", 4)

device.add_line("side_sat_tab", 0, "side_sat_offset", 0)
device.add_line("side_sat_offset", 0, "side_sel", 0)

# ── M/S Decode ───────────────────────────────────────────────────────────
# L = Mid' + Side'
device.add_line("mid_sel", 0, "dec_add", 0)
device.add_line("side_sel", 0, "dec_add", 1)
# R = Mid' - Side'
device.add_line("mid_sel", 0, "dec_sub", 0)
device.add_line("side_sel", 0, "dec_sub", 1)

# ── DC block ─────────────────────────────────────────────────────────────
device.add_line("dec_add", 0, "dc_l", 0)
device.add_line("dec_sub", 0, "dc_r", 0)

# ── Dry/wet mix ──────────────────────────────────────────────────────────
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# t f f f outlets fire RIGHT to LEFT: outlet 2, then 1, then 0
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

# Wet signal: DC-blocked output -> wet multipliers
device.add_line("dc_l", 0, "wet_l", 0)
device.add_line("dc_r", 0, "wet_r", 0)

# Dry signal: raw plugin~ -> dry multipliers
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Sum wet + dry
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# Output to plugout~
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# --- Output L/R meters: tap final output signals ---
device.add_line("out_l", 0, "meter_out_l", 0)
device.add_line("out_r", 0, "meter_out_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("MidSide Suite", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
