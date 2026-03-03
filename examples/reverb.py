"""Algorithmic reverb — AudioEffect example.

Demonstrates: LIGHT theme (unused by any other example), add_tab for room type,
Schroeder-style reverb network.

Architecture: Schroeder reverb
  plugin~ → predelay (tapin~/tapout~)
  → split to 4 parallel comb filters (tapin~ + tapout~ + feedback *~ + onepole~ damping)
  → sum → 2 series allpass filters (delay~ with feedforward/feedback)
  → dry/wet mix → plugout~

Comb filter base delays (ms) scaled by Room Size:
  Comb 1: 29.7ms, Comb 2: 37.1ms, Comb 3: 41.1ms, Comb 4: 43.7ms

Allpass delays (fixed, not scaled):
  Allpass 1: 5.0ms, Allpass 2: 1.7ms

Room type tab adjusts comb delay ratios:
  ROOM: ratios [1.0, 1.25, 1.39, 1.47]
  HALL: ratios [1.5, 1.88, 2.07, 2.21]
  PLATE: ratios [0.7, 0.88, 0.97, 1.03]
"""

from m4l_builder import AudioEffect, LIGHT, device_output_path

WIDTH = 380
HEIGHT = 200
device = AudioEffect("Algorithmic Reverb", width=WIDTH, height=HEIGHT, theme=LIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])

device.add_comment("title", [8, 5, 80, 16], "REVERB",
                   fontname="Ableton Sans Bold", fontsize=12.0,
                   textcolor=[0.12, 0.12, 0.14, 1.0])

