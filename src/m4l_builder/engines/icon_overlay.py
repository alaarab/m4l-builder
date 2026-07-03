"""Static icon overlay — a crisp vector glyph floating over a real control.

The premium answer to tiny text chips ("FULL", "EXPAND"): keep the live.text
as the param + click surface (its enum labels and automation names stay
untouched), render its text in invisible ink (textcolor == bgcolor), size it
down to a small square, and float one of these on top with ``ignoreclick=1``
so clicks fall straight through. The live.text's bg/bgoncolor still shows
through as the on/off state; this overlay contributes only the glyph.

Glyphs come from the shared :mod:`ui_icons` bank (``draw_glyph`` by name —
"expand", "collapse", "power", ...). ES5-safe, display-only, no inlets used.
"""

from string import Template

from .ui_icons import ICON_NAMES, ui_icons_js

ICON_OVERLAY_INLETS = 1
ICON_OVERLAY_OUTLETS = 0

__all__ = ["ICON_OVERLAY_INLETS", "ICON_OVERLAY_OUTLETS", "icon_overlay_js"]

_TEMPLATE = Template(r"""
// icon_overlay: one static "$glyph" glyph, transparent bg, mouse-transparent
// (the box below owns the click + state color).
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var GLYPH_CLR = [$color];

$icons_bank

function paint() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    mgraphics.set_source_rgba(GLYPH_CLR);
    draw_glyph("$glyph", w * 0.5, h * 0.5, Math.min(w, h) * $scale);
}

// Static glyph — the only repaint trigger is an explicit bang.
function bang() { mgraphics.redraw(); }
""")


def icon_overlay_js(glyph: str, *, color=(0.82, 0.84, 0.88, 0.95),
                    scale: float = 0.34) -> str:
    """Return standalone v8ui JS painting one centred ``glyph`` from the bank.

    ``scale`` is the glyph half-size as a fraction of the box's short edge
    (the bank draws in a ``2*s`` box). Pair with ``ignoreclick=1`` and a
    transparent box bg.
    """
    if glyph not in ICON_NAMES:
        raise ValueError(f"unknown glyph {glyph!r}; pick one of {ICON_NAMES}")
    return _TEMPLATE.substitute(
        glyph=glyph,
        color=", ".join(f"{c:.3f}" for c in color),
        icons_bank=ui_icons_js(),
        scale=f"{scale:.3f}",
    )
