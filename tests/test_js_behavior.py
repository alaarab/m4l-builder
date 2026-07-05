"""Behavioral tests for engine JS under the Node harness.

These run the actual generated JavaScript with mocked Max globals and
assert interaction logic: gesture semantics, outlet emissions, and the
no-echo rule. Skipped when Node isn't installed.
"""

import os

import pytest

from m4l_builder.engines.curve_editor import curve_editor_js
from m4l_builder.engines.envelope_editor import envelope_editor_js
from m4l_builder.engines.eq_curve import eq_curve_js
from m4l_builder.engines.integrated_lufs import integrated_lufs_js
from m4l_builder.engines.level_history import level_history_js
from m4l_builder.engines.level_meter import level_meter_js
from m4l_builder.engines.linear_phase_eq_display import linear_phase_eq_display_js
from m4l_builder.engines.loop_filter_curve import loop_filter_curve_js
from m4l_builder.engines.slice_overview import slice_overview_js
from m4l_builder.engines.step_bars import step_bars_js

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


class TestLevelMeter:
    def test_levels_convert_linear_to_db(self):
        result = run_jsui(level_meter_js(), """
            levels(1.0, 0.5);
            dump({dbL: lvlL, dbR: lvlR});
        """)
        assert abs(result.state["dbL"] - 0.0) < 1e-6          # 1.0 -> 0 dBFS
        assert abs(result.state["dbR"] - (-6.0206)) < 0.01    # 0.5 -> ~-6 dB

    def test_clip_latches_above_full_scale_until_reset(self):
        result = run_jsui(level_meter_js(), """
            levels(0.5, 0.5);   var safe = clip;
            levels(1.4, 0.2);   var clipped = clip;   // L over 0 dBFS
            levels(0.1, 0.1);   var held = clip;      // back under -> stays latched
            reset_clip();
            dump({safe: safe, clipped: clipped, held: held, afterReset: clip});
        """)
        assert result.state["safe"] == 0
        assert result.state["clipped"] == 1
        assert result.state["held"] == 1
        assert result.state["afterReset"] == 0

    def test_peak_hold_rises_instantly_then_decays(self):
        result = run_jsui(level_meter_js(), """
            levels(1.0, 1.0);      var p1 = peakL;   // peak at 0 dB
            levels(0.0001, 0.0001); var p2 = peakL;  // drop -> peak decays one frame
            dump({p1: p1, p2: p2});
        """)
        assert abs(result.state["p1"] - 0.0) < 1e-6
        assert abs(result.state["p2"] - (-0.4)) < 1e-6     # decay step 0.4 dB/frame


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

    def test_alt_click_empty_snapshots_analyzer_node_click_toggles_band(self):
        # it173: alt-click on EMPTY graph captures the live analyzer as an A/B
        # reference (and clears on repeat); alt-click on a NODE still toggles that
        # band's enable (the two gestures never collide).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            analyzer_display = []; analyzer_peaks = [];
            for (var k = 0; k < 40; k++) { analyzer_display[k] = -70 + k; analyzer_peaks[k] = -70 + k; }
            var ex = freq_to_x(80.0), ey = gain_to_y(0.0);   // empty (away from the 1kHz node)
            onpointerdown({x: ex, y: ey, buttons: 1, altKey: 1});
            var snap1 = analyzer_snapshot.length, en_empty = bands[0].enabled;
            onpointerdown({x: ex, y: ey, buttons: 1, altKey: 1});   // clears
            var snap2 = analyzer_snapshot.length;
            onpointerdown({x: freq_to_x(1000.0), y: gain_to_y(6.0), buttons: 1, altKey: 1});  // the node (arms)
            onpointerup({x: freq_to_x(1000.0), y: gain_to_y(6.0), buttons: 0});               // tap -> toggles bypass
            dump({snap1: snap1, en_empty: en_empty, snap2: snap2,
                  snap3: analyzer_snapshot.length, en_node: bands[0].enabled});
        """)
        assert result.state["snap1"] == 40     # empty alt-click captured the analyzer
        assert result.state["en_empty"] == 1   # ...and did NOT toggle the band
        assert result.state["snap2"] == 0      # repeat empty alt-click cleared it
        assert result.state["snap3"] == 0      # the node alt-click did NOT snapshot
        assert result.state["en_node"] == 0    # ...it toggled the band off (unchanged path)

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

    def test_press_on_empty_plot_creates_band(self):
        # Pro-Q create gesture: a single plain press on the empty graph creates a
        # band (a double-click no longer creates — the single press already does).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            onpointerdown({x: freq_to_x(2000.0), y: gain_to_y(0.0), buttons: 1});
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
            onpointerdown({x: freq_to_x(850.0), y: gain_to_y(0.0), buttons: 1});
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
            onpointerdown({x: freq_to_x(2000.0), y: gain_to_y(0.0), buttons: 1});
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
        # With sketch_mode off a press behaves normally (here: a press creates).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_sketch(0);
            onpointerdown({x: freq_to_x(2000.0), y: gain_to_y(0.0), buttons: 1});
            var n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) n += 1;
            dump({n: n, sketching: sketching});
        """)
        assert result.state["n"] == 1, "node gestures still work when sketch is off"
        assert result.state["sketching"] == 0

    def test_sketch_descending_stroke_fits_a_low_shelf(self):
        # A stroke high at the low-freq end that returns to 0 reads as a LOW SHELF
        # (TYPE_LOSHELF=1), not a pair of edge bells — the common bass-boost move.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_sketch(1);
            onpointerdown({x: freq_to_x(30.0), y: gain_to_y(9.0)});
            onpointermove({x: freq_to_x(120.0), y: gain_to_y(7.0), buttons: 1});
            onpointermove({x: freq_to_x(500.0), y: gain_to_y(2.0), buttons: 1});
            onpointermove({x: freq_to_x(3000.0), y: gain_to_y(0.0), buttons: 1});
            onpointerup({x: freq_to_x(3000.0), y: gain_to_y(0.0)});
            var idx = -1, n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) { n += 1; if (idx < 0) idx = i; }
            dump({n: n, type: bands[idx].type, gain: bands[idx].gain});
        """)
        assert result.state["n"] == 1, "a clean step makes one shelf, not edge bells"
        assert result.state["type"] == 1, "low-end step -> LOW SHELF (type 1)"
        assert result.state["gain"] > 6.0, "shelf carries the step gain"

    def test_sketch_q_tracks_drawn_bump_width(self):
        # A narrow drawn bump sketches a TIGHT bell (high Q); a wide bump a BROAD
        # one (low Q) — the band follows the shape, not a fixed Q=1.
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_sketch(1);
            // narrow bump around 1 kHz (~1/3 octave)
            onpointerdown({x: freq_to_x(900.0), y: gain_to_y(0.0)});
            onpointermove({x: freq_to_x(950.0), y: gain_to_y(5.0), buttons: 1});
            onpointermove({x: freq_to_x(1000.0), y: gain_to_y(9.0), buttons: 1});
            onpointermove({x: freq_to_x(1060.0), y: gain_to_y(5.0), buttons: 1});
            onpointermove({x: freq_to_x(1110.0), y: gain_to_y(0.0), buttons: 1});
            onpointerup({x: freq_to_x(1110.0), y: gain_to_y(0.0)});
            // wide bump around 1 kHz (several octaves)
            onpointerdown({x: freq_to_x(200.0), y: gain_to_y(0.0)});
            onpointermove({x: freq_to_x(450.0), y: gain_to_y(5.0), buttons: 1});
            onpointermove({x: freq_to_x(1000.0), y: gain_to_y(9.0), buttons: 1});
            onpointermove({x: freq_to_x(2200.0), y: gain_to_y(5.0), buttons: 1});
            onpointermove({x: freq_to_x(5000.0), y: gain_to_y(0.0), buttons: 1});
            onpointerup({x: freq_to_x(5000.0), y: gain_to_y(0.0)});
            dump({qn: bands[0].q, qw: bands[1].q});
        """)
        assert result.state["qn"] > 2.5, "a narrow draw makes a tight bell"
        assert result.state["qw"] < 1.0, "a wide draw makes a broad bell"
        assert result.state["qn"] > result.state["qw"]

    def test_option_click_toggles_enable_not_delete(self):
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(1, 800.0, 3.0, 1.0, 0, 1);
            var nx = freq_to_x(800.0);
            var ny = gain_to_y(3.0);
            onpointerdown({x: nx, y: ny, buttons: 1, altKey: 1});  // arm
            onpointerup({x: nx, y: ny, buttons: 0});               // tap -> disables (Pro-Q Alt+click)
            var first = bands[1].enabled;
            onpointerdown({x: nx, y: ny, buttons: 1, altKey: 1});  // arm
            onpointerup({x: nx, y: ny, buttons: 0});               // tap -> re-enables
            dump({first: first, second: bands[1].enabled,
                  present: bands[1].present});
        """)
        assert result.state["present"] == 1, "opt-click must NOT delete"
        assert result.state["first"] == 0, "first opt-click disables"
        assert result.state["second"] == 1, "second opt-click re-enables"
        enables = _named(result.outlets, "band_enable")
        assert [e[2:] for e in enables] == [[1, 0], [1, 1]]

    def test_alt_drag_constrains_to_dominant_axis(self):
        # Pro-Q: Alt+DRAG locks to ONE axis by the dominant initial travel. A
        # horizontal-dominant alt-drag moves only frequency (gain held even though
        # the cursor also moved vertically); a vertical-dominant one moves only gain
        # (freq held). Neither toggles bypass (that's the Alt+CLICK tap).
        result = run_jsui(eq_curve_js(), """
            set_num_bands(8);
            set_band(0, 1000.0, 6.0, 1.0, 0, 1);
            // horizontal-dominant: big x travel, small y travel -> freq-only
            onpointerdown({x: freq_to_x(1000.0), y: gain_to_y(6.0), buttons: 1, altKey: 1});
            onpointermove({x: freq_to_x(4000.0), y: gain_to_y(7.0), buttons: 1, altKey: 1});
            onpointermove({x: freq_to_x(8000.0), y: gain_to_y(9.0), buttons: 1, altKey: 1});
            onpointerup({x: freq_to_x(8000.0), y: gain_to_y(9.0), buttons: 0});
            var hfreq = bands[0].freq, hgain = bands[0].gain, henab = bands[0].enabled;

            set_band(1, 1000.0, 0.0, 1.0, 0, 1);
            // vertical-dominant: small x travel, big y travel -> gain-only
            onpointerdown({x: freq_to_x(1000.0), y: gain_to_y(0.0), buttons: 1, altKey: 1});
            onpointermove({x: freq_to_x(1030.0), y: gain_to_y(6.0), buttons: 1, altKey: 1});
            onpointermove({x: freq_to_x(1080.0), y: gain_to_y(10.0), buttons: 1, altKey: 1});
            onpointerup({x: freq_to_x(1080.0), y: gain_to_y(10.0), buttons: 0});
            var vfreq = bands[1].freq, vgain = bands[1].gain, venab = bands[1].enabled;
            dump({hfreq: hfreq, hgain: hgain, henab: henab,
                  vfreq: vfreq, vgain: vgain, venab: venab});
        """)
        # horizontal lock: freq swept up, gain HELD at ~6 dB despite vertical travel
        assert result.state["hfreq"] > 2000.0, "alt-drag horizontal moves frequency"
        assert abs(result.state["hgain"] - 6.0) < 0.5, "gain held during a horizontal alt-drag"
        assert result.state["henab"] == 1, "alt-DRAG must NOT toggle bypass"
        # vertical lock: gain swept up, freq HELD at ~1 kHz despite horizontal travel
        assert result.state["vgain"] > 4.0, "alt-drag vertical moves gain"
        assert abs(result.state["vfreq"] - 1000.0) < 80.0, "freq held during a vertical alt-drag"
        assert result.state["venab"] == 1, "alt-DRAG must NOT toggle bypass"

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

    def test_opt_click_empty_snapshots_analyzer_node_click_toggles_band(self):
        # it174: opt-click on EMPTY graph captures the live analyzer as an A/B
        # reference (and clears on repeat); opt-click on a NODE still toggles that
        # band's enable — the two gestures never collide.
        result = run_jsui(linear_phase_eq_display_js(), self._SETUP + """
            analyzer_display = []; analyzer_peaks = [];
            for (var k = 0; k < 40; k++) { analyzer_display[k] = -70 + k; analyzer_peaks[k] = -70 + k; }
            var ex = freq_to_x(80.0), ey = gain_to_y(0.0);   // empty (away from the 1kHz node)
            handle_press(ex, ey, 1, 0, 0, 1, 0, {altKey: 1, buttons: 1});
            var snap1 = analyzer_snapshot.length, en_empty = bands[0].enabled;
            handle_press(ex, ey, 1, 0, 0, 1, 0, {altKey: 1, buttons: 1});   // clears
            var snap2 = analyzer_snapshot.length;
            handle_press(nx, ny, 1, 0, 0, 1, 0, {altKey: 1, buttons: 1});   // the node -> toggle
            dump({snap1: snap1, en_empty: en_empty, snap2: snap2,
                  snap3: analyzer_snapshot.length, en_node: bands[0].enabled});
        """)
        assert result.state["snap1"] == 40     # empty opt-click captured the analyzer
        assert result.state["en_empty"] == 1   # ...and did NOT toggle the band
        assert result.state["snap2"] == 0      # repeat empty opt-click cleared it
        assert result.state["snap3"] == 0      # the node opt-click did NOT snapshot
        assert result.state["en_node"] == 0    # ...it toggled the band off

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

    _SK = ("set_num_bands(8);\n"
           "for (var i = 0; i < 8; i++) { bands[i].present = 0; bands[i].enabled = 0; }\n"
           "rebuild_band_cache();\n"
           "set_sketch(1);\n")

    def test_sketch_bump_creates_a_boost_band_at_the_apex(self):
        # EQ Sketch ported to the LP engine: a bump stroke drops one boost band.
        result = run_jsui(linear_phase_eq_display_js(), self._SK + """
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
        assert len(_named(result.outlets, "add_band")) == 1

    def test_sketch_flat_stroke_creates_nothing(self):
        result = run_jsui(linear_phase_eq_display_js(), self._SK + """
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
        result = run_jsui(linear_phase_eq_display_js(), """
            set_num_bands(8);
            for (var i = 0; i < 8; i++) { bands[i].present = 0; bands[i].enabled = 0; }
            rebuild_band_cache();
            set_sketch(0);
            handle_double_click(freq_to_x(2000.0), gain_to_y(0.0));
            var n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) n += 1;
            dump({n: n, sketching: sketching});
        """)
        assert result.state["n"] >= 1, "node gestures still work when sketch is off"
        assert result.state["sketching"] == 0

    def test_sketch_rising_stroke_fits_a_high_shelf(self):
        # A stroke high at the HIGH-freq end (and ~0 at the low end) reads as a
        # HIGH SHELF (TYPE_HISHELF=2) — the common "air" move. (LP engine.)
        result = run_jsui(linear_phase_eq_display_js(), self._SK + """
            onpointerdown({x: freq_to_x(200.0), y: gain_to_y(0.0)});
            onpointermove({x: freq_to_x(2000.0), y: gain_to_y(2.0), buttons: 1});
            onpointermove({x: freq_to_x(8000.0), y: gain_to_y(7.0), buttons: 1});
            onpointermove({x: freq_to_x(18000.0), y: gain_to_y(9.0), buttons: 1});
            onpointerup({x: freq_to_x(18000.0), y: gain_to_y(9.0)});
            var idx = -1, n = 0;
            for (var i = 0; i < num_bands; i++) if (bands[i].present) { n += 1; if (idx < 0) idx = i; }
            dump({n: n, type: bands[idx].type, gain: bands[idx].gain});
        """)
        assert result.state["n"] == 1, "a clean step makes one shelf"
        assert result.state["type"] == 2, "high-end step -> HIGH SHELF (type 2)"
        assert result.state["gain"] > 6.0, "shelf carries the step gain"


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

    def test_knee_grip_drag_widens_knee(self):
        # knee_drag=True: grabbing the knee grip and dragging it RIGHT widens the
        # soft knee (emits "knee"); the threshold is untouched.
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(knee_drag=True), """
            set_threshold(-20.0); set_knee(4.0);
            var gi = knee_grip_in();
            var gx = in_to_x(gi), gy = out_to_y(transfer_out_db(gi));
            onpointerdown({x: gx, y: gy, buttons: 1});
            var grabbed = knee_dragging, thr0 = threshold;
            onpointermove({x: in_to_x(-10.0), y: gy, buttons: 1});  // in -10 -> knee 20
            dump({grabbed: grabbed, knee: knee, thr: threshold, thr0: thr0});
        """, size=(132, 152))
        assert result.state["grabbed"] == 1, "press on the grip starts a knee drag"
        assert abs(result.state["knee"] - 20.0) < 0.2, "knee = 2*(in - threshold)"
        assert result.state["thr"] == result.state["thr0"], "knee drag leaves threshold alone"
        assert len(_named(result.outlets, "knee")) >= 1
        assert _named(result.outlets, "threshold") == []

    def test_knee_grip_off_by_default(self):
        # Default (limiters): no knee grip, a press starts the threshold drag.
        from m4l_builder.engines.transfer_curve import transfer_curve_js
        result = run_jsui(transfer_curve_js(), """
            set_threshold(-20.0); set_knee(4.0);
            var gi = knee_grip_in();
            onpointerdown({x: in_to_x(gi), y: out_to_y(transfer_out_db(gi)), buttons: 1});
            dump({knee_dragging: knee_dragging, dragging: dragging});
        """, size=(132, 152))
        assert result.state["knee_dragging"] == 0
        assert result.state["dragging"] == 1, "without knee_drag a press is a threshold drag"

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


class TestWaveshapeMorph:
    def test_morph_crossfades_character_a_to_b(self):
        # it168: shape() crossfades character A -> B by morph. At a high drive the
        # two characters differ; morph 0 == pure A, 1 == pure B, 0.5 == midpoint.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_drive(12.0); set_character(0); set_character_b(3);  // TAPE -> FOLD
            set_morph(0);   var a = shape(0.3);
            set_morph(100); var b = shape(0.3);
            set_morph(50);  var mid = shape(0.3);
            dump({a: a, b: b, mid: mid});
        """, size=(296, 152))
        a, b, mid = result.state["a"], result.state["b"], result.state["mid"]
        assert abs(a - b) > 0.05                     # the two characters differ
        assert abs(mid - 0.5 * (a + b)) < 1e-6        # exact crossfade midpoint

    def test_morph_zero_or_same_character_is_pure_a(self):
        # morph 0 (or B == A) leaves the curve bit-identical to character A, so the
        # pre-morph behaviour + the drive-0 null are preserved.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_drive(24.0); set_character(3);            // FOLD
            var base = shape(0.4);
            set_character_b(5); set_morph(0);            // morph 0 -> still A
            var m0 = shape(0.4);
            set_character_b(3); set_morph(100);          // B == A -> still A
            var same = shape(0.4);
            dump({base: base, m0: m0, same: same});
        """, size=(296, 152))
        assert result.state["m0"] == result.state["base"]
        assert result.state["same"] == result.state["base"]

    def test_split_routes_positive_to_a_negative_to_b(self):
        # it170: bipolar SPLIT — character A shapes the positive input half, B the
        # negative half (asymmetric distortion), instead of morphing.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_drive(18.0); set_character(0); set_character_b(2);  // A=TAPE B=CLIP
            set_morph(50); set_split(1);
            // positive x -> A (TAPE), negative x -> B (CLIP), morph IGNORED.
            dump({pos: shape(0.4), a_pos: shape_ch(0.4, 0),
                  neg: shape(-0.4), b_neg: shape_ch(-0.4, 2),
                  active: morph_active() ? 1 : 0});
        """, size=(296, 152))
        assert result.state["pos"] == result.state["a_pos"]   # +half == character A
        assert result.state["neg"] == result.state["b_neg"]   # -half == character B
        assert result.state["active"] == 0                    # morph rail hidden in split

    def test_split_off_restores_morph(self):
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_drive(18.0); set_character(0); set_character_b(3);
            set_morph(100); set_split(1); var s = shape(0.3);
            set_split(0); var m = shape(0.3);                  // back to morph -> B
            dump({split_v: s, morph_v: m, b: shape_ch(0.3, 3)});
        """, size=(296, 152))
        # split used A on the +half; morph 100 uses pure B -> the two differ, and
        # morph-100 equals character B exactly.
        assert result.state["morph_v"] == result.state["b"]
        assert result.state["split_v"] != result.state["morph_v"]

    def test_top_rail_drag_sets_morph_and_emits(self):
        # it169: dragging the A<->B rail at the hero's top edge sets the morph and
        # emits "morph <pct>" (so the product routes it to the Morph dial). A press
        # at the track's horizontal midpoint -> ~50%.
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        result = run_jsui(waveshape_curve_js(), """
            set_character(0); set_character_b(3);   // distinct B -> rail is active
            var midx = (morph_track_x0() + morph_track_x1()) / 2;
            onpointerdown({x: midx, y: plot_t() + 4, buttons: 1});
            dump({m: morph, dragging_morph: drag_morph});
        """, size=(296, 152))
        assert abs(result.state["m"] - 0.5) < 0.02       # midpoint -> ~50%
        assert result.state["dragging_morph"] == 1
        emits = _named(result.outlets, "morph")
        assert len(emits) == 1
        assert abs(emits[-1][2] - 50.0) < 2.0            # ~50 (%)

    def test_rail_hidden_when_no_distinct_b_and_pad_drag_untouched(self):
        # When B == A there is nothing to morph: the rail is inert and a top-edge
        # press falls through to the drive/bias pad. And a mid-plot drag is always
        # the pad, never the morph (the rail only owns the thin top strip).
        from m4l_builder.engines.waveshape_curve import waveshape_curve_js
        inert = run_jsui(waveshape_curve_js(), """
            set_character(2); set_character_b(2);   // B == A -> rail inactive
            onpointerdown({x: 150, y: plot_t() + 4, buttons: 1});
            dump({hit: morph_strip_hit(150, plot_t() + 4), dm: drag_morph,
                  dragging: dragging});
        """, size=(296, 152))
        assert inert.state["hit"] == 0
        assert inert.state["dm"] == 0
        assert inert.state["dragging"] == 1              # fell through to the pad
        pad = run_jsui(waveshape_curve_js(), """
            set_character(0); set_character_b(3); set_morph(40);
            onpointerdown({x: 150, y: 80, buttons: 1});  // mid-plot -> drive/bias
            onpointermove({x: 200, y: 40, buttons: 1});
            dump({m: morph, dm: drag_morph});
        """, size=(296, 152))
        assert abs(pad.state["m"] - 0.40) < 1e-6         # morph untouched by the pad
        assert pad.state["dm"] == 0
        assert _named(pad.outlets, "morph") == []


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
    def test_set_character_sets_state_clamped_without_echo(self):
        from m4l_builder.engines.delay_trail import delay_trail_js
        r = run_jsui(delay_trail_js(), """
            set_character(2); var bbd = character;
            set_character(1); var tape = character;
            set_character(0); var digital = character;
            set_character(9);                       // out of range -> clamps to 2
            dump({bbd: bbd, tape: tape, digital: digital, clamped: character});
        """, size=(326, 152))
        assert r.state["bbd"] == 2 and r.state["tape"] == 1 and r.state["digital"] == 0
        assert r.state["clamped"] == 2
        assert r.outlets == []   # a display setter must never echo an outlet

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

    def test_set_slufs_tracks_and_guards_nan(self):
        # Short-term LUFS (S, 3s) — the color-coded loudness-compliance read.
        result = run_jsui(level_history_js(loudness_target=True), """
            set_slufs(-12.3);
            var a = slufs;
            set_slufs("not-a-number");   // NaN guard -> floor at -70, not poisoned
            dump({a: a, b: slufs});
        """, size=(660, 320))
        assert abs(result.state["a"] - (-12.3)) < 1e-6
        assert result.state["b"] == -70.0

    def test_loud_target_chip_still_cycles_with_taller_block(self):
        # The M/S/I stack grew the readout block; the M row + the (now lower) TGT
        # row both still cycle the loudness target on a pop-out view.
        result = run_jsui(level_history_js(loudness_target=True), """
            var rx = plot_r() - 6, ty = plot_t() + 12;
            function tap(yy) { onpointerdown({x: rx - 40, y: yy, buttons: 1});
                               onpointerup({x: rx - 40, y: yy, buttons: 0}); }
            tap(ty);          // M row
            var t1 = loud_target;
            tap(ty + 33);     // TGT row (dropped two lines by the S + I rows)
            var t2 = loud_target;
            dump({t1: t1, t2: t2});
        """, size=(660, 320))
        assert result.state["t1"] == 1     # first tap armed -14
        assert result.state["t2"] == 2     # tap on the dropped TGT row still hit
        emits = _named(result.outlets, "loudtarget")
        assert [e[2] for e in emits] == [1, 2]

    def test_set_ilufs_tracks_and_guards_nan(self):
        # Integrated LUFS (I) — the whole-programme readout the pop-out shows.
        result = run_jsui(level_history_js(loudness_target=True), """
            set_ilufs(-14.7);
            var a = ilufs;
            set_ilufs("not-a-number");   // NaN guard -> floor at -70, not poisoned
            dump({a: a, b: ilufs});
        """, size=(660, 320))
        assert abs(result.state["a"] - (-14.7)) < 1e-6
        assert result.state["b"] == -70.0

    def test_i_line_click_resets_integration_not_target(self):
        # Clicking the "I" line (the ↺ row) emits loudreset + clears the local
        # value WITHOUT cycling the loudness target (the reset zone out-prioritises
        # the target-cycle block it sits inside).
        result = run_jsui(level_history_js(loudness_target=True), """
            set_ilufs(-9.0);
            var rx = plot_r() - 6, ty = plot_t() + 12;
            onpointerdown({x: rx - 40, y: ty + 22, buttons: 1});   // the I row
            onpointerup({x: rx - 40, y: ty + 22, buttons: 0});
            dump({i: ilufs, tgt: loud_target});
        """, size=(660, 320))
        assert result.state["i"] == -70.0           # integration cleared locally
        assert result.state["tgt"] == 0             # target NOT cycled
        resets = _named(result.outlets, "loudreset")
        assert len(resets) == 1
        assert _named(result.outlets, "loudtarget") == []


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


class TestIntegratedLufs:
    """ITU-R BS.1770-4 gated integrated loudness (the non-UI accumulator).

    Drives the engine's `block(m)` / `reset()` entry points directly and
    reads the running `ilufs` state + the float emitted on outlet 0.
    """

    def _feed(self, calls):
        return run_jsui(integrated_lufs_js(), calls)

    def test_constant_minus23_calibration(self):
        # The canonical EBU calibration: a constant -23 LUFS programme
        # integrates to -23 (all blocks equal -> both gates pass everything).
        r = self._feed("""
            for (var i = 0; i < 50; i++) block(-23.0);
            dump({i: ilufs, n: n_abs});
        """)
        assert r.state["n"] == 50
        assert abs(r.state["i"] - (-23.0)) < 0.01

    def test_constant_minus6_matches_block(self):
        r = self._feed("""
            for (var i = 0; i < 30; i++) block(-6.06);
            dump({i: ilufs});
        """)
        assert abs(r.state["i"] - (-6.06)) < 0.02

    def test_absolute_gate_drops_silence(self):
        # Blocks at/under -70 are silence -> never counted; ilufs stays at the
        # -70 "no measurement" sentinel.
        r = self._feed("""
            block(-70.0); block(-75.0); block(-80.0);
            dump({i: ilufs, n: n_abs});
        """)
        assert r.state["n"] == 0
        assert r.state["i"] == -70.0

    def test_relative_gate_excludes_quiet_section(self):
        # A loud section (-10) plus an equally long quiet section (-40): the
        # quiet blocks sit below (mean - 10 LU) so the relative gate drops them
        # and the integrated value tracks the loud section (~-10), NOT the -25
        # arithmetic midpoint of the two loudnesses.
        r = self._feed("""
            for (var i = 0; i < 40; i++) block(-10.0);
            for (var j = 0; j < 40; j++) block(-40.0);
            dump({i: ilufs, n: n_abs});
        """)
        assert r.state["n"] == 80               # both gated in absolutely
        assert abs(r.state["i"] - (-10.0)) < 0.3  # but the quiet half is rel-gated out

    def test_reset_clears_measurement_and_emits(self):
        r = self._feed("""
            for (var i = 0; i < 20; i++) block(-12.0);
            var before = ilufs;
            reset();
            dump({before: before, after: ilufs, n: n_abs});
        """)
        assert abs(r.state["before"] - (-12.0)) < 0.05
        assert r.state["after"] == -70.0
        assert r.state["n"] == 0
        # reset() emits the sentinel on outlet 0 so the probe + readout clear.
        assert r.outlets[-1] == [0, -70.0]

    def test_each_block_emits_current_integrated(self):
        r = self._feed("""
            block(-18.0); block(-18.0);
            dump({i: ilufs});
        """)
        floats = [o for o in r.outlets if len(o) == 2 and o[0] == 0]
        assert len(floats) >= 2                 # one emit per block
        assert abs(floats[-1][1] - (-18.0)) < 0.05

    def test_nan_block_never_poisons_state(self):
        r = self._feed("""
            block(-14.0);
            block(NaN);
            dump({i: ilufs, finite: isFinite(ilufs) ? 1 : 0});
        """)
        assert r.state["finite"] == 1
        assert abs(r.state["i"] - (-14.0)) < 0.05


# A 1-channel synthetic buffer with sharp energy bursts at known normalized
# positions: drives the slice_overview onset detector headlessly.
_SLICE_BUF = """
    var __fc = 0, __cc = 1, __centers = [];
    Buffer = function (nm) {
        this.peek = function (ch, fr) {
            var v = 0.0;
            for (var c = 0; c < __centers.length; c++) {
                var d = fr - __centers[c];
                if (d >= 0 && d < 2000) v += (1.0 - d / 2000.0) * 0.9;
            }
            return v;
        };
        this.framecount = function () { return __fc; };
        this.channelcount = function () { return __cc; };
    };
    function _bursts(fc, positions) {
        __fc = fc; __centers = [];
        for (var i = 0; i < positions.length; i++)
            __centers.push(Math.floor(positions[i] * fc));
    }
