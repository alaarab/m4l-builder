"""Tests for pre-wired DSP combo recipes."""

from m4l_builder import AudioEffect
from m4l_builder.recipes import (
    gain_controlled_stage,
    dry_wet_stage,
    tempo_synced_delay,
    midi_note_gate,
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
