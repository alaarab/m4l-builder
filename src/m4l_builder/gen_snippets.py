"""Composable GenExpr snippet registry.

Reusable, parameterized gen~ DSP fragments that plugins compose into their
GEN_CODE instead of re-deriving the same math inline. Each function returns a
GenExpr source string with caller-chosen variable names, so the same audited
primitive serves every plugin (and a fix lands once).

This is the registry the bigger DSP foundations (oversampling, dynamics,
true-peak, multiband) will grow into; it seeds with the Mid/Side matrix — the
highest-reach foundation, the gate for activating the suite's dead M/S menus.

Convention: every emitted block is a run of ``<lhs> = <expr>;`` statements with
no leading/trailing newline, so a caller splices it between its own lines.
"""

from __future__ import annotations

__all__ = [
    "ms_encode",
    "ms_decode",
    "ms_width",
    "drive_blend",
    "peak_follower",
    "isp_catmull_4x",
    "kweight_coeffs_bs1770",
    "exp_pole",
    "soft_knee_gain_computer",
    "dynamics_band",
    "biquad_df1",
    "rbj_peaking",
    "rbj_shelf",
    "one_pole_coeff",
    "one_pole_lp",
    "one_pole_hp",
    "exciter_harmonics",
]


def ms_encode(left: str, right: str, mid: str, side: str) -> str:
    """Encode L/R -> Mid/Side: ``mid = (L+R)/2``, ``side = (L-R)/2``.

    At unity this is loss-less; pair with :func:`ms_decode` to process the M and
    S channels independently (e.g. per-band EQ or compression in M/S).
    """
    return (
        f"{mid} = ({left} + {right}) * 0.5;\n"
        f"{side} = ({left} - {right}) * 0.5;"
    )


def ms_decode(mid: str, side: str, left: str, right: str) -> str:
    """Decode Mid/Side -> L/R: ``L = M+S``, ``R = M-S`` (inverse of ms_encode)."""
    return (
        f"{left} = {mid} + {side};\n"
        f"{right} = {mid} - {side};"
    )


def ms_width(
    left: str,
    right: str,
    out_left: str,
    out_right: str,
    width: str,
    *,
    mid: str = "mid",
    side: str = "side",
) -> str:
    """Stereo-width via M/S: scale the Side by ``width`` then decode.

    ``width`` is a linear factor variable (0 = mono, 1 = unchanged, up to 2 =
    double-wide). Emits the fused encode -> side-scale -> decode form::

        mid       = (L + R) * 0.5;
        side      = (L - R) * 0.5 * width;
        out_left  = mid + side;
        out_right = mid - side;

    ``mid``/``side`` are the intermediate variable names (override to avoid a
    clash when the primitive is used twice in one codebox).
    """
    return (
        f"{mid} = ({left} + {right}) * 0.5;\n"
        f"{side} = ({left} - {right}) * 0.5 * {width};\n"
        f"{out_left} = {mid} + {side};\n"
        f"{out_right} = {mid} - {side};"
    )


def drive_blend(x: str, out: str, k: str, drive: str) -> str:
    """Soft-clip drive with a clean<->saturated crossfade. Emits::

        out = x + (tanh(x*k)/tanh(k) - x) * drive;

    The ``tanh(x*k)`` shaper is level-matched by ``/tanh(k)`` (so full-scale
    stays unity and the stage adds harmonics without dumping gain), then
    crossfaded against the clean ``x`` by ``drive`` (0..1). At ``drive=0`` the
    block is bit-transparent; at ``drive=1`` it is the normalized soft-clip.
    ``k`` is the pre-gain / curve sharpness (caller computes it, e.g.
    ``1 + drive*5``).
    """
    return f"{out} = {x} + (tanh({x} * {k}) / tanh({k}) - {x}) * {drive};"


