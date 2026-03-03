"""Expression Control — 8 macro knobs for parameter mapping in Ableton."""

import os
from m4l_builder import AudioEffect, MIDNIGHT

device = AudioEffect("Expression Control", width=320, height=115, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 320, 115])

# Title
device.add_comment("title", [8, 6, 160, 16], "EXPRESSION",
                   fontname="Ableton Sans Bold", fontsize=13.0)

# Section label
device.add_comment("lbl_macros", [8, 24, 200, 12], "MACRO CONTROLS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# 8 macro dials in a row — each is a mappable Live parameter
for i in range(8):
    x = 8 + i * 38
    device.add_dial(f"macro_{i+1}", f"M{i+1}", [x, 34, 34, 72],
                    min_val=0.0, max_val=100.0, initial=50.0,
                    annotation_name=f"Macro {i+1} — map to any parameter")

# Audio passthrough (control device, no processing)
device.add_line("obj-plugin", 0, "obj-plugout", 0)
device.add_line("obj-plugin", 1, "obj-plugout", 1)

# Build
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/"
    "Max Audio Effect/Expression Control.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
