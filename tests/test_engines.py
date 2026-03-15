"""Tests for visual engine modules (jsui JavaScript code generators)."""
import os
import tempfile
import pytest

from m4l_builder import AudioEffect, MIDNIGHT
from m4l_builder.engines.filter_curve import filter_curve_js, FILTER_CURVE_INLETS
from m4l_builder.engines.crossover_display import (
    crossover_display_js,
    CROSSOVER_DISPLAY_INLETS,
)
from m4l_builder.engines.eq_band_column import (
    eq_band_column_js, EQ_BAND_COLUMN_INLETS, EQ_BAND_COLUMN_OUTLETS)
from m4l_builder.engines.eq_curve import eq_curve_js, EQ_CURVE_INLETS
from m4l_builder.engines.linear_phase_eq_display import (
    linear_phase_eq_display_js,
    LINEAR_PHASE_EQ_DISPLAY_INLETS,
    LINEAR_PHASE_EQ_DISPLAY_OUTLETS,
)
from m4l_builder.engines.spectrum_analyzer import (
    spectrum_analyzer_js,
    spectrum_analyzer_dsp,
    SPECTRUM_INLETS,
)
from m4l_builder.engines.envelope_display import envelope_display_js, ENVELOPE_INLETS
from m4l_builder.engines.waveform_display import waveform_display_js, WAVEFORM_INLETS
from m4l_builder.engines.xy_pad import xy_pad_js, XY_PAD_INLETS, XY_PAD_OUTLETS
from m4l_builder.engines.piano_roll import piano_roll_js, PIANO_ROLL_INLETS, PIANO_ROLL_OUTLETS
from m4l_builder.engines.velocity_curve_display import (
    velocity_curve_display_js, VELOCITY_CURVE_INLETS, VELOCITY_CURVE_OUTLETS)
from m4l_builder.engines.wavetable_display import (
    wavetable_display_js, WAVETABLE_DISPLAY_INLETS, WAVETABLE_DISPLAY_OUTLETS)
from m4l_builder.engines.resonance_bank_display import (
    resonance_bank_display_js, RESONANCE_BANK_INLETS, RESONANCE_BANK_OUTLETS)
from m4l_builder.engines.sidechain_display import (
    sidechain_display_js, SIDECHAIN_DISPLAY_INLETS, SIDECHAIN_DISPLAY_OUTLETS)
from m4l_builder.engines.spectral_display import (
    spectral_display_js, SPECTRAL_DISPLAY_INLETS, SPECTRAL_DISPLAY_OUTLETS)
from m4l_builder.engines.peaking_eq_display import (
    peaking_eq_display_js, PEAKING_EQ_DISPLAY_INLETS, PEAKING_EQ_DISPLAY_OUTLETS)
from m4l_builder.engines.step_grid_display import (
    step_grid_display_js, STEP_GRID_DISPLAY_INLETS, STEP_GRID_DISPLAY_OUTLETS)
from m4l_builder.engines.grain_display import (
    grain_display_js, GRAIN_DISPLAY_INLETS, GRAIN_DISPLAY_OUTLETS)
from m4l_builder.engines.grid_sequencer_display import (
    grid_sequencer_display_js, GRID_SEQ_INLETS, GRID_SEQ_OUTLETS)
from m4l_builder.engines.wavetable_editor import (
    wavetable_editor_js, WAVETABLE_EDITOR_INLETS, WAVETABLE_EDITOR_OUTLETS)
from m4l_builder.engines.spectral_vocoder_display import (
    spectral_vocoder_display_js, SPECTRAL_VOCODER_INLETS, SPECTRAL_VOCODER_OUTLETS)
from m4l_builder.engines.slice_overview import (
    slice_overview_js, SLICE_OVERVIEW_INLETS, SLICE_OVERVIEW_OUTLETS)
from m4l_builder.engines.slice_pattern_display import (
    slice_pattern_display_js,
    SLICE_PATTERN_DISPLAY_INLETS,
    SLICE_PATTERN_DISPLAY_OUTLETS,
)


class TestCrossoverDisplayEngine:
    def test_returns_string(self):
        js = crossover_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_declares_inlets(self):
        js = crossover_display_js()
        assert "inlets = 3;" in js

    def test_contains_paint_function(self):
        js = crossover_display_js()
        assert "function paint()" in js

    def test_contains_msg_float_handler(self):
        js = crossover_display_js()
        assert "function msg_float" in js

    def test_contains_band_labels(self):
        js = crossover_display_js()
        assert '"LOW"' in js
        assert '"MID"' in js
        assert '"HIGH"' in js

    def test_custom_colors_present(self):
        js = crossover_display_js(low_color="0.1, 0.2, 0.3, 0.4")
        assert "0.1, 0.2, 0.3, 0.4" in js

    def test_inlet_count_metadata(self):
        assert CROSSOVER_DISPLAY_INLETS == 3


class TestFilterCurveEngine:
    def test_returns_string(self):
        js = filter_curve_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = filter_curve_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = filter_curve_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = filter_curve_js()
        assert "inlets = 3;" in js

    def test_handles_msg_float(self):
        js = filter_curve_js()
        assert "function msg_float" in js

    def test_custom_line_color(self):
        js = filter_curve_js(line_color="1.0, 0.0, 0.0, 1.0")
        assert "1.0, 0.0, 0.0, 1.0" in js

    def test_custom_bg_color(self):
        js = filter_curve_js(bg_color="0.1, 0.1, 0.1, 1.0")
        assert "0.1, 0.1, 0.1, 1.0" in js

    def test_defaults_to_grey_shell_and_blue_plot(self):
        js = filter_curve_js()
        assert "0.24, 0.24, 0.25, 1.0" in js
        assert "0.07, 0.10, 0.15, 1.0" in js

    def test_no_es6_let(self):
        """Verify no 'let' declarations (ES5 only uses var).
        Checks for 'let ' at the start of a statement, not as substring of 'inlet'."""
        import re
        js = filter_curve_js()
        # Match 'let ' as a statement keyword (preceded by start or whitespace, not alphanumeric)
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        """Verify no arrow functions."""
        js = filter_curve_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"

    def test_inlet_count_metadata(self):
        assert FILTER_CURVE_INLETS == 3

    def test_contains_filter_types(self):
        js = filter_curve_js()
        assert "LP" in js
        assert "HP" in js

    def test_contains_mgraphics_redraw(self):
        js = filter_curve_js()
        assert "mgraphics.redraw()" in js

    def test_default_colors_present(self):
        js = filter_curve_js()
        # Default line color
        assert "0.45, 0.75, 0.65, 1.0" in js


class TestEqBandColumnEngine:
    def test_returns_string(self):
        js = eq_band_column_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_handlers(self):
        js = eq_band_column_js()
        assert "function paint()" in js
        assert "function set_band" in js
        assert "function set_selected" in js
        assert "function onclick" in js
        assert "function ondrag" in js

    def test_contains_expected_messages(self):
        js = eq_band_column_js(show_slope=True, show_solo=True, show_motion=True, show_dynamic=True)
        assert '"band_freq"' in js
        assert '"band_gain"' in js
        assert '"band_q"' in js
        assert '"band_type"' in js
        assert '"band_slope"' in js
        assert '"band_enable"' in js
        assert '"band_solo"' in js
        assert '"band_motion"' in js
        assert '"band_dynamic"' in js
        assert '"band_motion_rate"' in js
        assert '"band_motion_depth"' in js
        assert '"band_motion_direction"' in js

    def test_custom_titles_and_types_present(self):
        js = eq_band_column_js(title="DETAIL", type_names=["Peak", "Shelf"])
        assert '"DETAIL"' in js
        assert '"Shelf"' in js

    def test_inlet_and_outlet_metadata(self):
        assert EQ_BAND_COLUMN_INLETS == 1
        assert EQ_BAND_COLUMN_OUTLETS == 1

    def test_normalizes_cut_filter_q_and_disables_unsupported_dynamic(self):
        js = eq_band_column_js(show_motion=True, show_dynamic=True)
        assert "function apply_type_change(next_type)" in js
        assert "if (next_type === 3 || next_type === 4)" in js
        assert 'outlet(0, "band_q", selected_band, band.q);' in js
        assert "function supports_dynamic(type_idx)" in js
        assert "if (!supports_dynamic(band.type)) return;" in js

    def test_uses_distinct_motion_knob_accent(self):
        js = eq_band_column_js(show_motion=True)
        assert "var MOTION_ACCENT_COLOR = [0.34, 0.86, 0.98, 1.0];" in js
        assert "function knob_accent_color(info)" in js
        assert "function default_motion_rate(idx)" in js

    def test_supports_motion_direction_knob(self):
        js = eq_band_column_js(show_motion=True, show_type_controls=False)
        assert '"band_motion_direction"' in js
        assert "function default_motion_direction(idx)" in js
        assert "function clamp_motion_direction(value)" in js
        assert 'key: "motion_direction"' in js
        assert 'label: "DIR"' in js

    def test_can_hide_type_scroller_and_keep_vertical_state_stack(self):
        js = eq_band_column_js(show_motion=True, show_dynamic=True, show_type_controls=False)
        assert "var SHOW_TYPE_CONTROLS = 0;" in js
        assert "if (SHOW_TYPE_CONTROLS) {" in js
        assert "push_stack(\"enable\")" in js

    def test_uses_theme_font_hooks_and_compact_breakpoint(self):
        js = eq_band_column_js(font_name="Ableton Sans Medium", font_bold_name="Ableton Sans Bold")
        assert 'var FONT_NAME = "Ableton Sans Medium";' in js
        assert 'var FONT_BOLD_NAME = "Ableton Sans Bold";' in js
        assert "return mgraphics.size[0] <= 118 || mgraphics.size[1] <= 148;" in js
        assert "function mix_color(color_a, color_b, amount)" in js

    def test_supports_frameless_headerless_rail_and_alt_scroll_q(self):
        js = eq_band_column_js(show_header=False, show_frame=False, force_regular_layout=True)
        assert "var SHOW_HEADER = 0;" in js
        assert "var SHOW_FRAME = 0;" in js
        assert "var FORCE_REGULAR_LAYOUT = 1;" in js
        assert "function uses_minimal_rail_layout()" in js
        assert "if (FORCE_REGULAR_LAYOUT) return 0;" in js
        assert "function onwheel(x, y, scrollx, scrolly, cmd, shift, caps, opt, ctrl)" in js
        assert 'emit_value("q", next_q);' in js

    def test_uses_10hz_to_22khz_frequency_range(self):
        js = eq_band_column_js()
        assert "var MIN_FREQ = 10.0;" in js
        assert "var MAX_FREQ = 22000.0;" in js


