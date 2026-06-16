"""IT-67: delay-trail diagonal X/Y drag emits BOTH time and feedback.

The Echotide hero display drags on two axes at once: horizontal sets delay
time, vertical sets feedback (drag up = more). A single diagonal drag (one
onpointerdown followed by an onpointermove with BOTH x and y changed) must
fire a 'time' outlet AND a 'feedback' outlet so the product's
``route time feedback`` can drive both dials. Runs the real engine JS under
Node (skipped when Node isn't installed).
"""

import os

import pytest

from m4l_builder.engines.delay_trail import delay_trail_js

from .js_harness import NODE, run_jsui

pytestmark = pytest.mark.skipif(
    not (NODE and os.path.exists(NODE)), reason="node not available"
)


def _named(outlets, name):
    return [o for o in outlets if len(o) > 1 and o[1] == name]


class TestDelayTrailDiagonalDrag:
    def test_diagonal_drag_emits_both_time_and_feedback(self):
        # Down at (100,100), then move diagonally to (160, 40): +x grows time,
        # -y (drag up) grows feedback. Both axes change in ONE move.
        result = run_jsui(delay_trail_js(), """
            set_time(350.0);
            set_feedback(45.0);
            onpointerdown({x: 100, y: 100, buttons: 1});
            onpointermove({x: 160, y: 40, buttons: 1});
            dump({t: time_ms, fb: feedback_pct,
                  t0: 350.0, fb0: 45.0});
        """, size=(326, 152))
        times = _named(result.outlets, "time")
        feedbacks = _named(result.outlets, "feedback")
        assert len(times) >= 1, "diagonal drag must emit a 'time' outlet"
        assert len(feedbacks) >= 1, "diagonal drag must emit a 'feedback' outlet"
        # The single move emits exactly one of each (they fire together).
        assert len(times) == 1
        assert len(feedbacks) == 1
        # +x raised time, -y raised feedback (drag up = more).
        assert result.state["t"] > result.state["t0"]
        assert result.state["fb"] > result.state["fb0"]
        # The emitted ints track the engine's state (within a half-unit; JS
        # Math.round rounds .5 up while Python round() banker-rounds, so a value
        # landing exactly on x.5 can differ by 1 — that's a harness rounding
        # artifact, not an engine bug).
        assert abs(times[0][2] - result.state["t"]) <= 0.5
        assert abs(feedbacks[0][2] - result.state["fb"]) <= 0.5

    def test_opt_click_toggles_pingpong_without_moving_pad(self):
        # Opt-click flips PING-PONG (the trail visualises it) and leaves the
        # time/feedback pad untouched; a normal drag never touches ping-pong.
        result = run_jsui(delay_trail_js(), """
            set_time(350.0); set_feedback(45.0); set_pingpong(0);
            onpointerdown({x: 120, y: 80, altKey: 1});
            var p1 = pingpong, t1 = time_ms, f1 = feedback_pct;
            onpointerup({x: 120, y: 80});
            onpointerdown({x: 120, y: 80, altKey: 1});
            dump({p1: p1, p2: pingpong, t1: t1, f1: f1});
        """, size=(326, 152))
        assert result.state["p1"] == 1, "opt-click toggles ping-pong on"
        assert result.state["p2"] == 0, "a second opt-click toggles it off"
        assert result.state["t1"] == 350.0 and result.state["f1"] == 45.0, \
            "opt-click leaves the time/feedback pad alone"
        pps = _named(result.outlets, "pingpong")
        assert [p[2] for p in pps] == [1, 0]
        r2 = run_jsui(delay_trail_js(), """
            set_pingpong(1);
            onpointerdown({x: 100, y: 100, buttons: 1});
            onpointermove({x: 160, y: 40, buttons: 1});
            dump({p: pingpong});
        """, size=(326, 152))
        assert r2.state["p"] == 1, "a normal drag leaves ping-pong unchanged"

    def test_absolute_mapping_is_position_not_delta(self):
        # ABSOLUTE X/Y pad: the pointer POSITION sets the values, independent of
        # where the drag began. Two drags that END at the same point land on the
        # same time + feedback even though they STARTED far apart. (The old
        # relative start+delta model — which slammed the values to the rails on a
        # stray v8ui frame — would give two different results here.)
        a = run_jsui(delay_trail_js(), """
            set_time(350.0); set_feedback(45.0);
            onpointerdown({x: 40, y: 120, buttons: 1});
            onpointermove({x: 150, y: 70, buttons: 1});
            dump({t: time_ms, fb: feedback_pct});
        """, size=(326, 152))
        b = run_jsui(delay_trail_js(), """
            set_time(900.0); set_feedback(10.0);
            onpointerdown({x: 300, y: 30, buttons: 1});
            onpointermove({x: 150, y: 70, buttons: 1});
            dump({t: time_ms, fb: feedback_pct});
        """, size=(326, 152))
        # Same end point -> same mapped values regardless of start/initial state.
        assert abs(a.state["t"] - b.state["t"]) < 0.5
        assert abs(a.state["fb"] - b.state["fb"]) < 0.5
        # And the mapping matches the plot geometry: x=150 over [8 .. 318].
        # time = (150-8)/310 * 2000 ~= 916ms; fb = (136-70)/128 * 110 ~= 56.7%.
        assert 905.0 < a.state["t"] < 925.0
        assert 55.0 < a.state["fb"] < 58.0
        assert len(_named(a.outlets, "time")) == 1
        assert len(_named(a.outlets, "feedback")) == 1

    def test_drag_up_increases_feedback_drag_down_decreases(self):
        # Vertical axis polarity: up (smaller y) raises feedback, down lowers.
        up = run_jsui(delay_trail_js(), """
            set_feedback(45.0);
            onpointerdown({x: 100, y: 90, buttons: 1});
            onpointermove({x: 100, y: 20, buttons: 1});
            dump({fb: feedback_pct});
        """, size=(326, 152))
        down = run_jsui(delay_trail_js(), """
            set_feedback(45.0);
            onpointerdown({x: 100, y: 30, buttons: 1});
            onpointermove({x: 100, y: 110, buttons: 1});
            dump({fb: feedback_pct});
        """, size=(326, 152))
        assert up.state["fb"] > 45.0
        assert down.state["fb"] < 45.0

    def test_pointer_resolver_handles_localxy_property_names(self):
        # Live's v8ui exposes the object-local coords as .localX/.localY (NOT
        # .x/.y). The resolver must read those — otherwise the handler got
        # undefined and mapped to "NaN ms" (the live failure this fix targets).
        result = run_jsui(delay_trail_js(), """
            set_time(350.0); set_feedback(45.0);
            onpointerdown({localX: 100, localY: 90, buttons: 1});
            onpointermove({localX: 150, localY: 70, buttons: 1});
            dump({t: time_ms, fb: feedback_pct,
                  t_finite: isFinite(time_ms) ? 1 : 0,
                  fb_finite: isFinite(feedback_pct) ? 1 : 0});
        """, size=(326, 152))
        assert result.state["t_finite"] == 1
        assert result.state["fb_finite"] == 1
        # Same geometry as the .x/.y path: x=150 -> ~916ms, y=70 -> ~56.7%.
        assert 905.0 < result.state["t"] < 925.0
        assert 55.0 < result.state["fb"] < 58.0
        assert len(_named(result.outlets, "time")) == 1
        assert len(_named(result.outlets, "feedback")) == 1

    def test_missing_coords_never_poison_state_with_nan(self):
        # Defensive: a pointer frame with NO coordinate property at all must not
        # write NaN into time_ms/feedback_pct (the isNaN guard + fallback).
        result = run_jsui(delay_trail_js(), """
            set_time(350.0); set_feedback(45.0);
            onpointerdown({buttons: 1});
            onpointermove({buttons: 1});
            dump({t_finite: isFinite(time_ms) ? 1 : 0,
                  fb_finite: isFinite(feedback_pct) ? 1 : 0});
        """, size=(326, 152))
        assert result.state["t_finite"] == 1
        assert result.state["fb_finite"] == 1

    def test_double_click_resets_both_time_and_feedback(self):
        # Double-click the X/Y pad -> both time and feedback snap to defaults,
        # each emitted once so the routed Time/Feedback dials both reset.
        result = run_jsui(delay_trail_js(reset_time_ms=350.0,
                                         reset_feedback_pct=35.0), """
            set_time(1200.0); set_feedback(90.0);
            ondblclick(60, 60, 1, 0, 0, 0, 0, 0);
            dump({t: time_ms, fb: feedback_pct});
        """, size=(326, 152))
        assert abs(result.state["t"] - 350.0) < 1e-6
        assert abs(result.state["fb"] - 35.0) < 1e-6
        assert len(_named(result.outlets, "time")) == 1
        assert _named(result.outlets, "time")[0][2] == 350
        assert len(_named(result.outlets, "feedback")) == 1
        assert _named(result.outlets, "feedback")[0][2] == 35
