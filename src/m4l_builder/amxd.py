"""AMXD serialization and deserialization helpers."""

from __future__ import annotations

import json
import struct
import warnings

from .artifact_io import write_artifacts
from .constants import DEVICE_TYPE_CODES
from .container import build_amxd
from .patcher import build_patcher
from .validation import BuildValidationError, format_validation_issues


def _parameter_banks_payload(device) -> dict[str, dict]:
    # Live/Push expect each bank's `parameters` to be a FLAT 8-slot list of param
    # LONGNAME strings, positioned by slot, with "-" placeholders for empty slots.
    # Emitting a list-of-dicts {index,name,visible} silently broke Push banks on every
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


def collect_build_issues(device) -> list:
    """Collect the same build checks regardless of their reporting policy."""
    from .box_lint import lint_boxes, lint_boxes_with_args
    from .jsui_coverage import jsui_coverage_issues
    from .validation import ValidationIssue

    issues = list(device.lint(device_type=device.device_type))
    issues.extend(
        ValidationIssue(code="box-declaration-mismatch", message=msg, severity="error")
        for msg in lint_boxes(device.boxes)
    )
    # Advisory, never blocking. An argument-carrying box can only be checked on
    # outlet SHORTFALL, and the fleet's existing instances sit in a protected
    # device (Shard) and a SHA-pinned verification candidate (Foundry) whose
    # source must not change to satisfy a lint. Deliberately kept out of
    # default_codes so it reports without failing a build.
    issues.extend(
        ValidationIssue(code="box-outlets-under-declared", message=msg,
                        severity="warning")
        for msg in lint_boxes_with_args(device.boxes)
    )
    scripts = {
        asset.filename: {"content": (
            asset.content.decode(asset.encoding)
            if isinstance(asset.content, bytes) else asset.content
        )}
        for asset in device.assets() if asset.filename.endswith(".js")
    }
    issues.extend(
        ValidationIssue(
            code="jsui-handler-missing", severity="error",
            message=(f"{dest} (jsui/v8ui): message {sel!r} is routed in from {src}, "
                     f"but its script defines neither {sel}() nor anything()"),
        )
        for dest, sel, src in jsui_coverage_issues(device.boxes, device.lines, scripts)
    )
    return issues


def apply_validation_policy(device, policy) -> None:
    """Apply build validation semantics to a device-like object.

    policy None (default): enforce wiring-integrity rules only.
    policy False: skip all validation (explicit escape hatch).
    policy "warn"/"error": full lint with the chosen severity behavior.
    """
    if policy is False:
        return
    if policy not in {None, "warn", "error"}:
        raise ValueError("validate must be one of None, False, 'warn', or 'error'")
    issues = collect_build_issues(device)
    if policy is None:
        default_codes = WIRING_INTEGRITY_CODES | {
            "setwidth-mismatch", "expr-ternary", "box-declaration-mismatch",
            "jsui-handler-missing",
        }
        blocking = [issue for issue in issues if issue.code in default_codes]
        if blocking:
            raise BuildValidationError(blocking)
        return
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
    patcher = prepare_device_patcher(device, validate=validate)
    return build_amxd(patcher, DEVICE_TYPE_CODES[device.device_type])


def _assert_sidecars_registered(device, patcher) -> None:
    """Fail the build if a jsui/v8ui box references a sidecar .js that is NOT a
    registered asset.

    Such a reference ships a device whose jsui loads NO code: every message sent
    to it errors ``js: no function X`` in the Max console (a real shipped bug --
    the raw ``ui.jsui`` factory only sets ``filename`` and does NOT register the
    code, unlike ``device.add_v8ui``). Our JSON tests never caught it because the
    structure was valid; the *asset* was simply absent. This guard closes that gap
    for every device (main patcher + all subpatchers, walked recursively).
    """
    registered = {a.filename for a in device.assets()}
    referenced = set()

    def walk(node):
        if isinstance(node, dict):
            box = node.get("box", node)
            if isinstance(box, dict) and box.get("maxclass") in ("jsui", "v8ui"):
                fn = box.get("filename")
                if isinstance(fn, str) and fn.endswith(".js"):
                    referenced.add(fn)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(patcher)
    missing = sorted(referenced - registered)
    if missing:
        raise ValueError(
            "jsui/v8ui sidecar(s) referenced but NOT registered as assets -- they "
            "will ship MISSING, so the jsui loads no code and every message errors "
            "'js: no function ...' in Max. Register the code (device.add_v8ui, or "
            "device.register_asset(name, code, asset_type='TEXT', category='js')): "
            + ", ".join(missing)
        )


def prepare_device_patcher(device, *, validate=None) -> dict:
    """Validate graph and required scripts for every serialization path."""
    apply_validation_policy(device, validate)
    patcher = device_to_patcher(device)
    _assert_sidecars_registered(device, patcher)
    return patcher


def build_device(device, output_path: str, *, validate=None) -> int:
    """Stage the complete device and sidecars, then install them together."""
    data = device_to_bytes(device, validate=validate)
    return write_artifacts(output_path, data, assets=device.assets())


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