class TestEqCurveEngine:
    def test_returns_string(self):
        js = eq_curve_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_paint_function(self):
        js = eq_curve_js()
        assert "function paint()" in js

    def test_contains_mgraphics_init(self):
        js = eq_curve_js()
        assert "mgraphics.init()" in js


    def test_contains_mouse_handlers(self):
        js = eq_curve_js()
        assert "function onclick" in js
        assert "function ondblclick" in js
        assert "function ondrag" in js

    def test_declares_inlets(self):
        js = eq_curve_js()
        assert "inlets = 3;" in js

    def test_declares_outlets(self):
        js = eq_curve_js()
        assert "outlets = 4;" in js

    def test_outlet_count_metadata(self):
        from m4l_builder.engines.eq_curve import EQ_CURVE_OUTLETS
        assert EQ_CURVE_OUTLETS == 4

    def test_inlet_count_metadata(self):
        assert EQ_CURVE_INLETS == 3

    def test_custom_bg_color(self):
        js = eq_curve_js(bg_color="0.1, 0.2, 0.3, 1.0")
        assert "0.1, 0.2, 0.3, 1.0" in js

    def test_transparent_plot_keeps_transparent_panel(self):
        js = eq_curve_js(bg_color="0.0, 0.0, 0.0, 0.0")
        assert "var PANEL_CLR      = [0.0, 0.0, 0.0, 0.0];" in js

    def test_contains_set_band_handler(self):
        js = eq_curve_js()
        assert "function set_band" in js

    def test_contains_set_num_bands(self):
        js = eq_curve_js()
        assert "function set_num_bands" in js

    def test_contains_draw_grid(self):
        js = eq_curve_js()
        assert "function draw_grid" in js or "draw_grid" in js

    def test_contains_draw_nodes(self):
        js = eq_curve_js()
        assert "function draw_nodes" in js or "draw_nodes" in js

    def test_contains_band_colors(self):
        js = eq_curve_js()
        assert "BAND_COLORS" in js

    def test_contains_onwheel(self):
        js = eq_curve_js()
        assert "function onwheel" in js

    def test_contains_onidleout(self):
        js = eq_curve_js()
        assert "function onidleout" in js

    def test_contains_tooltip(self):
        js = eq_curve_js()
        assert "draw_tooltip" in js

    def test_contains_sample_rate_state(self):
        js = eq_curve_js()
        assert "var sample_rate = DEFAULT_SR;" in js
        assert "if (inlet === 1)" in js

    def test_contains_analyzer_support(self):
        js = eq_curve_js()
        assert "function draw_analyzer" in js
        assert "function set_analyzer_enabled" in js
        assert "if (inlet === 2)" in js
        assert "function list()" in js

    def test_contains_graph_band_management_messages(self):
        js = eq_curve_js()
        assert '"add_band"' in js
        assert '"delete_band"' in js
        assert "find_free_band" in js

    def test_contains_node_menu_motion_and_dynamic_messages(self):
        js = eq_curve_js()
        assert "function draw_node_menu" in js
        assert "function node_menu_hit_test" in js
        assert "function draw_dynamic_handles" in js
        assert "function dynamic_hit_test" in js
        assert "function open_node_menu_for" in js
        assert '"band_motion"' in js
        assert '"band_dynamic"' in js
        assert '"band_dynamic_amount"' in js
        assert '"band_motion_rate"' in js
        assert '"band_motion_depth"' in js
        assert "MAX_DYNAMIC_RANGE" in js
        assert "TYPE_SHORT_NAMES" in js

    def test_supports_pointer_context_clicks_for_node_menu(self):
        js = eq_curve_js()
        assert "function pointer_middle_click(pointerevent, but)" in js
        assert "pointerevent.button !== undefined && pointerevent.button === 1" in js
        assert "pointerevent.buttons !== undefined && (pointerevent.buttons & 4) !== 0" in js
        assert "if ((but & 4) !== 0) return 1;" in js
        assert "function pointer_context_click(pointerevent, but, ctrl)" in js
        assert "pointerevent.button !== undefined && pointerevent.button === 2" in js
        assert "pointerevent.buttons !== undefined && (pointerevent.buttons & 2) !== 0" in js
        assert "if ((but & 2) !== 0) return 1;" in js
        assert "return ctrl ? 1 : 0;" in js
        assert "function pointer_x(pointerevent, fallback)" in js
        assert "function pointer_y(pointerevent, fallback)" in js
        assert "function pointer_buttons(pointerevent, fallback)" in js
        assert "function note_pointer_press(x, y)" in js
        assert "function should_ignore_pointer_click(x, y)" in js
        assert "function handle_press(x, y, but, cmd, shift, opt, ctrl, pointerevent)" in js
        assert "var middle_click = pointer_middle_click(pointerevent, but);" in js
        assert "var context_click = pointer_context_click(pointerevent, but, ctrl);" in js
        assert "if (middle_click) {" in js
        assert "if (context_click) {" in js
        assert "if (dynamic_hit >= 0 || hit >= 0) {" in js
        assert "open_node_menu_for(selected_band, x, y);" in js
        assert "if (should_ignore_pointer_click(x, y)) return;" in js
        assert "function onpointerdown(pointerevent)" in js
        assert "function onpointermove(pointerevent)" in js
        assert "function onpointerup(pointerevent)" in js
        assert "function onpointerleave(pointerevent)" in js

    def test_contains_double_click_create_delete_and_drag_fast_path(self):
        js = eq_curve_js()
        assert "function create_band_at(x, y)" in js
        assert "function ondblclick(x, y, but, cmd, shift, caps, opt, ctrl)" in js
        assert "function delete_band_at(idx)" in js
        assert "var DOUBLE_CLICK_MS = 320;" in js
        assert "var suppress_next_ondblclick_delete = 0;" in js
        assert "delete_band_at(clicked_band);" in js
        assert "suppress_next_ondblclick_delete = 1;" in js
        assert "if (dynamic_hit >= 0 || hit >= 0)" in js
        assert "create_band_at(x, y);" in js
        assert "if (uses_gain && new_freq === b.freq && new_gain === b.gain) return;" in js
        assert "if (!uses_gain && new_freq === b.freq && new_q === b.q) return;" in js

    def test_contains_biquad_coeffs(self):
        js = eq_curve_js()
        assert "function biquad_coeffs" in js
        assert "function response_db" in js

    def test_contains_allpass_type(self):
        js = eq_curve_js()
        assert "TYPE_ALLPASS" in js
        assert "AllPass" in js

    def test_gain_range_30db(self):
        js = eq_curve_js()
        assert "MIN_GAIN" in js and "= -30" in js
        assert "MAX_GAIN" in js and "= 30" in js

    def test_display_range_defaults_to_15db(self):
        js = eq_curve_js()
        assert "var display_range = 15.0;" in js
        assert "if (display_range <= 15.0) return 3.0;" in js
        assert "display_range = 15.0;" in js

    def test_uses_10hz_to_22khz_frequency_range(self):
        js = eq_curve_js()
        assert "var MIN_FREQ      = 10;" in js
        assert "var MAX_FREQ      = 22000;" in js
        assert 'var FREQ_LABELS = ["10", "20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "22k"];' in js

    def test_no_ondragend(self):
        """ondragend does not exist in jsui — use but===0 in ondrag."""
        js = eq_curve_js()
        assert "ondragend" not in js

    def test_mouse_up_in_ondrag(self):
        """ondrag checks but === 0 for mouse release."""
        js = eq_curve_js()
        assert "but === 0" in js

    def test_normalizes_cut_filter_q_on_type_change(self):
        js = eq_curve_js()
        assert "function apply_band_type(idx, type_idx)" in js
        assert "if ((next_type === TYPE_LOWPASS || next_type === TYPE_HIGHPASS) && prev_type !== next_type)" in js
        assert 'outlet(3, "band_q", idx, band_cache[idx].q);' in js

    def test_contains_motion_animation_scheduler_and_redraw_throttle(self):
        js = eq_curve_js()
        assert "var REDRAW_INTERVAL_MS = 33;" in js
        assert "function request_redraw()" in js
        assert "function animation_tick()" in js
        assert 'typeof Task !== "undefined"' in js
        assert "refresh_animation_task();" in js

    def test_supports_motion_direction_and_draws_guides(self):
        js = eq_curve_js()
        assert "function motion_direction_components(direction)" in js
        assert "function draw_motion_guides()" in js
        assert "function set_motion_direction(idx, value)" in js
        assert 'outlet(0, "band_motion_direction", created_idx, bands[created_idx].motion_direction);' in js
        assert "Math.cos(radians)" in js
        assert "Math.sin(radians)" in js

    def test_includes_motion_readout_in_tooltip(self):
        js = eq_curve_js()
        assert 'line3 += "MOT " + format_motion_rate(b.motion_rate) + "  " + format_motion_depth(b.motion_depth) + "  DIR " + Math.round(clamp_motion_direction(b.motion_direction)) + "°";' in js
        assert "var tw = line3 ? 214 : 104;" in js

    def test_draws_continuous_analyzer_fill(self):
        js = eq_curve_js()
        assert "analyzer_display[i] = analyzer_display[i] * 0.55 + incoming * 0.45;" in js
        assert "mgraphics.set_line_width(1.0);" in js
        assert "mgraphics.move_to(xs[i], ys[i]);" in js
        assert "mgraphics.line_to(xs[i], ys[i]);" in js

    def test_only_draws_individual_band_curves_for_selected_or_hovered_band(self):
        js = eq_curve_js()
        assert "if (i !== selected_band && i !== hover_band) continue;" in js

    def test_bypass_keeps_nodes_visible_and_no_longer_calls_delete(self):
        js = eq_curve_js()
        assert "enabled_alpha = band_cache[i].enabled ? 1.0 : 0.26;" in js
        assert 'line2 += "  BYPASSED";' in js
        assert 'bands[idx].enabled = bands[idx].enabled ? 0 : 1;' in js
        assert 'outlet(0, "band_enable", idx, bands[idx].enabled ? 1 : 0);' in js
        assert "close_node_menu();" in js