"""


class TestSliceOnsetDetection:
    # The slice engine computes slice boundaries OFFLINE in JS (deterministic,
    # headless-testable) and emits per-slice coll-store lists `k start 0 end dur`.

    def test_grid_mode_even_boundaries(self):
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []);
            loaded = 1; sample_rate = 44100;
            set_mode(1); set_slices(8); analyze();
            dump({b: slice_boundaries, sc: slice_count});
        """)
        b = result.state["b"]
        assert result.state["sc"] == 8
        assert len(b) == 9
        for i in range(9):
            assert abs(b[i] - i / 8.0) < 1e-6

    def test_grid_emits_ms_coll_store_lists(self):
        # 44100 frames @ 44100 Hz = 1000 ms; 4 slices -> 250 ms each.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []);
            loaded = 1; sample_rate = 44100; slice_mode = 1; slice_count = 4;
            slice_boundaries = [];
            analyze();
            dump({sc: slice_count});
        """)
        stores = [o for o in result.outlets if o[0] == 1]
        assert len(stores) == 4
        # each store: [outlet=1, k, start_ms, 0, end_ms, dur_ms]
        for k, st in enumerate(stores):
            assert st[1] == k
            assert abs(st[2] - k * 250.0) < 1e-3      # start_ms
            assert st[3] == 0                          # the line~ jump segment
            assert abs(st[4] - (k + 1) * 250.0) < 1e-3  # end_ms
            assert abs(st[5] - 250.0) < 1e-3            # dur_ms (natural rate)
        counts = [o for o in result.outlets if o[0] == 2]
        assert counts[-1][1] == 4

    def test_transient_detects_known_onsets(self):
        # bursts at 0.2/0.4/0.6/0.8 -> interior boundaries near each.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, [0.2, 0.4, 0.6, 0.8]);
            loaded = 1; sample_rate = 44100;
            set_sensitivity(50); set_min_spacing(40);
            set_mode(0); analyze();
            dump({b: slice_boundaries});
        """)
        b = result.state["b"]
        assert b[0] == 0.0 and b[-1] == 1.0
        interior = b[1:-1]
        for target in (0.2, 0.4, 0.6, 0.8):
            assert any(abs(p - target) < 0.02 for p in interior), target

    def test_min_spacing_rejects_double_triggers(self):
        # two bursts ~20 ms apart, min spacing 80 ms -> collapse to one onset.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, [0.5, 0.5045]);
            loaded = 1; sample_rate = 44100;
            set_sensitivity(60); set_min_spacing(80);
            set_mode(0); analyze();
            dump({b: slice_boundaries});
        """)
        interior = result.state["b"][1:-1]
        near = [p for p in interior if 0.49 < p < 0.52]
        assert len(near) == 1

    def test_clamps_to_64_slices(self):
        positions = [round(0.02 + i * 0.0049, 5) for i in range(190)]
        result = run_jsui(slice_overview_js(), _SLICE_BUF + ("""
            _bursts(220500, %s);
            loaded = 1; sample_rate = 44100;
            set_sensitivity(100); set_min_spacing(5);
            set_mode(0); analyze();
            dump({sc: slice_count, n: slice_boundaries.length});
        """ % ("[" + ",".join(str(p) for p in positions) + "]")))
        assert result.state["sc"] <= 64
        assert result.state["n"] <= 65

    def test_set_messages_never_echo_an_outlet(self):
        # set_* with no sample loaded must not fire any outlet (no-echo rule).
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            loaded = 0;
            set_samplerate(48000);
            set_sensitivity(70);
            set_min_spacing(30);
            set_mode(1);
            set_pitch(0);
            dump({n: __captured.outlets.length});
        """)
        assert result.state["n"] == 0
        assert result.outlets == []


