"""Shared fixtures for the test suite."""

import os
import subprocess
import sys

import pytest

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def _run_script(script_name):
    """Run an example script, return (returncode, output_path, stderr)."""
    script_path = os.path.join(EXAMPLES_DIR, script_name)
    if not os.path.exists(script_path):
        return None, None, None
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, timeout=30,
    )
    output_path = None
    for line in result.stdout.strip().split("\n"):
        if "->" in line:
            output_path = line.split("->")[-1].strip()
            break
    return result.returncode, output_path, result.stderr


@pytest.fixture(scope="session")
def built_examples(request):
    """Build all example scripts exactly once per test session.

    Returns a dict: {script_name: {"path": str, "ok": bool, "stderr": str}}
    """
    from tests.test_examples import EXAMPLE_SCRIPTS  # avoid circular at module level

    results = {}
    for script in EXAMPLE_SCRIPTS:
        rc, path, stderr = _run_script(script)
        if rc is None:
            results[script] = {"path": None, "ok": False, "stderr": "not found"}
        else:
            results[script] = {"path": path, "ok": rc == 0, "stderr": stderr or ""}
    return results
