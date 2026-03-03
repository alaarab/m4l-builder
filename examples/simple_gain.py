"""Simple gain effect -- minimal m4l_builder example.

Showcase: WARM theme, compact vertical dial, minimal Swiss-style layout.
"""

import os
from m4l_builder import AudioEffect, WARM

device = AudioEffect("Simple Gain", width=150, height=110, theme=WARM)

# Background
device.add_panel("bg", [0, 0, 150, 110])

# Title
device.add_comment("title", [6, 5, 50, 14], "GAIN",
                    fontname="Ableton Sans Bold", fontsize=12.0)

# Gain dial — normal vertical appearance
device.add_dial("gain", "Gain", [10, 22, 50, 75],
                min_val=0.0, max_val=100.0, initial=50.0,
                appearance=0,
                annotation_name="Output Gain")

# Stereo output meters
device.add_meter("meter_l", [110, 8, 10, 90],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [124, 8, 10, 90],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# DSP: plugin~ -> *~ gain -> plugout~
gain_l = device.add_newobj("gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                           outlettype=["signal"], patching_rect=[30, 100, 40, 20])
gain_r = device.add_newobj("gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                           outlettype=["signal"], patching_rect=[150, 100, 40, 20])
scale = device.add_newobj("scale", "scale 0. 100. 0. 2.", numinlets=6, numoutlets=1,
                          outlettype=[""], patching_rect=[200, 80, 100, 20])

# Connections
device.add_line("obj-plugin", 0, "gain_l", 0)
device.add_line("obj-plugin", 1, "gain_r", 0)
device.add_line("gain_l", 0, "obj-plugout", 0)
device.add_line("gain_r", 0, "obj-plugout", 1)
device.add_line("gain", 0, "scale", 0)
device.add_line("scale", 0, "gain_l", 1)
device.add_line("scale", 0, "gain_r", 1)

# Meter connections — tap output signal
device.add_line("gain_l", 0, "meter_l", 0)
device.add_line("gain_r", 0, "meter_r", 0)

output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Simple Gain.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
