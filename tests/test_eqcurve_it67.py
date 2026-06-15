"""it67 — eq_curve dynamic ring-drag fix + echo-safe Motion handlers.

Node-harness behavioral tests proving:
  * the dynamic ring is hit-testable when amount == 0 (visible default offset),
  * a ring drag emits band_dynamic_amount monotonically and never flips to a
    node (band_freq / band_gain) edit,
  * ring-vs-node presses are deterministic (a press squarely on the node when
    the ring sits at the same band starts a NODE drag, not a ring drag),
  * the ring survives the amount==0 sign flip mid-drag (no glitch-out),
  * set_motion_rate / set_motion_depth are echo-safe (they never toggle the
    motion enable flag, and never fire an outlet).

Modelled on tests/test_js_behavior.py; skipped when Node isn't installed.
"""

import os

import pytest

from m4l_builder.engines.eq_curve import eq_curve_js

from .js_harness import NODE, run_jsui

pytestmark = pytest.mark.skipif(
    not (NODE and os.path.exists(NODE)), reason="node not available"
)


def _named(outlets, name):
    return [o for o in outlets if len(o) > 1 and o[1] == name]


def _non_chip(outlets):
    # chip_* = band-chip-row DISPLAY feed (Para<->LP parity), not a param echo.
    return [o for o in outlets
            if not (len(o) > 1 and str(o[1]).startswith("chip_"))]


class TestDynamicRingGrabbableAtZero:
    def test_ring_hit_testable_when_amount_zero(self):
        # Band is dynamic-enabled but its range is exactly 0. The ring must be
        # drawn + hit-testable at a visible default offset from the node (not
        # overlapping it), so it is reliably grabbable.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            // enable dynamic mode, then push the range to exactly 0
            set_dynamic_amount(0, 6.0);
            set_dynamic_amount(0, 0.0);
            var still_dyn = bands[0].dynamic;
            var nodeY = node_y_for_band(0);
            var ringY = gain_to_y(dynamic_handle_gain(band_cache[0]));
            var x = freq_to_x(1000.0);
            // a click at the ring's default-offset position resolves to the ring
            var hit_at_ring = dynamic_hit_test(x, ringY);
            // and the ring is NOT sitting on top of the node
            dump({still_dyn: still_dyn, hit_at_ring: hit_at_ring,
                  ring_off_node: Math.abs(ringY - nodeY)});
        """)
        s = result.state
        assert s["still_dyn"] == 1, "dynamic mode is sticky at amount 0"
        assert s["hit_at_ring"] == 0, "ring is grabbable at its default offset"
        assert s["ring_off_node"] > 10.0, "ring is visibly off the node"

    def test_no_rings_on_fresh_load(self):
        # Static bands with the default amount 0 must NOT show a ring (a ring on
        # every band at load would be wrong).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_dynamic_amount(0, 0.0);   // load default: 0
            var any = 0, i;
            for (i = 0; i < 8; i++) if (band_cache[i].dynamic) any = 1;
            dump({any_ring: any});
        """)
        assert result.state["any_ring"] == 0


class TestDynamicRingDragMonotonic:
    def test_ring_drag_emits_dynamic_amount_not_node_edits(self):
        # A sequence of ring drags (drag_mode 2) must emit only
        # band_dynamic_amount — never band_freq / band_gain — and the amount
        # must follow the cursor monotonically downward.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_dynamic_amount(0, 4.0);
            selected_band = 0; dragging = 1; drag_mode = 2;
            var x = freq_to_x(1000.0);
            // drag the ring downward in steps (cursor y increases -> gain falls)
            var ys = [gain_to_y(2.0), gain_to_y(0.0), gain_to_y(-3.0),
                      gain_to_y(-7.0), gain_to_y(-12.0)];
            for (var k = 0; k < ys.length; k++) handle_drag_at(x, ys[k], 1, 0, 0);
            dump({amt: bands[0].dynamic_amount});
        """)
        amts = _named(result.outlets, "band_dynamic_amount")
        assert len(amts) >= 3, "ring drag emitted dynamic amounts"
        # strictly non-increasing (monotonic downward drag)
        vals = [a[3] for a in amts]
        for a, b in zip(vals, vals[1:]):
            assert b <= a + 1e-9, f"amounts not monotonic: {vals}"
        # and NEVER flipped to a node (freq/gain) edit
        assert _named(result.outlets, "band_freq") == []
        assert _named(result.outlets, "band_gain") == []
        assert result.state["amt"] == amts[-1][3]

    def test_ring_survives_zero_crossing_without_vanishing(self):
        # Dragging the ring through amount==0 (sign flip) must keep the band's
        # ring grabbable the whole time — the reported glitch was the ring
        # disappearing mid-drag at 0.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_dynamic_amount(0, 3.0);
            selected_band = 0; dragging = 1; drag_mode = 2;
            var x = freq_to_x(1000.0);
            // land the ring exactly on the node gain -> amount == 0
            handle_drag_at(x, gain_to_y(6.0), 1, 0, 0);
            var at_zero = bands[0].dynamic_amount;
            var visible_at_zero = band_cache[0].dynamic;   // still drawn/hittable
            // keep dragging below -> negative amount, no glitch
            handle_drag_at(x, gain_to_y(0.0), 1, 0, 0);
            var below = bands[0].dynamic_amount;
            dump({at_zero: at_zero, visible_at_zero: visible_at_zero,
                  below: below});
        """)
        s = result.state
        assert abs(s["at_zero"]) < 0.2, "ring landed at ~0"
        assert s["visible_at_zero"] == 1, "ring stays drawn/hittable at 0"
        assert s["below"] < -0.5, "drag continued below 0 cleanly"


