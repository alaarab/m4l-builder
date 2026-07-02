"""E2/E3 LOM mapper kit: mapper js + retargetable sink + slot component."""

from m4l_builder import AudioEffect
from m4l_builder.dsp import live_modulate, live_remote, retargetable_param_sink
from m4l_builder.engines.lom_mapper import lom_mapper_js
from m4l_builder.recipes import modulator_slot_component


def test_lom_mapper_js_contract():
    js = lom_mapper_js()
    for handler in ("function map(", "function unmap(", "function setid(",
                    "function settarget(", "function announce(",
                    "function extunmap("):
        assert handler in js
    assert "outlets = 2" in js
    assert 'new RegExp("Map|Min|Max|Depth|Bipolar")' in js
    assert ".schedule(DEBOUNCE_MS)" in js and "DEBOUNCE_MS = 20" in js
    assert "selected_parameter" in js
    assert "canonical_parent" in js       # self-map guard reads the owner device
    assert 'outlet(0, "id", id)' in js    # sink bus speaks id lists only


def test_sinks_are_two_inlet_corpus_shapes():
    (rb,), _ = live_remote("t")
    assert rb["box"]["numinlets"] == 2
    assert rb["box"]["saved_object_attributes"]["_persistence"] == 1
    assert rb["box"]["saved_object_attributes"]["normalized"] == 0
    (mb,), _ = live_modulate("t")
    assert mb["box"]["numinlets"] == 2
    assert mb["box"]["text"] == "live.modulate~"


def test_retargetable_sink_wiring():
    boxes, lines = retargetable_param_sink("s")
    by_id = {b["box"]["id"]: b["box"] for b in boxes}
    assert by_id["s_remote"]["text"] == "live.remote~"
    assert by_id["s_gate"]["text"] == "gate 2 1"
    assert by_id["s_reg"]["text"] == "zl.reg id 0"
    conn = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0],
             ln["patchline"]["destination"][1]) for ln in lines}
    # the id reaches each sink's RIGHT inlet, always through deferlow
    assert ("s_defer_r", 0, "s_remote", 1) in conn
    assert ("s_defer_m", 0, "s_mod", 1) in conn
    # cross-detach: each path's bang fires `id 0` into the OTHER sink's deferlow
    assert ("s_tbl_r", 0, "s_id0_m", 0) in conn
    assert ("s_tbl_m", 0, "s_id0_r", 0) in conn
    assert ("s_id0_r", 0, "s_defer_r", 0) in conn
    assert ("s_id0_m", 0, "s_defer_m", 0) in conn
    # mode switch re-emits the stored id (t b i: int sets gate, bang re-fires reg)
    assert ("s_tbi", 1, "s_gate", 0) in conn
    assert ("s_tbi", 0, "s_reg", 0) in conn
    # forced-unmap detect: both sink outlets -> route mapped -> sel 0
    assert ("s_remote", 0, "s_route", 0) in conn
    assert ("s_mod", 0, "s_route", 0) in conn
    assert ("s_route", 0, "s_unmapped", 0) in conn


def test_modulator_slot_component():
    device = AudioEffect("Map Test", width=300, height=168)
    sub, ids = modulator_slot_component(device, accent=[1.0, 0.6, 0.2, 1.0])
    texts = [b["box"].get("text", "") for b in sub.boxes]
    assert any(t.startswith("v8 lom_mapper") and t.endswith("#1") for t in texts)
    # NOTHING crosses the embed boundary by --- name (Live-proven failure):
    # signal enters by bpatcher INLET, ctl uplink leaves by OUTLET
    assert not any("---" in t for t in texts)
    inlets = sorted((b["box"]["patching_rect"][0], b["box"]["id"])
                    for b in sub.boxes if b["box"].get("maxclass") == "inlet")
    assert [i[1] for i in inlets] == ["slot_in", "slot_rsig_r", "slot_rsig_m"]
    assert any(b["box"].get("maxclass") == "outlet" for b in sub.boxes)
    conn0 = {(ln["patchline"]["source"][0],
              ln["patchline"]["destination"][0]) for ln in sub.lines}
    assert ("slot_up_depth", "slot_out") in conn0
    assert ("slot_prep_ann", "slot_out") in conn0
    # uplink keys are UNINDEXED (embedded #1 doesn't substitute; topology
    # gives the parent the slot index)
    assert "prepend depth" in texts and "prepend tmin" in texts
    assert not any("_#1" in t for t in texts)
    varnames = {b["box"].get("varname") for b in sub.boxes}
    assert {"#1 Map", "#1 Depth", "#1 Min", "#1 Max", "#1 Bipolar"} <= varnames
    # the mapper source landed as a device js asset (content-addressed)
    assert any(name.startswith("lom_mapper") for name in device._js_files)
    # slot wiring: js sink-bus outlet 0 -> zl.reg; status outlet 1 -> route
    conn = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0],
             ln["patchline"]["destination"][1]) for ln in sub.lines}
    assert ("slot_js", 0, "slot_sink_reg", 0) in conn
    assert ("slot_js", 1, "slot_route", 0) in conn
    assert ("slot_sink_unmapped", 0, "slot_extunmap", 0) in conn
    assert ("slot_extunmap", 0, "slot_js", 0) in conn
