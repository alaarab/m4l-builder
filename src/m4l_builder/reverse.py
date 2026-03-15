"""Reverse-engineering helpers for snapshots and starter Python generation."""

from __future__ import annotations

import copy
import json
import os
import pprint
import re
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constants import AMXD_TYPE, AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .device import Device
from .live_api import (
    device_active_state,
    live_parameter_probe,
    live_object_path,
    live_observer,
    live_state_observer,
    live_set_control,
    live_thisdevice,
)
from .patcher import build_patcher
from .recipes import (
    dry_wet_stage,
    gain_controlled_stage,
    midi_note_gate,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)


TYPE_CODE_TO_DEVICE_TYPE = {
    AUDIO_EFFECT: "audio_effect",
    INSTRUMENT: "instrument",
    MIDI_EFFECT: "midi_effect",
}
DEVICE_TYPE_TO_CODE_CONSTANT = {
    "audio_effect": "AUDIO_EFFECT",
    "instrument": "INSTRUMENT",
    "midi_effect": "MIDI_EFFECT",
}
DEVICE_TYPE_TO_CLASS = {
    "audio_effect": "AudioEffect",
    "instrument": "Instrument",
    "midi_effect": "MidiEffect",
}
AMXD_INT_TO_DEVICE_TYPE = {value: key for key, value in AMXD_TYPE.items()}
UI_MAXCLASSES = {
    "panel",
    "live.comment",
    "live.dial",
    "live.drop",
    "live.grid",
    "live.line",
    "live.menu",
    "live.meter~",
    "live.numbox",
    "live.scope~",
    "live.step",
    "live.slider",
    "live.tab",
    "live.text",
    "live.toggle",
    "live.adsrui",
    "live.arrows",
    "multislider",
    "fpic",
    "jsui",
    "v8ui",
    "bpatcher",
    "swatch",
    "textedit",
    "textbutton",
    "umenu",
    "radiogroup",
    "rslider",
    "kslider",
    "nodes",
    "matrixctrl",
    "ubutton",
    "nslider",
}
PARAMETER_MAXCLASSES = {
    "live.dial",
    "live.menu",
    "live.numbox",
    "live.slider",
    "live.tab",
    "live.text",
    "live.toggle",
}
BRIDGE_TEXT_MARKERS = (
    "livemcp_bridge_runtime.js",
    "livemcp_bridge_server.js",
)
BUS_OPERATOR_SPECS = {
    "s": {"signal": False, "direction": "send"},
    "send": {"signal": False, "direction": "send"},
    "r": {"signal": False, "direction": "receive"},
    "receive": {"signal": False, "direction": "receive"},
    "s~": {"signal": True, "direction": "send"},
    "send~": {"signal": True, "direction": "send"},
    "r~": {"signal": True, "direction": "receive"},
    "receive~": {"signal": True, "direction": "receive"},
}
LIVE_API_CORE_OPERATORS = {
    "live.thisdevice",
    "live.path",
    "live.object",
    "live.observer",
    "live.remote~",
    "live.banks",
}
LIVE_API_HELPER_OPERATORS = {
    "route",
    "prepend",
    "deferlow",
    "sel",
    "gate",
    "pack",
    "unpack",
    "trigger",
    "t",
}
CONTROLLER_DISPATCH_OPERATORS = {
    "route",
    "sel",
    "gate",
    "switch",
    "gswitch",
    "split",
    "trigger",
    "t",
}
SCHEDULER_OPERATORS = {
    "loadbang",
    "loadmess",
    "deferlow",
    "delay",
    "del",
    "pipe",
    "onebang",
    "trigger",
    "t",
}
STATE_BUNDLE_OPERATORS = {
    "pack",
    "pak",
    "unpack",
    "buddy",
    "join",
}
EMBEDDED_PATCHER_OPERATORS = {
    "p",
    "poly~",
    "gen~",
    "pfft~",
}
SAMPLE_BUFFER_CORE_OPERATORS = {
    "buffer~",
    "info~",
    "peek~",
    "poke~",
    "play~",
    "record~",
    "groove~",
    "waveform~",
    "polybuffer~",
}
SAMPLE_BUFFER_HELPER_OPERATORS = {
    "b",
    "date",
    "defer",
    "deferlow",
    "delay",
    "del",
    "gate",
    "i",
    "info~",
    "join",
    "metro",
    "pack",
    "prepend",
    "regexp",
    "relativepath",
    "route",
    "sel",
    "sprintf",
    "strippath",
    "t",
    "trigger",
    "unpack",
    "uzi",
    "zl",
    "zl.compare",
    "zl.join",
    "zl.reg",
    "zl.slice",
}
GEN_PROCESSING_CORE_OPERATORS = {
    "gen~",
    "mc.gen~",
}
GEN_PROCESSING_HELPER_OPERATORS = {
    "buffer~",
    "click~",
    "defer",
    "deferlow",
    "delay",
    "del",
    "gate",
    "i",
    "in",
    "info~",
    "metro",
    "out",
    "p",
    "pack",
    "peek~",
    "prepend",
    "route",
    "sel",
    "t",
    "trigger",
    "unpack",
    "uzi",
}
DEFAULT_AUDIO_IO_BOXES = {
    "obj-plugin": {
        "text": "plugin~",
        "patching_rect": [30, 30, 60, 20],
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["signal", "signal"],
    },
    "obj-plugout": {
        "text": "plugout~",
        "patching_rect": [30, 200, 60, 20],
        "numinlets": 2,
        "numoutlets": 0,
    },
}


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
    device_name: Optional[str] = None,
    support_files: Optional[List[Dict[str, Any]]] = None,
    missing_support_files: Optional[List[Dict[str, Any]]] = None,
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


def _device_type_from_bridge(selected_device: Optional[dict]) -> str:
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
    for box in boxes:
        rect = box["box"].get("presentation_rect") or box["box"].get("patching_rect")
        if rect and len(rect) == 4:
            rects.append(rect)

    if not rects:
        return 400.0, 170.0

    width = max(rect[0] + rect[2] for rect in rects)
    height = max(rect[1] + rect[3] for rect in rects)
    return max(width, 120.0), max(height, 60.0)


def _coerce_flag(value: Any) -> int:
    return 1 if bool(value) else 0


def _normalize_bridge_box(summary: dict, attrs_payload: Optional[dict] = None) -> dict:
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


def _parameter_spec_from_box(box: dict) -> Optional[dict]:
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


def extract_parameter_specs(snapshot: dict) -> list[dict]:
    """Extract parameter/control specs from a normalized snapshot."""
    specs = []
    for wrapped in snapshot.get("boxes", []):
        spec = _parameter_spec_from_box(wrapped.get("box", {}))
        if spec is not None:
            specs.append(spec)
    return specs


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
    for index, wrapped in enumerate(snapshot.get("boxes", [])):
        box = wrapped.get("box", {})
        box_id = box.get("id")
        if box_id:
            boxes_by_id[box_id] = box
            box_indices[box_id] = index

    line_keys = {_line_key_from_wrapped(line) for line in snapshot.get("lines", [])}
    return boxes_by_id, box_indices, line_keys


def _box_operator(box: dict) -> Optional[str]:
    if box.get("maxclass") != "newobj":
        return None
    text = str(box.get("text", "")).strip()
    if not text:
        return None
    return text.split()[0]


def _box_text_args(box: dict) -> Optional[str]:
    text = str(box.get("text", "")).strip()
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    args = parts[1].strip()
    return args or None


def _buffer_target_name(box: dict) -> Optional[str]:
    args = _box_text_args(box)
    if not args:
        return None
    first = args.split()[0].strip()
    if not first or first.startswith("@"):
        return None
    return first


def _embedded_patcher_kind_and_target(box: dict) -> tuple[Optional[str], Optional[str]]:
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


def _snapshot_source_path(snapshot: dict) -> Optional[str]:
    source = snapshot.get("source", {})
    path = source.get("path")
    if not path:
        return None
    return os.path.abspath(str(path))


def _factory_pack_context(snapshot: dict) -> dict[str, Optional[str]]:
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
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
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


def _presentation_rect(box: dict) -> Optional[list[float]]:
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


def _text_float(text: str, prefix: str) -> Optional[float]:
    if not text.startswith(prefix):
        return None
    try:
        return float(text[len(prefix):].strip())
    except ValueError:
        return None


def _text_int(text: str, prefix: str) -> Optional[int]:
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
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
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


def _transport_lfo_division_from_text(text: str) -> Optional[str]:
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
    params: Optional[dict] = None,
    helper: Optional[dict] = None,
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
    params: Optional[dict] = None,
    recipe: Optional[dict] = None,
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
    params: Optional[dict] = None,
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
    params: Optional[dict] = None,
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
    candidate_box_ids = [wrapped["box"]["id"] for wrapped in candidate_boxes]
    actual_order = sorted(candidate_box_ids, key=lambda box_id: box_indices.get(box_id, 10 ** 9))
    if actual_order != candidate_box_ids:
        return False
    for wrapped in candidate_boxes:
        box = wrapped["box"]
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
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
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
    prop: Optional[str] = None,
) -> Optional[dict]:
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
) -> Optional[dict]:
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
) -> Optional[int]:
    matches = []
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
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
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
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
) -> Optional[int]:
    for index, wrapped in enumerate(snapshot.get("lines", [])):
        patchline = wrapped.get("patchline", {})
        source = patchline.get("source", [None, 0])
        destination = patchline.get("destination", [None, 0])
        if source == [source_id, source_outlet] and destination == [destination_id, destination_inlet]:
            return index
    return None


def _component_internal_line_keys(snapshot: dict, component_box_ids: list[str]) -> list[tuple]:
    component_id_set = set(component_box_ids)
    line_keys = []
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
        source_id = patchline.get("source", [None, 0])[0]
        dest_id = patchline.get("destination", [None, 0])[0]
        if source_id in component_id_set and dest_id in component_id_set:
            line_keys.append(_line_key_from_wrapped(wrapped))
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
    params: Optional[dict] = None,
) -> Optional[dict]:
    candidate_boxes, candidate_lines = helper_fn(*helper_positional, **helper_kwargs)
    candidate_box_ids = [wrapped["box"]["id"] for wrapped in candidate_boxes]
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
    annotation_name: Optional[str] = None,
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
    if annotation_name is not None and box.get("annotation_name") != annotation_name:
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
    recipe_boxes = {
        wrapped["box"]["id"]: wrapped["box"]
        for wrapped in recipe_device.boxes
    }
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


