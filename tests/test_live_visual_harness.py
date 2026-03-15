"""Unit tests for the machine-local Live visual harness helpers."""

from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw

from tools.live_visual_harness import (
    DEFAULT_PROFILE,
    Thresholds,
    analyze_frames,
    detect_separator,
    geometry_metrics,
    is_near_black,
    mean_abs_diff,
    mean_luminance,
)


def _write_image(path: Path, color, size=(1920, 1080)) -> Path:
    image = Image.new("RGBA", size, color)
    image.save(path)
    return path


def _device_size(box):
    return (box[2] - box[0], box[3] - box[1])


def _draw_strip(strip: Image.Image, *, offset_x: int = 0) -> None:
    draw = ImageDraw.Draw(strip)
    draw.rectangle((0, 0, strip.width, strip.height), fill=(47, 47, 47, 255))
    for row in DEFAULT_PROFILE.separator_rows:
        draw.rectangle((14, row, 128, row + 1), fill=(33, 33, 33, 255))
    for _, rect in DEFAULT_PROFILE.control_regions.items():
        x, y, w, h = rect
        draw.rectangle((x + offset_x, y, x + w - 1 + offset_x, y + h - 1), outline=(196, 196, 196, 255))


def _draw_graph(device: Image.Image, box, shift: int) -> None:
    draw = ImageDraw.Draw(device)
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(15, 21, 30, 255))
    draw.line((x0 + 12 + shift, y1 - 18, x1 - 12 + shift, y0 + 18), fill=(255, 163, 76, 255), width=3)


def _make_frame(path: Path, *, custom_shift: int = 0, stock_shift: int = 0, custom_strip_offset: int = 0) -> Path:
    frame = Image.new("RGBA", (1920, 1080), (18, 18, 18, 255))
    stock_device = Image.new("RGBA", _device_size(DEFAULT_PROFILE.stock_device_box), (26, 26, 26, 255))
    custom_device = Image.new("RGBA", _device_size(DEFAULT_PROFILE.custom_device_box), (26, 26, 26, 255))

    stock_strip = stock_device.crop(DEFAULT_PROFILE.stock_strip_box)
    custom_strip = custom_device.crop(DEFAULT_PROFILE.custom_strip_box)
    _draw_strip(stock_strip)
    _draw_strip(custom_strip, offset_x=custom_strip_offset)
    stock_device.paste(stock_strip, DEFAULT_PROFILE.stock_strip_box[:2])
    custom_device.paste(custom_strip, DEFAULT_PROFILE.custom_strip_box[:2])
    _draw_graph(stock_device, DEFAULT_PROFILE.stock_graph_box, stock_shift)
    _draw_graph(custom_device, DEFAULT_PROFILE.custom_graph_box, custom_shift)

    frame.paste(stock_device, DEFAULT_PROFILE.stock_device_box[:2])
    frame.paste(custom_device, DEFAULT_PROFILE.custom_device_box[:2])
    frame.save(path)
    return path


def test_mean_abs_diff_zero_for_identical_images(tmp_path):
    path = _write_image(tmp_path / "same.png", (10, 20, 30, 255), size=(10, 10))
    image = Image.open(path)
    assert mean_abs_diff(image, image) == 0.0


def test_mean_luminance_and_is_near_black():
    black = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
    bright = Image.new("RGBA", (8, 8), (255, 255, 255, 255))

    assert mean_luminance(black) == 0.0
    assert mean_luminance(bright) == 255.0
    assert is_near_black(black) is True
    assert is_near_black(bright) is False


def test_detect_separator_finds_expected_row():
    strip = Image.new("RGBA", (134, 158), (47, 47, 47, 255))
    draw = ImageDraw.Draw(strip)
    draw.rectangle((14, 52, 128, 53), fill=(20, 20, 20, 255))

    metrics = detect_separator(strip, 52)

    assert metrics["detected_y"] == 52
    assert metrics["offset_px"] == 0
    assert metrics["contrast"] > 0


def test_geometry_metrics_report_shifted_control_group():
    stock = Image.new("RGBA", (134, 158), (47, 47, 47, 255))
    custom = Image.new("RGBA", (134, 158), (47, 47, 47, 255))
    _draw_strip(stock)
    _draw_strip(custom, offset_x=4)

    metrics = geometry_metrics(stock, custom, {"channel_group": DEFAULT_PROFILE.control_regions["channel_group"]})

    assert metrics[0]["center_delta_px"] > 0
    assert metrics[0]["size_delta_px"] >= 0


def test_analyze_frames_flags_black_frames(tmp_path):
    capture_a = _write_image(tmp_path / "capture-a.png", (0, 0, 0, 255))
    capture_b = _write_image(tmp_path / "capture-b.png", (0, 0, 0, 255))

    results = analyze_frames([capture_a, capture_b], tmp_path / "out")

    assert results["capture_ok"] is False
    assert results["capture_black_frames"] == [str(capture_a), str(capture_b)]
    assert results["pass"] is False


def test_analyze_frames_reports_motion_and_failures(tmp_path):
    frame_a = _make_frame(tmp_path / "frame-a.png", custom_shift=0, stock_shift=1)
    frame_b = _make_frame(tmp_path / "frame-b.png", custom_shift=12, stock_shift=8, custom_strip_offset=5)

    results = analyze_frames(
        [frame_a, frame_b],
        tmp_path / "out",
        thresholds=Thresholds(
            max_strip_mean_abs_diff=5.0,
            min_graph_motion_mean_abs_diff=0.5,
            min_graph_changed_ratio=0.001,
            min_motion_ratio_vs_stock=0.1,
            max_separator_offset_px=1.0,
            min_separator_contrast=1.0,
            max_geometry_center_delta_px=1.0,
            max_geometry_size_delta_px=2.0,
            max_geometry_region_diff=10.0,
        ),
    )

    assert results["capture_ok"] is True
    assert results["graph_motion_mean_abs_diff"] > 0
    assert results["graph_changed_ratio"] > 0
    assert any(check["id"] == "geometry_channel_group" and not check["ok"] for check in results["checks"])
    assert results["failures"]
