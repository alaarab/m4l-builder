"""Reference-device dossiers (semantic-lift analysis) and cross-corpus comparison.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from ._corpus_file import *  # noqa: F401,F403
from ._corpus_mapping import *  # noqa: F401,F403
from .reverse import (
    extract_embedded_patcher_snapshots,
    extract_gen_processing_candidates,
    extract_sample_buffer_candidates,
    extract_snapshot_knowledge,
    generate_builder_python_from_amxd,
    generate_semantic_python_from_amxd,
    snapshot_from_amxd,
)

SEMANTIC_HELPER_CALL_NAMES = (
    "controller_surface_shell",
    "sequencer_dispatch_shell",
    "embedded_ui_shell",
    "embedded_ui_shell_v2",
    "named_bus_router",
    "init_dispatch_chain",
    "poly_shell",
    "poly_shell_bank",
    "live_thisdevice",
    "live_parameter_probe",
    "live_observer",
    "live_state_observer",
    "live_set_control",
    "device_active_state",
)


def build_reference_device_dossier(path: str) -> dict:
    """Build a semantic-lifting dossier for one reference AMXD."""
    absolute_path = os.path.abspath(path)
    try:
        snapshot = snapshot_from_amxd(path)
        knowledge = extract_snapshot_knowledge(snapshot)
        builder_source = generate_builder_python_from_amxd(path)
        semantic_source = generate_semantic_python_from_amxd(path)
        item = analyze_amxd_file(path)
        product_brief = build_mapping_product_brief(item) if item.get("status") == "ok" else None
    except Exception as exc:
        return {
            "name": Path(path).name,
            "path": absolute_path,
            "error": f"{type(exc).__name__}: {exc}",
            "recovered_classes": [],
            "raw_add_box_count": 0,
            "semantic_add_box_count": 0,
            "semantic_add_box_delta": 0,
            "raw_add_line_count": 0,
            "semantic_add_line_count": 0,
            "semantic_add_line_delta": 0,
            "semantic_helper_call_count": 0,
            "semantic_helper_calls": {},
            "structural_lift_score": 0,
            "fallback_zones": ["analysis_error"],
            "product_brief": None,
        }

    def _count_raw_add_box(source: str) -> int:
        return source.count("device.add_box(")

    def _count_raw_add_line(source: str) -> int:
        return source.count("device.add_line(")

    def _semantic_helper_call_counts(source: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for name in SEMANTIC_HELPER_CALL_NAMES:
            count = source.count(f"{name}(")
            if count:
                counts[name] = count
        return counts

    raw_add_box_count = _count_raw_add_box(builder_source)
    semantic_add_box_count = _count_raw_add_box(semantic_source)
    raw_add_line_count = _count_raw_add_line(builder_source)
    semantic_add_line_count = _count_raw_add_line(semantic_source)
    semantic_helper_calls = _semantic_helper_call_counts(semantic_source)
    semantic_helper_call_count = sum(semantic_helper_calls.values())
    embedded_sample_buffer_candidates: dict[str, int] = {}
    embedded_gen_processing_candidates: dict[str, int] = {}
    for entry in extract_embedded_patcher_snapshots(snapshot):
        nested_snapshot = entry.get("snapshot", {})
        for candidate in extract_sample_buffer_candidates(nested_snapshot):
            candidate_name = candidate.get("candidate_name")
            if candidate_name:
                embedded_sample_buffer_candidates[candidate_name] = (
                    embedded_sample_buffer_candidates.get(candidate_name, 0) + 1
                )
        for candidate in extract_gen_processing_candidates(nested_snapshot):
            candidate_name = candidate.get("candidate_name")
            if candidate_name:
                embedded_gen_processing_candidates[candidate_name] = (
                    embedded_gen_processing_candidates.get(candidate_name, 0) + 1
                )

    recovered_classes = sorted({
        *(entry.get("candidate_name") for entry in knowledge.get("controller_shell_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("embedded_ui_shell_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("named_bus_router_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("init_dispatch_chain_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("state_bundle_router_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("sample_buffer_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("gen_processing_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("presentation_widget_cluster_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("poly_shell_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("poly_shell_bank_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("poly_editor_bank_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("mapping_semantic_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("mapping_workflow_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("first_party_api_rig_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("first_party_abstraction_host_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("first_party_abstraction_family_candidates", [])),
        *(entry.get("candidate_name") for entry in knowledge.get("building_block_candidates", [])),
        *embedded_sample_buffer_candidates.keys(),
        *embedded_gen_processing_candidates.keys(),
    } - {None})
    fallback_zones = []
    if _count_raw_add_box(semantic_source):
        fallback_zones.append("raw_box_fallback")
    if knowledge.get("lossiness", {}).get("missing_support_files"):
        fallback_zones.append("missing_support_files")
    if knowledge.get("summary", {}).get("live_api_helper_opportunity_count", 0) > 0:
        fallback_zones.append("live_api_manual_review")

    return {
        "name": Path(path).name,
        "path": absolute_path,
        "source": knowledge.get("source", {}),
        "device_type": snapshot.get("device", {}).get("device_type"),
        "box_count": snapshot.get("analysis", {}).get("box_count", 0),
        "line_count": snapshot.get("analysis", {}).get("line_count", 0),
        "recovered_classes": recovered_classes,
        "behavior_hints": [entry.get("name") for entry in knowledge.get("behavior_hints", []) if entry.get("name")],
        "mapping_behavior_traces": [entry.get("name") for entry in knowledge.get("mapping_behavior_traces", []) if entry.get("name")],
        "raw_add_box_count": raw_add_box_count,
        "semantic_add_box_count": semantic_add_box_count,
        "semantic_add_box_delta": raw_add_box_count - semantic_add_box_count,
        "raw_add_line_count": raw_add_line_count,
        "semantic_add_line_count": semantic_add_line_count,
        "semantic_add_line_delta": raw_add_line_count - semantic_add_line_count,
        "semantic_helper_call_count": semantic_helper_call_count,
        "semantic_helper_calls": semantic_helper_calls,
        "structural_lift_score": (
            (raw_add_box_count - semantic_add_box_count)
            + (raw_add_line_count - semantic_add_line_count)
            + semantic_helper_call_count
        ),
        "fallback_zones": fallback_zones,
        "product_brief": product_brief,
    }


def build_reference_device_dossiers(paths: Iterable[str]) -> list[dict]:
    """Build dossiers for a fixed reference-device proof set."""
    dossiers = [build_reference_device_dossier(path) for path in paths]
    dossiers.sort(key=lambda entry: entry["name"])
    return dossiers


def build_corpus_comparison(reports_by_label: dict[str, dict]) -> dict:
    """Build a compact comparison view across separately mined corpora."""
    comparisons = []
    for label, report in sorted(reports_by_label.items()):
        summary = report.get("summary", {})
        frequencies = report.get("frequencies", {})
        comparisons.append({
            "label": label,
            "count": summary.get("count", 0),
            "ok": summary.get("ok", 0),
            "error": summary.get("error", 0),
            "avg_boxes": summary.get("avg_box_count", 0.0),
            "avg_lines": summary.get("avg_line_count", 0.0),
            "top_motifs": frequencies.get("motif_signatures", [])[:5],
            "top_live_api_helpers": frequencies.get("live_api_helpers", [])[:5],
            "top_controller_shells": frequencies.get("controller_shell_candidates", [])[:5],
            "top_behavior_hints": frequencies.get("behavior_hints", [])[:5],
            "top_embedded_ui_shells": frequencies.get("embedded_ui_shell_candidates", [])[:5],
            "top_sample_buffer_candidates": frequencies.get("sample_buffer_candidates", [])[:5],
            "top_gen_processing_candidates": frequencies.get("gen_processing_candidates", [])[:5],
            "top_embedded_sample_buffer_candidates": frequencies.get("embedded_sample_buffer_candidates", [])[:5],
            "top_embedded_gen_processing_candidates": frequencies.get("embedded_gen_processing_candidates", [])[:5],
            "top_presentation_widget_clusters": frequencies.get("presentation_widget_cluster_candidates", [])[:5],
            "top_poly_shell_banks": frequencies.get("poly_shell_bank_candidates", [])[:5],
            "top_poly_editor_banks": frequencies.get("poly_editor_bank_candidates", [])[:5],
            "top_first_party_abstraction_hosts": frequencies.get("first_party_abstraction_host_candidates", [])[:5],
            "top_first_party_abstraction_families": frequencies.get("first_party_abstraction_host_families", [])[:5],
            "top_building_blocks": frequencies.get("building_block_candidates", [])[:5],
            "top_pack_sections": frequencies.get("pack_sections", [])[:5],
        })
    return {"reports": comparisons}


__all__ = [
    "SEMANTIC_HELPER_CALL_NAMES",
    "build_reference_device_dossier",
    "build_reference_device_dossiers",
    "build_corpus_comparison",
]