def peak_follower(
    peak: str,
    state: str,
    attack_coeff: str,
    release_coeff: str,
    coeff: str = "acoeff",
) -> str:
    """Attack/release peak envelope follower (the dynamics detector core). Emits::

        coeff = peak > state ? attack_coeff : release_coeff;
        state = peak + coeff * (state - peak);

    A one-pole that chases ``peak`` with separate rise/fall rates: when the input
    rises above the envelope it uses ``attack_coeff``, otherwise ``release_coeff``
    (each a per-sample one-pole pole 0..1 — SMALLER = faster). This is the
    detector every compressor / limiter / ducker / de-esser sits on. ``peak`` is
    typically ``max(abs(L), abs(R))``; ``coeff`` names the scratch coefficient var.
    """
    return (
        f"{coeff} = {peak} > {state} ? {attack_coeff} : {release_coeff};\n"
        f"{state} = {peak} + {coeff} * ({state} - {peak});"
    )


def isp_catmull_4x(x: str, h1: str, h2: str, h3: str, out: str, *, ch: str = "l") -> str:
    """4x inter-sample-peak (ISP) estimate for one channel via cubic Catmull-Rom.

    ITU-R BS.1770-style true-peak detection: fit a cubic Catmull-Rom spline
    through the 4-sample window ``h3..h0`` (oldest..newest) and evaluate the
    inter-sample positions ``t = .25/.5/.75`` between ``h2`` and ``h1``; ``out``
    is the max absolute of those three estimates. ~1-sample detector group
    delay. Emits, with ``ch`` the channel suffix used for the scratch vars::

        h0{ch} = {x}; h1{ch} = {h1}; h2{ch} = {h2}; h3{ch} = {h3};
        k{ch}0 = h2{ch};
        k{ch}1 = 0.5 * (h1{ch} - h3{ch});
        k{ch}2 = h3{ch} - 2.5 * h2{ch} + 2.0 * h1{ch} - 0.5 * h0{ch};
        k{ch}3 = 0.5 * (h0{ch} - h3{ch}) + 1.5 * (h2{ch} - h1{ch});
        y{ch}1 = k{ch}0 + 0.25 * (k{ch}1 + 0.25 * (k{ch}2 + 0.25 * k{ch}3));
        y{ch}2 = k{ch}0 + 0.5 * (k{ch}1 + 0.5 * (k{ch}2 + 0.5 * k{ch}3));
        y{ch}3 = k{ch}0 + 0.75 * (k{ch}1 + 0.75 * (k{ch}2 + 0.75 * k{ch}3));
        {out} = max(max(abs(y{ch}1), abs(y{ch}2)), abs(y{ch}3));

    ``x`` is the newest sample; ``h1``/``h2``/``h3`` are the caller's 3 history
    vars (the caller shifts them each sample). Call once per channel (``ch="l"``
    / ``ch="r"``) then take ``tp = max(sp, max(ispl, ispr))``. This is the
    detector behind a provable dBTP limiter / true-peak meter — shared so the
    limiter (Ceiling) and the analyzer (Spectrum Analyzer) stop copy-pasting it.
    """
    return (
        f"h0{ch} = {x}; h1{ch} = {h1}; h2{ch} = {h2}; h3{ch} = {h3};\n"
        f"k{ch}0 = h2{ch};\n"
        f"k{ch}1 = 0.5 * (h1{ch} - h3{ch});\n"
        f"k{ch}2 = h3{ch} - 2.5 * h2{ch} + 2.0 * h1{ch} - 0.5 * h0{ch};\n"
        f"k{ch}3 = 0.5 * (h0{ch} - h3{ch}) + 1.5 * (h2{ch} - h1{ch});\n"
        f"y{ch}1 = k{ch}0 + 0.25 * (k{ch}1 + 0.25 * (k{ch}2 + 0.25 * k{ch}3));\n"
        f"y{ch}2 = k{ch}0 + 0.5 * (k{ch}1 + 0.5 * (k{ch}2 + 0.5 * k{ch}3));\n"
        f"y{ch}3 = k{ch}0 + 0.75 * (k{ch}1 + 0.75 * (k{ch}2 + 0.75 * k{ch}3));\n"
        f"{out} = max(max(abs(y{ch}1), abs(y{ch}2)), abs(y{ch}3));"
    )


