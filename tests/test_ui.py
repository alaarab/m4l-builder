"""Tests for UI/presentation element creators in ui.py."""

from m4l_builder.ui import (panel, dial, tab, toggle, comment, scope, meter,
                             menu, number_box, slider, button, live_text, fpic,
                             live_gain, multislider, jsui)
from m4l_builder.constants import DEFAULT_TEXT_COLOR


class TestPanel:
    """Test panel() creates correct background elements."""

    def test_returns_box_dict(self):
        result = panel("p-1", [0, 0, 200, 100], bgcolor=[0.1, 0.1, 0.1, 1.0])
        assert "box" in result

    def test_background_always_set_to_1(self):
        """CRITICAL: panel must always set background:1 to prevent rendering on top."""
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

    def test_parameter_enum_is_space_separated(self):
        result = tab("t-1", "mode", [0, 0, 200, 30], options=["sine", "saw", "square"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == "sine saw square"

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
        assert valueof["parameter_enum"] == "off on"

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

    def test_parameter_enum_is_space_separated(self):
        result = menu("mn-1", "waveform", [0, 0, 100, 20], options=["sine", "saw", "square"])
        valueof = result["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_enum"] == "sine saw square"

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
        assert valueof["parameter_enum"] == "off on"

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
        assert valueof["parameter_enum"] == "BYPASS ACTIVE"

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
