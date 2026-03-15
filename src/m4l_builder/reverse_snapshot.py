"""Snapshot IO and normalized AMXD extraction helpers."""

from __future__ import annotations

import copy
import json
import os
import re
import struct
from typing import Any, Dict, List, Optional

from .device import Device
from .patcher import build_patcher
from ._reverse_legacy import (
    TYPE_CODE_TO_DEVICE_TYPE,
    _bridge_dependencies_from_support_files,
    _coerce_flag,
    _dedupe_dependencies,
    _device_type_from_bridge,
    _device_type_from_patcher,
    _embedded_patcher_kind_and_target,
    _embedded_snapshot_from_patcher_dict,
    _infer_dimensions_from_bridge_boxes,
    _normalize_bridge_box,
    _normalize_bridge_patchline,
    _parameter_spec_from_box,
    _snapshot_from_parts,
)


def _finalize_snapshot(snapshot: dict) -> dict:
    from .reverse_analysis import analyze_snapshot

    snapshot["analysis"] = analyze_snapshot(snapshot)
    return snapshot


def extract_parameter_specs(snapshot: dict) -> list[dict]:
    """Extract parameter-facing UI specs from a normalized snapshot."""
    specs = []
    for wrapped in snapshot.get("boxes", []):
        spec = _parameter_spec_from_box(wrapped.get("box", {}))
        if spec:
            specs.append(spec)
    return specs


def extract_embedded_patcher_snapshots(snapshot: dict) -> list[dict]:
    """Extract embedded patchers as normalized nested snapshots."""
    extracted = []

    def visit(boxes: list[dict], depth: int, ancestry_box_ids: list[str]) -> None:
        for wrapped in boxes:
            box = wrapped.get("box", {})
            nested = box.get("patcher")
            if not isinstance(nested, dict):
                continue
            host_box_id = box.get("id")
            host_kind, target = _embedded_patcher_kind_and_target(box)
            nested_snapshot = _finalize_snapshot(_embedded_snapshot_from_patcher_dict(nested))
            entry = {
                "host_box_id": host_box_id,
                "host_kind": host_kind or "embedded",
                "target": target,
                "depth": depth,
                "ancestry_box_ids": copy.deepcopy(ancestry_box_ids),
                "snapshot": nested_snapshot,
            }
            extracted.append(entry)
            child_ancestry = ancestry_box_ids + ([host_box_id] if host_box_id else [])
            visit(nested_snapshot.get("boxes", []), depth + 1, child_ancestry)

    visit(snapshot.get("boxes", []), 1, [])
    return extracted


def _read_amxd_chunks(data: bytes) -> dict[bytes, bytes]:
    chunks: dict[bytes, bytes] = {}
    offset = 12
    while offset + 8 <= len(data):
        tag = data[offset:offset + 4]
        length = struct.unpack_from("<I", data, offset + 4)[0]
        payload_start = offset + 8
        payload_end = payload_start + length
        if payload_end > len(data):
            raise ValueError(
                "Chunk %r extends past end of file (%d > %d)" % (tag, payload_end, len(data))
            )
        chunks[tag] = data[payload_start:payload_end]
        offset = payload_end
    return chunks


def _decode_patcher_chunk(payload: bytes) -> dict:
    relaxed_decimal = re.compile(r"(?<![0-9A-Za-z_])(-?\d+)\.(?=[,\]\}\s])")

    def scan_json_bounds(start: int) -> tuple[int, int] | None:
        json_end = None
        depth = 0
        in_string = False
        escaping = False
        for index, byte in enumerate(payload[start:], start=start):
            if in_string:
                if escaping:
                    escaping = False
                elif byte == 0x5C:
                    escaping = True
                elif byte == 0x22:
                    in_string = False
                continue

            if byte == 0x22:
                in_string = True
            elif byte == 0x7B:
                depth += 1
            elif byte == 0x7D:
                depth -= 1
                if depth == 0:
                    json_end = index + 1
                    break
        if json_end is None:
            return None
        return start, json_end

    json_start = payload.find(b"{")
    if json_start < 0:
        raise ValueError("ptch chunk did not contain a JSON object")

    candidate_starts = []
    for index, byte in enumerate(payload[:128]):
        if byte == 0x7B and index not in candidate_starts:
            candidate_starts.append(index)
    if json_start not in candidate_starts:
        candidate_starts.insert(0, json_start)

    for start in candidate_starts:
        bounds = scan_json_bounds(start)
        if not bounds:
            continue
        json_bytes = payload[bounds[0]:bounds[1]]
        try:
            decoded = json.loads(json_bytes)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict) and "patcher" in decoded:
            return decoded

    for start in candidate_starts:
        raw = payload[start:]
        for encoding in ("utf-8", "latin1"):
            try:
                text = raw.decode(encoding)
            except UnicodeDecodeError:
                continue
            relaxed_text = relaxed_decimal.sub(r"\1.0", text)
            try:
                decoded, _ = json.JSONDecoder().raw_decode(relaxed_text)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict) and "patcher" in decoded:
                return decoded

    raise ValueError("ptch chunk JSON object did not terminate cleanly")


def read_amxd(path: str) -> dict:
    """Read an .amxd container and return its patcher plus inferred metadata."""
    with open(path, "rb") as handle:
        data = handle.read()

    if data[:4] != b"ampf":
        raise ValueError("Not an ampf container")

    type_code = data[8:12]
    chunks = _read_amxd_chunks(data)
    ptch_payload = chunks.get(b"ptch")
    if ptch_payload is None:
        raise ValueError("ampf container did not contain a ptch chunk")
    patcher_dict = _decode_patcher_chunk(ptch_payload)
    device_type = TYPE_CODE_TO_DEVICE_TYPE.get(type_code)
    if device_type is None:
        device_type = _device_type_from_patcher(patcher_dict)

    return {
        "type_code": type_code,
        "device_type": device_type,
        "patcher": patcher_dict,
    }


