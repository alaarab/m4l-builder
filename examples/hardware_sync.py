"""Hardware Sync — AudioEffect example.

Demonstrates: midi_clock_out (send clock to external gear),
midi_clock_in (detect incoming clock + display BPM), sync mode toggle,
stereo audio passthrough.

Signal flow:
  plugin~ → plugout~  (audio unchanged)
  Internal: transport → metro → midiout (24 ppqn)
  External: midiin → midiparse → clock detect → BPM calc → number_box
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import midi_clock_out, midi_clock_in

WIDTH = 340
HEIGHT = 160
device = AudioEffect("Hardware Sync", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

device.add_comment("title", [8, 5, 120, 16], "HARDWARE SYNC",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Sync mode toggle: 0 = internal (send), 1 = external (receive)
device.add_comment("lbl_mode", [8, 26, 80, 12], "SYNC MODE",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_tab("mode_tab", "Sync Mode", [8, 38, 160, 20],
               options=["INTERNAL", "EXTERNAL"],
               rounded=3.0, spacing_x=2.0,
               bgcolor=[0.25, 0.25, 0.27, 1.0],
               bgoncolor=[0.20, 0.65, 0.45, 1.0],
               textcolor=[0.55, 0.55, 0.57, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# BPM display for external clock
device.add_comment("lbl_bpm", [185, 26, 60, 12], "EXT BPM",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_number_box("bpm_display", "BPM", [185, 38, 80, 20],
                      min_val=20.0, max_val=300.0, initial=120.0,
                      unitstyle=0, shortname="BPM")

# Status labels
device.add_comment("lbl_out", [8, 72, 160, 12], "SEND: 24ppqn clock out",
                   fontsize=8.0, textcolor=[0.40, 0.60, 0.40, 0.7])
device.add_comment("lbl_in", [8, 86, 200, 12], "RECV: counts clock pulses, shows BPM",
                   fontsize=8.0, textcolor=[0.40, 0.60, 0.40, 0.7])

# Output meters (passthrough signal)
device.add_meter("meter_l", [WIDTH - 30, 22, 10, HEIGHT - 32],
                 coldcolor=[0.3, 0.65, 0.35, 1.0],
                 warmcolor=[0.9, 0.75, 0.15, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [WIDTH - 16, 22, 10, HEIGHT - 32],
                 coldcolor=[0.3, 0.65, 0.35, 1.0],
                 warmcolor=[0.9, 0.75, 0.15, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# =========================================================================
# DSP — clock out and clock in blocks
# =========================================================================

clkout_boxes, clkout_lines = midi_clock_out("clkout")
for b in clkout_boxes:
    device.add_box(b)
for l in clkout_lines:
    device.lines.append(l)

clkin_boxes, clkin_lines = midi_clock_in("clkin")
for b in clkin_boxes:
    device.add_box(b)
for l in clkin_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# Audio passthrough: plugin~ → plugout~ (sync doesn't touch audio)
device.add_line("obj-plugin", 0, "obj-plugout", 0)
device.add_line("obj-plugin", 1, "obj-plugout", 1)

# Meters tap from plugin~ directly
device.add_line("obj-plugin", 0, "meter_l", 0)
device.add_line("obj-plugin", 1, "meter_r", 0)

# BPM display from external clock detector
device.add_line("clkin_bpm_scale", 0, "bpm_display", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Hardware Sync")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
