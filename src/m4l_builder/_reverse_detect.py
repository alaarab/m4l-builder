"""Snapshot pattern/motif detectors for the legacy-device reverse tool.

Extracted from _reverse_legacy.py (god-file split); re-exported by it."""
from __future__ import annotations

import copy
import os
import pprint
import re
from pathlib import Path
from typing import Any

from ._reverse_constants import *  # noqa: F401,F403
from ._reverse_helpers import *  # noqa: F401,F403
from ._reverse_match import *  # noqa: F401,F403
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
from .recipes import (
    dry_wet_stage,
    gain_controlled_stage,
    midi_note_gate,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)


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


def _detect_live_api_helper_matches(snapshot: dict, motifs: list[dict] | None = None) -> list[dict]:
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


def _detect_live_api_helper_opportunities(
    snapshot: dict,
    *,
    motifs: list[dict] | None = None,
    exact_matches: list[dict] | None = None,
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

__all__ = [
    "detect_snapshot_patterns",
    "detect_snapshot_recipes",
    "_detect_named_bus_motifs",
    "_detect_controller_dispatch_motifs",
    "_detect_scheduler_chain_motifs",
    "_detect_state_bundle_motifs",
    "_detect_live_api_component_motifs",
    "_detect_sample_buffer_toolchain_motifs",
    "_detect_gen_processing_core_motifs",
    "_detect_embedded_patcher_motifs",
    "detect_snapshot_motifs",
    "_detect_live_api_helper_matches",
    "_detect_live_api_helper_opportunities",
]

