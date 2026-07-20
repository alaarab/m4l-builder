"""grain_cloud — Motes' hero: grain dots blooming over a rolling input wave.

A granular-class display on the D4 viz bus. The gen GUI tick re-derives
per-grain screen state from the UNTOUCHED ``data_param`` heap (progress, read
position, stereo spread) into ``buf_motes_grains`` (``3*n + 1`` samps; the
last samp is the freeze ramp), and keeps a rolling 128-bin input-peak history
in ``buf_motes_wave`` (``bins + 1`` samps; last samp = write head). This v8ui
draws the wave as symmetric bars (milky live / blue-lit frozen) with grain
dots over it. Wire with ``Device.add_viz_bus`` (grains + wave FIRST in the
buffer list — ``set_buffers`` binding is positional).
"""

from __future__ import annotations

from .buffer_viz import buffer_viz_js

MOTES_ACCENT = (0.62, 0.75, 0.96, 1.0)   # grain blue
MOTES_WAVE = (0.85, 0.87, 0.90, 1.0)     # milky wave


def grain_cloud_js(*, n_grains: int = 32, bins: int = 128,
                   accent=MOTES_ACCENT, wave_color=MOTES_WAVE,
                   poll_ms: int = 33) -> str:
    """v8ui source for the grain cloud (``frames.grains`` = ``[prog, pos,
    pan] * n + [freeze]``; ``frames.wave`` = ``bins`` peaks ``+ [head]``)."""
    acc = ", ".join(f"{c:g}" for c in accent)
    wav = ", ".join(f"{c:g}" for c in wave_color)
    draw = """
var g = frames.grains, wv = frames.wave;
var frz = (g && g[0]) ? g[0][N_GRAINS * 3] : 0;
if (wv && wv[0]) {
    var head = wv[0][BINS] | 0;
    var bw = w / BINS, cy = h / 2;
    for (var b = 0; b < BINS; b++) {
        var v = wv[0][(head + 1 + b) % BINS];
        if (v !== v) v = 0;
        var bh = Math.min(1, v) * (h * 0.46);
        var mixr = frz;
        mgraphics.set_source_rgba(
            WAV[0] + (ACC[0] - WAV[0]) * mixr,
            WAV[1] + (ACC[1] - WAV[1]) * mixr,
            WAV[2] + (ACC[2] - WAV[2]) * mixr,
            0.10 + 0.35 * (b / BINS));
        mgraphics.rectangle(b * bw, cy - bh, bw - 0.5, bh * 2 + 0.5);
        mgraphics.fill();
    }
}
if (g && g[0]) {
    for (var i = 0; i < N_GRAINS; i++) {
        var prog = g[0][i * 3], pos = g[0][i * 3 + 1], pan = g[0][i * 3 + 2];
        if (prog !== prog || prog <= 0) continue;
        var x = (1 - Math.min(1, pos)) * (w - 10) + 5;
        var y = h * (0.5 + 0.36 * (pan - 1));
        var r = 1.6 + 2.6 * (1 - prog);
        mgraphics.set_source_rgba(ACC[0], ACC[1], ACC[2],
                                  0.20 + 0.75 * (1 - prog));
        mgraphics.arc(x, y, r, 0, 2 * Math.PI);
        mgraphics.fill();
    }
}
"""
    return buffer_viz_js(
        draw=draw,
        buffers=[("grains", 3 * n_grains + 1, 1), ("wave", bins + 1, 1)],
        poll_ms=poll_ms,
        extra_globals=(f"var N_GRAINS = {int(n_grains)};\n"
                       f"var BINS = {int(bins)};\n"
                       f"var ACC = [{acc}];\n"
                       f"var WAV = [{wav}];\n"),
    )
