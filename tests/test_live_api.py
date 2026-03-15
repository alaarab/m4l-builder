"""Tests for live_api.py — live.path/live.object/live.thisdevice wrappers."""

from m4l_builder.live_api import (
    device_active_state,
    live_object_path,
    live_parameter_probe,
    live_observer,
    live_state_observer,
    live_set_control,
    live_thisdevice,
)


def _texts(boxes):
    return [b["box"]["text"] for b in boxes]


class TestLiveObjectPath:
    def test_returns_tuple(self):
        result = live_object_path("lop")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_boxes_not_empty(self):
        boxes, lines = live_object_path("lop")
        assert len(boxes) > 0

    def test_has_live_path(self):
        boxes, lines = live_object_path("lop")
        texts = _texts(boxes)
        assert any("live.path" in t for t in texts)

    def test_has_live_object(self):
        boxes, lines = live_object_path("lop")
        texts = _texts(boxes)
        assert any("live.object" in t for t in texts)

    def test_custom_path_in_text(self):
        boxes, lines = live_object_path("lop", path="live_set tracks 0")
        texts = _texts(boxes)
        assert any("live_set tracks 0" in t for t in texts)

    def test_has_connecting_line(self):
        boxes, lines = live_object_path("lop")
        assert len(lines) >= 1


class TestLiveObserver:
    def test_returns_tuple(self):
        result = live_observer("lo")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_boxes_not_empty(self):
        boxes, lines = live_observer("lo")
        assert len(boxes) > 0

    def test_has_live_observer(self):
        boxes, lines = live_observer("lo")
        texts = _texts(boxes)
        assert any("live.observer" in t for t in texts)

    def test_has_live_path(self):
        boxes, lines = live_observer("lo")
        texts = _texts(boxes)
        assert any("live.path" in t for t in texts)

    def test_has_live_object(self):
        boxes, lines = live_observer("lo")
        texts = _texts(boxes)
        assert any("live.object" in t for t in texts)

    def test_custom_prop_in_observer(self):
        boxes, lines = live_observer("lo", prop="is_playing")
        texts = _texts(boxes)
        assert any("is_playing" in t for t in texts)

    def test_has_lines(self):
        boxes, lines = live_observer("lo")
        assert len(lines) >= 2

    def test_direct_mode_uses_path_and_observer_only(self):
        boxes, lines = live_observer("lo", path="live_set", prop="tempo", via_object=False)
        texts = _texts(boxes)

        assert "live.object" not in texts
        assert "live.path live_set" in texts
        assert "live.observer tempo" in texts
        assert len(lines) == 1
        assert lines[0]["patchline"]["source"] == ["lo_path", 1]
        assert lines[0]["patchline"]["destination"] == ["lo_observer", 1]

    def test_direct_mode_can_bind_property_via_message(self):
        boxes, lines = live_observer("lo", path="live_set", prop="tempo", via_object=False, bind_via_message=True)
        texts = _texts(boxes)

        assert "live.object" not in texts
        assert "live.observer" in texts
        assert "property tempo" in texts
        assert len(lines) == 2

    def test_object_mode_can_bind_property_via_message(self):
        boxes, lines = live_observer("lo", path="live_set", prop="tempo", bind_via_message=True)
        texts = _texts(boxes)

        assert "live.path live_set" in texts
        assert "live.object" in texts
        assert "live.observer" in texts
        assert "property tempo" in texts
        assert len(lines) == 3


