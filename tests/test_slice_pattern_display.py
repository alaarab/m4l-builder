"""Behavioral tests for the slice_pattern_display engine (Node harness).

Covers the PLAYBACK path added for Shard's phrase/chop sequencer: the
``trigger <step>`` message must emit the same (lock-aware) slice index, gate,
pitch and ratchet sub-hits the lane draws, so display and audio never drift.
"""

import os

import pytest

from m4l_builder.engines.slice_pattern_display import (
    SLICE_PATTERN_DISPLAY_OUTLETS,
    slice_pattern_display_js,
)

from .js_harness import NODE, run_jsui

pytestmark = pytest.mark.skipif(
    not (NODE and os.path.exists(NODE)), reason="node not available"
)


def _run(driver):
    return run_jsui(slice_pattern_display_js(), driver, size=(320, 40))


def test_outlet_count_is_three():
    assert SLICE_PATTERN_DISPLAY_OUTLETS == 3


def _steps(result):
    return [o for o in result.outlets if o[0] == 2 and len(o) > 1 and o[1] == "step"]


def test_trigger_emits_step_playback_tuple():
    r = _run("""
        inlet = 1; msg_float(16);          // slice_count
        inlet = 0; msg_float(8);           // step_count
        inlet = 3; msg_float(2);           // mode = PAT (phrase)
        inlet = 5; msg_float(11);          // pattern_seed
        inlet = 14; messagename = 'trigger'; anything(3);
    """)
    s = _steps(r)
    assert len(s) == 1
    # [2, "step", stepNum, gate, pitch, dir, nHits, level, h0, h1, h2, h3]
    o = s[0]
    assert o[2] == 3                       # step number echoed
    assert o[3] in (0, 1)                  # gate
    assert o[5] in (-1, 1)                 # direction
    assert o[6] >= 1                       # nHits >= 1
    assert o[7] in (0.0, 0.45, 1.0, 1.25)  # CHOP volume tier
    assert 0 <= o[8] < 16                  # main slice index in range


def test_trigger_wraps_step_into_range():
    r = _run("""
        inlet = 0; msg_float(8);
        inlet = 14; messagename = 'trigger'; anything(11);   // 11 % 8 = 3
    """)
    assert _steps(r)[0][2] == 3


def test_chop_mutes_some_steps():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(16);
        inlet = 6; msg_float(90);          // chop_amount high
        inlet = 7; msg_float(37);          // chop_seed
        var muted = 0, i;
        for (i = 0; i < 16; i++) if (step_gate(i) < 0.5) muted++;
        dump({muted: muted});
    """)
    assert r.state["muted"] > 0            # chop gates real steps off
    # and a chopped step triggers gate 0
    r2 = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(16);
        inlet = 6; msg_float(100);         // chop everything
        inlet = 14; messagename = 'trigger'; anything(0);
    """)
    assert _steps(r2)[0][3] == 0           # gate off -> host plays nothing


def test_lock_overrides_index_and_triggers_it():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(8);
        inlet = 14; messagename = 'set'; anything(2, 5);     // lock step 2 -> slice 5
        inlet = 14; messagename = 'trigger'; anything(2);
    """)
    assert _steps(r)[0][8] == 5            # h0 == locked slice index


def test_pattern_seed_is_deterministic_and_reseeds():
    def phrase(seed):
        r = _run("""
            inlet = 1; msg_float(16);
            inlet = 0; msg_float(8);
            inlet = 3; msg_float(2);
            inlet = 5; msg_float(SEED);
            var p = [], i;
            for (i = 0; i < 8; i++) p.push(step_index(i));
            dump({p: p});
        """.replace("SEED", str(seed)))
        return r.state["p"]

    assert phrase(11) == phrase(11)        # same seed -> identical phrase
    assert phrase(11) != phrase(40)        # reseed (PHRASE GEN) -> new phrase


def _rows(result):
    # bare pattern-table rows: outlet 2, leading int key (no 'step' selector)
    return [o for o in result.outlets
            if o[0] == 2 and len(o) > 1 and not isinstance(o[1], str)]


def test_dumppattern_emits_one_row_per_step():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(8);
        __captured.outlets.length = 0;     // drop the auto-dumps from setup
        dumppattern();
    """)
    rows = _rows(r)
    assert len(rows) == 8
    # row: [2, step, gate, pitch, dir, nHits, level, h0, h1, h2, h3]
    assert [row[1] for row in rows] == list(range(8))
    for row in rows:
        assert row[2] in (0, 1)                    # gate
        assert row[4] in (-1, 1)                   # dir
        assert row[5] >= 1                         # nHits
        assert row[6] in (0.0, 0.45, 1.0, 1.25)    # CHOP volume tier
        assert 0 <= row[7] < 16                    # h0 in slice range


