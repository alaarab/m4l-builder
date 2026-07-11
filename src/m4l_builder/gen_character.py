"""Character / coloration DSP — the reusable "vibe" algorithms (harvest pass).

The filter/dynamics/stereo primitives in :mod:`gen_snippets` are the clean,
neutral building blocks. This module is the other half of the palette: the
*character* algorithms — optical compression, tape, Leslie, BBD chorus,
de-essing, console coloration, sidechain ducking — that give a device its
identity. Each was proven in Live inside a shipping device, then extracted here
so the ALGORITHM survives independently of any one faceplate. Compose these into
new devices instead of re-deriving them.

Every function is self-contained: it emits its own prefixed ``History`` /
``Delay`` declarations at the top of its returned block and namespaces every
scratch variable by ``prefix`` (pass a unique ``prefix`` to use one twice in a
codebox). Because gen~ requires ALL declarations before the first executable
statement, HOIST the decls to the top of the kernel — the fleet ``_hoist_history``
helper (see e.g. ``plugins/tilt/build.py``) does exactly this, or place the call
first. ``x`` / ``xl`` / ``xr`` and the parameter arguments are gen expressions
(a live ``Param`` name or a literal), all tunable at signal rate.

These are ports of Live-verified kernels; the math is byte-faithful to the
originals (Opti, Chrono, Rotary, Ensemble, Sibilant Surgeon, Console, Ducking
Delay). See :mod:`gen_snippets` for the neutral primitives they build on
(``soft_knee_gain_computer``, ``frac_read_cubic``).
"""

from __future__ import annotations

from .gen_snippets import frac_read_cubic, soft_knee_gain_computer

__all__ = [
    "optical_leveler",
    "wow_flutter",
    "tape_hysteresis",
    "leslie_rotor",
    "bbd_chorus",
    "bbd_ensemble",
    "deesser",
    "console_saturation",
    "crosstalk",
    "iron_transformer",
    "duck_gain",
    "haas_widener",
]

TWO_PI = "6.2831853"
HALF_PI = "1.5707963"


def optical_leveler(
    xl: str, xr: str, outl: str, outr: str, peakred: str, *,
    makeup: str = "0.", gr_out: str | None = None, prefix: str = "opt",
) -> str:
    """LA-2A-style optical leveler with a *program-dependent* release (harvested
    from Opti).

    The signature move of an optical compressor is that the release stretches
    the longer it has been working: a memory "pool" charges from the current
    gain-reduction depth and lengthens the release from ~60 ms (idle) toward
    ~3 s (fully charged), so sustained level is smoothed while transients still
    recover fast. ``peakred`` (0..100) drives threshold DOWN and ratio UP in
    lockstep (the single LA-2A "Peak Reduction" knob). Detection is stereo-linked
    (max of both channels) so the image never shifts; one gain is applied to
    both. Set ``gr_out`` to a var name to tap gain reduction (dB, <= 0) for a
    meter. Built on :func:`~m4l_builder.gen_snippets.soft_knee_gain_computer`.
    """
    p = prefix
    gr = f"{p}_gr"
    block = (
        f"History {p}_env(-90.); History {p}_pool(0.);\n"
        f"{p}_lvl = atodb(max(abs({xl}), abs({xr})) + 1e-9);\n"
        f"{p}_atk = 1.0 - exp(-1.0 / (0.010 * samplerate));\n"
        f"{p}_relms = 60.0 + {p}_pool * 2940.0;\n"
        f"{p}_relk = 1.0 - exp(-1.0 / (0.001 * {p}_relms * samplerate));\n"
        f"{p}_env = {p}_lvl > {p}_env ? {p}_env + ({p}_lvl - {p}_env) * {p}_atk"
        f" : {p}_env + ({p}_lvl - {p}_env) * {p}_relk;\n"
        f"{p}_pr = clamp({peakred}, 0., 100.) * 0.01;\n"
        f"{p}_thr = 0.0 - {p}_pr * 40.0;\n"
        f"{p}_ratio = 2.0 + {p}_pr * 4.0;\n"
        + soft_knee_gain_computer(
            f"{p}_env", f"{p}_thr", f"{p}_ratio", "12.0", gr,
            over=f"{p}_over", half_knee=f"{p}_hk", slope=f"{p}_slope",
            t=f"{p}_t")
        + "\n"
        f"{p}_grn = clamp(0.0 - {gr}, 0., 24.) / 24.;\n"
        f"{p}_pk = {p}_grn > {p}_pool ? 0.0005 : 0.00002;\n"
        f"{p}_pool = {p}_pool + ({p}_grn - {p}_pool) * {p}_pk;\n"
        f"{p}_g = dbtoa({gr} + ({makeup}));\n"
        f"{outl} = {xl} * {p}_g;\n"
        f"{outr} = {xr} * {p}_g;\n"
    )
    if gr_out is not None:
        block += f"{gr_out} = {gr};\n"
    return block


