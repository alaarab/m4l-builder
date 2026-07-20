"""Corpus analysis helpers for mining external .amxd device directories — thin facade.

The 2.6k-line implementation was split into _corpus_helpers/file/ranking/
mapping/dossier/aggregate/markdown (a DAG by call layer, verified acyclic).
This module re-exports the full surface so existing importers are unchanged."""
from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from statistics import mean
from typing import Any

from ._corpus_aggregate import *  # noqa: F401,F403
from ._corpus_dossier import *  # noqa: F401,F403
from ._corpus_file import *  # noqa: F401,F403
from ._corpus_helpers import *  # noqa: F401,F403
from ._corpus_mapping import *  # noqa: F401,F403
from ._corpus_markdown import *  # noqa: F401,F403
from ._corpus_ranking import *  # noqa: F401,F403
from .patcher_walk import iter_boxes
from .reverse import (
    extract_embedded_patcher_snapshots,
    extract_gen_processing_candidates,
    extract_sample_buffer_candidates,
    extract_snapshot_knowledge,
    generate_builder_python_from_amxd,
    generate_semantic_python_from_amxd,
    snapshot_from_amxd,
)

__all__ = [
    "classify_corpus_source_metadata",
    "analyze_amxd_file",
    "analyze_amxd_corpus",
    "rank_reverse_candidates",
    "rank_reverse_candidate_families",
    "build_reverse_candidate_family_profile",
    "build_reverse_candidate_family_profiles",
    "build_source_lane_profiles",
    "source_lane_profiles_markdown",
    "build_reference_device_dossier",
    "build_reference_device_dossiers",
    "reference_device_dossiers_markdown",
    "rank_mapping_candidates",
    "build_mapping_lane_report",
    "mapping_lane_report_markdown",
    "write_mapping_lane_report",
    "build_mapping_product_brief",
    "build_mapping_product_brief_from_path",
    "build_mapping_product_briefs",
    "mapping_product_brief_markdown",
    "mapping_product_briefs_markdown",
    "write_mapping_product_brief",
    "write_mapping_product_briefs",
    "build_corpus_comparison",
    "corpus_comparison_markdown",
    "corpus_report_markdown",
    "family_profile_markdown",
    "write_corpus_report",
    "write_family_profile",
]
