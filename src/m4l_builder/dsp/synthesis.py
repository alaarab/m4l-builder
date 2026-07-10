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


def slice_voice(id_prefix: str, buffer_name: str, *, channels: int = 2,
                declick_attack_ms: float = 2.0,
                declick_release_ms: float = 5.0) -> tuple:
    """One-shot buffer-subregion player with a de-click envelope.

    A ``play~`` read-head driven by a ``line~`` position ramp (the ramp *is*
    the playback). Trigger one slice by sending a 4-float list
    ``start_ms 0 end_ms dur_ms`` to ``{prefix}_unpack`` inlet 0 -- the same
    shape ``line~`` consumes: jump to start_ms in 0 ms, then ramp to end_ms
    over dur_ms (dur_ms = the slice length in ms gives natural-rate playback;
    a shorter dur pitches the slice up). The list also opens a ``live.adsr~``
    de-click VCA (attack on trigger, release after dur_ms via ``{prefix}_delay``)
    so ``play~``'s read-position jumps don't click.

    No ``sig~`` (lint-banned, and it zeroes gains on load): the position is a
    pure ``line~`` ramp built by the caller (or by the slice engine).

    Audio out: ``{prefix}_vca_l`` / ``{prefix}_vca_r`` outlet 0. A per-trigger
    ``{prefix}_gain`` (``*~ 1.``) sits on the envelope signal — send a float to
    its inlet 1 right before a trigger for per-hit level (accents/ducks);
    untouched it is a bit-exact unity pass.
    """
    if channels not in (1, 2):
        raise ValueError(f"slice_voice channels must be 1 or 2, got {channels}")
    p = id_prefix
    r_outlet = 1 if channels >= 2 else 0
    play_outlettype = ["signal"] * channels
    boxes = [
        newobj(f"{p}_unpack", "unpack 0. 0. 0. 0.",
               numinlets=1, numoutlets=4,
               outlettype=["float", "float", "float", "float"],
               patching_rect=[30, 30, 130, 20]),
        newobj(f"{p}_pack", "pack 0. 0. 0. 0.",
               numinlets=4, numoutlets=1, outlettype=[""],
               patching_rect=[30, 60, 130, 20]),
        newobj(f"{p}_tr", "t l b b", numinlets=1, numoutlets=3,
               outlettype=["", "bang", "bang"],
               patching_rect=[30, 90, 90, 20]),
        newobj(f"{p}_line", "line~", numinlets=2, numoutlets=2,
               outlettype=["signal", "bang"], patching_rect=[30, 120, 50, 20]),
        newobj(f"{p}_play", f"play~ {buffer_name} {channels}",
               numinlets=1, numoutlets=channels, outlettype=play_outlettype,
               patching_rect=[30, 150, 120, 20]),
        newobj(f"{p}_adsr",
               f"live.adsr~ {declick_attack_ms} 0 1 {declick_release_ms}",
               numinlets=5, numoutlets=4,
               outlettype=["signal", "signal", "", ""],
               patching_rect=[180, 90, 150, 20]),
        # per-trigger GAIN on the envelope control signal (scales both
        # channels through the VCAs). Defaults 1. = byte-identical until a
        # host addresses inlet 1 — the hook for seq accent/duck levels.
        newobj(f"{p}_gain", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[180, 120, 50, 20]),
        newobj(f"{p}_open", "t 1", numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[180, 60, 40, 20]),
        newobj(f"{p}_delay", "delay 0", numinlets=2, numoutlets=1,
               outlettype=["bang"], patching_rect=[120, 120, 50, 20]),
        newobj(f"{p}_rel", "t 0", numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[120, 150, 40, 20]),
        newobj(f"{p}_vca_l", "*~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 190, 50, 20]),
        newobj(f"{p}_vca_r", "*~", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[100, 190, 50, 20]),
    ]
    lines = [
        # rebuild the start/0/end/dur list, start (outlet 0) is the hot trigger
        patchline(f"{p}_unpack", 0, f"{p}_pack", 0),
        patchline(f"{p}_unpack", 1, f"{p}_pack", 1),
        patchline(f"{p}_unpack", 2, f"{p}_pack", 2),
        patchline(f"{p}_unpack", 3, f"{p}_pack", 3),
        # dur (outlet 3) also sets the release-delay time (cold inlet)
        patchline(f"{p}_unpack", 3, f"{p}_delay", 1),
        patchline(f"{p}_pack", 0, f"{p}_tr", 0),
        # t l b b fires right->left: start delay, open VCA, then ramp line~
        patchline(f"{p}_tr", 0, f"{p}_line", 0),
        patchline(f"{p}_tr", 1, f"{p}_open", 0),
        patchline(f"{p}_tr", 2, f"{p}_delay", 0),
        patchline(f"{p}_open", 0, f"{p}_adsr", 0),
        patchline(f"{p}_line", 0, f"{p}_play", 0),
        patchline(f"{p}_play", 0, f"{p}_vca_l", 0),
        patchline(f"{p}_play", r_outlet, f"{p}_vca_r", 0),
        patchline(f"{p}_adsr", 0, f"{p}_gain", 0),
        patchline(f"{p}_gain", 0, f"{p}_vca_l", 1),
        patchline(f"{p}_gain", 0, f"{p}_vca_r", 1),
        # ramp done -> release the de-click envelope
        patchline(f"{p}_delay", 0, f"{p}_rel", 0),
        patchline(f"{p}_rel", 0, f"{p}_adsr", 0),
    ]
    return (boxes, lines)


def slice_pool(id_prefix: str, buffer_name: str, num_voices: int = 4,
               **voice_kwargs) -> tuple:
    """Round-robin pool of ``num_voices`` ``slice_voice`` players, summed.

    Send a per-note slice list ``start_ms 0 end_ms dur_ms`` to
    ``{prefix}_in_tr`` inlet 0; the pool advances a ``counter`` and routes the
    list through a ``gate`` to the next voice (round-robin), so overlapping
    slice hits (rolls/stutters) keep their tails instead of choking a single
    voice. Summed stereo output from ``{prefix}_l_sum`` / ``{prefix}_r_sum``
    outlet 0.

    The named ``buffer~`` is NOT created here -- the device owns the single
    shared buffer (loaded by the dropfile and read by the slice display).
    """
    if num_voices < 1:
        raise ValueError(f"slice_pool num_voices must be >= 1, got {num_voices}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_in_tr", "t l b", numinlets=1, numoutlets=2,
               outlettype=["", "bang"], patching_rect=[30, 30, 90, 20]),
        newobj(f"{p}_counter", f"counter 1 {num_voices}",
               numinlets=5, numoutlets=4,
               outlettype=["int", "int", "int", "int"],
               patching_rect=[30, 60, 90, 20]),
        newobj(f"{p}_gate", f"gate {num_voices}",
               numinlets=2, numoutlets=num_voices,
               outlettype=[""] * num_voices, patching_rect=[30, 90, 160, 20]),
    ]
    lines = [
        patchline(f"{p}_in_tr", 1, f"{p}_counter", 0),
        patchline(f"{p}_counter", 0, f"{p}_gate", 0),
        patchline(f"{p}_in_tr", 0, f"{p}_gate", 1),
    ]

    for i in range(num_voices):
        vb, vl = slice_voice(f"{p}_v{i}", buffer_name, **voice_kwargs)
        boxes.extend(vb)
        lines.extend(vl)
        lines.append(patchline(f"{p}_gate", i, f"{p}_v{i}_unpack", 0))

    l_ids = [f"{p}_v{i}_vca_l" for i in range(num_voices)]
    r_ids = [f"{p}_v{i}_vca_r" for i in range(num_voices)]
    l_boxes, l_lines = _signal_sum_chain(f"{p}_l", l_ids)
    r_boxes, r_lines = _signal_sum_chain(f"{p}_r", r_ids)
    boxes.extend(l_boxes)
    boxes.extend(r_boxes)
    lines.extend(l_lines)
    lines.extend(r_lines)

    return (boxes, lines)


