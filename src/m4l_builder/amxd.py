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
    # Live/Push expect each bank's `parameters` to be a FLAT 8-slot list of param
    # LONGNAME strings, positioned by slot, with "-" placeholders for empty slots
    # (verified against real devices, e.g. SABROI AS Console). Emitting a
    # list-of-dicts {index,name,visible} silently broke Push banks on every
    # multi-param device. parameter_longname == ParameterSpec.name here.
    banks: dict[str, dict] = {}
    for varname, (bank, position) in device._param_banks.items():
        bank_key = str(bank)
        if bank_key not in banks:
            banks[bank_key] = {
                "index": bank,
                "name": device._param_bank_names.get(bank, ""),
                "parameters": ["-"] * 8,
            }
        if 0 <= position < 8:
            spec = device.parameter(varname)
            longname = getattr(spec, "name", None) or varname
            banks[bank_key]["parameters"][position] = longname
    return banks


# Wiring-integrity rules enforced on every build (policy None). Max drops
# patchlines to unknown box ids silently at load ("patchcord source not
# found: deleting") -> dead controls with no build error; these rules have
# zero false positives, so they are always errors.
WIRING_INTEGRITY_CODES = frozenset(
    {
        "duplicate-box-id",
        "unknown-source",
        "unknown-destination",
        "outlet-index-out-of-range",
        "inlet-index-out-of-range",
        "selector-initial-out-of-range",
        # Live-proven UI bug classes (Interaction arc): a visible live.text
        # with parameter_enable=0 never receives clicks; an interactive
        # control past the device edge (below the parking band) is
        # unreachable. Both shipped as real bugs — gate every build.
        "dead-live-text",
        "stranded-control",
    }
)


def apply_validation_policy(device, policy) -> None:
    """Apply build validation semantics to a device-like object.

    policy None (default): enforce wiring-integrity rules only.
    policy False: skip all validation (explicit escape hatch).
    policy "warn"/"error": full lint with the chosen severity behavior.
    """
    if policy is False:
        return
    if policy is None:
        issues = device.lint(device_type=device.device_type)
        # T26/Q46: the default build gate enforces wiring integrity AND the
        # LAYOUT error class (setwidth-mismatch — the runtime dead-zone bug).
        # STYLE errors (sig~ etc.) and layout WARNINGS stay advisory at the
        # default; opt into them with validate="warn"/"error".
        blocking = [
            issue for issue in issues
            if issue.code in WIRING_INTEGRITY_CODES
            or issue.code == "setwidth-mismatch"
        ]
        if blocking:
            raise BuildValidationError(blocking)
        return
    if policy not in {"warn", "error"}:
        raise ValueError("validate must be one of None, False, 'warn', or 'error'")

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
        latency=int(getattr(device, "latency", 0)),
        is_mpe=bool(getattr(device, "is_mpe", False)),
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
            raise OSError(
                f"Cannot write sidecar file {os.path.join(output_dir, asset.filename)}: {exc}"
            ) from exc
    return result


def device_from_amxd(path: str):
    """Parse an AMXD file back into a Device instance."""
    from .device import (
        AudioEffect,
        Device,
        Instrument,
        MidiEffect,
        MidiGenerator,
        MidiTransformation,
    )

    with open(path, "rb") as handle:
        data = handle.read()

    # The header is type_code(8:12) + meta_len at offset 16 (a uint32); the JSON
    # body starts after it. Bail with an actionable error rather than a cryptic
    # IndexError/struct.error on a truncated or non-AMXD file.
    if len(data) < 20:
        raise ValueError(
            f"{path}: not a valid AMXD file (truncated: {len(data)} bytes, need >= 20)"
        )

    type_code = data[8:12]
    type_map = {
        b"aaaa": "audio_effect",
        b"iiii": "instrument",
        b"mmmm": "midi_effect",
        b"natt": "note_transformation",
        b"nagg": "note_generator",
    }
    device_type = type_map.get(type_code, "audio_effect")

    meta_len = struct.unpack_from("<I", data, 16)[0]
    json_offset = 20 + meta_len + 8
    json_bytes = data[json_offset:].rstrip(b"\x00").rstrip(b"\n")
    if not json_bytes:
        raise ValueError(f"{path}: AMXD file contains no patcher JSON payload")
    try:
        patcher_dict = json.loads(json_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}: AMXD patcher JSON is malformed at byte {exc.pos}: {exc.msg}"
        ) from exc

    patcher = patcher_dict["patcher"]
    width = patcher.get("devicewidth", patcher.get("openrect", [0, 0, 400, 170])[2])
    height = patcher.get("openrect", [0, 0, 400, 170])[3]

    subclass_map = {
        "audio_effect": AudioEffect,
        "instrument": Instrument,
        "midi_effect": MidiEffect,
        "note_transformation": MidiTransformation,
        "note_generator": MidiGenerator,
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
        for position, entry in enumerate(bank_data.get("parameters", [])):
            if isinstance(entry, dict):
                # Legacy emitter shape {index,name,visible} — still readable.
                name = entry.get("name")
                if name is None:
                    continue
                device.assign_parameter_bank(
                    name,
                    bank=bank_index,
                    position=entry.get("index", position),
                    bank_name=bank_name,
                )
                spec = device.parameter(name)
                if spec is not None and "visible" in entry:
                    spec.visible = int(entry.get("visible", 1))
            else:
                # Correct Live shape: flat 8-slot longname list, "-" = empty slot.
                if not entry or entry == "-":
                    continue
                device.assign_parameter_bank(
                    entry,
                    bank=bank_index,
                    position=position,
                    bank_name=bank_name,
                )

    return device
