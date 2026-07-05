"""ui_interaction — the four UXI foundation mixins (T27, ux_innovation_plan).

JS snippet factories a v8ui/jsui engine prepends (like ``design_system_js``):

* :func:`draggable_node_js` — hit-test, drag state machine, normalized
  coordinate transforms, clamp, and outlet dedup (the shared substrate the
  three shipped editors each hand-rolled).
* :func:`tooltip_js` — edge-aware rounded hover/drag tooltip with a
  primary + secondary line and an accent border.
* :func:`edit_overlay_js` — double-click detection + a type-in numeric
  overlay (blinking cursor, parse → clamp → commit on Enter, Esc cancels).
* :func:`modifier_drag_js` — Shift fine-drag (0.15×), Cmd axis-lock, and
  arrow-key nudge deltas with a focus ring.

Everything is ES5 (runs in BOTH jsui and v8ui). State lives in ``dn_``/
``tt_``/``eo_``/``md_``-prefixed globals so mixins co-exist in one script.

LIVE KEYBOARD CONSTRAINT (Live-verified, T27): inside a LIVE DEVICE the
host owns the keyboard — a v8ui/jsui ``onkey`` never fires (it works in
the Max editor only). So in Live: the ``eo_*`` overlay's typing path and
``md_nudge`` arrow keys need a NATIVE text host — pair the overlay visual
with a real ``textedit``/``live.numbox`` revealed at the node (native
controls DO receive keys when clicked), or rely on the device's numbox
params for type-in. The mouse-side mixins (drag, tooltip, Shift fine-drag,
double-click detection, overlay VISUAL + parse/clamp/commit logic) are
fully Live-functional.
"""

DRAGGABLE_NODE_JS = r"""
// ── draggable_node mixin (T27 F1) ────────────────────────────────────────
var dn_drag_idx = -1;          // node being dragged (-1 = idle)
var dn_emit_cache = {};        // outlet dedup: last value per key

function dn_hit_test(px, py, xs, ys, n, radius) {
    // nearest node within radius; -1 if none. Screen coords.
    var best = -1, bestd = radius * radius;
    for (var i = 0; i < n; i++) {
        var dx = px - xs[i], dy = py - ys[i];
        var d = dx * dx + dy * dy;
        if (d <= bestd) { bestd = d; best = i; }
    }
    return best;
}

function dn_clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

function dn_norm_to_x(v, x0, w) { return x0 + dn_clamp(v, 0, 1) * w; }
function dn_x_to_norm(x, x0, w) { return dn_clamp((x - x0) / w, 0, 1); }
function dn_norm_to_y(v, y0, h) { return y0 + (1 - dn_clamp(v, 0, 1)) * h; }
function dn_y_to_norm(y, y0, h) { return dn_clamp(1 - (y - y0) / h, 0, 1); }

function dn_emit(key, value) {
    // outlet only on change (dedup) — callers route through this.
    if (dn_emit_cache[key] === value) return 0;
    dn_emit_cache[key] = value;
    outlet(0, [key, value]);
    return 1;
}
"""

TOOLTIP_JS = r"""
// ── tooltip mixin (T27 F2) ───────────────────────────────────────────────
var tt_active = 0;
var tt_x = 0, tt_y = 0;
var tt_primary = "", tt_secondary = "";

function tt_show(x, y, primary, secondary) {
    tt_active = 1; tt_x = x; tt_y = y;
    tt_primary = "" + primary;
    tt_secondary = secondary ? "" + secondary : "";
}

function tt_hide() { tt_active = 0; }

function tt_draw(accent) {
    if (!tt_active) return;
    var w = mgraphics.size[0], h = mgraphics.size[1];
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(9.0);
    var tw1 = mgraphics.text_measure(tt_primary)[0];
    var tw2 = 0;
    if (tt_secondary.length) {
        mgraphics.set_font_size(7.5);
        tw2 = mgraphics.text_measure(tt_secondary)[0];
    }
    var bw = Math.max(tw1, tw2) + 12;
    var bh = tt_secondary.length ? 26 : 16;
    // edge-aware: flip left of the cursor at the right edge, above at bottom
    var bx = tt_x + 10; if (bx + bw > w - 2) bx = tt_x - bw - 10;
    var by = tt_y - bh - 6; if (by < 2) by = tt_y + 12;
    if (bx < 2) bx = 2;
    mgraphics.set_source_rgba(0.07, 0.075, 0.085, 0.96);
    mgraphics.rectangle_rounded(bx, by, bw, bh, 3, 3);
    mgraphics.fill();
    mgraphics.set_source_rgba(accent[0], accent[1], accent[2], 0.9);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle_rounded(bx, by, bw, bh, 3, 3);
    mgraphics.stroke();
    mgraphics.set_source_rgba(0.93, 0.95, 0.98, 1.0);
    mgraphics.set_font_size(9.0);
    mgraphics.move_to(bx + 6, by + 11);
    mgraphics.show_text(tt_primary);
    if (tt_secondary.length) {
        mgraphics.set_source_rgba(0.63, 0.64, 0.66, 1.0);
        mgraphics.set_font_size(7.5);
        mgraphics.move_to(bx + 6, by + 21);
        mgraphics.show_text(tt_secondary);
    }
}

function tt_place(x, y, bw, bh, w, h) {
    // pure placement math (node-testable): returns [bx, by]
    var bx = x + 10; if (bx + bw > w - 2) bx = x - bw - 10;
    var by = y - bh - 6; if (by < 2) by = y + 12;
    if (bx < 2) bx = 2;
    return [bx, by];
}
"""

