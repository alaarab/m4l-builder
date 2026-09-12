"""Compile and exercise complete original-engine parameter-bank validation."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_native_live_parameter_state(tmp_path: Path) -> None:
    compiler = shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        pytest.skip("A C++17 compiler is required for native parameter-state checks")
    root = Path(__file__).resolve().parents[1]
    executable = tmp_path / "live_parameter_state"
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(root / "tests" / "native" / "live_parameter_state.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    subprocess.run(
        [str(executable)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

