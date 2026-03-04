"""MIDI Arpeggiator — MidiEffect example.

Arpeggiate held notes using the arpeggiate Max object.
Mode, rate, and octave range are controllable.

Signal flow:
  notein -> arpeggiate (with mode/rate) -> makenote -> noteout
"""

from m4l_builder import MidiEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, noteout, arpeggiator

MODES = ["up", "down", "up_down", "random", "as_played"]

device = MidiEffect("Midi Arpeggiator", width=260, height=130, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 260, 130])

device.add_comment("title", [8, 5, 120, 16], "ARPEGGIATOR",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Mode selector
device.add_menu("mode_sel", "Mode", [8, 24, 90, 20], MODES)

# Rate dial: 50-2000ms per step
device.add_dial("rate_dial", "Rate", [108, 24, 50, 70],
                min_val=50.0, max_val=2000.0, initial=200.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Arpeggiator step rate in milliseconds")

# Octave range dial: 1-4
device.add_dial("oct_dial", "Octaves", [168, 24, 50, 70],
                min_val=1.0, max_val=4.0, initial=1.0,
                unitstyle=0, appearance=1,
                annotation_name="Arpeggiator octave range")

# Section labels
device.add_comment("lbl_mode", [8, 46, 90, 12], "MODE",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_rate", [108, 96, 50, 12], "RATE",
                   fontsize=8.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_oct", [168, 96, 50, 12], "OCTAVES",
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

# Arpeggiator (default mode; mode_sel will switch at runtime)
arp_boxes, arp_lines = arpeggiator("ar", mode="up")
for b in arp_boxes:
    device.add_box(b)
for l in arp_lines:
    device.lines.append(l)

# Mode selector uses sel to switch between modes
# arpeggiate accepts a "mode <name>" message
device.add_newobj("mode_sel_obj", "sel 0 1 2 3 4", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 180, 100, 20])
for i, m in enumerate(MODES):
    device.add_newobj(f"mode_msg_{i}", f"prepend mode {m}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 210, 100, 20])

# Octave range: scales arpeggiate object's octave count
device.add_newobj("oct_int", "i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 180, 30, 20])
device.add_newobj("oct_prep", "prepend octaves", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 210, 100, 20])

# Note output
no_boxes, no_lines = noteout("no")
for b in no_boxes:
    device.add_box(b)
for l in no_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# notein -> arpeggiate
device.add_line("ni_notein", 0, "ar_arp", 0)     # pitch
device.add_line("ni_notein", 1, "ar_arp", 0)     # velocity (also to inlet 0 for note-off)

# Rate dial -> arpeggiate rate inlet
device.add_line("rate_dial", 0, "ar_arp", 1)

# Mode selector -> sel -> mode message -> arpeggiate
device.add_line("mode_sel", 0, "mode_sel_obj", 0)
for i in range(len(MODES)):
    device.add_line("mode_sel_obj", i, f"mode_msg_{i}", 0)
    device.add_line(f"mode_msg_{i}", 0, "ar_arp", 0)

# Octave dial -> int -> prepend -> arpeggiate
device.add_line("oct_dial", 0, "oct_int", 0)
device.add_line("oct_int", 0, "oct_prep", 0)
device.add_line("oct_prep", 0, "ar_arp", 0)

# makenote -> noteout
device.add_line("ar_make", 0, "no_noteout", 0)   # pitch
device.add_line("ar_make", 1, "no_noteout", 1)   # velocity
device.add_line("ni_notein", 2, "no_noteout", 2) # channel passthrough

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Midi Arpeggiator", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
