"""Python code generation from reverse-engineered snapshots.

Extracted from _reverse_legacy.py: the generate_*_python_* entry points and
their codegen-only helpers. Shared lower-level helpers stay in _reverse_legacy
and are imported below.
"""

from __future__ import annotations

import copy
from typing import Any

from ._reverse_legacy import (
    DEFAULT_AUDIO_IO_BOXES,
    DEVICE_TYPE_TO_CODE_CONSTANT,
    _assign_parameter_bank_statements,
    _box_builder_statement,
    _call_statement,
    _controller_shell_helper_call,
    _device_ctor_for_snapshot,
    _dsp_add_statement,
    _line_key_from_wrapped,
    _python_literal,
    _recipe_call_statement,
    _semantic_jsui_filenames,
    _snapshot_graph,
    _support_file_statements,
    _support_files_by_name,
    _wrapped_boxes_for_candidate,
    _wrapped_lines_for_candidate,
    analyze_snapshot,
    extract_building_block_candidates,
    extract_controller_shell_candidates,
    extract_embedded_ui_shell_candidates,
    extract_first_party_abstraction_family_candidates,
    extract_first_party_abstraction_host_candidates,
    extract_first_party_api_rig_candidates,
    extract_gen_processing_candidates,
    extract_init_dispatch_chain_candidates,
    extract_live_api_normalization_candidates,
    extract_mapping_behavior_traces,
    extract_mapping_semantic_candidates,
    extract_mapping_workflow_candidates,
    extract_named_bus_router_candidates,
    extract_poly_editor_bank_candidates,
    extract_poly_shell_bank_candidates,
    extract_poly_shell_candidates,
    extract_presentation_widget_cluster_candidates,
    extract_sample_buffer_candidates,
    extract_state_bundle_router_candidates,
    snapshot_from_amxd,
    snapshot_from_bridge_payload,
    snapshot_from_device,
)
from .device import Device