def wow_flutter(
    pos_out: str, base_ms: str, wow: str, flutter: str, *,
    prefix: str = "wf",
) -> str:
    """Tape transport drift as a modulated read position in SAMPLES (from Chrono).

    One motor drives two depth-scaled modulators: slow WOW (~0.9 Hz sine) and
    faster FLUTTER (~7.3 Hz sine plus a band-limited noise wobble). ``wow`` and
    ``flutter`` are 0..100 depths; ``base_ms`` is the nominal head-gap delay in
    ms. Emits ``pos_out`` = position in samples for a fractional
    :func:`~m4l_builder.gen_snippets.frac_read_cubic` read off a ``Delay`` you
    write the input into. Share one ``wf`` transport across L/R (write two Delay
    lines, read both at the same ``pos_out``) so the channels drift together.
    """
    p = prefix
    return (
        f"History {p}_wph(0.); History {p}_fph(0.); History {p}_fn(0.);\n"
        f"{p}_wph = wrap({p}_wph + 0.9 / samplerate, 0., 1.);\n"
        f"{p}_fph = wrap({p}_fph + 7.3 / samplerate, 0., 1.);\n"
        f"{p}_fnk = 1.0 - exp(-{TWO_PI} * 3. / samplerate);\n"
        f"{p}_fn = {p}_fn + {p}_fnk * (noise() - {p}_fn);\n"
        f"{p}_wamt = clamp({wow}, 0., 100.) * 0.01;\n"
        f"{p}_famt = clamp({flutter}, 0., 100.) * 0.01;\n"
        f"{p}_base = mstosamps({base_ms});\n"
        f"{pos_out} = {p}_base + mstosamps(2.5) * {p}_wamt * sin({TWO_PI} * {p}_wph)"
        f" + mstosamps(0.35) * {p}_famt * (sin({TWO_PI} * {p}_fph) + 6. * {p}_fn);\n"
    )


def tape_hysteresis(
    x: str, out: str, drive: str, *, memory: str = "0.12", prefix: str = "hy",
) -> str:
    """Magnetic-tape record-head saturation with hysteresis memory (from Chrono).

    A ``tanh`` soft-clip whose input is biased by ``memory`` times the PREVIOUS
    saturated sample — the magnetization "remembers" its recent state, the
    hysteretic character of tape. ``drive`` is 0..24 dB into the stage;
    an equal-and-opposite makeup (``-drive * 0.5 dB``) keeps the level roughly
    matched so the knob is pure color. For lowest aliasing, wrap this in the 2x
    oversampler (``os2x_*`` in :mod:`gen_snippets`) as Chrono does; standalone it
    is a clean single-rate tape stage.
    """
    p = prefix
    return (
        f"History {p}_hy(0.);\n"
        f"{p}_dg = dbtoa(clamp({drive}, 0., 24.));\n"
        f"{p}_comp = dbtoa(0. - clamp({drive}, 0., 24.) * 0.5);\n"
        f"{p}_h = tanh({x} * {p}_dg + ({memory}) * {p}_hy);\n"
        f"{p}_hy = {p}_h;\n"
        f"{out} = {p}_h * {p}_comp;\n"
    )