def kweight_coeffs_bs1770() -> str:
    """ITU-R BS.1770-4 K-weighting biquad coefficients, computed at the live rate.

    Emits the two-stage K-weight filter coefficients used by every BS.1770
    loudness meter — Stage 1 a +4 dB high-shelf at 1681.97 Hz (Q 0.7072), Stage 2
    an RLB high-pass at 38.135 Hz (Q 0.5003) — bilinear-transformed via ``tan`` at
    the running ``samplerate`` so the meter stays accurate at 44.1 / 48 / 96 kHz
    (the tabulated reference coefficients are 48k-only). Defines the Stage-1 vars
    ``sb0 sb1 sb2 sa1 sa2`` and the Stage-2 vars ``hb0 hb1 hb2 ha1 ha2`` for a
    Direct-Form-I application by the caller, plus the scratch vars
    ``KPI Ks Vh Vb a0s Kh a0h``.

    NOTE: unlike the other snippets this block keeps its two explanatory comments
    — the magic constants (1681.9744509555319, 0.7071752369554193, ...) are
    inscrutable and were carried verbatim from the audited Ceiling / Spectrum
    Analyzer source so the migration is byte-identical. Centralizing them means a
    coefficient fix/audit lands once instead of in every metering plugin.
    """
    return (
        "KPI = 3.14159265358979;\n"
        "// Stage 1 — high-shelf pre-filter (f0 1681.97 Hz, Q 0.70718, +3.9998 dB).\n"
        "Ks = tan(KPI * 1681.9744509555319 / samplerate);\n"
        "Vh = pow(10., 3.99984385397 / 20.);\n"
        "Vb = pow(Vh, 0.499666774155);\n"
        "a0s = 1. + Ks / 0.7071752369554193 + Ks * Ks;\n"
        "sb0 = (Vh + Vb * Ks / 0.7071752369554193 + Ks * Ks) / a0s;\n"
        "sb1 = 2. * (Ks * Ks - Vh) / a0s;\n"
        "sb2 = (Vh - Vb * Ks / 0.7071752369554193 + Ks * Ks) / a0s;\n"
        "sa1 = 2. * (Ks * Ks - 1.) / a0s;\n"
        "sa2 = (1. - Ks / 0.7071752369554193 + Ks * Ks) / a0s;\n"
        "// Stage 2 — RLB high-pass (f0 38.135 Hz, Q 0.50033).\n"
        "Kh = tan(KPI * 38.13547087613982 / samplerate);\n"
        "a0h = 1. + Kh / 0.5003270373253953 + Kh * Kh;\n"
        "hb0 = 1. / a0h;\n"
        "hb1 = -2. / a0h;\n"
        "hb2 = 1. / a0h;\n"
        "ha1 = 2. * (Kh * Kh - 1.) / a0h;\n"
        "ha2 = (1. - Kh / 0.5003270373253953 + Kh * Kh) / a0h;"
    )


def exp_pole(out: str, tau_seconds: str) -> str:
    """One-pole smoothing/ballistics coefficient: ``out = exp(-1/(tau*sr))``. Emits::

        out = exp(-1.0 / (tau_seconds * samplerate));

    The per-sample feedback pole of a one-pole low-pass / envelope follower with
    time constant ``tau_seconds``: pair it with a ``state = x + out*(state - x)``
    update (or peak_follower). SMALLER tau = faster. ``tau_seconds`` is an
    expression in the gen vars — e.g. ``"0.0004"`` for a fixed 0.4 ms smoother or
    ``"atk_ms * 0.001"`` for a millisecond Param. This is the smoothing/ballistics
    coefficient copy-pasted across every dynamics + metering plugin; sharing it
    audits the `exp(-1/(tau*fs))` formula once and is the unit the future
    samplerate-coefficient cache will wrap.
    """
    return f"{out} = exp(-1.0 / ({tau_seconds} * samplerate));"


