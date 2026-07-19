"""Validated wiring-idiom helpers (m4l_builder.idioms) — they encode the traps
that shipped as real bugs (expr ternary, float modulo, bang->change, cold inlet)."""
import pytest

from m4l_builder import (
    AudioEffect,
    control_smooth,
    debounce,
    dedupe_value,
    expr_cond,
    expr_safe_mod,
    init_prime,
)


def _dev():
    return AudioEffect("t", width=300, height=168)


def _texts(d):
    return [b["box"].get("text", "") for b in d.boxes]


def _lines(d):
    return [(l["patchline"]["source"][0], l["patchline"]["source"][1],
             l["patchline"]["destination"][0], l["patchline"]["destination"][1])
            for l in d.lines]


def test_all_exported_and_callable():
    assert all(callable(f) for f in (expr_cond, expr_safe_mod, debounce, dedupe_value, init_prime))


def test_expr_cond_is_branchless():
    assert expr_cond(("$i1==0", "1"), ("$i1==1", "$i3")) == "($i1==0)*(1) + ($i1==1)*($i3)"


def test_expr_cond_rejects_ternary():
    with pytest.raises(ValueError):
        expr_cond(("$i1 > 0 ? 1 : 0", "1"))
    with pytest.raises(ValueError):
        expr_cond(("$i1==0", "$i2 ? 1 : 0"))


def test_expr_safe_mod_guards_zero_and_stays_int():
    assert expr_safe_mod("$i2", "$i1/10") == "($i2) % (($i1/10)+(($i1/10)==0))"


def test_debounce_wiring():
    d = _dev()
    debounce(d, "db", "src", "tgt", ms=200)
    t = _texts(d)
    assert "t b f" in t and "delay 200" in t and "float" in t
    L = _lines(d)
    assert ("src", 0, "db_t", 0) in L         # source -> trigger
    assert ("db_t", 1, "db_f", 1) in L        # latest value stored cold
    assert ("db_t", 0, "db_d", 0) in L        # restart timer
    assert ("db_d", 0, "db_f", 0) in L        # settle -> emit
    assert ("db_f", 0, "tgt", 0) in L         # -> target


def test_dedupe_value_uses_change_on_a_number():
    d = _dev()
    dedupe_value(d, "dv", "src", "tgt")
    assert "change" in _texts(d)
    L = _lines(d)
    assert ("src", 0, "dv_chg", 0) in L and ("dv_chg", 0, "tgt", 0) in L


def test_init_prime_loadmess():
    d = _dev()
    init_prime(d, "ip", "tgt", 100)
    assert "loadmess 100" in _texts(d)
    assert ("ip_prime", 0, "tgt", 0) in _lines(d)


def test_control_smooth_with_and_without_scale():
    d = _dev()
    ln = control_smooth(d, "cut", "cut_dial", "scale 0. 127. 20. 20000.", 40)
    assert ln == "cut_ln"
    t = _texts(d)
    assert "scale 0. 127. 20. 20000." in t and "pack f 20" in t and "line~" in t
    L = _lines(d)
    assert ("cut_dial", 0, "cut_scale", 0) in L    # dial -> scale
    assert ("cut_scale", 0, "cut_pk", 0) in L      # scale -> pack
    assert ("cut_pk", 0, "cut_ln", 0) in L         # pack -> line~
    d2 = _dev()
    control_smooth(d2, "g", "g_dial", None, 40)    # scale_text=None skips the scale obj
    assert ("g_dial", 0, "g_pk", 0) in _lines(d2)
    assert not any("scale" in x for x in _texts(d2))