def leslie_rotor(
    mono: str, outl: str, outr: str, *, speed: str, doppler: str,
    balance: str, prefix: str = "lsl", horn_hz_out: str | None = None,
    drum_hz_out: str | None = None,
) -> str:
    """Leslie rotary speaker: dual horn+drum rotors with mechanical inertia
    (from Rotary).

    An 800 Hz crossover splits ``mono`` into a HORN (highs) and DRUM (lows)
    rotor. Each rotor is Doppler FM (a fractional-delay read modulated by the
    rotor angle) + throat/baffle AM + angular panning, and each SPINS UP/DOWN
    through a one-pole inertia (~1 s horn, ~4 s drum) toward the ``speed`` target
    (0 = slow/chorale, 1 = fast/tremolo) so you hear the spool-up. ``doppler``
    (0..100) scales pitch+pan depth; ``balance`` (0..100) crossfades horn vs drum
    (50 = both). Stereo out from mono. Set ``horn_hz_out`` / ``drum_hz_out`` to
    tap the live rotor rates (Hz) — a hero display should advance its OWN
    animation phase at those rates for smooth spin at any frame rate (streaming
    the audio-rate rotor phase itself would strobe). Self-contained: emits its own
    two ``Delay`` lines + rotor state.
    """
    p = prefix
    block = (
        f"Delay {p}_hd(4800); Delay {p}_dd(4800);\n"
        f"History {p}_hrate(0.8); History {p}_drate(0.66);\n"
        f"History {p}_hph(0.); History {p}_dph(0.25); History {p}_xlp(0.);\n"
        f"{p}_xk = 1.0 - exp(-{TWO_PI} * 800. / samplerate);\n"
        f"{p}_xlp = {p}_xlp + {p}_xk * ({mono} - {p}_xlp);\n"
        f"{p}_drum_in = {p}_xlp;\n"
        f"{p}_horn_in = {mono} - {p}_xlp;\n"
        f"{p}_ht = {speed} > 0.5 ? 6.7 : 0.8;\n"
        f"{p}_dt = {speed} > 0.5 ? 5.7 : 0.66;\n"
        f"{p}_hk = 1.0 - exp(-1.0 / (1.0 * samplerate));\n"
        f"{p}_dk = 1.0 - exp(-1.0 / (4.0 * samplerate));\n"
        f"{p}_hrate = {p}_hrate + {p}_hk * ({p}_ht - {p}_hrate);\n"
        f"{p}_drate = {p}_drate + {p}_dk * ({p}_dt - {p}_drate);\n"
        f"{p}_hph = wrap({p}_hph + {p}_hrate / samplerate, 0., 1.);\n"
        f"{p}_dph = wrap({p}_dph + {p}_drate / samplerate, 0., 1.);\n"
        f"{p}_dep = clamp({doppler}, 0., 100.) * 0.01;\n"
        f"{p}_hd.write({p}_horn_in);\n"
        f"{p}_hs = sin({TWO_PI} * {p}_hph);\n"
        f"{p}_hc = cos({TWO_PI} * {p}_hph);\n"
        f"{p}_hp = mstosamps(1.0) + mstosamps(0.6) * {p}_dep * {p}_hs;\n"
        + frac_read_cubic(f"{p}_hd", f"{p}_hp", f"{p}_hv")
        + f"{p}_ham = 1.0 - 0.35 * {p}_dep * (0.5 + 0.5 * {p}_hc);\n"
        f"{p}_hgl = 0.5 * (1.0 - 0.8 * {p}_dep * {p}_hs);\n"
        f"{p}_hgr = 0.5 * (1.0 + 0.8 * {p}_dep * {p}_hs);\n"
        f"{p}_hL = {p}_hv * {p}_ham * {p}_hgl;\n"
        f"{p}_hR = {p}_hv * {p}_ham * {p}_hgr;\n"
        f"{p}_dd.write({p}_drum_in);\n"
        f"{p}_ds = sin({TWO_PI} * {p}_dph);\n"
        f"{p}_dc = cos({TWO_PI} * {p}_dph);\n"
        f"{p}_dp = mstosamps(1.0) + mstosamps(0.25) * {p}_dep * {p}_ds;\n"
        + frac_read_cubic(f"{p}_dd", f"{p}_dp", f"{p}_dv")
        + f"{p}_dam = 1.0 - 0.25 * {p}_dep * (0.5 + 0.5 * {p}_dc);\n"
        f"{p}_dgl = 0.5 * (1.0 - 0.4 * {p}_dep * {p}_ds);\n"
        f"{p}_dgr = 0.5 * (1.0 + 0.4 * {p}_dep * {p}_ds);\n"
        f"{p}_dL = {p}_dv * {p}_dam * {p}_dgl;\n"
        f"{p}_dR = {p}_dv * {p}_dam * {p}_dgr;\n"
        f"{p}_bal = clamp({balance}, 0., 100.) * 0.01;\n"
        f"{p}_hg = min(1., {p}_bal * 2.);\n"
        f"{p}_dg = min(1., (1. - {p}_bal) * 2.);\n"
        f"{outl} = ({p}_hL * {p}_hg + {p}_dL * {p}_dg) * 2.;\n"
        f"{outr} = ({p}_hR * {p}_hg + {p}_dR * {p}_dg) * 2.;\n"
    )
    if horn_hz_out is not None:
        block += f"{horn_hz_out} = {p}_hrate;\n"
    if drum_hz_out is not None:
        block += f"{drum_hz_out} = {p}_drate;\n"
    return block


