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
    "viz_declares", "viz_poke_block", "poly_lfo_engine", "freeze_capture_block",
    "rampsmooth_fn", "ring_delay", "lowpass_12_fn", "highpass_12_fn",
    "allpass_fn", "diffuse_fn", "granular_voice_fn", "compose_gen_code",
    "variable_sigmoid_fn", "modulated_allpass_reverb",
    "op_fn", "qpow_fn", "fade_env_fn", "ramp_env_fn", "tanh_approx_fn",
    "svf_fn", "lfo_osc_fn",
    "RAMPSMOOTH_FN", "LOWPASS_12_FN", "HIGHPASS_12_FN", "ALLPASS_FN",
    "DIFFUSE_FN", "GRANULAR_VOICE_FN", "VARIABLE_SIGMOID_FN",
    "OP_FN", "QPOW_FN", "FADE_FN", "RAMP_FN", "TANA_FN", "SVF_FN", "LFO_OSC_FN",
    "LFO_VOICE_FN", "lfo_voice_fn",
]


# ── D4 viz bus: gen -> named buffer~ -> jsui (the corpus "keystone for live
# displays"; stranular / lfo-cluster / Particle-Reverb verbatim idiom). The gen
# side declares BARE Buffer names and pokes per-frame screen state on a
# counter-gated GUI tick; the DEVICE binds each Buffer to a ---scoped buffer~
# via a rebind message into gen~ inlet 0 (see Device.add_viz_bus), and a
# buffer_viz_js jsui peeks the same buffers on its own poll Task.

def viz_declares(*buffers: str, counter: str = "his_guiCout") -> str:
    """Declarations for a viz bus: bare ``Buffer`` decls (bound at load by the
    device-side rebind message — the stranular contract) plus the GUI-tick
    counter ``History``. Place with your OTHER declarations, BEFORE any
    executable statement (gen requires all decls first)."""
    lines = [f"Buffer {name};" for name in buffers]
    lines.append(f"History {counter}(0);")
    return "\n".join(lines)


def viz_poke_block(body: str, *, refresh_ms: float = 40.0,
                   counter: str = "his_guiCout") -> str:
    """The counter-gated GUI tick (stranular/lfo-cluster verbatim): every
    ``refresh_ms`` worth of samples, run ``body`` once — the block that pokes
    per-voice/per-frame screen state into the viz Buffers. Declare ``counter``
    via :func:`viz_declares`. Splice the result into the per-sample body."""
    indented = "\n".join("\t" + ln for ln in body.strip().split("\n"))
    return (f"{counter} = wrap({counter} + 1, 0, mstosamps({refresh_ms}));\n"
            f"if ({counter} == 1) {{\n{indented}\n}}")

# One LFO voice of the Orbit cluster: phase advance + 6 analytic shapes
# (sine / tri / saw / square / S&H / drift), all state in caller-owned Data
# rows so ONE function serves N voices (lfo-cluster's polyrhythmic cluster).
LFO_VOICE_FN = """lfo_voice(data_ph, data_sh, data_dr, idx, rt, shp) {
	ph = peek(data_ph, idx, 0);
	ph += rt / samplerate;
	if (ph >= 1) {
		ph -= 1;
		poke(data_sh, noise() * 0.5 + 0.5, idx, 0);
		poke(data_dr, noise() * 0.5 + 0.5, idx, 1);
	}
	poke(data_ph, ph, idx, 0);
	v = 0;
	if (shp < 0.5) {
		v = 0.5 - 0.5 * cos(ph * twopi);
	} else if (shp < 1.5) {
		v = 1 - abs(2 * ph - 1);
	} else if (shp < 2.5) {
		v = ph;
	} else if (shp < 3.5) {
		v = ph < 0.5;
	} else if (shp < 4.5) {
		v = peek(data_sh, idx, 0);
	} else {
		cur = peek(data_dr, idx, 0);
		tgt = peek(data_dr, idx, 1);
		cur += (tgt - cur) * min(1, rt * 8 / samplerate);
		poke(data_dr, cur, idx, 0);
		v = cur;
	}
	return v;
}"""


