"""Wrapper test for Device.add_curve_editor (catalog kit engines #2-#6).

The engine's contract/gesture behavior is covered in test_engines.py +
test_js_behavior.py; this file guards the DEVICE recipe — the jsui + the
hidden live.dial STATE hosts (count + per-point X/Y, Stored-Only) + the
tension/grid/snap params + the save/restore plumbing (route -> t -> listfunnel
-> spray fan-out on the way down, dials -> pak -> prepend set_all on the way
back) that makes the points list survive save/reload without a pattr blob.
"""

import pytest

from m4l_builder import AudioEffect
from m4l_builder.constants import UNITSTYLE_FLOAT, UNITSTYLE_INT, UNITSTYLE_PERCENT
from m4l_builder.parameters import PARAM_VIS_STORED_ONLY

RECT = [10, 20, 280, 120]
MAX_POINTS = 16


def _build(**kwargs):
    device = AudioEffect("Curve Editor Test", 300, 168)
    ref = device.add_curve_editor("curve", RECT, **kwargs)
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


def test_creates_jsui_with_single_message_inlet_and_points_outlet():
    device, ref = _build()
    assert ref == "curve"
    box = _boxes(device)["curve"]
    assert box["maxclass"] == "jsui"
    assert box["numinlets"] == 1
    assert box["numoutlets"] == 1
    assert box["outlettype"] == [""]
    assert box["presentation_rect"] == RECT
    # content-addressed sidecar: derive the name from the box, never hardcode it
    assert box["filename"].startswith("curve_curveedit_")
    assert box["filename"] in device._js_files


def test_state_hosts_are_stored_only_hidden_dials():
    device, _ = _build()
    boxes = _boxes(device)
    count = boxes["curve_count"]
    assert count["maxclass"] == "live.dial"
    assert count["presentation"] == 0
    valueof = count["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_longname"] == "Curve Points"
    assert valueof["parameter_mmin"] == 2.0
    assert valueof["parameter_mmax"] == float(MAX_POINTS)
    assert valueof["parameter_initial"] == [2.0]
    assert valueof["parameter_unitstyle"] == UNITSTYLE_INT
    assert valueof["parameter_invisible"] == PARAM_VIS_STORED_ONLY

    # default init_points ((0,0),(1,1)): P1=(0,0), P2=(1,1), spares zeroed.
    expected_initials = {"curve_p1x": 0.0, "curve_p1y": 0.0,
                         "curve_p2x": 1.0, "curve_p2y": 1.0,
                         "curve_p3x": 0.0, "curve_p16y": 0.0}
    for dial_id, initial in expected_initials.items():
        box = boxes[dial_id]
        assert box["maxclass"] == "live.dial"
        assert box["presentation"] == 0, "state hosts stay off the face"
        v = box["saved_attribute_attributes"]["valueof"]
        assert v["parameter_mmin"] == 0.0
        assert v["parameter_mmax"] == 1.0
        assert v["parameter_initial"] == [initial]
        assert v["parameter_unitstyle"] == UNITSTYLE_FLOAT
        assert v["parameter_invisible"] == PARAM_VIS_STORED_ONLY
    v = boxes["curve_p7x"]["saved_attribute_attributes"]["valueof"]
    assert v["parameter_longname"] == "Curve P7 X"


def test_tension_grid_snap_params_stay_automatable():
    device, _ = _build()
    boxes = _boxes(device)
    expected = {
        "curve_tension": ("Curve Tension", 0.0, 100.0, 0.0, UNITSTYLE_PERCENT),
        "curve_grid": ("Curve Grid", 1.0, 32.0, 4.0, UNITSTYLE_INT),
        "curve_snap": ("Curve Snap", 0.0, 1.0, 0.0, UNITSTYLE_INT),
    }
    for dial_id, (longname, mmin, mmax, initial, unitstyle) in expected.items():
        box = boxes[dial_id]
        assert box["presentation"] == 0
        v = box["saved_attribute_attributes"]["valueof"]
        assert v["parameter_longname"] == longname
        assert v["parameter_mmin"] == mmin
        assert v["parameter_mmax"] == mmax
        assert v["parameter_initial"] == [initial]
        assert v["parameter_unitstyle"] == unitstyle
        assert "parameter_invisible" not in v, "musical controls stay automatable"


def test_registers_all_parameters():
    device, _ = _build()
    names = {p.name for p in device.parameters()}
    expected = {"Curve Points", "Curve Tension", "Curve Grid", "Curve Snap"}
    for k in range(1, MAX_POINTS + 1):
        expected.add(f"Curve P{k} X")
        expected.add(f"Curve P{k} Y")
    assert expected <= names
    assert len(names) == 4 + 2 * MAX_POINTS


def test_save_path_wiring():
    device, _ = _build()
    boxes = _boxes(device)
    lines = _lines(device)
    assert boxes["curve_route"]["text"] == "route points"
    assert boxes["curve_split"]["text"] == "t l l"
    assert boxes["curve_len"]["text"] == "zl len"
    assert boxes["curve_half"]["text"] == "/ 2"
    assert boxes["curve_funnel"]["text"] == "listfunnel"
    assert boxes["curve_spray"]["text"] == f"spray {2 * MAX_POINTS}"
    assert boxes["curve_spray"]["numoutlets"] == 2 * MAX_POINTS
    assert ("curve", 0, "curve_route", 0) in lines
    assert ("curve_route", 0, "curve_split", 0) in lines
    # t l l fires right-to-left: coords (right outlet) land before the count.
    assert ("curve_split", 1, "curve_funnel", 0) in lines
    assert ("curve_split", 0, "curve_len", 0) in lines
    assert ("curve_len", 0, "curve_half", 0) in lines
    assert ("curve_half", 0, "curve_count", 0) in lines
    assert ("curve_funnel", 0, "curve_spray", 0) in lines
    for k in range(1, MAX_POINTS + 1):
        assert ("curve_spray", 2 * (k - 1), f"curve_p{k}x", 0) in lines
        assert ("curve_spray", 2 * (k - 1) + 1, f"curve_p{k}y", 0) in lines


