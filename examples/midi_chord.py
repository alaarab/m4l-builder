"""MIDI Chord generator — MidiEffect example.

Adds chord intervals to each incoming note. Chord type and
transpose amount are selectable.

Signal flow:
  notein -> transpose -> chord intervals -> noteout (one per interval)
"""

from m4l_builder import MidiEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, noteout, chord, transpose

CHORD_TYPES = {
    "major":  [4, 7],
    "minor":  [3, 7],
    "dim":    [3, 6],
    "aug":    [4, 8],
    "sus2":   [2, 7],
    "sus4":   [5, 7],
}
CHORD_NAMES = list(CHORD_TYPES.keys())
# Build a flat intervals list for each chord type (2 intervals = 2 extra notes)
# We'll use the major intervals as the default block and switch via sel + messages

device = MidiEffect("Midi Chord", width=260, height=130, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 260, 130])

device.add_comment("title", [8, 5, 100, 16], "CHORD",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Chord type menu
device.add_menu("chord_sel", "Chord Type", [8, 24, 90, 20], CHORD_NAMES)

# Section labels
device.add_comment("lbl_chord", [8, 46, 90, 12], "CHORD TYPE",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_trans", [108, 96, 60, 12], "TRANSPOSE",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Transpose dial: -12 to +12 semitones
device.add_dial("trans_dial", "Transpose", [108, 24, 50, 70],
                min_val=-12.0, max_val=12.0, initial=0.0,
                unitstyle=7, appearance=1,
                annotation_name="Transpose all notes by semitones")

# =========================================================================
# DSP objects
# =========================================================================

# Note input
ni_boxes, ni_lines = notein("ni")
for b in ni_boxes:
    device.add_box(b)
for l in ni_lines:
    device.lines.append(l)

# Transpose block
tp_boxes, tp_lines = transpose("tp", semitones=0)
for b in tp_boxes:
    device.add_box(b)
for l in tp_lines:
    device.lines.append(l)

# Chord block (default major: [4, 7])
# We create two interval adders and control their values via messages
device.add_newobj("chord_int1", "+ 4", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 200, 50, 20])
device.add_newobj("chord_int2", "+ 7", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[260, 200, 50, 20])

# Clip chord notes to 0-127
device.add_newobj("clip_int1", "clip 0 127", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 230, 70, 20])
device.add_newobj("clip_int2", "clip 0 127", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[260, 230, 70, 20])

# Chord type selector: sends interval values to the + objects
device.add_newobj("chord_type_sel", "sel 0 1 2 3 4 5", numinlets=1, numoutlets=7,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 280, 110, 20])

# For each chord type, message boxes that set interval values
for i, name in enumerate(CHORD_NAMES):
    ivs = CHORD_TYPES[name]
    device.add_newobj(f"ct_msg_{i}_1", f"i {ivs[0]}", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 310, 60, 20])
    device.add_newobj(f"ct_msg_{i}_2", f"i {ivs[1]}", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 340, 60, 20])

# Note outputs (root + 2 chord tones)
no_boxes, no_lines = noteout("no")
no2_boxes, no2_lines = noteout("no2")
no3_boxes, no3_lines = noteout("no3")
for b in no_boxes + no2_boxes + no3_boxes:
    device.add_box(b)
for l in no_lines + no2_lines + no3_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# Transpose dial controls transpose
device.add_line("trans_dial", 0, "tp_add", 1)

# notein -> transpose -> root noteout
device.add_line("ni_notein", 0, "tp_add", 0)
device.add_line("tp_clip", 0, "no_noteout", 0)
device.add_line("ni_notein", 1, "no_noteout", 1)
device.add_line("ni_notein", 2, "no_noteout", 2)

# Transposed root -> chord intervals
device.add_line("tp_clip", 0, "chord_int1", 0)
device.add_line("tp_clip", 0, "chord_int2", 0)

# Clip and send to noteout2/3
device.add_line("chord_int1", 0, "clip_int1", 0)
device.add_line("chord_int2", 0, "clip_int2", 0)
device.add_line("clip_int1", 0, "no2_noteout", 0)
device.add_line("ni_notein", 1, "no2_noteout", 1)
device.add_line("ni_notein", 2, "no2_noteout", 2)
device.add_line("clip_int2", 0, "no3_noteout", 0)
device.add_line("ni_notein", 1, "no3_noteout", 1)
device.add_line("ni_notein", 2, "no3_noteout", 2)

# Chord type menu -> sel -> interval messages
device.add_line("chord_sel", 0, "chord_type_sel", 0)
for i in range(len(CHORD_NAMES)):
    device.add_line("chord_type_sel", i, f"ct_msg_{i}_1", 0)
    device.add_line("chord_type_sel", i, f"ct_msg_{i}_2", 0)
    device.add_line(f"ct_msg_{i}_1", 0, "chord_int1", 1)
    device.add_line(f"ct_msg_{i}_2", 0, "chord_int2", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Midi Chord", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
