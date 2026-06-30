"""Premium v8ui UI kit — depth/material primitives + custom-drawn controls.

The fidelity toolkit: hand-drawn v8ui controls (knobs etc.) and panels with real
depth (gradients, shadows, glows, rounded corners) — the things our flat
single-fill devices lacked. A custom knob is DRAWN here and bound to a HIDDEN
automatable ``live.dial`` (see ``Device.add_custom_knob``), so it looks bespoke
(FabFilter/Rupture-style) while staying a normal Live parameter.

All snippets satisfy the v8ui contract (mgraphics bootstrap + paint + redraw) and
embed ``design_system_js()`` for the shared glow/shadow helpers.
"""

from .design_system import design_system_js

# ── shared drawing snippet: a premium rounded panel with depth ─────────────
_PANEL_SNIPPET = """
// ds_panel: rounded panel with a top-lit vertical gradient + border + drop shadow.
function ds_panel(x, y, w, h, lo, hi, border, radius, shadow) {
    if (shadow) {
        mgraphics.set_source_rgba(0, 0, 0, 0.45);
        mgraphics.rectangle_rounded(x, y + 2, w, h, radius, radius);
        mgraphics.fill();
    }
    var g = mgraphics.pattern_create_linear(x, y, x, y + h);
    g.add_color_stop_rgba(0.0, hi[0], hi[1], hi[2], hi[3]);
    g.add_color_stop_rgba(1.0, lo[0], lo[1], lo[2], lo[3]);
    mgraphics.set_source(g);
    mgraphics.rectangle_rounded(x, y, w, h, radius, radius);
    mgraphics.fill();
    if (border) {
        mgraphics.set_source_rgba(border[0], border[1], border[2], border[3]);
        mgraphics.set_line_width(1.0);
        mgraphics.rectangle_rounded(x + 0.5, y + 0.5, w - 1, h - 1, radius, radius);
        mgraphics.stroke();
    }
}
"""


