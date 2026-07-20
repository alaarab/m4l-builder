"""Shared aggregation/scoring helpers for corpus analysis.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any


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
    poly_shell_banks = int(item.get("poly_shell_bank_candidate_count", 0))
    poly_editor_banks = int(item.get("poly_editor_bank_candidate_count", 0))
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
    if poly_shell_banks:
        score += poly_shell_banks * 6.0
        reasons.append(f"{poly_shell_banks} poly-shell bank candidates")
    if poly_editor_banks:
        score += poly_editor_banks * 8.0
        reasons.append(f"{poly_editor_banks} poly-editor bank candidates")
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
    entries: list[dict[str, Any]] = []
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


__all__ = [
    "_object_name_from_box",
    "_motif_signature",
    "_sorted_frequency",
    "_top_items",
    "_reverse_candidate_score",
    "_reverse_candidate_family_key",
    "_aggregate_presence_counts",
    "_coverage_frequency_entries",
    "_family_variant_summaries",
    "_names_by_coverage",
    "_has_stable_dispatch_operator",
]
