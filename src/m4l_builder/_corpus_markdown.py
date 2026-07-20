"""Markdown rendering and disk-write helpers for corpus/mapping/dossier reports.

Extracted from corpus_analysis.py (god-file split); re-exported by it."""
from __future__ import annotations

import json
from pathlib import Path


def source_lane_profiles_markdown(profiles: list[dict]) -> str:
    """Render lane comparison profiles as markdown."""
    lines = ["# AMXD Source Lane Profiles", ""]
    if not profiles:
        lines.extend(["- None", ""])
        return "\n".join(lines)

    def _entry_names(entries: list[dict], *, with_coverage: bool = False) -> str:
        if not entries:
            return "None"
        if with_coverage:
            return ", ".join(f"{entry['name']} ({entry['coverage']})" for entry in entries[:5])
        return ", ".join(entry["name"] for entry in entries[:5])

    for profile in profiles:
        lines.extend([
            f"## {profile['lane']}",
            "",
            f"- Files: `{profile['count']}`",
            f"- Avg boxes / lines: `{profile['avg_boxes']}` / `{profile['avg_lines']}`",
            f"- Files with missing support: `{profile['files_with_missing_support']}`",
            f"- Pack names: `{_entry_names(profile.get('pack_names', []))}`",
            f"- Top motifs: `{_entry_names(profile.get('top_motif_signatures', []), with_coverage=True)}`",
            f"- Live API helpers: `{_entry_names(profile.get('top_live_api_helpers', []), with_coverage=True)}`",
            f"- Controller shells: `{_entry_names(profile.get('top_controller_shells', []), with_coverage=True)}`",
            f"- Behavior hints: `{_entry_names(profile.get('top_behavior_hints', []), with_coverage=True)}`",
            f"- Embedded UI shells: `{_entry_names(profile.get('top_embedded_ui_shells', []), with_coverage=True)}`",
            f"- Sample-buffer candidates: `{_entry_names(profile.get('top_sample_buffer_candidates', []), with_coverage=True)}`",
            f"- Gen-processing candidates: `{_entry_names(profile.get('top_gen_processing_candidates', []), with_coverage=True)}`",
            f"- Embedded sample-buffer candidates: `{_entry_names(profile.get('top_embedded_sample_buffer_candidates', []), with_coverage=True)}`",
            f"- Embedded gen-processing candidates: `{_entry_names(profile.get('top_embedded_gen_processing_candidates', []), with_coverage=True)}`",
            f"- Presentation widget clusters: `{_entry_names(profile.get('top_presentation_widget_clusters', []), with_coverage=True)}`",
            f"- Poly-shell banks: `{_entry_names(profile.get('top_poly_shell_banks', []), with_coverage=True)}`",
            f"- Poly-editor banks: `{_entry_names(profile.get('top_poly_editor_banks', []), with_coverage=True)}`",
            f"- First-party API rigs: `{_entry_names(profile.get('top_first_party_api_rigs', []), with_coverage=True)}`",
            f"- First-party abstraction hosts: `{_entry_names(profile.get('top_first_party_abstraction_hosts', []), with_coverage=True)}`",
            f"- First-party abstraction families: `{_entry_names(profile.get('top_first_party_abstraction_families', []), with_coverage=True)}`",
            f"- Building blocks: `{_entry_names(profile.get('top_building_blocks', []), with_coverage=True)}`",
            "",
        ])
    return "\n".join(lines)


