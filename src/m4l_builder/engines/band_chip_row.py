"""Shared band-chip-row jsui — a Pro-Q-style band overview strip used by
BOTH flagship EQs (Linear Phase + Parametric). Click a chip to select a
band, opt-click to disable, shift/ctrl-click to solo; fed set_num_bands /
set_band_state / set_selected, emits select_band / toggle_band_enable /
toggle_band_solo. Generic over any 8-band EQ; the host wires the feed."""

__all__ = ["band_chip_row_js"]


def band_chip_row_js() -> str:
    """Return jsui code for the band chip row."""
    return """\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

var num_bands = 8;
var selected = -1;
var present = [0, 0, 0, 0, 0, 0, 0, 0];
var enabled = [0, 0, 0, 0, 0, 0, 0, 0];
var solo = [0, 0, 0, 0, 0, 0, 0, 0];
var colors = [
    [0.92, 0.36, 0.34, 1.0],
    [0.94, 0.62, 0.24, 1.0],
    [0.88, 0.84, 0.28, 1.0],
    [0.36, 0.80, 0.46, 1.0],
    [0.26, 0.84, 0.92, 1.0],
    [0.38, 0.56, 0.92, 1.0],
    [0.66, 0.46, 0.88, 1.0],
    [0.90, 0.42, 0.66, 1.0]
];

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function chip_layout() {
    var w = mgraphics.size[0];
    var h = mgraphics.size[1];
    var compact = h <= 24 ? 1 : 0;
    var gap = compact ? 2 : 6;
    var inset_y = compact ? 3 : 5;
    var chip_h = compact ? h - 6 : h - 10;
    var chip_w = Math.floor((w - gap * (num_bands + 1)) / num_bands);
    var rects = [];
    var x = gap;
    var i;
    for (i = 0; i < num_bands; i++) {
        rects.push([x, inset_y, chip_w, chip_h]);
        x += chip_w + gap;
    }
    return rects;
}

function set_num_bands(v) {
    num_bands = clamp(Math.floor(v), 1, 8);
    mgraphics.redraw();
}

function set_band_state(idx, a, b, c) {
    idx = Math.floor(idx);
    if (idx < 0 || idx >= 8) return;
    if (c === undefined) {
        present[idx] = a ? 1 : 0;
        enabled[idx] = a ? 1 : 0;
        solo[idx] = b ? 1 : 0;
    } else {
        present[idx] = a ? 1 : 0;
        enabled[idx] = b ? 1 : 0;
        solo[idx] = c ? 1 : 0;
    }
    mgraphics.redraw();
}

function set_selected(idx) {
    idx = Math.floor(idx);
    selected = idx;
    mgraphics.redraw();
}

function paint() {
    var rects = chip_layout();
    var compact = mgraphics.size[1] <= 24 ? 1 : 0;
    var i, r, fill_alpha, border_alpha, color, label, label_x;
    var shell_alpha, shell_radius;

    mgraphics.set_source_rgba(0.06, 0.08, 0.11, 1.0);
    mgraphics.rectangle_rounded(0, 0, mgraphics.size[0], mgraphics.size[1], 6, 6);
    mgraphics.fill();

    for (i = 0; i < num_bands; i++) {
        r = rects[i];
        color = colors[i];
        fill_alpha = !present[i] ? (selected === i ? 0.12 : 0.02) : (selected === i ? 0.96 : (enabled[i] ? 0.24 : 0.08));
        border_alpha = !present[i] ? (selected === i ? 0.22 : 0.08) : (enabled[i] ? (selected === i ? 1.0 : 0.86) : (selected === i ? 0.42 : 0.22));
        shell_alpha = selected === i ? 0.34 : (solo[i] ? 0.18 : 0.10);
        shell_radius = compact ? 6 : 7;

        mgraphics.set_source_rgba(0.02, 0.03, 0.05, shell_alpha);
        mgraphics.rectangle_rounded(r[0] - 1, r[1] - 1, r[2] + 2, r[3] + 2, shell_radius, shell_radius);
        mgraphics.fill();

        mgraphics.set_source_rgba(color[0], color[1], color[2], fill_alpha);
        mgraphics.rectangle_rounded(r[0], r[1], r[2], r[3], 5, 5);
        mgraphics.fill_preserve();

        mgraphics.set_source_rgba(color[0], color[1], color[2], border_alpha);
        mgraphics.set_line_width(selected === i ? 2.0 : 1.1);
        mgraphics.stroke();

        mgraphics.select_font_face("Ableton Sans Bold");
        mgraphics.set_font_size(compact ? 7.0 : 8.5);
        mgraphics.set_source_rgba(
            selected === i ? 0.05 : 0.92,
            selected === i ? 0.06 : 0.95,
            selected === i ? 0.08 : 1.0,
            selected === i ? 0.96 : (!present[i] ? 0.14 : (enabled[i] ? 0.78 : 0.28))
        );
        label = compact ? (i + 1).toString() : "B" + (i + 1);
        label_x = compact ? (r[0] + r[2] * 0.5 - (label.length > 1 ? 4 : 2)) : (r[0] + 13);
        mgraphics.move_to(label_x, r[1] + (compact ? 12 : 16));
        mgraphics.show_text(label);

        if (solo[i]) {
            mgraphics.set_source_rgba(1.0, 0.96, 0.74, 0.98);
            mgraphics.rectangle_rounded(
                r[0] + r[2] - (compact ? 16 : 18),
                r[1] + (compact ? 3 : 5),
                compact ? 10 : 12,
                compact ? 5 : 6,
                3,
                3
            );
            mgraphics.fill();
            mgraphics.set_source_rgba(0.18, 0.12, 0.02, 0.96);
            mgraphics.select_font_face("Ableton Sans Bold");
            mgraphics.set_font_size(compact ? 4.8 : 5.4);
            mgraphics.move_to(r[0] + r[2] - (compact ? 13 : 15), r[1] + (compact ? 8 : 10));
            mgraphics.show_text("L");
        }

        if (present[i] && !enabled[i]) {
            mgraphics.set_source_rgba(0.92, 0.96, 1.0, selected === i ? 0.28 : 0.18);
            mgraphics.set_line_width(selected === i ? 1.6 : 1.1);
            mgraphics.move_to(r[0] + 4, r[1] + r[3] - 3);
            mgraphics.line_to(r[0] + r[2] - 4, r[1] + 3);
            mgraphics.stroke();
        }
    }
}

function onclick(x, y, but, cmd, shift, caps, opt, ctrl) {
    var rects = chip_layout();
    var i, r;
    for (i = 0; i < num_bands; i++) {
        r = rects[i];
        if (x >= r[0] && x <= (r[0] + r[2]) && y >= r[1] && y <= (r[1] + r[3])) {
            if (!present[i]) return;
            if (opt) {
                outlet(0, "toggle_band_enable", i);
                return;
            }
            if (shift || ctrl) {
                outlet(0, "toggle_band_solo", i);
                return;
            }
            outlet(0, "select_band", i);
            return;
        }
    }
}
"""