def bbd_chorus(
    mono: str, outl: str, outr: str, *, rate: str, depth: str, voices: str,
    tone: str, prefix: str = "bbd", sweep_out: str | None = None,
) -> str:
    """Bucket-brigade string-machine chorus, 2 or 3 voices (from Ensemble).

    A soft ``tanh`` BBD input stage feeds one delay line read by 2/3 voices at
    120-degree-spread phases. Each voice is swept by a DUAL-RANK LFO — a slow
    rank at ``rate`` plus a fast shimmer rank ~9.7x — for the lush, non-periodic
    Solina/Juno wash. ``depth`` (0..100) scales the sweep; ``voices`` >= 3
    enables the centre voice; ``tone`` (2k..16k Hz) is a per-voice one-pole for
    BBD darkness. Voices pan v1->L, v3->R, v2->centre; equal-power layout.
    Stereo out from mono. Set ``sweep_out`` to tap voice-1 sweep (ms). The caller
    does the dry/wet crossfade. Self-contained: emits its own ``Delay`` + state.
    """
    p = prefix
    block = (
        f"Delay {p}_ens(9600);\n"
        f"History {p}_phs(0.); History {p}_phf(0.);\n"
        f"History {p}_b1(0.); History {p}_b2(0.); History {p}_b3(0.);\n"
        f"{p}_mono = tanh(({mono}) * 0.6);\n"
        f"{p}_ens.write({p}_mono);\n"
        f"{p}_r = clamp({rate}, 0.05, 8.);\n"
        f"{p}_phs = wrap({p}_phs + {p}_r / samplerate, 0., 1.);\n"
        f"{p}_phf = wrap({p}_phf + {p}_r * 9.7 / samplerate, 0., 1.);\n"
        f"{p}_dpt = clamp({depth}, 0., 100.) * 0.01;\n"
        f"{p}_base = mstosamps(12.);\n"
        f"{p}_sws = mstosamps(4.5) * {p}_dpt;\n"
        f"{p}_swf = mstosamps(0.9) * {p}_dpt;\n"
        f"{p}_p1 = {p}_base + {p}_sws * sin({TWO_PI} * {p}_phs)"
        f" + {p}_swf * sin({TWO_PI} * {p}_phf);\n"
        f"{p}_p2 = {p}_base + {p}_sws * sin({TWO_PI} * ({p}_phs + 0.33333))"
        f" + {p}_swf * sin({TWO_PI} * ({p}_phf + 0.33333));\n"
        f"{p}_p3 = {p}_base + {p}_sws * sin({TWO_PI} * ({p}_phs + 0.66667))"
        f" + {p}_swf * sin({TWO_PI} * ({p}_phf + 0.66667));\n"
        + frac_read_cubic(f"{p}_ens", f"{p}_p1", f"{p}_v1")
        + frac_read_cubic(f"{p}_ens", f"{p}_p2", f"{p}_v2")
        + frac_read_cubic(f"{p}_ens", f"{p}_p3", f"{p}_v3")
        + f"{p}_tk = 1.0 - exp(-{TWO_PI} * clamp({tone}, 2000., 16000.) / samplerate);\n"
        f"{p}_b1 = {p}_b1 + {p}_tk * ({p}_v1 - {p}_b1);\n"
        f"{p}_b2 = {p}_b2 + {p}_tk * ({p}_v2 - {p}_b2);\n"
        f"{p}_b3 = {p}_b3 + {p}_tk * ({p}_v3 - {p}_b3);\n"
        f"{p}_g2 = {voices} > 2.5 ? 1. : 0.;\n"
        f"{p}_norm = 0.85 / (1. + 0.5 * {p}_g2);\n"
        f"{outl} = ({p}_b1 + 0.5 * {p}_g2 * {p}_b2) * {p}_norm;\n"
        f"{outr} = ({p}_b3 + 0.5 * {p}_g2 * {p}_b2) * {p}_norm;\n"
    )
    if sweep_out is not None:
        block += f"{sweep_out} = ({p}_p1 - {p}_base) * 1000. / samplerate;\n"
    return block


