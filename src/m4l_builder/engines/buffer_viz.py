"""buffer_viz — the jsui read side of the D4 gen->named-buffer->jsui viz bus.

The corpus keystone for live displays (stranular's grain cloud, lfo-cluster's
polar rings, Particle-Reverb's state ring): the gen~ engine pokes per-frame
screen state into ``---``-scoped ``buffer~`` objects (see
``gen_stateful.viz_declares`` / ``viz_poke_block``), and THIS v8ui peeks the
same buffers on a self-owned poll ``Task`` and redraws — zero patchcord
traffic, and the display physically cannot desync from the DSP.

Name delivery: ``---`` substitution happens in box text/args/jsarguments but
NOT inside generated JS strings, so the device sends the RESOLVED names at
load via a ``set_buffers <nameA> <nameB> ...`` message (positional, matching
the ``buffers`` order) — the fleet-proven ``set_analyzer_buffer`` idiom from
``eq_curve.py``. ``Device.add_viz_bus`` wires all of this.

The injected ``draw`` body runs inside ``paint()`` with:
  ``frames``  — object keyed by buffer name-key: ``frames[key]`` is an array of
                per-channel arrays (``frames[key][ch][i]``), or null until the
                first successful peek;
  ``w, h``    — the canvas size.
"""

from __future__ import annotations

DEFAULT_BG = "0.08, 0.09, 0.10, 1.0"


def buffer_viz_js(*, draw: str, buffers: list, poll_ms: int = 33,
                  bg_color: str = DEFAULT_BG, extra_globals: str = "",
                  extra_handlers: str = "") -> str:
    """v8ui source for a buffer-peeking animated display.

    ``buffers``: list of ``(key, samps, channels)`` — ``key`` is the LOCAL name
    the ``draw`` body uses (``frames[key]``); the runtime buffer~ name arrives
    positionally via ``set_buffers``. ``draw``: a JS statement block drawing
    from ``frames``. ``extra_globals`` / ``extra_handlers``: optional JS spliced
    at module scope (constants, message handlers).
    """
    keys = [b[0] for b in buffers]
    samps = [int(b[1]) for b in buffers]
    chans = [int(b[2]) for b in buffers]
    keys_js = ", ".join(f'"{k}"' for k in keys)
    samps_js = ", ".join(str(n) for n in samps)
    chans_js = ", ".join(str(c) for c in chans)
    return f"""// buffer_viz — D4 gen->buffer~->jsui animated display (corpus keystone)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 0;

var BG = [{bg_color}];
var VIZ_KEYS = [{keys_js}];
var VIZ_SAMPS = [{samps_js}];
var VIZ_CHANS = [{chans_js}];
var viz_names = [];      // resolved buffer~ names (set_buffers, positional)
var frames = {{}};
var poll_task = null;
{extra_globals}
function set_buffers() {{
    var args = arrayfromargs(arguments);
    viz_names = [];
    for (var i = 0; i < args.length && i < VIZ_KEYS.length; i++) {{
        viz_names[i] = "" + args[i];
    }}
    start_viz_poll();
}}

function read_viz_frame(name, samps, channels) {{
    if (name === "" || name === undefined) return null;
    try {{
        var b = new Buffer(name);
        var out = [];
        for (var ch = 0; ch < channels; ch++) {{
            out[ch] = b.peek(ch + 1, 0, samps);   // peek(channel is 1-based)
        }}
        return out;
    }} catch (e) {{
        return null;    // buffer~ not instantiated yet — retry next tick
    }}
}}

function poll_viz_buffers() {{
    var changed = 0;
    for (var i = 0; i < VIZ_KEYS.length; i++) {{
        var vals = read_viz_frame(viz_names[i], VIZ_SAMPS[i], VIZ_CHANS[i]);
        if (vals !== null) {{
            frames[VIZ_KEYS[i]] = vals;
            changed = 1;
        }}
    }}
    if (changed) mgraphics.redraw();
}}

function start_viz_poll() {{
    if (poll_task !== null) return;
    if (typeof Task !== "undefined") {{
        poll_task = new Task(poll_viz_buffers);
        poll_task.interval = {int(poll_ms)};
        poll_task.repeat();
    }} else if (typeof setInterval !== "undefined") {{
        poll_task = setInterval(poll_viz_buffers, {int(poll_ms)});
    }}
}}
{extra_handlers}
function paint() {{
    var w = mgraphics.size[0], h = mgraphics.size[1];
    mgraphics.set_source_rgba(BG[0], BG[1], BG[2], BG[3]);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();
{_indent(draw, 1)}
}}

function bang() {{
    mgraphics.redraw();
}}
"""


def _indent(code: str, levels: int) -> str:
    pad = "    " * levels
    return "\n".join(pad + ln if ln.strip() else ln
                     for ln in code.strip().split("\n"))


