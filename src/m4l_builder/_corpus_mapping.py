"""Mapping/modulation-lane product-brief construction and ranking.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

from ._corpus_file import *  # noqa: F401,F403
from ._corpus_helpers import *  # noqa: F401,F403


def _mapping_product_profile(item: dict) -> dict:
    semantic_counts = item.get("mapping_semantic_candidate_counts", {})
    trace_counts = item.get("mapping_behavior_trace_counts", {})
    hint_counts = item.get("behavior_hint_counts", {})
    missing_support = int(item.get("missing_support_files", 0))

    if semantic_counts.get("triggered_parameter_mapper", 0) > 0:
        return {
            "product_class": "parameter_mapper",
            "closest_reference": "Rnd Gen-style mapper",
            "essential_controls": [
                "lane count",
                "target assignment",
                "trigger mode",
                "random range/depth/shape",
                "smoothing/probability",
                "mapping session controls",
            ],
            "accidental_complexity": [
                entry
                for entry in [
                    "repeated poly editor shells",
                    "indexed bus naming",
                    "panel relayout scripting" if hint_counts.get("dynamic_panel_relayout", 0) else None,
                    "hidden sidecar mapping engine" if trace_counts.get("hidden_mapping_engine", 0) or missing_support else None,
                ]
                if entry
            ],
        }
    if semantic_counts.get("device_parameter_randomizer", 0) > 0:
        return {
            "product_class": "parameter_randomizer",
            "closest_reference": "Device Randomizer-style device",
            "essential_controls": [
                "target device scope",
                "trigger mode",
                "random amount/range",
                "parameter include/exclude rules",
                "store or recall settings",
            ],
            "accidental_complexity": [
                "selected-device tracking buses",
                "parameter enumeration and filtering shells",
                "settings storage plumbing",
            ],
        }
    if semantic_counts.get("random_modulation_mapper", 0) > 0:
        return {
            "product_class": "random_modulation_source",
            "closest_reference": "Macro Randomizer-style device",
            "essential_controls": [
                "output lanes",
                "trigger mode",
                "rate or clocking",
                "random range/depth/shape",
                "smoothing/probability",
            ],
            "accidental_complexity": [
                "fan-out trigger plumbing",
                "low-level random/scaling objects",
            ],
        }
    if semantic_counts.get("lfo_modulation_source", 0) > 0:
        return {
            "product_class": "lfo_modulation_source",
            "closest_reference": "LFO MIDI-style device",
            "essential_controls": [
                "waveform",
                "rate or sync",
                "depth or amount",
                "smoothing or jitter",
                "hold or retrigger behavior",
                "target output routing",
            ],
            "accidental_complexity": [
                "oscilloscope UI plumbing",
                "time-mode and sync shells",
                "waveform selector internals",
            ],
        }
    if semantic_counts.get("mapped_modulation_bank", 0) > 0:
        return {
            "product_class": "modulation_bank",
            "closest_reference": "Expression Control-style bank",
            "essential_controls": [
                "lane count",
                "lane labels",
                "output range",
            ],
            "accidental_complexity": [
                "per-lane output adapters",
            ],
        }
    if item.get("mapping_workflow_candidate_count", 0) > 0:
        return {
            "product_class": "mapping_workflow",
            "closest_reference": "mapping workflow shell",
            "essential_controls": [
                "lane count",
                "trigger mode",
                "mapping session controls",
            ],
            "accidental_complexity": [
                "workflow shell plumbing",
            ],
        }
    return {
        "product_class": "unknown",
        "closest_reference": "unknown",
        "essential_controls": [],
        "accidental_complexity": [],
    }


def _mapping_product_brief(item: dict) -> dict:
    """Build a product-level brief for a mapping/modulation-oriented device."""
    profile = _mapping_product_profile(item)
    product_class = profile["product_class"]
    trace_counts = item.get("mapping_behavior_trace_counts", {})
    hint_counts = item.get("behavior_hint_counts", {})
    semantic_counts = item.get("mapping_semantic_candidate_counts", {})
    workflow_counts = item.get("mapping_workflow_candidate_counts", {})
    missing_support = bool(item.get("missing_support_files"))

    confidence = "low"
    if product_class != "unknown":
        confidence = "high"
    elif item.get("mapping_workflow_candidate_count", 0) > 0:
        confidence = "medium"

    open_questions: list[str] = []
    if trace_counts.get("hidden_mapping_engine", 0) or missing_support:
        open_questions.append("exact value-generation and shaping may live in unresolved sidecars")
    if product_class == "parameter_mapper" and not trace_counts.get("random_value_generation", 0):
        open_questions.append("randomization algorithm is inferred from workflow shape more than fully visible internals")
    if product_class == "parameter_randomizer" and not semantic_counts.get("device_parameter_randomizer", 0):
        open_questions.append("parameter-scan shell is present, but parameter eligibility rules are still partially implicit")
    if product_class == "mapping_workflow":
        open_questions.append("workflow shell is clear, but the value model is not yet stable enough to classify further")

    if product_class == "parameter_mapper":
        thesis = "Triggered mapping workflow that assigns and updates target parameters across multiple lanes."
        value_model = "Fresh lane values are produced on trigger and pushed through per-lane update paths; exact shaping may be partly hidden behind sidecars."
        target_model = "Targets are assigned per lane through an explicit mapping session and stored as indexed lane routing."
        trigger_model = "Manual and MIDI-triggered, with optional scheduled refresh if the patch adds it."
        essential_subsystems = [
            "lane bank",
            "target assignment workflow",
            "trigger router",
            "mapping-session state",
            "lane update engine",
        ]
        build_cleanly_as = "A lane-based mapper with explicit map/start/done/refresh state and a single clear per-lane randomization stage."
    elif product_class == "parameter_randomizer":
        thesis = "Selected-device controller that scans parameters and applies randomized updates under explicit trigger rules."
        value_model = "Random values are generated against discovered parameters, usually with include/exclude filtering and stored settings."
        target_model = "Targets come from the current device or a filtered parameter list rather than fixed exposed lanes."
        trigger_model = "User-triggered or scheduled randomize actions, often with store/recall or edit-state gating."
        essential_subsystems = [
            "selected-device tracker",
            "parameter scanner/filter",
            "random value engine",
            "settings store and recall",
        ]
        build_cleanly_as = "A parameter-scoped randomizer with a clean selected-device model and explicit parameter-filtering rules."
    elif product_class == "random_modulation_source":
        thesis = "Bank of output lanes that emits fresh random values on demand or on a schedule."
        value_model = "Visible random generators and scaling stages create new lane values each trigger cycle."
        target_model = "Targets are fixed output lanes rather than a dynamic parameter-assignment workflow."
        trigger_model = "Manual, clocked, or free-running triggers fan out into per-lane random generation."
        essential_subsystems = [
            "output lane bank",
            "trigger distributor",
            "random generator/scaler",
        ]
        build_cleanly_as = "A simple random-output bank with one shared trigger clock and one normalized value-shaping path per lane."
    elif product_class == "lfo_modulation_source":
        thesis = "Periodic waveform modulation source with sync/time controls and a shaped modulation output path."
        value_model = "Waveform cores generate continuous modulation, then hold/smoothing stages shape it before output."
        target_model = "Targets are modulation outputs or routed destinations, not a parameter-mapping session."
        trigger_model = "Rate, sync, and retrigger behavior govern the periodic engine rather than discrete randomize actions."
        essential_subsystems = [
            "periodic waveform core",
            "sync/time-mode shell",
            "hold or smoothing stage",
            "output routing",
        ]
        build_cleanly_as = "A modulation source centered on one clean waveform core, one timing model, and one output-routing layer."
    elif product_class == "modulation_bank":
        thesis = "Stable bank of exposed modulation outputs with minimal internal decision-making."
        value_model = "Values mostly come from user controls or upstream modulators rather than a built-in generator."
        target_model = "Targets are fixed exposed lanes or direct macro-style outputs."
        trigger_model = "Primarily manual or upstream-driven; little or no internal trigger engine is required."
        essential_subsystems = [
            "lane bank",
            "output adapters",
        ]
        build_cleanly_as = "A compact exposed-lane bank with clean labeling and predictable output scaling."
    elif product_class == "mapping_workflow":
        thesis = "Mapping-session shell around lane editors whose trigger and assignment logic is clearer than its value-generation internals."
        value_model = "Likely a mapper-style engine, but the exact value-generation path is still partially unresolved."
        target_model = "Per-lane assignment and workflow state are more visible than the final modulation source."
        trigger_model = "Workflow-driven map/start/done/refresh actions are the main visible control surface."
        essential_subsystems = [
            "lane editor bank",
            "mapping-session controller",
            "trigger/session buses",
        ]
        build_cleanly_as = "A map-session shell separated cleanly from whichever value engine ultimately drives it."
    else:
        thesis = "Mapping or modulation signals are present, but the product-level role is still ambiguous."
        value_model = "Some control or modulation traces exist, but not enough to safely collapse the device into a stable product family."
        target_model = "Targeting model is not yet stable."
        trigger_model = "Trigger model is not yet stable."
        essential_subsystems = []
        build_cleanly_as = "A raw reverse candidate that still needs proof-set validation before it becomes a design reference."

    return {
        "name": item.get("name"),
        "path": item.get("path"),
        "source_lane": item.get("source_lane"),
        "source_family": item.get("source_family"),
        "pack_name": item.get("pack_name"),
        "pack_section": item.get("pack_section"),
        "pack_subsection": item.get("pack_subsection"),
        "device_type": item.get("device_type"),
        "product_class": product_class,
        "closest_reference": profile["closest_reference"],
        "product_thesis": thesis,
        "value_model": value_model,
        "target_model": target_model,
        "trigger_model": trigger_model,
        "essential_controls": profile["essential_controls"],
        "essential_subsystems": essential_subsystems,
        "accidental_complexity": profile["accidental_complexity"],
        "build_cleanly_as": build_cleanly_as,
        "behavior_hints": sorted(hint_counts),
        "mapping_behavior_traces": sorted(trace_counts),
        "mapping_semantic_candidates": sorted(semantic_counts),
        "mapping_workflow_candidates": sorted(workflow_counts),
        "open_questions": open_questions,
        "confidence": confidence,
    }


def _mapping_candidate_score(item: dict) -> int:
    """Return the ranking score for one mapping/modulation-oriented device."""
    semantic_counts = item.get("mapping_semantic_candidate_counts", {})
    return (
        semantic_counts.get("triggered_parameter_mapper", 0) * 100
        + semantic_counts.get("device_parameter_randomizer", 0) * 85
        + semantic_counts.get("random_modulation_mapper", 0) * 70
        + semantic_counts.get("lfo_modulation_source", 0) * 60
        + semantic_counts.get("mapped_modulation_bank", 0) * 40
        + item.get("mapping_workflow_candidate_count", 0) * 20
        + item.get("mapping_behavior_trace_count", 0) * 5
        + item.get("behavior_hint_count", 0) * 3
    )


def rank_mapping_candidates(report: dict, *, limit: int = 20) -> list[dict]:
    """Rank mapping/modulation-oriented devices within a corpus report."""
    ranked = []
    for item in report.get("items", []):
        if item.get("status") != "ok":
            continue
        trace_counts = item.get("mapping_behavior_trace_counts", {})
        hint_counts = item.get("behavior_hint_counts", {})
        semantic_counts = item.get("mapping_semantic_candidate_counts", {})
        if not (semantic_counts or trace_counts or hint_counts):
            continue
        brief = _mapping_product_brief(item)
        brief["score"] = _mapping_candidate_score(item)
        ranked.append(brief)
    ranked.sort(key=lambda entry: (-entry["score"], entry["product_class"], entry["name"]))
    return ranked[:limit]


def build_mapping_lane_report(report: dict, *, limit: int = 20) -> dict:
    """Build a focused report for mapping/modulation-oriented devices."""
    items = [
        item
        for item in report.get("items", [])
        if item.get("status") == "ok"
        and (
            item.get("mapping_semantic_candidate_count", 0) > 0
            or item.get("mapping_behavior_trace_count", 0) > 0
            or item.get("behavior_hint_count", 0) > 0
            or item.get("mapping_workflow_candidate_count", 0) > 0
        )
    ]
    product_class_counts: dict[str, int] = {}
    closest_reference_counts: dict[str, int] = {}
    source_family_counts: dict[str, int] = {}
    source_lane_counts: dict[str, int] = {}
    behavior_trace_counts: dict[str, int] = {}
    semantic_candidate_counts: dict[str, int] = {}
    behavior_hint_counts: dict[str, int] = {}

    for item in items:
        profile = _mapping_product_profile(item)
        product_class_counts[profile["product_class"]] = product_class_counts.get(profile["product_class"], 0) + 1
        closest_reference_counts[profile["closest_reference"]] = closest_reference_counts.get(profile["closest_reference"], 0) + 1
        source_family = item.get("source_family")
        if source_family:
            source_family_counts[source_family] = source_family_counts.get(source_family, 0) + 1
        source_lane = item.get("source_lane")
        if source_lane:
            source_lane_counts[source_lane] = source_lane_counts.get(source_lane, 0) + 1
        for name, count in item.get("mapping_behavior_trace_counts", {}).items():
            behavior_trace_counts[name] = behavior_trace_counts.get(name, 0) + int(count)
        for name, count in item.get("mapping_semantic_candidate_counts", {}).items():
            semantic_candidate_counts[name] = semantic_candidate_counts.get(name, 0) + int(count)
        for name, count in item.get("behavior_hint_counts", {}).items():
            behavior_hint_counts[name] = behavior_hint_counts.get(name, 0) + int(count)

    return {
        "summary": {
            "count": len(items),
            "files_with_behavior_hints": sum(1 for item in items if item.get("behavior_hint_count", 0) > 0),
            "files_with_mapping_behavior_traces": sum(1 for item in items if item.get("mapping_behavior_trace_count", 0) > 0),
            "files_with_mapping_semantic_candidates": sum(1 for item in items if item.get("mapping_semantic_candidate_count", 0) > 0),
            "files_with_mapping_workflow_candidates": sum(1 for item in items if item.get("mapping_workflow_candidate_count", 0) > 0),
        },
        "product_classes": _sorted_frequency(product_class_counts),
        "closest_references": _sorted_frequency(closest_reference_counts),
        "source_families": _sorted_frequency(source_family_counts),
        "source_lanes": _sorted_frequency(source_lane_counts),
        "behavior_hints": _sorted_frequency(behavior_hint_counts),
        "mapping_behavior_traces": _sorted_frequency(behavior_trace_counts),
        "mapping_semantic_candidates": _sorted_frequency(semantic_candidate_counts),
        "top_devices": rank_mapping_candidates(report, limit=limit),
    }


def build_mapping_product_brief(item: dict) -> dict:
    """Build one product-level brief from a mined corpus item."""
    brief = _mapping_product_brief(item)
    brief["score"] = _mapping_candidate_score(item)
    return brief


def build_mapping_product_brief_from_path(path: str) -> dict:
    """Build one product-level brief directly from an AMXD path."""
    item = analyze_amxd_file(path)
    if item.get("status") != "ok":
        raise ValueError(f"Could not analyze AMXD: {path}")
    return build_mapping_product_brief(item)


def build_mapping_product_briefs(
    report: dict,
    *,
    limit: int = 20,
    include_unknown: bool = False,
) -> list[dict]:
    """Build ordered product-level briefs for the mapping/modulation lane."""
    briefs = rank_mapping_candidates(report, limit=max(limit * 5, limit))
    if not include_unknown:
        briefs = [brief for brief in briefs if brief.get("product_class") != "unknown"]
    return briefs[:limit]


__all__ = [
    "_mapping_product_profile",
    "_mapping_product_brief",
    "_mapping_candidate_score",
    "rank_mapping_candidates",
    "build_mapping_lane_report",
    "build_mapping_product_brief",
    "build_mapping_product_brief_from_path",
    "build_mapping_product_briefs",
]
