"""Stereo multi-mode filter — m4l_builder example.

Showcase: COOL theme, hero filter curve display, Functional Flat style.

Layout (width=330, height=200):
  ┌──────────────────────────────────────────────────┐
  │ FILTER                                           │
  │ ┌──────────────────────────────────────────────┐ │
  │ │     FILTER CURVE DISPLAY (jsui)              │ │
  │ │     Shows frequency response                 │ │
  │ └──────────────────────────────────────────────┘ │
  │ [LP|HP|BP|NOTCH]                                 │
  │   [Freq]      [Res]       [Mix]     [L][R]       │
  └──────────────────────────────────────────────────┘

DSP signal flow:
  plugin~ L/R -> svf~ L/R (cutoff via line~, resonance via line~)
  svf~ 4 outlets -> selector~ 4 1 (LP/HP/BP/Notch)
  filter_type tab -> +1 -> selector~ (0-indexed -> 1-indexed)
  selector~ output -> dry/wet mix (via line~) -> plugout~

Parameter smoothing (20ms ramp via line~):
  freq_dial  -> freq_pk (pack f 20) -> freq_ln (line~) -> svf~ cutoff
  res_scale  -> res_pk  (pack f 20) -> res_ln  (line~) -> svf~ resonance
  mix_scale  -> mix_trig -> wet_pk/wet_r_pk -> wet_ln/wet_r_ln -> wet_l/wet_r *~
  mix_inv    -> dry_pk/dry_r_pk -> dry_ln/dry_r_ln -> dry_l/dry_r *~

Filter curve display:
  freq_dial  -> filter_display inlet 0 (freq Hz)
  res_scale  -> filter_display inlet 1 (resonance 0-1)
  filter_type -> filter_display inlet 2 (type 0-3)

Output meters on right edge (L/R vertical).
"""

import os
from m4l_builder import AudioEffect, COOL
from m4l_builder.engines.filter_curve import filter_curve_js

# --- Device setup ---
# Widened by 30px (300 -> 330) to accommodate L/R output meters on the right
device = AudioEffect("Stereo Filter", width=330, height=200, theme=COOL)

# =========================================================================
# UI
# =========================================================================

# Background panel
device.add_panel("bg", [0, 0, 330, 200])

# Title
device.add_comment("title", [8, 5, 80, 16], "FILTER",
                   fontname="Ableton Sans Bold", fontsize=13.0)

# Hero filter curve display — slightly narrower to leave room for meters
device.add_jsui("filter_display", [8, 24, 284, 80],
                js_code=filter_curve_js(
                    line_color="0.35, 0.60, 0.90, 1.0",
                    fill_color="0.35, 0.60, 0.90, 0.15",
                    bg_color="0.04, 0.05, 0.07, 1.0",
                ),
                numinlets=3)

# Filter type tab with rounded pill style
device.add_tab("filter_type", "Type", [8, 108, 284, 22],
               options=["LP", "HP", "BP", "NOTCH"],
               rounded=4.0, spacing_x=2.0)

# Dials row: Freq, Res, Mix
device.add_dial("freq_dial", "Freq", [20, 134, 70, 60],
                min_val=20.0, max_val=20000.0, initial=1000.0,
                unitstyle=3, parameter_exponent=3.0, appearance=1,
                annotation_name="Filter Cutoff")

device.add_dial("res_dial", "Res", [115, 134, 70, 60],
                min_val=0.0, max_val=100.0, initial=25.0,
                unitstyle=5, appearance=1,
                annotation_name="Resonance")

device.add_dial("mix_dial", "Mix", [210, 134, 70, 60],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Dry/Wet Mix")

# Output meters — right edge, vertical, 10px wide each with 2px gap
device.add_meter("meter_l", [298, 24, 12, 80],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])
device.add_meter("meter_r", [313, 24, 12, 80],
                 coldcolor=[0.3, 0.7, 0.35, 1.0],
                 warmcolor=[0.9, 0.8, 0.2, 1.0],
                 hotcolor=[0.9, 0.4, 0.1, 1.0],
                 overloadcolor=[0.9, 0.15, 0.15, 1.0])

# =========================================================================
# DSP objects
# =========================================================================

# svf~ for left and right channels
device.add_newobj("svf_l", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[30, 240, 40, 20])

device.add_newobj("svf_r", "svf~", numinlets=3, numoutlets=4,
                  outlettype=["signal", "signal", "signal", "signal"],
                  patching_rect=[150, 240, 40, 20])

# selector~ 4 1: 4 inputs, initial=1 (LP)
device.add_newobj("sel_l", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 300, 80, 20])

device.add_newobj("sel_r", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[150, 300, 80, 20])

