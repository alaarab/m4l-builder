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
    # guard extended in the laziness audit: lane 2 grabbing lane 1's
    # "1 RM" chip was Live-reproduced — the row-chip vocabulary is refused
    assert ('new RegExp("Map|Min|Max|Depth|Bipolar|RM|Add|Ratio|Source|On")'
            in js)
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


def test_slot_mode_switch_and_add_chip():
    """Catalog #15/#16: opt-in R/M switch drives the retarget sink's mode
    inlet (hot swap), '+' add chip uplinks like Bipolar; both default OFF."""
    device = AudioEffect("Map Test", width=300, height=168)
    sub, ids = modulator_slot_component(
        device, accent=[1.0, 0.6, 0.2, 1.0], mode_switch=True, add_chip=True)
    boxes = {b["box"]["id"]: b["box"] for b in sub.boxes}
    conn = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0],
             ln["patchline"]["destination"][1]) for ln in sub.lines}
    # R/M chip: enum param, wired to the sink's mode inlet + mode uplink
    mode = boxes["slot_mode"]
    v = mode["saved_attribute_attributes"]["valueof"]
    assert v["parameter_enum"] == ["R", "M"]
    assert v["parameter_longname"] == "#1 RM"
    assert ("slot_mode", 0, "slot_sink_mode", 0) in conn
    assert ("slot_mode", 0, "slot_up_mode", 0) in conn
    assert ("slot_up_mode", 0, "slot_out", 0) in conn
    assert boxes["slot_up_mode"]["text"] == "prepend mode"
    # '+' chip: enum param + add uplink (engine-side consumption, like BI)
    addc = boxes["slot_addc"]
    av = addc["saved_attribute_attributes"]["valueof"]
    assert av["parameter_longname"] == "#1 Add"
    assert ("slot_addc", 0, "slot_up_add", 0) in conn
    assert ("slot_up_add", 0, "slot_out", 0) in conn
    # chips extend the row rightward past BI without overlap
    bi_x = boxes["slot_bipolar"]["presentation_rect"][0]
    assert mode["presentation_rect"][0] == bi_x + 17
    assert addc["presentation_rect"][0] == bi_x + 34
    # column map exports every column for the header recipe
    cols = ids["columns"]
    assert {"map", "target", "depth", "min", "max",
            "bipolar", "mode", "add"} <= set(cols)
    assert cols["mode"] == (bi_x + 17, 15)
    assert ids["mode"] == "slot_mode" and ids["add"] == "slot_addc"


def test_slot_defaults_stay_byte_identical():
    """mode_switch/add_chip default OFF: Orbit's existing call must not gain
    boxes, params, or lines."""
    dev_a = AudioEffect("A", width=300, height=168)
    sub_a, ids_a = modulator_slot_component(dev_a, accent=[1, 0.6, 0.2, 1])
    ids_a.pop("columns")            # the only new key on the default path
    assert not any(b["box"]["id"] in ("slot_mode", "slot_addc",
                                      "slot_up_mode", "slot_up_add")
                   for b in sub_a.boxes)
    varnames = {b["box"].get("varname") for b in sub_a.boxes}
    assert "#1 RM" not in varnames and "#1 Add" not in varnames


def test_modulator_header_row_aligns_to_columns():
    from m4l_builder.recipes import modulator_header_row
    device = AudioEffect("H", width=300, height=168)
    sub, ids = modulator_slot_component(
        device, accent=[1, 0.6, 0.2, 1], mode_switch=True)
    modulator_header_row(device, "hdr", at=[8, 46], columns=ids["columns"])
    boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
    cols = ids["columns"]
    # one caption per column, x-aligned to slot geometry, 9px above the row
    for key, (cx, _cw) in cols.items():
        cap = boxes[f"hdr_h_{key}"]
        assert cap["presentation_rect"][0] == 8 + cx
        assert cap["presentation_rect"][1] == 46 - 9
    assert boxes["hdr_h_bipolar"]["text"] == "±"
    assert boxes["hdr_h_mode"]["text"] == "R M"


def test_parameter_modmode_serializes():
    """Live 12 Mod data model (Clix corpus): parameter_modmode emits only
    when set — the fleet stays byte-stable by default."""
    from m4l_builder.parameters import ParameterSpec
    spec = ParameterSpec(name="X", minimum=0.0, maximum=1.0, modmode=3,
                         linknames=1)
    v = spec.to_valueof_dict()
    assert v["parameter_modmode"] == 3
    plain = ParameterSpec(name="Y", minimum=0.0, maximum=1.0)
    assert "parameter_modmode" not in plain.to_valueof_dict()