def soft_knee_gain_computer(
    level: str,
    threshold: str,
    ratio: str,
    knee: str,
    out: str,
    *,
    over: str = "over",
    half_knee: str = "half_knee",
    slope: str = "slope",
    t: str = "t",
) -> str:
    """Soft-knee downward-compression gain computer (the dB gain-reduction curve).

    Given a detector ``level`` (dB), a ``threshold`` (dB), a ``ratio`` (>= 1) and a
    ``knee`` width (dB), emit the gain reduction ``out`` (dB, <= 0). Below the knee
    there is no reduction; within +/- half the knee a quadratic soft transition; above
    it the hard ``over * (1/ratio - 1)`` slope. This is the static compressor/limiter
    curve — pair it with a :func:`peak_follower` (or instant-attack envelope) feeding
    ``level`` and a ``dbtoa(out + makeup)`` applied to the audio. It is the
    gain-computer half of the audio-rate dynamics foundation (the detector half is
    peak_follower) that the dynamic-EQ bands compose. Emits an ``if``/``else if``
    block::

        over = level - threshold;
        half_knee = knee * 0.5;
        slope = (1.0 / max(ratio, 1.0)) - 1.0;
        out = 0.;
        if (over > half_knee) {
            out = over * slope;
        } else if (over > -half_knee && knee > 0.01) {
            t = over + half_knee;
            out = (t * t) / (2.0 * knee) * slope;
        }

    ``over``/``half_knee``/``slope``/``t`` are the scratch var names (override to
    avoid a clash when the primitive is used twice in one codebox).
    """
    return (
        f"{over} = {level} - {threshold};\n"
        f"{half_knee} = {knee} * 0.5;\n"
        f"{slope} = (1.0 / max({ratio}, 1.0)) - 1.0;\n"
        f"{out} = 0.;\n"
        f"if ({over} > {half_knee}) {{\n"
        f"    {out} = {over} * {slope};\n"
        f"}} else if ({over} > -{half_knee} && {knee} > 0.01) {{\n"
        f"    {t} = {over} + {half_knee};\n"
        f"    {out} = ({t} * {t}) / (2.0 * {knee}) * {slope};\n"
        f"}}"
    )


def dynamics_band(
    peak: str,
    env: str,
    attack_coeff: str,
    release_coeff: str,
    threshold: str,
    ratio: str,
    knee: str,
    makeup: str,
    out_gain: str,
    *,
    level: str = "level_db",
    coeff: str = "dcoeff",
    grdb: str = "grdb",
    floor: str = "0.0000316",
) -> str:
    """End-to-end downward-compression gain path: detector -> knee -> makeup.

    Composes the two shipped dynamics primitives into the reusable macro a
    dynamic-EQ band / compressor / limiter applies to one signal:

    1. convert the input ``peak`` (linear, e.g. ``max(abs(L), abs(R))``) to dB,
       floored so silence reads a finite ``-90`` dB instead of ``-inf``;
    2. attack/release envelope-follow in the dB domain (:func:`peak_follower`)
       into the ``env`` History with ``attack_coeff``/``release_coeff`` poles;
    3. soft-knee gain reduction (:func:`soft_knee_gain_computer`) -> ``grdb`` dB;
    4. ``out_gain = dbtoa(grdb + makeup)`` — the linear gain to multiply the
       (optionally delayed) audio by.

    At ``ratio == 1`` and ``makeup == 0`` the whole band is unity (transparent);
    it only ever attenuates relative to the makeup. ``level``/``coeff``/``grdb``
    are scratch var names (override to use the macro twice in one codebox);
    ``floor`` is the linear silence floor fed to ``atodb``. This is the audio-rate
    dynamics foundation the EQ dynamic-bands compose (detector = peak_follower,
    gain computer = soft_knee_gain_computer, both already null-tested).
    """
    return (
        f"{level} = max(atodb(max({peak}, {floor})), -90.);\n"
        + peak_follower(level, env, attack_coeff, release_coeff, coeff) + "\n"
        + soft_knee_gain_computer(env, threshold, ratio, knee, grdb) + "\n"
        + f"{out_gain} = dbtoa({grdb} + {makeup});"
    )


