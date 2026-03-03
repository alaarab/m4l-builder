"""Lo-Fi Processor — bitcrusher + sample rate reducer + hiss + tone filter."""

import os
from m4l_builder import AudioEffect, WARM

device = AudioEffect("LoFi Processor", width=280, height=175, theme=WARM)

# --- UI ---
# Dark background panel (background:1 so it renders behind controls)
device.add_panel("bg", [0, 0, 280, 175], bgcolor=[0.12, 0.12, 0.14, 1.0])

# Title
device.add_comment("title", [8, 6, 80, 16], "LO-FI",
                   textcolor=[0.95, 0.92, 0.85, 1.0], fontsize=13.0)

# Crushed waveform scope — shows the bitcrushed/degraded signal
device.add_scope("crush_scope", [8, 26, 264, 42],
                 bgcolor=[0.06, 0.06, 0.06, 1.0],
                 activelinecolor=[0.85, 0.55, 0.25, 1.0],
                 gridcolor=[0.15, 0.13, 0.10, 0.4],
                 range_vals=[-1.2, 1.2],
                 calccount=64, smooth=0, line_width=1.5)

# Section labels above dials
device.add_comment("lbl_crush", [8, 62, 84, 12], "CRUSH",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.6])
device.add_comment("lbl_color", [96, 62, 84, 12], "COLOR",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.6])
device.add_comment("lbl_output", [184, 62, 84, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.85, 0.55, 0.25, 0.6])

# Dials row: Bits, Rate, Drive, Tone, Hiss, Mix
# 6 dials at ~40px wide, spaced across 280px
device.add_dial("bits_dial", "Bits", [8, 72, 40, 75],
                min_val=1.0, max_val=16.0, initial=12.0,
                annotation_name="Bit depth reduction — lower values = crunchier")

device.add_dial("rate_dial", "Rate", [52, 72, 40, 75],
                min_val=0.0, max_val=100.0, initial=0.0,
                annotation_name="Sample rate reduction — higher values = more aliasing")

device.add_dial("drive_dial", "Drive", [96, 72, 40, 75],
                min_val=0.0, max_val=100.0, initial=0.0,
                annotation_name="Input drive before bitcrushing")

device.add_dial("tone_dial", "Tone", [140, 72, 40, 75],
                min_val=500.0, max_val=20000.0, initial=20000.0,
                unitstyle=3,  # HZ
                annotation_name="Post-crush lowpass filter cutoff")

device.add_dial("hiss_dial", "Hiss", [184, 72, 40, 75],
                min_val=0.0, max_val=100.0, initial=0.0,
                annotation_name="Analog tape hiss noise level")

device.add_dial("mix_dial", "Mix", [228, 72, 40, 75],
                min_val=0.0, max_val=100.0, initial=100.0,
                annotation_name="Dry/wet balance — 0% clean, 100% crushed")

# --- DSP objects ---