def lfo_voice_fn() -> str:
    """Return the gen function-definition for one Orbit LFO voice (phase +
    6 analytic shapes; state in caller Data rows). Caller declares
    ``Data data_ph(N); Data data_sh(N); Data data_dr(N, 2);``."""
    return LFO_VOICE_FN


# One chaos voice of the Entropy cluster: six sources on a shared rate clock,
# ENTROPY scaling each source's own wildness axis, and the TAME gesture baked
# in per voice — latch-and-crossfade toward the value where motion was caught,
# calm the math (logistic r / lorenz rho pull back to stability), and a slew
# that grows to a ~45 ms glide at full TAME. All state in caller-owned Data
# rows (data_st: 0=value 1=drift-target 2=logistic-x 3..5=lorenz xyz;
# data_out: 0=slewed-out 1=latched 2=tame-prev).
CHAOS_VOICE_FN = """chaos_voice(data_ph, data_st, data_out, idx, rt, src, ent, tame) {
	rte = rt * (1 - tame) * (1 - tame);
	ph = peek(data_ph, idx, 0);
	ph += rte / samplerate;
	wrapped = 0;
	if (ph >= 1) {
		ph -= 1;
		wrapped = 1;
	}
	poke(data_ph, ph, idx, 0);
	v = peek(data_st, idx, 0);
	if (src < 0.5) {
		tgt = peek(data_st, idx, 1);
		if (wrapped) {
			tgt = noise() * 0.5 + 0.5;
			poke(data_st, tgt, idx, 1);
		}
		v += (tgt - v) * min(1, rte * (2 + 6 * ent) / samplerate);
	} else if (src < 1.5) {
		if (wrapped) {
			n = noise() * 0.5 + 0.5;
			v = 0.5 + (n - 0.5) * (0.2 + 0.8 * ent);
		}
	} else if (src < 2.5) {
		if (wrapped) {
			v += noise() * (0.03 + 0.35 * ent);
			if (v > 1) v = 2 - v;
			if (v < 0) v = 0 - v;
		}
	} else if (src < 3.5) {
		x = peek(data_st, idx, 2);
		if (x <= 0.0001 || x >= 0.9999 || x != x) x = 0.5731 + 0.061 * idx;
		if (wrapped) {
			r = 3.2 + 0.7995 * ent;
			r = r - tame * max(0, r - 3.4);
			x = r * x * (1 - x);
			poke(data_st, x, idx, 2);
		}
		v += (x - v) * min(1, rte * 24 / samplerate);
	} else if (src < 4.5) {
		lx = peek(data_st, idx, 3);
		ly = peek(data_st, idx, 4);
		lz = peek(data_st, idx, 5);
		if ((lx == 0 && ly == 0 && lz == 0) || lx != lx || ly != ly || lz != lz) {
			lx = 0.4 + 0.31 * idx;
			ly = 0.1;
			lz = 18 + 2 * idx;
		}
		dt = min(0.012, rte * 6 / samplerate);
		rho = 14 + 14 * ent;
		rho = rho - tame * max(0, rho - 10);
		dx = 10 * (ly - lx);
		dy = lx * (rho - lz) - ly;
		dz = lx * ly - 2.6667 * lz;
		lx = clamp(lx + dx * dt, -60, 60);
		ly = clamp(ly + dy * dt, -60, 60);
		lz = clamp(lz + dz * dt, 0, 90);
		poke(data_st, lx, idx, 3);
		poke(data_st, ly, idx, 4);
		poke(data_st, lz, idx, 5);
		tap = lx;
		if (idx % 3 == 1) tap = ly;
		if (idx % 3 == 2) tap = lz - 25;
		v = clamp(tap / 45 + 0.5, 0, 1);
	} else {
		if (wrapped) {
			if (noise() * 0.5 + 0.5 < 0.15 + 0.85 * ent) v = 1;
		}
		v = v * (1 - min(0.35, rte * (2 + 5 * (1 - ent)) / samplerate));
	}
	v = clamp(v, 0, 1);
	poke(data_st, v, idx, 0);
	tprev = peek(data_out, idx, 2);
	if (tame > 0.02 && tprev <= 0.02) poke(data_out, v, idx, 1);
	poke(data_out, tame, idx, 2);
	lat = peek(data_out, idx, 1);
	tc = tame * tame * (3 - 2 * tame);
	vm = v + (lat - v) * tc;
	sm = peek(data_out, idx, 0);
	sm += (vm - sm) * (1 - tc * 0.9995);
	poke(data_out, sm, idx, 0);
	return sm;
}"""


