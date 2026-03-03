"""Stereo Delay with Feedback Saturation — m4l_builder example.

Signal flow (per channel):
  plugin~ → +~ (mix with feedback) → tapin~ 5000
  tapin~ → tapout~ (delay_ms float)
  tapout~ → tanh~ (saturate: warmer each repeat)
  tanh~ → onepole~ (damping: darker each repeat)
  onepole~ → *~ feedback_amount (0.0-0.95) → back to +~ inlet 1
  tapout~ also → *~ wet_gain → out_+~
  plugin~ → *~ dry_gain → out_+~

Mode tab: Stereo / PingPong / Mono
  - Stereo: L and R delay independently
  - PingPong: L feedback → R input, R feedback → L input (cross-feedback)
  - Mono: both channels share same delay time

Parameter smoothing: all dial → *~/onepole~ paths use pack f 20 → line~
  to eliminate zipper noise on automation and fast knob movements.

Tempo sync: live.menu selects Free or note division (1/1 to 1/16).
  When synced, delay time is derived from transport BPM via expr.
  selector~ 2 switches between free dial value and synced ms.

Output meters: L/R live.meter~ on the right edge for visual feedback.
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT

# --- Device setup (widened 30px for output meters) ---
WIDTH = 350
HEIGHT = 150
device = AudioEffect("Stereo Delay", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# --- UI ---
device.add_panel("bg", [0, 0, WIDTH, HEIGHT], bgcolor=[0.12, 0.12, 0.14, 1.0])

# Title
device.add_comment("title", [8, 6, 60, 16], "DELAY",
                   textcolor=[0.95, 0.92, 0.85, 1.0], fontsize=13.0)

# Mode tab: Stereo / PingPong / Mono (3 options)
device.add_tab("mode_tab", "Mode", [8, 26, 200, 20],
               options=["Stereo", "PingPong", "Mono"],
               bgcolor=[0.2, 0.2, 0.22, 1.0],
               bgoncolor=[0.35, 0.55, 0.75, 1.0],
               textcolor=[0.75, 0.75, 0.75, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# Section labels
device.add_comment("lbl_time", [8, 38, 80, 12], "TIME",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_char", [108, 38, 100, 12], "CHARACTER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_mix", [263, 38, 40, 12], "MIX",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Dials row
device.add_dial("ltime_dial", "L Time", [8, 48, 45, 75],
                min_val=1.0, max_val=5000.0, initial=375.0,
                unitstyle=2,
                annotation_name="Left channel delay time in milliseconds")

device.add_dial("rtime_dial", "R Time", [58, 48, 45, 75],
                min_val=1.0, max_val=5000.0, initial=500.0,
                unitstyle=2,
                annotation_name="Right channel delay time in milliseconds")

device.add_dial("fb_dial", "Feedback", [108, 48, 45, 75],
                min_val=0.0, max_val=95.0, initial=40.0,
                unitstyle=5,
                annotation_name="Feedback amount — higher values create more repeats")

device.add_dial("sat_dial", "Saturation", [158, 48, 45, 75],
                min_val=0.0, max_val=100.0, initial=30.0,
                unitstyle=5,
                annotation_name="Saturation drive into feedback — warmer with more repeats")

device.add_dial("tone_dial", "Tone", [208, 48, 45, 75],
                min_val=500.0, max_val=20000.0, initial=8000.0,
                unitstyle=3,
                annotation_name="Feedback damping — lower values darken each repeat")

device.add_dial("mix_dial", "Mix", [263, 48, 45, 75],
                min_val=0.0, max_val=100.0, initial=30.0,
                unitstyle=5,
                annotation_name="Dry/wet balance — 0% is fully dry, 100% fully wet")

# --- UI: Tempo sync menu ---
device.add_comment("lbl_sync", [215, 26, 40, 12], "SYNC",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_menu("sync_menu", "Sync", [248, 24, 60, 20],
                options=["Free", "1/1", "1/2", "1/4", "1/8", "1/16"])

# --- UI: Output meters ---
device.add_meter("meter_l", [WIDTH - 30, 8, 10, HEIGHT - 20],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [WIDTH - 16, 8, 10, HEIGHT - 20],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# ===================================================================
# DSP OBJECTS
# ===================================================================

# --- DSP: Delay buffers ---
device.add_newobj("tapin_l", "tapin~ 5000", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[30, 220, 80, 20])
device.add_newobj("tapin_r", "tapin~ 5000", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[200, 220, 80, 20])

# tapout~ inlet 1 = delay time float
device.add_newobj("tapout_l", "tapout~ 375", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 260, 80, 20])
device.add_newobj("tapout_r", "tapout~ 500", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 260, 80, 20])

# --- DSP: Feedback path (tanh~ → onepole~ → *~ feedback) ---
device.add_newobj("sat_gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 300, 40, 20])
device.add_newobj("sat_gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 300, 40, 20])

device.add_newobj("tanh_l", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 330, 40, 20])
device.add_newobj("tanh_r", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 330, 40, 20])

device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 360, 50, 20])
device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 360, 50, 20])

device.add_newobj("fb_mul_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 390, 40, 20])
device.add_newobj("fb_mul_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 390, 40, 20])

# --- DSP: Mode selector for feedback routing ---
# Modes: 1=Stereo, 2=PingPong (cross-feeds), 3=Mono
device.add_newobj("sel_fbl", "selector~ 3 1", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 430, 80, 20])
device.add_newobj("sel_fbr", "selector~ 3 1", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 430, 80, 20])

# live.tab is 0-indexed; selector~ is 1-indexed
device.add_newobj("tab_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 200, 40, 20])

# --- DSP: Input summing (dry input + feedback return) ---
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 470, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 470, 30, 20])

# --- DSP: Parameter scaling ---
# sat_dial 0-100 → 1.0-4.0 (unity to 4x drive into tanh~)
device.add_newobj("sat_scale", "scale 0. 100. 1. 4.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 300, 120, 20])

# fb_dial 0-95 → 0.0-0.95 (keep below 1.0 to prevent runaway)
device.add_newobj("fb_scale", "scale 0. 95. 0. 0.95", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 390, 120, 20])

device.add_newobj("fb_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[100, 410, 40, 20])

# --- DSP: Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 80, 120, 20])

# t f f f fans mix to wet_l, wet_r, and inverter (fires R to L)
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 100, 55, 20])

# !-~ 1. computes (1.0 - mix) for the dry gain
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 130, 45, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 500, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 500, 30, 20])

device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 500, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 500, 30, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 540, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 540, 30, 20])

# ===================================================================
# PARAMETER SMOOTHING: pack f 20 → line~ on all float-to-signal paths
# Eliminates zipper noise when automating dials or moving knobs quickly.
# ===================================================================

device.add_newobj("sat_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 315, 60, 20])
device.add_newobj("sat_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[100, 340, 40, 20])

device.add_newobj("tone_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 355, 60, 20])
device.add_newobj("tone_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[150, 380, 40, 20])

device.add_newobj("fb_pk_l", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[80, 425, 60, 20])
device.add_newobj("fb_ln_l", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[80, 450, 40, 20])
device.add_newobj("fb_pk_r", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[140, 425, 60, 20])
device.add_newobj("fb_ln_r", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[140, 450, 40, 20])

device.add_newobj("wetl_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 480, 60, 20])
device.add_newobj("wetl_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 505, 40, 20])

device.add_newobj("wetr_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[340, 480, 60, 20])
device.add_newobj("wetr_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[340, 505, 40, 20])

device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 140, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[460, 165, 40, 20])

# ===================================================================
# TEMPO SYNC: transport → expr (ms = 60000/BPM * beat_fraction) → selector~ → tapout~
# ===================================================================

# loadbang gets initial BPM on load; transport outlet 4 = tempo float
device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[550, 180, 55, 20])
device.add_newobj("transport", "transport", numinlets=1, numoutlets=7,
                  outlettype=["int", "", "float", "float", "float", "", "int"],
                  patching_rect=[550, 210, 70, 20])

# sel routes sync_menu index to beat fraction float messages
# outlet 0 = Free (no-op), outlets 1-5 = 1/1, 1/2, 1/4, 1/8, 1/16
device.add_newobj("sync_sel", "sel 0 1 2 3 4 5", numinlets=1, numoutlets=7,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[550, 250, 120, 20])

device.add_newobj("beat_4", "f 4.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[580, 280, 35, 20])
device.add_newobj("beat_2", "f 2.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[620, 280, 35, 20])
device.add_newobj("beat_1", "f 1.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[660, 280, 35, 20])
device.add_newobj("beat_05", "f 0.5", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[700, 280, 35, 20])
device.add_newobj("beat_025", "f 0.25", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[740, 280, 40, 20])

# beat_store holds last fraction so a tempo change can recalculate without re-selecting menu
device.add_newobj("beat_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[660, 310, 35, 20])

# expr: ms = 60000 / BPM * beat_fraction; inlet 0 = BPM, inlet 1 = fraction
device.add_newobj("sync_expr", "expr 60000. / $f1 * $f2", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[550, 350, 130, 20])

device.add_newobj("bpm_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[550, 310, 35, 20])

device.add_newobj("sync_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[550, 380, 40, 20])

# > 0: menu index 0 = Free → 0, indices 1-5 → 1 (synced)
device.add_newobj("sync_gt", "> 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[550, 265, 35, 20])

# +1 maps 0→1 (free) and 1→2 (synced) for selector~ inlet 0
device.add_newobj("sync_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[550, 285, 40, 20])

device.add_newobj("sync_menu_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[520, 240, 40, 20])

# selector~ 2 1: inlet 0=mode int, inlet 1=free (line~), inlet 2=synced (line~)
device.add_newobj("time_sel_l", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 240, 80, 20])
device.add_newobj("time_sel_r", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 240, 80, 20])

device.add_newobj("ltime_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 175, 60, 20])
device.add_newobj("ltime_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 200, 40, 20])
device.add_newobj("rtime_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 175, 60, 20])
device.add_newobj("rtime_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 200, 40, 20])

device.add_newobj("sync_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 395, 60, 20])
device.add_newobj("sync_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[550, 420, 40, 20])
device.add_newobj("sync_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[620, 395, 60, 20])
device.add_newobj("sync_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[620, 420, 40, 20])

# ===================================================================
# CONNECTIONS
# ===================================================================

# === Delay time: dials → pack/line~ (smooth) → selector~ inlet 1 (free) ===
device.add_line("ltime_dial", 0, "ltime_pk", 0)
device.add_line("ltime_pk", 0, "ltime_ln", 0)
device.add_line("ltime_ln", 0, "time_sel_l", 1)   # inlet 1 = free time

device.add_line("rtime_dial", 0, "rtime_pk", 0)
device.add_line("rtime_pk", 0, "rtime_ln", 0)
device.add_line("rtime_ln", 0, "time_sel_r", 1)   # inlet 1 = free time

# === Time selector output → tapout~ delay float ===
device.add_line("time_sel_l", 0, "tapout_l", 1)
device.add_line("time_sel_r", 0, "tapout_r", 1)

# === Saturation gain: sat_dial → scale → pack → line~ → sat_gain_l/r inlet 1 ===
device.add_line("sat_dial", 0, "sat_scale", 0)
device.add_line("sat_scale", 0, "sat_pk", 0)
device.add_line("sat_pk", 0, "sat_ln", 0)
device.add_line("sat_ln", 0, "sat_gain_l", 1)
device.add_line("sat_ln", 0, "sat_gain_r", 1)

# === Tone/damping: tone_dial → pack → line~ → onepole~ freq (signal inlet) ===
device.add_line("tone_dial", 0, "tone_pk", 0)
device.add_line("tone_pk", 0, "tone_ln", 0)
device.add_line("tone_ln", 0, "tone_l", 1)
device.add_line("tone_ln", 0, "tone_r", 1)

# === Feedback amount: fb_dial → scale → trigger fan → pack/line~ per channel ===
device.add_line("fb_dial", 0, "fb_scale", 0)
device.add_line("fb_scale", 0, "fb_trig", 0)
# t f f fires outlet 1 first (R), then outlet 0 (L)
device.add_line("fb_trig", 0, "fb_pk_l", 0)
device.add_line("fb_pk_l", 0, "fb_ln_l", 0)
device.add_line("fb_ln_l", 0, "fb_mul_l", 1)

device.add_line("fb_trig", 1, "fb_pk_r", 0)
device.add_line("fb_pk_r", 0, "fb_ln_r", 0)
device.add_line("fb_ln_r", 0, "fb_mul_r", 1)

# === Mode tab → +1 → selector int inlets ===
device.add_line("mode_tab", 0, "tab_offset", 0)
device.add_line("tab_offset", 0, "sel_fbl", 0)
device.add_line("tab_offset", 0, "sel_fbr", 0)

# === Feedback signal routing into selectors ===
# sel_fbl inlets: 1=Stereo (L fb→L), 2=PingPong (R fb→L), 3=Mono (L fb→L)
device.add_line("fb_mul_l", 0, "sel_fbl", 1)
device.add_line("fb_mul_r", 0, "sel_fbl", 2)   # ping-pong: cross-feed R→L
device.add_line("fb_mul_l", 0, "sel_fbl", 3)

# sel_fbr inlets: 1=Stereo (R fb→R), 2=PingPong (L fb→R), 3=Mono (R fb→R)
device.add_line("fb_mul_r", 0, "sel_fbr", 1)
device.add_line("fb_mul_l", 0, "sel_fbr", 2)   # ping-pong: cross-feed L→R
device.add_line("fb_mul_r", 0, "sel_fbr", 3)

# === Selector feedback → sum_l/r (with dry plugin~ input) ===
device.add_line("sel_fbl", 0, "sum_l", 1)
device.add_line("sel_fbr", 0, "sum_r", 1)

# === plugin~ → sum_l/r inlet 0 (dry input) ===
device.add_line("obj-plugin", 0, "sum_l", 0)
device.add_line("obj-plugin", 1, "sum_r", 0)

# === sum → tapin~ → tapout~ (delay chain) ===
device.add_line("sum_l", 0, "tapin_l", 0)
device.add_line("sum_r", 0, "tapin_r", 0)
device.add_line("tapin_l", 0, "tapout_l", 0)
device.add_line("tapin_r", 0, "tapout_r", 0)

# === tapout~ → sat_gain → tanh~ → onepole~ → fb_mul (feedback path) ===
device.add_line("tapout_l", 0, "sat_gain_l", 0)
device.add_line("tapout_r", 0, "sat_gain_r", 0)
device.add_line("sat_gain_l", 0, "tanh_l", 0)
device.add_line("sat_gain_r", 0, "tanh_r", 0)
device.add_line("tanh_l", 0, "tone_l", 0)
device.add_line("tanh_r", 0, "tone_r", 0)
device.add_line("tone_l", 0, "fb_mul_l", 0)
device.add_line("tone_r", 0, "fb_mul_r", 0)

# === Mix: mix_dial → scale → trigger → smoothed wet_l/r + smoothed dry ===
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# t f f f outlets fire R→L: outlet 2 first, then 1, then 0
device.add_line("mix_trig", 0, "wetl_pk", 0)
device.add_line("wetl_pk", 0, "wetl_ln", 0)
device.add_line("wetl_ln", 0, "wet_l", 1)

device.add_line("mix_trig", 1, "wetr_pk", 0)
device.add_line("wetr_pk", 0, "wetr_ln", 0)
device.add_line("wetr_ln", 0, "wet_r", 1)

device.add_line("mix_trig", 2, "mix_inv", 0)      # outlet 2 → inverter for dry
device.add_line("mix_inv", 0, "dry_pk", 0)
device.add_line("dry_pk", 0, "dry_ln", 0)
device.add_line("dry_ln", 0, "dry_l", 1)
device.add_line("dry_ln", 0, "dry_r", 1)

# === Wet signal: tapout~ → wet multipliers ===
device.add_line("tapout_l", 0, "wet_l", 0)
device.add_line("tapout_r", 0, "wet_r", 0)

# === Dry signal: plugin~ → dry multipliers ===
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# === Sum wet + dry → out ===
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# === Output → plugout~ ===
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# === Output → meters ===
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

# === Tempo sync connections ===

device.add_line("loadbang", 0, "transport", 0)
device.add_line("sync_menu", 0, "sync_menu_trig", 0)

# trig outlet 1 fires first: routes selector; outlet 0 fires second: looks up beat fraction
device.add_line("sync_menu_trig", 1, "sync_gt", 0)
device.add_line("sync_gt", 0, "sync_offset", 0)
device.add_line("sync_offset", 0, "time_sel_l", 0)
device.add_line("sync_offset", 0, "time_sel_r", 0)

device.add_line("sync_menu_trig", 0, "sync_sel", 0)

# sel outlet 0 = Free (no-op); outlets 1-5 = beat fractions 1/1 to 1/16
device.add_line("sync_sel", 1, "beat_4", 0)
device.add_line("sync_sel", 2, "beat_2", 0)
device.add_line("sync_sel", 3, "beat_1", 0)
device.add_line("sync_sel", 4, "beat_05", 0)
device.add_line("sync_sel", 5, "beat_025", 0)

# Beat fraction → store (for recalc when tempo changes later)
device.add_line("beat_4", 0, "beat_store", 1)
device.add_line("beat_2", 0, "beat_store", 1)
device.add_line("beat_1", 0, "beat_store", 1)
device.add_line("beat_05", 0, "beat_store", 1)
device.add_line("beat_025", 0, "beat_store", 1)

# Beat fraction → expr inlet 1, then bang bpm_store to trigger expr computation
device.add_line("beat_4", 0, "sync_expr", 1)
device.add_line("beat_2", 0, "sync_expr", 1)
device.add_line("beat_1", 0, "sync_expr", 1)
device.add_line("beat_05", 0, "sync_expr", 1)
device.add_line("beat_025", 0, "sync_expr", 1)

device.add_line("beat_4", 0, "bpm_store", 0)
device.add_line("beat_2", 0, "bpm_store", 0)
device.add_line("beat_1", 0, "bpm_store", 0)
device.add_line("beat_05", 0, "bpm_store", 0)
device.add_line("beat_025", 0, "bpm_store", 0)

device.add_line("bpm_store", 0, "sync_expr", 0)

# transport outlet 4 = tempo; on tempo change, re-bang beat_store to recalculate
device.add_line("transport", 4, "bpm_store", 1)
device.add_newobj("tempo_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[550, 325, 40, 20])
device.add_line("transport", 4, "tempo_trig", 0)
device.add_line("tempo_trig", 0, "bpm_store", 1)    # outlet 0 fires second: store BPM
device.add_line("tempo_trig", 1, "beat_store", 0)   # outlet 1 fires first: bang stored fraction
device.add_line("beat_store", 0, "sync_expr", 1)

device.add_line("sync_expr", 0, "sync_trig", 0)
# sync_trig outlet 1 fires first (R), outlet 0 fires second (L)
device.add_line("sync_trig", 0, "sync_l_pk", 0)
device.add_line("sync_l_pk", 0, "sync_l_ln", 0)
device.add_line("sync_l_ln", 0, "time_sel_l", 2)  # inlet 2 = synced time

device.add_line("sync_trig", 1, "sync_r_pk", 0)
device.add_line("sync_r_pk", 0, "sync_r_ln", 0)
device.add_line("sync_r_ln", 0, "time_sel_r", 2)  # inlet 2 = synced time

# --- Build ---
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Stereo Delay.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