def bbd_ensemble(
    mono: str, outl: str, outr: str, *, rate: str, depth: str, voices: str,
    tone: str, detune: str, shimmer: str, center_ms: str, feedback: str,
    spread: str, locut: str, prefix: str = "ens",
    sweep_out: str | None = None,
) -> str:
    """True multi-voice BBD ensemble, 2..6 voices (the bbd_chorus superset).

    One soft ``tanh`` BBD input stage (with ``feedback`` regeneration, capped
    safe and re-saturated through the same stage) feeds one delay line read by
    up to SIX voices. Each voice carries its OWN slow-rank phase accumulator
    running at ``rate`` skewed by a fixed per-voice ratio scaled by ``detune``
    (0..100 -> up to ~±17% rate variance: the non-periodic string-machine
    wash), plus the shared fast shimmer rank (~9.7x ``rate``) whose amplitude
    is ``shimmer`` (0..100; 100 = the classic bbd_chorus voicing). ``center_ms``
    (4..25) is the BBD centre tap — short is metallic/flangey, long is wide
    tape wobble. ``voices`` (2..6) gates voices in fixed order; loudness is
    re-normalised per count. ``tone`` (2k..16k) is the per-voice BBD darkness
    one-pole. Voices sit on a fixed pan layout scaled by ``spread`` (0..100;
    0 = mono wet). ``locut`` (20..500 Hz) high-passes the WET only, keeping
    the low end dry and mono. Caller does the dry/wet crossfade.
    Set ``sweep_out`` to tap voice-1 sweep (ms). Self-contained state.
    """
    p = prefix
    ks = (0.0, 0.21, -0.17, 0.34, -0.29, 0.12)      # per-voice rate skew
    pans = (-1.0, 1.0, -0.55, 0.55, -0.2, 0.2)      # fixed stereo layout
    head = (
        f"Delay {p}_ens(9600);\n"
        f"History {p}_phf(0.); History {p}_fb(0.);\n"
        + "".join(f"History {p}_ph{i}(0.); History {p}_b{i}(0.);\n"
                  for i in range(6))
        + f"History {p}_hpl(0.); History {p}_hpr(0.);\n"
        f"{p}_fbamt = clamp({feedback}, 0., 90.) * 0.007;\n"
        f"{p}_mono = tanh(({mono}) * 0.6 + {p}_fb * {p}_fbamt);\n"
        f"{p}_ens.write({p}_mono);\n"
        f"{p}_r = clamp({rate}, 0.05, 8.);\n"
        f"{p}_dt = clamp({detune}, 0., 100.) * 0.005;\n"
        f"{p}_phf = wrap({p}_phf + {p}_r * 9.7 / samplerate, 0., 1.);\n"
        f"{p}_dpt = clamp({depth}, 0., 100.) * 0.01;\n"
        f"{p}_base = mstosamps(clamp({center_ms}, 4., 25.));\n"
        f"{p}_sws = mstosamps(4.5) * {p}_dpt;\n"
        f"{p}_swf = mstosamps(0.9) * {p}_dpt"
        f" * clamp({shimmer}, 0., 100.) * 0.01;\n"
        f"{p}_tk = 1.0 - exp(-{TWO_PI} * clamp({tone}, 2000., 16000.)"
        f" / samplerate);\n"
        f"{p}_spr = clamp({spread}, 0., 100.) * 0.01;\n"
    )
    voices_blk = ""
    for i in range(6):
        off = i / 6.0
        voices_blk += (
            f"{p}_ph{i} = wrap({p}_ph{i} + {p}_r * (1. + {ks[i]} * {p}_dt)"
            f" / samplerate, 0., 1.);\n"
            f"{p}_p{i} = {p}_base + {p}_sws * sin({TWO_PI} * ({p}_ph{i}"
            f" + {off:.5f})) + {p}_swf * sin({TWO_PI} * ({p}_phf"
            f" + {off:.5f}));\n"
            + frac_read_cubic(f"{p}_ens", f"{p}_p{i}", f"{p}_v{i}")
            + f"{p}_b{i} = {p}_b{i} + {p}_tk * ({p}_v{i} - {p}_b{i});\n"
        )
        if i >= 2:
            voices_blk += f"{p}_g{i} = {voices} > {i + 0.5} ? 1. : 0.;\n"
    mix_terms_l, mix_terms_r, act_terms = [], [], ["2."]
    for i in range(6):
        gate = "1." if i < 2 else f"{p}_g{i}"
        if i >= 2:
            act_terms.append(f"{p}_g{i}")
        voices_blk += (
            f"{p}_pn{i} = {pans[i]} * {p}_spr;\n"
            f"{p}_gl{i} = cos(({p}_pn{i} + 1.) * 0.7853982);\n"
            f"{p}_gr{i} = sin(({p}_pn{i} + 1.) * 0.7853982);\n"
        )
        mix_terms_l.append(f"{gate} * {p}_b{i} * {p}_gl{i}")
        mix_terms_r.append(f"{gate} * {p}_b{i} * {p}_gr{i}")
    tail = (
        f"{p}_act = " + " + ".join(act_terms) + ";\n"
        f"{p}_norm = 0.9 / sqrt({p}_act);\n"
        f"{p}_wl = (" + " + ".join(mix_terms_l) + f") * {p}_norm;\n"
        f"{p}_wr = (" + " + ".join(mix_terms_r) + f") * {p}_norm;\n"
        f"{p}_fb = ({p}_wl + {p}_wr) * 0.5;\n"
        f"{p}_hk = 1.0 - exp(-{TWO_PI} * clamp({locut}, 20., 500.)"
        f" / samplerate);\n"
        f"{p}_hpl = {p}_hpl + {p}_hk * ({p}_wl - {p}_hpl);\n"
        f"{p}_hpr = {p}_hpr + {p}_hk * ({p}_wr - {p}_hpr);\n"
        f"{outl} = {p}_wl - {p}_hpl;\n"
        f"{outr} = {p}_wr - {p}_hpr;\n"
    )
    block = head + voices_blk + tail
    if sweep_out is not None:
        block += f"{sweep_out} = ({p}_p0 - {p}_base) * 1000. / samplerate;\n"
    return block