def chaos_voice_fn() -> str:
    """Return the gen function-definition for one Entropy chaos voice (six
    sources + per-voice TAME latch/settle; state in caller Data rows). Caller
    declares ``Data data_ph(N); Data data_st(N, 6); Data data_out(N, 3);``."""
    return CHAOS_VOICE_FN


def poly_chaos_engine(*, voices: int = 4, gui_refresh_ms: float = 40.0,
                      viz_buffer: str = "buf_entropy_gui") -> str:
    """The Entropy poly-chaos codebox — Orbit's cluster spine with chaos
    sources. Same outer contract as :func:`poly_lfo_engine` (rates spread from
    ONE Rate by the bias/offset fold; per-slot Depth/Min/Max/Bipolar windows;
    ``build_gendsp(code, 1, 2*voices)`` outs = REMOTE natives then MODULATE
    raws; the GUI tick pokes ``[radius, phase, value, depth]`` per voice for a
    polar_cluster-family hero).

    Global macros on gen inlet 0 (the device identity):
      ``entropy`` 0..100 %% — each source's wildness axis (drift slew, S&H
                  width, drunk step, logistic r 3.2→3.9995, lorenz rho 14→28,
                  burst probability)
      ``tame``    0..100 %% — the bring-it-in gesture: motion freezes at the
                  CAUGHT value (latch-and-crossfade), the math calms
                  (r/rho pulled back to stable ranges), rates scale by
                  (1-T)^2 and a slew grows to a glide. Automatable/mappable.

    PER-LANE ``source_{i}`` (0..5 = Drift / S&H / Drunk / Logistic / Lorenz /
    Burst): each lane picks its OWN chaos source — the whole point of the
    device. ``chaos_voice`` already takes ``src`` per call and ``data_st`` holds
    every source's state per voice, so this is pure param plumbing.

    The GUI tick pokes ``[value, source, depth, windowed]`` per lane (the raw
    0..1 source value for the hero's scrolling trace, plus source for tint and
    depth for brightness) — the chaos_lanes lane-stack hero contract.
    """
    params: list = [("rate", 0.5, 0.02, 16.0), ("bias", 0.13, 0.0, 1.0),
                    ("offset", 0.0, 0.0, 1.0),
                    ("entropy", 50.0, 0.0, 100.0), ("tame", 0.0, 0.0, 100.0),
                    ("lanes", float(voices), 1.0, float(voices))]
    for i in range(1, voices + 1):
        params += [(f"source_{i}", 0.0, 0.0, 5.0),
                   (f"depth_{i}", 100.0, 0.0, 100.0),
                   (f"umin_{i}", 0.0, 0.0, 100.0),
                   (f"umax_{i}", 100.0, 0.0, 100.0),
                   (f"bipolar_{i}", 0.0, 0.0, 1.0),
                   (f"tmin_{i}", 0.0), (f"tmax_{i}", 1.0)]
    decls = [f"Data data_ph({voices});", f"Data data_st({voices}, 6);",
             f"Data data_out({voices}, 3);",
             viz_declares(viz_buffer)]
    setup = ["ent_s = entropy * 0.01;", "tame_s = tame * 0.01;"]
    voice_lines = []
    pokes = []
    for i in range(1, voices + 1):
        k = i - 1
        voice_lines += [
            f"r_{i} = fold(offset + bias * {k}, 0, 1);",
            f"rt_{i} = rate * (1 + 3 * r_{i});",
            f"v_{i} = chaos_voice(data_ph, data_st, data_out, {k}, rt_{i}, "
            f"source_{i}, ent_s, tame_s);",
            f"d_{i} = depth_{i} * 0.01;",
            f"vv_{i} = bipolar_{i} > 0.5 ? 0.5 + d_{i} * (v_{i} - 0.5) : "
            f"v_{i} * d_{i};",
            f"out{i} = tmin_{i} + (tmax_{i} - tmin_{i}) * "
            f"(umin_{i} * 0.01 + (umax_{i} - umin_{i}) * 0.01 * vv_{i});",
            f"out{voices + i} = vv_{i};",
        ]
        pokes += [
            f"poke({viz_buffer}, v_{i}, {4 * k}, 0);",
            f"poke({viz_buffer}, source_{i}, {4 * k + 1}, 0);",
            f"poke({viz_buffer}, d_{i}, {4 * k + 2}, 0);",
            f"poke({viz_buffer}, vv_{i}, {4 * k + 3}, 0);",
        ]
    pokes.append(f"poke({viz_buffer}, lanes, {4 * voices}, 0);")
    body = "\n".join(decls + setup + voice_lines) + "\n" + viz_poke_block(
        "\n".join(pokes), refresh_ms=gui_refresh_ms)
    return compose_gen_code(params=params, functions=[CHAOS_VOICE_FN], body=body)


