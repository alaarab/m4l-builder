"""Shared design-system for the jsui/v8ui display engines.

One place for the reusable MGraphics drawing helpers + cursor handling that the
hero displays embed, so the suite shares a single "expensive" look and a change
lands once. Engines inject ``design_system_js()`` at the top of their generated
JS (prepended outside string.Template so a stray ``$`` is never re-parsed) and
call the namespaced ``ds_*`` helpers.

Pure ES5 (var/function only — no arrows/backticks/let/const) so it passes the
jsui contract checker and runs under the Node behaviour harness. Every Max-global
call (e.g. ``setcursor``) stays wrapped in try/catch so it can't throw under Node
or wedge a handler in a runtime that lacks it.

Cache note: Max caches .js sidecars by filename for the whole Live session, so a
change to ``DESIGN_SYSTEM_JS`` must bump ``DESIGN_SYSTEM_VERSION`` AND propagate a
fresh sidecar filename for every embedding device (the products version their JS
filenames; bump them when the embedded design-system version changes).
"""

import hashlib

# Bump whenever DESIGN_SYSTEM_JS changes; products fold version_tag() awareness
# into their versioned JS filenames so Max reloads the new snippet everywhere.
DESIGN_SYSTEM_VERSION = 1


def version_tag():
    """Short token (e.g. ``"ds1"``) for folding into sidecar filenames."""
    return "ds" + str(DESIGN_SYSTEM_VERSION)


def js_sidecar_name(filename, js_code, *, hash_len=8):
    """Content-address a v8ui/jsui sidecar filename: ``{stem}_{hash}.js``.

    Max caches a ``.js``/``v8ui`` sidecar BY NAME for the WHOLE Live session, so
    editing the JS without renaming the file serves the STALE cached snippet — the
    fix is dead-on-arrival (a real bug: the v8ui-drag fix never took until the
    filenames were hand-bumped). Folding a hash of ``js_code`` into the name makes
    ANY edit auto-rename → Max reloads fresh, with ZERO manual ``_vN`` bumps. The
    stem stays a stable, human-readable label; only the appended hash moves. Mirror
    of the gen~ side's :func:`m4l_builder.gen_patcher.gendsp_support_name`.
    """
    stem = filename[:-3] if filename.endswith(".js") else filename
    digest = hashlib.blake2b(
        js_code.encode("utf-8"), digest_size=(hash_len + 1) // 2
    ).hexdigest()
    return f"{stem}_{digest[:hash_len]}.js"


# ── The shared ES5 snippet ────────────────────────────────────────────────
# Namespaced ds_*/DS_* symbols so an engine can adopt it without renaming its
# own locals. Transplanted verbatim from the previously-duplicated copies in
# eq_curve.py / linear_phase_eq_display.py (byte-identical behaviour).
DESIGN_SYSTEM_JS = """\
// ── design-system (shared) ───────────────────────────────────────────────
// Mouse-cursor feedback (pro-plugin-style): a pointing hand over a grabbable
// node, a grab/closed hand while dragging, a crosshair over the open plot.
// Values are Max's t_jmouse_cursortype enum (jsui/v8ui setcursor). ds_cur_cursor
// guards so setcursor only fires on a transition (never per frame), and the
// call is wrapped so a runtime that lacks it can't wedge the hover handler.
var DS_CUR_ARROW = 1, DS_CUR_CROSS = 4, DS_CUR_HAND = 6, DS_CUR_GRAB = 7;
var ds_cur_cursor = -1;
function ds_set_cursor(c) {
    if (c === ds_cur_cursor) return;
    ds_cur_cursor = c;
    try { setcursor(c); } catch (e) {}
}

// Soft radial-gradient halo behind a node (a premium-EQ "lit node" look). Bright color
// at the center fading to transparent at the rim — one pattern fill.
function ds_node_glow(x, y, clr, radius, inner_alpha) {
    var g = mgraphics.pattern_create_radial(x, y, 0.0, x, y, radius);
    g.add_color_stop_rgba(0.0, clr[0], clr[1], clr[2], inner_alpha);
    g.add_color_stop_rgba(1.0, clr[0], clr[1], clr[2], 0.0);
    mgraphics.set_source(g);
    mgraphics.arc(x, y, radius, 0, Math.PI * 2);
    mgraphics.fill();
}

// Soft drop shadow: a radial glow in clr offset down by dy, behind an element
// of half-size radius. Cheap depth (NanoVG-style fake shadow).
function ds_drop_shadow(x, y, radius, dy, clr, alpha) {
    ds_node_glow(x, y + dy, clr, radius, alpha);
}
"""


def design_system_js():
    """Return the shared ES5 snippet to prepend to an engine's generated JS."""
    return DESIGN_SYSTEM_JS
