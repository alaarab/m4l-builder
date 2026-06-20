"""Core graph, device, and serialization primitives."""

from ..assets import Asset
from ..constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from ..container import build_amxd, write_amxd
from ..device import (
    AudioEffect,
    Device,
    Instrument,
    MidiEffect,
    MidiGenerator,
    MidiTransformation,
)
from ..gen_lint import lint_genexpr
from ..gen_patcher import build_gendsp
from ..gen_sim import GenKernel, UnsupportedKernel, simulate
from ..gen_snippets import (
    biquad_df1,
    drive_blend,
    dynamics_band,
    exp_pole,
    isp_catmull_4x,
    kweight_coeffs_bs1770,
    ms_decode,
    ms_encode,
    ms_width,
    peak_follower,
    rbj_peaking,
    rbj_shelf,
    soft_knee_gain_computer,
)
from ..graph import BoxRef, GraphContainer, InletRef, OutletRef
from ..jsui_contract import (
    JsuiContractError,
    find_jsui_contract_issues,
    find_v8ui_contract_issues,
    validate_jsui_contract,
    validate_v8ui_contract,
)
from ..layout import Column, Columns, Grid, Row, inset_rect
from ..modules import ModuleSpec, module_from_block, mount_module
from ..notes import NoteEvent, notes_dict
from ..objects import newobj, patchline
from ..parameters import (
    LIVE_NATIVE_INT_MAX,
    LIVE_NATIVE_INT_MIN,
    PARAM_HIDDEN,
    PARAM_VIS_AUTOMATED_AND_STORED,
    PARAM_VIS_HIDDEN,
    PARAM_VIS_STORED_ONLY,
    PARAM_VISIBLE,
    ParameterSpec,
)
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
    "MidiTransformation",
    "MidiGenerator",
    "Subpatcher",
    "GraphContainer",
    "BoxRef",
    "OutletRef",
    "InletRef",
    "ParameterSpec",
    "PARAM_HIDDEN",
    "PARAM_VISIBLE",
    "PARAM_VIS_AUTOMATED_AND_STORED",
    "PARAM_VIS_STORED_ONLY",
    "PARAM_VIS_HIDDEN",
    "LIVE_NATIVE_INT_MIN",
    "LIVE_NATIVE_INT_MAX",
    "Asset",
    "PatcherProfile",
    "DEFAULT_PATCHER_PROFILE",
    "JsuiContractError",
    "find_jsui_contract_issues",
    "validate_jsui_contract",
    "find_v8ui_contract_issues",
    "validate_v8ui_contract",
    "build_gendsp",
    "lint_genexpr",
    "ms_encode",
    "ms_decode",
    "ms_width",
    "drive_blend",
    "peak_follower",
    "isp_catmull_4x",
    "kweight_coeffs_bs1770",
    "exp_pole",
    "soft_knee_gain_computer",
    "dynamics_band",
    "biquad_df1",
    "rbj_peaking",
    "rbj_shelf",
    "simulate",
    "GenKernel",
    "UnsupportedKernel",
    "Stage",
    "StageResult",
    "stage_result",
    "ModuleSpec",
    "module_from_block",
    "mount_module",
    "NoteEvent",
    "notes_dict",
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
