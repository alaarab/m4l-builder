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


class TestDelayTrailTide:
    """The TIDE (D4 viz bus): real delay-line energy history rendered under
    the tap lanes. set_buffers arms a 33 ms peek Task; poll_tide reads the
    2-channel ring (256 bins + head + wobble slots); tide_energy maps an age
    in ms onto the shaped bin value; freeze flips the ice state. All features
    must be clean no-ops when no feed is wired (tideL stays null)."""

    # A Buffer stub the driver swaps in: ch1 (L) carries 0.8 in the head bin
    # and 0.4 five bins older; ch2 (R) is quiet; slot 256 = head index 10,
    # slot 257 = wobble LFO 0.5.
    STUB = """
        Buffer = function (name) {
            this.peek = function (ch, start, count) {
                var out = [];
                for (var i = 0; i < count; i++) out.push(0);
                if (ch === 1) { out[10] = 0.8; out[5] = 0.4; }
                if (ch === 2) { out[10] = 0.05; }
                out[256] = 10;
                out[257] = 0.5;
                return out;
            };
        };
    """

    def test_set_buffers_arms_poll_and_peeks(self):
        result = run_jsui(delay_trail_js(), self.STUB + """
            set_buffers("---buf_et_tide");
            poll_tide();
            dump({armed: tide_poll !== null ? 1 : 0,
                  name: tide_name, head: tide_head, wob: wob_live,
                  l_head: tideL[10], r_head: tideR[10]});
        """, size=(326, 152))
        assert result.state["armed"] == 1
        assert result.state["name"] == "---buf_et_tide"
        assert result.state["head"] == 10
        assert abs(result.state["wob"] - 0.5) < 1e-6
        assert abs(result.state["l_head"] - 0.8) < 1e-6
        assert abs(result.state["r_head"] - 0.05) < 1e-6

    def test_tide_energy_age_mapping(self):
        # Head bin 10 holds 0.8 (age 0); bin 5 holds 0.4 (5 bins older). With
        # MAX_MS 2000 and 256 bins, one bin is ~7.8 ms — age 0 must read the
        # head bin, age 5*bin_ms the older one, and out-of-window ages 0.
        result = run_jsui(delay_trail_js(), self.STUB + """
            set_buffers("---t");
            poll_tide();
            var bin_ms = 2000.0 / 256;
            dump({e0: tide_energy(tideL, 0),
                  e5: tide_energy(tideL, 5 * bin_ms + 1),
                  e_out: tide_energy(tideL, 2500.0),
                  e_null: tide_energy(null, 0)});
        """, size=(326, 152))
        assert result.state["e0"] > 0.8  # 0.8 shaped by pow(.55) brightens
        assert 0 < result.state["e5"] < result.state["e0"]
        assert result.state["e_out"] == 0
        assert result.state["e_null"] == 0

    def test_paint_safe_with_and_without_tide(self):
        # paint() must not throw before any feed arrives (tideL null) NOR
        # after a poll, frozen or not; set_freeze flips the flag.
        result = run_jsui(delay_trail_js(), self.STUB + """
            paint();
            set_freeze(1);
            var f1 = frozen;
            set_buffers("---t");
            poll_tide();
            paint();
            set_freeze(0);
            paint();
            dump({f1: f1, f2: frozen, ok: 1});
        """, size=(326, 152))
        assert result.state["f1"] == 1
        assert result.state["f2"] == 0
        assert result.state["ok"] == 1

    def test_no_feed_is_clean_noop(self):
        # Without set_buffers: no Task armed, tide null, ignition zero — the
        # geometric trail still paints (backward compatible for any host that
        # never wires a viz bus).
        result = run_jsui(delay_trail_js(), """
            paint();
            dump({armed: tide_poll === null ? 0 : 1,
                  l: tideL === null ? 0 : 1,
                  ign: tide_energy(tideL, 350.0)});
        """, size=(326, 152))
        assert result.state["armed"] == 0
        assert result.state["l"] == 0
        assert result.state["ign"] == 0
