"""device_from_amxd error handling + parameter-bank round-trip (scan #23).

The reverse/round-trip path is core to the per-plugin migration workflow, but it
parsed AMXD bytes with no length/JSON guards (cryptic IndexError/struct.error/
JSONDecodeError) and had no CI coverage for parameter-bank reconstruction.
"""

import struct

import pytest

from m4l_builder import AudioEffect, ParameterSpec
from m4l_builder.amxd import build_device, device_from_amxd


def _valid_header(meta_len: int = 0, type_code: bytes = b"aaaa") -> bytearray:
    """Minimal AMXD header: type_code at [8:12], meta_len uint32 at [16:20]."""
    header = bytearray(28)
    header[8:12] = type_code
    struct.pack_into("<I", header, 16, meta_len)
    return header


class TestDeviceFromAmxdErrors:
    def test_truncated_file_raises_value_error(self, tmp_path):
        path = tmp_path / "tiny.amxd"
        path.write_bytes(b"short")  # < 20 bytes
        with pytest.raises(ValueError, match="truncated"):
            device_from_amxd(str(path))

    def test_empty_json_payload_raises_value_error(self, tmp_path):
        path = tmp_path / "nopayload.amxd"
        path.write_bytes(bytes(_valid_header()))  # header only, no JSON body
        with pytest.raises(ValueError, match="no patcher JSON"):
            device_from_amxd(str(path))

    def test_malformed_json_raises_value_error(self, tmp_path):
        path = tmp_path / "badjson.amxd"
        path.write_bytes(bytes(_valid_header()) + b"{not valid json")
        with pytest.raises(ValueError, match="malformed"):
            device_from_amxd(str(path))


class TestParameterBankRoundTrip:
    def test_device_type_and_banks_survive_round_trip(self, tmp_path):
        device = AudioEffect("RoundTrip", 300, 150)
        device.assign_parameter_bank("Cutoff", bank=0, position=3, bank_name="Main")
        device.assign_parameter_bank("Reso", bank=0, position=4)

        path = tmp_path / "rt.amxd"
        build_device(device, str(path))
        back = device_from_amxd(str(path))

        assert back.device_type == "audio_effect"
        assert back._param_banks["Cutoff"] == (0, 3)
        assert back._param_banks["Reso"] == (0, 4)
        assert back._param_bank_names[0] == "Main"

    def test_bank_visibility_default_round_trips(self, tmp_path):
        device = AudioEffect("Vis", 300, 150)
        spec = ParameterSpec.continuous(
            "Gain", shortname="Gn", minimum=-12.0, maximum=12.0, initial=0.0
        )
        device.register_parameter(spec)
        device.assign_parameter_bank("Gain", bank=0, position=0, bank_name="Bank0")

        path = tmp_path / "vis.amxd"
        build_device(device, str(path))
        back = device_from_amxd(str(path))

        assert "Gain" in back._param_banks
