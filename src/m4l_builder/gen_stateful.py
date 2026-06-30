"""Stateful gen~ DSP primitives (Data / Buffer / wrap) — the cores the framework
could NOT express before (granular, looper, freeze, sampler, reverb tails).

``gen_snippets.py`` holds INLINE expression snippets (``lhs = expr;`` runs); these
are full gen FUNCTION definitions or stateful blocks that own History/Data state,
grounded in the real corpus codeboxes (stranular's 100-voice granular gen~, the
Particle-Reverb gen~). Place a returned function-definition string near the top of
GEN_CODE and call it; the block emitters splice into the per-sample body.

Verified gen signatures (Codebox form): ``poke(data, value, channel, index)``,
``peek(data, index, channel)``, ``wrap(value, min, max)``, ``Data name(size)``,
``History h(init)``.
"""

from __future__ import annotations

__all__ = [
    "rampsmooth_fn", "ring_delay", "lowpass_12_fn", "highpass_12_fn",
    "allpass_fn", "diffuse_fn", "granular_voice_fn", "compose_gen_code",
    "variable_sigmoid_fn", "modulated_allpass_reverb",
    "op_fn", "qpow_fn", "fade_env_fn", "ramp_env_fn", "tanh_approx_fn",
    "svf_fn", "lfo_osc_fn",
    "RAMPSMOOTH_FN", "LOWPASS_12_FN", "HIGHPASS_12_FN", "ALLPASS_FN",
    "DIFFUSE_FN", "GRANULAR_VOICE_FN", "VARIABLE_SIGMOID_FN",
    "OP_FN", "QPOW_FN", "FADE_FN", "RAMP_FN", "TANA_FN", "SVF_FN", "LFO_OSC_FN",
]


# Verbatim from Particle-Reverb_6.0 — the granular voice scatter (scheduler +
# polyphonic playback + freeze mode). The keystone for a granular device.
# CALLER CONTRACT (declare these before calling):
#   Data data_param(maxVoice, 6);  // per-voice state, channels:
#       0=counter(0=free / >0=playhead position), 1=size(samps), 2=read start pos,
#       3=pitch ratio offset, 4=width R gain, 5=width L gain
#   Buffer buf_win("<window>");    // grain window (e.g. Hann) read by phase
#   Delay  delaySigL(maxsize); Delay delaySigR(maxsize);  // the input delay lines
#   Data   data_freeze(...);       // captured buffer for freeze mode
# Returns (outR, outL). `freeze`>0 plays from data_freeze, else from the live delay lines.
GRANULAR_VOICE_FN = """granular_vp(maxVoice, buf_win, data_param, delaySigR, delaySigL, size, position, interval, freeze, invFreeze, data_freeze, wide, pitch, chorus) {
	History his_thisIndex(0);
	History his_cout(0);
	History his_interval(100);
	his_cout = wrap(his_cout + 1, 0, his_interval);
	if (his_cout == 1) {
		if (peek(data_param, his_thisIndex, 0) == 0) {
			poke(data_param, 1, his_thisIndex, 0);
			pitchScaled = pow(2, (pitch + chorus * noise()) * 0.0833) - 1;
			poke(data_param, pitchScaled, his_thisIndex, 3);
			sizeSamps = mstosamps(size * (1 + 0.02 * noise()));
			poke(data_param, sizeSamps, his_thisIndex, 1);
			poke(data_param, sizeSamps * pitchScaled + position * abs(noise()), his_thisIndex, 2);
			spreadRand = wide * noise();
			poke(data_param, 1 + spreadRand, his_thisIndex, 4);
			poke(data_param, 1 - spreadRand, his_thisIndex, 5);
			his_thisIndex = wrap(his_thisIndex + 1, 0, maxVoice);
		}
		his_interval = floor(mstosamps(interval * (1 + 0.05 * noise())));
	}
	outR = 0;
	outL = 0;
	output = 0;
	if (freeze > 0.0001) {
		for (i = 0; i < maxVoice; i += 1) {
			pCout = peek(data_param, i, 0);
			if (pCout != 0) {
				s = peek(data_param, i, 1);
				if (pCout < s) {
					pCoutScaled = pCout / s;
					winVal = peek(buf_win, pCoutScaled, 0, index="phase");
					p = peek(data_param, i, 2) * 0.1;
					if (i % 2 == 1) {
						output = peek(data_freeze, p + (pCout * (1 + peek(data_param, i, 3))), 0) * winVal;
					} else {
						output = -peek(data_freeze, p + (pCout * (1 + peek(data_param, i, 3))), 1) * winVal;
					}
					outR += output * peek(data_param, i, 4);
					outL += output * peek(data_param, i, 5);
					poke(data_param, pCout + 1, i, 0);
				} else {
					poke(data_param, 0, i, 0);
					continue;
				}
			}
		}
		outR *= freeze;
		outL *= freeze;
	} else {
		for (i = 0; i < maxVoice; i += 1) {
			pCout = peek(data_param, i, 0);
			if (pCout != 0) {
				s = peek(data_param, i, 1);
				if (pCout < s) {
					pCoutScaled = pCout / s;
					winVal = peek(buf_win, pCoutScaled, 0, index="phase");
					p = peek(data_param, i, 2);
					if (i % 2 == 1) {
						output = delaySigR.read(p - pCout * peek(data_param, i, 3)) * winVal;
					} else {
						output = -delaySigL.read(p - pCout * peek(data_param, i, 3)) * winVal;
					}
					outR += output * peek(data_param, i, 4);
					outL += output * peek(data_param, i, 5);
					poke(data_param, pCout + 1, i, 0);
				} else {
					poke(data_param, 0, i, 0);
					continue;
				}
			}
		}
		outR *= invFreeze;
		outL *= invFreeze;
	}
	return outR, outL;
}"""


