"""Physical screenshot/video harness for stock-vs-custom Spectrum validation.

This harness is intentionally machine-local and layout-specific. It stabilizes a
known Ableton Live view, loads stock Spectrum and the custom Spectrum Analyzer
side by side on a dedicated harness track, captures a short burst of full-screen
frames, and scores the visible result with concrete thresholds.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import socket
import struct
import subprocess
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

try:
    from PIL import Image, ImageChops, ImageStat
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only on machines without Pillow
    raise SystemExit(
        "Pillow is required for tools/live_visual_harness.py. "
        "Use an interpreter with Pillow installed, for example `python3` on this machine."
    ) from exc


DEFAULT_OUTPUT_DIR = Path("/tmp/live-visual-harness")
DEFAULT_LIVE_APP = "Ableton Live 12 Suite"
DEFAULT_TRACK_NAME = "Spectrum Harness"
DEFAULT_STOCK_URI = "query:AudioFx#Spectrum"
DEFAULT_CUSTOM_URI = (
    "query:UserLibrary#Presets:Audio%20Effects:Max%20Audio%20Effect:Spectrum%20Analyzer.amxd"
)
DEFAULT_BUILD_COMMAND = "uv run python plugins/spectrum_analyzer/build.py"
DEFAULT_SIGNAL_PATH = DEFAULT_OUTPUT_DIR / "spectrum-harness-source.wav"
LIVEMCP_HOST = "127.0.0.1"
LIVEMCP_PORT = 9877


@dataclass(frozen=True)
class LayoutProfile:
    stock_device_box: tuple[int, int, int, int]
    custom_device_box: tuple[int, int, int, int]
    stock_strip_box: tuple[int, int, int, int]
    custom_strip_box: tuple[int, int, int, int]
    stock_graph_box: tuple[int, int, int, int]
    custom_graph_box: tuple[int, int, int, int]
    separator_rows: tuple[int, ...]
    control_regions: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)


DEFAULT_PROFILE = LayoutProfile(
    # Tuned to the current Live layout on this machine.
    stock_device_box=(1020, 558, 1430, 760),
    custom_device_box=(1448, 558, 1856, 760),
    stock_strip_box=(0, 23, 134, 181),
    custom_strip_box=(0, 22, 134, 180),
    stock_graph_box=(134, 22, 386, 180),
    custom_graph_box=(134, 22, 396, 180),
    separator_rows=(22, 52, 101),
    control_regions={
        "input_meter": (0, 0, 9, 158),
        "block_menu": (56, 1, 73, 13),
        "channel_group": (56, 31, 54, 13),
        "refresh_box": (56, 59, 48, 13),
        "avg_box": (56, 78, 48, 13),
        "graph_group": (56, 110, 72, 13),
        "scale_group": (56, 128, 72, 13),
        "auto_button": (15, 146, 34, 12),
        "range_group": (56, 146, 72, 12),
    },
)


@dataclass(frozen=True)
class Thresholds:
    max_strip_mean_abs_diff: float = 18.0
    min_graph_motion_mean_abs_diff: float = 1.0
    min_graph_changed_ratio: float = 0.010
    min_motion_ratio_vs_stock: float = 0.20
    max_separator_offset_px: float = 2.0
    min_separator_contrast: float = 3.5
    max_geometry_center_delta_px: float = 5.0
    max_geometry_size_delta_px: float = 8.0
    max_geometry_region_diff: float = 42.0


DEFAULT_THRESHOLDS = Thresholds()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _run(command: Iterable[str]) -> None:
    subprocess.run(list(command), check=True)


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def rect_to_box(rect: Sequence[int]) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    return (x, y, x + w, y + h)


def crop_box(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Crop a box from an image."""
    return image.crop(box)


def mean_abs_diff(img_a: Image.Image, img_b: Image.Image) -> float:
    """Return mean absolute per-channel pixel difference."""
    diff = ImageChops.difference(img_a, img_b)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / len(stat.mean)


def mean_luminance(image: Image.Image) -> float:
    """Return mean image luminance on a 0-255 scale."""
    stat = ImageStat.Stat(image.convert("L"))
    return stat.mean[0]


