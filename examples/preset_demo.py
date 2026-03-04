"""Preset Demo — save and recall parameter states.

Demonstrates: preset_manager, add_preset_buttons, lowpass_filter,
gain_stage, dry_wet_mix.

Signal flow:
  plugin~ → lowpass_filter → *~ (gain) → dry_wet_mix → plugout~
  preset_manager controls recall/store of filter and gain parameters.
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import lowpass_filter, dry_wet_mix
from m4l_builder.presets import preset_manager, add_preset_buttons

WIDTH = 320
HEIGHT = 180
device = AudioEffect("Preset Demo", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

device.add_comment("title", [8, 5, 90, 16], "PRESET DEMO",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

device.add_comment("lbl_filter", [8, 22, 60, 12], "FILTER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("cutoff_dial", "Cutoff", [8, 32, 50, 65],
                min_val=20.0, max_val=20000.0, initial=1000.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1,
                annotation_name="Lowpass filter cutoff")

device.add_dial("res_dial", "Res", [68, 32, 50, 65],
                min_val=0.0, max_val=100.0, initial=20.0,
                unitstyle=5, appearance=1,
                annotation_name="Filter resonance")

device.add_comment("lbl_gain", [130, 22, 50, 12], "GAIN",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_dial("gain_dial", "Gain", [130, 32, 50, 65],
                min_val=-24.0, max_val=6.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Output gain in dB")

device.add_comment("lbl_mix", [190, 22, 50, 12], "MIX",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_dial("mix_dial", "Mix", [190, 32, 50, 65],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/wet mix")

device.add_comment("lbl_presets", [8, 106, 80, 12], "PRESETS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Preset buttons + manager (save/load/prev/next at bottom)
add_preset_buttons(device, x=8, y=118, num_presets=8)

# =========================================================================
# DSP
# =========================================================================

# Lowpass filter
lp_boxes, lp_lines = lowpass_filter("lp")
for b in lp_boxes:
    device.add_box(b)
for l in lp_lines:
    device.lines.append(l)

# Output gain stage: dB dial → linear
device.add_newobj("gain_expr", "expr pow(10., $f1 / 20.)", numinlets=1,
                  numoutlets=1, outlettype=[""],
                  patching_rect=[400, 80, 160, 20])
device.add_newobj("gain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 110, 60, 20])
device.add_newobj("gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 140, 40, 20])
device.add_newobj("out_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 170, 40, 20])
device.add_newobj("out_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 170, 40, 20])

# Cutoff smoothing
device.add_newobj("cut_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 200, 60, 20])
device.add_newobj("cut_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 230, 40, 20])
device.add_newobj("res_scale", "scale 0. 100. 0. 0.9", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 260, 150, 20])
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 290, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 320, 40, 20])

# dry_wet_mix block
dw_boxes, dw_lines = dry_wet_mix(
    "dw",
    wet_source_l=("out_l", 0), wet_source_r=("out_r", 0),
    dry_source_l=("obj-plugin", 0), dry_source_r=("obj-plugin", 1),
)
for b in dw_boxes:
    device.add_box(b)
for l in dw_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# Audio in → lowpass filter
device.add_line("obj-plugin", 0, "lp_l", 0)
device.add_line("obj-plugin", 1, "lp_r", 0)

# Cutoff dial → filter
device.add_line("cutoff_dial", 0, "cut_pk", 0)
device.add_line("cut_pk", 0, "cut_ln", 0)
device.add_line("cut_ln", 0, "lp_l", 1)
device.add_line("cut_ln", 0, "lp_r", 1)

# Resonance dial → filter
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "lp_l", 2)
device.add_line("res_ln", 0, "lp_r", 2)

# Filter output → gain
device.add_line("lp_out_l", 0, "out_l", 0)
device.add_line("lp_out_r", 0, "out_r", 0)
device.add_line("gain_dial", 0, "gain_expr", 0)
device.add_line("gain_expr", 0, "gain_pk", 0)
device.add_line("gain_pk", 0, "gain_ln", 0)
device.add_line("gain_ln", 0, "out_l", 1)
device.add_line("gain_ln", 0, "out_r", 1)

# Mix dial → dry_wet_mix
device.add_line("mix_dial", 0, "dw_mix_in", 0)

# Output → plugout~
device.add_line("dw_out_l", 0, "obj-plugout", 0)
device.add_line("dw_out_r", 0, "obj-plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Preset Demo")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