EDIT_OVERLAY_JS = r"""
// ── value-entry overlay mixin (T27 F3) ───────────────────────────────────
var eo_active = 0;
var eo_x = 0, eo_y = 0;
var eo_buf = "";
var eo_key = "";
var eo_lo = 0, eo_hi = 1;
var eo_frame = 0;
var eo_last_click_ms = -100000;

function eo_is_dblclick(now_ms) {
    var hit = (now_ms - eo_last_click_ms) < 350;
    eo_last_click_ms = now_ms;
    return hit ? 1 : 0;
}

function eo_open(x, y, initial, key, lo, hi) {
    eo_active = 1; eo_x = x; eo_y = y;
    eo_buf = "" + initial; eo_key = key;
    eo_lo = lo; eo_hi = hi;
}

function eo_cancel() { eo_active = 0; eo_buf = ""; }

function eo_commit() {
    if (!eo_active) return null;
    var v = parseFloat(eo_buf);
    eo_active = 0;
    if (isNaN(v)) return null;
    if (v < eo_lo) v = eo_lo;
    if (v > eo_hi) v = eo_hi;
    return v;
}

function eo_keychar(c) {
    // buffer digits / dot / minus; backspace = 8; ignore the rest.
    if (!eo_active) return;
    if (c === 8) { eo_buf = eo_buf.slice(0, -1); return; }
    var ch = String.fromCharCode(c);
    if ((ch >= "0" && ch <= "9") || ch === "." || ch === "-") eo_buf += ch;
}

function eo_draw(accent) {
    if (!eo_active) return;
    eo_frame++;
    var bw = Math.max(44, eo_buf.length * 7 + 16), bh = 16;
    mgraphics.set_source_rgba(0.05, 0.055, 0.06, 0.98);
    mgraphics.rectangle_rounded(eo_x, eo_y, bw, bh, 3, 3);
    mgraphics.fill();
    mgraphics.set_source_rgba(accent[0], accent[1], accent[2], 1.0);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle_rounded(eo_x, eo_y, bw, bh, 3, 3);
    mgraphics.stroke();
    mgraphics.set_source_rgba(0.93, 0.95, 0.98, 1.0);
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(9.0);
    mgraphics.move_to(eo_x + 6, eo_y + 11);
    mgraphics.show_text(eo_buf);
    if ((eo_frame >> 4) & 1) {   // blinking cursor
        var cx = eo_x + 8 + eo_buf.length * 6;
        mgraphics.move_to(cx, eo_y + 3);
        mgraphics.line_to(cx, eo_y + bh - 3);
        mgraphics.stroke();
    }
}
"""

MODIFIER_DRAG_JS = r"""
// ── modifier + keyboard layer (T27 F4) ───────────────────────────────────
var md_focus = -1;             // keyboard-focused node (-1 = none)

function md_apply_drag(v_new, v_prev, shift) {
    // Shift = fine: move 15% of the way toward the pointer value.
    if (shift) return v_prev + (v_new - v_prev) * 0.15;
    return v_new;
}

function md_axis_lock(dx, dy) {
    // Cmd axis-lock: 0 = horizontal wins, 1 = vertical wins.
    return Math.abs(dy) > Math.abs(dx) ? 1 : 0;
}

function md_nudge(keycode, shift, step) {
    // arrow keys -> +/- step (Shift = 10x). Max keycodes: left 30, right 31,
    // up 30?? — hosts differ, so callers pass the DECODED direction:
    // keycode here is -1 (down/left) or +1 (up/right).
    var d = keycode * step;
    return shift ? d * 10 : d;
}

function md_draw_focus_ring(x, y, r, accent) {
    mgraphics.set_source_rgba(accent[0], accent[1], accent[2], 0.85);
    mgraphics.set_line_width(1.4);
    mgraphics.arc(x, y, r + 3, 0, Math.PI * 2);
    mgraphics.stroke();
}
"""


def draggable_node_js() -> str:
    """The draggable-node substrate (hit-test / drag state / transforms /
    clamp / outlet dedup)."""
    return DRAGGABLE_NODE_JS


def tooltip_js() -> str:
    """Edge-aware hover/drag tooltip (primary + secondary line)."""
    return TOOLTIP_JS


def edit_overlay_js() -> str:
    """Double-click detect + type-in numeric overlay."""
    return EDIT_OVERLAY_JS


def modifier_drag_js() -> str:
    """Shift fine-drag, Cmd axis-lock, arrow nudge + focus ring."""
    return MODIFIER_DRAG_JS


def ui_interaction_js() -> str:
    """All four foundation mixins, in dependency order."""
    return (DRAGGABLE_NODE_JS + TOOLTIP_JS + EDIT_OVERLAY_JS
            + MODIFIER_DRAG_JS)