def generate_python_from_snapshot(snapshot: dict) -> str:
    """Generate a starter Python rebuild script from a normalized snapshot."""
    device_type = snapshot["device"]["device_type"]
    patcher_literal = _python_literal(snapshot["patcher"])
    support_files = _python_literal(snapshot.get("support_files", []))
    missing_support_files = _python_literal(snapshot.get("missing_support_files", []))
    analysis = _python_literal(snapshot.get("analysis", {}))
    fidelity = _python_literal(snapshot.get("fidelity", {}))
    device_type_constant = DEVICE_TYPE_TO_CODE_CONSTANT.get(device_type, "AUDIO_EFFECT")

    lines = [
        '"""Starter rebuild script generated from an m4l-builder snapshot."""',
        "",
        "import os",
        "",
        "from m4l_builder import write_amxd",
        "from m4l_builder.constants import %s" % device_type_constant,
        "",
        "PATCHER = %s" % patcher_literal,
        "",
        "SUPPORT_FILES = %s" % support_files,
        "",
        "MISSING_SUPPORT_FILES = %s" % missing_support_files,
        "",
        "SNAPSHOT_FIDELITY = %s" % fidelity,
        "",
        "SNAPSHOT_ANALYSIS = %s" % analysis,
        "",
        "",
        "def build(output_path: str) -> int:",
        '    """Write the reverse-engineered device and any recovered sidecars."""',
        "    written = write_amxd(PATCHER, output_path, %s)" % device_type_constant,
        '    output_dir = os.path.dirname(output_path) or "."',
        "    for support in SUPPORT_FILES:",
        '        support_path = os.path.join(output_dir, support["name"])',
        '        with open(support_path, "w", encoding="utf-8") as handle:',
        '            handle.write(support["content"])',
        "    return written",
        "",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(",
        "        'This generated module exposes build(output_path); it does not choose an output path automatically.'",
        "    )",
        "",
    ]

    if snapshot.get("missing_support_files"):
        lines.extend([
            "# Some dependency entries were declared in the source snapshot but their",
            "# sidecar contents could not be recovered automatically:",
            "# %s" % missing_support_files,
            "",
        ])

    return "\n".join(lines)


def generate_builder_python_from_snapshot(snapshot: dict) -> str:
    """Generate a hybrid builder-style Python rebuild script from a snapshot."""
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    fidelity = snapshot.get("fidelity", {})
    imports = ["Device", "AudioEffect", "Instrument", "MidiEffect"]
    support_files_by_name = _support_files_by_name(snapshot)
    semantic_jsui_filenames = _semantic_jsui_filenames(snapshot, support_files_by_name)
    lines = [
        '"""Hybrid builder-style rebuild script generated from an m4l-builder snapshot."""',
        "",
        "import os",
        "",
        "from m4l_builder import %s" % ", ".join(imports),
        "",
        "SNAPSHOT_FIDELITY = %s" % _python_literal(fidelity),
        "",
        "SNAPSHOT_ANALYSIS = %s" % _python_literal(analysis),
        "",
        "",
        "def build_device():",
        "    device = %s" % _device_ctor_for_snapshot(snapshot),
    ]

    lines.extend(_support_file_statements(snapshot, skipped_names=semantic_jsui_filenames))

    skip_default_audio_ids = set()
    if analysis.get("uses_default_audio_io", False):
        skip_default_audio_ids = set(DEFAULT_AUDIO_IO_BOXES)

    for wrapped in snapshot.get("boxes", []):
        box = wrapped.get("box", {})
        if box.get("id") in skip_default_audio_ids:
            continue
        lines.append(_box_builder_statement(box, support_files_by_name))

    for statement in _assign_parameter_bank_statements(snapshot):
        lines.append(statement)

    for line in snapshot.get("lines", []):
        patchline = line.get("patchline", {})
        lines.append(
            _call_statement(
                "add_line",
                [
                    patchline.get("source", [None, 0])[0],
                    patchline.get("source", [None, 0])[1],
                    patchline.get("destination", [None, 0])[0],
                    patchline.get("destination", [None, 0])[1],
                ],
                {},
            )
        )

    lines.extend([
        "    return device",
        "",
        "",
        "def build(output_path: str) -> int:",
        "    return build_device().build(output_path)",
        "",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(",
        "        'This generated module exposes build_device() and build(output_path); it does not choose an output path automatically.'",
        "    )",
        "",
    ])

    return "\n".join(lines)


def _select_live_api_codegen_candidates(
    snapshot: dict,
    *,
    allowed_levels: set[str],
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
) -> tuple[list[dict], list[dict]]:
    selected = []
    manual_review = []
    for candidate in extract_live_api_normalization_candidates(snapshot):
        candidate_level = candidate.get("normalization_level")
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        if any(box_id in consumed_box_ids for box_id in candidate_box_ids):
            continue
        if any(line_key in consumed_line_keys for line_key in candidate_line_keys):
            continue
        if candidate_level in allowed_levels:
            selected.append(candidate)
        elif candidate_level == "manual_review":
            manual_review.append(candidate)
    return selected, manual_review


def _select_controller_shell_codegen_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
) -> list[dict]:
    selected = []
    for candidate in extract_controller_shell_candidates(snapshot):
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        if any(box_id in consumed_box_ids for box_id in candidate_box_ids):
            continue
        if any(line_key in consumed_line_keys for line_key in candidate_line_keys):
            continue
        selected.append(candidate)
    return selected


def _select_embedded_ui_shell_codegen_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
) -> list[dict]:
    selected = []
    for candidate in extract_embedded_ui_shell_candidates(snapshot):
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        if any(box_id in consumed_box_ids for box_id in candidate_box_ids):
            continue
        if any(line_key in consumed_line_keys for line_key in candidate_line_keys):
            continue
        selected.append(candidate)
    return selected


