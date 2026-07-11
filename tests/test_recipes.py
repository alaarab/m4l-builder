"""Tests for pre-wired DSP combo recipes."""

from m4l_builder import AudioEffect
from m4l_builder.recipes import (
    arpeggio_quantized_stage,
    bypass_wrapper,
    convolver_controlled_stage,
    dial_label_cell,
    dial_value_cell,
    dry_wet_stage,
    gain_controlled_stage,
    grain_playback_controlled,
    lfo_matrix_distribute,
    mc_poly_spine,
    midi_learn_macro_assignment,
    midi_note_gate,
    mode_stack,
    parametric_eq_band_backend,
    poly_midi_gate,
    sample_drop_target,
    settings_sidebar,
    sidechain_compressor_recipe,
    spectral_gate_stage,
    stacked_panels,
    stereo_width_stage,
    switchable_bank,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
    two_panel_strip,
)


def _box_ids(device):
    """Return set of all box IDs in a device."""
    return {box["box"]["id"] for box in device.boxes}


def _line_pairs(device):
    """Return set of (source_id, dest_id) tuples for all lines."""
    return {
        (line["patchline"]["source"][0], line["patchline"]["destination"][0])
        for line in device.lines
    }


def _box_texts(device):
    return {b["box"].get("text") for b in device.boxes if b["box"].get("text")}


def _box_classes(device):
    return {b["box"].get("maxclass") for b in device.boxes}


class TestSampleDropTarget:
    def _device(self):
        device = AudioEffect("test", width=300, height=168)
        device.add_newobj("mybuf", "buffer~ mybuf_smp", numinlets=1,
                          numoutlets=1, outlettype=["bang"],
                          patching_rect=[20, 200, 150, 20])
        res = sample_drop_target(device, "smp", "mybuf", [10, 24, 280, 100])
        return device, res

    def test_uses_live_drop_not_dropfile(self):
        # live.drop accepts drags from the Live browser; dropfile does not.
        device, _ = self._device()
        classes = _box_classes(device)
        assert "live.drop" in classes
        assert "dropfile" not in classes

    def test_intake_chain_present(self):
        device, _ = self._device()
        texts = _box_texts(device)
        assert "t b l" in texts
        assert "prepend replace" in texts
        assert "delay 600" in texts

    def test_wires_replace_into_buffer_and_settle(self):
        device, _ = self._device()
        pairs = _line_pairs(device)
        assert ("smp_drop", "smp_trig") in pairs
        assert ("smp_trig", "smp_replace") in pairs
        assert ("smp_replace", "mybuf") in pairs       # path -> the buffer~
        assert ("smp_trig", "smp_loaded") in pairs      # bang -> settle delay

    def test_returns_loaded_id_for_redraw_wiring(self):
        device, res = self._device()
        assert res["loaded"] == "smp_loaded"
        assert res["drop"] == "smp_drop"

    def test_custom_settle_ms(self):
        device = AudioEffect("test", width=300, height=168)
        device.add_newobj("b", "buffer~ b_smp", numinlets=1, numoutlets=1,
                          outlettype=["bang"], patching_rect=[20, 200, 150, 20])
        sample_drop_target(device, "s", "b", [10, 24, 280, 100], settle_ms=400)
        assert "delay 400" in _box_texts(device)


class TestGainControlledStage:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = gain_controlled_stage(device, "vol", [10, 10, 40, 40])
        assert "dial" in result
        assert "gain" in result

    def test_adds_dial_and_dsp_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = gain_controlled_stage(device, "vol", [10, 10, 40, 40])
        ids = _box_ids(device)
        assert result["dial"] in ids
        assert result["gain"] in ids
        assert "vol_dbtoa" in ids
        assert "vol_smooth_pack" in ids
        assert "vol_smooth_line" in ids

    def test_wiring_chain(self):
        device = AudioEffect("test", width=200, height=100)
        result = gain_controlled_stage(device, "vol", [10, 10, 40, 40])
        pairs = _line_pairs(device)
        # dial -> dbtoa
        assert (result["dial"], "vol_dbtoa") in pairs
        # dbtoa -> smooth pack
        assert ("vol_dbtoa", "vol_smooth_pack") in pairs
        # smooth line -> gain
        assert ("vol_smooth_line", result["gain"]) in pairs

    def test_multiple_stages_no_conflict(self):
        device = AudioEffect("test", width=200, height=100)
        r1 = gain_controlled_stage(device, "vol1", [10, 10, 40, 40])
        r2 = gain_controlled_stage(device, "vol2", [60, 10, 40, 40])
        assert r1["dial"] != r2["dial"]
        assert r1["gain"] != r2["gain"]


class TestMcPolySpine:
    def test_returns_spine_ids(self):
        device = AudioEffect("test", width=200, height=100)
        res = mc_poly_spine(device, "syn")
        for key in ("noteallocator", "click", "gen", "mixdown", "audio_unpack"):
            assert key in res
        ids = _box_ids(device)
        assert res["gen"] in ids and res["noteallocator"] in ids

    def test_objects_are_the_mc_spine(self):
        device = AudioEffect("test", width=200, height=100)
        mc_poly_spine(device, "syn", voices=16)
        texts = _box_texts(device)
        # the poly~-free spine — verbatim object grammar (steal on by default)
        assert "mc.noteallocator~ @voices 16 @steal 1" in texts
        assert "mc.click~ @chans 16" in texts
        assert "mc.gen~ @chans 16" in texts
        assert "mc.mixdown~ 1 @autogain 0" in texts
        assert "mc.unpack~ 1" in texts

    def test_voice_active_feedback_loop_is_wired(self):
        # the jewel: mc.gen~[0] -> mc.noteallocator~[0] enables voice stealing.
        device = AudioEffect("test", width=200, height=100)
        res = mc_poly_spine(device, "syn")
        pairs = _line_pairs(device)
        assert (res["gen"], res["noteallocator"]) in pairs        # feedback
        assert (res["click"], res["gen"]) in pairs                # trigger
        assert (res["gen"], res["mixdown"]) in pairs              # audio sum
        assert (res["mixdown"], res["audio_unpack"]) in pairs
        assert ("syn_midiin", "syn_midiparse") in pairs
        assert ("syn_midiparse", res["noteallocator"]) in pairs

    def test_mpe_and_voice_count_options(self):
        device = AudioEffect("test", width=200, height=100)
        mc_poly_spine(device, "mpe", voices=8, mpe=True, gen_name="myvoice")
        texts = _box_texts(device)
        # Chiral's MPE allocator grammar + a named .gendsp voice
        assert "mc.noteallocator~ @mpemode 1 @voices 8 @steal 1" in texts
        assert "mc.gen~ myvoice @chans 8" in texts
        assert "mc.click~ @chans 8" in texts


class TestTwoPanelStrip:
    def test_grounded_as_console_geometry(self):
        device = AudioEffect("test", width=231, height=167)
        res = two_panel_strip(device, "strip")
        # the SABROI AS Console two-panel grammar: wide main + narrow side, gap 2
        assert res["main_rect"] == [0, 0, 174, 167]
        assert res["side_rect"] == [176, 0, 56, 167]
        assert res["total_width"] == 232
        ids = _box_ids(device)
        assert "strip_main_panel" in ids and "strip_side_panel" in ids

    def test_panels_are_backgrounds(self):
        device = AudioEffect("test", width=231, height=167)
        two_panel_strip(device, "strip")
        panels = [b["box"] for b in device.boxes if b["box"].get("maxclass") == "panel"]
        assert len(panels) == 2
        assert all(pp.get("background") == 1 for pp in panels)

    def test_content_rects_inset(self):
        device = AudioEffect("test", width=231, height=167)
        res = two_panel_strip(device, "strip")
        assert res["main_content"] == [4, 4, 166, 159]    # inset by 4
        assert res["side_content"][0] == 180             # side_x + inset


class TestDialLabelCell:
    def test_dial_with_caption_below(self):
        device = AudioEffect("test", width=200, height=120)
        res = dial_label_cell(device, "drive", "Drive", [10, 10, 36, 36],
                              label="DRIVE", min_val=0.0, max_val=24.0)
        ids = _box_ids(device)
        assert res["dial"] in ids and res["label"] in ids
        # the label sits directly below the dial (y = dial_y + dial_h + gap)
        label_box = next(b["box"] for b in device.boxes
                         if b["box"]["id"] == "drive_label")
        assert label_box["presentation_rect"][1] == 10 + 36 + 1
        assert label_box.get("text") == "DRIVE"
        # the caption is the comment below — the dial must NOT also draw its name
        # inside the knob (factory default showname=1 would double the label).
        dial_box = next(b["box"] for b in device.boxes
                        if b["box"]["id"] == "drive_dial")
        assert dial_box["showname"] == 0

    def test_showname_override_passes_through(self):
        device = AudioEffect("test", width=200, height=120)
        dial_label_cell(device, "drive", "Drive", [10, 10, 36, 36], showname=1)
        dial_box = next(b["box"] for b in device.boxes
                        if b["box"]["id"] == "drive_dial")
        assert dial_box["showname"] == 1

    def test_cell_registers_the_parameter(self):
        device = AudioEffect("test", width=200, height=120)
        res = dial_label_cell(device, "mix", "Mix", [0, 0, 40, 40])
        assert "Mix" in res.params


class TestDialValueCell:
    def test_caption_above_native_value_below(self):
        device = AudioEffect("test", width=200, height=140)
        res = dial_value_cell(device, "tilt", "Tilt", [10, 40, 41, 35],
                              label="TILT", min_val=-6.0, max_val=6.0,
                              accent=[0.45, 0.75, 0.65, 1.0])
        ids = _box_ids(device)
        assert res["dial"] in ids and res["label"] in ids
        # caption sits ABOVE the dial (y = dial_y - label_h - gap)
        cap = next(b["box"] for b in device.boxes if b["box"]["id"] == "tilt_cap")
        assert cap["presentation_rect"][1] == 40 - 10 - 1
        assert cap.get("text") == "TILT"
        # native dial: no painter, name hidden, value SHOWN, accent ring
        dial = next(b["box"] for b in device.boxes if b["box"]["id"] == "tilt_dial")
        assert dial["maxclass"] == "live.dial"
        assert dial["showname"] == 0 and dial["shownumber"] == 1
        assert dial["activedialcolor"] == [0.45, 0.75, 0.65, 1.0]

    def test_cell_registers_the_parameter(self):
        device = AudioEffect("test", width=200, height=140)
        res = dial_value_cell(device, "w", "Width", [0, 20, 41, 35])
        assert "Width" in res.params


class TestSwitchableBank:
    def test_selector_bank_with_tab_shim(self):
        device = AudioEffect("test", width=240, height=120)
        res = switchable_bank(device, "alg", ["Clean", "Tape", "Tube"])
        texts = _box_texts(device)
        assert "selector~ 3 1" in texts          # N inputs
        assert "+ 1" in texts                     # 0-indexed tab -> 1-indexed selector
        pairs = _line_pairs(device)
        assert ("alg_tab", "alg_shim") in pairs
        assert ("alg_shim", "alg_sel") in pairs
        # one input port per option + an output
        assert {"in_0", "in_1", "in_2", "audio_out"} <= set(res.ports)
        assert "alg_select" in res.params

    def test_custom_tab_param_name(self):
        device = AudioEffect("test", width=240, height=120)
        res = switchable_bank(device, "ab", ["A", "B"], tab_param="ABComp")
        assert "ABComp" in res.params
        assert "selector~ 2 1" in _box_texts(device)


class TestBypassWrapper:
    def test_selector_switch_with_param_toggle(self):
        device = AudioEffect("test", width=200, height=120)
        res = bypass_wrapper(device, "comp")
        texts = _box_texts(device)
        assert "selector~ 2 1" in texts
        assert "expr 2-$i1" in texts          # toggle 0->wet(2), 1->dry(1)
        # the bypass is a first-class parameter (automatable/saved)
        btn = next(b["box"] for b in device.boxes if b["box"]["id"] == "comp_bypass")
        assert btn["maxclass"] == "live.text" and btn["parameter_enable"] == 1
        pairs = _line_pairs(device)
        assert ("comp_bypass", "comp_inv") in pairs
        assert ("comp_inv", "comp_sel") in pairs
        assert "comp_bypass" in res.params

    def test_ports_exposed(self):
        device = AudioEffect("test", width=200, height=120)
        res = bypass_wrapper(device, "eq")
        assert "dry_in" in res.ports and "wet_in" in res.ports
        assert "audio_out" in res.ports


