"""Exercise shared effect-port and package-report ABI behavior on macOS."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="original module host is a Darwin probe")
def test_native_module_host_stock(tmp_path):
    compiler = shutil.which("clang++")
    if not compiler:
        pytest.skip("clang++ is unavailable")
    source = Path(__file__).parent / "native" / "module_host_stock.cpp"
    executable = tmp_path / "module_host_stock"
    subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-Wno-cast-function-type-mismatch", str(source), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
