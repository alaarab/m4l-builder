"""Top-level corpus orchestrator: walk a directory tree and aggregate metrics.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

from pathlib import Path
from statistics import mean

from ._corpus_file import *  # noqa: F401,F403
from ._corpus_helpers import *  # noqa: F401,F403
from ._corpus_ranking import *  # noqa: F401,F403


def analyze_amxd_corpus(path: str, *, recursive: bool = True) -> dict:
    """Analyze every `.amxd` file in a directory and aggregate corpus metrics."""
    root = Path(path).expanduser().resolve()
    discovered = sorted(root.rglob("*.amxd") if recursive else root.glob("*.amxd"))
    files = []
    seen_realpaths = set()
    for file_path in discovered:
        real_path = file_path.resolve()
        if str(real_path) in seen_realpaths:
            continue
        seen_realpaths.add(str(real_path))
        files.append(file_path)
    items = [analyze_amxd_file(str(file_path)) for file_path in files]
    ok_items = [item for item in items if item.get("status") == "ok"]

    device_type_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    error_type_counts: dict[str, int] = {}
    pattern_counts: dict[str, int] = {}
    recipe_counts: dict[str, int] = {}
    motif_counts: dict[str, int] = {}
    motif_signature_counts: dict[str, int] = {}
    maxclass_counts: dict[str, int] = {}
    object_name_counts: dict[str, int] = {}
    control_maxclass_counts: dict[str, int] = {}
    control_unitstyle_counts: dict[str, int] = {}
    display_role_counts: dict[str, int] = {}
    embedded_patcher_host_kind_counts: dict[str, int] = {}
    embedded_pattern_kind_counts: dict[str, int] = {}
    embedded_recipe_kind_counts: dict[str, int] = {}
    embedded_motif_kind_counts: dict[str, int] = {}
    live_api_path_target_counts: dict[str, int] = {}
    live_api_property_counts: dict[str, int] = {}
    live_api_get_target_counts: dict[str, int] = {}
    live_api_set_target_counts: dict[str, int] = {}
    live_api_call_target_counts: dict[str, int] = {}
    live_api_archetype_counts: dict[str, int] = {}
    named_bus_network_name_counts: dict[str, int] = {}
    cross_scope_named_bus_network_name_counts: dict[str, int] = {}
    live_api_helper_counts: dict[str, int] = {}
    live_api_normalization_level_counts: dict[str, int] = {}
    live_api_helper_opportunity_counts: dict[str, int] = {}
    live_api_helper_opportunity_blockers: dict[str, int] = {}
    controller_shell_candidate_counts: dict[str, int] = {}
    behavior_hint_counts: dict[str, int] = {}
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
    sample_buffer_candidate_counts: dict[str, int] = {}
    gen_processing_candidate_counts: dict[str, int] = {}
    embedded_sample_buffer_candidate_counts: dict[str, int] = {}
    embedded_gen_processing_candidate_counts: dict[str, int] = {}
    first_party_api_rig_candidate_counts: dict[str, int] = {}
    first_party_abstraction_host_candidate_counts: dict[str, int] = {}
    first_party_abstraction_host_family_counts: dict[str, int] = {}
    building_block_candidate_counts: dict[str, int] = {}
    embedded_live_api_path_target_counts: dict[str, int] = {}
    embedded_live_api_property_counts: dict[str, int] = {}
    embedded_live_api_get_target_counts: dict[str, int] = {}
    embedded_live_api_set_target_counts: dict[str, int] = {}
    embedded_live_api_call_target_counts: dict[str, int] = {}
    embedded_live_api_archetype_counts: dict[str, int] = {}
    missing_support_counts: dict[str, int] = {}
    source_lane_counts: dict[str, int] = {}
    source_family_counts: dict[str, int] = {}
    pack_name_counts: dict[str, int] = {}
    pack_section_counts: dict[str, int] = {}

    for item in items:
        if item.get("status") != "ok":
            error = item.get("error", "Unknown error")
            error_counts[error] = error_counts.get(error, 0) + 1
            error_type = item.get("error_type", "UnknownError")
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
            continue

        device_type = item.get("device_type", "unknown")
        device_type_counts[device_type] = device_type_counts.get(device_type, 0) + 1
        source_lane = item.get("source_lane")
        if source_lane:
            source_lane_counts[source_lane] = source_lane_counts.get(source_lane, 0) + 1
        source_family = item.get("source_family")
        if source_family:
            source_family_counts[source_family] = source_family_counts.get(source_family, 0) + 1
        pack_name = item.get("pack_name")
        if pack_name:
            pack_name_counts[pack_name] = pack_name_counts.get(pack_name, 0) + 1
        pack_section = item.get("pack_section")
        if pack_name and pack_section:
            section_name = f"{pack_name} / {pack_section}"
            pack_section_counts[section_name] = pack_section_counts.get(section_name, 0) + 1

        for kind in item.get("pattern_kinds", []):
            pattern_counts[kind] = pattern_counts.get(kind, 0) + 1
        for kind in item.get("recipe_kinds", []):
            recipe_counts[kind] = recipe_counts.get(kind, 0) + 1
        for kind in item.get("motif_kinds", []):
            motif_counts[kind] = motif_counts.get(kind, 0) + 1
        for signature, count in item.get("motif_signature_counts", {}).items():
            motif_signature_counts[signature] = motif_signature_counts.get(signature, 0) + int(count)
        for maxclass, count in item.get("maxclass_counts", {}).items():
            maxclass_counts[maxclass] = maxclass_counts.get(maxclass, 0) + int(count)
        for object_name, count in item.get("object_name_counts", {}).items():
            object_name_counts[object_name] = object_name_counts.get(object_name, 0) + int(count)
        for control_maxclass, count in item.get("control_maxclass_counts", {}).items():
            control_maxclass_counts[control_maxclass] = control_maxclass_counts.get(control_maxclass, 0) + int(count)
        for unitstyle, count in item.get("control_unitstyle_counts", {}).items():
            control_unitstyle_counts[unitstyle] = control_unitstyle_counts.get(unitstyle, 0) + int(count)
        for role, count in item.get("display_role_counts", {}).items():
            display_role_counts[role] = display_role_counts.get(role, 0) + int(count)
        for host_kind, count in item.get("embedded_patcher_host_kind_counts", {}).items():
            embedded_patcher_host_kind_counts[host_kind] = embedded_patcher_host_kind_counts.get(host_kind, 0) + int(count)
        for kind, count in item.get("embedded_pattern_kind_counts", {}).items():
            embedded_pattern_kind_counts[kind] = embedded_pattern_kind_counts.get(kind, 0) + int(count)
        for kind, count in item.get("embedded_recipe_kind_counts", {}).items():
            embedded_recipe_kind_counts[kind] = embedded_recipe_kind_counts.get(kind, 0) + int(count)
        for kind, count in item.get("embedded_motif_kind_counts", {}).items():
            embedded_motif_kind_counts[kind] = embedded_motif_kind_counts.get(kind, 0) + int(count)
        for target, count in item.get("live_api_path_target_counts", {}).items():
            live_api_path_target_counts[target] = live_api_path_target_counts.get(target, 0) + int(count)
        for prop, count in item.get("live_api_property_counts", {}).items():
            live_api_property_counts[prop] = live_api_property_counts.get(prop, 0) + int(count)
        for target, count in item.get("live_api_get_target_counts", {}).items():
            live_api_get_target_counts[target] = live_api_get_target_counts.get(target, 0) + int(count)
        for target, count in item.get("live_api_set_target_counts", {}).items():
            live_api_set_target_counts[target] = live_api_set_target_counts.get(target, 0) + int(count)
        for target, count in item.get("live_api_call_target_counts", {}).items():
            live_api_call_target_counts[target] = live_api_call_target_counts.get(target, 0) + int(count)
        for archetype, count in item.get("live_api_archetype_counts", {}).items():
            live_api_archetype_counts[archetype] = live_api_archetype_counts.get(archetype, 0) + int(count)
        for name, count in item.get("named_bus_network_names", {}).items():
            named_bus_network_name_counts[name] = named_bus_network_name_counts.get(name, 0) + int(count)
        for name, count in item.get("cross_scope_named_bus_network_names", {}).items():
            cross_scope_named_bus_network_name_counts[name] = cross_scope_named_bus_network_name_counts.get(name, 0) + int(count)
        for helper_name, count in item.get("live_api_helper_counts", {}).items():
            live_api_helper_counts[helper_name] = live_api_helper_counts.get(helper_name, 0) + int(count)
        for level, count in item.get("live_api_normalization_level_counts", {}).items():
            live_api_normalization_level_counts[level] = live_api_normalization_level_counts.get(level, 0) + int(count)
        for helper_name, count in item.get("live_api_helper_opportunity_counts", {}).items():
            live_api_helper_opportunity_counts[helper_name] = live_api_helper_opportunity_counts.get(helper_name, 0) + int(count)
        for blocker, count in item.get("live_api_helper_opportunity_blockers", {}).items():
            live_api_helper_opportunity_blockers[blocker] = live_api_helper_opportunity_blockers.get(blocker, 0) + int(count)
        for candidate_name, count in item.get("controller_shell_candidate_counts", {}).items():
            controller_shell_candidate_counts[candidate_name] = controller_shell_candidate_counts.get(candidate_name, 0) + int(count)
        for hint_name, count in item.get("behavior_hint_counts", {}).items():
            behavior_hint_counts[hint_name] = behavior_hint_counts.get(hint_name, 0) + int(count)
        for trace_name, count in item.get("mapping_behavior_trace_counts", {}).items():
            mapping_behavior_trace_counts[trace_name] = mapping_behavior_trace_counts.get(trace_name, 0) + int(count)
        for candidate_name, count in item.get("embedded_ui_shell_candidate_counts", {}).items():
            embedded_ui_shell_candidate_counts[candidate_name] = embedded_ui_shell_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("named_bus_router_candidate_counts", {}).items():
            named_bus_router_candidate_counts[candidate_name] = named_bus_router_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("init_dispatch_chain_candidate_counts", {}).items():
            init_dispatch_chain_candidate_counts[candidate_name] = init_dispatch_chain_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("state_bundle_router_candidate_counts", {}).items():
            state_bundle_router_candidate_counts[candidate_name] = state_bundle_router_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("presentation_widget_cluster_candidate_counts", {}).items():
            presentation_widget_cluster_candidate_counts[candidate_name] = presentation_widget_cluster_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("poly_shell_candidate_counts", {}).items():
            poly_shell_candidate_counts[candidate_name] = poly_shell_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("poly_shell_bank_candidate_counts", {}).items():
            poly_shell_bank_candidate_counts[candidate_name] = poly_shell_bank_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("poly_editor_bank_candidate_counts", {}).items():
            poly_editor_bank_candidate_counts[candidate_name] = poly_editor_bank_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("mapping_semantic_candidate_counts", {}).items():
            mapping_semantic_candidate_counts[candidate_name] = mapping_semantic_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("mapping_workflow_candidate_counts", {}).items():
            mapping_workflow_candidate_counts[candidate_name] = mapping_workflow_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("sample_buffer_candidate_counts", {}).items():
            sample_buffer_candidate_counts[candidate_name] = sample_buffer_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("gen_processing_candidate_counts", {}).items():
            gen_processing_candidate_counts[candidate_name] = gen_processing_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("embedded_sample_buffer_candidate_counts", {}).items():
            embedded_sample_buffer_candidate_counts[candidate_name] = embedded_sample_buffer_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("embedded_gen_processing_candidate_counts", {}).items():
            embedded_gen_processing_candidate_counts[candidate_name] = embedded_gen_processing_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("first_party_api_rig_candidate_counts", {}).items():
            first_party_api_rig_candidate_counts[candidate_name] = first_party_api_rig_candidate_counts.get(candidate_name, 0) + int(count)
        for candidate_name, count in item.get("first_party_abstraction_host_candidate_counts", {}).items():
            first_party_abstraction_host_candidate_counts[candidate_name] = first_party_abstraction_host_candidate_counts.get(candidate_name, 0) + int(count)
        for family_name, count in item.get("first_party_abstraction_host_family_counts", {}).items():
            first_party_abstraction_host_family_counts[family_name] = first_party_abstraction_host_family_counts.get(family_name, 0) + int(count)
        for candidate_name, count in item.get("building_block_candidate_counts", {}).items():
            building_block_candidate_counts[candidate_name] = building_block_candidate_counts.get(candidate_name, 0) + int(count)
        for target, count in item.get("embedded_live_api_path_target_counts", {}).items():
            embedded_live_api_path_target_counts[target] = embedded_live_api_path_target_counts.get(target, 0) + int(count)
        for prop, count in item.get("embedded_live_api_property_counts", {}).items():
            embedded_live_api_property_counts[prop] = embedded_live_api_property_counts.get(prop, 0) + int(count)
        for target, count in item.get("embedded_live_api_get_target_counts", {}).items():
            embedded_live_api_get_target_counts[target] = embedded_live_api_get_target_counts.get(target, 0) + int(count)
        for target, count in item.get("embedded_live_api_set_target_counts", {}).items():
            embedded_live_api_set_target_counts[target] = embedded_live_api_set_target_counts.get(target, 0) + int(count)
        for target, count in item.get("embedded_live_api_call_target_counts", {}).items():
            embedded_live_api_call_target_counts[target] = embedded_live_api_call_target_counts.get(target, 0) + int(count)
        for archetype, count in item.get("embedded_live_api_archetype_counts", {}).items():
            embedded_live_api_archetype_counts[archetype] = embedded_live_api_archetype_counts.get(archetype, 0) + int(count)
        for name in item.get("missing_support_names", []):
            missing_support_counts[name] = missing_support_counts.get(name, 0) + 1

    summary = {
        "count": len(items),
        "ok": len(ok_items),
        "error": len(items) - len(ok_items),
        "device_types": device_type_counts,
        "source_lanes": source_lane_counts,
        "bridge_enabled_files": sum(1 for item in ok_items if item.get("bridge_enabled")),
        "files_with_patterns": sum(1 for item in ok_items if item.get("pattern_count", 0) > 0),
        "files_with_recipes": sum(1 for item in ok_items if item.get("recipe_count", 0) > 0),
        "files_with_motifs": sum(1 for item in ok_items if item.get("motif_count", 0) > 0),
        "files_with_named_bus_networks": sum(1 for item in ok_items if item.get("named_bus_network_count", 0) > 0),
        "files_with_cross_scope_named_bus_networks": sum(1 for item in ok_items if item.get("cross_scope_named_bus_network_count", 0) > 0),
        "files_with_live_api_helpers": sum(1 for item in ok_items if item.get("live_api_helper_count", 0) > 0),
        "files_with_live_api_helper_opportunities": sum(1 for item in ok_items if item.get("live_api_helper_opportunity_count", 0) > 0),
        "files_with_controller_shell_candidates": sum(1 for item in ok_items if item.get("controller_shell_candidate_count", 0) > 0),
        "files_with_behavior_hints": sum(1 for item in ok_items if item.get("behavior_hint_count", 0) > 0),
        "files_with_mapping_behavior_traces": sum(1 for item in ok_items if item.get("mapping_behavior_trace_count", 0) > 0),
        "files_with_embedded_ui_shell_candidates": sum(1 for item in ok_items if item.get("embedded_ui_shell_candidate_count", 0) > 0),
        "files_with_named_bus_router_candidates": sum(1 for item in ok_items if item.get("named_bus_router_candidate_count", 0) > 0),
        "files_with_init_dispatch_chain_candidates": sum(1 for item in ok_items if item.get("init_dispatch_chain_candidate_count", 0) > 0),
        "files_with_state_bundle_router_candidates": sum(1 for item in ok_items if item.get("state_bundle_router_candidate_count", 0) > 0),
        "files_with_presentation_widget_cluster_candidates": sum(1 for item in ok_items if item.get("presentation_widget_cluster_candidate_count", 0) > 0),
        "files_with_poly_shell_candidates": sum(1 for item in ok_items if item.get("poly_shell_candidate_count", 0) > 0),
        "files_with_poly_shell_bank_candidates": sum(1 for item in ok_items if item.get("poly_shell_bank_candidate_count", 0) > 0),
        "files_with_poly_editor_bank_candidates": sum(1 for item in ok_items if item.get("poly_editor_bank_candidate_count", 0) > 0),
        "files_with_mapping_semantic_candidates": sum(1 for item in ok_items if item.get("mapping_semantic_candidate_count", 0) > 0),
        "files_with_mapping_workflow_candidates": sum(1 for item in ok_items if item.get("mapping_workflow_candidate_count", 0) > 0),
        "files_with_sample_buffer_candidates": sum(1 for item in ok_items if item.get("sample_buffer_candidate_count", 0) > 0),
        "files_with_gen_processing_candidates": sum(1 for item in ok_items if item.get("gen_processing_candidate_count", 0) > 0),
        "files_with_embedded_sample_buffer_candidates": sum(1 for item in ok_items if item.get("embedded_sample_buffer_candidate_count", 0) > 0),
        "files_with_embedded_gen_processing_candidates": sum(1 for item in ok_items if item.get("embedded_gen_processing_candidate_count", 0) > 0),
        "files_with_first_party_api_rig_candidates": sum(1 for item in ok_items if item.get("first_party_api_rig_candidate_count", 0) > 0),
        "files_with_first_party_abstraction_host_candidates": sum(1 for item in ok_items if item.get("first_party_abstraction_host_candidate_count", 0) > 0),
        "files_with_building_block_candidates": sum(1 for item in ok_items if item.get("building_block_candidate_count", 0) > 0),
        "files_with_embedded_patchers": sum(1 for item in ok_items if item.get("embedded_patcher_count", 0) > 0),
        "files_with_embedded_patterns": sum(1 for item in ok_items if item.get("embedded_pattern_count", 0) > 0),
        "files_with_embedded_recipes": sum(1 for item in ok_items if item.get("embedded_recipe_count", 0) > 0),
        "files_with_embedded_motifs": sum(1 for item in ok_items if item.get("embedded_motif_count", 0) > 0),
        "files_with_missing_support_files": sum(1 for item in ok_items if item.get("missing_support_files", 0) > 0),
        "avg_box_count": round(mean(item.get("box_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_line_count": round(mean(item.get("line_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_control_count": round(mean(item.get("control_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_display_count": round(mean(item.get("display_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_embedded_patcher_count": round(mean(item.get("embedded_patcher_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_embedded_pattern_count": round(mean(item.get("embedded_pattern_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_embedded_recipe_count": round(mean(item.get("embedded_recipe_count", 0) for item in ok_items), 2) if ok_items else 0.0,
        "avg_embedded_motif_count": round(mean(item.get("embedded_motif_count", 0) for item in ok_items), 2) if ok_items else 0.0,
    }

    report = {
        "corpus": {
            "root": str(root),
            "recursive": recursive,
            "file_count": len(files),
        },
        "summary": summary,
        "frequencies": {
            "patterns": _sorted_frequency(pattern_counts),
            "recipes": _sorted_frequency(recipe_counts),
            "motifs": _sorted_frequency(motif_counts),
            "motif_signatures": _sorted_frequency(motif_signature_counts),
            "maxclasses": _sorted_frequency(maxclass_counts),
            "object_names": _sorted_frequency(object_name_counts),
            "control_maxclasses": _sorted_frequency(control_maxclass_counts),
            "control_unitstyles": _sorted_frequency(control_unitstyle_counts),
            "display_roles": _sorted_frequency(display_role_counts),
            "embedded_patcher_host_kinds": _sorted_frequency(embedded_patcher_host_kind_counts),
            "embedded_patterns": _sorted_frequency(embedded_pattern_kind_counts),
            "embedded_recipes": _sorted_frequency(embedded_recipe_kind_counts),
            "embedded_motifs": _sorted_frequency(embedded_motif_kind_counts),
            "live_api_path_targets": _sorted_frequency(live_api_path_target_counts),
            "live_api_properties": _sorted_frequency(live_api_property_counts),
            "live_api_get_targets": _sorted_frequency(live_api_get_target_counts),
            "live_api_set_targets": _sorted_frequency(live_api_set_target_counts),
            "live_api_call_targets": _sorted_frequency(live_api_call_target_counts),
            "live_api_archetypes": _sorted_frequency(live_api_archetype_counts),
            "named_bus_network_names": _sorted_frequency(named_bus_network_name_counts),
            "cross_scope_named_bus_network_names": _sorted_frequency(cross_scope_named_bus_network_name_counts),
            "live_api_helpers": _sorted_frequency(live_api_helper_counts),
            "live_api_normalization_levels": _sorted_frequency(live_api_normalization_level_counts),
            "live_api_helper_opportunities": _sorted_frequency(live_api_helper_opportunity_counts),
            "live_api_helper_opportunity_blockers": _sorted_frequency(live_api_helper_opportunity_blockers),
            "controller_shell_candidates": _sorted_frequency(controller_shell_candidate_counts),
            "behavior_hints": _sorted_frequency(behavior_hint_counts),
            "mapping_behavior_traces": _sorted_frequency(mapping_behavior_trace_counts),
            "embedded_ui_shell_candidates": _sorted_frequency(embedded_ui_shell_candidate_counts),
            "named_bus_router_candidates": _sorted_frequency(named_bus_router_candidate_counts),
            "init_dispatch_chain_candidates": _sorted_frequency(init_dispatch_chain_candidate_counts),
            "state_bundle_router_candidates": _sorted_frequency(state_bundle_router_candidate_counts),
            "presentation_widget_cluster_candidates": _sorted_frequency(presentation_widget_cluster_candidate_counts),
            "poly_shell_candidates": _sorted_frequency(poly_shell_candidate_counts),
            "poly_shell_bank_candidates": _sorted_frequency(poly_shell_bank_candidate_counts),
            "poly_editor_bank_candidates": _sorted_frequency(poly_editor_bank_candidate_counts),
            "mapping_semantic_candidates": _sorted_frequency(mapping_semantic_candidate_counts),
            "mapping_workflow_candidates": _sorted_frequency(mapping_workflow_candidate_counts),
            "sample_buffer_candidates": _sorted_frequency(sample_buffer_candidate_counts),
            "gen_processing_candidates": _sorted_frequency(gen_processing_candidate_counts),
            "embedded_sample_buffer_candidates": _sorted_frequency(embedded_sample_buffer_candidate_counts),
            "embedded_gen_processing_candidates": _sorted_frequency(embedded_gen_processing_candidate_counts),
            "first_party_api_rig_candidates": _sorted_frequency(first_party_api_rig_candidate_counts),
            "first_party_abstraction_host_candidates": _sorted_frequency(first_party_abstraction_host_candidate_counts),
            "first_party_abstraction_host_families": _sorted_frequency(first_party_abstraction_host_family_counts),
            "building_block_candidates": _sorted_frequency(building_block_candidate_counts),
            "embedded_live_api_path_targets": _sorted_frequency(embedded_live_api_path_target_counts),
            "embedded_live_api_properties": _sorted_frequency(embedded_live_api_property_counts),
            "embedded_live_api_get_targets": _sorted_frequency(embedded_live_api_get_target_counts),
            "embedded_live_api_set_targets": _sorted_frequency(embedded_live_api_set_target_counts),
            "embedded_live_api_call_targets": _sorted_frequency(embedded_live_api_call_target_counts),
            "embedded_live_api_archetypes": _sorted_frequency(embedded_live_api_archetype_counts),
            "error_types": _sorted_frequency(error_type_counts),
            "errors": _sorted_frequency(error_counts),
            "missing_support_files": _sorted_frequency(missing_support_counts),
            "source_lanes": _sorted_frequency(source_lane_counts),
            "source_families": _sorted_frequency(source_family_counts),
            "pack_names": _sorted_frequency(pack_name_counts),
            "pack_sections": _sorted_frequency(pack_section_counts),
        },
        "largest_devices": {
            "by_boxes": _top_items(ok_items, "box_count"),
            "by_lines": _top_items(ok_items, "line_count"),
        },
        "items": items,
    }
    report["reverse_candidates"] = rank_reverse_candidates(report)
    report["reverse_candidate_families"] = rank_reverse_candidate_families(report)
    report["reverse_candidate_family_profiles"] = build_reverse_candidate_family_profiles(report)
    report["source_lane_profiles"] = build_source_lane_profiles(report)
    return report


__all__ = [
    "analyze_amxd_corpus",
]
