"""Manifest and fixture helpers for local external AMXD corpora."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence

from .corpus_analysis import analyze_amxd_corpus
from .reverse import (
    extract_snapshot_knowledge,
    generate_builder_python_from_amxd,
    generate_optimized_python_from_amxd,
    generate_python_from_amxd,
    generate_semantic_python_from_amxd,
    snapshot_from_amxd,
    snapshot_to_json,
)


_GENERATOR_MAP: dict[str, Callable[[str], str]] = {
    "exact": generate_python_from_amxd,
    "builder": generate_builder_python_from_amxd,
    "optimized": generate_optimized_python_from_amxd,
    "semantic": generate_semantic_python_from_amxd,
}

_DEFAULT_FIXTURE_MODES = ("exact", "builder", "optimized", "semantic")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "fixture"


def _family_key(name: str) -> str:
    stem = Path(name).stem
    if "__" in stem:
        stem = stem.split("__", 1)[1]
    stem = re.sub(r"-\d+(?:\.\d+)+$", "", stem)
    return stem or Path(name).stem or name


def _manifest_categories(item: dict, relative_path: str) -> list[str]:
    categories: set[str] = {f"status:{item.get('status', 'unknown')}"}
    categories.add(f"family:{_family_key(item.get('name') or relative_path)}")
    if relative_path and "/" in relative_path:
        categories.add(f"source_dir:{relative_path.split('/', 1)[0]}")

    if item.get("status") != "ok":
        categories.add(f"error_type:{item.get('error_type', 'UnknownError')}")
        return sorted(categories)

    device_type = item.get("device_type")
    if device_type:
        categories.add(f"device_type:{device_type}")
    if item.get("bridge_enabled"):
        categories.add("bridge_enabled")
    if item.get("pattern_count", 0) > 0:
        categories.add("has_patterns")
    if item.get("recipe_count", 0) > 0:
        categories.add("has_recipes")
    if item.get("motif_count", 0) > 0:
        categories.add("has_motifs")
    if item.get("live_api_helper_count", 0) > 0:
        categories.add("has_live_api_helpers")
    if item.get("live_api_helper_opportunity_count", 0) > 0:
        categories.add("has_live_api_helper_opportunities")
    if item.get("embedded_patcher_count", 0) > 0:
        categories.add("has_embedded_patchers")
    if item.get("missing_support_files", 0) > 0:
        categories.add("has_missing_support_files")

    for kind in item.get("pattern_kinds", []):
        categories.add(f"pattern:{kind}")
    for kind in item.get("recipe_kinds", []):
        categories.add(f"recipe:{kind}")
    for kind in item.get("motif_kinds", []):
        categories.add(f"motif:{kind}")
    for helper_name in item.get("live_api_helper_kinds", []):
        categories.add(f"live_api_helper:{helper_name}")
    for archetype in sorted(item.get("live_api_archetype_counts", {})):
        categories.add(f"live_api_archetype:{archetype}")
    for host_kind in sorted(item.get("embedded_patcher_host_kind_counts", {})):
        categories.add(f"embedded_host:{host_kind}")

    return sorted(categories)


def _dependency_notes(item: dict) -> list[str]:
    notes: list[str] = []
    if item.get("status") != "ok":
        error_type = item.get("error_type", "UnknownError")
        error = item.get("error", "")
        notes.append(f"parse_error:{error_type}")
        if error:
            notes.append(error)
        return notes

    if item.get("missing_support_files", 0) > 0:
        notes.append(f"missing_support_files:{item['missing_support_files']}")
        for name in item.get("missing_support_names", [])[:8]:
            notes.append(f"missing_support:{name}")
    if item.get("embedded_patcher_count", 0) > 0:
        notes.append(f"embedded_patchers:{item['embedded_patcher_count']}")
    if item.get("bridge_enabled"):
        notes.append("bridge_runtime_detected")
    if item.get("live_api_helper_count", 0) > 0:
        notes.append(f"live_api_helpers:{item['live_api_helper_count']}")
    if item.get("live_api_helper_opportunity_count", 0) > 0:
        notes.append(f"live_api_helper_opportunities:{item['live_api_helper_opportunity_count']}")
    return notes


def _selection_tags(entry: dict) -> set[str]:
    allowed_prefixes = (
        "device_type:",
        "pattern:",
        "recipe:",
        "motif:",
        "live_api_helper:",
        "live_api_archetype:",
        "embedded_host:",
        "error_type:",
    )
    tags = {
        category
        for category in entry.get("categories", [])
        if category in {
            "bridge_enabled",
            "has_patterns",
            "has_recipes",
            "has_motifs",
            "has_live_api_helpers",
            "has_live_api_helper_opportunities",
            "has_embedded_patchers",
            "has_missing_support_files",
        }
        or category.startswith(allowed_prefixes)
    }
    if entry.get("status") == "error":
        tags.add("status:error")
    return tags


def _stable_sample(entries: Sequence[dict], sample_size: int) -> list[str]:
    ok_entries = [entry for entry in entries if entry.get("status") == "ok"]
    if sample_size <= 0 or not ok_entries:
        return []

    uncovered = set()
    entry_tags: dict[str, set[str]] = {}
    for entry in ok_entries:
        tags = _selection_tags(entry)
        entry_tags[entry["relative_path"]] = tags
        uncovered.update(tags)

    selected: list[dict] = []
    remaining = list(ok_entries)

    while remaining and len(selected) < sample_size:
        ranked = sorted(
            remaining,
            key=lambda entry: (
                len(entry_tags[entry["relative_path"]] & uncovered),
                len(entry_tags[entry["relative_path"]]),
                int(entry.get("bridge_enabled", False)),
                int(entry.get("embedded_patcher_count", 0)),
                int(entry.get("motif_count", 0)),
                int(entry.get("box_count", 0)),
                int(entry.get("line_count", 0)),
                entry.get("relative_path", ""),
            ),
            reverse=True,
        )
        best = ranked[0]
        selected.append(best)
        uncovered -= entry_tags[best["relative_path"]]
        remaining = [entry for entry in remaining if entry["relative_path"] != best["relative_path"]]

    return [entry["relative_path"] for entry in sorted(selected, key=lambda entry: entry["relative_path"])]


def build_corpus_manifest(
    path: str,
    *,
    recursive: bool = True,
    stable_sample_size: int = 12,
    analysis: dict | None = None,
) -> dict:
    """Build a deterministic manifest for a local external AMXD corpus."""
    root = Path(path).expanduser().resolve()
    report = analysis if analysis is not None else analyze_amxd_corpus(str(root), recursive=recursive)
    entries: list[dict] = []
    for item in sorted(report.get("items", []), key=lambda entry: entry.get("path", "")):
        item_path = Path(item["path"]).expanduser().resolve()
        relative_path = _relative_path(item_path, root)
        stat = item_path.stat() if item_path.exists() else None
        entry = {
            "name": item.get("name") or item_path.name,
            "path": str(item_path),
            "relative_path": relative_path,
            "status": item.get("status", "unknown"),
            "sha256": _sha256_file(item_path) if item_path.exists() else None,
            "size_bytes": stat.st_size if stat is not None else 0,
            "mtime": stat.st_mtime if stat is not None else 0.0,
            "categories": _manifest_categories(item, relative_path),
            "dependency_notes": _dependency_notes(item),
            "analysis": {
                "device_type": item.get("device_type"),
                "box_count": item.get("box_count"),
                "line_count": item.get("line_count"),
                "control_count": item.get("control_count"),
                "display_count": item.get("display_count"),
                "pattern_kinds": list(item.get("pattern_kinds", [])),
                "recipe_kinds": list(item.get("recipe_kinds", [])),
                "motif_kinds": list(item.get("motif_kinds", [])),
                "live_api_helper_kinds": list(item.get("live_api_helper_kinds", [])),
                "live_api_helper_opportunity_kinds": list(item.get("live_api_helper_opportunity_kinds", [])),
                "embedded_patcher_count": item.get("embedded_patcher_count", 0),
                "missing_support_files": item.get("missing_support_files", 0),
            },
        }
        if item.get("status") != "ok":
            entry["error"] = {
                "type": item.get("error_type"),
                "message": item.get("error"),
            }
        entries.append(entry)

    manifest = {
        "corpus": {
            "root": str(root),
            "recursive": recursive,
            "file_count": len(entries),
            "analysis_summary": report.get("summary", {}),
        },
        "entries": entries,
        "sample_sets": {
            "stable": _stable_sample(entries, stable_sample_size),
            "errors": [
                entry["relative_path"]
                for entry in entries
                if entry.get("status") != "ok"
            ],
            "bridge_enabled": [
                entry["relative_path"]
                for entry in entries
                if "bridge_enabled" in entry.get("categories", [])
            ],
        },
    }
    return manifest


def load_corpus_manifest(path: str) -> dict:
    """Load a corpus manifest from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_corpus_manifest(manifest: dict, path: str) -> int:
    """Write a corpus manifest to disk."""
    text = json.dumps(manifest, indent=2, sort_keys=True)
    Path(path).write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def select_corpus_manifest_entries(
    manifest: dict,
    *,
    selection: str = "stable",
    limit: int | None = None,
) -> list[dict]:
    """Select manifest entries by sample set or category tag."""
    entries = list(manifest.get("entries", []))
    lookup = {entry["relative_path"]: entry for entry in entries}
    if selection == "stable":
        selected = [
            lookup[path]
            for path in manifest.get("sample_sets", {}).get("stable", [])
            if path in lookup
        ]
    elif selection == "all":
        selected = entries
    elif selection == "ok":
        selected = [entry for entry in entries if entry.get("status") == "ok"]
    elif selection == "errors":
        selected = [entry for entry in entries if entry.get("status") != "ok"]
    elif selection == "bridge_enabled":
        selected = [entry for entry in entries if "bridge_enabled" in entry.get("categories", [])]
    elif selection.startswith("family:"):
        family = selection.split(":", 1)[1]
        selected = [entry for entry in entries if f"family:{family}" in entry.get("categories", [])]
    elif selection.startswith("category:"):
        tag = selection.split(":", 1)[1]
        selected = [entry for entry in entries if tag in entry.get("categories", [])]
    else:
        raise ValueError(f"Unsupported corpus selection: {selection}")

    selected = sorted(selected, key=lambda entry: entry.get("relative_path", ""))
    if limit is not None:
        selected = selected[:limit]
    return selected


