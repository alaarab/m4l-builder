"""Standalone Spectrum Analyzer with a direct FFT-frame display path.

This build uses ``pfft~`` for analysis, but it no longer bridges magnitudes
through ``buffer~`` polling. The support patch emits live FFT frames directly
to a custom ``v8ui`` renderer so the graph can move like a real analyzer
instead of behaving like a pinned envelope.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m4l_builder import AudioEffect, Theme, device_output_path, newobj, patchline
from m4l_builder.constants import UNITSTYLE_FLOAT, UNITSTYLE_INT, UNITSTYLE_TIME


FFT_SIZE = 2048
FFT_OVERLAP = 4
FFT_BINS = FFT_SIZE // 2
KERNEL_FILENAME = "spectrum_analyzer_core_v2.maxpat"
DISPLAY_FILENAME = "spectrum_display_v4.js"
DISPLAY_POINTS = 320


def add_message(device, id, text, rect):
    """Add a Max message box and return its ID."""
    return device.add_box({
        "box": {
            "id": id,
            "maxclass": "message",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "text": text,
            "patching_rect": rect,
        }
    })


def _support_patcher(boxes, lines, width=540.0, height=260.0):
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


def build_spectrum_kernel() -> str:
    """Return a pfft~ support patch that streams FFT frames via ``out 1``."""
    boxes = []
    lines = []

    def add(box):
        boxes.append(box)

    def wire(src_id, src_outlet, dst_id, dst_inlet):
        lines.append(patchline(src_id, src_outlet, dst_id, dst_inlet))

    add(newobj("fft_in", "fftin~ 1 blackman", numinlets=1, numoutlets=3,
               outlettype=["signal", "signal", "signal"],
               patching_rect=[34.0, 34.0, 98.0, 22.0]))
    add(newobj("fft_out", "fftout~ 1 blackman", numinlets=2, numoutlets=0,
               patching_rect=[34.0, 234.0, 106.0, 22.0]))
    add(newobj("cartopol", "cartopol~", numinlets=2, numoutlets=2,
               outlettype=["signal", "signal"],
               patching_rect=[34.0, 74.0, 72.0, 22.0]))
    # Approximate 2/N FFT normalization so a strong sine lands near 0 dB.
    add(newobj("mag_scale", f"*~ {2.0 / FFT_SIZE}", numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[34.0, 114.0, 92.0, 22.0]))
    add(newobj("mag_smooth", f"vectral~ {FFT_BINS}", numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[34.0, 154.0, 96.0, 22.0]))
    add(newobj("smooth_default", "loadmess slide 3 11", numinlets=1, numoutlets=1,
               outlettype=[""],
               patching_rect=[146.0, 154.0, 118.0, 20.0]))
    add(newobj("frame_snap", "framesnap~ 33", numinlets=2, numoutlets=1,
               outlettype=["list"],
               patching_rect=[34.0, 194.0, 88.0, 22.0]))
    add(newobj("frame_start", "loadmess 1", numinlets=1, numoutlets=1,
               outlettype=[""],
               patching_rect=[146.0, 194.0, 72.0, 20.0]))
    add(newobj("ctrl_in", "in 1", numinlets=1, numoutlets=1,
               outlettype=[""],
               patching_rect=[284.0, 34.0, 34.0, 22.0]))
    add(newobj("ctrl_route", "route interval slide", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[284.0, 74.0, 116.0, 22.0]))
    add(newobj("smooth_prepend", "prepend slide", numinlets=1, numoutlets=1,
               outlettype=[""],
               patching_rect=[284.0, 114.0, 90.0, 22.0]))
    add(newobj("frame_out", "out 1", numinlets=1, numoutlets=0,
               patching_rect=[154.0, 234.0, 46.0, 22.0]))

    wire("fft_in", 0, "cartopol", 0)
    wire("fft_in", 1, "cartopol", 1)
    wire("fft_in", 0, "fft_out", 0)
    wire("fft_in", 1, "fft_out", 1)
    wire("cartopol", 0, "mag_scale", 0)
    wire("mag_scale", 0, "mag_smooth", 1)
    wire("smooth_default", 0, "mag_smooth", 0)
    wire("frame_start", 0, "frame_snap", 0)
    wire("mag_smooth", 0, "frame_snap", 0)
    wire("frame_snap", 0, "frame_out", 0)
    wire("ctrl_in", 0, "ctrl_route", 0)
    wire("ctrl_route", 0, "frame_snap", 1)
    wire("ctrl_route", 1, "smooth_prepend", 0)
    wire("smooth_prepend", 0, "mag_smooth", 0)

    return json.dumps(_support_patcher(boxes, lines), indent=2)


def spectrum_display_js(display_points: int) -> str:
    """Return the custom analyzer renderer used by the standalone product."""
    return (
        """// Spectrum display - custom FFT renderer
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 0;

var DISPLAY_POINTS = __DISPLAY_POINTS__;

var MIN_FREQ = 20.0;
var MAX_FREQ = 20000.0;
var FLOOR_DB = -144.0;
var CEIL_DB = -12.0;
var DISPLAY_TRIM_DB = -56.0;
var DISPLAY_TILT_DB = 0.0;

