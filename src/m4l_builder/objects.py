"""Max object factory functions for creating box and patchline dicts."""


def newobj(id: str, text: str, *, numinlets: int, numoutlets: int,
           outlettype: list = None, patching_rect: list = None, **kwargs) -> dict:
    """Create a Max newobj box dict with a "box" key."""
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
    """Create a patchline connection dict with a "patchline" key."""
    return {
        "patchline": {
            "source": [source_id, source_outlet],
            "destination": [dest_id, dest_inlet],
        }
    }