def deesser(
    xl: str, xr: str, outl: str, outr: str, *, split_hz: str, thresh: str,
    range_db: str, listen: str = "0.", prefix: str = "dess",
    gr_out: str | None = None, env_out: str | None = None,
) -> str:
    """Split-band de-esser: duck only the high band when sibilance triggers
    (from Sibilant Surgeon).

    A one-pole at ``split_hz`` (2k..12k) splits low/high; a fast-attack
    (0.5 ms) / 80 ms-release detector on the high band applies up to
    ``range_db`` (negative = cut) when it crosses ``thresh``, then the bands
    recombine. ``listen`` > 0.5 solos the processed high band so you can hear
    exactly what is being tamed. Stereo-linked detection keeps the image stable.
    Set ``gr_out`` to tap the applied high-band gain (dB) and ``env_out`` to tap
    the high-band detector level (dB, for a threshold display). More surgical
    than a full-band compressor for ess/harshness control.
    """
    p = prefix
    block = (
        f"History {p}_lpl(0.); History {p}_lpr(0.); History {p}_env(-90.);\n"
        f"{p}_k = 1.0 - exp(-{TWO_PI} * clamp({split_hz}, 2000., 12000.) / samplerate);\n"
        f"{p}_lpl = {p}_lpl + {p}_k * ({xl} - {p}_lpl);\n"
        f"{p}_lpr = {p}_lpr + {p}_k * ({xr} - {p}_lpr);\n"
        f"{p}_hil = {xl} - {p}_lpl;\n"
        f"{p}_hir = {xr} - {p}_lpr;\n"
        f"{p}_lvl = atodb(max(abs({p}_hil), abs({p}_hir)) + 1e-9);\n"
        f"{p}_ak = 1.0 - exp(-1.0 / (0.0005 * samplerate));\n"
        f"{p}_rk = 1.0 - exp(-1.0 / (0.080 * samplerate));\n"
        f"{p}_env = {p}_lvl > {p}_env ? {p}_env + ({p}_lvl - {p}_env) * {p}_ak"
        f" : {p}_env + ({p}_lvl - {p}_env) * {p}_rk;\n"
        f"{p}_drv = clamp(({p}_env - ({thresh})) / 10., 0., 1.);\n"
        f"{p}_hg = dbtoa(({range_db}) * {p}_drv);\n"
        f"{p}_dhl = {p}_hil * {p}_hg;\n"
        f"{p}_dhr = {p}_hir * {p}_hg;\n"
        f"{outl} = {listen} > 0.5 ? {p}_dhl : {p}_lpl + {p}_dhl;\n"
        f"{outr} = {listen} > 0.5 ? {p}_dhr : {p}_lpr + {p}_dhr;\n"
    )
    if gr_out is not None:
        block += f"{gr_out} = ({range_db}) * {p}_drv;\n"
    if env_out is not None:
        block += f"{env_out} = {p}_env;\n"
    return block


