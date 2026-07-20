"""Example 1 - a gain audio effect, built from scratch.

Shows the low-level building blocks: a panel, a dial, raw Max objects
(`add_newobj`) and wiring (`add_line`). `AudioEffect` auto-adds the stereo
`plugin~` / `plugout~` objects (IDs `obj-plugin` / `obj-plugout`).

For real use, write straight into your Ableton User Library with
`device_output_path("My Gain")`. This script writes to a local ./build/ folder
so it runs anywhere.

Run:  python examples/01_gain_audio_effect.py
"""

import os

from m4l_builder import WARM, AudioEffect

OUT_DIR = os.path.join(os.path.dirname(__file__), "build")


def build() -> str:
    device = AudioEffect("My Gain", width=150, height=110, theme=WARM)

    device.add_panel("bg", [0, 0, 150, 110])
    device.add_dial("gain", "Gain", [10, 6, 50, 90],
                    min_val=-70.0, max_val=6.0, initial=0.0,
                    unitstyle=4, annotation_name="Gain")

    device.add_newobj("mul_l", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("mul_r", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1, outlettype=[""])
    device.add_newobj("pk", "pack f 20", numinlets=2, numoutlets=1, outlettype=[""])
    device.add_newobj("ln", "line~", numinlets=2, numoutlets=2, outlettype=["signal", "bang"])

    device.add_line("obj-plugin", 0, "mul_l", 0)   # stereo in
    device.add_line("obj-plugin", 1, "mul_r", 0)
    device.add_line("mul_l", 0, "obj-plugout", 0)   # stereo out
    device.add_line("mul_r", 0, "obj-plugout", 1)
    device.add_line("gain", 0, "db2a", 0)           # dial -> dbtoa -> smooth -> gain
    device.add_line("db2a", 0, "pk", 0)
    device.add_line("pk", 0, "ln", 0)
    device.add_line("ln", 0, "mul_l", 1)
    device.add_line("ln", 0, "mul_r", 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "My Gain.amxd")
    device.build(path)
    return path


if __name__ == "__main__":
    print("wrote", build())
