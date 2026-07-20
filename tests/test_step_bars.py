"""Wrapper test for Device.add_step_bars (catalog kit engines #7-#8).

The engine's contract/gesture behavior is covered in test_engines.py +
test_js_behavior.py; this file guards the DEVICE recipe — the jsui + the
hidden live.dial STATE hosts (count + per-step values, Stored-Only) + the
native STEPS/LINK params + the save/restore plumbing (route -> t -> listfunnel
-> spray fan-out on the way down, dials -> pak -> prepend set_all on the way
back) that makes the bar values survive save/reload without a pattr blob —
plus the STEPS -> count-host sync wire that keeps the stored count honest
when the count changes without a bar edit.
"""

import pytest

from m4l_builder import AudioEffect
from m4l_builder.constants import UNITSTYLE_FLOAT, UNITSTYLE_INT
from m4l_builder.parameters import PARAM_VIS_STORED_ONLY

RECT = [10, 20, 280, 120]
MAX_STEPS = 16


def _build(**kwargs):
    device = AudioEffect("Step Bars Test", 300, 168)
    ref = device.add_step_bars("steps", RECT, **kwargs)
    return device, ref


def _boxes(device):
    return {b["box"]["id"]: b["box"] for b in device.boxes}


def _lines(device):
    return {
        (
            ln["patchline"]["source"][0],
            ln["patchline"]["source"][1],
            ln["patchline"]["destination"][0],
            ln["patchline"]["destination"][1],
        )
        for ln in device.lines
    }


def test_creates_jsui_with_single_message_inlet_and_values_outlet():
    device, ref = _build()
    assert ref == "steps"
    box = _boxes(device)["steps"]
    assert box["maxclass"] == "jsui"
    assert box["numinlets"] == 1
    assert box["numoutlets"] == 1
    assert box["outlettype"] == [""]
    assert box["presentation_rect"] == RECT
    # content-addressed sidecar: derive the name from the box, never hardcode it
    assert box["filename"].startswith("steps_stepbars_")
    assert box["filename"] in device._js_files


def test_state_hosts_are_stored_only_hidden_dials():
    device, _ = _build()
    boxes = _boxes(device)
    count = boxes["steps_steps"]
    assert count["maxclass"] == "live.dial"
    assert count["presentation"] == 0
    valueof = count["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_longname"] == "Steps N"
    assert valueof["parameter_mmin"] == 2.0
    assert valueof["parameter_mmax"] == float(MAX_STEPS)
    assert valueof["parameter_initial"] == [8.0]
    assert valueof["parameter_unitstyle"] == UNITSTYLE_INT
    assert valueof["parameter_invisible"] == PARAM_VIS_STORED_ONLY

    # default fill: every slot seeds at init_value = 1.0.
    for k in (1, 2, 8, MAX_STEPS):
        box = boxes[f"steps_s{k}"]
        assert box["maxclass"] == "live.dial"
        assert box["presentation"] == 0, "state hosts stay off the face"
        v = box["saved_attribute_attributes"]["valueof"]
        assert v["parameter_longname"] == f"Steps S{k}"
        assert v["parameter_mmin"] == 0.0
        assert v["parameter_mmax"] == 1.0
        assert v["parameter_initial"] == [1.0]
        assert v["parameter_unitstyle"] == UNITSTYLE_FLOAT
        assert v["parameter_invisible"] == PARAM_VIS_STORED_ONLY


def test_native_steps_and_link_params_stay_automatable():
    device, _ = _build()
    boxes = _boxes(device)
    num = boxes["steps_num"]
    assert num["maxclass"] == "live.numbox"
    assert num["presentation"] == 0, "parked off the face by default"
    v = num["saved_attribute_attributes"]["valueof"]
    assert v["parameter_longname"] == "Steps Count"
    assert v["parameter_mmin"] == 2.0
    assert v["parameter_mmax"] == float(MAX_STEPS)
    assert v["parameter_initial"] == [8.0]
    assert v["parameter_unitstyle"] == UNITSTYLE_INT
    assert "parameter_invisible" not in v, "STEPS is a musical control"

    link = boxes["steps_link"]
    assert link["maxclass"] == "live.text"
    assert link["presentation"] == 0
    assert link["mode"] == 1, "LINK is a latching toggle"
    lv = link["saved_attribute_attributes"]["valueof"]
    assert lv["parameter_longname"] == "Steps Link"
    assert lv["parameter_enum"] == ["Off", "Link"]
    assert lv["parameter_initial"] == [0]
    assert "parameter_invisible" not in lv


