"""Low-level helpers for the legacy-device reverse tool (leaf layer).

Extracted from _reverse_legacy.py (god-file split); re-exported by it."""
from __future__ import annotations

import copy
import os
import pprint
import re
from pathlib import Path
from typing import Any

from ._reverse_constants import *  # noqa: F401,F403
from .constants import AMXD_TYPE, AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .device import Device
from .live_api import (
    device_active_state,
    live_object_path,
    live_observer,
    live_parameter_probe,
    live_set_control,
    live_state_observer,
    live_thisdevice,
)
from .patcher_walk import boxes_by_id as _boxes_by_id
from .patcher_walk import iter_boxes, iter_patchlines, unwrap_box
from .recipes import (
    dry_wet_stage,
    gain_controlled_stage,
    midi_note_gate,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)


def _patcher_name(patcher_dict: dict) -> str:
    return patcher_dict.get("patcher", {}).get("name", "Untitled")


def _patcher_dimensions(patcher_dict: dict) -> tuple[float, float]:
    patcher = patcher_dict.get("patcher", {})
    openrect = patcher.get("openrect", [0.0, 0.0, 400.0, 170.0])
    width = patcher.get("devicewidth", openrect[2])
    height = openrect[3]
    return width, height


def _device_type_from_patcher(patcher_dict: dict, fallback: str = "audio_effect") -> str:
    project = patcher_dict.get("patcher", {}).get("project", {})
    amxdtype = project.get("amxdtype")
    return AMXD_INT_TO_DEVICE_TYPE.get(amxdtype, fallback)


