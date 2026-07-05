"""Parametric EQ curve display with draggable nodes for jsui.

Generates JavaScript (ES5) for Max's jsui object, drawing a Pro-Q/EQ Eight
style multi-band EQ with draggable nodes and composite response rendering.

Communication uses 3 inlets and 4 outlets.

Inlet 0 messages:
    set_band band_idx freq gain q type enabled [motion] [dynamic] [dynamic_amount]
             [motion_rate] [motion_depth] [motion_direction]
    set_num_bands N
    set_selected band_idx
    set_motion band_idx enabled
    set_dynamic band_idx enabled
    set_dynamic_amount band_idx amount
    set_motion_rate band_idx hz
    set_motion_depth band_idx percent
    set_motion_direction band_idx degrees
    set_analyzer_buffer name bins   (spectrum DISPLAY polls this buffer~)
    set_pre_overlay 0|1             (dim pre-EQ spectrum behind the post trace; default 1)
    set_dyn_buffer name [bins]      (dynamic DETECTOR polls this pre-EQ buffer~;
                                     empty/none = fall back to the display buffer)

Inlet 1:
    sample-rate float (typically from dspstate~ outlet 1)

Inlet 2:
    analyzer magnitude list in dB (typically -72..0 dB, log-spaced bins)

Outlet 0:
    selected_band band_idx
    add_band band_idx freq gain q type enabled
    delete_band band_idx
    band_type band_idx type
    band_enable band_idx enabled
    band_motion band_idx enabled
    band_dynamic band_idx enabled
    band_dynamic_amount band_idx amount
    band_motion_rate band_idx hz
    band_motion_depth band_idx percent
    band_motion_direction band_idx degrees
Outlet 1: band_freq band_idx freq
Outlet 2: band_gain band_idx gain
Outlet 3: band_q band_idx q

Mouse interaction:
    Click node: select band
    Drag node: adjust frequency and gain for bell/shelf filters
    Drag cut/notch/BP nodes: frequency horizontal, Q vertical
    Drag dynamic handle: adjust per-band dynamic range
    Mouse wheel on node: adjust Q
    Shift + drag / wheel: fine-tune (Pro-Q)
    Cmd/Ctrl + drag (vertical): adjust Q (Pro-Q)
    Alt + drag: constrain to one axis - horizontal = freq, vertical = gain/Q (Pro-Q)
    Alt + click a node: toggle that band's bypass (a tap; an Alt+drag constrains instead)
    Right-click node: open node menu for type / Motion / Dynamic / bypass / delete
    Double-click empty graph: add first disabled band at cursor
    Opt/Alt + click node: disable that band
"""

from string import Template

from ._graph_colors import (
    DEFAULT_GRAPH_PLOT_BORDER_COLOR,
    DEFAULT_GRAPH_PLOT_COLOR,
    band_palette_js,
    resolve_graph_panel_color,
)
from .design_system import design_system_js
from .graph_core import GRAPH_CORE_JS

EQ_CURVE_INLETS = 3
EQ_CURVE_OUTLETS = 4


def eq_curve_js(
    *,
    bg_color=DEFAULT_GRAPH_PLOT_COLOR,
    panel_color=None,
    plot_border_color=DEFAULT_GRAPH_PLOT_BORDER_COLOR,
    composite_color="0.85, 0.88, 0.92, 1.0",
    fill_color="0.45, 0.75, 0.65, 0.12",
    analyzer_fill_color="0.24, 0.78, 0.92, 0.12",
    analyzer_line_color="0.32, 0.84, 0.96, 0.48",
    analyzer_peak_color="0.92, 0.96, 1.0, 0.9",
    # EQ8-style spectrum colour: a muted grey for the heavy solid fill + thin line
    # used when the device flips to the "Ableton EQ Eight" look (vs the Rainbow
    # cyan line). Selected at runtime by set_analyzer_style 0|1.
    analyzer_eq8_color="0.70, 0.73, 0.78, 1.0",
    grid_color="0.2, 0.2, 0.22, 0.5",
    grid_color_light="0.16, 0.16, 0.19, 0.4",   # minor (2-9) decade lines — dimmer than grid_color (major decades)
    text_color="0.5, 0.5, 0.52, 1.0",
    zero_line_color="0.3, 0.3, 0.32, 0.8",
    # No boost: combined with the +12 dB headroom above, a loud signal lands
    # ~80% up as a backdrop, not pegged at the top. Was 18 (way too hot).
    analyzer_trim_db=0.0,
    # When True, an EXTERNAL compiled spectrum (e.g. Max's spectroscope~) is
    # drawn BEHIND this jsui, so the jsui skips its own opaque plot background
    # AND its hand-drawn spectrum/snapshot — leaving a transparent overlay that
    # draws only the grid + curve + bands on top of the external spectrum. The
    # FFT poll still runs (snap-to-peak grab + dynamic-EQ detection need the data).
    external_spectrum=False,
    # When True, draw a MINIMAL dB grid: only the 0 dB reference line + the
    # top/bottom range labels — no interior dB lines. Declutters the graph so the
    # axis labels read over a busy spectrum behind (freq lines/labels unchanged).
    minimal_grid=False,
):
    """Return JavaScript source for an interactive parametric EQ display.

    ``analyzer_trim_db`` lifts raw ``fft_frame`` magnitudes into the display's
    -72..0 dB window (2/N-normalized FFT bins of typical program material sit
    well below 0 dB). Ignored for the legacy dB-list analyzer path.
    """
    panel_color = resolve_graph_panel_color(bg_color, panel_color)
    return design_system_js() + "\n" + _JS_TEMPLATE.substitute(
        bg_color=bg_color,
        panel_color=panel_color,
        plot_border_color=plot_border_color,
        composite_color=composite_color,
        fill_color=fill_color,
        analyzer_fill_color=analyzer_fill_color,
        analyzer_line_color=analyzer_line_color,
        analyzer_peak_color=analyzer_peak_color,
        analyzer_eq8_color=analyzer_eq8_color,
        grid_color=grid_color,
        grid_color_light=grid_color_light,
        text_color=text_color,
        zero_line_color=zero_line_color,
        analyzer_trim_db=analyzer_trim_db,
        external_spectrum=(1 if external_spectrum else 0),
        minimal_grid=(1 if minimal_grid else 0),
        band_colors=band_palette_js(),
    ).replace("//__GRAPH_CORE__//", GRAPH_CORE_JS)


