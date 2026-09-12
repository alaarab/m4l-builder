"""Shared original-module host ABI regression; does not certify any device."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def test_original_module_host_abi_and_callbacks(tmp_path):
    if sys.platform != "darwin":
        pytest.skip("The current original-module probe targets the macOS LP64 ABI")
    compiler = shutil.which("clang++")
    if compiler is None:
        pytest.skip("clang++ is required for the native probe")
    source = Path(__file__).parent / "native" / "module_host.cpp"
    executable = tmp_path / "module-host-tests"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
         "-Wno-cast-function-type-mismatch",  # Max's generic method registry requires signature casts.
         str(source), "-o", str(executable)],
        check=True, capture_output=True, text=True,
    )
    result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
    assert "lifecycle: PASS" in result.stdout