def granular_voice_fn() -> str:
    """Return the gen function-definition for the granular voice scatter (verbatim
    from Particle-Reverb): an interval-gated round-robin grain scheduler + a
    polyphonic playback loop with a freeze mode, returning ``(outR, outL)``. See
    ``GRANULAR_VOICE_FN`` for the required Data/Buffer/Delay caller contract."""
    return GRANULAR_VOICE_FN


def _param_decl(p) -> str:
    """Render one gen `Param` declaration from a string or tuple.

    A string is passed through (a trailing `;` is ensured). A tuple is
    ``(name, default)`` or ``(name, default, min, max)`` →
    ``Param name(default[, min=.., max=..]);`` (the real corpus syntax).
    """
    if isinstance(p, str):
        return p if p.rstrip().endswith(";") else p + ";"
    name, default = p[0], p[1]
    if len(p) >= 4:
        return f"Param {name}({default}, min={p[2]}, max={p[3]});"
    return f"Param {name}({default});"


def compose_gen_code(*, params=(), functions=(), body: str = "") -> str:
    """Assemble a gen~ codebox string for :func:`gen_patcher.build_gendsp`.

    The integration harness that wires the orphaned ``gen_stateful`` /
    ``gen_snippets`` libraries into a build: emits the function definitions FIRST
    (e.g. ``lowpass_12_fn()``, ``allpass_fn()``), then the ``Param`` declarations,
    then the per-sample ``body`` (which must drive ``out1 = ...``). Pass the result
    to ``build_gendsp(code, nin, nout)``.

        code = compose_gen_code(
            params=[("cutoff", 1000, 20, 20000), ("q", 0.7)],
            functions=[lowpass_12_fn()],
            body="out1 = lowpass_12(in1, cutoff, q);",
        )

    ORDER MATTERS: Live's gen compiler wants every user-function definition at the
    TOP of the codebox (Particle-Reverb / Superberry both open with their function
    defs); a ``Param``/declaration BEFORE a function def silences the whole codebox
    (verified: a Param-first channel strip passed no audio until reordered).
    """
    parts = [f for f in functions if f]            # function DEFS first (gen requires it)
    parts += [_param_decl(p) for p in params]       # then Param declarations
    if body:
        parts.append(body)                          # then the per-sample statements
    return "\n\n".join(parts)


# Verbatim from stranular_2.0's gen~ codebox — an asymmetric History smoother:
# slews `input` UP over upSamps samples and DOWN over dwSamps (the slide~ in gen).
RAMPSMOOTH_FN = """rampsmooth(input, upSamps, dwSamps) {
	History his_input(0);
	History his_diff(0);
	History his_output(0);
	dlt = input - his_input;
	if (dlt != 0) {
		his_diff = input - his_output;
		his_input = input;
	}
	if (his_diff > 0) {
		his_output = minimum(his_output + his_diff / upSamps, input);
	} else {
		his_output = maximum(his_output + his_diff / dwSamps, input);
	}
	return his_output;
}"""


