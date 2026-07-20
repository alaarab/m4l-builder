"""Premium draggable curve node (v8ui) — an EQ-band-style node on a graph.

A generalized two-axis node: horizontal pointer drag drives param X, vertical
drag drives param Y (an EQ band, compressor threshold/ratio dot, filter
freq/reso node, send/return XY). It is :func:`custom_knob_js` doubled onto two
axes — one v8ui DRAWS the graph + node and handles the pointer, and it is backed
by TWO hidden automatable ``live.dial`` params (see ``Device.add_drag_curve_node``).

The ONLY structural difference vs the single-param kit controls: the v8ui carries
2 outlets (outlet 0 = X value, outlet 1 = Y value) and two inbound setters
(``set_value_x`` / ``set_value_y``) so automation can redraw either axis
independently. Satisfies the v8ui contract and self-paints a gradient-slice
background (never relies on transparency).
"""

from .design_system import design_system_js

# ── custom-drawn draggable curve node (v8ui) bound to TWO hidden live.dials ──
DRAG_CURVE_NODE_INLETS = 1
DRAG_CURVE_NODE_OUTLETS = 2


def drag_curve_node_js(
    *,
    # X axis (horizontal)
    label_x="X",
    vmin_x=20.0,
    vmax_x=20000.0,
    initial_x=1000.0,
    unit_x="Hz",
    decimals_x=0,
    exponent_x=3.0,          # exponent_x > 1 => log axis (match the dial's exponent)
    # Y axis (vertical, inverted: top = max)
    label_y="Y",
    vmin_y=-15.0,
    vmax_y=15.0,
    initial_y=0.0,
    unit_y="dB",
    decimals_y=1,
    exponent_y=1.0,
    accent="0.30, 0.80, 0.84",
    text_color="0.80, 0.84, 0.90, 1.0",
    dim_color="0.46, 0.49, 0.55, 1.0",
    grid_color="0.20, 0.20, 0.22, 0.5",
    draw_curve=True,         # symmetric bell through the node vs bare crosshair
    margins=(20, 8, 6, 12),  # L, R, T, B px for axis labels / gutters
    bg_top=None,
    bg_bot=None,
) -> str:
    """A premium draggable curve node: graph frame + grid + (optional) bell curve
    through a glowing accent node. Horizontal drag drives X, vertical drives Y.

    Inlet 0 receives ``set_value_x <v>`` / ``set_value_y <v>`` (from the two bound
    hidden ``live.dial`` params) to redraw either axis; pointer drag emits the moved
    axis on outlet 0 (X) and/or outlet 1 (Y). Modifiers mirror the EQ curve: Shift =
    fine, Cmd = lock to horizontal, Opt = lock to vertical; double-click resets BOTH
    axes to their initial values. The node WORKS in actual param units
    (``vmin_x``..``vmax_x`` / ``vmin_y``..``vmax_y``).

    ``exponent_x``/``exponent_y`` > 1 make that axis logarithmic (pass the SAME
    exponent to the bound dial so the drawn node matches Live's readout). ``unit_x``
    /``unit_y`` + ``decimals_x``/``decimals_y`` format the gutter readouts.

    ``bg_top``/``bg_bot`` (``"r, g, b"`` strings) make the node paint its OWN
    vertical-gradient background filling the whole object rect — a SLICE of the
    device panel gradient at this control's position, so it blends seamlessly (no
    opaque object box where the drawing leaves the rect empty). ``draw_curve``
    draws a symmetric bell through the node (EQ-band look); ``False`` draws a bare
    crosshair (XY-pad look).
    """
    has_bg = bg_top is not None and bg_bot is not None
    ml, mr, mt, mb = margins
    return (
        design_system_js() + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 2;\n"
        f'var LABEL_X = "{label_x}";\n'
        f'var LABEL_Y = "{label_y}";\n'
        f"var ACCENT = [{accent}, 1.0];\n"
        f"var VMINX = {float(vmin_x)};\n"
        f"var VMAXX = {float(vmax_x)};\n"
        f"var VMINY = {float(vmin_y)};\n"
        f"var VMAXY = {float(vmax_y)};\n"
        f"var EXPX = {float(exponent_x)};\n"
        f"var EXPY = {float(exponent_y)};\n"
        f'var UNITX = "{unit_x}";\n'
        f'var UNITY = "{unit_y}";\n'
        f"var DECX = {int(decimals_x)};\n"
        f"var DECY = {int(decimals_y)};\n"
        f"var INITX = {float(initial_x)};\n"
        f"var INITY = {float(initial_y)};\n"
        f"var TEXT = [{text_color}];\n"
        f"var DIM = [{dim_color}];\n"
        f"var GRID = [{grid_color}];\n"
        f"var DRAW_CURVE = {1 if draw_curve else 0};\n"
        f"var ML = {float(ml)}, MR = {float(mr)}, MT = {float(mt)}, MB = {float(mb)};\n"
        f"var HASBG = {1 if has_bg else 0};\n"
        f"var BG_TOP = [{bg_top if has_bg else '0,0,0'}];\n"
        f"var BG_BOT = [{bg_bot if has_bg else '0,0,0'}];\n"
        "var FRAME = [0.20, 0.21, 0.25, 1.0];\n"
        "var NODE_RADIUS = 6.5, NODE_RADIUS_SEL = 8.5, HIT_RADIUS = 18.0;\n"
        "var FONT = 'Ableton Sans Medium';\n"
        "var vx = INITX, vy = INITY;\n"
        "var dragging = 0, lock_axis = 0;\n"  # 0 none, 1 horiz-only, 2 vert-only
        "var hover = 0, hover_x = 0, hover_y = 0;\n"
        # ── coordinate helpers (generalized eq_curve freq/gain maps) ──
        "function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }\n"
        "function clampx(v) { return clamp(v, VMINX, VMAXX); }\n"
        "function clampy(v) { return clamp(v, VMINY, VMAXY); }\n"
        "function plot_left()   { return ML; }\n"
        "function plot_right()  { return mgraphics.size[0] - MR; }\n"
        "function plot_top()    { return MT; }\n"
        "function plot_bottom() { return mgraphics.size[1] - MB; }\n"
        "function plot_w()      { return plot_right() - plot_left(); }\n"
        "function plot_h()      { return plot_bottom() - plot_top(); }\n"
        "function point_in_plot(x, y) {\n"
        "    return x >= plot_left() && x <= plot_right() && y >= plot_top() && y <= plot_bottom();\n"
        "}\n"
        # X axis: linear or log (EXPX>1). norm 0..1 -> pixel.
        "function val_to_x(v) {\n"
        "    v = clampx(v);\n"
        "    var norm;\n"
        "    if (EXPX > 1.0001 && VMINX > 0.0) {\n"
        "        norm = (Math.log(v) - Math.log(VMINX)) / (Math.log(VMAXX) - Math.log(VMINX));\n"
        "    } else {\n"
        "        norm = (v - VMINX) / (VMAXX - VMINX);\n"
        "    }\n"
        "    return plot_left() + norm * plot_w();\n"
        "}\n"
        "function x_to_val(x) {\n"
        "    var norm = clamp((x - plot_left()) / plot_w(), 0, 1);\n"
        "    if (EXPX > 1.0001 && VMINX > 0.0) {\n"
        "        return Math.exp(Math.log(VMINX) + norm * (Math.log(VMAXX) - Math.log(VMINX)));\n"
        "    }\n"
        "    return VMINX + norm * (VMAXX - VMINX);\n"
        "}\n"
        # Y axis INVERTED (top = max). Optional log on EXPY>1.
        "function val_to_y(v) {\n"
        "    v = clampy(v);\n"
        "    var norm;\n"
        "    if (EXPY > 1.0001 && VMINY > 0.0) {\n"
        "        norm = (Math.log(v) - Math.log(VMAXY)) / (Math.log(VMINY) - Math.log(VMAXY));\n"
        "    } else {\n"
        "        norm = (v - VMAXY) / (VMINY - VMAXY);\n"
        "    }\n"
        "    return plot_top() + norm * plot_h();\n"
        "}\n"
        "function y_to_val(y) {\n"
        "    var norm = clamp((y - plot_top()) / plot_h(), 0, 1);\n"
        "    if (EXPY > 1.0001 && VMINY > 0.0) {\n"
        "        return Math.exp(Math.log(VMAXY) + norm * (Math.log(VMINY) - Math.log(VMAXY)));\n"
        "    }\n"
        "    return VMAXY + norm * (VMINY - VMAXY);\n"
        "}\n"
        # ── hit test + drag dispatch (copied shape from eq_curve) ──
        "function hit_test(x, y) {\n"
        "    var nx = val_to_x(vx), ny = val_to_y(vy);\n"
        "    var dx = x - nx, dy = y - ny;\n"
        "    return (dx * dx + dy * dy) <= HIT_RADIUS * HIT_RADIUS;\n"
        "}\n"
        "function round_to(v, step) { return Math.round(v / step) * step; }\n"
        "function handle_press(x, y, but, cmd, shift, opt) {\n"
        "    if (but === 0) return;\n"
        "    lock_axis = cmd ? 1 : (opt ? 2 : 0);\n"
        "    if (hit_test(x, y)) {\n"
        "        dragging = 1;\n"
        "    } else if (point_in_plot(x, y)) {\n"
        # free placement: a press in the plot snaps the node to the cursor and grabs.
        "        dragging = 1;\n"
        "        apply_drag(x, y, shift, 1, 1);\n"
        "    } else {\n"
        "        dragging = 0;\n"
        "    }\n"
        "    if (dragging) ds_set_cursor(DS_CUR_GRAB);\n"
        "}\n"
        "function apply_drag(x, y, shift, do_x, do_y) {\n"
        "    var changed_x = 0, changed_y = 0;\n"
        "    if (do_x) {\n"
        "        var nvx = x_to_val(x);\n"
        "        if (shift) nvx = vx + (nvx - vx) * 0.15;\n"  # Shift = fine (blend 15%)
        "        nvx = clampx(round_to(nvx, 0.1));\n"
        "        if (nvx !== vx) { vx = nvx; changed_x = 1; }\n"
        "    }\n"
        "    if (do_y) {\n"
        "        var nvy = y_to_val(y);\n"
        "        if (shift) nvy = vy + (nvy - vy) * 0.15;\n"
        "        nvy = clampy(round_to(nvy, 0.1));\n"
        "        if (nvy !== vy) { vy = nvy; changed_y = 1; }\n"
        "    }\n"
        # emit ONLY the moved axis (value-equality short-circuit prevents feedback thrash)
        "    if (changed_x) outlet(0, vx);\n"
        "    if (changed_y) outlet(1, vy);\n"
        "    if (changed_x || changed_y) mgraphics.redraw();\n"
        "}\n"
        "function handle_drag_at(x, y, but, cmd, shift) {\n"
        "    if (!dragging) return;\n"
        "    if (but === 0) { dragging = 0; ds_set_cursor(DS_CUR_HAND); mgraphics.redraw(); return; }\n"
        "    var do_x = lock_axis === 2 ? 0 : 1;\n"  # Opt locks vertical -> no X move
        "    var do_y = lock_axis === 1 ? 0 : 1;\n"  # Cmd locks horizontal -> no Y move
        "    apply_drag(x, y, shift, do_x, do_y);\n"
        "}\n"
        # ── inbound setters (automation -> redraw, NO outlet => no feedback storm) ──
        "function set_value_x(v) { vx = clampx(v); mgraphics.redraw(); }\n"
        "function set_value_y(v) { vy = clampy(v); mgraphics.redraw(); }\n"
        # ── modern pointer path (Live device) ──
        "function onpointerdown(pe) {\n"
        "    handle_press(pointer_x(pe, 0), pointer_y(pe, 0), pointer_buttons(pe, 1),\n"
        "        pointer_command_key(pe, 0), pointer_shift_key(pe, 0), pointer_option_key(pe, 0));\n"
        "}\n"
        "function onpointermove(pe) {\n"
        "    var buttons = pointer_buttons(pe, 0);\n"
        "    var x = pointer_x(pe, 0), y = pointer_y(pe, 0);\n"
        "    if (dragging && ((buttons & 1) !== 0)) {\n"
        "        handle_drag_at(x, y, buttons, pointer_command_key(pe, 0), pointer_shift_key(pe, 0));\n"
        "        return;\n"
        "    }\n"
        "    if (dragging && buttons === 0) { dragging = 0; lock_axis = 0; }\n"
        "    handle_hover(x, y);\n"
        "}\n"
        "function onpointerup(pe) {\n"
        "    if (dragging) { dragging = 0; lock_axis = 0; mgraphics.redraw(); }\n"
        "    handle_hover(pointer_x(pe, 0), pointer_y(pe, 0));\n"
        "}\n"
        "function onpointerleave(pe) { hover = 0; ds_set_cursor(DS_CUR_ARROW); mgraphics.redraw(); }\n"
        "function handle_hover(x, y) {\n"
        "    hover = point_in_plot(x, y) ? 1 : 0;\n"
        "    hover_x = x; hover_y = y;\n"
        "    ds_set_cursor(dragging ? DS_CUR_GRAB : (hit_test(x, y) ? DS_CUR_HAND : (hover ? DS_CUR_CROSS : DS_CUR_ARROW)));\n"
        "    mgraphics.redraw();\n"
        "}\n"
        # ── legacy pointer path (Max edit view) ──
        "function onclick(x, y, but, cmd, shift, caps, opt, ctrl, pe) {\n"
        "    handle_press(x, y, but ? but : 1, cmd, shift, opt);\n"
        "}\n"
        "function ondrag(x, y, but, cmd, shift) { handle_drag_at(x, y, but, cmd, shift); }\n"
        "function onidle(x, y, but, cmd, shift) { handle_hover(x, y); }\n"
        "function onidleout(x, y) { hover = 0; ds_set_cursor(DS_CUR_ARROW); mgraphics.redraw(); }\n"
        "function ondblclick(x, y) {\n"
        "    vx = clampx(INITX); vy = clampy(INITY);\n"
        "    outlet(0, vx); outlet(1, vy);\n"  # premium-EQ reset: emit BOTH so both params record
        "    mgraphics.redraw();\n"
        "}\n"
        # ── pointerevent accessors (copied from eq_curve so it works in Live + Max) ──
        "function pointer_x(pe, f) { if (!pe) return f; if (pe.x !== undefined) return pe.x;"
        " if (pe.localX !== undefined) return pe.localX; if (pe.offsetX !== undefined) return pe.offsetX;"
        " if (pe.clientX !== undefined) return pe.clientX; return f; }\n"
        "function pointer_y(pe, f) { if (!pe) return f; if (pe.y !== undefined) return pe.y;"
        " if (pe.localY !== undefined) return pe.localY; if (pe.offsetY !== undefined) return pe.offsetY;"
        " if (pe.clientY !== undefined) return pe.clientY; return f; }\n"
        "function pointer_buttons(pe, f) { if (!pe) return f; if (pe.buttons !== undefined) return pe.buttons;"
        " if (pe.button !== undefined) { return pe.button === 2 ? 2 : 1; } return f; }\n"
        "function pointer_shift_key(pe, s) { return (pe && pe.shiftKey) ? 1 : (s ? 1 : 0); }\n"
        "function pointer_command_key(pe, c) { return (pe && pe.commandKey) ? 1 : (c ? 1 : 0); }\n"
        "function pointer_option_key(pe, o) { if (pe) { if (pe.altKey) return 1; if (pe.optionKey) return 1; } return o ? 1 : 0; }\n"
        # ── readout formatting ──
        "function fmt_x(v) { return v.toFixed(DECX) + (UNITX.length ? ' ' + UNITX : ''); }\n"
        "function fmt_y(v) { return (v >= 0 && VMINY < 0 ? '+' : '') + v.toFixed(DECY) + (UNITY.length ? ' ' + UNITY : ''); }\n"
        # ── paint ──
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        # self-painted gradient slice (REQUIRED: transparent v8ui doesn't composite in M4L)
        "    if (HASBG) {\n"
        "        var bgp = mgraphics.pattern_create_linear(0, 0, 0, h);\n"
        "        bgp.add_color_stop_rgba(0.0, BG_TOP[0], BG_TOP[1], BG_TOP[2], 1.0);\n"
        "        bgp.add_color_stop_rgba(1.0, BG_BOT[0], BG_BOT[1], BG_BOT[2], 1.0);\n"
        "        mgraphics.set_source(bgp); mgraphics.rectangle(0, 0, w, h); mgraphics.fill();\n"
        "    }\n"
        "    var pl = plot_left(), pr = plot_right(), pt = plot_top(), pb = plot_bottom();\n"
        "    var pw = pr - pl, ph = pb - pt;\n"
        # faint grid (xy_pad-style loop)
        "    mgraphics.set_source_rgba(GRID[0], GRID[1], GRID[2], GRID[3]);\n"
        "    mgraphics.set_line_width(0.5);\n"
        "    var gi;\n"
        "    for (gi = 1; gi < 4; gi++) {\n"
        "        var gx = pl + (gi / 4) * pw;\n"
        "        mgraphics.move_to(gx, pt); mgraphics.line_to(gx, pb); mgraphics.stroke();\n"
        "        var gy = pt + (gi / 4) * ph;\n"
        "        mgraphics.move_to(pl, gy); mgraphics.line_to(pr, gy); mgraphics.stroke();\n"
        "    }\n"
        # zero line for bipolar Y (EQ 0 dB reference)
        "    if (VMINY < 0 && VMAXY > 0) {\n"
        "        var zy = val_to_y(0);\n"
        "        mgraphics.set_source_rgba(GRID[0], GRID[1], GRID[2], 0.9);\n"
        "        mgraphics.set_line_width(1.0);\n"
        "        mgraphics.move_to(pl, zy); mgraphics.line_to(pr, zy); mgraphics.stroke();\n"
        "    }\n"
        # frame
        "    mgraphics.set_source_rgba(FRAME[0], FRAME[1], FRAME[2], 1.0);\n"
        "    mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle(pl + 0.5, pt + 0.5, pw - 1, ph - 1); mgraphics.stroke();\n"
        "    var nx = val_to_x(vx), ny = val_to_y(vy);\n"
        # optional symmetric bell through the node (EQ-band look)
        "    if (DRAW_CURVE) {\n"
        "        var bw = pw * 0.30;\n"  # fixed visual half-width
        "        var baseY = (VMINY < 0 && VMAXY > 0) ? val_to_y(0) : pb;\n"
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.85);\n"
        "        mgraphics.set_line_width(1.6);\n"
        "        mgraphics.move_to(clamp(nx - bw, pl, pr), baseY);\n"
        "        mgraphics.curve_to(nx - bw * 0.4, baseY, nx - bw * 0.45, ny, nx, ny);\n"
        "        mgraphics.curve_to(nx + bw * 0.45, ny, nx + bw * 0.4, baseY, clamp(nx + bw, pl, pr), baseY);\n"
        "        mgraphics.stroke();\n"
        "    } else {\n"
        # bare crosshair (XY-pad look)
        "        mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.35);\n"
        "        mgraphics.set_line_width(1.0);\n"
        "        mgraphics.move_to(nx, pt); mgraphics.line_to(nx, pb); mgraphics.stroke();\n"
        "        mgraphics.move_to(pl, ny); mgraphics.line_to(pr, ny); mgraphics.stroke();\n"
        "    }\n"
        # the node: drop shadow + glow + filled accent + white center
        "    var r = dragging ? NODE_RADIUS_SEL : NODE_RADIUS;\n"
        "    ds_drop_shadow(nx, ny, r + 2, 2, [0.0, 0.0, 0.0], 0.5);\n"
        "    ds_node_glow(nx, ny, [ACCENT[0], ACCENT[1], ACCENT[2]], r * 2.6, dragging ? 0.6 : 0.4);\n"
        "    mgraphics.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 1.0);\n"
        "    mgraphics.arc(nx, ny, r, 0, Math.PI * 2); mgraphics.fill();\n"
        "    mgraphics.set_source_rgba(0.97, 0.98, 1.0, 1.0);\n"
        "    mgraphics.arc(nx, ny, r * 0.36, 0, Math.PI * 2); mgraphics.fill();\n"
        # hover/drag crosshair + gutter readouts (premium-EQ style)
        "    if (hover || dragging) {\n"
        "        var cxp = dragging ? nx : clamp(hover_x, pl, pr);\n"
        "        var cyp = dragging ? ny : clamp(hover_y, pt, pb);\n"
        "        mgraphics.select_font_face(FONT); mgraphics.set_font_size(7.5);\n"
        # X readout (bottom gutter)
        "        var xtxt = fmt_x(dragging ? vx : x_to_val(cxp));\n"
        "        var xw = mgraphics.text_measure(xtxt)[0] + 4;\n"
        "        var fx = clamp(cxp - xw * 0.5, 0.0, w - xw);\n"
        "        mgraphics.set_source_rgba(0.05, 0.06, 0.08, 0.92);\n"
        "        mgraphics.rectangle(fx, pb + 1.0, xw, MB - 1.0); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 0.98);\n"
        "        mgraphics.move_to(fx + 2.0, pb + MB - 2.5); mgraphics.show_text(xtxt);\n"
        # Y readout (left gutter)
        "        var ytxt = fmt_y(dragging ? vy : y_to_val(cyp));\n"
        "        mgraphics.set_source_rgba(0.05, 0.06, 0.08, 0.92);\n"
        "        mgraphics.rectangle(0.0, cyp - 5.0, ML - 1.0, 10.0); mgraphics.fill();\n"
        "        mgraphics.set_source_rgba(TEXT[0], TEXT[1], TEXT[2], 0.98);\n"
        "        mgraphics.move_to(1.0, cyp + 2.5); mgraphics.show_text(ytxt);\n"
        "    }\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )
