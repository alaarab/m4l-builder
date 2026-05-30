"""Tests for the generative MIDI building blocks and recipe."""

import pytest

from m4l_builder import MidiEffect
from m4l_builder.dsp import euclidean_rhythm, probability_gate, random_note
from m4l_builder.recipes import generative_midi_stage


def _line_pairs(device):
    return {
        (line["patchline"]["source"][0], line["patchline"]["destination"][0])
        for line in device.lines
    }


def _texts(boxes):
    return {b["box"]["id"]: b["box"]["text"] for b in boxes}


class TestProbabilityGate:
    def test_structure(self):
        boxes, lines = probability_gate("g", probability=0.5)
        assert [b["box"]["id"] for b in boxes] == ["g_gate", "g_thresh", "g_sel"]
        pairs = {(ln["patchline"]["source"][0], ln["patchline"]["destination"][0])
                 for ln in lines}
        assert ("g_gate", "g_thresh") in pairs
        assert ("g_thresh", "g_sel") in pairs

    def test_threshold_scales_with_probability(self):
        boxes, _ = probability_gate("g", probability=0.25)
        assert _texts(boxes)["g_thresh"] == "< 250"

    def test_invalid_probability_raises(self):
        with pytest.raises(ValueError):
            probability_gate("g", probability=1.5)


class TestRandomNote:
    def test_structure_and_range(self):
        boxes, _ = random_note("r", low=48, high=72)
        texts = _texts(boxes)
        assert texts["r_rand"] == "random 25"  # high - low + 1
        assert texts["r_offset"] == "+ 48"

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError):
            random_note("r", low=80, high=40)


class TestGenerativeMidiStage:
    def _build(self):
        device = MidiEffect("Gen", 260, 180)
        result = generative_midi_stage(
            device, "gen", [20, 30, 48, 48], [90, 30, 48, 48], scale="minor"
        )
        return device, result

    def test_returns_expected_keys(self):
        _, result = self._build()
        for key in ("enable", "rate", "density", "metro", "make", "noteout"):
            assert key in result

    def test_generative_chain_wired(self):
        device, _ = self._build()
        pairs = _line_pairs(device)
        for edge in [
            ("gen_enable", "gen_metro"),       # toggle starts the clock
            ("gen_metro", "gen_gate_gate"),    # clock -> probability gate
            ("gen_gate_sel", "gen_note_rand"), # hit -> random pitch
            ("gen_note_offset", "gen_quant_scale"),  # pitch -> scale quantize
            ("gen_quant_scale", "gen_make"),   # quantized pitch -> makenote
            ("gen_make", "gen_out_noteout"),   # makenote -> noteout
        ]:
            assert edge in pairs

    def test_builds_to_bytes(self):
        device, _ = self._build()
        assert device.to_bytes()[:4] == b"ampf"


class TestEuclideanRhythm:
    def test_even_distribution(self):
        boxes, _ = euclidean_rhythm("e", steps=16, pulses=4)
        sel = next(b["box"]["text"] for b in boxes if b["box"]["id"] == "e_sel")
        assert sel == "sel 0 4 8 12"

    def test_all_hits_merge_to_single_bang(self):
        _, lines = euclidean_rhythm("e", steps=16, pulses=5)
        sel_to_hit = [
            ln for ln in lines
            if ln["patchline"]["source"][0] == "e_sel"
            and ln["patchline"]["destination"][0] == "e_hit"
        ]
        assert len(sel_to_hit) == 5  # one per pulse

    def test_invalid_pulses_raises(self):
        with pytest.raises(ValueError):
            euclidean_rhythm("e", steps=4, pulses=8)
