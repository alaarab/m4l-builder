"""Resonant Comb Bank — 4 parallel tuned comb filters for pitched metallic resonance.

Signal flow:
  plugin~ L/R
    -> svf~ highpass (outlet 1) — removes low rumble
    -> 4x comb~ 50 in parallel (per channel)
    -> sum all 4 comb outputs per channel via +~ chain
    -> onepole~ damping per channel
    -> dry/wet mix
    -> plugout~

Pitch / chord:
  root_note dial (MIDI 24-96) -> 4 note offsets based on chord tab
  Each MIDI note -> mtof -> expr 1000./$f1 -> comb~ delay_ms inlet (1)

Chord modes (live.tab):
  UNI: all 4 voices at root
  OCT: root, +12, +24, +36
  5TH: root, +7, +12, +19
  MAJ: root, +4, +7, +12
  MIN: root, +3, +7, +12

comb~ 50 inlets:
  0 = signal
  1 = delay_ms (float)
  2 = a_gain (overall gain, leave 1.0)
  3 = b_ff (feedforward gain, leave 0.0)
  4 = c_fb (feedback 0.0-0.99, NEVER >= 1.0)

Feedback is clipped to 0.99 max via clip object.

Parameter smoothing:
  hp_dial -> pack -> line~ -> svf~ cutoff (L and R)
  damp_dial -> pack -> line~ -> onepole~ cutoff (L and R)
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path

# --- Device setup --- widened 30px for L/R output meters
device = AudioEffect("Comb Resonator", width=330, height=195, theme=MIDNIGHT)

# --- UI ---
device.add_panel("bg", [0, 0, 330, 195], bgcolor=[0.10, 0.10, 0.12, 1.0])

# Title
device.add_comment("title", [8, 5, 100, 16], "RESONATOR",
                   textcolor=[0.95, 0.88, 0.70, 1.0], fontsize=13.0)

# Resonance output scope — shows the resonating waveform
device.add_scope("res_scope", [8, 24, 284, 42],
                 bgcolor=[0.06, 0.06, 0.08, 1.0],
                 activelinecolor=[0.55, 0.35, 0.75, 1.0],
                 gridcolor=[0.15, 0.15, 0.17, 0.4],
                 range_vals=[-1.0, 1.0],
                 calccount=64, smooth=2, line_width=1.5)

# Chord tab: UNI / OCT / 5TH / MAJ / MIN
device.add_tab("chord_tab", "Chord", [8, 70, 284, 20],
               options=["UNI", "OCT", "5TH", "MAJ", "MIN"],
               bgcolor=[0.18, 0.18, 0.20, 1.0],
               bgoncolor=[0.45, 0.30, 0.65, 1.0],
               textcolor=[0.75, 0.75, 0.75, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# Section labels
device.add_comment("lbl_tuning", [8, 90, 100, 12], "TUNING",
                   textcolor=[0.45, 0.75, 0.65, 0.6], fontsize=9.0)
device.add_comment("lbl_color", [112, 90, 100, 12], "COLOR",
                   textcolor=[0.45, 0.75, 0.65, 0.6], fontsize=9.0)
device.add_comment("lbl_output", [240, 90, 48, 12], "OUTPUT",
                   textcolor=[0.45, 0.75, 0.65, 0.6], fontsize=9.0)

# Dials row: Root / Resonance / Damping / HP Freq / Mix
device.add_dial("root_dial", "Root", [8, 100, 48, 82],
                min_val=24.0, max_val=96.0, initial=60.0,
                unitstyle=8,
                annotation_name="Root Note")  # MIDI note

device.add_dial("res_dial", "Resonance", [60, 100, 48, 82],
                min_val=0.0, max_val=99.0, initial=60.0,
                unitstyle=5,
                annotation_name="Comb Resonance")  # PERCENT

device.add_dial("damp_dial", "Damping", [112, 100, 48, 82],
                min_val=500.0, max_val=20000.0, initial=8000.0,
                unitstyle=3,
                annotation_name="Damping Frequency")  # HZ

device.add_dial("hp_dial", "HP Freq", [164, 100, 48, 82],
                min_val=20.0, max_val=500.0, initial=80.0,
                unitstyle=3,
                annotation_name="Input Highpass")  # HZ

device.add_dial("mix_dial", "Mix", [240, 100, 48, 82],
                min_val=0.0, max_val=100.0, initial=30.0,
                unitstyle=5,
                annotation_name="Dry/Wet Mix")  # PERCENT

# --- Output L/R meters (right edge) ---
device.add_comment("lbl_meters", [301, 90, 24, 12], "OUT",
                   textcolor=[0.45, 0.75, 0.65, 0.6], fontsize=9.0)
device.add_comment("lbl_meter_l", [301, 178, 12, 12], "L",
                   textcolor=[0.75, 0.75, 0.75, 1.0], fontsize=8.0)
device.add_meter("meter_out_l", [301, 100, 12, 76],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_comment("lbl_meter_r", [315, 178, 12, 12], "R",
                   textcolor=[0.75, 0.75, 0.75, 1.0], fontsize=8.0)
device.add_meter("meter_out_r", [315, 100, 12, 76],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# ============================================================
# DSP OBJECTS
# ============================================================

# --- Input HP filter (svf~ outlet 1 = HP) ---
# svf~ inlets: signal(0), cutoff_hz(1), resonance_0to1(2)
# svf~ outlets: LP(0), HP(1), BP(2), Notch(3)
device.add_newobj("hp_l", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[80, 220, 40, 20])
device.add_newobj("hp_r", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[200, 220, 40, 20])

# Smoothing for HP cutoff: hp_dial -> pack -> line~ -> svf_l and svf_r cutoff (inlet 1)
device.add_newobj("hp_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[140, 245, 60, 20])
device.add_newobj("hp_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[140, 275, 40, 20])
# t~ f f to fan smoothed HP freq to both L and R svf~ inlets
device.add_newobj("hp_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[140, 305, 40, 20])

# --- Chord offset computation ---
# We compute 4 MIDI note values from root + offsets for each chord mode.
# Strategy: use selector~ to choose between 5 chord sets per voice.
# Each voice needs 5 options (UNI/OCT/5TH/MAJ/MIN).
# We use int addition (+ offset) for each chord/voice combo,
# then selector (int) to pick the right offset per voice.
# Voice 0 = root (always offset 0)
# Voice 1 = UNI:0, OCT:12, 5TH:7,  MAJ:4,  MIN:3
# Voice 2 = UNI:0, OCT:24, 5TH:12, MAJ:7,  MIN:7
# Voice 3 = UNI:0, OCT:36, 5TH:19, MAJ:12, MIN:12

# root_dial -> t i i i i i to fan int to all voices and chord-dependent adders
# We need to deliver root int to multiple branches; use trigger
device.add_newobj("root_trig", "t i i i i i i i i",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[160, 280, 120, 20])

# chord_tab -> route to select chord mode per voice
# We'll use separate selector objects for voice 1, 2, 3 offsets.
# chord_tab output (0-4) -> +1 -> selector~ int inputs for each voice selector

# For voice 1 offsets:
device.add_newobj("v1_uni", "i 0", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[220, 330, 30, 20])
device.add_newobj("v1_oct", "i 12", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[255, 330, 30, 20])
device.add_newobj("v1_fif", "i 7", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 330, 30, 20])
device.add_newobj("v1_maj", "i 4", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[325, 330, 30, 20])
device.add_newobj("v1_min", "i 3", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 330, 30, 20])

# For voice 2 offsets:
device.add_newobj("v2_uni", "i 0", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[220, 360, 30, 20])
device.add_newobj("v2_oct", "i 24", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[255, 360, 30, 20])
device.add_newobj("v2_fif", "i 12", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 360, 30, 20])
device.add_newobj("v2_maj", "i 7", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[325, 360, 30, 20])
device.add_newobj("v2_min", "i 7", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 360, 30, 20])

# For voice 3 offsets:
device.add_newobj("v3_uni", "i 0", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[220, 390, 30, 20])
device.add_newobj("v3_oct", "i 36", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[255, 390, 30, 20])
device.add_newobj("v3_fif", "i 19", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 390, 30, 20])
device.add_newobj("v3_maj", "i 12", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[325, 390, 30, 20])
device.add_newobj("v3_min", "i 12", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 390, 30, 20])

# Chord selectors for voice 1, 2, 3 — select 1 of 5 int values
# Route message selectors: route 0 1 2 3 4 for chord mode, pick offset int
# Use "sel" (message selector) instead of selector~: route object
# Actually use: route 0 1 2 3 4 -> each outlet goes to one voice's offset int holder
# Then the selected offset + root -> note -> freq

# Better approach: use "selector" (non-signal) for int routing via "route"
# chord_tab -> route 0 1 2 3 4 -> each output triggers the correct i-object for each voice
# But route only works on symbols. Use "sel" for int matching.

# Simpler: use "expr" to compute offsets based on chord mode via "table" or arithmetic.
# Simplest: just use a "prepend" + "zl.reg" or "coll" -- but these require more complexity.
#
# Cleanest approach in Max: use separate trigger paths with "sel" matching chord mode,
# each chord mode bang triggers the voice offset integers being set.
# chord_tab -> sel 0 1 2 3 4, each outlet triggers a specific t for voice offsets
# voice offset -> + root -> mtof -> expr -> comb~ delay

# chord_tab -> sel 0 1 2 3 4 (5 outlets, one per chord mode)
device.add_newobj("chord_sel", "sel 0 1 2 3 4", numinlets=1, numoutlets=5,
                  outlettype=["", "", "", "", ""],
                  patching_rect=[160, 310, 80, 20])

# When chord mode changes, we need to output 3 offset values (v1, v2, v3).
# Each chord sel outlet -> t b b b to bang v1/v2/v3 offset objects
# UNI (mode 0) -> v1=0, v2=0, v3=0
device.add_newobj("uni_trig", "t b b b", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[160, 340, 50, 20])
# OCT (mode 1) -> v1=12, v2=24, v3=36
device.add_newobj("oct_trig", "t b b b", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[215, 340, 50, 20])
# 5TH (mode 2) -> v1=7, v2=12, v3=19
device.add_newobj("fif_trig", "t b b b", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[270, 340, 50, 20])
# MAJ (mode 3) -> v1=4, v2=7, v3=12
device.add_newobj("maj_trig", "t b b b", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[325, 340, 50, 20])
# MIN (mode 4) -> v1=3, v2=7, v3=12
device.add_newobj("min_trig", "t b b b", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[380, 340, 50, 20])

# Voice offset storage (int registers for v1, v2, v3)
# When bang arrives, they output their stored value to the + root chain
device.add_newobj("v1_off", "i 0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 420, 30, 20])
device.add_newobj("v2_off", "i 0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 420, 30, 20])
device.add_newobj("v3_off", "i 0", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[330, 420, 30, 20])

# Voice MIDI note adders: root + offset -> MIDI note
# voice 0 = root directly
# v1_midi = root + v1_off
# v2_midi = root + v2_off
# v3_midi = root + v3_off
device.add_newobj("v1_add", "+", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 460, 30, 20])
device.add_newobj("v2_add", "+", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 460, 30, 20])
device.add_newobj("v3_add", "+", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[330, 460, 30, 20])

# mtof: MIDI note -> Hz (one per voice, 4 total)
device.add_newobj("mtof0", "mtof", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[210, 500, 40, 20])
device.add_newobj("mtof1", "mtof", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 500, 40, 20])
device.add_newobj("mtof2", "mtof", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 500, 40, 20])
device.add_newobj("mtof3", "mtof", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[330, 500, 40, 20])

# Hz -> ms delay: expr 1000. / $f1
# delay_ms = 1000 / freq_hz
device.add_newobj("f2ms0", "expr 1000. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[210, 530, 90, 20])
device.add_newobj("f2ms1", "expr 1000. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[250, 530, 90, 20])
device.add_newobj("f2ms2", "expr 1000. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[290, 530, 90, 20])
device.add_newobj("f2ms3", "expr 1000. / $f1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[330, 530, 90, 20])

# fan delay_ms to L and R comb pairs
# t f f: outlet 0 -> L comb delay, outlet 1 -> R comb delay
device.add_newobj("dm0_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[210, 560, 40, 20])
device.add_newobj("dm1_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[250, 560, 40, 20])
device.add_newobj("dm2_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[290, 560, 40, 20])
device.add_newobj("dm3_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[330, 560, 40, 20])

# --- Feedback (resonance) ---
# res_dial 0-99 -> clip 0. 99. -> scale 0. 99. 0. 0.99 -> fb_trig -> all 8 comb~ fb inlets
device.add_newobj("fb_clip", "clip 0. 99.", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[430, 290, 60, 20])
device.add_newobj("fb_scale", "scale 0. 99. 0. 0.99", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[430, 315, 120, 20])
# fan feedback to all 8 comb~ (4 L + 4 R): t f f f f f f f f
device.add_newobj("fb_fan", "t f f f f f f f f", numinlets=1, numoutlets=8,
                  outlettype=["", "", "", "", "", "", "", ""],
                  patching_rect=[430, 340, 130, 20])

# --- 4x comb~ per channel ---
# comb~ 50: max 50ms buffer (down to ~20Hz)
# inlets: signal(0), delay_ms(1), a_gain(2), b_ff(3), c_fb(4)
# outlet: filtered signal

# Left channel combs
device.add_newobj("cl0", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 620, 55, 20])
device.add_newobj("cl1", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 620, 55, 20])
device.add_newobj("cl2", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 620, 55, 20])
device.add_newobj("cl3", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[260, 620, 55, 20])

# Right channel combs
device.add_newobj("cr0", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 660, 55, 20])
device.add_newobj("cr1", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 660, 55, 20])
device.add_newobj("cr2", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 660, 55, 20])
device.add_newobj("cr3", "comb~ 50", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[260, 660, 55, 20])

# Sum 4 comb outputs per channel: cl0+cl1 -> +~, cl01+cl2 -> +~, cl012+cl3 -> +~
device.add_newobj("sum_l01", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 700, 30, 20])
device.add_newobj("sum_l012", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 720, 30, 20])
device.add_newobj("sum_l0123", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 740, 30, 20])

device.add_newobj("sum_r01", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 700, 30, 20])
device.add_newobj("sum_r012", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 720, 30, 20])
device.add_newobj("sum_r0123", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 740, 30, 20])

# Damping: onepole~ per channel after summing
device.add_newobj("damp_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 780, 50, 20])
device.add_newobj("damp_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 780, 50, 20])

# Smoothing for damping cutoff: damp_dial -> pack -> line~ -> onepole~ (L and R)
device.add_newobj("damp_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[310, 780, 60, 20])
device.add_newobj("damp_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[310, 810, 40, 20])
# t~ f f to fan smoothed damp freq to both L and R onepole~ inlets
device.add_newobj("damp_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[310, 840, 40, 20])

# --- Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[570, 80, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[570, 105, 55, 20])
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[570, 130, 45, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 820, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 820, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[320, 820, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[360, 820, 30, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 860, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[280, 860, 30, 20])

# ============================================================
# CONNECTIONS
# ============================================================

# --- Input HP filter ---
device.add_line("obj-plugin", 0, "hp_l", 0)    # plugin L -> svf_l signal
device.add_line("obj-plugin", 1, "hp_r", 0)    # plugin R -> svf_r signal
# HP cutoff smoothing: hp_dial -> pack -> line~ -> fan -> svf_l and svf_r cutoff
device.add_line("hp_dial", 0, "hp_pk", 0)
device.add_line("hp_pk", 0, "hp_ln", 0)
device.add_line("hp_ln", 0, "hp_fan", 0)
device.add_line("hp_fan", 0, "hp_l", 1)        # smoothed HP freq -> svf_l cutoff
device.add_line("hp_fan", 1, "hp_r", 1)        # smoothed HP freq -> svf_r cutoff
# svf~ outlet 1 = HP; connect to all 4 comb~ signal inlets per channel
device.add_line("hp_l", 1, "cl0", 0)
device.add_line("hp_l", 1, "cl1", 0)
device.add_line("hp_l", 1, "cl2", 0)
device.add_line("hp_l", 1, "cl3", 0)
device.add_line("hp_r", 1, "cr0", 0)
device.add_line("hp_r", 1, "cr1", 0)
device.add_line("hp_r", 1, "cr2", 0)
device.add_line("hp_r", 1, "cr3", 0)

# --- Root note -> voice MIDI notes ---
# root_dial -> root_trig (fan to 9 outlets)
device.add_line("root_dial", 0, "root_trig", 0)
# outlet 0 -> voice 0 (root directly -> mtof0)
device.add_line("root_trig", 0, "mtof0", 0)
# outlet 1 -> v1_add left (hot)
device.add_line("root_trig", 1, "v1_add", 0)
# outlet 2 -> v2_add left (hot)
device.add_line("root_trig", 2, "v2_add", 0)
# outlet 3 -> v3_add left (hot)
device.add_line("root_trig", 3, "v3_add", 0)
# outlets 4-8 spare (needed to trigger recalculation when root changes)
# Actually we only need 4 outlets (one per voice), 5 total with the trig
# But we declared 9 -- use 4 (0-3 for voices 0,1,2,3) and also
# outlets 4,5,6 to re-bang v1/v2/v3 offset objects when root changes
device.add_line("root_trig", 4, "v1_off", 0)   # re-bang v1 offset to refresh
device.add_line("root_trig", 5, "v2_off", 0)   # re-bang v2 offset to refresh
device.add_line("root_trig", 6, "v3_off", 0)   # re-bang v3 offset to refresh

# voice add result -> mtof
device.add_line("v1_add", 0, "mtof1", 0)
device.add_line("v2_add", 0, "mtof2", 0)
device.add_line("v3_add", 0, "mtof3", 0)

# v1/v2/v3 offset -> v_add right inlet (cold -- sets value)
device.add_line("v1_off", 0, "v1_add", 1)
device.add_line("v2_off", 0, "v2_add", 1)
device.add_line("v3_off", 0, "v3_add", 1)

# --- Chord tab -> offset routing ---
device.add_line("chord_tab", 0, "chord_sel", 0)

# chord_sel outlets -> mode triggers
device.add_line("chord_sel", 0, "uni_trig", 0)
device.add_line("chord_sel", 1, "oct_trig", 0)
device.add_line("chord_sel", 2, "fif_trig", 0)
device.add_line("chord_sel", 3, "maj_trig", 0)
device.add_line("chord_sel", 4, "min_trig", 0)

# UNI mode (0,0,0): uni_trig bangs v1/v2/v3 UNI offset int objects
device.add_line("uni_trig", 0, "v1_uni", 0)    # bang -> i 0 outputs 0 -> v1_off right
device.add_line("uni_trig", 1, "v2_uni", 0)
device.add_line("uni_trig", 2, "v3_uni", 0)
device.add_line("v1_uni", 0, "v1_off", 1)      # i 0 -> v1_off set (right inlet)
device.add_line("v2_uni", 0, "v2_off", 1)
device.add_line("v3_uni", 0, "v3_off", 1)

# OCT mode (12,24,36)
device.add_line("oct_trig", 0, "v1_oct", 0)
device.add_line("oct_trig", 1, "v2_oct", 0)
device.add_line("oct_trig", 2, "v3_oct", 0)
device.add_line("v1_oct", 0, "v1_off", 1)
device.add_line("v2_oct", 0, "v2_off", 1)
device.add_line("v3_oct", 0, "v3_off", 1)

# 5TH mode (7,12,19)
device.add_line("fif_trig", 0, "v1_fif", 0)
device.add_line("fif_trig", 1, "v2_fif", 0)
device.add_line("fif_trig", 2, "v3_fif", 0)
device.add_line("v1_fif", 0, "v1_off", 1)
device.add_line("v2_fif", 0, "v2_off", 1)
device.add_line("v3_fif", 0, "v3_off", 1)

# MAJ mode (4,7,12)
device.add_line("maj_trig", 0, "v1_maj", 0)
device.add_line("maj_trig", 1, "v2_maj", 0)
device.add_line("maj_trig", 2, "v3_maj", 0)
device.add_line("v1_maj", 0, "v1_off", 1)
device.add_line("v2_maj", 0, "v2_off", 1)
device.add_line("v3_maj", 0, "v3_off", 1)

# MIN mode (3,7,12)
device.add_line("min_trig", 0, "v1_min", 0)
device.add_line("min_trig", 1, "v2_min", 0)
device.add_line("min_trig", 2, "v3_min", 0)
device.add_line("v1_min", 0, "v1_off", 1)
device.add_line("v2_min", 0, "v2_off", 1)
device.add_line("v3_min", 0, "v3_off", 1)

# --- Hz -> delay ms -> comb~ delay inlets ---
device.add_line("mtof0", 0, "f2ms0", 0)
device.add_line("mtof1", 0, "f2ms1", 0)
device.add_line("mtof2", 0, "f2ms2", 0)
device.add_line("mtof3", 0, "f2ms3", 0)

device.add_line("f2ms0", 0, "dm0_fan", 0)
device.add_line("f2ms1", 0, "dm1_fan", 0)
device.add_line("f2ms2", 0, "dm2_fan", 0)
device.add_line("f2ms3", 0, "dm3_fan", 0)

# dm_fan outlet 0 -> L comb delay inlet (1), outlet 1 -> R comb delay inlet (1)
device.add_line("dm0_fan", 0, "cl0", 1)
device.add_line("dm0_fan", 1, "cr0", 1)
device.add_line("dm1_fan", 0, "cl1", 1)
device.add_line("dm1_fan", 1, "cr1", 1)
device.add_line("dm2_fan", 0, "cl2", 1)
device.add_line("dm2_fan", 1, "cr2", 1)
device.add_line("dm3_fan", 0, "cl3", 1)
device.add_line("dm3_fan", 1, "cr3", 1)

# --- Feedback routing: res_dial -> clip -> scale -> fan -> comb~ c_fb (inlet 4) ---
device.add_line("res_dial", 0, "fb_clip", 0)
device.add_line("fb_clip", 0, "fb_scale", 0)
device.add_line("fb_scale", 0, "fb_fan", 0)
# fan outlets (0-7) -> L comb 0-3 fb (inlet 4), R comb 0-3 fb (inlet 4)
# t f f f f f f f f fires outlets right to left (7 first, 0 last)
device.add_line("fb_fan", 0, "cl0", 4)
device.add_line("fb_fan", 1, "cl1", 4)
device.add_line("fb_fan", 2, "cl2", 4)
device.add_line("fb_fan", 3, "cl3", 4)
device.add_line("fb_fan", 4, "cr0", 4)
device.add_line("fb_fan", 5, "cr1", 4)
device.add_line("fb_fan", 6, "cr2", 4)
device.add_line("fb_fan", 7, "cr3", 4)

# --- Sum 4 comb outputs per channel ---
# L: cl0 + cl1 -> sum_l01; sum_l01 + cl2 -> sum_l012; sum_l012 + cl3 -> sum_l0123
device.add_line("cl0", 0, "sum_l01", 0)
device.add_line("cl1", 0, "sum_l01", 1)
device.add_line("sum_l01", 0, "sum_l012", 0)
device.add_line("cl2", 0, "sum_l012", 1)
device.add_line("sum_l012", 0, "sum_l0123", 0)
device.add_line("cl3", 0, "sum_l0123", 1)

# R: same
device.add_line("cr0", 0, "sum_r01", 0)
device.add_line("cr1", 0, "sum_r01", 1)
device.add_line("sum_r01", 0, "sum_r012", 0)
device.add_line("cr2", 0, "sum_r012", 1)
device.add_line("sum_r012", 0, "sum_r0123", 0)
device.add_line("cr3", 0, "sum_r0123", 1)

# --- Damping: sum_l0123/sum_r0123 -> onepole~ -> wet multipliers ---
device.add_line("sum_l0123", 0, "damp_l", 0)
device.add_line("sum_r0123", 0, "damp_r", 0)
# Damping cutoff smoothing: damp_dial -> pack -> line~ -> fan -> onepole_l and onepole_r
device.add_line("damp_dial", 0, "damp_pk", 0)
device.add_line("damp_pk", 0, "damp_ln", 0)
device.add_line("damp_ln", 0, "damp_fan", 0)
device.add_line("damp_fan", 0, "damp_l", 1)    # smoothed damp freq -> onepole_l cutoff
device.add_line("damp_fan", 1, "damp_r", 1)    # smoothed damp freq -> onepole_r cutoff

# --- Dry/wet mix ---
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# t f f f: outlet 0 -> wet_l gain, outlet 1 -> wet_r gain, outlet 2 -> inverter
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

# Wet: damp_l/r -> wet multipliers
device.add_line("damp_l", 0, "wet_l", 0)
device.add_line("damp_r", 0, "wet_r", 0)

# Dry: plugin~ -> dry multipliers
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Sum wet + dry -> output
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# Output -> plugout~
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# Resonance scope: show wet resonating waveform
device.add_line("damp_l", 0, "res_scope", 0)

# Output L/R meters: tap final output signals
device.add_line("out_l", 0, "meter_out_l", 0)
device.add_line("out_r", 0, "meter_out_r", 0)

# --- Build ---
output = device_output_path("Comb Resonator")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
