"""Convolution Reverb — AudioEffect using an impulse response buffer.

Demonstrates: convolver DSP block, live.drop for IR file loading,
dry_wet_mix, output gain.

Signal flow:
  plugin~ → convolve~ (ir_buf) → dry_wet_mix → *~ (gain) → plugout~
  live.drop → read message → buffer~
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import convolver, dry_wet_mix

WIDTH = 300
HEIGHT = 170
device = AudioEffect("Convolution Reverb", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)


# IR file drop target
device.add_comment("lbl_ir", [8, 26, 60, 12], "IMPULSE RESPONSE",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_live_drop("ir_drop", [8, 38, 170, 30])

# Dry/wet dial
device.add_comment("lbl_mix", [190, 26, 50, 12], "MIX",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_dial("mix_dial", "Mix", [190, 36, 50, 65],
                min_val=0.0, max_val=100.0, initial=40.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/wet mix — 0% dry, 100% wet")

# Output gain dial
device.add_comment("lbl_gain", [248, 26, 50, 12], "GAIN",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_dial("gain_dial", "Gain", [248, 36, 50, 65],
                min_val=-24.0, max_val=6.0, initial=0.0,
                unitstyle=4, appearance=1,
                annotation_name="Output gain in dB")

# =========================================================================
# DSP
# =========================================================================

# Convolver block — mono IR applied to L only, then duplicated
conv_boxes, conv_lines = convolver("conv", ir_buffer="conv_ir")
for b in conv_boxes:
    device.add_box(b)

# dry_wet_mix block
dw_boxes, dw_lines = dry_wet_mix(
    "dw",
    wet_source_l=("conv_conv", 0), wet_source_r=("conv_conv", 0),
    dry_source_l=("obj-plugin", 0), dry_source_r=("obj-plugin", 1),
)
for b in dw_boxes:
    device.add_box(b)
for l in dw_lines:
    device.lines.append(l)

# Output gain: dB → linear via pow(10, dB/20)
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

# live.drop → prepend "read " → conv buffer~
device.add_newobj("drop_prep", "prepend read", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 350, 90, 20])

# =========================================================================
# Connections
# =========================================================================

# Audio in → convolve~ (mix L+R to mono)
device.add_newobj("mix_mono", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 300, 30, 20])
device.add_newobj("scale_mono", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 330, 50, 20])

device.add_line("obj-plugin", 0, "mix_mono", 0)
device.add_line("obj-plugin", 1, "mix_mono", 1)
device.add_line("mix_mono", 0, "scale_mono", 0)
device.add_line("scale_mono", 0, "conv_conv", 0)

# live.drop → read into buffer~
device.add_line("ir_drop", 0, "drop_prep", 0)
device.add_line("drop_prep", 0, "conv_ir_buf", 0)

# Mix dial → dry_wet_mix
device.add_line("mix_dial", 0, "dw_mix_in", 0)

# Output gain
device.add_line("gain_dial", 0, "gain_expr", 0)
device.add_line("gain_expr", 0, "gain_pk", 0)
device.add_line("gain_pk", 0, "gain_ln", 0)
device.add_line("dw_out_l", 0, "out_l", 0)
device.add_line("dw_out_r", 0, "out_r", 0)
device.add_line("gain_ln", 0, "out_l", 1)
device.add_line("gain_ln", 0, "out_r", 1)

# Output → plugout~
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Convolution Reverb", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
