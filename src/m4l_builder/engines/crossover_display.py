"""Interactive narrow crossover graph for jsui (spectrum + draggable splits).

A compact, Pro-Q-style 3-band crossover the graph *is* the device:
  - a LIVE input spectrum behind the bands (fed by ``fft_analyzer_dsp`` via a
    ``buffer~``; the display polls it with a Task and rebins log-x),
  - two vertical crossover splits you DRAG on the graph. Each drag outlets the
    new Hz to a real ``live.dial`` (``low_xover`` / ``high_xover``) so Live
    records automation exactly like moving a knob.

The graph drives ONLY the two crossover splits (2 outlets, both crossover Hz);
per-band Solo (Listen) lives in the separate "S" buttons below the graph.

Inlets (5):
    0 -- low crossover Hz   (param back-sync -> redraw the low split)
    1 -- high crossover Hz  (param back-sync -> redraw the high split)
    2 -- MID / L+R analyzer: ``set_analyzer_buffer <name> <bins>`` + ``set_samplerate <hz>``
    3 -- SIDE analyzer:      ``set_analyzer_buffer2 <name> <bins>``
    4 -- stereo mode:        ``set_mode <0|1>`` (0 = Stereo one spectrum, 1 = Mid-Side two)

Outlets (2):
    0 -- low crossover Hz   (on drag)
    1 -- high crossover Hz  (on drag)
"""

from string import Template

CROSSOVER_DISPLAY_INLETS = 5
CROSSOVER_DISPLAY_OUTLETS = 2


def crossover_display_js(
    *,
    bg_color="0.05, 0.05, 0.06, 1.0",
    grid_color="0.22, 0.24, 0.28, 0.55",
    text_color="0.62, 0.66, 0.72, 1.0",
    line_color="0.92, 0.95, 0.98, 0.9",
    low_color="0.30, 0.58, 0.88, 0.26",
    mid_color="0.38, 0.78, 0.58, 0.22",
    high_color="0.92, 0.58, 0.28, 0.22",
    accent_color="0.96, 0.84, 0.40, 1.0",
    spec_fill="0.60, 0.66, 0.74, 0.34",
    spec_line="0.74, 0.80, 0.88, 0.85",
    side_fill="0.62, 0.44, 0.82, 0.20",
    side_line="0.72, 0.56, 0.92, 0.60",
):
    """Return JavaScript for an interactive spectrum-backed 3-band crossover.

    In Stereo mode the graph draws one spectrum (the MID / L+R fill). In Mid-Side
    mode it overlays two: the MID as the brighter ``spec_fill`` and the SIDE as a
    dimmer, tinted ``side_fill`` + ``side_line`` curve.
    """
    return _JS_TEMPLATE.substitute(
        bg_color=bg_color,
        grid_color=grid_color,
        text_color=text_color,
        line_color=line_color,
        low_color=low_color,
        mid_color=mid_color,
        high_color=high_color,
        accent_color=accent_color,
        spec_fill=spec_fill,
        spec_line=spec_line,
        side_fill=side_fill,
        side_line=side_line,
    )