class TestSliceDividerEdit:
    # The EDITOR instance (set_editable 1) makes the slice dividers click/drag-
    # editable; each edit emits the full normalized boundary list on outlet 3,
    # which the display instance adopts via set_display_bounds (single grid).
    # Inner width with the default 660 px harness: 660 - 2*PADDING(8) = 644.

    @staticmethod
    def _x(pos):
        return 8 + pos * 644.0

    def test_drag_moves_a_divider_and_emits_bounds(self):
        x05, x06 = self._x(0.5), self._x(0.6)
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            slice_boundaries = [0.0, 0.25, 0.5, 0.75, 1.0]; slice_count = 4;
            set_editable(1);
            onclick(%f, 50, 1, 0, 0, 0, 0, 0);   // grab the 0.5 divider (idx 2)
            ondrag(%f, 50, 1, 0, 0, 0, 0, 0);     // drag it to ~0.6
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);       // release
            dump({b: slice_boundaries, di: drag_index});
        """ % (x05, x06))
        b = result.state["b"]
        assert len(b) == 5 and b[0] == 0.0 and b[-1] == 1.0
        assert abs(b[2] - 0.6) < 0.01           # the dragged divider moved
        assert result.state["di"] == -1          # released
        bounds = [o for o in result.outlets if o[0] == 3]
        assert bounds, "outlet 3 (edited bounds) should fire on drag"
        assert abs(bounds[-1][3] - 0.6) < 0.01   # [outlet, b0, b1, b2, ...]

    def test_drag_clamps_between_neighbours(self):
        # dragging far past a neighbour clamps (never crosses / reorders).
        x05, xfar = self._x(0.5), self._x(0.95)
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            slice_boundaries = [0.0, 0.25, 0.5, 0.75, 1.0]; slice_count = 4;
            set_editable(1);
            onclick(%f, 50, 1, 0, 0, 0, 0, 0);
            ondrag(%f, 50, 1, 0, 0, 0, 0, 0);   // try to drag 0.5 past 0.75
            dump({b: slice_boundaries});
        """ % (x05, xfar))
        b = result.state["b"]
        assert b[1] < b[2] < b[3]                # still ordered
        assert b[2] <= 0.75 - 0.003              # clamped below the 0.75 neighbour

    def test_click_empty_space_adds_a_divider(self):
        x025 = self._x(0.25)
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            slice_boundaries = [0.0, 0.5, 1.0]; slice_count = 2;
            set_editable(1);
            onclick(%f, 50, 1, 0, 0, 0, 0, 0);   // click empty -> insert at ~0.25
            dump({b: slice_boundaries});
        """ % x025)
        b = result.state["b"]
        assert len(b) == 4
        assert any(abs(p - 0.25) < 0.01 for p in b)
        assert b == sorted(b)
        assert [o for o in result.outlets if o[0] == 3]

    def test_option_click_removes_nearest_divider(self):
        x05 = self._x(0.5)
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            slice_boundaries = [0.0, 0.25, 0.5, 0.75, 1.0]; slice_count = 4;
            set_editable(1);
            onclick(%f, 50, 1, 0, 0, 0, 1, 0);   // option-click near 0.5 -> remove
            dump({b: slice_boundaries});
        """ % x05)
        b = result.state["b"]
        assert len(b) == 4
        assert all(abs(p - 0.5) > 0.01 for p in b)   # 0.5 removed
        assert [o for o in result.outlets if o[0] == 3]

    def test_display_instance_click_scans_not_edits(self):
        # editable defaults to 0 -> onclick is the scan outlet (0), grid untouched.
        x05 = self._x(0.5)
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            slice_boundaries = [0.0, 0.5, 1.0];
            onclick(%f, 50, 1, 0, 0, 0, 0, 0);
            dump({b: slice_boundaries});
        """ % x05)
        scan = [o for o in result.outlets if o[0] == 0]
        assert len(scan) == 1 and abs(scan[0][1] - 0.5) < 0.01
        assert result.state["b"] == [0.0, 0.5, 1.0]   # unchanged
        assert [o for o in result.outlets if o[0] == 3] == []

    def test_set_display_bounds_adopts_grid_and_drives_coll(self):
        # the display instance adopts edited bounds and re-emits the coll-store
        # lists (so a manual edit in the editor reaches playback).
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            set_display_bounds(0.0, 0.3, 0.7, 1.0);
            dump({b: slice_boundaries, sc: slice_count});
        """)
        assert result.state["sc"] == 3
        assert result.state["b"] == [0.0, 0.3, 0.7, 1.0]
        stores = [o for o in result.outlets if o[0] == 1]
        assert len(stores) == 3                       # one coll store per slice
        assert abs(stores[1][2] - 300.0) < 1e-3       # slice 1 start_ms (0.3*1000)

    def test_set_active_index_lights_up_the_triggered_slice(self):
        # playback feedback: set_active_index(n) highlights slice n
        # ([boundaries[n], boundaries[n+1]]) and registers a fading hit.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            set_display_bounds(0.0, 0.25, 0.5, 0.75, 1.0);   // 4 slices
            set_active_index(2);
            dump({as: active_start, ae: active_end, hits: recent_hits.length});
        """)
        assert abs(result.state["as"] - 0.5) < 1e-6   # slice 2 start
        assert abs(result.state["ae"] - 0.75) < 1e-6  # slice 2 end
        assert result.state["hits"] == 1              # registered one hit marker

    def test_set_active_index_clamps_out_of_range(self):
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, []); loaded = 1; sample_rate = 44100;
            set_display_bounds(0.0, 0.5, 1.0);   // 2 slices (indices 0, 1)
            set_active_index(99);
            dump({as: active_start, ae: active_end});
        """)
        assert abs(result.state["as"] - 0.5) < 1e-6   # clamped to the last slice
        assert abs(result.state["ae"] - 1.0) < 1e-6

    def test_set_editable_never_echoes_an_outlet(self):
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            loaded = 0;
            set_editable(1);
            set_editable(0);
            dump({n: __captured.outlets.length});
        """)
        assert result.state["n"] == 0

    def test_manual_edit_survives_samplerate_refire(self):
        # after a hand edit, an environmental set_samplerate must NOT re-detect
        # (which would wipe the edit); a real param re-analyze still supersedes.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(44100, [0.2, 0.4, 0.6, 0.8]); loaded = 1; sample_rate = 44100;
            set_mode(0); analyze();
            set_display_bounds(0.0, 0.5, 1.0);   // hand edit -> 2 slices, manual_edit=1
            set_samplerate(48000);               // env re-fire: must keep the edit
            var kept = slice_boundaries.length;
            set_sensitivity(50);                 // a real re-slice supersedes
            dump({kept: kept, after: slice_boundaries.length, me: manual_edit});
        """)
        assert result.state["kept"] == 3          # edit survived the samplerate re-fire
        assert result.state["after"] > 3          # the sensitivity re-analyze re-detected
        assert result.state["me"] == 0            # manual flag cleared by the re-detect


