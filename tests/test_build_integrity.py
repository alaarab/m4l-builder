"""Exercise the public build paths with defects that once slipped through."""

import os

import pytest

from m4l_builder import AudioEffect
from m4l_builder.assets import Asset
from m4l_builder.ui import v8ui
from m4l_builder.validation import BuildValidationError

JS = """mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
function paint() {}
function bang() { mgraphics.redraw(); }
"""


def bad_handler(*, nested=False):
    device = AudioEffect("Handler", 200, 120)
    device.add_v8ui("view", [0, 0, 180, 100], js_code=JS)
    device.add_newobj("send", "prepend missing_handler", numinlets=1, numoutlets=1)
    device.add_line("send", 0, "view", 0)
    if nested:
        boxes, lines = device.boxes[2:], device.lines[:]
        device.boxes = device.boxes[:2]
        device.lines = []
        device.add_box({"box": {"id": "nested", "maxclass": "newobj", "text": "p nested",
                                "numinlets": 0, "numoutlets": 0,
                                "patcher": {"boxes": boxes, "lines": lines}}})
    return device


@pytest.mark.parametrize("policy", [None, "error"])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("frozen", [False, True])
def test_real_registered_js_missing_handler_is_rejected(policy, nested, frozen):
    with pytest.raises(BuildValidationError, match="missing_handler"):
        bad_handler(nested=nested).to_bytes(validate=policy, freeze=frozen)


def test_warn_reports_handler_issues_without_rejecting():
    with pytest.warns(UserWarning, match="missing_handler"):
        bad_handler().to_bytes(validate="warn")


@pytest.mark.parametrize("policy", [None, "error"])
def test_object_declarations_checked_in_both_policies(policy):
    device = AudioEffect("Arity", 200, 120)
    device.add_newobj("init", "live.thisdevice", numinlets=1, numoutlets=2,
                      outlettype=["bang", "int"])
    with pytest.raises(BuildValidationError, match="box-declaration-mismatch"):
        device.to_bytes(validate=policy)


@pytest.mark.parametrize("frozen", [False, True])
@pytest.mark.parametrize("write", [False, True])
def test_missing_scripts_rejected_by_every_output_path(tmp_path, frozen, write):
    device = AudioEffect("Missing", 200, 120)
    device.add_box(v8ui("view", [0, 0, 100, 100], js_filename="missing.js"))
    with pytest.raises(ValueError, match="NOT registered"):
        if write:
            device.build(str(tmp_path / "Missing.amxd"), freeze=frozen)
        else:
            device.to_bytes(freeze=frozen)
    assert not list(tmp_path.iterdir())


def test_failed_asset_stage_leaves_existing_installation_intact(tmp_path, monkeypatch):
    device = AudioEffect("Original", 200, 120)
    device.register_asset("script.js", "original")
    dest = tmp_path / "Original.amxd"
    device.build(str(dest))
    original = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    device.name = "Replacement"
    device.register_asset("script.js", "changed")

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(Asset, "write_to", fail)
    with pytest.raises(OSError, match="disk full"):
        device.build(str(dest))
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == original


def test_failed_commit_restores_old_assets_and_removes_new_ones(tmp_path, monkeypatch):
    device = AudioEffect("Original", 200, 120)
    device.register_asset("script.js", "original")
    dest = tmp_path / "Original.amxd"
    device.build(str(dest))
    original = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    device.name = "Replacement"
    device.register_asset("script.js", "changed")
    device.register_asset("new.js", "new")
    replace = os.replace

    def fail_binary_commit(src, target):
        if target == dest:
            raise OSError("binary replacement failed")
        replace(src, target)

    monkeypatch.setattr(os, "replace", fail_binary_commit)
    with pytest.raises(OSError, match="replacement failed"):
        device.build(str(dest))
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == original
