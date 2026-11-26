"""``m4l import``: an existing .amxd becomes a build script that rebuilds it.

The proof is a round trip through the real command line: build a device,
``m4l import`` it, ``m4l build`` the generated script, and compare the two
.amxd files box by box (IDs may differ). The comparison here is written
independently of the importer's own self-check, so a bug in that check can't
make these tests pass.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from m4l_builder import NEBULA, AudioEffect, Subpatcher, message
from m4l_builder.cli import main
from m4l_builder.container import build_amxd
from m4l_builder.freeze import freeze_amxd_file
from m4l_builder.importer import check_import, import_amxd, read_device, rebuild_from_script

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
HANDMADE = Path(__file__).resolve().parent / "fixtures" / "handmade"
HANDMADE_FILES = ("grit.gendsp", "helper.js", "pulse_view.js")


@pytest.fixture(autouse=True)
def user_library(tmp_path, monkeypatch):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))


# -- an independent equivalence check --------------------------------------- #

def _read_amxd(path: Path) -> tuple[bytes, dict]:
    """Type code and patcher of an unfrozen .amxd (header is 32 bytes)."""
    data = path.read_bytes()
    return data[8:12], json.loads(data[32:].rstrip(b"\x00").rstrip(b"\n"))["patcher"]


def _graph(patcher: dict) -> dict:
    """Boxes and patchlines with every box ID replaced by the box's content."""
    content = {}
    for entry in patcher.get("boxes", []):
        box = dict(entry["box"])
        box_id = box.pop("id")
        if isinstance(box.get("patcher"), dict):
            nested = box["patcher"]
            box["patcher"] = {
                **{k: v for k, v in nested.items() if k not in ("boxes", "lines")},
                **_graph(nested),
            }
        content[box_id] = json.dumps(box, sort_keys=True)
    lines = []
    for entry in patcher.get("lines", []):
        line = dict(entry["patchline"])
        (src, outlet), (dst, inlet) = line.pop("source"), line.pop("destination")
        lines.append(json.dumps([content[src], outlet, content[dst], inlet, line],
                                sort_keys=True))
    return {"boxes": sorted(content.values()), "lines": sorted(lines)}


def _device(path: Path) -> dict:
    """Everything that makes two devices equivalent, minus box IDs."""
    type_code, patcher = _read_amxd(path)
    deps = sorted(d["name"] for d in patcher.get("dependency_cache", []))
    return {
        "type": type_code,
        "size": [patcher["devicewidth"], patcher["openrect"][3]],
        "latency": patcher.get("latency", 0),
        "banks": patcher.get("parameters", {}).get("parameterbanks"),
        "dependencies": deps,
        "files": {name: (path.parent / name).read_bytes() for name in deps},
        **_graph(patcher),
    }


# -- source devices --------------------------------------------------------- #

def _example(name: str):
    def build(out_dir: Path) -> Path:
        assert main(["build", str(EXAMPLES / name), "--out", f"{out_dir}/"]) == 0
        (built,) = out_dir.glob("*.amxd")
        return built
    return build


METER_JS = """\
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
var level = 0;
function msg_float(v) { level = v; mgraphics.redraw(); }
function paint() {
    mgraphics.set_source_rgba(0.2, 0.8, 0.6, 1.0);
    mgraphics.rectangle(0, 0, box.rect[2] * level, 10);
    mgraphics.fill();
}
"""


