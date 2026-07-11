"""Dynamics processors."""

from ..objects import newobj, patchline
from .filters import crossover_3band


def envelope_follower(id_prefix: str, attack_ms: float = 10,
                      release_ms: float = 100) -> tuple:
    """Create an envelope follower: abs~ -> slide~.

    Uses samplerate~ to get the actual sample rate at runtime, then expr~ converts
    ms values to samples. slide~ inlets 1/2 accept the sample counts.

    Wire audio into {prefix}_abs inlet 0; output from {prefix}_slide outlet 0.
    Wire attack ms into {prefix}_atk_expr inlet 0.
    Wire release ms into {prefix}_rel_expr inlet 0.
    """
    p = id_prefix

    boxes = [
        newobj(f"{p}_abs", "abs~", numinlets=1, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 40, 20]),
        # samplerate~ outputs the current sample rate as a signal
        newobj(f"{p}_sr", "samplerate~", numinlets=0, numoutlets=1,
               outlettype=["signal"], patching_rect=[130, 90, 75, 20]),
        # expr~ converts sr signal to a float for downstream use
        newobj(f"{p}_sr_snap", "snapshot~", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[130, 115, 70, 20]),
        # expr converts attack ms to samples: ms/1000 * sr
        newobj(f"{p}_atk_expr", "expr ($f1 / 1000.0) * $f2",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 145, 150, 20]),
        # expr converts release ms to samples
        newobj(f"{p}_rel_expr", "expr ($f1 / 1000.0) * $f2",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[190, 145, 150, 20]),
        newobj(f"{p}_slide", f"slide~ {attack_ms * 44.1} {release_ms * 44.1}",
               numinlets=3, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 175, 120, 20]),
    ]

    lines = [
        patchline(f"{p}_abs", 0, f"{p}_slide", 0),
        # samplerate~ -> snapshot~ to get float sr value
        patchline(f"{p}_sr", 0, f"{p}_sr_snap", 0),
        # snapshot sr -> both expr inlets 1
        patchline(f"{p}_sr_snap", 0, f"{p}_atk_expr", 1),
        patchline(f"{p}_sr_snap", 0, f"{p}_rel_expr", 1),
        # expr outputs -> slide~ inlets 1 (attack) and 2 (release)
        patchline(f"{p}_atk_expr", 0, f"{p}_slide", 1),
        patchline(f"{p}_rel_expr", 0, f"{p}_slide", 2),
    ]

    return (boxes, lines)


