"""Behavioural tests for the gen~ kernel simulator (m4l_builder.gen_sim).

The simulator is the dynamic/null-test half of the gen harness (gen_lint.py is
the static half). These tests validate it against ALREADY-PROVEN references —
the isp_catmull_4x 1.25 inter-sample overshoot, closed-form exponential decay,
the peak_follower attack/release invariant — and an INDEPENDENT plain-Python
reimplementation, so a green here means the simulator reproduces gen semantics,
not just its own parser. They also exercise the simulator as a real null-test
harness on the shipped gen_snippets primitives.
"""

from math import exp, isclose

import pytest

from m4l_builder.gen_sim import GenKernel, UnsupportedKernel, simulate
from m4l_builder.gen_snippets import (
    drive_blend,
    exp_pole,
    isp_catmull_4x,
    kweight_coeffs_bs1770,
    ms_width,
    peak_follower,
)


# ── core semantics ───────────────────────────────────────────────────────────
def test_history_reads_previous_sample_then_commits():
    # one-pole lowpass step response: out = prev + 0.1*(in - prev); prev = out.
    # Proves History is read as the PRIOR sample at the top and committed at end:
    # the step response is the geometric series 0.1 * 0.9^(N-1).
    lp = "History prev(0.);\nout1 = prev + 0.1 * (in1 - prev);\nprev = out1;"
    out = simulate(lp, {"in1": [1.0, 0, 0, 0, 0]}, num_samples=5)["out1"]
    expected = [0.1, 0.09, 0.081, 0.0729, 0.06561]
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(out, expected))


def test_param_and_samplerate_are_honoured():
    k = "Param g(2.);\nout1 = in1 * g;\nout2 = samplerate;"
    o = simulate(k, {"in1": [1.0, 2.0]}, params={"g": 3.0}, samplerate=44100.0,
                 num_samples=2)
    assert o["out1"] == [3.0, 6.0]
    assert o["out2"] == [44100.0, 44100.0]


def test_nested_and_chained_ternary_precedence():
    # gen ternary is lowest-precedence + right-associative; both forms must work.
    nested = "out1 = (in1 < 0.3) ? 10. : ((in1 < 0.7) ? 20. : 30.);"
    chained = "out1 = in1 < 0.3 ? 10. : in1 < 0.7 ? 20. : 30.;"
    for code in (nested, chained):
        assert simulate(code, {"in1": [0.1, 0.5, 0.9]}, num_samples=3)["out1"] \
            == [10.0, 20.0, 30.0]


def test_ternary_branches_bind_below_arithmetic():
    # gen: `c ? a : b + d` == `(c ? a : b) + d` is NOT what we write; the audited
    # kernels parenthesise. Here confirm the false branch greedily extends:
    # `flag ? 1. : 2. + 3.` -> false branch is (2.+3.)=5.
    assert simulate("out1 = in1 > 0.5 ? 1. : 2. + 3.;",
                    {"in1": [0.0]}, num_samples=1)["out1"] == [5.0]


# ── validation against proven references ─────────────────────────────────────
def _ref_isp(seq):
    """Independent plain-Python ISP reimplementation (NOT via the simulator)."""
    xl1 = xl2 = xl3 = 0.0
    out = []
    for x in seq:
        h0, h1, h2, h3 = x, xl1, xl2, xl3
        k0 = h2
        k1 = 0.5 * (h1 - h3)
        k2 = h3 - 2.5 * h2 + 2.0 * h1 - 0.5 * h0
        k3 = 0.5 * (h0 - h3) + 1.5 * (h2 - h1)
        y1 = k0 + 0.25 * (k1 + 0.25 * (k2 + 0.25 * k3))
        y2 = k0 + 0.5 * (k1 + 0.5 * (k2 + 0.5 * k3))
        y3 = k0 + 0.75 * (k1 + 0.75 * (k2 + 0.75 * k3))
        out.append(max(max(abs(y1), abs(y2)), abs(y3)))
        xl1, xl2, xl3 = x, h1, h2
    return out


def test_isp_detector_multisample_matches_independent_reimpl():
    kernel = (
        "History xl1(0.); History xl2(0.); History xl3(0.);\n"
        + isp_catmull_4x("in1", "xl1", "xl2", "xl3", "out1", ch="l") + "\n"
        + "xl1 = in1; xl2 = h1l; xl3 = h2l;"
    )
    seq = [-1.0, 1.0, 1.0, -1.0]
    got = simulate(kernel, {"in1": seq}, num_samples=4)["out1"]
    ref = _ref_isp(seq)
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(got, ref))
    # the headline already-proven fact: the (-1,1,1,-1) window yields 1.25, the
    # inter-sample peak the sample peak (1.0) is blind to.
    assert isclose(got[3], 1.25, abs_tol=1e-12)


