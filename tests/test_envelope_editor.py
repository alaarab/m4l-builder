"""Wrapper test for Device.add_envelope_editor (dnksaus kit engine #1).

The engine's contract/gesture behavior is covered in test_engines.py +
test_js_behavior.py; this file guards the DEVICE recipe — the jsui + FOUR
hidden automatable live.dial params + the 8 wires (drag path out, back-sync
path in) that make the editor record automation like four knobs.
"""

import pytest

from m4l_builder import AudioEffect
from m4l_builder.constants import UNITSTYLE_FLOAT, UNITSTYLE_TIME

RECT = [10, 20, 280, 96]
PARAMS = ("Amp Attack", "Amp Decay", "Amp Sustain", "Amp Release")


def _build():
    device = AudioEffect("Env Editor Test", 300, 168)
    ref = device.add_envelope_editor("env", RECT, params=PARAMS)
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


def test_creates_jsui_with_four_by_four_io():
    device, ref = _build()
    assert ref == "env"
    box = _boxes(device)["env"]
    assert box["maxclass"] == "jsui"
    assert box["numinlets"] == 4
    assert box["numoutlets"] == 4
    assert box["outlettype"] == ["float", "float", "float", "float"]
    assert box["presentation_rect"] == RECT
    # content-addressed sidecar: derive the name from the box, never hardcode it
    assert box["filename"].startswith("env_envedit_")
    assert box["filename"] in device._js_files


def test_creates_four_hidden_automatable_params_with_given_longnames():
    device, _ = _build()
    boxes = _boxes(device)
    expected = {
        "env_dial0": ("Amp Attack", 2000.0, UNITSTYLE_TIME, 10.0),
        "env_dial1": ("Amp Decay", 4000.0, UNITSTYLE_TIME, 200.0),
        "env_dial2": ("Amp Sustain", 1.0, UNITSTYLE_FLOAT, 0.7),
        "env_dial3": ("Amp Release", 8000.0, UNITSTYLE_TIME, 400.0),
    }
    for dial_id, (longname, mmax, unitstyle, initial) in expected.items():
        box = boxes[dial_id]
        assert box["maxclass"] == "live.dial"
        assert box["presentation"] == 0, "param dials must stay out of presentation"
        valueof = box["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == longname
        assert valueof["parameter_mmin"] == 0.0
        assert valueof["parameter_mmax"] == mmax
        assert valueof["parameter_unitstyle"] == unitstyle
        assert valueof["parameter_initial"] == [initial]
    assert [p.name for p in device.parameters()] == list(PARAMS)


def test_wires_both_directions_eight_lines():
    device, _ = _build()
    lines = _lines(device)
    for i in range(4):
        assert ("env", i, f"env_dial{i}", 0) in lines, "drag path: jsui -> param"
        assert (f"env_dial{i}", 0, "env", i) in lines, "back-sync: param -> jsui inlet"
    env_lines = {ln for ln in lines if "env" in (ln[0], ln[2]) or
                 ln[0].startswith("env_") or ln[2].startswith("env_")}
    assert len(env_lines) == 8, "exactly the 8 wires, nothing extra"


def test_initials_and_ranges_thread_into_the_js():
    device, _ = _build()
    box = _boxes(device)["env"]
    js = device._js_files[box["filename"]]
    assert "var MAX_A = 2000.0;" in js
    assert "var MAX_D = 4000.0;" in js
    assert "var MAX_R = 8000.0;" in js
    assert "var attack_ms  = 10.0;" in js
    assert "var sustain    = 0.7;" in js


def test_custom_ranges_initial_and_names():
    device = AudioEffect("Env Editor Custom", 300, 168)
    device.add_envelope_editor(
        "shape", RECT,
        params=("A", "D", "S", "R"),
        max_attack_ms=500.0, max_decay_ms=1000.0, max_release_ms=2000.0,
        initial=(5.0, 50.0, 0.5, 100.0),
    )
    boxes = _boxes(device)
    js = device._js_files[boxes["shape"]["filename"]]
    assert "var MAX_A = 500.0;" in js
    assert "var MAX_R = 2000.0;" in js
    assert "var decay_ms   = 50.0;" in js
    valueof = boxes["shape_dial3"]["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_longname"] == "R"
    assert valueof["parameter_mmax"] == 2000.0
    assert valueof["parameter_initial"] == [100.0]


def test_rejects_malformed_params_and_initial():
    device = AudioEffect("Env Editor Bad", 300, 168)
    with pytest.raises(ValueError):
        device.add_envelope_editor("env", RECT, params=("A", "D", "S"))
    with pytest.raises(ValueError):
        device.add_envelope_editor("env", RECT, initial=(1.0, 2.0))


def test_no_error_severity_lint_issues():
    device, _ = _build()
    device.add_line("obj-plugin", 0, "obj-plugout", 0)
    device.add_line("obj-plugin", 1, "obj-plugout", 1)
    errors = [i for i in device.lint() if i.severity == "error"]
    assert errors == []