_JS_TEMPLATE = Template("""\
// Parametric EQ Curve Display - generated by m4l-builder
// ES5 compatible, no let/const/arrow/template literals

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 3;
outlets = 4;

// ── Configurable colors ──────────────────────────────────────────────
var BG_COLOR       = [$bg_color];
var PANEL_CLR      = [$panel_color];
var PLOT_BORDER_CLR = [$plot_border_color];
var COMPOSITE_CLR  = [$composite_color];
var FILL_CLR       = [$fill_color];
var ANALYZER_FILL_CLR = [$analyzer_fill_color];
var ANALYZER_LINE_CLR = [$analyzer_line_color];
var ANALYZER_PEAK_CLR = [$analyzer_peak_color];
var ANALYZER_EQ8_CLR  = [$analyzer_eq8_color];   // muted grey for the EQ8-style fill
var GRID_CLR       = [$grid_color];
var GRID_LIGHT_CLR = [$grid_color_light];
var TEXT_CLR       = [$text_color];
var ZERO_LINE_CLR  = [$zero_line_color];

var BAND_COLORS = $band_colors;
var MOTION_CLR = [0.34, 0.88, 0.96, 1.0];
var DYNAMIC_CLR = [0.98, 0.72, 0.26, 1.0];
var MENU_BG_CLR = [0.09, 0.10, 0.12, 0.96];
var MENU_SURFACE_CLR = [0.13, 0.14, 0.17, 0.98];
var MENU_BORDER_CLR = [0.24, 0.28, 0.34, 1.0];
var MENU_DISABLED_CLR = [0.14, 0.15, 0.17, 0.94];

// ── Filter types ─────────────────────────────────────────────────────
var TYPE_PEAK     = 0;
var TYPE_LOSHELF  = 1;
var TYPE_HISHELF  = 2;
var TYPE_LOWPASS  = 3;
var TYPE_HIGHPASS = 4;
var TYPE_NOTCH    = 5;
var TYPE_BANDPASS = 6;
var TYPE_ALLPASS  = 7;

var TYPE_NAMES = ["Peak", "LShelf", "HShelf", "LP", "HP", "Notch", "BP", "AllPass"];
var TYPE_SHORT_NAMES = ["PK", "LS", "HS", "LP", "HP", "NT", "BP", "AP"];
// ── Constants ────────────────────────────────────────────────────────
var MIN_FREQ      = 10;
var MAX_FREQ      = 22000;
var MIN_GAIN      = -30;
var MAX_GAIN      = 30;
var DISPLAY_FLOOR = -30;
var display_range = 15.0;
var MIN_Q         = 0.1;
var MAX_Q         = 30.0;
var NUM_POINTS    = 768;
var NODE_RADIUS     = 6.5;
var NODE_RADIUS_SEL = 8.5;
var HIT_RADIUS      = 18;
var DYNAMIC_HANDLE_RADIUS = 5.2;
var DYNAMIC_HIT_RADIUS = 15.0;
var MAX_DYNAMIC_RANGE = 18.0;
// When a band is dynamic-enabled but its range is ~0 the ring would sit exactly
// on the node, making node-vs-ring grabs ambiguous (the drag_mode flicker). Draw
// + hit-test the ring at this visible default offset (dB) from the node so it is
// reliably grabbable and visually distinct. Sign is opposite the node gain (a
// boost band previews a downward/compress ring; a cut previews an upward ring) —
// the same convention the menu's Dynamic-enable default uses.
var DYNAMIC_DEFAULT_OFFSET = 6.0;
// Ring vs node arbitration dead-zone (px^2). The ring only wins a press when it
// is hit AND it is at least this much closer (squared) than the node — small
// mouse jitter near the node can no longer flip drag_mode between gain and ring.
var DYNAMIC_GRAB_BIAS_SQ = 9.0;
var MAX_BANDS       = 8;
var DEFAULT_SR      = 48000.0;
var ANALYZER_MIN_DB = -78.0;
// Ceiling at 0 dBFS (matches our Spectrum Analyzer's MIN_DB=-78/MAX_DB=0, which
// fills the body to the top). The old +12 headroom reserved 12 dB above 0 that
// real audio never reaches, so the spectrum sat squished at the vertical centre
// (Rainbow uses +18 but its FFT runs hotter; ours needs the realistic 0 ceiling).
var ANALYZER_MAX_DB = 0.0;
var ANALYZER_BINS   = 512;        // log-spaced display points (was 256 -> too blocky on a wide graph; 512 ~= 1.5px/segment, FabFilter-smooth)
var ANALYZER_RCORNERS = 4.0;      // path_roundcorners radius (Rainbow spectRCorners=4): rounds the max-per-column polyline into Rainbow's smooth line instead of Catmull-Rom grass
var ANALYZER_TRIM_DB = $analyzer_trim_db;
var EXTERNAL_SPECTRUM = $external_spectrum;   // 1 = a compiled spectrum (spectroscope~) draws behind; skip jsui bg + spectrum
var MINIMAL_GRID = $minimal_grid;   // 1 = only the 0 dB line + range labels (no interior dB lines)
// Spectrum Grab (Pro-Q): a plain press over an analyzer peak louder than this
// spawns a band right at that frequency and starts dragging it. The floor sits
// near ANALYZER_MIN_DB so this cleanly distinguishes a real resonance.
var SPECTRUM_GRAB_DB = -48.0;
var LOG_MIN         = Math.log(MIN_FREQ);
var LOG_MAX         = Math.log(MAX_FREQ);
var LOG_RANGE       = LOG_MAX - LOG_MIN;
var REDRAW_INTERVAL_MS = 33;
var DOUBLE_CLICK_MS = 320;

// ── Margin / padding for axis labels ─────────────────────────────────
var MARGIN_LEFT   = 20;
var MARGIN_RIGHT  = 8;
var MARGIN_TOP    = 6;
var MARGIN_BOTTOM = 12;

// ── State ────────────────────────────────────────────────────────────
var sample_rate = DEFAULT_SR;
var analyzer_enabled = 1;
var ANALYZER_STYLE = 0;   // 0 = Rainbow (thin colour line + light wash); 1 = EQ8 (heavy grey fill, smoothed)
// Display-domain spectrum tilt around a 1 kHz pivot (SPAN/Pro-Q style):
// +4.5 dB/oct makes pink noise read ~flat behind the curve. Pure render
// transform — never touches the audio path. Freeze halts the ballistics and
// holds the last frame (a snapshot to EQ against).
var analyzer_slope_db_oct = 0.0;
var analyzer_frozen = 0;
var num_bands = 0;
var selected_band = -1;
var hover_band = -1;
var hover_x = -1.0;
var hover_y = -1.0;
var hover_in_plot = 0;
// Cursor feedback + node glow come from the shared design-system snippet
// (ds_set_cursor / DS_CUR_* / ds_node_glow), prepended to this script.
var dragging = 0;
var drag_mode = 0;
// EQ Sketch (draw-to-EQ): with sketch_mode on, a drag across the plot records a
// freehand target curve; on release the prominent peaks/dips become bell bands.
var sketch_mode = 0;
var sketching = 0;
var sketch_x = [];   // captured plot x's
var sketch_g = [];   // captured gains (dB) at those x's
var drag_start_freq = 0;
var drag_start_gain = 0;
var drag_start_q = 1.0;
var drag_start_dynamic = 0.0;
// Pro-Q Alt gestures: drag_start_x/y anchor the axis-constrain; alt_drag_pending
// marks a press that began with Alt held on a node (decide bypass-toggle vs
// constrain on release); alt_moved flips once the drag travels; constrain_axis is
// 0 undecided / 1 horizontal (freq) / 2 vertical (gain or Q).
var drag_start_x = 0;
var drag_start_y = 0;
var alt_drag_pending = 0;
var alt_moved = 0;
var constrain_axis = 0;
var menu_band = -1;
var menu_x = 0;
var menu_y = 0;
var menu_hover = "";
var redraw_task = null;
var redraw_task_running = 0;
var last_redraw_ms = 0;
var last_click_ms = 0;
var last_click_band = -1;
var last_pointer_press_ms = 0;
var last_pointer_press_x = 0;
var last_pointer_press_y = 0;
var suppress_next_click = 0;
var suppress_next_ondblclick_delete = 0;

var bands = [];
var band_cache = [];
var analyzer_display = [];
var analyzer_peaks = [];
var analyzer_snapshot = [];   // it173: captured A/B reference of the analyzer, or empty
var i;
for (i = 0; i < MAX_BANDS; i++) {
    bands[i] = {
        present: 0,
        freq: 1000,
        gain: 0,
        q: 1.0,
        type: TYPE_PEAK,
        enabled: 0,
        motion: 0,
        dynamic: 0,
        dynamic_amount: 0.0,
        dynamic_current: 0.0,
        dynamic_env: 0.0,
        motion_rate: default_motion_rate(i),
        motion_depth: default_motion_depth(i),
        motion_direction: default_motion_direction(i)
    };
    band_cache[i] = {
        idx: i,
        present: 0,
        enabled: 0,
        freq: 1000,
        gain: 0,
        q: 1.0,
        type: TYPE_PEAK,
        motion: 0,
        dynamic: 0,
        dynamic_amount: 0.0,
        motion_rate: default_motion_rate(i),
        motion_depth: default_motion_depth(i),
        motion_direction: default_motion_direction(i),
        node_gain: 0,
        uses_gain: 1,
        coeffs: [1, 0, 0, 1, 0, 0]
    };
}

// ── Coordinate helpers ───────────────────────────────────────────────
function plot_left()   { return MARGIN_LEFT; }
function plot_right()  { return mgraphics.size[0] - MARGIN_RIGHT; }
function plot_top()    { return MARGIN_TOP; }
function plot_bottom() { return mgraphics.size[1] - MARGIN_BOTTOM; }
function plot_w()      { return plot_right() - plot_left(); }
function plot_h()      { return plot_bottom() - plot_top(); }
function point_in_plot(x, y) {
    return x >= plot_left() && x <= plot_right() && y >= plot_top() && y <= plot_bottom();
}

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function safe_log10(v) {
    if (v <= 1.0e-20) v = 1.0e-20;
    return Math.log(v) / Math.log(10);
}

function default_motion_rate(idx) {
    var defaults = [0.18, 0.27, 0.39, 0.56, 0.80, 1.12, 1.48, 1.92];
    idx = Math.floor(idx);
    if (idx >= 0 && idx < defaults.length) return defaults[idx];
    return 0.56;
}

function default_motion_depth(idx) {
    var defaults = [18.0, 24.0, 30.0, 36.0, 44.0, 52.0, 60.0, 68.0];
    idx = Math.floor(idx);
    if (idx >= 0 && idx < defaults.length) return defaults[idx];
    return 36.0;
}

function default_motion_direction(idx) {
    var defaults = [0, 35, 70, 120, 165, 215, 285, 330];
    idx = Math.floor(idx);
    if (idx >= 0 && idx < defaults.length) return defaults[idx];
    return 0.0;
}

function clamp_motion_direction(value) {
    if (value === undefined || value !== value) return 0.0;
    while (value < 0.0) value += 360.0;
    while (value >= 360.0) value -= 360.0;
    return clamp(value, 0.0, 359.0);
}

//__GRAPH_CORE__//

// x_to_freq: moved to the shared graph_core include (T25)

function gain_to_y(g) {
    var hi = display_range;
    var lo = -display_range;
    var norm = (clamp(g, lo, hi) - hi) / (lo - hi);
    return plot_top() + norm * plot_h();
}

function y_to_gain(y) {
    var norm = (y - plot_top()) / plot_h();
    norm = clamp(norm, 0, 1);
    var hi = display_range;
    var lo = -display_range;
    return hi + norm * (lo - hi);
}

function q_to_y(q) {
    var norm = (Math.log(clamp(q, MIN_Q, MAX_Q)) - Math.log(MIN_Q))
        / (Math.log(MAX_Q) - Math.log(MIN_Q));
    return plot_bottom() - norm * plot_h();
}

function y_to_q(y) {
    var norm = (plot_bottom() - y) / plot_h();
    norm = clamp(norm, 0, 1);
    return Math.exp(Math.log(MIN_Q) + norm * (Math.log(MAX_Q) - Math.log(MIN_Q)));
}

function analyzer_db_to_y(db) {
    var clamped = clamp(db, ANALYZER_MIN_DB, ANALYZER_MAX_DB);
    var norm = (clamped - ANALYZER_MIN_DB) / (ANALYZER_MAX_DB - ANALYZER_MIN_DB);
    return plot_bottom() - norm * plot_h();
}

function analyzer_bin_freq(idx, count) {
    var norm = idx / Math.max(count - 1, 1);
    return Math.exp(LOG_MIN + norm * LOG_RANGE);
}

// dB offset added to a bin at the draw stage for the display tilt. Zero is the
// fast path (no tilt). Pivot at 1 kHz so the slope rotates the spectrum about
// 1k: lows pulled down, highs lifted (or vice versa for a negative slope).
function analyzer_slope_at(freq) {
    if (analyzer_slope_db_oct === 0.0) return 0.0;
    return analyzer_slope_db_oct *
        (Math.log(clamp(freq, MIN_FREQ, MAX_FREQ) / 1000.0) / Math.LN2);
}

// Display dB for a bin: a bin at the noise floor (no signal) STAYS at the floor
// so the tilt can't lift the empty floor into a fake rising diagonal; a bin with
// real energy gets the display tilt added.
function analyzer_tilted_db(raw_db, tilt) {
    return (raw_db <= ANALYZER_MIN_DB + 0.5) ? ANALYZER_MIN_DB : raw_db + tilt;
}

// A real spectrum always has structure (peaks, rolloff); a PERFECTLY FLAT line
// across all bins is a no-signal artifact (digital-silence FFT or an unfed/
// uninitialized analyzer buffer) — drawn through the tilt it becomes a fake
// rising diagonal. Detect it (tiny bin-to-bin range) so the spectrum can be
// skipped entirely (reads empty, like Pro-Q with no audio).
function analyzer_is_flat() {
    var n = analyzer_display.length, i;
    if (n < 2) return 1;
    var lo = analyzer_display[0], hi = analyzer_display[0];
    for (i = 1; i < n; i++) {
        if (analyzer_display[i] < lo) lo = analyzer_display[i];
        if (analyzer_display[i] > hi) hi = analyzer_display[i];
    }
    // Effective silence: even with residual bin spread (smoothing/averaging
    // keeps a couple dB of wiggle at the floor), if the LOUDEST bin is still
    // near the floor there is nothing to show — the old floor-band rendered
    // as a fake grey bar hugging the plot bottom (user-flagged).
    if (hi < ANALYZER_MIN_DB + 12.0) return 1;
    return (hi - lo < 1.5) ? 1 : 0;
}

function now_ms() {
    return new Date().getTime();
}

function force_redraw() {
    last_redraw_ms = now_ms();
    mgraphics.redraw();
}

function request_redraw() {
    var now = now_ms();
    if (now - last_redraw_ms < REDRAW_INTERVAL_MS) return;
    last_redraw_ms = now;
    mgraphics.redraw();
}

function has_motion_animation() {
    var idx;
    for (idx = 0; idx < num_bands; idx++) {
        if (band_cache[idx].enabled && band_cache[idx].motion) return 1;
    }
    return 0;
}

function animation_tick() {
    // Driven by a repeating Task (interval+repeat — schedule() no-ops in Live).
    if (!has_motion_animation()) {
        if (redraw_task && redraw_task_running) redraw_task.cancel();
        redraw_task_running = 0;
        return;
    }
    request_redraw();
}

function refresh_animation_task() {
    if (!redraw_task && typeof Task !== "undefined") {
        redraw_task = new Task(animation_tick, this);
    }
    if (has_motion_animation()) {
        if (redraw_task && !redraw_task_running) {
            redraw_task_running = 1;
            redraw_task.interval = REDRAW_INTERVAL_MS;
            redraw_task.repeat();
        }
        return;
    }
    if (redraw_task && redraw_task_running) {
        redraw_task.cancel();
        redraw_task_running = 0;
    }
}

function update_analyzer_data(values) {
    var i, n, incoming;
    if (analyzer_frozen) return;   // hold the snapshot
    n = values.length;
    if (n < 2) {
        analyzer_display = [];
        analyzer_peaks = [];
        request_redraw();
        return;
    }

    if (analyzer_display.length !== n) {
        analyzer_display = [];
        analyzer_peaks = [];
        for (i = 0; i < n; i++) {
            analyzer_display[i] = ANALYZER_MIN_DB;
            analyzer_peaks[i] = ANALYZER_MIN_DB;
        }
    }

    for (i = 0; i < n; i++) {
        incoming = values[i];
        if (incoming !== incoming || incoming === undefined) incoming = ANALYZER_MIN_DB;
        incoming = clamp(incoming, ANALYZER_MIN_DB, ANALYZER_MAX_DB);
        analyzer_display[i] = analyzer_display[i] * 0.55 + incoming * 0.45;
        if (analyzer_display[i] > analyzer_peaks[i]) {
            analyzer_peaks[i] = analyzer_display[i];
        } else {
            analyzer_peaks[i] = Math.max(ANALYZER_MIN_DB, analyzer_peaks[i] - 0.38);
        }
    }
    request_redraw();
}

// Raw FFT magnitude frame (fft_frame): linear-spaced, linear-magnitude bins.
// Rebin into a fixed set of log-spaced display bins so the analyzer always has
// ANALYZER_BINS entries (no blank-out when the FFT size changes), and so the
// log frequency axis is correct (raw FFT bins are linear in Hz).
function ensure_analyzer_arrays() {
    var i;
    if (analyzer_display.length === ANALYZER_BINS) return;
    analyzer_display = [];
    analyzer_peaks = [];
    for (i = 0; i < ANALYZER_BINS; i++) {
        analyzer_display[i] = ANALYZER_MIN_DB;
        analyzer_peaks[i] = ANALYZER_MIN_DB;
    }
}

// Shared Rainbow/Ableton MAX-per-pixel-COLUMN rebin (the Spectrum Analyzer v42
// algorithm) — used by BOTH the post-EQ display path and the pre-EQ overlay so
// the two traces are column-for-column comparable. Returns ANALYZER_BINS dB
// columns (floor-filled), or null when the frame is unusable.
function rebin_fft_to_columns(mags) {
    var m = mags.length;
    if (m < 4) return null;
    // Rainbow/Ableton MAX-per-pixel-COLUMN rebin (the Spectrum Analyzer v42 algorithm,
    // ground-truth-verified vs Ableton Spectrum + EQ8): forward-map every linear FFT
    // bin to its LOG display column and keep the MAX bin per column; interpolate the
    // sparse low columns. Replaces the old wide-cell band (which blobbed the lows /
    // plateaued the mids). Lows smooth (~1 bin/col -> line between bins), highs peaky
    // (many bins/col -> max rides the partials). NO frequency averaging, NO tilt.
    var nyq = sample_rate * 0.5;
    var fmin = Math.exp(LOG_MIN), fmax = Math.exp(LOG_MIN + LOG_RANGE);
    var i, b, a, k, col = [];
    for (i = 0; i < ANALYZER_BINS; i++) col[i] = -999.0;   // -999 = empty column
    for (b = 1; b < m; b++) {
        var f = nyq * b / (m - 1);
        if (f < fmin || f > fmax) continue;
        var px = Math.round(((Math.log(f) - LOG_MIN) / LOG_RANGE) * (ANALYZER_BINS - 1));
        if (px < 0) px = 0; else if (px > ANALYZER_BINS - 1) px = ANALYZER_BINS - 1;
        var mag = mags[b]; if (mag < 0.0) mag = -mag; if (mag !== mag) mag = 0.0;
        var db = mag > 1e-9 ? (20.0 * Math.log(mag) / Math.LN10) : ANALYZER_MIN_DB;
        db += ANALYZER_TRIM_DB;
        if (db > col[px]) col[px] = db;     // MAX per column
    }
    // Fill empty low columns (<1 bin/column) by linear interpolation between filled
    // neighbours (Rainbow joins its sparse low points with line_to).
    var lastIdx = -1, lastVal = ANALYZER_MIN_DB;
    for (i = 0; i < ANALYZER_BINS; i++) {
        if (col[i] > -998.0) {
            if (lastIdx < 0) { for (a = 0; a < i; a++) col[a] = col[i]; }
            else if (i - lastIdx > 1) {
                for (k = lastIdx + 1; k < i; k++)
                    col[k] = lastVal + (col[i] - lastVal) * (k - lastIdx) / (i - lastIdx);
            }
            lastIdx = i; lastVal = col[i];
        }
    }
    if (lastIdx < 0) { for (i = 0; i < ANALYZER_BINS; i++) col[i] = ANALYZER_MIN_DB; }
    else { for (i = lastIdx + 1; i < ANALYZER_BINS; i++) col[i] = lastVal; }
    return col;
}

function update_analyzer_from_fft(mags) {
    if (analyzer_frozen) return;   // hold the snapshot
    var col = rebin_fft_to_columns(mags);
    if (col === null) return;
    ensure_analyzer_arrays();
    // Ballistics: instant attack, slewed release (no rise smoothing).
    var i;
    for (i = 0; i < ANALYZER_BINS; i++) {
        var v = clamp(col[i], ANALYZER_MIN_DB, ANALYZER_MAX_DB);
        if (v >= analyzer_display[i]) analyzer_display[i] = v;
        else analyzer_display[i] = analyzer_display[i] * 0.82 + v * 0.18;
        if (analyzer_display[i] > analyzer_peaks[i]) analyzer_peaks[i] = analyzer_display[i];
        else analyzer_peaks[i] = Math.max(ANALYZER_MIN_DB, analyzer_peaks[i] - 0.22);
    }
    request_redraw();
}

// ── PRE-EQ overlay (Pro-Q 3 grammar): the dedicated pre-EQ detector buffer is
// rebinned with the SAME column algorithm and drawn as a dim neutral backdrop
// behind the live post-EQ spectrum, so cuts/boosts read as pre-vs-post daylight.
var pre_overlay = 1;            // set_pre_overlay 0|1 (default ON)
var pre_display = [];
function update_pre_from_fft(mags) {
    if (analyzer_frozen) return;
    var col = rebin_fft_to_columns(mags);
    if (col === null) return;
    var i;
    if (pre_display.length !== ANALYZER_BINS) {
        pre_display = [];
        for (i = 0; i < ANALYZER_BINS; i++) pre_display[i] = ANALYZER_MIN_DB;
    }
    for (i = 0; i < ANALYZER_BINS; i++) {
        var v = clamp(col[i], ANALYZER_MIN_DB, ANALYZER_MAX_DB);
        if (v >= pre_display[i]) pre_display[i] = v;
        else pre_display[i] = pre_display[i] * 0.82 + v * 0.18;
    }
}

function set_pre_overlay(v) {
    pre_overlay = v ? 1 : 0;
    request_redraw();
}

function pre_smooth_at(i, n) {
    var R = 1, acc = 0.0, wsum = 0.0, k, idx, w;
    for (k = -R; k <= R; k++) {
        idx = i + k;
        if (idx < 0) idx = 0; else if (idx >= n) idx = n - 1;
        w = (R + 1) - (k < 0 ? -k : k);
        acc += pre_display[idx] * w;
        wsum += w;
    }
    return acc / wsum;
}

function pre_is_flat() {
    var n = pre_display.length, i;
    if (n < 2) return true;
    for (i = 0; i < n; i++) {
        if (pre_display[i] > ANALYZER_MIN_DB + 1.5) return false;
    }
    return true;
}

// Dim neutral pre-EQ trace — fill-only wash + a quiet grey edge, drawn BEFORE
// the live post spectrum (never over it). Respects the display tilt so the
// pre/post pair stays comparable at any slope setting.
function draw_analyzer_pre() {
    if (!pre_overlay || !analyzer_enabled) return;
    if (dyn_buffer_name === "") return;      // no dedicated pre tap on this device
    var n = pre_display.length, k, freq, tilt;
    if (n < 2 || pre_is_flat()) return;
    var left = plot_left(), right = plot_right();
    var bottom = plot_bottom(), top = plot_top();
    var sx = [], sy = [];
    for (k = 0; k < n; k++) {
        freq = analyzer_bin_freq(k, n);
        tilt = analyzer_slope_at(freq);
        sx[k] = freq_to_x(freq);
        sy[k] = analyzer_db_to_y(analyzer_tilted_db(pre_smooth_at(k, n), tilt));
    }
    var grad = mgraphics.pattern_create_linear(left, top, left, bottom);
    grad.add_color_stop_rgba(0.0, 0.62, 0.66, 0.72, 0.05);
    grad.add_color_stop_rgba(1.0, 0.62, 0.66, 0.72, 0.13);
    mgraphics.set_source(grad);
    mgraphics.move_to(sx[0], bottom + 2);
    for (k = 0; k < n; k++) mgraphics.line_to(sx[k], sy[k]);
    mgraphics.line_to(sx[n - 1], bottom + 2);
    mgraphics.close_path();
    mgraphics.path_roundcorners(ANALYZER_RCORNERS);
    mgraphics.fill();
    mgraphics.set_source_rgba(0.62, 0.66, 0.72, 0.35);
    mgraphics.set_line_width(1.0);
    for (k = 0; k < n; k++) {
        if (k === 0) mgraphics.move_to(sx[k], sy[k]);
        else mgraphics.line_to(sx[k], sy[k]);
    }
    mgraphics.path_roundcorners(ANALYZER_RCORNERS);
    mgraphics.stroke();
}

// Draw-time triangular smoothing of the analyzer (read-only -> never compounds
// across frames, unlike smoothing the temporal analyzer_display state itself).
// Rounds the wide-cell max-envelope plateaus into a clean curve.
function analyzer_smooth_at(i, n) {
    var R = 1, acc = 0.0, wsum = 0.0, k, idx, w;
    for (k = -R; k <= R; k++) {
        idx = i + k;
        if (idx < 0) idx = 0; else if (idx >= n) idx = n - 1;
        w = (R + 1) - (k < 0 ? -k : k);
        acc += analyzer_display[idx] * w;
        wsum += w;
    }
    return acc / wsum;
}

function fft_frame() {
    update_analyzer_from_fft(arrayfromargs(arguments));
}

function set_samplerate(hz) {
    if (hz > 1000.0 && hz < 768000.0) {
        sample_rate = hz;
        rebuild_band_cache();
        request_redraw();
    }
}

// Buffer-polling analyzer source: the fft_analyzer backend pokes magnitudes
// into a named buffer~ every spectral frame; we read it on a ~30fps clock.
// (Scheduler-message frames proved unreliable in Live — see fft_analyzer.py.)
var analyzer_buffer_name = "";
var analyzer_buffer_bins = 0;
var analyzer_poll_task = null;

// Optional DEDICATED detector buffer (a pre-EQ tap). When set via
// set_dyn_buffer, the dynamic detector reads THIS buffer instead of the
// post-EQ display buffer, so a dynamic cut does not pull down the level it
// reacts to. Empty = fall back to the display buffer (other devices unchanged).
var dyn_buffer_name = "";
var dyn_buffer_bins = 0;

// Read fft_size/2 linear magnitudes from a named buffer~. Returns null if the
// name is empty or the buffer~ is not instantiated yet (retry next tick).
function read_buffer_frame(nm, bins) {
    if (nm === "") return null;
    try {
        var b = new Buffer(nm);
        var n = bins > 0 ? bins : 1024;
        return b.peek(1, 0, n);
    } catch (e) {
        return null;
    }
}

function poll_analyzer_buffer() {
    if (analyzer_buffer_name === "" && dyn_buffer_name === "") return;
    var vals = read_buffer_frame(analyzer_buffer_name, analyzer_buffer_bins);
    // Spectrum display reads ONLY the (post-EQ) display buffer, gated by enable.
    if (vals && vals.length >= 4 && analyzer_enabled) update_analyzer_from_fft(vals);
    // Dynamic detector: read the DEDICATED pre-EQ buffer when one is set, else
    // fall back to the display buffer so other eq_curve devices are unchanged.
    var dyn_vals = dyn_buffer_name !== "" ? read_buffer_frame(dyn_buffer_name, dyn_buffer_bins) : null;
    // Pre/post overlay: the dedicated pre-EQ tap doubles as the PRE trace.
    if (dyn_vals && dyn_vals.length >= 4 && analyzer_enabled && pre_overlay) {
        update_pre_from_fft(dyn_vals);
    }
    if (dyn_vals === null) dyn_vals = vals;
    if (dyn_vals && dyn_vals.length >= 4) {
        if (update_dynamic_from_fft(dyn_vals)) request_redraw();
    }
}

function start_analyzer_poll() {
    if (analyzer_poll_task !== null) return;
    if (typeof Task !== "undefined") {
        analyzer_poll_task = new Task(poll_analyzer_buffer);
        analyzer_poll_task.interval = 33;
        analyzer_poll_task.repeat();
    } else if (typeof setInterval !== "undefined") {
        analyzer_poll_task = setInterval(poll_analyzer_buffer, 33);
    }
}

function set_analyzer_buffer(name, bins) {
    analyzer_buffer_name = "" + name;
    analyzer_buffer_bins = bins ? Math.floor(bins) : 0;
    start_analyzer_poll();
}

// Point the DYNAMIC detector at its own (pre-EQ) buffer~, separate from the
// post-EQ spectrum display buffer. Send with no name (or 'none'/'0') to clear
// it and fall back to the display buffer. Shares the one analyzer poll Task.
function set_dyn_buffer(name, bins) {
    var nm = (name === undefined) ? "" : "" + name;
    if (nm === "none" || nm === "0") nm = "";
    dyn_buffer_name = nm;
    dyn_buffer_bins = bins ? Math.floor(bins) : 0;
    start_analyzer_poll();
}

// Display tilt (dB/oct around 1 kHz). Render-only; no outlet, no audio effect.
function set_analyzer_slope(v) {
    if (v === undefined || v !== v) return;
    analyzer_slope_db_oct = clamp(v, -12.0, 12.0);
    request_redraw();
}

// Freeze/thaw the analyzer. Frozen holds the last frame (the update guards
// no-op) so you can EQ against a captured spectrum; thaw resumes ballistics.
function set_analyzer_freeze(v) {
    analyzer_frozen = v ? 1 : 0;
    force_redraw();
}

// Spectrum render style: 0 = Rainbow (thin colour line + 5% wash, max-per-column
// detail); 1 = EQ Eight (heavy muted-grey solid fill + smoothing → the creamy
// filled look from Ableton's EQ8); 2 = Both (grey filled backdrop + the crisp
// cyan line on top — energy AND a precise envelope, the most useful for real EQ
// work). Render-only; the FFT feed + dB mapping are identical, draw_analyzer branches.
function set_analyzer_style(v) {
    if (v === undefined || v !== v) v = 0;
    ANALYZER_STYLE = v < 0 ? 0 : (v > 2 ? 2 : Math.round(v));
    force_redraw();
}

function band_uses_gain(type) {
    return type === TYPE_PEAK || type === TYPE_LOSHELF || type === TYPE_HISHELF;
}

function band_supports_dynamic(type) {
    return band_uses_gain(type);
}

// ── Dynamic EQ detector ─────────────────────────────────────────────────
// For each dynamic-enabled gain band, derive a gain OFFSET that tracks the
// level in the band's frequency region from the FFT magnitudes (a dedicated
// pre-EQ detector buffer when set via set_dyn_buffer, else the spectrum buffer):
// offset = dynamic_amount * envelope(level). Negative amount
// = compress (cut when loud), positive = expand (boost when loud). The offset
// is emitted as "band_dyngain idx offset" on outlet 0 for the product to ADD
// to the band's filter gain — kept separate from the static Gain param so the
// modulation never writes the param. Runs at the analyzer poll rate; biquad
// coefficient interpolation downstream smooths the steps.
var DYN_TRIGGER_FLOOR = -42.0;
var DYN_TRIGGER_RANGE = 24.0;
var DYN_ATTACK = 0.24;
var DYN_RELEASE = 0.10;
var DYN_TRIM_DB = 18.0;
var DYN_MIN_DB = -72.0;

// Peak dB of the raw FFT magnitudes in the band's region (freq +/- ~1/4 oct).
function dyn_probe_db(freq, mags) {
    var m = mags.length;
    if (m < 4) return DYN_MIN_DB;
    var hz_per_bin = (sample_rate * 0.5) / m;
    var klo = Math.floor((freq * 0.84) / hz_per_bin);
    var khi = Math.ceil((freq * 1.19) / hz_per_bin);
    if (klo < 0) klo = 0;
    if (khi >= m) khi = m - 1;
    if (khi < klo) khi = klo;
    var peak = 0.0, k, mag;
    for (k = klo; k <= khi; k++) {
        mag = mags[k]; if (mag < 0.0) mag = -mag; if (mag !== mag) mag = 0.0;
        if (mag > peak) peak = mag;
    }
    var db = peak > 1e-9 ? (20.0 * Math.log(peak) / Math.LN10) + DYN_TRIM_DB : DYN_MIN_DB;
    if (db < DYN_MIN_DB) db = DYN_MIN_DB;
    if (db > 0.0) db = 0.0;
    return db;
}

// Update every dynamic band's offset from one raw FFT frame; emit + redraw on
// change. Returns 1 if any band changed (so the caller can refresh the curve).
function update_dynamic_from_fft(mags) {
    var i, b, level, norm, coeff, target;
    var changed = 0;
    for (i = 0; i < num_bands; i++) {
        b = bands[i];
        if (!b || !b.present) continue;
        if (!b.enabled || !b.dynamic || !band_supports_dynamic(b.type) ||
                Math.abs(b.dynamic_amount) < 0.001) {
            if (Math.abs(b.dynamic_current) > 0.01 || Math.abs(b.dynamic_env) > 0.01) {
                b.dynamic_env = b.dynamic_env * 0.82;
                b.dynamic_current = b.dynamic_current * 0.82;
                outlet(0, "band_dyngain", i, b.dynamic_current);
                apply_dyn_to_cache(i);
                changed = 1;
            }
            continue;
        }
        level = dyn_probe_db(b.freq, mags);
        norm = clamp((level - DYN_TRIGGER_FLOOR) / DYN_TRIGGER_RANGE, 0.0, 1.0);
        coeff = norm > b.dynamic_env ? DYN_ATTACK : DYN_RELEASE;
        b.dynamic_env = b.dynamic_env * (1.0 - coeff) + norm * coeff;
        target = Math.round(b.dynamic_amount * b.dynamic_env * 10.0) / 10.0;
        if (Math.abs(target - b.dynamic_current) >= 0.05) {
            b.dynamic_current = target;
            outlet(0, "band_dyngain", i, target);
            apply_dyn_to_cache(i);
            changed = 1;
        }
    }
    return changed;
}

// Reflect a band's live dynamic offset in the DRAWN curve: recompute its biquad
// response at the effective gain (static + dynamic_current). The node dot stays
// at the static gain (Pro-Q style — the ring shows the range, the curve moves).
function apply_dyn_to_cache(i) {
    var bc = band_cache[i];
    if (!bc || !bc.present || !bc.enabled || !bc.uses_gain) return;
    bc.coeffs = biquad_coeffs(bc.type, bc.freq,
        clamp(bc.gain + bands[i].dynamic_current, MIN_GAIN, MAX_GAIN), bc.q);
}

// Re-sweep a motion-enabled band's DRAWN coeffs at the LFO-swept frequency (and
// gain), so the curve bump visibly moves in time with the audio LFO. Called
// every paint and recomputed from the static cache each rebuild; folds in any
// dynamic offset so motion + dynamic compose. Returns 1 if it swept (so the
// caller knows a band is animating).
function apply_motion_to_cache(i) {
    var bc = band_cache[i];
    if (!bc || !bc.present || !bc.enabled || !bc.motion || bc.motion_depth < 0.5) return 0;
    var dir = motion_direction_components(bc.motion_direction);
    var swing = Math.sin(motion_phase(i, bc));
    var f = bc.freq;
    var g = bc.gain;
    if (bands[i] && bands[i].dynamic) g = g + bands[i].dynamic_current;
    if (Math.abs(dir[0]) > 0.001) {
        f = clamp(bc.freq * Math.pow(2.0, swing * (bc.motion_depth / 100.0) * 1.25 * dir[0]),
                  MIN_FREQ, MAX_FREQ);
    }
    if (Math.abs(dir[1]) > 0.001 && bc.uses_gain) {
        g = g + swing * (bc.motion_depth / 100.0) * 12.0 * dir[1];
    }
    bc.coeffs = biquad_coeffs(bc.type, f, clamp(g, MIN_GAIN, MAX_GAIN), bc.q);
    return 1;
}

function type_default_q(type) {
    if (type === TYPE_LOWPASS || type === TYPE_HIGHPASS) return 0.707;
    return 1.0;
}

function apply_band_type(idx, type_idx) {
    var next_type;
    var prev_type;
    var prev_dynamic;
    var prev_dynamic_amount;
    var q_changed;

    idx = Math.floor(idx);
    next_type = Math.floor(type_idx);
    if (idx < 0 || idx >= num_bands) return 0;
    if (next_type < 0 || next_type >= TYPE_NAMES.length) return 0;

    prev_type = bands[idx].type;
    prev_dynamic = bands[idx].dynamic ? 1 : 0;
    prev_dynamic_amount = Math.abs(bands[idx].dynamic_amount || 0.0) > 0.001;
    q_changed = 0;

    bands[idx].type = next_type;
    if ((next_type === TYPE_LOWPASS || next_type === TYPE_HIGHPASS) && prev_type !== next_type) {
        bands[idx].q = type_default_q(next_type);
        q_changed = 1;
    }
    if (!band_supports_dynamic(next_type)) {
        bands[idx].dynamic = 0;
        bands[idx].dynamic_amount = 0.0;
    }

    rebuild_band_cache();
    outlet(0, "band_type", idx, next_type);
    if (q_changed) {
        outlet(3, "band_q", idx, band_cache[idx].q);
    }
    if (!band_supports_dynamic(next_type) && (prev_dynamic || prev_dynamic_amount)) {
        outlet(0, "band_dynamic", idx, 0);
        outlet(0, "band_dynamic_amount", idx, 0.0);
    }
    return 1;
}

function band_node_gain(b) {
    if (band_uses_gain(b.type)) return clamp(b.gain, MIN_GAIN, MAX_GAIN);
    return 0.0;
}

// Effective ring offset (dB) used for drawing AND hit-testing. With a real
// non-zero range it is the range itself; at ~0 it falls back to a signed visible
// default so the ring never overlaps the node (which is what made the grab
// ambiguous). Direction defaults opposite the node gain so a boost previews a
// compress ring and a cut previews an expand ring.
function dynamic_handle_offset(cache) {
    var amt = cache.dynamic_amount;
    // Mid-drag the ring must follow the cursor continuously through 0 (the
    // default-offset snap would make it jump at the sign flip).
    if (cache.idx !== undefined && is_active_ring_drag(cache.idx)) return amt;
    if (Math.abs(amt) >= 0.05) return amt;
    return cache.node_gain >= 0.0 ? -DYNAMIC_DEFAULT_OFFSET : DYNAMIC_DEFAULT_OFFSET;
}

function dynamic_handle_gain(cache) {
    return clamp(cache.node_gain + dynamic_handle_offset(cache), MIN_GAIN, MAX_GAIN);
}

// True while a ring-drag (drag_mode 2) is in flight on this band, so the ring
// stays visible/hittable across the amount==0 sign flip.
function is_active_ring_drag(idx) {
    return dragging && drag_mode === 2 && idx === selected_band;
}

function find_free_band() {
    var i;
    for (i = 0; i < num_bands; i++) {
        if (!band_cache[i].present) return i;
    }
    return -1;
}

function next_enabled_band(preferred_idx) {
    var i;
    if (preferred_idx >= 0 && preferred_idx < num_bands && band_cache[preferred_idx].present) {
        return preferred_idx;
    }
    for (i = 0; i < num_bands; i++) {
        if (band_cache[i].present) return i;
    }
    return -1;
}

function close_node_menu() {
    menu_band = -1;
    menu_x = 0;
    menu_y = 0;
    menu_hover = "";
}

function open_node_menu_for(idx, x, y) {
    if (idx < 0 || idx >= num_bands || !band_cache[idx].present) {
        close_node_menu();
        return;
    }
    menu_band = idx;
    menu_x = x;
    menu_y = y;
    menu_hover = "";
}

function delete_band_at(idx) {
    var next_idx;
    if (idx < 0 || idx >= num_bands) return;
    if (!bands[idx].present) return;

    bands[idx].present = 0;
    bands[idx].enabled = 0;
    bands[idx].motion = 0;
    bands[idx].dynamic = 0;
    bands[idx].dynamic_amount = 0.0;
    rebuild_band_cache();
    next_idx = next_enabled_band(idx === selected_band ? idx + 1 : selected_band);
    selected_band = next_idx;
    outlet(0, "delete_band", idx);
    outlet(0, "selected_band", next_idx);
    dragging = 0;
    close_node_menu();
    mgraphics.redraw();
}

// Pro-Q-style: the TYPE of a band created by clicking the empty graph depends on
// WHERE you click. The far edges make pass filters (high-pass at the low end,
// low-pass at the high end), just inside makes shelves, and the broad middle makes
// a bell -- matching FabFilter's create gesture so "click and it makes the right
// band". Zones are fractions of the plot width: [HP][LoShelf][--- BELL ---][HiShelf][LP].
var CREATE_HP_FRAC   = 0.07;
var CREATE_LOSH_FRAC = 0.18;
var CREATE_HISH_FRAC = 0.82;
var CREATE_LP_FRAC   = 0.93;
function band_type_for_x(x) {
    var l = plot_left();
    var r = plot_right();
    if (r <= l) return TYPE_PEAK;
    var frac = (x - l) / (r - l);
    if (frac <= CREATE_HP_FRAC) return TYPE_HIGHPASS;
    if (frac < CREATE_LOSH_FRAC) return TYPE_LOSHELF;
    if (frac >= CREATE_LP_FRAC) return TYPE_LOWPASS;
    if (frac > CREATE_HISH_FRAC) return TYPE_HISHELF;
    return TYPE_PEAK;
}

function create_band_at(x, y, btype, no_snap, bq) {
    var created_idx;
    var created_freq;
    var created_gain;
    var t = (btype === undefined) ? band_type_for_x(x) : Math.floor(btype);
    var q0;
    if (bq === undefined || !(bq > 0)) {
        // Pass filters open at a natural Butterworth-ish Q; bells/shelves at 1.0.
        q0 = (t === TYPE_LOWPASS || t === TYPE_HIGHPASS) ? 0.707 : 1.0;
    } else {
        q0 = clamp(bq, 0.1, 30.0);
    }
    created_idx = find_free_band();
    if (created_idx < 0) return 0;

    created_freq = x_to_freq(x);
    // SPECTRUM GRAB: if a clear analyzer peak sits near the click, snap the new
    // band onto it (Pro-Q "grab the resonance"). No peak -> exact placement.
    // Skipped for sketch-created bands (no_snap) so the drawn shape is respected.
    if (!no_snap) {
        var snap_freq = analyzer_peak_near_x(x);
        if (snap_freq > 0.0) created_freq = snap_freq;
    }
    created_gain = y_to_gain(y);
    created_gain = Math.round(created_gain * 10.0) / 10.0;
    bands[created_idx].freq = clamp(created_freq, MIN_FREQ, MAX_FREQ);
    bands[created_idx].gain = clamp(created_gain, MIN_GAIN, MAX_GAIN);
    bands[created_idx].q = q0;
    bands[created_idx].type = t;
    bands[created_idx].present = 1;
    bands[created_idx].enabled = 1;
    bands[created_idx].motion = 0;
    bands[created_idx].dynamic = 0;
    bands[created_idx].dynamic_amount = 0.0;
    bands[created_idx].motion_rate = default_motion_rate(created_idx);
    bands[created_idx].motion_depth = default_motion_depth(created_idx);
    bands[created_idx].motion_direction = default_motion_direction(created_idx);
    selected_band = created_idx;
    dragging = 0;
    drag_mode = 0;
    rebuild_band_cache();
    close_node_menu();
    outlet(
        0,
        "add_band",
        created_idx,
        bands[created_idx].freq,
        bands[created_idx].gain,
        bands[created_idx].q,
        bands[created_idx].type,
        1
    );
    outlet(1, "band_freq", created_idx, bands[created_idx].freq);
    outlet(2, "band_gain", created_idx, bands[created_idx].gain);
    outlet(3, "band_q", created_idx, bands[created_idx].q);
    outlet(0, "band_type", created_idx, bands[created_idx].type);
    outlet(0, "band_enable", created_idx, 1);
    outlet(0, "band_motion", created_idx, 0);
    outlet(0, "band_dynamic", created_idx, 0);
    outlet(0, "band_dynamic_amount", created_idx, 0.0);
    outlet(0, "band_motion_rate", created_idx, bands[created_idx].motion_rate);
    outlet(0, "band_motion_depth", created_idx, bands[created_idx].motion_depth);
    outlet(0, "band_motion_direction", created_idx, bands[created_idx].motion_direction);
    outlet(0, "selected_band", created_idx);
    force_redraw();
    return 1;
}

// ── EQ Sketch (draw-to-EQ) ───────────────────────────────────────────
// Pro-Q-style: turn on Sketch, drag the shape you want across the plot, and the
// prominent peaks/dips of your stroke become bell bands (additive). The fit is
// pure (no mgraphics/Buffer) so it is unit-testable in the Node harness.
function set_sketch(v) {
    sketch_mode = (v && v !== "0") ? 1 : 0;
    if (!sketch_mode) { sketching = 0; sketch_x = []; sketch_g = []; }
    mgraphics.redraw();
}

function sketch_begin(x, y) {
    sketching = 1;
    sketch_x = [x];
    sketch_g = [y_to_gain(y)];
    mgraphics.redraw();
}

function sketch_extend(x, y) {
    if (!sketching) return;
    sketch_x.push(x);
    sketch_g.push(y_to_gain(y));
    mgraphics.redraw();
}

function sketch_commit() {
    if (!sketching) return;
    sketching = 0;
    var anchors = fit_sketch(sketch_x, sketch_g);
    sketch_x = [];
    sketch_g = [];
    for (var i = 0; i < anchors.length; i++) {
        create_band_at(anchors[i].x, gain_to_y(anchors[i].gain), anchors[i].type, 1, anchors[i].q);
    }
    mgraphics.redraw();
}

function sketch_cancel() {
    sketching = 0;
    sketch_x = [];
    sketch_g = [];
    mgraphics.redraw();
}

// Estimate a bell's Q from how wide the drawn bump is: find the half-gain points
// on each side of the extremum, measure the octave span (via x_to_freq), and map
// it to a Q (narrow draw -> tight bell, wide draw -> broad bell). Falls back to
// the stroke ends when a side never returns to half-gain.
function sketch_q(X, S, i, n) {
    var half = Math.abs(S[i]) * 0.5;
    var fl = x_to_freq(X[0]), fr = x_to_freq(X[n - 1]), j;
    for (j = i - 1; j >= 0; j--) { if (Math.abs(S[j]) <= half) { fl = x_to_freq(X[j]); break; } }
    for (j = i + 1; j < n; j++) { if (Math.abs(S[j]) <= half) { fr = x_to_freq(X[j]); break; } }
    if (!(fl > 0) || !(fr > fl)) return 1.0;
    var oct = Math.log(fr / fl) / Math.LN2;
    if (oct < 0.18) oct = 0.18;
    if (oct > 3.0) oct = 3.0;
    var p = Math.pow(2.0, oct);
    return clamp(Math.sqrt(p) / (p - 1.0), 0.3, 8.0);
}

// Reduce a freehand stroke to up to 5 band anchors: smooth, take interior local
// extrema (Q from their drawn width) + the endpoints/shelves that clear a dB
// threshold, then greedily keep the strongest with a minimum plot-x spacing.
// Returns [{x, gain, type, q}] (plot x, dB).
function fit_sketch(xs, gs) {
    var out = [], n = xs.length, i;
    if (n < 2) return out;
    var order = [];
    for (i = 0; i < n; i++) order.push(i);
    order.sort(function (a, b) { return xs[a] - xs[b]; });
    var X = [], G = [];
    for (i = 0; i < n; i++) { X.push(xs[order[i]]); G.push(gs[order[i]]); }
    // 3-point smooth so pointer jitter does not spawn spurious extrema.
    var S = [];
    for (i = 0; i < n; i++) {
        var a = G[i > 0 ? i - 1 : 0];
        var c = G[i < n - 1 ? i + 1 : n - 1];
        S.push((a + G[i] + c) / 3.0);
    }
    var THRESH = 1.5;     // dB; flatter strokes than this add nothing
    var SHELF_MIN = 2.5;  // dB; an end this raised/cut + a flat opposite end = shelf
    var MIN_PX = 22;      // min plot-x gap between two sketched bands
    var CAP = 5;
    // SHELF FIT: a stroke that steps up/down at one end and returns toward 0 at
    // the other reads as a SHELF (the most common EQ move — bass boost, air),
    // not a pair of edge bells. The shelf goes in first (dominant feature) and
    // consumes that endpoint; its corner is where the stroke crosses half-gain.
    var lo_used = 0, hi_used = 0;
    if (Math.abs(G[0]) >= SHELF_MIN && Math.abs(G[n - 1]) < Math.abs(G[0]) * 0.45) {
        var halfL = Math.abs(G[0]) * 0.5, cxL = X[n - 1];
        for (i = 1; i < n; i++) { if (Math.abs(S[i]) <= halfL) { cxL = X[i]; break; } }
        out.push({ x: cxL, gain: G[0], type: TYPE_LOSHELF });
        lo_used = 1;
    }
    if (Math.abs(G[n - 1]) >= SHELF_MIN && Math.abs(G[0]) < Math.abs(G[n - 1]) * 0.45) {
        var halfH = Math.abs(G[n - 1]) * 0.5, cxH = X[0];
        for (i = n - 2; i >= 0; i--) { if (Math.abs(S[i]) <= halfH) { cxH = X[i]; break; } }
        out.push({ x: cxH, gain: G[n - 1], type: TYPE_HISHELF });
        hi_used = 1;
    }
    var cand = [];
    // Endpoints (if not already a shelf) use the RAW gain (smoothing pulls a flat
    // end up toward an interior bump, which would spawn a spurious edge band).
    if (!lo_used && Math.abs(G[0]) >= THRESH) cand.push({ x: X[0], gain: G[0], type: TYPE_PEAK });
    for (i = 1; i < n - 1; i++) {
        // STRICT extrema only: a flat/sloped run is not a peak.
        var ismax = S[i] > S[i - 1] && S[i] > S[i + 1];
        var ismin = S[i] < S[i - 1] && S[i] < S[i + 1];
        if ((ismax || ismin) && Math.abs(S[i]) >= THRESH) {
            cand.push({ x: X[i], gain: S[i], type: TYPE_PEAK, q: sketch_q(X, S, i, n) });
        }
    }
    if (!hi_used && Math.abs(G[n - 1]) >= THRESH) cand.push({ x: X[n - 1], gain: G[n - 1], type: TYPE_PEAK });
    cand.sort(function (a, b) { return Math.abs(b.gain) - Math.abs(a.gain); });
    for (i = 0; i < cand.length && out.length < CAP; i++) {
        var ok = 1;
        for (var j = 0; j < out.length; j++) {
            if (Math.abs(cand[i].x - out[j].x) < MIN_PX) { ok = 0; break; }
        }
        if (ok) out.push(cand[i]);
    }
    return out;
}

// The live stroke preview while sketching (a dashed accent polyline).
function draw_sketch() {
    if (!sketching || sketch_x.length < 2) return;
    mgraphics.set_source_rgba(0.95, 0.85, 0.45, 0.9);
    mgraphics.set_line_width(1.6);
    for (var i = 0; i < sketch_x.length; i++) {
        var yy = gain_to_y(sketch_g[i]);
        if (i === 0) mgraphics.move_to(sketch_x[i], yy);
        else mgraphics.line_to(sketch_x[i], yy);
    }
    mgraphics.stroke();
}

// ── Filter coefficients / response ───────────────────────────────────
// biquad_coeffs: moved to the shared graph_core include (T25)

// response_db: moved to the shared graph_core include (T25)

function rebuild_band_cache() {
    var i;
    for (i = 0; i < MAX_BANDS; i++) {
        band_cache[i].present = bands[i].present ? 1 : 0;
        band_cache[i].enabled = bands[i].enabled ? 1 : 0;
        band_cache[i].freq = clamp(bands[i].freq, MIN_FREQ, MAX_FREQ);
        band_cache[i].gain = clamp(bands[i].gain, MIN_GAIN, MAX_GAIN);
        band_cache[i].q = clamp(bands[i].q, MIN_Q, MAX_Q);
        band_cache[i].type = Math.floor(bands[i].type);
        band_cache[i].motion = bands[i].motion ? 1 : 0;
        // While the ring of this band is actively being dragged, keep it
        // "dynamic" even as the live amount sweeps through 0 — otherwise the
        // ring would vanish mid-drag at the sign flip and the gesture glitches
        // (the reported bug). Drag owns the band; the flag is restored on release.
        band_cache[i].dynamic = (bands[i].dynamic || is_active_ring_drag(i)) ? 1 : 0;
        band_cache[i].dynamic_amount = clamp(bands[i].dynamic_amount || 0.0, -MAX_DYNAMIC_RANGE, MAX_DYNAMIC_RANGE);
        band_cache[i].motion_rate = clamp(bands[i].motion_rate || default_motion_rate(i), 0.05, 12.0);
        band_cache[i].motion_depth = clamp(bands[i].motion_depth || 0.0, 0.0, 100.0);
        band_cache[i].motion_direction = clamp_motion_direction(bands[i].motion_direction);
        band_cache[i].uses_gain = band_uses_gain(band_cache[i].type) ? 1 : 0;
        band_cache[i].node_gain = band_node_gain(band_cache[i]);
        if (!band_supports_dynamic(band_cache[i].type)) {
            band_cache[i].dynamic = 0;
            band_cache[i].dynamic_amount = 0.0;
        }

        if (!band_cache[i].present || !band_cache[i].enabled) {
            band_cache[i].coeffs = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0];
        } else if (!band_cache[i].uses_gain && band_cache[i].type === TYPE_BANDPASS) {
            band_cache[i].coeffs = biquad_coeffs(
                band_cache[i].type, band_cache[i].freq, 0.0, band_cache[i].q
            );
        } else {
            band_cache[i].coeffs = biquad_coeffs(
                band_cache[i].type, band_cache[i].freq, band_cache[i].gain, band_cache[i].q
            );
        }
    }
    refresh_animation_task();
    emit_chip_states();
}

// Band CHIP ROW feed (Pro-Q-style band overview, Para<->LP parity). Emits unique
// selectors so the existing outlet-0 band-router traffic is untouched; the product
// routes chip_num/chip_band/chip_sel into a band_chip_row jsui. Called from
// rebuild_band_cache (covers add/delete/toggle/drag) and set_selected (selection).
function emit_chip_states() {
    var i;
    outlet(0, "chip_num", num_bands);
    for (i = 0; i < num_bands; i++) {
        outlet(0, "chip_band", i,
            bands[i].present ? 1 : 0, bands[i].enabled ? 1 : 0, 0);
    }
    outlet(0, "chip_sel", selected_band);
}

// Chip clicks (from the band_chip_row jsui): select a band / toggle its enable.
function select_band(idx) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands || !bands[idx].present) return;
    set_selected(idx);
    outlet(0, "selected_band", selected_band);
}
function toggle_band_enable(idx) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands || !bands[idx].present) return;
    bands[idx].enabled = bands[idx].enabled ? 0 : 1;
    selected_band = idx;
    rebuild_band_cache();
    outlet(0, "band_enable", idx, bands[idx].enabled);
    outlet(0, "selected_band", idx);
}

// ── Build frequency table (logarithmic spacing) ─────────────────────
var freq_table = [];
(function() {
    var i;
    for (i = 0; i < NUM_POINTS; i++) {
        var norm = i / (NUM_POINTS - 1);
        freq_table[i] = Math.exp(LOG_MIN + norm * LOG_RANGE);
    }
    rebuild_band_cache();
})();

// ── Drawing ──────────────────────────────────────────────────────────
function draw_plot_background() {
    if (EXTERNAL_SPECTRUM) {
        // A compiled spectrum (spectroscope~) fills the plot behind this jsui —
        // keep the PLOT transparent so it shows through; draw only the border.
        // The label GUTTER below the plot has no scope over it, so the lighter
        // device panel showed through as a full-width grey band (user-flagged)
        // — paint the gutter to the plot's dark bg so the axis numbers sit on
        // the same ground as the graph.
        mgraphics.set_source_rgba(BG_COLOR);
        mgraphics.rectangle(0, plot_bottom(), mgraphics.size[0],
                            mgraphics.size[1] - plot_bottom());
        mgraphics.fill();
        mgraphics.set_source_rgba(PLOT_BORDER_CLR);
        mgraphics.rectangle(plot_left(), plot_top(), plot_w(), plot_h());
        mgraphics.set_line_width(1.0);
        mgraphics.stroke();
        return;
    }
    mgraphics.set_source_rgba(PANEL_CLR);
    mgraphics.rectangle(0, 0, mgraphics.size[0], mgraphics.size[1]);
    mgraphics.fill();

    mgraphics.set_source_rgba(BG_COLOR);
    mgraphics.rectangle(plot_left(), plot_top(), plot_w(), plot_h());
    mgraphics.fill_preserve();
    mgraphics.set_source_rgba(PLOT_BORDER_CLR);
    mgraphics.set_line_width(1.0);
    mgraphics.stroke();
}

function paint() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];

    draw_plot_background();

    draw_grid();
    if (!EXTERNAL_SPECTRUM) {
        draw_analyzer_snapshot();   // it173: A/B reference behind the live analyzer
        draw_analyzer_pre();        // pre-EQ dim backdrop (Pro-Q pre/post grammar)
        draw_analyzer();
    }
    // Re-sweep each motion band's drawn coeffs so the curve moves with the LFO.
    var _mi;
    for (_mi = 0; _mi < num_bands; _mi++) apply_motion_to_cache(_mi);
    draw_band_curves();
    draw_composite_curve();
    draw_motion_guides();
    draw_hover_crosshair();
    draw_dynamic_handles();
    draw_nodes();
    draw_sketch();
    draw_tooltip();
    draw_node_menu();
}

// ── Grid ─────────────────────────────────────────────────────────────
var FREQ_LINES  = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 22000];
var FREQ_LABELS = ["10", "20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "22k"];
function gain_grid_step() {
    if (display_range <= 15.0) return 3.0;
    if (display_range <= 18.0) return 3.0;
    if (display_range <= 24.0) return 6.0;
    return 6.0;
}

function gain_grid_values() {
    var vals = [];
    var step = gain_grid_step();
    var g = -display_range;
    while (g <= display_range + 0.0001) {
        vals.push(Math.round(g * 100.0) / 100.0);
        g += step;
    }
    return vals;
}

// Rainbow EQ-grid recipe (EQ_DESIGN_TEARDOWN.md): log-decade two-tone ruler +
// half-pixel-snapped hairlines + bg edge-fade gradients (the #1 "looks nice"
// factor) + Ableton Sans Bold labels + bright 0 dB + dual axis (EQ-dB left /
// spectrum-dB right).
function draw_grid() {
    var i, x, y, label, metrics, sx, sy, grad;
    var L = plot_left(), R = plot_right(), T = plot_top(), B = plot_bottom();
    var W = mgraphics.size[0], H = mgraphics.size[1];
    var gains = gain_grid_values();

    // ── Frequency decade ruler: 1,2..9,10,20..90,100.. — MAJOR at decades (bright
    //    GRID_CLR), minor 2-9 dim (GRID_LIGHT_CLR). 0.5px lines snapped to x+0.5.
    mgraphics.set_line_width(0.5);
    var fact10 = 10.0, freq = 0.0;
    while (freq < MAX_FREQ) {
        freq = freq + fact10;
        var nf = fact10 * 10.0;
        if (Math.floor(nf) === Math.floor(freq)) fact10 = nf;   // crossed a decade -> step x10
        if (freq < MIN_FREQ || freq > MAX_FREQ) continue;
        x = freq_to_x(freq);
        if (x < L + 1 || x > R - 1) continue;
        mgraphics.set_source_rgba((Math.abs(fact10 - freq) < 0.5) ? GRID_CLR : GRID_LIGHT_CLR);
        sx = Math.floor(x) + 0.5;
        mgraphics.move_to(sx, T); mgraphics.line_to(sx, B); mgraphics.stroke();
    }

    // ── EQ dB lines: 0 dB BRIGHT (the spine), ±6/±12 dim. Snapped to y+0.5.
    for (i = 0; i < gains.length; i++) {
        var isz = Math.abs(gains[i]) < 0.0001;
        if (MINIMAL_GRID && !isz) continue;
        y = gain_to_y(gains[i]); sy = Math.floor(y) + 0.5;
        if (isz) { mgraphics.set_source_rgba(ZERO_LINE_CLR); mgraphics.set_line_width(1.0); }
        else { mgraphics.set_source_rgba(GRID_LIGHT_CLR); mgraphics.set_line_width(0.5); }
        mgraphics.move_to(L, sy); mgraphics.line_to(R, sy); mgraphics.stroke();
    }

    // ── THE premium move: edge-fade — gridlines DISSOLVE into BG_COLOR over the
    //    outer ~44px L/R + the bottom label band, instead of hard-clipping.
    var gW = 44.0;
    mgraphics.rectangle(0, 0, W, H);
    grad = mgraphics.pattern_create_linear(W - gW, 0, W, 0);
    grad.add_color_stop_rgba(0.0, BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 0.0);
    grad.add_color_stop_rgba(0.9, BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 1.0);
    mgraphics.set_source(grad); mgraphics.fill_preserve();
    grad = mgraphics.pattern_create_linear(gW, 0, 0, 0);
    grad.add_color_stop_rgba(0.0, BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 0.0);
    grad.add_color_stop_rgba(0.9, BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 1.0);
    mgraphics.set_source(grad); mgraphics.fill();
    // (bottom fade band REMOVED: the freq labels moved to the gutter below
    // the plot, and the band's baked BG_COLOR mismatched the panel bg — it
    // rendered as a full-width grey bar at the -15 line, user-flagged.)

    // ── Labels (drawn AFTER the fade so they melt at the edges). Ableton Sans Bold.
    mgraphics.select_font_face("Ableton Sans Bold");
    mgraphics.set_font_size(9.5);
    mgraphics.set_source_rgba(TEXT_CLR);
    for (i = 0; i < FREQ_LINES.length; i++) {
        x = freq_to_x(FREQ_LINES[i]);
        if (x < L + 8 || x > R - 8) continue;
        label = FREQ_LABELS[i];
        metrics = mgraphics.text_measure(label);
        // SEATED in the reserved MARGIN_BOTTOM gutter BELOW the plot line
        // (they floated inside the plot at B-3 — user-flagged placement bug)
        mgraphics.move_to(x - metrics[0] * 0.5, B + 9.5);
        mgraphics.show_text(label);
    }
    // EQ dB labels LEFT + spectrum dB labels RIGHT = the dual axis.
    mgraphics.set_font_size(8.5);
    for (i = 0; i < gains.length; i++) {
        var iz = Math.abs(gains[i]) < 0.0001;
        var ie = (i === 0 || i === gains.length - 1);
        var show = MINIMAL_GRID ? (iz || ie) : (Math.abs(gains[i] % gain_grid_step()) < 0.0001 || iz);
        if (!show) continue;
        y = gain_to_y(gains[i]);
        label = iz ? "0" : (gains[i] > 0 ? "+" + gains[i] : "" + gains[i]);
        mgraphics.set_source_rgba(TEXT_CLR);
        mgraphics.move_to(3, y + 3); mgraphics.show_text(label);
    }
    if (!EXTERNAL_SPECTRUM) {
        var sdbs = [0, -12, -24, -36, -48, -60], sl;
        for (i = 0; i < sdbs.length; i++) {
            y = analyzer_db_to_y(sdbs[i]);
            if (y < T + 6 || y > B - 6) continue;
            sl = "" + sdbs[i];
            metrics = mgraphics.text_measure(sl);
            mgraphics.set_source_rgba(TEXT_CLR);
            mgraphics.move_to(W - metrics[0] - 3, y + 3); mgraphics.show_text(sl);
        }
    }
}

// it173: capture the live analyzer as a static A/B reference, or clear it. We
// store the SMOOTHED values (what draw_analyzer plots) so an unchanged input
// overlaps exactly; the tilt is re-applied at draw so it tracks the Tilt control.
function toggle_analyzer_snapshot() {
    if (analyzer_snapshot.length > 1) {
        analyzer_snapshot = [];
    } else {
        var n = analyzer_display.length, k;
        analyzer_snapshot = [];
        if (n > 1 && !analyzer_is_flat()) {
            for (k = 0; k < n; k++) analyzer_snapshot[k] = analyzer_smooth_at(k, n);
        }
    }
    outlet(0, "analyzer_snapshot", analyzer_snapshot.length > 1 ? 1 : 0);  // -> SnapProbe
    mgraphics.redraw();
}

// The captured reference (A/B compare) — a dim warm line + faint fill drawn
// behind the live spectrum. Persists while the live trace comes and goes.
function draw_analyzer_snapshot() {
    var n = analyzer_snapshot.length, k, freq, tilt;
    if (n < 2) return;
    var left = plot_left(), right = plot_right();
    var bottom = plot_bottom(), top = plot_top();
    var sx = [], sy = [];
    for (k = 0; k < n; k++) {
        freq = analyzer_bin_freq(k, n);
        tilt = analyzer_slope_at(freq);
        sx[k] = freq_to_x(freq);
        sy[k] = analyzer_db_to_y(analyzer_tilted_db(analyzer_snapshot[k], tilt));
    }
    var grad = mgraphics.pattern_create_linear(left, top, left, bottom);
    grad.add_color_stop_rgba(0.0, 0.90, 0.82, 0.55, 0.07);
    grad.add_color_stop_rgba(1.0, 0.90, 0.82, 0.55, 0.0);
    mgraphics.set_source(grad);
    mgraphics.move_to(sx[0], bottom);
    for (k = 0; k < n; k++) mgraphics.line_to(sx[k], sy[k]);
    mgraphics.line_to(sx[n - 1], bottom);
    mgraphics.close_path();
    mgraphics.fill();
    mgraphics.set_source_rgba(0.90, 0.82, 0.55, 0.55);
    mgraphics.set_line_width(1.2);
    for (k = 0; k < n; k++) {
        if (k === 0) mgraphics.move_to(sx[k], sy[k]);
        else mgraphics.line_to(sx[k], sy[k]);
    }
    mgraphics.stroke();
}

function draw_analyzer() {
    var i, n, freq;
    var xs = [];
    var ys = [];
    var py = [];
    if (!analyzer_enabled) return;
    n = analyzer_display.length;
    if (n < 2) return;
    if (analyzer_is_flat()) return;   // no real signal -> draw nothing (empty)

    var left = plot_left();
    var right = plot_right();
    var bottom = plot_bottom();
    var top = plot_top();

    var tilt;
    // Floor bins (no real signal) stay at the floor (analyzer_tilted_db) so the
    // tilt can't lift the empty floor into a fake rising diagonal.
    for (i = 0; i < n; i++) {
        freq = analyzer_bin_freq(i, n);
        tilt = analyzer_slope_at(freq);
        xs[i] = freq_to_x(freq);
        ys[i] = analyzer_db_to_y(analyzer_tilted_db(analyzer_smooth_at(i, n), tilt));
        py[i] = analyzer_db_to_y(analyzer_tilted_db(analyzer_peaks[i], tilt));
    }

    // Two render styles (set_analyzer_style): both use the SAME max-per-column data
    // ROUNDED with path_roundcorners (spectRCorners=4); only the fill weight, line
    // and smoothing differ.
    //   0 Rainbow — thin colour line + 5% wash (display.js StereoSpectrum), detail kept.
    //   1 EQ8     — heavy muted-grey solid fill + an extra ±3-tap smooth that lifts the
    //               inter-harmonic valleys into the creamy filled envelope of Ableton EQ8.
    var ai;
    var style = ANALYZER_STYLE;        // 0 Rainbow, 1 EQ8, 2 Both
    var eq8 = (style === 1);
    var both = (style === 2);
    if (eq8) {
        // Creamy EQ8 smooth (pure EQ8 only — Rainbow + Both keep max-per-column
        // detail so resonances stay visible for real EQ work).
        var sm = [], j, acc, cnt;   // box-smooth in y (= dB; the map is linear) → fill the comb gaps
        for (i = 0; i < n; i++) {
            acc = 0; cnt = 0;
            for (j = i - 3; j <= i + 3; j++) { if (j >= 0 && j < n) { acc += ys[j]; cnt++; } }
            sm[i] = acc / cnt;
        }
        ys = sm;
    }
    // Fill: Rainbow = light cyan wash; EQ8 = heavy grey; Both = a grey backdrop
    // (lighter than EQ8) UNDER the crisp cyan line — energy + a precise envelope.
    var fc, fTopA, fBotA;
    if (eq8)       { fc = ANALYZER_EQ8_CLR;  fTopA = 0.30; fBotA = 0.46; }
    else if (both) { fc = ANALYZER_EQ8_CLR;  fTopA = 0.16; fBotA = 0.30; }
    else           { fc = ANALYZER_FILL_CLR; fTopA = ANALYZER_FILL_CLR[3] * 0.5; fBotA = ANALYZER_FILL_CLR[3]; }
    mgraphics.move_to(xs[0], bottom + 2);
    mgraphics.line_to(xs[0], ys[0]);
    for (ai = 1; ai < n; ai++) mgraphics.line_to(xs[ai], ys[ai]);
    mgraphics.line_to(xs[n - 1], bottom + 2);
    mgraphics.close_path();
    mgraphics.path_roundcorners(ANALYZER_RCORNERS);
    var grad = mgraphics.pattern_create_linear(left, top, left, bottom);
    grad.add_color_stop_rgba(0.0, fc[0], fc[1], fc[2], fTopA);
    grad.add_color_stop_rgba(1.0, fc[0], fc[1], fc[2], fBotA);
    mgraphics.set_source(grad);
    mgraphics.fill();

    // Envelope on top — Rainbow = bright thin colour line; EQ8 = a quiet grey edge
    // (the fill is the spectrum, not the line).
    mgraphics.move_to(xs[0], ys[0]);
    for (ai = 1; ai < n; ai++) mgraphics.line_to(xs[ai], ys[ai]);
    mgraphics.path_roundcorners(ANALYZER_RCORNERS);
    if (eq8) {
        mgraphics.set_source_rgba(ANALYZER_EQ8_CLR[0], ANALYZER_EQ8_CLR[1], ANALYZER_EQ8_CLR[2], 0.85);
        mgraphics.set_line_width(1.0);
    } else {
        mgraphics.set_source_rgba(ANALYZER_LINE_CLR);
        mgraphics.set_line_width(1.1);
    }
    mgraphics.stroke();

    // Peak-hold line (slow-decaying), drawn thin above the live spectrum. Cyan +
    // grassy (the peaks aren't smoothed), so it belongs to the DETAIL styles only:
    // skip it in EQ8 mode, where it would read as a second overlaid spectrum on top
    // of the clean grey fill (EQ8 = monochrome smooth).
    if (!eq8 && ANALYZER_PEAK_CLR[3] > 0.001) {
        mgraphics.set_source_rgba(ANALYZER_PEAK_CLR);
        mgraphics.set_line_width(1.0);
        var started = 0;
        for (i = 0; i < n; i++) {
            if (analyzer_peaks[i] <= ANALYZER_MIN_DB + 1.0) { started = 0; continue; }
            if (!started) { mgraphics.move_to(xs[i], py[i]); started = 1; }
            else mgraphics.line_to(xs[i], py[i]);
        }
        mgraphics.stroke();
    }

    // FROZEN badge — top-right of the plot while the spectrum is held.
    if (analyzer_frozen) {
        mgraphics.select_font_face("Arial");
        mgraphics.set_font_size(8.0);
        mgraphics.set_source_rgba(ANALYZER_PEAK_CLR[0], ANALYZER_PEAK_CLR[1],
                                  ANALYZER_PEAK_CLR[2], 0.92);
        mgraphics.move_to(right - 44, top + 11);
        mgraphics.show_text("FROZEN");
    }
}

function format_freq_text(freq) {
    if (freq >= 10000) return (freq / 1000.0).toFixed(1) + "k";
    if (freq >= 1000) return (freq / 1000.0).toFixed(2) + "k";
    return Math.round(freq) + " Hz";
}

// Nearest musical note for a frequency (Pro-Q style: identify a band by pitch).
var NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
function note_name(freq) {
    if (freq <= 0.0) return "";
    var midi = Math.round(69 + 12 * (Math.log(freq / 440.0) / Math.LN2));
    return NOTE_NAMES[((midi % 12) + 12) % 12] + (Math.floor(midi / 12) - 1);
}

// Note + cents detune (e.g. "A3 +16c"); cents hidden when essentially in tune.
function note_label(freq) {
    if (freq <= 0.0) return "";
    var midi = 69 + 12 * (Math.log(freq / 440.0) / Math.LN2);
    var ni = Math.round(midi);
    var cents = Math.round((midi - ni) * 100);
    var nm = NOTE_NAMES[((ni % 12) + 12) % 12] + (Math.floor(ni / 12) - 1);
    if (cents >= -1 && cents <= 1) return nm;
    return nm + " " + (cents >= 0 ? "+" : "") + cents + "c";
}

function band_response_db(idx, freq) {
    if (!band_cache[idx].enabled) return 0.0;
    return response_db(band_cache[idx].coeffs, freq);
}

function curve_db_is_visible(db) {
    return db > DISPLAY_FLOOR + 0.05;
}

// ── Individual band curves ───────────────────────────────────────────
// Pro-Q-style band shading: every active gain band tints its own
// contribution with its band color so the EQ reads at a glance and is
// distinct from the analyzer behind it. The selected/hovered band gets a
// stronger fill plus its colored outline.
function draw_band_curves() {
    var i, j, f, x, y, db, clr, zero_y, started, is_active, fill_a;
    zero_y = gain_to_y(0);

    for (i = 0; i < num_bands; i++) {
        if (!band_cache[i].present) continue;
        if (!band_cache[i].enabled) continue;
        if (!band_cache[i].uses_gain) continue;
        if (Math.abs(band_cache[i].gain) < 0.01) continue;

        clr = BAND_COLORS[i % BAND_COLORS.length];
        is_active = (i === selected_band || i === hover_band);
        fill_a = is_active ? 0.34 : 0.20;

        // Filled colored region from the 0 dB line to this band's response
        // (boost fills upward, cut fills downward — both tinted). it178: a
        // vertical gradient gives the lobe depth — brightest at the band's peak
        // deviation, fading to near-transparent at the 0 dB waist (Pro-Q "lit
        // lobe"), same anchored-at-zero pattern as the composite fill.
        var bptop = plot_top(), bpbot = plot_bottom();
        var bfz = (zero_y - bptop) / (bpbot - bptop);
        if (bfz < 0.04) bfz = 0.04; else if (bfz > 0.96) bfz = 0.96;
        var bgrad = mgraphics.pattern_create_linear(plot_left(), bptop, plot_left(), bpbot);
        bgrad.add_color_stop_rgba(0.0, clr[0], clr[1], clr[2], fill_a * 1.55);
        bgrad.add_color_stop_rgba(bfz, clr[0], clr[1], clr[2], fill_a * 0.18);
        bgrad.add_color_stop_rgba(1.0, clr[0], clr[1], clr[2], fill_a * 1.55);
        mgraphics.set_source(bgrad);
        mgraphics.move_to(freq_to_x(freq_table[0]), zero_y);
        for (j = 0; j < NUM_POINTS; j++) {
            f = freq_table[j];
            db = band_response_db(i, f);
            mgraphics.line_to(freq_to_x(f), gain_to_y(db));
        }
        mgraphics.line_to(freq_to_x(freq_table[NUM_POINTS - 1]), zero_y);
        mgraphics.close_path();
        mgraphics.fill();

        // Colored outline only on the active band (keeps the rest clean).
        if (!is_active) continue;
        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], 0.55);
        mgraphics.set_line_width(1.0);
        started = 0;
        for (j = 0; j < NUM_POINTS; j++) {
            f = freq_table[j];
            db = band_response_db(i, f);
            if (!curve_db_is_visible(db)) {
                started = 0;
                continue;
            }
            x = freq_to_x(f);
            y = gain_to_y(db);
            if (!started) {
                mgraphics.move_to(x, y);
                started = 1;
            } else {
                mgraphics.line_to(x, y);
            }
        }
        if (started) mgraphics.stroke();
    }
}

// ── Composite curve + fill ───────────────────────────────────────────
function draw_composite_curve() {
    var j, f, x, y, total_db, started;
    var zero_y = gain_to_y(0);
    var xs = [];
    var ys = [];
    var vis = [];
    var i;

    for (j = 0; j < NUM_POINTS; j++) {
        f = freq_table[j];
        total_db = 0.0;
        for (i = 0; i < num_bands; i++) {
            if (band_cache[i].enabled) {
                total_db += band_response_db(i, f);
            }
        }
        // The FILL plots EVERY point clamped to the display floor, so a sustained
        // cut (LP / HP / deep notch) pins to the bottom — never the old phantom
        // rise to 0 dB. The STROKE, though, is GAPPED where the curve is at/below
        // the floor (vis=0): the bright line drops and exits through the bottom
        // rather than running as a hard line along the bottom edge — the value is
        // off the bottom of the scale, so its line shouldn't show there.
        vis[j] = (total_db > DISPLAY_FLOOR + 0.05) ? 1 : 0;
        if (total_db < DISPLAY_FLOOR) total_db = DISPLAY_FLOOR;
        xs[j] = freq_to_x(f);
        ys[j] = gain_to_y(total_db);
    }

    if (num_bands > 0) {
        // it178: premium gradient fill (Pro-Q "lit curve") — brightest along the
        // curve's deviation from flat, fading to near-transparent at the 0 dB
        // waist. One vertical pattern anchored at zero_y: both boost and cut lobes
        // glow at the curve and fade toward the axis, so bigger moves reach the
        // brighter edge zones. Matches the analyzer/transfer/level/trail gradient
        // language (it171+), bringing the last flat fill into the suite's look.
        var ptop = plot_top(), pbot = plot_bottom();
        var fz = (zero_y - ptop) / (pbot - ptop);
        if (fz < 0.04) fz = 0.04; else if (fz > 0.96) fz = 0.96;
        var aw = FILL_CLR[3] * 0.22;
        var ae = FILL_CLR[3] * 1.7; if (ae > 0.9) ae = 0.9;
        var cgrad = mgraphics.pattern_create_linear(plot_left(), ptop, plot_left(), pbot);
        cgrad.add_color_stop_rgba(0.0, FILL_CLR[0], FILL_CLR[1], FILL_CLR[2], ae);
        cgrad.add_color_stop_rgba(fz, FILL_CLR[0], FILL_CLR[1], FILL_CLR[2], aw);
        cgrad.add_color_stop_rgba(1.0, FILL_CLR[0], FILL_CLR[1], FILL_CLR[2], ae);
        mgraphics.set_source(cgrad);
        mgraphics.move_to(xs[0], zero_y);
        for (j = 0; j < NUM_POINTS; j++) {
            mgraphics.line_to(xs[j], ys[j]);
        }
        mgraphics.line_to(xs[NUM_POINTS - 1], zero_y);
        mgraphics.close_path();
        mgraphics.fill();
    }

    if (num_bands > 0) {
        // Stroke only the in-range part; gap where the curve sits at/below the
        // display floor so the line exits the bottom instead of a hard bottom edge.
        mgraphics.set_source_rgba(COMPOSITE_CLR);
        mgraphics.set_line_width(2.0);
        started = 0;
        for (j = 0; j < NUM_POINTS; j++) {
            if (!vis[j]) { started = 0; continue; }
            if (!started) { mgraphics.move_to(xs[j], ys[j]); started = 1; }
            else mgraphics.line_to(xs[j], ys[j]);
        }
        if (started) mgraphics.stroke();
    }
}

function motion_phase(idx, cache) {
    return now_ms() * 0.001 * cache.motion_rate * Math.PI * 2.0 + idx * 0.85;
}

function motion_direction_components(direction) {
    var radians = clamp_motion_direction(direction) * Math.PI / 180.0;
    return [Math.cos(radians), Math.sin(radians)];
}

function draw_motion_guides() {
    var i, cache, clr, alpha, phase, swing, direction;
    var x0, x1, y0, y1, mx, my;
    var freq_octaves, gain_span, low_freq, high_freq;

    for (i = 0; i < num_bands; i++) {
        cache = band_cache[i];
        if (!cache.present) continue;
        if (!cache.enabled || !cache.motion || cache.motion_depth < 0.5) continue;

        clr = BAND_COLORS[i % BAND_COLORS.length];
        alpha = 0.40;
        phase = motion_phase(i, cache);
        swing = Math.sin(phase);
        direction = motion_direction_components(cache.motion_direction);
        x0 = freq_to_x(cache.freq);
        y0 = node_y_for_band(i);
        x1 = x0;
        y1 = y0;
        mx = x0;
        my = y0;

        if (Math.abs(direction[0]) > 0.001) {
            freq_octaves = (cache.motion_depth / 100.0) * 1.25 * Math.abs(direction[0]);
            low_freq = clamp(cache.freq * Math.pow(2.0, -freq_octaves), MIN_FREQ, MAX_FREQ);
            high_freq = clamp(cache.freq * Math.pow(2.0, freq_octaves), MIN_FREQ, MAX_FREQ);
            x0 = freq_to_x(low_freq);
            x1 = freq_to_x(high_freq);
            mx = freq_to_x(clamp(cache.freq * Math.pow(2.0, swing * freq_octaves * direction[0]), MIN_FREQ, MAX_FREQ));
        }

        if (Math.abs(direction[1]) > 0.001 && cache.uses_gain) {
            gain_span = (cache.motion_depth / 100.0) * 12.0 * Math.abs(direction[1]);
            y0 = gain_to_y(clamp(cache.node_gain - gain_span, MIN_GAIN, MAX_GAIN));
            y1 = gain_to_y(clamp(cache.node_gain + gain_span, MIN_GAIN, MAX_GAIN));
            my = gain_to_y(clamp(cache.node_gain + swing * gain_span * direction[1], MIN_GAIN, MAX_GAIN));
        }

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], alpha);
        mgraphics.set_line_width(1.4);
        mgraphics.move_to(x0, y0);
        mgraphics.line_to(x1, y1);
        mgraphics.stroke();

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], 0.20);
        mgraphics.arc(mx, my, 5.0, 0, Math.PI * 2.0);
        mgraphics.fill();

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], 0.92);
        mgraphics.arc(mx, my, 1.9, 0, Math.PI * 2.0);
        mgraphics.fill();
    }
}

function node_y_for_band(idx) {
    if (band_cache[idx].uses_gain) return gain_to_y(band_cache[idx].node_gain);
    return gain_to_y(0.0);
}

// ── Draggable nodes ──────────────────────────────────────────────────
function draw_nodes() {
    var i, x, y, r, clr, enabled_alpha, ring_alpha, core_alpha, center_alpha;

    for (i = 0; i < num_bands; i++) {
        if (!band_cache[i].present) continue;
        x = freq_to_x(band_cache[i].freq);
        y = node_y_for_band(i);

        clr = BAND_COLORS[i % BAND_COLORS.length];
        r = (i === selected_band) ? NODE_RADIUS_SEL : NODE_RADIUS;
        enabled_alpha = band_cache[i].enabled ? 1.0 : 0.26;
        ring_alpha = band_cache[i].enabled ? 1.0 : 0.44;
        core_alpha = band_cache[i].enabled ? 0.92 : 0.18;
        center_alpha = band_cache[i].enabled ? 0.75 : 0.0;

        // Radial glow: a soft ambient halo on every enabled node + a brighter
        // one on the selected/hovered node (replaces the old flat disc).
        if (band_cache[i].enabled) ds_node_glow(x, y, clr, r + 6.0, 0.13);
        if (i === selected_band || i === hover_band) {
            ds_node_glow(x, y, clr, r + 11.0, band_cache[i].enabled ? 0.42 : 0.16);
        }

        mgraphics.set_source_rgba(0.02, 0.02, 0.03, band_cache[i].enabled ? (i === selected_band ? 0.78 : 0.58) : 0.28);
        mgraphics.arc(x, y, r + 1.7, 0, Math.PI * 2);
        mgraphics.fill();

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], core_alpha);
        mgraphics.arc(x, y, r, 0, Math.PI * 2);
        mgraphics.fill();

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], ring_alpha);
        mgraphics.set_line_width(i === selected_band ? 2.4 : 1.9);
        mgraphics.arc(x, y, r, 0, Math.PI * 2);
        mgraphics.stroke();

        if (band_cache[i].dynamic) {
            mgraphics.set_source_rgba(DYNAMIC_CLR[0], DYNAMIC_CLR[1], DYNAMIC_CLR[2], i === selected_band ? 0.94 : 0.72);
            mgraphics.set_line_width(1.6);
            mgraphics.move_to(x - (r + 4), y + (r + 4));
            mgraphics.line_to(x - 1, y + (r + 1));
            mgraphics.line_to(x - (r + 4), y + (r - 1));
            mgraphics.close_path();
            mgraphics.fill();
        }

        if (center_alpha > 0.0) {
            mgraphics.set_source_rgba(1.0, 1.0, 1.0, center_alpha);
            mgraphics.arc(x, y, 2.1, 0, Math.PI * 2);
            mgraphics.fill();
        }

        mgraphics.set_source_rgba(1.0, 1.0, 1.0, band_cache[i].enabled ? 0.88 : 0.42);
        mgraphics.select_font_face("Arial");
        mgraphics.set_font_size(i === selected_band ? 9.0 : 8.0);
        // The band-number caption sits upper-RIGHT of the node, but FLIP it to the
        // left when the node nears the right edge so it doesn't crowd the right-edge
        // dB scale labels (user-flagged: a node at ~19 kHz parked its "4" on -36).
        var cap = "" + (i + 1);
        var capw = cap.length * 6 + 2;
        var capx = x + r + 3;
        if (capx + capw > plot_right()) capx = x - r - 3 - capw;
        mgraphics.move_to(capx, y - r + 1);
        mgraphics.show_text(cap);
    }
}

function draw_dynamic_handles() {
    var x, base_y, target_y, clr, alpha, size;

    for (i = 0; i < num_bands; i++) {
        if (!band_cache[i].present) continue;
        if (!band_cache[i].enabled) continue;
        if (!band_cache[i].dynamic) continue;
        if (!band_supports_dynamic(band_cache[i].type)) continue;

        x = freq_to_x(band_cache[i].freq);
        base_y = node_y_for_band(i);
        target_y = gain_to_y(dynamic_handle_gain(band_cache[i]));
        clr = BAND_COLORS[i % BAND_COLORS.length];
        alpha = i === selected_band ? 0.92 : (i === hover_band ? 0.78 : 0.58);
        size = i === selected_band ? (DYNAMIC_HANDLE_RADIUS + 1.6) : DYNAMIC_HANDLE_RADIUS;

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], i === selected_band ? 0.34 : 0.20);
        mgraphics.set_line_width(i === selected_band ? 1.9 : 1.2);
        mgraphics.move_to(x, base_y);
        mgraphics.line_to(x, target_y);
        mgraphics.stroke();

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], alpha);
        mgraphics.set_line_width(i === selected_band ? 1.8 : 1.2);
        mgraphics.rectangle(x - size * 0.5, target_y - size * 0.5, size, size);
        mgraphics.stroke();

        mgraphics.set_source_rgba(clr[0], clr[1], clr[2], i === selected_band ? 0.30 : 0.18);
        mgraphics.rectangle(x - size * 0.5 - 2, target_y - size * 0.5 - 2, size + 4, size + 4);
        mgraphics.fill();
    }
}

function node_menu_rect(idx) {
    var anchor_x = menu_x;
    var anchor_y = menu_y;
    var x;
    var y;
    var w = 126;
    var h = 74;
    if (anchor_x <= 0 && anchor_y <= 0) {
        anchor_x = freq_to_x(band_cache[idx].freq);
        anchor_y = node_y_for_band(idx);
    }
    x = anchor_x + 8;
    y = anchor_y - 10;
    if (x + w > plot_right()) x = freq_to_x(band_cache[idx].freq) - w - 18;
    if (x < plot_left() + 4) x = plot_left() + 4;
    if (y < plot_top() + 28) y = plot_top() + 28;
    if (y + h > plot_bottom()) y = plot_bottom() - h;
    return [x, y, w, h];
}

function menu_chip_hit(mx, my, x, y, w, h) {
    return mx >= x && mx <= x + w && my >= y && my <= y + h;
}

function node_menu_hit_test(mx, my) {
    var idx = menu_band;
    var rect;
    var col;
    var row;
    var chip_x;
    var chip_y;
    var type_idx;
    var action_x;
    var action_rects = [
        ["motion", 6, 26],
        ["dynamic", 36, 26],
        ["bypass", 66, 24],
        ["delete", 94, 24]
    ];
    var i;

    if (idx < 0 || idx >= num_bands) return "";
    rect = node_menu_rect(idx);
    if (!menu_chip_hit(mx, my, rect[0], rect[1], rect[2], rect[3])) return "";

    for (type_idx = 0; type_idx < TYPE_NAMES.length; type_idx++) {
        col = type_idx % 4;
        row = Math.floor(type_idx / 4);
        chip_x = rect[0] + 6 + col * 28;
        chip_y = rect[1] + 6 + row * 14;
        if (menu_chip_hit(mx, my, chip_x, chip_y, 24, 12)) {
            return "type:" + type_idx;
        }
    }

    for (i = 0; i < action_rects.length; i++) {
        action_x = rect[0] + action_rects[i][1];
        if (menu_chip_hit(mx, my, action_x, rect[1] + 36, action_rects[i][2], 14)) {
            return action_rects[i][0];
        }
    }
    return "panel";
}

function draw_menu_chip(x, y, w, h, label, active, color) {
    var fill = color || MENU_SURFACE_CLR;
    mgraphics.set_source_rgba(fill[0], fill[1], fill[2], active ? 0.96 : 0.82);
    mgraphics.rectangle_rounded(x, y, w, h, 3, 3);
    mgraphics.fill();

    mgraphics.set_source_rgba(active ? 0.04 : MENU_BORDER_CLR[0], active ? 0.04 : MENU_BORDER_CLR[1], active ? 0.05 : MENU_BORDER_CLR[2], active ? 0.0 : 1.0);
    if (!active) {
        mgraphics.set_line_width(1.0);
        mgraphics.rectangle_rounded(x + 0.5, y + 0.5, w - 1.0, h - 1.0, 3, 3);
        mgraphics.stroke();
    }

    mgraphics.set_source_rgba(active ? 0.05 : 0.92, active ? 0.05 : 0.94, active ? 0.06 : 0.98, 1.0);
    mgraphics.select_font_face("Arial Bold");
    mgraphics.set_font_size(7.0);
    var metrics = mgraphics.text_measure(label);
    mgraphics.move_to(x + (w - metrics[0]) * 0.5, y + 8.5);
    mgraphics.show_text(label);
}

function draw_node_menu() {
    var idx = menu_band;
    var rect;
    var type_idx;
    var col;
    var row;
    var chip_x;
    var chip_y;
    var motion_active;
    var dynamic_active;
    var menu_motion = menu_hover === "motion";
    var menu_dynamic = menu_hover === "dynamic";
    var menu_bypass = menu_hover === "bypass";
    var menu_delete = menu_hover === "delete";
    var dynamic_supported;
    if (idx < 0 || idx >= num_bands || !band_cache[idx].present) return;
    rect = node_menu_rect(idx);

    mgraphics.set_source_rgba(MENU_BG_CLR[0], MENU_BG_CLR[1], MENU_BG_CLR[2], MENU_BG_CLR[3]);
    mgraphics.rectangle_rounded(rect[0], rect[1], rect[2], rect[3], 5, 5);
    mgraphics.fill();

    mgraphics.set_source_rgba(MENU_BORDER_CLR[0], MENU_BORDER_CLR[1], MENU_BORDER_CLR[2], 1.0);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle_rounded(rect[0] + 0.5, rect[1] + 0.5, rect[2] - 1.0, rect[3] - 1.0, 5, 5);
    mgraphics.stroke();

    for (type_idx = 0; type_idx < TYPE_NAMES.length; type_idx++) {
        col = type_idx % 4;
        row = Math.floor(type_idx / 4);
        chip_x = rect[0] + 6 + col * 28;
        chip_y = rect[1] + 6 + row * 14;
        draw_menu_chip(
            chip_x,
            chip_y,
            24,
            12,
            TYPE_SHORT_NAMES[type_idx],
            band_cache[idx].type === type_idx || menu_hover === ("type:" + type_idx),
            band_cache[idx].type === type_idx ? BAND_COLORS[idx % BAND_COLORS.length] : MENU_SURFACE_CLR
        );
    }

    motion_active = band_cache[idx].enabled && band_cache[idx].motion ? 1 : 0;
    dynamic_active = band_cache[idx].enabled && band_cache[idx].dynamic ? 1 : 0;
    dynamic_supported = band_supports_dynamic(band_cache[idx].type) ? 1 : 0;
    draw_menu_chip(rect[0] + 6, rect[1] + 36, 26, 14, "MOT", motion_active || menu_motion, motion_active ? MOTION_CLR : MENU_SURFACE_CLR);
    draw_menu_chip(rect[0] + 36, rect[1] + 36, 26, 14, "DYN", dynamic_supported && (dynamic_active || menu_dynamic), dynamic_supported ? (dynamic_active ? DYNAMIC_CLR : MENU_SURFACE_CLR) : MENU_DISABLED_CLR);
    draw_menu_chip(rect[0] + 66, rect[1] + 36, 24, 14, band_cache[idx].enabled ? "BYP" : "ON", menu_bypass || !band_cache[idx].enabled, menu_bypass ? BAND_COLORS[idx % BAND_COLORS.length] : MENU_SURFACE_CLR);
    draw_menu_chip(rect[0] + 94, rect[1] + 36, 24, 14, "DEL", menu_delete, menu_delete ? BAND_COLORS[idx % BAND_COLORS.length] : MENU_SURFACE_CLR);
}

function apply_menu_action(action) {
    var idx = menu_band;
    var type_idx;
    var dynamic_was_active;
    var dynamic_amount_was_active;
    if (idx < 0 || idx >= num_bands) return;

    if (action.indexOf("type:") === 0) {
        type_idx = Math.floor(action.split(":")[1]);
        if (type_idx >= 0 && type_idx < TYPE_NAMES.length && bands[idx].type !== type_idx) {
            dynamic_was_active = bands[idx].dynamic ? 1 : 0;
            dynamic_amount_was_active = Math.abs(bands[idx].dynamic_amount || 0.0) > 0.001;
            apply_band_type(idx, type_idx);
        }
        close_node_menu();
        mgraphics.redraw();
        return;
    }

    if (action === "motion") {
        if (!bands[idx].enabled) {
            close_node_menu();
            mgraphics.redraw();
            return;
        }
        bands[idx].motion = bands[idx].motion ? 0 : 1;
        if (bands[idx].motion && (!bands[idx].motion_depth || bands[idx].motion_depth < 1.0)) {
            bands[idx].motion_depth = default_motion_depth(idx);
        }
        if (bands[idx].motion && (!bands[idx].motion_rate || bands[idx].motion_rate < 0.05)) {
            bands[idx].motion_rate = default_motion_rate(idx);
        }
        rebuild_band_cache();
        outlet(0, "band_motion", idx, bands[idx].motion ? 1 : 0);
        outlet(0, "band_motion_rate", idx, band_cache[idx].motion_rate);
        outlet(0, "band_motion_depth", idx, band_cache[idx].motion_depth);
        close_node_menu();
        mgraphics.redraw();
        return;
    }

    if (action === "dynamic") {
        if (!bands[idx].enabled) {
            close_node_menu();
            mgraphics.redraw();
            return;
        }
        if (!band_supports_dynamic(bands[idx].type)) {
            close_node_menu();
            mgraphics.redraw();
            return;
        }
        bands[idx].dynamic = bands[idx].dynamic ? 0 : 1;
        if (!bands[idx].dynamic) {
            bands[idx].dynamic_amount = 0.0;
        } else if (Math.abs(bands[idx].dynamic_amount || 0.0) < 0.01) {
            bands[idx].dynamic_amount = bands[idx].gain >= 0.0 ? -6.0 : 6.0;
        }
        rebuild_band_cache();
        outlet(0, "band_dynamic", idx, bands[idx].dynamic ? 1 : 0);
        outlet(0, "band_dynamic_amount", idx, band_cache[idx].dynamic_amount);
        close_node_menu();
        mgraphics.redraw();
        return;
    }

    if (action === "bypass") {
        bands[idx].enabled = bands[idx].enabled ? 0 : 1;
        rebuild_band_cache();
        outlet(0, "band_enable", idx, bands[idx].enabled ? 1 : 0);
        close_node_menu();
        mgraphics.redraw();
        return;
    }

    if (action === "delete") {
        delete_band_at(idx);
    }
}

// ── Tooltip on hover ────────────────────────────────────────────────
function draw_tooltip() {
    // Hover/drag only — a persistent tooltip for the selected band occludes
    // the curve (the left strip already shows the selection's values).
    var target = -1;
    if (menu_band >= 0) {
        target = -1;
    } else if (dragging && selected_band >= 0) {
        target = selected_band;
    } else if (hover_band >= 0) {
        target = hover_band;
    }
    if (target < 0 || target >= num_bands) return;

    var b = band_cache[target];
    var nx = freq_to_x(b.freq);
    var ny = node_y_for_band(target);
    var line1;
    var line2;
    var line3 = "";

    var freq_str = format_freq_text(b.freq) + " · " + note_label(b.freq);

    if (b.uses_gain) {
        var gain_str = (b.gain >= 0 ? "+" : "") + b.gain.toFixed(1) + " dB";
        line1 = freq_str + "  " + gain_str;
        line2 = "Q " + b.q.toFixed(2) + "  " + (TYPE_NAMES[b.type] || "Peak");
    } else {
        line1 = freq_str + "  " + (TYPE_NAMES[b.type] || "Filter");
        line2 = "Q " + b.q.toFixed(2);
    }
    if (!b.enabled) {
        line2 += "  BYPASSED";
    }
    if (b.dynamic && b.enabled) {
        line3 += "DYN " + format_dynamic_amount(b.dynamic_amount);
    }
    if (b.motion && b.enabled) {
        if (line3) line3 += "   ";
        line3 += "MOT " + format_motion_rate(b.motion_rate) + "  " + format_motion_depth(b.motion_depth) + "  DIR " + Math.round(clamp_motion_direction(b.motion_direction)) + "°";
    }

    var tx = nx + 16;
    var ty = ny - 32;
    var tw = line3 ? 214 : 104;
    var th = line3 ? 54 : 40;

    if (tx + tw > plot_right()) tx = nx - tw - 16;
    if (ty < plot_top()) ty = ny + 8;
    if (ty + th > plot_bottom()) ty = plot_bottom() - th;

    mgraphics.set_source_rgba(0.12, 0.12, 0.14, 0.92);
    mgraphics.rectangle_rounded(tx, ty, tw, th, 3, 3);
    mgraphics.fill();

    var clr = BAND_COLORS[target % BAND_COLORS.length];
    mgraphics.set_source_rgba(clr[0], clr[1], clr[2], 0.42);
    mgraphics.set_line_width(1);
    mgraphics.rectangle_rounded(tx + 0.5, ty + 0.5, tw - 1, th - 1, 3, 3);
    mgraphics.stroke();

    mgraphics.set_source_rgba(0.92, 0.92, 0.94, 1.0);
    mgraphics.select_font_face("Arial");
    mgraphics.set_font_size(9);
    mgraphics.move_to(tx + 5, ty + 13);
    mgraphics.show_text(line1);
    mgraphics.set_source_rgba(0.65, 0.65, 0.68, 1.0);
    mgraphics.move_to(tx + 5, ty + 26);
    mgraphics.show_text(line2);
    if (line3) {
        mgraphics.set_source_rgba(0.72, 0.85, 0.92, 1.0);
        mgraphics.move_to(tx + 5, ty + 39);
        mgraphics.show_text(line3);
    }
}

function ring_is_grabbable(i) {
    if (!band_cache[i].present) return 0;
    if (!band_cache[i].enabled) return 0;
    if (!band_cache[i].dynamic) return 0;
    if (!band_supports_dynamic(band_cache[i].type)) return 0;
    return 1;
}

// Squared pixel distance from (mx,my) to band i's ring handle (or a large
// sentinel when the band has no grabbable ring).
function ring_dist_sq(i, mx, my) {
    var x, y, dx, dy;
    if (!ring_is_grabbable(i)) return 1.0e12;
    x = freq_to_x(band_cache[i].freq);
    y = gain_to_y(dynamic_handle_gain(band_cache[i]));
    dx = mx - x;
    dy = my - y;
    return dx * dx + dy * dy;
}

// Closest grabbable ring within the hit radius (was first-match — now nearest,
// so two nearby rings resolve deterministically).
function dynamic_hit_test(mx, my) {
    var i, d, best = -1, best_d = DYNAMIC_HIT_RADIUS * DYNAMIC_HIT_RADIUS;
    for (i = 0; i < num_bands; i++) {
        d = ring_dist_sq(i, mx, my);
        if (d <= best_d) {
            best_d = d;
            best = i;
        }
    }
    return best;
}

// ── Hit-testing ──────────────────────────────────────────────────────
function hit_test(mx, my) {
    var i, x, y, dx, dy, dist;
    var best = -1;
    var best_dist = HIT_RADIUS + 1;

    for (i = 0; i < num_bands; i++) {
        if (!band_cache[i].present) continue;
        x = freq_to_x(band_cache[i].freq);
        y = node_y_for_band(i);
        dx = mx - x;
        dy = my - y;
        dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < best_dist) {
            best_dist = dist;
            best = i;
        }
    }
    return best;
}

// Squared pixel distance from (mx,my) to band idx's node dot (large sentinel
// when the band is absent). Used to arbitrate ring-vs-node presses.
function node_dist_sq(idx, mx, my) {
    var x, y, dx, dy;
    if (idx < 0 || idx >= num_bands || !band_cache[idx].present) return 1.0e12;
    x = freq_to_x(band_cache[idx].freq);
    y = node_y_for_band(idx);
    dx = mx - x;
    dy = my - y;
    return dx * dx + dy * dy;
}

// ── Message handlers (inlet 0 messages, inlet 1 sample rate) ────────
function set_band(idx, freq, gain, q, type, enabled, motion, dynamic, dynamic_amount, motion_rate, motion_depth, motion_direction) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= MAX_BANDS) return;
    // Drag ownership: while the user drags this band the graph is the source
    // of truth. Parameter echoes of our own outlet values would fight the
    // gesture and force a rebuild+redraw per tick.
    if (dragging && idx === selected_band) return;
    // Echo guard: the shell routes our outlets into live.* params whose
    // changes come straight back here. Skip exact no-ops (6-arg form only —
    // the extended motion/dynamic form always applies).
    if (arguments.length <= 6) {
        var bb = bands[idx];
        var en_g = enabled ? 1 : 0;
        if ((en_g ? bb.present : 1) &&
            bb.enabled === en_g &&
            bb.type === Math.floor(type) &&
            Math.abs(bb.freq - freq) < 0.05 &&
            Math.abs(bb.gain - gain) < 0.01 &&
            Math.abs(bb.q - q) < 0.005) {
            return;
        }
    }
    if (enabled) {
        bands[idx].present = 1;
    }
    bands[idx].freq    = freq;
    bands[idx].gain    = gain;
    bands[idx].q       = q;
    bands[idx].type    = Math.floor(type);
    bands[idx].enabled = enabled ? 1 : 0;
    if (arguments.length >= 7 && motion !== undefined) {
        bands[idx].motion = motion ? 1 : 0;
    }
    if (arguments.length >= 8 && dynamic !== undefined) {
        bands[idx].dynamic = dynamic ? 1 : 0;
    }
    if (arguments.length >= 9 && dynamic_amount !== undefined) {
        bands[idx].dynamic_amount = clamp(dynamic_amount, -MAX_DYNAMIC_RANGE, MAX_DYNAMIC_RANGE);
    }
    if (arguments.length >= 10 && motion_rate !== undefined) {
        bands[idx].motion_rate = clamp(motion_rate, 0.05, 12.0);
    }
    if (arguments.length >= 11 && motion_depth !== undefined) {
        bands[idx].motion_depth = clamp(motion_depth, 0.0, 100.0);
    }
    if (arguments.length >= 12 && motion_direction !== undefined) {
        bands[idx].motion_direction = clamp_motion_direction(motion_direction);
    }
    rebuild_band_cache();
    // Message-driven updates coalesce through the 33ms throttle; direct
    // gestures redraw synchronously in their own handlers.
    request_redraw();
}

function set_num_bands(n) {
    n = Math.floor(n);
    if (n < 0) n = 0;
    if (n > MAX_BANDS) n = MAX_BANDS;
    num_bands = n;
    if (selected_band >= num_bands) selected_band = -1;
    if (menu_band >= num_bands) close_node_menu();
    rebuild_band_cache();
    force_redraw();
}

function set_selected(idx) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands || !band_cache[idx].present) {
        selected_band = -1;
    } else {
        selected_band = idx;
    }
    force_redraw();
    emit_chip_states();
}

function set_motion(idx, enabled) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands) return;
    bands[idx].motion = enabled ? 1 : 0;
    if (bands[idx].motion && (!bands[idx].motion_depth || bands[idx].motion_depth < 1.0)) {
        bands[idx].motion_depth = default_motion_depth(idx);
    }
    if (bands[idx].motion && (!bands[idx].motion_rate || bands[idx].motion_rate < 0.05)) {
        bands[idx].motion_rate = default_motion_rate(idx);
    }
    rebuild_band_cache();
    refresh_animation_task();
    force_redraw();
}

function set_dynamic(idx, enabled) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands) return;
    bands[idx].dynamic = enabled ? 1 : 0;
    if (!bands[idx].dynamic) {
        bands[idx].dynamic_amount = 0.0;
    } else if (Math.abs(bands[idx].dynamic_amount || 0.0) < 0.01) {
        bands[idx].dynamic_amount = bands[idx].gain >= 0.0 ? -6.0 : 6.0;
    }
    rebuild_band_cache();
    force_redraw();
}

function set_dynamic_amount(idx, amount) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands) return;
    bands[idx].dynamic_amount = clamp(amount, -MAX_DYNAMIC_RANGE, MAX_DYNAMIC_RANGE);
    // A non-zero range turns dynamic mode ON. A zero range does NOT force it
    // back OFF: a band the user explicitly put into Dynamic mode keeps its
    // grabbable ring (drawn at a visible default offset) even at amount 0, so
    // dragging the ring through 0 doesn't make the handle disappear. The load
    // default is amount 0 with dynamic already 0, so no rings show on load.
    if (Math.abs(bands[idx].dynamic_amount) > 0.001) {
        bands[idx].dynamic = 1;
    } else {
        bands[idx].dynamic_current = 0.0;
        bands[idx].dynamic_env = 0.0;
    }
    rebuild_band_cache();
    force_redraw();
}

function set_motion_rate(idx, value) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands) return;
    // Echo-safe: rate/depth NEVER toggle the enable flag. set_motion owns it.
    // (When the graph disables motion it also emits the band's current
    // rate/depth; if those re-enabled motion here the disable would bounce back
    // through the product's reverse route — an echo fight.)
    bands[idx].motion_rate = clamp(value, 0.05, 12.0);
    rebuild_band_cache();
    force_redraw();
}

function set_motion_depth(idx, value) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands) return;
    bands[idx].motion_depth = clamp(value, 0.0, 100.0);
    rebuild_band_cache();
    force_redraw();
}

function set_motion_direction(idx, value) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= num_bands) return;
    bands[idx].motion_direction = clamp_motion_direction(value);
    rebuild_band_cache();
    force_redraw();
}

function set_analyzer_enabled(v) {
    analyzer_enabled = v ? 1 : 0;
    force_redraw();
}

function set_display_range(v) {
    var next = Math.abs(v);
    if (next <= 16.5) {
        display_range = 15.0;
    } else if (next <= 21) {
        display_range = 18.0;
    } else if (next <= 27) {
        display_range = 24.0;
    } else {
        display_range = 30.0;
    }
    force_redraw();
}

function list() {
    if (inlet === 2) {
        update_analyzer_data(arrayfromargs(arguments));
    }
}

function msg_float(v) {
    if (inlet === 1) {
        sample_rate = clamp(v, 22050.0, 384000.0);
        rebuild_band_cache();
        mgraphics.redraw();
    }
}

function msg_int(v) {
    if (inlet === 1) {
        msg_float(v);
    }
}

function pointer_middle_click(pointerevent, but) {
    if (pointerevent) {
        if (pointerevent.button !== undefined && pointerevent.button === 1) return 1;
        if (pointerevent.buttons !== undefined && (pointerevent.buttons & 4) !== 0) return 1;
    }
    if (but !== undefined && but !== null) {
        if ((but & 4) !== 0) return 1;
    }
    return 0;
}

function pointer_context_click(pointerevent, but, ctrl) {
    if (pointerevent) {
        if (pointerevent.button !== undefined && pointerevent.button === 2) return 1;
        if (pointerevent.buttons !== undefined && (pointerevent.buttons & 2) !== 0) return 1;
    }
    if (but !== undefined && but !== null) {
        if ((but & 2) !== 0) return 1;
    }
    // In classic jsui mouse callbacks, mod2/ctrl carries right-click on Windows
    // and control-click on macOS, which should open the context menu here.
    return ctrl ? 1 : 0;
}

function pointer_option_key(pointerevent, opt) {
    if (pointerevent) {
        if (pointerevent.altKey) return 1;
        if (pointerevent.optionKey) return 1;
    }
    return opt ? 1 : 0;
}

function pointer_shift_key(pointerevent, shift) {
    if (pointerevent && pointerevent.shiftKey) return 1;
    return shift ? 1 : 0;
}

function pointer_command_key(pointerevent, cmd) {
    if (pointerevent && pointerevent.commandKey) return 1;
    return cmd ? 1 : 0;
}

function pointer_control_key(pointerevent, ctrl) {
    if (pointerevent && pointerevent.contextModifier) return 1;
    return ctrl ? 1 : 0;
}

function pointer_x(pointerevent, fallback) {
    if (!pointerevent) return fallback;
    if (pointerevent.x !== undefined) return pointerevent.x;
    if (pointerevent.localX !== undefined) return pointerevent.localX;
    if (pointerevent.offsetX !== undefined) return pointerevent.offsetX;
    if (pointerevent.clientX !== undefined) return pointerevent.clientX;
    return fallback;
}

function pointer_y(pointerevent, fallback) {
    if (!pointerevent) return fallback;
    if (pointerevent.y !== undefined) return pointerevent.y;
    if (pointerevent.localY !== undefined) return pointerevent.localY;
    if (pointerevent.offsetY !== undefined) return pointerevent.offsetY;
    if (pointerevent.clientY !== undefined) return pointerevent.clientY;
    return fallback;
}

function pointer_buttons(pointerevent, fallback) {
    if (!pointerevent) return fallback;
    if (pointerevent.buttons !== undefined) return pointerevent.buttons;
    if (pointerevent.button !== undefined) {
        if (pointerevent.button === 2) return 2;
        return 1;
    }
    return fallback;
}

function note_pointer_press(x, y) {
    last_pointer_press_ms = new Date().getTime();
    last_pointer_press_x = x;
    last_pointer_press_y = y;
    suppress_next_click = 1;
}

function should_ignore_pointer_click(x, y) {
    var now_ms;
    if (!suppress_next_click) return 0;
    now_ms = new Date().getTime();
    if ((now_ms - last_pointer_press_ms) > 300) {
        suppress_next_click = 0;
        return 0;
    }
    if (Math.abs(x - last_pointer_press_x) > 4 || Math.abs(y - last_pointer_press_y) > 4) {
        suppress_next_click = 0;
        return 0;
    }
    suppress_next_click = 0;
    return 1;
}

// Analyzer magnitude (dB) under a plot x — the display bins are log-spaced over
// [MIN_FREQ, MAX_FREQ] with the same norm as freq_to_x, so x maps straight to a
// bin. Used by Spectrum Grab to detect a peak under the cursor.
function analyzer_db_at_x(x) {
    var n = analyzer_display.length;
    if (n < 2) return ANALYZER_MIN_DB;
    var norm = (x - plot_left()) / Math.max(1.0, plot_right() - plot_left());
    if (norm < 0.0 || norm > 1.0) return ANALYZER_MIN_DB;
    var bin = Math.round(norm * (n - 1));
    if (bin < 0) bin = 0;
    else if (bin >= n) bin = n - 1;
    return analyzer_display[bin];
}

// SPECTRUM GRAB (Pro-Q): find a prominent analyzer peak near plot-x and return
// its frequency, or -1 when there's no clear resonance to grab. Used so a
// double-click to ADD a band snaps onto the visible peak (you click the bump,
// the band lands on it), and so the hover affordance can mark the grab target.
// Conservative on purpose: on a flat/quiet spectrum it returns -1 (no snap), so
// placement away from peaks stays exactly where you clicked.
var GRAB_WIN = Math.round(ANALYZER_BINS * 0.04);   // +/- display bins (~0.45 octave each way, density-independent)
var GRAB_FLOOR_OVER = 18.0;   // peak must sit this far above the analyzer floor
var GRAB_PROMINENCE = 4.0;    // ...and this far above the local window average
function analyzer_peak_near_x(x) {
    var n = analyzer_display.length;
    if (n < 4 || !analyzer_enabled) return -1.0;
    var left = plot_left(), right = plot_right();
    var norm = (x - left) / Math.max(1.0, right - left);
    if (norm < 0.0 || norm > 1.0) return -1.0;
    var center = Math.round(norm * (n - 1));
    var lo = center - GRAB_WIN; if (lo < 0) lo = 0;
    var hi = center + GRAB_WIN; if (hi >= n) hi = n - 1;
    var best = -1, bestdb = ANALYZER_MIN_DB, sum = 0.0, cnt = 0, i;
    for (i = lo; i <= hi; i++) {
        var d = analyzer_display[i];
        sum += d; cnt++;
        if (d > bestdb) { bestdb = d; best = i; }
    }
    if (best < 0 || cnt < 3) return -1.0;
    if (bestdb < ANALYZER_MIN_DB + GRAB_FLOOR_OVER) return -1.0;
    if (bestdb - (sum / cnt) < GRAB_PROMINENCE) return -1.0;   // not a real bump
    // require a genuine local maximum (don't snap to a window edge sloping up)
    if (best > 0 && analyzer_display[best] < analyzer_display[best - 1]) return -1.0;
    if (best < n - 1 && analyzer_display[best] < analyzer_display[best + 1]) return -1.0;
    return Math.exp(LOG_MIN + (best / (n - 1)) * LOG_RANGE);
}

// ── Mouse interaction ────────────────────────────────────────────────
function handle_press(x, y, but, cmd, shift, opt, ctrl, pointerevent) {
    var hit = hit_test(x, y);
    var dynamic_hit = dynamic_hit_test(x, y);
    // Deterministic ring-vs-node arbitration. The ring only wins a drag-start
    // when it is genuinely closer than its band's node by a dead-zone margin
    // (DYNAMIC_GRAB_BIAS_SQ) — so tiny mouse jitter near a node that has its
    // dynamic ring nearby (e.g. a small/zero range) can no longer flip the
    // drag_mode between a gain edit and a ring edit. A ring with no competing
    // node (hit < 0) is always grabbable.
    var ring_wins = 0;
    if (dynamic_hit >= 0) {
        if (hit < 0) {
            ring_wins = 1;
        } else {
            ring_wins = ring_dist_sq(dynamic_hit, x, y) + DYNAMIC_GRAB_BIAS_SQ
                <= node_dist_sq(hit, x, y) ? 1 : 0;
        }
    }
    if (!ring_wins) dynamic_hit = -1;
    var clicked_band = dynamic_hit >= 0 ? dynamic_hit : hit;
    var menu_hit = node_menu_hit_test(x, y);
    var now_ms = new Date().getTime();
    var middle_click = pointer_middle_click(pointerevent, but);
    var context_click = pointer_context_click(pointerevent, but, ctrl);
    var option_click = pointer_option_key(pointerevent, opt);
    var command_click = pointer_command_key(pointerevent, cmd);
    var control_click = pointer_control_key(pointerevent, ctrl);
    var is_delete_double_click = (
        clicked_band >= 0 &&
        clicked_band === last_click_band &&
        (now_ms - last_click_ms) <= DOUBLE_CLICK_MS &&
        !option_click &&
        !control_click &&
        !command_click &&
        !context_click &&
        but <= 1
    );

    last_click_ms = now_ms;
    last_click_band = clicked_band;

    // Anchor every press for the Alt axis-constrain math; default to a non-Alt press.
    drag_start_x = x;
    drag_start_y = y;
    alt_drag_pending = 0;
    alt_moved = 0;
    constrain_axis = 0;

    if (middle_click) {
        dragging = 0;
        drag_mode = 0;
        mgraphics.redraw();
        return;
    }

    if (is_delete_double_click) {
        close_node_menu();
        reset_band_at(clicked_band);
        suppress_next_ondblclick_delete = 1;
        last_click_ms = 0;
        last_click_band = -1;
        return;
    }

    if (menu_band >= 0) {
        if (menu_hit && menu_hit !== "panel") {
            apply_menu_action(menu_hit);
            return;
        }
        if (!menu_hit) {
            // Click-off DISMISSES AND CONSUMES the press (standard popup
            // semantics) — falling through here silently added a band at the
            // click point (Live-verified), the exact "weird things when
            // clicking off" failure the fleet forbids.
            close_node_menu();
            mgraphics.redraw();
            return;
        }
        mgraphics.redraw();
        return;
    }

    // Pro-Q Cmd+Alt+click on a node: cycle the band type (PK->LS->HS->LP->
    // HP->NT->BP->AP->PK). apply_band_type owns all the outlet plumbing.
    if (command_click && option_click && clicked_band >= 0) {
        close_node_menu();
        selected_band = clicked_band;
        outlet(0, "selected_band", clicked_band);
        apply_band_type(clicked_band, (bands[clicked_band].type + 1) % TYPE_NAMES.length);
        mgraphics.redraw();
        return;
    }

    if (option_click) {
        if (dynamic_hit >= 0 || hit >= 0) {
            var opt_idx = dynamic_hit >= 0 ? dynamic_hit : hit;
            // Pro-Q: Alt+CLICK toggles the band bypass, Alt+DRAG constrains to one
            // axis. We can't tell which yet, so ARM a drag now and decide on release:
            // a tap (no travel) toggles bypass in onpointerup; a move constrains.
            selected_band = opt_idx;
            dragging = 1;
            drag_mode = (dynamic_hit >= 0) ? 2 : 1;
            drag_start_freq = bands[opt_idx].freq;
            drag_start_gain = bands[opt_idx].gain;
            drag_start_q = bands[opt_idx].q;
            drag_start_dynamic = bands[opt_idx].dynamic_amount || 0.0;
            alt_drag_pending = 1;
            outlet(0, "selected_band", opt_idx);
            close_node_menu();
            mgraphics.redraw();
            return;
        }
        // it173: alt/opt-click on EMPTY graph captures the live analyzer as a
        // static A/B reference (or clears it) — a Pro-Q-style compare. (A node
        // alt-click toggles that band, above; this only fires off a node.)
        if (x >= plot_left() && x <= plot_right() &&
                y >= plot_top() && y <= plot_bottom()) {
            toggle_analyzer_snapshot();
            return;
        }
    }

    if (context_click) {
        if (dynamic_hit >= 0 || hit >= 0) {
            selected_band = dynamic_hit >= 0 ? dynamic_hit : hit;
            dragging = 0;
            drag_mode = 0;
            outlet(0, "selected_band", selected_band);
            open_node_menu_for(selected_band, x, y);
            mgraphics.redraw();
            return;
        }
        dragging = 0;
        drag_mode = 0;
        mgraphics.redraw();
        return;
    }

    if (hit < 0 && dynamic_hit < 0) {
        // Pro-Q create gesture: a plain press on the empty graph spawns a band at
        // the click and immediately drags it — the band TYPE is chosen by WHERE you
        // clicked (band_type_for_x: far edges -> HP/LP, just inside -> shelves, the
        // middle -> bell). If a prominent analyzer peak sits under the cursor,
        // create_band_at snaps onto it (the Spectrum Grab "grab the resonance").
        // Modifier presses (opt/cmd/ctrl/context) keep their own jobs, below.
        if (!option_click && !context_click && !command_click && !control_click &&
                x >= plot_left() && x <= plot_right() &&
                y >= plot_top() && y <= plot_bottom() &&
                find_free_band() >= 0) {
            if (create_band_at(x, y)) {
                dragging = 1;
                drag_mode = 1;
                drag_start_freq = bands[selected_band].freq;
                drag_start_gain = bands[selected_band].gain;
                drag_start_q = bands[selected_band].q;
                return;
            }
        }
        selected_band = -1;
        dragging = 0;
        drag_mode = 0;
        close_node_menu();
        mgraphics.redraw();
        return;
    }

    if (dynamic_hit >= 0) {
        selected_band = dynamic_hit;
        dragging = 1;
        drag_mode = 2;
        close_node_menu();
        drag_start_dynamic = bands[dynamic_hit].dynamic_amount || 0.0;
        outlet(0, "selected_band", dynamic_hit);
        mgraphics.redraw();
        return;
    }

    if (hit >= 0) {
        selected_band = hit;
        dragging = 1;
        drag_mode = 1;
        close_node_menu();
        drag_start_freq = bands[hit].freq;
        drag_start_gain = bands[hit].gain;
        drag_start_q = bands[hit].q;
        outlet(0, "selected_band", hit);
    } else {
        selected_band = -1;
        dragging = 0;
        drag_mode = 0;
        close_node_menu();
    }
    mgraphics.redraw();
}

function reset_band_at(idx) {
    // Pro-Q semantics: double-click resets the band (gain bands -> 0 dB,
    // gain-less types -> default Q). Delete stays on the context menu.
    if (idx < 0 || idx >= num_bands) return;
    if (!bands[idx].present) return;
    selected_band = idx;
    if (band_cache[idx].uses_gain) {
        if (bands[idx].gain !== 0.0) {
            bands[idx].gain = 0.0;
            rebuild_band_cache();
            outlet(2, "band_gain", idx, 0.0);
        }
    } else if (bands[idx].q !== 1.0) {
        bands[idx].q = 1.0;
        rebuild_band_cache();
        outlet(3, "band_q", idx, 1.0);
    }
    outlet(0, "selected_band", idx);
    mgraphics.redraw();
}

function handle_double_click(x, y) {
    if (suppress_next_ondblclick_delete) {
        suppress_next_ondblclick_delete = 0;
        return;
    }

    var hit = hit_test(x, y);
    var dynamic_hit = dynamic_hit_test(x, y);

    if (dynamic_hit >= 0 || hit >= 0) {
        reset_band_at(dynamic_hit >= 0 ? dynamic_hit : hit);
        return;
    }
    // Empty double-clicks no longer create a band — a single press already does
    // (Pro-Q create gesture), so a double-click on empty space is a no-op.
}

function handle_drag_at(x, y, but, cmd, shift, opt) {
    if (but === 0) {
        dragging = 0;
        drag_mode = 0;
        mgraphics.redraw();
        return;
    }
    if (!dragging || selected_band < 0 || selected_band >= num_bands) return;

    // Once an Alt-armed drag travels, it's a constrain-drag, not a bypass tap.
    if (alt_drag_pending && (Math.abs(x - drag_start_x) > 2 || Math.abs(y - drag_start_y) > 2)) {
        alt_moved = 1;
    }

    var b = bands[selected_band];
    var cache = band_cache[selected_band];
    var new_dynamic;
    var new_freq = x_to_freq(x);
    var new_gain = b.gain;
    var new_q = b.q;
    var uses_gain = cache.uses_gain ? 1 : 0;
    var q_drag = 0;
    var target_y;

    if (menu_band >= 0) {
        close_node_menu();
    }

    if (drag_mode === 2) {
        new_dynamic = y_to_gain(y) - cache.node_gain;
        if (shift) {
            new_dynamic = b.dynamic_amount + (new_dynamic - b.dynamic_amount) * 0.15;
        }
        new_dynamic = Math.round(clamp(new_dynamic, -MAX_DYNAMIC_RANGE, MAX_DYNAMIC_RANGE) * 10.0) / 10.0;
        if (new_dynamic === b.dynamic_amount) return;
        bands[selected_band].dynamic = 1;
        bands[selected_band].dynamic_amount = new_dynamic;
        rebuild_band_cache();
        outlet(0, "band_dynamic", selected_band, 1);
        outlet(0, "band_dynamic_amount", selected_band, new_dynamic);
        mgraphics.redraw();
        return;
    }

    if (uses_gain && cmd) {
        // Pro-Q cmd-drag: HOLD the gain so vertical now drives the Q instead, so
        // you can tighten or widen a bell/shelf WITHOUT lifting the mouse button.
        new_gain = drag_start_gain;
        new_q = y_to_q(y);
        if (shift) {
            new_q = b.q + (new_q - b.q) * 0.15;
        }
        new_q = Math.round(new_q * 100.0) / 100.0;
        new_q = clamp(new_q, MIN_Q, MAX_Q);
        q_drag = 1;
    } else if (uses_gain) {
        target_y = y;
        new_gain = y_to_gain(target_y);
        if (shift) {
            new_gain = b.gain + (new_gain - b.gain) * 0.15;
        }
        new_gain = Math.round(new_gain * 10.0) / 10.0;
        new_gain = clamp(new_gain, MIN_GAIN, MAX_GAIN);
    } else {
        target_y = y;
        new_q = y_to_q(target_y);
        if (cmd) {
            new_q = drag_start_q;
        }
        if (shift) {
            new_q = b.q + (new_q - b.q) * 0.15;
        }
        new_q = Math.round(new_q * 100.0) / 100.0;
        new_q = clamp(new_q, MIN_Q, MAX_Q);
    }

    if (shift) {
        new_freq = b.freq + (new_freq - b.freq) * 0.15;
    }

    // Pro-Q Alt+drag: constrain to ONE axis, chosen by the dominant initial travel.
    // Horizontal -> frequency only (hold gain + Q); vertical -> gain/Q only (hold freq).
    if (opt && drag_mode === 1) {
        var adx = Math.abs(x - drag_start_x);
        var ady = Math.abs(y - drag_start_y);
        if (constrain_axis === 0 && (adx > 3 || ady > 3)) {
            constrain_axis = (adx >= ady) ? 1 : 2;
        }
        if (constrain_axis === 1) {
            new_gain = drag_start_gain;
            new_q = drag_start_q;
        } else if (constrain_axis === 2) {
            new_freq = drag_start_freq;
        } else {
            new_freq = drag_start_freq;
            new_gain = drag_start_gain;
            new_q = drag_start_q;
        }
    }

    // Continuous frequency (0.1 Hz resolution) — the old 10 Hz snap above
    // 1 kHz made the node stutter against the visual drag position. Display
    // formatting handles presentation rounding.
    new_freq = Math.round(new_freq * 10.0) / 10.0;
    new_freq = clamp(new_freq, MIN_FREQ, MAX_FREQ);

    var edits_gain = (uses_gain && !q_drag) ? 1 : 0;
    if (edits_gain && new_freq === b.freq && new_gain === b.gain) return;
    if (!edits_gain && new_freq === b.freq && new_q === b.q) return;

    bands[selected_band].freq = new_freq;
    if (edits_gain) {
        bands[selected_band].gain = new_gain;
    } else {
        bands[selected_band].q = new_q;
    }

    rebuild_band_cache();
    outlet(1, "band_freq", selected_band, new_freq);
    if (edits_gain) {
        outlet(2, "band_gain", selected_band, new_gain);
    } else {
        outlet(3, "band_q", selected_band, new_q);
    }
    mgraphics.redraw();
}

function handle_hover(x, y) {
    var prev = hover_band;
    var dynamic_hover;
    var prev_menu = menu_hover;
    dynamic_hover = dynamic_hit_test(x, y);
    hover_band = dynamic_hover >= 0 ? dynamic_hover : hit_test(x, y);
    if (menu_band >= 0) {
        menu_hover = node_menu_hit_test(x, y);
        if (menu_hover === "panel") menu_hover = "";
    } else {
        menu_hover = "";
    }
    var prev_in = hover_in_plot;
    hover_x = x;
    hover_y = y;
    hover_in_plot = (!dragging && x >= plot_left() && x <= plot_right() &&
                     y >= plot_top() && y <= plot_bottom()) ? 1 : 0;
    // Cursor: pointing hand over a grabbable node/ring/menu-chip, crosshair over
    // the open plot, default arrow otherwise. (Drag uses the grab hand, set at
    // press/drag time since onpointermove skips hover while a button is down.)
    ds_set_cursor((hover_band >= 0 || menu_hover) ? DS_CUR_HAND
               : (hover_in_plot ? DS_CUR_CROSS : DS_CUR_ARROW));
    if (hover_band !== prev || menu_hover !== prev_menu ||
            hover_in_plot || prev_in) {
        request_redraw();
    }
}

function clear_hover_state() {
    ds_set_cursor(DS_CUR_ARROW);
    if (hover_band >= 0 || menu_hover || hover_in_plot) {
        hover_band = -1;
        menu_hover = "";
        hover_in_plot = 0;
        mgraphics.redraw();
    }
}

// Pro-Q-style hover crosshair: faint guides from the cursor to the axes,
// with the exact frequency in the bottom gutter and gain in the left gutter.
function draw_hover_crosshair() {
    if (!hover_in_plot) return;
    var x = clamp(hover_x, plot_left(), plot_right());
    var y = clamp(hover_y, plot_top(), plot_bottom());
    mgraphics.set_source_rgba(TEXT_CLR[0], TEXT_CLR[1], TEXT_CLR[2], 0.46);
    mgraphics.set_line_width(1.0);
    mgraphics.move_to(x, plot_top()); mgraphics.line_to(x, plot_bottom()); mgraphics.stroke();
    mgraphics.move_to(plot_left(), y); mgraphics.line_to(plot_right(), y); mgraphics.stroke();

    // SPECTRUM GRAB affordance: if a clear analyzer peak is near the cursor, ring
    // it (this is where a double-click-add will snap) and read out its frequency.
    var snap_freq = analyzer_peak_near_x(x);
    if (snap_freq > 0.0) {
        var sx = freq_to_x(snap_freq);
        var sy = analyzer_db_to_y(analyzer_tilted_db(
            analyzer_db_at_x(sx), analyzer_slope_at(snap_freq)));
        mgraphics.set_source_rgba(ANALYZER_LINE_CLR[0], ANALYZER_LINE_CLR[1], ANALYZER_LINE_CLR[2], 0.95);
        mgraphics.set_line_width(1.4);
        mgraphics.arc(sx, sy, 4.2, 0.0, 6.2832); mgraphics.stroke();
        mgraphics.move_to(sx - 2.6, sy); mgraphics.line_to(sx + 2.6, sy); mgraphics.stroke();
        mgraphics.move_to(sx, sy - 2.6); mgraphics.line_to(sx, sy + 2.6); mgraphics.stroke();
    }

    mgraphics.select_font_face("Arial");
    mgraphics.set_font_size(8.0);
    // Frequency (+ musical note) under the cursor (bottom gutter); when grabbing a
    // peak, show the SNAP target frequency instead of the raw cursor frequency.
    var hover_freq = (snap_freq > 0.0) ? snap_freq : x_to_freq(x);
    var ftxt = format_freq_text(hover_freq) + " " + note_label(hover_freq);
    var fw = ftxt.length * 4.6 + 4;
    var fx = clamp(x - fw * 0.5, 0.0, mgraphics.size[0] - fw);
    mgraphics.set_source_rgba(0.05, 0.06, 0.08, 0.92);
    mgraphics.rectangle(fx, plot_bottom() + 1.0, fw, 10.0);
    mgraphics.fill();
    mgraphics.set_source_rgba(TEXT_CLR[0], TEXT_CLR[1], TEXT_CLR[2], 0.98);
    mgraphics.move_to(fx + 2.0, plot_bottom() + 8.5);
    mgraphics.show_text(ftxt);
    // Gain at the cursor (left gutter).
    var gv = y_to_gain(y);
    var gtxt = (gv >= 0 ? "+" : "") + gv.toFixed(1);
    mgraphics.set_source_rgba(0.05, 0.06, 0.08, 0.92);
    mgraphics.rectangle(0.0, y - 5.0, MARGIN_LEFT - 1.0, 10.0);
    mgraphics.fill();
    mgraphics.set_source_rgba(TEXT_CLR[0], TEXT_CLR[1], TEXT_CLR[2], 0.98);
    mgraphics.move_to(1.0, y + 2.5);
    mgraphics.show_text(gtxt);
}

function onpointerdown(pointerevent) {
    var x = pointer_x(pointerevent, 0);
    var y = pointer_y(pointerevent, 0);
    if (sketch_mode) {
        // right-click during sketch = ABORT the stroke (dismiss-and-consume;
        // sketch_cancel was orphaned — every overlay needs an escape hatch)
        if (pointer_context_click(pointerevent, pointer_buttons(pointerevent, 1), 0)) {
            sketch_cancel();
            return;
        }
        sketch_begin(x, y);
        return;
    }
    note_pointer_press(x, y);
    handle_press(
        x,
        y,
        pointer_buttons(pointerevent, 1),
        pointer_command_key(pointerevent, 0),
        pointer_shift_key(pointerevent, 0),
        pointer_option_key(pointerevent, 0),
        pointer_control_key(pointerevent, 0),
        pointerevent
    );
    if (dragging) ds_set_cursor(DS_CUR_GRAB);
}

function onpointermove(pointerevent) {
    var buttons = pointer_buttons(pointerevent, 0);
    var x = pointer_x(pointerevent, 0);
    var y = pointer_y(pointerevent, 0);
    if (sketching) {
        if ((buttons & 1) !== 0) sketch_extend(x, y);
        else sketch_commit();
        return;
    }
    if (dragging && ((buttons & 1) !== 0)) {
        ds_set_cursor(DS_CUR_GRAB);
        handle_drag_at(
            x,
            y,
            buttons,
            pointer_command_key(pointerevent, 0),
            pointer_shift_key(pointerevent, 0),
            pointer_option_key(pointerevent, 0)
        );
        return;
    }
    if (dragging && buttons === 0) {
        dragging = 0;
        drag_mode = 0;
    }
    handle_hover(x, y);
}

function onpointerup(pointerevent) {
    var x = pointer_x(pointerevent, 0);
    var y = pointer_y(pointerevent, 0);
    if (sketching) { sketch_commit(); return; }
    if (dragging) {
        // Pro-Q: an Alt+CLICK (armed a drag but never travelled) toggles band bypass.
        if (alt_drag_pending && !alt_moved && selected_band >= 0 && selected_band < num_bands) {
            bands[selected_band].enabled = bands[selected_band].enabled ? 0 : 1;
            rebuild_band_cache();
            outlet(0, "band_enable", selected_band, bands[selected_band].enabled);
        }
        dragging = 0;
        drag_mode = 0;
        alt_drag_pending = 0;
        alt_moved = 0;
        constrain_axis = 0;
        mgraphics.redraw();
    } else {
        handle_hover(x, y);
    }
}

function onpointerleave(pointerevent) {
    if (sketching) { sketch_commit(); return; }
    if (dragging && pointerevent && pointerevent.buttons === 0) {
        dragging = 0;
        drag_mode = 0;
    }
    clear_hover_state();
}

function onclick(x, y, but, cmd, shift, caps, opt, ctrl, pointerevent) {
    if (sketch_mode) return;
    if (should_ignore_pointer_click(x, y)) return;
    handle_press(x, y, but, cmd, shift, opt, ctrl, pointerevent);
}

function ondblclick(x, y, but, cmd, shift, caps, opt, ctrl) {
    if (sketch_mode) return;
    handle_double_click(x, y);
}

function ondrag(x, y, but, cmd, shift, caps, opt, ctrl) {
    if (sketch_mode) return;
    handle_drag_at(x, y, but, cmd, shift, opt);
}

function onidle(x, y, but, cmd, shift, caps, opt, ctrl) {
    handle_hover(x, y);
}

function onidleout(x, y, but, cmd, shift, caps, opt, ctrl) {
    clear_hover_state();
}

function onwheel(x, y, scrollx, scrolly, cmd, shift, caps, opt, ctrl) {
    // Pro-Q wheel matrix (Shift = fine everywhere):
    //   plain      -> Q
    //   Cmd/Ctrl   -> gain
    //   Alt        -> dynamic range (auto-enables DYN, like the menu chip)
    //   Alt+Cmd    -> linked gain<->dynamic trade (gain +x, dynamic -x)
    var target = hover_band >= 0 ? hover_band : selected_band;
    if (target < 0 || target >= num_bands) return;
    if (!bands[target].enabled) return;
    var b = bands[target];
    var uses_gain = band_uses_gain(b.type);
    var cmd_mod = cmd || ctrl;

    if (opt && cmd_mod) {
        if (!uses_gain || !band_supports_dynamic(b.type)) return;
        var step_l = (shift ? 0.1 : 0.5) * (scrolly > 0 ? 1 : -1);
        if (!scrolly) return;
        var ng = Math.round(clamp(b.gain + step_l, MIN_GAIN, MAX_GAIN) * 10.0) / 10.0;
        var nd = Math.round(clamp((b.dynamic_amount || 0.0) - step_l,
                                  -MAX_DYNAMIC_RANGE, MAX_DYNAMIC_RANGE) * 10.0) / 10.0;
        if (ng === b.gain && nd === (b.dynamic_amount || 0.0)) return;
        b.gain = ng;
        b.dynamic = 1;
        b.dynamic_amount = nd;
        rebuild_band_cache();
        outlet(2, "band_gain", target, ng);
        outlet(0, "band_dynamic", target, 1);
        outlet(0, "band_dynamic_amount", target, nd);
        mgraphics.redraw();
        return;
    }

    if (opt) {
        if (!band_supports_dynamic(b.type)) return;
        var step_d = (shift ? 0.1 : 0.5) * (scrolly > 0 ? 1 : -1);
        if (!scrolly) return;
        var nd2 = Math.round(clamp((b.dynamic_amount || 0.0) + step_d,
                                   -MAX_DYNAMIC_RANGE, MAX_DYNAMIC_RANGE) * 10.0) / 10.0;
        if (nd2 === (b.dynamic_amount || 0.0)) return;
        b.dynamic = 1;
        b.dynamic_amount = nd2;
        rebuild_band_cache();
        outlet(0, "band_dynamic", target, 1);
        outlet(0, "band_dynamic_amount", target, nd2);
        mgraphics.redraw();
        return;
    }

    if (cmd_mod) {
        if (!uses_gain) return;
        var step_g = (shift ? 0.1 : 0.5) * (scrolly > 0 ? 1 : -1);
        if (!scrolly) return;
        var ng2 = Math.round(clamp(b.gain + step_g, MIN_GAIN, MAX_GAIN) * 10.0) / 10.0;
        if (ng2 === b.gain) return;
        b.gain = ng2;
        rebuild_band_cache();
        outlet(2, "band_gain", target, ng2);
        mgraphics.redraw();
        return;
    }

    var q = b.q;
    var factor = shift ? 0.02 : 0.08;
    q = q * (1.0 + scrolly * factor);
    q = clamp(q, MIN_Q, MAX_Q);
    q = Math.round(q * 100.0) / 100.0;
    if (q === b.q) return;

    b.q = q;
    rebuild_band_cache();
    outlet(3, "band_q", target, q);
    mgraphics.redraw();
}

function format_dynamic_amount(v) {
    var prefix = v > 0 ? "+" : "";
    return prefix + v.toFixed(1) + " dB";
}
""")