class TestSlicePlayhead:
    # playhead_ms feeds a live read position (ms) and normalizes by buffer length
    # so the marker sweeps the whole waveform during playback.
    def test_playhead_ms_normalizes_by_buffer_length(self):
        # 48000 frames @ 48000 Hz = 1000 ms; 250 ms -> 0.25, 750 ms -> 0.75.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(48000, []); loaded = 1; sample_rate = 48000;
            playhead_ms(250.0); var p1 = playhead;
            playhead_ms(750.0);
            dump({p1: p1, p2: playhead});
        """)
        assert abs(result.state["p1"] - 0.25) < 1e-6
        assert abs(result.state["p2"] - 0.75) < 1e-6

    def test_playhead_ms_clamps_and_is_inert_without_buffer(self):
        # past the end clamps to 1.0; with no buffer (fc=0) the call is a no-op.
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(48000, []); loaded = 1; sample_rate = 48000;
            playhead_ms(5000.0); var clamped = playhead;     // > length -> 1.0
            _bursts(0, []);                                   // buffer gone
            playhead_ms(250.0);                               // must not move it
            dump({clamped: clamped, after: playhead});
        """)
        assert abs(result.state["clamped"] - 1.0) < 1e-6
        assert abs(result.state["after"] - 1.0) < 1e-6      # unchanged (no buffer)

    def test_load_resets_playhead_to_start(self):
        result = run_jsui(slice_overview_js(), _SLICE_BUF + """
            _bursts(48000, []); loaded = 1; sample_rate = 48000;
            playhead_ms(750.0); var before = playhead;
            inlet = 0; msg_float(1.0);                        // re-load (inlet 0)
            dump({before: before, after: playhead});
        """)
        assert abs(result.state["before"] - 0.75) < 1e-6
        assert abs(result.state["after"] - 0.0) < 1e-6


