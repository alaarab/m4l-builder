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
