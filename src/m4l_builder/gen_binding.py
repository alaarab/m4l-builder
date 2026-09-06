"""Validated control-message bindings to registered GenExpr parameters."""

from __future__ import annotations

import json
import re

from .gen_lint import _strip_comments
from .patcher_walk import boxes_by_id, iter_boxes


def gen_parameter_names(device, target: str) -> set[str]:
    """Read Params from an embedded or registered external gen~ patcher."""
    boxes = boxes_by_id(device)
    box = boxes.get(target)
    if box is None:
        raise ValueError(f"Unknown gen~ target: {target}")
    words = box.get("text", "").split()
    if not words or words[0] != "gen~":
        raise ValueError(f"Target {target} is not a gen~ object")
    patcher = box.get("patcher")
    if patcher is None:
        if len(words) < 2 or words[1].startswith("@"):
            raise ValueError(f"Target {target} has no inspectable GenExpr patcher")
        filename = words[1] if words[1].endswith(".gendsp") else words[1] + ".gendsp"
        asset = next((a for a in device.assets() if a.filename == filename), None)
        if asset is None:
            raise ValueError(f"Register {filename} before binding its parameters")
        patcher = json.loads(asset.content)
    names = set()
    for node in iter_boxes(patcher.get("patcher", patcher)):
        if node.get("maxclass") == "codebox":
            code = "\n".join(_strip_comments(node.get("code", "")))
            names.update(re.findall(r"\bParam\s+([A-Za-z_]\w*)\s*(?:\(|;)", code))
        elif node.get("maxclass") == "newobj":
            match = re.match(r"param\s+([A-Za-z_]\w*)\b", node.get("text", ""))
            if match:
                names.add(match.group(1))
    return names


def bind_gen_param(device, source, target, parameter: str, *, id: str,
                   source_outlet: int = 0, **kwargs):
    """Add control -> prepend parameter -> gen~, validating before mutation.

    Register the gen~ core and source first. IDs, outlet and box attributes are
    caller-controlled so adopting this helper preserves existing patch graphs.
    Returns the prepend BoxRef for additional display or state fan-out.
    """
    if parameter not in gen_parameter_names(device, target):
        raise ValueError(f"Unknown GenExpr parameter {parameter!r} on {target}")
    boxes = boxes_by_id(device)
    if source not in boxes:
        raise ValueError(f"Unknown control source: {source}")
    if id in boxes:
        raise ValueError(f"Binding box ID already exists: {id}")
    if not isinstance(source_outlet, int) or not 0 <= source_outlet < boxes[source].get("numoutlets", 0):
        raise ValueError(f"Invalid source outlet {source_outlet} on {source}")
    ref = device.add_newobj(id, f"prepend {parameter}", numinlets=1, numoutlets=1, **kwargs)
    device.add_line(source, source_outlet, ref, 0)
    device.add_line(ref, 0, target, 0)
    return ref
