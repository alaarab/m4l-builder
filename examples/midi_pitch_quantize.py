"""MIDI Pitch Quantize — MidiEffect example.

Snaps incoming MIDI pitches to a selected musical scale.
Root note and scale type are configurable.

Signal flow:
  notein -> transpose (root offset) -> scale quantize -> noteout
"""

from m4l_builder import MidiEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, noteout, pitch_quantize

SCALES = ["chromatic", "major", "minor", "pentatonic", "dorian"]

device = MidiEffect("Midi Pitch Quantize", width=280, height=130, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 280, 130])

device.add_comment("title", [8, 5, 120, 16], "PITCH QUANTIZE",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Scale selector menu
device.add_menu("scale_sel", "Scale", [8, 24, 90, 20], SCALES)
device.add_comment("lbl_scale", [8, 46, 90, 12], "SCALE",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Root note dial: 0-11 (C=0, C#=1, ... B=11)
device.add_dial("root_dial", "Root", [108, 24, 50, 70],
                min_val=0.0, max_val=11.0, initial=0.0,
                unitstyle=0, appearance=1,
                annotation_name="Root note (0=C, 1=C#, 2=D, ... 11=B)")
device.add_comment("lbl_root", [108, 96, 50, 12], "ROOT",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# =========================================================================
# DSP objects
# =========================================================================

# Note input
ni_boxes, ni_lines = notein("ni")
for b in ni_boxes:
    device.add_box(b)
for l in ni_lines:
    device.lines.append(l)

# Pitch quantize block (default chromatic; scale_sel drives runtime changes)
pq_boxes, pq_lines = pitch_quantize("pq", scale="chromatic")
for b in pq_boxes:
    device.add_box(b)
for l in pq_lines:
    device.lines.append(l)

# Root offset: subtract root, quantize, add root back
# This shifts the note so that the scale starts on the chosen root
device.add_newobj("sub_root", "- 0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 200, 50, 20])
device.add_newobj("add_root", "+ 0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 200, 50, 20])
device.add_newobj("root_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[200, 180, 45, 20])
device.add_newobj("root_store", "i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 200, 30, 20])
device.add_newobj("root_clip", "clip 0 127", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[150, 230, 70, 20])

# Scale selector: send scale name to pq_scale object via message
device.add_newobj("scale_type_sel", "sel 0 1 2 3 4", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 260, 100, 20])
for i, name in enumerate(SCALES):
    device.add_newobj(f"scale_msg_{i}", f"set {name}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 290, 100, 20])

# Note output
no_boxes, no_lines = noteout("no")
for b in no_boxes:
    device.add_box(b)
for l in no_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# notein pitch -> subtract root -> scale quantize -> add root back -> clip -> noteout
device.add_line("ni_notein", 0, "sub_root", 0)
device.add_line("sub_root", 0, "pq_scale", 0)
device.add_line("pq_scale", 0, "add_root", 0)
device.add_line("add_root", 0, "root_clip", 0)
device.add_line("root_clip", 0, "no_noteout", 0)
device.add_line("ni_notein", 1, "no_noteout", 1)
device.add_line("ni_notein", 2, "no_noteout", 2)

# Root dial -> trigger -> sub_root and add_root right inlets
device.add_line("root_dial", 0, "root_trig", 0)
device.add_line("root_trig", 0, "root_store", 0)
device.add_line("root_store", 0, "add_root", 1)
device.add_line("root_trig", 1, "sub_root", 1)

# Scale menu -> sel -> scale messages -> pq_scale
device.add_line("scale_sel", 0, "scale_type_sel", 0)
for i in range(len(SCALES)):
    device.add_line("scale_type_sel", i, f"scale_msg_{i}", 0)
    device.add_line(f"scale_msg_{i}", 0, "pq_scale", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Midi Pitch Quantize", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
