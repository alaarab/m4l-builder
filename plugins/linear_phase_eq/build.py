"""Linear Phase EQ - mastering-style linear-phase EQ with a dedicated UI.

This is a separate product from Parametric EQ and Linear Phase Crossover:
  - Parametric EQ: fast mix EQ
  - Linear Phase Crossover: clean split-band routing
  - Linear Phase EQ: slower, precision linear-phase processing

Design notes:
  - Uses three fixed FFT quality tiers (Short / Medium / High)
  - A local JS state engine computes magnitude-response tables into buffer~
  - Three pfft~ kernels share the same control state and switch by quality mode
  - The hero graph, selected-band strip, and chip row all stay synchronized
"""

import json
import sys
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m4l_builder import AudioEffect, MIDNIGHT, device_output_path, newobj, patchline
from m4l_builder.engines import linear_phase_eq_display_js
from m4l_builder.engines.spectrum_analyzer import spectrum_analyzer_dsp


NUM_BANDS = 8
TYPE_OPTIONS = ["Peak", "LShelf", "HShelf", "LCut", "HCut", "Notch", "BPass"]
QUALITY_OPTIONS = ["S", "M", "H"]
ANALYZER_OPTIONS = ["OFF", "IN", "OUT"]
RANGE_OPTIONS = ["3", "6", "12", "30"]
SLOPE_OPTIONS = ["12", "24", "48"]
COLLISION_OPTIONS = ["OFF", "ON"]

QUALITY_MODES = [
    ("short", "Short", 2048),
    ("medium", "Medium", 4096),
    ("high", "High", 8192),
]

RESPONSE_BUFFERS = {
    "short": "lpeq_resp_short",
    "medium": "lpeq_resp_medium",
    "high": "lpeq_resp_high",
}

KERNEL_FILENAMES = {
    "short": "linear_phase_eq_short_core.maxpat",
    "medium": "linear_phase_eq_medium_core.maxpat",
    "high": "linear_phase_eq_high_core.maxpat",
}

STATE_FILENAME = "linear_phase_eq_state.js"
CHIPROW_FILENAME = "linear_phase_eq_chips.js"
DISPLAY_FILENAME = "lpeq_display_v2.js"

BG = [0.05, 0.06, 0.08, 1.0]
SURFACE = [0.08, 0.10, 0.13, 1.0]
SURFACE_ALT = [0.10, 0.12, 0.16, 1.0]
SURFACE_RAISED = [0.11, 0.14, 0.18, 1.0]
BORDER = [0.17, 0.20, 0.25, 1.0]
TEXT = [0.94, 0.96, 1.0, 1.0]
TEXT_DIM = [0.56, 0.62, 0.70, 1.0]
TEXT_SOFT = [0.42, 0.48, 0.56, 1.0]
ANALYZER = [0.24, 0.84, 0.98, 1.0]
CURVE = [0.95, 0.97, 1.0, 1.0]
ACCENT_SOFT = [0.15, 0.18, 0.22, 1.0]

BAND_COLORS = [
    [0.92, 0.36, 0.34, 1.0],
    [0.94, 0.62, 0.24, 1.0],
    [0.88, 0.84, 0.28, 1.0],
    [0.36, 0.80, 0.46, 1.0],
    [0.26, 0.84, 0.92, 1.0],
    [0.38, 0.56, 0.92, 1.0],
    [0.66, 0.46, 0.88, 1.0],
    [0.90, 0.42, 0.66, 1.0],
]


def _support_patcher(boxes, lines, width=1280.0, height=900.0):
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


def build_linear_phase_kernel(buffer_name: str) -> str:
    """Build a stereo FFT kernel that multiplies bins by a response buffer."""
    boxes = []
    lines = []

    def add(box):
        boxes.append(box)

    def wire(src_id, src_outlet, dest_id, dest_inlet):
        lines.append(patchline(src_id, src_outlet, dest_id, dest_inlet))

    channel_specs = [
        ("l", 1, 40.0),
        ("r", 2, 280.0),
    ]

    for channel, fft_index, base_x in channel_specs:
        add(newobj(f"fft_{channel}", f"fftin~ {fft_index}", numinlets=1, numoutlets=3,
                   outlettype=["signal", "signal", "signal"],
                   patching_rect=[base_x, 40.0, 60.0, 20.0]))
        add(newobj(f"lookup_{channel}", f"index~ {buffer_name}", numinlets=2, numoutlets=1,
                   outlettype=["signal"],
                   patching_rect=[base_x + 86.0, 70.0, 110.0, 20.0]))
        add(newobj(f"real_mul_{channel}", "*~", numinlets=2, numoutlets=1,
                   outlettype=["signal"],
                   patching_rect=[base_x, 108.0, 36.0, 20.0]))
        add(newobj(f"imag_mul_{channel}", "*~", numinlets=2, numoutlets=1,
                   outlettype=["signal"],
                   patching_rect=[base_x + 48.0, 108.0, 36.0, 20.0]))
        add(newobj(f"out_{channel}", f"fftout~ {fft_index}", numinlets=2, numoutlets=0,
                   patching_rect=[base_x, 144.0, 62.0, 20.0]))

        wire(f"fft_{channel}", 2, f"lookup_{channel}", 0)
        wire(f"fft_{channel}", 0, f"real_mul_{channel}", 0)
        wire(f"fft_{channel}", 1, f"imag_mul_{channel}", 0)
        wire(f"lookup_{channel}", 0, f"real_mul_{channel}", 1)
        wire(f"lookup_{channel}", 0, f"imag_mul_{channel}", 1)
        wire(f"real_mul_{channel}", 0, f"out_{channel}", 0)
        wire(f"imag_mul_{channel}", 0, f"out_{channel}", 1)

    return json.dumps(_support_patcher(boxes, lines), indent=2)


