"""Auto-Filter — envelope follower + LFO modulating SVF filter cutoff.

Showcase: MIDNIGHT theme, hero filter curve display showing frequency response.

Layout (width=440, height=230):
  ┌──────────────────────────────────────────────────────┐
  │ ┌──────────────────────────────────────────────┐     │
  │ │                                              │ L R │
  │ │         FILTER CURVE DISPLAY                │ │ │ │
  │ │         (hero — ~55% of height)             │ │ │ │
  │ │                                              │ │ │ │
  │ └──────────────────────────────────────────────┘     │
  │ FILTER          ENVELOPE           LFO              │
  │ [Cutoff] [Res]  [Depth] [Atk] [Rel] [Dpth][Rate]   │
  │ [LP|HP|BP|NOTCH]                   [Mix]            │
  └──────────────────────────────────────────────────────┘

DSP signal flow:

Envelope path:
  plugin~ L + R -> abs~ L + abs~ R -> +~ -> *~ 0.5 -> slide~ attack release
  -> *~ env_depth = env_offset_hz

LFO path:
  cycle~ rate -> *~ 0.5 -> +~ 0.5 (unipolar 0-1) -> *~ lfo_depth = lfo_offset_hz

Modulation sum:
  base_freq (from cutoff_dial) + env_offset + lfo_offset -> svf~ inlet 1

Filter:
  plugin~ L -> svf_l (inlet 0), plugin~ R -> svf_r (inlet 0)
  Resonance: res_dial -> scale 0. 100. 0. 1. -> pack+line~ -> svf~ inlet 2
  Mode: svf~ 4 outlets (LP=0, HP=1, BP=2, notch=3) -> selector~ 4 1

Dry/wet mix -> plugout~

Filter curve display:
  cutoff_dial -> filter_display inlet 0 (freq)
  res_scale   -> filter_display inlet 1 (resonance 0-1)
  filter_type -> filter_display inlet 2 (type 0-3)

Parameter smoothing:
  All float-to-signal connections routed through pack f 20 -> line~

CRITICAL RULES:
  - No sig~ (floats sent directly to inlets)
  - selector~ 4 1 (always has initial arg)
  - live.tab +1 offset for selector~
  - panels background:1
  - slide~ args in SAMPLES (ms * 44.1)
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT, device_output_path
from m4l_builder.engines.filter_curve import filter_curve_js

# Device — taller to give the filter display more visual weight
device = AudioEffect("Auto Filter", width=440, height=230, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

# Background panel
device.add_panel("bg", [0, 0, 440, 230])

# ---- HERO: Filter curve display — takes 55% of height ----
device.add_jsui("filter_display", [10, 8, 360, 118],
                js_code=filter_curve_js(
                    line_color="0.45, 0.75, 0.65, 1.0",
                    fill_color="0.45, 0.75, 0.65, 0.15",
                    bg_color="0.05, 0.05, 0.06, 1.0",
                    grid_color="0.2, 0.2, 0.22, 0.5",
                    text_color="0.5, 0.5, 0.52, 1.0",
                    cursor_color="0.8, 0.8, 0.8, 0.4",
                ),
                numinlets=3)

# Output meters — right edge, full height
device.add_meter("meter_l", [414, 5, 10, 220],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [428, 5, 10, 220],
                 coldcolor=MIDNIGHT.accent,
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# Live cutoff Hz readout — prominent, sits below the display
device.add_comment("lbl_hz", [376, 10, 30, 11], "Hz",
                   textcolor=[0.45, 0.75, 0.65, 0.6], fontsize=8.5)
device.add_number_box("cutoff_hz", "Cutoff Hz", [376, 22, 34, 22],
                      min_val=20.0, max_val=20000.0, initial=1000.0,
                      fontsize=9.0,
                      textcolor=[0.45, 0.75, 0.65, 1.0],
                      bgcolor=[0.07, 0.07, 0.09, 1.0],
                      bordercolor=[0.25, 0.25, 0.28, 0.7])

# Section labels row (y=132)
device.add_comment("lbl_filter", [8, 132, 60, 11], "FILTER",
                   textcolor=[0.45, 0.75, 0.65, 1.0], fontsize=8.5)

device.add_comment("lbl_env", [128, 132, 70, 11], "ENVELOPE",
                   textcolor=[0.85, 0.65, 0.25, 1.0], fontsize=8.5)

device.add_comment("lbl_lfo", [260, 132, 40, 11], "LFO",
                   textcolor=[0.45, 0.75, 0.65, 1.0], fontsize=8.5)

# --- Filter section dials (y=142) ---
device.add_dial("cutoff_dial", "Cutoff", [5, 142, 55, 56],
                min_val=20.0, max_val=20000.0, initial=1000.0,
                unitstyle=3, appearance=1, parameter_exponent=3.0,
                annotation_name="Filter Cutoff Frequency")

device.add_dial("res_dial", "Resonance", [62, 142, 55, 56],
                min_val=0.0, max_val=100.0, initial=25.0,
                unitstyle=5, appearance=1,
                annotation_name="Filter Resonance")

# Mode tab — below filter dials
device.add_tab("filter_type", "Mode", [5, 200, 115, 22],
               options=["LP", "HP", "BP", "NOTCH"],
               rounded=3.0, spacing_x=1.0)

# --- Envelope section dials (y=142) ---
device.add_dial("env_depth_dial", "Env Depth", [123, 142, 52, 56],
                min_val=0.0, max_val=10000.0, initial=500.0,
                unitstyle=3, appearance=1,
                annotation_name="Envelope Modulation Depth")

device.add_dial("attack_dial", "Attack", [177, 142, 52, 56],
                min_val=1.0, max_val=500.0, initial=10.0,
                unitstyle=2, appearance=1,
                annotation_name="Envelope Attack Time")

device.add_dial("release_dial", "Release", [231, 142, 52, 56],
                min_val=10.0, max_val=2000.0, initial=100.0,
                unitstyle=2, appearance=1,
                annotation_name="Envelope Release Time")

# --- LFO section dials (y=142) ---
device.add_dial("lfo_depth_dial", "LFO Depth", [290, 142, 42, 56],
                min_val=0.0, max_val=10000.0, initial=200.0,
                unitstyle=3, appearance=1,
                annotation_name="LFO Modulation Depth")

device.add_dial("rate_dial", "Rate", [334, 142, 42, 56],
                min_val=0.1, max_val=20.0, initial=1.0,
                unitstyle=1, appearance=1,
                annotation_name="LFO Rate")

# Mix dial — bottom right corner, aligned with LFO section
device.add_comment("lbl_mix", [376, 132, 34, 11], "MIX",
                   textcolor=MIDNIGHT.accent, fontsize=8.5)
device.add_dial("mix_dial", "Mix", [376, 142, 34, 56],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet Mix")

# =========================================================================
# DSP objects
# =========================================================================

# --- Resonance scaling (0-100 -> 0-1 for svf~ and filter_display) ---
device.add_newobj("res_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 300, 120, 20])

# --- Parameter smoothing: resonance -> svf~ inlet 2 ---
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 325, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 355, 40, 20])

# --- Parameter smoothing: cutoff_dial -> mod_sum2 inlet 1 ---
device.add_newobj("cutoff_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[160, 325, 60, 20])
device.add_newobj("cutoff_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[160, 355, 40, 20])

# --- Parameter smoothing: env_depth_dial -> env_scale inlet 1 ---
device.add_newobj("envd_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[60, 448, 60, 20])
device.add_newobj("envd_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[60, 478, 40, 20])

# --- Parameter smoothing: rate_dial -> lfo_osc inlet 0 ---
device.add_newobj("rate_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 348, 60, 20])
device.add_newobj("rate_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 378, 40, 20])

# --- Parameter smoothing: lfo_depth_dial -> lfo_depth_mul inlet 1 ---
device.add_newobj("lfod_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 423, 60, 20])
device.add_newobj("lfod_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 453, 40, 20])

# --- Attack/Release: ms -> samples ---
device.add_newobj("attack_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 330, 60, 20])
device.add_newobj("release_samp", "* 44.1", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[130, 330, 60, 20])

# --- Envelope follower ---
device.add_newobj("abs_l", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 360, 35, 20])
device.add_newobj("abs_r", "abs~", numinlets=1, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 360, 35, 20])
device.add_newobj("env_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 385, 30, 20])
device.add_newobj("env_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 410, 45, 20])
device.add_newobj("env_follow", "slide~", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 435, 45, 20])
device.add_newobj("env_scale", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[60, 505, 30, 20])

# --- LFO path ---
device.add_newobj("lfo_osc", "cycle~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 403, 45, 20])
device.add_newobj("lfo_scale", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 428, 45, 20])
device.add_newobj("lfo_shift", "+~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 453, 45, 20])
device.add_newobj("lfo_depth_mul", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[200, 478, 30, 20])

# --- Modulation sum ---
device.add_newobj("mod_sum1", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[130, 510, 30, 20])
device.add_newobj("mod_sum2", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[130, 535, 30, 20])
device.add_newobj("cutoff_snap", "snapshot~ 1", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[130, 560, 70, 20])

# --- SVF filters ---
device.add_newobj("svf_l", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[30, 590, 40, 20])
device.add_newobj("svf_r", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[150, 590, 40, 20])

# --- Mode selector (live.tab is 0-indexed, selector~ is 1-indexed) ---
device.add_newobj("tab_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 630, 40, 20])

device.add_newobj("sel_l", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 655, 80, 20])
device.add_newobj("sel_r", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[150, 655, 80, 20])

# --- Dry/wet mix ---
device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 90, 55, 20])
device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 120, 45, 20])
device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 690, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 690, 30, 20])
device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 690, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 690, 30, 20])
device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 730, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 730, 30, 20])

# =========================================================================
# Connections
# =========================================================================

# --- Audio input to filters ---
device.add_line("obj-plugin", 0, "svf_l", 0)
device.add_line("obj-plugin", 1, "svf_r", 0)

# --- Resonance -> scale -> pack+line~ -> svf~ inlet 2 (smoothed) ---
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "svf_l", 2)
device.add_line("res_ln", 0, "svf_r", 2)
device.add_line("res_scale", 0, "filter_display", 1)   # resonance 0-1 to curve display (unsmoothed, UI only)

# --- Attack/Release ms -> samples ---
device.add_line("attack_dial", 0, "attack_samp", 0)
device.add_line("attack_samp", 0, "env_follow", 1)

device.add_line("release_dial", 0, "release_samp", 0)
device.add_line("release_samp", 0, "env_follow", 2)

# --- Envelope follower path ---
device.add_line("obj-plugin", 0, "abs_l", 0)
device.add_line("obj-plugin", 1, "abs_r", 0)
device.add_line("abs_l", 0, "env_sum", 0)
device.add_line("abs_r", 0, "env_sum", 1)
device.add_line("env_sum", 0, "env_avg", 0)
device.add_line("env_avg", 0, "env_follow", 0)
device.add_line("env_follow", 0, "env_scale", 0)

# --- Env depth: dial -> pack+line~ -> env_scale inlet 1 (smoothed) ---
device.add_line("env_depth_dial", 0, "envd_pk", 0)
device.add_line("envd_pk", 0, "envd_ln", 0)
device.add_line("envd_ln", 0, "env_scale", 1)

# --- LFO rate: dial -> pack+line~ -> cycle~ inlet 0 (smoothed) ---
device.add_line("rate_dial", 0, "rate_pk", 0)
device.add_line("rate_pk", 0, "rate_ln", 0)
device.add_line("rate_ln", 0, "lfo_osc", 0)

device.add_line("lfo_osc", 0, "lfo_scale", 0)
device.add_line("lfo_scale", 0, "lfo_shift", 0)
device.add_line("lfo_shift", 0, "lfo_depth_mul", 0)

# --- LFO depth: dial -> pack+line~ -> lfo_depth_mul inlet 1 (smoothed) ---
device.add_line("lfo_depth_dial", 0, "lfod_pk", 0)
device.add_line("lfod_pk", 0, "lfod_ln", 0)
device.add_line("lfod_ln", 0, "lfo_depth_mul", 1)

# --- Cutoff: dial -> pack+line~ -> mod_sum2 inlet 1 (smoothed) ---
device.add_line("cutoff_dial", 0, "cutoff_pk", 0)
device.add_line("cutoff_pk", 0, "cutoff_ln", 0)

# --- Modulation sum -> cutoff -> SVF ---
device.add_line("env_scale", 0, "mod_sum1", 0)
device.add_line("lfo_depth_mul", 0, "mod_sum1", 1)
device.add_line("mod_sum1", 0, "mod_sum2", 0)
device.add_line("cutoff_ln", 0, "mod_sum2", 1)
device.add_line("mod_sum2", 0, "cutoff_snap", 0)
device.add_line("cutoff_snap", 0, "svf_l", 1)
device.add_line("cutoff_snap", 0, "svf_r", 1)

# --- Modulated cutoff to filter curve display (animated sweep!) ---
device.add_line("cutoff_snap", 0, "filter_display", 0)   # modulated freq Hz

# --- Filter type to selector and display ---
device.add_line("filter_type", 0, "tab_offset", 0)
device.add_line("tab_offset", 0, "sel_l", 0)
device.add_line("tab_offset", 0, "sel_r", 0)
device.add_line("filter_type", 0, "filter_display", 2)   # type 0-3

# --- SVF outputs -> selector ---
device.add_line("svf_l", 0, "sel_l", 1)
device.add_line("svf_l", 1, "sel_l", 2)
device.add_line("svf_l", 2, "sel_l", 3)
device.add_line("svf_l", 3, "sel_l", 4)

device.add_line("svf_r", 0, "sel_r", 1)
device.add_line("svf_r", 1, "sel_r", 2)
device.add_line("svf_r", 2, "sel_r", 3)
device.add_line("svf_r", 3, "sel_r", 4)

# --- Dry/wet mix ---
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)
device.add_line("mix_trig", 0, "wet_l", 1)
device.add_line("mix_trig", 1, "wet_r", 1)
device.add_line("mix_trig", 2, "mix_inv", 0)
device.add_line("mix_inv", 0, "dry_l", 1)
device.add_line("mix_inv", 0, "dry_r", 1)

device.add_line("sel_l", 0, "wet_l", 0)
device.add_line("sel_r", 0, "wet_r", 0)

device.add_line("obj-plugin", 0, "dry_l", 0)
device.add_line("obj-plugin", 1, "dry_r", 0)

device.add_line("wet_l", 0, "out_l", 0)
device.add_line("dry_l", 0, "out_l", 1)
device.add_line("wet_r", 0, "out_r", 0)
device.add_line("dry_r", 0, "out_r", 1)

device.add_line("out_l", 0, "obj-plugout", 0)
device.add_line("out_r", 0, "obj-plugout", 1)

# --- Live cutoff Hz readout ---
device.add_line("cutoff_snap", 0, "cutoff_hz", 0)

# --- Output meters: tap final output ---
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Auto Filter")  # width=440, height=230
written = device.build(output)
print(f"Built {written} bytes -> {output}")
