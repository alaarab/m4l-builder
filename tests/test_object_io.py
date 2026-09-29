"""Inlet/outlet inference for newobj boxes (m4l_builder.object_io)."""

import ast
from pathlib import Path

import pytest

from m4l_builder import AudioEffect
from m4l_builder.box_lint import lint_box
from m4l_builder.object_io import UnknownObjectIO, infer_object_io, resolve_newobj_io
from m4l_builder.objects import newobj
from m4l_builder.subpatcher import Subpatcher

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("text, expected", [
    ("pack 0 0 0", (3, 1, [""])),
    ("pack", (2, 1, [""])),
    ("pak 0. 1.", (2, 1, [""])),
    ("unpack", (1, 2, ["int", "int"])),
    ("unpack f i 0. s", (1, 4, ["float", "int", "float", ""])),
    ("t b i f l", (1, 4, ["bang", "int", "float", ""])),
    ("trigger 0 1.", (1, 2, ["int", "float"])),
    ("route a b c", (4, 4, ["", "", "", ""])),
    ("route", (2, 2, ["", ""])),
    ("sel 1", (2, 2, ["bang", ""])),
    ("select 0 1 2", (4, 4, ["bang", "bang", "bang", ""])),
    ("gate", (2, 1, [""])),
    ("gate 4 1", (2, 4, ["", "", "", ""])),
    ("gate~ 3", (2, 3, ["signal"] * 3)),
    ("switch 3", (4, 1, [""])),
    ("selector~ 3 1", (4, 1, ["signal"])),
    ("join 3 @triggers 1", (3, 1, [""])),
    ("unjoin 4", (1, 5, [""] * 5)),
    ("spray 3", (1, 3, ["", "", ""])),
    ("funnel 4", (4, 1, ["list"])),
    ("+ 1", (2, 1, ["int"])),
    ("* 0.5", (2, 1, ["float"])),
    ("== 0.", (2, 1, ["int"])),
    ("*~ 0.5", (2, 1, ["signal"])),
    ("s foo", (1, 0, [])),
    ("r foo", (0, 1, [""])),
    ("expr $f1 * $i3", (3, 1, [""])),
    ("sprintf %s-%i", (2, 1, [""])),
    ("mc.pack~ 4", (4, 1, ["multichannelsignal"])),
    ("tapout~ 0 0", (2, 2, ["signal", "signal"])),
    # dataset, bare
    ("live.thisdevice", (1, 3, ["bang", "int", "int"])),
    ("dcblock~", None),
    # dataset, arguments that don't change the shape
    ("metro 100", (2, 1, ["bang"])),
    ("prepend set", (1, 1, [""])),
    ("line~ 0.", (2, 2, ["signal", "bang"])),
])
def test_infer(text, expected):
    if expected is None:
        with pytest.raises(UnknownObjectIO):
            infer_object_io(text)
    else:
        assert tuple(infer_object_io(text)) == expected


@pytest.mark.parametrize("text, reason", [
    ("gen~", "gen patcher"),
    ("p sub", "embedded patcher"),
    ("poly~ voice 4", "voice patcher"),
    ("js ui.js", "script"),
    ("in 1", "poly~"),
    ("live.dial", "UI object"),
    ("mc.cycle~", "multichannel"),
    ("noteout 2", "arguments"),
    ("cycle~ 440 @phase 0.5", "attributes"),
    ("prepend 0", "arguments"),
    ("scale minor", "arguments"),
    ("gate $1", "literal positive integer"),
    ("t b set", "constant-symbol"),
    ("+ $1", "non-literal"),
    ('route "a b"', "quoted"),
    ("s", "name argument"),
    ("notanobject~", "no inlet/outlet data"),
])
def test_unknown_raises_with_reason(text, reason):
    with pytest.raises(UnknownObjectIO, match="pass numinlets/numoutlets") as err:
        infer_object_io(text)
    assert reason in str(err.value)


def test_explicit_counts_are_untouched():
    assert resolve_newobj_io("gate 4", 9, 9, None) == (9, 9, None)
    assert resolve_newobj_io("gen~", 3, 2, ["signal"]) == (3, 2, ["signal"])
    assert newobj("x", "cycle~ 440", numinlets=2, numoutlets=1) == {"box": {
        "id": "x", "maxclass": "newobj", "fontname": "Arial Bold",
        "fontsize": 10.0, "numinlets": 2, "numoutlets": 1,
        "patching_rect": [0, 0, 60, 20], "text": "cycle~ 440"}}


def test_partial_override():
    assert resolve_newobj_io("gate 4", 3, None, None) == (3, 4, ["", "", "", ""])
    # an overridden outlet count drops the inferred outlettype
    assert resolve_newobj_io("gate 4", None, 2, None) == (2, 2, None)
    assert resolve_newobj_io("gate 4", None, None, ["bang"] * 4) == (2, 4, ["bang"] * 4)


def test_add_newobj_infers_and_lints_clean():
    device = AudioEffect("io", width=100, height=100)
    ref = device.add_newobj("sel", "sel 0 1")
    box = device.boxes[-1]["box"]
    assert (ref, box["numinlets"], box["numoutlets"], box["outlettype"]) == (
        "sel", 3, 3, ["bang", "bang", ""])
    device.add_newobj("snap", "snapshot~")
    assert lint_box(device.boxes[-1]["box"]) == []
    device.add_newobj("snd", "s foo")
    assert "outlettype" not in device.boxes[-1]["box"]
    with pytest.raises(UnknownObjectIO):
        device.add_newobj("g", "gen~")

    sub = Subpatcher("inner")
    sub.add_newobj("m", "metro 10")
    assert sub.boxes[-1]["box"]["outlettype"] == ["bang"]


