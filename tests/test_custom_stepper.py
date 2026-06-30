"""Tests for the custom +/- stepper v8ui generator (ui_kit.custom_stepper_js)."""

from m4l_builder.engines.ui_kit import (
    CUSTOM_STEPPER_INLETS,
    CUSTOM_STEPPER_OUTLETS,
    custom_stepper_js,
)
from m4l_builder.jsui_contract import validate_v8ui_contract


def test_custom_stepper_satisfies_v8ui_contract():
    js = custom_stepper_js(
        label="VOICES", vmin=1, vmax=8, initial=1, step=1, decimals=0,
        bg_top="0.08, 0.09, 0.10", bg_bot="0.07, 0.07, 0.08",
    )
    # Does not raise; returns the same source (mgraphics bootstrap + paint + redraw).
    assert validate_v8ui_contract(js) == js


def test_custom_stepper_has_pointer_and_step_logic():
    js = custom_stepper_js(label="DRIVE", vmin=-24, vmax=24, initial=0.0, step=0.5, decimals=1)
    for snippet in (
        "function onclick(", "function onpointermove(", "function ondblclick(",
        "function set_value(", "function quantize(", "outlet(0, value)",
        "rectangle_rounded", "ds_set_cursor",
    ):
        assert snippet in js, snippet
    assert "inlets = 1" in js
    assert "outlets = 1" in js
    assert CUSTOM_STEPPER_INLETS == 1
    assert CUSTOM_STEPPER_OUTLETS == 1


def test_custom_stepper_self_paints_gradient_background():
    js = custom_stepper_js(bg_top="0.08, 0.09, 0.10", bg_bot="0.07, 0.07, 0.08")
    assert "var HASBG = 1;" in js
    assert "pattern_create_linear(0, 0, 0, h)" in js
    # No gradient supplied → HASBG off (still a valid, self-contained engine).
    assert "var HASBG = 0;" in custom_stepper_js()


def test_fine_step_defaults_by_decimals():
    # Integer params: fine_step == step (no sub-unit steps).
    assert "var FINE = 1.0;" in custom_stepper_js(step=1, decimals=0)
    # Float params: fine_step == step / 10.
    assert "var FINE = 0.05;" in custom_stepper_js(step=0.5, decimals=1)
    # Explicit fine_step is honored.
    assert "var FINE = 0.25;" in custom_stepper_js(step=1.0, fine_step=0.25, decimals=2)