def band_chip_row_js() -> str:
    """Return jsui code for the band chip row."""
    return """\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

var num_bands = 8;
var selected = -1;
var enabled = [0, 0, 0, 0, 0, 0, 0, 0];
var solo = [0, 0, 0, 0, 0, 0, 0, 0];
var colors = [
    [0.92, 0.36, 0.34, 1.0],
    [0.94, 0.62, 0.24, 1.0],
    [0.88, 0.84, 0.28, 1.0],
    [0.36, 0.80, 0.46, 1.0],
    [0.26, 0.84, 0.92, 1.0],
    [0.38, 0.56, 0.92, 1.0],
    [0.66, 0.46, 0.88, 1.0],
    [0.90, 0.42, 0.66, 1.0]
];

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function chip_layout() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    var compact = h <= 24 ? 1 : 0;
    var gap = compact ? 2 : 6;
    var inset_y = compact ? 3 : 5;
    var chip_h = compact ? h - 6 : h - 10;
    var chip_w = Math.floor((w - gap * (num_bands + 1)) / num_bands);
    var rects = [];
    var x = gap;
    var i;
    for (i = 0; i < num_bands; i++) {
        rects.push([x, inset_y, chip_w, chip_h]);
        x += chip_w + gap;
    }
    return rects;
}

function set_num_bands(v) {
    num_bands = clamp(Math.floor(v), 1, 8);
    mgraphics.redraw();
}

function set_band_state(idx, is_enabled, is_solo) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= 8) return;
    enabled[idx] = is_enabled ? 1 : 0;
    solo[idx] = is_solo ? 1 : 0;
    mgraphics.redraw();
}

function set_selected(idx) {
    idx = Math.floor(idx);
    selected = idx;
    mgraphics.redraw();
}

function paint() {
    var rects = chip_layout();
    var compact = mgraphics.size[1] <= 24 ? 1 : 0;
    var i, r, fill_alpha, border_alpha, color, label, label_x;

    mgraphics.set_source_rgba(0.06, 0.08, 0.11, 1.0);
    mgraphics.rectangle_rounded(0, 0, mgraphics.size[0], mgraphics.size[1], 6, 6);
    mgraphics.fill();

    for (i = 0; i < num_bands; i++) {
        r = rects[i];
        color = colors[i];
        fill_alpha = selected === i ? 0.94 : (enabled[i] ? 0.24 : 0.04);
        border_alpha = enabled[i] ? 0.92 : 0.14;

        mgraphics.set_source_rgba(color[0], color[1], color[2], fill_alpha);
        mgraphics.rectangle_rounded(r[0], r[1], r[2], r[3], 5, 5);
        mgraphics.fill_preserve();

        mgraphics.set_source_rgba(color[0], color[1], color[2], border_alpha);
        mgraphics.set_line_width(selected === i ? 2.0 : 1.1);
        mgraphics.stroke();

        mgraphics.select_font_face("Ableton Sans Bold");
        mgraphics.set_font_size(compact ? 7.0 : 8.5);
        mgraphics.set_source_rgba(
            selected === i ? 0.05 : 0.92,
            selected === i ? 0.06 : 0.95,
            selected === i ? 0.08 : 1.0,
            selected === i ? 0.96 : (enabled[i] ? 0.78 : 0.28)
        );
        label = compact ? (i + 1).toString() : "B" + (i + 1);
        label_x = compact ? (r[0] + r[2] * 0.5 - (label.length > 1 ? 4 : 2)) : (r[0] + 13);
        mgraphics.move_to(label_x, r[1] + (compact ? 12 : 16));
        mgraphics.show_text(label);

        if (solo[i]) {
            mgraphics.set_source_rgba(1.0, 0.96, 0.74, 0.96);
            mgraphics.rectangle_rounded(
                r[0] + r[2] - (compact ? 16 : 18),
                r[1] + (compact ? 3 : 5),
                compact ? 10 : 12,
                compact ? 5 : 6,
                3,
                3
            );
            mgraphics.fill();
        }
    }
}

function onclick(x, y, but, cmd, shift, caps, opt, ctrl) {
    var rects = chip_layout();
    var i, r;
    for (i = 0; i < num_bands; i++) {
        r = rects[i];
        if (x >= r[0] && x <= (r[0] + r[2]) && y >= r[1] && y <= (r[1] + r[3])) {
            outlet(0, "select_band", i);
            return;
        }
    }
}
"""


