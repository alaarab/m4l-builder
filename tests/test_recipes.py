"""Tests for pre-wired DSP combo recipes."""

from m4l_builder import AudioEffect
from m4l_builder.recipes import (
    gain_controlled_stage,
    dry_wet_stage,
    tempo_synced_delay,
    midi_note_gate,
    convolver_controlled_stage,
    sidechain_compressor_recipe,
    lfo_matrix_distribute,
    spectral_gate_stage,
    arpeggio_quantized_stage,
    grain_playback_controlled,
    poly_midi_gate,
    transport_sync_lfo_recipe,
    midi_learn_macro_assignment,
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
