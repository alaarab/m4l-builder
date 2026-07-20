"""Example 5 - a Euclidean rhythm MIDI sequencer.

Uses the `euclidean_rhythm` block: 4 pulses spread evenly over 16 steps drive a
fixed note (C3) through makenote -> noteout. A toggle starts the clock and a
dial sets the step time. The hit pattern is computed in Python at build time, so
the device is fully self-contained.

Run:  python examples/05_euclidean_midi.py
"""

import os

from m4l_builder import FOREST, MidiEffect, euclidean_rhythm
from m4l_builder.dsp import noteout

OUT_DIR = os.path.join(os.path.dirname(__file__), "build")


def build() -> str:
    device = MidiEffect("Pulse", width=200, height=150, theme=FOREST)
    device.add_panel("bg", [0, 0, 200, 150])
    device.add_toggle("enable", "enable", [20, 24, 22, 22])
    device.add_dial("rate", "rate", [70, 16, 48, 48],
                    min_val=30.0, max_val=500.0, initial=125.0,
                    unitstyle=0, annotation_name="Step ms")

    device.add_dsp(*euclidean_rhythm("euc", steps=16, pulses=4))
    device.add_newobj("note", "t 60", numinlets=1, numoutlets=1, outlettype=[""])
    device.add_newobj("make", "makenote 100 200", numinlets=3, numoutlets=2,
                      outlettype=["", ""])
    device.add_dsp(*noteout("out"))

    device.add_line("enable", 0, "euc_metro", 0)   # toggle starts the clock
    device.add_line("rate", 0, "euc_metro", 1)     # dial sets step time
    device.add_line("euc_hit", 0, "note", 0)       # rhythm bang -> fixed pitch
    device.add_line("note", 0, "make", 0)
    device.add_line("make", 0, "out_noteout", 0)
    device.add_line("make", 1, "out_noteout", 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "Pulse.amxd")
    device.build(path)
    return path


if __name__ == "__main__":
    print("wrote", build())
