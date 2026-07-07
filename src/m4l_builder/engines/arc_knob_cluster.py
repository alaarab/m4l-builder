"""Arc-knob cluster — a bespoke, interactive premium control grid (v8ui).

A compact grid of draggable ARC-KNOBS drawn with mgraphics: each knob is a
270° gauge (gap at the bottom) with a glowing accent value-arc, a white
indicator dot, an uppercase label above and the live value below. Vertical
drag changes the value; every knob emits ``outlet(0, "<key>", value)`` and
mirrors a ``set_<key> <v>`` message back for display sync — the Opti/Rotary
interactive-hero contract, generalized to N knobs in ONE v8ui.

The DEVICE wrapper (:meth:`m4l_builder.device.Device.add_arc_knob_cluster`)
backs each knob with a PARKED ``live.dial`` host (off-face, presentation=0)
so automation / MIDI-map / preset recall behave exactly like a native dial —
the v8ui is only the skin + the gesture source.

The arc is drawn as an explicit POLYLINE (sampled points), never
``mgraphics.arc`` — arc() over-sweeps its endpoint when the start angle is
greater than the end, which would smear the gauge.

Inlet (1) — ``set_<key> <v>`` per knob (display only, never re-emitted).
Outlet (1) — ``<key> <value>`` on every drag (the gesture stream).
"""

from string import Template

ARC_KNOB_CLUSTER_INLETS = 1
ARC_KNOB_CLUSTER_OUTLETS = 1


def arc_knob_cluster_js(
    knobs,
    *,
    accent="0.36, 0.87, 0.99",
    text="0.91, 0.94, 0.97",
    dim="0.47, 0.52, 0.60",
    cols=2,
    radius=14,
    drag_px=90,
):
    """Return ES5 JavaScript for an interactive arc-knob cluster (Max v8ui).

    ``knobs``: list of dicts with ``key`` (outlet selector + ``set_`` suffix),
    ``label`` (uppercase caption), ``min``, ``max``, optional ``init``
    (defaults to ``min``) and ``signed`` (show a leading ``+`` for positive
    values). Knobs are laid out row-major in ``cols`` columns. ``radius`` is
    the knob arc radius in px; ``drag_px`` is the pixels of vertical drag that
    spans the full value range.
    """
    if not knobs:
        raise ValueError("arc_knob_cluster_js needs at least one knob")
    keys = [k["key"] for k in knobs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"arc_knob_cluster_js keys must be unique, got {keys}")
    labels = [k["label"] for k in knobs]
    mins = [float(k["min"]) for k in knobs]
    maxs = [float(k["max"]) for k in knobs]
    inits = [float(k.get("init", k["min"])) for k in knobs]
    signed = [1 if k.get("signed") else 0 for k in knobs]
    for key, lo, hi in zip(keys, mins, maxs):
        if hi <= lo:
            raise ValueError(f"knob {key!r}: max must exceed min")
    setters = "\n".join(
        f"function set_{k}(v) {{ vals[{i}] = v; mgraphics.redraw(); }}"
        for i, k in enumerate(keys)
    )
    return _TEMPLATE.substitute(
        accent=accent,
        text=text,
        dim=dim,
        cols=int(cols),
        radius=float(radius),
        drag_px=float(drag_px),
        n=len(knobs),
        keys=", ".join(f'"{k}"' for k in keys),
        labels=", ".join(f'"{lb}"' for lb in labels),
        mins=", ".join(repr(v) for v in mins),
        maxs=", ".join(repr(v) for v in maxs),
        inits=", ".join(repr(v) for v in inits),
        signed=", ".join(str(s) for s in signed),
        setters=setters,
    )


