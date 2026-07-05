"""Hand-drawn v8ui glyph library — the TapeLeap/Rupture icon vocabulary.

A bank of small vector glyphs (wave shapes, filter responses, transport, utility)
drawn with mgraphics, plus a ``draw_glyph(name, cx, cy, s)`` dispatcher so a
control can render an icon by name. Each glyph draws in the CURRENT source color
(the caller sets color + alpha first) and centres itself in a ``2*s`` box.

Prepend :func:`ui_icons_js` to any v8ui that wants glyphs (e.g. the mode-glyph
selector). ES5-safe (works in both jsui and v8ui).
"""

ICON_NAMES = [
    "sine", "saw", "square", "triangle", "noise", "fold",
    "lowpass", "highpass", "bandpass", "notch",
    "power", "play", "pause", "loop", "bypass", "bell",
    "expand", "collapse",
    # dnksaus micro-language (catalog #63): dice=randomize, replay=re-roll,
    # clear=unmap/delete, hamburger=options popover, headphone=listen
    "dice", "replay", "clear", "hamburger", "headphone",
]

_ICONS_JS = r"""
// ── glyph bank: each draws in the current source color, centred in a 2*s box ──
function _ico_lw(s) { return Math.max(1.0, s * 0.20); }

function draw_icon_sine(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var n = 24, a = s * 0.62;
    mgraphics.move_to(cx - s, cy);
    for (var i = 1; i <= n; i++) {
        var t = i / n;
        mgraphics.line_to(cx - s + 2 * s * t, cy - Math.sin(t * Math.PI * 2) * a);
    }
    mgraphics.stroke();
}
function draw_icon_saw(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var a = s * 0.6;
    mgraphics.move_to(cx - s, cy + a);
    mgraphics.line_to(cx, cy - a);
    mgraphics.line_to(cx, cy + a);
    mgraphics.line_to(cx + s, cy - a);
    mgraphics.stroke();
}
function draw_icon_square(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var a = s * 0.6;
    mgraphics.move_to(cx - s, cy + a);
    mgraphics.line_to(cx - s, cy - a);
    mgraphics.line_to(cx, cy - a);
    mgraphics.line_to(cx, cy + a);
    mgraphics.line_to(cx + s, cy + a);
    mgraphics.line_to(cx + s, cy - a);
    mgraphics.stroke();
}
function draw_icon_triangle(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var a = s * 0.6;
    mgraphics.move_to(cx - s, cy + a);
    mgraphics.line_to(cx - s * 0.5, cy - a);
    mgraphics.line_to(cx + s * 0.5, cy + a);
    mgraphics.line_to(cx + s, cy - a);
    mgraphics.stroke();
}
function draw_icon_noise(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var ys = [0.2, -0.6, 0.5, -0.3, 0.7, -0.5, 0.3, -0.7, 0.4];
    mgraphics.move_to(cx - s, cy + ys[0] * s);
    for (var i = 1; i < ys.length; i++) {
        mgraphics.line_to(cx - s + (2 * s) * (i / (ys.length - 1)), cy + ys[i] * s);
    }
    mgraphics.stroke();
}
function draw_icon_fold(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var n = 24, a = s * 0.6;
    mgraphics.move_to(cx - s, cy);
    for (var i = 1; i <= n; i++) {
        var t = i / n;
        var v = Math.sin(t * Math.PI * 2) * 1.7;
        if (v > 1) v = 2 - v; if (v < -1) v = -2 - v;
        mgraphics.line_to(cx - s + 2 * s * t, cy - v * a);
    }
    mgraphics.stroke();
}
function _ico_curve(cx, cy, s, pts) {
    mgraphics.set_line_width(_ico_lw(s));
    mgraphics.move_to(cx - s, cy - pts[0] * s);
    for (var i = 1; i < pts.length; i++) {
        mgraphics.line_to(cx - s + (2 * s) * (i / (pts.length - 1)), cy - pts[i] * s);
    }
    mgraphics.stroke();
}
function draw_icon_lowpass(cx, cy, s) { _ico_curve(cx, cy, s, [0.5, 0.5, 0.45, 0.1, -0.5, -0.6]); }
function draw_icon_highpass(cx, cy, s) { _ico_curve(cx, cy, s, [-0.6, -0.5, 0.1, 0.45, 0.5, 0.5]); }
function draw_icon_bandpass(cx, cy, s) { _ico_curve(cx, cy, s, [-0.5, -0.2, 0.6, 0.6, -0.2, -0.5]); }
function draw_icon_bell(cx, cy, s) { _ico_curve(cx, cy, s, [-0.1, 0.0, 0.5, 0.5, 0.0, -0.1]); }
function draw_icon_notch(cx, cy, s) { _ico_curve(cx, cy, s, [0.5, 0.2, -0.6, -0.6, 0.2, 0.5]); }
function draw_icon_power(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    mgraphics.arc(cx, cy, s * 0.62, -Math.PI * 0.35, Math.PI * 1.35);
    mgraphics.stroke();
    mgraphics.move_to(cx, cy - s * 0.7); mgraphics.line_to(cx, cy - s * 0.05); mgraphics.stroke();
}
function draw_icon_play(cx, cy, s) {
    mgraphics.move_to(cx - s * 0.5, cy - s * 0.6);
    mgraphics.line_to(cx + s * 0.62, cy);
    mgraphics.line_to(cx - s * 0.5, cy + s * 0.6);
    mgraphics.close_path(); mgraphics.fill();
}
function draw_icon_pause(cx, cy, s) {
    var bw = s * 0.32;
    mgraphics.rectangle(cx - s * 0.5, cy - s * 0.6, bw, s * 1.2);
    mgraphics.rectangle(cx + s * 0.18, cy - s * 0.6, bw, s * 1.2);
    mgraphics.fill();
}
function draw_icon_loop(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    mgraphics.arc(cx, cy, s * 0.62, -Math.PI * 0.5, Math.PI * 0.9); mgraphics.stroke();
    mgraphics.move_to(cx + s * 0.34, cy - s * 0.78);
    mgraphics.line_to(cx + s * 0.0, cy - s * 0.62);
    mgraphics.line_to(cx + s * 0.34, cy - s * 0.36);
    mgraphics.stroke();
}
function draw_icon_bypass(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    mgraphics.arc(cx, cy, s * 0.62, 0, Math.PI * 2); mgraphics.stroke();
    mgraphics.move_to(cx - s * 0.44, cy + s * 0.44);
    mgraphics.line_to(cx + s * 0.44, cy - s * 0.44); mgraphics.stroke();
}
function _ico_bracket(cx, cy, dx, dy, s) {
    // one L-bracket at corner direction (dx,dy in {-1,1}); arms point inward.
    var a = s * 0.9, arm = s * 0.55;
    mgraphics.move_to(cx + dx * (a - arm), cy + dy * a);
    mgraphics.line_to(cx + dx * a, cy + dy * a);
    mgraphics.line_to(cx + dx * a, cy + dy * (a - arm));
    mgraphics.stroke();
}
function draw_icon_expand(cx, cy, s) {
    // fullscreen: four outward corner brackets
    mgraphics.set_line_width(_ico_lw(s));
    _ico_bracket(cx, cy, -1, -1, s); _ico_bracket(cx, cy, 1, -1, s);
    _ico_bracket(cx, cy, -1, 1, s);  _ico_bracket(cx, cy, 1, 1, s);
}
function draw_icon_collapse(cx, cy, s) {
    // exit-fullscreen / shrink: a solid small pane docked bottom-left of a frame
    mgraphics.set_line_width(_ico_lw(s));
    var a = s * 0.9;
    mgraphics.rectangle(cx - a, cy - a, 2 * a, 2 * a);
    mgraphics.stroke();
    mgraphics.rectangle(cx - a, cy - s * 0.1, a * 1.0, a * 1.1);
    mgraphics.fill();
}
function draw_icon_dice(cx, cy, s) {
    var a = s * 0.85, r = Math.max(0.8, s * 0.16);
    mgraphics.set_line_width(_ico_lw(s) * 0.8);
    mgraphics.rectangle(cx - a, cy - a, 2 * a, 2 * a);
    mgraphics.stroke();
    var d = a * 0.45;
    var pips = [[-d, -d], [d, -d], [0, 0], [-d, d], [d, d]];
    for (var i = 0; i < pips.length; i++) {
        mgraphics.arc(cx + pips[i][0], cy + pips[i][1], r, 0, Math.PI * 2);
        mgraphics.fill();
    }
}
function draw_icon_replay(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var r = s * 0.7;
    mgraphics.arc(cx, cy, r, -Math.PI * 0.35, Math.PI * 1.15);
    mgraphics.stroke();
    var ax = cx + r * Math.cos(-Math.PI * 0.35);
    var ay = cy + r * Math.sin(-Math.PI * 0.35);
    mgraphics.move_to(ax - s * 0.28, ay - s * 0.30);
    mgraphics.line_to(ax + s * 0.24, ay - s * 0.02);
    mgraphics.line_to(ax - s * 0.30, ay + s * 0.26);
    mgraphics.close_path();
    mgraphics.fill();
}
function draw_icon_clear(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var a = s * 0.55;
    mgraphics.move_to(cx - a, cy - a);
    mgraphics.line_to(cx + a, cy + a);
    mgraphics.move_to(cx + a, cy - a);
    mgraphics.line_to(cx - a, cy + a);
    mgraphics.stroke();
}
function draw_icon_hamburger(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var a = s * 0.75, g = s * 0.5;
    for (var i = -1; i <= 1; i++) {
        mgraphics.move_to(cx - a, cy + i * g);
        mgraphics.line_to(cx + a, cy + i * g);
    }
    mgraphics.stroke();
}
function draw_icon_headphone(cx, cy, s) {
    mgraphics.set_line_width(_ico_lw(s));
    var r = s * 0.72;
    mgraphics.arc(cx, cy + s * 0.1, r, Math.PI, Math.PI * 2);
    mgraphics.stroke();
    var pw = s * 0.30, ph = s * 0.55;
    mgraphics.rectangle(cx - r - pw * 0.4, cy + s * 0.1, pw, ph);
    mgraphics.fill();
    mgraphics.rectangle(cx + r - pw * 0.6, cy + s * 0.1, pw, ph);
    mgraphics.fill();
}
function draw_glyph(name, cx, cy, s) {
    switch (name) {
        case 'sine': return draw_icon_sine(cx, cy, s);
        case 'saw': return draw_icon_saw(cx, cy, s);
        case 'square': return draw_icon_square(cx, cy, s);
        case 'triangle': return draw_icon_triangle(cx, cy, s);
        case 'noise': return draw_icon_noise(cx, cy, s);
        case 'fold': return draw_icon_fold(cx, cy, s);
        case 'lowpass': return draw_icon_lowpass(cx, cy, s);
        case 'highpass': return draw_icon_highpass(cx, cy, s);
        case 'bandpass': return draw_icon_bandpass(cx, cy, s);
        case 'bell': return draw_icon_bell(cx, cy, s);
        case 'notch': return draw_icon_notch(cx, cy, s);
        case 'power': return draw_icon_power(cx, cy, s);
        case 'play': return draw_icon_play(cx, cy, s);
        case 'pause': return draw_icon_pause(cx, cy, s);
        case 'loop': return draw_icon_loop(cx, cy, s);
        case 'bypass': return draw_icon_bypass(cx, cy, s);
        case 'expand': return draw_icon_expand(cx, cy, s);
        case 'collapse': return draw_icon_collapse(cx, cy, s);
        case 'dice': return draw_icon_dice(cx, cy, s);
        case 'replay': return draw_icon_replay(cx, cy, s);
        case 'clear': return draw_icon_clear(cx, cy, s);
        case 'hamburger': return draw_icon_hamburger(cx, cy, s);
        case 'headphone': return draw_icon_headphone(cx, cy, s);
        default: return draw_icon_bypass(cx, cy, s);
    }
}
"""


def ui_icons_js() -> str:
    """Return the glyph-bank JS snippet to prepend to a v8ui that draws icons."""
    return _ICONS_JS
