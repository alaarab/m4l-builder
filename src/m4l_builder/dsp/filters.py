"""Filters and EQ."""

from ..objects import newobj, patchline
from ._common import _biquad_shelf, _svf_filter


def highpass_filter(id_prefix: str) -> tuple:
    """Create a stereo high-pass filter using svf~.

    svf~ has 3 inlets (signal, cutoff_hz, resonance 0-1) and 4 outlets (LP, HP, BP, notch).
    Wires outlet 1 (HP) through a *~ 1. pass-through so the caller has a single clean outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff into inlet 1, resonance into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    return _svf_filter(id_prefix, 1)


def lowpass_filter(id_prefix: str) -> tuple:
    """Create a stereo low-pass filter using svf~.

    svf~ has 3 inlets (signal, cutoff_hz, resonance 0-1) and 4 outlets (LP, HP, BP, notch).
    Wires outlet 0 (LP) through a *~ 1. pass-through so the caller has a single clean outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff into inlet 1, resonance into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    return _svf_filter(id_prefix, 0)


def onepole_filter(id_prefix: str, freq: float = 1000.) -> tuple:
    """Create a stereo one-pole low-pass filter (onepole~, 2 inlets: signal, cutoff Hz)."""
    boxes = [
        newobj(f"{id_prefix}_l", f"onepole~ {freq}", numinlets=2,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 80, 20]),
        newobj(f"{id_prefix}_r", f"onepole~ {freq}", numinlets=2,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[150, 120, 80, 20]),
    ]
    return (boxes, [])


def tilt_eq(id_prefix: str, freq: float = 1000.) -> tuple:
    """Create a stereo tilt EQ using onepole~ as a crossover.

    Low band (onepole~ output) and high band (original minus LP) are scaled
    independently and summed. Boost one side to tilt.

    Per channel:
        signal -> onepole~ -> *~ (low gain)  -> +~ (output)
        signal -> -~ (original - LP = HP)    -> *~ (high gain) -> +~ (output)

    Wire audio into {prefix}_lp_l / {prefix}_lp_r AND {prefix}_hp_l / {prefix}_hp_r (same signal).
    Wire low gain to {prefix}_lo_l / {prefix}_lo_r inlet 1.
    Wire high gain to {prefix}_hi_l / {prefix}_hi_r inlet 1.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    p = id_prefix
    boxes = []
    lines = []
    for ch in ("l", "r"):
        x = 30 if ch == "l" else 250
        # Low-pass via onepole~
        boxes.append(newobj(f"{p}_lp_{ch}", f"onepole~ {freq}", numinlets=2,
                            numoutlets=1, outlettype=["signal"],
                            patching_rect=[x, 120, 80, 20]))
        # Subtract LP from input to get HP
        boxes.append(newobj(f"{p}_hp_{ch}", "-~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x + 90, 120, 30, 20]))
        # Low gain
        boxes.append(newobj(f"{p}_lo_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 150, 40, 20]))
        # High gain
        boxes.append(newobj(f"{p}_hi_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x + 90, 150, 40, 20]))
        # Sum
        boxes.append(newobj(f"{p}_out_{ch}", "+~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x + 45, 180, 30, 20]))
        # Wiring
        # onepole~ LP output -> low gain input
        lines.append(patchline(f"{p}_lp_{ch}", 0, f"{p}_lo_{ch}", 0))
        # onepole~ LP output -> subtract inlet 1 (subtract LP from original)
        lines.append(patchline(f"{p}_lp_{ch}", 0, f"{p}_hp_{ch}", 1))
        # HP (original - LP) -> high gain input
        lines.append(patchline(f"{p}_hp_{ch}", 0, f"{p}_hi_{ch}", 0))
        # Gains -> sum
        lines.append(patchline(f"{p}_lo_{ch}", 0, f"{p}_out_{ch}", 0))
        lines.append(patchline(f"{p}_hi_{ch}", 0, f"{p}_out_{ch}", 1))

    return (boxes, lines)


def crossover_3band(id_prefix: str) -> tuple:
    """Create a 3-band crossover using two cross~ objects.

    cross~ inlets: (signal, freq_hz); outlets: (LP, HP).
    First cross~ splits at low freq; its HP feeds the second cross~ at high freq.

    Wire audio into {prefix}_xover_lo inlet 0.
    Wire low crossover freq into {prefix}_xover_lo inlet 1.
    Wire high crossover freq into {prefix}_xover_hi inlet 1.
    Low band: {prefix}_xover_lo outlet 0. Mid: {prefix}_xover_hi outlet 0.
    High: {prefix}_xover_hi outlet 1. Recombined: {prefix}_sum outlet 0.
    """
    p = id_prefix
    boxes = [
        # First crossover: splits into low and everything-above-low
        newobj(f"{p}_xover_lo", "cross~", numinlets=2, numoutlets=2,
               outlettype=["signal", "signal"],
               patching_rect=[30, 120, 50, 20]),
        # Second crossover: splits the HP of first into mid and high
        newobj(f"{p}_xover_hi", "cross~", numinlets=2, numoutlets=2,
               outlettype=["signal", "signal"],
               patching_rect=[150, 120, 50, 20]),
        # Sum low + mid
        newobj(f"{p}_sum_lo_mid", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 180, 30, 20]),
        # Sum (low+mid) + high
        newobj(f"{p}_sum", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[90, 210, 30, 20]),
    ]

    lines = [
        # HP of first crossover -> second crossover input
        patchline(f"{p}_xover_lo", 1, f"{p}_xover_hi", 0),
        # Low band -> sum low+mid inlet 0
        patchline(f"{p}_xover_lo", 0, f"{p}_sum_lo_mid", 0),
        # Mid band -> sum low+mid inlet 1
        patchline(f"{p}_xover_hi", 0, f"{p}_sum_lo_mid", 1),
        # Sum low+mid -> final sum inlet 0
        patchline(f"{p}_sum_lo_mid", 0, f"{p}_sum", 0),
        # High band -> final sum inlet 1
        patchline(f"{p}_xover_hi", 1, f"{p}_sum", 1),
    ]

    return (boxes, lines)


def bandpass_filter(id_prefix: str) -> tuple:
    """Create a stereo band-pass filter using svf~.

    svf~ outlets: 0=LP, 1=HP, 2=BP, 3=notch. Wires outlet 2 (BP) through a
    *~ 1. pass-through for a clean single outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff Hz into inlet 1, resonance (0-1) into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    return _svf_filter(id_prefix, 2)


