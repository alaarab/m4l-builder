"""Audio I/O and gain stages."""

from ..objects import newobj, patchline


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
