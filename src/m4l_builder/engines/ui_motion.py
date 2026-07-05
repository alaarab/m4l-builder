"""ui_motion — UXI foundations 5 + 6 (T28, ux_innovation_plan).

* :func:`tween_js` — the UI-thread smoothing engine: a shared 33 ms Task
  drives frame-rate-INDEPENDENT exponential ease-out for any number of
  keyed values (``tw_set``/``tw_get``); the Task self-stops when every
  value converges, so an idle device burns nothing. The step math is a
  pure function (``tw_step``) for node-harness testing.
* :func:`glow_js` — the theme + glow palette: one accent array drives
  every interactive state (``ds_accent_state``), plus ``ds_node_glow``
  (layered-arc halo), ``ds_drop_shadow`` (two-layer soft shadow) and
  ``ds_heatmap_cell`` (bg→accent lerp fill).

ES5-safe (jsui + v8ui). State is ``tw_``/``ds_``-prefixed; composes with
the T27 ``ui_interaction`` mixins.
"""

TWEEN_JS = r"""
// ── tween / smoothing engine (T28 F5) ────────────────────────────────────
var tw_map = {};            // key -> {cur, target, tau_ms}
var tw_task = null;
var tw_last_ms = 0;
var tw_epsilon = 0.0005;

function tw_step(cur, target, tau_ms, dt_ms) {
    // frame-rate-independent exponential ease-out (pure; node-testable):
    // the fraction covered depends only on dt/tau, not on frame cadence.
    var k = 1.0 - Math.exp(-dt_ms / Math.max(1.0, tau_ms));
    var next = cur + (target - cur) * k;
    if (Math.abs(target - next) < tw_epsilon) next = target;
    return next;
}

function tw_tick() {
    var now = Date.now();
    var dt = tw_last_ms > 0 ? (now - tw_last_ms) : 33;
    tw_last_ms = now;
    var live = 0;
    for (var key in tw_map) {
        var t = tw_map[key];
        t.cur = tw_step(t.cur, t.target, t.tau_ms, dt);
        if (t.cur !== t.target) live++;
    }
    mgraphics.redraw();
    if (!live && tw_task) { tw_task.cancel(); tw_task = null; tw_last_ms = 0; }
}

function tw_set(key, target, tau_ms) {
    if (!(key in tw_map)) tw_map[key] = {cur: target, target: target,
                                         tau_ms: tau_ms || 90};
    var t = tw_map[key];
    t.target = target;
    if (tau_ms) t.tau_ms = tau_ms;
    if (t.cur !== t.target && !tw_task) {
        tw_task = new Task(tw_tick);
        tw_task.interval = 33;
        tw_last_ms = 0;
        tw_task.repeat();
    }
}

function tw_jump(key, value) {
    // set without animating (init / preset recall)
    if (!(key in tw_map)) tw_map[key] = {cur: value, target: value,
                                         tau_ms: 90};
    else { tw_map[key].cur = value; tw_map[key].target = value; }
}

function tw_get(key, fallback) {
    return (key in tw_map) ? tw_map[key].cur : fallback;
}
"""

GLOW_JS = r"""
// ── theme + glow palette (T28 F6) ────────────────────────────────────────
function ds_accent_state(accent, state) {
    // one accent drives every interactive state; returns [r,g,b,a].
    // states: "idle" | "hover" | "active" | "selected" | "disabled"
    var a = 0.75;
    if (state === "hover") a = 0.9;
    else if (state === "active") a = 1.0;
    else if (state === "selected") a = 1.0;
    else if (state === "disabled") a = 0.25;
    return [accent[0], accent[1], accent[2], a];
}

function ds_node_glow(x, y, r, accent, intensity) {
    // layered-arc halo (cheap radial glow; intensity 0..1)
    var k = intensity === undefined ? 1.0 : intensity;
    var layers = [[r * 2.4, 0.05], [r * 1.8, 0.10], [r * 1.3, 0.18]];
    for (var i = 0; i < layers.length; i++) {
        mgraphics.set_source_rgba(accent[0], accent[1], accent[2],
                                  layers[i][1] * k);
        mgraphics.arc(x, y, layers[i][0], 0, Math.PI * 2);
        mgraphics.fill();
    }
}

function ds_drop_shadow(x, y, w, h, radius, alpha) {
    // two-layer soft shadow under a card/panel
    var a = alpha === undefined ? 0.35 : alpha;
    mgraphics.set_source_rgba(0, 0, 0, a * 0.45);
    mgraphics.rectangle_rounded(x - 2, y + 3, w + 4, h + 4, radius + 2,
                                radius + 2);
    mgraphics.fill();
    mgraphics.set_source_rgba(0, 0, 0, a);
    mgraphics.rectangle_rounded(x, y + 1.5, w, h + 1, radius, radius);
    mgraphics.fill();
}

function ds_heatmap_lerp(v, bg, accent) {
    // pure color math (node-testable): bg -> accent by v (0..1)
    var t = v < 0 ? 0 : (v > 1 ? 1 : v);
    return [bg[0] + (accent[0] - bg[0]) * t,
            bg[1] + (accent[1] - bg[1]) * t,
            bg[2] + (accent[2] - bg[2]) * t,
            1.0];
}

function ds_heatmap_cell(x, y, w, h, v, bg, accent) {
    var c = ds_heatmap_lerp(v, bg, accent);
    mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
    mgraphics.rectangle(x, y, w, h);
    mgraphics.fill();
}
"""


def tween_js() -> str:
    """The shared-Task exponential-ease smoothing engine (foundation 5)."""
    return TWEEN_JS


def glow_js() -> str:
    """Accent-state palette + glow/shadow/heatmap primitives (foundation 6)."""
    return GLOW_JS


def ui_motion_js() -> str:
    """Both motion/theme foundations."""
    return TWEEN_JS + GLOW_JS