def linear_phase_state_js(buffer_names, fft_sizes) -> str:
    """Return regular-js code for state coordination and response buffers."""
    return Template("""\
inlets = 1;
outlets = 3;

var RESPONSE_BUFFERS = $buffer_names;
var FFT_SIZES = $fft_sizes;
var TYPE_NAMES = ["Peak", "LShelf", "HShelf", "LCut", "HCut", "Notch", "BPass"];
var DEFAULT_FREQS = [80.0, 320.0, 1800.0, 9000.0, 160.0, 640.0, 3600.0, 14000.0];
var TYPE_PEAK = 0;
var TYPE_LOSHELF = 1;
var TYPE_HISHELF = 2;
var TYPE_LOWCUT = 3;
var TYPE_HIGHCUT = 4;
var TYPE_NOTCH = 5;
var TYPE_BANDPASS = 6;
var NUM_BANDS = 8;
var MIN_FREQ = 10.0;
var MAX_FREQ = 22050.0;
var MIN_GAIN = -30.0;
var MAX_GAIN = 30.0;
var MIN_Q = 0.1;
var MAX_Q = 30.0;
var sample_rate = 48000.0;
var quality_mode = 1;
var response_tables_dirty = 0;
var response_buffer_handles = [];
var selected_band = -1;
var bands = [];
var i;

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function safe_log10(v) {
    if (v <= 1.0e-20) v = 1.0e-20;
    return Math.log(v) / Math.LN10;
}

function band_uses_gain(type) {
    return type === TYPE_PEAK || type === TYPE_LOSHELF || type === TYPE_HISHELF;
}

function any_solo_enabled() {
    for (i = 0; i < NUM_BANDS; i++) {
        if (bands[i].enabled && bands[i].solo) return 1;
    }
    return 0;
}

function slope_stage_count(slope) {
    if (slope === 2) return 4;
    if (slope === 1) return 2;
    return 1;
}

function reset_bands() {
    bands = [];
    for (i = 0; i < NUM_BANDS; i++) {
        bands[i] = {
            freq: DEFAULT_FREQS[i],
            gain: 0.0,
            q: 1.0,
            type: TYPE_PEAK,
            enabled: i < 4 ? 1 : 0,
            slope: 0,
            solo: 0
        };
    }
    selected_band = 2;
}

function clone_band(idx) {
    return {
        freq: bands[idx].freq,
        gain: bands[idx].gain,
        q: bands[idx].q,
        type: bands[idx].type,
        enabled: bands[idx].enabled,
        slope: bands[idx].slope,
        solo: bands[idx].solo
    };
}

function find_free_band() {
    for (i = 0; i < NUM_BANDS; i++) {
        if (!bands[i].enabled) return i;
    }
    return -1;
}

function next_enabled_band(preferred_idx) {
    var idx;
    if (preferred_idx >= 0 && preferred_idx < NUM_BANDS && bands[preferred_idx].enabled) {
        return preferred_idx;
    }
    for (idx = 0; idx < NUM_BANDS; idx++) {
        if (bands[idx].enabled) return idx;
    }
    return -1;
}

function coeffs_for_band(band) {
    var sr = clamp(sample_rate, 22050.0, 384000.0);
    var fc = clamp(band.freq, 5.0, Math.min(MAX_FREQ, sr * 0.49));
    var q = clamp(band.q, MIN_Q, MAX_Q);
    var gain = clamp(band.gain, MIN_GAIN, MAX_GAIN);
    var w0 = 2.0 * Math.PI * fc / sr;
    var cosw0 = Math.cos(w0);
    var sinw0 = Math.sin(w0);
    var alpha = sinw0 / (2.0 * q);
    var A = Math.pow(10.0, gain / 40.0);
    var shelf_s = clamp(q, 0.1, 4.0);
    var shelf_alpha = sinw0 * 0.5 * Math.sqrt((A + 1.0 / A) * (1.0 / shelf_s - 1.0) + 2.0);
    var two_sqrt_A_alpha = 2.0 * Math.sqrt(A) * shelf_alpha;
    var b0, b1, b2, a0, a1, a2;

    switch (band.type) {
        case TYPE_PEAK:
            b0 = 1.0 + alpha * A;
            b1 = -2.0 * cosw0;
            b2 = 1.0 - alpha * A;
            a0 = 1.0 + alpha / A;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha / A;
            break;
        case TYPE_LOSHELF:
            b0 = A * ((A + 1.0) - (A - 1.0) * cosw0 + two_sqrt_A_alpha);
            b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosw0);
            b2 = A * ((A + 1.0) - (A - 1.0) * cosw0 - two_sqrt_A_alpha);
            a0 = (A + 1.0) + (A - 1.0) * cosw0 + two_sqrt_A_alpha;
            a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosw0);
            a2 = (A + 1.0) + (A - 1.0) * cosw0 - two_sqrt_A_alpha;
            break;
        case TYPE_HISHELF:
            b0 = A * ((A + 1.0) + (A - 1.0) * cosw0 + two_sqrt_A_alpha);
            b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw0);
            b2 = A * ((A + 1.0) + (A - 1.0) * cosw0 - two_sqrt_A_alpha);
            a0 = (A + 1.0) - (A - 1.0) * cosw0 + two_sqrt_A_alpha;
            a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw0);
            a2 = (A + 1.0) - (A - 1.0) * cosw0 - two_sqrt_A_alpha;
            break;
        case TYPE_LOWCUT:
            b0 = (1.0 + cosw0) * 0.5;
            b1 = -(1.0 + cosw0);
            b2 = (1.0 + cosw0) * 0.5;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;
        case TYPE_HIGHCUT:
            b0 = (1.0 - cosw0) * 0.5;
            b1 = 1.0 - cosw0;
            b2 = (1.0 - cosw0) * 0.5;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;
        case TYPE_NOTCH:
            b0 = 1.0;
            b1 = -2.0 * cosw0;
            b2 = 1.0;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;
        case TYPE_BANDPASS:
            b0 = alpha;
            b1 = 0.0;
            b2 = -alpha;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;
        default:
            return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0];
    }

    if (Math.abs(a0) < 1.0e-12) return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0];
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

function response_db(coeffs, eval_freq) {
    var sr = clamp(sample_rate, 22050.0, 384000.0);
    var freq = clamp(eval_freq, 0.0001, sr * 0.49);
    var w = 2.0 * Math.PI * freq / sr;
    var c1 = Math.cos(w);
    var s1 = Math.sin(w);
    var c2 = Math.cos(2.0 * w);
    var s2 = Math.sin(2.0 * w);
    var b0 = coeffs[0];
    var b1 = coeffs[1];
    var b2 = coeffs[2];
    var a0 = coeffs[3];
    var a1 = coeffs[4];
    var a2 = coeffs[5];
    var nr = b0 + b1 * c1 + b2 * c2;
    var ni = -b1 * s1 - b2 * s2;
    var dr = a0 + a1 * c1 + a2 * c2;
    var di = -a1 * s1 - a2 * s2;
    var num = nr * nr + ni * ni;
    var den = dr * dr + di * di;
    return 10.0 * safe_log10(num / Math.max(den, 1.0e-20));
}

function band_db_at(band, coeffs, eval_freq) {
    var db;
    if (!band.enabled) return 0.0;
    db = response_db(coeffs, eval_freq);
    if (band.type === TYPE_LOWCUT || band.type === TYPE_HIGHCUT) {
        db = db * slope_stage_count(band.slope);
    }
    return db;
}

function octave_distance(eval_freq, center_freq) {
    var safe_eval = clamp(eval_freq, 0.0001, MAX_FREQ);
    var safe_center = clamp(center_freq, MIN_FREQ, MAX_FREQ);
    return Math.abs(Math.log(safe_eval / safe_center) / Math.LN2);
}

function audition_mask_db_at(band, coeffs, eval_freq) {
    var focus = 0.0;
    var q = clamp(band.q, MIN_Q, MAX_Q);
    var oct = octave_distance(eval_freq, band.freq);
    var width;
    var ratio;
    var emphasis;

    if (!band.enabled || !band.solo) return -42.0;

    switch (band.type) {
        case TYPE_PEAK:
        case TYPE_NOTCH:
        case TYPE_BANDPASS:
            width = clamp(1.7 / Math.sqrt(q), 0.18, 2.6);
            focus = Math.exp(-Math.pow(oct / width, 2.0));
            break;
        case TYPE_LOSHELF:
            ratio = clamp(eval_freq / Math.max(band.freq, 20.0), 0.0001, 1000.0);
            focus = 1.0 / (1.0 + Math.pow(ratio, 3.0));
            break;
        case TYPE_HISHELF:
            ratio = clamp(Math.max(band.freq, 20.0) / Math.max(eval_freq, 0.0001), 0.0001, 1000.0);
            focus = 1.0 / (1.0 + Math.pow(ratio, 3.0));
            break;
        case TYPE_LOWCUT:
            ratio = clamp(eval_freq / Math.max(band.freq, 20.0), 0.0001, 1000.0);
            focus = 1.0 / (1.0 + Math.pow(ratio, 4.0));
            break;
        case TYPE_HIGHCUT:
            ratio = clamp(Math.max(band.freq, 20.0) / Math.max(eval_freq, 0.0001), 0.0001, 1000.0);
            focus = 1.0 / (1.0 + Math.pow(ratio, 4.0));
            break;
        default:
            focus = 0.0;
    }

    emphasis = Math.min(10.0, Math.abs(band_db_at(band, coeffs, eval_freq)) * 0.45);
    return clamp(-42.0 + focus * 48.0 + emphasis, -42.0, 12.0);
}

function emit_graph_band(idx) {
    outlet(
        0,
        "set_band",
        idx,
        bands[idx].freq,
        bands[idx].gain,
        bands[idx].q,
        bands[idx].type,
        bands[idx].enabled,
        bands[idx].slope,
        bands[idx].solo
    );
}

function emit_graph_state() {
    outlet(0, "set_num_bands", NUM_BANDS);
    for (i = 0; i < NUM_BANDS; i++) {
        emit_graph_band(i);
    }
    outlet(0, "set_selected", selected_band);
    outlet(0, "set_quality_mode", quality_mode);
    outlet(0, "set_latency_ms", current_latency_ms());
}

function emit_chip_state(idx) {
    outlet(2, "set_band_state", idx, bands[idx].enabled, bands[idx].solo);
}

function emit_chip_row() {
    outlet(2, "set_num_bands", NUM_BANDS);
    for (i = 0; i < NUM_BANDS; i++) {
        emit_chip_state(i);
    }
    outlet(2, "set_selected", selected_band);
}

function emit_strip_state() {
    var band;
    if (selected_band < 0 || selected_band >= NUM_BANDS) {
        outlet(1, "band_label", "NO BAND");
        outlet(1, "band_status", "Click the graph to add a band.");
        outlet(1, "freq", 1000.0);
        outlet(1, "gain", 0.0);
        outlet(1, "q", 1.0);
        outlet(1, "type", 0);
        outlet(1, "slope", 0);
        outlet(1, "enable", 0);
        outlet(1, "solo", 0);
        outlet(1, "selected", -1);
        outlet(1, "latency_text", "LATENCY " + current_latency_ms().toFixed(1) + " ms");
        return;
    }

    band = clone_band(selected_band);
    outlet(1, "selected", selected_band);
    outlet(1, "band_label", "B" + (selected_band + 1) + " " + TYPE_NAMES[band.type].toUpperCase());
    outlet(1, "band_status", band.enabled ? (band.solo ? "Enabled | Listen isolates the marked band region" : "Enabled") : "Bypassed");
    outlet(1, "freq", band.freq);
    outlet(1, "gain", band.gain);
    outlet(1, "q", band.q);
    outlet(1, "type", band.type);
    outlet(1, "slope", band.slope);
    outlet(1, "enable", band.enabled);
    outlet(1, "solo", band.solo);
    outlet(1, "latency_text", "LATENCY " + current_latency_ms().toFixed(1) + " ms");
}

function current_latency_ms() {
    return (FFT_SIZES[quality_mode] * 0.5 / Math.max(sample_rate, 1.0)) * 1000.0;
}

function response_buffer_for(qIndex) {
    if (!response_buffer_handles[qIndex]) {
        response_buffer_handles[qIndex] = new Buffer(RESPONSE_BUFFERS[qIndex]);
    }
    return response_buffer_handles[qIndex];
}

function rebuild_response_table(qIndex, coeffs, activeBands, soloMode) {
    var frames, bin, freq, totalDb, linearValue, values, auditionDb, responseBuffer;
    frames = Math.floor(FFT_SIZES[qIndex] / 2) + 1;
    values = new Array(frames);
    responseBuffer = response_buffer_for(qIndex);
    responseBuffer.send("sizeinsamps", frames);
    for (bin = 0; bin < frames; bin++) {
        freq = (bin * sample_rate) / FFT_SIZES[qIndex];
        if (bin === 0) freq = 0.0001;
        if (soloMode) {
            auditionDb = -42.0;
            for (i = 0; i < NUM_BANDS; i++) {
                if (!activeBands[i].solo) continue;
                auditionDb = Math.max(
                    auditionDb,
                    audition_mask_db_at(activeBands[i], coeffs[i], freq)
                );
            }
            linearValue = Math.pow(10.0, auditionDb / 20.0);
        } else {
            totalDb = 0.0;
            for (i = 0; i < NUM_BANDS; i++) {
                totalDb += band_db_at(activeBands[i], coeffs[i], freq);
            }
            linearValue = Math.pow(10.0, totalDb / 20.0);
        }
        if (linearValue < 0.00001) linearValue = 0.00001;
        if (linearValue > 31.62278) linearValue = 31.62278;
        values[bin] = linearValue;
    }
    responseBuffer.poke(1, 0, values);
}

function rebuild_response_tables() {
    var qIndex;
    var coeffs = [];
    var soloMode = any_solo_enabled();
    for (i = 0; i < NUM_BANDS; i++) {
        coeffs[i] = coeffs_for_band(bands[i]);
    }

    for (qIndex = 0; qIndex < FFT_SIZES.length; qIndex++) {
        rebuild_response_table(qIndex, coeffs, bands, soloMode);
    }
    response_tables_dirty = 0;
}

function rebuild_active_response_table() {
    var coeffs = [];
    var soloMode = any_solo_enabled();
    for (i = 0; i < NUM_BANDS; i++) {
        coeffs[i] = coeffs_for_band(bands[i]);
    }
    rebuild_response_table(quality_mode, coeffs, bands, soloMode);
    response_tables_dirty = 1;
}

function sync_selection(idx) {
    if (idx < -1) idx = -1;
    if (idx >= NUM_BANDS) idx = NUM_BANDS - 1;
    selected_band = idx;
    outlet(0, "set_selected", selected_band);
    outlet(2, "set_selected", selected_band);
    emit_strip_state();
}

function commit_band(idx, rebuildBuffers, refreshChip) {
    if (refreshChip === undefined) refreshChip = 1;
    emit_graph_band(idx);
    if (refreshChip) emit_chip_state(idx);
    if (selected_band === idx) emit_strip_state();
    if (rebuildBuffers) rebuild_active_response_table();
}

function add_default_band() {
    var idx = find_free_band();
    if (idx < 0) return;
    bands[idx].freq = 1000.0;
    bands[idx].gain = 0.0;
    bands[idx].q = 1.0;
    bands[idx].type = TYPE_PEAK;
    bands[idx].enabled = 1;
    bands[idx].slope = 0;
    bands[idx].solo = 0;
    commit_band(idx, 1);
    sync_selection(idx);
}

function add_band_from_graph(idx, freq, gain, q, type, enabled, slope, solo) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].freq = clamp(freq, 20.0, 20000.0);
    bands[idx].gain = clamp(gain, MIN_GAIN, MAX_GAIN);
    bands[idx].q = clamp(q, MIN_Q, MAX_Q);
    bands[idx].type = Math.floor(type);
    bands[idx].enabled = enabled ? 1 : 0;
    bands[idx].slope = Math.floor(clamp(slope, 0, 2));
    bands[idx].solo = solo ? 1 : 0;
    commit_band(idx, 1);
    sync_selection(idx);
}

function delete_band(idx) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].enabled = 0;
    bands[idx].solo = 0;
    commit_band(idx, 1);
    if (selected_band === idx) sync_selection(next_enabled_band(idx + 1));
    else emit_strip_state();
}

function set_selected_band(idx) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= NUM_BANDS) idx = -1;
    sync_selection(idx);
}

function set_selected_param(name, value) {
    if (selected_band < 0 || selected_band >= NUM_BANDS) return;
    if (name === "freq") {
        bands[selected_band].freq = clamp(value, 20.0, 20000.0);
    } else if (name === "gain") {
        bands[selected_band].gain = clamp(value, MIN_GAIN, MAX_GAIN);
    } else if (name === "q") {
        bands[selected_band].q = clamp(value, MIN_Q, MAX_Q);
    } else if (name === "type") {
        bands[selected_band].type = Math.floor(clamp(value, 0, TYPE_BANDPASS));
    } else if (name === "slope") {
        bands[selected_band].slope = Math.floor(clamp(value, 0, 2));
    } else if (name === "enable") {
        bands[selected_band].enabled = value ? 1 : 0;
        if (!bands[selected_band].enabled) {
            bands[selected_band].solo = 0;
        }
    } else if (name === "solo") {
        bands[selected_band].solo = value ? 1 : 0;
    }

    commit_band(selected_band, 1);
}

function set_quality(idx) {
    if (response_tables_dirty) rebuild_response_tables();
    quality_mode = Math.floor(clamp(idx, 0, FFT_SIZES.length - 1));
    outlet(0, "set_quality_mode", quality_mode);
    outlet(0, "set_latency_ms", current_latency_ms());
    emit_strip_state();
}

function set_sample_rate(v) {
    sample_rate = clamp(v, 22050.0, 384000.0);
    outlet(0, "set_latency_ms", current_latency_ms());
    emit_strip_state();
    rebuild_response_tables();
}

function init() {
    reset_bands();
    rebuild_response_tables();
    emit_graph_state();
    emit_chip_row();
    emit_strip_state();
}

function loadbang() {
    init();
}

function anything() {
    var args = arrayfromargs(arguments);

    switch (messagename) {
        case "init":
            init();
            return;
        case "set_sample_rate":
            if (args.length > 0) set_sample_rate(args[0]);
            return;
        case "set_quality":
            if (args.length > 0) set_quality(args[0]);
            return;
        case "select_band":
            if (args.length > 0) set_selected_band(args[0]);
            return;
        case "add_band":
            if (args.length >= 8) {
                add_band_from_graph(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7]);
            } else {
                add_default_band();
            }
            return;
        case "delete_band":
            if (args.length > 0) delete_band(args[0]);
            return;
        case "band_freq":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("freq", args[1]);
            }
            return;
        case "band_gain":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("gain", args[1]);
            }
            return;
        case "band_q":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("q", args[1]);
            }
            return;
        case "band_drag_gain":
            if (args.length >= 3) {
                if (selected_band !== Math.floor(args[0])) set_selected_band(args[0]);
                bands[selected_band].freq = clamp(args[1], 20.0, 20000.0);
                bands[selected_band].gain = clamp(args[2], MIN_GAIN, MAX_GAIN);
                commit_band(selected_band, 1, 0);
            }
            return;
        case "band_drag_q":
            if (args.length >= 3) {
                if (selected_band !== Math.floor(args[0])) set_selected_band(args[0]);
                bands[selected_band].freq = clamp(args[1], 20.0, 20000.0);
                bands[selected_band].q = clamp(args[2], MIN_Q, MAX_Q);
                commit_band(selected_band, 1, 0);
            }
            return;
        case "context_type":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("type", args[1]);
            }
            return;
        case "context_slope":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("slope", args[1]);
            }
            return;
        case "context_enable":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("enable", args[1]);
            }
            return;
        case "context_solo":
            if (args.length >= 2) {
                set_selected_band(args[0]);
                set_selected_param("solo", args[1]);
            }
            return;
        case "selected_band":
            if (args.length > 0) set_selected_band(args[0]);
            return;
        case "strip_freq":
            if (args.length > 0) set_selected_param("freq", args[0]);
            return;
        case "strip_gain":
            if (args.length > 0) set_selected_param("gain", args[0]);
            return;
        case "strip_q":
            if (args.length > 0) set_selected_param("q", args[0]);
            return;
        case "strip_type":
            if (args.length > 0) set_selected_param("type", args[0]);
            return;
        case "strip_slope":
            if (args.length > 0) set_selected_param("slope", args[0]);
            return;
        case "strip_enable":
            if (args.length > 0) set_selected_param("enable", args[0]);
            return;
        case "strip_solo":
            if (args.length > 0) set_selected_param("solo", args[0]);
            return;
    }
}
""").substitute(
        buffer_names=json.dumps([buffer_names["short"], buffer_names["medium"], buffer_names["high"]]),
        fft_sizes=json.dumps([fft_sizes["short"], fft_sizes["medium"], fft_sizes["high"]]),
    )


