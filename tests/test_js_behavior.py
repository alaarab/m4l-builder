"""Behavioral tests for engine JS under the Node harness.

These run the actual generated JavaScript with mocked Max globals and
assert interaction logic: gesture semantics, outlet emissions, and the
no-echo rule. Skipped when Node isn't installed.
"""

import os

import pytest

from m4l_builder.engines.eq_curve import eq_curve_js
from m4l_builder.engines.level_history import level_history_js
from m4l_builder.engines.linear_phase_eq_display import linear_phase_eq_display_js
from m4l_builder.engines.loop_filter_curve import loop_filter_curve_js

from .js_harness import NODE, run_jsui

pytestmark = pytest.mark.skipif(
    not (NODE and os.path.exists(NODE)), reason="node not available"
)


def _named(outlets, name):
    return [o for o in outlets if len(o) > 1 and o[1] == name]


def _non_chip(outlets):
    # chip_num/chip_band/chip_sel are the band-chip-row DISPLAY feed (Para<->LP
    # parity), not a param echo — exclude them from no-echo assertions.
    return [o for o in outlets
            if not (len(o) > 1 and str(o[1]).startswith("chip_"))]


class TestEqCurveNoteNames:
    def test_note_name_maps_known_pitches(self):
        # it131: frequency readouts show the nearest musical note (Pro-Q style).
        result = run_jsui(eq_curve_js(), """
            dump({a3: note_name(220.0), a4: note_name(440.0),
                  c4: note_name(261.63), low: note_name(0.0)});
        """)
        assert result.state["a3"] == "A3"
        assert result.state["a4"] == "A4"
        assert result.state["c4"] == "C4"
        assert result.state["low"] == ""

    def test_note_label_adds_cents_when_detuned(self):
        # it132: note_label appends cents when off-pitch, hides them when in tune.
        result = run_jsui(eq_curve_js(), """
            dump({inTune: note_label(220.0), sharp: note_label(222.0),
                  low: note_label(0.0)});
        """)
        assert result.state["inTune"] == "A3"        # exact pitch -> just the note
        assert result.state["sharp"] == "A3 +16c"    # 222 Hz is ~16 cents sharp
        assert result.state["low"] == ""


