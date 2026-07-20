"""Premium drawing-techniques library + a showcase glass/metal background.

``premium_drawing_techniques`` is NOT a new pointer-control: it is a SHARED
rendering library that upgrades how EVERY existing custom control PAINTS. The
deliverable has two parts:

1. ``DS_HELPERS_JS`` — eight reusable, pure-ES5 ``ds_*`` mgraphics helpers
   (soft shadows, rim/glass/metal materials, glowing arcs, deterministic noise,
   gradient-filled curves). These build ONLY on primitives proven in Live
   (``pattern_create_linear``/``pattern_create_radial`` + ``add_color_stop_rgba``,
   ``arc``, ``rectangle_rounded``, ``move_to``/``curve_to``/``close_path``,
   ``fill``/``stroke``). mgraphics has NO clip/save/restore/transform/dash and its
   radial gradients ignore the inner-radius term, so every soft edge is FAKED with
   a single-center radial fill (the ``ds_node_glow`` shape) or stacked alpha
   strokes — never a feathered box-gradient. Every Max-global call stays wrapped in
   try/catch so it can't wedge under the Node harness, matching the existing
   ``design_system.py`` snippet's rule.

   The lead folds ``DS_HELPERS_JS`` into ``design_system.DESIGN_SYSTEM_JS`` and
   bumps ``DESIGN_SYSTEM_VERSION`` 1->2; once there, every control that already
   prepends ``design_system_js()`` can call the new ``ds_*`` symbols for free.

2. ``glass_panel_bg_js`` — a showcase full-device v8ui background that EXERCISES
   the new helpers (frosted-glass plate + faked inner shadow + rim light + stable
   noise texture), so the library can be Live-verified in a real device. It mirrors
   ``panel_bg_js`` exactly: prepends ``design_system_js()``, self-paints its own
   gradient, satisfies the v8ui contract (init / relative_coords=0 / autofill=0 /
   ``paint()`` / a ``redraw()`` hook), 1 inlet / 0 outlets, no pointer.

Cache note (same as ``design_system.py``): bumping the embedded helpers means
bumping ``DESIGN_SYSTEM_VERSION`` AND every embedding device's versioned
``js_filename`` (fold ``version_tag()`` in) or Live serves the stale sidecar — the
single most likely false-negative during verify.
"""

from .design_system import design_system_js