def biquad_df1(
    x: str,
    b0: str, b1: str, b2: str,
    a1: str, a2: str,
    x1: str, x2: str,
    y1: str, y2: str,
    out: str,
) -> str:
    """One Direct-Form-I biquad stage: ``y = b0 x + b1 x1 + b2 x2 - a1 y1 - a2 y2``.

    Applies a normalised biquad (``a0 == 1``) to ``x`` with feed-forward coeffs
    ``b0 b1 b2`` and feedback coeffs ``a1 a2``, using the four History state cells
    ``x1 x2`` (input delays) and ``y1 y2`` (output delays), writing the filtered
    sample to ``out`` and shifting the state. Emits::

        out = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = x; y2 = y1; y1 = out;

    Cascade two stages for the BS.1770 K-weight (shelf then RLB high-pass), and it
    is the apply-block the cascaded-filter foundation builds on. The caller
    declares ``x1 x2 y1 y2`` as History and supplies the coeffs (e.g. from
    :func:`kweight_coeffs_bs1770`). This is the DF-I apply copy-pasted across the
    metering plugins; sharing it audits the recurrence once.
    """
    return (
        f"{out} = {b0} * {x} + {b1} * {x1} + {b2} * {x2} - {a1} * {y1} - {a2} * {y2};\n"
        f"{x2} = {x1}; {x1} = {x}; {y2} = {y1}; {y1} = {out};"
    )


def one_pole_coeff(out: str, freq: str) -> str:
    """Cutoff-frequency one-pole coefficient: ``out = 1 - exp(-2*pi*fc/fs)``. Emits::

        out = 1.0 - exp(-6.28318530717959 * freq / samplerate);

    The per-sample lerp coefficient of a one-pole low-pass with -3 dB corner at
    ``freq`` Hz, computed at the running ``samplerate`` so the corner stays put at
    44.1 / 48 / 96 / 192 kHz. Pair it with :func:`one_pole_lp` / :func:`one_pole_hp`
    (``state = state + coeff*(x - state)``). LARGER coeff (higher freq) = faster /
    brighter; at ``freq`` -> 0 the coeff -> 0 (the filter freezes, output holds).
    This is the ``1 - exp(-2*pi*f/fs)`` form copy-pasted across the saturation /
    tone / exciter plugins (distinct from :func:`exp_pole`'s time-constant
    ``exp(-1/(tau*fs))`` ballistics pole); sharing it audits the corner math once.
    """
    return f"{out} = 1.0 - exp(-6.28318530717959 * {freq} / samplerate);"


def one_pole_lp(x: str, state: str, coeff: str, out: str) -> str:
    """One-pole low-pass: chase ``x`` into the ``state`` History, expose it. Emits::

        state = state + coeff * (x - state);
        out = state;

    A first-order (6 dB/oct) low-pass where ``coeff`` (0..1, from
    :func:`one_pole_coeff`) is the lerp rate: 1 passes ``x`` through, 0 freezes the
    state. ``state`` is the caller's History cell (the filter memory); ``out`` may
    alias ``state``. This is the smoother/tone-LP recurrence shared across the
    saturation + exciter cores (the LP half; :func:`one_pole_hp` is the complement).
    """
    return (
        f"{state} = {state} + {coeff} * ({x} - {state});\n"
        f"{out} = {state};"
    )


def one_pole_hp(x: str, state: str, coeff: str, out: str) -> str:
    """One-pole high-pass via ``x - lowpass(x)``. Emits::

        state = state + coeff * (x - state);
        out = x - state;

    The complement of :func:`one_pole_lp` sharing the same one-pole ``state``: the
    low-passed energy is subtracted from the input, leaving a first-order
    (6 dB/oct) high-pass with corner ``freq`` (via :func:`one_pole_coeff`). At
    ``coeff`` -> 0 the state stays at its init so ``out`` -> ``x`` (all-pass / DC
    retained); at ``coeff`` -> 1 the state tracks ``x`` so ``out`` -> 0. This is the
    pre-saturation low-cut / exciter high-band split shared across the cores.
    """
    return (
        f"{state} = {state} + {coeff} * ({x} - {state});\n"
        f"{out} = {x} - {state};"
    )