def _select_first_party_helper_codegen_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
    prefer_semantic_group_box_ids: set[str] | None = None,
) -> list[dict]:
    selected = []
    local_consumed_box_ids = set(consumed_box_ids)
    local_consumed_line_keys = set(consumed_line_keys)
    prefer_semantic_group_box_ids = prefer_semantic_group_box_ids or set()
    for extractor in (
        extract_poly_shell_bank_candidates,
        extract_poly_shell_candidates,
        extract_init_dispatch_chain_candidates,
        extract_named_bus_router_candidates,
    ):
        for candidate in extractor(snapshot):
            candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
            candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
            if (
                candidate.get("candidate_name") in {"poly_shell_bank", "poly_shell"}
                and prefer_semantic_group_box_ids
                and set(candidate_box_ids).issubset(prefer_semantic_group_box_ids)
            ):
                continue
            if any(box_id in local_consumed_box_ids for box_id in candidate_box_ids):
                continue
            if any(line_key in local_consumed_line_keys for line_key in candidate_line_keys):
                continue
            selected.append(candidate)
            local_consumed_box_ids.update(candidate_box_ids)
            local_consumed_line_keys.update(candidate_line_keys)
    return sorted(selected, key=lambda item: (item["first_box_index"], item["candidate_name"]))


def _controller_shell_helper_statements(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str],
) -> list[str]:
    helper = copy.deepcopy(candidate.get("helper_call") or {})
    if not helper:
        helper = _controller_shell_helper_call(
            snapshot,
            candidate,
            skip_default_audio_ids=skip_default_audio_ids,
        )
    else:
        helper["kwargs"] = copy.deepcopy(helper.get("kwargs", {}))
        helper["kwargs"]["boxes"] = _wrapped_boxes_for_candidate(
            snapshot,
            candidate,
            skip_default_audio_ids=skip_default_audio_ids,
        )
    helper_name = helper.get("name")
    lines = [f"    # semantic target: {helper_name}"]
    for evidence in candidate.get("evidence", []):
        lines.append(f"    # {evidence}")
    lines.append(
        _dsp_add_statement(
            helper_name,
            helper.get("positional", []),
            helper.get("kwargs", {}),
        )
    )
    return lines


def _candidate_helper_statements(candidate: dict) -> list[str]:
    helper = copy.deepcopy(candidate.get("helper_call") or {})
    helper_name = helper.get("name") or candidate.get("candidate_name")
    lines = [f"    # semantic target: {helper_name}"]
    for evidence in candidate.get("evidence", []):
        lines.append(f"    # {evidence}")
    lines.append(
        _dsp_add_statement(
            helper_name,
            helper.get("positional", []),
            helper.get("kwargs", {}),
        )
    )
    return lines


def _embedded_ui_shell_helper_statements(candidate: dict) -> list[str]:
    return _candidate_helper_statements(candidate)


def _trim_candidate_to_unconsumed(
    snapshot: dict,
    candidate: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
    skip_default_audio_ids: set[str],
) -> dict | None:
    boxes_by_id, box_indices, _line_keys = _snapshot_graph(snapshot)
    remaining_box_ids = [
        box_id
        for box_id in candidate.get("box_ids", [])
        if box_id not in consumed_box_ids and box_id not in skip_default_audio_ids
    ]
    if not remaining_box_ids:
        return None

    remaining_box_id_set = set(remaining_box_ids)
    remaining_line_keys = [
        line_key
        for line_key in candidate.get("line_keys", [])
        if line_key not in consumed_line_keys
        and line_key[0] in remaining_box_id_set
        and line_key[2] in remaining_box_id_set
    ]
    trimmed = copy.deepcopy(candidate)
    trimmed["box_ids"] = remaining_box_ids
    trimmed["line_keys"] = remaining_line_keys
    trimmed["first_box_index"] = min(box_indices.get(box_id, 10 ** 9) for box_id in remaining_box_ids)
    trimmed["consume_box_ids"] = copy.deepcopy(remaining_box_ids)
    return trimmed