def test_restore_path_wiring_and_pak_defaults():
    device, _ = _build()
    boxes = _boxes(device)
    lines = _lines(device)
    pak = boxes["curve_pak"]
    args = pak["text"].split()
    assert args[0] == "pak"
    assert args[1] == "2", "pak count default = the initial point count"
    assert args[2:6] == ["0.0", "0.0", "1.0", "1.0"], \
        "pak coordinate defaults = the initial endpoints (float-typed args)"
    assert len(args) == 2 + 2 * MAX_POINTS
    assert pak["numinlets"] == 1 + 2 * MAX_POINTS
    assert boxes["curve_setall"]["text"] == "prepend set_all"
    assert ("curve_count", 0, "curve_pak", 0) in lines
    for k in range(1, MAX_POINTS + 1):
        assert (f"curve_p{k}x", 0, "curve_pak", 2 * (k - 1) + 1) in lines
        assert (f"curve_p{k}y", 0, "curve_pak", 2 * (k - 1) + 2) in lines
    assert ("curve_pak", 0, "curve_setall", 0) in lines
    assert ("curve_setall", 0, "curve", 0) in lines


def test_control_params_feed_the_jsui_via_prepends():
    device, _ = _build()
    boxes = _boxes(device)
    lines = _lines(device)
    for cid, msg in (("curve_tension", "set_tension"),
                     ("curve_grid", "set_grid"),
                     ("curve_snap", "set_snap")):
        prep = f"{cid}_prep"
        assert boxes[prep]["text"] == f"prepend {msg}"
        assert (cid, 0, prep, 0) in lines
        assert (prep, 0, "curve", 0) in lines


def test_wire_count_is_exact():
    device, _ = _build()
    # 7 save-path spine wires + 32 spray fan-out + 33 dial->pak + 2 pak->jsui
    # + 6 tension/grid/snap = 80. Nothing extra, nothing dangling.
    assert len(_lines(device)) == 80


def test_stored_only_false_makes_points_automatable():
    device, _ = _build(stored_only=False)
    v = _boxes(device)["curve_p1x"]["saved_attribute_attributes"]["valueof"]
    assert "parameter_invisible" not in v


def test_custom_state_param_max_points_and_init_points():
    device = AudioEffect("Curve Editor Custom", 300, 168)
    device.add_curve_editor(
        "shape", RECT, state_param="Shape", max_points=4,
        init_points=((0.0, 0.2), (0.5, 0.9), (1.0, 0.4)),
        init_tension=35.0, init_grid=8, init_snap=1,
    )
    boxes = _boxes(device)
    js = device._js_files[boxes["shape"]["filename"]]
    assert "var MAX_POINTS = 4;" in js
    assert "var ys = [0.2, 0.4];" in js       # endpoints seed the first paint
    assert "var tension = 35.0;" in js
    assert "var grid_n  = 8;" in js
    assert "var snap_on = 1;" in js
    count_v = boxes["shape_count"]["saved_attribute_attributes"]["valueof"]
    assert count_v["parameter_longname"] == "Shape Points"
    assert count_v["parameter_initial"] == [3.0]
    assert count_v["parameter_mmax"] == 4.0
    mid_v = boxes["shape_p2x"]["saved_attribute_attributes"]["valueof"]
    assert mid_v["parameter_initial"] == [0.5]
    assert boxes["shape_pak"]["text"].startswith("pak 3 0.0 0.2 0.5 0.9 1.0 0.4")
    assert boxes["shape_spray"]["numoutlets"] == 8


def test_rejects_malformed_arguments():
    device = AudioEffect("Curve Editor Bad", 300, 168)
    with pytest.raises(ValueError):
        device.add_curve_editor("c1", RECT, max_points=1)
    with pytest.raises(ValueError):
        device.add_curve_editor("c2", RECT, max_points=33)
    with pytest.raises(ValueError):
        device.add_curve_editor("c3", RECT, init_points=((0.0, 0.0),))
    with pytest.raises(ValueError):
        device.add_curve_editor("c4", RECT,
                                init_points=((0.1, 0.0), (1.0, 1.0)))
    with pytest.raises(ValueError):
        device.add_curve_editor("c5", RECT,
                                init_points=((0.0, 0.0), (0.9, 1.0)))
    with pytest.raises(ValueError):
        device.add_curve_editor("c6", RECT,
                                init_points=((0.0, 0.0), (0.5, 1.5), (1.0, 1.0)))
    with pytest.raises(ValueError):
        device.add_curve_editor(
            "c7", RECT, max_points=2,
            init_points=((0.0, 0.0), (0.5, 0.5), (1.0, 1.0)))


def test_no_error_severity_lint_issues():
    device, _ = _build()
    device.add_line("obj-plugin", 0, "obj-plugout", 0)
    device.add_line("obj-plugin", 1, "obj-plugout", 1)
    errors = [i for i in device.lint() if i.severity == "error"]
    assert errors == []
