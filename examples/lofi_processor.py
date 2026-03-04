"""Lo-Fi Processor — bitcrusher + sample rate reducer + hiss + tone filter.

Parameter smoothing:
  All float->signal paths go through pack->line~ to eliminate zipper noise.
  line~ ramps over 20ms giving click-free dial sweeps.

Note: degrade~ inlets 1 (sr_factor) and 2 (bit_depth) are message-rate
  integer controls for digital artifacts — left unsmoothed intentionally
  as their stepped character is part of the lo-fi effect.

Signal chain:
  plugin~ -> drive *~ (pre-crush gain boost) -> degrade~ (bit+rate crush)
  -> tanh~ (soft clip to prevent harsh digital clipping after crush)
  -> onepole~ tone filter -> dry/wet mix -> plugout~
  The tanh~ is intentional: heavy crushing at high Drive settings can produce
  samples outside [-1,1]. tanh~ folds these back in a musically pleasing way
  rather than hard clipping. Bypass Drive entirely (0%) to skip the effect.
"""

import os
from m4l_builder import AudioEffect, WARM, device_output_path

device = AudioEffect("LoFi Processor", width=310, height=200, theme=WARM)

device.add_panel("bg", [0, 0, 310, 200])

# Bitcrushed waveform scope — the visual heart, takes ~40% of height
device.add_scope("crush_scope", [8, 8, 264, 70],
                 bgcolor=[0.05, 0.04, 0.03, 1.0],
                 activelinecolor=[0.85, 0.55, 0.25, 1.0],
                 gridcolor=[0.14, 0.11, 0.08, 0.4],
                 range_vals=[-1.2, 1.2],
                 calccount=64, smooth=0, line_width=2.0)

# Section labels above dials
device.add_comment("lbl_crush", [8, 84, 84, 12], "CRUSH",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.7])
device.add_comment("lbl_drive", [100, 84, 40, 12], "DRIVE",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.7])
device.add_comment("lbl_color", [144, 84, 40, 12], "COLOR",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.7])
device.add_comment("lbl_output", [228, 84, 55, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.7])

# Bits and Rate are the primary controls — bigger dials
device.add_dial("bits_dial", "Bits", [8, 94, 48, 88],
                min_val=1.0, max_val=16.0, initial=12.0,
                annotation_name="Bit depth reduction — lower values = crunchier")

device.add_dial("rate_dial", "Rate", [60, 94, 48, 88],
                min_val=0.0, max_val=100.0, initial=0.0,
                unitstyle=5,  # PERCENT
                annotation_name="Sample rate reduction — higher values = more aliasing")

device.add_dial("drive_dial", "Drive", [112, 94, 40, 88],
                min_val=0.0, max_val=100.0, initial=0.0,
                annotation_name="Input drive before bitcrushing")

device.add_dial("tone_dial", "Tone", [152, 94, 40, 88],
                min_val=500.0, max_val=20000.0, initial=20000.0,
                unitstyle=3,  # HZ
                annotation_name="Post-crush lowpass filter cutoff")

device.add_dial("hiss_dial", "Hiss", [192, 94, 40, 88],
                min_val=0.0, max_val=100.0, initial=0.0,
                annotation_name="Analog tape hiss noise level")

device.add_dial("mix_dial", "Mix", [232, 94, 44, 88],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5,  # PERCENT
                annotation_name="Dry/wet balance — 0% clean, 100% crushed")

