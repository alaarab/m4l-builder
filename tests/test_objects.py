"""Tests for objects.py — newobj() and patchline() factory functions."""

import pytest

from m4l_builder.objects import newobj, patchline


class TestNewobj:
    """Test newobj() box factory."""

    def test_returns_dict_with_box_key(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2)
        assert "box" in result

    def test_default_patching_rect(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2)
        assert result["box"]["patching_rect"] == [0, 0, 60, 20]

    def test_custom_patching_rect(self):
        rect = [10, 20, 100, 30]
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2, patching_rect=rect)
        assert result["box"]["patching_rect"] == rect

    def test_default_fontname(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2)
        assert result["box"]["fontname"] == "Arial Bold"

    def test_default_fontsize(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2)
        assert result["box"]["fontsize"] == 10.0

    def test_outlettype_included_when_provided(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2, outlettype=["signal"])
        assert result["box"]["outlettype"] == ["signal"]

    def test_outlettype_omitted_when_none(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2, outlettype=None)
        assert "outlettype" not in result["box"]

    def test_outlettype_omitted_by_default(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2)
        assert "outlettype" not in result["box"]

    def test_numinlets_set(self):
        result = newobj("obj-1", "plugin~", numinlets=3, numoutlets=1)
        assert result["box"]["numinlets"] == 3

    def test_numoutlets_set(self):
        result = newobj("obj-1", "plugin~", numinlets=1, numoutlets=4)
        assert result["box"]["numoutlets"] == 4

    def test_id_set(self):
        result = newobj("obj-99", "plugin~", numinlets=2, numoutlets=2)
        assert result["box"]["id"] == "obj-99"

    def test_text_set(self):
        result = newobj("obj-1", "*~ 0.5", numinlets=2, numoutlets=1)
        assert result["box"]["text"] == "*~ 0.5"

    def test_maxclass_is_newobj(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2)
        assert result["box"]["maxclass"] == "newobj"

    def test_extra_kwargs_merged_into_box(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2, color=[1.0, 0.0, 0.0, 1.0])
        assert result["box"]["color"] == [1.0, 0.0, 0.0, 1.0]

    def test_multiple_extra_kwargs(self):
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2,
                        presentation=1, presentation_rect=[0, 0, 100, 50])
        assert result["box"]["presentation"] == 1
        assert result["box"]["presentation_rect"] == [0, 0, 100, 50]

    def test_kwargs_do_not_override_fixed_fields(self):
        # maxclass should remain "newobj" even if passed as kwarg
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2, maxclass="overridden")
        assert result["box"]["maxclass"] == "overridden"

    def test_outlettype_empty_list_omitted(self):
        # An empty list is falsy, so outlettype should be omitted
        result = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2, outlettype=[])
        assert "outlettype" not in result["box"]

    def test_multiple_outlet_types(self):
        result = newobj("obj-1", "plugin~", numinlets=1, numoutlets=2,
                        outlettype=["signal", "signal"])
        assert result["box"]["outlettype"] == ["signal", "signal"]


class TestPatchline:
    """Test patchline() connection factory."""

    def test_returns_dict_with_patchline_key(self):
        result = patchline("obj-1", 0, "obj-2", 0)
        assert "patchline" in result

    def test_source_is_list_of_id_and_outlet(self):
        result = patchline("obj-1", 0, "obj-2", 0)
        assert result["patchline"]["source"] == ["obj-1", 0]

    def test_destination_is_list_of_id_and_inlet(self):
        result = patchline("obj-1", 0, "obj-2", 0)
        assert result["patchline"]["destination"] == ["obj-2", 0]

    def test_source_outlet_index(self):
        result = patchline("obj-1", 2, "obj-2", 0)
        assert result["patchline"]["source"] == ["obj-1", 2]

    def test_destination_inlet_index(self):
        result = patchline("obj-1", 0, "obj-2", 3)
        assert result["patchline"]["destination"] == ["obj-2", 3]

    def test_different_source_and_dest_ids(self):
        result = patchline("obj-10", 1, "obj-20", 2)
        assert result["patchline"]["source"][0] == "obj-10"
        assert result["patchline"]["destination"][0] == "obj-20"

    def test_patchline_only_has_source_and_destination(self):
        result = patchline("obj-1", 0, "obj-2", 0)
        assert set(result["patchline"].keys()) == {"source", "destination"}
