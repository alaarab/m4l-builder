"""Modulation Matrix Demo — AudioEffect example.

Demonstrates: macro_modulation_matrix (4 sources x 4 targets),
4 morphing_lfo instances as sources, targets mapped to filter cutoff,
reverb size, saturation drive, and LFO rate. 4 macro dials as amplitude.

Signal flow:
  plugin~ → saturation → lowpass_filter → reverb_network → plugout~
  4x morphing_lfo → macro_modulation_matrix → targets (cutoff, reverb, sat, rate)
"""

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.dsp import (morphing_lfo, macro_modulation_matrix,
                               lowpass_filter, reverb_network, saturation)

WIDTH = 400
HEIGHT = 200
device = AudioEffect("Modulation Matrix Demo", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], background=1)

device.add_comment("title", [8, 5, 180, 16], "MODULATION MATRIX",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.88, 0.88, 0.88, 1.0])

# Section labels
device.add_comment("lbl_src", [8, 26, 80, 12], "LFO SOURCES",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_macro", [8, 90, 80, 12], "MACRO AMOUNTS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# 4 LFO rate dials (one per source)
LFO_LABELS = ["LFO 1", "LFO 2", "LFO 3", "LFO 4"]
LFO_RATES = [0.5, 1.0, 2.0, 4.0]

for i, (lbl, rate) in enumerate(zip(LFO_LABELS, LFO_RATES)):
    x = 8 + i * 80
    device.add_dial(f"lfo_rate_{i}", lbl, [x, 36, 50, 50],
                    min_val=0.01, max_val=20.0, initial=rate,
                    unitstyle=3, parameter_exponent=2.0, appearance=1,
                    annotation_name=f"Rate for LFO source {i + 1}")

# 4 macro amount dials
MACRO_LABELS = ["Macro 1", "Macro 2", "Macro 3", "Macro 4"]
for i, lbl in enumerate(MACRO_LABELS):
    x = 8 + i * 80
    device.add_dial(f"macro_{i}", lbl, [x, 100, 50, 70],
                    min_val=0.0, max_val=1.0, initial=0.0,
                    unitstyle=1, appearance=1,
                    annotation_name=f"Macro {i + 1} modulation amount")

# Target labels
TARGET_LABELS = ["Cutoff", "Reverb", "Drive", "Rate"]
device.add_comment("lbl_targets", [220, 26, 160, 12], "TARGETS",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
for i, lbl in enumerate(TARGET_LABELS):
    device.add_comment(f"lbl_tgt_{i}", [240 + i * 40, 38, 38, 12], lbl,
                       fontsize=7.5, textcolor=[0.55, 0.55, 0.57, 0.7])

# =========================================================================
# DSP — 4 morphing LFOs
# =========================================================================

for i in range(4):
    lfo_boxes, lfo_lines = morphing_lfo(f"lfo{i}")
    for b in lfo_boxes:
        device.add_box(b)
    for l in lfo_lines:
        device.lines.append(l)

# =========================================================================
# DSP — modulation matrix (4x4)
# =========================================================================

mm_boxes, mm_lines = macro_modulation_matrix("mm", sources=4, targets=4)
for b in mm_boxes:
    device.add_box(b)
for l in mm_lines:
    device.lines.append(l)

# =========================================================================
# DSP — signal chain: saturation → lowpass → reverb
# =========================================================================

sat_boxes, sat_lines = saturation("sat", mode="tanh")
for b in sat_boxes:
    device.add_box(b)
for l in sat_lines:
    device.lines.append(l)

lp_boxes, lp_lines = lowpass_filter("lp")
for b in lp_boxes:
    device.add_box(b)
for l in lp_lines:
    device.lines.append(l)

rv_boxes, rv_lines = reverb_network("rv", num_combs=4, num_allpasses=2)
for b in rv_boxes:
    device.add_box(b)
for l in rv_lines:
    device.lines.append(l)

# =========================================================================
# Modulation depth scale objects (one per macro, scale 0-1 → 0-5000 Hz or 0-1)
# =========================================================================

# Macro amount → scale → modulation matrix gain inlet 1 per source-to-target cell
# Each macro dial scales one source's contribution across all 4 targets
# Wire each macro dial to the appropriate *~ cells in the matrix
for i in range(4):
    device.add_newobj(f"macro_pk_{i}", "pack f 20", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[400 + i * 70, 300, 60, 20])
    device.add_newobj(f"macro_ln_{i}", "line~", numinlets=2, numoutlets=2,
                      outlettype=["signal", "bang"], patching_rect=[400 + i * 70, 330, 40, 20])

# Cutoff target: scale matrix output 0-1 → 200-8000 Hz
device.add_newobj("tgt_cutoff_scale", "scale 0. 1. 200. 8000.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 600, 140, 20])
# Reverb target: scale 0-1 → 0.3-0.9 feedback
device.add_newobj("tgt_rv_scale", "scale 0. 1. 0.3 0.9", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 600, 140, 20])
# Saturation drive: scale 0-1 → 0.5-4.0
device.add_newobj("tgt_sat_scale", "scale 0. 1. 0.5 4.0", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[370, 600, 140, 20])
# Rate target feeds back to LFO 0 rate
device.add_newobj("tgt_rate_scale", "scale 0. 1. 0.1 10.0", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[540, 600, 140, 20])
device.add_newobj("tgt_rate_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[540, 630, 60, 20])
device.add_newobj("tgt_rate_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[540, 660, 40, 20])

# =========================================================================
# Connections
# =========================================================================

# LFO rate dials → phasor and sine rate inlets
for i in range(4):
    device.add_line(f"lfo_rate_{i}", 0, f"lfo{i}_phasor", 0)
    device.add_line(f"lfo_rate_{i}", 0, f"lfo{i}_sine", 0)

# LFO outputs → modulation matrix source inputs (each LFO fans to all 4 targets)
for i in range(4):
    for j in range(4):
        device.add_line(f"lfo{i}_sel", 0, f"mm_src_{i}_to_{j}", 0)

# Macro dials → pack/line~ → matrix gain cells (inlet 1 per cell)
for i in range(4):
    device.add_line(f"macro_{i}", 0, f"macro_pk_{i}", 0)
    device.add_line(f"macro_pk_{i}", 0, f"macro_ln_{i}", 0)
    for j in range(4):
        device.add_line(f"macro_ln_{i}", 0, f"mm_src_{i}_to_{j}", 1)

# Matrix target outputs → parameter scalers
# tgt_0 = cutoff, tgt_1 = reverb, tgt_2 = saturation drive, tgt_3 = LFO rate
device.add_line("mm_tgt_0", 0, "tgt_cutoff_scale", 0)
device.add_line("mm_tgt_1", 0, "tgt_rv_scale", 0)
device.add_line("mm_tgt_2", 0, "tgt_sat_scale", 0)
device.add_line("mm_tgt_3", 0, "tgt_rate_scale", 0)

# Cutoff target → filter inlet 1 (cutoff Hz)
device.add_line("tgt_cutoff_scale", 0, "lp_l", 1)
device.add_line("tgt_cutoff_scale", 0, "lp_r", 1)

# Reverb target → comb filters (feedback inlet 1)
for c in range(4):
    device.add_line("tgt_rv_scale", 0, f"rv_comb_{c}", 1)

# Drive target → sat multiplier (passthrough — tanh~ has 1 inlet; use upstream *~)
# We can't easily modulate tanh~ drive, so we modulate the output level
device.add_newobj("sat_drive_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 700, 40, 20])
device.add_newobj("sat_drive_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 700, 40, 20])
device.add_line("tgt_sat_scale", 0, "sat_drive_l", 1)
device.add_line("tgt_sat_scale", 0, "sat_drive_r", 1)

# Rate target feeds back to LFO 0 rate via line~
device.add_line("tgt_rate_scale", 0, "tgt_rate_pk", 0)
device.add_line("tgt_rate_pk", 0, "tgt_rate_ln", 0)
device.add_line("tgt_rate_ln", 0, "lfo0_phasor", 0)

# Plugin audio → saturation → drive scale → lowpass filter → reverb → plugout~
device.add_line("obj-plugin", 0, "sat_l", 0)
device.add_line("obj-plugin", 1, "sat_r", 0)
device.add_line("sat_l", 0, "sat_drive_l", 0)
device.add_line("sat_r", 0, "sat_drive_r", 0)
device.add_line("sat_drive_l", 0, "lp_l", 0)
device.add_line("sat_drive_r", 0, "lp_r", 0)
device.add_line("lp_out_l", 0, "rv_comb_0", 0)
device.add_line("lp_out_l", 0, "rv_comb_1", 0)
device.add_line("lp_out_l", 0, "rv_comb_2", 0)
device.add_line("lp_out_l", 0, "rv_comb_3", 0)
device.add_line("rv_ap_1", 0, "obj-plugout", 0)
device.add_line("lp_out_r", 0, "obj-plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Modulation Matrix Demo")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
