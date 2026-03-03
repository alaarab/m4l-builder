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
