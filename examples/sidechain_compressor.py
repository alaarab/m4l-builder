"""Sidechain compressor -- use a sidechain signal to trigger compression.

Showcase: sidechain_detect + compressor DSP blocks, stereo processing.
"""
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import sidechain_detect, compressor, gain_stage

device = AudioEffect("Sidechain Comp", width=250, height=130, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 250, 130])

# Controls
device.add_dial("thresh", "Threshold", [10, 10, 50, 90],
                min_val=-60.0, max_val=0.0, initial=-20.0, unitstyle=4)
device.add_dial("amount", "Amount", [70, 10, 50, 90],
                min_val=0.0, max_val=100.0, initial=50.0, unitstyle=5)
device.add_dial("mix", "Mix", [130, 10, 50, 90],
                min_val=0.0, max_val=100.0, initial=100.0, unitstyle=5)

# Meters
device.add_meter("meter_l", [200, 10, 10, 90])
device.add_meter("meter_r", [214, 10, 10, 90])

# DSP: sidechain detection on left channel input
sc_boxes, sc_lines = sidechain_detect("sc")
comp_boxes, comp_lines = compressor("comp")

for b in sc_boxes + comp_boxes:
    device.add_box(b)
for l in sc_lines + comp_lines:
    device.lines.append(l)

# Wire plugin -> compressor detection + output multiplier inputs
# Compressor needs audio at abs (for detection) AND at out (for gain application)
device.add_line("obj-plugin", 0, "comp_abs_l", 0)
device.add_line("obj-plugin", 0, "comp_out_l", 0)
device.add_line("obj-plugin", 1, "comp_abs_r", 0)
device.add_line("obj-plugin", 1, "comp_out_r", 0)

# Compressor output -> plugout
device.add_line("comp_out_l", 0, "obj-plugout", 0)
device.add_line("comp_out_r", 0, "obj-plugout", 1)

# Meters
device.add_line("comp_out_l", 0, "meter_l", 0)
device.add_line("comp_out_r", 0, "meter_r", 0)

output = device_output_path("Sidechain Comp")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