def reference_device_dossiers_markdown(dossiers: list[dict]) -> str:
    """Render reference-device dossiers as markdown."""
    lines = ["# AMXD Reference Device Dossiers", ""]
    if not dossiers:
        lines.extend(["- None", ""])
        return "\n".join(lines)
    for dossier in dossiers:
        if dossier.get("error"):
            lines.extend([
                f"## {dossier['name']}",
                "",
                f"- Path: `{dossier['path']}`",
                f"- Error: `{dossier['error']}`",
                f"- Fallback zones: `{', '.join(dossier['fallback_zones']) or 'None'}`",
                "",
            ])
            continue
        lines.extend([
            f"## {dossier['name']}",
            "",
            f"- Path: `{dossier['path']}`",
            f"- Device type: `{dossier['device_type']}`",
            f"- Source lane: `{dossier.get('source', {}).get('source_lane')}`",
            f"- Pack section: `{dossier.get('source', {}).get('pack_name')} / {dossier.get('source', {}).get('pack_section')}`",
            f"- Boxes / lines: `{dossier['box_count']}` / `{dossier['line_count']}`",
            f"- Recovered classes: `{', '.join(dossier['recovered_classes']) or 'None'}`",
            f"- Behavior hints: `{', '.join(dossier.get('behavior_hints', [])) or 'None'}`",
            f"- Mapping behavior traces: `{', '.join(dossier.get('mapping_behavior_traces', [])) or 'None'}`",
            f"- Raw add_box / add_line count: `{dossier['raw_add_box_count']}` / `{dossier['raw_add_line_count']}`",
            f"- Semantic add_box / add_line count: `{dossier['semantic_add_box_count']}` / `{dossier['semantic_add_line_count']}`",
            f"- Semantic helper calls: `{', '.join(f'{name} x{count}' for name, count in sorted(dossier['semantic_helper_calls'].items())) or 'None'}`",
            f"- Semantic lift delta: `{dossier['semantic_add_box_delta']}`",
            f"- Structural lift score: `{dossier['structural_lift_score']}`",
            f"- Fallback zones: `{', '.join(dossier['fallback_zones']) or 'None'}`",
            "",
        ])
        product_brief = dossier.get("product_brief")
        if product_brief:
            lines.extend([
                "### Product Brief",
                "",
                f"- Product class: `{product_brief.get('product_class')}`",
                f"- Closest reference: `{product_brief.get('closest_reference')}`",
                f"- Product read: `{product_brief.get('product_thesis', '')}`",
                f"- Value model: `{product_brief.get('value_model', '')}`",
                f"- Target model: `{product_brief.get('target_model', '')}`",
                f"- Trigger model: `{product_brief.get('trigger_model', '')}`",
                f"- Essential controls: `{', '.join(product_brief.get('essential_controls', [])) or 'None'}`",
                f"- Essential subsystems: `{', '.join(product_brief.get('essential_subsystems', [])) or 'None'}`",
                f"- Accidental complexity: `{', '.join(product_brief.get('accidental_complexity', [])) or 'None'}`",
                f"- Build cleanly as: `{product_brief.get('build_cleanly_as', '')}`",
                f"- Open questions: `{', '.join(product_brief.get('open_questions', [])) or 'None'}`",
                f"- Confidence: `{product_brief.get('confidence', 'unknown')}`",
                "",
            ])
    return "\n".join(lines)


