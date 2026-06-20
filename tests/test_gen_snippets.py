"""Tests for the composable GenExpr snippet registry (m4l_builder.gen_snippets).

The M/S primitives are pure arithmetic, so the emitted GenExpr is also valid
Python — we can exec it to behaviourally verify the math (round-trip identity,
mono/wide), not just snapshot the text.
"""
import re
from math import pow, tan, tanh

from m4l_builder.gen_snippets import (
    drive_blend,
    exp_pole,
    isp_catmull_4x,
    kweight_coeffs_bs1770,
    ms_decode,
    ms_encode,
    ms_width,
    peak_follower,
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
