"""Morphing LFO Demo - AudioEffect example.

Demonstrates: morphing_lfo (waveform blend 0.0-3.0), LFO rate/depth controls,
auto_gain output normalization, dry/wet mix, tremolo effect.

Signal flow:
  plugin~ → tremolo (*~) → auto_gain → dry_wet_mix → plugout~
  morphing_lfo → depth scale → tremolo amplitude
"""

from m4l_builder import AudioEffect, COOL, device_output_path
from m4l_builder.dsp import morphing_lfo, auto_gain, dry_wet_mix

WIDTH = 340
HEIGHT = 170
device = AudioEffect("Morphing LFO Demo", width=WIDTH, height=HEIGHT, theme=COOL)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

device.add_comment("title", [8, 5, 140, 16], "MORPHING LFO",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.12, 0.12, 0.14, 1.0])

# Section labels
device.add_comment("lbl_lfo", [8, 26, 60, 12], "LFO",
                   fontsize=9.0, textcolor=[0.20, 0.50, 0.85, 0.7])
device.add_comment("lbl_trem", [210, 26, 80, 12], "TREMOLO",
                   fontsize=9.0, textcolor=[0.20, 0.50, 0.85, 0.7])

# Waveform blend dial: 0=sine, 1=tri, 2=square, 3=saw
device.add_dial("shape_dial", "Shape", [8, 36, 50, 70],
                min_val=0.0, max_val=3.0, initial=0.0,
                unitstyle=1, appearance=1,
                annotation_name="Waveform blend: 0=sine 1=tri 2=square 3=saw")

# Rate dial
device.add_dial("rate_dial", "Rate", [68, 36, 50, 70],
                min_val=0.01, max_val=20.0, initial=2.0,
                unitstyle=3, parameter_exponent=2.0, appearance=1,
                annotation_name="LFO rate in Hz")

# Depth dial
device.add_dial("depth_dial", "Depth", [128, 36, 50, 70],
                min_val=0.0, max_val=100.0, initial=60.0,
                unitstyle=5, appearance=1,
                annotation_name="Tremolo depth 0-100%")

# Dry/wet mix dial
device.add_dial("mix_dial", "Mix", [210, 36, 50, 70],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/wet mix")

# Scope showing modulated output
device.add_scope("scope", [270, 36, 60, 70],
                 smooth=2, line_width=1.5, calccount=128)

# =========================================================================
# DSP: morphing_lfo, auto_gain, dry_wet_mix
# =========================================================================

lfo_boxes, lfo_lines = morphing_lfo("mlfo")
for b in lfo_boxes:
    device.add_box(b)
for l in lfo_lines:
    device.lines.append(l)

# Tremolo multiplier: audio * lfo-modulated gain
# depth scale: 0-100% → 0-1 range, LFO is -1..1, we want 0..1 modulated gain
# gain = 1 - depth * (1 - lfo) * 0.5  →  bias=0.5, depth scales swing
device.add_newobj("depth_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 280, 130, 20])
device.add_newobj("depth_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 310, 60, 20])
device.add_newobj("depth_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 340, 40, 20])

# LFO scaled by depth: lfo_out * depth
device.add_newobj("trem_mul", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 380, 50, 20])
# Invert to get (1 - depth*lfo) envelope
device.add_newobj("trem_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 410, 45, 20])

# Stereo tremolo gates
device.add_newobj("trem_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 440, 40, 20])
device.add_newobj("trem_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[330, 440, 40, 20])

# auto_gain for output normalization
ag_boxes, ag_lines = auto_gain("ag")
for b in ag_boxes:
    device.add_box(b)
for l in ag_lines:
    device.lines.append(l)

# dry_wet_mix block
dw_boxes, dw_lines = dry_wet_mix(
    "dw",
    wet_source_l=("ag_mul", 0), wet_source_r=("ag_mul", 0),
    dry_source_l=("obj-plugin", 0), dry_source_r=("obj-plugin", 1),
)
for b in dw_boxes:
    device.add_box(b)
for l in dw_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# Rate dial → morphing LFO phasor
device.add_line("rate_dial", 0, "mlfo_phasor", 0)
device.add_line("rate_dial", 0, "mlfo_sine", 0)

# Shape dial → sel: needs integer 1-4 from 0-3 float
# sel inlet 0 = integer selector (1-indexed in selector~)
device.add_newobj("shape_int", "expr (int)$f1 + 1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 440, 140, 20])
device.add_line("shape_dial", 0, "shape_int", 0)
device.add_line("shape_int", 0, "mlfo_sel", 0)

# Depth dial → scale → pack/line~ → trem_mul inlet 1
device.add_line("depth_dial", 0, "depth_scale", 0)
device.add_line("depth_scale", 0, "depth_pk", 0)
device.add_line("depth_pk", 0, "depth_ln", 0)
device.add_line("depth_ln", 0, "trem_mul", 1)

# LFO output → trem_mul (scale by depth)
device.add_line("mlfo_sel", 0, "trem_mul", 0)

# Tremolo chain: mul → inv → trem_l/r gates
device.add_line("trem_mul", 0, "trem_inv", 0)
device.add_line("trem_inv", 0, "trem_l", 1)
device.add_line("trem_inv", 0, "trem_r", 1)

# Plugin audio → tremolo gates
device.add_line("obj-plugin", 0, "trem_l", 0)
device.add_line("obj-plugin", 1, "trem_r", 0)

# Tremolo L into auto_gain (mono tap for gain computation, apply to both)
device.add_line("trem_l", 0, "ag_env", 0)
device.add_line("trem_l", 0, "ag_mul", 0)

# Dry/wet mix control: mix_dial → dw_mix_in
device.add_line("mix_dial", 0, "dw_mix_in", 0)

# Scope from auto_gain output
device.add_line("ag_mul", 0, "scope", 0)
device.add_line("ag_mul", 0, "scope", 1)

# dw output → plugout~
device.add_line("dw_out_l", 0, "obj-plugout", 0)
device.add_line("dw_out_r", 0, "obj-plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Morphing LFO Demo")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
