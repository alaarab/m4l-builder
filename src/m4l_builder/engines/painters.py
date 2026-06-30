"""Render-only ``jspainterfile`` painters (C1).

A ``jspainterfile`` is a small ES5 ``.js`` that PAINTS a *native* Live control
(``live.dial`` / ``live.numbox`` / ``toggle`` …) — the control keeps full native
behaviour and parameter storage (``parameter_enable: 1``); the script only draws
it. The corpus leans on this hard (Superberry has 67 ``jspainterfile`` instances,
Chiral 19, the AS Console suite one each) — it is how they get a custom look
without a hidden second control. Attach one with
:meth:`m4l_builder.device.Device.paint_control`.

NOTE: the corpus ``.amxd`` only references each painter by *filename* (the script
bytes are a separate bundled file, not in the patcher JSON), so these painters are
authored from the documented ``mgraphics`` API (the same one the ``jsui`` engines
already use) rather than lifted verbatim — their RENDER must be Live-verified when
a device first uses them. To stay low-risk these are BACKGROUND painters: they fill
the control's rectangle (dimensions baked in at build time, so no reliance on the
runtime size-query API) and never try to read the control value.
"""

from __future__ import annotations


def _rgba(color) -> str:
    """``[r,g,b,a]`` (or ``[r,g,b]``) -> the ``r, g, b, a`` literal mgraphics wants."""
    c = list(color)
    if len(c) == 3:
        c = c + [1.0]
    return ", ".join(repr(round(float(v), 4)) for v in c[:4])


def lcd_dial_painter_js(*, track="0.22, 0.24, 0.28, 1.0",
                        body="0.13, 0.14, 0.16, 1.0", sweep_deg=270.0,
                        line_w=2.4) -> str:
    """Return an ORIGINAL render-only ``jspainterfile`` painter for a native
    ``live.dial`` — an original implementation of the universal knob-drawing idea
    (a swept value arc + a dark body + an indicator), NOT lifted from any device.

    It reads the host dial's live value (``box.getvalueof()``) and range
    (``box.getattr("_parameter_range")``) to fill the arc, and tints from the dial's
    own ``activedialcolor`` / ``dialcolor`` so it themes per-control. The control
    stays a full native automatable parameter; this only draws it. Attach with
    ``Device.paint_control(box_id, "x.js", painter_js=lcd_dial_painter_js())``.
    Render must be Live-verified on first use (mgraphics is authored, not snapshot).
    """
    half = sweep_deg / 2.0
    return (
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "function _norm() {\n"
        '    var r = box.getattr("_parameter_range");\n'
        "    var v = box.getvalueof();\n"
        '    if (box.getattr("_parameter_type") == 2) {\n'
        "        var n = (r && r.length) ? r.length - 1 : 1;\n"
        "        return n > 0 ? parseFloat(v) / n : 0.0;\n"
        "    }\n"
        "    if (!r || r.length < 2 || r[1] == r[0]) return 0.0;\n"
        "    var t = (v - r[0]) / (r[1] - r[0]);\n"
        "    return t < 0 ? 0.0 : (t > 1 ? 1.0 : t);\n"
        "}\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0], h = mgraphics.size[1];\n"
        "    var cx = w * 0.5, cy = h * 0.5, rad = Math.min(w, h) * 0.40;\n"
        "    var t = _norm();\n"
        '    var acc = box.getattr("active") ? box.getattr("activedialcolor")\n'
        '                                    : box.getattr("dialcolor");\n'
        "    if (!acc) acc = [0.43, 0.83, 1.0, 1.0];\n"
        f"    var DEG = Math.PI / 180.0, a0 = (90 + {half}) * DEG, a1 = (90 + 360 - {half}) * DEG;\n"
        "    var va = a0 + (a1 - a0) * t;\n"
        f"    mgraphics.set_line_width({line_w});\n"
        f"    mgraphics.set_source_rgba({track});\n"
        "    mgraphics.arc(cx, cy, rad, a0, a1); mgraphics.stroke();\n"
        "    mgraphics.set_source_rgba(acc[0], acc[1], acc[2], 1.0);\n"
        "    mgraphics.arc(cx, cy, rad, a0, va); mgraphics.stroke();\n"
        f"    mgraphics.set_source_rgba({body});\n"
        "    mgraphics.ellipse(cx - rad * 0.66, cy - rad * 0.66, rad * 1.32, rad * 1.32);\n"
        "    mgraphics.fill();\n"
        "    mgraphics.set_line_width(2.0);\n"
        "    mgraphics.set_source_rgba(acc[0], acc[1], acc[2], 1.0);\n"
        "    mgraphics.move_to(cx + Math.cos(va) * rad * 0.30, cy + Math.sin(va) * rad * 0.30);\n"
        "    mgraphics.line_to(cx + Math.cos(va) * rad * 0.60, cy + Math.sin(va) * rad * 0.60);\n"
        "    mgraphics.stroke();\n"
        "}\n"
    )


