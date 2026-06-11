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