# + 1 to offset live.tab 0-indexed output to selector~ 1-indexed input
device.add_newobj("tab_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[30, 210, 40, 20])

# Resonance scaling: dial 0-100 -> svf~ 0.0-1.0
device.add_newobj("res_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 195, 120, 20])

# ── Parameter smoothing: frequency ──────────────────────────────────────────
# freq_dial -> freq_pk (pack f 20) -> freq_ln (line~) -> svf_l/svf_r cutoff inlet
device.add_newobj("freq_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[270, 195, 60, 20])
device.add_newobj("freq_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[270, 225, 40, 20])

# ── Parameter smoothing: resonance ──────────────────────────────────────────
# res_scale -> res_pk (pack f 20) -> res_ln (line~) -> svf_l/svf_r resonance inlet
device.add_newobj("res_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 155, 60, 20])
device.add_newobj("res_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[30, 185, 40, 20])

# Dry/wet mix
device.add_newobj("mix_trig", "t f f f", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[400, 80, 55, 20])

device.add_newobj("mix_scale", "scale 0. 100. 0. 1.", numinlets=6, numoutlets=1,
                  outlettype=[""], patching_rect=[400, 60, 120, 20])

device.add_newobj("mix_inv", "!-~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[400, 110, 45, 20])

# ── Parameter smoothing: wet mix L ──────────────────────────────────────────
device.add_newobj("wet_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 130, 60, 20])
device.add_newobj("wet_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 160, 40, 20])

# ── Parameter smoothing: wet mix R ──────────────────────────────────────────
device.add_newobj("wet_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[360, 130, 60, 20])
device.add_newobj("wet_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[360, 160, 40, 20])

# ── Parameter smoothing: dry mix L ──────────────────────────────────────────
device.add_newobj("dry_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[460, 130, 60, 20])
device.add_newobj("dry_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[460, 160, 40, 20])

# ── Parameter smoothing: dry mix R ──────────────────────────────────────────
device.add_newobj("dry_r_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[520, 130, 60, 20])
device.add_newobj("dry_r_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[520, 160, 40, 20])

device.add_newobj("wet_l", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[300, 340, 30, 20])
device.add_newobj("wet_r", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[340, 340, 30, 20])

device.add_newobj("dry_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[460, 340, 30, 20])
device.add_newobj("dry_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[500, 340, 30, 20])

device.add_newobj("out_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[380, 380, 30, 20])
device.add_newobj("out_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 380, 30, 20])

# =========================================================================
# Connections
# =========================================================================

device.add_line("obj-plugin", 0, "svf_l", 0)
device.add_line("obj-plugin", 1, "svf_r", 0)

# Frequency smoothing: freq_dial -> pack -> line~ -> svf cutoff (inlet 1)
device.add_line("freq_dial", 0, "freq_pk", 0)
device.add_line("freq_pk", 0, "freq_ln", 0)
device.add_line("freq_ln", 0, "svf_l", 1)
device.add_line("freq_ln", 0, "svf_r", 1)

# Resonance scaling + smoothing: res_dial -> scale -> pack -> line~ -> svf resonance (inlet 2)
device.add_line("res_dial", 0, "res_scale", 0)
device.add_line("res_scale", 0, "res_pk", 0)
device.add_line("res_pk", 0, "res_ln", 0)
device.add_line("res_ln", 0, "svf_l", 2)
device.add_line("res_ln", 0, "svf_r", 2)

device.add_line("filter_type", 0, "tab_offset", 0)
device.add_line("tab_offset", 0, "sel_l", 0)
device.add_line("tab_offset", 0, "sel_r", 0)

device.add_line("svf_l", 0, "sel_l", 1)
device.add_line("svf_l", 1, "sel_l", 2)
device.add_line("svf_l", 2, "sel_l", 3)
device.add_line("svf_l", 3, "sel_l", 4)

device.add_line("svf_r", 0, "sel_r", 1)
device.add_line("svf_r", 1, "sel_r", 2)
device.add_line("svf_r", 2, "sel_r", 3)
device.add_line("svf_r", 3, "sel_r", 4)

# Mix smoothing chain
device.add_line("mix_dial", 0, "mix_scale", 0)
device.add_line("mix_scale", 0, "mix_trig", 0)

# Wet L: mix_trig outlet 0 -> pack -> line~ -> wet_l inlet 1
device.add_line("mix_trig", 0, "wet_pk", 0)
device.add_line("wet_pk", 0, "wet_ln", 0)
device.add_line("wet_ln", 0, "wet_l", 1)

# Wet R: mix_trig outlet 1 -> pack -> line~ -> wet_r inlet 1
device.add_line("mix_trig", 1, "wet_r_pk", 0)
device.add_line("wet_r_pk", 0, "wet_r_ln", 0)
device.add_line("wet_r_ln", 0, "wet_r", 1)

# Dry via !-~ (signal complement of wet): mix_trig outlet 2 -> !-~ inlet 0
device.add_line("mix_trig", 2, "mix_inv", 0)

# Dry L: mix_inv -> pack -> line~ -> dry_l inlet 1
device.add_line("mix_inv", 0, "dry_pk", 0)
device.add_line("dry_pk", 0, "dry_ln", 0)
device.add_line("dry_ln", 0, "dry_l", 1)

# Dry R: mix_inv -> pack -> line~ -> dry_r inlet 1
device.add_line("mix_inv", 0, "dry_r_pk", 0)
device.add_line("dry_r_pk", 0, "dry_r_ln", 0)
device.add_line("dry_r_ln", 0, "dry_r", 1)

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

# Connect parameters to filter curve display
device.add_line("freq_dial", 0, "filter_display", 0)    # freq Hz
device.add_line("res_scale", 0, "filter_display", 1)    # resonance 0-1
device.add_line("filter_type", 0, "filter_display", 2)  # type 0-3

# Output meters: tap from last processing stage (out_l/out_r) before plugout~
device.add_line("out_l", 0, "meter_l", 0)
device.add_line("out_r", 0, "meter_r", 0)

# =========================================================================
# Build
# =========================================================================
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/Stereo Filter.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
