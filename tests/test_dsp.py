"""Tests for DSP building blocks in dsp.py."""

import pytest

from m4l_builder.dsp import (
    stereo_io,
    gain_stage,
    dry_wet_mix,
    ms_encode_decode,
    dc_block,
    saturation,
    selector,
    highpass_filter,
    lowpass_filter,
    onepole_filter,
    signal_divide,
    tilt_eq,
    crossover_3band,
    envelope_follower,
    delay_line,
    lfo,
    comb_resonator,
    feedback_delay,
    tremolo,
    param_smooth,
    bandpass_filter,
    notch_filter,
    highshelf_filter,
    lowshelf_filter,
    compressor,
    limiter,
    noise_source,
    tempo_sync,
    live_remote,
    live_param_signal,
    adsr_envelope,
    peaking_eq,
    allpass_filter,
    gate_expander,
    sidechain_detect,
    sample_and_hold,
    multiband_compressor,
    reverb_network,
    notein,
    noteout,
    ctlin,
    ctlout,
    velocity_curve,
    transpose,
    midi_thru,
    wavetable_osc,
    buffer_load,
    arpeggiator,
    chord,
    pitch_quantize,
    lookahead_envelope_follower,
    fdn_reverb,
    spectral_gate,
    spectral_gate_subpatcher,
    vocoder,
    mc_expand,
    mc_collapse,
    note_expression_decode,
    transport_lfo,
    pitchbend_in,
    modwheel_in,
    aftertouch_in,
    xfade_matrix,
    midi_learn_chain,
    convolver,
    program_change_in,
    bank_select_in,
    sample_and_hold_triggered,
    bitcrusher,
    poly_voices,
    spectral_crossover,
    spectral_crossover_subpatcher,
    grain_cloud,
    auto_gain,
    midi_clock_out,
    macromap,
    stft_phase_vocoder,
    phase_vocoder_subpatcher,
    spectrum_band_extract,
    morphing_lfo,
    midi_clock_in,
    sidechain_routing,
    random_walk,
    matrix_mixer,
    cv_recorder,
    quantize_time,
    macro_modulation_matrix,
    analog_oscillator_bank,
    lfsr_generator,
    cv_smooth_lag,
)


# -- helpers --

def _box_texts(boxes):
    """Extract the 'text' field from each box dict."""
    return [b["box"]["text"] for b in boxes]


def _box_ids(boxes):
    """Extract the 'id' field from each box dict."""
    return [b["box"]["id"] for b in boxes]


def _find_box(boxes, obj_id):
    """Find a box by its ID."""
    for b in boxes:
        if b["box"]["id"] == obj_id:
            return b["box"]
    raise KeyError(f"No box with id {obj_id!r}")


class TestStereoIO:
    """Test stereo_io() creates plugin~/plugout~ pair."""

    def test_returns_2_boxes_0_lines(self):
        boxes, lines = stereo_io()
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_plugin_object(self):
        boxes, _ = stereo_io()
        plugin = boxes[0]["box"]
        assert plugin["text"] == "plugin~"
        assert plugin["numinlets"] == 1
        assert plugin["numoutlets"] == 2
        assert plugin["outlettype"] == ["signal", "signal"]

    def test_plugout_object(self):
        boxes, _ = stereo_io()
        plugout = boxes[1]["box"]
        assert plugout["text"] == "plugout~"
        assert plugout["numinlets"] == 2
        assert plugout["numoutlets"] == 0

    def test_default_ids(self):
        boxes, _ = stereo_io()
        assert boxes[0]["box"]["id"] == "obj-plugin"
        assert boxes[1]["box"]["id"] == "obj-plugout"

    def test_custom_ids(self):
        boxes, _ = stereo_io(plugin_id="my-in", plugout_id="my-out")
        assert boxes[0]["box"]["id"] == "my-in"
        assert boxes[1]["box"]["id"] == "my-out"

    def test_default_rects(self):
        boxes, _ = stereo_io()
        assert boxes[0]["box"]["patching_rect"] == [30, 30, 60, 20]
        assert boxes[1]["box"]["patching_rect"] == [30, 200, 60, 20]

    def test_custom_rects(self):
        r1 = [10, 10, 80, 25]
        r2 = [10, 300, 80, 25]
        boxes, _ = stereo_io(plugin_rect=r1, plugout_rect=r2)
        assert boxes[0]["box"]["patching_rect"] == r1
        assert boxes[1]["box"]["patching_rect"] == r2