device = AudioEffect("Linear Phase EQ", width=752, height=188, theme=MIDNIGHT)

for slug, _, fft_size in QUALITY_MODES:
    device.add_support_file(
        KERNEL_FILENAMES[slug],
        build_linear_phase_kernel(RESPONSE_BUFFERS[slug]),
        file_type="JSON",
    )

device.add_support_file(
    STATE_FILENAME,
    linear_phase_state_js(
        RESPONSE_BUFFERS,
        {slug: fft_size for slug, _, fft_size in QUALITY_MODES},
    ),
)

# ---------------------------------------------------------------------------
# UI shell
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 752, 188], bgcolor=BG)
device.add_panel("hero_frame", [8, 8, 736, 148], bgcolor=[0.05, 0.05, 0.06, 1.0],
                 border=1, bordercolor=BORDER, rounded=8)
device.add_panel("chips_frame", [8, 160, 736, 20], bgcolor=SURFACE,
                 border=1, bordercolor=BORDER, rounded=6)

device.add_comment("strip_band_label", [356, 163, 58, 10], "NO BAND",
                   fontname="Ableton Sans Bold", fontsize=6.8, textcolor=TEXT)
device.add_comment("freq_caption", [414, 163, 8, 8], "F",
                   fontsize=6.0, textcolor=TEXT_DIM)
