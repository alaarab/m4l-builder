"""SVG previews of a device's presentation view (``m4l_builder.preview``)."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from m4l_builder import WARM, AudioEffect, ParameterSpec
from m4l_builder.cli import main, run_build_script, slugify
from m4l_builder.engines.filter_curve import filter_curve_js
from m4l_builder.preview import format_value, render_svg

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SCRIPTS = sorted((ROOT / "examples").glob("[0-9]*.py"))
PREVIEWS = ROOT / "docs" / "previews"
SVG = "{http://www.w3.org/2000/svg}"


def _example_device(script: Path):
    (record,) = run_build_script(script, lambda _d, _p: None, quiet=True)
    return record.device


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda p: p.stem)
def test_example_previews_match_the_committed_gallery(script):
    device = _example_device(script)
    golden = PREVIEWS / f"{slugify(device.name)}.svg"
    assert golden.is_file(), f"missing {golden.relative_to(ROOT)}: run `make previews`"
    assert render_svg(device, scale=2) == golden.read_text(encoding="utf-8"), (
        f"{golden.relative_to(ROOT)} is stale: run `make previews` and review the SVG diff"
    )


# -- what gets drawn ------------------------------------------------------- #

def _tour(**dial_kwargs):
    d = AudioEffect("Tour", 300, 160, theme=WARM)
    d.add_panel("bg", [0, 0, 300, 160])
    d.add_tab("mode", "Mode", [10, 10, 120, 18], options=["A", "B", "C"],
              parameter=ParameterSpec.enumerated("Mode", ["A", "B", "C"], initial=2))
    d.add_menu("shape", "Shape", [10, 34, 80, 18], options=["Sine", "Saw"],
               parameter=ParameterSpec.enumerated("Shape", ["Sine", "Saw"], initial=1))
    d.add_toggle("tg", "Tog", [100, 34, 18, 18],
                 parameter=ParameterSpec.enumerated("Tog", ["off", "on"], initial=1))
    d.add_jsui("viz", [140, 10, 100, 60], js_code=filter_curve_js())
    d.add_dial("cut", "Cutoff", [10, 60, 50, 80], min_val=20.0, max_val=20000.0,
               unitstyle=3, **dial_kwargs)
    d.add_slider("mix", "Mix", [250, 10, 30, 100], initial=0.25)
    d.add_live_text("byp", "Bypass", [140, 80, 50, 18], text_off="DRY")
    d.add_number_box("num", "Num", [200, 80, 40, 16], initial=64.0, unitstyle=0)
    d.add_comment("note", [140, 104, 80, 16], "Two\nlines", textjustification=1)
    d.add_meter("lvl", [285, 10, 10, 100])
    d.add_scope("sc", [200, 124, 60, 30])
    d.add_box({"box": {"id": "grid", "maxclass": "live.grid", "presentation": 1,
                       "presentation_rect": [70, 60, 60, 40], "numinlets": 1,
                       "numoutlets": 1}})
    d.add_box({"box": {"id": "gone", "maxclass": "live.dial", "presentation": 1,
                       "hidden": 1, "presentation_rect": [140, 80, 40, 40],
                       "numinlets": 1, "numoutlets": 2}})
    d.add_box({"box": {"id": "parked", "maxclass": "live.dial", "presentation": 1,
                       "presentation_rect": [900, 900, 40, 40],
                       "numinlets": 1, "numoutlets": 2}})
    return d


def _groups(svg: str) -> dict:
    root = ET.fromstring(svg)
    return {g.get("data-id"): g for g in root.iter(f"{SVG}g") if g.get("data-id")}


def _texts(group) -> list:
    return [t.text for t in group.iter(f"{SVG}text")]


def _fills(group) -> set:
    return {r.get("fill") for r in group.iter(f"{SVG}rect")}


def test_draws_visible_presentation_boxes_only_background_first():
    groups = _groups(render_svg(_tour(initial=1000.0)))
    # plugin~/plugout~ have no presentation rect; hidden and off-canvas boxes are skipped.
    assert list(groups) == ["bg", "mode", "shape", "tg", "viz", "cut", "mix", "byp",
                            "num", "note", "lvl", "sc", "grid"]


def test_controls_show_their_initial_state():
    groups = _groups(render_svg(_tour(initial=1000.0)))
    accent = "#d98c40"  # WARM accent [0.85, 0.55, 0.25]

    assert _texts(groups["mode"]) == ["A", "B", "C"]
    tab_cells = [r.get("fill") for r in groups["mode"].iter(f"{SVG}rect")]
    assert tab_cells[2] == accent and accent not in tab_cells[:2]

    assert _texts(groups["shape"]) == ["Saw"]
    assert accent in _fills(groups["tg"])
    assert _texts(groups["cut"]) == ["Cutoff", "1.00 kHz"]
    assert _texts(groups["mix"]) == ["Mix", "0.25"]
    assert _texts(groups["byp"]) == ["DRY"]
    assert _texts(groups["num"]) == ["64"]
    assert _texts(groups["note"]) == ["Two", "lines"]


def test_engines_and_unknown_objects_are_labelled_placeholders():
    groups = _groups(render_svg(_tour(initial=1000.0)))
    assert _texts(groups["viz"]) == ["jsui", "viz.js"]
    assert _texts(groups["grid"]) == ["live.grid"]


def _arcs(svg: str) -> list:
    dial = _groups(svg)["cut"]
    return [p.get("d") for p in dial.iter(f"{SVG}path")]


def test_dial_value_arc_spans_the_track_at_max_and_is_absent_at_min():
    track, value = _arcs(render_svg(_tour(initial=20000.0)))
    assert value == track  # full sweep: same start, same end point
    assert len(_arcs(render_svg(_tour(initial=20.0)))) == 1  # only the track


@pytest.mark.parametrize("value, unitstyle, units, expected", [
    (3.6, 0, None, "4"),
    (0.5, 1, None, "0.50"),
    (250.0, 2, None, "250 ms"),
    (1500.0, 2, None, "1.50 s"),
    (440.0, 3, None, "440 Hz"),
    (2500.0, 3, None, "2.50 kHz"),
    (-6.0, 4, None, "-6.0 dB"),
    (-70.0, 4, None, "-inf dB"),
    (42.0, 5, None, "42 %"),
    (0.0, 6, None, "C"),
    (-25.0, 6, None, "25L"),
    (7.0, 7, None, "+7 st"),
    (60.0, 8, None, "C3"),
    (3.0, 9, "%.1f x", "3.0 x"),
])
def test_format_value_follows_live_unit_styles(value, unitstyle, units, expected):
    assert format_value(value, unitstyle, units) == expected


# -- inputs and the command line ------------------------------------------- #

def test_amxd_and_patcher_inputs_render_like_the_device(tmp_path):
    device = _example_device(ROOT / "examples" / "02_generative_midi.py")
    path = tmp_path / f"{device.name}.amxd"
    device.build(str(path))
    expected = render_svg(device)
    assert render_svg(path) == expected
    assert render_svg(device.to_patcher(), title=device.name) == expected


def test_cli_preview_writes_svg_files(tmp_path, capsys):
    script = ROOT / "examples" / "01_gain_audio_effect.py"
    assert main(["preview", str(script), "--out", str(tmp_path)]) == 0
    framed = ET.parse(tmp_path / "my_gain.svg").getroot()
    assert (framed.get("width"), framed.get("height")) == ("150", "128")

    single = tmp_path / "bare.svg"
    assert main(["preview", str(script), "--out", str(single), "--no-frame",
                 "--scale", "2"]) == 0
    bare = ET.parse(single).getroot()
    assert (bare.get("width"), bare.get("height"), bare.get("viewBox")) == (
        "300", "220", "0 0 150 110")
    assert "preview My Gain ->" in capsys.readouterr().out
