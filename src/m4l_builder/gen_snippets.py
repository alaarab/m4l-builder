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

__all__ = ["ms_encode", "ms_decode", "ms_width", "drive_blend", "peak_follower"]


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
