"""Live transport and parameter access."""

from ..objects import newobj, patchline


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
