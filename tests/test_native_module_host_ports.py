"""Reject wrong channel arrays before entering an original module callback."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple LP64 Max ABI probe")
def test_native_module_host_ports(tmp_path: Path) -> None:
    compiler = shutil.which("clang++")
    if compiler is None:
        pytest.skip("clang++ is unavailable")
    source = Path(__file__).parent / "native" / "module_host_ports.cpp"
    executable = tmp_path / "module-host-ports"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
         "-Wno-cast-function-type-mismatch", "-fsanitize=undefined",
         "-fno-sanitize-recover=all", str(source), "-o", str(executable)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    result = subprocess.run(
        [str(executable)], check=True, capture_output=True, text=True, timeout=10,
    )
    assert "Compiled render port contracts: PASS" in result.stdout