# Output meters — full height
device.add_meter("meter_l", [280, 8, 14, 184], orientation=0,
                 coldcolor=[0.85, 0.55, 0.25, 1.0],
                 warmcolor=[0.90, 0.75, 0.20, 1.0],
                 hotcolor=[0.90, 0.40, 0.10, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [295, 8, 14, 184], orientation=0,
                 coldcolor=[0.85, 0.55, 0.25, 1.0],
                 warmcolor=[0.90, 0.75, 0.20, 1.0],
                 hotcolor=[0.90, 0.40, 0.10, 1.0],
                 overloadcolor=[0.90, 0.15, 0.15, 1.0])

# Input drive: scale dial 0-100 -> 1.0-3.0, then *~ for L and R
device.add_newobj("drive_scale", "scale 0. 100. 1. 3.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 200, 120, 20])

# Smoothing for drive (scale -> pack -> line~)
device.add_newobj("drive_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 200, 60, 20])
device.add_newobj("drive_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[160, 230, 40, 20])

device.add_newobj("drive_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 240, 40, 20])

device.add_newobj("drive_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 240, 40, 20])

# degrade~ for L and R channels
# 3 inlets: signal(0), sr_factor(1 = message float), bit_depth(2 = message float)
# At sr_factor=1 and bit_depth=16, degrade~ is transparent
device.add_newobj("degrade_l", "degrade~ 1 16", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 280, 60, 20])

device.add_newobj("degrade_r", "degrade~ 1 16", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 280, 60, 20])

# Sample rate factor: scale dial 0-100 -> sr_factor 1-32
device.add_newobj("rate_scale", "scale 0. 100. 1. 32.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 270, 120, 20])

# Bits: dial outputs 1-16 integer directly -> degrade~ inlet 2
# (no scaling needed, dial range matches degrade~ bit_depth range)
# degrade~ message inlets are intentionally left unsmoothed — the stepped
# character of bit-depth changes is central to the lo-fi aesthetic.

# tanh~ for post-crush soft saturation (L and R).
# Heavy crush at high drive can push samples outside [-1,1]. tanh~ folds them
# back musically rather than hard clipping. Set Drive=0 to bypass the effect.
device.add_newobj("tanh_l", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 320, 35, 20])

device.add_newobj("tanh_r", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 320, 35, 20])

# onepole~ tone filter (L and R), Tone dial -> Hz cutoff directly
device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 360, 50, 20])

device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 360, 50, 20])

# Smoothing for tone cutoff (dial -> pack -> line~ -> onepole~ both channels)
device.add_newobj("tone_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 350, 60, 20])
device.add_newobj("tone_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[160, 380, 40, 20])

# Hiss chain: noise~ -> svf~ bandpass (outlet 2) -> *~ hiss_level
# svf~ inlets: signal(0), cutoff_hz(1), res_0to1(2)
# We send freq as float to inlet 1, so use 1 inlet for signal + message inlets
device.add_newobj("noise", "noise~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 280, 40, 20])

device.add_newobj("hiss_svf", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[160, 320, 40, 20])

# Message boxes to set svf~ freq to 5000 Hz and res to 0.3 on load
# Use loadbang -> message box (maxclass: "message") -> svf~ inlets
device.add_newobj("lb", "loadbang", numinlets=0, numoutlets=1,
                  outlettype=["bang"], patching_rect=[220, 270, 60, 20])

device.add_box({
    "box": {
        "id": "hiss_freq_msg",
        "maxclass": "message",
        "text": "5000.",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [220, 295, 45, 20],
    }
})

device.add_box({
    "box": {
        "id": "hiss_res_msg",
        "maxclass": "message",
        "text": "0.3",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [275, 295, 35, 20],
    }
})

# Hiss level: scale dial 0-100 -> 0.0-0.3
device.add_newobj("hiss_scale", "scale 0. 100. 0. 0.3", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 200, 120, 20])

# Smoothing for hiss level (scale -> pack -> line~)
device.add_newobj("hiss_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 230, 60, 20])
device.add_newobj("hiss_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 260, 40, 20])

device.add_newobj("hiss_amp", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 370, 30, 20])

# Sum processed + hiss (L and R)
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 410, 30, 20])

device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 410, 30, 20])

# Dry/wet mix
# mix_dial 0-100 -> scale -> 0.0-1.0
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])

# Smoothing for mix (scale -> pack -> line~ -> wet/dry multipliers)
device.add_newobj("mix_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 90, 60, 20])
device.add_newobj("mix_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[400, 120, 40, 20])

# Invert mix for dry: !-~ 1. gives (1.0 - mix)
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 150, 50, 20])

# Wet gain multipliers
device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 450, 30, 20])

device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 450, 30, 20])

# Dry gain multipliers
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 450, 30, 20])

device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 450, 30, 20])

# Output sum wet + dry
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 490, 30, 20])

device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[130, 490, 30, 20])

# Input drive chain: plugin~ -> drive_l/r -> degrade_l/r
device.add_line("obj-plugin", 0, "drive_l", 0)   # plugin~ L -> drive_l signal
device.add_line("obj-plugin", 1, "drive_r", 0)   # plugin~ R -> drive_r signal

# Drive smoothing: dial -> scale -> pack -> line~ -> drive_l/r inlet 1
device.add_line("drive_dial", 0, "drive_scale", 0)
device.add_line("drive_scale", 0, "drive_pk", 0)
device.add_line("drive_pk", 0, "drive_ln", 0)
device.add_line("drive_ln", 0, "drive_l", 1)     # smoothed drive -> drive_l float
device.add_line("drive_ln", 0, "drive_r", 1)     # smoothed drive -> drive_r float

