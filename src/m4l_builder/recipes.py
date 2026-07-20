"""Pre-wired DSP combo recipes for common M4L patterns.

Each recipe takes a device instance and parameters, then adds a complete
pre-wired section using device.add_dsp(), device.add_newobj(), device.add_dial(),
and device.add_line(). Returns a dict of important IDs for further wiring.
"""

from .dsp import (
    arpeggiator,
    compressor,
    convolver,
    delay_line,
    euclidean_rhythm,
    grain_cloud,
    lfo,
    macromap,
    midi_learn_chain,
    noteout,
    param_smooth,
    pitch_quantize,
    poly_voices,
    probability_gate,
    random_note,
    sidechain_routing,
    spectral_gate,
    transport_lfo,
    velocity_curve,
)
from .dsp import notein as dsp_notein
from .engines.sidechain_display import SIDECHAIN_DISPLAY_INLETS, sidechain_display_js
from .engines.spectral_display import SPECTRAL_DISPLAY_INLETS, spectral_display_js
from .recipes_io import (
    _API_ROUTING_JS,
    _DEVICE_PALETTE_JS,
    _RECORD_MIDI_JS,
    _REGION_TRANSLATE_JS,
    _SAMPLE_EXPORT_JS,
    _SCALE_AWARE_JS,
    buffer_viewport,
    device_palette,
    expandable_column,
    header_strip,
    icon_rail,
    io_routing_menus,
    meter_feed,
    midi_from,
    record_midi,
    region_translate,
    sample_export,
    sample_lfo,
    scale_awareness,
    stereo_mode,
)
from .recipes_layout import (
    bypass_wrapper,
    delta_listen,
    dial_label_cell,
    dial_value_cell,
    latency_readout,
    mode_stack,
    modulator_slot_component,
    randomize_matrix,
    report_latency,
    settings_sidebar,
    stacked_panels,
    switchable_bank,
    two_panel_strip,
)

# recipes.py is a thin facade: the 62 recipes live in
# recipes_{stages,layout,widgets,io}.py and are re-exported here so every
# `from m4l_builder.recipes import X` keeps working unchanged.
from .recipes_stages import (
    arpeggio_quantized_stage,
    beat_phase_gate,
    convolver_controlled_stage,
    dry_wet_stage,
    euclidean_sequencer_stage,
    gain_controlled_stage,
    generative_midi_stage,
    grain_playback_controlled,
    lfo_matrix_distribute,
    mc_poly_spine,
    midi_learn_macro_assignment,
    midi_note_gate,
    parametric_eq_band_backend,
    poly_midi_gate,
    sample_drop_target,
    sidechain_compressor_recipe,
    spectral_gate_stage,
    stereo_width_stage,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)
from .recipes_widgets import (
    _CHIP_KINDS,
    _HEADER_CAPTIONS,
    _LANE_ROTATOR_JS,
    _NOTE_HZ_JS,
    _PARAM_LINK_JS,
    _PROGRESS_TICK_JS,
    dim_steppers,
    display_header,
    ghost_label,
    hero_readout,
    lane_rotator,
    mapping_summary_chip,
    mod_source_matrix,
    mode_pill,
    modulator_header_row,
    note_hz_readout,
    page_selector,
    param_link,
    progress_tick,
    standard_chip,
    takeover_menu,
)
from .stages import stage_result
from .ui import live_drop