def poly_lfo_engine(*, voices: int = 4, gui_refresh_ms: float = 40.0,
                    viz_buffer: str = "buf_orbit_gui") -> str:
    """The Orbit poly-LFO codebox (lfo-cluster class): ``voices`` LFOs whose
    rates spread from ONE Rate by the cluster fold ``r = fold(offset +
    bias*i, 0, 1)`` -> ``rate * (1 + 3r)`` (the radius->rate polyrhythm), with
    per-slot Depth/Min/Max/Bipolar windows, PER-LANE ``shape_{i}`` (each lane
    its own waveform — the Entropy v2 pattern) and a ``lanes`` reveal count.
    GUI tick pokes ``[value, shape, depth, windowed]`` per lane + the lanes
    count at ``4*voices`` — the chaos_lanes lane-stack hero contract.

    Signal outs (``build_gendsp(code, 1, 2*voices)``):
      out 1..voices        REMOTE family, native units for a ``normalized=0``
                           live.remote~: ``tmin_i + (tmax_i-tmin_i) *
                           (umin_i + (umax_i-umin_i) * vv_i)`` where ``vv_i``
                           is the depth/bipolar-windowed wave;
      out voices+1..2v     MODULATE family: ``vv_i`` raw (0..1 relative).

    Message params on gen inlet 0: global ``rate/bias/offset/shape`` + per
    slot ``depth_i/umin_i/umax_i/bipolar_i`` (slot dials) and
    ``tmin_i/tmax_i`` (the mapper's target min/max reads). The GUI tick pokes
    ``[radius, phase, value, depth]`` per voice into ``viz_buffer`` (samps =
    ``4*voices``) for the polar_cluster hero.
    """
    params: list = [("rate", 1.0, 0.02, 8.0), ("bias", 0.13, 0.0, 1.0),
                    ("offset", 0.0, 0.0, 1.0),
                    ("lanes", float(voices), 1.0, float(voices))]
    for i in range(1, voices + 1):
        # depth/umin/umax arrive as 0..100 percents (the slot numboxes read
        # "100 %" like the stock modulators); scaled by 0.01 in the body.
        # shape is PER-LANE (Entropy v2 pattern): each lane its own waveform.
        params += [(f"shape_{i}", 0.0, 0.0, 5.0),
                   (f"depth_{i}", 100.0, 0.0, 100.0),
                   (f"umin_{i}", 0.0, 0.0, 100.0),
                   (f"umax_{i}", 100.0, 0.0, 100.0),
                   (f"bipolar_{i}", 0.0, 0.0, 1.0),
                   (f"tmin_{i}", 0.0), (f"tmax_{i}", 1.0)]
    decls = [f"Data data_ph({voices});", f"Data data_sh({voices});",
             f"Data data_dr({voices}, 2);",
             viz_declares(viz_buffer)]
    voice_lines = []
    pokes = []
    for i in range(1, voices + 1):
        k = i - 1
        voice_lines += [
            f"r_{i} = fold(offset + bias * {k}, 0, 1);",
            f"rt_{i} = rate * (1 + 3 * r_{i});",
            f"v_{i} = lfo_voice(data_ph, data_sh, data_dr, {k}, rt_{i}, shape_{i});",
            f"d_{i} = depth_{i} * 0.01;",
            f"vv_{i} = bipolar_{i} > 0.5 ? 0.5 + d_{i} * (v_{i} - 0.5) : "
            f"v_{i} * d_{i};",
            f"out{i} = tmin_{i} + (tmax_{i} - tmin_{i}) * "
            f"(umin_{i} * 0.01 + (umax_{i} - umin_{i}) * 0.01 * vv_{i});",
            f"out{voices + i} = vv_{i};",
        ]
        pokes += [
            f"poke({viz_buffer}, v_{i}, {4 * k}, 0);",
            f"poke({viz_buffer}, shape_{i}, {4 * k + 1}, 0);",
            f"poke({viz_buffer}, d_{i}, {4 * k + 2}, 0);",
            f"poke({viz_buffer}, vv_{i}, {4 * k + 3}, 0);",
        ]
    pokes.append(f"poke({viz_buffer}, lanes, {4 * voices}, 0);")
    body = "\n".join(decls + voice_lines) + "\n" + viz_poke_block(
        "\n".join(pokes), refresh_ms=gui_refresh_ms)
    return compose_gen_code(params=params, functions=[LFO_VOICE_FN], body=body)


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


