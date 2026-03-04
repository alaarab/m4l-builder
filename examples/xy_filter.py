"""XY filter -- control filter frequency and resonance with an XY pad.

Showcase: XY pad engine, filter DSP, interactive JSUI control.
"""
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.engines.xy_pad import xy_pad_js, XY_PAD_INLETS, XY_PAD_OUTLETS
from m4l_builder.dsp import lowpass_filter

device = AudioEffect("XY Filter", width=250, height=220, theme=MIDNIGHT)

# Background
device.add_panel("bg", [0, 0, 250, 220])

# XY Pad display
device.add_jsui("xy", [10, 10, 230, 180],
                js_code=xy_pad_js(),
                numinlets=XY_PAD_INLETS,
                numoutlets=XY_PAD_OUTLETS)

# Labels
device.add_comment("x_lbl", [10, 195, 40, 16], "Freq", fontsize=9.0)
device.add_comment("y_lbl", [200, 195, 40, 16], "Res", fontsize=9.0)

# Filter DSP: lowpass_filter returns svf~ pairs with pass-through outputs
# svf~ inlets: 0=signal, 1=cutoff_hz, 2=resonance (0-1)
# Output boxes: lpf_out_l, lpf_out_r (outlet 0)
flt_boxes, flt_lines = lowpass_filter("lpf")
for b in flt_boxes:
    device.add_box(b)
for l in flt_lines:
    device.lines.append(l)

# Scale X (0-1) to frequency (20-20000): expr 20. * pow(1000., $f1)
device.add_newobj("x_scale", "expr 20. * pow(1000.\\, $f1)",
                  numinlets=1, numoutlets=1, outlettype=[""])

# Wire: plugin -> filter -> plugout
device.add_line("obj-plugin", 0, "lpf_l", 0)
device.add_line("obj-plugin", 1, "lpf_r", 0)
device.add_line("lpf_out_l", 0, "obj-plugout", 0)
device.add_line("lpf_out_r", 0, "obj-plugout", 1)

# XY pad -> scaling -> filter control
device.add_line("xy", 0, "x_scale", 0)      # X -> freq scaling
device.add_line("x_scale", 0, "lpf_l", 1)   # scaled freq -> filter L
device.add_line("x_scale", 0, "lpf_r", 1)   # scaled freq -> filter R
device.add_line("xy", 1, "lpf_l", 2)        # Y -> resonance L
device.add_line("xy", 1, "lpf_r", 2)        # Y -> resonance R

output = device_output_path("XY Filter")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
