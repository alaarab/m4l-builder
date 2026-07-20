"""Faithful clone engine — reproduce a real device from its extracted patcher JSON.

Replays a corpus device's box+line graph (including embedded bpatcher / `p`
subpatchers and gen~ code, which ride along inside their box dicts) through the
builder's own assembly + serialization, producing a STRUCTURALLY identical .amxd.

This is the FAITHFUL-REPRODUCTION path (proves the builder can assemble + serialize
any device, and gets all 15 corpus devices cloned + installable fast). The
IDIOMATIC path — rebuilding each control via add_dial / add_number_box(appearance=4)
/ add_bpatcher_module / the gen~ kit etc. — is a separate quality pass that proves
each high-level primitive; this engine is the structural backbone underneath it.

    from m4l_builder.clone import clone_from_patcher_json
    device = clone_from_patcher_json("path/to/device.json",
                                     name="My Device")
    device.build(out_path)
"""

import json
from pathlib import Path

from .device import Device
from .parameters import tolerant_reconstruction
from .patcher_walk import iter_patchlines

# .amxd ampf device-type code -> builder device_type.
_DEVICE_TYPE = {"aaaa": "audio_effect", "mmmm": "midi_effect", "iiii": "instrument"}


def device_type_from_amxd(amxd_path) -> str:
    """Read the ampf chunk (bytes 8-11) to classify the device. Defaults audio_effect."""
    head = Path(amxd_path).read_bytes()[:16]
    return _DEVICE_TYPE.get(head[8:12].decode("latin1", "replace"), "audio_effect")


def clone_from_patcher_json(json_path, name=None, *, device_type="audio_effect") -> Device:
    """Build a Device that faithfully reproduces the patcher in ``json_path``.

    Replays every box (via add_box — embedded patchers/gen~ code ride along), every
    line, and the parameter-bank assignments. Returns the built-but-unwritten Device
    (call ``.build(path)``). The device presentation size is taken from the source
    patcher ``openrect``.
    """
    src = json.loads(Path(json_path).read_text())
    patcher = src["patcher"]
    boxes = patcher.get("boxes", [])
    lines = patcher.get("lines", [])
    banks = patcher.get("parameters", {}).get("parameterbanks", {})
    openrect = patcher.get("openrect") or [0, 0, 400, 170]
    width, height = round(openrect[2]), round(openrect[3])

    device = Device(name or src.get("patcher", {}).get("digest") or "Clone",
                    width, height, device_type=device_type)
    # Real shipping devices legitimately violate our stricter authoring rules
    # (enum initial beyond options, empty enum option); reconstruct tolerantly so
    # the clone preserves the original values verbatim.
    with tolerant_reconstruction():
        for box in boxes:
            device.add_box(box)
    for patchline in iter_patchlines(lines):
        src_pl = patchline["source"]
        dst_pl = patchline["destination"]
        device.add_line(src_pl[0], src_pl[1], dst_pl[0], dst_pl[1])
    for bank_key, data in banks.items():
        bank_name = data.get("name") or None
        for position, longname in enumerate(data.get("parameters", [])):
            if longname and longname != "-":
                try:
                    device.assign_parameter_bank(
                        longname, bank=int(bank_key), position=position,
                        bank_name=bank_name,
                    )
                except (ValueError, KeyError):
                    pass  # bank entry references a param not in this patcher — skip
    return device