class TestSliceOverviewEngine:
    def test_returns_string(self):
        js = slice_overview_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_declares_expected_io(self):
        js = slice_overview_js()
        assert "inlets = 7;" in js
        assert "outlets = 1;" in js
        assert SLICE_OVERVIEW_INLETS == 7
        assert SLICE_OVERVIEW_OUTLETS == 1

    def test_contains_sampler_surface_handlers(self):
        js = slice_overview_js()
        assert "function paint()" in js
        assert "function onclick" in js
        assert "function ondrag" in js
        assert "function draw_waveform" in js
        assert "function rebuild_waveform_cache()" in js
        assert "function register_hit()" in js
        assert "new Buffer(BUFFER_NAME)" in js
        assert "recent_hits" in js
        assert "ACTIVE" in js
        assert "DROP SAMPLE" in js

    def test_allows_custom_region_color(self):
        js = slice_overview_js(region_line="1.0, 0.0, 0.0, 1.0")
        assert "1.0, 0.0, 0.0, 1.0" in js

    def test_allows_custom_buffer_name(self):
        js = slice_overview_js(buffer_name="custombuf")
        assert "var BUFFER_NAME = 'custombuf';" in js


class TestSlicePatternDisplayEngine:
    def test_returns_string(self):
        js = slice_pattern_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_declares_expected_io(self):
        js = slice_pattern_display_js()
        assert "inlets = 15;" in js
        assert "outlets = 2;" in js
        assert SLICE_PATTERN_DISPLAY_INLETS == 15
        assert SLICE_PATTERN_DISPLAY_OUTLETS == 2

    def test_contains_pattern_helpers(self):
        js = slice_pattern_display_js()
        assert "function step_base_index(step)" in js
        assert "function step_computed_index(step)" in js
        assert "function step_index(step)" in js
        assert "function step_chopped(step)" in js
        assert "function step_ratchet_count(step)" in js
        assert "function main_glitch_shift(step)" in js
        assert "function step_direction(step)" in js
        assert "function step_pitch(step)" in js
        assert "function ratchet_index(step, ratchet_no)" in js
        assert "function step_arp(step)" in js
        assert "function onclick(x, y, but, cmd, shift, capslock, option, ctrl)" in js
        assert "function ondrag(x, y, but, cmd, shift, capslock, option, ctrl)" in js
        assert "function anything()" in js
        assert "function normalize_locks()" in js
        assert "function slice_index_from_point(y)" in js
        assert "function direction_from_point(y)" in js
        assert "function pitch_from_point(y)" in js
        assert "function paint_drag_range(step, y)" in js
        assert "function emit_scene_dump(slot)" in js
        assert "outlet(0, 'lock', step, idx);" in js
        assert "outlet(0, 'unlock', step);" in js
        assert "outlet(0, 'clear');" in js
        assert "outlet(0, 'dirlock', step, direction);" in js
        assert "outlet(0, 'dirunlock', step);" in js
        assert "outlet(0, 'dirclear');" in js
        assert "outlet(0, 'pitchlock', step, semitone);" in js
        assert "outlet(0, 'pitchunlock', step);" in js
        assert "outlet(0, 'pitchclear');" in js
        assert "outlet(0, 'gatelock', step, gate);" in js
        assert "outlet(0, 'gateunlock', step);" in js
        assert "outlet(0, 'gateclear');" in js
        assert "outlet(0, 'ratchetlock', step, count);" in js
        assert "outlet(0, 'ratchetunlock', step);" in js
        assert "outlet(0, 'ratchetclear');" in js
        assert "outlet(1, slot, 'set', i, step_locked_index(i));" in js
        assert "outlet(1, slot, 'dirset', i, step_locked_direction(i));" in js
        assert "outlet(1, slot, 'pitchset', i, step_locked_pitch(i));" in js
        assert "outlet(1, slot, 'gateset', i, step_locked_gate(i));" in js
        assert "outlet(1, slot, 'ratchetset', i, step_locked_ratchet(i));" in js
        assert "if (inlet !== 14) return;" in js
        assert "if (messagename === 'dumpa')" in js
        assert "if (messagename === 'dumpb')" in js
        assert "if (messagename === 'set' && argv.length >= 2)" in js
        assert "if (messagename === 'unset' && argv.length >= 1)" in js
        assert "if (messagename === 'dirset' && argv.length >= 2)" in js
        assert "if (messagename === 'dirunset' && argv.length >= 1)" in js
        assert "if (messagename === 'pitchset' && argv.length >= 2)" in js
        assert "if (messagename === 'pitchunset' && argv.length >= 1)" in js
        assert "if (messagename === 'gateset' && argv.length >= 2)" in js
        assert "if (messagename === 'gateunset' && argv.length >= 1)" in js
        assert "if (messagename === 'ratchetset' && argv.length >= 2)" in js
        assert "if (messagename === 'ratchetunset' && argv.length >= 1)" in js
        assert "function step_gate(step)" in js
        assert "function gate_from_point(y)" in js
        assert "function ratchet_from_point(y)" in js
        assert "if (shift && option && !cmd && !ctrl) drag_mode = 5;" in js
        assert "else if (cmd && option && !ctrl) drag_mode = 4;" in js
        assert "else if (ctrl) drag_mode = option ? -3 : 3;" in js
        assert "else if (option) drag_mode = 2;" in js
        assert "else drag_mode = cmd ? -1 : 1;" in js
        assert "return y < (h * 0.5) ? 1 : -1;" in js
        assert "return y < (h * 0.5) ? 1 : 0;" in js
        assert "return clamp(Math.round((norm * 48.0) - 24.0), -24, 24);" in js
        assert "return clamp(Math.floor(norm * 4.0), 0, 3);" in js
        assert "RATCHET_POSITIONS" in js
        assert "MODE_LABELS" in js

    def test_allows_custom_bar_color(self):
        js = slice_pattern_display_js(bar_color="0.9, 0.4, 0.1, 1.0")
        assert "0.9, 0.4, 0.1" in js

    def test_no_es6_arrow_functions(self):
        js = slice_pattern_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestLinearPhaseEqDisplayEngine:
    def test_returns_string(self):
        js = linear_phase_eq_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_declares_inlets(self):
        js = linear_phase_eq_display_js()
        assert "inlets = 3;" in js

    def test_declares_outlets(self):
        js = linear_phase_eq_display_js()
        assert "outlets = 4;" in js

    def test_inlet_count_metadata(self):
        assert LINEAR_PHASE_EQ_DISPLAY_INLETS == 3

    def test_outlet_count_metadata(self):
        assert LINEAR_PHASE_EQ_DISPLAY_OUTLETS == 4

    def test_contains_quality_and_latency_handlers(self):
        js = linear_phase_eq_display_js()
        assert "function set_quality_mode" in js
        assert "function set_analyzer_mode" in js
        assert "function set_latency_ms" in js
        assert "draw_hud();" in js
        assert "QUALITY_NAMES" in js
        assert "ANALYZER_MODE_NAMES" in js
        assert "RANGE_VALUES" in js
        assert "var RANGE_VALUES = [15.0];" in js
        assert "var display_range = 15.0;" in js

    def test_contains_redraw_throttle_for_analyzer_updates(self):
        js = linear_phase_eq_display_js()
        assert "var REDRAW_INTERVAL_MS = 33;" in js
        assert "function request_redraw()" in js

    def test_contains_collision_and_empty_state_support(self):
        js = linear_phase_eq_display_js()
        assert "function set_collision_mode" in js
        assert "function draw_empty_state" in js
        assert "label_overlaps" in js

    def test_contains_click_add_band_and_context_menu(self):
        js = linear_phase_eq_display_js()
        assert "function create_band_at" in js
        assert "function delete_band_at(idx)" in js
        assert "function hud_badges()" in js
        assert "function cycle_hud_badge(key, reverse)" in js
        assert "function draw_dynamic_handles" in js
        assert "function dynamic_hit_test" in js
        assert "function pointer_context_click" in js
        assert "function pointer_x" in js
        assert "function pointer_y" in js
        assert "function pointer_buttons" in js
        assert "function onpointerdown" in js
        assert "function onpointermove" in js
        assert "function onpointerup" in js
        assert "function handle_press" in js
        assert "function handle_double_click(x, y)" in js
        assert "function handle_drag_at" in js
        assert "function draw_context_menu" in js
        assert "function ensure_curve_cache" in js
        assert "function graph_db_to_y" in js
        assert "function draw_tooltip" in js
        assert "curve_dirty = 1" in js
        assert "pointerevent.contextModifier" in js
        assert "pointerevent.x !== undefined" in js
        assert "pointerevent.localX !== undefined" in js
        assert "legacy mouse handlers now receive an additional pointerevent struct" not in js
        assert "if (cache.uses_gain && new_freq === b.freq && new_gain === b.gain) return;" in js
        assert "if (!cache.uses_gain && new_freq === b.freq && new_q === b.q) return;" in js
        assert '"context_type"' in js
        assert '"context_dynamic"' in js
        assert '"context_slope"' in js
        assert '"context_solo"' in js
        assert '"context_enable"' in js
        assert '"band_dynamic_amount"' in js
        assert '"Make Dynamic"' in js
        assert '"add_band"' in js
        assert '"delete_band"' in js
        assert '"hud_quality"' in js
        assert '"hud_analyzer"' in js
        assert '"hud_range"' in js
        assert "find_free_band" in js
        assert "handle_double_click(x, y);" in js

    def test_keeps_disabled_nodes_visible_and_selectable(self):
        js = linear_phase_eq_display_js()
        assert "var DEFAULT_FREQS = [30.0, 200.0, 1000.0, 5000.0, 3600.0, 7200.0, 12000.0, 18000.0];" in js
        assert "var num_bands = MAX_BANDS;" in js
        assert 'band_cache[selected_band].enabled ? "" : "   Bypassed"' in js
        assert "if (num_bands > 0) {" in js
        assert "if (!band_cache[i]) continue;" in js
        assert "display_range = 15.0;" in js
        assert "mgraphics.arc(x, y, radius, 0, Math.PI * 2.0);" in js
        assert "mgraphics.rectangle_rounded(box_x" not in js

    def test_context_menu_can_open_for_disabled_nodes(self):
        js = linear_phase_eq_display_js()
        assert "if (!band_cache[context_menu_band].enabled) return;" not in js

    def test_paint_does_not_use_clip_state_stack(self):
        js = linear_phase_eq_display_js()
        assert "mgraphics.save();" not in js
        assert "mgraphics.clip();" not in js
        assert "mgraphics.restore();" not in js

    def test_excludes_allpass(self):
        js = linear_phase_eq_display_js()
        assert "AllPass" not in js
        assert "TYPE_ALLPASS" not in js

    def test_custom_badge_color(self):
        js = linear_phase_eq_display_js(badge_color="0.1, 0.2, 0.3, 0.4")
        assert "0.1, 0.2, 0.3, 0.4" in js

    def test_can_disable_dynamic_controls(self):
        js = linear_phase_eq_display_js(show_dynamic=False)
        assert "var SHOW_DYNAMIC = 0;" in js