def corpus_comparison_markdown(comparison: dict) -> str:
    """Render a multi-corpus comparison report as markdown."""
    lines = ["# AMXD Corpus Comparison", ""]
    reports = comparison.get("reports", [])
    if not reports:
        lines.extend(["- None", ""])
        return "\n".join(lines)
    for report in reports:
        lines.extend([
            f"## {report['label']}",
            "",
            f"- Files scanned / ok / error: `{report['count']}` / `{report['ok']}` / `{report['error']}`",
            f"- Avg boxes / lines: `{report['avg_boxes']}` / `{report['avg_lines']}`",
            f"- Top motifs: `{', '.join(entry['name'] for entry in report.get('top_motifs', [])) or 'None'}`",
            f"- Live API helpers: `{', '.join(entry['name'] for entry in report.get('top_live_api_helpers', [])) or 'None'}`",
            f"- Controller shells: `{', '.join(entry['name'] for entry in report.get('top_controller_shells', [])) or 'None'}`",
            f"- Behavior hints: `{', '.join(entry['name'] for entry in report.get('top_behavior_hints', [])) or 'None'}`",
            f"- Embedded UI shells: `{', '.join(entry['name'] for entry in report.get('top_embedded_ui_shells', [])) or 'None'}`",
            f"- Sample-buffer candidates: `{', '.join(entry['name'] for entry in report.get('top_sample_buffer_candidates', [])) or 'None'}`",
            f"- Gen-processing candidates: `{', '.join(entry['name'] for entry in report.get('top_gen_processing_candidates', [])) or 'None'}`",
            f"- Embedded sample-buffer candidates: `{', '.join(entry['name'] for entry in report.get('top_embedded_sample_buffer_candidates', [])) or 'None'}`",
            f"- Embedded gen-processing candidates: `{', '.join(entry['name'] for entry in report.get('top_embedded_gen_processing_candidates', [])) or 'None'}`",
            f"- Presentation widget clusters: `{', '.join(entry['name'] for entry in report.get('top_presentation_widget_clusters', [])) or 'None'}`",
            f"- Poly-shell banks: `{', '.join(entry['name'] for entry in report.get('top_poly_shell_banks', [])) or 'None'}`",
            f"- Poly-editor banks: `{', '.join(entry['name'] for entry in report.get('top_poly_editor_banks', [])) or 'None'}`",
            f"- First-party abstraction hosts: `{', '.join(entry['name'] for entry in report.get('top_first_party_abstraction_hosts', [])) or 'None'}`",
            f"- First-party abstraction families: `{', '.join(entry['name'] for entry in report.get('top_first_party_abstraction_families', [])) or 'None'}`",
            f"- Building blocks: `{', '.join(entry['name'] for entry in report.get('top_building_blocks', [])) or 'None'}`",
            f"- Pack sections: `{', '.join(entry['name'] for entry in report.get('top_pack_sections', [])) or 'None'}`",
            "",
        ])
    return "\n".join(lines)


