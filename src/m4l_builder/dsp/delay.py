"""Delay and reverb."""

from ..objects import newobj, patchline
from ._common import _signal_sum_chain


def delay_line(id_prefix: str, max_delay_ms: int = 5000) -> tuple:
    """Create a tapin~/tapout~ delay line pair.

    Wire audio into {prefix}_tapin inlet 0; output from {prefix}_tapout outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_tapin", f"tapin~ {max_delay_ms}", numinlets=1,
               numoutlets=1, outlettype=["tapconnect"],
               patching_rect=[30, 120, 100, 20]),
        newobj(f"{p}_tapout", f"tapout~ {max_delay_ms}", numinlets=1,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 150, 100, 20]),
    ]

    lines = [
        patchline(f"{p}_tapin", 0, f"{p}_tapout", 0),
    ]

    return (boxes, lines)


def comb_resonator(id_prefix: str, num_voices: int = 4) -> tuple:
    """Create N parallel comb~ filters summed to a single output.

    comb~ inlets: signal, delay_ms, a_gain, b_ff, c_fb. Keep c_fb < 1.0.
    Wire audio into each {prefix}_comb_{n} inlet 0.
    Output from {prefix}_sum outlet 0.
    """
    if num_voices < 1:
        raise ValueError(f"comb_resonator num_voices must be >= 1, got {num_voices}")
    p = id_prefix
    boxes = []

    for i in range(num_voices):
        boxes.append(newobj(f"{p}_comb_{i}", "comb~", numinlets=5, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30 + i * 100, 120, 50, 20]))

    source_ids = [f"{p}_comb_{i}" for i in range(num_voices)]
    sum_boxes, sum_lines = _signal_sum_chain(p, source_ids)
    boxes.extend(sum_boxes)

    return (boxes, sum_lines)


def feedback_delay(id_prefix: str, max_delay_ms: int = 5000) -> tuple:
    """Create a delay line with tanh~ saturation and onepole~ filtering in the feedback path.

    Signal flow:
        input -> +~ (sum with feedback) -> tapin~ -> tapout~ ->
        tanh~ -> onepole~ -> *~ feedback_amount -> back to +~ sum

    Wire audio into {prefix}_sum inlet 0.
    Wire feedback amount (0-1) into {prefix}_fb inlet 1.
    Wire onepole~ cutoff into {prefix}_lp inlet 1.
    Output from {prefix}_tapout outlet 0.
    """
    p = id_prefix
    boxes = [
        # Input sum (dry + feedback return)
        newobj(f"{p}_sum", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 30, 20]),
        # Delay line
        newobj(f"{p}_tapin", f"tapin~ {max_delay_ms}", numinlets=1,
               numoutlets=1, outlettype=["tapconnect"],
               patching_rect=[30, 150, 100, 20]),
        newobj(f"{p}_tapout", f"tapout~ {max_delay_ms}", numinlets=1,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 180, 100, 20]),
        # Feedback path: tanh~ saturation
        newobj(f"{p}_sat", "tanh~", numinlets=1, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 210, 45, 20]),
        # Feedback path: onepole~ lowpass
        newobj(f"{p}_lp", "onepole~ 3000.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 240, 90, 20]),
        # Feedback amount
        newobj(f"{p}_fb", "*~ 0.5", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 270, 50, 20]),
    ]

    lines = [
        # Input sum -> tapin~
        patchline(f"{p}_sum", 0, f"{p}_tapin", 0),
        # tapin~ -> tapout~
        patchline(f"{p}_tapin", 0, f"{p}_tapout", 0),
        # Feedback path: tapout~ -> tanh~ -> onepole~ -> *~ fb -> back to sum
        patchline(f"{p}_tapout", 0, f"{p}_sat", 0),
        patchline(f"{p}_sat", 0, f"{p}_lp", 0),
        patchline(f"{p}_lp", 0, f"{p}_fb", 0),
        patchline(f"{p}_fb", 0, f"{p}_sum", 1),
    ]

    return (boxes, lines)


def reverb_network(id_prefix: str, num_combs: int = 4, num_allpasses: int = 2) -> tuple:
    """Schroeder reverb network with parallel combs and series allpasses.

    Mono input, mono output. Comb filters run in parallel, their outputs
    are summed, then passed through a chain of allpass filters.
    """
    if num_combs < 1:
        raise ValueError(f"reverb_network num_combs must be >= 1, got {num_combs}")
    if num_allpasses < 0:
        raise ValueError(f"reverb_network num_allpasses must be >= 0, got {num_allpasses}")
    # Classic Schroeder delay times in ms
    comb_delays = [29.7, 37.1, 41.1, 43.7, 31.3, 36.7, 40.1, 45.3]
    allpass_delays = [5.0, 1.7, 3.3, 4.1]

    boxes = []
    lines = []

    # Parallel comb filters
    for i in range(num_combs):
        delay_ms = comb_delays[i % len(comb_delays)]
        boxes.append(
            newobj(f"{id_prefix}_comb_{i}", f"comb~ {delay_ms} 0.7",
                   numinlets=3, numoutlets=1, outlettype=["signal"])
        )

    # Sum combs together with a chain of +~ objects
    if num_combs > 1:
        for i in range(num_combs - 1):
            boxes.append(
                newobj(f"{id_prefix}_sum_{i}", "+~", numinlets=2, numoutlets=1,
                       outlettype=["signal"])
            )

        # First two combs into first summer
        lines.append(patchline(f"{id_prefix}_comb_0", 0, f"{id_prefix}_sum_0", 0))
        lines.append(patchline(f"{id_prefix}_comb_1", 0, f"{id_prefix}_sum_0", 1))

        # Remaining combs chain through summers
        for i in range(2, num_combs):
            lines.append(patchline(f"{id_prefix}_sum_{i - 2}", 0, f"{id_prefix}_sum_{i - 1}", 0))
            lines.append(patchline(f"{id_prefix}_comb_{i}", 0, f"{id_prefix}_sum_{i - 1}", 1))

    # Allpass filters in series
    for i in range(num_allpasses):
        delay_ms = allpass_delays[i % len(allpass_delays)]
        boxes.append(
            newobj(f"{id_prefix}_ap_{i}", f"allpass~ {delay_ms} 0.5",
                   numinlets=3, numoutlets=1, outlettype=["signal"])
        )

    # Wire last summer (or single comb) to first allpass
    if num_combs > 1:
        last_sum = f"{id_prefix}_sum_{num_combs - 2}"
    else:
        last_sum = f"{id_prefix}_comb_0"

    if num_allpasses > 0:
        lines.append(patchline(last_sum, 0, f"{id_prefix}_ap_0", 0))
        # Chain allpasses in series
        for i in range(1, num_allpasses):
            lines.append(patchline(f"{id_prefix}_ap_{i - 1}", 0, f"{id_prefix}_ap_{i}", 0))

    return (boxes, lines)


def fdn_reverb(id_prefix: str, num_delays: int = 8) -> tuple:
    """Feedback delay network reverb with prime delay times.

    Uses N tapin~/tapout~ pairs at prime delay times (47,53,59,61,67,71,73,79ms).
    All tapout~ outputs are summed with a +~ chain.

    Wire audio into each {prefix}_tapin_{n} inlet 0.
    Output from {prefix}_sum outlet 0.
    """
    if num_delays < 1:
        raise ValueError(f"fdn_reverb num_delays must be >= 1, got {num_delays}")
    prime_delays = [47, 53, 59, 61, 67, 71, 73, 79]
    p = id_prefix
    boxes = []
    lines = []

    for i in range(num_delays):
        delay_ms = prime_delays[i % len(prime_delays)]
        boxes.append(newobj(f"{p}_tapin_{i}", f"tapin~ {delay_ms}", numinlets=1,
                            numoutlets=1, outlettype=["tapconnect"],
                            patching_rect=[30 + i * 100, 120, 80, 20]))
        boxes.append(newobj(f"{p}_tapout_{i}", f"tapout~ {delay_ms}", numinlets=1,
                            numoutlets=1, outlettype=["signal"],
                            patching_rect=[30 + i * 100, 150, 80, 20]))
        lines.append(patchline(f"{p}_tapin_{i}", 0, f"{p}_tapout_{i}", 0))

    source_ids = [f"{p}_tapout_{i}" for i in range(num_delays)]
    sum_boxes, sum_lines = _signal_sum_chain(p, source_ids)
    boxes.extend(sum_boxes)
    lines.extend(sum_lines)

    return (boxes, lines)


def convolver(id_prefix: str, ir_buffer: str = 'ir_buf') -> tuple:
    """Convolve a signal with an impulse response stored in a buffer~.

    Creates a buffer~ for the IR and a convolve~ pointing to it.
    Send 'read <filename>' to {prefix}_ir_buf inlet 0 to load an IR file.

    Wire audio into {prefix}_conv inlet 0.
    Output from {prefix}_conv outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_ir_buf", f"buffer~ {ir_buffer}", numinlets=1,
               numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 60, 120, 20]),
        newobj(f"{p}_conv", f"convolve~ {ir_buffer}", numinlets=1,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 120, 20]),
    ]
    return (boxes, [])