class TestEnvelopeDisplayEngine:
    def test_returns_string(self):
        js = envelope_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_paint(self):
        js = envelope_display_js()
        assert "function paint()" in js

    def test_contains_mgraphics_init(self):
        js = envelope_display_js()
        assert "mgraphics.init()" in js

    def test_inlet_count_metadata(self):
        # ENVELOPE_INLETS is 4 (the Python constant)
        assert ENVELOPE_INLETS == 4

    def test_handles_msg_float(self):
        js = envelope_display_js()
        assert "function msg_float" in js

    def test_handles_adsr_segments(self):
        js = envelope_display_js()
        assert "attack" in js.lower()
        assert "decay" in js.lower()
        assert "sustain" in js.lower()
        assert "release" in js.lower()

    def test_custom_line_color(self):
        js = envelope_display_js(line_color="0.9, 0.3, 0.3, 1.0")
        assert "0.9, 0.3, 0.3, 1.0" in js

    def test_contains_build_envelope(self):
        js = envelope_display_js()
        assert "build_envelope" in js

    def test_contains_segment_labels(self):
        js = envelope_display_js()
        assert '"A"' in js
        assert '"D"' in js
        assert '"S"' in js
        assert '"R"' in js

    def test_no_es6_let(self):
        import re
        js = envelope_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"


class TestSpectrumAnalyzerEngine:
    def test_returns_string(self):
        js = spectrum_analyzer_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = spectrum_analyzer_js()
        assert "mgraphics.init()" in js

    def test_contains_paint(self):
        js = spectrum_analyzer_js()
        assert "function paint()" in js

    def test_contains_list_handler(self):
        js = spectrum_analyzer_js()
        assert "function list()" in js

    def test_inlet_count(self):
        assert SPECTRUM_INLETS == 2

    def test_declares_inlets(self):
        js = spectrum_analyzer_js()
        assert "inlets = 2;" in js

    def test_custom_bar_color(self):
        js = spectrum_analyzer_js(bar_color="0.8, 0.4, 0.2, 0.9")
        assert "0.8, 0.4, 0.2, 0.9" in js

    def test_custom_panel_color(self):
        js = spectrum_analyzer_js(panel_color="0.2, 0.2, 0.2, 1.0")
        assert "0.2, 0.2, 0.2, 1.0" in js

    def test_gradient_true_by_default(self):
        js = spectrum_analyzer_js()
        assert "USE_GRADIENT = true" in js

    def test_gradient_false_option(self):
        js = spectrum_analyzer_js(gradient=False)
        assert "USE_GRADIENT = false" in js

    def test_contains_peak_tracking(self):
        js = spectrum_analyzer_js()
        assert "peaks" in js

    def test_contains_exponential_smoothing(self):
        js = spectrum_analyzer_js()
        assert "smoothing" in js

    def test_supports_control_messages_and_hover_readout(self):
        js = spectrum_analyzer_js()
        assert "function anything()" in js
        assert 'messagename == "set_smoothing"' in js
        assert 'messagename == "set_peak_decay"' in js
        assert 'messagename == "set_show_peaks"' in js
        assert 'messagename == "set_range"' in js
        assert "function onidle(x, y)" in js
        assert "function onidleout()" in js
        assert "format_freq" in js
        assert "show_peaks" in js

    def test_no_es6_let(self):
        import re
        js = spectrum_analyzer_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"


