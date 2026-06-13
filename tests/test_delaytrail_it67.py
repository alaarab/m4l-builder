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
        # The emitted ints match the engine's rounded state.
        assert times[0][2] == round(result.state["t"])
        assert feedbacks[0][2] == round(result.state["fb"])

    def test_pure_horizontal_drag_still_moves_feedback_only_by_zero(self):
        # Sanity: a horizontal-only move (y unchanged) emits time AND feedback
        # outlets each move (both axes are always reported), but feedback is
        # unchanged because dy == 0.
        result = run_jsui(delay_trail_js(), """
            set_time(350.0);
            set_feedback(45.0);
            onpointerdown({x: 100, y: 80, buttons: 1});
            onpointermove({x: 150, y: 80, buttons: 1});
            dump({fb: feedback_pct});
        """, size=(326, 152))
        assert result.state["fb"] == 45.0
        assert len(_named(result.outlets, "time")) == 1
        assert len(_named(result.outlets, "feedback")) == 1

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