def is_near_black(image: Image.Image, threshold: float = 1.0) -> bool:
    """Return True when a capture is effectively all black."""
    return mean_luminance(image) <= threshold


def changed_pixel_ratio(img_a: Image.Image, img_b: Image.Image, threshold: int = 10) -> float:
    """Return the ratio of pixels whose luminance changed beyond a threshold."""
    diff = ImageChops.difference(img_a.convert("L"), img_b.convert("L"))
    mask = diff.point(lambda value: 255 if value >= threshold else 0)
    stat = ImageStat.Stat(mask)
    total_pixels = mask.size[0] * mask.size[1]
    if total_pixels <= 0:
        return 0.0
    return (stat.sum[0] / 255.0) / total_pixels


def estimate_region_background(region: Image.Image) -> int:
    """Estimate a region background luminance from the four corners."""
    gray = region.convert("L")
    width, height = gray.size
    samples = [
        gray.getpixel((0, 0)),
        gray.getpixel((max(width - 1, 0), 0)),
        gray.getpixel((0, max(height - 1, 0))),
        gray.getpixel((max(width - 1, 0), max(height - 1, 0))),
    ]
    return int(sum(samples) / len(samples))


def foreground_bbox(region: Image.Image, threshold: int = 14) -> tuple[int, int, int, int] | None:
    """Return the bounding box of foreground pixels inside a control region."""
    gray = region.convert("L")
    background = estimate_region_background(region)
    background_fill = Image.new("L", gray.size, background)
    diff = ImageChops.difference(gray, background_fill)
    mask = diff.point(lambda value: 255 if value >= threshold else 0)
    return mask.getbbox()


def detect_separator(strip: Image.Image, expected_y: int, search_radius: int = 4) -> dict:
    """Locate a horizontal separator near an expected row."""
    gray = strip.convert("L")
    width, height = gray.size
    best_y = expected_y
    best_contrast = -1.0
    start = max(expected_y - search_radius, 1)
    end = min(expected_y + search_radius, height - 2)
    for y in range(start, end + 1):
        row_mean = ImageStat.Stat(gray.crop((0, y, width, y + 1))).mean[0]
        neighbor_mean = ImageStat.Stat(gray.crop((0, y - 1, width, y + 2))).mean[0]
        contrast = neighbor_mean - row_mean
        if contrast > best_contrast:
            best_contrast = contrast
            best_y = y
    return {
        "expected_y": expected_y,
        "detected_y": best_y,
        "offset_px": abs(best_y - expected_y),
        "contrast": best_contrast,
    }


def geometry_metrics(
    stock_strip: Image.Image,
    custom_strip: Image.Image,
    control_regions: dict[str, tuple[int, int, int, int]],
) -> list[dict]:
    """Measure bounding-box and region-diff drift for each control group."""
    metrics = []
    for name, rect in control_regions.items():
        stock_region = crop_box(stock_strip, rect_to_box(rect))
        custom_region = crop_box(custom_strip, rect_to_box(rect))
        stock_bbox = foreground_bbox(stock_region)
        custom_bbox = foreground_bbox(custom_region)
        region_diff = mean_abs_diff(stock_region, custom_region)

        if stock_bbox is None or custom_bbox is None:
            metrics.append(
                {
                    "name": name,
                    "stock_bbox": stock_bbox,
                    "custom_bbox": custom_bbox,
                    "region_mean_abs_diff": region_diff,
                    "center_delta_px": None,
                    "size_delta_px": None,
                }
            )
            continue

        stock_center = (
            (stock_bbox[0] + stock_bbox[2]) / 2.0,
            (stock_bbox[1] + stock_bbox[3]) / 2.0,
        )
        custom_center = (
            (custom_bbox[0] + custom_bbox[2]) / 2.0,
            (custom_bbox[1] + custom_bbox[3]) / 2.0,
        )
        stock_size = (stock_bbox[2] - stock_bbox[0], stock_bbox[3] - stock_bbox[1])
        custom_size = (custom_bbox[2] - custom_bbox[0], custom_bbox[3] - custom_bbox[1])
        center_delta = math.hypot(stock_center[0] - custom_center[0], stock_center[1] - custom_center[1])
        size_delta = math.hypot(stock_size[0] - custom_size[0], stock_size[1] - custom_size[1])
        metrics.append(
            {
                "name": name,
                "stock_bbox": stock_bbox,
                "custom_bbox": custom_bbox,
                "region_mean_abs_diff": region_diff,
                "center_delta_px": center_delta,
                "size_delta_px": size_delta,
            }
        )
    return metrics


