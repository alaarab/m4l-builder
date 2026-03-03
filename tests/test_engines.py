"""Tests for visual engine modules (jsui JavaScript code generators)."""
import os
import tempfile
import pytest

from m4l_builder import AudioEffect, MIDNIGHT
from m4l_builder.engines.filter_curve import filter_curve_js, FILTER_CURVE_INLETS
from m4l_builder.engines.eq_curve import eq_curve_js, EQ_CURVE_INLETS
from m4l_builder.engines.spectrum_analyzer import spectrum_analyzer_js, SPECTRUM_INLETS
from m4l_builder.engines.envelope_display import envelope_display_js, ENVELOPE_INLETS
from m4l_builder.engines.waveform_display import waveform_display_js, WAVEFORM_INLETS


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
        assert "inlets = 1;" in js

    def test_declares_outlets(self):
        js = eq_curve_js()
        assert "outlets = 4;" in js

    def test_outlet_count_metadata(self):
        from m4l_builder.engines.eq_curve import EQ_CURVE_OUTLETS
        assert EQ_CURVE_OUTLETS == 4

    def test_inlet_count_metadata(self):
        assert EQ_CURVE_INLETS == 1

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

    def test_gain_range_30db(self):
        js = eq_curve_js()
        assert "MIN_GAIN   = -30" in js
        assert "MAX_GAIN   = 30" in js

    def test_no_ondragend(self):
        """ondragend does not exist in jsui — use but===0 in ondrag."""
        js = eq_curve_js()
        assert "ondragend" not in js

    def test_mouse_up_in_ondrag(self):
        """ondrag checks but === 0 for mouse release."""
        js = eq_curve_js()
        assert "but === 0" in js


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


class TestEngineImports:
    """Test that all engines import correctly from the package."""

    def test_import_from_engines_package(self):
        from m4l_builder.engines import (filter_curve_js, eq_curve_js,
                                          envelope_display_js, spectrum_analyzer_js,
                                          waveform_display_js)
        assert callable(filter_curve_js)
        assert callable(eq_curve_js)
        assert callable(envelope_display_js)
        assert callable(spectrum_analyzer_js)
        assert callable(waveform_display_js)

    def test_import_constants_from_modules(self):
        from m4l_builder.engines.filter_curve import FILTER_CURVE_INLETS, FILTER_CURVE_OUTLETS
        from m4l_builder.engines.eq_curve import EQ_CURVE_INLETS, EQ_CURVE_OUTLETS
        from m4l_builder.engines.spectrum_analyzer import SPECTRUM_INLETS, SPECTRUM_OUTLETS
        from m4l_builder.engines.envelope_display import ENVELOPE_INLETS, ENVELOPE_OUTLETS
        from m4l_builder.engines.waveform_display import WAVEFORM_INLETS, WAVEFORM_OUTLETS
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
                   js_code=eq_curve_js(), numinlets=1, numoutlets=3)
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
