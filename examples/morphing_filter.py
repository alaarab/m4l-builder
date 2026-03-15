"""Morphing Filter -- XY pad IS the entire control surface.

X=cutoff, Y=resonance. A live filter curve below shows the frequency
response updating as you move. LFO drives Lissajous auto-movement.

Layout (width=340, height=220):
  +---------------------------------------+
  | +------------------+ [LP|HP|BP|NOTCH] |
  | |                  |  [  Mix  ]       |
  | |    XY PAD        |  [  Drive ]      |
  | |                  |  [LFO Rate]      |
  | +------------------+                  |
  | +------------------+                  |
  | | FILTER CURVE     |                  |
  | +------------------+                  |
  +---------------------------------------+

DSP signal flow:
  plugin~ L/R -> drive (*~) -> svf~ L/R
  XY pad outlet 0 (X 0-1) -> scale 20-20000 -> svf~ cutoff
  XY pad outlet 1 (Y 0-1) -> scale 0-100 -> svf~ resonance
  svf~ 4 outputs -> selector~ 4 1 (LP/HP/BP/Notch)
  selector~ -> dry/wet mix -> plugout~
  LFO: phasor~ -> sin/cos -> modulate XY position
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.engines.xy_pad import xy_pad_js, XY_PAD_INLETS, XY_PAD_OUTLETS
from m4l_builder.engines.filter_curve import filter_curve_js

device = AudioEffect("Morphing Filter", width=340, height=220, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, 340, 220])

# Large XY pad -- the main control surface
device.add_jsui("xy_pad", [8, 8, 240, 142],
                js_code=xy_pad_js(
                    bg_color="0.05, 0.05, 0.06, 1.0",
                    dot_color="0.45, 0.75, 0.65, 1.0",
                    grid_color="0.2, 0.2, 0.22, 0.5",
                ),
                numinlets=XY_PAD_INLETS,
                numoutlets=XY_PAD_OUTLETS)

# Axis labels
device.add_comment("lbl_cutoff", [8, 152, 60, 10], "CUTOFF \u2192",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_res", [220, 8, 26, 10], "RES",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)

# Filter curve display below XY pad
device.add_jsui("filter_display", [8, 162, 240, 50],
                js_code=filter_curve_js(
                    line_color="0.45, 0.75, 0.65, 1.0",
                    fill_color="0.45, 0.75, 0.65, 0.15",
                    grid_color="0.2, 0.2, 0.22, 0.5",
                    text_color="0.5, 0.5, 0.52, 1.0",
                    cursor_color="0.8, 0.8, 0.8, 0.4",
                ),
                numinlets=3)

# Right column (x=256)
device.add_tab("filter_type", "Type", [256, 8, 76, 18],
               options=["LP", "HP", "BP", "NOTCH"],
               rounded=3.0, spacing_x=1.0)

device.add_dial("mix_dial", "Mix", [256, 32, 76, 60],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet Mix")

device.add_dial("drive_dial", "Drive", [256, 96, 76, 60],
                min_val=0.0, max_val=100.0, initial=0.0,
                unitstyle=5, appearance=1,
                annotation_name="Drive Amount")

device.add_dial("lfo_rate_dial", "LFO Rate", [256, 160, 76, 50],
                min_val=0.0, max_val=1.0, initial=0.0,
                unitstyle=1, appearance=1,
                annotation_name="LFO Rate")

# =========================================================================
# DSP objects
# =========================================================================

# --- XY pad scaling ---
# X (0-1) -> frequency 20-20000 Hz (log scale via expr)
device.add_newobj("x_scale", "expr 20. * pow(1000.\\, $f1)",
                  numinlets=1, numoutlets=1, outlettype=[""],
                  patching_rect=[30, 300, 160, 20])

# Y (0-1) -> resonance 0-1 for svf~ (already 0-1 from XY pad, direct use)
# But we also need 0-100 display value for filter_display,
# so scale to 0-100 first, then /100 for svf~
device.add_newobj("y_to_pct", "scale 0. 1. 0. 100.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 300, 120, 20])

# Resonance: 0-100 -> 0-1 for svf~
device.add_newobj("res_to_svf", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 330, 120, 20])

# --- Parameter smoothing: cutoff ---
device.add_newobj("freq_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 340, 60, 20])
device.add_newobj("freq_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 370, 40, 20])

# --- Parameter smoothing: resonance ---
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 360, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 390, 40, 20])

# --- Drive stage ---
# Drive 0-100% -> scale to gain 1.0-4.0
device.add_newobj("drive_scale", "scale 0. 100. 1. 4.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 300, 120, 20])
device.add_newobj("drive_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 330, 60, 20])
device.add_newobj("drive_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 360, 40, 20])
device.add_newobj("drive_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 400, 30, 20])
device.add_newobj("drive_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[150, 400, 30, 20])

# --- SVF filters ---
device.add_newobj("svf_l", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[30, 440, 40, 20])
device.add_newobj("svf_r", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[150, 440, 40, 20])

# --- Mode selector ---
device.add_newobj("tab_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 470, 40, 20])
device.add_newobj("sel_l", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 500, 80, 20])
device.add_newobj("sel_r", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[150, 500, 80, 20])

# --- Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 500, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 530, 55, 20])
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 560, 45, 20])
device.add_newobj("wet_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 550, 60, 20])
device.add_newobj("wet_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 580, 40, 20])
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 550, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[360, 580, 40, 20])
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 550, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[460, 580, 40, 20])
device.add_newobj("dry_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[520, 550, 60, 20])
device.add_newobj("dry_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[520, 580, 40, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 620, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 620, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 620, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 620, 30, 20])
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 660, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 660, 30, 20])

# --- LFO for Lissajous auto-movement ---
device.add_newobj("lfo_rate_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 300, 60, 20])
device.add_newobj("lfo_rate_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[550, 330, 40, 20])
device.add_newobj("lfo_phasor", "phasor~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[550, 360, 50, 20])

# sin(2*pi*phase) for X modulation
device.add_newobj("lfo_twopi", "*~ 6.283185", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[550, 390, 70, 20])
device.add_newobj("lfo_sin", "cos~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[550, 420, 40, 20])
# cos(2*pi*phase) for Y modulation (offset by using sin~)
device.add_newobj("lfo_cos", "sin~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[640, 420, 40, 20])

# Scale LFO to small range (depth = 0.2, so XY moves +/- 0.2)
device.add_newobj("lfo_x_depth", "*~ 0.2", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[550, 450, 50, 20])
device.add_newobj("lfo_y_depth", "*~ 0.2", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[640, 450, 50, 20])

# snapshot~ to get signal back to float for XY pad position feedback
device.add_newobj("lfo_x_snap", "snapshot~ 20", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 480, 70, 20])
device.add_newobj("lfo_y_snap", "snapshot~ 20", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[640, 480, 70, 20])

# Add LFO offset to XY pad base position
# XY pad sends 0-1 floats, LFO adds offset, clamp to 0-1
device.add_newobj("x_base", "float", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 510, 40, 20])
device.add_newobj("y_base", "float", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[640, 510, 40, 20])
device.add_newobj("x_add", "+ 0.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 540, 40, 20])
device.add_newobj("y_add", "+ 0.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[640, 540, 40, 20])
device.add_newobj("x_clip", "clip 0. 1.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[550, 570, 60, 20])
device.add_newobj("y_clip", "clip 0. 1.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[640, 570, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# --- Audio input -> drive -> SVF ---
device.add_line("obj-plugin", 0, "drive_l", 0)
device.add_line("obj-plugin", 1, "drive_r", 0)
device.add_line("drive_dial", 0, "drive_scale", 0)
device.add_line("drive_scale", 0, "drive_pk", 0)
device.add_line("drive_pk", 0, "drive_ln", 0)
device.add_line("drive_ln", 0, "drive_l", 1)
device.add_line("drive_ln", 0, "drive_r", 1)
device.add_line("drive_l", 0, "svf_l", 0)
device.add_line("drive_r", 0, "svf_r", 0)

# --- XY pad -> base position storage ---
# XY pad outputs go to base position (for LFO offset), AND directly to
# the filter scaling chain. When LFO is active, the clipped outputs also
# feed x_scale/y_to_pct (last message wins in Max, which is fine).
device.add_line("xy_pad", 0, "x_base", 1)        # store base X
device.add_line("xy_pad", 1, "y_base", 1)        # store base Y

# Direct XY -> filter scaling (works when LFO rate=0)
device.add_line("xy_pad", 0, "x_scale", 0)
device.add_line("xy_pad", 1, "y_to_pct", 0)

# --- Frequency scaling -> smoothing -> SVF ---
device.add_line("x_scale", 0, "freq_pk", 0)
device.add_line("freq_pk", 0, "freq_ln", 0)
device.add_line("freq_ln", 0, "svf_l", 1)
device.add_line("freq_ln", 0, "svf_r", 1)

# --- Resonance scaling -> smoothing -> SVF ---
device.add_line("y_to_pct", 0, "res_to_svf", 0)
device.add_line("res_to_svf", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "svf_l", 2)
device.add_line("res_ln", 0, "svf_r", 2)

# --- Filter type -> selector ---
device.add_line("filter_type", 0, "tab_offset", 0)
device.add_line("tab_offset", 0, "sel_l", 0)
device.add_line("tab_offset", 0, "sel_r", 0)

# --- SVF outputs -> selector ---
device.add_line("svf_l", 0, "sel_l", 1)   # LP
device.add_line("svf_l", 1, "sel_l", 2)   # HP
device.add_line("svf_l", 2, "sel_l", 3)   # BP
device.add_line("svf_l", 3, "sel_l", 4)   # Notch

device.add_line("svf_r", 0, "sel_r", 1)
device.add_line("svf_r", 1, "sel_r", 2)
device.add_line("svf_r", 2, "sel_r", 3)
device.add_line("svf_r", 3, "sel_r", 4)

# --- Dry/wet mix ---
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)

device.add_line("mix_trig", 0, "wet_pk", 0)
device.add_line("wet_pk", 0, "wet_ln", 0)
device.add_line("wet_ln", 0, "wet_l", 1)

device.add_line("mix_trig", 1, "wet_r_pk", 0)
device.add_line("wet_r_pk", 0, "wet_r_ln", 0)
device.add_line("wet_r_ln", 0, "wet_r", 1)

device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_pk", 0)
device.add_line("dry_pk", 0, "dry_ln", 0)
device.add_line("dry_ln", 0, "dry_l", 1)

device.add_line("mix_inv", 0, "dry_r_pk", 0)
device.add_line("dry_r_pk", 0, "dry_r_ln", 0)
device.add_line("dry_r_ln", 0, "dry_r", 1)

device.add_line("sel_l", 0, "wet_l", 0)
device.add_line("sel_r", 0, "wet_r", 0)

device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# --- Filter curve display wiring ---
device.add_line("x_scale", 0, "filter_display", 0)       # freq Hz
device.add_line("res_to_svf", 0, "filter_display", 1)    # resonance 0-1
device.add_line("filter_type", 0, "filter_display", 2)   # type 0-3

# --- LFO for Lissajous auto-movement ---
device.add_line("lfo_rate_dial", 0, "lfo_rate_pk", 0)
device.add_line("lfo_rate_pk", 0, "lfo_rate_ln", 0)
device.add_line("lfo_rate_ln", 0, "lfo_phasor", 0)

device.add_line("lfo_phasor", 0, "lfo_twopi", 0)
device.add_line("lfo_twopi", 0, "lfo_sin", 0)
device.add_line("lfo_twopi", 0, "lfo_cos", 0)

device.add_line("lfo_sin", 0, "lfo_x_depth", 0)
device.add_line("lfo_cos", 0, "lfo_y_depth", 0)

device.add_line("lfo_x_depth", 0, "lfo_x_snap", 0)
device.add_line("lfo_y_depth", 0, "lfo_y_snap", 0)

# LFO snap -> add to base position -> clip -> feed back to XY pad
device.add_line("lfo_x_snap", 0, "x_add", 0)
device.add_line("lfo_y_snap", 0, "y_add", 0)
device.add_line("x_base", 0, "x_add", 1)
device.add_line("y_base", 0, "y_add", 1)
device.add_line("x_add", 0, "x_clip", 0)
device.add_line("y_add", 0, "y_clip", 0)

# LFO-modulated position drives filter directly (NOT the XY pad)
# XY pad is for manual mouse control only -- LFO never writes to it
device.add_line("x_clip", 0, "x_scale", 0)
device.add_line("y_clip", 0, "y_to_pct", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Morphing Filter")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