def build_device_artifacts(
    first_frame: Image.Image,
    last_frame: Image.Image,
    output_dir: Path,
    profile: LayoutProfile,
) -> dict:
    """Save the primary device/strip/graph artifact images."""
    stock_device = crop_box(first_frame, profile.stock_device_box)
    custom_device = crop_box(first_frame, profile.custom_device_box)
    stock_strip = crop_box(stock_device, profile.stock_strip_box)
    custom_strip = crop_box(custom_device, profile.custom_strip_box)
    stock_graph_first = crop_box(stock_device, profile.stock_graph_box)
    custom_graph_first = crop_box(custom_device, profile.custom_graph_box)
    stock_graph_last = crop_box(crop_box(last_frame, profile.stock_device_box), profile.stock_graph_box)
    custom_graph_last = crop_box(crop_box(last_frame, profile.custom_device_box), profile.custom_graph_box)

    stock_device_path = output_dir / "stock-device.png"
    custom_device_path = output_dir / "custom-device.png"
    stock_strip_path = output_dir / "stock-strip.png"
    custom_strip_path = output_dir / "custom-strip.png"
    stock_graph_first_path = output_dir / "stock-graph-first.png"
    custom_graph_first_path = output_dir / "custom-graph-first.png"
    stock_graph_last_path = output_dir / "stock-graph-last.png"
    custom_graph_last_path = output_dir / "custom-graph-last.png"

    stock_device.save(stock_device_path)
    custom_device.save(custom_device_path)
    stock_strip.save(stock_strip_path)
    custom_strip.save(custom_strip_path)
    stock_graph_first.save(stock_graph_first_path)
    custom_graph_first.save(custom_graph_first_path)
    stock_graph_last.save(stock_graph_last_path)
    custom_graph_last.save(custom_graph_last_path)

    strip_diff = ImageChops.difference(stock_strip, custom_strip)
    strip_diff_path = output_dir / "strip-diff.png"
    strip_diff.save(strip_diff_path)

    side_by_side = Image.new("RGBA", (stock_device.width + custom_device.width, max(stock_device.height, custom_device.height)))
    side_by_side.paste(stock_device, (0, 0))
    side_by_side.paste(custom_device, (stock_device.width, 0))
    side_by_side_path = output_dir / "device-side-by-side.png"
    side_by_side.save(side_by_side_path)

    return {
        "stock_device": stock_device_path,
        "custom_device": custom_device_path,
        "stock_strip": stock_strip_path,
        "custom_strip": custom_strip_path,
        "strip_diff": strip_diff_path,
        "stock_graph_first": stock_graph_first_path,
        "custom_graph_first": custom_graph_first_path,
        "stock_graph_last": stock_graph_last_path,
        "custom_graph_last": custom_graph_last_path,
        "device_side_by_side": side_by_side_path,
        "stock_strip_image": stock_strip,
        "custom_strip_image": custom_strip,
    }


