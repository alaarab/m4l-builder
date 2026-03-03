"""Tests for Theme dataclass and Device theme integration."""

from m4l_builder.theme import Theme, MIDNIGHT, WARM, COOL, LIGHT
from m4l_builder.device import Device, AudioEffect


class TestThemeDataclass:
    """Test Theme dataclass defaults and __post_init__ derivation."""

    def test_basic_construction(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.bg == [0.1, 0.1, 0.1, 1.0]
        assert t.accent == [0.5, 0.8, 0.6, 1.0]

    def test_dial_color_derived_from_accent(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.dial_color == [0.5, 0.8, 0.6, 1.0]

    def test_needle_color_derived_from_text(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.needle_color == [0.9, 0.9, 0.9, 1.0]

    def test_tab_bg_derived_from_surface(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.tab_bg == [0.15, 0.15, 0.15, 1.0]

    def test_tab_bg_on_derived_from_accent(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.tab_bg_on == [0.5, 0.8, 0.6, 1.0]

    def test_tab_text_derived_from_text_dim(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.tab_text == [0.5, 0.5, 0.5, 1.0]

    def test_tab_text_on_derived_from_text(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.tab_text_on == [0.9, 0.9, 0.9, 1.0]

    def test_explicit_dial_color_not_overridden(self):
        custom = [1.0, 0.0, 0.0, 1.0]
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
            dial_color=custom,
        )
        assert t.dial_color == custom

    def test_default_fontname(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.fontname == "Ableton Sans Medium"
        assert t.fontname_bold == "Ableton Sans Bold"

    def test_derived_values_are_copies(self):
        """Derived values should be copies, not references to the original."""
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        t.dial_color[0] = 0.99
        assert t.accent[0] == 0.5  # original unchanged

    def test_default_meter_colors_exist(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.meter_cold is not None and len(t.meter_cold) == 4
        assert t.meter_warm is not None and len(t.meter_warm) == 4
        assert t.meter_hot is not None and len(t.meter_hot) == 4
        assert t.meter_over is not None and len(t.meter_over) == 4

    def test_scope_color_derived_from_accent(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.scope_color == [0.5, 0.8, 0.6, 1.0]

    def test_scope_bgcolor_derived_from_bg(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        assert t.scope_bgcolor == [0.1, 0.1, 0.1, 1.0]

    def test_meter_kwargs_structure(self):
        t = Theme(
            bg=[0.1, 0.1, 0.1, 1.0],
            surface=[0.15, 0.15, 0.15, 1.0],
            section=[0.2, 0.2, 0.2, 1.0],
            text=[0.9, 0.9, 0.9, 1.0],
            text_dim=[0.5, 0.5, 0.5, 1.0],
            accent=[0.5, 0.8, 0.6, 1.0],
        )
        kwargs = t.meter_kwargs()
        assert 'coldcolor' in kwargs
        assert 'warmcolor' in kwargs
        assert 'hotcolor' in kwargs
        assert 'overloadcolor' in kwargs
        assert kwargs['coldcolor'] == t.meter_cold
        assert kwargs['warmcolor'] == t.meter_warm
        assert kwargs['hotcolor'] == t.meter_hot
        assert kwargs['overloadcolor'] == t.meter_over


class TestPrebuiltThemes:
    """Test the 4 pre-built themes are valid."""

    def test_midnight_has_all_fields(self):
        assert MIDNIGHT.bg is not None
        assert MIDNIGHT.accent is not None
        assert MIDNIGHT.dial_color is not None
        assert MIDNIGHT.meter_cold is not None
        assert MIDNIGHT.meter_warm is not None
        assert MIDNIGHT.meter_hot is not None
        assert MIDNIGHT.meter_over is not None
        assert MIDNIGHT.scope_color is not None
        assert MIDNIGHT.scope_bgcolor is not None

    def test_warm_has_all_fields(self):
        assert WARM.bg is not None
        assert WARM.accent is not None
        assert WARM.dial_color is not None
        assert WARM.meter_cold is not None
        assert WARM.meter_warm is not None
        assert WARM.meter_hot is not None
        assert WARM.meter_over is not None
        assert WARM.scope_color is not None
        assert WARM.scope_bgcolor is not None

    def test_cool_has_all_fields(self):
        assert COOL.bg is not None
        assert COOL.accent is not None
        assert COOL.dial_color is not None
        assert COOL.meter_cold is not None
        assert COOL.meter_warm is not None
        assert COOL.meter_hot is not None
        assert COOL.meter_over is not None
        assert COOL.scope_color is not None
        assert COOL.scope_bgcolor is not None

    def test_light_has_all_fields(self):
        assert LIGHT.bg is not None
        assert LIGHT.accent is not None
        assert LIGHT.dial_color is not None
        assert LIGHT.meter_cold is not None
        assert LIGHT.meter_warm is not None
        assert LIGHT.meter_hot is not None
        assert LIGHT.meter_over is not None
        assert LIGHT.scope_color is not None
        assert LIGHT.scope_bgcolor is not None

    def test_themes_are_distinct(self):
        assert MIDNIGHT.bg != WARM.bg
        assert COOL.bg != LIGHT.bg
        assert WARM.accent != COOL.accent

    def test_meter_colors_are_four_element_lists(self):
        for theme in (MIDNIGHT, WARM, COOL, LIGHT):
            assert len(theme.meter_cold) == 4
            assert len(theme.meter_warm) == 4
            assert len(theme.meter_hot) == 4
            assert len(theme.meter_over) == 4

    def test_scope_colors_are_four_element_lists(self):
        for theme in (MIDNIGHT, WARM, COOL, LIGHT):
            assert len(theme.scope_color) == 4
            assert len(theme.scope_bgcolor) == 4

    def test_meter_kwargs_returns_correct_keys(self):
        kwargs = MIDNIGHT.meter_kwargs()
        assert set(kwargs.keys()) == {'coldcolor', 'warmcolor', 'hotcolor', 'overloadcolor'}

    def test_meter_kwargs_values_match_fields(self):
        for theme in (MIDNIGHT, WARM, COOL, LIGHT):
            kwargs = theme.meter_kwargs()
            assert kwargs['coldcolor'] == theme.meter_cold
            assert kwargs['warmcolor'] == theme.meter_warm
            assert kwargs['hotcolor'] == theme.meter_hot
            assert kwargs['overloadcolor'] == theme.meter_over


class TestDeviceThemeIntegration:
    """Test Device with theme applies colors to UI elements."""

    def test_device_without_theme_works(self):
        d = Device("Test", 200, 100)
        d.add_panel("bg", [0, 0, 200, 100], bgcolor=[0.1, 0.1, 0.1, 1.0])
        d.add_dial("d1", "test", [10, 10, 45, 45])
        assert len(d.boxes) == 2

    def test_device_with_theme_stores_it(self):
        d = Device("Test", 200, 100, theme=WARM)
        assert d.theme is WARM

    def test_panel_gets_theme_bgcolor(self):
        d = Device("Test", 200, 100, theme=WARM)
        d.add_panel("bg", [0, 0, 200, 100])
        box = d.boxes[0]["box"]
        assert box["bgcolor"] == WARM.bg

    def test_panel_user_bgcolor_overrides_theme(self):
        custom = [0.5, 0.5, 0.5, 1.0]
        d = Device("Test", 200, 100, theme=WARM)
        d.add_panel("bg", [0, 0, 200, 100], bgcolor=custom)
        box = d.boxes[0]["box"]
        assert box["bgcolor"] == custom

    def test_dial_gets_theme_colors(self):
        d = Device("Test", 200, 100, theme=MIDNIGHT)
        d.add_dial("d1", "test", [10, 10, 45, 45])
        box = d.boxes[0]["box"]
        assert box["activedialcolor"] == MIDNIGHT.dial_color
        assert box["activeneedlecolor"] == MIDNIGHT.needle_color

    def test_dial_user_color_overrides_theme(self):
        custom = [1.0, 0.0, 0.0, 1.0]
        d = Device("Test", 200, 100, theme=MIDNIGHT)
        d.add_dial("d1", "test", [10, 10, 45, 45], activedialcolor=custom)
        box = d.boxes[0]["box"]
        assert box["activedialcolor"] == custom

    def test_comment_gets_theme_text_color(self):
        d = Device("Test", 200, 100, theme=COOL)
        d.add_comment("c1", [0, 0, 100, 20], "Hello")
        box = d.boxes[0]["box"]
        assert box["textcolor"] == COOL.text

    def test_comment_user_textcolor_overrides_theme(self):
        custom = [1.0, 0.0, 0.0, 1.0]
        d = Device("Test", 200, 100, theme=COOL)
        d.add_comment("c1", [0, 0, 100, 20], "Hello", textcolor=custom)
        box = d.boxes[0]["box"]
        assert box["textcolor"] == custom

    def test_tab_gets_theme_colors(self):
        d = Device("Test", 200, 100, theme=WARM)
        d.add_tab("t1", "mode", [0, 0, 200, 30], options=["A", "B"])
        box = d.boxes[0]["box"]
        assert box["bgcolor"] == WARM.tab_bg
        assert box["bgoncolor"] == WARM.tab_bg_on
        assert box["textcolor"] == WARM.tab_text
        assert box["textoncolor"] == WARM.tab_text_on

    def test_toggle_gets_theme_accent(self):
        d = Device("Test", 200, 100, theme=MIDNIGHT)
        d.add_toggle("tog1", "on", [10, 10, 20, 20])
        box = d.boxes[0]["box"]
        assert box["activebgoncolor"] == MIDNIGHT.accent

    def test_scope_gets_theme_colors(self):
        d = Device("Test", 200, 100, theme=COOL)
        d.add_scope("s1", [0, 0, 200, 100])
        box = d.boxes[0]["box"]
        assert box["bgcolor"] == COOL.scope_bgcolor
        assert box["activelinecolor"] == COOL.scope_color

    def test_meter_gets_theme_colors(self):
        d = Device("Test", 200, 100, theme=MIDNIGHT)
        d.add_meter("m1", [0, 0, 20, 100])
        box = d.boxes[0]["box"]
        assert box["coldcolor"] == MIDNIGHT.meter_cold
        assert box["warmcolor"] == MIDNIGHT.meter_warm
        assert box["hotcolor"] == MIDNIGHT.meter_hot
        assert box["overloadcolor"] == MIDNIGHT.meter_over

    def test_meter_user_colors_override_theme(self):
        custom_cold = [0.0, 1.0, 0.0, 1.0]
        d = Device("Test", 200, 100, theme=MIDNIGHT)
        d.add_meter("m1", [0, 0, 20, 100], coldcolor=custom_cold)
        box = d.boxes[0]["box"]
        assert box["coldcolor"] == custom_cold
        # other colors still from theme
        assert box["warmcolor"] == MIDNIGHT.meter_warm

    def test_meter_without_theme_has_no_colors_injected(self):
        d = Device("Test", 200, 100)
        d.add_meter("m1", [0, 0, 20, 100])
        box = d.boxes[0]["box"]
        assert "coldcolor" not in box
        assert "warmcolor" not in box

    def test_audio_effect_with_theme(self):
        d = AudioEffect("Test", 200, 100, theme=WARM)
        assert d.theme is WARM
        d.add_panel("bg", [0, 0, 200, 100])
        box = d.boxes[-1]["box"]
        assert box["bgcolor"] == WARM.bg

    def test_builds_successfully_with_theme(self):
        d = AudioEffect("Themed", 200, 100, theme=MIDNIGHT)
        d.add_panel("bg", [0, 0, 200, 100])
        d.add_dial("d1", "test", [10, 10, 45, 45])
        d.add_comment("title", [8, 8, 100, 16], "TEST")
        data = d.to_bytes()
        assert len(data) > 0
