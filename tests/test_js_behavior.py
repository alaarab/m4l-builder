"""Behavioral tests for engine JS under the Node harness.

These run the actual generated JavaScript with mocked Max globals and
assert interaction logic: gesture semantics, outlet emissions, and the
no-echo rule. Skipped when Node isn't installed.
"""

import os

import pytest

from m4l_builder.engines.eq_curve import eq_curve_js
from m4l_builder.engines.level_history import level_history_js

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
        from m4l_builder.engines.delay_trail import delay_trail_js
        result = run_jsui(delay_trail_js(), """
            set_time(350.0);
            onpointerdown({x: 100, y: 60, buttons: 1});
            onpointermove({x: 150, y: 60, buttons: 1});
            var expected = 350.0 + (50.0 / plot_w()) * MAX_MS;
            dump({t: time_ms, expected: expected});
        """, size=(326, 152))
        assert abs(result.state["t"] - result.state["expected"]) < 0.6
        emits = _named(result.outlets, "time")
        assert len(emits) == 1
        assert emits[0][2] == round(result.state["t"])

    def test_drag_clamps_and_wheel_feedback(self):
        from m4l_builder.engines.delay_trail import delay_trail_js
        result = run_jsui(delay_trail_js(), """
            set_time(350.0);
            set_feedback(45.0);
            onpointerdown({x: 100, y: 60, buttons: 1});
            onpointermove({x: -4000, y: 60, buttons: 1});
            var floor_ms = time_ms;
            onwheel(100, 60, 0, 1);
            var fb_up = feedback_pct;
            for (var i = 0; i < 100; i++) onwheel(100, 60, 0, 1);
            dump({floor_ms: floor_ms, fb_up: fb_up, fb_cap: feedback_pct});
        """, size=(326, 152))
        assert result.state["floor_ms"] == 1.0
        assert result.state["fb_up"] == 47.0
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

    def test_interactive_drag_emits_threshold_with_drag_owns_line(self):
        result = run_jsui(level_history_js(ref_db=-12.0, interactive=True), """
            onpointerdown({x: 60, y: 40, buttons: 1});
            onpointermove({x: 60, y: 70, buttons: 1});
            var mid = ref_db;
            set_ref_db(-3.0);              // must be ignored mid-drag
            var after_echo = ref_db;
            onpointerup({x: 60, y: 70, buttons: 0});
            set_ref_db(-3.0);              // applies after release
            var expected = -12.0 - (30.0 / plot_h()) * (hi_db - lo_db);
            dump({mid: mid, after_echo: after_echo, final: ref_db,
                  expected: expected});
        """, size=(208, 152))
        assert abs(result.state["mid"] - result.state["expected"]) < 0.11
        assert result.state["after_echo"] == result.state["mid"]
        assert result.state["final"] == -3.0
        emits = _named(result.outlets, "threshold")
        assert len(emits) == 1

    def test_interactive_clamps_at_zero(self):
        result = run_jsui(level_history_js(ref_db=-2.0, interactive=True), """
            onpointerdown({x: 60, y: 100, buttons: 1});
            onpointermove({x: 60, y: -900, buttons: 1});
            dump({ref: ref_db});
        """, size=(208, 152))
        assert result.state["ref"] == 0.0
