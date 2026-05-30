"""Example 6 - a simple subtractive-ish synth instrument.

Covers the Instrument device type (which leaves audio I/O to you): MIDI notes
drive an oscillator through an ADSR amplitude envelope to `plugout~`.

    notein -> mtof -> cycle~ -.
    notein (velocity) -> adsr~ -> *~ <- cycle~
                                  *~ -> plugout~ (L/R)

Run:  python examples/06_simple_synth.py
"""

import os

from m4l_builder import SYNTHWAVE, Instrument

OUT_DIR = os.path.join(os.path.dirname(__file__), "build")


def build() -> str:
    device = Instrument("Simple Synth", width=220, height=150, theme=SYNTHWAVE)
    device.add_panel("bg", [0, 0, 220, 150])

    device.add_newobj("notein", "notein", numinlets=1, numoutlets=3, outlettype=["", "", ""])
    device.add_newobj("mtof", "mtof", numinlets=1, numoutlets=1, outlettype=[""])
    device.add_newobj("osc", "cycle~", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("env", "adsr~ 10 80 0.6 300", numinlets=5, numoutlets=1,
                      outlettype=["signal"])
    device.add_newobj("amp", "*~", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("out", "plugout~", numinlets=2, numoutlets=0)

    device.add_line("notein", 0, "mtof", 0)   # pitch -> mtof -> osc frequency
    device.add_line("mtof", 0, "osc", 0)
    device.add_line("notein", 1, "env", 0)     # velocity gates the envelope
    device.add_line("osc", 0, "amp", 0)        # osc * envelope
    device.add_line("env", 0, "amp", 1)
    device.add_line("amp", 0, "out", 0)        # to both output channels
    device.add_line("amp", 0, "out", 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "Simple Synth.amxd")
    device.build(path)
    return path


if __name__ == "__main__":
    print("wrote", build())
