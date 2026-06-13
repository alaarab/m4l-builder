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

from .js_harness import NODE, run_jsui

pytestmark = pytest.mark.skipif(
    not (NODE and os.path.exists(NODE)), reason="node not available"
)


def _named(outlets, name):
    return [o for o in outlets if len(o) > 1 and o[1] == name]


class TestEqCurveGestures:
    def test_set_band_does_not_echo(self):
        # The no-echo rule: inbound state never fires outlets.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            dump({n: __captured.outlets.length});
        """)
        assert result.outlets == []

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
        assert result.outlets == []

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
        assert result.outlets == []

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
        assert result.outlets == []

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
        assert result.outlets == []

    def test_ring_wraps_and_guards_nonfinite(self):
        result = run_jsui(level_history_js(seconds=1.0, rate_hz=30.0), """
            for (var i = 0; i < 100; i++) levels(-20.0 - (i % 5), -2.0);
            levels("garbage", "alsogarbage");
            dump({count: count, cap: cap});
        """, size=(208, 152))
        assert result.state["cap"] == 30
        assert result.state["count"] == 30  # saturated, wrapped, no crash


class TestTransferCurveDrag:
    def test_drag_down_lowers_threshold_relative(self):
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_threshold(-12.0);
            onpointerdown({x: 60, y: 50, buttons: 1});
            onpointermove({x: 60, y: 80, buttons: 1});
            var expected = -12.0 - (30.0 / plot_h()) * (MAX_DB - MIN_DB);
            dump({thr: threshold, expected: expected});
        """, size=(132, 152))
        assert abs(result.state["thr"] - result.state["expected"]) < 0.11
        emits = _named(result.outlets, "threshold")
        assert len(emits) == 1
        assert abs(emits[0][2] - result.state["thr"]) < 0.06

    def test_drag_shift_is_fine(self):
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_threshold(-12.0);
            onpointerdown({x: 60, y: 50, buttons: 1});
            onpointermove({x: 60, y: 80, buttons: 1, shiftKey: 1});
            var coarse = (30.0 / plot_h()) * (MAX_DB - MIN_DB);
            dump({thr: threshold, fine_expected: -12.0 - coarse * 0.15});
        """, size=(132, 152))
        assert abs(result.state["thr"] - result.state["fine_expected"]) < 0.11

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
        assert result.outlets == []
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
        # press (click-to-set) + move = two emits in the absolute model
        assert len(emits) == 2
        assert abs(emits[-1][2] - result.state["mid"]) < 0.06

    def test_interactive_clamps_at_zero(self):
        result = run_jsui(level_history_js(ref_db=-2.0, interactive=True), """
            onpointerdown({x: 60, y: 100, buttons: 1});
            onpointermove({x: 60, y: -900, buttons: 1});
            dump({ref: ref_db});
        """, size=(208, 152))
        assert result.state["ref"] == 0.0


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
        assert result.outlets == []
