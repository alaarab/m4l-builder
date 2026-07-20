"""Stateful gen~ DSP primitives (Data / Buffer / wrap) — the cores the framework
could NOT express before (granular, looper, freeze, sampler, reverb tails).

``gen_snippets.py`` holds INLINE expression snippets (``lhs = expr;`` runs); these
are full gen FUNCTION definitions or stateful blocks that own History/Data state,
grounded in standard granular + reverb DSP idioms. Place a returned function-definition string near the top of
GEN_CODE and call it; the block emitters splice into the per-sample body.

Verified gen signatures (Codebox form): ``poke(data, value, channel, index)``,
``peek(data, index, channel)``, ``wrap(value, min, max)``, ``Data name(size)``,
``History h(init)``.
"""

from __future__ import annotations

import re

__all__ = [
    "viz_declares", "viz_poke_block", "poly_mod_engine",
    "freeze_capture_block",
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


# ── D4 viz bus: gen -> named buffer~ -> jsui (a standard idiom for live
# displays). The gen
# side declares BARE Buffer names and pokes per-frame screen state on a
# counter-gated GUI tick; the DEVICE binds each Buffer to a ---scoped buffer~
# via a rebind message into gen~ inlet 0 (see Device.add_viz_bus), and a
# buffer_viz_js jsui peeks the same buffers on its own poll Task.

def viz_declares(*buffers: str, counter: str = "his_guiCout") -> str:
    """Declarations for a viz bus: bare ``Buffer`` decls (bound at load by the
    device-side rebind message) plus the GUI-tick
    counter ``History``. Place with your OTHER declarations, BEFORE any
    executable statement (gen requires all decls first)."""
    lines = [f"Buffer {name};" for name in buffers]
    lines.append(f"History {counter}(0);")
    return "\n".join(lines)


def viz_poke_block(body: str, *, refresh_ms: float = 40.0,
                   counter: str = "his_guiCout") -> str:
    """Run ``body`` once per ``refresh_ms`` of samples — the GUI tick that pokes
    per-voice/per-frame screen state into the viz Buffers.

    ``counter`` is a sample counter (declare it with :func:`viz_declares`); it
    counts up every sample and, on reaching ``refresh_ms`` worth of samples,
    resets and runs ``body``. Splice the result into the per-sample body."""
    inner = "\n".join("\t" + line for line in body.splitlines())
    return (
        f"{counter} = {counter} + 1;\n"
        f"if ({counter} >= mstosamps({refresh_ms})) {{\n"
        f"\t{counter} = 0;\n"
        f"{inner}\n"
        "}"
    )

# One LFO voice of the Orbit cluster: phase advance + 6 analytic shapes
# (sine / tri / saw / square / S&H / drift), all state in caller-owned Data
# rows so ONE function serves N voices (a polyrhythmic modulation cluster).
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
		rho = 22 + 7 * ent;
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


def poly_mod_engine(*, voices: int = 8, gui_refresh_ms: float = 40.0,
                    viz_buffer: str = "buf_orbit_gui",
                    draw_buffer: str | None = None) -> str:
    """The MERGED Orbit modulator codebox (#76: Orbit + Entropy in one).

    Per-lane ``source_{i}`` 0..9 unifies both families on the shared cluster
    spine (rates spread from ONE Rate by the bias/offset fold; per-slot
    Depth/Min/Max/Bipolar windows; per-lane ``on_i`` gates; outs = REMOTE
    natives then MODULATE raws; GUI pokes ``[value, source, depth, on]``):

      0..3  LFO family    — Sine / Tri / Saw / Square (``lfo_voice``)
      4..9  chaos family  — Drift / S&H / Drunk / Logistic / Lorenz / Burst
                            (``chaos_voice``; ENTROPY = wildness, TAME =
                            freeze-and-calm). LFO lanes ignore both globals —
                            they are deterministic by design.

    ``draw_buffer`` (a named 128-frame, ``voices``-channel ``buffer~``)
    adds source 10 = DRAW: the lane samples its own hand-drawn wavetable
    channel at the lane clock (the function-editor feeds it
    from the message domain via ``peek~``).

    ONLY the selected family computes per lane (codebox ``if/else`` — gen
    ternaries evaluate eagerly, so gating needs real branches): 8 lanes of
    one voice fn each instead of three. An unselected family's state holds
    and resumes on switch. (A flat default-entropy Lorenz once framed this
    gating — that was sub-critical rho physics, since rescaled.) Each family
    keeps its own Data blocks, so there is no state clash.
    """
    params: list = [("rate", 1.0, 0.02, 16.0), ("bias", 0.13, 0.0, 1.0),
                    ("offset", 0.0, 0.0, 1.0),
                    ("entropy", 50.0, 0.0, 100.0), ("tame", 0.0, 0.0, 100.0)]
    for i in range(1, voices + 1):
        src_max = 10.0 if draw_buffer else 9.0
        params += [(f"source_{i}", 0.0, 0.0, src_max),
                   (f"on_{i}", 1.0, 0.0, 1.0),
                   (f"depth_{i}", 100.0, 0.0, 100.0),
                   (f"umin_{i}", 0.0, 0.0, 100.0),
                   (f"umax_{i}", 100.0, 0.0, 100.0),
                   (f"bipolar_{i}", 0.0, 0.0, 1.0),
                   (f"tmin_{i}", 0.0), (f"tmax_{i}", 1.0)]
    decls = [f"Data data_ph({voices});", f"Data data_sh({voices});",
             f"Data data_dr({voices}, 2);",
             f"Data data_phc({voices});", f"Data data_st({voices}, 6);",
             f"Data data_out({voices}, 3);",
             viz_declares(viz_buffer)]
    if draw_buffer:
        decls += [f'Buffer buf_odraw("{draw_buffer}");',
                  f"Data data_phd({voices});"]
    setup = ["ent_s = entropy * 0.01;", "tame_s = tame * 0.01;"]
    voice_lines = []
    pokes = []
    for i in range(1, voices + 1):
        k = i - 1
        voice_lines += [
            f"r_{i} = fold(offset + bias * {k}, 0, 1);",
            f"rt_{i} = rate * (1 + 3 * r_{i});",
        ]
        if draw_buffer:
            voice_lines += [
                f"v_{i} = 0.;",
                f"if (source_{i} < 3.5) {{",
                f"v_{i} = lfo_voice(data_ph, data_sh, data_dr, {k}, rt_{i}, "
                f"clamp(source_{i}, 0., 3.));",
                f"}} else if (source_{i} < 9.5) {{",
                f"v_{i} = chaos_voice(data_phc, data_st, data_out, {k}, "
                f"rt_{i}, clamp(source_{i} - 4., 0., 5.), ent_s, tame_s);",
                "} else {",
                f"phd_{i} = wrap(peek(data_phd, {k}, 0) + rt_{i}"
                f" / samplerate, 0., 1.);",
                f"poke(data_phd, phd_{i}, {k}, 0);",
                f"v_{i} = sample(buf_odraw, phd_{i} * (dim(buf_odraw) - 1), {k});",
                "}",
            ]
        else:
            voice_lines += [
                f"v_{i} = 0.;",
                f"if (source_{i} < 3.5) {{",
                f"v_{i} = lfo_voice(data_ph, data_sh, data_dr, {k}, rt_{i}, "
                f"clamp(source_{i}, 0., 3.));",
                "} else {",
                f"v_{i} = chaos_voice(data_phc, data_st, data_out, {k}, "
                f"rt_{i}, clamp(source_{i} - 4., 0., 5.), ent_s, tame_s);",
                "}",
            ]
        voice_lines += [
            f"d_{i} = depth_{i} * 0.01 * on_{i};",
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
            f"poke({viz_buffer}, on_{i}, {4 * k + 3}, 0);",
        ]
    body = "\n".join(decls + setup + voice_lines) + "\n" + viz_poke_block(
        "\n".join(pokes), refresh_ms=gui_refresh_ms)
    return compose_gen_code(params=params,
                            functions=[LFO_VOICE_FN, CHAOS_VOICE_FN],
                            body=body)


# ── Granular voice scatter + freeze capture ─────────────────────────────────
# Standard granular synthesis (C. Roads, "Microsound", MIT Press 2001): a hop
# clock spawns windowed grains onto free voices round-robin. A grain transposes
# by `ratio` by reading a delay tap that moves (1 - ratio) samples per sample,
# so its start tap sits far enough back that an upward grain never reaches the
# write head. Grains sum with a power normalisation for their expected overlap
# (a Hann window's mean square is 3/8).
#
# CALLER CONTRACT (declare these before calling):
#   Data data_param(maxVoice, 6);  // per-voice state, channels:
#       0 = counter (0 = free, n > 0 = playing its n-th sample), 1 = length (samps),
#       2 = start tap (samples behind the write head), 3 = playback ratio,
#       4 = right gain, 5 = left gain (equal-power pan, 1 and 1 at centre)
#   Buffer buf_win;                // one-channel grain window, read by 0..1 phase
#   Delay delaySigL(n); Delay delaySigR(n);  // live input lines, written by the caller
#   Data data_freeze(n, 2);        // filled by freeze_capture_block: ch0 = R, ch1 = L;
#                                  // its last frame (ch0) holds the captured length
# Arguments: size and interval in ms, position in samples behind the write head,
# freeze / invFreeze the crossfade gains from freeze_capture_block, wide 0..1 the
# random pan spread, pitch and chorus in semitones (chorus = the per-grain random
# detune range). Returns (outR, outL).
GRANULAR_VOICE_FN = """granular_vp(maxVoice, buf_win, data_param, delaySigR, delaySigL, size, position, interval, freeze, invFreeze, data_freeze, wide, pitch, chorus) {
	History gr_clock(0);
	History gr_cursor(0);
	voices = clip(floor(maxVoice), 1, dim(data_param));
	grainLen = max(floor(mstosamps(size)), 16);
	hop = max(mstosamps(interval), 1);
	gr_clock = gr_clock + 1;
	if (gr_clock >= hop) {
		gr_clock = gr_clock - hop;
		placed = 0;
		for (k = 0; k < voices; k += 1) {
			slot = wrap(gr_cursor + k, 0, voices);
			if (placed == 0 && peek(data_param, slot, 0) <= 0) {
				ratio = pow(2, (pitch + chorus * noise()) / 12);
				panPos = clip(wide, 0, 1) * noise();
				poke(data_param, 1, slot, 0);
				poke(data_param, grainLen, slot, 1);
				poke(data_param, max(position, 0) + max(ratio - 1, 0) * grainLen + 2, slot, 2);
				poke(data_param, ratio, slot, 3);
				poke(data_param, sqrt(1 + panPos), slot, 4);
				poke(data_param, sqrt(1 - panPos), slot, 5);
				gr_cursor = wrap(slot + 1, 0, voices);
				placed = 1;
			}
		}
	}
	frozenLen = max(peek(data_freeze, dim(data_freeze) - 1, 0), 2);
	sumR = 0;
	sumL = 0;
	for (v = 0; v < voices; v += 1) {
		cnt = peek(data_param, v, 0);
		if (cnt > 0) {
			glen = peek(data_param, v, 1);
			age = cnt - 1;
			win = sample(buf_win, age / glen, 0);
			tap = peek(data_param, v, 2) + (1 - peek(data_param, v, 3)) * age;
			srcR = 0;
			srcL = 0;
			if (invFreeze > 0) {
				srcR = invFreeze * delaySigR.read(tap, interp="linear");
				srcL = invFreeze * delaySigL.read(tap, interp="linear");
			}
			if (freeze > 0) {
				fpos = wrap(tap - 1, 0, frozenLen - 1);
				f0 = floor(fpos);
				ffrac = fpos - f0;
				srcR = srcR + freeze * mix(peek(data_freeze, f0, 0), peek(data_freeze, f0 + 1, 0), ffrac);
				srcL = srcL + freeze * mix(peek(data_freeze, f0, 1), peek(data_freeze, f0 + 1, 1), ffrac);
			}
			sumR = sumR + win * peek(data_param, v, 4) * srcR;
			sumL = sumL + win * peek(data_param, v, 5) * srcL;
			nxt = cnt + 1;
			if (nxt > glen) {
				nxt = 0;
			}
			poke(data_param, nxt, v, 0);
		}
	}
	norm = 1 / sqrt(max(1, 0.375 * min(voices, grainLen / hop)));
	return sumR * norm, sumL * norm;
}"""


def granular_voice_fn() -> str:
    """Return the gen function-definition for the granular voice scatter: a
    hop-clocked round-robin grain scheduler plus a polyphonic playback loop that
    reads the live delay lines, the frozen capture, or a crossfade of both,
    returning ``(outR, outL)``. See ``GRANULAR_VOICE_FN`` for the
    Data/Buffer/Delay caller contract."""
    return GRANULAR_VOICE_FN


def freeze_capture_block(*, freeze_param: str = "freezeTgt",
                         data: str = "data_freeze",
                         lines: tuple = ("delaySigR", "delaySigL"),
                         capture_samps: str = "freezeSamps",
                         ramp_ms: float = 400.0,
                         ramp_state: str = "his_freezeRamp") -> str:
    """The freeze gesture for a ``granular_voice_fn`` caller: capture the newest
    audio when ``freeze_param`` rises and crossfade live to frozen.

    When ``freeze_param`` crosses 0.5 upward, copy the newest ``capture_samps``
    samples of each Delay in ``lines`` into ``data`` (channel ``i`` from
    ``lines[i]``; frame ``j`` holds the sample ``j + 1`` behind the write head,
    the same addressing as a live tap) and store the captured length in the
    last frame of channel 0, which ``granular_vp`` uses to wrap frozen reads.
    ``ramp_state`` then moves linearly toward 1 (frozen) or 0 (live) over
    ``ramp_ms`` and feeds an equal-power crossfade, ``freezeG = sin(ramp*pi/2)``
    and ``invFreezeG = cos(ramp*pi/2)``, for ``granular_vp``'s
    ``freeze``/``invFreeze`` arguments.

    Caller declares ``History {ramp_state}(0);``, the ``Data {data}(n, 2)``,
    both ``Delay`` lines, and (if symbolic) ``capture_samps``. Splice the
    result into the per-sample body after the Delay writes; it defines
    ``freezeG``/``invFreezeG``.
    """
    first, second = lines
    return "\n".join([
        f"fz_on = {freeze_param} > 0.5;",
        "fz_rise = change(fz_on) > 0;",
        "if (fz_rise) {",
        f"\tfz_len = clip(floor({capture_samps}), 2, dim({data}) - 1);",
        "\tfor (fz_k = 0; fz_k < fz_len; fz_k += 1) {",
        f"\t\tpoke({data}, {first}.read(fz_k + 1, interp=\"none\"), fz_k, 0);",
        f"\t\tpoke({data}, {second}.read(fz_k + 1, interp=\"none\"), fz_k, 1);",
        "\t}",
        f"\tpoke({data}, fz_len, dim({data}) - 1, 0);",
        "}",
        f"{ramp_state} = clip({ramp_state} + (2 * fz_on - 1) / "
        f"max(mstosamps({ramp_ms}), 1), 0, 1);",
        f"freezeG = sin({ramp_state} * halfpi);",
        f"invFreezeG = cos({ramp_state} * halfpi);",
    ])


def _param_decl(p) -> str:
    """Render one gen `Param` declaration from a string or tuple.

    A string is passed through (a trailing `;` is ensured). A tuple is
    ``(name, default)`` or ``(name, default, min, max)`` →
    ``Param name(default[, min=.., max=..]);`` (the real library syntax).
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
    TOP of the codebox; a ``Param``/declaration BEFORE a function def silences the whole codebox
    (verified: a Param-first channel strip passed no audio until reordered).
    """
    parts = [f for f in functions if f]            # function DEFS first (gen requires it)
    parts += [_param_decl(p) for p in params]       # then Param declarations
    if body:
        parts.append(body)                          # then the per-sample statements
    return "\n\n".join(parts)


# An asymmetric History smoother:
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

    Place at the top of GEN_CODE, then call
    e.g. ``smoothed = rampsmooth(target, 480, 480);``.
    """
    return RAMPSMOOTH_FN


# ── 12 dB/oct filters and the Schroeder allpass ─────────────────────────────
# lowpass_12 / highpass_12 are the trapezoidal-integrator (TPT) state-variable
# filter from V. Zavalishin, "The Art of VA Filter Design" (rev. 2.1, ch. 4):
#   g = tan(pi*fc/fs), k = 1/Q,
#   hp = (x - (k + g)*s1 - s2) / (1 + g*(k + g)),  bp = g*hp + s1,  lp = g*bp + s2,
#   s1 <- g*hp + bp,  s2 <- g*bp + lp.
# It is the bilinear transform of the analog 2-pole, so its magnitude response
# equals the RBJ Audio EQ Cookbook LPF/HPF at the same f0 and Q, and the
# zero-delay-feedback structure stays stable under fast cutoff modulation. cf and
# q pass through a 5 ms one-pole smoother (seeded with the first value) that
# removes zipper noise from stepped controls; the integrator states are
# denormal-flushed.
def _tpt_svf_12(name: str, output: str, prefix: str) -> str:
    return f"""{name}(sig, cf, q) {{
	History {prefix}_f(-1);
	History {prefix}_q(-1);
	History {prefix}_s1(0);
	History {prefix}_s2(0);
	fTarget = clip(cf, 5, samplerate * 0.49);
	qTarget = clip(q, 0.05, 100);
	if ({prefix}_f < 0) {{
		{prefix}_f = fTarget;
		{prefix}_q = qTarget;
	}}
	smooth = 1 - exp(-200 / samplerate);
	{prefix}_f = {prefix}_f + (fTarget - {prefix}_f) * smooth;
	{prefix}_q = {prefix}_q + (qTarget - {prefix}_q) * smooth;
	g = tan(pi * {prefix}_f / samplerate);
	k = 1 / {prefix}_q;
	hp = (sig - (k + g) * {prefix}_s1 - {prefix}_s2) / (1 + g * (k + g));
	bp = g * hp + {prefix}_s1;
	lp = g * bp + {prefix}_s2;
	{prefix}_s1 = fixdenorm(g * hp + bp);
	{prefix}_s2 = fixdenorm(g * bp + lp);
	return {output};
}}"""


LOWPASS_12_FN = _tpt_svf_12("lowpass_12", "lp", "lp12")


# Schroeder's allpass (M. R. Schroeder, "Natural Sounding Artificial
# Reverberation", JAES 1962) in direct form I, one delay line per side:
#   y[n] = -g*x[n] + x[n-M] + g*y[n-M]
# delaySig1 carries the input, delaySig2 the output. Unity gain at every
# frequency for |g| < 1 and integer M; taps read with linear interpolation so M
# can be modulated. The output line is the feedback path, so its write is
# denormal-flushed.
ALLPASS_FN = """allpass(x, g, delaySamps, delaySig1, delaySig2) {
	m = max(delaySamps, 1);
	xm = delaySig1.read(m, interp="linear");
	ym = delaySig2.read(m, interp="linear");
	y = xm + g * (ym - x);
	delaySig1.write(x);
	delaySig2.write(fixdenorm(y));
	return y;
}"""


# The compact one-multiply Schroeder allpass
# (a SINGLE gen Delay). Chain N of these (with mutually-prime delay lengths) for a
# diffusion stage. Declare `Delay d1(maxsize)` and call `diffuse(sig, 142, d1, 0.6)`.
# The delay write is the feedback state (stage1 reads the line back through *coef),
# so it is denormal-flushed — bit-transparent for normal values.
DIFFUSE_FN = """diffuse(sig, delaySamps, delaySig, coef) {
	stage1 = sig - delaySig.read(delaySamps) * coef;
	delaySig.write(fixdenorm(stage1));
	stage2 = stage1 * coef + delaySig.read(delaySamps);
	return stage2;
}"""


def diffuse_fn() -> str:
    """Return the gen function-definition for ``diffuse(sig, delaySamps, d, coef)``
    where ``d`` is a gen ``Delay`` — the compact one-multiply Schroeder allpass.
    Chain several (mutually-prime delays) for reverb diffusion."""
    return DIFFUSE_FN


HIGHPASS_12_FN = _tpt_svf_12("highpass_12", "hp", "hp12")


def lowpass_12_fn() -> str:
    """Return the gen function-definition for ``lowpass_12(sig, cf, q)`` — a
    12 dB/oct lowpass (Zavalishin TPT state-variable filter; the RBJ cookbook
    LPF magnitude response at cutoff ``cf`` Hz and resonance ``q``) with
    smoothed, modulation-safe controls."""
    return LOWPASS_12_FN


def highpass_12_fn() -> str:
    """Return the gen function-definition for ``highpass_12(sig, cf, q)`` — the
    12 dB/oct highpass output of the same TPT state-variable filter as
    ``lowpass_12``."""
    return HIGHPASS_12_FN


def allpass_fn() -> str:
    """Return the gen function-definition for ``allpass(x, g, delaySamps, d1, d2)``
    where d1/d2 are gen ``Delay`` operators — a Schroeder allpass (direct form I)
    for reverb diffusion. Chain N of these, with mutually prime delays, for a
    dense tail."""
    return ALLPASS_FN


def ring_delay(name: str, size_samps, *, input: str = "x", delay: str = "dsamps",
               out: str = "y", index: str = "his_widx") -> str:
    """Data-backed ring buffer: write ``input`` at the head, read a ``delay``-sample-
    old value (wrapped), advance the head. The granular/looper/delay keystone.

    Returns a run of statements (declarations + per-sample body) grounded in the
    standard poke/peek/wrap ring-buffer idiom. ``size_samps`` is the buffer length.
    The line write is denormal-flushed: when the caller closes a feedback loop
    around it (``input`` mixing the read-back ``out``), a silent tail would
    otherwise recirculate subnormals; for a plain (feed-forward) delay the
    flush is bit-transparent.
    """
    return (
        f"Data {name}({size_samps});\n"
        f"History {index}(0);\n"
        f"poke({name}, fixdenorm({input}), 0, {index});\n"
        f"{out} = peek({name}, wrap({index} - ({delay}), 0, {size_samps}), 0);\n"
        f"{index} = wrap({index} + 1, 0, {size_samps});"
    )


# A drive-able logistic-sigmoid saturation curve whose knee
# is set by `sigmoid` (clamped <= -2): -2 ~= a tanh approximation, -5 ~= 'tape',
# and you can drive it to -100 for a hard squash. `pregain`/`postgain` are in dB.
# The curve is the single line `y = (2/(1+exp(sigmoid*x))) - 1`.
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
    saturator (pre/post gain in dB, knee set by ``sigmoid``): ``sigmoid``=-2 approximates tanh, -5 is tape-like."""
    return VARIABLE_SIGMOID_FN


# The modulated allpass reverb. Per side, Dattorro's four input diffusers (J.
# Dattorro, "Effect Design Part 1", JAES 1997: 4.77/3.60/12.73/9.30 ms at gains
# 0.75/0.75/0.625/0.625; the right side is stretched 3.7% so a mono input
# decorrelates) feed a figure-8 tank: each side's diffused input plus the OTHER
# side's damped loop output runs through two size-scaled, slowly modulated
# allpasses into that side's loop delay. Times are ms at a size scale of 1;
# `size` 0..1 maps to a 0.35..2.0 scale.
_PRE_DIFFUSER_GAINS = (0.75, 0.75, 0.625, 0.625)


_R_STRETCH = 1.037


_TANK_MS = {"L": (41.3, 17.1, 23.3), "R": (47.9, 18.7, 25.9)}  # loop, ap 1, ap 2


_TANK_AP_GAINS = (0.6, 0.5)


_MOD_HZ = 0.5


_MOD_DEPTH = 0.0035


def modulated_allpass_reverb(*, in_left: str = "in1", in_right: str = "in2",
                             out_left: str = "out1", out_right: str = "out2",
                             size: str = "rvbSize", damp_hz: str = "rvbDamp",
                             decay: str = "rvbDecay",
                             dry_wet: str = "rvbMix") -> str:
    """Emit a complete stereo allpass-reverb gen~ program (ready for
    ``build_gendsp(code, nin=2, nout=2)``).

    Per side, four series Schroeder allpasses at Dattorro's 1997 input-diffusion
    times feed a figure-8 tank: two size-scaled allpasses, slowly modulated
    (0.5 Hz, ±0.35%) against metallic ringing, into a loop delay whose damped
    (``lowpass_12``) output feeds the OTHER side. ``size`` is 0..1 (smoothed, 0.35x
    to 2x the base times), ``damp_hz`` the loop lowpass cutoff, ``decay`` the
    loop feedback (0..0.98), ``dry_wet`` 0..1. Each control that is a plain
    name (not ``inN``) is declared as a ``Param``.

    Built on the shipped ``allpass_fn`` / ``lowpass_12_fn`` primitives.
    """
    other = {"L": "R", "R": "L"}
    decls = ["History rv_size(-1);", "History rv_lfo(0);"]
    for side in ("L", "R"):
        decls.append(f"Delay rv_loop{side}(24000);")
        for i in range(len(_PRE_DIFFUSER_GAINS)):
            decls.append(f"Delay rv_pre{side}{i}x(4096); Delay rv_pre{side}{i}y(4096);")
        for i in (1, 2):
            decls.append(f"Delay rv_ap{side}{i}x(12000); Delay rv_ap{side}{i}y(12000);")
    stmts = [
        f"rv_target = clip({size}, 0, 1);",
        "if (rv_size < 0) {",
        "\trv_size = rv_target;",
        "}",
        "rv_size = rv_size + (rv_target - rv_size) * (1 - exp(-20 / samplerate));",
        "rv_scale = 0.35 + 1.65 * rv_size;",
        f"rv_lfo = wrap(rv_lfo + {_MOD_HZ:g} / samplerate, 0, 1);",
        f"rv_modA = 1 + {_MOD_DEPTH:g} * sin(twopi * rv_lfo);",
        f"rv_modB = 1 - {_MOD_DEPTH:g} * sin(twopi * rv_lfo);",
        f"rv_fb = clip({decay}, 0, 0.98);",
        f"rv_damp = clip({damp_hz}, 200, 18000);",
    ]
    for side in ("L", "R"):
        stmts.append(
            f"rv_tail{side} = lowpass_12(rv_fb * rv_loop{side}.read(mstosamps("
            f"{_TANK_MS[side][0]:g} * rv_scale), interp=\"linear\"), rv_damp, 0.7071);")
    for side, source, stretch in (("L", in_left, 1.0), ("R", in_right, _R_STRETCH)):
        current = source
        for i, (gain, ms) in enumerate(zip(_PRE_DIFFUSER_GAINS, _DATTORRO_DIFFUSION_MS, strict=True)):
            stmts.append(f"rv_diff{side} = allpass({current}, {gain:g}, "
                         f"mstosamps({ms * stretch:.4g}), rv_pre{side}{i}x, rv_pre{side}{i}y);")
            current = f"rv_diff{side}"
    for side, (mod1, mod2) in (("L", ("rv_modA", "rv_modB")), ("R", ("rv_modB", "rv_modA"))):
        _, ap1_ms, ap2_ms = _TANK_MS[side]
        g1, g2 = _TANK_AP_GAINS
        stmts += [
            f"rv_wet{side} = allpass(rv_diff{side} + rv_tail{other[side]}, {g1:g}, "
            f"mstosamps({ap1_ms:g} * rv_scale * {mod1}), rv_ap{side}1x, rv_ap{side}1y);",
            f"rv_wet{side} = allpass(rv_wet{side}, {g2:g}, "
            f"mstosamps({ap2_ms:g} * rv_scale * {mod2}), rv_ap{side}2x, rv_ap{side}2y);",
            f"rv_loop{side}.write(fixdenorm(rv_wet{side}));",
        ]
    stmts += [
        f"rv_mix = clip({dry_wet}, 0, 1);",
        f"{out_left} = {in_left} + (rv_wetL - {in_left}) * rv_mix;",
        f"{out_right} = {in_right} + (rv_wetR - {in_right}) * rv_mix;",
    ]
    params = [(name, default, lo, hi) for name, default, lo, hi in (
        (size, 0.5, 0, 1), (damp_hz, 6000, 200, 18000),
        (decay, 0.7, 0, 0.98), (dry_wet, 0.3, 0, 1))
        if re.fullmatch(r"[A-Za-z_]\w*", name) and not re.fullmatch(r"in\d+", name)]
    return compose_gen_code(functions=[ALLPASS_FN, LOWPASS_12_FN], params=params,
                            body="\n".join(decls + stmts))


# ===========================================================================
# D3 — synth-voice kit (FM operator, wavetable LFO, envelopes, SVF)
# ===========================================================================

# ── Synth-voice primitives ──────────────────────────────────────────────────
# FM operator in the phase-modulation form of J. Chowning, "The Synthesis of
# Complex Audio Spectra by Means of Frequency Modulation" (JAES 1973):
#   y = sin(2*pi*(phase + ph + pm + feedback)).
# Self-feedback uses the mean of the last two outputs (the usual cure for the
# period-2 "hunting" of one-sample feedback) and tapers to zero toward fs/4 to
# limit aliasing. fb -1..1 maps to +-pi/2 rad (|fb| = 1 is close to a sawtooth);
# ph and pm are in cycles. A rising edge on trig resets the phase.
OP_FN = """op(freq, mult, ph, pm, fb, trig) {
	History op_phase(0);
	History op_gate(0);
	History op_y1(0);
	History op_y2(0);
	f = freq * mult;
	if (trig > 0 && op_gate <= 0) {
		op_phase = 0;
	}
	op_gate = trig;
	taper = clip(1 - 4 * abs(f) / samplerate, 0, 1);
	fbTurns = 0.125 * clip(fb, -1, 1) * taper * (op_y1 + op_y2);
	y = sin(twopi * (op_phase + ph + pm + fbTurns));
	op_y2 = op_y1;
	op_y1 = y;
	op_phase = wrap(op_phase + f / samplerate, 0, 1);
	return y;
}"""


# Power curve: for 0 <= u <= 1, p >= 0 gives u^(1+p) (bends toward 0), p < 0 the
# mirrored 1 - (1-u)^(1-p) (bends toward 1), p = 0 the identity. Odd-symmetric in
# x and clamped to |x| <= 1, so it serves as a waveshaper and as a 0..1 phase warp
# (Casio CZ-style phase distortion).
QPOW_FN = """qpow(x, p) {
	u = min(abs(x), 1);
	y = u;
	if (p >= 0) {
		y = pow(u, 1 + p);
	} else {
		y = 1 - pow(1 - u, 1 - p);
	}
	return sign(x) * y;
}"""


# One-pole AR gate envelope: while trig > 0 the level rises toward 1, otherwise
# it falls toward 0. attack and decay are rates per second (time constant 1/rate
# seconds), turned into exact one-pole coefficients 1 - exp(-rate/fs).
FADE_FN = """fade(trig, attack, decay) {
	History fd_level(0);
	fdTarget = 0;
	fdRate = max(decay, 0);
	if (trig > 0) {
		fdTarget = 1;
		fdRate = max(attack, 0);
	}
	fd_level = fixdenorm(fd_level + (fdTarget - fd_level) * (1 - exp(-fdRate / samplerate)));
	return fd_level;
}"""


# Free-running 1 -> 0 ramp clock. Each cycle falls linearly from 1 to 0 over
# `time` ms and wraps back to 1, carrying the sub-sample remainder so the period
# is exact; a rising edge on trig restarts the cycle at 1. At every (re)start the
# cycle length becomes time * (1 + 0.9 * rand * rnd_t): rand 0..1 is the jitter
# depth, rnd_t -1..1 the random draw for that cycle (pass noise() for white
# jitter, or a per-note value to tie the jitter to notes).
RAMP_FN = """ramp(trig, time, rnd_t, rand) {
	History rp_level(0);
	History rp_step(0);
	History rp_gate(0);
	if (trig > 0 && rp_gate <= 0) {
		rp_level = 0;
	}
	rp_gate = trig;
	if (rp_level <= 0) {
		jitter = 1 + 0.9 * clip(rand, 0, 1) * clip(rnd_t, -1, 1);
		rp_step = 1 / max(mstosamps(max(time, 0.01)) * jitter, 1);
		rp_level = rp_level + 1;
	}
	level = rp_level;
	rp_level = rp_level - rp_step;
	return level;
}"""


# Rational tanh approximation x*(27 + x^2)/(27 + 9*x^2), clamped at |x| = 3, where
# it reaches exactly +-1 with zero slope, so the clamp adds no kink. Odd,
# monotonic and within 0.025 of tanh.
TANA_FN = """tanA(x) {
	v = clip(x, -3, 3);
	v2 = v * v;
	return v * (27 + v2) / (27 + 9 * v2);
}"""


# 24 dB/oct LP<->HP morphing filter: two Zavalishin TPT state-variable cores in
# series (the lowpass_12 equations). Stage 1 hands stage 2 its LP/HP mix and the
# output is stage 2's LP/HP mix, so type 0 is a 4-pole lowpass, 1 a 4-pole
# highpass, and values between crossfade. f is the cutoff in Hz, q each stage's Q
# (0.7071 puts the corner at -6 dB).
SVF_FN = """svf(x, f, q, type) {
	History sv_a1(0);
	History sv_a2(0);
	History sv_b1(0);
	History sv_b2(0);
	g = tan(pi * clip(f, 5, samplerate * 0.49) / samplerate);
	k = 1 / clip(q, 0.05, 100);
	t = clip(type, 0, 1);
	den = 1 / (1 + g * (k + g));
	hpA = (x - (k + g) * sv_a1 - sv_a2) * den;
	bpA = g * hpA + sv_a1;
	lpA = g * bpA + sv_a2;
	sv_a1 = fixdenorm(g * hpA + bpA);
	sv_a2 = fixdenorm(g * bpA + lpA);
	mid = lpA + (hpA - lpA) * t;
	hpB = (mid - (k + g) * sv_b1 - sv_b2) * den;
	bpB = g * hpB + sv_b1;
	lpB = g * bpB + sv_b2;
	sv_b1 = fixdenorm(g * hpB + bpB);
	sv_b2 = fixdenorm(g * bpB + lpB);
	return lpB + (hpB - lpB) * t;
}"""


# Wavetable LFO: buf holds one single-cycle shape per channel (bipolar -1..1).
# phase 0..1 (from the caller's phasor) is warped by qpow(phase, bend), read with
# sample() from channel floor(wave) and crossfaded into the next channel by
# wave's fraction, so wave scans the shapes continuously (keep it within
# 0..channels-1). uni > 0 rescales the output to 0..1.
LFO_OSC_FN = """lfo_osc(buf, phase, uni, wave, bend) {
	warped = qpow(wrap(phase, 0, 1), bend);
	w = max(wave, 0);
	c0 = floor(w);
	a = sample(buf, warped, c0);
	b = sample(buf, warped, c0 + 1);
	y = a + (b - a) * (w - c0);
	if (uni > 0) {
		y = y * 0.5 + 0.5;
	}
	return y;
}"""


def op_fn() -> str:
    """Return the gen function-definition for ``op(freq, mult, ph, pm, fb, trig)``
    — a phase-modulation FM operator (Chowning FM) at ``freq * mult`` Hz with
    a phase offset ``ph`` and modulation input ``pm`` (both in cycles), signed
    self-feedback ``fb`` (-1..1) and a phase reset on each rising ``trig``.
    Chain operators by feeding one output into the next ``pm``."""
    return OP_FN


def qpow_fn() -> str:
    """Return the gen function-definition for ``qpow(x, p)`` — a signed power
    curve (``p`` = 0 identity, > 0 bends toward 0, < 0 toward 1) for parameter
    curves, waveshaping and CZ-style phase distortion."""
    return QPOW_FN


def fade_env_fn() -> str:
    """Return the gen function-definition for ``fade(trig, attack, decay)`` — a
    one-pole AR gate envelope: rises toward 1 while ``trig`` > 0, falls toward 0
    otherwise, ``attack``/``decay`` in rate per second (time constant 1/rate s).
    The adsr_codebox core."""
    return FADE_FN


def ramp_env_fn() -> str:
    """Return the gen function-definition for ``ramp(trig, time, rnd_t, rand)`` —
    a free-running 1→0 ramp clock of ``time`` ms per cycle, restarted by a rising
    ``trig``, with each cycle's length jittered by ``rand`` (depth) times
    ``rnd_t`` (the caller's -1..1 random draw)."""
    return RAMP_FN


def tanh_approx_fn() -> str:
    """Return the gen function-definition for ``tanA(x)`` — a fast rational
    tanh approximation that reaches ±1 smoothly at |x| = 3."""
    return TANA_FN


def svf_fn() -> str:
    """Return the gen function-definition for ``svf(x, f, q, type)`` — two
    cascaded Zavalishin TPT state-variable filters (24 dB/oct), ``type``
    morphing lowpass (0) to highpass (1). Self-contained."""
    return SVF_FN


def lfo_osc_fn() -> str:
    """Return the gen function-definition for ``lfo_osc(buf, phase, uni, wave, bend)``
    — a wavetable LFO that scans the shapes stored one per channel of ``buf``
    (``wave``) with ``qpow`` phase distortion (``bend``) and an optional 0..1
    output (``uni``). MUST be emitted together with ``qpow_fn`` (it calls
    ``qpow``)."""
    return LFO_OSC_FN


# ── T29 reverb kernels (dsp_library_plan #3/#9/#12) ─────────────────────────
# Dattorro 1997 input-diffusion times (ms) — the canonical pre-stage.
_DATTORRO_DIFFUSION_MS = [4.77, 3.60, 12.73, 9.30]


def allpass_diffusion_chain(x: str, out: str, num_stages: int = 4,
                            delay_times_ms=None, feedback_coeff: float = 0.5,
                            *, prefix: str = "apd") -> str:
    """Schroeder/Dattorro allpass diffusion chain (plan #3) — the reverb
    pre-stage that smears the input into a dense, colorless cloud.

    Per stage: ``y = -g*x + z`` with ``z`` the delayed ``x + g*y`` (the
    canonical one-multiplier-per-branch allpass). Defaults to Dattorro's
    four 1997 input-diffusion times. Delay-based — gen_lint proves shape;
    behaviour is device-level QA (gen_sim refuses Delay by design).
    """
    times = list(delay_times_ms) if delay_times_ms else (
        _DATTORRO_DIFFUSION_MS * ((num_stages + 3) // 4))[:num_stages]
    g = float(feedback_coeff)
    lines = []
    cur = x
    for i, t in enumerate(times[:num_stages]):
        d = f"{prefix}_d{i}"
        lines.append(f"Delay {d}(9600);")
        lines += [
            f"{prefix}_z{i} = {d}.read(mstosamps({t:g}), interp=\"none\");",
            f"{prefix}_y{i} = -{g:g} * {cur} + {prefix}_z{i};",
            f"{d}.write(fixdenorm({cur} + {g:g} * {prefix}_y{i}));",
        ]
        cur = f"{prefix}_y{i}"
    lines.append(f"{out} = {cur};")
    return "\n".join(lines) + "\n"


def fdn_reverb(in_l: str = "in1", in_r: str = "in2", out_l: str = "out1",
               out_r: str = "out2", fb_amount: str = "fb",
               damp_freq: str = "damp_hz", size: str = "size",
               *, prefix: str = "fdn") -> str:
    """4-line Hadamard FDN reverb (plan #9): four prime-ish delays, the
    orthonormal H4 feedback matrix (0.5 * ±1 pattern — energy-preserving,
    so ``{fb_amount}`` alone sets decay), and a one-pole damping lowpass
    per line. ``{size}`` scales the base times (0.25..4 sane). Stereo out
    decorrelates as L = d0+d2, R = d1+d3.
    """
    base_ms = [29.7, 37.1, 41.1, 43.7]
    p = prefix
    lines = [f"History {p}_lp{i}(0.); " for i in range(4)]
    lines = ["".join(lines).rstrip()]
    for i in range(4):
        lines.append(f"Delay {p}_d{i}(96000);")
    # read the four lines (damped by a one-pole each)
    lines.append(f"{p}_dampk = 1.0 - exp(-6.2831853 * "
                 f"clamp({damp_freq}, 200., 18000.) / samplerate);")
    for i, t in enumerate(base_ms):
        lines += [
            f"{p}_r{i} = {p}_d{i}.read(mstosamps({t:g} * "
            f"clamp({size}, 0.25, 4.)), interp=\"linear\");",
            f"{p}_lp{i} = {p}_lp{i} + {p}_dampk * ({p}_r{i} - {p}_lp{i});",
        ]
    # Hadamard H4 (rows of +/-; 0.5 normalizes -> unitary)
    lines += [
        f"{p}_h0 = 0.5 * ({p}_lp0 + {p}_lp1 + {p}_lp2 + {p}_lp3);",
        f"{p}_h1 = 0.5 * ({p}_lp0 - {p}_lp1 + {p}_lp2 - {p}_lp3);",
        f"{p}_h2 = 0.5 * ({p}_lp0 + {p}_lp1 - {p}_lp2 - {p}_lp3);",
        f"{p}_h3 = 0.5 * ({p}_lp0 - {p}_lp1 - {p}_lp2 + {p}_lp3);",
    ]
    # write back: input injection (L into even, R into odd lines) + feedback
    lines.append(f"{p}_g = clamp({fb_amount}, 0., 0.98);")
    for i in range(4):
        inj = in_l if i % 2 == 0 else in_r
        lines.append(f"{p}_d{i}.write({inj} + {p}_g * {p}_h{i});")
    lines += [
        f"{out_l} = {p}_lp0 + {p}_lp2;",
        f"{out_r} = {p}_lp1 + {p}_lp3;",
    ]
    return "\n".join(lines) + "\n"


def dattorro_plate_tank(in_sig: str, out_l: str, out_r: str,
                        decay: str = "decay", damping: str = "damping",
                        *, prefix: str = "plate") -> str:
    """The Dattorro 1997 plate tank (plan #12): input diffusion (4
    allpasses) into the figure-8 loop — per branch a decay-diffusion
    allpass, a long delay, a damping one-pole, a second allpass and a
    second delay, each branch feeding the OTHER scaled by ``{decay}``.
    Output taps follow the paper's cross-tap idea (compacted to 3 per
    side). ``{decay}`` 0..0.95, ``{damping}`` as a Hz lowpass.
    """
    p = prefix
    head = allpass_diffusion_chain(in_sig, f"{p}_diff", prefix=f"{p}_ind")
    lines = [head.rstrip()]
    lines.append(f"History {p}_lpA(0.); History {p}_lpB(0.); "
                 f"History {p}_fbA(0.); History {p}_fbB(0.);")
    for name, ap1_t, ap1_g, d1_t, ap2_t, ap2_g, d2_t, exc_hz in (
            ("A", 22.58, 0.70, 149.62, 60.48, 0.50, 124.99, 1.0),
            ("B", 30.51, 0.70, 141.69, 89.24, 0.50, 106.28, 0.87)):
        b = f"{p}_{name}"
        other = f"{p}_fb{'B' if name == 'A' else 'A'}"
        lines += [
            f"Delay {b}_ap1(samplerate); Delay {b}_d1(samplerate); "
            f"Delay {b}_ap2(samplerate); Delay {b}_d2(samplerate);",
            # branch input: diffused input + the OTHER branch's tail * decay
            f"{b}_in = {p}_diff + {other} * clamp({decay}, 0., 0.95);",
            # decay-diffusion allpass 1, with the paper's EXCURSION: a slow
            # ~1 Hz LFO wobbles this read by ±16 samples @ 29.761 kHz
            # (= ±0.5376 ms, samplerate-scaled) — the Dattorro-1997 detail
            # that breaks the static tank's metallic ring (hunt #64). The
            # wobble forces a fractional tap -> interp="linear" on this read.
            f"{b}_exc = mstosamps(0.5376) * sin(6.2831853 * phasor({exc_hz:g}));",
            f"{b}_z1 = {b}_ap1.read(mstosamps({ap1_t:g}) + {b}_exc, "
            f"interp=\"linear\");",
            f"{b}_y1 = -{ap1_g:g} * {b}_in + {b}_z1;",
            f"{b}_ap1.write(fixdenorm({b}_in + {ap1_g:g} * {b}_y1));",
            # long delay 1 -> damping one-pole
            f"{b}_t1 = {b}_d1.read(mstosamps({d1_t:g}), interp=\"none\");",
            f"{b}_d1.write({b}_y1);",
            f"{p}_dampk = 1.0 - exp(-6.2831853 * "
            f"clamp({damping}, 500., 18000.) / samplerate);",
            f"{p}_lp{name} = fixdenorm({p}_lp{name} + {p}_dampk * "
            f"({b}_t1 - {p}_lp{name}));",
            # allpass 2 -> delay 2 -> becomes this branch's tail
            f"{b}_z2 = {b}_ap2.read(mstosamps({ap2_t:g}), interp=\"none\");",
            f"{b}_y2 = -{ap2_g:g} * {p}_lp{name} + {b}_z2;",
            f"{b}_ap2.write(fixdenorm({p}_lp{name} + {ap2_g:g} * {b}_y2));",
            f"{b}_t2 = {b}_d2.read(mstosamps({d2_t:g}), interp=\"none\");",
            f"{b}_d2.write({b}_y2);",
            f"{p}_fb{name} = fixdenorm({b}_t2);",
        ]
    # cross taps (paper-style: each ear listens mostly to the OTHER branch)
    lines += [
        f"{out_l} = 0.6 * ({p}_B_d1.read(mstosamps(52.7), interp=\"none\") "
        f"+ {p}_B_d2.read(mstosamps(66.9), interp=\"none\") "
        f"- {p}_A_ap2.read(mstosamps(29.8), interp=\"none\"));",
        f"{out_r} = 0.6 * ({p}_A_d1.read(mstosamps(49.6), interp=\"none\") "
        f"+ {p}_A_d2.read(mstosamps(73.5), interp=\"none\") "
        f"- {p}_B_ap2.read(mstosamps(27.4), interp=\"none\"));",
    ]
    return "\n".join(lines) + "\n"


def clickless_delay(x: str, out: str, time_ms: str = "time_ms", *,
                    prefix: str = "cxd", max_ms: float = 2000.0,
                    xfade_ms: float = 50.0) -> str:
    """Click-free variable delay (T36/Q19 — the vdelay~ Building
    Block as a gen~ kernel).

    Two read taps on one line: the CURRENT tap keeps sounding while a
    time change fades the NEW tap in over ``xfade_ms`` (equal-power), then
    the new time becomes current — no zipper/click on automation, no pitch
    chirp (unlike a slewed single tap). A time change arriving mid-fade is
    picked up on the next completed fade.
    """
    p = prefix
    samps = int(max_ms * 48) + 96
    return (
        f"Delay {p}_dl({samps});\n"
        f"History {p}_cur(1.); History {p}_tgt(1.); History {p}_xf(1.);\n"
        f"{p}_dl.write({x});\n"
        f"{p}_nt = clamp({time_ms}, 0.02, {max_ms});\n"
        f"if ({p}_nt != {p}_tgt && {p}_xf >= 1.) {{\n"
        f"    {p}_tgt = {p}_nt;\n"
        f"    {p}_xf = 0.;\n"
        f"}}\n"
        f"{p}_xf = {p}_xf + 1000. / ({xfade_ms} * samplerate);\n"
        f"{p}_g = {p}_xf > 1. ? 1. : {p}_xf;\n"
        f"{p}_a = {p}_dl.read(mstosamps({p}_cur), interp=\"linear\");\n"
        f"{p}_b = {p}_dl.read(mstosamps({p}_tgt), interp=\"linear\");\n"
        f"{out} = {p}_a * cos({p}_g * 1.5707963) "
        f"+ {p}_b * sin({p}_g * 1.5707963);\n"
        f"if ({p}_g >= 1.) {{\n"
        f"    {p}_cur = {p}_tgt;\n"
        f"}}\n"
    )
