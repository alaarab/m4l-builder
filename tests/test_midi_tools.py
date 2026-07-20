"""Tests for Live 12 MIDI Tools (Generator / Transformation) support.

The expected device-type codes and amxdtype integers were reverse-engineered
from real Live 12 MIDI Tool devices.
"""

import json

from m4l_builder import MidiGenerator, MidiTransformation, midi_tool_io
from m4l_builder.amxd import device_from_amxd


def _amxdtype(data: bytes) -> int:
    patcher = json.loads(data[32:].rstrip(b"\x00").rstrip(b"\n").decode("utf-8"))["patcher"]
    return patcher.get("project", {}).get("amxdtype")


class TestMidiToolDeviceTypes:
    def test_transformation_header_and_amxdtype(self):
        data = MidiTransformation("T", 200, 120).to_bytes()
        assert data[8:12] == b"natt"
        assert _amxdtype(data) == 1851880564

    def test_generator_header_and_amxdtype(self):
        data = MidiGenerator("G", 200, 120).to_bytes()
        assert data[8:12] == b"nagg"
        assert _amxdtype(data) == 1851877223

    def test_round_trip(self, tmp_path):
        for cls, dtype in [(MidiTransformation, "note_transformation"),
                           (MidiGenerator, "note_generator")]:
            path = tmp_path / f"{dtype}.amxd"
            cls("X", 200, 120).build(str(path))
            recovered = device_from_amxd(str(path))
            assert recovered.device_type == dtype
            assert type(recovered) is cls


class TestMidiToolIo:
    def test_creates_in_and_out_objects(self):
        boxes, _ = midi_tool_io("mt")
        objs = {b["box"]["id"]: b["box"]["text"] for b in boxes}
        assert objs["mt_in"] == "live.miditool.in"
        assert objs["mt_out"] == "live.miditool.out"

    def test_passthrough_builds(self):
        device = MidiTransformation("PT", 200, 120)
        device.add_dsp(*midi_tool_io("mt"))
        device.add_line("mt_in", 0, "mt_out", 0)
        assert device.to_bytes()[:4] == b"ampf"
