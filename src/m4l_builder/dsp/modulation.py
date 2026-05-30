"""Modulation sources."""

from ..objects import newobj, patchline
from ._common import _nxn_signal_sum


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


def sample_and_hold(id_prefix: str) -> tuple:
    """Sample-and-hold modulation source.

    noise~ feeds sah~ signal input. Trigger input comes via sah~ inlet.
    """
    boxes = [
        newobj(f"{id_prefix}_noise", "noise~", numinlets=0, numoutlets=1,
               outlettype=["signal"]),
        newobj(f"{id_prefix}_sah", "sah~", numinlets=2, numoutlets=1,
               outlettype=["signal"]),
    ]
    lines = [
        patchline(f"{id_prefix}_noise", 0, f"{id_prefix}_sah", 0),
    ]
    return (boxes, lines)


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


def macro_modulation_matrix(id_prefix: str, sources: int = 4,
                             targets: int = 4) -> tuple:
    """N sources x N targets modulation matrix with per-cell gain.

    Sources (LFOs/envs) feed *~ gain cells, summed into target outputs.
    Wire source signal i into {prefix}_src_{i}_to_{j} inlet 0 for each target j.
    Output for target j from {prefix}_tgt_{j} outlet 0.
    """
    if sources < 1:
        raise ValueError(f"macro_modulation_matrix sources must be >= 1, got {sources}")
    if targets < 1:
        raise ValueError(f"macro_modulation_matrix targets must be >= 1, got {targets}")
    p = id_prefix
    boxes, lines = _nxn_signal_sum(
        p, sources, targets,
        cell_fmt=lambda i, j: f"{p}_src_{i}_to_{j}",
        adder_prefix=f"{p}_sum",
        out_fmt=lambda j: f"{p}_tgt_{j}",
    )
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


def scale_range(id_prefix: str, in_lo: float = 0., in_hi: float = 1.,
                out_lo: float = 0., out_hi: float = 1.,
                curve: float = 1.) -> tuple:
    """Create a scale object to map an input range to an output range.

    Optional exponential curve parameter (1.0 = linear).
    Wire input into {prefix}_scale inlet 0.
    Output from {prefix}_scale outlet 0.
    """
    boxes = [
        newobj(f"{id_prefix}_scale",
               f"scale {in_lo} {in_hi} {out_lo} {out_hi} {curve}",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 180, 20]),
    ]
    return (boxes, [])
