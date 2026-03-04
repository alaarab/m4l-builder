"""Subpatcher: a nested patcher that can be embedded inside a Device."""

from .constants import DEFAULT_APPVERSION
from .objects import newobj, patchline


class Subpatcher:
    """A nested patcher that lives inside a parent device as a `p name` box.

    Provides the same add_box/add_line/add_dsp/add_newobj interface as Device,
    then serializes to a box dict with an embedded "patcher" key via to_box().
    """

    def __init__(self, name: str = "subpatch"):
        self.name = name
        self.boxes = []
        self.lines = []

    def add_box(self, box_dict: dict) -> str:
        """Add a raw box dict and return its object ID."""
        self.boxes.append(box_dict)
        return box_dict["box"]["id"]

    def add_line(self, source_id: str, source_outlet: int,
                 dest_id: str, dest_inlet: int):
        self.lines.append(patchline(source_id, source_outlet, dest_id, dest_inlet))

    def add_dsp(self, boxes: list, lines: list):
        """Add all boxes and lines from a DSP block tuple."""
        for box in boxes:
            self.add_box(box)
        for line in lines:
            self.lines.append(line)

    def add_newobj(self, id: str, text: str, *, numinlets: int, numoutlets: int,
                   **kwargs) -> str:
        return self.add_box(newobj(id, text, numinlets=numinlets,
                                   numoutlets=numoutlets, **kwargs))

    def to_patcher_dict(self) -> dict:
        """Return the inner patcher dict (without the outer box wrapper)."""
        return {
            "fileversion": 1,
            "appversion": DEFAULT_APPVERSION.copy(),
            "rect": [0, 0, 400, 300],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": list(self.boxes),
            "lines": list(self.lines),
        }

    def to_box(self, id: str, rect: list, *,
               numinlets: int = 1, numoutlets: int = 1,
               outlettype: list = None) -> dict:
        """Return a full box dict ready for device.add_box().

        The box is a newobj with text "p {name}" and an embedded patcher.
        """
        box = {
            "id": id,
            "maxclass": "newobj",
            "text": f"p {self.name}",
            "patcher": self.to_patcher_dict(),
            "patching_rect": rect,
            "numinlets": numinlets,
            "numoutlets": numoutlets,
        }
        if outlettype:
            box["outlettype"] = outlettype
        return {"box": box}
