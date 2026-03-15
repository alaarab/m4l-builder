"""Reusable stages, modules, and higher-level recipes."""

from ..modules import ModuleSpec, module_from_block, mount_module
from ..recipes import (
    arpeggio_quantized_stage,
    convolver_controlled_stage,
    dry_wet_stage,
    gain_controlled_stage,
    grain_playback_controlled,
    lfo_matrix_distribute,
    midi_learn_macro_assignment,
    midi_note_gate,
    parametric_eq_band_backend,
    poly_midi_gate,
    sidechain_compressor_recipe,
    spectral_gate_stage,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)
from ..stages import Stage, StageResult, stage_result

__all__ = [
    "Stage",
    "StageResult",
    "stage_result",
    "ModuleSpec",
    "module_from_block",
    "mount_module",
    "gain_controlled_stage",
    "parametric_eq_band_backend",
    "dry_wet_stage",
    "tempo_synced_delay",
    "midi_note_gate",
    "convolver_controlled_stage",
    "sidechain_compressor_recipe",
    "lfo_matrix_distribute",
    "spectral_gate_stage",
    "arpeggio_quantized_stage",
    "grain_playback_controlled",
    "poly_midi_gate",
    "transport_sync_lfo_recipe",
    "midi_learn_macro_assignment",
]
