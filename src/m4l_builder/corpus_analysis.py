"""Corpus analysis helpers for mining external .amxd device directories."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List

from .reverse import extract_snapshot_knowledge, snapshot_from_amxd


def _object_name_from_box(box: dict) -> str | None:
    maxclass = box.get("maxclass")
    if maxclass == "newobj":
        text = str(box.get("text", "")).strip()
        if text:
            return text.split()[0]
        return "newobj"
    if maxclass in {"message", "comment"}:
        return maxclass
    return None


def _motif_signature(motif: dict) -> str:
    kind = motif.get("kind", "unknown")
    params = motif.get("params", {})
    if kind == "named_bus":
        domain = "signal" if params.get("signal") else "message"
        return f"{kind}:{domain}"
    if kind == "controller_dispatch":
        primary = params.get("primary_operators") or []
        if primary:
            return f"{kind}:{'+'.join(primary)}"
    if kind == "scheduler_chain":
        archetypes = params.get("archetypes") or []
        if archetypes:
            return f"{kind}:{'+'.join(archetypes)}"
        operators = params.get("operator_counts") or {}
        if operators:
            return f"{kind}:{'+'.join(sorted(operators))}"
    if kind == "state_bundle":
        archetypes = params.get("archetypes") or []
        if archetypes:
            return f"{kind}:{'+'.join(archetypes)}"
        operators = params.get("operator_counts") or {}
        if operators:
            return f"{kind}:{'+'.join(sorted(operators))}"
    if kind == "embedded_patcher":
        return f"{kind}:{params.get('host_kind') or 'unknown'}"
    if kind == "live_api_component":
        core_operators = params.get("core_operators") or []
        if core_operators:
            return f"{kind}:{'+'.join(core_operators)}"
    return kind


def analyze_amxd_file(path: str) -> dict:
    """Analyze one .amxd file for corpus mining."""
    absolute_path = os.path.abspath(path)
    item = {
        "path": absolute_path,
        "name": os.path.basename(path),
    }

    try:
        snapshot = snapshot_from_amxd(absolute_path)
        knowledge = extract_snapshot_knowledge(snapshot)
        analysis = snapshot.get("analysis", {})
        missing_support_files = snapshot.get("missing_support_files", [])
        object_name_counts: Dict[str, int] = {}
        for wrapped in snapshot.get("boxes", []):
            box = wrapped.get("box", {})
            object_name = _object_name_from_box(box)
            if object_name:
                object_name_counts[object_name] = object_name_counts.get(object_name, 0) + 1

        control_maxclass_counts: Dict[str, int] = {}
        control_unitstyle_counts: Dict[str, int] = {}
        for control in knowledge.get("controls", []):
            maxclass = control.get("maxclass")
            if maxclass:
                control_maxclass_counts[maxclass] = control_maxclass_counts.get(maxclass, 0) + 1
            unitstyle = control.get("unitstyle")
            if unitstyle is not None:
                key = str(unitstyle)
                control_unitstyle_counts[key] = control_unitstyle_counts.get(key, 0) + 1
        motif_signature_counts: Dict[str, int] = {}
        for motif in knowledge.get("motifs", []):
            signature = _motif_signature(motif)
            motif_signature_counts[signature] = motif_signature_counts.get(signature, 0) + 1
        live_api_helper_counts: Dict[str, int] = {}
        for entry in knowledge.get("live_api_helpers", []):
            helper_name = entry.get("helper_name")
            if helper_name:
                live_api_helper_counts[helper_name] = live_api_helper_counts.get(helper_name, 0) + 1
        live_api_normalization_level_counts: Dict[str, int] = {}
        for entry in knowledge.get("live_api_normalization_candidates", []):
            level = entry.get("normalization_level")
            if level:
                live_api_normalization_level_counts[level] = live_api_normalization_level_counts.get(level, 0) + 1
        live_api_helper_opportunity_counts: Dict[str, int] = {}
        live_api_helper_opportunity_blockers: Dict[str, int] = {}
        controller_shell_candidate_counts: Dict[str, int] = {}
        embedded_ui_shell_candidate_counts: Dict[str, int] = {}
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
        for entry in knowledge.get("embedded_ui_shell_candidates", []):
            candidate_name = entry.get("candidate_name")
            if candidate_name:
                embedded_ui_shell_candidate_counts[candidate_name] = (
                    embedded_ui_shell_candidate_counts.get(candidate_name, 0) + 1
                )
        live_api_path_target_counts: Dict[str, int] = {}
        live_api_property_counts: Dict[str, int] = {}
        live_api_get_target_counts: Dict[str, int] = {}
        live_api_set_target_counts: Dict[str, int] = {}
        live_api_call_target_counts: Dict[str, int] = {}
        live_api_archetype_counts: Dict[str, int] = {}
        named_bus_network_names: Dict[str, int] = {}
        cross_scope_named_bus_network_names: Dict[str, int] = {}
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
        embedded_patcher_host_kind_counts: Dict[str, int] = {}
        embedded_pattern_kind_counts: Dict[str, int] = {}
        embedded_recipe_kind_counts: Dict[str, int] = {}
        embedded_motif_kind_counts: Dict[str, int] = {}
        embedded_live_api_path_target_counts: Dict[str, int] = {}
        embedded_live_api_property_counts: Dict[str, int] = {}
        embedded_live_api_get_target_counts: Dict[str, int] = {}
        embedded_live_api_set_target_counts: Dict[str, int] = {}
        embedded_live_api_call_target_counts: Dict[str, int] = {}
        embedded_live_api_archetype_counts: Dict[str, int] = {}
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
            "embedded_ui_shell_candidate_count": sum(embedded_ui_shell_candidate_counts.values()),
            "embedded_ui_shell_candidate_kinds": sorted(embedded_ui_shell_candidate_counts),
            "embedded_ui_shell_candidate_counts": embedded_ui_shell_candidate_counts,
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


def _sorted_frequency(mapping: dict[str, int]) -> list[dict]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(mapping.items(), key=lambda item: (-item[1], item[0]))
    ]


def _top_items(items: Iterable[dict], key: str, limit: int = 10) -> list[dict]:
    ranked = sorted(
        items,
        key=lambda item: (-item.get(key, 0), item.get("name", "")),
    )
    return [
        {
            "name": item.get("name"),
            key: item.get(key, 0),
            "device_type": item.get("device_type"),
        }
        for item in ranked[:limit]
    ]


def _reverse_candidate_score(item: dict) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    motif_count = int(item.get("motif_count", 0))
    embedded_patcher_count = int(item.get("embedded_patcher_count", 0))
    motif_signatures = item.get("motif_signature_counts", {})
    controller_hits = sum(
        int(count)
        for name, count in motif_signatures.items()
        if name.startswith("controller_dispatch:")
    )
    scheduler_hits = sum(
        int(count)
        for name, count in motif_signatures.items()
        if name.startswith("scheduler_chain:")
    )
    bundle_hits = sum(
        int(count)
        for name, count in motif_signatures.items()
        if name.startswith("state_bundle:")
    )
    live_api_opportunities = int(item.get("live_api_helper_opportunity_count", 0))
    missing_support = int(item.get("missing_support_files", 0))
    patterns = int(item.get("pattern_count", 0))
    recipes = int(item.get("recipe_count", 0))

    if motif_count:
        score += motif_count * 2.0
        reasons.append(f"{motif_count} generic motifs")
    cross_scope_buses = int(item.get("cross_scope_named_bus_network_count", 0))
    if cross_scope_buses:
        score += cross_scope_buses * 4.0
        reasons.append(f"{cross_scope_buses} cross-scope bus networks")
    if embedded_patcher_count:
        score += embedded_patcher_count * 3.0
        reasons.append(f"{embedded_patcher_count} embedded patchers")
    if controller_hits:
        score += controller_hits * 2.5
        reasons.append(f"{controller_hits} controller-dispatch hits")
    if scheduler_hits:
        score += scheduler_hits * 2.0
        reasons.append(f"{scheduler_hits} scheduler hits")
    if bundle_hits:
        score += bundle_hits * 1.5
        reasons.append(f"{bundle_hits} state-bundle hits")
    if live_api_opportunities:
        score += live_api_opportunities * 2.0
        reasons.append(f"{live_api_opportunities} unresolved Live API helpers")
    if patterns:
        score -= patterns * 0.5
    if recipes:
        score -= recipes * 0.5
    if missing_support:
        score -= min(missing_support, 10) * 0.25
        reasons.append(f"{missing_support} missing sidecars")

    return round(score, 2), reasons


def _reverse_candidate_family_key(name: str) -> str:
    stem = Path(name).stem
    if "__" in stem:
        stem = stem.split("__", 1)[1]
    stem = re.sub(r"-\d+(?:\.\d+)+$", "", stem)
    return stem


def _aggregate_presence_counts(items: list[dict], field: str) -> tuple[dict[str, int], dict[str, int]]:
    totals: dict[str, int] = {}
    presence: dict[str, int] = {}
    for item in items:
        seen: set[str] = set()
        for name, count in item.get(field, {}).items():
            numeric = int(count)
            if numeric <= 0:
                continue
            totals[name] = totals.get(name, 0) + numeric
            seen.add(name)
        for name in seen:
            presence[name] = presence.get(name, 0) + 1
    return totals, presence


def _coverage_frequency_entries(
    totals: dict[str, int],
    presence: dict[str, int],
    variant_count: int,
    *,
    stable_only: bool | None = None,
    limit: int | None = None,
) -> list[dict]:
    entries = []
    for name, total in totals.items():
        variant_presence = presence.get(name, 0)
        is_stable = variant_presence == variant_count
        if stable_only is True and not is_stable:
            continue
        if stable_only is False and is_stable:
            continue
        entries.append({
            "name": name,
            "count": total,
            "variant_presence": variant_presence,
            "coverage": round(variant_presence / variant_count, 3) if variant_count else 0.0,
        })
    entries.sort(key=lambda entry: (-entry["variant_presence"], -entry["count"], entry["name"]))
    if limit is None:
        return entries
    return entries[:limit]


def _family_variant_summaries(items: list[dict]) -> list[dict]:
    variants = []
    for item in sorted(items, key=lambda entry: entry.get("name", "")):
        variants.append({
            "name": item.get("name"),
            "path": item.get("path"),
            "device_type": item.get("device_type"),
            "box_count": item.get("box_count", 0),
            "line_count": item.get("line_count", 0),
            "motif_count": item.get("motif_count", 0),
            "embedded_patcher_count": item.get("embedded_patcher_count", 0),
            "live_api_helper_count": item.get("live_api_helper_count", 0),
            "live_api_helper_opportunity_count": item.get("live_api_helper_opportunity_count", 0),
            "missing_support_files": item.get("missing_support_files", 0),
        })
    return variants


def _names_by_coverage(entries: list[dict], minimum: float = 0.0) -> set[str]:
    return {
        entry["name"]
        for entry in entries
        if float(entry.get("coverage", 0.0)) >= minimum
    }


def _has_stable_dispatch_operator(entries: list[dict], operator: str) -> bool:
    prefix = "controller_dispatch:"
    for entry in entries:
        if float(entry.get("coverage", 0.0)) < 1.0:
            continue
        name = str(entry.get("name", ""))
        if not name.startswith(prefix):
            continue
        parts = name[len(prefix):].split("+")
        if operator in parts:
            return True
    return False


def _infer_family_semantic_targets(profile: dict) -> tuple[list[dict], list[str]]:
    stable_motif_entries = profile.get("stable_signals", {}).get("motif_signatures", [])
    stable_motif_names = _names_by_coverage(stable_motif_entries, 1.0)
    stable_object_names = _names_by_coverage(profile.get("stable_signals", {}).get("object_names", []), 1.0)
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
            "named_bus_network_names": _coverage_frequency_entries(
                named_bus_totals,
                named_bus_presence,
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
            "named_bus_network_names": _coverage_frequency_entries(
                named_bus_totals,
                named_bus_presence,
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

    device_type_counts: Dict[str, int] = {}
    error_counts: Dict[str, int] = {}
    error_type_counts: Dict[str, int] = {}
    pattern_counts: Dict[str, int] = {}
    recipe_counts: Dict[str, int] = {}
    motif_counts: Dict[str, int] = {}
    motif_signature_counts: Dict[str, int] = {}
    maxclass_counts: Dict[str, int] = {}
    object_name_counts: Dict[str, int] = {}
    control_maxclass_counts: Dict[str, int] = {}
    control_unitstyle_counts: Dict[str, int] = {}
    display_role_counts: Dict[str, int] = {}
    embedded_patcher_host_kind_counts: Dict[str, int] = {}
    embedded_pattern_kind_counts: Dict[str, int] = {}
    embedded_recipe_kind_counts: Dict[str, int] = {}
    embedded_motif_kind_counts: Dict[str, int] = {}
    live_api_path_target_counts: Dict[str, int] = {}
    live_api_property_counts: Dict[str, int] = {}
    live_api_get_target_counts: Dict[str, int] = {}
    live_api_set_target_counts: Dict[str, int] = {}
    live_api_call_target_counts: Dict[str, int] = {}
    live_api_archetype_counts: Dict[str, int] = {}
    named_bus_network_name_counts: Dict[str, int] = {}
    cross_scope_named_bus_network_name_counts: Dict[str, int] = {}
    live_api_helper_counts: Dict[str, int] = {}
    live_api_normalization_level_counts: Dict[str, int] = {}
    live_api_helper_opportunity_counts: Dict[str, int] = {}
    live_api_helper_opportunity_blockers: Dict[str, int] = {}
    controller_shell_candidate_counts: Dict[str, int] = {}
    embedded_ui_shell_candidate_counts: Dict[str, int] = {}
    embedded_live_api_path_target_counts: Dict[str, int] = {}
    embedded_live_api_property_counts: Dict[str, int] = {}
    embedded_live_api_get_target_counts: Dict[str, int] = {}
    embedded_live_api_set_target_counts: Dict[str, int] = {}
    embedded_live_api_call_target_counts: Dict[str, int] = {}
    embedded_live_api_archetype_counts: Dict[str, int] = {}
    missing_support_counts: Dict[str, int] = {}

    for item in items:
        if item.get("status") != "ok":
            error = item.get("error", "Unknown error")
            error_counts[error] = error_counts.get(error, 0) + 1
            error_type = item.get("error_type", "UnknownError")
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
            continue

        device_type = item.get("device_type", "unknown")
        device_type_counts[device_type] = device_type_counts.get(device_type, 0) + 1

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
        for candidate_name, count in item.get("embedded_ui_shell_candidate_counts", {}).items():
            embedded_ui_shell_candidate_counts[candidate_name] = embedded_ui_shell_candidate_counts.get(candidate_name, 0) + int(count)
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
        "bridge_enabled_files": sum(1 for item in ok_items if item.get("bridge_enabled")),
        "files_with_patterns": sum(1 for item in ok_items if item.get("pattern_count", 0) > 0),
        "files_with_recipes": sum(1 for item in ok_items if item.get("recipe_count", 0) > 0),
        "files_with_motifs": sum(1 for item in ok_items if item.get("motif_count", 0) > 0),
        "files_with_named_bus_networks": sum(1 for item in ok_items if item.get("named_bus_network_count", 0) > 0),
        "files_with_cross_scope_named_bus_networks": sum(1 for item in ok_items if item.get("cross_scope_named_bus_network_count", 0) > 0),
        "files_with_live_api_helpers": sum(1 for item in ok_items if item.get("live_api_helper_count", 0) > 0),
        "files_with_live_api_helper_opportunities": sum(1 for item in ok_items if item.get("live_api_helper_opportunity_count", 0) > 0),
        "files_with_controller_shell_candidates": sum(1 for item in ok_items if item.get("controller_shell_candidate_count", 0) > 0),
        "files_with_embedded_ui_shell_candidates": sum(1 for item in ok_items if item.get("embedded_ui_shell_candidate_count", 0) > 0),
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
            "embedded_ui_shell_candidates": _sorted_frequency(embedded_ui_shell_candidate_counts),
            "embedded_live_api_path_targets": _sorted_frequency(embedded_live_api_path_target_counts),
            "embedded_live_api_properties": _sorted_frequency(embedded_live_api_property_counts),
            "embedded_live_api_get_targets": _sorted_frequency(embedded_live_api_get_target_counts),
            "embedded_live_api_set_targets": _sorted_frequency(embedded_live_api_set_target_counts),
            "embedded_live_api_call_targets": _sorted_frequency(embedded_live_api_call_target_counts),
            "embedded_live_api_archetypes": _sorted_frequency(embedded_live_api_archetype_counts),
            "error_types": _sorted_frequency(error_type_counts),
            "errors": _sorted_frequency(error_counts),
            "missing_support_files": _sorted_frequency(missing_support_counts),
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
    return report


def corpus_report_markdown(report: dict) -> str:
    """Render a human-readable markdown report from `analyze_amxd_corpus()`."""
    summary = report.get("summary", {})
    frequencies = report.get("frequencies", {})
    largest = report.get("largest_devices", {})
    lines = [
        "# AMXD Corpus Report",
        "",
        f"- Root: `{report.get('corpus', {}).get('root', '')}`",
        f"- Files scanned: `{summary.get('count', 0)}`",
        f"- Parsed successfully: `{summary.get('ok', 0)}`",
        f"- Parse errors: `{summary.get('error', 0)}`",
        f"- Device types: `{json.dumps(summary.get('device_types', {}), sort_keys=True)}`",
        f"- Bridge-enabled files: `{summary.get('bridge_enabled_files', 0)}`",
        f"- Files with helper patterns: `{summary.get('files_with_patterns', 0)}`",
        f"- Files with recipe patterns: `{summary.get('files_with_recipes', 0)}`",
        f"- Files with generic motifs: `{summary.get('files_with_motifs', 0)}`",
        f"- Files with named-bus networks: `{summary.get('files_with_named_bus_networks', 0)}`",
        f"- Files with cross-scope named-bus networks: `{summary.get('files_with_cross_scope_named_bus_networks', 0)}`",
        f"- Files with semantic Live API helper recoveries: `{summary.get('files_with_live_api_helpers', 0)}`",
        f"- Files with Live API helper opportunities: `{summary.get('files_with_live_api_helper_opportunities', 0)}`",
        f"- Files with controller-shell candidates: `{summary.get('files_with_controller_shell_candidates', 0)}`",
        f"- Files with embedded-ui shell candidates: `{summary.get('files_with_embedded_ui_shell_candidates', 0)}`",
        f"- Files with embedded patchers: `{summary.get('files_with_embedded_patchers', 0)}`",
        f"- Files with embedded helper patterns: `{summary.get('files_with_embedded_patterns', 0)}`",
        f"- Files with embedded recipes: `{summary.get('files_with_embedded_recipes', 0)}`",
        f"- Files with embedded motifs: `{summary.get('files_with_embedded_motifs', 0)}`",
        f"- Files missing sidecars: `{summary.get('files_with_missing_support_files', 0)}`",
        f"- Avg boxes / lines: `{summary.get('avg_box_count', 0)}` / `{summary.get('avg_line_count', 0)}`",
        f"- Avg controls / displays: `{summary.get('avg_control_count', 0)}` / `{summary.get('avg_display_count', 0)}`",
        f"- Avg embedded patchers: `{summary.get('avg_embedded_patcher_count', 0)}`",
        f"- Avg embedded patterns / recipes / motifs: `{summary.get('avg_embedded_pattern_count', 0)}` / `{summary.get('avg_embedded_recipe_count', 0)}` / `{summary.get('avg_embedded_motif_count', 0)}`",
        "",
    ]

    def add_frequency_section(title: str, entries: list[dict], *, limit: int = 10) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not entries:
            lines.append("- None")
            lines.append("")
            return
        for entry in entries[:limit]:
            lines.append(f"- `{entry['name']}`: `{entry['count']}`")
        lines.append("")

    add_frequency_section("Top Patterns", frequencies.get("patterns", []))
    add_frequency_section("Top Recipes", frequencies.get("recipes", []))
    add_frequency_section("Top Motifs", frequencies.get("motifs", []))
    add_frequency_section("Top Motif Signatures", frequencies.get("motif_signatures", []))
    add_frequency_section("Top Maxclasses", frequencies.get("maxclasses", []))
    add_frequency_section("Top Object Names", frequencies.get("object_names", []))
    add_frequency_section("Top Control Maxclasses", frequencies.get("control_maxclasses", []))
    add_frequency_section("Top Control Unitstyles", frequencies.get("control_unitstyles", []))
    add_frequency_section("Top Display Roles", frequencies.get("display_roles", []))
    add_frequency_section("Top Embedded Patcher Host Kinds", frequencies.get("embedded_patcher_host_kinds", []))
    add_frequency_section("Top Embedded Patterns", frequencies.get("embedded_patterns", []))
    add_frequency_section("Top Embedded Recipes", frequencies.get("embedded_recipes", []))
    add_frequency_section("Top Embedded Motifs", frequencies.get("embedded_motifs", []))
    add_frequency_section("Top Live API Path Targets", frequencies.get("live_api_path_targets", []))
    add_frequency_section("Top Live API Properties", frequencies.get("live_api_properties", []))
    add_frequency_section("Top Live API Get Targets", frequencies.get("live_api_get_targets", []))
    add_frequency_section("Top Live API Set Targets", frequencies.get("live_api_set_targets", []))
    add_frequency_section("Top Live API Call Targets", frequencies.get("live_api_call_targets", []))
    add_frequency_section("Top Live API Archetypes", frequencies.get("live_api_archetypes", []))
    add_frequency_section("Top Named Bus Networks", frequencies.get("named_bus_network_names", []))
    add_frequency_section("Top Cross-Scope Named Bus Networks", frequencies.get("cross_scope_named_bus_network_names", []))
    add_frequency_section("Top Live API Helper Recoveries", frequencies.get("live_api_helpers", []))
    add_frequency_section("Top Live API Normalization Levels", frequencies.get("live_api_normalization_levels", []))
    add_frequency_section("Top Live API Helper Opportunities", frequencies.get("live_api_helper_opportunities", []))
    add_frequency_section("Top Live API Helper Opportunity Blockers", frequencies.get("live_api_helper_opportunity_blockers", []))
    add_frequency_section("Top Controller Shell Candidates", frequencies.get("controller_shell_candidates", []))
    add_frequency_section("Top Embedded UI Shell Candidates", frequencies.get("embedded_ui_shell_candidates", []))
    add_frequency_section("Top Embedded Live API Path Targets", frequencies.get("embedded_live_api_path_targets", []))
    add_frequency_section("Top Embedded Live API Properties", frequencies.get("embedded_live_api_properties", []))
    add_frequency_section("Top Embedded Live API Get Targets", frequencies.get("embedded_live_api_get_targets", []))
    add_frequency_section("Top Embedded Live API Set Targets", frequencies.get("embedded_live_api_set_targets", []))
    add_frequency_section("Top Embedded Live API Call Targets", frequencies.get("embedded_live_api_call_targets", []))
    add_frequency_section("Top Embedded Live API Archetypes", frequencies.get("embedded_live_api_archetypes", []))
    add_frequency_section("Top Missing Sidecars", frequencies.get("missing_support_files", []))
    add_frequency_section("Top Error Types", frequencies.get("error_types", []))
    add_frequency_section("Top Errors", frequencies.get("errors", []), limit=12)

    lines.append("## Largest Devices By Boxes")
    lines.append("")
    if largest.get("by_boxes"):
        for entry in largest["by_boxes"][:10]:
            lines.append(f"- `{entry['name']}`: `{entry['box_count']}` boxes (`{entry.get('device_type')}`)")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Largest Devices By Lines")
    lines.append("")
    if largest.get("by_lines"):
        for entry in largest["by_lines"][:10]:
            lines.append(f"- `{entry['name']}`: `{entry['line_count']}` lines (`{entry.get('device_type')}`)")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Top Reverse Candidates")
    lines.append("")
    reverse_candidates = report.get("reverse_candidates", [])
    if reverse_candidates:
        for entry in reverse_candidates[:10]:
            reason_text = ", ".join(entry.get("reasons", []))
            lines.append(
                f"- `{entry['name']}`: score `{entry['score']}`"
                f" ({entry.get('device_type')})"
                + (f" -- {reason_text}" if reason_text else "")
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Top Reverse Candidate Families")
    lines.append("")
    reverse_candidate_families = report.get("reverse_candidate_families", [])
    if reverse_candidate_families:
        for entry in reverse_candidate_families[:10]:
            reason_text = ", ".join(entry.get("reasons", []))
            lines.append(
                f"- `{entry['family']}`: best score `{entry['best_score']}`,"
                f" `{entry['variants']}` variant(s), best file `{entry['best_name']}`"
                + (f" -- {reason_text}" if reason_text else "")
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Top Reverse Candidate Family Profiles")
    lines.append("")
    reverse_candidate_family_profiles = report.get("reverse_candidate_family_profiles", [])
    if reverse_candidate_family_profiles:
        for entry in reverse_candidate_family_profiles[:5]:
            top_motif = entry.get("top_motif_signatures", [])
            motif_text = ", ".join(
                f"{motif['name']}:{motif['count']}"
                for motif in top_motif[:3]
            )
            lines.append(
                f"- `{entry['family']}`: best score `{entry['best_score']}`,"
                f" `{entry['variants']}` variant(s), embedded patchers `{entry['embedded_patcher_total']}`,"
                f" missing sidecars `{entry['missing_support_total']}`"
                + (f" -- top motifs {motif_text}" if motif_text else "")
            )
    else:
        lines.append("- None")
    lines.append("")

    return "\n".join(lines)


def family_profile_markdown(profile: dict) -> str:
    """Render a human-readable markdown report from a family profile."""
    lines = [
        "# AMXD Family Report",
        "",
        f"- Family: `{profile.get('family', '')}`",
        f"- Variants: `{profile.get('variant_count', 0)}`",
        f"- Best score: `{profile.get('best_score', 0)}`",
        f"- Best file: `{profile.get('best_name', '')}`",
        f"- Device types: `{json.dumps(profile.get('device_types', {}), sort_keys=True)}`",
        f"- Totals: `{json.dumps(profile.get('totals', {}), sort_keys=True)}`",
    ]
    reasons = profile.get("reasons", [])
    if reasons:
        lines.append(f"- Rank reasons: `{'; '.join(reasons)}`")
    lines.append("")

    lines.append("## Semantic Targets")
    lines.append("")
    semantic_targets = profile.get("semantic_targets", [])
    if semantic_targets:
        for entry in semantic_targets:
            evidence = "; ".join(entry.get("evidence", []))
            lines.append(
                f"- `{entry['name']}`: confidence `{entry.get('confidence', 0.0)}`"
                + (f" -- {evidence}" if evidence else "")
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Next Work Items")
    lines.append("")
    next_work_items = profile.get("next_work_items", [])
    if next_work_items:
        for item in next_work_items:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")

    def add_section(title: str, entries: list[dict], *, limit: int = 12) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not entries:
            lines.append("- None")
            lines.append("")
            return
        for entry in entries[:limit]:
            lines.append(
                f"- `{entry['name']}`: total `{entry['count']}`,"
                f" variants `{entry['variant_presence']}/{profile.get('variant_count', 0)}`"
                f" (coverage `{entry['coverage']}`)"
            )
        lines.append("")

    stable = profile.get("stable_signals", {})
    variable = profile.get("variable_signals", {})
    add_section("Stable Motif Signatures", stable.get("motif_signatures", []))
    add_section("Variable Motif Signatures", variable.get("motif_signatures", []))
    add_section("Stable Object Names", stable.get("object_names", []))
    add_section("Variable Object Names", variable.get("object_names", []))
    add_section("Stable Live API Archetypes", stable.get("live_api_archetypes", []))
    add_section("Variable Live API Archetypes", variable.get("live_api_archetypes", []))
    add_section("Stable Named Bus Networks", stable.get("named_bus_network_names", []))
    add_section("Variable Named Bus Networks", variable.get("named_bus_network_names", []))
    add_section("Stable Embedded Host Kinds", stable.get("embedded_host_kinds", []))
    add_section("Variable Embedded Host Kinds", variable.get("embedded_host_kinds", []))

    lines.append("## Variants")
    lines.append("")
    variants = profile.get("variants", [])
    if not variants:
        lines.append("- None")
    else:
        for variant in variants:
            lines.append(
                f"- `{variant['name']}`: `{variant['device_type']}`,"
                f" boxes `{variant['box_count']}`, lines `{variant['line_count']}`,"
                f" motifs `{variant['motif_count']}`, embedded patchers `{variant['embedded_patcher_count']}`,"
                f" helper recoveries `{variant['live_api_helper_count']}`,"
                f" helper opportunities `{variant['live_api_helper_opportunity_count']}`,"
                f" missing sidecars `{variant['missing_support_files']}`"
            )
    lines.append("")
    return "\n".join(lines)


def write_corpus_report(report: dict, path: str) -> int:
    """Write a markdown corpus report to disk."""
    text = corpus_report_markdown(report)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return len(text.encode("utf-8"))


def write_family_profile(profile: dict, path: str) -> int:
    """Write a markdown family report to disk."""
    text = family_profile_markdown(profile)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return len(text.encode("utf-8"))


__all__ = [
    "analyze_amxd_file",
    "analyze_amxd_corpus",
    "rank_reverse_candidates",
    "rank_reverse_candidate_families",
    "build_reverse_candidate_family_profile",
    "build_reverse_candidate_family_profiles",
    "corpus_report_markdown",
    "family_profile_markdown",
    "write_corpus_report",
    "write_family_profile",
]
