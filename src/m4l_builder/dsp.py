"""Reusable DSP building blocks for M4L devices.

Each function returns a (boxes, lines) tuple where boxes is a list of box dicts
and lines is a list of patchline dicts. This makes it easy to compose DSP chains
by extending a device's boxes and lines lists.
"""

from .objects import newobj, patchline


def stereo_io(plugin_id: str = "obj-plugin", plugout_id: str = "obj-plugout",
              plugin_rect: list = None, plugout_rect: list = None) -> tuple:
    """Create plugin~ and plugout~ pair for audio I/O.

    Args:
        plugin_id: ID for the plugin~ object.
        plugout_id: ID for the plugout~ object.
        plugin_rect: Patching rect for plugin~.
        plugout_rect: Patching rect for plugout~.

    Returns:
        (boxes, lines) tuple. No lines are created — caller wires the DSP chain.
    """
    boxes = [
        newobj(plugin_id, "plugin~", numinlets=1, numoutlets=2,
               outlettype=["signal", "signal"],
               patching_rect=plugin_rect or [30, 30, 60, 20]),
        newobj(plugout_id, "plugout~", numinlets=2, numoutlets=0,
               patching_rect=plugout_rect or [30, 200, 60, 20]),
    ]
    return (boxes, [])


def gain_stage(id_prefix: str, *, patching_rect_l: list = None,
               patching_rect_r: list = None) -> tuple:
    """Create a stereo *~ gain stage.

    Creates two *~ objects for left and right channels. The second inlet
    of each accepts a signal-rate gain value.

    Args:
        id_prefix: Prefix for object IDs (creates {prefix}_l and {prefix}_r).
        patching_rect_l: Patching rect for left channel multiplier.
        patching_rect_r: Patching rect for right channel multiplier.

    Returns:
        (boxes, lines) tuple. No internal lines — caller connects inputs/outputs.
    """
    boxes = [
        newobj(f"{id_prefix}_l", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=patching_rect_l or [30, 120, 40, 20]),
        newobj(f"{id_prefix}_r", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=patching_rect_r or [150, 120, 40, 20]),
    ]
    return (boxes, [])


