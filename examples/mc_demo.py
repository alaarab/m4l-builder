"""MC multichannel demo -- expand, gain, mix back to stereo.

Stereo input from plugin~ gets expanded to 4 MC channels via mc.pack~.
mc.gain~ controls per-channel level, then mc.mix~ sums back to stereo
for plugout~.
"""

from m4l_builder import AudioEffect, COOL, device_output_path
from m4l_builder.dsp import mc_expand, mc_gain_stage, mc_mixer, mc_collapse

device = AudioEffect("MC Demo", width=300, height=120, theme=COOL)

# Background
device.add_panel("bg", [0, 0, 300, 120], bgcolor=COOL.bg)
device.add_comment("title", [10, 6, 280, 20], text="MC Demo",
                   fontsize=14, textcolor=COOL.text)

# Gain dial for the MC gain stage
device.add_dial("gain_knob", "MC Gain", [20, 30, 50, 80],
                min_val=-70.0, max_val=6.0, initial=0.0, unitstyle=4)

# DSP blocks
expand_boxes, expand_lines = mc_expand("exp", channels=4)
device.add_dsp(expand_boxes, expand_lines)

gain_boxes, gain_lines = mc_gain_stage("lvl", channels=4)
device.add_dsp(gain_boxes, gain_lines)

mix_boxes, mix_lines = mc_mixer("sum", inputs=1, channels=2)
device.add_dsp(mix_boxes, mix_lines)

collapse_boxes, collapse_lines = mc_collapse("col", channels=4)
device.add_dsp(collapse_boxes, collapse_lines)

# dbtoa for gain dial conversion
device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 40, 50, 20])
device.add_newobj("gain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 70, 60, 20])
device.add_newobj("gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 100, 40, 20])

# Wiring: plugin~ stereo -> mc.pack~ (expand to 4 channels)
device.add_line("obj-plugin", 0, "exp_pack", 0)
device.add_line("obj-plugin", 1, "exp_pack", 1)

# mc.pack~ -> mc.gain~ -> mc.unpack~ (collapse back)
device.add_line("exp_pack", 0, "lvl_mcgain", 0)
device.add_line("lvl_mcgain", 0, "col_unpack", 0)

# mc_collapse routes even channels to L, odd to R
device.add_line("col_sum_l", 0, "obj-plugout", 0)
device.add_line("col_sum_r", 0, "obj-plugout", 1)

# Gain dial -> dbtoa -> pack -> line~ -> mc.gain~ inlet 1
device.add_line("gain_knob", 0, "db2a", 0)
device.add_line("db2a", 0, "gain_pk", 0)
device.add_line("gain_pk", 0, "gain_ln", 0)
device.add_line("gain_ln", 0, "lvl_mcgain", 1)

output = device_output_path("MC Demo", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
