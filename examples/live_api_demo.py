"""Live API Demo — watch and control Live set tempo.

Demonstrates: live_observer, live_set_control, number_box display,
button trigger, stereo_io passthrough.

Signal flow:
  plugin~ → plugout~ (passthrough)
  live.observer (tempo) → number_box display
  button → message "120" → live_set_control (tempo)
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.live_api import live_observer, live_set_control

WIDTH = 300
HEIGHT = 150
device = AudioEffect("Live API Demo", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)


device.add_comment("lbl_tempo", [8, 26, 80, 12], "CURRENT TEMPO",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_number_box("tempo_display", "Tempo", [8, 38, 80, 22],
                      min_val=60.0, max_val=200.0, initial=120.0,
                      unitstyle=3, shortname="BPM")

device.add_comment("lbl_btn", [100, 26, 100, 12], "SET TEMPO TO 120",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_button("tempo_btn", "Set 120", [100, 38, 80, 22])

# =========================================================================
# DSP
# =========================================================================

# Live observer: watches live_set tempo
obs_boxes, obs_lines = live_observer("obs", path="live_set", prop="tempo")
for b in obs_boxes:
    device.add_box(b)
for l in obs_lines:
    device.lines.append(l)

# Live set control: sets tempo
ctl_boxes, ctl_lines = live_set_control("ctl", path="live_set", prop="tempo")
for b in ctl_boxes:
    device.add_box(b)
for l in ctl_lines:
    device.lines.append(l)

# Message object holding value 120 for the button
device.add_newobj("tempo_120_msg", "f 120.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 200, 40, 20])

# =========================================================================
# Connections
# =========================================================================

# Observer output → tempo display number box
device.add_line("obs_observer", 0, "tempo_display", 0)

# Button → bang → f 120 → live.object set tempo
device.add_line("tempo_btn", 0, "tempo_120_msg", 0)
device.add_line("tempo_120_msg", 0, "ctl_obj", 0)

# Passthrough: plugin~ → plugout~ (direct audio pass)
device.add_line("obj-plugin", 0, "obj-plugout", 0)
device.add_line("obj-plugin", 1, "obj-plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Live API Demo")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
