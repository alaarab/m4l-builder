"""Parametric EQ — Pro-Q style 8-band parametric equalizer.

Hero device showcasing the eq_curve jsui engine with interactive draggable
nodes. 8 fully parametric bands using filtercoeff~ + biquad~ for true
parametric EQ quality. Supports Peak/LShelf/HShelf/LP/HP/Notch/BP/AP types.

Layout (780×408):
  Top bar: focus band selector, analyzer toggle, display range selector
  Hero graph: interactive EQ curve with integrated post-output analyzer,
              draggable band nodes, mouse wheel Q, shift+drag fine-tune,
              cmd+drag lock gain/Q axis, hover HUD
  Bottom: 8 band cards (Freq/Gain/Q/type/on) + output card + L/R meters

DSP signal flow (filtercoeff~ + biquad~ per band):
  Each band: filtercoeff~ type -> biquad~ in series
  filtercoeff~ generates 5 biquad coefficients (a0,a1,a2,b1,b2) at signal rate
  biquad~ applies the filter: y[n] = a0*x[n] + a1*x[n-1] + a2*x[n-2] - b1*y[n-1] - b2*y[n-2]

  Signal chain:
    plugin~ L -> biquad~_b0_l -> biquad~_b1_l -> ... -> biquad~_b7_l -> out_gain_l -> plugout~ L
    plugin~ R -> biquad~_b0_r -> biquad~_b1_r -> ... -> biquad~_b7_r -> out_gain_r -> plugout~ R

  Each filtercoeff~ receives:
    inlet 0: frequency (Hz)
    inlet 1: gain (LINEAR via dbtoa, NOT dB)
    inlet 2: Q (resonance/bandwidth)
  And outputs 5 signal-rate coefficients to biquad~ inlets 1-5.

  When band is disabled: filtercoeff~ type set to "off" -> passthrough coefficients

Parameter smoothing (click-free):
  freq/gain(linear)/Q all routed through pack+line~ before reaching filtercoeff~.
  pack f {default} 20 -> line~ ramps each coefficient change over 20 ms.
  This is the most important anti-click measure — biquad~ coefficients cause
  loud clicks when changed instantaneously.

CRITICAL RULES:
  - No sig~ — floats sent directly to signal inlets
  - filtercoeff~ gain is LINEAR not dB — always use dbtoa
  - Send "resamp 1" to each filtercoeff~ for smooth sweeps
  - *~ with no arg defaults to 0 — always use *~ 1. or *~ 0.
  - Panels: background:1
  - presentation_rect values must be whole integers
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m4l_builder import AudioEffect, Theme
from m4l_builder.engines.eq_band_column import eq_band_column_js
from m4l_builder.engines.eq_curve import eq_curve_js, EQ_CURVE_INLETS, EQ_CURVE_OUTLETS


def mix(color_a, color_b, amount):
    """Blend two RGBA colors."""
    keep = 1.0 - amount
    return [round(color_a[i] * keep + color_b[i] * amount, 4) for i in range(4)]


def alpha(color, value):
    """Return a copy of color with a new alpha."""
    return [color[0], color[1], color[2], value]


def js_color(color):
    """Format an RGBA list for jsui engine kwargs."""
    return ", ".join(str(round(component, 4)) for component in color)


UI_THEME = Theme.custom(
    bg=[0.24, 0.24, 0.25, 1.0],
    surface=[0.29, 0.29, 0.30, 1.0],
    section=[0.34, 0.34, 0.35, 1.0],
    text=[0.93, 0.93, 0.94, 1.0],
    text_dim=[0.72, 0.72, 0.74, 1.0],
    accent=[0.96, 0.66, 0.26, 1.0],
    meter_cold=[0.35, 0.70, 0.38, 1.0],
    meter_warm=[0.82, 0.68, 0.24, 1.0],
    meter_hot=[0.90, 0.54, 0.18, 1.0],
    meter_over=[0.86, 0.28, 0.22, 1.0],
    fontname="Arial",
    fontname_bold="Arial Bold",
)


# ---------------------------------------------------------------------------
# Device setup — flagship layout with a larger hero graph and control bar
# ---------------------------------------------------------------------------
device = AudioEffect("Parametric EQ", width=760, height=188, theme=UI_THEME)
theme = device.theme

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BG = list(theme.bg)
SURFACE = list(theme.surface)
SURFACE_ALT = list(theme.section)
SECTION = list(theme.section)
TEXT = list(theme.text)
TEXT_DIM = list(theme.text_dim)
ACCENT = list(theme.accent)
ACCENT_SOFT = mix(theme.surface, theme.accent, 0.22)
CONTROL_BG = [0.22, 0.22, 0.23, 1.0]
CONTROL_BORDER = [0.41, 0.41, 0.43, 1.0]
GRAPH_FRAME_BG = list(SURFACE)
GRAPH_BG = [0.07, 0.10, 0.15, 1.0]
GRAPH_BORDER = [0.27, 0.27, 0.29, 1.0]
GRAPH_COMPOSITE = mix(TEXT, ACCENT, 0.16)
GRAPH_FILL = alpha(ACCENT, 0.10)
GRAPH_ANALYZER = mix(ACCENT, TEXT, 0.42)
GRAPH_GRID = alpha([0.82, 0.82, 0.84, 1.0], 0.18)
GRAPH_TEXT = [0.74, 0.74, 0.76, 1.0]
GRAPH_ZERO = [0.74, 0.74, 0.76, 0.56]
RAIL_BORDER = list(CONTROL_BORDER)
RAIL_KNOB_FILL = mix(SURFACE, BG, 0.10)
RAIL_KNOB_TRACK = mix(SECTION, BG, 0.20)
RAIL_DISABLED = mix(SECTION, BG, 0.42)
RAIL_MOTION = list(ACCENT)
DYNAMIC_COLOR = list(ACCENT)
BYPASS_COLOR = [0.74, 0.32, 0.32, 1.0]
TEXT_ON_DARK = [0.14, 0.14, 0.15, 1.0]
HIDDEN_X = 900
CORE_X = 14
CORE_Y = 14
CORE_W = 70
CORE_H = 156
GRAPH_X = 92
GRAPH_Y = 14
GRAPH_W = 356
GRAPH_H = 156
DETAIL_X = HIDDEN_X
DETAIL_Y = 148
DETAIL_WIDTH = 1
DETAIL_H = 1
EDITOR_X = 456
EDITOR_Y = 14
EDITOR_W = 152
EDITOR_H = 156
GLOBAL_X = 616
GLOBAL_Y = 14
GLOBAL_W = 120
GLOBAL_H = 156
CARD_Y = 900
CARD_W = 64
CARD_H = 42
CARD_GAP = 4

# Per-band accent colors matching jsui BAND_COLORS
BAND_COLORS = [
    [0.90, 0.35, 0.35, 1.0],  # 1: red
    [0.90, 0.65, 0.25, 1.0],  # 2: orange
    [0.85, 0.85, 0.30, 1.0],  # 3: yellow
    [0.35, 0.80, 0.45, 1.0],  # 4: green
    [0.35, 0.75, 0.85, 1.0],  # 5: cyan
    [0.40, 0.55, 0.90, 1.0],  # 6: blue
    [0.65, 0.45, 0.85, 1.0],  # 7: purple
    [0.85, 0.45, 0.65, 1.0],  # 8: pink
]

NUM_BANDS = 8

# Default hidden band slots: freq, type_index
# With 0-band startup the graph owns creation, so keep the underlying slots
# neutral. New bands can become shelves/cuts from the node menu after creation.
# Types: 0=Peak, 1=LShelf, 2=HShelf, 3=LP, 4=HP, 5=Notch, 6=BP, 7=AP
BAND_DEFAULTS = [
    (30.0,    0),
    (80.0,    0),
    (250.0,   0),
    (800.0,   0),
    (2500.0,  0),
    (6000.0,  0),
    (10000.0, 0),
    (18000.0, 0),
]
BAND_DEFAULT_ENABLED = [1, 1, 1, 1, 0, 0, 0, 0]

MOTION_RATE_DEFAULTS = [0.18, 0.27, 0.39, 0.56, 0.80, 1.12, 1.48, 1.92]
MOTION_DEPTH_DEFAULTS = [18.0, 24.0, 30.0, 36.0, 44.0, 52.0, 60.0, 68.0]
MOTION_DIRECTION_DEFAULTS = [0.0, 35.0, 70.0, 120.0, 165.0, 215.0, 285.0, 330.0]

# filtercoeff~ type names for each menu index
FILTERCOEFF_TYPES = ["peaknotch", "lowshelf", "highshelf", "lowpass", "highpass",
                     "bandstop", "bandpass", "allpass"]

TYPE_OPTIONS = ["Peak", "LShelf", "HShelf", "LP", "HP", "Notch", "BP", "AP"]
EQ_DISPLAY_FILENAME = "peq_display_v7.js"
SELECTED_EDITOR_FILENAME = "peq_selected_band_editor_v3.js"
SELECTED_CORE_FILENAME = "peq_selected_core_rail_v1.js"

# ---------------------------------------------------------------------------
# UI — Background, hero frame, and top bar
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 760, 188], bgcolor=BG)
device.add_panel("hero_frame", [10, 8, 740, 172],
                 bgcolor=SURFACE, border=1,
                 bordercolor=CONTROL_BORDER, rounded=8)
device.add_panel("core_frame", [CORE_X, CORE_Y, CORE_W, CORE_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=8)
device.add_panel("graph_frame", [GRAPH_X - 2, GRAPH_Y - 2, GRAPH_W + 4, GRAPH_H + 4],
                 bgcolor=GRAPH_FRAME_BG, border=1,
                 bordercolor=GRAPH_BORDER, rounded=8)
device.add_panel("graph_plot_bg", [GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H],
                 bgcolor=GRAPH_BG, border=1,
                 bordercolor=GRAPH_BORDER, rounded=6)
device.add_panel("detail_frame", [DETAIL_X, DETAIL_Y, DETAIL_WIDTH, DETAIL_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=8)
device.add_panel("editor_frame", [EDITOR_X, EDITOR_Y, EDITOR_W, EDITOR_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=8)
device.add_panel("global_frame", [GLOBAL_X, GLOBAL_Y, GLOBAL_W, GLOBAL_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=8)
device.add_panel("bands_bg", [14, CARD_Y - 2, 544, CARD_H + 4],
                 bgcolor=SURFACE, border=1,
                 bordercolor=RAIL_BORDER, rounded=8)
device.add_comment("core_title", [CORE_X + 8, CORE_Y + 8, CORE_W - 16, 10], "SEL",
                   textcolor=TEXT_DIM, fontsize=6.6, fontname=theme.fontname_bold, justification=1)
device.add_comment("detail_title", [DETAIL_X + 10, DETAIL_Y + 8, 94, 12], "SELECTED BAND",
                   textcolor=TEXT_DIM, fontsize=7.6, fontname=theme.fontname_bold)
device.add_tab("focus_tab", "Focus Band", [900, 148, 1, 1],
               options=[f"B{i + 1}" for i in range(NUM_BANDS)],
               bgcolor=CONTROL_BG, bgoncolor=ACCENT,
               textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
               rounded=4, spacing_x=1.0, fontsize=8.0)
device.add_comment("mod_title", [HIDDEN_X, 148, 1, 1], "BAND MOD",
                   textcolor=TEXT_DIM, fontsize=7.6, fontname=theme.fontname_bold)
device.add_comment("global_title", [GLOBAL_X + 10, GLOBAL_Y + 8, 54, 12], "GLOBAL",
                   textcolor=TEXT_DIM, fontsize=7.6, fontname=theme.fontname_bold)
device.add_comment("global_analyzer_title", [GLOBAL_X + 8, GLOBAL_Y + 24, 40, 8], "ANALYZER",
                   textcolor=TEXT_DIM, fontsize=6.2)
device.add_comment("global_range_title", [GLOBAL_X + 66, GLOBAL_Y + 24, 28, 8], "RANGE",
                   textcolor=TEXT_DIM, fontsize=6.2)
device.add_tab("analyzer_mode_tab", "Analyzer Mode", [GLOBAL_X + 8, GLOBAL_Y + 32, 56, 18],
               options=["OFF", "PRE", "POST"],
               bgcolor=CONTROL_BG, bgoncolor=ACCENT,
               textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
               rounded=4, spacing_x=1.0, fontsize=8.0)
device.add_tab("range_tab", "Display Range", [GLOBAL_X + 64, GLOBAL_Y + 32, 48, 18],
               options=["15", "18", "24", "30"],
               bgcolor=CONTROL_BG, bgoncolor=ACCENT,
               textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
               rounded=4, spacing_x=1.0, fontsize=8.0)

# ---------------------------------------------------------------------------
# UI — EQ curve interactive display
# ---------------------------------------------------------------------------
device.add_box({
    "box": {
        "id": "peq_spectroscope",
        "maxclass": "spectroscope~",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "background": 0,
        "ignoreclick": 1,
        "logfreq": 1,
        "interval": 16,
        "scroll": 0,
        "sono": 0,
        "logamp": 1,
        "domain": [10.0, 22000.0],
        "bgcolor": [GRAPH_BG[0], GRAPH_BG[1], GRAPH_BG[2], 0.0],
        "fgcolor": [GRAPH_ANALYZER[0], GRAPH_ANALYZER[1], GRAPH_ANALYZER[2], 0.58],
        "markercolor": [TEXT_DIM[0], TEXT_DIM[1], TEXT_DIM[2], 0.0],
        "patching_rect": [10, 30, 668, 158],
        "presentation": 1,
        "presentation_rect": [GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H],
    }
})

device.add_v8ui(
    "eq_display",
    [GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H],
    js_code=eq_curve_js(
        bg_color=js_color(alpha(GRAPH_BG, 0.0)),
        composite_color=js_color(GRAPH_COMPOSITE),
        fill_color=js_color(GRAPH_FILL),
        analyzer_fill_color=js_color(alpha(GRAPH_ANALYZER, 0.0)),
        analyzer_line_color=js_color(alpha(GRAPH_ANALYZER, 0.0)),
        analyzer_peak_color=js_color(alpha(TEXT, 0.0)),
        grid_color=js_color(GRAPH_GRID),
        text_color=js_color(GRAPH_TEXT),
        zero_line_color=js_color(GRAPH_ZERO),
    ),
    numinlets=EQ_CURVE_INLETS,
    numoutlets=EQ_CURVE_OUTLETS,
    outlettype=[""] * EQ_CURVE_OUTLETS,
    js_filename=EQ_DISPLAY_FILENAME,
    patching_rect=[10, 30, 668, 158],
    bgcolor=alpha(BG, 0.0),
    border=0,
    background=0,
)

device.add_jsui(
    "selected_core_rail",
    [CORE_X + 4, CORE_Y + 18, CORE_W - 8, CORE_H - 24],
    js_code=eq_band_column_js(
        title="",
        subtitle="",
        type_names=TYPE_OPTIONS,
        gain_enabled_types=[0, 1, 2],
        slope_enabled_types=[],
        show_slope=False,
        show_solo=False,
        show_motion=False,
        show_dynamic=False,
        show_type_controls=False,
        show_toggle_stack=False,
        show_header=False,
        show_frame=False,
        force_regular_layout=True,
        bg_color=js_color(alpha(BG, 0.0)),
        panel_color=js_color(SURFACE_ALT),
        border_color=js_color(RAIL_BORDER),
        text_color=js_color(TEXT),
        text_dim_color=js_color(TEXT_DIM),
        accent_color=js_color(ACCENT),
        motion_accent_color=js_color(RAIL_MOTION),
        knob_fill_color=js_color(RAIL_KNOB_FILL),
        knob_track_color=js_color(RAIL_KNOB_TRACK),
        disabled_color=js_color(RAIL_DISABLED),
        enable_color=js_color(ACCENT),
        solo_color=js_color(DYNAMIC_COLOR),
        font_name=theme.fontname,
        font_bold_name=theme.fontname_bold,
    ),
    numinlets=1,
    numoutlets=1,
    outlettype=[""],
    js_filename=SELECTED_CORE_FILENAME,
    bgcolor=alpha(BG, 0.0),
    border=0,
    background=0,
    patching_rect=[10, 260, 92, 154],
)

device.add_jsui(
    "selected_band_column",
    [EDITOR_X + 8, EDITOR_Y + 8, EDITOR_W - 16, EDITOR_H - 16],
    js_code=eq_band_column_js(
        title="SELECTED BAND",
        subtitle="Click a node to edit it",
        type_names=TYPE_OPTIONS,
        gain_enabled_types=[0, 1, 2],
        slope_enabled_types=[],
        show_slope=False,
        show_solo=False,
        show_motion=True,
        show_dynamic=True,
        show_type_controls=True,
        show_toggle_stack=True,
        show_header=True,
        show_frame=False,
        force_regular_layout=False,
        bg_color=js_color(alpha(BG, 0.0)),
        panel_color=js_color(SURFACE),
        border_color=js_color(RAIL_BORDER),
        text_color=js_color(TEXT),
        text_dim_color=js_color(TEXT_DIM),
        accent_color=js_color(ACCENT),
        motion_accent_color=js_color(RAIL_MOTION),
        knob_fill_color=js_color(RAIL_KNOB_FILL),
        knob_track_color=js_color(RAIL_KNOB_TRACK),
        disabled_color=js_color(RAIL_DISABLED),
        enable_color=js_color(ACCENT),
        solo_color=js_color(DYNAMIC_COLOR),
        font_name=theme.fontname,
        font_bold_name=theme.fontname_bold,
    ),
    numinlets=1,
    numoutlets=1,
    outlettype=[""],
    js_filename=SELECTED_EDITOR_FILENAME,
    bgcolor=alpha(BG, 0.0),
    border=0,
    background=0,
    patching_rect=[10, 260, 92, 154],
)

device.add_number_box("out_gain_compact", "Out Compact", [900, 148, 54, 16],
                      min_val=-24.0, max_val=24.0, initial=0.0,
                      unitstyle=4, patching_rect=[1700, 0, 60, 16], fontsize=7.4,
                      parameter_enable=0)
device.add_live_text("bypass_compact", "Bypass Compact", [900, 148, 50, 16],
                     text_on="BYP", text_off="ACT",
                     bgcolor=CONTROL_BG, bgoncolor=BYPASS_COLOR,
                     textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                     rounded=4, fontsize=7.2, shortname="BypassVis",
                     parameter_enable=0)

device.add_comment("selected_band_label", [DETAIL_X + 10, DETAIL_Y + 22, DETAIL_WIDTH - 20, 12], "NO BAND",
                   textcolor=TEXT, fontsize=8.8, fontname=theme.fontname_bold)
device.add_comment("selected_band_status", [DETAIL_X + 10, DETAIL_Y + 36, DETAIL_WIDTH - 20, 10], "Click a node",
                   textcolor=TEXT_DIM, fontsize=7.0)
device.add_comment("selected_type_caption", [DETAIL_X + 10, DETAIL_Y + 50, 28, 8], "TYPE",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_menu("selected_type", "Selected Type", [DETAIL_X + 10, DETAIL_Y + 58, DETAIL_WIDTH - 20, 18],
                options=TYPE_OPTIONS, fontsize=8.2, parameter_enable=0,
                bgcolor=CONTROL_BG, bgoncolor=ACCENT,
                textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK)
device.add_comment("selected_freq_caption", [DETAIL_X + 10, DETAIL_Y + 82, 28, 8], "FREQ",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_comment("selected_gain_caption", [DETAIL_X + 84, DETAIL_Y + 82, 28, 8], "GAIN",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_number_box("selected_freq", "Selected Freq", [DETAIL_X + 10, DETAIL_Y + 90, 66, 18],
                      min_val=10.0, max_val=22000.0, initial=BAND_DEFAULTS[0][0],
                      unitstyle=3, fontsize=8.2, parameter_enable=0)
device.add_number_box("selected_gain", "Selected Gain", [DETAIL_X + 84, DETAIL_Y + 90, 66, 18],
                      min_val=-30.0, max_val=30.0, initial=0.0,
                      unitstyle=4, fontsize=8.2, parameter_enable=0)
device.add_comment("selected_q_caption", [DETAIL_X + 10, DETAIL_Y + 114, 18, 8], "Q",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_comment("selected_dynamic_amt_caption", [DETAIL_X + 84, DETAIL_Y + 114, 50, 8], "DYN AMT",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_number_box("selected_q", "Selected Q", [DETAIL_X + 10, DETAIL_Y + 122, 66, 18],
                      min_val=0.1, max_val=30.0, initial=1.0,
                      unitstyle=1, fontsize=8.2, parameter_enable=0)
device.add_number_box("selected_dynamic_amt", "Selected Dynamic Amt", [DETAIL_X + 84, DETAIL_Y + 122, 66, 18],
                      min_val=-18.0, max_val=18.0, initial=0.0,
                      unitstyle=4, fontsize=8.0, parameter_enable=0)

device.add_live_text("selected_enable", "Selected Enable", [DETAIL_X + 10, DETAIL_Y + 142, 42, 14],
                     text_on="ON", text_off="OFF",
                     bgcolor=CONTROL_BG, bgoncolor=ACCENT,
                     textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                     rounded=4, fontsize=7.0, parameter_enable=0)
device.add_live_text("selected_motion", "Selected Motion", [DETAIL_X + 58, DETAIL_Y + 142, 42, 14],
                     text_on="MOVE", text_off="MOVE",
                     bgcolor=CONTROL_BG, bgoncolor=RAIL_MOTION,
                     textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                     rounded=4, fontsize=7.0, parameter_enable=0)
device.add_live_text("selected_dynamic", "Selected Dynamic", [DETAIL_X + 106, DETAIL_Y + 142, 44, 14],
                     text_on="DYN", text_off="DYN",
                     bgcolor=CONTROL_BG, bgoncolor=DYNAMIC_COLOR,
                     textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                     rounded=4, fontsize=7.0, parameter_enable=0)
device.add_comment("selected_motion_rate_caption", [HIDDEN_X, 148, 1, 1], "RATE",
                   textcolor=TEXT_DIM, fontsize=6.2)
device.add_number_box("selected_motion_rate", "Selected Motion Rate", [HIDDEN_X, 148, 1, 1],
                      min_val=0.05, max_val=12.0, initial=MOTION_RATE_DEFAULTS[0],
                      fontsize=7.6, parameter_enable=0)
device.add_comment("selected_motion_depth_caption", [HIDDEN_X, 148, 1, 1], "DEPTH",
                   textcolor=TEXT_DIM, fontsize=6.2)
device.add_number_box("selected_motion_depth", "Selected Motion Depth", [HIDDEN_X, 148, 1, 1],
                      min_val=0.0, max_val=100.0, initial=MOTION_DEPTH_DEFAULTS[0],
                      unitstyle=5, fontsize=7.6, parameter_enable=0)
device.add_comment("selected_motion_direction_caption", [HIDDEN_X, 148, 1, 1], "DIR",
                   textcolor=TEXT_DIM, fontsize=6.2)
device.add_number_box("selected_motion_direction", "Selected Motion Direction", [HIDDEN_X, 148, 1, 1],
                      min_val=0.0, max_val=359.0, initial=MOTION_DIRECTION_DEFAULTS[0],
                      fontsize=7.6, parameter_enable=0)

# ---------------------------------------------------------------------------
# UI — 8 band cards + output card
# ---------------------------------------------------------------------------
BAND_X = [16 + i * (CARD_W + CARD_GAP) for i in range(NUM_BANDS)]
OUT_X = 690

for i, bx in enumerate(BAND_X):
    bc = BAND_COLORS[i]
    lbl = str(i + 1)
    default_freq, default_type = BAND_DEFAULTS[i]
    default_enabled = BAND_DEFAULT_ENABLED[i]
    default_motion_rate = MOTION_RATE_DEFAULTS[i]
    default_motion_depth = MOTION_DEPTH_DEFAULTS[i]
    default_motion_direction = MOTION_DIRECTION_DEFAULTS[i]

    device.add_panel(f"card_b{i}", [bx, CARD_Y, CARD_W, CARD_H],
                     bgcolor=SURFACE_ALT, border=1,
                     bordercolor=[bc[0], bc[1], bc[2], 0.85], rounded=6)
    device.add_comment(f"lbl_b{i}", [bx + 4, CARD_Y + 3, 16, 8], f"B{lbl}",
                       textcolor=bc, fontsize=6.8,
                       fontname=theme.fontname_bold)
    device.add_comment(f"lbl_fg_b{i}", [bx + 24, CARD_Y + 4, 18, 8], "FGQ",
                       textcolor=TEXT_DIM, fontsize=5.5, justification=1)

    device.add_menu(f"type_b{i}", f"Type B{lbl}",
                    [bx + 4, CARD_Y + 14, CARD_W - 8, 12],
                    options=TYPE_OPTIONS,
                    shortname=f"Typ{lbl}",
                    patching_rect=[700 + i * 10, 200, 70, 14],
                    fontsize=6.0)

    device.add_dial(f"freq_b{i}", f"Freq B{lbl}",
                    [bx + 4, CARD_Y + 26, 16, 16],
                    min_val=10.0, max_val=22000.0, initial=default_freq,
                    unitstyle=3, appearance=1, parameter_exponent=3.0,
                    activedialcolor=bc, showname=0, shownumber=0,
                    annotation_name=f"Band {lbl} Frequency")

    device.add_dial(f"gain_b{i}", f"Gain B{lbl}",
                    [bx + 24, CARD_Y + 26, 16, 16],
                    min_val=-30.0, max_val=30.0, initial=0.0,
                    unitstyle=4, appearance=1,
                    activedialcolor=bc, showname=0, shownumber=0,
                    annotation_name=f"Band {lbl} Gain dB")

    device.add_comment(f"lbl_q_b{i}", [bx + 44, CARD_Y + 27, 14, 7], "Q",
                       textcolor=TEXT_DIM, fontsize=5.4, justification=1)
    device.add_dial(f"q_b{i}", f"Q B{lbl}",
                    [bx + 44, CARD_Y + 34, 14, 8],
                    min_val=0.1, max_val=30.0, initial=1.0,
                    unitstyle=1, appearance=1,
                    activedialcolor=bc, showname=0, shownumber=0,
                    annotation_name=f"Band {lbl} Q")

    device.add_live_text(f"on_b{i}", f"On B{lbl}",
                         [bx + 24, CARD_Y + 3, 36, 10],
                         text_on="ON", text_off="OFF",
                         bgcolor=ACCENT_SOFT, bgoncolor=bc,
                         textcolor=TEXT_DIM, textoncolor=[0.03, 0.04, 0.05, 1.0],
                         rounded=4, fontsize=5.8,
                         shortname=f"On{lbl}",
                         saved_attribute_attributes={
                             "valueof": {
                                 "parameter_initial_enable": 1,
                                 "parameter_initial": [default_enabled],
                             }
                         })
    device.add_live_text(f"motion_b{i}", f"Motion B{lbl}",
                         [900, 148, 34, 12],
                         text_on="MOT", text_off="MOT",
                         bgcolor=ACCENT_SOFT, bgoncolor=RAIL_MOTION,
                         textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                         rounded=4, fontsize=6.2, shortname=f"Mot{lbl}",
                         patching_rect=[1720, 40 + i * 18, 34, 12])
    device.add_live_text(f"dynamic_b{i}", f"Dynamic B{lbl}",
                         [900, 148, 34, 12],
                         text_on="DYN", text_off="DYN",
                         bgcolor=ACCENT_SOFT, bgoncolor=DYNAMIC_COLOR,
                         textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                         rounded=4, fontsize=6.2, shortname=f"Dyn{lbl}",
                         patching_rect=[1760, 40 + i * 18, 34, 12])
    device.add_number_box(f"dynamic_amt_b{i}", f"Dynamic Amt B{lbl}",
                          [900, 148, 38, 12],
                          min_val=-18.0, max_val=18.0, initial=0.0,
                          unitstyle=4, fontsize=6.2,
                          patching_rect=[1800, 40 + i * 18, 40, 12])
    device.add_number_box(f"motion_rate_b{i}", f"Motion Rate B{lbl}",
                          [900, 148, 42, 12],
                          min_val=0.05, max_val=12.0, initial=default_motion_rate,
                          fontsize=6.2,
                          patching_rect=[1846, 40 + i * 18, 44, 12])
    device.add_number_box(f"motion_depth_b{i}", f"Motion Depth B{lbl}",
                          [900, 148, 42, 12],
                          min_val=0.0, max_val=100.0, initial=default_motion_depth,
                          unitstyle=5, fontsize=6.2,
                          patching_rect=[1896, 40 + i * 18, 44, 12])
    device.add_number_box(f"motion_direction_b{i}", f"Motion Direction B{lbl}",
                          [900, 148, 24, 12],
                          min_val=0.0, max_val=359.0, initial=default_motion_direction,
                          fontsize=6.2,
                          patching_rect=[1946, 40 + i * 18, 24, 12])

device.add_panel("output_card", [900, 900, 1, 1],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=[ACCENT[0], ACCENT[1], ACCENT[2], 0.85], rounded=6)
device.add_comment("lbl_out", [GLOBAL_X + 10, GLOBAL_Y + 60, 40, 8], "OUTPUT",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_number_box("out_gain", "Out Gain", [GLOBAL_X + 8, GLOBAL_Y + 68, 56, 18],
                      min_val=-24.0, max_val=24.0, initial=0.0,
                      unitstyle=4, fontsize=8.0)
device.add_live_text("bypass_toggle", "Bypass", [GLOBAL_X + 66, GLOBAL_Y + 68, 46, 18],
                     text_on="BYP", text_off="ACT",
                     bgcolor=CONTROL_BG, bgoncolor=BYPASS_COLOR,
                     textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                     rounded=4, fontsize=7.4, shortname="Bypass")
device.add_comment("lbl_meters", [GLOBAL_X + 90, GLOBAL_Y + 114, 22, 8], "LR",
                   textcolor=TEXT_DIM, fontsize=6.0, justification=1)
device.add_meter("meter_l", [GLOBAL_X + 94, GLOBAL_Y + 82, 8, 30],
                 patching_rect=[1600, 0, 8, 80])
device.add_meter("meter_r", [GLOBAL_X + 106, GLOBAL_Y + 82, 8, 30],
                 patching_rect=[1620, 0, 8, 80])

# ---------------------------------------------------------------------------
# DSP — Init: loadbang -> "set_num_bands 8" message + resamp 1 messages
# ---------------------------------------------------------------------------
device.add_newobj("lb_init", "loadbang",
                  numinlets=0, numoutlets=1,
                  outlettype=["bang"],
                  patching_rect=[10, 200, 70, 20])
device.add_newobj("dspstate_eq", "dspstate~",
                  numinlets=1, numoutlets=4,
                  outlettype=["int", "float", "int", "int"],
                  patching_rect=[140, 200, 70, 20])

# Message to tell jsui about band count
device.add_box({
    "box": {
        "id": "msg_num_bands",
        "maxclass": "message",
        "text": "set_num_bands 8",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [10, 225, 120, 20],
    }
})

device.add_line("lb_init", 0, "msg_num_bands", 0)
device.add_line("lb_init", 0, "dspstate_eq", 0)
device.add_line("msg_num_bands", 0, "eq_display", 0)
device.add_line("msg_num_bands", 0, "selected_core_rail", 0)
device.add_line("msg_num_bands", 0, "selected_band_column", 0)
device.add_line("dspstate_eq", 1, "eq_display", 1)

# Focus band defaults + syncing between graph and focus tab
device.add_box({
    "box": {
        "id": "msg_focus_default",
        "maxclass": "message",
        "text": "0",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [10, 250, 40, 20],
    }
})
device.add_newobj("focus_init_delay", "del 1",
                  numinlets=2, numoutlets=1,
                  outlettype=["bang"],
                  patching_rect=[56, 250, 44, 20])
device.add_newobj("selected_band_store", "int -1",
                  numinlets=2, numoutlets=1,
                  outlettype=["int"],
                  patching_rect=[104, 250, 48, 20])
device.add_newobj("prepend_focus", "prepend set_selected",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[60, 250, 120, 20])
device.add_newobj("route_graph_events", "route selected_band add_band delete_band",
                  numinlets=1, numoutlets=4,
                  outlettype=["", "", "", ""],
                  patching_rect=[190, 250, 220, 20])

device.add_line("lb_init", 0, "focus_init_delay", 0)
device.add_line("focus_init_delay", 0, "msg_focus_default", 0)
device.add_line("msg_focus_default", 0, "selected_band_store", 0)
device.add_line("selected_band_store", 0, "prepend_focus", 0)
device.add_line("prepend_focus", 0, "eq_display", 0)
device.add_line("prepend_focus", 0, "selected_core_rail", 0)
device.add_line("prepend_focus", 0, "selected_band_column", 0)
device.add_line("focus_tab", 0, "selected_band_store", 0)
device.add_line("eq_display", 0, "route_graph_events", 0)
device.add_line("route_graph_events", 0, "focus_tab", 0)
device.add_line("route_graph_events", 0, "selected_band_store", 0)

# Analyzer mode defaults + routing
device.add_box({
    "box": {
        "id": "msg_analyzer_mode_default",
        "maxclass": "message",
        "text": "2",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [320, 250, 40, 20],
    }
})
device.add_newobj("analyzer_mode_sel", "select 0 1 2",
                  numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", ""],
                  patching_rect=[370, 250, 90, 20])
device.add_newobj("prepend_analyzer", "prepend set_analyzer_enabled",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[470, 250, 160, 20])

device.add_box({
    "box": {
        "id": "msg_analyzer_off",
        "maxclass": "message",
        "text": "0",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [370, 276, 32, 20],
    }
})
device.add_box({
    "box": {
        "id": "msg_analyzer_on",
        "maxclass": "message",
        "text": "1",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [406, 276, 32, 20],
    }
})
device.add_box({
    "box": {
        "id": "msg_analyzer_pre_src",
        "maxclass": "message",
        "text": "1",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [442, 276, 32, 20],
    }
})
device.add_box({
    "box": {
        "id": "msg_analyzer_post_src",
        "maxclass": "message",
        "text": "2",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [478, 276, 32, 20],
    }
})

device.add_line("lb_init", 0, "msg_analyzer_mode_default", 0)
device.add_line("msg_analyzer_mode_default", 0, "analyzer_mode_tab", 0)
device.add_line("msg_analyzer_mode_default", 0, "analyzer_mode_sel", 0)
device.add_line("analyzer_mode_tab", 0, "analyzer_mode_sel", 0)

device.add_line("analyzer_mode_sel", 0, "msg_analyzer_off", 0)
device.add_line("analyzer_mode_sel", 1, "msg_analyzer_on", 0)
device.add_line("analyzer_mode_sel", 1, "msg_analyzer_pre_src", 0)
device.add_line("analyzer_mode_sel", 2, "msg_analyzer_on", 0)
device.add_line("analyzer_mode_sel", 2, "msg_analyzer_post_src", 0)

device.add_line("msg_analyzer_off", 0, "prepend_analyzer", 0)
device.add_line("msg_analyzer_on", 0, "prepend_analyzer", 0)
device.add_line("prepend_analyzer", 0, "eq_display", 0)

# Display range defaults + routing
device.add_box({
    "box": {
        "id": "msg_range_default",
        "maxclass": "message",
        "text": "0",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [540, 250, 40, 20],
    }
})
device.add_newobj("range_sel", "select 0 1 2 3",
                  numinlets=1, numoutlets=5,
                  outlettype=["bang", "bang", "bang", "bang", ""],
                  patching_rect=[590, 250, 100, 20])
device.add_newobj("prepend_range", "prepend set_display_range",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[700, 250, 150, 20])

for idx, value in enumerate([15, 18, 24, 30]):
    device.add_box({
        "box": {
            "id": f"msg_range_{value}",
            "maxclass": "message",
            "text": str(value),
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [590 + idx * 42, 276, 40, 20],
        }
    })
    device.add_line("range_sel", idx, f"msg_range_{value}", 0)
    device.add_line(f"msg_range_{value}", 0, "prepend_range", 0)

device.add_line("lb_init", 0, "msg_range_default", 0)
device.add_line("msg_range_default", 0, "range_tab", 0)
device.add_line("msg_range_default", 0, "range_sel", 0)
device.add_line("range_tab", 0, "range_sel", 0)
device.add_line("prepend_range", 0, "eq_display", 0)

# Graph add/delete events route back into the actual band controls
device.add_newobj("route_add_band_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[860, 140, 200, 20])
device.add_newobj("delete_band_sel", "select 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang", "bang", ""],
                  patching_rect=[860, 165, 200, 20])
device.add_line("route_graph_events", 1, "route_add_band_idx", 0)
device.add_line("route_graph_events", 2, "delete_band_sel", 0)

for i in range(NUM_BANDS):
    default_motion_rate = MOTION_RATE_DEFAULTS[i]
    default_motion_depth = MOTION_DEPTH_DEFAULTS[i]
    default_motion_direction = MOTION_DIRECTION_DEFAULTS[i]
    device.add_newobj(
        f"unpack_add_b{i}",
        "unpack f f f i i",
        numinlets=1, numoutlets=5,
        outlettype=["", "", "", "", ""],
        patching_rect=[1080, 140 + i * 24, 120, 20]
    )
    device.add_newobj(
        f"set_freq_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1080, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_gain_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1156, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_q_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1232, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_type_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1308, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_on_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1384, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_motion_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1460, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_dynamic_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1536, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_dynamic_amt_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1612, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_motion_rate_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1688, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_motion_depth_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1764, 164 + i * 24, 70, 20]
    )
    device.add_newobj(
        f"set_motion_direction_from_graph_b{i}",
        "prepend set",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[1840, 164 + i * 24, 70, 20]
    )
    device.add_box({
        "box": {
            "id": f"msg_off_from_graph_b{i}",
            "maxclass": "message",
            "text": "0",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1220, 140 + i * 24, 30, 20],
        }
    })
    device.add_box({
        "box": {
            "id": f"msg_motion_reset_b{i}",
            "maxclass": "message",
            "text": "0",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1256, 140 + i * 24, 30, 20],
        }
    })
    device.add_box({
        "box": {
            "id": f"msg_dynamic_reset_b{i}",
            "maxclass": "message",
            "text": "0",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1292, 140 + i * 24, 30, 20],
        }
    })
    device.add_box({
        "box": {
            "id": f"msg_dynamic_amt_reset_b{i}",
            "maxclass": "message",
            "text": "0.",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1328, 140 + i * 24, 34, 20],
        }
    })
    device.add_box({
        "box": {
            "id": f"msg_motion_rate_reset_b{i}",
            "maxclass": "message",
            "text": str(default_motion_rate),
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1368, 140 + i * 24, 38, 20],
        }
    })
    device.add_box({
        "box": {
            "id": f"msg_motion_depth_reset_b{i}",
            "maxclass": "message",
            "text": str(default_motion_depth),
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1412, 140 + i * 24, 34, 20],
        }
    })
    device.add_box({
        "box": {
            "id": f"msg_motion_direction_reset_b{i}",
            "maxclass": "message",
            "text": str(default_motion_direction),
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [1452, 140 + i * 24, 30, 20],
        }
    })
    device.add_line("route_add_band_idx", i, f"unpack_add_b{i}", 0)
    device.add_line("route_add_band_idx", i, f"msg_motion_reset_b{i}", 0)
    device.add_line("route_add_band_idx", i, f"msg_dynamic_reset_b{i}", 0)
    device.add_line("route_add_band_idx", i, f"msg_dynamic_amt_reset_b{i}", 0)
    device.add_line("route_add_band_idx", i, f"msg_motion_rate_reset_b{i}", 0)
    device.add_line("route_add_band_idx", i, f"msg_motion_depth_reset_b{i}", 0)
    device.add_line("route_add_band_idx", i, f"msg_motion_direction_reset_b{i}", 0)
    device.add_line(f"unpack_add_b{i}", 0, f"pak_b{i}", 1)
    device.add_line(f"unpack_add_b{i}", 1, f"pak_b{i}", 2)
    device.add_line(f"unpack_add_b{i}", 2, f"pak_b{i}", 3)
    device.add_line(f"unpack_add_b{i}", 3, f"pak_b{i}", 4)
    device.add_line(f"unpack_add_b{i}", 4, f"pak_b{i}", 5)
    device.add_line(f"unpack_add_b{i}", 0, f"set_freq_from_graph_b{i}", 0)
    device.add_line(f"set_freq_from_graph_b{i}", 0, f"freq_b{i}", 0)
    device.add_line(f"unpack_add_b{i}", 1, f"set_gain_from_graph_b{i}", 0)
    device.add_line(f"set_gain_from_graph_b{i}", 0, f"gain_b{i}", 0)
    device.add_line(f"unpack_add_b{i}", 2, f"set_q_from_graph_b{i}", 0)
    device.add_line(f"set_q_from_graph_b{i}", 0, f"q_b{i}", 0)
    device.add_line(f"unpack_add_b{i}", 3, f"set_type_from_graph_b{i}", 0)
    device.add_line(f"set_type_from_graph_b{i}", 0, f"type_b{i}", 0)
    device.add_line(f"unpack_add_b{i}", 4, f"set_on_from_graph_b{i}", 0)
    device.add_line(f"set_on_from_graph_b{i}", 0, f"on_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_off_from_graph_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_motion_reset_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_dynamic_reset_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_dynamic_amt_reset_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_motion_rate_reset_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_motion_depth_reset_b{i}", 0)
    device.add_line("delete_band_sel", i, f"msg_motion_direction_reset_b{i}", 0)
    # Delete resets must not drive the hot pak state bus back into eq_display.
    # Otherwise the first reset can re-emit a stale enabled band before the
    # final off state lands, which recreates the deleted node as dimmed.
    device.add_line(f"msg_off_from_graph_b{i}", 0, f"set_on_from_graph_b{i}", 0)
    device.add_line(f"msg_motion_reset_b{i}", 0, f"set_motion_from_graph_b{i}", 0)
    device.add_line(f"msg_dynamic_reset_b{i}", 0, f"set_dynamic_from_graph_b{i}", 0)
    device.add_line(f"msg_dynamic_amt_reset_b{i}", 0, f"set_dynamic_amt_from_graph_b{i}", 0)
    device.add_line(f"msg_motion_rate_reset_b{i}", 0, f"set_motion_rate_from_graph_b{i}", 0)
    device.add_line(f"msg_motion_depth_reset_b{i}", 0, f"set_motion_depth_from_graph_b{i}", 0)
    device.add_line(f"msg_motion_direction_reset_b{i}", 0, f"set_motion_direction_from_graph_b{i}", 0)
    device.add_line(f"set_on_from_graph_b{i}", 0, f"on_b{i}", 0)
    device.add_line(f"set_motion_from_graph_b{i}", 0, f"motion_b{i}", 0)
    device.add_line(f"set_dynamic_from_graph_b{i}", 0, f"dynamic_b{i}", 0)
    device.add_line(f"set_dynamic_amt_from_graph_b{i}", 0, f"dynamic_amt_b{i}", 0)
    device.add_line(f"set_motion_rate_from_graph_b{i}", 0, f"motion_rate_b{i}", 0)
    device.add_line(f"set_motion_depth_from_graph_b{i}", 0, f"motion_depth_b{i}", 0)
    device.add_line(f"set_motion_direction_from_graph_b{i}", 0, f"motion_direction_b{i}", 0)

# ---------------------------------------------------------------------------
# DSP — Per-band jsui messaging using pak + prepend
#
# pak (all-hot): ANY inlet change triggers full list output.
# pak i freq gain q type enabled motion dynamic dynamic_amount motion_rate motion_depth motion_direction
#     -> prepend set_band -> eq_display
# ---------------------------------------------------------------------------
for i in range(NUM_BANDS):
    lbl = str(i + 1)
    default_freq, default_type = BAND_DEFAULTS[i]
    default_enabled = BAND_DEFAULT_ENABLED[i]
    default_motion_rate = MOTION_RATE_DEFAULTS[i]
    default_motion_depth = MOTION_DEPTH_DEFAULTS[i]
    default_motion_direction = MOTION_DIRECTION_DEFAULTS[i]

    # pak: 12 inlets, all hot. Initial: band_idx, freq, gain, q, type, on,
    # motion, dynamic, dynamic_amount, motion_rate, motion_depth, motion_direction
    device.add_newobj(
        f"pak_b{i}",
        f"pak {i} {default_freq} 0. 1. {default_type} {default_enabled} 0 0 0. {default_motion_rate} {default_motion_depth} {default_motion_direction}",
        numinlets=12, numoutlets=1,
        outlettype=[""],
        patching_rect=[800, 200 + i * 40, 200, 20]
    )

    # prepend set_band
    device.add_newobj(
        f"prepend_b{i}",
        "prepend set_band",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[800, 225 + i * 40, 120, 20]
    )

    # pak -> prepend -> eq_display
    device.add_line(f"pak_b{i}", 0, f"prepend_b{i}", 0)
    device.add_line(f"prepend_b{i}", 0, "eq_display", 0)
    device.add_line(f"prepend_b{i}", 0, "selected_core_rail", 0)
    device.add_line(f"prepend_b{i}", 0, "selected_band_column", 0)

# ---------------------------------------------------------------------------
# DSP — Per-band filtercoeff~ + biquad~ (true parametric EQ)
#
# Architecture: per-band filtercoeff~ generates 5 biquad coefficients
# at signal rate -> connects to biquad~ inlets 1-5.
# biquad~ inlet 0 receives audio from previous stage.
# Bands cascade in series: plugin~ -> biquad~_b0 -> biquad~_b1 -> ... -> out
#
# filtercoeff~ inlets:
#   0: frequency (Hz) - float
#   1: gain (LINEAR) - float via dbtoa
#   2: Q (resonance) - float
#
# filtercoeff~ outlets (all signal):
#   0: a0, 1: a1, 2: a2, 3: b1, 4: b2
#
# biquad~ inlets:
#   0: signal input
#   1: a0, 2: a1, 3: a2, 4: b1, 5: b2
# ---------------------------------------------------------------------------

for i in range(NUM_BANDS):
    default_freq, default_type = BAND_DEFAULTS[i]
    default_motion_rate = MOTION_RATE_DEFAULTS[i]
    default_motion_direction = MOTION_DIRECTION_DEFAULTS[i]
    fc_type = FILTERCOEFF_TYPES[default_type]

    # One filtercoeff~ per band (shared L+R — coefficients are the same)
    device.add_newobj(
        f"fc_b{i}",
        f"filtercoeff~ {fc_type}",
        numinlets=3, numoutlets=5,
        outlettype=["signal", "signal", "signal", "signal", "signal"],
        patching_rect=[100 + i * 60, 350, 80, 20]
    )

    # "resamp 1" message for smooth coefficient updates
    device.add_box({
        "box": {
            "id": f"msg_resamp_b{i}",
            "maxclass": "message",
            "text": "resamp 1",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [100 + i * 60, 320, 60, 20],
        }
    })
    device.add_line("lb_init", 0, f"msg_resamp_b{i}", 0)
    device.add_line(f"msg_resamp_b{i}", 0, f"fc_b{i}", 0)

    # Two biquad~ per band (one per channel)
    for ch in ["l", "r"]:
        y_off = 0 if ch == "l" else 200
        device.add_newobj(
            f"bq_b{i}_{ch}",
            "biquad~",
            numinlets=6, numoutlets=1,
            outlettype=["signal"],
            patching_rect=[100 + i * 60, 400 + y_off, 50, 20]
        )

        # Connect filtercoeff~ outlets 0-4 -> biquad~ inlets 1-5
        for c in range(5):
            device.add_line(f"fc_b{i}", c, f"bq_b{i}_{ch}", c + 1)

    # ------------------------------------------------------------------
    # Parameter smoothing — pack f {default} 20 -> line~
    # Prevents clicks when filtercoeff~ coefficients change abruptly.
    # pack packs [value, 20] so line~ ramps to new value over 20 ms.
    # ------------------------------------------------------------------

    # Freq smoothing
    device.add_newobj(
        f"pk_freq_b{i}",
        f"pack f {default_freq} 20",
        numinlets=2, numoutlets=1,
        outlettype=[""],
        patching_rect=[1100, 350 + i * 30, 80, 20]
    )
    device.add_newobj(
        f"ln_freq_b{i}",
        "line~",
        numinlets=2, numoutlets=2,
        outlettype=["signal", "bang"],
        patching_rect=[1190, 350 + i * 30, 40, 20]
    )
    device.add_line(f"pk_freq_b{i}", 0, f"ln_freq_b{i}", 0)

    # Motion: cycle~ -> direction-weighted frequency ratio -> multiply base freq
    device.add_newobj(
        f"motion_lfo_b{i}",
        f"cycle~ {default_motion_rate}",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[1240, 350 + i * 30, 58, 20]
    )
    device.add_newobj(
        f"motion_depth_mul_b{i}",
        "expr~ pow(2., $v1 * $f2)",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[1306, 350 + i * 30, 48, 20]
    )
    device.add_newobj(
        f"motion_freq_mul_b{i}",
        "*~ 1.",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[1362, 350 + i * 30, 48, 20]
    )
    device.add_newobj(
        f"motion_depth_expr_b{i}",
        "expr ($f2 > 0.5) ? (($f1 / 100.) * 1.25 * cos($f3 * 0.0174533)) : 0.",
        numinlets=3, numoutlets=1,
        outlettype=[""],
        patching_rect=[1418, 350 + i * 30, 120, 20]
    )
    device.add_line(f"ln_freq_b{i}", 0, f"motion_freq_mul_b{i}", 0)
    device.add_line(f"motion_lfo_b{i}", 0, f"motion_depth_mul_b{i}", 0)
    device.add_line(f"motion_depth_mul_b{i}", 0, f"motion_freq_mul_b{i}", 1)
    device.add_line(f"motion_freq_mul_b{i}", 0, f"fc_b{i}", 0)

    # Gain smoothing in dB, then direction-weighted gain motion, then dB -> linear
    device.add_newobj(
        f"pk_gain_db_b{i}",
        "pack f 0. 20",
        numinlets=2, numoutlets=1,
        outlettype=[""],
        patching_rect=[1100, 390 + i * 30, 80, 20]
    )
    device.add_newobj(
        f"ln_gain_db_b{i}",
        "line~",
        numinlets=2, numoutlets=2,
        outlettype=["signal", "bang"],
        patching_rect=[1190, 390 + i * 30, 40, 20]
    )
    device.add_newobj(
        f"motion_gain_depth_expr_b{i}",
        "expr ($f2 > 0.5) ? (($f1 / 100.) * 12. * sin($f3 * 0.0174533)) : 0.",
        numinlets=3, numoutlets=1,
        outlettype=[""],
        patching_rect=[1240, 390 + i * 30, 120, 20]
    )
    device.add_newobj(
        f"motion_gain_mul_b{i}",
        "*~ 0.",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[1368, 390 + i * 30, 44, 20]
    )
    device.add_newobj(
        f"motion_gain_sum_b{i}",
        "+~ 0.",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[1420, 390 + i * 30, 44, 20]
    )
    device.add_newobj(
        f"gain_dbtoa_sig_b{i}",
        "expr~ pow(10., $v1 * 0.05)",
        numinlets=1, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[1472, 390 + i * 30, 92, 20]
    )
    device.add_line(f"pk_gain_db_b{i}", 0, f"ln_gain_db_b{i}", 0)
    device.add_line(f"ln_gain_db_b{i}", 0, f"motion_gain_sum_b{i}", 0)
    device.add_line(f"motion_lfo_b{i}", 0, f"motion_gain_mul_b{i}", 0)
    device.add_line(f"motion_gain_mul_b{i}", 0, f"motion_gain_sum_b{i}", 1)
    device.add_line(f"motion_gain_sum_b{i}", 0, f"gain_dbtoa_sig_b{i}", 0)
    device.add_line(f"gain_dbtoa_sig_b{i}", 0, f"fc_b{i}", 1)

    # Q smoothing
    device.add_newobj(
        f"pk_q_b{i}",
        "pack f 1. 20",
        numinlets=2, numoutlets=1,
        outlettype=[""],
        patching_rect=[1100, 430 + i * 30, 80, 20]
    )
    device.add_newobj(
        f"ln_q_b{i}",
        "line~",
        numinlets=2, numoutlets=2,
        outlettype=["signal", "bang"],
        patching_rect=[1190, 430 + i * 30, 40, 20]
    )
    device.add_line(f"pk_q_b{i}", 0, f"ln_q_b{i}", 0)
    device.add_line(f"ln_q_b{i}", 0, f"fc_b{i}", 2)

    # Type switching: menu index -> filtercoeff~ type message
    # Route the type menu output to select the right type name
    device.add_newobj(
        f"type_sel_b{i}",
        "select 0 1 2 3 4 5 6 7",
        numinlets=1, numoutlets=9,
        outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang", "bang", ""],
        patching_rect=[700, 350 + i * 30, 140, 20]
    )

    # Message boxes for each filter type
    for ti, tname in enumerate(FILTERCOEFF_TYPES):
        device.add_box({
            "box": {
                "id": f"msg_type_{ti}_b{i}",
                "maxclass": "message",
                "text": tname,
                "numinlets": 2,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [700 + ti * 65, 380 + i * 30, 60, 20],
            }
        })
        # select outlet -> type message -> filtercoeff~
        device.add_line(f"type_sel_b{i}", ti, f"msg_type_{ti}_b{i}", 0)
        device.add_line(f"msg_type_{ti}_b{i}", 0, f"fc_b{i}", 0)

    # Enable/disable: when OFF, send "off" to filtercoeff~ (passthrough)
    # when ON, send the current type back
    # Use a gate: on_toggle -> gate -> type message replay
    # Simpler: use select 0 1 on the toggle output
    device.add_newobj(
        f"on_sel_b{i}",
        "select 0 1",
        numinlets=1, numoutlets=3,
        outlettype=["bang", "bang", ""],
        patching_rect=[900, 350 + i * 30, 60, 20]
    )
    # When OFF (0): send "off" to filtercoeff~
    device.add_box({
        "box": {
            "id": f"msg_off_b{i}",
            "maxclass": "message",
            "text": "off",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [900, 380 + i * 30, 30, 20],
        }
    })
    # When ON (1): resend current type via a trigger chain
    # We'll bang the type menu to re-output its current value
    device.add_newobj(
        f"on_bang_b{i}",
        "t b",
        numinlets=1, numoutlets=1,
        outlettype=["bang"],
        patching_rect=[940, 380 + i * 30, 30, 20]
    )

    device.add_line(f"on_sel_b{i}", 0, f"msg_off_b{i}", 0)     # OFF -> "off" msg
    device.add_line(f"msg_off_b{i}", 0, f"fc_b{i}", 0)          # "off" -> filtercoeff~
    device.add_line(f"on_sel_b{i}", 1, f"on_bang_b{i}", 0)      # ON -> bang
    device.add_line(f"on_bang_b{i}", 0, f"type_b{i}", 0)        # bang -> type menu re-output

# ---------------------------------------------------------------------------
# DSP — Parameter routing
# Each parameter goes to BOTH the DSP chain AND the pak for jsui update.
# Smoothing sits between the dial/dbtoa and the filtercoeff~ inlets.
# ---------------------------------------------------------------------------
for i in range(NUM_BANDS):
    # freq -> pak inlet 1 AND smoothing chain -> filtercoeff~ inlet 0
    device.add_line(f"freq_b{i}", 0, f"pak_b{i}", 1)
    device.add_line(f"freq_b{i}", 0, f"pk_freq_b{i}", 0)
    # pk_freq_b{i} -> ln_freq_b{i} -> fc_b{i} 0  (already wired above)

    # gain -> pak inlet 2 AND dbtoa -> gain smoothing -> filtercoeff~ inlet 1
    device.add_line(f"gain_b{i}", 0, f"pak_b{i}", 2)
    device.add_line(f"gain_b{i}", 0, f"pk_gain_db_b{i}", 0)
    # pk_gain_db_b{i} -> ln_gain_db_b{i} -> motion_gain_sum_b{i}
    # -> gain_dbtoa_sig_b{i} -> fc_b{i} 1  (already wired above)

    # q -> pak inlet 3 AND smoothing chain -> filtercoeff~ inlet 2
    device.add_line(f"q_b{i}", 0, f"pak_b{i}", 3)
    device.add_line(f"q_b{i}", 0, f"pk_q_b{i}", 0)
    # pk_q_b{i} -> ln_q_b{i} -> fc_b{i} 2  (already wired above)

    # type -> pak inlet 4 AND type_sel for filtercoeff~ type switching
    device.add_line(f"type_b{i}", 0, f"pak_b{i}", 4)
    device.add_line(f"type_b{i}", 0, f"type_sel_b{i}", 0)

    # on -> pak inlet 5 AND on_sel for enable/disable
    device.add_line(f"on_b{i}", 0, f"pak_b{i}", 5)
    device.add_line(f"on_b{i}", 0, f"on_sel_b{i}", 0)
    device.add_line(f"motion_b{i}", 0, f"pak_b{i}", 6)
    device.add_line(f"dynamic_b{i}", 0, f"pak_b{i}", 7)
    device.add_line(f"dynamic_amt_b{i}", 0, f"pak_b{i}", 8)
    device.add_line(f"motion_rate_b{i}", 0, f"pak_b{i}", 9)
    device.add_line(f"motion_depth_b{i}", 0, f"pak_b{i}", 10)
    device.add_line(f"motion_direction_b{i}", 0, f"pak_b{i}", 11)
    device.add_line(f"motion_rate_b{i}", 0, f"motion_lfo_b{i}", 0)
    device.add_line(f"motion_depth_b{i}", 0, f"motion_depth_expr_b{i}", 0)
    device.add_line(f"motion_b{i}", 0, f"motion_depth_expr_b{i}", 1)
    device.add_line(f"motion_direction_b{i}", 0, f"motion_depth_expr_b{i}", 2)
    device.add_line(f"motion_depth_expr_b{i}", 0, f"motion_depth_mul_b{i}", 1)
    device.add_line(f"motion_depth_b{i}", 0, f"motion_gain_depth_expr_b{i}", 0)
    device.add_line(f"motion_b{i}", 0, f"motion_gain_depth_expr_b{i}", 1)
    device.add_line(f"motion_direction_b{i}", 0, f"motion_gain_depth_expr_b{i}", 2)
    device.add_line(f"motion_gain_depth_expr_b{i}", 0, f"motion_gain_mul_b{i}", 1)

# ---------------------------------------------------------------------------
# DSP — Audio signal cascade: plugin~ -> biquad~_b0 -> biquad~_b1 -> ... -> out
# ---------------------------------------------------------------------------
for ch in ["l", "r"]:
    ch_idx = 0 if ch == "l" else 1

    # plugin~ -> first biquad~
    device.add_line("obj-plugin", ch_idx, f"bq_b0_{ch}", 0)

    # Chain biquad~ stages in series
    for i in range(NUM_BANDS - 1):
        device.add_line(f"bq_b{i}_{ch}", 0, f"bq_b{i+1}_{ch}", 0)

# ---------------------------------------------------------------------------
# DSP — Output gain stage with parameter smoothing
# out_gain dial (dB) -> dbtoa -> pack+line~ -> *~ L, *~ R
#
# line~ outlet 0 (signal) connects directly to *~ inlet 1 on both channels.
# This ramps the output gain over 20 ms, eliminating gain-change clicks.
# ---------------------------------------------------------------------------
device.add_newobj("out_dbtoa", "dbtoa",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[600, 600, 50, 20])

# Output gain smoothing
device.add_newobj("pk_out", "pack f 1. 20",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[660, 600, 80, 20])
device.add_newobj("ln_out", "line~",
                  numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"],
                  patching_rect=[750, 600, 40, 20])

device.add_newobj("out_mul_l", "*~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 620, 40, 20])

device.add_newobj("out_mul_r", "*~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[200, 620, 40, 20])

device.add_line("out_gain", 0, "out_dbtoa", 0)
device.add_line("out_dbtoa", 0, "pk_out", 0)
device.add_line("pk_out", 0, "ln_out", 0)
# line~ signal outlet fans out to both multiplier gain inlets
device.add_line("ln_out", 0, "out_mul_l", 1)
device.add_line("ln_out", 0, "out_mul_r", 1)
device.add_line("out_gain_compact", 0, "out_gain", 0)
device.add_newobj("prepend_set_out_gain_compact", "prepend set",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[820, 600, 80, 20])
device.add_line("out_gain", 0, "prepend_set_out_gain_compact", 0)
device.add_line("prepend_set_out_gain_compact", 0, "out_gain_compact", 0)

# Last biquad~ -> output gain multiplier
device.add_line(f"bq_b{NUM_BANDS-1}_l", 0, "out_mul_l", 0)
device.add_line(f"bq_b{NUM_BANDS-1}_r", 0, "out_mul_r", 0)

# ---------------------------------------------------------------------------
# DSP — Bypass: selector~ 2 1 (1=processed, 2=dry)
# bypass_toggle 0=not bypassed (processed), 1=bypassed (dry)
# toggle output: 0 -> +1 -> selector 1 (processed)
#                1 -> +1 -> selector 2 (dry)
# ---------------------------------------------------------------------------
device.add_newobj("bypass_add1", "+ 1",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[600, 660, 40, 20])

device.add_newobj("bypass_trig", "t i i",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[600, 685, 50, 20])

device.add_newobj("bypass_sel_l", "selector~ 2 1",
                  numinlets=3, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 700, 80, 20])

device.add_newobj("bypass_sel_r", "selector~ 2 1",
                  numinlets=3, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[200, 700, 80, 20])

device.add_line("bypass_toggle", 0, "bypass_add1", 0)
device.add_line("bypass_compact", 0, "bypass_toggle", 0)
device.add_newobj("prepend_set_bypass_compact", "prepend set",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[660, 660, 80, 20])
device.add_line("bypass_toggle", 0, "prepend_set_bypass_compact", 0)
device.add_line("prepend_set_bypass_compact", 0, "bypass_compact", 0)
device.add_line("bypass_add1", 0, "bypass_trig", 0)
device.add_line("bypass_trig", 0, "bypass_sel_l", 0)
device.add_line("bypass_trig", 1, "bypass_sel_r", 0)

# Processed -> selector inlet 1
device.add_line("out_mul_l", 0, "bypass_sel_l", 1)
device.add_line("out_mul_r", 0, "bypass_sel_r", 1)

# Dry -> selector inlet 2
device.add_line("obj-plugin", 0, "bypass_sel_l", 2)
device.add_line("obj-plugin", 1, "bypass_sel_r", 2)

# Selector -> plugout~
device.add_line("bypass_sel_l", 0, "obj-plugout", 0)
device.add_line("bypass_sel_r", 0, "obj-plugout", 1)

# ---------------------------------------------------------------------------
# DSP — Output meters: tap signal after bypass selector (post-output level)
# ---------------------------------------------------------------------------
device.add_line("bypass_sel_l", 0, "meter_l", 0)
device.add_line("bypass_sel_r", 0, "meter_r", 0)

# ---------------------------------------------------------------------------
# DSP — Analyzer source switch: PRE (dry input) or POST (heard output)
# ---------------------------------------------------------------------------
device.add_newobj("analyzer_pre_sum", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[300, 718, 40, 20])
device.add_newobj("analyzer_pre_avg", "*~ 0.5",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[346, 718, 44, 20])
device.add_newobj("analyzer_post_sum", "+~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[300, 742, 40, 20])
device.add_newobj("analyzer_post_avg", "*~ 0.5",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[346, 742, 44, 20])
device.add_newobj("analyzer_source_sel", "selector~ 2 1",
                  numinlets=3, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[396, 730, 90, 20])
device.add_newobj("analyzer_gate", "*~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[492, 730, 40, 20])
device.add_newobj("analyzer_gain_pack", "pack 0. 30",
                  numinlets=2, numoutlets=1,
                  outlettype=["list"],
                  patching_rect=[538, 730, 72, 20])
device.add_newobj("analyzer_gain_line", "line~",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[616, 730, 40, 20])
device.add_line("obj-plugin", 0, "analyzer_pre_sum", 0)
device.add_line("obj-plugin", 1, "analyzer_pre_sum", 1)
device.add_line("analyzer_pre_sum", 0, "analyzer_pre_avg", 0)
device.add_line("bypass_sel_l", 0, "analyzer_post_sum", 0)
device.add_line("bypass_sel_r", 0, "analyzer_post_sum", 1)
device.add_line("analyzer_post_sum", 0, "analyzer_post_avg", 0)
device.add_line("analyzer_pre_avg", 0, "analyzer_source_sel", 1)
device.add_line("analyzer_post_avg", 0, "analyzer_source_sel", 2)
device.add_line("msg_analyzer_pre_src", 0, "analyzer_source_sel", 0)
device.add_line("msg_analyzer_post_src", 0, "analyzer_source_sel", 0)
device.add_line("analyzer_source_sel", 0, "analyzer_gate", 0)
device.add_line("msg_analyzer_off", 0, "analyzer_gain_pack", 0)
device.add_line("msg_analyzer_on", 0, "analyzer_gain_pack", 0)
device.add_line("analyzer_gain_pack", 0, "analyzer_gain_line", 0)
device.add_line("analyzer_gain_line", 0, "analyzer_gate", 1)
device.add_line("analyzer_gate", 0, "peq_spectroscope", 0)
device.add_line("analyzer_gate", 0, "peq_spectroscope", 1)

# ---------------------------------------------------------------------------
# DSP — Native analyzer behind the graph
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DSP — jsui drag output -> update freq/gain/Q dials (bidirectional)
# eq_display outlet 0: "selected_band N" — sync focus tab selection
# eq_display outlet 1: "band_freq N freq" — route to freq_bi dial
# eq_display outlet 2: "band_gain N gain" — route to gain_bi dial
# eq_display outlet 3: "band_q N q" — route to q_bi dial
#
# Route chain: outlet -> route band_freq -> route 0 1 2 3 4 5 6 7 -> dial
# ---------------------------------------------------------------------------
# Freq routing from jsui drag
device.add_newobj("route_freq", "route band_freq",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[10, 780, 100, 20])
device.add_newobj("route_freq_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[10, 805, 200, 20])
device.add_line("eq_display", 1, "route_freq", 0)
device.add_line("selected_core_rail", 0, "route_freq", 0)
device.add_line("selected_band_column", 0, "route_freq", 0)
device.add_line("route_freq", 0, "route_freq_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_freq_idx", i, f"freq_b{i}", 0)
    device.add_line("route_freq_idx", i, f"pak_b{i}", 1)

# Gain routing from jsui drag
device.add_newobj("route_gain", "route band_gain",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[220, 780, 100, 20])
device.add_newobj("route_gain_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[220, 805, 200, 20])
device.add_line("eq_display", 2, "route_gain", 0)
device.add_line("selected_core_rail", 0, "route_gain", 0)
device.add_line("selected_band_column", 0, "route_gain", 0)
device.add_line("route_gain", 0, "route_gain_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_gain_idx", i, f"gain_b{i}", 0)
    device.add_line("route_gain_idx", i, f"pak_b{i}", 2)

# Q routing from jsui mouse wheel
device.add_newobj("route_q", "route band_q",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[430, 780, 80, 20])
device.add_newobj("route_q_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[430, 805, 200, 20])
device.add_line("eq_display", 3, "route_q", 0)
device.add_line("selected_core_rail", 0, "route_q", 0)
device.add_line("selected_band_column", 0, "route_q", 0)
device.add_line("route_q", 0, "route_q_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_q_idx", i, f"q_b{i}", 0)
    device.add_line("route_q_idx", i, f"pak_b{i}", 3)

device.add_newobj("route_type", "route band_type",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[640, 780, 90, 20])
device.add_newobj("route_type_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[640, 805, 200, 20])
device.add_line("eq_display", 0, "route_type", 0)
device.add_line("selected_band_column", 0, "route_type", 0)
device.add_line("route_type", 0, "route_type_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_type_idx", i, f"type_b{i}", 0)
    device.add_line("route_type_idx", i, f"pak_b{i}", 4)

device.add_newobj("route_enable", "route band_enable",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[850, 780, 104, 20])
device.add_newobj("route_enable_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[850, 805, 200, 20])
device.add_line("eq_display", 0, "route_enable", 0)
device.add_line("selected_band_column", 0, "route_enable", 0)
device.add_line("route_enable", 0, "route_enable_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_enable_idx", i, f"on_b{i}", 0)
    device.add_line("route_enable_idx", i, f"pak_b{i}", 5)

device.add_newobj("route_motion", "route band_motion",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[1060, 780, 104, 20])
device.add_newobj("route_motion_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[1060, 805, 200, 20])
device.add_line("eq_display", 0, "route_motion", 0)
device.add_line("selected_band_column", 0, "route_motion", 0)
device.add_line("route_motion", 0, "route_motion_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_motion_idx", i, f"motion_b{i}", 0)
    device.add_line("route_motion_idx", i, f"pak_b{i}", 6)

device.add_newobj("route_dynamic", "route band_dynamic",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[1270, 780, 114, 20])
device.add_newobj("route_dynamic_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[1270, 805, 200, 20])
device.add_line("eq_display", 0, "route_dynamic", 0)
device.add_line("selected_band_column", 0, "route_dynamic", 0)
device.add_line("route_dynamic", 0, "route_dynamic_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_dynamic_idx", i, f"dynamic_b{i}", 0)
    device.add_line("route_dynamic_idx", i, f"pak_b{i}", 7)

device.add_newobj("route_dynamic_amount", "route band_dynamic_amount",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[1490, 780, 144, 20])
device.add_newobj("route_dynamic_amount_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[1490, 805, 200, 20])
device.add_line("eq_display", 0, "route_dynamic_amount", 0)
device.add_line("route_dynamic_amount", 0, "route_dynamic_amount_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_dynamic_amount_idx", i, f"dynamic_amt_b{i}", 0)
    device.add_line("route_dynamic_amount_idx", i, f"pak_b{i}", 8)

device.add_newobj("route_motion_rate", "route band_motion_rate",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[1710, 780, 132, 20])
device.add_newobj("route_motion_rate_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[1710, 805, 200, 20])
device.add_line("eq_display", 0, "route_motion_rate", 0)
device.add_line("selected_band_column", 0, "route_motion_rate", 0)
device.add_line("route_motion_rate", 0, "route_motion_rate_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_motion_rate_idx", i, f"motion_rate_b{i}", 0)
    device.add_line("route_motion_rate_idx", i, f"pak_b{i}", 9)

device.add_newobj("route_motion_depth", "route band_motion_depth",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[1930, 780, 140, 20])
device.add_newobj("route_motion_depth_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[1930, 805, 200, 20])
device.add_line("eq_display", 0, "route_motion_depth", 0)
device.add_line("selected_band_column", 0, "route_motion_depth", 0)
device.add_line("route_motion_depth", 0, "route_motion_depth_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_motion_depth_idx", i, f"motion_depth_b{i}", 0)
    device.add_line("route_motion_depth_idx", i, f"pak_b{i}", 10)

device.add_newobj("route_motion_direction", "route band_motion_direction",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[2140, 780, 140, 20])
device.add_newobj("route_motion_direction_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[2140, 805, 200, 20])
device.add_line("eq_display", 0, "route_motion_direction", 0)
device.add_line("selected_band_column", 0, "route_motion_direction", 0)
device.add_line("route_motion_direction", 0, "route_motion_direction_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_motion_direction_idx", i, f"motion_direction_b{i}", 0)
    device.add_line("route_motion_direction_idx", i, f"pak_b{i}", 11)

# ---------------------------------------------------------------------------
# Selected-band proxy UI sync and routing
# ---------------------------------------------------------------------------
device.add_newobj(
    "route_selected_ui",
    "route selected_label selected_status selected_freq selected_gain selected_q selected_type selected_enable selected_motion selected_dynamic selected_dynamic_amount selected_motion_rate selected_motion_depth selected_motion_direction",
    numinlets=1, numoutlets=14,
    outlettype=[""] * 14,
    patching_rect=[2380, 780, 560, 20]
)
device.add_line("selected_band_column", 0, "route_selected_ui", 0)

for route_index, prepend_id, target_id, patch_x in [
    (0, "set_selected_label", "selected_band_label", 2380),
    (1, "set_selected_status", "selected_band_status", 2460),
    (2, "set_selected_freq", "selected_freq", 2540),
    (3, "set_selected_gain", "selected_gain", 2620),
    (4, "set_selected_q", "selected_q", 2700),
    (5, "set_selected_type", "selected_type", 2780),
    (6, "set_selected_enable", "selected_enable", 2860),
    (7, "set_selected_motion", "selected_motion", 2940),
    (8, "set_selected_dynamic", "selected_dynamic", 3020),
    (9, "set_selected_dynamic_amt", "selected_dynamic_amt", 3100),
    (10, "set_selected_motion_rate", "selected_motion_rate", 3180),
    (11, "set_selected_motion_depth", "selected_motion_depth", 3260),
    (12, "set_selected_motion_direction", "selected_motion_direction", 3340),
]:
    device.add_newobj(prepend_id, "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[patch_x, 806, 72, 20])
    device.add_line("route_selected_ui", route_index, prepend_id, 0)
    device.add_line(prepend_id, 0, target_id, 0)

for control_id, pack_text, target_prefix, patch_y in [
    ("selected_freq", "pack f i", "freq_b", 832),
    ("selected_gain", "pack f i", "gain_b", 858),
    ("selected_q", "pack f i", "q_b", 884),
    ("selected_type", "pack i i", "type_b", 910),
    ("selected_enable", "pack i i", "on_b", 936),
    ("selected_motion", "pack i i", "motion_b", 962),
    ("selected_dynamic", "pack i i", "dynamic_b", 988),
    ("selected_dynamic_amt", "pack f i", "dynamic_amt_b", 1014),
    ("selected_motion_rate", "pack f i", "motion_rate_b", 1040),
    ("selected_motion_depth", "pack f i", "motion_depth_b", 1066),
    ("selected_motion_direction", "pack f i", "motion_direction_b", 1092),
]:
    pack_id = f"{control_id}_pack"
    swap_id = f"{control_id}_swap"
    route_id = f"{control_id}_route_idx"
    device.add_newobj(pack_id, pack_text, numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[2380, patch_y, 72, 20])
    device.add_box({
        "box": {
            "id": swap_id,
            "maxclass": "message",
            "text": "$2 $1",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [2460, patch_y, 46, 20],
        }
    })
    device.add_newobj(route_id, "route 0 1 2 3 4 5 6 7", numinlets=1, numoutlets=9,
                      outlettype=["", "", "", "", "", "", "", "", ""],
                      patching_rect=[2514, patch_y, 200, 20])
    device.add_line(control_id, 0, pack_id, 0)
    device.add_line("selected_band_store", 0, pack_id, 1)
    device.add_line(pack_id, 0, swap_id, 0)
    device.add_line(swap_id, 0, route_id, 0)
    for i in range(NUM_BANDS):
        device.add_line(route_id, i, f"{target_prefix}{i}", 0)

# ---------------------------------------------------------------------------
# Parameter banks — Live/Push grouping
# ---------------------------------------------------------------------------
device.set_parameter_bank_name(0, "Global")
for position, varname in enumerate([
    "Out Gain",
    "Bypass",
    "Analyzer Mode",
    "Display Range",
    "Focus Band",
]):
    device.assign_parameter_bank(varname, bank=0, position=position)

for i in range(NUM_BANDS):
    label = i + 1
    core_bank = 1 + i
    motion_bank = 1 + NUM_BANDS + i

    device.set_parameter_bank_name(core_bank, f"B{label} Core")
    for position, varname in enumerate([
        f"Freq B{label}",
        f"Gain B{label}",
        f"Q B{label}",
        f"Type B{label}",
        f"On B{label}",
        f"Motion B{label}",
        f"Dynamic B{label}",
        f"Dynamic Amt B{label}",
    ]):
        device.assign_parameter_bank(varname, bank=core_bank, position=position)

    device.set_parameter_bank_name(motion_bank, f"B{label} Motion")
    for position, varname in enumerate([
        f"Motion Rate B{label}",
        f"Motion Depth B{label}",
        f"Motion Direction B{label}",
    ]):
        device.assign_parameter_bank(varname, bank=motion_bank, position=position)

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/"
    "Max Audio Effect/Parametric EQ.amxd"
)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
