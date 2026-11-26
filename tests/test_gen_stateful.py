"""Stateful gen~ primitives (D1 core).

The DSP primitives are checked by behaviour, simulated with gen_sim: frequency
response against closed-form references, energy, decay and timing. Primitives
that need Data/Buffer access (granular, lfo_osc) are beyond the simulator and are
covered by the gen lint build tests here and in test_motes_kit.py.
"""

import cmath
import math
import random

import pytest

from m4l_builder.gen_patcher import build_gendsp
from m4l_builder.gen_sim import simulate
from m4l_builder.gen_stateful import (
    RAMPSMOOTH_FN,
    allpass_fn,
    compose_gen_code,
    diffuse_fn,
    fade_env_fn,
    highpass_12_fn,
    lfo_osc_fn,
    lowpass_12_fn,
    modulated_allpass_reverb,
    op_fn,
    qpow_fn,
    ramp_env_fn,
    rampsmooth_fn,
    ring_delay,
    svf_fn,
    tanh_approx_fn,
    variable_sigmoid_fn,
)


def test_rampsmooth_is_a_valid_gen_function():
    code = rampsmooth_fn()
    assert code == RAMPSMOOTH_FN
    assert code.startswith("rampsmooth(input, upSamps, dwSamps)")
    # balanced braces + the History-smoother shape
    assert code.count("{") == code.count("}")
    assert "History his_output(0);" in code
    assert "return his_output;" in code


def test_ring_delay_emits_data_poke_peek_wrap():
    code = ring_delay("buf_grain", 44100, input="sig", delay="dly", out="wet")
    assert "Data buf_grain(44100);" in code
    # the line write is denormal-flushed (Q44: caller-closed feedback loops)
    assert "poke(buf_grain, fixdenorm(sig), 0, his_widx);" in code
    assert "wet = peek(buf_grain, wrap(his_widx - (dly), 0, 44100), 0);" in code
    # head advances with wrap
    assert "his_widx = wrap(his_widx + 1, 0, 44100);" in code


def test_ring_delay_custom_index_name():
    code = ring_delay("rb", 1024, index="wp")
    assert "History wp(0);" in code
    assert "poke(rb, fixdenorm(x), 0, wp);" in code


def test_diffuse_is_one_multiply_schroeder_allpass():
    code = diffuse_fn()
    assert code.startswith("diffuse(sig, delaySamps, delaySig, coef)")
    assert "delaySig.read(delaySamps)" in code
    # feedback state write is denormal-flushed (Q44)
    assert "delaySig.write(fixdenorm(stage1));" in code
    assert code.count("{") == code.count("}")


def test_compose_gen_code_assembles_param_fn_body():
    code = compose_gen_code(
        params=[("cutoff", 1000, 20, 20000), ("q", 0.7)],
        functions=[lowpass_12_fn()],
        body="out1 = lowpass_12(in1, cutoff, q);",
    )
    assert "Param cutoff(1000, min=20, max=20000);" in code
    assert "Param q(0.7);" in code
    assert "lowpass_12(sig, cf, q)" in code            # the function def
    assert "out1 = lowpass_12(in1, cutoff, q);" in code
    # REGRESSION: Live's gen silences a codebox whose function def follows a Param
    # declaration — function defs MUST come first. (A Param-first build passed no
    # audio until this ordering was fixed.)
    assert code.index("lowpass_12(sig, cf, q)") < code.index("Param cutoff")


def test_composed_code_builds_a_valid_gendsp():
    # the integration proof: the harness output is accepted by build_gendsp (lint passes)
    code = compose_gen_code(
        params=[("cutoff", 1000, 20, 20000), ("q", 0.7)],
        functions=[lowpass_12_fn()],
        body="out1 = lowpass_12(in1, cutoff, q);",
    )
    gendsp = build_gendsp(code, 1, 1)
    assert '"classnamespace"' in gendsp and "dsp.gen" in gendsp


