"""chaos_lanes — Entropy's hero: N stacked scrolling chaos traces.

One horizontal mini-lane per voice, each drawing its source's live value as a
scrolling trace (client-side ring history off the D4 viz bus), tinted by the
lane's SOURCE (six-colour palette: Drift/S&H/Drunk/Logistic/Lorenz/Burst),
brightness by depth, and dimmed to a whisper when the lane is beyond the
revealed count — so a Lorenz lane visibly writhes while an S&H lane steps,
which a polar ring can't show. Frame layout ``[value, source, depth, windowed]``
per lane plus the revealed-lane count at slot ``4*voices``
(:func:`gen_stateful.poly_chaos_engine` pokes exactly this).
"""

from __future__ import annotations

from .buffer_viz import buffer_viz_js

# One colour per source — related hues so the stack reads as a family.
SOURCE_COLORS = (
    (0.55, 0.62, 0.95),   # Drift — periwinkle
    (0.35, 0.85, 0.85),   # S&H — cyan
    (0.45, 0.90, 0.55),   # Drunk — green
    (0.95, 0.80, 0.35),   # Logistic — gold
    (0.95, 0.45, 0.40),   # Lorenz — ember
    (0.85, 0.45, 0.95),   # Burst — magenta
)


def chaos_lanes_js(*, voices: int = 8, accent=(0.72, 0.38, 0.95, 1.0),
                   history: int = 96, poll_ms: int = 33) -> str:
    """v8ui source for the lane-stack hero (``frames.entropy``:
    ``4*voices + 1`` samps, 1 channel)."""
    acc = ", ".join(f"{c:g}" for c in accent[:3])
    pal = ",\n    ".join(f"[{r:g}, {g:g}, {b:g}]" for r, g, b in SOURCE_COLORS)
    draw = """
var f = frames.entropy;
if (f && f[0]) {
    var lanes = Math.max(1, Math.min(VOICES, Math.round(f[0][VOICES * 4])));
    // push current values into the ring history
    for (var i = 0; i < VOICES; i++) {
        hist[i][hpos] = f[0][i * 4];
    }
    hpos = (hpos + 1) % HISTORY;
    var laneH = h / VOICES;
    for (var i = 0; i < VOICES; i++) {
        var src = Math.max(0, Math.min(5, Math.round(f[0][i * 4 + 1])));
        var dp = f[0][i * 4 + 2];
        var on = i < lanes ? 1 : 0;
        var c = PAL[src];
        var y0 = i * laneH;
        var alpha = on ? (0.28 + 0.62 * dp) : 0.07;
        // baseline
        mgraphics.set_source_rgba(c[0], c[1], c[2], on ? 0.14 : 0.05);
        mgraphics.move_to(2, y0 + laneH * 0.5);
        mgraphics.line_to(w - 2, y0 + laneH * 0.5);
        mgraphics.stroke();
        // the scrolling trace (newest at the right edge)
        mgraphics.set_source_rgba(c[0], c[1], c[2], alpha);
        mgraphics.set_line_width(on ? 1.3 : 0.8);
        var started = 0;
        for (var k = 0; k < HISTORY; k++) {
            var v = hist[i][(hpos + k) % HISTORY];
            var x = 2 + (w - 4) * (k / (HISTORY - 1));
            var y = y0 + laneH * (0.88 - 0.76 * v);
            if (!started) { mgraphics.move_to(x, y); started = 1; }
            else mgraphics.line_to(x, y);
        }
        mgraphics.stroke();
        // live head dot
        var vh = f[0][i * 4];
        mgraphics.set_source_rgba(c[0], c[1], c[2], on ? 0.95 : 0.12);
        mgraphics.arc(w - 4, y0 + laneH * (0.88 - 0.76 * vh), 2.0, 0, 2 * Math.PI);
        mgraphics.fill();
        // lane index tag
        mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], on ? 0.5 : 0.12);
        mgraphics.set_font_size(7);
        mgraphics.move_to(3, y0 + laneH * 0.5 - 2);
        mgraphics.show_text("" + (i + 1));
    }
}
"""
    return buffer_viz_js(
        draw=draw,
        buffers=[("entropy", 4 * voices + 1, 1)],
        poll_ms=poll_ms,
        extra_globals=(
            f"var VOICES = {int(voices)};\n"
            f"var HISTORY = {int(history)};\n"
            f"var ACC = [{acc}];\n"
            f"var PAL = [\n    {pal}\n];\n"
            "var hist = [];\n"
            "for (var _i = 0; _i < VOICES; _i++) {\n"
            "    hist.push([]);\n"
            "    for (var _k = 0; _k < HISTORY; _k++) hist[_i].push(0.5);\n"
            "}\n"
            "var hpos = 0;\n"
        ),
    )