def test_every_pattern_change_auto_dumps():
    r = _run("""
        inlet = 0; msg_float(4);                   // step_count change -> dump
    """)
    assert len(_rows(r)) == 4                      # one fresh table
    r2 = _run("""
        inlet = 0; msg_float(4);
        __captured.outlets.length = 0;
        inlet = 14; messagename = 'set'; anything(1, 5);   // lock -> re-dump
    """)
    assert len(_rows(r2)) == 4
    r3 = _run("""
        inlet = 0; msg_float(4);
        __captured.outlets.length = 0;
        inlet = 10; msg_float(2);                  // PLAYHEAD must NOT dump
    """)
    assert _rows(r3) == []


def test_roll_and_reverse_distances():
    # ROLL: distance 0 -> every step resolves to slice 0 (host adds the held
    # key's offset); REV: distance -1 walks backward through the slices.
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(8);
        inlet = 3; msg_float(0);                   // RUN
        inlet = 2; msg_float(0);                   // ROLL
        var roll = [], i;
        for (i = 0; i < 8; i++) roll.push(step_index(i));
        inlet = 2; msg_float(-1);                  // REV traversal
        var rev = [], j;
        for (j = 0; j < 8; j++) rev.push(step_index(j));
        dump({roll: roll, rev: rev});
    """)
    assert r.state["roll"] == [0] * 8
    assert r.state["rev"] == [0, 15, 14, 13, 12, 11, 10, 9]


def test_mode_off_is_accepted():
    r = _run("""
        inlet = 3; msg_float(-1);
        dump({m: mode});
    """)
    assert r.state["m"] == -1


def test_ratchets_emit_sub_hits():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(8);
        inlet = 8; msg_float(100);         // glitch_amount max -> ratchets likely
        inlet = 9; msg_float(53);
        var found = -1, i;
        for (i = 0; i < 8; i++) if (step_ratchet_count(i) > 0) { found = i; break; }
        dump({found: found});
    """)
    if r.state["found"] >= 0:
        step = r.state["found"]
        r2 = _run("""
            inlet = 1; msg_float(16);
            inlet = 0; msg_float(8);
            inlet = 8; msg_float(100);
            inlet = 9; msg_float(53);
            inlet = 14; messagename = 'trigger'; anything(STEP);
        """.replace("STEP", str(step)))
        o = _steps(r2)[0]
        assert o[6] > 1                    # nHits > 1 on a ratcheted step
        assert o[9] >= 0                   # at least one ratchet sub-hit index