def freeze_capture_block(*, freeze_param: str = "freezeTgt",
                         data: str = "data_freeze",
                         lines: tuple = ("delaySigR", "delaySigL"),
                         capture_samps: str = "freezeSamps",
                         ramp_ms: float = 400.0,
                         ramp_state: str = "his_freezeRamp") -> str:
    """The Particle-Reverb freeze gesture for a granular caller: on the RISING
    edge of ``freeze_param``, copy the last ``capture_samps`` of both Delay
    ``lines`` TIME-REVERSED into ``data`` (channels 0/1 — verbatim: ``index =
    freezeSamps - i``), then slew a 0..1 ramp over ``ramp_ms`` whose
    equal-power split ``freezeG = sqrt(ramp)`` / ``invFreezeG = sqrt(1-ramp)``
    feeds ``granular_vp``'s freeze/invFreeze gains — the click-free seam.

    Caller declares ``History {ramp_state}(0);``, the ``Data {data}(n, 2)``,
    both ``Delay`` lines, and (if symbolic) ``capture_samps``. Splice the
    result into the per-sample body; it defines ``freezeG``/``invFreezeG``.
    """
    line_r, line_l = lines
    return (
        f"freezeChange = change({freeze_param} > 0.5);\n"
        f"if (freezeChange == 1) {{\n"
        f"\tfor (fz_i = 0; fz_i < {capture_samps}; fz_i += 1) {{\n"
        f"\t\tfz_idx = {capture_samps} - fz_i;\n"
        f"\t\tpoke({data}, {line_r}.read(fz_idx), fz_i, 0);\n"
        f"\t\tpoke({data}, {line_l}.read(fz_idx), fz_i, 1);\n"
        f"\t}}\n"
        f"}}\n"
        f"{ramp_state} = clamp({ramp_state} + "
        f"(({freeze_param} > 0.5) * 2 - 1) / mstosamps({ramp_ms}), 0, 1);\n"
        f"freezeG = sqrt({ramp_state});\n"
        f"invFreezeG = sqrt(1 - {ramp_state});"
    )


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