def rampsmooth_fn() -> str:
    """Return the gen function-definition string for ``rampsmooth(in, up, dw)``.

    Verbatim-verified from stranular_2.0. Place at the top of GEN_CODE, then call
    e.g. ``smoothed = rampsmooth(target, 480, 480);``.
    """
    return RAMPSMOOTH_FN


# Verbatim from Particle-Reverb_6.0's gen~ codebox — a 2-pole RBJ lowpass biquad
# with History-smoothed cf/q and a change()-gated coefficient recompute (only
# recomputes the expensive sin/cos when the smoothed cutoff*q actually moves — the
# built-in CPU-discipline pattern). DF1 with 4 history taps.
LOWPASS_12_FN = """lowpass_12(sig, cf, q) {
	History his_cf(0);
	History his_q(0);
	History his_h1(0);
	History his_h2(0);
	History his_h3(0);
	History his_h4(0);
	History his_b1(0);
	History his_b2(0);
	History his_a0(0);
	History his_a1(0);
	History his_a2(0);
	his_cf = (cf - his_cf) * 0.001 + his_cf;
	his_q = (q - his_q) * 0.001 + his_q;
	CHANGE = change(his_cf * his_q);
	if (CHANGE != 0) {
		omega = his_cf * twopi / samplerate;
		sn = sin(omega);
		cs = cos(omega);
		one_over_q = 1. / his_q;
		alpha = sn * 0.5 * one_over_q;
		b0 = 1. / (1. + alpha);
		a2 = ((1 - cs) * 0.5) * b0;
		his_a0 = a2;
		his_a1 = (1. - cs) * b0;
		his_a2 = a2;
		his_b1 = (-2. * cs) * b0;
		his_b2 = (1. - alpha) * b0;
	}
	output = (((sig * his_a0 + his_h3 * his_a1)) + his_h2 * his_a2) - ((his_h4 * his_b1 + his_h1 * his_b2));
	his_h1 = his_h4;
	his_h2 = his_h3;
	his_h3 = sig;
	his_h4 = output;
	return output;
}"""


# Verbatim from Particle-Reverb_6.0 — a Schroeder/Dattorro allpass diffuser. The
# two delay lines are gen `Delay` operators passed in (declare e.g.
# `Delay ap1d1(48000); Delay ap1d2(48000);` then `allpass(x, 0.5, 1234, ap1d1, ap1d2)`).
ALLPASS_FN = """allpass(x, g, delaySamps, delaySig1, delaySig2) {
	delaySig1.write(x);
	y = g * x + delaySig1.read(delaySamps) - g * delaySig2.read(delaySamps);
	delaySig2.write(y);
	return y;
}"""


# Verbatim from Particle-Reverb_6.0 — the compact one-multiply Schroeder allpass
# (a SINGLE gen Delay). Chain N of these (with mutually-prime delay lengths) for a
# diffusion stage. Declare `Delay d1(maxsize)` and call `diffuse(sig, 142, d1, 0.6)`.
DIFFUSE_FN = """diffuse(sig, delaySamps, delaySig, coef) {
	stage1 = sig - delaySig.read(delaySamps) * coef;
	delaySig.write(stage1);
	stage2 = stage1 * coef + delaySig.read(delaySamps);
	return stage2;
}"""


def diffuse_fn() -> str:
    """Return the gen function-definition for ``diffuse(sig, delaySamps, d, coef)``
    where ``d`` is a gen ``Delay`` — the compact one-multiply Schroeder allpass.
    Chain several (mutually-prime delays) for reverb diffusion (verbatim from
    Particle-Reverb)."""
    return DIFFUSE_FN