class TestWaveformDisplayEngine:
    def test_returns_string(self):
        js = waveform_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = waveform_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint(self):
        js = waveform_display_js()
        assert "function paint()" in js

    def test_contains_list_handler(self):
        js = waveform_display_js()
        assert "function list()" in js

    def test_inlet_count(self):
        assert WAVEFORM_INLETS == 2

    def test_declares_inlets(self):
        js = waveform_display_js()
        assert "inlets = 2;" in js

    def test_contains_circular_buffer(self):
        js = waveform_display_js()
        assert "BUFFER_SIZE" in js
        assert "buffer" in js

    def test_custom_line_color(self):
        js = waveform_display_js(line_color="0.9, 0.5, 0.2, 1.0")
        assert "0.9, 0.5, 0.2, 1.0" in js

    def test_contains_display_modes(self):
        js = waveform_display_js()
        assert "display_mode" in js

    def test_contains_line_trace(self):
        js = waveform_display_js()
        assert "set_line_width(1.5)" in js

    def test_no_es6_let(self):
        import re
        js = waveform_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"


class TestXYPadEngine:
    def test_returns_string(self):
        js = xy_pad_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = xy_pad_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = xy_pad_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = xy_pad_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = xy_pad_js()
        assert "outlets = 2;" in js

    def test_inlet_count_metadata(self):
        assert XY_PAD_INLETS == 2

    def test_outlet_count_metadata(self):
        assert XY_PAD_OUTLETS == 2

    def test_contains_onclick(self):
        js = xy_pad_js()
        assert "function onclick" in js

    def test_contains_ondrag(self):
        js = xy_pad_js()
        assert "function ondrag" in js

    def test_handles_msg_float(self):
        js = xy_pad_js()
        assert "function msg_float" in js

    def test_custom_bg_color(self):
        js = xy_pad_js(bg_color="0.1, 0.1, 0.1, 1.0")
        assert "0.1, 0.1, 0.1, 1.0" in js

    def test_custom_dot_color(self):
        js = xy_pad_js(dot_color="1.0, 0.0, 0.0, 1.0")
        assert "1.0, 0.0, 0.0, 1.0" in js

    def test_contains_outlet_calls(self):
        js = xy_pad_js()
        assert "outlet(0" in js
        assert "outlet(1" in js

    def test_no_es6_let(self):
        import re
        js = xy_pad_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = xy_pad_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"

    def test_contains_mgraphics_redraw(self):
        js = xy_pad_js()
        assert "mgraphics.redraw()" in js

    def test_mouse_up_in_ondrag(self):
        js = xy_pad_js()
        assert "but === 0" in js


class TestPianoRollEngine:
    def test_returns_string(self):
        js = piano_roll_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = piano_roll_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = piano_roll_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = piano_roll_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = piano_roll_js()
        assert "outlets = 0;" in js

    def test_inlet_count_metadata(self):
        assert PIANO_ROLL_INLETS == 2

    def test_outlet_count_metadata(self):
        assert PIANO_ROLL_OUTLETS == 0

    def test_default_rows(self):
        js = piano_roll_js()
        assert "NUM_ROWS = 12" in js

    def test_default_cols(self):
        js = piano_roll_js()
        assert "NUM_COLS = 16" in js

    def test_custom_rows(self):
        js = piano_roll_js(rows=24)
        assert "NUM_ROWS = 24" in js

    def test_custom_cols(self):
        js = piano_roll_js(cols=32)
        assert "NUM_COLS = 32" in js

    def test_contains_set_function(self):
        js = piano_roll_js()
        assert "function set(" in js

    def test_handles_msg_int(self):
        js = piano_roll_js()
        assert "function msg_int" in js

    def test_custom_bg_color(self):
        js = piano_roll_js(bg_color="0.1, 0.2, 0.3, 1.0")
        assert "0.1, 0.2, 0.3, 1.0" in js

    def test_custom_note_color(self):
        js = piano_roll_js(note_color="1.0, 0.5, 0.0, 1.0")
        assert "1.0, 0.5, 0.0" in js

    def test_contains_playhead(self):
        js = piano_roll_js()
        assert "playhead_pos" in js

    def test_contains_velocity_alpha(self):
        js = piano_roll_js()
        assert "vel / 127" in js

    def test_no_es6_let(self):
        import re
        js = piano_roll_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = piano_roll_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"

    def test_contains_mgraphics_redraw(self):
        js = piano_roll_js()
        assert "mgraphics.redraw()" in js


class TestEngineImports:
    """Test that all engines import correctly from the package."""

    def test_import_from_engines_package(self):
        from m4l_builder.engines import (filter_curve_js, eq_curve_js,
                                          envelope_display_js, spectrum_analyzer_js,
                                          waveform_display_js, xy_pad_js, piano_roll_js,
                                          velocity_curve_display_js, wavetable_display_js,
                                          resonance_bank_display_js,
                                          sidechain_display_js, spectral_display_js,
                                          peaking_eq_display_js, step_grid_display_js,
                                          grain_display_js,
                                          slice_pattern_display_js)
        assert callable(filter_curve_js)
        assert callable(eq_curve_js)
        assert callable(envelope_display_js)
        assert callable(spectrum_analyzer_js)
        assert callable(waveform_display_js)
        assert callable(xy_pad_js)
        assert callable(piano_roll_js)
        assert callable(velocity_curve_display_js)
        assert callable(wavetable_display_js)
        assert callable(resonance_bank_display_js)
        assert callable(sidechain_display_js)
        assert callable(spectral_display_js)
        assert callable(peaking_eq_display_js)
        assert callable(step_grid_display_js)
        assert callable(grain_display_js)
        assert callable(slice_pattern_display_js)

    def test_import_constants_from_modules(self):
        from m4l_builder.engines.filter_curve import FILTER_CURVE_INLETS, FILTER_CURVE_OUTLETS
        from m4l_builder.engines.eq_curve import EQ_CURVE_INLETS, EQ_CURVE_OUTLETS
        from m4l_builder.engines.spectrum_analyzer import SPECTRUM_INLETS, SPECTRUM_OUTLETS
        from m4l_builder.engines.envelope_display import ENVELOPE_INLETS, ENVELOPE_OUTLETS
        from m4l_builder.engines.waveform_display import WAVEFORM_INLETS, WAVEFORM_OUTLETS
        from m4l_builder.engines.xy_pad import XY_PAD_INLETS, XY_PAD_OUTLETS
        from m4l_builder.engines.piano_roll import PIANO_ROLL_INLETS, PIANO_ROLL_OUTLETS
        from m4l_builder.engines.velocity_curve_display import (
            VELOCITY_CURVE_INLETS, VELOCITY_CURVE_OUTLETS)
        from m4l_builder.engines.wavetable_display import (
            WAVETABLE_DISPLAY_INLETS, WAVETABLE_DISPLAY_OUTLETS)
        from m4l_builder.engines.resonance_bank_display import (
            RESONANCE_BANK_INLETS, RESONANCE_BANK_OUTLETS)
        assert isinstance(FILTER_CURVE_INLETS, int)
        assert isinstance(EQ_CURVE_INLETS, int)
        assert isinstance(SPECTRUM_INLETS, int)
        assert isinstance(ENVELOPE_INLETS, int)
        assert isinstance(WAVEFORM_INLETS, int)
        assert FILTER_CURVE_OUTLETS == 0
        assert EQ_CURVE_OUTLETS == 4
        assert SPECTRUM_OUTLETS == 0
        assert ENVELOPE_OUTLETS == 0
        assert WAVEFORM_OUTLETS == 0
        assert XY_PAD_INLETS == 2
        assert XY_PAD_OUTLETS == 2
        assert PIANO_ROLL_INLETS == 2
        assert PIANO_ROLL_OUTLETS == 0
        assert VELOCITY_CURVE_INLETS == 1
        assert VELOCITY_CURVE_OUTLETS == 5
        assert WAVETABLE_DISPLAY_INLETS == 1
        assert WAVETABLE_DISPLAY_OUTLETS == 0
        assert RESONANCE_BANK_INLETS == 1
        assert RESONANCE_BANK_OUTLETS == 0
        assert SIDECHAIN_DISPLAY_INLETS == 2
        assert SIDECHAIN_DISPLAY_OUTLETS == 0
        assert SPECTRAL_DISPLAY_INLETS == 2
        assert SPECTRAL_DISPLAY_OUTLETS == 0
        assert PEAKING_EQ_DISPLAY_INLETS == 1
        assert PEAKING_EQ_DISPLAY_OUTLETS == 4
        assert STEP_GRID_DISPLAY_INLETS == 2
        assert STEP_GRID_DISPLAY_OUTLETS == 4
        assert GRAIN_DISPLAY_INLETS == 2
        assert GRAIN_DISPLAY_OUTLETS == 1


