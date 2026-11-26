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
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(out, expected, strict=False))


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
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(got, ref, strict=False))
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
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(flat, sig, strict=False))
    driven = simulate(db, {"in1": sig}, params={"drv": 1.0}, num_samples=5)["out1"]
    assert any(not isclose(a, b, abs_tol=1e-6) for a, b in zip(driven, sig, strict=False))


def test_ms_width_null_test_identity_and_mono():
    mw = "Param w(1.);\n" + ms_width("in1", "in2", "out1", "out2", "w")
    left, right = [0.6, -0.2, 0.5], [0.1, 0.4, -0.3]
    ident = simulate(mw, {"in1": left, "in2": right}, params={"w": 1.0}, num_samples=3)
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(ident["out1"], left, strict=False))
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(ident["out2"], right, strict=False))
    mono = simulate(mw, {"in1": left, "in2": right}, params={"w": 0.0}, num_samples=3)
    assert all(isclose(a, b, abs_tol=1e-12)
               for a, b in zip(mono["out1"], mono["out2"], strict=False))


# ── if / else / else-if control flow ─────────────────────────────────────────
def test_if_else_branches():
    k = "out1 = 0.;\nif (in1 > 0.5) {\n  out1 = 10.;\n} else {\n  out1 = 20.;\n}"
    assert simulate(k, {"in1": [0.7, 0.3]}, num_samples=2)["out1"] == [10.0, 20.0]


def test_else_if_chain():
    k = ("out1 = 0.;\nif (in1 > 0.7) { out1 = 3.; } "
         "else if (in1 > 0.4) { out1 = 2.; } else { out1 = 1.; }")
    assert simulate(k, {"in1": [0.9, 0.5, 0.1]}, num_samples=3)["out1"] == [3.0, 2.0, 1.0]


def test_nested_if():
    k = ("out1 = 0.;\nif (in1 > 0.5) {\n"
         "  if (in2 > 0.5) { out1 = 11.; } else { out1 = 10.; }\n"
         "} else { out1 = 0.; }")
    out = simulate(k, {"in1": [1., 1., 0.], "in2": [1., 0., 1.]}, num_samples=3)["out1"]
    assert out == [11.0, 10.0, 0.0]


def test_history_written_in_mutually_exclusive_branches():
    # legitimate (only the taken branch runs); was wrongly refused before if/else.
    k = ("History s(0.);\n"
         "if (in1 > 0.5) { s = s + 1.; } else { s = s - 0.5; }\nout1 = s;")
    out = simulate(k, {"in1": [1., 1., 0., 0.]}, num_samples=4)["out1"]
    assert out == [1.0, 2.0, 1.5, 1.0]


def test_and_condition_with_double_bound():
    # gen '&&' inside a condition (the soft-knee guard form: a > lo && b > 0).
    k = ("out1 = 0.;\nif (in1 > -1. && in2 > 0.01) { out1 = 1.; }")
    assert simulate(k, {"in1": [0., 0.], "in2": [1., 0.]}, num_samples=2)["out1"] == [1.0, 0.0]


# ── user function definitions ────────────────────────────────────────────────
_ACC_FN = "acc(x) {\n\tHistory s(0);\n\ts = s + x;\n\treturn s;\n}\n"


def test_every_function_call_site_keeps_its_own_history():
    # gen gives each call site its own state, including sites nested in another
    # function: twice(n) = two independent running sums of n.
    k = (_ACC_FN + "twice(x) {\n\treturn acc(x) + acc(x);\n}\n"
         "out1 = acc(1);\nout2 = twice(in1);")
    out = simulate(k, {"in1": [10., 10., 10.]})
    assert out["out1"] == [1., 2., 3.]
    assert out["out2"] == [20., 40., 60.]


def test_declarations_may_precede_function_definitions():
    k = "Param g(2.);\nHistory h(0.);\n" + _ACC_FN + "h = acc(in1) * g;\nout1 = h;"
    assert simulate(k, {"in1": [1., 1., 1.]})["out1"] == [2., 4., 6.]


def test_function_takes_a_delay_line_and_returns_two_values():
    k = ("tap(x, d) {\n\tlate = d.read(2);\n\td.write(x);\n\treturn x, late;\n}\n"
         "Delay line(8);\nnow, past = tap(in1, line);\nout1 = now;\nout2 = past;")
    out = simulate(k, {"in1": [1., 2., 3., 4.]})
    assert out["out1"] == [1., 2., 3., 4.]
    assert out["out2"] == [0., 0., 1., 2.]


