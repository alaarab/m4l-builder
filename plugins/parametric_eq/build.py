"""Parametric EQ — Pro-Q style 8-band parametric equalizer.

Hero device showcasing the eq_curve jsui engine with interactive draggable
nodes. 8 fully parametric bands using filtercoeff~ + biquad~ for true
parametric EQ quality. Supports Peak/LShelf/HShelf/LP/HP/Notch/BP/AP types.

Layout (760×188 visible surface):
  Left strip: compact selected-band mini-column using native Live controls
  Hero graph: interactive EQ curve with integrated post-output analyzer,
              draggable band nodes, mouse wheel Q, shift+drag fine-tune,
              cmd+drag lock gain/Q axis, hover HUD
  Right strip: minimal global switches for analyzer, range, and bypass
  Hidden canonical controls: per-band parameter widgets and focus tab kept
                             offscreen for parameter identity and routing

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
from m4l_builder.eq_shells import (
    add_band_message_routers,
    add_selected_band_focus_shell,
    add_selected_band_proxy_shell,
)
from m4l_builder.engines.eq_band_column import eq_band_column_js
from m4l_builder.engines.eq_curve import eq_curve_js, EQ_CURVE_INLETS, EQ_CURVE_OUTLETS
from m4l_builder.recipes import parametric_eq_band_backend


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


def band_nav_js() -> str:
    """Return jsui code for the compact vertical band navigator."""
    return """\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

var num_bands = 8;
var selected = -1;
var enabled = [1, 1, 1, 1, 0, 0, 0, 0];
var colors = [
    [0.90, 0.35, 0.35, 1.0],
    [0.90, 0.65, 0.25, 1.0],
    [0.85, 0.85, 0.30, 1.0],
    [0.35, 0.80, 0.45, 1.0],
    [0.35, 0.75, 0.85, 1.0],
    [0.40, 0.55, 0.90, 1.0],
    [0.65, 0.45, 0.85, 1.0],
    [0.85, 0.45, 0.65, 1.0]
];

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function item_layout() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    var gap = 3;
    var inset = 3;
    var item_h = Math.floor((h - inset * 2 - gap * (num_bands - 1)) / num_bands);
    var rects = [];
    var y = inset;
    var i;
    for (i = 0; i < num_bands; i++) {
        rects.push([4, y, w - 8, item_h]);
        y += item_h + gap;
    }
    return rects;
}

function set_num_bands(v) {
    num_bands = clamp(Math.floor(v), 1, 8);
    mgraphics.redraw();
}

function set_band(idx, freq, gain, q, type, is_enabled) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= 8) return;
    enabled[idx] = is_enabled ? 1 : 0;
    mgraphics.redraw();
}

function set_selected(idx) {
    idx = Math.floor(idx);
    selected = idx;
    mgraphics.redraw();
}

function paint() {
    var rects = item_layout();
    var i, r, c, fill_alpha, stroke_alpha, text_alpha;

    mgraphics.set_source_rgba(0.0, 0.0, 0.0, 0.0);
    mgraphics.paint();

    for (i = 0; i < num_bands; i++) {
        r = rects[i];
        c = colors[i];
        fill_alpha = selected === i ? 0.92 : (enabled[i] ? 0.22 : 0.05);
        stroke_alpha = selected === i ? 0.98 : (enabled[i] ? 0.82 : 0.18);
        text_alpha = selected === i ? 0.96 : (enabled[i] ? 0.76 : 0.34);

        mgraphics.set_source_rgba(c[0], c[1], c[2], fill_alpha);
        mgraphics.rectangle_rounded(r[0], r[1], r[2], r[3], 4, 4);
        mgraphics.fill_preserve();

        mgraphics.set_source_rgba(c[0], c[1], c[2], stroke_alpha);
        mgraphics.set_line_width(selected === i ? 1.8 : 1.0);
        mgraphics.stroke();

        mgraphics.set_source_rgba(c[0], c[1], c[2], enabled[i] ? 0.94 : 0.22);
        mgraphics.rectangle(r[0] + 2, r[1] + 2, 3, r[3] - 4);
        mgraphics.fill();

        mgraphics.select_font_face("Arial Bold");
        mgraphics.set_font_size(8.2);
        mgraphics.set_source_rgba(
            selected === i ? 0.08 : 0.93,
            selected === i ? 0.09 : 0.94,
            selected === i ? 0.11 : 0.96,
            text_alpha
        );
        mgraphics.move_to(r[0] + 11, r[1] + r[3] * 0.68);
        mgraphics.show_text("B" + (i + 1));
    }
}