# Verbatim from Particle-Reverb_6.0 — the RBJ 2-pole HIGHPASS twin of lowpass_12
# (same DF1 + smoothed coeffs + change()-gated recompute). Use for the channel
# strip HP and any EQ low-cut.
HIGHPASS_12_FN = """highpass_12(sig, cf, q) {
	History his_cf(0);
	History his_q(0);
	History his_h1(0);
	History his_h2(0);
	History his_h3(0);
	History his_h4(0);
	History his_b1(0);
	History his_b2(0);
	History his_a0(0);
	History his_a1(0);
	History his_a2(0);
	his_cf = (cf - his_cf) * 0.001 + his_cf;
	his_q = (q - his_q) * 0.001 + his_q;
	CHANGE = change(his_cf * his_q);
	if (CHANGE != 0) {
		omega = his_cf * twopi / samplerate;
		sn = sin(omega);
		cs = cos(omega);
		alpha = sn * 0.5 / his_q;
		b0 = 1. / (1. + alpha);
		a2 = ((1. + cs) * 0.5) * b0;
		his_a0 = a2;
		his_a1 = -(1. + cs) * b0;
		his_a2 = a2;
		his_b1 = (-2. * cs) * b0;
		his_b2 = (1. - alpha) * b0;
	}
	output = (((sig * his_a0 + his_h3 * his_a1)) + his_h2 * his_a2) - ((his_h4 * his_b1 + his_h1 * his_b2));
	his_h1 = his_h4;
	his_h2 = his_h3;
	his_h3 = sig;
	his_h4 = output;
	return output;
}"""


def lowpass_12_fn() -> str:
    """Return the gen function-definition for ``lowpass_12(sig, cf, q)`` — a 2-pole
    RBJ lowpass with smoothed coeffs + change()-gated recompute (verbatim from
    Particle-Reverb)."""
    return LOWPASS_12_FN


def highpass_12_fn() -> str:
    """Return the gen function-definition for ``highpass_12(sig, cf, q)`` — the
    2-pole RBJ highpass twin of ``lowpass_12`` (verbatim from Particle-Reverb)."""
    return HIGHPASS_12_FN


def allpass_fn() -> str:
    """Return the gen function-definition for ``allpass(x, g, delaySamps, d1, d2)``
    where d1/d2 are gen ``Delay`` operators — a Schroeder/Dattorro diffuser stage
    (verbatim from Particle-Reverb). Chain N of these for a reverb tail."""
    return ALLPASS_FN


def ring_delay(name: str, size_samps, *, input: str = "x", delay: str = "dsamps",
               out: str = "y", index: str = "his_widx") -> str:
    """Data-backed ring buffer: write ``input`` at the head, read a ``delay``-sample-
    old value (wrapped), advance the head. The granular/looper/delay keystone.

    Returns a run of statements (declarations + per-sample body) grounded in the
    real stranular poke/peek/wrap idiom. ``size_samps`` is the buffer length.
    """
    return (
        f"Data {name}({size_samps});\n"
        f"History {index}(0);\n"
        f"poke({name}, {input}, 0, {index});\n"
        f"{out} = peek({name}, wrap({index} - ({delay}), 0, {size_samps}), 0);\n"
        f"{index} = wrap({index} + 1, 0, {size_samps});"
    )


# Verbatim saturation curve from Chiral's `tapeH` — a logistic sigmoid whose knee
# is set by `sigmoid` (clamped <= -2): -2 ~= a tanh approximation, -5 ~= 'tape',
# and you can drive it to -100 for a hard squash. `pregain`/`postgain` are in dB.
# The single line `y = (2/(1+exp(sigmoid*x))) - 1` is the jewel.
VARIABLE_SIGMOID_FN = """variable_sigmoid(xin, pregain, postgain, sigmoid) {
	pregain = dbtoa(clip(pregain, -48., 48.));
	postgain = dbtoa(clip(postgain, -96., 12.));
	sigmoid = minimum(sigmoid, -2.);
	x = xin * pregain;
	y = (2. / (1. + exp(sigmoid * x))) - 1.;
	return y * postgain;
}"""


def variable_sigmoid_fn() -> str:
    """Return the gen function-definition for
    ``variable_sigmoid(xin, pregain, postgain, sigmoid)`` — a drive-able logistic
    saturator (pre/post gain in dB, knee set by ``sigmoid``). The curve is verbatim
    from Chiral's ``tapeH``: ``sigmoid``=-2 approximates tanh, -5 is tape-like."""
    return VARIABLE_SIGMOID_FN


# Grounded constants for the modulated allpass reverb — VERBATIM from
# Particle-Reverb_6.0. The pre-diffusion bank is 4 series Schroeder allpasses with
# fixed short delays (in SAMPLES) and these gains; the main bank is 2 size-modulated
# allpasses sharing a 0.625 gain whose delays recompute (change()-gated) from a
# room-size param scaled 180..3500 ms, with the second tap at the 1.36255 ratio.
_PRE_ALLPASS = ((0.75, 44.64), (0.75, 17.184), (0.625, 61.014), (0.625, 44.64))
_MAIN_ALLPASS_GAIN = 0.625
_MAIN_RATIOS = (1.0, 1.36255)
_AP_RATE = 0.27
_MIN_AP_MS = 150.0
_SIZE_LO_MS = 180.0
_SIZE_HI_MS = 3500.0