class TestDeviceJsuiIntegration:
    """Test that devices with jsui objects build correctly."""

    def test_add_jsui_stores_js_code(self):
        d = AudioEffect("Test", 300, 150, theme=MIDNIGHT)
        d.add_jsui("display", [10, 10, 200, 80],
                   js_code="// test code", numinlets=3)
        assert "display.js" in d._js_files
        assert d._js_files["display.js"] == "// test code"

    def test_add_jsui_custom_filename(self):
        d = AudioEffect("Test", 300, 150)
        d.add_jsui("display", [10, 10, 200, 80],
                   js_code="// test", js_filename="custom.js", numinlets=1)
        assert "custom.js" in d._js_files

    def test_dependency_cache_populated(self):
        d = AudioEffect("Test", 300, 150)
        d.add_jsui("display", [10, 10, 200, 80],
                   js_code="// test", numinlets=1)
        patcher = d.to_patcher()
        deps = patcher["patcher"]["dependency_cache"]
        assert any(dep["name"] == "display.js" for dep in deps)

    def test_dependency_cache_type_is_text(self):
        d = AudioEffect("Test", 300, 150)
        d.add_jsui("display", [10, 10, 200, 80],
                   js_code="// test", numinlets=1)
        patcher = d.to_patcher()
        deps = patcher["patcher"]["dependency_cache"]
        js_dep = next(dep for dep in deps if dep["name"] == "display.js")
        assert js_dep["type"] == "TEXT"

    def test_build_writes_js_file(self):
        d = AudioEffect("Test", 300, 150)
        d.add_jsui("my_display", [10, 10, 200, 80],
                   js_code="// my js code here", numinlets=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "Test.amxd")
            d.build(amxd_path)
            assert os.path.exists(amxd_path)
            js_path = os.path.join(tmpdir, "my_display.js")
            assert os.path.exists(js_path)
            with open(js_path) as f:
                assert f.read() == "// my js code here"

    def test_build_with_custom_filename(self):
        d = AudioEffect("Test", 300, 150)
        d.add_jsui("display", [10, 10, 200, 80],
                   js_code="// custom", js_filename="custom_name.js", numinlets=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "Test.amxd")
            d.build(amxd_path)
            js_path = os.path.join(tmpdir, "custom_name.js")
            assert os.path.exists(js_path)

    def test_build_with_engine_code(self):
        """Build a device using actual filter curve engine code."""
        d = AudioEffect("Test Filter", 300, 150)
        d.add_jsui("fc", [10, 10, 200, 80],
                   js_code=filter_curve_js(), numinlets=3)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "TestFilter.amxd")
            d.build(amxd_path)
            assert os.path.exists(amxd_path)
            js_path = os.path.join(tmpdir, "fc.js")
            assert os.path.exists(js_path)
            with open(js_path) as f:
                content = f.read()
                assert "mgraphics" in content
                assert "function paint()" in content

    def test_build_with_eq_engine_code(self):
        """Build a device using actual EQ curve engine code."""
        d = AudioEffect("Test EQ", 400, 200)
        d.add_jsui("eq", [10, 10, 300, 120],
                   js_code=eq_curve_js(), numinlets=3, numoutlets=4)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "TestEQ.amxd")
            d.build(amxd_path)
            assert os.path.exists(amxd_path)
            js_path = os.path.join(tmpdir, "eq.js")
            assert os.path.exists(js_path)
            with open(js_path) as f:
                content = f.read()
                assert "mgraphics" in content
                assert "function paint()" in content

    def test_spectrum_dsp_can_target_nonzero_inlet(self):
        d = AudioEffect("Test EQ", 400, 200)
        d.add_jsui("eq", [10, 10, 300, 120],
                   js_code=eq_curve_js(), numinlets=3, numoutlets=4)
        spectrum_analyzer_dsp(
            d,
            "eq",
            "obj-plugin",
            source_outlet=0,
            num_bands=4,
            id_prefix="spec",
            target_inlet=2,
            min_db=-72.0,
            max_db=0.0,
        )
        patcher = d.to_patcher()
        boxes = patcher["patcher"]["boxes"]
        lines = patcher["patcher"]["lines"]
        clip_texts = {box["box"].get("text", "") for box in boxes}
        assert "clip -72.0 0.0" in clip_texts
        assert any(
            line["patchline"]["source"] == ["spec_group", 0]
            and line["patchline"]["destination"] == ["eq", 2]
            for line in lines
        )

    def test_spectrum_dsp_supports_custom_resolution(self):
        d = AudioEffect("Test EQ", 400, 200)
        d.add_jsui("eq", [10, 10, 300, 120],
                   js_code=eq_curve_js(), numinlets=3, numoutlets=4)
        spectrum_analyzer_dsp(
            d,
            "eq",
            "obj-plugin",
            source_outlet=0,
            num_bands=8,
            id_prefix="specx",
            target_inlet=2,
            peak_window=256,
            q_min=4.0,
            q_max=12.0,
        )
        patcher = d.to_patcher()
        texts = {box["box"].get("text", "") for box in patcher["patcher"]["boxes"]}
        assert "zl.group 8" in texts
        assert "peakamp~ 256" in texts
        assert any(text.startswith("reson~ ") and " 4.0 " in text for text in texts)

    def test_build_with_envelope_engine_code(self):
        """Build a device using actual envelope display engine code."""
        d = AudioEffect("Test Env", 300, 150)
        d.add_jsui("env", [10, 10, 200, 80],
                   js_code=envelope_display_js(), numinlets=4)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "TestEnv.amxd")
            d.build(amxd_path)
            assert os.path.exists(amxd_path)
            js_path = os.path.join(tmpdir, "env.js")
            assert os.path.exists(js_path)

    def test_build_with_spectrum_engine_code(self):
        """Build a device using actual spectrum analyzer engine code."""
        d = AudioEffect("Test Spec", 300, 150)
        d.add_jsui("spec", [10, 10, 200, 80],
                   js_code=spectrum_analyzer_js(), numinlets=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "TestSpec.amxd")
            d.build(amxd_path)
            assert os.path.exists(amxd_path)
            js_path = os.path.join(tmpdir, "spec.js")
            assert os.path.exists(js_path)

    def test_build_with_waveform_engine_code(self):
        """Build a device using actual waveform display engine code."""
        d = AudioEffect("Test Wave", 300, 150)
        d.add_jsui("wave", [10, 10, 200, 80],
                   js_code=waveform_display_js(), numinlets=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "TestWave.amxd")
            d.build(amxd_path)
            assert os.path.exists(amxd_path)
            js_path = os.path.join(tmpdir, "wave.js")
            assert os.path.exists(js_path)

    def test_multiple_jsui_in_one_device(self):
        """Multiple jsui objects can coexist in a single device."""
        d = AudioEffect("Multi", 400, 300)
        d.add_jsui("fc", [10, 10, 150, 80],
                   js_code=filter_curve_js(), numinlets=3)
        d.add_jsui("env", [170, 10, 150, 80],
                   js_code=envelope_display_js(), numinlets=4)
        assert "fc.js" in d._js_files
        assert "env.js" in d._js_files
        with tempfile.TemporaryDirectory() as tmpdir:
            amxd_path = os.path.join(tmpdir, "Multi.amxd")
            d.build(amxd_path)
            assert os.path.exists(os.path.join(tmpdir, "fc.js"))
            assert os.path.exists(os.path.join(tmpdir, "env.js"))


class TestVelocityCurveEngine:
    def test_returns_string(self):
        js = velocity_curve_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = velocity_curve_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = velocity_curve_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = velocity_curve_display_js()
        assert "inlets = 1;" in js

    def test_declares_outlets(self):
        js = velocity_curve_display_js()
        assert "outlets = 5;" in js

    def test_inlet_count_metadata(self):
        assert VELOCITY_CURVE_INLETS == 1

    def test_outlet_count_metadata(self):
        assert VELOCITY_CURVE_OUTLETS == 5

    def test_contains_onclick(self):
        js = velocity_curve_display_js()
        assert "function onclick" in js

    def test_contains_ondrag(self):
        js = velocity_curve_display_js()
        assert "function ondrag" in js

    def test_contains_outlet_calls(self):
        js = velocity_curve_display_js()
        assert "outlet(0" in js
        assert "outlet(4" in js

    def test_custom_bg_color(self):
        js = velocity_curve_display_js(bg_color="0.1, 0.1, 0.1, 1.0")
        assert "0.1, 0.1, 0.1, 1.0" in js

    def test_custom_curve_color(self):
        js = velocity_curve_display_js(curve_color="1.0, 0.0, 0.5, 1.0")
        assert "1.0, 0.0, 0.5, 1.0" in js

    def test_custom_point_color(self):
        js = velocity_curve_display_js(point_color="0.8, 0.8, 0.0, 1.0")
        assert "0.8, 0.8, 0.0, 1.0" in js

    def test_contains_control_points(self):
        js = velocity_curve_display_js()
        assert "pt_x1" in js
        assert "pt_y1" in js
        assert "pt_x2" in js
        assert "pt_y2" in js

    def test_contains_msg_list(self):
        js = velocity_curve_display_js()
        assert "function msg_list" in js

    def test_mouse_up_in_ondrag(self):
        js = velocity_curve_display_js()
        assert "but === 0" in js

    def test_no_es6_let(self):
        import re
        js = velocity_curve_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = velocity_curve_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"

    def test_no_es6_const(self):
        import re
        js = velocity_curve_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])const\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'const' found: {stripped}"

    def test_contains_mgraphics_redraw(self):
        js = velocity_curve_display_js()
        assert "mgraphics.redraw()" in js


