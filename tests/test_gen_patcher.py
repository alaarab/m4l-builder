"""Tests for the shared gen~ patcher (.gendsp) codegen (m4l_builder.gen_patcher).

This is the single canonical build_gendsp the DSP flagships (pressure, ceiling,
heat, echotide, spectrum_analyzer) used to copy-paste; these lock its contract so
the shared version cannot silently drift.
"""
import json

import pytest

from m4l_builder.gen_patcher import build_gendsp, embed_gendsp, gendsp_support_name


def test_build_gendsp_is_valid_dsp_gen_patcher():
    p = json.loads(build_gendsp("out1 = in1;", 1, 1))["patcher"]
    assert p["classnamespace"] == "dsp.gen"
    ids = [b["box"]["id"] for b in p["boxes"]]
    assert "codebox" in ids and "in_1" in ids and "out_1" in ids
    cb = next(b["box"] for b in p["boxes"] if b["box"]["id"] == "codebox")
    assert cb["maxclass"] == "codebox"
    assert cb["code"] == "out1 = in1;"


def test_build_gendsp_in_out_counts_and_wiring():
    # all 3 outs assigned so the default lint passes; this test is about wiring
    p = json.loads(build_gendsp("out1 = in1; out2 = in2; out3 = in1 + in2;", 2, 3))["patcher"]
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


def test_build_gendsp_lints_by_default_and_raises_on_dead_output():
    # out2/out3 are declared (numouts=3) but never assigned -> lint should fail
    with pytest.raises(ValueError, match="lint failed"):
        build_gendsp("out1 = in1;", 2, 3)


def test_build_gendsp_lint_false_bypasses():
    # explicit opt-out still serializes the (malformed) patcher
    out = build_gendsp("out1 = in1;", 2, 3, lint=False)
    assert json.loads(out)["patcher"]["classnamespace"] == "dsp.gen"


def test_build_gendsp_clean_code_passes_lint():
    out = build_gendsp("out1 = in1; out2 = in2;", 2, 2)
    assert json.loads(out)["patcher"]["classnamespace"] == "dsp.gen"


def test_embed_gendsp_returns_gen_box_with_inline_patcher():
    # LIVE-VERIFIED that an EMBEDDED gen~ may define functions and still pass audio
    # (the external .gendsp path silences functions). embed_gendsp inlines the patcher.
    code = "osc(f){\n\treturn cycle(f);\n}\nout1 = osc(220) * 0.2;\nout2 = out1;"
    box = embed_gendsp(code, 2, 2, box_id="rev")["box"]
    assert box["maxclass"] == "newobj" and box["text"] == "gen~"
    assert box["id"] == "rev"
    assert box["numinlets"] == 2 and box["numoutlets"] == 2
    assert box["outlettype"] == ["signal", "signal"]
    # the gen patcher is EMBEDDED (no external .gendsp file reference)
    patcher = box["patcher"]
    assert patcher["classnamespace"] == "dsp.gen"
    cbs = [b["box"] for b in patcher["boxes"] if b["box"].get("maxclass") == "codebox"]
    assert len(cbs) == 1
    assert "osc(f)" in cbs[0]["code"]            # the USER FUNCTION rides inline


def test_embed_gendsp_generator_zero_ins_keeps_one_inlet():
    box = embed_gendsp("out1 = cycle(220);", 0, 1)["box"]
    assert box["numinlets"] == 1               # gen~ always has >=1 inlet
    assert box["numoutlets"] == 1


# --- content-addressed support filename (stale-gen-cache fix) ----------------


def test_gendsp_support_name_is_stem_prefixed_and_gendsp_suffixed():
    name = gendsp_support_name("heat_core", "out1 = in1;")
    assert name.startswith("heat_core_")          # stable, human-readable stem prefix
    assert name.endswith(".gendsp")
    # underscore-joined hash suffix (the proven <stem>_<suffix>.gendsp convention)
    suffix = name[len("heat_core_"):-len(".gendsp")]
    assert len(suffix) == 8 and all(c in "0123456789abcdef" for c in suffix)


