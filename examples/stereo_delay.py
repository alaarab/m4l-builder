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
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT

# --- Device setup ---
device = AudioEffect("Stereo Delay", width=320, height=150, theme=MIDNIGHT)

# --- UI ---
device.add_panel("bg", [0, 0, 320, 150], bgcolor=[0.12, 0.12, 0.14, 1.0])

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

# --- DSP: Delay buffers ---
# tapin~ 5000: 5-second max delay buffer, 1in/1out
device.add_newobj("tapin_l", "tapin~ 5000", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[30, 220, 80, 20])
device.add_newobj("tapin_r", "tapin~ 5000", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[200, 220, 80, 20])

# tapout~ initial_delay_ms: outlet 0 is delayed signal; inlet 0 from tapin~ outlet, inlet 1 float for delay time
device.add_newobj("tapout_l", "tapout~ 375", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 260, 80, 20])
device.add_newobj("tapout_r", "tapout~ 500", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 260, 80, 20])

# --- DSP: Feedback path (tanh~ → onepole~ → *~ feedback) ---
# Saturation input gain: *~ 1. (sat_dial scales this). Inlet 0=signal, inlet 1=gain float.
device.add_newobj("sat_gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 300, 40, 20])
device.add_newobj("sat_gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 300, 40, 20])

# tanh~ for saturation (smooth limiting)
device.add_newobj("tanh_l", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 330, 40, 20])
device.add_newobj("tanh_r", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 330, 40, 20])

# onepole~ for tone/damping (lowpass). Inlet 0=signal, inlet 1=freq float.
device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 360, 50, 20])
device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 360, 50, 20])

# Feedback amount multiplier. Inlet 0=signal, inlet 1=feedback float (0.0-0.95).
device.add_newobj("fb_mul_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 390, 40, 20])
device.add_newobj("fb_mul_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 390, 40, 20])

# --- DSP: Mode selector for feedback routing ---
# Modes: 1=Stereo (L fb→L, R fb→R), 2=PingPong (L fb→R, R fb→L), 3=Mono (sum to center)
# selector~ 3 1: 3 signal inputs, initial=1 (Stereo)
# selector L feedback routing: inlet 1=L fb (stereo), inlet 2=R fb (ping-pong), inlet 3=L fb (mono)
device.add_newobj("sel_fbl", "selector~ 3 1", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 430, 80, 20])
# selector R feedback routing: inlet 1=R fb (stereo), inlet 2=L fb (ping-pong), inlet 3=R fb (mono)
device.add_newobj("sel_fbr", "selector~ 3 1", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 430, 80, 20])

# +1 offset: live.tab 0-indexed → selector~ 1-indexed
device.add_newobj("tab_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 200, 40, 20])

# --- DSP: Input summing (dry input + feedback return) ---
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 470, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 470, 30, 20])

# --- DSP: Saturation gain scaling ---
# sat_dial 0-100 → scale to 1.0-4.0 (unity to 4x drive into tanh)
device.add_newobj("sat_scale", "scale 0. 100. 1. 4.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 300, 120, 20])

# --- DSP: Feedback scaling ---
# fb_dial 0-95 → scale to 0.0-0.95
device.add_newobj("fb_scale", "scale 0. 95. 0. 0.95", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 390, 120, 20])

# trigger to fan feedback float to both channels
device.add_newobj("fb_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[100, 410, 40, 20])

# --- DSP: Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 80, 120, 20])

# trigger fan: t f f f → wet_l, wet_r, inverter (fires R to L)
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 100, 55, 20])

# !-~ 1. computes (1.0 - mix) for dry gain
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 130, 45, 20])

# Wet gain multipliers
device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 500, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 500, 30, 20])

# Dry gain multipliers
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 500, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 500, 30, 20])

# Output sum: wet + dry
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 540, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 540, 30, 20])

# --- Connections ---

# === Delay time: dials → tapout~ delay float ===
device.add_line("ltime_dial", 0, "tapout_l", 1)   # L time dial → tapout_l delay
device.add_line("rtime_dial", 0, "tapout_r", 1)   # R time dial → tapout_r delay

# === Saturation gain: sat_dial → scale → sat_gain_l/r inlet 1 ===
device.add_line("sat_dial", 0, "sat_scale", 0)
device.add_line("sat_scale", 0, "sat_gain_l", 1)
device.add_line("sat_scale", 0, "sat_gain_r", 1)

# === Tone/damping: tone_dial → onepole~ freq ===
device.add_line("tone_dial", 0, "tone_l", 1)
device.add_line("tone_dial", 0, "tone_r", 1)

# === Feedback amount: fb_dial → scale → trigger fan → fb_mul_l/r inlet 1 ===
device.add_line("fb_dial", 0, "fb_scale", 0)
device.add_line("fb_scale", 0, "fb_trig", 0)
# t f f fires outlet 1 first (R), then outlet 0 (L)
device.add_line("fb_trig", 0, "fb_mul_l", 1)
device.add_line("fb_trig", 1, "fb_mul_r", 1)

# === Mode tab → +1 → selector int inlets ===
device.add_line("mode_tab", 0, "tab_offset", 0)
device.add_line("tab_offset", 0, "sel_fbl", 0)
device.add_line("tab_offset", 0, "sel_fbr", 0)

# === Feedback signal routing into selectors ===
# sel_fbl: inlet 1=L fb (stereo), inlet 2=R fb (ping-pong), inlet 3=L fb (mono)
device.add_line("fb_mul_l", 0, "sel_fbl", 1)   # stereo: L fb → L input
device.add_line("fb_mul_r", 0, "sel_fbl", 2)   # ping-pong: R fb → L input
device.add_line("fb_mul_l", 0, "sel_fbl", 3)   # mono: L fb → L input

# sel_fbr: inlet 1=R fb (stereo), inlet 2=L fb (ping-pong), inlet 3=R fb (mono)
device.add_line("fb_mul_r", 0, "sel_fbr", 1)   # stereo: R fb → R input
device.add_line("fb_mul_l", 0, "sel_fbr", 2)   # ping-pong: L fb → R input
device.add_line("fb_mul_r", 0, "sel_fbr", 3)   # mono: R fb → R input

# === Selector feedback → sum_l/r (with dry plugin~ input) ===
device.add_line("sel_fbl", 0, "sum_l", 1)      # feedback → sum_l inlet 1
device.add_line("sel_fbr", 0, "sum_r", 1)      # feedback → sum_r inlet 1

# === plugin~ → sum_l/r inlet 0 (dry input) ===
device.add_line("obj-plugin", 0, "sum_l", 0)
device.add_line("obj-plugin", 1, "sum_r", 0)

# === sum → tapin~ → tapout~ (delay chain) ===
device.add_line("sum_l", 0, "tapin_l", 0)
device.add_line("sum_r", 0, "tapin_r", 0)
device.add_line("tapin_l", 0, "tapout_l", 0)   # tapin~ outlet → tapout~ inlet 0
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
# fb_mul → sel_fbl/fbr (already connected above)

# === Mix: mix_dial → scale → trigger → wet_l/r + dry inverter ===
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# t f f f outlets fire R→L: outlet 2 first, then 1, then 0
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

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

# --- Build ---
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Stereo Delay.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