class TestEqCurveGestures:
    def test_set_band_does_not_echo(self):
        # The no-echo rule: inbound state never fires outlets.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            dump({n: __captured.outlets.length});
        """)
        assert _non_chip(result.outlets) == []

    def test_double_click_on_gain_band_resets_gain_not_delete(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            var nx = freq_to_x(1000.0);
            var ny = gain_to_y(6.0);
            onpointerdown({x: nx, y: ny, buttons: 1});
            onpointerup({x: nx, y: ny, buttons: 0});
            onpointerdown({x: nx, y: ny, buttons: 1});
            dump({gain: bands[0].gain, present: bands[0].present});
        """)
        assert result.state["present"] == 1, "band must NOT be deleted"
        assert result.state["gain"] == 0.0, "double-click resets gain"
        gains = _named(result.outlets, "band_gain")
        assert [0, 0.0] == [gains[-1][2], gains[-1][3]]
        assert _named(result.outlets, "delete_band") == []

    def test_double_click_via_ondblclick_resets_too(self):
        # Legacy jsui path (ondblclick) must agree with the pointer path.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(2, 500.0, -9.0, 2.0, 0, 1);
            ondblclick(freq_to_x(500.0), gain_to_y(-9.0), 1, 0, 0, 0, 0, 0);
            dump({gain: bands[2].gain, present: bands[2].present});
        """)
        assert result.state == {"gain": 0.0, "present": 1}
        assert _named(result.outlets, "delete_band") == []

    def test_double_click_empty_plot_still_creates_band(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            ondblclick(freq_to_x(2000.0), gain_to_y(0.0), 1, 0, 0, 0, 0, 0);
            var n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) n += 1;
            dump({present_count: n});
        """)
        assert result.state["present_count"] == 1
        assert len(_named(result.outlets, "band_freq")) == 1

    def test_spectrum_grab_snaps_new_band_to_analyzer_peak(self):
        # Build an analyzer peak at 1 kHz, double-click NEAR it (850 Hz):
        # the new band should snap onto the 1 kHz resonance (Pro-Q grab).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            analyzer_enabled = 1;
            ensure_analyzer_arrays();
            var N = analyzer_display.length;
            for (var i = 0; i < N; i++) analyzer_display[i] = ANALYZER_MIN_DB;
            var pbin = Math.round((Math.log(1000.0) - LOG_MIN) / LOG_RANGE * (N - 1));
            analyzer_display[pbin] = -6.0;
            analyzer_display[pbin-1] = -14.0; analyzer_display[pbin+1] = -14.0;
            analyzer_display[pbin-2] = -26.0; analyzer_display[pbin+2] = -26.0;
            ondblclick(freq_to_x(850.0), gain_to_y(0.0), 1, 0, 0, 0, 0, 0);
            var idx = -1;
            for (var j = 0; j < num_bands; j++) if (bands[j].present) { idx = j; break; }
            dump({created_freq: bands[idx].freq});
        """)
        assert abs(result.state["created_freq"] - 1000.0) < 60.0, \
            "double-click near a peak must snap the band onto it"

    def test_spectrum_grab_no_snap_on_flat_spectrum(self):
        # No clear peak -> exact placement at the click frequency (no surprise).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            analyzer_enabled = 1;
            ensure_analyzer_arrays();
            var N = analyzer_display.length;
            for (var i = 0; i < N; i++) analyzer_display[i] = ANALYZER_MIN_DB;
            ondblclick(freq_to_x(2000.0), gain_to_y(0.0), 1, 0, 0, 0, 0, 0);
            var idx = -1;
            for (var j = 0; j < num_bands; j++) if (bands[j].present) { idx = j; break; }
            dump({created_freq: bands[idx].freq});
        """)
        assert abs(result.state["created_freq"] - 2000.0) < 120.0, \
            "flat spectrum must place the band exactly at the click"

    def test_sketch_bump_creates_a_boost_band_at_the_apex(self):
        # EQ Sketch: with sketch_mode on, dragging a bump (0 -> +9 -> 0) drops a
        # single boost band near the apex; the existing node gestures are bypassed.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_sketch(1);
            onpointerdown({x: freq_to_x(100.0), y: gain_to_y(0.0)});
            onpointermove({x: freq_to_x(300.0), y: gain_to_y(5.0), buttons: 1});
            onpointermove({x: freq_to_x(1000.0), y: gain_to_y(9.0), buttons: 1});
            onpointermove({x: freq_to_x(3000.0), y: gain_to_y(5.0), buttons: 1});
            onpointermove({x: freq_to_x(8000.0), y: gain_to_y(0.0), buttons: 1});
            onpointerup({x: freq_to_x(8000.0), y: gain_to_y(0.0)});
            var idx = -1, n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) { n += 1; if (idx < 0) idx = i; }
            dump({n: n, freq: bands[idx].freq, gain: bands[idx].gain});
        """)
        assert result.state["n"] == 1, "a single bump sketches one band"
        assert 500.0 < result.state["freq"] < 2000.0, "band lands near the apex"
        assert result.state["gain"] > 2.0, "the apex sketches a boost"
        assert len(_named(result.outlets, "band_freq")) == 1

    def test_sketch_flat_stroke_creates_nothing(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_sketch(1);
            onpointerdown({x: freq_to_x(100.0), y: gain_to_y(0.0)});
            onpointermove({x: freq_to_x(1000.0), y: gain_to_y(0.2), buttons: 1});
            onpointermove({x: freq_to_x(8000.0), y: gain_to_y(0.0), buttons: 1});
            onpointerup({x: freq_to_x(8000.0), y: gain_to_y(0.0)});
            var n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) n += 1;
            dump({n: n});
        """)
        assert result.state["n"] == 0, "a flat stroke adds no bands"

    def test_sketch_off_leaves_node_gestures_intact(self):
        # With sketch_mode off a press behaves normally (here: double-click adds).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_sketch(0);
            ondblclick(freq_to_x(2000.0), gain_to_y(0.0), 1, 0, 0, 0, 0, 0);
            var n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) n += 1;
            dump({n: n, sketching: sketching});
        """)
        assert result.state["n"] == 1, "node gestures still work when sketch is off"
        assert result.state["sketching"] == 0

    def test_option_click_toggles_enable_not_delete(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(1, 800.0, 3.0, 1.0, 0, 1);
            var nx = freq_to_x(800.0);
            var ny = gain_to_y(3.0);
            onpointerdown({x: nx, y: ny, buttons: 1, altKey: 1});
            var first = bands[1].enabled;
            onpointerup({x: nx, y: ny, buttons: 0});
            onpointerdown({x: nx, y: ny, buttons: 1, altKey: 1});
            dump({first: first, second: bands[1].enabled,
                  present: bands[1].present});
        """)
        assert result.state["present"] == 1, "opt-click must NOT delete"
        assert result.state["first"] == 0, "first opt-click disables"
        assert result.state["second"] == 1, "second opt-click re-enables"
        enables = _named(result.outlets, "band_enable")
        assert [e[2:] for e in enables] == [[1, 0], [1, 1]]

    def test_wheel_adjusts_q_and_emits(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            onpointermove({x: freq_to_x(1000.0), y: gain_to_y(6.0), buttons: 0});
            onwheel(freq_to_x(1000.0), gain_to_y(6.0), 0, 1, 0, 0, 0, 0, 0);
            dump({q: bands[0].q});
        """)
        assert result.state["q"] > 1.0
        qs = _named(result.outlets, "band_q")
        assert len(qs) == 1 and qs[0][2] == 0

    def test_wheel_on_disabled_band_is_inert(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 0);
            onpointermove({x: freq_to_x(1000.0), y: gain_to_y(6.0), buttons: 0});
            onwheel(freq_to_x(1000.0), gain_to_y(6.0), 0, 1, 0, 0, 0, 0, 0);
            dump({q: bands[0].q});
        """)
        assert result.state["q"] == 1.0
        assert _named(result.outlets, "band_q") == []

    def test_drag_emits_freq_and_gain(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 0.0, 1.0, 0, 1);
            var nx = freq_to_x(1000.0);
            var ny = gain_to_y(0.0);
            onpointerdown({x: nx, y: ny, buttons: 1});
            onpointermove({x: nx + 14, y: ny - 10, buttons: 1});
            dump({dragging: dragging, selected: selected_band});
        """)
        assert result.state["dragging"] == 1
        assert result.state["selected"] == 0
        assert len(_named(result.outlets, "band_freq")) >= 1
        assert len(_named(result.outlets, "band_gain")) >= 1


class TestEqCurveAnalyzerTilt:
    def test_slope_and_freeze_never_echo(self):
        # Display-only messages: must never fire an outlet (no-echo rule).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_analyzer_slope(4.5);
            set_analyzer_freeze(1);
            set_analyzer_freeze(0);
            update_analyzer_data([-10, -20, -30, -40]);
            dump({n: __captured.outlets.length});
        """)
        assert _non_chip(result.outlets) == []

    def test_slope_pivots_at_1k_and_clamps(self):
        result = run_jsui(eq_curve_js(), """
            set_analyzer_slope(4.5);
            var a = {slope: analyzer_slope_db_oct,
                     at1k: analyzer_slope_at(1000.0),
                     at2k: analyzer_slope_at(2000.0),
                     at500: analyzer_slope_at(500.0)};
            set_analyzer_slope(99.0);
            a.clamped = analyzer_slope_db_oct;
            set_analyzer_slope(0.0);
            a.off = analyzer_slope_at(8000.0);
            dump(a);
        """)
        assert result.state["slope"] == pytest.approx(4.5)
        assert result.state["at1k"] == pytest.approx(0.0)       # pivot
        assert result.state["at2k"] == pytest.approx(4.5)       # +1 octave
        assert result.state["at500"] == pytest.approx(-4.5)     # -1 octave
        assert result.state["clamped"] == pytest.approx(12.0)   # clamp ceiling
        assert result.state["off"] == 0.0                       # 0 = fast path

    def test_floor_bins_ignore_tilt(self):
        # A bin at the noise floor STAYS at the floor (so the tilt can't lift the
        # empty floor into a fake rising diagonal with no audio); a bin with real
        # energy gets the tilt added.
        result = run_jsui(eq_curve_js(), """
            dump({floor: analyzer_tilted_db(ANALYZER_MIN_DB, 30.0),
                  nearfloor: analyzer_tilted_db(ANALYZER_MIN_DB + 0.2, 30.0),
                  signal: analyzer_tilted_db(-30.0, 10.0),
                  min: ANALYZER_MIN_DB});
        """)
        assert result.state["floor"] == result.state["min"]      # floor stays put
        assert result.state["nearfloor"] == result.state["min"]  # within the gate
        assert result.state["signal"] == pytest.approx(-20.0)    # -30 + 10 tilt

    def test_flat_spectrum_is_suppressed(self):
        # A perfectly flat line across all bins is a no-signal artifact (drawn
        # through the tilt it becomes a fake diagonal), so analyzer_is_flat()
        # flags it; a spectrum with real structure is NOT flat.
        result = run_jsui(eq_curve_js(), """
            analyzer_display = [];
            for (var i = 0; i < 40; i++) analyzer_display.push(-40.0);  // flat
            var flat = analyzer_is_flat();
            analyzer_display = [];
            for (i = 0; i < 40; i++) analyzer_display.push(-60.0 + (i % 7) * 4.0);
            var shaped = analyzer_is_flat();   // has structure -> not flat
            dump({flat: flat, shaped: shaped});
        """)
        assert result.state["flat"] == 1
        assert result.state["shaped"] == 0

    def test_freeze_holds_the_last_frame(self):
        result = run_jsui(eq_curve_js(), """
            update_analyzer_data([-10, -10, -10, -10]);
            var before = analyzer_display[0];
            set_analyzer_freeze(1);
            update_analyzer_data([0, 0, 0, 0]);   // would move toward 0 if live
            var after = analyzer_display[0];
            set_analyzer_freeze(0);
            update_analyzer_data([0, 0, 0, 0]);   // resumes
            dump({before: before, after: after, thawed: analyzer_display[0]});
        """)
        assert result.state["after"] == result.state["before"], "frozen holds"
        assert result.state["thawed"] > result.state["before"], "thaw resumes"


