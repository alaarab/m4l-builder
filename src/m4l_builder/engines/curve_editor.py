"""General breakpoint curve editor for jsui (dnksaus-catalog kit engines #2-#6).

The Multi Shaper core widget: N draggable breakpoints on a dark plot with an
accent curve, a dim N-division grid, square nodes, a value row beneath the plot
("5 pt / Curve 40% / Grid 4 / Snap"), a live "X 59 Y 60" cursor readout while
dragging, and a loop-glyph rendering hook. Corpus grounding: dnksaus builds its
curves by rebuilding a native ``[function]`` object from SCALAR Live params
(FunctionHandler.maxpat: indexed point messages like ``1 <x> <y> <curve>``,
mid-x clamped 1..126 so ``[function]`` never renumbers its points) —
this engine is the kit-native generalization: our own jsui editor with the SAME
neighbor-clamp rule and the same scalar-param persistence story (see
``Device.add_curve_editor``).

Gestures (the proven jsui onclick/ondrag idiom + native ondblclick):
    click empty plot   -- ADD a point there (snapped if snap is on), up to
                          ``max_points``; the new point is grabbed for placing
    drag a node        -- MOVE it: x clamped strictly between its neighbors
                          (endpoints' x locked to 0 / 1), y clamped 0..1;
                          snap quantizes both axes to the grid divisions
    double-click node  -- DELETE it (endpoints undeletable; a point added by
                          the immediately-preceding click is guarded so a
                          double-click on empty nets ONE point, not zero)

Interpolation (documented contract): cosine-blend. Within each segment,
``y(t) = y0 + (y1 - y0) * ((1-k)*t + k*(1 - cos(pi*t))/2)`` with
``k = tension/100``. Tension 0 = exact linear polyline; 100 = full cosine
ease per segment (horizontal tangents at every node -- heavy smoothing). The
curve passes through every breakpoint at ANY tension and never overshoots
(monotone within each segment), unlike Catmull-Rom style splines.

Inlet (1) -- messages only (never re-emit; all are ignored mid-drag so a
restore cascade can never fight a live gesture):
    set_points x0 y0 x1 y1 ...  -- back-sync/restore: replace all breakpoints
                                   (normalized 0..1 pairs; sorted, endpoints
                                   forced to x=0 / x=1, capped at max_points)
    set_all n x0 y0 ... x15 y15 -- wrapper-internal restore (count-first fixed
                                   slot layout fed by the hidden param pak)
    set_tension v               -- 0..100 global smoothing
    set_grid n                  -- grid divisions (1..64)
    set_snap v                  -- 0/1 quantize drags to the grid
    set_loop v                  -- 0/1 loop-glyph rendering hook (visual only)

Outlet (1) -- ``points x0 y0 x1 y1 ...`` (normalized 0..1), emitted on ANY
edit (add / move / delete). The points list is the persistence payload; no
eval outlet (evaluate host-side or via a future rev), no tension outlet (no
on-graph tension gesture -- tension arrives on the inlet from its own param).
"""

from string import Template

CURVE_EDITOR_INLETS = 1
CURVE_EDITOR_OUTLETS = 1


