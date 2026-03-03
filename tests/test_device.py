"""Tests for the high-level Device API (device.py)."""

import json
import struct
import os

import pytest

from m4l_builder.device import Device, AudioEffect, Instrument, MidiEffect
from m4l_builder.constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_amxd_json(data: bytes) -> dict:
    """Extract and parse the JSON payload from an .amxd binary."""
    json_payload = data[32:].rstrip(b"\x00").rstrip(b"\n").decode("utf-8")
    return json.loads(json_payload)


# ---------------------------------------------------------------------------
# TestDevice – base class
# ---------------------------------------------------------------------------

class TestDevice:
    """Tests for the Device base class."""

    def _make(self, **kwargs):
        defaults = dict(name="TestDevice", width=400, height=170,
                        device_type="audio_effect")
        defaults.update(kwargs)
        return Device(**defaults)

    def test_init_name(self):
        d = self._make(name="MyDevice")
        assert d.name == "MyDevice"

    def test_init_width(self):
        d = self._make(width=600)
        assert d.width == 600

    def test_init_height(self):
        d = self._make(height=200)
        assert d.height == 200

    def test_init_device_type(self):
        d = self._make(device_type="midi_effect")
        assert d.device_type == "midi_effect"

    def test_init_empty_boxes(self):
        d = self._make()
        assert d.boxes == []

    def test_init_empty_lines(self):
        d = self._make()
        assert d.lines == []

    def test_add_box_appends(self):
        d = self._make()
        box = {"box": {"id": "obj-1", "maxclass": "newobj"}}
        d.add_box(box)
        assert len(d.boxes) == 1

    def test_add_box_returns_id(self):
        d = self._make()
        box = {"box": {"id": "obj-42", "maxclass": "newobj"}}
        returned_id = d.add_box(box)
        assert returned_id == "obj-42"

    def test_add_box_stores_exact_dict(self):
        d = self._make()
        box = {"box": {"id": "obj-1", "maxclass": "newobj"}}
        d.add_box(box)
        assert d.boxes[0] is box

    def test_add_line_appends(self):
        d = self._make()
        d.add_line("obj-1", 0, "obj-2", 0)
        assert len(d.lines) == 1

    def test_add_line_patchline_structure(self):
        d = self._make()
        d.add_line("obj-src", 1, "obj-dst", 2)
        line = d.lines[0]
        assert "patchline" in line
        assert line["patchline"]["source"] == ["obj-src", 1]
        assert line["patchline"]["destination"] == ["obj-dst", 2]

    def test_add_panel_returns_id(self):
        d = self._make()
        returned_id = d.add_panel("panel-bg", [0, 0, 400, 170],
                                  bgcolor=[0.1, 0.1, 0.1, 1.0])
        assert returned_id == "panel-bg"

    def test_add_panel_appends_box(self):
        d = self._make()
        d.add_panel("panel-bg", [0, 0, 400, 170], bgcolor=[0.1, 0.1, 0.1, 1.0])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["id"] == "panel-bg"

    def test_add_panel_maxclass(self):
        d = self._make()
        d.add_panel("p1", [0, 0, 200, 100], bgcolor=[0, 0, 0, 1])
        assert d.boxes[0]["box"]["maxclass"] == "panel"

    def test_add_dial_returns_id(self):
        d = self._make()
        returned_id = d.add_dial("dial-gain", "Gain", [10, 10, 40, 40])
        assert returned_id == "dial-gain"

    def test_add_dial_appends_box(self):
        d = self._make()
        d.add_dial("dial-gain", "Gain", [10, 10, 40, 40])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.dial"

    def test_add_dial_varname(self):
        d = self._make()
        d.add_dial("d1", "MyParam", [0, 0, 40, 40])
        assert d.boxes[0]["box"]["varname"] == "MyParam"

    def test_add_tab_returns_id(self):
        d = self._make()
        returned_id = d.add_tab("tab-mode", "Mode", [0, 0, 120, 24],
                                options=["A", "B", "C"])
        assert returned_id == "tab-mode"

    def test_add_tab_appends_box(self):
        d = self._make()
        d.add_tab("t1", "Mode", [0, 0, 120, 24], options=["X", "Y"])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.tab"

    def test_add_tab_options_stored(self):
        d = self._make()
        d.add_tab("t1", "Mode", [0, 0, 120, 24], options=["Low", "Mid", "High"])
        attrs = d.boxes[0]["box"]["saved_attribute_attributes"]["valueof"]
        assert attrs["parameter_enum"] == "Low Mid High"

    def test_add_toggle_returns_id(self):
        d = self._make()
        returned_id = d.add_toggle("tog-bypass", "Bypass", [0, 0, 24, 24])
        assert returned_id == "tog-bypass"

    def test_add_toggle_appends_box(self):
        d = self._make()
        d.add_toggle("tog-bypass", "Bypass", [0, 0, 24, 24])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.toggle"

    def test_add_comment_returns_id(self):
        d = self._make()
        returned_id = d.add_comment("lbl-1", [0, 0, 80, 16], "Hello")
        assert returned_id == "lbl-1"

    def test_add_comment_appends_box(self):
        d = self._make()
        d.add_comment("lbl-1", [0, 0, 80, 16], "Hello")
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.comment"

    def test_add_comment_text(self):
        d = self._make()
        d.add_comment("lbl-1", [0, 0, 80, 16], "Label Text")
        assert d.boxes[0]["box"]["text"] == "Label Text"

    def test_add_scope_returns_id(self):
        d = self._make()
        returned_id = d.add_scope("scope-1", [0, 0, 120, 60])
        assert returned_id == "scope-1"

    def test_add_scope_appends_box(self):
        d = self._make()
        d.add_scope("scope-1", [0, 0, 120, 60])
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "live.scope~"

    def test_add_newobj_returns_id(self):
        d = self._make()
        returned_id = d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        assert returned_id == "obj-1"

    def test_add_newobj_appends_box(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        assert len(d.boxes) == 1
        assert d.boxes[0]["box"]["maxclass"] == "newobj"

    def test_add_newobj_text(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        assert d.boxes[0]["box"]["text"] == "gain~"

    def test_add_newobj_numinlets_numoutlets(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=3, numoutlets=2)
        box = d.boxes[0]["box"]
        assert box["numinlets"] == 3
        assert box["numoutlets"] == 2

    def test_to_patcher_returns_dict(self):
        d = self._make()
        result = d.to_patcher()
        assert isinstance(result, dict)
        assert "patcher" in result

    def test_to_patcher_name(self):
        d = self._make(name="MyFX")
        result = d.to_patcher()
        assert result["patcher"]["project"]["amxdtype"] == 1633771873

    def test_to_patcher_rect(self):
        d = self._make(width=500, height=250)
        result = d.to_patcher()
        assert result["patcher"]["openrect"] == [0.0, 0.0, 500, 250]

    def test_to_patcher_boxes_included(self):
        d = self._make()
        d.add_panel("p1", [0, 0, 200, 100], bgcolor=[0, 0, 0, 1])
        result = d.to_patcher()
        assert len(result["patcher"]["boxes"]) == 1

    def test_to_patcher_lines_included(self):
        d = self._make()
        d.add_newobj("obj-1", "gain~", numinlets=2, numoutlets=1)
        d.add_newobj("obj-2", "dac~", numinlets=2, numoutlets=0)
        d.add_line("obj-1", 0, "obj-2", 0)
        result = d.to_patcher()
        assert len(result["patcher"]["lines"]) == 1

    def test_to_bytes_returns_bytes(self):
        d = self._make()
        result = d.to_bytes()
        assert isinstance(result, bytes)

    def test_to_bytes_magic_header(self):
        d = self._make()
        result = d.to_bytes()
        assert result[:4] == b"ampf"

    def test_to_bytes_device_type_audio_effect(self):
        d = self._make(device_type="audio_effect")
        result = d.to_bytes()
        assert result[8:12] == b"aaaa"

    def test_to_bytes_device_type_instrument(self):
        d = self._make(device_type="instrument")
        result = d.to_bytes()
        assert result[8:12] == b"iiii"

    def test_to_bytes_device_type_midi_effect(self):
        d = self._make(device_type="midi_effect")
        result = d.to_bytes()
        assert result[8:12] == b"mmmm"

    def test_to_bytes_null_terminated(self):
        d = self._make()
        result = d.to_bytes()
        assert result[-1:] == b"\x00"

    def test_to_bytes_json_recoverable(self):
        d = self._make(name="RoundTrip")
        result = d.to_bytes()
        recovered = _parse_amxd_json(result)
        assert recovered["patcher"]["project"]["amxdtype"] == 1633771873

    def test_build_writes_file(self, tmp_path):
        d = self._make(name="WriteTest")
        output = str(tmp_path / "test.amxd")
        d.build(output)
        assert os.path.exists(output)

    def test_build_returns_byte_count(self, tmp_path):
        d = self._make()
        output = str(tmp_path / "test.amxd")
        count = d.build(output)
        assert count == os.path.getsize(output)

    def test_build_file_starts_with_ampf(self, tmp_path):
        d = self._make()
        output = str(tmp_path / "test.amxd")
        d.build(output)
        with open(output, "rb") as f:
            header = f.read(4)
        assert header == b"ampf"

    def test_build_file_valid_json_payload(self, tmp_path):
        d = self._make(name="FileTest")
        output = str(tmp_path / "test.amxd")
        d.build(output)
        with open(output, "rb") as f:
            data = f.read()
        recovered = _parse_amxd_json(data)
        assert recovered["patcher"]["project"]["amxdtype"] == 1633771873


# ---------------------------------------------------------------------------
# TestAudioEffect
# ---------------------------------------------------------------------------

class TestAudioEffect:
    """Tests for the AudioEffect subclass."""

    def test_device_type(self):
        fx = AudioEffect("FX", 400, 170)
        assert fx.device_type == "audio_effect"

    def test_auto_adds_two_boxes(self):
        fx = AudioEffect("FX", 400, 170)
        assert len(fx.boxes) == 2

    def test_auto_adds_no_lines(self):
        """stereo_io() returns an empty lines list."""
        fx = AudioEffect("FX", 400, 170)
        assert len(fx.lines) == 0

    def test_first_box_is_plugin_tilde(self):
        fx = AudioEffect("FX", 400, 170)
        assert fx.boxes[0]["box"]["text"] == "plugin~"

    def test_second_box_is_plugout_tilde(self):
        fx = AudioEffect("FX", 400, 170)
        assert fx.boxes[1]["box"]["text"] == "plugout~"

    def test_plugin_tilde_has_two_outlets(self):
        fx = AudioEffect("FX", 400, 170)
        plugin_box = fx.boxes[0]["box"]
        assert plugin_box["numoutlets"] == 2

    def test_plugin_tilde_outlet_types_are_signal(self):
        fx = AudioEffect("FX", 400, 170)
        plugin_box = fx.boxes[0]["box"]
        assert plugin_box["outlettype"] == ["signal", "signal"]

    def test_plugout_tilde_has_two_inlets(self):
        fx = AudioEffect("FX", 400, 170)
        plugout_box = fx.boxes[1]["box"]
        assert plugout_box["numinlets"] == 2

    def test_plugout_tilde_has_zero_outlets(self):
        fx = AudioEffect("FX", 400, 170)
        plugout_box = fx.boxes[1]["box"]
        assert plugout_box["numoutlets"] == 0

    def test_to_bytes_magic_bytes(self):
        fx = AudioEffect("FX", 400, 170)
        data = fx.to_bytes()
        assert data[:4] == b"ampf"

    def test_to_bytes_type_code_audio_effect(self):
        fx = AudioEffect("FX", 400, 170)
        data = fx.to_bytes()
        assert data[8:12] == b"aaaa"

    def test_add_box_after_init_increments_count(self):
        fx = AudioEffect("FX", 400, 170)
        fx.add_panel("bg", [0, 0, 400, 170], bgcolor=[0, 0, 0, 1])
        assert len(fx.boxes) == 3

    def test_patcher_contains_auto_boxes(self):
        fx = AudioEffect("FX", 400, 170)
        patcher = fx.to_patcher()
        assert len(patcher["patcher"]["boxes"]) == 2

    def test_build_writes_valid_file(self, tmp_path):
        fx = AudioEffect("FX", 400, 170)
        output = str(tmp_path / "fx.amxd")
        count = fx.build(output)
        assert count > 0
        assert os.path.exists(output)


# ---------------------------------------------------------------------------
# TestInstrument
# ---------------------------------------------------------------------------

class TestInstrument:
    """Tests for the Instrument subclass."""

    def test_device_type(self):
        inst = Instrument("Synth", 400, 170)
        assert inst.device_type == "instrument"

    def test_no_auto_boxes(self):
        inst = Instrument("Synth", 400, 170)
        assert len(inst.boxes) == 0

    def test_no_auto_lines(self):
        inst = Instrument("Synth", 400, 170)
        assert len(inst.lines) == 0

    def test_to_bytes_type_code_instrument(self):
        inst = Instrument("Synth", 400, 170)
        data = inst.to_bytes()
        assert data[8:12] == b"iiii"

    def test_to_bytes_magic_bytes(self):
        inst = Instrument("Synth", 400, 170)
        data = inst.to_bytes()
        assert data[:4] == b"ampf"

    def test_patcher_amxdtype(self):
        inst = Instrument("Synth", 400, 170)
        patcher = inst.to_patcher()
        # iiii as uint32 LE = 1768515945
        assert patcher["patcher"]["project"]["amxdtype"] == 1768515945

    def test_build_writes_file(self, tmp_path):
        inst = Instrument("Synth", 400, 170)
        output = str(tmp_path / "synth.amxd")
        count = inst.build(output)
        assert count > 0
        assert os.path.exists(output)


# ---------------------------------------------------------------------------
# TestMidiEffect
# ---------------------------------------------------------------------------

class TestMidiEffect:
    """Tests for the MidiEffect subclass."""

    def test_device_type(self):
        midi = MidiEffect("Arp", 400, 170)
        assert midi.device_type == "midi_effect"

    def test_no_auto_boxes(self):
        midi = MidiEffect("Arp", 400, 170)
        assert len(midi.boxes) == 0

    def test_no_auto_lines(self):
        midi = MidiEffect("Arp", 400, 170)
        assert len(midi.lines) == 0

    def test_to_bytes_type_code_midi_effect(self):
        midi = MidiEffect("Arp", 400, 170)
        data = midi.to_bytes()
        assert data[8:12] == b"mmmm"

    def test_to_bytes_magic_bytes(self):
        midi = MidiEffect("Arp", 400, 170)
        data = midi.to_bytes()
        assert data[:4] == b"ampf"

    def test_patcher_amxdtype(self):
        midi = MidiEffect("Arp", 400, 170)
        patcher = midi.to_patcher()
        # mmmm as uint32 LE = 1835887981
        assert patcher["patcher"]["project"]["amxdtype"] == 1835887981

    def test_build_writes_file(self, tmp_path):
        midi = MidiEffect("Arp", 400, 170)
        output = str(tmp_path / "arp.amxd")
        count = midi.build(output)
        assert count > 0
        assert os.path.exists(output)


# ---------------------------------------------------------------------------
# TestDeviceIntegration
# ---------------------------------------------------------------------------

class TestDeviceIntegration:
    """Integration tests building more complete devices."""

    def test_audio_effect_with_panel_and_dial(self, tmp_path):
        fx = AudioEffect("TestFX", 400, 170)
        fx.add_panel("bg", [0, 0, 400, 170], bgcolor=[0.15, 0.15, 0.17, 1.0])
        fx.add_dial("gain-dial", "Gain", [20, 20, 40, 40],
                    min_val=0.0, max_val=100.0, initial=75.0)
        data = fx.to_bytes()
        assert data[:4] == b"ampf"
        # 2 auto + 1 panel + 1 dial
        recovered = _parse_amxd_json(data)
        assert len(recovered["patcher"]["boxes"]) == 4

    def test_audio_effect_json_boxes_count(self):
        fx = AudioEffect("CountFX", 400, 170)
        fx.add_newobj("obj-gain-l", "*~ 1.", numinlets=2, numoutlets=1)
        # 2 auto + 1 newobj
        patcher = fx.to_patcher()
        assert len(patcher["patcher"]["boxes"]) == 3

    def test_audio_effect_wired_connection(self):
        fx = AudioEffect("WiredFX", 400, 170)
        # Wire plugin~ outlet 0 to plugout~ inlet 0
        fx.add_line("obj-plugin", 0, "obj-plugout", 0)
        fx.add_line("obj-plugin", 1, "obj-plugout", 1)
        patcher = fx.to_patcher()
        assert len(patcher["patcher"]["lines"]) == 2

    def test_instrument_with_multiple_ui_elements(self, tmp_path):
        inst = Instrument("MySynth", 500, 200)
        inst.add_panel("bg", [0, 0, 500, 200], bgcolor=[0.1, 0.1, 0.1, 1.0])
        inst.add_dial("osc-tune", "Tune", [10, 10, 40, 40],
                      min_val=-24.0, max_val=24.0, initial=0.0)
        inst.add_toggle("tog-mono", "Mono", [60, 10, 24, 24])
        inst.add_tab("tab-wave", "Waveform", [90, 10, 120, 24],
                     options=["Sine", "Saw", "Square"])
        output = str(tmp_path / "synth.amxd")
        count = inst.build(output)
        assert count > 0
        with open(output, "rb") as f:
            data = f.read()
        recovered = _parse_amxd_json(data)
        # 1 panel + 1 dial + 1 toggle + 1 tab
        assert len(recovered["patcher"]["boxes"]) == 4

    def test_midi_effect_build_round_trip(self, tmp_path):
        midi = MidiEffect("Randomizer", 300, 120)
        midi.add_comment("lbl-title", [10, 10, 150, 16], "MIDI Randomizer")
        midi.add_dial("d-chance", "Chance", [10, 40, 40, 40],
                      min_val=0.0, max_val=100.0, initial=50.0)
        output = str(tmp_path / "midi.amxd")
        midi.build(output)
        with open(output, "rb") as f:
            data = f.read()
        assert data[:4] == b"ampf"
        assert data[8:12] == b"mmmm"
        recovered = _parse_amxd_json(data)
        assert recovered["patcher"]["project"]["amxdtype"] == 1835887981  # mmmm
        assert len(recovered["patcher"]["boxes"]) == 2

    def test_build_byte_count_matches_to_bytes(self, tmp_path):
        fx = AudioEffect("ByteCount", 400, 170)
        output = str(tmp_path / "fx.amxd")
        written = fx.build(output)
        in_memory = fx.to_bytes()
        assert written == len(in_memory)
