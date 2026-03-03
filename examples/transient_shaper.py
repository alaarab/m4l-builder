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

UI controls (280x120, dark theme):
  Attack  | Sustain | Speed  | Mix   (single row of dials)

Scale attack/sustain: dial -100 to 100 -> -1.0 to 1.0 for *~ multiplier.
Speed dial adjusts slide~ coefficients (slow=longer transient, fast=shorter).

CRITICAL RULES followed:
  - No sig~  (floats sent directly to *~ inlet 1)
  - No dcblock~ (doesn't exist in Max 8)
  - panels use background:1
  - t f f / t f f f for fanning floats (outlets fire right-to-left)
"""

import os
from m4l_builder import AudioEffect, WARM

# --- Device setup ---
device = AudioEffect("Transient Shaper", width=280, height=170, theme=WARM)

# =========================================================================
# UI
# =========================================================================

# Dark background
device.add_panel("bg", [0, 0, 280, 170], bgcolor=[0.10, 0.10, 0.12, 1.0])

# Title
device.add_comment("title", [8, 5, 180, 16], "TRANSIENT",
                   textcolor=[0.95, 0.92, 0.85, 1.0], fontsize=13.0)

# Hero display: gain envelope scope — shows the transient shaping gain (1.0 = unity)
device.add_scope("gain_scope", [8, 24, 264, 50],
                 bgcolor=[0.06, 0.06, 0.08, 1.0],
                 activelinecolor=[0.85, 0.55, 0.25, 1.0],
                 gridcolor=[0.15, 0.15, 0.17, 0.4],
                 range_vals=[0.0, 2.5],
                 calccount=128, smooth=2, line_width=1.5)

# Section labels above dial groups
device.add_comment("lbl_shape", [8, 76, 130, 12], "SHAPE",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.6])
device.add_comment("lbl_detect", [148, 76, 60, 12], "DETECT",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.6])
device.add_comment("lbl_output", [218, 76, 60, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.6])

# Attack dial
device.add_comment("attack_lbl", [10, 77, 45, 12], "ATTACK",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5)
device.add_dial("attack_dial", "Attack", [8, 87, 60, 58],
                min_val=-100.0, max_val=100.0, initial=0.0,
                unitstyle=5,  # PERCENT
                annotation_name="Boost or cut the transient attack")

# Sustain dial
device.add_comment("sustain_lbl", [80, 77, 48, 12], "SUSTAIN",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5)
device.add_dial("sustain_dial", "Sustain", [78, 87, 60, 58],
                min_val=-100.0, max_val=100.0, initial=0.0,
                unitstyle=5,  # PERCENT
                annotation_name="Boost or cut the sustain/body")

# Speed dial
device.add_comment("speed_lbl", [150, 77, 40, 12], "SPEED",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5)
device.add_dial("speed_dial", "Speed", [148, 87, 60, 58],
                min_val=1.0, max_val=10.0, initial=1.0,
                unitstyle=1,  # FLOAT
                annotation_name="Detection sensitivity — adjusts envelope response")

# Mix dial
device.add_comment("mix_lbl", [220, 77, 30, 12], "MIX",
                   textcolor=[0.65, 0.65, 0.65, 1.0], fontsize=8.5)
device.add_dial("mix_dial", "Mix", [218, 87, 60, 58],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5,  # PERCENT
                annotation_name="Dry/wet balance — 0% bypassed, 100% fully shaped")

# =========================================================================
# DSP objects
# =========================================================================

# --- Scale attack dial: -100..100 -> -1.0..1.0 ---
device.add_newobj("attack_scale", "scale -100. 100. -1. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 200, 130, 20])

# --- Scale sustain dial: -100..100 -> -1.0..1.0 ---
device.add_newobj("sustain_scale", "scale -100. 100. -1. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[130, 200, 130, 20])

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
                  outlettype=["signal"], patching_rect=[30, 240, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 240, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 265, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 290, 45, 20])

# --- Fast envelope: slide~ 44 880 (1ms attack, 20ms release) ---
# slide~ inlets: 0=signal, 1=attack_samples, 2=release_samples
device.add_newobj("fast_env", "slide~ 44 880", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 315, 80, 20])

# --- Slow envelope: slide~ 660 880 (15ms attack, 20ms release) ---
device.add_newobj("slow_env", "slide~ 660 880", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 315, 80, 20])

# --- Transient = fast - slow ---
# -~: inlet 0 = minuend (fast), inlet 1 = subtrahend (slow)
device.add_newobj("transient", "-~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 345, 30, 20])

# --- Scale transient by attack_scaled (float into *~ inlet 1) ---
device.add_newobj("trans_scaled", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 370, 40, 20])

# --- Scale sustain (slow_env) by sustain_scaled (float into *~ inlet 1) ---
device.add_newobj("sust_scaled", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 370, 40, 20])

# --- Sum transient_scaled + sustain_scaled ---
device.add_newobj("gain_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 400, 30, 20])

# --- Add 1.0: final_gain = 1.0 + gain_sum ---
# +~ 1.: inlet 0=signal, arg sets inlet 1 constant
device.add_newobj("gain_plus1", "+~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[110, 425, 45, 20])

# --- Apply gain to L/R audio ---
device.add_newobj("out_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 455, 30, 20])
device.add_newobj("out_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 455, 30, 20])

# --- Dry/wet mix stage ---
# scale mix dial 0..100 -> 0..1
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])
# t f f f fires outlets right-to-left: outlet 2 first (cold), then 1, then 0 (hot)
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 90, 55, 20])
# !-~ 1. gives (1.0 - mix) for dry gain
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 120, 45, 20])
device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 490, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 490, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 490, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 490, 30, 20])
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 530, 30, 20])
device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 530, 30, 20])

# =========================================================================
# Connections
# =========================================================================

# --- Attack dial -> scale -> trans_scaled inlet 1 ---
device.add_line("attack_dial", 0, "attack_scale", 0)
device.add_line("attack_scale", 0, "trans_scaled", 1)   # float -> *~ inlet 1

# --- Sustain dial -> scale -> sust_scaled inlet 1 ---
device.add_line("sustain_dial", 0, "sustain_scale", 0)
device.add_line("sustain_scale", 0, "sust_scaled", 1)   # float -> *~ inlet 1

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

# --- Scale transient by attack amount ---
device.add_line("transient", 0, "trans_scaled", 0)

# --- Scale slow_env (sustain) by sustain amount ---
device.add_line("slow_env", 0, "sust_scaled", 0)

# --- Sum transient_scaled + sust_scaled -> +1.0 = final gain ---
device.add_line("trans_scaled", 0, "gain_sum", 0)
device.add_line("sust_scaled", 0, "gain_sum", 1)
device.add_line("gain_sum", 0, "gain_plus1", 0)

# --- Apply final gain to L/R audio ---
device.add_line("obj-plugin", 0, "out_l", 0)
device.add_line("obj-plugin", 1, "out_r", 0)
device.add_line("gain_plus1", 0, "out_l", 1)      # float gain -> *~ inlet 1
device.add_line("gain_plus1", 0, "out_r", 1)

# --- Mix: dial -> scale -> trigger fan -> wet/dry ---
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# outlet 2 fires first (cold): dry inverse
# outlet 1 fires second: wet_r
# outlet 0 fires last (hot): wet_l
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
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

# Output: sum -> plugout~
device.add_line("sum_l", 0, "obj-plugout", 0)
device.add_line("sum_r", 0, "obj-plugout", 1)

# Scope display — show gain_plus1 signal (transient shaping in action)
device.add_line("gain_plus1", 0, "gain_scope", 0)

# =========================================================================
# Build
# =========================================================================
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Transient Shaper.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
