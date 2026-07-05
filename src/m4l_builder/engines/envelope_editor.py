"""Draggable ADSR envelope editor for jsui (dnksaus-catalog kit engine #1).

The dnksaus Auto Gate / dnkFM envelope look, as an INTERACTIVE editor: a dark
graph with an accent envelope polyline (attack rise 0->1, decay to the sustain
level, fixed-width sustain plateau, release back to 0), subtle fill under the
curve, a dim grid, square draggable nodes, and a value row beneath the plot
(A / D / S / R readouts). Segment widths scale with ``sqrt(time/max)`` inside
fixed per-segment slots, so short times stay readable (log-ish feel) and a
drag on one node never re-scales the whole graph.

FOUR draggable nodes (onclick/ondrag hit-test the nearest node in a grab
radius -- the crossover_display jsui idiom):
    0 -- attack peak     (x -> attack ms)
    1 -- decay knee      (x -> decay ms, y -> sustain level)
    2 -- sustain plateau (y -> sustain level)
    3 -- release end     (x -> release ms)

Inlets (4) -- param back-sync (set + redraw ONLY; inbound values never
re-emit, so wiring a live.dial both ways cannot echo-storm):
    0 -- attack ms    1 -- decay ms    2 -- sustain (0..1)    3 -- release ms

Outlets (4) -- emitted ONLY while dragging, and only the dragged value(s)
(the decay knee owns two axes so it emits decay + sustain):
    0 -- attack ms    1 -- decay ms    2 -- sustain (0..1)    3 -- release ms

``set_phase`` is a reserved no-op hook for a future live trigger / progress
cursor (feed it 0..1 later; today it only stores the value).
"""

from string import Template

ENVELOPE_EDITOR_INLETS = 4
ENVELOPE_EDITOR_OUTLETS = 4


def envelope_editor_js(
    *,
    accent="0.36, 0.92, 0.96, 1.0",
    bg="0.05, 0.05, 0.06, 1.0",
    grid_color="0.22, 0.24, 0.28, 0.45",
    text_color="0.92, 0.95, 0.98, 0.95",
    label_color="0.52, 0.56, 0.63, 0.9",
    fill_color=None,
    node_fill="0.88, 0.92, 0.96, 1.0",
    node_stroke="0.05, 0.05, 0.06, 1.0",
    max_attack_ms=2000.0,
    max_decay_ms=4000.0,
    max_release_ms=8000.0,
    init_attack_ms=10.0,
    init_decay_ms=200.0,
    init_sustain=0.7,
    init_release_ms=400.0,
    sustain_frac=0.16,
):
    """Return ES5 JavaScript for a draggable ADSR envelope editor (Max jsui).

    Colors are RGBA strings (``"r, g, b, a"``). ``fill_color=None`` derives the
    under-curve wash from ``accent`` at low alpha so a custom accent tints the
    fill too. Ranges are template params: attack ``0..max_attack_ms``, decay
    ``0..max_decay_ms``, sustain ``0..1``, release ``0..max_release_ms``; the
    ``init_*`` values are the first paint (match them to the bound params'
    initials so the curve is honest before any automation arrives).
    ``sustain_frac`` is the fixed plateau fraction of the plot width.
    """
    if fill_color is None:
        parts = [p.strip() for p in accent.split(",")]
        fill_color = ", ".join(parts[:3]) + ", 0.13"
    return _JS_TEMPLATE.substitute(
        accent=accent,
        bg=bg,
        grid_color=grid_color,
        text_color=text_color,
        label_color=label_color,
        fill_color=fill_color,
        node_fill=node_fill,
        node_stroke=node_stroke,
        max_a=float(max_attack_ms),
        max_d=float(max_decay_ms),
        max_r=float(max_release_ms),
        init_a=float(init_attack_ms),
        init_d=float(init_decay_ms),
        init_s=float(init_sustain),
        init_r=float(init_release_ms),
        sustain_frac=float(sustain_frac),
    )