# Input drive: scale dial 0-100 -> 1.0-3.0, then *~ for L and R
device.add_newobj("drive_scale", "scale 0. 100. 1. 3.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 200, 120, 20])

device.add_newobj("drive_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 230, 40, 20])

device.add_newobj("drive_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 230, 40, 20])

# degrade~ for L and R channels
# 3 inlets: signal(0), sr_factor(1 = message float), bit_depth(2 = message float)
# At sr_factor=1 and bit_depth=16, degrade~ is transparent
device.add_newobj("degrade_l", "degrade~ 1 16", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 270, 60, 20])

device.add_newobj("degrade_r", "degrade~ 1 16", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 270, 60, 20])

# Sample rate factor: scale dial 0-100 -> sr_factor 1-32
device.add_newobj("rate_scale", "scale 0. 100. 1. 32.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 200, 120, 20])

# Bits: dial outputs 1-16 integer directly -> degrade~ inlet 2
# (no scaling needed, dial range matches degrade~ bit_depth range)

# tanh~ for post-crush warmth (L and R)
device.add_newobj("tanh_l", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 310, 35, 20])

device.add_newobj("tanh_r", "tanh~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 310, 35, 20])

# onepole~ tone filter (L and R), Tone dial -> Hz cutoff directly
device.add_newobj("tone_l", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 350, 50, 20])

device.add_newobj("tone_r", "onepole~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 350, 50, 20])

# Hiss chain: noise~ -> svf~ bandpass (outlet 2) -> *~ hiss_level
# svf~ inlets: signal(0), cutoff_hz(1), res_0to1(2)
# We send freq as float to inlet 1, so use 1 inlet for signal + message inlets
device.add_newobj("noise", "noise~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 270, 40, 20])

device.add_newobj("hiss_svf", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[160, 310, 40, 20])

# Message boxes to set svf~ freq to 5000 Hz and res to 0.3 on load
# Use loadbang -> message box (maxclass: "message") -> svf~ inlets
device.add_newobj("lb", "loadbang", numinlets=0, numoutlets=1,
                  outlettype=["bang"], patching_rect=[220, 260, 60, 20])

device.add_box({
    "box": {
        "id": "hiss_freq_msg",
        "maxclass": "message",
        "text": "5000.",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [220, 285, 45, 20],
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
        "patching_rect": [275, 285, 35, 20],
    }
})

# Hiss level: scale dial 0-100 -> 0.0-0.3
device.add_newobj("hiss_scale", "scale 0. 100. 0. 0.3", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 200, 120, 20])

device.add_newobj("hiss_amp", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[160, 360, 30, 20])

# Sum processed + hiss (L and R)
device.add_newobj("sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 400, 30, 20])

device.add_newobj("sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 400, 30, 20])

# Dry/wet mix
# mix_dial 0-100 -> scale -> 0.0-1.0
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])

# Trigger to fan mix to wet and dry paths (t f f f fires right to left)
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 90, 55, 20])

# Invert mix for dry: !-~ 1. gives (1.0 - mix)
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 120, 50, 20])

# Wet gain multipliers
device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[20, 440, 30, 20])

device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 440, 30, 20])

# Dry gain multipliers
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 440, 30, 20])

device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[180, 440, 30, 20])

# Output sum wet + dry
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[80, 480, 30, 20])

device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[130, 480, 30, 20])

# --- Connections ---

# Input drive chain: plugin~ -> drive_l/r -> degrade_l/r
device.add_line("obj-plugin", 0, "drive_l", 0)   # plugin~ L -> drive_l signal
device.add_line("obj-plugin", 1, "drive_r", 0)   # plugin~ R -> drive_r signal
device.add_line("drive_dial", 0, "drive_scale", 0)
device.add_line("drive_scale", 0, "drive_l", 1)  # drive scale -> drive_l float
device.add_line("drive_scale", 0, "drive_r", 1)  # drive scale -> drive_r float

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

# Tone dial -> onepole~ cutoff freq (Hz directly, no scaling)
device.add_line("tone_dial", 0, "tone_l", 1)
device.add_line("tone_dial", 0, "tone_r", 1)

# Hiss chain
device.add_line("noise", 0, "hiss_svf", 0)       # noise~ -> svf~ signal

# Initialize svf~ freq and res via loadbang
device.add_line("lb", 0, "hiss_freq_msg", 0)
device.add_line("hiss_freq_msg", 0, "hiss_svf", 1)   # 5000 Hz -> svf~ freq
device.add_line("lb", 0, "hiss_res_msg", 0)
device.add_line("hiss_res_msg", 0, "hiss_svf", 2)    # 0.3 res -> svf~ res

# svf~ outlet 2 = bandpass -> hiss_amp
device.add_line("hiss_svf", 2, "hiss_amp", 0)        # bandpass out -> hiss amp signal

# Hiss dial -> scale -> hiss_amp inlet 1 (float)
device.add_line("hiss_dial", 0, "hiss_scale", 0)
device.add_line("hiss_scale", 0, "hiss_amp", 1)

# Sum processed signal + hiss
device.add_line("tone_l", 0, "sum_l", 0)          # processed L -> sum
device.add_line("tone_r", 0, "sum_r", 0)          # processed R -> sum
device.add_line("hiss_amp", 0, "sum_l", 1)        # hiss -> sum L
device.add_line("hiss_amp", 0, "sum_r", 1)        # hiss -> sum R (mono hiss)

# Dry/wet mix
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
# mix_trig: outlet 0 -> wet_l gain, outlet 1 -> wet_r gain, outlet 2 -> inverter
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
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

# --- Build ---
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/LoFi Processor.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
