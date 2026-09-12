"""Portable validation of the original-bundle host boundary, not original DSP."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_original_live_bundle_abi_boundary(tmp_path):
    compiler = shutil.which("clang++") or shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++17 compiler is required for the native ABI check")
    root = Path(__file__).resolve().parents[1]
    executable = tmp_path / "bundle-abi"
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(root / "src/m4l_builder/native"),
            str(root / "tests/native/live_bundle_abi.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    subprocess.run([str(executable)], check=True, capture_output=True, text=True, timeout=15)