def compressor(id_prefix: str) -> tuple:
    """Create a log-domain stereo compressor.

    Signal flow per channel:
      input -> abs~ -> slide~ (attack/release) -> ampdb~ (linear to dB) ->
      - threshold -> * (1 - 1/ratio) -> clip~ 0 inf -> -~ 0 (negate gain reduction) ->
      dbtoa~ -> *~ input

    This is a detector + VCA: the dry audio must be fanned to BOTH the detector
    entry (abs~) AND the gain-apply inlet 0 (out *~). The out *~ inlet 0 is left
    as an external connection by design so a separate sidechain signal can drive
    detection — wiring nothing there yields constant 0 (silence).

    Wire audio L/R into {prefix}_abs_l / {prefix}_abs_r inlet 0 (detector) AND
    {prefix}_out_l / {prefix}_out_r inlet 0 (the signal to compress).
    Wire threshold (dB, negative) float into {prefix}_thresh_l inlet 1 and {prefix}_thresh_r inlet 1.
    Wire ratio float (> 1) into {prefix}_ratio_l inlet 1 and {prefix}_ratio_r inlet 1.
    Wire attack ms into {prefix}_atk_l inlet 1 and {prefix}_atk_r inlet 1.
    Wire release ms into {prefix}_rel_l inlet 1 and {prefix}_rel_r inlet 1.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    p = id_prefix
    boxes = []
    lines = []
    for ch in ("l", "r"):
        x = 30 if ch == "l" else 300

        # Level detection: abs~ -> slide~ for attack/release envelope
        boxes.append(newobj(f"{p}_abs_{ch}", "abs~", numinlets=1, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 120, 40, 20]))
        boxes.append(newobj(f"{p}_atk_{ch}", "slide~ 441 4410", numinlets=3, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 150, 120, 20]))
        # Convert to dB domain
        boxes.append(newobj(f"{p}_adb_{ch}", "ampdb~", numinlets=1, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 180, 55, 20]))
        # Subtract threshold (threshold is negative dB, e.g. -20)
        boxes.append(newobj(f"{p}_thresh_{ch}", "-~ 20.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 210, 60, 20]))
        # Compute gain reduction: excess * (1 - 1/ratio), clipped to positive
        boxes.append(newobj(f"{p}_ratio_{ch}", "*~ 0.5", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 240, 50, 20]))
        boxes.append(newobj(f"{p}_clip_{ch}", "clip~ 0. 1000.", numinlets=3, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 270, 90, 20]))
        # Negate: subtract gain reduction from 0 to get negative dB gain
        boxes.append(newobj(f"{p}_neg_{ch}", "!-~ 0.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 300, 55, 20]))
        # Convert back to linear
        boxes.append(newobj(f"{p}_lin_{ch}", "dbtoa~", numinlets=1, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 330, 50, 20]))
        # Apply gain to input
        boxes.append(newobj(f"{p}_out_{ch}", "*~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 360, 30, 20]))

        lines.append(patchline(f"{p}_abs_{ch}", 0, f"{p}_atk_{ch}", 0))
        lines.append(patchline(f"{p}_atk_{ch}", 0, f"{p}_adb_{ch}", 0))
        lines.append(patchline(f"{p}_adb_{ch}", 0, f"{p}_thresh_{ch}", 0))
        lines.append(patchline(f"{p}_thresh_{ch}", 0, f"{p}_ratio_{ch}", 0))
        lines.append(patchline(f"{p}_ratio_{ch}", 0, f"{p}_clip_{ch}", 0))
        lines.append(patchline(f"{p}_clip_{ch}", 0, f"{p}_neg_{ch}", 0))
        lines.append(patchline(f"{p}_neg_{ch}", 0, f"{p}_lin_{ch}", 0))
        lines.append(patchline(f"{p}_lin_{ch}", 0, f"{p}_out_{ch}", 1))

    return (boxes, lines)


def limiter(id_prefix: str) -> tuple:
    """Create a stereo brickwall limiter.

    Like compressor but with instant attack (1 sample) and infinite ratio (clip~).
    Detects peak level per channel, computes how much to attenuate, applies.

    Wire audio L/R into {prefix}_abs_l / {prefix}_abs_r inlet 0 AND {prefix}_out_l / {prefix}_out_r inlet 0.
    Wire threshold (linear, 0-1) into {prefix}_thresh_l inlet 1 and {prefix}_thresh_r inlet 1.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
    """
    p = id_prefix
    boxes = []
    lines = []
    for ch in ("l", "r"):
        x = 30 if ch == "l" else 250

        # Peak detection: abs~ -> slide~ with instant attack, slow release
        boxes.append(newobj(f"{p}_abs_{ch}", "abs~", numinlets=1, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 120, 40, 20]))
        boxes.append(newobj(f"{p}_peak_{ch}", "slide~ 1 4410", numinlets=3, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 150, 100, 20]))
        # Compute gain: threshold / peak (clip to max 1.0 so no expansion)
        # Use !/~ to get reciprocal of peak, then *~ threshold
        boxes.append(newobj(f"{p}_recip_{ch}", "!/~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 180, 55, 20]))
        boxes.append(newobj(f"{p}_thresh_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 210, 50, 20]))
        # Clip gain to max 1.0 so we only reduce, never expand
        boxes.append(newobj(f"{p}_gclip_{ch}", "clip~ 0. 1.", numinlets=3, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 240, 80, 20]))
        # Apply gain to input signal
        boxes.append(newobj(f"{p}_out_{ch}", "*~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[x, 270, 30, 20]))

        lines.append(patchline(f"{p}_abs_{ch}", 0, f"{p}_peak_{ch}", 0))
        lines.append(patchline(f"{p}_peak_{ch}", 0, f"{p}_recip_{ch}", 0))
        lines.append(patchline(f"{p}_recip_{ch}", 0, f"{p}_thresh_{ch}", 0))
        lines.append(patchline(f"{p}_thresh_{ch}", 0, f"{p}_gclip_{ch}", 0))
        lines.append(patchline(f"{p}_gclip_{ch}", 0, f"{p}_out_{ch}", 1))

    return (boxes, lines)


def gate_expander(id_prefix: str) -> tuple:
    """Stereo noise gate with threshold detection.

    Signal flow per channel: input -> abs~ -> slide~ -> >~ threshold -> *~ original
    The >~ output (0 or 1) multiplies the original signal to gate it.

    Detector + VCA: fan the dry audio to BOTH the detector entry (abs~) AND the
    gate-apply inlet 0 (*~). The {prefix}_gate_l / {prefix}_gate_r inlet 0 is an
    external connection by design (enables a sidechain key) — wiring nothing
    there yields constant 0 (silence).

    Wire audio L/R into {prefix}_abs_l / {prefix}_abs_r inlet 0 (detector) AND
    {prefix}_gate_l / {prefix}_gate_r inlet 0 (the signal to gate).
    Wire threshold (linear) into {prefix}_thresh_l / {prefix}_thresh_r inlet 1.
    Output from {prefix}_gate_l / {prefix}_gate_r outlet 0.
    """
    boxes = []
    lines = []

    for ch in ("l", "r"):
        # Envelope detection chain
        boxes.append(newobj(f"{id_prefix}_abs_{ch}", "abs~", numinlets=1, numoutlets=1,
                            outlettype=["signal"]))
        boxes.append(newobj(f"{id_prefix}_slide_{ch}", "slide~ 10 100", numinlets=3, numoutlets=1,
                            outlettype=["signal"]))
        boxes.append(newobj(f"{id_prefix}_thresh_{ch}", ">~ 0.1", numinlets=2, numoutlets=1,
                            outlettype=["signal"]))
        # Gate multiplier
        boxes.append(newobj(f"{id_prefix}_gate_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"]))

        # Detection chain: abs -> slide -> >~
        lines.append(patchline(f"{id_prefix}_abs_{ch}", 0, f"{id_prefix}_slide_{ch}", 0))
        lines.append(patchline(f"{id_prefix}_slide_{ch}", 0, f"{id_prefix}_thresh_{ch}", 0))
        # Gate signal = threshold comparison * original
        lines.append(patchline(f"{id_prefix}_thresh_{ch}", 0, f"{id_prefix}_gate_{ch}", 1))

    return (boxes, lines)


def sidechain_detect(id_prefix: str) -> tuple:
    """Mono envelope follower for sidechain signal detection.

    Signal flow: input -> abs~ -> slide~ -> envelope output (0-1 range).
    """
    boxes = [
        newobj(f"{id_prefix}_abs", "abs~", numinlets=1, numoutlets=1,
               outlettype=["signal"]),
        newobj(f"{id_prefix}_slide", "slide~ 10 300", numinlets=3, numoutlets=1,
               outlettype=["signal"]),
    ]
    lines = [
        patchline(f"{id_prefix}_abs", 0, f"{id_prefix}_slide", 0),
    ]
    return (boxes, lines)


def multiband_compressor(id_prefix: str) -> tuple:
    """3-band mono compressor using crossover_3band and compressor blocks.

    Splits signal into 3 bands via crossover, compresses each band
    independently (using the L channel of each stereo compressor),
    then sums back together.

    Wire audio into {prefix}_xover_xover_lo inlet 0.
    Output from {prefix}_sum2 outlet 0.
    """
    # Split into 3 bands
    xover_boxes, xover_lines = crossover_3band(f"{id_prefix}_xover")

    # Compress each band (compressor is stereo, we use L channel only)
    lo_boxes, lo_lines = compressor(f"{id_prefix}_lo")
    mid_boxes, mid_lines = compressor(f"{id_prefix}_mid")
    hi_boxes, hi_lines = compressor(f"{id_prefix}_hi")

    # Summing chain: lo + mid -> sum1, sum1 + hi -> sum2
    sum_boxes = [
        newobj(f"{id_prefix}_sum1", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"]),
        newobj(f"{id_prefix}_sum2", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"]),
    ]

    # Wire crossover band outputs to compressor inputs (L channel)
    # crossover_3band outputs:
    #   low band:  {prefix}_xover_xover_lo outlet 0
    #   mid band:  {prefix}_xover_xover_hi outlet 0
    #   high band: {prefix}_xover_xover_hi outlet 1
    xover_lines_extra = [
        # Low band -> lo compressor input (abs_l is the entry point)
        patchline(f"{id_prefix}_xover_xover_lo", 0, f"{id_prefix}_lo_abs_l", 0),
        # Also feed original to the output multiplier
        patchline(f"{id_prefix}_xover_xover_lo", 0, f"{id_prefix}_lo_out_l", 0),
        # Mid band -> mid compressor
        patchline(f"{id_prefix}_xover_xover_hi", 0, f"{id_prefix}_mid_abs_l", 0),
        patchline(f"{id_prefix}_xover_xover_hi", 0, f"{id_prefix}_mid_out_l", 0),
        # High band -> hi compressor
        patchline(f"{id_prefix}_xover_xover_hi", 1, f"{id_prefix}_hi_abs_l", 0),
        patchline(f"{id_prefix}_xover_xover_hi", 1, f"{id_prefix}_hi_out_l", 0),
    ]

    # Wire compressor outputs to summers
    sum_lines = [
        patchline(f"{id_prefix}_lo_out_l", 0, f"{id_prefix}_sum1", 0),
        patchline(f"{id_prefix}_mid_out_l", 0, f"{id_prefix}_sum1", 1),
        patchline(f"{id_prefix}_sum1", 0, f"{id_prefix}_sum2", 0),
        patchline(f"{id_prefix}_hi_out_l", 0, f"{id_prefix}_sum2", 1),
    ]

    boxes = xover_boxes + lo_boxes + mid_boxes + hi_boxes + sum_boxes
    lines = (xover_lines + lo_lines + mid_lines + hi_lines
             + xover_lines_extra + sum_lines)

    return (boxes, lines)


def lookahead_envelope_follower(id_prefix: str, lookahead_ms: float = 5) -> tuple:
    """Lookahead envelope follower: delays the signal while detecting envelope ahead.

    Signal flow:
        input -> tapin~ (delay buffer)
                 -> tapout~ (delayed signal output)
        input -> abs~ -> slide~ (envelope detection, parallel path)

    Wire audio into {prefix}_tapin inlet 0 AND {prefix}_abs inlet 0.
    Output delayed signal from {prefix}_tapout outlet 0.
    Output envelope from {prefix}_slide outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_tapin", f"tapin~ {int(lookahead_ms * 2)}", numinlets=1,
               numoutlets=1, outlettype=["tapconnect"],
               patching_rect=[30, 120, 100, 20]),
        newobj(f"{p}_tapout", f"tapout~ {lookahead_ms}", numinlets=1,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 150, 100, 20]),
        newobj(f"{p}_abs", "abs~", numinlets=1, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[160, 120, 40, 20]),
        newobj(f"{p}_slide", "slide~ 10 100", numinlets=3, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[160, 150, 90, 20]),
    ]
    lines = [
        patchline(f"{p}_tapin", 0, f"{p}_tapout", 0),
        patchline(f"{p}_abs", 0, f"{p}_slide", 0),
    ]
    return (boxes, lines)