def console_saturation(
    x: str, out: str, drive: str, *, prefix: str = "csat",
) -> str:
    """Asymmetric console/transformer soft-clip with DC blocking (from Console).

    ``tanh(u + 0.12*u^2)`` adds the even-harmonic asymmetry of iron/tube gain
    staging; the squared term injects a DC offset, so a one-pole DC blocker
    (0.995) follows to keep it centred. ``drive`` is 0..18 dB in, with a
    ``-drive*0.45 dB`` makeup so the knob is mostly color. Mono; run per channel
    (use a distinct ``prefix`` per channel). Pairs with :func:`crosstalk` and
    :func:`iron_transformer` for a full large-format channel.
    """
    p = prefix
    return (
        f"History {p}_dcx(0.); History {p}_dcy(0.);\n"
        f"{p}_dg = dbtoa(clamp({drive}, 0., 18.));\n"
        f"{p}_comp = dbtoa(0. - clamp({drive}, 0., 18.) * 0.45);\n"
        f"{p}_u = {x} * {p}_dg * 0.7;\n"
        f"{p}_s = tanh({p}_u + 0.12 * {p}_u * {p}_u);\n"
        f"{p}_y = {p}_s - {p}_dcx + 0.995 * {p}_dcy;\n"
        f"{p}_dcx = {p}_s;\n"
        f"{p}_dcy = {p}_y;\n"
        f"{out} = {p}_y * {p}_comp;\n"
    )


def crosstalk(
    xl: str, xr: str, outl: str, outr: str, *, amount: str, prefix: str = "xtk",
) -> str:
    """Analog channel crosstalk: each channel bleeds a low-weighted copy of the
    OTHER into itself (from Console).

    A 700 Hz one-pole on the opposite channel (bleed is dominated by lows, as in
    real consoles) scaled by ``amount`` (0..100, internally capped at a subtle
    6%). Narrows/glues the stereo image the way summing through shared iron does.
    Mono-in-stereo-out pair. Emits the applied bleed nowhere; tap externally if a
    meter is wanted.
    """
    p = prefix
    return (
        f"History {p}_xl(0.); History {p}_xr(0.);\n"
        f"{p}_xg = clamp({amount}, 0., 100.) * 0.01 * 0.06;\n"
        f"{p}_xk = 1.0 - exp(-{TWO_PI} * 700. / samplerate);\n"
        f"{p}_xl = {p}_xl + {p}_xk * ({xr} - {p}_xl);\n"
        f"{p}_xr = {p}_xr + {p}_xk * ({xl} - {p}_xr);\n"
        f"{outl} = {xl} + {p}_xg * {p}_xl;\n"
        f"{outr} = {xr} + {p}_xg * {p}_xr;\n"
    )


