"""Tests for live_api.py — live.path, live.object, live.observer wrappers."""

import pytest

from m4l_builder.live_api import live_object_path, live_observer, live_set_control


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
