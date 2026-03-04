"""Reusable DSP building blocks for M4L devices.

Each function returns a (boxes, lines) tuple where boxes is a list of box dicts
and lines is a list of patchline dicts. This makes it easy to compose DSP chains
by extending a device's boxes and lines lists.
"""

from .objects import newobj, patchline


def stereo_io(plugin_id: str = "obj-plugin", plugout_id: str = "obj-plugout",
              plugin_rect: list = None, plugout_rect: list = None) -> tuple:
    """Create plugin~ and plugout~ pair for audio I/O.

    Returns (boxes, lines) with no lines. Caller wires the DSP chain.
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
    """Create a stereo *~ gain stage (left and right channels).

    The second inlet of each *~ accepts a signal-rate gain value.
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
    """Create a stereo dry/wet crossfade stage (0.0-1.0 mix control).

    Send the mix float to {prefix}_mix_in inlet 0.
    Output from {prefix}_out_l and {prefix}_out_r, outlet 0 each.
    """
    p = id_prefix
    boxes = [
        # Mix control: t f f f fans the float to 3 destinations.
        # don't use sig~ here, starts at 0.0 on load and overrides *~ args, causing silence.
        newobj(f"{p}_mix_in", "t f f f", numinlets=1, numoutlets=3,
               outlettype=["", "", ""], patching_rect=[400, 80, 55, 20]),
        # Invert mix for dry: !-~ 1. gives (1 - mix)
        newobj(f"{p}_inv", "!-~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[400, 110, 45, 20]),
        # Wet gain, default 0 (muted until mix value arrives)
        newobj(f"{p}_wet_l", "*~ 0.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[300, 140, 30, 20]),
        newobj(f"{p}_wet_r", "*~ 0.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[340, 140, 30, 20]),
        # Dry gain, default 1 (pass-through: audio always flows at startup)
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

    Wire audio into {prefix}_enc_add and {prefix}_enc_sub, process Mid/Side,
    then feed decoded results into {prefix}_dec_add and {prefix}_dec_sub.
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

    dcblock~ doesn't exist in Max 8, so this uses biquad~ with HP coefficients:
    biquad~ 1. -1. 0. -0.9997 0. (biquad~ has 6 inlets: signal + 5 coefficients).
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

    Modes:
    - "tanh": tanh~, smooth tape-like saturation
    - "overdrive": overdrive~, tube-like saturation
    - "clip": clip~ -1. 1., hard clipping (3 inlets: signal, min, max)
    - "degrade": degrade~, bit/sample rate crush (3 inlets: signal, sr_factor, bit_depth)

    Raises ValueError for unknown modes.
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
    """Create a selector~ for switching between signal inputs.

    selector~ N initial has N+1 inlets (int selector + N signal inputs).
    selector~ N without an initial arg defaults to input 0 (silence), so always pass initial.
    """
    if initial < 0 or initial > num_inputs:
        raise ValueError(f"selector~ initial {initial} out of range [0, {num_inputs}]")
    boxes = [
        newobj(id_prefix, f"selector~ {num_inputs} {initial}",
               numinlets=num_inputs + 1, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 100, 20]),
    ]
    return (boxes, [])


def highpass_filter(id_prefix: str) -> tuple:
    """Create a stereo high-pass filter using svf~.

    svf~ has 3 inlets (signal, cutoff_hz, resonance 0-1) and 4 outlets (LP, HP, BP, notch).
    Wires outlet 1 (HP) through a *~ 1. pass-through so the caller has a single clean outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff into inlet 1, resonance into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
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

    svf~ has 3 inlets (signal, cutoff_hz, resonance 0-1) and 4 outlets (LP, HP, BP, notch).
    Wires outlet 0 (LP) through a *~ 1. pass-through so the caller has a single clean outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff into inlet 1, resonance into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
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


def signal_divide(id_prefix: str) -> tuple:
    """Create a signal-rate division block.

    /~ doesn't work for signal/signal in Max, so this uses !/~ 1. to get the reciprocal
    (1/denominator), then multiplies by the numerator with *~.

    Wire denominator into {prefix}_recip inlet 0.
    Wire numerator into {prefix}_mul inlet 0.
    Output from {prefix}_mul outlet 0.
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
        newobj(f"{p}_atk_expr", f"expr ($f1 / 1000.0) * $f2",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 145, 150, 20]),
        # expr converts release ms to samples
        newobj(f"{p}_rel_expr", f"expr ($f1 / 1000.0) * $f2",
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


def lfo(id_prefix: str, waveform: str = "sine") -> tuple:
    """Create a unipolar LFO (0-1 output) with depth scaling.

    Waveforms: "sine" (cycle~), "saw" (phasor~, already 0-1), "square" (rect~).
    sine and square are shifted to 0-1 via *~ 0.5 + 0.5.

    Wire rate (Hz) into the oscillator inlet 0.
    Wire depth into {prefix}_depth inlet 1; output from {prefix}_depth outlet 0.

    Raises ValueError for unknown waveforms.
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
    elif waveform == "triangle":
        # tri~ outputs -1 to 1, convert to 0 to 1
        boxes.append(newobj(f"{p}_osc", "tri~", numinlets=2, numoutlets=1,
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
                         f"Choose from: sine, saw, square, triangle")

    # Depth scaling: unipolar LFO * depth amount
    boxes.append(newobj(f"{p}_depth", "*~ 1.", numinlets=2, numoutlets=1,
                        outlettype=["signal"],
                        patching_rect=[30, 210, 40, 20]))
    lines.append(patchline(uni_out[0], uni_out[1], f"{p}_depth", 0))

    return (boxes, lines)


def comb_resonator(id_prefix: str, num_voices: int = 4) -> tuple:
    """Create N parallel comb~ filters summed to a single output.

    comb~ inlets: signal, delay_ms, a_gain, b_ff, c_fb. Keep c_fb < 1.0.
    Wire audio into each {prefix}_comb_{n} inlet 0.
    Output from {prefix}_sum outlet 0.
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
    """Create a tremolo effect: LFO amplitude modulation.

    Wire audio into {prefix}_mod inlet 0.
    Wire LFO rate (Hz) into the oscillator inlet 0.
    Wire depth into {prefix}_lfo_depth inlet 1.
    Output from {prefix}_mod outlet 0.
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


def param_smooth(id_prefix: str, smooth_ms: float = 20) -> tuple:
    """Smooth a control signal using pack + line~.

    The pack f {ms} -> line~ pattern for smoothing parameter changes. Useful for
    eliminating zipper noise on any float-rate control value.

    Wire control float into {prefix}_pack inlet 0.
    Output from {prefix}_line outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pack", f"pack f {smooth_ms}", numinlets=2, numoutlets=1,
               outlettype=[""], patching_rect=[30, 120, 80, 20]),
        newobj(f"{p}_line", "line~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 150, 40, 20]),
    ]
    lines = [
        patchline(f"{p}_pack", 0, f"{p}_line", 0),
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
        # svf~ outlet 2 = BP
        patchline(f"{p}_l", 2, f"{p}_out_l", 0),
        patchline(f"{p}_r", 2, f"{p}_out_r", 0),
    ]
    return (boxes, lines)


def notch_filter(id_prefix: str) -> tuple:
    """Create a stereo notch filter using svf~.

    svf~ outlets: 0=LP, 1=HP, 2=BP, 3=notch. Wires outlet 3 (notch) through a
    *~ 1. pass-through for a clean single outlet.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Wire cutoff Hz into inlet 1, resonance (0-1) into inlet 2.
    Output from {prefix}_out_l / {prefix}_out_r outlet 0.
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
        # svf~ outlet 3 = notch
        patchline(f"{p}_l", 3, f"{p}_out_l", 0),
        patchline(f"{p}_r", 3, f"{p}_out_r", 0),
    ]
    return (boxes, lines)


def highshelf_filter(id_prefix: str, freq: float = 3000., gain_db: float = 0.) -> tuple:
    """Create a stereo high-shelf EQ filter using biquad~.

    Uses fixed high-shelf biquad coefficients. Wire cutoff and gain updates
    externally via direct biquad~ coefficient messages if needed.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Output from {prefix}_l / {prefix}_r outlet 0.
    """
    p = id_prefix
    import math
    # Compute high-shelf biquad coefficients
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / 44100.0
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / 2.0 * math.sqrt((A + 1 / A) * (1 / 0.7071 - 1) + 2)
    b0 = A * ((A + 1) + (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cos_w0)
    b2 = A * ((A + 1) + (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cos_w0)
    a2 = (A + 1) - (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha
    # Normalize
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


def lowshelf_filter(id_prefix: str, freq: float = 300., gain_db: float = 0.) -> tuple:
    """Create a stereo low-shelf EQ filter using biquad~.

    Uses fixed low-shelf biquad coefficients. Wire cutoff and gain updates
    externally via direct biquad~ coefficient messages if needed.

    Wire audio into {prefix}_l / {prefix}_r inlet 0.
    Output from {prefix}_l / {prefix}_r outlet 0.
    """
    p = id_prefix
    import math
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / 44100.0
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / 2.0 * math.sqrt((A + 1 / A) * (1 / 0.7071 - 1) + 2)
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


def compressor(id_prefix: str) -> tuple:
    """Create a log-domain stereo compressor.

    Signal flow per channel:
      input -> abs~ -> slide~ (attack/release) -> ampdb~ (linear to dB) ->
      - threshold -> * (1 - 1/ratio) -> clip~ 0 inf -> -~ 0 (negate gain reduction) ->
      dbtoa~ -> *~ input

    Wire audio L/R into {prefix}_abs_l / {prefix}_abs_r inlet 0.
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


def noise_source(id_prefix: str, color: str = "white") -> tuple:
    """Create a noise generator.

    Colors:
    - "white": noise~, flat spectrum
    - "pink": noise~ filtered through onepole~ 0.95, approximates -3dB/oct rolloff

    Raises ValueError for unknown colors.
    Output from {prefix}_noise outlet 0 (white) or {prefix}_lp outlet 0 (pink).
    """
    p = id_prefix
    if color == "white":
        boxes = [
            newobj(f"{p}_noise", "noise~", numinlets=0, numoutlets=1,
                   outlettype=["signal"], patching_rect=[30, 120, 50, 20]),
        ]
        return (boxes, [])
    elif color == "pink":
        boxes = [
            newobj(f"{p}_noise", "noise~", numinlets=0, numoutlets=1,
                   outlettype=["signal"], patching_rect=[30, 120, 50, 20]),
            newobj(f"{p}_lp", "onepole~ 0.95", numinlets=2, numoutlets=1,
                   outlettype=["signal"], patching_rect=[30, 150, 90, 20]),
        ]
        lines = [
            patchline(f"{p}_noise", 0, f"{p}_lp", 0),
        ]
        return (boxes, lines)
    else:
        raise ValueError(f"Unknown noise color {color!r}. Choose from: white, pink")


def tempo_sync(id_prefix: str, division: float = 1.0) -> tuple:
    """Read Live transport tempo and compute a time value for a given beat division.

    Uses the transport object to get BPM as a float, then computes:
      delay_ms = (60000 / bpm) * division
      rate_hz  = bpm / (60.0 * division)

    division=1.0 means one beat, 0.5=eighth note, 2.0=half note, etc.

    Wire {prefix}_bpm outlet 0 to downstream objects that need BPM.
    {prefix}_delay outlet 0 gives delay time in ms.
    {prefix}_rate outlet 0 gives LFO rate in Hz.
    """
    p = id_prefix
    boxes = [
        # transport outputs tempo, time signature, etc. as a list
        newobj(f"{p}_transport", "transport", numinlets=1, numoutlets=4,
               outlettype=["", "", "", ""],
               patching_rect=[30, 90, 70, 20]),
        # unpack the transport output: tempo is outlet 0 (float)
        newobj(f"{p}_bpm", "f", numinlets=2, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 120, 30, 20]),
        # Compute delay ms: expr 60000.0 / $f1 * division
        newobj(f"{p}_delay", f"expr 60000.0 / $f1 * {division}",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 150, 160, 20]),
        # Compute LFO rate Hz: expr $f1 / (60.0 * division)
        newobj(f"{p}_rate", f"expr $f1 / (60.0 * {division})",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 180, 160, 20]),
    ]
    lines = [
        # transport outlet 0 (tempo) -> bpm float box
        patchline(f"{p}_transport", 0, f"{p}_bpm", 0),
        # bpm -> delay expr and rate expr
        patchline(f"{p}_bpm", 0, f"{p}_delay", 0),
        patchline(f"{p}_bpm", 0, f"{p}_rate", 0),
    ]
    return (boxes, lines)