def test_locks_survive_slice_count_changes():
    # bigger-bet 2 prerequisite: a SENS tweak (slice count change) must NOT
    # remap or erase hand-placed locks (the old normalize wrapped them).
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(8);
        inlet = 14; messagename = 'set'; anything(2, 12);   // lock step 2 -> slice 12
        inlet = 1; msg_float(8);                            // slices shrink to 8
        inlet = 1; msg_float(16);                           // ...and back
        dump({idx: locked_steps[String(2)]});
    """)
    assert r.state["idx"] == 12                             # verbatim, not wrapped


def test_set_negative_unsets_lock():
    r = _run("""
        inlet = 0; msg_float(8);
        inlet = 14; messagename = 'set'; anything(3, 5);
        inlet = 14; messagename = 'set'; anything(3, -1);   // restore-vocab unset
        dump({locked: is_step_locked(3)});
    """)
    assert r.state["locked"] == 0 or r.state["locked"] is False


def test_clear_all_requires_shift_cmd():
    r = _run("""
        inlet = 0; msg_float(8);
        inlet = 14; messagename = 'set'; anything(1, 4);
        onclick(20, 20, 1, 0, 1, 0, 0, 0);                  // bare shift: NOT clear
        var survived = is_step_locked(1);
        onclick(20, 20, 1, 1, 1, 0, 0, 0);                  // shift+cmd: clear
        dump({survived: survived, after: is_step_locked(1)});
    """)
    assert r.state["survived"] in (1, True)
    assert r.state["after"] in (0, False)


def test_chop_volume_tiers():
    # CHOP is a volume generator: at a high amount the same seed family
    # yields mutes (0), ducks (0.45), accents (1.25) AND full steps together,
    # deterministically per seed.
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(32);
        inlet = 6; msg_float(60);          // GAPS amount
        inlet = 7; msg_float(37);          // chop seed
        var t = {}, i;
        for (i = 0; i < 32; i++) { var l = step_level(i); t[l] = (t[l] || 0) + 1; }
        var again = [], j;
        for (j = 0; j < 32; j++) again.push(step_level(j));
        var again2 = [], k;
        for (k = 0; k < 32; k++) again2.push(step_level(k));
        dump({tiers: t, stable: JSON.stringify(again) === JSON.stringify(again2)});
    """)
    tiers = {float(k): v for k, v in r.state["tiers"].items()}
    assert tiers.get(0.45, 0) > 0          # ducks present
    assert tiers.get(1.25, 0) > 0          # accents present
    assert tiers.get(0.0, 0) > 0           # mutes present
    assert r.state["stable"] in (1, True)  # deterministic per seed


def test_zero_chop_is_all_full_volume():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(16);
        inlet = 6; msg_float(0);
        var mx = 1.0, mn = 1.0, i;
        for (i = 0; i < 16; i++) { var l = step_level(i); if (l > mx) mx = l; if (l < mn) mn = l; }
        dump({mx: mx, mn: mn});
    """)
    assert r.state["mx"] == 1.0 and r.state["mn"] == 1.0


def _snapshot_driver(extra=""):
    # full derived-pattern snapshot: index/gate/ratchet/pitch per step
    return """
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(16);
        inlet = 3; msg_float(2);           // PAT
        inlet = 5; msg_float(11);
        inlet = 6; msg_float(40);          // some chop so gates vary
        inlet = 7; msg_float(37);
        EXTRA
        var snap = [], i;
        for (i = 0; i < 16; i++) {
            snap.push([step_index(i), step_gate(i),
                       step_ratchet_count(i), step_pitch(i)]);
        }
        dump({snap: snap});
    """.replace("EXTRA", extra)


def test_variation_defaults_are_inert():
    # v6 back-compat: salts/bar/active alone change NOTHING — the amounts
    # are the gates. (scale_mode 0 must also be byte-parity — tested below.)
    base = _run(_snapshot_driver()).state["snap"]
    armed = _run(_snapshot_driver("""
        inlet = 16; msg_float(4242);       // vary salt, amount still 0
        inlet = 19; msg_float(5);          // form bar
        inlet = 20; msg_float(1);          // fill active, amount still 0
    """)).state["snap"]
    assert armed == base


def test_vary_mutates_deterministically():
    base = _run(_snapshot_driver()).state["snap"]
    a = _run(_snapshot_driver("""
        inlet = 16; msg_float(4242);
        inlet = 15; msg_float(45);
    """)).state["snap"]
    b = _run(_snapshot_driver("""
        inlet = 16; msg_float(4242);
        inlet = 15; msg_float(45);
    """)).state["snap"]
    c = _run(_snapshot_driver("""
        inlet = 16; msg_float(777);
        inlet = 15; msg_float(45);
    """)).state["snap"]
    assert a != base                       # mutation bites
    assert a == b                          # same salt+amount = same variant
    assert c != a                          # new salt = new variant


def test_vary_touch_count_grows_with_amount():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(32);
        inlet = 16; msg_float(4242);
        var count_at = function (amt) {
            inlet = 15; msg_float(amt);
            var n = 0, i;
            for (i = 0; i < 32; i++) if (step_mutated(i)) n++;
            return n;
        };
        dump({lo: count_at(15), hi: count_at(90)});
    """)
    assert 0 < r.state["lo"] <= r.state["hi"]


