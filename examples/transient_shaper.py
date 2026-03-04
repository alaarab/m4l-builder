"""Transient Shaper — m4l_builder example.

Attack/sustain control via differential envelope follower.

DSP signal flow:
  plugin~ L/R
    -> abs~ L + abs~ R -> +~ -> *~ 0.5 (mono peak average)
    -> Fast envelope:  slide~ 44 880   (1ms attack, 20ms release at 44100sr)
    -> Slow envelope:  slide~ 660 880  (15ms attack, 20ms release)
    -> Transient = fast - slow via -~  (positive during attacks)
    -> Sustain  = slow envelope
    -> Gain signal = 1.0 + (transient * attack_scaled) + (sustain * sustain_scaled)
    -> Apply gain to L/R via *~
    -> Dry/wet mix -> plugout~

UI controls (310x120, dark theme):
  Attack  | Sustain | Speed  | Mix   (single row of dials)
  Meter L | Meter R (right edge)

Parameter smoothing: all float-to-signal paths use pack/line~ to
eliminate zipper noise:
  scale -> pack f 20 -> line~ -> *~ inlet 1

Output meters: L/R vertical meters on right edge.

CRITICAL RULES followed:
  - No sig~  (line~ provides smoothed signal to *~ inlet 1)
  - No dcblock~ (doesn't exist in Max 8)
  - panels use background:1
  - t f f / t f f f for fanning floats (outlets fire right-to-left)
"""

import os
from m4l_builder import AudioEffect, WARM, device_output_path

device = AudioEffect("Transient Shaper", width=310, height=170, theme=WARM)

# =========================================================================
# UI
# =========================================================================

# Dark background
device.add_panel("bg", [0, 0, 310, 170], bgcolor=WARM.bg)

# Hero display: gain envelope scope — shows the transient shaping gain (1.0 = unity)
device.add_scope("gain_scope", [8, 6, 264, 62],
                 bgcolor=[0.06, 0.06, 0.08, 1.0],
                 activelinecolor=[0.85, 0.55, 0.25, 1.0],
                 gridcolor=[0.15, 0.15, 0.17, 0.4],
                 range_vals=[0.0, 2.5],
                 calccount=128, smooth=2, line_width=1.5)

# Dial section labels
device.add_comment("lbl_shape", [8, 71, 130, 11], "SHAPE",
                   fontsize=9.0, textcolor=WARM.text_dim)
device.add_comment("lbl_detect", [148, 71, 60, 11], "DETECT",
                   fontsize=9.0, textcolor=WARM.text_dim)
device.add_comment("lbl_output", [218, 71, 60, 11], "OUTPUT",
                   fontsize=9.0, textcolor=WARM.text_dim)

# Attack dial
device.add_dial("attack_dial", "Attack", [8, 82, 60, 72],
                min_val=-100.0, max_val=100.0, initial=0.0,
                unitstyle=5,
                annotation_name="Boost or cut the transient attack")

# Sustain dial
device.add_dial("sustain_dial", "Sustain", [78, 82, 60, 72],
                min_val=-100.0, max_val=100.0, initial=0.0,
                unitstyle=5,
                annotation_name="Boost or cut the sustain/body")

# Detection speed dial — affects how fast the envelope responds
device.add_dial("speed_dial", "Detection Speed", [148, 82, 60, 72],
                min_val=1.0, max_val=10.0, initial=1.0,
                unitstyle=0,
                annotation_name="Detection speed — 1=slow, 10=fast")

# Mix dial
device.add_dial("mix_dial", "Mix", [218, 82, 60, 72],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5,
                annotation_name="Dry/wet balance — 0% bypassed, 100% fully shaped")

# Output meters — L/R vertical on right edge, WARM theme orange tones
device.add_meter("meter_l", [280, 6, 12, 158],
                 coldcolor=[0.55, 0.40, 0.20, 1.0],
                 warmcolor=[0.85, 0.55, 0.25, 1.0],
                 hotcolor=[0.90, 0.35, 0.10, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0],
                 patching_rect=[800, 0, 12, 158])
device.add_meter("meter_r", [294, 6, 12, 158],
                 coldcolor=[0.55, 0.40, 0.20, 1.0],
                 warmcolor=[0.85, 0.55, 0.25, 1.0],
                 hotcolor=[0.90, 0.35, 0.10, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0],
                 patching_rect=[820, 0, 12, 158])

# =========================================================================
# DSP objects
# =========================================================================

