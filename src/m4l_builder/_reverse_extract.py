"""Candidate extractors + top-level snapshot analysis (reverse tool).

Extracted from _reverse_legacy.py (god-file split); re-exported by it."""
from __future__ import annotations

import copy
import os
import pprint
import re
from pathlib import Path
from typing import Any

from ._reverse_constants import *  # noqa: F401,F403
from ._reverse_detect import *  # noqa: F401,F403
from ._reverse_helpers import *  # noqa: F401,F403
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


def extract_parameter_specs(snapshot: dict) -> list[dict]:
    """Extract parameter/control specs from a normalized snapshot."""
    from .reverse_snapshot import extract_parameter_specs as _extract_parameter_specs

    return _extract_parameter_specs(snapshot)


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
    maxclass_counts: dict[str, int] = {}
    object_name_counts: dict[str, int] = {}
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


def analyze_snapshot(snapshot: dict) -> dict:
    """Return first-pass structural analysis for a normalized snapshot."""
    boxes = snapshot.get("boxes", [])
    lines = snapshot.get("lines", [])
    support_names = {entry.get("name") for entry in snapshot.get("support_files", [])}

    maxclass_counts: dict[str, int] = {}
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


def _embedded_target_snapshots(snapshot: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in extract_embedded_patcher_snapshots(snapshot):
        target = str(entry.get("target") or "").strip()
        if not target:
            continue
        grouped.setdefault(target, []).append(entry.get("snapshot", {}))
    return grouped


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
        annotation = str(_box_annotation_name(box) or "").strip()
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
            _box_annotation_name(box),
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
                "annotation_name": _box_annotation_name(box),
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


def extract_embedded_patcher_snapshots(snapshot: dict) -> list[dict]:
    """Extract embedded patchers as normalized nested snapshots."""
    from .reverse_snapshot import (
        extract_embedded_patcher_snapshots as _extract_embedded_patcher_snapshots,
    )

    return _extract_embedded_patcher_snapshots(snapshot)

__all__ = [
    "extract_parameter_specs",
    "extract_live_api_normalization_candidates",
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
    "extract_first_party_api_rig_candidates",
    "extract_first_party_abstraction_host_candidates",
    "extract_first_party_abstraction_family_candidates",
    "extract_building_block_candidates",
    "_collect_embedded_patcher_summaries_from_box",
    "_collect_embedded_patcher_summaries",
    "analyze_snapshot",
    "_embedded_target_snapshots",
    "extract_behavior_hints",
    "extract_mapping_behavior_traces",
    "extract_mapping_semantic_candidates",
    "extract_mapping_workflow_candidates",
    "extract_snapshot_knowledge",
    "extract_embedded_patcher_snapshots",
]

