"""Legacy-device reverse-engineering tool — thin facade.

The 7.9k-line implementation was split into _reverse_constants/helpers/
detect/match/extract (a DAG by call layer). This module re-exports the
full surface so existing importers are unchanged."""
from __future__ import annotations

import copy
import os
import pprint
import re
from pathlib import Path
from typing import Any

from ._reverse_constants import *  # noqa: F401,F403
from ._reverse_detect import *  # noqa: F401,F403
from ._reverse_extract import *  # noqa: F401,F403
from ._reverse_helpers import *  # noqa: F401,F403
from ._reverse_match import *  # noqa: F401,F403
from .constants import AMXD_TYPE, AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .device import Device
from .live_api import (
    device_active_state,
    live_object_path,
    live_observer,
    live_parameter_probe,
    live_set_control,
    live_state_observer,
    live_thisdevice,
)
from .recipes import (
    dry_wet_stage,
    gain_controlled_stage,
    midi_note_gate,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)

__all__ = [
    "read_amxd",
    "snapshot_from_device",
    "snapshot_from_amxd",
    "snapshot_from_bridge_payload",
    "snapshot_to_json",
    "write_snapshot",
    "load_snapshot",
    "analyze_snapshot",
    "extract_embedded_patcher_snapshots",
    "extract_controller_shell_candidates",
    "extract_embedded_ui_shell_candidates",
    "extract_named_bus_router_candidates",
    "extract_init_dispatch_chain_candidates",
    "extract_state_bundle_router_candidates",
    "extract_sample_buffer_candidates",
    "extract_gen_processing_candidates",
    "extract_presentation_widget_cluster_candidates",
    "extract_poly_shell_candidates",
    "extract_poly_shell_bank_candidates",
    "extract_poly_editor_bank_candidates",
    "extract_behavior_hints",
    "extract_mapping_behavior_traces",
    "extract_mapping_semantic_candidates",
    "extract_mapping_workflow_candidates",
    "extract_first_party_api_rig_candidates",
    "extract_first_party_abstraction_host_candidates",
    "extract_first_party_abstraction_family_candidates",
    "extract_building_block_candidates",
    "extract_live_api_normalization_candidates",
    "detect_snapshot_patterns",
    "detect_snapshot_recipes",
    "detect_snapshot_motifs",
    "extract_parameter_specs",
    "extract_snapshot_knowledge",
]
