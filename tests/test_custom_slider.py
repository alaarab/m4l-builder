import pytest

from m4l_builder.engines.ui_kit import custom_slider_js
from m4l_builder.jsui_contract import (
    find_v8ui_contract_issues,
    validate_v8ui_contract,
)


class TestCustomSliderJs:
    @pytest.mark.parametrize("orientation", [0, 1])
    @pytest.mark.parametrize("bipolar", [False, True])
    def test_satisfies_v8ui_contract(self, orientation, bipolar):
        js = custom_slider_js(
            label="GAIN", vmin=-12.0, vmax=12.0, initial=0.0,
            orientation=orientation, bipolar=bipolar,
            bg_top="0.08, 0.08, 0.09", bg_bot="0.05, 0.05, 0.06",
        )
        # raises on any missing mgraphics bootstrap / paint / redraw
        assert validate_v8ui_contract(js) is js
        assert find_v8ui_contract_issues(js) == []

    def test_contract_required_snippets_present(self):
        js = custom_slider_js()
        for snippet in (
            "mgraphics.init()",
            "mgraphics.relative_coords = 0",
            "mgraphics.autofill = 0",
            "function paint()",
            "mgraphics.redraw()",
        ):
            assert snippet in js

    def test_io_and_pointer_handlers(self):
        js = custom_slider_js()
        assert "inlets = 1;" in js
        assert "outlets = 1;" in js
        # absolute-pointer handlers + inlet feedback entry points
        for fn in (
            "function onclick(",
            "function onpointermove(",   # v8ui drag handler (ondrag is dead on v8ui)
            "function ondblclick(",
            "function set_from_pointer(",
            "function set_value(",
            "function msg_float(",
            "function geom(",
        ):
            assert fn in js

    def test_embeds_design_system_helpers(self):
        js = custom_slider_js()
        assert "function ds_drop_shadow(" in js
        assert "outlet(0, value)" in js  # drag emits the value on outlet 0

    def test_absolute_pointer_mapping_not_relative_drag(self):
        js = custom_slider_js()
        # the fader maps the pointer ABSOLUTELY through set_from_pointer, and the
        # drag handler must NOT re-implement a relative delta like the knob does.
        assert "set_from_pointer(x, y, shift)" in js
        assert "drag_v0" not in js  # knob-style relative-delta state absent

    def test_vertical_inverts_y_so_up_is_max(self):
        js = custom_slider_js(orientation=0)
        # vertical: f = (track_bottom_y - y) / (track_bottom_y - track_top_y)
        assert "(gm[0] - y) / (gm[0] - gm[1])" in js

    def test_horizontal_maps_x(self):
        js = custom_slider_js(orientation=1)
        assert "(x - gm[0]) / (gm[1] - gm[0])" in js

    def test_initial_value_baked_into_state_and_reset(self):
        js = custom_slider_js(initial=3.5)
        assert "var INITIAL = 3.5;" in js
        assert "var value = 3.5;" in js
        assert "value = clampv(INITIAL)" in js  # ondblclick reset

    def test_bipolar_fill_from_zero_detent(self):
        js = custom_slider_js(vmin=-12.0, vmax=12.0, bipolar=True)
        assert "var BIPOLAR = 1;" in js
        # detent normalized from value 0, not the track midpoint
        assert "var nd = BIPOLAR ? norm(0) : 0;" in js

    def test_self_paints_gradient_background(self):
        js = custom_slider_js(bg_top="0.08, 0.08, 0.09", bg_bot="0.05, 0.05, 0.06")
        assert "var HASBG = 1;" in js
        assert "pattern_create_linear(0, 0, 0, h)" in js
        assert "mgraphics.rectangle(0, 0, w, h); mgraphics.fill();" in js

    def test_no_bg_when_slice_missing(self):
        js = custom_slider_js()
        assert "var HASBG = 0;" in js

    def test_paint_is_flat_no_nested_functions(self):
        js = custom_slider_js()
        start = js.index("function paint()")
        depth = 0
        i = js.index("{", start)
        body_start = i
        while i < len(js):
            if js[i] == "{":
                depth += 1
            elif js[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = js[body_start:i + 1]
        assert "function " not in body
