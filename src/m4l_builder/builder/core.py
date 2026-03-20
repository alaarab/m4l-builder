"""Core graph, device, and serialization primitives."""

from ..assets import Asset
from ..constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from ..container import build_amxd, write_amxd
from ..device import AudioEffect, Device, Instrument, MidiEffect
from ..graph import BoxRef, GraphContainer, InletRef, OutletRef
from ..jsui_contract import JsuiContractError, find_jsui_contract_issues, validate_jsui_contract
from ..layout import Column, Columns, Grid, Row, inset_rect
from ..modules import ModuleSpec, module_from_block, mount_module
from ..objects import newobj, patchline
from ..parameters import LIVE_NATIVE_INT_MAX, LIVE_NATIVE_INT_MIN, PARAM_HIDDEN, PARAM_VISIBLE, ParameterSpec
from ..paths import device_output_path, user_library
from ..profiles import DEFAULT_PATCHER_PROFILE, PatcherProfile
from ..stages import Stage, StageResult, stage_result
from ..subpatcher import Subpatcher
from ..validation import (
    BuildValidationError,
    ValidationIssue,
    format_validation_issues,
    lint_graph,
)

__all__ = [
    "Device",
    "AudioEffect",
    "Instrument",
    "MidiEffect",
    "Subpatcher",
    "GraphContainer",
    "BoxRef",
    "OutletRef",
    "InletRef",
    "ParameterSpec",
    "PARAM_HIDDEN",
    "PARAM_VISIBLE",
    "LIVE_NATIVE_INT_MIN",
    "LIVE_NATIVE_INT_MAX",
    "Asset",
    "PatcherProfile",
    "DEFAULT_PATCHER_PROFILE",
    "JsuiContractError",
    "find_jsui_contract_issues",
    "validate_jsui_contract",
    "Stage",
    "StageResult",
    "stage_result",
    "ModuleSpec",
    "module_from_block",
    "mount_module",
    "ValidationIssue",
    "BuildValidationError",
    "format_validation_issues",
    "lint_graph",
    "Row",
    "Column",
    "Columns",
    "Grid",
    "inset_rect",
    "build_amxd",
    "write_amxd",
    "newobj",
    "patchline",
    "AUDIO_EFFECT",
    "INSTRUMENT",
    "MIDI_EFFECT",
    "user_library",
    "device_output_path",
]
