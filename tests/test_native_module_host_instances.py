"""Independent original-module host contexts; no proprietary binary required."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple LP64 Max ABI probe")
def test_native_module_host_instances(tmp_path: Path) -> None:
    compiler = shutil.which("clang++")
    if compiler is None:
        pytest.skip("clang++ is unavailable")
    source = Path(__file__).parent / "native" / "module_host_instances.cpp"
    executable = tmp_path / "module-host-instances"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
         "-Wno-cast-function-type-mismatch", str(source), "-o", str(executable)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    result = subprocess.run(
        [str(executable)], check=True, capture_output=True, text=True, timeout=10,
    )
    assert "Independent DSP contexts" in result.stdout
    assert "PASS" in result.stdout