class TestEqCurveDynamic:
    # Dynamic EQ detector: FFT level -> envelope -> gain offset (band_dyngain).
    _MAGS = ("var mags=[];for(var i=0;i<1024;i++)mags[i]=(i>=40&&i<46)?1.0:0.0;")

    def test_static_band_emits_no_dyngain(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            sample_rate = 48000;
            """ + self._MAGS + """
            update_dynamic_from_fft(mags);
            dump({n: __captured.outlets.length});
        """)
        assert _non_chip(result.outlets) == []

    def test_dynamic_band_compresses_on_signal(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            bands[0].dynamic = 1; bands[0].dynamic_amount = -6.0;
            sample_rate = 48000;
            """ + self._MAGS + """
            for (var f = 0; f < 40; f++) update_dynamic_from_fft(mags);
            dump({cur: bands[0].dynamic_current, env: bands[0].dynamic_env});
        """)
        assert result.state["env"] > 0.5          # envelope built up under signal
        assert result.state["cur"] < -1.0         # negative amount -> compressed
        assert len(_named(result.outlets, "band_dyngain")) >= 1

    def test_dynamic_releases_when_quiet(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            bands[0].dynamic = 1; bands[0].dynamic_amount = -6.0;
            sample_rate = 48000;
            """ + self._MAGS + """
            var quiet = []; for (var i = 0; i < 1024; i++) quiet[i] = 0.0;
            for (var f = 0; f < 40; f++) update_dynamic_from_fft(mags);
            var peak = bands[0].dynamic_current;
            for (var f = 0; f < 80; f++) update_dynamic_from_fft(quiet);
            dump({peak: peak, after: bands[0].dynamic_current});
        """)
        assert result.state["peak"] < -1.0
        assert result.state["after"] > result.state["peak"]   # released toward 0

    def test_dynamic_handle_drag_emits_band_dynamic_amount(self):
        # Dragging the dynamic ring (drag_mode 2) emits band_dynamic_amount so
        # the product can route it to the Dyn param (the Pro-Q ring-drag).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            selected_band = 0; dragging = 1; drag_mode = 2;
            // drag the ring below the node's gain -> a negative (compress) range
            handle_drag_at(freq_to_x(1000.0), gain_to_y(-6.0), 1, 0, 0);
            dump({amt: bands[0].dynamic_amount});
        """)
        amts = _named(result.outlets, "band_dynamic_amount")
        assert len(amts) >= 1
        assert amts[-1][3] < 0.0                     # a compress range was emitted
        assert result.state["amt"] == amts[-1][3]    # engine state matches the emit

    def test_dyn_probe_tracks_level(self):
        result = run_jsui(eq_curve_js(), """
            sample_rate = 48000;
            var lo = []; for (var i = 0; i < 1024; i++) lo[i] = 0.0005;
            var hi = []; for (var i = 0; i < 1024; i++) hi[i] = (i>=40&&i<46)?1.0:0.0005;
            dump({lo: dyn_probe_db(1000.0, lo), hi: dyn_probe_db(1000.0, hi)});
        """)
        assert result.state["hi"] > result.state["lo"] + 10.0


class TestEqCurveDynBufferSplit:
    # The detector reads a DEDICATED pre-EQ buffer (set_dyn_buffer) separate
    # from the post-EQ spectrum display buffer (set_analyzer_buffer), so a
    # dynamic cut can't soften itself via the post-EQ level it carved.
    _BUF = """
        var __frames = {};
        Buffer = function (nm) {
            this.peek = function () { return __frames[nm] || []; };
            this.poke = function () {};
            this.framecount = function () { return 0; };
        };
        function _fill(n, v) { var a = [], i; for (i = 0; i < n; i++) a[i] = v; return a; }
    """

    def test_detector_reads_dyn_buffer_not_display(self):
        # pre-EQ dyn buffer LOUD, post-EQ display buffer SILENT -> compresses.
        result = run_jsui(eq_curve_js(), self._BUF + """
            __frames["pre"] = _fill(512, 0.6);
            __frames["post"] = _fill(1024, 0.0005);
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            bands[0].dynamic = 1; bands[0].dynamic_amount = -8.0;
            sample_rate = 48000; analyzer_enabled = 0;
            set_analyzer_buffer("post", 1024);
            set_dyn_buffer("pre", 512);
            for (var f = 0; f < 40; f++) poll_analyzer_buffer();
            dump({cur: bands[0].dynamic_current});
        """)
        assert result.state["cur"] < -1.0

    def test_detector_falls_back_to_display_when_no_dyn_buffer(self):
        # No dyn buffer; display buffer LOUD -> still compresses (fallback).
        # Guarantees backward compatibility for other eq_curve devices.
        result = run_jsui(eq_curve_js(), self._BUF + """
            __frames["post"] = _fill(1024, 0.6);
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            bands[0].dynamic = 1; bands[0].dynamic_amount = -8.0;
            sample_rate = 48000; analyzer_enabled = 0;
            set_analyzer_buffer("post", 1024);
            for (var f = 0; f < 40; f++) poll_analyzer_buffer();
            dump({cur: bands[0].dynamic_current, dynname: dyn_buffer_name});
        """)
        assert result.state["dynname"] == ""
        assert result.state["cur"] < -1.0

    def test_set_dyn_buffer_clear_restores_fallback(self):
        # Setting then clearing ('none') falls back to the display buffer.
        result = run_jsui(eq_curve_js(), self._BUF + """
            __frames["post"] = _fill(1024, 0.6);
            __frames["pre"] = _fill(512, 0.0005);
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            bands[0].dynamic = 1; bands[0].dynamic_amount = -8.0;
            sample_rate = 48000; analyzer_enabled = 0;
            set_analyzer_buffer("post", 1024);
            set_dyn_buffer("pre", 512);
            var nameSet = dyn_buffer_name;
            set_dyn_buffer("none");
            for (var f = 0; f < 40; f++) poll_analyzer_buffer();
            dump({nameSet: nameSet, nameCleared: dyn_buffer_name,
                  cur: bands[0].dynamic_current});
        """)
        assert result.state["nameSet"] == "pre"
        assert result.state["nameCleared"] == ""
        assert result.state["cur"] < -1.0   # fell back to the loud display buffer

    def test_detector_ignores_loud_display_when_dyn_buffer_silent(self):
        # Inverse cross-check: post-EQ display LOUD, pre-EQ dyn SILENT -> the
        # detector stays quiet (it is NOT cross-wired onto the display buffer).
        result = run_jsui(eq_curve_js(), self._BUF + """
            __frames["post"] = _fill(1024, 0.6);
            __frames["pre"] = _fill(512, 0.0005);
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            bands[0].dynamic = 1; bands[0].dynamic_amount = -8.0;
            sample_rate = 48000; analyzer_enabled = 1;
            set_analyzer_buffer("post", 1024);
            set_dyn_buffer("pre", 512);
            for (var f = 0; f < 40; f++) poll_analyzer_buffer();
            dump({cur: bands[0].dynamic_current});
        """)
        assert result.state["cur"] > -0.5   # silent pre buffer -> no compression


