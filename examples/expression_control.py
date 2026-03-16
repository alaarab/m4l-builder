"""Expression Control — 8 macro knobs that send MIDI CC messages."""

import os
from m4l_builder import MidiEffect, MIDNIGHT, device_output_path

device = MidiEffect("Expression Control", width=320, height=115, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 320, 115])

# Section label
device.add_comment("lbl_macros", [8, 6, 200, 12], "MACRO CONTROLS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# 8 macro dials — each sends a MIDI CC
for i in range(8):
    x = 8 + i * 38
    device.add_dial(f"macro_{i+1}", f"M{i+1}", [x, 18, 34, 72],
                    min_val=0.0, max_val=127.0, initial=64.0,
                    unitstyle=8,
                    annotation_name=f"Macro {i+1} — outputs CC {i+1}")

# CC number labels under each dial
for i in range(8):
    x = 8 + i * 38
    device.add_comment(f"lbl_cc{i+1}", [x, 92, 34, 10], f"CC{i+1}",
                       fontsize=7.5, textcolor=[0.45, 0.75, 0.65, 0.6])

# Each dial -> int (clip to 0-127) -> ctlout (cc number, channel 1)

for i in range(8):
    cc_num = i + 1
    # int converts float to integer for MIDI
    device.add_newobj(f"int_{i+1}", "int", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[20 + i * 50, 200, 30, 20])
    # ctlout: inlet 0 = value, inlet 1 = CC number, inlet 2 = channel
    device.add_newobj(f"ctlout_{i+1}", f"ctlout {cc_num} 1",
                      numinlets=3, numoutlets=0,
                      outlettype=[], patching_rect=[20 + i * 50, 230, 60, 20])

for i in range(8):
    device.add_line(f"macro_{i+1}", 0, f"int_{i+1}", 0)
    device.add_line(f"int_{i+1}", 0, f"ctlout_{i+1}", 0)

# Build
output = device_output_path("Expression Control", device_type="midi_effect", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