device.add_number_box("selected_freq", "Selected Freq", [422, 160, 62, 16],
                      min_val=20.0, max_val=20000.0, initial=1000.0,
                      unitstyle=3, patching_rect=[700, 130, 70, 16], fontsize=7.2)
device.add_comment("gain_caption", [482, 163, 8, 8], "G",
                   fontsize=6.0, textcolor=TEXT_DIM)
device.add_number_box("selected_gain", "Selected Gain", [490, 160, 46, 16],
                      min_val=-30.0, max_val=30.0, initial=0.0,
                      unitstyle=4, patching_rect=[700, 160, 52, 16], fontsize=7.2)
device.add_comment("q_caption", [534, 163, 8, 8], "Q",
                   fontsize=6.0, textcolor=TEXT_DIM)
device.add_number_box("selected_q", "Selected Q", [542, 160, 38, 16],
                      min_val=0.1, max_val=30.0, initial=1.0,
                      unitstyle=1, patching_rect=[700, 190, 44, 16], fontsize=7.2)
device.add_live_text("selected_enable", "Selected Enable", [648, 160, 40, 16],
                     text_on="ON", text_off="BYP",
                     bgcolor=ACCENT_SOFT, bgoncolor=[0.26, 0.78, 0.52, 1.0],
                     textcolor=TEXT_DIM, textoncolor=[0.04, 0.06, 0.08, 1.0],
                     rounded=5, fontsize=6.2)
device.add_live_text("selected_solo", "Selected Solo", [692, 160, 48, 16],
                     text_on="LISTEN", text_off="LISTEN",
                     bgcolor=ACCENT_SOFT, bgoncolor=[0.90, 0.74, 0.24, 1.0],
                     textcolor=TEXT_DIM, textoncolor=[0.04, 0.06, 0.08, 1.0],
                     rounded=5, fontsize=6.0)

device.add_comment("lbl_quality", [150, 163, 8, 8], "Q",
                   fontsize=5.8, textcolor=TEXT_DIM)