class TestWavetableDisplayEngine:
    def test_returns_string(self):
        js = wavetable_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = wavetable_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = wavetable_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = wavetable_display_js()
        assert "inlets = 1;" in js

    def test_declares_outlets(self):
        js = wavetable_display_js()
        assert "outlets = 0;" in js

    def test_inlet_count_metadata(self):
        assert WAVETABLE_DISPLAY_INLETS == 1

    def test_outlet_count_metadata(self):
        assert WAVETABLE_DISPLAY_OUTLETS == 0

    def test_contains_msg_list(self):
        js = wavetable_display_js()
        assert "function msg_list" in js

    def test_custom_bg_color(self):
        js = wavetable_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_custom_line_color(self):
        js = wavetable_display_js(line_color="0.9, 0.3, 0.3, 1.0")
        assert "0.9, 0.3, 0.3, 1.0" in js

    def test_custom_fill_color(self):
        js = wavetable_display_js(fill_color="0.9, 0.3, 0.3, 0.1")
        assert "0.9, 0.3, 0.3, 0.1" in js

    def test_contains_samples_array(self):
        js = wavetable_display_js()
        assert "samples" in js
        assert "num_samples" in js

    def test_contains_line_draw(self):
        js = wavetable_display_js()
        assert "line_to" in js
        assert "move_to" in js

    def test_no_es6_let(self):
        import re
        js = wavetable_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = wavetable_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"

    def test_contains_mgraphics_redraw(self):
        js = wavetable_display_js()
        assert "mgraphics.redraw()" in js


class TestResonanceBankEngine:
    def test_returns_string(self):
        js = resonance_bank_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = resonance_bank_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = resonance_bank_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = resonance_bank_display_js()
        assert "inlets = 1;" in js

    def test_declares_outlets(self):
        js = resonance_bank_display_js()
        assert "outlets = 0;" in js

    def test_inlet_count_metadata(self):
        assert RESONANCE_BANK_INLETS == 1

    def test_outlet_count_metadata(self):
        assert RESONANCE_BANK_OUTLETS == 0

    def test_contains_msg_list(self):
        js = resonance_bank_display_js()
        assert "function msg_list" in js

    def test_custom_bg_color(self):
        js = resonance_bank_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_custom_bar_color(self):
        js = resonance_bank_display_js(bar_color="0.2, 0.6, 0.9, 1.0")
        assert "0.2" in js
        assert "0.6" in js
        assert "0.9" in js

    def test_custom_hot_color(self):
        js = resonance_bank_display_js(hot_color="1.0, 0.2, 0.0, 1.0")
        assert "1.0" in js
        assert "0.2" in js

    def test_contains_freq_and_gain_arrays(self):
        js = resonance_bank_display_js()
        assert "freqs" in js
        assert "gains" in js
        assert "num_bands" in js

    def test_contains_log_scale(self):
        js = resonance_bank_display_js()
        assert "Math.log" in js

    def test_contains_bar_drawing(self):
        js = resonance_bank_display_js()
        assert "mgraphics.rectangle" in js

    def test_contains_color_interpolation(self):
        js = resonance_bank_display_js()
        assert "lerp" in js

    def test_no_es6_let(self):
        import re
        js = resonance_bank_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = resonance_bank_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"

    def test_contains_mgraphics_redraw(self):
        js = resonance_bank_display_js()
        assert "mgraphics.redraw()" in js