# ── The eight reusable ds_* drawing helpers (pure ES5) ──────────────────────
# Namespaced ds_*, var/function only (no let/const/arrow/backtick/class), every
# Max-global call wrapped in try/catch — identical discipline to DESIGN_SYSTEM_JS
# so it slots straight into that snippet and passes the jsui ES5 checker too. The
# lead appends this block to design_system.DESIGN_SYSTEM_JS and bumps the version.
DS_HELPERS_JS = """\
// ── premium drawing techniques (shared, pure ES5) ────────────────────────
// Soft edges are FAKED: mgraphics has no blur/box-gradient/clip and its radial
// gradients ignore the inner radius, so we reuse the single-center ds_node_glow
// fill or stack at most 3 alpha layers. Keep alpha steps coarse-enough-to-see but
// fine-enough-not-to-band (3 layers max).

// 1. Outer drop shadow for a ROUNDED-RECT element: stack 2-3 rounded fills at a
// growing inset below/right, falling alpha, since we can't blur. Generalizes the
// existing ds_drop_shadow (which is the radial form for round bodies).
function ds_outer_shadow(x, y, w, h, r, dx, dy, alpha) {
    var a0 = (alpha === undefined) ? 0.18 : alpha;
    var steps = [[2.5, a0], [1.2, a0 * 0.55], [0.0, a0 * 0.28]];
    var i, s, g;
    for (i = 0; i < steps.length; i++) {
        g = steps[i][0];
        mgraphics.set_source_rgba(0.0, 0.0, 0.0, steps[i][1]);
        mgraphics.rectangle_rounded(x + dx - g, y + dy - g, w + 2 * g, h + 2 * g,
                                    r + g, r + g);
        mgraphics.fill();
    }
}

// 2. Inner shadow on a filled panel: stroke the rounded rect at +0.5/+1.5/+2.5
// inset in falling-alpha black with growing line width — a faked top-inner
// feather (the NanoVG inner-shadow look without a box-gradient). Call AFTER the
// panel fill.
function ds_inner_shadow(x, y, w, h, r, depth) {
    var d = (depth === undefined) ? 1.0 : depth;
    var layers = [[0.5, 0.30, 1.0], [1.5, 0.16, 1.4], [2.5, 0.07, 1.8]];
    var i, ins, a, lw;
    for (i = 0; i < layers.length; i++) {
        ins = layers[i][0] * d;
        a = layers[i][1];
        lw = layers[i][2];
        mgraphics.set_source_rgba(0.0, 0.0, 0.0, a);
        mgraphics.set_line_width(lw);
        mgraphics.rectangle_rounded(x + ins, y + ins, w - 2 * ins, h - 2 * ins,
                                    Math.max(0.5, r - ins), Math.max(0.5, r - ins));
        mgraphics.stroke();
    }
}

// 3. Rim / catch light: a thin bright stroke on the rounded-rect edge (clr@a),
// the lit top edge of a material. Subtle by default.
function ds_rim_light(x, y, w, h, r, clr, a) {
    var aa = (a === undefined) ? 0.5 : a;
    mgraphics.set_source_rgba(clr[0], clr[1], clr[2], aa);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle_rounded(x + 0.5, y + 0.5, w - 1, h - 1, r, r);
    mgraphics.stroke();
}

// 4. Frosted-glass plate: vertical body gradient (hi top -> lo bottom) + a top
// highlight ellipse spanning the upper ~45% + a rim light on the top edge. lo/hi
// are [r,g,b] arrays.
function ds_glass_panel(x, y, w, h, r, lo, hi) {
    var g = mgraphics.pattern_create_linear(x, y, x, y + h);
    g.add_color_stop_rgba(0.0, hi[0], hi[1], hi[2], 1.0);
    g.add_color_stop_rgba(1.0, lo[0], lo[1], lo[2], 1.0);
    mgraphics.set_source(g);
    mgraphics.rectangle_rounded(x, y, w, h, r, r);
    mgraphics.fill();
    // Top sheen: a soft white wash over the upper plate (radial fade so it is a
    // glassy highlight, not a hard band). Centre above the plate so only its
    // lower bloom shows across the top.
    var hy = y + h * 0.10;
    var hr = Math.max(w, h) * 0.55;
    var sh = mgraphics.pattern_create_radial(x + w * 0.5, hy, 0.0, x + w * 0.5, hy, hr);
    sh.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.07);
    sh.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0);
    mgraphics.set_source(sh);
    mgraphics.rectangle_rounded(x, y, w, h, r, r);
    mgraphics.fill();
    ds_rim_light(x, y, w, h, r, [1.0, 1.0, 1.0], 0.10);
}

// 5. Brushed-metal cap: the radial hi-center -> lo-rim fill the knob body already
// uses, promoted so toggles/buttons reuse the look. Highlight sits up-left of
// center (the proven knob offset). hi/lo are [r,g,b] arrays.
function ds_metal_radial(cx, cy, R, hi, lo) {
    var g = mgraphics.pattern_create_radial(cx, cy - R * 0.45, 0.0, cx, cy, R);
    g.add_color_stop_rgba(0.0, hi[0], hi[1], hi[2], 1.0);
    g.add_color_stop_rgba(1.0, lo[0], lo[1], lo[2], 1.0);
    mgraphics.set_source(g);
    mgraphics.arc(cx, cy, R, 0, Math.PI * 2);
    mgraphics.fill();
}

// 6. Glowing value arc / meter: a WIDE underlay arc in clr@bloom (the bloom) then
// the crisp arc in clr@1.0 — exactly what custom_knob_js inlines for its value
// arc, extracted so any control gets a glowing arc.
function ds_glow_arc(cx, cy, r, a0, a1, clr, lw, bloom) {
    var bl = (bloom === undefined) ? 0.22 : bloom;
    mgraphics.set_source_rgba(clr[0], clr[1], clr[2], bl);
    mgraphics.set_line_width(lw + 3);
    mgraphics.arc(cx, cy, r, a0, a1);
    mgraphics.stroke();
    mgraphics.set_source_rgba(clr[0], clr[1], clr[2], 1.0);
    mgraphics.set_line_width(lw);
    mgraphics.arc(cx, cy, r, a0, a1);
    mgraphics.stroke();
}

// 7. Subtle noise texture: n short 1px strokes at deterministic pseudo-random
// positions (a tiny LCG seeded by seed so it is STABLE across redraws, not
// flickering) in white@alpha. COST: keep n small (<=200) and use ONLY on rarely
// repainted backgrounds (no layer caching in mgraphics) — never on animated
// controls/meters.
function ds_noise_overlay(x, y, w, h, n, alpha, seed) {
    var a = (alpha === undefined) ? 0.02 : alpha;
    var st = (seed === undefined) ? 1 : (seed | 0);
    if (st <= 0) st = 1;
    var cnt = n > 200 ? 200 : n;
    mgraphics.set_source_rgba(1.0, 1.0, 1.0, a);
    mgraphics.set_line_width(1.0);
    var i, px, py;
    for (i = 0; i < cnt; i++) {
        st = (st * 1103515245 + 12345) & 0x7fffffff;     // LCG (deterministic)
        px = x + (st % 10000) / 10000.0 * w;
        st = (st * 1103515245 + 12345) & 0x7fffffff;
        py = y + (st % 10000) / 10000.0 * h;
        mgraphics.move_to(px, py);
        mgraphics.line_to(px + 1.0, py);
        mgraphics.stroke();
    }
}

// 8. Gradient-filled curve band: fill the region under a curve with a vertical
// linear gradient (top color -> transparent bottom) — the premium-EQ filled-band
// look. closed_path_fn(ctx) must lay down a CLOSED path (move_to + line_to/curve_to
// + close_path); ctx is mgraphics so callers can build the path inline. c_top is
// [r,g,b,a], the gradient fades to alpha 0 at y1.
function ds_gradient_fill_path(closed_path_fn, x0, y0, x1, y1, c_top) {
    var g = mgraphics.pattern_create_linear(x0, y0, x1, y1);
    g.add_color_stop_rgba(0.0, c_top[0], c_top[1], c_top[2], c_top[3]);
    g.add_color_stop_rgba(1.0, c_top[0], c_top[1], c_top[2], 0.0);
    mgraphics.set_source(g);
    closed_path_fn(mgraphics);
    mgraphics.fill();
}
"""


