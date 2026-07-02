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