class TestLinearPhaseGestureParity:
    # it106: bring the LP display's node gestures to Parametric-EQ parity —
    # double-click RESETS (gain bands -> 0, cut/notch -> neutral Q) and opt-click
    # TOGGLES enable, instead of both deleting. Delete stays in the right-click menu.
    _SETUP = ("set_num_bands(8);\n"
              "set_band(0, 1000.0, 6.0, 1.0, 1, 1, 0, 0, 0, 0.0, 0.0);\n"
              "rebuild_band_cache();\n"
              "var nx = freq_to_x(1000.0), ny = gain_to_y(6.0);\n")

    def test_double_click_resets_gain_not_delete(self):
        result = run_jsui(linear_phase_eq_display_js(), self._SETUP + """
            handle_double_click(nx, ny);
            dump({present: bands[0].present, gain: bands[0].gain});
        """)
        assert result.state["present"] == 1, "double-click must NOT delete"
        assert result.state["gain"] == 0.0, "double-click resets gain"
        assert len(_named(result.outlets, "band_drag_gain")) >= 1
        assert _named(result.outlets, "delete_band") == []

    def test_opt_click_toggles_enable_not_delete(self):
        result = run_jsui(linear_phase_eq_display_js(), self._SETUP + """
            handle_press(nx, ny, 1, 0, 0, 1, 0, {altKey: 1, buttons: 1});
            var first = bands[0].enabled;
            handle_press(nx, ny, 1, 0, 0, 1, 0, {altKey: 1, buttons: 1});
            dump({present: bands[0].present, first: first, second: bands[0].enabled});
        """)
        assert result.state["present"] == 1, "opt-click must NOT delete"
        assert result.state["first"] == 0, "first opt-click disables"
        assert result.state["second"] == 1, "second opt-click re-enables"
        # emit is [outlet, "context_enable", band_idx, enabled] -> check enabled.
        enables = _named(result.outlets, "context_enable")
        assert [e[3] for e in enables] == [0, 1]
        assert _named(result.outlets, "delete_band") == []

    def test_double_click_empty_still_creates_band(self):
        result = run_jsui(linear_phase_eq_display_js(), """
            set_num_bands(8);
            for (var i = 0; i < 8; i++) { bands[i].present = 0; bands[i].enabled = 0; }
            rebuild_band_cache();
            handle_double_click(freq_to_x(2000.0), gain_to_y(0.0));
            var n = 0;
            for (i = 0; i < num_bands; i++) if (bands[i].present) n += 1;
            dump({present_count: n});
        """)
        assert result.state["present_count"] >= 1

    def test_spectrum_grab_snaps_new_band_to_analyzer_peak(self):
        # Parity with the Parametric EQ: a band created near a prominent analyzer
        # peak snaps onto it (double-click at 850 Hz lands on the 1 kHz bump).
        result = run_jsui(linear_phase_eq_display_js(), """
            set_num_bands(8);
            for (var i = 0; i < 8; i++) { bands[i].present = 0; bands[i].enabled = 0; }
            rebuild_band_cache();
            analyzer_enabled = 1;
            var N = 256;
            analyzer_display = [];
            for (i = 0; i < N; i++) analyzer_display.push(ANALYZER_MIN_DB);
            var pbin = Math.round((Math.log(1000.0) - LOG_MIN) / LOG_RANGE * (N - 1));
            analyzer_display[pbin] = -6.0;
            analyzer_display[pbin-1] = -14.0; analyzer_display[pbin+1] = -14.0;
            analyzer_display[pbin-2] = -26.0; analyzer_display[pbin+2] = -26.0;
            handle_double_click(freq_to_x(850.0), gain_to_y(0.0));
            var idx = -1;
            for (i = 0; i < num_bands; i++) if (bands[i].present) { idx = i; break; }
            dump({created_freq: bands[idx].freq});
        """)
        assert abs(result.state["created_freq"] - 1000.0) < 60.0, \
            "LP band created near a peak must snap onto it"


class TestLinearPhaseAnalyzerTilt:
    # Same tilt/freeze contract as eq_curve, ported to the LP display engine.
    def test_slope_and_freeze_never_echo(self):
        result = run_jsui(linear_phase_eq_display_js(), """
            set_analyzer_slope(4.5);
            set_analyzer_freeze(1);
            set_analyzer_freeze(0);
            update_analyzer_data([-10, -20, -30, -40]);
            dump({n: __captured.outlets.length});
        """)
        assert _non_chip(result.outlets) == []

    def test_slope_pivots_at_1k_and_clamps(self):
        result = run_jsui(linear_phase_eq_display_js(), """
            set_analyzer_slope(4.5);
            var a = {at1k: analyzer_slope_at(1000.0),
                     at2k: analyzer_slope_at(2000.0),
                     at500: analyzer_slope_at(500.0)};
            set_analyzer_slope(99.0); a.clamped = analyzer_slope_db_oct;
            set_analyzer_slope(0.0); a.off = analyzer_slope_at(8000.0);
            dump(a);
        """)
        assert result.state["at1k"] == pytest.approx(0.0)
        assert result.state["at2k"] == pytest.approx(4.5)
        assert result.state["at500"] == pytest.approx(-4.5)
        assert result.state["clamped"] == pytest.approx(12.0)
        assert result.state["off"] == 0.0

    def test_floor_gate_and_flat_suppress(self):
        # Same no-signal fixes as the Parametric: a floor bin stays at the floor
        # (no tilted-diagonal), and a perfectly flat spectrum is flagged so it can
        # be skipped (reads empty) instead of drawn as a fake diagonal.
        result = run_jsui(linear_phase_eq_display_js(), """
            var a = {floor: analyzer_tilted_db(ANALYZER_MIN_DB, 30.0),
                     signal: analyzer_tilted_db(-30.0, 10.0),
                     min: ANALYZER_MIN_DB};
            analyzer_display = [];
            for (var i = 0; i < 40; i++) analyzer_display.push(-40.0);
            a.flat = analyzer_is_flat();
            analyzer_display = [];
            for (i = 0; i < 40; i++) analyzer_display.push(-60.0 + (i % 7) * 4.0);
            a.shaped = analyzer_is_flat();
            dump(a);
        """)
        assert result.state["floor"] == result.state["min"]
        assert result.state["signal"] == pytest.approx(-20.0)
        assert result.state["flat"] == 1
        assert result.state["shaped"] == 0

    def test_freeze_holds_the_last_frame(self):
        result = run_jsui(linear_phase_eq_display_js(), """
            update_analyzer_data([-10, -10, -10, -10]);
            var before = analyzer_display[0];
            set_analyzer_freeze(1);
            update_analyzer_data([0, 0, 0, 0]);
            var after = analyzer_display[0];
            dump({before: before, after: after});
        """)
        assert result.state["after"] == result.state["before"]


class TestLevelHistoryBehavior:
    def test_levels_never_fire_outlets(self):
        result = run_jsui(level_history_js(), """
            levels(-12.0, -3.0);
            levels(-6.0, -6.0);
            set_range(-48, 6);
            set_ref_db(-0.3);
            clear();
            dump({ok: 1});
        """, size=(208, 152))
        assert _non_chip(result.outlets) == []

    def test_ring_wraps_and_guards_nonfinite(self):
        result = run_jsui(level_history_js(seconds=1.0, rate_hz=30.0), """
            for (var i = 0; i < 100; i++) levels(-20.0 - (i % 5), -2.0);
            levels("garbage", "alsogarbage");
            dump({count: count, cap: cap});
        """, size=(208, 152))
        assert result.state["cap"] == 30
        assert result.state["count"] == 30  # saturated, wrapped, no crash

    def test_shift_fine_adjust_ref_line(self):
        # Shift = fine-adjust: the ceiling/threshold line eases ~15% toward the
        # cursor instead of snapping (Pro-L/Pro-C precision placement).
        plain = run_jsui(level_history_js(interactive=True, lo_db=-48, hi_db=6,
                                          ref_db=-0.3), """
            onpointerdown({y: 20, buttons: 1});
            for (var i = 0; i < 20; i++) onpointermove({y: 80, buttons: 1});
            dump({ref: ref_db});
        """, size=(208, 152))
        fine = run_jsui(level_history_js(interactive=True, lo_db=-48, hi_db=6,
                                         ref_db=-0.3), """
            onpointerdown({y: 20, buttons: 1, shiftKey: 1});
            for (var i = 0; i < 20; i++) onpointermove({y: 80, buttons: 1, shiftKey: 1});
            dump({ref: ref_db});
        """, size=(208, 152))
        start = -0.3
        dp = plain.state["ref"] - start
        df = fine.state["ref"] - start
        assert abs(df) < abs(dp)
        assert 0.15 < (df / dp) < 0.25   # ~1/5th, STABLE after 20 moves