# ── refusal of the out-of-subset constructs (never a false green) ────────────
@pytest.mark.parametrize("code,label", [
    ("Delay d(512);\nout1 = d.read(10, interp=\"spline\");\nd.write(in1);", "Delay spline interp"),
    ('Buffer b("tbl");\nout1 = peek(b, 3);', "Buffer"),
    ('Data d(8);\nout1 = peek(d, 2, 0, interp="linear");', "peek option"),
    ("out1 = in1; for (i = 0; i < 3; i = i + 1) { out1 = out1 + 1.; }", "for-loop"),
    ("out1 = data[3];", "indexed access"),
    ("f(x) {\n\tx = x + 1;\n}\nout1 = f(in1);", "function without return"),
    ("out1 = in1;\nreturn out1;", "return outside a function"),
    ("out1 = phasor(10.);", "operator the simulator does not model"),
    ("out1 = in1 / (in1 - 1.);", "division by zero"),
    ("if (in1 > 0.) { out2 = 1.; }\nout1 = in1;", "output not assigned on every sample"),
])
def test_refuses_unsupported_constructs(code, label):
    with pytest.raises(UnsupportedKernel):
        GenKernel(code).run({"in1": [1.0, 0.0]})


def test_runtime_refusal_names_the_sample():
    with pytest.raises(UnsupportedKernel, match="sample 2: unknown name 'later'"):
        simulate("out1 = in1 > 0.5 ? later : 0.;", {"in1": [0., 0., 1.]})


# ── approximate constructs are run, but always declared ─────────────────────
def test_noise_is_seeded_bounded_and_declared_approximate():
    kernel = GenKernel("out1 = noise();")
    assert kernel.approximations and "noise()" in kernel.approximations[0]
    first = kernel.run(num_samples=2000)["out1"]
    assert all(-1.0 <= v < 1.0 for v in first) and max(first) - min(first) > 1.5
    assert kernel.run(num_samples=2000)["out1"] == first
    assert kernel.run(num_samples=2000, seed=1)["out1"] != first
    with pytest.raises(UnsupportedKernel, match="strict"):
        GenKernel("out1 = noise();", strict=True)


def test_cubic_delay_read_is_exact_on_taps_and_on_a_cubic():
    # 4-point Lagrange reproduces any cubic exactly, and hits whole taps exactly.
    sig = [0.001 * n ** 3 - 0.02 * n ** 2 + 0.3 * n for n in range(40)]
    kernel = GenKernel('Delay d(64);\nd.write(in1);\n'
                       'out1 = d.read(5, interp="cubic");\nout2 = d.read(5.25, interp="cubic");')
    assert kernel.approximations and "cubic" in kernel.approximations[0]
    out = kernel.run({"in1": sig})
    for n in range(10, 40):
        assert out["out1"][n] == pytest.approx(sig[n - 5], abs=1e-12)
        assert out["out2"][n] == pytest.approx(
            0.001 * (n - 5.25) ** 3 - 0.02 * (n - 5.25) ** 2 + 0.3 * (n - 5.25), abs=1e-9)


def test_exact_kernels_declare_no_approximations():
    assert GenKernel('Delay d(8);\nout1 = d.read(1.5, interp="linear");\nd.write(in1);'
                     ).approximations == []


# ── fold / change / compound assignment / Data ───────────────────────────────
def test_fold_reflects_into_the_range():
    out = simulate("out1 = fold(in1, 0., 1.);", {"in1": [0.25, 1.3, -0.2, 2.5, 3.75]})
    assert out["out1"] == pytest.approx([0.25, 0.7, 0.2, 0.5, 0.25])


def test_change_is_the_sign_of_the_step_per_call_site():
    k = ("hold(x) {\n\treturn change(x);\n}\n"
         "out1 = change(in1);\nout2 = hold(in1) + hold(-in1);")
    out = simulate(k, {"in1": [0., 1., 1., .5, 2.]})
    assert out["out1"] == [0., 1., 0., -1., 1.]
    assert out["out2"] == [0., 0., 0., 0., 0.]   # two sites, opposite signs