def _match_param_smooth(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    pack_id = f"{prefix}_pack"
    line_id = f"{prefix}_line"
    pack = boxes_by_id.get(pack_id)
    line = boxes_by_id.get(line_id)
    if not pack or not line:
        return None

    pack_text = str(pack.get("text", ""))
    smooth_ms = _text_float(pack_text, "pack f ")
    if smooth_ms is None or line.get("text") != "line~":
        return None

    required_line = _line_key(pack_id, 0, line_id, 0)
    if required_line not in line_keys:
        return None

    helper = None
    if _rect_matches(pack, [30, 120, 80, 20]) and _rect_matches(line, [30, 150, 40, 20]):
        helper_kwargs = {}
        if float(smooth_ms) != 20.0:
            helper_kwargs["smooth_ms"] = _normalize_number(float(smooth_ms))
        helper = {
            "name": "param_smooth",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="param_smooth",
        prefix=prefix,
        box_ids=[pack_id, line_id],
        line_keys=[required_line],
        params={"smooth_ms": _normalize_number(float(smooth_ms))},
        helper=helper,
    )


def _match_delay_line(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    tapin_id = f"{prefix}_tapin"
    tapout_id = f"{prefix}_tapout"
    tapin = boxes_by_id.get(tapin_id)
    tapout = boxes_by_id.get(tapout_id)
    if not tapin or not tapout:
        return None

    max_delay_tapin = _text_int(str(tapin.get("text", "")), "tapin~ ")
    max_delay_tapout = _text_int(str(tapout.get("text", "")), "tapout~ ")
    if max_delay_tapin is None or max_delay_tapout is None or max_delay_tapin != max_delay_tapout:
        return None

    required_line = _line_key(tapin_id, 0, tapout_id, 0)
    if required_line not in line_keys:
        return None

    helper = None
    if _rect_matches(tapin, [30, 120, 100, 20]) and _rect_matches(tapout, [30, 150, 100, 20]):
        helper_kwargs = {}
        if max_delay_tapin != 5000:
            helper_kwargs["max_delay_ms"] = max_delay_tapin
        helper = {
            "name": "delay_line",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="delay_line",
        prefix=prefix,
        box_ids=[tapin_id, tapout_id],
        line_keys=[required_line],
        params={"max_delay_ms": max_delay_tapin},
        helper=helper,
    )


def _match_gain_stage(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None
    if left.get("text") != "*~ 1." or right.get("text") != "*~ 1.":
        return None

    helper_kwargs = {}
    if not _rect_matches(left, [30, 120, 40, 20]):
        helper_kwargs["patching_rect_l"] = copy.deepcopy(left.get("patching_rect"))
    if not _rect_matches(right, [150, 120, 40, 20]):
        helper_kwargs["patching_rect_r"] = copy.deepcopy(right.get("patching_rect"))

    return _pattern_match(
        kind="gain_stage",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        helper={
            "name": "gain_stage",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        },
    )


def _match_dc_block(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None

    dc_text = "biquad~ 1. -1. 0. -0.9997 0."
    if left.get("text") != dc_text or right.get("text") != dc_text:
        return None

    helper = None
    if _rect_matches(left, [30, 120, 180, 20]) and _rect_matches(right, [220, 120, 180, 20]):
        helper = {
            "name": "dc_block",
            "positional": [prefix],
            "kwargs": {},
        }

    return _pattern_match(
        kind="dc_block",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        helper=helper,
    )


def _match_saturation(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None

    mode_by_text = {
        "tanh~": "tanh",
        "overdrive~": "overdrive",
        "clip~ -1. 1.": "clip",
        "degrade~": "degrade",
    }
    mode = mode_by_text.get(str(left.get("text", "")))
    if mode is None or right.get("text") != left.get("text"):
        return None

    helper = None
    if _rect_matches(left, [30, 120, 80, 20]) and _rect_matches(right, [150, 120, 80, 20]):
        helper_kwargs = {}
        if mode != "tanh":
            helper_kwargs["mode"] = mode
        helper = {
            "name": "saturation",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="saturation",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        params={"mode": mode},
        helper=helper,
    )


def _match_selector(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    box = boxes_by_id.get(prefix)
    if not box:
        return None

    match = re.match(r"^selector~ (\d+) (\d+)$", str(box.get("text", "")))
    if not match:
        return None

    num_inputs = int(match.group(1))
    initial = int(match.group(2))
    helper = None
    if _rect_matches(box, [30, 120, 100, 20]):
        helper_kwargs = {}
        if num_inputs != 2:
            helper_kwargs["num_inputs"] = num_inputs
        if initial != 1:
            helper_kwargs["initial"] = initial
        helper = {
            "name": "selector",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="selector",
        prefix=prefix,
        box_ids=[prefix],
        line_keys=[],
        params={"num_inputs": num_inputs, "initial": initial},
        helper=helper,
    )


def _match_onepole_filter(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None

    freq_l = _text_float(str(left.get("text", "")), "onepole~ ")
    freq_r = _text_float(str(right.get("text", "")), "onepole~ ")
    if freq_l is None or freq_r is None or float(freq_l) != float(freq_r):
        return None

    helper = None
    if _rect_matches(left, [30, 120, 80, 20]) and _rect_matches(right, [150, 120, 80, 20]):
        helper_kwargs = {}
        if float(freq_l) != 1000.0:
            helper_kwargs["freq"] = _normalize_number(float(freq_l))
        helper = {
            "name": "onepole_filter",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="onepole_filter",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        params={"freq": _normalize_number(float(freq_l))},
        helper=helper,
    )


def _match_svf_filter(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    out_left_id = f"{prefix}_out_l"
    out_right_id = f"{prefix}_out_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    out_left = boxes_by_id.get(out_left_id)
    out_right = boxes_by_id.get(out_right_id)
    if not all((left, right, out_left, out_right)):
        return None

    if left.get("text") != "svf~" or right.get("text") != "svf~":
        return None
    if out_left.get("text") != "*~ 1." or out_right.get("text") != "*~ 1.":
        return None

    for outlet, kind in ((0, "lowpass_filter"), (1, "highpass_filter"), (2, "bandpass_filter")):
        required_lines = [
            _line_key(left_id, outlet, out_left_id, 0),
            _line_key(right_id, outlet, out_right_id, 0),
        ]
        if not all(line in line_keys for line in required_lines):
            continue

        helper = None
        if (
            _rect_matches(left, [30, 120, 40, 20])
            and _rect_matches(right, [150, 120, 40, 20])
            and _rect_matches(out_left, [30, 150, 40, 20])
            and _rect_matches(out_right, [150, 150, 40, 20])
        ):
            helper = {
                "name": kind,
                "positional": [prefix],
                "kwargs": {},
            }

        return _pattern_match(
            kind=kind,
            prefix=prefix,
            box_ids=[left_id, right_id, out_left_id, out_right_id],
            line_keys=required_lines,
            helper=helper,
        )

    return None


def _match_lfo(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    osc_id = f"{prefix}_osc"
    depth_id = f"{prefix}_depth"
    osc = boxes_by_id.get(osc_id)
    depth = boxes_by_id.get(depth_id)
    if not osc or not depth or depth.get("text") != "*~ 1.":
        return None

    osc_text = str(osc.get("text", ""))
    required_boxes = [osc_id, depth_id]
    required_lines = []
    waveform = None
    helperizable = False

    if osc_text == "phasor~":
        waveform = "saw"
        required_lines = [_line_key(osc_id, 0, depth_id, 0)]
        helperizable = (
            _rect_matches(osc, [30, 120, 60, 20])
            and _rect_matches(depth, [30, 210, 40, 20])
        )
    elif osc_text in {"cycle~", "rect~", "tri~"}:
        scale_id = f"{prefix}_scale"
        offset_id = f"{prefix}_offset"
        scale = boxes_by_id.get(scale_id)
        offset = boxes_by_id.get(offset_id)
        if not scale or not offset:
            return None
        if scale.get("text") != "*~ 0.5" or offset.get("text") != "+~ 0.5":
            return None
        waveform = {
            "cycle~": "sine",
            "rect~": "square",
            "tri~": "triangle",
        }[osc_text]
        required_boxes = [osc_id, scale_id, offset_id, depth_id]
        required_lines = [
            _line_key(osc_id, 0, scale_id, 0),
            _line_key(scale_id, 0, offset_id, 0),
            _line_key(offset_id, 0, depth_id, 0),
        ]
        helperizable = (
            _rect_matches(depth, [30, 210, 40, 20])
            and _rect_matches(scale, [30, 150, 50, 20])
            and _rect_matches(offset, [30, 180, 50, 20])
            and (
                (osc_text == "cycle~" and _rect_matches(osc, [30, 120, 50, 20]))
                or (osc_text == "rect~" and _rect_matches(osc, [30, 120, 50, 20]))
                or (osc_text == "tri~" and _rect_matches(osc, [30, 120, 50, 20]))
            )
        )
    else:
        return None

    if not all(line in line_keys for line in required_lines):
        return None

    helper = None
    if helperizable:
        helper_kwargs = {}
        if waveform != "sine":
            helper_kwargs["waveform"] = waveform
        helper = {
            "name": "lfo",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="lfo",
        prefix=prefix,
        box_ids=required_boxes,
        line_keys=required_lines,
        params={"waveform": waveform},
        helper=helper,
    )


def _match_transport_lfo(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    transport_id = f"{prefix}_transport"
    bpm_id = f"{prefix}_bpm"
    rate_id = f"{prefix}_rate"
    osc_id = f"{prefix}_osc"
    transport = boxes_by_id.get(transport_id)
    bpm = boxes_by_id.get(bpm_id)
    rate = boxes_by_id.get(rate_id)
    osc = boxes_by_id.get(osc_id)
    if not all((transport, bpm, rate, osc)):
        return None

    if transport.get("text") != "transport" or bpm.get("text") != "f":
        return None

    division = _transport_lfo_division_from_text(str(rate.get("text", "")))
    if division is None:
        return None

    shape_map = {
        "cycle~": "sine",
        "phasor~": "saw",
        "rect~": "square",
    }
    shape = shape_map.get(osc.get("text"))
    if shape is None:
        return None

    required_lines = [
        _line_key(transport_id, 0, bpm_id, 0),
        _line_key(bpm_id, 0, rate_id, 0),
        _line_key(rate_id, 0, osc_id, 0),
    ]
    if not _line_keys_present(line_keys, required_lines):
        return None

    helper = None
    if (
        _rect_matches(transport, [30, 60, 70, 20])
        and _rect_matches(bpm, [30, 90, 30, 20])
        and _rect_matches(rate, [30, 120, 160, 20])
        and _rect_matches(osc, [30, 160, 60, 20])
    ):
        helper_kwargs = {}
        if division != "1/4":
            helper_kwargs["division"] = division
        if shape != "sine":
            helper_kwargs["shape"] = shape
        helper = {
            "name": "transport_lfo",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="transport_lfo",
        prefix=prefix,
        box_ids=[transport_id, bpm_id, rate_id, osc_id],
        line_keys=required_lines,
        params={
            "division": division,
            "shape": shape,
        },
        helper=helper,
    )


def _match_ms_encode_decode(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    specs = {
        f"{prefix}_enc_add": "+~",
        f"{prefix}_enc_sub": "-~",
        f"{prefix}_enc_mid": "*~ 0.5",
        f"{prefix}_enc_side": "*~ 0.5",
        f"{prefix}_dec_add": "+~",
        f"{prefix}_dec_sub": "-~",
    }
    boxes = {}
    for box_id, text in specs.items():
        box = boxes_by_id.get(box_id)
        if not box or box.get("text") != text:
            return None
        boxes[box_id] = box

    required_lines = [
        _line_key(f"{prefix}_enc_add", 0, f"{prefix}_enc_mid", 0),
        _line_key(f"{prefix}_enc_sub", 0, f"{prefix}_enc_side", 0),
    ]
    if not all(line in line_keys for line in required_lines):
        return None

    helper = None
    if (
        _rect_matches(boxes[f"{prefix}_enc_add"], [300, 60, 30, 20])
        and _rect_matches(boxes[f"{prefix}_enc_sub"], [340, 60, 30, 20])
        and _rect_matches(boxes[f"{prefix}_enc_mid"], [300, 90, 45, 20])
        and _rect_matches(boxes[f"{prefix}_enc_side"], [340, 90, 45, 20])
        and _rect_matches(boxes[f"{prefix}_dec_add"], [300, 160, 30, 20])
        and _rect_matches(boxes[f"{prefix}_dec_sub"], [340, 160, 30, 20])
    ):
        helper = {
            "name": "ms_encode_decode",
            "positional": [prefix],
            "kwargs": {},
        }

    return _pattern_match(
        kind="ms_encode_decode",
        prefix=prefix,
        box_ids=list(specs),
        line_keys=required_lines,
        helper=helper,
    )


def _match_feedback_delay(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> Optional[dict]:
    sum_id = f"{prefix}_sum"
    tapin_id = f"{prefix}_tapin"
    tapout_id = f"{prefix}_tapout"
    sat_id = f"{prefix}_sat"
    lp_id = f"{prefix}_lp"
    fb_id = f"{prefix}_fb"

    boxes = {
        sum_id: boxes_by_id.get(sum_id),
        tapin_id: boxes_by_id.get(tapin_id),
        tapout_id: boxes_by_id.get(tapout_id),
        sat_id: boxes_by_id.get(sat_id),
        lp_id: boxes_by_id.get(lp_id),
        fb_id: boxes_by_id.get(fb_id),
    }
    if not all(boxes.values()):
        return None

    max_delay_tapin = _text_int(str(boxes[tapin_id].get("text", "")), "tapin~ ")
    max_delay_tapout = _text_int(str(boxes[tapout_id].get("text", "")), "tapout~ ")
    lp_freq = _text_float(str(boxes[lp_id].get("text", "")), "onepole~ ")
    fb_amount = _text_float(str(boxes[fb_id].get("text", "")), "*~ ")
    if (
        boxes[sum_id].get("text") != "+~"
        or max_delay_tapin is None
        or max_delay_tapout is None
        or max_delay_tapin != max_delay_tapout
        or boxes[sat_id].get("text") != "tanh~"
        or lp_freq is None
        or fb_amount is None
    ):
        return None

    required_lines = [
        _line_key(sum_id, 0, tapin_id, 0),
        _line_key(tapin_id, 0, tapout_id, 0),
        _line_key(tapout_id, 0, sat_id, 0),
        _line_key(sat_id, 0, lp_id, 0),
        _line_key(lp_id, 0, fb_id, 0),
        _line_key(fb_id, 0, sum_id, 1),
    ]
    if not all(line in line_keys for line in required_lines):
        return None

    helper = None
    if (
        float(lp_freq) == 3000.0
        and float(fb_amount) == 0.5
        and _rect_matches(boxes[sum_id], [30, 120, 30, 20])
        and _rect_matches(boxes[tapin_id], [30, 150, 100, 20])
        and _rect_matches(boxes[tapout_id], [30, 180, 100, 20])
        and _rect_matches(boxes[sat_id], [30, 210, 45, 20])
        and _rect_matches(boxes[lp_id], [30, 240, 90, 20])
        and _rect_matches(boxes[fb_id], [30, 270, 50, 20])
    ):
        helper_kwargs = {}
        if max_delay_tapin != 5000:
            helper_kwargs["max_delay_ms"] = max_delay_tapin
        helper = {
            "name": "feedback_delay",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="feedback_delay",
        prefix=prefix,
        box_ids=[sum_id, tapin_id, tapout_id, sat_id, lp_id, fb_id],
        line_keys=required_lines,
        params={
            "max_delay_ms": max_delay_tapin,
            "lp_freq": _normalize_number(float(lp_freq)),
            "feedback_amount": _normalize_number(float(fb_amount)),
        },
        helper=helper,
    )


PATTERN_MATCHERS = [
    ([""], _match_feedback_delay),
    (["_transport", "_bpm", "_rate", "_osc"], _match_transport_lfo),
    (["_osc", "_depth"], _match_lfo),
    (["_enc_add", "_enc_sub", "_enc_mid", "_enc_side", "_dec_add", "_dec_sub"], _match_ms_encode_decode),
    (["_l", "_r", "_out_l", "_out_r"], _match_svf_filter),
    (["_tapin", "_tapout"], _match_delay_line),
    (["_pack", "_line"], _match_param_smooth),
    (["_l", "_r"], _match_dc_block),
    (["_l", "_r"], _match_saturation),
    (["_l", "_r"], _match_onepole_filter),
    (["_l", "_r"], _match_gain_stage),
    ([""], _match_selector),
]


def detect_snapshot_patterns(snapshot: dict) -> list[dict]:
    """Detect known m4l-builder DSP/helper patterns inside a snapshot."""
    boxes_by_id, box_indices, line_keys = _snapshot_graph(snapshot)
    used_boxes = set()
    used_lines = set()
    patterns = []

    for suffixes, matcher in PATTERN_MATCHERS:
        for prefix in _candidate_prefixes(boxes_by_id, suffixes):
            match = matcher(prefix, boxes_by_id, line_keys)
            if match is None:
                continue
            if any(box_id in used_boxes for box_id in match["box_ids"]):
                continue
            if any(line_key in used_lines for line_key in match["line_keys"]):
                continue
            match["first_box_index"] = min(box_indices.get(box_id, 10 ** 9) for box_id in match["box_ids"])
            patterns.append(match)
            used_boxes.update(match["box_ids"])
            used_lines.update(match["line_keys"])

    patterns.sort(key=lambda item: (item["first_box_index"], item["kind"], item["prefix"]))
    return patterns


def _match_gain_controlled_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> Optional[dict]:
    dial_id = f"{prefix}_dial"
    dbtoa_id = f"{prefix}_dbtoa"
    gain_id = f"{prefix}_gain"
    dial = boxes_by_id.get(dial_id)
    dbtoa = boxes_by_id.get(dbtoa_id)
    gain = boxes_by_id.get(gain_id)
    smooth = pattern_index.get(("param_smooth", f"{prefix}_smooth"))
    if not all((dial, dbtoa, gain, smooth)):
        return None

    if not _box_parameter_matches(
        dial,
        maxclass="live.dial",
        varname=f"{prefix}_gain",
        min_val=-70.0,
        max_val=6.0,
        initial=0.0,
        unitstyle=4,
        annotation_name=f"{prefix} Gain",
    ):
        return None
    if dbtoa.get("text") != "dbtoa" or gain.get("text") != "*~ 1.":
        return None

    extra_lines = [
        _line_key(dial_id, 0, dbtoa_id, 0),
        _line_key(dbtoa_id, 0, f"{prefix}_smooth_pack", 0),
        _line_key(f"{prefix}_smooth_line", 0, gain_id, 1),
    ]
    required_line_keys = list(smooth["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    dial_rect = copy.deepcopy(dial.get("presentation_rect") or dial.get("patching_rect"))
    dbtoa_rect = copy.deepcopy(dbtoa.get("patching_rect"))
    x = y = None
    if dbtoa_rect and len(dbtoa_rect) == 4:
        x = _normalize_number(float(dbtoa_rect[0]))
        y = _normalize_number(float(dbtoa_rect[1]))

    recipe = None
    if dial_rect is not None and x is not None and y is not None:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="gain_controlled_stage",
            prefix=prefix,
            positional=[dial_rect],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "gain_controlled_stage",
                "positional": [prefix, dial_rect],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="gain_controlled_stage",
        prefix=prefix,
        box_ids=[dial_id, dbtoa_id, gain_id, *smooth["box_ids"]],
        line_keys=required_line_keys,
        params={
            "dial_rect": dial_rect,
            "x": x,
            "y": y,
        },
        recipe=recipe,
    )


def _match_dry_wet_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> Optional[dict]:
    dial_id = f"{prefix}_dial"
    scale_id = f"{prefix}_scale"
    trig_id = f"{prefix}_trig"
    inv_id = f"{prefix}_inv"
    wet_gain_id = f"{prefix}_wet_gain"
    dry_gain_id = f"{prefix}_dry_gain"
    dial = boxes_by_id.get(dial_id)
    scale = boxes_by_id.get(scale_id)
    trig = boxes_by_id.get(trig_id)
    inv = boxes_by_id.get(inv_id)
    wet_gain = boxes_by_id.get(wet_gain_id)
    dry_gain = boxes_by_id.get(dry_gain_id)
    wet_smooth = pattern_index.get(("param_smooth", f"{prefix}_wet_smooth"))
    dry_smooth = pattern_index.get(("param_smooth", f"{prefix}_dry_smooth"))
    if not all((dial, scale, trig, inv, wet_gain, dry_gain, wet_smooth, dry_smooth)):
        return None

    if not _box_parameter_matches(
        dial,
        maxclass="live.dial",
        varname=f"{prefix}_mix",
        min_val=0.0,
        max_val=100.0,
        initial=50.0,
        unitstyle=5,
        annotation_name=f"{prefix} Dry/Wet",
    ):
        return None
    if (
        scale.get("text") != "*~ 0.01"
        or trig.get("text") != "t f f"
        or inv.get("text") != "!-~ 1."
        or wet_gain.get("text") != "*~ 0."
        or dry_gain.get("text") != "*~ 1."
    ):
        return None

    extra_lines = [
        _line_key(dial_id, 0, trig_id, 0),
        _line_key(trig_id, 0, f"{prefix}_wet_smooth_pack", 0),
        _line_key(f"{prefix}_wet_smooth_line", 0, wet_gain_id, 1),
        _line_key(trig_id, 1, inv_id, 0),
        _line_key(inv_id, 0, f"{prefix}_dry_smooth_pack", 0),
        _line_key(f"{prefix}_dry_smooth_line", 0, dry_gain_id, 1),
    ]
    required_line_keys = list(wet_smooth["line_keys"]) + list(dry_smooth["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    dial_rect = copy.deepcopy(dial.get("presentation_rect") or dial.get("patching_rect"))
    scale_rect = copy.deepcopy(scale.get("patching_rect"))
    x = y = None
    if scale_rect and len(scale_rect) == 4:
        x = _normalize_number(float(scale_rect[0]))
        y = _normalize_number(float(scale_rect[1]))

    recipe = None
    if dial_rect is not None and x is not None and y is not None:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="dry_wet_stage",
            prefix=prefix,
            positional=[dial_rect],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "dry_wet_stage",
                "positional": [prefix, dial_rect],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="dry_wet_stage",
        prefix=prefix,
        box_ids=[dial_id, scale_id, trig_id, inv_id, wet_gain_id, dry_gain_id, *wet_smooth["box_ids"], *dry_smooth["box_ids"]],
        line_keys=required_line_keys,
        params={
            "dial_rect": dial_rect,
            "x": x,
            "y": y,
        },
        recipe=recipe,
    )


def _match_tempo_synced_delay_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> Optional[dict]:
    time_dial_id = f"{prefix}_time_dial"
    fb_dial_id = f"{prefix}_fb_dial"
    transport_id = f"{prefix}_transport"
    loadbang_id = f"{prefix}_loadbang"
    fb_scale_id = f"{prefix}_fb_scale"
    fb_mul_id = f"{prefix}_fb_mul"
    sum_id = f"{prefix}_sum"
    time_dial = boxes_by_id.get(time_dial_id)
    fb_dial = boxes_by_id.get(fb_dial_id)
    transport = boxes_by_id.get(transport_id)
    loadbang = boxes_by_id.get(loadbang_id)
    fb_scale = boxes_by_id.get(fb_scale_id)
    fb_mul = boxes_by_id.get(fb_mul_id)
    total_sum = boxes_by_id.get(sum_id)
    delay = pattern_index.get(("delay_line", f"{prefix}_delay"))
    time_smooth = pattern_index.get(("param_smooth", f"{prefix}_time_smooth"))
    fb_smooth = pattern_index.get(("param_smooth", f"{prefix}_fb_smooth"))
    if not all((time_dial, fb_dial, transport, loadbang, fb_scale, fb_mul, total_sum, delay, time_smooth, fb_smooth)):
        return None

    if not _box_parameter_matches(
        time_dial,
        maxclass="live.dial",
        varname=f"{prefix}_time",
        min_val=1.0,
        max_val=5000.0,
        initial=375.0,
        unitstyle=2,
        annotation_name=f"{prefix} Delay Time",
    ):
        return None
    if not _box_parameter_matches(
        fb_dial,
        maxclass="live.dial",
        varname=f"{prefix}_feedback",
        min_val=0.0,
        max_val=95.0,
        initial=40.0,
        unitstyle=5,
        annotation_name=f"{prefix} Feedback",
    ):
        return None
    if (
        transport.get("text") != "transport"
        or loadbang.get("text") != "loadbang"
        or fb_scale.get("text") != "scale 0. 95. 0. 0.95"
        or fb_mul.get("text") != "*~ 0."
        or total_sum.get("text") != "+~"
    ):
        return None

    extra_lines = [
        _line_key(time_dial_id, 0, f"{prefix}_time_smooth_pack", 0),
        _line_key(f"{prefix}_time_smooth_line", 0, f"{prefix}_delay_tapout", 1),
        _line_key(fb_dial_id, 0, fb_scale_id, 0),
        _line_key(fb_scale_id, 0, f"{prefix}_fb_smooth_pack", 0),
        _line_key(f"{prefix}_fb_smooth_line", 0, fb_mul_id, 1),
        _line_key(f"{prefix}_delay_tapout", 0, fb_mul_id, 0),
        _line_key(fb_mul_id, 0, sum_id, 1),
        _line_key(sum_id, 0, f"{prefix}_delay_tapin", 0),
        _line_key(loadbang_id, 0, transport_id, 0),
    ]
    required_line_keys = list(delay["line_keys"]) + list(time_smooth["line_keys"]) + list(fb_smooth["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    time_dial_rect = copy.deepcopy(time_dial.get("presentation_rect") or time_dial.get("patching_rect"))
    fb_dial_rect = copy.deepcopy(fb_dial.get("presentation_rect") or fb_dial.get("patching_rect"))
    fb_mul_rect = copy.deepcopy(fb_mul.get("patching_rect"))
    transport_rect = copy.deepcopy(transport.get("patching_rect"))
    x = y = None
    if fb_mul_rect and transport_rect and len(fb_mul_rect) == 4 and len(transport_rect) == 4:
        x = _normalize_number(float(fb_mul_rect[0]))
        y = _normalize_number(float(transport_rect[1]))

    recipe = None
    if time_dial_rect is not None and fb_dial_rect is not None and x is not None and y is not None:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="tempo_synced_delay",
            prefix=prefix,
            positional=[time_dial_rect, fb_dial_rect],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "tempo_synced_delay",
                "positional": [prefix, time_dial_rect, fb_dial_rect],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="tempo_synced_delay",
        prefix=prefix,
        box_ids=[
            time_dial_id,
            fb_dial_id,
            transport_id,
            loadbang_id,
            fb_scale_id,
            fb_mul_id,
            sum_id,
            *delay["box_ids"],
            *time_smooth["box_ids"],
            *fb_smooth["box_ids"],
        ],
        line_keys=required_line_keys,
        params={
            "time_dial_rect": time_dial_rect,
            "feedback_dial_rect": fb_dial_rect,
            "x": x,
            "y": y,
        },
        recipe=recipe,
    )


def _match_midi_note_gate_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> Optional[dict]:
    del pattern_index

    notein_id = f"{prefix}_notein"
    stripnote_id = f"{prefix}_stripnote"
    kslider_id = f"{prefix}_kslider"
    notein = boxes_by_id.get(notein_id)
    stripnote = boxes_by_id.get(stripnote_id)
    kslider = boxes_by_id.get(kslider_id)
    if not all((notein, stripnote, kslider)):
        return None

    notein_text = str(notein.get("text", ""))
    if notein_text not in {"notein", "notein 0"}:
        if not notein_text.startswith("notein "):
            return None
    if stripnote.get("text") != "stripnote" or kslider.get("maxclass") != "kslider":
        return None

    required_line_keys = [
        _line_key(notein_id, 0, stripnote_id, 0),
        _line_key(notein_id, 1, stripnote_id, 1),
        _line_key(stripnote_id, 0, kslider_id, 0),
    ]
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    stripnote_rect = copy.deepcopy(stripnote.get("patching_rect"))
    kslider_rect = copy.deepcopy(kslider.get("presentation_rect") or kslider.get("patching_rect"))
    x = y = None
    if stripnote_rect and len(stripnote_rect) == 4:
        x = _normalize_number(float(stripnote_rect[0]))
        y = _normalize_number(float(stripnote_rect[1]) - 30.0)

    notein_channel = 0
    if notein_text not in {"notein", "notein 0"}:
        match = re.fullmatch(r"notein\s+(\d+)", notein_text)
        if match is None:
            return None
        notein_channel = int(match.group(1))

    recipe = None
    if kslider_rect is not None and x is not None and y is not None and notein_channel == 0:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="midi_note_gate",
            prefix=prefix,
            positional=[],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "midi_note_gate",
                "positional": [prefix],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="midi_note_gate",
        prefix=prefix,
        box_ids=[notein_id, stripnote_id, kslider_id],
        line_keys=required_line_keys,
        params={
            "channel": notein_channel,
            "x": x,
            "y": y,
            "kslider_rect": kslider_rect,
        },
        recipe=recipe,
    )


def _match_transport_sync_lfo_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> Optional[dict]:
    depth_dial_id = f"{prefix}_depth_dial"
    depth_mul_id = f"{prefix}_depth_mul"
    menu_id = f"{prefix}_div_menu"
    depth_dial = boxes_by_id.get(depth_dial_id)
    depth_mul = boxes_by_id.get(depth_mul_id)
    menu = boxes_by_id.get(menu_id)
    transport_lfo = pattern_index.get(("transport_lfo", f"{prefix}_lfo"))
    if not all((depth_dial, depth_mul, menu, transport_lfo)):
        return None

    if not _box_parameter_matches(
        depth_dial,
        maxclass="live.dial",
        varname=f"{prefix}_depth",
        min_val=0.0,
        max_val=100.0,
        initial=50.0,
        unitstyle=5,
        annotation_name=f"{prefix} Depth",
    ):
        return None
    if depth_mul.get("text") != "*~ 0.01" or menu.get("maxclass") != "umenu":
        return None
    if menu.get("items") != ["1/4", "1/8", "1/16", "1/32"]:
        return None

    extra_lines = [
        _line_key(depth_dial_id, 0, depth_mul_id, 0),
        _line_key(f"{prefix}_lfo_osc", 0, depth_mul_id, 1),
    ]
    required_line_keys = list(transport_lfo["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    depth_rect = copy.deepcopy(depth_dial.get("presentation_rect") or depth_dial.get("patching_rect"))
    mul_rect = copy.deepcopy(depth_mul.get("patching_rect"))
    x = y = None
    if mul_rect and len(mul_rect) == 4:
        x = _normalize_number(float(mul_rect[0]))
        y = _normalize_number(float(mul_rect[1]) - 60.0)

    recipe = None
    lfo_params = transport_lfo.get("params", {})
    if (
        depth_rect is not None
        and x is not None
        and y is not None
        and lfo_params.get("division") == "1/4"
        and lfo_params.get("shape") == "sine"
    ):
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="transport_sync_lfo_recipe",
            prefix=prefix,
            positional=[],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "transport_sync_lfo_recipe",
                "positional": [prefix],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="transport_sync_lfo_recipe",
        prefix=prefix,
        box_ids=[depth_dial_id, depth_mul_id, menu_id, *transport_lfo["box_ids"]],
        line_keys=required_line_keys,
        params={
            "division": lfo_params.get("division"),
            "shape": lfo_params.get("shape"),
            "x": x,
            "y": y,
            "depth_rect": depth_rect,
        },
        recipe=recipe,
    )


RECIPE_MATCHERS = [
    (["_depth_dial", "_depth_mul", "_div_menu"], _match_transport_sync_lfo_recipe),
    (["_notein", "_stripnote", "_kslider"], _match_midi_note_gate_recipe),
    (["_time_dial", "_fb_dial", "_transport"], _match_tempo_synced_delay_recipe),
    (["_dial", "_scale", "_trig", "_wet_gain", "_dry_gain"], _match_dry_wet_recipe),
    (["_dial", "_dbtoa", "_gain"], _match_gain_controlled_recipe),
]


def detect_snapshot_recipes(snapshot: dict) -> list[dict]:
    """Detect higher-level m4l-builder recipes inside a snapshot."""
    boxes_by_id, box_indices, line_keys = _snapshot_graph(snapshot)
    patterns = detect_snapshot_patterns(snapshot)
    pattern_index = {
        (pattern["kind"], pattern["prefix"]): pattern
        for pattern in patterns
    }
    used_boxes = set()
    used_lines = set()
    recipes = []

    for suffixes, matcher in RECIPE_MATCHERS:
        for prefix in _candidate_prefixes(boxes_by_id, suffixes):
            match = matcher(prefix, boxes_by_id, line_keys, pattern_index)
            if match is None:
                continue
            if any(box_id in used_boxes for box_id in match["box_ids"]):
                continue
            if any(line_key in used_lines for line_key in match["line_keys"]):
                continue
            match["first_box_index"] = min(box_indices.get(box_id, 10 ** 9) for box_id in match["box_ids"])
            recipes.append(match)
            used_boxes.update(match["box_ids"])
            used_lines.update(match["line_keys"])

    recipes.sort(key=lambda item: (item["first_box_index"], item["kind"], item["prefix"]))
    return recipes


def _detect_named_bus_motifs(boxes_by_id: dict, box_indices: dict) -> list[dict]:
    groups: dict[tuple[bool, str], dict[str, Any]] = {}

    for box_id, box in boxes_by_id.items():
        operator = _box_operator(box)
        spec = BUS_OPERATOR_SPECS.get(operator or "")
        if spec is None:
            continue
        text = str(box.get("text", "")).strip()
        parts = text.split()
        if len(parts) < 2:
            continue
        bus_name = " ".join(parts[1:]).strip()
        if not bus_name:
            continue
        key = (spec["signal"], bus_name)
        entry = groups.setdefault(key, {
            "box_ids": [],
            "send_count": 0,
            "receive_count": 0,
            "forms": set(),
        })
        entry["box_ids"].append(box_id)
        entry["forms"].add(operator)
        if spec["direction"] == "send":
            entry["send_count"] += 1
        else:
            entry["receive_count"] += 1

    motifs = []
    for (signal, bus_name), entry in groups.items():
        total = entry["send_count"] + entry["receive_count"]
        if total < 2 and not (entry["send_count"] and entry["receive_count"]):
            continue
        first_box_index = min(box_indices.get(box_id, 10 ** 9) for box_id in entry["box_ids"])
        motifs.append(_motif_match(
            kind="named_bus",
            box_ids=entry["box_ids"],
            first_box_index=first_box_index,
            params={
                "name": bus_name,
                "signal": signal,
                "sender_count": entry["send_count"],
                "receiver_count": entry["receive_count"],
                "forms": sorted(entry["forms"]),
            },
        ))
    return motifs


def _detect_controller_dispatch_motifs(snapshot: dict, boxes_by_id: dict, box_indices: dict) -> list[dict]:
    components, operators_by_id, full_adjacency = _operator_components(
        snapshot,
        boxes_by_id,
        box_indices,
        lambda operator: operator in CONTROLLER_DISPATCH_OPERATORS,
    )
    motifs = []
    primary_operators = {"route", "sel", "gate", "switch", "gswitch", "split"}
    for component in components:
        operator_counts: dict[str, int] = {}
        route_selectors = []
        selector_values = []
        trigger_shapes = []
        gate_texts = []
        for box_id in component:
            operator = operators_by_id[box_id]
            operator_counts[operator] = operator_counts.get(operator, 0) + 1
            text = str(boxes_by_id[box_id].get("text", "")).strip()
            if operator == "route":
                route_selectors.extend(text.split()[1:])
            elif operator == "sel":
                selector_values.extend(text.split()[1:])
            elif operator in {"trigger", "t"}:
                trigger_shapes.append(" ".join(text.split()[1:]).strip())
            elif operator in {"gate", "switch", "gswitch", "split"}:
                gate_texts.append(text)

        active_primary = sorted(operator for operator in operator_counts if operator in primary_operators)
        if not active_primary:
            continue
        if len(component) < 2 and not _adjacent_message_texts(component, full_adjacency, boxes_by_id):
            continue

        archetypes = []
        if "route" in operator_counts:
            archetypes.append("route_dispatch")
        if "sel" in operator_counts:
            archetypes.append("selector_dispatch")
        if {"gate", "switch", "gswitch", "split"} & set(operator_counts):
            archetypes.append("state_gate")
        if ("route" in operator_counts or "sel" in operator_counts) and (
            {"gate", "switch", "gswitch", "split"} & set(operator_counts)
        ):
            archetypes.append("gated_route")
        if {"trigger", "t"} & set(operator_counts):
            archetypes.append("trigger_fanout")

        motifs.append(_motif_match(
            kind="controller_dispatch",
            box_ids=component,
            first_box_index=min(box_indices.get(box_id, 10 ** 9) for box_id in component),
            params={
                "operator_counts": {
                    name: operator_counts[name]
                    for name in sorted(operator_counts)
                },
                "primary_operators": active_primary,
                "trigger_shapes": sorted(shape for shape in set(trigger_shapes) if shape),
                "route_selectors": sorted(set(route_selectors)),
                "selector_values": sorted(set(selector_values)),
                "gate_texts": sorted(set(gate_texts)),
                "adjacent_message_texts": _adjacent_message_texts(component, full_adjacency, boxes_by_id),
                "archetypes": sorted(set(archetypes)),
            },
        ))
    return motifs


def _detect_scheduler_chain_motifs(snapshot: dict, boxes_by_id: dict, box_indices: dict) -> list[dict]:
    components, operators_by_id, full_adjacency = _operator_components(
        snapshot,
        boxes_by_id,
        box_indices,
        lambda operator: operator in SCHEDULER_OPERATORS,
    )
    motifs = []
    for component in components:
        operator_counts: dict[str, int] = {}
        trigger_shapes = []
        timing_texts = []
        load_messages = []
        for box_id in component:
            operator = operators_by_id[box_id]
            operator_counts[operator] = operator_counts.get(operator, 0) + 1
            text = str(boxes_by_id[box_id].get("text", "")).strip()
            if operator in {"trigger", "t"}:
                trigger_shapes.append(" ".join(text.split()[1:]).strip())
            elif operator in {"delay", "del", "pipe"}:
                timing_texts.append(text)
            elif operator == "loadmess":
                load_messages.append(" ".join(text.split()[1:]).strip())

        scheduler_ops = {"loadbang", "loadmess", "deferlow", "delay", "del", "pipe", "onebang"} & set(operator_counts)
        if not scheduler_ops:
            continue
        if len(component) < 2 and not _adjacent_message_texts(component, full_adjacency, boxes_by_id):
            continue

        archetypes = []
        if {"loadbang", "loadmess"} & set(operator_counts):
            archetypes.append("init_chain")
        if {"loadbang", "loadmess"} & set(operator_counts) and "deferlow" in operator_counts:
            archetypes.append("deferred_init")
        if {"loadbang", "loadmess"} & set(operator_counts) and {"trigger", "t"} & set(operator_counts):
            archetypes.append("init_fanout")
        if "deferlow" in operator_counts and {"trigger", "t"} & set(operator_counts):
            archetypes.append("deferred_fanout")
        if {"delay", "del", "pipe"} & set(operator_counts):
            archetypes.append("timed_dispatch")

        motifs.append(_motif_match(
            kind="scheduler_chain",
            box_ids=component,
            first_box_index=min(box_indices.get(box_id, 10 ** 9) for box_id in component),
            params={
                "operator_counts": {
                    name: operator_counts[name]
                    for name in sorted(operator_counts)
                },
                "trigger_shapes": sorted(shape for shape in set(trigger_shapes) if shape),
                "timing_texts": sorted(set(timing_texts)),
                "load_messages": sorted(message for message in set(load_messages) if message),
                "adjacent_message_texts": _adjacent_message_texts(component, full_adjacency, boxes_by_id),
                "archetypes": sorted(set(archetypes)),
            },
        ))
    return motifs


def _detect_state_bundle_motifs(snapshot: dict, boxes_by_id: dict, box_indices: dict) -> list[dict]:
    components, operators_by_id, full_adjacency = _operator_components(
        snapshot,
        boxes_by_id,
        box_indices,
        _matches_state_bundle_operator,
    )
    motifs = []
    for component in components:
        operator_counts: dict[str, int] = {}
        pack_texts = []
        unpack_texts = []
        zl_operators = []
        for box_id in component:
            operator = operators_by_id[box_id]
            operator_counts[operator] = operator_counts.get(operator, 0) + 1
            text = str(boxes_by_id[box_id].get("text", "")).strip()
            if operator in {"pack", "pak", "join", "buddy"}:
                pack_texts.append(text)
            elif operator == "unpack":
                unpack_texts.append(text)
            if operator == "zl" or operator.startswith("zl."):
                zl_operators.append(operator)

        bundle_ops = {"pack", "pak", "unpack", "join", "buddy"} & set(operator_counts)
        has_zl = bool(zl_operators)
        if not bundle_ops and not has_zl:
            continue
        if len(component) < 2 and not _adjacent_message_texts(component, full_adjacency, boxes_by_id):
            continue

        archetypes = []
        if {"pack", "pak", "join", "buddy"} & set(operator_counts):
            archetypes.append("bundle_pack")
        if "unpack" in operator_counts:
            archetypes.append("bundle_fanout")
        if {"pack", "pak", "join", "buddy"} & set(operator_counts) and "unpack" in operator_counts:
            archetypes.append("pack_unpack")
        if has_zl:
            archetypes.append("list_transform")

        motifs.append(_motif_match(
            kind="state_bundle",
            box_ids=component,
            first_box_index=min(box_indices.get(box_id, 10 ** 9) for box_id in component),
            params={
                "operator_counts": {
                    name: operator_counts[name]
                    for name in sorted(operator_counts)
                },
                "pack_texts": sorted(set(pack_texts)),
                "unpack_texts": sorted(set(unpack_texts)),
                "zl_operators": sorted(set(zl_operators)),
                "adjacent_message_texts": _adjacent_message_texts(component, full_adjacency, boxes_by_id),
                "archetypes": sorted(set(archetypes)),
            },
        ))
    return motifs


def _detect_live_api_component_motifs(snapshot: dict, boxes_by_id: dict, box_indices: dict) -> list[dict]:
    relevant_ids = set()
    operators_by_id: dict[str, str] = {}
    for box_id, box in boxes_by_id.items():
        operator = _box_operator(box)
        if operator in LIVE_API_CORE_OPERATORS or operator in LIVE_API_HELPER_OPERATORS:
            relevant_ids.add(box_id)
            operators_by_id[box_id] = operator

    adjacency = {box_id: set() for box_id in relevant_ids}
    full_adjacency = {box_id: set() for box_id in boxes_by_id}
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
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

    motifs = []
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

        operator_counts: dict[str, int] = {}
        for box_id in component:
            operator = operators_by_id[box_id]
            operator_counts[operator] = operator_counts.get(operator, 0) + 1

        core_operators = sorted(
            operator
            for operator in operator_counts
            if operator in LIVE_API_CORE_OPERATORS
        )
        if not core_operators:
            continue
        if len(component) < 2 and len(core_operators) < 2:
            continue

        path_targets = []
        route_selectors = []
        prepend_targets = []
        direct_message_texts = []
        property_names = []
        get_targets = []
        set_targets = []
        call_targets = []
        for box_id in component:
            box = boxes_by_id[box_id]
            operator = operators_by_id[box_id]
            text = str(box.get("text", "")).strip()
            if operator == "live.path":
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    path_targets.append(parts[1])
            elif operator == "route":
                parts = text.split()[1:]
                route_selectors.extend(parts)
            elif operator == "prepend":
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    prepend_targets.append(parts[1])

            for neighbor_id in full_adjacency.get(box_id, set()):
                if neighbor_id in component:
                    continue
                neighbor = boxes_by_id.get(neighbor_id)
                if not neighbor or neighbor.get("maxclass") != "message":
                    continue
                message_text = str(neighbor.get("text", "")).strip()
                if not message_text:
                    continue
                direct_message_texts.append(message_text)
                parsed = _parse_live_api_message_text(message_text)
                path_targets.extend(parsed["paths"])
                property_names.extend(parsed["properties"])
                get_targets.extend(parsed["gets"])
                set_targets.extend(parsed["sets"])
                call_targets.extend(parsed["calls"])

        params = {
            "operator_counts": {
                name: operator_counts[name]
                for name in sorted(operator_counts)
            },
            "core_operators": core_operators,
            "core_operator_count": sum(operator_counts[name] for name in core_operators),
            "helper_operator_count": sum(
                count
                for name, count in operator_counts.items()
                if name in LIVE_API_HELPER_OPERATORS
            ),
            "path_targets": sorted(set(path_targets)),
            "route_selectors": sorted(set(route_selectors)),
            "prepend_targets": sorted(set(prepend_targets)),
            "property_names": sorted(set(name for name in property_names if name)),
            "get_targets": sorted(set(name for name in get_targets if name)),
            "set_targets": sorted(set(name for name in set_targets if name)),
            "call_targets": sorted(set(name for name in call_targets if name)),
            "direct_message_texts": sorted(set(direct_message_texts)),
        }
        params["archetypes"] = _classify_live_api_component_archetypes(params)

        first_box_index = min(box_indices.get(box_id, 10 ** 9) for box_id in component)
        motifs.append(_motif_match(
            kind="live_api_component",
            box_ids=list(component),
            first_box_index=first_box_index,
            params=params,
        ))
    return motifs


def _sample_buffer_component_label(box: dict) -> Optional[str]:
    operator = _box_operator(box)
    if operator in SAMPLE_BUFFER_CORE_OPERATORS or operator in SAMPLE_BUFFER_HELPER_OPERATORS:
        return operator
    if box.get("maxclass") == "live.drop":
        return "live.drop"
    return None


def _gen_processing_component_label(box: dict) -> Optional[str]:
    operator = _box_operator(box)
    if operator in GEN_PROCESSING_CORE_OPERATORS or operator in GEN_PROCESSING_HELPER_OPERATORS:
        return operator
    return None


def _detect_sample_buffer_toolchain_motifs(snapshot: dict, boxes_by_id: dict, box_indices: dict) -> list[dict]:
    components, labels_by_id, full_adjacency = _relevant_box_components(
        snapshot,
        boxes_by_id,
        box_indices,
        _sample_buffer_component_label,
    )
    merged_components = []
    component_targets = []
    for component in components:
        buffer_targets = {
            _buffer_target_name(boxes_by_id[box_id])
            for box_id in component
            if labels_by_id[box_id] in SAMPLE_BUFFER_CORE_OPERATORS
        }
        component_targets.append({target for target in buffer_targets if target})

    used_components = set()
    for index, component in enumerate(components):
        if index in used_components:
            continue
        merged_ids = set(component)
        merged_targets = set(component_targets[index])
        used_components.add(index)
        changed = True
        while changed:
            changed = False
            for other_index, other_component in enumerate(components):
                if other_index in used_components:
                    continue
                other_targets = component_targets[other_index]
                if not merged_targets or not other_targets or not (merged_targets & other_targets):
                    continue
                merged_ids.update(other_component)
                merged_targets.update(other_targets)
                used_components.add(other_index)
                changed = True
        merged_components.append(sorted(merged_ids, key=lambda item: box_indices.get(item, 10 ** 9)))

    motifs = []
    file_ops = {"date", "opendialog", "regexp", "relativepath", "sprintf", "strippath"}
    for component in merged_components:
        label_counts: dict[str, int] = {}
        buffer_targets = []
        drop_varnames = []
        for box_id in component:
            label = labels_by_id[box_id]
            label_counts[label] = label_counts.get(label, 0) + 1
            box = boxes_by_id[box_id]
            if label == "buffer~":
                target = _buffer_target_name(box)
                if target:
                    buffer_targets.append(target)
            elif label in {"info~", "peek~", "poke~", "play~", "record~", "groove~", "waveform~", "polybuffer~"}:
                target = _buffer_target_name(box)
                if target:
                    buffer_targets.append(target)
            elif label == "live.drop" and box.get("varname"):
                drop_varnames.append(str(box.get("varname")))

        core_count = sum(label_counts.get(operator, 0) for operator in SAMPLE_BUFFER_CORE_OPERATORS)
        has_live_drop = bool(label_counts.get("live.drop"))
        if not label_counts.get("buffer~"):
            continue
        if core_count + int(has_live_drop) < 2:
            continue

        archetypes = []
        if has_live_drop or any(label_counts.get(name) for name in file_ops):
            archetypes.append("sample_import")
        if label_counts.get("info~"):
            archetypes.append("sample_metadata")
        if label_counts.get("peek~") or label_counts.get("waveform~"):
            archetypes.append("waveform_probe")
        if label_counts.get("poke~") or label_counts.get("record~"):
            archetypes.append("buffer_write")
        if label_counts.get("groove~") or label_counts.get("play~"):
            archetypes.append("buffer_playback")
        if label_counts.get("metro") or label_counts.get("uzi"):
            archetypes.append("driven_visual_probe")
        if not archetypes:
            archetypes.append("buffer_utility")

        motifs.append(_motif_match(
            kind="sample_buffer_toolchain",
            box_ids=component,
            first_box_index=min(box_indices.get(box_id, 10 ** 9) for box_id in component),
            params={
                "operator_counts": {
                    name: label_counts[name]
                    for name in sorted(label_counts)
                },
                "core_operators": [
                    name
                    for name in sorted(SAMPLE_BUFFER_CORE_OPERATORS)
                    if label_counts.get(name)
                ],
                "has_live_drop": has_live_drop,
                "buffer_targets": sorted(set(buffer_targets)),
                "drop_varnames": sorted(set(drop_varnames)),
                "file_operators": [
                    name
                    for name in sorted(file_ops)
                    if label_counts.get(name)
                ],
                "adjacent_message_texts": _adjacent_message_texts(component, full_adjacency, boxes_by_id),
                "archetypes": sorted(set(archetypes)),
            },
        ))
    return motifs


def _detect_gen_processing_core_motifs(snapshot: dict, boxes_by_id: dict, box_indices: dict) -> list[dict]:
    components, labels_by_id, full_adjacency = _relevant_box_components(
        snapshot,
        boxes_by_id,
        box_indices,
        _gen_processing_component_label,
    )
    motifs = []
    for component in components:
        label_counts: dict[str, int] = {}
        buffer_targets = []
        for box_id in component:
            label = labels_by_id[box_id]
            label_counts[label] = label_counts.get(label, 0) + 1
            if label == "buffer~":
                target = _buffer_target_name(boxes_by_id[box_id])
                if target:
                    buffer_targets.append(target)

        gen_count = sum(label_counts.get(operator, 0) for operator in GEN_PROCESSING_CORE_OPERATORS)
        helper_count = sum(
            count
            for name, count in label_counts.items()
            if name not in GEN_PROCESSING_CORE_OPERATORS
        )
        if not gen_count or not helper_count:
            continue

        archetypes = []
        if label_counts.get("buffer~"):
            archetypes.append("buffered_gen_core")
        if label_counts.get("click~") or label_counts.get("delay") or label_counts.get("del"):
            archetypes.append("triggered_gen_core")
        if label_counts.get("route") or label_counts.get("gate") or label_counts.get("sel"):
            archetypes.append("routed_gen_core")
        if label_counts.get("p"):
            archetypes.append("nested_gen_shell")
        if not archetypes:
            archetypes.append("gen_utility")

        motifs.append(_motif_match(
            kind="gen_processing_core",
            box_ids=component,
            first_box_index=min(box_indices.get(box_id, 10 ** 9) for box_id in component),
            params={
                "operator_counts": {
                    name: label_counts[name]
                    for name in sorted(label_counts)
                },
                "core_operators": [
                    name
                    for name in sorted(GEN_PROCESSING_CORE_OPERATORS)
                    if label_counts.get(name)
                ],
                "buffer_targets": sorted(set(buffer_targets)),
                "adjacent_message_texts": _adjacent_message_texts(component, full_adjacency, boxes_by_id),
                "archetypes": sorted(set(archetypes)),
            },
        ))
    return motifs


def _detect_embedded_patcher_motifs(boxes_by_id: dict, box_indices: dict) -> list[dict]:
    motifs = []
    for box_id, box in boxes_by_id.items():
        host_kind, target = _embedded_patcher_kind_and_target(box)
        if host_kind is None:
            continue
        motifs.append(_motif_match(
            kind="embedded_patcher",
            box_ids=[box_id],
            first_box_index=box_indices.get(box_id, 10 ** 9),
            params={
                "host_kind": host_kind,
                "target": target,
                "embedded": bool(box.get("patcher")) or host_kind == "subpatcher" or bool(box.get("embed")),
            },
        ))
    return motifs


def detect_snapshot_motifs(snapshot: dict) -> list[dict]:
    """Detect generic Max motifs such as named buses and Live API clusters."""
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    motifs = []
    motifs.extend(_detect_named_bus_motifs(boxes_by_id, box_indices))
    motifs.extend(_detect_controller_dispatch_motifs(snapshot, boxes_by_id, box_indices))
    motifs.extend(_detect_scheduler_chain_motifs(snapshot, boxes_by_id, box_indices))
    motifs.extend(_detect_state_bundle_motifs(snapshot, boxes_by_id, box_indices))
    motifs.extend(_detect_live_api_component_motifs(snapshot, boxes_by_id, box_indices))
    motifs.extend(_detect_sample_buffer_toolchain_motifs(snapshot, boxes_by_id, box_indices))
    motifs.extend(_detect_gen_processing_core_motifs(snapshot, boxes_by_id, box_indices))
    motifs.extend(_detect_embedded_patcher_motifs(boxes_by_id, box_indices))
    motifs.sort(key=lambda item: (item["first_box_index"], item["kind"], item["box_ids"]))
    return motifs


def _detect_live_api_helper_matches(snapshot: dict, motifs: Optional[list[dict]] = None) -> list[dict]:
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    motifs = motifs if motifs is not None else detect_snapshot_motifs(snapshot)
    matches = []

    for motif in motifs:
        if motif.get("kind") != "live_api_component":
            continue

        component_ids = motif.get("box_ids", [])
        operator_ids: dict[str, list[str]] = {}
        for box_id in component_ids:
            box = boxes_by_id.get(box_id)
            if box is None:
                continue
            operator = _box_operator(box)
            if operator:
                operator_ids.setdefault(operator, []).append(box_id)

        live_path_ids = operator_ids.get("live.path", [])
        live_object_ids = operator_ids.get("live.object", [])
        live_observer_ids = operator_ids.get("live.observer", [])
        thisdevice_ids = operator_ids.get("live.thisdevice", [])
        prepend_ids = operator_ids.get("prepend", [])

        if len(live_path_ids) == 1 and len(live_object_ids) == 1 and len(live_observer_ids) == 1:
            path_id = live_path_ids[0]
            object_id = live_object_ids[0]
            observer_id = live_observer_ids[0]
            path_box = boxes_by_id[path_id]
            object_box = boxes_by_id[object_id]
            observer_box = boxes_by_id[observer_id]
            path_text = str(path_box.get("text", "")).strip()
            observer_text = str(observer_box.get("text", "")).strip()
            if path_text.startswith("live.path ") and observer_text.startswith("live.observer "):
                prefix = _infer_helper_prefix(
                    [path_id, object_id, observer_id],
                    ["_path", "_obj", "_observer"],
                )
                path = path_text[len("live.path "):].strip()
                prop = observer_text[len("live.observer "):].strip()
                match = _canonical_live_api_helper_match(
                    snapshot,
                    boxes_by_id,
                    box_indices,
                    kind="live_observer",
                    box_ids=[path_id, object_id, observer_id],
                    helper_name="live_observer",
                    helper_fn=live_observer,
                    helper_positional=[prefix],
                    helper_kwargs={
                        "path": path,
                        "prop": prop,
                        "path_id": path_id,
                        "object_id": object_id,
                        "observer_id": observer_id,
                        "path_rect": copy.deepcopy(path_box.get("patching_rect")),
                        "object_rect": copy.deepcopy(object_box.get("patching_rect")),
                        "observer_rect": copy.deepcopy(observer_box.get("patching_rect")),
                        "path_attrs": _live_api_helper_box_attrs(
                            path_box,
                            ["id", "maxclass", "text", "patching_rect"],
                        ),
                        "object_attrs": _live_api_helper_box_attrs(
                            object_box,
                            ["id", "maxclass", "text", "patching_rect"],
                        ),
                        "observer_attrs": _live_api_helper_box_attrs(
                            observer_box,
                            ["id", "maxclass", "text", "patching_rect"],
                        ),
                        "include_default_style": _live_api_include_default_style(
                            path_box,
                            object_box,
                            observer_box,
                        ),
                    },
                    params={
                        "archetypes": motif.get("params", {}).get("archetypes", []),
                        "path": path,
                        "prop": prop,
                    },
                )
                if match is not None:
                    matches.append(match)
                    continue

        if len(live_path_ids) == 1 and not live_object_ids and len(live_observer_ids) == 1:
            path_id = live_path_ids[0]
            observer_id = live_observer_ids[0]
            path_box = boxes_by_id[path_id]
            observer_box = boxes_by_id[observer_id]
            path_text = str(path_box.get("text", "")).strip()
            observer_text = str(observer_box.get("text", "")).strip()
            adjacent_messages = _adjacent_message_boxes_for_component(snapshot, component_ids, boxes_by_id)
            property_messages = [
                box for box in adjacent_messages
                if str(box.get("text", "")).strip().startswith("property ")
            ]
            if path_text.startswith("live.path "):
                prefix = _infer_helper_prefix(
                    [path_id, observer_id] + [box.get("id") for box in property_messages if box.get("id")],
                    ["_path", "_observer", "_property"],
                )
                path = path_text[len("live.path "):].strip()
                prop = None
                helper_kwargs = {
                    "path": path,
                    "path_id": path_id,
                    "observer_id": observer_id,
                    "path_rect": copy.deepcopy(path_box.get("patching_rect")),
                    "observer_rect": copy.deepcopy(observer_box.get("patching_rect")),
                    "via_object": False,
                    "path_attrs": _live_api_helper_box_attrs(
                        path_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "observer_attrs": _live_api_helper_box_attrs(
                        observer_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                }
                box_ids = [path_id, observer_id]
                if observer_text.startswith("live.observer "):
                    prop = observer_text[len("live.observer "):].strip()
                elif len(property_messages) == 1:
                    property_box = property_messages[0]
                    prop = str(property_box.get("text", "")).strip()[len("property "):].strip()
                    helper_kwargs["bind_via_message"] = True
                    helper_kwargs["property_id"] = property_box.get("id")
                    helper_kwargs["property_rect"] = copy.deepcopy(property_box.get("patching_rect"))
                    helper_kwargs["property_attrs"] = _live_api_helper_box_attrs(
                        property_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    )
                    box_ids.append(property_box.get("id"))
                if prop:
                    helper_kwargs["include_default_style"] = _live_api_include_default_style(
                        path_box,
                        observer_box,
                    )
                    helper_kwargs["prop"] = prop
                    match = _canonical_live_api_helper_match(
                        snapshot,
                        boxes_by_id,
                        box_indices,
                        kind="live_observer",
                        box_ids=box_ids,
                        helper_name="live_observer",
                        helper_fn=live_observer,
                        helper_positional=[prefix],
                        helper_kwargs=helper_kwargs,
                        params={
                            "archetypes": motif.get("params", {}).get("archetypes", []),
                            "path": path,
                            "prop": prop,
                            "via_object": False,
                        },
                    )
                    if match is not None:
                        matches.append(match)
                        continue

        if (
            len(thisdevice_ids) == 1
            and len(live_path_ids) == 1
            and not live_object_ids
            and len(live_observer_ids) == 1
            and len(operator_ids.get("sel", [])) == 1
            and len(operator_ids.get("t", [])) == 2
        ):
            property_box = _adjacent_property_message_box(
                snapshot,
                component_ids,
                boxes_by_id,
            )
            if property_box is not None:
                helper_box_ids = list(component_ids) + [property_box.get("id")]
                prefix = _infer_helper_prefix(
                    helper_box_ids,
                    ["_device", "_init", "_path", "_property", "_observer", "_value", "_selector"],
                )
                params = {
                    "archetypes": motif.get("params", {}).get("archetypes", []),
                    "path": str(boxes_by_id[live_path_ids[0]].get("text", "")).strip()[len("live.path "):].strip(),
                    "prop": str(property_box.get("text", "")).strip()[len("property "):].strip(),
                }
                helper_call = _live_api_helper_call_from_snapshot(
                    snapshot,
                    boxes_by_id,
                    box_indices,
                    helper_name="live_state_observer",
                    prefix=prefix,
                    component_box_ids=helper_box_ids,
                    params=params,
                )
                required_keys = {
                    "device_id",
                    "init_trigger_id",
                    "path_id",
                    "property_id",
                    "observer_id",
                    "value_trigger_id",
                    "selector_id",
                }
                if required_keys.issubset(helper_call.get("kwargs", {})):
                    match = _canonical_live_api_helper_match(
                        snapshot,
                        boxes_by_id,
                        box_indices,
                        kind="live_state_observer",
                        box_ids=helper_call.get("consume_box_ids", helper_box_ids),
                        helper_name="live_state_observer",
                        helper_fn=live_state_observer,
                        helper_positional=[prefix],
                        helper_kwargs=helper_call.get("kwargs", {}),
                        params=params,
                    )
                    if match is not None:
                        matches.append(match)
                        continue

        if len(live_path_ids) == 1 and len(live_object_ids) == 1 and not live_observer_ids:
            path_id = live_path_ids[0]
            object_id = live_object_ids[0]
            path_box = boxes_by_id[path_id]
            object_box = boxes_by_id[object_id]
            path_text = str(path_box.get("text", "")).strip()
            object_text = str(object_box.get("text", "")).strip()
            if path_text.startswith("live.path "):
                probe_message = _adjacent_probe_message_box(snapshot, [path_id, object_id], boxes_by_id)
                prefix_box_ids = [path_id, object_id]
                if probe_message is not None and probe_message.get("id"):
                    prefix_box_ids.append(probe_message.get("id"))
                prefix = _infer_helper_prefix(prefix_box_ids, ["_path", "_obj", "_message"])
                path = path_text[len("live.path "):].strip()
                helper_name = None
                helper_fn = None
                helper_kwargs = {
                    "path": path,
                    "path_id": path_id,
                    "object_id": object_id,
                    "path_rect": copy.deepcopy(path_box.get("patching_rect")),
                    "object_rect": copy.deepcopy(object_box.get("patching_rect")),
                    "path_attrs": _live_api_helper_box_attrs(
                        path_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "object_attrs": _live_api_helper_box_attrs(
                        object_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "include_default_style": _live_api_include_default_style(
                        path_box,
                        object_box,
                    ),
                }
                params = {
                    "archetypes": motif.get("params", {}).get("archetypes", []),
                    "path": path,
                }
                if object_text == "live.object":
                    if probe_message is not None:
                        helper_name = "live_parameter_probe"
                        helper_fn = live_parameter_probe
                        helper_kwargs["message_id"] = probe_message.get("id")
                        helper_kwargs["message_rect"] = copy.deepcopy(probe_message.get("patching_rect"))
                        helper_kwargs["message_attrs"] = _live_api_helper_box_attrs(
                            probe_message,
                            ["id", "maxclass", "text", "patching_rect"],
                        )
                        helper_kwargs["commands"] = _message_segments(str(probe_message.get("text", "")))
                        helper_kwargs["message_line_attrs"] = _line_attrs_from_snapshot(
                            snapshot,
                            probe_message.get("id"),
                            0,
                            object_id,
                            0,
                        )
                        params["commands"] = copy.deepcopy(helper_kwargs["commands"])
                        params["get_targets"] = copy.deepcopy(
                            motif.get("params", {}).get("get_targets", [])
                        )
                        params["call_targets"] = copy.deepcopy(
                            motif.get("params", {}).get("call_targets", [])
                        )
                    else:
                        helper_name = "live_object_path"
                        helper_fn = live_object_path
                elif object_text.startswith("live.object set "):
                    helper_name = "live_set_control"
                    helper_fn = live_set_control
                    helper_kwargs["prop"] = object_text[len("live.object set "):].strip()
                    params["prop"] = helper_kwargs["prop"]
                if helper_name is not None:
                    helper_box_ids = [path_id, object_id]
                    if helper_name == "live_parameter_probe" and probe_message is not None:
                        helper_box_ids.append(probe_message.get("id"))
                    match = _canonical_live_api_helper_match(
                        snapshot,
                        boxes_by_id,
                        box_indices,
                        kind=helper_name,
                        box_ids=helper_box_ids,
                        helper_name=helper_name,
                        helper_fn=helper_fn,
                        helper_positional=[prefix],
                        helper_kwargs=helper_kwargs,
                        params=params,
                    )
                    if match is not None:
                        matches.append(match)
                        continue

        if not live_path_ids and len(live_object_ids) == 1 and not live_observer_ids:
            object_id = live_object_ids[0]
            object_box = boxes_by_id[object_id]
            object_text = str(object_box.get("text", "")).strip()
            route_ids = operator_ids.get("route", [])
            trigger_ids = operator_ids.get("t", [])
            route_id = route_ids[0] if len(route_ids) == 1 else None
            route_box = boxes_by_id.get(route_id or "")
            probe_message = _adjacent_probe_message_box(snapshot, component_ids, boxes_by_id)
            if (
                object_text == "live.object"
                and probe_message is not None
                and len(route_ids) <= 1
                and len(trigger_ids) <= 1
                and int(motif.get("params", {}).get("helper_operator_count", 0)) == len(route_ids) + len(trigger_ids)
            ):
                helper_box_ids = [object_id, probe_message.get("id")]
                helper_kwargs = {
                    "path": None,
                    "object_id": object_id,
                    "message_id": probe_message.get("id"),
                    "object_rect": copy.deepcopy(object_box.get("patching_rect")),
                    "message_rect": copy.deepcopy(probe_message.get("patching_rect")),
                    "object_attrs": _live_api_helper_box_attrs(
                        object_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "message_attrs": _live_api_helper_box_attrs(
                        probe_message,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "commands": _message_segments(str(probe_message.get("text", ""))),
                    "message_line_attrs": _line_attrs_from_snapshot(
                        snapshot,
                        probe_message.get("id"),
                        0,
                        object_id,
                        0,
                    ),
                }
                if route_box is not None:
                    helper_box_ids.append(route_id)
                    helper_kwargs["route_id"] = route_id
                    helper_kwargs["route_rect"] = copy.deepcopy(route_box.get("patching_rect"))
                    helper_kwargs["route_attrs"] = _live_api_helper_box_attrs(
                        route_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    )
                    helper_kwargs["route_selectors"] = str(route_box.get("text", "")).strip().split()[1:]
                    helper_kwargs["route_line_attrs"] = _line_attrs_from_snapshot(
                        snapshot,
                        object_id,
                        0,
                        route_id,
                        0,
                    )
                trigger_box = None
                trigger_id = trigger_ids[0] if len(trigger_ids) == 1 else None
                if trigger_id is not None:
                    trigger_box = boxes_by_id.get(trigger_id)
                    trigger_message_outlet = _line_source_outlet_to_destination(
                        snapshot,
                        trigger_id,
                        probe_message.get("id"),
                    )
                    trigger_object_outlet = _line_source_outlet_to_destination(
                        snapshot,
                        trigger_id,
                        object_id,
                    )
                    if trigger_box is None or trigger_message_outlet is None or trigger_object_outlet is None:
                        trigger_box = None
                    else:
                        helper_box_ids.append(trigger_id)
                        helper_kwargs["trigger_id"] = trigger_id
                        helper_kwargs["trigger_text"] = str(trigger_box.get("text", "")).strip()
                        helper_kwargs["trigger_rect"] = copy.deepcopy(trigger_box.get("patching_rect"))
                        helper_kwargs["trigger_attrs"] = _live_api_helper_box_attrs(
                            trigger_box,
                            ["id", "maxclass", "text", "patching_rect"],
                        )
                        helper_kwargs["message_from_trigger_outlet"] = trigger_message_outlet
                        helper_kwargs["object_from_trigger_outlet"] = trigger_object_outlet
                        helper_kwargs["trigger_message_line_attrs"] = _line_attrs_from_snapshot(
                            snapshot,
                            trigger_id,
                            trigger_message_outlet,
                            probe_message.get("id"),
                            0,
                        )
                        helper_kwargs["trigger_object_line_attrs"] = _line_attrs_from_snapshot(
                            snapshot,
                            trigger_id,
                            trigger_object_outlet,
                            object_id,
                            0,
                        )
                if trigger_id is not None and trigger_box is None:
                    continue
                prefix = _infer_helper_prefix(
                    helper_box_ids,
                    ["_obj", "_message", "_route", "_trigger"],
                )
                order_pairs = []
                if route_box is not None:
                    order_pairs.append((box_indices.get(route_id, 10 ** 9), "route"))
                order_pairs.append((box_indices.get(probe_message.get("id"), 10 ** 9), "message"))
                if trigger_box is not None and trigger_id:
                    order_pairs.append((box_indices.get(trigger_id, 10 ** 9), "trigger"))
                order_pairs.append((box_indices.get(object_id, 10 ** 9), "object"))
                helper_kwargs["box_order"] = [name for _idx, name in sorted(order_pairs)]
                helper_kwargs["include_default_style"] = _live_api_include_default_style(
                    *(box for box in (object_box, route_box, trigger_box) if box is not None)
                )
                match = _canonical_live_api_helper_match(
                    snapshot,
                    boxes_by_id,
                    box_indices,
                    kind="live_parameter_probe",
                    box_ids=helper_box_ids,
                    helper_name="live_parameter_probe",
                    helper_fn=live_parameter_probe,
                    helper_positional=[prefix],
                    helper_kwargs=helper_kwargs,
                    params={
                        "archetypes": motif.get("params", {}).get("archetypes", []),
                        "path": None,
                        "commands": copy.deepcopy(helper_kwargs["commands"]),
                        "get_targets": copy.deepcopy(motif.get("params", {}).get("get_targets", [])),
                        "call_targets": copy.deepcopy(motif.get("params", {}).get("call_targets", [])),
                        "route_selectors": copy.deepcopy(
                            str(route_box.get("text", "")).strip().split()[1:] if route_box is not None else []
                        ),
                        "trigger_text": helper_kwargs.get("trigger_text"),
                    },
                )
                if match is not None:
                    matches.append(match)
                    continue

        if len(thisdevice_ids) == 1 and len(prepend_ids) == 1:
            device_id = thisdevice_ids[0]
            prepend_id = prepend_ids[0]
            prepend_box = boxes_by_id[prepend_id]
            device_box = boxes_by_id[device_id]
            prepend_text = str(prepend_box.get("text", "")).strip()
            if prepend_text == "prepend active":
                from_device_outlet = _line_source_outlet_to_destination(
                    snapshot,
                    device_id,
                    prepend_id,
                )
                helper_kwargs = {
                    "device_id": device_id,
                    "prepend_id": prepend_id,
                    "device_rect": copy.deepcopy(device_box.get("patching_rect")),
                    "prepend_rect": copy.deepcopy(prepend_box.get("patching_rect")),
                    "device_attrs": _live_api_helper_box_attrs(
                        device_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "prepend_attrs": _live_api_helper_box_attrs(
                        prepend_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "include_default_style": _live_api_include_default_style(
                        prepend_box,
                        device_box,
                    ),
                    "box_order": [
                        name for _idx, name in sorted(
                            [
                                (box_indices.get(prepend_id, 10 ** 9), "prepend"),
                                (box_indices.get(device_id, 10 ** 9), "device"),
                            ]
                        )
                    ],
                }
                if from_device_outlet is not None:
                    helper_kwargs["from_device_outlet"] = from_device_outlet
                    helper_kwargs["device_to_prepend_line_attrs"] = _line_attrs_from_snapshot(
                        snapshot,
                        device_id,
                        from_device_outlet,
                        prepend_id,
                        0,
                    )
                else:
                    helper_kwargs["prepend_to_device_line_attrs"] = _line_attrs_from_snapshot(
                        snapshot,
                        prepend_id,
                        0,
                        device_id,
                        0,
                    )
                prefix = _infer_helper_prefix([prepend_id, device_id], ["_prepend", "_device"])
                match = _canonical_live_api_helper_match(
                    snapshot,
                    boxes_by_id,
                    box_indices,
                    kind="device_active_state",
                    box_ids=[prepend_id, device_id],
                    helper_name="device_active_state",
                    helper_fn=device_active_state,
                    helper_positional=[prefix],
                    helper_kwargs=helper_kwargs,
                    params={"archetypes": motif.get("params", {}).get("archetypes", [])},
                )
                if match is not None:
                    matches.append(match)
                    continue

        if len(thisdevice_ids) == 1 and not prepend_ids:
            device_id = thisdevice_ids[0]
            device_box = boxes_by_id[device_id]
            prefix = _infer_helper_prefix([device_id], ["_device"])
            match = _canonical_live_api_helper_match(
                snapshot,
                boxes_by_id,
                box_indices,
                kind="live_thisdevice",
                box_ids=[device_id],
                helper_name="live_thisdevice",
                helper_fn=live_thisdevice,
                helper_positional=[prefix],
                helper_kwargs={
                    "device_id": device_id,
                    "device_rect": copy.deepcopy(device_box.get("patching_rect")),
                    "device_attrs": _live_api_helper_box_attrs(
                        device_box,
                        ["id", "maxclass", "text", "patching_rect"],
                    ),
                    "include_default_style": _live_api_include_default_style(device_box),
                },
                params={"archetypes": motif.get("params", {}).get("archetypes", [])},
            )
            if match is not None:
                matches.append(match)

    matched_box_ids = {box_id for match in matches for box_id in match["box_ids"]}
    for box_id, box in boxes_by_id.items():
        if box_id in matched_box_ids or _box_operator(box) != "live.thisdevice":
            continue
        prefix = _infer_helper_prefix([box_id], ["_device"])
        match = _canonical_live_api_helper_match(
            snapshot,
            boxes_by_id,
            box_indices,
            kind="live_thisdevice",
            box_ids=[box_id],
            helper_name="live_thisdevice",
            helper_fn=live_thisdevice,
            helper_positional=[prefix],
            helper_kwargs={
                "device_id": box_id,
                "device_rect": copy.deepcopy(box.get("patching_rect")),
                "device_attrs": _live_api_helper_box_attrs(
                    box,
                    ["id", "maxclass", "text", "patching_rect"],
                ),
                "include_default_style": _live_api_include_default_style(box),
            },
            params={"archetypes": ["thisdevice_reference"]},
        )
        if match is not None:
            matches.append(match)

    matches.sort(key=lambda item: (item["first_box_index"], item["kind"], item["prefix"]))
    return matches


def _helper_opportunity(
    *,
    helper_name: str,
    prefix: str,
    box_ids: list[str],
    params: Optional[dict] = None,
    blocking_factors: Optional[list[str]] = None,
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


def _detect_live_api_helper_opportunities(
    snapshot: dict,
    *,
    motifs: Optional[list[dict]] = None,
    exact_matches: Optional[list[dict]] = None,
) -> list[dict]:
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    motifs = motifs if motifs is not None else detect_snapshot_motifs(snapshot)
    exact_matches = exact_matches if exact_matches is not None else _detect_live_api_helper_matches(snapshot, motifs=motifs)
    exact_keys = {
        (match.get("helper", {}).get("name"), tuple(sorted(match.get("box_ids", []))))
        for match in exact_matches
    }
    opportunities = []

    for motif in motifs:
        if motif.get("kind") != "live_api_component":
            continue

        component_ids = motif.get("box_ids", [])
        params = motif.get("params", {})
        operator_ids: dict[str, list[str]] = {}
        for box_id in component_ids:
            box = boxes_by_id.get(box_id)
            if box is None:
                continue
            operator = _box_operator(box)
            if operator:
                operator_ids.setdefault(operator, []).append(box_id)

        helper_name = None
        prefix = _infer_helper_prefix(component_ids, ["_path", "_obj", "_observer", "_prepend", "_device"])
        helper_params = {"archetypes": copy.deepcopy(params.get("archetypes", []))}
        blocking_factors = []
        path_ids = operator_ids.get("live.path", [])
        object_ids = operator_ids.get("live.object", [])
        observer_ids = operator_ids.get("live.observer", [])
        thisdevice_ids = operator_ids.get("live.thisdevice", [])
        prepend_ids = operator_ids.get("prepend", [])
        helper_operator_count = int(params.get("helper_operator_count", 0))

        if len(path_ids) == 1 and len(object_ids) == 1 and len(observer_ids) == 1:
            helper_name = "live_observer"
            path_text = str(boxes_by_id[path_ids[0]].get("text", "")).strip()
            observer_text = str(boxes_by_id[observer_ids[0]].get("text", "")).strip()
            if path_text.startswith("live.path "):
                helper_params["path"] = path_text[len("live.path "):].strip()
                helper_params["via_object"] = True
            if observer_text.startswith("live.observer "):
                helper_params["prop"] = observer_text[len("live.observer "):].strip()
            elif len(params.get("property_names", [])) == 1:
                helper_params["prop"] = params["property_names"][0]
                helper_params["bind_via_message"] = True
                blocking_factors.append("indirect_property_binding")
            else:
                helper_name = None
            if helper_name and (len(component_ids) != 3 or helper_operator_count):
                blocking_factors.append("extra_component_boxes")
        elif len(path_ids) == 1 and not object_ids and len(observer_ids) == 1:
            helper_name = "live_observer"
            path_text = str(boxes_by_id[path_ids[0]].get("text", "")).strip()
            observer_text = str(boxes_by_id[observer_ids[0]].get("text", "")).strip()
            if path_text.startswith("live.path "):
                helper_params["path"] = path_text[len("live.path "):].strip()
                helper_params["via_object"] = False
            if observer_text.startswith("live.observer "):
                helper_params["prop"] = observer_text[len("live.observer "):].strip()
            elif len(params.get("property_names", [])) == 1:
                helper_params["prop"] = params["property_names"][0]
                helper_params["bind_via_message"] = True
                blocking_factors.append("indirect_property_binding")
            else:
                helper_name = None
            if helper_name and (len(component_ids) != 2 or helper_operator_count):
                blocking_factors.append("extra_component_boxes")
        elif len(path_ids) == 1 and len(object_ids) == 1 and not observer_ids:
            path_text = str(boxes_by_id[path_ids[0]].get("text", "")).strip()
            object_text = str(boxes_by_id[object_ids[0]].get("text", "")).strip()
            probe_message = _adjacent_probe_message_box(snapshot, component_ids, boxes_by_id)
            if path_text.startswith("live.path "):
                helper_params["path"] = path_text[len("live.path "):].strip()
                if object_text == "live.object":
                    if probe_message is not None:
                        helper_name = "live_parameter_probe"
                        helper_params["commands"] = _message_segments(str(probe_message.get("text", "")))
                        helper_params["get_targets"] = copy.deepcopy(params.get("get_targets", []))
                        helper_params["call_targets"] = copy.deepcopy(params.get("call_targets", []))
                        helper_params["route_selectors"] = []
                        prefix = _infer_helper_prefix(
                            component_ids + ([probe_message.get("id")] if probe_message.get("id") else []),
                            ["_path", "_obj", "_message"],
                        )
                    else:
                        helper_name = "live_object_path"
                elif object_text.startswith("live.object set "):
                    helper_name = "live_set_control"
                    helper_params["prop"] = object_text[len("live.object set "):].strip()
            if helper_name and (len(component_ids) != 2 or helper_operator_count):
                blocking_factors.append("extra_component_boxes")
        elif not path_ids and len(object_ids) == 1 and not observer_ids:
            object_text = str(boxes_by_id[object_ids[0]].get("text", "")).strip()
            probe_message = _adjacent_probe_message_box(snapshot, component_ids, boxes_by_id)
            route_ids = operator_ids.get("route", [])
            trigger_ids = operator_ids.get("t", [])
            if object_text == "live.object" and probe_message is not None:
                helper_name = "live_parameter_probe"
                helper_params["path"] = None
                helper_params["commands"] = _message_segments(str(probe_message.get("text", "")))
                helper_params["get_targets"] = copy.deepcopy(params.get("get_targets", []))
                helper_params["call_targets"] = copy.deepcopy(params.get("call_targets", []))
                helper_params["route_selectors"] = []
                prefix = _infer_helper_prefix(
                    component_ids + ([probe_message.get("id")] if probe_message.get("id") else []),
                    ["_obj", "_message", "_route", "_trigger"],
                )
                if len(route_ids) == 1:
                    helper_params["route_selectors"] = str(boxes_by_id[route_ids[0]].get("text", "")).strip().split()[1:]
                if len(trigger_ids) == 1:
                    trigger_id = trigger_ids[0]
                    trigger_box = boxes_by_id.get(trigger_id)
                    helper_params["trigger_text"] = str(trigger_box.get("text", "")).strip() if trigger_box else None
                    message_outlet = _line_source_outlet_to_destination(
                        snapshot,
                        trigger_id,
                        probe_message.get("id"),
                    )
                    object_outlet = _line_source_outlet_to_destination(
                        snapshot,
                        trigger_id,
                        object_ids[0],
                    )
                    if message_outlet is not None:
                        helper_params["message_from_trigger_outlet"] = message_outlet
                    if object_outlet is not None:
                        helper_params["object_from_trigger_outlet"] = object_outlet
                    if message_outlet is None or object_outlet is None:
                        blocking_factors.append("extra_component_boxes")
                if helper_operator_count > len(route_ids) + len(trigger_ids) or len(route_ids) > 1 or len(trigger_ids) > 1:
                    blocking_factors.append("extra_component_boxes")
        elif len(thisdevice_ids) == 1 and len(prepend_ids) == 1:
            prepend_text = str(boxes_by_id[prepend_ids[0]].get("text", "")).strip()
            if prepend_text == "prepend active":
                helper_name = "device_active_state"
                from_device_outlet = _line_source_outlet_to_destination(
                    snapshot,
                    thisdevice_ids[0],
                    prepend_ids[0],
                )
                if from_device_outlet is not None:
                    helper_params["from_device_outlet"] = from_device_outlet
                if len(component_ids) != 2 or helper_operator_count > 1:
                    blocking_factors.append("extra_component_boxes")
        elif len(thisdevice_ids) == 1 and not prepend_ids:
            helper_name = "live_thisdevice"

        if not helper_name:
            continue
        if helper_name == "live_thisdevice" and any(
            any(box_id in set(match.get("box_ids", [])) for box_id in thisdevice_ids)
            for match in exact_matches
        ):
            continue
        if any(
            set(component_ids).issubset(set(match.get("box_ids", [])))
            for match in exact_matches
        ):
            continue
        if "noncanonical_box_attrs_or_layout" not in blocking_factors:
            blocking_factors.append("noncanonical_box_attrs_or_layout")
        opportunities.append(
            _helper_opportunity(
                helper_name=helper_name,
                prefix=prefix,
                box_ids=component_ids,
                params=helper_params,
                blocking_factors=blocking_factors,
                first_box_index=motif.get("first_box_index", 0),
            )
        )

    matched_exact_box_ids = {box_id for match in exact_matches for box_id in match.get("box_ids", [])}
    for box_id, box in boxes_by_id.items():
        if box_id in matched_exact_box_ids or _box_operator(box) != "live.thisdevice":
            continue
        key = ("live_thisdevice", (box_id,))
        if key in exact_keys:
            continue
        opportunities.append(
            _helper_opportunity(
                helper_name="live_thisdevice",
                prefix=_infer_helper_prefix([box_id], ["_device"]),
                box_ids=[box_id],
                params={"archetypes": ["thisdevice_reference"]},
                blocking_factors=["noncanonical_box_attrs_or_layout"],
                first_box_index=box_indices.get(box_id, 10 ** 9),
            )
        )

    opportunities.sort(key=lambda item: (item["first_box_index"], item["helper_name"], item["prefix"]))
    return opportunities


def extract_live_api_normalization_candidates(snapshot: dict) -> list[dict]:
    """Return actionable Live API helper rewrite candidates for a snapshot."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs")
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    exact_matches = _detect_live_api_helper_matches(snapshot, motifs=motifs)
    opportunities = _detect_live_api_helper_opportunities(
        snapshot,
        motifs=motifs,
        exact_matches=exact_matches,
    )
    candidates = []
    for match in exact_matches:
        helper = match.get("helper", {})
        candidates.append({
            "helper_name": helper.get("name"),
            "prefix": match.get("prefix"),
            "box_ids": copy.deepcopy(match.get("box_ids", [])),
            "consume_box_ids": copy.deepcopy(match.get("box_ids", [])),
            "params": copy.deepcopy(match.get("params", {})),
            "blocking_factors": [],
            "exact": True,
            "normalization_level": "exact",
            "helper_call": {
                "name": helper.get("name"),
                "positional": copy.deepcopy(helper.get("positional", [])),
                "kwargs": copy.deepcopy(helper.get("kwargs", {})),
                "consume_box_ids": copy.deepcopy(match.get("box_ids", [])),
                "line_keys": copy.deepcopy(match.get("line_keys", [])),
            },
            "line_keys": copy.deepcopy(match.get("line_keys", [])),
            "first_box_index": match.get("first_box_index", 0),
        })
    for entry in opportunities:
        helper_call = _live_api_semantic_helper_call(
            snapshot,
            boxes_by_id,
            box_indices,
            helper_name=entry.get("helper_name"),
            prefix=entry.get("prefix"),
            box_ids=entry.get("box_ids", []),
            params=entry.get("params", {}),
        )
        candidates.append({
            "helper_name": entry.get("helper_name"),
            "prefix": entry.get("prefix"),
            "box_ids": copy.deepcopy(entry.get("box_ids", [])),
            "consume_box_ids": copy.deepcopy(helper_call.get("consume_box_ids", [])),
            "params": copy.deepcopy(entry.get("params", {})),
            "blocking_factors": copy.deepcopy(entry.get("blocking_factors", [])),
            "exact": False,
            "normalization_level": _live_api_normalization_level(entry.get("blocking_factors", [])),
            "helper_call": helper_call,
            "line_keys": copy.deepcopy(helper_call.get("line_keys", [])),
            "first_box_index": entry.get("first_box_index", 0),
        })
    candidates.sort(key=lambda item: (item["first_box_index"], item["helper_name"], item["prefix"]))
    return candidates


def _line_keys_for_box_ids(snapshot: dict, box_ids: set[str]) -> list[tuple]:
    line_keys = []
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
        source = patchline.get("source", [None, 0])[0]
        destination = patchline.get("destination", [None, 0])[0]
        if source in box_ids and destination in box_ids:
            line_keys.append(_line_key_from_wrapped(wrapped))
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


def extract_controller_shell_candidates(snapshot: dict) -> list[dict]:
    """Return snapshot-level controller-shell normalization candidates."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs") or detect_snapshot_motifs(snapshot)
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    object_counts = _root_object_name_counts(boxes_by_id)

    route_dispatch_motifs = [
        motif
        for motif in motifs
        if motif.get("kind") == "controller_dispatch"
        and "route" in motif.get("params", {}).get("primary_operators", [])
    ]
    sel_dispatch_motifs = [
        motif
        for motif in motifs
        if motif.get("kind") == "controller_dispatch"
        and "sel" in motif.get("params", {}).get("primary_operators", [])
    ]
    gate_dispatch_motifs = [
        motif
        for motif in motifs
        if motif.get("kind") == "controller_dispatch"
        and {"gate", "switch", "gswitch", "split"} & set(motif.get("params", {}).get("primary_operators", []))
    ]
    timed_dispatch_motifs = [
        motif
        for motif in motifs
        if motif.get("kind") == "scheduler_chain"
        and "timed_dispatch" in motif.get("params", {}).get("archetypes", [])
    ]
    named_bus_motifs = [
        motif
        for motif in motifs
        if motif.get("kind") == "named_bus"
        and not motif.get("params", {}).get("signal")
    ]
    embedded_motifs = [motif for motif in motifs if motif.get("kind") == "embedded_patcher"]
    live_api_archetypes = {
        archetype
        for motif in motifs
        if motif.get("kind") == "live_api_component"
        for archetype in motif.get("params", {}).get("archetypes", [])
    }

    candidates = []

    has_message_or_trigger = bool(object_counts.get("message") or object_counts.get("t") or object_counts.get("trigger"))
    has_send_receive = bool(
        (object_counts.get("send") and object_counts.get("receive"))
        or (object_counts.get("s") and object_counts.get("r"))
    )
    has_thisdevice = bool(object_counts.get("live.thisdevice") or "thisdevice_reference" in live_api_archetypes)

    if route_dispatch_motifs and has_message_or_trigger and object_counts.get("prepend") and has_thisdevice:
        candidate_box_ids = set()
        for motif in route_dispatch_motifs:
            candidate_box_ids.update(motif.get("box_ids", []))
        for motif in embedded_motifs:
            candidate_box_ids.update(motif.get("box_ids", []))
        for box_id, box in boxes_by_id.items():
            operator = _box_operator(box)
            if operator in {"prepend", "live.thisdevice", "t", "trigger"}:
                candidate_box_ids.add(box_id)
            elif box.get("maxclass") == "message":
                candidate_box_ids.add(box_id)
        first_box_index = min((box_indices.get(box_id, 10 ** 9) for box_id in candidate_box_ids), default=0)
        candidates.append({
            "candidate_name": "controller_surface_shell",
            "box_ids": sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            "line_keys": _line_keys_for_box_ids(snapshot, candidate_box_ids),
            "motif_kinds": ["controller_dispatch"] + (["embedded_patcher"] if embedded_motifs else []),
            "params": {
                "has_named_bus_layer": bool(named_bus_motifs),
                "has_send_receive_layer": has_send_receive,
                "has_thisdevice_layer": has_thisdevice,
                "stable_objects": sorted(
                    name
                    for name in {"message", "t", "trigger", "route", "prepend", "live.thisdevice", "send", "receive", "s", "r"}
                    if object_counts.get(name)
                ),
            },
            "evidence": [
                "route-based controller dispatch",
                "message/trigger/prepend shell",
                "thisdevice-aware control layer",
            ],
            "normalization_level": "semantic_pattern",
            "first_box_index": first_box_index,
        })

    if sel_dispatch_motifs and gate_dispatch_motifs and timed_dispatch_motifs and named_bus_motifs:
        candidate_box_ids = set()
        for motif in sel_dispatch_motifs + gate_dispatch_motifs + timed_dispatch_motifs + named_bus_motifs + embedded_motifs:
            candidate_box_ids.update(motif.get("box_ids", []))
        first_box_index = min((box_indices.get(box_id, 10 ** 9) for box_id in candidate_box_ids), default=0)
        candidates.append({
            "candidate_name": "sequencer_dispatch_shell",
            "box_ids": sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            "line_keys": _line_keys_for_box_ids(snapshot, candidate_box_ids),
            "motif_kinds": ["controller_dispatch", "scheduler_chain", "named_bus"] + (["embedded_patcher"] if embedded_motifs else []),
            "params": {
                "named_bus_names": sorted(
                    motif.get("params", {}).get("name")
                    for motif in named_bus_motifs
                    if motif.get("params", {}).get("name")
                ),
                "has_live_api_layer": bool(live_api_archetypes),
            },
            "evidence": [
                "selector and gate dispatch motifs",
                "timed-dispatch scheduler layer",
                "message named-bus fabric",
            ],
            "normalization_level": "semantic_pattern",
            "first_box_index": first_box_index,
        })

    for candidate in candidates:
        candidate["helper_name"] = candidate.get("candidate_name")
        candidate["exact"] = True
        candidate["helper_call"] = _controller_shell_helper_call(snapshot, candidate)

    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_embedded_ui_shell_candidates(snapshot: dict) -> list[dict]:
    """Return exact-safe embedded-host shell candidates from a snapshot."""
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs", [])
    candidates = []
    relevant_motif_kinds = {
        "named_bus",
        "controller_dispatch",
        "scheduler_chain",
        "state_bundle",
        "live_api_component",
    }

    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        box_id = box.get("id")
        if not box_id:
            continue
        host_kind, target = _embedded_patcher_kind_and_target(box)
        if host_kind not in {"subpatcher", "bpatcher"}:
            continue

        connected_box_ids = _connected_box_ids(snapshot, {box_id})
        connected_line_count = 0
        for line in snapshot.get("lines", []):
            patchline = line.get("patchline", {})
            source_id = patchline.get("source", [None, 0])[0]
            dest_id = patchline.get("destination", [None, 0])[0]
            if source_id == box_id or dest_id == box_id:
                connected_line_count += 1

        candidate_box_ids = {box_id}
        direct_shell_box_ids = set()
        for neighbor_id in connected_box_ids:
            neighbor = boxes_by_id.get(neighbor_id)
            operator = _box_operator(neighbor or {})
            if (
                (neighbor or {}).get("maxclass") == "message"
                or operator in BUS_OPERATOR_SPECS
                or operator in CONTROLLER_DISPATCH_OPERATORS
                or operator in SCHEDULER_OPERATORS
                or _matches_state_bundle_operator(operator or "")
                or operator in LIVE_API_CORE_OPERATORS
                or operator in LIVE_API_HELPER_OPERATORS
            ):
                direct_shell_box_ids.add(neighbor_id)
        candidate_box_ids.update(direct_shell_box_ids)

        attached_motifs = []
        for motif in motifs:
            if motif.get("kind") not in relevant_motif_kinds:
                continue
            motif_box_ids = set(motif.get("box_ids", []))
            if not motif_box_ids or not (motif_box_ids & connected_box_ids):
                continue
            attached_motifs.append(motif)
            candidate_box_ids.update(motif_box_ids)

        line_keys = _line_keys_for_box_ids(snapshot, candidate_box_ids)
        attached_bus_names = sorted({
            motif.get("params", {}).get("name")
            for motif in attached_motifs
            if motif.get("kind") == "named_bus" and motif.get("params", {}).get("name")
        })
        attached_motif_kinds = sorted({motif.get("kind") for motif in attached_motifs})
        attached_control_line_count = sum(
            1
            for line_key in line_keys
            if box_id in {line_key[0], line_key[2]}
        )

        has_nested_patcher = isinstance(box.get("patcher"), dict)
        evidence = [f"embedded host: {host_kind}"]
        if target:
            evidence.append(f"target: {target}")
        if has_nested_patcher:
            evidence.append("embedded patcher payload present")
        if connected_line_count:
            evidence.append(f"connected to top-level patcher with {connected_line_count} line(s)")
        if attached_bus_names:
            evidence.append(f"attached buses: {', '.join(attached_bus_names)}")
        if attached_motif_kinds:
            evidence.append(f"attached motifs: {', '.join(attached_motif_kinds)}")

        candidate = {
            "candidate_name": "embedded_ui_shell_v2",
            "box_ids": sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            "line_keys": line_keys,
            "motif_kinds": ["embedded_patcher"] + attached_motif_kinds,
            "params": {
                "host_kind": host_kind,
                "target": target,
                "has_nested_patcher": has_nested_patcher,
                "connected_line_count": connected_line_count,
                "attached_box_count": max(0, len(candidate_box_ids) - 1),
                "attached_bus_names": attached_bus_names,
                "attached_motif_kinds": attached_motif_kinds,
                "attached_control_line_count": attached_control_line_count,
            },
            "evidence": evidence,
            "normalization_level": "exact",
            "first_box_index": box_indices.get(box_id, 0),
            "helper_name": "embedded_ui_shell_v2",
            "exact": True,
        }
        candidate["helper_call"] = _controller_shell_helper_call(snapshot, candidate)
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["first_box_index"], item["params"].get("host_kind", "")))
    return candidates


def extract_named_bus_router_candidates(snapshot: dict) -> list[dict]:
    """Return exact named-bus router candidates from named-bus motifs."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs", [])
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    networks = {
        (entry.get("name"), bool(entry.get("signal"))): entry
        for entry in _named_bus_networks(
            motifs,
            analysis.get("embedded_patcher_summaries", []),
        )
    }
    candidates = []

    for motif in motifs:
        if motif.get("kind") != "named_bus":
            continue
        params = motif.get("params", {})
        candidate_box_ids = set(motif.get("box_ids", []))
        if not candidate_box_ids:
            continue
        attached_neighbor_ids = []
        for neighbor_id in sorted(
            _connected_box_ids(snapshot, candidate_box_ids),
            key=lambda item: box_indices.get(item, 10 ** 9),
        ):
            if neighbor_id in DEFAULT_AUDIO_IO_BOXES:
                continue
            neighbor = boxes_by_id.get(neighbor_id)
            operator = _box_operator(neighbor or {})
            if (
                (neighbor or {}).get("patcher")
                or (neighbor or {}).get("maxclass") in UI_MAXCLASSES
                or (neighbor or {}).get("maxclass") in {"message", "comment", "number", "flonum"}
                or operator in CONTROLLER_DISPATCH_OPERATORS
            ):
                candidate_box_ids.add(neighbor_id)
                attached_neighbor_ids.append(neighbor_id)
        box_ids = sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9))
        network = networks.get((params.get("name"), bool(params.get("signal"))), {})
        candidate = {
            "candidate_name": "named_bus_router",
            "box_ids": box_ids,
            "line_keys": _line_keys_for_box_ids(snapshot, set(box_ids)),
            "motif_kinds": ["named_bus"],
            "params": {
                "name": params.get("name"),
                "signal": bool(params.get("signal")),
                "sender_count": int(params.get("sender_count", 0)),
                "receiver_count": int(params.get("receiver_count", 0)),
                "forms": copy.deepcopy(params.get("forms", [])),
                "cross_scope": bool(network.get("cross_scope")),
                "scope_count": int(network.get("scope_count", 0)),
                "attached_neighbor_ids": copy.deepcopy(attached_neighbor_ids),
                "attached_neighbor_count": len(attached_neighbor_ids),
            },
            "evidence": [
                f"named bus: {params.get('name')}",
                f"forms: {', '.join(params.get('forms', [])) or 'unknown'}",
            ],
            "normalization_level": "exact",
            "first_box_index": motif.get("first_box_index", 0),
            "helper_name": "named_bus_router",
            "exact": True,
        }
        candidate["helper_call"] = _controller_shell_helper_call(snapshot, candidate)
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["first_box_index"], item["params"].get("name") or ""))
    return candidates


def extract_init_dispatch_chain_candidates(snapshot: dict) -> list[dict]:
    """Return exact init/scheduler dispatch candidates from scheduler motifs."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs", [])
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    candidates = []

    for motif in motifs:
        if motif.get("kind") != "scheduler_chain":
            continue
        archetypes = set(motif.get("params", {}).get("archetypes", []))
        if not ({"init_chain", "deferred_init", "init_fanout"} & archetypes):
            continue
        candidate_box_ids = set(motif.get("box_ids", []))
        for neighbor_id in _connected_box_ids(snapshot, candidate_box_ids):
            neighbor = boxes_by_id.get(neighbor_id)
            operator = _box_operator(neighbor or {})
            if (neighbor or {}).get("maxclass") == "message" or operator in CONTROLLER_DISPATCH_OPERATORS:
                candidate_box_ids.add(neighbor_id)
        candidate = {
            "candidate_name": "init_dispatch_chain",
            "box_ids": sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            "line_keys": _line_keys_for_box_ids(snapshot, candidate_box_ids),
            "motif_kinds": ["scheduler_chain"],
            "params": {
                "archetypes": sorted(archetypes),
                "trigger_shapes": copy.deepcopy(motif.get("params", {}).get("trigger_shapes", [])),
                "timing_texts": copy.deepcopy(motif.get("params", {}).get("timing_texts", [])),
                "load_messages": copy.deepcopy(motif.get("params", {}).get("load_messages", [])),
                "adjacent_message_texts": copy.deepcopy(motif.get("params", {}).get("adjacent_message_texts", [])),
                "downstream_targets": sorted({
                    _box_operator(boxes_by_id[box_id]) or boxes_by_id[box_id].get("maxclass")
                    for box_id in candidate_box_ids
                    if box_id in boxes_by_id and box_id not in motif.get("box_ids", [])
                }),
            },
            "evidence": [
                f"scheduler archetypes: {', '.join(sorted(archetypes))}",
                "loadbang/deferlow/trigger init scaffold",
            ],
            "normalization_level": "exact",
            "first_box_index": motif.get("first_box_index", 0),
            "helper_name": "init_dispatch_chain",
            "exact": True,
        }
        candidate["helper_call"] = _controller_shell_helper_call(snapshot, candidate)
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_state_bundle_router_candidates(snapshot: dict) -> list[dict]:
    """Return semantic grouped state-bundle router candidates."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs", [])
    candidates = []
    for motif in motifs:
        if motif.get("kind") != "state_bundle":
            continue
        candidate = {
            "candidate_name": "state_bundle_router",
            "box_ids": copy.deepcopy(motif.get("box_ids", [])),
            "line_keys": _line_keys_for_box_ids(snapshot, set(motif.get("box_ids", []))),
            "motif_kinds": ["state_bundle"],
            "params": copy.deepcopy(motif.get("params", {})),
            "evidence": [
                "pack/pak/unpack state shuttle",
            ],
            "normalization_level": "semantic_pattern",
            "first_box_index": motif.get("first_box_index", 0),
            "helper_name": None,
            "exact": False,
        }
        candidates.append(candidate)
    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


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


def extract_sample_buffer_candidates(snapshot: dict) -> list[dict]:
    """Return semantic sample-buffer candidates derived from generic motifs."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    candidates = []
    for motif in analysis.get("motifs", []):
        if motif.get("kind") != "sample_buffer_toolchain":
            continue
        archetypes = set(motif.get("params", {}).get("archetypes", []))
        if {"sample_import", "sample_metadata"} & archetypes:
            candidate_name = "sample_file_handling_shell"
        elif "waveform_probe" in archetypes:
            candidate_name = "sample_visualization_shell"
        elif "buffer_playback" in archetypes:
            candidate_name = "sample_playback_shell"
        else:
            candidate_name = "sample_buffer_toolchain"
        evidence = ["sample-buffer processing shell"]
        if archetypes:
            evidence.append("archetypes: %s" % ", ".join(sorted(archetypes)))
        buffer_targets = motif.get("params", {}).get("buffer_targets", [])
        if buffer_targets:
            evidence.append("buffer targets: %s" % ", ".join(buffer_targets))
        candidates.append(
            _motif_semantic_candidate(
                snapshot,
                motif,
                candidate_name=candidate_name,
                evidence=evidence,
            )
        )
    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_gen_processing_candidates(snapshot: dict) -> list[dict]:
    """Return semantic gen~ candidates derived from generic motifs."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    candidates = []
    for motif in analysis.get("motifs", []):
        if motif.get("kind") != "gen_processing_core":
            continue
        archetypes = set(motif.get("params", {}).get("archetypes", []))
        if {"buffered_gen_core", "triggered_gen_core"} <= archetypes:
            candidate_name = "buffered_gen_capture_shell"
        elif "buffered_gen_core" in archetypes:
            candidate_name = "buffered_gen_processing_shell"
        else:
            candidate_name = "gen_processing_core"
        evidence = ["gen~ processing shell"]
        if archetypes:
            evidence.append("archetypes: %s" % ", ".join(sorted(archetypes)))
        buffer_targets = motif.get("params", {}).get("buffer_targets", [])
        if buffer_targets:
            evidence.append("buffer targets: %s" % ", ".join(buffer_targets))
        candidates.append(
            _motif_semantic_candidate(
                snapshot,
                motif,
                candidate_name=candidate_name,
                evidence=evidence,
            )
        )
    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_presentation_widget_cluster_candidates(snapshot: dict) -> list[dict]:
    """Return semantic grouped top-level presentation widget clusters for first-party devices."""
    context = _factory_pack_context(snapshot)
    if context.get("source_lane") != "factory":
        return []

    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    eligible_box_ids = []
    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        box_id = box.get("id")
        rect = _presentation_rect(box)
        if not box_id or not rect or box_id in DEFAULT_AUDIO_IO_BOXES:
            continue
        maxclass = box.get("maxclass")
        if (
            maxclass in UI_MAXCLASSES
            or maxclass in {"comment", "message", "number", "flonum", "toggle", "button", "waveform~"}
        ):
            eligible_box_ids.append(box_id)

    if len(eligible_box_ids) < 4:
        return []

    adjacency = {box_id: set() for box_id in eligible_box_ids}
    eligible_set = set(eligible_box_ids)
    for box_id in eligible_box_ids:
        rect = _presentation_rect(boxes_by_id.get(box_id, {}))
        if rect is None:
            continue
        for other_id in eligible_box_ids:
            if other_id <= box_id:
                continue
            other_rect = _presentation_rect(boxes_by_id.get(other_id, {}))
            if other_rect is None:
                continue
            if _rects_touch(rect, other_rect):
                adjacency[box_id].add(other_id)
                adjacency[other_id].add(box_id)
    for wrapped in snapshot.get("lines", []):
        patchline = wrapped.get("patchline", {})
        source_id = patchline.get("source", [None, 0])[0]
        destination_id = patchline.get("destination", [None, 0])[0]
        if source_id in eligible_set and destination_id in eligible_set:
            adjacency[source_id].add(destination_id)
            adjacency[destination_id].add(source_id)

    clusters = []
    seen = set()
    for seed_id in eligible_box_ids:
        if seed_id in seen:
            continue
        stack = [seed_id]
        component = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(neighbor for neighbor in adjacency[current] if neighbor not in seen)
        if len(component) < 4:
            continue
        component.sort(key=lambda item: box_indices.get(item, 10 ** 9))
        rects = [
            _presentation_rect(boxes_by_id[box_id])
            for box_id in component
            if _presentation_rect(boxes_by_id[box_id]) is not None
        ]
        if not rects:
            continue
        min_x = min(rect[0] for rect in rects)
        min_y = min(rect[1] for rect in rects)
        max_x = max(rect[0] + rect[2] for rect in rects)
        max_y = max(rect[1] + rect[3] for rect in rects)
        maxclasses = sorted({
            str(boxes_by_id[box_id].get("maxclass") or "unknown")
            for box_id in component
        })
        candidate = {
            "candidate_name": "presentation_widget_cluster",
            "box_ids": component,
            "line_keys": _line_keys_for_box_ids(snapshot, set(component)),
            "motif_kinds": ["presentation_widget_cluster"],
            "params": {
                "presentation_bounds": [min_x, min_y, max_x - min_x, max_y - min_y],
                "widget_count": len(component),
                "maxclasses": maxclasses,
            },
            "evidence": [
                "first-party presentation widget cluster",
                f"presentation bounds: [{min_x:.1f}, {min_y:.1f}, {max_x - min_x:.1f}, {max_y - min_y:.1f}]",
            ],
            "normalization_level": "semantic_pattern",
            "first_box_index": box_indices.get(component[0], 0),
            "helper_name": None,
            "exact": False,
        }
        clusters.append(candidate)

    clusters.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return clusters


def extract_poly_shell_candidates(snapshot: dict) -> list[dict]:
    """Return exact `poly~` host shell candidates."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    motifs = analysis.get("motifs", [])
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    candidates = []

    for motif in motifs:
        if motif.get("kind") != "embedded_patcher":
            continue
        params = motif.get("params", {})
        if params.get("host_kind") != "poly":
            continue
        host_box_id = motif.get("box_ids", [None])[0]
        if not host_box_id:
            continue
        connected_box_ids = _connected_box_ids(snapshot, {host_box_id})
        candidate_box_ids = {host_box_id}
        direct_neighbor_ids = []
        attached_bus_names = []
        attached_motif_kinds = []
        for neighbor_id in sorted(connected_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)):
            if neighbor_id in DEFAULT_AUDIO_IO_BOXES:
                continue
            candidate_box_ids.add(neighbor_id)
            direct_neighbor_ids.append(neighbor_id)
        for attached in motifs:
            if attached.get("kind") not in {
                "named_bus",
                "controller_dispatch",
                "scheduler_chain",
                "state_bundle",
            }:
                continue
            attached_ids = set(attached.get("box_ids", []))
            if not attached_ids or not (attached_ids & connected_box_ids):
                continue
            candidate_box_ids.update(attached_ids)
            attached_motif_kinds.append(attached.get("kind"))
            if attached.get("kind") == "named_bus" and attached.get("params", {}).get("name"):
                attached_bus_names.append(attached["params"]["name"])
        for neighbor_id in connected_box_ids:
            neighbor = boxes_by_id.get(neighbor_id)
            operator = _box_operator(neighbor or {})
            if (neighbor or {}).get("maxclass") == "message" or operator in LIVE_API_HELPER_OPERATORS:
                candidate_box_ids.add(neighbor_id)

        candidate = {
            "candidate_name": "poly_shell",
            "box_ids": sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            "line_keys": _line_keys_for_box_ids(snapshot, candidate_box_ids),
            "motif_kinds": ["embedded_patcher"] + sorted(set(attached_motif_kinds)),
            "params": {
                "target": params.get("target"),
                "direct_neighbor_ids": copy.deepcopy(direct_neighbor_ids),
                "direct_neighbor_count": len(direct_neighbor_ids),
                "attached_bus_names": sorted(set(attached_bus_names)),
                "attached_motif_kinds": sorted(set(attached_motif_kinds)),
                "connected_line_count": sum(
                    1
                    for wrapped in snapshot.get("lines", [])
                    if host_box_id in {
                        wrapped.get("patchline", {}).get("source", [None, 0])[0],
                        wrapped.get("patchline", {}).get("destination", [None, 0])[0],
                    }
                ),
            },
            "evidence": [
                "poly~ host shell",
                "attached control and routing layer",
            ],
            "normalization_level": "exact",
            "first_box_index": motif.get("first_box_index", 0),
            "helper_name": "poly_shell",
            "exact": True,
        }
        candidate["helper_call"] = _controller_shell_helper_call(snapshot, candidate)
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def _candidate_helper_boxes(candidate: dict) -> list[dict]:
    return copy.deepcopy(candidate.get("helper_call", {}).get("kwargs", {}).get("boxes", []))


def _candidate_named_bus_texts(candidate: dict) -> list[str]:
    names = []
    for wrapped in _candidate_helper_boxes(candidate):
        box = wrapped.get("box", {})
        text = str(box.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("s ") or text.startswith("r "):
            names.append(text.split(" ", 1)[1].strip())
    return names


def _candidate_bpatcher_names(candidate: dict) -> list[str]:
    names = []
    for wrapped in _candidate_helper_boxes(candidate):
        box = wrapped.get("box", {})
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


def extract_poly_shell_bank_candidates(snapshot: dict) -> list[dict]:
    """Return exact grouped banks of repeated `poly~` editor shells."""
    poly_candidates = extract_poly_shell_candidates(snapshot)
    if len(poly_candidates) < 3:
        return []

    grouped: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
    for candidate in poly_candidates:
        params = candidate.get("params", {})
        signature = (
            str(params.get("target") or ""),
            tuple(_candidate_bpatcher_names(candidate)),
        )
        grouped.setdefault(signature, []).append(candidate)

    bank_candidates = []
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    for (target, bpatcher_names), members in grouped.items():
        if len(members) < 3:
            continue
        member_box_ids = sorted({
            box_id
            for member in members
            for box_id in member.get("box_ids", [])
        }, key=lambda item: box_indices.get(item, 10 ** 9))
        if not member_box_ids:
            continue
        member_line_keys = sorted({
            tuple(line_key)
            for member in members
            for line_key in member.get("line_keys", [])
        })
        bus_names = sorted({
            name
            for member in members
            for name in _candidate_named_bus_texts(member)
        })
        indexed_signatures = _indexed_name_signatures(bus_names)
        indexed_bus_prefix = None
        indexed_bus_indices: list[int] = []
        if indexed_signatures:
            indexed_bus_prefix, indexed_bus_indices = max(
                indexed_signatures.items(),
                key=lambda item: (len(item[1]), item[0]),
            )
        shared_box_ids = sorted({
            box_id
            for box_id in member_box_ids
            if sum(1 for member in members if box_id in set(member.get("box_ids", []))) > 1
        }, key=lambda item: box_indices.get(item, 10 ** 9))
        candidate = {
            "candidate_name": "poly_shell_bank",
            "box_ids": member_box_ids,
            "line_keys": member_line_keys,
            "motif_kinds": ["embedded_patcher"],
            "params": {
                "target": target or None,
                "poly_shell_count": len(members),
                "bpatcher_names": list(bpatcher_names),
                "bus_names": bus_names,
                "indexed_bus_prefix": indexed_bus_prefix,
                "indexed_bus_indices": indexed_bus_indices,
                "shared_box_ids": shared_box_ids,
                "member_first_box_indices": [
                    member.get("first_box_index", 0)
                    for member in members
                ],
            },
            "evidence": [
                "repeated poly~ host shells",
                f"shell count: {len(members)}",
            ] + ([f"target: {target}"] if target else []) + (
                [f"bpatchers: {', '.join(bpatcher_names)}"] if bpatcher_names else []
            ) + (
                [f"indexed bus family: {indexed_bus_prefix}[{', '.join(str(index) for index in indexed_bus_indices)}]"]
                if indexed_bus_prefix and indexed_bus_indices else []
            ),
            "normalization_level": "exact",
            "first_box_index": min(member.get("first_box_index", 10 ** 9) for member in members),
            "helper_name": "poly_shell_bank",
            "exact": True,
        }
        candidate["helper_call"] = _controller_shell_helper_call(snapshot, candidate)
        bank_candidates.append(candidate)

    bank_candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return bank_candidates


def extract_poly_editor_bank_candidates(snapshot: dict) -> list[dict]:
    """Return semantic editor-bank candidates derived from repeated `poly~` shells."""
    candidates = []
    for bank_candidate in extract_poly_shell_bank_candidates(snapshot):
        params = bank_candidate.get("params", {})
        bpatcher_names = params.get("bpatcher_names", [])
        if not bpatcher_names:
            continue
        candidate = copy.deepcopy(bank_candidate)
        candidate["candidate_name"] = "poly_editor_bank"
        candidate["motif_kinds"] = ["embedded_patcher", "poly_shell_bank"]
        candidate["normalization_level"] = "semantic_pattern"
        candidate["helper_name"] = None
        candidate["exact"] = False
        candidate["params"] = {
            "target": params.get("target"),
            "voice_count": params.get("poly_shell_count"),
            "editor_ui_names": copy.deepcopy(bpatcher_names),
            "bus_names": copy.deepcopy(params.get("bus_names", [])),
            "indexed_bus_prefix": params.get("indexed_bus_prefix"),
            "indexed_bus_indices": copy.deepcopy(params.get("indexed_bus_indices", [])),
            "shared_box_ids": copy.deepcopy(params.get("shared_box_ids", [])),
        }
        candidate["evidence"] = [
            "repeated poly~ editor bank",
            f"voice count: {params.get('poly_shell_count')}",
        ] + (
            [f"target: {params.get('target')}"] if params.get("target") else []
        ) + (
            [f"editor UIs: {', '.join(bpatcher_names)}"]
        ) + (
            [f"indexed bus family: {params.get('indexed_bus_prefix')}[{', '.join(str(index) for index in params.get('indexed_bus_indices', []))}]"]
            if params.get("indexed_bus_prefix") and params.get("indexed_bus_indices") else []
        )
        candidate.pop("helper_call", None)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_first_party_api_rig_candidates(snapshot: dict) -> list[dict]:
    """Return grouped API rig candidates for first-party Building Tools devices."""
    context = _factory_pack_context(snapshot)
    if context.get("pack_name") != "M4L Building Tools" or context.get("pack_section") != "API":
        return []

    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    motifs = analysis.get("motifs", [])
    relevant = [entry for entry in motifs if entry.get("kind") == "live_api_component"]
    box_ids = sorted({
        box_id
        for entry in relevant
        for box_id in entry.get("box_ids", [])
    }, key=lambda item: box_indices.get(item, 10 ** 9))
    if not box_ids:
        box_ids = [
            box_id
            for box_id in boxes_by_id
            if box_id not in DEFAULT_AUDIO_IO_BOXES
        ]
    if not box_ids:
        return []

    file_stem = Path(context.get("source_path") or snapshot.get("device", {}).get("name", "")).stem
    api_family = file_stem.replace("Max Api ", "", 1).split()[0] if file_stem.startswith("Max Api ") else file_stem
    return [{
        "candidate_name": "first_party_api_rig",
        "box_ids": box_ids,
        "line_keys": _line_keys_for_box_ids(snapshot, set(box_ids)),
        "motif_kinds": ["live_api_component"] if relevant else copy.deepcopy(analysis.get("motif_kinds", [])),
        "params": {
            "api_family": api_family,
            "pack_name": context.get("pack_name"),
            "pack_section": context.get("pack_section"),
            "pack_subsection": context.get("pack_subsection"),
            "fallback_to_full_device": not bool(relevant),
        },
        "evidence": [
            "first-party M4L Building Tools API device",
            f"API family: {api_family}",
        ] + ([] if relevant else ["no root-level Live API motif; grouped full device shell"]),
        "normalization_level": "semantic_pattern",
        "first_box_index": min(box_indices.get(box_id, 10 ** 9) for box_id in box_ids),
        "helper_name": None,
        "exact": False,
    }]


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


def extract_first_party_abstraction_host_candidates(snapshot: dict) -> list[dict]:
    """Return grouped first-party `M4L.*` abstraction host candidates."""
    context = _factory_pack_context(snapshot)
    if context.get("source_lane") != "factory":
        return []

    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    host_ids = {
        box_id
        for box_id, box in boxes_by_id.items()
        if box.get("maxclass") == "newobj"
        and str(_box_operator(box) or "").startswith("M4L.")
    }
    if not host_ids:
        return []

    relevant_neighbor_maxclasses = UI_MAXCLASSES | {
        "comment",
        "message",
        "number",
        "flonum",
        "toggle",
        "button",
        "scope~",
        "waveform~",
    }
    candidates = []
    visited_host_ids: set[str] = set()

    for host_id in sorted(host_ids, key=lambda item: box_indices.get(item, 10 ** 9)):
        if host_id in visited_host_ids:
            continue

        component_box_ids = {host_id}
        pending_host_ids = [host_id]
        component_host_ids = set()

        while pending_host_ids:
            current_host_id = pending_host_ids.pop()
            if current_host_id in component_host_ids:
                continue
            component_host_ids.add(current_host_id)
            visited_host_ids.add(current_host_id)
            component_box_ids.add(current_host_id)
            connected_ids = _connected_box_ids(snapshot, {current_host_id})
            for neighbor_id in sorted(connected_ids, key=lambda item: box_indices.get(item, 10 ** 9)):
                if neighbor_id in DEFAULT_AUDIO_IO_BOXES:
                    continue
                neighbor = boxes_by_id.get(neighbor_id)
                operator = _box_operator(neighbor or {})
                neighbor_maxclass = (neighbor or {}).get("maxclass")
                if neighbor_id in host_ids:
                    component_box_ids.add(neighbor_id)
                    if neighbor_id not in component_host_ids:
                        pending_host_ids.append(neighbor_id)
                    continue
                if (
                    (neighbor or {}).get("patcher")
                    or neighbor_maxclass in relevant_neighbor_maxclasses
                    or operator in CONTROLLER_DISPATCH_OPERATORS
                    or operator in SCHEDULER_OPERATORS
                    or operator in LIVE_API_CORE_OPERATORS
                    or operator in LIVE_API_HELPER_OPERATORS
                ):
                    component_box_ids.add(neighbor_id)
                    for second_neighbor_id in _connected_box_ids(snapshot, {neighbor_id}):
                        if second_neighbor_id in host_ids and second_neighbor_id not in component_host_ids:
                            component_box_ids.add(second_neighbor_id)
                            pending_host_ids.append(second_neighbor_id)

        component_box_ids = sorted(component_box_ids, key=lambda item: box_indices.get(item, 10 ** 9))
        if not component_box_ids:
            continue

        abstraction_names = sorted({
            str(_box_operator(boxes_by_id[box_id]) or "")
            for box_id in component_host_ids
            if box_id in boxes_by_id
        })
        if not abstraction_names:
            continue
        abstraction_family = _first_party_abstraction_family(abstraction_names)

        attached_box_ids = [box_id for box_id in component_box_ids if box_id not in component_host_ids]
        attached_controls = [
            box_id
            for box_id in attached_box_ids
            if boxes_by_id.get(box_id, {}).get("maxclass") in UI_MAXCLASSES
        ]
        control_varnames = sorted({
            str(boxes_by_id.get(box_id, {}).get("varname") or "")
            for box_id in attached_controls
            if boxes_by_id.get(box_id, {}).get("varname")
        })
        control_maxclasses = sorted({
            str(boxes_by_id.get(box_id, {}).get("maxclass") or "unknown")
            for box_id in attached_controls
        })
        attached_comments = [
            box_id
            for box_id in attached_box_ids
            if boxes_by_id.get(box_id, {}).get("maxclass") == "comment"
        ]
        comment_texts = [
            str(boxes_by_id.get(box_id, {}).get("text") or "").strip()
            for box_id in attached_comments
            if str(boxes_by_id.get(box_id, {}).get("text") or "").strip()
        ][:5]
        attached_controller_ops = sorted({
            _box_operator(boxes_by_id[box_id])
            for box_id in attached_box_ids
            if _box_operator(boxes_by_id.get(box_id, {})) in CONTROLLER_DISPATCH_OPERATORS | SCHEDULER_OPERATORS
        })
        evidence = [
            "first-party abstraction host cluster",
            f"abstractions: {', '.join(abstraction_names)}",
        ]
        if abstraction_family:
            evidence.append(f"family: {abstraction_family}")
        if attached_controls:
            evidence.append(f"attached controls: {len(attached_controls)}")
        if attached_controller_ops:
            evidence.append(f"attached controller ops: {', '.join(attached_controller_ops)}")

        candidates.append({
            "candidate_name": "first_party_abstraction_host",
            "box_ids": component_box_ids,
            "line_keys": _line_keys_for_box_ids(snapshot, set(component_box_ids)),
            "motif_kinds": ["first_party_abstraction_host"],
            "params": {
                "abstraction_names": abstraction_names,
                "primary_abstraction_name": abstraction_names[0],
                "abstraction_family": abstraction_family,
                "host_box_count": len(component_host_ids),
                "attached_box_count": len(attached_box_ids),
                "attached_control_count": len(attached_controls),
                "control_varnames": control_varnames,
                "control_maxclasses": control_maxclasses,
                "attached_comment_count": len(attached_comments),
                "comment_texts": comment_texts,
                "attached_controller_ops": attached_controller_ops,
                "pack_name": context.get("pack_name"),
                "pack_section": context.get("pack_section"),
                "pack_subsection": context.get("pack_subsection"),
            },
            "evidence": evidence,
            "normalization_level": "semantic_pattern",
            "first_box_index": min(box_indices.get(box_id, 10 ** 9) for box_id in component_box_ids),
            "helper_name": None,
            "exact": False,
        })

    candidates.sort(
        key=lambda item: (
            item["first_box_index"],
            item["params"].get("primary_abstraction_name") or "",
        )
    )
    return candidates


def extract_first_party_abstraction_family_candidates(snapshot: dict) -> list[dict]:
    """Return semantic family candidates derived from first-party abstraction hosts."""
    candidates = []
    for host_candidate in extract_first_party_abstraction_host_candidates(snapshot):
        family_name = host_candidate.get("params", {}).get("abstraction_family")
        if not family_name:
            continue
        candidate = copy.deepcopy(host_candidate)
        candidate["candidate_name"] = family_name
        candidate["motif_kinds"] = ["first_party_abstraction_family"]
        candidate["normalization_level"] = "semantic_pattern"
        candidate["helper_name"] = None
        candidate["exact"] = False
        evidence = copy.deepcopy(candidate.get("evidence", []))
        if all(not str(item).startswith("family: ") for item in evidence):
            evidence.append(f"family: {family_name}")
        candidate["evidence"] = evidence
        candidates.append(candidate)
    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_building_block_candidates(snapshot: dict) -> list[dict]:
    """Return grouped building-block candidates for first-party Building Tools devices."""
    context = _factory_pack_context(snapshot)
    if context.get("pack_name") != "M4L Building Tools" or context.get("pack_section") != "Building Blocks":
        return []

    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    box_ids = [
        box_id
        for box_id in boxes_by_id
        if box_id not in DEFAULT_AUDIO_IO_BOXES
    ]
    if not box_ids:
        return []

    return [{
        "candidate_name": "building_block_candidate",
        "box_ids": sorted(box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
        "line_keys": _line_keys_for_box_ids(snapshot, set(box_ids)),
        "motif_kinds": copy.deepcopy((snapshot.get("analysis") or analyze_snapshot(snapshot)).get("motif_kinds", [])),
        "params": {
            "block_name": Path(context.get("source_path") or snapshot.get("device", {}).get("name", "")).stem,
            "pack_name": context.get("pack_name"),
            "pack_section": context.get("pack_section"),
            "pack_subsection": context.get("pack_subsection"),
        },
        "evidence": [
            "first-party M4L Building Tools building block",
        ],
        "normalization_level": "semantic_pattern",
        "first_box_index": min(box_indices.get(box_id, 10 ** 9) for box_id in box_ids),
        "helper_name": None,
        "exact": False,
    }]


def _collect_embedded_patcher_summaries_from_box(box: dict, depth: int = 1) -> list[dict]:
    nested = box.get("patcher")
    if not isinstance(nested, dict):
        return []

    host_kind, target = _embedded_patcher_kind_and_target(box)
    if host_kind is None:
        host_kind = "embedded"

    nested_boxes = nested.get("boxes", [])
    nested_lines = nested.get("lines", [])
    maxclass_counts: Dict[str, int] = {}
    object_name_counts: Dict[str, int] = {}
    direct_child_ids = []

    for wrapped in nested_boxes:
        child_box = wrapped.get("box", {})
        maxclass = child_box.get("maxclass")
        if maxclass:
            maxclass_counts[maxclass] = maxclass_counts.get(maxclass, 0) + 1
        operator = _box_operator(child_box)
        if operator:
            object_name_counts[operator] = object_name_counts.get(operator, 0) + 1
        if isinstance(child_box.get("patcher"), dict):
            child_id = child_box.get("id")
            if child_id:
                direct_child_ids.append(child_id)

    nested_snapshot = _embedded_snapshot_from_patcher_dict(nested)
    nested_parameter_specs = extract_parameter_specs(nested_snapshot)
    nested_patterns = detect_snapshot_patterns(nested_snapshot)
    nested_recipes = detect_snapshot_recipes(nested_snapshot)
    nested_motifs = detect_snapshot_motifs(nested_snapshot)
    nested_live_api_path_targets = []
    nested_live_api_properties = []
    nested_live_api_get_targets = []
    nested_live_api_set_targets = []
    nested_live_api_call_targets = []
    nested_named_bus_entries = []
    for motif in nested_motifs:
        params = motif.get("params", {})
        if motif.get("kind") == "named_bus":
            nested_named_bus_entries.append({
                "name": params.get("name"),
                "signal": bool(params.get("signal")),
                "sender_count": int(params.get("sender_count", 0)),
                "receiver_count": int(params.get("receiver_count", 0)),
                "forms": copy.deepcopy(params.get("forms", [])),
            })
        if motif.get("kind") != "live_api_component":
            continue
        nested_live_api_path_targets.extend(params.get("path_targets", []))
        nested_live_api_properties.extend(params.get("property_names", []))
        nested_live_api_get_targets.extend(params.get("get_targets", []))
        nested_live_api_set_targets.extend(params.get("set_targets", []))
        nested_live_api_call_targets.extend(params.get("call_targets", []))
    nested_live_api_params = {
        "path_targets": sorted(set(nested_live_api_path_targets)),
        "property_names": sorted(set(nested_live_api_properties)),
        "get_targets": sorted(set(nested_live_api_get_targets)),
        "set_targets": sorted(set(nested_live_api_set_targets)),
        "call_targets": sorted(set(nested_live_api_call_targets)),
        "prepend_targets": [],
        "direct_message_texts": [],
        "core_operators": [],
    }

    summary = {
        "host_box_id": box.get("id"),
        "host_kind": host_kind,
        "target": target,
        "depth": depth,
        "box_count": len(nested_boxes),
        "line_count": len(nested_lines),
        "control_count": len(nested_parameter_specs),
        "display_count": sum(
            1
            for wrapped in nested_boxes
            if wrapped.get("box", {}).get("maxclass") in UI_MAXCLASSES
        ),
        "pattern_count": len(nested_patterns),
        "recipe_count": len(nested_recipes),
        "motif_count": len(nested_motifs),
        "pattern_kinds": [entry.get("kind") for entry in nested_patterns],
        "recipe_kinds": [entry.get("kind") for entry in nested_recipes],
        "motif_kinds": [entry.get("kind") for entry in nested_motifs],
        "live_api_path_targets": sorted(set(nested_live_api_path_targets)),
        "live_api_properties": sorted(set(nested_live_api_properties)),
        "live_api_get_targets": sorted(set(nested_live_api_get_targets)),
        "live_api_set_targets": sorted(set(nested_live_api_set_targets)),
        "live_api_call_targets": sorted(set(nested_live_api_call_targets)),
        "live_api_archetypes": _classify_live_api_component_archetypes(nested_live_api_params),
        "named_bus_count": len(nested_named_bus_entries),
        "named_bus_names": sorted({
            entry.get("name")
            for entry in nested_named_bus_entries
            if entry.get("name")
        }),
        "named_bus_entries": nested_named_bus_entries,
        "direct_embedded_child_count": len(direct_child_ids),
        "direct_embedded_child_box_ids": sorted(direct_child_ids),
        "maxclass_counts": {
            name: maxclass_counts[name]
            for name in sorted(maxclass_counts)
        },
        "object_name_counts": {
            name: object_name_counts[name]
            for name in sorted(object_name_counts)
        },
    }

    summaries = [summary]
    for wrapped in nested_boxes:
        child_box = wrapped.get("box", {})
        if isinstance(child_box.get("patcher"), dict):
            summaries.extend(_collect_embedded_patcher_summaries_from_box(child_box, depth + 1))
    return summaries


def _collect_embedded_patcher_summaries(snapshot: dict) -> list[dict]:
    summaries = []
    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        if isinstance(box.get("patcher"), dict):
            summaries.extend(_collect_embedded_patcher_summaries_from_box(box, depth=1))
    return summaries


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


def analyze_snapshot(snapshot: dict) -> dict:
    """Return first-pass structural analysis for a normalized snapshot."""
    boxes = snapshot.get("boxes", [])
    lines = snapshot.get("lines", [])
    support_names = {entry.get("name") for entry in snapshot.get("support_files", [])}

    maxclass_counts: Dict[str, int] = {}
    ui_box_ids = []
    parameter_box_ids = []
    presentation_box_ids = []
    bridge_box_ids = []
    audio_io_box_ids = []
    parameter_specs = []

    for wrapped in boxes:
        box = wrapped.get("box", {})
        box_id = box.get("id")
        maxclass = box.get("maxclass")
        text = str(box.get("text", ""))

        if maxclass:
            maxclass_counts[maxclass] = maxclass_counts.get(maxclass, 0) + 1
        if maxclass in UI_MAXCLASSES and box_id:
            ui_box_ids.append(box_id)
        if (
            maxclass in PARAMETER_MAXCLASSES
            or "saved_attribute_attributes" in box
        ) and box_id:
            parameter_box_ids.append(box_id)
            spec = _parameter_spec_from_box(box)
            if spec is not None:
                parameter_specs.append(spec)
        if box.get("presentation") == 1 or box.get("presentation_rect") is not None:
            if box_id:
                presentation_box_ids.append(box_id)
        if text in ("plugin~", "plugout~") and box_id:
            audio_io_box_ids.append(box_id)
        if box_id and _is_bridge_runtime_box(box):
            bridge_box_ids.append(box_id)

    uses_default_audio_io = _snapshot_uses_default_audio_io(snapshot)
    notes = []
    fidelity = snapshot.get("fidelity", {})
    if not fidelity.get("exact_patcher_dict", False):
        notes.append("Snapshot was reconstructed from bridge payload and may be lossy.")
    if not fidelity.get("has_line_data", False):
        notes.append("No patchline data was available in the source snapshot.")
    if snapshot.get("missing_support_files"):
        notes.append("Some dependency sidecars were referenced but could not be recovered.")
    if "livemcp_bridge_runtime.js" in support_names or bridge_box_ids:
        notes.append("LiveMCP bridge internals were detected in this snapshot.")
    patterns = detect_snapshot_patterns(snapshot)
    recipes = detect_snapshot_recipes(snapshot)
    motifs = detect_snapshot_motifs(snapshot)
    embedded_patcher_summaries = _collect_embedded_patcher_summaries(snapshot)
    if patterns:
        notes.append(f"Recognized {len(patterns)} known m4l-builder helper pattern(s).")
    if recipes:
        notes.append(f"Recognized {len(recipes)} known m4l-builder recipe pattern(s).")
    if motifs:
        notes.append(f"Recognized {len(motifs)} generic Max motif(s).")
    if embedded_patcher_summaries:
        notes.append(
            f"Captured {len(embedded_patcher_summaries)} embedded patcher summary node(s)."
        )

    return {
        "box_count": len(boxes),
        "line_count": len(lines),
        "maxclass_counts": maxclass_counts,
        "ui_box_ids": sorted(ui_box_ids),
        "parameter_box_ids": sorted(parameter_box_ids),
        "presentation_box_ids": sorted(presentation_box_ids),
        "bridge_box_ids": sorted(bridge_box_ids),
        "audio_io_box_ids": sorted(audio_io_box_ids),
        "uses_default_audio_io": uses_default_audio_io,
        "parameter_specs": parameter_specs,
        "patterns": patterns,
        "recipes": recipes,
        "motifs": motifs,
        "embedded_patcher_summaries": embedded_patcher_summaries,
        "notes": notes,
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
    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
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


def _embedded_target_snapshots(snapshot: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in extract_embedded_patcher_snapshots(snapshot):
        target = str(entry.get("target") or "").strip()
        if not target:
            continue
        grouped.setdefault(target, []).append(entry.get("snapshot", {}))
    return grouped


def _snapshot_contains_all_texts(snapshot: dict, required: list[str]) -> bool:
    texts = _snapshot_object_texts(snapshot)
    return all(any(text == candidate for candidate in texts) for text in required)


def extract_behavior_hints(snapshot: dict) -> list[dict]:
    """Return product-level behavioral hints inferred from structure."""
    hints = []
    embedded_by_target = _embedded_target_snapshots(snapshot)
    poly_editor_banks = extract_poly_editor_bank_candidates(snapshot)

    for candidate in poly_editor_banks:
        params = candidate.get("params", {})
        hints.append({
            "name": "multi_lane_mapping_bank",
            "confidence": 0.88,
            "params": {
                "target": params.get("target"),
                "voice_count": params.get("voice_count"),
                "editor_ui_names": copy.deepcopy(params.get("editor_ui_names", [])),
                "indexed_bus_prefix": params.get("indexed_bus_prefix"),
                "indexed_bus_indices": copy.deepcopy(params.get("indexed_bus_indices", [])),
            },
            "evidence": [
                "repeated poly editor bank",
                *(candidate.get("evidence", []) or []),
            ],
        })

    midi_logic_snapshots = embedded_by_target.get("MIDILogic", [])
    if any(
        _snapshot_contains_all_texts(
            nested,
            ["r ---manualmode", "gate", "midiparse", "stripnote", "s ---notebang"],
        )
        for nested in midi_logic_snapshots
    ):
        hints.append({
            "name": "manual_or_midi_trigger_mode",
            "confidence": 0.9,
            "params": {
                "source": "MIDILogic",
                "manual_mode_bus": "---manualmode",
                "trigger_bus": "---notebang",
            },
            "evidence": [
                "manual mode gates MIDI note parsing",
                "MIDILogic emits note-trigger bangs",
            ],
        })

    qm_snapshots = embedded_by_target.get("qm", [])
    if any(
        _snapshot_contains_all_texts(
            nested,
            ["s ---qmap_start", "r ---done_qmap", "s ---qmap", "s ---update_local"],
        )
        for nested in qm_snapshots
    ):
        hints.append({
            "name": "mapping_session_controller",
            "confidence": 0.92,
            "params": {
                "source": "qm",
                "start_bus": "---qmap_start",
                "done_bus": "---done_qmap",
                "update_bus": "---update_local",
            },
            "evidence": [
                "qm subpatch drives q-map start/finish/update state",
                "mapping session can be cleared and reset separately from note triggers",
            ],
        })

    ui_scripting_snapshots = embedded_by_target.get("UiScripting", [])
    if any(
        _snapshot_contains_all_texts(
            nested,
            ["setUiPos $1 $2 $3 $4", "setwidth $1"],
        )
        and any(
            text.startswith("script sendbox global presentation_rect")
            for text in _snapshot_object_texts(nested)
        )
        for nested in ui_scripting_snapshots
    ):
        hints.append({
            "name": "dynamic_panel_relayout",
            "confidence": 0.84,
            "params": {
                "source": "UiScripting",
            },
            "evidence": [
                "UI scripting adjusts presentation geometry dynamically",
                "layout changes are part of interaction flow, not static skinning",
            ],
        })

    hint_names = {hint["name"] for hint in hints}
    if {"multi_lane_mapping_bank", "manual_or_midi_trigger_mode", "mapping_session_controller"} <= hint_names:
        mapping_bank = next(
            (hint for hint in hints if hint["name"] == "multi_lane_mapping_bank"),
            {},
        )
        hints.append({
            "name": "mapped_random_control_device",
            "confidence": 0.93,
            "params": {
                "voice_count": mapping_bank.get("params", {}).get("voice_count"),
                "editor_target": mapping_bank.get("params", {}).get("target"),
            },
            "evidence": [
                "device combines a repeated mapping-editor bank with explicit trigger-mode switching and q-map session control",
            ],
        })

    hints.sort(key=lambda item: (-float(item.get("confidence", 0.0)), item.get("name", "")))
    return hints


def extract_mapping_behavior_traces(snapshot: dict) -> list[dict]:
    """Extract structured behavior traces for mapping/modulation devices."""
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    parameter_specs = {spec.get("box_id"): spec for spec in extract_parameter_specs(snapshot)}
    hints_by_name = {
        entry.get("name"): entry
        for entry in extract_behavior_hints(snapshot)
        if entry.get("name")
    }
    embedded_entries = extract_embedded_patcher_snapshots(snapshot)
    embedded_by_target: dict[str, list[dict]] = {}
    for entry in embedded_entries:
        target = str(entry.get("target") or "").strip()
        if target:
            embedded_by_target.setdefault(target, []).append(entry)

    traces: list[dict] = []

    def add_trace(
        name: str,
        *,
        box_ids: list[str],
        params: dict[str, Any],
        evidence: list[str],
        confidence: float,
    ) -> None:
        ordered_box_ids = sorted(set(box_ids), key=lambda item: box_indices.get(item, 10 ** 9))
        if not ordered_box_ids:
            return
        traces.append({
            "name": name,
            "box_ids": ordered_box_ids,
            "line_keys": _line_keys_for_box_ids(snapshot, set(ordered_box_ids)),
            "params": copy.deepcopy(params),
            "evidence": copy.deepcopy(evidence),
            "confidence": confidence,
            "first_box_index": min((box_indices.get(box_id, 10 ** 9) for box_id in ordered_box_ids), default=0),
        })

    for candidate in extract_poly_editor_bank_candidates(snapshot):
        params = candidate.get("params", {})
        add_trace(
            "modulation_output_bank",
            box_ids=candidate.get("box_ids", []),
            params={
                "output_mode": "mapped_editor_bank",
                "lane_count": params.get("voice_count"),
                "target": params.get("target"),
                "editor_ui_names": copy.deepcopy(params.get("editor_ui_names", [])),
                "indexed_bus_prefix": params.get("indexed_bus_prefix"),
                "indexed_bus_indices": copy.deepcopy(params.get("indexed_bus_indices", [])),
            },
            evidence=[
                "repeated editor bank exposes multiple mapped lanes",
                *(candidate.get("evidence", []) or []),
            ],
            confidence=0.89,
        )

    control_bank_box_ids: list[str] = []
    control_labels: list[str] = []
    for box_id, spec in parameter_specs.items():
        box = boxes_by_id.get(box_id)
        if not box or box.get("maxclass") != "live.dial":
            continue
        annotation = str(box.get("annotation_name") or "").strip()
        shortname = str(spec.get("shortname") or "").strip()
        label = annotation or shortname or str(box.get("varname") or box_id)
        label_lower = label.lower()
        if any(token in label_lower for token in ("output", "randomizable", "macro", "cc")):
            control_bank_box_ids.append(box_id)
            control_labels.append(label)

    if len(control_bank_box_ids) >= 2:
        connected_box_ids = set(control_bank_box_ids)
        frontier = set(control_bank_box_ids)
        for _ in range(3):
            next_frontier: set[str] = set()
            for box_id in frontier:
                next_frontier.update(_connected_box_ids(snapshot, {box_id}))
            next_frontier -= connected_box_ids
            if not next_frontier:
                break
            connected_box_ids.update(next_frontier)
            frontier = next_frontier
        connected_operators = {
            _box_operator(boxes_by_id.get(box_id, {}))
            for box_id in connected_box_ids
            if _box_operator(boxes_by_id.get(box_id, {}))
        }
        output_mode = "exposed_control_bank"
        if "ctlout" in connected_operators:
            output_mode = "midi_cc_output_bank"
        add_trace(
            "modulation_output_bank",
            box_ids=sorted(connected_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            params={
                "output_mode": output_mode,
                "lane_count": len(control_bank_box_ids),
                "control_ids": sorted(control_bank_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
                "control_labels": control_labels,
            },
            evidence=[
                "multiple exposed modulation/macro controls",
                f"output mode: {output_mode}",
            ],
            confidence=0.82,
        )

    trigger_box_ids: set[str] = set()
    trigger_modes: list[str] = []
    trigger_buses: list[str] = []
    if "manual_or_midi_trigger_mode" in hints_by_name:
        trigger_modes.extend(["manual_mode_gate", "midi_note_trigger"])
        trigger_buses.extend([
            hints_by_name["manual_or_midi_trigger_mode"].get("params", {}).get("manual_mode_bus"),
            hints_by_name["manual_or_midi_trigger_mode"].get("params", {}).get("trigger_bus"),
        ])
        for entry in embedded_by_target.get("MIDILogic", []):
            host_box_id = entry.get("host_box_id")
            if host_box_id in boxes_by_id:
                trigger_box_ids.add(host_box_id)
    metro_ids = [
        box_id
        for box_id, box in boxes_by_id.items()
        if _box_operator(box) == "metro"
    ]
    if metro_ids:
        trigger_modes.append("auto_scheduler")
        for box_id in metro_ids:
            trigger_box_ids.add(box_id)
            trigger_box_ids.update(_connected_box_ids(snapshot, {box_id}))
    manual_trigger_ids = [
        box_id
        for box_id, box in boxes_by_id.items()
        if _box_operator(box) == "sel" and str(box.get("text", "")).strip().startswith("sel 1")
    ]
    if manual_trigger_ids:
        trigger_modes.append("manual_button_trigger")
        for box_id in manual_trigger_ids:
            trigger_box_ids.add(box_id)
            trigger_box_ids.update(_connected_box_ids(snapshot, {box_id}))
    if trigger_modes:
        add_trace(
            "trigger_source_cluster",
            box_ids=sorted(trigger_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            params={
                "trigger_modes": sorted(set(mode for mode in trigger_modes if mode)),
                "trigger_buses": sorted(set(bus for bus in trigger_buses if bus)),
            },
            evidence=[
                "device has explicit trigger-source routing",
                *(
                    ["manual vs MIDI trigger gating"]
                    if "manual_or_midi_trigger_mode" in hints_by_name else []
                ),
                *(
                    ["auto scheduler present"]
                    if "auto_scheduler" in trigger_modes else []
                ),
                *(
                    ["manual trigger button/filter present"]
                    if "manual_button_trigger" in trigger_modes else []
                ),
            ],
            confidence=0.86,
        )

    random_box_ids = [
        box_id
        for box_id, box in boxes_by_id.items()
        if _box_operator(box) in {"random", "drunk"}
    ]
    if random_box_ids:
        generation_box_ids = set(random_box_ids)
        scaler_texts: list[str] = []
        random_ranges: list[str] = []
        for box_id in random_box_ids:
            box = boxes_by_id[box_id]
            text = str(box.get("text", "")).strip()
            if text:
                random_ranges.append(text)
            for neighbor_id in _connected_box_ids(snapshot, {box_id}):
                neighbor = boxes_by_id.get(neighbor_id, {})
                operator = _box_operator(neighbor)
                if operator in {"/", "scale", "*", "+", "-", "expr"} or neighbor.get("maxclass") == "message":
                    generation_box_ids.add(neighbor_id)
                    neighbor_text = str(neighbor.get("text", "")).strip()
                    if neighbor_text:
                        scaler_texts.append(neighbor_text)
        add_trace(
            "random_value_generation",
            box_ids=sorted(generation_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            params={
                "generator_operators": sorted({
                    _box_operator(boxes_by_id.get(box_id, {}))
                    for box_id in random_box_ids
                    if _box_operator(boxes_by_id.get(box_id, {}))
                }),
                "generator_texts": random_ranges,
                "scaler_texts": sorted(set(scaler_texts)),
            },
            evidence=[
                "random-value generators are visible in the patcher",
                *([f"generators: {', '.join(random_ranges)}"] if random_ranges else []),
                *([f"shaping/scaling: {', '.join(sorted(set(scaler_texts)))}"] if scaler_texts else []),
            ],
            confidence=0.87,
        )

    periodic_host_ids: set[str] = set()
    periodic_operators: set[str] = set()
    waveform_targets: set[str] = set()
    if embedded_entries:
        periodic_target_names = {
            "sync",
            "timemode",
            "waveform_select",
            "hold",
            "jitter and smooth",
            "line",
            "signalscaling",
            "signalscalingdisplay",
            "toctlout",
        }
        periodic_operator_markers = {
            "phasor~",
            "triangle~",
            "cycle~",
            "noise~",
            "snapshot~",
            "selector~",
            "line",
            "line~",
        }
        for entry in embedded_entries:
            target = str(entry.get("target") or "").strip()
            target_lower = target.lower()
            child = entry.get("snapshot", {})
            child_texts = [
                str(wrapped.get("box", {}).get("text", "")).strip()
                for wrapped in child.get("boxes", [])
                if wrapped.get("box", {}).get("maxclass") == "newobj"
            ]
            matched = False
            for text in child_texts:
                operator = text.split()[0] if text else ""
                if operator in periodic_operator_markers:
                    periodic_operators.add(operator)
                    matched = True
            if target_lower in periodic_target_names:
                waveform_targets.add(target)
                matched = True
            if matched and entry.get("host_box_id") in boxes_by_id:
                periodic_host_ids.add(entry["host_box_id"])
        if periodic_host_ids and periodic_operators and (
            {"phasor~", "triangle~", "cycle~", "noise~", "snapshot~", "line", "line~"} & periodic_operators
        ):
            add_trace(
                "periodic_modulation_core",
                box_ids=sorted(periodic_host_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
                params={
                    "waveform_targets": sorted(waveform_targets),
                    "core_operators": sorted(periodic_operators),
                    "time_sync": any(name.lower() == "sync" for name in waveform_targets),
                    "hold_stage": any(name.lower() == "hold" for name in waveform_targets),
                    "smoothing_stage": any(name.lower() == "jitter and smooth" for name in waveform_targets),
                },
                evidence=[
                    "embedded modulation core exposes periodic waveform or sample-and-hold operators",
                    *([f"embedded modulation stages: {', '.join(sorted(waveform_targets))}"] if waveform_targets else []),
                    *([f"core operators: {', '.join(sorted(periodic_operators))}"] if periodic_operators else []),
                ],
                confidence=0.88,
            )

    parameter_scan_host_ids: set[str] = set()
    parameter_scan_targets: set[str] = set()
    settings_buses: set[str] = set()
    parameter_scan_markers = {
        "get_selected_device_id",
        "selectedid",
        "checkparamavalibility",
        "storesettings",
        "modulation_enabled",
        "activate",
    }
    if embedded_entries:
        for entry in embedded_entries:
            target = str(entry.get("target") or "").strip()
            target_lower = target.lower()
            child = entry.get("snapshot", {})
            child_texts = [
                str(wrapped.get("box", {}).get("text", "")).strip()
                for wrapped in child.get("boxes", [])
                if wrapped.get("box", {}).get("maxclass") == "newobj"
            ]
            joined_texts = " ".join(child_texts)
            matched = target_lower in parameter_scan_markers
            if any(text.startswith(("live.path", "live.object")) for text in child_texts):
                if any(marker in joined_texts for marker in ("route id", "parameters", "is_quantized", "class_name", "Device On")):
                    matched = True
            for text in child_texts:
                if text.startswith(("s ---", "r ---")) and any(
                    marker in text
                    for marker in (
                        "StoreRandSettings",
                        "RecallRandSettings",
                        "AllowEditing",
                        "numOfParams",
                        "bangAllParamsInitialized",
                    )
                ):
                    settings_buses.add(text)
                    matched = True
            if matched and entry.get("host_box_id") in boxes_by_id:
                parameter_scan_host_ids.add(entry["host_box_id"])
                if target:
                    parameter_scan_targets.add(target)
        if parameter_scan_host_ids:
            add_trace(
                "parameter_target_scan",
                box_ids=sorted(parameter_scan_host_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
                params={
                    "scan_targets": sorted(parameter_scan_targets),
                    "settings_buses": sorted(settings_buses),
                    "selected_device_tracking": any(
                        name.lower() in {"selectedid", "get_selected_device_id"}
                        for name in parameter_scan_targets
                    ),
                    "parameter_filtering": any(
                        name.lower() in {"checkparamavalibility", "modulation_enabled"}
                        for name in parameter_scan_targets
                    ),
                },
                evidence=[
                    "embedded subpatchers enumerate devices or parameters for later control",
                    *([f"scan targets: {', '.join(sorted(parameter_scan_targets))}"] if parameter_scan_targets else []),
                    *([f"settings buses: {', '.join(sorted(settings_buses))}"] if settings_buses else []),
                ],
                confidence=0.87,
            )

    if "mapping_session_controller" in hints_by_name:
        lifecycle_box_ids: set[str] = set()
        for entry in embedded_by_target.get("qm", []):
            host_box_id = entry.get("host_box_id")
            if host_box_id in boxes_by_id:
                lifecycle_box_ids.add(host_box_id)
        add_trace(
            "mapping_session_lifecycle",
            box_ids=sorted(lifecycle_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            params={
                "start_bus": hints_by_name["mapping_session_controller"].get("params", {}).get("start_bus"),
                "done_bus": hints_by_name["mapping_session_controller"].get("params", {}).get("done_bus"),
                "update_bus": hints_by_name["mapping_session_controller"].get("params", {}).get("update_bus"),
            },
            evidence=[
                "mapping lifecycle buses are exposed explicitly",
                "q-map session state can start, complete, and refresh separately",
            ],
            confidence=0.9,
        )

    lane_update_params = None
    lane_update_box_ids: set[str] = set()
    if extract_poly_editor_bank_candidates(snapshot):
        editor_candidate = extract_poly_editor_bank_candidates(snapshot)[0]
        lane_update_params = {
            "indexed_bus_prefix": editor_candidate.get("params", {}).get("indexed_bus_prefix"),
            "indexed_bus_indices": copy.deepcopy(editor_candidate.get("params", {}).get("indexed_bus_indices", [])),
            "target": editor_candidate.get("params", {}).get("target"),
        }
        lane_update_box_ids.update(editor_candidate.get("box_ids", []))
    elif control_bank_box_ids:
        lane_update_params = {
            "control_ids": sorted(control_bank_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            "target": "exposed_controls",
        }
        lane_update_box_ids.update(control_bank_box_ids)
    if lane_update_params:
        add_trace(
            "lane_update_paths",
            box_ids=sorted(lane_update_box_ids, key=lambda item: box_indices.get(item, 10 ** 9)),
            params=lane_update_params,
            evidence=[
                "per-lane outputs or buses are exposed",
            ],
            confidence=0.81,
        )

    hidden_mapping_sidecars = []
    for entry in snapshot.get("missing_support_files", []):
        if isinstance(entry, dict):
            name = str(entry.get("name", "")).strip()
        else:
            name = str(entry).strip()
        if name and any(token in name.lower() for token in ("map", "transform", "moveui", "rndgen")):
            hidden_mapping_sidecars.append(name)
    if hidden_mapping_sidecars and (
        "mapped_random_control_device" in hints_by_name
        or "mapping_session_controller" in hints_by_name
    ):
        add_trace(
            "hidden_mapping_engine",
            box_ids=sorted(
                {
                    entry.get("host_box_id")
                    for target in ("MIDILogic", "qm", "UiScripting")
                    for entry in embedded_by_target.get(target, [])
                    if entry.get("host_box_id") in boxes_by_id
                },
                key=lambda item: box_indices.get(item, 10 ** 9),
            ),
            params={
                "missing_support_files": hidden_mapping_sidecars,
            },
            evidence=[
                "part of the mapping/random engine lives in unresolved sidecars",
                "value generation and shaping are not fully visible from the root patcher alone",
            ],
            confidence=0.78,
        )

    traces.sort(key=lambda item: (item["first_box_index"], item["name"]))
    return traces


def extract_mapping_semantic_candidates(snapshot: dict) -> list[dict]:
    """Return higher-level semantic mapping/modulation candidates."""
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    traces = extract_mapping_behavior_traces(snapshot)
    trace_by_name: dict[str, list[dict]] = {}
    for trace in traces:
        trace_by_name.setdefault(trace.get("name", ""), []).append(trace)
    hints_by_name = {
        entry.get("name"): entry
        for entry in extract_behavior_hints(snapshot)
        if entry.get("name")
    }
    workflow_candidates = extract_mapping_workflow_candidates(snapshot)
    candidates: list[dict] = []
    control_labels_lower: set[str] = set()
    for spec in extract_parameter_specs(snapshot):
        box = boxes_by_id.get(spec.get("box_id"), {})
        for label in (
            box.get("annotation_name"),
            spec.get("shortname"),
            spec.get("varname"),
            box.get("varname"),
        ):
            if label:
                control_labels_lower.add(str(label).strip().lower())

    output_traces = trace_by_name.get("modulation_output_bank", [])
    trigger_traces = trace_by_name.get("trigger_source_cluster", [])
    random_traces = trace_by_name.get("random_value_generation", [])
    lifecycle_traces = trace_by_name.get("mapping_session_lifecycle", [])
    hidden_engine_traces = trace_by_name.get("hidden_mapping_engine", [])
    periodic_core_traces = trace_by_name.get("periodic_modulation_core", [])
    parameter_scan_traces = trace_by_name.get("parameter_target_scan", [])

    def add_candidate(
        candidate_name: str,
        *,
        box_ids: set[str],
        params: dict[str, Any],
        evidence: list[str],
        priority: int,
    ) -> None:
        ordered_box_ids = sorted(box_ids, key=lambda item: box_indices.get(item, 10 ** 9))
        if not ordered_box_ids:
            return
        candidates.append({
            "candidate_name": candidate_name,
            "box_ids": ordered_box_ids,
            "line_keys": _line_keys_for_box_ids(snapshot, set(ordered_box_ids)),
            "motif_kinds": ["mapping_behavior"],
            "params": copy.deepcopy(params),
            "evidence": copy.deepcopy(evidence),
            "normalization_level": "semantic_pattern",
            "first_box_index": min((box_indices.get(box_id, 10 ** 9) for box_id in ordered_box_ids), default=0),
            "helper_name": None,
            "exact": False,
            "_priority": priority,
        })

    for output_trace in output_traces:
        params = output_trace.get("params", {})
        if (
            params.get("output_mode") == "mapped_editor_bank"
            and not trigger_traces
            and not lifecycle_traces
            and "mapped_random_control_device" not in hints_by_name
        ):
            continue
        add_candidate(
            "mapped_modulation_bank",
            box_ids=set(output_trace.get("box_ids", [])),
            params={
                "lane_count": params.get("lane_count"),
                "output_mode": params.get("output_mode"),
                "target": params.get("target"),
                "control_labels": copy.deepcopy(params.get("control_labels", [])),
                "indexed_bus_prefix": params.get("indexed_bus_prefix"),
                "indexed_bus_indices": copy.deepcopy(params.get("indexed_bus_indices", [])),
            },
            evidence=[
                "multiple modulation lanes are exposed as one bank",
                *output_trace.get("evidence", []),
            ],
            priority=3,
        )

    for output_trace in output_traces:
        if not trigger_traces:
            continue
        if not random_traces and "mapped_random_control_device" not in hints_by_name:
            continue
        box_ids = set(output_trace.get("box_ids", []))
        for trace in trigger_traces + random_traces + hidden_engine_traces:
            box_ids.update(trace.get("box_ids", []))
        params = {
            "lane_count": output_trace.get("params", {}).get("lane_count"),
            "output_mode": output_trace.get("params", {}).get("output_mode"),
            "trigger_modes": sorted({
                mode
                for trace in trigger_traces
                for mode in trace.get("params", {}).get("trigger_modes", [])
            }),
            "random_engine_visible": bool(random_traces),
            "random_engine_hidden": bool(hidden_engine_traces),
        }
        add_candidate(
            "random_modulation_mapper",
            box_ids=box_ids,
            params=params,
            evidence=[
                "modulation bank is driven by explicit trigger sources and randomization logic",
                *(
                    ["visible random-value generation is present"]
                    if random_traces else []
                ),
                *(
                    ["randomization behavior is inferred from workflow + missing sidecars"]
                    if not random_traces and "mapped_random_control_device" in hints_by_name else []
                ),
            ],
            priority=2,
        )

    for workflow_candidate in workflow_candidates:
        if not lifecycle_traces or not trigger_traces:
            continue
        box_ids = set(workflow_candidate.get("box_ids", []))
        for trace in lifecycle_traces + trigger_traces:
            box_ids.update(trace.get("box_ids", []))
        if random_traces or hidden_engine_traces:
            for trace in random_traces + hidden_engine_traces:
                box_ids.update(trace.get("box_ids", []))
        add_candidate(
            "triggered_parameter_mapper",
            box_ids=box_ids,
            params={
                "voice_count": workflow_candidate.get("params", {}).get("voice_count"),
                "editor_target": workflow_candidate.get("params", {}).get("editor_target"),
                "trigger_modes": sorted({
                    mode
                    for trace in trigger_traces
                    for mode in trace.get("params", {}).get("trigger_modes", [])
                }),
                "mapping_start_bus": workflow_candidate.get("params", {}).get("mapping_start_bus"),
                "mapping_done_bus": workflow_candidate.get("params", {}).get("mapping_done_bus"),
                "mapping_update_bus": workflow_candidate.get("params", {}).get("mapping_update_bus"),
            },
            evidence=[
                "mapping workflow is explicitly trigger-driven and session-managed",
                *workflow_candidate.get("evidence", []),
            ],
            priority=1,
        )

    for periodic_trace in periodic_core_traces:
        if parameter_scan_traces:
            continue
        params = periodic_trace.get("params", {})
        waveform_targets = {str(name).lower() for name in params.get("waveform_targets", [])}
        core_operators = set(params.get("core_operators", []))
        has_rate_control = any(
            any(fragment in label for fragment in ("rate", "time mode", "sync", "bpm"))
            for label in control_labels_lower
        )
        lfo_control_axes = 0
        if any(any(fragment in label for fragment in ("shape", "waveform")) for label in control_labels_lower):
            lfo_control_axes += 1
        if any("depth" in label for label in control_labels_lower):
            lfo_control_axes += 1
        if any("phase" in label for label in control_labels_lower):
            lfo_control_axes += 1
        if any("hold" in label for label in control_labels_lower):
            lfo_control_axes += 1
        if any(any(fragment in label for fragment in ("jitter", "smooth")) for label in control_labels_lower):
            lfo_control_axes += 1
        if any("offset" in label for label in control_labels_lower):
            lfo_control_axes += 1
        lfo_shell_signature = bool(
            {"waveform_select", "hold", "jitter and smooth", "signalscaling", "signalscalingdisplay"} & waveform_targets
            or params.get("hold_stage")
            or params.get("smoothing_stage")
        )
        lfo_signature = (
            has_rate_control
            and lfo_shell_signature
            and (
                lfo_control_axes >= 2
                or lfo_control_axes >= 1
            )
        )
        if not lfo_signature:
            continue
        box_ids = set(periodic_trace.get("box_ids", []))
        for trace in trigger_traces:
            box_ids.update(trace.get("box_ids", []))
        add_candidate(
            "lfo_modulation_source",
            box_ids=box_ids,
            params={
                "waveform_targets": copy.deepcopy(params.get("waveform_targets", [])),
                "core_operators": copy.deepcopy(params.get("core_operators", [])),
                "time_sync": params.get("time_sync"),
                "hold_stage": params.get("hold_stage"),
                "smoothing_stage": params.get("smoothing_stage"),
                "trigger_modes": sorted({
                    mode
                    for trace in trigger_traces
                    for mode in trace.get("params", {}).get("trigger_modes", [])
                }),
            },
            evidence=[
                "periodic modulation core is visible in embedded waveform/time subpatchers",
                *periodic_trace.get("evidence", []),
            ],
            priority=2,
        )

    for scan_trace in parameter_scan_traces:
        if not trigger_traces:
            continue
        params = scan_trace.get("params", {})
        if not (
            params.get("selected_device_tracking")
            or params.get("parameter_filtering")
            or params.get("settings_buses")
        ):
            continue
        box_ids = set(scan_trace.get("box_ids", []))
        for trace in trigger_traces + random_traces + hidden_engine_traces:
            box_ids.update(trace.get("box_ids", []))
        add_candidate(
            "device_parameter_randomizer",
            box_ids=box_ids,
            params={
                "scan_targets": copy.deepcopy(params.get("scan_targets", [])),
                "settings_buses": copy.deepcopy(params.get("settings_buses", [])),
                "selected_device_tracking": params.get("selected_device_tracking"),
                "parameter_filtering": params.get("parameter_filtering"),
                "trigger_modes": sorted({
                    mode
                    for trace in trigger_traces
                    for mode in trace.get("params", {}).get("trigger_modes", [])
                }),
                "random_engine_visible": bool(random_traces),
                "random_engine_hidden": bool(hidden_engine_traces),
            },
            evidence=[
                "device scans selected-device parameters and applies triggered randomization/control logic",
                *scan_trace.get("evidence", []),
            ],
            priority=2,
        )

    candidates.sort(key=lambda item: (item["first_box_index"], item.get("_priority", 99), item["candidate_name"]))
    for candidate in candidates:
        candidate.pop("_priority", None)
    return candidates


def extract_mapping_workflow_candidates(snapshot: dict) -> list[dict]:
    """Return semantic mapping-workflow candidates derived from behavior hints."""
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    hint_by_name = {
        entry.get("name"): entry
        for entry in extract_behavior_hints(snapshot)
        if entry.get("name")
    }
    if "mapped_random_control_device" not in hint_by_name:
        return []

    embedded_entries_by_target: dict[str, list[dict]] = {}
    for entry in extract_embedded_patcher_snapshots(snapshot):
        target = str(entry.get("target") or "").strip()
        if target:
            embedded_entries_by_target.setdefault(target, []).append(entry)

    required_targets = ("MIDILogic", "qm")
    if any(not embedded_entries_by_target.get(target) for target in required_targets):
        return []

    candidates = []
    mapping_hint = hint_by_name.get("multi_lane_mapping_bank", {})
    trigger_hint = hint_by_name.get("manual_or_midi_trigger_mode", {})
    session_hint = hint_by_name.get("mapping_session_controller", {})
    relayout_hint = hint_by_name.get("dynamic_panel_relayout", {})

    for editor_candidate in extract_poly_editor_bank_candidates(snapshot):
        candidate_box_ids = set(editor_candidate.get("box_ids", []))
        attached_targets = []
        for target in required_targets:
            for entry in embedded_entries_by_target.get(target, []):
                host_box_id = entry.get("host_box_id")
                if host_box_id in boxes_by_id:
                    candidate_box_ids.add(host_box_id)
            attached_targets.append(target)
        if relayout_hint and embedded_entries_by_target.get("UiScripting"):
            for entry in embedded_entries_by_target.get("UiScripting", []):
                host_box_id = entry.get("host_box_id")
                if host_box_id in boxes_by_id:
                    candidate_box_ids.add(host_box_id)
            attached_targets.append("UiScripting")

        ordered_box_ids = sorted(candidate_box_ids, key=lambda item: box_indices.get(item, 10 ** 9))
        candidate_params = {
            "target": editor_candidate.get("params", {}).get("target"),
            "voice_count": editor_candidate.get("params", {}).get("voice_count"),
            "editor_ui_names": copy.deepcopy(editor_candidate.get("params", {}).get("editor_ui_names", [])),
            "indexed_bus_prefix": editor_candidate.get("params", {}).get("indexed_bus_prefix"),
            "indexed_bus_indices": copy.deepcopy(editor_candidate.get("params", {}).get("indexed_bus_indices", [])),
            "manual_mode_bus": trigger_hint.get("params", {}).get("manual_mode_bus"),
            "trigger_bus": trigger_hint.get("params", {}).get("trigger_bus"),
            "mapping_start_bus": session_hint.get("params", {}).get("start_bus"),
            "mapping_done_bus": session_hint.get("params", {}).get("done_bus"),
            "mapping_update_bus": session_hint.get("params", {}).get("update_bus"),
            "editor_target": mapping_hint.get("params", {}).get("target"),
            "attached_targets": attached_targets,
            "dynamic_panel_relayout": bool(relayout_hint),
        }
        evidence = [
            "mapped random-control workflow",
            "repeated mapping editor bank",
            "manual and MIDI trigger paths",
            "explicit q-map session control",
        ]
        if candidate_params.get("voice_count"):
            evidence.append(f"voice count: {candidate_params['voice_count']}")
        if candidate_params.get("editor_target"):
            evidence.append(f"editor target: {candidate_params['editor_target']}")
        if candidate_params.get("indexed_bus_prefix") and candidate_params.get("indexed_bus_indices"):
            evidence.append(
                "indexed bus family: %s[%s]"
                % (
                    candidate_params["indexed_bus_prefix"],
                    ", ".join(str(index) for index in candidate_params["indexed_bus_indices"]),
                )
            )
        if relayout_hint:
            evidence.append("includes dynamic panel relayout shell")
        candidates.append({
            "candidate_name": "mapping_workflow_shell",
            "box_ids": ordered_box_ids,
            "line_keys": _line_keys_for_box_ids(snapshot, candidate_box_ids),
            "motif_kinds": ["poly_shell_bank", "embedded_patcher"],
            "params": candidate_params,
            "evidence": evidence,
            "normalization_level": "semantic_pattern",
            "first_box_index": min((box_indices.get(box_id, 10 ** 9) for box_id in ordered_box_ids), default=0),
            "helper_name": None,
            "exact": False,
        })

    candidates.sort(key=lambda item: (item["first_box_index"], item["candidate_name"]))
    return candidates


def extract_snapshot_knowledge(snapshot: dict) -> dict:
    """Extract a structured knowledge manifest from a normalized snapshot."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    parameter_specs = {
        spec["box_id"]: copy.deepcopy(spec)
        for spec in analysis.get("parameter_specs", [])
        if spec.get("box_id")
    }
    control_box_ids = set(analysis.get("parameter_box_ids", []))
    controls = []
    displays = []
    display_groups = {
        "labels": [],
        "monitors": [],
        "custom_ui": [],
        "embedded_patchers": [],
        "widgets": [],
    }

    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        box_id = box.get("id")
        if not box_id:
            continue

        rect = copy.deepcopy(box.get("presentation_rect") or box.get("patching_rect"))
        if box_id in control_box_ids:
            spec = parameter_specs.get(box_id, {})
            controls.append({
                "box_id": box_id,
                "varname": box.get("varname"),
                "maxclass": box.get("maxclass"),
                "annotation_name": box.get("annotation_name"),
                "shortname": spec.get("shortname"),
                "parameter_type": spec.get("parameter_type"),
                "min": spec.get("min"),
                "max": spec.get("max"),
                "initial": spec.get("initial"),
                "unitstyle": spec.get("unitstyle"),
                "enum": copy.deepcopy(spec.get("enum")),
                "rect": rect,
                "presentation": box.get("presentation") == 1 or box.get("presentation_rect") is not None,
            })
            continue

        if box.get("maxclass") in UI_MAXCLASSES:
            display = {
                "box_id": box_id,
                "maxclass": box.get("maxclass"),
                "role": _ui_role(box),
                "varname": box.get("varname"),
                "text": box.get("text"),
                "rect": rect,
                "presentation": box.get("presentation") == 1 or box.get("presentation_rect") is not None,
            }
            displays.append(display)
            role = display["role"]
            if role == "label":
                display_groups["labels"].append(copy.deepcopy(display))
            elif role == "monitor":
                display_groups["monitors"].append(copy.deepcopy(display))
            elif role == "custom_ui":
                display_groups["custom_ui"].append(copy.deepcopy(display))
            elif role == "embedded_patcher":
                display_groups["embedded_patchers"].append(copy.deepcopy(display))
            else:
                display_groups["widgets"].append(copy.deepcopy(display))

    patterns = []
    for pattern in analysis.get("patterns", []):
        helper = pattern.get("helper") or {}
        patterns.append({
            "kind": pattern.get("kind"),
            "prefix": pattern.get("prefix"),
            "params": copy.deepcopy(pattern.get("params", {})),
            "helperizable": pattern.get("helperizable", False),
            "helper_name": helper.get("name"),
        })

    recipes = []
    for recipe in analysis.get("recipes", []):
        recipe_meta = recipe.get("recipe") or {}
        recipes.append({
            "kind": recipe.get("kind"),
            "prefix": recipe.get("prefix"),
            "params": copy.deepcopy(recipe.get("params", {})),
            "recipeizable": recipe.get("recipeizable", False),
            "recipe_name": recipe_meta.get("name"),
        })
    motifs = [
        {
            "kind": motif.get("kind"),
            "params": copy.deepcopy(motif.get("params", {})),
            "box_ids": copy.deepcopy(motif.get("box_ids", [])),
        }
        for motif in analysis.get("motifs", [])
    ]
    live_api_normalization_candidates = extract_live_api_normalization_candidates(snapshot)
    controller_shell_candidates = extract_controller_shell_candidates(snapshot)
    embedded_ui_shell_candidates = extract_embedded_ui_shell_candidates(snapshot)
    named_bus_router_candidates = extract_named_bus_router_candidates(snapshot)
    init_dispatch_chain_candidates = extract_init_dispatch_chain_candidates(snapshot)
    state_bundle_router_candidates = extract_state_bundle_router_candidates(snapshot)
    sample_buffer_candidates = extract_sample_buffer_candidates(snapshot)
    gen_processing_candidates = extract_gen_processing_candidates(snapshot)
    presentation_widget_cluster_candidates = extract_presentation_widget_cluster_candidates(snapshot)
    poly_shell_candidates = extract_poly_shell_candidates(snapshot)
    poly_shell_bank_candidates = extract_poly_shell_bank_candidates(snapshot)
    poly_editor_bank_candidates = extract_poly_editor_bank_candidates(snapshot)
    behavior_hints = extract_behavior_hints(snapshot)
    mapping_behavior_traces = extract_mapping_behavior_traces(snapshot)
    mapping_semantic_candidates = extract_mapping_semantic_candidates(snapshot)
    mapping_workflow_candidates = extract_mapping_workflow_candidates(snapshot)
    first_party_api_rig_candidates = extract_first_party_api_rig_candidates(snapshot)
    first_party_abstraction_host_candidates = extract_first_party_abstraction_host_candidates(snapshot)
    first_party_abstraction_family_candidates = extract_first_party_abstraction_family_candidates(snapshot)
    building_block_candidates = extract_building_block_candidates(snapshot)
    live_api_helpers = [
        copy.deepcopy(entry)
        for entry in live_api_normalization_candidates
        if entry.get("exact")
    ]
    live_api_helper_opportunities = [
        copy.deepcopy(entry)
        for entry in live_api_normalization_candidates
        if not entry.get("exact")
    ]
    embedded_patchers = [
        {
            "host_box_id": entry.get("host_box_id"),
            "host_kind": entry.get("host_kind"),
            "target": entry.get("target"),
            "depth": entry.get("depth"),
            "box_count": entry.get("box_count"),
            "line_count": entry.get("line_count"),
            "control_count": entry.get("control_count", 0),
            "display_count": entry.get("display_count", 0),
            "pattern_count": entry.get("pattern_count", 0),
            "recipe_count": entry.get("recipe_count", 0),
            "motif_count": entry.get("motif_count", 0),
            "pattern_kinds": copy.deepcopy(entry.get("pattern_kinds", [])),
            "recipe_kinds": copy.deepcopy(entry.get("recipe_kinds", [])),
            "motif_kinds": copy.deepcopy(entry.get("motif_kinds", [])),
            "live_api_path_targets": copy.deepcopy(entry.get("live_api_path_targets", [])),
            "live_api_properties": copy.deepcopy(entry.get("live_api_properties", [])),
            "live_api_get_targets": copy.deepcopy(entry.get("live_api_get_targets", [])),
            "live_api_set_targets": copy.deepcopy(entry.get("live_api_set_targets", [])),
            "live_api_call_targets": copy.deepcopy(entry.get("live_api_call_targets", [])),
            "live_api_archetypes": copy.deepcopy(entry.get("live_api_archetypes", [])),
            "named_bus_count": entry.get("named_bus_count", 0),
            "named_bus_names": copy.deepcopy(entry.get("named_bus_names", [])),
            "named_bus_entries": copy.deepcopy(entry.get("named_bus_entries", [])),
            "direct_embedded_child_count": entry.get("direct_embedded_child_count", 0),
            "direct_embedded_child_box_ids": copy.deepcopy(entry.get("direct_embedded_child_box_ids", [])),
            "maxclass_counts": copy.deepcopy(entry.get("maxclass_counts", {})),
            "object_name_counts": copy.deepcopy(entry.get("object_name_counts", {})),
        }
        for entry in analysis.get("embedded_patcher_summaries", [])
    ]
    named_bus_networks = _named_bus_networks(motifs, embedded_patchers)

    bridge_support_files = [
        support.get("name")
        for support in snapshot.get("support_files", [])
        if "livemcp_bridge" in str(support.get("name", ""))
    ]

    sidecars = [
        {
            "name": support.get("name"),
            "type": support.get("type", "TEXT"),
            "kind": _support_file_kind(str(support.get("name", ""))),
        }
        for support in snapshot.get("support_files", [])
    ]
    fidelity = copy.deepcopy(snapshot.get("fidelity", {}))
    lossiness = {
        "exact_patcher_dict": fidelity.get("exact_patcher_dict", False),
        "has_line_data": fidelity.get("has_line_data", False),
        "rebuild_strategy": fidelity.get("rebuild_strategy"),
        "source_kind": snapshot.get("source", {}).get("kind"),
        "missing_support_files": copy.deepcopy(snapshot.get("missing_support_files", [])),
        "bridge_reconstructed": snapshot.get("source", {}).get("kind") == "bridge",
        "notes": [],
    }
    if not lossiness["exact_patcher_dict"]:
        lossiness["notes"].append("Snapshot was reconstructed rather than read from an exact patcher dict.")
    if not lossiness["has_line_data"]:
        lossiness["notes"].append("Patchline data was unavailable, so wiring may be incomplete.")
    if lossiness["missing_support_files"]:
        lossiness["notes"].append("Some dependency sidecars were referenced but could not be recovered.")
    if lossiness["bridge_reconstructed"]:
        lossiness["notes"].append("Snapshot originated from a LiveMCP bridge payload, not a raw .amxd file.")

    source_context = _factory_pack_context(snapshot)

    return {
        "device": copy.deepcopy(snapshot.get("device", {})),
        "source": {
            "kind": snapshot.get("source", {}).get("kind"),
            "path": _snapshot_source_path(snapshot),
            "source_lane": source_context.get("source_lane"),
            "pack_name": source_context.get("pack_name"),
            "pack_section": source_context.get("pack_section"),
            "pack_subsection": source_context.get("pack_subsection"),
            "pack_section_path": source_context.get("pack_section_path"),
        },
        "summary": {
            "control_count": len(controls),
            "display_count": len(displays),
            "display_role_counts": {
                "labels": len(display_groups["labels"]),
                "monitors": len(display_groups["monitors"]),
                "custom_ui": len(display_groups["custom_ui"]),
                "embedded_patchers": len(display_groups["embedded_patchers"]),
                "widgets": len(display_groups["widgets"]),
            },
            "pattern_count": len(patterns),
            "recipe_count": len(recipes),
            "motif_count": len(motifs),
            "named_bus_network_count": len(named_bus_networks),
            "cross_scope_named_bus_network_count": sum(
                1 for entry in named_bus_networks if entry.get("cross_scope")
            ),
            "live_api_helper_count": len(live_api_helpers),
            "live_api_helper_opportunity_count": len(live_api_helper_opportunities),
            "live_api_normalization_candidate_count": len(live_api_normalization_candidates),
            "controller_shell_candidate_count": len(controller_shell_candidates),
            "embedded_ui_shell_candidate_count": len(embedded_ui_shell_candidates),
            "named_bus_router_candidate_count": len(named_bus_router_candidates),
            "init_dispatch_chain_candidate_count": len(init_dispatch_chain_candidates),
            "state_bundle_router_candidate_count": len(state_bundle_router_candidates),
            "sample_buffer_candidate_count": len(sample_buffer_candidates),
            "gen_processing_candidate_count": len(gen_processing_candidates),
            "presentation_widget_cluster_candidate_count": len(presentation_widget_cluster_candidates),
            "poly_shell_candidate_count": len(poly_shell_candidates),
            "poly_shell_bank_candidate_count": len(poly_shell_bank_candidates),
            "poly_editor_bank_candidate_count": len(poly_editor_bank_candidates),
            "behavior_hint_count": len(behavior_hints),
            "mapping_behavior_trace_count": len(mapping_behavior_traces),
            "mapping_semantic_candidate_count": len(mapping_semantic_candidates),
            "mapping_workflow_candidate_count": len(mapping_workflow_candidates),
            "first_party_api_rig_candidate_count": len(first_party_api_rig_candidates),
            "first_party_abstraction_host_candidate_count": len(first_party_abstraction_host_candidates),
            "first_party_abstraction_family_candidate_count": len(first_party_abstraction_family_candidates),
            "building_block_candidate_count": len(building_block_candidates),
            "embedded_patcher_count": len(embedded_patchers),
            "embedded_pattern_count": sum(entry.get("pattern_count", 0) for entry in embedded_patchers),
            "embedded_recipe_count": sum(entry.get("recipe_count", 0) for entry in embedded_patchers),
            "embedded_motif_count": sum(entry.get("motif_count", 0) for entry in embedded_patchers),
            "sidecar_count": len(sidecars),
            "bridge_enabled": bool(analysis.get("bridge_box_ids") or bridge_support_files),
            "lossy": any(
                (
                    not lossiness["exact_patcher_dict"],
                    not lossiness["has_line_data"],
                    bool(lossiness["missing_support_files"]),
                )
            ),
        },
        "controls": controls,
        "displays": displays,
        "display_groups": display_groups,
        "patterns": patterns,
        "recipes": recipes,
        "motifs": motifs,
        "named_bus_networks": named_bus_networks,
        "live_api_helpers": live_api_helpers,
        "live_api_helper_opportunities": live_api_helper_opportunities,
        "live_api_normalization_candidates": live_api_normalization_candidates,
        "controller_shell_candidates": controller_shell_candidates,
        "embedded_ui_shell_candidates": embedded_ui_shell_candidates,
        "named_bus_router_candidates": named_bus_router_candidates,
        "init_dispatch_chain_candidates": init_dispatch_chain_candidates,
        "state_bundle_router_candidates": state_bundle_router_candidates,
        "sample_buffer_candidates": sample_buffer_candidates,
        "gen_processing_candidates": gen_processing_candidates,
        "presentation_widget_cluster_candidates": presentation_widget_cluster_candidates,
        "poly_shell_candidates": poly_shell_candidates,
        "poly_shell_bank_candidates": poly_shell_bank_candidates,
        "poly_editor_bank_candidates": poly_editor_bank_candidates,
        "behavior_hints": behavior_hints,
        "mapping_behavior_traces": mapping_behavior_traces,
        "mapping_semantic_candidates": mapping_semantic_candidates,
        "mapping_workflow_candidates": mapping_workflow_candidates,
        "first_party_api_rig_candidates": first_party_api_rig_candidates,
        "first_party_abstraction_host_candidates": first_party_abstraction_host_candidates,
        "first_party_abstraction_family_candidates": first_party_abstraction_family_candidates,
        "building_block_candidates": building_block_candidates,
        "embedded_patchers": embedded_patchers,
        "sidecars": sidecars,
        "audio_routing": {
            "uses_default_audio_io": analysis.get("uses_default_audio_io", False),
            "audio_io_box_ids": copy.deepcopy(analysis.get("audio_io_box_ids", [])),
        },
        "bridge": {
            "enabled": bool(analysis.get("bridge_box_ids") or bridge_support_files),
            "box_ids": copy.deepcopy(analysis.get("bridge_box_ids", [])),
            "support_files": bridge_support_files,
        },
        "lossiness": lossiness,
        "notes": copy.deepcopy(analysis.get("notes", [])),
    }


def _finalize_snapshot(snapshot: dict) -> dict:
    snapshot["analysis"] = analyze_snapshot(snapshot)
    return snapshot


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


def _snapshot_uses_default_audio_io(snapshot: dict) -> bool:
    if snapshot.get("device", {}).get("device_type") != "audio_effect":
        return False

    boxes_by_id = {
        wrapped.get("box", {}).get("id"): wrapped.get("box", {})
        for wrapped in snapshot.get("boxes", [])
    }
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

    def _scan_json_bounds(start: int) -> tuple[int, int] | None:
        json_end = None
        depth = 0
        in_string = False
        escaping = False
        for index, byte in enumerate(payload[start:], start=start):
            if in_string:
                if escaping:
                    escaping = False
                elif byte == 0x5C:  # backslash
                    escaping = True
                elif byte == 0x22:  # quote
                    in_string = False
                continue

            if byte == 0x22:  # quote
                in_string = True
            elif byte == 0x7B:  # {
                depth += 1
            elif byte == 0x7D:  # }
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
        bounds = _scan_json_bounds(start)
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
    """Capture a normalized snapshot from LiveMCP Max bridge payloads.

    This is a fidelity-limited reconstruction. It normalizes current patcher
    metadata, box summaries, optional box attrs, and optional patchline data
    into the same snapshot schema used for `.amxd` imports.
    """
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
    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        filename = box.get("filename")
        if box.get("maxclass") in {"jsui", "v8ui"} and filename in support_files_by_name:
            filenames.add(filename)
    return filenames


def _support_file_statements(snapshot: dict, *, skipped_names: Optional[set[str]] = None) -> list[str]:
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
    return kwargs


def _box_builder_statement(box: dict, support_files_by_name: Optional[dict[str, dict]] = None) -> str:
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


def generate_python_from_snapshot(snapshot: dict) -> str:
    """Generate a starter Python rebuild script from a normalized snapshot."""
    device_type = snapshot["device"]["device_type"]
    patcher_literal = _python_literal(snapshot["patcher"])
    support_files = _python_literal(snapshot.get("support_files", []))
    missing_support_files = _python_literal(snapshot.get("missing_support_files", []))
    analysis = _python_literal(snapshot.get("analysis", {}))
    fidelity = _python_literal(snapshot.get("fidelity", {}))
    device_type_constant = DEVICE_TYPE_TO_CODE_CONSTANT.get(device_type, "AUDIO_EFFECT")

    lines = [
        '"""Starter rebuild script generated from an m4l-builder snapshot."""',
        "",
        "import os",
        "",
        "from m4l_builder import write_amxd",
        "from m4l_builder.constants import %s" % device_type_constant,
        "",
        "PATCHER = %s" % patcher_literal,
        "",
        "SUPPORT_FILES = %s" % support_files,
        "",
        "MISSING_SUPPORT_FILES = %s" % missing_support_files,
        "",
        "SNAPSHOT_FIDELITY = %s" % fidelity,
        "",
        "SNAPSHOT_ANALYSIS = %s" % analysis,
        "",
        "",
        "def build(output_path: str) -> int:",
        '    """Write the reverse-engineered device and any recovered sidecars."""',
        "    written = write_amxd(PATCHER, output_path, %s)" % device_type_constant,
        '    output_dir = os.path.dirname(output_path) or "."',
        "    for support in SUPPORT_FILES:",
        '        support_path = os.path.join(output_dir, support["name"])',
        '        with open(support_path, "w", encoding="utf-8") as handle:',
        '            handle.write(support["content"])',
        "    return written",
        "",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(",
        "        'This generated module exposes build(output_path); it does not choose an output path automatically.'",
        "    )",
        "",
    ]

    if snapshot.get("missing_support_files"):
        lines.extend([
            "# Some dependency entries were declared in the source snapshot but their",
            "# sidecar contents could not be recovered automatically:",
            "# %s" % missing_support_files,
            "",
        ])

    return "\n".join(lines)


def generate_builder_python_from_snapshot(snapshot: dict) -> str:
    """Generate a hybrid builder-style Python rebuild script from a snapshot."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    fidelity = snapshot.get("fidelity", {})
    imports = ["Device", "AudioEffect", "Instrument", "MidiEffect"]
    support_files_by_name = _support_files_by_name(snapshot)
    semantic_jsui_filenames = _semantic_jsui_filenames(snapshot, support_files_by_name)
    lines = [
        '"""Hybrid builder-style rebuild script generated from an m4l-builder snapshot."""',
        "",
        "import os",
        "",
        "from m4l_builder import %s" % ", ".join(imports),
        "",
        "SNAPSHOT_FIDELITY = %s" % _python_literal(fidelity),
        "",
        "SNAPSHOT_ANALYSIS = %s" % _python_literal(analysis),
        "",
        "",
        "def build_device():",
        "    device = %s" % _device_ctor_for_snapshot(snapshot),
    ]

    lines.extend(_support_file_statements(snapshot, skipped_names=semantic_jsui_filenames))

    skip_default_audio_ids = set()
    if analysis.get("uses_default_audio_io", False):
        skip_default_audio_ids = set(DEFAULT_AUDIO_IO_BOXES)

    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        if box.get("id") in skip_default_audio_ids:
            continue
        lines.append(_box_builder_statement(box, support_files_by_name))

    for statement in _assign_parameter_bank_statements(snapshot):
        lines.append(statement)

    for line in snapshot.get("lines", []):
        patchline = line.get("patchline", {})
        lines.append(
            _call_statement(
                "add_line",
                [
                    patchline.get("source", [None, 0])[0],
                    patchline.get("source", [None, 0])[1],
                    patchline.get("destination", [None, 0])[0],
                    patchline.get("destination", [None, 0])[1],
                ],
                {},
            )
        )

    lines.extend([
        "    return device",
        "",
        "",
        "def build(output_path: str) -> int:",
        "    return build_device().build(output_path)",
        "",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(",
        "        'This generated module exposes build_device() and build(output_path); it does not choose an output path automatically.'",
        "    )",
        "",
    ])

    return "\n".join(lines)


def _select_live_api_codegen_candidates(
    snapshot: dict,
    *,
    allowed_levels: set[str],
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
) -> tuple[list[dict], list[dict]]:
    selected = []
    manual_review = []
    for candidate in extract_live_api_normalization_candidates(snapshot):
        candidate_level = candidate.get("normalization_level")
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        if any(box_id in consumed_box_ids for box_id in candidate_box_ids):
            continue
        if any(line_key in consumed_line_keys for line_key in candidate_line_keys):
            continue
        if candidate_level in allowed_levels:
            selected.append(candidate)
        elif candidate_level == "manual_review":
            manual_review.append(candidate)
    return selected, manual_review


def _select_controller_shell_codegen_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
) -> list[dict]:
    selected = []
    for candidate in extract_controller_shell_candidates(snapshot):
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        if any(box_id in consumed_box_ids for box_id in candidate_box_ids):
            continue
        if any(line_key in consumed_line_keys for line_key in candidate_line_keys):
            continue
        selected.append(candidate)
    return selected


def _select_embedded_ui_shell_codegen_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
) -> list[dict]:
    selected = []
    for candidate in extract_embedded_ui_shell_candidates(snapshot):
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        if any(box_id in consumed_box_ids for box_id in candidate_box_ids):
            continue
        if any(line_key in consumed_line_keys for line_key in candidate_line_keys):
            continue
        selected.append(candidate)
    return selected


def _select_first_party_helper_codegen_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
    prefer_semantic_group_box_ids: set[str] | None = None,
) -> list[dict]:
    selected = []
    local_consumed_box_ids = set(consumed_box_ids)
    local_consumed_line_keys = set(consumed_line_keys)
    prefer_semantic_group_box_ids = prefer_semantic_group_box_ids or set()
    for extractor in (
        extract_poly_shell_bank_candidates,
        extract_poly_shell_candidates,
        extract_init_dispatch_chain_candidates,
        extract_named_bus_router_candidates,
    ):
        for candidate in extractor(snapshot):
            candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
            candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
            if (
                candidate.get("candidate_name") in {"poly_shell_bank", "poly_shell"}
                and prefer_semantic_group_box_ids
                and set(candidate_box_ids).issubset(prefer_semantic_group_box_ids)
            ):
                continue
            if any(box_id in local_consumed_box_ids for box_id in candidate_box_ids):
                continue
            if any(line_key in local_consumed_line_keys for line_key in candidate_line_keys):
                continue
            selected.append(candidate)
            local_consumed_box_ids.update(candidate_box_ids)
            local_consumed_line_keys.update(candidate_line_keys)
    return sorted(selected, key=lambda item: (item["first_box_index"], item["candidate_name"]))


def _wrapped_boxes_for_candidate(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str],
) -> list[dict]:
    candidate_box_ids = set(candidate.get("box_ids", []))
    boxes = []
    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
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


def _controller_shell_helper_statements(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str],
) -> list[str]:
    helper = copy.deepcopy(candidate.get("helper_call") or {})
    if not helper:
        helper = _controller_shell_helper_call(
            snapshot,
            candidate,
            skip_default_audio_ids=skip_default_audio_ids,
        )
    else:
        helper["kwargs"] = copy.deepcopy(helper.get("kwargs", {}))
        helper["kwargs"]["boxes"] = _wrapped_boxes_for_candidate(
            snapshot,
            candidate,
            skip_default_audio_ids=skip_default_audio_ids,
        )
    helper_name = helper.get("name")
    lines = [f"    # semantic target: {helper_name}"]
    for evidence in candidate.get("evidence", []):
        lines.append(f"    # {evidence}")
    lines.append(
        _dsp_add_statement(
            helper_name,
            helper.get("positional", []),
            helper.get("kwargs", {}),
        )
    )
    return lines


def _candidate_helper_statements(candidate: dict) -> list[str]:
    helper = copy.deepcopy(candidate.get("helper_call") or {})
    helper_name = helper.get("name") or candidate.get("candidate_name")
    lines = [f"    # semantic target: {helper_name}"]
    for evidence in candidate.get("evidence", []):
        lines.append(f"    # {evidence}")
    lines.append(
        _dsp_add_statement(
            helper_name,
            helper.get("positional", []),
            helper.get("kwargs", {}),
        )
    )
    return lines


def _embedded_ui_shell_helper_statements(candidate: dict) -> list[str]:
    return _candidate_helper_statements(candidate)


def _trim_candidate_to_unconsumed(
    snapshot: dict,
    candidate: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
    skip_default_audio_ids: set[str],
) -> dict | None:
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    remaining_box_ids = [
        box_id
        for box_id in candidate.get("box_ids", [])
        if box_id not in consumed_box_ids and box_id not in skip_default_audio_ids
    ]
    if not remaining_box_ids:
        return None

    remaining_box_id_set = set(remaining_box_ids)
    remaining_line_keys = [
        line_key
        for line_key in candidate.get("line_keys", [])
        if line_key not in consumed_line_keys
        and line_key[0] in remaining_box_id_set
        and line_key[2] in remaining_box_id_set
    ]
    trimmed = copy.deepcopy(candidate)
    trimmed["box_ids"] = remaining_box_ids
    trimmed["line_keys"] = remaining_line_keys
    trimmed["first_box_index"] = min(box_indices.get(box_id, 10 ** 9) for box_id in remaining_box_ids)
    trimmed["consume_box_ids"] = copy.deepcopy(remaining_box_ids)
    return trimmed


def _select_semantic_group_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
    skip_default_audio_ids: set[str],
) -> list[dict]:
    selected = []
    local_consumed_box_ids = set(consumed_box_ids)
    local_consumed_line_keys = set(consumed_line_keys)
    for extractor in (
        extract_mapping_semantic_candidates,
        extract_mapping_workflow_candidates,
        extract_poly_editor_bank_candidates,
        extract_first_party_api_rig_candidates,
        extract_first_party_abstraction_family_candidates,
        extract_first_party_abstraction_host_candidates,
        extract_gen_processing_candidates,
        extract_sample_buffer_candidates,
        extract_presentation_widget_cluster_candidates,
        extract_building_block_candidates,
        extract_state_bundle_router_candidates,
    ):
        for candidate in extractor(snapshot):
            trimmed = _trim_candidate_to_unconsumed(
                snapshot,
                candidate,
                consumed_box_ids=local_consumed_box_ids,
                consumed_line_keys=local_consumed_line_keys,
                skip_default_audio_ids=skip_default_audio_ids,
            )
            if not trimmed:
                continue
            selected.append(trimmed)
            local_consumed_box_ids.update(trimmed.get("box_ids", []))
            local_consumed_line_keys.update(trimmed.get("line_keys", []))
    return sorted(selected, key=lambda item: (item["first_box_index"], item["candidate_name"]))


def _semantic_group_candidate_statements(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str],
) -> list[str]:
    boxes = _wrapped_boxes_for_candidate(
        snapshot,
        candidate,
        skip_default_audio_ids=skip_default_audio_ids,
    )
    lines = _wrapped_lines_for_candidate(snapshot, candidate)
    helper_name = candidate.get("candidate_name")
    statement_lines = [f"    # semantic group: {helper_name}"]
    for evidence in candidate.get("evidence", []):
        statement_lines.append(f"    # {evidence}")
    statement_lines.extend([
        "    device.add_dsp(",
        f"        {_python_literal(boxes)},",
        f"        {_python_literal(lines)},",
        "    )",
    ])
    return statement_lines


def _structured_generator_source(
    snapshot: dict,
    *,
    docstring: str,
    allowed_live_api_levels: set[str],
    include_manual_review_notes: bool,
    include_controller_shell_candidates: bool,
    include_embedded_ui_shell_candidates: bool,
    include_semantic_group_candidates: bool = False,
) -> str:
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    fidelity = snapshot.get("fidelity", {})
    patterns = analysis.get("patterns", [])
    recipes = analysis.get("recipes", [])
    support_files_by_name = _support_files_by_name(snapshot)
    semantic_jsui_filenames = _semantic_jsui_filenames(snapshot, support_files_by_name)
    skip_default_audio_ids = set()
    if analysis.get("uses_default_audio_io", False):
        skip_default_audio_ids = set(DEFAULT_AUDIO_IO_BOXES)
    live_api_candidates_all = extract_live_api_normalization_candidates(snapshot)
    controller_shell_candidates_all = extract_controller_shell_candidates(snapshot)
    embedded_ui_shell_candidates_all = extract_embedded_ui_shell_candidates(snapshot)
    named_bus_router_candidates_all = extract_named_bus_router_candidates(snapshot)
    init_dispatch_chain_candidates_all = extract_init_dispatch_chain_candidates(snapshot)
    poly_shell_candidates_all = extract_poly_shell_candidates(snapshot)
    poly_shell_bank_candidates_all = extract_poly_shell_bank_candidates(snapshot)
    poly_editor_bank_candidates_all = extract_poly_editor_bank_candidates(snapshot)
    mapping_behavior_traces_all = extract_mapping_behavior_traces(snapshot)
    mapping_semantic_candidates_all = extract_mapping_semantic_candidates(snapshot)
    mapping_workflow_candidates_all = extract_mapping_workflow_candidates(snapshot)
    state_bundle_router_candidates_all = extract_state_bundle_router_candidates(snapshot)
    sample_buffer_candidates_all = extract_sample_buffer_candidates(snapshot)
    gen_processing_candidates_all = extract_gen_processing_candidates(snapshot)
    presentation_widget_cluster_candidates_all = extract_presentation_widget_cluster_candidates(snapshot)
    first_party_api_rig_candidates_all = extract_first_party_api_rig_candidates(snapshot)
    first_party_abstraction_host_candidates_all = extract_first_party_abstraction_host_candidates(snapshot)
    first_party_abstraction_family_candidates_all = extract_first_party_abstraction_family_candidates(snapshot)
    building_block_candidates_all = extract_building_block_candidates(snapshot)
    semantic_group_preference_box_ids: set[str] = set()
    if include_semantic_group_candidates:
        for candidate in extract_mapping_semantic_candidates(snapshot):
            semantic_group_preference_box_ids.update(candidate.get("box_ids", []))
        for candidate in extract_mapping_workflow_candidates(snapshot):
            semantic_group_preference_box_ids.update(candidate.get("box_ids", []))
        for candidate in extract_poly_editor_bank_candidates(snapshot):
            semantic_group_preference_box_ids.update(candidate.get("box_ids", []))

    imports = ["Device", "AudioEffect", "Instrument", "MidiEffect"]
    optimized_recipes = [recipe for recipe in recipes if recipe.get("recipeizable")]
    for recipe in optimized_recipes:
        recipe_name = recipe.get("recipe", {}).get("name")
        if recipe_name and recipe_name not in imports:
            imports.append(recipe_name)

    consumed_box_ids = set()
    consumed_line_keys = set()
    recipes_by_index: dict[int, list[dict]] = {}
    for recipe in optimized_recipes:
        consumed_box_ids.update(recipe["box_ids"])
        consumed_line_keys.update(recipe["line_keys"])
        recipes_by_index.setdefault(recipe["first_box_index"], []).append(recipe)

    first_party_helper_candidates = _select_first_party_helper_codegen_candidates(
        snapshot,
        consumed_box_ids=consumed_box_ids,
        consumed_line_keys=consumed_line_keys,
        prefer_semantic_group_box_ids=semantic_group_preference_box_ids,
    )
    for candidate in first_party_helper_candidates:
        helper_name = candidate.get("helper_call", {}).get("name") or candidate.get("candidate_name")
        if helper_name and helper_name not in imports:
            imports.append(helper_name)
    for candidate in first_party_helper_candidates:
        consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    optimized_patterns = []
    for pattern in patterns:
        if not pattern.get("helperizable"):
            continue
        if any(box_id in consumed_box_ids for box_id in pattern["box_ids"]):
            continue
        if any(line_key in consumed_line_keys for line_key in pattern["line_keys"]):
            continue
        optimized_patterns.append(pattern)

    for pattern in optimized_patterns:
        helper_name = pattern.get("helper", {}).get("name")
        if helper_name and helper_name not in imports:
            imports.append(helper_name)

    controller_shell_candidates = []
    if include_controller_shell_candidates:
        controller_shell_candidates = _select_controller_shell_codegen_candidates(
            snapshot,
            consumed_box_ids=consumed_box_ids,
            consumed_line_keys=consumed_line_keys,
        )
        for candidate in controller_shell_candidates:
            helper_name = candidate.get("helper_call", {}).get("name") or candidate.get("candidate_name")
            if helper_name and helper_name not in imports:
                imports.append(helper_name)
        for candidate in controller_shell_candidates:
            consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
            consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    embedded_ui_shell_candidates = []
    if include_embedded_ui_shell_candidates:
        embedded_ui_shell_candidates = _select_embedded_ui_shell_codegen_candidates(
            snapshot,
            consumed_box_ids=consumed_box_ids,
            consumed_line_keys=consumed_line_keys,
        )
        for candidate in embedded_ui_shell_candidates:
            helper_name = candidate.get("helper_call", {}).get("name") or candidate.get("candidate_name")
            if helper_name and helper_name not in imports:
                imports.append(helper_name)
        for candidate in embedded_ui_shell_candidates:
            consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
            consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    live_api_candidates, manual_review_live_api = _select_live_api_codegen_candidates(
        snapshot,
        allowed_levels=allowed_live_api_levels,
        consumed_box_ids=consumed_box_ids,
        consumed_line_keys=consumed_line_keys,
    )
    for candidate in live_api_candidates:
        helper_name = candidate.get("helper_call", {}).get("name")
        if helper_name and helper_name not in imports:
            imports.append(helper_name)
    for candidate in live_api_candidates:
        consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    semantic_group_candidates = []
    if include_semantic_group_candidates:
        semantic_group_candidates = _select_semantic_group_candidates(
            snapshot,
            consumed_box_ids=consumed_box_ids,
            consumed_line_keys=consumed_line_keys,
            skip_default_audio_ids=skip_default_audio_ids,
        )
        for candidate in semantic_group_candidates:
            consumed_box_ids.update(candidate.get("box_ids", []))
            consumed_line_keys.update(candidate.get("line_keys", []))

    matched_box_ids = set()
    matched_line_keys = set()
    first_party_helpers_by_index: dict[int, list[dict]] = {}
    for candidate in first_party_helper_candidates:
        matched_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))
        first_party_helpers_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    controller_shells_by_index: dict[int, list[dict]] = {}
    for candidate in controller_shell_candidates:
        matched_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))
        controller_shells_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    embedded_ui_shells_by_index: dict[int, list[dict]] = {}
    for candidate in embedded_ui_shell_candidates:
        matched_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))
        embedded_ui_shells_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    live_api_helpers_by_index: dict[int, list[dict]] = {}
    for candidate in live_api_candidates:
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        matched_box_ids.update(candidate_box_ids)
        matched_line_keys.update(candidate_line_keys)
        live_api_helpers_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    semantic_groups_by_index: dict[int, list[dict]] = {}
    for candidate in semantic_group_candidates:
        matched_box_ids.update(candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys", []))
        semantic_groups_by_index.setdefault(candidate["first_box_index"], []).append(candidate)

    patterns_by_index: dict[int, list[dict]] = {}
    for pattern in optimized_patterns:
        matched_box_ids.update(pattern["box_ids"])
        matched_line_keys.update(pattern["line_keys"])
        patterns_by_index.setdefault(pattern["first_box_index"], []).append(pattern)
    matched_box_ids.update(consumed_box_ids)
    matched_line_keys.update(consumed_line_keys)

    lines = [
        docstring,
        "",
        "import os",
        "",
        "from m4l_builder import %s" % ", ".join(imports),
        "",
        "SNAPSHOT_FIDELITY = %s" % _python_literal(fidelity),
        "",
        "SNAPSHOT_ANALYSIS = %s" % _python_literal(analysis),
        "",
        "SNAPSHOT_PATTERNS = %s" % _python_literal(patterns),
        "",
        "SNAPSHOT_RECIPES = %s" % _python_literal(recipes),
        "",
        "SNAPSHOT_LIVE_API_NORMALIZATION_CANDIDATES = %s" % _python_literal(live_api_candidates_all),
        "",
        "SNAPSHOT_CONTROLLER_SHELL_CANDIDATES = %s" % _python_literal(controller_shell_candidates_all),
        "",
        "SNAPSHOT_EMBEDDED_UI_SHELL_CANDIDATES = %s" % _python_literal(embedded_ui_shell_candidates_all),
        "",
        "SNAPSHOT_NAMED_BUS_ROUTER_CANDIDATES = %s" % _python_literal(named_bus_router_candidates_all),
        "",
        "SNAPSHOT_INIT_DISPATCH_CHAIN_CANDIDATES = %s" % _python_literal(init_dispatch_chain_candidates_all),
        "",
        "SNAPSHOT_POLY_SHELL_CANDIDATES = %s" % _python_literal(poly_shell_candidates_all),
        "",
        "SNAPSHOT_POLY_SHELL_BANK_CANDIDATES = %s" % _python_literal(poly_shell_bank_candidates_all),
        "",
        "SNAPSHOT_POLY_EDITOR_BANK_CANDIDATES = %s" % _python_literal(poly_editor_bank_candidates_all),
        "",
        "SNAPSHOT_MAPPING_BEHAVIOR_TRACES = %s" % _python_literal(mapping_behavior_traces_all),
        "",
        "SNAPSHOT_MAPPING_SEMANTIC_CANDIDATES = %s" % _python_literal(mapping_semantic_candidates_all),
        "",
        "SNAPSHOT_MAPPING_WORKFLOW_CANDIDATES = %s" % _python_literal(mapping_workflow_candidates_all),
        "",
        "SNAPSHOT_STATE_BUNDLE_ROUTER_CANDIDATES = %s" % _python_literal(state_bundle_router_candidates_all),
        "",
        "SNAPSHOT_SAMPLE_BUFFER_CANDIDATES = %s" % _python_literal(sample_buffer_candidates_all),
        "",
        "SNAPSHOT_GEN_PROCESSING_CANDIDATES = %s" % _python_literal(gen_processing_candidates_all),
        "",
        "SNAPSHOT_PRESENTATION_WIDGET_CLUSTER_CANDIDATES = %s" % _python_literal(presentation_widget_cluster_candidates_all),
        "",
        "SNAPSHOT_FIRST_PARTY_API_RIG_CANDIDATES = %s" % _python_literal(first_party_api_rig_candidates_all),
        "",
        "SNAPSHOT_FIRST_PARTY_ABSTRACTION_HOST_CANDIDATES = %s" % _python_literal(first_party_abstraction_host_candidates_all),
        "",
        "SNAPSHOT_FIRST_PARTY_ABSTRACTION_FAMILY_CANDIDATES = %s" % _python_literal(first_party_abstraction_family_candidates_all),
        "",
        "SNAPSHOT_BUILDING_BLOCK_CANDIDATES = %s" % _python_literal(building_block_candidates_all),
        "",
        "",
    ]

    lines.extend([
        "def build_device():",
        "    device = %s" % _device_ctor_for_snapshot(snapshot),
    ])

    if include_manual_review_notes and manual_review_live_api:
        lines.append("    # Live API clusters left expanded for manual review:")
        for candidate in manual_review_live_api:
            lines.append(
                "    # %s -> %s (%s)"
                % (
                    candidate.get("helper_name"),
                    ", ".join(candidate.get("box_ids", [])),
                    ", ".join(candidate.get("blocking_factors", [])),
                )
            )

    lines.extend(_support_file_statements(snapshot, skipped_names=semantic_jsui_filenames))

    for index, wrapped in enumerate(snapshot.get("boxes", [])):
        for candidate in first_party_helpers_by_index.get(index, []):
            lines.extend(_candidate_helper_statements(candidate))
        for recipe in recipes_by_index.get(index, []):
            recipe_call = recipe["recipe"]
            lines.append(
                _recipe_call_statement(
                    recipe_call["name"],
                    recipe_call.get("positional", []),
                    recipe_call.get("kwargs", {}),
                )
            )
        for candidate in controller_shells_by_index.get(index, []):
            lines.extend(
                _controller_shell_helper_statements(
                    snapshot,
                    candidate,
                    skip_default_audio_ids=skip_default_audio_ids,
                )
            )
        for candidate in embedded_ui_shells_by_index.get(index, []):
            lines.extend(_embedded_ui_shell_helper_statements(candidate))
        for candidate in live_api_helpers_by_index.get(index, []):
            helper = candidate["helper_call"]
            lines.append(
                _dsp_add_statement(
                    helper["name"],
                    helper.get("positional", []),
                    helper.get("kwargs", {}),
                )
            )
        for candidate in semantic_groups_by_index.get(index, []):
            lines.extend(
                _semantic_group_candidate_statements(
                    snapshot,
                    candidate,
                    skip_default_audio_ids=skip_default_audio_ids,
                )
            )
        for pattern in patterns_by_index.get(index, []):
            helper = pattern["helper"]
            lines.append(
                _dsp_add_statement(
                    helper["name"],
                    helper.get("positional", []),
                    helper.get("kwargs", {}),
                )
            )

        box = wrapped.get("box", {})
        box_id = box.get("id")
        if box_id in skip_default_audio_ids or box_id in matched_box_ids:
            continue
        lines.append(_box_builder_statement(box, support_files_by_name))

    for statement in _assign_parameter_bank_statements(snapshot):
        lines.append(statement)

    for line in snapshot.get("lines", []):
        line_key = _line_key_from_wrapped(line)
        if line_key in matched_line_keys:
            continue
        patchline = line.get("patchline", {})
        lines.append(
            _call_statement(
                "add_line",
                [
                    patchline.get("source", [None, 0])[0],
                    patchline.get("source", [None, 0])[1],
                    patchline.get("destination", [None, 0])[0],
                    patchline.get("destination", [None, 0])[1],
                ],
                {},
            )
        )

    lines.extend([
        "    return device",
        "",
        "",
        "def build(output_path: str) -> int:",
        "    return build_device().build(output_path)",
        "",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(",
        "        'This generated module exposes build_device() and build(output_path); it does not choose an output path automatically.'",
        "    )",
        "",
    ])

    return "\n".join(lines)


def generate_optimized_python_from_snapshot(snapshot: dict) -> str:
    """Generate an exact-safe builder script that emits recognized helpers where possible."""
    return _structured_generator_source(
        snapshot,
        docstring='"""Optimized builder-style rebuild script generated from an m4l-builder snapshot."""',
        allowed_live_api_levels={"exact"},
        include_manual_review_notes=False,
        include_controller_shell_candidates=True,
        include_embedded_ui_shell_candidates=True,
    )


def generate_semantic_python_from_snapshot(snapshot: dict) -> str:
    """Generate a semantic builder script that also normalizes safe Live API opportunities."""
    return _structured_generator_source(
        snapshot,
        docstring='"""Semantic builder-style rebuild script generated from an m4l-builder snapshot."""',
        allowed_live_api_levels={"exact", "normalized_safe", "normalized_with_binding"},
        include_manual_review_notes=True,
        include_controller_shell_candidates=True,
        include_embedded_ui_shell_candidates=True,
        include_semantic_group_candidates=True,
    )


def generate_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> normalized snapshot -> starter Python."""
    return generate_python_from_snapshot(snapshot_from_amxd(path))


def generate_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> normalized snapshot -> starter Python."""
    return generate_python_from_snapshot(snapshot_from_device(device))


def generate_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> normalized snapshot -> starter Python."""
    return generate_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


def generate_builder_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> snapshot -> hybrid builder-style Python."""
    return generate_builder_python_from_snapshot(snapshot_from_amxd(path))


def generate_builder_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> snapshot -> hybrid builder-style Python."""
    return generate_builder_python_from_snapshot(snapshot_from_device(device))


def generate_builder_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> snapshot -> hybrid builder-style Python."""
    return generate_builder_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


def generate_optimized_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> snapshot -> optimized builder-style Python."""
    return generate_optimized_python_from_snapshot(snapshot_from_amxd(path))


def generate_optimized_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> snapshot -> optimized builder-style Python."""
    return generate_optimized_python_from_snapshot(snapshot_from_device(device))


def generate_optimized_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> snapshot -> optimized builder-style Python."""
    return generate_optimized_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


def generate_semantic_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> snapshot -> semantic builder-style Python."""
    return generate_semantic_python_from_snapshot(snapshot_from_amxd(path))


def generate_semantic_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> snapshot -> semantic builder-style Python."""
    return generate_semantic_python_from_snapshot(snapshot_from_device(device))


def generate_semantic_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> snapshot -> semantic builder-style Python."""
    return generate_semantic_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


__all__ = [
    "read_amxd",
    "snapshot_from_device",
    "snapshot_from_amxd",
    "snapshot_from_bridge_payload",
    "snapshot_to_json",
    "write_snapshot",
    "load_snapshot",
    "analyze_snapshot",
    "extract_embedded_patcher_snapshots",
    "extract_controller_shell_candidates",
    "extract_embedded_ui_shell_candidates",
    "extract_named_bus_router_candidates",
    "extract_init_dispatch_chain_candidates",
    "extract_state_bundle_router_candidates",
    "extract_sample_buffer_candidates",
    "extract_gen_processing_candidates",
    "extract_presentation_widget_cluster_candidates",
    "extract_poly_shell_candidates",
    "extract_poly_shell_bank_candidates",
    "extract_poly_editor_bank_candidates",
    "extract_behavior_hints",
    "extract_mapping_behavior_traces",
    "extract_mapping_semantic_candidates",
    "extract_mapping_workflow_candidates",
    "extract_first_party_api_rig_candidates",
    "extract_first_party_abstraction_host_candidates",
    "extract_first_party_abstraction_family_candidates",
    "extract_building_block_candidates",
    "extract_live_api_normalization_candidates",
    "detect_snapshot_patterns",
    "detect_snapshot_recipes",
    "detect_snapshot_motifs",
    "extract_parameter_specs",
    "extract_snapshot_knowledge",
    "generate_python_from_snapshot",
    "generate_python_from_amxd",
    "generate_python_from_device",
    "generate_python_from_bridge_payload",
    "generate_builder_python_from_snapshot",
    "generate_builder_python_from_amxd",
    "generate_builder_python_from_device",
    "generate_builder_python_from_bridge_payload",
    "generate_optimized_python_from_snapshot",
    "generate_optimized_python_from_amxd",
    "generate_optimized_python_from_device",
    "generate_optimized_python_from_bridge_payload",
    "generate_semantic_python_from_snapshot",
    "generate_semantic_python_from_amxd",
    "generate_semantic_python_from_device",
    "generate_semantic_python_from_bridge_payload",
]