_JS_TEMPLATE = Template("""\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 5;
outlets = 2;

var BG_COLOR     = [$bg_color];
var GRID_COLOR   = [$grid_color];
var TEXT_COLOR   = [$text_color];
var LINE_COLOR   = [$line_color];
var LOW_COLOR    = [$low_color];
var MID_COLOR    = [$mid_color];
var HIGH_COLOR   = [$high_color];
var ACCENT_COLOR = [$accent_color];
var SPEC_FILL    = [$spec_fill];
var SPEC_LINE    = [$spec_line];
var SIDE_FILL    = [$side_fill];
var SIDE_LINE    = [$side_line];

var MIN_FREQ  = 20.0;
var MAX_FREQ  = 20000.0;
var LOG_MIN   = Math.log(MIN_FREQ);
var LOG_MAX   = Math.log(MAX_FREQ);
var LOG_RANGE = LOG_MAX - LOG_MIN;

var MARGIN_LEFT   = 6;
var MARGIN_RIGHT  = 6;
var MARGIN_TOP    = 8;
var MARGIN_BOTTOM = 15;

// the two split params are range-limited so they can never cross.
var LOW_MIN = 40.0, LOW_MAX = 1200.0;
var HIGH_MIN = 1500.0, HIGH_MAX = 16000.0;

var low_xover = 160.0;
var high_xover = 3200.0;

// spectrum -- buffer 1 = MID / L+R, buffer 2 = SIDE (drawn only in Mid-Side mode)
var spec_buf = null;
var spec_bins = 0;
var spec_buf2 = null;
var spec_bins2 = 0;
var spec_sr = 44100.0;
var mags = [];
var mags2 = [];
var poll_task = null;
var stereo_mode = 0;         // 0 = Stereo (one spectrum), 1 = Mid-Side (two)
var SPEC_TOP_DB = 6.0;
var SPEC_BOT_DB = -80.0;

// interaction
var drag_target = -1;        // 0 = low handle, 1 = high handle
var HANDLE_HIT = 8.0;

var GRID_FREQS = [50, 100, 200, 500, 1000, 2000, 5000, 10000];
var LABEL_FREQS = [100, 1000, 10000];

function plot_left()   { return MARGIN_LEFT; }
function plot_right()  { return mgraphics.size[0] - MARGIN_RIGHT; }
function plot_top()    { return MARGIN_TOP; }
function plot_bottom() { return mgraphics.size[1] - MARGIN_BOTTOM; }
function plot_w()      { return plot_right() - plot_left(); }
function plot_h()      { return plot_bottom() - plot_top(); }

function set_rgba(c) { mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]); }

function clamp_low(f)  { if (f < LOW_MIN) return LOW_MIN; if (f > LOW_MAX) return LOW_MAX; return f; }
function clamp_high(f) { if (f < HIGH_MIN) return HIGH_MIN; if (f > HIGH_MAX) return HIGH_MAX; return f; }

function freq_to_x(freq) {
    var norm = (Math.log(freq) - LOG_MIN) / LOG_RANGE;
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;
    return plot_left() + norm * plot_w();
}

function x_to_freq(x) {
    var t = (x - plot_left()) / plot_w();
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    return Math.exp(LOG_MIN + t * LOG_RANGE);
}

function db_to_y(db) {
    var t = (SPEC_TOP_DB - db) / (SPEC_TOP_DB - SPEC_BOT_DB);
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    return plot_top() + t * plot_h();
}

function format_freq(freq) {
    if (freq >= 1000) {
        if (freq >= 10000) return (freq / 1000.0).toFixed(1) + "k";
        return (freq / 1000.0).toFixed(2) + "k";
    }
    return Math.round(freq) + "";
}

// ---- spectrum feed -------------------------------------------------------
function ensure_poll() {
    if (poll_task === null) {
        poll_task = new Task(poll_spectrum, this);
        poll_task.interval = 45;
        poll_task.repeat();
    }
}

function set_analyzer_buffer(name, bins) {    // MID / L+R
    spec_buf = new Buffer(name);
    spec_bins = bins;
    ensure_poll();
}

function set_analyzer_buffer2(name, bins) {   // SIDE (Mid-Side overlay)
    spec_buf2 = new Buffer(name);
    spec_bins2 = bins;
    ensure_poll();
}

function set_samplerate(hz) { if (hz > 0) spec_sr = hz; }

// stereo mode from the device: 0 = Stereo (one spectrum), 1 = Mid-Side (two).
function set_mode(v) { stereo_mode = (v > 0) ? 1 : 0; mgraphics.redraw(); }

function poll_spectrum() {
    var changed = 0;
    if (spec_buf !== null && spec_bins >= 2) {
        var got = spec_buf.peek(1, 0, spec_bins);
        if (got != null) { mags = (got.length === undefined) ? [got] : got; changed = 1; }
    }
    if (spec_buf2 !== null && spec_bins2 >= 2) {
        var got2 = spec_buf2.peek(1, 0, spec_bins2);
        if (got2 != null) { mags2 = (got2.length === undefined) ? [got2] : got2; changed = 1; }
    }
    if (changed) mgraphics.redraw();
}

// ---- drawing -------------------------------------------------------------
function draw_background() {
    set_rgba(BG_COLOR);
    mgraphics.rectangle(0, 0, mgraphics.size[0], mgraphics.size[1]);
    mgraphics.fill();
}

// Draw one spectrum as a filled area; if line_c is non-null, also stroke the
// outline (used for the tinted SIDE overlay in Mid-Side mode).
function draw_spectrum_buf(arr, bins, fill_c, line_c) {
    if (arr.length < 4) return;
    var pl = plot_left(), pb = plot_bottom();
    var binhz = spec_sr / (2.0 * bins);
    var started = 0;
    mgraphics.move_to(pl, pb);
    var i, f, x, db, y, m;
    for (i = 1; i < arr.length; i++) {
        f = i * binhz;
        if (f < MIN_FREQ) continue;
        if (f > MAX_FREQ) break;
        m = arr[i];
        if (m < 0) m = -m;
        db = 20.0 * Math.log(m + 1e-9) / Math.LN10;
        x = freq_to_x(f);
        y = db_to_y(db);
        if (!started) { mgraphics.line_to(x, pb); started = 1; }
        mgraphics.line_to(x, y);
    }
    if (!started) return;
    mgraphics.line_to(plot_right(), pb);
    mgraphics.close_path();
    set_rgba(fill_c);
    if (line_c === null) {
        mgraphics.fill();
    } else {
        mgraphics.fill_preserve();
        set_rgba(line_c);
        mgraphics.set_line_width(1.0);
        mgraphics.stroke();
    }
}

function draw_spectrum() {
    // Stereo: one MID / L+R fill. Mid-Side: MID fill (brighter) + SIDE overlay
    // (dimmer, tinted fill + line) so both spectra read at once.
    draw_spectrum_buf(mags, spec_bins, SPEC_FILL, null);
    if (stereo_mode === 1) {
        draw_spectrum_buf(mags2, spec_bins2, SIDE_FILL, SIDE_LINE);
    }
}

function draw_grid() {
    var i, x;
    set_rgba(GRID_COLOR);
    mgraphics.set_line_width(1.0);
    for (i = 0; i < GRID_FREQS.length; i++) {
        x = freq_to_x(GRID_FREQS[i]);
        mgraphics.move_to(x, plot_top());
        mgraphics.line_to(x, plot_bottom());
        mgraphics.stroke();
    }
    mgraphics.move_to(plot_left(), plot_bottom());
    mgraphics.line_to(plot_right(), plot_bottom());
    mgraphics.stroke();

    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(7.5);
    set_rgba(TEXT_COLOR);
    for (i = 0; i < LABEL_FREQS.length; i++) {
        x = freq_to_x(LABEL_FREQS[i]);
        mgraphics.move_to(x - 6, plot_bottom() + 11);
        mgraphics.show_text(LABEL_FREQS[i] >= 1000 ? (LABEL_FREQS[i] / 1000) + "k" : LABEL_FREQS[i] + "");
    }
}

function fill_region(x0, x1, color) {
    mgraphics.set_source_rgba(color[0], color[1], color[2], color[3]);
    mgraphics.rectangle(x0, plot_top(), x1 - x0, plot_h());
    mgraphics.fill();
}

function draw_regions(xl, xh) {
    fill_region(plot_left(), xl, LOW_COLOR);
    fill_region(xl, xh, MID_COLOR);
    fill_region(xh, plot_right(), HIGH_COLOR);
}

function draw_markers(xl, xh) {
    var yt = plot_top(), yb = plot_bottom();
    mgraphics.set_line_width(2.0);
    set_rgba(LINE_COLOR);
    mgraphics.move_to(xl, yt); mgraphics.line_to(xl, yb); mgraphics.stroke();
    mgraphics.move_to(xh, yt); mgraphics.line_to(xh, yb); mgraphics.stroke();

    set_rgba(ACCENT_COLOR);
    mgraphics.arc(xl, yb - 4, 3.5, 0, Math.PI * 2); mgraphics.fill();
    mgraphics.arc(xh, yb - 4, 3.5, 0, Math.PI * 2); mgraphics.fill();

    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(8.5);
    set_rgba([0.95, 0.97, 1.0, 0.95]);
    mgraphics.move_to(xl + 3, yb - 6);  mgraphics.show_text(format_freq(low_xover));
    mgraphics.move_to(xh + 3, yb - 6);  mgraphics.show_text(format_freq(high_xover));
}

function paint() {
    low_xover = clamp_low(low_xover);
    high_xover = clamp_high(high_xover);
    var xl = freq_to_x(low_xover);
    var xh = freq_to_x(high_xover);
    draw_background();
    draw_spectrum();
    draw_regions(xl, xh);
    draw_grid();
    draw_markers(xl, xh);
}

// ---- interaction ---------------------------------------------------------
function apply_drag(x) {
    var f = x_to_freq(x);
    if (drag_target === 0) {
        low_xover = clamp_low(f);
        outlet(0, low_xover);
    } else if (drag_target === 1) {
        high_xover = clamp_high(f);
        outlet(1, high_xover);
    }
    mgraphics.redraw();
}

function onclick(x, y, but, cmd, shift, capslock, option, ctrl) {
    drag_target = -1;
    var xl = freq_to_x(low_xover);
    var xh = freq_to_x(high_xover);
    if (Math.abs(x - xl) <= HANDLE_HIT) drag_target = 0;
    else if (Math.abs(x - xh) <= HANDLE_HIT) drag_target = 1;
    else drag_target = (Math.abs(x - xl) < Math.abs(x - xh)) ? 0 : 1;
    apply_drag(x);
}

function ondrag(x, y, but, cmd, shift, capslock, option, ctrl) {
    if (but === 0) { drag_target = -1; return; }
    if (drag_target < 0) return;
    apply_drag(x);
}

// ---- param back-sync (inlets 0/1/2) --------------------------------------
function msg_float(value) {
    if (inlet === 0) low_xover = clamp_low(value);
    else if (inlet === 1) high_xover = clamp_high(value);
    mgraphics.redraw();
}

function msg_int(value) { msg_float(value); }
""")
