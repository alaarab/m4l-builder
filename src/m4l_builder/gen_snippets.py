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

import math

__all__ = [
    "ms_encode",
    "ms_decode",
    "ms_width",
    "drive_blend",
    "tanh_adaa",
    "hardclip_adaa",
    "peak_follower",
    "isp_catmull_4x",
    "kweight_coeffs_bs1770",
    "exp_pole",
    "soft_knee_gain_computer",
    "dynamics_band",
    "biquad_df1",
    "rbj_peaking",
    "rbj_shelf",
    "rbj_lowpass",
    "rbj_highpass",
    "butterworth_q_table",
    "biquad_cascade",
    "tilt_shelf",
    "lr_crossover",
    "multiband_split",
    "tpt_svf",
    "lfo",
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


def tanh_adaa(
    x: str,
    out: str,
    xprev: str,
    *,
    ax: str = "adaa_ax", axp: str = "adaa_axp",
    fx: str = "adaa_fx", fxp: str = "adaa_fxp", dx: str = "adaa_dx",
) -> str:
    """First-order antiderivative-anti-aliased (ADAA) tanh saturation.

    A drop-in for ``tanh(x)`` that SUPPRESSES the aliasing a naive per-sample
    waveshaper folds back into the audio band — the transparency move every
    flagship saturator/clipper makes (FabFilter Saturn, Pro-C/Pro-L soft-clip)
    but WITHOUT oversampling. Instead of sampling ``f(x)=tanh(x)`` it uses the
    average of ``f`` over each sample step via the antiderivative
    ``F(x)=ln(cosh(x))`` (Parker/Bilbao 2016)::

        adaa_dx = x - xprev;
        out = abs(adaa_dx) > 0.00001
            ? (F(x) - F(xprev)) / adaa_dx       # mean of tanh over [xprev, x]
            : tanh(0.5 * (x + xprev));           # |dx|->0 limit (avoids 0/0)
        xprev = x;

    ``F`` is evaluated in the overflow-stable form ``|x| + log(1 + exp(-2|x|)) -
    ln2`` (no ``cosh`` blow-up at high drive). Output is bounded in ``[-1, 1]``
    (a mean of ``tanh`` values) and matches ``tanh`` for slow signals; it adds a
    constant 0.5-sample group delay (1st-order ADAA). ``xprev`` is the caller's
    1-sample state (declare ``History {xprev}(0.);``). Scale ``x`` by a drive
    pre-gain and level-match at the call site (as :func:`drive_blend` does);
    ``ax axp fx fxp dx`` are scratch var names (override to place several in one
    codebox). The anti-aliased upgrade path for Heat/Ceiling/Pressure/Echotide.
    """
    ln2 = "0.6931471805599453"
    return "\n".join([
        f"{ax} = abs({x});",
        f"{fx} = {ax} + log(1. + exp(-2. * {ax})) - {ln2};",
        f"{axp} = abs({xprev});",
        f"{fxp} = {axp} + log(1. + exp(-2. * {axp})) - {ln2};",
        f"{dx} = {x} - {xprev};",
        f"{out} = abs({dx}) > 0.00001 ? "
        f"({fx} - {fxp}) / {dx} : tanh(0.5 * ({x} + {xprev}));",
        f"{xprev} = {x};",
    ])


def hardclip_adaa(
    x: str,
    out: str,
    xprev: str,
    *,
    ax: str = "hca_ax", axp: str = "hca_axp",
    fx: str = "hca_fx", fxp: str = "hca_fxp", dx: str = "hca_dx", mid: str = "hca_mid",
) -> str:
    """First-order antiderivative-anti-aliased HARD clipper (clamp at +/-1).

    The brickwall counterpart to :func:`tanh_adaa`: a ``clamp(x, -1, 1)`` clipper
    that SUPPRESSES the aliasing a naive per-sample clipper folds back into the
    band — the loudness-clipper move (Pro-L 2 / Ableton Soft Clip / Ozone
    clipper / mastering clip) without oversampling. Unlike a soft tanh, a clipper
    is TRANSPARENT below the ceiling (no level loss on already-quiet signal), so
    it is the right shape for a true-peak limiter's clip stage. Uses the mean of
    ``f(x)=clamp(x,-1,1)`` over each sample step via its antiderivative
    ``F(x) = |x|<=1 ? x^2/2 : |x| - 1/2`` (Parker/Bilbao 1st-order ADAA)::

        hca_dx = x - xprev;
        out = abs(hca_dx) > 0.00001
            ? (F(x) - F(xprev)) / hca_dx        # mean of clamp over [xprev, x]
            : clamp(0.5*(x + xprev), -1., 1.);   # |dx|->0 limit (avoids 0/0)
        xprev = x;

    Output is bounded in ``[-1, 1]`` (a mean of clamp values) and equals the input
    (modulo a 0.5-sample average) while ``|x| <= 1``; scale ``x`` by a drive
    pre-gain and the result by its inverse at the call site to set the clip
    ceiling. Arithmetic + ``clamp`` only (no log/exp) — fully gen_sim-verifiable.
    ``xprev`` is the caller's 1-sample state (declare ``History {xprev}(0.);``);
    ``ax axp fx fxp dx mid`` are scratch var names. Adds a constant 0.5-sample
    group delay. The clip half of the anti-aliased-shaper set (soft = tanh_adaa).
    """
    return "\n".join([
        f"{ax} = abs({x});",
        f"{fx} = {ax} <= 1. ? {x} * {x} * 0.5 : {ax} - 0.5;",
        f"{axp} = abs({xprev});",
        f"{fxp} = {axp} <= 1. ? {xprev} * {xprev} * 0.5 : {axp} - 0.5;",
        f"{dx} = {x} - {xprev};",
        f"{mid} = 0.5 * ({x} + {xprev});",
        f"{out} = abs({dx}) > 0.00001 ? "
        f"({fx} - {fxp}) / {dx} : clamp({mid}, -1., 1.);",
        f"{xprev} = {x};",
    ])


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


def rbj_lowpass(
    freq: str,
    q: str,
    b0: str, b1: str, b2: str,
    a1: str, a2: str,
    *,
    w0: str = "w0", cw: str = "cw", alpha: str = "alpha", a0: str = "a0",
) -> str:
    """Runtime RBJ low-pass biquad coefficients (Audio-EQ-Cookbook, a0-normalised).

    Computes the Direct-Form-I coefficients ``b0 b1 b2 a1 a2`` for a 2nd-order
    (12 dB/oct) low-pass at cutoff ``freq`` (Hz) and resonance ``q``, at the
    running ``samplerate`` (tunable LIVE). Pair with :func:`biquad_df1` to apply
    it. Emits::

        w0 = 2 * pi * freq / samplerate;  cw = cos(w0);  alpha = sin(w0) / (2 * q);
        a0 = 1 + alpha;
        b0 = ((1 - cw) / 2) / a0;  b1 = (1 - cw) / a0;  b2 = ((1 - cw) / 2) / a0;
        a1 = (-2 * cw) / a0;       a2 = (1 - alpha) / a0;

    Unity gain at DC, zero at Nyquist; ``q = 0.70710678`` gives a maximally-flat
    (Butterworth) -3.01 dB corner at ``freq``. Cascade staggered-Q stages
    (:func:`butterworth_q_table` / :func:`biquad_cascade`) for variable slope.
    The complement is :func:`rbj_highpass`. ``w0 cw alpha a0`` are scratch var
    names (override to use the primitive twice in one codebox).
    """
    return (
        f"{w0} = 2. * 3.14159265358979 * {freq} / samplerate;\n"
        f"{cw} = cos({w0});\n"
        f"{alpha} = sin({w0}) / (2. * {q});\n"
        f"{a0} = 1. + {alpha};\n"
        f"{b0} = ((1. - {cw}) / 2.) / {a0};\n"
        f"{b1} = (1. - {cw}) / {a0};\n"
        f"{b2} = ((1. - {cw}) / 2.) / {a0};\n"
        f"{a1} = (-2. * {cw}) / {a0};\n"
        f"{a2} = (1. - {alpha}) / {a0};"
    )


def rbj_highpass(
    freq: str,
    q: str,
    b0: str, b1: str, b2: str,
    a1: str, a2: str,
    *,
    w0: str = "w0", cw: str = "cw", alpha: str = "alpha", a0: str = "a0",
) -> str:
    """Runtime RBJ high-pass biquad coefficients (Audio-EQ-Cookbook, a0-normalised).

    The complement of :func:`rbj_lowpass`: a 2nd-order (12 dB/oct) high-pass at
    cutoff ``freq`` (Hz), resonance ``q``, at the running ``samplerate``. Pair
    with :func:`biquad_df1`. Emits the same ``w0 cw alpha a0`` and feedback
    coeffs as the low-pass, with high-pass numerators::

        b0 = ((1 + cw) / 2) / a0;  b1 = (-(1 + cw)) / a0;  b2 = ((1 + cw) / 2) / a0;
        a1 = (-2 * cw) / a0;        a2 = (1 - alpha) / a0;

    Zero gain at DC, unity at Nyquist; ``q = 0.70710678`` is the Butterworth
    -3.01 dB corner. Cascade staggered-Q stages via :func:`biquad_cascade` for
    variable slope. ``w0 cw alpha a0`` are scratch var names.
    """
    return (
        f"{w0} = 2. * 3.14159265358979 * {freq} / samplerate;\n"
        f"{cw} = cos({w0});\n"
        f"{alpha} = sin({w0}) / (2. * {q});\n"
        f"{a0} = 1. + {alpha};\n"
        f"{b0} = ((1. + {cw}) / 2.) / {a0};\n"
        f"{b1} = (-(1. + {cw})) / {a0};\n"
        f"{b2} = ((1. + {cw}) / 2.) / {a0};\n"
        f"{a1} = (-2. * {cw}) / {a0};\n"
        f"{a2} = (1. - {alpha}) / {a0};"
    )


def butterworth_q_table(order: int) -> list[float]:
    """Per-stage resonance Q values for an even-order Butterworth filter.

    Returns ``order // 2`` Q values for realising an order-``order`` Butterworth
    low/high-pass as a cascade of 2nd-order sections: stage ``k`` (1-indexed) has
    ``Q_k = 1 / (2 * cos((2k - 1) * pi / (2 * order)))``. A cascade of
    :func:`rbj_lowpass` / :func:`rbj_highpass` biquads at these staggered Qs is a
    maximally-flat Butterworth of the given order (``order * 6`` dB/oct slope),
    exactly -3.01 dB at the cutoff for any order.

    Examples: ``order 2 -> [0.7071]``; ``order 4 -> [0.5412, 1.3066]``;
    ``order 8 -> [0.5098, 0.6013, 0.9000, 2.5629]``. ``order`` must be even and
    >= 2 (slopes 12, 24, 36, ... dB/oct; up to order 16 = 96 dB/oct).
    """
    if order < 2 or order % 2 != 0:
        raise ValueError(
            f"butterworth_q_table order must be even and >= 2, got {order}"
        )
    return [
        1.0 / (2.0 * math.cos((2 * k - 1) * math.pi / (2 * order)))
        for k in range(1, order // 2 + 1)
    ]


def biquad_cascade(
    x: str,
    out: str,
    freq: str,
    kind: str,
    order: int,
    *,
    prefix: str = "cas",
) -> str:
    """Variable-slope Butterworth low/high-pass as cascaded biquads (self-contained).

    Chains ``order // 2`` :func:`biquad_df1` stages, each an :func:`rbj_lowpass`
    (``kind="low"``) or :func:`rbj_highpass` (``kind="high"``) at the
    Butterworth-staggered Q from :func:`butterworth_q_table`, from input ``x`` to
    output ``out``, all sharing the one runtime cutoff ``freq`` (Hz). The result
    is a maximally-flat ``order``-th-order filter: ``order * 6`` dB/oct slope
    (e.g. ``order=4`` = 24 dB/oct, ``order=16`` = 96 dB/oct), -3.01 dB at ``freq``.

    SELF-CONTAINED: emits its own ``History`` state declarations (4 cells per
    stage, named ``{prefix}{i}_x1/_x2/_y1/_y2``) plus per-stage scratch coeff vars,
    so the caller just splices the returned block into its codebox. ``order`` must
    be even and >= 2. ``prefix`` namespaces all generated vars (override to use
    more than one cascade in a single codebox).
    """
    if kind not in ("low", "high"):
        raise ValueError(f"biquad_cascade kind must be 'low' or 'high', got {kind!r}")
    qs = butterworth_q_table(order)  # validates even / >= 2
    coeff_fn = rbj_lowpass if kind == "low" else rbj_highpass
    n = len(qs)
    decls = []
    body = []
    for i, q in enumerate(qs):
        p = f"{prefix}{i}"
        stage_in = x if i == 0 else f"{prefix}{i - 1}_y"
        stage_out = out if i == n - 1 else f"{p}_y"
        decls.append(
            f"History {p}_x1(0.); History {p}_x2(0.); "
            f"History {p}_y1(0.); History {p}_y2(0.);"
        )
        body.append(
            coeff_fn(
                freq, f"{q:.12g}",
                f"{p}_b0", f"{p}_b1", f"{p}_b2", f"{p}_a1", f"{p}_a2",
                w0=f"{p}_w0", cw=f"{p}_cw", alpha=f"{p}_al", a0=f"{p}_a0",
            )
        )
        body.append(
            biquad_df1(
                stage_in, f"{p}_b0", f"{p}_b1", f"{p}_b2", f"{p}_a1", f"{p}_a2",
                f"{p}_x1", f"{p}_x2", f"{p}_y1", f"{p}_y2", stage_out,
            )
        )
    return "\n".join(decls) + "\n" + "\n".join(body)


def tilt_shelf(
    x: str,
    out: str,
    freq: str,
    tilt_db: str,
    *,
    prefix: str = "tilt",
) -> str:
    """Constant-slope spectral TILT around a pivot frequency (self-contained).

    A tilt EQ pivots the whole spectrum about ``freq``: positive ``tilt_db``
    CUTS everything below ``freq`` and BOOSTS everything above it (the mastering
    "tilt"/"tone" control — Tonelux/Niveau, FabFilter Pro-Q's tilt-shelf shape).
    Built as a complementary shelf pair on the shared runtime :func:`rbj_shelf` +
    :func:`biquad_df1`: a LOW-shelf at ``-tilt_db`` in series with a HIGH-shelf at
    ``+tilt_db``, both at cutoff ``freq``. Asymptotes: ``-tilt_db`` at DC,
    ``+tilt_db`` at Nyquist (a ``2 * tilt_db`` total spread), and ~0 dB at the
    pivot (the two shelves cross). ``tilt_db == 0`` is flat (each shelf unity), so
    a hosted Tilt control is transparent at center.

    SELF-CONTAINED: emits its own ``History`` state (two biquads = 8 cells, named
    ``{prefix}_lo_*`` / ``{prefix}_hi_*``) plus per-stage scratch coeff vars and
    one intermediate signal ``{prefix}_mid``, so the caller just splices the block
    in. ``freq`` and ``tilt_db`` are gen expressions (var names or literals), both
    tunable LIVE. ``prefix`` namespaces all generated vars (override for more than
    one tilt in a codebox). Gives both EQs the "audio tilt" feature and any tone
    stage a one-knob spectral tilt — the last piece of the cascaded-filter layer.
    """
    lo, hi = f"{prefix}_lo", f"{prefix}_hi"
    mid = f"{prefix}_mid"
    decls = (
        f"History {lo}_x1(0.); History {lo}_x2(0.); "
        f"History {lo}_y1(0.); History {lo}_y2(0.);\n"
        f"History {hi}_x1(0.); History {hi}_x2(0.); "
        f"History {hi}_y1(0.); History {hi}_y2(0.);"
    )
    coeff_lo = rbj_shelf(
        freq, f"-1. * ({tilt_db})", "low",
        f"{lo}_b0", f"{lo}_b1", f"{lo}_b2", f"{lo}_a1", f"{lo}_a2",
        A=f"{lo}_A", w0=f"{lo}_w0", cw=f"{lo}_cw", alpha=f"{lo}_al",
        a0=f"{lo}_a0", sqA=f"{lo}_sqA", tsa=f"{lo}_tsa",
    )
    apply_lo = biquad_df1(
        x, f"{lo}_b0", f"{lo}_b1", f"{lo}_b2", f"{lo}_a1", f"{lo}_a2",
        f"{lo}_x1", f"{lo}_x2", f"{lo}_y1", f"{lo}_y2", mid,
    )
    coeff_hi = rbj_shelf(
        freq, f"{tilt_db}", "high",
        f"{hi}_b0", f"{hi}_b1", f"{hi}_b2", f"{hi}_a1", f"{hi}_a2",
        A=f"{hi}_A", w0=f"{hi}_w0", cw=f"{hi}_cw", alpha=f"{hi}_al",
        a0=f"{hi}_a0", sqA=f"{hi}_sqA", tsa=f"{hi}_tsa",
    )
    apply_hi = biquad_df1(
        mid, f"{hi}_b0", f"{hi}_b1", f"{hi}_b2", f"{hi}_a1", f"{hi}_a2",
        f"{hi}_x1", f"{hi}_x2", f"{hi}_y1", f"{hi}_y2", out,
    )
    return "\n".join([decls, coeff_lo, apply_lo, coeff_hi, apply_hi])


def lr_crossover(
    x: str,
    lo_out: str,
    hi_out: str,
    freq: str,
    order: int,
    *,
    prefix: str = "xo",
) -> str:
    """Linkwitz-Riley complementary crossover split (self-contained).

    Splits ``x`` into a LOW band (``lo_out``) and a HIGH band (``hi_out``) at the
    runtime cutoff ``freq`` (Hz) with an LR filter of ``order`` — a positive
    multiple of 4 (``4`` = LR4 24 dB/oct, ``8`` = LR8 48 dB/oct, ``12`` = 72,
    ``16`` = 96). Each band is a Butterworth filter of order ``order // 2`` applied
    TWICE (the Linkwitz-Riley = Butterworth-squared construction), so the two
    bands stay in phase and **sum to a flat (allpass) magnitude**: ``lo_out +
    hi_out`` reconstructs the input with no peak or notch at the crossover (each
    band is exactly -6 dB at ``freq``). Split repeatedly for an N-band multiband
    bank whose bands recombine flat.

    SELF-CONTAINED: emits its own ``History`` state (``order`` biquads total,
    ``order // 2`` per band, 4 cells each) and per-stage scratch coeffs, so the
    caller just splices the block in. ``order`` MUST be a positive multiple of 4
    — odd/lower LR orders (e.g. LR2) are 180 deg out of phase at the crossover and
    notch instead of summing flat, so they are rejected. ``prefix`` namespaces all
    generated vars (override to place more than one crossover in a codebox).
    """
    if order < 4 or order % 4 != 0:
        raise ValueError(
            f"lr_crossover order must be a positive multiple of 4 (LR4/LR8/...), got {order}"
        )
    # LR = Butterworth-(order/2) applied twice; order//2 is even so the table accepts it.
    qs = butterworth_q_table(order // 2) * 2
    decls = []
    body = []
    for coeff_fn, out_var, tag in ((rbj_lowpass, lo_out, "lo"),
                                   (rbj_highpass, hi_out, "hi")):
        n = len(qs)
        for i, q in enumerate(qs):
            p = f"{prefix}_{tag}{i}"
            stage_in = x if i == 0 else f"{prefix}_{tag}{i - 1}_y"
            stage_out = out_var if i == n - 1 else f"{p}_y"
            decls.append(
                f"History {p}_x1(0.); History {p}_x2(0.); "
                f"History {p}_y1(0.); History {p}_y2(0.);"
            )
            body.append(
                coeff_fn(
                    freq, f"{q:.12g}",
                    f"{p}_b0", f"{p}_b1", f"{p}_b2", f"{p}_a1", f"{p}_a2",
                    w0=f"{p}_w0", cw=f"{p}_cw", alpha=f"{p}_al", a0=f"{p}_a0",
                )
            )
            body.append(
                biquad_df1(
                    stage_in, f"{p}_b0", f"{p}_b1", f"{p}_b2", f"{p}_a1", f"{p}_a2",
                    f"{p}_x1", f"{p}_x2", f"{p}_y1", f"{p}_y2", stage_out,
                )
            )
    return "\n".join(decls) + "\n" + "\n".join(body)


def multiband_split(x: str, band_outs: list, freqs: list, order: int = 4,
                    *, prefix: str = "mb") -> str:
    """Flat-reconstructing N-band Linkwitz-Riley split (allpass-compensated).

    Splits ``x`` into ``len(freqs) + 1`` frequency bands at the ascending
    crossover cutoffs ``freqs`` (var names or literals), writing band signals
    low->high into the ``band_outs`` var names. Built from :func:`lr_crossover`
    on a split-the-high tree, with the key correction that makes a multiband
    bank usable on a flagship: each lower band is ALLPASS-COMPENSATED for every
    higher crossover it skipped (run through that crossover and re-summed, since
    an LR crossover's ``lo + hi`` is an allpass). Without this the bands sum with
    audible ripple at the lower crossovers; WITH it the bands recombine to a
    perfectly FLAT magnitude — ``sum(band_outs)`` reconstructs the input
    (allpass overall), so the band processors can be transparent at unity.

    ``order`` is the LR order (a multiple of 4: 4 = 24 dB/oct, 8 = 48; see
    :func:`lr_crossover`). SELF-CONTAINED: emits all the ``History`` state for
    every internal crossover. ``prefix`` namespaces all generated vars. Needs at
    least one crossover (2 bands); ``len(band_outs)`` must equal
    ``len(freqs) + 1``.
    """
    n_bands = len(freqs) + 1
    if len(freqs) < 1:
        raise ValueError("multiband_split needs at least 1 crossover frequency (2 bands)")
    if len(band_outs) != n_bands:
        raise ValueError(
            f"multiband_split needs {n_bands} band_outs for {len(freqs)} crossover(s), "
            f"got {len(band_outs)}"
        )
    parts = []
    raw_lows = []          # (band_index, low_var)
    hchain = x             # the running high-band signal (the HP cascade)
    for i, f in enumerate(freqs):
        is_last = i == len(freqs) - 1
        lo_var = f"{prefix}_lo{i}"
        hi_var = band_outs[n_bands - 1] if is_last else f"{prefix}_hi{i}"
        parts.append(lr_crossover(hchain, lo_var, hi_var, f, order,
                                  prefix=f"{prefix}_s{i}"))
        raw_lows.append((i, lo_var))
        hchain = hi_var
    # band n_bands-1 (the top) is already the last split's high; compensate lows.
    for i, lo_var in raw_lows:
        comps = freqs[i + 1:]     # higher crossovers this band skipped
        sig = lo_var
        if not comps:
            parts.append(f"{band_outs[i]} = {sig};")
            continue
        for k, cf in enumerate(comps):
            last = k == len(comps) - 1
            c_lo, c_hi = f"{prefix}_c{i}_{k}lo", f"{prefix}_c{i}_{k}hi"
            out_var = band_outs[i] if last else f"{prefix}_c{i}_{k}o"
            parts.append(lr_crossover(sig, c_lo, c_hi, cf, order,
                                      prefix=f"{prefix}_c{i}_{k}"))
            parts.append(f"{out_var} = {c_lo} + {c_hi};")
            sig = out_var
    return "\n".join(parts)


def tpt_svf(
    x: str,
    freq: str,
    q: str,
    lp: str, bp: str, hp: str, notch: str,
    ic1: str, ic2: str,
    *,
    g: str = "g", k: str = "k", a1: str = "a1", a2: str = "a2", a3: str = "a3",
    v1: str = "v1", v2: str = "v2", v3: str = "v3",
) -> str:
    """Zero-delay-feedback / TPT state-variable filter (Zavalishin).

    A single 2nd-order structure that yields the four classic responses at once
    from input ``x`` at runtime cutoff ``freq`` (Hz) and resonance ``q``: writes
    ``lp`` (low-pass), ``bp`` (band-pass), ``hp`` (high-pass) and ``notch``. This
    is the MODULATION-FRIENDLY resonant filter — the bilinear/topology-preserving
    transform makes it stable and zipper-free under fast cutoff/Q sweeps (where a
    static biquad zippers), and it is the gen-domain workaround for Live 12's
    silent ``svf~``. Emits::

        g = tan(pi * freq / samplerate);  k = 1 / q;
        a1 = 1/(1 + g*(g+k));  a2 = g*a1;  a3 = g*a2;
        v3 = x - ic2;  v1 = a1*ic1 + a2*v3;  v2 = ic2 + a2*ic1 + a3*v3;
        ic1 = 2*v1 - ic1;  ic2 = 2*v2 - ic2;          # trapezoidal integrators
        lp = v2;  bp = v1;  hp = x - k*v1 - v2;  notch = x - k*v1;

    At ``q = 0.70710678`` it is a Butterworth corner (all three of LP/BP/HP are
    -3 dB at ``freq``, notch is a deep null there); higher ``q`` resonates. The
    identity ``notch == lp + hp`` holds. ``ic1 ic2`` are the caller's two History
    integrator states (declare ``History {ic1}(0.); History {ic2}(0.);``); the
    other names are per-sample scratch (override to place several SVFs in one
    codebox).
    """
    return (
        f"{g} = tan(3.14159265358979 * {freq} / samplerate);\n"
        f"{k} = 1. / {q};\n"
        f"{a1} = 1. / (1. + {g} * ({g} + {k}));\n"
        f"{a2} = {g} * {a1};\n"
        f"{a3} = {g} * {a2};\n"
        f"{v3} = {x} - {ic2};\n"
        f"{v1} = {a1} * {ic1} + {a2} * {v3};\n"
        f"{v2} = {ic2} + {a2} * {ic1} + {a3} * {v3};\n"
        f"{ic1} = 2. * {v1} - {ic1};\n"
        f"{ic2} = 2. * {v2} - {ic2};\n"
        f"{lp} = {v2};\n"
        f"{bp} = {v1};\n"
        f"{hp} = {x} - {k} * {v1} - {v2};\n"
        f"{notch} = {x} - {k} * {v1};"
    )


def lfo(
    out: str,
    rate: str,
    shape: str,
    phase: str,
    *,
    sq: str = "lfo_sq", tri: str = "lfo_tri", saw: str = "lfo_saw", sn: str = "lfo_sn",
) -> str:
    """In-gen low-frequency oscillator (phase accumulator -> selectable shape).

    A bipolar (-1..1) LFO at runtime ``rate`` (Hz) for modulating gen parameters
    INSIDE a codebox — filter-sweep / auto-wah cutoff (pair with :func:`tpt_svf`),
    tape wobble, tremolo, drive movement — without leaving gen for a ``cycle~``.
    ``shape``: 0 = sine, 1 = triangle, 2 = saw (rising), 3 = square. Emits::

        phase = phase + rate / samplerate;
        phase = phase >= 1. ? phase - 1. : phase;     # wrap 0..1
        sq  = phase < 0.5 ? 1. : -1.;
        tri = 1. - 4. * abs(phase - 0.5);             # -1 at 0/1, +1 at 0.5
        saw = 2. * phase - 1.;
        sn  = sin(2 * pi * phase);
        out = shape==1 ? tri : (shape==2 ? saw : (shape==3 ? sq : sn));

    ``phase`` is the caller's History cell (declare ``History {phase}(0.);``).
    Single-subtract wrap is exact for LFO rates (rate << samplerate). Scale/offset
    ``out`` at the call site to map the -1..1 swing onto a target range. ``sq tri
    saw sn`` are scratch names (override to place several LFOs in one codebox).
    """
    return (
        f"{phase} = {phase} + {rate} / samplerate;\n"
        f"{phase} = {phase} >= 1. ? {phase} - 1. : {phase};\n"
        f"{sq} = {phase} < 0.5 ? 1. : -1.;\n"
        f"{tri} = 1. - 4. * abs({phase} - 0.5);\n"
        f"{saw} = 2. * {phase} - 1.;\n"
        f"{sn} = sin(6.28318530717959 * {phase});\n"
        f"{out} = {shape} == 1 ? {tri} : "
        f"({shape} == 2 ? {saw} : ({shape} == 3 ? {sq} : {sn}));"
    )