def dry_wet_mix(id_prefix: str,
                wet_source_l: tuple, wet_source_r: tuple,
                dry_source_l: tuple, dry_source_r: tuple) -> tuple:
    """Create a dry/wet mix stage.

    Uses *~ and +~ to crossfade between dry and wet signals based on a
    0.0-1.0 mix control. Send the mix float to {prefix}_mix_in inlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        wet_source_l: (object_id, outlet) tuple for wet left signal.
        wet_source_r: (object_id, outlet) tuple for wet right signal.
        dry_source_l: (object_id, outlet) tuple for dry left signal.
        dry_source_r: (object_id, outlet) tuple for dry right signal.

    Returns:
        (boxes, lines) tuple. Output is from {prefix}_out_l and {prefix}_out_r,
        outlet 0 each.
    """
    p = id_prefix
    boxes = [
        # Mix control entry: trigger fans float to 3 destinations.
        # CRITICAL: Do NOT use sig~ here — it starts at 0.0 on load,
        # which overrides *~ arguments and causes silence.
        newobj(f"{p}_mix_in", "t f f f", numinlets=1, numoutlets=3,
               outlettype=["", "", ""], patching_rect=[400, 80, 55, 20]),
        # Invert mix for dry: !-~ 1. gives (1 - mix)
        newobj(f"{p}_inv", "!-~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[400, 110, 45, 20]),
        # Wet gain — default 0 (muted until mix value arrives)
        newobj(f"{p}_wet_l", "*~ 0.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[300, 140, 30, 20]),
        newobj(f"{p}_wet_r", "*~ 0.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[340, 140, 30, 20]),
        # Dry gain — default 1 (pass-through: audio always flows at startup)
        newobj(f"{p}_dry_l", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[460, 140, 30, 20]),
        newobj(f"{p}_dry_r", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[500, 140, 30, 20]),
        # Sum
        newobj(f"{p}_out_l", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[380, 180, 30, 20]),
        newobj(f"{p}_out_r", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[420, 180, 30, 20]),
    ]

    lines = [
        # trigger fans mix float to wet L/R multipliers and dry inverter
        # trigger fires outlets RIGHT to LEFT: outlet 2 first, then 1, then 0
        patchline(f"{p}_mix_in", 0, f"{p}_wet_l", 1),
        patchline(f"{p}_mix_in", 1, f"{p}_wet_r", 1),
        patchline(f"{p}_mix_in", 2, f"{p}_inv", 0),
        patchline(f"{p}_inv", 0, f"{p}_dry_l", 1),
        patchline(f"{p}_inv", 0, f"{p}_dry_r", 1),
        # Wet sources -> wet multipliers
        patchline(wet_source_l[0], wet_source_l[1], f"{p}_wet_l", 0),
        patchline(wet_source_r[0], wet_source_r[1], f"{p}_wet_r", 0),
        # Dry sources -> dry multipliers
        patchline(dry_source_l[0], dry_source_l[1], f"{p}_dry_l", 0),
        patchline(dry_source_r[0], dry_source_r[1], f"{p}_dry_r", 0),
        # Sum wet + dry
        patchline(f"{p}_wet_l", 0, f"{p}_out_l", 0),
        patchline(f"{p}_dry_l", 0, f"{p}_out_l", 1),
        patchline(f"{p}_wet_r", 0, f"{p}_out_r", 0),
        patchline(f"{p}_dry_r", 0, f"{p}_out_r", 1),
    ]

    return (boxes, lines)


def ms_encode_decode(id_prefix: str) -> tuple:
    """Create Mid/Side encode and decode stages.

    Encoding: Mid = (L + R) * 0.5, Side = (L - R) * 0.5
    Decoding: L = Mid + Side, R = Mid - Side

    Caller should wire audio into {prefix}_enc_add and {prefix}_enc_sub
    inlets, process Mid from {prefix}_enc_mid outlet 0 and Side from
    {prefix}_enc_side outlet 0, then feed results into {prefix}_dec_add
    and {prefix}_dec_sub for decoded L/R output.

    Args:
        id_prefix: Prefix for object IDs.

    Returns:
        (boxes, lines) tuple.
    """
    p = id_prefix
    boxes = [
        # Encoder
        newobj(f"{p}_enc_add", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[300, 60, 30, 20]),
        newobj(f"{p}_enc_sub", "-~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[340, 60, 30, 20]),
        newobj(f"{p}_enc_mid", "*~ 0.5", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[300, 90, 45, 20]),
        newobj(f"{p}_enc_side", "*~ 0.5", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[340, 90, 45, 20]),
        # Decoder
        newobj(f"{p}_dec_add", "+~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[300, 160, 30, 20]),
        newobj(f"{p}_dec_sub", "-~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[340, 160, 30, 20]),
    ]

    lines = [
        # Encode: sum/diff -> scale by 0.5
        patchline(f"{p}_enc_add", 0, f"{p}_enc_mid", 0),
        patchline(f"{p}_enc_sub", 0, f"{p}_enc_side", 0),
    ]

    return (boxes, lines)


def dc_block(id_prefix: str) -> tuple:
    """Create a stereo DC blocking filter.

    GOTCHA: dcblock~ does NOT exist in Max 8. Uses biquad~ with
    high-pass coefficients instead: biquad~ 1. -1. 0. -0.9997 0.
    biquad~ has 6 inlets (signal + 5 coefficients) and 1 outlet.

    Args:
        id_prefix: Prefix for object IDs (creates {prefix}_l and {prefix}_r).

    Returns:
        (boxes, lines) tuple. No internal lines — caller connects inputs/outputs.
    """
    boxes = [
        newobj(f"{id_prefix}_l", "biquad~ 1. -1. 0. -0.9997 0.",
               numinlets=6, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 180, 20]),
        newobj(f"{id_prefix}_r", "biquad~ 1. -1. 0. -0.9997 0.",
               numinlets=6, numoutlets=1, outlettype=["signal"],
               patching_rect=[220, 120, 180, 20]),
    ]
    return (boxes, [])


def saturation(id_prefix: str, mode: str) -> tuple:
    """Create a stereo saturation stage.

    Supported modes:
    - "tanh": tanh~ — smooth tape-like saturation (1 inlet, 1 outlet)
    - "overdrive": overdrive~ — tube-like saturation (1 inlet, 1 outlet)
    - "clip": clip~ -1. 1. — hard clipping (3 inlets: signal, min, max; 1 outlet)
    - "degrade": degrade~ — bit/sample rate crush (3 inlets: signal, sr_factor,
      bit_depth; 1 outlet)

    Args:
        id_prefix: Prefix for object IDs (creates {prefix}_l and {prefix}_r).
        mode: One of "tanh", "overdrive", "clip", "degrade".

    Returns:
        (boxes, lines) tuple. No internal lines — caller connects inputs/outputs.

    Raises:
        ValueError: If mode is not recognized.
    """
    specs = {
        "tanh": ("tanh~", 1, 1, ["signal"]),
        "overdrive": ("overdrive~", 1, 1, ["signal"]),
        "clip": ("clip~ -1. 1.", 3, 1, ["signal"]),
        "degrade": ("degrade~", 3, 1, ["signal"]),
    }
    if mode not in specs:
        raise ValueError(f"Unknown saturation mode {mode!r}. "
                         f"Choose from: {', '.join(specs)}")
    text, numinlets, numoutlets, outlettype = specs[mode]
    boxes = [
        newobj(f"{id_prefix}_l", text, numinlets=numinlets,
               numoutlets=numoutlets, outlettype=outlettype,
               patching_rect=[30, 120, 80, 20]),
        newobj(f"{id_prefix}_r", text, numinlets=numinlets,
               numoutlets=numoutlets, outlettype=outlettype,
               patching_rect=[150, 120, 80, 20]),
    ]
    return (boxes, [])


def selector(id_prefix: str, num_inputs: int, initial: int = 1) -> tuple:
    """Create a selector~ object for switching between signal inputs.

    GOTCHA: selector~ N defaults to input 0 which means NO input (silence).
    Always specify the initial input argument. Default here is 1.

    selector~ N initial has N+1 inlets (int selector + N signal inputs)
    and 1 outlet.

    Args:
        id_prefix: Object ID for the selector~.
        num_inputs: Number of signal inputs (N).
        initial: Initial input selection (1-indexed, default 1). 0 = silence.

    Returns:
        (boxes, lines) tuple. No internal lines — caller connects inputs/outputs.
    """
    boxes = [
        newobj(id_prefix, f"selector~ {num_inputs} {initial}",
               numinlets=num_inputs + 1, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 100, 20]),
    ]
    return (boxes, [])


def highpass_filter(id_prefix: str) -> tuple:
    """Create a stereo high-pass filter using svf~.

    svf~ has 3 inlets (signal, cutoff_hz, resonance 0-1) and 4 outlets
    (LP, HP, BP, notch). This wires outlet 1 (HP) to a pass-through *~ 1.
    so the caller has a clear single-outlet object to connect from.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff into inlet 1, resonance into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.

    Args:
        id_prefix: Prefix for object IDs.

    Returns:
        (boxes, lines) tuple.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_l", "svf~", numinlets=3, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[30, 120, 40, 20]),
        newobj(f"{p}_r", "svf~", numinlets=3, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[150, 120, 40, 20]),
        # Pass-through to isolate HP outlet
        newobj(f"{p}_out_l", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 150, 40, 20]),
        newobj(f"{p}_out_r", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[150, 150, 40, 20]),
    ]
    lines = [
        # svf~ outlet 1 = HP
        patchline(f"{p}_l", 1, f"{p}_out_l", 0),
        patchline(f"{p}_r", 1, f"{p}_out_r", 0),
    ]
    return (boxes, lines)


def lowpass_filter(id_prefix: str) -> tuple:
    """Create a stereo low-pass filter using svf~.

    svf~ has 3 inlets (signal, cutoff_hz, resonance 0-1) and 4 outlets
    (LP, HP, BP, notch). This wires outlet 0 (LP) to a pass-through *~ 1.
    so the caller has a clear single-outlet object to connect from.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff into inlet 1, resonance into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.

    Args:
        id_prefix: Prefix for object IDs.

    Returns:
        (boxes, lines) tuple.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_l", "svf~", numinlets=3, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[30, 120, 40, 20]),
        newobj(f"{p}_r", "svf~", numinlets=3, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[150, 120, 40, 20]),
        # Pass-through to isolate LP outlet
        newobj(f"{p}_out_l", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 150, 40, 20]),
        newobj(f"{p}_out_r", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[150, 150, 40, 20]),
    ]
    lines = [
        # svf~ outlet 0 = LP
        patchline(f"{p}_l", 0, f"{p}_out_l", 0),
        patchline(f"{p}_r", 0, f"{p}_out_r", 0),
    ]
    return (boxes, lines)


def onepole_filter(id_prefix: str, freq: float = 1000.) -> tuple:
    """Create a stereo one-pole low-pass filter.

    onepole~ has 2 inlets (signal, cutoff frequency) and 1 outlet.

    Args:
        id_prefix: Prefix for object IDs (creates {prefix}_l and {prefix}_r).
        freq: Initial cutoff frequency in Hz.

    Returns:
        (boxes, lines) tuple. No internal lines — caller connects inputs/outputs.
    """
    boxes = [
        newobj(f"{id_prefix}_l", f"onepole~ {freq}", numinlets=2,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 80, 20]),
        newobj(f"{id_prefix}_r", f"onepole~ {freq}", numinlets=2,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[150, 120, 80, 20]),
    ]
    return (boxes, [])


def signal_divide(id_prefix: str) -> tuple:
    """Create a signal-rate division block.

    GOTCHA: /~ does NOT work for signal / signal in Max. Instead use
    !/~ 1. to compute the reciprocal (1/denominator), then multiply
    by the numerator with *~.

    !/~ 1. has 2 inlets (denominator signal on inlet 0, numerator arg
    on inlet 1) and 1 outlet (reciprocal). *~ has 2 inlets and 1 outlet.

    Wire denominator into {prefix}_recip inlet 0.
    Wire numerator into {prefix}_mul inlet 0.
    Output from {prefix}_mul outlet 0.

    Args:
        id_prefix: Prefix for object IDs.

    Returns:
        (boxes, lines) tuple.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_recip", "!/~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 50, 20]),
        newobj(f"{p}_mul", "*~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 150, 30, 20]),
    ]
    lines = [
        # reciprocal output -> multiplier inlet 1
        patchline(f"{p}_recip", 0, f"{p}_mul", 1),
    ]
    return (boxes, lines)


def tilt_eq(id_prefix: str, freq: float = 1000.) -> tuple:
    """Create a stereo tilt EQ.

    Uses onepole~ as a crossover filter at the given frequency. The low
    band (onepole~ output) and high band (original minus low) are each
    scaled independently, then summed. Adjusting the two gain stages
    creates a tilt effect: boosting lows while cutting highs, or vice versa.

    Per channel:
        signal -> onepole~ -> *~ (low gain)  -> +~ (output)
        signal -> -~ (subtract LP to get HP) -> *~ (high gain) -> +~ (output)

    Wire audio into {prefix}_lp_l / {prefix}_lp_r inlet 0 AND
    {prefix}_hp_l / {prefix}_hp_r inlet 0 (same signal to both).
    Wire low gain to {prefix}_lo_l / {prefix}_lo_r inlet 1.
    Wire high gain to {prefix}_hi_l / {prefix}_hi_r inlet 1.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        freq: Initial crossover frequency in Hz.

    Returns:
        (boxes, lines) tuple.
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
    """Create a 3-band crossover splitter using two cross~ objects.

    cross~ has 2 inlets (signal, freq_hz) and 2 outlets (LP, HP).
    First cross~ splits at a low frequency: LP=low band, HP feeds second cross~.
    Second cross~ splits at a high frequency: LP=mid band, HP=high band.
    Includes +~ summing objects for recombining the bands.

    Wire audio into {prefix}_xover_lo inlet 0.
    Wire low crossover freq into {prefix}_xover_lo inlet 1.
    Wire high crossover freq into {prefix}_xover_hi inlet 1.
    Low band from {prefix}_xover_lo outlet 0.
    Mid band from {prefix}_xover_hi outlet 0.
    High band from {prefix}_xover_hi outlet 1.
    Recombined output from {prefix}_sum outlet 0.

    Args:
        id_prefix: Prefix for object IDs.

    Returns:
        (boxes, lines) tuple.
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


def envelope_follower(id_prefix: str, attack_ms: float = 10,
                      release_ms: float = 100) -> tuple:
    """Create an envelope follower using abs~ and slide~.

    Signal flow: input -> abs~ -> slide~ -> output.
    slide~ args are in SAMPLES (multiply ms by 44.1 at 44100 sr).

    Wire audio into {prefix}_abs inlet 0.
    Output from {prefix}_slide outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        attack_ms: Attack time in milliseconds.
        release_ms: Release time in milliseconds.

    Returns:
        (boxes, lines) tuple.
    """
    p = id_prefix
    # Convert ms to samples at 44100 sr
    attack_samps = attack_ms * 44.1
    release_samps = release_ms * 44.1

    boxes = [
        newobj(f"{p}_abs", "abs~", numinlets=1, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 40, 20]),
        newobj(f"{p}_slide", f"slide~ {attack_samps} {release_samps}",
               numinlets=3, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 150, 120, 20]),
    ]

    lines = [
        patchline(f"{p}_abs", 0, f"{p}_slide", 0),
    ]

    return (boxes, lines)


def delay_line(id_prefix: str, max_delay_ms: int = 5000) -> tuple:
    """Create a tapin~/tapout~ delay line pair.

    tapin~ has 1 inlet (signal) and 1 outlet (tap connection).
    tapout~ has 1 inlet (from tapin~) and 1 outlet (delayed signal).

    Wire audio into {prefix}_tapin inlet 0.
    Output from {prefix}_tapout outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        max_delay_ms: Maximum delay time in milliseconds.

    Returns:
        (boxes, lines) tuple.
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


def lfo(id_prefix: str, waveform: str = "sine") -> tuple:
    """Create an LFO with rate and depth scaling, unipolar output (0-1).

    Supported waveforms:
    - "sine": cycle~ with *~ 0.5 then +~ 0.5 for unipolar
    - "saw": phasor~ (already 0-1 unipolar)
    - "square": rect~ with *~ 0.5 then +~ 0.5 for unipolar

    Wire rate (Hz) into the oscillator's inlet 0.
    Wire depth into {prefix}_depth inlet 1.
    Output from {prefix}_depth outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        waveform: One of "sine", "saw", "square".

    Returns:
        (boxes, lines) tuple.

    Raises:
        ValueError: If waveform is not recognized.
    """
    p = id_prefix
    boxes = []
    lines = []

    if waveform == "sine":
        # cycle~ outputs -1 to 1, convert to 0 to 1
        boxes.append(newobj(f"{p}_osc", "cycle~", numinlets=2, numoutlets=2,
                            outlettype=["signal", "signal"],
                            patching_rect=[30, 120, 50, 20]))
        boxes.append(newobj(f"{p}_scale", "*~ 0.5", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 150, 50, 20]))
        boxes.append(newobj(f"{p}_offset", "+~ 0.5", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 50, 20]))
        lines.append(patchline(f"{p}_osc", 0, f"{p}_scale", 0))
        lines.append(patchline(f"{p}_scale", 0, f"{p}_offset", 0))
        uni_out = (f"{p}_offset", 0)
    elif waveform == "saw":
        # phasor~ already outputs 0 to 1
        boxes.append(newobj(f"{p}_osc", "phasor~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 120, 60, 20]))
        uni_out = (f"{p}_osc", 0)
    elif waveform == "square":
        # rect~ outputs -1 to 1, convert to 0 to 1
        boxes.append(newobj(f"{p}_osc", "rect~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 120, 50, 20]))
        boxes.append(newobj(f"{p}_scale", "*~ 0.5", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 150, 50, 20]))
        boxes.append(newobj(f"{p}_offset", "+~ 0.5", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 50, 20]))
        lines.append(patchline(f"{p}_osc", 0, f"{p}_scale", 0))
        lines.append(patchline(f"{p}_scale", 0, f"{p}_offset", 0))
        uni_out = (f"{p}_offset", 0)
    else:
        raise ValueError(f"Unknown waveform {waveform!r}. "
                         f"Choose from: sine, saw, square")

    # Depth scaling: unipolar LFO * depth amount
    boxes.append(newobj(f"{p}_depth", "*~ 1.", numinlets=2, numoutlets=1,
                        outlettype=["signal"],
                        patching_rect=[30, 210, 40, 20]))
    lines.append(patchline(uni_out[0], uni_out[1], f"{p}_depth", 0))

    return (boxes, lines)


def comb_resonator(id_prefix: str, num_voices: int = 4) -> tuple:
    """Create N parallel comb~ filters with summing.

    comb~ has 5 inlets (signal, delay_ms, a_gain, b_ff, c_fb).
    Feedback must be < 1.0 to prevent instability.

    Wire audio into each {prefix}_comb_{n} inlet 0.
    Wire delay_ms, a_gain, b_ff, c_fb into inlets 1-4 of each comb.
    Output from {prefix}_sum outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        num_voices: Number of parallel comb filters.

    Returns:
        (boxes, lines) tuple.
    """
    p = id_prefix
    boxes = []
    lines = []

    for i in range(num_voices):
        boxes.append(newobj(f"{p}_comb_{i}", "comb~", numinlets=5, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30 + i * 100, 120, 50, 20]))

    # Build summing chain: comb_0 + comb_1 -> +~ -> + comb_2 -> +~ -> ...
    if num_voices == 1:
        # Single comb, just pass through
        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 40, 20]))
        lines.append(patchline(f"{p}_comb_0", 0, f"{p}_sum", 0))
    else:
        # First adder sums comb_0 + comb_1
        boxes.append(newobj(f"{p}_add_0", "+~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180, 30, 20]))
        lines.append(patchline(f"{p}_comb_0", 0, f"{p}_add_0", 0))
        lines.append(patchline(f"{p}_comb_1", 0, f"{p}_add_0", 1))

        prev_sum = f"{p}_add_0"
        for i in range(2, num_voices):
            adder_id = f"{p}_add_{i - 1}"
            boxes.append(newobj(adder_id, "+~", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 180 + (i - 1) * 30, 30, 20]))
            lines.append(patchline(prev_sum, 0, adder_id, 0))
            lines.append(patchline(f"{p}_comb_{i}", 0, adder_id, 1))
            prev_sum = adder_id

        # Pass-through for consistent output naming
        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 180 + (num_voices - 1) * 30, 40, 20]))
        lines.append(patchline(prev_sum, 0, f"{p}_sum", 0))

    return (boxes, lines)


