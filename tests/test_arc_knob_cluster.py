"""Tests for the arc-knob cluster engine + Device.add_arc_knob_cluster.

The JS gesture behavior (drag -> outlet, set_ -> display, no echo) runs under
the Node harness; the device recipe (v8ui + parked live.dial hosts + route +
sync wiring) is asserted structurally.
"""

import os

import pytest

from m4l_builder import AudioEffect
from m4l_builder.constants import UNITSTYLE_PERCENT
from m4l_builder.engines.arc_knob_cluster import arc_knob_cluster_js

from .js_harness import NODE, run_jsui

KNOBS = [
    {"key": "chance", "label": "CHANCE", "min": 0, "max": 100, "init": 100,
     "name": "Chance", "unitstyle": UNITSTYLE_PERCENT},
    {"key": "rev", "label": "REV", "min": 0, "max": 100, "init": 0},
    {"key": "pitch", "label": "PITCH", "min": -12, "max": 12, "init": 0,
     "signed": True},
    {"key": "mix", "label": "MIX", "min": 0, "max": 100, "init": 100},
]
RECT = [300, 30, 162, 130]


def _build():
    device = AudioEffect("Arc Cluster Test", 480, 168)
    hosts = device.add_arc_knob_cluster("cluster", RECT, KNOBS)
    return device, hosts


def _boxes(device):
    return {b["box"]["id"]: b["box"] for b in device.boxes}


def _lines(device):
    return {
        (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
         ln["patchline"]["destination"][0], ln["patchline"]["destination"][1])
        for ln in device.lines
    }


# ── structural device recipe ────────────────────────────────────────────────
def test_returns_host_id_per_knob():
    _, hosts = _build()
    assert hosts == {"chance": "cluster_chance", "rev": "cluster_rev",
                     "pitch": "cluster_pitch", "mix": "cluster_mix"}


def test_v8ui_is_interactive_single_outlet():
    device, _ = _build()
    box = _boxes(device)["cluster"]
    assert box["maxclass"] == "v8ui"
    assert box["numinlets"] == 1
    assert box["numoutlets"] == 1
    assert box["presentation_rect"] == RECT
    assert int(box.get("ignoreclick", 0)) == 0  # accepts the pointer


def test_hosts_are_parked_hidden_dials_with_names():
    device, _ = _build()
    boxes = _boxes(device)
    for key, name in (("chance", "Chance"), ("pitch", "Pitch")):
        host = boxes[f"cluster_{key}"]
        assert host["maxclass"] == "live.dial"
        assert host.get("presentation", 0) == 0        # off the face
        assert host["patching_rect"][0] == 900          # parked off-canvas
        va = host["saved_attribute_attributes"]["valueof"]
        assert va["parameter_longname"] == name


def test_gesture_route_and_visual_sync_wired():
    device, _ = _build()
    boxes, lines = _boxes(device), _lines(device)
    assert boxes["cluster_route"]["text"] == "route chance rev pitch mix"
    assert ("cluster", 0, "cluster_route", 0) in lines      # v8ui -> route
    # each knob: route outlet -> host, and host -> prepend set_ -> v8ui
    for i, k in enumerate(("chance", "rev", "pitch", "mix")):
        assert ("cluster_route", i, f"cluster_{k}", 0) in lines
        assert (f"cluster_{k}", 0, f"cluster_sync_{k}", 0) in lines
        assert (f"cluster_sync_{k}", 0, "cluster", 0) in lines
        assert boxes[f"cluster_sync_{k}"]["text"] == f"prepend set_{k}"


def test_pitch_host_spans_signed_range():
    device, _ = _build()
    va = _boxes(device)["cluster_pitch"]["saved_attribute_attributes"]["valueof"]
    assert va["parameter_mmin"] == -12.0 and va["parameter_mmax"] == 12.0


def test_rejects_duplicate_keys():
    device = AudioEffect("Dup", 300, 168)
    with pytest.raises(ValueError):
        device.add_arc_knob_cluster(
            "c", RECT, [{"key": "a", "label": "A", "min": 0, "max": 1},
                        {"key": "a", "label": "B", "min": 0, "max": 1}])


# ── JS behavior (Node harness) ──────────────────────────────────────────────
@pytest.mark.skipif(not (NODE and os.path.exists(NODE)), reason="node not available")
class TestArcKnobClusterJs:
    def test_drag_down_lowers_value_and_emits_key(self):
        # MIX starts at 100; drag down 45px over a 90px span = -50% of range.
        result = run_jsui(arc_knob_cluster_js(KNOBS), """
            var c = knobC(3);                 // MIX (index 3)
            onclick(c[0], c[1], 1);
            ondrag(c[0], c[1] + 45, 1);
            dump({v: vals[3]});
        """, size=(162, 130))
        assert abs(result.state["v"] - 50.0) < 0.01
        assert [0, "mix", result.state["v"]] in result.outlets

    def test_set_updates_display_without_emitting(self):
        result = run_jsui(arc_knob_cluster_js(KNOBS), """
            set_chance(42);
            dump({v: vals[0]});
        """, size=(162, 130))
        assert result.state["v"] == 42
        assert result.outlets == []            # set_ never re-emits

    def test_drag_clamps_to_range(self):
        result = run_jsui(arc_knob_cluster_js(KNOBS), """
            var c = knobC(1);                  // REV starts at 0
            onclick(c[0], c[1], 1);
            ondrag(c[0], c[1] + 400, 1);       // way past the bottom
            dump({v: vals[1]});
        """, size=(162, 130))
        assert result.state["v"] == 0          # clamped at min, not negative

    def test_release_ends_drag(self):
        result = run_jsui(arc_knob_cluster_js(KNOBS), """
            var c = knobC(0);
            onclick(c[0], c[1], 1);
            ondrag(c[0], c[1], 0);             // button up
            ondrag(c[0], c[1] - 50, 1);        // stray move after release
            dump({v: vals[0]});
        """, size=(162, 130))
        assert result.state["v"] == 100        # unchanged: no active drag