def snapshot_from_device(device: Device) -> dict:
    """Capture a normalized snapshot from an in-memory Device instance."""
    patcher_dict = device.to_patcher()
    support_files: List[Dict[str, Any]] = []

    for filename, code in getattr(device, "_js_files", {}).items():
        support_files.append({
            "name": filename,
            "type": "TEXT",
            "content": code,
        })
    for filename, metadata in getattr(device, "_support_files", {}).items():
        support_files.append({
            "name": filename,
            "type": metadata.get("type", "TEXT"),
            "content": metadata.get("content", ""),
        })

    snapshot = _snapshot_from_parts(
        patcher_dict=patcher_dict,
        device_type=device.device_type,
        source={
            "kind": "device",
            "name": device.name,
        },
        device_name=device.name,
        support_files=support_files,
    )
    return _finalize_snapshot(snapshot)


def snapshot_from_amxd(path: str) -> dict:
    """Capture a normalized snapshot from an .amxd file and nearby sidecars."""
    loaded = read_amxd(path)
    patcher_dict = loaded["patcher"]
    dependency_cache = patcher_dict.get("patcher", {}).get("dependency_cache", [])
    output_dir = os.path.dirname(path)
    support_files = []
    missing_support_files = []

    for dep in _dedupe_dependencies(dependency_cache):
        name = dep.get("name")
        dep_type = dep.get("type", "TEXT")
        if not name:
            continue
        sidecar_path = os.path.join(output_dir, name)
        if os.path.isfile(sidecar_path):
            try:
                with open(sidecar_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except UnicodeDecodeError:
                missing_support_files.append({
                    "name": name,
                    "type": dep_type,
                    "reason": "non-text-sidecar",
                })
                continue
            support_files.append({
                "name": name,
                "type": dep_type,
                "content": content,
            })
        else:
            missing_support_files.append({
                "name": name,
                "type": dep_type,
                "reason": "sidecar-not-found",
            })

    snapshot = _snapshot_from_parts(
        patcher_dict=patcher_dict,
        device_type=loaded["device_type"],
        source={
            "kind": "amxd",
            "path": os.path.abspath(path),
        },
        device_name=os.path.splitext(os.path.basename(path))[0],
        support_files=support_files,
        missing_support_files=missing_support_files,
    )
    return _finalize_snapshot(snapshot)


def snapshot_from_bridge_payload(
    *,
    current_patcher: dict,
    boxes: list[dict],
    selected_device: Optional[dict] = None,
    box_attrs: Optional[dict] = None,
    patchlines: Optional[list[dict]] = None,
    support_files: Optional[list[dict]] = None,
) -> dict:
    """Capture a normalized snapshot from LiveMCP Max bridge payloads."""
    box_attrs = box_attrs or {}
    support_files = copy.deepcopy(support_files or [])
    normalized_boxes = [
        _normalize_bridge_box(summary, box_attrs.get(summary["box_id"]))
        for summary in boxes
    ]
    normalized_lines = [
        _normalize_bridge_patchline(line)
        for line in (patchlines or [])
    ]
    width, height = _infer_dimensions_from_bridge_boxes(normalized_boxes)
    device_type = _device_type_from_bridge(selected_device)
    patcher_name = (
        current_patcher.get("name")
        or (selected_device or {}).get("device_name")
        or "Untitled"
    )
    patcher_dict = build_patcher(
        normalized_boxes,
        normalized_lines,
        name=patcher_name,
        width=width,
        height=height,
        device_type=device_type,
    )
    patcher = patcher_dict["patcher"]
    patcher["name"] = patcher_name
    patcher["dependency_cache"] = _bridge_dependencies_from_support_files(support_files)
    patcher["openinpresentation"] = _coerce_flag(current_patcher.get("presentation_mode"))
    patcher["bglocked"] = _coerce_flag(current_patcher.get("locked"))
    patcher["autosave"] = 0

    snapshot = _snapshot_from_parts(
        patcher_dict=patcher_dict,
        device_type=device_type,
        source={
            "kind": "bridge",
            "bridge_session_id": current_patcher.get("bridge_session_id"),
            "selected_device": copy.deepcopy(selected_device or {}),
            "filepath": current_patcher.get("filepath"),
        },
        device_name=patcher_name,
        support_files=support_files,
    )
    snapshot["fidelity"] = {
        "exact_patcher_dict": False,
        "has_line_data": bool(patchlines),
        "rebuild_strategy": "write_amxd",
    }
    return _finalize_snapshot(snapshot)


def snapshot_to_json(snapshot: dict, *, indent: int = 2) -> str:
    """Serialize a normalized snapshot to JSON."""
    return json.dumps(snapshot, indent=indent)


def write_snapshot(snapshot: dict, path: str, *, indent: int = 2) -> int:
    """Write a normalized snapshot to disk as JSON."""
    text = snapshot_to_json(snapshot, indent=indent)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return len(text.encode("utf-8"))


def load_snapshot(path: str) -> dict:
    """Load a previously written normalized snapshot."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


__all__ = [
    "read_amxd",
    "snapshot_from_device",
    "snapshot_from_amxd",
    "snapshot_from_bridge_payload",
    "snapshot_to_json",
    "write_snapshot",
    "load_snapshot",
    "extract_embedded_patcher_snapshots",
    "extract_parameter_specs",
]
