"""Tape Degradation Engine — m4l_builder example.

Showcase: WARM theme with custom overrides, rounded tabs, scope with styled
trace, Module Rack feel.

Signal flow:
  plugin~ L/R -> *~ drive -> tapin~ 50 (50ms buffer)
  Wow LFO:     cycle~ 0.5  -> *~ wow_depth   -> +~ base_delay
  Flutter LFO: cycle~ 10.  -> *~ flutter_depth -> +~ (added to wow sum)
  Sum delay -> tapout~ 5 (modulated delay time)
  tapout~ -> tanh~ (saturation) -> onepole~ tone (head rolloff)
  Hiss: noise~ -> svf~ BP @ 6kHz -> *~ hiss_level -> +~ main signal
  Dry/wet mix -> plugout~

Parameter smoothing:
  All float→signal paths go through pack→line~ to eliminate zipper noise.
  line~ ramps over 20ms for gain/mix params, giving artifact-free modulation.
"""

import os
from m4l_builder import AudioEffect, WARM, device_output_path

# --- Device setup ---
# Widen by 30px for L/R output meters on right edge
device = AudioEffect("Tape Degradation", width=330, height=185, theme=WARM)

# --- UI ---
device.add_panel("bg", [0, 0, 330, 185])

# Section panel
device.add_panel("section_bg", [4, 24, 322, 157],
                 bgcolor=WARM.section, rounded=4)

device.add_comment("title", [8, 5, 60, 12], "TAPE",
                   fontname="Ableton Sans Bold", fontsize=10.0,
                   textcolor=WARM.text_dim)

# Wow/Flutter LFO modulation scope
device.add_scope("lfo_scope", [8, 26, 284, 40],
                 bgcolor=[0.06, 0.06, 0.06, 1.0],
                 activelinecolor=[0.85, 0.55, 0.25, 1.0],
                 gridcolor=[0.15, 0.13, 0.10, 0.4],
                 range_vals=[-4.0, 4.0],
                 calccount=128, smooth=2, line_width=1.5)

# Dial row — 6 dials spread across the first 300px, meters on the right
DIAL_Y = 72
DIAL_W = 44
DIAL_H = 75

device.add_dial("wow_dial", "Wow", [5, DIAL_Y, DIAL_W, DIAL_H],
                min_val=0.0, max_val=100.0, initial=30.0,
                unitstyle=5, annotation_name="Wow Depth")

device.add_dial("flutter_dial", "Flutter", [53, DIAL_Y, DIAL_W, DIAL_H],
                min_val=0.0, max_val=100.0, initial=20.0,
                unitstyle=5, annotation_name="Flutter Depth")

device.add_dial("drive_dial", "Drive", [101, DIAL_Y, DIAL_W, DIAL_H],
                min_val=0.0, max_val=100.0, initial=30.0,
                unitstyle=5, annotation_name="Tape Drive")

device.add_dial("tone_dial", "Tone", [149, DIAL_Y, DIAL_W, DIAL_H],
                min_val=1000.0, max_val=20000.0, initial=12000.0,
                unitstyle=3, parameter_exponent=2.0,
                annotation_name="Head Rolloff")

device.add_dial("hiss_dial", "Hiss", [197, DIAL_Y, DIAL_W, DIAL_H],
                min_val=0.0, max_val=100.0, initial=10.0,
                unitstyle=5, annotation_name="Tape Hiss Level")

device.add_dial("mix_dial", "Mix", [245, DIAL_Y, DIAL_W, DIAL_H],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, annotation_name="Dry/Wet Mix")

# Output meters — L and R on right edge, vertical
METER_COLORS = dict(
    coldcolor=WARM.accent,
    warmcolor=[0.9, 0.8, 0.2, 1.0],
    hotcolor=[0.9, 0.4, 0.1, 1.0],
    overloadcolor=[0.9, 0.15, 0.15, 1.0],
)
device.add_meter("meter_l", [296, 26, 14, 155], orientation=0, **METER_COLORS)
device.add_meter("meter_r", [312, 26, 14, 155], orientation=0, **METER_COLORS)

# --- DSP objects ---