var samplerate_hz = 48000.0;
var refresh_mode = 0;
var color_mode = 0;
var channel_label = "SUM";
var rise_smoothing = 0.22;
var fall_smoothing = 0.82;
var peak_drop = 1.2;

var last_frame = [];
var displayed = [];
var peaks = [];
var sampled = [];

var LOG_MIN = Math.log(MIN_FREQ) / Math.LN10;
var LOG_MAX = Math.log(MAX_FREQ) / Math.LN10;
var LOG_RANGE = LOG_MAX - LOG_MIN;

var MAJOR_FREQS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];
var MINOR_FREQS = [30, 70, 150, 300, 700, 1500, 3000, 7000, 15000];
var DB_LINES = [0, -12, -24, -36, -48, -60, -72];

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function lerp(a, b, t) {
    return a + (b - a) * t;
}

function ensure_arrays() {
    if (displayed.length == DISPLAY_POINTS) return;
    displayed = [];
    peaks = [];
    sampled = [];
    for (var i = 0; i < DISPLAY_POINTS; i++) {
        displayed.push(FLOOR_DB);
        peaks.push(FLOOR_DB);
        sampled.push(FLOOR_DB);
    }
}

function set_refresh_mode(mode) {
    refresh_mode = clamp(Math.round(mode), 0, 2);
    if (refresh_mode === 0) {
        rise_smoothing = 0.16;
        fall_smoothing = 0.74;
        peak_drop = 1.6;
    } else if (refresh_mode === 1) {
        rise_smoothing = 0.22;
        fall_smoothing = 0.82;
        peak_drop = 1.2;
    } else {
        rise_smoothing = 0.30;
        fall_smoothing = 0.88;
        peak_drop = 0.8;
    }
}

function log_freq(norm) {
    return Math.pow(10, LOG_MIN + clamp(norm, 0.0, 1.0) * LOG_RANGE);
}

function freq_to_x(freq, plot_x, plot_w) {
    var logv = Math.log(clamp(freq, MIN_FREQ, MAX_FREQ)) / Math.LN10;
    return plot_x + ((logv - LOG_MIN) / LOG_RANGE) * plot_w;
}

function db_to_y(db, plot_y, plot_h) {
    var clipped = clamp(db, FLOOR_DB, CEIL_DB);
    return plot_y + (1.0 - ((clipped - FLOOR_DB) / (CEIL_DB - FLOOR_DB))) * plot_h;
}

function linear_to_db(v) {
    var safe = v;
    if (safe < 0.000000001) safe = 0.000000001;
    return 20.0 * (Math.log(safe) / Math.LN10);
}

function freq_tilt_db(freq) {
    var norm = (Math.log(clamp(freq, MIN_FREQ, MAX_FREQ)) / Math.LN10 - LOG_MIN) / LOG_RANGE;
    return norm * DISPLAY_TILT_DB;
}

function band_energy(bins, frame_count, freq_lo, freq_hi) {
    var nyquist = Math.max(samplerate_hz * 0.5, MAX_FREQ);
    var bin_lo = clamp(Math.floor((freq_lo / nyquist) * (frame_count - 1)), 1, frame_count - 1);
    var bin_hi = clamp(Math.ceil((freq_hi / nyquist) * (frame_count - 1)), bin_lo, frame_count - 1);
    var peak = 0.0;
    var sum = 0.0;
    var count = 0;
    var i;
    for (i = bin_lo; i <= bin_hi; i++) {
        var value = bins[i];
        if (value > peak) peak = value;
        sum += value;
        count += 1;
    }
    if (count < 1) return 0.0;
    return peak * 0.40 + (sum / count) * 0.60;
}

function process_frame(bins) {
    ensure_arrays();
    var frame_count = bins.length;
    if (!frame_count || frame_count < 8) return false;

    var i;
    for (i = 0; i < DISPLAY_POINTS; i++) {
        var norm = i / Math.max(DISPLAY_POINTS - 1, 1);
        var freq = log_freq(norm);
        var left_norm = (i - 2.15) / Math.max(DISPLAY_POINTS - 1, 1);
        var right_norm = (i + 2.15) / Math.max(DISPLAY_POINTS - 1, 1);
        var raw = band_energy(bins, frame_count, log_freq(left_norm), log_freq(right_norm));
        sampled[i] = clamp(
            linear_to_db(raw) + DISPLAY_TRIM_DB + freq_tilt_db(freq),
            FLOOR_DB,
            CEIL_DB
        );
    }

    for (i = 0; i < DISPLAY_POINTS; i++) {
        var prev1 = sampled[Math.max(i - 1, 0)];
        var next1 = sampled[Math.min(i + 1, DISPLAY_POINTS - 1)];
        var incoming = sampled[i] * 0.60 + prev1 * 0.20 + next1 * 0.20;

        if (incoming > displayed[i]) {
            displayed[i] = displayed[i] * rise_smoothing + incoming * (1.0 - rise_smoothing);
        } else {
            displayed[i] = displayed[i] * fall_smoothing + incoming * (1.0 - fall_smoothing);
        }

        if (displayed[i] > peaks[i]) {
            peaks[i] = displayed[i];
        } else {
            peaks[i] = Math.max(FLOOR_DB, peaks[i] - peak_drop);
        }
    }

    return true;
}