def _select_semantic_group_candidates(
    snapshot: dict,
    *,
    consumed_box_ids: set[str],
    consumed_line_keys: set[tuple],
    skip_default_audio_ids: set[str],
) -> list[dict]:
    selected = []
    local_consumed_box_ids = set(consumed_box_ids)
    local_consumed_line_keys = set(consumed_line_keys)
    for extractor in (
        extract_mapping_semantic_candidates,
        extract_mapping_workflow_candidates,
        extract_poly_editor_bank_candidates,
        extract_first_party_api_rig_candidates,
        extract_first_party_abstraction_family_candidates,
        extract_first_party_abstraction_host_candidates,
        extract_gen_processing_candidates,
        extract_sample_buffer_candidates,
        extract_presentation_widget_cluster_candidates,
        extract_building_block_candidates,
        extract_state_bundle_router_candidates,
    ):
        for candidate in extractor(snapshot):
            trimmed = _trim_candidate_to_unconsumed(
                snapshot,
                candidate,
                consumed_box_ids=local_consumed_box_ids,
                consumed_line_keys=local_consumed_line_keys,
                skip_default_audio_ids=skip_default_audio_ids,
            )
            if not trimmed:
                continue
            selected.append(trimmed)
            local_consumed_box_ids.update(trimmed.get("box_ids", []))
            local_consumed_line_keys.update(trimmed.get("line_keys", []))
    return sorted(selected, key=lambda item: (item["first_box_index"], item["candidate_name"]))


def _semantic_group_candidate_statements(
    snapshot: dict,
    candidate: dict,
    *,
    skip_default_audio_ids: set[str],
) -> list[str]:
    boxes = _wrapped_boxes_for_candidate(
        snapshot,
        candidate,
        skip_default_audio_ids=skip_default_audio_ids,
    )
    lines = _wrapped_lines_for_candidate(snapshot, candidate)
    helper_name = candidate.get("candidate_name")
    statement_lines = [f"    # semantic group: {helper_name}"]
    for evidence in candidate.get("evidence", []):
        statement_lines.append(f"    # {evidence}")
    statement_lines.extend([
        "    device.add_dsp(",
        f"        {_python_literal(boxes)},",
        f"        {_python_literal(lines)},",
        "    )",
    ])
    return statement_lines


