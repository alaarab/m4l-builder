"""Tests for the draggable_value_readout v8ui control (custom_readout_js).

Mirrors the test style of the existing kit controls: import the generator, run
the v8ui contract gate over its output, and assert the key structure (bootstrap,
pointer handlers, the self-painted bg-slice block, and the two-way wiring hooks).
"""

import pytest

from m4l_builder.engines.ui_kit import custom_readout_js
from m4l_builder.jsui_contract import (
    find_v8ui_contract_issues,
    validate_v8ui_contract,
)


def test_custom_readout_satisfies_v8ui_contract():
    # Contract: mgraphics.init / relative_coords=0 / autofill=0 / paint() / redraw.
    js = custom_readout_js()
    assert find_v8ui_contract_issues(js) == []
    # validate_* raises on violation; returns the source on success.
    assert validate_v8ui_contract(js) == js


def test_custom_readout_declares_inlet_and_outlet():
    js = custom_readout_js()
    assert "inlets = 1;" in js
    assert "outlets = 1;" in js


def test_custom_readout_has_pointer_handlers_and_drag_math():
    js = custom_readout_js(vmin=-12.0, vmax=12.0)
    # The drag handlers (clone of custom_knob_js) emit on outlet 0 in param units.
    assert "function onclick(" in js
    assert "function onpointermove(" in js   # v8ui drag handler (ondrag dead on v8ui)
    assert "function ondblclick(" in js
    assert "outlet(0, value);" in js
    # Vertical drag math + Shift-fine sensitivity (param-unit drag).
    assert "(drag_y0 - y) / 130.0" in js
    assert "shift ? 0.22 : 1.0" in js


def test_custom_readout_receives_set_value_for_automation_redraw():
    # The hidden dial sends 'set_value <v>' back in to redraw on automation.
    js = custom_readout_js()
    assert "function set_value(v)" in js
    assert "function msg_float(v)" in js
    assert "mgraphics.redraw()" in js


def test_custom_readout_self_paints_bg_slice_when_supplied():
    # With bg_top/bg_bot it must paint its OWN gradient slice (no transparent
    # compositing in M4L) — the HASBG block from the knob, verbatim shape.
    js = custom_readout_js(bg_top="0.08, 0.09, 0.10", bg_bot="0.05, 0.06, 0.07")
    assert "var HASBG = 1;" in js
    assert "pattern_create_linear(0, 0, 0, h)" in js
    assert "mgraphics.rectangle(0, 0, w, h); mgraphics.fill();" in js
    # Without the gradient, HASBG is off (still a valid, framed cell).
    assert "var HASBG = 0;" in custom_readout_js()


def test_custom_readout_embeds_label_unit_and_value_text():
    js = custom_readout_js(label="GAIN", unit=" dB", decimals=2)
    assert 'var LABEL = "GAIN";' in js
    assert 'var UNIT = " dB";' in js
    assert "var DECIMALS = 2;" in js
    assert "value.toFixed(DECIMALS) + UNIT" in js


def test_custom_readout_bipolar_bar_originates_at_center():
    js = custom_readout_js(bipolar=True)
    assert "var BIPOLAR = 1;" in js
    # Bipolar fill grows from the 0.5 center, unipolar from 0.0.
    assert "BIPOLAR ? 0.5 : 0.0" in js


@pytest.mark.parametrize("align,code", [("left", 0), ("center", 1), ("right", 2)])
def test_custom_readout_align_maps_to_code(align, code):
    js = custom_readout_js(align=align)
    assert f"var ALIGN = {code};" in js


def test_custom_readout_show_bar_toggle_and_glow_tip():
    on = custom_readout_js(show_bar=True)
    assert "var SHOW_BAR = 1;" in on
    # Compact single-row layout: the bar draws a thin accent fill to xTo (no
    # node-glow tip, kept minimal so the readout stays legible down to ~h=13).
    assert "line_to(hi, barY)" in on
    off = custom_readout_js(show_bar=False)
    assert "var SHOW_BAR = 0;" in off
