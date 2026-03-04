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

WIDTH = 360
HEIGHT = 200

BG = [0.04, 0.04, 0.05, 1.0]
SURFACE = [0.09, 0.09, 0.10, 1.0]

device = MidiEffect("Midi Chord", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], bgcolor=BG)

# Controls panel — left side
device.add_panel("ctrl_panel", [6, 6, 212, 188], bgcolor=SURFACE, rounded=4)

# Keyboard panel — right side
device.add_panel("keys_panel", [224, 6, 130, 188], bgcolor=SURFACE, rounded=4)

# kslider shows chord voicing
device.add_box({
    "box": {
        "id": "kslider",
        "maxclass": "kslider",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["int", "int"],
        "patching_rect": [700, 0, 50, 180],
        "presentation": 1,
        "presentation_rect": [228, 10, 122, 178],
        "parameter_enable": 0,
    }
})

# Chord type as a tab — the focal point
device.add_tab("chord_sel", "Chord Type", [14, 14, 196, 28],
               options=["MAJ", "MIN", "DIM", "AUG", "SUS2", "SUS4"],
               shortname="Chord")

device.add_comment("lbl_chord", [14, 44, 196, 10], "CHORD TYPE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_trans", [14, 154, 196, 10], "TRANSPOSE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_keys", [228, 174, 122, 10], "KEYBOARD",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)

# Transpose dial — large, takes remaining height
device.add_dial("trans_dial", "Transpose", [14, 56, 196, 96],
                min_val=-12.0, max_val=12.0, initial=0.0,
                unitstyle=7, appearance=1,
                annotation_name="Transpose all notes by semitones")

# =========================================================================
# DSP objects
# =========================================================================

ni_boxes, ni_lines = notein("ni")
for b in ni_boxes:
    device.add_box(b)
for l in ni_lines:
    device.lines.append(l)

tp_boxes, tp_lines = transpose("tp", semitones=0)
for b in tp_boxes:
    device.add_box(b)
for l in tp_lines:
    device.lines.append(l)

device.add_newobj("chord_int1", "+ 4", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 200, 50, 20])
device.add_newobj("chord_int2", "+ 7", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[260, 200, 50, 20])

device.add_newobj("clip_int1", "clip 0 127", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 230, 70, 20])
device.add_newobj("clip_int2", "clip 0 127", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[260, 230, 70, 20])

device.add_newobj("chord_type_sel", "sel 0 1 2 3 4 5", numinlets=1, numoutlets=7,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 280, 110, 20])

for i, name in enumerate(CHORD_NAMES):
    ivs = CHORD_TYPES[name]
    device.add_newobj(f"ct_msg_{i}_1", f"i {ivs[0]}", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 310, 60, 20])
    device.add_newobj(f"ct_msg_{i}_2", f"i {ivs[1]}", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 340, 60, 20])

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

device.add_line("trans_dial", 0, "tp_add", 1)

device.add_line("ni_notein", 0, "tp_add", 0)
device.add_line("tp_clip", 0, "no_noteout", 0)
device.add_line("ni_notein", 1, "no_noteout", 1)
device.add_line("ni_notein", 2, "no_noteout", 2)

device.add_line("tp_clip", 0, "chord_int1", 0)
device.add_line("tp_clip", 0, "chord_int2", 0)

device.add_line("chord_int1", 0, "clip_int1", 0)
device.add_line("chord_int2", 0, "clip_int2", 0)
device.add_line("clip_int1", 0, "no2_noteout", 0)
device.add_line("ni_notein", 1, "no2_noteout", 1)
device.add_line("ni_notein", 2, "no2_noteout", 2)
device.add_line("clip_int2", 0, "no3_noteout", 0)
device.add_line("ni_notein", 1, "no3_noteout", 1)
device.add_line("ni_notein", 2, "no3_noteout", 2)

device.add_line("chord_sel", 0, "chord_type_sel", 0)
for i in range(len(CHORD_NAMES)):
    device.add_line("chord_type_sel", i, f"ct_msg_{i}_1", 0)
    device.add_line("chord_type_sel", i, f"ct_msg_{i}_2", 0)
    device.add_line(f"ct_msg_{i}_1", 0, "chord_int1", 1)
    device.add_line(f"ct_msg_{i}_2", 0, "chord_int2", 1)

# Feed chord notes to kslider
device.add_line("tp_clip", 0, "kslider", 0)
device.add_line("clip_int1", 0, "kslider", 0)
device.add_line("clip_int2", 0, "kslider", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Midi Chord", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