def panel_bg_js(
    *,
    lo="0.055, 0.058, 0.067, 1.0",
    hi="0.085, 0.090, 0.102, 1.0",
    border="0.20, 0.22, 0.26, 0.9",
    radius=8.0,
    inset=4.0,
) -> str:
    """A full-device v8ui background: one premium rounded, top-lit panel w/ depth."""
    return (
        design_system_js() + "\n" + _PANEL_SNIPPET + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 0;\n"
        f"var LO = [{lo}];\n"
        f"var HI = [{hi}];\n"
        f"var BORDER = [{border}];\n"
        f"var RADIUS = {float(radius)};\n"
        f"var INSET = {float(inset)};\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    ds_panel(INSET, INSET, w - 2 * INSET, h - 2 * INSET, LO, HI, BORDER, RADIUS, 1);\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn knob (v8ui) bound to a hidden live.dial ────────────────────
CUSTOM_KNOB_INLETS = 1
CUSTOM_KNOB_OUTLETS = 1


def custom_knob_js(
    *,
    label="KNOB",
    accent="0.30, 0.80, 0.84",
    vmin=0.0,
    vmax=100.0,
    initial=0.0,
    unit="",
    decimals=1,
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    bg_top=None,
    bg_bot=None,
    bipolar=False,
) -> str:
    """A premium hand-drawn knob: arc track + glowing value arc + indicator + body.

    Inlet 0 receives ``set_value <v>`` (from the bound hidden ``live.dial``) to
    redraw; vertical pointer drag emits the new value on outlet 0 (Shift = fine).
    The knob WORKS in actual param units (``vmin``..``vmax``).

    ``bg_top``/``bg_bot`` (``"r, g, b"`` strings) make the knob paint its OWN
    vertical-gradient background filling the whole object rect — a SLICE of the
    device panel gradient at this knob's position, so it blends seamlessly (no
    opaque object box where the drawing leaves the rect empty). ``bipolar`` makes
    the value arc originate at 12-o'clock and sweep toward the value (pan-style),
    instead of filling up from the minimum (unipolar, default).
    """
    has_bg = bg_top is not None and bg_bot is not None
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var VMIN = {float(vmin)};\n"
        f"var VMAX = {float(vmax)};\n"
        f'var UNIT = "{unit}";\n'
        f"var DECIMALS = {int(decimals)};\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var BIPOLAR = {1 if bipolar else 0};\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var TRACK = [0.20, 0.21, 0.25, 1.0];\n"
        "var BODY_HI = [0.22, 0.235, 0.265, 1.0];\n"
        "var BODY_LO = [0.085, 0.09, 0.105, 1.0];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var value = {float(initial)};\n"
        "var dragging = false, drag_y0 = 0, drag_v0 = 0;\n"
        "function clampv(v) { return v < VMIN ? VMIN : (v > VMAX ? VMAX : v); }\n"
        "function norm() { return (VMAX - VMIN) === 0 ? 0 : (value - VMIN) / (VMAX - VMIN); }\n"
        "function set_value(v) { value = clampv(v); mgraphics.redraw(); }\n"
        "function msg_float(v) { set_value(v); }\n"
        "function onclick(x, y, but, cmd, shift) { dragging = true; drag_y0 = y; drag_v0 = value; }\n"
        # v8ui drag = onpointermove (the but===0 guard ignores hover); jsui's ondrag is
        # NEVER called on a v8ui box — using it left these custom controls click-only (no drag).
        "function onpointermove(x, y, but, cmd, shift) {\n"
        "    if (but === 0) { dragging = false; return; }\n"
        "    var span = VMAX - VMIN;\n"
        "    var sens = shift ? 0.22 : 1.0;\n"
        "    value = clampv(drag_v0 + (drag_y0 - y) / 130.0 * span * sens);\n"
        "    outlet(0, value);\n"
        "    mgraphics.redraw();\n"
        "}\n"
        "function ondblclick(x, y) { value = clampv(" + f"{float(initial)}" + "); outlet(0, value); mgraphics.redraw(); }\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp);\n"
        "        mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var cx = w * 0.5;\n"
        "    var cy = h * 0.5 + 1;\n"
        "    var R = Math.min(w * 0.42, (h - 22) * 0.5);\n"
        "    var lw_px = Math.max(2.0, R * 0.16);\n"
        "    var a0 = Math.PI * 0.75, a1 = Math.PI * 2.25;\n"
        "    var av = a0 + (a1 - a0) * norm();\n"
        "    var aFrom = BIPOLAR ? (Math.PI * 1.5) : a0;\n"
        "    var aLo = Math.min(aFrom, av), aHi = Math.max(aFrom, av);\n"
        "    ds_drop_shadow(cx, cy, R + 2, 2, [0.0, 0.0, 0.0], 0.5);\n"
        "    var g = mgraphics.pattern_create_radial(cx, cy - R * 0.45, 0.0, cx, cy, R);\n"
        "    g.add_color_stop_rgba(0.0, BODY_HI[0], BODY_HI[1], BODY_HI[2], 1.0);\n"
        "    g.add_color_stop_rgba(1.0, BODY_LO[0], BODY_LO[1], BODY_LO[2], 1.0);\n"
        "    mgraphics.set_source(g);\n"
        "    mgraphics.arc(cx, cy, R, 0, Math.PI * 2); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(0, 0, 0, 0.55); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.arc(cx, cy, R, 0, Math.PI * 2); mgraphics.stroke();\n"
        "    var tr = R + 3;\n"
        "    mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0); mgraphics.set_line_width(lw_px);\n"
        "    mgraphics.arc(cx, cy, tr, a0, a1); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.22); mgraphics.set_line_width(lw_px + 3);\n"
        "    mgraphics.arc(cx, cy, tr, aLo, aHi); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0); mgraphics.set_line_width(lw_px);\n"
        "    mgraphics.arc(cx, cy, tr, aLo, aHi); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(0.96, 0.97, 0.99, 1.0); mgraphics.set_line_width(Math.max(1.5, R * 0.11));\n"
        "    mgraphics.move_to(cx + Math.cos(av) * R * 0.32, cy + Math.sin(av) * R * 0.32);\n"
        "    mgraphics.line_to(cx + Math.cos(av) * R * 0.82, cy + Math.sin(av) * R * 0.82);\n"
        "    mgraphics.stroke();\n"
        "    mgraphics.select_font_face(FONT);\n"
        "    mgraphics.set_font_size(6.5);\n"
        "    mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "    var lw = mgraphics.text_measure(LABEL);\n"
        "    mgraphics.move_to(cx - lw[0] * 0.5, 8); mgraphics.show_text(LABEL);\n"
        "    mgraphics.set_font_size(7.5);\n"
        "    mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 1.0);\n"
        "    var vs = value.toFixed(DECIMALS) + UNIT;\n"
        "    var vw = mgraphics.text_measure(vs);\n"
        "    mgraphics.move_to(cx - vw[0] * 0.5, h - 2); mgraphics.show_text(vs);\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn TOGGLE (v8ui) bound to a hidden live.toggle ─────────────────
def custom_toggle_js(
    *,
    label="",
    accent="0.30, 0.80, 0.84",
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    bg_top=None,
    bg_bot=None,
    initial=0,
) -> str:
    """A compact, minimal toggle: a small LED dot + label on ONE row. The dot
    lights the accent (with a soft glow) and the label brightens when ON — no
    chunky pill. Whole rect is the click target.

    Inlet 0 receives ``set_value <0|1>`` (from the bound hidden ``live.toggle``)
    to redraw; a click flips the state and emits the new ``0|1`` on outlet 0.
    """
    has_bg = bg_top is not None and bg_bot is not None
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var state = {1 if initial else 0};\n"
        "function set_value(v) { state = v ? 1 : 0; mgraphics.redraw(); }\n"
        "function msg_int(v) { set_value(v); }\n"
        "function msg_float(v) { set_value(v); }\n"
        "function onclick(x, y, but, cmd, shift) { state = state ? 0 : 1; outlet(0, state); mgraphics.redraw(); }\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var cy = h * 0.5;\n"
        "    var r = Math.min(3.4, h * 0.30);\n"
        "    var dx = r + 3;\n"
        "    if (state) {\n"
        "        ds_node_glow(dx, cy, [ACCENT[0], ACCENT[1], ACCENT[2]], r * 2.6, 0.5);\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "        mgraphics.arc(dx, cy, r, 0, Math.PI * 2); mgraphics.fill();\n"
        "    } else {\n"
        "        mgraphics.set_source_rgba(0.0, 0.0, 0.0, 0.35);\n"
        "        mgraphics.arc(dx, cy, r, 0, Math.PI * 2); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 0.7); mgraphics.set_line_width(1.0);\n"
        "        mgraphics.arc(dx, cy, r, 0, Math.PI * 2); mgraphics.stroke();\n"
        "    }\n"
        "    if (LABEL.length > 0) {\n"
        "        mgraphics.select_font_face(FONT);\n"
        "        mgraphics.set_font_size(7.0);\n"
        "        var c = state ? TEXT : DIM;\n"
        "        mgraphics.set_source_rgba(c[0], c[1], c[2], 1.0);\n"
        "        var tm = mgraphics.text_measure(LABEL);\n"
        "        mgraphics.move_to(dx + r + 4, cy + tm[1] * 0.34); mgraphics.show_text(LABEL);\n"
        "    }\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn CYCLE / "select" button (v8ui) bound to a hidden live.tab ──
def custom_cycle_js(
    *,
    options=None,
    glyphs=None,
    label="",
    accent="0.30, 0.80, 0.84",
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    bg_top=None,
    bg_bot=None,
    initial=0,
) -> str:
    """A single COMPACT select button that steps through options on click (the
    space-saving alternative to a full glyph/segment row). Shows the current
    option (a glyph if ``glyphs`` given, else the ``options`` text) + a ▾ chevron.
    Click = next, Shift-click = previous (wraps). Bound to a hidden ``live.tab``:
    inlet 0 ``set_index <i>`` redraws; clicking emits the new index on outlet 0.
    """
    is_glyph = glyphs is not None
    items = list(glyphs) if is_glyph else list(options or [])
    items_js = "[" + ", ".join('"' + str(it) + '"' for it in items) + "]"
    icons = ""
    if is_glyph:
        from .ui_icons import ui_icons_js
        icons = ui_icons_js() + "\n"
    has_bg = bg_top is not None and bg_bot is not None
    return (
        design_system_js() + "\n" + icons +
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f"var ITEMS = {items_js};\n"
        "var N = ITEMS.length;\n"
        f"var IS_GLYPH = {1 if is_glyph else 0};\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var TRACK = [0.13, 0.14, 0.17, 1.0];\n"
        "var BORDER = [0.24, 0.26, 0.30, 1.0];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var sel = {int(initial)};\n"
        "function set_index(i) { sel = ((i | 0) % N + N) % N; mgraphics.redraw(); }\n"
        "function msg_int(i) { set_index(i); }\n"
        "function msg_float(i) { set_index(i); }\n"
        "function onclick(x, y, but, cmd, shift) {\n"
        "    var d = shift ? -1 : 1;\n"
        "    sel = (sel + d + N) % N; outlet(0, sel); mgraphics.redraw();\n"
        "}\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    mgraphics.select_font_face(FONT);\n"
        "    var top = 0;\n"
        "    if (LABEL.length > 0) {\n"
        "        mgraphics.set_font_size(6.5); mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        mgraphics.move_to(1, 8); mgraphics.show_text(LABEL); top = 11;\n"
        "    }\n"
        "    var by = top, bh = h - top;\n"
        "    var rad = 3.5;\n"
        "    mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0);\n"
        "    mgraphics.rectangle_rounded(0.5, by + 0.5, w - 1, bh - 1, rad, rad); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 0.9); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(0.5, by + 0.5, w - 1, bh - 1, rad, rad); mgraphics.stroke();\n"
        "    var cyb = by + bh * 0.5;\n"
        "    if (IS_GLYPH) {\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "        draw_glyph(ITEMS[sel], bh * 0.5 + 2, cyb, Math.min(bh, 14) * 0.30);\n"
        "    } else {\n"
        "        mgraphics.set_font_size(7.5); mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "        var tm = mgraphics.text_measure(ITEMS[sel]);\n"
        "        mgraphics.move_to(5, cyb + tm[1] * 0.34); mgraphics.show_text(ITEMS[sel]);\n"
        "    }\n"
        "    var ax = w - 6;\n"
        "    mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 0.95); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.move_to(ax - 3, cyb - 1.5); mgraphics.line_to(ax, cyb + 2.0);\n"
        "    mgraphics.line_to(ax + 3, cyb - 1.5); mgraphics.stroke();\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn GLYPH selector (v8ui) bound to a hidden live.tab ────────────
def custom_glyph_selector_js(
    *,
    glyphs,
    accent="0.30, 0.80, 0.84",
    dim_color="0.46, 0.49, 0.55, 1.0",
    label="",
    bg_top=None,
    bg_bot=None,
    initial=0,
) -> str:
    """A compact row of small hand-drawn GLYPH buttons (Rupture's mode-glyphs).

    ``glyphs`` is a list of icon names (see ``ui_icons.ICON_NAMES``). The selected
    button gets a soft accent backing + accent glyph; the rest are dim. Inlet 0
    receives ``set_index <i>`` (from the hidden ``live.tab``) to redraw; clicking
    a button emits its index on outlet 0.
    """
    from .ui_icons import ui_icons_js

    has_bg = bg_top is not None and bg_bot is not None
    glyphs_js = "[" + ", ".join('"' + str(g) + '"' for g in glyphs) + "]"
    return (
        design_system_js() + "\n" + ui_icons_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f"var GLYPHS = {glyphs_js};\n"
        "var N = GLYPHS.length;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var DIM = [{dim_color}];\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var sel = {int(initial)};\n"
        "function set_index(i) { sel = i | 0; mgraphics.redraw(); }\n"
        "function msg_int(i) { set_index(i); }\n"
        "function msg_float(i) { set_index(i); }\n"
        "function onclick(x, y, but, cmd, shift) {\n"
        "    var top = LABEL.length > 0 ? 11 : 0;\n"
        "    if (y < top) { return; }\n"
        "    var i = Math.floor((x) / (mgraphics.size[0] / N));\n"
        "    if (i < 0) i = 0; if (i > N - 1) i = N - 1;\n"
        "    sel = i; outlet(0, i); mgraphics.redraw();\n"
        "}\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var top = 0;\n"
        "    if (LABEL.length > 0) {\n"
        "        mgraphics.select_font_face(FONT); mgraphics.set_font_size(6.5);\n"
        "        mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        mgraphics.move_to(1, 8); mgraphics.show_text(LABEL); top = 11;\n"
        "    }\n"
        "    var bw = w / N, bh = h - top;\n"
        "    var s = Math.min(bw, bh) * 0.30;\n"
        "    for (var i = 0; i < N; i++) {\n"
        "        var cx = bw * i + bw * 0.5;\n"
        "        var cy = top + bh * 0.5;\n"
        "        if (i === sel) {\n"
        "            mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.16);\n"
        "            mgraphics.rectangle_rounded(bw * i + 2, top + 2, bw - 4, bh - 4, 4, 4); mgraphics.fill();\n"
        "            mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "        } else {\n"
        "            mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 0.95);\n"
        "        }\n"
        "        draw_glyph(GLYPHS[i], cx, cy, s);\n"
        "    }\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn SEGMENTED selector (v8ui) bound to a hidden live.tab ────────
def custom_segment_js(
    *,
    options,
    accent="0.30, 0.80, 0.84",
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    label="",
    bg_top=None,
    bg_bot=None,
    initial=0,
) -> str:
    """A premium horizontal segmented control (tabs / mode picker).

    Draws one labelled segment per option; the selected one is accent-filled.
    Inlet 0 receives ``set_index <i>`` (from the bound hidden ``live.tab``) to
    redraw; clicking a segment emits its index on outlet 0.
    """
    has_bg = bg_top is not None and bg_bot is not None
    opts_js = "[" + ", ".join('"' + str(o) + '"' for o in options) + "]"
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f"var OPTS = {opts_js};\n"
        "var N = OPTS.length;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var TRACK = [0.13, 0.14, 0.17, 1.0];\n"
        "var BORDER = [0.24, 0.26, 0.30, 1.0];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var sel = {int(initial)};\n"
        "function set_index(i) { sel = i | 0; mgraphics.redraw(); }\n"
        "function msg_int(i) { set_index(i); }\n"
        "function msg_float(i) { set_index(i); }\n"
        "function onclick(x, y, but, cmd, shift) {\n"
        "    var top = LABEL.length > 0 ? 12 : 2;\n"
        "    if (y < top) { return; }\n"
        "    var i = Math.floor((x - 2) / ((mgraphics.size[0] - 4) / N));\n"
        "    if (i < 0) i = 0; if (i > N - 1) i = N - 1;\n"
        "    sel = i; outlet(0, i); mgraphics.redraw();\n"
        "}\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    mgraphics.select_font_face(FONT);\n"
        "    var top = 2;\n"
        "    if (LABEL.length > 0) {\n"
        "        mgraphics.set_font_size(6.5);\n"
        "        mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        var lw = mgraphics.text_measure(LABEL);\n"
        "        mgraphics.move_to(2, 8); mgraphics.show_text(LABEL);\n"
        "        top = 12;\n"
        "    }\n"
        "    var x0 = 2, y0 = top, bw = w - 4, bh = h - top - 2;\n"
        "    var rad = 4.0;\n"
        "    mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0);\n"
        "    mgraphics.rectangle_rounded(x0, y0, bw, bh, rad, rad); mgraphics.fill();\n"
        "    var segw = bw / N;\n"
        "    for (var i = 0; i < N; i++) {\n"
        "        var sx = x0 + i * segw;\n"
        "        if (i === sel) {\n"
        "            mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.88);\n"
        "            mgraphics.rectangle_rounded(sx + 1, y0 + 1, segw - 2, bh - 2, rad - 1, rad - 1); mgraphics.fill();\n"
        "        }\n"
        "        if (i > 0) {\n"
        "            mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 0.7); mgraphics.set_line_width(1.0);\n"
        "            mgraphics.move_to(sx, y0 + 2); mgraphics.line_to(sx, y0 + bh - 2); mgraphics.stroke();\n"
        "        }\n"
        "        mgraphics.set_font_size(7.0);\n"
        "        var tc = (i === sel) ? [0.06, 0.07, 0.09] : [DIM[0], DIM[1], DIM[2]];\n"
        "        mgraphics.set_source_rgba(tc[0], tc[1], tc[2], 1.0);\n"
        "        var tw2 = mgraphics.text_measure(OPTS[i]);\n"
        "        mgraphics.move_to(sx + segw * 0.5 - tw2[0] * 0.5, y0 + bh * 0.5 + tw2[1] * 0.35);\n"
        "        mgraphics.show_text(OPTS[i]);\n"
        "    }\n"
        "    mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 0.9); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(x0 + 0.5, y0 + 0.5, bw - 1, bh - 1, rad, rad); mgraphics.stroke();\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn SLIDER / fader (v8ui) bound to a hidden live.dial ───────────
def custom_slider_js(
    *,
    label="FADER",
    accent="0.30, 0.80, 0.84",
    vmin=0.0,
    vmax=100.0,
    initial=0.0,
    unit="",
    decimals=1,
    orientation=0,
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    bg_top=None,
    bg_bot=None,
    bipolar=False,
) -> str:
    """A premium hand-drawn fader (FabFilter-style): recessed track + accent fill
    + a wide handle cap + label/value readout. Vertical (``orientation=0``, the
    handle slides up = max) or horizontal (``orientation=1``, right = max).

    Inlet 0 receives ``set_value <v>`` (from the bound hidden ``live.dial``) to
    redraw; the pointer drives the value with ABSOLUTE positioning — the handle
    JUMPS to the click and tracks the cursor along the axis (FabFilter behavior),
    unlike the knob's relative drag delta. Shift = fine (blends 25% toward the
    target for sub-pixel precision); double-click = reset to ``initial``. The
    fader WORKS in actual param units (``vmin``..``vmax``).

    ``bg_top``/``bg_bot`` (``"r, g, b"`` strings) make the fader paint its OWN
    vertical-gradient background filling the whole object rect — a SLICE of the
    device panel gradient at this control's position, so it blends seamlessly (no
    opaque object box where the drawing leaves the rect empty). ``bipolar`` makes
    the accent fill grow from the value=0 detent pixel toward the handle (pan/gain
    style) with a faint center tick, instead of filling up from the minimum
    (unipolar, default).

    The four track edges are computed ONCE in ``geom()`` and reused by ``paint()``
    AND ``set_from_pointer()`` so click-mapping and drawing never disagree (the
    same shared-geometry discipline ``eq_curve`` uses for ``plot_left/right``).
    """
    has_bg = bg_top is not None and bg_bot is not None
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var VMIN = {float(vmin)};\n"
        f"var VMAX = {float(vmax)};\n"
        f'var UNIT = "{unit}";\n'
        f"var DECIMALS = {int(decimals)};\n"
        f"var ORIENT = {1 if orientation else 0};\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var BIPOLAR = {1 if bipolar else 0};\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var TRACK = [0.13, 0.14, 0.17, 1.0];\n"
        "var BORDER = [0.05, 0.055, 0.065, 1.0];\n"
        "var BODY_HI = [0.27, 0.285, 0.315, 1.0];\n"
        "var BODY_LO = [0.13, 0.14, 0.16, 1.0];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var INITIAL = {float(initial)};\n"
        f"var value = {float(initial)};\n"
        "var dragging = false;\n"
        "function clampv(v) { return v < VMIN ? VMIN : (v > VMAX ? VMAX : v); }\n"
        "function norm(v) { return (VMAX - VMIN) === 0 ? 0 : (v - VMIN) / (VMAX - VMIN); }\n"
        "function set_value(v) { value = clampv(v); mgraphics.redraw(); }\n"
        "function msg_float(v) { set_value(v); }\n"
        "function msg_int(v) { set_value(v); }\n"
        # geom() -> [lo, hi, c0, c1, hth]: lo = the MIN pixel end, hi = the MAX pixel
        # end (vertical -> max at TOP/small y; horizontal -> max at RIGHT/large x),
        # c0/c1 = the two cross-axis track edges, hth = handle thickness.
        "function geom() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    var hth = 9;\n"
        "    if (ORIENT) {\n"
        "        var pad = hth * 0.5 + 2;\n"
        "        var lo = pad;\n"
        "        var hi = w - pad;\n"
        "        var c0 = 11;\n"
        "        var c1 = h - 12;\n"
        "        return [lo, hi, c0, c1, hth];\n"
        "    } else {\n"
        "        var padv = hth * 0.5 + 2;\n"
        "        var lov = h - 11 - padv;\n"
        "        var hiv = 11 + padv;\n"
        "        var cl = w * 0.5 - 5;\n"
        "        var cr = w * 0.5 + 5;\n"
        "        return [lov, hiv, cl, cr, hth];\n"
        "    }\n"
        "}\n"
        # ABSOLUTE pointer -> value (xy_pad.update_position pattern). Vertical INVERTS
        # y so dragging UP raises the value (max at the top). Clamp 0..1; Shift blends
        # toward the target for fine control.
        "function set_from_pointer(x, y, shift) {\n"
        "    var gm = geom();\n"
        "    var f;\n"
        "    if (ORIENT) { f = (x - gm[0]) / (gm[1] - gm[0]); }\n"
        "    else { f = (gm[0] - y) / (gm[0] - gm[1]); }\n"
        "    if (f < 0) f = 0; if (f > 1) f = 1;\n"
        "    var target = VMIN + f * (VMAX - VMIN);\n"
        "    if (shift) { value = clampv(value + (target - value) * 0.25); }\n"
        "    else { value = clampv(target); }\n"
        "    outlet(0, value);\n"
        "    mgraphics.redraw();\n"
        "}\n"
        "function onclick(x, y, but, cmd, shift) { dragging = true; set_from_pointer(x, y, shift); }\n"
        # v8ui drag = onpointermove (the but===0 guard ignores hover); jsui's ondrag is
        # NEVER called on a v8ui box — using it left these custom controls click-only (no drag).
        "function onpointermove(x, y, but, cmd, shift) {\n"
        "    if (but === 0) { dragging = false; return; }\n"
        "    set_from_pointer(x, y, shift);\n"
        "}\n"
        "function ondblclick(x, y) { value = clampv(INITIAL); outlet(0, value); mgraphics.redraw(); }\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var gm = geom();\n"
        "    var lo = gm[0], hi = gm[1], c0 = gm[2], c1 = gm[3], hth = gm[4];\n"
        "    var n = norm(value);\n"
        "    var nd = BIPOLAR ? norm(0) : 0;\n"
        "    var tw = c1 - c0;\n"
        "    var rad = 2.5;\n"
        # track groove: recessed rounded rect spanning the full travel + 1px inner border.
        "    if (ORIENT) {\n"
        "        mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0);\n"
        "        mgraphics.rectangle_rounded(lo, c0, hi - lo, tw, rad, rad); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 1.0); mgraphics.set_line_width(1.0);\n"
        "        mgraphics.rectangle_rounded(lo + 0.5, c0 + 0.5, hi - lo - 1, tw - 1, rad, rad); mgraphics.stroke();\n"
        "    } else {\n"
        "        mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0);\n"
        "        mgraphics.rectangle_rounded(c0, hi, tw, lo - hi, rad, rad); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 1.0); mgraphics.set_line_width(1.0);\n"
        "        mgraphics.rectangle_rounded(c0 + 0.5, hi + 0.5, tw - 1, lo - hi - 1, rad, rad); mgraphics.stroke();\n"
        "    }\n"
        # handle pixel (hp) + detent pixel (dp = value=0 for bipolar, MIN end unipolar).
        "    var hp = lo + (hi - lo) * n;\n"
        "    var dp = lo + (hi - lo) * nd;\n"
        # accent fill from detent -> handle, two-pass (soft glow underlay + solid).
        "    var fa = Math.min(hp, dp), fb = Math.max(hp, dp);\n"
        "    if (ORIENT) {\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.22);\n"
        "        mgraphics.rectangle_rounded(fa, c0 - 1, fb - fa, tw + 2, rad, rad); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "        mgraphics.rectangle_rounded(fa, c0, fb - fa, tw, rad, rad); mgraphics.fill();\n"
        "        if (BIPOLAR) {\n"
        "            mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 0.7); mgraphics.set_line_width(1.0);\n"
        "            mgraphics.move_to(dp, c0 - 1); mgraphics.line_to(dp, c0 + tw + 1); mgraphics.stroke();\n"
        "        }\n"
        "    } else {\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.22);\n"
        "        mgraphics.rectangle_rounded(c0 - 1, fa, tw + 2, fb - fa, rad, rad); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "        mgraphics.rectangle_rounded(c0, fa, tw, fb - fa, rad, rad); mgraphics.fill();\n"
        "        if (BIPOLAR) {\n"
        "            mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 0.7); mgraphics.set_line_width(1.0);\n"
        "            mgraphics.move_to(c0 - 1, dp); mgraphics.line_to(c0 + tw + 1, dp); mgraphics.stroke();\n"
        "        }\n"
        "    }\n"
        # handle cap: wide flat thumb spanning track + a few px, body gradient,
        # drop shadow, dark outline, and a bright accent indicator line across center.
        "    var hcx, hcy, hw, hh;\n"
        "    if (ORIENT) { hcx = hp; hcy = (c0 + c1) * 0.5; hw = hth; hh = tw + 8; }\n"
        "    else { hcx = (c0 + c1) * 0.5; hcy = hp; hw = tw + 8; hh = hth; }\n"
        "    ds_drop_shadow(hcx, hcy, hth + 3, 2, [0.0, 0.0, 0.0], 0.5);\n"
        "    var hg = mgraphics.pattern_create_linear(hcx - hw * 0.5, hcy - hh * 0.5, hcx - hw * 0.5, hcy + hh * 0.5);\n"
        "    hg.add_color_stop_rgba(0.0, BODY_HI[0], BODY_HI[1], BODY_HI[2], 1.0);\n"
        "    hg.add_color_stop_rgba(1.0, BODY_LO[0], BODY_LO[1], BODY_LO[2], 1.0);\n"
        "    mgraphics.set_source(hg);\n"
        "    mgraphics.rectangle_rounded(hcx - hw * 0.5, hcy - hh * 0.5, hw, hh, 2.5, 2.5); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(0.0, 0.0, 0.0, 0.6); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(hcx - hw * 0.5 + 0.5, hcy - hh * 0.5 + 0.5, hw - 1, hh - 1, 2.5, 2.5); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0); mgraphics.set_line_width(1.5);\n"
        "    if (ORIENT) { mgraphics.move_to(hcx, hcy - hh * 0.5 + 2); mgraphics.line_to(hcx, hcy + hh * 0.5 - 2); }\n"
        "    else { mgraphics.move_to(hcx - hw * 0.5 + 2, hcy); mgraphics.line_to(hcx + hw * 0.5 - 2, hcy); }\n"
        "    mgraphics.stroke();\n"
        # text: label + value, centered per orientation (knob-style readout).
        "    mgraphics.select_font_face(FONT);\n"
        "    mgraphics.set_font_size(6.5);\n"
        "    var lw = mgraphics.text_measure(LABEL);\n"
        "    var vs = value.toFixed(DECIMALS) + UNIT;\n"
        "    mgraphics.set_font_size(7.5);\n"
        "    var vw = mgraphics.text_measure(vs);\n"
        "    if (ORIENT) {\n"
        "        mgraphics.set_font_size(6.5); mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        mgraphics.move_to(2, 8); mgraphics.show_text(LABEL);\n"
        "        mgraphics.set_font_size(7.5); mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 1.0);\n"
        "        mgraphics.move_to(w - vw[0] - 2, 8); mgraphics.show_text(vs);\n"
        "    } else {\n"
        "        mgraphics.set_font_size(6.5); mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        mgraphics.move_to(w * 0.5 - lw[0] * 0.5, 8); mgraphics.show_text(LABEL);\n"
        "        mgraphics.set_font_size(7.5); mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 1.0);\n"
        "        mgraphics.move_to(w * 0.5 - vw[0] * 0.5, h - 2); mgraphics.show_text(vs);\n"
        "    }\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn STEPPER (+/-) (v8ui) bound to a hidden live.dial ────────────
CUSTOM_STEPPER_INLETS = 1
CUSTOM_STEPPER_OUTLETS = 1


def custom_stepper_js(
    *,
    label="",
    accent="0.30, 0.80, 0.84",
    vmin=0.0,
    vmax=100.0,
    initial=0.0,
    step=1.0,
    fine_step=None,
    unit="",
    decimals=0,
    scrub=True,
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    bg_top=None,
    bg_bot=None,
) -> str:
    """A compact +/- numeric stepper bound to a hidden ``live.dial`` (the right
    control for discrete/integer params — octave, voices, semitones — and for
    fine numeric entry where a knob is imprecise).

    Draws a rounded pill: a ``-`` minus button (left) and ``+`` plus button
    (right) flanking the formatted value. Clicking a button steps the value by
    ``step`` (Shift = ``fine_step``); dragging the value field vertically scrubs
    (when ``scrub``); double-click resets to ``initial``. The value lives in real
    param units (``vmin``..``vmax``), quantized to ``step`` and shown with
    ``decimals``. At the extremes the corresponding button dims (value>=vmax →
    ``+`` at 0.35 alpha). Inlet 0 receives ``set_value <v>`` (from the bound
    hidden ``live.dial``) to redraw; pointer mutations emit the new value (display
    units) on outlet 0.

    ``fine_step`` defaults to ``step`` for integer params (``decimals<=0``) and
    ``step/10`` for floats. ``bg_top``/``bg_bot`` (``"r, g, b"`` strings) make the
    stepper paint its OWN vertical-gradient background filling the whole object
    rect — a SLICE of the device panel gradient at this control's position, so it
    blends seamlessly (no opaque object box). Emits the same mgraphics bootstrap +
    ``design_system_js()`` prefix as :func:`custom_knob_js`. Keep rects ≥48px wide
    so two buttons + a readable number fit.
    """
    if fine_step is None:
        fine_step = step if int(decimals) <= 0 else step / 10.0
    has_bg = bg_top is not None and bg_bot is not None
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var VMIN = {float(vmin)};\n"
        f"var VMAX = {float(vmax)};\n"
        f"var STEP = {float(step)};\n"
        f"var FINE = {float(fine_step)};\n"
        f'var UNIT = "{unit}";\n'
        f"var DECIMALS = {int(decimals)};\n"
        f"var SCRUB = {1 if scrub else 0};\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var TRACK = [0.13, 0.14, 0.17, 1.0];\n"
        "var BORDER = [0.24, 0.26, 0.30, 1.0];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var value = {float(initial)};\n"
        "var dragging = false, drag_y0 = 0, drag_v0 = 0, hot = 0;\n"
        "function clampv(v) { return v < VMIN ? VMIN : (v > VMAX ? VMAX : v); }\n"
        "function quantize(v) {\n"
        "    if (STEP <= 0) return v;\n"
        "    var n = Math.round((v - VMIN) / STEP);\n"
        "    return VMIN + n * STEP;\n"
        "}\n"
        "function stepfor(shift) { return shift ? FINE : STEP; }\n"
        "function set_value(v) { value = clampv(v); mgraphics.redraw(); }\n"
        "function msg_float(v) { set_value(v); }\n"
        "function msg_int(v) { set_value(v); }\n"
        "function labtop() { return LABEL.length > 0 ? 11 : 0; }\n"
        "function btnw() {\n"
        "    var bh = mgraphics.size[1] - labtop();\n"
        "    return Math.min(bh, 18);\n"
        "}\n"
        "function onclick(x, y, but, cmd, shift) {\n"
        "    var top = labtop();\n"
        "    if (y < top) { return; }\n"
        "    var w = mgraphics.size[0];\n"
        "    var bw = btnw();\n"
        "    if (x <= bw) {\n"
        "        value = clampv(quantize(value - stepfor(shift)));\n"
        "        hot = -1; outlet(0, value); mgraphics.redraw(); return;\n"
        "    }\n"
        "    if (x >= w - bw) {\n"
        "        value = clampv(quantize(value + stepfor(shift)));\n"
        "        hot = 1; outlet(0, value); mgraphics.redraw(); return;\n"
        "    }\n"
        "    if (SCRUB) {\n"
        "        dragging = true; drag_y0 = y; drag_v0 = value;\n"
        "        ds_set_cursor(7);\n"
        "    }\n"
        "}\n"
        # v8ui drag = onpointermove (the but===0 guard ignores hover); jsui's ondrag is
        # NEVER called on a v8ui box — using it left these custom controls click-only (no drag).
        "function onpointermove(x, y, but, cmd, shift) {\n"
        "    if (but === 0) { dragging = false; hot = 0; ds_set_cursor(1); mgraphics.redraw(); return; }\n"
        "    if (!dragging) { return; }\n"
        "    var s = shift ? FINE : STEP;\n"
        "    value = clampv(quantize(drag_v0 + (drag_y0 - y) / 10.0 * s));\n"
        "    outlet(0, value); mgraphics.redraw();\n"
        "}\n"
        "function ondblclick(x, y) { value = clampv(quantize(" + f"{float(initial)}" + ")); outlet(0, value); mgraphics.redraw(); }\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    mgraphics.select_font_face(FONT);\n"
        "    var top = 0;\n"
        "    if (LABEL.length > 0) {\n"
        "        mgraphics.set_font_size(6.5); mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        mgraphics.move_to(1, 8); mgraphics.show_text(LABEL); top = 11;\n"
        "    }\n"
        "    var by = top, bh = h - top;\n"
        "    var rad = 3.5;\n"
        "    var bw = Math.min(bh, 18);\n"
        "    mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0);\n"
        "    mgraphics.rectangle_rounded(0.5, by + 0.5, w - 1, bh - 1, rad, rad); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 0.9); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(0.5, by + 0.5, w - 1, bh - 1, rad, rad); mgraphics.stroke();\n"
        "    var cyb = by + bh * 0.5;\n"
        "    var atMin = value <= VMIN + 1e-9;\n"
        "    var atMax = value >= VMAX - 1e-9;\n"
        "    var glen = Math.min(bw * 0.34, 5.0);\n"
        "    var mcx = bw * 0.5;\n"
        "    var minClr = (hot === -1) ? ACCENT : DIM;\n"
        "    var minA = atMin ? 0.35 : 1.0;\n"
        "    mgraphics.set_source_rgba(minClr[0], minClr[1], minClr[2], minA); mgraphics.set_line_width(1.6);\n"
        "    mgraphics.move_to(mcx - glen, cyb); mgraphics.line_to(mcx + glen, cyb); mgraphics.stroke();\n"
        "    var pcx = w - bw * 0.5;\n"
        "    var plusClr = (hot === 1) ? ACCENT : DIM;\n"
        "    var plusA = atMax ? 0.35 : 1.0;\n"
        "    mgraphics.set_source_rgba(plusClr[0], plusClr[1], plusClr[2], plusA); mgraphics.set_line_width(1.6);\n"
        "    mgraphics.move_to(pcx - glen, cyb); mgraphics.line_to(pcx + glen, cyb); mgraphics.stroke();\n"
        "    mgraphics.move_to(pcx, cyb - glen); mgraphics.line_to(pcx, cyb + glen); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 0.6); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.move_to(bw, by + 3); mgraphics.line_to(bw, by + bh - 3); mgraphics.stroke();\n"
        "    mgraphics.move_to(w - bw, by + 3); mgraphics.line_to(w - bw, by + bh - 3); mgraphics.stroke();\n"
        "    mgraphics.set_font_size(9.0); mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 1.0);\n"
        "    var vs = value.toFixed(DECIMALS) + UNIT;\n"
        "    var vw = mgraphics.text_measure(vs);\n"
        "    var fcx = (bw + (w - bw)) * 0.5;\n"
        "    mgraphics.move_to(fcx - vw[0] * 0.5, cyb + vw[1] * 0.34); mgraphics.show_text(vs);\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )


# ── custom-drawn READOUT (v8ui) bound to a hidden live.dial ─────────────────
# A flat draggable numeric value field — the premium alternative to a visible
# live.numbox. Near-clone of custom_knob_js: SAME bootstrap, SAME self-painted
# bg-slice block, SAME pointer handlers + drag math (works in real param units),
# only paint() differs (flat readout cell instead of an arc/knob body).


def custom_readout_js(
    *,
    label="VALUE",
    accent="0.30, 0.80, 0.84",
    vmin=0.0,
    vmax=100.0,
    initial=0.0,
    unit="",
    decimals=1,
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    bg_top=None,
    bg_bot=None,
    bipolar=False,
    show_bar=True,
    align="right",
) -> str:
    """A premium flat draggable numeric readout: framed cell + small top-left
    LABEL + a big bright VALUE + an optional accent fill bar showing position.

    Inlet 0 receives ``set_value <v>`` (from the bound hidden ``live.dial``) to
    redraw; vertical pointer drag emits the new value on outlet 0 (Shift = fine,
    double-click = reset to ``initial``). The readout WORKS in actual param units
    (``vmin``..``vmax``) — the same drag math as :func:`custom_knob_js`.

    ``bg_top``/``bg_bot`` (``"r, g, b"`` strings) make the readout paint its OWN
    vertical-gradient background filling the whole object rect — a SLICE of the
    device panel gradient at this control's position, so it blends seamlessly (no
    opaque object box; a transparent v8ui does NOT composite in M4L). ``bipolar``
    draws the fill bar from center (12-o'clock origin, pan-style) instead of from
    the minimum. ``show_bar`` toggles the position rail; ``align`` (``"right"`` /
    ``"center"`` / ``"left"``) places the value text within the cell.
    """
    has_bg = bg_top is not None and bg_bot is not None
    align_code = {"left": 0, "center": 1, "right": 2}.get(align, 2)
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 1;\n"
        f'var LABEL = "{label}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var VMIN = {float(vmin)};\n"
        f"var VMAX = {float(vmax)};\n"
        f'var UNIT = "{unit}";\n'
        f"var DECIMALS = {int(decimals)};\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var BIPOLAR = {1 if bipolar else 0};\n"
        f"var SHOW_BAR = {1 if show_bar else 0};\n"
        f"var ALIGN = {align_code};\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var TRACK = [0.13, 0.14, 0.17, 1.0];\n"
        "var RAIL = [0.20, 0.21, 0.25, 1.0];\n"
        "var BORDER = [0.24, 0.26, 0.30, 1.0];\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var value = {float(initial)};\n"
        "var dragging = false, drag_y0 = 0, drag_v0 = 0;\n"
        "function clampv(v) { return v < VMIN ? VMIN : (v > VMAX ? VMAX : v); }\n"
        "function norm() { return (VMAX - VMIN) === 0 ? 0 : (value - VMIN) / (VMAX - VMIN); }\n"
        "function set_value(v) { value = clampv(v); mgraphics.redraw(); }\n"
        "function msg_float(v) { set_value(v); }\n"
        "function onclick(x, y, but, cmd, shift) { dragging = true; drag_y0 = y; drag_v0 = value; ds_set_cursor(DS_CUR_GRAB); }\n"
        # v8ui drag = onpointermove (the but===0 guard ignores hover); jsui's ondrag is
        # NEVER called on a v8ui box — using it left these custom controls click-only (no drag).
        "function onpointermove(x, y, but, cmd, shift) {\n"
        "    if (but === 0) { dragging = false; ds_set_cursor(DS_CUR_HAND); return; }\n"
        "    var span = VMAX - VMIN;\n"
        "    var sens = shift ? 0.22 : 1.0;\n"
        "    value = clampv(drag_v0 + (drag_y0 - y) / 130.0 * span * sens);\n"
        "    outlet(0, value);\n"
        "    mgraphics.redraw();\n"
        "}\n"
        "function ondblclick(x, y) { value = clampv(" + f"{float(initial)}" + "); outlet(0, value); mgraphics.redraw(); }\n"
        "function onidle(x, y) { if (!dragging) ds_set_cursor(DS_CUR_HAND); }\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp);\n"
        "        mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var pad = 4;\n"
        "    var rad = 3.5;\n"
        "    mgraphics.set_source_rgba(TRACK[0], TRACK[1], TRACK[2], 1.0);\n"
        "    mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], 0.9); mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad); mgraphics.stroke();\n"
        "    mgraphics.select_font_face(FONT);\n"
        # Compact SINGLE-ROW layout: label left (dim) + value right (text) on one
        # baseline, optional thin bar at the bottom. No stacking / no chevron, so it
        # stays legible and space-efficient down to ~h=13.\n"
        "    var midY = SHOW_BAR ? (h * 0.5 - 1.5) : (h * 0.5);\n"
        "    var lx = 5;\n"
        "    if (LABEL.length > 0) {\n"
        "        mgraphics.set_font_size(6.5);\n"
        "        mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        var lm = mgraphics.text_measure(LABEL);\n"
        "        mgraphics.move_to(5, midY + lm[1] * 0.34); mgraphics.show_text(LABEL);\n"
        "        lx = 5 + lm[0] + 4;\n"
        "    }\n"
        "    var fs = Math.min(10.0, h - 5);\n"
        "    mgraphics.set_font_size(fs);\n"
        "    mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 1.0);\n"
        "    var vs = value.toFixed(DECIMALS) + UNIT;\n"
        "    var vm = mgraphics.text_measure(vs);\n"
        "    var vx = w - vm[0] - 5;\n"
        "    if (ALIGN === 1) { vx = (w - vm[0]) * 0.5; }\n"
        "    if (vx < lx) vx = lx;\n"
        "    mgraphics.move_to(vx, midY + vm[1] * 0.34); mgraphics.show_text(vs);\n"
        "    if (SHOW_BAR) {\n"
        "        var bx0 = 4, bx1 = w - 4, bw = bx1 - bx0, barY = h - 2.5;\n"
        "        mgraphics.set_source_rgba(RAIL[0], RAIL[1], RAIL[2], 1.0); mgraphics.set_line_width(1.5);\n"
        "        mgraphics.move_to(bx0, barY); mgraphics.line_to(bx1, barY); mgraphics.stroke();\n"
        "        var nf = norm();\n"
        "        var xFrom = bx0 + bw * (BIPOLAR ? 0.5 : 0.0);\n"
        "        var xTo = bx0 + bw * nf;\n"
        "        var lo = Math.min(xFrom, xTo), hi = Math.max(xFrom, xTo);\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0); mgraphics.set_line_width(1.5);\n"
        "        mgraphics.move_to(lo, barY); mgraphics.line_to(hi, barY); mgraphics.stroke();\n"
        "    }\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )
