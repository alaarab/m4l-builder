"""Step-bar lane editor for jsui (dnksaus-catalog kit engines #7-#8).

The Auto Gate / Trig Rnd step lane, kit-native: N vertical bars in a dark
plot (dnksaus ships this as a raw ``multislider`` -- Auto_Gate's 8-slot rate
lane), with the curve_editor's chrome idiom (same margins, dim grid, footer
value row, drag readout) and the SIGNATURE step-editor gesture set:

    click a bar         -- set it to the clicked value (y -> 0..1)
    drag                -- PAINT: continuously writes values across every bar
                           the pointer crosses (bars skipped between pointer
                           events are filled by linear interpolation, so a
                           fast sweep still writes every bar exactly once)
    Cmd/Alt-click       -- reset the bar under the cursor to ``reset_value``
                           (no paint stroke starts; a plain click does)
    (no double-click semantics)

Engine #8 (the value-linked step chip) lives here as DISPLAY state: when
``set_link 1`` arrives, a small chain-link glyph is drawn top-left and the
lane is tinted with the accent wash. The engine only displays the link
state -- the WRAPPER (``Device.add_step_bars``) owns the semantic by wiring
a native LINK param to this message.

Inlet (1) -- messages only (never re-emit; the state-restoring ones are
ignored mid-drag so a restore cascade can never fight a live gesture):
    set_steps n           -- active step count (2..max_steps): re-quantizes
                             the display and PRESERVES every slot value
                             (bars beyond the count keep their values and
                             come back when the count grows)
    set_values v0 v1 ...  -- restore/back-sync bar values (clamped 0..1,
                             up to max_steps slots); the count is unchanged
    set_all n v0 v1 ...   -- wrapper-internal restore (count-first fixed
                             slot layout fed by the hidden param pak)
    set_link v            -- 0/1 value-link chip display (glyph + lane tint)
    set_playhead i        -- highlight step i (-1 or out of range = none;
                             for future sequencer use)

Outlet (1) -- two message shapes, both documented contract:
    step i v              -- per-step edit stream: emitted for EVERY bar a
                             gesture writes (click, each drag-painted bar,
                             modifier-reset) -- cheap real-time consumers
                             subscribe here without parsing the full list
    values v0 v1 ...      -- ALL active steps (normalized 0..1), emitted
                             after ANY edit event -- the persistence payload
"""

from string import Template

STEP_BARS_INLETS = 1
STEP_BARS_OUTLETS = 1


def step_bars_js(
    *,
    accent="0.36, 0.92, 0.96, 1.0",
    bg="0.05, 0.05, 0.06, 1.0",
    grid_color="0.22, 0.24, 0.28, 0.45",
    text_color="0.92, 0.95, 0.98, 0.95",
    label_color="0.52, 0.56, 0.63, 0.9",
    fill_color=None,
    max_steps=16,
    init_steps=8,
    init_values=None,
    init_value=1.0,
    reset_value=0.0,
    init_link=0,
):
    """Return ES5 JavaScript for a step-bar lane editor (Max jsui).

    Colors are RGBA strings (``"r, g, b, a"``); ``fill_color=None`` derives
    the link-tint wash from ``accent`` at low alpha. ``max_steps`` (2..32) is
    the fixed slot count; ``init_steps`` (2..max_steps, default 8) is the
    active count at first paint. ``init_values`` seeds the leading slots
    (normalized 0..1); remaining slots fill with ``init_value``. Match the
    initials to the bound params' initials so the lane is honest before any
    value arrives. ``reset_value`` is the Cmd/Alt-click reset target and
    ``init_link`` seeds the link-chip display.
    """
    max_steps = int(max_steps)
    if not 2 <= max_steps <= 32:
        raise ValueError(f"max_steps must be 2..32, got {max_steps}")
    init_steps = int(init_steps)
    if not 2 <= init_steps <= max_steps:
        raise ValueError(f"init_steps must be 2..{max_steps}, got {init_steps}")
    init_value = float(init_value)
    reset_value = float(reset_value)
    if not 0.0 <= init_value <= 1.0:
        raise ValueError(f"init_value must be 0..1, got {init_value}")
    if not 0.0 <= reset_value <= 1.0:
        raise ValueError(f"reset_value must be 0..1, got {reset_value}")
    seeds = [float(v) for v in (init_values or ())]
    if len(seeds) > max_steps:
        raise ValueError(
            f"init_values holds {len(seeds)} values, max_steps is {max_steps}"
        )
    if any(not 0.0 <= v <= 1.0 for v in seeds):
        raise ValueError("init_values must be normalized 0..1")
    slots = seeds + [init_value] * (max_steps - len(seeds))
    if fill_color is None:
        parts = [p.strip() for p in accent.split(",")]
        fill_color = ", ".join(parts[:3]) + ", 0.13"
    return _JS_TEMPLATE.substitute(
        accent=accent,
        bg=bg,
        grid_color=grid_color,
        text_color=text_color,
        label_color=label_color,
        fill_color=fill_color,
        max_steps=max_steps,
        init_steps=init_steps,
        init_values=", ".join(repr(v) for v in slots),
        reset_value=reset_value,
        init_link=int(bool(init_link)),
    )


_JS_TEMPLATE = Template("""\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

var BG_COLOR    = [$bg];
var GRID_COLOR  = [$grid_color];
var TEXT_COLOR  = [$text_color];
var LABEL_COLOR = [$label_color];
var ACCENT      = [$accent];
var FILL_COLOR  = [$fill_color];

var MAX_STEPS   = $max_steps;
var RESET_VALUE = $reset_value;

// fixed slot array: ALL MAX_STEPS values persist; num_steps is only how many
// are shown/emitted, so shrinking then growing the count round-trips values.
var num_steps = $init_steps;
var values = [$init_values];

var link_on  = $init_link;     // #8 value-link chip DISPLAY state
var playhead = -1;             // highlighted step (-1 = none)

var dragging  = 0;             // a paint stroke is active
var last_bar  = -1;            // previous painted bar (interp anchor)
var last_val  = 0.0;
var drag_step = -1;            // live readout while painting
var drag_v    = 0.0;

var BAR_GAP = 1.0;             // px between bars

var MARGIN_L = 6;
var MARGIN_R = 6;
var MARGIN_T = 6;
var MARGIN_B = 15;             // the value row lives below the plot

function plot_left()   { return MARGIN_L; }
function plot_right()  { return mgraphics.size[0] - MARGIN_R; }
function plot_top()    { return MARGIN_T; }
function plot_bottom() { return mgraphics.size[1] - MARGIN_B; }
function plot_w()      { return plot_right() - plot_left(); }
function plot_h()      { return plot_bottom() - plot_top(); }

function set_rgba(c) { mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]); }
function clamp01(v) { if (v < 0) return 0; if (v > 1) return 1; return v; }

// pixel <-> value maps (to_px_y matches curve_editor's bottom-up convention)
function to_px_y(nv) { return plot_bottom() - clamp01(nv) * plot_h(); }
function from_px_y(y) { return clamp01((plot_bottom() - y) / plot_h()); }

function bar_w() { return plot_w() / num_steps; }
function bar_left(i) { return plot_left() + bar_w() * i; }
function bar_center_x(i) { return bar_left(i) + bar_w() / 2; }

// bar under an x pixel, clamped into range (painting past an edge clamps
// to the first/last bar instead of dropping the stroke).
function bar_index(x) {
    var i = Math.floor((x - plot_left()) / bar_w());
    if (i < 0) i = 0;
    if (i > num_steps - 1) i = num_steps - 1;
    return i;
}

// ---- edit plumbing ---------------------------------------------------------
function emit_step(i) {
    outlet(0, "step", i, values[i]);
}

function emit_values() {
    var args = [0, "values"], i;
    for (i = 0; i < num_steps; i++) args.push(values[i]);
    outlet.apply(this, args);
}

// write one bar (per-step stream); returns 1 so paint_to can OR the strokes.
function write_bar(i, v) {
    values[i] = clamp01(v);
    emit_step(i);
    return 1;
}

// drag-paint: write every bar between the stroke anchor and the current bar
// with linearly interpolated values, so a fast sweep never skips a bar.
function paint_to(bx, v) {
    var span, dir, i, wrote = 0;
    if (last_bar < 0) { last_bar = bx; last_val = v; }
    if (bx === last_bar) {
        wrote = write_bar(bx, v);
    } else {
        dir = (bx > last_bar) ? 1 : -1;
        span = (bx - last_bar) * dir;
        for (i = 1; i <= span; i++) {
            wrote = write_bar(last_bar + dir * i,
                              last_val + (v - last_val) * (i / span)) || wrote;
        }
    }
    last_bar = bx;
    last_val = v;
    drag_step = bx;
    drag_v = values[bx];
    if (wrote) emit_values();
    mgraphics.redraw();
}

// ---- drawing ---------------------------------------------------------------
function draw_background() {
    set_rgba(BG_COLOR);
    mgraphics.rectangle(0, 0, mgraphics.size[0], mgraphics.size[1]);
    mgraphics.fill();
    if (link_on) {                 // #8: tint the lane while linked
        set_rgba(FILL_COLOR);
        mgraphics.rectangle(plot_left(), plot_top(), plot_w(), plot_h());
        mgraphics.fill();
    }
}

function draw_grid() {
    var i, y;
    set_rgba(GRID_COLOR);
    mgraphics.set_line_width(1.0);
    for (i = 1; i < 4; i++) {      // quarter guides, curve_editor's dim idiom
        y = plot_top() + plot_h() * i / 4;
        mgraphics.move_to(plot_left(), y);
        mgraphics.line_to(plot_right(), y);
        mgraphics.stroke();
    }
    mgraphics.move_to(plot_left(), plot_bottom());
    mgraphics.line_to(plot_right(), plot_bottom());
    mgraphics.stroke();
}

function draw_bars() {
    var i, x, w, h;
    w = bar_w() - BAR_GAP;
    if (w < 1) w = 1;
    for (i = 0; i < num_steps; i++) {
        x = bar_left(i);
        set_rgba(GRID_COLOR);      // dim slot track behind the value bar
        mgraphics.rectangle(x, plot_top(), w, plot_h());
        mgraphics.fill();
        set_rgba(ACCENT);
        h = values[i] * plot_h();
        if (h < 1.5) h = 1.5;      // zero bars keep a visible baseline stub
        mgraphics.rectangle(x, plot_bottom() - h, w, h);
        mgraphics.fill();
    }
}

function draw_playhead() {
    if (playhead < 0 || playhead >= num_steps) return;
    set_rgba(TEXT_COLOR);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle(bar_left(playhead), plot_top(),
                        bar_w() - BAR_GAP, plot_h());
    mgraphics.stroke();
}

// #8 chip: a small chain-link glyph, top-left (visual only)
function draw_link_glyph() {
    if (!link_on) return;
    var cx = plot_left() + 8;
    var cy = plot_top() + 8;
    set_rgba(ACCENT);
    mgraphics.set_line_width(1.2);
    mgraphics.arc(cx - 2.2, cy, 3.0, 0, Math.PI * 2);
    mgraphics.stroke();
    mgraphics.arc(cx + 2.2, cy, 3.0, 0, Math.PI * 2);
    mgraphics.stroke();
}

// footer: "8 st   Link   P 3" (count / link chip state / playhead)
function draw_value_row() {
    var ty = mgraphics.size[1] - 4;
    var cell = (mgraphics.size[0] - MARGIN_L - MARGIN_R) / 4.0;
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(7.5);
    set_rgba(TEXT_COLOR);
    mgraphics.move_to(plot_left(), ty);
    mgraphics.show_text(num_steps + " st");
    set_rgba(link_on ? TEXT_COLOR : LABEL_COLOR);
    mgraphics.move_to(plot_left() + cell, ty);
    mgraphics.show_text(link_on ? "Link" : "link");
    if (playhead >= 0 && playhead < num_steps) {
        set_rgba(LABEL_COLOR);
        mgraphics.move_to(plot_left() + cell * 2, ty);
        mgraphics.show_text("P " + playhead);
    }
}

// "S 3 V 74" live readout while painting (value normalized 0..100)
function format_step() {
    return "S " + drag_step + " V " + Math.round(drag_v * 100);
}

function draw_drag_readout() {
    if (drag_step < 0) return;
    mgraphics.select_font_face("Ableton Sans Medium");
    mgraphics.set_font_size(7.5);
    set_rgba(TEXT_COLOR);
    mgraphics.move_to(plot_right() - 52, plot_top() + 8);
    mgraphics.show_text(format_step());
}

function paint() {
    draw_background();
    draw_grid();
    draw_bars();
    draw_playhead();
    draw_value_row();
    draw_drag_readout();
    draw_link_glyph();
}

// ---- interaction -----------------------------------------------------------
function onclick(x, y, but, cmd, shift, capslock, option, ctrl) {
    if (x < plot_left() - 2 || x > plot_right() + 2 ||
        y < plot_top() - 2 || y > plot_bottom() + 2) return;
    var i = bar_index(x);
    if (cmd || option) {           // modifier reset: no paint stroke starts
        dragging = 0;
        last_bar = -1;
        write_bar(i, RESET_VALUE);
        emit_values();
        mgraphics.redraw();
        return;
    }
    dragging = 1;
    last_bar = i;
    last_val = from_px_y(y);
    paint_to(i, last_val);
}

function ondrag(x, y, but, cmd, shift, capslock, option, ctrl) {
    if (but === 0) {               // release: stroke + readout end
        dragging = 0;
        last_bar = -1;
        drag_step = -1;
        mgraphics.redraw();
        return;
    }
    if (!dragging) return;
    paint_to(bar_index(x), from_px_y(y));
}

// ---- messages (set + redraw, NEVER re-emit; restores ignored mid-drag) -----
function set_steps(n) {
    if (dragging) return;
    n = Math.round(n);
    if (n < 2) n = 2;
    if (n > MAX_STEPS) n = MAX_STEPS;
    num_steps = n;                 // slot values all preserved
    if (playhead >= num_steps) playhead = -1;
    mgraphics.redraw();
}

function set_values() {
    if (dragging) return;
    var a = arrayfromargs(arguments), i;
    var n = a.length < MAX_STEPS ? a.length : MAX_STEPS;
    for (i = 0; i < n; i++) values[i] = clamp01(a[i]);
    mgraphics.redraw();
}

// wrapper-internal restore: count-first fixed-slot layout from the param pak
function set_all() {
    if (dragging) return;
    var a = arrayfromargs(arguments), i;
    if (a.length < 1) return;
    var n = Math.round(a[0]);
    if (n < 2) n = 2;
    if (n > MAX_STEPS) n = MAX_STEPS;
    if (n > a.length - 1) n = a.length - 1;
    if (n < 2) return;
    for (i = 0; i < MAX_STEPS && i < a.length - 1; i++) {
        values[i] = clamp01(a[i + 1]);
    }
    num_steps = n;
    if (playhead >= num_steps) playhead = -1;
    mgraphics.redraw();
}

function set_link(v) { link_on = (v > 0) ? 1 : 0; mgraphics.redraw(); }

function set_playhead(v) {
    v = Math.round(v);
    playhead = (v >= 0 && v < num_steps) ? v : -1;
    mgraphics.redraw();
}

// stray bare numbers on the inlet are meaningless -- swallow them silently
// so nothing ever posts "no function" errors to the Max console.
function msg_float(v) {}
function msg_int(v) {}
""")