class TestSidechainDisplay:
    def test_returns_string(self):
        js = sidechain_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = sidechain_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = sidechain_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = sidechain_display_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = sidechain_display_js()
        assert "outlets = 0;" in js

    def test_inlet_count_metadata(self):
        assert SIDECHAIN_DISPLAY_INLETS == 2

    def test_outlet_count_metadata(self):
        assert SIDECHAIN_DISPLAY_OUTLETS == 0

    def test_handles_msg_float(self):
        js = sidechain_display_js()
        assert "function msg_float" in js

    def test_contains_level_state(self):
        js = sidechain_display_js()
        assert "level" in js

    def test_contains_threshold_state(self):
        js = sidechain_display_js()
        assert "threshold" in js

    def test_custom_bg_color(self):
        js = sidechain_display_js(bg_color="0.1, 0.1, 0.1, 1.0")
        assert "0.1, 0.1, 0.1, 1.0" in js

    def test_custom_bar_color(self):
        js = sidechain_display_js(bar_color="0.8, 0.4, 0.2, 1.0")
        assert "0.8, 0.4, 0.2, 1.0" in js

    def test_custom_threshold_color(self):
        js = sidechain_display_js(threshold_color="1.0, 0.0, 0.0, 0.9")
        assert "1.0, 0.0, 0.0, 0.9" in js

    def test_contains_mgraphics_redraw(self):
        js = sidechain_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = sidechain_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = sidechain_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestSpectralDisplay:
    def test_returns_string(self):
        js = spectral_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = spectral_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = spectral_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = spectral_display_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = spectral_display_js()
        assert "outlets = 0;" in js

    def test_inlet_count_metadata(self):
        assert SPECTRAL_DISPLAY_INLETS == 2

    def test_outlet_count_metadata(self):
        assert SPECTRAL_DISPLAY_OUTLETS == 0

    def test_contains_msg_list(self):
        js = spectral_display_js()
        assert "function msg_list" in js

    def test_contains_threshold(self):
        js = spectral_display_js()
        assert "threshold" in js

    def test_contains_bins(self):
        js = spectral_display_js()
        assert "bins" in js

    def test_custom_bg_color(self):
        js = spectral_display_js(bg_color="0.1, 0.1, 0.1, 1.0")
        assert "0.1, 0.1, 0.1, 1.0" in js

    def test_custom_panel_color(self):
        js = spectral_display_js(panel_color="0.2, 0.2, 0.2, 1.0")
        assert "0.2, 0.2, 0.2, 1.0" in js

    def test_custom_bar_color(self):
        js = spectral_display_js(bar_color="0.6, 0.3, 0.9, 0.8")
        assert "0.6, 0.3, 0.9, 0.8" in js

    def test_custom_threshold_color(self):
        js = spectral_display_js(threshold_color="1.0, 0.0, 0.0, 0.9")
        assert "1.0, 0.0, 0.0, 0.9" in js

    def test_contains_mgraphics_redraw(self):
        js = spectral_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = spectral_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = spectral_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestPeakingEqDisplay:
    def test_returns_string(self):
        js = peaking_eq_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = peaking_eq_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = peaking_eq_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = peaking_eq_display_js()
        assert "inlets = 1;" in js

    def test_declares_outlets(self):
        js = peaking_eq_display_js()
        assert "outlets = 4;" in js

    def test_inlet_count_metadata(self):
        assert PEAKING_EQ_DISPLAY_INLETS == 1

    def test_outlet_count_metadata(self):
        assert PEAKING_EQ_DISPLAY_OUTLETS == 4

    def test_contains_onclick(self):
        js = peaking_eq_display_js()
        assert "function onclick" in js

    def test_contains_ondrag(self):
        js = peaking_eq_display_js()
        assert "function ondrag" in js

    def test_contains_msg_list(self):
        js = peaking_eq_display_js()
        assert "function msg_list" in js

    def test_contains_bands_array(self):
        js = peaking_eq_display_js()
        assert "bands" in js
        assert "MAX_BANDS" in js

    def test_contains_outlet_calls(self):
        js = peaking_eq_display_js()
        assert "outlet(0" in js
        assert "outlet(3" in js

    def test_mouse_up_in_ondrag(self):
        js = peaking_eq_display_js()
        assert "but === 0" in js

    def test_custom_bg_color(self):
        js = peaking_eq_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_custom_panel_color(self):
        js = peaking_eq_display_js(panel_color="0.2, 0.2, 0.2, 1.0")
        assert "0.2, 0.2, 0.2, 1.0" in js

    def test_custom_line_color(self):
        js = peaking_eq_display_js(line_color="0.9, 0.3, 0.3, 1.0")
        assert "0.9, 0.3, 0.3, 1.0" in js

    def test_custom_point_color(self):
        js = peaking_eq_display_js(point_color="0.2, 0.8, 0.5, 1.0")
        assert "0.2, 0.8, 0.5, 1.0" in js

    def test_contains_mgraphics_redraw(self):
        js = peaking_eq_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = peaking_eq_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = peaking_eq_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestStepGridDisplay:
    def test_returns_string(self):
        js = step_grid_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = step_grid_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = step_grid_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = step_grid_display_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = step_grid_display_js()
        assert "outlets = 4;" in js

    def test_inlet_count_metadata(self):
        assert STEP_GRID_DISPLAY_INLETS == 2

    def test_outlet_count_metadata(self):
        assert STEP_GRID_DISPLAY_OUTLETS == 4

    def test_default_steps(self):
        js = step_grid_display_js()
        assert "NUM_STEPS = 16" in js

    def test_custom_steps(self):
        js = step_grid_display_js(steps=32)
        assert "NUM_STEPS = 32" in js

    def test_contains_onclick(self):
        js = step_grid_display_js()
        assert "function onclick" in js

    def test_contains_msg_list(self):
        js = step_grid_display_js()
        assert "function msg_list" in js

    def test_contains_msg_int(self):
        js = step_grid_display_js()
        assert "function msg_int" in js

    def test_contains_playhead(self):
        js = step_grid_display_js()
        assert "playhead" in js

    def test_contains_outlet_calls(self):
        js = step_grid_display_js()
        assert "outlet(0" in js
        assert "outlet(3" in js

    def test_custom_bg_color(self):
        js = step_grid_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_custom_active_color(self):
        js = step_grid_display_js(active_color="0.9, 0.4, 0.1, 1.0")
        assert "0.9, 0.4, 0.1" in js

    def test_contains_mgraphics_redraw(self):
        js = step_grid_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = step_grid_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = step_grid_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestGrainDisplay:
    def test_returns_string(self):
        js = grain_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = grain_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = grain_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = grain_display_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = grain_display_js()
        assert "outlets = 1;" in js

    def test_inlet_count_metadata(self):
        assert GRAIN_DISPLAY_INLETS == 2

    def test_outlet_count_metadata(self):
        assert GRAIN_DISPLAY_OUTLETS == 1

    def test_contains_msg_list(self):
        js = grain_display_js()
        assert "function msg_list" in js

    def test_contains_msg_float(self):
        js = grain_display_js()
        assert "function msg_float" in js

    def test_contains_onclick(self):
        js = grain_display_js()
        assert "function onclick" in js

    def test_contains_ondrag(self):
        js = grain_display_js()
        assert "function ondrag" in js

    def test_contains_playhead(self):
        js = grain_display_js()
        assert "playhead" in js

    def test_contains_samples(self):
        js = grain_display_js()
        assert "samples" in js

    def test_contains_outlet_call(self):
        js = grain_display_js()
        assert "outlet(0" in js

    def test_mouse_up_in_ondrag(self):
        js = grain_display_js()
        assert "but === 0" in js

    def test_custom_bg_color(self):
        js = grain_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_custom_wave_color(self):
        js = grain_display_js(wave_color="0.8, 0.4, 0.2, 0.7")
        assert "0.8, 0.4, 0.2" in js

    def test_custom_playhead_color(self):
        js = grain_display_js(playhead_color="1.0, 0.0, 0.5, 0.9")
        assert "1.0, 0.0, 0.5, 0.9" in js

    def test_contains_mgraphics_redraw(self):
        js = grain_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = grain_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = grain_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestGridSequencerDisplay:
    def test_returns_string(self):
        js = grid_sequencer_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = grid_sequencer_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = grid_sequencer_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = grid_sequencer_display_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = grid_sequencer_display_js()
        assert "outlets = 4;" in js

    def test_inlet_count_metadata(self):
        assert GRID_SEQ_INLETS == 2

    def test_outlet_count_metadata(self):
        assert GRID_SEQ_OUTLETS == 4

    def test_custom_rows_cols(self):
        js = grid_sequencer_display_js(rows=8, cols=8)
        assert "NUM_ROWS = 8" in js
        assert "NUM_COLS = 8" in js

    def test_default_rows_cols(self):
        js = grid_sequencer_display_js()
        assert "NUM_ROWS = 12" in js
        assert "NUM_COLS = 16" in js

    def test_contains_onclick(self):
        js = grid_sequencer_display_js()
        assert "function onclick" in js

    def test_contains_msg_list(self):
        js = grid_sequencer_display_js()
        assert "function msg_list" in js

    def test_contains_msg_int(self):
        js = grid_sequencer_display_js()
        assert "function msg_int" in js

    def test_outputs_on_click(self):
        js = grid_sequencer_display_js()
        assert "outlet(0, col)" in js
        assert "outlet(1, row)" in js
        assert "outlet(2, grid_active" in js
        assert "outlet(3, grid_velocity" in js

    def test_playhead_column(self):
        js = grid_sequencer_display_js()
        assert "playhead_col" in js

    def test_custom_active_color(self):
        js = grid_sequencer_display_js(active_color="1.0, 0.5, 0.0, 1.0")
        assert "1.0, 0.5, 0.0" in js

    def test_custom_bg_color(self):
        js = grid_sequencer_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_contains_mgraphics_redraw(self):
        js = grid_sequencer_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = grid_sequencer_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = grid_sequencer_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestWavetableEditor:
    def test_returns_string(self):
        js = wavetable_editor_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = wavetable_editor_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = wavetable_editor_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = wavetable_editor_js()
        assert "inlets = 1;" in js

    def test_declares_outlets(self):
        js = wavetable_editor_js()
        assert "outlets = 1;" in js

    def test_inlet_count_metadata(self):
        assert WAVETABLE_EDITOR_INLETS == 1

    def test_outlet_count_metadata(self):
        assert WAVETABLE_EDITOR_OUTLETS == 1

    def test_contains_onclick(self):
        js = wavetable_editor_js()
        assert "function onclick" in js

    def test_contains_ondrag(self):
        js = wavetable_editor_js()
        assert "function ondrag" in js

    def test_contains_msg_list(self):
        js = wavetable_editor_js()
        assert "function msg_list" in js

    def test_outputs_samples_on_edit(self):
        js = wavetable_editor_js()
        assert "outlet(0, out)" in js

    def test_contains_edit_at(self):
        js = wavetable_editor_js()
        assert "function edit_at" in js

    def test_custom_wave_color(self):
        js = wavetable_editor_js(wave_color="0.8, 0.4, 0.2, 1.0")
        assert "0.8, 0.4, 0.2" in js

    def test_custom_edit_color(self):
        js = wavetable_editor_js(edit_color="1.0, 1.0, 0.0, 1.0")
        assert "1.0, 1.0, 0.0, 1.0" in js

    def test_custom_bg_color(self):
        js = wavetable_editor_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_contains_mgraphics_redraw(self):
        js = wavetable_editor_js()
        assert "mgraphics.redraw()" in js

    def test_samples_clamped_to_range(self):
        js = wavetable_editor_js()
        assert "Math.max(-1, Math.min(1" in js

    def test_no_es6_let(self):
        import re
        js = wavetable_editor_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = wavetable_editor_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"


class TestSpectralVocoderDisplay:
    def test_returns_string(self):
        js = spectral_vocoder_display_js()
        assert isinstance(js, str)
        assert len(js) > 100

    def test_contains_mgraphics_init(self):
        js = spectral_vocoder_display_js()
        assert "mgraphics.init()" in js

    def test_contains_paint_function(self):
        js = spectral_vocoder_display_js()
        assert "function paint()" in js

    def test_declares_inlets(self):
        js = spectral_vocoder_display_js()
        assert "inlets = 2;" in js

    def test_declares_outlets(self):
        js = spectral_vocoder_display_js()
        assert "outlets = 0;" in js

    def test_inlet_count_metadata(self):
        assert SPECTRAL_VOCODER_INLETS == 2

    def test_outlet_count_metadata(self):
        assert SPECTRAL_VOCODER_OUTLETS == 0

    def test_contains_msg_list(self):
        js = spectral_vocoder_display_js()
        assert "function msg_list" in js

    def test_handles_both_inlets(self):
        js = spectral_vocoder_display_js()
        assert "carrier_bands" in js
        assert "modulator_bands" in js

    def test_inlet_routing(self):
        js = spectral_vocoder_display_js()
        assert "inlet === 0" in js
        assert "inlet === 1" in js

    def test_custom_carrier_color(self):
        js = spectral_vocoder_display_js(carrier_color="0.2, 0.9, 0.5, 1.0")
        assert "0.2, 0.9, 0.5, 1.0" in js

    def test_custom_modulator_color(self):
        js = spectral_vocoder_display_js(modulator_color="0.9, 0.2, 0.2, 1.0")
        assert "0.9, 0.2, 0.2, 1.0" in js

    def test_custom_bg_color(self):
        js = spectral_vocoder_display_js(bg_color="0.05, 0.05, 0.06, 1.0")
        assert "0.05, 0.05, 0.06, 1.0" in js

    def test_draws_bars(self):
        js = spectral_vocoder_display_js()
        assert "carrier_h" in js
        assert "mod_h" in js

    def test_contains_mgraphics_redraw(self):
        js = spectral_vocoder_display_js()
        assert "mgraphics.redraw()" in js

    def test_no_es6_let(self):
        import re
        js = spectral_vocoder_display_js()
        pattern = re.compile(r'(?<![a-zA-Z0-9_])let\s')
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert not pattern.search(stripped), f"ES6 'let' found: {stripped}"

    def test_no_es6_arrow_functions(self):
        js = spectral_vocoder_display_js()
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            assert '=>' not in stripped, f"ES6 arrow function found: {stripped}"
