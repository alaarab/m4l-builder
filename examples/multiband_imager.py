"""Multiband Stereo Imager — 3-band crossover with per-band M/S width control."""

import os
from m4l_builder import AudioEffect, COOL, device_output_path

# --- Device setup ---
W, H = 340, 170
device = AudioEffect("Multiband Imager", width=W, height=H, theme=COOL)

# --- UI ---

# Background panel
device.add_panel("bg", [0, 0, W, H], bgcolor=COOL.bg)

# Row 1: Crossover frequency dials
device.add_comment("lbl_xover", [15, 18, 120, 12], "CROSSOVER",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

device.add_dial("dial_low_xover", "Low Xover", [15, 28, 55, 60],
                min_val=20.0, max_val=2000.0, initial=200.0,
                shortname="Lo X", unitstyle=3,  # Hz
                annotation_name="Low crossover frequency")

device.add_dial("dial_high_xover", "High Xover", [80, 28, 55, 60],
                min_val=500.0, max_val=20000.0, initial=4000.0,
                shortname="Hi X", unitstyle=3,  # Hz
                annotation_name="High crossover frequency")

# Row 1 labels
device.add_comment("lbl_lox", [15, 90, 55, 12], "LO X",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                   justification=1)
device.add_comment("lbl_hix", [80, 90, 55, 12], "HI X",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                   justification=1)

# Stereo output meters (L/R) — COOL theme blue tones
device.add_comment("lbl_out", [210, 6, 40, 16], "OUT",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0)
device.add_meter("meter_l", [210, 22, 10, 66],
                 coldcolor=[0.20, 0.40, 0.65, 1.0],
                 warmcolor=[0.35, 0.60, 0.90, 1.0],
                 hotcolor=[0.75, 0.65, 0.25, 1.0],
                 overloadcolor=[0.90, 0.20, 0.15, 1.0])
device.add_meter("meter_r", [224, 22, 10, 66],
                 coldcolor=[0.20, 0.40, 0.65, 1.0],
                 warmcolor=[0.35, 0.60, 0.90, 1.0],
                 hotcolor=[0.75, 0.65, 0.25, 1.0],
                 overloadcolor=[0.90, 0.20, 0.15, 1.0])

# Vectorscope (Lissajous XY scope)
device.add_scope("vectorscope", [244, 6, 90, 82],
                 bgcolor=[0.06, 0.06, 0.08, 1.0],
                 activelinecolor=[0.35, 0.60, 0.90, 0.7],
                 gridcolor=[0.15, 0.15, 0.17, 0.3],
                 range_vals=[-1.0, 1.0],
                 calccount=32, smooth=2, line_width=1.0,
                 decay_time=80)

# Row 2: Width dials per band
device.add_comment("lbl_width", [15, 90, 185, 12], "WIDTH",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

device.add_dial("dial_low_w", "Low Width", [15, 100, 55, 55],
                min_val=0.0, max_val=200.0, initial=100.0,
                shortname="Lo W", unitstyle=5,  # Percent
                annotation_name="Low band stereo width")

device.add_dial("dial_mid_w", "Mid Width", [80, 100, 55, 55],
                min_val=0.0, max_val=200.0, initial=100.0,
                shortname="Mid W", unitstyle=5,
                annotation_name="Mid band stereo width")

device.add_dial("dial_high_w", "High Width", [145, 100, 55, 55],
                min_val=0.0, max_val=200.0, initial=100.0,
                shortname="Hi W", unitstyle=5,
                annotation_name="High band stereo width")

# Per-band labels under width dials
device.add_comment("lbl_lo_band", [15, 157, 55, 11], "LO",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                   justification=1)
device.add_comment("lbl_mid_band", [80, 157, 55, 11], "MID",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                   justification=1)
device.add_comment("lbl_hi_band", [145, 157, 55, 11], "HI",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                   justification=1)

# --- DSP ---
# plugin~ (obj-plugin) and plugout~ (obj-plugout) are auto-added.
#
# Signal flow:
#   plugin~ L/R → cross~ low_freq → LP=LOW, HP=MID+HIGH
#                 MID+HIGH → cross~ high_freq → LP=MID, HP=HIGH
#   Per band: M/S encode → width scale → smoothed line~ → M/S decode
#   Sum all 3 bands → plugout~

# ── Crossover (Left channel) ───────────────────────────────────────────────
# cross~ has 2 inlets (signal, freq) and 2 outlets (LP=0, HP=1)

# Stage 1: split at low frequency → LOW and MID+HIGH
device.add_newobj("xo1_l", "cross~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[30, 160, 50, 20])

# Stage 2: split MID+HIGH at high frequency → MID and HIGH
device.add_newobj("xo2_l", "cross~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[30, 190, 50, 20])

# ── Crossover (Right channel) ──────────────────────────────────────────────
device.add_newobj("xo1_r", "cross~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[300, 160, 50, 20])

device.add_newobj("xo2_r", "cross~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[300, 190, 50, 20])

# ── Parameter smoothing: crossover frequencies ─────────────────────────────
# dial_low_xover → lox_pk → lox_ln → xo1_l/r inlet 1 (signal)
device.add_newobj("lox_pk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[30, 135, 60, 20])
device.add_newobj("lox_ln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[30, 148, 40, 20])

# dial_high_xover → hix_pk → hix_ln → xo2_l/r inlet 1 (signal)
device.add_newobj("hix_pk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[130, 135, 60, 20])
device.add_newobj("hix_ln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[130, 148, 40, 20])

# ── LOW band M/S ───────────────────────────────────────────────────────────
# Encode: mid = (L+R)*0.5, side = (L-R)*0.5
device.add_newobj("lo_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 240, 30, 20])
device.add_newobj("lo_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[70, 240, 30, 20])
device.add_newobj("lo_mid", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 260, 50, 20])
device.add_newobj("lo_side", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[70, 260, 50, 20])

# Width scale: dial 0-200 → 0.0-2.0
device.add_newobj("lo_wscale", "scale 0. 200. 0. 2.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[70, 280, 110, 20])

# Width smoothing: lo_wscale → lo_wpk → lo_wln → lo_wmul inlet 1
device.add_newobj("lo_wpk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[70, 298, 60, 20])
device.add_newobj("lo_wln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[70, 313, 40, 20])

# Width: side * smoothed_width_factor
device.add_newobj("lo_wmul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[70, 330, 40, 20])

# Decode: L = mid + scaled_side, R = mid - scaled_side
device.add_newobj("lo_dec_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 360, 30, 20])
device.add_newobj("lo_inv", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 330, 50, 20])
device.add_newobj("lo_dec_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 360, 30, 20])

# ── MID band M/S ──────────────────────────────────────────────────────────
device.add_newobj("mid_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 240, 30, 20])
device.add_newobj("mid_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 240, 30, 20])
device.add_newobj("mid_mid", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 260, 50, 20])
device.add_newobj("mid_side", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 260, 50, 20])

device.add_newobj("mid_wscale", "scale 0. 200. 0. 2.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[240, 280, 110, 20])

# Width smoothing: mid_wscale → mid_wpk → mid_wln → mid_wmul inlet 1
device.add_newobj("mid_wpk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[240, 298, 60, 20])
device.add_newobj("mid_wln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[240, 313, 40, 20])

device.add_newobj("mid_wmul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 330, 40, 20])

device.add_newobj("mid_dec_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 360, 30, 20])
device.add_newobj("mid_inv", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 330, 50, 20])
device.add_newobj("mid_dec_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 360, 30, 20])

# ── HIGH band M/S ─────────────────────────────────────────────────────────
device.add_newobj("hi_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[370, 240, 30, 20])
device.add_newobj("hi_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[410, 240, 30, 20])
device.add_newobj("hi_mid", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[370, 260, 50, 20])
device.add_newobj("hi_side", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[410, 260, 50, 20])

device.add_newobj("hi_wscale", "scale 0. 200. 0. 2.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[410, 280, 110, 20])

# Width smoothing: hi_wscale → hi_wpk → hi_wln → hi_wmul inlet 1
device.add_newobj("hi_wpk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[410, 298, 60, 20])
device.add_newobj("hi_wln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[410, 313, 40, 20])

device.add_newobj("hi_wmul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[410, 330, 40, 20])

device.add_newobj("hi_dec_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[370, 360, 30, 20])
device.add_newobj("hi_inv", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 330, 50, 20])
device.add_newobj("hi_dec_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 360, 30, 20])

# ── Sum all 3 bands ───────────────────────────────────────────────────────
# L: lo_dec_l + mid_dec_l + hi_dec_l
device.add_newobj("sum_lm_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 400, 30, 20])
device.add_newobj("sum_all_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 430, 30, 20])

# R: lo_dec_r + mid_dec_r + hi_dec_r
device.add_newobj("sum_lm_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 400, 30, 20])
device.add_newobj("sum_all_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 430, 30, 20])

# --- Connections ---

# ── Audio input → crossovers ──────────────────────────────────────────────
device.add_line("obj-plugin", 0, "xo1_l", 0)   # L → crossover 1 L
device.add_line("obj-plugin", 1, "xo1_r", 0)   # R → crossover 1 R

# Crossover frequencies with smoothing
# Low: dial → pack → line~ → xo1_l/r inlet 1 (signal)
device.add_line("dial_low_xover", 0, "lox_pk", 0)
device.add_line("lox_pk", 0, "lox_ln", 0)
device.add_line("lox_ln", 0, "xo1_l", 1)
device.add_line("lox_ln", 0, "xo1_r", 1)

# High: dial → pack → line~ → xo2_l/r inlet 1 (signal)
device.add_line("dial_high_xover", 0, "hix_pk", 0)
device.add_line("hix_pk", 0, "hix_ln", 0)
device.add_line("hix_ln", 0, "xo2_l", 1)
device.add_line("hix_ln", 0, "xo2_r", 1)

# Stage 1 HP (MID+HIGH) → Stage 2
device.add_line("xo1_l", 1, "xo2_l", 0)   # xo1 L HP → xo2 L signal
device.add_line("xo1_r", 1, "xo2_r", 0)   # xo1 R HP → xo2 R signal

# ── LOW band wiring ──────────────────────────────────────────────────────
# xo1 LP (outlet 0) = LOW band L and R
device.add_line("xo1_l", 0, "lo_add", 0)    # LOW L → sum inlet 0
device.add_line("xo1_r", 0, "lo_add", 1)    # LOW R → sum inlet 1
device.add_line("xo1_l", 0, "lo_sub", 0)    # LOW L → diff inlet 0
device.add_line("xo1_r", 0, "lo_sub", 1)    # LOW R → diff inlet 1
device.add_line("lo_add", 0, "lo_mid", 0)   # sum → *0.5 = mid
device.add_line("lo_sub", 0, "lo_side", 0)  # diff → *0.5 = side

# Width control with smoothing: dial → scale → pack → line~ → *~ inlet 1
device.add_line("dial_low_w", 0, "lo_wscale", 0)    # dial → scale
device.add_line("lo_wscale", 0, "lo_wpk", 0)        # scaled float → pack
device.add_line("lo_wpk", 0, "lo_wln", 0)           # pack → line~
device.add_line("lo_wln", 0, "lo_wmul", 1)          # smoothed signal → *~ inlet 1
device.add_line("lo_side", 0, "lo_wmul", 0)          # side signal → *~ inlet 0

# Decode
device.add_line("lo_mid", 0, "lo_dec_l", 0)          # mid → + inlet 0
device.add_line("lo_wmul", 0, "lo_dec_l", 1)         # scaled_side → + inlet 1 (L = mid + side)
device.add_line("lo_wmul", 0, "lo_inv", 0)            # scaled_side → *~ -1.
device.add_line("lo_mid", 0, "lo_dec_r", 0)           # mid → + inlet 0
device.add_line("lo_inv", 0, "lo_dec_r", 1)           # -scaled_side → + inlet 1 (R = mid - side)

# ── MID band wiring ─────────────────────────────────────────────────────
# xo2 LP (outlet 0) = MID band L and R
device.add_line("xo2_l", 0, "mid_add", 0)
device.add_line("xo2_r", 0, "mid_add", 1)
device.add_line("xo2_l", 0, "mid_sub", 0)
device.add_line("xo2_r", 0, "mid_sub", 1)
device.add_line("mid_add", 0, "mid_mid", 0)
device.add_line("mid_sub", 0, "mid_side", 0)

device.add_line("dial_mid_w", 0, "mid_wscale", 0)
device.add_line("mid_wscale", 0, "mid_wpk", 0)
device.add_line("mid_wpk", 0, "mid_wln", 0)
device.add_line("mid_wln", 0, "mid_wmul", 1)
device.add_line("mid_side", 0, "mid_wmul", 0)

device.add_line("mid_mid", 0, "mid_dec_l", 0)
device.add_line("mid_wmul", 0, "mid_dec_l", 1)
device.add_line("mid_wmul", 0, "mid_inv", 0)
device.add_line("mid_mid", 0, "mid_dec_r", 0)
device.add_line("mid_inv", 0, "mid_dec_r", 1)

# ── HIGH band wiring ────────────────────────────────────────────────────
# xo2 HP (outlet 1) = HIGH band L and R
device.add_line("xo2_l", 1, "hi_add", 0)
device.add_line("xo2_r", 1, "hi_add", 1)
device.add_line("xo2_l", 1, "hi_sub", 0)
device.add_line("xo2_r", 1, "hi_sub", 1)
device.add_line("hi_add", 0, "hi_mid", 0)
device.add_line("hi_sub", 0, "hi_side", 0)

device.add_line("dial_high_w", 0, "hi_wscale", 0)
device.add_line("hi_wscale", 0, "hi_wpk", 0)
device.add_line("hi_wpk", 0, "hi_wln", 0)
device.add_line("hi_wln", 0, "hi_wmul", 1)
device.add_line("hi_side", 0, "hi_wmul", 0)

device.add_line("hi_mid", 0, "hi_dec_l", 0)
device.add_line("hi_wmul", 0, "hi_dec_l", 1)
device.add_line("hi_wmul", 0, "hi_inv", 0)
device.add_line("hi_mid", 0, "hi_dec_r", 0)
device.add_line("hi_inv", 0, "hi_dec_r", 1)

# ── Sum all bands ────────────────────────────────────────────────────────
# L: low + mid → sum_lm_l, then + high → sum_all_l
device.add_line("lo_dec_l", 0, "sum_lm_l", 0)
device.add_line("mid_dec_l", 0, "sum_lm_l", 1)
device.add_line("sum_lm_l", 0, "sum_all_l", 0)
device.add_line("hi_dec_l", 0, "sum_all_l", 1)

# R: low + mid → sum_lm_r, then + high → sum_all_r
device.add_line("lo_dec_r", 0, "sum_lm_r", 0)
device.add_line("mid_dec_r", 0, "sum_lm_r", 1)
device.add_line("sum_lm_r", 0, "sum_all_r", 0)
device.add_line("hi_dec_r", 0, "sum_all_r", 1)

# ── Output ───────────────────────────────────────────────────────────────
device.add_line("sum_all_l", 0, "obj-plugout", 0)
device.add_line("sum_all_r", 0, "obj-plugout", 1)

# ── Output meters + vectorscope ─────────────────────────────────────────
device.add_line("sum_all_l", 0, "meter_l", 0)
device.add_line("sum_all_r", 0, "meter_r", 0)
device.add_line("sum_all_l", 0, "vectorscope", 0)   # L → X axis
device.add_line("sum_all_r", 0, "vectorscope", 1)   # R → Y axis

# --- Build ---
output = device_output_path("Multiband Imager")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
