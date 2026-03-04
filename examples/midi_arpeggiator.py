"""MIDI Arpeggiator — MidiEffect example.

Arpeggiate held notes using the arpeggiate Max object.
Mode, rate, and octave range are controllable.

Signal flow:
  notein -> arpeggiate (with mode/rate) -> makenote -> noteout
"""

from m4l_builder import MidiEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import notein, noteout, arpeggiator

MODES = ["up", "down", "up_down", "random", "as_played"]

WIDTH = 360
HEIGHT = 200

BG = [0.04, 0.04, 0.05, 1.0]
SURFACE = [0.09, 0.09, 0.10, 1.0]

device = MidiEffect("Midi Arpeggiator", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], bgcolor=BG)

# Left panel: mode tab + rate/octave dials
device.add_panel("ctrl_panel", [6, 6, 212, 188], bgcolor=SURFACE, rounded=4)

# Right panel: keyboard display
device.add_panel("keys_panel", [224, 6, 130, 188], bgcolor=SURFACE, rounded=4)

# kslider oriented vertically to show a full octave range
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

# Mode as a tab — the main visual decision point
device.add_tab("mode_sel", "Mode", [14, 14, 196, 28],
               options=["UP", "DOWN", "UD", "RND", "PLAY"],
               shortname="Mode")

# Section labels
device.add_comment("lbl_mode", [14, 44, 196, 10], "MODE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_rate", [14, 152, 96, 10], "RATE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_oct", [116, 152, 96, 10], "OCTAVES",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_keys", [228, 174, 122, 10], "KEYBOARD",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)

# Rate dial
device.add_dial("rate_dial", "Rate", [14, 58, 96, 90],
                min_val=50.0, max_val=2000.0, initial=200.0,
                unitstyle=2, parameter_exponent=2.0, appearance=1,
                annotation_name="Arpeggiator step rate in milliseconds")

# Octave range dial
device.add_dial("oct_dial", "Octaves", [116, 58, 96, 90],
                min_val=1.0, max_val=4.0, initial=1.0,
                unitstyle=0, appearance=1,
                annotation_name="Arpeggiator octave range")

# =========================================================================
# DSP objects
# =========================================================================

ni_boxes, ni_lines = notein("ni")
for b in ni_boxes:
    device.add_box(b)
for l in ni_lines:
    device.lines.append(l)

arp_boxes, arp_lines = arpeggiator("ar", mode="up")
for b in arp_boxes:
    device.add_box(b)
for l in arp_lines:
    device.lines.append(l)

# Mode tab -> sel -> mode messages -> arpeggiate
device.add_newobj("mode_sel_obj", "sel 0 1 2 3 4", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 180, 100, 20])

mode_names = ["up", "down", "up_down", "random", "as_played"]
for i, m in enumerate(mode_names):
    device.add_newobj(f"mode_msg_{i}", f"prepend mode {m}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[30 + i * 100, 210, 100, 20])

device.add_newobj("oct_int", "i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 180, 30, 20])
device.add_newobj("oct_prep", "prepend octaves", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 210, 100, 20])

no_boxes, no_lines = noteout("no")
for b in no_boxes:
    device.add_box(b)
for l in no_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

device.add_line("ni_notein", 0, "ar_arp", 0)
device.add_line("ni_notein", 1, "ar_arp", 0)

device.add_line("rate_dial", 0, "ar_arp", 1)

device.add_line("mode_sel", 0, "mode_sel_obj", 0)
for i in range(len(mode_names)):
    device.add_line("mode_sel_obj", i, f"mode_msg_{i}", 0)
    device.add_line(f"mode_msg_{i}", 0, "ar_arp", 0)

device.add_line("oct_dial", 0, "oct_int", 0)
device.add_line("oct_int", 0, "oct_prep", 0)
device.add_line("oct_prep", 0, "ar_arp", 0)

device.add_line("ar_make", 0, "no_noteout", 0)
device.add_line("ar_make", 1, "no_noteout", 1)
device.add_line("ni_notein", 2, "no_noteout", 2)

# Active note -> kslider display
device.add_line("ar_make", 0, "kslider", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Midi Arpeggiator", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