def modulated_allpass_reverb(
    *,
    in_left: str = "in1",
    in_right: str = "in2",
    out_left: str = "out1",
    out_right: str = "out2",
    size: str = "rvbSize",
    damp_hz: str = "rvbDamp",
    decay: str = "rvbDecay",
    dry_wet: str = "rvbMix",
) -> str:
    """Emit a complete stereo allpass-reverb gen~ program (ready for
    ``build_gendsp(code, nin=2, nout=2)``).

    The topology is grounded VERBATIM in Particle-Reverb_6.0: a 4-stage series
    Schroeder pre-diffusion bank (gains/delays in ``_PRE_ALLPASS``) feeding a
    2-stage *size-modulated* allpass bank (delays recomputed only on a ``change()``
    of the smoothed size, second tap at the 1.36255 ratio), with a lowpass-damped
    feedback tank for the tail. ``size`` is 0..1 (room size), ``damp_hz`` the
    feedback lowpass cutoff, ``decay`` the tank feedback (0..<1), ``dry_wet`` 0..1.

    Built on the shipped ``allpass_fn`` / ``lowpass_12_fn`` primitives — this is the
    D5 reverb composite the granular freeze-reverb device is authored on.
    """
    params = "\n".join((
        f"Param {size}(0.5, min=0, max=1);",
        f"Param {damp_hz}(12000, min=200, max=20000);",
        f"Param {decay}(0.7, min=0, max=0.98);",
        f"Param {dry_wet}(0.3, min=0, max=1);",
    ))

    # Per-channel Delay state (allpass needs two delays per stage). Pre-diffusion
    # delays are short (declare at 1 s); the size-modulated main + tank can reach
    # ~3.5 s of room, so declare at 5 s like the source.
    decls = []
    for ch in ("L", "R"):
        for i in range(len(_PRE_ALLPASS)):
            decls.append(f"Delay pre{ch}{i}a(samplerate); Delay pre{ch}{i}b(samplerate);")
        for i in range(len(_MAIN_RATIOS)):
            decls.append(f"Delay main{ch}{i}a(samplerate*5); Delay main{ch}{i}b(samplerate*5);")
        decls.append(f"Delay tank{ch}(samplerate*5);")
    delays = "\n".join(decls)

    # gen requires ALL top-level History/Delay/Data declarations BEFORE any
    # executable statement (Particle-Reverb declares every operator up front); a
    # History declared after a statement makes Live's gen compiler silence the whole
    # codebox. So declare every History first, THEN smooth + the change()-gate.
    smooth = "\n".join((
        "History his_size(0);",
        *(f"History his_apd{i + 1}(0);" for i in range(len(_MAIN_RATIOS))),
        "History his_tank(0);",
        f"his_size = ({size} - his_size) * 0.001 + his_size;",
        "changeDelayTime = change(his_size);",
        "if (changeDelayTime != 0) {",
        f"\tscaledSizeSamps = mstosamps(scale(his_size, 0, 1, {_SIZE_LO_MS}, {_SIZE_HI_MS}));",
        f"\tminSamps = mstosamps({_MIN_AP_MS});",
        *(f"\this_apd{i + 1} = minSamps + {_AP_RATE} * scaledSizeSamps * {r};"
          for i, r in enumerate(_MAIN_RATIOS)),
        "\this_tank = scaledSizeSamps;",
        "}",
    ))

    def channel(ch: str, in_sig: str, out_sig: str) -> str:
        lines = [
            f"fb{ch} = lowpass_12({decay} * tank{ch}.read(his_tank), {damp_hz}, 0.707);",
            f"pre{ch} = {in_sig} + fb{ch};",
        ]
        for i, (g, d) in enumerate(_PRE_ALLPASS):
            lines.append(f"pre{ch} = allpass(pre{ch}, {g}, {d}, pre{ch}{i}a, pre{ch}{i}b);")
        lines.append(f"main{ch} = pre{ch};")
        for i in range(len(_MAIN_RATIOS)):
            lines.append(
                f"main{ch} = allpass(main{ch}, {_MAIN_ALLPASS_GAIN}, his_apd{i + 1}, "
                f"main{ch}{i}a, main{ch}{i}b);"
            )
        lines.append(f"tank{ch}.write(main{ch});")
        lines.append(f"{out_sig} = mix({in_sig}, main{ch}, {dry_wet});")
        return "\n".join(lines)

    body = "\n\n".join((
        channel("L", in_left, out_left),
        channel("R", in_right, out_right),
    ))

    return "\n\n".join((
        ALLPASS_FN,
        LOWPASS_12_FN,
        params,
        delays,
        smooth,
        body,
    ))


