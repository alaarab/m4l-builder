"""Production Chain -- recipe cookbook example.

A channel strip that chains four recipe stages into one usable device:
  1. Input gain (gain_controlled_stage)
  2. Sidechain compressor (sidechain_compressor_recipe)
  3. LFO modulation matrix (lfo_matrix_distribute) with 3 targets
  4. Dry/wet output (dry_wet_stage)

Uses the MIDNIGHT theme throughout. Each section is labeled with a comment
so the device reads like a signal flow diagram in Live.
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.recipes import (
    gain_controlled_stage,
    sidechain_compressor_recipe,
    lfo_matrix_distribute,
    dry_wet_stage,
)

device = AudioEffect("Production Chain", width=480, height=200, theme=MIDNIGHT)

# -- Background + section labels --
device.add_panel("bg", [0, 0, 480, 200])
device.add_comment("lbl_input", [10, 4, 80, 16], "INPUT",
                   fontsize=9, textcolor=[0.5, 0.5, 0.55, 1.0])
device.add_comment("lbl_comp", [120, 4, 100, 16], "SIDECHAIN",
                   fontsize=9, textcolor=[0.5, 0.5, 0.55, 1.0])
device.add_comment("lbl_lfo", [260, 4, 80, 16], "LFO MOD",
                   fontsize=9, textcolor=[0.5, 0.5, 0.55, 1.0])
device.add_comment("lbl_out", [420, 4, 60, 16], "OUTPUT",
                   fontsize=9, textcolor=[0.5, 0.5, 0.55, 1.0])

# -- 1. Input gain stage --
input_stage = gain_controlled_stage(
    device, "in", dial_rect=[20, 28, 50, 80], x=30, y=30,
)

# Mirror gain control to R channel
gain_r = device.add_newobj(
    "in_gain_r", "*~ 1.", numinlets=2, numoutlets=1,
    outlettype=["signal"], patching_rect=[200, 120, 40, 20],
)
device.add_line("obj-plugin", 0, input_stage["gain"], 0)
device.add_line("obj-plugin", 1, "in_gain_r", 0)
device.add_line("in_smooth_line", 0, "in_gain_r", 1)

# -- 2. Sidechain compressor --
comp = sidechain_compressor_recipe(
    device, "sc",
    threshold_rect=[120, 28, 50, 80],
    ratio_rect=[180, 28, 50, 80],
    x=400, y=30,
)

# Feed gained signal into compressor detection + output
device.add_line(input_stage["gain"], 0, "sc_comp_abs_l", 0)
device.add_line(input_stage["gain"], 0, "sc_comp_out_l", 0)
device.add_line("in_gain_r", 0, "sc_comp_abs_r", 0)
device.add_line("in_gain_r", 0, "sc_comp_out_r", 0)

# -- 3. LFO modulation matrix (3 depth dials) --
lfo_mod = lfo_matrix_distribute(
    device, "mod", targets=3, x=270, y=28,
)

# Label each depth target
device.add_comment("lbl_d0", [272, 72, 40, 14], "Gain",
                   fontsize=8, textcolor=[0.4, 0.4, 0.45, 1.0])
device.add_comment("lbl_d1", [322, 72, 40, 14], "Thresh",
                   fontsize=8, textcolor=[0.4, 0.4, 0.45, 1.0])
device.add_comment("lbl_d2", [372, 72, 40, 14], "Ratio",
                   fontsize=8, textcolor=[0.4, 0.4, 0.45, 1.0])

# -- 4. Dry/wet output --
mix = dry_wet_stage(
    device, "out", dial_rect=[430, 28, 40, 80], x=800, y=30,
)

# Compressor L output -> wet, original input -> dry
device.add_line("sc_comp_out_l", 0, mix["wet_gain"], 0)
device.add_line(input_stage["gain"], 0, mix["dry_gain"], 0)

# Sum wet + dry -> output
out_sum = device.add_newobj(
    "out_sum", "+~", numinlets=2, numoutlets=1,
    outlettype=["signal"], patching_rect=[800, 150, 30, 20],
)
device.add_line(mix["wet_gain"], 0, "out_sum", 0)
device.add_line(mix["dry_gain"], 0, "out_sum", 1)

# Output meter
device.add_meter("meter_l", [456, 28, 10, 80],
                 coldcolor=[0.30, 0.55, 0.45, 1.0],
                 warmcolor=[0.45, 0.75, 0.65, 1.0],
                 hotcolor=[0.80, 0.60, 0.20, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Mono sum to plugout (recipe demo, not full stereo chain)
device.add_line("out_sum", 0, "obj-plugout", 0)
device.add_line("out_sum", 0, "obj-plugout", 1)
device.add_line("out_sum", 0, "meter_l", 0)

# -- Section dividers --
device.add_panel("div1", [110, 8, 1, 184],
                 bgcolor=[0.2, 0.2, 0.22, 0.5])
device.add_panel("div2", [250, 8, 1, 184],
                 bgcolor=[0.2, 0.2, 0.22, 0.5])
device.add_panel("div3", [410, 8, 1, 184],
                 bgcolor=[0.2, 0.2, 0.22, 0.5])

# -- Build --
output = device_output_path("Production Chain")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