def bitcrusher(id_prefix: str, bits: int = 8,
               rate_ratio: float = 1.0) -> tuple:
    """Bit depth and sample rate reduction.

    Uses degrade~ for combined bit/rate reduction: inlet 1 is a 0..1
    SAMPLING-RATE RATIO — ``1.0`` = full rate (no reduction), LOWER =
    more decimation (``0.5`` = half rate). Inlet 2 = bit depth.

    Direction verified against Cycling '74's factory "Max Degrader"
    (its Resamp% dial passes through ``/ 100.`` into inlet 1, i.e.
    0.01..1.0). The old ``rate_reduction >= 1`` model was BACKWARDS:
    every value >= 1 leaves the sample rate untouched, so "SR grit"
    controls scaled 1..N were silently inert (improvement-hunt #39/#49).

    Wire audio into {prefix}_degrade inlet 0.
    Output from {prefix}_degrade outlet 0.
    """
    if bits < 1 or bits > 32:
        raise ValueError(f"bitcrusher bits must be 1-32, got {bits}")
    if not 0.0 < rate_ratio <= 1.0:
        raise ValueError(
            f"bitcrusher rate_ratio must be in (0, 1] — degrade~ inlet 1 is a "
            f"sampling-rate RATIO (1.0 = no reduction), got {rate_ratio}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_degrade", f"degrade~ {rate_ratio:g} {bits}",
               numinlets=3, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 120, 20]),
    ]
    return (boxes, [])


