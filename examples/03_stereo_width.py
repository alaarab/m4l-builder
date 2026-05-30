"""Example 3 - a mid/side stereo width audio effect.

Uses the `stereo_width_stage` recipe and wires it between the device's stereo
`plugin~` inputs and `plugout~` outputs. The width dial goes from mono (0) to
unchanged (1) to wide (2).

Run:  python examples/03_stereo_width.py
"""

import os

from m4l_builder import MIDNIGHT, AudioEffect
from m4l_builder.recipes import stereo_width_stage

OUT_DIR = os.path.join(os.path.dirname(__file__), "build")


def build() -> str:
    device = AudioEffect("Widener", width=140, height=150, theme=MIDNIGHT)
    device.add_panel("bg", [0, 0, 140, 150])

    stage = stereo_width_stage(device, "wid", dial_rect=[45, 30, 50, 50])

    # Route the device's stereo I/O through the width stage.
    device.add_line("obj-plugin", 0, stage["in_l"], 0)
    device.add_line("obj-plugin", 1, stage["in_r"], 0)
    device.add_line(stage["left"], 0, "obj-plugout", 0)
    device.add_line(stage["right"], 0, "obj-plugout", 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "Widener.amxd")
    device.build(path)
    return path


if __name__ == "__main__":
    print("wrote", build())
