"""Smoke tests for the standalone Spectrum Analyzer plugin build."""

import os
import tempfile

from plugins.spectrum_analyzer.build import DISPLAY_FILENAME, KERNEL_FILENAME, build_device


def test_build_device_contains_expected_controls():
    device = build_device()
    boxes = {box["box"]["id"]: box["box"] for box in device.boxes}
    ids = set(boxes)
    assert "spec_display" in ids
    assert "graph_bg" in ids
    assert "input_meter" in ids
    assert "block_menu" in ids
    assert "refresh_box" in ids
    assert "avg_box" in ids
    assert "range_lo_box" in ids
    assert "range_hi_box" in ids
    assert "channel_btn_l" in ids
    assert "channel_btn_r" in ids
    assert "channel_btn_sum" in ids
    assert "graph_btn_line" in ids
    assert "graph_btn_max" in ids
    assert "scale_btn_lin" in ids
    assert "scale_btn_log" in ids
    assert "scale_btn_st" in ids
    assert "auto_button" in ids
    assert "src_sel" in ids
    assert "channel_state" in ids
    assert "graph_state" in ids
    assert "scale_state" in ids
    assert "range_pack" in ids
    assert "range_msg" in ids
    assert "sep_block" in ids
    assert "sep_channel" in ids
    assert "sep_avg" in ids

    assert device.width == 413
    assert device.height == 158

    expected_controls = {
        "label_block": {
            "maxclass": "live.comment",
            "presentation_rect": [15, 3, 28, 10],
            "fontsize": 8.7,
        },
        "label_channel": {
            "maxclass": "live.comment",
            "presentation_rect": [15, 33, 40, 10],
            "fontsize": 8.7,
        },
        "label_refresh": {
            "maxclass": "live.comment",
            "presentation_rect": [15, 64, 38, 10],
            "fontsize": 8.7,
        },
        "label_avg": {
            "maxclass": "live.comment",
            "presentation_rect": [15, 83, 18, 10],
            "fontsize": 8.7,
        },
        "label_graph": {
            "maxclass": "live.comment",
            "presentation_rect": [15, 113, 30, 10],
            "fontsize": 8.7,
        },
        "label_scale": {
            "maxclass": "live.comment",
            "presentation_rect": [15, 131, 36, 10],
            "fontsize": 8.7,
        },
        "input_meter": {
            "maxclass": "live.meter~",
            "presentation_rect": [0, 0, 9, 158],
        },
        "block_menu": {
            "maxclass": "live.menu",
            "presentation_rect": [56, 1, 73, 13],
            "fontsize": 8.5,
        },
        "refresh_box": {
            "maxclass": "live.numbox",
            "presentation_rect": [56, 59, 48, 13],
            "fontsize": 8.5,
            "appearance": 2,
        },
        "avg_box": {
            "maxclass": "live.numbox",
            "presentation_rect": [56, 78, 48, 13],
            "fontsize": 8.5,
            "appearance": 2,
        },
        "channel_btn_l": {
            "maxclass": "live.text",
            "presentation_rect": [56, 31, 13, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "channel_btn_r": {
            "maxclass": "live.text",
            "presentation_rect": [72, 31, 13, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "channel_btn_sum": {
            "maxclass": "live.text",
            "presentation_rect": [88, 31, 22, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "graph_btn_line": {
            "maxclass": "live.text",
            "presentation_rect": [56, 110, 38, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "graph_btn_max": {
            "maxclass": "live.text",
            "presentation_rect": [97, 110, 31, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "scale_btn_lin": {
            "maxclass": "live.text",
            "presentation_rect": [56, 128, 22, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "scale_btn_log": {
            "maxclass": "live.text",
            "presentation_rect": [81, 128, 22, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "scale_btn_st": {
            "maxclass": "live.text",
            "presentation_rect": [106, 128, 22, 13],
            "fontsize": 8.1,
            "mode": 0,
        },
        "auto_button": {
            "maxclass": "live.text",
            "presentation_rect": [15, 146, 34, 12],
            "fontsize": 8.1,
            "mode": 1,
        },
        "range_lo_box": {
            "maxclass": "live.numbox",
            "presentation_rect": [56, 146, 33, 12],
            "fontsize": 7.8,
        },
        "range_hi_box": {
            "maxclass": "live.numbox",
            "presentation_rect": [95, 146, 33, 12],
            "fontsize": 7.8,
        },
        "sep_block": {
            "maxclass": "panel",
            "presentation_rect": [14, 22, 114, 1],
        },
        "sep_channel": {
            "maxclass": "panel",
            "presentation_rect": [14, 52, 114, 1],
        },
        "sep_avg": {
            "maxclass": "panel",
            "presentation_rect": [14, 101, 114, 1],
        },
        "spec_display": {
            "maxclass": "v8ui",
            "presentation_rect": [134, 0, 279, 158],
        },
    }

    for control_id, expected in expected_controls.items():
        control = boxes[control_id]
        assert control["maxclass"] == expected["maxclass"]
        assert control["presentation_rect"] == expected["presentation_rect"]
        if "fontsize" in expected:
            assert control["fontsize"] == expected["fontsize"]
        if "mode" in expected:
            assert control["mode"] == expected["mode"]
        if "appearance" in expected:
            assert control["appearance"] == expected["appearance"]

    block_attrs = boxes["block_menu"]["saved_attribute_attributes"]["valueof"]
    refresh_attrs = boxes["refresh_box"]["saved_attribute_attributes"]["valueof"]
    avg_attrs = boxes["avg_box"]["saved_attribute_attributes"]["valueof"]
    range_lo_attrs = boxes["range_lo_box"]["saved_attribute_attributes"]["valueof"]
    range_hi_attrs = boxes["range_hi_box"]["saved_attribute_attributes"]["valueof"]

    assert block_attrs["parameter_initial"] == [3]
    assert block_attrs["parameter_enum"] == ["1024", "2048", "4096", "8192", "16384"]
    assert refresh_attrs["parameter_initial"] == [60.0]
    assert refresh_attrs["parameter_unitstyle"] == 2
    assert avg_attrs["parameter_initial"] == [1]
    assert avg_attrs["parameter_unitstyle"] == 0
    assert range_lo_attrs["parameter_initial"] == [0.0]
    assert range_lo_attrs["parameter_unitstyle"] == 1
    assert range_hi_attrs["parameter_initial"] == [1.0]
    assert range_hi_attrs["parameter_unitstyle"] == 1

    assert boxes["spec_display"]["filename"] == DISPLAY_FILENAME
    assert boxes["spec_display"]["ignoreclick"] == 1
    assert boxes["spec_display"]["background"] == 0
    assert boxes["fft_core"]["text"] == "pfft~ spectrum_analyzer_core_v2 2048 4"
    assert boxes["channel_state"]["text"] == "int"
    assert boxes["graph_state"]["text"] == "int"
    assert boxes["scale_state"]["text"] == "int"
    assert boxes["range_msg"]["text"] == "prepend set_range"
    assert DISPLAY_FILENAME in device._js_files
    assert KERNEL_FILENAME in device._support_files
    assert "out 1" in device._support_files[KERNEL_FILENAME]["content"]
    assert "function list()" in device._js_files[DISPLAY_FILENAME]


def test_build_device_writes_amxd():
    device = build_device()
    with tempfile.TemporaryDirectory() as tmpdir:
        amxd_path = os.path.join(tmpdir, "Spectrum Analyzer.amxd")
        device.build(amxd_path)
        assert os.path.exists(amxd_path)
        assert os.path.exists(os.path.join(tmpdir, DISPLAY_FILENAME))
        assert os.path.exists(os.path.join(tmpdir, KERNEL_FILENAME))
