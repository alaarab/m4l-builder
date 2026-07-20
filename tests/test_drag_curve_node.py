"""Contract + structure tests for the drag_curve_node v8ui engine."""


from m4l_builder.engines.ui_curve_node import (
    DRAG_CURVE_NODE_INLETS,
    DRAG_CURVE_NODE_OUTLETS,
    drag_curve_node_js,
)
from m4l_builder.jsui_contract import (
    find_v8ui_contract_issues,
    validate_v8ui_contract,
)


def test_drag_curve_node_satisfies_v8ui_contract():
    # bg slice supplied (the seamless-float path).
    js = drag_curve_node_js(bg_top="0.085, 0.090, 0.102", bg_bot="0.055, 0.058, 0.067")
    # Must not raise.
    validate_v8ui_contract(js)
    assert find_v8ui_contract_issues(js) == []


def test_contract_holds_without_bg_and_for_crosshair_variant():
    js = drag_curve_node_js(draw_curve=False)  # no bg, bare crosshair
    validate_v8ui_contract(js)


def test_emits_required_mgraphics_bootstrap():
    js = drag_curve_node_js()
    for snippet in (
        "mgraphics.init()",
        "mgraphics.relative_coords = 0",
        "mgraphics.autofill = 0",
        "function paint()",
        "mgraphics.redraw()",
    ):
        assert snippet in js, f"missing bootstrap fragment: {snippet}"


def test_two_outlets_and_dual_axis_setters():
    assert DRAG_CURVE_NODE_INLETS == 1
    assert DRAG_CURVE_NODE_OUTLETS == 2
    js = drag_curve_node_js()
    # Two outlets declared.
    assert "outlets = 2;" in js
    assert "inlets = 1;" in js
    # One setter per axis (automation -> redraw), dispatched by message name.
    assert "function set_value_x(" in js
    assert "function set_value_y(" in js
    # Each axis emits on its own outlet index, ONLY when moved.
    assert "outlet(0, vx)" in js
    assert "outlet(1, vy)" in js


def test_setters_do_not_emit_outlet_no_feedback_storm():
    # The inbound setters must redraw but NEVER call outlet(), else automation
    # playback feeds back into the dials.
    js = drag_curve_node_js()
    setx = js[js.index("function set_value_x("):]
    setx = setx[: setx.index("}") + 1]
    sety = js[js.index("function set_value_y("):]
    sety = sety[: sety.index("}") + 1]
    assert "outlet(" not in setx
    assert "outlet(" not in sety
    assert "mgraphics.redraw()" in setx
    assert "mgraphics.redraw()" in sety


def test_dual_pointer_path_present():
    js = drag_curve_node_js()
    # Modern (Live device) + legacy (Max edit view) handlers both present.
    for fn in (
        "function onpointerdown(",
        "function onpointermove(",
        "function onpointerup(",
        "function onclick(",
        "function ondrag(",
        "function ondblclick(",
    ):
        assert fn in js, f"missing pointer handler: {fn}"


def test_coordinate_maps_and_hit_test_present():
    js = drag_curve_node_js()
    for fn in (
        "function val_to_x(",
        "function x_to_val(",
        "function val_to_y(",
        "function y_to_val(",
        "function hit_test(",
        "function handle_press(",
        "function handle_drag_at(",
    ):
        assert fn in js, f"missing map/drag fn: {fn}"


def test_self_paints_background_slice_when_supplied():
    js = drag_curve_node_js(bg_top="0.085, 0.090, 0.102", bg_bot="0.055, 0.058, 0.067")
    assert "var HASBG = 1;" in js
    assert "pattern_create_linear(0, 0, 0, h)" in js
    assert "var BG_TOP = [0.085, 0.090, 0.102];" in js
    assert "var BG_BOT = [0.055, 0.058, 0.067];" in js
    # No bg -> HASBG off.
    assert "var HASBG = 0;" in drag_curve_node_js()


def test_log_axis_threads_exponent():
    # exponent_x > 1 emits the log-map branch in val_to_x/x_to_val.
    js = drag_curve_node_js(exponent_x=3.0)
    assert "var EXPX = 3.0;" in js
    assert "EXPX > 1.0001" in js


def test_design_system_helpers_prepended():
    js = drag_curve_node_js()
    # The shared glow/shadow/cursor helpers must be embedded.
    for sym in ("ds_node_glow", "ds_drop_shadow", "ds_set_cursor", "DS_CUR_GRAB"):
        assert sym in js, f"missing design-system symbol: {sym}"