def feedback_delay(id_prefix: str, max_delay_ms: int = 5000) -> tuple:
    """Create a delay line with tanh~ saturation and onepole~ filtering in the feedback path.

    Signal flow:
        input -> +~ (sum with feedback) -> tapin~ -> tapout~ ->
        tanh~ -> onepole~ -> *~ feedback_amount -> back to +~ sum

    Wire audio into {prefix}_sum inlet 0.
    Wire feedback amount (0-1) into {prefix}_fb inlet 1.
    Wire onepole~ cutoff into {prefix}_lp inlet 1.
    Output from {prefix}_tapout outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        max_delay_ms: Maximum delay time in milliseconds.

    Returns:
        (boxes, lines) tuple.
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


def tremolo(id_prefix: str, waveform: str = "sine") -> tuple:
    """Create a tremolo effect: LFO modulating signal amplitude.

    Uses an internal LFO (unipolar 0-1) multiplied against the input signal.

    Wire audio into {prefix}_mod inlet 0.
    Wire LFO rate (Hz) into the oscillator inlet 0.
    Wire depth into {prefix}_lfo_depth inlet 1.
    Output from {prefix}_mod outlet 0.

    Args:
        id_prefix: Prefix for object IDs.
        waveform: LFO waveform — "sine", "saw", or "square".

    Returns:
        (boxes, lines) tuple.

    Raises:
        ValueError: If waveform is not recognized.
    """
    p = id_prefix

    # Build LFO sub-chain
    lfo_boxes, lfo_lines = lfo(f"{p}_lfo", waveform=waveform)

    # Amplitude modulator: signal * LFO
    mod_box = newobj(f"{p}_mod", "*~", numinlets=2, numoutlets=1,
                     outlettype=["signal"], patching_rect=[30, 270, 30, 20])

    boxes = lfo_boxes + [mod_box]
    lines = lfo_lines + [
        # LFO depth output -> modulator inlet 1
        patchline(f"{p}_lfo_depth", 0, f"{p}_mod", 1),
    ]

    return (boxes, lines)