def _kitchen_sink(out_dir: Path) -> Path:
    """A library-built device using what the examples don't: gen~ (embedded and
    as a .gendsp), a v8ui script, a subpatcher, a message box, more controls,
    Push banks and latency."""
    d = AudioEffect("Kitchen Sink", width=320, height=160, theme=NEBULA)
    d.add_panel("bg", [0, 0, 320, 160])
    d.add_comment("title", [8, 4, 120, 16], "Kitchen Sink")
    d.add_menu("mode", "Mode", [8, 24, 70, 16], options=["Soft", "Hard", "Fold"])
    d.add_tab("range", "Range", [90, 24, 90, 16], options=["Lo", "Hi"])
    d.add_slider("drive", "Drive", [8, 48, 20, 80], min_val=0.0, max_val=24.0,
                 initial=6.0, unitstyle=4)
    d.add_number_box("ceiling", "Ceiling", [40, 48, 50, 16], min_val=-24.0, max_val=0.0,
                     initial=-1.0, unitstyle=4)
    d.add_dial("mix", "Mix", [100, 48, 50, 70], min_val=0.0, max_val=100.0, initial=100.0,
               unitstyle=5, parameter_exponent=2.0)
    d.add_v8ui("meter", [180, 48, 120, 12], js_code=METER_JS)
    d.embed_gendsp("shaper", "out1 = tanh(in1 * in2);\nout2 = tanh(in3 * in2);", 3, 2,
                   [30, 100, 120, 22])
    d.add_gendsp("tone", "tone", "out1 = in1 * 0.5;\nout2 = in2 * 0.5;", 2, 2,
                 [30, 140, 120, 22])
    sub = Subpatcher("scaler")
    sub.add_newobj("in", "inlet", numinlets=0, numoutlets=1, outlettype=[""])
    sub.add_newobj("scale", "scale 0. 24. 1. 16.")
    sub.add_newobj("out", "outlet", numinlets=1, numoutlets=0)
    sub.add_line("in", 0, "scale", 0)
    sub.add_line("scale", 0, "out", 0)
    d.add_subpatcher(sub, "scaler", [200, 60, 80, 22], outlettype=[""])
    d.add_box(message("init", "loadbang", patching_rect=[300, 10, 60, 22]))
    d.add_newobj("smooth", "line~")
    for src, outlet, dst, inlet in [
        ("obj-plugin", 0, "shaper", 0), ("obj-plugin", 1, "shaper", 2),
        ("drive", 0, "scaler", 0), ("scaler", 0, "smooth", 0), ("smooth", 0, "shaper", 1),
        ("shaper", 0, "tone", 0), ("shaper", 1, "tone", 1),
        ("tone", 0, "obj-plugout", 0), ("tone", 1, "obj-plugout", 1), ("mix", 0, "meter", 0),
    ]:
        d.add_line(src, outlet, dst, inlet)
    d.latency = 64
    d.assign_parameter_bank("Drive", bank=0, position=0, bank_name="Main")
    d.assign_parameter_bank("Mix", bank=0, position=1)
    path = out_dir / "Kitchen Sink.amxd"
    d.build(str(path))
    return path


def _handmade(out_dir: Path) -> Path:
    """A device saved the way Max saves one (Max's own IDs and attribute sets),
    written by hand and packed with the raw container API."""
    patcher = json.loads((HANDMADE / "handmade_device.json").read_text(encoding="utf-8"))
    path = out_dir / "Hand Made.amxd"
    path.write_bytes(build_amxd(patcher, b"aaaa"))
    for name in HANDMADE_FILES:
        shutil.copy(HANDMADE / name, out_dir / name)
    return path


CASES = {
    "01_gain": (_example("01_gain_audio_effect.py"), "WARM"),
    "02_generative_midi": (_example("02_generative_midi.py"), "COOL"),
    "03_stereo_width": (_example("03_stereo_width.py"), "MIDNIGHT"),
    "04_midi_transformation": (_example("04_midi_transformation.py"), "MIDNIGHT"),
    "05_euclidean_midi": (_example("05_euclidean_midi.py"), "FOREST"),
    "06_simple_synth": (_example("06_simple_synth.py"), "SYNTHWAVE"),
    "kitchen_sink": (_kitchen_sink, "NEBULA"),
    "handmade": (_handmade, None),
}


def _ruff_clean(script: Path) -> None:
    if importlib.util.find_spec("ruff") is None:
        pytest.skip("ruff is not installed")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--config",
         str(ROOT / "pyproject.toml"), str(script)],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


# -- the round trip --------------------------------------------------------- #

