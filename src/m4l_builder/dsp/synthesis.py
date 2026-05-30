"""Oscillators and sound sources."""

from ..objects import newobj, patchline
from ._common import _signal_sum_chain


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


def poly_voices(id_prefix: str, num_voices: int = 4,
                patch_name: str = 'voice') -> tuple:
    """Polyphonic voice allocator using poly~.

    poly~ handles voice stealing and MIDI note routing.
    Wire MIDI note pitch into {prefix}_poly inlet 0.
    Wire velocity into {prefix}_poly inlet 1.
    Output from {prefix}_poly outlet 0.
    """
    if num_voices < 1:
        raise ValueError(f"poly_voices num_voices must be >= 1, got {num_voices}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_poly", f"poly~ {patch_name} {num_voices}",
               numinlets=2, numoutlets=3,
               outlettype=["signal", "signal", ""],
               patching_rect=[30, 120, 160, 20]),
    ]
    return (boxes, [])


def grain_cloud(id_prefix: str, buffer_name: str,
                num_voices: int = 4) -> tuple:
    """Granular cloud using groove~ for multi-voice playback.

    Creates a buffer~ for the source audio and N groove~ instances.
    Wire record trigger into {prefix}_buf inlet 0.
    Output from {prefix}_sum outlet 0.
    """
    if num_voices < 1:
        raise ValueError(f"grain_cloud num_voices must be >= 1, got {num_voices}")
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

    source_ids = [f"{p}_groove_{i}" for i in range(num_voices)]
    sum_boxes, sum_lines = _signal_sum_chain(p, source_ids)
    boxes.extend(sum_boxes)
    lines.extend(sum_lines)

    return (boxes, lines)


def analog_oscillator_bank(id_prefix: str, num_oscs: int = 4) -> tuple:
    """Multiple phasor~ oscillators with per-voice detuning for unison thickness.

    Wire base frequency (Hz) into {prefix}_detune_{i} inlet 0 for each osc.
    Output summed signal from {prefix}_sum outlet 0.
    """
    if num_oscs < 1:
        raise ValueError(f"analog_oscillator_bank num_oscs must be >= 1, got {num_oscs}")
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

    source_ids = [f"{p}_osc_{i}" for i in range(num_oscs)]
    sum_boxes, sum_lines = _signal_sum_chain(p, source_ids)
    boxes.extend(sum_boxes)
    lines.extend(sum_lines)

    return (boxes, lines)


def groove_player(id_prefix: str, buf_name: str) -> tuple:
    """Create a buffer~ + groove~ pair for sample playback.

    groove~ reads from the named buffer~. A patchline connects the
    buffer~ second outlet (size update) to groove~ first inlet.

    Trigger playback via {prefix}_groove inlet 0 (1 = play, 0 = stop).
    Audio output from {prefix}_groove outlets 0 and 1.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_buffer", f"buffer~ {buf_name}",
               numinlets=1, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 30, 120, 20]),
        newobj(f"{p}_groove", f"groove~ {buf_name}",
               numinlets=2, numoutlets=2, outlettype=["signal", "signal"],
               patching_rect=[30, 70, 120, 20]),
    ]
    lines = [
        patchline(f"{p}_buffer", 1, f"{p}_groove", 0),
    ]
    return (boxes, lines)
