"""m4l_builder: Programmatically build Max for Live (.amxd) devices.

The root package stays compatibility-oriented, but it now resolves most exports
lazily so importing `m4l_builder` does not eagerly load reverse/corpus tooling.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from ._exports import ROOT_ALL, ROOT_EXPORT_GROUPS, ROOT_NAMESPACE_MODULES

if TYPE_CHECKING:
    # Static mirror of the lazy exports below, so type checkers see real types.
    # BEGIN GENERATED ROOT TYPE IMPORTS (tools/gen_root_type_imports.py)
    # isort: off
    from . import analysis as analysis
    from . import authoring as authoring
    from . import bridge as bridge
    from . import builder as builder
    from . import live as live
    from . import reverse_api as _reverse_module
    from . import reverse_analysis as reverse_analysis
    from . import reverse_codegen as reverse_codegen
    from . import reverse_patterns as reverse_patterns
    from . import reverse_snapshot as reverse_snapshot
    from ._corpus_aggregate import (
        analyze_amxd_corpus as analyze_amxd_corpus,
    )
    from ._corpus_dossier import (
        build_corpus_comparison as build_corpus_comparison,
        build_reference_device_dossier as build_reference_device_dossier,
        build_reference_device_dossiers as build_reference_device_dossiers,
    )
    from ._corpus_file import (
        analyze_amxd_file as analyze_amxd_file,
        classify_corpus_source_metadata as classify_corpus_source_metadata,
    )
    from ._corpus_mapping import (
        build_mapping_lane_report as build_mapping_lane_report,
        build_mapping_product_brief as build_mapping_product_brief,
        build_mapping_product_brief_from_path as build_mapping_product_brief_from_path,
        build_mapping_product_briefs as build_mapping_product_briefs,
        rank_mapping_candidates as rank_mapping_candidates,
    )
    from ._corpus_markdown import (
        corpus_comparison_markdown as corpus_comparison_markdown,
        corpus_report_markdown as corpus_report_markdown,
        family_profile_markdown as family_profile_markdown,
        mapping_lane_report_markdown as mapping_lane_report_markdown,
        mapping_product_brief_markdown as mapping_product_brief_markdown,
        mapping_product_briefs_markdown as mapping_product_briefs_markdown,
        reference_device_dossiers_markdown as reference_device_dossiers_markdown,
        source_lane_profiles_markdown as source_lane_profiles_markdown,
        write_corpus_report as write_corpus_report,
        write_family_profile as write_family_profile,
        write_mapping_lane_report as write_mapping_lane_report,
        write_mapping_product_brief as write_mapping_product_brief,
        write_mapping_product_briefs as write_mapping_product_briefs,
    )
    from ._corpus_ranking import (
        build_reverse_candidate_family_profile as build_reverse_candidate_family_profile,
        build_reverse_candidate_family_profiles as build_reverse_candidate_family_profiles,
        build_source_lane_profiles as build_source_lane_profiles,
        rank_reverse_candidate_families as rank_reverse_candidate_families,
        rank_reverse_candidates as rank_reverse_candidates,
    )
    from ._reverse_codegen import (
        generate_builder_python_from_amxd as generate_builder_python_from_amxd,
        generate_builder_python_from_bridge_payload as generate_builder_python_from_bridge_payload,
        generate_builder_python_from_device as generate_builder_python_from_device,
        generate_builder_python_from_snapshot as generate_builder_python_from_snapshot,
        generate_optimized_python_from_amxd as generate_optimized_python_from_amxd,
        generate_optimized_python_from_bridge_payload as generate_optimized_python_from_bridge_payload,
        generate_optimized_python_from_device as generate_optimized_python_from_device,
        generate_optimized_python_from_snapshot as generate_optimized_python_from_snapshot,
        generate_python_from_amxd as generate_python_from_amxd,
        generate_python_from_bridge_payload as generate_python_from_bridge_payload,
        generate_python_from_device as generate_python_from_device,
        generate_python_from_snapshot as generate_python_from_snapshot,
        generate_semantic_python_from_amxd as generate_semantic_python_from_amxd,
        generate_semantic_python_from_bridge_payload as generate_semantic_python_from_bridge_payload,
        generate_semantic_python_from_device as generate_semantic_python_from_device,
        generate_semantic_python_from_snapshot as generate_semantic_python_from_snapshot,
    )
    from ._reverse_detect import (
        detect_snapshot_motifs as detect_snapshot_motifs,
        detect_snapshot_patterns as detect_snapshot_patterns,
        detect_snapshot_recipes as detect_snapshot_recipes,
    )
    from ._reverse_extract import (
        analyze_snapshot as analyze_snapshot,
        extract_behavior_hints as extract_behavior_hints,
        extract_building_block_candidates as extract_building_block_candidates,
        extract_controller_shell_candidates as extract_controller_shell_candidates,
        extract_embedded_ui_shell_candidates as extract_embedded_ui_shell_candidates,
        extract_first_party_abstraction_family_candidates as extract_first_party_abstraction_family_candidates,
        extract_first_party_abstraction_host_candidates as extract_first_party_abstraction_host_candidates,
        extract_first_party_api_rig_candidates as extract_first_party_api_rig_candidates,
        extract_gen_processing_candidates as extract_gen_processing_candidates,
        extract_init_dispatch_chain_candidates as extract_init_dispatch_chain_candidates,
        extract_live_api_normalization_candidates as extract_live_api_normalization_candidates,
        extract_mapping_behavior_traces as extract_mapping_behavior_traces,
        extract_mapping_semantic_candidates as extract_mapping_semantic_candidates,
        extract_mapping_workflow_candidates as extract_mapping_workflow_candidates,
        extract_named_bus_router_candidates as extract_named_bus_router_candidates,
        extract_poly_editor_bank_candidates as extract_poly_editor_bank_candidates,
        extract_poly_shell_bank_candidates as extract_poly_shell_bank_candidates,
        extract_poly_shell_candidates as extract_poly_shell_candidates,
        extract_presentation_widget_cluster_candidates as extract_presentation_widget_cluster_candidates,
        extract_sample_buffer_candidates as extract_sample_buffer_candidates,
        extract_snapshot_knowledge as extract_snapshot_knowledge,
        extract_state_bundle_router_candidates as extract_state_bundle_router_candidates,
    )
    from .assets import (
        Asset as Asset,
    )
    from .bridge_probe import (
        add_bridge_probe_runtime as add_bridge_probe_runtime,
        env_flag as env_flag,
        livemcp_asset_dir as livemcp_asset_dir,
        register_bridge_probe_assets as register_bridge_probe_assets,
    )
    from .constants import (
        AUDIO_EFFECT as AUDIO_EFFECT,
        INSTRUMENT as INSTRUMENT,
        MIDI_EFFECT as MIDI_EFFECT,
    )
    from .container import (
        build_amxd as build_amxd,
        write_amxd as write_amxd,
    )
    from .controller_shells import (
        controller_surface_shell as controller_surface_shell,
        embedded_ui_shell as embedded_ui_shell,
        embedded_ui_shell_v2 as embedded_ui_shell_v2,
        init_dispatch_chain as init_dispatch_chain,
        named_bus_router as named_bus_router,
        poly_shell as poly_shell,
        poly_shell_bank as poly_shell_bank,
        sequencer_dispatch_shell as sequencer_dispatch_shell,
    )
    from .corpus_fixture import (
        build_corpus_manifest as build_corpus_manifest,
        load_corpus_manifest as load_corpus_manifest,
        run_corpus_fixture as run_corpus_fixture,
        select_corpus_manifest_entries as select_corpus_manifest_entries,
        write_corpus_fixture_results as write_corpus_fixture_results,
        write_corpus_manifest as write_corpus_manifest,
    )
    from .device import (
        AudioEffect as AudioEffect,
        Device as Device,
        Instrument as Instrument,
        MidiEffect as MidiEffect,
        MidiGenerator as MidiGenerator,
        MidiTransformation as MidiTransformation,
    )
    from .dsp.data import (
        coll_store as coll_store,
        cv_recorder as cv_recorder,
        dict_store as dict_store,
        gen_codebox as gen_codebox,
        loadbang as loadbang,
        pattr_system as pattr_system,
    )
    from .dsp.delay import (
        comb_resonator as comb_resonator,
        convolver as convolver,
        delay_line as delay_line,
        fdn_reverb as fdn_reverb,
        feedback_delay as feedback_delay,
        reverb_network as reverb_network,
    )
    from .dsp.dynamics import (
        auto_gain as auto_gain,
        bitcrusher as bitcrusher,
        compressor as compressor,
        envelope_follower as envelope_follower,
        gate_expander as gate_expander,
        limiter as limiter,
        lookahead_envelope_follower as lookahead_envelope_follower,
        multiband_compressor as multiband_compressor,
        sidechain_detect as sidechain_detect,
    )
    from .dsp.filters import (
        allpass_filter as allpass_filter,
        bandpass_filter as bandpass_filter,
        crossover_3band as crossover_3band,
        highpass_filter as highpass_filter,
        highshelf_filter as highshelf_filter,
        lowpass_filter as lowpass_filter,
        lowshelf_filter as lowshelf_filter,
        notch_filter as notch_filter,
        onepole_filter as onepole_filter,
        peaking_eq as peaking_eq,
        spectrum_band_extract as spectrum_band_extract,
        tilt_eq as tilt_eq,
    )
    from .dsp.generative import (
        euclidean_rhythm as euclidean_rhythm,
        probability_gate as probability_gate,
        random_note as random_note,
    )
    from .dsp.io import (
        dc_block as dc_block,
        dry_wet_mix as dry_wet_mix,
        gain_stage as gain_stage,
        ms_encode_decode as ms_encode_decode,
        saturation as saturation,
        sidechain_routing as sidechain_routing,
        signal_divide as signal_divide,
        stereo_io as stereo_io,
    )
    from .dsp.live import (
        live_param_signal as live_param_signal,
        live_remote as live_remote,
        macromap as macromap,
        quantize_time as quantize_time,
        tempo_sync as tempo_sync,
    )
    from .dsp.midi import (
        aftertouch_in as aftertouch_in,
        arpeggiator as arpeggiator,
        bank_select_in as bank_select_in,
        cc_mapper_lane as cc_mapper_lane,
        cc_mapper_lane_mpe_lines as cc_mapper_lane_mpe_lines,
        cc_mapper_lane_ui_lines as cc_mapper_lane_ui_lines,
        chord as chord,
        ctlin as ctlin,
        ctlout as ctlout,
        midi_channel_filter as midi_channel_filter,
        midi_clock_in as midi_clock_in,
        midi_clock_out as midi_clock_out,
        midi_learn_chain as midi_learn_chain,
        midi_thru as midi_thru,
        midi_tool_io as midi_tool_io,
        modwheel_in as modwheel_in,
        mpe_io_chain as mpe_io_chain,
        note_expression_decode as note_expression_decode,
        notein as notein,
        noteout as noteout,
        pitch_quantize as pitch_quantize,
        pitchbend_in as pitchbend_in,
        program_change_in as program_change_in,
        sysex_out as sysex_out,
        transpose as transpose,
        velocity_curve as velocity_curve,
    )
    from .dsp.modulation import (
        cv_smooth_lag as cv_smooth_lag,
        lfo as lfo,
        lfsr_generator as lfsr_generator,
        macro_modulation_matrix as macro_modulation_matrix,
        morphing_lfo as morphing_lfo,
        param_smooth as param_smooth,
        random_walk as random_walk,
        sample_and_hold as sample_and_hold,
        sample_and_hold_triggered as sample_and_hold_triggered,
        scale_range as scale_range,
        transport_lfo as transport_lfo,
        tremolo as tremolo,
    )
    from .dsp.routing import (
        matrix_mixer as matrix_mixer,
        mc_collapse as mc_collapse,
        mc_expand as mc_expand,
        mc_gain_stage as mc_gain_stage,
        mc_mixer as mc_mixer,
        mc_selector as mc_selector,
        receive_msg as receive_msg,
        receive_signal as receive_signal,
        selector as selector,
        send_msg as send_msg,
        send_signal as send_signal,
        xfade_matrix as xfade_matrix,
    )
    from .dsp.spectral import (
        phase_vocoder_subpatcher as phase_vocoder_subpatcher,
        spectral_crossover as spectral_crossover,
        spectral_crossover_subpatcher as spectral_crossover_subpatcher,
        spectral_gate as spectral_gate,
        spectral_gate_subpatcher as spectral_gate_subpatcher,
        stft_phase_vocoder as stft_phase_vocoder,
        vocoder as vocoder,
    )
    from .dsp.synthesis import (
        adsr_envelope as adsr_envelope,
        analog_oscillator_bank as analog_oscillator_bank,
        buffer_load as buffer_load,
        grain_cloud as grain_cloud,
        groove_player as groove_player,
        noise_source as noise_source,
        poly_voices as poly_voices,
        wavetable_osc as wavetable_osc,
    )
    from .engines.sidechain_display import (
        SIDECHAIN_DISPLAY_INLETS as SIDECHAIN_DISPLAY_INLETS,
        SIDECHAIN_DISPLAY_OUTLETS as SIDECHAIN_DISPLAY_OUTLETS,
        sidechain_display_js as sidechain_display_js,
    )
    from .engines.spectral_display import (
        SPECTRAL_DISPLAY_INLETS as SPECTRAL_DISPLAY_INLETS,
        SPECTRAL_DISPLAY_OUTLETS as SPECTRAL_DISPLAY_OUTLETS,
        spectral_display_js as spectral_display_js,
    )
    from .engines.wavetable_display import (
        WAVETABLE_DISPLAY_INLETS as WAVETABLE_DISPLAY_INLETS,
        WAVETABLE_DISPLAY_OUTLETS as WAVETABLE_DISPLAY_OUTLETS,
        wavetable_display_js as wavetable_display_js,
    )
    from .engines.xy_pad import (
        XY_PAD_INLETS as XY_PAD_INLETS,
        XY_PAD_OUTLETS as XY_PAD_OUTLETS,
        xy_pad_js as xy_pad_js,
    )
    from .freeze import (
        assemble_frozen_amxd as assemble_frozen_amxd,
        device_to_frozen_bytes as device_to_frozen_bytes,
        extract_frozen_amxd as extract_frozen_amxd,
        freeze_amxd_file as freeze_amxd_file,
    )
    from .gen_lint import (
        lint_genexpr as lint_genexpr,
    )
    from .gen_patcher import (
        build_gendsp as build_gendsp,
        embed_gendsp as embed_gendsp,
    )
    from .gen_sim import (
        simulate as simulate,
    )
    from .gen_snippets import (
        biquad_df1 as biquad_df1,
        drive_blend as drive_blend,
        dynamics_band as dynamics_band,
        exp_pole as exp_pole,
        isp_catmull_4x as isp_catmull_4x,
        kweight_coeffs_bs1770 as kweight_coeffs_bs1770,
        kweight_coeffs_bs1770_cached as kweight_coeffs_bs1770_cached,
        ms_decode as ms_decode,
        ms_encode as ms_encode,
        ms_width as ms_width,
        peak_follower as peak_follower,
        rbj_peaking as rbj_peaking,
        rbj_shelf as rbj_shelf,
        soft_knee_gain_computer as soft_knee_gain_computer,
    )
    from .graph import (
        BoxRef as BoxRef,
        GraphContainer as GraphContainer,
        InletRef as InletRef,
        OutletRef as OutletRef,
    )
    from .idioms import (
        control_smooth as control_smooth,
        debounce as debounce,
        dedupe_value as dedupe_value,
        expr_cond as expr_cond,
        expr_safe_mod as expr_safe_mod,
        init_prime as init_prime,
    )
    from .jsui_contract import (
        JsuiContractError as JsuiContractError,
        find_jsui_contract_issues as find_jsui_contract_issues,
        find_v8ui_contract_issues as find_v8ui_contract_issues,
        validate_jsui_contract as validate_jsui_contract,
        validate_v8ui_contract as validate_v8ui_contract,
    )
    from .layout import (
        Column as Column,
        Columns as Columns,
        Grid as Grid,
        Row as Row,
        inset_rect as inset_rect,
    )
    from .live_api import (
        device_active_state as device_active_state,
        live_object_path as live_object_path,
        live_observer as live_observer,
        live_parameter_probe as live_parameter_probe,
        live_set_control as live_set_control,
        live_state_observer as live_state_observer,
        live_thisdevice as live_thisdevice,
    )
    from .livemcp_bridge import (
        BOX_ATTR_ALLOWLIST as BOX_ATTR_ALLOWLIST,
        BRIDGE_CAPABILITIES as BRIDGE_CAPABILITIES,
        BRIDGE_COMMANDS as BRIDGE_COMMANDS,
        BRIDGE_PROTOCOL_VERSION as BRIDGE_PROTOCOL_VERSION,
        BRIDGE_RUNTIME_FILENAME as BRIDGE_RUNTIME_FILENAME,
        BRIDGE_SCHEMA_FILENAME as BRIDGE_SCHEMA_FILENAME,
        BRIDGE_SERVER_FILENAME as BRIDGE_SERVER_FILENAME,
        DEFAULT_BRIDGE_PORT as DEFAULT_BRIDGE_PORT,
        DISALLOWED_CREATE_CLASSES as DISALLOWED_CREATE_CLASSES,
        OBJECT_ATTR_ALLOWLIST as OBJECT_ATTR_ALLOWLIST,
        bridge_runtime_js as bridge_runtime_js,
        bridge_schema as bridge_schema,
        bridge_server_js as bridge_server_js,
        build_livemcp_bridge_demo as build_livemcp_bridge_demo,
        enable_livemcp_bridge as enable_livemcp_bridge,
    )
    from .modules import (
        ModuleSpec as ModuleSpec,
        module_from_block as module_from_block,
        mount_module as mount_module,
    )
    from .notes import (
        NoteEvent as NoteEvent,
        notes_dict as notes_dict,
    )
    from .objects import (
        message as message,
        newobj as newobj,
        patchline as patchline,
    )
    from .parameters import (
        PARAM_HIDDEN as PARAM_HIDDEN,
        PARAM_VISIBLE as PARAM_VISIBLE,
        PARAM_VIS_AUTOMATED_AND_STORED as PARAM_VIS_AUTOMATED_AND_STORED,
        PARAM_VIS_HIDDEN as PARAM_VIS_HIDDEN,
        PARAM_VIS_STORED_ONLY as PARAM_VIS_STORED_ONLY,
        ParameterSpec as ParameterSpec,
    )
    from .paths import (
        device_output_path as device_output_path,
        user_library as user_library,
    )
    from .presets import (
        add_preset_buttons as add_preset_buttons,
        preset_manager as preset_manager,
    )
    from .profiles import (
        DEFAULT_PATCHER_PROFILE as DEFAULT_PATCHER_PROFILE,
        PatcherProfile as PatcherProfile,
    )
    from .recipes_layout import (
        bypass_wrapper as bypass_wrapper,
        dial_label_cell as dial_label_cell,
        stacked_panels as stacked_panels,
        switchable_bank as switchable_bank,
        two_panel_strip as two_panel_strip,
    )
    from .recipes_stages import (
        arpeggio_quantized_stage as arpeggio_quantized_stage,
        convolver_controlled_stage as convolver_controlled_stage,
        dry_wet_stage as dry_wet_stage,
        euclidean_sequencer_stage as euclidean_sequencer_stage,
        gain_controlled_stage as gain_controlled_stage,
        generative_midi_stage as generative_midi_stage,
        grain_playback_controlled as grain_playback_controlled,
        lfo_matrix_distribute as lfo_matrix_distribute,
        mc_poly_spine as mc_poly_spine,
        midi_learn_macro_assignment as midi_learn_macro_assignment,
        midi_note_gate as midi_note_gate,
        poly_midi_gate as poly_midi_gate,
        sample_drop_target as sample_drop_target,
        sidechain_compressor_recipe as sidechain_compressor_recipe,
        spectral_gate_stage as spectral_gate_stage,
        stereo_width_stage as stereo_width_stage,
        tempo_synced_delay as tempo_synced_delay,
        transport_sync_lfo_recipe as transport_sync_lfo_recipe,
    )
    from .reverse_snapshot import (
        extract_embedded_patcher_snapshots as extract_embedded_patcher_snapshots,
        extract_parameter_specs as extract_parameter_specs,
        load_snapshot as load_snapshot,
        read_amxd as read_amxd,
        snapshot_from_amxd as snapshot_from_amxd,
        snapshot_from_bridge_payload as snapshot_from_bridge_payload,
        snapshot_from_device as snapshot_from_device,
        snapshot_to_json as snapshot_to_json,
        write_snapshot as write_snapshot,
    )
    from .stages import (
        Stage as Stage,
        StageResult as StageResult,
        stage_result as stage_result,
    )
    from .subpatcher import (
        Subpatcher as Subpatcher,
    )
    from .surface import (
        Surface as Surface,
        SurfaceError as SurfaceError,
    )
    from .theme import (
        COOL as COOL,
        FOREST as FOREST,
        INDUSTRIAL as INDUSTRIAL,
        LIGHT as LIGHT,
        LOFI as LOFI,
        MIDNIGHT as MIDNIGHT,
        NEBULA as NEBULA,
        SOLAR as SOLAR,
        SYNTHWAVE as SYNTHWAVE,
        Theme as Theme,
        VIOLET as VIOLET,
        WARM as WARM,
        alpha as alpha,
        derive_palette as derive_palette,
        js_color as js_color,
    )
    from .ui import (
        adsrui as adsrui,
        bpatcher as bpatcher,
        button as button,
        comment as comment,
        dial as dial,
        fpic as fpic,
        jsui as jsui,
        kslider as kslider,
        live_arrows as live_arrows,
        live_drop as live_drop,
        live_gain as live_gain,
        live_grid as live_grid,
        live_line as live_line,
        live_step as live_step,
        live_text as live_text,
        matrixctrl as matrixctrl,
        menu as menu,
        meter as meter,
        multislider as multislider,
        nodes as nodes,
        nslider as nslider,
        number_box as number_box,
        panel as panel,
        radiogroup as radiogroup,
        rslider as rslider,
        scope as scope,
        slider as slider,
        swatch as swatch,
        tab as tab,
        textbutton as textbutton,
        textedit as textedit,
        toggle as toggle,
        ubutton as ubutton,
        umenu as umenu,
        v8ui as v8ui,
    )
    from .validation import (
        BuildValidationError as BuildValidationError,
        ValidationIssue as ValidationIssue,
        format_validation_issues as format_validation_issues,
        lint_graph as lint_graph,
    )
    reverse = _reverse_module
    # isort: on
    # END GENERATED ROOT TYPE IMPORTS

__all__ = list(ROOT_ALL)


def __getattr__(name: str):
    module_name = ROOT_NAMESPACE_MODULES.get(name)
    if module_name is not None:
        module = import_module(module_name)
        globals()[name] = module
        return module

    for module_name, exports in ROOT_EXPORT_GROUPS:
        if name in exports:
            value = getattr(import_module(module_name), name)
            globals()[name] = value
            return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
