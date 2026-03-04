"""MIDI transpose effect -- shift notes up or down by semitones.

Showcase: MidiEffect device type, MIDI DSP blocks, simple MIDI processing chain.
"""
from m4l_builder import MidiEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, noteout, transpose

device = MidiEffect("MIDI Transpose", width=160, height=110, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 160, 110])

# Transpose dial: -24 to +24 semitones
device.add_dial("amt", "Semitones", [10, 6, 50, 90],
                min_val=-24, max_val=24, initial=0,
                unitstyle=7)  # semitone display

# Status label
device.add_comment("lbl", [80, 45, 70, 16], "Transpose",
                   fontsize=10.0)

# DSP: notein -> transpose -> noteout
ni_boxes, ni_lines = notein("ni")
tp_boxes, tp_lines = transpose("tp")
no_boxes, no_lines = noteout("no")

for b in ni_boxes + tp_boxes + no_boxes:
    device.add_box(b)
for l in ni_lines + tp_lines + no_lines:
    device.lines.append(l)

# Wire: notein pitch -> transpose -> noteout pitch
device.add_line("ni_notein", 0, "tp_add", 0)      # pitch -> transpose
device.add_line("tp_clip", 0, "no_noteout", 0)      # transposed pitch -> noteout
device.add_line("ni_notein", 1, "no_noteout", 1)    # velocity passthrough
device.add_line("ni_notein", 2, "no_noteout", 2)    # channel passthrough

# Dial controls transpose amount
device.add_line("amt", 0, "tp_add", 1)  # dial -> + right inlet

output = device_output_path("MIDI Transpose", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