# ===========================================================================
# D3 — Superberry synth-voice kit (all VERBATIM from Superberry's gen~ codebox)
# ===========================================================================

# The FM operator with phase-modulation input + self-feedback — Superberry's
# whole engine in one function. `pm` is the phase-mod input (chain operators by
# feeding one's output into the next's `pm`); `fb` is signed self-feedback (fb>0
# = sine fold, fb<0 = squared/asymmetric); `trig` resets phase+feedback at a new
# note. `fb_factor = 13*pow(0.5 - norm_f, 4)` tames feedback at high frequencies.
OP_FN = """op(freq, mult, ph, pm, fb, trig) {
	History fbk(0), osc(0);
	if (trig) {
		fbk = 0;
		osc = 0;
	}
	norm_f = (freq * mult) / samplerate;
	fb_factor = 13 * pow(0.5 - norm_f, 4);
	phase = phasor(freq * mult, trig);
	osc = cycle((phase - 0.25 + ph) + fbk + pm, index = "phase");
	if (fb > 0) {
		fbk = mix(osc * (fb * fb_factor), fbk, 0.5);
	}
	if (fb < 0) {
		fbk = mix((osc * osc) * (fb * fb_factor), fbk, 0.5);
	}
	return osc;
}"""


# Iterative power-curve waveshaper — `p` (can be negative) bends `x` in [0,1]
# toward 0 or 1 across `floor(|p|)` exponentiation passes. Used both as a
# parameter-response curve and (in `lfo_osc`) as a CZ-style phase distortion.
QPOW_FN = """qpow(x, p) {
	z = 0;
	if (p < 0) {
		z = p * -1;
	} else {
		z = p;
	}
	y = z;
	for (i = 0; i < z; i += 1) {
		y = (clip(z, i, i + 1) - i);
		if (p < 0) {
			y = y * -1;
		}
		x = x * ((x * y) + (1 - y));
	}
	return x;
}"""


# AD envelope (the adsr_codebox core) — `trig` starts it; rises at `attack`,
# falls at `decay` (both as rate-per-second slews of a one-pole toward 1.01 / 0).
# Zero attack-or-decay holds at 1 (a gate). Verbatim from Superberry.
FADE_FN = """fade(trig, attack, decay) {
	History env(0), dec(0), atk(0), trg(0);
	sr_n = 1 / samplerate;
	if (trig) {
		if (attack > 0) {
			env = 0;
			dec = 0;
			atk = 1;
		} else if (decay > 0) {
			env = 1;
			atk = 0;
			dec = 1;
		} else {
			env = 1;
			atk = 0;
			dec = 0;
		}
	}
	if (atk) {
		trg = 0;
		env += attack * (1.01 - env) * sr_n;
		if (env >= 1) {
			atk = 0;
			env = 1;
		}
	} else if (dec) {
		env += decay * (0 - env) * sr_n;
	} else if (attack <= 0 || decay <= 0) {
		env = 1;
	}
	return clip(env, 0, 1);
}"""


# A 1→0 ramp over `time` samples, optionally jittered per-note (`rnd_t` on, `rand`
# depth) by a noise() perturbation of the slope — the grain/voice scheduler clock.
RAMP_FN = """ramp(trig, time, rnd_t, rand) {
	History x(0), y(0), y0(0);
	if (trig) {
		x = 1;
		y0 = time;
		y = 1 / time;
	}
	if (x > 0) {
		if (rnd_t) {
			y = 1 / (time + clip((noise() * time) * rand, time * -0.9, time * 10));
		}
		x -= y;
	}
	return clip(x, 0, 1);
}"""