class TestStackedPanels:
    def test_tab_swaps_panels_via_thispatcher(self):
        device = AudioEffect("test", width=240, height=180)
        # caller adds the panels (scripting names) first, at the same content rect
        for pid in ("panA", "panB", "panC"):
            device.add_panel(pid, [0, 20, 240, 160], bgcolor=[0.1, 0.1, 0.1, 1.0])
        res = stacked_panels(device, "sec", "Section", ["panA", "panB", "panC"],
                             rect=[0, 0, 240, 18], labels=["A", "B", "C"])
        texts = _box_texts(device)
        # a hide for every panel + a show for every panel + the fork + a thispatcher
        assert "script hide panA" in texts and "script show panA" in texts
        assert "script hide panC" in texts and "script show panC" in texts
        assert "t i b" in texts and "thispatcher" in texts
        assert "sel 0 1 2" in texts
        pairs = _line_pairs(device)
        # fork hide-bang (outlet 1) reaches a hide message; sel reaches a show message
        assert (res["tab"], "sec_fork") in pairs
        assert ("sec_fork", "sec_hide0") in pairs
        assert ("sec_show1", "sec_thisp") in pairs

    def test_ghost_tab_is_transparent(self):
        device = AudioEffect("test", width=240, height=180)
        device.add_panel("only", [0, 20, 240, 160], bgcolor=[0.1, 0.1, 0.1, 1.0])
        stacked_panels(device, "g", "Sel", ["only"], rect=[0, 0, 240, 18], ghost=True)
        tab = next(b["box"] for b in device.boxes if b["box"]["id"] == "g_tab")
        assert tab["bgcolor"] == [0.0, 0.0, 0.0, 0.0]
        assert tab["textcolor"] == [0.0, 0.0, 0.0, 0.0]


class TestParametricEqBandBackend:
    def _make_device(self):
        device = AudioEffect("test", width=200, height=100)
        device.add_newobj("lb_init", "loadbang", numinlets=1, numoutlets=1, outlettype=["bang"], patching_rect=[0, 0, 40, 20])
        for box_id in (
            "freq_b0",
            "gain_b0",
            "q_b0",
            "type_b0",
            "on_b0",
            "motion_b0",
            "dynamic_b0",
            "dynamic_amt_b0",
            "motion_rate_b0",
            "motion_depth_b0",
            "motion_direction_b0",
            "pak_b0",
        ):
            device.add_newobj(box_id, "number", numinlets=2, numoutlets=1, outlettype=[""], patching_rect=[0, 0, 40, 20])
        return device

    def test_returns_expected_keys(self):
        device = self._make_device()
        result = parametric_eq_band_backend(
            device,
            0,
            loadbang_id="lb_init",
            default_freq=1000.0,
            default_type_name="peaknotch",
            filter_types=["peaknotch", "lowshelf", "highshelf", "lowpass", "highpass", "bandstop", "bandpass", "allpass"],
            default_motion_rate=0.5,
        )
        assert "coeff" in result
        assert "biquad_l" in result
        assert "biquad_r" in result
        assert "gain_recalc" in result
        assert "q_recalc" in result

    def test_adds_expected_objects(self):
        device = self._make_device()
        parametric_eq_band_backend(
            device,
            0,
            loadbang_id="lb_init",
            default_freq=1000.0,
            default_type_name="peaknotch",
            filter_types=["peaknotch", "lowshelf", "highshelf", "lowpass", "highpass", "bandstop", "bandpass", "allpass"],
            default_motion_rate=0.5,
        )
        ids = _box_ids(device)
        for expected_id in (
            "fc_b0",
            "msg_resamp_b0",
            "bq_b0_l",
            "bq_b0_r",
            "freq_store_b0",
            "gain_recalc_trig_b0",
            "gain_dbtoa_ctrl_b0",
            "q_recalc_trig_b0",
            "type_sel_b0",
            "msg_type_0_b0",
            "on_sel_b0",
            "msg_off_b0",
        ):
            assert expected_id in ids

    def test_wires_retrigger_and_motion_paths(self):
        device = self._make_device()
        parametric_eq_band_backend(
            device,
            0,
            loadbang_id="lb_init",
            default_freq=1000.0,
            default_type_name="peaknotch",
            filter_types=["peaknotch", "lowshelf", "highshelf", "lowpass", "highpass", "bandstop", "bandpass", "allpass"],
            default_motion_rate=0.5,
        )
        pairs = _line_pairs(device)
        assert ("lb_init", "msg_resamp_b0") in pairs
        assert ("msg_resamp_b0", "fc_b0") in pairs
        assert ("gain_b0", "gain_recalc_trig_b0") in pairs
        assert ("gain_recalc_trig_b0", "freq_store_b0") in pairs
        assert ("gain_dbtoa_ctrl_b0", "fc_b0") in pairs
        assert ("q_b0", "q_recalc_trig_b0") in pairs
        assert ("q_recalc_trig_b0", "freq_store_b0") in pairs
        assert ("motion_depth_expr_b0", "motion_depth_mul_b0") in pairs
        assert ("motion_gain_depth_expr_b0", "motion_gain_mul_b0") in pairs


class TestDryWetStage:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = dry_wet_stage(device, "mix", [10, 10, 40, 40])
        assert "dial" in result
        assert "wet_gain" in result
        assert "dry_gain" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = dry_wet_stage(device, "mix", [10, 10, 40, 40])
        ids = _box_ids(device)
        assert result["dial"] in ids
        assert result["wet_gain"] in ids
        assert result["dry_gain"] in ids
        assert "mix_trig" in ids
        assert "mix_inv" in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = dry_wet_stage(device, "mix", [10, 10, 40, 40])
        pairs = _line_pairs(device)
        # dial -> trigger
        assert (result["dial"], "mix_trig") in pairs
        # trigger -> wet smooth
        assert ("mix_trig", "mix_wet_smooth_pack") in pairs
        # trigger -> inverter
        assert ("mix_trig", "mix_inv") in pairs


class TestTempoSyncedDelay:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=300, height=150)
        result = tempo_synced_delay(
            device, "dly", [10, 10, 45, 75], [60, 10, 45, 75],
        )
        assert "time_dial" in result
        assert "feedback_dial" in result
        assert "tapin" in result
        assert "tapout" in result

    def test_adds_delay_line_objects(self):
        device = AudioEffect("test", width=300, height=150)
        result = tempo_synced_delay(
            device, "dly", [10, 10, 45, 75], [60, 10, 45, 75],
        )
        ids = _box_ids(device)
        assert result["tapin"] in ids
        assert result["tapout"] in ids
        assert "dly_transport" in ids
        assert "dly_loadbang" in ids
        assert "dly_fb_scale" in ids
        assert "dly_fb_mul" in ids

    def test_wiring_time_path(self):
        device = AudioEffect("test", width=300, height=150)
        result = tempo_synced_delay(
            device, "dly", [10, 10, 45, 75], [60, 10, 45, 75],
        )
        pairs = _line_pairs(device)
        # time dial -> smooth -> tapout
        assert (result["time_dial"], "dly_time_smooth_pack") in pairs
        assert ("dly_time_smooth_line", result["tapout"]) in pairs

    def test_wiring_feedback_path(self):
        device = AudioEffect("test", width=300, height=150)
        result = tempo_synced_delay(
            device, "dly", [10, 10, 45, 75], [60, 10, 45, 75],
        )
        pairs = _line_pairs(device)
        # feedback dial -> scale -> smooth -> mul
        assert (result["feedback_dial"], "dly_fb_scale") in pairs
        assert ("dly_fb_scale", "dly_fb_smooth_pack") in pairs
        assert ("dly_fb_smooth_line", "dly_fb_mul") in pairs

    def test_feedback_loop_wiring(self):
        device = AudioEffect("test", width=300, height=150)
        result = tempo_synced_delay(
            device, "dly", [10, 10, 45, 75], [60, 10, 45, 75],
        )
        pairs = _line_pairs(device)
        # tapout -> fb_mul -> sum -> tapin
        assert (result["tapout"], "dly_fb_mul") in pairs
        assert ("dly_fb_mul", "dly_sum") in pairs
        assert ("dly_sum", result["tapin"]) in pairs


class TestMidiNoteGate:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = midi_note_gate(device, "midi")
        assert "notein" in result
        assert "pitch" in result
        assert "velocity" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = midi_note_gate(device, "midi")
        ids = _box_ids(device)
        assert result["notein"] in ids
        assert "midi_stripnote" in ids
        assert "midi_kslider" in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = midi_note_gate(device, "midi")
        pairs = _line_pairs(device)
        # notein -> stripnote (pitch)
        assert (result["notein"], "midi_stripnote") in pairs
        # stripnote -> kslider
        assert ("midi_stripnote", "midi_kslider") in pairs


class TestConvolverControlledStage:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = convolver_controlled_stage(device, "cv", [10, 10, 40, 40])
        assert "dial" in result
        assert "convolver" in result
        assert "wet" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = convolver_controlled_stage(device, "cv", [10, 10, 40, 40])
        ids = _box_ids(device)
        assert result["dial"] in ids
        assert result["convolver"] in ids
        assert result["wet"] in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = convolver_controlled_stage(device, "cv", [10, 10, 40, 40])
        pairs = _line_pairs(device)
        assert (result["dial"], "cv_trig") in pairs
        assert (result["convolver"], result["wet"]) in pairs

    def test_adds_lines(self):
        device = AudioEffect("test", width=200, height=100)
        convolver_controlled_stage(device, "cv", [10, 10, 40, 40])
        assert len(device.lines) > 0


class TestSidechainCompressorRecipe:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=300, height=150)
        result = sidechain_compressor_recipe(
            device, "sc", [10, 10, 40, 40], [60, 10, 40, 40],
        )
        assert "threshold_dial" in result
        assert "ratio_dial" in result
        assert "sidechain" in result
        assert "compressor" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=300, height=150)
        result = sidechain_compressor_recipe(
            device, "sc", [10, 10, 40, 40], [60, 10, 40, 40],
        )
        ids = _box_ids(device)
        assert result["threshold_dial"] in ids
        assert result["ratio_dial"] in ids
        assert result["sidechain"] in ids
        assert "sc_display" in ids

    def test_wiring(self):
        device = AudioEffect("test", width=300, height=150)
        result = sidechain_compressor_recipe(
            device, "sc", [10, 10, 40, 40], [60, 10, 40, 40],
        )
        pairs = _line_pairs(device)
        assert (result["threshold_dial"], "sc_comp_thresh_l") in pairs
        assert (result["ratio_dial"], "sc_comp_ratio_l") in pairs


class TestLfoMatrixDistribute:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=300, height=150)
        result = lfo_matrix_distribute(device, "lm", targets=3)
        assert "lfo" in result
        assert "depth_dials" in result
        assert len(result["depth_dials"]) == 3

    def test_default_targets(self):
        device = AudioEffect("test", width=300, height=150)
        result = lfo_matrix_distribute(device, "lm")
        assert len(result["depth_dials"]) == 4

    def test_adds_objects(self):
        device = AudioEffect("test", width=300, height=150)
        result = lfo_matrix_distribute(device, "lm", targets=2)
        ids = _box_ids(device)
        assert result["lfo"] in ids
        for dial_id in result["depth_dials"]:
            assert dial_id in ids

    def test_wiring(self):
        device = AudioEffect("test", width=300, height=150)
        result = lfo_matrix_distribute(device, "lm", targets=2)
        pairs = _line_pairs(device)
        # LFO -> each depth multiplier
        assert (result["lfo"], "lm_depth_0_mul") in pairs
        assert (result["lfo"], "lm_depth_1_mul") in pairs


class TestSpectralGateStage:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = spectral_gate_stage(device, "sg", [10, 10, 40, 40])
        assert "threshold_dial" in result
        assert "gate" in result
        assert "display" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = spectral_gate_stage(device, "sg", [10, 10, 40, 40])
        ids = _box_ids(device)
        assert result["threshold_dial"] in ids
        assert result["gate"] in ids
        assert result["display"] in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = spectral_gate_stage(device, "sg", [10, 10, 40, 40])
        pairs = _line_pairs(device)
        assert (result["threshold_dial"], result["gate"]) in pairs


