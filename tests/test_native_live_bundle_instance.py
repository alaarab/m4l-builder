"""Portable original-bundle owner checks; synthetic callbacks are not device parity."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("sanitize", [False, True], ids=["optimized", "asan-ubsan"])
def test_original_live_bundle_instance(tmp_path, sanitize):
    compiler = shutil.which("clang++") or shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++17 compiler is required for the bundle instance check")
    root = Path(__file__).resolve().parents[1]
    executable = tmp_path / "bundle-instance"
    options = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"] if sanitize else ["-O2"]
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            *options,
            "-I",
            str(root / "src/m4l_builder/native"),
            str(root / "tests/native/live_bundle_instance.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = subprocess.run(
        [str(executable)], check=True, capture_output=True, text=True, timeout=15
    )
    assert '"passed":true' in result.stdout
    assert '"original_device_parity":false' in result.stdout