@pytest.mark.parametrize("frozen", [False, True], ids=["sidecars", "frozen"])
@pytest.mark.parametrize("case", sorted(CASES))
def test_import_rebuilds_an_equivalent_device(tmp_path, capsys, case, frozen):
    make, theme = CASES[case]
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = make(source_dir)
    imported = source
    if frozen:
        imported = tmp_path / "frozen" / source.name
        imported.parent.mkdir()
        freeze_amxd_file(str(source), output_path=str(imported))

    script = tmp_path / "imported" / "build.py"
    assert main(["import", str(imported), "--out", str(script)]) == 0
    assert "rebuilds an identical device" in capsys.readouterr().out

    rebuilt_dir = tmp_path / "rebuilt"
    assert main(["build", str(script), "--out", f"{rebuilt_dir}/"]) == 0
    assert _device(rebuilt_dir / source.name) == _device(source)

    assert main(["lint", str(script)]) == 0
    _ruff_clean(script)

    result = import_amxd(imported)
    assert result.theme_name == theme
    if case != "handmade":
        assert result.raw_boxes == [], "a library-built device needs no raw boxes"


def test_handmade_device_keeps_only_what_has_no_library_call_raw(tmp_path):
    source = _handmade(tmp_path)
    result = import_amxd(source)
    kept_raw = sorted(entry.split(" (")[0] for entry in result.raw_boxes)
    # A plain Max comment and number box have no add_* helper, and the gen~ and
    # subpatcher patchers carry Max's own settings, so those four stay raw. The
    # controls, objects, message, jsui, js and external gen~ all become calls.
    assert kept_raw == ["drive_gain_label", "gen", "number", "smoothing"]
    assert "GEN_CODE = (" in result.script, "gen~ code should stay readable"

    script = tmp_path / "out" / "build.py"
    result.write(script)
    ids = {entry["box"]["id"] for entry in rebuild_from_script(script).boxes}
    assert not [box_id for box_id in ids if re.fullmatch(r"obj-\d+", box_id)]
    assert {"drive", "shape", "grit", "dbtoa", "msg_drive", "pulse_view",
            "obj-plugin", "obj-plugout"} <= ids


def test_check_import_names_the_box_an_edited_script_no_longer_rebuilds(tmp_path):
    source = _example("01_gain_audio_effect.py")(tmp_path)
    script = tmp_path / "gain" / "build.py"
    import_amxd(source).write(script)
    assert check_import(read_device(source), script) == []

    edited = script.read_text().replace("max_val=6.0", "max_val=12.0")
    assert edited != script.read_text()
    script.write_text(edited)
    diffs = check_import(read_device(source), script)
    assert any("live.dial" in diff and "Gain" in diff for diff in diffs), diffs


def test_import_refuses_to_overwrite_without_force(tmp_path, capsys):
    source = _handmade(tmp_path)
    out = tmp_path / "imported"
    assert main(["import", str(source), "--out", str(out)]) == 0
    (out / "helper.js").write_text("// edited\n")

    assert main(["import", str(source), "--out", str(out)]) == 1
    assert "already exists" in capsys.readouterr().err
    assert (out / "helper.js").read_text() == "// edited\n"

    assert main(["import", str(source), "--out", str(out), "--force"]) == 0
    assert (out / "helper.js").read_bytes() == (HANDMADE / "helper.js").read_bytes()


# -- devices as Max saves them, and hostile inputs --------------------------- #

def _max_device(tmp_path: Path, name: str, boxes: list, lines: list = (), **patcher) -> Path:
    """Pack a Max-style patcher (boxes/lines as bare dicts) into an .amxd."""
    body = {"openrect": [0.0, 0.0, 0.0, 169.0], "devicewidth": 0.0,
            "boxes": [{"box": box} for box in boxes],
            "lines": [{"patchline": {"source": [s, so], "destination": [d, di]}}
                      for s, so, d, di in lines],
            "dependency_cache": [], **patcher}
    path = tmp_path / f"{name}.amxd"
    path.write_bytes(build_amxd({"patcher": body}, b"mmmm"))
    return path


def _obj(box_id, text, rect, ins=1, outs=1):
    return {"id": box_id, "maxclass": "newobj", "numinlets": ins, "numoutlets": outs,
            "outlettype": [""] * outs, "patching_rect": rect, "text": text}