def live_remote(id_prefix: str) -> tuple:
    """Create a live.remote~ object for sample-accurate parameter control.

    Wire parameter value into inlet 0, parameter ID into inlet 1,
    ramp time into inlet 2.
    Output from {prefix}_remote outlet 0 (signal).
    """
    boxes = [
        newobj(f"{id_prefix}_remote", "live.remote~", numinlets=3,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 90, 20]),
    ]
    return (boxes, [])


def live_param_signal(id_prefix: str) -> tuple:
    """Create a live.param~ object that outputs a parameter value as signal.

    Inlet 0 accepts parameter messages.
    Outlet 0 is the signal output, outlet 1 is the raw value.
    """
    boxes = [
        newobj(f"{id_prefix}_param", "live.param~", numinlets=1,
               numoutlets=2, outlettype=["signal", ""],
               patching_rect=[30, 120, 80, 20]),
    ]
    return (boxes, [])


def adsr_envelope(id_prefix: str, *, attack_ms: float = 10,
                  decay_ms: float = 100, sustain: float = 0.7,
                  release_ms: float = 200) -> tuple:
    """Create a live.adsr~ envelope generator.

    Wire note-on/off into inlet 0. Inlets 1-4 set attack, decay, sustain,
    release in real time.
    Outlet 0 is the envelope signal, outlet 1 is the retrigger signal.
    """
    boxes = [
        newobj(f"{id_prefix}_adsr",
               f"live.adsr~ {attack_ms} {decay_ms} {sustain} {release_ms}",
               numinlets=5, numoutlets=4,
               outlettype=["signal", "signal", "", ""],
               patching_rect=[30, 120, 180, 20]),
    ]
    return (boxes, [])


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


# -- MIDI DSP blocks --

