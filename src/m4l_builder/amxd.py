"""AMXD serialization and deserialization helpers."""

from __future__ import annotations

import json
import os
import struct
import warnings

from .constants import DEVICE_TYPE_CODES
from .container import build_amxd, write_amxd
from .patcher import build_patcher
from .validation import BuildValidationError, format_validation_issues


def _parameter_banks_payload(device) -> dict[str, dict]:
    banks: dict[str, dict] = {}
    for varname, (bank, position) in device._param_banks.items():
        bank_key = str(bank)
        if bank_key not in banks:
            banks[bank_key] = {
                "index": bank,
                "name": device._param_bank_names.get(bank, ""),
                "parameters": [],
            }
        spec = device.parameter(varname)
        banks[bank_key]["parameters"].append(
            {
                "index": position,
                "name": varname,
                "visible": 1 if spec is None else spec.visible,
            }
        )
    return banks


def apply_validation_policy(device, policy) -> None:
    """Apply build validation semantics to a device-like object."""
    if policy in (None, False):
        return
    if policy not in {"warn", "error"}:
        raise ValueError("validate must be one of None, 'warn', or 'error'")

    issues = device.lint(device_type=device.device_type)
    if not issues:
        return

    error_issues = [issue for issue in issues if issue.severity == "error"]
    warning_issues = [issue for issue in issues if issue.severity != "error"]

    if policy == "warn":
        warnings.warn(format_validation_issues(issues), stacklevel=3)
        return

    if error_issues:
        raise BuildValidationError(error_issues, warnings=warning_issues)
    if warning_issues:
        warnings.warn(format_validation_issues(warning_issues), stacklevel=3)


def device_to_patcher(device, *, profile=None) -> dict:
    """Serialize a device-like authoring object into a patcher dict."""
    effective_profile = profile or device.profile
    patcher = build_patcher(
        device.boxes,
        device.lines,
        name=device.name,
        width=device.width,
        height=device.height,
        device_type=device.device_type,
        profile=effective_profile,
    )
    patcher["patcher"]["dependency_cache"] = [
        asset.dependency_entry() for asset in device.assets()
    ]
    if device._param_banks:
        patcher["patcher"]["parameters"]["parameterbanks"] = _parameter_banks_payload(device)
    return patcher


def device_to_bytes(device, *, validate=None) -> bytes:
    """Build an AMXD binary for a device-like authoring object."""
    apply_validation_policy(device, validate)
    type_code = DEVICE_TYPE_CODES[device.device_type]
    return build_amxd(device_to_patcher(device), type_code)


def build_device(device, output_path: str, *, validate=None) -> int:
    """Write an AMXD file and any sidecar assets for a device-like object."""
    apply_validation_policy(device, validate)
    type_code = DEVICE_TYPE_CODES[device.device_type]
    result = write_amxd(device_to_patcher(device), output_path, type_code)
    output_dir = os.path.dirname(output_path)
    for asset in device.assets():
        try:
            asset.write_to(output_dir)
        except OSError as exc:
            raise IOError(
                f"Cannot write sidecar file {os.path.join(output_dir, asset.filename)}: {exc}"
            ) from exc
    return result


def device_from_amxd(path: str):
    """Parse an AMXD file back into a Device instance."""
    from .device import AudioEffect, Device, Instrument, MidiEffect

    with open(path, "rb") as handle:
        data = handle.read()

    type_code = data[8:12]
    type_map = {
        b"aaaa": "audio_effect",
        b"iiii": "instrument",
        b"mmmm": "midi_effect",
    }
    device_type = type_map.get(type_code, "audio_effect")

    meta_len = struct.unpack_from("<I", data, 16)[0]
    json_offset = 20 + meta_len + 8
    json_bytes = data[json_offset:].rstrip(b"\x00").rstrip(b"\n")
    patcher_dict = json.loads(json_bytes)

    patcher = patcher_dict["patcher"]
    width = patcher.get("devicewidth", patcher.get("openrect", [0, 0, 400, 170])[2])
    height = patcher.get("openrect", [0, 0, 400, 170])[3]

    subclass_map = {
        "audio_effect": AudioEffect,
        "instrument": Instrument,
        "midi_effect": MidiEffect,
    }
    klass = subclass_map.get(device_type, Device)

    if klass is Device:
        device = Device("Untitled", width, height, device_type=device_type)
    else:
        device = klass("Untitled", width, height)

    if klass is AudioEffect:
        device.boxes.clear()
        device.lines.clear()
        device._assets.clear()
        device._parameter_specs.clear()
        device._box_parameters.clear()
        device._reserved_ids.clear()

    for box in patcher.get("boxes", []):
        device.add_box(box)
    for line in patcher.get("lines", []):
        device.lines.append(line)
    for bank_key, bank_data in patcher.get("parameters", {}).get("parameterbanks", {}).items():
        bank_index = int(bank_key)
        bank_name = bank_data.get("name") or None
        if bank_name is not None:
            device.set_parameter_bank_name(bank_index, bank_name)
        for entry in bank_data.get("parameters", []):
            name = entry.get("name")
            if name is None:
                continue
            device.assign_parameter_bank(
                name,
                bank=bank_index,
                position=entry.get("index", 0),
                bank_name=bank_name,
            )
            spec = device.parameter(name)
            if spec is not None and "visible" in entry:
                spec.visible = int(entry.get("visible", 1))

    return device
