"""Multiband Saturator — m4l_builder example.

3-band crossover with independent saturation per band.

Signal flow:
  plugin~ L/R
    → cross~ low_freq (L+R) → LP=LOW, HP → cross~ high_freq (L+R) → LP=MID, HP=HIGH
  Per band, per channel:
    → *~ drive  (pre-saturation gain, smoothed via line~)
    → selector~ 4 1 → mode 1=tanh~, 2=overdrive~, 3=clip~, 4=bypass *~
    → *~ band_gain (post-saturation level, smoothed via line~)
  Sum bands: LOW + MID + HIGH via +~
  DC block: biquad~ 1. -1. 0. -0.9997 0.
  Dry/wet mix (smoothed via line~) → plugout~
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path

# -------------------------------------------------------------------
# Device setup — taller to fit scope at top
# -------------------------------------------------------------------
device = AudioEffect("Multiband Saturator", width=380, height=205, theme=MIDNIGHT)

# -------------------------------------------------------------------
# UI panels (background MUST have background:1)
# -------------------------------------------------------------------
device.add_panel("bg", [0, 0, 380, 205],
                 bgcolor=[0.05, 0.05, 0.06, 1.0])

# Output waveform scope — hero visual at top
device.add_scope("out_scope", [8, 8, 328, 46],
                 bgcolor=[0.04, 0.04, 0.05, 1.0],
                 activelinecolor=[0.45, 0.75, 0.65, 1.0],
                 gridcolor=[0.12, 0.12, 0.14, 0.4],
                 range_vals=[-1.0, 1.0],
                 calccount=64, smooth=2, line_width=1.5)

# Band column backgrounds (subtle tint, dark MIDNIGHT palette)
band_colors = {
    "low":  [0.08, 0.09, 0.12, 1.0],
    "mid":  [0.08, 0.11, 0.09, 1.0],
    "high": [0.12, 0.08, 0.08, 1.0],
}
band_x = {"low": 100, "mid": 180, "high": 260}
for band, bx in band_x.items():
    device.add_panel(f"panel_{band}", [bx, 58, 78, 143],
                     bgcolor=band_colors[band])

# Stereo output meters
device.add_meter("meter_l", [342, 8, 12, 155],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [358, 8, 12, 155],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# -------------------------------------------------------------------
# Crossover frequency dials
# -------------------------------------------------------------------
device.add_comment("lbl_xover", [6, 58, 96, 12], "CROSSOVER",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("low_xover", "Low Xover", [6, 68, 50, 68],
                min_val=40.0, max_val=1000.0, initial=200.0,
                unitstyle=3,   # Hz
                annotation_name="Low crossover frequency")

device.add_dial("high_xover", "High Xover", [52, 68, 50, 68],
                min_val=400.0, max_val=12000.0, initial=3000.0,
                unitstyle=3,   # Hz
                annotation_name="High crossover frequency")

# -------------------------------------------------------------------
# Global Mix dial
# -------------------------------------------------------------------
device.add_comment("lbl_mix", [6, 140, 50, 12], "MIX",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

device.add_dial("mix_dial", "Mix", [6, 152, 50, 50],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5,   # percent
                annotation_name="Dry/wet mix amount")

# -------------------------------------------------------------------
# Per-band UI: Drive dial + Mode tab + Gain dial
# Tab options: TAPE / TUBE / CLIP / OFF  (selector~ expects 1-indexed)
# -------------------------------------------------------------------
tab_colors = {
    "low":  [0.25, 0.35, 0.60, 1.0],
    "mid":  [0.25, 0.50, 0.30, 1.0],
    "high": [0.55, 0.25, 0.25, 1.0],
}
band_labels = {"low": "LOW", "mid": "MID", "high": "HIGH"}

device.add_comment("lbl_drive_gain", [100, 58, 238, 12], "DRIVE / GAIN",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.5])

for band, bx in band_x.items():
    # Column label
    device.add_comment(f"lbl_{band}", [bx + 2, 58, 74, 12],
                       band_labels[band],
                       textcolor=[0.80, 0.80, 0.80, 1.0], fontsize=10.0)

    # Drive dial
    device.add_dial(f"drive_{band}", f"Drive {band_labels[band]}",
                    [bx + 2, 70, 36, 50],
                    min_val=0.0, max_val=100.0, initial=15.0,
                    unitstyle=5,
                    annotation_name=f"{band_labels[band]} band saturation drive")

    # Gain dial: -12 to +6 dB
    device.add_dial(f"gain_{band}", f"Gain {band_labels[band]}",
                    [bx + 40, 70, 36, 50],
                    min_val=-12.0, max_val=6.0, initial=0.0,
                    unitstyle=4,
                    annotation_name=f"{band_labels[band]} band post-saturation gain")

    # Mode tab
    device.add_tab(f"mode_{band}", f"Mode {band_labels[band]}",
                   [bx + 2, 126, 74, 20],
                   options=["TAPE", "TUBE", "CLIP", "OFF"],
                   bgcolor=[0.10, 0.10, 0.12, 1.0],
                   bgoncolor=tab_colors[band],
                   textcolor=[0.55, 0.55, 0.55, 1.0],
                   textoncolor=[1.0, 1.0, 1.0, 1.0])

    # +1 offset: live.tab outputs 0-indexed, selector~ needs 1-indexed
    device.add_newobj(f"tab_off_{band}", "+ 1",
                      numinlets=2, numoutlets=1,
                      outlettype=["int"],
                      patching_rect=[200, 300, 36, 20])

# -------------------------------------------------------------------
# DSP objects: crossovers
# cross~ freq  (2in: signal, freq_hz / 2out: LP=0, HP=1)
# Need 4 cross~ total: 2 crossover points x 2 channels
# -------------------------------------------------------------------

# Low crossover (splits signal into LOW and MID+HIGH)
device.add_newobj("cross_low_l", "cross~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[50, 250, 55, 20])

device.add_newobj("cross_low_r", "cross~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[120, 250, 55, 20])

# High crossover (splits HP-of-low into MID and HIGH)
device.add_newobj("cross_high_l", "cross~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[200, 250, 55, 20])

device.add_newobj("cross_high_r", "cross~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[270, 250, 55, 20])

# -------------------------------------------------------------------
# Parameter smoothing: crossover frequencies
# low_xover → lox_pk → lox_ln → cross_low_l/r inlet 1
# high_xover → hix_pk → hix_ln → cross_high_l/r inlet 1
# -------------------------------------------------------------------
device.add_newobj("lox_pk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[50, 215, 60, 20])
device.add_newobj("lox_ln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[50, 235, 40, 20])

device.add_newobj("hix_pk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[200, 215, 60, 20])
device.add_newobj("hix_ln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[200, 235, 40, 20])

# -------------------------------------------------------------------
# Per-band, per-channel DSP: drive *~, sat modes, selector~, gain *~
# Bands: low, mid, high  |  Channels: l, r
# -------------------------------------------------------------------

# Layout: place DSP objects in a grid below the crossovers
dsp_base_y = 310
band_dsp_x = {"low": 50, "mid": 250, "high": 450}
ch_offset_x = {"l": 0, "r": 80}

for band in ["low", "mid", "high"]:
    bx = band_dsp_x[band]

    for ch in ["l", "r"]:
        cx = bx + ch_offset_x[ch]

        # Drive: *~ 1.  (pre-saturation gain, inlet 1 receives smoothed signal)
        device.add_newobj(f"drv_{band}_{ch}", "*~ 1.",
                          numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y, 36, 20])

        # Saturation modes (4 options fed into selector~)
        # 1: tanh~  (tape)
        device.add_newobj(f"tanh_{band}_{ch}", "tanh~",
                          numinlets=1, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y + 30, 36, 20])

        # 2: overdrive~  (tube)
        device.add_newobj(f"od_{band}_{ch}", "overdrive~",
                          numinlets=1, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y + 55, 36, 20])

        # 3: clip~ -1. 1.  (hard clip)
        device.add_newobj(f"clip_{band}_{ch}", "clip~ -1. 1.",
                          numinlets=3, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y + 80, 36, 20])

        # 4: *~ 1.  (bypass — pass-through)
        device.add_newobj(f"byp_{band}_{ch}", "*~ 1.",
                          numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y + 105, 36, 20])

        # selector~ 4 1  (4 inputs, init=1)
        # 5 inlets: int (0) + 4 signal inputs (1-4); 1 outlet
        device.add_newobj(f"sel_{band}_{ch}", "selector~ 4 1",
                          numinlets=5, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y + 135, 60, 20])

        # Band gain: *~ 1.  (post-saturation level, inlet 1 receives smoothed signal)
        device.add_newobj(f"bndg_{band}_{ch}", "*~ 1.",
                          numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[cx, dsp_base_y + 165, 36, 20])

# -------------------------------------------------------------------
# Parameter smoothing: per-band drive and gain dials
# drive_{band} → drv_{band}_sc (0-100 -> 0.5-8) → drv_{band}_pk → drv_{band}_ln
# gain_{band}  → bndg_{band}_dbtoa → bndg_{band}_pk → bndg_{band}_ln
# -------------------------------------------------------------------
smooth_y_base = 490
for i, band in enumerate(["low", "mid", "high"]):
    bx = band_dsp_x[band]
    sy = smooth_y_base + i * 60   # stagger vertically to avoid overlap

    # Drive: map 0-100% display value to 0.5-8.0 internal multiplier
    device.add_newobj(f"drv_{band}_sc", "scale 0. 100. 0.5 8.",
                      numinlets=6, numoutlets=1,
                      outlettype=[""],
                      patching_rect=[bx, sy - 25, 120, 20])

    # Drive smoothing
    device.add_newobj(f"drv_{band}_pk", "pack f 20",
                      numinlets=2, numoutlets=1,
                      outlettype=[""],
                      patching_rect=[bx, sy, 60, 20])
    device.add_newobj(f"drv_{band}_ln", "line~",
                      numinlets=2, numoutlets=2,
                      outlettype=["signal", "bang"],
                      patching_rect=[bx, sy + 25, 40, 20])

    # Gain: convert dB to linear amplitude before smoothing
    device.add_newobj(f"bndg_{band}_dbtoa", "dbtoa",
                      numinlets=1, numoutlets=1,
                      outlettype=[""],
                      patching_rect=[bx + 70, sy - 25, 45, 20])

    # Gain smoothing
    device.add_newobj(f"bndg_{band}_pk", "pack f 20",
                      numinlets=2, numoutlets=1,
                      outlettype=[""],
                      patching_rect=[bx + 70, sy, 60, 20])
    device.add_newobj(f"bndg_{band}_ln", "line~",
                      numinlets=2, numoutlets=2,
                      outlettype=["signal", "bang"],
                      patching_rect=[bx + 70, sy + 25, 40, 20])

# -------------------------------------------------------------------
# Band summing: low + mid + high for each channel
# First sum: low + mid → then + high
# -------------------------------------------------------------------

# Left channel sums
device.add_newobj("sum_lm_l", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 600, 36, 20])

device.add_newobj("sum_lmh_l", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 630, 36, 20])

# Right channel sums
device.add_newobj("sum_lm_r", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[160, 600, 36, 20])

device.add_newobj("sum_lmh_r", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[160, 630, 36, 20])

# -------------------------------------------------------------------
# DC block: biquad~ 1. -1. 0. -0.9997 0.
# (6 inlets: signal + 5 coefficients; 1 outlet)
# Apply post-saturation on L and R
# -------------------------------------------------------------------
device.add_newobj("dcblock_l", "biquad~ 1. -1. 0. -0.9997 0.",
                  numinlets=6, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 670, 100, 20])

device.add_newobj("dcblock_r", "biquad~ 1. -1. 0. -0.9997 0.",
                  numinlets=6, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[220, 670, 100, 20])

# -------------------------------------------------------------------
# Dry/wet mix
# Scale: dial 0-100 → 0.0-1.0
# Smoothed via pack/line~ — line~ output (signal) goes directly to
# wet_l/wet_r inlet 1, and mix_inv inlet 0.
# -------------------------------------------------------------------
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.",
                  numinlets=6, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[600, 60, 120, 20])

# Smoothing for mix
device.add_newobj("mix_pk", "pack f 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[600, 85, 60, 20])
device.add_newobj("mix_ln", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[600, 110, 40, 20])

# !-~ 1. gives (1.0 - mix) for dry
device.add_newobj("mix_inv", "!-~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[600, 135, 45, 20])

# Wet multipliers
device.add_newobj("wet_l", "*~ 0.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 710, 36, 20])

device.add_newobj("wet_r", "*~ 0.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[160, 710, 36, 20])

# Dry multipliers
device.add_newobj("dry_l", "*~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[240, 710, 36, 20])

device.add_newobj("dry_r", "*~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[290, 710, 36, 20])

# Final sum: wet + dry
device.add_newobj("out_l", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 750, 36, 20])

device.add_newobj("out_r", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[160, 750, 36, 20])

# -------------------------------------------------------------------
# CONNECTIONS
# -------------------------------------------------------------------

# 1. Audio input → crossovers
device.add_line("obj-plugin", 0, "cross_low_l", 0)   # plugin~ L → low cross L
device.add_line("obj-plugin", 1, "cross_low_r", 0)   # plugin~ R → low cross R

# Low crossover frequency: dial → pack → line~ → cross~ inlet 1 (signal)
device.add_line("low_xover", 0, "lox_pk", 0)
device.add_line("lox_pk", 0, "lox_ln", 0)
device.add_line("lox_ln", 0, "cross_low_l", 1)
device.add_line("lox_ln", 0, "cross_low_r", 1)

# cross_low HP outlet → high crossover
device.add_line("cross_low_l", 1, "cross_high_l", 0)  # LP=0, HP=1
device.add_line("cross_low_r", 1, "cross_high_r", 0)

# High crossover frequency: dial → pack → line~ → cross~ inlet 1 (signal)
device.add_line("high_xover", 0, "hix_pk", 0)
device.add_line("hix_pk", 0, "hix_ln", 0)
device.add_line("hix_ln", 0, "cross_high_l", 1)
device.add_line("hix_ln", 0, "cross_high_r", 1)

# 2. Crossover outputs → band drive *~ inputs
# LOW band: cross_low LP outlet (0) → drive
device.add_line("cross_low_l", 0, "drv_low_l", 0)
device.add_line("cross_low_r", 0, "drv_low_r", 0)

# MID band: cross_high LP outlet (0) → drive
device.add_line("cross_high_l", 0, "drv_mid_l", 0)
device.add_line("cross_high_r", 0, "drv_mid_r", 0)

# HIGH band: cross_high HP outlet (1) → drive
device.add_line("cross_high_l", 1, "drv_high_l", 0)
device.add_line("cross_high_r", 1, "drv_high_r", 0)

# 3. Drive dials → scale (0-100->0.5-8) → smoothing → drive *~ inlet 1 (signal from line~)
for band in ["low", "mid", "high"]:
    device.add_line(f"drive_{band}", 0, f"drv_{band}_sc", 0)
    device.add_line(f"drv_{band}_sc", 0, f"drv_{band}_pk", 0)
    device.add_line(f"drv_{band}_pk", 0, f"drv_{band}_ln", 0)
    device.add_line(f"drv_{band}_ln", 0, f"drv_{band}_l", 1)
    device.add_line(f"drv_{band}_ln", 0, f"drv_{band}_r", 1)

# 4. drive *~ → all 4 saturation modes (fan out)
for band in ["low", "mid", "high"]:
    for ch in ["l", "r"]:
        device.add_line(f"drv_{band}_{ch}", 0, f"tanh_{band}_{ch}", 0)
        device.add_line(f"drv_{band}_{ch}", 0, f"od_{band}_{ch}", 0)
        device.add_line(f"drv_{band}_{ch}", 0, f"clip_{band}_{ch}", 0)
        device.add_line(f"drv_{band}_{ch}", 0, f"byp_{band}_{ch}", 0)

# 5. Saturation modes → selector~ signal inlets (1-4)
for band in ["low", "mid", "high"]:
    for ch in ["l", "r"]:
        device.add_line(f"tanh_{band}_{ch}", 0, f"sel_{band}_{ch}", 1)  # mode 1: TAPE
        device.add_line(f"od_{band}_{ch}",   0, f"sel_{band}_{ch}", 2)  # mode 2: TUBE
        device.add_line(f"clip_{band}_{ch}", 0, f"sel_{band}_{ch}", 3)  # mode 3: CLIP
        device.add_line(f"byp_{band}_{ch}",  0, f"sel_{band}_{ch}", 4)  # mode 4: OFF

# 6. Mode tabs → +1 offset → selector~ int inlet (0)
# One selector per band shared across L/R channels (same mode for both)
for band in ["low", "mid", "high"]:
    device.add_line(f"mode_{band}", 0, f"tab_off_{band}", 0)
    device.add_line(f"tab_off_{band}", 0, f"sel_{band}_l", 0)
    device.add_line(f"tab_off_{band}", 0, f"sel_{band}_r", 0)

# 7. selector~ → band gain *~ (inlet 0 = signal)
for band in ["low", "mid", "high"]:
    for ch in ["l", "r"]:
        device.add_line(f"sel_{band}_{ch}", 0, f"bndg_{band}_{ch}", 0)

# 8. Gain dials → dbtoa → smoothing → band gain *~ inlet 1 (signal from line~)
for band in ["low", "mid", "high"]:
    device.add_line(f"gain_{band}", 0, f"bndg_{band}_dbtoa", 0)
    device.add_line(f"bndg_{band}_dbtoa", 0, f"bndg_{band}_pk", 0)
    device.add_line(f"bndg_{band}_pk", 0, f"bndg_{band}_ln", 0)
    device.add_line(f"bndg_{band}_ln", 0, f"bndg_{band}_l", 1)
    device.add_line(f"bndg_{band}_ln", 0, f"bndg_{band}_r", 1)

# 9. Band sums: low + mid + high for L and R
# Left: bndg_low_l + bndg_mid_l → sum_lm_l → + bndg_high_l → sum_lmh_l
device.add_line("bndg_low_l",  0, "sum_lm_l", 0)
device.add_line("bndg_mid_l",  0, "sum_lm_l", 1)
device.add_line("sum_lm_l",    0, "sum_lmh_l", 0)
device.add_line("bndg_high_l", 0, "sum_lmh_l", 1)

# Right: bndg_low_r + bndg_mid_r → sum_lm_r → + bndg_high_r → sum_lmh_r
device.add_line("bndg_low_r",  0, "sum_lm_r", 0)
device.add_line("bndg_mid_r",  0, "sum_lm_r", 1)
device.add_line("sum_lm_r",    0, "sum_lmh_r", 0)
device.add_line("bndg_high_r", 0, "sum_lmh_r", 1)

# 10. DC block post-saturation
device.add_line("sum_lmh_l", 0, "dcblock_l", 0)
device.add_line("sum_lmh_r", 0, "dcblock_r", 0)

# 11. Dry/wet mix with smoothing
# dial → scale → pack → line~ (signal) → wet multipliers and dry inverter
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_pk", 0)
device.add_line("mix_pk", 0, "mix_ln", 0)
# mix_ln (signal) → wet_l inlet 1, wet_r inlet 1, mix_inv inlet 0
device.add_line("mix_ln", 0, "wet_l", 1)
device.add_line("mix_ln", 0, "wet_r", 1)
device.add_line("mix_ln", 0, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

# Wet signal: dc-blocked processed signal → wet multipliers
device.add_line("dcblock_l", 0, "wet_l", 0)
device.add_line("dcblock_r", 0, "wet_r", 0)

# Dry signal: unprocessed input → dry multipliers
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Sum wet + dry → output
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# Output
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# Output meters: tap final output
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

# Output scope: show the saturated mix
device.add_line("out_l", 0, "out_scope", 0)

# -------------------------------------------------------------------
# Build
# -------------------------------------------------------------------
output = device_output_path("Multiband Saturator", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
