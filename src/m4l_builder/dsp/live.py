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
        # transport only reports when banged: poll it so tempo changes track
        newobj(f"{p}_poll", "metro 100 @active 1", numinlets=2, numoutlets=1,
               outlettype=["bang"],
               patching_rect=[30, 60, 110, 20]),
        # transport is 2-in/9-out; tempo is outlet 4 (maxdiff-validated shape)
        newobj(f"{p}_transport", "transport", numinlets=2, numoutlets=9,
               outlettype=["int", "int", "float", "float", "float", "", "int",
                           "float", ""],
               patching_rect=[30, 90, 70, 20]),
        newobj(f"{p}_bpm", "f", numinlets=2, numoutlets=1,
               outlettype=["float"],
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
        patchline(f"{p}_poll", 0, f"{p}_transport", 0),
        # transport outlet 4 (tempo) -> bpm float box
        patchline(f"{p}_transport", 4, f"{p}_bpm", 0),
        # bpm -> delay expr and rate expr
        patchline(f"{p}_bpm", 0, f"{p}_delay", 0),
        patchline(f"{p}_bpm", 0, f"{p}_rate", 0),
    ]
    return (boxes, lines)


def live_remote(id_prefix: str, *, normalized: int = 0) -> tuple:
    """Create a live.remote~ object for sample-accurate parameter control.

    Corpus-verbatim shape (lfo-cluster obj-42): **2 inlets** — value signal
    into inlet 0, ``id <n>`` into inlet 1 (RIGHT, always via ``deferlow``);
    ``id 0`` detaches. One outlet (message): reports ``mapped 0|1``.
    ``normalized=0`` (the corpus default) takes values in the target param's
    NATIVE units — scale in gen from the mapper's min/max reads;
    ``normalized=1`` maps input 0..1 across the target's full range.
    ``_persistence 1`` restores the mapping on save/load.
    """
    boxes = [
        newobj(f"{id_prefix}_remote", "live.remote~", numinlets=2,
               numoutlets=1, outlettype=[""],
               patching_rect=[30, 120, 90, 20],
               saved_object_attributes={
                   "_persistence": 1, "normalized": normalized,
                   "smoothing": 1.0}),
    ]
    return (boxes, [])


def live_modulate(id_prefix: str, *, depth: float = 1.0) -> tuple:
    """Create a live.modulate~ object — Live's grey modulation-ring output path.

    Corpus-verbatim shape (lfo-cluster obj-33): 2 inlets — modulation signal
    (0..1, relative) into inlet 0, ``id <n>`` into inlet 1 (RIGHT, via
    ``deferlow``); one message outlet reporting ``mapped 0|1``. Unlike
    live.remote~ the user keeps control of the param; modulation is additive
    around the dial position.
    """
    boxes = [
        newobj(f"{id_prefix}_mod", "live.modulate~", numinlets=2,
               numoutlets=1, outlettype=[""],
               patching_rect=[30, 160, 90, 20],
               saved_object_attributes={
                   "_persistence": 1, "depth": depth, "smoothing": 1.0}),
    ]
    return (boxes, [])