function bang() {
    mgraphics.redraw();
}

function msg_int(v) {
    set_refresh_mode(v);
    mgraphics.redraw();
}

function msg_float(v) {
    msg_int(Math.round(v));
}

function list() {
    var args = arrayfromargs(arguments);
    if (args.length > 7) {
        last_frame = args;
        process_frame(args);
        mgraphics.redraw();
    }
}

function anything() {
    var args = arrayfromargs(arguments);
    if (messagename == "set_refresh" && args.length > 0) {
        set_refresh_mode(args[0]);
    } else if (messagename == "set_color_mode" && args.length > 0) {
        color_mode = clamp(Math.round(args[0]), 0, 1);
    } else if (messagename == "set_channel" && args.length > 0) {
        channel_label = String(args[0]);
    } else if (messagename == "set_samplerate" && args.length > 0) {
        samplerate_hz = Math.max(22050.0, args[0]);
    } else if (messagename == "clear_peaks") {
        for (var i = 0; i < peaks.length; i++) {
            peaks[i] = displayed[i];
        }
    }
    mgraphics.redraw();
}

function path_curve(values, plot_x, plot_y, plot_w, plot_h) {
    var i;
    for (i = 0; i < values.length; i++) {
        var t = i / Math.max(values.length - 1, 1);
        var x = plot_x + t * plot_w;
        var y = db_to_y(values[i], plot_y, plot_h);
        if (i === 0) {
            mgraphics.move_to(x, y);
        } else {
            mgraphics.line_to(x, y);
        }
    }
}

function freq_color(t) {
    var c0;
    var c1;
    var local_t;
    if (t < 0.25) {
        c0 = [0.96, 0.26, 0.22];
        c1 = [0.95, 0.58, 0.18];
        local_t = t / 0.25;
    } else if (t < 0.52) {
        c0 = [0.95, 0.58, 0.18];
        c1 = [0.86, 0.82, 0.24];
        local_t = (t - 0.25) / 0.27;
    } else if (t < 0.78) {
        c0 = [0.86, 0.82, 0.24];
        c1 = [0.28, 0.78, 0.56];
        local_t = (t - 0.52) / 0.26;
    } else {
        c0 = [0.28, 0.78, 0.56];
        c1 = [0.22, 0.72, 0.96];
        local_t = (t - 0.78) / 0.22;
    }
    return [
        lerp(c0[0], c1[0], local_t),
        lerp(c0[1], c1[1], local_t),
        lerp(c0[2], c1[2], local_t)
    ];
}

function draw_plot_bg(plot_x, plot_y, plot_w, plot_h) {
    var top = [0.06, 0.09, 0.13, 0.98];
    var bottom = [0.08, 0.11, 0.16, 0.98];
    var gradient = mgraphics.pattern_create_linear(plot_x, plot_y, plot_x, plot_y + plot_h);
    gradient.add_color_stop_rgba(0.0, top[0], top[1], top[2], top[3]);
    gradient.add_color_stop_rgba(1.0, bottom[0], bottom[1], bottom[2], bottom[3]);

    mgraphics.set_source(gradient);
    mgraphics.rectangle_rounded(plot_x, plot_y, plot_w, plot_h, 5, 5);
    mgraphics.fill();

    mgraphics.set_line_width(1.0);
    mgraphics.set_source_rgba(0.24, 0.28, 0.34, 0.88);
    mgraphics.rectangle_rounded(plot_x + 0.5, plot_y + 0.5, plot_w - 1.0, plot_h - 1.0, 4, 4);
    mgraphics.stroke();
}

function draw_grid(plot_x, plot_y, plot_w, plot_h) {
    var i;
    mgraphics.set_line_width(1.0);
    mgraphics.set_source_rgba(0.20, 0.24, 0.29, 0.22);
    for (i = 0; i < MINOR_FREQS.length; i++) {
        var mx = freq_to_x(MINOR_FREQS[i], plot_x, plot_w);
        mgraphics.move_to(mx, plot_y + 1);
        mgraphics.line_to(mx, plot_y + plot_h - 1);
        mgraphics.stroke();
    }

    mgraphics.set_source_rgba(0.28, 0.32, 0.38, 0.34);
    for (i = 0; i < MAJOR_FREQS.length; i++) {
        var x = freq_to_x(MAJOR_FREQS[i], plot_x, plot_w);
        mgraphics.move_to(x, plot_y + 1);
        mgraphics.line_to(x, plot_y + plot_h - 1);
        mgraphics.stroke();
    }

    for (i = 0; i < DB_LINES.length; i++) {
        var db = DB_LINES[i];
        var y = db_to_y(db, plot_y, plot_h);
        if (db === 0) {
            mgraphics.set_source_rgba(0.42, 0.48, 0.56, 0.56);
        } else {
            mgraphics.set_source_rgba(0.22, 0.26, 0.31, 0.28);
        }
        mgraphics.move_to(plot_x + 1, y);
        mgraphics.line_to(plot_x + plot_w - 1, y);
        mgraphics.stroke();
    }
}

