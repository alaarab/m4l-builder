"""Max for Live Live API objects: live.object, live.path, live.observer."""

from .objects import newobj, patchline


def _live_path_pair(p, path, obj_text, obj_width=80):
    """Return (boxes, lines) for a live.path + live.object pair."""
    boxes = [
        newobj(f"{p}_path", f"live.path {path}", numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 120, 120, 20]),
        newobj(f"{p}_obj", obj_text, numinlets=1, numoutlets=2,
               outlettype=["", ""],
               patching_rect=[30, 150, obj_width, 20]),
    ]
    lines = [patchline(f"{p}_path", 0, f"{p}_obj", 0)]
    return boxes, lines


def live_object_path(id_prefix: str, path: str = "live_set") -> tuple:
    """Create a live.path + live.object pair for getting/setting properties.

    Send 'get <prop>' or 'set <prop> <val>' messages to the live.object inlet.
    """
    boxes, lines = _live_path_pair(id_prefix, path, "live.object")
    return (boxes, lines)


def live_observer(id_prefix: str, path: str = "live_set",
                  prop: str = "tempo") -> tuple:
    """Watch a Live property and output its value whenever it changes.

    Connects live.path -> live.object -> live.observer.
    The live.observer outlet emits the current value of `prop` on change.
    """
    p = id_prefix
    boxes, lines = _live_path_pair(p, path, "live.object")
    boxes.append(newobj(f"{p}_observer", f"live.observer {prop}",
                        numinlets=1, numoutlets=1, outlettype=[""],
                        patching_rect=[30, 180, 120, 20]))
    lines.append(patchline(f"{p}_obj", 0, f"{p}_observer", 0))
    return (boxes, lines)


def live_set_control(id_prefix: str, path: str = "live_set",
                     prop: str = "tempo") -> tuple:
    """Create a live.path + live.object for sending set messages to a property.

    Send a value to the live.object inlet to set the property.
    """
    boxes, lines = _live_path_pair(id_prefix, path,
                                   f"live.object set {prop}", obj_width=120)
    return (boxes, lines)