# --- Scale attack dial: -100..100 -> -1.0..1.0 ---
device.add_newobj("attack_scale", "scale -100. 100. -1. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 200, 130, 20])

# --- Parameter smoothing for attack: pack f 20 -> line~ ---
# line~ ramps to new value over 20ms, eliminating zipper noise on *~ inlet 1
device.add_newobj("attack_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 225, 60, 20])
device.add_newobj("attack_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 250, 40, 20])

# --- Scale sustain dial: -100..100 -> -1.0..1.0 ---
device.add_newobj("sustain_scale", "scale -100. 100. -1. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[130, 200, 130, 20])

# --- Parameter smoothing for sustain: pack f 20 -> line~ ---
device.add_newobj("sustain_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[130, 225, 60, 20])
device.add_newobj("sustain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[130, 250, 40, 20])

# --- Speed dial -> scale to attack coefficient for fast envelope ---
# Speed 1..10: fast attack samples = 44 * speed, slow attack = 660 * speed
# Fast envelope attack: 44 samples (1ms) at speed=1
device.add_newobj("speed_fast_atk", "* 44.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 200, 60, 20])
# Slow envelope attack: 660 samples (15ms) at speed=1
device.add_newobj("speed_slow_atk", "* 660.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[370, 200, 60, 20])
# Fan speed to both fast and slow attack scalers (t f f: fires outlet 1 first, then 0)
device.add_newobj("speed_fan", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[330, 175, 45, 20])

# --- Envelope follower: abs~ L + R -> average ---
device.add_newobj("abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 290, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 290, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 315, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 340, 45, 20])

# --- Fast envelope: slide~ 44 880 (1ms attack, 20ms release) ---
# slide~ inlets: 0=signal, 1=attack_samples, 2=release_samples
device.add_newobj("fast_env", "slide~ 44 880", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 365, 80, 20])

# --- Slow envelope: slide~ 660 880 (15ms attack, 20ms release) ---
device.add_newobj("slow_env", "slide~ 660 880", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 365, 80, 20])

# --- Transient = fast - slow ---
# -~: inlet 0 = minuend (fast), inlet 1 = subtrahend (slow)
device.add_newobj("transient", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 395, 30, 20])

# --- Scale transient by attack_ln signal (smoothed) ---
device.add_newobj("trans_scaled", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 420, 30, 20])

# --- Scale sustain (slow_env) by sustain_ln signal (smoothed) ---
device.add_newobj("sust_scaled", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 420, 30, 20])

# --- Sum transient_scaled + sustain_scaled ---
device.add_newobj("gain_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 450, 30, 20])

# --- Add 1.0: final_gain = 1.0 + gain_sum ---
# +~ 1.: inlet 0=signal, arg sets inlet 1 constant
device.add_newobj("gain_plus1", "+~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 475, 45, 20])

# --- Apply gain to L/R audio ---
device.add_newobj("out_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 505, 30, 20])
device.add_newobj("out_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 505, 30, 20])

# --- Dry/wet mix stage ---
# scale mix dial 0..100 -> 0..1
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])

# --- Parameter smoothing for mix: pack f 20 -> line~ ---
# line~ smooths wet/dry level transitions to prevent clicks
device.add_newobj("mix_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 85, 60, 20])
device.add_newobj("mix_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 110, 40, 20])

# !-~ 1. gives (1.0 - mix) for dry gain — receives smoothed signal now
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 140, 45, 20])
device.add_newobj("wet_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 540, 30, 20])
device.add_newobj("wet_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 540, 30, 20])
device.add_newobj("dry_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 540, 30, 20])
device.add_newobj("dry_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 540, 30, 20])
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 580, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 580, 30, 20])

# Output protection: clip to prevent loud transients from clipping
device.add_newobj("clip_l", "clip~ -1. 1.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 610, 65, 20])
device.add_newobj("clip_r", "clip~ -1. 1.", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 610, 65, 20])

# =========================================================================
# Connections
# =========================================================================

# --- Attack dial -> scale -> pack -> line~ -> trans_scaled inlet 1 (signal) ---
device.add_line("attack_dial", 0, "attack_scale", 0)
device.add_line("attack_scale", 0, "attack_pk", 0)     # float -> pack inlet 0
device.add_line("attack_pk", 0, "attack_ln", 0)        # list [val, 20] -> line~
device.add_line("attack_ln", 0, "trans_scaled", 1)     # smoothed signal -> *~ inlet 1

# --- Sustain dial -> scale -> pack -> line~ -> sust_scaled inlet 1 (signal) ---
device.add_line("sustain_dial", 0, "sustain_scale", 0)
device.add_line("sustain_scale", 0, "sustain_pk", 0)   # float -> pack inlet 0
device.add_line("sustain_pk", 0, "sustain_ln", 0)      # list [val, 20] -> line~
device.add_line("sustain_ln", 0, "sust_scaled", 1)     # smoothed signal -> *~ inlet 1

# --- Speed dial -> fan -> fast/slow attack scalers -> slide~ inlets ---
device.add_line("speed_dial", 0, "speed_fan", 0)
# outlet 1 fires first (cold), outlet 0 fires last (hot)
device.add_line("speed_fan", 0, "speed_fast_atk", 0)   # hot: fast attack
device.add_line("speed_fan", 1, "speed_slow_atk", 0)   # cold: slow attack
device.add_line("speed_fast_atk", 0, "fast_env", 1)    # -> slide~ attack inlet
device.add_line("speed_slow_atk", 0, "slow_env", 1)    # -> slide~ attack inlet

# --- Envelope follower: plugin~ -> abs~ -> sum -> avg ---
device.add_line("obj-plugin", 0, "abs_l", 0)
device.add_line("obj-plugin", 1, "abs_r", 0)
device.add_line("abs_l", 0, "env_sum", 0)
device.add_line("abs_r", 0, "env_sum", 1)
device.add_line("env_sum", 0, "env_avg", 0)

# --- avg -> fast_env and slow_env ---
device.add_line("env_avg", 0, "fast_env", 0)
device.add_line("env_avg", 0, "slow_env", 0)

# --- Transient = fast - slow ---
device.add_line("fast_env", 0, "transient", 0)    # minuend
device.add_line("slow_env", 0, "transient", 1)    # subtrahend

# --- Scale transient by smoothed attack signal ---
device.add_line("transient", 0, "trans_scaled", 0)

# --- Scale slow_env (sustain) by smoothed sustain signal ---
device.add_line("slow_env", 0, "sust_scaled", 0)

# --- Sum transient_scaled + sust_scaled -> +1.0 = final gain ---
device.add_line("trans_scaled", 0, "gain_sum", 0)
device.add_line("sust_scaled", 0, "gain_sum", 1)
device.add_line("gain_sum", 0, "gain_plus1", 0)

# --- Apply final gain to L/R audio (signal -> *~ inlet 1) ---
device.add_line("obj-plugin", 0, "out_l", 0)
device.add_line("obj-plugin", 1, "out_r", 0)
device.add_line("gain_plus1", 0, "out_l", 1)      # signal gain -> *~ inlet 1
device.add_line("gain_plus1", 0, "out_r", 1)

# --- Mix: dial -> scale -> pack -> line~ -> wet/dry multipliers (all signal) ---
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_pk", 0)      # float -> pack inlet 0
device.add_line("mix_pk", 0, "mix_ln", 0)         # list [val, 20] -> line~
# mix_ln outlet 0 (signal) fans to wet_l, wet_r, and mix_inv
# All three are signal inlets — connect smoothed signal directly
device.add_line("mix_ln", 0, "wet_l", 1)          # smoothed mix -> wet_l *~ inlet 1
device.add_line("mix_ln", 0, "wet_r", 1)          # smoothed mix -> wet_r *~ inlet 1
device.add_line("mix_ln", 0, "mix_inv", 0)        # smoothed mix -> !-~ inlet 0
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

# Wet: processed audio -> wet multipliers
device.add_line("out_l", 0, "wet_l", 0)
device.add_line("out_r", 0, "wet_r", 0)

# Dry: plugin~ -> dry multipliers
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Sum wet + dry
device.add_line("wet_l", 0, "sum_l", 0)
device.add_line("dry_l", 0, "sum_l", 1)
device.add_line("wet_r", 0, "sum_r", 0)
device.add_line("dry_r", 0, "sum_r", 1)

# Output: sum -> clip~ -> plugout~
device.add_line("sum_l", 0, "clip_l", 0)
device.add_line("sum_r", 0, "clip_r", 0)
device.add_line("clip_l", 0, "obj-plugout", 0)
device.add_line("clip_r", 0, "obj-plugout", 1)

# Scope display — show gain_plus1 signal (transient shaping in action)
device.add_line("gain_plus1", 0, "gain_scope", 0)

# Output meters — tap off final clipped output
device.add_line("clip_l", 0, "meter_l", 0)
device.add_line("clip_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Transient Shaper")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
