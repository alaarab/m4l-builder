"""MIDI processing."""

from ..objects import newobj, patchline


def notein(id_prefix: str, channel: int = 0) -> tuple:
    """Receive MIDI note messages (pitch, velocity, channel).

    Returns (boxes, lines) with one notein object.
    """
    text = f"notein {channel}" if channel else "notein"
    boxes = [
        newobj(f"{id_prefix}_notein", text, numinlets=1, numoutlets=3,
               outlettype=["int", "int", "int"]),
    ]
    return (boxes, [])


def noteout(id_prefix: str, channel: int = 0) -> tuple:
    """Send MIDI note messages."""
    text = f"noteout {channel}" if channel else "noteout"
    boxes = [
        newobj(f"{id_prefix}_noteout", text, numinlets=3, numoutlets=0),
    ]
    return (boxes, [])


def ctlin(id_prefix: str, cc: int = None, channel: int = 0) -> tuple:
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


def ctlout(id_prefix: str, cc: int = 1, channel: int = 1) -> tuple:
    """Send MIDI continuous controller messages."""
    boxes = [
        newobj(f"{id_prefix}_ctlout", f"ctlout {cc} {channel}",
               numinlets=3, numoutlets=0),
    ]
    return (boxes, [])


def velocity_curve(id_prefix: str, curve: str = "linear") -> tuple:
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
        expr_text = curves[curve]
        assert expr_text is not None  # non-linear curves always define an expr
        boxes.append(
            newobj(f"{id_prefix}_expr", expr_text, numinlets=1, numoutlets=1,
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


def transpose(id_prefix: str, semitones: int = 0) -> tuple:
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


def midi_thru(id_prefix: str) -> tuple:
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
    lines: list = []

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


def midi_tool_io(id_prefix: str) -> tuple:
    """Create the live.miditool.in / live.miditool.out pair for a MIDI Tool.

    Required scaffolding for Live 12 MIDI Generator / Transformation devices
    (the MidiGenerator / MidiTransformation device types). `{prefix}_in` carries
    the notes dictionary on outlet 0 and the context dictionary (grid,
    selection, scale, root) on outlet 1; route your note processing from there
    into `{prefix}_out` inlet 0 to write notes back to the clip. A bare
    `{prefix}_in` outlet 0 -> `{prefix}_out` inlet 0 connection is a valid
    pass-through transformation.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_in", "live.miditool.in", numinlets=1, numoutlets=2,
               outlettype=["", ""], patching_rect=[30, 30, 110, 22]),
        newobj(f"{p}_out", "live.miditool.out", numinlets=1, numoutlets=0,
               patching_rect=[30, 260, 110, 22]),
    ]
    return (boxes, [])


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


def midi_clock_out(id_prefix: str) -> tuple:
    """Send MIDI clock (24 ppqn) synced to Live transport.

    Uses transport to get tempo, formats clock bytes via midiformat, sends via midiout.
    Self-drives from the Live transport, no wiring needed.
    Output MIDI clock on the default MIDI out.
    """
    p = id_prefix
    boxes = [
        # transport is 2-in/9-out; tempo is outlet 4 (maxdiff-validated shape).
        newobj(f"{p}_transport", "transport",
               numinlets=2, numoutlets=9,
               outlettype=["int", "int", "float", "float", "float", "", "int",
                           "float", ""],
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
        patchline(f"{p}_transport", 4, f"{p}_tempo", 0),
        patchline(f"{p}_tempo", 0, f"{p}_metro", 1),
        patchline(f"{p}_metro", 0, f"{p}_clockbyte", 0),
        patchline(f"{p}_clockbyte", 0, f"{p}_midiout", 0),
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


def midi_channel_filter(id_prefix: str, channel: int = 1) -> tuple:
    """Route MIDI input to a specific channel.

    Uses midiin to capture raw MIDI, midiparse to split it into
    components, and sel to filter by channel number.

    Raw MIDI from {prefix}_midiin outlet 0 goes through midiparse.
    Channel number from midiparse outlet 6 is matched by sel.
    Matched output from {prefix}_sel outlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_midiin", "midiin",
               numinlets=0, numoutlets=2, outlettype=["int", "int"],
               patching_rect=[30, 30, 50, 20]),
        newobj(f"{p}_midiparse", "midiparse",
               numinlets=1, numoutlets=7,
               outlettype=["", "", "", "", "", "", ""],
               patching_rect=[30, 70, 70, 20]),
        newobj(f"{p}_sel", f"sel {channel}",
               numinlets=1, numoutlets=2, outlettype=["bang", ""],
               patching_rect=[30, 110, 60, 20]),
    ]
    lines = [
        patchline(f"{p}_midiin", 0, f"{p}_midiparse", 0),
        patchline(f"{p}_midiparse", 6, f"{p}_sel", 0),
    ]
    return (boxes, lines)
