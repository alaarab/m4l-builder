"""Three-band crossover display for jsui.

Draws a logarithmic low/mid/high band map with movable crossover markers.
This is display-only: send low crossover Hz to inlet 0, high crossover Hz to
inlet 1, and monitor mode (0=sum, 1=low, 2=mid, 3=high) to inlet 2.
"""

from string import Template

CROSSOVER_DISPLAY_INLETS = 3


def crossover_display_js(
    *,
    bg_color="0.05, 0.05, 0.06, 1.0",
    grid_color="0.22, 0.24, 0.28, 0.55",
    text_color="0.62, 0.66, 0.72, 1.0",
    line_color="0.92, 0.95, 0.98, 0.9",
    low_color="0.30, 0.58, 0.88, 0.28",
    mid_color="0.38, 0.78, 0.58, 0.24",
    high_color="0.92, 0.58, 0.28, 0.24",
    accent_color="0.96, 0.84, 0.40, 1.0",
):
    """Return JavaScript for a display-only 3-band crossover view."""
    return _JS_TEMPLATE.substitute(
        bg_color=bg_color,
        grid_color=grid_color,
        text_color=text_color,
        line_color=line_color,
        low_color=low_color,
        mid_color=mid_color,
        high_color=high_color,
        accent_color=accent_color,
    )