def _fixture_item_dir(output_dir: Path, index: int, entry: dict) -> Path:
    stem = Path(entry["relative_path"]).stem or entry.get("name") or f"fixture-{index:02d}"
    return output_dir / f"{index:02d}-{_slugify(stem)}"


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def run_corpus_fixture(
    corpus_or_manifest: str | dict,
    output_dir: str,
    *,
    selection: str = "stable",
    limit: int | None = None,
    recursive: bool = True,
    stable_sample_size: int = 12,
    modes: Iterable[str] = _DEFAULT_FIXTURE_MODES,
) -> dict:
    """Generate local reverse/codegen artifacts for a selected corpus subset."""
    manifest = (
        corpus_or_manifest
        if isinstance(corpus_or_manifest, dict)
        else build_corpus_manifest(
            str(corpus_or_manifest),
            recursive=recursive,
            stable_sample_size=stable_sample_size,
        )
    )
    selected = select_corpus_manifest_entries(manifest, selection=selection, limit=limit)
    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    mode_list = tuple(modes)
    for mode in mode_list:
        if mode not in _GENERATOR_MAP:
            raise ValueError(f"Unsupported fixture mode: {mode}")

    results = {
        "corpus": manifest.get("corpus", {}),
        "selection": selection,
        "limit": limit,
        "modes": list(mode_list),
        "output_dir": str(output_root),
        "selected_count": len(selected),
        "selected": [entry["relative_path"] for entry in selected],
        "fixture_ok_count": 0,
        "fixture_partial_count": 0,
        "fixture_error_count": 0,
        "items": [],
    }

    for index, entry in enumerate(selected, start=1):
        item_dir = _fixture_item_dir(output_root, index, entry)
        item_dir.mkdir(parents=True, exist_ok=True)
        result_item = {
            "name": entry.get("name"),
            "path": entry.get("path"),
            "relative_path": entry.get("relative_path"),
            "status": entry.get("status"),
            "fixture_status": "pending",
            "fixture_dir": str(item_dir),
            "categories": list(entry.get("categories", [])),
            "dependency_notes": list(entry.get("dependency_notes", [])),
            "artifacts": {},
        }

        if entry.get("status") != "ok":
            result_item["fixture_status"] = "skipped"
            result_item["error"] = entry.get("error")
            results["items"].append(result_item)
            continue

        try:
            snapshot = snapshot_from_amxd(entry["path"])
            knowledge = extract_snapshot_knowledge(snapshot)
            snapshot_path = item_dir / "snapshot.json"
            knowledge_path = item_dir / "knowledge.json"
            snapshot_path.write_text(snapshot_to_json(snapshot), encoding="utf-8")
            _write_json(knowledge_path, knowledge)
            result_item["artifacts"]["snapshot"] = str(snapshot_path)
            result_item["artifacts"]["knowledge"] = str(knowledge_path)

            script_lengths: dict[str, int] = {}
            mode_errors: dict[str, str] = {}
            for mode in mode_list:
                generator = _GENERATOR_MAP[mode]
                try:
                    script_text = generator(entry["path"])
                except Exception as exc:  # pragma: no cover - exercised via monkeypatch
                    mode_errors[mode] = f"{type(exc).__name__}: {exc}"
                    continue
                script_path = item_dir / f"{mode}.py"
                script_path.write_text(script_text, encoding="utf-8")
                result_item["artifacts"][mode] = str(script_path)
                script_lengths[mode] = len(script_text)
            result_item["script_lengths"] = script_lengths
            if mode_errors:
                result_item["fixture_status"] = "partial"
                result_item["mode_errors"] = mode_errors
                results["fixture_partial_count"] += 1
            else:
                result_item["fixture_status"] = "ok"
                results["fixture_ok_count"] += 1
        except Exception as exc:  # pragma: no cover - depends on hostile corpus inputs
            result_item["fixture_status"] = "error"
            result_item["fixture_error"] = f"{type(exc).__name__}: {exc}"
            results["fixture_error_count"] += 1
        results["items"].append(result_item)

    return results


def write_corpus_fixture_results(results: dict, path: str) -> int:
    """Write fixture-run results to disk."""
    text = json.dumps(results, indent=2, sort_keys=True)
    Path(path).write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


__all__ = [
    "build_corpus_manifest",
    "load_corpus_manifest",
    "write_corpus_manifest",
    "select_corpus_manifest_entries",
    "run_corpus_fixture",
    "write_corpus_fixture_results",
]
