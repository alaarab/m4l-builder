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
    # [2, "step", stepNum, gate, pitch, dir, nHits, h0, h1, h2, h3]
    o = s[0]
    assert o[2] == 3                       # step number echoed
    assert o[3] in (0, 1)                  # gate
    assert o[5] in (-1, 1)                 # direction
    assert o[6] >= 1                       # nHits >= 1
    assert 0 <= o[7] < 16                  # main slice index in range


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
    assert _steps(r)[0][7] == 5            # h0 == locked slice index


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
    # row: [2, step, gate, pitch, dir, nHits, h0, h1, h2, h3]
    assert [row[1] for row in rows] == list(range(8))
    for row in rows:
        assert row[2] in (0, 1)                    # gate
        assert row[4] in (-1, 1)                   # dir
        assert row[5] >= 1                         # nHits
        assert 0 <= row[6] < 16                    # h0 in slice range


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
        assert o[8] >= 0                   # at least one ratchet sub-hit index
