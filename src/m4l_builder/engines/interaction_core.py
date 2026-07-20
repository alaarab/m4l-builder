"""interaction_core — shared verbatim JS boilerplate for interactive display engines.

A prior audit found ~45-55 LOC of literally byte-identical JS hand-copied into
every interactive jsui/v8ui display engine: the pointer-coordinate resolver
trio, ``clamp``, ``onresize``, and the ``plot_l/r/t/b`` + ``plot_w/h``
geometry accessors. This module holds the CANONICAL copies so a change lands
once, following the same byte-identity discipline as :mod:`design_system` and
:mod:`graph_core`.

Two independent naming conventions exist in the wild for the pointer
resolvers and for ``clamp`` — NOT just cosmetic parameter renames, the bodies
differ too (``pointer_buttons``' button-code branch is a ternary in one family
and an if/return in the other). Forcing a single parameterized template would
require reformatting hand-authored engine text — a byte-for-byte change to a
device's shipped JS. So each family gets its own literal constant; pick the
one that matches the engine you're touching (grep its existing
``function pointer_x(...)`` signature to tell them apart).

Usage mirrors :mod:`graph_core`'s marker technique (safer than threading a
raw JS blob through ``string.Template.substitute`` — a stray ``$`` in a
future edit would otherwise get mis-parsed as a template placeholder): plant
a marker comment in the engine's ``_JS_TEMPLATE`` at the exact position of
the old hand-authored block, then after ``.substitute(...)`` chain
``.replace("//__MARKER__//", THE_CONSTANT)``. Every constant here holds
EXACTLY the original function text with no leading/trailing newline, so a
marker placed where the old text lived reproduces the old surrounding
blank-line pattern untouched.

Plot geometry (``plot_l/r/t/b`` + ``plot_w/h``) is exposed as functions, not
constants, since the margin values differ per engine (though several engines
share literally the same numbers by coincidence) — the SURROUNDING structure
(which lines exist, their exact spacing/order, the width/height body style)
is what repeats. Two families found in the wild: short names
(``plot_l/r/t/b``) and long, column-aligned names (``plot_left/right/top/
bottom``); within each, ``plot_w``/``plot_h`` come in a plain form and a
zero-guarded form (``d > 1 ? d : 1``). Verify byte-for-byte against the real
engine before trusting a new call site — the margin EXPRESSION (not just a
bare number) sometimes carries other arithmetic (e.g. a meter-bar width
subtracted out), which is fine as long as it's passed through verbatim.
"""

__all__ = [
    "POINTER_X_JS",
    "POINTER_Y_JS",
    "POINTER_BUTTONS_JS",
    "POINTER_X_LONGNAME_JS",
    "POINTER_Y_LONGNAME_JS",
    "POINTER_BUTTONS_LONGNAME_JS",
    "CLAMP_TERNARY_JS",
    "CLAMP_IFORM_JS",
    "ONRESIZE_JS",
    "plot_geometry_short_js",
    "plot_geometry_long_js",
]


# ── Pointer-coordinate resolvers: "(pe, fb)" family ─────────────────────────
# v8ui pointer events expose the object-local position under different
# property names across Max/runtime versions (.x/.localX/.offsetX/.clientX);
# reading only one returns undefined in some hosts. Verbatim from
# ballistics_curve.py / delay_trail.py (byte-identical across 7 adopters).
POINTER_X_JS = """\
function pointer_x(pe, fb) {
    if (!pe) return fb;
    if (pe.x !== undefined) return pe.x;
    if (pe.localX !== undefined) return pe.localX;
    if (pe.offsetX !== undefined) return pe.offsetX;
    if (pe.clientX !== undefined) return pe.clientX;
    return fb;
}"""

POINTER_Y_JS = """\
function pointer_y(pe, fb) {
    if (!pe) return fb;
    if (pe.y !== undefined) return pe.y;
    if (pe.localY !== undefined) return pe.localY;
    if (pe.offsetY !== undefined) return pe.offsetY;
    if (pe.clientY !== undefined) return pe.clientY;
    return fb;
}"""

POINTER_BUTTONS_JS = """\
function pointer_buttons(pe, fb) {
    if (!pe) return fb;
    if (pe.buttons !== undefined) return pe.buttons;
    if (pe.button !== undefined) return pe.button === 2 ? 2 : 1;
    return fb;
}"""


# ── Pointer-coordinate resolvers: "(pointerevent, fallback)" family ────────
# Same resolution logic, spelled-out parameter names, and an if/return
# (not ternary) button-code branch. Verbatim from eq_curve.py (byte-identical
# with linear_phase_eq_display.py).
POINTER_X_LONGNAME_JS = """\
function pointer_x(pointerevent, fallback) {
    if (!pointerevent) return fallback;
    if (pointerevent.x !== undefined) return pointerevent.x;
    if (pointerevent.localX !== undefined) return pointerevent.localX;
    if (pointerevent.offsetX !== undefined) return pointerevent.offsetX;
    if (pointerevent.clientX !== undefined) return pointerevent.clientX;
    return fallback;
}"""