def graph_motion_metrics(
    frames: Sequence[Path],
    output_dir: Path,
    profile: LayoutProfile,
) -> dict:
    """Measure graph motion over a burst of captured frames."""
    stock_graphs = []
    custom_graphs = []
    for frame_path in frames:
        frame = Image.open(frame_path).convert("RGBA")
        stock_graphs.append(crop_box(crop_box(frame, profile.stock_device_box), profile.stock_graph_box))
        custom_graphs.append(crop_box(crop_box(frame, profile.custom_device_box), profile.custom_graph_box))

    stock_diffs = []
    custom_diffs = []
    stock_changed = []
    custom_changed = []
    pairwise_paths = []
    for index in range(len(frames) - 1):
        stock_a = stock_graphs[index]
        stock_b = stock_graphs[index + 1]
        custom_a = custom_graphs[index]
        custom_b = custom_graphs[index + 1]

        stock_diff = ImageChops.difference(stock_a, stock_b)
        custom_diff = ImageChops.difference(custom_a, custom_b)
        stock_diff_path = output_dir / f"stock-graph-diff-{index:03d}.png"
        custom_diff_path = output_dir / f"custom-graph-diff-{index:03d}.png"
        stock_diff.save(stock_diff_path)
        custom_diff.save(custom_diff_path)
        pairwise_paths.append(
            {
                "stock": stock_diff_path,
                "custom": custom_diff_path,
            }
        )
        stock_diffs.append(mean_abs_diff(stock_a, stock_b))
        custom_diffs.append(mean_abs_diff(custom_a, custom_b))
        stock_changed.append(changed_pixel_ratio(stock_a, stock_b))
        custom_changed.append(changed_pixel_ratio(custom_a, custom_b))

    custom_motion = sum(custom_diffs) / len(custom_diffs) if custom_diffs else 0.0
    stock_motion = sum(stock_diffs) / len(stock_diffs) if stock_diffs else 0.0
    custom_ratio = sum(custom_changed) / len(custom_changed) if custom_changed else 0.0
    stock_ratio = sum(stock_changed) / len(stock_changed) if stock_changed else 0.0

    return {
        "stock_graph_motion_mean_abs_diff": stock_motion,
        "graph_motion_mean_abs_diff": custom_motion,
        "stock_graph_changed_ratio": stock_ratio,
        "graph_changed_ratio": custom_ratio,
        "motion_ratio_vs_stock": (custom_motion / stock_motion) if stock_motion > 0 else 0.0,
        "pairwise_motion_diffs": [
            {
                "stock_mean_abs_diff": stock_diffs[index],
                "custom_mean_abs_diff": custom_diffs[index],
                "stock_changed_ratio": stock_changed[index],
                "custom_changed_ratio": custom_changed[index],
                "stock_diff": pairwise_paths[index]["stock"],
                "custom_diff": pairwise_paths[index]["custom"],
            }
            for index in range(len(pairwise_paths))
        ],
    }


def evaluate_checks(
    results: dict,
    thresholds: Thresholds,
) -> list[dict]:
    """Turn raw metrics into explicit pass/fail checks."""
    checks = []

    def add_check(check_id: str, ok: bool, measured, threshold, detail: str) -> None:
        checks.append(
            {
                "id": check_id,
                "ok": ok,
                "measured": _jsonable(measured),
                "threshold": _jsonable(threshold),
                "detail": detail,
            }
        )

    add_check(
        "capture_ok",
        bool(results.get("capture_ok")),
        results.get("capture_black_frames", []),
        [],
        "All captured frames must be non-black and within the configured layout boxes.",
    )

    if not results.get("capture_ok"):
        return checks

    add_check(
        "strip_similarity",
        results["strip_mean_abs_diff"] <= thresholds.max_strip_mean_abs_diff,
        results["strip_mean_abs_diff"],
        {"max": thresholds.max_strip_mean_abs_diff},
        "The custom control strip should stay visually close to the stock strip crop.",
    )

    add_check(
        "graph_motion_mean_abs_diff",
        results["graph_motion_mean_abs_diff"] >= thresholds.min_graph_motion_mean_abs_diff,
        results["graph_motion_mean_abs_diff"],
        {"min": thresholds.min_graph_motion_mean_abs_diff},
        "The custom graph must visibly move across captured frames.",
    )
    add_check(
        "graph_changed_ratio",
        results["graph_changed_ratio"] >= thresholds.min_graph_changed_ratio,
        results["graph_changed_ratio"],
        {"min": thresholds.min_graph_changed_ratio},
        "Graph motion must change a meaningful portion of the custom graph crop.",
    )
    add_check(
        "motion_ratio_vs_stock",
        results["motion_ratio_vs_stock"] >= thresholds.min_motion_ratio_vs_stock,
        results["motion_ratio_vs_stock"],
        {"min": thresholds.min_motion_ratio_vs_stock},
        "The custom graph should retain a minimum share of the stock graph's motion.",
    )

    for separator in results["separator_metrics"]:
        ok = (
            separator["offset_px"] <= thresholds.max_separator_offset_px
            and separator["contrast"] >= thresholds.min_separator_contrast
        )
        add_check(
            f"separator_{separator['expected_y']}",
            ok,
            separator,
            {
                "max_offset_px": thresholds.max_separator_offset_px,
                "min_contrast": thresholds.min_separator_contrast,
            },
            "Each section separator should be present and aligned in the custom strip.",
        )

    for metric in results["geometry_metrics"]:
        ok = (
            metric["stock_bbox"] is not None
            and metric["custom_bbox"] is not None
            and metric["center_delta_px"] <= thresholds.max_geometry_center_delta_px
            and metric["size_delta_px"] <= thresholds.max_geometry_size_delta_px
            and metric["region_mean_abs_diff"] <= thresholds.max_geometry_region_diff
        )
        add_check(
            f"geometry_{metric['name']}",
            ok,
            metric,
            {
                "max_center_delta_px": thresholds.max_geometry_center_delta_px,
                "max_size_delta_px": thresholds.max_geometry_size_delta_px,
                "max_region_diff": thresholds.max_geometry_region_diff,
            },
            "Each control region should keep its visible footprint aligned with stock.",
        )

    return checks


