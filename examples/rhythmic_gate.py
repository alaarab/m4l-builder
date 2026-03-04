"""Rhythmic Gate — LFO-driven amplitude gating with waveform selection."""

import os
from m4l_builder import AudioEffect, WARM, device_output_path
from m4l_builder.engines.lfo_display import lfo_display_js

device = AudioEffect("Rhythmic Gate", width=310, height=180, theme=WARM)

device.add_panel("bg", [0, 0, 310, 180])

# Waveform tab: SINE / SAW / SQUARE / TRI
device.add_tab("wave_tab", "Wave", [8, 26, 160, 22],
               options=["SINE", "SAW", "SQUARE", "TRI"],
               bgcolor=[0.2, 0.2, 0.22, 1.0],
               bgoncolor=[0.35, 0.55, 0.75, 1.0],
               textcolor=[0.75, 0.75, 0.75, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# Stereo mode tab: NORMAL / ALT
device.add_tab("stereo_tab", "Stereo", [172, 26, 100, 22],
               options=["NORMAL", "ALT"],
               bgcolor=[0.2, 0.2, 0.22, 1.0],
               bgoncolor=[0.55, 0.35, 0.75, 1.0],
               textcolor=[0.75, 0.75, 0.75, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0])

# Hero display: LFO waveform preview — shows shape, phase, and depth
device.add_jsui("lfo_preview", [8, 52, 264, 50],
                js_code=lfo_display_js(
                    bg_color="0.06, 0.06, 0.08, 1.0",
                    wave_color="0.85, 0.55, 0.25, 1.0",
                    playhead_color="1.0, 1.0, 1.0, 0.6",
                    grid_color="0.15, 0.15, 0.17, 0.4",
                ),
                numinlets=3)

# Output meters — right edge
device.add_meter("meter_l", [280, 5, 10, 170],
                 coldcolor=WARM.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [294, 5, 10, 170],
                 coldcolor=WARM.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# Section labels
device.add_comment("lbl_rhythm", [15, 98, 55, 12], "RHYTHM",
                   textcolor=[0.85, 0.55, 0.25, 0.6], fontsize=9.0)
device.add_comment("lbl_shape", [100, 98, 55, 12], "SHAPE",
                   textcolor=[0.85, 0.55, 0.25, 0.6], fontsize=9.0)
device.add_comment("lbl_output", [185, 98, 55, 12], "OUTPUT",
                   textcolor=[0.85, 0.55, 0.25, 0.6], fontsize=9.0)

# Dials row: Rate, Depth, Mix
device.add_dial("rate_dial", "Rate", [15, 108, 55, 75],
                min_val=0.25, max_val=20.0, initial=4.0,
                unitstyle=3,
                annotation_name="Gate Rate")   # HZ

device.add_dial("depth_dial", "Depth", [100, 108, 55, 75],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5,
                annotation_name="Gate Depth")   # PERCENT

device.add_dial("mix_dial", "Mix", [185, 108, 55, 75],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5,
                annotation_name="Dry/Wet Mix")   # PERCENT

# --- Parameter smoothing: rate_dial -> all 4 oscillator freq inlets (smoothed) ---
# Single pack+line~ for rate; then trigger distributes to all 4 oscillators.
# line~ outputs signal; cycle~/phasor~/rect~ accept signal on inlet 0.
device.add_newobj("rate_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[60, 178, 60, 20])
device.add_newobj("rate_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[60, 208, 40, 20])

# --- Parameter smoothing: depth_scale -> depth_mul inlet 1 (smoothed) ---
device.add_newobj("depth_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[330, 248, 60, 20])
device.add_newobj("depth_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[330, 278, 40, 20])

# LFO oscillators — all accept freq signal on inlet 0
# 1. Sine: cycle~ → *~ 0.5 → +~ 0.5 (convert -1..1 to 0..1)
device.add_newobj("lfo_sine", "cycle~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 238, 50, 20])
device.add_newobj("sine_scale", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 263, 55, 20])
device.add_newobj("sine_offset", "+~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 288, 55, 20])

# 2. Sawtooth: phasor~ already outputs 0..1
device.add_newobj("lfo_saw", "phasor~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[100, 238, 55, 20])

# 3. Square: rect~ 0.5 (50% duty) → *~ 0.5 → +~ 0.5 (convert ±1 to 0..1)
device.add_newobj("lfo_rect", "rect~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 238, 50, 20])
device.add_newobj("rect_scale", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 263, 55, 20])
device.add_newobj("rect_offset", "+~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[170, 288, 55, 20])

# rect~ duty cycle float input — fixed at 0.5
device.add_newobj("rect_duty", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[170, 213, 55, 20])
device.add_newobj("rect_duty_val", "float 0.5", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[230, 213, 65, 20])

# 4. Triangle: phasor~ → *~ 2. → +~ -1. → abs~ (gives 0..1 triangle)
device.add_newobj("lfo_tri_phasor", "phasor~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 238, 55, 20])
device.add_newobj("tri_scale", "*~ 2.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 263, 50, 20])
device.add_newobj("tri_shift", "+~ -1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 288, 55, 20])
device.add_newobj("tri_abs", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 313, 40, 20])
# Invert: 1 - abs result to get peak-up triangle (0=low, 1=peak)
device.add_newobj("tri_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[240, 338, 50, 20])

# Waveform selector~ 4 1: selects among 4 unipolar LFO signals
# inlets: 0=int selector, 1=sine, 2=saw, 3=square, 4=tri
device.add_newobj("lfo_sel", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[140, 368, 80, 20])

# +1 offset: live.tab 0-indexed → selector~ 1-indexed
device.add_newobj("wave_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[140, 338, 40, 20])

# Depth control: gain = LFO * depth + (1 - depth)
# Scale depth dial 0-100 -> 0.0-1.0
device.add_newobj("depth_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[330, 238, 120, 20])

# Depth multiply: LFO * depth_factor (smoothed via depth_ln)
device.add_newobj("depth_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[330, 308, 30, 20])

# Compute (1 - depth) for the constant offset: !- 1 on depth float
device.add_newobj("depth_inv", "!- 1.", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[380, 238, 50, 20])

# Add (1 - depth) to the LFO*depth signal: final_gain = LFO*depth + (1-depth)
device.add_newobj("gain_add", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[330, 338, 30, 20])

# Stereo mode ping-pong: invert gain for R channel via !-~ 1.
# When stereo=PING-PONG: R_gain = 1 - L_gain
device.add_newobj("gain_inv_r", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 338, 50, 20])

# Stereo selector~ 2 1: normal=final_gain, ping-pong=inverted_gain for R
# inlets: 0=int selector, 1=normal (final_gain), 2=ping-pong (inverted)
device.add_newobj("stereo_sel", "selector~ 2 1", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 368, 80, 20])
device.add_newobj("stereo_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[460, 338, 40, 20])

# Apply gain to audio: plugin~ L * final_gain_l, plugin~ R * stereo_gain_r
device.add_newobj("gate_l", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[330, 408, 30, 20])
device.add_newobj("gate_r", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 408, 30, 20])

# Dry/wet mix
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[500, 238, 120, 20])

device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[500, 268, 55, 20])

device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 298, 45, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 438, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 438, 30, 20])

device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[550, 438, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[590, 438, 30, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 478, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[540, 478, 30, 20])

# LFO preview: phasor~ for phase tracking -> snapshot~ -> jsui inlet 1
device.add_newobj("lfo_phase_phasor", "phasor~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 238, 55, 20])
device.add_newobj("lfo_phase_snap", "snapshot~ 4", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[500, 268, 70, 20])

# Depth 0-100 -> 0-1 for jsui inlet 2
device.add_newobj("depth_disp_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[580, 238, 120, 20])

# Rate dial -> pack+line~ (smoothed signal) -> all 4 oscillator freq inlets
device.add_line("rate_dial", 0, "rate_pk", 0)
device.add_line("rate_pk", 0, "rate_ln", 0)
device.add_line("rate_ln", 0, "lfo_sine", 0)         # smoothed signal -> sine freq
device.add_line("rate_ln", 0, "lfo_saw", 0)           # smoothed signal -> saw freq
device.add_line("rate_ln", 0, "lfo_rect", 0)          # smoothed signal -> rect freq
device.add_line("rate_ln", 0, "lfo_tri_phasor", 0)    # smoothed signal -> tri phasor freq

# rect~ duty cycle: loadbang -> float 0.5 -> rect~ inlet 1
device.add_line("rect_duty", 0, "rect_duty_val", 0)
device.add_line("rect_duty_val", 0, "lfo_rect", 1)

# Sine chain: cycle~ -> *~ 0.5 -> +~ 0.5 -> selector~ inlet 1
device.add_line("lfo_sine", 0, "sine_scale", 0)
device.add_line("sine_scale", 0, "sine_offset", 0)
device.add_line("sine_offset", 0, "lfo_sel", 1)

# Saw: phasor~ -> selector~ inlet 2
device.add_line("lfo_saw", 0, "lfo_sel", 2)

# Square chain: rect~ -> *~ 0.5 -> +~ 0.5 -> selector~ inlet 3
device.add_line("lfo_rect", 0, "rect_scale", 0)
device.add_line("rect_scale", 0, "rect_offset", 0)
device.add_line("rect_offset", 0, "lfo_sel", 3)

# Triangle chain: phasor~ -> *~ 2 -> +~ -1 -> abs~ -> !-~ 1 -> selector~ inlet 4
device.add_line("lfo_tri_phasor", 0, "tri_scale", 0)
device.add_line("tri_scale", 0, "tri_shift", 0)
device.add_line("tri_shift", 0, "tri_abs", 0)
device.add_line("tri_abs", 0, "tri_inv", 0)
device.add_line("tri_inv", 0, "lfo_sel", 4)

# Waveform tab -> +1 offset -> lfo_sel int inlet
device.add_line("wave_tab", 0, "wave_offset", 0)
device.add_line("wave_offset", 0, "lfo_sel", 0)

# Depth: dial -> scale -> pack+line~ (smoothed) -> depth_mul signal inlet
device.add_line("depth_dial", 0, "depth_scale", 0)
device.add_line("depth_scale", 0, "depth_pk", 0)
device.add_line("depth_pk", 0, "depth_ln", 0)
device.add_line("depth_ln", 0, "depth_mul", 1)   # smoothed depth_mul inlet 1

# depth_inv still uses float path (it feeds +~ inlet 1 as a float offset, which is fine)
device.add_line("depth_scale", 0, "depth_inv", 0)   # depth_inv computes 1-depth

# LFO * depth -> selector outlet to depth_mul signal inlet 0
device.add_line("lfo_sel", 0, "depth_mul", 0)

# LFO*depth + (1-depth) = final_gain
device.add_line("depth_mul", 0, "gain_add", 0)
device.add_line("depth_inv", 0, "gain_add", 1)      # +~ inlet 1 accepts float

# Stereo: final_gain goes directly to gate_l
device.add_line("gain_add", 0, "gate_l", 1)         # gate_l inlet 1 = gain

# Ping-pong: invert final_gain for R
device.add_line("gain_add", 0, "gain_inv_r", 0)    # !-~ 1. inlet 0

# Stereo selector~ for R channel: normal=final_gain, ping-pong=inverted
device.add_line("gain_add", 0, "stereo_sel", 1)    # inlet 1 = normal
device.add_line("gain_inv_r", 0, "stereo_sel", 2)  # inlet 2 = ping-pong
device.add_line("stereo_tab", 0, "stereo_offset", 0)
device.add_line("stereo_offset", 0, "stereo_sel", 0)

# Stereo selector output -> gate_r gain
device.add_line("stereo_sel", 0, "gate_r", 1)

# Audio input -> gate multipliers (signal inlets)
device.add_line("obj-plugin", 0, "gate_l", 0)      # plugin~ L -> gate_l signal
device.add_line("obj-plugin", 1, "gate_r", 0)      # plugin~ R -> gate_r signal

# Mix: dial -> scale -> trigger -> wet/dry
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

# Wet signal: gated output -> wet multipliers
device.add_line("gate_l", 0, "wet_l", 0)
device.add_line("gate_r", 0, "wet_r", 0)

# Dry signal: plugin~ -> dry multipliers
device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

# Sum wet + dry -> out
device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

# Output -> plugout~
device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# LFO preview display: wave_tab -> inlet 0 (shape), phase -> inlet 1, depth -> inlet 2
device.add_line("wave_tab", 0, "lfo_preview", 0)
device.add_line("rate_ln", 0, "lfo_phase_phasor", 0)
device.add_line("lfo_phase_phasor", 0, "lfo_phase_snap", 0)
device.add_line("lfo_phase_snap", 0, "lfo_preview", 1)
device.add_line("depth_dial", 0, "depth_disp_scale", 0)
device.add_line("depth_disp_scale", 0, "lfo_preview", 2)

# Output meters: tap final output
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

output = device_output_path("Rhythmic Gate")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