def test_exp_pole_free_decay_reaches_e_inverse():
    # tau = 0.1 s; after tau*samplerate = 4800 samples a free decay reaches e^-1.
    decay = ("History state(1.0);\n" + exp_pole("coeff", "0.1")
             + "\nstate = coeff * state;\nout1 = state;")
    out = simulate(decay, {"in1": [0.0] * 4801}, samplerate=48000.0,
                   num_samples=4801)["out1"]
    assert isclose(out[4800], exp(-1), abs_tol=1e-4)


def test_peak_follower_attack_is_faster_than_release():
    atk = exp(-1 / (0.001 * 48000))   # 1 ms
    rel = exp(-1 / (0.100 * 48000))   # 100 ms
    pf = ("History env(0.);\n"
          + peak_follower("in1", "env", f"{atk}", f"{rel}", "coeff")
          + "\nout1 = env;")
    out = simulate(pf, {"in1": [1.0] * 5 + [0.0] * 5}, num_samples=10)["out1"]
    # rises meaningfully on attack, barely falls on the slow release
    assert out[4] > 0.09                       # climbed toward 1.0 in 5 * 1ms
    assert (out[5] - out[9]) < 1e-3            # 100ms release barely moves in 5 samp


def test_kweight_coeffs_eval_to_48k_reference():
    # runs the shipped kweight primitive through the pure-function table and
    # reproduces the canonical ITU-R BS.1770 48k coefficients.
    code = kweight_coeffs_bs1770() + "\nout1 = sb0;\nout2 = sa1;\nout3 = ha2;"
    o = simulate(code, {"in1": [0.0]}, samplerate=48000.0, num_samples=1)
    assert isclose(o["out1"][0], 1.53512486, abs_tol=1e-6)
    assert isclose(o["out2"][0], -1.69065929, abs_tol=1e-6)
    assert isclose(o["out3"][0], 0.99007225, abs_tol=1e-6)


# ── the harness as a real null-test on shipped primitives ────────────────────
def test_drive_blend_null_test_transparent_at_zero_drive():
    db = "Param drv(0.);\n" + drive_blend("in1", "out1", "6.0", "drv")
    sig = [-0.7, 0.0, 0.3, 0.9, -0.5]
    flat = simulate(db, {"in1": sig}, params={"drv": 0.0}, num_samples=5)["out1"]
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(flat, sig))
    driven = simulate(db, {"in1": sig}, params={"drv": 1.0}, num_samples=5)["out1"]
    assert any(not isclose(a, b, abs_tol=1e-6) for a, b in zip(driven, sig))


def test_ms_width_null_test_identity_and_mono():
    mw = "Param w(1.);\n" + ms_width("in1", "in2", "out1", "out2", "w")
    left, right = [0.6, -0.2, 0.5], [0.1, 0.4, -0.3]
    ident = simulate(mw, {"in1": left, "in2": right}, params={"w": 1.0}, num_samples=3)
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(ident["out1"], left))
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(ident["out2"], right))
    mono = simulate(mw, {"in1": left, "in2": right}, params={"w": 0.0}, num_samples=3)
    assert all(isclose(a, b, abs_tol=1e-12)
               for a, b in zip(mono["out1"], mono["out2"]))


# ── refusal of the out-of-subset constructs (never a false green) ────────────
@pytest.mark.parametrize("code,label", [
    ("Delay d(512);\nout1 = d.read(10);", "Delay/.read"),
    ("History h(0.);\nh = peek(buf, 3);\nout1 = h;", "peek"),
    ("History h(0.);\nif (in1 > 0.) { h = 1.; }\nout1 = h;", "if-block"),
    ("History h(0.);\nh = in1;\nh = in1 * 2.;\nout1 = h;", "double History write"),
    ("out1 = data[3];", "indexed access"),
])
def test_refuses_unsupported_constructs(code, label):
    with pytest.raises(UnsupportedKernel):
        GenKernel(code)


def test_num_outs_autodetected():
    assert GenKernel("out1 = in1;\nout3 = in1 * 2.;").num_outs == 3
