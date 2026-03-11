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

    def test_contains_double_click_delete_and_drag_fast_path(self):
        js = eq_curve_js()
        assert "var DOUBLE_CLICK_MS = 280;" in js
        assert "var last_click_was_create = 0;" in js
        assert "function delete_band_at(idx)" in js
        assert "if (last_click_band === hit && click_ms - last_click_ms <= DOUBLE_CLICK_MS)" in js
        assert "if (!last_click_was_create)" in js
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

    def test_no_ondragend(self):
        """ondragend does not exist in jsui — use but===0 in ondrag."""
        js = eq_curve_js()
        assert "ondragend" not in js

    def test_mouse_up_in_ondrag(self):
        """ondrag checks but === 0 for mouse release."""
        js = eq_curve_js()
        assert "but === 0" in js


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
        assert "function set_latency_ms" in js
        assert "QUALITY_NAMES" in js

    def test_contains_collision_and_empty_state_support(self):
        js = linear_phase_eq_display_js()
        assert "function set_collision_mode" in js
        assert "function draw_empty_state" in js
        assert "label_overlaps" in js

    def test_contains_click_add_band_and_context_menu(self):
        js = linear_phase_eq_display_js()
        assert "function create_band_at" in js
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
        assert "mgraphics.clip();" in js
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
        assert "find_free_band" in js

    def test_excludes_allpass(self):
        js = linear_phase_eq_display_js()
        assert "AllPass" not in js
        assert "TYPE_ALLPASS" not in js

    def test_custom_badge_color(self):
        js = linear_phase_eq_display_js(badge_color="0.1, 0.2, 0.3, 0.4")
        assert "0.1, 0.2, 0.3, 0.4" in js


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
        assert "DECAY" in js

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
                                          grain_display_js)
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
