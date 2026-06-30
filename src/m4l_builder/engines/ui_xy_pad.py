"""Premium custom XY pad (v8ui) bound to TWO hidden live.dials (X + Y).

The ``add_custom_knob`` recipe DOUBLED: one v8ui (2 inlets / 2 outlets) DRAWS a
2D pad -- recessed plot well, grid, crosshair, glowing puck, value readouts --
and owns the pointer; TWO hidden automatable ``live.dial`` params (presentation=0)
hold the X and Y values. Drag the puck -> both params move and record automation;
automate either -> the puck redraws. Inlet 0 = X feedback, inlet 1 = Y feedback;
outlet 0 = X, outlet 1 = Y.

Satisfies the v8ui contract (mgraphics bootstrap + paint + redraw) and embeds
``design_system_js()`` for the glow/shadow helpers. Self-paints a vertical
gradient-SLICE background (``bg_top``/``bg_bot``) so it floats seamlessly over the
device panel -- transparent v8ui does NOT composite in M4L (same fix as the knob).
"""

from .design_system import design_system_js

CUSTOM_XY_PAD_INLETS = 2
CUSTOM_XY_PAD_OUTLETS = 2


def custom_xy_pad_js(
    *,
    label_x="X",
    label_y="Y",
    accent="0.30, 0.80, 0.84",
    accent2=None,
    vminx=0.0,
    vmaxx=1.0,
    initialx=0.5,
    vminy=0.0,
    vmaxy=1.0,
    initialy=0.5,
    unitx="",
    unity="",
    decimals=2,
    bipolar_x=False,
    bipolar_y=False,
    show_readout=True,
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    grid_color="0.20, 0.20, 0.22, 0.5",
    bg_top=None,
    bg_bot=None,
) -> str:
    """A premium hand-drawn 2D XY pad: recessed plot well + grid + crosshair +
    glowing puck + optional value readouts, working in REAL param units.

    Inlet 0 receives ``set_value <x>`` (from the bound hidden X ``live.dial``) and
    inlet 1 receives ``set_value <y>`` (Y dial) to redraw; dragging the puck emits
    the new X on outlet 0 and Y on outlet 1 (click = jump-to-cursor, Shift-drag =
    relative fine, double-click = reset both to initial). The pad WORKS in actual
    param units (``vminx``..``vmaxx`` / ``vminy``..``vmaxy``); Y is screen-INVERTED
    (top of pad = max Y).

    ``bg_top``/``bg_bot`` (``"r, g, b"`` strings) make the pad paint its OWN
    vertical-gradient background filling the whole object rect -- a SLICE of the
    device panel gradient at this pad's position -- so it blends seamlessly (no
    opaque object box). ``accent`` is the X-axis / puck accent; ``accent2`` tints
    the Y crosshair (defaults to ``accent``). ``bipolar_x``/``bipolar_y`` brighten
    a centered origin crosshair for pan-style bipolar axes.
    """
    has_bg = bg_top is not None and bg_bot is not None
    accent2 = accent if accent2 is None else accent2
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 2;\n"
        "outlets = 2;\n"
        f'var LABEL_X = "{label_x}";\n'
        f'var LABEL_Y = "{label_y}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var ACCENT2 = [{accent2}, 1.0];\n"
        f"var VMINX = {float(vminx)};\n"
        f"var VMAXX = {float(vmaxx)};\n"
        f"var VMINY = {float(vminy)};\n"
        f"var VMAXY = {float(vmaxy)};\n"
        f"var INITIALX = {float(initialx)};\n"
        f"var INITIALY = {float(initialy)};\n"
        f'var UNITX = "{unitx}";\n'
        f'var UNITY = "{unity}";\n'
        f"var DECIMALS = {int(decimals)};\n"
        f"var BIPOLAR_X = {1 if bipolar_x else 0};\n"
        f"var BIPOLAR_Y = {1 if bipolar_y else 0};\n"
        f"var SHOW_READOUT = {1 if show_readout else 0};\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var GRID = [{grid_color}];\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var WELL_HI = [0.085, 0.090, 0.105, 1.0];\n"
        "var WELL_LO = [0.045, 0.048, 0.057, 1.0];\n"
        "var WELL_BORDER = [0.22, 0.24, 0.28, 0.9];\n"
        "var PAD = 5.0;\n"
        "var RADIUS = 4.0;\n"
        "var GRID_DIVISIONS = 4;\n"
        "var FONT = 'Ableton Sans Medium';\n"
        f"var value_x = {float(initialx)};\n"
        f"var value_y = {float(initialy)};\n"
        "var dragging = false;\n"
        "var drag_x0 = 0, drag_y0 = 0, drag_vx0 = 0, drag_vy0 = 0;\n"
        "function clampx(v) { return v < VMINX ? VMINX : (v > VMAXX ? VMAXX : v); }\n"
        "function clampy(v) { return v < VMINY ? VMINY : (v > VMAXY ? VMAXY : v); }\n"
        "function normx() { return (VMAXX - VMINX) === 0 ? 0 : (value_x - VMINX) / (VMAXX - VMINX); }\n"
        "function normy() { return (VMAXY - VMINY) === 0 ? 0 : (value_y - VMINY) / (VMAXY - VMINY); }\n"
        "// 2-inlet dispatch: inlet 0 = X feedback, inlet 1 = Y feedback.\n"
        "function set_value(v) {\n"
        "    if (inlet === 1) { value_y = clampy(v); } else { value_x = clampx(v); }\n"
        "    mgraphics.redraw();\n"
        "}\n"
        "function msg_float(v) { set_value(v); }\n"
        "function msg_int(v) { set_value(v); }\n"
        "// Geometry helper: the inset plot rect [px, py, pw, ph].\n"
        "function plot_rect() {\n"
        "    var w = mgraphics.size[0], h = mgraphics.size[1];\n"
        "    return [PAD, PAD, Math.max(1, w - 2 * PAD), Math.max(1, h - 2 * PAD)];\n"
        "}\n"
        "// Pointer px -> param units, clamped to plot area, Y inverted (top = max).\n"
        "function update(mx, my) {\n"
        "    var r = plot_rect();\n"
        "    var nx = (mx - r[0]) / r[2];\n"
        "    var ny = (my - r[1]) / r[3];\n"
        "    nx = nx < 0 ? 0 : (nx > 1 ? 1 : nx);\n"
        "    ny = ny < 0 ? 0 : (ny > 1 ? 1 : ny);\n"
        "    value_x = VMINX + nx * (VMAXX - VMINX);\n"
        "    value_y = VMINY + (1 - ny) * (VMAXY - VMINY);\n"
        "    outlet(0, value_x);\n"
        "    outlet(1, value_y);\n"
        "    mgraphics.redraw();\n"
        "}\n"
        "function onclick(x, y, but, cmd, shift) {\n"
        "    dragging = true;\n"
        "    drag_x0 = x; drag_y0 = y; drag_vx0 = value_x; drag_vy0 = value_y;\n"
        "    update(x, y);\n"
        "}\n"
        # v8ui drag = onpointermove (fires on every move; the but===0 guard ignores
        # HOVER moves), NOT ondrag — jsui's ondrag is NEVER called on a v8ui box, which
        # left the puck click-to-jump only with no drag (the v8ui-ondrag pitfall).
        "function onpointermove(x, y, but, cmd, shift) {\n"
        "    if (but === 0) { dragging = false; return; }\n"
        "    if (shift) {\n"
        "        var r = plot_rect();\n"
        "        var dnx = (x - drag_x0) / r[2] * 0.22;\n"
        "        var dny = (y - drag_y0) / r[3] * 0.22;\n"
        "        value_x = clampx(drag_vx0 + dnx * (VMAXX - VMINX));\n"
        "        value_y = clampy(drag_vy0 - dny * (VMAXY - VMINY));\n"
        "        outlet(0, value_x);\n"
        "        outlet(1, value_y);\n"
        "        mgraphics.redraw();\n"
        "    } else {\n"
        "        update(x, y);\n"
        "    }\n"
        "}\n"
        "function onpointerup(x, y, but, cmd, shift) {\n"
        "    dragging = false;\n"
        "}\n"
        "function ondblclick(x, y) {\n"
        "    value_x = clampx(INITIALX); value_y = clampy(INITIALY);\n"
        "    outlet(0, value_x); outlet(1, value_y); mgraphics.redraw();\n"
        "}\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    // (1) Self-paint the panel-slice background FIRST (seamless float).\n"
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp);\n"
        "        mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var r = plot_rect();\n"
        "    var px = r[0], py = r[1], pw = r[2], ph = r[3];\n"
        "    // (2) Recessed plot well: dark gradient + border (sunken surface).\n"
        "    var wg = mgraphics.pattern_create_linear(px, py, px, py + ph);\n"
        "    wg.add_color_stop_rgba(0.0, WELL_LO[0], WELL_LO[1], WELL_LO[2], 1.0);\n"
        "    wg.add_color_stop_rgba(1.0, WELL_HI[0], WELL_HI[1], WELL_HI[2], 1.0);\n"
        "    mgraphics.set_source(wg);\n"
        "    mgraphics.rectangle_rounded(px, py, pw, ph, RADIUS, RADIUS); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(WELL_BORDER[0], WELL_BORDER[1], WELL_BORDER[2], WELL_BORDER[3]);\n"
        "    mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(px + 0.5, py + 0.5, pw - 1, ph - 1, RADIUS, RADIUS); mgraphics.stroke();\n"
        "    // (3) Grid lines inside the well.\n"
        "    mgraphics.set_source_rgba(GRID[0], GRID[1], GRID[2], GRID[3]);\n"
        "    mgraphics.set_line_width(0.5);\n"
        "    var gi;\n"
        "    for (gi = 1; gi < GRID_DIVISIONS; gi++) {\n"
        "        var gx = px + (gi / GRID_DIVISIONS) * pw;\n"
        "        mgraphics.move_to(gx, py); mgraphics.line_to(gx, py + ph); mgraphics.stroke();\n"
        "        var gy = py + (gi / GRID_DIVISIONS) * ph;\n"
        "        mgraphics.move_to(px, gy); mgraphics.line_to(px + pw, gy); mgraphics.stroke();\n"
        "    }\n"
        "    // (4) Bipolar center origin crosshair (brighter) for pan-style axes.\n"
        "    if (BIPOLAR_X) {\n"
        "        mgraphics.set_source_rgba(GRID[0], GRID[1], GRID[2], 0.9); mgraphics.set_line_width(0.75);\n"
        "        var ox = px + 0.5 * pw;\n"
        "        mgraphics.move_to(ox, py); mgraphics.line_to(ox, py + ph); mgraphics.stroke();\n"
        "    }\n"
        "    if (BIPOLAR_Y) {\n"
        "        mgraphics.set_source_rgba(GRID[0], GRID[1], GRID[2], 0.9); mgraphics.set_line_width(0.75);\n"
        "        var oy = py + 0.5 * ph;\n"
        "        mgraphics.move_to(px, oy); mgraphics.line_to(px + pw, oy); mgraphics.stroke();\n"
        "    }\n"
        "    // (5) Puck position: Y inverted so top = max Y.\n"
        "    var cx = px + normx() * pw;\n"
        "    var cy = py + (1 - normy()) * ph;\n"
        "    // Full-extent accent crosshairs through the puck (X-tint vert, Y-tint horiz).\n"
        "    mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.35); mgraphics.set_line_width(0.75);\n"
        "    mgraphics.move_to(cx, py); mgraphics.line_to(cx, py + ph); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(ACCENT2[0], ACCENT2[1], ACCENT2[2], 0.35); mgraphics.set_line_width(0.75);\n"
        "    mgraphics.move_to(px, cy); mgraphics.line_to(px + pw, cy); mgraphics.stroke();\n"
        "    // Soft glow halo + mid ring + bright puck core.\n"
        "    var pr = Math.max(3.0, Math.min(pw, ph) * 0.045);\n"
        "    ds_node_glow(cx, cy, [ACCENT[0], ACCENT[1], ACCENT[2]], pr * 2.6, 0.5);\n"
        "    mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.85); mgraphics.set_line_width(1.5);\n"
        "    mgraphics.arc(cx, cy, pr, 0, Math.PI * 2); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(0.96, 0.97, 0.99, 1.0);\n"
        "    mgraphics.arc(cx, cy, pr * 0.45, 0, Math.PI * 2); mgraphics.fill();\n"
        "    // (6) Optional value readouts (real units): X bottom-left, Y bottom-right.\n"
        "    if (SHOW_READOUT) {\n"
        "        mgraphics.select_font_face(FONT);\n"
        "        mgraphics.set_font_size(6.5);\n"
        "        mgraphics.set_source_rgba(DIM[0], DIM[1], DIM[2], 1.0);\n"
        "        var xs = LABEL_X + ' ' + value_x.toFixed(DECIMALS) + UNITX;\n"
        "        mgraphics.move_to(px + 3, py + ph - 3); mgraphics.show_text(xs);\n"
        "        var ys = LABEL_Y + ' ' + value_y.toFixed(DECIMALS) + UNITY;\n"
        "        var yw = mgraphics.text_measure(ys);\n"
        "        mgraphics.move_to(px + pw - yw[0] - 3, py + ph - 3); mgraphics.show_text(ys);\n"
        "    }\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )
