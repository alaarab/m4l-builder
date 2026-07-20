"""settings_bar — a randomizer's LEFT sidebar opener (classic jsui).

A thin vertical bar that lives on the device's left edge and holds the
collapsible-settings DROPDOWN affordance: a drawn accent triangle at the top
(points DOWN ▾ when closed, UP ▴ when open — a real glyph, so it always renders,
unlike a font ``▾``) above a rotated "SETTINGS" label. Clicking the bar toggles;
the automatable enum param lives in a parked ``live.text`` the bar drives + reads
(inlet 0 = current open state for display, outlet 0 = toggled state on click),
so automation / recall / MCP still work.

Deconstructed from the randomizer's obj-74 (circular dropdown) + obj-76 (rotated
"Settings" label) in its 19px left panel.
"""

from __future__ import annotations

SETTINGS_BAR_INLETS = 1
SETTINGS_BAR_OUTLETS = 1

__all__ = [
    "SETTINGS_BAR_INLETS",
    "SETTINGS_BAR_OUTLETS",
    "settings_bar_js",
]

_TEMPLATE = r"""// settings_bar: left-edge dropdown opener + rotated label (randomizer idiom)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 1;

var ACC = [%(acc)s];
var LABEL = "%(label)s";
var isopen = 0;

function paint() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    // the drawn dropdown triangle near the top (always renders — no font glyph);
    // it points RIGHT in BOTH states (the column's visibility is the open/closed
    // cue), matching a compact dropdown glyph — open just brightens it
    var cx = w * 0.5;
    var ay = w * 0.5 + 3;
    var s = Math.max(3, w * 0.30);
    mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], isopen ? 1.0 : 0.85);
    mgraphics.move_to(cx - s * 0.55, ay - s * 0.8);
    mgraphics.line_to(cx - s * 0.55, ay + s * 0.8);
    mgraphics.line_to(cx + s * 0.75, ay);
    mgraphics.close_path();
    mgraphics.fill();
    // the rotated SETTINGS label (reads bottom -> top)
    mgraphics.set_source_rgba(0.62, 0.64, 0.67, 0.85);
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(8);
    mgraphics.save();
    mgraphics.translate(w * 0.5 + 3, h - 6);
    mgraphics.rotate(-1.5707963);
    mgraphics.move_to(0, 0);
    mgraphics.show_text(LABEL);
    mgraphics.restore();
}

// inlet 0: current open state (parked-param echo) -> sync the arrow
function msg_int(v) { isopen = v ? 1 : 0; mgraphics.redraw(); }
function msg_float(v) { msg_int(Math.round(v)); }
function list() { msg_int(Math.round(arguments[0])); }
function bang() { mgraphics.redraw(); }

// click anywhere on the bar toggles -> out to the parked param (which fires
// the reflow + setwidth and echoes back here to set the arrow direction).
// NB: this box is a CLASSIC jsui — its mouse event is onclick(x, y, ...);
// v8ui pointer events NEVER fire here (shipped that way once: every
// sidebar opener was silently dead to the mouse while param-driven QA passed).
function onclick(x, y) {
    isopen = isopen ? 0 : 1;
    outlet(0, isopen);
    mgraphics.redraw();
}
"""


def settings_bar_js(*, accent=(0.72, 0.38, 0.95, 1.0),
                    label: str = "SETTINGS") -> str:
    """Return classic-jsui JS for the left-edge settings-dropdown bar.

    Pair with a parked ``live.text`` enum param (``[Closed, Open]``): param
    outlet -> bar inlet 0 (arrow display sync), bar outlet 0 -> param inlet
    (click toggles the automatable param, which drives the reflow).
    """
    acc = ", ".join(f"{c:g}" for c in accent[:3])
    return _TEMPLATE % {"acc": acc, "label": label}