function draw_labels(plot_x, plot_y, plot_w, plot_h, h) {
    var i;
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(8);
    mgraphics.set_source_rgba(0.55, 0.62, 0.72, 0.88);

    for (i = 0; i < MAJOR_FREQS.length; i++) {
        var label_freq = MAJOR_FREQS[i];
        var label = label_freq >= 1000 ? ((label_freq / 1000) + "k") : String(label_freq);
        var label_x = freq_to_x(label_freq, plot_x, plot_w);
        mgraphics.move_to(label_x - 8, h - 6);
        mgraphics.show_text(label);
    }

    var db_marks = [-12, -48, -84, -120];
    for (i = 0; i < db_marks.length; i++) {
        var db_y = db_to_y(db_marks[i], plot_y, plot_h);
        mgraphics.move_to(plot_x + 6, db_y - 2);
        mgraphics.show_text(String(db_marks[i]));
    }

    mgraphics.set_source_rgba(0.80, 0.84, 0.90, 0.80);
    mgraphics.move_to(plot_x + 10, plot_y + 13);
    mgraphics.show_text(channel_label);
}

function draw_solid_curve(plot_x, plot_y, plot_w, plot_h) {
    mgraphics.set_line_width(2.2);
    mgraphics.set_source_rgba(0.10, 0.54, 0.70, 0.18);
    path_curve(displayed, plot_x, plot_y, plot_w, plot_h);
    mgraphics.stroke();

    mgraphics.set_line_width(1.15);
    mgraphics.set_source_rgba(0.02, 0.86, 0.96, 0.94);
    path_curve(displayed, plot_x, plot_y, plot_w, plot_h);
    mgraphics.stroke();
}

function draw_freq_curve(plot_x, plot_y, plot_w, plot_h) {
    var i;
    for (i = 0; i < DISPLAY_POINTS - 1; i++) {
        var t0 = i / Math.max(DISPLAY_POINTS - 1, 1);
        var c0 = freq_color(t0);
        var x0 = plot_x + t0 * plot_w;
        var y0 = db_to_y(displayed[i], plot_y, plot_h);
        var x1 = plot_x + ((i + 1) / Math.max(DISPLAY_POINTS - 1, 1)) * plot_w;
        var y1 = db_to_y(displayed[i + 1], plot_y, plot_h);
        mgraphics.set_line_width(1.15);
        mgraphics.set_source_rgba(c0[0], c0[1], c0[2], 0.94);
        mgraphics.move_to(x0, y0);
        mgraphics.line_to(x1, y1);
        mgraphics.stroke();
    }
}

function draw_peaks(plot_x, plot_y, plot_w, plot_h) {
    mgraphics.set_line_width(1.0);
    mgraphics.set_source_rgba(0.76, 0.86, 0.94, 0.16);
    path_curve(peaks, plot_x, plot_y, plot_w, plot_h);
    mgraphics.stroke();
}

function draw_no_signal(plot_x, plot_y, plot_w, plot_h) {
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(10);
    mgraphics.set_source_rgba(0.54, 0.60, 0.68, 0.46);
    mgraphics.move_to(plot_x + plot_w * 0.5 - 30, plot_y + plot_h * 0.5);
    mgraphics.show_text("NO SIGNAL");
}

function paint() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    var plot_x = 6.0;
    var plot_y = 6.0;
    var plot_w = w - 12.0;
    var plot_h = h - 18.0;

    draw_plot_bg(plot_x, plot_y, plot_w, plot_h);
    draw_grid(plot_x, plot_y, plot_w, plot_h);

    if (displayed.length > 0) {
        if (color_mode === 0) {
            draw_solid_curve(plot_x, plot_y, plot_w, plot_h);
        } else {
            draw_freq_curve(plot_x, plot_y, plot_w, plot_h);
        }
        draw_peaks(plot_x, plot_y, plot_w, plot_h);
    } else {
        draw_no_signal(plot_x, plot_y, plot_w, plot_h);
    }

    draw_labels(plot_x, plot_y, plot_w, plot_h, h);
}