device.add_tab("quality_tab", "Quality", [158, 160, 52, 16], options=QUALITY_OPTIONS,
               bgcolor=ACCENT_SOFT, bgoncolor=[0.24, 0.30, 0.38, 1.0],
               textcolor=TEXT_DIM, textoncolor=[0.04, 0.05, 0.07, 1.0], rounded=4, spacing_x=1.0,
               saved_attribute_attributes={
                   "valueof": {
                       "parameter_longname": "Quality",
                       "parameter_shortname": "Quality",
                       "parameter_type": 2,
                       "parameter_mmin": 0,
                       "parameter_mmax": len(QUALITY_OPTIONS) - 1,
                       "parameter_initial_enable": 1,
                       "parameter_initial": [1],
                       "parameter_enum": QUALITY_OPTIONS,
                   }
                   })

device.add_comment("lbl_analyzer", [222, 163, 8, 8], "A",
                   fontsize=5.8, textcolor=TEXT_DIM)
device.add_tab("analyzer_tab", "Analyzer", [230, 160, 56, 16], options=ANALYZER_OPTIONS,
               bgcolor=ACCENT_SOFT, bgoncolor=[ANALYZER[0], ANALYZER[1], ANALYZER[2], 1.0],
               textcolor=TEXT_DIM, textoncolor=[0.04, 0.05, 0.07, 1.0],
               rounded=4, spacing_x=1.0,
               saved_attribute_attributes={
                   "valueof": {
                       "parameter_longname": "Analyzer",
                       "parameter_shortname": "Analyzer",
                       "parameter_type": 2,
                       "parameter_mmin": 0,
                       "parameter_mmax": len(ANALYZER_OPTIONS) - 1,
                       "parameter_initial_enable": 1,
                       "parameter_initial": [2],
                       "parameter_enum": ANALYZER_OPTIONS,
                   }
                   })

device.add_comment("lbl_range", [294, 163, 8, 8], "R",
                   fontsize=5.8, textcolor=TEXT_DIM)
device.add_tab("range_tab", "Range", [302, 160, 44, 16], options=RANGE_OPTIONS,
               bgcolor=ACCENT_SOFT, bgoncolor=[0.24, 0.30, 0.38, 1.0],
               textcolor=TEXT_DIM, textoncolor=[0.04, 0.05, 0.07, 1.0], rounded=4, spacing_x=1.0,
               saved_attribute_attributes={
                   "valueof": {
                       "parameter_longname": "Range",
                       "parameter_shortname": "Range",
                       "parameter_type": 2,
                       "parameter_mmin": 0,
                       "parameter_mmax": len(RANGE_OPTIONS) - 1,
                       "parameter_initial_enable": 1,
                       "parameter_initial": [2],
                       "parameter_enum": RANGE_OPTIONS,
                   }
               })

device.add_comment("lbl_type", [900, 70, 24, 8], "TYPE",
                   fontsize=5.8, textcolor=TEXT_DIM)
device.add_menu("selected_type", "Selected Type", [900, 67, 62, 14],
                options=TYPE_OPTIONS, shortname="SelType",
                patching_rect=[700, 100, 72, 16], fontsize=7.2)

device.add_comment("lbl_slope", [900, 88, 24, 8], "SLOPE",
                   fontsize=5.8, textcolor=TEXT_DIM)
device.add_tab("selected_slope", "Selected Slope", [900, 85, 62, 14],
               options=SLOPE_OPTIONS,
               bgcolor=ACCENT_SOFT, bgoncolor=[0.24, 0.30, 0.38, 1.0],
               textcolor=TEXT_DIM, textoncolor=[0.04, 0.05, 0.07, 1.0], rounded=4, spacing_x=1.0)

device.add_comment("lbl_out", [900, 70, 14, 8], "G",
                   fontsize=5.8, textcolor=TEXT_DIM)
device.add_number_box("output_gain", "Output Gain", [900, 67, 56, 14],
                      min_val=-24.0, max_val=24.0, initial=0.0,
                      unitstyle=4, patching_rect=[700, 230, 52, 16], fontsize=7.2)

device.add_comment("menu_hint", [900, 88, 72, 12], "RIGHT-CLICK NODE",
                   fontsize=5.8, textcolor=TEXT_DIM, justification=1)

device.add_tab("collision_tab", "Collision", [900, 160, 8, 8], options=COLLISION_OPTIONS,
               bgcolor=ACCENT_SOFT, bgoncolor=[0.24, 0.30, 0.38, 1.0],
               textcolor=TEXT_DIM, textoncolor=TEXT, rounded=2, spacing_x=1.0,
               saved_attribute_attributes={
                   "valueof": {
                       "parameter_longname": "Collision",
                       "parameter_shortname": "Collision",
                       "parameter_type": 2,
                       "parameter_mmin": 0,
                       "parameter_mmax": len(COLLISION_OPTIONS) - 1,
                       "parameter_initial_enable": 1,
                       "parameter_initial": [1],
                       "parameter_enum": COLLISION_OPTIONS,
                   }
               })

device.add_comment("latency_readout", [586, 163, 56, 10], "46.4 ms",
                   fontsize=6.0, textcolor=TEXT_DIM, justification=1)

device.add_box({
    "box": {
        "id": "lpeq_spectroscope",
        "maxclass": "spectroscope~",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "background": 1,
        "ignoreclick": 1,
        "logfreq": 1,
        "interval": 20,
        "scroll": 0,
        "sono": 0,
        "logamp": 1,
        "domain": [20.0, 20000.0],
        "bgcolor": [0.05, 0.06, 0.07, 0.0],
        "fgcolor": [0.32, 0.92, 1.0, 0.12],
        "markercolor": [0.62, 0.62, 0.62, 0.0],
        "patching_rect": [10, 30, 728, 142],
        "presentation": 0,
    }
})

device.add_jsui(
    "lpeq_display",
    [12, 10, 728, 142],
    js_code=linear_phase_eq_display_js(
        bg_color="0.05, 0.06, 0.07, 0.0",
        composite_color="0.95, 0.97, 1.0, 1.0",
        fill_color="0.42, 0.74, 0.94, 0.10",
        analyzer_fill_color="0.24, 0.84, 0.98, 0.02",
        analyzer_line_color="0.40, 0.94, 1.0, 0.18",
        analyzer_peak_color="0.96, 0.98, 1.0, 0.0",
        grid_color="0.18, 0.20, 0.25, 0.64",
        text_color="0.48, 0.52, 0.58, 1.0",
        zero_line_color="0.34, 0.37, 0.42, 0.94",
        badge_color="0.10, 0.12, 0.15, 0.92",
        badge_border_color="0.25, 0.28, 0.34, 1.0",
    ),
    js_filename=DISPLAY_FILENAME,
    numinlets=3,
    numoutlets=4,
    outlettype=["", "", "", ""],
    patching_rect=[10, 30, 728, 142],
)

device.add_jsui(
    "band_chip_row",
    [12, 163, 132, 14],
    js_code=band_chip_row_js(),
    js_filename=CHIPROW_FILENAME,
    numinlets=1,
    numoutlets=1,
    outlettype=[""],
    patching_rect=[10, 320, 132, 20],
)