def test_gendsp_support_name_is_deterministic():
    # same source -> byte-identical name -> Max reuses the cached compile
    assert gendsp_support_name("k", "out1 = in1;") == gendsp_support_name("k", "out1 = in1;")


def test_gendsp_support_name_changes_with_code():
    # any DSP edit -> new filename -> guaranteed fresh compile (no manual _vNN bump)
    a = gendsp_support_name("k", "out1 = in1 * 0.5;")
    b = gendsp_support_name("k", "out1 = in1 * 0.6;")
    assert a != b


def test_gendsp_support_name_hashes_code_not_window_size():
    # cosmetic codebox_h/patcher_h differ but the CODE is identical -> same name,
    # so an editor-window tweak does NOT churn the filename (only real DSP edits do)
    code = "out1 = in1; out2 = in2;"
    assert gendsp_support_name("k", code) == gendsp_support_name("k", code)
    # and the name is independent of the full serialized patcher bytes
    big = build_gendsp(code, 2, 2, codebox_h=900.0, patcher_h=1000.0)
    small = build_gendsp(code, 2, 2, codebox_h=300.0, patcher_h=400.0)
    assert big != small                                       # serialized bytes differ
    assert gendsp_support_name("k", code) == gendsp_support_name("k", code)  # name stable


def test_gendsp_support_name_hash_len_override():
    assert len(gendsp_support_name("k", "out1=in1;", hash_len=12)[len("k_"):-len(".gendsp")]) == 12


# --- History auto-hoist (multi-kernel silencing fix) -------------------------

def _codebox_code(gendsp_json):
    p = json.loads(gendsp_json)["patcher"]
    for b in p["boxes"]:
        if b["box"].get("maxclass") == "codebox":
            return b["box"]["code"]
    raise AssertionError("no codebox in gendsp")


def _state_all_before_first_stmt(code):
    """True iff no depth-0 History/Delay/Data decl appears after the first statement."""
    from m4l_builder.gen_patcher import _STATE_DECL, _is_stmt
    seen_stmt = False
    depth = 0
    for ln in code.split("\n"):
        s = ln.strip()
        if depth == 0:
            if s.startswith(_STATE_DECL) and seen_stmt:
                return False
            if _is_stmt(s):
                seen_stmt = True
        depth += ln.count("{") - ln.count("}")
    return True


def test_build_gendsp_hoists_interleaved_history():
    # two stateful kernels: the 2nd kernel's History lands AFTER the 1st's body
    # (exactly the pattern that silenced Tilt/Aurora/MonoMaker/Snap in Live).
    code = (
        "Param a(0.);\n"
        "History k1(0.);\n"
        "x = in1 * a;\n"            # <- first statement
        "History k2(0.);\n"        # <- VIOLATION: state decl after a statement
        "out1 = x + k1 + k2;\n"
    )
    assert not _state_all_before_first_stmt(code)            # input is broken
    out = _codebox_code(build_gendsp(code, 1, 1, lint=False))
    assert _state_all_before_first_stmt(out)                 # build_gendsp fixed it
    assert "History k2(0.);" in out                          # decl preserved


def test_hoist_history_is_noop_when_correct():
    from m4l_builder.gen_patcher import hoist_declarations
    code = ("Param a(0.);\nHistory k1(0.);\nHistory k2(0.);\n"
            "x = in1 * a;\nout1 = x + k1 + k2;")
    assert hoist_declarations(code) == code                      # byte-identical no-op


def test_hoist_history_keeps_state_inside_functions():
    from m4l_builder.gen_patcher import hoist_declarations
    # History inside a gen function body (depth>0) must NOT be hoisted out, and the
    # function must stay above the hoisted top-level decl.
    code = ("osc(f){\n\tHistory h(0.);\n\treturn cycle(f) + h;\n}\n"
            "y = osc(220);\n"
            "History g(0.);\n"      # depth-0 violation -> hoist THIS one only
            "out1 = y + g;\n")
    out = hoist_declarations(code)
    assert out.split("\n")[0] == "osc(f){"                   # function still first
    assert "\tHistory h(0.);" in out                         # inner History untouched
    assert _state_all_before_first_stmt(out)                 # top-level decl hoisted
