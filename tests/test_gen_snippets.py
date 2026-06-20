"""Tests for the composable GenExpr snippet registry (m4l_builder.gen_snippets).

The M/S primitives are pure arithmetic, so the emitted GenExpr is also valid
Python — we can exec it to behaviourally verify the math (round-trip identity,
mono/wide), not just snapshot the text.
"""
import re
from math import pow, tan, tanh

from m4l_builder.gen_snippets import (
    biquad_cascade,
    biquad_df1,
    butterworth_q_table,
    drive_blend,
    dynamics_band,
    exciter_harmonics,
    exp_pole,
    isp_catmull_4x,
    kweight_coeffs_bs1770,
    lr_crossover,
    ms_decode,
    ms_encode,
    ms_width,
    one_pole_coeff,
    one_pole_hp,
    one_pole_lp,
    peak_follower,
    rbj_highpass,
    rbj_lowpass,
    rbj_peaking,
    rbj_shelf,
    soft_knee_gain_computer,
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


# --- isp_catmull_4x: 4x inter-sample-peak detector (Catmull-Rom) -------------
# Pure polynomial arithmetic (+,-,*, max, abs), so the emitted GenExpr execs as
# Python directly. The window is (h3,h2,h1,h0) = oldest..newest; the primitive
# fits a cubic through it and evaluates t=.25/.5/.75 between h2 and h1.

def _run_isp(h3, h2, h1, h0):
    code = isp_catmull_4x("x", "h1", "h2", "h3", "isp", ch="l")
    ns = {"x": h0, "h1": h1, "h2": h2, "h3": h3}
    exec(code, ns)  # noqa: S102 - trusted generated GenExpr
    return ns["isp"]


def test_isp_constant_window_has_no_overshoot():
    # a flat DC window -> the spline is flat -> ISP == the level (no phantom peak)
    assert abs(_run_isp(0.5, 0.5, 0.5, 0.5) - 0.5) < 1e-12
    assert abs(_run_isp(-0.3, -0.3, -0.3, -0.3) - 0.3) < 1e-12


def test_isp_detects_inter_sample_overshoot():
    # samples (-1, 1, 1, -1): both middle samples are +1 but the negative
    # neighbours bow the spline ABOVE 1 between them. Closed form y(t)=1+t-t^2,
    # peaking at t=.5 -> 1.25. ISP must catch the 1.25 inter-sample peak that the
    # sample peak (1.0) is blind to.
    assert abs(_run_isp(-1.0, 1.0, 1.0, -1.0) - 1.25) < 1e-12


def test_isp_left_and_right_channels_compute_identically():
    # ISP alone is evaluated strictly BETWEEN samples (t=.25/.5/.75), so it is
    # NOT bounded below by the sample peak — that is why callers take
    # tp = max(sample_peak, isp). What must hold is that the L and R forms are
    # the same math: identical windows -> identical ISP regardless of suffix.
    codeL = isp_catmull_4x("x", "h1", "h2", "h3", "ispL", ch="l")
    codeR = isp_catmull_4x("x", "h1", "h2", "h3", "ispR", ch="r")
    for window in [(0.2, 0.9, 0.4, -0.1), (-0.7, 0.3, 0.8, 0.1), (0.0, 1.0, -1.0, 0.0)]:
        h3, h2, h1, h0 = window
        nsL = {"x": h0, "h1": h1, "h2": h2, "h3": h3}
        nsR = dict(nsL)
        exec(codeL, nsL)  # noqa: S102
        exec(codeR, nsR)  # noqa: S102
        assert nsL["ispL"] == nsR["ispR"]


def test_isp_matches_ceiling_shipped_form():
    assert isp_catmull_4x("inL", "xl1", "xl2", "xl3", "ispl", ch="l") == (
        "h0l = inL; h1l = xl1; h2l = xl2; h3l = xl3;\n"
        "kl0 = h2l;\n"
        "kl1 = 0.5 * (h1l - h3l);\n"
        "kl2 = h3l - 2.5 * h2l + 2.0 * h1l - 0.5 * h0l;\n"
        "kl3 = 0.5 * (h0l - h3l) + 1.5 * (h2l - h1l);\n"
        "yl1 = kl0 + 0.25 * (kl1 + 0.25 * (kl2 + 0.25 * kl3));\n"
        "yl2 = kl0 + 0.5 * (kl1 + 0.5 * (kl2 + 0.5 * kl3));\n"
        "yl3 = kl0 + 0.75 * (kl1 + 0.75 * (kl2 + 0.75 * kl3));\n"
        "ispl = max(max(abs(yl1), abs(yl2)), abs(yl3));"
    )


def test_isp_right_channel_uses_r_suffix():
    code = isp_catmull_4x("inR", "xr1", "xr2", "xr3", "ispr", ch="r")
    assert code.splitlines()[0] == "h0r = inR; h1r = xr1; h2r = xr2; h3r = xr3;"
    assert code.splitlines()[-1] == "ispr = max(max(abs(yr1), abs(yr2)), abs(yr3));"


# --- kweight_coeffs_bs1770: ITU-R BS.1770-4 K-weight biquad coefficients ------
# The block carries two // comments (the magic constants are opaque), so strip
# them before exec; the math is tan/pow on the samplerate.

def _run_kweight(samplerate):
    code = kweight_coeffs_bs1770()
    py = "\n".join(l for l in code.splitlines() if not l.strip().startswith("//"))
    ns = {"tan": tan, "pow": pow, "samplerate": float(samplerate)}
    exec(py, ns)  # noqa: S102
    return ns


def test_kweight_reproduces_bs1770_48k_reference():
    # The canonical ITU-R BS.1770-4 coefficients are tabulated at 48 kHz; the gen
    # bilinear-transforms them at the live rate and must reproduce the reference.
    ns = _run_kweight(48000)
    # Stage 1 high-shelf (normalized by a0)
    assert abs(ns["sb0"] - 1.53512485958697) < 1e-9
    assert abs(ns["sb1"] - -2.69169618940638) < 1e-9
    assert abs(ns["sb2"] - 1.19839281085285) < 1e-9
    assert abs(ns["sa1"] - -1.69065929318241) < 1e-9
    assert abs(ns["sa2"] - 0.73248077421585) < 1e-9
    # Stage 2 RLB high-pass feedback coeffs
    assert abs(ns["ha1"] - -1.99004745483398) < 1e-9
    assert abs(ns["ha2"] - 0.99007225036621) < 1e-9


def test_kweight_is_samplerate_dependent():
    # not hardcoded to one rate: 96k must yield different coefficients than 48k
    c48 = _run_kweight(48000)
    c96 = _run_kweight(96000)
    assert c48["sb0"] != c96["sb0"]
    assert c48["ha1"] != c96["ha1"]


def test_kweight_matches_shipped_form():
    # guards the byte-identical migration in Ceiling + Spectrum Analyzer
    code = kweight_coeffs_bs1770()
    assert code.startswith("KPI = 3.14159265358979;\n")
    assert "Ks = tan(KPI * 1681.9744509555319 / samplerate);" in code
    assert "Kh = tan(KPI * 38.13547087613982 / samplerate);" in code
    assert code.rstrip().endswith("ha2 = (1. - Kh / 0.5003270373253953 + Kh * Kh) / a0h;")


# --- exp_pole: one-pole smoothing/ballistics coefficient exp(-1/(tau*fs)) ------

def test_exp_pole_text():
    assert exp_pole("sm", "0.0004") == "sm = exp(-1.0 / (0.0004 * samplerate));"
    assert exp_pole("atk", "atk_ms * 0.001") == \
        "atk = exp(-1.0 / (atk_ms * 0.001 * samplerate));"


def test_exp_pole_value_matches_time_constant():
    # exp(-1/(tau*fs)): a 1ms pole at 48k -> exp(-1/48) ~ 0.97937; smaller tau = faster
    from math import exp as _exp
    code = exp_pole("c", "tau")
    ns = {"exp": _exp, "tau": 0.001, "samplerate": 48000.0}
    exec(code, ns)  # noqa: S102
    assert abs(ns["c"] - _exp(-1.0 / (0.001 * 48000.0))) < 1e-15
    # faster (smaller tau) -> smaller coefficient (less retention)
    ns_fast = {"exp": _exp, "tau": 0.0001, "samplerate": 48000.0}
    exec(code, ns_fast)  # noqa: S102
    assert ns_fast["c"] < ns["c"]


def test_exp_pole_matches_ceiling_and_pressure_shipped_forms():
    assert exp_pole("rel", "max(release, 5.) * 0.001") == \
        "rel = exp(-1.0 / (max(release, 5.) * 0.001 * samplerate));"
    assert exp_pole("rel_fast", "clamp(rel_ms * 0.12, 20., 120.) * 0.001") == \
        "rel_fast = exp(-1.0 / (clamp(rel_ms * 0.12, 20., 120.) * 0.001 * samplerate));"


# --- soft_knee_gain_computer: the compressor/limiter gain-reduction curve ------
# An if/else block; null-tested behaviourally via the gen_sim simulator.
from m4l_builder.gen_sim import simulate as _sim  # noqa: E402


def _grdb(level, *, threshold=-18.0, ratio=4.0, knee=6.0):
    code = ("Param threshold(-18.);\nParam ratio(4.);\nParam knee(6.);\n"
            + soft_knee_gain_computer("in1", "threshold", "ratio", "knee", "grdb")
            + "\nout1 = grdb;")
    return _sim(code, {"in1": [level]}, params={"threshold": threshold,
                "ratio": ratio, "knee": knee}, num_samples=1)["out1"][0]


def test_soft_knee_gain_computer_matches_pressure_shipped_form():
    assert soft_knee_gain_computer("env", "threshold", "ratio", "knee", "grdb") == (
        "over = env - threshold;\n"
        "half_knee = knee * 0.5;\n"
        "slope = (1.0 / max(ratio, 1.0)) - 1.0;\n"
        "grdb = 0.;\n"
        "if (over > half_knee) {\n"
        "    grdb = over * slope;\n"
        "} else if (over > -half_knee && knee > 0.01) {\n"
        "    t = over + half_knee;\n"
        "    grdb = (t * t) / (2.0 * knee) * slope;\n"
        "}"
    )


def test_gain_computer_unity_ratio_is_transparent():
    # ratio == 1 -> slope 0 -> zero reduction at every level (the null test).
    for level in (-40.0, -18.0, 0.0, 12.0):
        assert abs(_grdb(level, ratio=1.0)) < 1e-12


def test_gain_computer_below_threshold_no_reduction():
    assert abs(_grdb(-40.0)) < 1e-12       # far below knee


def test_gain_computer_only_attenuates():
    for level in (-60.0, -18.0, -6.0, 0.0, 12.0):
        assert _grdb(level) <= 1e-12


def test_gain_computer_above_knee_is_hard_slope():
    # over = 0 - (-18) = 18, slope = 1/4 - 1 = -0.75 -> grdb = -13.5
    assert abs(_grdb(0.0) - (18.0 * (0.25 - 1.0))) < 1e-9


def test_gain_computer_custom_scratch_names_avoid_clash():
    out = soft_knee_gain_computer("L", "th", "rt", "kn", "gr",
                                  over="o2", half_knee="hk2", slope="sl2", t="t2")
    assert "o2 = L - th;" in out and "t2 = o2 + hk2;" in out
    assert "\nover " not in out and " over " not in out


# --- dynamics_band: detector -> knee -> makeup, end-to-end compressor gain path
from math import exp as _exp  # noqa: E402


def _band_kernel():
    atk = _exp(-1 / (0.001 * 48000))   # 1 ms attack
    rel = _exp(-1 / (0.100 * 48000))   # 100 ms release
    return ("History env(-90.);\n"
            "Param threshold(-18.);\nParam ratio(4.);\nParam knee(6.);\nParam makeup(0.);\n"
            + dynamics_band("in1", "env", f"{atk}", f"{rel}", "threshold", "ratio",
                            "knee", "makeup", "g")
            + "\nout1 = g;\nout2 = env;")


def _band(level, n, **params):
    return _sim(_band_kernel(), {"in1": [level] * n}, params=params, num_samples=n)


def test_dynamics_band_unity_ratio_is_transparent():
    # ratio == 1, makeup == 0 -> g converges to 1 at any input (transparent).
    out = _band(0.5, 1024, ratio=1.0, makeup=0.0, threshold=-18.0, knee=6.0)["out1"]
    assert abs(out[-1] - 1.0) < 1e-9


def test_dynamics_band_below_threshold_is_unity():
    out = _band(0.01, 1024, ratio=4.0, makeup=0.0, threshold=-18.0, knee=6.0)["out1"]
    assert abs(out[-1] - 1.0) < 1e-6   # -40 dB in, well below -18 threshold


def test_dynamics_band_hot_signal_attenuates():
    out = _band(0.9, 1024, ratio=4.0, makeup=0.0, threshold=-18.0, knee=6.0)["out1"]
    assert out[-1] < 1.0


def test_dynamics_band_makeup_raises_gain():
    out = _band(0.01, 512, ratio=4.0, makeup=6.0, threshold=-18.0, knee=6.0)["out1"]
    assert abs(out[-1] - 10 ** (6.0 / 20.0)) < 1e-4   # below threshold -> pure makeup


def test_dynamics_band_attack_is_faster_than_release():
    # a 1 ms attack settles the dB envelope near the input level within ~1000
    # samples; the 100 ms release does NOT return to the floor in the same window.
    kern = _band_kernel()
    seq = [0.9] * 1000 + [0.0001] * 1000
    env = _sim(kern, {"in1": seq}, params={"ratio": 4.0, "makeup": 0.0},
               num_samples=2000)["out2"]
    # attack: env reached close to atodb(0.9) ~= -0.9 dB by the end of the loud run
    assert env[999] > -2.0
    # release: 1000 samples later env has fallen but is FAR from the -90 floor
    assert env[1999] > -40.0
    assert env[1999] < env[999]   # it is releasing (falling)


# --- biquad_df1: one Direct-Form-I biquad stage --------------------------------
def _run_biquad(x_seq, b0, b1, b2, a1, a2):
    code = ("History x1(0.); History x2(0.); History y1(0.); History y2(0.);\n"
            + biquad_df1("in1", f"{b0}", f"{b1}", f"{b2}", f"{a1}", f"{a2}",
                         "x1", "x2", "y1", "y2", "y") + "\nout1 = y;")
    return _sim(code, {"in1": list(x_seq)}, num_samples=len(x_seq))["out1"]


def test_biquad_df1_matches_kweight_shipped_form():
    assert biquad_df1("oL", "sb0", "sb1", "sb2", "sa1", "sa2",
                      "kx1L", "kx2L", "ky1L", "ky2L", "s1L") == (
        "s1L = sb0 * oL + sb1 * kx1L + sb2 * kx2L - sa1 * ky1L - sa2 * ky2L;\n"
        "kx2L = kx1L; kx1L = oL; ky2L = ky1L; ky1L = s1L;"
    )


def test_biquad_df1_identity_passes_signal_through():
    # b0=1, all else 0 -> y == x sample for sample.
    sig = [0.3, -0.7, 1.0, 0.0, 0.5]
    out = _run_biquad(sig, 1.0, 0.0, 0.0, 0.0, 0.0)
    assert all(abs(a - b) < 1e-12 for a, b in zip(out, sig))


def test_biquad_df1_impulse_response_is_b_then_feedback():
    # impulse in -> y[0]=b0, y[1]=b1 - a1*b0, y[2]=b2 - a1*y[1] - a2*b0 (DF-I).
    b0, b1, b2, a1, a2 = 0.5, 0.2, 0.1, -0.3, 0.05
    out = _run_biquad([1.0, 0.0, 0.0, 0.0], b0, b1, b2, a1, a2)
    y0 = b0
    y1 = b1 - a1 * y0
    y2 = b2 - a1 * y1 - a2 * y0
    y3 = -a1 * y2 - a2 * y1
    for got, exp in zip(out, [y0, y1, y2, y3]):
        assert abs(got - exp) < 1e-12


def test_biquad_df1_dc_gain():
    # constant 1.0 input -> steady-state y = (b0+b1+b2)/(1+a1+a2).
    b0, b1, b2, a1, a2 = 0.2, 0.2, 0.2, -0.5, 0.1
    out = _run_biquad([1.0] * 4000, b0, b1, b2, a1, a2)
    expected = (b0 + b1 + b2) / (1.0 + a1 + a2)
    assert abs(out[-1] - expected) < 1e-9


def test_biquad_df1_stable_filter_stays_bounded():
    # a stable lowpass fed full-scale must not blow up (|y| bounded).
    # RBJ-ish stable coeffs (gentle lowpass)
    out = _run_biquad([(-1.0) ** n for n in range(2000)],
                      0.05, 0.1, 0.05, -1.6, 0.7)
    assert all(abs(v) < 10.0 for v in out)


# --- rbj_peaking: runtime peaking-EQ biquad coefficients -----------------------
def _rbj_coeffs(freq, q, gain_db, sr=48000.0):
    code = ("Param f(1000.);\nParam q(1.);\nParam g(6.);\n"
            + rbj_peaking("f", "q", "g", "b0", "b1", "b2", "a1", "a2")
            + "\nout1 = b0;\nout2 = b1;\nout3 = b2;\nout4 = a1;\nout5 = a2;")
    o = _sim(code, {"in1": [0.0]}, params={"f": freq, "q": q, "g": gain_db},
             samplerate=sr, num_samples=1)
    return [o[f"out{k}"][0] for k in range(1, 6)]


def test_rbj_peaking_matches_reference_coeffs():
    # independently computed RBJ peaking for f0=1000, Q=1, +6 dB, 48k.
    ref = [1.0439530870, -1.8953207239, 0.8677222848, -1.8953207239, 0.9116753718]
    got = _rbj_coeffs(1000.0, 1.0, 6.0)
    assert all(abs(a - b) < 1e-9 for a, b in zip(got, ref)), got


def test_rbj_peaking_zero_gain_is_unity_through_biquad():
    # gain_db = 0 -> b == a -> the band is flat: filtered output == input.
    code = ("Param f(1000.);\nParam q(1.);\nParam g(0.);\n"
            "History x1(0.); History x2(0.); History y1(0.); History y2(0.);\n"
            + rbj_peaking("f", "q", "g", "b0", "b1", "b2", "a1", "a2") + "\n"
            + biquad_df1("in1", "b0", "b1", "b2", "a1", "a2",
                         "x1", "x2", "y1", "y2", "y") + "\nout1 = y;")
    sig = [0.3, -0.7, 1.0, 0.0, 0.5, -0.2]
    out = _sim(code, {"in1": sig}, params={"f": 1000.0, "q": 1.0, "g": 0.0},
               num_samples=len(sig))["out1"]
    assert all(abs(a - b) < 1e-12 for a, b in zip(out, sig))


def test_rbj_peaking_dc_gain_is_unity():
    # a peaking EQ passes DC at unity regardless of gain: (b0+b1+b2)/(1+a1+a2)==1.
    for gain in (-12.0, -3.0, 3.0, 12.0):
        b0, b1, b2, a1, a2 = _rbj_coeffs(1000.0, 1.0, gain)
        assert abs((b0 + b1 + b2) / (1.0 + a1 + a2) - 1.0) < 1e-9


def test_rbj_peaking_centre_frequency_gain_matches_db():
    # end-to-end: a sine at f0 through [rbj_peaking + biquad_df1] is boosted/cut by
    # exactly gain_db. Measure steady-state output amplitude vs input amplitude.
    from math import pi, sin
    f0, sr, gain = 1000.0, 48000.0, 6.0
    n = 8000
    sine = [sin(2 * pi * f0 * k / sr) for k in range(n)]
    code = ("Param f(1000.);\nParam q(1.);\nParam g(6.);\n"
            "History x1(0.); History x2(0.); History y1(0.); History y2(0.);\n"
            + rbj_peaking("f", "q", "g", "b0", "b1", "b2", "a1", "a2") + "\n"
            + biquad_df1("in1", "b0", "b1", "b2", "a1", "a2",
                         "x1", "x2", "y1", "y2", "y") + "\nout1 = y;")
    out = _sim(code, {"in1": sine}, params={"f": f0, "q": 1.0, "g": gain},
               samplerate=sr, num_samples=n)["out1"]
    amp = max(abs(v) for v in out[-2000:])     # steady-state peak (input amp == 1)
    assert abs(amp - 10 ** (gain / 20.0)) < 0.02   # ~ +6 dB == x1.995


# --- rbj_shelf: runtime low/high-shelf biquad coefficients ---------------------
def _shelf_coeffs(kind, freq, gain_db, sr=48000.0):
    code = ("Param f(1000.);\nParam g(6.);\n"
            + rbj_shelf("f", "g", kind, "b0", "b1", "b2", "a1", "a2")
            + "\nout1 = b0;\nout2 = b1;\nout3 = b2;\nout4 = a1;\nout5 = a2;")
    o = _sim(code, {"in1": [0.0]}, params={"f": freq, "g": gain_db},
             samplerate=sr, num_samples=1)
    return [o[f"out{k}"][0] for k in range(1, 6)]


def test_rbj_shelf_invalid_kind_raises():
    import pytest
    with pytest.raises(ValueError, match="must be 'low' or 'high'"):
        rbj_shelf("f", "g", "band", "b0", "b1", "b2", "a1", "a2")


def test_rbj_low_shelf_matches_reference():
    # RBJ low-shelf, +6 dB, 1k, 48k, normalised for the biquad_df1 convention
    # (regression snapshot; physical correctness is the DC/Nyquist tests below).
    ref = [1.03795790, -1.81274621, 0.79692279, -1.81826669, 0.82936021]
    got = _shelf_coeffs("low", 1000.0, 6.0)
    assert all(abs(a - b) < 1e-7 for a, b in zip(got, ref)), got


def test_rbj_high_shelf_matches_reference():
    ref = [1.92229600, -3.49524679, 1.59427581, -1.74645447, 0.76777949]
    got = _shelf_coeffs("high", 1000.0, 6.0)
    assert all(abs(a - b) < 1e-7 for a, b in zip(got, ref)), got


def test_rbj_shelf_zero_gain_is_unity_through_biquad():
    for kind in ("low", "high"):
        code = ("Param f(1000.);\nParam g(0.);\n"
                "History x1(0.); History x2(0.); History y1(0.); History y2(0.);\n"
                + rbj_shelf("f", "g", kind, "b0", "b1", "b2", "a1", "a2") + "\n"
                + biquad_df1("in1", "b0", "b1", "b2", "a1", "a2",
                             "x1", "x2", "y1", "y2", "y") + "\nout1 = y;")
        sig = [0.3, -0.7, 1.0, 0.0, 0.5, -0.2]
        out = _sim(code, {"in1": sig}, params={"f": 1000.0, "g": 0.0},
                   num_samples=len(sig))["out1"]
        assert all(abs(a - b) < 1e-12 for a, b in zip(out, sig)), kind


def test_rbj_low_shelf_dc_gain_is_full_nyquist_unity():
    # low-shelf boosts DC by gain_db, unity at Nyquist.
    for gain in (-9.0, 6.0):
        b0, b1, b2, a1, a2 = _shelf_coeffs("low", 1000.0, gain)
        dc = (b0 + b1 + b2) / (1.0 + a1 + a2)
        nyq = (b0 - b1 + b2) / (1.0 - a1 + a2)
        assert abs(dc - 10 ** (gain / 20.0)) < 1e-6
        assert abs(nyq - 1.0) < 1e-6


def test_rbj_high_shelf_dc_unity_nyquist_full():
    for gain in (-9.0, 6.0):
        b0, b1, b2, a1, a2 = _shelf_coeffs("high", 1000.0, gain)
        dc = (b0 + b1 + b2) / (1.0 + a1 + a2)
        nyq = (b0 - b1 + b2) / (1.0 - a1 + a2)
        assert abs(dc - 1.0) < 1e-6
        assert abs(nyq - 10 ** (gain / 20.0)) < 1e-6


# --- one_pole_coeff / one_pole_lp / one_pole_hp: the shared 1st-order filter -----
import math  # noqa: E402
from math import exp as _exp_op  # noqa: E402
from math import pi as _pi  # noqa: E402


def test_one_pole_coeff_text():
    assert one_pole_coeff("c", "fc") == \
        "c = 1.0 - exp(-6.28318530717959 * fc / samplerate);"


def test_one_pole_coeff_matches_minus_2pi_fc_over_fs():
    code = one_pole_coeff("c", "fc")
    for fc, sr in [(100.0, 48000.0), (3000.0, 44100.0), (8000.0, 96000.0)]:
        ns = {"exp": _exp_op, "fc": fc, "samplerate": sr}
        exec(code, ns)  # noqa: S102
        assert abs(ns["c"] - (1.0 - _exp_op(-2.0 * _pi * fc / sr))) < 1e-12
        assert 0.0 < ns["c"] < 1.0   # a stable lerp rate


def test_one_pole_lp_and_hp_text():
    assert one_pole_lp("x", "s", "c", "y") == "s = s + c * (x - s);\ny = s;"
    assert one_pole_hp("x", "s", "c", "y") == "s = s + c * (x - s);\ny = x - s;"


def _run_one_pole(kind, x_seq, freq, sr=48000.0, init=0.0):
    snip = one_pole_lp if kind == "lp" else one_pole_hp
    code = (f"History s({init});\n"
            + one_pole_coeff("c", "fc") + "\n"
            + snip("in1", "s", "c", "y") + "\nout1 = y;")
    return _sim(code, {"in1": list(x_seq)}, params={"fc": freq},
                samplerate=sr, num_samples=len(x_seq))["out1"]


def test_one_pole_lp_dc_settles_to_input():
    # a low-pass fed constant DC converges to that DC level (unity DC gain).
    out = _run_one_pole("lp", [1.0] * 4000, 1000.0)
    assert abs(out[-1] - 1.0) < 1e-6


def test_one_pole_hp_removes_dc():
    # the complementary high-pass strips the DC: a constant input decays to ~0.
    out = _run_one_pole("hp", [1.0] * 4000, 1000.0)
    assert abs(out[-1]) < 1e-3


def test_one_pole_lp_hp_reconstruct_the_input():
    # lp(x) + hp(x) == x sample-for-sample (they share one state -> exact split).
    sig = [0.3, -0.7, 1.0, 0.0, 0.5, -0.2, 0.9]
    lp = _run_one_pole("lp", sig, 2000.0)
    hp = _run_one_pole("hp", sig, 2000.0)
    assert all(abs((a + b) - x) < 1e-12 for a, b, x in zip(lp, hp, sig))


def test_one_pole_hp_passes_nyquist_alternation():
    # full-scale +/- alternation (Nyquist, all "highs") passes the high-pass with
    # most of its level intact: |out| stays high (the band an exciter shapes),
    # whereas DC is removed to ~0 (test_one_pole_hp_removes_dc) — that contrast is
    # the frequency selectivity the exciter relies on.
    out = _run_one_pole("hp", [(-1.0) ** n for n in range(2000)], 3000.0)
    assert abs(out[-1]) > 0.75


# --- exciter_harmonics: the harmonic-generation core (added content) ------------
def _exc_harm(band, k, even):
    code = ("Param k(2.);\nParam even(0.);\n"
            + exciter_harmonics("in1", "k", "even", "h") + "\nout1 = h;")
    return _sim(code, {"in1": [band]}, params={"k": k, "even": even},
                num_samples=1)["out1"][0]


def test_exciter_harmonics_text():
    assert exciter_harmonics("b", "k", "e", "h") == (
        "hx_odd = tanh(b * k) / tanh(k);\n"
        "hx_sq = b * b;\n"
        "h = (hx_odd - b) + e * hx_sq;"
    )


def test_exciter_harmonics_silence_adds_nothing():
    # band == 0 -> no harmonics added (silence in, silence added) for any k/even.
    for k in (1.0, 2.0, 8.0):
        for even in (0.0, 0.5, 1.0):
            assert abs(_exc_harm(0.0, k, even)) < 1e-12


def test_exciter_harmonics_odd_only_when_even_is_zero():
    # even == 0 -> out == tanh(band*k)/tanh(k) - band exactly (pure odd generator).
    band, k = 0.5, 3.0
    expect = tanh(band * k) / tanh(k) - band
    assert abs(_exc_harm(band, k, 0.0) - expect) < 1e-12


def test_exciter_harmonics_even_term_is_symmetric_square():
    # the even contribution is band^2*even: equal for +/-band (it is the even,
    # DC-bearing 2nd-harmonic source the caller DC-blocks). Isolate it by
    # subtracting the (odd, antisymmetric) even=0 baseline.
    band, k, even = 0.6, 4.0, 1.0
    base_p = _exc_harm(band, k, 0.0)
    base_n = _exc_harm(-band, k, 0.0)
    even_p = _exc_harm(band, k, even) - base_p
    even_n = _exc_harm(-band, k, even) - base_n
    assert abs(even_p - even_n) < 1e-12           # symmetric -> even harmonics
    assert abs(even_p - band * band) < 1e-12


def test_exciter_harmonics_more_drive_more_odd_energy():
    # at a fixed mid-level band, a higher k generates more odd-harmonic delta.
    band = 0.4
    lo = abs(_exc_harm(band, 1.5, 0.0))
    hi = abs(_exc_harm(band, 6.0, 0.0))
    assert hi > lo > 0.0


def test_exciter_harmonics_stays_finite_under_extremes():
    for band in (-1.0, -0.001, 0.0, 0.001, 1.0):
        for k in (1.0, 12.0, 40.0):
            for even in (0.0, 1.0):
                v = _exc_harm(band, k, even)
                assert math.isfinite(v)


# --- rbj_lowpass / rbj_highpass: runtime 2nd-order LP/HP coefficients ----------
def _lphp_coeffs(fn, freq, q, sr=48000.0):
    code = ("Param f(1000.);\nParam q(0.7071);\n"
            + fn("f", "q", "b0", "b1", "b2", "a1", "a2")
            + "\nout1 = b0;\nout2 = b1;\nout3 = b2;\nout4 = a1;\nout5 = a2;")
    o = _sim(code, {"in1": [0.0]}, params={"f": freq, "q": q},
             samplerate=sr, num_samples=1)
    return [o[f"out{k}"][0] for k in range(1, 6)]


def _lphp_run(fn, x_seq, freq, q, sr=48000.0):
    code = ("Param f(1000.);\nParam q(0.7071);\n"
            "History x1(0.); History x2(0.); History y1(0.); History y2(0.);\n"
            + fn("f", "q", "b0", "b1", "b2", "a1", "a2") + "\n"
            + biquad_df1("in1", "b0", "b1", "b2", "a1", "a2",
                         "x1", "x2", "y1", "y2", "y") + "\nout1 = y;")
    return _sim(code, {"in1": list(x_seq)}, params={"f": freq, "q": q},
                samplerate=sr, num_samples=len(x_seq))["out1"]


def test_rbj_lowpass_matches_reference_coeffs():
    # independently cross-checked (numpy + scipy): RBJ LPF f=1k Q=0.70710678 48k,
    # normalised for the biquad_df1 MINUS convention (a1,a2 are +a1/a0,+a2/a0).
    ref = [0.00391612666, 0.00783225332, 0.00391612666, -1.81534108245, 0.83100558909]
    got = _lphp_coeffs(rbj_lowpass, 1000.0, 0.70710678)
    assert all(abs(a - b) < 1e-9 for a, b in zip(got, ref)), got


def test_rbj_highpass_matches_reference_coeffs():
    ref = [0.91158666788, -1.82317333577, 0.91158666788, -1.81534108245, 0.83100558909]
    got = _lphp_coeffs(rbj_highpass, 1000.0, 0.70710678)
    assert all(abs(a - b) < 1e-9 for a, b in zip(got, ref)), got


def test_rbj_lowpass_passes_dc_blocks_nyquist():
    # LP: unity at DC, zero at Nyquist (alternating +/-1).
    dc = _lphp_run(rbj_lowpass, [1.0] * 400, 1000.0, 0.70710678)
    nyq = _lphp_run(rbj_lowpass, [(-1.0) ** n for n in range(400)], 1000.0, 0.70710678)
    assert abs(dc[-1] - 1.0) < 1e-6
    assert max(abs(v) for v in nyq[300:]) < 1e-3


def test_rbj_highpass_blocks_dc_passes_nyquist():
    # HP: zero at DC, unity at Nyquist (the complement of the low-pass).
    dc = _lphp_run(rbj_highpass, [1.0] * 400, 1000.0, 0.70710678)
    nyq = _lphp_run(rbj_highpass, [(-1.0) ** n for n in range(400)], 1000.0, 0.70710678)
    assert abs(dc[-1]) < 1e-6
    assert abs(max(abs(v) for v in nyq[300:]) - 1.0) < 1e-3


def test_lphp_coeff_dc_nyquist_gains_analytic():
    # closed-form DC/Nyquist gains from the coeffs (no recurrence): LP 1/0, HP 0/1.
    lb0, lb1, lb2, la1, la2 = _lphp_coeffs(rbj_lowpass, 1000.0, 0.70710678)
    hb0, hb1, hb2, ha1, ha2 = _lphp_coeffs(rbj_highpass, 1000.0, 0.70710678)
    assert abs((lb0 + lb1 + lb2) / (1 + la1 + la2) - 1.0) < 1e-9   # LP DC = 1
    assert abs((lb0 - lb1 + lb2) / (1 - la1 + la2)) < 1e-9         # LP Nyquist = 0
    assert abs((hb0 + hb1 + hb2) / (1 + ha1 + ha2)) < 1e-9         # HP DC = 0
    assert abs((hb0 - hb1 + hb2) / (1 - ha1 + ha2) - 1.0) < 1e-9   # HP Nyquist = 1


# --- butterworth_q_table: per-stage Q for an even-order cascade ----------------
def test_butterworth_q_table_known_values():
    import pytest
    # cross-checked closed-form Q_k = 1/(2 cos((2k-1) pi / (2n))).
    assert butterworth_q_table(2) == pytest.approx([0.7071067811865475], abs=1e-9)
    assert butterworth_q_table(4) == pytest.approx([0.5411961001, 1.3065629649], abs=1e-9)
    assert butterworth_q_table(6) == pytest.approx(
        [0.5176380902, 0.7071067812, 1.9318516526], abs=1e-9)
    assert butterworth_q_table(8) == pytest.approx(
        [0.5097955791, 0.6013448869, 0.8999762231, 2.5629154477], abs=1e-9)
    assert len(butterworth_q_table(16)) == 8   # 96 dB/oct


def test_butterworth_q_table_rejects_odd_and_small():
    import pytest
    for bad in (0, 1, 3, 5, 7):
        with pytest.raises(ValueError, match="even and >= 2"):
            butterworth_q_table(bad)


# --- biquad_cascade: variable-slope Butterworth low/high-pass ------------------
def _cascade_mag_db(kind, order, f, fc=1000.0, sr=48000.0, n=8192):
    from math import log10, pi, sin
    code = biquad_cascade("in1", "out1", f"{fc}", kind, order)
    seq = [sin(2 * pi * f * k / sr) for k in range(n)]
    out = _sim(code, {"in1": seq}, samplerate=sr, num_samples=n)["out1"]
    return 20 * log10(max(abs(v) for v in out[n // 2:]))


def test_biquad_cascade_4th_order_lowpass_response():
    # cross-checked composite: -0.017 dB at 0.5fc, -3.01 at fc, -24.25 at 2fc.
    assert abs(_cascade_mag_db("low", 4, 500.0) - (-0.0167)) < 0.05
    assert abs(_cascade_mag_db("low", 4, 1000.0) - (-3.0100)) < 0.05
    assert abs(_cascade_mag_db("low", 4, 2000.0) - (-24.248)) < 0.30


def test_biquad_cascade_is_minus3db_at_cutoff_every_order():
    # the maximally-flat Butterworth invariant: -3.01 dB at fc for ANY even order.
    for order in (2, 4, 6, 8):
        assert abs(_cascade_mag_db("low", order, 1000.0) - (-3.0103)) < 0.06, order


def test_biquad_cascade_highpass_is_complementary():
    # HP cascade: deep cut a half-octave below fc, ~0 dB a half-octave above.
    assert _cascade_mag_db("high", 4, 1000.0) == _cascade_mag_db("high", 4, 1000.0)
    assert abs(_cascade_mag_db("high", 4, 2000.0) - 0.0) < 0.05      # passband above fc
    assert _cascade_mag_db("high", 4, 500.0) < -20.0                 # stopband below fc
    assert abs(_cascade_mag_db("high", 4, 1000.0) - (-3.0103)) < 0.06   # -3 dB at fc


def test_biquad_cascade_slope_steepens_with_order():
    # at 2*fc the attenuation deepens ~6 dB/oct per order (24/oct per +order step).
    a4 = _cascade_mag_db("low", 4, 2000.0)
    a8 = _cascade_mag_db("low", 8, 2000.0)
    assert a8 < a4 - 20.0    # 8th-order is far steeper than 4th at 2fc


def test_biquad_cascade_is_self_contained_and_namespaced():
    code = biquad_cascade("in1", "out1", "1000.", "low", 6)
    assert "History cas0_x1(0.);" in code      # declares its own state
    assert code.count("History ") == 3 * 4     # 3 stages x 4 cells (decl lines)
    # prefix namespaces everything so two cascades coexist in one codebox
    other = biquad_cascade("in1", "out1", "1000.", "low", 6, prefix="lp")
    assert "lp0_x1" in other and "cas" not in other


def test_biquad_cascade_invalid_args_raise():
    import pytest
    with pytest.raises(ValueError, match="must be 'low' or 'high'"):
        biquad_cascade("in1", "out1", "f", "band", 4)
    with pytest.raises(ValueError, match="even and >= 2"):
        biquad_cascade("in1", "out1", "f", "low", 3)


# --- lr_crossover: Linkwitz-Riley complementary crossover split ---------------
def _lr_rms_db(order, which, f, fc=1000.0, sr=48000.0, n=8192):
    # RMS-based amplitude (exact for a steady sine regardless of sample phase,
    # unlike max|sample| which under-reads at few-samples-per-cycle).
    from math import log10, pi, sin, sqrt
    code = lr_crossover("in1", "lo", "hi", f"{fc}", order)
    code += "\nout1 = lo + hi;" if which == "sum" else f"\nout1 = {which};"
    seq = [sin(2 * pi * f * k / sr) for k in range(n)]
    out = _sim(code, {"in1": seq}, samplerate=sr, num_samples=n)["out1"]
    tail = out[n // 2:]
    rms = sqrt(sum(v * v for v in tail) / len(tail))
    amp = rms * sqrt(2.0)
    return 20 * log10(amp) if amp > 1e-12 else -999.0


def test_lr_crossover_flat_sum_reconstruction():
    # THE defining Linkwitz-Riley property: lo + hi sums to a FLAT magnitude
    # (allpass) at every frequency — no peak or notch at the crossover.
    for order in (4, 8):
        for f in (100.0, 300.0, 700.0, 1000.0, 1500.0, 3000.0):
            assert abs(_lr_rms_db(order, "sum", f)) < 0.1, (order, f)


def test_lr_crossover_minus6db_at_crossover():
    # each LR band is exactly -6.02 dB at the crossover (vs -3 dB for Butterworth).
    for order in (4, 8):
        assert abs(_lr_rms_db(order, "lo", 1000.0) - (-6.02)) < 0.1, order
        assert abs(_lr_rms_db(order, "hi", 1000.0) - (-6.02)) < 0.1, order


def test_lr_crossover_dc_nyquist_split():
    # LP band passes DC / blocks Nyquist; HP band is the complement.
    code = lr_crossover("in1", "lo", "hi", "1000.", 4)
    dc = _sim(code + "\nout1 = lo;\nout2 = hi;", {"in1": [1.0] * 600}, num_samples=600)
    assert abs(dc["out1"][-1] - 1.0) < 1e-4        # LP -> DC passes
    assert abs(dc["out2"][-1]) < 1e-4              # HP -> DC blocked
    nyq_seq = [(-1.0) ** k for k in range(600)]
    nyq = _sim(code + "\nout1 = lo;\nout2 = hi;", {"in1": nyq_seq}, num_samples=600)
    assert max(abs(v) for v in nyq["out1"][500:]) < 1e-3   # LP -> Nyquist blocked
    assert max(abs(v) for v in nyq["out2"][500:]) > 0.99   # HP -> Nyquist passes


def test_lr_crossover_slope_steepens_with_order():
    # LR4 = 24 dB/oct, LR8 = 48 dB/oct: the LP at 2*fc drops by ~ order*6 dB/oct.
    lp4 = _lr_rms_db(4, "lo", 2000.0)
    lp8 = _lr_rms_db(8, "lo", 2000.0)
    assert abs(lp4 - (-24.8)) < 1.5
    assert lp8 < lp4 - 20.0          # 48 dB/oct far steeper than 24 at 2fc


def test_lr_crossover_self_contained_and_namespaced():
    code = lr_crossover("in1", "lo", "hi", "1000.", 8)
    assert "History xo_lo0_x1(0.);" in code        # declares its own state
    # LR8: order//2 = 4 -> Butterworth-4 (2 biquads) twice = 4 biquads PER band,
    # x2 bands = 8 biquads total, 4 History cells each = 32 History decls.
    assert code.count("History ") == 8 * 4
    other = lr_crossover("in1", "lo", "hi", "1000.", 4, prefix="bandsplit")
    assert "bandsplit_lo0" in other and "bandsplit_hi0" in other
    assert "xo_" not in other


def test_lr_crossover_rejects_non_multiple_of_4():
    import pytest
    for bad in (0, 2, 3, 6, 7, 10):
        with pytest.raises(ValueError, match="multiple of 4"):
            lr_crossover("in1", "lo", "hi", "f", bad)