# ---------------------------------------------------------------------------
# Control plumbing
# ---------------------------------------------------------------------------
device.add_newobj("lb_init", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[20, 540, 55, 20])
device.add_newobj("dspstate_eq", "dspstate~", numinlets=1, numoutlets=4,
                  outlettype=["int", "float", "int", "int"],
                  patching_rect=[90, 540, 65, 20])
device.add_newobj("state_js", f"js {STATE_FILENAME}", numinlets=1, numoutlets=3,
                  outlettype=["", "", ""], patching_rect=[170, 540, 120, 20])

device.add_box({
    "box": {
        "id": "msg_state_init",
        "maxclass": "message",
        "text": "init",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [20, 568, 40, 20],
    }
})
device.add_newobj("prepend_sr", "prepend set_sample_rate", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[90, 568, 130, 20])

device.add_line("lb_init", 0, "msg_state_init", 0)
device.add_line("msg_state_init", 0, "state_js", 0)
device.add_line("lb_init", 0, "dspstate_eq", 0)
device.add_line("dspstate_eq", 1, "lpeq_display", 1)
device.add_line("dspstate_eq", 1, "prepend_sr", 0)
device.add_line("prepend_sr", 0, "state_js", 0)

device.add_newobj("route_strip_state",
                  "route band_label band_status freq gain q type slope enable solo latency_text selected",
                  numinlets=1, numoutlets=11,
                  outlettype=["", "", "", "", "", "", "", "", "", "", ""],
                  patching_rect=[310, 540, 420, 20])
device.add_line("state_js", 1, "route_strip_state", 0)

for route_id, target_id, patch_x in [
    ("prepend_set_band_label", "strip_band_label", 310),
    ("prepend_set_freq", "selected_freq", 420),
    ("prepend_set_gain", "selected_gain", 530),
    ("prepend_set_q", "selected_q", 640),
    ("prepend_set_type", "selected_type", 750),
    ("prepend_set_slope", "selected_slope", 860),
    ("prepend_set_enable", "selected_enable", 970),
    ("prepend_set_solo", "selected_solo", 1080),
    ("prepend_set_latency", "latency_readout", 1190),
]:
    device.add_newobj(route_id, "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[patch_x, 568, 80, 20])
    source_index = {
        "prepend_set_band_label": 0,
        "prepend_set_freq": 2,
        "prepend_set_gain": 3,
        "prepend_set_q": 4,
        "prepend_set_type": 5,
        "prepend_set_slope": 6,
        "prepend_set_enable": 7,
        "prepend_set_solo": 8,
        "prepend_set_latency": 9,
    }[route_id]
    device.add_line("route_strip_state", source_index, route_id, 0)
    device.add_line(route_id, 0, target_id, 0)

device.add_line("state_js", 0, "lpeq_display", 0)
device.add_line("state_js", 2, "band_chip_row", 0)

device.add_newobj("prepend_quality", "prepend set_quality", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 620, 110, 20])
device.add_newobj("quality_add1", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[140, 620, 36, 20])
device.add_newobj("quality_to_graph", "prepend set_quality_mode", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[186, 620, 136, 20])

device.add_box({
    "box": {
        "id": "msg_quality_default",
        "maxclass": "message",
        "text": "1",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [20, 646, 36, 20],
    }
})
device.add_line("lb_init", 0, "msg_quality_default", 0)
device.add_line("msg_quality_default", 0, "prepend_quality", 0)
device.add_line("msg_quality_default", 0, "quality_add1", 0)
device.add_line("msg_quality_default", 0, "quality_to_graph", 0)
device.add_line("quality_tab", 0, "prepend_quality", 0)
device.add_line("quality_tab", 0, "quality_add1", 0)
device.add_line("quality_tab", 0, "quality_to_graph", 0)
device.add_line("prepend_quality", 0, "state_js", 0)
device.add_line("quality_to_graph", 0, "lpeq_display", 0)

