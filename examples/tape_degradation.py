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
"""

import os
from m4l_builder import AudioEffect, WARM

# --- Device setup ---
device = AudioEffect("Tape Degradation", width=300, height=185, theme=WARM)

# --- UI ---
device.add_panel("bg", [0, 0, 300, 185])

# Section panel
device.add_panel("section_bg", [4, 24, 292, 157],
                 bgcolor=WARM.section, rounded=4)

device.add_comment("title", [8, 5, 60, 16], "TAPE",
                   fontname="Ableton Sans Bold", fontsize=13.0,
                   textcolor=[0.95, 0.88, 0.72, 1.0])

# Wow/Flutter LFO modulation scope
device.add_scope("lfo_scope", [8, 26, 284, 40],
                 bgcolor=[0.06, 0.06, 0.06, 1.0],
                 activelinecolor=[0.85, 0.55, 0.25, 1.0],
                 gridcolor=[0.15, 0.13, 0.10, 0.4],
                 range_vals=[-4.0, 4.0],
                 calccount=128, smooth=2, line_width=1.5)

# Dial row — 6 dials spread across 300px
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

device.add_dial("mix_dial", "Mix", [248, DIAL_Y, DIAL_W, DIAL_H],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, annotation_name="Dry/Wet Mix")

# --- DSP objects ---

# === Input drive ===
device.add_newobj("drive_scale_l", "scale 0. 100. 1. 5.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 200, 120, 20])
device.add_newobj("drive_scale_r", "scale 0. 100. 1. 5.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 225, 120, 20])

device.add_newobj("gain_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 250, 30, 20])
device.add_newobj("gain_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 250, 30, 20])

# === Tape delay line ===
device.add_newobj("tapin_l", "tapin~ 50", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 280, 60, 20])
device.add_newobj("tapin_r", "tapin~ 50", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[100, 280, 60, 20])

device.add_newobj("tapout_l", "tapout~ 5", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 320, 60, 20])
device.add_newobj("tapout_r", "tapout~ 5", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 320, 60, 20])

# === Wow/Flutter LFOs ===
device.add_newobj("wow_lfo", "cycle~ 0.5", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[200, 200, 60, 20])

device.add_newobj("flutter_lfo", "cycle~ 10.", numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"], patching_rect=[280, 200, 60, 20])

device.add_newobj("wow_depth_scale", "scale 0. 100. 0. 3.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 225, 120, 20])

device.add_newobj("flutter_depth_scale", "scale 0. 100. 0. 0.5", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[340, 225, 130, 20])

device.add_newobj("wow_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 255, 30, 20])
device.add_newobj("flutter_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 255, 30, 20])

device.add_newobj("lfo_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 285, 30, 20])

device.add_newobj("delay_base", "+~ 5.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 310, 45, 20])

# === Tape saturation ===
device.add_newobj("sat_l", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 360, 40, 20])
device.add_newobj("sat_r", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 360, 40, 20])

# === Tape head tone rolloff ===
device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 390, 50, 20])
device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 390, 50, 20])

# === Hiss generation ===
device.add_newobj("hiss_noise", "noise~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 200, 40, 20])

device.add_newobj("hiss_svf", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[380, 225, 40, 20])

device.add_newobj("hiss_scale", "scale 0. 100. 0. 0.04", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[380, 255, 130, 20])

device.add_newobj("hiss_gain", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 280, 30, 20])

device.add_newobj("hiss_add_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 420, 30, 20])
device.add_newobj("hiss_add_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 420, 30, 20])

# === Dry/Wet mix ===
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 200, 120, 20])

device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[460, 225, 55, 20])

device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 255, 50, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 290, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 290, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[540, 290, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[580, 290, 30, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 330, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 330, 30, 20])

# --- Connections ---

device.add_line("drive_dial", 0, "drive_scale_l", 0)
device.add_line("drive_dial", 0, "drive_scale_r", 0)
device.add_line("drive_scale_l", 0, "gain_l", 1)
device.add_line("drive_scale_r", 0, "gain_r", 1)

device.add_line("obj-plugin", 0, "gain_l", 0)
device.add_line("obj-plugin", 1, "gain_r", 0)

device.add_line("gain_l", 0, "tapin_l", 0)
device.add_line("gain_r", 0, "tapin_r", 0)

device.add_line("tapin_l", 0, "tapout_l", 0)
device.add_line("tapin_r", 0, "tapout_r", 0)

device.add_line("wow_dial", 0, "wow_depth_scale", 0)
device.add_line("flutter_dial", 0, "flutter_depth_scale", 0)

device.add_line("wow_lfo", 0, "wow_mul", 0)
device.add_line("flutter_lfo", 0, "flutter_mul", 0)

device.add_line("wow_depth_scale", 0, "wow_mul", 1)
device.add_line("flutter_depth_scale", 0, "flutter_mul", 1)

device.add_line("wow_mul", 0, "lfo_sum", 0)
device.add_line("flutter_mul", 0, "lfo_sum", 1)

device.add_line("lfo_sum", 0, "delay_base", 0)

device.add_line("delay_base", 0, "tapout_l", 0)
device.add_line("delay_base", 0, "tapout_r", 0)

device.add_line("tapout_l", 0, "sat_l", 0)
device.add_line("tapout_r", 0, "sat_r", 0)

device.add_line("sat_l", 0, "tone_l", 0)
device.add_line("sat_r", 0, "tone_r", 0)

device.add_line("tone_dial", 0, "tone_l", 1)
device.add_line("tone_dial", 0, "tone_r", 1)

device.add_line("hiss_noise", 0, "hiss_svf", 0)
device.add_line("hiss_svf", 2, "hiss_gain", 0)
device.add_line("hiss_scale", 0, "hiss_gain", 1)
device.add_line("hiss_dial", 0, "hiss_scale", 0)

device.add_line("tone_l", 0, "hiss_add_l", 0)
device.add_line("tone_r", 0, "hiss_add_r", 0)
device.add_line("hiss_gain", 0, "hiss_add_l", 1)
device.add_line("hiss_gain", 0, "hiss_add_r", 1)

device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
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

# --- Build ---
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Tape Degradation.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
