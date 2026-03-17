"""Smoke tests for writing representative .amxd artifacts."""

import json
import struct

import pytest

from m4l_builder import AudioEffect, Instrument, MidiEffect


def _parse_amxd(path):
    with open(path, "rb") as f:
        data = f.read()
    header = {
        "magic": data[:4],
        "version": struct.unpack_from("<I", data, 4)[0],
        "type_code": data[8:12],
        "meta_tag": data[12:16],
        "ptch_tag": data[24:28],
        "json_len": struct.unpack_from("<I", data, 28)[0],
    }
    json_bytes = data[32:]
    json_str = json_bytes.rstrip(b"\x00").rstrip(b"\n").decode("utf-8")
    return header, json.loads(json_str)


def _get_box_texts(patcher):
    return {box["box"].get("text", "") for box in patcher["patcher"]["boxes"]}


def _build_audio_effect(path):
    device = AudioEffect("Smoke FX", width=180, height=120)
    device.add_panel("bg", [0, 0, 180, 120], bgcolor=[0.12, 0.12, 0.12, 1.0])
    device.add_dial(
        "gain",
        "Gain",
        [10, 10, 50, 90],
        min_val=-24.0,
        max_val=6.0,
        initial=0.0,
        unitstyle=4,
    )
    device.add_newobj(
        "sel_l",
        "selector~ 2 1",
        numinlets=3,
        numoutlets=1,
        outlettype=["signal"],
    )
    device.add_newobj(
        "sel_r",
        "selector~ 2 1",
        numinlets=3,
        numoutlets=1,
        outlettype=["signal"],
    )
    device.add_line("obj-plugin", 0, "sel_l", 1)
    device.add_line("obj-plugin", 0, "sel_l", 2)
    device.add_line("obj-plugin", 1, "sel_r", 1)
    device.add_line("obj-plugin", 1, "sel_r", 2)
    device.add_line("sel_l", 0, "obj-plugout", 0)
    device.add_line("sel_r", 0, "obj-plugout", 1)
    return device.build(str(path))


def _build_instrument(path):
    device = Instrument("Smoke Synth", width=200, height=120)
    device.add_panel("bg", [0, 0, 200, 120], bgcolor=[0.12, 0.12, 0.12, 1.0])
    device.add_dial(
        "level",
        "Level",
        [10, 10, 50, 90],
        min_val=0.0,
        max_val=100.0,
        initial=50.0,
        unitstyle=5,
    )
    device.add_newobj("osc", "cycle~ 220", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("amp", "*~ 0.1", numinlets=2, numoutlets=1, outlettype=["signal"])
    device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0)
    device.add_line("osc", 0, "amp", 0)
    device.add_line("amp", 0, "plugout", 0)
    device.add_line("amp", 0, "plugout", 1)
    return device.build(str(path))


def _build_midi_effect(path):
    device = MidiEffect("Smoke MIDI", width=180, height=100)
    device.add_panel("bg", [0, 0, 180, 100], bgcolor=[0.12, 0.12, 0.12, 1.0])
    device.add_toggle("enable", "Enable", [10, 10, 60, 20])
    device.add_newobj("notein", "notein", numinlets=0, numoutlets=3, outlettype=["int", "int", "int"])
    device.add_newobj("noteout", "noteout", numinlets=3, numoutlets=0)
    device.add_line("notein", 0, "noteout", 0)
    device.add_line("notein", 1, "noteout", 1)
    device.add_line("notein", 2, "noteout", 2)
    return device.build(str(path))


BUILDERS = [
    ("audio_effect", b"aaaa", _build_audio_effect),
    ("instrument", b"iiii", _build_instrument),
    ("midi_effect", b"mmmm", _build_midi_effect),
]


@pytest.mark.parametrize("name,type_code,builder", BUILDERS)
def test_smoke_builds_write_valid_amxd(tmp_path, name, type_code, builder):
    output = tmp_path / f"{name}.amxd"

    written = builder(output)

    assert written > 0
    assert output.exists()

    header, patcher = _parse_amxd(output)
    assert header["magic"] == b"ampf"
    assert header["version"] == 4
    assert header["type_code"] == type_code
    assert header["meta_tag"] == b"meta"
    assert header["ptch_tag"] == b"ptch"
    assert "patcher" in patcher
    assert patcher["patcher"]["boxes"]
    assert isinstance(patcher["patcher"]["lines"], list)

    assert any(
        box["box"].get("presentation") == 1
        for box in patcher["patcher"]["boxes"]
    )


@pytest.mark.parametrize("name,_,builder", BUILDERS)
def test_smoke_build_patchlines_reference_existing_boxes(tmp_path, name, _, builder):
    output = tmp_path / f"{name}.amxd"
    builder(output)

    _, patcher = _parse_amxd(output)
    box_ids = {box["box"]["id"] for box in patcher["patcher"]["boxes"]}
    for line in patcher["patcher"]["lines"]:
        src_id = line["patchline"]["source"][0]
        dst_id = line["patchline"]["destination"][0]
        assert src_id in box_ids
        assert dst_id in box_ids


def test_audio_effect_smoke_build_has_expected_io_and_safe_objects(tmp_path):
    output = tmp_path / "audio_effect.amxd"
    _build_audio_effect(output)

    _, patcher = _parse_amxd(output)
    texts = _get_box_texts(patcher)

    assert "plugin~" in texts
    assert "plugout~" in texts
    assert "sig~" not in texts
    assert "dcblock~" not in texts
    assert "selector~ 2 1" in texts

    for box in patcher["patcher"]["boxes"]:
        payload = box["box"]
        if payload.get("maxclass") == "panel":
            assert payload.get("background") == 1