class TestEnvelopeEditorGestures:
    """Drag semantics of the ADSR envelope editor (dnksaus kit engine #1):
    nearest-node hit test, per-node value emission, range clamps, and the
    no-echo back-sync rule."""

    SIZE = (280, 96)

    def test_attack_drag_is_monotonic_and_clamps_at_range_edges(self):
        # Drag the attack peak rightward through its slot, then way past it
        # (clamp at MAX_A) and way left of the plot (clamp at 0).
        result = run_jsui(envelope_editor_js(), """
            var pl = plot_left(), pw = plot_w(), pt = plot_top();
            onclick(node_x(0), node_y(0), 1, 0, 0, 0, 0, 0);
            ondrag(pl + 0.10 * pw, pt, 1, 0, 0, 0, 0, 0);
            ondrag(pl + 0.18 * pw, pt, 1, 0, 0, 0, 0, 0);
            ondrag(pl + 0.26 * pw, pt, 1, 0, 0, 0, 0, 0);
            ondrag(pl + 0.90 * pw, pt, 1, 0, 0, 0, 0, 0);
            ondrag(pl - 60, pt, 1, 0, 0, 0, 0, 0);
            ondrag(pl - 60, pt, 0, 0, 0, 0, 0, 0);
            dump({a: attack_ms, target_after: drag_target});
        """, size=self.SIZE)
        assert result.outlets, "drag must emit"
        assert {o[0] for o in result.outlets} == {0}, "ONLY the attack outlet fires"
        vals = [o[1] for o in result.outlets]
        assert vals[1] < vals[2] < vals[3], "rightward drag rises monotonically"
        assert vals[4] == 2000.0                      # clamped at MAX_A
        assert vals[5] == 0.0                         # clamped at 0
        assert result.state["a"] == 0.0
        assert result.state["target_after"] == -1     # button-up releases the node

    def test_sustain_node_vertical_drag_clamps_0_to_1(self):
        result = run_jsui(envelope_editor_js(), """
            onclick(node_x(2), node_y(2), 1, 0, 0, 0, 0, 0);
            var nx = node_x(2);
            ondrag(nx, env_y(0.25), 1, 0, 0, 0, 0, 0);
            ondrag(nx, plot_bottom() + 40, 1, 0, 0, 0, 0, 0);
            ondrag(nx, plot_top() - 40, 1, 0, 0, 0, 0, 0);
            dump({s: sustain});
        """, size=self.SIZE)
        assert {o[0] for o in result.outlets} == {2}, "ONLY the sustain outlet fires"
        vals = [o[1] for o in result.outlets]
        assert abs(vals[1] - 0.25) < 1e-6
        assert vals[2] == 0.0                         # below the plot -> clamp 0
        assert vals[3] == 1.0                         # above the plot -> clamp 1
        assert result.state["s"] == 1.0

    def test_decay_knee_drag_emits_decay_and_sustain_only(self):
        # The knee owns TWO axes: x -> decay ms, y -> sustain. Attack and
        # release must stay silent for the whole gesture.
        result = run_jsui(envelope_editor_js(), """
            onclick(node_x(1), node_y(1), 1, 0, 0, 0, 0, 0);
            ondrag(ax() + 0.20 * plot_w(), env_y(0.4), 1, 0, 0, 0, 0, 0);
            dump({d: decay_ms, s: sustain});
        """, size=self.SIZE)
        assert {o[0] for o in result.outlets} == {1, 2}
        assert abs(result.state["s"] - 0.4) < 1e-6
        last_decay = [o[1] for o in result.outlets if o[0] == 1][-1]
        assert abs(last_decay - result.state["d"]) < 1e-6
        assert result.state["d"] > 200.0              # dragged right of the initial

    def test_release_drag_is_monotonic_and_clamps_at_max(self):
        result = run_jsui(envelope_editor_js(), """
            onclick(node_x(3), node_y(3), 1, 0, 0, 0, 0, 0);
            var pb = plot_bottom();
            ondrag(sx() + 0.10 * plot_w(), pb, 1, 0, 0, 0, 0, 0);
            ondrag(sx() + 0.25 * plot_w(), pb, 1, 0, 0, 0, 0, 0);
            ondrag(plot_right() + 100, pb, 1, 0, 0, 0, 0, 0);
            dump({r: release_ms});
        """, size=self.SIZE)
        assert {o[0] for o in result.outlets} == {3}, "ONLY the release outlet fires"
        vals = [o[1] for o in result.outlets]
        assert vals[1] < vals[2] < vals[3], "rightward drag rises monotonically"
        assert vals[3] == 8000.0                      # clamped at MAX_R
        assert result.state["r"] == 8000.0

    def test_hit_test_targets_nearest_node_and_misses_empty_plot(self):
        result = run_jsui(envelope_editor_js(), """
            onclick(node_x(0), node_y(0), 1, 0, 0, 0, 0, 0);
            var t0 = drag_target;
            ondrag(node_x(0), node_y(0), 0, 0, 0, 0, 0, 0);
            onclick(node_x(3), node_y(3), 1, 0, 0, 0, 0, 0);
            var t3 = drag_target;
            ondrag(node_x(3), node_y(3), 0, 0, 0, 0, 0, 0);
            var n_before = __captured.outlets.length;
            onclick(plot_left() + plot_w() * 0.5, plot_top() + 2, 1, 0, 0, 0, 0, 0);
            dump({t0: t0, t3: t3, tmiss: drag_target,
                  missEmitted: __captured.outlets.length - n_before});
        """, size=self.SIZE)
        assert result.state["t0"] == 0
        assert result.state["t3"] == 3
        assert result.state["tmiss"] == -1            # empty plot: no grab
        assert result.state["missEmitted"] == 0       # ...and no emission

    def test_back_sync_sets_state_without_re_emitting(self):
        # The no-echo rule: inbound param values (msg_float on inlets 0-3)
        # redraw the curve but NEVER fire outlets; over-range values clamp.
        result = run_jsui(envelope_editor_js(), """
            inlet = 0; msg_float(500.0);
            inlet = 1; msg_float(1000.0);
            inlet = 2; msg_float(0.5);
            inlet = 3; msg_float(2000.0);
            inlet = 0; msg_float(99999.0);
            dump({a: attack_ms, d: decay_ms, s: sustain, r: release_ms});
        """, size=self.SIZE)
        assert result.outlets == []
        assert result.state == {"a": 2000.0, "d": 1000.0, "s": 0.5, "r": 2000.0}