def mapping_lane_report_markdown(report: dict) -> str:
    """Render a mapping/modulation lane report as markdown."""
    summary = report.get("summary", {})
    lines = [
        "# Mapping / Modulation Lane Report",
        "",
        f"- Devices in lane: `{summary.get('count', 0)}`",
        f"- Files with behavior hints: `{summary.get('files_with_behavior_hints', 0)}`",
        f"- Files with mapping behavior traces: `{summary.get('files_with_mapping_behavior_traces', 0)}`",
        f"- Files with mapping semantic candidates: `{summary.get('files_with_mapping_semantic_candidates', 0)}`",
        f"- Files with mapping workflow candidates: `{summary.get('files_with_mapping_workflow_candidates', 0)}`",
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

    add_frequency_section("Product Classes", report.get("product_classes", []))
    add_frequency_section("Closest References", report.get("closest_references", []))
    add_frequency_section("Source Lanes", report.get("source_lanes", []))
    add_frequency_section("Top Source Families", report.get("source_families", []))
    add_frequency_section("Top Behavior Hints", report.get("behavior_hints", []))
    add_frequency_section("Top Mapping Behavior Traces", report.get("mapping_behavior_traces", []))
    add_frequency_section("Top Mapping Semantic Candidates", report.get("mapping_semantic_candidates", []))

    lines.append("## Top Devices")
    lines.append("")
    top_devices = report.get("top_devices", [])
    if not top_devices:
        lines.extend(["- None", ""])
        return "\n".join(lines)
    for entry in top_devices:
        lines.extend([
            f"### {entry['name']}",
            "",
            f"- Product class: `{entry['product_class']}`",
            f"- Closest reference: `{entry['closest_reference']}`",
            f"- Product read: `{entry.get('product_thesis', '')}`",
            f"- Source lane/family: `{entry.get('source_lane')}` / `{entry.get('source_family')}`",
            f"- Semantic candidates: `{', '.join(entry.get('mapping_semantic_candidates', [])) or 'None'}`",
            f"- Behavior traces: `{', '.join(entry.get('mapping_behavior_traces', [])) or 'None'}`",
            f"- Behavior hints: `{', '.join(entry.get('behavior_hints', [])) or 'None'}`",
            f"- Value model: `{entry.get('value_model', '') or 'Unknown'}`",
            f"- Target model: `{entry.get('target_model', '') or 'Unknown'}`",
            f"- Trigger model: `{entry.get('trigger_model', '') or 'Unknown'}`",
            f"- Essential controls: `{', '.join(entry.get('essential_controls', [])) or 'None'}`",
            f"- Essential subsystems: `{', '.join(entry.get('essential_subsystems', [])) or 'None'}`",
            f"- Accidental complexity: `{', '.join(entry.get('accidental_complexity', [])) or 'None'}`",
            f"- Build cleanly as: `{entry.get('build_cleanly_as', '') or 'Unknown'}`",
            f"- Open questions: `{', '.join(entry.get('open_questions', [])) or 'None'}`",
            f"- Confidence: `{entry.get('confidence', 'unknown')}`",
            f"- Score: `{entry.get('score', 0)}`",
            "",
        ])
    return "\n".join(lines)


def mapping_product_briefs_markdown(briefs: list[dict]) -> str:
    """Render mapping/modulation product briefs as markdown."""
    lines = ["# Mapping / Modulation Product Briefs", ""]
    if not briefs:
        lines.extend(["- None", ""])
        return "\n".join(lines)
    for brief in briefs:
        lines.extend([
            f"## {brief['name']}",
            "",
            f"- Product class: `{brief['product_class']}`",
            f"- Closest reference: `{brief['closest_reference']}`",
            f"- Source lane/family: `{brief.get('source_lane')}` / `{brief.get('source_family')}`",
            f"- Product read: `{brief.get('product_thesis', '')}`",
            f"- Value model: `{brief.get('value_model', '')}`",
            f"- Target model: `{brief.get('target_model', '')}`",
            f"- Trigger model: `{brief.get('trigger_model', '')}`",
            f"- Essential controls: `{', '.join(brief.get('essential_controls', [])) or 'None'}`",
            f"- Essential subsystems: `{', '.join(brief.get('essential_subsystems', [])) or 'None'}`",
            f"- Accidental complexity: `{', '.join(brief.get('accidental_complexity', [])) or 'None'}`",
            f"- Build cleanly as: `{brief.get('build_cleanly_as', '')}`",
            f"- Semantic candidates: `{', '.join(brief.get('mapping_semantic_candidates', [])) or 'None'}`",
            f"- Behavior traces: `{', '.join(brief.get('mapping_behavior_traces', [])) or 'None'}`",
            f"- Behavior hints: `{', '.join(brief.get('behavior_hints', [])) or 'None'}`",
            f"- Open questions: `{', '.join(brief.get('open_questions', [])) or 'None'}`",
            f"- Confidence: `{brief.get('confidence', 'unknown')}`",
            f"- Score: `{brief.get('score', 0)}`",
            "",
        ])
    return "\n".join(lines)


def mapping_product_brief_markdown(brief: dict) -> str:
    """Render one mapping/modulation product brief as markdown."""
    lines = mapping_product_briefs_markdown([brief]).splitlines()
    if lines:
        lines[0] = "# Mapping / Modulation Product Brief"
    return "\n".join(lines)


def write_mapping_product_brief(brief: dict, path: str) -> int:
    """Write one rendered mapping/modulation product brief to disk."""
    text = mapping_product_brief_markdown(brief)
    Path(path).write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def write_mapping_product_briefs(briefs: list[dict], path: str) -> int:
    """Write rendered mapping/modulation product briefs to disk."""
    text = mapping_product_briefs_markdown(briefs)
    Path(path).write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def write_mapping_lane_report(report: dict, path: str) -> int:
    """Write a rendered mapping/modulation lane report to disk."""
    text = mapping_lane_report_markdown(report)
    Path(path).write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


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
        f"- Source lanes: `{json.dumps(summary.get('source_lanes', {}), sort_keys=True)}`",
        f"- Bridge-enabled files: `{summary.get('bridge_enabled_files', 0)}`",
        f"- Files with helper patterns: `{summary.get('files_with_patterns', 0)}`",
        f"- Files with recipe patterns: `{summary.get('files_with_recipes', 0)}`",
        f"- Files with generic motifs: `{summary.get('files_with_motifs', 0)}`",
        f"- Files with named-bus networks: `{summary.get('files_with_named_bus_networks', 0)}`",
        f"- Files with cross-scope named-bus networks: `{summary.get('files_with_cross_scope_named_bus_networks', 0)}`",
        f"- Files with semantic Live API helper recoveries: `{summary.get('files_with_live_api_helpers', 0)}`",
        f"- Files with Live API helper opportunities: `{summary.get('files_with_live_api_helper_opportunities', 0)}`",
        f"- Files with controller-shell candidates: `{summary.get('files_with_controller_shell_candidates', 0)}`",
        f"- Files with behavior hints: `{summary.get('files_with_behavior_hints', 0)}`",
        f"- Files with mapping-behavior traces: `{summary.get('files_with_mapping_behavior_traces', 0)}`",
        f"- Files with embedded-ui shell candidates: `{summary.get('files_with_embedded_ui_shell_candidates', 0)}`",
        f"- Files with named-bus router candidates: `{summary.get('files_with_named_bus_router_candidates', 0)}`",
        f"- Files with init-dispatch candidates: `{summary.get('files_with_init_dispatch_chain_candidates', 0)}`",
        f"- Files with state-bundle router candidates: `{summary.get('files_with_state_bundle_router_candidates', 0)}`",
        f"- Files with presentation widget clusters: `{summary.get('files_with_presentation_widget_cluster_candidates', 0)}`",
        f"- Files with poly-shell candidates: `{summary.get('files_with_poly_shell_candidates', 0)}`",
        f"- Files with poly-shell bank candidates: `{summary.get('files_with_poly_shell_bank_candidates', 0)}`",
        f"- Files with poly-editor bank candidates: `{summary.get('files_with_poly_editor_bank_candidates', 0)}`",
        f"- Files with mapping semantic candidates: `{summary.get('files_with_mapping_semantic_candidates', 0)}`",
        f"- Files with mapping-workflow candidates: `{summary.get('files_with_mapping_workflow_candidates', 0)}`",
        f"- Files with sample-buffer candidates: `{summary.get('files_with_sample_buffer_candidates', 0)}`",
        f"- Files with gen-processing candidates: `{summary.get('files_with_gen_processing_candidates', 0)}`",
        f"- Files with embedded sample-buffer candidates: `{summary.get('files_with_embedded_sample_buffer_candidates', 0)}`",
        f"- Files with embedded gen-processing candidates: `{summary.get('files_with_embedded_gen_processing_candidates', 0)}`",
        f"- Files with first-party API rig candidates: `{summary.get('files_with_first_party_api_rig_candidates', 0)}`",
        f"- Files with first-party abstraction-host candidates: `{summary.get('files_with_first_party_abstraction_host_candidates', 0)}`",
        f"- Files with building-block candidates: `{summary.get('files_with_building_block_candidates', 0)}`",
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
    add_frequency_section("Top Behavior Hints", frequencies.get("behavior_hints", []))
    add_frequency_section("Top Mapping Behavior Traces", frequencies.get("mapping_behavior_traces", []))
    add_frequency_section("Top Embedded UI Shell Candidates", frequencies.get("embedded_ui_shell_candidates", []))
    add_frequency_section("Top Named Bus Router Candidates", frequencies.get("named_bus_router_candidates", []))
    add_frequency_section("Top Init Dispatch Candidates", frequencies.get("init_dispatch_chain_candidates", []))
    add_frequency_section("Top State Bundle Router Candidates", frequencies.get("state_bundle_router_candidates", []))
    add_frequency_section("Top Presentation Widget Cluster Candidates", frequencies.get("presentation_widget_cluster_candidates", []))
    add_frequency_section("Top Poly Shell Candidates", frequencies.get("poly_shell_candidates", []))
    add_frequency_section("Top Poly Shell Bank Candidates", frequencies.get("poly_shell_bank_candidates", []))
    add_frequency_section("Top Poly Editor Bank Candidates", frequencies.get("poly_editor_bank_candidates", []))
    add_frequency_section("Top Mapping Semantic Candidates", frequencies.get("mapping_semantic_candidates", []))
    add_frequency_section("Top Mapping Workflow Candidates", frequencies.get("mapping_workflow_candidates", []))
    add_frequency_section("Top Sample Buffer Candidates", frequencies.get("sample_buffer_candidates", []))
    add_frequency_section("Top Gen Processing Candidates", frequencies.get("gen_processing_candidates", []))
    add_frequency_section("Top Embedded Sample Buffer Candidates", frequencies.get("embedded_sample_buffer_candidates", []))
    add_frequency_section("Top Embedded Gen Processing Candidates", frequencies.get("embedded_gen_processing_candidates", []))
    add_frequency_section("Top First-Party API Rig Candidates", frequencies.get("first_party_api_rig_candidates", []))
    add_frequency_section("Top First-Party Abstraction Host Candidates", frequencies.get("first_party_abstraction_host_candidates", []))
    add_frequency_section("Top First-Party Abstraction Host Families", frequencies.get("first_party_abstraction_host_families", []))
    add_frequency_section("Top Building Block Candidates", frequencies.get("building_block_candidates", []))
    add_frequency_section("Top Embedded Live API Path Targets", frequencies.get("embedded_live_api_path_targets", []))
    add_frequency_section("Top Embedded Live API Properties", frequencies.get("embedded_live_api_properties", []))
    add_frequency_section("Top Embedded Live API Get Targets", frequencies.get("embedded_live_api_get_targets", []))
    add_frequency_section("Top Embedded Live API Set Targets", frequencies.get("embedded_live_api_set_targets", []))
    add_frequency_section("Top Embedded Live API Call Targets", frequencies.get("embedded_live_api_call_targets", []))
    add_frequency_section("Top Embedded Live API Archetypes", frequencies.get("embedded_live_api_archetypes", []))
    add_frequency_section("Top Source Lanes", frequencies.get("source_lanes", []))
    add_frequency_section("Top Source Families", frequencies.get("source_families", []))
    add_frequency_section("Top Pack Names", frequencies.get("pack_names", []))
    add_frequency_section("Top Pack Sections", frequencies.get("pack_sections", []))
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

    lines.append("## Source Lane Profiles")
    lines.append("")
    source_lane_profiles = report.get("source_lane_profiles", [])
    if source_lane_profiles:
        for entry in source_lane_profiles:
            motifs = ", ".join(motif["name"] for motif in entry.get("top_motif_signatures", [])[:3]) or "None"
            lines.append(
                f"- `{entry['lane']}`: `{entry['count']}` file(s),"
                f" avg boxes `{entry['avg_boxes']}`, avg lines `{entry['avg_lines']}`,"
                f" motifs `{motifs}`"
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
    add_section("Stable Behavior Hints", stable.get("behavior_hints", []))
    add_section("Variable Behavior Hints", variable.get("behavior_hints", []))
    add_section("Stable Named Bus Networks", stable.get("named_bus_network_names", []))
    add_section("Variable Named Bus Networks", variable.get("named_bus_network_names", []))
    add_section("Stable Poly Shell Banks", stable.get("poly_shell_banks", []))
    add_section("Variable Poly Shell Banks", variable.get("poly_shell_banks", []))
    add_section("Stable Poly Editor Banks", stable.get("poly_editor_banks", []))
    add_section("Variable Poly Editor Banks", variable.get("poly_editor_banks", []))
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
    "source_lane_profiles_markdown",
    "reference_device_dossiers_markdown",
    "corpus_comparison_markdown",
    "mapping_lane_report_markdown",
    "mapping_product_briefs_markdown",
    "mapping_product_brief_markdown",
    "write_mapping_product_brief",
    "write_mapping_product_briefs",
    "write_mapping_lane_report",
    "corpus_report_markdown",
    "family_profile_markdown",
    "write_corpus_report",
    "write_family_profile",
]