def test_steps_and_link_rects_place_the_native_controls():
    device, _ = _build(steps_rect=[10, 150, 56, 15], link_rect=[80, 148, 46, 17])
    boxes = _boxes(device)
    assert boxes["steps_num"]["presentation"] == 1
    assert boxes["steps_num"]["presentation_rect"] == [10, 150, 56, 15]
    assert boxes["steps_link"]["presentation"] == 1
    assert boxes["steps_link"]["presentation_rect"] == [80, 148, 46, 17]


def test_registers_all_parameters():
    device, _ = _build()
    names = {p.name for p in device.parameters()}
    expected = {"Steps N", "Steps Count", "Steps Link"}
    for k in range(1, MAX_STEPS + 1):
        expected.add(f"Steps S{k}")
    assert expected <= names
    assert len(names) == 3 + MAX_STEPS


def test_save_path_wiring():
    device, _ = _build()
    boxes = _boxes(device)
    lines = _lines(device)
    assert boxes["steps_route"]["text"] == "route values"
    assert boxes["steps_split"]["text"] == "t l l"
    assert boxes["steps_len"]["text"] == "zl len"
    assert boxes["steps_funnel"]["text"] == "listfunnel"
    assert boxes["steps_spray"]["text"] == f"spray {MAX_STEPS}"
    assert boxes["steps_spray"]["numoutlets"] == MAX_STEPS
    assert "steps_half" not in boxes, "one atom per step: length IS the count"
    assert ("steps", 0, "steps_route", 0) in lines
    assert ("steps_route", 0, "steps_split", 0) in lines
    # t l l fires right-to-left: slots (right outlet) land before the count.
    assert ("steps_split", 1, "steps_funnel", 0) in lines
    assert ("steps_split", 0, "steps_len", 0) in lines
    assert ("steps_len", 0, "steps_steps", 0) in lines
    assert ("steps_funnel", 0, "steps_spray", 0) in lines
    for k in range(1, MAX_STEPS + 1):
        assert ("steps_spray", k - 1, f"steps_s{k}", 0) in lines


def test_restore_path_wiring_and_pak_defaults():
    device, _ = _build()
    boxes = _boxes(device)
    lines = _lines(device)
    pak = boxes["steps_pak"]
    args = pak["text"].split()
    assert args[0] == "pak"
    assert args[1] == "8", "pak count default = the initial step count"
    assert args[2:] == ["1.0"] * MAX_STEPS, \
        "pak slot defaults = the initial values (float-typed args)"
    assert pak["numinlets"] == 1 + MAX_STEPS
    assert boxes["steps_setall"]["text"] == "prepend set_all"
    assert ("steps_steps", 0, "steps_pak", 0) in lines
    for k in range(1, MAX_STEPS + 1):
        assert (f"steps_s{k}", 0, "steps_pak", k) in lines
    assert ("steps_pak", 0, "steps_setall", 0) in lines
    assert ("steps_setall", 0, "steps", 0) in lines


def test_native_params_feed_the_jsui_via_prepends():
    device, _ = _build()
    boxes = _boxes(device)
    lines = _lines(device)
    assert boxes["steps_num_prep"]["text"] == "prepend set_steps"
    assert ("steps_num", 0, "steps_num_prep", 0) in lines
    assert ("steps_num_prep", 0, "steps", 0) in lines
    assert boxes["steps_link_prep"]["text"] == "prepend set_link"
    assert ("steps_link", 0, "steps_link_prep", 0) in lines
    assert ("steps_link_prep", 0, "steps", 0) in lines