# Room type tab — switches comb delay ratios
device.add_tab("room_tab", "Room Type", [8, 22, 220, 20],
               options=["ROOM", "HALL", "PLATE"],
               rounded=3.0, spacing_x=2.0,
               bgcolor=[0.80, 0.80, 0.82, 1.0],
               bgoncolor=[0.20, 0.50, 0.85, 1.0],
               textcolor=[0.40, 0.40, 0.42, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# Section labels
device.add_comment("lbl_space", [8, 48, 70, 12], "SPACE",
                   fontsize=9.0, textcolor=[0.20, 0.50, 0.85, 0.7])
device.add_comment("lbl_time", [168, 48, 60, 12], "TIME",
                   fontsize=9.0, textcolor=[0.20, 0.50, 0.85, 0.7])
device.add_comment("lbl_mix", [278, 48, 60, 12], "MIX",
                   fontsize=9.0, textcolor=[0.20, 0.50, 0.85, 0.7])

# Dials row
device.add_dial("size_dial", "Size", [8, 58, 50, 70],
                min_val=0.1, max_val=1.0, initial=0.5,
                unitstyle=1, appearance=1,
                annotation_name="Room size — scales comb filter delay times")

device.add_dial("damp_dial", "Damp", [68, 58, 50, 70],
                min_val=0.0, max_val=100.0, initial=40.0,
                unitstyle=5, appearance=1,
                annotation_name="Damping — high frequency absorption in feedback loop")

device.add_dial("pre_dial", "Pre", [128, 58, 30, 70],
                min_val=0.0, max_val=100.0, initial=10.0,
                unitstyle=2, appearance=1,
                shortname="Pre",
                annotation_name="Predelay in milliseconds (0-100ms)")

device.add_dial("mix_dial", "Mix", [278, 58, 50, 70],
                min_val=0.0, max_val=100.0, initial=30.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet mix — 0% dry, 100% wet")

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

# Diff label for allpass diffusion indicator
device.add_comment("lbl_diff", [168, 130, 100, 12], "SCHROEDER ALLPASS",
                   fontsize=8.0, textcolor=[0.40, 0.40, 0.42, 0.5])

# =========================================================================
# DSP objects
# =========================================================================

# Predelay: tapin~/tapout~ up to 200ms; tapout inlet 1 = delay time
device.add_newobj("pre_tapin_l", "tapin~ 200", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[30, 30, 80, 20])
device.add_newobj("pre_tapin_r", "tapin~ 200", numinlets=1, numoutlets=1,
                  outlettype=["tapconnect"], patching_rect=[200, 30, 80, 20])

device.add_newobj("pre_tapout_l", "tapout~ 10", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 60, 70, 20])
device.add_newobj("pre_tapout_r", "tapout~ 10", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 60, 70, 20])

# predelay smoothing: pre_dial (0-100ms) → pack → line~ → both tapouts
device.add_newobj("pre_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 220, 60, 20])
device.add_newobj("pre_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 250, 40, 20])

# Room size: stored for comb delay calculations; size 0.1-1.0
device.add_newobj("size_store", "f 0.5", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 280, 40, 20])

# Room type ratios stored in message objects.
# room_tab → sel → message to size_trig that fans ratios to comb tapouts.
# Base delays (ms): 29.7, 37.1, 41.1, 43.7 × room_size × room_ratio
# Use expr to compute: base_ms * room_ratio * room_size
# We use: room-type adjusts base delay constants via a "scale" baked into each comb.
# ROOM (tab 0): factors 1.0 for base delays as given
# HALL (tab 1): multiply base by 1.5 (longer)
# PLATE (tab 2): multiply base by 0.7 (shorter)

device.add_newobj("room_sel", "sel 0 1 2", numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", ""],
                  patching_rect=[30, 310, 65, 20])

device.add_newobj("ratio_room",  "f 1.0",  numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 340, 40, 20])
device.add_newobj("ratio_hall",  "f 1.5",  numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[80, 340, 40, 20])
device.add_newobj("ratio_plate", "f 0.7",  numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[130, 340, 45, 20])

# Ratio store — holds current room ratio for comb delay computation
device.add_newobj("ratio_store", "f 1.0", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[80, 310, 40, 20])

# Trigger: when ratio or size changes, recompute all 4 comb delays
# comb_N delay = base_ms * ratio * size
# base_ms values: 29.7, 37.1, 41.1, 43.7
COMB_BASE = [29.7, 37.1, 41.1, 43.7]
for i, base in enumerate(COMB_BASE):
    device.add_newobj(f"comb_expr_{i}",
                      f"expr {base} * $f1 * $f2",
                      numinlets=2, numoutlets=1, outlettype=["float"],
                      patching_rect=[200 + i * 100, 340, 100, 20])
    device.add_newobj(f"comb_pk_{i}", "pack f 20", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[200 + i * 100, 370, 60, 20])
    device.add_newobj(f"comb_ln_{i}", "line~", numinlets=2, numoutlets=2,
                      outlettype=["signal", "bang"],
                      patching_rect=[200 + i * 100, 400, 40, 20])

# Comb filters: each is tapin~ / tapout~ / *~ feedback / onepole~ damping
# Max buffer: 200ms (covers all room sizes and types)
# Damping: onepole~ cutoff derived from damp_dial (0%=20kHz open, 100%=200Hz closed)
# L channel combs
for i in range(4):
    x = 30 + i * 80
    device.add_newobj(f"ctapin_l{i}", "tapin~ 200", numinlets=1, numoutlets=1,
                      outlettype=["tapconnect"], patching_rect=[x, 430, 70, 20])
    device.add_newobj(f"ctapout_l{i}", "tapout~ 30", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 460, 70, 20])
    device.add_newobj(f"cdamp_l{i}", "onepole~ 5000.", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 490, 80, 20])
    device.add_newobj(f"cfb_l{i}", "*~ 0.7", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 520, 50, 20])
    device.add_newobj(f"csum_l{i}", "+~", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 550, 30, 20])

# R channel combs
for i in range(4):
    x = 400 + i * 80
    device.add_newobj(f"ctapin_r{i}", "tapin~ 200", numinlets=1, numoutlets=1,
                      outlettype=["tapconnect"], patching_rect=[x, 430, 70, 20])
    device.add_newobj(f"ctapout_r{i}", "tapout~ 30", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 460, 70, 20])
    device.add_newobj(f"cdamp_r{i}", "onepole~ 5000.", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 490, 80, 20])
    device.add_newobj(f"cfb_r{i}", "*~ 0.7", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 520, 50, 20])
    device.add_newobj(f"csum_r{i}", "+~", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[x, 550, 30, 20])

