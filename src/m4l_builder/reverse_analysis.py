"""Higher-level reverse analysis and behavior inference helpers."""

from ._reverse_legacy import (
    analyze_snapshot,
    extract_behavior_hints,
    extract_mapping_behavior_traces,
    extract_mapping_semantic_candidates,
    extract_mapping_workflow_candidates,
    extract_snapshot_knowledge,
)

__all__ = [
    "analyze_snapshot",
    "extract_behavior_hints",
    "extract_mapping_behavior_traces",
    "extract_mapping_semantic_candidates",
    "extract_mapping_workflow_candidates",
    "extract_snapshot_knowledge",
]