def lcd_slider_painter_js(*, accent="0.43, 0.83, 1.0", track="0.17, 0.19, 0.23, 1.0",
                          handle="0.86, 0.90, 0.95, 1.0") -> str:
    """Return an ORIGINAL render-only ``jspainterfile`` painter for a native
    ``live.slider`` — a groove + an accent fill to the value + a handle bar. Original
    implementation of the universal fader idea (not lifted from any device); it reads
    the host slider's live value (``box.getvalueof()`` + ``_parameter_range``) and
    auto-orients vertical/horizontal by the box aspect. ``accent`` is the fill color.
    """
    return (
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "function _norm() {\n"
        '    var r = box.getattr("_parameter_range");\n'
        "    var v = box.getvalueof();\n"
        "    if (!r || r.length < 2 || r[1] == r[0]) return 0.0;\n"
        "    var t = (v - r[0]) / (r[1] - r[0]);\n"
        "    return t < 0 ? 0.0 : (t > 1 ? 1.0 : t);\n"
        "}\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0], h = mgraphics.size[1], t = _norm();\n"
        "    var vert = h >= w, pad = 3.0;\n"
        "    if (vert) {\n"
        "        var gx = w * 0.5 - 2.0, gh = h - 2 * pad;\n"
        f"        mgraphics.set_source_rgba({track});\n"
        "        mgraphics.rectangle_rounded(gx, pad, 4.0, gh, 2, 2); mgraphics.fill();\n"
        "        var fh = gh * t;\n"
        f"        mgraphics.set_source_rgba({accent}, 1.0);\n"
        "        mgraphics.rectangle_rounded(gx, pad + gh - fh, 4.0, fh, 2, 2); mgraphics.fill();\n"
        "        var hy = pad + gh - fh;\n"
        f"        mgraphics.set_source_rgba({handle});\n"
        "        mgraphics.rectangle_rounded(w * 0.5 - 7.0, hy - 2.0, 14.0, 4.0, 2, 2); mgraphics.fill();\n"
        "    } else {\n"
        "        var gy = h * 0.5 - 2.0, gw = w - 2 * pad;\n"
        f"        mgraphics.set_source_rgba({track});\n"
        "        mgraphics.rectangle_rounded(pad, gy, gw, 4.0, 2, 2); mgraphics.fill();\n"
        "        var fw = gw * t;\n"
        f"        mgraphics.set_source_rgba({accent}, 1.0);\n"
        "        mgraphics.rectangle_rounded(pad, gy, fw, 4.0, 2, 2); mgraphics.fill();\n"
        f"        mgraphics.set_source_rgba({handle});\n"
        "        mgraphics.rectangle_rounded(pad + fw - 2.0, h * 0.5 - 7.0, 4.0, 14.0, 2, 2); mgraphics.fill();\n"
        "    }\n"
        "}\n"
    )


def lcd_panel_painter_js(width: float, height: float, *, bg, border=None,
                         radius: float = 3.0) -> str:
    """Return a render-only ``jspainterfile`` painter that fills a native control
    with a themed rounded LCD panel (optional 1 px border).

    ``width`` / ``height`` are the control's pixel size (baked into the script so
    it never queries size at runtime); ``bg`` / ``border`` are ``[r,g,b,a]``. Drawn
    with the framework's standard ``mgraphics.rectangle_rounded`` + ``fill`` idiom.
    Pass the result as ``painter_js`` to ``Device.paint_control``.
    """
    border_block = ""
    if border is not None:
        border_block = (
            f"    mgraphics.set_source_rgba({_rgba(border)});\n"
            "    mgraphics.set_line_width(1);\n"
            f"    mgraphics.rectangle_rounded(0.5, 0.5, {width - 1}, {height - 1}, "
            f"{radius}, {radius});\n"
            "    mgraphics.stroke();\n"
        )
    return (
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "function paint() {\n"
        f"    mgraphics.set_source_rgba({_rgba(bg)});\n"
        f"    mgraphics.rectangle_rounded(0, 0, {width}, {height}, "
        f"{radius}, {radius});\n"
        "    mgraphics.fill();\n"
        f"{border_block}"
        "}\n"
    )