def curve_editor_js(
    *,
    accent="0.36, 0.92, 0.96, 1.0",
    bg="0.05, 0.05, 0.06, 1.0",
    grid_color="0.22, 0.24, 0.28, 0.45",
    text_color="0.92, 0.95, 0.98, 0.95",
    label_color="0.52, 0.56, 0.63, 0.9",
    fill_color=None,
    node_fill="0.88, 0.92, 0.96, 1.0",
    node_stroke="0.05, 0.05, 0.06, 1.0",
    max_points=16,
    init_y0=0.0,
    init_y1=1.0,
    init_tension=0.0,
    init_grid=4,
    init_snap=0,
    init_loop=0,
):
    """Return ES5 JavaScript for a general breakpoint curve editor (Max jsui).

    Colors are RGBA strings (``"r, g, b, a"``); ``fill_color=None`` derives the
    under-curve wash from ``accent`` at low alpha. ``max_points`` caps how many
    breakpoints a click can add (2..64). The default curve is the two endpoints
    ``(0, init_y0)`` and ``(1, init_y1)``; ``init_tension`` (0..100),
    ``init_grid`` (divisions), ``init_snap`` and ``init_loop`` (0/1) seed the
    first paint -- match them to the bound params' initials so the widget is
    honest before any value arrives.
    """
    max_points = int(max_points)
    if not 2 <= max_points <= 64:
        raise ValueError(f"max_points must be 2..64, got {max_points}")
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
        max_points=max_points,
        init_y0=float(init_y0),
        init_y1=float(init_y1),
        init_tension=float(init_tension),
        init_grid=int(init_grid),
        init_snap=int(bool(init_snap)),
        init_loop=int(bool(init_loop)),
    )


