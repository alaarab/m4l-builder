"""Behavioral tests for the seed_history "dice brain" (Node harness).

The brain owns Shard's DICE policy and undo ring so those semantics are
testable here instead of living as pak-assembly hazards in the patch.
"""

import os

import pytest

from m4l_builder.engines.seed_history import (
    SEED_HISTORY_OUTLETS,
    seed_history_js,
)

from .js_harness import NODE, run_jsui

pytestmark = pytest.mark.skipif(
    not (NODE and os.path.exists(NODE)), reason="node not available"
)


def _run(driver):
    return run_jsui(seed_history_js(), driver, size=(10, 10))


def _seed_events(result):
    return [o[2:] for o in result.outlets if o[0] == 0 and o[1] == "seeds"]


def _pos_events(result):
    return [o[2:] for o in result.outlets if o[0] == 1 and o[1] == "pos"]


def test_outlet_count():
    assert SEED_HISTORY_OUTLETS == 2


def test_roll_is_deterministic():
    a = _run("seeds(1, 2, 3, 4, 5); roll(1234, 0);")
    b = _run("seeds(1, 2, 3, 4, 5); roll(1234, 0);")
    c = _run("seeds(1, 2, 3, 4, 5); roll(4321, 0);")
    assert _seed_events(a) == _seed_events(b)
    assert _seed_events(a) != _seed_events(c)


def test_vary_threshold_policy():
    # 0 < vary < 70 -> salt-only (seeds stay); vary 0 or >= 70 -> full reseed
    mid = _seed_events(_run("seeds(1, 2, 3, 4, 5); roll(999, 30);"))[0]
    assert mid[:4] == [1, 2, 3, 4]         # groove kept
    assert mid[4] != 5                     # fresh mutation salt
    zero = _seed_events(_run("seeds(1, 2, 3, 4, 5); roll(999, 0);"))[0]
    wild = _seed_events(_run("seeds(1, 2, 3, 4, 5); roll(999, 85);"))[0]
    assert zero[:4] != [1, 2, 3, 4]        # classic dice
    assert wild[:4] != [1, 2, 3, 4]
    assert zero == wild                    # same rand -> same full reseed


def test_history_walk_and_undo_truncation():
    r = _run("""
        seeds(1, 2, 3, 4, 5);
        roll(100, 0); roll(200, 0); roll(300, 0);
        back(); back();
        fwd();
        roll(400, 0);                       // forks: truncates the redo tail
        fwd();                              // inert at the head now
        back();
    """)
    seeds = _seed_events(r)
    # emissions: roll a, b, c; back->b; back->a; fwd->b; roll d; back->b
    assert len(seeds) == 8
    a, b, c = seeds[0], seeds[1], seeds[2]
    assert seeds[3] == b and seeds[4] == a
    assert seeds[5] == b
    d = seeds[6]
    assert d not in (a, b, c)              # the fork is a fresh roll
    assert seeds[7] == b                   # after the fork, back lands on b
    pos = _pos_events(r)
    # ring = [primed, a, b, d] after the fork -> b sits at index 2 of 4
    assert pos[-1][0] == 2
    assert pos[-1][1] == 4                 # the c tail was truncated


def test_ring_caps_at_depth():
    r = _run("""
        seeds(1, 2, 3, 4, 5);
        var i;
        for (i = 0; i < 12; i++) roll(1000 + i, 0);
    """)
    assert _pos_events(r)[-1][1] == 8      # DEPTH=8 cap
    assert _pos_events(r)[-1][0] == 7


def test_field_sync_keeps_current_honest():
    # individual GEN buttons sync fields silently; the next walk reflects them
    r = _run("""
        seeds(1, 2, 3, 4, 5);
        seedc(777);                         // e.g. CHOP button rolled
        roll(50, 30);                       // salt-only: keeps synced seeds
    """)
    assert _seed_events(r)[0][:4] == [1, 777, 3, 4]


def test_back_at_tail_and_fwd_at_head_are_inert():
    r = _run("seeds(1, 2, 3, 4, 5); back(); fwd();")
    assert _seed_events(r) == []           # no movement, no emission


def test_first_roll_archives_the_original_groove():
    # the device primes FIELDS (seedp/seedc/...) rather than the ring; the
    # first DICE press must still let `back` return to the pre-roll state
    r = _run("""
        seedp(1); seedc(2); seedg(3); seedm(4); seedv(5);
        roll(1234, 0);
        back();
    """)
    seeds = _seed_events(r)
    assert len(seeds) == 2
    assert seeds[1] == [1, 2, 3, 4, 5]     # back -> the original groove