def test_steps_param_syncs_the_stored_count_host():
    # The deliberate extra wire: STEPS -> count host, so a count change with
    # no bar edit can never leave a stale stored count (reload-order hazard).
    device, _ = _build()
    assert ("steps_num", 0, "steps_steps", 0) in _lines(device)


def test_wire_count_is_exact():
    device, _ = _build()
    # 6 save-path spine + 16 spray fan-out + 17 host->pak + 2 pak->jsui
    # + 3 STEPS (prep pair + count sync) + 2 LINK = 46. Nothing dangling.
    assert len(_lines(device)) == 14 + 2 * MAX_STEPS


def test_stored_only_false_makes_slots_automatable():
    device, _ = _build(stored_only=False)
    boxes = _boxes(device)
    v = boxes["steps_s1"]["saved_attribute_attributes"]["valueof"]
    assert "parameter_invisible" not in v
    cv = boxes["steps_steps"]["saved_attribute_attributes"]["valueof"]
    assert "parameter_invisible" not in cv


def test_custom_state_param_max_steps_and_init_values():
    device = AudioEffect("Step Bars Custom", 300, 168)
    device.add_step_bars(
        "lane", RECT, state_param="Rate", max_steps=8, init_steps=4,
        init_values=(0.25, 0.5), init_value=0.75, reset_value=0.5,
        init_link=1, link_labels=("Free", "Lock"),
    )
    boxes = _boxes(device)
    js = device._js_files[boxes["lane"]["filename"]]
    assert "var MAX_STEPS   = 8;" in js
    assert "var num_steps = 4;" in js
    assert "var values = [0.25, 0.5, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75];" in js
    assert "var RESET_VALUE = 0.5;" in js
    assert "var link_on  = 1;" in js
    count_v = boxes["lane_steps"]["saved_attribute_attributes"]["valueof"]
    assert count_v["parameter_longname"] == "Rate N"
    assert count_v["parameter_initial"] == [4.0]
    assert count_v["parameter_mmax"] == 8.0
    assert boxes["lane_s2"]["saved_attribute_attributes"]["valueof"][
        "parameter_initial"] == [0.5]
    assert boxes["lane_pak"]["text"] == \
        "pak 4 0.25 0.5 0.75 0.75 0.75 0.75 0.75 0.75"
    assert boxes["lane_spray"]["numoutlets"] == 8
    lv = boxes["lane_link"]["saved_attribute_attributes"]["valueof"]
    assert lv["parameter_enum"] == ["Free", "Lock"]
    assert lv["parameter_initial"] == [1]


def test_rejects_malformed_arguments():
    device = AudioEffect("Step Bars Bad", 300, 168)
    with pytest.raises(ValueError):
        device.add_step_bars("b1", RECT, max_steps=1)
    with pytest.raises(ValueError):
        device.add_step_bars("b2", RECT, max_steps=33)
    with pytest.raises(ValueError):
        device.add_step_bars("b3", RECT, max_steps=4, init_steps=5)
    with pytest.raises(ValueError):
        device.add_step_bars("b4", RECT, init_steps=1)
    with pytest.raises(ValueError):
        device.add_step_bars("b5", RECT, max_steps=2,
                             init_values=(0.1, 0.2, 0.3))
    with pytest.raises(ValueError):
        device.add_step_bars("b6", RECT, init_values=(0.5, 1.5))
    with pytest.raises(ValueError):
        device.add_step_bars("b7", RECT, init_value=1.5)
    with pytest.raises(ValueError):
        device.add_step_bars("b8", RECT, reset_value=-0.1)


def test_no_error_severity_lint_issues():
    device, _ = _build()
    device.add_line("obj-plugin", 0, "obj-plugout", 0)
    device.add_line("obj-plugin", 1, "obj-plugout", 1)
    errors = [i for i in device.lint() if i.severity == "error"]
    assert errors == []
