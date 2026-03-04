"""FDN Reverb — AudioEffect example.

Feedback delay network reverb using prime delay times for a dense,
diffuse reverberation tail.

Architecture:
  plugin~ -> fdn_reverb (8 tapin~/tapout~ at prime delays + sum)
  -> pre-delay tapin~/tapout~
  -> damping onepole~ on each tapout (feedback path)
  -> dry/wet mix -> plugout~
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import fdn_reverb, dry_wet_mix

WIDTH = 360
HEIGHT = 190
device = AudioEffect("FDN Reverb", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])

device.add_comment("title", [8, 5, 80, 16], "FDN REVERB",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

device.add_comment("lbl_params", [8, 22, 100, 12], "PARAMETERS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_mix", [238, 22, 60, 12], "MIX",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Pre-delay dial: 0-100ms
device.add_dial("pre_dial", "Pre-Delay", [8, 32, 50, 70],
                min_val=0.0, max_val=100.0, initial=10.0,
                unitstyle=2, appearance=1,
                annotation_name="Pre-delay before reverb onset in milliseconds")
device.add_comment("lbl_pre", [8, 106, 50, 12], "PRE-DLY",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Size dial: 0.1-2.0 (scales feedback amount)
device.add_dial("size_dial", "Size", [66, 32, 50, 70],
                min_val=0.1, max_val=2.0, initial=0.6,
                unitstyle=1, appearance=1,
                annotation_name="Room size — scales feedback delay times")
device.add_comment("lbl_size", [66, 106, 50, 12], "SIZE",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Damping dial: 0-100%
device.add_dial("damp_dial", "Damping", [124, 32, 50, 70],
                min_val=0.0, max_val=100.0, initial=40.0,
                unitstyle=5, appearance=1,
                annotation_name="High-frequency damping in the reverb tail")
device.add_comment("lbl_damp", [124, 106, 50, 12], "DAMPING",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Dry/wet mix dial: 0-100%
device.add_dial("mix_dial", "Mix", [238, 32, 50, 70],
                min_val=0.0, max_val=100.0, initial=35.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/wet mix — 0% dry, 100% wet")
device.add_comment("lbl_mix2", [238, 106, 50, 12], "DRY/WET",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Output meters
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
# DSP objects
# =========================================================================

# Pre-delay: simple tapin~/tapout~ pair (stereo)
device.add_newobj("pre_tapin_l", "tapin~ 200", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[30, 230, 80, 20])
device.add_newobj("pre_tapout_l", "tapout~ 10", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 260, 70, 20])
device.add_newobj("pre_tapin_r", "tapin~ 200", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[150, 230, 80, 20])
device.add_newobj("pre_tapout_r", "tapout~ 10", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[150, 260, 70, 20])

device.add_newobj("pre_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 200, 60, 20])
device.add_newobj("pre_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 220, 40, 20])

# FDN reverb block (L channel — mono network, spread to stereo after)
fdn_boxes_l, fdn_lines_l = fdn_reverb("fdnL", num_delays=8)
fdn_boxes_r, fdn_lines_r = fdn_reverb("fdnR", num_delays=8)
for b in fdn_boxes_l + fdn_boxes_r:
    device.add_box(b)
for l in fdn_lines_l + fdn_lines_r:
    device.lines.append(l)

# Size/feedback scaling: size 0.1-2.0 -> feedback 0.3-0.85
# scale 0.1 2.0 0.3 0.85
device.add_newobj("size_fb", "scale 0.1 2.0 0.3 0.85", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[280, 230, 140, 20])
device.add_newobj("fb_trig", "t f f f f f f f f f f f f f f f f",
                  numinlets=1, numoutlets=16,
                  outlettype=[""] * 16, patching_rect=[280, 260, 250, 20])

# Feedback multipliers for each delay line (L and R)
for i in range(8):
    device.add_newobj(f"fbL_{i}", "*~ 0.6", numinlets=2, numoutlets=1,
                      outlettype=["signal"],
                      patching_rect=[30 + i * 100, 310, 50, 20])
    device.add_newobj(f"fbR_{i}", "*~ 0.6", numinlets=2, numoutlets=1,
                      outlettype=["signal"],
                      patching_rect=[30 + i * 100, 360, 50, 20])

# Damping: damp_dial 0-100% -> onepole~ cutoff 20000-500 Hz
device.add_newobj("damp_scale", "scale 0. 100. 20000. 500.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 310, 130, 20])
device.add_newobj("damp_trig", "t f f f f f f f f f f f f f f f f",
                  numinlets=1, numoutlets=16,
                  outlettype=[""] * 16, patching_rect=[400, 340, 250, 20])

# Onepole damping per tap (L and R)
for i in range(8):
    device.add_newobj(f"dampL_{i}", "onepole~ 5000.", numinlets=2, numoutlets=1,
                      outlettype=["signal"],
                      patching_rect=[30 + i * 100, 340, 80, 20])
    device.add_newobj(f"dampR_{i}", "onepole~ 5000.", numinlets=2, numoutlets=1,
                      outlettype=["signal"],
                      patching_rect=[30 + i * 100, 390, 80, 20])

# Dry/wet mix
dw_boxes, dw_lines = dry_wet_mix(
    "dw",
    wet_source_l=("fdnL_sum", 0),
    wet_source_r=("fdnR_sum", 0),
    dry_source_l=("obj-plugin", 0),
    dry_source_r=("obj-plugin", 1),
)
for b in dw_boxes:
    device.add_box(b)
for l in dw_lines:
    device.lines.append(l)

# =========================================================================
# Connections
# =========================================================================

# plugin~ -> pre-delay
device.add_line("obj-plugin", 0, "pre_tapin_l", 0)
device.add_line("obj-plugin", 1, "pre_tapin_r", 0)
device.add_line("pre_tapin_l", 0, "pre_tapout_l", 0)
device.add_line("pre_tapin_r", 0, "pre_tapout_r", 0)

# Pre-delay time smoothing
device.add_line("pre_dial", 0, "pre_pk", 0)
device.add_line("pre_pk", 0, "pre_ln", 0)
device.add_line("pre_ln", 0, "pre_tapout_l", 1)
device.add_line("pre_ln", 0, "pre_tapout_r", 1)

# Pre-delay output -> FDN input taps (same signal to all taps)
for i in range(8):
    device.add_line("pre_tapout_l", 0, f"fdnL_tapin_{i}", 0)
    device.add_line("pre_tapout_r", 0, f"fdnR_tapin_{i}", 0)

# Feedback: tapout -> damp -> feedback mul -> sum back into tapin
for i in range(8):
    device.add_line(f"fdnL_tapout_{i}", 0, f"dampL_{i}", 0)
    device.add_line(f"fdnR_tapout_{i}", 0, f"dampR_{i}", 0)
    device.add_line(f"dampL_{i}", 0, f"fbL_{i}", 0)
    device.add_line(f"dampR_{i}", 0, f"fbR_{i}", 0)
    # Feedback into corresponding tapin (cross-couple neighboring taps for FDN)
    device.add_line(f"fbL_{i}", 0, f"fdnL_tapin_{(i + 1) % 8}", 0)
    device.add_line(f"fbR_{i}", 0, f"fdnR_tapin_{(i + 1) % 8}", 0)

# Size -> feedback scale -> fan to all feedback multipliers
device.add_line("size_dial", 0, "size_fb", 0)
device.add_line("size_fb", 0, "fb_trig", 0)
for i in range(8):
    device.add_line("fb_trig", i, f"fbL_{i}", 1)
    device.add_line("fb_trig", i + 8, f"fbR_{i}", 1)

# Damping -> scale -> fan to all onepole cutoffs
device.add_line("damp_dial", 0, "damp_scale", 0)
device.add_line("damp_scale", 0, "damp_trig", 0)
for i in range(8):
    device.add_line("damp_trig", i, f"dampL_{i}", 1)
    device.add_line("damp_trig", i + 8, f"dampR_{i}", 1)

# Mix dial -> dry/wet block
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[500, 80, 120, 20])
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "dw_mix_in", 0)

# Dry/wet outputs -> plugout~ and meters
device.add_line("dw_out_l", 0, "obj-plugout", 0)
device.add_line("dw_out_r", 0, "obj-plugout", 1)
device.add_line("dw_out_l", 0, "meter_l", 0)
device.add_line("dw_out_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("FDN Reverb")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
