"""Tests for patcher.py — build_patcher() function."""

import pytest

from m4l_builder.patcher import build_patcher
from m4l_builder.constants import AMXD_TYPE, DEFAULT_APPVERSION


SAMPLE_BOX = {"box": {"id": "obj-1", "maxclass": "newobj", "text": "plugin~"}}
SAMPLE_LINE = {"patchline": {"source": ["obj-1", 0], "destination": ["obj-2", 0]}}


class TestBuildPatcher:
    """Test build_patcher() produces correct patcher dict structure."""

    def test_returns_dict_with_patcher_key(self):
        result = build_patcher([], [])
        assert "patcher" in result

    def test_boxes_included(self):
        result = build_patcher([SAMPLE_BOX], [])
        assert result["patcher"]["boxes"] == [SAMPLE_BOX]

    def test_lines_included(self):
        result = build_patcher([], [SAMPLE_LINE])
        assert result["patcher"]["lines"] == [SAMPLE_LINE]

    def test_empty_boxes_and_lines(self):
        result = build_patcher([], [])
        assert result["patcher"]["boxes"] == []
        assert result["patcher"]["lines"] == []

    def test_multiple_boxes_and_lines(self):
        box2 = {"box": {"id": "obj-2", "maxclass": "newobj", "text": "plugout~"}}
        result = build_patcher([SAMPLE_BOX, box2], [SAMPLE_LINE])
        assert len(result["patcher"]["boxes"]) == 2
        assert len(result["patcher"]["lines"]) == 1

    def test_default_device_type_is_audio_effect(self):
        result = build_patcher([], [])
        assert result["patcher"]["project"]["amxdtype"] == AMXD_TYPE["audio_effect"]

    def test_instrument_device_type(self):
        result = build_patcher([], [], device_type="instrument")
        assert result["patcher"]["project"]["amxdtype"] == AMXD_TYPE["instrument"]

    def test_midi_effect_device_type(self):
        result = build_patcher([], [], device_type="midi_effect")
        assert result["patcher"]["project"]["amxdtype"] == AMXD_TYPE["midi_effect"]

    def test_unknown_device_type_falls_back_to_audio_effect(self):
        result = build_patcher([], [], device_type="unknown_type")
        assert result["patcher"]["project"]["amxdtype"] == AMXD_TYPE["audio_effect"]

    def test_default_width_in_openrect(self):
        result = build_patcher([], [])
        assert result["patcher"]["openrect"][2] == 400.0

    def test_default_height_in_openrect(self):
        result = build_patcher([], [])
        assert result["patcher"]["openrect"][3] == 170.0

    def test_custom_width(self):
        result = build_patcher([], [], width=600.0)
        assert result["patcher"]["openrect"][2] == 600.0
        assert result["patcher"]["devicewidth"] == 600.0

    def test_custom_height(self):
        result = build_patcher([], [], height=250.0)
        assert result["patcher"]["openrect"][3] == 250.0

    def test_openrect_origin_is_zero(self):
        result = build_patcher([], [])
        assert result["patcher"]["openrect"][0] == 0.0
        assert result["patcher"]["openrect"][1] == 0.0

    def test_edit_rect_is_fixed(self):
        result = build_patcher([], [])
        assert result["patcher"]["rect"] == [100.0, 100.0, 900.0, 700.0]

    def test_openinpresentation_is_1(self):
        result = build_patcher([], [])
        assert result["patcher"]["openinpresentation"] == 1

    def test_gridsize_is_8x8(self):
        result = build_patcher([], [])
        assert result["patcher"]["gridsize"] == [8.0, 8.0]

    def test_appversion_matches_default(self):
        result = build_patcher([], [])
        assert result["patcher"]["appversion"] == DEFAULT_APPVERSION

    def test_appversion_major(self):
        result = build_patcher([], [])
        assert result["patcher"]["appversion"]["major"] == DEFAULT_APPVERSION["major"]

    def test_appversion_minor(self):
        result = build_patcher([], [])
        assert result["patcher"]["appversion"]["minor"] == DEFAULT_APPVERSION["minor"]

    def test_appversion_architecture(self):
        result = build_patcher([], [])
        assert result["patcher"]["appversion"]["architecture"] == DEFAULT_APPVERSION["architecture"]

    def test_parameters_section_present(self):
        result = build_patcher([], [])
        assert "parameters" in result["patcher"]

    def test_parameterbanks_present(self):
        result = build_patcher([], [])
        assert "parameterbanks" in result["patcher"]["parameters"]

    def test_parameterbanks_has_bank_0(self):
        result = build_patcher([], [])
        banks = result["patcher"]["parameters"]["parameterbanks"]
        assert "0" in banks

    def test_parameterbanks_bank_0_index(self):
        result = build_patcher([], [])
        bank = result["patcher"]["parameters"]["parameterbanks"]["0"]
        assert bank["index"] == 0

    def test_parameterbanks_bank_0_parameters_empty(self):
        result = build_patcher([], [])
        bank = result["patcher"]["parameters"]["parameterbanks"]["0"]
        assert bank["parameters"] == []

    def test_project_has_amxdtype(self):
        result = build_patcher([], [])
        assert result["patcher"]["project"]["amxdtype"] == 1633771873

    def test_project_has_full_structure(self):
        result = build_patcher([], [], name="my_synth")
        proj = result["patcher"]["project"]
        assert proj["version"] == 1
        assert proj["hideprojectwindow"] == 1
        assert "contents" in proj

    def test_fileversion_is_1(self):
        result = build_patcher([], [])
        assert result["patcher"]["fileversion"] == 1

    def test_classnamespace_is_box(self):
        result = build_patcher([], [])
        assert result["patcher"]["classnamespace"] == "box"

    def test_all_three_device_types_have_distinct_amxdtype(self):
        audio = build_patcher([], [], device_type="audio_effect")["patcher"]["project"]["amxdtype"]
        instr = build_patcher([], [], device_type="instrument")["patcher"]["project"]["amxdtype"]
        midi = build_patcher([], [], device_type="midi_effect")["patcher"]["project"]["amxdtype"]
        assert len({audio, instr, midi}) == 3
