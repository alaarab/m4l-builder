"""Max object factory functions for creating box and patchline dicts."""

from __future__ import annotations

from .object_io import resolve_newobj_io


def newobj(id: str, text: str, *, numinlets: int | None = None,
           numoutlets: int | None = None, outlettype: list = None,
           patching_rect: list = None, **kwargs) -> dict:
    """Create a Max newobj box dict with a "box" key.

    Omitted ``numinlets``/``numoutlets``/``outlettype`` are inferred from
    ``text`` (see :mod:`m4l_builder.object_io`); an object whose shape isn't
    known raises :class:`~m4l_builder.object_io.UnknownObjectIO`.
    """
    numinlets, numoutlets, outlettype = resolve_newobj_io(
        text, numinlets, numoutlets, outlettype)
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


def message(
    id: str,
    text: str,
    *,
    numinlets: int = 2,
    numoutlets: int = 1,
    outlettype: list = None,
    patching_rect: list = None,
    **kwargs,
) -> dict:
    """Create a Max message box dict with a "box" key."""
    box = {
        "id": id,
        "maxclass": "message",
        "text": text,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "patching_rect": patching_rect or [0, 0, 50, 22],
    }
    if outlettype is not None:
        box["outlettype"] = outlettype
    box.update(kwargs)
    return {"box": box}


def patchline(source_id: str, source_outlet: int, dest_id: str, dest_inlet: int, **kwargs) -> dict:
    """Create a patchline connection dict with a "patchline" key."""
    patchline_dict = {
        "source": [source_id, source_outlet],
        "destination": [dest_id, dest_inlet],
    }
    patchline_dict.update(kwargs)
    return {"patchline": patchline_dict}