def gate_expander(id_prefix):
    """Stereo noise gate with threshold detection.

    Signal flow per channel: input -> abs~ -> slide~ -> >~ threshold -> *~ original
    The >~ output (0 or 1) multiplies the original signal to gate it.
    Inlet 0/1: audio L/R, inlet via >~ objects: threshold (float).
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


def sidechain_detect(id_prefix):
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


def sample_and_hold(id_prefix):
    """Sample-and-hold modulation source.

    noise~ feeds sah~ signal input. Trigger input comes via sah~ inlet.
    """
    boxes = [
        newobj(f"{id_prefix}_noise", "noise~", numinlets=1, numoutlets=1,
               outlettype=["signal"]),
        newobj(f"{id_prefix}_sah", "sah~", numinlets=2, numoutlets=1,
               outlettype=["signal"]),
    ]
    lines = [
        patchline(f"{id_prefix}_noise", 0, f"{id_prefix}_sah", 0),
    ]
    return (boxes, lines)


def multiband_compressor(id_prefix):
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


def reverb_network(id_prefix, num_combs=4, num_allpasses=2):
    """Schroeder reverb network with parallel combs and series allpasses.

    Mono input, mono output. Comb filters run in parallel, their outputs
    are summed, then passed through a chain of allpass filters.
    """
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


def notein(id_prefix, channel=0):
    """Receive MIDI note messages (pitch, velocity, channel).

    Returns (boxes, lines) with one notein object.
    """
    text = f"notein {channel}" if channel else "notein"
    boxes = [
        newobj(f"{id_prefix}_notein", text, numinlets=1, numoutlets=3,
               outlettype=["", "", ""]),
    ]
    return (boxes, [])


def noteout(id_prefix, channel=0):
    """Send MIDI note messages."""
    text = f"noteout {channel}" if channel else "noteout"
    boxes = [
        newobj(f"{id_prefix}_noteout", text, numinlets=3, numoutlets=0),
    ]
    return (boxes, [])


def ctlin(id_prefix, cc=None, channel=0):
    """Receive MIDI continuous controller messages."""
    parts = ["ctlin"]
    if cc is not None:
        parts.append(str(cc))
        if channel:
            parts.append(str(channel))
    elif channel:
        parts.append("0")  # cc=0 means all
        parts.append(str(channel))
    text = " ".join(parts)
    boxes = [
        newobj(f"{id_prefix}_ctlin", text, numinlets=1, numoutlets=3,
               outlettype=["", "", ""]),
    ]
    return (boxes, [])


def ctlout(id_prefix, cc=1, channel=1):
    """Send MIDI continuous controller messages."""
    boxes = [
        newobj(f"{id_prefix}_ctlout", f"ctlout {cc} {channel}",
               numinlets=3, numoutlets=0),
    ]
    return (boxes, [])


def velocity_curve(id_prefix, curve="linear"):
    """Remap MIDI velocity with a curve function.

    Curves: linear, compress, expand, soft, hard.
    Input: velocity 0-127, Output: remapped velocity 0-127.
    """
    curves = {
        "linear": None,  # pass through, no expr needed
        "compress": "expr pow($f1 / 127.\\, 0.5) * 127.",
        "expand": "expr pow($f1 / 127.\\, 2.0) * 127.",
        "soft": "expr pow($f1 / 127.\\, 0.3) * 127.",
        "hard": "expr pow($f1 / 127.\\, 3.0) * 127.",
    }
    if curve not in curves:
        raise ValueError(f"Unknown curve: {curve!r}, expected one of {list(curves)}")

    boxes = []
    lines = []

    if curve == "linear":
        # Pass through -- just a clip for safety
        boxes.append(
            newobj(f"{id_prefix}_clip", "clip 0 127", numinlets=3, numoutlets=1,
                   outlettype=[""]),
        )
    else:
        boxes.append(
            newobj(f"{id_prefix}_expr", curves[curve], numinlets=1, numoutlets=1,
                   outlettype=[""]),
        )
        boxes.append(
            newobj(f"{id_prefix}_clip", "clip 0 127", numinlets=3, numoutlets=1,
                   outlettype=[""]),
        )
        lines.append(
            patchline(f"{id_prefix}_expr", 0, f"{id_prefix}_clip", 0),
        )

    return (boxes, lines)


def transpose(id_prefix, semitones=0):
    """Transpose MIDI pitch by semitones with 0-127 clamping."""
    boxes = [
        newobj(f"{id_prefix}_add", f"+ {semitones}", numinlets=2, numoutlets=1,
               outlettype=[""]),
        newobj(f"{id_prefix}_clip", "clip 0 127", numinlets=3, numoutlets=1,
               outlettype=[""]),
    ]
    lines = [
        patchline(f"{id_prefix}_add", 0, f"{id_prefix}_clip", 0),
    ]
    return (boxes, lines)


def midi_thru(id_prefix):
    """Raw MIDI byte passthrough (midiin -> midiout)."""
    boxes = [
        newobj(f"{id_prefix}_midiin", "midiin", numinlets=1, numoutlets=1,
               outlettype=[""]),
        newobj(f"{id_prefix}_midiout", "midiout", numinlets=1, numoutlets=0),
    ]
    lines = [
        patchline(f"{id_prefix}_midiin", 0, f"{id_prefix}_midiout", 0),
    ]
    return (boxes, lines)


def wavetable_osc(id_prefix: str) -> tuple:
    """Create a wavetable~ oscillator.

    wavetable~ inlets: 0=signal/freq, 1=wavetable-number, 2=position.
    Wire frequency into {prefix}_wt inlet 0.
    Wire wavetable index into {prefix}_wt inlet 1.
    Wire position into {prefix}_wt inlet 2.
    Output from {prefix}_wt outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_wt", "wavetable~", numinlets=3, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[30, 120, 80, 20]),
    ]
    return (boxes, [])


def buffer_load(id_prefix: str, buffer_name: str, size: int = 1024) -> tuple:
    """Create a buffer~ for wavetable storage.

    buffer~ is self-contained. Send read/set messages to inlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_buf", f"buffer~ {buffer_name} {size}",
               numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 60, 120, 20]),
    ]
    return (boxes, [])


def arpeggiator(id_prefix: str, mode: str = "up") -> tuple:
    """Create an arpeggiator using arpeggiate and makenote.

    Modes: up, down, up_down, random, as_played.
    Wire chord notes into {prefix}_arp inlet 0.
    Wire rate (ms) into {prefix}_arp inlet 1.
    Wire duration into {prefix}_make inlet 1.
    Output pitch from {prefix}_make outlet 0, velocity outlet 1.
    """
    valid_modes = ("up", "down", "up_down", "random", "as_played",
                   "converge", "diverge", "sweep")
    if mode not in valid_modes:
        raise ValueError(f"Unknown arpeggiator mode {mode!r}. Choose from: {valid_modes}")

    p = id_prefix
    boxes = [
        newobj(f"{p}_arp", f"arpeggiate {mode}", numinlets=2, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 120, 100, 20]),
        newobj(f"{p}_make", "makenote 100 100", numinlets=3, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 160, 100, 20]),
    ]
    lines = [
        patchline(f"{p}_arp", 0, f"{p}_make", 0),
        patchline(f"{p}_arp", 1, f"{p}_make", 2),
    ]
    return (boxes, lines)


def chord(id_prefix: str, intervals: list = None) -> tuple:
    """Transpose MIDI pitch into a chord using + objects for each interval.

    Default intervals=[4, 7] gives a major triad (root, maj3rd, P5th).
    Wire input pitch into each {prefix}_int_{n} inlet 0.
    Output from {prefix}_int_{n} outlet 0 for each interval.
    """
    if intervals is None:
        intervals = [4, 7]

    p = id_prefix
    boxes = []
    lines = []

    for i, semitones in enumerate(intervals):
        boxes.append(
            newobj(f"{p}_int_{i}", f"+ {semitones}", numinlets=2, numoutlets=1,
                   outlettype=[""],
                   patching_rect=[30 + i * 80, 120, 50, 20])
        )

    return (boxes, lines)


def pitch_quantize(id_prefix: str, scale: str = "chromatic") -> tuple:
    """Quantize MIDI pitch to a musical scale using the scale Max object.

    Scales: chromatic, major, minor, pentatonic, dorian.
    Wire pitch into {prefix}_scale inlet 0.
    Output quantized pitch from {prefix}_scale outlet 0.
    """
    valid_scales = ("chromatic", "major", "minor", "pentatonic", "dorian")
    if scale not in valid_scales:
        raise ValueError(f"Unknown scale {scale!r}. Choose from: {valid_scales}")

    p = id_prefix
    boxes = [
        newobj(f"{p}_scale", f"scale {scale}", numinlets=1, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 120, 100, 20]),
    ]
    return (boxes, [])


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


def fdn_reverb(id_prefix: str, num_delays: int = 8) -> tuple:
    """Feedback delay network reverb with prime delay times.

    Uses N tapin~/tapout~ pairs at prime delay times (47,53,59,61,67,71,73,79ms).
    All tapout~ outputs are summed with a +~ chain.

    Wire audio into each {prefix}_tapin_{n} inlet 0.
    Output from {prefix}_sum outlet 0 (or {prefix}_tapout_0 if N=1).
    """
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

    if num_delays == 1:
        # No summing needed for a single delay
        return (boxes, lines)

    # Sum all tapout outputs with a +~ chain
    for i in range(num_delays - 1):
        boxes.append(newobj(f"{p}_add_{i}", "+~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30 + i * 60, 200, 30, 20]))

    # First adder: tapout_0 + tapout_1
    lines.append(patchline(f"{p}_tapout_0", 0, f"{p}_add_0", 0))
    lines.append(patchline(f"{p}_tapout_1", 0, f"{p}_add_0", 1))

    prev = f"{p}_add_0"
    for i in range(2, num_delays):
        adder = f"{p}_add_{i - 1}"
        lines.append(patchline(prev, 0, adder, 0))
        lines.append(patchline(f"{p}_tapout_{i}", 0, adder, 1))
        prev = adder

    # Rename last adder to _sum for a consistent output name
    boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                        outlettype=["signal"],
                        patching_rect=[30, 240, 40, 20]))
    lines.append(patchline(prev, 0, f"{p}_sum", 0))

    return (boxes, lines)


def spectral_gate(id_prefix: str, threshold: float = 0.01,
                  fade_time: float = 10) -> tuple:
    """Spectral gate using pfft~ pointing to spectral_gate_sub.maxpat.

    Wire audio into {prefix}_pfft inlet 0.
    Wire threshold into {prefix}_pfft inlet 1.
    Output from {prefix}_pfft outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pfft", f"pfft~ spectral_gate_sub.maxpat 1024 4",
               numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[30, 120, 200, 20]),
    ]
    return (boxes, [])