def test_variable_sigmoid_shape():
    code = variable_sigmoid_fn()
    assert code.startswith("variable_sigmoid(xin, pregain, postgain, sigmoid)")
    assert code.count("{") == code.count("}")
    # the jewel: the logistic curve + the knee clamp + dB-domain gains
    assert "y = (2. / (1. + exp(sigmoid * x))) - 1.;" in code
    assert "sigmoid = minimum(sigmoid, -2.);" in code
    assert "pregain = dbtoa(clip(pregain, -48., 48.));" in code


def test_modulated_allpass_reverb_builds_a_valid_gendsp():
    # the integration proof: lint accepts it as a real stereo effect — out1/out2
    # are driven by the tank, not a silent passthrough (nin=2, nout=2).
    code = modulated_allpass_reverb()
    gendsp = build_gendsp(code, 2, 2)
    assert '"classnamespace"' in gendsp and "dsp.gen" in gendsp


def test_filter_shaper_chain_builds_a_valid_gendsp():
    # integration proof: tanA + svf + qpow wire into a real effect (out1 from in1).
    code = compose_gen_code(
        functions=[tanh_approx_fn(), svf_fn(), qpow_fn()],
        body="out1 = svf(qpow(in1, 2), 2000, 1, 0);",
    )
    gendsp = build_gendsp(code, 1, 1)
    assert '"classnamespace"' in gendsp and "dsp.gen" in gendsp


def test_fm_voice_builds_a_valid_gendsp():
    # integration proof: op + fade compose into a gated FM voice (in1 = gate/trig).
    code = compose_gen_code(
        functions=[op_fn(), fade_env_fn()],
        body="out1 = op(220, 1, 0, 0, 0.4, in1) * fade(in1, 20, 3);",
    )
    gendsp = build_gendsp(code, 1, 1)
    assert '"classnamespace"' in gendsp and "dsp.gen" in gendsp


def test_wavetable_lfo_builds_a_valid_gendsp():
    # integration proof: lfo_osc needs qpow and reads a Buffer by phase.
    code = compose_gen_code(
        functions=[qpow_fn(), lfo_osc_fn()],
        body="Buffer shapes;\nout1 = lfo_osc(shapes, in1, 0, 0.5, 0.3);",
    )
    gendsp = build_gendsp(code, 1, 1)
    assert '"classnamespace"' in gendsp and "dsp.gen" in gendsp


# ── behaviour (gen_sim) ───────────────────────────────────────────────────────
FS = 48000.0


def _tone(freq, n, fs=FS, amp=0.5):
    return [amp * math.sin(2.0 * math.pi * freq * i / fs) for i in range(n)]


def _rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values))


def _gain_db(kernel, freq, *, fs=FS, params=None):
    """Steady-state sine gain of a 1-in/1-out kernel: settle 20 ms, then measure
    over 50 ms (a whole number of periods at the test frequencies)."""
    settle, measure = int(0.02 * fs), int(0.05 * fs)
    x = _tone(freq, settle + measure, fs)
    y = simulate(kernel, x, params=params, samplerate=fs)["out1"]
    return 20.0 * math.log10(_rms(y[settle:]) / _rms(x[settle:]))