def test_max_defaults_auto_width_and_empty_push_bank_import_cleanly(tmp_path, capsys):
    """Max saves devicewidth 0 (Live sizes the device) and an all-empty bank 0."""
    sub_patcher = {"fileversion": 1, "rect": [0, 0, 300, 200], "boxes": [], "lines": []}
    source = _max_device(tmp_path, "Defaults", [
        {"id": "obj-1", "maxclass": "live.comment", "numinlets": 1, "numoutlets": 0,
         "patching_rect": [10, 10, 80, 20], "presentation": 1,
         "presentation_rect": [200.0, 20.0, 80.0, 20.0], "text": "Hello"},
        {**_obj("obj-2", "p ", [10, 60, 40, 22], ins=0, outs=0), "patcher": sub_patcher},
    ], parameters={"parameterbanks": {"0": {"index": 0, "name": "",
                                            "parameters": ["-"] * 8}}})
    script = tmp_path / "out" / "build.py"
    assert main(["import", str(source), "--out", str(script)]) == 0
    assert "rebuilds an identical device" in capsys.readouterr().out
    assert rebuild_from_script(script).width == 280  # the content's right edge


def test_check_catches_swapped_wiring_between_identical_boxes(tmp_path):
    rect = [10, 100, 40, 22]
    source = _max_device(tmp_path, "Swap", [
        _obj("x", "+ 1", [10, 10, 40, 22]), _obj("y", "+ 2", [60, 10, 40, 22]),
        _obj("a", "* 2", rect, ins=2), _obj("b", "* 2", rect, ins=2),
        _obj("left", "t l", [10, 200, 40, 22]), _obj("right", "t r", [60, 200, 40, 22]),
    ], [("x", 0, "a", 0), ("y", 0, "b", 0), ("a", 0, "left", 0), ("b", 0, "right", 0)])
    script = tmp_path / "out" / "build.py"
    import_amxd(source).write(script)
    assert check_import(read_device(source), script) == []

    text = script.read_text()
    swapped = (text.replace('add_line("x", 0, "a", 0)', "SWAP")
               .replace('add_line("y", 0, "b", 0)', 'add_line("y", 0, "a", 0)')
               .replace("SWAP", 'add_line("x", 0, "b", 0)'))
    assert swapped != text
    script.write_text(swapped)
    assert check_import(read_device(source), script)


def test_frozen_files_the_dependency_list_omits_are_carried(tmp_path):
    from m4l_builder.freeze import assemble_frozen_amxd

    plain = _max_device(tmp_path, "Plain", [_obj("obj-1", "t b", [10, 10, 40, 22])])
    patcher_json = plain.read_bytes()[32:]  # JSON after the 32-byte header
    knob = bytes(range(256))  # binary, not in dependency_cache
    frozen = tmp_path / "frozen" / "Plain.amxd"
    frozen.parent.mkdir()
    frozen.write_bytes(assemble_frozen_amxd(b"mmmm", "Plain.amxd", patcher_json,
                                            [("knob.png", knob)]))
    result = import_amxd(frozen)
    assert result.files["knob.png"] == knob
    script = tmp_path / "out" / "build.py"
    result.write(script)
    assert check_import(result.source, script) == []
    assert rebuild_from_script(script).asset("knob.png").content == knob


def test_dependency_names_pointing_outside_the_device_folder_are_never_read(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("do not copy")
    folder = tmp_path / "device"
    folder.mkdir()
    source = _max_device(folder, "Nosy", [_obj("obj-1", "t b", [10, 10, 40, 22])],
                         dependency_cache=[{"name": "../secret.txt", "type": "TEXT"},
                                           {"name": str(secret), "type": "TEXT"}])
    result = import_amxd(source)
    assert sorted(result.source.unsafe) == sorted(["../secret.txt", str(secret)])
    assert b"do not copy" not in b"".join(result.source.assets.values())
    assert result.files == {}
    written = result.write(tmp_path / "out" / "build.py")
    assert written == [tmp_path / "out" / "build.py"]


@pytest.mark.skipif(sys.platform == "win32", reason="backslash is not a filename character")
def test_device_names_with_quotes_and_backslashes_give_a_runnable_script(tmp_path):
    source = _max_device(tmp_path, 'Say """hi""" \\Unit', [_obj("obj-1", "t b", [10, 10, 40, 22])])
    script = tmp_path / "out" / "build.py"
    result = import_amxd(source)
    result.write(script)
    assert check_import(result.source, script) == []
    assert rebuild_from_script(script).name == 'Say """hi""" \\Unit'