def spectral_gate_subpatcher(threshold: float = 0.01) -> dict:
    """Return a dict representing the pfft~ subpatcher JSON for spectral gating.

    The subpatcher contains fftin~, fftout~, and threshold-based magnitude gating.
    """
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 600, 400],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": [
                {"box": {"id": "sp_fftin", "maxclass": "newobj", "text": "fftin~ 1",
                         "numinlets": 0, "numoutlets": 2,
                         "outlettype": ["signal", "signal"],
                         "patching_rect": [30, 30, 70, 20]}},
                {"box": {"id": "sp_cartopol", "maxclass": "newobj",
                         "text": "cartopol~",
                         "numinlets": 2, "numoutlets": 2,
                         "outlettype": ["signal", "signal"],
                         "patching_rect": [30, 70, 70, 20]}},
                {"box": {"id": "sp_thresh", "maxclass": "newobj",
                         "text": f">~ {threshold}",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["signal"],
                         "patching_rect": [30, 110, 70, 20]}},
                {"box": {"id": "sp_gate", "maxclass": "newobj",
                         "text": "*~",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["signal"],
                         "patching_rect": [30, 150, 30, 20]}},
                {"box": {"id": "sp_poltocar", "maxclass": "newobj",
                         "text": "poltocar~",
                         "numinlets": 2, "numoutlets": 2,
                         "outlettype": ["signal", "signal"],
                         "patching_rect": [30, 200, 70, 20]}},
                {"box": {"id": "sp_fftout", "maxclass": "newobj",
                         "text": "fftout~ 1",
                         "numinlets": 2, "numoutlets": 0,
                         "patching_rect": [30, 250, 70, 20]}},
            ],
            "lines": [
                {"patchline": {"source": ["sp_fftin", 0], "destination": ["sp_cartopol", 0]}},
                {"patchline": {"source": ["sp_fftin", 1], "destination": ["sp_cartopol", 1]}},
                {"patchline": {"source": ["sp_cartopol", 0], "destination": ["sp_thresh", 0]}},
                {"patchline": {"source": ["sp_cartopol", 0], "destination": ["sp_gate", 0]}},
                {"patchline": {"source": ["sp_thresh", 0], "destination": ["sp_gate", 1]}},
                {"patchline": {"source": ["sp_gate", 0], "destination": ["sp_poltocar", 0]}},
                {"patchline": {"source": ["sp_cartopol", 1], "destination": ["sp_poltocar", 1]}},
                {"patchline": {"source": ["sp_poltocar", 0], "destination": ["sp_fftout", 0]}},
                {"patchline": {"source": ["sp_poltocar", 1], "destination": ["sp_fftout", 1]}},
            ],
        }
    }


def vocoder(id_prefix: str, num_bands: int = 16) -> tuple:
    """N-band vocoder: carrier analysis + modulator filtering.

    For each band:
      - A bandpass_filter instance analyzes the carrier
      - An envelope_follower tracks the carrier band level
      - The modulator passes through a bandpass_filter, then gets multiplied
        by the carrier envelope

    Wire carrier into each {prefix}_car_bp_{n}_l inlet 0.
    Wire modulator into each {prefix}_mod_bp_{n}_l inlet 0.
    Each band output comes from {prefix}_out_{n} outlet 0.
    """
    p = id_prefix
    all_boxes = []
    all_lines = []

    for i in range(num_bands):
        # Carrier analysis: bandpass
        car_bp_boxes, car_bp_lines = bandpass_filter(f"{p}_car_bp_{i}")
        # Carrier envelope follower (mono, use L channel)
        env_boxes, env_lines = envelope_follower(f"{p}_env_{i}")
        # Modulator bandpass
        mod_bp_boxes, mod_bp_lines = bandpass_filter(f"{p}_mod_bp_{i}")
        # Multiply modulator by carrier envelope
        out_box = newobj(f"{p}_out_{i}", "*~", numinlets=2, numoutlets=1,
                         outlettype=["signal"],
                         patching_rect=[30 + i * 60, 400, 30, 20])

        all_boxes.extend(car_bp_boxes + env_boxes + mod_bp_boxes + [out_box])
        all_lines.extend(car_bp_lines + env_lines + mod_bp_lines)

        # Wire carrier BP (L) -> envelope follower
        all_lines.append(patchline(f"{p}_car_bp_{i}_out_l", 0, f"{p}_env_{i}_abs", 0))
        # Wire envelope -> out multiplier inlet 1
        all_lines.append(patchline(f"{p}_env_{i}_slide", 0, f"{p}_out_{i}", 1))
        # Wire modulator BP (L) -> out multiplier inlet 0
        all_lines.append(patchline(f"{p}_mod_bp_{i}_out_l", 0, f"{p}_out_{i}", 0))

    return (all_boxes, all_lines)