def _rbj_db(kind, freq, f0, q, fs=FS):
    """|H| in dB of the RBJ Audio EQ Cookbook 2-pole LPF/HPF (independent reference)."""
    w0 = 2.0 * math.pi * f0 / fs
    alpha, c = math.sin(w0) / (2.0 * q), math.cos(w0)
    b = ((1 - c) / 2, 1 - c, (1 - c) / 2) if kind == "lp" else ((1 + c) / 2, -(1 + c), (1 + c) / 2)
    a = (1 + alpha, -2 * c, 1 - alpha)
    z = cmath.exp(-2j * math.pi * freq / fs)
    h = (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    return 20.0 * math.log10(abs(h))


@pytest.mark.parametrize("fn,call,kind", [
    (lowpass_12_fn, "lowpass_12", "lp"),
    (highpass_12_fn, "highpass_12", "hp"),
])
def test_12db_filters_match_the_rbj_cookbook_response(fn, call, kind):
    kernel = fn() + f"\nout1 = {call}(in1, 1000, 2);"
    for freq in (100, 1000, 4000, 12000):
        assert abs(_gain_db(kernel, freq) - _rbj_db(kind, freq, 1000, 2)) < 0.1, freq


def test_lowpass_12_stays_bounded_while_its_cutoff_jumps_at_audio_rate():
    rng = random.Random(7)
    n = 9600
    noise = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    cutoff = [40.0 if (i // 37) % 2 else 18000.0 for i in range(n)]
    out = simulate(lowpass_12_fn() + "\nout1 = lowpass_12(in1, in2, 10);",
                   {"in1": noise, "in2": cutoff})["out1"]
    assert all(math.isfinite(v) for v in out)
    assert max(abs(v) for v in out) < 20.0


def test_allpass_is_a_lossless_schroeder_allpass():
    g, m = 0.6, 7
    kernel = allpass_fn() + f"\nDelay a(64);\nDelay b(64);\nout1 = allpass(in1, {g}, {m}, a, b);"
    h = simulate(kernel, [1.0], num_samples=3000)["out1"]
    # H(z) = (-g + z^-M) / (1 - g z^-M): h[0] = -g, h[M] = 1 - g^2, unit energy
    assert math.isclose(h[0], -g) and math.isclose(h[m], 1 - g * g)
    assert math.isclose(sum(v * v for v in h), 1.0, rel_tol=1e-9)
    for freq in (500, 3000, 9600):
        assert abs(_gain_db(kernel, freq)) < 0.01


def test_reverb_dry_setting_is_an_exact_passthrough():
    left, right = _tone(440, 300, 16000.0), _tone(660, 300, 16000.0)
    out = simulate(modulated_allpass_reverb(), {"in1": left, "in2": right},
                   params={"rvbMix": 0.0}, samplerate=16000.0)
    assert out["out1"] == left and out["out2"] == right


def test_reverb_tail_decays_and_decorrelates_a_mono_input():
    n = 8000
    impulse = [1.0] + [0.0] * (n - 1)
    out = simulate(modulated_allpass_reverb(), {"in1": impulse, "in2": impulse},
                   params={"rvbMix": 1.0, "rvbDecay": 0.7, "rvbSize": 0.3,
                           "rvbDamp": 5000.0}, samplerate=16000.0)
    left, right = out["out1"], out["out2"]
    early = sum(v * v for v in left[:1600])
    late = sum(v * v for v in left[6400:])
    assert 0.0 < late < 0.5 * early          # a real tail that decays
    cross = sum(a * b for a, b in zip(left[400:], right[400:], strict=True))
    norm = math.sqrt(sum(a * a for a in left[400:]) * sum(b * b for b in right[400:]))
    assert abs(cross / norm) < 0.5           # mono in, decorrelated stereo out


def test_op_is_a_pure_sine_without_modulation_and_resets_on_trig():
    n = 600
    trig = [0.0] * n
    trig[300] = 1.0
    kernel = op_fn() + "\nout1 = op(440, 1.5, 0.25, 0, 0, in1);"
    y = simulate(kernel, trig)["out1"]
    f = 660.0 / FS
    for i in range(300):
        assert math.isclose(y[i], math.sin(2 * math.pi * (i * f + 0.25)), abs_tol=1e-9)
    for i in range(300, n):  # the rising edge restarts the phase
        assert math.isclose(y[i], math.sin(2 * math.pi * ((i - 300) * f + 0.25)), abs_tol=1e-9)


def test_op_feedback_adds_harmonics_without_leaving_unit_range():
    def harmonic(y, k, f0):
        w = 2 * math.pi * k * f0 / FS
        return abs(sum(v * cmath.exp(-1j * w * i) for i, v in enumerate(y))) / len(y)

    kernel = op_fn() + "\nout1 = op(480, 1, 0, 0, in1, 0);"
    clean = simulate(kernel, [0.0] * 4800)["out1"]
    fed = simulate(kernel, [1.0] * 4800)["out1"]
    assert harmonic(clean, 2, 480) < 1e-6
    assert harmonic(fed, 2, 480) > 0.05 * harmonic(fed, 1, 480)
    assert max(abs(v) for v in fed) <= 1.0


def test_qpow_is_an_odd_monotonic_curve_bent_by_the_sign_of_p():
    xs = [i / 50.0 for i in range(-60, 61)]          # symmetric, past |x| = 1
    kernel = qpow_fn() + "\nParam p(0);\nout1 = qpow(in1, p);"
    for p in (-3.0, -0.5, 0.0, 0.5, 3.0):
        ys = simulate(kernel, xs, params={"p": p})["out1"]
        assert all(math.isclose(y, -m, abs_tol=1e-12) for y, m in zip(ys, ys[::-1], strict=True))
        assert all(b >= a for a, b in zip(ys, ys[1:], strict=False))
        assert ys[xs.index(1.0)] == 1.0 and ys[-1] == 1.0    # clamped past |x| = 1
        inner = [(x, y) for x, y in zip(xs, ys, strict=True) if 0.0 < x < 1.0]
        if p > 0:
            assert all(y < x for x, y in inner)
        elif p < 0:
            assert all(y > x for x, y in inner)
        else:
            assert all(math.isclose(y, x) for x, y in inner)


def test_fade_rises_and_falls_with_one_pole_time_constants():
    attack, decay = 20.0, 4.0           # rates per second -> 50 ms and 250 ms
    up, down = int(FS / attack), int(FS / decay)
    gate = [1.0] * up + [0.0] * down
    env = simulate(fade_env_fn() + f"\nout1 = fade(in1, {attack}, {decay});", gate)["out1"]
    assert math.isclose(env[up - 1], 1 - math.exp(-1), abs_tol=1e-3)
    assert math.isclose(env[-1], env[up - 1] * math.exp(-1), abs_tol=1e-3)
    assert all(b >= a for a, b in zip(env[:up], env[1:up], strict=False))
    assert all(b <= a for a, b in zip(env[up:], env[up + 1:], strict=False))


def _wrap_points(level):
    return [i for i in range(1, len(level)) if level[i] > level[i - 1]]


def test_ramp_clock_period_jitter_and_retrigger():
    kernel = ramp_env_fn() + "\nParam draw(0);\nParam depth(0);\nout1 = ramp(in1, 10, draw, depth);"
    level = simulate(kernel, [0.0] * 4800)["out1"]
    wraps = _wrap_points(level)
    assert level[0] == 1.0 and all(0.0 < v <= 1.0 for v in level)
    assert len(wraps) == 9 and {b - a for a, b in zip(wraps, wraps[1:], strict=False)} <= {480, 481}
    slow = simulate(kernel, [0.0] * 4800, params={"draw": 1.0, "depth": 1.0})["out1"]
    assert _wrap_points(slow)[0] in (911, 912)          # 10 ms * 1.9
    trig = [0.0] * 4800
    trig[100] = 1.0
    restarted = simulate(kernel, trig)["out1"]
    assert restarted[100] == 1.0 and restarted[99] < 1.0


def test_tana_tracks_tanh_and_saturates_smoothly():
    xs = [i / 20.0 for i in range(-120, 121)]
    ys = simulate(tanh_approx_fn() + "\nout1 = tanA(in1);", xs)["out1"]
    assert max(abs(y - math.tanh(x)) for x, y in zip(xs, ys, strict=True)) < 0.025
    assert all(b >= a for a, b in zip(ys, ys[1:], strict=False))
    assert ys[0] == -1.0 and ys[-1] == 1.0


def test_svf_is_a_24db_lowpass_morphing_to_highpass():
    lp = svf_fn() + "\nout1 = svf(in1, 1000, 0.7071, 0);"
    hp = svf_fn() + "\nout1 = svf(in1, 1000, 0.7071, 1);"
    assert abs(_gain_db(lp, 100)) < 0.05
    assert abs(_gain_db(lp, 1000) + 6.02) < 0.1        # two -3 dB Butterworth stages
    assert -27.0 < _gain_db(lp, 8000) - _gain_db(lp, 4000) < -21.0   # 24 dB/oct
    assert abs(_gain_db(hp, 12000)) < 0.1
    assert abs(_gain_db(hp, 1000) + 6.02) < 0.1
    assert _gain_db(hp, 100) < -75.0