# --- agreement with every explicit declaration in the repo -------------------
#
# Each literal ``newobj(...)`` / ``add_newobj(...)`` call in src/, examples/ and
# tests/ that declares its counts is checked against inference. The entries
# below are the existing declarations that disagree; they are left as is
# (explicit values win, and changing them would change built devices). A new
# disagreement, or an entry that no longer occurs, fails the test.

MAX9 = "Max 9 saves this shape; the vendored Max 8.6 dataset differs"
FIXTURE = "synthetic test fixture, not a Max shape"

KNOWN_COUNT_DISAGREEMENTS = {
    ("cycle~", 2, 2): MAX9,
    ("noise~", 0, 1): MAX9,
    ("midiparse", 1, 7): MAX9,
    ("buffer~ b_smp", 1, 1): FIXTURE,
    ("buffer~ mybuf_smp", 1, 1): FIXTURE,
    ("live.thisdevice", 1, 2): FIXTURE,
    ("plugin~", 1, 2): FIXTURE,
    ("plugin~", 1, 4): FIXTURE,
    ("plugin~", 3, 1): FIXTURE,
    ("transport", 1, 7): "deliberately wrong: box_lint must reject it",
}

GENERIC = "declared a generic '' outlet where Max types it"
TYPED = "declared a typed outlet where Max saves ''"
KNOWN_TYPE_DISAGREEMENTS = {
    ("* 60.", ("",)): GENERIC,
    ("+ 1", ("",)): GENERIC,
    ("/ 1000.", ("",)): GENERIC,
    ("/ 2.5", ("",)): GENERIC,
    ("i", ("",)): GENERIC,
    ("i 248", ("",)): GENERIC,
    ("t 0", ("",)): GENERIC,
    ("t 1", ("",)): GENERIC,
    ("t 60", ("",)): GENERIC,
    ("t f f", ("", "")): GENERIC,
    ("t f f f", ("", "", "")): GENERIC,
    ("bendin", ("", "")): GENERIC,
    ("ctlin", ("", "", "")): GENERIC,
    ("midiin", ("",)): GENERIC,
    ("notein", ("", "", "")): GENERIC,
    ("touchin", ("", "")): GENERIC,
    ("dbtoa", ("float",)): TYPED,
    ("if $i1 == -1 then 0 else $i1", ("int",)): TYPED,
    ("random 1000", ("int",)): MAX9,
    ("random 10001", ("int",)): MAX9,
    ("plugin~", ("signal",)): FIXTURE,
}


def _literal(node):
    try:
        return ast.literal_eval(node)
    except ValueError:
        return None


def _declared_newobjs():
    """``(where, text, numinlets, numoutlets, outlettype|None)`` for literal calls."""
    this_file = Path(__file__).resolve()
    for root in ("src/m4l_builder", "examples", "tests"):
        for path in sorted((ROOT / root).rglob("*.py")):
            if path.resolve() == this_file:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                if name not in ("newobj", "add_newobj"):
                    continue
                kw = {k.arg: k.value for k in node.keywords if k.arg}
                text = node.args[1] if len(node.args) > 1 else kw.get("text")
                if text is None or "numinlets" not in kw or "numoutlets" not in kw:
                    continue
                text, ni, no = _literal(text), _literal(kw["numinlets"]), _literal(kw["numoutlets"])
                ot = _literal(kw["outlettype"]) if "outlettype" in kw else None
                if isinstance(text, str) and isinstance(ni, int) and isinstance(no, int):
                    yield f"{path.relative_to(ROOT)}:{node.lineno}", text, ni, no, ot


def test_inference_agrees_with_existing_declarations():
    checked = 0
    count_diffs: dict = {}
    type_diffs: dict = {}
    for where, text, ni, no, ot in _declared_newobjs():
        try:
            io = infer_object_io(text)
        except UnknownObjectIO:
            continue
        checked += 1
        if (io.numinlets, io.numoutlets) != (ni, no):
            count_diffs.setdefault((text, ni, no), where)
        elif ot and list(ot) != io.outlettype:
            type_diffs.setdefault((text, tuple(ot)), where)

    assert checked >= 450, f"only {checked} declarations checked; did the scan break?"
    new = {k: v for k, v in count_diffs.items() if k not in KNOWN_COUNT_DISAGREEMENTS}
    gone = set(KNOWN_COUNT_DISAGREEMENTS) - set(count_diffs)
    assert not new, f"declared counts disagree with inference: {new}"
    assert not gone, f"no longer occur, remove from KNOWN_COUNT_DISAGREEMENTS: {gone}"
    new = {k: v for k, v in type_diffs.items() if k not in KNOWN_TYPE_DISAGREEMENTS}
    gone = set(KNOWN_TYPE_DISAGREEMENTS) - set(type_diffs)
    assert not new, f"declared outlettype disagrees with inference: {new}"
    assert not gone, f"no longer occur, remove from KNOWN_TYPE_DISAGREEMENTS: {gone}"