def mc_expand(id_prefix: str, channels: int = 8) -> tuple:
    """Expand stereo to N-channel using mc.pack~.

    Wire stereo signals into {prefix}_pack inlet 0 and 1.
    Output MC signal from {prefix}_pack outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pack", f"mc.pack~ {channels}", numinlets=channels,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 80, 20]),
    ]
    return (boxes, [])


def mc_collapse(id_prefix: str, channels: int = 8) -> tuple:
    """Collapse N-channel MC signal to stereo using mc.unpack~ and summing.

    Wire MC signal into {prefix}_unpack inlet 0.
    Output stereo L/R from {prefix}_sum_l / {prefix}_sum_r outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_unpack", f"mc.unpack~ {channels}", numinlets=1,
               numoutlets=channels, outlettype=["signal"] * channels,
               patching_rect=[30, 120, 100, 20]),
    ]
    lines = []

    # Sum even-indexed channels to L, odd to R
    l_channels = list(range(0, channels, 2))
    r_channels = list(range(1, channels, 2))

    for side, ch_list in (("l", l_channels), ("r", r_channels)):
        if len(ch_list) == 1:
            boxes.append(newobj(f"{p}_sum_{side}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 200, 40, 20]))
            lines.append(patchline(f"{p}_unpack", ch_list[0], f"{p}_sum_{side}", 0))
        else:
            # Build a +~ summing chain
            for j, ch in enumerate(ch_list):
                if j == 0:
                    boxes.append(newobj(f"{p}_add_{side}_0", "+~", numinlets=2,
                                        numoutlets=1, outlettype=["signal"],
                                        patching_rect=[30, 200, 30, 20]))
                    lines.append(patchline(f"{p}_unpack", ch_list[0], f"{p}_add_{side}_0", 0))
                    lines.append(patchline(f"{p}_unpack", ch_list[1], f"{p}_add_{side}_0", 1))
                elif j >= 2:
                    adder_id = f"{p}_add_{side}_{j - 1}"
                    boxes.append(newobj(adder_id, "+~", numinlets=2, numoutlets=1,
                                        outlettype=["signal"],
                                        patching_rect=[30, 200 + j * 30, 30, 20]))
                    lines.append(patchline(f"{p}_add_{side}_{j - 2}", 0, adder_id, 0))
                    lines.append(patchline(f"{p}_unpack", ch, adder_id, 1))

            last_adder = f"{p}_add_{side}_{max(len(ch_list) - 2, 0)}"
            boxes.append(newobj(f"{p}_sum_{side}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 300, 40, 20]))
            lines.append(patchline(last_adder, 0, f"{p}_sum_{side}", 0))

    return (boxes, lines)


def note_expression_decode(id_prefix: str) -> tuple:
    """Decode MIDI note expression: pitch, velocity, channel, aftertouch, pitchbend.

    Creates:
      - notein for pitch/velocity/channel
      - polytouchin for per-note aftertouch
      - pitchin for pitchbend per channel

    Output pitch from {prefix}_notein outlet 0.
    Output velocity from {prefix}_notein outlet 1.
    Output channel from {prefix}_notein outlet 2.
    Output aftertouch from {prefix}_polytouch outlet 0.
    Output pitchbend from {prefix}_pitchin outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_notein", "notein", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[30, 120, 60, 20]),
        newobj(f"{p}_polytouch", "polytouchin", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[120, 120, 80, 20]),
        newobj(f"{p}_pitchin", "pitchin", numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[220, 120, 60, 20]),
    ]
    return (boxes, [])


# -- #22-32, #40, #44-46 additions --

def transport_lfo(id_prefix: str, division: str = '1/4',
                  shape: str = 'sine') -> tuple:
    """LFO synced to Live transport tempo.

    Reads BPM via transport, converts to Hz for the given beat division,
    drives cycle~ (sine), phasor~ (saw), or rect~ (square).

    division: '1/8', '1/4', '1/2', '1/1'
    shape: 'sine', 'saw', 'square'
    Output from {prefix}_osc outlet 0.
    """
    division_map = {
        '1/8':  0.5,
        '1/4':  1.0,
        '1/2':  2.0,
        '1/1':  4.0,
    }
    valid_shapes = ('sine', 'saw', 'square')
    if division not in division_map:
        raise ValueError(f"Unknown division {division!r}. "
                         f"Choose from: {', '.join(division_map)}")
    if shape not in valid_shapes:
        raise ValueError(f"Unknown shape {shape!r}. "
                         f"Choose from: {', '.join(valid_shapes)}")

    div_beats = division_map[division]
    p = id_prefix

    # transport -> bpm float -> rate Hz
    boxes = [
        newobj(f"{p}_transport", "transport", numinlets=1, numoutlets=4,
               outlettype=["", "", "", ""],
               patching_rect=[30, 60, 70, 20]),
        newobj(f"{p}_bpm", "f", numinlets=2, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 90, 30, 20]),
        # rate Hz = bpm / (60 * div_beats)
        newobj(f"{p}_rate", f"expr $f1 / (60.0 * {div_beats})",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 120, 160, 20]),
    ]
    lines = [
        patchline(f"{p}_transport", 0, f"{p}_bpm", 0),
        patchline(f"{p}_bpm", 0, f"{p}_rate", 0),
    ]

    osc_map = {
        'sine':   ("cycle~", 2, 2, ["signal", "signal"]),
        'saw':    ("phasor~", 2, 1, ["signal"]),
        'square': ("rect~", 2, 1, ["signal"]),
    }
    osc_text, osc_inlets, osc_outlets, osc_types = osc_map[shape]
    boxes.append(newobj(f"{p}_osc", osc_text,
                        numinlets=osc_inlets, numoutlets=osc_outlets,
                        outlettype=osc_types,
                        patching_rect=[30, 160, 60, 20]))
    lines.append(patchline(f"{p}_rate", 0, f"{p}_osc", 0))

    return (boxes, lines)


def pitchbend_in(id_prefix: str, semitones: int = 2) -> tuple:
    """Receive MIDI pitchbend and scale to semitone range.

    bendin outputs raw 0-16383. We shift to -8192..8191, divide by 8192,
    multiply by semitones to get a semitone-range float.

    Output scaled semitone value from {prefix}_scale outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_bendin", "bendin", numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 120, 60, 20]),
        newobj(f"{p}_scale", f"expr ($i1 - 8192) / 8192.0 * {semitones}",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 160, 200, 20]),
    ]
    lines = [
        patchline(f"{p}_bendin", 0, f"{p}_scale", 0),
    ]
    return (boxes, lines)


def modwheel_in(id_prefix: str) -> tuple:
    """Receive MIDI mod wheel (CC 1), output 0-127.

    Output from {prefix}_ctlin outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_ctlin", "ctlin 1", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[30, 120, 60, 20]),
    ]
    return (boxes, [])


def aftertouch_in(id_prefix: str) -> tuple:
    """Receive MIDI channel aftertouch, output 0-127.

    Output from {prefix}_touchin outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_touchin", "touchin", numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 120, 60, 20]),
    ]
    return (boxes, [])


def xfade_matrix(id_prefix: str, sources: int = 4) -> tuple:
    """N-input crossfade matrix.

    Control (float 0.0 to N-1) sets crossfade position across sources.
    Each source weight = max(0, 1 - abs(control - i)) computed with expr~.
    All weighted sources summed with +~ chain.

    Wire signals into {prefix}_mul_{i} inlet 0 for each source i.
    Wire control float into {prefix}_ctrl inlet 0.
    Output from {prefix}_sum outlet 0.
    """
    p = id_prefix
    boxes = []
    lines = []

    # Control signal input: convert float to signal via sig~... but we must
    # avoid sig~ (cold-start silence). Use pack + line~ for smooth control.
    boxes.append(newobj(f"{p}_ctrl", "pack f 10", numinlets=2, numoutlets=1,
                        outlettype=[""],
                        patching_rect=[30, 60, 80, 20]))
    boxes.append(newobj(f"{p}_ctrl_line", "line~", numinlets=2, numoutlets=1,
                        outlettype=["signal"],
                        patching_rect=[30, 90, 50, 20]))
    lines.append(patchline(f"{p}_ctrl", 0, f"{p}_ctrl_line", 0))

    for i in range(sources):
        # weight = max(0, 1 - abs(ctrl - i))
        boxes.append(newobj(f"{p}_wt_{i}",
                            f"expr~ (1. - fabs($v1 - {float(i)})) > 0. ? "
                            f"(1. - fabs($v1 - {float(i)})) : 0.",
                            numinlets=1, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30 + i * 130, 130, 220, 20]))
        lines.append(patchline(f"{p}_ctrl_line", 0, f"{p}_wt_{i}", 0))

        # multiply source by weight
        boxes.append(newobj(f"{p}_mul_{i}", "*~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30 + i * 130, 170, 30, 20]))
        lines.append(patchline(f"{p}_wt_{i}", 0, f"{p}_mul_{i}", 1))

    # Sum all weighted sources with +~ chain
    if sources == 1:
        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 220, 40, 20]))
        lines.append(patchline(f"{p}_mul_0", 0, f"{p}_sum", 0))
    else:
        boxes.append(newobj(f"{p}_add_0", "+~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 220, 30, 20]))
        lines.append(patchline(f"{p}_mul_0", 0, f"{p}_add_0", 0))
        lines.append(patchline(f"{p}_mul_1", 0, f"{p}_add_0", 1))
        prev = f"{p}_add_0"
        for i in range(2, sources):
            adder = f"{p}_add_{i - 1}"
            boxes.append(newobj(adder, "+~", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 220 + (i - 1) * 30, 30, 20]))
            lines.append(patchline(prev, 0, adder, 0))
            lines.append(patchline(f"{p}_mul_{i}", 0, adder, 1))
            prev = adder

        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 220 + (sources - 1) * 30, 40, 20]))
        lines.append(patchline(prev, 0, f"{p}_sum", 0))

    return (boxes, lines)


def midi_learn_chain(id_prefix: str, param_name: str) -> tuple:
    """MIDI learn chain: captures next incoming CC and routes it to a named send.

    A toggle controls learn mode. When learn=1, the next CC number is stored
    and used to filter subsequent ctlin messages, passing the value to
    a send object named param_name.

    Wire toggle state into {prefix}_learn inlet 0.
    """
    p = id_prefix
    boxes = [
        # Listen to all CCs on all channels
        newobj(f"{p}_ctlin", "ctlin", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[30, 60, 50, 20]),
        # Learn mode toggle
        newobj(f"{p}_learn", "toggle", numinlets=1, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 90, 20, 20]),
        # Gate: only pass CC number when learn is on
        newobj(f"{p}_gate", "gate", numinlets=2, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 120, 40, 20]),
        # Store the learned CC number
        newobj(f"{p}_cc_store", "i", numinlets=2, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 150, 20, 20]),
        # Route: only pass CC value when it matches stored CC number
        newobj(f"{p}_route", "route", numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 180, 50, 20]),
        # Send the value to the named parameter
        newobj(f"{p}_send", f"send {param_name}", numinlets=1, numoutlets=0,
               patching_rect=[30, 210, 100, 20]),
    ]
    lines = [
        # CC number (outlet 1 of ctlin) -> gate inlet 0
        patchline(f"{p}_ctlin", 1, f"{p}_gate", 0),
        # Learn toggle -> gate enable inlet 1
        patchline(f"{p}_learn", 0, f"{p}_gate", 1),
        # When learn active, captured CC number -> store
        patchline(f"{p}_gate", 0, f"{p}_cc_store", 0),
        # Stored CC number -> route selector
        patchline(f"{p}_cc_store", 0, f"{p}_route", 0),
        # Route outlet 0 (matched CC value) -> send
        patchline(f"{p}_route", 0, f"{p}_send", 0),
    ]
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


def program_change_in(id_prefix: str, channel: int = 0) -> tuple:
    """Receive MIDI program change messages.

    channel=0 listens on all channels.
    Output program number (0-127) from {prefix}_pgmin outlet 0.
    """
    p = id_prefix
    text = f"pgmin {channel}" if channel else "pgmin"
    boxes = [
        newobj(f"{p}_pgmin", text, numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 120, 60, 20]),
    ]
    return (boxes, [])


