"""Stateful gen~ primitives (D1 core)."""

from m4l_builder.gen_patcher import build_gendsp
from m4l_builder.gen_stateful import (
    RAMPSMOOTH_FN,
    allpass_fn,
    compose_gen_code,
    diffuse_fn,
    fade_env_fn,
    granular_voice_fn,
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


def test_lowpass_12_is_verbatim_rbj_biquad():
    code = lowpass_12_fn()
    assert code.startswith("lowpass_12(sig, cf, q)")
    assert code.count("{") == code.count("}")
    # change()-gated coefficient recompute (CPU discipline) + DF1 history taps
    assert "CHANGE = change(his_cf * his_q);" in code
    assert "twopi / samplerate" in code
    # y-feedback write is denormal-flushed (Q44); his_h1 copies the flushed cell
    assert "his_h4 = fixdenorm(output);" in code
    assert "his_h1 = his_h4;" in code


def test_allpass_uses_gen_delay_operators():
    code = allpass_fn()
    assert code.startswith("allpass(x, g, delaySamps, delaySig1, delaySig2)")
    assert "delaySig1.write(x);" in code
    assert "delaySig1.read(delaySamps)" in code
    # the feedback line write is denormal-flushed (Q44 silent-tail guard)
    assert "delaySig2.write(fixdenorm(y));" in code
    assert code.count("{") == code.count("}")


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


def test_granular_voice_fn_balanced_and_stereo():
    code = granular_voice_fn()
    assert code.startswith("granular_vp(")
    assert code.count("{") == code.count("}")
    assert "his_thisIndex" in code and "data_freeze" in code
    assert code.rstrip().endswith("return outR, outL;\n}")


def test_highpass_12_is_verbatim_rbj_biquad():
    code = highpass_12_fn()
    assert code.startswith("highpass_12(sig, cf, q)")
    assert code.count("{") == code.count("}")
    assert "CHANGE = change(his_cf * his_q);" in code
    assert "alpha = sn * 0.5 / his_q;" in code


def test_variable_sigmoid_shape():
    code = variable_sigmoid_fn()
    assert code.startswith("variable_sigmoid(xin, pregain, postgain, sigmoid)")
    assert code.count("{") == code.count("}")
    # the jewel: the logistic curve + the knee clamp + dB-domain gains
    assert "y = (2. / (1. + exp(sigmoid * x))) - 1.;" in code
    assert "sigmoid = minimum(sigmoid, -2.);" in code
    assert "pregain = dbtoa(clip(pregain, -48., 48.));" in code


def test_modulated_allpass_reverb_grounded_topology():
    code = modulated_allpass_reverb()
    assert code.count("{") == code.count("}")
    # Reverb constants, verbatim: pre-diffusion delay seeds, the 1.36255
    # second-tap ratio, the 0.27 apRate, the change()-gated size recompute.
    assert "allpass(preL, 0.75, 44.64," in code
    assert "allpass(preL, 0.625, 61.014," in code
    assert "1.36255" in code and "0.27" in code
    assert "changeDelayTime = change(his_size);" in code
    # lowpass-damped feedback tank, both channels; the tank write (THE feedback
    # loop) is denormal-flushed (Q44)
    assert "fbL = lowpass_12(rvbDecay * tankL.read(his_tank)" in code
    assert "tankL.write(fixdenorm(mainL));" in code
    assert "tankR.write(fixdenorm(mainR));" in code
    # hunt #60 — R-channel decorrelation: identical L/R delays made a mono
    # input produce a bit-identical (dual-mono) tail. R reads its OWN tank +
    # main-allpass taps (~1.9-2.3% long) and its pre-diffusion delays scale
    # by 1.019 (44.64 -> 45.4882); L keeps the verbatim source topology.
    assert "fbR = lowpass_12(rvbDecay * tankR.read(his_tankR)" in code
    assert "his_tankR = scaledSizeSamps * 1.023;" in code
    assert "his_apd1R = his_apd1 * 1.019;" in code
    assert "allpass(mainR, 0.625, his_apd1R," in code
    assert "allpass(preR, 0.75, 45.4882," in code
    # REGRESSION: Live's gen silences a codebox that declares a History AFTER an
    # executable statement — every top-level History must precede the first
    # statement. (A his_apd1-after-his_size= build passed no audio until reordered.)
    assert code.index("History his_tank(0);") < code.index("his_size = (rvbSize")


def test_modulated_allpass_reverb_builds_a_valid_gendsp():
    # the integration proof: lint accepts it as a real stereo effect — out1/out2
    # are driven by the tank, not a silent passthrough (nin=2, nout=2).
    code = modulated_allpass_reverb()
    gendsp = build_gendsp(code, 2, 2)
    assert '"classnamespace"' in gendsp and "dsp.gen" in gendsp


# --- D3: premium synth-voice kit (verbatim) --------------------------------


def test_op_is_fm_operator_with_feedback():
    code = op_fn()
    assert code.startswith("op(freq, mult, ph, pm, fb, trig)")
    assert code.count("{") == code.count("}")
    # phase-mod input + signed self-feedback + the hf feedback taming + note reset
    assert "fb_factor = 13 * pow(0.5 - norm_f, 4);" in code
    assert 'osc = cycle((phase - 0.25 + ph) + fbk + pm, index = "phase");' in code
    assert "phasor(freq * mult, trig)" in code


def test_qpow_iterative_power_curve():
    code = qpow_fn()
    assert code.startswith("qpow(x, p)")
    assert code.count("{") == code.count("}")
    assert "for (i = 0; i < z; i += 1) {" in code
    assert "x = x * ((x * y) + (1 - y));" in code


def test_fade_ad_envelope():
    code = fade_env_fn()
    assert code.startswith("fade(trig, attack, decay)")
    assert code.count("{") == code.count("}")
    assert "env += attack * (1.01 - env) * sr_n;" in code
    assert "env += decay * (0 - env) * sr_n;" in code


def test_ramp_scheduler_clock():
    code = ramp_env_fn()
    assert code.startswith("ramp(trig, time, rnd_t, rand)")
    assert code.count("{") == code.count("}")
    assert "y = 1 / (time + clip((noise() * time) * rand, time * -0.9, time * 10));" in code


def test_tana_pade_tanh():
    code = tanh_approx_fn()
    assert code.startswith("tanA(x)")
    assert code.count("{") == code.count("}")
    assert "0.999999492001" in code and "0.009981877999" in code


def test_svf_is_double_cascaded_tpt():
    code = svf_fn()
    assert code.startswith("svf(x, f, q, type)")
    assert code.count("{") == code.count("}")
    assert "g = tanA(f * pi / samplerate);" in code  # depends on tanA
    # two cascaded TPT cores (y0..y1 then y2..y3) → 24 dB/oct
    assert "return mix(lp0, hp0, type);" in code


def test_lfo_osc_wavetable_with_phase_bend():
    code = lfo_osc_fn()
    assert code.startswith("lfo_osc(buf, phase, uni, wave, bend)")
    assert code.count("{") == code.count("}")
    assert "_phase = qpow(phase, bend);" in code  # depends on qpow
    assert 'peek(buf, _phase + x_scan, uni, interp = "linear")' in code


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
