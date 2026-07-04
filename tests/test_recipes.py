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
# single-column value rows -> default panel_width = 90
_CW = 90


def _sidebar_device(mini=420):
    """A device with one pre-existing on-canvas control + the full-bleed bg."""
    device = AudioEffect("test", width=mini, height=168)
    device.add_panel("surf_bg", [0, 0, mini, 168], bgcolor=[0.1, 0.1, 0.1, 1.0])
    device.add_dial("rate_map", "Depth", [40, 20, 41, 35])   # main content
    return device


class TestSettingsSidebar:
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
