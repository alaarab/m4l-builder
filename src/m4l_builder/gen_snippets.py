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

__all__ = ["ms_encode", "ms_decode", "ms_width"]


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
