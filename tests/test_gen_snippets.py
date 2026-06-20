"""Tests for the composable GenExpr snippet registry (m4l_builder.gen_snippets).

The M/S primitives are pure arithmetic, so the emitted GenExpr is also valid
Python — we can exec it to behaviourally verify the math (round-trip identity,
mono/wide), not just snapshot the text.
"""
from m4l_builder.gen_snippets import ms_decode, ms_encode, ms_width


def _run(code, **vars):
    ns = dict(vars)
    exec(code, ns)  # GenExpr +,-,* and numeric literals are valid Python
    return ns


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
