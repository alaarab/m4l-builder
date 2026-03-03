"""Stereo Utility effect — gain, pan, width (M/S), phase invert, mono."""

import os
from m4l_builder import AudioEffect, COOL

# Device dimensions: ~250 wide, 140 tall
W, H = 250, 140
W, H = 350, 170
device = AudioEffect("Stereo Utility", width=W, height=H, theme=COOL)

# ── UI ──────────────────────────────────────────────────────────────────────

# Background panel (dark)
device.add_panel("bg", [0, 0, W, H], bgcolor=[0.12, 0.12, 0.14, 1.0])

# Title
device.add_comment("title", [8, 6, 60, 16], "UTIL",
                    textcolor=[0.9, 0.85, 0.75, 1.0], fontsize=13.0)

# Hero display: Lissajous vectorscope (live.scope~ in XY mode)
# L signal on X axis, R on Y — shows stereo field
device.add_scope("vectorscope", [235, 6, 108, 108],
                 bgcolor=[0.06, 0.06, 0.08, 1.0],
                 activelinecolor=[0.35, 0.60, 0.90, 0.7],
                 gridcolor=[0.15, 0.15, 0.17, 0.3],
                 range_vals=[-1.0, 1.0],
                 calccount=32, smooth=2, line_width=1.0,
                 decay_time=80)
device.add_comment("lbl_scope", [252, 116, 80, 10], "STEREO FIELD",
                    textcolor=[0.45, 0.45, 0.50, 1.0], fontsize=7.0,
                    justification=1)

# Stereo output meters — updated colors per spec
device.add_meter("meter_l", [220, 10, 6, 100],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [228, 10, 6, 100],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# Section labels above dial groups
device.add_comment("lbl_level", [15, 12, 60, 12], "LEVEL",
                    fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])
device.add_comment("lbl_stereo", [80, 12, 125, 12], "STEREO",
                    fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

# Dials row: Gain | Pan | Width
device.add_dial("dial_gain", "Gain", [15, 22, 60, 60],
                min_val=0.0, max_val=200.0, initial=100.0, shortname="Gain",
                unitstyle=5,
                annotation_name="Output gain — 100% = unity, 200% = +6dB")
device.add_dial("dial_pan", "Pan", [80, 22, 60, 60],
                min_val=-100.0, max_val=100.0, initial=0.0, shortname="Pan",
                unitstyle=5,
                annotation_name="Stereo pan — negative = left, positive = right")
device.add_dial("dial_width", "Width", [145, 22, 60, 60],
                min_val=0.0, max_val=200.0, initial=100.0, shortname="Width",
                unitstyle=5,
                annotation_name="Stereo width via M/S — 0% = mono, 100% = natural, 200% = wide")

# Labels under dials
device.add_comment("lbl_gain",  [15, 84, 60, 14], "GAIN",
                    textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                    justification=1)
device.add_comment("lbl_pan",   [80, 84, 60, 14], "PAN",
                    textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                    justification=1)
device.add_comment("lbl_width", [145, 84, 60, 14], "WIDTH",
                    textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=9.0,
                    justification=1)

# Section label above toggles
device.add_comment("lbl_routing", [20, 96, 190, 12], "ROUTING",
                    fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

# Toggles row: Phase L | Phase R | Mono
device.add_toggle("tog_phase_l", "Phase L", [30, 105, 20, 20],
                   shortname="Ph L", labels=("Normal", "Inverted"))
device.add_toggle("tog_phase_r", "Phase R", [100, 105, 20, 20],
                   shortname="Ph R", labels=("Normal", "Inverted"))
device.add_toggle("tog_mono", "Mono", [170, 105, 20, 20],
                   shortname="Mono", labels=("Stereo", "Mono"))

# Toggle labels
device.add_comment("lbl_phl",  [20, 127, 40, 12], "PH L",
                    textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5,
                    justification=1)
device.add_comment("lbl_phr",  [90, 127, 40, 12], "PH R",
                    textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5,
                    justification=1)
device.add_comment("lbl_mono", [158, 127, 40, 12], "MONO",
                    textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5,
                    justification=1)

# ── DSP ─────────────────────────────────────────────────────────────────────
# plugin~ (obj-plugin) and plugout~ (obj-plugout) are auto-added.
#
# Signal flow (per channel where applicable):
#   plugin~ → phase_sel~ → [M/S encode → width → M/S decode] → pan → gain
#           → mono_sel~ → plugout~
#
# Layout uses x=30..200 for L, x=450..620 for R in patching view.

# ── Phase invert (L) ───────────────────────────────────────────────────────
# Invert: *~ -1.
# selector~ 2 1: inlet 0 = int select, inlet 1 = signal input 1 (direct),
#                inlet 2 = signal input 2 (inverted). Initial=1 = passthrough.
device.add_newobj("ph_inv_l", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 70, 50, 20])
device.add_newobj("ph_sel_l", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 100, 80, 20])
# +1 converts toggle 0/1 to selector 1/2
device.add_newobj("ph_add1_l", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 55, 35, 20])

