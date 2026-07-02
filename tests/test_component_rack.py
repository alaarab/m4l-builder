"""Component rack (F2 — corpus P11): stamp one Subpatcher N times via #1 args."""

import json

from m4l_builder import AudioEffect, Subpatcher
from m4l_builder.parameters import ParameterSpec
from m4l_builder.theme import GRAPHITE
from m4l_builder.ui import dial


def _component():
    sub = Subpatcher("band")
    sub.add_box(dial(
        "rate", "#1 Rate", [10, 10, 41, 35], min_val=0.0, max_val=100.0,
        initial=50.0, showname=0, shownumber=1, parameter=ParameterSpec(
            name="#1 Rate", shortname="#1 Rate", minimum=0.0, maximum=100.0,
            initial=50.0, initial_enable=True, linknames=1)))
    return sub


def _boxes(device):
    return {e["box"]["id"]: e["box"] for e in device.boxes}


class TestComponentRack:
    def test_rack_stamps_n_bpatchers_with_args(self):
        d = AudioEffect("rack", width=300, height=168, theme=GRAPHITE)
        ids = d.add_component_rack(
            _component(), 3,
            rects=[[8 + i * 90, 8, 86, 152] for i in range(3)],
            id_prefix="band")
        assert ids == ["band_1", "band_2", "band_3"]
        boxes = _boxes(d)
        for i, bid in enumerate(ids):
            b = boxes[bid]
            assert b["maxclass"] == "bpatcher"
            assert b["embed"] == 1
            assert b["args"] == [i + 1]
            # the embedded component carries the #1 placeholder longname
            blob = json.dumps(b["patcher"])
            assert "#1 Rate" in blob
            assert '"parameter_linknames": 1' in blob

    def test_rect_count_mismatch_raises(self):
        d = AudioEffect("rack", width=300, height=168, theme=GRAPHITE)
        try:
            d.add_component_rack(_component(), 3, rects=[[0, 0, 10, 10]])
        except ValueError as e:
            assert "3 instances" in str(e)
        else:
            raise AssertionError("expected ValueError")

    def test_rack_device_serializes(self):
        d = AudioEffect("rack", width=300, height=168, theme=GRAPHITE)
        d.add_component_rack(
            _component(), 2, rects=[[8, 8, 86, 152], [98, 8, 86, 152]])
        assert len(d.to_bytes()) > 1000