def ds_helpers_js():
    """Return the eight ``ds_*`` helpers to APPEND to ``DESIGN_SYSTEM_JS``.

    The lead folds this into ``design_system.DESIGN_SYSTEM_JS`` (so every control
    that prepends ``design_system_js()`` can call them) and bumps
    ``DESIGN_SYSTEM_VERSION`` 1->2. Standalone here only so it ships + tests as a
    unit before the merge.
    """
    return DS_HELPERS_JS


# ── Showcase: a glass/metal full-device background (v8ui) ────────────────────
def glass_panel_bg_js(
    *,
    lo="0.050, 0.052, 0.060, 1.0",
    hi="0.100, 0.108, 0.124, 1.0",
    border="0.22, 0.24, 0.28, 0.9",
    rim="1.0, 1.0, 1.0",
    radius=8.0,
    inset=4.0,
    noise=True,
    noise_count=180,
    noise_seed=12345,
) -> str:
    """A full-device v8ui background: a frosted-glass plate with depth.

    Showcases the premium drawing techniques on a STATIC background (the only safe
    home for the noise overlay — it repaints every paint with no layer caching).
    Draws ``ds_glass_panel`` (gradient body + top sheen + rim), then a faked
    ``ds_inner_shadow`` (depth without a box-gradient), an optional deterministic
    ``ds_noise_overlay`` (stable across redraws via a seeded LCG, so it reads as
    texture not flicker), then the panel border + a brighter ``ds_rim_light`` on
    top. Mirrors ``panel_bg_js``: prepends ``design_system_js()``, self-paints its
    own gradient (never relies on transparency), 1 inlet / 0 outlets, no pointer.

    ``lo``/``hi``/``border``/``rim`` are ``"r, g, b[, a]"`` strings (feed them from
    ``theme.panel_bg_kwargs()`` so the material matches the palette). ``noise``
    toggles the texture; ``noise_count`` (<=200) and ``noise_seed`` keep it cheap
    and stable.
    """
    return (
        design_system_js() + "\n" + DS_HELPERS_JS + "\n"
        "mgraphics.init();\n"
        "mgraphics.relative_coords = 0;\n"
        "mgraphics.autofill = 0;\n"
        "inlets = 1;\n"
        "outlets = 0;\n"
        f"var LO = [{lo}];\n"
        f"var HI = [{hi}];\n"
        f"var BORDER = [{border}];\n"
        f"var RIM = [{rim}];\n"
        f"var RADIUS = {float(radius)};\n"
        f"var INSET = {float(inset)};\n"
        f"var NOISE = {1 if noise else 0};\n"
        f"var NOISE_N = {int(noise_count)};\n"
        f"var NOISE_SEED = {int(noise_seed)};\n"
        "function paint() {\n"
        "    var w = mgraphics.size[0];\n"
        "    var h = mgraphics.size[1];\n"
        "    var x = INSET, y = INSET, pw = w - 2 * INSET, ph = h - 2 * INSET;\n"
        "    ds_glass_panel(x, y, pw, ph, RADIUS, LO, HI);\n"
        "    ds_inner_shadow(x, y, pw, ph, RADIUS, 1.0);\n"
        "    if (NOISE) { ds_noise_overlay(x, y, pw, ph, NOISE_N, 0.02, NOISE_SEED); }\n"
        "    mgraphics.set_source_rgba(BORDER[0], BORDER[1], BORDER[2], BORDER.length > 3 ? BORDER[3] : 1.0);\n"
        "    mgraphics.set_line_width(1.0);\n"
        "    mgraphics.rectangle_rounded(x + 0.5, y + 0.5, pw - 1, ph - 1, RADIUS, RADIUS);\n"
        "    mgraphics.stroke();\n"
        "    ds_rim_light(x, y, pw, ph, RADIUS, RIM, 0.12);\n"
        "}\n"
        "function bang() { mgraphics.redraw(); }\n"
    )
