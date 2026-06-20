"""Tests for the shared gen~ patcher (.gendsp) codegen (m4l_builder.gen_patcher).

This is the single canonical build_gendsp the DSP flagships (pressure, ceiling,
heat, echotide, spectrum_analyzer) used to copy-paste; these lock its contract so
the shared version cannot silently drift.
"""
import json

from m4l_builder.gen_patcher import build_gendsp


def test_build_gendsp_is_valid_dsp_gen_patcher():
    p = json.loads(build_gendsp("out1 = in1;", 1, 1))["patcher"]
    assert p["classnamespace"] == "dsp.gen"
    ids = [b["box"]["id"] for b in p["boxes"]]
    assert "codebox" in ids and "in_1" in ids and "out_1" in ids
    cb = next(b["box"] for b in p["boxes"] if b["box"]["id"] == "codebox")
    assert cb["maxclass"] == "codebox"
    assert cb["code"] == "out1 = in1;"


def test_build_gendsp_in_out_counts_and_wiring():
    p = json.loads(build_gendsp("out1 = in1 + in2;", 2, 3))["patcher"]
    ins = [b for b in p["boxes"] if b["box"]["id"].startswith("in_")]
    outs = [b for b in p["boxes"] if b["box"]["id"].startswith("out_")]
    assert len(ins) == 2 and len(outs) == 3
    # every input is wired into the codebox; every codebox out feeds an out N
    in_dests = {(l["patchline"]["destination"][0]) for l in p["lines"]
                if l["patchline"]["source"][0].startswith("in_")}
    assert in_dests == {"codebox"}
    out_srcs = {(l["patchline"]["source"][0]) for l in p["lines"]
                if l["patchline"]["destination"][0].startswith("out_")}
    assert out_srcs == {"codebox"}


def test_window_size_params_are_cosmetic_only():
    default = json.loads(build_gendsp("out1 = in1;", 1, 1))["patcher"]
    assert default["rect"][3] == 660.0
    cb = next(b["box"] for b in default["boxes"] if b["box"]["id"] == "codebox")
    assert cb["patching_rect"][3] == 560.0
    custom = json.loads(build_gendsp("out1 = in1;", 1, 1, codebox_h=540.0, patcher_h=640.0))["patcher"]
    assert custom["rect"][3] == 640.0
    # the window sizes are the ONLY difference; zero them and the docs are equal,
    # proving the override (used by pressure to keep byte-parity) is non-DSP.
    a = json.loads(build_gendsp("out1 = in1;", 1, 1))
    b = json.loads(build_gendsp("out1 = in1;", 1, 1, codebox_h=540.0, patcher_h=640.0))
    for doc in (a, b):
        doc["patcher"]["rect"][3] = 0
        for box in doc["patcher"]["boxes"]:
            if box["box"]["id"] == "codebox":
                box["box"]["patching_rect"][3] = 0
    assert a == b