def test_locks_win_over_mutation():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(16);
        inlet = 14; messagename = 'set'; anything(2, 9);      // slice lock
        inlet = 14; messagename = 'gateset'; anything(2, 1);  // gate lock ON
        inlet = 16; msg_float(4242);
        inlet = 15; msg_float(100);
        inlet = 17; msg_float(100);
        inlet = 19; msg_float(3);
        dump({idx: step_index(2), gate: step_gate(2)});
    """)
    assert r.state["idx"] == 9
    assert r.state["gate"] == 1


def test_drift_loops_per_bar():
    def bar_snap(bar):
        return _run(_snapshot_driver("""
            inlet = 17; msg_float(60);
            inlet = 19; msg_float(BAR);
        """.replace("BAR", str(bar)))).state["snap"]

    b3a = bar_snap(3)
    b5 = bar_snap(5)
    b3b = bar_snap(3)
    assert b3a == b3b                      # same bar = the same variant
    assert b3a != b5                       # different bar = different variant


def test_fill_transforms_last_quarter_only():
    base = _run(_snapshot_driver()).state["snap"]
    filled = _run(_snapshot_driver("""
        inlet = 18; msg_float(90);
        inlet = 20; msg_float(1);
    """)).state["snap"]
    assert filled[:12] == base[:12]        # zone = last 4 of 16 only
    assert filled[12:] != base[12:]
    inert = _run(_snapshot_driver("""
        inlet = 18; msg_float(90);
        inlet = 20; msg_float(0);          // not the last bar -> no fill
    """)).state["snap"]
    assert inert == base


def test_fill_unmutes_and_ratchets_the_zone():
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(16);
        inlet = 6; msg_float(100);         // chop everything...
        inlet = 18; msg_float(100);
        inlet = 20; msg_float(1);
        var gates = [], hits = [], i;
        for (i = 12; i < 16; i++) { gates.push(step_gate(i)); hits.push(step_ratchet_count(i)); }
        dump({gates: gates, hits: hits});
    """)
    assert any(g == 1 for g in r.state["gates"])   # fill punches through
    assert any(h >= 2 for h in r.state["hits"])    # burst bias


def test_scale_zero_is_byte_parity_and_scales_differ():
    r = _run("""
        var v5 = [0.0, 3.0, 7.0, 10.0, 12.0, 15.0, 19.0, 24.0];
        var parity = [], i;
        for (i = 0; i < 8; i++) parity.push(arp_semitone(i) === v5[i]);
        inlet = 21; msg_float(2);          // major
        var major = [], j;
        for (j = 0; j < 8; j++) major.push(arp_semitone(j));
        dump({parity: parity, major: major, v5: v5});
    """)
    assert all(r.state["parity"])
    assert r.state["major"] != r.state["v5"]


def test_gate_lock_overrides_level():
    # a gate-locked-ON step never mutes even under full chop; locked-OFF -> 0.
    r = _run("""
        inlet = 1; msg_float(16);
        inlet = 0; msg_float(8);
        inlet = 6; msg_float(100);
        inlet = 14; messagename = 'gateset'; anything(2, 1);   // force ON
        inlet = 14; messagename = 'gateset'; anything(3, 0);   // force OFF
        dump({on: step_level(2) > 0, off: step_level(3)});
    """)
    assert r.state["on"] in (1, True)
    assert r.state["off"] == 0.0