# degrade~ signal path
device.add_line("drive_l", 0, "degrade_l", 0)    # drive_l -> degrade_l signal
device.add_line("drive_r", 0, "degrade_r", 0)    # drive_r -> degrade_r signal

# Sample rate factor: rate_dial -> scale -> degrade~ inlet 1 (MESSAGE float)
device.add_line("rate_dial", 0, "rate_scale", 0)
device.add_line("rate_scale", 0, "degrade_l", 1)  # sr_factor float -> degrade_l inlet 1
device.add_line("rate_scale", 0, "degrade_r", 1)  # sr_factor float -> degrade_r inlet 1

# Bits: bits_dial -> degrade~ inlet 2 (MESSAGE float, integer 1-16)
device.add_line("bits_dial", 0, "degrade_l", 2)  # bits float -> degrade_l inlet 2
device.add_line("bits_dial", 0, "degrade_r", 2)  # bits float -> degrade_r inlet 2

# Post-crush saturation: degrade~ -> tanh~
device.add_line("degrade_l", 0, "tanh_l", 0)
device.add_line("degrade_r", 0, "tanh_r", 0)

# Tone filter: tanh~ -> onepole~
device.add_line("tanh_l", 0, "tone_l", 0)
device.add_line("tanh_r", 0, "tone_r", 0)

# Tone smoothing: dial -> pack -> line~ -> onepole~ cutoff (both channels)
device.add_line("tone_dial", 0, "tone_pk", 0)
device.add_line("tone_pk", 0, "tone_ln", 0)
device.add_line("tone_ln", 0, "tone_l", 1)       # smoothed cutoff -> tone_l
device.add_line("tone_ln", 0, "tone_r", 1)       # smoothed cutoff -> tone_r

# Hiss chain
device.add_line("noise", 0, "hiss_svf", 0)       # noise~ -> svf~ signal

# Initialize svf~ freq and res via loadbang
device.add_line("lb", 0, "hiss_freq_msg", 0)
device.add_line("hiss_freq_msg", 0, "hiss_svf", 1)   # 5000 Hz -> svf~ freq
device.add_line("lb", 0, "hiss_res_msg", 0)
device.add_line("hiss_res_msg", 0, "hiss_svf", 2)    # 0.3 res -> svf~ res

# svf~ outlet 2 = bandpass -> hiss_amp
device.add_line("hiss_svf", 2, "hiss_amp", 0)        # bandpass out -> hiss amp signal

# Hiss smoothing: dial -> scale -> pack -> line~ -> hiss_amp inlet 1
device.add_line("hiss_dial", 0, "hiss_scale", 0)
device.add_line("hiss_scale", 0, "hiss_pk", 0)
device.add_line("hiss_pk", 0, "hiss_ln", 0)
device.add_line("hiss_ln", 0, "hiss_amp", 1)         # smoothed hiss level

# Sum processed signal + hiss
device.add_line("tone_l", 0, "sum_l", 0)          # processed L -> sum
device.add_line("tone_r", 0, "sum_r", 0)          # processed R -> sum
device.add_line("hiss_amp", 0, "sum_l", 1)        # hiss -> sum L
device.add_line("hiss_amp", 0, "sum_r", 1)        # hiss -> sum R (mono hiss)

# Mix smoothing: dial -> scale -> pack -> line~ -> wet/dry multipliers
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_pk", 0)
device.add_line("mix_pk", 0, "mix_ln", 0)
# mix_ln (signal) fans to wet_l gain, wet_r gain, and the inverter
device.add_line("mix_ln", 0, "wet_l", 1)
device.add_line("mix_ln", 0, "wet_r", 1)
device.add_line("mix_ln", 0, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

# Wet path: sum -> wet multipliers
device.add_line("sum_l", 0, "wet_l", 0)
device.add_line("sum_r", 0, "wet_r", 0)

# Dry path: plugin~ -> dry multipliers
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Output: wet + dry -> out
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# Output to plugout~
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# Crush scope: show the degraded/bitcrushed signal (stairstepped waveform)
device.add_line("degrade_l", 0, "crush_scope", 0)

# Output meters: tap the final output signals
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

output = device_output_path("LoFi Processor")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
