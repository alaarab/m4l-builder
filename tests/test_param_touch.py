"""param_touch — invisible native touch overlays for custom-UI surfaces."""

from m4l_builder import AudioEffect
from m4l_builder.param_touch import (add_touch_dial, add_touch_menu,
                                     add_touch_slider)

CLEAR = [0.0, 0.0, 0.0, 0.0]


def _boxes_by_id(device):
    return {b["box"]["id"]: b["box"] for b in device.boxes}


def test_touch_dial_is_transparent_native_param_host():
    dev = AudioEffect("ZZTouch", 100, 168)
    add_touch_dial(dev, "pk_dial", "Mild Dose", [10, 10, 44, 118],
                   initial=60.0)
    box = _boxes_by_id(dev)["pk_dial"]
    assert box["maxclass"] == "live.dial"
    # invisible: every colour surface alpha-0, no name/number/triangle
    for attr in ("activedialcolor", "dialcolor", "activefgdialcolor",
                 "activeneedlecolor", "needlecolor", "textcolor"):
        assert box[attr] == CLEAR, attr
    assert box["showname"] == 0 and box["shownumber"] == 0
    assert box["triangle"] == 0
    # real automatable param, full rect hit-zone
    valueof = box["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_longname"] == "Mild Dose"
    assert box["presentation_rect"][2:] == [44, 118]


def test_touch_dial_kwargs_override():
    dev = AudioEffect("ZZTouch2", 100, 168)
    add_touch_dial(dev, "d", "X", [0, 0, 10, 10],
                   min_val=-12.0, max_val=12.0, unitstyle=0,
                   annotation_name="note")
    box = _boxes_by_id(dev)["d"]
    valueof = box["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_mmin"] == -12.0
    assert valueof["parameter_mmax"] == 12.0


def test_touch_menu_is_transparent_native_picker():
    dev = AudioEffect("ZZTouch3", 100, 168)
    add_touch_menu(dev, "food_menu", "Item", [4, 70, 108, 90],
                   options=["A", "B", "C"])
    box = _boxes_by_id(dev)["food_menu"]
    assert box["maxclass"] == "live.menu"
    assert box["bgcolor"] == CLEAR
    assert box["textcolor"] == CLEAR
    valueof = box["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_longname"] == "Item"
    assert valueof["parameter_enum"] == ["A", "B", "C"]


def test_touch_slider_is_transparent_full_rect_fader():
    dev = AudioEffect("ZZTouch4", 100, 168)
    add_touch_slider(dev, "pk", "Mild Dose", [10, 10, 44, 118], initial=60.0)
    box = _boxes_by_id(dev)["pk"]
    assert box["maxclass"] == "live.slider"
    assert box["slidercolor"] == CLEAR and box["textcolor"] == CLEAR
    assert box["showname"] == 0 and box["shownumber"] == 0
    valueof = box["saved_attribute_attributes"]["valueof"]
    assert valueof["parameter_longname"] == "Mild Dose"