def iron_transformer(
    x: str, out: str, amount: str, *, prefix: str = "iron",
) -> str:
    """Transformer "iron" tone: a low-frequency bump + a gentle top dip, one knob
    (from Console).

    ``amount`` (0..100) adds 40% of a 120 Hz low-pass (the transformer low bump)
    and subtracts 18% of the >9 kHz content (the gentle high-end softening) — the
    weight and roll-off of output iron in a single control. Mono; run per channel.
    """
    p = prefix
    return (
        f"History {p}_lo(0.); History {p}_hi(0.);\n"
        f"{p}_ig = clamp({amount}, 0., 100.) * 0.01;\n"
        f"{p}_lk = 1.0 - exp(-{TWO_PI} * 120. / samplerate);\n"
        f"{p}_hk = 1.0 - exp(-{TWO_PI} * 9000. / samplerate);\n"
        f"{p}_lo = {p}_lo + {p}_lk * ({x} - {p}_lo);\n"
        f"{p}_w = {x} + {p}_ig * 0.4 * {p}_lo;\n"
        f"{p}_hi = {p}_hi + {p}_hk * ({p}_w - {p}_hi);\n"
        f"{out} = {p}_w - {p}_ig * 0.18 * ({p}_w - {p}_hi);\n"
    )


def duck_gain(
    scl: str, scr: str, gain_out: str, *, duck: str, release_ms: str,
    prefix: str = "duck",
) -> str:
    """Sidechain ducking gain: 1.0 when the trigger is quiet, pulled down while
    it is hot (from Ducking Delay).

    An instant-attack / ``release_ms``-decay envelope on the ``scl``/``scr``
    trigger drives a gain that drops by up to ``duck`` (0..100 %) — multiply your
    wet/delay/pad path by ``gain_out`` so it gets out of the way of the dry
    signal (the classic "delay throws bloom in the gaps" move, or general
    sidechain ducking). Reusable with any trigger source; the delay/effect itself
    is separate (see :func:`~m4l_builder.gen_stateful.clickless_delay`).
    """
    p = prefix
    return (
        f"History {p}_env(0.);\n"
        f"{p}_lvl = max(abs({scl}), abs({scr}));\n"
        f"{p}_relk = 1.0 - exp(-1.0 / (0.001 * max({release_ms}, 10.) * samplerate));\n"
        f"{p}_env = {p}_lvl > {p}_env ? {p}_lvl : {p}_env * (1.0 - {p}_relk);\n"
        f"{p}_dk = clamp({duck}, 0., 100.) * 0.01;\n"
        f"{gain_out} = 1.0 - {p}_dk * clamp({p}_env * 3.0, 0., 1.);\n"
    )


def haas_widener(
    xl: str, xr: str, outl: str, outr: str, *, amount_ms: str,
    side: str = "1.", prefix: str = "haas",
) -> str:
    """Haas-effect stereo widener: delay ONE channel a few ms for width (from
    Expansion).

    A sub-15 ms delay on one side makes the ear hear width without changing the
    mono balance much (the precedence/Haas effect). ``amount_ms`` (0..15, 0 =
    bypass) is the delay; ``side`` > 0.5 delays RIGHT, else LEFT. Pairs with
    :func:`~m4l_builder.gen_snippets.ms_width_equal_power` (spread) and
    :func:`~m4l_builder.gen_snippets.mono_below` (keep the bass centred) for a
    full widener. Watch mono-compatibility — deep Haas can hollow the centre in
    mono, so meter correlation alongside it.
    """
    p = prefix
    return (
        f"Delay {p}_d(2400);\n"
        f"{p}_din = {side} > 0.5 ? {xr} : {xl};\n"
        f"{p}_d.write({p}_din);\n"
        f"{p}_wet = {amount_ms} > 0.05 ? "
        f"{p}_d.read(mstosamps(clamp({amount_ms}, 0., 15.)), interp=\"linear\")"
        f" : {p}_din;\n"
        f"{outl} = {side} > 0.5 ? {xl} : {p}_wet;\n"
        f"{outr} = {side} > 0.5 ? {p}_wet : {xr};\n"
    )
