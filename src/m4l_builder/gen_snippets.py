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
