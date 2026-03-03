"""Reusable DSP building blocks for M4L devices.

Each function returns a (boxes, lines) tuple where boxes is a list of box dicts
and lines is a list of patchline dicts. This makes it easy to compose DSP chains
by extending a device's boxes and lines lists.
"""

from .objects import newobj, patchline


def stereo_io(plugin_id: str = "obj-plugin", plugout_id: str = "obj-plugout",
              plugin_rect: list = None, plugout_rect: list = None) -> tuple:
    """Create plugin~ and plugout~ pair for audio I/O.

    Returns (boxes, lines) with no lines — caller wires the DSP chain.
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
        # don't use sig~ here — starts at 0.0 on load and overrides *~ args, causing silence.
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
    biquad~ 1. -1. 0. -0.9997 0. — biquad~ has 6 inlets (signal + 5 coefficients).
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
    - "tanh": tanh~ — smooth tape-like saturation
    - "overdrive": overdrive~ — tube-like saturation
    - "clip": clip~ -1. 1. — hard clipping (3 inlets: signal, min, max)
    - "degrade": degrade~ — bit/sample rate crush (3 inlets: signal, sr_factor, bit_depth)

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
    selector~ N without an initial arg defaults to input 0 (silence) — always pass initial.
    """
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

    /~ doesn't work for signal/signal in Max — uses !/~ 1. to get the reciprocal
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
    independently and summed — boost one side to tilt.

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
    - "white": noise~ — flat spectrum
    - "pink": noise~ filtered through onepole~ 0.95 — approximates -3dB/oct rolloff

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