def bank_select_in(id_prefix: str, channel: int = 0) -> tuple:
    """Receive MIDI bank select (CC 0 MSB + CC 32 LSB), output combined bank number.

    Bank number = MSB * 128 + LSB.
    Output from {prefix}_bank outlet 0.
    """
    p = id_prefix
    boxes = [
        # CC 0 = bank MSB
        newobj(f"{p}_msb", "ctlin 0", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[30, 60, 60, 20]),
        # CC 32 = bank LSB
        newobj(f"{p}_lsb", "ctlin 32", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[130, 60, 65, 20]),
        # Store MSB
        newobj(f"{p}_msb_store", "i", numinlets=2, numoutlets=1,
               outlettype=[""],
               patching_rect=[30, 100, 20, 20]),
        # Combine: bank = MSB * 128 + LSB
        newobj(f"{p}_bank", "expr $i1 * 128 + $i2",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 140, 160, 20]),
    ]
    lines = [
        # MSB value -> store
        patchline(f"{p}_msb", 0, f"{p}_msb_store", 0),
        # MSB store -> bank expr inlet 0
        patchline(f"{p}_msb_store", 0, f"{p}_bank", 0),
        # LSB value -> bank expr inlet 1
        patchline(f"{p}_lsb", 0, f"{p}_bank", 1),
    ]
    return (boxes, lines)


def sample_and_hold_triggered(id_prefix: str) -> tuple:
    """Sample-and-hold with external trigger signal.

    inlet 0: audio to sample, inlet 1: trigger signal (>0 triggers hold).
    Output from {prefix}_sah outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_sah", "samphold~", numinlets=2, numoutlets=1,
               outlettype=["signal"],
               patching_rect=[30, 120, 70, 20]),
    ]
    return (boxes, [])


def bitcrusher(id_prefix: str, bits: int = 8,
               rate_reduction: int = 1) -> tuple:
    """Bit depth and sample rate reduction.

    Uses degrade~ for combined bit/rate reduction: inlet 1 = sr factor,
    inlet 2 = bit depth.

    Wire audio into {prefix}_degrade inlet 0.
    Output from {prefix}_degrade outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_degrade", f"degrade~ {rate_reduction} {bits}",
               numinlets=3, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 120, 20]),
    ]
    return (boxes, [])


def poly_voices(id_prefix: str, num_voices: int = 4,
                patch_name: str = 'voice') -> tuple:
    """Polyphonic voice allocator using poly~.

    poly~ handles voice stealing and MIDI note routing.
    Wire MIDI note pitch into {prefix}_poly inlet 0.
    Wire velocity into {prefix}_poly inlet 1.
    Output from {prefix}_poly outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_poly", f"poly~ {patch_name} {num_voices}",
               numinlets=2, numoutlets=3,
               outlettype=["signal", "signal", ""],
               patching_rect=[30, 120, 160, 20]),
    ]
    return (boxes, [])


def spectral_crossover(id_prefix: str, bands: int = 4) -> tuple:
    """Spectral crossover using pfft~ pointing to spectral_crossover_sub.maxpat.

    Wire audio into {prefix}_pfft inlet 0.
    Output from {prefix}_pfft outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pfft", "pfft~ spectral_crossover_sub.maxpat 1024 4",
               numinlets=1, numoutlets=bands,
               outlettype=["signal"] * bands,
               patching_rect=[30, 120, 240, 20]),
    ]
    return (boxes, [])


def spectral_crossover_subpatcher(bands: int = 4) -> dict:
    """Return the pfft~ subpatcher dict for spectral band splitting.

    Splits the input spectrum into N equal-width frequency bands using
    fftin~, bin-range routing logic, and fftout~.
    """
    sub_boxes = [
        {"box": {"id": "sc_fftin", "maxclass": "newobj", "text": "fftin~ 1",
                 "numinlets": 0, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 30, 70, 20]}},
        {"box": {"id": "sc_cartopol", "maxclass": "newobj", "text": "cartopol~",
                 "numinlets": 2, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 70, 70, 20]}},
    ]
    for i in range(bands):
        sub_boxes.append({
            "box": {
                "id": f"sc_fftout_{i}", "maxclass": "newobj",
                "text": f"fftout~ {i + 1}",
                "numinlets": 2, "numoutlets": 0,
                "patching_rect": [30 + i * 80, 200, 70, 20],
            }
        })

    sub_lines = [
        {"patchline": {"source": ["sc_fftin", 0], "destination": ["sc_cartopol", 0]}},
        {"patchline": {"source": ["sc_fftin", 1], "destination": ["sc_cartopol", 1]}},
    ]

    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 600, 400],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": sub_boxes,
            "lines": sub_lines,
        }
    }


def grain_cloud(id_prefix: str, buffer_name: str,
                num_voices: int = 4) -> tuple:
    """Granular cloud using groove~ for multi-voice playback.

    Creates a buffer~ for the source audio and N groove~ instances.
    Wire record trigger into {prefix}_buf inlet 0.
    Output from {prefix}_sum outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_buf", f"buffer~ {buffer_name} 10000",
               numinlets=1, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 30, 140, 20]),
    ]
    lines = []

    for i in range(num_voices):
        boxes.append(newobj(f"{p}_groove_{i}", f"groove~ {buffer_name}",
                            numinlets=3, numoutlets=2,
                            outlettype=["signal", "signal"],
                            patching_rect=[30 + i * 100, 90, 100, 20]))

    # Sum all groove~ outputs with a +~ chain
    if num_voices == 1:
        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 150, 40, 20]))
        lines.append(patchline(f"{p}_groove_0", 0, f"{p}_sum", 0))
    else:
        boxes.append(newobj(f"{p}_add_0", "+~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 150, 30, 20]))
        lines.append(patchline(f"{p}_groove_0", 0, f"{p}_add_0", 0))
        lines.append(patchline(f"{p}_groove_1", 0, f"{p}_add_0", 1))
        prev = f"{p}_add_0"
        for i in range(2, num_voices):
            adder = f"{p}_add_{i - 1}"
            boxes.append(newobj(adder, "+~", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 150 + (i - 1) * 30, 30, 20]))
            lines.append(patchline(prev, 0, adder, 0))
            lines.append(patchline(f"{p}_groove_{i}", 0, adder, 1))
            prev = adder

        boxes.append(newobj(f"{p}_sum", "*~ 1.", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30, 150 + (num_voices - 1) * 30, 40, 20]))
        lines.append(patchline(prev, 0, f"{p}_sum", 0))

    return (boxes, lines)


def auto_gain(id_prefix: str) -> tuple:
    """RMS-based auto loudness normalization.

    Uses env~ to measure RMS, then *~ to apply makeup gain.
    Wire audio into {prefix}_mul inlet 0.
    Output from {prefix}_mul outlet 0.
    Feed gain CV into {prefix}_mul inlet 1.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_env", "env~ 1024 512",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 100, 20]),
        newobj(f"{p}_div", "/ 1.",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 70, 60, 20]),
        newobj(f"{p}_ftom", "atodb",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 110, 60, 20]),
        newobj(f"{p}_gain", "dbtoa",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 150, 60, 20]),
        newobj(f"{p}_mul", "*~ 1.",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 190, 60, 20]),
    ]
    lines = [
        patchline(f"{p}_env", 0, f"{p}_div", 1),
        patchline(f"{p}_div", 0, f"{p}_ftom", 0),
        patchline(f"{p}_ftom", 0, f"{p}_gain", 0),
        patchline(f"{p}_gain", 0, f"{p}_mul", 1),
    ]
    return (boxes, lines)


def midi_clock_out(id_prefix: str) -> tuple:
    """Send MIDI clock (24 ppqn) synced to Live transport.

    Uses transport to get tempo, formats clock bytes via midiformat, sends via midiout.
    Self-drives from the Live transport, no wiring needed.
    Output MIDI clock on the default MIDI out.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_transport", "transport",
               numinlets=1, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 30, 80, 20]),
        newobj(f"{p}_tempo", "/ 2.5",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 70, 60, 20]),
        newobj(f"{p}_metro", "metro 1",
               numinlets=2, numoutlets=1, outlettype=["bang"],
               patching_rect=[30, 110, 70, 20]),
        newobj(f"{p}_clockbyte", "i 248",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 150, 50, 20]),
        newobj(f"{p}_midiout", "midiout",
               numinlets=1, numoutlets=0,
               patching_rect=[30, 190, 60, 20]),
    ]
    lines = [
        patchline(f"{p}_transport", 0, f"{p}_tempo", 0),
        patchline(f"{p}_tempo", 0, f"{p}_metro", 1),
        patchline(f"{p}_metro", 0, f"{p}_clockbyte", 0),
        patchline(f"{p}_clockbyte", 0, f"{p}_midiout", 0),
    ]
    return (boxes, lines)


def macromap(id_prefix: str, param_name: str, macro_num: int = 1) -> tuple:
    """Maps a device parameter to a Live macro knob.

    Uses live.remote~ to connect param_name to macro macro_num (1-8).
    Wire parameter value into {prefix}_remote inlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_remote", f"live.remote~ macro{macro_num}",
               numinlets=1, numoutlets=0,
               patching_rect=[30, 30, 160, 20]),
        newobj(f"{p}_param", f"live.param~ {param_name}",
               numinlets=1, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 70, 160, 20]),
    ]
    lines = [
        patchline(f"{p}_param", 0, f"{p}_remote", 0),
    ]
    return (boxes, lines)


