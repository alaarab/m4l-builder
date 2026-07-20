"""Analysis namespace for corpus and fixture tooling."""

from .corpus_analysis import (
    analyze_amxd_corpus,
    analyze_amxd_file,
    build_corpus_comparison,
    build_mapping_lane_report,
    build_mapping_product_brief,
    build_mapping_product_brief_from_path,
    build_mapping_product_briefs,
    build_reference_device_dossier,
    build_reference_device_dossiers,
    build_reverse_candidate_family_profile,
    build_reverse_candidate_family_profiles,
    build_source_lane_profiles,
    classify_corpus_source_metadata,
    corpus_comparison_markdown,
    corpus_report_markdown,
    family_profile_markdown,
    mapping_lane_report_markdown,
    mapping_product_brief_markdown,
    mapping_product_briefs_markdown,
    rank_mapping_candidates,
    rank_reverse_candidate_families,
    rank_reverse_candidates,
    reference_device_dossiers_markdown,
    source_lane_profiles_markdown,
    write_corpus_report,
    write_family_profile,
    write_mapping_lane_report,
    write_mapping_product_brief,
    write_mapping_product_briefs,
)
from .corpus_fixture import (
    build_corpus_manifest,
    load_corpus_manifest,
    run_corpus_fixture,
    select_corpus_manifest_entries,
    write_corpus_fixture_results,
    write_corpus_manifest,
)

__all__ = [name for name in globals() if not name.startswith("_")]