def exciter_harmonics(band: str, k: str, even: str, out: str,
                      *, odd: str = "hx_odd", sq: str = "hx_sq") -> str:
    """Generated harmonic content of a band-limited signal (the exciter core). Emits::

        odd = tanh(band * k) / tanh(k);
        sq = band * band;
        out = (odd - band) + even * sq;

    A harmonic exciter ADDS upper harmonics of a filtered band back to the dry
    signal (Aphex Aural Exciter / Ozone Exciter), and ``out`` is exactly that ADDED
    content (the delta, not the wet band):

    * ``odd - band`` — a level-matched ``tanh`` shaper (``tanh(x*k)/tanh(k)``)
      minus its input, i.e. the ODD harmonics it generated (symmetric, "clear"
      air). ``k`` (>= 1) is the drive / harmonic density; bigger = brighter.
    * ``even * sq`` — a squarer (``band^2``) scaled by ``even`` (0..1), the EVEN
      harmonics (2nd, "warm" tube colour). ``band^2`` carries DC, so the CALLER
      DC-blocks ``out`` before mixing (the exciter sums it into the dry path).

    At ``band == 0`` -> ``out == 0`` (silence in, silence added). The caller scales
    ``out`` by a per-band amount and adds it to dry, so amount 0 is a perfect null.
    ``odd``/``sq`` are scratch var names (override to use the macro twice — e.g. a
    LOW and a HIGH band — in one codebox).
    """
    return (
        f"{odd} = tanh({band} * {k}) / tanh({k});\n"
        f"{sq} = {band} * {band};\n"
        f"{out} = ({odd} - {band}) + {even} * {sq};"
    )


def rbj_peaking(
    freq: str,
    q: str,
    gain_db: str,
    b0: str, b1: str, b2: str,
    a1: str, a2: str,
    *,
    A: str = "A", w0: str = "w0", cw: str = "cw", alpha: str = "alpha", a0: str = "a0",
) -> str:
    """Runtime RBJ peaking-EQ biquad coefficients (Audio-EQ-Cookbook, a0-normalised).

    Computes the Direct-Form-I coefficients ``b0 b1 b2 a1 a2`` for a peaking
    (bell) EQ band from ``freq`` (Hz), ``q``, and ``gain_db``, at the running
    ``samplerate`` — so the band is tunable LIVE (unlike the build-time-baked
    ``_biquad_shelf`` or the ``filtercoeff~`` object path). Pair with
    :func:`biquad_df1` to apply it. Emits::

        A = pow(10., gain_db / 40.);
        w0 = 2 * pi * freq / samplerate;
        cw = cos(w0);  alpha = sin(w0) / (2 * q);
        a0 = 1 + alpha / A;
        b0 = (1 + alpha * A) / a0;   b1 = (-2 * cw) / a0;   b2 = (1 - alpha * A) / a0;
        a1 = (-2 * cw) / a0;         a2 = (1 - alpha / A) / a0;

    At ``gain_db == 0`` the b coeffs equal the a coeffs -> unity (flat); the band
    is unity at DC and Nyquist for any gain. This is the runtime peaking-band
    coefficient half of the cascaded-filter foundation (the apply half is
    :func:`biquad_df1`). ``A w0 cw alpha a0`` are scratch var names (override to
    use the primitive twice in one codebox).
    """
    return (
        f"{A} = pow(10., {gain_db} / 40.);\n"
        f"{w0} = 2. * 3.14159265358979 * {freq} / samplerate;\n"
        f"{cw} = cos({w0});\n"
        f"{alpha} = sin({w0}) / (2. * {q});\n"
        f"{a0} = 1. + {alpha} / {A};\n"
        f"{b0} = (1. + {alpha} * {A}) / {a0};\n"
        f"{b1} = (-2. * {cw}) / {a0};\n"
        f"{b2} = (1. - {alpha} * {A}) / {a0};\n"
        f"{a1} = (-2. * {cw}) / {a0};\n"
        f"{a2} = (1. - {alpha} / {A}) / {a0};"
    )