def retargetable_param_sink(id_prefix: str, *, default_mode: int = 0,
                            normalized: int = 0) -> tuple:
    """The verbatim lfo-cluster retarget sink: one ``id <n>`` stream drives
    EITHER live.remote~ (mode 0) or live.modulate~ (mode 1), hot-swappable.

    Wiring (grounded in lfo-cluster ``_extracted/04_patch_4.json``):
      ``{p}_reg``    ``zl.reg id 0``  — caller wires the mapper js outlet 0 here
                     (inlet **1** stores without emitting; a bang on inlet 0
                     re-emits — the mode switch uses that to re-route);
      ``{p}_gate``   ``gate 2 <default_mode+1>`` — outlet 0 = remote path,
                     outlet 1 = modulate path;
      each path: ``t b l`` — the ``l`` (fires FIRST) goes ``deferlow`` → its
      sink's RIGHT inlet (attach); the ``b`` fires ``id 0`` → the OTHER path's
      deferlow (cross-detach — one target, one sink at a time);
      both sink outlets → ``route mapped`` → ``sel 0`` = forced-unmap detect
      (``{p}_unmapped`` bangs when the host releases the mapping — wire it back
      to the mapper js ``extunmap``).

    Caller contract: value signal → ``{p}_remote`` inlet 0 and ``{p}_mod``
    inlet 0; mode int (0=remote, 1=modulate) → ``{p}_mode`` inlet 0; mapper
    ``id <n>`` lists → ``{p}_reg`` inlet 1 AND a bang → ``{p}_reg`` inlet 0
    (or send the list to inlet 0 directly to store+emit in one step).
    """
    p = id_prefix
    remote_boxes, _ = live_remote(p, normalized=normalized)
    mod_boxes, _ = live_modulate(p)
    boxes = [
        newobj(f"{p}_reg", "zl.reg id 0", numinlets=2, numoutlets=2,
               outlettype=["", ""], patching_rect=[30, 30, 80, 20]),
        newobj(f"{p}_mode", "+ 1", numinlets=2, numoutlets=1,
               outlettype=["int"], patching_rect=[150, 30, 40, 20]),
        newobj(f"{p}_tbi", "t b i", numinlets=1, numoutlets=2,
               outlettype=["bang", "int"], patching_rect=[150, 60, 50, 20]),
        newobj(f"{p}_gate", f"gate 2 {int(default_mode) + 1}", numinlets=2,
               numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 90, 70, 20]),
        newobj(f"{p}_tbl_r", "t b l", numinlets=1, numoutlets=2,
               outlettype=["bang", ""], patching_rect=[30, 120, 50, 20]),
        newobj(f"{p}_tbl_m", "t b l", numinlets=1, numoutlets=2,
               outlettype=["bang", ""], patching_rect=[120, 120, 50, 20]),
        {"box": {
            "id": f"{p}_id0_r", "maxclass": "message", "text": "id 0",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [30, 150, 40, 20]}},
        {"box": {
            "id": f"{p}_id0_m", "maxclass": "message", "text": "id 0",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [120, 150, 40, 20]}},
        newobj(f"{p}_defer_r", "deferlow", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[30, 180, 60, 20]),
        newobj(f"{p}_defer_m", "deferlow", numinlets=1, numoutlets=1,
               outlettype=[""], patching_rect=[120, 180, 60, 20]),
        *remote_boxes,
        *mod_boxes,
        newobj(f"{p}_route", "route mapped", numinlets=2, numoutlets=2,
               outlettype=["", ""], patching_rect=[30, 250, 90, 20]),
        newobj(f"{p}_unmapped", "sel 0", numinlets=2, numoutlets=2,
               outlettype=["bang", ""], patching_rect=[30, 280, 50, 20]),
    ]
    lines = [
        # stored id list -> gate data inlet
        patchline(f"{p}_reg", 0, f"{p}_gate", 1),
        # mode change: set the gate outlet, then bang zl.reg to re-emit the
        # stored id down the newly selected path (corpus + 1 / t b i)
        patchline(f"{p}_mode", 0, f"{p}_tbi", 0),
        patchline(f"{p}_tbi", 1, f"{p}_gate", 0),
        patchline(f"{p}_tbi", 0, f"{p}_reg", 0),
        # remote path: l (first) -> deferlow -> remote RIGHT inlet;
        # b (second) -> id 0 -> the modulate deferlow (cross-detach)
        patchline(f"{p}_gate", 0, f"{p}_tbl_r", 0),
        patchline(f"{p}_tbl_r", 1, f"{p}_defer_r", 0),
        patchline(f"{p}_tbl_r", 0, f"{p}_id0_m", 0),
        # modulate path: mirror image
        patchline(f"{p}_gate", 1, f"{p}_tbl_m", 0),
        patchline(f"{p}_tbl_m", 1, f"{p}_defer_m", 0),
        patchline(f"{p}_tbl_m", 0, f"{p}_id0_r", 0),
        patchline(f"{p}_id0_r", 0, f"{p}_defer_r", 0),
        patchline(f"{p}_id0_m", 0, f"{p}_defer_m", 0),
        patchline(f"{p}_defer_r", 0, f"{p}_remote", 1),
        patchline(f"{p}_defer_m", 0, f"{p}_mod", 1),
        # forced-unmap detect
        patchline(f"{p}_remote", 0, f"{p}_route", 0),
        patchline(f"{p}_mod", 0, f"{p}_route", 0),
        patchline(f"{p}_route", 0, f"{p}_unmapped", 0),
    ]
    return (boxes, lines)


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