# Damping: damp_dial 0-100% → onepole cutoff 20000-200 Hz (inverted mapping)
# scale 0. 100. 20000. 200. (descending)
device.add_newobj("damp_scale", "scale 0. 100. 20000. 200.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[600, 490, 130, 20])
device.add_newobj("damp_trig", "t f f f f f f f f", numinlets=1, numoutlets=8,
                  outlettype=["", "", "", "", "", "", "", ""],
                  patching_rect=[600, 510, 150, 20])

# Feedback multiplier: fixed at 0.7 (standard Schroeder), controlled per comb
# (All combs share same feedback level for simplicity)
device.add_newobj("fb_val", "f 0.7", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[750, 520, 40, 20])

# Sum 4 combs per channel, scale by 0.25
device.add_newobj("comb_sum_l0", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 590, 30, 20])
device.add_newobj("comb_sum_l1", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 610, 30, 20])
device.add_newobj("comb_sum_l2", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 630, 30, 20])
device.add_newobj("comb_scale_l", "*~ 0.25", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[120, 650, 50, 20])

device.add_newobj("comb_sum_r0", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 590, 30, 20])
device.add_newobj("comb_sum_r1", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[430, 610, 30, 20])
device.add_newobj("comb_sum_r2", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 630, 30, 20])
device.add_newobj("comb_scale_r", "*~ 0.25", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[490, 650, 50, 20])

# Allpass filters — 2 in series (L and R separate)
# Allpass: delay~ + feedforward (g) and feedback (-g)
# Standard allpass: output = -g*input + delay_output + g*delay_output
# Simplified as: y = -g*x + d + g*d = -g*x + (1+g)*d  where d = z^-M * (x + g*y)
# Use tapin~/tapout~ for the delay, sum+feedback path
# Allpass 1: 5ms, Allpass 2: 1.7ms, g = 0.7 (standard coefficient)

AP_DELAYS = [5.0, 1.7]
AP_G = 0.7

for ch in ("l", "r"):
    x_base = 30 if ch == "l" else 400
    for j, ap_ms in enumerate(AP_DELAYS):
        yoff = 670 + j * 80
        # ap input → sum with feedback → tapin~ → tapout~ → out
        # out = -g*in + tapout + g*tapout = -g*in + (1+g)*tapout
        device.add_newobj(f"ap{j}_sum_{ch}", "+~", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[x_base, yoff, 30, 20])
        device.add_newobj(f"ap{j}_tapin_{ch}", f"tapin~ {int(ap_ms + 1)}", numinlets=1, numoutlets=1,
                          outlettype=["tapconnect"],
                          patching_rect=[x_base, yoff + 25, 60, 20])
        device.add_newobj(f"ap{j}_tapout_{ch}", f"tapout~ {ap_ms}", numinlets=1, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[x_base, yoff + 50, 65, 20])
        # Feedforward: (1 + g) * tapout
        device.add_newobj(f"ap{j}_ff_{ch}", f"*~ {1.0 + AP_G}", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[x_base + 70, yoff + 50, 55, 20])
        # Feedback into sum: g * tapout (negated: feed -g*tapout back)
        device.add_newobj(f"ap{j}_fbg_{ch}", f"*~ {-AP_G}", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[x_base + 70, yoff + 30, 55, 20])
        # Output sum: ff + (-g * in)
        device.add_newobj(f"ap{j}_neg_{ch}", f"*~ {-AP_G}", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[x_base + 130, yoff, 55, 20])
        device.add_newobj(f"ap{j}_out_{ch}", "+~", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[x_base + 130, yoff + 50, 30, 20])

