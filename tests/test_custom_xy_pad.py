"""Contract + structure test for the custom XY pad v8ui engine."""

from m4l_builder.engines.ui_xy_pad import (
    CUSTOM_XY_PAD_INLETS,
    CUSTOM_XY_PAD_OUTLETS,
    custom_xy_pad_js,
)
from m4l_builder.jsui_contract import (
    find_v8ui_contract_issues,
    validate_v8ui_contract,
)


def test_xy_pad_satisfies_v8ui_contract():
    """The generated JS passes the shared mgraphics bootstrap contract."""
    js = custom_xy_pad_js(bg_top="0.08, 0.09, 0.10", bg_bot="0.05, 0.05, 0.06")
    assert find_v8ui_contract_issues(js) == []
    validate_v8ui_contract(js)  # raises on failure
    for boot in (
        "mgraphics.init()",
        "mgraphics.relative_coords = 0",
        "mgraphics.autofill = 0",
        "function paint()",
        "mgraphics.redraw()",
    ):
        assert boot in js


def test_xy_pad_two_inlets_two_outlets_and_inlet_dispatch():
    """2 inlets / 2 outlets, and set_value dispatches on the `inlet` global."""
    assert (CUSTOM_XY_PAD_INLETS, CUSTOM_XY_PAD_OUTLETS) == (2, 2)
    js = custom_xy_pad_js()
    assert "inlets = 2;" in js
    assert "outlets = 2;" in js
    assert "function set_value(v)" in js
    assert "inlet === 1" in js          # Y feedback on inlet 1
    assert "value_y = clampy(v)" in js
    assert "value_x = clampx(v)" in js
    assert "outlet(0, value_x)" in js   # drag emits X then Y
    assert "outlet(1, value_y)" in js


def test_xy_pad_y_inversion_consistent_in_update_and_paint():
    """Y is screen-inverted in BOTH the pointer->value math and the puck draw."""
    js = custom_xy_pad_js()
    assert "(1 - ny)" in js          # update(): value_y = VMINY + (1-ny)*span
    assert "(1 - normy())" in js     # paint(): cy = py + (1-normy())*ph


def test_xy_pad_pointer_handlers_and_reset():
    """Click jump, drag-fine state, and double-click reset to stored initials."""
    js = custom_xy_pad_js()
    assert "function onclick" in js
    # v8ui drag must be onpointermove/onpointerup — jsui's ondrag is NEVER called on a
    # v8ui box, so the puck would only click-to-jump with no drag (the v8ui pitfall).
    assert "function onpointermove" in js
    assert "function onpointerup" in js
    assert "function ondrag" not in js             # the dead jsui handler must be gone
    assert "function ondblclick" in js
    assert "drag_vx0" in js and "drag_vy0" in js   # Shift-fine drag-start state
    assert "INITIALX" in js and "INITIALY" in js


def test_xy_pad_self_paints_bg_and_embeds_design_system():
    """Look fixes: self-painted gradient-slice bg + glow helper, no transparency."""
    js = custom_xy_pad_js(bg_top="0.08, 0.09, 0.10", bg_bot="0.05, 0.05, 0.06")
    assert "var HASBG = 1;" in js
    assert "pattern_create_linear(0, 0, 0, h)" in js   # full-rect bg slice fill
    assert "ds_node_glow" in js                        # puck halo
    assert "// ── design-system (shared)" in js  # design_system_js() prepended


def test_xy_pad_no_bg_variant_is_valid():
    """Without bg_top/bg_bot the engine still satisfies the contract."""
    js = custom_xy_pad_js()
    validate_v8ui_contract(js)
    assert "var HASBG = 0;" in js
