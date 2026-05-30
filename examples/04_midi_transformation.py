"""Example 4 - a Live 12 MIDI Transformation (a MIDI Tool).

The minimal valid MIDI Tool: notes from `live.miditool.in` pass straight to
`live.miditool.out`. To actually transform a clip, replace the direct
connection with your own note processing between `mt_in` (outlet 0 = notes
dictionary, outlet 1 = context: grid/selection/scale/root) and `mt_out`
(inlet 0).

MIDI Tools load from Ableton's User Library under
`MIDI Tools/Max Transformations/`. Use `MidiGenerator` (loads under
`Max Generators/`) the same way to add new notes instead of rewriting them.

Run:  python examples/04_midi_transformation.py
"""

import os

from m4l_builder import MIDNIGHT, MidiTransformation, midi_tool_io

OUT_DIR = os.path.join(os.path.dirname(__file__), "build")


def build() -> str:
    device = MidiTransformation("Passthrough", width=200, height=120, theme=MIDNIGHT)
    device.add_panel("bg", [0, 0, 200, 120])

    device.add_dsp(*midi_tool_io("mt"))
    device.add_line("mt_in", 0, "mt_out", 0)  # notes dict -> out (pass-through)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "Passthrough.amxd")
    device.build(path)
    return path


if __name__ == "__main__":
    print("wrote", build())