def rbj_shelf(
    freq: str,
    gain_db: str,
    kind: str,
    b0: str, b1: str, b2: str,
    a1: str, a2: str,
    *,
    A: str = "A", w0: str = "w0", cw: str = "cw", alpha: str = "alpha",
    a0: str = "a0", sqA: str = "sqA", tsa: str = "tsa",
) -> str:
    """Runtime RBJ low/high-shelf biquad coefficients (Butterworth slope, S=1).

    ``kind`` is ``"low"`` or ``"high"``. Computes the Direct-Form-I shelf
    coefficients ``b0 b1 b2 a1 a2`` from ``freq`` (Hz) and ``gain_db`` at the
    running ``samplerate`` (tunable LIVE), matching the build-time ``_biquad_shelf``
    math (alpha uses the Butterworth shelf slope ``1/S = sqrt(2)``). Pair with
    :func:`biquad_df1` to apply it.

    A low-shelf boosts/cuts DC by ``gain_db`` and is unity at Nyquist; a high-shelf
    is the inverse. At ``gain_db == 0`` (A == 1) the b coeffs equal the a coeffs ->
    flat. This is the shelf half of the runtime EQ-band coefficient set (peaking is
    :func:`rbj_peaking`). ``A w0 cw alpha a0 sqA tsa`` are scratch var names.
    """
    if kind not in ("low", "high"):
        raise ValueError(f"rbj_shelf kind must be 'low' or 'high', got {kind!r}")
    if kind == "low":
        b0e = f"{A} * (({A} + 1.) - ({A} - 1.) * {cw} + {tsa})"
        b1e = f"2. * {A} * (({A} - 1.) - ({A} + 1.) * {cw})"
        b2e = f"{A} * (({A} + 1.) - ({A} - 1.) * {cw} - {tsa})"
        a0e = f"({A} + 1.) + ({A} - 1.) * {cw} + {tsa}"
        a1e = f"-2. * (({A} - 1.) + ({A} + 1.) * {cw})"
        a2e = f"({A} + 1.) + ({A} - 1.) * {cw} - {tsa}"
    else:  # high
        b0e = f"{A} * (({A} + 1.) + ({A} - 1.) * {cw} + {tsa})"
        b1e = f"-2. * {A} * (({A} - 1.) + ({A} + 1.) * {cw})"
        b2e = f"{A} * (({A} + 1.) + ({A} - 1.) * {cw} - {tsa})"
        a0e = f"({A} + 1.) - ({A} - 1.) * {cw} + {tsa}"
        a1e = f"2. * (({A} - 1.) - ({A} + 1.) * {cw})"
        a2e = f"({A} + 1.) - ({A} - 1.) * {cw} - {tsa}"
    return (
        f"{A} = pow(10., {gain_db} / 40.);\n"
        f"{w0} = 2. * 3.14159265358979 * {freq} / samplerate;\n"
        f"{cw} = cos({w0});\n"
        f"{alpha} = sin({w0}) / 2. * sqrt(({A} + 1. / {A}) * (1.4142135623730951 - 1.) + 2.);\n"
        f"{sqA} = sqrt({A});\n"
        f"{tsa} = 2. * {sqA} * {alpha};\n"
        f"{a0} = {a0e};\n"
        f"{b0} = ({b0e}) / {a0};\n"
        f"{b1} = ({b1e}) / {a0};\n"
        f"{b2} = ({b2e}) / {a0};\n"
        f"{a1} = ({a1e}) / {a0};\n"
        f"{a2} = ({a2e}) / {a0};"
    )
