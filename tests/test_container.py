"""Tests for the binary .amxd container format."""

import json
import struct

from m4l_builder.container import build_amxd
from m4l_builder.constants import AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT


MINIMAL_PATCHER = {"patcher": {"fileversion": 1, "boxes": [], "lines": []}}


class TestBuildAmxd:
    """Test build_amxd produces correct binary output."""

    def test_magic_bytes(self):
        data = build_amxd(MINIMAL_PATCHER)
        assert data[:4] == b"ampf"

    def test_format_version(self):
        data = build_amxd(MINIMAL_PATCHER)
        version = struct.unpack_from("<I", data, 4)[0]
        assert version == 4

    def test_audio_effect_type(self):
        data = build_amxd(MINIMAL_PATCHER, AUDIO_EFFECT)
        assert data[8:12] == b"aaaa"

    def test_instrument_type(self):
        data = build_amxd(MINIMAL_PATCHER, INSTRUMENT)
        assert data[8:12] == b"iiii"

    def test_midi_effect_type(self):
        data = build_amxd(MINIMAL_PATCHER, MIDI_EFFECT)
        assert data[8:12] == b"mmmm"

    def test_meta_section(self):
        data = build_amxd(MINIMAL_PATCHER)
        assert data[12:16] == b"meta"
        meta_len = struct.unpack_from("<I", data, 16)[0]
        assert meta_len == 4
        assert data[20:24] == b"\x00\x00\x00\x00"

    def test_ptch_section_tag(self):
        data = build_amxd(MINIMAL_PATCHER)
        assert data[24:28] == b"ptch"

    def test_json_null_terminated(self):
        data = build_amxd(MINIMAL_PATCHER)
        assert data[-1:] == b"\x00"

    def test_json_payload_length(self):
        data = build_amxd(MINIMAL_PATCHER)
        declared_len = struct.unpack_from("<I", data, 28)[0]
        actual_payload = data[32:]
        assert declared_len == len(actual_payload)

    def test_json_roundtrip(self):
        data = build_amxd(MINIMAL_PATCHER)
        json_payload = data[32:]
        # Strip trailing newline + null
        json_str = json_payload.rstrip(b"\x00").rstrip(b"\n").decode("utf-8")
        recovered = json.loads(json_str)
        assert recovered == MINIMAL_PATCHER

    def test_total_header_size(self):
        """Header is always 32 bytes before JSON payload."""
        data = build_amxd(MINIMAL_PATCHER)
        json_len = struct.unpack_from("<I", data, 28)[0]
        assert len(data) == 32 + json_len

    def test_complex_patcher_roundtrip(self):
        patcher = {
            "patcher": {
                "fileversion": 1,
                "boxes": [
                    {"box": {"id": "obj-1", "maxclass": "newobj", "text": "plugin~"}},
                    {"box": {"id": "obj-2", "maxclass": "newobj", "text": "plugout~"}},
                ],
                "lines": [
                    {"patchline": {"source": ["obj-1", 0], "destination": ["obj-2", 0]}},
                ],
            }
        }
        data = build_amxd(patcher, AUDIO_EFFECT)
        json_payload = data[32:].rstrip(b"\x00").rstrip(b"\n").decode("utf-8")
        recovered = json.loads(json_payload)
        assert recovered == patcher
        assert len(recovered["patcher"]["boxes"]) == 2
        assert len(recovered["patcher"]["lines"]) == 1
