"""Max object factory functions for creating box and patchline dicts."""


def newobj(id: str, text: str, *, numinlets: int, numoutlets: int,
           outlettype: list = None, patching_rect: list = None, **kwargs) -> dict:
    """Create a standard Max newobj box.

    Args:
        id: Unique object identifier (e.g. "obj-1").
        text: Max object text (e.g. "plugin~", "*~ 1.").
        numinlets: Number of inlets.
        numoutlets: Number of outlets.
        outlettype: List of outlet type strings (e.g. ["signal"]).
        patching_rect: [x, y, width, height] in patching view.
        **kwargs: Additional box properties.

    Returns:
        Dict with a "box" key containing the object definition.
    """
    box = {
        "id": id,
        "maxclass": "newobj",
        "fontname": "Arial Bold",
        "fontsize": 10.0,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "patching_rect": patching_rect or [0, 0, 60, 20],
        "text": text,
    }
    if outlettype:
        box["outlettype"] = outlettype
    box.update(kwargs)
    return {"box": box}


def patchline(source_id: str, source_outlet: int, dest_id: str, dest_inlet: int) -> dict:
    """Create a patchline connection between two objects.

    Args:
        source_id: ID of the source object.
        source_outlet: Outlet index on the source.
        dest_id: ID of the destination object.
        dest_inlet: Inlet index on the destination.

    Returns:
        Dict with a "patchline" key containing source/destination arrays.
    """
    return {
        "patchline": {
            "source": [source_id, source_outlet],
            "destination": [dest_id, dest_inlet],
        }
    }