set_refresh_mode(0);
"""
        .replace("__DISPLAY_POINTS__", str(display_points))
    )


UI_THEME = Theme.custom(
    bg=[0.24, 0.24, 0.25, 1.0],
    surface=[0.28, 0.29, 0.31, 1.0],
    section=[0.20, 0.21, 0.23, 1.0],
    text=[0.92, 0.92, 0.93, 1.0],
    text_dim=[0.70, 0.71, 0.74, 1.0],
    accent=[0.28, 0.78, 0.94, 1.0],
    meter_cold=[0.28, 0.64, 0.88, 1.0],
    meter_warm=[0.52, 0.80, 0.96, 1.0],
    meter_hot=[0.88, 0.72, 0.24, 1.0],
    meter_over=[0.88, 0.24, 0.18, 1.0],
    fontname="Ableton Sans Medium",
    fontname_bold="Ableton Sans Bold",
)


def build_device():
    """Return the standalone Spectrum Analyzer device."""
    device = AudioEffect("Spectrum Analyzer", width=413, height=158, theme=UI_THEME)
    theme = device.theme

    bg = [47 / 255.0, 47 / 255.0, 47 / 255.0, 1.0]
    strip_bg = list(bg)
    graph_bg = [0.07, 0.10, 0.14, 1.0]
    text = [0.82, 0.82, 0.83, 1.0]
    text_dim = [0.70, 0.71, 0.73, 1.0]
    divider_color = [33 / 255.0, 33 / 255.0, 33 / 255.0, 1.0]
    button_bg = [18 / 255.0, 18 / 255.0, 18 / 255.0, 1.0]
    button_on = [1.0, 163 / 255.0, 76 / 255.0, 1.0]
    button_text = [0.86, 0.88, 0.90, 1.0]
    button_text_on = [0.10, 0.11, 0.13, 1.0]
    auto_bg = [11 / 255.0, 187 / 255.0, 207 / 255.0, 1.0]
    auto_text = [0.06, 0.12, 0.14, 1.0]

    def add_mode_button(id, varname, rect, label, *, mode=0, on_color=None,
                        off_color=None, text_color=None, text_on_color=None):
        return device.add_box({
            "box": {
                "id": id,
                "maxclass": "live.text",
                "varname": varname,
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", ""],
                "parameter_enable": 0,
                "text": label,
                "texton": label,
                "fontname": theme.fontname,
                "fontsize": 8.1,
                "mode": mode,
                "rounded": 0.0,
                "bgcolor": list(off_color or button_bg),
                "bgoncolor": list(on_color or button_on),
                "textcolor": list(text_color or button_text),
                "textoncolor": list(text_on_color or button_text_on),
                "patching_rect": [700, 1100, rect[2], rect[3]],
                "presentation": 1,
                "presentation_rect": rect,
            }
        })

    block_valueof = {
        "parameter_longname": "Block",
        "parameter_shortname": "Block",
        "parameter_type": 2,
        "parameter_mmin": 0,
        "parameter_mmax": 4,
        "parameter_initial_enable": 1,
        "parameter_initial": [3],
        "parameter_enum": ["1024", "2048", "4096", "8192", "16384"],
    }

    device.add_panel("bg", [0, 0, 413, 158], bgcolor=bg)
    device.add_panel("control_strip", [0, 0, 134, 158],
                     bgcolor=strip_bg,
                     border=0)
    device.add_panel("divider", [133, 0, 1, 158],
                     bgcolor=divider_color,
                     border=0)
    device.add_panel("sep_block", [14, 22, 114, 1], bgcolor=divider_color, border=0)
    device.add_panel("sep_channel", [14, 52, 114, 1], bgcolor=divider_color, border=0)
    device.add_panel("sep_avg", [14, 101, 114, 1], bgcolor=divider_color, border=0)

    device.add_comment("label_block", [15, 3, 28, 10], text="Block",
                       textcolor=text, fontsize=8.7, bgcolor=[0, 0, 0, 0])
    device.add_comment("label_channel", [15, 33, 40, 10], text="Channel",
                       textcolor=text, fontsize=8.7, bgcolor=[0, 0, 0, 0])
    device.add_comment("label_refresh", [15, 64, 38, 10], text="Refresh",
                       textcolor=text, fontsize=8.7, bgcolor=[0, 0, 0, 0])
    device.add_comment("label_avg", [15, 83, 18, 10], text="Avg",
                       textcolor=text, fontsize=8.7, bgcolor=[0, 0, 0, 0])
    device.add_comment("label_graph", [15, 113, 30, 10], text="Graph",
                       textcolor=text, fontsize=8.7, bgcolor=[0, 0, 0, 0])
    device.add_comment("label_scale", [15, 131, 36, 10], text="Scale X",
                       textcolor=text, fontsize=8.7, bgcolor=[0, 0, 0, 0])

    device.add_meter("input_meter", [0, 0, 9, 158],
                     coldcolor=[0.14, 0.88, 0.37, 1.0],
                     warmcolor=[0.22, 0.95, 0.46, 1.0],
                     hotcolor=[0.40, 1.00, 0.58, 1.0],
                     overloadcolor=[0.72, 1.00, 0.70, 1.0])

    device.add_panel("graph_bg", [134, 0, 279, 158], bgcolor=graph_bg, border=0)
    device.add_support_file(KERNEL_FILENAME, build_spectrum_kernel())
    device.add_v8ui(
        "spec_display",
        [134, 0, 279, 158],
        js_code=spectrum_display_js(DISPLAY_POINTS),
        js_filename=DISPLAY_FILENAME,
        numinlets=1,
        numoutlets=0,
        patching_rect=[158, 30, 279, 158],
        background=0,
        ignoreclick=1,
        bgcolor=[0.0, 0.0, 0.0, 0.0],
        border=0,
    )

    device.add_menu("block_menu", "Block", [56, 1, 73, 13],
                    options=["1024", "2048", "4096", "8192", "16384"],
                    fontsize=8.5,
                    saved_attribute_attributes={"valueof": block_valueof})
    device.add_number_box("refresh_box", "Refresh", [56, 59, 48, 13],
                          min_val=20.0, max_val=500.0, initial=60.0,
                          fontsize=8.5, unitstyle=UNITSTYLE_TIME,
                          appearance=2,
                          activeslidercolor=[0.22, 0.66, 0.78, 1.0])
    device.add_number_box("avg_box", "Avg", [56, 78, 48, 13],
                          min_val=1, max_val=32, initial=1,
                          fontsize=8.5, unitstyle=UNITSTYLE_INT,
                          appearance=2,
                          activeslidercolor=[0.25, 0.29, 0.33, 1.0])
    device.add_number_box("range_lo_box", "Range Low", [56, 146, 33, 12],
                          min_val=0.0, max_val=1.2, initial=0.0,
                          fontsize=7.8, unitstyle=UNITSTYLE_FLOAT)
    device.add_number_box("range_hi_box", "Range High", [95, 146, 33, 12],
                          min_val=0.1, max_val=1.2, initial=1.0,
                          fontsize=7.8, unitstyle=UNITSTYLE_FLOAT)

    add_mode_button("channel_btn_l", "Channel L", [56, 31, 13, 13], "L")
    add_mode_button("channel_btn_r", "Channel R", [72, 31, 13, 13], "R")
    add_mode_button("channel_btn_sum", "Channel L+R", [88, 31, 22, 13], "L+R")
    add_mode_button("graph_btn_line", "Graph Line", [56, 110, 38, 13], "Line")
    add_mode_button("graph_btn_max", "Graph Max", [97, 110, 31, 13], "Max")
    add_mode_button("scale_btn_lin", "Scale Lin", [56, 128, 22, 13], "Lin")
    add_mode_button("scale_btn_log", "Scale Log", [81, 128, 22, 13], "Log")
    add_mode_button("scale_btn_st", "Scale ST", [106, 128, 22, 13], "ST")
    add_mode_button("auto_button", "Auto", [15, 146, 34, 12], "Auto",
                    mode=1,
                    on_color=auto_bg,
                    off_color=auto_bg,
                    text_color=auto_text,
                    text_on_color=auto_text)

    # Transparent audible path.
    device.add_line("obj-plugin", 0, "obj-plugout", 0)
    device.add_line("obj-plugin", 1, "obj-plugout", 1)

    # Analyzer tap.
    device.add_newobj("src_sum", "+~", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[26, 240, 30, 20])
    device.add_newobj("src_avg", "*~ 0.5", numinlets=2, numoutlets=1,
                      outlettype=["signal"], patching_rect=[26, 268, 45, 20])
    device.add_newobj("src_sel", "selector~ 3 1", numinlets=4, numoutlets=1,
                      outlettype=["signal"], patching_rect=[26, 298, 84, 20])
    device.add_newobj("fft_core", f"pfft~ {Path(KERNEL_FILENAME).stem} {FFT_SIZE} {FFT_OVERLAP}",
                      numinlets=2, numoutlets=2,
                      outlettype=["signal", ""], patching_rect=[26, 326, 196, 22])
    device.add_newobj("channel_state", "int", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[116, 242, 36, 20])
    device.add_newobj("graph_state", "int", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[160, 242, 36, 20])
    device.add_newobj("scale_state", "int", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[204, 242, 36, 20])
    device.add_newobj("channel_eq_l", "== 0", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[116, 270, 34, 20])
    device.add_newobj("channel_eq_r", "== 1", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[156, 270, 34, 20])
    device.add_newobj("channel_eq_sum", "== 2", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[196, 270, 34, 20])
    device.add_newobj("graph_eq_line", "== 0", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[240, 270, 34, 20])
    device.add_newobj("graph_eq_max", "== 1", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[280, 270, 34, 20])
    device.add_newobj("scale_eq_lin", "== 0", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[320, 270, 34, 20])
    device.add_newobj("scale_eq_log", "== 1", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[360, 270, 34, 20])
    device.add_newobj("scale_eq_st", "== 2", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[400, 270, 34, 20])
    device.add_newobj("set_channel_l", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[116, 298, 72, 20])
    device.add_newobj("set_channel_r", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[194, 298, 72, 20])
    device.add_newobj("set_channel_sum", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[272, 298, 72, 20])
    device.add_newobj("set_graph_line", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[350, 298, 72, 20])
    device.add_newobj("set_graph_max", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[428, 298, 72, 20])
    device.add_newobj("set_scale_lin", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[506, 298, 72, 20])
    device.add_newobj("set_scale_log", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[584, 298, 72, 20])
    device.add_newobj("set_scale_st", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[662, 298, 72, 20])
    device.add_newobj("channel_label_sel", "sel 0 1 2", numinlets=4, numoutlets=4,
                      outlettype=["bang", "bang", "bang", ""],
                      patching_rect=[740, 298, 84, 20])
    device.add_newobj("channel_label_msg", "prepend set_channel", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[830, 298, 108, 20])
    add_message(device, "msg_channel_idx_l", "0", [116, 326, 24, 18])
    add_message(device, "msg_channel_idx_r", "1", [144, 326, 24, 18])
    add_message(device, "msg_channel_idx_sum", "2", [172, 326, 24, 18])
    add_message(device, "msg_graph_idx_line", "0", [240, 326, 24, 18])
    add_message(device, "msg_graph_idx_max", "1", [268, 326, 24, 18])
    add_message(device, "msg_scale_idx_lin", "0", [320, 326, 24, 18])
    add_message(device, "msg_scale_idx_log", "1", [348, 326, 24, 18])
    add_message(device, "msg_scale_idx_st", "2", [376, 326, 24, 18])
    add_message(device, "msg_channel_l", "2", [440, 326, 24, 18])
    add_message(device, "msg_channel_r", "3", [468, 326, 24, 18])
    add_message(device, "msg_channel_sum", "1", [496, 326, 24, 18])
    add_message(device, "msg_channel_label_l", "L", [526, 326, 24, 18])
    add_message(device, "msg_channel_label_r", "R", [554, 326, 24, 18])
    add_message(device, "msg_channel_label_sum", "SUM", [582, 326, 36, 18])

    device.add_line("obj-plugin", 0, "src_sum", 0)
    device.add_line("obj-plugin", 1, "src_sum", 1)
    device.add_line("src_sum", 0, "src_avg", 0)
    device.add_line("src_avg", 0, "src_sel", 1)
    device.add_line("src_avg", 0, "input_meter", 0)
    device.add_line("obj-plugin", 0, "src_sel", 2)
    device.add_line("obj-plugin", 1, "src_sel", 3)
    device.add_line("src_sel", 0, "fft_core", 0)
    device.add_line("fft_core", 1, "spec_display", 0)

    # Channel selection.
    device.add_newobj("channel_default", "loadmess 2", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[540, 234, 70, 20])
    device.add_line("channel_default", 0, "channel_state", 0)
    device.add_line("channel_btn_l", 0, "msg_channel_idx_l", 0)
    device.add_line("channel_btn_r", 0, "msg_channel_idx_r", 0)
    device.add_line("channel_btn_sum", 0, "msg_channel_idx_sum", 0)
    device.add_line("msg_channel_idx_l", 0, "channel_state", 0)
    device.add_line("msg_channel_idx_r", 0, "channel_state", 0)
    device.add_line("msg_channel_idx_sum", 0, "channel_state", 0)
    device.add_line("channel_state", 0, "channel_eq_l", 0)
    device.add_line("channel_state", 0, "channel_eq_r", 0)
    device.add_line("channel_state", 0, "channel_eq_sum", 0)
    device.add_line("channel_eq_l", 0, "set_channel_l", 0)
    device.add_line("channel_eq_r", 0, "set_channel_r", 0)
    device.add_line("channel_eq_sum", 0, "set_channel_sum", 0)
    device.add_line("set_channel_l", 0, "channel_btn_l", 0)
    device.add_line("set_channel_r", 0, "channel_btn_r", 0)
    device.add_line("set_channel_sum", 0, "channel_btn_sum", 0)
    device.add_line("channel_state", 0, "channel_label_sel", 0)
    device.add_line("channel_label_sel", 0, "msg_channel_label_l", 0)
    device.add_line("channel_label_sel", 1, "msg_channel_label_r", 0)
    device.add_line("channel_label_sel", 2, "msg_channel_label_sum", 0)
    device.add_line("msg_channel_label_l", 0, "channel_label_msg", 0)
    device.add_line("msg_channel_label_r", 0, "channel_label_msg", 0)
    device.add_line("msg_channel_label_sum", 0, "channel_label_msg", 0)
    device.add_line("channel_label_msg", 0, "spec_display", 0)
    device.add_line("channel_state", 0, "msg_channel_l", 0)
    device.add_line("channel_state", 0, "msg_channel_r", 0)
    device.add_line("channel_state", 0, "msg_channel_sum", 0)
    device.add_line("msg_channel_l", 0, "src_sel", 0)
    device.add_line("msg_channel_r", 0, "src_sel", 0)
    device.add_line("msg_channel_sum", 0, "src_sel", 0)

    # Refresh interval.
    device.add_newobj("refresh_interval", "prepend interval", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[620, 234, 92, 20])
    device.add_newobj("refresh_default", "loadmess 60", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[720, 234, 78, 20])
    device.add_line("refresh_default", 0, "refresh_box", 0)
    device.add_line("refresh_default", 0, "refresh_interval", 0)
    device.add_line("refresh_box", 1, "refresh_interval", 0)
    device.add_line("refresh_interval", 0, "fft_core", 1)

    # Averaging -> vectral~ slide settings inside the FFT core.
    device.add_newobj("avg_default", "loadmess 1", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[620, 326, 72, 20])
    device.add_newobj("avg_slide_split", "t i i", numinlets=1, numoutlets=2,
                      outlettype=["int", "int"], patching_rect=[700, 326, 40, 20])
    device.add_newobj("avg_slide_pair", "pak 1 1", numinlets=2, numoutlets=1,
                      outlettype=["list"], patching_rect=[746, 326, 54, 20])
    device.add_newobj("avg_slide_msg", "prepend slide", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[806, 326, 92, 20])
    device.add_line("avg_default", 0, "avg_box", 0)
    device.add_line("avg_default", 0, "avg_slide_split", 0)
    device.add_line("avg_box", 1, "avg_slide_split", 0)
    device.add_line("avg_slide_split", 0, "avg_slide_pair", 0)
    device.add_line("avg_slide_split", 1, "avg_slide_pair", 1)
    device.add_line("avg_slide_pair", 0, "avg_slide_msg", 0)
    device.add_line("avg_slide_msg", 0, "fft_core", 1)

    # Visible group buttons mirror stock geometry while hidden ints hold state.
    device.add_newobj("graph_default", "loadmess 0", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[540, 262, 70, 20])
    device.add_newobj("scale_default", "loadmess 1", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[620, 262, 70, 20])
    device.add_line("graph_default", 0, "graph_state", 0)
    device.add_line("scale_default", 0, "scale_state", 0)
    device.add_line("graph_btn_line", 0, "msg_graph_idx_line", 0)
    device.add_line("graph_btn_max", 0, "msg_graph_idx_max", 0)
    device.add_line("msg_graph_idx_line", 0, "graph_state", 0)
    device.add_line("msg_graph_idx_max", 0, "graph_state", 0)
    device.add_line("graph_state", 0, "graph_eq_line", 0)
    device.add_line("graph_state", 0, "graph_eq_max", 0)
    device.add_line("graph_eq_line", 0, "set_graph_line", 0)
    device.add_line("graph_eq_max", 0, "set_graph_max", 0)
    device.add_line("set_graph_line", 0, "graph_btn_line", 0)
    device.add_line("set_graph_max", 0, "graph_btn_max", 0)

    device.add_newobj("scale_is_log", "!= 0", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[700, 262, 42, 20])
    device.add_newobj("graph_color_mode", "prepend set_color_mode", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[748, 262, 126, 20])
    device.add_line("scale_btn_lin", 0, "msg_scale_idx_lin", 0)
    device.add_line("scale_btn_log", 0, "msg_scale_idx_log", 0)
    device.add_line("scale_btn_st", 0, "msg_scale_idx_st", 0)
    device.add_line("msg_scale_idx_lin", 0, "scale_state", 0)
    device.add_line("msg_scale_idx_log", 0, "scale_state", 0)
    device.add_line("msg_scale_idx_st", 0, "scale_state", 0)
    device.add_line("scale_state", 0, "scale_eq_lin", 0)
    device.add_line("scale_state", 0, "scale_eq_log", 0)
    device.add_line("scale_state", 0, "scale_eq_st", 0)
    device.add_line("scale_eq_lin", 0, "set_scale_lin", 0)
    device.add_line("scale_eq_log", 0, "set_scale_log", 0)
    device.add_line("scale_eq_st", 0, "set_scale_st", 0)
    device.add_line("set_scale_lin", 0, "scale_btn_lin", 0)
    device.add_line("set_scale_log", 0, "scale_btn_log", 0)
    device.add_line("set_scale_st", 0, "scale_btn_st", 0)
    device.add_line("graph_state", 0, "graph_color_mode", 0)
    device.add_line("graph_color_mode", 0, "spec_display", 0)

    # Display range and Auto reset.
    device.add_newobj("range_pack", "pak 0. 1.", numinlets=2, numoutlets=1,
                      outlettype=["list"], patching_rect=[860, 234, 72, 20])
    device.add_newobj("range_msg", "prepend set_range", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[938, 234, 88, 20])
    device.add_newobj("auto_trigger", "t b b", numinlets=1, numoutlets=2,
                      outlettype=["bang", "bang"], patching_rect=[860, 262, 40, 20])
    device.add_newobj("auto_lo_default", "loadmess 0.", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[906, 262, 70, 20])
    device.add_newobj("auto_hi_default", "loadmess 1.", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[982, 262, 70, 20])
    device.add_line("auto_lo_default", 0, "range_lo_box", 0)
    device.add_line("auto_hi_default", 0, "range_hi_box", 0)
    device.add_line("auto_lo_default", 0, "range_pack", 0)
    device.add_line("auto_hi_default", 0, "range_pack", 1)
    device.add_line("range_lo_box", 1, "range_pack", 0)
    device.add_line("range_hi_box", 1, "range_pack", 1)
    device.add_line("range_pack", 0, "range_msg", 0)
    device.add_line("range_msg", 0, "spec_display", 0)
    device.add_line("auto_button", 0, "auto_trigger", 0)
    device.add_line("auto_trigger", 0, "auto_hi_default", 0)
    device.add_line("auto_trigger", 1, "auto_lo_default", 0)

    return device


def build(output_path=None):
    """Build the device to the Ableton User Library by default."""
    device = build_device()
    target = output_path or device_output_path("Spectrum Analyzer", "audio_effect")
    device.build(target)
    return target


if __name__ == "__main__":
    print(build())