def notch_filter(id_prefix: str) -> tuple:
    """Create a stereo notch filter using svf~.

    svf~ outlets: 0=LP, 1=HP, 2=BP, 3=notch. Wires outlet 3 (notch) through a
    *~ 1. pass-through for a clean single outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff Hz into inlet 1, resonance (0-1) into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    return _svf_filter(id_prefix, 3)


def highshelf_filter(id_prefix: str, freq: float = 3000., gain_db: float = 0.) -> tuple:
    """Create a stereo high-shelf EQ filter using biquad~.

    Uses fixed high-shelf biquad coefficients. Wire cutoff and gain updates
    externally via direct biquad~ coefficient messages if needed.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Output from {prefix}_l / {prefix}_r outlet 0.
    """
    return _biquad_shelf(id_prefix, 'high', freq, gain_db)


def lowshelf_filter(id_prefix: str, freq: float = 300., gain_db: float = 0.) -> tuple:
    """Create a stereo low-shelf EQ filter using biquad~.

    Uses fixed low-shelf biquad coefficients. Wire cutoff and gain updates
    externally via direct biquad~ coefficient messages if needed.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Output from {prefix}_l / {prefix}_r outlet 0.
    """
    return _biquad_shelf(id_prefix, 'low', freq, gain_db)


def peaking_eq(id_prefix: str, *, freq: float = 1000,
               gain: float = 0, q: float = 1.0) -> tuple:
    """Create a parametric peaking EQ band using filtercoeff~ and biquad~.

    filtercoeff~ computes biquad coefficients for the given freq/gain/Q.
    biquad~ applies them to the audio signal.

    Wire audio into {prefix}_biquad inlet 0.
    Output from {prefix}_biquad outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_coeff", f"filtercoeff~ peaknotch {freq} {gain} {q}",
               numinlets=6, numoutlets=1, outlettype=[""],
               patching_rect=[30, 120, 200, 20]),
        newobj(f"{p}_biquad", "biquad~", numinlets=6, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[30, 160, 50, 20]),
    ]
    lines = [
        patchline(f"{p}_coeff", 0, f"{p}_biquad", 1),
    ]
    return (boxes, lines)


def allpass_filter(id_prefix: str, *, freq: float = 1000,
                   q: float = 0.7) -> tuple:
    """Create an allpass filter using filtercoeff~ and biquad~.

    Same pattern as peaking_eq but with allpass coefficients.

    Wire audio into {prefix}_biquad inlet 0.
    Output from {prefix}_biquad outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_coeff", f"filtercoeff~ allpass {freq} 1. {q}",
               numinlets=6, numoutlets=1, outlettype=[""],
               patching_rect=[30, 120, 200, 20]),
        newobj(f"{p}_biquad", "biquad~", numinlets=6, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[30, 160, 50, 20]),
    ]
    lines = [
        patchline(f"{p}_coeff", 0, f"{p}_biquad", 1),
    ]
    return (boxes, lines)


def spectrum_band_extract(id_prefix: str, low_hz: float = 200,
                          high_hz: float = 2000) -> tuple:
    """Extract a frequency band using cascaded highpass + lowpass filters.

    Uses hip~ at low_hz and lop~ at high_hz.
    Wire audio into {prefix}_hp inlet 0.
    Output from {prefix}_lp outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_hp", f"hip~ {low_hz}",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 30, 80, 20]),
        newobj(f"{p}_lp", f"lop~ {high_hz}",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 70, 80, 20]),
    ]
    lines = [
        patchline(f"{p}_hp", 0, f"{p}_lp", 0),
    ]
    return (boxes, lines)