device.add_newobj("analyzer_sel", "select 0 1 2", numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", ""], patching_rect=[340, 620, 88, 20])
device.add_newobj("prepend_analyzer", "prepend set_analyzer_enabled", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[438, 620, 156, 20])
device.add_box({
    "box": {
        "id": "msg_analyzer_off",
        "maxclass": "message",
        "text": "0",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [340, 646, 30, 20],
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
        "patching_rect": [374, 646, 30, 20],
    }
})
device.add_box({
    "box": {
        "id": "msg_analyzer_pre",
        "maxclass": "message",
        "text": "1",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [408, 646, 30, 20],
    }
})
device.add_box({
    "box": {
        "id": "msg_analyzer_post",
        "maxclass": "message",
        "text": "2",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [442, 646, 30, 20],
    }
})
device.add_box({
    "box": {
        "id": "msg_analyzer_default",
        "maxclass": "message",
        "text": "2",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [476, 646, 36, 20],
    }
})
device.add_line("lb_init", 0, "msg_analyzer_default", 0)
device.add_line("msg_analyzer_default", 0, "analyzer_sel", 0)
device.add_line("analyzer_tab", 0, "analyzer_sel", 0)
device.add_line("analyzer_sel", 0, "msg_analyzer_off", 0)
device.add_line("analyzer_sel", 1, "msg_analyzer_on", 0)
device.add_line("analyzer_sel", 1, "msg_analyzer_pre", 0)
device.add_line("analyzer_sel", 2, "msg_analyzer_on", 0)
device.add_line("analyzer_sel", 2, "msg_analyzer_post", 0)
device.add_line("msg_analyzer_off", 0, "prepend_analyzer", 0)
device.add_line("msg_analyzer_on", 0, "prepend_analyzer", 0)
device.add_line("prepend_analyzer", 0, "lpeq_display", 0)

device.add_newobj("range_sel", "select 0 1 2 3", numinlets=1, numoutlets=5,
                  outlettype=["bang", "bang", "bang", "bang", ""],
                  patching_rect=[610, 620, 100, 20])
device.add_newobj("prepend_range", "prepend set_display_range", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[720, 620, 150, 20])

for idx, value in enumerate([3, 6, 12, 30]):
    msg_id = f"msg_range_{value}"
    device.add_box({
        "box": {
            "id": msg_id,
            "maxclass": "message",
            "text": str(value),
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [610 + idx * 38, 646, 34, 20],
        }
    })
    device.add_line("range_sel", idx, msg_id, 0)
    device.add_line(msg_id, 0, "prepend_range", 0)

device.add_box({
    "box": {
        "id": "msg_range_default",
        "maxclass": "message",
        "text": "2",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [770, 646, 34, 20],
    }
})
device.add_line("lb_init", 0, "msg_range_default", 0)
device.add_line("msg_range_default", 0, "range_sel", 0)
device.add_line("range_tab", 0, "range_sel", 0)
device.add_line("prepend_range", 0, "lpeq_display", 0)

device.add_newobj("prepend_collision", "prepend set_collision_mode", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[20, 698, 144, 20])
device.add_box({
    "box": {
        "id": "msg_collision_default",
        "maxclass": "message",
        "text": "1",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [172, 698, 34, 20],
    }
})
device.add_line("lb_init", 0, "msg_collision_default", 0)
device.add_line("msg_collision_default", 0, "prepend_collision", 0)
device.add_line("collision_tab", 0, "prepend_collision", 0)
device.add_line("prepend_collision", 0, "lpeq_display", 0)

for control_id, message_name, patch_x in [
    ("selected_freq", "strip_freq", 20),
    ("selected_gain", "strip_gain", 138),
    ("selected_q", "strip_q", 256),
    ("selected_type", "strip_type", 374),
    ("selected_slope", "strip_slope", 492),
    ("selected_enable", "strip_enable", 610),
    ("selected_solo", "strip_solo", 728),
]:
    prepend_id = f"prepend_{message_name}"
    device.add_newobj(prepend_id, f"prepend {message_name}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[patch_x, 730, 96, 20])
    device.add_line(control_id, 0, prepend_id, 0)
    device.add_line(prepend_id, 0, "state_js", 0)

device.add_line("band_chip_row", 0, "state_js", 0)
device.add_line("lpeq_display", 0, "state_js", 0)
device.add_line("lpeq_display", 1, "state_js", 0)
device.add_line("lpeq_display", 2, "state_js", 0)
device.add_line("lpeq_display", 3, "state_js", 0)

# ---------------------------------------------------------------------------
# Linear-phase backend
# ---------------------------------------------------------------------------
for slug, _, fft_size in QUALITY_MODES:
    device.add_newobj(RESPONSE_BUFFERS[slug], f"buffer~ {RESPONSE_BUFFERS[slug]}",
                      numinlets=1, numoutlets=2, outlettype=["float", "bang"],
                      patching_rect=[20, 780 + QUALITY_MODES.index((slug, _, fft_size)) * 26, 150, 20])

for slug, _, fft_size in QUALITY_MODES:
    pfft_id = f"pfft_{slug}"
    filename = KERNEL_FILENAMES[slug].replace(".maxpat", "")
    device.add_newobj(pfft_id, f"pfft~ {filename} {fft_size} 4",
                      numinlets=2, numoutlets=2, outlettype=["signal", "signal"],
                      patching_rect=[220, 780 + QUALITY_MODES.index((slug, _, fft_size)) * 28, 180, 20])
    device.add_line("obj-plugin", 0, pfft_id, 0)
    device.add_line("obj-plugin", 1, pfft_id, 1)

device.add_newobj("quality_sel_l", "selector~ 3 2", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[420, 780, 82, 20])
device.add_newobj("quality_sel_r", "selector~ 3 2", numinlets=4, numoutlets=1,
                  outlettype=["signal"], patching_rect=[514, 780, 82, 20])
device.add_line("quality_add1", 0, "quality_sel_l", 0)
device.add_line("quality_add1", 0, "quality_sel_r", 0)
device.add_line("pfft_short", 0, "quality_sel_l", 1)
device.add_line("pfft_medium", 0, "quality_sel_l", 2)
device.add_line("pfft_high", 0, "quality_sel_l", 3)
device.add_line("pfft_short", 1, "quality_sel_r", 1)
device.add_line("pfft_medium", 1, "quality_sel_r", 2)
device.add_line("pfft_high", 1, "quality_sel_r", 3)

device.add_newobj("out_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[612, 780, 46, 20])
device.add_newobj("out_gain_pack", "pack f 1. 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[666, 780, 80, 20])
device.add_newobj("out_gain_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[754, 780, 40, 20])
device.add_newobj("out_mul_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[804, 780, 44, 20])
device.add_newobj("out_mul_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[856, 780, 44, 20])

device.add_line("output_gain", 0, "out_dbtoa", 0)
device.add_line("out_dbtoa", 0, "out_gain_pack", 0)
device.add_line("out_gain_pack", 0, "out_gain_line", 0)
device.add_line("out_gain_line", 0, "out_mul_l", 1)
device.add_line("out_gain_line", 0, "out_mul_r", 1)
device.add_line("quality_sel_l", 0, "out_mul_l", 0)
device.add_line("quality_sel_r", 0, "out_mul_r", 0)
device.add_line("out_mul_l", 0, "obj-plugout", 0)
device.add_line("out_mul_r", 0, "obj-plugout", 1)

device.add_newobj("analyzer_source_sel_l", "selector~ 2 2", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[848, 810, 90, 20])
device.add_newobj("analyzer_source_sel_r", "selector~ 2 2", numinlets=3, numoutlets=1,
                  outlettype=["signal"], patching_rect=[948, 810, 90, 20])
device.add_newobj("analyzer_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1050, 810, 36, 20])
device.add_newobj("analyzer_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1092, 810, 44, 20])
device.add_newobj("analyzer_gate", "*~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1142, 810, 36, 20])
device.add_newobj("analyzer_gain_pack", "pack 0. 30", numinlets=2, numoutlets=1,
                  outlettype=["list"], patching_rect=[1184, 810, 70, 20])
device.add_newobj("analyzer_gain_line", "line~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1260, 810, 40, 20])
device.add_line("obj-plugin", 0, "analyzer_source_sel_l", 1)
device.add_line("obj-plugin", 1, "analyzer_source_sel_r", 1)
device.add_line("out_mul_l", 0, "analyzer_source_sel_l", 2)
device.add_line("out_mul_r", 0, "analyzer_source_sel_r", 2)
device.add_line("msg_analyzer_pre", 0, "analyzer_source_sel_l", 0)
device.add_line("msg_analyzer_pre", 0, "analyzer_source_sel_r", 0)
device.add_line("msg_analyzer_post", 0, "analyzer_source_sel_l", 0)
device.add_line("msg_analyzer_post", 0, "analyzer_source_sel_r", 0)
device.add_line("analyzer_source_sel_l", 0, "analyzer_sum", 0)
device.add_line("analyzer_source_sel_r", 0, "analyzer_sum", 1)
device.add_line("analyzer_sum", 0, "analyzer_avg", 0)
device.add_line("analyzer_avg", 0, "analyzer_gate", 0)
device.add_line("msg_analyzer_off", 0, "analyzer_gain_pack", 0)
device.add_line("msg_analyzer_on", 0, "analyzer_gain_pack", 0)
device.add_line("analyzer_gain_pack", 0, "analyzer_gain_line", 0)
device.add_line("analyzer_gain_line", 0, "analyzer_gate", 1)
device.add_line("analyzer_gate", 0, "lpeq_spectroscope", 0)
spectrum_analyzer_dsp(
    device,
    "lpeq_display",
    "analyzer_gate",
    source_outlet=0,
    num_bands=40,
    id_prefix="lpeq_overlay_spec",
    target_inlet=2,
    min_db=-72.0,
    max_db=0.0,
)

output = device_output_path("Linear Phase EQ")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
