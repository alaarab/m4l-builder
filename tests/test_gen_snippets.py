"""Tests for the composable GenExpr snippet registry (m4l_builder.gen_snippets).

The M/S primitives are pure arithmetic, so the emitted GenExpr is also valid
Python — we can exec it to behaviourally verify the math (round-trip identity,
mono/wide), not just snapshot the text.
"""
import re
from math import tanh

from m4l_builder.gen_snippets import (
    drive_blend,
    ms_decode,
    ms_encode,
    ms_width,
    peak_follower,
)


def _run(code, **vars):
    ns = {"tanh": tanh}
    ns.update(vars)
    exec(code, ns)  # GenExpr +,-,*,tanh and numeric literals are valid Python
    return ns


def _gen_to_py(code):
    # rewrite a single GenExpr ternary "lhs = cond ? a : b;" as Python so _run
    # can exec it (GenExpr ?: is not Python syntax).
    return re.sub(r"(\w+)\s*=\s*(.+?)\s*\?\s*(.+?)\s*:\s*(.+?);",
                  r"\1 = (\3 if \2 else \4)", code)


def test_ms_encode_text():
    assert ms_encode("L", "R", "M", "S") == "M = (L + R) * 0.5;\nS = (L - R) * 0.5;"


def test_ms_decode_text():
    assert ms_decode("M", "S", "L", "R") == "L = M + S;\nR = M - S;"


def test_ms_encode_decode_roundtrip_is_identity():
    code = ms_encode("L", "R", "M", "S") + "\n" + ms_decode("M", "S", "Lo", "Ro")
    ns = _run(code, L=0.61, R=-0.27)
    assert abs(ns["Lo"] - 0.61) < 1e-12
    assert abs(ns["Ro"] - (-0.27)) < 1e-12


def test_ms_width_unity_is_identity():
    ns = _run(ms_width("L", "R", "Lo", "Ro", "W"), L=0.61, R=-0.27, W=1.0)
    assert abs(ns["Lo"] - 0.61) < 1e-12
    assert abs(ns["Ro"] - (-0.27)) < 1e-12


def test_ms_width_zero_is_mono():
    ns = _run(ms_width("L", "R", "Lo", "Ro", "W"), L=0.6, R=-0.2, W=0.0)
    assert abs(ns["Lo"] - 0.2) < 1e-12  # both channels collapse to mid = (0.6-0.2)/2
    assert abs(ns["Ro"] - 0.2) < 1e-12


def test_ms_width_double_widens_side():
    ns = _run(ms_width("L", "R", "Lo", "Ro", "W"), L=0.6, R=0.2, W=2.0)
    # mid=0.4, side=(0.4/2)*2=0.4 -> Lo=0.8, Ro=0.0
    assert abs(ns["Lo"] - 0.8) < 1e-12
    assert abs(ns["Ro"] - 0.0) < 1e-12


def test_ms_width_matches_echotide_shipped_form():
    assert ms_width("wetL0", "wetR0", "wetLw", "wetRw", "wf") == (
        "mid = (wetL0 + wetR0) * 0.5;\n"
        "side = (wetL0 - wetR0) * 0.5 * wf;\n"
        "wetLw = mid + side;\n"
        "wetRw = mid - side;"
    )


def test_ms_width_custom_intermediate_names_avoid_clash():
    out = ms_width("L", "R", "Lo", "Ro", "W", mid="m2", side="s2")
    assert "m2 = (L + R) * 0.5;" in out
    assert "s2 = (L - R) * 0.5 * W;" in out
    assert "mid" not in out and "side" not in out


def test_drive_blend_text():
    assert drive_blend("x", "y", "k", "d") == "y = x + (tanh(x * k) / tanh(k) - x) * d;"


def test_drive_blend_transparent_at_zero_drive():
    for x in (-0.7, 0.0, 0.3, 0.9):
        ns = _run(drive_blend("X", "Y", "K", "D"), X=x, K=6.0, D=0.0)
        assert abs(ns["Y"] - x) < 1e-12  # bit-transparent when drive=0


def test_drive_blend_full_scale_stays_unity_at_full_drive():
    # x=1, drive=1 -> tanh(k)/tanh(k) = 1 (level-matched, no gain dump)
    ns = _run(drive_blend("X", "Y", "K", "D"), X=1.0, K=6.0, D=1.0)
    assert abs(ns["Y"] - 1.0) < 1e-12


def test_drive_blend_soft_compresses_midlevel_at_full_drive():
    # x=0.5, drive=1 -> tanh(0.5k)/tanh(k) > 0.5 (upward soft-clip gain on lower levels)
    ns = _run(drive_blend("X", "Y", "K", "D"), X=0.5, K=6.0, D=1.0)
    assert ns["Y"] > 0.5
    assert ns["Y"] == tanh(0.5 * 6.0) / tanh(6.0)


def test_drive_blend_matches_echotide_shipped_form():
    assert drive_blend("fbcL", "fbL", "k", "drv") == (
        "fbL = fbcL + (tanh(fbcL * k) / tanh(k) - fbcL) * drv;"
    )


def test_peak_follower_text():
    assert peak_follower("dpk", "denv", "0.6", "0.9997", "dcoeff") == (
        "dcoeff = dpk > denv ? 0.6 : 0.9997;\n"
        "denv = dpk + dcoeff * (denv - dpk);"
    )


def test_peak_follower_attack_fast_release_slow():
    code = _gen_to_py(peak_follower("P", "S", "AC", "RC", "C"))
    # attack: input above the envelope -> uses AC (small pole = fast rise)
    ns = _run(code, P=1.0, S=0.0, AC=0.1, RC=0.9)
    assert abs(ns["S"] - 0.9) < 1e-12       # rose 0 -> 0.9 in one step
    assert abs(ns["C"] - 0.1) < 1e-12       # picked the attack coeff
    # release: input below the envelope -> uses RC (big pole = slow fall)
    ns2 = _run(code, P=0.0, S=1.0, AC=0.1, RC=0.9)
    assert abs(ns2["S"] - 0.9) < 1e-12      # fell only 1.0 -> 0.9
    assert abs(ns2["C"] - 0.9) < 1e-12      # picked the release coeff


def test_peak_follower_matches_echotide_wet_env_form():
    assert peak_follower("wpk", "env", "0.6", "0.995", "coeff") == (
        "coeff = wpk > env ? 0.6 : 0.995;\n"
        "env = wpk + coeff * (env - wpk);"
    )