def auto_gain(id_prefix: str, target_db: float = -12.0) -> tuple:
    """RMS-based makeup gain toward a target level.

    env~ reports the input RMS as a float stream; that level is converted to dB
    (atodb), subtracted from the target via !- to get the makeup in dB
    (target_db - measured_db), converted back to linear (dbtoa), and applied as
    the *~ gain coefficient. target_db sets the loudness goal (default -12 dB).

    Wire audio into {prefix}_env inlet 0 (the detector) AND {prefix}_mul inlet 0
    (the signal to normalize). Output from {prefix}_mul outlet 0.

    The previous form divided an unset numerator by the measured level, so the
    gain collapsed to 0 (silence) and env~ was never given an input — this wires
    the detector and computes a real target-relative makeup instead.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_env", "env~ 1024 512",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 100, 20]),
        # measured RMS -> dB
        newobj(f"{p}_atodb", "atodb",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 70, 60, 20]),
        # makeup dB = target_db - measured_db  (!- computes arg - input)
        newobj(f"{p}_makeup", f"!- {target_db}",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 110, 60, 20]),
        # makeup dB -> linear gain coefficient
        newobj(f"{p}_gain", "dbtoa",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 150, 60, 20]),
        newobj(f"{p}_mul", "*~ 1.",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 190, 60, 20]),
    ]
    lines = [
        patchline(f"{p}_env", 0, f"{p}_atodb", 0),
        patchline(f"{p}_atodb", 0, f"{p}_makeup", 0),
        patchline(f"{p}_makeup", 0, f"{p}_gain", 0),
        patchline(f"{p}_gain", 0, f"{p}_mul", 1),
    ]
    return (boxes, lines)