_JS_TEMPLATE = Template("""\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 4;
outlets = 4;

var BG_COLOR    = [$bg];
var GRID_COLOR  = [$grid_color];
var TEXT_COLOR  = [$text_color];
var LABEL_COLOR = [$label_color];
var ACCENT      = [$accent];
var FILL_COLOR  = [$fill_color];
var NODE_FILL   = [$node_fill];
var NODE_STROKE = [$node_stroke];

// ranges (ms; sustain is 0..1)
var MAX_A = $max_a;
var MAX_D = $max_d;
var MAX_R = $max_r;

var attack_ms  = $init_a;
var decay_ms   = $init_d;
var sustain    = $init_s;
var release_ms = $init_r;

// geometry: A/D/R segment widths scale with sqrt(time/max) inside FIXED
// per-segment slots; the sustain plateau is a fixed fraction of the plot.
var SUSTAIN_FRAC = $sustain_frac;
var SEG_FRAC = (1.0 - SUSTAIN_FRAC) / 3.0;

var MARGIN_L = 6;
var MARGIN_R = 6;
var MARGIN_T = 7;
var MARGIN_B = 16;          // the value row lives below the plot

// interaction: 0=attack peak, 1=decay knee, 2=sustain plateau, 3=release end
var drag_target = -1;
var NODE_HIT  = 14.0;       // grab radius (px)
var NODE_HALF = 3.0;        // square node half-size (px)

// reserved: live trigger / progress cursor (future engine rev draws it)
var play_phase = -1;
function set_phase(v) { play_phase = v; }

function plot_left()   { return MARGIN_L; }
function plot_right()  { return mgraphics.size[0] - MARGIN_R; }
function plot_top()    { return MARGIN_T; }
function plot_bottom() { return mgraphics.size[1] - MARGIN_B; }
function plot_w()      { return plot_right() - plot_left(); }
function plot_h()      { return plot_bottom() - plot_top(); }

function set_rgba(c) { mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]); }

function clamp01(v) { if (v < 0) return 0; if (v > 1) return 1; return v; }
function clamp_time(v, tmax) { if (v < 0) return 0; if (v > tmax) return tmax; return v; }

// sqrt time scaling: perceptual spread for short times inside a fixed slot.
function seg_w(t, tmax) {
    var n = (tmax > 0) ? t / tmax : 0;
    return Math.sqrt(clamp01(n)) * SEG_FRAC * plot_w();
}

// inverse: px offset inside a segment slot -> time, clamped to 0..tmax.
function seg_time(px, tmax) {
    var span = SEG_FRAC * plot_w();
    var n = clamp01((span > 0) ? px / span : 0);
    return n * n * tmax;
}

function env_y(level) { return plot_bottom() - clamp01(level) * plot_h(); }

function ax() { return plot_left() + seg_w(attack_ms, MAX_A); }   // attack peak x
function dx() { return ax() + seg_w(decay_ms, MAX_D); }           // decay knee x
function sx() { return dx() + SUSTAIN_FRAC * plot_w(); }          // plateau end x
function rx() { return sx() + seg_w(release_ms, MAX_R); }         // release end x

function node_x(i) {
    if (i === 0) return ax();
    if (i === 1) return dx();
    if (i === 2) return (dx() + sx()) * 0.5;
    return rx();
}

function node_y(i) {
    if (i === 0) return env_y(1);
    if (i === 3) return env_y(0);
    return env_y(sustain);
}

function format_ms(ms) {
    if (ms >= 1000) return (ms / 1000.0).toFixed(2) + "s";
    if (ms >= 100) return Math.round(ms) + "ms";
    return ms.toFixed(1) + "ms";
}

// ---- drawing -------------------------------------------------------------
function draw_background() {
    set_rgba(BG_COLOR);
    mgraphics.rectangle(0, 0, mgraphics.size[0], mgraphics.size[1]);
    mgraphics.fill();
}

function draw_grid() {
    var i, y;
    set_rgba(GRID_COLOR);
    mgraphics.set_line_width(1.0);
    for (i = 1; i <= 3; i++) {
        y = plot_top() + plot_h() * i / 4.0;
        mgraphics.move_to(plot_left(), y);
        mgraphics.line_to(plot_right(), y);
        mgraphics.stroke();
    }
    mgraphics.move_to(plot_left(), plot_bottom());
    mgraphics.line_to(plot_right(), plot_bottom());
    mgraphics.stroke();
}

function trace_envelope() {
    mgraphics.move_to(plot_left(), env_y(0));
    mgraphics.line_to(ax(), env_y(1));
    mgraphics.line_to(dx(), env_y(sustain));
    mgraphics.line_to(sx(), env_y(sustain));
    mgraphics.line_to(rx(), env_y(0));
}

function draw_envelope() {
    trace_envelope();                 // subtle fill under the curve
    mgraphics.close_path();
    set_rgba(FILL_COLOR);
    mgraphics.fill();

    trace_envelope();                 // accent polyline on top
    set_rgba(ACCENT);
    mgraphics.set_line_width(1.6);
    mgraphics.stroke();
}

function draw_nodes() {
    var i, x, y;
    for (i = 0; i < 4; i++) {
        x = node_x(i);
        y = node_y(i);
        set_rgba((i === drag_target) ? ACCENT : NODE_FILL);
        mgraphics.rectangle(x - NODE_HALF, y - NODE_HALF, NODE_HALF * 2, NODE_HALF * 2);
        mgraphics.fill();
        set_rgba(NODE_STROKE);
        mgraphics.set_line_width(1.0);
        mgraphics.rectangle(x - NODE_HALF, y - NODE_HALF, NODE_HALF * 2, NODE_HALF * 2);
        mgraphics.stroke();
    }
}

function draw_value_row() {
    var labels = ["A", "D", "S", "R"];
    var values = [format_ms(attack_ms), format_ms(decay_ms),
                  sustain.toFixed(2), format_ms(release_ms)];
    var cell = (mgraphics.size[0] - MARGIN_L - MARGIN_R) / 4.0;
    var ty = mgraphics.size[1] - 5;
    var i, cx;
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(7.5);
    for (i = 0; i < 4; i++) {
        cx = plot_left() + i * cell;
        set_rgba(LABEL_COLOR);
        mgraphics.move_to(cx, ty);
        mgraphics.show_text(labels[i]);
        set_rgba(TEXT_COLOR);
        mgraphics.move_to(cx + 9, ty);
        mgraphics.show_text(values[i]);
    }
}

function paint() {
    attack_ms  = clamp_time(attack_ms, MAX_A);
    decay_ms   = clamp_time(decay_ms, MAX_D);
    sustain    = clamp01(sustain);
    release_ms = clamp_time(release_ms, MAX_R);
    draw_background();
    draw_grid();
    draw_envelope();
    draw_nodes();
    draw_value_row();
}

// ---- interaction -----------------------------------------------------------
function nearest_node(x, y) {
    var best = -1;
    var bestd = NODE_HIT * NODE_HIT;
    var i, ddx, ddy, d;
    for (i = 0; i < 4; i++) {
        ddx = x - node_x(i);
        ddy = y - node_y(i);
        d = ddx * ddx + ddy * ddy;
        if (d <= bestd) { bestd = d; best = i; }
    }
    return best;
}

// Emit ONLY the dragged value(s): the knee owns two axes (decay x, sustain y);
// every other node owns exactly one outlet. Inbound msg_float never lands here.
function apply_drag(x, y) {
    if (drag_target === 0) {
        attack_ms = seg_time(x - plot_left(), MAX_A);
        outlet(0, attack_ms);
    } else if (drag_target === 1) {
        decay_ms = seg_time(x - ax(), MAX_D);
        sustain = clamp01((plot_bottom() - y) / plot_h());
        outlet(1, decay_ms);
        outlet(2, sustain);
    } else if (drag_target === 2) {
        sustain = clamp01((plot_bottom() - y) / plot_h());
        outlet(2, sustain);
    } else if (drag_target === 3) {
        release_ms = seg_time(x - sx(), MAX_R);
        outlet(3, release_ms);
    }
    mgraphics.redraw();
}

function onclick(x, y, but, cmd, shift, capslock, option, ctrl) {
    drag_target = nearest_node(x, y);
    if (drag_target >= 0) apply_drag(x, y);
}

function ondrag(x, y, but, cmd, shift, capslock, option, ctrl) {
    if (but === 0) { drag_target = -1; mgraphics.redraw(); return; }
    if (drag_target < 0) return;
    apply_drag(x, y);
}

// ---- param back-sync (inlets 0-3): set + redraw, NEVER re-emit -------------
function msg_float(v) {
    if (inlet === 0) attack_ms = clamp_time(v, MAX_A);
    else if (inlet === 1) decay_ms = clamp_time(v, MAX_D);
    else if (inlet === 2) sustain = clamp01(v);
    else if (inlet === 3) release_ms = clamp_time(v, MAX_R);
    mgraphics.redraw();
}

function msg_int(v) { msg_float(v); }
""")