def _points_emissions(outlets):
    """Every captured ``points ...`` list emission -> list of [x0, y0, ...]."""
    return [o[2:] for o in outlets if len(o) > 1 and o[1] == "points"]


class TestCurveEditorGestures:
    """Gesture + message semantics of the general breakpoint curve editor
    (dnksaus kit engines #2-#6): click-empty-adds, neighbor-clamped drags,
    double-click delete with the fresh-point guard, grid snap, the cosine
    tension blend, and the no-echo rule for set_points / set_all."""

    SIZE = (280, 120)

    def test_click_empty_adds_a_point_and_emits_the_full_list(self):
        result = run_jsui(curve_editor_js(), """
            onclick(to_px_x(0.3), to_px_y(0.55), 1, 0, 0, 0, 0, 0);
            dump({n: xs.length, x1: xs[1], y1: ys[1],
                  grabbed: drag_target, fresh: just_added});
        """, size=self.SIZE)
        assert result.state["n"] == 3
        assert abs(result.state["x1"] - 0.3) < 0.01     # px round-trip tolerance
        assert abs(result.state["y1"] - 0.55) < 0.02
        assert result.state["grabbed"] == 1             # new point is grabbed
        assert result.state["fresh"] == 1
        pts = _points_emissions(result.outlets)
        assert len(pts) == 1, "the add emits exactly one points list"
        assert len(pts[0]) == 6                         # 3 points -> 6 atoms
        assert pts[0][0] == 0 and pts[0][4] == 1        # endpoint x are 0 / 1

    def test_click_empty_at_max_points_is_ignored(self):
        result = run_jsui(curve_editor_js(max_points=3), """
            onclick(to_px_x(0.3), to_px_y(0.5), 1, 0, 0, 0, 0, 0);   // 3rd point
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);                           // release
            var before = __captured.outlets.length;
            onclick(to_px_x(0.7), to_px_y(0.5), 1, 0, 0, 0, 0, 0);   // over max
            dump({n: xs.length, extra: __captured.outlets.length - before});
        """, size=self.SIZE)
        assert result.state["n"] == 3
        assert result.state["extra"] == 0

    def test_drag_clamps_x_between_neighbors(self):
        # The generalized FunctionHandler rule: a dragged point can never
        # cross its neighbors, however far the pointer goes.
        result = run_jsui(curve_editor_js(), """
            set_points(0.0, 0.0, 0.5, 0.5, 1.0, 1.0);
            onclick(to_px_x(0.5), to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            ondrag(to_px_x(1.0) + 60, to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            var xr = xs[1];
            ondrag(to_px_x(0.0) - 60, to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            var xl = xs[1];
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            dump({xr: xr, xl: xl, n: xs.length});
        """, size=self.SIZE)
        assert result.state["n"] == 3
        assert 0.99 <= result.state["xr"] < 1.0, "clamped strictly left of x=1"
        assert 0.0 < result.state["xl"] <= 0.011, "clamped strictly right of x=0"

    def test_endpoint_drag_moves_y_only(self):
        result = run_jsui(curve_editor_js(init_y0=0.0, init_y1=1.0), """
            onclick(to_px_x(0.0), to_px_y(0.0), 1, 0, 0, 0, 0, 0);
            ondrag(to_px_x(0.4), to_px_y(0.8), 1, 0, 0, 0, 0, 0);
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            dump({x0: xs[0], y0: ys[0], n: xs.length});
        """, size=self.SIZE)
        assert result.state["n"] == 2
        assert result.state["x0"] == 0.0, "endpoint x stays locked at 0"
        assert abs(result.state["y0"] - 0.8) < 0.02
        assert len(_points_emissions(result.outlets)) == 1   # one move, one emit

    def test_double_click_deletes_interior_only_with_fresh_point_guard(self):
        result = run_jsui(curve_editor_js(), """
            // add a point, then immediately double-click it (the accidental
            // double-click-on-empty flow): the fresh-point guard keeps it.
            onclick(to_px_x(0.5), to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            onclick(to_px_x(xs[1]), to_px_y(ys[1]), 1, 0, 0, 0, 0, 0);
            ondblclick(to_px_x(xs[1]), to_px_y(ys[1]), 1, 0, 0, 0, 0, 0);
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            var kept = xs.length;
            // a LATER double-click on the same (no longer fresh) node deletes.
            onclick(to_px_x(xs[1]), to_px_y(ys[1]), 1, 0, 0, 0, 0, 0);
            ondblclick(to_px_x(xs[1]), to_px_y(ys[1]), 1, 0, 0, 0, 0, 0);
            var afterDelete = xs.length;
            // endpoints are undeletable.
            ondblclick(to_px_x(0.0), to_px_y(ys[0]), 1, 0, 0, 0, 0, 0);
            ondblclick(to_px_x(1.0), to_px_y(ys[1]), 1, 0, 0, 0, 0, 0);
            dump({kept: kept, afterDelete: afterDelete, ends: xs.length});
        """, size=self.SIZE)
        assert result.state["kept"] == 3, "fresh point survives its own dblclick"
        assert result.state["afterDelete"] == 2, "later dblclick deletes it"
        assert result.state["ends"] == 2, "endpoints never delete"
        pts = _points_emissions(result.outlets)
        assert len(pts[-1]) == 4, "the delete emitted the shrunken list"

    def test_snap_quantizes_added_and_dragged_points(self):
        result = run_jsui(curve_editor_js(), """
            set_grid(4);
            set_snap(1);
            onclick(to_px_x(0.3), to_px_y(0.55), 1, 0, 0, 0, 0, 0);
            var ax = xs[1], ay = ys[1];
            ondrag(to_px_x(0.62), to_px_y(0.88), 1, 0, 0, 0, 0, 0);
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            dump({ax: ax, ay: ay, dx: xs[1], dy: ys[1]});
        """, size=self.SIZE)
        assert abs(result.state["ax"] - 0.25) < 1e-6, "added x snaps to grid/4"
        assert abs(result.state["ay"] - 0.5) < 1e-6, "added y snaps to grid/4"
        assert abs(result.state["dx"] - 0.5) < 1e-6, "dragged x snaps"
        assert abs(result.state["dy"] - 1.0) < 1e-6, "dragged y snaps"

    def test_set_points_round_trips_without_re_emitting(self):
        # The no-echo rule: inbound lists rebuild state, redraw, NEVER emit —
        # and the sanitizer sorts + forces the endpoint x values.
        result = run_jsui(curve_editor_js(), """
            set_points(0.02, 0.2, 1.0, 0.4, 0.5, 0.9);
            dump({n: xs.length, xs: xs.slice(), ys: ys.slice()});
        """, size=self.SIZE)
        assert result.outlets == []
        assert result.state["n"] == 3
        assert result.state["xs"] == [0.0, 0.5, 1.0]      # sorted + endpoints forced
        assert result.state["ys"] == [0.2, 0.9, 0.4]

    def test_set_all_uses_count_and_ignores_stale_slots(self):
        # The wrapper restore message: count-first fixed-slot layout — stale
        # coordinates beyond the count must not become points.
        result = run_jsui(curve_editor_js(), """
            set_all(3, 0.0, 0.1, 0.5, 0.6, 1.0, 0.9, 0.7, 0.7, 0.8, 0.8);
            dump({n: xs.length, x1: xs[1], y2: ys[2]});
        """, size=self.SIZE)
        assert result.outlets == []
        assert result.state["n"] == 3
        assert result.state["x1"] == 0.5
        assert result.state["y2"] == 0.9

    def test_inbound_lists_ignored_mid_drag(self):
        # A restore cascade (our own edit echoed through the param hosts)
        # can never fight a live gesture.
        result = run_jsui(curve_editor_js(), """
            set_points(0.0, 0.0, 0.5, 0.5, 1.0, 1.0);
            onclick(to_px_x(0.5), to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            set_points(0.0, 1.0, 1.0, 0.0);
            set_all(2, 0.0, 1.0, 1.0, 0.0);
            var during = xs.length;
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            set_points(0.0, 1.0, 1.0, 0.0);
            dump({during: during, after: xs.length});
        """, size=self.SIZE)
        assert result.state["during"] == 3, "mid-drag restore is ignored"
        assert result.state["after"] == 2, "after release it applies"

    def test_tension_blends_linear_to_cosine(self):
        # The documented interpolation contract on a rising (0,0)->(1,1) line:
        # k=0 exact linear, k=1 full cosine ease, k=0.5 their midpoint.
        result = run_jsui(curve_editor_js(), """
            set_tension(0);    var lin = curve_y_at(0.25);
            set_tension(100);  var cos_ = curve_y_at(0.25);
            set_tension(50);   var mid = curve_y_at(0.25);
            set_tension(100);  var through = curve_y_at(0.5);
            dump({lin: lin, cos_: cos_, mid: mid, through: through});
        """, size=self.SIZE)
        assert result.outlets == []
        assert abs(result.state["lin"] - 0.25) < 1e-9
        expected_cos = (1 - __import__("math").cos(__import__("math").pi * 0.25)) / 2
        assert abs(result.state["cos_"] - expected_cos) < 1e-9
        assert abs(result.state["mid"] - (0.25 + expected_cos) / 2) < 1e-9
        assert abs(result.state["through"] - 0.5) < 1e-9, \
            "the curve passes through segment midpoints of a symmetric line"

    def test_xy_readout_and_flag_messages(self):
        result = run_jsui(curve_editor_js(), """
            onclick(to_px_x(0.5), to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            ondrag(to_px_x(0.59), to_px_y(0.6), 1, 0, 0, 0, 0, 0);
            var readout = format_xy();
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            set_grid(7.4);  var g1 = grid_n;
            set_grid(99);   var g2 = grid_n;
            set_snap(2);    var s = snap_on;
            set_loop(1);    var l = loop_on;
            dump({readout: readout, g1: g1, g2: g2, s: s, l: l});
        """, size=self.SIZE)
        assert result.state["readout"] == "X 59 Y 60"
        assert result.state["g1"] == 7
        assert result.state["g2"] == 64
        assert result.state["s"] == 1
        assert result.state["l"] == 1


