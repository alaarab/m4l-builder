"""Reverse-candidate ranking, family profiling, and source-lane profiling.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

from statistics import mean

from ._corpus_helpers import *  # noqa: F401,F403


def _infer_family_semantic_targets(profile: dict) -> tuple[list[dict], list[str]]:
    stable_motif_entries = profile.get("stable_signals", {}).get("motif_signatures", [])
    stable_motif_names = _names_by_coverage(stable_motif_entries, 1.0)
    stable_object_names = _names_by_coverage(profile.get("stable_signals", {}).get("object_names", []), 1.0)
    stable_poly_shell_banks = _names_by_coverage(profile.get("stable_signals", {}).get("poly_shell_banks", []), 1.0)
    stable_poly_editor_banks = _names_by_coverage(profile.get("stable_signals", {}).get("poly_editor_banks", []), 1.0)
    stable_behavior_hints = _names_by_coverage(profile.get("stable_signals", {}).get("behavior_hints", []), 1.0)
    variable_live_api = profile.get("variable_signals", {}).get("live_api_archetypes", [])
    stable_named_buses = profile.get("stable_signals", {}).get("named_bus_network_names", [])
    variable_named_buses = profile.get("variable_signals", {}).get("named_bus_network_names", [])
    stable_embedded_hosts = _names_by_coverage(profile.get("stable_signals", {}).get("embedded_host_kinds", []), 1.0)
    stable_live_api = _names_by_coverage(profile.get("stable_signals", {}).get("live_api_archetypes", []), 1.0)
    has_stable_route_dispatch = _has_stable_dispatch_operator(stable_motif_entries, "route")
    has_stable_sel_dispatch = _has_stable_dispatch_operator(stable_motif_entries, "sel")
    has_stable_gate_dispatch = _has_stable_dispatch_operator(stable_motif_entries, "gate")

    targets: list[dict] = []
    next_work: list[str] = []

    if "mapped_random_control_device" in stable_behavior_hints:
        targets.append({
            "name": "mapped_random_control_device",
            "confidence": 0.97,
            "evidence": [
                "stable product-level behavior hint: mapped_random_control_device",
            ],
        })
        next_work.append(
            "Trace the hidden sidecar logic behind the stable mapped-random-control shell so future rebuilds can target behavior, not just structure."
        )

    if stable_poly_editor_banks:
        targets.append({
            "name": "poly_editor_bank",
            "confidence": 0.96,
            "evidence": [
                f"stable editor-bank candidates: {', '.join(sorted(stable_poly_editor_banks))}",
            ],
        })
        next_work.append(
            "Generalize the repeated voice-editor-bank structure into reusable multi-voice abstractions and split stable editor banks from one-off repeated poly shells."
        )
    elif stable_poly_shell_banks:
        targets.append({
            "name": "poly_shell_bank",
            "confidence": 0.88,
            "evidence": [
                f"stable exact poly-shell banks: {', '.join(sorted(stable_poly_shell_banks))}",
            ],
        })
        next_work.append(
            "Lift the stable repeated poly-shell bank into a richer semantic editor-bank layer instead of keeping only the exact helper surface."
        )

    if (
        has_stable_route_dispatch
        and {"route", "prepend"} <= stable_object_names
        and ({"message", "t"} & stable_object_names)
        and (
            "live.thisdevice" in stable_object_names
            or "thisdevice_reference" in stable_live_api
            or any(
                entry.get("name") == "thisdevice_reference"
                and float(entry.get("coverage", 0.0)) >= 0.5
                for entry in variable_live_api
            )
        )
    ):
        targets.append({
            "name": "controller_surface_shell",
            "confidence": 0.92,
            "evidence": [
                "stable route-based controller dispatch",
                "stable message/trigger/prepend shell",
                "stable or dominant thisdevice layer",
            ],
        })
        next_work.append(
            "Normalize the stable route/prepend/send-receive/live.thisdevice shell into a reusable controller-surface abstraction."
        )

    if (
        has_stable_sel_dispatch
        and has_stable_gate_dispatch
        and "scheduler_chain:timed_dispatch" in stable_motif_names
        and stable_named_buses
    ):
        targets.append({
            "name": "sequencer_dispatch_shell",
            "confidence": 0.94,
            "evidence": [
                "stable selector and gate dispatch motifs",
                "stable timed-dispatch scheduler motif",
                "stable named-bus message fabric",
            ],
        })
        next_work.append(
            "Lift the stable sel/gate/named-bus/timed-dispatch controller shell into a sequencer-control normalization pass."
        )

    if stable_embedded_hosts:
        targets.append({
            "name": "embedded_ui_shell",
            "confidence": 0.78,
            "evidence": [
                f"stable embedded hosts: {', '.join(sorted(stable_embedded_hosts))}",
            ],
        })
        next_work.append(
            "Recurse the stable embedded host layer and separate host-shell structure from internal controller logic."
        )

    if stable_live_api:
        targets.append({
            "name": "stable_live_api_control_layer",
            "confidence": 0.84,
            "evidence": [
                f"stable Live API archetypes: {', '.join(sorted(stable_live_api))}",
            ],
        })
    elif variable_live_api:
        representative = sorted(
            variable_live_api,
            key=lambda entry: (-float(entry.get("coverage", 0.0)), -int(entry.get("count", 0)), entry["name"]),
        )
        targets.append({
            "name": "optional_live_api_layer",
            "confidence": 0.71,
            "evidence": [
                "Live API layer is present in only a subset of variants",
                f"top optional archetypes: {', '.join(entry['name'] for entry in representative[:3])}",
            ],
        })
        next_work.append(
            "Model the Live API layer as optional evolution on top of the stable controller shell instead of core family identity."
        )

    if any(entry.get("coverage", 0.0) >= 0.5 for entry in variable_named_buses) and not stable_named_buses:
        targets.append({
            "name": "optional_named_bus_layer",
            "confidence": 0.68,
            "evidence": [
                "named-bus networks recur across many variants but are not stable across the full family",
            ],
        })
        next_work.append(
            "Treat the named-bus fabric as an optional stratum and normalize it separately from the mandatory controller shell."
        )

    return targets, next_work


def rank_reverse_candidates(report: dict, *, limit: int = 20) -> list[dict]:
    """Rank parsed corpus items by expected reverse-engineering payoff."""
    ranked = []
    for item in report.get("items", []):
        if item.get("status") != "ok":
            continue
        score, reasons = _reverse_candidate_score(item)
        motif_signatures = _sorted_frequency(item.get("motif_signature_counts", {}))
        ranked.append({
            "name": item.get("name"),
            "path": item.get("path"),
            "device_type": item.get("device_type"),
            "score": score,
            "reasons": reasons[:5],
            "motif_count": item.get("motif_count", 0),
            "embedded_patcher_count": item.get("embedded_patcher_count", 0),
            "missing_support_files": item.get("missing_support_files", 0),
            "top_motif_signatures": motif_signatures[:5],
        })
    ranked.sort(key=lambda entry: (-entry["score"], entry.get("name", "")))
    return ranked[:limit]


def rank_reverse_candidate_families(report: dict, *, limit: int = 20) -> list[dict]:
    """Rank normalized device families instead of individual files."""
    families: dict[str, dict] = {}
    for entry in rank_reverse_candidates(report, limit=max(200, limit * 5)):
        family_key = _reverse_candidate_family_key(entry["name"])
        family = families.setdefault(family_key, {
            "family": family_key,
            "variants": 0,
            "best_score": entry["score"],
            "best_name": entry["name"],
            "best_path": entry["path"],
            "reasons": list(entry.get("reasons", [])),
        })
        family["variants"] += 1
        if entry["score"] > family["best_score"]:
            family["best_score"] = entry["score"]
            family["best_name"] = entry["name"]
            family["best_path"] = entry["path"]
            family["reasons"] = list(entry.get("reasons", []))
    ranked = sorted(
        families.values(),
        key=lambda entry: (-entry["best_score"], -entry["variants"], entry["family"]),
    )
    return ranked[:limit]


def build_reverse_candidate_family_profile(report: dict, family: str) -> dict | None:
    """Build a detailed stable-vs-variable profile for one normalized device family."""
    family_key = _reverse_candidate_family_key(family)
    items = [
        item
        for item in report.get("items", [])
        if item.get("status") == "ok"
        and _reverse_candidate_family_key(item.get("name", "")) == family_key
    ]
    if not items:
        return None

    ranked_families = {
        entry["family"]: entry
        for entry in rank_reverse_candidate_families(report, limit=max(200, len(report.get("items", []))))
    }
    ranking = ranked_families.get(family_key, {
        "family": family_key,
        "variants": len(items),
        "best_score": 0.0,
        "best_name": items[0].get("name"),
        "best_path": items[0].get("path"),
        "reasons": [],
    })

    variant_count = len(items)
    device_types: dict[str, int] = {}
    for item in items:
        device_type = item.get("device_type", "unknown")
        device_types[device_type] = device_types.get(device_type, 0) + 1

    motif_totals, motif_presence = _aggregate_presence_counts(items, "motif_signature_counts")
    object_totals, object_presence = _aggregate_presence_counts(items, "object_name_counts")
    live_api_archetype_totals, live_api_archetype_presence = _aggregate_presence_counts(items, "live_api_archetype_counts")
    named_bus_totals, named_bus_presence = _aggregate_presence_counts(items, "named_bus_network_names")
    embedded_host_totals, embedded_host_presence = _aggregate_presence_counts(items, "embedded_patcher_host_kind_counts")
    behavior_hint_totals, behavior_hint_presence = _aggregate_presence_counts(items, "behavior_hint_counts")
    poly_shell_bank_totals, poly_shell_bank_presence = _aggregate_presence_counts(items, "poly_shell_bank_candidate_counts")
    poly_editor_bank_totals, poly_editor_bank_presence = _aggregate_presence_counts(items, "poly_editor_bank_candidate_counts")

    variants = _family_variant_summaries(items)
    profile = {
        "family": family_key,
        "variant_count": variant_count,
        "best_score": ranking.get("best_score", 0.0),
        "best_name": ranking.get("best_name"),
        "best_path": ranking.get("best_path"),
        "reasons": list(ranking.get("reasons", [])),
        "device_types": {
            name: device_types[name]
            for name in sorted(device_types)
        },
        "totals": {
            "motif_count": sum(int(item.get("motif_count", 0)) for item in items),
            "embedded_patcher_count": sum(int(item.get("embedded_patcher_count", 0)) for item in items),
            "live_api_helper_count": sum(int(item.get("live_api_helper_count", 0)) for item in items),
            "live_api_helper_opportunity_count": sum(int(item.get("live_api_helper_opportunity_count", 0)) for item in items),
            "missing_support_files": sum(int(item.get("missing_support_files", 0)) for item in items),
            "named_bus_network_count": sum(int(item.get("named_bus_network_count", 0)) for item in items),
            "cross_scope_named_bus_network_count": sum(
                int(item.get("cross_scope_named_bus_network_count", 0))
                for item in items
            ),
        },
        "stable_signals": {
            "motif_signatures": _coverage_frequency_entries(motif_totals, motif_presence, variant_count, stable_only=True),
            "object_names": _coverage_frequency_entries(object_totals, object_presence, variant_count, stable_only=True),
            "live_api_archetypes": _coverage_frequency_entries(
                live_api_archetype_totals,
                live_api_archetype_presence,
                variant_count,
                stable_only=True,
            ),
            "behavior_hints": _coverage_frequency_entries(
                behavior_hint_totals,
                behavior_hint_presence,
                variant_count,
                stable_only=True,
            ),
            "named_bus_network_names": _coverage_frequency_entries(
                named_bus_totals,
                named_bus_presence,
                variant_count,
                stable_only=True,
            ),
            "poly_shell_banks": _coverage_frequency_entries(
                poly_shell_bank_totals,
                poly_shell_bank_presence,
                variant_count,
                stable_only=True,
            ),
            "poly_editor_banks": _coverage_frequency_entries(
                poly_editor_bank_totals,
                poly_editor_bank_presence,
                variant_count,
                stable_only=True,
            ),
            "embedded_host_kinds": _coverage_frequency_entries(
                embedded_host_totals,
                embedded_host_presence,
                variant_count,
                stable_only=True,
            ),
        },
        "variable_signals": {
            "motif_signatures": _coverage_frequency_entries(motif_totals, motif_presence, variant_count, stable_only=False),
            "object_names": _coverage_frequency_entries(object_totals, object_presence, variant_count, stable_only=False),
            "live_api_archetypes": _coverage_frequency_entries(
                live_api_archetype_totals,
                live_api_archetype_presence,
                variant_count,
                stable_only=False,
            ),
            "behavior_hints": _coverage_frequency_entries(
                behavior_hint_totals,
                behavior_hint_presence,
                variant_count,
                stable_only=False,
            ),
            "named_bus_network_names": _coverage_frequency_entries(
                named_bus_totals,
                named_bus_presence,
                variant_count,
                stable_only=False,
            ),
            "poly_shell_banks": _coverage_frequency_entries(
                poly_shell_bank_totals,
                poly_shell_bank_presence,
                variant_count,
                stable_only=False,
            ),
            "poly_editor_banks": _coverage_frequency_entries(
                poly_editor_bank_totals,
                poly_editor_bank_presence,
                variant_count,
                stable_only=False,
            ),
            "embedded_host_kinds": _coverage_frequency_entries(
                embedded_host_totals,
                embedded_host_presence,
                variant_count,
                stable_only=False,
            ),
        },
        "variants": variants,
    }
    semantic_targets, next_work = _infer_family_semantic_targets(profile)
    profile["semantic_targets"] = semantic_targets
    profile["next_work_items"] = next_work
    return profile


def build_reverse_candidate_family_profiles(report: dict, *, limit: int = 20) -> list[dict]:
    """Aggregate variant-level motif/object signals into family profiles."""
    profiles = []
    for ranking in rank_reverse_candidate_families(report, limit=limit):
        detailed = build_reverse_candidate_family_profile(report, ranking["family"])
        if detailed is None:
            continue
        profiles.append({
            "family": detailed["family"],
            "variants": detailed["variant_count"],
            "best_score": detailed["best_score"],
            "best_name": detailed["best_name"],
            "device_types": detailed["device_types"],
            "top_motif_signatures": detailed["stable_signals"]["motif_signatures"][:10]
            or detailed["variable_signals"]["motif_signatures"][:10],
            "top_object_names": detailed["stable_signals"]["object_names"][:10]
            or detailed["variable_signals"]["object_names"][:10],
            "top_live_api_archetypes": detailed["stable_signals"]["live_api_archetypes"][:10]
            or detailed["variable_signals"]["live_api_archetypes"][:10],
            "top_named_bus_network_names": detailed["stable_signals"]["named_bus_network_names"][:10]
            or detailed["variable_signals"]["named_bus_network_names"][:10],
            "stable_motif_signature_count": len(detailed["stable_signals"]["motif_signatures"]),
            "variable_motif_signature_count": len(detailed["variable_signals"]["motif_signatures"]),
            "missing_support_total": detailed["totals"]["missing_support_files"],
            "embedded_patcher_total": detailed["totals"]["embedded_patcher_count"],
            "cross_scope_named_bus_network_total": detailed["totals"]["cross_scope_named_bus_network_count"],
            "semantic_targets": detailed["semantic_targets"],
            "variant_names": [variant["name"] for variant in detailed["variants"][:20]],
        })
    profiles.sort(key=lambda entry: (-entry["best_score"], -entry["variants"], entry["family"]))
    return profiles[:limit]


def build_source_lane_profiles(report: dict) -> list[dict]:
    """Aggregate motif and abstraction signals by source lane."""
    profiles = []
    ok_items = [item for item in report.get("items", []) if item.get("status") == "ok"]
    lane_names = sorted({item.get("source_lane") for item in ok_items if item.get("source_lane")})
    for lane in lane_names:
        items = [item for item in ok_items if item.get("source_lane") == lane]
        pack_name_counts: dict[str, int] = {}
        for item in items:
            pack_name = item.get("pack_name")
            if pack_name:
                pack_name_counts[pack_name] = pack_name_counts.get(pack_name, 0) + 1
        motif_totals, motif_presence = _aggregate_presence_counts(items, "motif_signature_counts")
        helper_totals, helper_presence = _aggregate_presence_counts(items, "live_api_helper_counts")
        controller_totals, controller_presence = _aggregate_presence_counts(items, "controller_shell_candidate_counts")
        behavior_totals, behavior_presence = _aggregate_presence_counts(items, "behavior_hint_counts")
        embedded_totals, embedded_presence = _aggregate_presence_counts(items, "embedded_ui_shell_candidate_counts")
        sample_buffer_totals, sample_buffer_presence = _aggregate_presence_counts(items, "sample_buffer_candidate_counts")
        gen_processing_totals, gen_processing_presence = _aggregate_presence_counts(items, "gen_processing_candidate_counts")
        embedded_sample_buffer_totals, embedded_sample_buffer_presence = _aggregate_presence_counts(items, "embedded_sample_buffer_candidate_counts")
        embedded_gen_processing_totals, embedded_gen_processing_presence = _aggregate_presence_counts(items, "embedded_gen_processing_candidate_counts")
        presentation_cluster_totals, presentation_cluster_presence = _aggregate_presence_counts(items, "presentation_widget_cluster_candidate_counts")
        poly_shell_bank_totals, poly_shell_bank_presence = _aggregate_presence_counts(items, "poly_shell_bank_candidate_counts")
        poly_editor_bank_totals, poly_editor_bank_presence = _aggregate_presence_counts(items, "poly_editor_bank_candidate_counts")
        first_party_api_totals, first_party_api_presence = _aggregate_presence_counts(items, "first_party_api_rig_candidate_counts")
        first_party_abstraction_totals, first_party_abstraction_presence = _aggregate_presence_counts(items, "first_party_abstraction_host_candidate_counts")
        first_party_abstraction_family_totals, first_party_abstraction_family_presence = _aggregate_presence_counts(items, "first_party_abstraction_host_family_counts")
        block_totals, block_presence = _aggregate_presence_counts(items, "building_block_candidate_counts")
        profiles.append({
            "lane": lane,
            "count": len(items),
            "pack_names": _sorted_frequency(pack_name_counts),
            "top_motif_signatures": _coverage_frequency_entries(motif_totals, motif_presence, len(items), stable_only=None)[:10],
            "top_live_api_helpers": _coverage_frequency_entries(helper_totals, helper_presence, len(items), stable_only=None)[:10],
            "top_controller_shells": _coverage_frequency_entries(controller_totals, controller_presence, len(items), stable_only=None)[:10],
            "top_behavior_hints": _coverage_frequency_entries(behavior_totals, behavior_presence, len(items), stable_only=None)[:10],
            "top_embedded_ui_shells": _coverage_frequency_entries(embedded_totals, embedded_presence, len(items), stable_only=None)[:10],
            "top_sample_buffer_candidates": _coverage_frequency_entries(sample_buffer_totals, sample_buffer_presence, len(items), stable_only=None)[:10],
            "top_gen_processing_candidates": _coverage_frequency_entries(gen_processing_totals, gen_processing_presence, len(items), stable_only=None)[:10],
            "top_embedded_sample_buffer_candidates": _coverage_frequency_entries(embedded_sample_buffer_totals, embedded_sample_buffer_presence, len(items), stable_only=None)[:10],
            "top_embedded_gen_processing_candidates": _coverage_frequency_entries(embedded_gen_processing_totals, embedded_gen_processing_presence, len(items), stable_only=None)[:10],
            "top_presentation_widget_clusters": _coverage_frequency_entries(presentation_cluster_totals, presentation_cluster_presence, len(items), stable_only=None)[:10],
            "top_poly_shell_banks": _coverage_frequency_entries(poly_shell_bank_totals, poly_shell_bank_presence, len(items), stable_only=None)[:10],
            "top_poly_editor_banks": _coverage_frequency_entries(poly_editor_bank_totals, poly_editor_bank_presence, len(items), stable_only=None)[:10],
            "top_first_party_api_rigs": _coverage_frequency_entries(first_party_api_totals, first_party_api_presence, len(items), stable_only=None)[:10],
            "top_first_party_abstraction_hosts": _coverage_frequency_entries(first_party_abstraction_totals, first_party_abstraction_presence, len(items), stable_only=None)[:10],
            "top_first_party_abstraction_families": _coverage_frequency_entries(first_party_abstraction_family_totals, first_party_abstraction_family_presence, len(items), stable_only=None)[:10],
            "top_building_blocks": _coverage_frequency_entries(block_totals, block_presence, len(items), stable_only=None)[:10],
            "avg_boxes": round(mean(item.get("box_count", 0) for item in items), 2) if items else 0.0,
            "avg_lines": round(mean(item.get("line_count", 0) for item in items), 2) if items else 0.0,
            "files_with_missing_support": sum(1 for item in items if item.get("missing_support_files", 0) > 0),
        })
    profiles.sort(key=lambda entry: (-entry["count"], entry["lane"]))
    return profiles


__all__ = [
    "_infer_family_semantic_targets",
    "rank_reverse_candidates",
    "rank_reverse_candidate_families",
    "build_reverse_candidate_family_profile",
    "build_reverse_candidate_family_profiles",
    "build_source_lane_profiles",
]
