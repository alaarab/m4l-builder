"""MIDI velocity curve -- reshape velocity response.

Showcase: velocity_curve DSP block, menu-driven curve selection.
"""
from m4l_builder import MidiEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, noteout, velocity_curve

device = MidiEffect("Velocity Curve", width=180, height=110, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 180, 110])

# Curve selector menu
device.add_menu("curve_sel", "Curve", [10, 10, 80, 20],
                ["Linear", "Compress", "Expand", "Soft", "Hard"])

# Label
device.add_comment("lbl", [100, 10, 70, 16], "Velocity",
                   fontsize=10.0)

# DSP: notein -> velocity_curve (compress by default) -> noteout
ni_boxes, ni_lines = notein("ni")
vc_boxes, vc_lines = velocity_curve("vc", curve="compress")
no_boxes, no_lines = noteout("no")

for b in ni_boxes + vc_boxes + no_boxes:
    device.add_box(b)
for l in ni_lines + vc_lines + no_lines:
    device.lines.append(l)

# Wire: notein velocity -> curve -> noteout velocity
device.add_line("ni_notein", 1, "vc_expr", 0)       # velocity -> expr
device.add_line("vc_clip", 0, "no_noteout", 1)      # curved velocity -> noteout
device.add_line("ni_notein", 0, "no_noteout", 0)     # pitch passthrough
device.add_line("ni_notein", 2, "no_noteout", 2)     # channel passthrough

output = device_output_path("Velocity Curve", device_type="midi_effect", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
