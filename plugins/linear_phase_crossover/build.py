"""Linear-Phase Crossover — complementary FFT crossover for phase-safe band work.

Design goals:
  - Split stereo audio into low/mid/high bands without IIR crossover phase skew
  - Preserve flat recombination when monitor mode is set to SUM
  - Let the user audition each band and trim levels after the split

Implementation notes:
  - Uses pfft~ with a companion .maxpat spectral kernel written next to the .amxd
  - The spectral kernel applies complementary magnitude masks only, which preserves
    phase inside each FFT frame and avoids the minimum-phase crossover shifts you
    get from typical EQ-style splitting
  - Trade-off: linear-phase FFT processing adds latency and can ring around very
    sharp transitions, so the crossover masks use a small 4-bin crossfade
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path, newobj, patchline
from m4l_builder.engines import crossover_display_js


FFT_SIZE = 4096
FFT_OVERLAP = 4
TRANSITION_BINS = 4.0
PFFT_NAME = "linear_phase_splitter_core"
PFFT_FILENAME = f"{PFFT_NAME}.maxpat"


def _support_patcher(boxes, lines, width=1200.0, height=900.0):
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {
                "major": 8,
                "minor": 6,
                "revision": 0,
                "architecture": "x64",
                "modernui": 1,
            },
            "classnamespace": "box",
            "rect": [50.0, 50.0, width, height],
            "bglocked": 0,
            "openinpresentation": 0,
            "default_fontface": 0,
            "default_fontname": "Arial",
            "default_fontsize": 10.0,
            "gridonopen": 1,
            "gridsize": [15.0, 15.0],
            "gridsnaponopen": 1,
            "objectsnaponopen": 1,
            "statusbarvisible": 2,
            "toolbarvisible": 1,
            "boxes": boxes,
            "lines": lines,
        }
    }


def build_splitter_kernel():
    boxes = []
    lines = []

    def add(box):
        boxes.append(box)

    def wire(src_id, src_outlet, dest_id, dest_inlet):
        lines.append(patchline(src_id, src_outlet, dest_id, dest_inlet))

    add(newobj("fft_l", "fftin~ 1", numinlets=1, numoutlets=3,
               outlettype=["signal", "signal", "signal"],
               patching_rect=[40, 40, 55, 20]))
    add(newobj("fft_r", "fftin~ 2", numinlets=1, numoutlets=3,
               outlettype=["signal", "signal", "signal"],
               patching_rect=[280, 40, 55, 20]))

    add(newobj("recv_low", "r lps_low_bin", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[40, 95, 75, 20]))
    add(newobj("recv_high", "r lps_high_bin", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[140, 95, 80, 20]))

    add(newobj("low_top", f"+ {TRANSITION_BINS}", numinlets=2, numoutlets=1,
               outlettype=[""], patching_rect=[40, 125, 45, 20]))
    add(newobj("high_bottom", f"- {TRANSITION_BINS}", numinlets=2, numoutlets=1,
               outlettype=[""], patching_rect=[140, 125, 45, 20]))

    add(newobj("low_sub", "-~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[40, 170, 35, 20]))
    add(newobj("low_scale", "*~ -0.125", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[40, 200, 65, 20]))
    add(newobj("low_mask", "clip~ 0. 1.", numinlets=3, numoutlets=1,
               outlettype=["signal"], patching_rect=[40, 230, 75, 20]))

    add(newobj("high_sub", "-~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[140, 170, 35, 20]))
    add(newobj("high_scale", "*~ 0.125", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[140, 200, 60, 20]))
    add(newobj("high_mask", "clip~ 0. 1.", numinlets=3, numoutlets=1,
               outlettype=["signal"], patching_rect=[140, 230, 75, 20]))

    add(newobj("mask_sum", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[90, 270, 35, 20]))
    add(newobj("mid_inv", "*~ -1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[90, 300, 50, 20]))
    add(newobj("mid_add", "+~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[90, 330, 45, 20]))
    add(newobj("mid_mask", "clip~ 0. 1.", numinlets=3, numoutlets=1,
               outlettype=["signal"], patching_rect=[90, 360, 75, 20]))

    band_outlets = {
        "low": 1,
        "mid": 2,
        "high": 3,
    }
    channel_base_x = {
        "l": 40,
        "r": 280,
    }
    channel_fft = {
        "l": "fft_l",
        "r": "fft_r",
    }
    mask_ids = {
        "low": "low_mask",
        "mid": "mid_mask",
        "high": "high_mask",
    }

    for channel in ("l", "r"):
        base_x = channel_base_x[channel]
        fft_id = channel_fft[channel]

        for index, band in enumerate(("low", "mid", "high")):
            y = 430 + index * 105
            band_out = band_outlets[band] + (0 if channel == "l" else 3)
            mask_id = mask_ids[band]

            add(newobj(f"{band}_{channel}_real", "*~", numinlets=2, numoutlets=1,
                       outlettype=["signal"], patching_rect=[base_x, y, 35, 20]))
            add(newobj(f"{band}_{channel}_imag", "*~", numinlets=2, numoutlets=1,
                       outlettype=["signal"], patching_rect=[base_x + 50, y, 35, 20]))
            add(newobj(f"{band}_{channel}_out", f"fftout~ {band_out}",
                       numinlets=2, numoutlets=0,
                       patching_rect=[base_x, y + 30, 60, 20]))

            wire(fft_id, 0, f"{band}_{channel}_real", 0)
            wire(fft_id, 1, f"{band}_{channel}_imag", 0)
            wire(mask_id, 0, f"{band}_{channel}_real", 1)
            wire(mask_id, 0, f"{band}_{channel}_imag", 1)
            wire(f"{band}_{channel}_real", 0, f"{band}_{channel}_out", 0)
            wire(f"{band}_{channel}_imag", 0, f"{band}_{channel}_out", 1)

    wire("recv_low", 0, "low_top", 0)
    wire("recv_high", 0, "high_bottom", 0)

    wire("fft_l", 2, "low_sub", 0)
    wire("fft_l", 2, "high_sub", 0)
    wire("low_top", 0, "low_sub", 1)
    wire("high_bottom", 0, "high_sub", 1)

    wire("low_sub", 0, "low_scale", 0)
    wire("low_scale", 0, "low_mask", 0)

    wire("high_sub", 0, "high_scale", 0)
    wire("high_scale", 0, "high_mask", 0)

    wire("low_mask", 0, "mask_sum", 0)
    wire("high_mask", 0, "mask_sum", 1)
    wire("mask_sum", 0, "mid_inv", 0)
    wire("mid_inv", 0, "mid_add", 0)
    wire("mid_add", 0, "mid_mask", 0)

    return json.dumps(_support_patcher(boxes, lines), indent=2)


BG = [0.05, 0.05, 0.06, 1.0]
SURFACE = [0.10, 0.10, 0.12, 1.0]
SURFACE_ALT = [0.12, 0.13, 0.15, 1.0]
TEXT = [0.90, 0.93, 0.97, 1.0]
TEXT_DIM = [0.58, 0.63, 0.69, 1.0]
LOW_COLOR = [0.30, 0.58, 0.88, 1.0]
MID_COLOR = [0.38, 0.78, 0.58, 1.0]
HIGH_COLOR = [0.92, 0.58, 0.28, 1.0]

device = AudioEffect("Linear Phase Crossover", width=548, height=214, theme=MIDNIGHT)
device.add_support_file(PFFT_FILENAME, build_splitter_kernel(), file_type="JSON")

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 548, 214], bgcolor=BG)

device.add_comment("title", [12, 6, 194, 14], "LINEAR-PHASE CROSSOVER",
                   fontname="Ableton Sans Bold", fontsize=11.5,
                   textcolor=TEXT)
device.add_comment("subtitle", [12, 19, 270, 10],
                   "Dedicated FFT band splitter for clean multiband routing",
                   fontsize=8.0, textcolor=TEXT_DIM)
device.add_comment("latency_note", [330, 7, 198, 20],
                   "Use for split-band processing. Flat-sum when aligned.",
                   fontsize=8.0, textcolor=TEXT_DIM, justification=2)

device.add_panel("display_shell", [8, 32, 504, 94],
                 bgcolor=SURFACE, rounded=6,
                 border=1, bordercolor=[0.18, 0.20, 0.24, 1.0])
device.add_jsui("xover_display", [12, 36, 496, 86],
                js_code=crossover_display_js(),
                numinlets=3,
                patching_rect=[20, 40, 496, 86])

device.add_comment("meter_tag", [515, 36, 22, 9], "OUT",
                   fontsize=6.5, textcolor=TEXT_DIM, justification=1)
device.add_meter("meter_l", [516, 48, 10, 74],
                 coldcolor=[0.30, 0.58, 0.88, 1.0],
                 warmcolor=[0.67, 0.82, 0.96, 1.0],
                 hotcolor=[0.96, 0.84, 0.40, 1.0],
                 overloadcolor=[0.92, 0.24, 0.16, 1.0])
device.add_meter("meter_r", [530, 48, 10, 74],
                 coldcolor=[0.30, 0.58, 0.88, 1.0],
                 warmcolor=[0.67, 0.82, 0.96, 1.0],
                 hotcolor=[0.96, 0.84, 0.40, 1.0],
                 overloadcolor=[0.92, 0.24, 0.16, 1.0])

device.add_panel("xover_panel", [8, 132, 176, 74],
                 bgcolor=SURFACE_ALT, rounded=6)
device.add_comment("lbl_xover", [16, 138, 90, 10], "CROSSOVERS",
                   fontsize=8.0, textcolor=[0.75, 0.82, 0.90, 1.0])
device.add_dial("low_xover", "Low Xover", [16, 148, 72, 56],
                min_val=40.0, max_val=1200.0, initial=160.0,
                unitstyle=3, appearance=1, parameter_exponent=2.2,
                activedialcolor=LOW_COLOR,
                annotation_name="Low to mid crossover frequency")
device.add_dial("high_xover", "High Xover", [96, 148, 72, 56],
                min_val=1500.0, max_val=16000.0, initial=3200.0,
                unitstyle=3, appearance=1, parameter_exponent=2.2,
                activedialcolor=HIGH_COLOR,
                annotation_name="Mid to high crossover frequency")

device.add_panel("trim_panel", [190, 132, 160, 74],
                 bgcolor=SURFACE_ALT, rounded=6)
device.add_comment("lbl_trim", [198, 138, 80, 10], "BAND TRIM",
                   fontsize=8.0, textcolor=[0.75, 0.82, 0.90, 1.0])

band_meta = (
    ("low", "LOW", [198, 148, 44, 56], LOW_COLOR),
    ("mid", "MID", [248, 148, 44, 56], MID_COLOR),
    ("high", "HIGH", [298, 148, 44, 56], HIGH_COLOR),
)

for band_id, label, rect, color in band_meta:
    device.add_dial(f"trim_{band_id}", f"{label.title()} Trim", rect,
                    min_val=-18.0, max_val=18.0, initial=0.0,
                    unitstyle=4, appearance=1, activedialcolor=color,
                    annotation_name=f"{label.title()} band trim")

device.add_panel("monitor_panel", [356, 132, 184, 74],
                 bgcolor=SURFACE_ALT, rounded=6)
device.add_comment("lbl_monitor", [366, 138, 90, 10], "LISTEN",
                   fontsize=8.0, textcolor=[0.75, 0.82, 0.90, 1.0])
device.add_tab("monitor_tab", "Monitor", [366, 154, 162, 22],
               options=["SUM", "LOW", "MID", "HIGH"],
               bgcolor=[0.14, 0.16, 0.19, 1.0],
               bgoncolor=[0.30, 0.56, 0.86, 1.0],
               textcolor=[0.72, 0.78, 0.84, 1.0],
               textoncolor=[1.0, 1.0, 1.0, 1.0],
               spacing_x=2.0, rounded=4.0)
device.add_comment("monitor_hint", [366, 182, 160, 10],
                   "SUM stays flat. LOW/MID/HIGH solo the chosen band.",
                   fontsize=7.3, textcolor=TEXT_DIM)

# ---------------------------------------------------------------------------
# Control and spectral split core
# ---------------------------------------------------------------------------
device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[20, 240, 55, 20])
device.add_newobj("dspstate", "dspstate~", numinlets=1, numoutlets=4,
                  outlettype=["int", "float", "int", "int"],
                  patching_rect=[20, 268, 60, 20])
device.add_newobj("display_low_init", "loadmess 160.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 296, 80, 20])
device.add_newobj("display_high_init", "loadmess 3200.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 322, 88, 20])
device.add_newobj("display_mode_init", "loadmess 0", numinlets=1, numoutlets=1,
                  outlettype=["int"], patching_rect=[20, 348, 72, 20])

device.add_newobj("low_bin_pak", "pak f f", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[110, 240, 60, 20])
device.add_newobj("high_bin_pak", "pak f f", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[180, 240, 60, 20])
device.add_newobj("low_bin_expr", f"expr ($f1 * {FFT_SIZE}.) / $f2",
                  numinlets=2, numoutlets=1, outlettype=[""],
                  patching_rect=[110, 270, 110, 20])
device.add_newobj("high_bin_expr", f"expr ($f1 * {FFT_SIZE}.) / $f2",
                  numinlets=2, numoutlets=1, outlettype=[""],
                  patching_rect=[180, 300, 110, 20])
device.add_newobj("send_low_bin", "s lps_low_bin", numinlets=1, numoutlets=0,
                  patching_rect=[110, 300, 70, 20])
device.add_newobj("send_high_bin", "s lps_high_bin", numinlets=1, numoutlets=0,
                  patching_rect=[180, 330, 75, 20])

device.add_newobj("fft_split", f"pfft~ {PFFT_NAME} {FFT_SIZE} {FFT_OVERLAP}",
                  numinlets=2, numoutlets=6,
                  outlettype=["signal", "signal", "signal",
                              "signal", "signal", "signal"],
                  patching_rect=[20, 360, 180, 20])

for index, (band_id, _, _, _) in enumerate(band_meta):
    y = 410 + index * 95
    device.add_newobj(f"{band_id}_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[260, y, 45, 20])
    device.add_newobj(f"{band_id}_pk", "pack f 20", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[312, y, 60, 20])
    device.add_newobj(f"{band_id}_ln", "line~", numinlets=2, numoutlets=2,
                      outlettype=["signal", "bang"], patching_rect=[378, y, 40, 20])
    device.add_newobj(f"{band_id}_gain_l", "*~", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[430, y, 30, 20])
    device.add_newobj(f"{band_id}_gain_r", "*~", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[466, y, 30, 20])

device.add_newobj("sum_l_a", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[430, 720, 30, 20])
device.add_newobj("sum_r_a", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[466, 720, 30, 20])
device.add_newobj("sum_l_b", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[430, 750, 30, 20])
device.add_newobj("sum_r_b", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[466, 750, 30, 20])

device.add_newobj("monitor_offset", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[560, 410, 40, 20])
device.add_newobj("monitor_l", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[560, 445, 80, 20])
device.add_newobj("monitor_r", "selector~ 4 1", numinlets=5, numoutlets=1,
                  outlettype=["signal"], patching_rect=[650, 445, 80, 20])

# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------
device.add_line("loadbang", 0, "dspstate", 0)
device.add_line("display_low_init", 0, "xover_display", 0)
device.add_line("display_high_init", 0, "xover_display", 1)
device.add_line("display_mode_init", 0, "xover_display", 2)

device.add_line("low_xover", 0, "low_bin_pak", 0)
device.add_line("high_xover", 0, "high_bin_pak", 0)
device.add_line("low_xover", 0, "xover_display", 0)
device.add_line("high_xover", 0, "xover_display", 1)
device.add_line("dspstate", 1, "low_bin_pak", 1)
device.add_line("dspstate", 1, "high_bin_pak", 1)
device.add_line("low_bin_pak", 0, "low_bin_expr", 0)
device.add_line("high_bin_pak", 0, "high_bin_expr", 0)
device.add_line("low_bin_expr", 0, "send_low_bin", 0)
device.add_line("high_bin_expr", 0, "send_high_bin", 0)

device.add_line("obj-plugin", 0, "fft_split", 0)
device.add_line("obj-plugin", 1, "fft_split", 1)

fft_outputs = {
    "low_l": 0,
    "mid_l": 1,
    "high_l": 2,
    "low_r": 3,
    "mid_r": 4,
    "high_r": 5,
}

for band_id, _, _, _ in band_meta:
    device.add_line(f"trim_{band_id}", 0, f"{band_id}_dbtoa", 0)
    device.add_line(f"{band_id}_dbtoa", 0, f"{band_id}_pk", 0)
    device.add_line(f"{band_id}_pk", 0, f"{band_id}_ln", 0)
    device.add_line(f"{band_id}_ln", 0, f"{band_id}_gain_l", 1)
    device.add_line(f"{band_id}_ln", 0, f"{band_id}_gain_r", 1)

    device.add_line("fft_split", fft_outputs[f"{band_id}_l"], f"{band_id}_gain_l", 0)
    device.add_line("fft_split", fft_outputs[f"{band_id}_r"], f"{band_id}_gain_r", 0)

device.add_line("low_gain_l", 0, "sum_l_a", 0)
device.add_line("mid_gain_l", 0, "sum_l_a", 1)
device.add_line("low_gain_r", 0, "sum_r_a", 0)
device.add_line("mid_gain_r", 0, "sum_r_a", 1)
device.add_line("sum_l_a", 0, "sum_l_b", 0)
device.add_line("high_gain_l", 0, "sum_l_b", 1)
device.add_line("sum_r_a", 0, "sum_r_b", 0)
device.add_line("high_gain_r", 0, "sum_r_b", 1)

device.add_line("monitor_tab", 0, "monitor_offset", 0)
device.add_line("monitor_tab", 0, "xover_display", 2)
device.add_line("monitor_offset", 0, "monitor_l", 0)
device.add_line("monitor_offset", 0, "monitor_r", 0)

device.add_line("sum_l_b", 0, "monitor_l", 1)
device.add_line("low_gain_l", 0, "monitor_l", 2)
device.add_line("mid_gain_l", 0, "monitor_l", 3)
device.add_line("high_gain_l", 0, "monitor_l", 4)

device.add_line("sum_r_b", 0, "monitor_r", 1)
device.add_line("low_gain_r", 0, "monitor_r", 2)
device.add_line("mid_gain_r", 0, "monitor_r", 3)
device.add_line("high_gain_r", 0, "monitor_r", 4)

device.add_line("monitor_l", 0, "obj-plugout", 0)
device.add_line("monitor_r", 0, "obj-plugout", 1)
device.add_line("monitor_l", 0, "meter_l", 0)
device.add_line("monitor_r", 0, "meter_r", 0)


output = device_output_path("Linear Phase Crossover")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