def _values_emissions(outlets):
    """Every captured ``values ...`` list emission -> list of [v0, v1, ...]."""
    return [o[2:] for o in outlets if len(o) > 1 and o[1] == "values"]


def _step_emissions(outlets):
    """Every captured ``step i v`` emission -> list of [i, v]."""
    return [o[2:] for o in outlets if len(o) > 1 and o[1] == "step"]


class TestStepBarsGestures:
    """Gesture + message semantics of the step-bar lane editor (dnksaus kit
    engines #7-#8): click-sets-bar, interpolated drag-paint across bars,
    modifier-click reset (no stroke), value-preserving set_steps, and the
    no-echo / ignored-mid-drag rules for set_values / set_all."""

    SIZE = (280, 120)

    def test_click_sets_the_bar_under_the_cursor(self):
        result = run_jsui(step_bars_js(), """
            onclick(bar_center_x(2), to_px_y(0.7), 1, 0, 0, 0, 0, 0);
            dump({v2: values[2], n: num_steps, painting: dragging});
        """, size=self.SIZE)
        assert abs(result.state["v2"] - 0.7) < 0.02
        assert result.state["n"] == 8
        assert result.state["painting"] == 1          # a plain click starts a stroke
        steps = _step_emissions(result.outlets)
        assert len(steps) == 1 and steps[0][0] == 2
        vals = _values_emissions(result.outlets)
        assert len(vals) == 1, "the click emits exactly one values list"
        assert len(vals[0]) == 8, "the payload carries the ACTIVE steps only"
        assert abs(vals[0][2] - 0.7) < 0.02

    def test_drag_paint_across_three_bars_writes_three_values(self):
        # THE signature step-editor gesture: one stroke over bars 0->2 writes
        # all three, with the skipped middle bar linearly interpolated.
        result = run_jsui(step_bars_js(), """
            onclick(bar_center_x(0), to_px_y(0.2), 1, 0, 0, 0, 0, 0);
            ondrag(bar_center_x(2), to_px_y(0.8), 1, 0, 0, 0, 0, 0);
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            dump({v0: values[0], v1: values[1], v2: values[2], v3: values[3],
                  readout_gone: drag_step});
        """, size=self.SIZE)
        assert abs(result.state["v0"] - 0.2) < 0.02
        assert abs(result.state["v1"] - 0.5) < 0.03   # lerped midpoint
        assert abs(result.state["v2"] - 0.8) < 0.02
        assert result.state["v3"] == 1.0              # untouched default
        assert result.state["readout_gone"] == -1     # release ends the readout
        touched = {s[0] for s in _step_emissions(result.outlets)}
        assert touched == {0, 1, 2}, "every crossed bar got a step emission"

    def test_modifier_click_resets_a_bar_and_starts_no_stroke(self):
        result = run_jsui(step_bars_js(reset_value=0.0), """
            set_values(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9);
            onclick(bar_center_x(2), to_px_y(0.9), 1, 1, 0, 0, 0, 0);   // cmd
            var cmd_reset = values[2];
            onclick(bar_center_x(3), to_px_y(0.9), 1, 0, 0, 0, 1, 0);   // alt
            var alt_reset = values[3];
            // the reset started NO paint stroke: a follow-up drag is inert.
            ondrag(bar_center_x(5), to_px_y(0.1), 1, 0, 0, 0, 1, 0);
            dump({cmd_reset: cmd_reset, alt_reset: alt_reset, v5: values[5]});
        """, size=self.SIZE)
        assert result.state["cmd_reset"] == 0.0
        assert result.state["alt_reset"] == 0.0
        assert result.state["v5"] == 0.9, "no stroke after a modifier reset"
        assert len(_values_emissions(result.outlets)) == 2, \
            "each reset emitted the persistence payload"

    def test_set_steps_requantizes_and_preserves_slot_values(self):
        result = run_jsui(step_bars_js(), """
            set_values(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8);
            set_steps(4);
            var shrunk = num_steps;
            set_steps(8);
            dump({shrunk: shrunk, n: num_steps, v6: values[6],
                  lo: (set_steps(1), num_steps), hi: (set_steps(99), num_steps)});
        """, size=self.SIZE)
        assert result.outlets == [], "set_steps / set_values never re-emit"
        assert result.state["shrunk"] == 4
        assert result.state["n"] == 8
        assert abs(result.state["v6"] - 0.7) < 1e-9, \
            "values beyond a shrunken count survive and come back"
        assert result.state["lo"] == 2
        assert result.state["hi"] == 16

    def test_set_values_round_trips_and_clamps_without_re_emitting(self):
        result = run_jsui(step_bars_js(), """
            set_values(0.25, 0.5, 2.0, -1.0);
            dump({v0: values[0], v1: values[1], v2: values[2], v3: values[3],
                  v4: values[4], n: num_steps});
        """, size=self.SIZE)
        assert result.outlets == []
        assert result.state["v0"] == 0.25
        assert result.state["v1"] == 0.5
        assert result.state["v2"] == 1.0              # clamped high
        assert result.state["v3"] == 0.0              # clamped low
        assert result.state["v4"] == 1.0              # untouched default
        assert result.state["n"] == 8, "set_values leaves the count alone"

    def test_set_all_uses_count_and_fills_the_slots(self):
        # The wrapper restore message: count-first fixed-slot layout.
        result = run_jsui(step_bars_js(max_steps=8), """
            set_all(3, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8);
            dump({n: num_steps, v1: values[1], v5: values[5]});
        """, size=self.SIZE)
        assert result.outlets == []
        assert result.state["n"] == 3
        assert result.state["v1"] == 0.2
        assert result.state["v5"] == 0.6, "stale slots still restore (fixed array)"

    def test_restores_ignored_mid_drag(self):
        # A restore cascade (our own edit echoed through the param hosts)
        # can never fight a live paint stroke.
        result = run_jsui(step_bars_js(), """
            onclick(bar_center_x(1), to_px_y(0.6), 1, 0, 0, 0, 0, 0);
            set_values(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
            set_all(4, 0.0, 0.0, 0.0, 0.0);
            set_steps(4);
            var during_v = values[1], during_n = num_steps;
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            set_steps(4);
            dump({during_v: during_v, during_n: during_n, after_n: num_steps});
        """, size=self.SIZE)
        assert abs(result.state["during_v"] - 0.6) < 0.02, "mid-drag restore ignored"
        assert result.state["during_n"] == 8
        assert result.state["after_n"] == 4, "after release it applies"

    def test_out_of_range_clicks_and_playhead_clamp(self):
        result = run_jsui(step_bars_js(), """
            onclick(bar_center_x(0), plot_top() - 1, 1, 0, 0, 0, 0, 0);
            var hi = values[0];
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            onclick(bar_center_x(1), plot_bottom() + 1, 1, 0, 0, 0, 0, 0);
            var lo = values[1];
            ondrag(bar_center_x(7) + 500, to_px_y(0.5), 1, 0, 0, 0, 0, 0);
            var last = values[7];
            ondrag(0, 0, 0, 0, 0, 0, 0, 0);
            set_playhead(3);   var p_ok = playhead;
            set_playhead(99);  var p_hi = playhead;
            set_playhead(-1);  var p_off = playhead;
            var readout = (onclick(bar_center_x(3), to_px_y(0.74), 1, 0, 0, 0, 0, 0),
                           format_step());
            dump({hi: hi, lo: lo, last: last,
                  p_ok: p_ok, p_hi: p_hi, p_off: p_off, readout: readout});
        """, size=self.SIZE)
        assert result.state["hi"] == 1.0, "clicks above the plot clamp to 1"
        assert result.state["lo"] == 0.0, "clicks below the plot clamp to 0"
        assert abs(result.state["last"] - 0.5) < 0.02, \
            "painting past the right edge clamps to the last bar"
        assert result.state["p_ok"] == 3
        assert result.state["p_hi"] == -1
        assert result.state["p_off"] == -1
        assert result.state["readout"] == "S 3 V 74"

    def test_link_flag_is_display_only(self):
        result = run_jsui(step_bars_js(), """
            set_link(1);  var on = link_on;
            set_link(0);  var off = link_on;
            dump({on: on, off: off});
        """, size=self.SIZE)
        assert result.outlets == []
        assert result.state["on"] == 1
        assert result.state["off"] == 0