def test_compound_assignment():
    out = simulate("History h(0.);\nh += in1;\nout1 = h;\nout2 = in1;\nout2 *= 3.;",
                   {"in1": [1., 2., 3.]})
    assert out["out1"] == [1., 3., 6.]
    assert out["out2"] == [3., 6., 9.]


def test_data_ring_buffer_delays_by_three_samples():
    k = ("Data buf(16);\nHistory w(0);\n"
         "poke(buf, in1, w, 0);\n"
         "out1 = peek(buf, wrap(w - 3, 0, dim(buf)), 0);\n"
         "w = wrap(w + 1, 0, dim(buf));")
    sig = [0., 0., 1., .5, 0., .25, 0., 0., 0., 0.]
    assert simulate(k, {"in1": sig})["out1"] == [0., 0., 0., 0., 0., 1., .5, 0., .25, 0.]


def test_data_out_of_range_reads_zero_and_writes_are_dropped():
    k = ("Data d(4, 2);\n"
         "poke(d, 7., 9, 0);\npoke(d, 5., 1, 3);\npoke(d, in1, 1, 1);\n"
         "out1 = peek(d, 9, 0);\nout2 = peek(d, 1, 1);\nout3 = channels(d);")
    out = simulate(k, {"in1": [2.]})
    assert (out["out1"], out["out2"], out["out3"]) == ([0.], [2.], [2.])


def test_delay_read_before_write_sees_the_past():
    k = "Delay d(64);\nout1 = d.read(3);\nd.write(in1);"
    assert simulate(k, {"in1": [1., 0., 0., 0., 0.]})["out1"] == [0., 0., 0., 1., 0.]


def test_delay_read_after_write_sees_the_current_sample_at_tap_zero():
    k = "Delay d(8);\nd.write(in1);\nout1 = d.read(0);"
    assert simulate(k, {"in1": [.5, .25]})["out1"] == [.5, .25]


def test_delay_linear_read_interpolates_between_taps():
    k = "Delay d(16);\nout1 = d.read(2.25, interp=\"linear\");\nd.write(in1);"
    assert simulate(k, {"in1": [1., 0., 0., 0., 0.]})["out1"] == pytest.approx([0., 0., .75, .25, 0.])


def test_delay_feedback_comb_decays_by_its_feedback():
    k = ("Delay d(32);\nHistory y(0.);\n"
         "y = in1 + 0.5 * d.read(4);\nd.write(y);\nout1 = y;")
    out = simulate(k, {"in1": [1.] + [0.] * 12})["out1"]
    assert out[0] == 1. and out[4] == .5 and out[8] == .25 and out[12] == .125


def test_num_outs_autodetected():
    assert GenKernel("out1 = in1;\nout3 = in1 * 2.;").num_outs == 3


def test_num_outs_counts_assignments_inside_branches():
    k = "if (in1 > 0.) { out1 = 1.; out2 = 2.; } else { out1 = 0.; }"
    assert GenKernel(k).num_outs == 2


# ── fixdenorm (Q44 denormal-flush primitive) ─────────────────────────────────
def test_fixdenorm_is_identity_for_normals_and_zero():
    out = simulate("out1 = fixdenorm(in1);",
                   {"in1": [0.0, 1.0, -0.5, 1e-300, -1e-300]}, num_samples=5)["out1"]
    assert out == [0.0, 1.0, -0.5, 1e-300, -1e-300]


def test_fixdenorm_flushes_subnormals_to_zero():
    sub = 5e-324  # smallest positive subnormal double
    out = simulate("out1 = fixdenorm(in1);",
                   {"in1": [sub, -sub]}, num_samples=2)["out1"]
    assert out == [0.0, 0.0]


def test_flushed_one_pole_matches_unflushed_for_normal_signals():
    # bit-transparency proof: the flushed one-pole recurrence equals the bare
    # recurrence sample-for-sample on a normal-range signal.
    from m4l_builder.gen_snippets import one_pole_lp
    sig = [0.5, -0.25, 1.0, 0.0, 0.125, -1.0, 0.75, 0.0]
    flushed = ("History s(0.);\n" + one_pole_lp("in1", "s", "0.3", "y")
               + "\nout1 = y;")
    bare = ("History s(0.);\ns = s + 0.3 * (in1 - s);\ny = s;\nout1 = y;")
    a = simulate(flushed, {"in1": sig}, num_samples=len(sig))["out1"]
    b = simulate(bare, {"in1": sig}, num_samples=len(sig))["out1"]
    assert a == b