POINTER_Y_LONGNAME_JS = """\
function pointer_y(pointerevent, fallback) {
    if (!pointerevent) return fallback;
    if (pointerevent.y !== undefined) return pointerevent.y;
    if (pointerevent.localY !== undefined) return pointerevent.localY;
    if (pointerevent.offsetY !== undefined) return pointerevent.offsetY;
    if (pointerevent.clientY !== undefined) return pointerevent.clientY;
    return fallback;
}"""

POINTER_BUTTONS_LONGNAME_JS = """\
function pointer_buttons(pointerevent, fallback) {
    if (!pointerevent) return fallback;
    if (pointerevent.buttons !== undefined) return pointerevent.buttons;
    if (pointerevent.button !== undefined) {
        if (pointerevent.button === 2) return 2;
        return 1;
    }
    return fallback;
}"""


# ── clamp: two byte-identical families ──────────────────────────────────────
# Ternary one-liner. Verbatim from ballistics_curve.py (byte-identical across
# 10 adopters: arc_knob_cluster, ballistics_curve, delay_trail, exciter_curve,
# level_history, level_meter, loop_filter_curve, transfer_curve,
# transient_history, waveshape_curve).
CLAMP_TERNARY_JS = """\
function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }"""

# If-form. Verbatim from band_chip_row.py (byte-identical across 5 adopters:
# band_chip_row, eq_band_column, eq_curve, linear_phase_eq_display,
# performance_canvas).
CLAMP_IFORM_JS = """\
function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}"""


# ── onresize: byte-identical 1-liner ────────────────────────────────────────
# Verbatim from ballistics_curve.py (byte-identical across 9 adopters:
# ballistics_curve, delay_trail, exciter_curve, level_history, level_meter,
# loop_filter_curve, transfer_curve, transient_history, waveshape_curve).
ONRESIZE_JS = """\
function onresize(w, h) { mgraphics.redraw(); }"""


def plot_geometry_short_js(l_expr, r_expr, t_expr, b_expr, *, guarded=False):
    """Format the ``plot_l/r/t/b`` + ``plot_w/h`` block (short-name family).

    ``l_expr``/``r_expr``/``t_expr``/``b_expr`` are the literal JS
    return-expressions for each margin (e.g. ``"5"``, ``"MARGIN_L"``,
    ``"mgraphics.size[0] - 5"``, ``"MARGIN + 8"``) — pass exactly what the
    original engine returned. ``guarded=True`` selects the zero-guarded
    ``plot_w``/``plot_h`` body (``var d = ...; return d > 1 ? d : 1;``) used
    by ballistics_curve.py / loop_filter_curve.py; the plain form
    (``return plot_r() - plot_l();``) matches delay_trail.py,
    exciter_curve.py, level_history.py, transfer_curve.py,
    transient_history.py, waveshape_curve.py.
    """
    if guarded:
        w = "function plot_w() { var d = plot_r() - plot_l(); return d > 1 ? d : 1; }"
        h = "function plot_h() { var d = plot_b() - plot_t(); return d > 1 ? d : 1; }"
    else:
        w = "function plot_w() { return plot_r() - plot_l(); }"
        h = "function plot_h() { return plot_b() - plot_t(); }"
    return "\n".join([
        "function plot_l() { return " + l_expr + "; }",
        "function plot_r() { return " + r_expr + "; }",
        "function plot_t() { return " + t_expr + "; }",
        "function plot_b() { return " + b_expr + "; }",
        w,
        h,
    ])


def plot_geometry_long_js(l_expr, r_expr, t_expr, b_expr):
    """Format the ``plot_left/right/top/bottom`` + ``plot_w/h`` block.

    Long, column-aligned name family (verbatim spacing from eq_curve.py,
    byte-identical across crossover_display.py, curve_editor.py,
    envelope_editor.py, eq_curve.py, step_bars.py). ``l_expr``/``r_expr``/
    ``t_expr``/``b_expr`` are the literal JS return-expressions, as in
    :func:`plot_geometry_short_js`. linear_phase_eq_display.py uses the same
    function/variable names but WITHOUT the column-alignment padding — not
    byte-compatible with this formatter, handled as its own case if ever
    adopted.
    """
    return "\n".join([
        "function plot_left()   { return " + l_expr + "; }",
        "function plot_right()  { return " + r_expr + "; }",
        "function plot_top()    { return " + t_expr + "; }",
        "function plot_bottom() { return " + b_expr + "; }",
        "function plot_w()      { return plot_right() - plot_left(); }",
        "function plot_h()      { return plot_bottom() - plot_top(); }",
    ])