def multi_lane_thumbnail_js(*, key: str, samps: int, lanes: int,
                            colors: list, poll_ms: int = 50,
                            bg_color: str = DEFAULT_BG,
                            line_width: float = 1.2) -> str:
    """Multi-curve thumbnail (dnksaus Multi Shaper, catalog #20): ALL lanes'
    curves overlaid in their lane colors in one small square — the
    "small multiples" summary of a multi-lane device.

    Reads one ``(key, samps, lanes)`` viz buffer (values normalized 0..1 per
    sample) and polylines every channel. ``colors``: one RGBA list per lane
    (cycled if short). Deliver the resolved buffer name via ``set_buffers``
    exactly like every buffer_viz display.
    """
    cols = [list(colors[i % len(colors)]) for i in range(lanes)]
    cols_js = ", ".join(
        "[" + ", ".join(f"{float(c):.4g}" for c in col[:4]) + "]"
        for col in cols)
    draw = f"""
  var f = frames["{key}"];
  if (f) {{
    var pad = 2, pw = w - pad * 2, ph = h - pad * 2;
    for (var ch = 0; ch < {int(lanes)}; ch++) {{
      var lane = f[ch];
      if (!lane) continue;
      mgraphics.set_source_rgba(TH_COLS[ch]);
      mgraphics.set_line_width({float(line_width)});
      for (var i = 0; i < lane.length; i++) {{
        var px = pad + pw * i / (lane.length - 1);
        var py = pad + ph * (1.0 - Math.max(0, Math.min(1, lane[i])));
        if (i === 0) mgraphics.move_to(px, py);
        else mgraphics.line_to(px, py);
      }}
      mgraphics.stroke();
    }}
  }}
"""
    return buffer_viz_js(
        draw=draw,
        buffers=[(key, int(samps), int(lanes))],
        poll_ms=poll_ms,
        bg_color=bg_color,
        extra_globals=f"var TH_COLS = [{cols_js}];\n",
    )


def waveform_layers_js(*, key: str, samps: int, audio_ch: int = 0,
                       gain_ch: int = None, channels: int = None,
                       poll_ms: int = 50,
                       wave_color: str = "0.55, 0.58, 0.62, 1.0",
                       gain_color: str = "0.90, 0.36, 0.60, 1.0",
                       head_color: str = "0.05, 0.76, 0.83, 1.0",
                       bg_color: str = DEFAULT_BG,
                       playhead: bool = False, ruler: bool = False,
                       caption: bool = False) -> str:
    """Layered buffer waveform (catalog #44 + #45 + #46): grey audio
    history with an optional APPLIED-GAIN polyline over it (Clix pink-over-
    grey — show what the processor DID), an optional live playhead cursor
    (``set_playhead 0..1`` messages, Live Stretch), and an optional
    sample-count ruler + ``set_caption <name…>`` filename line (Random
    Sample Picker).

    Buffer contract: one ``(key, samps, channels)`` viz buffer —
    ``audio_ch`` holds -1..1 audio, ``gain_ch`` (if given) holds 0..1 gain.
    """
    n_ch = channels if channels is not None else (
        max(audio_ch, gain_ch if gain_ch is not None else 0) + 1)
    handlers = """
function set_playhead(v) {
    ph = Math.max(0, Math.min(1, v));
    mgraphics.redraw();
}
function set_caption() {
    cap = Array.prototype.slice.call(arguments).join(" ");
    mgraphics.redraw();
}
"""
    globs = f"""var ph = -1.0;
var cap = "";
var WAVE_C = [{wave_color}];
var GAIN_C = [{gain_color}];
var HEAD_C = [{head_color}];
"""
    gain_block = "" if gain_ch is None else f"""
    var g = f[{int(gain_ch)}];
    if (g) {{
      mgraphics.set_source_rgba(GAIN_C);
      mgraphics.set_line_width(1.4);
      for (var gi = 0; gi < g.length; gi++) {{
        var gx = pad + pw * gi / (g.length - 1);
        var gy = pad + phh * (1.0 - Math.max(0, Math.min(1, g[gi])));
        if (gi === 0) mgraphics.move_to(gx, gy);
        else mgraphics.line_to(gx, gy);
      }}
      mgraphics.stroke();
    }}"""
    head_block = "" if not playhead else """
    if (ph >= 0) {
      mgraphics.set_source_rgba(HEAD_C);
      mgraphics.rectangle(pad + pw * ph - 1, pad, 2, phh);
      mgraphics.fill();
    }"""
    ruler_block = "" if not ruler else f"""
    mgraphics.set_source_rgba(WAVE_C[0], WAVE_C[1], WAVE_C[2], 0.8);
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(6.0);
    var marks = [0, 0.5, 1.0];
    for (var mi = 0; mi < marks.length; mi++) {{
      var mx = pad + pw * marks[mi];
      mgraphics.rectangle(mx - 0.5, pad + phh - 3, 1, 3);
      mgraphics.fill();
      var lbl = "" + Math.round(marks[mi] * {int(samps)});
      mgraphics.move_to(Math.min(mx + 2, w - 24), pad + phh - 5);
      mgraphics.show_text(lbl);
    }}"""
    cap_block = "" if not caption else """
    if (cap.length) {
      mgraphics.set_source_rgba(WAVE_C[0], WAVE_C[1], WAVE_C[2], 0.9);
      mgraphics.select_font_face("Ableton Sans Medium");
      mgraphics.set_font_size(6.5);
      mgraphics.move_to(pad + 2, pad + 8);
      mgraphics.show_text(cap);
    }"""
    draw = f"""
  var f = frames["{key}"];
  var pad = 1, pw = w - pad * 2, phh = h - pad * 2;
  if (f) {{
    var a = f[{int(audio_ch)}];
    if (a) {{
      mgraphics.set_source_rgba(WAVE_C[0], WAVE_C[1], WAVE_C[2], 0.55);
      var mid = pad + phh / 2;
      for (var i = 0; i < a.length; i++) {{
        var x = pad + pw * i / (a.length - 1);
        var v = Math.max(-1, Math.min(1, a[i]));
        var hh = Math.max(0.5, Math.abs(v) * phh / 2);
        mgraphics.rectangle(x, mid - hh, Math.max(1, pw / a.length), hh * 2);
        mgraphics.fill();
      }}
    }}{gain_block}{head_block}{ruler_block}{cap_block}
  }}
"""
    return buffer_viz_js(
        draw=draw,
        buffers=[(key, int(samps), int(n_ch))],
        poll_ms=poll_ms,
        bg_color=bg_color,
        extra_globals=globs,
        extra_handlers=handlers,
    )
