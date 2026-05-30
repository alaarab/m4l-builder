"""Example 2 - a generative MIDI device.

Uses the `generative_midi_stage` recipe: an enable toggle plus rate/density
dials drive a probabilistic, scale-quantized random-note generator. Showcases
the MidiEffect device type and the generative building blocks
(`probability_gate`, `random_note`).

Run:  python examples/02_generative_midi.py
"""

import os

from m4l_builder import COOL, MidiEffect
from m4l_builder.recipes import generative_midi_stage

OUT_DIR = os.path.join(os.path.dirname(__file__), "build")


def build() -> str:
    device = MidiEffect("Sparkle", width=200, height=140, theme=COOL)
    device.add_panel("bg", [0, 0, 200, 140])

    generative_midi_stage(
        device, "gen",
        rate_rect=[24, 40, 56, 56],
        density_rect=[110, 40, 56, 56],
        low=48, high=72, scale="minor",
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "Sparkle.amxd")
    device.build(path)
    return path


if __name__ == "__main__":
    print("wrote", build())