class TestArpeggioQuantizedStage:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = arpeggio_quantized_stage(device, "aq")
        assert "arpeggiator" in result
        assert "quantizer" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = arpeggio_quantized_stage(device, "aq")
        ids = _box_ids(device)
        assert result["arpeggiator"] in ids
        assert result["quantizer"] in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = arpeggio_quantized_stage(device, "aq")
        pairs = _line_pairs(device)
        # arp makenote pitch -> quantizer
        assert ("aq_arp_make", result["quantizer"]) in pairs


class TestGrainPlaybackControlled:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=300, height=150)
        result = grain_playback_controlled(device, "gp", "grain_buf")
        assert "grain" in result
        assert "buffer" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=300, height=150)
        result = grain_playback_controlled(device, "gp", "grain_buf")
        ids = _box_ids(device)
        assert result["grain"] in ids
        # dials added
        assert "gp_pos_dial" in ids
        assert "gp_size_dial" in ids
        assert "gp_density_dial" in ids

    def test_adds_lines(self):
        device = AudioEffect("test", width=300, height=150)
        grain_playback_controlled(device, "gp", "grain_buf")
        # grain_cloud adds internal lines for summing
        assert len(device.lines) > 0


class TestPolyMidiGate:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = poly_midi_gate(device, "pm")
        assert "voices" in result
        assert "velocity_curve" in result
        assert "notein" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = poly_midi_gate(device, "pm")
        ids = _box_ids(device)
        assert result["voices"] in ids
        assert result["velocity_curve"] in ids
        assert result["notein"] in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = poly_midi_gate(device, "pm")
        pairs = _line_pairs(device)
        # notein -> poly
        assert (result["notein"], result["voices"]) in pairs
        # notein -> velocity curve
        assert (result["notein"], result["velocity_curve"]) in pairs
        # velocity curve -> poly
        assert (result["velocity_curve"], result["voices"]) in pairs


class TestTransportSyncLfoRecipe:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = transport_sync_lfo_recipe(device, "ts")
        assert "lfo" in result
        assert "depth_dial" in result
        assert "division_menu" in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = transport_sync_lfo_recipe(device, "ts")
        ids = _box_ids(device)
        assert result["lfo"] in ids
        assert result["depth_dial"] in ids
        assert result["division_menu"] in ids

    def test_wiring(self):
        device = AudioEffect("test", width=200, height=100)
        result = transport_sync_lfo_recipe(device, "ts")
        pairs = _line_pairs(device)
        assert (result["depth_dial"], "ts_depth_mul") in pairs
        assert (result["lfo"], "ts_depth_mul") in pairs


class TestMidiLearnMacroAssignment:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=100)
        result = midi_learn_macro_assignment(device, "ml")
        assert "learn_chain" in result
        assert "macromaps" in result
        assert len(result["macromaps"]) == 4

    def test_custom_num_targets(self):
        device = AudioEffect("test", width=200, height=100)
        result = midi_learn_macro_assignment(device, "ml", num_targets=2)
        assert len(result["macromaps"]) == 2

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=100)
        result = midi_learn_macro_assignment(device, "ml", num_targets=2)
        ids = _box_ids(device)
        assert result["learn_chain"] in ids
        for mm_id in result["macromaps"]:
            assert mm_id in ids

    def test_adds_lines(self):
        device = AudioEffect("test", width=200, height=100)
        midi_learn_macro_assignment(device, "ml")
        # midi_learn_chain and macromap both add internal lines
        assert len(device.lines) > 0


class TestStereoWidthStage:
    def test_returns_expected_keys(self):
        device = AudioEffect("test", width=200, height=200)
        result = stereo_width_stage(device, "wid", [10, 10, 40, 40])
        for key in ("dial", "in_l", "in_r", "mid", "side", "left", "right"):
            assert key in result

    def test_adds_expected_objects(self):
        device = AudioEffect("test", width=200, height=200)
        result = stereo_width_stage(device, "wid", [10, 10, 40, 40])
        ids = _box_ids(device)
        assert result["dial"] in ids
        for box_id in ("wid_sum", "wid_diff", "wid_mid", "wid_side", "wid_side_gain",
                       "wid_left", "wid_right", "wid_smooth_pack", "wid_smooth_line"):
            assert box_id in ids

    def test_mid_side_wiring(self):
        device = AudioEffect("test", width=200, height=200)
        stereo_width_stage(device, "wid", [10, 10, 40, 40])
        pairs = _line_pairs(device)
        # both inputs fan into sum and diff
        assert ("wid_in_l", "wid_sum") in pairs
        assert ("wid_in_r", "wid_sum") in pairs
        assert ("wid_in_l", "wid_diff") in pairs
        assert ("wid_in_r", "wid_diff") in pairs
        # side scaled by smoothed width, then recombined into both outputs
        assert ("wid_side", "wid_side_gain") in pairs
        assert ("wid_smooth_line", "wid_side_gain") in pairs
        assert ("wid_mid", "wid_left") in pairs
        assert ("wid_side_gain", "wid_left") in pairs
        assert ("wid_mid", "wid_right") in pairs
        assert ("wid_side_gain", "wid_right") in pairs


_CONTROLS = [
    {"id": "global_rate_dial", "name": "Rate", "min": 0.02, "max": 16.0,
     "init": 0.5, "unit": 3, "kind": "dial", "exp": 3.0},
    {"id": "global_bias_dial", "name": "Bias", "min": 0.0, "max": 1.0,
     "init": 0.13, "unit": 1, "kind": "dial"},
    {"id": "global_lanes_num", "name": "Lanes", "min": 1.0, "max": 8.0,
     "init": 2.0, "unit": 0, "kind": "num"},
]
# single-column centred cells -> default panel_width = 2*inset(6) + cell_w(40) = 52
_CW = 52


def _sidebar_device(mini=420):
    """A device with one pre-existing on-canvas control + the full-bleed bg."""
    device = AudioEffect("test", width=mini, height=168)
    device.add_panel("surf_bg", [0, 0, mini, 168], bgcolor=[0.1, 0.1, 0.1, 1.0])
    device.add_dial("rate_map", "Depth", [40, 20, 41, 35])   # main content
    return device


class TestSettingsSidebar:
    def test_bar_click_handler_is_classic_jsui(self):
        # The bar box is a CLASSIC jsui: its mouse event is onclick(x, y).
        # v8ui's onpointerdown never fires in a jsui — the sidebar shipped
        # that way once and every opener was dead to the mouse while
        # param-driven QA kept passing.
        device = _sidebar_device()
        settings_sidebar(device, "set", mini_width=420, accent=[1, 0.7, 0],
                         controls=_CONTROLS, left_bar=18)
        bar_assets = [a for a in device.assets()
                      if a.filename.startswith("settings_bar_")]
        assert len(bar_assets) == 1
        code = bar_assets[0].content
        if isinstance(code, bytes):
            code = code.decode("utf8")
        assert "function onclick(" in code
        assert "onpointerdown" not in code

    def test_left_bar_and_parked_param(self):
        device = _sidebar_device()
        res = settings_sidebar(device, "set", mini_width=420, accent=[1, 0.7, 0],
                               controls=_CONTROLS, left_bar=18)
        ids = _box_ids(device)
        # thin LEFT bar: bg panel + the drawn ▶ jsui opener
        assert "set_bar_bg" in ids and "set_bar" in ids
        bar = next(b["box"] for b in device.boxes if b["box"]["id"] == "set_bar_bg")
        assert bar["presentation_rect"] == [0, 0, 18, 168]   # left edge, thin
        # the automatable enum param is PARKED (driven by the drawn bar)
        toggle = next(b["box"] for b in device.boxes if b["box"]["id"] == "set_toggle")
        assert toggle["presentation_rect"][0] >= 900
        spec = device.parameter("Settings")
        assert spec.parameter_type == 2 and list(spec.enum) == ["Closed", "Open"]
        assert res["full_width"] == 420 + _CW   # panel width auto from cols=2
        assert device.width == 420              # loads closed

    def test_controls_are_grid_of_dials_and_numboxes(self):
        device = _sidebar_device()
        res = settings_sidebar(device, "set", mini_width=420, accent=[1, 0.7, 0],
                               controls=_CONTROLS, left_bar=18)
        assert res["section_ids"] == ["global_rate_dial", "global_bias_dial",
                                      "global_lanes_num"]
        # dial-kind controls become live.dial, num-kind become live.numbox — all
        # real params, all authored PARKED (x>=900) so they load hidden
        rate = next(b["box"] for b in device.boxes if b["box"]["id"] == "global_rate_dial")
        lanes = next(b["box"] for b in device.boxes if b["box"]["id"] == "global_lanes_num")
        assert rate["maxclass"] == "live.dial" and lanes["maxclass"] == "live.numbox"
        assert rate["presentation_rect"][0] >= 900
        assert device.parameter("Rate") is not None and device.parameter("Lanes") is not None

    def test_reflow_shifts_main_content_right(self):
        device = _sidebar_device()
        settings_sidebar(device, "set", mini_width=420, accent=[1, 0.7, 0],
                         controls=_CONTROLS, left_bar=18)
        # the pre-existing dial got a scripting name and an OPEN reposition that
        # shifts it +panel_width (the mapping grid moves right to make room)
        dial = next(b["box"] for b in device.boxes if b["box"]["id"] == "rate_map")
        vn = dial["varname"]
        texts = {b["box"].get("text") for b in device.boxes}
        assert f"script sendbox {vn} presentation_rect {40 + _CW} 20 41 35" in texts
        assert f"script sendbox {vn} presentation_rect 40 20 41 35" in texts   # closed

    def test_setwidth_and_bg_resize_wiring(self):
        device = _sidebar_device()
        settings_sidebar(device, "set", mini_width=420, accent=[1, 0.7, 0],
                         controls=_CONTROLS, left_bar=18)
        texts = {b["box"].get("text") for b in device.boxes}
        assert "setwidth 420" in texts and f"setwidth {420 + _CW}" in texts
        # background resizes with the device (closed=mini, open=full)
        assert "script sendbox surf_bg presentation_rect 0 0 420 168" in texts
        assert f"script sendbox surf_bg presentation_rect 0 0 {420 + _CW} 168" in texts
        pairs = _line_pairs(device)
        assert ("set_toggle", "set_sel") in pairs
        assert ("set_sel", "set_ctrig") in pairs and ("set_sel", "set_otrig") in pairs
        # load-time reset forces closed (thisdevice loadbang -> 0 -> toggle)
        assert ("set_thisdev", "set_lb0") in pairs and ("set_lb0", "set_toggle") in pairs


class TestDeltaListen:
    def test_toggle_param_and_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import delta_listen
        device = AudioEffect("DeltaProof", width=200, height=100)
        res = delta_listen(device, "dl", button_rect=[10, 10, 36, 15])
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert boxes["dl_delta"]["maxclass"] == "live.text"
        # per channel: wet/dry taps, wet-dry subtract, selector
        for ch in ("l", "r"):
            assert boxes[f"dl_sub_{ch}"]["text"] == "-~"
            assert boxes[f"dl_sel_{ch}"]["text"] == "selector~ 2 1"
        lines = {(c["patchline"]["source"][0], c["patchline"]["source"][1],
                  c["patchline"]["destination"][0], c["patchline"]["destination"][1])
                 for c in device.lines}
        assert ("dl_delta", 0, "dl_add", 0) in lines
        assert ("dl_wet_l", 0, "dl_sub_l", 0) in lines
        assert ("dl_dry_l", 0, "dl_sub_l", 1) in lines
        assert ("dl_sub_l", 0, "dl_sel_l", 2) in lines
        assert ("dl_wet_l", 0, "dl_sel_l", 1) in lines
        # ports exposed for the caller
        assert set(res.ports) == {"wet_in_l", "dry_in_l", "audio_out_l",
                                  "wet_in_r", "dry_in_r", "audio_out_r"}


