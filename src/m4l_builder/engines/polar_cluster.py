"""polar_cluster — Orbit's hero: concentric rings + orbiting dots per voice.

The lfo-cluster signature display on the D4 viz bus: the poly_lfo_engine pokes
``[radius, phase, value, depth]`` per voice into a ``---``-scoped buffer on
its GUI tick; this v8ui (a :func:`buffer_viz_js` draw body) renders each voice
as a ring whose radius is the cluster-fold spread and a dot orbiting at the
voice's phase, lit by its current windowed value. Wire with
``Device.add_viz_bus`` exactly like any buffer_viz display.
"""

from __future__ import annotations

from .buffer_viz import buffer_viz_js

ORBIT_ACCENT = (0.96, 0.70, 0.20, 1.0)   # amber (unipolar voices)
ORBIT_ACCENT2 = (0.30, 0.75, 0.95, 1.0)  # cyan (reserved: bipolar tint)


def polar_cluster_js(*, voices: int = 4, accent=ORBIT_ACCENT,
                     accent2=ORBIT_ACCENT2, poll_ms: int = 33) -> str:
    """v8ui source for the polar cluster hero (``frames.orbit`` layout:
    ``[r, phase, value, depth]`` per voice, ``4*voices`` samps, 1 channel)."""
    acc = ", ".join(f"{c:g}" for c in accent)
    acc2 = ", ".join(f"{c:g}" for c in accent2)
    draw = """
var f = frames.orbit;
if (f && f[0]) {
    var cx = w / 2, cy = h / 2;
    var maxR = Math.min(w, h) / 2 - 7;
    for (var i = 0; i < VOICES; i++) {
        var r = f[0][i * 4], ph = f[0][i * 4 + 1];
        var v = f[0][i * 4 + 2], dp = f[0][i * 4 + 3];
        if (r !== r) continue;
        var R = 10 + r * (maxR - 10);
        mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], 0.10 + 0.18 * dp);
        mgraphics.set_line_width(1.0);
        mgraphics.arc(cx, cy, R, 0, 2 * Math.PI);
        mgraphics.stroke();
        var ang = ph * 2 * Math.PI - Math.PI / 2;
        var dx = cx + R * Math.cos(ang), dy = cy + R * Math.sin(ang);
        mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2], 0.25 + 0.75 * v);
        mgraphics.arc(dx, dy, 3.2, 0, 2 * Math.PI);
        mgraphics.fill();
    }
    mgraphics.set_source_rgba(ACC2[0], ACC2[1], ACC2[2], 0.5);
    mgraphics.arc(cx, cy, 1.6, 0, 2 * Math.PI);
    mgraphics.fill();
}
"""
    return buffer_viz_js(
        draw=draw,
        buffers=[("orbit", 4 * voices, 1)],
        poll_ms=poll_ms,
        extra_globals=(f"var VOICES = {int(voices)};\n"
                       f"var ACC = [{acc}];\n"
                       f"var ACC2 = [{acc2}];\n"),
    )