def analyze_frames(
    frames: Sequence[Path],
    output_dir: Path,
    profile: LayoutProfile = DEFAULT_PROFILE,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> dict:
    """Analyze a burst of captured full-screen frames."""
    _ensure_dir(output_dir)
    if len(frames) < 2:
        raise ValueError("Need at least two frames to measure graph motion")

    images = [Image.open(path).convert("RGBA") for path in frames]
    frame_luminance = [mean_luminance(image) for image in images]
    black_frames = [str(path) for path, image in zip(frames, images) if is_near_black(image)]

    results = {
        "frame_paths": [str(path) for path in frames],
        "frame_count": len(frames),
        "frame_luminance": frame_luminance,
        "capture_black_frames": black_frames,
        "capture_ok": not black_frames,
        "profile": _jsonable(asdict(profile)),
        "thresholds": _jsonable(asdict(thresholds)),
    }
    if black_frames:
        results["capture_failure_reason"] = "black_frames"
        results["capture_hint"] = (
            "Full-screen frames came back black. On macOS this usually means the calling "
            "app lacks Screen Recording permission, or the capture backend returned protected frames."
        )
        results["checks"] = evaluate_checks(results, thresholds)
        results["pass"] = False
        results["failures"] = [check for check in results["checks"] if not check["ok"]]
        return results

    artifacts = build_device_artifacts(images[0], images[-1], output_dir, profile)
    stock_strip = artifacts.pop("stock_strip_image")
    custom_strip = artifacts.pop("custom_strip_image")
    results.update({key: str(value) for key, value in artifacts.items()})
    results["strip_mean_abs_diff"] = mean_abs_diff(stock_strip, custom_strip)

    separator_metrics = [detect_separator(custom_strip, row) for row in profile.separator_rows]
    geometry = geometry_metrics(stock_strip, custom_strip, profile.control_regions)
    motion = graph_motion_metrics(frames, output_dir, profile)

    results["separator_metrics"] = separator_metrics
    results["geometry_metrics"] = geometry
    results.update(
        {
            "stock_graph_motion_mean_abs_diff": motion["stock_graph_motion_mean_abs_diff"],
            "graph_motion_mean_abs_diff": motion["graph_motion_mean_abs_diff"],
            "stock_graph_changed_ratio": motion["stock_graph_changed_ratio"],
            "graph_changed_ratio": motion["graph_changed_ratio"],
            "motion_ratio_vs_stock": motion["motion_ratio_vs_stock"],
            "pairwise_motion_diffs": _jsonable(motion["pairwise_motion_diffs"]),
        }
    )

    results["checks"] = evaluate_checks(results, thresholds)
    results["failures"] = [check for check in results["checks"] if not check["ok"]]
    results["pass"] = not results["failures"]
    return results


def capture_live_frame(output_path: Path, app_name: str = DEFAULT_LIVE_APP) -> Path:
    """Activate Live and capture the full screen."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run(["osascript", "-e", f'tell application "{app_name}" to activate'])
    time.sleep(0.2)
    _run(["screencapture", "-x", str(output_path)])
    return output_path


def capture_live_frames(
    output_dir: Path,
    *,
    frames: int,
    delay_seconds: float,
    app_name: str = DEFAULT_LIVE_APP,
) -> list[Path]:
    """Capture a burst of full-screen frames from Ableton Live."""
    _ensure_dir(output_dir)
    paths = []
    for index in range(frames):
        frame_path = output_dir / f"live-frame-{index:03d}.png"
        capture_live_frame(frame_path, app_name=app_name)
        paths.append(frame_path)
        if index < frames - 1:
            time.sleep(delay_seconds)
    return paths


def maybe_encode_video(frames: Sequence[Path], output_dir: Path, fps: float) -> Path | None:
    """Encode the capture burst as an MP4 when ffmpeg is available."""
    if not frames or shutil.which("ffmpeg") is None:
        return None
    video_path = output_dir / "capture-burst.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            f"{fps:.4f}",
            "-i",
            str(output_dir / "live-frame-%03d.png"),
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ]
    )
    return video_path


class LiveMCPClient:
    """Minimal stdlib TCP client for the existing LiveMCP socket transport."""

    def __init__(self, host: str = LIVEMCP_HOST, port: int = LIVEMCP_PORT, timeout: float = 15.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.request_id = 0

    def send(self, command: str, params: dict | None = None) -> dict:
        self.request_id += 1
        payload = json.dumps(
            {
                "id": self.request_id,
                "type": command,
                "params": params or {},
            }
        ).encode("utf-8") + b"\n"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.sendall(payload)
            buffer = b""
            while b"\n" not in buffer:
                chunk = sock.recv(8192)
                if not chunk:
                    raise ConnectionError("LiveMCP closed the socket")
                buffer += chunk
        message, _, _ = buffer.partition(b"\n")
        response = json.loads(message.decode("utf-8"))
        if response.get("status") == "error":
            raise RuntimeError(response.get("error") or response.get("message", "Unknown LiveMCP error"))
        return response.get("result", {})


def build_custom_device(build_command: str, output_dir: Path) -> dict:
    """Build the custom Spectrum Analyzer into the User Library."""
    _ensure_dir(output_dir)
    log_path = output_dir / "build.log"
    result = subprocess.run(
        build_command,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    )
    log_path.write_text((result.stdout or "") + (result.stderr or ""))
    return {
        "build_command": build_command,
        "build_log": str(log_path),
    }


def ensure_test_signal(output_path: Path, *, duration_seconds: float = 8.0, sample_rate: int = 48000) -> Path:
    """Generate a deterministic stereo analyzer test clip."""
    _ensure_dir(output_path.parent)
    rng = random.Random(1337)
    total_frames = int(duration_seconds * sample_rate)
    phase_a = 0.0
    phase_b = 0.0
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for index in range(total_frames):
            t = index / sample_rate
            sweep_hz = 120.0 + 7800.0 * (t / duration_seconds)
            wobble_hz = 0.15 + 0.05 * math.sin(2.0 * math.pi * 0.12 * t)
            phase_a += (2.0 * math.pi * sweep_hz) / sample_rate
            phase_b += (2.0 * math.pi * (220.0 + 900.0 * wobble_hz)) / sample_rate
            noise = (rng.random() * 2.0) - 1.0
            envelope = 0.6 + 0.4 * math.sin(2.0 * math.pi * 0.31 * t)
            left = (
                0.28 * math.sin(phase_a)
                + 0.18 * math.sin(2.0 * math.pi * 58.0 * t)
                + 0.08 * noise * envelope
            )
            right = (
                0.24 * math.sin(phase_a * 0.91 + 0.6)
                + 0.16 * math.sin(phase_b)
                + 0.08 * noise * (1.0 - 0.35 * math.sin(2.0 * math.pi * 0.21 * t))
            )
            fade = min(1.0, t * 4.0, (duration_seconds - t) * 4.0)
            left = max(-0.95, min(0.95, left * fade))
            right = max(-0.95, min(0.95, right * fade))
            frames.extend(struct.pack("<hh", int(left * 32767.0), int(right * 32767.0)))
        wav_file.writeframes(frames)
    return output_path


def ensure_harness_track(client: LiveMCPClient, track_name: str) -> int:
    """Create or reuse a dedicated harness track."""
    tracks = client.send("get_all_tracks_info", {}).get("tracks", [])
    for track in tracks:
        if track.get("name") == track_name:
            return int(track["index"])

    client.send("create_audio_track", {"index": -1})
    tracks = client.send("get_all_tracks_info", {}).get("tracks", [])
    track_index = max(int(track["index"]) for track in tracks)
    client.send("set_track_name", {"track_index": track_index, "name": track_name})
    return track_index


def clear_track(client: LiveMCPClient, track_index: int) -> None:
    """Delete existing devices and clip content on the harness track."""
    track_info = client.send("get_track_info", {"track_index": track_index})
    for device in reversed(track_info.get("devices", [])):
        client.send(
            "delete_device",
            {
                "track_index": track_index,
                "device_index": int(device["index"]),
            },
        )
    for slot in track_info.get("clip_slots", []):
        if slot.get("has_clip"):
            client.send("delete_clip", {"track_index": track_index, "clip_index": int(slot["index"])})


def prepare_live_comparison(
    *,
    build_command: str,
    stock_uri: str,
    custom_uri: str,
    track_name: str,
    signal_path: Path,
    settle_seconds: float,
) -> dict:
    """Build the custom device and stage the stock/custom comparison in Live."""
    client = LiveMCPClient()
    build_info = build_custom_device(build_command, signal_path.parent)
    ensure_test_signal(signal_path)

    track_index = ensure_harness_track(client, track_name)
    clear_track(client, track_index)
    client.send("set_selected_track", {"track_index": track_index})
    client.send("show_view", {"view_name": "Browser"})
    client.send("show_view", {"view_name": "Arranger"})
    client.send("show_view", {"view_name": "Detail"})
    client.send("show_view", {"view_name": "Detail/DeviceChain"})
    client.send("load_browser_item", {"track_index": track_index, "item_uri": stock_uri})
    client.send("load_browser_item", {"track_index": track_index, "item_uri": custom_uri})
    client.send(
        "create_session_audio_clip",
        {
            "track_index": track_index,
            "clip_index": 0,
            "file_path": str(signal_path),
        },
    )
    client.send("fire_clip", {"track_index": track_index, "clip_index": 0})
    time.sleep(settle_seconds)

    track_info = client.send("get_track_info", {"track_index": track_index})
    return {
        **build_info,
        "track_index": track_index,
        "track_name": track_name,
        "signal_path": str(signal_path),
        "track_info": track_info,
    }


def run_harness(
    *,
    output_dir: Path,
    delay_seconds: float,
    frames: int,
    app_name: str,
    prepare_live: bool,
    build_command: str,
    stock_uri: str,
    custom_uri: str,
    track_name: str,
    signal_path: Path,
    settle_seconds: float,
    profile: LayoutProfile = DEFAULT_PROFILE,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> dict:
    """Capture a burst of Live frames and return scored visual metrics."""
    _ensure_dir(output_dir)
    setup = None
    if prepare_live:
        setup = prepare_live_comparison(
            build_command=build_command,
            stock_uri=stock_uri,
            custom_uri=custom_uri,
            track_name=track_name,
            signal_path=signal_path,
            settle_seconds=settle_seconds,
        )

    frame_paths = capture_live_frames(
        output_dir,
        frames=frames,
        delay_seconds=delay_seconds,
        app_name=app_name,
    )
    results = analyze_frames(frame_paths, output_dir, profile=profile, thresholds=thresholds)
    fps = 1.0 / max(delay_seconds, 0.001)
    video_path = maybe_encode_video(frame_paths, output_dir, fps=fps)
    if video_path is not None:
        results["capture_video"] = str(video_path)
    if setup is not None:
        results["live_setup"] = _jsonable(setup)
    return results


def analyze_existing_captures(
    capture_paths: Sequence[Path],
    output_dir: Path,
    *,
    profile: LayoutProfile = DEFAULT_PROFILE,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> dict:
    """Analyze an existing set of captured frames."""
    return analyze_frames(capture_paths, output_dir, profile=profile, thresholds=thresholds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--delay", type=float, default=0.50)
    parser.add_argument("--frames", type=int, default=4)
    parser.add_argument("--app-name", default=DEFAULT_LIVE_APP)
    parser.add_argument("--prepare-live", action="store_true")
    parser.add_argument("--build-command", default=DEFAULT_BUILD_COMMAND)
    parser.add_argument("--stock-uri", default=DEFAULT_STOCK_URI)
    parser.add_argument("--custom-uri", default=DEFAULT_CUSTOM_URI)
    parser.add_argument("--track-name", default=DEFAULT_TRACK_NAME)
    parser.add_argument("--signal-path", type=Path, default=DEFAULT_SIGNAL_PATH)
    parser.add_argument("--settle-seconds", type=float, default=1.5)
    parser.add_argument("--capture", type=Path, action="append")
    parser.add_argument("--max-strip-diff", type=float, default=DEFAULT_THRESHOLDS.max_strip_mean_abs_diff)
    parser.add_argument("--min-motion-diff", type=float, default=DEFAULT_THRESHOLDS.min_graph_motion_mean_abs_diff)
    parser.add_argument("--min-changed-ratio", type=float, default=DEFAULT_THRESHOLDS.min_graph_changed_ratio)
    parser.add_argument("--min-motion-ratio-vs-stock", type=float, default=DEFAULT_THRESHOLDS.min_motion_ratio_vs_stock)
    parser.add_argument("--max-separator-offset", type=float, default=DEFAULT_THRESHOLDS.max_separator_offset_px)
    parser.add_argument("--min-separator-contrast", type=float, default=DEFAULT_THRESHOLDS.min_separator_contrast)
    parser.add_argument("--max-geometry-center-delta", type=float, default=DEFAULT_THRESHOLDS.max_geometry_center_delta_px)
    parser.add_argument("--max-geometry-size-delta", type=float, default=DEFAULT_THRESHOLDS.max_geometry_size_delta_px)
    parser.add_argument("--max-geometry-region-diff", type=float, default=DEFAULT_THRESHOLDS.max_geometry_region_diff)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    thresholds = Thresholds(
        max_strip_mean_abs_diff=args.max_strip_diff,
        min_graph_motion_mean_abs_diff=args.min_motion_diff,
        min_graph_changed_ratio=args.min_changed_ratio,
        min_motion_ratio_vs_stock=args.min_motion_ratio_vs_stock,
        max_separator_offset_px=args.max_separator_offset,
        min_separator_contrast=args.min_separator_contrast,
        max_geometry_center_delta_px=args.max_geometry_center_delta,
        max_geometry_size_delta_px=args.max_geometry_size_delta,
        max_geometry_region_diff=args.max_geometry_region_diff,
    )

    if args.capture:
        results = analyze_existing_captures(
            args.capture,
            args.output_dir,
            profile=DEFAULT_PROFILE,
            thresholds=thresholds,
        )
    else:
        results = run_harness(
            output_dir=args.output_dir,
            delay_seconds=args.delay,
            frames=args.frames,
            app_name=args.app_name,
            prepare_live=args.prepare_live,
            build_command=args.build_command,
            stock_uri=args.stock_uri,
            custom_uri=args.custom_uri,
            track_name=args.track_name,
            signal_path=args.signal_path,
            settle_seconds=args.settle_seconds,
            profile=DEFAULT_PROFILE,
            thresholds=thresholds,
        )

    print(json.dumps(_jsonable(results), indent=2))
    if args.enforce and not results.get("pass", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