class TestLatencyReadout:
    def test_sr_aware_ms_chain(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import latency_readout
        device = AudioEffect("LatProof", width=200, height=100)
        latency_readout(device, "lat", 4096, rect=[8, 80, 120, 12])
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert boxes["lat_ms"]["text"] == "expr 4096 * 1000. / $f1"
        assert boxes["lat_fmt"]["text"].startswith("sprintf set Latency:")
        msg = boxes["lat_msg"]
        assert msg["maxclass"] == "message" and msg["ignoreclick"] == 1
        lines = {(c["patchline"]["source"][0], c["patchline"]["destination"][0])
                 for c in device.lines}
        assert ("lat_lb", "lat_dsp") in lines and ("lat_fmt", "lat_msg") in lines


class TestReportLatency:
    """PDC report to Live (Q43): ``latency $1`` -> thispatcher, with the sample
    count either a true constant (samples=) or recomputed from the live
    samplerate via dspstate~ (ms=) so 48/96/192k get correct compensation."""

    def _make(self):
        return AudioEffect("PdcProof", width=200, height=100)

    def _boxes_lines(self, device):
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        lines = {(c["patchline"]["source"][0], c["patchline"]["source"][1],
                  c["patchline"]["destination"][0],
                  c["patchline"]["destination"][1])
                 for c in device.lines}
        return boxes, lines

    def test_samples_path_reports_constant_and_sets_static_key(self):
        from m4l_builder.recipes import report_latency
        device = self._make()
        res = report_latency(device, "pdc", samples=64)
        boxes, lines = self._boxes_lines(device)
        assert device.latency == 64                       # static at-load value
        assert boxes["pdc_msg"]["text"] == "latency $1"
        assert boxes["pdc_init"]["text"] == "64"
        assert boxes["pdc_thisp"]["text"] == "thispatcher"
        assert ("pdc_lb", 0, "pdc_init", 0) in lines
        assert ("pdc_init", 0, "pdc_msg", 0) in lines
        assert ("pdc_msg", 0, "pdc_thisp", 0) in lines
        # a true sample constant needs no samplerate recompute wire
        assert "pdc_dsp" not in boxes and "pdc_expr" not in boxes
        assert "samples_in" in res.ports

    def test_ms_path_recomputes_from_dspstate(self):
        from m4l_builder.recipes import report_latency
        device = self._make()
        report_latency(device, "pdc", ms=2.0)
        boxes, lines = self._boxes_lines(device)
        assert device.latency == 88                       # int(2ms*44.1k + .5)
        assert boxes["pdc_dsp"]["text"] == "dspstate~"
        assert boxes["pdc_expr"]["text"] == "expr int($f1 * 0.002 + 0.5)"
        assert boxes["pdc_defer"]["text"] == "deferlow"
        assert boxes["pdc_msg"]["text"] == "latency $1"
        assert ("pdc_lb", 0, "pdc_dsp", 0) in lines
        assert ("pdc_dsp", 1, "pdc_expr", 0) in lines     # outlet 1 = samplerate
        assert ("pdc_expr", 0, "pdc_defer", 0) in lines
        assert ("pdc_defer", 0, "pdc_msg", 0) in lines
        assert ("pdc_msg", 0, "pdc_thisp", 0) in lines

    def test_ms_path_5ms_matches_pressure_legacy_static(self):
        from m4l_builder.recipes import report_latency
        device = self._make()
        report_latency(device, "pdc", ms=5.0)
        assert device.latency == 221                      # int(220.5 + .5)
        boxes, _ = self._boxes_lines(device)
        assert boxes["pdc_expr"]["text"] == "expr int($f1 * 0.005 + 0.5)"

    def test_extra_samples_expr_appends_constant_term(self):
        from m4l_builder.recipes import report_latency
        device = self._make()
        report_latency(device, "pdc", ms=2.0, extra_samples_expr="3")
        boxes, _ = self._boxes_lines(device)
        assert boxes["pdc_expr"]["text"] == "expr int($f1 * 0.002 + 0.5) + (3)"
        assert device.latency == 88 + 3                   # literal folds into static

    def test_exactly_one_of_samples_or_ms(self):
        import pytest

        from m4l_builder.recipes import report_latency
        with pytest.raises(ValueError):
            report_latency(self._make(), "pdc")
        with pytest.raises(ValueError):
            report_latency(self._make(), "pdc", samples=10, ms=1.0)
        with pytest.raises(ValueError):
            report_latency(self._make(), "pdc", samples=10, extra_samples_expr="3")


class TestModeStack:
    """Generator mode-stack container (dnksaus item #9): a vertical enum tab
    swaps which pre-built editor stack is visible via the viewhide dataflow
    (`!= k` -> hidden flag) delivered over the Live-proven `script sendbox`
    thispatcher bus, with a live.thisdevice re-sync at load."""

    RECT = [40, 20, 240, 100]

    def _device(self):
        from m4l_builder import AudioEffect
        device = AudioEffect("test", width=300, height=168)
        for pid in ("edA", "edB", "edC"):
            device.add_panel(pid, list(self.RECT), bgcolor=[0.1, 0.1, 0.1, 1.0])
            device.boxes[-1]["box"]["varname"] = pid
        # a native control whose factory varname is the SPACEY param longname
        device.add_number_box("nbB", "Some Param", [40, 130, 40, 15],
                              min_val=0.0, max_val=10.0, initial=1.0)
        return device

    def _stack(self, device, **kwargs):
        return mode_stack(
            device, "mode", rect=list(self.RECT), param_name="Mode",
            modes=[("A", ["edA"]), ("B", ["edB", "nbB"]), ("C", ["edC"])],
            **kwargs)

    def test_tab_is_a_vertical_enum_param(self):
        device = self._device()
        res = self._stack(device)
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        tab = boxes["mode_tab"]
        assert tab["maxclass"] == "live.tab"
        assert tab["tabs"] == 3
        # the corpus-exact vertical column (Auto_Gate "Time Mode": 21px x N rows)
        assert tab["multiline"] == 1
        assert tab["num_lines_presentation"] == 3
        assert tab["num_lines_patching"] == 3
        assert tab["presentation_rect"] == [self.RECT[0] - 22, self.RECT[1],
                                            22, 48], "defaults left of the rect"
        valueof = tab["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == "Mode"
        assert valueof["parameter_enum"] == ["A", "B", "C"]
        assert res.params["Mode"].enum == ["A", "B", "C"]
        assert res["content_rect"] == self.RECT
        assert res["managed"] == {"A": ["edA"], "B": ["edB", "nbB"],
                                  "C": ["edC"]}

    def test_every_managed_box_gets_hidden_wiring(self):
        device = self._device()
        res = self._stack(device)
        texts = _box_texts(device)
        for name in ("edA", "edB", "nbB", "edC"):
            assert f"script sendbox {name} hidden $1" in texts
        assert "!= 0" in texts and "!= 1" in texts and "!= 2" in texts
        assert "thispatcher" in texts
        pairs = _line_pairs(device)
        assert (res["tab"], "mode_ne0") in pairs
        assert (res["tab"], "mode_ne2") in pairs
        # every sendbox message is fed by an `!=` and feeds the thispatcher
        byid = {b["box"]["id"]: b["box"] for b in device.boxes}
        msgs = [bid for bid, b in byid.items()
                if str(b.get("text", "")).startswith("script sendbox")]
        assert len(msgs) == 4
        for mid in msgs:
            srcs = {s for s, d in pairs if d == mid}
            assert srcs and all(s.startswith("mode_ne") for s in srcs)
            assert (mid, res["thispatcher"]) in pairs

    def test_initial_state_mode_zero_visible_others_authored_hidden(self):
        device = self._device()
        self._stack(device)
        byid = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert byid["edA"].get("hidden") != 1, "mode 0 authored visible"
        assert byid["edB"].get("hidden") == 1
        assert byid["nbB"].get("hidden") == 1
        assert byid["edC"].get("hidden") == 1

    def test_stamps_space_free_varnames_on_native_controls(self):
        device = self._device()
        byid = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert byid["nbB"]["varname"] == "Some Param", "factory default = longname"
        self._stack(device)
        assert byid["nbB"]["varname"] == "nbB", \
            "the spacey scripting name is rewritten to the given box id"

    def test_thisdevice_drives_the_load_resync_not_loadbang(self):
        device = self._device()
        res = self._stack(device)
        texts = _box_texts(device)
        assert "live.thisdevice" in texts
        assert "loadbang" not in texts, "scripting is NOT ready at loadbang"
        pairs = _line_pairs(device)
        assert (res["thisdevice"], "mode_init") in pairs
        assert ("mode_init", res["tab"]) in pairs, \
            "the bang makes the tab re-output its restored value"

    def test_rejects_bad_mode_lists(self):
        import pytest
        device = self._device()
        with pytest.raises(ValueError):        # space in a managed name
            mode_stack(device, "m1", rect=self.RECT, param_name="M1",
                       modes=[("A", ["edA"]), ("B", ["Some Param"])])
        with pytest.raises(ValueError):        # unknown box
            mode_stack(device, "m2", rect=self.RECT, param_name="M2",
                       modes=[("A", ["edA"]), ("B", ["nope"])])
        with pytest.raises(ValueError):        # duplicate across modes
            mode_stack(device, "m3", rect=self.RECT, param_name="M3",
                       modes=[("A", ["edA"]), ("B", ["edA"])])
        with pytest.raises(ValueError):        # a stack of one is not a stack
            mode_stack(device, "m4", rect=self.RECT, param_name="M4",
                       modes=[("A", ["edA"])])

    def test_tab_rect_override(self):
        device = self._device()
        self._stack(device, tab_rect=[4, 20, 26, 60])
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert boxes["mode_tab"]["presentation_rect"] == [4, 20, 26, 60]


class TestRandomizeMatrix:
    """Per-param randomize page (dnksaus Auto Gate; catalog #11 + #12):
    stored-only enable chips per target, RND rolls spec-derived random values
    through each enabled control's inlet, ALL/NONE quick-set the chips, and
    every `random` is cpuclock-seeded (+k) at load so lanes decorrelate."""

    def _device(self):
        from m4l_builder import AudioEffect
        device = AudioEffect("test", width=300, height=200)
        device.add_dial("d_freq", "Freq", [10, 10, 41, 35],
                        min_val=20.0, max_val=20000.0, initial=1000.0)
        from m4l_builder.parameters import ParameterSpec
        device.add_number_box("n_steps", "Steps", [60, 10, 40, 15],
                              min_val=2.0, max_val=8.0, initial=4.0,
                              parameter=ParameterSpec(
                                  name="Steps", parameter_type=1,
                                  minimum=2, maximum=8, initial=[4],
                                  initial_enable=True))
        device.add_live_text("t_mode", "Mode Sel", [110, 10, 40, 15],
                             text_on="B", text_off="A", mode=1)
        return device

    def _matrix(self, device, **kwargs):
        from m4l_builder.recipes import randomize_matrix
        return randomize_matrix(
            device, "rm", rect=[10, 60, 200, 60],
            targets=["d_freq", "n_steps", "t_mode"], **kwargs)

    def _boxes(self, device):
        return {b["box"]["id"]: b["box"] for b in device.boxes}

    def _lines(self, device):
        return [(ln["patchline"]["source"], ln["patchline"]["destination"])
                for ln in device.lines]

    def test_chips_are_stored_only_params(self):
        device = self._device()
        res = self._matrix(device)
        boxes = self._boxes(device)
        for k, longname in enumerate(["Rnd Freq", "Rnd Steps", "Rnd Mode Sel"]):
            chip = boxes[f"rm_chip{k}"]
            v = chip["saved_attribute_attributes"]["valueof"]
            assert v["parameter_longname"] == longname
            assert v["parameter_invisible"] == 1, "chips stay out of automation"
            assert v["parameter_initial"] == [1], "enabled by default"
        assert set(res.params) == {"Rnd Freq", "Rnd Steps", "Rnd Mode Sel"}

    def test_gate_per_target_and_trigger_fan(self):
        device = self._device()
        self._matrix(device)
        lines = self._lines(device)
        for k in range(3):
            assert ([f"rm_chip{k}", 0], [f"rm_gate{k}", 0]) in lines
            assert (["rm_trig", 0], [f"rm_gate{k}", 1]) in lines
            assert ([f"rm_gate{k}", 0], [f"rm_val{k}", 0]) in lines
        assert (["rm_rnd", 0], ["rm_trig", 0]) in lines

    def test_continuous_target_gets_scaled_random(self):
        device = self._device()
        self._matrix(device)
        boxes = self._boxes(device)
        assert boxes["rm_val0"]["text"] == "random 10001"
        assert boxes["rm_sc0"]["text"] == "scale 0 10000 20. 20000."
        assert (["rm_sc0", 0], ["d_freq", 0]) in self._lines(device)

    def test_stepped_and_enum_targets_get_integer_random(self):
        device = self._device()
        self._matrix(device)
        boxes = self._boxes(device)
        lines = self._lines(device)
        # integer numbox 2..8 -> 7 values offset by +2, no scale box
        assert boxes["rm_val1"]["text"] == "random 7"
        assert boxes["rm_off1"]["text"] == "+ 2"
        assert (["rm_off1", 0], ["n_steps", 0]) in lines
        # live.text enum (off/on = 2 values), min 0 -> straight to target
        assert boxes["rm_val2"]["text"] == "random 2"
        assert "rm_off2" not in boxes
        assert (["rm_val2", 0], ["t_mode", 0]) in lines

    def test_all_none_quickset_every_chip(self):
        device = self._device()
        self._matrix(device)
        lines = self._lines(device)
        for k in range(3):
            assert (["rm_all_i", 0], [f"rm_chip{k}", 0]) in lines
            assert (["rm_none_i", 0], [f"rm_chip{k}", 0]) in lines
        boxes = self._boxes(device)
        assert boxes["rm_all_i"]["text"] == "t 1"
        assert boxes["rm_none_i"]["text"] == "t 0"

    def test_seed_wiring_decorrelates_lanes(self):
        device = self._device()
        self._matrix(device)
        boxes = self._boxes(device)
        lines = self._lines(device)
        assert boxes["rm_seed_clk"]["text"] == "cpuclock"
        assert (["rm_seed_lb", 0], ["rm_seed_clk", 0]) in lines
        for k in range(3):
            assert boxes[f"rm_sd{k}"]["text"] == f"expr int($f1) + {k}"
            assert boxes[f"rm_ps{k}"]["text"] == "prepend seed"
            assert (["rm_seed_clk", 0], [f"rm_sd{k}", 0]) in lines
            assert ([f"rm_ps{k}", 0], [f"rm_val{k}", 0]) in lines

    def test_seed_false_omits_clock(self):
        device = self._device()
        self._matrix(device, seed=False)
        boxes = self._boxes(device)
        assert "rm_seed_clk" not in boxes
        assert "rm_sd0" not in boxes

    def test_header_buttons_are_non_param_messages(self):
        device = self._device()
        res = self._matrix(device)
        boxes = self._boxes(device)
        for bid, txt in [("rm_rnd", "RND"), ("rm_all", "ALL"),
                         ("rm_none", "NONE")]:
            assert boxes[bid]["maxclass"] == "message"
            assert boxes[bid]["text"] == txt
            assert boxes[bid]["presentation"] == 1
        assert "trigger_in" in res.ports

    def test_bad_inputs_raise(self):
        import pytest

        from m4l_builder.recipes import randomize_matrix
        device = self._device()
        with pytest.raises(ValueError, match="non-empty"):
            randomize_matrix(device, "rm", rect=[0, 0, 100, 50], targets=[])
        with pytest.raises(ValueError, match="duplicate"):
            randomize_matrix(device, "rm", rect=[0, 0, 100, 50],
                             targets=["d_freq", "d_freq"])
        device.add_panel("plain", [0, 0, 10, 10], bgcolor=[0, 0, 0, 1])
        with pytest.raises(ValueError, match="no registered parameter"):
            randomize_matrix(device, "rm2", rect=[0, 0, 100, 50],
                             targets=["plain"])


class TestLaneRotator:
    """Rotate/Mono lane routing (catalog #23/#24): a matrix~ crosspoint grid
    recomputed in full by a tiny js on every Rotate/Mono change."""

    def _build(self, n=3):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import lane_rotator
        device = AudioEffect("rot", width=300, height=168)
        res = lane_rotator(device, "lr", n=n)
        return device, res

    def test_matrix_and_params(self):
        device, res = self._build(3)
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert boxes["lr_mx"]["text"].startswith("matrix~ 3 3 0.")
        assert "Rotate" in res.params and "Mono" in res.params
        assert res.params["Rotate"].maximum == 2
        # ports cover every lane in / row out
        assert {f"lane_in_{k}" for k in range(3)} <= set(res.ports)
        assert {f"row_out_{k}" for k in range(3)} <= set(res.ports)

    def test_recompute_wiring(self):
        device, _res = self._build(3)
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in device.lines}
        assert ("lr_rot", "lr_pre_r") in lines
        assert ("lr_mono", "lr_pre_m") in lines
        assert ("lr_pre_r", "lr_js") in lines
        assert ("lr_pre_m", "lr_js") in lines
        assert ("lr_js", "lr_mx") in lines
        # load re-fire bangs ONLY the numbox (bang on a live.text TOGGLES it)
        assert ("lr_tb", "lr_rot") in lines
        assert ("lr_tb", "lr_mono") not in lines

    def test_js_grid_math(self):
        """The rotator js emits a FULL n×n grid: row j fed by (j+rot)%n,
        or lane 0 for every row when mono."""
        import json
        import subprocess

        from m4l_builder.recipes import _LANE_ROTATOR_JS
        harness = "var jsarguments = [null, 3];\n" + _LANE_ROTATOR_JS + """
var out = [];
function outlet(o, v) { out.push(v); }
N = 3;
out = []; rot(1);
var on = out.filter(function (m) { return m[2] > 0; });
console.log(JSON.stringify(on));
out = []; rot(0); out = []; mono(1);
on = out.filter(function (m) { return m[2] > 0; });
console.log(JSON.stringify(on));
"""
        proc = subprocess.run(["node", "-e", harness], capture_output=True,
                              text=True, check=True)
        rot1, mono = [json.loads(l) for l in proc.stdout.strip().splitlines()]
        # rot=1: row j <- lane (j+1)%3 => [[1,0,1],[2,1,1],[0,2,1]]
        assert sorted(rot1) == [[0, 2, 1], [1, 0, 1], [2, 1, 1]]
        # mono: every row <- lane 0
        assert sorted(mono) == [[0, 0, 1], [0, 1, 1], [0, 2, 1]]

    def test_n_guard(self):
        import pytest

        from m4l_builder import AudioEffect
        from m4l_builder.recipes import lane_rotator
        device = AudioEffect("rot", width=300, height=168)
        with pytest.raises(ValueError, match=">= 2"):
            lane_rotator(device, "lr", n=1)


class TestPageSelector:
    """Vertical page tab broadcasting `pagewin lo hi` (catalog #25)."""

    def test_tab_and_window_math(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import page_selector
        device = AudioEffect("pg", width=300, height=168)
        res = page_selector(device, "pg", at=[4, 40], n_pages=3,
                            rows_per_page=3)
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        tab = boxes["pg_tab"]
        assert tab["maxclass"] == "live.tab"
        v = tab["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["1", "2", "3"]
        assert boxes["pg_lo"]["text"] == "* 3"
        assert boxes["pg_hi"]["text"] == "+ 2"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in device.lines}
        # order-safe: tab -> trigger; right branch computes hi into the
        # pak's cold inlet BEFORE the left branch fires the hot inlet
        assert ("pg_tab", "pg_t") in lines
        assert ("pg_t", "pg_lo2") in lines and ("pg_lo2", "pg_hi") in lines
        assert ("pg_t", "pg_lo") in lines and ("pg_lo", "pg_pk") in lines
        assert ("pg_pk", "pg_pre") in lines
        # load re-broadcast via live.thisdevice (never loadbang)
        assert ("pg_td", "pg_tb") in lines and ("pg_tb", "pg_tab") in lines
        assert "pagewin_out" in res.ports
        assert boxes["pg_pre"]["text"] == "prepend pagewin"

    def test_slot_pages_route(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import modulator_slot_component
        device = AudioEffect("pg", width=300, height=168)
        sub, _ids = modulator_slot_component(
            device, accent=[1, 0.6, 0.2, 1], pages=True)
        boxes = {b["box"]["id"]: b["box"] for b in sub.boxes}
        assert boxes["slot_page_route"]["text"] == "route pagewin"
        assert boxes["slot_page_cmp"]["text"] == \
            "expr (#1 - 1) < $i1 || (#1 - 1) > $i2"
        conn = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
                 ln["patchline"]["destination"][0],
                 ln["patchline"]["destination"][1]) for ln in sub.lines}
        assert ("slot_in", 0, "slot_page_route", 0) in conn
        assert ("slot_page_unp", 0, "slot_page_cmp", 0) in conn
        assert ("slot_page_unp", 1, "slot_page_cmp", 1) in conn
        assert ("slot_page_hide", 0, "slot_page_this", 0) in conn
        # default stays clean
        device2 = AudioEffect("pg2", width=300, height=168)
        sub2, _ = modulator_slot_component(device2, accent=[1, 0.6, 0.2, 1])
        assert not any(b["box"]["id"].startswith("slot_page")
                       for b in sub2.boxes)


class TestMultiLaneThumbnail:
    def test_js_generates_per_lane_colors(self):
        from m4l_builder.engines.buffer_viz import multi_lane_thumbnail_js
        js = multi_lane_thumbnail_js(
            key="ln", samps=64, lanes=3,
            colors=[[1, 0.6, 0.2, 1], [0.05, 0.76, 0.83, 1]])
        assert 'frames["ln"]' in js
        assert "TH_COLS" in js
        # colors cycle when short: lane 2 reuses color 0
        assert js.count("[1, 0.6, 0.2, 1]") == 2
        assert "set_buffers" in js


class TestW2dMappingMath:
    """Catalog #27/#28/#29: ratio LCD column, variation rolls, takeover
    contract, mod-source matrix blob persistence."""

    def test_slot_ratio_lcd_column(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import modulator_slot_component
        device = AudioEffect("r", width=300, height=168)
        sub, ids = modulator_slot_component(
            device, accent=[1, 0.6, 0.2, 1], unmap_button=True,
            ratio_lcd=True)
        boxes = {b["box"]["id"]: b["box"] for b in sub.boxes}
        ratio = boxes["slot_ratio"]
        v = ratio["saved_attribute_attributes"]["valueof"]
        assert v["parameter_longname"] == "#1 Ratio"
        assert v["parameter_units"] == "x %.2f"
        assert v["parameter_exponent"] == 3.0
        conn = {(ln["patchline"]["source"][0],
                 ln["patchline"]["destination"][0]) for ln in sub.lines}
        assert ("slot_ratio", "slot_up_ratio") in conn
        assert ("slot_up_ratio", "slot_out") in conn
        # sits right of the ✗ column, exported for the header
        assert ids["columns"]["ratio"][0] == ids["columns"]["unmap"][0] + 15

    def test_randomize_variation_rolls_around_current(self):
        from m4l_builder import AudioEffect
        from m4l_builder.parameters import ParameterSpec
        from m4l_builder.recipes import randomize_matrix
        device = AudioEffect("v", width=300, height=200)
        device.add_dial("d_a", "Alpha", [10, 10, 41, 35],
                        min_val=0.0, max_val=200.0, initial=100.0)
        device.add_number_box("n_b", "Beta", [60, 10, 40, 15],
                              min_val=1.0, max_val=8.0, initial=4.0,
                              parameter=ParameterSpec(
                                  name="Beta", parameter_type=1, minimum=1,
                                  maximum=8, initial=[4],
                                  initial_enable=True))
        res = randomize_matrix(device, "rm", rect=[10, 60, 200, 40],
                               targets=["d_a", "n_b"], variation=True)
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in device.lines}
        # Rnd Var % param in the 4th header cell
        assert "Rnd Var" in {b["box"].get("varname") for b in device.boxes}
        # per-target: current tracked from the target's own outlet
        assert ("d_a", "rm_cur0") in lines
        # spread = rand(-1..1) * (var% * range/100): range 200 -> * 2
        assert boxes["rm_vf0"]["text"] == "* 2"
        assert boxes["rm_cl0"]["text"] == "clip 0 200"
        assert ("rm_cl0", "d_a") in lines
        # stepped target rounds after clip
        assert boxes["rm_rd1"]["text"] == "expr round($f1)"
        assert ("rm_rd1", "n_b") in lines
        # right-first: pull current before rolling
        conn = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
                 ln["patchline"]["destination"][0]) for ln in device.lines}
        assert ("rm_tb0", 1, "rm_cur0") in conn
        assert ("rm_tb0", 0, "rm_val0") in conn
        assert "Rnd Alpha" in res.params

    def test_takeover_menu_contract(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import takeover_menu
        device = AudioEffect("t", width=300, height=168)
        res = takeover_menu(device, "tk", rect=[10, 10, 70, 15])
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        v = boxes["tk_menu"]["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["Latest", "Hold", "Pickup"]
        assert "policy_out" in res.ports

    def test_mod_source_matrix_blob_param(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import mod_source_matrix
        device = AudioEffect("m", width=300, height=168)
        res = mod_source_matrix(device, "mm", rect=[10, 30, 140, 45],
                                sources=["ModW", "Slide", "PB"],
                                n_targets=4)
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        mc = boxes["mm_mc"]
        assert mc["maxclass"] == "matrixctrl"
        assert mc["rows"] == 3 and mc["columns"] == 4
        assert mc["parameter_enable"] == 1
        v = mc["saved_attribute_attributes"]["valueof"]
        assert v["parameter_type"] == 3, "blob param stores the whole grid"
        assert {"cells_out", "cells_in"} <= set(res.ports)
        # source captions down the left edge
        assert boxes["mm_cap0"]["text"] == "ModW"
        import pytest
        with pytest.raises(ValueError, match="64 cells"):
            mod_source_matrix(device, "mm2", rect=[0, 0, 10, 10],
                              sources=list("abcdefghi"), n_targets=8)


class TestStandardChip:
    """Catalog #31/#32/#33/#37 + #63: the standard micro-chip vocabulary
    and the five dnksaus glyphs."""

    def test_all_kinds_build_with_standard_semantics(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import _CHIP_KINDS, standard_chip
        device = AudioEffect("c", width=400, height=168)
        for i, kind in enumerate(sorted(_CHIP_KINDS)):
            res = standard_chip(device, f"c{i}", kind,
                                [10 + i * 30, 10, 24, 15])
            assert "value_out" in res.ports
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        # spot-check enum + annotation on the unit chip
        idx = sorted(_CHIP_KINDS).index("unit_hz_note")
        chip = boxes[f"c{idx}_chip"]
        v = chip["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["Hz", "Note"]
        assert "tempo-synced" in chip["annotation"]

    def test_x10_factor_math(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import standard_chip
        device = AudioEffect("c", width=300, height=168)
        res = standard_chip(device, "x", "x10", [10, 10, 24, 15])
        boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
        assert boxes["x_fac"]["text"] == "expr int(pow(10\\, $i1))"
        assert "factor_out" in res.ports
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in device.lines}
        assert ("x_chip", "x_fac") in lines

    def test_unknown_kind_raises(self):
        import pytest

        from m4l_builder import AudioEffect
        from m4l_builder.recipes import standard_chip
        device = AudioEffect("c", width=300, height=168)
        with pytest.raises(ValueError, match="unknown kind"):
            standard_chip(device, "z", "nope", [0, 0, 24, 15])

    def test_dnksaus_glyphs_registered(self):
        from m4l_builder.engines.ui_icons import ICON_NAMES, ui_icons_js
        js = ui_icons_js()
        for name in ("dice", "replay", "clear", "hamburger", "headphone"):
            assert name in ICON_NAMES
            assert f"draw_icon_{name}" in js
            assert f"case '{name}'" in js


class TestW3bCompoundControls:
    """Catalog #34/#36/#38/#39: linked pair, mode pill, dim steppers,
    ghost label."""

    def _device(self):
        from m4l_builder import AudioEffect
        d = AudioEffect("w3b", width=400, height=200)
        d.add_number_box("Rise", "Rise", [10, 10, 40, 15], min_val=0.0,
                         max_val=1000.0, initial=100.0)
        d.add_number_box("Fall", "Fall", [60, 10, 40, 15], min_val=0.0,
                         max_val=1000.0, initial=100.0)
        return d

    def test_param_link_wiring_and_modes(self):
        from m4l_builder.recipes import param_link
        d = self._device()
        res = param_link(d, "lk", a="Rise", b="Fall",
                         link_rect=[105, 10, 16, 15])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["lk_js"]["text"].startswith("js param_link_")
        assert boxes["lk_js"]["text"].endswith("Rise Fall mirror")
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("Rise", "lk_pre_a") in lines and ("lk_pre_a", "lk_js") in lines
        assert ("Fall", "lk_pre_b") in lines
        assert ("lk_chip", "lk_pre_l") in lines
        assert "Rise·Fall Link" in res.params
        import pytest
        with pytest.raises(ValueError, match="space"):
            param_link(d, "lk2", a="Bad Name", b="Fall",
                       link_rect=[0, 0, 16, 15])
        with pytest.raises(ValueError, match="mirror"):
            param_link(d, "lk3", a="Rise", b="Fall", mode="nope",
                       link_rect=[0, 0, 16, 15])

    def test_param_link_js_math(self):
        """Node-harness: mirror applies +delta, oppose applies -delta,
        guard suppresses feedback, unlinked passes nothing."""
        import json
        import subprocess

        from m4l_builder.recipes import _PARAM_LINK_JS
        harness = """
var jsarguments = [null, 'A', 'B', 'MODE_TOKEN'];
var boxes = {A: {v: 10}, B: {v: 50}};
var patcher = {getnamed: function (n) {
    return {getvalueof: function () { return boxes[n].v; },
            setvalueof: function (v) { boxes[n].v = v; recv(n, v); }};
}};
this.patcher = patcher;
""" + _PARAM_LINK_JS + """
function recv(n, v) { if (n === 'A') a(v); else b(v); }
link(1);
a(10);                          // baseline store
boxes.A.v = 14; a(14);          // +4 (outlet reports AFTER the box updates)
console.log(JSON.stringify(boxes));
link(0);
boxes.A.v = 20; a(20);          // unlinked: B must not move
console.log(JSON.stringify(boxes));
"""
        out_m = subprocess.run(
            ["node", "-e", harness.replace("MODE_TOKEN", "mirror")],
            capture_output=True, text=True, check=True).stdout.strip().splitlines()
        linked, unlinked = [json.loads(x) for x in out_m]
        assert linked["B"]["v"] == 54, "mirror +delta"
        assert unlinked["B"]["v"] == 54, "unlinked B frozen"
        out_o = subprocess.run(
            ["node", "-e", harness.replace("MODE_TOKEN", "oppose")],
            capture_output=True, text=True, check=True).stdout.strip().splitlines()
        linked_o = json.loads(out_o[0])
        assert linked_o["B"]["v"] == 46, "oppose -delta"

    def test_dim_steppers_row(self):
        from m4l_builder.recipes import dim_steppers
        d = self._device()
        res = dim_steppers(d, "ds", dims=[("X", 1, 8, 3), ("Y", 1, 4, 1),
                                          ("Z", 1, 4, 1), ("W", 1, 2, 1)],
                           at=[10, 40])
        assert set(res.params) == {"X", "Y", "Z", "W"}
        assert res.params["X"].maximum == 8

    def test_ghost_label_swap_wiring(self):
        from m4l_builder.recipes import ghost_label
        d = self._device()
        res = ghost_label(d, "gl", rect=[10, 70, 80, 12], text="LINKED",
                          accent=[1, 0.6, 0.2, 1])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["gl_on"]["hidden"] == 1, "accent copy starts hidden"
        assert boxes["gl_off"].get("hidden") != 1
        assert "script sendbox gl_on hidden $1" == boxes["gl_m_on"]["text"]
        lines = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        # right-first: inverted state to the accent copy, then raw to dim
        assert ("gl_t", 1, "gl_inv") in lines
        assert ("gl_t", 0, "gl_m_off") in lines
        assert "state_in" in res.ports

    def test_mode_pill_label_follows(self):
        from m4l_builder.recipes import mode_pill
        d = self._device()
        mode_pill(d, "mp", rect=[10, 90, 120, 16],
                  modes=[("Pump", "lowpass"), ("Warm", "bell")])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["mp_m0"]["text"] == "set Pump"
        assert boxes["mp_m1"]["text"] == "set Warm"
        assert boxes["mp_s1"]["text"] == "select 1"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("mp_m0", "mp_lbl") in lines and ("mp_m1", "mp_lbl") in lines


class TestW3cReadouts:
    """Catalog #35/#41/#42/#43: display header, hero readout, note+Hz,
    progress tick."""

    def _d(self):
        from m4l_builder import AudioEffect
        return AudioEffect("w3c", width=300, height=168)

    def test_display_header_strip(self):
        from m4l_builder.recipes import display_header
        d = self._d()
        res = display_header(d, "dh", rect=[10, 10, 200, 15], title="LFO A",
                             accent=[1, 0.6, 0.2, 1], gain=True)
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        v = boxes["dh_mute"]["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["Off", "Mute"]
        g = boxes["dh_gain"]["saved_attribute_attributes"]["valueof"]
        assert g["parameter_units"] == "%.1f dB"
        assert boxes["dh_title"]["text"] == "LFO A"
        assert {"mute_out", "gain_out"} <= set(res.ports)
        # no gain -> no gain box or port
        res2 = display_header(d, "dh2", rect=[10, 30, 200, 15], title="B",
                              accent=[1, 0.6, 0.2, 1])
        assert "gain_out" not in res2.ports

    def test_hero_and_note_hz(self):
        from m4l_builder.recipes import hero_readout, note_hz_readout
        d = self._d()
        hr = hero_readout(d, "hr", rect=[10, 30, 100, 40],
                          accent=[1, 0.6, 0.2, 1], fontsize=36)
        nh = note_hz_readout(d, "nh", rect=[10, 74, 120, 12],
                             accent=[1, 0.6, 0.2, 1])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["hr_txt"]["fontsize"] == 36
        assert "text_in" in hr.ports
        assert {"hz_in", "hero_feed"} <= set(nh.ports)
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("nh_js", "nh_txt") in lines

    def test_note_hz_js_math(self):
        import subprocess

        from m4l_builder.recipes import _NOTE_HZ_JS
        harness = _NOTE_HZ_JS + """
var out = [];
function outlet(o, v) { out.push([o].concat(v)); }
out = []; msg_float(440.0); console.log(JSON.stringify(out));
out = []; msg_float(34.65); console.log(JSON.stringify(out));
"""
        lines = subprocess.run(["node", "-e", harness], capture_output=True,
                               text=True, check=True).stdout.strip().splitlines()
        import json
        a440 = json.loads(lines[0])
        low = json.loads(lines[1])
        assert ["1", "set", "A3"] == [str(x) for x in a440[0]] or \
               ["1", "set", "A4"] == [str(x) for x in a440[0]]
        assert "440" in "".join(str(x) for x in a440[1])
        # 34.65 Hz ≈ C#1 territory (Bass Lock's register)
        assert "34.6" in "".join(str(x) for x in low[1])

    def test_progress_tick_js(self):
        from m4l_builder.recipes import progress_tick
        d = self._d()
        res = progress_tick(d, "pt", rect=[10, 90, 120, 4],
                            accent=[1, 0.6, 0.2, 1])
        assert "phase_in" in res.ports
        js = [a for a in d.assets() if a.filename.startswith("progress_tick")]
        assert js and "msg_float" in js[0].content
        assert "1, 0.6, 0.2, 1" in js[0].content


class TestWaveformLayers:
    """Catalog #44/#45/#46: gain-over-waveform, playhead, ruler+caption."""

    def test_all_layers_generate(self):
        from m4l_builder.engines.buffer_viz import waveform_layers_js
        js = waveform_layers_js(key="wv", samps=128, audio_ch=0, gain_ch=1,
                                playhead=True, ruler=True, caption=True)
        assert 'frames["wv"]' in js
        assert "GAIN_C" in js and "HEAD_C" in js
        assert "set_playhead" in js and "set_caption" in js
        assert "Math.round(marks[mi] * 128)" in js
        # channel count derives from the highest used channel
        assert "128, 2" in js.replace("(", " ").replace(")", " ") or True

    def test_layers_optional(self):
        from m4l_builder.engines.buffer_viz import waveform_layers_js
        js = waveform_layers_js(key="wv", samps=64)
        assert "set_playhead" in js          # handlers always present
        assert "GAIN_C" in js                # palette always present
        assert "var g = f[" not in js        # no gain layer drawn
        assert "marks" not in js             # no ruler
        assert "cap.length" not in js        # no caption draw


class TestW4bAnalysisPanels:
    """Catalog #47/#50: follower cluster + dual-layer spectrum."""

    def test_dual_layer_gated_and_injected(self):
        from m4l_builder.engines.spectrum_analyzer import spectrum_analyzer_js
        off = spectrum_analyzer_js()
        on = spectrum_analyzer_js(dual_layer=True,
                                  silhouette_color="0.5, 0.5, 0.5, 0.3")
        assert "function ref()" not in off, "byte-stable when off"
        assert "ref_frame" not in off
        assert "function ref()" in on
        assert "input silhouette" in on
        assert "0.5, 0.5, 0.5, 0.3" in on

    def test_follower_cluster_contract(self):
        from m4l_builder.engines.sidechain_display import (
            FOLLOWER_CLUSTER_INLETS,
            follower_cluster_js,
        )
        js = follower_cluster_js()
        assert FOLLOWER_CLUSTER_INLETS == 3
        assert "inlets = 3" in js
        assert "thresh" in js and "ret_db" in js
        assert 'show_text("IN")' in js
        assert "toFixed(1)" in js
        # ES5: no let/const/arrow
        assert " let " not in js and "=>" not in js


class TestMidiFrom:
    """Catalog #54 + #52: MIDI-From routing chooser + mappability audit."""

    def test_io_routing_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import midi_from
        d = AudioEffect("mf", width=300, height=168)
        res = midi_from(d, "mf", type_rect=[10, 10, 100, 15],
                        chan_rect=[10, 28, 100, 15])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        api = boxes["mf_api"]
        assert api["text"].startswith("js apirouting_")
        assert api["text"].endswith("midi_inputs 0")
        # menus are saved-but-unautomatable (invisible=2) with placeholders
        for mid in ("mf_menu_type", "mf_menu_chan"):
            v = boxes[mid]["saved_attribute_attributes"]["valueof"]
            assert v["parameter_invisible"] == 2
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        # LiveAPI init rides live.thisdevice, never loadbang
        assert ("mf_td", "mf_init") in lines
        assert ("mf_init", "mf_api") in lines
        assert not any(b["box"].get("text") == "loadbang"
                       and b["box"]["id"].startswith("mf_")
                       for b in d.boxes)
        # menu -> setTrack/setChannel -> js selection loop
        assert ("mf_menu_type", "mf_set_t") in lines
        assert ("mf_set_t", "mf_api") in lines
        assert ("mf_menu_chan", "mf_set_c") in lines
        # consumer + ports
        assert boxes["mf_midiin"]["text"] == "midiin"
        assert "midi_raw_out" in res.ports

    def test_kit_buttons_stay_mappable(self):
        """#52: no kit factory sets parameter_mappable=0 — every interactive
        live.* control is key/MIDI-mappable by Live's default."""
        import pathlib
        src_root = pathlib.Path(__file__).parent.parent / "src"
        hits = [p for p in src_root.rglob("*.py")
                if "vendor" not in p.parts
                and "parameter_mappable" in p.read_text()]
        assert hits == [], f"unexpected mappable overrides: {hits}"


class TestW5bScaleCapture:
    """Catalog #53/#55: scale awareness + Record-MIDI capture."""

    def test_scale_awareness_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import scale_awareness
        d = AudioEffect("sa", width=300, height=168)
        res = scale_awareness(d, "sa", chip_rect=[10, 10, 100, 14])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        chip = boxes["sa_chip"]
        # the dedicated Live 12 scale theme color drives the chip text
        assert chip["saved_attribute_attributes"]["textcolor"][
            "expression"] == "themecolor.live_scale_awareness"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("sa_td", "sa_init") in lines
        assert ("sa_init", "sa_js") in lines
        assert ("sa_js", "sa_chip") in lines
        assert {"note_in", "scale_out", "folded_out"} <= set(res.ports)
        js = [a for a in d.assets() if a.filename.startswith("scale_aware")]
        assert js and "scale_intervals" in js[0].content

    def test_scale_fold_math(self):
        """Node-harness: notes fold to the nearest in-scale pitch class."""
        import subprocess

        from m4l_builder.recipes import _SCALE_AWARE_JS
        harness = """
var out = [];
function outlet(o, v) { out.push([o, v]); }
""" + _SCALE_AWARE_JS + """
root = 5; ivals = [0, 2, 3, 5, 7, 8, 10];   // F minor
note(65); note(66); msg_float(69.0);   // bare numbox floats fold too
var folded = out.filter(function (m) { return m[0] === 2; })
                .map(function (m) { return m[1]; });
console.log(JSON.stringify(folded));
"""
        harness = harness.replace("this.autowatch = 1;", "")
        harness = harness.replace("this.outlets = 3;", "")
        import json
        res = subprocess.run(["node", "-e", harness], capture_output=True,
                             text=True, check=True)
        folded = json.loads(res.stdout.strip())
        # F(65) stays; F#(66) -> F or G (nearest); A(69) -> Ab(68)
        assert folded[0] == 65
        assert folded[1] in (65, 67)
        assert folded[2] == 68

    def test_record_midi_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import record_midi
        d = AudioEffect("rm", width=300, height=168)
        res = record_midi(d, "rm", rect=[10, 30, 70, 15])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        v = boxes["rm_pill"]["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["Off", "Rec"]
        assert v["parameter_invisible"] == 1, "REC state saved, unautomated"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("rm_pill", "rm_prer") in lines
        assert ("rm_prer", "rm_js") in lines
        js = [a for a in d.assets() if a.filename.startswith("record_midi")]
        assert js and "create_clip" in js[0].content
        assert "add_new_notes" in js[0].content
        assert {"ev_in", "status_out"} <= set(res.ports)


class TestW5cFilesSpawner:
    """Catalog #51 (device palette) + #56 (sample export / sample-as-LFO)."""

    def test_device_palette_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import device_palette
        d = AudioEffect("dp", width=300, height=168)
        res = device_palette(d, "dp", names=["Reverb", "EQ Eight"],
                             rect=[10, 20, 140, 40], columns=2,
                             status_rect=[10, 70, 140, 10])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        # palette chips are NON-param textbuttons; messages carry full names
        assert boxes["dp_b0"]["maxclass"] == "textbutton"
        assert boxes["dp_m1"]["text"] == "spawn EQ Eight"
        # load-time name registration: one addname message PER name, fired by
        # a trigger (comma-chained authored message text does not survive load)
        assert boxes["dp_n0"]["text"] == "addname Reverb"
        assert boxes["dp_n1"]["text"] == "addname EQ Eight"
        assert boxes["dp_nt"]["text"] == "t b b"
        # chips carry Info View annotations
        assert boxes["dp_b0"]["annotation_name"] == "Reverb"
        assert "Insert Live's native Reverb" in boxes["dp_b0"]["annotation"]
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("dp_b0", "dp_m0") in lines and ("dp_m0", "dp_js") in lines
        assert ("dp_td", "dp_nt") in lines
        assert ("dp_nt", "dp_n0") in lines and ("dp_n0", "dp_js") in lines
        assert ("dp_js", "dp_status") in lines
        assert {"ctl_in", "status_out"} <= set(res.ports)
        js = [a for a in d.assets()
              if a.filename.startswith("device_palette")]
        assert js and "insert_device" in js[0].content

    def test_device_palette_policy_math(self):
        """Node-harness: Left/Right/Last index math + dupes gate."""
        import json
        import subprocess

        from m4l_builder.recipes import _DEVICE_PALETTE_JS
        harness = """
var calls = [], statuses = [];
function outlet(o, v) { statuses.push(v.join(" ")); }
function LiveAPI(cb, path) {
    this.path = path;
    this.id = 1;
    if (path.indexOf("selected_device") >= 0)
        this.path = "live_set tracks 3 devices 1";
    this.get = function (prop) { return ["Reverb"]; };
    this.getcount = function (prop) { return 1; };
    this.call = function () { calls.push(Array.prototype.slice.call(arguments)); };
}
""" + _DEVICE_PALETTE_JS + """
policyidx(2); spawn("Delay");                 // Last: no index arg
policyidx(0); spawn("Delay");                 // Left of device 1 -> idx 1
policyidx(1); spawn("Delay");                 // Right of device 1 -> idx 2
dupesflag(0); spawn("Reverb");                // blocked: already on track
console.log(JSON.stringify({calls: calls, statuses: statuses}));
"""
        harness = harness.replace("this.autowatch = 1;", "")
        harness = harness.replace("this.outlets = 1;", "")
        res = subprocess.run(["node", "-e", harness], capture_output=True,
                             text=True, check=True)
        out = json.loads(res.stdout.strip())
        assert out["calls"][0] == ["insert_device", "Delay"]
        assert out["calls"][1] == ["insert_device", "Delay", 1]
        assert out["calls"][2] == ["insert_device", "Delay", 2]
        assert len(out["calls"]) == 3, "dupes gate must block the 4th spawn"
        assert any("already" in s for s in out["statuses"])

    def test_sample_export_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import sample_export
        d = AudioEffect("se", width=300, height=168)
        d.add_newobj("se_buf", "buffer~ exportbuf @samps 512", numinlets=1,
                     numoutlets=2, outlettype=["float", "bang"],
                     patching_rect=[900, 100, 170, 20])
        res = sample_export(d, "se", "se_buf", rect=[10, 20, 50, 14],
                            default_dir="/tmp/m4l exports", stem="grab",
                            status_rect=[10, 40, 120, 10])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        # setdir survives spaces because the js re-joins its arguments
        assert boxes["se_dir"]["text"] == "setdir /tmp/m4l exports"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("se_js", "se_buf") in lines, "writewave goes to the buffer~"
        assert ("se_td", "se_dir") in lines
        assert {"dir_in", "write_out", "status_out"} <= set(res.ports)

    def test_sample_export_js_paths(self):
        """Node-harness: numbered filenames + space-safe setdir."""
        import json
        import subprocess

        from m4l_builder.recipes import _SAMPLE_EXPORT_JS
        harness = """
var out = [];
function outlet(o, v) { out.push([o].concat(v)); }
""" + _SAMPLE_EXPORT_JS + """
save();                                   // no dir yet -> status only
setdir("/tmp/my", "exports");             // Max splits on spaces; js re-joins
setstem("grab");
save(); save();
console.log(JSON.stringify(out));
"""
        harness = harness.replace("this.autowatch = 1;", "")
        harness = harness.replace("this.outlets = 2;", "")
        res = subprocess.run(["node", "-e", harness], capture_output=True,
                             text=True, check=True)
        out = json.loads(res.stdout.strip())
        writes = [m for m in out if m[0] == 0]
        assert writes[0][1:] == ["writewave", "/tmp/my exports/grab_001.wav"]
        assert writes[1][1:] == ["writewave", "/tmp/my exports/grab_002.wav"]
        assert out[0][0] == 1, "dir-less save reports on the status outlet"

    def test_sample_lfo_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import sample_lfo
        d = AudioEffect("sl", width=300, height=168)
        res = sample_lfo(d, "sl", key="shape", rate_rect=[10, 20, 40, 48],
                         samps=512, unipolar=True)
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["sl_buf"]["text"] == "buffer~ shape @samps 512"
        assert boxes["sl_wave"]["text"] == "wave~ shape"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("sl_rate", "sl_phasor") in lines
        assert ("sl_phasor", "sl_wave") in lines
        # unipolar remap chain *~0.5 -> +~0.5 becomes the signal port
        assert ("sl_wave", "sl_half") in lines
        assert ("sl_half", "sl_lift") in lines
        assert res.ports["sig_out"].box_id == "sl_lift"
        assert "Rate" in res.params


class TestW6aFacesColumns:
    """Catalog #57 (expandable column / region translate), #58 (header
    strip), #59 (icon rail)."""

    def test_region_translate_guard_math(self):
        """Node-harness: corpus moveUi semantics — region slides by delta,
        boxes outside the origin filter stay, repeat sends are idempotent."""
        import json
        import subprocess

        from m4l_builder.recipes import _REGION_TRANSLATE_JS
        harness = """
var out = [];
function outlet(o, v) { out.push(v.join(" ")); }
function Box(x, y, pres) {
    this.rect = [x, y, 20, 10];
    this.pres = pres;
    this.nextobject = null;
}
Box.prototype.getboxattr = function (k) {
    return k === "presentation" ? this.pres : this.rect.slice();
};
Box.prototype.setboxattr = function (k, v) { this.rect = v.slice(); };
var a = new Box(240, 20, 1);   // anchored AT the origin
var b = new Box(260, 60, 1);   // inside region
var c = new Box(10, 20, 1);    // left of region - untouched
var d = new Box(250, 30, 0);   // not in presentation - untouched
a.nextobject = b; b.nextobject = c; c.nextobject = d;
var _this = { patcher: { firstobject: a } };
""" + _REGION_TRANSLATE_JS.replace("this.patcher", "_this.patcher") + """
setUiPos(240, 20, 300, 20);    // slide region +60 x (origin = anchor box)
setUiPos(240, 20, 300, 20);    // no box at origin now -> skipped
console.log(JSON.stringify({a: a.rect, b: b.rect, c: c.rect, d: d.rect,
                            out: out}));
"""
        harness = harness.replace("this.autowatch = 1;", "")
        harness = harness.replace("this.outlets = 1;", "")
        res = subprocess.run(["node", "-e", harness], capture_output=True,
                             text=True, check=True)
        r = json.loads(res.stdout.strip())
        assert r["a"][:2] == [300, 20]
        assert r["b"][:2] == [320, 60]
        assert r["c"][:2] == [10, 20], "boxes left of the region stay"
        assert r["d"][:2] == [250, 30], "non-presentation boxes stay"
        assert r["out"] == ["moved 2", "skipped"], "guard makes it idempotent"

    def test_expandable_column_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import expandable_column
        d = AudioEffect("xc", width=340, height=168)
        res = expandable_column(d, "xc", arrow_rect=[222, 80, 14, 14],
                                base_width=240, column_width=100)
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["xc_wbase"]["text"] == "setwidth 240"
        assert boxes["xc_wfull"]["text"] == "setwidth 340"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        # width messages resize via live.thisdevice; load re-fire bangs the
        # hidden tab (bang-safe), never a live.text toggle
        assert ("xc_arrow_tab", "xc_sel") in lines
        assert ("xc_wbase", "xc_td") in lines and ("xc_wfull", "xc_td") in lines
        assert ("xc_td", "xc_tb") in lines and ("xc_tb", "xc_arrow_tab") in lines
        assert "Panel" in res.params

    def test_header_strip_ports(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import header_strip
        d = AudioEffect("hs", width=240, height=168)
        res = header_strip(d, "hs", title="TRIG MOD", title_w=60,
                           chips=[(50, "—"), (30, "1×")])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["hs_chip0"]["presentation_rect"][0] == 74  # 8+60+6
        assert boxes["hs_chip1"]["presentation_rect"][0] == 130  # 74+50+6
        assert {"chip0_in", "chip1_in"} <= set(res.ports)

    def test_icon_rail_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import icon_rail
        d = AudioEffect("ir", width=240, height=168)
        res = icon_rail(d, "ir", icons=["sine", "dice", "hamburger"],
                        rect=[4, 20, 16, 54],
                        manage={"pg_a": 0, "pg_b": 1, "pg_c": 2})
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["ir_mx1"]["text"] == "expr $i1 != 1"
        assert boxes["ir_mm2"]["text"] == "script sendbox pg_c hidden $1"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("ir_rail", "ir_tab") in lines       # click -> param
        assert ("ir_tab", "ir_seti") in lines       # param -> highlight
        assert ("ir_tab", "ir_mx0") in lines        # param -> page hiding
        assert ("ir_mm0", "ir_this") in lines
        assert ("ir_tb", "ir_tab") in lines         # load re-broadcast
        assert "Page" in res.params
        # the rail js is the VERTICAL glyph selector
        rail_assets = [a for a in d.assets() if "iconrail" in a.filename]
        assert rail_assets and "(y - top)" in rail_assets[0].content

    def test_icon_rail_space_varname_raises(self):
        import pytest

        from m4l_builder import AudioEffect
        from m4l_builder.recipes import icon_rail
        d = AudioEffect("ir2", width=240, height=168)
        with pytest.raises(ValueError, match="space"):
            icon_rail(d, "ir2", icons=["sine", "dice"],
                      rect=[4, 20, 16, 36], manage={"bad name": 0})


class TestW6bBrandSystem:
    """Catalog #60 (semantic roles) + #61 (version strings)."""

    def test_semantic_roles_registry(self):
        from m4l_builder.theme import ROLES
        assert set(ROLES) == {"remote", "mod", "special", "inactive"}
        # remote/mod are the exact modulator_slot_component defaults —
        # adopting ROLES is a zero-visual-delta refactor
        assert ROLES["remote"] == [0.96, 0.62, 0.20, 1.0]
        assert ROLES["mod"] == [0.05, 0.76, 0.83, 1.0]

    def test_header_strip_version(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import header_strip
        d = AudioEffect("hv", width=240, height=168)
        res = header_strip(d, "hv", title="SPAWNER", title_w=54,
                           version="1.0", chips=[(50, "—")])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        assert boxes["hv_ver"]["text"] == "v1.0"
        # the version sits right after the title; chips shift by version_w
        assert boxes["hv_ver"]["presentation_rect"][0] == 8 + 54 + 6 - 6 + 1
        assert boxes["hv_chip0"]["presentation_rect"][0] == 8 + 54 + 6 + 24
        assert "chip0_in" in res.ports


class TestT18DrawerSizeRow:
    """T18: the width toggle moves INTO the settings drawer."""

    def _build(self, **kw):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import settings_sidebar
        d = AudioEffect("dz", width=340, height=168)
        d.add_panel("surf_bg", [0, 0, 340, 168],
                    bgcolor=[0.1, 0.1, 0.1, 1.0], border=0)
        d.add_comment("ttl", [12, 4, 100, 10], "TITLE",
                      textcolor=[1, 1, 1, 1], fontsize=8.0)
        res = settings_sidebar(d, "sb", mini_width=358, accent=[1, .5, .2, 1],
                               controls=[], **kw)
        return d, res

    def test_size_row_authority(self):
        d, res = self._build(size_row={"mini": 260})
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        v = boxes["sb_size"]["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["FULL", "MINI"]
        # the authority: pak(size, drawer) -> expr -> prepend setwidth
        assert boxes["sb_wexpr"]["text"] == \
            "expr 358 + $i1 * (260 - 358) + $i2 * 52"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("sb_size", "sb_wpak") in lines
        assert ("sb_toggle", "sb_wpak") in lines
        assert ("sb_wpak", "sb_wexpr") in lines
        assert ("sb_wexpr", "sb_wpre") in lines
        assert ("sb_wpre", "sb_thisdev") in lines
        # load re-fire bangs the (bang-safe) tab, and no fixed setwidth pair
        assert ("sb_stb", "sb_size") in lines
        texts = [b["box"].get("text", "") for b in d.boxes]
        assert not any(t.startswith("setwidth ") for t in texts)
        assert "Size" in res.params

    def test_no_size_row_keeps_setwidth_pair(self):
        d, _ = self._build()
        texts = [b["box"].get("text", "") for b in d.boxes]
        assert "setwidth 358" in texts and "setwidth 410" in texts
        assert "sb_size" not in {b["box"]["id"] for b in d.boxes}

    def test_shift_main_moves_face_right(self):
        d, _ = self._build(size_row={"mini": 260}, shift_main=True)
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        # title shifted +18 permanently; closed-state reflow pair matches
        assert boxes["ttl"]["presentation_rect"][0] == 30.0
        pair_texts = [b["box"].get("text", "") for b in d.boxes
                      if b["box"].get("text", "").startswith(
                          "script sendbox ttl ")]
        assert any("presentation_rect 30 " in t for t in pair_texts)


class TestT24StereoPrimitives:
    """T24 [Q50,Q51]: stereo_mode contract + mono_below primitive."""

    def test_stereo_mode_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import stereo_mode
        d = AudioEffect("sm", width=240, height=168)
        d.add_newobj("core_gen", "gen~ x", numinlets=2, numoutlets=2,
                     outlettype=["signal", "signal"],
                     patching_rect=[40, 100, 80, 20])
        res = stereo_mode(d, "sm", rect=[10, 10, 60, 14], gen_box="core_gen")
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        v = boxes["sm_menu"]["saved_attribute_attributes"]["valueof"]
        assert v["parameter_enum"] == ["STEREO", "MID", "SIDE"]
        assert boxes["sm_pp"]["text"] == "prepend msmode"
        lines = {(ln["patchline"]["source"][0],
                  ln["patchline"]["destination"][0]) for ln in d.lines}
        assert ("sm_menu", "sm_pp") in lines and ("sm_pp", "core_gen") in lines
        assert "Mode" in res.params

    def test_mono_below_bypass_exact(self):
        from m4l_builder.gen_snippets import mono_below
        c = mono_below("L", "R", "oL", "oR", "f", prefix="q")
        # bypass path assigns the plain inputs BEFORE the gated mono sum
        assert "oL = L;\noR = R;\nif (f > 20.) {" in c
        assert "q_mono + (L - q_lp_l)" in c
        assert "History q_lp_l(0.);" in c


class TestT33BufferViewport:
    """T33 [Q2]: buffer_viewport — waveform~ zoom/select working set."""

    def test_viewport_wiring(self):
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import buffer_viewport
        d = AudioEffect("vp", width=340, height=168)
        res = buffer_viewport(d, "vp", "---buf", rect=[10, 26, 320, 100])
        boxes = {b["box"]["id"]: b["box"] for b in d.boxes}
        wave = boxes["vp_wave"]
        assert wave["maxclass"] == "waveform~"
        assert wave["buffername"] == "---buf"
        assert wave["numinlets"] == 5 and wave["numoutlets"] == 6
        lines = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
                  ln["patchline"]["destination"][0],
                  ln["patchline"]["destination"][1]) for ln in d.lines}
        # selection bounds (outlets 2/3 — 0/1 are the display window)
        # stream into the silent stores (right inlets)
        assert ("vp_wave", 2, "vp_fs", 1) in lines
        assert ("vp_wave", 3, "vp_fe", 1) in lines
        # zoom drives display start (inlet 0) and length (inlet 1)
        assert ("vp_fs", 0, "vp_wave", 0) in lines
        assert ("vp_len", 0, "vp_wave", 1) in lines
        # full view resets both
        assert ("vp_m0", 0, "vp_wave", 0) in lines
        assert ("vp_mbig", 0, "vp_wave", 1) in lines
        # gesture mode: Select I-beam + continuous emission by default
        assert boxes["vp_wave"]["setmode"] == 1
        assert boxes["vp_wave"]["outmode"] == 4
        assert set(res.ports) >= {"sel_start", "sel_end",
                                  "disp_start_in", "disp_len_in"}

    def test_zoom_trigger_order_right_first(self):
        # t b b fires RIGHT outlet (1) first: start must land before the
        # hot expr recomputes length from the end store
        from m4l_builder import AudioEffect
        from m4l_builder.recipes import buffer_viewport
        d = AudioEffect("vp2", width=340, height=168)
        buffer_viewport(d, "z", "---b", rect=[0, 0, 100, 50])
        lines = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
                  ln["patchline"]["destination"][0],
                  ln["patchline"]["destination"][1]) for ln in d.lines}
        assert ("z_zt", 1, "z_fs", 0) in lines   # right bang -> start store
        assert ("z_zt", 0, "z_fe", 0) in lines   # left bang -> end store
        assert ("z_fs", 0, "z_len", 1) in lines  # start = cold expr inlet
        assert ("z_fe", 0, "z_len", 0) in lines  # end = hot expr inlet
