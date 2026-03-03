"""Macro Randomizer — 7 randomizable output params with auto/manual trigger."""

import os
from m4l_builder import AudioEffect, COOL

device = AudioEffect("Macro Randomizer", width=330, height=140, theme=COOL)

# Background
device.add_panel("bg", [0, 0, 330, 140])

# Title
device.add_comment("title", [8, 6, 140, 16], "RANDOMIZER",
                   fontname="Ableton Sans Bold", fontsize=13.0)

# Auto toggle — starts/stops continuous randomization
device.add_live_text("auto_toggle", "Auto", [200, 4, 44, 20],
                     text_on="AUTO", text_off="OFF", mode=0,
                     rounded=4.0,
                     bgcolor=[0.09, 0.10, 0.13, 1.0],
                     bgoncolor=[0.35, 0.60, 0.90, 1.0],
                     textcolor=[0.45, 0.50, 0.55, 1.0],
                     textoncolor=[0.06, 0.07, 0.09, 1.0])

# Trigger button — one-shot randomize
device.add_live_text("trig_btn", "Trig", [248, 4, 44, 20],
                     text_on="GO", text_off="TRIG", mode=1,
                     rounded=4.0,
                     bgcolor=[0.12, 0.14, 0.17, 1.0],
                     bgoncolor=[0.35, 0.60, 0.90, 1.0],
                     textcolor=[0.85, 0.88, 0.92, 1.0],
                     textoncolor=[0.06, 0.07, 0.09, 1.0])

# Section labels
device.add_comment("lbl_output", [8, 26, 180, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])
device.add_comment("lbl_speed", [252, 26, 40, 12], "SPEED",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

# 7 output parameter dials — randomized values, mappable in Ableton
for i in range(7):
    x = 8 + i * 34
    device.add_dial(f"p{i+1}_dial", f"P{i+1}", [x, 38, 30, 70],
                    min_val=0.0, max_val=100.0, initial=50.0,
                    annotation_name=f"Parameter {i+1} — randomizable output")

# Rate dial (auto-randomize speed)
device.add_dial("rate_dial", "Rate", [252, 38, 40, 70],
                min_val=0.0, max_val=100.0, initial=25.0,
                annotation_name="Auto-randomize speed — 0 slow, 100 fast")

# Stereo output meters — right edge
device.add_meter("meter_l", [300, 8, 10, 120],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [314, 8, 10, 120],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# --- DSP / Logic ---

# Metro for auto-randomization (default 500ms interval, stopped)
device.add_newobj("metro", "metro 500", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[20, 200, 70, 20])

# Rate scaling: dial 0-100 → 2000ms (slow) to 50ms (fast)
device.add_newobj("rate_scale", "scale 0. 100. 2000. 50.",
                  numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[120, 200, 120, 20])

# Filter trigger button press (1 only, ignore 0 on release)
device.add_newobj("trig_sel", "sel 1", numinlets=2, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[250, 200, 40, 20])

# Fan out bang to 7 random objects
device.add_newobj("fan", "t b b b b b b b", numinlets=1, numoutlets=7,
                  outlettype=["bang", "bang", "bang", "bang",
                              "bang", "bang", "bang"],
                  patching_rect=[20, 240, 200, 20])

# 7 random generators (each outputs 0-100)
for i in range(7):
    device.add_newobj(f"rand_{i+1}", "random 101",
                      numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[20 + i * 50, 280, 65, 20])

# --- Connections ---

# Auto toggle → metro on/off
device.add_line("auto_toggle", 0, "metro", 0)

# Rate dial → scale → metro interval
device.add_line("rate_dial", 0, "rate_scale", 0)
device.add_line("rate_scale", 0, "metro", 1)

# Trigger button → sel 1 → bang (press only)
device.add_line("trig_btn", 0, "trig_sel", 0)

# Metro and trigger both feed the fan
device.add_line("metro", 0, "fan", 0)
device.add_line("trig_sel", 0, "fan", 0)

# Fan outlets → random generators → output dials
for i in range(7):
    device.add_line("fan", i, f"rand_{i+1}", 0)
    device.add_line(f"rand_{i+1}", 0, f"p{i+1}_dial", 0)

# Audio passthrough
device.add_line("obj-plugin", 0, "obj-plugout", 0)
device.add_line("obj-plugin", 1, "obj-plugout", 1)

# Meter connections — tap the passthrough signal from plugin~
device.add_line("obj-plugin", 0, "meter_l", 0)
device.add_line("obj-plugin", 1, "meter_r", 0)

# Build
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/"
    "Max Audio Effect/Macro Randomizer.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