function onclick(x, y, but, cmd, shift, caps, opt, ctrl) {
    var rects = item_layout();
    var i, r;
    for (i = 0; i < num_bands; i++) {
        r = rects[i];
        if (x >= r[0] && x <= (r[0] + r[2]) && y >= r[1] && y <= (r[1] + r[3])) {
            outlet(0, i);
            return;
        }
    }
}
"""


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
CONTROL_ACCENT = [0.35, 0.86, 0.96, 1.0]
ACCENT_SOFT = mix(theme.surface, theme.accent, 0.22)
CONTROL_BG = [0.22, 0.22, 0.23, 1.0]
CONTROL_BORDER = [0.41, 0.41, 0.43, 1.0]
CONTROL_SURFACE = [0.66, 0.66, 0.68, 1.0]
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
CORE_W = 56
CORE_H = 156
GRAPH_X = 72
GRAPH_Y = 14
GRAPH_W = 602
GRAPH_H = 156
DETAIL_X = HIDDEN_X
DETAIL_Y = 148
DETAIL_WIDTH = 1
DETAIL_H = 1
EDITOR_X = HIDDEN_X
EDITOR_Y = 148
EDITOR_W = 1
EDITOR_H = 1
GLOBAL_X = 676
GLOBAL_Y = 14
GLOBAL_W = 60
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
BAND_NAV_FILENAME = "peq_band_nav_v1.js"

# ---------------------------------------------------------------------------
# UI — Background, hero frame, and top bar
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 760, 188], bgcolor=BG)
device.add_panel("hero_frame", [10, 8, 740, 172],
                 bgcolor=SURFACE, border=1,
                 bordercolor=CONTROL_BORDER, rounded=0)
device.add_panel("core_frame", [CORE_X, CORE_Y, CORE_W, CORE_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=0)
device.add_panel("graph_frame", [GRAPH_X - 2, GRAPH_Y - 2, GRAPH_W + 4, GRAPH_H + 4],
                 bgcolor=GRAPH_FRAME_BG, border=1,
                 bordercolor=GRAPH_BORDER, rounded=0)
device.add_panel("graph_plot_bg", [GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H],
                 bgcolor=GRAPH_BG, border=1,
                 bordercolor=GRAPH_BORDER, rounded=0)
device.add_panel("detail_frame", [DETAIL_X, DETAIL_Y, DETAIL_WIDTH, DETAIL_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=3)
device.add_panel("editor_frame", [EDITOR_X, EDITOR_Y, EDITOR_W, EDITOR_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=3)
device.add_panel("global_frame", [GLOBAL_X, GLOBAL_Y, GLOBAL_W, GLOBAL_H],
                 bgcolor=SURFACE_ALT, border=1,
                 bordercolor=RAIL_BORDER, rounded=0)
device.add_panel("bands_bg", [14, CARD_Y - 2, 544, CARD_H + 4],
                 bgcolor=SURFACE, border=1,
                 bordercolor=RAIL_BORDER, rounded=3)
device.add_comment("core_title", [HIDDEN_X, 148, 1, 1], "BAND",
                   textcolor=TEXT_DIM, fontsize=7.2, fontname=theme.fontname_bold, justification=1)
device.add_comment("detail_title", [DETAIL_X + 10, DETAIL_Y + 8, 94, 12], "SELECTED BAND",
                   textcolor=TEXT_DIM, fontsize=7.6, fontname=theme.fontname_bold)
device.add_tab("focus_tab", "Focus Band", [900, 148, 1, 1],
               options=[f"B{i + 1}" for i in range(NUM_BANDS)],
               bgcolor=CONTROL_BG, bgoncolor=ACCENT,
               textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
               rounded=4, spacing_x=1.0, fontsize=8.0)
device.add_comment("mod_title", [HIDDEN_X, 148, 1, 1], "BAND MOD",
                   textcolor=TEXT_DIM, fontsize=7.6, fontname=theme.fontname_bold)
device.add_comment("global_title", [HIDDEN_X, 148, 1, 1], "VIEW",
                   textcolor=TEXT_DIM, fontsize=7.6, fontname=theme.fontname_bold)
device.add_comment("global_analyzer_title", [GLOBAL_X + 3, GLOBAL_Y + 20, GLOBAL_W - 6, 8], "ANALYZE",
                   textcolor=TEXT_DIM, fontsize=5.0, justification=1)
device.add_comment("global_range_title", [GLOBAL_X + 3, GLOBAL_Y + 47, GLOBAL_W - 6, 8], "SCALE",
                   textcolor=TEXT_DIM, fontsize=5.0, justification=1)
device.add_tab("analyzer_mode_tab", "Analyzer Mode", [GLOBAL_X + 3, GLOBAL_Y + 26, GLOBAL_W - 6, 15],
               options=["OFF", "PRE", "POST"],
               bgcolor=CONTROL_BG, bgoncolor=CONTROL_ACCENT,
               textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
               rounded=2, spacing_x=0.6, fontsize=5.9)
device.add_tab("range_tab", "Display Range", [GLOBAL_X + 3, GLOBAL_Y + 53, GLOBAL_W - 6, 15],
               options=["15", "18", "24", "30"],
               bgcolor=CONTROL_BG, bgoncolor=CONTROL_ACCENT,
               textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
               rounded=2, spacing_x=0.6, fontsize=5.9)
device.add_comment("global_bypass_title", [GLOBAL_X + 3, GLOBAL_Y + 73, GLOBAL_W - 6, 8], "ACTIVE",
                   textcolor=TEXT_DIM, fontsize=5.0, justification=1)

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
    "band_nav",
    [HIDDEN_X, 148, 1, 1],
    js_code=band_nav_js(),
    numinlets=1,
    numoutlets=1,
    outlettype=["int"],
    js_filename=BAND_NAV_FILENAME,
    bgcolor=alpha(BG, 0.0),
    border=0,
    background=0,
    patching_rect=[10, 260, 92, 154],
)

device.add_jsui(
    "selected_band_column",
    [HIDDEN_X, 148, 1, 1],
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

device.add_panel("selected_type_chip_bg", [CORE_X + 7, CORE_Y + 86, CORE_W - 14, 8],
                 bgcolor=CONTROL_BG, border=1,
                 bordercolor=CONTROL_BORDER, rounded=0)
device.add_comment("selected_type_label", [CORE_X + 6, CORE_Y + 87, CORE_W - 12, 7], "PK",
                   textcolor=TEXT_DIM, fontsize=5.2, fontname=theme.fontname_bold, justification=1)
device.add_panel("selected_band_chip_bg", [CORE_X + 11, CORE_Y + 95, CORE_W - 22, 8],
                 bgcolor=CONTROL_BG, border=1,
                 bordercolor=CONTROL_ACCENT, rounded=0)
device.add_comment("selected_band_label", [CORE_X + 7, CORE_Y + 95, CORE_W - 14, 8], "-",
                   textcolor=CONTROL_ACCENT, fontsize=5.6, fontname=theme.fontname_bold, justification=1)
device.add_comment("selected_band_status", [HIDDEN_X, 148, 1, 1], "Click a node",
                   textcolor=TEXT_DIM, fontsize=7.0, justification=1)
device.add_comment("selected_type_caption", [HIDDEN_X, 148, 1, 1], "TYPE",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_menu("selected_type", "Selected Type", [HIDDEN_X, 148, 1, 1],
                options=TYPE_OPTIONS, fontsize=8.2, parameter_enable=0,
                bgcolor=CONTROL_BG, bgoncolor=ACCENT,
                textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK)
device.add_dial("selected_freq", "Freq", [CORE_X + 4, CORE_Y + 10, CORE_W - 8, 22],
                min_val=10.0, max_val=22000.0, initial=BAND_DEFAULTS[0][0],
                unitstyle=3, parameter_exponent=3.0,
                appearance=1, activedialcolor=CONTROL_ACCENT, showname=1, shownumber=1,
                fontsize=6.5,
                parameter_enable=0)
device.add_dial("selected_gain", "Gain", [CORE_X + 4, CORE_Y + 33, CORE_W - 8, 22],
                min_val=-30.0, max_val=30.0, initial=0.0,
                unitstyle=4, appearance=1, activedialcolor=CONTROL_ACCENT,
                showname=1, shownumber=1, fontsize=6.5, parameter_enable=0)
device.add_dial("selected_q", "Q", [CORE_X + 4, CORE_Y + 56, CORE_W - 8, 22],
                min_val=0.1, max_val=30.0, initial=1.0,
                unitstyle=1, appearance=1, activedialcolor=CONTROL_ACCENT,
                showname=1, shownumber=1, fontsize=6.5, parameter_enable=0)
device.add_comment("selected_hint", [HIDDEN_X, 148, 1, 1],
                   "Right-click node for menu.",
                   textcolor=TEXT_DIM, fontsize=6.0, justification=1)
device.add_comment("selected_dynamic_amt_caption", [DETAIL_X + 84, DETAIL_Y + 114, 50, 8], "DYN AMT",
                   textcolor=TEXT_DIM, fontsize=6.4)
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
device.add_comment("lbl_out", [HIDDEN_X, 148, 1, 1], "OUTPUT",
                   textcolor=TEXT_DIM, fontsize=6.4)
device.add_number_box("out_gain", "Out Gain", [HIDDEN_X, 148, 1, 1],
                      min_val=-24.0, max_val=24.0, initial=0.0,
                      unitstyle=4, fontsize=8.0)
device.add_live_text("bypass_toggle", "Bypass", [GLOBAL_X + 3, GLOBAL_Y + 79, GLOBAL_W - 6, 15],
                     text_on="OFF", text_off="ON",
                     bgcolor=CONTROL_BG, bgoncolor=BYPASS_COLOR,
                     textcolor=TEXT_DIM, textoncolor=TEXT_ON_DARK,
                     rounded=2, fontsize=5.9, shortname="Bypass")
device.add_comment("lbl_meters", [HIDDEN_X, 148, 1, 1], "LR",
                   textcolor=TEXT_DIM, fontsize=6.0, justification=1)
device.add_meter("meter_l", [HIDDEN_X, 148, 1, 1],
                 patching_rect=[1600, 0, 8, 80])
device.add_meter("meter_r", [HIDDEN_X, 148, 1, 1],
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
device.add_line("msg_num_bands", 0, "band_nav", 0)
device.add_line("msg_num_bands", 0, "selected_band_column", 0)
device.add_line("dspstate_eq", 1, "eq_display", 1)

# Focus band defaults + syncing between graph and focus tab
add_selected_band_focus_shell(
    device,
    loadbang_id="lb_init",
    focus_control_id="focus_tab",
    graph_source_id="eq_display",
    nav_source_id="band_nav",
    focus_target_ids=["eq_display", "band_nav", "selected_band_column"],
    default_band=0,
    patch_x=10,
    patch_y=250,
)

# Visible selected-band label follows the active graph/node selection.
device.add_newobj(
    "selected_band_name_sel", "select -1 0 1 2 3 4 5 6 7",
    numinlets=1, numoutlets=10,
    outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang", "bang", "bang", ""],
    patching_rect=[10, 276, 220, 20],
)
device.add_newobj(
    "prepend_selected_band_label", "prepend set",
    numinlets=1, numoutlets=1,
    outlettype=[""],
    patching_rect=[236, 276, 80, 20],
)
for idx, label in enumerate(["-", "1", "2", "3", "4", "5", "6", "7", "8"]):
    device.add_box({
        "box": {
            "id": f"msg_selected_band_label_{idx}",
            "maxclass": "message",
            "text": label,
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [10 + idx * 36, 302, 44, 20],
        }
    })
    device.add_line("selected_band_name_sel", idx, f"msg_selected_band_label_{idx}", 0)
    device.add_line(f"msg_selected_band_label_{idx}", 0, "prepend_selected_band_label", 0)
device.add_line("selected_band_store", 0, "selected_band_name_sel", 0)
device.add_line("prepend_selected_band_label", 0, "selected_band_label", 0)

device.add_newobj(
    "selected_type_name_route", "route selected_type",
    numinlets=1, numoutlets=2,
    outlettype=["", ""],
    patching_rect=[324, 276, 108, 20],
)
device.add_newobj(
    "selected_type_name_sel", "select 0 1 2 3 4 5 6 7",
    numinlets=1, numoutlets=9,
    outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang", "bang", ""],
    patching_rect=[438, 276, 196, 20],
)
device.add_newobj(
    "prepend_selected_type_label", "prepend set",
    numinlets=1, numoutlets=1,
    outlettype=[""],
    patching_rect=[640, 276, 80, 20],
)
device.add_newobj(
    "selected_type_clear_sel", "select -1",
    numinlets=1, numoutlets=2,
    outlettype=["bang", ""],
    patching_rect=[726, 276, 54, 20],
)
device.add_newobj(
    "selected_type_clear_delay", "del 1",
    numinlets=2, numoutlets=1,
    outlettype=["bang"],
    patching_rect=[786, 276, 40, 20],
)
device.add_box({
    "box": {
        "id": "msg_selected_type_label_clear",
        "maxclass": "message",
        "text": "-",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [832, 276, 30, 20],
    }
})
for idx, label in enumerate(["PK", "LS", "HS", "LP", "HP", "NT", "BP", "AP"]):
    device.add_box({
        "box": {
            "id": f"msg_selected_type_label_{idx}",
            "maxclass": "message",
            "text": label,
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [324 + idx * 36, 302, 34, 20],
        }
    })
    device.add_line("selected_type_name_sel", idx, f"msg_selected_type_label_{idx}", 0)
    device.add_line(f"msg_selected_type_label_{idx}", 0, "prepend_selected_type_label", 0)
device.add_line("selected_band_column", 0, "selected_type_name_route", 0)
device.add_line("selected_type_name_route", 0, "selected_type_name_sel", 0)
device.add_line("selected_band_store", 0, "selected_type_clear_sel", 0)
device.add_line("selected_type_clear_sel", 0, "selected_type_clear_delay", 0)
device.add_line("selected_type_clear_delay", 0, "msg_selected_type_label_clear", 0)
device.add_line("msg_selected_type_label_clear", 0, "prepend_selected_type_label", 0)
device.add_line("prepend_selected_type_label", 0, "selected_type_label", 0)

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
    device.add_line(f"prepend_b{i}", 0, "band_nav", 0)
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
    parametric_eq_band_backend(
        device,
        i,
        loadbang_id="lb_init",
        default_freq=default_freq,
        default_type_name=FILTERCOEFF_TYPES[default_type],
        filter_types=FILTERCOEFF_TYPES,
        default_motion_rate=MOTION_RATE_DEFAULTS[i],
    )

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
# DSP — graph and selected-band editor routing shells
# ---------------------------------------------------------------------------
add_band_message_routers(
    device,
    num_bands=NUM_BANDS,
    route_specs=[
        {
            "name": "freq",
            "message": "band_freq",
            "sources": [("eq_display", 1), ("selected_band_column", 0)],
            "targets": [{"prefix": "freq_b"}, {"prefix": "pak_b", "inlet": 1}],
            "patch_x": 10,
            "patch_y": 780,
            "route_width": 100,
        },
        {
            "name": "gain",
            "message": "band_gain",
            "sources": [("eq_display", 2), ("selected_band_column", 0)],
            "targets": [{"prefix": "gain_b"}, {"prefix": "pak_b", "inlet": 2}],
            "patch_x": 220,
            "patch_y": 780,
            "route_width": 100,
        },
        {
            "name": "q",
            "message": "band_q",
            "sources": [("eq_display", 3), ("selected_band_column", 0)],
            "targets": [{"prefix": "q_b"}, {"prefix": "pak_b", "inlet": 3}],
            "patch_x": 430,
            "patch_y": 780,
            "route_width": 80,
        },
        {
            "name": "type",
            "message": "band_type",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "type_b"}, {"prefix": "pak_b", "inlet": 4}],
            "patch_x": 640,
            "patch_y": 780,
            "route_width": 90,
        },
        {
            "name": "enable",
            "message": "band_enable",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "on_b"}, {"prefix": "pak_b", "inlet": 5}],
            "patch_x": 850,
            "patch_y": 780,
            "route_width": 104,
        },
        {
            "name": "motion",
            "message": "band_motion",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "motion_b"}, {"prefix": "pak_b", "inlet": 6}],
            "patch_x": 1060,
            "patch_y": 780,
            "route_width": 104,
        },
        {
            "name": "dynamic",
            "message": "band_dynamic",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "dynamic_b"}, {"prefix": "pak_b", "inlet": 7}],
            "patch_x": 1270,
            "patch_y": 780,
            "route_width": 114,
        },
        {
            "name": "dynamic_amount",
            "message": "band_dynamic_amount",
            "sources": [("eq_display", 0)],
            "targets": [{"prefix": "dynamic_amt_b"}, {"prefix": "pak_b", "inlet": 8}],
            "patch_x": 1490,
            "patch_y": 780,
            "route_width": 144,
        },
        {
            "name": "motion_rate",
            "message": "band_motion_rate",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "motion_rate_b"}, {"prefix": "pak_b", "inlet": 9}],
            "patch_x": 1710,
            "patch_y": 780,
            "route_width": 132,
        },
        {
            "name": "motion_depth",
            "message": "band_motion_depth",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "motion_depth_b"}, {"prefix": "pak_b", "inlet": 10}],
            "patch_x": 1930,
            "patch_y": 780,
            "route_width": 140,
        },
        {
            "name": "motion_direction",
            "message": "band_motion_direction",
            "sources": [("eq_display", 0), ("selected_band_column", 0)],
            "targets": [{"prefix": "motion_direction_b"}, {"prefix": "pak_b", "inlet": 11}],
            "patch_x": 2140,
            "patch_y": 780,
            "route_width": 140,
        },
    ],
)

# ---------------------------------------------------------------------------
# Selected-band proxy UI sync and routing
# ---------------------------------------------------------------------------
add_selected_band_proxy_shell(
    device,
    num_bands=NUM_BANDS,
    source_id="selected_band_column",
    selected_band_store_id="selected_band_store",
    route_fields=[
        {"route_name": "selected_status", "prepend_id": "set_selected_status", "target_id": "selected_band_status", "patch_x": 2460},
        {"route_name": "selected_freq", "prepend_id": "set_selected_freq", "target_id": "selected_freq", "patch_x": 2540},
        {"route_name": "selected_gain", "prepend_id": "set_selected_gain", "target_id": "selected_gain", "patch_x": 2620},
        {"route_name": "selected_q", "prepend_id": "set_selected_q", "target_id": "selected_q", "patch_x": 2700},
        {"route_name": "selected_type", "prepend_id": "set_selected_type", "target_id": "selected_type", "patch_x": 2780},
        {"route_name": "selected_enable", "prepend_id": "set_selected_enable", "target_id": "selected_enable", "patch_x": 2860},
        {"route_name": "selected_motion", "prepend_id": "set_selected_motion", "target_id": "selected_motion", "patch_x": 2940},
        {"route_name": "selected_dynamic", "prepend_id": "set_selected_dynamic", "target_id": "selected_dynamic", "patch_x": 3020},
        {"route_name": "selected_dynamic_amount", "prepend_id": "set_selected_dynamic_amt", "target_id": "selected_dynamic_amt", "patch_x": 3100},
        {"route_name": "selected_motion_rate", "prepend_id": "set_selected_motion_rate", "target_id": "selected_motion_rate", "patch_x": 3180},
        {"route_name": "selected_motion_depth", "prepend_id": "set_selected_motion_depth", "target_id": "selected_motion_depth", "patch_x": 3260},
        {"route_name": "selected_motion_direction", "prepend_id": "set_selected_motion_direction", "target_id": "selected_motion_direction", "patch_x": 3340},
    ],
    control_routes=[
        {"control_id": "selected_freq", "pack_text": "pack f i", "target_prefix": "freq_b", "patch_y": 832},
        {"control_id": "selected_gain", "pack_text": "pack f i", "target_prefix": "gain_b", "patch_y": 858},
        {"control_id": "selected_q", "pack_text": "pack f i", "target_prefix": "q_b", "patch_y": 884},
        {"control_id": "selected_type", "pack_text": "pack i i", "target_prefix": "type_b", "patch_y": 910},
        {"control_id": "selected_enable", "pack_text": "pack i i", "target_prefix": "on_b", "patch_y": 936},
        {"control_id": "selected_motion", "pack_text": "pack i i", "target_prefix": "motion_b", "patch_y": 962},
        {"control_id": "selected_dynamic", "pack_text": "pack i i", "target_prefix": "dynamic_b", "patch_y": 988},
        {"control_id": "selected_dynamic_amt", "pack_text": "pack f i", "target_prefix": "dynamic_amt_b", "patch_y": 1014},
        {"control_id": "selected_motion_rate", "pack_text": "pack f i", "target_prefix": "motion_rate_b", "patch_y": 1040},
        {"control_id": "selected_motion_depth", "pack_text": "pack f i", "target_prefix": "motion_depth_b", "patch_y": 1066},
        {"control_id": "selected_motion_direction", "pack_text": "pack f i", "target_prefix": "motion_direction_b", "patch_y": 1092},
    ],
)

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