# Fast tanh approximation (Padé form) — the saturator `svf` and the operators
# lean on. Verbatim from Superberry.
TANA_FN = """tanA(x) {
	x2 = x * x;
	return x * (0.999999492001 + x2 * -0.096524608111) /
	(1 + x2 * (-0.429867256894 + x2 * 0.009981877999));
}"""


# Émilie Gillet's TPT state-variable filter, cascaded twice (12 dB → 24 dB/oct).
# `type` morphs lowpass↔highpass (0=LP, 1=HP). Requires `tanA` (the `g` prewarp).
# Verbatim from Superberry (credited in-source to émilie gillet).
SVF_FN = """svf(x, f, q, type) {
	History y0(0), y1(0), lp(0), hp(0), bp(0);
	History y2(0), y3(0), lp0(0), hp0(0), bp0(0);
	f = clip(f, 1, 19000);
	g = tanA(f * pi / samplerate);
	r = 1 / q;
	h = 1 / (1 + r * g + g * g);
	rpg = r + g;
	hp = (x - rpg * y0 - y1) * h;
	bp = g * hp + y0;
	y0 = g * hp + bp;
	lp = g * bp + y1;
	y1 = g * bp + lp;
	x2 = mix(lp, hp, type);
	hp0 = (x2 - rpg * y2 - y3) * h;
	bp0 = g * hp0 + y2;
	y2 = g * hp0 + bp0;
	lp0 = g * bp0 + y3;
	y3 = g * bp0 + lp0;
	return mix(lp0, hp0, type);
}"""


# Wavetable LFO/oscillator — reads two adjacent 256-sample tables from `buf`
# (channel `uni`) and crossfades by the fractional part of `wave`, after passing
# `phase` through `qpow(phase, bend)` for a CZ-style phase-distortion morph.
# Requires `qpow`. Verbatim from Superberry.
LFO_OSC_FN = """lfo_osc(buf, phase, uni, wave, bend) {
	_phase = qpow(phase, bend);
	_phase = _phase * 255;
	x_scan = int(wave);
	y_scan = x_scan + 1;
	x_scan += x_scan % 2;
	y_scan += y_scan % 2;
	y_scan -= 1;
	x_scan *= 256;
	y_scan *= 256;
	x = peek(buf, _phase + x_scan, uni, interp = "linear");
	y = peek(buf, _phase + y_scan, uni, interp = "linear");
	return mix(x, y, fold(wave, 0, 1));
}"""


def op_fn() -> str:
    """Return the gen function-definition for ``op(freq, mult, ph, pm, fb, trig)``
    — Superberry's FM operator with a phase-modulation input and signed
    self-feedback (verbatim). Chain operators by feeding output into the next
    ``pm``; ``trig`` resets phase at a new note."""
    return OP_FN


def qpow_fn() -> str:
    """Return the gen function-definition for ``qpow(x, p)`` — Superberry's
    iterative power-curve waveshaper (signed ``p``), used for parameter curves and
    CZ-style phase distortion (verbatim)."""
    return QPOW_FN


def fade_env_fn() -> str:
    """Return the gen function-definition for ``fade(trig, attack, decay)`` — the
    Superberry AD gate envelope (rate-per-second one-pole slews; verbatim). This is
    the adsr_codebox core."""
    return FADE_FN


def ramp_env_fn() -> str:
    """Return the gen function-definition for ``ramp(trig, time, rnd_t, rand)`` —
    Superberry's per-note-jitterable 1→0 ramp/scheduler clock (verbatim)."""
    return RAMP_FN


def tanh_approx_fn() -> str:
    """Return the gen function-definition for ``tanA(x)`` — Superberry's fast Padé
    tanh approximation (verbatim). Required by ``svf_fn``."""
    return TANA_FN


def svf_fn() -> str:
    """Return the gen function-definition for ``svf(x, f, q, type)`` — Émilie
    Gillet's TPT state-variable filter cascaded to 24 dB/oct, ``type`` morphing
    LP↔HP (verbatim from Superberry). MUST be emitted together with ``tanh_approx_fn``
    (it calls ``tanA``)."""
    return SVF_FN


def lfo_osc_fn() -> str:
    """Return the gen function-definition for ``lfo_osc(buf, phase, uni, wave, bend)``
    — Superberry's wavetable LFO with ``qpow`` phase-distortion morph (verbatim).
    MUST be emitted together with ``qpow_fn`` (it calls ``qpow``)."""
    return LFO_OSC_FN
