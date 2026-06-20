"""Shared low-level DSP helpers."""

import math

from ..objects import newobj, patchline


def _svf_filter(id_prefix: str, outlet_index: int) -> tuple:
    """Shared stereo svf~ filter wiring an outlet through *~ 1. pass-through.

    outlet_index: 0=LP, 1=HP, 2=BP, 3=notch.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_l", "svf~", numinlets=3, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[30, 120, 40, 20]),
        newobj(f"{p}_r", "svf~", numinlets=3, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[150, 120, 40, 20]),
        newobj(f"{p}_out_l", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 150, 40, 20]),
        newobj(f"{p}_out_r", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[150, 150, 40, 20]),
    ]
    lines = [
        patchline(f"{p}_l", outlet_index, f"{p}_out_l", 0),
        patchline(f"{p}_r", outlet_index, f"{p}_out_r", 0),
    ]
    return (boxes, lines)


def _signal_sum_chain(id_prefix: str, source_ids: list) -> tuple:
    """Sum N signal sources via a +~ chain, output from {prefix}_sum.

    Returns (boxes, lines) for the summing chain only.
    Caller must provide the source boxes separately.
    """
    p = id_prefix
    n = len(source_ids)
    boxes = []
    lines = []

    if n == 0:
        boxes.append(newobj(f"{p}_sum", "*~ 0.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 40, 20]))
    elif n == 1:
        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 40, 20]))
        lines.append(patchline(source_ids[0], 0, f"{p}_sum", 0))
    else:
        boxes.append(newobj(f"{p}_add_0", "+~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 30, 20]))
        lines.append(patchline(source_ids[0], 0, f"{p}_add_0", 0))
        lines.append(patchline(source_ids[1], 0, f"{p}_add_0", 1))
        prev = f"{p}_add_0"
        for i in range(2, n):
            adder_id = f"{p}_add_{i - 1}"
            boxes.append(newobj(adder_id, "+~", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 180 + (i - 1) * 30, 30, 20]))
            lines.append(patchline(prev, 0, adder_id, 0))
            lines.append(patchline(source_ids[i], 0, adder_id, 1))
            prev = adder_id
        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180 + (n - 1) * 30, 40, 20]))
        lines.append(patchline(prev, 0, f"{p}_sum", 0))

    return (boxes, lines)


def _biquad_shelf(id_prefix: str, shelf_type: str,
                  freq: float, gain_db: float,
                  samplerate: float = 48000.0) -> tuple:
    """Shared biquad~ shelf filter (high or low).

    shelf_type: 'high' or 'low'.
    samplerate: session sample rate used to normalize the cutoff. Defaults to
        48000 Hz (Ableton Live's default) — coefficients are baked at build
        time, so a device built for 44100 sounds shifted at 48k and vice versa.
    """
    p = id_prefix
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / samplerate
    cos_w0 = math.cos(w0)
    # RBJ shelving EQ: alpha = sin(w0)/2 * sqrt((A + 1/A)*(1/S - 1) + 2) with
    # shelf slope S = 1/sqrt(2) (Butterworth), so 1/S = sqrt(2).
    alpha = math.sin(w0) / 2.0 * math.sqrt((A + 1 / A) * (math.sqrt(2) - 1) + 2)

    if shelf_type == 'high':
        b0 = A * ((A + 1) + (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * cos_w0)
        b2 = A * ((A + 1) + (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha)
        a0 = (A + 1) - (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha
        a1 = 2 * ((A - 1) - (A + 1) * cos_w0)
        a2 = (A + 1) - (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha
    else:
        b0 = A * ((A + 1) - (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha)
        b1 = 2 * A * ((A - 1) - (A + 1) * cos_w0)
        b2 = A * ((A + 1) - (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha)
        a0 = (A + 1) + (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha
        a1 = -2 * ((A - 1) + (A + 1) * cos_w0)
        a2 = (A + 1) + (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha

    b0n = round(b0 / a0, 6)
    b1n = round(b1 / a0, 6)
    b2n = round(b2 / a0, 6)
    a1n = round(-a1 / a0, 6)
    a2n = round(-a2 / a0, 6)
    coeff_str = f"biquad~ {b0n} {b1n} {b2n} {a1n} {a2n}"

    boxes = [
        newobj(f"{p}_l", coeff_str, numinlets=6, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 200, 20]),
        newobj(f"{p}_r", coeff_str, numinlets=6, numoutlets=1,
               outlettype=["signal"], patching_rect=[240, 120, 200, 20]),
    ]
    return (boxes, [])


def _nxn_signal_sum(p, rows, cols, cell_fmt, adder_prefix, out_fmt):
    """Build an NxN *~ gain matrix with per-column +~ summing chains.

    cell_fmt(i, j) -> cell ID string
    adder_prefix   -> prefix for intermediate +~ nodes
    out_fmt(j)     -> output node ID string
    """
    boxes = []
    lines = []

    for i in range(rows):
        for j in range(cols):
            cell_id = cell_fmt(i, j)
            boxes.append(newobj(cell_id, "*~ 0.",
                                numinlets=2, numoutlets=1, outlettype=["signal"],
                                patching_rect=[30 + j * 60, 30 + i * 40, 50, 20]))

    for j in range(cols):
        prev = None
        for i in range(rows):
            cell_id = cell_fmt(i, j)
            if prev is None:
                prev = cell_id
            else:
                adder_id = f"{adder_prefix}_{j}_{i}"
                boxes.append(newobj(adder_id, "+~",
                                    numinlets=2, numoutlets=1, outlettype=["signal"],
                                    patching_rect=[30 + j * 60,
                                                   30 + rows * 40 + i * 30, 30, 20]))
                lines.append(patchline(prev, 0, adder_id, 0))
                lines.append(patchline(cell_id, 0, adder_id, 1))
                prev = adder_id

        out_id = out_fmt(j)
        boxes.append(newobj(out_id, "*~ 1.",
                            numinlets=2, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30 + j * 60,
                                           30 + rows * 40 + rows * 30, 50, 20]))
        if prev is not None:
            lines.append(patchline(prev, 0, out_id, 0))

    return boxes, lines
