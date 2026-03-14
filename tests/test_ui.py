"""Tests for UI/presentation element creators in ui.py."""

from m4l_builder.ui import (panel, dial, tab, toggle, comment, scope, meter,
                             menu, number_box, slider, button, live_text, fpic,
                             live_gain, multislider, jsui, v8ui, adsrui, live_drop,
                             bpatcher, swatch, textedit, live_step, live_grid,
                             live_line, live_arrows, rslider, kslider,
                             textbutton, umenu, radiogroup, nodes, matrixctrl,
                             ubutton, nslider)
from m4l_builder.constants import DEFAULT_TEXT_COLOR


class TestPanel:
    """Test panel() creates correct background elements."""

    def test_returns_box_dict(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.1, 0.1, 0.1, 1.0])
        assert "box" in result

    def test_background_always_set_to_1(self):
        """panel must set background:1 so it renders behind other objects in presentation view."""
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["background"] == 1

    def test_bgcolor_is_set(self):
        color = [0.2, 0.3, 0.4, 1.0]
        result = panel("p-1", [0, 0, 200, 100], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_mode_is_0(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["mode"] == 0

    def test_presentation_is_1(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 300, 150]
        result = panel("p-1", rect, bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["presentation_rect"] == rect

    def test_border_default_is_0(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["border"] == 0

    def test_rounded_default_is_0(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["rounded"] == 0

    def test_bordercolor_omitted_by_default(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert "bordercolor" not in result["box"]

    def test_bordercolor_set_when_provided(self):
        color = [1.0, 0.0, 0.0, 1.0]
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0], bordercolor=color)
        assert result["box"]["bordercolor"] == color

    def test_custom_border_and_rounded(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0],
                       border=2, rounded=8)
        assert result["box"]["border"] == 2
        assert result["box"]["rounded"] == 8

    def test_maxclass_is_panel(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["maxclass"] == "panel"

    def test_numinlets_and_numoutlets(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 0

    def test_patching_rect_defaults_offscreen(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 100

    def test_kwargs_passthrough(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0],
                       custom_attr="test_val")
        assert result["box"]["custom_attr"] == "test_val"

    def test_bgfillcolor_set(self):
        gradient = {"type": "gradient", "color1": [0.1, 0.1, 0.1, 1.0],
                     "color2": [0.2, 0.2, 0.2, 1.0], "angle": 270, "proportion": 0.5}
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0],
                       bgfillcolor=gradient)
        assert result["box"]["bgfillcolor"] == gradient

    def test_shadow_set(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0], shadow=2)
        assert result["box"]["shadow"] == 2

    def test_shape_set(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.0, 0.0, 0.0, 1.0], shape=1)
        assert result["box"]["shape"] == 1


class TestDial:
    """Test dial() creates correct live.dial parameter objects."""

    def test_returns_box_dict(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert "box" in result

    def test_maxclass_is_live_dial(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["maxclass"] == "live.dial"

    def test_varname_is_set(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["varname"] == "cutoff"

    def test_parameter_enable_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["parameter_enable"] == 1

    def test_numinlets_and_numoutlets(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 2

    def test_presentation_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 45, 45]
        result = dial("d-1", "cutoff", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_saved_attribute_attributes_exists(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert "saved_attribute_attributes" in result["box"]
        assert "valueof" in result["box"]["saved_attribute_attributes"]

    def test_parameter_initial_enable_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_initial_enable"] == 1

    def test_parameter_initial_is_list(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45], initial=25.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert isinstance(valueof["parameter_initial"], list)
        assert valueof["parameter_initial"] == [25.0]

    def test_min_max_vals(self):
        result = dial("d-1", "freq", [10, 10, 45, 45], min_val=20.0, max_val=20000.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == 20.0
        assert valueof["parameter_mmax"] == 20000.0

    def test_default_min_max(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == 0.0
        assert valueof["parameter_mmax"] == 100.0

    def test_shortname_defaults_to_varname(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "cutoff"

    def test_shortname_custom(self):
        result = dial("d-1", "cutoff_freq", [10, 10, 45, 45], shortname="Cutoff")
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "Cutoff"

    def test_unitstyle_default_is_5(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_unitstyle"] == 5

    def test_unitstyle_custom(self):
        result = dial("d-1", "freq", [10, 10, 45, 45], unitstyle=2)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_unitstyle"] == 2

    def test_parameter_longname_is_varname(self):
        result = dial("d-1", "resonance", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == "resonance"

    def test_parameter_type_is_0(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 0

    def test_patching_rect_defaults_offscreen(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 45
        assert pr[3] == 45

    def test_custom_patching_rect(self):
        custom = [50, 50, 45, 45]
        result = dial("d-1", "cutoff", [10, 10, 45, 45], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_kwargs_passthrough(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45],
                       activedialcolor=[1, 0, 0, 1])
        assert result["box"]["activedialcolor"] == [1, 0, 0, 1]

    def test_appearance_default_is_0(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["appearance"] == 0

    def test_appearance_custom(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45], appearance=2)
        assert result["box"]["appearance"] == 2

    def test_activedialcolor_set(self):
        color = [0.8, 0.2, 0.1, 1.0]
        result = dial("d-1", "cutoff", [10, 10, 45, 45], activedialcolor=color)
        assert result["box"]["activedialcolor"] == color

    def test_activeneedlecolor_set(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = dial("d-1", "cutoff", [10, 10, 45, 45], activeneedlecolor=color)
        assert result["box"]["activeneedlecolor"] == color

    def test_showname_default_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["showname"] == 1

    def test_showname_hidden(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45], showname=0)
        assert result["box"]["showname"] == 0

    def test_shownumber_default_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["shownumber"] == 1

    def test_parameter_exponent_default_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_exponent"] == 1.0

    def test_parameter_exponent_custom(self):
        result = dial("d-1", "freq", [10, 10, 45, 45], parameter_exponent=3.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_exponent"] == 3.0

    def test_triangle_default_is_1(self):
        result = dial("d-1", "cutoff", [10, 10, 45, 45])
        assert result["box"]["triangle"] == 1

    def test_focusbordercolor_set(self):
        color = [0.5, 0.8, 0.5, 1.0]
        result = dial("d-1", "cutoff", [10, 10, 45, 45], focusbordercolor=color)
        assert result["box"]["focusbordercolor"] == color


class TestTab:
    """Test tab() creates correct live.tab selector objects."""

    def test_returns_box_dict(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B", "C"])
        assert "box" in result

    def test_maxclass_is_live_tab(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"])
        assert result["box"]["maxclass"] == "live.tab"

    def test_parameter_type_is_2(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B", "C"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 2

    def test_parameter_enum_is_list(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["sine", "saw", "square"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == ["sine", "saw", "square"]

    def test_parameter_mmax_matches_last_option_index(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B", "C", "D"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == 0
        assert valueof["parameter_mmax"] == 3
        assert valueof["parameter_initial"] == [0]

    def test_num_lines_patching_is_1(self):
        options = ["A", "B", "C", "D"]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=options)
        assert result["box"]["num_lines_patching"] == 1

    def test_num_lines_presentation_is_1(self):
        options = ["A", "B", "C"]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=options)
        assert result["box"]["num_lines_presentation"] == 1

    def test_numinlets_and_numoutlets(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"])
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 3

    def test_presentation_is_1(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 10, 200, 30]
        result = tab("t-1", "mode", rect, options=["A", "B"])
        assert result["box"]["presentation_rect"] == rect

    def test_color_kwargs_omitted_by_default(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"])
        box = result["box"]
        assert "bgcolor" not in box
        assert "bgoncolor" not in box
        assert "textcolor" not in box
        assert "textoncolor" not in box

    def test_bgcolor_set_when_provided(self):
        color = [0.1, 0.1, 0.1, 1.0]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_bgoncolor_set_when_provided(self):
        color = [0.5, 0.5, 0.9, 1.0]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], bgoncolor=color)
        assert result["box"]["bgoncolor"] == color

    def test_textcolor_set_when_provided(self):
        color = [0.8, 0.8, 0.8, 1.0]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], textcolor=color)
        assert result["box"]["textcolor"] == color

    def test_textoncolor_set_when_provided(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], textoncolor=color)
        assert result["box"]["textoncolor"] == color

    def test_patching_rect_defaults_offscreen(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700

    def test_custom_patching_rect(self):
        custom = [100, 100, 200, 30]
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_rounded_set(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], rounded=4.0)
        assert result["box"]["rounded"] == 4.0

    def test_spacing_x_set(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], spacing_x=2.0)
        assert result["box"]["spacing_x"] == 2.0

    def test_appearance_set(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"], appearance=1)
        assert result["box"]["appearance"] == 1

    def test_kwargs_passthrough(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["A", "B"],
                      custom_key="custom_val")
        assert result["box"]["custom_key"] == "custom_val"


class TestToggle:
    """Test toggle() creates correct live.toggle objects."""

    def test_returns_box_dict(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        assert "box" in result

    def test_maxclass_is_live_toggle(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        assert result["box"]["maxclass"] == "live.toggle"

    def test_parameter_type_is_2(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 2

    def test_parameter_enum_is_off_on(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == ["off", "on"]

    def test_numinlets_is_1(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_1(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        assert result["box"]["numoutlets"] == 1

    def test_parameter_enable_is_1(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        assert result["box"]["parameter_enable"] == 1

    def test_presentation_is_1(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [15, 25, 20, 20]
        result = toggle("tog-1", "enabled", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_shortname_defaults_to_varname(self):
        result = toggle("tog-1", "bypass", [10, 10, 20, 20])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "bypass"

    def test_shortname_custom(self):
        result = toggle("tog-1", "bypass", [10, 10, 20, 20], shortname="On/Off")
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "On/Off"

    def test_patching_rect_defaults_offscreen(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700

    def test_custom_patching_rect(self):
        custom = [200, 200, 20, 20]
        result = toggle("tog-1", "enabled", [10, 10, 20, 20], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_kwargs_passthrough(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20],
                         activebgoncolor=[1, 0.5, 0, 1])
        assert result["box"]["activebgoncolor"] == [1, 0.5, 0, 1]

    def test_activebgcolor_set(self):
        color = [0.2, 0.2, 0.2, 1.0]
        result = toggle("tog-1", "enabled", [10, 10, 20, 20], activebgcolor=color)
        assert result["box"]["activebgcolor"] == color

    def test_activebgoncolor_set(self):
        color = [0.8, 0.4, 0.1, 1.0]
        result = toggle("tog-1", "enabled", [10, 10, 20, 20], activebgoncolor=color)
        assert result["box"]["activebgoncolor"] == color

    def test_rounded_set(self):
        result = toggle("tog-1", "enabled", [10, 10, 20, 20], rounded=3.0)
        assert result["box"]["rounded"] == 3.0


class TestComment:
    """Test comment() creates correct live.comment label objects."""

    def test_returns_box_dict(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert "box" in result

    def test_maxclass_is_live_comment(self):
        """maxclass must be 'live.comment' for proper Live theme styling."""
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["maxclass"] == "live.comment"

    def test_text_is_set(self):
        result = comment("c-1", [0, 0, 100, 20], "My Label")
        assert result["box"]["text"] == "My Label"

    def test_default_textcolor_is_default_text_color(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["textcolor"] == list(DEFAULT_TEXT_COLOR)

    def test_custom_textcolor(self):
        color = [0.8, 0.2, 0.2, 1.0]
        result = comment("c-1", [0, 0, 100, 20], "Hello", textcolor=color)
        assert result["box"]["textcolor"] == color

    def test_default_fontsize(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["fontsize"] == 10.0

    def test_custom_fontsize(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello", fontsize=14.0)
        assert result["box"]["fontsize"] == 14.0

    def test_default_fontname(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["fontname"] == "Ableton Sans Medium"

    def test_custom_fontname(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello", fontname="Helvetica")
        assert result["box"]["fontname"] == "Helvetica"

    def test_textjustification_default_is_0(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["textjustification"] == 0

    def test_textjustification_custom(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello", justification=1)
        assert result["box"]["textjustification"] == 1

    def test_presentation_is_1(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 15, 120, 25]
        result = comment("c-1", rect, "Hello")
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_and_numoutlets(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 0

    def test_patching_rect_defaults_offscreen(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello")
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700

    def test_custom_patching_rect(self):
        custom = [300, 300, 100, 20]
        result = comment("c-1", [0, 0, 100, 20], "Hello", patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_kwargs_passthrough(self):
        result = comment("c-1", [0, 0, 100, 20], "Hello",
                          bubble=1)
        assert result["box"]["bubble"] == 1


class TestScope:
    """Test scope() creates correct live.scope~ display objects."""

    def test_returns_box_dict(self):
        result = scope("s-1", [0, 0, 200, 100])
        assert "box" in result

    def test_maxclass_is_live_scope(self):
        result = scope("s-1", [0, 0, 200, 100])
        assert result["box"]["maxclass"] == "live.scope~"

    def test_numinlets_is_2(self):
        result = scope("s-1", [0, 0, 200, 100])
        assert result["box"]["numinlets"] == 2

    def test_numoutlets_is_0(self):
        result = scope("s-1", [0, 0, 200, 100])
        assert result["box"]["numoutlets"] == 0

    def test_calccount_default_is_64(self):
        result = scope("s-1", [0, 0, 200, 100])
        assert result["box"]["calccount"] == 64

    def test_calccount_custom(self):
        result = scope("s-1", [0, 0, 200, 100], calccount=128)
        assert result["box"]["calccount"] == 128

    def test_presentation_is_1(self):
        result = scope("s-1", [0, 0, 200, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [20, 30, 200, 100]
        result = scope("s-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_optional_colors_omitted_by_default(self):
        result = scope("s-1", [0, 0, 200, 100])
        box = result["box"]
        assert "bgcolor" not in box
        assert "linecolor" not in box
        assert "gridcolor" not in box
        assert "range" not in box

    def test_bgcolor_set_when_provided(self):
        color = [0.0, 0.0, 0.0, 1.0]
        result = scope("s-1", [0, 0, 200, 100], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_linecolor_set_when_provided(self):
        color = [0.0, 1.0, 0.0, 1.0]
        result = scope("s-1", [0, 0, 200, 100], linecolor=color)
        assert result["box"]["linecolor"] == color

    def test_gridcolor_set_when_provided(self):
        color = [0.3, 0.3, 0.3, 1.0]
        result = scope("s-1", [0, 0, 200, 100], gridcolor=color)
        assert result["box"]["gridcolor"] == color

    def test_range_vals_set_as_range(self):
        result = scope("s-1", [0, 0, 200, 100], range_vals=[-1.0, 1.0])
        assert result["box"]["range"] == [-1.0, 1.0]

    def test_patching_rect_defaults_offscreen(self):
        result = scope("s-1", [0, 0, 200, 100])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 100

    def test_custom_patching_rect(self):
        custom = [400, 400, 200, 100]
        result = scope("s-1", [0, 0, 200, 100], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_kwargs_passthrough(self):
        result = scope("s-1", [0, 0, 200, 100], custom_scope_attr=42)
        assert result["box"]["custom_scope_attr"] == 42

    def test_smooth_set(self):
        result = scope("s-1", [0, 0, 200, 100], smooth=2)
        assert result["box"]["smooth"] == 2

    def test_line_width_set(self):
        result = scope("s-1", [0, 0, 200, 100], line_width=2.5)
        assert result["box"]["line_width"] == 2.5

    def test_mode_set(self):
        result = scope("s-1", [0, 0, 200, 100], mode="history")
        assert result["box"]["mode"] == "history"

    def test_activelinecolor_set(self):
        color = [0.5, 0.8, 0.3, 1.0]
        result = scope("s-1", [0, 0, 200, 100], activelinecolor=color)
        assert result["box"]["activelinecolor"] == color

    def test_decay_time_set(self):
        result = scope("s-1", [0, 0, 200, 100], decay_time=500)
        assert result["box"]["decay_time"] == 500


class TestPresentationBoxHelper:
    """Test _presentation_box helper behavior via public functions."""

    def test_patching_rect_uses_rect_dimensions_when_default(self):
        result = panel("p-1", [0, 0, 150, 75], bgcolor=[0.0, 0.0, 0.0, 1.0])
        pr = result["box"]["patching_rect"]
        assert pr[2] == 150
        assert pr[3] == 75

    def test_custom_patching_rect_overrides_default(self):
        custom = [10, 20, 150, 75]
        result = scope("s-1", [0, 0, 150, 75], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_id_is_stored(self):
        result = panel("my-id", [0, 0, 100, 50], bgcolor=[0.0, 0.0, 0.0, 1.0])
        assert result["box"]["id"] == "my-id"


class TestMeter:
    """Test meter() creates correct live.meter~ display objects."""

    def test_returns_box_dict(self):
        result = meter("m-1", [0, 0, 20, 100])
        assert "box" in result

    def test_maxclass_is_live_meter(self):
        result = meter("m-1", [0, 0, 20, 100])
        assert result["box"]["maxclass"] == "live.meter~"

    def test_numinlets_is_1(self):
        result = meter("m-1", [0, 0, 20, 100])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_1(self):
        result = meter("m-1", [0, 0, 20, 100])
        assert result["box"]["numoutlets"] == 1

    def test_orientation_default_is_0(self):
        result = meter("m-1", [0, 0, 20, 100])
        assert result["box"]["orientation"] == 0

    def test_custom_orientation(self):
        result = meter("m-1", [0, 0, 100, 20], orientation=1)
        assert result["box"]["orientation"] == 1

    def test_presentation_is_1(self):
        result = meter("m-1", [0, 0, 20, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 20, 100]
        result = meter("m-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_patching_rect_defaults(self):
        result = meter("m-1", [0, 0, 20, 100])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 20
        assert pr[3] == 100

    def test_kwargs_passthrough(self):
        result = meter("m-1", [0, 0, 20, 100], custom_meter=True)
        assert result["box"]["custom_meter"] is True

    def test_coldcolor_set(self):
        color = [0.0, 0.5, 0.0, 1.0]
        result = meter("m-1", [0, 0, 20, 100], coldcolor=color)
        assert result["box"]["coldcolor"] == color

    def test_warmcolor_set(self):
        color = [0.8, 0.8, 0.0, 1.0]
        result = meter("m-1", [0, 0, 20, 100], warmcolor=color)
        assert result["box"]["warmcolor"] == color

    def test_hotcolor_set(self):
        color = [1.0, 0.4, 0.0, 1.0]
        result = meter("m-1", [0, 0, 20, 100], hotcolor=color)
        assert result["box"]["hotcolor"] == color

    def test_overloadcolor_set(self):
        color = [1.0, 0.0, 0.0, 1.0]
        result = meter("m-1", [0, 0, 20, 100], overloadcolor=color)
        assert result["box"]["overloadcolor"] == color


class TestMenu:
    """Test menu() creates correct live.menu dropdown objects."""

    def test_returns_box_dict(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["sine", "saw", "square"])
        assert "box" in result

    def test_maxclass_is_live_menu(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["sine", "saw"])
        assert result["box"]["maxclass"] == "live.menu"

    def test_numinlets_is_1(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_3(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        assert result["box"]["numoutlets"] == 3

    def test_parameter_enable_is_1(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        assert result["box"]["parameter_enable"] == 1

    def test_parameter_type_is_2(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 2

    def test_parameter_enum_is_list(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["sine", "saw", "square"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == ["sine", "saw", "square"]

    def test_parameter_mmax_matches_last_option_index(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B", "C"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == 0
        assert valueof["parameter_mmax"] == 2
        assert valueof["parameter_initial"] == [0]

    def test_saved_attribute_attributes_present(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        assert "saved_attribute_attributes" in result["box"]
        assert "valueof" in result["box"]["saved_attribute_attributes"]

    def test_shortname_defaults_to_varname(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "waveform"

    def test_shortname_custom(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"], shortname="Wave")
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "Wave"

    def test_presentation_is_1(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 10, 100, 20]
        result = menu("mn-1", "waveform", rect, options=["A", "B"])
        assert result["box"]["presentation_rect"] == rect

    def test_kwargs_passthrough(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["A", "B"],
                       custom_menu_key=99)
        assert result["box"]["custom_menu_key"] == 99


class TestNumberBox:
    """Test number_box() creates correct live.numbox objects."""

    def test_returns_box_dict(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        assert "box" in result

    def test_maxclass_is_live_numbox(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        assert result["box"]["maxclass"] == "live.numbox"

    def test_numinlets_is_1(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_2(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        assert result["box"]["numoutlets"] == 2

    def test_parameter_enable_is_1(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        assert result["box"]["parameter_enable"] == 1

    def test_parameter_initial_enable_is_1(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_initial_enable"] == 1

    def test_parameter_initial_is_list(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20], initial=64.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert isinstance(valueof["parameter_initial"], list)
        assert valueof["parameter_initial"] == [64.0]

    def test_min_max_vals(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20], min_val=0.0, max_val=127.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == 0.0
        assert valueof["parameter_mmax"] == 127.0

    def test_unitstyle_default_is_1(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_unitstyle"] == 1

    def test_presentation_is_1(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 50, 20]
        result = number_box("nb-1", "velocity", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_kwargs_passthrough(self):
        result = number_box("nb-1", "velocity", [0, 0, 50, 20],
                             textcolor=[1, 0, 0, 1])
        assert result["box"]["textcolor"] == [1, 0, 0, 1]


class TestSlider:
    """Test slider() creates correct live.slider parameter objects."""

    def test_returns_box_dict(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert "box" in result

    def test_maxclass_is_live_slider(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert result["box"]["maxclass"] == "live.slider"

    def test_varname_is_set(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert result["box"]["varname"] == "mix"

    def test_parameter_enable_is_1(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert result["box"]["parameter_enable"] == 1

    def test_numinlets_and_numoutlets(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 2

    def test_presentation_is_1(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 20, 100]
        result = slider("sl-1", "mix", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_default_min_max(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == 0.0
        assert valueof["parameter_mmax"] == 1.0

    def test_custom_min_max(self):
        result = slider("sl-1", "gain", [10, 10, 20, 100], min_val=-60.0, max_val=6.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == -60.0
        assert valueof["parameter_mmax"] == 6.0

    def test_default_initial(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_initial"] == [0.5]

    def test_custom_initial(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100], initial=0.0)
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_initial"] == [0.0]

    def test_parameter_initial_enable_is_1(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_initial_enable"] == 1

    def test_parameter_longname_is_varname(self):
        result = slider("sl-1", "depth", [10, 10, 20, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == "depth"

    def test_shortname_defaults_to_varname(self):
        result = slider("sl-1", "depth", [10, 10, 20, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "depth"

    def test_shortname_custom(self):
        result = slider("sl-1", "depth", [10, 10, 20, 100], shortname="Depth")
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "Depth"

    def test_unitstyle_default_is_1(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_unitstyle"] == 1

    def test_orientation_default_is_0(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert result["box"]["orientation"] == 0

    def test_orientation_horizontal(self):
        result = slider("sl-1", "mix", [10, 10, 100, 20], orientation=1)
        assert result["box"]["orientation"] == 1

    def test_patching_rect_defaults_offscreen(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 20
        assert pr[3] == 100

    def test_custom_patching_rect(self):
        custom = [50, 50, 20, 100]
        result = slider("sl-1", "mix", [10, 10, 20, 100], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_saved_attribute_attributes_present(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100])
        assert "saved_attribute_attributes" in result["box"]
        assert "valueof" in result["box"]["saved_attribute_attributes"]

    def test_kwargs_passthrough(self):
        result = slider("sl-1", "mix", [10, 10, 20, 100],
                         slidercolor=[0.5, 0.8, 0.2, 1.0])
        assert result["box"]["slidercolor"] == [0.5, 0.8, 0.2, 1.0]


class TestButton:
    """Test button() creates correct live.button objects."""

    def test_returns_box_dict(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert "box" in result

    def test_maxclass_is_live_button(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert result["box"]["maxclass"] == "live.button"

    def test_varname_is_set(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert result["box"]["varname"] == "trigger"

    def test_parameter_enable_is_1(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert result["box"]["parameter_enable"] == 1

    def test_numinlets_is_1(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_1(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert result["box"]["numoutlets"] == 1

    def test_presentation_is_1(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [15, 25, 24, 24]
        result = button("btn-1", "trigger", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_parameter_type_is_2(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 2

    def test_parameter_enum_is_off_on(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == ["off", "on"]

    def test_shortname_defaults_to_varname(self):
        result = button("btn-1", "fire", [10, 10, 24, 24])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "fire"

    def test_shortname_custom(self):
        result = button("btn-1", "fire", [10, 10, 24, 24], shortname="Fire!")
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "Fire!"

    def test_patching_rect_defaults_offscreen(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 24
        assert pr[3] == 24

    def test_custom_patching_rect(self):
        custom = [200, 200, 24, 24]
        result = button("btn-1", "trigger", [10, 10, 24, 24], patching_rect=custom)
        assert result["box"]["patching_rect"] == custom

    def test_saved_attribute_attributes_present(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24])
        assert "saved_attribute_attributes" in result["box"]
        assert "valueof" in result["box"]["saved_attribute_attributes"]

    def test_kwargs_passthrough(self):
        result = button("btn-1", "trigger", [10, 10, 24, 24],
                         bgcolor=[0.3, 0.3, 0.3, 1.0])
        assert result["box"]["bgcolor"] == [0.3, 0.3, 0.3, 1.0]


class TestLiveText:
    """Test live_text() creates correct live.text objects."""

    def test_returns_box_dict(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert "box" in result

    def test_maxclass_is_live_text(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["maxclass"] == "live.text"

    def test_varname_is_set(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["varname"] == "bypass"

    def test_default_text_on_off(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["text"] == "OFF"
        assert result["box"]["texton"] == "ON"

    def test_custom_text_on_off(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20],
                            text_on="ACTIVE", text_off="BYPASS")
        assert result["box"]["text"] == "BYPASS"
        assert result["box"]["texton"] == "ACTIVE"

    def test_parameter_enable_is_1(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["parameter_enable"] == 1

    def test_numinlets_and_numoutlets(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 2

    def test_mode_default_is_0(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["mode"] == 0

    def test_mode_button(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20], mode=1)
        assert result["box"]["mode"] == 1

    def test_default_fontname(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["fontname"] == "Ableton Sans Medium"

    def test_bgcolor_set(self):
        color = [0.2, 0.2, 0.2, 1.0]
        result = live_text("lt-1", "bypass", [0, 0, 60, 20], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_bgoncolor_set(self):
        color = [0.8, 0.4, 0.1, 1.0]
        result = live_text("lt-1", "bypass", [0, 0, 60, 20], bgoncolor=color)
        assert result["box"]["bgoncolor"] == color

    def test_rounded_set(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20], rounded=4.0)
        assert result["box"]["rounded"] == 4.0

    def test_presentation_is_1(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20])
        assert result["box"]["presentation"] == 1

    def test_parameter_enum_uses_text(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20],
                            text_on="ACTIVE", text_off="BYPASS")
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == ["BYPASS", "ACTIVE"]

    def test_kwargs_passthrough(self):
        result = live_text("lt-1", "bypass", [0, 0, 60, 20], custom=42)
        assert result["box"]["custom"] == 42


class TestFpic:
    """Test fpic() creates correct image display objects."""

    def test_returns_box_dict(self):
        result = fpic("fp-1", [0, 0, 100, 100])
        assert "box" in result

    def test_maxclass_is_fpic(self):
        result = fpic("fp-1", [0, 0, 100, 100])
        assert result["box"]["maxclass"] == "fpic"

    def test_default_pic_is_empty(self):
        result = fpic("fp-1", [0, 0, 100, 100])
        assert result["box"]["pic"] == ""

    def test_custom_pic(self):
        result = fpic("fp-1", [0, 0, 100, 100], pic="logo.png")
        assert result["box"]["pic"] == "logo.png"

    def test_autofit_default_is_1(self):
        result = fpic("fp-1", [0, 0, 100, 100])
        assert result["box"]["autofit"] == 1

    def test_numinlets_and_numoutlets(self):
        result = fpic("fp-1", [0, 0, 100, 100])
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 1

    def test_presentation_is_1(self):
        result = fpic("fp-1", [0, 0, 100, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 100, 100]
        result = fpic("fp-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_kwargs_passthrough(self):
        result = fpic("fp-1", [0, 0, 100, 100], border=2)
        assert result["box"]["border"] == 2


class TestLiveGain:
    """Test live_gain() creates correct live.gain~ objects."""

    def test_returns_box_dict(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert "box" in result

    def test_maxclass_is_live_gain(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["maxclass"] == "live.gain~"

    def test_varname_is_set(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["varname"] == "output"

    def test_numinlets_is_2(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["numinlets"] == 2

    def test_numoutlets_is_5(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["numoutlets"] == 5

    def test_parameter_enable_is_1(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["parameter_enable"] == 1

    def test_default_min_max(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_mmin"] == -70.0
        assert valueof["parameter_mmax"] == 6.0

    def test_default_initial(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_initial"] == [0.0]

    def test_unitstyle_is_db(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_unitstyle"] == 4

    def test_orientation_default_is_0(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["orientation"] == 0

    def test_presentation_is_1(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100])
        assert result["box"]["presentation"] == 1

    def test_kwargs_passthrough(self):
        result = live_gain("lg-1", "output", [0, 0, 30, 100], custom_gain=True)
        assert result["box"]["custom_gain"] is True


class TestMultislider:
    """Test multislider() creates correct multislider objects."""

    def test_returns_box_dict(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert "box" in result

    def test_maxclass_is_multislider(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["maxclass"] == "multislider"

    def test_default_size_is_16(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["size"] == 16

    def test_custom_size(self):
        result = multislider("ms-1", [0, 0, 100, 50], size=8)
        assert result["box"]["size"] == 8

    def test_default_setminmax(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["setminmax"] == [0.0, 1.0]

    def test_custom_setminmax(self):
        result = multislider("ms-1", [0, 0, 100, 50], setminmax=[-1.0, 1.0])
        assert result["box"]["setminmax"] == [-1.0, 1.0]

    def test_numinlets_is_2(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["numinlets"] == 2

    def test_numoutlets_is_2(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["numoutlets"] == 2

    def test_setstyle_default_is_0(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["setstyle"] == 0

    def test_setstyle_line(self):
        result = multislider("ms-1", [0, 0, 100, 50], setstyle=1)
        assert result["box"]["setstyle"] == 1

    def test_slidercolor_set(self):
        color = [0.5, 0.8, 0.2, 1.0]
        result = multislider("ms-1", [0, 0, 100, 50], slidercolor=color)
        assert result["box"]["slidercolor"] == color

    def test_presentation_is_1(self):
        result = multislider("ms-1", [0, 0, 100, 50])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 100, 50]
        result = multislider("ms-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_kwargs_passthrough(self):
        result = multislider("ms-1", [0, 0, 100, 50], custom_ms=True)
        assert result["box"]["custom_ms"] is True


class TestJsui:
    """Tests for jsui() UI function."""

    def test_maxclass_is_jsui(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js")
        assert result["box"]["maxclass"] == "jsui"

    def test_filename_set(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="my_engine.js")
        assert result["box"]["filename"] == "my_engine.js"

    def test_presentation_mode(self):
        result = jsui("test", [10, 20, 200, 80], js_filename="test.js")
        assert result["box"]["presentation"] == 1
        assert result["box"]["presentation_rect"] == [10, 20, 200, 80]

    def test_default_inlets_outlets(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js")
        assert result["box"]["numinlets"] == 1
        assert result["box"]["numoutlets"] == 0

    def test_custom_inlets_outlets(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js",
                      numinlets=3, numoutlets=2)
        assert result["box"]["numinlets"] == 3
        assert result["box"]["numoutlets"] == 2

    def test_outlettype_auto_generated(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js",
                      numoutlets=3)
        assert result["box"]["outlettype"] == ["", "", ""]

    def test_outlettype_empty_when_no_outlets(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js",
                      numoutlets=0)
        assert result["box"]["outlettype"] == []

    def test_returns_box_dict(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js")
        assert "box" in result

    def test_id_set(self):
        result = jsui("my_display", [0, 0, 200, 80], js_filename="test.js")
        assert result["box"]["id"] == "my_display"

    def test_kwargs_passthrough(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js",
                      custom_attr="value")
        assert result["box"]["custom_attr"] == "value"

    def test_patching_rect_default(self):
        """patching_rect defaults based on rect dimensions."""
        result = jsui("test", [10, 20, 200, 80], js_filename="test.js")
        pr = result["box"]["patching_rect"]
        # Width and height should match rect[2] and rect[3]
        assert pr[2] == 200
        assert pr[3] == 80

    def test_patching_rect_override(self):
        result = jsui("test", [0, 0, 200, 80], js_filename="test.js",
                      patching_rect=[50, 50, 100, 40])
        assert result["box"]["patching_rect"] == [50, 50, 100, 40]


class TestV8ui:
    """Tests for v8ui() UI function."""

    def test_maxclass_is_v8ui(self):
        result = v8ui("test", [0, 0, 200, 80], js_filename="test.js")
        assert result["box"]["maxclass"] == "v8ui"

    def test_filename_set(self):
        result = v8ui("test", [0, 0, 200, 80], js_filename="my_engine.js")
        assert result["box"]["filename"] == "my_engine.js"

    def test_textfile_metadata_set(self):
        result = v8ui("test", [0, 0, 200, 80], js_filename="engine.js")
        assert result["box"]["textfile"]["filename"] == "engine.js"
        assert result["box"]["textfile"]["autowatch"] == 1

    def test_presentation_mode(self):
        result = v8ui("test", [10, 20, 200, 80], js_filename="test.js")
        assert result["box"]["presentation"] == 1
        assert result["box"]["presentation_rect"] == [10, 20, 200, 80]


class TestAdsrui:
    """Tests for adsrui() ADSR envelope editor."""

    def test_returns_box_dict(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert "box" in result

    def test_maxclass_is_live_adsrui(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert result["box"]["maxclass"] == "live.adsrui"

    def test_id_set(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert result["box"]["id"] == "adsr-1"

    def test_presentation_is_1(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 200, 80]
        result = adsrui("adsr-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_4(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert result["box"]["numoutlets"] == 4

    def test_outlettype_has_4_floats(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert result["box"]["outlettype"] == ["float", "float", "float", "float"]

    def test_patching_rect_defaults_offscreen(self):
        result = adsrui("adsr-1", [10, 20, 200, 80])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 80

    def test_patching_rect_override(self):
        result = adsrui("adsr-1", [0, 0, 200, 80], patching_rect=[50, 50, 200, 80])
        assert result["box"]["patching_rect"] == [50, 50, 200, 80]

    def test_bgcolor_not_set_by_default(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert "bgcolor" not in result["box"]

    def test_bgcolor_set_when_provided(self):
        color = [0.1, 0.1, 0.1, 1.0]
        result = adsrui("adsr-1", [0, 0, 200, 80], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_bordercolor_not_set_by_default(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert "bordercolor" not in result["box"]

    def test_bordercolor_set_when_provided(self):
        color = [0.5, 0.5, 0.5, 1.0]
        result = adsrui("adsr-1", [0, 0, 200, 80], bordercolor=color)
        assert result["box"]["bordercolor"] == color

    def test_focusbordercolor_not_set_by_default(self):
        result = adsrui("adsr-1", [0, 0, 200, 80])
        assert "focusbordercolor" not in result["box"]

    def test_focusbordercolor_set_when_provided(self):
        color = [0.8, 0.2, 0.8, 1.0]
        result = adsrui("adsr-1", [0, 0, 200, 80], focusbordercolor=color)
        assert result["box"]["focusbordercolor"] == color

    def test_kwargs_passthrough(self):
        result = adsrui("adsr-1", [0, 0, 200, 80], custom_attr="test")
        assert result["box"]["custom_attr"] == "test"


class TestLiveDrop:
    """Tests for live_drop() drag-and-drop file target."""

    def test_returns_box_dict(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert "box" in result

    def test_maxclass_is_live_drop(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert result["box"]["maxclass"] == "live.drop"

    def test_id_set(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert result["box"]["id"] == "drop-1"

    def test_presentation_is_1(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 10, 100, 30]
        result = live_drop("drop-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_1(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert result["box"]["numoutlets"] == 1

    def test_outlettype_is_single_string(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert result["box"]["outlettype"] == [""]

    def test_patching_rect_defaults_offscreen(self):
        result = live_drop("drop-1", [10, 20, 100, 30])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 100
        assert pr[3] == 30

    def test_patching_rect_override(self):
        result = live_drop("drop-1", [0, 0, 100, 30], patching_rect=[50, 50, 100, 30])
        assert result["box"]["patching_rect"] == [50, 50, 100, 30]

    def test_textcolor_not_set_by_default(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert "textcolor" not in result["box"]

    def test_textcolor_set_when_provided(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = live_drop("drop-1", [0, 0, 100, 30], textcolor=color)
        assert result["box"]["textcolor"] == color

    def test_bgcolor_not_set_by_default(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert "bgcolor" not in result["box"]

    def test_bgcolor_set_when_provided(self):
        color = [0.2, 0.2, 0.2, 1.0]
        result = live_drop("drop-1", [0, 0, 100, 30], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_bordercolor_not_set_by_default(self):
        result = live_drop("drop-1", [0, 0, 100, 30])
        assert "bordercolor" not in result["box"]

    def test_bordercolor_set_when_provided(self):
        color = [0.4, 0.4, 0.4, 1.0]
        result = live_drop("drop-1", [0, 0, 100, 30], bordercolor=color)
        assert result["box"]["bordercolor"] == color

    def test_kwargs_passthrough(self):
        result = live_drop("drop-1", [0, 0, 100, 30], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestBpatcher:
    """Tests for bpatcher() embeddable sub-patcher."""

    def test_returns_box_dict(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert "box" in result

    def test_maxclass_is_bpatcher(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["maxclass"] == "bpatcher"

    def test_id_set(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["id"] == "bp-1"

    def test_name_is_patcher_name(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["name"] == "my_patch.maxpat"

    def test_presentation_is_1(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 200, 100]
        result = bpatcher("bp-1", rect, "my_patch.maxpat")
        assert result["box"]["presentation_rect"] == rect

    def test_embed_default_is_1(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["embed"] == 1

    def test_embed_custom(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat", embed=0)
        assert result["box"]["embed"] == 0

    def test_numinlets_is_0(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["numinlets"] == 0

    def test_numoutlets_is_0(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert result["box"]["numoutlets"] == 0

    def test_patching_rect_defaults_offscreen(self):
        result = bpatcher("bp-1", [10, 20, 200, 100], "my_patch.maxpat")
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 100

    def test_patching_rect_override(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat",
                          patching_rect=[50, 50, 200, 100])
        assert result["box"]["patching_rect"] == [50, 50, 200, 100]

    def test_args_not_set_by_default(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat")
        assert "args" not in result["box"]

    def test_args_set_when_provided(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat", args="1 2 3")
        assert result["box"]["args"] == "1 2 3"

    def test_kwargs_passthrough(self):
        result = bpatcher("bp-1", [0, 0, 200, 100], "my_patch.maxpat", custom_attr=42)
        assert result["box"]["custom_attr"] == 42


class TestSwatch:
    """Tests for swatch() color picker/display."""

    def test_returns_box_dict(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert "box" in result

    def test_maxclass_is_swatch(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert result["box"]["maxclass"] == "swatch"

    def test_id_set(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert result["box"]["id"] == "sw-1"

    def test_presentation_is_1(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 10, 40, 20]
        result = swatch("sw-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_4(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert result["box"]["numoutlets"] == 4

    def test_outlettype_has_4_entries(self):
        result = swatch("sw-1", [0, 0, 40, 20])
        assert result["box"]["outlettype"] == ["", "", "", ""]

    def test_patching_rect_defaults_offscreen(self):
        result = swatch("sw-1", [10, 20, 40, 20])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 40
        assert pr[3] == 20

    def test_patching_rect_override(self):
        result = swatch("sw-1", [0, 0, 40, 20], patching_rect=[50, 50, 40, 20])
        assert result["box"]["patching_rect"] == [50, 50, 40, 20]

    def test_kwargs_passthrough(self):
        result = swatch("sw-1", [0, 0, 40, 20], color=[1.0, 0.0, 0.0, 1.0])
        assert result["box"]["color"] == [1.0, 0.0, 0.0, 1.0]


class TestTextedit:
    """Tests for textedit() editable text field."""

    def test_returns_box_dict(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert "box" in result

    def test_maxclass_is_textedit(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["maxclass"] == "textedit"

    def test_id_set(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["id"] == "te-1"

    def test_presentation_is_1(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 150, 25]
        result = textedit("te-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_4(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["numoutlets"] == 4

    def test_outlettype_correct(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["outlettype"] == ["", "", "", "int"]

    def test_fontname_default(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["fontname"] == "Ableton Sans Medium"

    def test_fontname_custom(self):
        result = textedit("te-1", [0, 0, 150, 25], fontname="Arial")
        assert result["box"]["fontname"] == "Arial"

    def test_fontsize_default(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert result["box"]["fontsize"] == 10.0

    def test_fontsize_custom(self):
        result = textedit("te-1", [0, 0, 150, 25], fontsize=14.0)
        assert result["box"]["fontsize"] == 14.0

    def test_patching_rect_defaults_offscreen(self):
        result = textedit("te-1", [10, 20, 150, 25])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 150
        assert pr[3] == 25

    def test_patching_rect_override(self):
        result = textedit("te-1", [0, 0, 150, 25], patching_rect=[50, 50, 150, 25])
        assert result["box"]["patching_rect"] == [50, 50, 150, 25]

    def test_textcolor_not_set_by_default(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert "textcolor" not in result["box"]

    def test_textcolor_set_when_provided(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = textedit("te-1", [0, 0, 150, 25], textcolor=color)
        assert result["box"]["textcolor"] == color

    def test_bgcolor_not_set_by_default(self):
        result = textedit("te-1", [0, 0, 150, 25])
        assert "bgcolor" not in result["box"]

    def test_bgcolor_set_when_provided(self):
        color = [0.1, 0.1, 0.1, 1.0]
        result = textedit("te-1", [0, 0, 150, 25], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_kwargs_passthrough(self):
        result = textedit("te-1", [0, 0, 150, 25], custom_attr="hello")
        assert result["box"]["custom_attr"] == "hello"


class TestLiveStep:
    """Tests for live_step() step sequencer UI."""

    def test_returns_box_dict(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert "box" in result

    def test_maxclass_is_live_step(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["maxclass"] == "live.step"

    def test_id_set(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["id"] == "ls-1"

    def test_presentation_is_1(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 300, 100]
        result = live_step("ls-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_5(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["numoutlets"] == 5

    def test_outlettype_has_5_entries(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["outlettype"] == ["", "", "", "", ""]

    def test_nstep_default(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["nstep"] == 16

    def test_nstep_custom(self):
        result = live_step("ls-1", [0, 0, 300, 100], nstep=32)
        assert result["box"]["nstep"] == 32

    def test_nseq_default(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert result["box"]["nseq"] == 1

    def test_nseq_custom(self):
        result = live_step("ls-1", [0, 0, 300, 100], nseq=4)
        assert result["box"]["nseq"] == 4

    def test_loop_start_not_set_by_default(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert "loop_start" not in result["box"]

    def test_loop_start_set_when_provided(self):
        result = live_step("ls-1", [0, 0, 300, 100], loop_start=4)
        assert result["box"]["loop_start"] == 4

    def test_loop_end_not_set_by_default(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert "loop_end" not in result["box"]

    def test_loop_end_set_when_provided(self):
        result = live_step("ls-1", [0, 0, 300, 100], loop_end=12)
        assert result["box"]["loop_end"] == 12

    def test_mode_not_set_by_default(self):
        result = live_step("ls-1", [0, 0, 300, 100])
        assert "mode" not in result["box"]

    def test_mode_set_when_provided(self):
        result = live_step("ls-1", [0, 0, 300, 100], mode=1)
        assert result["box"]["mode"] == 1

    def test_patching_rect_defaults_offscreen(self):
        result = live_step("ls-1", [10, 20, 300, 100])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 300
        assert pr[3] == 100

    def test_patching_rect_override(self):
        result = live_step("ls-1", [0, 0, 300, 100], patching_rect=[50, 50, 300, 100])
        assert result["box"]["patching_rect"] == [50, 50, 300, 100]

    def test_kwargs_passthrough(self):
        result = live_step("ls-1", [0, 0, 300, 100], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestLiveGrid:
    """Tests for live_grid() toggleable cell grid."""

    def test_returns_box_dict(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert "box" in result

    def test_maxclass_is_live_grid(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["maxclass"] == "live.grid"

    def test_id_set(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["id"] == "lg-1"

    def test_presentation_is_1(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 200, 100]
        result = live_grid("lg-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_4(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["numoutlets"] == 4

    def test_outlettype_has_4_entries(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["outlettype"] == ["", "", "", ""]

    def test_columns_default(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["columns"] == 16

    def test_columns_custom(self):
        result = live_grid("lg-1", [0, 0, 200, 100], columns=8)
        assert result["box"]["columns"] == 8

    def test_rows_default(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert result["box"]["rows"] == 8

    def test_rows_custom(self):
        result = live_grid("lg-1", [0, 0, 200, 100], rows=4)
        assert result["box"]["rows"] == 4

    def test_direction_not_set_by_default(self):
        result = live_grid("lg-1", [0, 0, 200, 100])
        assert "direction" not in result["box"]

    def test_direction_set_when_provided(self):
        result = live_grid("lg-1", [0, 0, 200, 100], direction=0)
        assert result["box"]["direction"] == 0

    def test_patching_rect_defaults_offscreen(self):
        result = live_grid("lg-1", [10, 20, 200, 100])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 100

    def test_patching_rect_override(self):
        result = live_grid("lg-1", [0, 0, 200, 100], patching_rect=[50, 50, 200, 100])
        assert result["box"]["patching_rect"] == [50, 50, 200, 100]

    def test_kwargs_passthrough(self):
        result = live_grid("lg-1", [0, 0, 200, 100], custom_attr=42)
        assert result["box"]["custom_attr"] == 42


class TestLiveLine:
    """Tests for live_line() visual divider."""

    def test_returns_box_dict(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert "box" in result

    def test_maxclass_is_live_line(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["maxclass"] == "live.line"

    def test_id_set(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["id"] == "ll-1"

    def test_presentation_is_1(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 80, 200, 2]
        result = live_line("ll-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_0(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["numoutlets"] == 0

    def test_outlettype_is_empty(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["outlettype"] == []

    def test_justification_default_is_0(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert result["box"]["justification"] == 0

    def test_justification_vertical(self):
        result = live_line("ll-1", [0, 0, 2, 100], justification=1)
        assert result["box"]["justification"] == 1

    def test_linecolor_not_set_by_default(self):
        result = live_line("ll-1", [0, 0, 200, 2])
        assert "linecolor" not in result["box"]

    def test_linecolor_set_when_provided(self):
        color = [0.5, 0.5, 0.5, 1.0]
        result = live_line("ll-1", [0, 0, 200, 2], linecolor=color)
        assert result["box"]["linecolor"] == color

    def test_patching_rect_defaults_offscreen(self):
        result = live_line("ll-1", [10, 20, 200, 2])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 2

    def test_patching_rect_override(self):
        result = live_line("ll-1", [0, 0, 200, 2], patching_rect=[50, 50, 200, 2])
        assert result["box"]["patching_rect"] == [50, 50, 200, 2]

    def test_kwargs_passthrough(self):
        result = live_line("ll-1", [0, 0, 200, 2], custom_attr="test")
        assert result["box"]["custom_attr"] == "test"


class TestLiveArrows:
    """Tests for live_arrows() direction arrow buttons."""

    def test_returns_box_dict(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert "box" in result

    def test_maxclass_is_live_arrows(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert result["box"]["maxclass"] == "live.arrows"

    def test_id_set(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert result["box"]["id"] == "la-1"

    def test_presentation_is_1(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [5, 10, 40, 20]
        result = live_arrows("la-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_1(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert result["box"]["numoutlets"] == 1

    def test_outlettype_is_single_string(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert result["box"]["outlettype"] == [""]

    def test_arrowcolor_not_set_by_default(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert "arrowcolor" not in result["box"]

    def test_arrowcolor_set_when_provided(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = live_arrows("la-1", [0, 0, 40, 20], arrowcolor=color)
        assert result["box"]["arrowcolor"] == color

    def test_arrowbgcolor_not_set_by_default(self):
        result = live_arrows("la-1", [0, 0, 40, 20])
        assert "arrowbgcolor" not in result["box"]

    def test_arrowbgcolor_set_when_provided(self):
        color = [0.2, 0.2, 0.2, 1.0]
        result = live_arrows("la-1", [0, 0, 40, 20], arrowbgcolor=color)
        assert result["box"]["arrowbgcolor"] == color

    def test_patching_rect_defaults_offscreen(self):
        result = live_arrows("la-1", [10, 20, 40, 20])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 40
        assert pr[3] == 20

    def test_patching_rect_override(self):
        result = live_arrows("la-1", [0, 0, 40, 20], patching_rect=[50, 50, 40, 20])
        assert result["box"]["patching_rect"] == [50, 50, 40, 20]

    def test_kwargs_passthrough(self):
        result = live_arrows("la-1", [0, 0, 40, 20], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestRslider:
    """Tests for rslider() range slider."""

    def test_returns_box_dict(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert "box" in result

    def test_maxclass_is_rslider(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["maxclass"] == "rslider"

    def test_id_set(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["id"] == "rs-1"

    def test_presentation_is_1(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 20, 140]
        result = rslider("rs-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_2(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["numinlets"] == 2

    def test_numoutlets_is_2(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["numoutlets"] == 2

    def test_outlettype(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["outlettype"] == ["", ""]

    def test_min_default(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["min"] == 0

    def test_max_default(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["max"] == 127

    def test_min_custom(self):
        result = rslider("rs-1", [0, 0, 20, 140], min_val=10)
        assert result["box"]["min"] == 10

    def test_max_custom(self):
        result = rslider("rs-1", [0, 0, 20, 140], max_val=200)
        assert result["box"]["max"] == 200

    def test_bgcolor_not_set_by_default(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert "bgcolor" not in result["box"]

    def test_bgcolor_set_when_provided(self):
        color = [0.2, 0.2, 0.2, 1.0]
        result = rslider("rs-1", [0, 0, 20, 140], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_fgcolor_not_set_by_default(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert "fgcolor" not in result["box"]

    def test_fgcolor_set_when_provided(self):
        color = [0.8, 0.4, 0.1, 1.0]
        result = rslider("rs-1", [0, 0, 20, 140], fgcolor=color)
        assert result["box"]["fgcolor"] == color

    def test_patching_rect_default(self):
        result = rslider("rs-1", [0, 0, 20, 140])
        assert result["box"]["patching_rect"] == [0, 0, 20, 140]

    def test_patching_rect_override(self):
        result = rslider("rs-1", [0, 0, 20, 140], patching_rect=[50, 50, 20, 140])
        assert result["box"]["patching_rect"] == [50, 50, 20, 140]

    def test_kwargs_passthrough(self):
        result = rslider("rs-1", [0, 0, 20, 140], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestKslider:
    """Tests for kslider() piano keyboard display."""

    def test_returns_box_dict(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert "box" in result

    def test_maxclass_is_kslider(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["maxclass"] == "kslider"

    def test_id_set(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["id"] == "ks-1"

    def test_presentation_is_1(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 300, 50]
        result = kslider("ks-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_2(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["numinlets"] == 2

    def test_numoutlets_is_2(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["numoutlets"] == 2

    def test_outlettype(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["outlettype"] == ["", ""]

    def test_range_default(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["range"] == 61

    def test_range_custom(self):
        result = kslider("ks-1", [0, 0, 300, 50], range=25)
        assert result["box"]["range"] == 25

    def test_offset_default(self):
        result = kslider("ks-1", [0, 0, 300, 50])
        assert result["box"]["offset"] == 36

    def test_offset_custom(self):
        result = kslider("ks-1", [0, 0, 300, 50], offset=48)
        assert result["box"]["offset"] == 48

    def test_patching_rect_defaults_offscreen(self):
        result = kslider("ks-1", [10, 20, 300, 50])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 300
        assert pr[3] == 50

    def test_patching_rect_override(self):
        result = kslider("ks-1", [0, 0, 300, 50], patching_rect=[50, 50, 300, 50])
        assert result["box"]["patching_rect"] == [50, 50, 300, 50]

    def test_kwargs_passthrough(self):
        result = kslider("ks-1", [0, 0, 300, 50], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestTextbutton:
    """Tests for textbutton() text button."""

    def test_returns_box_dict(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert "box" in result

    def test_maxclass_is_textbutton(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["maxclass"] == "textbutton"

    def test_id_set(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["id"] == "tb-1"

    def test_presentation_is_1(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 80, 24]
        result = textbutton("tb-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_3(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["numoutlets"] == 3

    def test_outlettype(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["outlettype"] == ["", "", "int"]

    def test_text_default(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["text"] == "Button"

    def test_text_custom(self):
        result = textbutton("tb-1", [0, 0, 80, 24], "Play")
        assert result["box"]["text"] == "Play"

    def test_mode_default_is_0(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert result["box"]["mode"] == 0

    def test_mode_toggle(self):
        result = textbutton("tb-1", [0, 0, 80, 24], mode=1)
        assert result["box"]["mode"] == 1

    def test_texton_not_set_by_default(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert "texton" not in result["box"]

    def test_texton_set_when_provided(self):
        result = textbutton("tb-1", [0, 0, 80, 24], texton="ON")
        assert result["box"]["texton"] == "ON"

    def test_textoff_not_set_by_default(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert "textoff" not in result["box"]

    def test_textoff_set_when_provided(self):
        result = textbutton("tb-1", [0, 0, 80, 24], textoff="OFF")
        assert result["box"]["textoff"] == "OFF"

    def test_fontsize_not_set_by_default(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert "fontsize" not in result["box"]

    def test_fontsize_set_when_provided(self):
        result = textbutton("tb-1", [0, 0, 80, 24], fontsize=12.0)
        assert result["box"]["fontsize"] == 12.0

    def test_bgcolor_not_set_by_default(self):
        result = textbutton("tb-1", [0, 0, 80, 24])
        assert "bgcolor" not in result["box"]

    def test_bgcolor_set_when_provided(self):
        color = [0.3, 0.3, 0.3, 1.0]
        result = textbutton("tb-1", [0, 0, 80, 24], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_bgoncolor_set_when_provided(self):
        color = [0.8, 0.2, 0.1, 1.0]
        result = textbutton("tb-1", [0, 0, 80, 24], bgoncolor=color)
        assert result["box"]["bgoncolor"] == color

    def test_textcolor_set_when_provided(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = textbutton("tb-1", [0, 0, 80, 24], textcolor=color)
        assert result["box"]["textcolor"] == color

    def test_textoncolor_set_when_provided(self):
        color = [0.0, 1.0, 0.0, 1.0]
        result = textbutton("tb-1", [0, 0, 80, 24], textoncolor=color)
        assert result["box"]["textoncolor"] == color

    def test_patching_rect_defaults_offscreen(self):
        result = textbutton("tb-1", [10, 20, 80, 24])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 80
        assert pr[3] == 24

    def test_patching_rect_override(self):
        result = textbutton("tb-1", [0, 0, 80, 24], patching_rect=[50, 50, 80, 24])
        assert result["box"]["patching_rect"] == [50, 50, 80, 24]

    def test_kwargs_passthrough(self):
        result = textbutton("tb-1", [0, 0, 80, 24], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestUmenu:
    """Tests for umenu() dropdown menu."""

    def test_returns_box_dict(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert "box" in result

    def test_maxclass_is_umenu(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert result["box"]["maxclass"] == "umenu"

    def test_id_set(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert result["box"]["id"] == "um-1"

    def test_presentation_is_1(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 120, 22]
        result = umenu("um-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_3(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert result["box"]["numoutlets"] == 3

    def test_outlettype(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert result["box"]["outlettype"] == ["int", "", ""]

    def test_items_not_set_by_default(self):
        result = umenu("um-1", [0, 0, 120, 22])
        assert "items" not in result["box"]

    def test_items_set_when_provided(self):
        result = umenu("um-1", [0, 0, 120, 22], items=["sine", "saw", "square"])
        assert result["box"]["items"] == ["sine", "saw", "square"]

    def test_patching_rect_defaults_offscreen(self):
        result = umenu("um-1", [10, 20, 120, 22])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 120
        assert pr[3] == 22

    def test_patching_rect_override(self):
        result = umenu("um-1", [0, 0, 120, 22], patching_rect=[50, 50, 120, 22])
        assert result["box"]["patching_rect"] == [50, 50, 120, 22]

    def test_kwargs_passthrough(self):
        result = umenu("um-1", [0, 0, 120, 22], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestRadiogroup:
    """Tests for radiogroup() vertical radio buttons."""

    def test_returns_box_dict(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert "box" in result

    def test_maxclass_is_radiogroup(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["maxclass"] == "radiogroup"

    def test_id_set(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["id"] == "rg-1"

    def test_presentation_is_1(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 80, 80]
        result = radiogroup("rg-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_1(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["numoutlets"] == 1

    def test_outlettype(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["outlettype"] == [""]

    def test_itemcount_default(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert result["box"]["itemcount"] == 4

    def test_itemcount_custom(self):
        result = radiogroup("rg-1", [0, 0, 80, 80], itemcount=6)
        assert result["box"]["itemcount"] == 6

    def test_value_not_set_by_default(self):
        result = radiogroup("rg-1", [0, 0, 80, 80])
        assert "value" not in result["box"]

    def test_value_set_when_provided(self):
        result = radiogroup("rg-1", [0, 0, 80, 80], value=2)
        assert result["box"]["value"] == 2

    def test_patching_rect_defaults_offscreen(self):
        result = radiogroup("rg-1", [10, 20, 80, 80])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 80
        assert pr[3] == 80

    def test_patching_rect_override(self):
        result = radiogroup("rg-1", [0, 0, 80, 80], patching_rect=[50, 50, 80, 80])
        assert result["box"]["patching_rect"] == [50, 50, 80, 80]

    def test_kwargs_passthrough(self):
        result = radiogroup("rg-1", [0, 0, 80, 80], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestNodes:
    """Tests for nodes() XY node editor."""

    def test_returns_box_dict(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert "box" in result

    def test_maxclass_is_nodes(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["maxclass"] == "nodes"

    def test_id_set(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["id"] == "nd-1"

    def test_presentation_is_1(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 200, 100]
        result = nodes("nd-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_3(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["numoutlets"] == 3

    def test_outlettype(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["outlettype"] == ["", "", ""]

    def test_numnodes_default(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert result["box"]["numnodes"] == 4

    def test_numnodes_custom(self):
        result = nodes("nd-1", [0, 0, 200, 100], numnodes=8)
        assert result["box"]["numnodes"] == 8

    def test_xmin_not_set_by_default(self):
        result = nodes("nd-1", [0, 0, 200, 100])
        assert "xmin" not in result["box"]

    def test_xmin_set_when_provided(self):
        result = nodes("nd-1", [0, 0, 200, 100], xmin=0.0)
        assert result["box"]["xmin"] == 0.0

    def test_xmax_set_when_provided(self):
        result = nodes("nd-1", [0, 0, 200, 100], xmax=1.0)
        assert result["box"]["xmax"] == 1.0

    def test_ymin_set_when_provided(self):
        result = nodes("nd-1", [0, 0, 200, 100], ymin=-1.0)
        assert result["box"]["ymin"] == -1.0

    def test_ymax_set_when_provided(self):
        result = nodes("nd-1", [0, 0, 200, 100], ymax=1.0)
        assert result["box"]["ymax"] == 1.0

    def test_patching_rect_defaults_offscreen(self):
        result = nodes("nd-1", [10, 20, 200, 100])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 200
        assert pr[3] == 100

    def test_patching_rect_override(self):
        result = nodes("nd-1", [0, 0, 200, 100], patching_rect=[50, 50, 200, 100])
        assert result["box"]["patching_rect"] == [50, 50, 200, 100]

    def test_kwargs_passthrough(self):
        result = nodes("nd-1", [0, 0, 200, 100], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestMatrixctrl:
    """Tests for matrixctrl() grid matrix control."""

    def test_returns_box_dict(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert "box" in result

    def test_maxclass_is_matrixctrl(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["maxclass"] == "matrixctrl"

    def test_id_set(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["id"] == "mc-1"

    def test_presentation_is_1(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 120, 120]
        result = matrixctrl("mc-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_2(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["numoutlets"] == 2

    def test_outlettype(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["outlettype"] == ["", ""]

    def test_rows_default(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["rows"] == 8

    def test_rows_custom(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120], rows=4)
        assert result["box"]["rows"] == 4

    def test_columns_default(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120])
        assert result["box"]["columns"] == 8

    def test_columns_custom(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120], columns=16)
        assert result["box"]["columns"] == 16

    def test_patching_rect_defaults_offscreen(self):
        result = matrixctrl("mc-1", [10, 20, 120, 120])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 120
        assert pr[3] == 120

    def test_patching_rect_override(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120], patching_rect=[50, 50, 120, 120])
        assert result["box"]["patching_rect"] == [50, 50, 120, 120]

    def test_kwargs_passthrough(self):
        result = matrixctrl("mc-1", [0, 0, 120, 120], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestUbutton:
    """Tests for ubutton() invisible click zone."""

    def test_returns_box_dict(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert "box" in result

    def test_maxclass_is_ubutton(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert result["box"]["maxclass"] == "ubutton"

    def test_id_set(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert result["box"]["id"] == "ub-1"

    def test_presentation_is_1(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 60, 60]
        result = ubutton("ub-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_1(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert result["box"]["numinlets"] == 1

    def test_numoutlets_is_4(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert result["box"]["numoutlets"] == 4

    def test_outlettype(self):
        result = ubutton("ub-1", [0, 0, 60, 60])
        assert result["box"]["outlettype"] == ["bang", "", "", "int"]

    def test_patching_rect_defaults_offscreen(self):
        result = ubutton("ub-1", [10, 20, 60, 60])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 60
        assert pr[3] == 60

    def test_patching_rect_override(self):
        result = ubutton("ub-1", [0, 0, 60, 60], patching_rect=[50, 50, 60, 60])
        assert result["box"]["patching_rect"] == [50, 50, 60, 60]

    def test_kwargs_passthrough(self):
        result = ubutton("ub-1", [0, 0, 60, 60], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"


class TestNslider:
    """Tests for nslider() staff notation display."""

    def test_returns_box_dict(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert "box" in result

    def test_maxclass_is_nslider(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert result["box"]["maxclass"] == "nslider"

    def test_id_set(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert result["box"]["id"] == "ns-1"

    def test_presentation_is_1(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert result["box"]["presentation"] == 1

    def test_presentation_rect_matches_input(self):
        rect = [10, 20, 100, 120]
        result = nslider("ns-1", rect)
        assert result["box"]["presentation_rect"] == rect

    def test_numinlets_is_2(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert result["box"]["numinlets"] == 2

    def test_numoutlets_is_2(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert result["box"]["numoutlets"] == 2

    def test_outlettype(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert result["box"]["outlettype"] == ["", ""]

    def test_staffs_not_set_by_default(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert "staffs" not in result["box"]

    def test_staffs_set_when_provided(self):
        result = nslider("ns-1", [0, 0, 100, 120], staffs=2)
        assert result["box"]["staffs"] == 2

    def test_bgcolor_not_set_by_default(self):
        result = nslider("ns-1", [0, 0, 100, 120])
        assert "bgcolor" not in result["box"]

    def test_bgcolor_set_when_provided(self):
        color = [1.0, 1.0, 1.0, 1.0]
        result = nslider("ns-1", [0, 0, 100, 120], bgcolor=color)
        assert result["box"]["bgcolor"] == color

    def test_patching_rect_defaults_offscreen(self):
        result = nslider("ns-1", [10, 20, 100, 120])
        pr = result["box"]["patching_rect"]
        assert pr[0] == 700
        assert pr[2] == 100
        assert pr[3] == 120

    def test_patching_rect_override(self):
        result = nslider("ns-1", [0, 0, 100, 120], patching_rect=[50, 50, 100, 120])
        assert result["box"]["patching_rect"] == [50, 50, 100, 120]

    def test_kwargs_passthrough(self):
        result = nslider("ns-1", [0, 0, 100, 120], custom_attr="val")
        assert result["box"]["custom_attr"] == "val"