def _dedupe_dependencies(entries: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for entry in entries:
        name = entry.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(copy.deepcopy(entry))
    return result


def _snapshot_from_parts(
    *,
    patcher_dict: dict,
    device_type: str,
    source: dict,
    device_name: str | None = None,
    support_files: list[dict[str, Any]] | None = None,
    missing_support_files: list[dict[str, Any]] | None = None,
) -> dict:
    width, height = _patcher_dimensions(patcher_dict)
    patcher = patcher_dict.get("patcher", {})
    return {
        "schema_version": 1,
        "source": copy.deepcopy(source),
        "device": {
            "name": device_name or _patcher_name(patcher_dict),
            "device_type": device_type,
            "width": width,
            "height": height,
        },
        "patcher": copy.deepcopy(patcher_dict),
        "boxes": copy.deepcopy(patcher.get("boxes", [])),
        "lines": copy.deepcopy(patcher.get("lines", [])),
        "dependencies": _dedupe_dependencies(patcher.get("dependency_cache", [])),
        "parameterbanks": copy.deepcopy(
            patcher.get("parameters", {}).get("parameterbanks", {})
        ),
        "support_files": copy.deepcopy(support_files or []),
        "missing_support_files": copy.deepcopy(missing_support_files or []),
        "fidelity": {
            "exact_patcher_dict": True,
            "has_line_data": True,
            "rebuild_strategy": "write_amxd",
        },
    }


def _device_type_from_bridge(selected_device: dict | None) -> str:
    class_name = str((selected_device or {}).get("class_name") or "")
    lowered = class_name.lower()
    if "audioeffect" in lowered:
        return "audio_effect"
    if "midieffect" in lowered:
        return "midi_effect"
    if "instrument" in lowered:
        return "instrument"
    return "audio_effect"


def _infer_dimensions_from_bridge_boxes(boxes: list[dict]) -> tuple[float, float]:
    rects = []
    for box in iter_boxes(boxes):
        rect = box.get("presentation_rect") or box.get("patching_rect")
        if rect and len(rect) == 4:
            rects.append(rect)

    if not rects:
        return 400.0, 170.0

    width = max(rect[0] + rect[2] for rect in rects)
    height = max(rect[1] + rect[3] for rect in rects)
    return max(width, 120.0), max(height, 60.0)


def _coerce_flag(value: Any) -> int:
    return 1 if bool(value) else 0


def _normalize_bridge_box(summary: dict, attrs_payload: dict | None = None) -> dict:
    attrs_payload = attrs_payload or {}
    object_attrs = copy.deepcopy(attrs_payload.get("object_attrs", {}))
    box_attrs = copy.deepcopy(attrs_payload.get("box_attrs", {}))

    box = {
        "id": summary["box_id"],
        "maxclass": summary.get("maxclass", "newobj"),
    }

    rect = summary.get("rect")
    if rect is not None:
        box["patching_rect"] = rect
    presentation_rect = summary.get("presentation_rect")
    if presentation_rect is not None:
        box["presentation_rect"] = presentation_rect
        box["presentation"] = 1
    if "hidden" in summary:
        box["hidden"] = _coerce_flag(summary["hidden"])
    if "background" in summary:
        box["background"] = _coerce_flag(summary["background"])
    if summary.get("varname"):
        box["varname"] = summary["varname"]

    box.update(box_attrs)
    box.update(object_attrs)

    if summary.get("boxtext") is not None and "text" not in box:
        box["text"] = summary["boxtext"]
    if box.get("presentation_rect") is not None and "presentation" not in box:
        box["presentation"] = 1

    return {"box": box}


def _normalize_bridge_patchline(line: dict) -> dict:
    return {
        "patchline": {
            "source": [line["from_box_id"], line["outlet"]],
            "destination": [line["to_box_id"], line["inlet"]],
        }
    }


def _bridge_dependencies_from_support_files(support_files: list[dict]) -> list[dict]:
    deps = []
    for support in support_files:
        deps.append({
            "name": support["name"],
            "type": support.get("type", "TEXT"),
            "implicit": 1,
        })
    return deps


def _box_annotation_name(box: dict):
    """Read a param's annotation name from the valueof (the correct location, A2)
    with a fallback to a legacy box-level `annotation_name` attr."""
    vo = box.get("saved_attribute_attributes", {}).get("valueof", {})
    return vo.get("parameter_annotation_name") or box.get("annotation_name")


def _parameter_spec_from_box(box: dict) -> dict | None:
    valueof = box.get("saved_attribute_attributes", {}).get("valueof")
    if not isinstance(valueof, dict):
        return None

    initial = valueof.get("parameter_initial")
    if isinstance(initial, list) and initial:
        initial_value = initial[0]
    else:
        initial_value = None

    return {
        "box_id": box.get("id"),
        "varname": box.get("varname"),
        "maxclass": box.get("maxclass"),
        "parameter_type": valueof.get("parameter_type"),
        "shortname": valueof.get("parameter_shortname"),
        "min": valueof.get("parameter_mmin"),
        "max": valueof.get("parameter_mmax"),
        "initial": initial_value,
        "unitstyle": valueof.get("parameter_unitstyle"),
        "enum": copy.deepcopy(valueof.get("parameter_enum")),
    }


def _normalize_number(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _line_key(source_id: str, source_outlet: int, dest_id: str, dest_inlet: int) -> tuple:
    return (source_id, source_outlet, dest_id, dest_inlet)


def _line_key_from_wrapped(line: dict) -> tuple:
    patchline = line.get("patchline", {})
    source = patchline.get("source", [None, 0])
    destination = patchline.get("destination", [None, 0])
    return _line_key(source[0], source[1], destination[0], destination[1])


def _snapshot_graph(snapshot: dict) -> tuple[dict, dict, set[tuple]]:
    boxes_by_id = {}
    box_indices = {}
    for index, box in enumerate(iter_boxes(snapshot)):
        box_id = box.get("id")
        if box_id:
            boxes_by_id[box_id] = box
            box_indices[box_id] = index

    line_keys = set()
    for patchline in iter_patchlines(snapshot):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        line_keys.add(_line_key(source[0], source[1], destination[0], destination[1]))
    return boxes_by_id, box_indices, line_keys


def _box_operator(box: dict) -> str | None:
    if box.get("maxclass") != "newobj":
        return None
    text = str(box.get("text", "")).strip()
    if not text:
        return None
    return text.split()[0]


def _box_text_args(box: dict) -> str | None:
    text = str(box.get("text", "")).strip()
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    args = parts[1].strip()
    return args or None


def _buffer_target_name(box: dict) -> str | None:
    args = _box_text_args(box)
    if not args:
        return None
    first = args.split()[0].strip()
    if not first or first.startswith("@"):
        return None
    return first


def _embedded_patcher_kind_and_target(box: dict) -> tuple[str | None, str | None]:
    if box.get("maxclass") == "bpatcher":
        return "bpatcher", box.get("name")

    operator = _box_operator(box)
    if operator not in EMBEDDED_PATCHER_OPERATORS:
        return None, None

    text = str(box.get("text", "")).strip()
    parts = text.split(maxsplit=1)
    target = parts[1] if len(parts) > 1 else None
    host_kind = {
        "p": "subpatcher",
        "poly~": "poly",
        "gen~": "gen",
        "pfft~": "pfft",
    }[operator]
    return host_kind, target


def _snapshot_source_path(snapshot: dict) -> str | None:
    source = snapshot.get("source", {})
    path = source.get("path")
    if not path:
        return None
    return os.path.abspath(str(path))


def _factory_pack_context(snapshot: dict) -> dict[str, str | None]:
    source_path = _snapshot_source_path(snapshot)
    context = {
        "source_path": source_path,
        "source_lane": "public",
        "pack_name": None,
        "pack_section": None,
        "pack_subsection": None,
        "pack_section_path": None,
    }
    if not source_path:
        return context

    parts = Path(source_path).parts
    if "Factory Packs" not in parts:
        return context

    index = parts.index("Factory Packs")
    trailing = list(parts[index + 1:])
    if not trailing:
        return context

    context["source_lane"] = "factory"
    context["pack_name"] = trailing[0]
    if len(trailing) > 1:
        context["pack_section"] = trailing[1]
    if len(trailing) > 2:
        context["pack_subsection"] = trailing[2]
    if len(trailing) > 1:
        context["pack_section_path"] = " / ".join(trailing[: min(3, len(trailing) - 1)])
    return context


def _connected_box_ids(snapshot: dict, seed_box_ids: set[str]) -> set[str]:
    connected = set()
    for patchline in iter_patchlines(snapshot):
        source_id = patchline.get("source", [None, 0])[0]
        destination_id = patchline.get("destination", [None, 0])[0]
        if source_id in seed_box_ids and destination_id:
            connected.add(destination_id)
        if destination_id in seed_box_ids and source_id:
            connected.add(source_id)
    return connected - set(seed_box_ids)


def _rect_matches(box: dict, expected: list[float]) -> bool:
    rect = box.get("patching_rect")
    if rect is None or len(rect) != len(expected):
        return False
    return all(float(actual) == float(target) for actual, target in zip(rect, expected))


def _presentation_rect(box: dict) -> list[float] | None:
    rect = box.get("presentation_rect")
    if rect is None or len(rect) != 4:
        return None
    return [float(value) for value in rect]


def _rects_touch(a: list[float], b: list[float], *, padding: float = 18.0) -> bool:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2 = ax1 + aw
    ay2 = ay1 + ah
    bx2 = bx1 + bw
    by2 = by1 + bh
    return not (
        (ax2 + padding) < bx1
        or (bx2 + padding) < ax1
        or (ay2 + padding) < by1
        or (by2 + padding) < ay1
    )


def _text_float(text: str, prefix: str) -> float | None:
    if not text.startswith(prefix):
        return None
    try:
        return float(text[len(prefix):].strip())
    except ValueError:
        return None


def _text_int(text: str, prefix: str) -> int | None:
    value = _text_float(text, prefix)
    if value is None or not float(value).is_integer():
        return None
    return int(value)


def _parse_live_api_message_text(text: str) -> dict[str, list[str]]:
    parsed = {
        "paths": [],
        "properties": [],
        "gets": [],
        "sets": [],
        "calls": [],
    }
    segments = [segment.strip() for segment in text.split(",") if segment.strip()]
    for segment in segments:
        if segment.startswith("path "):
            value = segment[len("path "):].strip()
            if value:
                parsed["paths"].append(value)
            continue
        if segment.startswith("property "):
            value = segment[len("property "):].strip()
            if value:
                parsed["properties"].append(value)
            continue
        if segment.startswith("get "):
            value = segment[len("get "):].strip()
            if value:
                parsed["gets"].append(value)
            continue
        if segment.startswith("set "):
            tokens = segment.split()
            if len(tokens) > 1:
                parsed["sets"].append(tokens[1])
            continue
        if segment.startswith("call "):
            tokens = segment.split()
            if len(tokens) > 1:
                parsed["calls"].append(tokens[1])
            continue
    return parsed


def _classify_live_api_component_archetypes(params: dict[str, Any]) -> list[str]:
    archetypes = []
    property_names = set(params.get("property_names", []))
    get_targets = set(params.get("get_targets", []))
    set_targets = set(params.get("set_targets", []))
    call_targets = set(params.get("call_targets", []))
    prepend_targets = set(params.get("prepend_targets", []))
    direct_message_texts = set(params.get("direct_message_texts", []))
    core_operators = set(params.get("core_operators", []))

    if "is_playing" in property_names:
        archetypes.append("transport_state_observer")
    if "tempo" in property_names:
        archetypes.append("tempo_observer")
    if (
        "scale_mode" in property_names
        or "scaleIntervals" in prepend_targets
        or any(text.startswith("rootNote ") for text in direct_message_texts)
    ):
        archetypes.append("scale_state_observer")
    if (
        {"value", "min", "max"} & get_targets
        or "value" in property_names
        or "value" in set_targets
        or "str_for_value" in call_targets
    ):
        archetypes.append("parameter_probe")
    if (
        "tracks" in get_targets
        or "create_audio_track" in call_targets
        or {"arm", "mute", "name"} & set_targets
    ):
        archetypes.append("track_management")
    if (
        "live.thisdevice" in core_operators
        and ("active" in prepend_targets or any(text.startswith("active ") for text in direct_message_texts))
    ):
        archetypes.append("device_active_state")
    if not archetypes and core_operators == {"live.thisdevice"}:
        archetypes.append("thisdevice_reference")

    return sorted(set(archetypes))


def _matches_state_bundle_operator(operator: str) -> bool:
    return operator in STATE_BUNDLE_OPERATORS or operator == "zl" or operator.startswith("zl.")


def _operator_components(
    snapshot: dict,
    boxes_by_id: dict,
    box_indices: dict,
    predicate,
) -> tuple[list[list[str]], dict[str, str], dict[str, set[str]]]:
    return _relevant_box_components(
        snapshot,
        boxes_by_id,
        box_indices,
        lambda box: _box_operator(box) if predicate(_box_operator(box) or "") else None,
    )


def _relevant_box_components(
    snapshot: dict,
    boxes_by_id: dict,
    box_indices: dict,
    label_for_box,
) -> tuple[list[list[str]], dict[str, str], dict[str, set[str]]]:
    relevant_ids = set()
    labels_by_id: dict[str, str] = {}
    for box_id, box in boxes_by_id.items():
        label = label_for_box(box)
        if label:
            relevant_ids.add(box_id)
            labels_by_id[box_id] = label

    adjacency = {box_id: set() for box_id in relevant_ids}
    full_adjacency = {box_id: set() for box_id in boxes_by_id}
    for patchline in iter_patchlines(snapshot):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        source_id = source[0]
        dest_id = destination[0]
        if source_id in full_adjacency and dest_id in full_adjacency:
            full_adjacency[source_id].add(dest_id)
            full_adjacency[dest_id].add(source_id)
        if source_id in relevant_ids and dest_id in relevant_ids:
            adjacency[source_id].add(dest_id)
            adjacency[dest_id].add(source_id)

    components = []
    seen = set()
    for start_id in sorted(relevant_ids, key=lambda item: box_indices.get(item, 10 ** 9)):
        if start_id in seen:
            continue
        stack = [start_id]
        component = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency[current] - component)
        seen.update(component)
        components.append(sorted(component, key=lambda item: box_indices.get(item, 10 ** 9)))
    return components, labels_by_id, full_adjacency


def _adjacent_message_texts(component: list[str], full_adjacency: dict[str, set[str]], boxes_by_id: dict) -> list[str]:
    texts = []
    component_ids = set(component)
    for box_id in component:
        for neighbor_id in full_adjacency.get(box_id, set()):
            if neighbor_id in component_ids:
                continue
            neighbor = boxes_by_id.get(neighbor_id)
            if not neighbor or neighbor.get("maxclass") != "message":
                continue
            text = str(neighbor.get("text", "")).strip()
            if text:
                texts.append(text)
    return sorted(set(texts))


def _transport_lfo_division_from_text(text: str) -> str | None:
    match = re.fullmatch(r"expr \$f1 / \(60\.0 \* ([0-9.]+)\)", text)
    if match is None:
        return None
    divisor = float(match.group(1))
    divisions = {
        0.5: "1/8",
        1.0: "1/4",
        2.0: "1/2",
        4.0: "1/1",
    }
    return divisions.get(divisor)


def _candidate_prefixes(boxes_by_id: dict, suffixes: list[str]) -> list[str]:
    prefixes = set()
    for box_id in boxes_by_id:
        for suffix in suffixes:
            if suffix == "":
                prefixes.add(box_id)
            elif box_id.endswith(suffix):
                prefixes.add(box_id[:-len(suffix)])
    return sorted(prefixes)


def _pattern_match(
    *,
    kind: str,
    prefix: str,
    box_ids: list[str],
    line_keys: list[tuple],
    params: dict | None = None,
    helper: dict | None = None,
) -> dict:
    return {
        "kind": kind,
        "prefix": prefix,
        "box_ids": box_ids,
        "line_keys": line_keys,
        "params": params or {},
        "first_box_index": None,
        "helperizable": helper is not None,
        "helper": helper,
    }


def _recipe_match(
    *,
    kind: str,
    prefix: str,
    box_ids: list[str],
    line_keys: list[tuple],
    params: dict | None = None,
    recipe: dict | None = None,
) -> dict:
    return {
        "kind": kind,
        "prefix": prefix,
        "box_ids": box_ids,
        "line_keys": line_keys,
        "params": params or {},
        "first_box_index": None,
        "recipeizable": recipe is not None,
        "recipe": recipe,
    }


def _motif_match(
    *,
    kind: str,
    box_ids: list[str],
    params: dict | None = None,
    first_box_index: int = 0,
) -> dict:
    return {
        "kind": kind,
        "box_ids": sorted(box_ids),
        "params": params or {},
        "first_box_index": first_box_index,
    }


def _semantic_helper_match(
    *,
    kind: str,
    prefix: str,
    box_ids: list[str],
    line_keys: list[tuple],
    helper: dict[str, Any],
    params: dict | None = None,
    first_box_index: int = 0,
) -> dict:
    return {
        "kind": kind,
        "prefix": prefix,
        "box_ids": box_ids,
        "line_keys": line_keys,
        "params": params or {},
        "first_box_index": first_box_index,
        "helper": helper,
    }


def _infer_helper_prefix(box_ids: list[str], suffixes: list[str]) -> str:
    ordered = sorted(box_ids)
    for suffix in suffixes:
        for box_id in ordered:
            if suffix and box_id.endswith(suffix):
                prefix = box_id[:-len(suffix)]
                if prefix:
                    return prefix
    common = os.path.commonprefix(ordered).rstrip("_-")
    return common or ordered[0]


def _boxes_match_in_snapshot_order(
    candidate_boxes: list[dict],
    box_indices: dict[str, int],
    boxes_by_id: dict[str, dict],
) -> bool:
    candidate_box_ids = [box["id"] for box in iter_boxes(candidate_boxes)]
    actual_order = sorted(candidate_box_ids, key=lambda box_id: box_indices.get(box_id, 10 ** 9))
    if actual_order != candidate_box_ids:
        return False
    for box in iter_boxes(candidate_boxes):
        if boxes_by_id.get(box["id"]) != box:
            return False
    return True


def _lines_match_in_snapshot_order(
    snapshot: dict,
    candidate_lines: list[dict],
    candidate_box_ids: list[str],
) -> bool:
    actual_lines = []
    candidate_id_set = set(candidate_box_ids)
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
        source = patchline.get("source", [None, 0])[0]
        destination = patchline.get("destination", [None, 0])[0]
        if source in candidate_id_set and destination in candidate_id_set:
            actual_lines.append(wrapped)
    return actual_lines == candidate_lines


def _live_api_helper_box_attrs(box: dict, excluded_keys: list[str]) -> dict:
    return {
        key: copy.deepcopy(value)
        for key, value in box.items()
        if key not in set(excluded_keys)
    }


def _live_api_include_default_style(*boxes: dict) -> bool:
    return all("fontname" in box and "fontsize" in box for box in boxes if box is not None)


def _adjacent_message_boxes_for_component(
    snapshot: dict,
    component_box_ids: list[str],
    boxes_by_id: dict[str, dict],
) -> list[dict]:
    component_id_set = set(component_box_ids)
    adjacent = []
    seen_ids = set()
    for patchline in iter_patchlines(snapshot):
        source_id = patchline.get("source", [None, 0])[0]
        dest_id = patchline.get("destination", [None, 0])[0]
        neighbor_id = None
        if source_id in component_id_set and dest_id not in component_id_set:
            neighbor_id = dest_id
        elif dest_id in component_id_set and source_id not in component_id_set:
            neighbor_id = source_id
        if neighbor_id is None or neighbor_id in seen_ids:
            continue
        neighbor = boxes_by_id.get(neighbor_id)
        if neighbor and neighbor.get("maxclass") == "message":
            adjacent.append(neighbor)
            seen_ids.add(neighbor_id)
    return sorted(adjacent, key=lambda box: box.get("id") or "")


def _adjacent_property_message_box(
    snapshot: dict,
    component_box_ids: list[str],
    boxes_by_id: dict[str, dict],
    *,
    prop: str | None = None,
) -> dict | None:
    property_boxes = []
    for box in _adjacent_message_boxes_for_component(snapshot, component_box_ids, boxes_by_id):
        text = str(box.get("text", "")).strip()
        if not text.startswith("property "):
            continue
        value = text[len("property "):].strip()
        if prop is not None and value != prop:
            continue
        property_boxes.append(box)
    if len(property_boxes) == 1:
        return property_boxes[0]
    return None


def _message_segments(text: str) -> list[str]:
    return [segment.strip() for segment in str(text).split(",") if segment.strip()]


def _adjacent_probe_message_box(
    snapshot: dict,
    component_box_ids: list[str],
    boxes_by_id: dict[str, dict],
) -> dict | None:
    probe_boxes = []
    for box in _adjacent_message_boxes_for_component(snapshot, component_box_ids, boxes_by_id):
        text = str(box.get("text", "")).strip()
        segments = _message_segments(text)
        if not segments:
            continue
        parsed = _parse_live_api_message_text(text)
        if not (parsed["gets"] or parsed["calls"]):
            continue
        if parsed["paths"] or parsed["properties"] or parsed["sets"]:
            continue
        probe_boxes.append(box)
    if len(probe_boxes) == 1:
        return probe_boxes[0]
    return None


def _line_source_outlet_to_destination(
    snapshot: dict,
    source_id: str,
    destination_id: str,
) -> int | None:
    matches = []
    for patchline in iter_patchlines(snapshot):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        if source[0] == source_id and destination[0] == destination_id:
            matches.append(int(source[1]))
    if len(matches) == 1:
        return matches[0]
    return None


def _line_attrs_from_snapshot(
    snapshot: dict,
    source_id: str,
    source_outlet: int,
    destination_id: str,
    destination_inlet: int,
) -> dict:
    for patchline in iter_patchlines(snapshot):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        if source == [source_id, source_outlet] and destination == [destination_id, destination_inlet]:
            return {
                key: copy.deepcopy(value)
                for key, value in patchline.items()
                if key not in {"source", "destination"}
            }
    return {}


def _line_index_in_snapshot(
    snapshot: dict,
    source_id: str,
    source_outlet: int,
    destination_id: str,
    destination_inlet: int,
) -> int | None:
    for index, patchline in enumerate(iter_patchlines(snapshot)):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        if source == [source_id, source_outlet] and destination == [destination_id, destination_inlet]:
            return index
    return None


def _component_internal_line_keys(snapshot: dict, component_box_ids: list[str]) -> list[tuple]:
    component_id_set = set(component_box_ids)
    line_keys = []
    for patchline in iter_patchlines(snapshot):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        if source[0] in component_id_set and destination[0] in component_id_set:
            line_keys.append(_line_key(source[0], source[1], destination[0], destination[1]))
    return line_keys


def _ordered_box_ids(box_ids: list[str], box_indices: dict[str, int]) -> list[str]:
    return sorted(dict.fromkeys(box_ids), key=lambda box_id: box_indices.get(box_id, 10 ** 9))


def _live_api_helper_call_from_snapshot(
    snapshot: dict,
    boxes_by_id: dict[str, dict],
    box_indices: dict[str, int],
    *,
    helper_name: str,
    prefix: str,
    component_box_ids: list[str],
    params: dict[str, Any],
) -> dict:
    ordered_component_ids = _ordered_box_ids(component_box_ids, box_indices)
    operator_ids: dict[str, list[str]] = {}
    for box_id in ordered_component_ids:
        operator = _box_operator(boxes_by_id.get(box_id, {}))
        if operator:
            operator_ids.setdefault(operator, []).append(box_id)

    helper_kwargs: dict[str, Any] = {}
    consume_box_ids = list(ordered_component_ids)

    if helper_name in {"live_object_path", "live_set_control", "live_observer", "live_parameter_probe"}:
        path_id = operator_ids.get("live.path", [None])[0]
        path_box = boxes_by_id.get(path_id or "")
        if path_box is not None:
            helper_kwargs["path_id"] = path_id
            helper_kwargs["path_rect"] = copy.deepcopy(path_box.get("patching_rect"))
            helper_kwargs["path_attrs"] = _live_api_helper_box_attrs(
                path_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
            helper_kwargs["path"] = params.get("path", "live_set")
        elif helper_name == "live_parameter_probe":
            helper_kwargs["path"] = None

    if helper_name in {"live_object_path", "live_set_control", "live_parameter_probe"}:
        object_id = operator_ids.get("live.object", [None])[0]
        object_box = boxes_by_id.get(object_id or "")
        route_box = None
        trigger_box = None
        if object_box is not None:
            helper_kwargs["object_id"] = object_id
            helper_kwargs["object_rect"] = copy.deepcopy(object_box.get("patching_rect"))
            helper_kwargs["object_attrs"] = _live_api_helper_box_attrs(
                object_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        if helper_name == "live_set_control":
            helper_kwargs["prop"] = params.get("prop", "tempo")
        elif helper_name == "live_parameter_probe":
            message_box = _adjacent_probe_message_box(snapshot, ordered_component_ids, boxes_by_id)
            if message_box is not None:
                helper_kwargs["message_id"] = message_box.get("id")
                helper_kwargs["message_rect"] = copy.deepcopy(message_box.get("patching_rect"))
                helper_kwargs["message_attrs"] = _live_api_helper_box_attrs(
                    message_box,
                    ["id", "maxclass", "text", "patching_rect"],
                )
                helper_kwargs["commands"] = _message_segments(str(message_box.get("text", "")))
                if object_box is not None and object_id:
                    helper_kwargs["message_line_attrs"] = _line_attrs_from_snapshot(
                        snapshot,
                        message_box.get("id"),
                        0,
                        object_id,
                        0,
                    )
                consume_box_ids.append(message_box.get("id"))
            route_id = operator_ids.get("route", [None])[0]
            route_box = boxes_by_id.get(route_id or "")
            if route_box is not None:
                route_text = str(route_box.get("text", "")).strip().split()[1:]
                helper_kwargs["route_id"] = route_id
                helper_kwargs["route_rect"] = copy.deepcopy(route_box.get("patching_rect"))
                helper_kwargs["route_attrs"] = _live_api_helper_box_attrs(
                    route_box,
                    ["id", "maxclass", "text", "patching_rect"],
                )
                helper_kwargs["route_selectors"] = route_text
                if message_box is not None and box_indices.get(route_id, 10 ** 9) < box_indices.get(message_box.get("id"), 10 ** 9):
                    helper_kwargs["route_before_message"] = True
                if object_box is not None and object_id:
                    helper_kwargs["route_line_attrs"] = _line_attrs_from_snapshot(
                        snapshot,
                        object_id,
                        0,
                        route_id,
                        0,
                    )
                consume_box_ids.append(route_id)
            trigger_id = operator_ids.get("t", [None])[0]
            trigger_box = boxes_by_id.get(trigger_id or "")
            if trigger_box is not None:
                helper_kwargs["trigger_id"] = trigger_id
                helper_kwargs["trigger_text"] = str(trigger_box.get("text", "")).strip()
                helper_kwargs["trigger_rect"] = copy.deepcopy(trigger_box.get("patching_rect"))
                helper_kwargs["trigger_attrs"] = _live_api_helper_box_attrs(
                    trigger_box,
                    ["id", "maxclass", "text", "patching_rect"],
                )
                if message_box is not None and message_box.get("id"):
                    outlet = _line_source_outlet_to_destination(
                        snapshot,
                        trigger_id,
                        message_box.get("id"),
                    )
                    if outlet is not None:
                        helper_kwargs["message_from_trigger_outlet"] = outlet
                        helper_kwargs["trigger_message_line_attrs"] = _line_attrs_from_snapshot(
                            snapshot,
                            trigger_id,
                            outlet,
                            message_box.get("id"),
                            0,
                        )
                if object_box is not None and object_id:
                    outlet = _line_source_outlet_to_destination(
                        snapshot,
                        trigger_id,
                        object_id,
                    )
                    if outlet is not None:
                        helper_kwargs["object_from_trigger_outlet"] = outlet
                        helper_kwargs["trigger_object_line_attrs"] = _line_attrs_from_snapshot(
                            snapshot,
                            trigger_id,
                            outlet,
                            object_id,
                            0,
                        )
                consume_box_ids.append(trigger_id)
            order_pairs = []
            if path_box is not None:
                order_pairs.append((box_indices.get(path_id, 10 ** 9), "path"))
            if trigger_box is not None and trigger_id:
                order_pairs.append((box_indices.get(trigger_id, 10 ** 9), "trigger"))
            if object_box is not None:
                order_pairs.append((box_indices.get(object_id, 10 ** 9), "object"))
            if route_box is not None:
                order_pairs.append((box_indices.get(route_id, 10 ** 9), "route"))
            if message_box is not None and message_box.get("id"):
                order_pairs.append((box_indices.get(message_box.get("id"), 10 ** 9), "message"))
            helper_kwargs["box_order"] = [name for _idx, name in sorted(order_pairs)]
        helper_kwargs["include_default_style"] = _live_api_include_default_style(
            *(
                box for box in (
                    path_box,
                    object_box,
                    route_box if helper_name == "live_parameter_probe" else None,
                    trigger_box if helper_name == "live_parameter_probe" else None,
                ) if box is not None
            )
        )

    elif helper_name == "live_observer":
        via_object = params.get("via_object", True)
        helper_kwargs["via_object"] = via_object
        observer_id = operator_ids.get("live.observer", [None])[0]
        observer_box = boxes_by_id.get(observer_id or "")
        if observer_box is not None:
            helper_kwargs["observer_id"] = observer_id
            helper_kwargs["observer_rect"] = copy.deepcopy(observer_box.get("patching_rect"))
            helper_kwargs["observer_attrs"] = _live_api_helper_box_attrs(
                observer_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        helper_kwargs["prop"] = params.get("prop", "tempo")
        style_boxes = [box for box in (path_box, observer_box) if box is not None]
        if via_object:
            object_id = operator_ids.get("live.object", [None])[0]
            object_box = boxes_by_id.get(object_id or "")
            if object_box is not None:
                helper_kwargs["object_id"] = object_id
                helper_kwargs["object_rect"] = copy.deepcopy(object_box.get("patching_rect"))
                helper_kwargs["object_attrs"] = _live_api_helper_box_attrs(
                    object_box,
                    ["id", "maxclass", "text", "patching_rect"],
                )
                style_boxes.append(object_box)
        property_box = None
        if params.get("bind_via_message"):
            property_box = _adjacent_property_message_box(
                snapshot,
                ordered_component_ids,
                boxes_by_id,
                prop=params.get("prop"),
            )
            if property_box is not None:
                helper_kwargs["bind_via_message"] = True
                helper_kwargs["property_id"] = property_box.get("id")
                helper_kwargs["property_rect"] = copy.deepcopy(property_box.get("patching_rect"))
                helper_kwargs["property_attrs"] = _live_api_helper_box_attrs(
                    property_box,
                    ["id", "maxclass", "text", "patching_rect"],
                )
                consume_box_ids.append(property_box.get("id"))
        helper_kwargs["include_default_style"] = _live_api_include_default_style(*style_boxes)

    elif helper_name == "live_state_observer":
        device_id = operator_ids.get("live.thisdevice", [None])[0]
        path_id = operator_ids.get("live.path", [None])[0]
        observer_id = operator_ids.get("live.observer", [None])[0]
        selector_id = operator_ids.get("sel", [None])[0]
        trigger_ids = operator_ids.get("t", [])
        device_box = boxes_by_id.get(device_id or "")
        path_box = boxes_by_id.get(path_id or "")
        observer_box = boxes_by_id.get(observer_id or "")
        selector_box = boxes_by_id.get(selector_id or "")
        property_box = None
        for box_id in ordered_component_ids:
            box = boxes_by_id.get(box_id)
            if box is None or box.get("maxclass") != "message":
                continue
            text = str(box.get("text", "")).strip()
            if not text.startswith("property "):
                continue
            value = text[len("property "):].strip()
            if params.get("prop") is not None and value != params.get("prop"):
                continue
            property_box = box
            break
        if property_box is None:
            property_box = _adjacent_property_message_box(
                snapshot,
                ordered_component_ids,
                boxes_by_id,
                prop=params.get("prop"),
            )
        init_trigger_id = None
        value_trigger_id = None
        for trigger_id in trigger_ids:
            if property_box is not None and path_id:
                to_property = _line_source_outlet_to_destination(snapshot, trigger_id, property_box.get("id"))
                to_path = _line_source_outlet_to_destination(snapshot, trigger_id, path_id)
                if to_property is not None and to_path is not None:
                    init_trigger_id = trigger_id
            if observer_id and selector_id:
                from_observer = _line_source_outlet_to_destination(snapshot, observer_id, trigger_id)
                to_selector = _line_source_outlet_to_destination(snapshot, trigger_id, selector_id)
                if from_observer is not None and to_selector is not None:
                    value_trigger_id = trigger_id
        init_trigger_box = boxes_by_id.get(init_trigger_id or "")
        value_trigger_box = boxes_by_id.get(value_trigger_id or "")
        if device_box is not None:
            helper_kwargs["device_id"] = device_id
            helper_kwargs["device_rect"] = copy.deepcopy(device_box.get("patching_rect"))
            helper_kwargs["device_attrs"] = _live_api_helper_box_attrs(
                device_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        if init_trigger_box is not None:
            helper_kwargs["init_trigger_id"] = init_trigger_id
            helper_kwargs["init_trigger_text"] = str(init_trigger_box.get("text", "")).strip()
            helper_kwargs["init_trigger_rect"] = copy.deepcopy(init_trigger_box.get("patching_rect"))
            helper_kwargs["init_trigger_attrs"] = _live_api_helper_box_attrs(
                init_trigger_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        if path_box is not None:
            helper_kwargs["path_id"] = path_id
            helper_kwargs["path_rect"] = copy.deepcopy(path_box.get("patching_rect"))
            helper_kwargs["path_attrs"] = _live_api_helper_box_attrs(
                path_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
            helper_kwargs["path"] = params.get("path", "live_set")
        if property_box is not None:
            helper_kwargs["property_id"] = property_box.get("id")
            helper_kwargs["property_rect"] = copy.deepcopy(property_box.get("patching_rect"))
            helper_kwargs["property_attrs"] = _live_api_helper_box_attrs(
                property_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
            consume_box_ids.append(property_box.get("id"))
        if observer_box is not None:
            helper_kwargs["observer_id"] = observer_id
            helper_kwargs["observer_rect"] = copy.deepcopy(observer_box.get("patching_rect"))
            helper_kwargs["observer_attrs"] = _live_api_helper_box_attrs(
                observer_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        if value_trigger_box is not None:
            helper_kwargs["value_trigger_id"] = value_trigger_id
            helper_kwargs["value_trigger_text"] = str(value_trigger_box.get("text", "")).strip()
            helper_kwargs["value_trigger_rect"] = copy.deepcopy(value_trigger_box.get("patching_rect"))
            helper_kwargs["value_trigger_attrs"] = _live_api_helper_box_attrs(
                value_trigger_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        if selector_box is not None:
            helper_kwargs["selector_id"] = selector_id
            helper_kwargs["selector_text"] = str(selector_box.get("text", "")).strip()
            helper_kwargs["selector_rect"] = copy.deepcopy(selector_box.get("patching_rect"))
            helper_kwargs["selector_attrs"] = _live_api_helper_box_attrs(
                selector_box,
                ["id", "maxclass", "text", "patching_rect"],
            )

        helper_kwargs["prop"] = params.get("prop", "scale_mode")
        if device_id and init_trigger_id:
            outlet = _line_source_outlet_to_destination(snapshot, device_id, init_trigger_id)
            if outlet is not None:
                helper_kwargs["device_to_init_outlet"] = outlet
                helper_kwargs["device_to_init_line_attrs"] = _line_attrs_from_snapshot(
                    snapshot, device_id, outlet, init_trigger_id, 0
                )
        if init_trigger_id and property_box is not None:
            outlet = _line_source_outlet_to_destination(snapshot, init_trigger_id, property_box.get("id"))
            if outlet is not None:
                helper_kwargs["init_to_property_outlet"] = outlet
                helper_kwargs["init_to_property_line_attrs"] = _line_attrs_from_snapshot(
                    snapshot, init_trigger_id, outlet, property_box.get("id"), 0
                )
        if init_trigger_id and path_id:
            outlet = _line_source_outlet_to_destination(snapshot, init_trigger_id, path_id)
            if outlet is not None:
                helper_kwargs["init_to_path_outlet"] = outlet
                helper_kwargs["init_to_path_line_attrs"] = _line_attrs_from_snapshot(
                    snapshot, init_trigger_id, outlet, path_id, 0
                )
        if property_box is not None and observer_id:
            helper_kwargs["property_to_observer_line_attrs"] = _line_attrs_from_snapshot(
                snapshot, property_box.get("id"), 0, observer_id, 0
            )
        if path_id and observer_id:
            outlet = _line_source_outlet_to_destination(snapshot, path_id, observer_id)
            if outlet is not None:
                helper_kwargs["path_to_observer_outlet"] = outlet
                helper_kwargs["path_to_observer_line_attrs"] = _line_attrs_from_snapshot(
                    snapshot, path_id, outlet, observer_id, 1
                )
        if observer_id and value_trigger_id:
            outlet = _line_source_outlet_to_destination(snapshot, observer_id, value_trigger_id)
            if outlet is not None:
                helper_kwargs["observer_to_value_outlet"] = outlet
                helper_kwargs["observer_to_value_line_attrs"] = _line_attrs_from_snapshot(
                    snapshot, observer_id, outlet, value_trigger_id, 0
                )
        if value_trigger_id and selector_id:
            outlet = _line_source_outlet_to_destination(snapshot, value_trigger_id, selector_id)
            if outlet is not None:
                helper_kwargs["value_to_selector_outlet"] = outlet
                helper_kwargs["value_to_selector_line_attrs"] = _line_attrs_from_snapshot(
                    snapshot, value_trigger_id, outlet, selector_id, 0
                )

        line_order_pairs = []
        line_specs = [
            ("device_to_init", device_id, helper_kwargs.get("device_to_init_outlet", 0), init_trigger_id, 0),
            ("init_to_property", init_trigger_id, helper_kwargs.get("init_to_property_outlet", 0), property_box.get("id") if property_box is not None else None, 0),
            ("init_to_path", init_trigger_id, helper_kwargs.get("init_to_path_outlet", 1), path_id, 0),
            ("property_to_observer", property_box.get("id") if property_box is not None else None, 0, observer_id, 0),
            ("path_to_observer", path_id, helper_kwargs.get("path_to_observer_outlet", 1), observer_id, 1),
            ("observer_to_value", observer_id, helper_kwargs.get("observer_to_value_outlet", 0), value_trigger_id, 0),
            ("value_to_selector", value_trigger_id, helper_kwargs.get("value_to_selector_outlet", 0), selector_id, 0),
        ]
        for name, source_id, source_outlet, dest_id, dest_inlet in line_specs:
            if source_id is None or dest_id is None:
                continue
            index = _line_index_in_snapshot(snapshot, source_id, source_outlet, dest_id, dest_inlet)
            if index is not None:
                line_order_pairs.append((index, name))
        helper_kwargs["line_order"] = [name for _idx, name in sorted(line_order_pairs)]

        order_pairs = []
        for box_id, name in [
            (device_id, "device"),
            (init_trigger_id, "init_trigger"),
            (path_id, "path"),
            (property_box.get("id") if property_box is not None else None, "property"),
            (observer_id, "observer"),
            (value_trigger_id, "value_trigger"),
            (selector_id, "selector"),
        ]:
            if box_id:
                order_pairs.append((box_indices.get(box_id, 10 ** 9), name))
        helper_kwargs["box_order"] = [name for _idx, name in sorted(order_pairs)]
        helper_kwargs["include_default_style"] = _live_api_include_default_style(
            *(box for box in (device_box, init_trigger_box, path_box, observer_box, value_trigger_box, selector_box) if box is not None)
        )

    elif helper_name == "live_thisdevice":
        device_id = operator_ids.get("live.thisdevice", [None])[0]
        device_box = boxes_by_id.get(device_id or "")
        if device_box is not None:
            helper_kwargs["device_id"] = device_id
            helper_kwargs["device_rect"] = copy.deepcopy(device_box.get("patching_rect"))
            helper_kwargs["device_attrs"] = _live_api_helper_box_attrs(
                device_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
            helper_kwargs["include_default_style"] = _live_api_include_default_style(device_box)

    elif helper_name == "device_active_state":
        device_id = operator_ids.get("live.thisdevice", [None])[0]
        prepend_id = operator_ids.get("prepend", [None])[0]
        device_box = boxes_by_id.get(device_id or "")
        prepend_box = boxes_by_id.get(prepend_id or "")
        if device_box is not None:
            helper_kwargs["device_id"] = device_id
            helper_kwargs["device_rect"] = copy.deepcopy(device_box.get("patching_rect"))
            helper_kwargs["device_attrs"] = _live_api_helper_box_attrs(
                device_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        if prepend_box is not None:
            helper_kwargs["prepend_id"] = prepend_id
            helper_kwargs["prepend_rect"] = copy.deepcopy(prepend_box.get("patching_rect"))
            helper_kwargs["prepend_attrs"] = _live_api_helper_box_attrs(
                prepend_box,
                ["id", "maxclass", "text", "patching_rect"],
            )
        device_to_prepend_outlet = None
        if device_id and prepend_id:
            device_to_prepend_outlet = _line_source_outlet_to_destination(
                snapshot,
                device_id,
                prepend_id,
            )
        if device_to_prepend_outlet is not None:
            helper_kwargs["from_device_outlet"] = device_to_prepend_outlet
            helper_kwargs["device_to_prepend_line_attrs"] = _line_attrs_from_snapshot(
                snapshot,
                device_id,
                device_to_prepend_outlet,
                prepend_id,
                0,
            )
        elif device_id and prepend_id:
            helper_kwargs["prepend_to_device_line_attrs"] = _line_attrs_from_snapshot(
                snapshot,
                prepend_id,
                0,
                device_id,
                0,
            )
        order_pairs = []
        if prepend_box is not None and prepend_id:
            order_pairs.append((box_indices.get(prepend_id, 10 ** 9), "prepend"))
        if device_box is not None and device_id:
            order_pairs.append((box_indices.get(device_id, 10 ** 9), "device"))
        helper_kwargs["box_order"] = [name for _idx, name in sorted(order_pairs)]
        helper_kwargs["include_default_style"] = _live_api_include_default_style(
            *(box for box in (prepend_box, device_box) if box is not None)
        )

    consume_box_ids = _ordered_box_ids(
        [box_id for box_id in consume_box_ids if box_id],
        box_indices,
    )
    return {
        "name": helper_name,
        "positional": [prefix],
        "kwargs": helper_kwargs,
        "consume_box_ids": consume_box_ids,
        "line_keys": _component_internal_line_keys(snapshot, consume_box_ids),
    }


def _canonical_live_api_helper_match(
    snapshot: dict,
    boxes_by_id: dict[str, dict],
    box_indices: dict[str, int],
    *,
    kind: str,
    box_ids: list[str],
    helper_name: str,
    helper_fn,
    helper_positional: list[Any],
    helper_kwargs: dict[str, Any],
    params: dict | None = None,
) -> dict | None:
    candidate_boxes, candidate_lines = helper_fn(*helper_positional, **helper_kwargs)
    candidate_box_ids = [box["id"] for box in iter_boxes(candidate_boxes)]
    if sorted(candidate_box_ids) != sorted(box_ids):
        return None
    if not _boxes_match_in_snapshot_order(candidate_boxes, box_indices, boxes_by_id):
        return None
    if not _lines_match_in_snapshot_order(snapshot, candidate_lines, candidate_box_ids):
        return None
    return _semantic_helper_match(
        kind=kind,
        prefix=helper_positional[0],
        box_ids=candidate_box_ids,
        line_keys=[_line_key_from_wrapped(line) for line in candidate_lines],
        params=params,
        helper={
            "name": helper_name,
            "positional": helper_positional,
            "kwargs": helper_kwargs,
        },
        first_box_index=min(box_indices.get(box_id, 10 ** 9) for box_id in candidate_box_ids),
    )


def _box_parameter_matches(
    box: dict,
    *,
    maxclass: str,
    varname: str,
    min_val: float,
    max_val: float,
    initial: float,
    unitstyle: int,
    annotation_name: str | None = None,
) -> bool:
    if box.get("maxclass") != maxclass or box.get("varname") != varname:
        return False
    spec = _parameter_spec_from_box(box)
    if spec is None:
        return False
    if spec.get("min") != min_val or spec.get("max") != max_val:
        return False
    if spec.get("initial") != initial or spec.get("unitstyle") != unitstyle:
        return False
    if annotation_name is not None:
        # annotation_name now lives in the param valueof (A2), not as a box attr.
        vo = box.get("saved_attribute_attributes", {}).get("valueof", {})
        if vo.get("parameter_annotation_name") != annotation_name:
            return False
    return True


def _line_keys_present(line_keys: set[tuple], required_line_keys: list[tuple]) -> bool:
    return all(line_key in line_keys for line_key in required_line_keys)


def _canonical_recipe_subset(
    recipe_name: str,
    prefix: str,
    positional: list[Any],
    kwargs: dict[str, Any],
) -> tuple[dict[str, dict], set[tuple]]:
    recipe_device = Device("Recipe Check", 10, 10, device_type="audio_effect")
    recipe_fn = {
        "gain_controlled_stage": gain_controlled_stage,
        "dry_wet_stage": dry_wet_stage,
        "midi_note_gate": midi_note_gate,
        "tempo_synced_delay": tempo_synced_delay,
        "transport_sync_lfo_recipe": transport_sync_lfo_recipe,
    }[recipe_name]
    recipe_fn(recipe_device, prefix, *positional, **kwargs)
    recipe_boxes = _boxes_by_id(recipe_device)
    recipe_lines = {_line_key_from_wrapped(line) for line in recipe_device.lines}
    return recipe_boxes, recipe_lines


def _recipeizable_subset_matches(
    *,
    recipe_name: str,
    prefix: str,
    positional: list[Any],
    kwargs: dict[str, Any],
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
) -> bool:
    recipe_boxes, recipe_lines = _canonical_recipe_subset(recipe_name, prefix, positional, kwargs)
    for box_id, expected_box in recipe_boxes.items():
        if boxes_by_id.get(box_id) != expected_box:
            return False
    return recipe_lines.issubset(line_keys)


def _sample_buffer_component_label(box: dict) -> str | None:
    operator = _box_operator(box)
    if operator in SAMPLE_BUFFER_CORE_OPERATORS or operator in SAMPLE_BUFFER_HELPER_OPERATORS:
        return operator
    if box.get("maxclass") == "live.drop":
        return "live.drop"
    return None


def _gen_processing_component_label(box: dict) -> str | None:
    operator = _box_operator(box)
    if operator in GEN_PROCESSING_CORE_OPERATORS or operator in GEN_PROCESSING_HELPER_OPERATORS:
        return operator
    return None


def _helper_opportunity(
    *,
    helper_name: str,
    prefix: str,
    box_ids: list[str],
    params: dict | None = None,
    blocking_factors: list[str] | None = None,
    first_box_index: int = 0,
) -> dict:
    return {
        "helper_name": helper_name,
        "prefix": prefix,
        "box_ids": sorted(box_ids),
        "params": params or {},
        "blocking_factors": sorted(set(blocking_factors or [])),
        "first_box_index": first_box_index,
        "exact": False,
    }


def _live_api_normalization_level(blocking_factors: list[str]) -> str:
    blockers = set(blocking_factors)
    if "extra_component_boxes" in blockers:
        return "manual_review"
    if "indirect_property_binding" in blockers:
        return "normalized_with_binding"
    return "normalized_safe"


def _live_api_semantic_helper_call(
    snapshot: dict,
    boxes_by_id: dict[str, dict],
    box_indices: dict[str, int],
    *,
    helper_name: str,
    prefix: str,
    box_ids: list[str],
    params: dict[str, Any],
) -> dict:
    return _live_api_helper_call_from_snapshot(
        snapshot,
        boxes_by_id,
        box_indices,
        helper_name=helper_name,
        prefix=prefix,
        component_box_ids=box_ids,
        params=params,
    )


def _line_keys_for_box_ids(snapshot: dict, box_ids: set[str]) -> list[tuple]:
    line_keys = []
    for patchline in iter_patchlines(snapshot):
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        if source[0] in box_ids and destination[0] in box_ids:
            line_keys.append(_line_key(source[0], source[1], destination[0], destination[1]))
    return line_keys


def _root_object_name_counts(boxes_by_id: dict[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for box in boxes_by_id.values():
        maxclass = box.get("maxclass")
        name = None
        if maxclass == "newobj":
            text = str(box.get("text", "")).strip()
            if text:
                name = text.split()[0]
        elif maxclass in {"message", "comment"}:
            name = str(maxclass)
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


def _motif_semantic_candidate(
    snapshot: dict,
    motif: dict,
    *,
    candidate_name: str,
    evidence: list[str],
) -> dict:
    return {
        "candidate_name": candidate_name,
        "box_ids": copy.deepcopy(motif.get("box_ids", [])),
        "line_keys": _line_keys_for_box_ids(snapshot, set(motif.get("box_ids", []))),
        "motif_kinds": [motif.get("kind")],
        "params": copy.deepcopy(motif.get("params", {})),
        "evidence": evidence,
        "normalization_level": "semantic_pattern",
        "first_box_index": motif.get("first_box_index", 0),
        "helper_name": None,
        "exact": False,
    }


def _candidate_helper_boxes(candidate: dict) -> list[dict]:
    return copy.deepcopy(candidate.get("helper_call", {}).get("kwargs", {}).get("boxes", []))


def _candidate_named_bus_texts(candidate: dict) -> list[str]:
    names = []
    for box in iter_boxes(_candidate_helper_boxes(candidate)):
        text = str(box.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("s ") or text.startswith("r "):
            names.append(text.split(" ", 1)[1].strip())
    return names


def _candidate_bpatcher_names(candidate: dict) -> list[str]:
    names = []
    for box in iter_boxes(_candidate_helper_boxes(candidate)):
        if box.get("maxclass") != "bpatcher":
            continue
        name = str(box.get("name") or "").strip()
        if name:
            names.append(name)
    return sorted(set(names))


def _indexed_name_signatures(names: list[str]) -> dict[str, list[int]]:
    signatures: dict[str, list[int]] = {}
    for name in names:
        match = re.match(r"^(.*?)(\d+)$", name)
        if not match:
            continue
        prefix, suffix = match.groups()
        signatures.setdefault(prefix, []).append(int(suffix))
    for prefix in signatures:
        signatures[prefix] = sorted(set(signatures[prefix]))
    return signatures


def _first_party_abstraction_family(abstraction_names: list[str]) -> str | None:
    names = set(abstraction_names)
    if names & {"M4L.gain1~", "M4L.gain2~"}:
        return "gain_shell"
    if names & {"M4L.bal1~", "M4L.bal2~"}:
        return "balance_shell"
    if names & {"M4L.pan1~", "M4L.pan2~"}:
        return "pan_shell"
    if "M4L.envfol~" in names:
        return "envelope_follower_shell"
    if "M4L.vdelay~" in names:
        return "variable_delay_shell"
    if "M4L.cross1~" in names:
        return "mid_side_shell"
    if any(name.startswith("M4L.api.") for name in names):
        return "api_internal_shell"
    return None


def _embedded_snapshot_from_patcher_dict(patcher_dict: dict) -> dict:
    return {
        "schema_version": 1,
        "source": {
            "kind": "embedded_patcher",
        },
        "device": {
            "name": patcher_dict.get("name", "Embedded"),
            "device_type": "audio_effect",
            "width": 0.0,
            "height": 0.0,
        },
        "patcher": {"patcher": copy.deepcopy(patcher_dict)},
        "boxes": copy.deepcopy(patcher_dict.get("boxes", [])),
        "lines": copy.deepcopy(patcher_dict.get("lines", [])),
        "dependencies": _dedupe_dependencies(patcher_dict.get("dependency_cache", [])),
        "parameterbanks": copy.deepcopy(
            patcher_dict.get("parameters", {}).get("parameterbanks", {})
        ),
        "support_files": [],
        "missing_support_files": [],
        "fidelity": {
            "exact_patcher_dict": True,
            "has_line_data": True,
            "rebuild_strategy": "embedded_patcher",
        },
    }


def _ui_role(box: dict) -> str:
    maxclass = box.get("maxclass")
    if maxclass == "live.comment":
        return "label"
    if maxclass in {"live.scope~", "live.meter~"}:
        return "monitor"
    if maxclass in {"jsui", "v8ui"}:
        return "custom_ui"
    if maxclass == "bpatcher":
        return "embedded_patcher"
    return "widget"


def _support_file_kind(name: str) -> str:
    lowered = name.lower()
    if lowered.endswith(".js"):
        return "javascript"
    if lowered.endswith(".json"):
        return "json"
    if lowered.endswith(".jsui"):
        return "jsui"
    if lowered.endswith(".svg"):
        return "svg"
    if lowered.endswith(".png"):
        return "image"
    return "text"


def _named_bus_networks(root_motifs: list[dict], embedded_patchers: list[dict]) -> list[dict]:
    groups: dict[tuple[bool, str], dict[str, Any]] = {}

    def add_entry(
        *,
        name: str,
        signal: bool,
        sender_count: int,
        receiver_count: int,
        forms: list[str],
        scope: str,
        host_box_id: str | None,
        host_kind: str | None,
        target: str | None,
        depth: int,
    ) -> None:
        if not name:
            return
        key = (signal, name)
        network = groups.setdefault(key, {
            "name": name,
            "signal": signal,
            "total_sender_count": 0,
            "total_receiver_count": 0,
            "forms": set(),
            "scopes": [],
        })
        network["total_sender_count"] += int(sender_count)
        network["total_receiver_count"] += int(receiver_count)
        network["forms"].update(forms or [])
        network["scopes"].append({
            "scope": scope,
            "host_box_id": host_box_id,
            "host_kind": host_kind,
            "target": target,
            "depth": depth,
            "sender_count": int(sender_count),
            "receiver_count": int(receiver_count),
            "forms": sorted(set(forms or [])),
        })

    for motif in root_motifs:
        if motif.get("kind") != "named_bus":
            continue
        params = motif.get("params", {})
        add_entry(
            name=str(params.get("name") or ""),
            signal=bool(params.get("signal")),
            sender_count=int(params.get("sender_count", 0)),
            receiver_count=int(params.get("receiver_count", 0)),
            forms=copy.deepcopy(params.get("forms", [])),
            scope="root",
            host_box_id=None,
            host_kind="root",
            target=None,
            depth=0,
        )

    for embedded in embedded_patchers:
        for entry in embedded.get("named_bus_entries", []):
            add_entry(
                name=str(entry.get("name") or ""),
                signal=bool(entry.get("signal")),
                sender_count=int(entry.get("sender_count", 0)),
                receiver_count=int(entry.get("receiver_count", 0)),
                forms=copy.deepcopy(entry.get("forms", [])),
                scope="embedded",
                host_box_id=embedded.get("host_box_id"),
                host_kind=embedded.get("host_kind"),
                target=embedded.get("target"),
                depth=int(embedded.get("depth", 0) or 0),
            )

    networks = []
    for network in groups.values():
        scopes = sorted(
            network["scopes"],
            key=lambda entry: (
                int(entry.get("depth", 0)),
                entry.get("scope", ""),
                entry.get("host_box_id") or "",
            ),
        )
        networks.append({
            "name": network["name"],
            "signal": network["signal"],
            "total_sender_count": network["total_sender_count"],
            "total_receiver_count": network["total_receiver_count"],
            "forms": sorted(network["forms"]),
            "scope_count": len(scopes),
            "embedded_scope_count": sum(1 for scope in scopes if scope.get("scope") == "embedded"),
            "cross_scope": len(scopes) > 1,
            "scopes": scopes,
        })

    networks.sort(
        key=lambda entry: (
            -int(entry.get("scope_count", 0)),
            -int(entry.get("total_sender_count", 0) + entry.get("total_receiver_count", 0)),
            entry.get("name", ""),
        )
    )
    return networks


def _snapshot_object_texts(snapshot: dict) -> list[str]:
    texts = []
    for box in iter_boxes(snapshot):
        text = str(box.get("text") or "").strip()
        name = str(box.get("name") or "").strip()
        varname = str(box.get("varname") or "").strip()
        if text:
            texts.append(text)
        if name:
            texts.append(name)
        if varname:
            texts.append(varname)
    return texts


def _snapshot_contains_all_texts(snapshot: dict, required: list[str]) -> bool:
    texts = _snapshot_object_texts(snapshot)
    return all(any(text == candidate for candidate in texts) for text in required)


def _finalize_snapshot(snapshot: dict) -> dict:
    from .reverse_snapshot import _finalize_snapshot as _snapshot_finalize

    return _snapshot_finalize(snapshot)


def _snapshot_uses_default_audio_io(snapshot: dict) -> bool:
    if snapshot.get("device", {}).get("device_type") != "audio_effect":
        return False

    boxes_by_id = _boxes_by_id(snapshot)
    for box_id, defaults in DEFAULT_AUDIO_IO_BOXES.items():
        box = boxes_by_id.get(box_id)
        if not box:
            return False
        for key, expected in defaults.items():
            if box.get(key) != expected:
                return False
    return True


def _is_bridge_runtime_box(box: dict) -> bool:
    text = str(box.get("text", ""))
    return any(marker in text for marker in BRIDGE_TEXT_MARKERS)


def _read_amxd_chunks(data: bytes) -> dict[bytes, bytes]:
    from .reverse_snapshot import _read_amxd_chunks as _snapshot_read_amxd_chunks

    return _snapshot_read_amxd_chunks(data)


def _decode_patcher_chunk(payload: bytes) -> dict:
    from .reverse_snapshot import _decode_patcher_chunk as _snapshot_decode_patcher_chunk

    return _snapshot_decode_patcher_chunk(payload)


def read_amxd(path: str) -> dict:
    """Read an .amxd container and return its patcher plus inferred metadata."""
    from .reverse_snapshot import read_amxd as _read_amxd

    return _read_amxd(path)


def snapshot_from_device(device: Device) -> dict:
    """Capture a normalized snapshot from an in-memory Device instance."""
    from .reverse_snapshot import snapshot_from_device as _snapshot_from_device

    return _snapshot_from_device(device)


def snapshot_from_amxd(path: str) -> dict:
    """Capture a normalized snapshot from an .amxd file and nearby sidecars."""
    from .reverse_snapshot import snapshot_from_amxd as _snapshot_from_amxd

    return _snapshot_from_amxd(path)


def snapshot_from_bridge_payload(
    *,
    current_patcher: dict,
    boxes: list[dict],
    selected_device: dict | None = None,
    box_attrs: dict | None = None,
    patchlines: list[dict] | None = None,
    support_files: list[dict] | None = None,
) -> dict:
    """Capture a normalized snapshot from LiveMCP Max bridge payloads.

    This is a fidelity-limited reconstruction. It normalizes current patcher
    metadata, box summaries, optional box attrs, and optional patchline data
    into the same snapshot schema used for `.amxd` imports.
    """
    from .reverse_snapshot import (
        snapshot_from_bridge_payload as _snapshot_from_bridge_payload,
    )

    return _snapshot_from_bridge_payload(
        current_patcher=current_patcher,
        boxes=boxes,
        selected_device=selected_device,
        box_attrs=box_attrs,
        patchlines=patchlines,
        support_files=support_files,
    )


def snapshot_to_json(snapshot: dict, *, indent: int = 2) -> str:
    """Serialize a normalized snapshot to JSON."""
    from .reverse_snapshot import snapshot_to_json as _snapshot_to_json

    return _snapshot_to_json(snapshot, indent=indent)


def write_snapshot(snapshot: dict, path: str, *, indent: int = 2) -> int:
    """Write a normalized snapshot to disk as JSON."""
    from .reverse_snapshot import write_snapshot as _write_snapshot

    return _write_snapshot(snapshot, path, indent=indent)


def load_snapshot(path: str) -> dict:
    """Load a previously written normalized snapshot."""
    from .reverse_snapshot import load_snapshot as _load_snapshot

    return _load_snapshot(path)


def _python_literal(value: Any) -> str:
    return pprint.pformat(value, width=88, sort_dicts=False)


def _call_statement(method_name: str, positional: list[Any], kwargs: dict[str, Any]) -> str:
    lines = [f"    device.{method_name}("]
    for value in positional:
        lines.append(f"        {_python_literal(value)},")
    for key, value in kwargs.items():
        lines.append(f"        {key}={_python_literal(value)},")
    lines.append("    )")
    return "\n".join(lines)


def _dsp_add_statement(function_name: str, positional: list[Any], kwargs: dict[str, Any]) -> str:
    lines = [
        "    device.add_dsp(",
        f"        *{function_name}(",
    ]
    for value in positional:
        lines.append(f"            {_python_literal(value)},")
    for key, value in kwargs.items():
        lines.append(f"            {key}={_python_literal(value)},")
    lines.extend([
        "        )",
        "    )",
    ])
    return "\n".join(lines)


def _function_call_statement(function_name: str, positional: list[Any], kwargs: dict[str, Any]) -> str:
    lines = [f"    {function_name}("]
    for value in positional:
        lines.append(f"        {_python_literal(value)},")
    for key, value in kwargs.items():
        lines.append(f"        {key}={_python_literal(value)},")
    lines.append("    )")
    return "\n".join(lines)


def _recipe_call_statement(function_name: str, positional: list[Any], kwargs: dict[str, Any]) -> str:
    lines = [f"    {function_name}(", "        device,"]
    for value in positional:
        lines.append(f"        {_python_literal(value)},")
    for key, value in kwargs.items():
        lines.append(f"        {key}={_python_literal(value)},")
    lines.append("    )")
    return "\n".join(lines)


def _support_files_by_name(snapshot: dict) -> dict[str, dict]:
    return {
        support.get("name"): support
        for support in snapshot.get("support_files", [])
        if support.get("name")
    }


def _semantic_jsui_filenames(snapshot: dict, support_files_by_name: dict[str, dict]) -> set[str]:
    filenames = set()
    for box in iter_boxes(snapshot):
        filename = box.get("filename")
        if box.get("maxclass") in {"jsui", "v8ui"} and filename in support_files_by_name:
            filenames.add(filename)
    return filenames


def _support_file_statements(snapshot: dict, *, skipped_names: set[str] | None = None) -> list[str]:
    statements = []
    skipped_names = skipped_names or set()
    for support in snapshot.get("support_files", []):
        if support.get("name") in skipped_names:
            continue
        statements.append(
            _call_statement(
                "add_support_file",
                [support.get("name"), support.get("content", "")],
                {"file_type": support.get("type", "TEXT")},
            )
        )
    return statements


def _saved_valueof(box: dict) -> dict:
    return copy.deepcopy(box.get("saved_attribute_attributes", {}).get("valueof", {}))


def _base_box_kwargs(box: dict, excluded: list[str]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in box.items()
        if key not in excluded
    }


def _comment_kwargs(box: dict) -> dict[str, Any]:
    kwargs = _base_box_kwargs(
        box,
        [
            "id",
            "maxclass",
            "text",
            "presentation",
            "presentation_rect",
        ],
    )
    if "textjustification" in kwargs:
        kwargs["justification"] = kwargs.pop("textjustification")
    return kwargs


def _parameter_box_common_kwargs(box: dict, *, include_shortname: bool = True) -> dict[str, Any]:
    valueof = _saved_valueof(box)
    kwargs = _base_box_kwargs(
        box,
        [
            "id",
            "maxclass",
            "varname",
            "presentation",
            "presentation_rect",
            "saved_attribute_attributes",
            "parameter_enable",
            "numinlets",
            "numoutlets",
            "outlettype",
        ],
    )
    if include_shortname:
        shortname = valueof.get("parameter_shortname")
        if shortname and shortname != box.get("varname"):
            kwargs["shortname"] = shortname
    initial = valueof.get("parameter_initial")
    if isinstance(initial, list) and initial:
        kwargs["initial"] = initial[0]
    if "parameter_mmin" in valueof:
        kwargs["min_val"] = valueof["parameter_mmin"]
    if "parameter_mmax" in valueof:
        kwargs["max_val"] = valueof["parameter_mmax"]
    if "parameter_unitstyle" in valueof:
        kwargs["unitstyle"] = valueof["parameter_unitstyle"]
    # Extended param metadata (A0): pre-wired GUARDED mappings so the reverse
    # snapshot->python->rebuild round-trip preserves these valueof fields the
    # moment a factory starts emitting them (A2 annotation/info, E1 units, E4
    # steps). No-op until the field is present in a real valueof, so adding the
    # field later does NOT ripple through the reverse-codegen self-consistency.
    for _vkey, _kwarg in _EXTENDED_PARAM_VALUEOF_KWARGS:
        if _vkey in valueof:
            kwargs[_kwarg] = valueof[_vkey]
    return kwargs


def _box_builder_statement(box: dict, support_files_by_name: dict[str, dict] | None = None) -> str:
    maxclass = box.get("maxclass")
    box_id = box.get("id")
    rect = copy.deepcopy(box.get("presentation_rect") or box.get("patching_rect") or [0, 0, 60, 20])
    support_files_by_name = support_files_by_name or {}

    if maxclass == "panel":
        kwargs = _base_box_kwargs(
            box,
            [
                "id",
                "maxclass",
                "presentation",
                "presentation_rect",
                "bgcolor",
                "numinlets",
                "numoutlets",
                "outlettype",
            ],
        )
        return _call_statement("add_panel", [box_id, rect], {"bgcolor": box.get("bgcolor"), **kwargs})

    if maxclass == "live.comment":
        kwargs = _comment_kwargs({
            key: value
            for key, value in box.items()
            if key not in ("numinlets", "numoutlets", "outlettype")
        })
        return _call_statement("add_comment", [box_id, rect, box.get("text", "")], kwargs)

    if maxclass == "live.dial":
        kwargs = _parameter_box_common_kwargs(box)
        valueof = _saved_valueof(box)
        if "parameter_exponent" in valueof:
            kwargs["parameter_exponent"] = valueof["parameter_exponent"]
        return _call_statement("add_dial", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "live.tab":
        kwargs = _parameter_box_common_kwargs(box, include_shortname=False)
        valueof = _saved_valueof(box)
        options = valueof.get("parameter_enum", [])
        return _call_statement("add_tab", [box_id, box.get("varname"), rect], {"options": options, **kwargs})

    if maxclass == "live.toggle":
        kwargs = _parameter_box_common_kwargs(box)
        valueof = _saved_valueof(box)
        labels = valueof.get("parameter_enum", ["off", "on"])
        if labels and labels != ["off", "on"]:
            kwargs["labels"] = tuple(labels)
        return _call_statement("add_toggle", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "live.menu":
        kwargs = _parameter_box_common_kwargs(box)
        valueof = _saved_valueof(box)
        options = valueof.get("parameter_enum", [])
        return _call_statement("add_menu", [box_id, box.get("varname"), rect], {"options": options, **kwargs})

    if maxclass == "live.numbox":
        kwargs = _parameter_box_common_kwargs(box)
        return _call_statement("add_number_box", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "live.slider":
        kwargs = _parameter_box_common_kwargs(box)
        return _call_statement("add_slider", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "live.button":
        kwargs = _base_box_kwargs(
            box,
            [
                "id",
                "maxclass",
                "varname",
                "presentation",
                "presentation_rect",
                "saved_attribute_attributes",
                "parameter_enable",
                "numinlets",
                "numoutlets",
                "outlettype",
            ],
        )
        valueof = _saved_valueof(box)
        shortname = valueof.get("parameter_shortname")
        if shortname and shortname != box.get("varname"):
            kwargs["shortname"] = shortname
        return _call_statement("add_button", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "live.text":
        kwargs = _base_box_kwargs(
            box,
            [
                "id",
                "maxclass",
                "varname",
                "presentation",
                "presentation_rect",
                "saved_attribute_attributes",
                "parameter_enable",
                "numinlets",
                "numoutlets",
                "outlettype",
                "text",
                "texton",
            ],
        )
        valueof = _saved_valueof(box)
        shortname = valueof.get("parameter_shortname")
        if shortname and shortname != box.get("varname"):
            kwargs["shortname"] = shortname
        if box.get("texton") is not None:
            kwargs["text_on"] = box.get("texton")
        if box.get("text") is not None:
            kwargs["text_off"] = box.get("text")
        return _call_statement("add_live_text", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "live.gain~":
        kwargs = _parameter_box_common_kwargs(box)
        return _call_statement("add_live_gain", [box_id, box.get("varname"), rect], kwargs)

    if maxclass == "fpic":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "pic", "autofit", "numinlets", "numoutlets", "outlettype"],
        )
        if "autofit" in box:
            kwargs["autofit"] = box["autofit"]
        if "pic" in box:
            kwargs["pic"] = box["pic"]
        return _call_statement("add_fpic", [box_id, rect], kwargs)

    if maxclass == "multislider":
        kwargs = _base_box_kwargs(
            box,
            [
                "id",
                "maxclass",
                "presentation",
                "presentation_rect",
                "size",
                "setminmax",
                "orientation",
                "setstyle",
                "slidercolor",
                "candicane2",
                "numinlets",
                "numoutlets",
                "outlettype",
            ],
        )
        if "size" in box:
            kwargs["size"] = box["size"]
        if "setminmax" in box:
            kwargs["setminmax"] = copy.deepcopy(box["setminmax"])
        if "orientation" in box:
            kwargs["orientation"] = box["orientation"]
        if "setstyle" in box:
            kwargs["setstyle"] = box["setstyle"]
        if "slidercolor" in box:
            kwargs["slidercolor"] = copy.deepcopy(box["slidercolor"])
        if "candicane2" in box:
            kwargs["candicane2"] = copy.deepcopy(box["candicane2"])
        return _call_statement("add_multislider", [box_id, rect], kwargs)

    if maxclass == "jsui":
        filename = box.get("filename")
        support = support_files_by_name.get(filename)
        if support is not None:
            kwargs = _base_box_kwargs(
                box,
                [
                    "id",
                    "maxclass",
                    "presentation",
                    "presentation_rect",
                    "filename",
                    "numinlets",
                    "numoutlets",
                ],
            )
            numoutlets = box.get("numoutlets", 0)
            if box.get("outlettype"):
                kwargs["outlettype"] = copy.deepcopy(box.get("outlettype"))
            return _call_statement(
                "add_jsui",
                [box_id, rect],
                {
                    "js_code": support.get("content", ""),
                    "js_filename": filename,
                    "numinlets": box.get("numinlets", 1),
                    "numoutlets": numoutlets,
                    **kwargs,
                },
            )

    if maxclass == "v8ui":
        filename = box.get("filename")
        support = support_files_by_name.get(filename)
        if support is not None:
            kwargs = _base_box_kwargs(
                box,
                [
                    "id",
                    "maxclass",
                    "presentation",
                    "presentation_rect",
                    "filename",
                    "textfile",
                    "parameter_enable",
                    "numinlets",
                    "numoutlets",
                ],
            )
            numoutlets = box.get("numoutlets", 0)
            if box.get("outlettype"):
                kwargs["outlettype"] = copy.deepcopy(box.get("outlettype"))
            return _call_statement(
                "add_v8ui",
                [box_id, rect],
                {
                    "js_code": support.get("content", ""),
                    "js_filename": filename,
                    "numinlets": box.get("numinlets", 1),
                    "numoutlets": numoutlets,
                    # reconstructing an arbitrary real device: its extracted v8ui
                    # JS need not satisfy the authoring mgraphics contract.
                    "validate_contract": False,
                    **kwargs,
                },
            )

    if maxclass == "live.scope~":
        kwargs = _base_box_kwargs(box, ["id", "maxclass", "presentation", "presentation_rect", "range"])
        if "range" in box:
            kwargs["range_vals"] = box["range"]
        return _call_statement("add_scope", [box_id, rect], kwargs)

    if maxclass == "live.meter~":
        kwargs = _base_box_kwargs(box, ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"])
        return _call_statement("add_meter", [box_id, rect], kwargs)

    if maxclass == "live.adsrui":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_adsrui", [box_id, rect], kwargs)

    if maxclass == "live.drop":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_live_drop", [box_id, rect], kwargs)

    if maxclass == "bpatcher":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "name", "numinlets", "numoutlets"],
        )
        kwargs["numinlets"] = box.get("numinlets", 0)
        kwargs["numoutlets"] = box.get("numoutlets", 0)
        return _call_statement("add_bpatcher", [box_id, rect, box.get("name")], kwargs)

    if maxclass == "textbutton":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "text", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_textbutton", [box_id, rect], {"text": box.get("text", "Button"), **kwargs})

    if maxclass == "umenu":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "items", "numinlets", "numoutlets", "outlettype"],
        )
        if "items" in box:
            kwargs["items"] = copy.deepcopy(box["items"])
        return _call_statement("add_umenu", [box_id, rect], kwargs)

    if maxclass == "radiogroup":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "itemcount", "value", "numinlets", "numoutlets", "outlettype"],
        )
        if "itemcount" in box:
            kwargs["itemcount"] = box["itemcount"]
        if "value" in box:
            kwargs["value"] = box["value"]
        return _call_statement("add_radiogroup", [box_id, rect], kwargs)

    if maxclass == "swatch":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_swatch", [box_id, rect], kwargs)

    if maxclass == "textedit":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_textedit", [box_id, rect], kwargs)

    if maxclass == "live.step":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "nstep", "nseq", "loop_start", "loop_end", "mode", "numinlets", "numoutlets", "outlettype"],
        )
        if "nstep" in box:
            kwargs["nstep"] = box["nstep"]
        if "nseq" in box:
            kwargs["nseq"] = box["nseq"]
        if "loop_start" in box:
            kwargs["loop_start"] = box["loop_start"]
        if "loop_end" in box:
            kwargs["loop_end"] = box["loop_end"]
        if "mode" in box:
            kwargs["mode"] = box["mode"]
        return _call_statement("add_live_step", [box_id, rect], kwargs)

    if maxclass == "live.grid":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "columns", "rows", "direction", "numinlets", "numoutlets", "outlettype"],
        )
        if "columns" in box:
            kwargs["columns"] = box["columns"]
        if "rows" in box:
            kwargs["rows"] = box["rows"]
        if "direction" in box:
            kwargs["direction"] = box["direction"]
        return _call_statement("add_live_grid", [box_id, rect], kwargs)

    if maxclass == "live.line":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_live_line", [box_id, rect], kwargs)

    if maxclass == "live.arrows":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_live_arrows", [box_id, rect], kwargs)

    if maxclass == "rslider":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "min", "max", "numinlets", "numoutlets", "outlettype"],
        )
        if "min" in box:
            kwargs["min_val"] = box["min"]
        if "max" in box:
            kwargs["max_val"] = box["max"]
        return _call_statement("add_rslider", [box_id, rect], kwargs)

    if maxclass == "kslider":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "range", "offset", "numinlets", "numoutlets", "outlettype"],
        )
        if "range" in box:
            kwargs["range"] = box["range"]
        if "offset" in box:
            kwargs["offset"] = box["offset"]
        return _call_statement("add_kslider", [box_id, rect], kwargs)

    if maxclass == "nodes":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numnodes", "xmin", "xmax", "ymin", "ymax", "numinlets", "numoutlets", "outlettype"],
        )
        for name in ("numnodes", "xmin", "xmax", "ymin", "ymax"):
            if name in box:
                kwargs[name] = box[name]
        return _call_statement("add_nodes", [box_id, rect], kwargs)

    if maxclass == "matrixctrl":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "rows", "columns", "numinlets", "numoutlets", "outlettype"],
        )
        if "rows" in box:
            kwargs["rows"] = box["rows"]
        if "columns" in box:
            kwargs["columns"] = box["columns"]
        return _call_statement("add_matrixctrl", [box_id, rect], kwargs)

    if maxclass == "ubutton":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "numinlets", "numoutlets", "outlettype"],
        )
        return _call_statement("add_ubutton", [box_id, rect], kwargs)

    if maxclass == "nslider":
        kwargs = _base_box_kwargs(
            box,
            ["id", "maxclass", "presentation", "presentation_rect", "staffs", "numinlets", "numoutlets", "outlettype"],
        )
        if "staffs" in box:
            kwargs["staffs"] = box["staffs"]
        return _call_statement("add_nslider", [box_id, rect], kwargs)

    if maxclass == "newobj":
        kwargs = _base_box_kwargs(box, ["id", "maxclass", "text", "numinlets", "numoutlets"])
        return _call_statement(
            "add_newobj",
            [box_id, box.get("text", "")],
            {
                "numinlets": box.get("numinlets", 0),
                "numoutlets": box.get("numoutlets", 0),
                **kwargs,
            },
        )

    return "    device.add_box(%s)" % _python_literal({"box": box})


def _assign_parameter_bank_statements(snapshot: dict) -> list[str]:
    statements = []
    parameterbanks = snapshot.get("parameterbanks", {})
    for bank_key, bank in sorted(parameterbanks.items(), key=lambda item: int(item[0])):
        bank_index = int(bank.get("index", bank_key))
        bank_name = bank.get("name")
        normalized_params = []
        for position, param in enumerate(bank.get("parameters", [])):
            if isinstance(param, dict):
                name = param.get("name")
                param_index = param.get("index", position)
            else:
                name = str(param)
                param_index = position
            if not name or name == "-":
                continue
            normalized_params.append({
                "name": name,
                "index": param_index,
            })
        for param in sorted(normalized_params, key=lambda item: item.get("index", 0)):
            kwargs = {
                "bank": bank_index,
                "position": param.get("index", 0),
            }
            if bank_name:
                kwargs["bank_name"] = bank_name
            statements.append(
                _call_statement(
                    "assign_parameter_bank",
                    [param.get("name")],
                    kwargs,
                )
            )
    return statements


def _device_ctor_for_snapshot(snapshot: dict) -> str:
    device_type = snapshot["device"]["device_type"]
    analysis = snapshot.get("analysis", {})
    if device_type == "audio_effect" and not analysis.get("uses_default_audio_io", False):
        return "Device(%s, %s, %s, device_type='audio_effect')" % (
            _python_literal(snapshot["device"]["name"]),
            _python_literal(snapshot["device"]["width"]),
            _python_literal(snapshot["device"]["height"]),
        )
    class_name = DEVICE_TYPE_TO_CLASS.get(device_type, "Device")
    if class_name == "Device":
        return "Device(%s, %s, %s, device_type=%s)" % (
            _python_literal(snapshot["device"]["name"]),
            _python_literal(snapshot["device"]["width"]),
            _python_literal(snapshot["device"]["height"]),
            _python_literal(device_type),
        )
    return "%s(%s, %s, %s)" % (
        class_name,
        _python_literal(snapshot["device"]["name"]),
        _python_literal(snapshot["device"]["width"]),
        _python_literal(snapshot["device"]["height"]),
    )


def _wrapped_boxes_for_candidate(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str],
) -> list[dict]:
    candidate_box_ids = set(candidate.get("box_ids", []))
    boxes = []
    for wrapped in snapshot.get("boxes", []):
        box = unwrap_box(wrapped)
        box_id = box.get("id")
        if box_id in skip_default_audio_ids or box_id not in candidate_box_ids:
            continue
        boxes.append(copy.deepcopy(wrapped))
    return boxes