# ── Phase invert (R) ───────────────────────────────────────────────────────
device.add_newobj("ph_inv_r", "*~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 70, 50, 20])
device.add_newobj("ph_sel_r", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[450, 100, 80, 20])
device.add_newobj("ph_add1_r", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[450, 55, 35, 20])

# ── M/S encode ────────────────────────────────────────────────────────────
# mid = (L + R) * 0.5, side = (L - R) * 0.5
device.add_newobj("ms_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 140, 30, 20])
device.add_newobj("ms_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 140, 30, 20])
device.add_newobj("ms_mid", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 170, 50, 20])
device.add_newobj("ms_side", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 170, 50, 20])

# ── Width control ─────────────────────────────────────────────────────────
# Multiply side by width factor (0.0–2.0). Signal inlet via line~.
device.add_newobj("width_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 200, 40, 20])
# Scale: Width dial 0–200 → 0.0–2.0
device.add_newobj("width_scale", "scale 0. 200. 0. 2.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[240, 230, 110, 20])

# ── Parameter smoothing: width ───────────────────────────────────────────
# width_scale -> width_pk -> width_ln -> width_mul inlet 1
device.add_newobj("width_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[240, 260, 60, 20])
device.add_newobj("width_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[240, 290, 40, 20])

# ── M/S decode ────────────────────────────────────────────────────────────
# L = mid + side, R = mid - side
device.add_newobj("dec_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 320, 30, 20])
device.add_newobj("dec_sub", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 320, 30, 20])

# ── Pan ───────────────────────────────────────────────────────────────────
# Pan dial: -100..100. Center (0) → both gains = 1.0.
# L gain = (1 - pan_norm) * 2 where pan_norm = scale(-100..100 -> 0..1)
# Center (0): pan_norm=0.5 → 1 - 0.5 = 0.5 → * 2 = 1.0  ✓
# Hard left (-100): pan_norm=0 → 1 - 0 = 1 → * 2 = 2.0 (L boosted)
# Hard right (+100): pan_norm=1 → 1 - 1 = 0 → * 2 = 0.0 (L muted)
# R gain = pan_norm * 2
# Center: 0.5 * 2 = 1.0  ✓. Hard left: 0 * 2 = 0.0. Hard right: 1 * 2 = 2.0.
device.add_newobj("pan_norm", "scale -100. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 300, 120, 20])
# L gain: (1 - pan_norm) * 2. Use !- 1. then * 2.
device.add_newobj("pan_inv_l", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 330, 45, 20])
device.add_newobj("pan_gain_l", "* 2.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 360, 40, 20])
# R gain: pan_norm * 2
device.add_newobj("pan_gain_r", "* 2.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[240, 330, 40, 20])

# ── Parameter smoothing: pan L ───────────────────────────────────────────
# pan_gain_l -> pan_l_pk -> pan_l_ln -> pan_sig_l inlet 1
device.add_newobj("pan_l_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 385, 60, 20])
device.add_newobj("pan_l_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 415, 40, 20])

# ── Parameter smoothing: pan R ───────────────────────────────────────────
# pan_gain_r -> pan_r_pk -> pan_r_ln -> pan_sig_r inlet 1
device.add_newobj("pan_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[240, 355, 60, 20])
device.add_newobj("pan_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[240, 385, 40, 20])

# ── Post-pan signal gain (L and R) ────────────────────────────────────────
device.add_newobj("pan_sig_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 445, 40, 20])
device.add_newobj("pan_sig_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 415, 40, 20])

# ── Output gain ───────────────────────────────────────────────────────────
device.add_newobj("gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 490, 40, 20])
device.add_newobj("gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 490, 40, 20])
# Scale: Gain dial 0–200 → 0.0–2.0
device.add_newobj("gain_scale", "scale 0. 200. 0. 2.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[140, 460, 110, 20])

# ── Parameter smoothing: output gain ─────────────────────────────────────
# gain_scale -> gain_pk -> gain_ln -> gain_l/gain_r inlet 1
device.add_newobj("gain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[140, 490, 60, 20])
device.add_newobj("gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[140, 520, 40, 20])

# ── Mono ──────────────────────────────────────────────────────────────────
# Sum L+R, scale by 0.5 for mid
device.add_newobj("mono_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 540, 30, 20])
device.add_newobj("mono_half", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 570, 50, 20])
# selector~ 2 1: input 1 = stereo (original L/R), input 2 = mono (mid sent to both)
device.add_newobj("mono_sel_l", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 600, 80, 20])
device.add_newobj("mono_sel_r", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 600, 80, 20])
device.add_newobj("mono_add1", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[140, 525, 35, 20])

# ── Wiring ───────────────────────────────────────────────────────────────

# Phase L: plugin~ L → ph_inv_l and ph_sel_l inlet 1 (direct)
device.add_line("obj-plugin", 0, "ph_inv_l", 0)      # L signal → inverter
device.add_line("obj-plugin", 0, "ph_sel_l", 1)      # L signal → sel input 1
device.add_line("ph_inv_l", 0, "ph_sel_l", 2)        # inverted → sel input 2
device.add_line("tog_phase_l", 0, "ph_add1_l", 0)    # toggle 0/1 → +1
device.add_line("ph_add1_l", 0, "ph_sel_l", 0)       # 1/2 → sel int inlet

# Phase R: plugin~ R → ph_inv_r and ph_sel_r inlet 1
device.add_line("obj-plugin", 1, "ph_inv_r", 0)
device.add_line("obj-plugin", 1, "ph_sel_r", 1)
device.add_line("ph_inv_r", 0, "ph_sel_r", 2)
device.add_line("tog_phase_r", 0, "ph_add1_r", 0)
device.add_line("ph_add1_r", 0, "ph_sel_r", 0)

# M/S encode: ph_sel_l/r → ms_add and ms_sub
device.add_line("ph_sel_l", 0, "ms_add", 0)          # L → sum inlet 0
device.add_line("ph_sel_r", 0, "ms_add", 1)          # R → sum inlet 1
device.add_line("ph_sel_l", 0, "ms_sub", 0)          # L → diff inlet 0
device.add_line("ph_sel_r", 0, "ms_sub", 1)          # R → diff inlet 1
device.add_line("ms_add", 0, "ms_mid", 0)            # sum → *0.5 mid
device.add_line("ms_sub", 0, "ms_side", 0)           # diff → *0.5 side

# Width smoothing: dial → scale → pack → line~ → width_mul inlet 1 (signal)
device.add_line("dial_width", 0, "width_scale", 0)
device.add_line("width_scale", 0, "width_pk", 0)
device.add_line("width_pk", 0, "width_ln", 0)
device.add_line("width_ln", 0, "width_mul", 1)       # smoothed signal → *~ inlet 1
device.add_line("ms_side", 0, "width_mul", 0)        # side signal → *~ inlet 0

# M/S decode: mid + side_w → L; mid - side_w → R
device.add_line("ms_mid", 0, "dec_add", 0)           # mid → + inlet 0
device.add_line("width_mul", 0, "dec_add", 1)        # side_w → + inlet 1
device.add_line("ms_mid", 0, "dec_sub", 0)           # mid → - inlet 0
device.add_line("width_mul", 0, "dec_sub", 1)        # side_w → - inlet 1

# Pan: dial → normalize → L and R gain floats → smoothing → pan_sig
device.add_line("dial_pan", 0, "pan_norm", 0)
device.add_line("pan_norm", 0, "pan_inv_l", 0)       # pan_norm → !- 1.
device.add_line("pan_inv_l", 0, "pan_gain_l", 0)     # (1-pan) → * 2

# Pan L smoothing: pan_gain_l -> pack -> line~ -> pan_sig_l inlet 1
device.add_line("pan_gain_l", 0, "pan_l_pk", 0)
device.add_line("pan_l_pk", 0, "pan_l_ln", 0)
device.add_line("pan_l_ln", 0, "pan_sig_l", 1)

device.add_line("pan_norm", 0, "pan_gain_r", 0)      # pan_norm → * 2

# Pan R smoothing: pan_gain_r -> pack -> line~ -> pan_sig_r inlet 1
device.add_line("pan_gain_r", 0, "pan_r_pk", 0)
device.add_line("pan_r_pk", 0, "pan_r_ln", 0)
device.add_line("pan_r_ln", 0, "pan_sig_r", 1)

# Apply pan to decoded L/R signals (signal inlet 0)
device.add_line("dec_add", 0, "pan_sig_l", 0)        # decoded L → *~ inlet 0
device.add_line("dec_sub", 0, "pan_sig_r", 0)        # decoded R → *~ inlet 0

# Gain smoothing: dial → scale → pack → line~ → gain_l/gain_r inlet 1
device.add_line("dial_gain", 0, "gain_scale", 0)
device.add_line("gain_scale", 0, "gain_pk", 0)
device.add_line("gain_pk", 0, "gain_ln", 0)
device.add_line("gain_ln", 0, "gain_l", 1)           # smoothed signal → *~ inlet 1
device.add_line("gain_ln", 0, "gain_r", 1)

device.add_line("pan_sig_l", 0, "gain_l", 0)
device.add_line("pan_sig_r", 0, "gain_r", 0)

# Mono sum: gain_l/r → mono_sum → *0.5 → mono_half
device.add_line("gain_l", 0, "mono_sum", 0)
device.add_line("gain_r", 0, "mono_sum", 1)
device.add_line("mono_sum", 0, "mono_half", 0)

# Mono selector control
device.add_line("tog_mono", 0, "mono_add1", 0)       # toggle → +1
device.add_line("mono_add1", 0, "mono_sel_l", 0)     # 1/2 → sel int (L)
device.add_line("mono_add1", 0, "mono_sel_r", 0)     # 1/2 → sel int (R)

# Mono selector inputs
device.add_line("gain_l", 0, "mono_sel_l", 1)        # stereo L → input 1
device.add_line("mono_half", 0, "mono_sel_l", 2)     # mono mid → input 2
device.add_line("gain_r", 0, "mono_sel_r", 1)        # stereo R → input 1
device.add_line("mono_half", 0, "mono_sel_r", 2)     # mono mid → input 2

# Output to plugout~
device.add_line("mono_sel_l", 0, "obj-plugout", 0)
device.add_line("mono_sel_r", 0, "obj-plugout", 1)

# Vectorscope: L -> X axis (inlet 0), R -> Y axis (inlet 1)
device.add_line("mono_sel_l", 0, "vectorscope", 0)
device.add_line("mono_sel_r", 0, "vectorscope", 1)

# Output meters (from final output stage before plugout~)
device.add_line("mono_sel_l", 0, "meter_l", 0)
device.add_line("mono_sel_r", 0, "meter_r", 0)

# ── Build ────────────────────────────────────────────────────────────────

output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Stereo Utility.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