# Dry/wet mix
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[800, 80, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[800, 100, 55, 20])
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[800, 130, 45, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[800, 860, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[840, 860, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[880, 860, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[920, 860, 30, 20])

device.add_newobj("wet_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[800, 810, 60, 20])
device.add_newobj("wet_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[800, 840, 40, 20])
device.add_newobj("wetr_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[840, 810, 60, 20])
device.add_newobj("wetr_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[840, 840, 40, 20])
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[880, 130, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[880, 160, 40, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[860, 900, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[900, 900, 30, 20])

# =========================================================================
# Connections
# =========================================================================

# plugin~ → predelay
device.add_line("obj-plugin", 0, "pre_tapin_l", 0)
device.add_line("obj-plugin", 1, "pre_tapin_r", 0)
device.add_line("pre_tapin_l", 0, "pre_tapout_l", 0)
device.add_line("pre_tapin_r", 0, "pre_tapout_r", 0)

# Predelay time: pre_dial → pack → line~ → tapout inlet 1
device.add_line("pre_dial", 0, "pre_pk", 0)
device.add_line("pre_pk", 0, "pre_ln", 0)
device.add_line("pre_ln", 0, "pre_tapout_l", 1)
device.add_line("pre_ln", 0, "pre_tapout_r", 1)

# Room type tab → sel → ratio objects
device.add_line("room_tab", 0, "room_sel", 0)
device.add_line("room_sel", 0, "ratio_room", 0)
device.add_line("room_sel", 1, "ratio_hall", 0)
device.add_line("room_sel", 2, "ratio_plate", 0)

# Ratios → ratio_store (right inlet sets value, left outlet bangs it)
device.add_line("ratio_room", 0, "ratio_store", 1)
device.add_line("ratio_hall", 0, "ratio_store", 1)
device.add_line("ratio_plate", 0, "ratio_store", 1)

# size_dial → size_store; when either changes, ratio_store bangs → comb_exprs
device.add_line("size_dial", 0, "size_store", 1)
device.add_line("size_dial", 0, "ratio_store", 0)   # bang ratio_store to recalculate

# ratio_store → comb_expr inlets: $f1 = ratio, $f2 = size
# We need both: route ratio as $f1 and size as $f2
# ratio_store outlet 0 → all comb_expr inlet 0 (ratio)
# size_store outlet 0 → all comb_expr inlet 1 (size)
# When ratio changes, bang size_store to provide $f2 automatically
device.add_line("ratio_store", 0, "size_store", 0)   # bang size_store for size value

for i in range(4):
    device.add_line("size_store", 0, f"comb_expr_{i}", 0)    # $f1 = size
    device.add_line("ratio_store", 0, f"comb_expr_{i}", 1)   # $f2 = ratio
    device.add_line(f"comb_expr_{i}", 0, f"comb_pk_{i}", 0)
    device.add_line(f"comb_pk_{i}", 0, f"comb_ln_{i}", 0)
    # comb delay time → both L and R tapout inlet 1
    device.add_line(f"comb_ln_{i}", 0, f"ctapout_l{i}", 1)
    device.add_line(f"comb_ln_{i}", 0, f"ctapout_r{i}", 1)

# Damping: damp_dial → scale → fan to all 8 onepole~ cutoffs
device.add_line("damp_dial", 0, "damp_scale", 0)
device.add_line("damp_scale", 0, "damp_trig", 0)
for i in range(4):
    device.add_line("damp_trig", i, f"cdamp_l{i}", 1)
    device.add_line("damp_trig", i + 4, f"cdamp_r{i}", 1)

# Comb filter signal flow per voice (L and R)
for i in range(4):
    # Input (from predelay) → sum inlet 0
    device.add_line("pre_tapout_l", 0, f"csum_l{i}", 0)
    device.add_line("pre_tapout_r", 0, f"csum_r{i}", 0)
    # sum → tapin~ → tapout~
    device.add_line(f"csum_l{i}", 0, f"ctapin_l{i}", 0)
    device.add_line(f"csum_r{i}", 0, f"ctapin_r{i}", 0)
    device.add_line(f"ctapin_l{i}", 0, f"ctapout_l{i}", 0)
    device.add_line(f"ctapin_r{i}", 0, f"ctapout_r{i}", 0)
    # tapout~ → damping → feedback mul → back to sum inlet 1
    device.add_line(f"ctapout_l{i}", 0, f"cdamp_l{i}", 0)
    device.add_line(f"ctapout_r{i}", 0, f"cdamp_r{i}", 0)
    device.add_line(f"cdamp_l{i}", 0, f"cfb_l{i}", 0)
    device.add_line(f"cdamp_r{i}", 0, f"cfb_r{i}", 0)
    device.add_line(f"cfb_l{i}", 0, f"csum_l{i}", 1)
    device.add_line(f"cfb_r{i}", 0, f"csum_r{i}", 1)

# Sum 4 combs per channel
device.add_line("ctapout_l0", 0, "comb_sum_l0", 0)
device.add_line("ctapout_l1", 0, "comb_sum_l0", 1)
device.add_line("comb_sum_l0", 0, "comb_sum_l1", 0)
device.add_line("ctapout_l2", 0, "comb_sum_l1", 1)
device.add_line("comb_sum_l1", 0, "comb_sum_l2", 0)
device.add_line("ctapout_l3", 0, "comb_sum_l2", 1)
device.add_line("comb_sum_l2", 0, "comb_scale_l", 0)

device.add_line("ctapout_r0", 0, "comb_sum_r0", 0)
device.add_line("ctapout_r1", 0, "comb_sum_r0", 1)
device.add_line("comb_sum_r0", 0, "comb_sum_r1", 0)
device.add_line("ctapout_r2", 0, "comb_sum_r1", 1)
device.add_line("comb_sum_r1", 0, "comb_sum_r2", 0)
device.add_line("ctapout_r3", 0, "comb_sum_r2", 1)
device.add_line("comb_sum_r2", 0, "comb_scale_r", 0)

# Allpass chain per channel
for ch in ("l", "r"):
    prev_l = f"comb_scale_{ch}"
    prev_out = 0
    for j in range(len(AP_DELAYS)):
        # input → ap sum inlet 0, and neg (for -g*x term)
        device.add_line(prev_l, prev_out, f"ap{j}_sum_{ch}", 0)
        device.add_line(prev_l, prev_out, f"ap{j}_neg_{ch}", 0)
        # sum → tapin~ → tapout~
        device.add_line(f"ap{j}_sum_{ch}", 0, f"ap{j}_tapin_{ch}", 0)
        device.add_line(f"ap{j}_tapin_{ch}", 0, f"ap{j}_tapout_{ch}", 0)
        # tapout~ → feedforward (1+g) and feedback (-g)
        device.add_line(f"ap{j}_tapout_{ch}", 0, f"ap{j}_ff_{ch}", 0)
        device.add_line(f"ap{j}_tapout_{ch}", 0, f"ap{j}_fbg_{ch}", 0)
        # feedback → sum inlet 1
        device.add_line(f"ap{j}_fbg_{ch}", 0, f"ap{j}_sum_{ch}", 1)
        # output = neg + ff
        device.add_line(f"ap{j}_neg_{ch}", 0, f"ap{j}_out_{ch}", 0)
        device.add_line(f"ap{j}_ff_{ch}", 0, f"ap{j}_out_{ch}", 1)
        prev_l = f"ap{j}_out_{ch}"
        prev_out = 0

# Allpass outputs → wet multipliers
device.add_line("ap1_out_l", 0, "wet_l", 0)
device.add_line("ap1_out_r", 0, "wet_r", 0)

# Dry signal from plugin~
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Mix: mix_dial → scale → trigger
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# t f f f fires R→L: outlet 2 first, then 1, then 0
device.add_line("mix_trig", 0, "wet_pk", 0)
device.add_line("wet_pk", 0, "wet_ln", 0)
device.add_line("wet_ln", 0, "wet_l", 1)

device.add_line("mix_trig", 1, "wetr_pk", 0)
device.add_line("wetr_pk", 0, "wetr_ln", 0)
device.add_line("wetr_ln", 0, "wet_r", 1)

device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_pk", 0)
device.add_line("dry_pk", 0, "dry_ln", 0)
device.add_line("dry_ln", 0, "dry_l", 1)
device.add_line("dry_ln", 0, "dry_r", 1)

# Sum wet + dry
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# Output → plugout~ and meters
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Algorithmic Reverb")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