class TestRingVsNodeArbitration:
    def test_press_on_node_starts_node_drag_not_ring(self):
        # A band with a dynamic ring offset above it. A press squarely on the
        # NODE must start a NODE (gain) drag (drag_mode 1), deterministically —
        # the dead-zone prevents the ring from stealing a node press.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 0.0, 1.0, 0, 1);
            set_dynamic_amount(0, -6.0);   // ring sits BELOW the node
            var nx = freq_to_x(1000.0);
            var ny = node_y_for_band(0);
            onpointerdown({x: nx, y: ny, buttons: 1});
            dump({mode: drag_mode, dragging: dragging, sel: selected_band});
        """)
        s = result.state
        assert s["dragging"] == 1
        assert s["mode"] == 1, "press on the node => node drag, not ring"
        assert s["sel"] == 0

    def test_press_on_ring_starts_ring_drag(self):
        # A press squarely on the ring (clearly closer to it than the node)
        # starts a RING drag (drag_mode 2).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 0.0, 1.0, 0, 1);
            set_dynamic_amount(0, -12.0);   // ring far below the node
            var nx = freq_to_x(1000.0);
            var ry = gain_to_y(dynamic_handle_gain(band_cache[0]));
            onpointerdown({x: nx, y: ry, buttons: 1});
            dump({mode: drag_mode, dragging: dragging});
        """)
        s = result.state
        assert s["dragging"] == 1
        assert s["mode"] == 2, "press on the ring => ring drag"

    def test_arbitration_is_position_deterministic_at_amount_zero(self):
        # Regression for the flicker: with the ring at its default offset (amount
        # 0), the press arbitration is purely positional and stable — a sweep of
        # cursor y from the node to the ring resolves node => node, ring => ring,
        # with a single clean crossover and no oscillation. (Pointer presses can
        # coincide as double-clicks in the headless harness, so this drives the
        # arbitration helpers directly.)
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 8.0, 1.0, 0, 1);
            set_dynamic_amount(0, 6.0);
            set_dynamic_amount(0, 0.0);   // amount 0 -> default-offset ring
            var nx = freq_to_x(1000.0);
            var ny = node_y_for_band(0);
            var ry = gain_to_y(dynamic_handle_gain(band_cache[0]));
            // ring_wins() mirrors handle_press's arbitration.
            function ring_wins(x, y) {
                var hit = hit_test(x, y);
                var dh = dynamic_hit_test(x, y);
                if (dh < 0) return 0;
                if (hit < 0) return 1;
                return ring_dist_sq(dh, x, y) + 9.0 <= node_dist_sq(hit, x, y) ? 1 : 0;
            }
            var seq = [], flips = 0, prev = -1, y, w, step;
            for (step = 0; step <= 40; step++) {
                y = ny + (ry - ny) * (step / 40.0);
                w = ring_wins(nx, y);
                if (w !== prev && prev !== -1) flips += 1;
                prev = w;
                seq.push(w);
            }
            dump({at_node: ring_wins(nx, ny), at_ring: ring_wins(nx, ry),
                  flips: flips, ring_off: Math.abs(ry - ny)});
        """)
        s = result.state
        assert s["at_node"] == 0, "node position => node drag"
        assert s["at_ring"] == 1, "ring position => ring drag"
        assert s["flips"] <= 1, "single clean crossover (no flicker)"
        assert s["ring_off"] > 10.0, "ring is well clear of the node"


class TestMotionHandlersEchoSafe:
    def test_set_motion_rate_does_not_toggle_enable(self):
        # Echo-safe: setting the rate must NOT enable motion on its own, and
        # must not fire an outlet (inbound state never echoes).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            var before = bands[0].motion;
            set_motion_rate(0, 3.5);
            var after_rate = bands[0].motion;
            set_motion_depth(0, 50.0);
            var after_depth = bands[0].motion;
            dump({before: before, after_rate: after_rate,
                  after_depth: after_depth, rate: bands[0].motion_rate,
                  depth: bands[0].motion_depth, n: __captured.outlets.length});
        """)
        s = result.state
        assert s["before"] == 0
        assert s["after_rate"] == 0, "rate must not enable motion"
        assert s["after_depth"] == 0, "depth must not enable motion"
        assert abs(s["rate"] - 3.5) < 1e-6
        assert abs(s["depth"] - 50.0) < 1e-6
        assert _non_chip(result.outlets) == [], "rate/depth handlers never echo"

    def test_set_motion_owns_enable(self):
        # set_motion is the sole owner of the enable flag; it never fires an
        # outlet (no echo loop with the product's reverse route).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_motion(0, 1);
            var on = bands[0].motion;
            set_motion(0, 0);
            var off = bands[0].motion;
            dump({on: on, off: off, n: __captured.outlets.length});
        """)
        s = result.state
        assert s["on"] == 1
        assert s["off"] == 0
        assert _non_chip(result.outlets) == []

    def test_disable_motion_keeps_rate_depth_so_no_reenable(self):
        # The exact echo scenario: the product, on motion-off, would re-send the
        # band's current rate/depth. Those handlers must leave motion OFF.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            set_motion(0, 1);
            set_motion_rate(0, 2.0);
            set_motion_depth(0, 40.0);
            set_motion(0, 0);                 // user disables motion
            set_motion_rate(0, 2.0);          // product echoes current rate
            set_motion_depth(0, 40.0);        // product echoes current depth
            dump({motion: bands[0].motion});
        """)
        assert result.state["motion"] == 0, "echoed rate/depth never re-enable"
