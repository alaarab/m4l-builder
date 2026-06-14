"""Data storage and scripting."""

from ..objects import newobj, patchline


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


def loadbang(id_prefix: str) -> tuple:
    """Create a loadbang object that fires a bang on device load.

    Output from {prefix}_loadbang outlet 0.
    """
    boxes = [
        newobj(f"{id_prefix}_loadbang", "loadbang",
               numinlets=0, numoutlets=1, outlettype=["bang"],
               patching_rect=[30, 30, 60, 20]),
    ]
    return (boxes, [])


def coll_store(id_prefix: str, name: str) -> tuple:
    """Create a coll object for indexed data storage.

    Wire messages into {prefix}_coll inlet 0.
    Output from {prefix}_coll outlets 0 and 1.
    """
    boxes = [
        newobj(f"{id_prefix}_coll", f"coll {name}",
               numinlets=2, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 30, 80, 20]),
    ]
    return (boxes, [])


def dict_store(id_prefix: str, name: str) -> tuple:
    """Create a dict object for key-value data storage.

    Wire messages into {prefix}_dict inlet 0.
    Output from {prefix}_dict outlet 0.
    """
    boxes = [
        newobj(f"{id_prefix}_dict", f"dict {name}",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 80, 20]),
    ]
    return (boxes, [])


def pattr_system(id_prefix: str) -> tuple:
    """Create an autopattr + pattrstorage pair for parameter save/recall.

    autopattr collects all named UI objects automatically.
    pattrstorage saves and recalls their states as presets.

    Wire preset index into {prefix}_pattrstorage inlet 0.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_autopattr", "autopattr",
               numinlets=1, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 60, 20]),
        newobj(f"{p}_pattrstorage", f"pattrstorage {p}_storage",
               numinlets=2, numoutlets=2, outlettype=["", ""],
               patching_rect=[30, 70, 160, 20]),
    ]
    lines = [
        patchline(f"{p}_autopattr", 0, f"{p}_pattrstorage", 0),
    ]
    return (boxes, lines)


def gen_codebox(id_prefix: str, gen_code: str, numinlets: int = 1,
                numoutlets: int = 1, outlettype: list = None) -> tuple:
    """Create a gen~ object with embedded codebox code.

    gen~ is Max's DSP codegen environment. The gen_code string is stored
    as a "code" attribute on the box, letting you write inline DSP
    without a separate .gendsp file.

    Wire audio into {prefix}_gen inlet 0.
    Output from {prefix}_gen outlets 0..N.

    PITFALL (verified live in Live 12, 2026-06): a gen~ codebox that DEFINES a
    user function — any ``name(args) { ... return ... }`` — fails to compile and
    the object outputs pure SILENCE (no console error surfaces in the M4L run).
    This held even for a single trivial single-return function. Inline the math
    instead (branch on a constant into a pre-initialized variable); see the
    Heat flagship kernel for the 7-character shaper inlined this way. Symptom to
    watch for: device passes audio with a bare/passthrough kernel but silences
    the moment a function definition is added.
    """
    if outlettype is None:
        outlettype = ["signal"] * numoutlets
    box = newobj(f"{id_prefix}_gen", "gen~",
                 numinlets=numinlets, numoutlets=numoutlets,
                 outlettype=outlettype,
                 patching_rect=[30, 30, 120, 20])
    box["box"]["code"] = gen_code
    return ([box], [])