def _wrapped_lines_for_candidate(snapshot: dict, candidate: dict) -> list[dict]:
    candidate_line_keys = set(candidate.get("line_keys", []))
    lines = []
    for wrapped in snapshot.get("lines", []):
        line_key = _line_key_from_wrapped(wrapped)
        if line_key not in candidate_line_keys:
            continue
        lines.append(copy.deepcopy(wrapped))
    return lines


def _controller_shell_helper_call(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str] | None = None,
) -> dict:
    skip_default_audio_ids = skip_default_audio_ids or set()
    return {
        "name": candidate.get("candidate_name"),
        "positional": [],
        "kwargs": {
            "boxes": _wrapped_boxes_for_candidate(
                snapshot,
                candidate,
                skip_default_audio_ids=skip_default_audio_ids,
            ),
            "lines": _wrapped_lines_for_candidate(snapshot, candidate),
        },
        "consume_box_ids": copy.deepcopy(candidate.get("box_ids", [])),
        "line_keys": copy.deepcopy(candidate.get("line_keys", [])),
    }

__all__ = [
    "_patcher_name",
    "_patcher_dimensions",
    "_device_type_from_patcher",
    "_dedupe_dependencies",
    "_snapshot_from_parts",
    "_device_type_from_bridge",
    "_infer_dimensions_from_bridge_boxes",
    "_coerce_flag",
    "_normalize_bridge_box",
    "_normalize_bridge_patchline",
    "_bridge_dependencies_from_support_files",
    "_box_annotation_name",
    "_parameter_spec_from_box",
    "_normalize_number",
    "_line_key",
    "_line_key_from_wrapped",
    "_snapshot_graph",
    "_box_operator",
    "_box_text_args",
    "_buffer_target_name",
    "_embedded_patcher_kind_and_target",
    "_snapshot_source_path",
    "_factory_pack_context",
    "_connected_box_ids",
    "_rect_matches",
    "_presentation_rect",
    "_rects_touch",
    "_text_float",
    "_text_int",
    "_parse_live_api_message_text",
    "_classify_live_api_component_archetypes",
    "_matches_state_bundle_operator",
    "_operator_components",
    "_relevant_box_components",
    "_adjacent_message_texts",
    "_transport_lfo_division_from_text",
    "_candidate_prefixes",
    "_pattern_match",
    "_recipe_match",
    "_motif_match",
    "_semantic_helper_match",
    "_infer_helper_prefix",
    "_boxes_match_in_snapshot_order",
    "_lines_match_in_snapshot_order",
    "_live_api_helper_box_attrs",
    "_live_api_include_default_style",
    "_adjacent_message_boxes_for_component",
    "_adjacent_property_message_box",
    "_message_segments",
    "_adjacent_probe_message_box",
    "_line_source_outlet_to_destination",
    "_line_attrs_from_snapshot",
    "_line_index_in_snapshot",
    "_component_internal_line_keys",
    "_ordered_box_ids",
    "_live_api_helper_call_from_snapshot",
    "_canonical_live_api_helper_match",
    "_box_parameter_matches",
    "_line_keys_present",
    "_canonical_recipe_subset",
    "_recipeizable_subset_matches",
    "_sample_buffer_component_label",
    "_gen_processing_component_label",
    "_helper_opportunity",
    "_live_api_normalization_level",
    "_live_api_semantic_helper_call",
    "_line_keys_for_box_ids",
    "_root_object_name_counts",
    "_motif_semantic_candidate",
    "_candidate_helper_boxes",
    "_candidate_named_bus_texts",
    "_candidate_bpatcher_names",
    "_indexed_name_signatures",
    "_first_party_abstraction_family",
    "_embedded_snapshot_from_patcher_dict",
    "_ui_role",
    "_support_file_kind",
    "_named_bus_networks",
    "_snapshot_object_texts",
    "_snapshot_contains_all_texts",
    "_finalize_snapshot",
    "_snapshot_uses_default_audio_io",
    "_is_bridge_runtime_box",
    "_read_amxd_chunks",
    "_decode_patcher_chunk",
    "read_amxd",
    "snapshot_from_device",
    "snapshot_from_amxd",
    "snapshot_from_bridge_payload",
    "snapshot_to_json",
    "write_snapshot",
    "load_snapshot",
    "_python_literal",
    "_call_statement",
    "_dsp_add_statement",
    "_function_call_statement",
    "_recipe_call_statement",
    "_support_files_by_name",
    "_semantic_jsui_filenames",
    "_support_file_statements",
    "_saved_valueof",
    "_base_box_kwargs",
    "_comment_kwargs",
    "_parameter_box_common_kwargs",
    "_box_builder_statement",
    "_assign_parameter_bank_statements",
    "_device_ctor_for_snapshot",
    "_wrapped_boxes_for_candidate",
    "_wrapped_lines_for_candidate",
    "_controller_shell_helper_call",
]