_TEMPLATE = Template("""\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 1;

var ACC = [$accent];
var TXT = [$text], DIM = [$dim];
var KEYS = [$keys];
var LABELS = [$labels];
var MINS = [$mins];
var MAXS = [$maxs];
var SIGNED = [$signed];
var vals = [$inits];
var COLS = $cols, N = $n, KRAD = $radius, DRAG = $drag_px;
var A0 = 2.35619449, SW = 4.71238898;      // 3pi/4 start, 3pi/2 sweep, gap at bottom

function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
function kfmt(k) { var v = Math.round(vals[k]); return (SIGNED[k] && v > 0) ? "+" + v : "" + v; }
function knobC(k) {
    var w = mgraphics.size[0], hh = mgraphics.size[1];
    var rows = Math.ceil(N / COLS), col = k % COLS, row = Math.floor(k / COLS);
    return [w * (col + 0.5) / COLS, hh * (row + 0.5) / rows];
}
function arcpoly(cx, cy, rad, f) {
    var a1 = A0 + SW * f, steps = Math.max(2, Math.round(46 * f));
    mgraphics.move_to(cx + rad * Math.cos(A0), cy + rad * Math.sin(A0));
    for (var i = 1; i <= steps; i++) {
        var t = A0 + (a1 - A0) * i / steps;
        mgraphics.line_to(cx + rad * Math.cos(t), cy + rad * Math.sin(t));
    }
    mgraphics.stroke();
}
function knob(k) {
    var c = knobC(k), cx = c[0], cy = c[1];
    var f = (vals[k] - MINS[k]) / (MAXS[k] - MINS[k]); f = clamp(f, 0, 1);
    mgraphics.set_source_rgba(0.20, 0.23, 0.27, 1.0);        // track
    mgraphics.set_line_width(2.2); arcpoly(cx, cy, KRAD, 1.0);
    mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], 0.12);  // glow
    mgraphics.set_line_width(4.2); arcpoly(cx, cy, KRAD, f);
    mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], 0.22);
    mgraphics.set_line_width(2.8); arcpoly(cx, cy, KRAD, f);
    mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], 0.96);  // core
    mgraphics.set_line_width(1.8); arcpoly(cx, cy, KRAD, f);
    var ae = A0 + SW * f, ix = cx + KRAD * Math.cos(ae), iy = cy + KRAD * Math.sin(ae);
    mgraphics.set_source_rgba(1, 1, 1, 0.95);
    mgraphics.ellipse(ix - 1.8, iy - 1.8, 3.6, 3.6); mgraphics.fill();
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(6.5);
    mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 0.95);
    var lb = LABELS[k], lw = mgraphics.text_measure(lb)[0];
    mgraphics.move_to(cx - lw / 2, cy - KRAD - 5); mgraphics.show_text(lb);
    mgraphics.set_font_size(10.0);
    mgraphics.set_source_rgba(TXT[0], TXT[1], TXT[2], 1.0);
    var vf = kfmt(k), vw = mgraphics.text_measure(vf)[0];
    mgraphics.move_to(cx - vw / 2, cy + 3.5); mgraphics.show_text(vf);
}
function paint() { for (var k = 0; k < N; k++) knob(k); }
$setters
var drag_k = -1, down_y = 0, down_v = 0;
function inKnob(x, y, k) {
    var c = knobC(k), dx = x - c[0], dy = y - c[1];
    return (dx * dx + dy * dy) <= (KRAD + 8) * (KRAD + 8);
}
function onclick(x, y, but) {
    drag_k = -1;
    for (var k = 0; k < N; k++) if (inKnob(x, y, k)) { drag_k = k; down_y = y; down_v = vals[k]; return; }
}
function ondrag(x, y, but) {
    if (!but) { drag_k = -1; return; }
    if (drag_k < 0) return;
    var range = MAXS[drag_k] - MINS[drag_k];
    var nv = clamp(down_v + (down_y - y) / DRAG * range, MINS[drag_k], MAXS[drag_k]);
    vals[drag_k] = nv; outlet(0, KEYS[drag_k], nv); mgraphics.redraw();
}
function bang() { mgraphics.redraw(); }
""")