# === Input drive ===
# One shared scale feeds both channels — 0-100% maps to 1x-3x into tanh~
device.add_newobj("drive_scale", "scale 0. 100. 1. 3.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 200, 120, 20])

# Smoothing for drive (scale -> pack -> line~ -> both channels)
device.add_newobj("drive_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 200, 60, 20])
device.add_newobj("drive_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[160, 230, 40, 20])

# drive_r_pk/ln are aliases that reuse the same smoothed signal via fan from drive_l_ln
device.add_newobj("drive_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[230, 200, 60, 20])
device.add_newobj("drive_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[230, 230, 40, 20])

device.add_newobj("gain_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 260, 30, 20])
device.add_newobj("gain_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 260, 30, 20])

# === Tape delay line ===
device.add_newobj("tapin_l", "tapin~ 50", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 290, 60, 20])
device.add_newobj("tapin_r", "tapin~ 50", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 290, 60, 20])

device.add_newobj("tapout_l", "tapout~ 5", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 330, 60, 20])
device.add_newobj("tapout_r", "tapout~ 5", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 330, 60, 20])

# === Wow/Flutter LFOs ===
device.add_newobj("wow_lfo", "cycle~ 0.5", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[200, 200, 60, 20])

device.add_newobj("flutter_lfo", "cycle~ 10.", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[280, 200, 60, 20])

device.add_newobj("wow_depth_scale", "scale 0. 100. 0. 3.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 225, 120, 20])

device.add_newobj("flutter_depth_scale", "scale 0. 100. 0. 0.5", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[340, 225, 130, 20])

# Smoothing for wow depth (scale -> pack -> line~)
device.add_newobj("wow_d_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 250, 60, 20])
device.add_newobj("wow_d_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 280, 40, 20])

# Smoothing for flutter depth (scale -> pack -> line~)
device.add_newobj("flutter_d_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[340, 250, 60, 20])
device.add_newobj("flutter_d_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[340, 280, 40, 20])

device.add_newobj("wow_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 310, 30, 20])
device.add_newobj("flutter_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 310, 30, 20])

device.add_newobj("lfo_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 340, 30, 20])

device.add_newobj("delay_base", "+~ 5.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 365, 45, 20])

# === Tape saturation ===
device.add_newobj("sat_l", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 370, 40, 20])
device.add_newobj("sat_r", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 370, 40, 20])

# === Tape head tone rolloff ===
device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 400, 50, 20])
device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 400, 50, 20])

# Smoothing for tone cutoff (dial -> pack -> line~ -> onepole~ both channels)
device.add_newobj("tone_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 390, 60, 20])
device.add_newobj("tone_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 420, 40, 20])

# === Hiss generation ===
device.add_newobj("hiss_noise", "noise~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 200, 40, 20])

device.add_newobj("hiss_svf", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[380, 225, 40, 20])

device.add_newobj("hiss_scale", "scale 0. 100. 0. 0.04", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[380, 255, 130, 20])

# Smoothing for hiss level (scale -> pack -> line~)
device.add_newobj("hiss_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[380, 280, 60, 20])
device.add_newobj("hiss_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[380, 310, 40, 20])

device.add_newobj("hiss_gain", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 340, 30, 20])

device.add_newobj("hiss_add_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 430, 30, 20])
device.add_newobj("hiss_add_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 430, 30, 20])

# === Dry/Wet mix ===
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 200, 120, 20])

# Smoothing for mix (scale -> pack -> line~ -> t f f f fan)
device.add_newobj("mix_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 225, 60, 20])
device.add_newobj("mix_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[460, 255, 40, 20])

device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 290, 50, 20])

device.add_newobj("wet_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 330, 30, 20])
device.add_newobj("wet_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 330, 30, 20])
device.add_newobj("dry_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[540, 330, 30, 20])
device.add_newobj("dry_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[580, 330, 30, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 370, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 370, 30, 20])

# --- Connections ---

# Drive: dial -> single scale -> fan to both L and R pack+line~ chains
device.add_line("drive_dial", 0, "drive_scale", 0)
device.add_line("drive_scale", 0, "drive_l_pk", 0)
device.add_line("drive_l_pk", 0, "drive_l_ln", 0)
device.add_line("drive_l_ln", 0, "gain_l", 1)   # smoothed drive -> gain_l
device.add_line("drive_scale", 0, "drive_r_pk", 0)
device.add_line("drive_r_pk", 0, "drive_r_ln", 0)
device.add_line("drive_r_ln", 0, "gain_r", 1)   # smoothed drive -> gain_r

device.add_line("obj-plugin", 0, "gain_l", 0)
device.add_line("obj-plugin", 1, "gain_r", 0)

device.add_line("gain_l", 0, "tapin_l", 0)
device.add_line("gain_r", 0, "tapin_r", 0)

device.add_line("tapin_l", 0, "tapout_l", 0)
device.add_line("tapin_r", 0, "tapout_r", 0)

# Wow depth: dial -> scale -> pack -> line~ -> *~ inlet 1
device.add_line("wow_dial", 0, "wow_depth_scale", 0)
device.add_line("wow_depth_scale", 0, "wow_d_pk", 0)
device.add_line("wow_d_pk", 0, "wow_d_ln", 0)
device.add_line("wow_d_ln", 0, "wow_mul", 1)    # smoothed wow depth -> wow_mul

# Flutter depth: dial -> scale -> pack -> line~ -> *~ inlet 1
device.add_line("flutter_dial", 0, "flutter_depth_scale", 0)
device.add_line("flutter_depth_scale", 0, "flutter_d_pk", 0)
device.add_line("flutter_d_pk", 0, "flutter_d_ln", 0)
device.add_line("flutter_d_ln", 0, "flutter_mul", 1)  # smoothed flutter depth

device.add_line("wow_lfo", 0, "wow_mul", 0)
device.add_line("flutter_lfo", 0, "flutter_mul", 0)

device.add_line("wow_mul", 0, "lfo_sum", 0)
device.add_line("flutter_mul", 0, "lfo_sum", 1)

device.add_line("lfo_sum", 0, "delay_base", 0)

device.add_line("delay_base", 0, "tapout_l", 0)
device.add_line("delay_base", 0, "tapout_r", 0)

device.add_line("tapout_l", 0, "sat_l", 0)
device.add_line("tapout_r", 0, "sat_r", 0)

device.add_line("sat_l", 0, "tone_l", 0)
device.add_line("sat_r", 0, "tone_r", 0)

# Tone: dial -> pack -> line~ -> onepole~ inlet 1 (both L and R)
device.add_line("tone_dial", 0, "tone_pk", 0)
device.add_line("tone_pk", 0, "tone_ln", 0)
device.add_line("tone_ln", 0, "tone_l", 1)      # smoothed cutoff -> tone_l
device.add_line("tone_ln", 0, "tone_r", 1)      # smoothed cutoff -> tone_r

# Hiss: dial -> scale -> pack -> line~ -> *~ inlet 1
device.add_line("hiss_noise", 0, "hiss_svf", 0)
device.add_line("hiss_svf", 2, "hiss_gain", 0)
device.add_line("hiss_dial", 0, "hiss_scale", 0)
device.add_line("hiss_scale", 0, "hiss_pk", 0)
device.add_line("hiss_pk", 0, "hiss_ln", 0)
device.add_line("hiss_ln", 0, "hiss_gain", 1)   # smoothed hiss level -> hiss_gain

device.add_line("tone_l", 0, "hiss_add_l", 0)
device.add_line("tone_r", 0, "hiss_add_r", 0)
device.add_line("hiss_gain", 0, "hiss_add_l", 1)
device.add_line("hiss_gain", 0, "hiss_add_r", 1)

# Mix: dial -> scale -> pack -> line~ -> wet/dry multipliers
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_pk", 0)
device.add_line("mix_pk", 0, "mix_ln", 0)
# mix_ln outlet 0 (signal) fans to wet_l, wet_r, and mix_inv
device.add_line("mix_ln", 0, "wet_l", 1)
device.add_line("mix_ln", 0, "wet_r", 1)
device.add_line("mix_ln", 0, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

device.add_line("hiss_add_l", 0, "wet_l", 0)
device.add_line("hiss_add_r", 0, "wet_r", 0)

device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# LFO scope: show wow+flutter modulation signal
device.add_line("lfo_sum", 0, "lfo_scope", 0)

# Output meters: tap the final output signals
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

# --- Build ---
output = device_output_path("Tape Degradation")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
