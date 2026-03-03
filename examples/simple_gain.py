"""Simple gain effect -- minimal m4l_builder example.

Showcase: WARM theme, compact vertical dial, minimal Swiss-style layout.
Gain in dB: -70 dB to +6 dB, 0 dB = unity. Uses dbtoa for conversion.
"""

import os
from m4l_builder import AudioEffect, WARM, device_output_path

device = AudioEffect("Simple Gain", width=150, height=110, theme=WARM)

# Background
device.add_panel("bg", [0, 0, 150, 110], bgcolor=WARM.bg)

# Gain dial in dB: -70 to +6, default 0 dB (unity)
device.add_dial("gain", "Gain", [10, 6, 50, 90],
                min_val=-70.0, max_val=6.0, initial=0.0,
                unitstyle=4, appearance=0,
                annotation_name="Output Gain")

# Stereo output meters — warm orange tones matching WARM theme accent
device.add_meter("meter_l", [80, 8, 10, 90],
                 coldcolor=[0.55, 0.40, 0.20, 1.0],
                 warmcolor=[0.85, 0.55, 0.25, 1.0],
                 hotcolor=[0.90, 0.35, 0.10, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [94, 8, 10, 90],
                 coldcolor=[0.55, 0.40, 0.20, 1.0],
                 warmcolor=[0.85, 0.55, 0.25, 1.0],
                 hotcolor=[0.90, 0.35, 0.10, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# DSP: plugin~ -> *~ gain -> plugout~
gain_l = device.add_newobj("gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                           outlettype=["signal"], patching_rect=[30, 100, 40, 20])
gain_r = device.add_newobj("gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                           outlettype=["signal"], patching_rect=[150, 100, 40, 20])
# dbtoa converts dB to linear amplitude (0 dB -> 1.0, -6 dB -> 0.5, +6 dB -> 2.0)
device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 80, 50, 20])

# Parameter smoothing: dbtoa -> pack -> line~ -> *~ (shared, fans to both channels)
device.add_newobj("gain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 110, 60, 20])
device.add_newobj("gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 140, 40, 20])

# Connections
device.add_line("obj-plugin", 0, "gain_l", 0)
device.add_line("obj-plugin", 1, "gain_r", 0)
device.add_line("gain_l", 0, "obj-plugout", 0)
device.add_line("gain_r", 0, "obj-plugout", 1)

# Gain routing: dial -> dbtoa -> pack -> line~ -> both *~
device.add_line("gain", 0, "db2a", 0)
device.add_line("db2a", 0, "gain_pk", 0)
device.add_line("gain_pk", 0, "gain_ln", 0)
device.add_line("gain_ln", 0, "gain_l", 1)
device.add_line("gain_ln", 0, "gain_r", 1)

# Meter connections — tap output signal
device.add_line("gain_l", 0, "meter_l", 0)
device.add_line("gain_r", 0, "meter_r", 0)

output = device_output_path("Simple Gain")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