_JS_TEMPLATE = Template("""\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 3;
outlets = 0;

var BG_COLOR     = [$bg_color];
var GRID_COLOR   = [$grid_color];
var TEXT_COLOR   = [$text_color];
var LINE_COLOR   = [$line_color];
var LOW_COLOR    = [$low_color];
var MID_COLOR    = [$mid_color];
var HIGH_COLOR   = [$high_color];
var ACCENT_COLOR = [$accent_color];

var MIN_FREQ  = 20.0;
var MAX_FREQ  = 20000.0;
var LOG_MIN   = Math.log(MIN_FREQ);
var LOG_MAX   = Math.log(MAX_FREQ);
var LOG_RANGE = LOG_MAX - LOG_MIN;

var MARGIN_LEFT   = 28;
var MARGIN_RIGHT  = 12;
var MARGIN_TOP    = 12;
var MARGIN_BOTTOM = 20;

var low_xover = 160.0;
var high_xover = 3200.0;
var monitor_mode = 0;

var GRID_FREQS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];

function plot_left()   { return MARGIN_LEFT; }
function plot_right()  { return mgraphics.size[0] - MARGIN_RIGHT; }
function plot_top()    { return MARGIN_TOP; }
function plot_bottom() { return mgraphics.size[1] - MARGIN_BOTTOM; }
function plot_w()      { return plot_right() - plot_left(); }
function plot_h()      { return plot_bottom() - plot_top(); }

function clamp_freqs() {
    if (low_xover < MIN_FREQ) low_xover = MIN_FREQ;
    if (high_xover > MAX_FREQ) high_xover = MAX_FREQ;
    if (low_xover > high_xover * 0.96) low_xover = high_xover * 0.96;
    if (high_xover < low_xover * 1.04) high_xover = low_xover * 1.04;
}

function freq_to_x(freq) {
    var norm = (Math.log(freq) - LOG_MIN) / LOG_RANGE;
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;
    return plot_left() + norm * plot_w();
}

function format_freq(freq) {
    if (freq >= 1000) {
        if (freq >= 10000) {
            return (freq / 1000.0).toFixed(1) + " kHz";
        }
        return (freq / 1000.0).toFixed(2) + " kHz";
    }
    return Math.round(freq) + " Hz";
}

function set_rgba(color) {
    mgraphics.set_source_rgba(color[0], color[1], color[2], color[3]);
}

function draw_background() {
    set_rgba(BG_COLOR);
    mgraphics.rectangle(0, 0, mgraphics.size[0], mgraphics.size[1]);
    mgraphics.fill();
}

function draw_grid() {
    var i;
    var x;
    set_rgba(GRID_COLOR);
    mgraphics.set_line_width(1.0);

    for (i = 0; i < GRID_FREQS.length; i++) {
        x = freq_to_x(GRID_FREQS[i]);
        mgraphics.move_to(x, plot_top());
        mgraphics.line_to(x, plot_bottom());
        mgraphics.stroke();
    }

    mgraphics.move_to(plot_left(), plot_bottom());
    mgraphics.line_to(plot_right(), plot_bottom());
    mgraphics.stroke();

    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(9.0);
    set_rgba(TEXT_COLOR);

    for (i = 0; i < GRID_FREQS.length; i++) {
        x = freq_to_x(GRID_FREQS[i]);
        mgraphics.move_to(x - 12, plot_bottom() + 12);
        if (GRID_FREQS[i] >= 1000) {
            if (GRID_FREQS[i] >= 10000) {
                mgraphics.show_text((GRID_FREQS[i] / 1000.0).toFixed(0) + "k");
            } else {
                mgraphics.show_text((GRID_FREQS[i] / 1000.0).toFixed(1) + "k");
            }
        } else {
            mgraphics.show_text(String(GRID_FREQS[i]));
        }
    }
}

function region_alpha(band_index) {
    if (monitor_mode === 0) return 1.0;
    if (monitor_mode === band_index) return 1.0;
    return 0.32;
}

function draw_regions() {
    var x_low = freq_to_x(low_xover);
    var x_high = freq_to_x(high_xover);
    var top = plot_top();
    var height = plot_h();

    mgraphics.set_source_rgba(
        LOW_COLOR[0], LOW_COLOR[1], LOW_COLOR[2], LOW_COLOR[3] * region_alpha(1)
    );
    mgraphics.rectangle(plot_left(), top, x_low - plot_left(), height);
    mgraphics.fill();

    mgraphics.set_source_rgba(
        MID_COLOR[0], MID_COLOR[1], MID_COLOR[2], MID_COLOR[3] * region_alpha(2)
    );
    mgraphics.rectangle(x_low, top, x_high - x_low, height);
    mgraphics.fill();

    mgraphics.set_source_rgba(
        HIGH_COLOR[0], HIGH_COLOR[1], HIGH_COLOR[2], HIGH_COLOR[3] * region_alpha(3)
    );
    mgraphics.rectangle(x_high, top, plot_right() - x_high, height);
    mgraphics.fill();
}

function draw_band_labels() {
    var x_low = freq_to_x(low_xover);
    var x_high = freq_to_x(high_xover);
    var y = plot_top() + 18;

    mgraphics.select_font_face("Ableton Sans Bold");
    mgraphics.set_font_size(11.0);
    set_rgba([0.92, 0.95, 0.98, 0.92]);

    mgraphics.move_to(plot_left() + 10, y);
    mgraphics.show_text("LOW");

    mgraphics.move_to((x_low + x_high) * 0.5 - 13, y);
    mgraphics.show_text("MID");

    mgraphics.move_to(plot_right() - 40, y);
    mgraphics.show_text("HIGH");
}

function draw_markers() {
    var x_low = freq_to_x(low_xover);
    var x_high = freq_to_x(high_xover);
    var y_top = plot_top();
    var y_bottom = plot_bottom();

    mgraphics.set_line_width(2.0);
    set_rgba(LINE_COLOR);

    mgraphics.move_to(x_low, y_top);
    mgraphics.line_to(x_low, y_bottom);
    mgraphics.stroke();

    mgraphics.move_to(x_high, y_top);
    mgraphics.line_to(x_high, y_bottom);
    mgraphics.stroke();

    mgraphics.set_source_rgba(
        ACCENT_COLOR[0], ACCENT_COLOR[1], ACCENT_COLOR[2], ACCENT_COLOR[3]
    );
    mgraphics.arc(x_low, y_top + 10, 4.5, 0, Math.PI * 2);
    mgraphics.fill();
    mgraphics.arc(x_high, y_top + 10, 4.5, 0, Math.PI * 2);
    mgraphics.fill();

    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(9.5);
    set_rgba([0.95, 0.97, 1.0, 0.92]);
    mgraphics.move_to(x_low + 8, y_top + 14);
    mgraphics.show_text(format_freq(low_xover));
    mgraphics.move_to(x_high + 8, y_top + 28);
    mgraphics.show_text(format_freq(high_xover));
}

function paint() {
    clamp_freqs();
    draw_background();
    draw_regions();
    draw_grid();
    draw_band_labels();
    draw_markers();
}

function msg_float(value) {
    if (inlet === 0) {
        low_xover = value;
    } else if (inlet === 1) {
        high_xover = value;
    } else if (inlet === 2) {
        monitor_mode = Math.round(value);
        if (monitor_mode < 0) monitor_mode = 0;
        if (monitor_mode > 3) monitor_mode = 3;
    }
    clamp_freqs();
    mgraphics.redraw();
}
""")