_JS_TEMPLATE = Template("""\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

var BG_COLOR    = [$bg];
var GRID_COLOR  = [$grid_color];
var TEXT_COLOR  = [$text_color];
var LABEL_COLOR = [$label_color];
var ACCENT      = [$accent];
var FILL_COLOR  = [$fill_color];
var NODE_FILL   = [$node_fill];
var NODE_STROKE = [$node_stroke];

var MAX_POINTS = $max_points;

// breakpoints: parallel arrays, normalized 0..1, ALWAYS sorted by x with
// xs[0] === 0 and xs[last] === 1 (the undeletable endpoints).
var xs = [0.0, 1.0];
var ys = [$init_y0, $init_y1];

var tension = $init_tension;   // 0..100 global smoothing (cosine blend)
var grid_n  = $init_grid;      // grid divisions (drawn always, snapped when on)
var snap_on = $init_snap;
var loop_on = $init_loop;      // loop-glyph rendering hook (visual only)

// dnksaus FunctionHandler rule, generalized: a point must never cross its
// neighbors ("Point 1 should never be set to the left of point 0 or to the
// right of point 2, otherwise [function] will renumber the points").
var MIN_DX = 0.001;

var drag_target = -1;
var just_added  = -1;          // dblclick-on-empty guard: keep the fresh point
var drag_nx = 0.0;             // live X/Y readout while dragging
var drag_ny = 0.0;
var NODE_HIT  = 12.0;          // grab radius (px)
var NODE_HALF = 3.0;           // square node half-size (px)

var MARGIN_L = 6;
var MARGIN_R = 6;
var MARGIN_T = 6;
var MARGIN_B = 15;             // the value row lives below the plot

function plot_left()   { return MARGIN_L; }
function plot_right()  { return mgraphics.size[0] - MARGIN_R; }
function plot_top()    { return MARGIN_T; }
function plot_bottom() { return mgraphics.size[1] - MARGIN_B; }
function plot_w()      { return plot_right() - plot_left(); }
function plot_h()      { return plot_bottom() - plot_top(); }

function set_rgba(c) { mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]); }
function clamp01(v) { if (v < 0) return 0; if (v > 1) return 1; return v; }

function to_px_x(nx) { return plot_left() + clamp01(nx) * plot_w(); }
function to_px_y(ny) { return plot_bottom() - clamp01(ny) * plot_h(); }
function from_px_x(x) { return clamp01((x - plot_left()) / plot_w()); }
function from_px_y(y) { return clamp01((plot_bottom() - y) / plot_h()); }

// snap: quantize a normalized value to the grid divisions when snap is on.
function snap_q(v) {
    if (!snap_on || grid_n < 1) return v;
    return clamp01(Math.round(v * grid_n) / grid_n);
}

// ---- interpolation: cosine blend (SEE module docstring for the contract) ---
function seg_shape(t) { return (1 - Math.cos(Math.PI * t)) / 2; }

function curve_y_at(gx) {
    var i, t, k, m, dx;
    if (gx <= xs[0]) return ys[0];
    if (gx >= xs[xs.length - 1]) return ys[ys.length - 1];
    for (i = 0; i < xs.length - 1; i++) {
        if (gx <= xs[i + 1]) {
            dx = xs[i + 1] - xs[i];
            t = (dx > 0) ? (gx - xs[i]) / dx : 0;
            k = tension / 100.0;
            m = (1 - k) * t + k * seg_shape(t);
            return ys[i] + (ys[i + 1] - ys[i]) * m;
        }
    }
    return ys[ys.length - 1];
}

// ---- edit plumbing ---------------------------------------------------------
function emit_points() {
    var args = [0, "points"], i;
    for (i = 0; i < xs.length; i++) { args.push(xs[i]); args.push(ys[i]); }
    outlet.apply(this, args);
}

function nearest_node(x, y) {
    var best = -1;
    var bestd = NODE_HIT * NODE_HIT;
    var i, ddx, ddy, d;
    for (i = 0; i < xs.length; i++) {
        ddx = x - to_px_x(xs[i]);
        ddy = y - to_px_y(ys[i]);
        d = ddx * ddx + ddy * ddy;
        if (d <= bestd) { bestd = d; best = i; }
    }
    return best;
}

function insert_point(nx, ny) {
    var j = 1;
    while (j < xs.length - 1 && xs[j] <= nx) j++;
    // keep strictly inside the neighbors (the FunctionHandler rule)
    if (nx <= xs[j - 1]) nx = xs[j - 1] + MIN_DX;
    if (nx >= xs[j]) nx = xs[j] - MIN_DX;
    xs.splice(j, 0, nx);
    ys.splice(j, 0, clamp01(ny));
    return j;
}

// replace all breakpoints from flat pairs; sanitize to the sorted/endpoint
// invariant. Shared by set_points (public) and set_all (wrapper restore).
function apply_pairs(flat) {
    var pairs = [], i, n;
    for (i = 0; i + 1 < flat.length; i += 2) {
        pairs.push([clamp01(flat[i]), clamp01(flat[i + 1])]);
    }
    if (pairs.length < 2) return;
    if (pairs.length > MAX_POINTS) pairs.length = MAX_POINTS;
    pairs.sort(function (a, b) { return a[0] - b[0]; });
    n = pairs.length;
    pairs[0][0] = 0.0;
    pairs[n - 1][0] = 1.0;
    xs = []; ys = [];
    for (i = 0; i < n; i++) {
        if (i > 0 && i < n - 1 && pairs[i][0] <= xs[i - 1]) {
            pairs[i][0] = Math.min(xs[i - 1] + MIN_DX, 1.0 - MIN_DX);
        }
        xs.push(pairs[i][0]);
        ys.push(pairs[i][1]);
    }
}

// ---- drawing ---------------------------------------------------------------
function draw_background() {
    set_rgba(BG_COLOR);
    mgraphics.rectangle(0, 0, mgraphics.size[0], mgraphics.size[1]);
    mgraphics.fill();
}

function draw_grid() {
    var i, x, y;
    set_rgba(GRID_COLOR);
    mgraphics.set_line_width(1.0);
    for (i = 1; i < grid_n; i++) {
        x = plot_left() + plot_w() * i / grid_n;
        mgraphics.move_to(x, plot_top());
        mgraphics.line_to(x, plot_bottom());
        mgraphics.stroke();
        y = plot_top() + plot_h() * i / grid_n;
        mgraphics.move_to(plot_left(), y);
        mgraphics.line_to(plot_right(), y);
        mgraphics.stroke();
    }
    mgraphics.move_to(plot_left(), plot_bottom());
    mgraphics.line_to(plot_right(), plot_bottom());
    mgraphics.stroke();
}

function trace_curve() {
    var sx, gx;
    mgraphics.move_to(to_px_x(0), to_px_y(ys[0]));
    for (sx = plot_left() + 2; sx < plot_right(); sx += 2) {
        gx = (sx - plot_left()) / plot_w();
        mgraphics.line_to(sx, to_px_y(curve_y_at(gx)));
    }
    mgraphics.line_to(to_px_x(1), to_px_y(ys[ys.length - 1]));
}

function draw_curve() {
    trace_curve();                 // subtle wash under the curve
    mgraphics.line_to(plot_right(), plot_bottom());
    mgraphics.line_to(plot_left(), plot_bottom());
    mgraphics.close_path();
    set_rgba(FILL_COLOR);
    mgraphics.fill();

    trace_curve();                 // accent line on top
    set_rgba(ACCENT);
    mgraphics.set_line_width(1.6);
    mgraphics.stroke();
}

function draw_nodes() {
    var i, x, y;
    for (i = 0; i < xs.length; i++) {
        x = to_px_x(xs[i]);
        y = to_px_y(ys[i]);
        set_rgba((i === drag_target) ? ACCENT : NODE_FILL);
        mgraphics.rectangle(x - NODE_HALF, y - NODE_HALF, NODE_HALF * 2, NODE_HALF * 2);
        mgraphics.fill();
        set_rgba(NODE_STROKE);
        mgraphics.set_line_width(1.0);
        mgraphics.rectangle(x - NODE_HALF, y - NODE_HALF, NODE_HALF * 2, NODE_HALF * 2);
        mgraphics.stroke();
    }
}

// the Multi Shaper footer: "5 pt   Curve 40%   Grid 4   Snap"
function draw_value_row() {
    var ty = mgraphics.size[1] - 4;
    var cell = (mgraphics.size[0] - MARGIN_L - MARGIN_R) / 4.0;
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(7.5);
    set_rgba(TEXT_COLOR);
    mgraphics.move_to(plot_left(), ty);
    mgraphics.show_text(xs.length + " pt");
    set_rgba(LABEL_COLOR);
    mgraphics.move_to(plot_left() + cell, ty);
    mgraphics.show_text("Curve " + Math.round(tension) + "%");
    mgraphics.move_to(plot_left() + cell * 2, ty);
    mgraphics.show_text("Grid " + grid_n);
    set_rgba(snap_on ? TEXT_COLOR : LABEL_COLOR);
    mgraphics.move_to(plot_left() + cell * 3, ty);
    mgraphics.show_text(snap_on ? "Snap" : "snap");
}

// "X 59 Y 60" live cursor telemetry while dragging (normalized 0..100)
function format_xy() {
    return "X " + Math.round(drag_nx * 100) + " Y " + Math.round(drag_ny * 100);
}

function draw_drag_readout() {
    if (drag_target < 0) return;
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(7.5);
    set_rgba(TEXT_COLOR);
    mgraphics.move_to(plot_right() - 52, plot_top() + 8);
    mgraphics.show_text(format_xy());
}

// loop-glyph rendering hook: a small circular arrow, top-left (visual only)
function draw_loop_glyph() {
    if (!loop_on) return;
    var cx = plot_left() + 8;
    var cy = plot_top() + 8;
    var r = 4.0;
    set_rgba(LABEL_COLOR);
    mgraphics.set_line_width(1.2);
    mgraphics.arc(cx, cy, r, 0.5, Math.PI * 1.8);
    mgraphics.stroke();
    mgraphics.move_to(cx + r + 1.5, cy + 1.5);
    mgraphics.line_to(cx + r, cy - 1.5);
    mgraphics.line_to(cx + r - 3.0, cy + 1.0);
    mgraphics.close_path();
    set_rgba(LABEL_COLOR);
    mgraphics.fill();
}

function paint() {
    draw_background();
    draw_grid();
    draw_curve();
    draw_nodes();
    draw_value_row();
    draw_drag_readout();
    draw_loop_glyph();
}

// ---- interaction -----------------------------------------------------------
function onclick(x, y, but, cmd, shift, capslock, option, ctrl) {
    var hit = nearest_node(x, y);
    if (hit >= 0) {
        drag_target = hit;
        if (hit !== just_added) just_added = -1;
        drag_nx = xs[hit];
        drag_ny = ys[hit];
        mgraphics.redraw();
        return;
    }
    if (x < plot_left() - 2 || x > plot_right() + 2 ||
        y < plot_top() - 2 || y > plot_bottom() + 2) return;
    if (xs.length >= MAX_POINTS) return;
    var nx = snap_q(from_px_x(x));
    var ny = snap_q(from_px_y(y));
    drag_target = insert_point(nx, ny);
    just_added = drag_target;
    drag_nx = xs[drag_target];
    drag_ny = ys[drag_target];
    emit_points();
    mgraphics.redraw();
}

function apply_drag(x, y) {
    var i = drag_target;
    var nx, ny;
    ny = clamp01(snap_q(from_px_y(y)));
    if (i === 0) {
        nx = 0.0;                              // endpoint x locked
    } else if (i === xs.length - 1) {
        nx = 1.0;                              // endpoint x locked
    } else {
        nx = snap_q(from_px_x(x));             // snap first, then neighbor-clamp
        if (nx < xs[i - 1] + MIN_DX) nx = xs[i - 1] + MIN_DX;
        if (nx > xs[i + 1] - MIN_DX) nx = xs[i + 1] - MIN_DX;
    }
    xs[i] = nx;
    ys[i] = ny;
    drag_nx = nx;
    drag_ny = ny;
    emit_points();
    mgraphics.redraw();
}

function ondrag(x, y, but, cmd, shift, capslock, option, ctrl) {
    if (but === 0) { drag_target = -1; mgraphics.redraw(); return; }
    if (drag_target < 0) return;
    just_added = -1;               // a real move commits the point
    apply_drag(x, y);
}

function ondblclick(x, y, but, cmd, shift, capslock, option, ctrl) {
    var hit = nearest_node(x, y);
    if (hit < 0) return;
    if (hit === just_added) { just_added = -1; return; }   // fresh point: keep
    if (hit === 0 || hit === xs.length - 1) return;        // endpoints stay
    xs.splice(hit, 1);
    ys.splice(hit, 1);
    drag_target = -1;
    emit_points();
    mgraphics.redraw();
}

// ---- messages (set + redraw, NEVER re-emit; ignored mid-drag) --------------
function set_points() {
    if (drag_target >= 0) return;
    apply_pairs(arrayfromargs(arguments));
    mgraphics.redraw();
}

// wrapper-internal restore: count-first fixed-slot layout from the param pak
function set_all() {
    if (drag_target >= 0) return;
    var a = arrayfromargs(arguments);
    if (a.length < 1) return;
    var n = Math.round(a[0]);
    if (n < 2) n = 2;
    if (n > MAX_POINTS) n = MAX_POINTS;
    var avail = Math.floor((a.length - 1) / 2);
    if (n > avail) n = avail;
    if (n < 2) return;
    apply_pairs(a.slice(1, 1 + 2 * n));
    mgraphics.redraw();
}

function set_tension(v) {
    tension = v;
    if (tension < 0) tension = 0;
    if (tension > 100) tension = 100;
    mgraphics.redraw();
}

function set_grid(v) {
    grid_n = Math.round(v);
    if (grid_n < 1) grid_n = 1;
    if (grid_n > 64) grid_n = 64;
    mgraphics.redraw();
}

function set_snap(v) { snap_on = (v > 0) ? 1 : 0; mgraphics.redraw(); }
function set_loop(v) { loop_on = (v > 0) ? 1 : 0; mgraphics.redraw(); }

// stray bare numbers on the inlet are meaningless -- swallow them silently
// so nothing ever posts "no function" errors to the Max console.
function msg_float(v) {}
function msg_int(v) {}
""")