def _structured_generator_source(
    snapshot: dict,
    *,
    docstring: str,
    allowed_live_api_levels: set[str],
    include_manual_review_notes: bool,
    include_controller_shell_candidates: bool,
    include_embedded_ui_shell_candidates: bool,
    include_semantic_group_candidates: bool = False,
) -> str:
    analysis = snapshot.get("analysis") or analyze_snapshot(snapshot)
    fidelity = snapshot.get("fidelity", {})
    patterns = analysis.get("patterns", [])
    recipes = analysis.get("recipes", [])
    support_files_by_name = _support_files_by_name(snapshot)
    semantic_jsui_filenames = _semantic_jsui_filenames(snapshot, support_files_by_name)
    skip_default_audio_ids = set()
    if analysis.get("uses_default_audio_io", False):
        skip_default_audio_ids = set(DEFAULT_AUDIO_IO_BOXES)
    live_api_candidates_all = extract_live_api_normalization_candidates(snapshot)
    controller_shell_candidates_all = extract_controller_shell_candidates(snapshot)
    embedded_ui_shell_candidates_all = extract_embedded_ui_shell_candidates(snapshot)
    named_bus_router_candidates_all = extract_named_bus_router_candidates(snapshot)
    init_dispatch_chain_candidates_all = extract_init_dispatch_chain_candidates(snapshot)
    poly_shell_candidates_all = extract_poly_shell_candidates(snapshot)
    poly_shell_bank_candidates_all = extract_poly_shell_bank_candidates(snapshot)
    poly_editor_bank_candidates_all = extract_poly_editor_bank_candidates(snapshot)
    mapping_behavior_traces_all = extract_mapping_behavior_traces(snapshot)
    mapping_semantic_candidates_all = extract_mapping_semantic_candidates(snapshot)
    mapping_workflow_candidates_all = extract_mapping_workflow_candidates(snapshot)
    state_bundle_router_candidates_all = extract_state_bundle_router_candidates(snapshot)
    sample_buffer_candidates_all = extract_sample_buffer_candidates(snapshot)
    gen_processing_candidates_all = extract_gen_processing_candidates(snapshot)
    presentation_widget_cluster_candidates_all = extract_presentation_widget_cluster_candidates(snapshot)
    first_party_api_rig_candidates_all = extract_first_party_api_rig_candidates(snapshot)
    first_party_abstraction_host_candidates_all = extract_first_party_abstraction_host_candidates(snapshot)
    first_party_abstraction_family_candidates_all = extract_first_party_abstraction_family_candidates(snapshot)
    building_block_candidates_all = extract_building_block_candidates(snapshot)
    semantic_group_preference_box_ids: set[str] = set()
    if include_semantic_group_candidates:
        for candidate in extract_mapping_semantic_candidates(snapshot):
            semantic_group_preference_box_ids.update(candidate.get("box_ids", []))
        for candidate in extract_mapping_workflow_candidates(snapshot):
            semantic_group_preference_box_ids.update(candidate.get("box_ids", []))
        for candidate in extract_poly_editor_bank_candidates(snapshot):
            semantic_group_preference_box_ids.update(candidate.get("box_ids", []))

    imports = ["Device", "AudioEffect", "Instrument", "MidiEffect"]
    optimized_recipes = [recipe for recipe in recipes if recipe.get("recipeizable")]
    for recipe in optimized_recipes:
        recipe_name = recipe.get("recipe", {}).get("name")
        if recipe_name and recipe_name not in imports:
            imports.append(recipe_name)

    consumed_box_ids = set()
    consumed_line_keys = set()
    recipes_by_index: dict[int, list[dict]] = {}
    for recipe in optimized_recipes:
        consumed_box_ids.update(recipe["box_ids"])
        consumed_line_keys.update(recipe["line_keys"])
        recipes_by_index.setdefault(recipe["first_box_index"], []).append(recipe)

    first_party_helper_candidates = _select_first_party_helper_codegen_candidates(
        snapshot,
        consumed_box_ids=consumed_box_ids,
        consumed_line_keys=consumed_line_keys,
        prefer_semantic_group_box_ids=semantic_group_preference_box_ids,
    )
    for candidate in first_party_helper_candidates:
        helper_name = candidate.get("helper_call", {}).get("name") or candidate.get("candidate_name")
        if helper_name and helper_name not in imports:
            imports.append(helper_name)
    for candidate in first_party_helper_candidates:
        consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    optimized_patterns = []
    for pattern in patterns:
        if not pattern.get("helperizable"):
            continue
        if any(box_id in consumed_box_ids for box_id in pattern["box_ids"]):
            continue
        if any(line_key in consumed_line_keys for line_key in pattern["line_keys"]):
            continue
        optimized_patterns.append(pattern)

    for pattern in optimized_patterns:
        helper_name = pattern.get("helper", {}).get("name")
        if helper_name and helper_name not in imports:
            imports.append(helper_name)

    controller_shell_candidates = []
    if include_controller_shell_candidates:
        controller_shell_candidates = _select_controller_shell_codegen_candidates(
            snapshot,
            consumed_box_ids=consumed_box_ids,
            consumed_line_keys=consumed_line_keys,
        )
        for candidate in controller_shell_candidates:
            helper_name = candidate.get("helper_call", {}).get("name") or candidate.get("candidate_name")
            if helper_name and helper_name not in imports:
                imports.append(helper_name)
        for candidate in controller_shell_candidates:
            consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
            consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    embedded_ui_shell_candidates = []
    if include_embedded_ui_shell_candidates:
        embedded_ui_shell_candidates = _select_embedded_ui_shell_codegen_candidates(
            snapshot,
            consumed_box_ids=consumed_box_ids,
            consumed_line_keys=consumed_line_keys,
        )
        for candidate in embedded_ui_shell_candidates:
            helper_name = candidate.get("helper_call", {}).get("name") or candidate.get("candidate_name")
            if helper_name and helper_name not in imports:
                imports.append(helper_name)
        for candidate in embedded_ui_shell_candidates:
            consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
            consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    live_api_candidates, manual_review_live_api = _select_live_api_codegen_candidates(
        snapshot,
        allowed_levels=allowed_live_api_levels,
        consumed_box_ids=consumed_box_ids,
        consumed_line_keys=consumed_line_keys,
    )
    for candidate in live_api_candidates:
        helper_name = candidate.get("helper_call", {}).get("name")
        if helper_name and helper_name not in imports:
            imports.append(helper_name)
    for candidate in live_api_candidates:
        consumed_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        consumed_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))

    semantic_group_candidates = []
    if include_semantic_group_candidates:
        semantic_group_candidates = _select_semantic_group_candidates(
            snapshot,
            consumed_box_ids=consumed_box_ids,
            consumed_line_keys=consumed_line_keys,
            skip_default_audio_ids=skip_default_audio_ids,
        )
        for candidate in semantic_group_candidates:
            consumed_box_ids.update(candidate.get("box_ids", []))
            consumed_line_keys.update(candidate.get("line_keys", []))

    matched_box_ids = set()
    matched_line_keys = set()
    first_party_helpers_by_index: dict[int, list[dict]] = {}
    for candidate in first_party_helper_candidates:
        matched_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))
        first_party_helpers_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    controller_shells_by_index: dict[int, list[dict]] = {}
    for candidate in controller_shell_candidates:
        matched_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))
        controller_shells_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    embedded_ui_shells_by_index: dict[int, list[dict]] = {}
    for candidate in embedded_ui_shell_candidates:
        matched_box_ids.update(candidate.get("consume_box_ids") or candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", []))
        embedded_ui_shells_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    live_api_helpers_by_index: dict[int, list[dict]] = {}
    for candidate in live_api_candidates:
        candidate_box_ids = candidate.get("consume_box_ids") or candidate.get("box_ids", [])
        candidate_line_keys = candidate.get("line_keys") or candidate.get("helper_call", {}).get("line_keys", [])
        matched_box_ids.update(candidate_box_ids)
        matched_line_keys.update(candidate_line_keys)
        live_api_helpers_by_index.setdefault(candidate["first_box_index"], []).append(candidate)
    semantic_groups_by_index: dict[int, list[dict]] = {}
    for candidate in semantic_group_candidates:
        matched_box_ids.update(candidate.get("box_ids", []))
        matched_line_keys.update(candidate.get("line_keys", []))
        semantic_groups_by_index.setdefault(candidate["first_box_index"], []).append(candidate)

    patterns_by_index: dict[int, list[dict]] = {}
    for pattern in optimized_patterns:
        matched_box_ids.update(pattern["box_ids"])
        matched_line_keys.update(pattern["line_keys"])
        patterns_by_index.setdefault(pattern["first_box_index"], []).append(pattern)
    matched_box_ids.update(consumed_box_ids)
    matched_line_keys.update(consumed_line_keys)

    lines = [
        docstring,
        "",
        "import os",
        "",
        "from m4l_builder import %s" % ", ".join(imports),
        "",
        "SNAPSHOT_FIDELITY = %s" % _python_literal(fidelity),
        "",
        "SNAPSHOT_ANALYSIS = %s" % _python_literal(analysis),
        "",
        "SNAPSHOT_PATTERNS = %s" % _python_literal(patterns),
        "",
        "SNAPSHOT_RECIPES = %s" % _python_literal(recipes),
        "",
        "SNAPSHOT_LIVE_API_NORMALIZATION_CANDIDATES = %s" % _python_literal(live_api_candidates_all),
        "",
        "SNAPSHOT_CONTROLLER_SHELL_CANDIDATES = %s" % _python_literal(controller_shell_candidates_all),
        "",
        "SNAPSHOT_EMBEDDED_UI_SHELL_CANDIDATES = %s" % _python_literal(embedded_ui_shell_candidates_all),
        "",
        "SNAPSHOT_NAMED_BUS_ROUTER_CANDIDATES = %s" % _python_literal(named_bus_router_candidates_all),
        "",
        "SNAPSHOT_INIT_DISPATCH_CHAIN_CANDIDATES = %s" % _python_literal(init_dispatch_chain_candidates_all),
        "",
        "SNAPSHOT_POLY_SHELL_CANDIDATES = %s" % _python_literal(poly_shell_candidates_all),
        "",
        "SNAPSHOT_POLY_SHELL_BANK_CANDIDATES = %s" % _python_literal(poly_shell_bank_candidates_all),
        "",
        "SNAPSHOT_POLY_EDITOR_BANK_CANDIDATES = %s" % _python_literal(poly_editor_bank_candidates_all),
        "",
        "SNAPSHOT_MAPPING_BEHAVIOR_TRACES = %s" % _python_literal(mapping_behavior_traces_all),
        "",
        "SNAPSHOT_MAPPING_SEMANTIC_CANDIDATES = %s" % _python_literal(mapping_semantic_candidates_all),
        "",
        "SNAPSHOT_MAPPING_WORKFLOW_CANDIDATES = %s" % _python_literal(mapping_workflow_candidates_all),
        "",
        "SNAPSHOT_STATE_BUNDLE_ROUTER_CANDIDATES = %s" % _python_literal(state_bundle_router_candidates_all),
        "",
        "SNAPSHOT_SAMPLE_BUFFER_CANDIDATES = %s" % _python_literal(sample_buffer_candidates_all),
        "",
        "SNAPSHOT_GEN_PROCESSING_CANDIDATES = %s" % _python_literal(gen_processing_candidates_all),
        "",
        "SNAPSHOT_PRESENTATION_WIDGET_CLUSTER_CANDIDATES = %s" % _python_literal(presentation_widget_cluster_candidates_all),
        "",
        "SNAPSHOT_FIRST_PARTY_API_RIG_CANDIDATES = %s" % _python_literal(first_party_api_rig_candidates_all),
        "",
        "SNAPSHOT_FIRST_PARTY_ABSTRACTION_HOST_CANDIDATES = %s" % _python_literal(first_party_abstraction_host_candidates_all),
        "",
        "SNAPSHOT_FIRST_PARTY_ABSTRACTION_FAMILY_CANDIDATES = %s" % _python_literal(first_party_abstraction_family_candidates_all),
        "",
        "SNAPSHOT_BUILDING_BLOCK_CANDIDATES = %s" % _python_literal(building_block_candidates_all),
        "",
        "",
    ]

    lines.extend([
        "def build_device():",
        "    device = %s" % _device_ctor_for_snapshot(snapshot),
    ])

    if include_manual_review_notes and manual_review_live_api:
        lines.append("    # Live API clusters left expanded for manual review:")
        for candidate in manual_review_live_api:
            lines.append(
                "    # %s -> %s (%s)"
                % (
                    candidate.get("helper_name"),
                    ", ".join(candidate.get("box_ids", [])),
                    ", ".join(candidate.get("blocking_factors", [])),
                )
            )

    lines.extend(_support_file_statements(snapshot, skipped_names=semantic_jsui_filenames))

    for index, wrapped in enumerate(snapshot.get("boxes", [])):
        for candidate in first_party_helpers_by_index.get(index, []):
            lines.extend(_candidate_helper_statements(candidate))
        for recipe in recipes_by_index.get(index, []):
            recipe_call = recipe["recipe"]
            lines.append(
                _recipe_call_statement(
                    recipe_call["name"],
                    recipe_call.get("positional", []),
                    recipe_call.get("kwargs", {}),
                )
            )
        for candidate in controller_shells_by_index.get(index, []):
            lines.extend(
                _controller_shell_helper_statements(
                    snapshot,
                    candidate,
                    skip_default_audio_ids=skip_default_audio_ids,
                )
            )
        for candidate in embedded_ui_shells_by_index.get(index, []):
            lines.extend(_embedded_ui_shell_helper_statements(candidate))
        for candidate in live_api_helpers_by_index.get(index, []):
            helper = candidate["helper_call"]
            lines.append(
                _dsp_add_statement(
                    helper["name"],
                    helper.get("positional", []),
                    helper.get("kwargs", {}),
                )
            )
        for candidate in semantic_groups_by_index.get(index, []):
            lines.extend(
                _semantic_group_candidate_statements(
                    snapshot,
                    candidate,
                    skip_default_audio_ids=skip_default_audio_ids,
                )
            )
        for pattern in patterns_by_index.get(index, []):
            helper = pattern["helper"]
            lines.append(
                _dsp_add_statement(
                    helper["name"],
                    helper.get("positional", []),
                    helper.get("kwargs", {}),
                )
            )

        box = wrapped.get("box", {})
        box_id = box.get("id")
        if box_id in skip_default_audio_ids or box_id in matched_box_ids:
            continue
        lines.append(_box_builder_statement(box, support_files_by_name))

    for statement in _assign_parameter_bank_statements(snapshot):
        lines.append(statement)

    for line in snapshot.get("lines", []):
        line_key = _line_key_from_wrapped(line)
        if line_key in matched_line_keys:
            continue
        patchline = line.get("patchline", {})
        lines.append(
            _call_statement(
                "add_line",
                [
                    patchline.get("source", [None, 0])[0],
                    patchline.get("source", [None, 0])[1],
                    patchline.get("destination", [None, 0])[0],
                    patchline.get("destination", [None, 0])[1],
                ],
                {},
            )
        )

    lines.extend([
        "    return device",
        "",
        "",
        "def build(output_path: str) -> int:",
        "    return build_device().build(output_path)",
        "",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(",
        "        'This generated module exposes build_device() and build(output_path); it does not choose an output path automatically.'",
        "    )",
        "",
    ])

    return "\n".join(lines)


def generate_optimized_python_from_snapshot(snapshot: dict) -> str:
    """Generate an exact-safe builder script that emits recognized helpers where possible."""
    return _structured_generator_source(
        snapshot,
        docstring='"""Optimized builder-style rebuild script generated from an m4l-builder snapshot."""',
        allowed_live_api_levels={"exact"},
        include_manual_review_notes=False,
        include_controller_shell_candidates=True,
        include_embedded_ui_shell_candidates=True,
    )


def generate_semantic_python_from_snapshot(snapshot: dict) -> str:
    """Generate a semantic builder script that also normalizes safe Live API opportunities."""
    return _structured_generator_source(
        snapshot,
        docstring='"""Semantic builder-style rebuild script generated from an m4l-builder snapshot."""',
        allowed_live_api_levels={"exact", "normalized_safe", "normalized_with_binding"},
        include_manual_review_notes=True,
        include_controller_shell_candidates=True,
        include_embedded_ui_shell_candidates=True,
        include_semantic_group_candidates=True,
    )


def generate_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> normalized snapshot -> starter Python."""
    return generate_python_from_snapshot(snapshot_from_amxd(path))


def generate_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> normalized snapshot -> starter Python."""
    return generate_python_from_snapshot(snapshot_from_device(device))


def generate_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> normalized snapshot -> starter Python."""
    return generate_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


def generate_builder_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> snapshot -> hybrid builder-style Python."""
    return generate_builder_python_from_snapshot(snapshot_from_amxd(path))


def generate_builder_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> snapshot -> hybrid builder-style Python."""
    return generate_builder_python_from_snapshot(snapshot_from_device(device))


def generate_builder_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> snapshot -> hybrid builder-style Python."""
    return generate_builder_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


def generate_optimized_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> snapshot -> optimized builder-style Python."""
    return generate_optimized_python_from_snapshot(snapshot_from_amxd(path))


def generate_optimized_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> snapshot -> optimized builder-style Python."""
    return generate_optimized_python_from_snapshot(snapshot_from_device(device))


def generate_optimized_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> snapshot -> optimized builder-style Python."""
    return generate_optimized_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))


def generate_semantic_python_from_amxd(path: str) -> str:
    """Convenience helper for AMXD -> snapshot -> semantic builder-style Python."""
    return generate_semantic_python_from_snapshot(snapshot_from_amxd(path))


def generate_semantic_python_from_device(device: Device) -> str:
    """Convenience helper for Device -> snapshot -> semantic builder-style Python."""
    return generate_semantic_python_from_snapshot(snapshot_from_device(device))


def generate_semantic_python_from_bridge_payload(**kwargs: Any) -> str:
    """Convenience helper for bridge payload -> snapshot -> semantic builder-style Python."""
    return generate_semantic_python_from_snapshot(snapshot_from_bridge_payload(**kwargs))
