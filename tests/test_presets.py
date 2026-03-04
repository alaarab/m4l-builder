"""Tests for presets.py — preset_manager and add_preset_buttons."""

import pytest

from m4l_builder.presets import preset_manager, add_preset_buttons
from m4l_builder import AudioEffect


def _texts(boxes):
    return [b["box"]["text"] for b in boxes]


class TestPresetManager:
    def test_returns_tuple(self):
        result = preset_manager("pm")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_boxes_not_empty(self):
        boxes, lines = preset_manager("pm")
        assert len(boxes) > 0

    def test_has_preset_object(self):
        boxes, lines = preset_manager("pm")
        texts = _texts(boxes)
        assert any(t == "preset" or t.startswith("preset") for t in texts)

    def test_has_umenu(self):
        boxes, lines = preset_manager("pm")
        texts = _texts(boxes)
        assert any("umenu" in t for t in texts)

    def test_default_num_presets(self):
        boxes, lines = preset_manager("pm")
        texts = _texts(boxes)
        menu_text = next(t for t in texts if "umenu" in t)
        # 8 slots → "1 2 3 4 5 6 7 8" in the text
        assert "8" in menu_text

    def test_custom_num_presets(self):
        boxes, lines = preset_manager("pm", num_presets=4)
        texts = _texts(boxes)
        menu_text = next(t for t in texts if "umenu" in t)
        assert "4" in menu_text

    def test_has_line(self):
        boxes, lines = preset_manager("pm")
        assert len(lines) >= 1


class TestAddPresetButtons:
    def _make_device(self):
        return AudioEffect("TestDevice", width=400, height=200)

    def test_boxes_added(self):
        device = self._make_device()
        initial = len(device.boxes)
        add_preset_buttons(device, x=10, y=10)
        assert len(device.boxes) > initial

    def test_returns_ids(self):
        device = self._make_device()
        ids = add_preset_buttons(device, x=10, y=10)
        assert isinstance(ids, list)
        assert len(ids) > 0

    def test_preset_box_added(self):
        device = self._make_device()
        add_preset_buttons(device, x=10, y=10)
        texts = [b["box"].get("text", "") for b in device.boxes]
        assert any("preset" in t for t in texts)

    def test_correct_number_of_ids(self):
        device = self._make_device()
        ids = add_preset_buttons(device, x=10, y=10)
        # preset + save + load + prev + next = 5
        assert len(ids) == 5

    def test_lines_added(self):
        device = self._make_device()
        initial_lines = len(device.lines)
        add_preset_buttons(device, x=10, y=10)
        assert len(device.lines) > initial_lines