class TestLiveParameterProbe:
    def test_builds_probe_message_cluster(self):
        boxes, lines = live_parameter_probe(
            "probe",
            path="live_set tracks 0 devices 0 parameters 0",
            commands=["get max", "get min", "get value", "call str_for_value 0.5"],
        )
        texts = _texts(boxes)

        assert "live.path live_set tracks 0 devices 0 parameters 0" in texts
        assert "live.object" in texts
        assert "get max, get min, get value, call str_for_value 0.5" in texts
        assert len(lines) == 2

    def test_can_build_object_only_probe_with_route(self):
        boxes, lines = live_parameter_probe(
            "probe",
            path=None,
            commands=["get name", "get max", "get min", "get value"],
            route_selectors=["value", "max", "min", "name"],
        )
        texts = _texts(boxes)

        assert "live.path" not in " ".join(texts)
        assert "live.object" in texts
        assert "get name, get max, get min, get value" in texts
        assert "route value max min name" in texts
        assert len(lines) == 2

    def test_can_build_object_only_probe_with_trigger_wrapper(self):
        boxes, lines = live_parameter_probe(
            "probe",
            path=None,
            commands=["get name", "get max", "get min", "get value"],
            route_selectors=["value", "max", "min", "name"],
            trigger_text="t b s",
            message_from_trigger_outlet=0,
            object_from_trigger_outlet=1,
        )
        texts = _texts(boxes)

        assert "t b s" in texts
        assert "live.object" in texts
        assert "route value max min name" in texts
        assert len(lines) == 4


class TestLiveSetControl:
    def test_returns_tuple(self):
        result = live_set_control("lsc")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_boxes_not_empty(self):
        boxes, lines = live_set_control("lsc")
        assert len(boxes) > 0

    def test_has_live_object(self):
        boxes, lines = live_set_control("lsc")
        texts = _texts(boxes)
        assert any("live.object" in t for t in texts)

    def test_has_live_path(self):
        boxes, lines = live_set_control("lsc")
        texts = _texts(boxes)
        assert any("live.path" in t for t in texts)

    def test_has_connecting_line(self):
        boxes, lines = live_set_control("lsc")
        assert len(lines) >= 1


class TestLiveStateObserver:
    def test_builds_initialized_state_cluster(self):
        boxes, lines = live_state_observer("state")
        texts = _texts(boxes)

        assert "live.thisdevice" in texts
        assert "t b b" in texts
        assert "live.path live_set" in texts
        assert "property scale_mode" in texts
        assert "live.observer" in texts
        assert "t i i" in texts
        assert "sel 0" in texts
        assert len(lines) == 7


class TestLiveApiCustomization:
    def test_custom_ids_and_rects_are_preserved(self):
        boxes, lines = live_object_path(
            "probe",
            path="live_set tracks 0 devices 0",
            path_id="tempo_path",
            object_id="tempo_obj",
            path_rect=[10, 20, 120, 20],
            object_rect=[10, 50, 96, 20],
        )

        assert boxes[0]["box"]["id"] == "tempo_path"
        assert boxes[0]["box"]["patching_rect"] == [10, 20, 120, 20]
        assert boxes[1]["box"]["id"] == "tempo_obj"
        assert boxes[1]["box"]["patching_rect"] == [10, 50, 96, 20]
        assert lines[0]["patchline"]["source"] == ["tempo_path", 0]
        assert lines[0]["patchline"]["destination"] == ["tempo_obj", 0]


class TestLiveThisDevice:
    def test_returns_single_thisdevice_box(self):
        boxes, lines = live_thisdevice("dev")

        assert len(boxes) == 1
        assert lines == []
        assert boxes[0]["box"]["text"] == "live.thisdevice"
        assert boxes[0]["box"]["id"] == "dev_device"


class TestDeviceActiveState:
    def test_builds_prepend_and_thisdevice_pair(self):
        boxes, lines = device_active_state("active")
        texts = _texts(boxes)

        assert texts == ["prepend active", "live.thisdevice"]
        assert boxes[0]["box"]["id"] == "active_prepend"
        assert boxes[1]["box"]["id"] == "active_device"
        assert len(lines) == 1
        assert lines[0]["patchline"]["source"] == ["active_prepend", 0]
        assert lines[0]["patchline"]["destination"] == ["active_device", 0]

    def test_can_build_device_to_prepend_variant(self):
        boxes, lines = device_active_state("active", from_device_outlet=1)
        texts = _texts(boxes)

        assert texts == ["prepend active", "live.thisdevice"]
        assert len(lines) == 1
        assert lines[0]["patchline"]["source"] == ["active_device", 1]
        assert lines[0]["patchline"]["destination"] == ["active_prepend", 0]
