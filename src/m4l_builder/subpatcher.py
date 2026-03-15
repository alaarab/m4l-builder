"""Subpatcher: a nested patcher that can be embedded inside a Device."""

from .graph import GraphContainer
from .profiles import DEFAULT_PATCHER_PROFILE


class Subpatcher(GraphContainer):
    """A nested patcher that lives inside a parent device as a `p name` box.

    Provides the same add_box/add_line/add_dsp/add_newobj interface as Device,
    then serializes to a box dict with an embedded "patcher" key via to_box().
    """

    def __init__(self, name: str = "subpatch", profile=None):
        super().__init__()
        self.name = name
        self.profile = profile or DEFAULT_PATCHER_PROFILE

    def add_newobj(self, id: str = None, text: str = "", *, numinlets: int, numoutlets: int,
                   **kwargs) -> str:
        return super().add_newobj(id, text, numinlets=numinlets,
                                  numoutlets=numoutlets, **kwargs)

    def to_patcher_dict(self) -> dict:
        """Return the inner patcher dict (without the outer box wrapper)."""
        return self.profile.build_subpatcher_patcher(self.boxes, self.lines)

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
