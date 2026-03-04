"""Transport LFO Demo — tremolo driven by Live's transport clock.

Demonstrates: transport_lfo DSP block, beat-division selector, LFO shape
selector, tremolo amplitude modulation, dry/wet mix.

Signal flow:
  plugin~ → *~ (tremolo) → dry_wet_mix → plugout~
  transport_lfo → depth *~ → tremolo gain inlet
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import transport_lfo, dry_wet_mix

WIDTH = 300
HEIGHT = 160
device = AudioEffect("Transport LFO Demo", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

device.add_comment("title", [8, 5, 120, 16], "TRANSPORT LFO",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Beat division selector
device.add_comment("lbl_div", [8, 26, 70, 12], "DIVISION",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_menu("div_menu", "Division", [8, 38, 80, 20],
                ["1/8", "1/4", "1/2", "1/1"])

# LFO shape selector
device.add_comment("lbl_shape", [100, 26, 60, 12], "SHAPE",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_menu("shape_menu", "Shape", [100, 38, 70, 20],
                ["Sine", "Square", "Saw"])

# Depth dial
device.add_comment("lbl_depth", [185, 26, 50, 12], "DEPTH",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_dial("depth_dial", "Depth", [185, 36, 50, 65],
                min_val=0.0, max_val=100.0, initial=50.0,
                unitstyle=5, appearance=1,
                annotation_name="Tremolo depth 0-100%")

# Dry/wet dial
device.add_comment("lbl_mix", [245, 26, 50, 12], "MIX",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_dial("mix_dial", "Mix", [245, 36, 50, 65],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/wet mix")

# =========================================================================
# DSP — transport_lfo with default sine shape
# =========================================================================

# Use the sine transport_lfo block (default)
lfo_boxes, lfo_lines = transport_lfo("tlfo", division='1/4', shape='sine')
for b in lfo_boxes:
    device.add_box(b)
for l in lfo_lines:
    device.lines.append(l)

# Division selector changes the LFO rate via separate expr objects
# div_menu: 0=1/8, 1=1/4, 2=1/2, 3=1/1
# We swap the rate divisor by re-routing through a selector~
# Use a simple approach: div_menu output selects a constant from message objects
device.add_newobj("div_sel", "sel 0 1 2 3", numinlets=1, numoutlets=5,
                  outlettype=["bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 200, 65, 20])
device.add_newobj("div_m_eighth", "f 2.0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 230, 40, 20])
device.add_newobj("div_m_quarter", "f 1.0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[80, 230, 40, 20])
device.add_newobj("div_m_half", "f 0.5", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[130, 230, 40, 20])
device.add_newobj("div_m_whole", "f 0.25", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[180, 230, 45, 20])

# Multiplier applied to the raw BPM-based rate
device.add_newobj("div_store", "f 1.0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 270, 40, 20])
# Override rate: re-compute bpm / (60 * beats) with stored multiplier
device.add_newobj("rate_mul", "expr $f1 * $f2", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 300, 120, 20])

# Shape selector: 0=Sine(cycle~), 1=Square(rect~), 2=Saw(phasor~)
# We keep three transport_lfo outputs but only pass one through a selector~
lfo_sq_boxes, lfo_sq_lines = transport_lfo("tlfo_sq", division='1/4', shape='square')
lfo_saw_boxes, lfo_saw_lines = transport_lfo("tlfo_saw", division='1/4', shape='saw')
for b in lfo_sq_boxes + lfo_saw_boxes:
    device.add_box(b)
for l in lfo_sq_lines + lfo_saw_lines:
    device.lines.append(l)

# selector~ 3 1  — 3 inputs, initial input 1 (sine)
device.add_newobj("shape_sel", "selector~ 3 1", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 330, 80, 20])
device.add_newobj("shape_sel_ctl", "sel 0 1 2", numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", ""],
                  patching_rect=[30, 360, 65, 20])
device.add_newobj("shape_idx", "t 1 2 3", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[30, 390, 55, 20])

# Depth scaling: depth_dial 0-100% → *~ tremolo depth
device.add_newobj("depth_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 330, 130, 20])
device.add_newobj("depth_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 360, 60, 20])
device.add_newobj("depth_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 390, 40, 20])

# LFO scaled by depth → tremolo multiplier
# Tremolo = 1 - (depth * lfo_signal)  so at depth=0 gain=1 (dry), at depth=1 it modulates
device.add_newobj("trem_mul", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 420, 50, 20])
device.add_newobj("trem_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 450, 45, 20])

# Stereo tremolo gain multipliers
device.add_newobj("trem_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 450, 40, 20])
device.add_newobj("trem_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[330, 450, 40, 20])

# dry_wet_mix block
dw_boxes, dw_lines = dry_wet_mix(
    "dw",
    wet_source_l=("trem_l", 0), wet_source_r=("trem_r", 0),
    dry_source_l=("obj-plugin", 0), dry_source_r=("obj-plugin", 1),
)
for b in dw_boxes:
    device.add_box(b)
for l in dw_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# Division menu → selector → div_store → rate_mul
device.add_line("div_menu", 0, "div_sel", 0)
device.add_line("div_sel", 0, "div_m_eighth", 0)
device.add_line("div_sel", 1, "div_m_quarter", 0)
device.add_line("div_sel", 2, "div_m_half", 0)
device.add_line("div_sel", 3, "div_m_whole", 0)
device.add_line("div_m_eighth", 0, "div_store", 1)
device.add_line("div_m_quarter", 0, "div_store", 1)
device.add_line("div_m_half", 0, "div_store", 1)
device.add_line("div_m_whole", 0, "div_store", 1)

# Fan division multiplier to all 3 LFO rate objects
device.add_line("div_store", 0, "rate_mul", 1)
device.add_line("tlfo_rate", 0, "rate_mul", 0)
device.add_line("rate_mul", 0, "tlfo_osc", 0)
device.add_line("rate_mul", 0, "tlfo_sq_osc", 0)
device.add_line("rate_mul", 0, "tlfo_saw_osc", 0)

# Shape selector wiring
device.add_line("shape_menu", 0, "shape_sel_ctl", 0)
device.add_line("shape_sel_ctl", 0, "shape_idx", 0)
device.add_line("shape_sel_ctl", 1, "shape_idx", 1)
device.add_line("shape_sel_ctl", 2, "shape_idx", 2)
device.add_line("shape_idx", 0, "shape_sel", 0)
device.add_line("shape_idx", 1, "shape_sel", 0)
device.add_line("shape_idx", 2, "shape_sel", 0)
device.add_line("tlfo_osc", 0, "shape_sel", 1)
device.add_line("tlfo_sq_osc", 0, "shape_sel", 2)
device.add_line("tlfo_saw_osc", 0, "shape_sel", 3)

# Depth scaling
device.add_line("depth_dial", 0, "depth_scale", 0)
device.add_line("depth_scale", 0, "depth_pk", 0)
device.add_line("depth_pk", 0, "depth_ln", 0)

# LFO output scaled by depth → tremolo
device.add_line("shape_sel", 0, "trem_mul", 0)
device.add_line("depth_ln", 0, "trem_mul", 1)
device.add_line("trem_mul", 0, "trem_inv", 0)

# Tremolo gain applied to audio
device.add_line("obj-plugin", 0, "trem_l", 0)
device.add_line("obj-plugin", 1, "trem_r", 0)
device.add_line("trem_inv", 0, "trem_l", 1)
device.add_line("trem_inv", 0, "trem_r", 1)

# Mix dial → dry_wet mix
device.add_line("mix_dial", 0, "dw_mix_in", 0)

# Output → plugout~
device.add_line("dw_out_l", 0, "obj-plugout", 0)
device.add_line("dw_out_r", 0, "obj-plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Transport LFO Demo")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