def test_slot_row_anatomy_kwargs():
    """Catalog #14/#19/#21/#22/#26: ✗ unmap, rowcolor recolor bus, value bar,
    pname/dname uplinks — all opt-in; default stays byte-identical."""
    device = AudioEffect("Map Test", width=300, height=168)
    sub, ids = modulator_slot_component(
        device, accent=[1.0, 0.6, 0.2, 1.0], mode_switch=True, add_chip=True,
        unmap_button=True, value_bar=True, row_color=True,
        uplink_pname=True, uplink_dname=True)
    boxes = {b["box"]["id"]: b["box"] for b in sub.boxes}
    conn = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
             ln["patchline"]["destination"][0],
             ln["patchline"]["destination"][1]) for ln in sub.lines}
    # ✗ unmap: message click -> "unmap" -> mapper js
    assert boxes["slot_x"]["text"] == "✗"
    assert boxes["slot_x_un"]["text"] == "unmap"
    assert ("slot_x", 0, "slot_x_un", 0) in conn
    assert ("slot_x_un", 0, "slot_js", 0) in conn
    # value bar: leftmost 5px meter fed by snapshot~ from the remote inlet;
    # the whole row shifted right 7px
    assert boxes["slot_bar"]["presentation_rect"] == [0, 1, 5, 15]
    assert boxes["slot_map"]["presentation_rect"][0] == 7
    assert ("slot_rsig_r", 0, "slot_bar_snap", 0) in conn
    assert ("slot_bar_snap", 0, "slot_bar", 0) in conn
    # rowcolor: inlet-0 route recolors chips (bgoncolor) + LCDs (lcdcolor)
    assert ("slot_in", 0, "slot_rc_route", 0) in conn
    for chip in ("slot_map", "slot_bipolar", "slot_mode", "slot_addc"):
        assert ("slot_rc_on", 0, chip, 0) in conn
    for nb in ("slot_depth", "slot_umin", "slot_umax"):
        assert ("slot_rc_lcd", 0, nb, 0) in conn
    assert ("slot_rc_bar", 0, "slot_bar", 0) in conn
    # pname/dname uplink = the RAW js status stream (selectors pname/dname
    # are safe; re-prefixing after route hands prepend a `set …` payload it
    # consumes as its own re-config verb — Live-verified trap, T05)
    assert ("slot_js", 1, "slot_out", 0) in conn
    # columns gained bar + unmap; unmap sits right of the + chip
    assert ids["columns"]["bar"] == (0, 5)
    un_x, _ = ids["columns"]["unmap"]
    assert un_x == ids["columns"]["add"][0] + 17


def test_slot_value_bar_rejects_icon_mode():
    import pytest
    device = AudioEffect("Map Test", width=300, height=168)
    with pytest.raises(ValueError, match="left edge"):
        modulator_slot_component(
            device, accent=[1, 0.6, 0.2, 1], value_bar=True,
            source_enum=["A", "B"], source_glyphs=["sine", "square"])


def test_slot_anatomy_defaults_add_nothing():
    device = AudioEffect("A", width=300, height=168)
    sub, _ids = modulator_slot_component(device, accent=[1, 0.6, 0.2, 1])
    ids_present = {b["box"]["id"] for b in sub.boxes}
    for absent in ("slot_x", "slot_bar", "slot_rc_route"):
        assert absent not in ids_present
    conn_d = {(ln["patchline"]["source"][0], ln["patchline"]["source"][1],
               ln["patchline"]["destination"][0])
              for ln in sub.lines}
    assert ("slot_js", 1, "slot_out") not in conn_d


def test_mapping_summary_chip():
    from m4l_builder.recipes import mapping_summary_chip
    device = AudioEffect("S", width=300, height=168)
    res = mapping_summary_chip(device, "sum", rect=[40, 2, 140, 12],
                               accent=[1.0, 0.6, 0.2, 1.0])
    boxes = {b["box"]["id"]: b["box"] for b in device.boxes}
    lines = {(ln["patchline"]["source"][0],
              ln["patchline"]["destination"][0]) for ln in device.lines}
    assert boxes["sum_txt"]["text"] == "—"
    # js emits ready-made "set <name>" payloads — ports ARE the textedits
    assert res.ports["pname_in"].box_id == "sum_txt"
    assert res.ports["dname_in"].box_id == "sum_dev"
    # unmap (mapped 0) clears both fields and dims the dot
    assert ("sum_clr_p", "sum_txt") in lines
    assert ("sum_clr_d", "sum_dev") in lines
    assert ("sum_c_off", "sum_dot") in lines
    assert {"pname_in", "dname_in", "mapped_in"} <= set(res.ports)