class TestGainStage:
    """Test gain_stage() creates stereo *~ pair."""

    def test_returns_2_boxes_0_lines(self):
        boxes, lines = gain_stage("gain")
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_both_are_multiply_signal(self):
        boxes, _ = gain_stage("gain")
        for b in boxes:
            assert b["box"]["text"] == "*~ 1."

    def test_each_has_2_inlets_1_outlet(self):
        boxes, _ = gain_stage("gain")
        for b in boxes:
            assert b["box"]["numinlets"] == 2
            assert b["box"]["numoutlets"] == 1
            assert b["box"]["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = gain_stage("mygain")
        ids = _box_ids(boxes)
        assert "mygain_l" in ids
        assert "mygain_r" in ids

    def test_custom_rects(self):
        r_l = [0, 0, 50, 25]
        r_r = [100, 0, 50, 25]
        boxes, _ = gain_stage("g", patching_rect_l=r_l, patching_rect_r=r_r)
        assert _find_box(boxes, "g_l")["patching_rect"] == r_l
        assert _find_box(boxes, "g_r")["patching_rect"] == r_r


class TestDryWetMix:
    """Test dry_wet_mix() creates correct crossfade network."""

    def _make(self):
        return dry_wet_mix(
            "mix",
            wet_source_l=("wet_l", 0),
            wet_source_r=("wet_r", 0),
            dry_source_l=("dry_l", 0),
            dry_source_r=("dry_r", 0),
        )

    def test_returns_8_boxes(self):
        boxes, _ = self._make()
        assert len(boxes) == 8

    def test_no_sig_objects(self):
        """sig~ starts at 0.0 on load and overrides *~ args — must use t f f f instead."""
        boxes, _ = self._make()
        for b in boxes:
            assert "sig~" not in b["box"]["text"], (
                f"Found sig~ in {b['box']['id']!r} — must use 't f f f' instead"
            )

    def test_mix_entry_is_trigger(self):
        boxes, _ = self._make()
        mix_in = _find_box(boxes, "mix_mix_in")
        assert mix_in["text"] == "t f f f"
        assert mix_in["numinlets"] == 1
        assert mix_in["numoutlets"] == 3

    def test_inverter_is_bang_minus(self):
        boxes, _ = self._make()
        inv = _find_box(boxes, "mix_inv")
        assert inv["text"] == "!-~ 1."
        assert inv["numoutlets"] == 1

    def test_wet_multipliers_exist(self):
        boxes, _ = self._make()
        wet_l = _find_box(boxes, "mix_wet_l")
        wet_r = _find_box(boxes, "mix_wet_r")
        assert wet_l["text"] == "*~ 0."
        assert wet_r["text"] == "*~ 0."

    def test_dry_multipliers_exist(self):
        boxes, _ = self._make()
        dry_l = _find_box(boxes, "mix_dry_l")
        dry_r = _find_box(boxes, "mix_dry_r")
        assert dry_l["text"] == "*~ 1."
        assert dry_r["text"] == "*~ 1."

    def test_sum_outputs_exist(self):
        boxes, _ = self._make()
        out_l = _find_box(boxes, "mix_out_l")
        out_r = _find_box(boxes, "mix_out_r")
        assert out_l["text"] == "+~"
        assert out_r["text"] == "+~"

    def test_line_count(self):
        _, lines = self._make()
        # 3 from trigger + 2 from inv + 2 wet sources + 2 dry sources + 4 sums = 13
        assert len(lines) == 13

    def test_trigger_fans_to_wet_and_inv(self):
        _, lines = self._make()
        sources = {}
        for line in lines:
            src = (line["patchline"]["source"][0], line["patchline"]["source"][1])
            dst = (line["patchline"]["destination"][0], line["patchline"]["destination"][1])
            sources.setdefault(src, []).append(dst)

        # Trigger outlet 0 -> wet_l inlet 1
        assert ("mix_wet_l", 1) in sources[("mix_mix_in", 0)]
        # Trigger outlet 1 -> wet_r inlet 1
        assert ("mix_wet_r", 1) in sources[("mix_mix_in", 1)]
        # Trigger outlet 2 -> inv inlet 0
        assert ("mix_inv", 0) in sources[("mix_mix_in", 2)]

    def test_inv_fans_to_dry_multipliers(self):
        _, lines = self._make()
        inv_dests = [
            (l["patchline"]["destination"][0], l["patchline"]["destination"][1])
            for l in lines
            if l["patchline"]["source"] == ["mix_inv", 0]
        ]
        assert ("mix_dry_l", 1) in inv_dests
        assert ("mix_dry_r", 1) in inv_dests

    def test_wet_source_connections(self):
        _, lines = self._make()
        # wet_l source -> mix_wet_l inlet 0
        found_l = any(
            l["patchline"]["source"] == ["wet_l", 0]
            and l["patchline"]["destination"] == ["mix_wet_l", 0]
            for l in lines
        )
        found_r = any(
            l["patchline"]["source"] == ["wet_r", 0]
            and l["patchline"]["destination"] == ["mix_wet_r", 0]
            for l in lines
        )
        assert found_l, "Missing wet_l -> mix_wet_l connection"
        assert found_r, "Missing wet_r -> mix_wet_r connection"

    def test_dry_source_connections(self):
        _, lines = self._make()
        found_l = any(
            l["patchline"]["source"] == ["dry_l", 0]
            and l["patchline"]["destination"] == ["mix_dry_l", 0]
            for l in lines
        )
        found_r = any(
            l["patchline"]["source"] == ["dry_r", 0]
            and l["patchline"]["destination"] == ["mix_dry_r", 0]
            for l in lines
        )
        assert found_l, "Missing dry_l -> mix_dry_l connection"
        assert found_r, "Missing dry_r -> mix_dry_r connection"

    def test_sum_wiring(self):
        _, lines = self._make()
        # wet_l -> out_l inlet 0, dry_l -> out_l inlet 1
        assert any(
            l["patchline"]["source"] == ["mix_wet_l", 0]
            and l["patchline"]["destination"] == ["mix_out_l", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["mix_dry_l", 0]
            and l["patchline"]["destination"] == ["mix_out_l", 1]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["mix_wet_r", 0]
            and l["patchline"]["destination"] == ["mix_out_r", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["mix_dry_r", 0]
            and l["patchline"]["destination"] == ["mix_out_r", 1]
            for l in lines
        )


class TestMSEncodeDecode:
    """Test ms_encode_decode() creates encoder/decoder stages."""

    def test_returns_6_boxes_2_lines(self):
        boxes, lines = ms_encode_decode("ms")
        assert len(boxes) == 6
        assert len(lines) == 2

    def test_encoder_sum_and_diff(self):
        boxes, _ = ms_encode_decode("ms")
        enc_add = _find_box(boxes, "ms_enc_add")
        enc_sub = _find_box(boxes, "ms_enc_sub")
        assert enc_add["text"] == "+~"
        assert enc_sub["text"] == "-~"

    def test_encoder_scalers(self):
        boxes, _ = ms_encode_decode("ms")
        enc_mid = _find_box(boxes, "ms_enc_mid")
        enc_side = _find_box(boxes, "ms_enc_side")
        assert enc_mid["text"] == "*~ 0.5"
        assert enc_side["text"] == "*~ 0.5"

    def test_decoder_sum_and_diff(self):
        boxes, _ = ms_encode_decode("ms")
        dec_add = _find_box(boxes, "ms_dec_add")
        dec_sub = _find_box(boxes, "ms_dec_sub")
        assert dec_add["text"] == "+~"
        assert dec_sub["text"] == "-~"

    def test_internal_lines_connect_encoder_to_scalers(self):
        _, lines = ms_encode_decode("ms")
        # enc_add -> enc_mid
        assert any(
            l["patchline"]["source"] == ["ms_enc_add", 0]
            and l["patchline"]["destination"] == ["ms_enc_mid", 0]
            for l in lines
        )
        # enc_sub -> enc_side
        assert any(
            l["patchline"]["source"] == ["ms_enc_sub", 0]
            and l["patchline"]["destination"] == ["ms_enc_side", 0]
            for l in lines
        )

    def test_all_boxes_have_signal_outlets(self):
        boxes, _ = ms_encode_decode("ms")
        for b in boxes:
            assert b["box"]["outlettype"] == ["signal"]


class TestDCBlock:
    """Test dc_block() creates biquad~ based DC blocker."""

    def test_returns_2_boxes_0_lines(self):
        boxes, lines = dc_block("dc")
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_uses_biquad_not_dcblock(self):
        """dcblock~ doesn't exist in Max 8 — must use biquad~ with HP coefficients."""
        boxes, _ = dc_block("dc")
        for b in boxes:
            assert "biquad~" in b["box"]["text"]
            assert "dcblock~" not in b["box"]["text"]

    def test_coefficients_in_text(self):
        boxes, _ = dc_block("dc")
        for b in boxes:
            assert b["box"]["text"] == "biquad~ 1. -1. 0. -0.9997 0."

    def test_6_inlets_1_outlet(self):
        """biquad~ has signal + 5 coefficient inlets."""
        boxes, _ = dc_block("dc")
        for b in boxes:
            assert b["box"]["numinlets"] == 6
            assert b["box"]["numoutlets"] == 1
            assert b["box"]["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = dc_block("mydc")
        ids = _box_ids(boxes)
        assert "mydc_l" in ids
        assert "mydc_r" in ids


class TestSaturation:
    """Test saturation() for all four modes."""

    def test_tanh_mode(self):
        boxes, lines = saturation("sat", "tanh")
        assert len(boxes) == 2
        assert len(lines) == 0
        for b in boxes:
            assert b["box"]["text"] == "tanh~"
            assert b["box"]["numinlets"] == 1
            assert b["box"]["numoutlets"] == 1

    def test_overdrive_mode(self):
        boxes, _ = saturation("sat", "overdrive")
        for b in boxes:
            assert b["box"]["text"] == "overdrive~"
            assert b["box"]["numinlets"] == 1
            assert b["box"]["numoutlets"] == 1

    def test_clip_mode(self):
        boxes, _ = saturation("sat", "clip")
        for b in boxes:
            assert b["box"]["text"] == "clip~ -1. 1."
            assert b["box"]["numinlets"] == 3
            assert b["box"]["numoutlets"] == 1

    def test_degrade_mode(self):
        boxes, _ = saturation("sat", "degrade")
        for b in boxes:
            assert b["box"]["text"] == "degrade~"
            assert b["box"]["numinlets"] == 3
            assert b["box"]["numoutlets"] == 1

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown saturation mode"):
            saturation("sat", "fuzz")

    def test_ids_use_prefix(self):
        boxes, _ = saturation("dist", "tanh")
        ids = _box_ids(boxes)
        assert "dist_l" in ids
        assert "dist_r" in ids

    def test_all_modes_return_signal_outlets(self):
        for mode in ("tanh", "overdrive", "clip", "degrade"):
            boxes, _ = saturation("s", mode)
            for b in boxes:
                assert b["box"]["outlettype"] == ["signal"]


class TestSelector:
    """Test selector() creates selector~ with initial arg."""

    def test_returns_1_box_0_lines(self):
        boxes, lines = selector("sel", 3)
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_text_includes_initial_arg(self):
        """selector~ defaults to input 0 (silence) without an initial arg."""
        boxes, _ = selector("sel", 4, initial=2)
        assert boxes[0]["box"]["text"] == "selector~ 4 2"

    def test_default_initial_is_1(self):
        boxes, _ = selector("sel", 3)
        assert boxes[0]["box"]["text"] == "selector~ 3 1"

    def test_numinlets_is_n_plus_1(self):
        """selector~ N has N+1 inlets: int selector + N signal inputs."""
        boxes, _ = selector("sel", 5)
        assert boxes[0]["box"]["numinlets"] == 6

    def test_numoutlets_is_1(self):
        boxes, _ = selector("sel", 3)
        assert boxes[0]["box"]["numoutlets"] == 1
        assert boxes[0]["box"]["outlettype"] == ["signal"]

    def test_initial_0_means_silence(self):
        boxes, _ = selector("sel", 2, initial=0)
        assert boxes[0]["box"]["text"] == "selector~ 2 0"


class TestHighpassFilter:
    """Test highpass_filter() uses svf~ outlet 1 (HP)."""

    def test_returns_4_boxes_2_lines(self):
        boxes, lines = highpass_filter("hp")
        assert len(boxes) == 4
        assert len(lines) == 2

    def test_svf_objects(self):
        boxes, _ = highpass_filter("hp")
        svf_l = _find_box(boxes, "hp_l")
        svf_r = _find_box(boxes, "hp_r")
        assert svf_l["text"] == "svf~"
        assert svf_r["text"] == "svf~"
        assert svf_l["numinlets"] == 3
        assert svf_l["numoutlets"] == 4

    def test_passthrough_objects(self):
        boxes, _ = highpass_filter("hp")
        out_l = _find_box(boxes, "hp_out_l")
        out_r = _find_box(boxes, "hp_out_r")
        assert out_l["text"] == "*~ 1."
        assert out_r["text"] == "*~ 1."

    def test_wires_outlet_1_hp(self):
        """Must wire svf~ outlet 1 (HP), NOT outlet 0 (LP)."""
        _, lines = highpass_filter("hp")
        # hp_l outlet 1 -> hp_out_l inlet 0
        assert any(
            l["patchline"]["source"] == ["hp_l", 1]
            and l["patchline"]["destination"] == ["hp_out_l", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["hp_r", 1]
            and l["patchline"]["destination"] == ["hp_out_r", 0]
            for l in lines
        )

    def test_no_lp_wiring(self):
        """Must NOT accidentally wire outlet 0 (LP)."""
        _, lines = highpass_filter("hp")
        lp_wires = [
            l for l in lines
            if l["patchline"]["source"][1] == 0
            and l["patchline"]["source"][0] in ("hp_l", "hp_r")
        ]
        assert len(lp_wires) == 0


class TestLowpassFilter:
    """Test lowpass_filter() uses svf~ outlet 0 (LP)."""

    def test_returns_4_boxes_2_lines(self):
        boxes, lines = lowpass_filter("lp")
        assert len(boxes) == 4
        assert len(lines) == 2

    def test_svf_objects(self):
        boxes, _ = lowpass_filter("lp")
        svf_l = _find_box(boxes, "lp_l")
        svf_r = _find_box(boxes, "lp_r")
        assert svf_l["text"] == "svf~"
        assert svf_r["text"] == "svf~"
        assert svf_l["numinlets"] == 3
        assert svf_l["numoutlets"] == 4

    def test_passthrough_objects(self):
        boxes, _ = lowpass_filter("lp")
        out_l = _find_box(boxes, "lp_out_l")
        out_r = _find_box(boxes, "lp_out_r")
        assert out_l["text"] == "*~ 1."
        assert out_r["text"] == "*~ 1."

    def test_wires_outlet_0_lp(self):
        """Must wire svf~ outlet 0 (LP), NOT outlet 1 (HP)."""
        _, lines = lowpass_filter("lp")
        assert any(
            l["patchline"]["source"] == ["lp_l", 0]
            and l["patchline"]["destination"] == ["lp_out_l", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["lp_r", 0]
            and l["patchline"]["destination"] == ["lp_out_r", 0]
            for l in lines
        )

    def test_no_hp_wiring(self):
        """Must NOT accidentally wire outlet 1 (HP)."""
        _, lines = lowpass_filter("lp")
        hp_wires = [
            l for l in lines
            if l["patchline"]["source"][1] == 1
            and l["patchline"]["source"][0] in ("lp_l", "lp_r")
        ]
        assert len(hp_wires) == 0


class TestOnepoleFilter:
    """Test onepole_filter() creates stereo onepole~ pair."""

    def test_returns_2_boxes_0_lines(self):
        boxes, lines = onepole_filter("op")
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_default_freq(self):
        boxes, _ = onepole_filter("op")
        for b in boxes:
            assert b["box"]["text"] == "onepole~ 1000.0"

    def test_custom_freq(self):
        boxes, _ = onepole_filter("op", freq=500.0)
        for b in boxes:
            assert b["box"]["text"] == "onepole~ 500.0"

    def test_2_inlets_1_outlet(self):
        boxes, _ = onepole_filter("op")
        for b in boxes:
            assert b["box"]["numinlets"] == 2
            assert b["box"]["numoutlets"] == 1
            assert b["box"]["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = onepole_filter("filt")
        ids = _box_ids(boxes)
        assert "filt_l" in ids
        assert "filt_r" in ids


class TestSignalDivide:
    """Test signal_divide() uses !/~ NOT /~."""

    def test_returns_2_boxes_1_line(self):
        boxes, lines = signal_divide("div")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_uses_inverse_divide_not_divide(self):
        """/~ doesn't work for signal/signal in Max — uses !/~ 1. for reciprocal then *~."""
        boxes, _ = signal_divide("div")
        texts = _box_texts(boxes)
        assert "!/~ 1." in texts
        assert "/~" not in [t for t in texts if not t.startswith("!")]

    def test_recip_object(self):
        boxes, _ = signal_divide("div")
        recip = _find_box(boxes, "div_recip")
        assert recip["text"] == "!/~ 1."
        assert recip["numinlets"] == 2
        assert recip["numoutlets"] == 1

    def test_mul_object(self):
        boxes, _ = signal_divide("div")
        mul = _find_box(boxes, "div_mul")
        assert mul["text"] == "*~"
        assert mul["numinlets"] == 2
        assert mul["numoutlets"] == 1

    def test_internal_line_recip_to_mul(self):
        _, lines = signal_divide("div")
        assert lines[0]["patchline"]["source"] == ["div_recip", 0]
        assert lines[0]["patchline"]["destination"] == ["div_mul", 1]


class TestTiltEQ:
    """Test tilt_eq() creates per-channel crossover EQ."""

    def test_returns_10_boxes(self):
        """5 per channel: onepole~, -~, *~ low, *~ high, +~ sum."""
        boxes, _ = tilt_eq("tilt")
        assert len(boxes) == 10

    def test_returns_10_lines(self):
        """5 per channel: lp->lo, lp->hp_sub, hp->hi, lo->out, hi->out."""
        _, lines = tilt_eq("tilt")
        assert len(lines) == 10

    def test_left_channel_objects(self):
        boxes, _ = tilt_eq("tilt")
        lp = _find_box(boxes, "tilt_lp_l")
        hp = _find_box(boxes, "tilt_hp_l")
        lo = _find_box(boxes, "tilt_lo_l")
        hi = _find_box(boxes, "tilt_hi_l")
        out = _find_box(boxes, "tilt_out_l")
        assert "onepole~" in lp["text"]
        assert hp["text"] == "-~"
        assert lo["text"] == "*~ 1."
        assert hi["text"] == "*~ 1."
        assert out["text"] == "+~"

    def test_right_channel_objects(self):
        boxes, _ = tilt_eq("tilt")
        lp = _find_box(boxes, "tilt_lp_r")
        hp = _find_box(boxes, "tilt_hp_r")
        lo = _find_box(boxes, "tilt_lo_r")
        hi = _find_box(boxes, "tilt_hi_r")
        out = _find_box(boxes, "tilt_out_r")
        assert "onepole~" in lp["text"]
        assert hp["text"] == "-~"
        assert lo["text"] == "*~ 1."
        assert hi["text"] == "*~ 1."
        assert out["text"] == "+~"

    def test_default_freq(self):
        boxes, _ = tilt_eq("tilt")
        lp_l = _find_box(boxes, "tilt_lp_l")
        assert lp_l["text"] == "onepole~ 1000.0"

    def test_custom_freq(self):
        boxes, _ = tilt_eq("tilt", freq=2000.0)
        lp_l = _find_box(boxes, "tilt_lp_l")
        assert lp_l["text"] == "onepole~ 2000.0"

    def test_internal_wiring_left(self):
        _, lines = tilt_eq("tilt")
        # LP -> low gain
        assert any(
            l["patchline"]["source"] == ["tilt_lp_l", 0]
            and l["patchline"]["destination"] == ["tilt_lo_l", 0]
            for l in lines
        )
        # LP -> subtractor inlet 1
        assert any(
            l["patchline"]["source"] == ["tilt_lp_l", 0]
            and l["patchline"]["destination"] == ["tilt_hp_l", 1]
            for l in lines
        )
        # HP -> high gain
        assert any(
            l["patchline"]["source"] == ["tilt_hp_l", 0]
            and l["patchline"]["destination"] == ["tilt_hi_l", 0]
            for l in lines
        )
        # Gains -> sum
        assert any(
            l["patchline"]["source"] == ["tilt_lo_l", 0]
            and l["patchline"]["destination"] == ["tilt_out_l", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["tilt_hi_l", 0]
            and l["patchline"]["destination"] == ["tilt_out_l", 1]
            for l in lines
        )

    def test_internal_wiring_right(self):
        _, lines = tilt_eq("tilt")
        assert any(
            l["patchline"]["source"] == ["tilt_lp_r", 0]
            and l["patchline"]["destination"] == ["tilt_lo_r", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["tilt_lp_r", 0]
            and l["patchline"]["destination"] == ["tilt_hp_r", 1]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["tilt_hp_r", 0]
            and l["patchline"]["destination"] == ["tilt_hi_r", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["tilt_lo_r", 0]
            and l["patchline"]["destination"] == ["tilt_out_r", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["tilt_hi_r", 0]
            and l["patchline"]["destination"] == ["tilt_out_r", 1]
            for l in lines
        )


class TestCrossover3Band:
    """Test crossover_3band() creates two cross~ objects with summing chain."""

    def test_returns_4_boxes(self):
        """2 cross~ + 2 +~ summing objects."""
        boxes, _ = crossover_3band("xo")
        assert len(boxes) == 4

    def test_has_two_cross_objects(self):
        boxes, _ = crossover_3band("xo")
        cross_boxes = [b for b in boxes if b["box"]["text"] == "cross~"]
        assert len(cross_boxes) == 2

    def test_cross_ids(self):
        boxes, _ = crossover_3band("xo")
        xover_lo = _find_box(boxes, "xo_xover_lo")
        xover_hi = _find_box(boxes, "xo_xover_hi")
        assert xover_lo["text"] == "cross~"
        assert xover_hi["text"] == "cross~"

    def test_cross_inlets_and_outlets(self):
        boxes, _ = crossover_3band("xo")
        xover_lo = _find_box(boxes, "xo_xover_lo")
        assert xover_lo["numinlets"] == 2
        assert xover_lo["numoutlets"] == 2
        assert xover_lo["outlettype"] == ["signal", "signal"]

    def test_has_two_sum_objects(self):
        """Two +~ objects for recombining bands."""
        boxes, _ = crossover_3band("xo")
        sum_boxes = [b for b in boxes if b["box"]["text"] == "+~"]
        assert len(sum_boxes) == 2

    def test_sum_ids_exist(self):
        boxes, _ = crossover_3band("xo")
        sum_lo_mid = _find_box(boxes, "xo_sum_lo_mid")
        sum_final = _find_box(boxes, "xo_sum")
        assert sum_lo_mid["text"] == "+~"
        assert sum_final["text"] == "+~"

    def test_hp_of_first_cross_feeds_second(self):
        """xover_lo outlet 1 (HP) must wire to xover_hi inlet 0."""
        _, lines = crossover_3band("xo")
        assert any(
            l["patchline"]["source"] == ["xo_xover_lo", 1]
            and l["patchline"]["destination"] == ["xo_xover_hi", 0]
            for l in lines
        )

    def test_low_band_to_sum_lo_mid(self):
        """xover_lo outlet 0 (LP=low band) -> sum_lo_mid inlet 0."""
        _, lines = crossover_3band("xo")
        assert any(
            l["patchline"]["source"] == ["xo_xover_lo", 0]
            and l["patchline"]["destination"] == ["xo_sum_lo_mid", 0]
            for l in lines
        )

    def test_mid_band_to_sum_lo_mid(self):
        """xover_hi outlet 0 (LP=mid band) -> sum_lo_mid inlet 1."""
        _, lines = crossover_3band("xo")
        assert any(
            l["patchline"]["source"] == ["xo_xover_hi", 0]
            and l["patchline"]["destination"] == ["xo_sum_lo_mid", 1]
            for l in lines
        )

    def test_sum_lo_mid_to_final_sum(self):
        _, lines = crossover_3band("xo")
        assert any(
            l["patchline"]["source"] == ["xo_sum_lo_mid", 0]
            and l["patchline"]["destination"] == ["xo_sum", 0]
            for l in lines
        )

    def test_high_band_to_final_sum(self):
        """xover_hi outlet 1 (HP=high band) -> sum inlet 1."""
        _, lines = crossover_3band("xo")
        assert any(
            l["patchline"]["source"] == ["xo_xover_hi", 1]
            and l["patchline"]["destination"] == ["xo_sum", 1]
            for l in lines
        )

    def test_no_sig_in_output(self):
        boxes, _ = crossover_3band("xo")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = crossover_3band("xo")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]

    def test_line_count(self):
        _, lines = crossover_3band("xo")
        assert len(lines) == 5


class TestEnvelopeFollower:
    """Test envelope_follower() creates abs~ -> slide~ chain with runtime samplerate~."""

    def test_returns_6_boxes_6_lines(self):
        boxes, lines = envelope_follower("env")
        assert len(boxes) == 6
        assert len(lines) == 6

    def test_has_abs_object(self):
        boxes, _ = envelope_follower("env")
        abs_box = _find_box(boxes, "env_abs")
        assert abs_box["text"] == "abs~"
        assert abs_box["numinlets"] == 1
        assert abs_box["numoutlets"] == 1
        assert abs_box["outlettype"] == ["signal"]

    def test_has_slide_object(self):
        boxes, _ = envelope_follower("env")
        slide_box = _find_box(boxes, "env_slide")
        assert slide_box["text"].startswith("slide~")

    def test_slide_has_sample_based_args_default(self):
        """Default attack=10ms, release=100ms -> 441.0 and 4410.0 samples at 44100sr."""
        boxes, _ = envelope_follower("env")
        slide_box = _find_box(boxes, "env_slide")
        assert "441.0" in slide_box["text"]
        assert "4410.0" in slide_box["text"]

    def test_slide_args_custom_times(self):
        """Custom attack=5ms, release=200ms -> 220.5 and 8820.0 samples."""
        boxes, _ = envelope_follower("env", attack_ms=5, release_ms=200)
        slide_box = _find_box(boxes, "env_slide")
        assert "220.5" in slide_box["text"]
        assert "8820.0" in slide_box["text"]

    def test_slide_numinlets(self):
        boxes, _ = envelope_follower("env")
        slide_box = _find_box(boxes, "env_slide")
        assert slide_box["numinlets"] == 3

    def test_abs_feeds_slide(self):
        _, lines = envelope_follower("env")
        assert any(
            l["patchline"]["source"] == ["env_abs", 0]
            and l["patchline"]["destination"] == ["env_slide", 0]
            for l in lines
        )

    def test_no_sig_in_output(self):
        boxes, _ = envelope_follower("env")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = envelope_follower("env")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]


class TestDelayLine:
    """Test delay_line() creates tapin~/tapout~ pair."""

    def test_returns_2_boxes_1_line(self):
        boxes, lines = delay_line("dl")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_tapin(self):
        boxes, _ = delay_line("dl")
        tapin = _find_box(boxes, "dl_tapin")
        assert tapin["text"].startswith("tapin~")
        assert tapin["numinlets"] == 1
        assert tapin["numoutlets"] == 1
        assert tapin["outlettype"] == ["tapconnect"]

    def test_has_tapout(self):
        boxes, _ = delay_line("dl")
        tapout = _find_box(boxes, "dl_tapout")
        assert tapout["text"].startswith("tapout~")
        assert tapout["numinlets"] == 1
        assert tapout["numoutlets"] == 1
        assert tapout["outlettype"] == ["signal"]

    def test_default_max_delay_in_tapin(self):
        boxes, _ = delay_line("dl")
        tapin = _find_box(boxes, "dl_tapin")
        assert "5000" in tapin["text"]

    def test_custom_max_delay_in_tapin(self):
        boxes, _ = delay_line("dl", max_delay_ms=2000)
        tapin = _find_box(boxes, "dl_tapin")
        assert "2000" in tapin["text"]

    def test_tapin_feeds_tapout(self):
        _, lines = delay_line("dl")
        assert any(
            l["patchline"]["source"] == ["dl_tapin", 0]
            and l["patchline"]["destination"] == ["dl_tapout", 0]
            for l in lines
        )

    def test_no_sig_in_output(self):
        boxes, _ = delay_line("dl")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = delay_line("dl")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]


class TestLFO:
    """Test lfo() for all three waveforms with correct unipolar scaling."""

    def test_sine_uses_cycle(self):
        boxes, _ = lfo("lfo", waveform="sine")
        osc = _find_box(boxes, "lfo_osc")
        assert osc["text"] == "cycle~"

    def test_saw_uses_phasor(self):
        boxes, _ = lfo("lfo", waveform="saw")
        osc = _find_box(boxes, "lfo_osc")
        assert osc["text"] == "phasor~"

    def test_square_uses_rect(self):
        boxes, _ = lfo("lfo", waveform="square")
        osc = _find_box(boxes, "lfo_osc")
        assert osc["text"] == "rect~"

    def test_sine_has_scale_and_offset(self):
        """cycle~ is bipolar: needs *~ 0.5 and +~ 0.5 to become unipolar."""
        boxes, _ = lfo("lfo", waveform="sine")
        scale = _find_box(boxes, "lfo_scale")
        offset = _find_box(boxes, "lfo_offset")
        assert scale["text"] == "*~ 0.5"
        assert offset["text"] == "+~ 0.5"

    def test_square_has_scale_and_offset(self):
        """rect~ is bipolar: needs *~ 0.5 and +~ 0.5 to become unipolar."""
        boxes, _ = lfo("lfo", waveform="square")
        scale = _find_box(boxes, "lfo_scale")
        offset = _find_box(boxes, "lfo_offset")
        assert scale["text"] == "*~ 0.5"
        assert offset["text"] == "+~ 0.5"

    def test_saw_no_scale_offset(self):
        """phasor~ is already 0-1: no scale/offset objects needed."""
        boxes, _ = lfo("lfo", waveform="saw")
        ids = _box_ids(boxes)
        assert "lfo_scale" not in ids
        assert "lfo_offset" not in ids

    def test_depth_object_always_present(self):
        for wf in ("sine", "saw", "square"):
            boxes, _ = lfo("lfo", waveform=wf)
            depth = _find_box(boxes, "lfo_depth")
            assert depth["text"] == "*~ 1."

    def test_sine_box_count(self):
        """cycle~ + *~ 0.5 + +~ 0.5 + *~ depth = 4 boxes."""
        boxes, _ = lfo("lfo", waveform="sine")
        assert len(boxes) == 4

    def test_saw_box_count(self):
        """phasor~ + *~ depth = 2 boxes."""
        boxes, _ = lfo("lfo", waveform="saw")
        assert len(boxes) == 2

    def test_square_box_count(self):
        """rect~ + *~ 0.5 + +~ 0.5 + *~ depth = 4 boxes."""
        boxes, _ = lfo("lfo", waveform="square")
        assert len(boxes) == 4

    def test_sine_unipolar_chain_wiring(self):
        """osc -> scale -> offset -> depth."""
        _, lines = lfo("lfo", waveform="sine")
        assert any(
            l["patchline"]["source"] == ["lfo_osc", 0]
            and l["patchline"]["destination"] == ["lfo_scale", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["lfo_scale", 0]
            and l["patchline"]["destination"] == ["lfo_offset", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["lfo_offset", 0]
            and l["patchline"]["destination"] == ["lfo_depth", 0]
            for l in lines
        )

    def test_saw_depth_wiring(self):
        """phasor~ output -> depth directly."""
        _, lines = lfo("lfo", waveform="saw")
        assert any(
            l["patchline"]["source"] == ["lfo_osc", 0]
            and l["patchline"]["destination"] == ["lfo_depth", 0]
            for l in lines
        )

    def test_unknown_waveform_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown waveform"):
            lfo("lfo", waveform="noise")

    def test_no_sig_in_output(self):
        for wf in ("sine", "saw", "square", "triangle"):
            boxes, _ = lfo("lfo", waveform=wf)
            for b in boxes:
                assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        for wf in ("sine", "saw", "square"):
            boxes, _ = lfo("lfo", waveform=wf)
            for b in boxes:
                assert "dcblock~" not in b["box"]["text"]


class TestCombResonator:
    """Test comb_resonator() creates N parallel comb~ voices with summing."""

    def test_default_4_voices(self):
        boxes, _ = comb_resonator("cr")
        comb_boxes = [b for b in boxes if b["box"]["text"] == "comb~"]
        assert len(comb_boxes) == 4

    def test_comb_ids_sequential(self):
        boxes, _ = comb_resonator("cr", num_voices=3)
        for i in range(3):
            comb = _find_box(boxes, f"cr_comb_{i}")
            assert comb["text"] == "comb~"

    def test_comb_has_5_inlets(self):
        """comb~ has 5 inlets: signal, delay_ms, a_gain, b_ff, c_fb."""
        boxes, _ = comb_resonator("cr")
        comb = _find_box(boxes, "cr_comb_0")
        assert comb["numinlets"] == 5
        assert comb["numoutlets"] == 1

    def test_sum_output_exists(self):
        boxes, _ = comb_resonator("cr")
        sum_box = _find_box(boxes, "cr_sum")
        assert sum_box is not None

    def test_2_voices_has_sum_chain(self):
        """2 voices: add_0 sums comb_0 + comb_1, sum is pass-through."""
        boxes, _ = comb_resonator("cr", num_voices=2)
        add = _find_box(boxes, "cr_add_0")
        assert add["text"] == "+~"

    def test_4_voices_has_3_adders(self):
        """4 voices: add_0 + add_1 + add_2 summing adders, plus sum pass-through."""
        boxes, _ = comb_resonator("cr", num_voices=4)
        sum_boxes = [b for b in boxes if b["box"]["text"] == "+~"]
        assert len(sum_boxes) == 3

    def test_1_voice_passthrough(self):
        """Single voice uses *~ 1. passthrough, no +~ adders."""
        boxes, _ = comb_resonator("cr", num_voices=1)
        add_boxes = [b for b in boxes if b["box"]["text"] == "+~"]
        assert len(add_boxes) == 0
        sum_box = _find_box(boxes, "cr_sum")
        assert sum_box["text"] == "*~ 1."

    def test_comb_0_feeds_add_0(self):
        _, lines = comb_resonator("cr", num_voices=4)
        assert any(
            l["patchline"]["source"] == ["cr_comb_0", 0]
            and l["patchline"]["destination"] == ["cr_add_0", 0]
            for l in lines
        )

    def test_comb_1_feeds_add_0(self):
        _, lines = comb_resonator("cr", num_voices=4)
        assert any(
            l["patchline"]["source"] == ["cr_comb_1", 0]
            and l["patchline"]["destination"] == ["cr_add_0", 1]
            for l in lines
        )

    def test_no_sig_in_output(self):
        boxes, _ = comb_resonator("cr")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = comb_resonator("cr")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]


class TestFeedbackDelay:
    """Test feedback_delay() creates delay with tanh~/onepole~ feedback path."""

    def test_returns_6_boxes(self):
        boxes, _ = feedback_delay("fd")
        assert len(boxes) == 6

    def test_has_tapin(self):
        boxes, _ = feedback_delay("fd")
        tapin = _find_box(boxes, "fd_tapin")
        assert tapin["text"].startswith("tapin~")

    def test_has_tapout(self):
        boxes, _ = feedback_delay("fd")
        tapout = _find_box(boxes, "fd_tapout")
        assert tapout["text"].startswith("tapout~")

    def test_has_tanh(self):
        boxes, _ = feedback_delay("fd")
        sat = _find_box(boxes, "fd_sat")
        assert sat["text"] == "tanh~"
        assert sat["numinlets"] == 1
        assert sat["numoutlets"] == 1

    def test_has_onepole(self):
        boxes, _ = feedback_delay("fd")
        lp = _find_box(boxes, "fd_lp")
        assert lp["text"].startswith("onepole~")
        assert lp["numinlets"] == 2

    def test_has_sum_input(self):
        boxes, _ = feedback_delay("fd")
        sum_box = _find_box(boxes, "fd_sum")
        assert sum_box["text"] == "+~"

    def test_has_feedback_amount(self):
        boxes, _ = feedback_delay("fd")
        fb = _find_box(boxes, "fd_fb")
        assert fb["text"].startswith("*~")

    def test_default_max_delay_in_tapin(self):
        boxes, _ = feedback_delay("fd")
        tapin = _find_box(boxes, "fd_tapin")
        assert "5000" in tapin["text"]

    def test_custom_max_delay_in_tapin(self):
        boxes, _ = feedback_delay("fd", max_delay_ms=1000)
        tapin = _find_box(boxes, "fd_tapin")
        assert "1000" in tapin["text"]

    def test_feedback_chain_sum_to_tapin(self):
        _, lines = feedback_delay("fd")
        assert any(
            l["patchline"]["source"] == ["fd_sum", 0]
            and l["patchline"]["destination"] == ["fd_tapin", 0]
            for l in lines
        )

    def test_feedback_chain_tapin_to_tapout(self):
        _, lines = feedback_delay("fd")
        assert any(
            l["patchline"]["source"] == ["fd_tapin", 0]
            and l["patchline"]["destination"] == ["fd_tapout", 0]
            for l in lines
        )

    def test_feedback_chain_tapout_to_sat(self):
        _, lines = feedback_delay("fd")
        assert any(
            l["patchline"]["source"] == ["fd_tapout", 0]
            and l["patchline"]["destination"] == ["fd_sat", 0]
            for l in lines
        )

    def test_feedback_chain_sat_to_lp(self):
        _, lines = feedback_delay("fd")
        assert any(
            l["patchline"]["source"] == ["fd_sat", 0]
            and l["patchline"]["destination"] == ["fd_lp", 0]
            for l in lines
        )

    def test_feedback_chain_lp_to_fb(self):
        _, lines = feedback_delay("fd")
        assert any(
            l["patchline"]["source"] == ["fd_lp", 0]
            and l["patchline"]["destination"] == ["fd_fb", 0]
            for l in lines
        )

    def test_feedback_chain_fb_returns_to_sum(self):
        _, lines = feedback_delay("fd")
        assert any(
            l["patchline"]["source"] == ["fd_fb", 0]
            and l["patchline"]["destination"] == ["fd_sum", 1]
            for l in lines
        )

    def test_no_sig_in_output(self):
        boxes, _ = feedback_delay("fd")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = feedback_delay("fd")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]


class TestTremolo:
    """Test tremolo() creates LFO modulating signal amplitude via *~."""

    def test_has_lfo_objects_sine(self):
        """tremolo includes LFO sub-chain: cycle~, *~ 0.5, +~ 0.5, *~ depth."""
        boxes, _ = tremolo("tr", waveform="sine")
        osc = _find_box(boxes, "tr_lfo_osc")
        assert osc["text"] == "cycle~"

    def test_has_lfo_objects_saw(self):
        boxes, _ = tremolo("tr", waveform="saw")
        osc = _find_box(boxes, "tr_lfo_osc")
        assert osc["text"] == "phasor~"

    def test_has_lfo_objects_square(self):
        boxes, _ = tremolo("tr", waveform="square")
        osc = _find_box(boxes, "tr_lfo_osc")
        assert osc["text"] == "rect~"

    def test_has_mod_multiplier(self):
        """*~ for amplitude modulation: signal * LFO."""
        boxes, _ = tremolo("tr")
        mod = _find_box(boxes, "tr_mod")
        assert mod["text"] == "*~"
        assert mod["numinlets"] == 2
        assert mod["numoutlets"] == 1

    def test_lfo_depth_feeds_mod_inlet_1(self):
        """LFO depth output -> mod inlet 1 (the LFO side of multiplication)."""
        _, lines = tremolo("tr")
        assert any(
            l["patchline"]["source"] == ["tr_lfo_depth", 0]
            and l["patchline"]["destination"] == ["tr_mod", 1]
            for l in lines
        )

    def test_sine_total_box_count(self):
        """LFO sine (4 boxes) + mod (1) = 5."""
        boxes, _ = tremolo("tr", waveform="sine")
        assert len(boxes) == 5

    def test_saw_total_box_count(self):
        """LFO saw (2 boxes) + mod (1) = 3."""
        boxes, _ = tremolo("tr", waveform="saw")
        assert len(boxes) == 3

    def test_unknown_waveform_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown waveform"):
            tremolo("tr", waveform="noise")

    def test_no_sig_in_output(self):
        boxes, _ = tremolo("tr")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = tremolo("tr")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]


class TestParamSmooth:
    """Test param_smooth() creates pack -> line~ smoother."""

    def test_returns_2_boxes_1_line(self):
        boxes, lines = param_smooth("sm")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_pack_with_default_ms(self):
        boxes, _ = param_smooth("sm")
        pack = _find_box(boxes, "sm_pack")
        assert pack["text"] == "pack f 20"

    def test_has_pack_with_custom_ms(self):
        boxes, _ = param_smooth("sm", smooth_ms=50)
        pack = _find_box(boxes, "sm_pack")
        assert pack["text"] == "pack f 50"

    def test_has_line_tilde(self):
        boxes, _ = param_smooth("sm")
        line = _find_box(boxes, "sm_line")
        assert line["text"] == "line~"
        assert line["outlettype"] == ["signal"]

    def test_pack_feeds_line(self):
        _, lines = param_smooth("sm")
        assert any(
            l["patchline"]["source"] == ["sm_pack", 0]
            and l["patchline"]["destination"] == ["sm_line", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = param_smooth("ctrl")
        ids = _box_ids(boxes)
        assert "ctrl_pack" in ids
        assert "ctrl_line" in ids


class TestBandpassFilter:
    """Test bandpass_filter() wires svf~ outlet 2 (BP)."""

    def test_returns_4_boxes_2_lines(self):
        boxes, lines = bandpass_filter("bp")
        assert len(boxes) == 4
        assert len(lines) == 2

    def test_has_svf_objects(self):
        boxes, _ = bandpass_filter("bp")
        for obj_id in ("bp_l", "bp_r"):
            box = _find_box(boxes, obj_id)
            assert box["text"] == "svf~"
            assert box["numinlets"] == 3
            assert box["numoutlets"] == 4

    def test_has_passthrough_objects(self):
        boxes, _ = bandpass_filter("bp")
        for obj_id in ("bp_out_l", "bp_out_r"):
            box = _find_box(boxes, obj_id)
            assert box["text"] == "*~ 1."

    def test_wires_outlet_2_bp(self):
        """svf~ outlet 2 is band-pass."""
        _, lines = bandpass_filter("bp")
        assert any(
            l["patchline"]["source"] == ["bp_l", 2]
            and l["patchline"]["destination"] == ["bp_out_l", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["bp_r", 2]
            and l["patchline"]["destination"] == ["bp_out_r", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = bandpass_filter("myfilter")
        ids = _box_ids(boxes)
        assert "myfilter_l" in ids
        assert "myfilter_r" in ids


class TestNotchFilter:
    """Test notch_filter() wires svf~ outlet 3 (notch)."""

    def test_returns_4_boxes_2_lines(self):
        boxes, lines = notch_filter("nf")
        assert len(boxes) == 4
        assert len(lines) == 2

    def test_has_svf_objects(self):
        boxes, _ = notch_filter("nf")
        for obj_id in ("nf_l", "nf_r"):
            box = _find_box(boxes, obj_id)
            assert box["text"] == "svf~"
            assert box["numinlets"] == 3
            assert box["numoutlets"] == 4

    def test_has_passthrough_objects(self):
        boxes, _ = notch_filter("nf")
        for obj_id in ("nf_out_l", "nf_out_r"):
            box = _find_box(boxes, obj_id)
            assert box["text"] == "*~ 1."

    def test_wires_outlet_3_notch(self):
        """svf~ outlet 3 is notch."""
        _, lines = notch_filter("nf")
        assert any(
            l["patchline"]["source"] == ["nf_l", 3]
            and l["patchline"]["destination"] == ["nf_out_l", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["nf_r", 3]
            and l["patchline"]["destination"] == ["nf_out_r", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = notch_filter("notch")
        ids = _box_ids(boxes)
        assert "notch_l" in ids
        assert "notch_r" in ids


class TestHighshelfFilter:
    """Test highshelf_filter() creates biquad~ shelf filter."""

    def test_returns_2_boxes_0_lines(self):
        boxes, lines = highshelf_filter("hs")
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_uses_biquad(self):
        boxes, _ = highshelf_filter("hs")
        for b in boxes:
            assert b["box"]["text"].startswith("biquad~")

    def test_6_inlets_1_outlet(self):
        boxes, _ = highshelf_filter("hs")
        for b in boxes:
            assert b["box"]["numinlets"] == 6
            assert b["box"]["numoutlets"] == 1
            assert b["box"]["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = highshelf_filter("shelf")
        ids = _box_ids(boxes)
        assert "shelf_l" in ids
        assert "shelf_r" in ids

    def test_custom_freq_changes_coefficients(self):
        boxes1, _ = highshelf_filter("hs", freq=1000.)
        boxes2, _ = highshelf_filter("hs", freq=5000.)
        assert boxes1[0]["box"]["text"] != boxes2[0]["box"]["text"]

    def test_custom_gain_changes_coefficients(self):
        boxes1, _ = highshelf_filter("hs", gain_db=0.)
        boxes2, _ = highshelf_filter("hs", gain_db=6.)
        assert boxes1[0]["box"]["text"] != boxes2[0]["box"]["text"]


class TestLowshelfFilter:
    """Test lowshelf_filter() creates biquad~ shelf filter."""

    def test_returns_2_boxes_0_lines(self):
        boxes, lines = lowshelf_filter("ls")
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_uses_biquad(self):
        boxes, _ = lowshelf_filter("ls")
        for b in boxes:
            assert b["box"]["text"].startswith("biquad~")

    def test_6_inlets_1_outlet(self):
        boxes, _ = lowshelf_filter("ls")
        for b in boxes:
            assert b["box"]["numinlets"] == 6
            assert b["box"]["numoutlets"] == 1
            assert b["box"]["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = lowshelf_filter("shelf")
        ids = _box_ids(boxes)
        assert "shelf_l" in ids
        assert "shelf_r" in ids

    def test_custom_freq_changes_coefficients(self):
        boxes1, _ = lowshelf_filter("ls", freq=200.)
        boxes2, _ = lowshelf_filter("ls", freq=800.)
        assert boxes1[0]["box"]["text"] != boxes2[0]["box"]["text"]

    def test_no_dcblock_in_output(self):
        boxes, _ = lowshelf_filter("ls")
        for b in boxes:
            assert "dcblock~" not in b["box"]["text"]


class TestTriangleLFO:
    """Test lfo() with waveform='triangle'."""

    def test_returns_boxes_and_lines(self):
        boxes, lines = lfo("lfo", waveform="triangle")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_uses_tri_tilde(self):
        boxes, _ = lfo("lfo", waveform="triangle")
        osc = _find_box(boxes, "lfo_osc")
        assert osc["text"] == "tri~"
        assert osc["numinlets"] == 2
        assert osc["numoutlets"] == 1

    def test_scale_and_offset_for_unipolar(self):
        boxes, _ = lfo("lfo", waveform="triangle")
        scale = _find_box(boxes, "lfo_scale")
        offset = _find_box(boxes, "lfo_offset")
        assert scale["text"] == "*~ 0.5"
        assert offset["text"] == "+~ 0.5"

    def test_has_depth_stage(self):
        boxes, _ = lfo("lfo", waveform="triangle")
        depth = _find_box(boxes, "lfo_depth")
        assert depth["text"] == "*~ 1."

    def test_wiring_osc_to_scale_to_offset_to_depth(self):
        _, lines = lfo("lfo", waveform="triangle")
        assert any(
            l["patchline"]["source"] == ["lfo_osc", 0]
            and l["patchline"]["destination"] == ["lfo_scale", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["lfo_scale", 0]
            and l["patchline"]["destination"] == ["lfo_offset", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["lfo_offset", 0]
            and l["patchline"]["destination"] == ["lfo_depth", 0]
            for l in lines
        )

    def test_same_box_count_as_sine(self):
        sine_boxes, _ = lfo("lfo", waveform="sine")
        tri_boxes, _ = lfo("lfo", waveform="triangle")
        assert len(sine_boxes) == len(tri_boxes)

    def test_no_sig_in_output(self):
        boxes, _ = lfo("lfo", waveform="triangle")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]


class TestCompressor:
    """Test compressor() creates a log-domain stereo compressor."""

    def test_returns_boxes_and_lines(self):
        boxes, lines = compressor("comp")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_stereo_abs_objects(self):
        boxes, _ = compressor("comp")
        for ch in ("l", "r"):
            box = _find_box(boxes, f"comp_abs_{ch}")
            assert box["text"] == "abs~"

    def test_stereo_slide_objects(self):
        boxes, _ = compressor("comp")
        for ch in ("l", "r"):
            box = _find_box(boxes, f"comp_atk_{ch}")
            assert box["text"].startswith("slide~")

    def test_has_ampdb_objects(self):
        boxes, _ = compressor("comp")
        for ch in ("l", "r"):
            box = _find_box(boxes, f"comp_adb_{ch}")
            assert box["text"] == "ampdb~"

    def test_has_dbtoa_objects(self):
        boxes, _ = compressor("comp")
        for ch in ("l", "r"):
            box = _find_box(boxes, f"comp_lin_{ch}")
            assert box["text"] == "dbtoa~"

    def test_has_output_multipliers(self):
        boxes, _ = compressor("comp")
        for ch in ("l", "r"):
            box = _find_box(boxes, f"comp_out_{ch}")
            assert box["text"] == "*~"

    def test_ids_use_prefix(self):
        boxes, _ = compressor("mycomp")
        ids = _box_ids(boxes)
        assert "mycomp_abs_l" in ids
        assert "mycomp_abs_r" in ids
        assert "mycomp_out_l" in ids
        assert "mycomp_out_r" in ids

    def test_abs_feeds_slide(self):
        _, lines = compressor("comp")
        for ch in ("l", "r"):
            assert any(
                l["patchline"]["source"] == [f"comp_abs_{ch}", 0]
                and l["patchline"]["destination"] == [f"comp_atk_{ch}", 0]
                for l in lines
            )

    def test_dbtoa_feeds_output(self):
        _, lines = compressor("comp")
        for ch in ("l", "r"):
            assert any(
                l["patchline"]["source"] == [f"comp_lin_{ch}", 0]
                and l["patchline"]["destination"] == [f"comp_out_{ch}", 1]
                for l in lines
            )

    def test_no_sig_in_output(self):
        boxes, _ = compressor("comp")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]


class TestLimiter:
    """Test limiter() creates a stereo brickwall limiter."""

    def test_returns_boxes_and_lines(self):
        boxes, lines = limiter("lim")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_stereo_structure(self):
        boxes, _ = limiter("lim")
        for ch in ("l", "r"):
            _find_box(boxes, f"lim_abs_{ch}")
            _find_box(boxes, f"lim_peak_{ch}")
            _find_box(boxes, f"lim_out_{ch}")

    def test_instant_attack_in_slide(self):
        """Brickwall limiter uses slide~ 1 for instant attack."""
        boxes, _ = limiter("lim")
        for ch in ("l", "r"):
            peak = _find_box(boxes, f"lim_peak_{ch}")
            assert peak["text"].startswith("slide~ 1 ")

    def test_has_gain_clip(self):
        """Gain must be clipped to max 1.0 — no expansion."""
        boxes, _ = limiter("lim")
        for ch in ("l", "r"):
            gclip = _find_box(boxes, f"lim_gclip_{ch}")
            assert "clip~" in gclip["text"]
            assert "1." in gclip["text"]

    def test_output_is_multiply(self):
        boxes, _ = limiter("lim")
        for ch in ("l", "r"):
            out = _find_box(boxes, f"lim_out_{ch}")
            assert out["text"] == "*~"

    def test_ids_use_prefix(self):
        boxes, _ = limiter("brick")
        ids = _box_ids(boxes)
        assert "brick_abs_l" in ids
        assert "brick_abs_r" in ids

    def test_no_sig_in_output(self):
        boxes, _ = limiter("lim")
        for b in boxes:
            assert "sig~" not in b["box"]["text"]


class TestNoiseSource:
    """Test noise_source() creates noise generators."""

    def test_white_noise_returns_1_box_0_lines(self):
        boxes, lines = noise_source("ns", color="white")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_white_noise_object(self):
        boxes, _ = noise_source("ns", color="white")
        noise = _find_box(boxes, "ns_noise")
        assert noise["text"] == "noise~"
        assert noise["numoutlets"] == 1
        assert noise["outlettype"] == ["signal"]

    def test_pink_noise_returns_2_boxes_1_line(self):
        boxes, lines = noise_source("ns", color="pink")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_pink_noise_has_noise_and_filter(self):
        boxes, _ = noise_source("ns", color="pink")
        noise = _find_box(boxes, "ns_noise")
        lp = _find_box(boxes, "ns_lp")
        assert noise["text"] == "noise~"
        assert lp["text"].startswith("onepole~")

    def test_pink_noise_wiring(self):
        _, lines = noise_source("ns", color="pink")
        assert any(
            l["patchline"]["source"] == ["ns_noise", 0]
            and l["patchline"]["destination"] == ["ns_lp", 0]
            for l in lines
        )

    def test_default_is_white(self):
        boxes, lines = noise_source("ns")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_unknown_color_raises(self):
        with pytest.raises(ValueError, match="Unknown noise color"):
            noise_source("ns", color="brown")

    def test_ids_use_prefix(self):
        boxes, _ = noise_source("gen", color="white")
        ids = _box_ids(boxes)
        assert "gen_noise" in ids


class TestTempoSync:
    """Test tempo_sync() reads Live transport and computes time values."""

    def test_returns_4_boxes_3_lines(self):
        boxes, lines = tempo_sync("ts")
        assert len(boxes) == 4
        assert len(lines) == 3

    def test_has_transport_object(self):
        boxes, _ = tempo_sync("ts")
        transport = _find_box(boxes, "ts_transport")
        assert transport["text"] == "transport"

    def test_has_bpm_float(self):
        boxes, _ = tempo_sync("ts")
        bpm = _find_box(boxes, "ts_bpm")
        assert bpm["text"] == "f"

    def test_has_delay_expr(self):
        boxes, _ = tempo_sync("ts")
        delay = _find_box(boxes, "ts_delay")
        assert "expr" in delay["text"]
        assert "60000" in delay["text"]

    def test_has_rate_expr(self):
        boxes, _ = tempo_sync("ts")
        rate = _find_box(boxes, "ts_rate")
        assert "expr" in rate["text"]
        assert "60" in rate["text"]

    def test_division_in_expr(self):
        boxes, _ = tempo_sync("ts", division=0.5)
        delay = _find_box(boxes, "ts_delay")
        rate = _find_box(boxes, "ts_rate")
        assert "0.5" in delay["text"]
        assert "0.5" in rate["text"]

    def test_transport_feeds_bpm(self):
        _, lines = tempo_sync("ts")
        assert any(
            l["patchline"]["source"] == ["ts_transport", 0]
            and l["patchline"]["destination"] == ["ts_bpm", 0]
            for l in lines
        )

    def test_bpm_feeds_delay_and_rate(self):
        _, lines = tempo_sync("ts")
        assert any(
            l["patchline"]["source"] == ["ts_bpm", 0]
            and l["patchline"]["destination"] == ["ts_delay", 0]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["ts_bpm", 0]
            and l["patchline"]["destination"] == ["ts_rate", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = tempo_sync("beat")
        ids = _box_ids(boxes)
        assert "beat_transport" in ids
        assert "beat_bpm" in ids
        assert "beat_delay" in ids
        assert "beat_rate" in ids


class TestEnvelopeFollowerSampleratefix:
    """Test that envelope_follower uses samplerate~ instead of hardcoded 44100."""

    def test_has_samplerate_object(self):
        boxes, _ = envelope_follower("env")
        sr = _find_box(boxes, "env_sr")
        assert sr["text"] == "samplerate~"

    def test_has_snapshot_object(self):
        boxes, _ = envelope_follower("env")
        snap = _find_box(boxes, "env_sr_snap")
        assert snap["text"] == "snapshot~"

    def test_has_attack_expr(self):
        boxes, _ = envelope_follower("env")
        atk = _find_box(boxes, "env_atk_expr")
        assert "expr" in atk["text"]
        assert "$f1" in atk["text"]
        assert "$f2" in atk["text"]

    def test_has_release_expr(self):
        boxes, _ = envelope_follower("env")
        rel = _find_box(boxes, "env_rel_expr")
        assert "expr" in rel["text"]

    def test_samplerate_feeds_snapshot(self):
        _, lines = envelope_follower("env")
        assert any(
            l["patchline"]["source"] == ["env_sr", 0]
            and l["patchline"]["destination"] == ["env_sr_snap", 0]
            for l in lines
        )

    def test_snapshot_feeds_both_exprs(self):
        _, lines = envelope_follower("env")
        assert any(
            l["patchline"]["source"] == ["env_sr_snap", 0]
            and l["patchline"]["destination"] == ["env_atk_expr", 1]
            for l in lines
        )
        assert any(
            l["patchline"]["source"] == ["env_sr_snap", 0]
            and l["patchline"]["destination"] == ["env_rel_expr", 1]
            for l in lines
        )

    def test_expr_feeds_slide_attack_inlet(self):
        _, lines = envelope_follower("env")
        assert any(
            l["patchline"]["source"] == ["env_atk_expr", 0]
            and l["patchline"]["destination"] == ["env_slide", 1]
            for l in lines
        )

    def test_expr_feeds_slide_release_inlet(self):
        _, lines = envelope_follower("env")
        assert any(
            l["patchline"]["source"] == ["env_rel_expr", 0]
            and l["patchline"]["destination"] == ["env_slide", 2]
            for l in lines
        )


class TestLiveRemote:
    """Test live_remote() creates a live.remote~ object."""

    def test_returns_1_box_0_lines(self):
        boxes, lines = live_remote("lr")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_object_text(self):
        boxes, _ = live_remote("lr")
        box = _find_box(boxes, "lr_remote")
        assert box["text"] == "live.remote~"

    def test_inlets_outlets(self):
        boxes, _ = live_remote("lr")
        box = _find_box(boxes, "lr_remote")
        assert box["numinlets"] == 3
        assert box["numoutlets"] == 1
        assert box["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = live_remote("ctrl")
        ids = _box_ids(boxes)
        assert "ctrl_remote" in ids


class TestLiveParamSignal:
    """Test live_param_signal() creates a live.param~ object."""

    def test_returns_1_box_0_lines(self):
        boxes, lines = live_param_signal("lp")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_object_text(self):
        boxes, _ = live_param_signal("lp")
        box = _find_box(boxes, "lp_param")
        assert box["text"] == "live.param~"

    def test_inlets_outlets(self):
        boxes, _ = live_param_signal("lp")
        box = _find_box(boxes, "lp_param")
        assert box["numinlets"] == 1
        assert box["numoutlets"] == 2
        assert box["outlettype"] == ["signal", ""]

    def test_ids_use_prefix(self):
        boxes, _ = live_param_signal("myp")
        ids = _box_ids(boxes)
        assert "myp_param" in ids


class TestAdsrEnvelope:
    """Test adsr_envelope() creates a live.adsr~ object."""

    def test_returns_1_box_0_lines(self):
        boxes, lines = adsr_envelope("env")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_args(self):
        boxes, _ = adsr_envelope("env")
        box = _find_box(boxes, "env_adsr")
        assert box["text"] == "live.adsr~ 10 100 0.7 200"

    def test_custom_args(self):
        boxes, _ = adsr_envelope("env", attack_ms=5, decay_ms=50,
                                 sustain=0.5, release_ms=500)
        box = _find_box(boxes, "env_adsr")
        assert box["text"] == "live.adsr~ 5 50 0.5 500"

    def test_inlets_outlets(self):
        boxes, _ = adsr_envelope("env")
        box = _find_box(boxes, "env_adsr")
        assert box["numinlets"] == 5
        assert box["numoutlets"] == 4
        assert box["outlettype"] == ["signal", "signal", "", ""]

    def test_ids_use_prefix(self):
        boxes, _ = adsr_envelope("amp")
        ids = _box_ids(boxes)
        assert "amp_adsr" in ids


class TestPeakingEq:
    """Test peaking_eq() creates filtercoeff~ + biquad~ pair."""

    def test_returns_2_boxes_1_line(self):
        boxes, lines = peaking_eq("eq")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_filtercoeff(self):
        boxes, _ = peaking_eq("eq")
        coeff = _find_box(boxes, "eq_coeff")
        assert coeff["text"] == "filtercoeff~ peaknotch 1000 0 1.0"
        assert coeff["numinlets"] == 6
        assert coeff["numoutlets"] == 1

    def test_has_biquad(self):
        boxes, _ = peaking_eq("eq")
        bq = _find_box(boxes, "eq_biquad")
        assert bq["text"] == "biquad~"
        assert bq["numinlets"] == 6
        assert bq["numoutlets"] == 1
        assert bq["outlettype"] == ["signal"]

    def test_coeff_feeds_biquad(self):
        _, lines = peaking_eq("eq")
        assert any(
            l["patchline"]["source"] == ["eq_coeff", 0]
            and l["patchline"]["destination"] == ["eq_biquad", 1]
            for l in lines
        )

    def test_custom_params(self):
        boxes, _ = peaking_eq("eq", freq=2000, gain=6, q=2.0)
        coeff = _find_box(boxes, "eq_coeff")
        assert coeff["text"] == "filtercoeff~ peaknotch 2000 6 2.0"

    def test_ids_use_prefix(self):
        boxes, _ = peaking_eq("band1")
        ids = _box_ids(boxes)
        assert "band1_coeff" in ids
        assert "band1_biquad" in ids


class TestAllpassFilter:
    """Test allpass_filter() creates filtercoeff~ allpass + biquad~ pair."""

    def test_returns_2_boxes_1_line(self):
        boxes, lines = allpass_filter("ap")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_filtercoeff(self):
        boxes, _ = allpass_filter("ap")
        coeff = _find_box(boxes, "ap_coeff")
        assert coeff["text"] == "filtercoeff~ allpass 1000 1. 0.7"
        assert coeff["numinlets"] == 6
        assert coeff["numoutlets"] == 1

    def test_has_biquad(self):
        boxes, _ = allpass_filter("ap")
        bq = _find_box(boxes, "ap_biquad")
        assert bq["text"] == "biquad~"
        assert bq["numinlets"] == 6
        assert bq["numoutlets"] == 1
        assert bq["outlettype"] == ["signal"]

    def test_coeff_feeds_biquad(self):
        _, lines = allpass_filter("ap")
        assert any(
            l["patchline"]["source"] == ["ap_coeff", 0]
            and l["patchline"]["destination"] == ["ap_biquad", 1]
            for l in lines
        )

    def test_custom_params(self):
        boxes, _ = allpass_filter("ap", freq=500, q=1.5)
        coeff = _find_box(boxes, "ap_coeff")
        assert coeff["text"] == "filtercoeff~ allpass 500 1. 1.5"

    def test_ids_use_prefix(self):
        boxes, _ = allpass_filter("phase")
        ids = _box_ids(boxes)
        assert "phase_coeff" in ids
        assert "phase_biquad" in ids


class TestNotein:
    def test_returns_boxes_and_lines(self):
        boxes, lines = notein("ni")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_all_channels(self):
        boxes, _ = notein("ni")
        assert _box_texts(boxes) == ["notein"]

    def test_specific_channel(self):
        boxes, _ = notein("ni", channel=3)
        assert _box_texts(boxes) == ["notein 3"]

    def test_box_id(self):
        boxes, _ = notein("ni")
        assert _box_ids(boxes) == ["ni_notein"]

    def test_three_outlets(self):
        boxes, _ = notein("ni")
        assert boxes[0]["box"]["numoutlets"] == 3


class TestNoteout:
    def test_returns_boxes_and_lines(self):
        boxes, lines = noteout("no")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_all_channels(self):
        boxes, _ = noteout("no")
        assert _box_texts(boxes) == ["noteout"]

    def test_specific_channel(self):
        boxes, _ = noteout("no", channel=5)
        assert _box_texts(boxes) == ["noteout 5"]

    def test_box_id(self):
        boxes, _ = noteout("no")
        assert _box_ids(boxes) == ["no_noteout"]

    def test_three_inlets(self):
        boxes, _ = noteout("no")
        assert boxes[0]["box"]["numinlets"] == 3

    def test_zero_outlets(self):
        boxes, _ = noteout("no")
        assert boxes[0]["box"]["numoutlets"] == 0


class TestCtlin:
    def test_returns_boxes_and_lines(self):
        boxes, lines = ctlin("cc")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_all_cc_all_channels(self):
        boxes, _ = ctlin("cc")
        assert _box_texts(boxes) == ["ctlin"]

    def test_specific_cc(self):
        boxes, _ = ctlin("cc", cc=74)
        assert _box_texts(boxes) == ["ctlin 74"]

    def test_specific_cc_and_channel(self):
        boxes, _ = ctlin("cc", cc=1, channel=2)
        assert _box_texts(boxes) == ["ctlin 1 2"]

    def test_channel_without_cc(self):
        boxes, _ = ctlin("cc", channel=3)
        assert _box_texts(boxes) == ["ctlin 0 3"]

    def test_three_outlets(self):
        boxes, _ = ctlin("cc")
        assert boxes[0]["box"]["numoutlets"] == 3


class TestCtlout:
    def test_returns_boxes_and_lines(self):
        boxes, lines = ctlout("co")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_cc_and_channel(self):
        boxes, _ = ctlout("co")
        assert _box_texts(boxes) == ["ctlout 1 1"]

    def test_custom_cc_and_channel(self):
        boxes, _ = ctlout("co", cc=74, channel=3)
        assert _box_texts(boxes) == ["ctlout 74 3"]

    def test_three_inlets(self):
        boxes, _ = ctlout("co")
        assert boxes[0]["box"]["numinlets"] == 3

    def test_zero_outlets(self):
        boxes, _ = ctlout("co")
        assert boxes[0]["box"]["numoutlets"] == 0


class TestVelocityCurve:
    def test_linear_returns_clip_only(self):
        boxes, lines = velocity_curve("vc")
        assert len(boxes) == 1
        assert len(lines) == 0
        assert "clip 0 127" in _box_texts(boxes)

    def test_compress_returns_expr_and_clip(self):
        boxes, lines = velocity_curve("vc", curve="compress")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_compress_expr_text(self):
        boxes, _ = velocity_curve("vc", curve="compress")
        texts = _box_texts(boxes)
        assert any("pow" in t and "0.5" in t for t in texts)

    def test_expand_uses_power_2(self):
        boxes, _ = velocity_curve("vc", curve="expand")
        texts = _box_texts(boxes)
        assert any("2.0" in t for t in texts)

    def test_soft_uses_power_03(self):
        boxes, _ = velocity_curve("vc", curve="soft")
        texts = _box_texts(boxes)
        assert any("0.3" in t for t in texts)

    def test_hard_uses_power_3(self):
        boxes, _ = velocity_curve("vc", curve="hard")
        texts = _box_texts(boxes)
        assert any("3.0" in t for t in texts)

    def test_invalid_curve_raises(self):
        with pytest.raises(ValueError, match="Unknown curve"):
            velocity_curve("vc", curve="bogus")

    def test_clip_follows_expr(self):
        boxes, lines = velocity_curve("vc", curve="compress")
        # Line goes from expr to clip
        assert lines[0]["patchline"]["source"] == ["vc_expr", 0]
        assert lines[0]["patchline"]["destination"] == ["vc_clip", 0]


class TestTranspose:
    def test_returns_add_and_clip(self):
        boxes, lines = transpose("tp")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_default_zero_semitones(self):
        boxes, _ = transpose("tp")
        assert "+ 0" in _box_texts(boxes)

    def test_custom_semitones(self):
        boxes, _ = transpose("tp", semitones=7)
        assert "+ 7" in _box_texts(boxes)

    def test_negative_semitones(self):
        boxes, _ = transpose("tp", semitones=-12)
        assert "+ -12" in _box_texts(boxes)

    def test_clip_0_127(self):
        boxes, _ = transpose("tp")
        assert "clip 0 127" in _box_texts(boxes)

    def test_add_to_clip_connection(self):
        _, lines = transpose("tp")
        assert lines[0]["patchline"]["source"] == ["tp_add", 0]
        assert lines[0]["patchline"]["destination"] == ["tp_clip", 0]


class TestMidiThru:
    def test_returns_boxes_and_lines(self):
        boxes, lines = midi_thru("mt")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_box_texts(self):
        boxes, _ = midi_thru("mt")
        texts = _box_texts(boxes)
        assert "midiin" in texts
        assert "midiout" in texts

    def test_midiin_to_midiout_connection(self):
        _, lines = midi_thru("mt")
        assert lines[0]["patchline"]["source"] == ["mt_midiin", 0]
        assert lines[0]["patchline"]["destination"] == ["mt_midiout", 0]


class TestGateExpander:
    def test_returns_boxes_and_lines(self):
        boxes, lines = gate_expander("ge")
        assert len(boxes) == 8  # 4 per channel (abs, slide, thresh, gate) x 2
        assert len(lines) == 6  # 3 per channel x 2

    def test_stereo_box_ids(self):
        boxes, _ = gate_expander("ge")
        ids = _box_ids(boxes)
        assert "ge_abs_l" in ids
        assert "ge_abs_r" in ids
        assert "ge_gate_l" in ids
        assert "ge_gate_r" in ids

    def test_contains_abs_tilde(self):
        boxes, _ = gate_expander("ge")
        texts = _box_texts(boxes)
        assert texts.count("abs~") == 2

    def test_contains_slide_tilde(self):
        boxes, _ = gate_expander("ge")
        texts = _box_texts(boxes)
        slide_count = sum(1 for t in texts if t.startswith("slide~"))
        assert slide_count == 2

    def test_contains_threshold_compare(self):
        boxes, _ = gate_expander("ge")
        texts = _box_texts(boxes)
        thresh_count = sum(1 for t in texts if t.startswith(">~"))
        assert thresh_count == 2

    def test_all_outlets_are_signal(self):
        boxes, _ = gate_expander("ge")
        for b in boxes:
            if b["box"].get("outlettype"):
                assert b["box"]["outlettype"] == ["signal"]


class TestSidechainDetect:
    def test_returns_boxes_and_lines(self):
        boxes, lines = sidechain_detect("sc")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_box_ids(self):
        boxes, _ = sidechain_detect("sc")
        ids = _box_ids(boxes)
        assert "sc_abs" in ids
        assert "sc_slide" in ids

    def test_abs_to_slide_connection(self):
        _, lines = sidechain_detect("sc")
        assert lines[0]["patchline"]["source"] == ["sc_abs", 0]
        assert lines[0]["patchline"]["destination"] == ["sc_slide", 0]


class TestSampleAndHold:
    def test_returns_boxes_and_lines(self):
        boxes, lines = sample_and_hold("sh")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_box_ids(self):
        boxes, _ = sample_and_hold("sh")
        ids = _box_ids(boxes)
        assert "sh_noise" in ids
        assert "sh_sah" in ids

    def test_noise_to_sah_connection(self):
        _, lines = sample_and_hold("sh")
        assert lines[0]["patchline"]["source"] == ["sh_noise", 0]
        assert lines[0]["patchline"]["destination"] == ["sh_sah", 0]

    def test_contains_noise_tilde(self):
        boxes, _ = sample_and_hold("sh")
        assert "noise~" in _box_texts(boxes)

    def test_contains_sah_tilde(self):
        boxes, _ = sample_and_hold("sh")
        assert "sah~" in _box_texts(boxes)


class TestMultibandCompressor:
    def test_returns_boxes_and_lines(self):
        boxes, lines = multiband_compressor("mbc")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_contains_crossover_boxes(self):
        boxes, _ = multiband_compressor("mbc")
        ids = _box_ids(boxes)
        assert any("xover" in id for id in ids)

    def test_contains_compressor_boxes(self):
        boxes, _ = multiband_compressor("mbc")
        ids = _box_ids(boxes)
        assert any("lo" in id for id in ids)
        assert any("mid" in id for id in ids)
        assert any("hi" in id for id in ids)

    def test_contains_summing(self):
        boxes, _ = multiband_compressor("mbc")
        ids = _box_ids(boxes)
        assert any("sum" in id for id in ids)


class TestReverbNetwork:
    def test_returns_boxes_and_lines(self):
        boxes, lines = reverb_network("rv")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_default_4_combs(self):
        boxes, _ = reverb_network("rv")
        comb_count = sum(1 for b in boxes if "comb" in b["box"].get("text", ""))
        assert comb_count == 4

    def test_default_2_allpasses(self):
        boxes, _ = reverb_network("rv")
        ids = _box_ids(boxes)
        ap_count = sum(1 for id in ids if "_ap_" in id)
        assert ap_count == 2

    def test_custom_num_combs(self):
        boxes, _ = reverb_network("rv", num_combs=6)
        comb_ids = [id for id in _box_ids(boxes) if "_comb_" in id]
        assert len(comb_ids) == 6

    def test_custom_num_allpasses(self):
        boxes, _ = reverb_network("rv", num_allpasses=4)
        ap_ids = [id for id in _box_ids(boxes) if "_ap_" in id]
        assert len(ap_ids) == 4

    def test_single_comb_no_summers(self):
        boxes, _ = reverb_network("rv", num_combs=1)
        sum_ids = [id for id in _box_ids(boxes) if "_sum_" in id]
        assert len(sum_ids) == 0

    def test_all_outlets_are_signal(self):
        boxes, _ = reverb_network("rv")
        for b in boxes:
            if b["box"].get("outlettype"):
                assert b["box"]["outlettype"] == ["signal"]


class TestWavetableOsc:
    def test_returns_1_box_0_lines(self):
        boxes, lines = wavetable_osc("wt")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_wavetable_object(self):
        boxes, _ = wavetable_osc("wt")
        box = _find_box(boxes, "wt_wt")
        assert box["text"] == "wavetable~"
        assert box["numinlets"] == 3
        assert box["numoutlets"] == 1
        assert box["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = wavetable_osc("myosc")
        assert "myosc_wt" in _box_ids(boxes)


class TestBufferLoad:
    def test_returns_1_box_0_lines(self):
        boxes, lines = buffer_load("bl", "mywave")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_buffer_object(self):
        boxes, _ = buffer_load("bl", "mywave")
        box = _find_box(boxes, "bl_buf")
        assert "buffer~" in box["text"]
        assert "mywave" in box["text"]
        assert "1024" in box["text"]

    def test_custom_size(self):
        boxes, _ = buffer_load("bl", "wave2", size=512)
        box = _find_box(boxes, "bl_buf")
        assert "512" in box["text"]

    def test_ids_use_prefix(self):
        boxes, _ = buffer_load("mybuf", "tab")
        assert "mybuf_buf" in _box_ids(boxes)


class TestArpeggiator:
    def test_returns_2_boxes_2_lines(self):
        boxes, lines = arpeggiator("arp")
        assert len(boxes) == 2
        assert len(lines) == 2

    def test_default_mode_up(self):
        boxes, _ = arpeggiator("arp")
        box = _find_box(boxes, "arp_arp")
        assert "arpeggiate up" in box["text"]

    def test_custom_mode(self):
        boxes, _ = arpeggiator("arp", mode="down")
        box = _find_box(boxes, "arp_arp")
        assert "arpeggiate down" in box["text"]

    def test_has_makenote(self):
        boxes, _ = arpeggiator("arp")
        box = _find_box(boxes, "arp_make")
        assert "makenote" in box["text"]

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown arpeggiator mode"):
            arpeggiator("arp", mode="zigzag")

    def test_arp_to_make_connection(self):
        _, lines = arpeggiator("arp")
        assert any(
            l["patchline"]["source"] == ["arp_arp", 0]
            and l["patchline"]["destination"] == ["arp_make", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = arpeggiator("myarp")
        ids = _box_ids(boxes)
        assert "myarp_arp" in ids
        assert "myarp_make" in ids


class TestChord:
    def test_default_major_triad(self):
        boxes, _ = chord("ch")
        assert len(boxes) == 2

    def test_default_intervals_in_text(self):
        boxes, _ = chord("ch")
        texts = _box_texts(boxes)
        assert any("4" in t for t in texts)
        assert any("7" in t for t in texts)

    def test_custom_intervals(self):
        boxes, _ = chord("ch", intervals=[3, 7, 10])
        assert len(boxes) == 3

    def test_uses_plus_objects(self):
        boxes, _ = chord("ch")
        for b in boxes:
            assert b["box"]["text"].startswith("+ ")

    def test_returns_no_lines(self):
        _, lines = chord("ch")
        assert len(lines) == 0

    def test_ids_use_prefix(self):
        boxes, _ = chord("mychord", intervals=[4, 7])
        ids = _box_ids(boxes)
        assert "mychord_int_0" in ids
        assert "mychord_int_1" in ids


class TestPitchQuantize:
    def test_returns_1_box_0_lines(self):
        boxes, lines = pitch_quantize("pq")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_chromatic(self):
        boxes, _ = pitch_quantize("pq")
        box = _find_box(boxes, "pq_scale")
        assert "scale chromatic" in box["text"]

    def test_custom_scale(self):
        boxes, _ = pitch_quantize("pq", scale="major")
        box = _find_box(boxes, "pq_scale")
        assert "scale major" in box["text"]

    def test_invalid_scale_raises(self):
        with pytest.raises(ValueError, match="Unknown scale"):
            pitch_quantize("pq", scale="blues")

    def test_all_valid_scales(self):
        for scale in ("chromatic", "major", "minor", "pentatonic", "dorian"):
            boxes, _ = pitch_quantize("pq", scale=scale)
            assert len(boxes) == 1

    def test_ids_use_prefix(self):
        boxes, _ = pitch_quantize("myq")
        assert "myq_scale" in _box_ids(boxes)


class TestLookaheadEnvelopeFollower:
    def test_returns_4_boxes_2_lines(self):
        boxes, lines = lookahead_envelope_follower("lah")
        assert len(boxes) == 4
        assert len(lines) == 2

    def test_has_tapin(self):
        boxes, _ = lookahead_envelope_follower("lah")
        box = _find_box(boxes, "lah_tapin")
        assert "tapin~" in box["text"]
        assert box["outlettype"] == ["tapconnect"]

    def test_has_tapout(self):
        boxes, _ = lookahead_envelope_follower("lah")
        box = _find_box(boxes, "lah_tapout")
        assert "tapout~" in box["text"]
        assert box["outlettype"] == ["signal"]

    def test_has_abs_and_slide(self):
        boxes, _ = lookahead_envelope_follower("lah")
        _find_box(boxes, "lah_abs")
        _find_box(boxes, "lah_slide")

    def test_tapin_feeds_tapout(self):
        _, lines = lookahead_envelope_follower("lah")
        assert any(
            l["patchline"]["source"] == ["lah_tapin", 0]
            and l["patchline"]["destination"] == ["lah_tapout", 0]
            for l in lines
        )

    def test_abs_feeds_slide(self):
        _, lines = lookahead_envelope_follower("lah")
        assert any(
            l["patchline"]["source"] == ["lah_abs", 0]
            and l["patchline"]["destination"] == ["lah_slide", 0]
            for l in lines
        )

    def test_custom_lookahead(self):
        boxes, _ = lookahead_envelope_follower("lah", lookahead_ms=10)
        box = _find_box(boxes, "lah_tapout")
        assert "10" in box["text"]

    def test_ids_use_prefix(self):
        boxes, _ = lookahead_envelope_follower("myenv")
        ids = _box_ids(boxes)
        assert "myenv_tapin" in ids
        assert "myenv_abs" in ids


class TestFdnReverb:
    def test_default_8_delays(self):
        boxes, _ = fdn_reverb("fdn")
        tapin_count = sum(1 for b in boxes if "tapin~" in b["box"].get("text", ""))
        assert tapin_count == 8

    def test_default_8_tapouts(self):
        boxes, _ = fdn_reverb("fdn")
        tapout_count = sum(1 for b in boxes if "tapout~" in b["box"].get("text", ""))
        assert tapout_count == 8

    def test_prime_delay_times(self):
        boxes, _ = fdn_reverb("fdn")
        texts = [b["box"]["text"] for b in boxes if "tapin~" in b["box"].get("text", "")]
        # First tapin should use 47ms
        assert any("47" in t for t in texts)

    def test_has_sum_output(self):
        boxes, _ = fdn_reverb("fdn")
        ids = _box_ids(boxes)
        assert "fdn_sum" in ids

    def test_single_delay_no_adders(self):
        boxes, _ = fdn_reverb("fdn", num_delays=1)
        add_ids = [id for id in _box_ids(boxes) if "_add_" in id]
        assert len(add_ids) == 0

    def test_custom_num_delays(self):
        boxes, _ = fdn_reverb("fdn", num_delays=4)
        tapin_count = sum(1 for b in boxes if "tapin~" in b["box"].get("text", ""))
        assert tapin_count == 4

    def test_returns_boxes_and_lines(self):
        boxes, lines = fdn_reverb("fdn")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_ids_use_prefix(self):
        boxes, _ = fdn_reverb("myfdn")
        assert "myfdn_tapin_0" in _box_ids(boxes)


class TestSpectralGate:
    def test_returns_1_box_0_lines(self):
        boxes, lines = spectral_gate("sg")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_pfft_object(self):
        boxes, _ = spectral_gate("sg")
        box = _find_box(boxes, "sg_pfft")
        assert "pfft~" in box["text"]
        assert "spectral_gate_sub.maxpat" in box["text"]

    def test_inlets_outlets(self):
        boxes, _ = spectral_gate("sg")
        box = _find_box(boxes, "sg_pfft")
        assert box["numinlets"] == 2
        assert box["numoutlets"] == 1
        assert box["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = spectral_gate("mysg")
        assert "mysg_pfft" in _box_ids(boxes)


class TestSpectralGateSubpatcher:
    def test_returns_dict_with_patcher_key(self):
        result = spectral_gate_subpatcher()
        assert "patcher" in result

    def test_has_fftin(self):
        result = spectral_gate_subpatcher()
        boxes = result["patcher"]["boxes"]
        texts = [b["box"]["text"] for b in boxes]
        assert any("fftin~" in t for t in texts)

    def test_has_fftout(self):
        result = spectral_gate_subpatcher()
        boxes = result["patcher"]["boxes"]
        texts = [b["box"]["text"] for b in boxes]
        assert any("fftout~" in t for t in texts)

    def test_has_threshold_comparison(self):
        result = spectral_gate_subpatcher(threshold=0.05)
        boxes = result["patcher"]["boxes"]
        texts = [b["box"]["text"] for b in boxes]
        assert any("0.05" in t for t in texts)

    def test_has_lines(self):
        result = spectral_gate_subpatcher()
        assert len(result["patcher"]["lines"]) > 0


class TestVocoder:
    def test_default_16_bands(self):
        boxes, _ = vocoder("vc")
        out_ids = [id for id in _box_ids(boxes) if id.startswith("vc_out_")]
        assert len(out_ids) == 16

    def test_custom_num_bands(self):
        boxes, _ = vocoder("vc", num_bands=4)
        out_ids = [id for id in _box_ids(boxes) if id.startswith("vc_out_")]
        assert len(out_ids) == 4

    def test_has_carrier_bandpass(self):
        boxes, _ = vocoder("vc", num_bands=2)
        ids = _box_ids(boxes)
        assert any("car_bp" in id for id in ids)

    def test_has_modulator_bandpass(self):
        boxes, _ = vocoder("vc", num_bands=2)
        ids = _box_ids(boxes)
        assert any("mod_bp" in id for id in ids)

    def test_has_envelope_followers(self):
        boxes, _ = vocoder("vc", num_bands=2)
        ids = _box_ids(boxes)
        assert any("env" in id for id in ids)

    def test_returns_boxes_and_lines(self):
        boxes, lines = vocoder("vc", num_bands=2)
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_out_multiplier_objects(self):
        boxes, _ = vocoder("vc", num_bands=2)
        for i in range(2):
            box = _find_box(boxes, f"vc_out_{i}")
            assert box["text"] == "*~"

    def test_ids_use_prefix(self):
        boxes, _ = vocoder("myvc", num_bands=1)
        ids = _box_ids(boxes)
        assert "myvc_out_0" in ids


class TestMcExpand:
    def test_returns_1_box_0_lines(self):
        boxes, lines = mc_expand("mc")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_mc_pack(self):
        boxes, _ = mc_expand("mc")
        box = _find_box(boxes, "mc_pack")
        assert "mc.pack~" in box["text"]

    def test_default_8_channels(self):
        boxes, _ = mc_expand("mc")
        box = _find_box(boxes, "mc_pack")
        assert "8" in box["text"]

    def test_custom_channels(self):
        boxes, _ = mc_expand("mc", channels=4)
        box = _find_box(boxes, "mc_pack")
        assert "4" in box["text"]
        assert box["numinlets"] == 4

    def test_ids_use_prefix(self):
        boxes, _ = mc_expand("mymc")
        assert "mymc_pack" in _box_ids(boxes)


class TestMcCollapse:
    def test_returns_boxes_and_lines(self):
        boxes, lines = mc_collapse("mc")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_mc_unpack(self):
        boxes, _ = mc_collapse("mc")
        box = _find_box(boxes, "mc_unpack")
        assert "mc.unpack~" in box["text"]

    def test_default_8_channels(self):
        boxes, _ = mc_collapse("mc")
        box = _find_box(boxes, "mc_unpack")
        assert "8" in box["text"]

    def test_has_stereo_sum_outputs(self):
        boxes, _ = mc_collapse("mc")
        ids = _box_ids(boxes)
        assert "mc_sum_l" in ids
        assert "mc_sum_r" in ids

    def test_custom_channels(self):
        boxes, _ = mc_collapse("mc", channels=4)
        box = _find_box(boxes, "mc_unpack")
        assert "4" in box["text"]

    def test_ids_use_prefix(self):
        boxes, _ = mc_collapse("mymc")
        ids = _box_ids(boxes)
        assert "mymc_unpack" in ids


class TestNoteExpressionDecode:
    def test_returns_3_boxes_0_lines(self):
        boxes, lines = note_expression_decode("ned")
        assert len(boxes) == 3
        assert len(lines) == 0

    def test_has_notein(self):
        boxes, _ = note_expression_decode("ned")
        box = _find_box(boxes, "ned_notein")
        assert box["text"] == "notein"
        assert box["numoutlets"] == 3

    def test_has_polytouchin(self):
        boxes, _ = note_expression_decode("ned")
        box = _find_box(boxes, "ned_polytouch")
        assert "polytouchin" in box["text"]
        assert box["numoutlets"] == 3

    def test_has_pitchin(self):
        boxes, _ = note_expression_decode("ned")
        box = _find_box(boxes, "ned_pitchin")
        assert "pitchin" in box["text"]
        assert box["numoutlets"] == 2

    def test_ids_use_prefix(self):
        boxes, _ = note_expression_decode("myned")
        ids = _box_ids(boxes)
        assert "myned_notein" in ids
        assert "myned_polytouch" in ids
        assert "myned_pitchin" in ids


class TestTransportLfo:
    def test_returns_boxes_and_lines(self):
        boxes, lines = transport_lfo("tlfo")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_transport_object(self):
        boxes, _ = transport_lfo("tlfo")
        t = _find_box(boxes, "tlfo_transport")
        assert t["text"] == "transport"

    def test_has_bpm_float(self):
        boxes, _ = transport_lfo("tlfo")
        b = _find_box(boxes, "tlfo_bpm")
        assert b["text"] == "f"

    def test_has_rate_expr(self):
        boxes, _ = transport_lfo("tlfo")
        r = _find_box(boxes, "tlfo_rate")
        assert "expr" in r["text"]

    def test_default_sine_uses_cycle(self):
        boxes, _ = transport_lfo("tlfo", shape="sine")
        osc = _find_box(boxes, "tlfo_osc")
        assert osc["text"] == "cycle~"

    def test_saw_uses_phasor(self):
        boxes, _ = transport_lfo("tlfo", shape="saw")
        osc = _find_box(boxes, "tlfo_osc")
        assert osc["text"] == "phasor~"

    def test_square_uses_rect(self):
        boxes, _ = transport_lfo("tlfo", shape="square")
        osc = _find_box(boxes, "tlfo_osc")
        assert osc["text"] == "rect~"

    def test_invalid_division_raises(self):
        with pytest.raises(ValueError, match="Unknown division"):
            transport_lfo("tlfo", division="1/3")

    def test_invalid_shape_raises(self):
        with pytest.raises(ValueError, match="Unknown shape"):
            transport_lfo("tlfo", shape="triangle")

    def test_rate_feeds_osc(self):
        _, lines = transport_lfo("tlfo")
        assert any(
            l["patchline"]["source"] == ["tlfo_rate", 0]
            and l["patchline"]["destination"] == ["tlfo_osc", 0]
            for l in lines
        )

    def test_division_changes_rate_expr(self):
        boxes1, _ = transport_lfo("tlfo", division="1/8")
        boxes2, _ = transport_lfo("tlfo", division="1/1")
        r1 = _find_box(boxes1, "tlfo_rate")["text"]
        r2 = _find_box(boxes2, "tlfo_rate")["text"]
        assert r1 != r2

    def test_ids_use_prefix(self):
        boxes, _ = transport_lfo("mysync")
        ids = _box_ids(boxes)
        assert "mysync_transport" in ids
        assert "mysync_osc" in ids


class TestPitchbendIn:
    def test_returns_2_boxes_1_line(self):
        boxes, lines = pitchbend_in("pb")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_bendin(self):
        boxes, _ = pitchbend_in("pb")
        b = _find_box(boxes, "pb_bendin")
        assert b["text"] == "bendin"
        assert b["numoutlets"] == 2

    def test_has_scale_expr(self):
        boxes, _ = pitchbend_in("pb")
        s = _find_box(boxes, "pb_scale")
        assert "expr" in s["text"]
        assert "8192" in s["text"]

    def test_default_semitones_in_expr(self):
        boxes, _ = pitchbend_in("pb")
        s = _find_box(boxes, "pb_scale")
        assert "2" in s["text"]

    def test_custom_semitones(self):
        boxes, _ = pitchbend_in("pb", semitones=12)
        s = _find_box(boxes, "pb_scale")
        assert "12" in s["text"]

    def test_bendin_feeds_scale(self):
        _, lines = pitchbend_in("pb")
        assert any(
            l["patchline"]["source"] == ["pb_bendin", 0]
            and l["patchline"]["destination"] == ["pb_scale", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = pitchbend_in("mypb")
        ids = _box_ids(boxes)
        assert "mypb_bendin" in ids
        assert "mypb_scale" in ids


class TestModwheelIn:
    def test_returns_1_box_0_lines(self):
        boxes, lines = modwheel_in("mw")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_ctlin_1(self):
        boxes, _ = modwheel_in("mw")
        b = _find_box(boxes, "mw_ctlin")
        assert b["text"] == "ctlin 1"

    def test_three_outlets(self):
        boxes, _ = modwheel_in("mw")
        b = _find_box(boxes, "mw_ctlin")
        assert b["numoutlets"] == 3

    def test_ids_use_prefix(self):
        boxes, _ = modwheel_in("mymod")
        assert "mymod_ctlin" in _box_ids(boxes)


class TestAftertouchIn:
    def test_returns_1_box_0_lines(self):
        boxes, lines = aftertouch_in("at")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_touchin(self):
        boxes, _ = aftertouch_in("at")
        b = _find_box(boxes, "at_touchin")
        assert b["text"] == "touchin"

    def test_two_outlets(self):
        boxes, _ = aftertouch_in("at")
        b = _find_box(boxes, "at_touchin")
        assert b["numoutlets"] == 2

    def test_ids_use_prefix(self):
        boxes, _ = aftertouch_in("myat")
        assert "myat_touchin" in _box_ids(boxes)


class TestXfadeMatrix:
    def test_returns_boxes_and_lines(self):
        boxes, lines = xfade_matrix("xf")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_ctrl_input(self):
        boxes, _ = xfade_matrix("xf")
        ids = _box_ids(boxes)
        assert "xf_ctrl" in ids

    def test_has_weight_objects(self):
        boxes, _ = xfade_matrix("xf", sources=4)
        ids = _box_ids(boxes)
        for i in range(4):
            assert f"xf_wt_{i}" in ids

    def test_has_mul_objects(self):
        boxes, _ = xfade_matrix("xf", sources=4)
        ids = _box_ids(boxes)
        for i in range(4):
            assert f"xf_mul_{i}" in ids

    def test_has_sum_output(self):
        boxes, _ = xfade_matrix("xf", sources=4)
        ids = _box_ids(boxes)
        assert "xf_sum" in ids

    def test_ctrl_line_feeds_weights(self):
        _, lines = xfade_matrix("xf", sources=2)
        assert any(
            l["patchline"]["source"] == ["xf_ctrl_line", 0]
            and "xf_wt_" in l["patchline"]["destination"][0]
            for l in lines
        )

    def test_single_source(self):
        boxes, lines = xfade_matrix("xf", sources=1)
        assert "xf_sum" in _box_ids(boxes)

    def test_ids_use_prefix(self):
        boxes, _ = xfade_matrix("myxf", sources=2)
        ids = _box_ids(boxes)
        assert "myxf_wt_0" in ids
        assert "myxf_mul_0" in ids
        assert "myxf_sum" in ids


class TestMidiLearnChain:
    def test_returns_boxes_and_lines(self):
        boxes, lines = midi_learn_chain("ml", "my_param")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_ctlin(self):
        boxes, _ = midi_learn_chain("ml", "p")
        b = _find_box(boxes, "ml_ctlin")
        assert b["text"] == "ctlin"

    def test_has_learn_toggle(self):
        boxes, _ = midi_learn_chain("ml", "p")
        b = _find_box(boxes, "ml_learn")
        assert b["text"] == "toggle"

    def test_has_send_with_param_name(self):
        boxes, _ = midi_learn_chain("ml", "cutoff")
        b = _find_box(boxes, "ml_send")
        assert "send cutoff" in b["text"]

    def test_has_gate_and_store(self):
        boxes, _ = midi_learn_chain("ml", "p")
        ids = _box_ids(boxes)
        assert "ml_gate" in ids
        assert "ml_cc_store" in ids

    def test_ids_use_prefix(self):
        boxes, _ = midi_learn_chain("myml", "p")
        ids = _box_ids(boxes)
        assert "myml_ctlin" in ids
        assert "myml_send" in ids


class TestConvolver:
    def test_returns_2_boxes_0_lines(self):
        boxes, lines = convolver("cv")
        assert len(boxes) == 2
        assert len(lines) == 0

    def test_has_buffer(self):
        boxes, _ = convolver("cv")
        b = _find_box(boxes, "cv_ir_buf")
        assert "buffer~" in b["text"]

    def test_has_convolve(self):
        boxes, _ = convolver("cv")
        b = _find_box(boxes, "cv_conv")
        assert "convolve~" in b["text"]

    def test_default_ir_buffer_name(self):
        boxes, _ = convolver("cv")
        buf = _find_box(boxes, "cv_ir_buf")
        assert "ir_buf" in buf["text"]
        conv = _find_box(boxes, "cv_conv")
        assert "ir_buf" in conv["text"]

    def test_custom_ir_buffer_name(self):
        boxes, _ = convolver("cv", ir_buffer="my_ir")
        buf = _find_box(boxes, "cv_ir_buf")
        assert "my_ir" in buf["text"]
        conv = _find_box(boxes, "cv_conv")
        assert "my_ir" in conv["text"]

    def test_convolve_has_signal_outlet(self):
        boxes, _ = convolver("cv")
        b = _find_box(boxes, "cv_conv")
        assert b["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = convolver("mycv")
        ids = _box_ids(boxes)
        assert "mycv_ir_buf" in ids
        assert "mycv_conv" in ids


class TestProgramChangeIn:
    def test_returns_1_box_0_lines(self):
        boxes, lines = program_change_in("pc")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_default_all_channels(self):
        boxes, _ = program_change_in("pc")
        b = _find_box(boxes, "pc_pgmin")
        assert b["text"] == "pgmin"

    def test_specific_channel(self):
        boxes, _ = program_change_in("pc", channel=3)
        b = _find_box(boxes, "pc_pgmin")
        assert b["text"] == "pgmin 3"

    def test_two_outlets(self):
        boxes, _ = program_change_in("pc")
        b = _find_box(boxes, "pc_pgmin")
        assert b["numoutlets"] == 2

    def test_ids_use_prefix(self):
        boxes, _ = program_change_in("mypc")
        assert "mypc_pgmin" in _box_ids(boxes)


class TestBankSelectIn:
    def test_returns_4_boxes_3_lines(self):
        boxes, lines = bank_select_in("bs")
        assert len(boxes) == 4
        assert len(lines) == 3

    def test_has_msb_ctlin(self):
        boxes, _ = bank_select_in("bs")
        b = _find_box(boxes, "bs_msb")
        assert "ctlin 0" in b["text"]

    def test_has_lsb_ctlin(self):
        boxes, _ = bank_select_in("bs")
        b = _find_box(boxes, "bs_lsb")
        assert "ctlin 32" in b["text"]

    def test_has_bank_expr(self):
        boxes, _ = bank_select_in("bs")
        b = _find_box(boxes, "bs_bank")
        assert "expr" in b["text"]
        assert "128" in b["text"]

    def test_msb_feeds_store(self):
        _, lines = bank_select_in("bs")
        assert any(
            l["patchline"]["source"] == ["bs_msb", 0]
            and l["patchline"]["destination"] == ["bs_msb_store", 0]
            for l in lines
        )

    def test_store_feeds_bank_expr(self):
        _, lines = bank_select_in("bs")
        assert any(
            l["patchline"]["source"] == ["bs_msb_store", 0]
            and l["patchline"]["destination"] == ["bs_bank", 0]
            for l in lines
        )

    def test_lsb_feeds_bank_expr(self):
        _, lines = bank_select_in("bs")
        assert any(
            l["patchline"]["source"] == ["bs_lsb", 0]
            and l["patchline"]["destination"] == ["bs_bank", 1]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = bank_select_in("mybs")
        ids = _box_ids(boxes)
        assert "mybs_msb" in ids
        assert "mybs_lsb" in ids
        assert "mybs_bank" in ids


class TestSampleAndHoldTriggered:
    def test_returns_1_box_0_lines(self):
        boxes, lines = sample_and_hold_triggered("sht")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_samphold(self):
        boxes, _ = sample_and_hold_triggered("sht")
        b = _find_box(boxes, "sht_sah")
        assert b["text"] == "samphold~"

    def test_two_inlets(self):
        boxes, _ = sample_and_hold_triggered("sht")
        b = _find_box(boxes, "sht_sah")
        assert b["numinlets"] == 2

    def test_signal_outlet(self):
        boxes, _ = sample_and_hold_triggered("sht")
        b = _find_box(boxes, "sht_sah")
        assert b["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = sample_and_hold_triggered("mysht")
        assert "mysht_sah" in _box_ids(boxes)


class TestBitcrusher:
    def test_returns_1_box_0_lines(self):
        boxes, lines = bitcrusher("bc")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_degrade(self):
        boxes, _ = bitcrusher("bc")
        b = _find_box(boxes, "bc_degrade")
        assert "degrade~" in b["text"]

    def test_default_bits_in_text(self):
        boxes, _ = bitcrusher("bc")
        b = _find_box(boxes, "bc_degrade")
        assert "8" in b["text"]

    def test_default_rate_reduction_in_text(self):
        boxes, _ = bitcrusher("bc")
        b = _find_box(boxes, "bc_degrade")
        assert "1" in b["text"]

    def test_custom_bits(self):
        boxes, _ = bitcrusher("bc", bits=4)
        b = _find_box(boxes, "bc_degrade")
        assert "4" in b["text"]

    def test_custom_rate_reduction(self):
        boxes, _ = bitcrusher("bc", rate_reduction=4)
        b = _find_box(boxes, "bc_degrade")
        assert "4" in b["text"]

    def test_three_inlets(self):
        boxes, _ = bitcrusher("bc")
        b = _find_box(boxes, "bc_degrade")
        assert b["numinlets"] == 3

    def test_signal_outlet(self):
        boxes, _ = bitcrusher("bc")
        b = _find_box(boxes, "bc_degrade")
        assert b["outlettype"] == ["signal"]

    def test_ids_use_prefix(self):
        boxes, _ = bitcrusher("mybc")
        assert "mybc_degrade" in _box_ids(boxes)


class TestPolyVoices:
    def test_returns_1_box_0_lines(self):
        boxes, lines = poly_voices("pv")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_poly_object(self):
        boxes, _ = poly_voices("pv")
        b = _find_box(boxes, "pv_poly")
        assert "poly~" in b["text"]

    def test_default_patch_name(self):
        boxes, _ = poly_voices("pv")
        b = _find_box(boxes, "pv_poly")
        assert "voice" in b["text"]

    def test_default_num_voices(self):
        boxes, _ = poly_voices("pv")
        b = _find_box(boxes, "pv_poly")
        assert "4" in b["text"]

    def test_custom_voices(self):
        boxes, _ = poly_voices("pv", num_voices=8)
        b = _find_box(boxes, "pv_poly")
        assert "8" in b["text"]

    def test_custom_patch_name(self):
        boxes, _ = poly_voices("pv", patch_name="mysynth")
        b = _find_box(boxes, "pv_poly")
        assert "mysynth" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = poly_voices("mypv")
        assert "mypv_poly" in _box_ids(boxes)


class TestSpectralCrossover:
    def test_returns_1_box_0_lines(self):
        boxes, lines = spectral_crossover("sc")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_pfft_object(self):
        boxes, _ = spectral_crossover("sc")
        b = _find_box(boxes, "sc_pfft")
        assert "pfft~" in b["text"]
        assert "spectral_crossover_sub.maxpat" in b["text"]

    def test_default_4_bands(self):
        boxes, _ = spectral_crossover("sc")
        b = _find_box(boxes, "sc_pfft")
        assert b["numoutlets"] == 4

    def test_custom_bands(self):
        boxes, _ = spectral_crossover("sc", bands=8)
        b = _find_box(boxes, "sc_pfft")
        assert b["numoutlets"] == 8

    def test_ids_use_prefix(self):
        boxes, _ = spectral_crossover("mysc")
        assert "mysc_pfft" in _box_ids(boxes)


class TestSpectralCrossoverSubpatcher:
    def test_returns_dict_with_patcher_key(self):
        result = spectral_crossover_subpatcher()
        assert "patcher" in result

    def test_has_fftin(self):
        result = spectral_crossover_subpatcher()
        boxes = result["patcher"]["boxes"]
        texts = [b["box"]["text"] for b in boxes]
        assert any("fftin~" in t for t in texts)

    def test_has_fftout_per_band(self):
        result = spectral_crossover_subpatcher(bands=4)
        boxes = result["patcher"]["boxes"]
        fftout_boxes = [b for b in boxes if "fftout~" in b["box"]["text"]]
        assert len(fftout_boxes) == 4

    def test_custom_bands(self):
        result = spectral_crossover_subpatcher(bands=8)
        boxes = result["patcher"]["boxes"]
        fftout_boxes = [b for b in boxes if "fftout~" in b["box"]["text"]]
        assert len(fftout_boxes) == 8

    def test_has_cartopol(self):
        result = spectral_crossover_subpatcher()
        boxes = result["patcher"]["boxes"]
        texts = [b["box"]["text"] for b in boxes]
        assert any("cartopol~" in t for t in texts)

    def test_has_lines(self):
        result = spectral_crossover_subpatcher()
        assert len(result["patcher"]["lines"]) > 0


class TestGrainCloud:
    def test_returns_boxes_and_lines(self):
        boxes, lines = grain_cloud("gc", "my_sample")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_buffer(self):
        boxes, _ = grain_cloud("gc", "my_sample")
        b = _find_box(boxes, "gc_buf")
        assert "buffer~" in b["text"]
        assert "my_sample" in b["text"]

    def test_has_groove_instances(self):
        boxes, _ = grain_cloud("gc", "smp", num_voices=4)
        ids = _box_ids(boxes)
        for i in range(4):
            assert f"gc_groove_{i}" in ids

    def test_groove_uses_buffer_name(self):
        boxes, _ = grain_cloud("gc", "my_sample", num_voices=2)
        g = _find_box(boxes, "gc_groove_0")
        assert "my_sample" in g["text"]

    def test_has_sum_output(self):
        boxes, _ = grain_cloud("gc", "smp", num_voices=4)
        assert "gc_sum" in _box_ids(boxes)

    def test_single_voice(self):
        boxes, lines = grain_cloud("gc", "smp", num_voices=1)
        assert "gc_sum" in _box_ids(boxes)
        assert any(
            l["patchline"]["source"] == ["gc_groove_0", 0]
            and l["patchline"]["destination"] == ["gc_sum", 0]
            for l in lines
        )

    def test_groove_has_signal_outlet(self):
        boxes, _ = grain_cloud("gc", "smp", num_voices=2)
        g = _find_box(boxes, "gc_groove_0")
        assert "signal" in g["outlettype"][0]

    def test_ids_use_prefix(self):
        boxes, _ = grain_cloud("mygc", "s")
        ids = _box_ids(boxes)
        assert "mygc_buf" in ids
        assert "mygc_groove_0" in ids


class TestArpeggiatorExtendedModes:
    def test_converge_mode(self):
        boxes, _ = arpeggiator("arp", mode="converge")
        b = _find_box(boxes, "arp_arp")
        assert "arpeggiate converge" in b["text"]

    def test_diverge_mode(self):
        boxes, _ = arpeggiator("arp", mode="diverge")
        b = _find_box(boxes, "arp_arp")
        assert "arpeggiate diverge" in b["text"]

    def test_sweep_mode(self):
        boxes, _ = arpeggiator("arp", mode="sweep")
        b = _find_box(boxes, "arp_arp")
        assert "arpeggiate sweep" in b["text"]

    def test_original_modes_still_valid(self):
        for mode in ("up", "down", "up_down", "random", "as_played"):
            boxes, _ = arpeggiator("arp", mode=mode)
            b = _find_box(boxes, "arp_arp")
            assert f"arpeggiate {mode}" in b["text"]

    def test_invalid_mode_still_raises(self):
        with pytest.raises(ValueError, match="Unknown arpeggiator mode"):
            arpeggiator("arp", mode="zigzag")


class TestAutoGain:
    def test_returns_boxes_and_lines(self):
        boxes, lines = auto_gain("ag")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_env(self):
        boxes, _ = auto_gain("ag")
        b = _find_box(boxes, "ag_env")
        assert "env~" in b["text"]

    def test_has_mul(self):
        boxes, _ = auto_gain("ag")
        b = _find_box(boxes, "ag_mul")
        assert "*~" in b["text"]

    def test_mul_has_signal_outlet(self):
        boxes, _ = auto_gain("ag")
        b = _find_box(boxes, "ag_mul")
        assert "signal" in b["outlettype"][0]

    def test_ids_use_prefix(self):
        boxes, _ = auto_gain("mygain")
        ids = _box_ids(boxes)
        assert "mygain_env" in ids
        assert "mygain_mul" in ids


class TestMidiClockOut:
    def test_returns_boxes_and_lines(self):
        boxes, lines = midi_clock_out("mc")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_transport(self):
        boxes, _ = midi_clock_out("mc")
        b = _find_box(boxes, "mc_transport")
        assert "transport" in b["text"]

    def test_has_midiout(self):
        boxes, _ = midi_clock_out("mc")
        b = _find_box(boxes, "mc_midiout")
        assert "midiout" in b["text"]

    def test_has_metro(self):
        boxes, _ = midi_clock_out("mc")
        b = _find_box(boxes, "mc_metro")
        assert "metro" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = midi_clock_out("clk")
        ids = _box_ids(boxes)
        assert "clk_transport" in ids
        assert "clk_midiout" in ids


class TestMacromap:
    def test_returns_boxes_and_lines(self):
        boxes, lines = macromap("mm", "MyParam")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_remote(self):
        boxes, _ = macromap("mm", "MyParam")
        b = _find_box(boxes, "mm_remote")
        assert "live.remote~" in b["text"]
        assert "macro1" in b["text"]

    def test_macro_num_param(self):
        boxes, _ = macromap("mm", "MyParam", macro_num=5)
        b = _find_box(boxes, "mm_remote")
        assert "macro5" in b["text"]

    def test_has_param(self):
        boxes, _ = macromap("mm", "Cutoff")
        b = _find_box(boxes, "mm_param")
        assert "live.param~" in b["text"]
        assert "Cutoff" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = macromap("mymap", "Gain")
        ids = _box_ids(boxes)
        assert "mymap_remote" in ids
        assert "mymap_param" in ids


class TestStftPhaseVocoder:
    def test_returns_boxes_no_lines(self):
        boxes, lines = stft_phase_vocoder("pv")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_pfft(self):
        boxes, _ = stft_phase_vocoder("pv")
        b = _find_box(boxes, "pv_pfft")
        assert "pfft~" in b["text"]
        assert "phase_vocoder_sub.maxpat" in b["text"]

    def test_pfft_signal_outlet(self):
        boxes, _ = stft_phase_vocoder("pv")
        b = _find_box(boxes, "pv_pfft")
        assert "signal" in b["outlettype"][0]

    def test_ids_use_prefix(self):
        boxes, _ = stft_phase_vocoder("mypv")
        assert "mypv_pfft" in _box_ids(boxes)


class TestPhaseVocoderSubpatcher:
    def test_returns_dict_with_patcher(self):
        result = phase_vocoder_subpatcher()
        assert "patcher" in result

    def test_has_fftin(self):
        result = phase_vocoder_subpatcher()
        texts = [b["box"]["text"] for b in result["patcher"]["boxes"]]
        assert any("fftin~" in t for t in texts)

    def test_has_fftout(self):
        result = phase_vocoder_subpatcher()
        texts = [b["box"]["text"] for b in result["patcher"]["boxes"]]
        assert any("fftout~" in t for t in texts)

    def test_has_phase_acc(self):
        result = phase_vocoder_subpatcher()
        texts = [b["box"]["text"] for b in result["patcher"]["boxes"]]
        assert any("+~" in t for t in texts)

    def test_has_lines(self):
        result = phase_vocoder_subpatcher()
        assert len(result["patcher"]["lines"]) > 0

    def test_has_cartopol(self):
        result = phase_vocoder_subpatcher()
        texts = [b["box"]["text"] for b in result["patcher"]["boxes"]]
        assert any("cartopol~" in t for t in texts)


class TestSpectrumBandExtract:
    def test_returns_boxes_and_lines(self):
        boxes, lines = spectrum_band_extract("sbe")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_highpass(self):
        boxes, _ = spectrum_band_extract("sbe")
        b = _find_box(boxes, "sbe_hp")
        assert "hip~" in b["text"]
        assert "200" in b["text"]

    def test_has_lowpass(self):
        boxes, _ = spectrum_band_extract("sbe")
        b = _find_box(boxes, "sbe_lp")
        assert "lop~" in b["text"]
        assert "2000" in b["text"]

    def test_custom_freqs(self):
        boxes, _ = spectrum_band_extract("sbe", low_hz=500, high_hz=5000)
        hp = _find_box(boxes, "sbe_hp")
        lp = _find_box(boxes, "sbe_lp")
        assert "500" in hp["text"]
        assert "5000" in lp["text"]

    def test_hp_feeds_lp(self):
        _, lines = spectrum_band_extract("sbe")
        assert any(
            l["patchline"]["source"] == ["sbe_hp", 0]
            and l["patchline"]["destination"] == ["sbe_lp", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = spectrum_band_extract("band")
        ids = _box_ids(boxes)
        assert "band_hp" in ids
        assert "band_lp" in ids


class TestMorphingLfo:
    def test_returns_boxes_and_lines(self):
        boxes, lines = morphing_lfo("mlfo")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_phasor(self):
        boxes, _ = morphing_lfo("mlfo")
        b = _find_box(boxes, "mlfo_phasor")
        assert "phasor~" in b["text"]

    def test_has_sine(self):
        boxes, _ = morphing_lfo("mlfo")
        b = _find_box(boxes, "mlfo_sine")
        assert "cycle~" in b["text"]

    def test_has_selector(self):
        boxes, _ = morphing_lfo("mlfo")
        b = _find_box(boxes, "mlfo_sel")
        assert "selector~" in b["text"]

    def test_has_waveform_exprs(self):
        boxes, _ = morphing_lfo("mlfo")
        ids = _box_ids(boxes)
        assert "mlfo_tri" in ids
        assert "mlfo_sq" in ids
        assert "mlfo_saw" in ids

    def test_selector_has_signal_outlet(self):
        boxes, _ = morphing_lfo("mlfo")
        b = _find_box(boxes, "mlfo_sel")
        assert "signal" in b["outlettype"][0]

    def test_ids_use_prefix(self):
        boxes, _ = morphing_lfo("myx")
        ids = _box_ids(boxes)
        assert "myx_phasor" in ids
        assert "myx_sel" in ids


class TestMidiClockIn:
    def test_returns_boxes_and_lines(self):
        boxes, lines = midi_clock_in("mci")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_midiin(self):
        boxes, _ = midi_clock_in("mci")
        b = _find_box(boxes, "mci_midiin")
        assert "midiin" in b["text"]

    def test_has_midiparse(self):
        boxes, _ = midi_clock_in("mci")
        b = _find_box(boxes, "mci_midiparse")
        assert "midiparse" in b["text"]

    def test_has_clockdet(self):
        boxes, _ = midi_clock_in("mci")
        b = _find_box(boxes, "mci_clockdet")
        assert "248" in b["text"]

    def test_has_bpm_scale(self):
        boxes, _ = midi_clock_in("mci")
        b = _find_box(boxes, "mci_bpm_scale")
        assert "60" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = midi_clock_in("ck")
        ids = _box_ids(boxes)
        assert "ck_midiin" in ids
        assert "ck_bpm_scale" in ids


class TestSidechainRouting:
    def test_returns_boxes_no_lines(self):
        boxes, lines = sidechain_routing("sc")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_has_plugin(self):
        boxes, _ = sidechain_routing("sc")
        b = _find_box(boxes, "sc_plugin")
        assert "plugin~" in b["text"]

    def test_plugin_has_4_outlets(self):
        boxes, _ = sidechain_routing("sc")
        b = _find_box(boxes, "sc_plugin")
        assert b["numoutlets"] == 4

    def test_ids_use_prefix(self):
        boxes, _ = sidechain_routing("mysc")
        assert "mysc_plugin" in _box_ids(boxes)


class TestRandomWalk:
    def test_returns_boxes_and_lines(self):
        boxes, lines = random_walk("rw")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_noise(self):
        boxes, _ = random_walk("rw")
        b = _find_box(boxes, "rw_noise")
        assert "noise~" in b["text"]

    def test_has_clip(self):
        boxes, _ = random_walk("rw")
        b = _find_box(boxes, "rw_clip")
        assert "clip~" in b["text"]

    def test_has_slide(self):
        boxes, _ = random_walk("rw")
        b = _find_box(boxes, "rw_slide")
        assert "slide~" in b["text"]

    def test_custom_step_size(self):
        boxes, _ = random_walk("rw", step_size=0.05)
        b = _find_box(boxes, "rw_scale")
        assert "0.05" in b["text"]

    def test_slide_has_signal_outlet(self):
        boxes, _ = random_walk("rw")
        b = _find_box(boxes, "rw_slide")
        assert "signal" in b["outlettype"][0]

    def test_ids_use_prefix(self):
        boxes, _ = random_walk("walk")
        ids = _box_ids(boxes)
        assert "walk_noise" in ids
        assert "walk_slide" in ids


class TestMatrixMixer:
    def test_returns_boxes_and_lines(self):
        boxes, lines = matrix_mixer("mx")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_gain_cells(self):
        boxes, _ = matrix_mixer("mx", inputs=2, outputs=2)
        ids = _box_ids(boxes)
        assert "mx_in_0_gain_0" in ids
        assert "mx_in_0_gain_1" in ids
        assert "mx_in_1_gain_0" in ids
        assert "mx_in_1_gain_1" in ids

    def test_gain_cells_count(self):
        boxes, _ = matrix_mixer("mx", inputs=3, outputs=3)
        gain_cells = [b for b in boxes if "_gain_" in b["box"]["id"]]
        assert len(gain_cells) == 9

    def test_has_output_nodes(self):
        boxes, _ = matrix_mixer("mx", inputs=2, outputs=2)
        ids = _box_ids(boxes)
        assert "mx_out_0" in ids
        assert "mx_out_1" in ids

    def test_output_has_signal_outlet(self):
        boxes, _ = matrix_mixer("mx", inputs=2, outputs=2)
        b = _find_box(boxes, "mx_out_0")
        assert "signal" in b["outlettype"][0]

    def test_default_4x4(self):
        boxes, _ = matrix_mixer("mx")
        gain_cells = [b for b in boxes if "_gain_" in b["box"]["id"]]
        assert len(gain_cells) == 16

    def test_ids_use_prefix(self):
        boxes, _ = matrix_mixer("mymx", inputs=2, outputs=2)
        ids = _box_ids(boxes)
        assert "mymx_in_0_gain_0" in ids
        assert "mymx_out_0" in ids


class TestCvRecorder:
    def test_returns_boxes_no_lines(self):
        boxes, lines = cv_recorder("cvr")
        assert len(boxes) == 3
        assert len(lines) == 0

    def test_has_buffer(self):
        boxes, _ = cv_recorder("cvr")
        b = _find_box(boxes, "cvr_table")
        assert "buffer~" in b["text"]

    def test_has_record(self):
        boxes, _ = cv_recorder("cvr")
        b = _find_box(boxes, "cvr_rec")
        assert "record~" in b["text"]

    def test_has_play(self):
        boxes, _ = cv_recorder("cvr")
        b = _find_box(boxes, "cvr_play")
        assert "play~" in b["text"]

    def test_play_has_signal_outlet(self):
        boxes, _ = cv_recorder("cvr")
        b = _find_box(boxes, "cvr_play")
        assert "signal" in b["outlettype"][0]

    def test_custom_buffer_size(self):
        boxes, _ = cv_recorder("cvr", buffer_size=8820)
        b = _find_box(boxes, "cvr_table")
        assert "8820" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = cv_recorder("rec")
        ids = _box_ids(boxes)
        assert "rec_table" in ids
        assert "rec_rec" in ids
        assert "rec_play" in ids


class TestQuantizeTime:
    def test_returns_boxes_and_lines(self):
        boxes, lines = quantize_time("qt")
        assert len(boxes) == 2
        assert len(lines) == 1

    def test_has_transport(self):
        boxes, _ = quantize_time("qt")
        b = _find_box(boxes, "qt_transport")
        assert "transport" in b["text"]

    def test_has_quantize(self):
        boxes, _ = quantize_time("qt")
        b = _find_box(boxes, "qt_quant")
        assert "quantize" in b["text"]
        assert "1/16" in b["text"]

    def test_custom_division(self):
        boxes, _ = quantize_time("qt", division="1/8")
        b = _find_box(boxes, "qt_quant")
        assert "1/8" in b["text"]

    def test_transport_feeds_quant(self):
        _, lines = quantize_time("qt")
        assert any(
            l["patchline"]["source"] == ["qt_transport", 0]
            and l["patchline"]["destination"] == ["qt_quant", 0]
            for l in lines
        )

    def test_ids_use_prefix(self):
        boxes, _ = quantize_time("myqt")
        ids = _box_ids(boxes)
        assert "myqt_transport" in ids
        assert "myqt_quant" in ids


class TestMacroModulationMatrix:
    def test_returns_boxes_and_lines(self):
        boxes, lines = macro_modulation_matrix("mmm")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_source_cells(self):
        boxes, _ = macro_modulation_matrix("mmm", sources=2, targets=2)
        ids = _box_ids(boxes)
        assert "mmm_src_0_to_0" in ids
        assert "mmm_src_0_to_1" in ids
        assert "mmm_src_1_to_0" in ids

    def test_has_target_outputs(self):
        boxes, _ = macro_modulation_matrix("mmm", sources=2, targets=2)
        ids = _box_ids(boxes)
        assert "mmm_tgt_0" in ids
        assert "mmm_tgt_1" in ids

    def test_cell_count(self):
        boxes, _ = macro_modulation_matrix("mmm", sources=3, targets=3)
        cells = [b for b in boxes if "_to_" in b["box"]["id"]]
        assert len(cells) == 9

    def test_target_has_signal_outlet(self):
        boxes, _ = macro_modulation_matrix("mmm", sources=2, targets=2)
        b = _find_box(boxes, "mmm_tgt_0")
        assert "signal" in b["outlettype"][0]

    def test_default_4x4(self):
        boxes, _ = macro_modulation_matrix("mmm")
        cells = [b for b in boxes if "_to_" in b["box"]["id"]]
        assert len(cells) == 16

    def test_ids_use_prefix(self):
        boxes, _ = macro_modulation_matrix("mymod", sources=2, targets=2)
        ids = _box_ids(boxes)
        assert "mymod_src_0_to_0" in ids
        assert "mymod_tgt_0" in ids


class TestAnalogOscillatorBank:
    def test_returns_boxes_and_lines(self):
        boxes, lines = analog_oscillator_bank("aob")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_phasors(self):
        boxes, _ = analog_oscillator_bank("aob", num_oscs=4)
        ids = _box_ids(boxes)
        for i in range(4):
            assert f"aob_osc_{i}" in ids

    def test_phasor_signal_outlet(self):
        boxes, _ = analog_oscillator_bank("aob", num_oscs=2)
        b = _find_box(boxes, "aob_osc_0")
        assert "signal" in b["outlettype"][0]

    def test_has_detune_exprs(self):
        boxes, _ = analog_oscillator_bank("aob", num_oscs=4)
        ids = _box_ids(boxes)
        for i in range(4):
            assert f"aob_detune_{i}" in ids

    def test_has_sum_output(self):
        boxes, _ = analog_oscillator_bank("aob", num_oscs=4)
        assert "aob_sum" in _box_ids(boxes)

    def test_single_osc(self):
        boxes, lines = analog_oscillator_bank("aob", num_oscs=1)
        assert "aob_osc_0" in _box_ids(boxes)
        assert "aob_sum" in _box_ids(boxes)

    def test_detune_offset_zero_for_center(self):
        boxes, _ = analog_oscillator_bank("aob", num_oscs=1)
        b = _find_box(boxes, "aob_detune_0")
        assert "0.0000" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = analog_oscillator_bank("myosc", num_oscs=2)
        ids = _box_ids(boxes)
        assert "myosc_osc_0" in ids
        assert "myosc_sum" in ids


class TestLfsrGenerator:
    def test_returns_boxes_and_lines(self):
        boxes, lines = lfsr_generator("lfsr")
        assert len(boxes) > 0
        assert len(lines) > 0

    def test_has_reg(self):
        boxes, _ = lfsr_generator("lfsr")
        b = _find_box(boxes, "lfsr_reg")
        assert "i" in b["text"]

    def test_has_bit_output(self):
        boxes, _ = lfsr_generator("lfsr")
        b = _find_box(boxes, "lfsr_bit")
        assert "bitand" in b["text"]

    def test_has_feedback(self):
        boxes, _ = lfsr_generator("lfsr")
        b = _find_box(boxes, "lfsr_feedback")
        assert "expr" in b["text"]

    def test_has_shift(self):
        boxes, _ = lfsr_generator("lfsr")
        b = _find_box(boxes, "lfsr_shift")
        assert "expr" in b["text"]

    def test_has_clock(self):
        boxes, _ = lfsr_generator("lfsr")
        b = _find_box(boxes, "lfsr_clock")
        assert "t b b" in b["text"]

    def test_custom_poly_order(self):
        boxes, _ = lfsr_generator("lfsr", poly_order=16)
        b = _find_box(boxes, "lfsr_reg")
        assert str((1 << 16) - 1) in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = lfsr_generator("mylfsr")
        ids = _box_ids(boxes)
        assert "mylfsr_reg" in ids
        assert "mylfsr_bit" in ids


class TestCvSmoothLag:
    def test_exponential_mode(self):
        boxes, lines = cv_smooth_lag("lag")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_exponential_uses_slide(self):
        boxes, _ = cv_smooth_lag("lag", lag_ms=50)
        b = _find_box(boxes, "lag_smoother")
        assert "slide~" in b["text"]
        assert "50" in b["text"]

    def test_linear_mode(self):
        boxes, lines = cv_smooth_lag("lag", mode="linear")
        assert len(boxes) == 1
        assert len(lines) == 0

    def test_linear_uses_line(self):
        boxes, _ = cv_smooth_lag("lag", lag_ms=100, mode="linear")
        b = _find_box(boxes, "lag_smoother")
        assert "line~" in b["text"]
        assert "100" in b["text"]

    def test_smoother_signal_outlet_exponential(self):
        boxes, _ = cv_smooth_lag("lag")
        b = _find_box(boxes, "lag_smoother")
        assert "signal" in b["outlettype"][0]

    def test_smoother_signal_outlet_linear(self):
        boxes, _ = cv_smooth_lag("lag", mode="linear")
        b = _find_box(boxes, "lag_smoother")
        assert "signal" in b["outlettype"][0]

    def test_custom_lag_ms(self):
        boxes, _ = cv_smooth_lag("lag", lag_ms=200)
        b = _find_box(boxes, "lag_smoother")
        assert "200" in b["text"]

    def test_ids_use_prefix(self):
        boxes, _ = cv_smooth_lag("mylag")
        assert "mylag_smoother" in _box_ids(boxes)