def poly_voice_template(id_prefix: str, voices: int = 8) -> tuple:
    """Embedded ``poly~`` voice-allocation instrument core (T36/Q20 — the
    official poly~/thispoly~/adsr~ lesson as one block).

    The embedded voice patcher is the canonical shape:

    - ``in 1`` receives the ``midinote pitch velocity`` pair the host
      sends (poly~ target-routes note-ons to free voices)
    - ``unpack`` splits pitch/velocity; ``mtof`` -> ``cycle~`` is the
      placeholder oscillator (swap the source, keep the envelope contract)
    - velocity 0..127 scales to 0..1 and TRIGGERS ``adsr~``; note-off
      (velocity 0) releases it
    - ``adsr~``'s status outlet drives ``thispoly~`` mute/busy — the voice
      frees itself when the release tail ends (the whole point of the
      lesson: CPU idles at zero for silent voices)

    Host side: wire ``prepend midinote`` -> ``{p}_poly`` inlet 0 from your
    notein pair, and ``{p}_poly`` outlet 0 to the instrument output stage.
    """
    p = id_prefix
    voice = {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 640, 480],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": [
                {"box": {"id": "v_in", "maxclass": "newobj", "text": "in 1",
                         "numinlets": 0, "numoutlets": 1, "outlettype": [""],
                         "patching_rect": [30, 30, 40, 20]}},
                {"box": {"id": "v_unpack", "maxclass": "newobj",
                         "text": "unpack 0 0",
                         "numinlets": 1, "numoutlets": 2,
                         "outlettype": ["int", "int"],
                         "patching_rect": [30, 70, 80, 20]}},
                {"box": {"id": "v_mtof", "maxclass": "newobj", "text": "mtof",
                         "numinlets": 1, "numoutlets": 1, "outlettype": [""],
                         "patching_rect": [30, 110, 50, 20]}},
                {"box": {"id": "v_osc", "maxclass": "newobj", "text": "cycle~",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["signal"],
                         "patching_rect": [30, 150, 60, 20]}},
                {"box": {"id": "v_velscale", "maxclass": "newobj",
                         "text": "/ 127.",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["float"],
                         "patching_rect": [140, 110, 50, 20]}},
                {"box": {"id": "v_adsr", "maxclass": "newobj",
                         "text": "adsr~ 5 80 0.7 200",
                         "numinlets": 5, "numoutlets": 3,
                         "outlettype": ["signal", "signal", ""],
                         "patching_rect": [140, 150, 130, 20]}},
                {"box": {"id": "v_thispoly", "maxclass": "newobj",
                         "text": "thispoly~",
                         "numinlets": 1, "numoutlets": 1,
                         "outlettype": ["int"],
                         "patching_rect": [290, 190, 70, 20]}},
                {"box": {"id": "v_vca", "maxclass": "newobj", "text": "*~",
                         "numinlets": 2, "numoutlets": 1,
                         "outlettype": ["signal"],
                         "patching_rect": [30, 200, 40, 20]}},
                {"box": {"id": "v_out", "maxclass": "newobj", "text": "out~ 1",
                         "numinlets": 1, "numoutlets": 0,
                         "patching_rect": [30, 250, 50, 20]}},
            ],
            "lines": [
                {"patchline": {"source": ["v_in", 0], "destination": ["v_unpack", 0]}},
                {"patchline": {"source": ["v_unpack", 0], "destination": ["v_mtof", 0]}},
                {"patchline": {"source": ["v_mtof", 0], "destination": ["v_osc", 0]}},
                {"patchline": {"source": ["v_unpack", 1], "destination": ["v_velscale", 0]}},
                {"patchline": {"source": ["v_velscale", 0], "destination": ["v_adsr", 0]}},
                {"patchline": {"source": ["v_osc", 0], "destination": ["v_vca", 0]}},
                {"patchline": {"source": ["v_adsr", 0], "destination": ["v_vca", 1]}},
                {"patchline": {"source": ["v_adsr", 2], "destination": ["v_thispoly", 0]}},
                {"patchline": {"source": ["v_vca", 0], "destination": ["v_out", 0]}},
            ],
        }
    }
    box = {
        "box": {
            "id": f"{p}_poly", "maxclass": "newobj",
            "text": f"poly~ {p}_voice.maxpat {voices}",
            "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"],
            "patching_rect": [30, 30, 160, 20],
        }
    }
    # poly~ cannot embed its patcher inline (Live-verified silent on the
    # T23b wrapper) — the voice ships as a .maxpat sidecar; register it:
    # device.register_asset(name, content, asset_type="TEXT", category="js")
    import json as _json
    sidecar = (f"{p}_voice.maxpat", _json.dumps(voice, indent="\t"))
    return ([box], [], sidecar)