def stft_phase_vocoder(id_prefix: str) -> tuple:
    """Phase vocoder using pfft~ for time-stretch/pitch-shift.

    Points to phase_vocoder_sub.maxpat as the subpatcher.
    Wire audio into {prefix}_pfft inlet 0.
    Output from {prefix}_pfft outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_pfft", "pfft~ phase_vocoder_sub.maxpat 1024 4",
               numinlets=1, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 30, 260, 20]),
    ]
    return (boxes, [])


def phase_vocoder_subpatcher() -> dict:
    """Return the pfft~ subpatcher dict for a phase vocoder.

    Contains fftin~, fftout~, and phase accumulation objects for time-stretch.
    """
    sub_boxes = [
        {"box": {"id": "pv_fftin", "maxclass": "newobj", "text": "fftin~ 1",
                 "numinlets": 0, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 30, 70, 20]}},
        {"box": {"id": "pv_cartopol", "maxclass": "newobj", "text": "cartopol~",
                 "numinlets": 2, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 80, 80, 20]}},
        {"box": {"id": "pv_phase_acc", "maxclass": "newobj", "text": "+~",
                 "numinlets": 2, "numoutlets": 1,
                 "outlettype": ["signal"],
                 "patching_rect": [120, 80, 30, 20]}},
        {"box": {"id": "pv_poltocar", "maxclass": "newobj", "text": "poltocar~",
                 "numinlets": 2, "numoutlets": 2,
                 "outlettype": ["signal", "signal"],
                 "patching_rect": [30, 140, 80, 20]}},
        {"box": {"id": "pv_fftout", "maxclass": "newobj", "text": "fftout~ 1",
                 "numinlets": 2, "numoutlets": 0,
                 "patching_rect": [30, 200, 70, 20]}},
    ]
    sub_lines = [
        {"patchline": {"source": ["pv_fftin", 0], "destination": ["pv_cartopol", 0]}},
        {"patchline": {"source": ["pv_fftin", 1], "destination": ["pv_cartopol", 1]}},
        {"patchline": {"source": ["pv_cartopol", 0], "destination": ["pv_poltocar", 0]}},
        {"patchline": {"source": ["pv_cartopol", 1], "destination": ["pv_phase_acc", 0]}},
        {"patchline": {"source": ["pv_phase_acc", 0], "destination": ["pv_poltocar", 1]}},
        {"patchline": {"source": ["pv_poltocar", 0], "destination": ["pv_fftout", 0]}},
        {"patchline": {"source": ["pv_poltocar", 1], "destination": ["pv_fftout", 1]}},
    ]
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 400, 300],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": sub_boxes,
            "lines": sub_lines,
        }
    }


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


def morphing_lfo(id_prefix: str) -> tuple:
    """LFO blending between sine, triangle, square, and saw shapes.

    Blend param 0.0-3.0 selects waveform region.
    Uses cycle~ for sine, phasor~ derived shapes, selector~ for switching.
    Wire rate (Hz) into {prefix}_phasor inlet 0.
    Wire blend (0.0-3.0) into {prefix}_sel inlet 0.
    Output from {prefix}_sel outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_phasor", "phasor~ 1.",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 30, 80, 20]),
        newobj(f"{p}_sine", "cycle~ 1.",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 70, 70, 20]),
        newobj(f"{p}_tri", "expr~ ($v1 < 0.5) ? (4.*$v1 - 1.) : (3. - 4.*$v1)",
               numinlets=1, numoutlets=1, outlettype=["signal"],
               patching_rect=[120, 70, 300, 20]),
        newobj(f"{p}_sq", "expr~ ($v1 < 0.5) ? -1. : 1.",
               numinlets=1, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 110, 180, 20]),
        newobj(f"{p}_saw", "expr~ 2.*$v1 - 1.",
               numinlets=1, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 150, 120, 20]),
        newobj(f"{p}_sel", "selector~ 4 1",
               numinlets=5, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 200, 100, 20]),
    ]
    lines = [
        patchline(f"{p}_phasor", 0, f"{p}_tri", 0),
        patchline(f"{p}_phasor", 0, f"{p}_sq", 0),
        patchline(f"{p}_phasor", 0, f"{p}_saw", 0),
        patchline(f"{p}_sine", 0, f"{p}_sel", 1),
        patchline(f"{p}_tri", 0, f"{p}_sel", 2),
        patchline(f"{p}_sq", 0, f"{p}_sel", 3),
        patchline(f"{p}_saw", 0, f"{p}_sel", 4),
    ]
    return (boxes, lines)


def midi_clock_in(id_prefix: str) -> tuple:
    """Detect incoming MIDI clock and output BPM as a float.

    Counts 24 ppqn clock pulses via midiin + midiparse, outputs BPM.
    Output BPM float from {prefix}_bpm_scale outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_midiin", "midiin",
               numinlets=0, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 60, 20]),
        newobj(f"{p}_midiparse", "midiparse",
               numinlets=1, numoutlets=7, outlettype=[""] * 7,
               patching_rect=[30, 70, 80, 20]),
        newobj(f"{p}_clockdet", "select 248",
               numinlets=1, numoutlets=2, outlettype=["bang", ""],
               patching_rect=[30, 110, 80, 20]),
        newobj(f"{p}_counter", "counter 0 23",
               numinlets=1, numoutlets=3, outlettype=["", "bang", ""],
               patching_rect=[30, 150, 100, 20]),
        newobj(f"{p}_timer", "timer",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 190, 60, 20]),
        newobj(f"{p}_bpm", "/ 1000.",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 230, 60, 20]),
        newobj(f"{p}_bpm_scale", "* 60.",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 270, 60, 20]),
    ]
    lines = [
        patchline(f"{p}_midiin", 0, f"{p}_midiparse", 0),
        patchline(f"{p}_midiparse", 0, f"{p}_clockdet", 0),
        patchline(f"{p}_clockdet", 0, f"{p}_counter", 0),
        patchline(f"{p}_counter", 1, f"{p}_timer", 1),
        patchline(f"{p}_clockdet", 0, f"{p}_timer", 0),
        patchline(f"{p}_timer", 0, f"{p}_bpm", 0),
        patchline(f"{p}_bpm", 0, f"{p}_bpm_scale", 0),
    ]
    return (boxes, lines)


def sidechain_routing(id_prefix: str) -> tuple:
    """Route external audio as sidechain via second plugin~ input.

    Creates plugin~ with 2 stereo pairs (4 inlets), routes inlet 2 as sidechain.
    Wire main audio into {prefix}_plugin inlets 0-1.
    Sidechain signal available from {prefix}_plugin outlet 2 (right) / 3 (left).
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_plugin", "plugin~ 2",
               numinlets=2, numoutlets=4,
               outlettype=["signal", "signal", "signal", "signal"],
               patching_rect=[30, 30, 80, 20]),
    ]
    return (boxes, [])


