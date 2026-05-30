"""Smoke tests: every shipped example builds a valid .amxd device.

Keeps the examples from bit-rotting as the API evolves.
"""

import importlib.util
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE_SCRIPTS = sorted(EXAMPLES_DIR.glob("[0-9]*.py"))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_examples_exist():
    assert EXAMPLE_SCRIPTS, "expected runnable example scripts in examples/"


@pytest.mark.parametrize("path", EXAMPLE_SCRIPTS, ids=lambda p: p.name)
def test_example_builds_valid_amxd(path):
    module = _load(path)
    assert hasattr(module, "build"), f"{path.name} must define build()"
    output = module.build()
    data = Path(output).read_bytes()
    assert data[:4] == b"ampf", f"{path.name} did not produce a valid .amxd"
