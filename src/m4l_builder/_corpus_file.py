"""Per-file `.amxd` analysis: classify one device and mine its snapshot.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

import os
import re
from pathlib import Path

from ._corpus_helpers import *  # noqa: F401,F403
from .patcher_walk import iter_boxes
from .reverse import (
    extract_embedded_patcher_snapshots,
    extract_gen_processing_candidates,
    extract_sample_buffer_candidates,
    extract_snapshot_knowledge,
    snapshot_from_amxd,
)


def classify_corpus_source_metadata(path: str) -> dict:
    """Classify a corpus item into public/factory/site-lead lanes."""
    absolute_path = os.path.realpath(os.path.abspath(path))
    parts = Path(absolute_path).parts
    source_lane = "public"
    source_family = None
    pack_name = None
    pack_section = None
    pack_subsection = None

    if "Factory Packs" in parts:
        index = parts.index("Factory Packs")
        trailing = list(parts[index + 1:])
        source_lane = "factory"
        if trailing:
            pack_name = trailing[0]
            source_family = trailing[0]
        if len(trailing) > 1:
            pack_section = trailing[1]
        if len(trailing) > 2:
            pack_subsection = trailing[2]
    elif "maxforlivedevices" in absolute_path.lower():
        source_lane = "site_leads"
        source_family = "maxforlivedevices"
    else:
        match = re.search(r"__([^/]+?)__[^/]+\.amxd$", absolute_path)
        if match:
            source_family = match.group(1)
        else:
            parent = Path(absolute_path).parent.name
            if parent and parent != Path(absolute_path).name:
                source_family = parent

    return {
        "source_lane": source_lane,
        "source_family": source_family,
        "pack_name": pack_name,
        "pack_section": pack_section,
        "pack_subsection": pack_subsection,
    }


def analyze_amxd_file(path: str) -> dict:
    """Analyze one .amxd file for corpus mining."""
    absolute_path = os.path.realpath(os.path.abspath(path))
    source_metadata = classify_corpus_source_metadata(absolute_path)
    item = {
        "path": absolute_path,
        "name": os.path.basename(path),
        **source_metadata,
    }

    try:
        snapshot = snapshot_from_amxd(absolute_path)
        knowledge = extract_snapshot_knowledge(snapshot)
        analysis = snapshot.get("analysis", {})
        missing_support_files = snapshot.get("missing_support_files", [])
        object_name_counts: dict[str, int] = {}
        for box in iter_boxes(snapshot):
            object_name = _object_name_from_box(box)
            if object_name:
                object_name_counts[object_name] = object_name_counts.get(object_name, 0) + 1

        control_maxclass_counts: dict[str, int] = {}
        control_unitstyle_counts: dict[str, int] = {}
        for control in knowledge.get("controls", []):
            maxclass = control.get("maxclass")
            if maxclass:
                control_maxclass_counts[maxclass] = control_maxclass_counts.get(maxclass, 0) + 1
            unitstyle = control.get("unitstyle")
            if unitstyle is not None:
                key = str(unitstyle)
                control_unitstyle_counts[key] = control_unitstyle_counts.get(key, 0) + 1
        motif_signature_counts: dict[str, int] = {}
        for motif in knowledge.get("motifs", []):
            signature = _motif_signature(motif)
            motif_signature_counts[signature] = motif_signature_counts.get(signature, 0) + 1
        live_api_helper_counts: dict[str, int] = {}
        for entry in knowledge.get("live_api_helpers", []):
            helper_name = entry.get("helper_name")
            if helper_name:
                live_api_helper_counts[helper_name] = live_api_helper_counts.get(helper_name, 0) + 1
        live_api_normalization_level_counts: dict[str, int] = {}
        for entry in knowledge.get("live_api_normalization_candidates", []):
            level = entry.get("normalization_level")
            if level:
                live_api_normalization_level_counts[level] = live_api_normalization_level_counts.get(level, 0) + 1
        live_api_helper_opportunity_counts: dict[str, int] = {}
        live_api_helper_opportunity_blockers: dict[str, int] = {}
        controller_shell_candidate_counts: dict[str, int] = {}
        embedded_ui_shell_candidate_counts: dict[str, int] = {}
        named_bus_router_candidate_counts: dict[str, int] = {}
        init_dispatch_chain_candidate_counts: dict[str, int] = {}
        state_bundle_router_candidate_counts: dict[str, int] = {}
        presentation_widget_cluster_candidate_counts: dict[str, int] = {}
        poly_shell_candidate_counts: dict[str, int] = {}
        poly_shell_bank_candidate_counts: dict[str, int] = {}
        poly_editor_bank_candidate_counts: dict[str, int] = {}
        mapping_behavior_trace_counts: dict[str, int] = {}
        mapping_semantic_candidate_counts: dict[str, int] = {}
        mapping_workflow_candidate_counts: dict[str, int] = {}
        behavior_hint_counts: dict[str, int] = {}
        sample_buffer_candidate_counts: dict[str, int] = {}
        gen_processing_candidate_counts: dict[str, int] = {}
        embedded_sample_buffer_candidate_counts: dict[str, int] = {}
        embedded_gen_processing_candidate_counts: dict[str, int] = {}
        first_party_api_rig_candidate_counts: dict[str, int] = {}
        first_party_abstraction_host_candidate_counts: dict[str, int] = {}
        first_party_abstraction_host_family_counts: dict[str, int] = {}
        building_block_candidate_counts: dict[str, int] = {}
        for entry in knowledge.get("live_api_helper_opportunities", []):
            helper_name = entry.get("helper_name")
            if helper_name:
                live_api_helper_opportunity_counts[helper_name] = live_api_helper_opportunity_counts.get(helper_name, 0) + 1
            for blocker in entry.get("blocking_factors", []):
                live_api_helper_opportunity_blockers[blocker] = live_api_helper_opportunity_blockers.get(blocker, 0) + 1
        for entry in knowledge.get("controller_shell_candidates", []):
            candidate_name = entry.get("candidate_name")
            if candidate_name:
                controller_shell_candidate_counts[candidate_name] = (
                    controller_shell_candidate_counts.get(candidate_name, 0) + 1
                )
        for entry in knowledge.get("behavior_hints", []):
            hint_name = entry.get("name")
            if hint_name:
                behavior_hint_counts[hint_name] = behavior_hint_counts.get(hint_name, 0) + 1
        for entry in knowledge.get("mapping_behavior_traces", []):
            trace_name = entry.get("name")
            if trace_name:
                mapping_behavior_trace_counts[trace_name] = mapping_behavior_trace_counts.get(trace_name, 0) + 1
        for entry in knowledge.get("embedded_ui_shell_candidates", []):
            candidate_name = entry.get("candidate_name")
            if candidate_name:
                embedded_ui_shell_candidate_counts[candidate_name] = (
                    embedded_ui_shell_candidate_counts.get(candidate_name, 0) + 1
                )
        for key, field in (
            ("named_bus_router_candidates", named_bus_router_candidate_counts),
            ("init_dispatch_chain_candidates", init_dispatch_chain_candidate_counts),
            ("state_bundle_router_candidates", state_bundle_router_candidate_counts),
            ("sample_buffer_candidates", sample_buffer_candidate_counts),
            ("gen_processing_candidates", gen_processing_candidate_counts),
            ("presentation_widget_cluster_candidates", presentation_widget_cluster_candidate_counts),
            ("poly_shell_candidates", poly_shell_candidate_counts),
            ("poly_shell_bank_candidates", poly_shell_bank_candidate_counts),
            ("poly_editor_bank_candidates", poly_editor_bank_candidate_counts),
            ("mapping_semantic_candidates", mapping_semantic_candidate_counts),
            ("mapping_workflow_candidates", mapping_workflow_candidate_counts),
            ("first_party_api_rig_candidates", first_party_api_rig_candidate_counts),
        ):
            for entry in knowledge.get(key, []):
                candidate_name = entry.get("candidate_name")
                if candidate_name:
                    field[candidate_name] = field.get(candidate_name, 0) + 1
        for nested in extract_embedded_patcher_snapshots(snapshot):
            nested_snapshot = nested.get("snapshot", {})
            for entry in extract_sample_buffer_candidates(nested_snapshot):
                candidate_name = entry.get("candidate_name")
                if candidate_name:
                    embedded_sample_buffer_candidate_counts[candidate_name] = (
                        embedded_sample_buffer_candidate_counts.get(candidate_name, 0) + 1
                    )
            for entry in extract_gen_processing_candidates(nested_snapshot):
                candidate_name = entry.get("candidate_name")
                if candidate_name:
                    embedded_gen_processing_candidate_counts[candidate_name] = (
                        embedded_gen_processing_candidate_counts.get(candidate_name, 0) + 1
                    )
        for entry in knowledge.get("first_party_abstraction_host_candidates", []):
            candidate_name = (
                entry.get("params", {}).get("primary_abstraction_name")
                or entry.get("candidate_name")
            )
            if candidate_name:
                first_party_abstraction_host_candidate_counts[candidate_name] = (
                    first_party_abstraction_host_candidate_counts.get(candidate_name, 0) + 1
                )
            family_name = entry.get("params", {}).get("abstraction_family")
            if family_name:
                first_party_abstraction_host_family_counts[family_name] = (
                    first_party_abstraction_host_family_counts.get(family_name, 0) + 1
                )
        for entry in knowledge.get("building_block_candidates", []):
            candidate_name = (
                entry.get("params", {}).get("block_name")
                or entry.get("candidate_name")
            )
            if candidate_name:
                building_block_candidate_counts[candidate_name] = (
                    building_block_candidate_counts.get(candidate_name, 0) + 1
                )
        live_api_path_target_counts: dict[str, int] = {}
        live_api_property_counts: dict[str, int] = {}
        live_api_get_target_counts: dict[str, int] = {}
        live_api_set_target_counts: dict[str, int] = {}
        live_api_call_target_counts: dict[str, int] = {}
        live_api_archetype_counts: dict[str, int] = {}
        named_bus_network_names: dict[str, int] = {}
        cross_scope_named_bus_network_names: dict[str, int] = {}
        for motif in knowledge.get("motifs", []):
            if motif.get("kind") != "live_api_component":
                continue
            params = motif.get("params", {})
            for target in params.get("path_targets", []):
                live_api_path_target_counts[target] = live_api_path_target_counts.get(target, 0) + 1
            for prop in params.get("property_names", []):
                live_api_property_counts[prop] = live_api_property_counts.get(prop, 0) + 1
            for target in params.get("get_targets", []):
                live_api_get_target_counts[target] = live_api_get_target_counts.get(target, 0) + 1
            for target in params.get("set_targets", []):
                live_api_set_target_counts[target] = live_api_set_target_counts.get(target, 0) + 1
            for target in params.get("call_targets", []):
                live_api_call_target_counts[target] = live_api_call_target_counts.get(target, 0) + 1
            for archetype in params.get("archetypes", []):
                live_api_archetype_counts[archetype] = live_api_archetype_counts.get(archetype, 0) + 1
        for network in knowledge.get("named_bus_networks", []):
            name = network.get("name")
            if name:
                named_bus_network_names[name] = named_bus_network_names.get(name, 0) + 1
                if network.get("cross_scope"):
                    cross_scope_named_bus_network_names[name] = (
                        cross_scope_named_bus_network_names.get(name, 0) + 1
                    )
        embedded_patcher_host_kind_counts: dict[str, int] = {}
        embedded_pattern_kind_counts: dict[str, int] = {}
        embedded_recipe_kind_counts: dict[str, int] = {}
        embedded_motif_kind_counts: dict[str, int] = {}
        embedded_live_api_path_target_counts: dict[str, int] = {}
        embedded_live_api_property_counts: dict[str, int] = {}
        embedded_live_api_get_target_counts: dict[str, int] = {}
        embedded_live_api_set_target_counts: dict[str, int] = {}
        embedded_live_api_call_target_counts: dict[str, int] = {}
        embedded_live_api_archetype_counts: dict[str, int] = {}
        for embedded in knowledge.get("embedded_patchers", []):
            host_kind = embedded.get("host_kind")
            if host_kind:
                embedded_patcher_host_kind_counts[host_kind] = embedded_patcher_host_kind_counts.get(host_kind, 0) + 1
            for kind in embedded.get("pattern_kinds", []):
                embedded_pattern_kind_counts[kind] = embedded_pattern_kind_counts.get(kind, 0) + 1
            for kind in embedded.get("recipe_kinds", []):
                embedded_recipe_kind_counts[kind] = embedded_recipe_kind_counts.get(kind, 0) + 1
            for kind in embedded.get("motif_kinds", []):
                embedded_motif_kind_counts[kind] = embedded_motif_kind_counts.get(kind, 0) + 1
            for target in embedded.get("live_api_path_targets", []):
                embedded_live_api_path_target_counts[target] = embedded_live_api_path_target_counts.get(target, 0) + 1
            for prop in embedded.get("live_api_properties", []):
                embedded_live_api_property_counts[prop] = embedded_live_api_property_counts.get(prop, 0) + 1
            for target in embedded.get("live_api_get_targets", []):
                embedded_live_api_get_target_counts[target] = embedded_live_api_get_target_counts.get(target, 0) + 1
            for target in embedded.get("live_api_set_targets", []):
                embedded_live_api_set_target_counts[target] = embedded_live_api_set_target_counts.get(target, 0) + 1
            for target in embedded.get("live_api_call_targets", []):
                embedded_live_api_call_target_counts[target] = embedded_live_api_call_target_counts.get(target, 0) + 1
            for archetype in embedded.get("live_api_archetypes", []):
                embedded_live_api_archetype_counts[archetype] = embedded_live_api_archetype_counts.get(archetype, 0) + 1

        item.update({
            "status": "ok",
            "device_type": snapshot["device"]["device_type"],
            "box_count": analysis.get("box_count", 0),
            "line_count": analysis.get("line_count", 0),
            "control_count": knowledge["summary"]["control_count"],
            "display_count": knowledge["summary"]["display_count"],
            "pattern_count": knowledge["summary"]["pattern_count"],
            "recipe_count": knowledge["summary"]["recipe_count"],
            "motif_count": knowledge["summary"].get("motif_count", 0),
            "bridge_enabled": knowledge["summary"]["bridge_enabled"],
            "pattern_kinds": [entry["kind"] for entry in knowledge.get("patterns", [])],
            "recipe_kinds": [entry["kind"] for entry in knowledge.get("recipes", [])],
            "motif_kinds": [entry["kind"] for entry in knowledge.get("motifs", [])],
            "live_api_helper_count": sum(live_api_helper_counts.values()),
            "live_api_helper_kinds": sorted(live_api_helper_counts),
            "live_api_helper_counts": live_api_helper_counts,
            "live_api_normalization_level_counts": live_api_normalization_level_counts,
            "live_api_helper_opportunity_count": sum(live_api_helper_opportunity_counts.values()),
            "live_api_helper_opportunity_kinds": sorted(live_api_helper_opportunity_counts),
            "live_api_helper_opportunity_counts": live_api_helper_opportunity_counts,
            "live_api_helper_opportunity_blockers": live_api_helper_opportunity_blockers,
            "controller_shell_candidate_count": sum(controller_shell_candidate_counts.values()),
            "controller_shell_candidate_kinds": sorted(controller_shell_candidate_counts),
            "controller_shell_candidate_counts": controller_shell_candidate_counts,
            "behavior_hint_count": sum(behavior_hint_counts.values()),
            "behavior_hint_kinds": sorted(behavior_hint_counts),
            "behavior_hint_counts": behavior_hint_counts,
            "embedded_ui_shell_candidate_count": sum(embedded_ui_shell_candidate_counts.values()),
            "embedded_ui_shell_candidate_kinds": sorted(embedded_ui_shell_candidate_counts),
            "embedded_ui_shell_candidate_counts": embedded_ui_shell_candidate_counts,
            "named_bus_router_candidate_count": sum(named_bus_router_candidate_counts.values()),
            "named_bus_router_candidate_kinds": sorted(named_bus_router_candidate_counts),
            "named_bus_router_candidate_counts": named_bus_router_candidate_counts,
            "init_dispatch_chain_candidate_count": sum(init_dispatch_chain_candidate_counts.values()),
            "init_dispatch_chain_candidate_kinds": sorted(init_dispatch_chain_candidate_counts),
            "init_dispatch_chain_candidate_counts": init_dispatch_chain_candidate_counts,
            "state_bundle_router_candidate_count": sum(state_bundle_router_candidate_counts.values()),
            "state_bundle_router_candidate_kinds": sorted(state_bundle_router_candidate_counts),
            "state_bundle_router_candidate_counts": state_bundle_router_candidate_counts,
            "sample_buffer_candidate_count": sum(sample_buffer_candidate_counts.values()),
            "sample_buffer_candidate_kinds": sorted(sample_buffer_candidate_counts),
            "sample_buffer_candidate_counts": sample_buffer_candidate_counts,
            "gen_processing_candidate_count": sum(gen_processing_candidate_counts.values()),
            "gen_processing_candidate_kinds": sorted(gen_processing_candidate_counts),
            "gen_processing_candidate_counts": gen_processing_candidate_counts,
            "embedded_sample_buffer_candidate_count": sum(embedded_sample_buffer_candidate_counts.values()),
            "embedded_sample_buffer_candidate_kinds": sorted(embedded_sample_buffer_candidate_counts),
            "embedded_sample_buffer_candidate_counts": embedded_sample_buffer_candidate_counts,
            "embedded_gen_processing_candidate_count": sum(embedded_gen_processing_candidate_counts.values()),
            "embedded_gen_processing_candidate_kinds": sorted(embedded_gen_processing_candidate_counts),
            "embedded_gen_processing_candidate_counts": embedded_gen_processing_candidate_counts,
            "presentation_widget_cluster_candidate_count": sum(presentation_widget_cluster_candidate_counts.values()),
            "presentation_widget_cluster_candidate_kinds": sorted(presentation_widget_cluster_candidate_counts),
            "presentation_widget_cluster_candidate_counts": presentation_widget_cluster_candidate_counts,
            "poly_shell_candidate_count": sum(poly_shell_candidate_counts.values()),
            "poly_shell_candidate_kinds": sorted(poly_shell_candidate_counts),
            "poly_shell_candidate_counts": poly_shell_candidate_counts,
            "poly_shell_bank_candidate_count": sum(poly_shell_bank_candidate_counts.values()),
            "poly_shell_bank_candidate_kinds": sorted(poly_shell_bank_candidate_counts),
            "poly_shell_bank_candidate_counts": poly_shell_bank_candidate_counts,
            "poly_editor_bank_candidate_count": sum(poly_editor_bank_candidate_counts.values()),
            "poly_editor_bank_candidate_kinds": sorted(poly_editor_bank_candidate_counts),
            "poly_editor_bank_candidate_counts": poly_editor_bank_candidate_counts,
            "mapping_behavior_trace_count": sum(mapping_behavior_trace_counts.values()),
            "mapping_behavior_trace_kinds": sorted(mapping_behavior_trace_counts),
            "mapping_behavior_trace_counts": mapping_behavior_trace_counts,
            "mapping_semantic_candidate_count": sum(mapping_semantic_candidate_counts.values()),
            "mapping_semantic_candidate_kinds": sorted(mapping_semantic_candidate_counts),
            "mapping_semantic_candidate_counts": mapping_semantic_candidate_counts,
            "mapping_workflow_candidate_count": sum(mapping_workflow_candidate_counts.values()),
            "mapping_workflow_candidate_kinds": sorted(mapping_workflow_candidate_counts),
            "mapping_workflow_candidate_counts": mapping_workflow_candidate_counts,
            "first_party_api_rig_candidate_count": sum(first_party_api_rig_candidate_counts.values()),
            "first_party_api_rig_candidate_kinds": sorted(first_party_api_rig_candidate_counts),
            "first_party_api_rig_candidate_counts": first_party_api_rig_candidate_counts,
            "first_party_abstraction_host_candidate_count": sum(first_party_abstraction_host_candidate_counts.values()),
            "first_party_abstraction_host_candidate_kinds": sorted(first_party_abstraction_host_candidate_counts),
            "first_party_abstraction_host_candidate_counts": first_party_abstraction_host_candidate_counts,
            "first_party_abstraction_host_family_counts": first_party_abstraction_host_family_counts,
            "building_block_candidate_count": sum(building_block_candidate_counts.values()),
            "building_block_candidate_kinds": sorted(building_block_candidate_counts),
            "building_block_candidate_counts": building_block_candidate_counts,
            "maxclass_counts": analysis.get("maxclass_counts", {}),
            "object_name_counts": object_name_counts,
            "control_maxclass_counts": control_maxclass_counts,
            "control_unitstyle_counts": control_unitstyle_counts,
            "display_role_counts": knowledge["summary"].get("display_role_counts", {}),
            "motif_signature_counts": motif_signature_counts,
            "live_api_path_target_counts": live_api_path_target_counts,
            "live_api_property_counts": live_api_property_counts,
            "live_api_get_target_counts": live_api_get_target_counts,
            "live_api_set_target_counts": live_api_set_target_counts,
            "live_api_call_target_counts": live_api_call_target_counts,
            "live_api_archetype_counts": live_api_archetype_counts,
            "named_bus_network_count": knowledge["summary"].get("named_bus_network_count", 0),
            "cross_scope_named_bus_network_count": knowledge["summary"].get("cross_scope_named_bus_network_count", 0),
            "named_bus_network_names": named_bus_network_names,
            "cross_scope_named_bus_network_names": cross_scope_named_bus_network_names,
            "embedded_patcher_count": knowledge["summary"].get("embedded_patcher_count", 0),
            "embedded_pattern_count": knowledge["summary"].get("embedded_pattern_count", 0),
            "embedded_recipe_count": knowledge["summary"].get("embedded_recipe_count", 0),
            "embedded_motif_count": knowledge["summary"].get("embedded_motif_count", 0),
            "embedded_patcher_host_kind_counts": embedded_patcher_host_kind_counts,
            "embedded_pattern_kind_counts": embedded_pattern_kind_counts,
            "embedded_recipe_kind_counts": embedded_recipe_kind_counts,
            "embedded_motif_kind_counts": embedded_motif_kind_counts,
            "embedded_live_api_path_target_counts": embedded_live_api_path_target_counts,
            "embedded_live_api_property_counts": embedded_live_api_property_counts,
            "embedded_live_api_get_target_counts": embedded_live_api_get_target_counts,
            "embedded_live_api_set_target_counts": embedded_live_api_set_target_counts,
            "embedded_live_api_call_target_counts": embedded_live_api_call_target_counts,
            "embedded_live_api_archetype_counts": embedded_live_api_archetype_counts,
            "missing_support_files": len(missing_support_files),
            "missing_support_names": [
                entry.get("name")
                for entry in missing_support_files
                if entry.get("name")
            ],
        })
    except Exception as exc:  # pragma: no cover - covered by aggregate tests
        item.update({
            "status": "error",
            "error_type": type(exc).__name__,
            "error": f"{type(exc).__name__}: {exc}",
        })

    return item


__all__ = [
    "classify_corpus_source_metadata",
    "analyze_amxd_file",
]