def random_walk(id_prefix: str, step_size: float = 0.01) -> tuple:
    """Brownian motion smooth random CV signal.

    Uses noise~ scaled by step_size, accumulated via +~, clamped 0-1, smoothed.
    Output from {prefix}_slide outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_noise", "noise~",
               numinlets=0, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 30, 60, 20]),
        newobj(f"{p}_scale", f"*~ {step_size}",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 70, 80, 20]),
        newobj(f"{p}_acc", "+~",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 110, 30, 20]),
        newobj(f"{p}_clip", "clip~ 0. 1.",
               numinlets=3, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 150, 80, 20]),
        newobj(f"{p}_slide", "slide~ 1000. 1000.",
               numinlets=3, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 190, 120, 20]),
    ]
    lines = [
        patchline(f"{p}_noise", 0, f"{p}_scale", 0),
        patchline(f"{p}_scale", 0, f"{p}_acc", 0),
        patchline(f"{p}_acc", 0, f"{p}_clip", 0),
        patchline(f"{p}_clip", 0, f"{p}_acc", 1),
        patchline(f"{p}_clip", 0, f"{p}_slide", 0),
    ]
    return (boxes, lines)


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


def matrix_mixer(id_prefix: str, inputs: int = 4, outputs: int = 4) -> tuple:
    """NxN gain routing matrix.

    Creates inputs*outputs *~ gain cells and +~ summing chains per output.
    Wire each input signal into {prefix}_in_{i}_gain_{j} inlet 0.
    Output from {prefix}_out_{j} outlet 0.
    """
    p = id_prefix
    boxes, lines = _nxn_signal_sum(
        p, inputs, outputs,
        cell_fmt=lambda i, j: f"{p}_in_{i}_gain_{j}",
        adder_prefix=f"{p}_add",
        out_fmt=lambda j: f"{p}_out_{j}",
    )
    return (boxes, lines)


def cv_recorder(id_prefix: str, buffer_size: int = 4410) -> tuple:
    """Record and playback CV to a table object.

    Uses record~ and play~ for CV storage/retrieval.
    Wire CV into {prefix}_rec inlet 0, trigger record via {prefix}_rec inlet 1.
    Trigger playback via {prefix}_play inlet 0.
    Output from {prefix}_play outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_table", f"buffer~ {p}_cv_buf {buffer_size}",
               numinlets=1, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 30, 160, 20]),
        newobj(f"{p}_rec", f"record~ {p}_cv_buf",
               numinlets=2, numoutlets=1, outlettype=["bang"],
               patching_rect=[30, 70, 120, 20]),
        newobj(f"{p}_play", f"play~ {p}_cv_buf",
               numinlets=2, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 110, 120, 20]),
    ]
    return (boxes, [])


def quantize_time(id_prefix: str, division: str = '1/16') -> tuple:
    """Snap time to beat grid using transport quantize.

    Uses transport object with quantize set to division.
    Output quantized beat position from {prefix}_transport outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_transport", f"transport @quantize {division}",
               numinlets=1, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 30, 200, 20]),
        newobj(f"{p}_quant", f"quantize {division}",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 70, 120, 20]),
    ]
    lines = [
        patchline(f"{p}_transport", 0, f"{p}_quant", 0),
    ]
    return (boxes, lines)


def macro_modulation_matrix(id_prefix: str, sources: int = 4,
                             targets: int = 4) -> tuple:
    """N sources x N targets modulation matrix with per-cell gain.

    Sources (LFOs/envs) feed *~ gain cells, summed into target outputs.
    Wire source signal i into {prefix}_src_{i}_to_{j} inlet 0 for each target j.
    Output for target j from {prefix}_tgt_{j} outlet 0.
    """
    p = id_prefix
    boxes, lines = _nxn_signal_sum(
        p, sources, targets,
        cell_fmt=lambda i, j: f"{p}_src_{i}_to_{j}",
        adder_prefix=f"{p}_sum",
        out_fmt=lambda j: f"{p}_tgt_{j}",
    )
    return (boxes, lines)


def analog_oscillator_bank(id_prefix: str, num_oscs: int = 4) -> tuple:
    """Multiple phasor~ oscillators with per-voice detuning for unison thickness.

    Wire base frequency (Hz) into {prefix}_detune_{i} inlet 0 for each osc.
    Output summed signal from {prefix}_sum outlet 0.
    """
    p = id_prefix
    boxes = []
    lines = []

    total_detune = 20.0
    for i in range(num_oscs):
        if num_oscs > 1:
            offset = total_detune * (i / (num_oscs - 1) - 0.5)
        else:
            offset = 0.0
        osc_id = f"{p}_osc_{i}"
        add_id = f"{p}_detune_{i}"
        boxes.append(newobj(add_id, f"expr $f1 + {offset:.4f}",
                            numinlets=1, numoutlets=1, outlettype=[""],
                            patching_rect=[30 + i * 100, 30, 120, 20]))
        boxes.append(newobj(osc_id, "phasor~",
                            numinlets=2, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30 + i * 100, 70, 60, 20]))
        lines.append(patchline(add_id, 0, osc_id, 0))

    if num_oscs == 1:
        boxes.append(newobj(f"{p}_sum", "*~ 1.",
                            numinlets=2, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30, 130, 50, 20]))
        lines.append(patchline(f"{p}_osc_0", 0, f"{p}_sum", 0))
    else:
        adder_id = f"{p}_add_0"
        boxes.append(newobj(adder_id, "+~",
                            numinlets=2, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30, 130, 30, 20]))
        lines.append(patchline(f"{p}_osc_0", 0, adder_id, 0))
        lines.append(patchline(f"{p}_osc_1", 0, adder_id, 1))
        prev = adder_id
        for i in range(2, num_oscs):
            next_adder = f"{p}_add_{i - 1}"
            boxes.append(newobj(next_adder, "+~",
                                numinlets=2, numoutlets=1, outlettype=["signal"],
                                patching_rect=[30, 130 + (i - 1) * 30, 30, 20]))
            lines.append(patchline(prev, 0, next_adder, 0))
            lines.append(patchline(f"{p}_osc_{i}", 0, next_adder, 1))
            prev = next_adder
        boxes.append(newobj(f"{p}_sum", "*~ 1.",
                            numinlets=2, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30, 130 + (num_oscs - 1) * 30, 50, 20]))
        lines.append(patchline(prev, 0, f"{p}_sum", 0))

    return (boxes, lines)


def lfsr_generator(id_prefix: str, poly_order: int = 8) -> tuple:
    """Linear feedback shift register for pseudo-random sequences.

    Uses counter + bitshift operations with expr/bitand for LFSR taps.
    Trigger via {prefix}_clock inlet 0.
    Output bit from {prefix}_bit outlet 0.
    """
    p = id_prefix
    mask = (1 << poly_order) - 1
    boxes = [
        newobj(f"{p}_reg", f"i {mask}",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 80, 20]),
        newobj(f"{p}_bit", "bitand 1",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 70, 70, 20]),
        newobj(f"{p}_feedback", "expr ($i1 ^ ($i1 >> 4)) & 1",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 110, 200, 20]),
        newobj(f"{p}_shift", f"expr (($i1 >> 1) | ($i2 << {poly_order - 1})) & {mask}",
               numinlets=2, numoutlets=1, outlettype=[""],
               patching_rect=[30, 150, 320, 20]),
        newobj(f"{p}_clock", "t b b",
               numinlets=1, numoutlets=2, outlettype=["bang", "bang"],
               patching_rect=[30, 190, 50, 20]),
    ]
    lines = [
        patchline(f"{p}_reg", 0, f"{p}_bit", 0),
        patchline(f"{p}_reg", 0, f"{p}_feedback", 0),
        patchline(f"{p}_reg", 0, f"{p}_shift", 0),
        patchline(f"{p}_feedback", 0, f"{p}_shift", 1),
        patchline(f"{p}_clock", 0, f"{p}_reg", 1),
        patchline(f"{p}_shift", 0, f"{p}_reg", 0),
        patchline(f"{p}_clock", 1, f"{p}_bit", 0),
    ]
    return (boxes, lines)


def cv_smooth_lag(id_prefix: str, lag_ms: float = 50,
                  mode: str = 'exponential') -> tuple:
    """Extended CV smoothing with selectable mode.

    exponential: slide~ with lag_ms-derived rise/fall times.
    linear: line~ based smoothing.

    Wire CV into {prefix}_smoother inlet 0.
    Output from {prefix}_smoother outlet 0.
    """
    p = id_prefix
    if mode == 'exponential':
        boxes = [
            newobj(f"{p}_smoother", f"slide~ {lag_ms} {lag_ms}",
                   numinlets=3, numoutlets=1, outlettype=["signal"],
                   patching_rect=[30, 30, 140, 20]),
        ]
    elif mode == 'linear':
        boxes = [
            newobj(f"{p}_smoother", f"line~ {lag_ms}",
                   numinlets=2, numoutlets=1, outlettype=["signal"],
                   patching_rect=[30, 30, 100, 20]),
        ]
    else:
        raise ValueError(f"cv_smooth_lag: unknown mode '{mode}', expected 'exponential' or 'linear'")
    return (boxes, [])