class TestTransferCurveDrag:
    def test_drag_sets_threshold_absolute(self):
        # ABSOLUTE: the threshold follows the cursor's output-axis level.
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_threshold(-12.0);
            onpointerdown({x: 60, y: 50, buttons: 1});
            onpointermove({x: 60, y: 80, buttons: 1});
            var lo_y = threshold;
            onpointermove({x: 60, y: 30, buttons: 1});   // higher on screen
            var hi_y = threshold;
            var expected80 = clamp(MIN_DB + ((plot_b() - 80) / plot_h()) * (MAX_DB - MIN_DB), MIN_DB, 0.0);
            dump({lo_y: lo_y, hi_y: hi_y, expected80: expected80});
        """, size=(132, 152))
        assert abs(result.state["lo_y"] - result.state["expected80"]) < 0.11
        assert result.state["hi_y"] > result.state["lo_y"]   # drag up -> higher thr
        emits = _named(result.outlets, "threshold")
        assert len(emits) == 2
        assert abs(emits[-1][2] - result.state["hi_y"]) < 0.06

    def test_double_click_resets_threshold(self):
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(reset_db=0.0), """
            set_threshold(-30.0);
            ondblclick(60, 80, 1, 0, 0, 0, 0, 0);
            dump({after: threshold});
        """, size=(132, 152))
        assert result.state["after"] == 0.0
        emits = _named(result.outlets, "threshold")
        assert len(emits) == 1 and emits[0][2] == 0.0
        # configurable reset target (Ceiling resets its ceiling to -0.3)
        r2 = run_jsui(transfer_curve_js(reset_db=-0.3), """
            set_threshold(-30.0);
            ondblclick(60, 80, 1, 0, 0, 0, 0, 0);
            dump({after: threshold});
        """, size=(132, 152))
        assert abs(r2.state["after"] - (-0.3)) < 1e-6

    def test_drag_clamps_to_zero_and_floor(self):
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_threshold(-3.0);
            onpointerdown({x: 60, y: 100, buttons: 1});
            onpointermove({x: 60, y: -400, buttons: 1});
            var top = threshold;
            onpointermove({x: 60, y: 900, buttons: 1});
            dump({top: top, floor: threshold});
        """, size=(132, 152))
        assert result.state["top"] == 0.0
        assert result.state["floor"] == -60.0

    def test_wheel_steps_ratio_and_clamps(self):
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_ratio(2.0);
            onwheel(60, 60, 0, 1, 0, 0);
            var up = ratio;
            onwheel(60, 60, 0, 1, 0, 1);
            var fine = ratio;
            for (var i = 0; i < 200; i++) onwheel(60, 60, 0, -1, 0, 0);
            dump({up: up, fine: fine, floor: ratio});
        """, size=(132, 152))
        assert abs(result.state["up"] - 2.2) < 1e-6
        assert abs(result.state["fine"] - 2.25) < 1e-6
        assert result.state["floor"] == 1.0

    def test_horizontal_drag_sets_ratio(self):
        # 2-axis pad: horizontal drag = ratio (relative to the press point).
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_ratio(2.0);
            onpointerdown({x: 40, y: 60, buttons: 1});
            onpointermove({x: 90, y: 60, buttons: 1});   // drag right -> more ratio
            var up = ratio;
            onpointermove({x: 10, y: 60, buttons: 1});   // drag left -> less ratio
            dump({up: up, down: ratio});
        """, size=(132, 152))
        assert result.state["up"] > 2.0
        assert result.state["down"] < result.state["up"]
        assert len(_named(result.outlets, "ratio")) >= 1

    def test_shift_fine_adjust_threshold(self):
        # Shift = fine-adjust: the threshold moves 1/5th of the cursor distance
        # FROM THE PRESS, and (critically) stays there over many move events
        # rather than creeping to the cursor (relative-to-start, not a lag).
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        plain = run_jsui(transfer_curve_js(), """
            set_threshold(-12.0);
            onpointerdown({x: 60, y: 50, buttons: 1});
            for (var i = 0; i < 20; i++) onpointermove({x: 60, y: 95, buttons: 1});
            dump({thr: threshold});
        """, size=(132, 152))
        fine = run_jsui(transfer_curve_js(), """
            set_threshold(-12.0);
            onpointerdown({x: 60, y: 50, buttons: 1, shiftKey: 1});
            for (var i = 0; i < 20; i++) onpointermove({x: 60, y: 95, buttons: 1, shiftKey: 1});
            dump({thr: threshold});
        """, size=(132, 152))
        start = -12.0
        dp = plain.state["thr"] - start
        df = fine.state["thr"] - start
        assert abs(df) < abs(dp)                    # fine moves less
        assert 0.15 < (df / dp) < 0.25              # ~1/5th, STABLE after 20 moves

    def test_shift_fine_adjust_ratio(self):
        # Shift slows the per-pixel ratio rate to 15% for fine control.
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        plain = run_jsui(transfer_curve_js(), """
            set_ratio(2.0);
            onpointerdown({x: 40, y: 60, buttons: 1});
            onpointermove({x: 90, y: 60, buttons: 1});
            dump({r: ratio});
        """, size=(132, 152))
        fine = run_jsui(transfer_curve_js(), """
            set_ratio(2.0);
            onpointerdown({x: 40, y: 60, buttons: 1, shiftKey: 1});
            onpointermove({x: 90, y: 60, buttons: 1, shiftKey: 1});
            dump({r: ratio});
        """, size=(132, 152))
        dp = plain.state["r"] - 2.0
        df = fine.state["r"] - 2.0
        assert df > 0 and df < dp
        assert 0.15 < (df / dp) < 0.25

    def test_vertical_drag_leaves_ratio_untouched(self):
        # A pure vertical (threshold) drag must not nudge ratio.
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_ratio(4.0);
            onpointerdown({x: 60, y: 40, buttons: 1});
            onpointermove({x: 60, y: 110, buttons: 1});
            dump({after: ratio});
        """, size=(132, 152))
        assert result.state["after"] == 4.0
        assert len(_named(result.outlets, "ratio")) == 0

    def test_ratio_drag_disabled_for_limiter(self):
        # Limiters (fixed ratio) pass ratio_drag=False -> horizontal drag inert.
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(ratio_drag=False), """
            set_ratio(20.0);
            onpointerdown({x: 40, y: 60, buttons: 1});
            onpointermove({x: 100, y: 60, buttons: 1});
            dump({after: ratio});
        """, size=(132, 152))
        assert result.state["after"] == 20.0
        assert len(_named(result.outlets, "ratio")) == 0


class TestWaveshapeScopeTrigger:
    def test_trigger_slice_starts_at_rising_zero_cross(self):
        # it130: the live scope triggers on a rising zero-crossing so the trace
        # is phase-stable. trigger_slice is pure (no Buffer) -> Node-testable.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            // A sine phase-shifted so its first rising zero-cross is a few
            // samples in (raw[2]<0, raw[3]>=0). Length > WAVE_WIN so we slice.
            var raw = [], k;
            for (k = 0; k < WAVE_WIN + 80; k++) raw.push(Math.sin((k - 3) * 0.05));
            var sl = trigger_slice(raw);
            dump({len: sl.length, first: sl[0], second: sl[1], startNeg: raw[2]});
        """, size=(296, 152))
        assert result.state["len"] == 512                 # sliced to WAVE_WIN
        assert result.state["startNeg"] < 0.0             # the sample before is negative
        assert result.state["first"] >= 0.0               # slice starts at/after the cross
        assert abs(result.state["first"]) < 0.06          # ...right at zero
        assert result.state["second"] > result.state["first"]   # rising

    def test_trigger_slice_falls_back_when_no_cross(self):
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            var raw = [], k;
            for (k = 0; k < WAVE_WIN + 80; k++) raw.push(0.5);  // all positive
            var sl = trigger_slice(raw);
            dump({len: sl.length, first: sl[0]});
        """, size=(296, 152))
        assert result.state["len"] == 512
        assert abs(result.state["first"] - 0.5) < 1e-9     # started at index 0


class TestWaveshapeDrag:
    def test_drag_up_adds_drive_at_documented_scale(self):
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_drive(6.0);
            onpointerdown({x: 60, y: 100, buttons: 1});
            onpointermove({x: 60, y: 80, buttons: 1});
            dump({drive: drive_db});
        """, size=(180, 152))
        assert abs(result.state["drive"] - 12.0) < 1e-6  # 20px * 0.3
        emits = _named(result.outlets, "drive")
        assert len(emits) == 1 and abs(emits[0][2] - 12.0) < 1e-6

    def test_drag_zone_boundary_emits_split_and_resizes_zone(self):
        # Heat "cool & colorful" finale: grab a zone divider and drag it to
        # resize which part of the wave a color/mode covers; emit the split as
        # input amplitude (-1..1) for the gen~. Press ON boundary 0 (~1/3).
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            var bx = bound_x(0), by = plot_t() + 8;
            var before = zone_bound[0];
            onpointerdown({x: bx, y: by, buttons: 1});
            var grabbed = drag_bound;
            onpointermove({x: plot_l() + 0.5 * plot_w(), y: by, buttons: 1});
            dump({before: before, after: zone_bound[0], grabbed: grabbed});
        """, size=(296, 152))
        assert result.state["grabbed"] == 0, "press on the divider grabs it"
        assert result.state["after"] > result.state["before"], "dragged right"
        emits = _named(result.outlets, "z_split_lo")
        assert len(emits) >= 1
        assert abs(emits[-1][2] - 0.0) < 0.06, "frac ~0.5 -> input ~0.0"
        assert _named(result.outlets, "drive") == [], "boundary drag is not a drive drag"

    def test_press_off_divider_is_a_drive_drag_not_boundary(self):
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            // press well away from either divider -> normal drive/bias drag
            onpointerdown({x: plot_l() + 4, y: plot_t() + 30, buttons: 1});
            dump({dragbound: drag_bound, dragging: dragging});
        """, size=(296, 152))
        assert result.state["dragbound"] == -1
        assert result.state["dragging"] == 1

    def test_horizontal_drag_sets_bias_vertical_leaves_it(self):
        # it107: the hero is a 2-axis pad — vertical = drive, horizontal = bias.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        # Pure horizontal drag (y constant): bias moves, drive stays.
        result = run_jsui(waveshape_curve_js(), """
            set_drive(0.0); set_bias(0.0);
            onpointerdown({x: 80, y: 70, buttons: 1});
            onpointermove({x: 180, y: 70, buttons: 1});
            dump({drive: drive_db, bias: bias});
        """, size=(296, 152))
        assert abs(result.state["drive"]) < 1e-6           # vertical untouched
        assert abs(result.state["bias"] - 0.8) < 1e-6      # 100px * 0.008
        assert len(_named(result.outlets, "bias")) >= 1
        # Pure vertical drag (x constant): drive moves, bias stays.
        result2 = run_jsui(waveshape_curve_js(), """
            set_drive(0.0); set_bias(0.0);
            onpointerdown({x: 150, y: 100, buttons: 1});
            onpointermove({x: 150, y: 40, buttons: 1});
            dump({drive: drive_db, bias: bias});
        """, size=(296, 152))
        assert abs(result2.state["drive"] - 18.0) < 1e-6   # 60px * 0.3
        assert abs(result2.state["bias"]) < 1e-6           # horizontal untouched

    def test_drag_clamps_and_shift_fine(self):
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_drive(6.0);
            onpointerdown({x: 60, y: 100, buttons: 1});
            onpointermove({x: 60, y: 80, buttons: 1, shiftKey: 1});
            var fine = drive_db;
            onpointermove({x: 60, y: -9000, buttons: 1});
            var top = drive_db;
            onpointermove({x: 60, y: 9000, buttons: 1});
            dump({fine: fine, top: top, floor: drive_db});
        """, size=(180, 152))
        assert abs(result.state["fine"] - 6.9) < 1e-6  # 20px * 0.045
        assert result.state["top"] == 36.0
        assert result.state["floor"] == 0.0

    def test_dropped_sample_scope_renders_toggles_and_clears(self):
        # draw_sample()/read_window() need Max's Buffer (absent in Node) so they
        # no-op; the scope paint (input line + saturated overlay) must render,
        # set_mode flips curve<->scope, and double-click clears back to the curve.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            draw_sample("nope");            // no Buffer -> stays display-only
            var after_nobuf = sample_loaded;
            set_drive(18.0); set_character(2);
            scope = [];
            for (var i = 0; i < WAVE_WIN; i++) scope[i] = Math.sin(i * 0.13) * 0.8;
            sample_loaded = 1; mode = 1; scope_frames = 100000;
            paint();                        // renders the scope + saturated line
            var scoped = mode;
            set_mode(0); paint();           // toggled back to the transfer curve
            var curved = mode;
            set_mode(1);
            scope_tick();                   // advances pos (no-ops the buffer read)
            var pos = scope_pos;
            ondblclick(60, 60, 1, 0, 0, 0, 0, 0);
            paint();
            dump({after_nobuf: after_nobuf, scoped: scoped, curved: curved,
                  pos: pos, after_clear: sample_loaded, mode_after: mode});
        """, size=(180, 152))
        assert result.state["after_nobuf"] == 0
        assert result.state["scoped"] == 1
        assert result.state["curved"] == 0
        assert result.state["pos"] > 0          # scope_tick advanced the window
        assert result.state["after_clear"] == 0
        assert result.state["mode_after"] == 0  # clear returns to the curve
        # the auto-switch + clear emit "mode" so the rail toggle stays in sync
        modes = _named(result.outlets, "mode")
        assert any(m[2] == 0 for m in modes)

    def test_sample_transfer_table_drives_curve_and_arms_dsp(self):
        # The dropped sample IS the transfer function: a 256-pt table plotted
        # input->output. sample_transfer() interpolates it (the same lookup the
        # gen~ core runs); the curve view renders it; clear emits "sample 0" so
        # the DSP shaper disarms.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            // Inject a known table: a clean -1..1 ramp (identity transfer).
            curve_tbl = [];
            for (var i = 0; i < 256; i++) curve_tbl.push(-1 + (i / 255) * 2);
            curve_n = curve_tbl.length;
            sample_loaded = 1; mode = 0; env_lin = 0.5;
            var mid = sample_transfer(0.0);     // ramp midpoint ~ 0
            var top = sample_transfer(1.0);     // ramp top ~ +1
            var bot = sample_transfer(-1.0);    // ramp bottom ~ -1
            paint();                            // draw_sample_transfer path
            // clearing disarms the DSP shaper and drops the table
            clear_sample();
            dump({mid: mid, top: top, bot: bot, curved: mode,
                  n_after: curve_n, loaded_after: sample_loaded});
        """, size=(180, 152))
        assert abs(result.state["mid"]) < 0.01      # identity at 0
        assert abs(result.state["top"] - 1.0) < 0.01
        assert abs(result.state["bot"] + 1.0) < 0.01
        assert result.state["curved"] == 0
        assert result.state["n_after"] == 0         # table dropped on clear
        assert result.state["loaded_after"] == 0
        # drop arms ("sample 1"), clear disarms ("sample 0")
        samples = _named(result.outlets, "sample")
        assert any(s[2] == 0 for s in samples)

    def test_mode_swatches_pick_palette_and_emit_dmode(self):
        # The bottom-right swatch row picks a color/distortion MODE: clicking the
        # last swatch sets dmode + emits "dmode <i>" (drives the gen + Mode param);
        # set_dmode syncs + clamps to the palette count.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_dmode(2);
            var m2 = dmode;
            paint();                       // renders palette 2 + the swatch row
            onpointerdown({x: 150, y: 130});  // click the last swatch (mode 3)
            var picked = dmode;
            paint();
            set_dmode(99);                 // clamps to the last palette
            var clamped = dmode;
            dump({m2: m2, picked: picked, clamped: clamped});
        """, size=(180, 152))
        assert result.state["m2"] == 2
        assert result.state["picked"] == 3
        assert result.state["clamped"] == 3
        emits = _named(result.outlets, "dmode")
        assert any(e[2] == 3 for e in emits)

    def test_zone_strips_cycle_and_emit_per_third(self):
        # The input axis is split into thirds; clicking a zone strip cycles that
        # third's mode (AUTO->PRISM->...) and emits "zmode_*"; set_zmode syncs.
        # zone_mode 0=AUTO (follows dmode); v -> effective mode v-1.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            paint();
            onpointerdown({x: 43, y: 119});   // click LOW (zone 0) strip -> 1
            var z0 = zone_mode[0];
            var eff0 = zone_eff(0);           // value 1 -> mode 0 (PRISM)
            set_zmode(2, 4);                  // HIGH zone -> SHRED
            var z2 = zone_mode[2];
            var eff2 = zone_eff(2);
            paint();                          // renders zone_grad (painted)
            dump({z0: z0, eff0: eff0, z2: z2, eff2: eff2,
                  painted: any_zone_painted()});
        """, size=(180, 152))
        assert result.state["z0"] == 1
        assert result.state["eff0"] == 0
        assert result.state["z2"] == 4
        assert result.state["eff2"] == 3
        assert result.state["painted"] == 1
        los = _named(result.outlets, "zmode_lo")
        assert any(e[2] == 1 for e in los)


class TestDelayTrailDrag:
    def test_horizontal_drag_maps_time_and_emits(self):
        # ABSOLUTE pad: pointer x maps directly to time along the ruler.
        from m4l_builder.engines.delay_trail import delay_trail_js
        result = run_jsui(delay_trail_js(), """
            set_time(350.0);
            onpointerdown({x: 100, y: 60, buttons: 1});
            onpointermove({x: 150, y: 60, buttons: 1});
            var expected = clamp((150 - plot_l()) / plot_w(), 0, 1) * MAX_MS;
            dump({t: time_ms, expected: expected});
        """, size=(326, 152))
        assert abs(result.state["t"] - result.state["expected"]) < 0.6
        emits = _named(result.outlets, "time")
        assert len(emits) == 1
        # within a half-unit (JS Math.round vs Python round half-rounding)
        assert abs(emits[0][2] - result.state["t"]) <= 0.5

    def test_shift_fine_adjust_time_and_feedback(self):
        # Shift = fine-adjust: time AND feedback move 1/5th of the cursor
        # distance from the press anchor, STABLE over many move events
        # (relative-to-start, completing the suite-wide tactile grammar).
        from m4l_builder.engines.delay_trail import delay_trail_js
        plain = run_jsui(delay_trail_js(), """
            set_time(200.0); set_feedback(20.0);
            onpointerdown({x: 60, y: 120, buttons: 1});
            for (var i = 0; i < 20; i++) onpointermove({x: 280, y: 40, buttons: 1});
            dump({t: time_ms, f: feedback_pct});
        """, size=(326, 152))
        fine = run_jsui(delay_trail_js(), """
            set_time(200.0); set_feedback(20.0);
            onpointerdown({x: 60, y: 120, buttons: 1, shiftKey: 1});
            for (var i = 0; i < 20; i++) onpointermove({x: 280, y: 40, buttons: 1, shiftKey: 1});
            dump({t: time_ms, f: feedback_pct});
        """, size=(326, 152))
        dpt = plain.state["t"] - 200.0
        dft = fine.state["t"] - 200.0
        assert abs(dft) < abs(dpt) and 0.15 < (dft / dpt) < 0.25
        dpf = plain.state["f"] - 20.0
        dff = fine.state["f"] - 20.0
        assert abs(dff) < abs(dpf) and 0.15 < (dff / dpf) < 0.25

    def test_drag_clamps_and_wheel_feedback(self):
        # x far off the left rail clamps time to its 1ms floor; the wheel still
        # nudges feedback +2/step and caps at 110 (absolute drag sets feedback
        # from y, so capture the post-move baseline before wheeling).
        from m4l_builder.engines.delay_trail import delay_trail_js
        result = run_jsui(delay_trail_js(), """
            set_time(350.0);
            set_feedback(45.0);
            onpointerdown({x: 100, y: 60, buttons: 1});
            onpointermove({x: -4000, y: 60, buttons: 1});
            var floor_ms = time_ms;
            var fb_after_move = feedback_pct;
            onwheel(100, 60, 0, 1);
            var fb_up = feedback_pct;
            for (var i = 0; i < 100; i++) onwheel(100, 60, 0, 1);
            dump({floor_ms: floor_ms, fb_after_move: fb_after_move,
                  fb_up: fb_up, fb_cap: feedback_pct});
        """, size=(326, 152))
        assert result.state["floor_ms"] == 1.0
        assert result.state["fb_up"] == result.state["fb_after_move"] + 2.0
        assert result.state["fb_cap"] == 110.0


class TestLevelHistoryInteractive:
    def test_default_is_display_only(self):
        result = run_jsui(level_history_js(ref_db=-20.0), """
            onpointerdown({x: 60, y: 40, buttons: 1});
            onpointermove({x: 60, y: 90, buttons: 1});
            onpointerup({x: 60, y: 90, buttons: 0});
            dump({ref: ref_db, dragging: dragging});
        """, size=(208, 152))
        assert _non_chip(result.outlets) == []
        assert result.state == {"ref": -20.0, "dragging": 0}

    def test_interactive_drag_sets_threshold_absolute_with_drag_owns_line(self):
        # ABSOLUTE: the line follows the cursor's level (y -> dB), not a delta.
        result = run_jsui(level_history_js(ref_db=-12.0, interactive=True), """
            onpointerdown({x: 60, y: 40, buttons: 1});
            onpointermove({x: 60, y: 70, buttons: 1});
            var mid = ref_db;
            set_ref_db(-3.0);              // must be ignored mid-drag
            var after_echo = ref_db;
            onpointerup({x: 60, y: 70, buttons: 0});
            set_ref_db(-3.0);              // applies after release
            var expected = clamp(y_to_db(70), lo_db, Math.min(hi_db, 0.0));
            dump({mid: mid, after_echo: after_echo, final: ref_db,
                  expected: expected});
        """, size=(208, 152))
        assert abs(result.state["mid"] - result.state["expected"]) < 0.11
        assert result.state["after_echo"] == result.state["mid"]
        assert result.state["final"] == -3.0
        emits = _named(result.outlets, "threshold")
        # press only arms (no apply); the move sets it -> one emit. (Press-apply
        # was dropped so a double-click's clicks don't pre-empt reset_ref.)
        assert len(emits) == 1
        assert abs(emits[-1][2] - result.state["mid"]) < 0.06

    def test_interactive_clamps_at_zero(self):
        result = run_jsui(level_history_js(ref_db=-2.0, interactive=True), """
            onpointerdown({x: 60, y: 100, buttons: 1});
            onpointermove({x: 60, y: -900, buttons: 1});
            dump({ref: ref_db});
        """, size=(208, 152))
        assert result.state["ref"] == 0.0

    def test_double_click_resets_ref(self):
        # Ceiling's history resets its ceiling line to -0.3 on double-click.
        result = run_jsui(level_history_js(ref_db=-0.3, interactive=True,
                                           reset_db=-0.3), """
            onpointerdown({x: 60, y: 120, buttons: 1});
            onpointermove({x: 60, y: 120, buttons: 1});   // drag it away
            var moved = ref_db;
            ondblclick(60, 60, 1, 0, 0, 0, 0, 0);
            dump({moved: moved, after: ref_db});
        """, size=(208, 152))
        assert abs(result.state["moved"] - (-0.3)) > 0.5    # drag moved it
        assert abs(result.state["after"] - (-0.3)) < 1e-6   # reset to -0.3
        emits = _named(result.outlets, "threshold")
        assert abs(emits[-1][2] - (-0.3)) < 0.06
        # non-interactive build never resets/emits
        r2 = run_jsui(level_history_js(ref_db=-12.0, reset_db=0.0), """
            ondblclick(60, 60, 1, 0, 0, 0, 0, 0);
            dump({ref: ref_db});
        """, size=(208, 152))
        assert r2.state["ref"] == -12.0 and r2.outlets == []


class TestBallisticsCurve:
    def test_envelope_rises_holds_decays(self):
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        result = run_jsui(ballistics_curve_js(attack_ms=10, release_ms=120,
                                              ratio=4), """
            var sp = spans();
            var tgt = target_gr();
            dump({
                start: env_at(0, sp, tgt),
                attack_end: env_at(sp.a, sp, tgt),
                hold: env_at(sp.a + sp.hold * 0.5, sp, tgt),
                release_end: env_at(sp.T, sp, tgt),
                tgt: tgt
            });
        """, size=(132, 68))
        s = result.state
        # GR starts at 0, reaches ~95% of target by attack end, holds at
        # the target, decays to ~5% by the end of release.
        assert s["start"] < 0.01
        assert s["attack_end"] > 0.9 * s["tgt"]
        assert abs(s["hold"] - s["tgt"]) < 0.01
        assert s["release_end"] < 0.1 * s["tgt"]
        # Representative depth = 12 dB-over * (1 - 1/ratio).
        assert abs(s["tgt"] - 12.0 * (1.0 - 1.0 / 4.0)) < 0.01

    def test_faster_attack_settles_in_less_time(self):
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        # A slow attack stretches the attack span; a fast one shrinks it.
        result = run_jsui(ballistics_curve_js(attack_ms=10, release_ms=120,
                                              ratio=4), """
            var fast = spans().a;
            set_attack(200);
            var slow = spans().a;
            set_attack(1);
            var faster = spans().a;
            dump({fast: fast, slow: slow, faster: faster});
        """, size=(132, 68))
        s = result.state
        assert s["slow"] > s["fast"] > s["faster"]

    def test_target_depth_scales_with_ratio(self):
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        result = run_jsui(ballistics_curve_js(ratio=2), """
            var t2 = target_gr();
            set_ratio(10);
            var t10 = target_gr();
            dump({t2: t2, t10: t10});
        """, size=(132, 68))
        # Higher ratio -> deeper representative gain reduction.
        assert result.state["t10"] > result.state["t2"]

    def test_interactive_left_drags_attack_right_drags_release(self):
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        # Left half = ATTACK, right half = RELEASE (matches the corner labels).
        result = run_jsui(ballistics_curve_js(attack_ms=10, release_ms=120,
                                              interactive=True), """
            onpointerdown({x: 18, y: 30, buttons: 1});
            onpointermove({x: 40, y: 30, buttons: 1});
            onpointerup({x: 40, y: 30, buttons: 0});
            var a1 = attack_ms, r1 = release_ms;
            onpointerdown({x: 55, y: 30, buttons: 1});  // further right in left half
            var a2 = attack_ms;
            onpointerup({x: 55, y: 30, buttons: 0});
            var a_before = attack_ms;
            onpointerdown({x: 110, y: 30, buttons: 1}); // right half -> release
            var r2 = release_ms, a_after = attack_ms;
            onpointerup({x: 110, y: 30, buttons: 0});
            dump({a1: a1, r1: r1, a2: a2, r2: r2,
                  a_unchanged: (a_after === a_before) ? 1 : 0});
        """, size=(132, 68))
        s = result.state
        assert 0.05 <= s["a1"] <= 250.0
        assert abs(s["r1"] - 120.0) < 1e-6       # release untouched by left drag
        assert s["a2"] > s["a1"]                  # further right -> larger attack
        assert 5.0 <= s["r2"] <= 2000.0
        assert s["a_unchanged"] == 1              # right drag leaves attack alone
        assert len(_named(result.outlets, "attack")) >= 1
        assert len(_named(result.outlets, "release")) >= 1

    def test_non_interactive_emits_nothing(self):
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        result = run_jsui(ballistics_curve_js(), """
            onpointerdown({x: 18, y: 30, buttons: 1});
            onpointermove({x: 40, y: 30, buttons: 1});
            dump({ok: 1});
        """, size=(132, 68))
        assert _non_chip(result.outlets) == []

    def test_double_click_resets_attack_and_release(self):
        # it108: double-click resets BOTH attack + release to defaults, emits both.
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        result = run_jsui(ballistics_curve_js(interactive=True, attack_ms=10,
                                              release_ms=120), """
            set_attack(99); set_release(900);
            ondblclick(50, 30, 1, 0, 0, 0, 0, 0);
            dump({attack: attack_ms, release: release_ms});
        """, size=(132, 68))
        assert result.state["attack"] == 10.0
        assert result.state["release"] == 120.0
        assert [o[2] for o in _named(result.outlets, "attack")][-1] == 10.0
        assert [o[2] for o in _named(result.outlets, "release")][-1] == 120.0

    def test_double_click_non_interactive_inert(self):
        from m4l_builder.engines.ballistics_curve import ballistics_curve_js
        result = run_jsui(ballistics_curve_js(interactive=False), """
            ondblclick(50, 30, 1, 0, 0, 0, 0, 0);
            dump({ok: 1});
        """, size=(132, 68))
        assert _non_chip(result.outlets) == []


class TestLoopFilterCurve:
    """The loop DAMP/TONE response display (Echotide's filter panel)."""

    def test_set_damp_tone_do_not_echo(self):
        result = run_jsui(loop_filter_curve_js(interactive=True), """
            set_samplerate(44100);
            set_damp(60);
            set_tone(40);
            dump({damp: damp_pct, tone: tone_pct});
        """)
        assert _non_chip(result.outlets) == []
        assert abs(result.state["damp"] - 60) < 1e-6
        assert abs(result.state["tone"] - 40) < 1e-6

    def test_drag_emits_damp_and_tone(self):
        result = run_jsui(loop_filter_curve_js(interactive=True), """
            set_samplerate(44100);
            onpointerdown({x: 300, y: 50, buttons: 1});
            dump({dragging: dragging});
        """)
        assert result.state["dragging"] == 1
        assert len(_named(result.outlets, "damp")) >= 1
        assert len(_named(result.outlets, "tone")) >= 1

    def test_dc_is_unity_and_damp_darkens_highs(self):
        result = run_jsui(loop_filter_curve_js(interactive=True), """
            set_samplerate(44100);
            set_tone(0);
            set_damp(20); var lo20 = response_db(20.0); var hi20 = response_db(15000.0);
            set_damp(80); var hi80 = response_db(15000.0);
            dump({dc: lo20, hi20: hi20, hi80: hi80});
        """)
        assert abs(result.state["dc"]) < 0.5          # ~0 dB at DC
        assert result.state["hi80"] < result.state["hi20"] - 3.0  # more damp = darker

    def test_not_interactive_does_not_drag(self):
        result = run_jsui(loop_filter_curve_js(interactive=False), """
            onpointerdown({x: 300, y: 50, buttons: 1});
            dump({dragging: dragging});
        """)
        assert result.state["dragging"] == 0
        assert _non_chip(result.outlets) == []

    def test_double_click_resets_damp_and_tone(self):
        # it108: double-click resets DAMP+TONE to their defaults, emits both.
        result = run_jsui(loop_filter_curve_js(interactive=True, damp_pct=20.0,
                                               tone_pct=0.0), """
            set_damp(77); set_tone(55);
            ondblclick(50, 50, 1, 0, 0, 0, 0, 0);
            dump({damp: damp_pct, tone: tone_pct});
        """)
        assert result.state["damp"] == 20.0
        assert result.state["tone"] == 0.0
        assert [o[2] for o in _named(result.outlets, "damp")][-1] == 20.0
        assert [o[2] for o in _named(result.outlets, "tone")][-1] == 0.0
