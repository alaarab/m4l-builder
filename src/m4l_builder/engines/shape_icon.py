"""shape_icon — a clickable per-lane waveform/source glyph (v8ui).

Replaces the text SOURCE dropdown in a modulation lane with a tiny icon that
DRAWS the current shape (a saw ramps, a square steps, S&H staircases, Lorenz
loops) and CYCLES to the next on click. The automatable enum param lives in a
parked live.menu the icon drives + reads, so automation/recall/MCP still work.

Deconstructed from dnksaus_Rnd_Gen: per-lane indicator at the row start, no
column header, self-documenting. Inlet 0 receives the current index (menu
echo); outlet 0 emits the next index on click (into the parked menu).
"""

from __future__ import annotations

# Every glyph the fleet's two modulators need, drawn inline at ~12px.
GLYPHS = (
    "sine", "tri", "saw", "square", "sh", "drift",
    "drunk", "logistic", "lorenz", "burst",
)

SHAPE_ICON_INLETS = 1
SHAPE_ICON_OUTLETS = 1

__all__ = ["GLYPHS", "SHAPE_ICON_INLETS", "SHAPE_ICON_OUTLETS", "shape_icon_js"]

_DRAW = r"""
function drawGlyph(name, cx, cy, s) {
    var i, n, t, x, y, v;
    if (name === "sine") {
        n = 16;
        mgraphics.move_to(cx - s, cy);
        for (i = 1; i <= n; i++) {
            t = i / n;
            mgraphics.line_to(cx - s + 2 * s * t, cy - Math.sin(t * 6.283) * s * 0.7);
        }
        mgraphics.stroke();
    } else if (name === "tri") {
        mgraphics.move_to(cx - s, cy + s * 0.6);
        mgraphics.line_to(cx - s * 0.5, cy - s * 0.6);
        mgraphics.line_to(cx + s * 0.5, cy + s * 0.6);
        mgraphics.line_to(cx + s, cy - s * 0.6);
        mgraphics.stroke();
    } else if (name === "saw") {
        mgraphics.move_to(cx - s, cy + s * 0.6);
        mgraphics.line_to(cx, cy - s * 0.6);
        mgraphics.line_to(cx, cy + s * 0.6);
        mgraphics.line_to(cx + s, cy - s * 0.6);
        mgraphics.stroke();
    } else if (name === "square") {
        mgraphics.move_to(cx - s, cy + s * 0.6);
        mgraphics.line_to(cx - s, cy - s * 0.6);
        mgraphics.line_to(cx, cy - s * 0.6);
        mgraphics.line_to(cx, cy + s * 0.6);
        mgraphics.line_to(cx + s, cy + s * 0.6);
        mgraphics.line_to(cx + s, cy - s * 0.6);
        mgraphics.stroke();
    } else if (name === "sh") {
        var ys = [0.5, 0.5, -0.2, -0.2, 0.6, 0.6, -0.5, -0.5];
        mgraphics.move_to(cx - s, cy - ys[0] * s);
        for (i = 1; i < ys.length; i++) {
            x = cx - s + 2 * s * (Math.floor(i / 2) / 3);
            mgraphics.line_to(x, cy - ys[i] * s);
        }
        mgraphics.stroke();
    } else if (name === "drift") {
        var dp = [0.1, 0.4, 0.2, 0.5, 0.3, 0.15];
        mgraphics.move_to(cx - s, cy - (dp[0] - 0.3) * 2 * s);
        for (i = 1; i < dp.length; i++) {
            mgraphics.line_to(cx - s + 2 * s * (i / (dp.length - 1)), cy - (dp[i] - 0.3) * 2 * s);
        }
        mgraphics.stroke();
    } else if (name === "drunk") {
        var jp = [0.2, -0.4, 0.5, -0.1, 0.6, -0.5, 0.3];
        mgraphics.move_to(cx - s, cy + jp[0] * s);
        for (i = 1; i < jp.length; i++) {
            mgraphics.line_to(cx - s + 2 * s * (i / (jp.length - 1)), cy + jp[i] * s);
        }
        mgraphics.stroke();
    } else if (name === "logistic") {
        // a doubling fork
        mgraphics.move_to(cx - s, cy);
        mgraphics.line_to(cx - s * 0.1, cy);
        mgraphics.stroke();
        mgraphics.move_to(cx - s * 0.1, cy);
        mgraphics.line_to(cx + s, cy - s * 0.6);
        mgraphics.stroke();
        mgraphics.move_to(cx - s * 0.1, cy);
        mgraphics.line_to(cx + s, cy + s * 0.6);
        mgraphics.stroke();
    } else if (name === "lorenz") {
        // a small figure-eight
        n = 22;
        mgraphics.move_to(cx, cy);
        for (i = 1; i <= n; i++) {
            t = i / n * 6.283;
            mgraphics.line_to(cx + s * 0.8 * Math.sin(t), cy - s * 0.55 * Math.sin(2 * t));
        }
        mgraphics.stroke();
    } else if (name === "burst") {
        mgraphics.move_to(cx - s, cy + s * 0.5);
        mgraphics.line_to(cx - s * 0.15, cy + s * 0.5);
        mgraphics.line_to(cx, cy - s * 0.6);
        mgraphics.line_to(cx + s * 0.15, cy + s * 0.5);
        mgraphics.line_to(cx + s, cy + s * 0.5);
        mgraphics.stroke();
    }
}
"""

_TEMPLATE = r"""// shape_icon: clickable per-lane waveform glyph (cycles the parked menu param)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 1;

var NAMES = [%(names)s];
var NCOUNT = %(ncount)d;
var ACC = [%(acc)s];
var idx = 0;

%(draw)s

function paint() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], 0.92);
    mgraphics.set_line_width(1.1);
    var s = Math.min(w, h) * 0.34;
    drawGlyph(NAMES[idx %% NCOUNT], w * 0.5, h * 0.5, s);
}

// inlet 0: the current shape index (menu echo) -> update the glyph
function msg_int(v) { idx = ((v %% NCOUNT) + NCOUNT) %% NCOUNT; mgraphics.redraw(); }
function msg_float(v) { msg_int(Math.round(v)); }
function list() { msg_int(Math.round(arguments[0])); }

// click cycles to the next shape -> out to the parked menu (which sets the param)
function onpointerdown() { idx = (idx + 1) %% NCOUNT; outlet(0, idx); mgraphics.redraw(); }
function bang() { mgraphics.redraw(); }
"""


def shape_icon_js(*, shapes, accent=(0.72, 0.38, 0.95, 1.0)) -> str:
    """Return v8ui JS for a clickable shape glyph over ``shapes`` (enum order).

    Each name in ``shapes`` must be one of :data:`GLYPHS`. Pair with a parked
    ``live.menu`` of the same enum: menu outlet -> icon inlet (display),
    icon outlet -> menu inlet (click-cycle sets the automatable param).
    """
    for name in shapes:
        if name not in GLYPHS:
            raise ValueError(f"unknown glyph {name!r}; pick from {GLYPHS}")
    return _TEMPLATE % {
        "names": ", ".join(f'"{s}"' for s in shapes),
        "ncount": len(shapes),
        "acc": ", ".join(f"{c:g}" for c in accent[:3]),
        "draw": _DRAW.strip(),
    }
