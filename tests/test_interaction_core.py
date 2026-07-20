"""Tests for interaction_core.py and the engines migrated to use it.

These are regression guards, not migration proof (the migration itself was
verified by hand via `diff` against pre-edit output for every engine touched,
per the P6 session). The point here is to catch FUTURE breakage: Max caches
a jsui/v8ui sidecar by a hash of its JS text (see design_system.py's
js_sidecar_name), so a change to a migrated engine's rendered output — even
one byte — is a change to what a shipped device embeds. An accidental edit to
a marker, a wrong margin expression passed to plot_geometry_*_js, or a stray
character in a shared constant should fail loudly here.
"""
import hashlib

from m4l_builder.engines import interaction_core as ic
from m4l_builder.engines.ballistics_curve import ballistics_curve_js
from m4l_builder.engines.delay_trail import delay_trail_js
from m4l_builder.engines.eq_curve import eq_curve_js
from m4l_builder.engines.exciter_curve import exciter_curve_js
from m4l_builder.engines.level_history import level_history_js
from m4l_builder.engines.level_meter import level_meter_js
from m4l_builder.engines.linear_phase_eq_display import linear_phase_eq_display_js
from m4l_builder.engines.loop_filter_curve import loop_filter_curve_js
from m4l_builder.engines.transfer_curve import transfer_curve_js
from m4l_builder.engines.transient_history import transient_history_js
from m4l_builder.engines.waveshape_curve import waveshape_curve_js
from m4l_builder.jsui_contract import find_jsui_contract_issues, find_v8ui_contract_issues


def _sha256(js: str) -> str:
    return hashlib.sha256(js.encode("utf-8")).hexdigest()


class TestConstantsAreES5Clean:
    """Mirrors test_design_system_snippet_is_es5_clean: every shared literal
    must carry no forbidden ES6 constructs, since engines splice it into a
    jsui/v8ui file that has to pass the same static contract check."""

    CONSTANTS = [
        ic.POINTER_X_JS,
        ic.POINTER_Y_JS,
        ic.POINTER_BUTTONS_JS,
        ic.POINTER_X_LONGNAME_JS,
        ic.POINTER_Y_LONGNAME_JS,
        ic.POINTER_BUTTONS_LONGNAME_JS,
        ic.CLAMP_TERNARY_JS,
        ic.CLAMP_IFORM_JS,
        ic.ONRESIZE_JS,
    ]

    def test_no_forbidden_es6_constructs(self):
        for snippet in self.CONSTANTS:
            for bad in ("`", "=>", " let ", " const ", "class "):
                assert bad not in snippet, (bad, snippet)

    def test_no_constant_has_leading_or_trailing_newline(self):
        # A marker-replace only reproduces the original byte-for-byte if the
        # constant carries none of the surrounding template's own newlines.
        for snippet in self.CONSTANTS:
            assert not snippet.startswith("\n"), snippet
            assert not snippet.endswith("\n"), snippet

    def test_pointer_families_are_distinct_not_just_renamed(self):
        # The two families differ in the pointer_buttons BODY (ternary vs
        # if/return), not just parameter names -- guard against someone
        # "simplifying" them back into one template.
        assert "? 2 : 1" in ic.POINTER_BUTTONS_JS
        assert "? 2 : 1" not in ic.POINTER_BUTTONS_LONGNAME_JS
        assert "if (pointerevent.button === 2) return 2;" in ic.POINTER_BUTTONS_LONGNAME_JS


class TestPlotGeometryFormatters:
    """Pure-function checks on the two plot_geometry_*_js formatters."""

    def test_short_plain(self):
        js = ic.plot_geometry_short_js("8", "mgraphics.size[0] - 8", "8", "mgraphics.size[1] - 16")
        assert js == (
            "function plot_l() { return 8; }\n"
            "function plot_r() { return mgraphics.size[0] - 8; }\n"
            "function plot_t() { return 8; }\n"
            "function plot_b() { return mgraphics.size[1] - 16; }\n"
            "function plot_w() { return plot_r() - plot_l(); }\n"
            "function plot_h() { return plot_b() - plot_t(); }"
        )

    def test_short_guarded(self):
        js = ic.plot_geometry_short_js("5", "mgraphics.size[0] - 5", "11", "mgraphics.size[1] - 10", guarded=True)
        assert "var d = plot_r() - plot_l(); return d > 1 ? d : 1;" in js
        assert "var d = plot_b() - plot_t(); return d > 1 ? d : 1;" in js

    def test_short_accepts_arbitrary_expressions(self):
        # transfer_curve.py / waveshape_curve.py pass compound expressions,
        # not bare numbers or identifiers -- must pass through verbatim.
        js = ic.plot_geometry_short_js(
            "MARGIN_L", "mgraphics.size[0] - MARGIN_R - GR_BAR_W - 6", "MARGIN_T", "mgraphics.size[1] - MARGIN_B"
        )
        assert "function plot_r() { return mgraphics.size[0] - MARGIN_R - GR_BAR_W - 6; }" in js

    def test_long_is_column_aligned(self):
        js = ic.plot_geometry_long_js("MARGIN_LEFT", "mgraphics.size[0] - MARGIN_RIGHT", "MARGIN_TOP", "mgraphics.size[1] - MARGIN_BOTTOM")
        assert js == (
            "function plot_left()   { return MARGIN_LEFT; }\n"
            "function plot_right()  { return mgraphics.size[0] - MARGIN_RIGHT; }\n"
            "function plot_top()    { return MARGIN_TOP; }\n"
            "function plot_bottom() { return mgraphics.size[1] - MARGIN_BOTTOM; }\n"
            "function plot_w()      { return plot_right() - plot_left(); }\n"
            "function plot_h()      { return plot_bottom() - plot_top(); }"
        )


class TestMigratedEnginesContainExpectedSharedBlocks:
    """Targeted diagnostic: the right interaction_core constant appears
    verbatim in each migrated engine's output. Failing here points straight
    at which shared piece broke, rather than just "the hash changed"."""

    def test_ballistics_curve_pe_fb_family(self):
        js = ballistics_curve_js()
        assert ic.POINTER_X_JS in js
        assert ic.POINTER_BUTTONS_JS in js
        assert ic.CLAMP_TERNARY_JS in js
        assert ic.ONRESIZE_JS in js

    def test_delay_trail_pe_fb_family(self):
        js = delay_trail_js()
        assert ic.POINTER_X_JS in js
        assert ic.POINTER_Y_JS in js
        assert ic.POINTER_BUTTONS_JS in js
        assert ic.CLAMP_TERNARY_JS in js
        assert ic.ONRESIZE_JS in js

    def test_eq_curve_longname_family(self):
        js = eq_curve_js()
        assert ic.POINTER_X_LONGNAME_JS in js
        assert ic.POINTER_Y_LONGNAME_JS in js
        assert ic.POINTER_BUTTONS_LONGNAME_JS in js
        assert ic.CLAMP_IFORM_JS in js
        assert "function plot_left()   { return MARGIN_LEFT; }" in js

    def test_linear_phase_eq_display_longname_family(self):
        js = linear_phase_eq_display_js()
        assert ic.POINTER_X_LONGNAME_JS in js
        assert ic.POINTER_Y_LONGNAME_JS in js
        assert ic.POINTER_BUTTONS_LONGNAME_JS in js
        assert ic.CLAMP_IFORM_JS in js

    def test_level_meter_clamp_and_onresize_only(self):
        # Different plot_l/t/r/b declaration ORDER than the shared formatter
        # covers, so level_meter.py deliberately keeps its own plot block.
        js = level_meter_js()
        assert ic.CLAMP_TERNARY_JS in js
        assert ic.ONRESIZE_JS in js

    def test_transfer_curve_y_x_order(self):
        # transfer_curve.py declares pointer_y before pointer_x (unlike
        # ballistics/delay_trail's x-before-y) -- both orders must work.
        js = transfer_curve_js()
        assert js.index(ic.POINTER_Y_JS) < js.index(ic.POINTER_X_JS)

    def test_follows_v8ui_contract(self):
        # These host pointer events (onpointerdown/move/up/leave) and must be
        # held to the v8ui contract, not the classic-jsui one -- mirrors
        # test_engines.py's V8UI_FACTORIES / test_pointer_engines_follow_v8ui_contract.
        for factory in (
            ballistics_curve_js,
            delay_trail_js,
            eq_curve_js,
            exciter_curve_js,
            level_history_js,
            level_meter_js,
            linear_phase_eq_display_js,
            loop_filter_curve_js,
            transfer_curve_js,
            waveshape_curve_js,
        ):
            assert find_v8ui_contract_issues(factory()) == [], factory.__name__

    def test_transient_history_follows_jsui_contract(self):
        # Display-only (no pointer handlers), so the classic-jsui contract
        # applies here instead of v8ui.
        assert find_jsui_contract_issues(transient_history_js()) == []


# Golden byte-identity hashes: default-kwargs output at the time these 11
# engines were migrated onto interaction_core.py, verified byte-for-byte
# identical (via `diff`) to the pre-migration hand-authored output. If a
# future change to interaction_core.py or one of these engines is
# INTENTIONAL, regenerate the hash; if it's not, this is the bug.
GOLDEN_SHA256 = {
    "ballistics_curve_js": ("c51c9943187efe5551d0167632a350734c047e33ab961f21e5dd1dbf83729f46", 12357),
    "delay_trail_js": ("db52b252ed497f14515a932eaa97b547063056f3ba36e856c4a4f53d3f098fd9", 37858),
    "eq_curve_js": ("6b53347417b5c3c187e5b5b663e9fdf22677a1c1aec11e6226fc6ee3a2e259e9", 130435),
    "exciter_curve_js": ("497f90e209a10514d61ee7861a1e9abc3853ad69491aeb01a98e85e8630287cc", 19581),
    "level_history_js": ("8cbd1632e9e218efc3adefc228e4ce5949d9cb570ac6eb95b2b2b84e5abc938b", 24533),
    "level_meter_js": ("4ae60d290ee6cec9499ab61844106a08497d26c8c40ca9a7781a1bfd81e5387c", 5408),
    "linear_phase_eq_display_js": ("65bf26868963d743bf081bc22ab5dd041ae1f4afb3da73970000dd639c7d4ae2", 93540),
    "loop_filter_curve_js": ("083b0e76b60ea1fd70a6780c5c336f318ea41d29887d6e1372a151ed8c4689f9", 10029),
    "transfer_curve_js": ("2bac0c2c47f2c6fe02de8d842304a46935d5f0cd74b467f97324e110e4775d8d", 20173),
    "transient_history_js": ("32e95da84d28f319a0b19a717b87a0652a733bfefd58202767f767847fbd03b3", 11395),
    "waveshape_curve_js": ("c7256aa064f5e937ca0fbd1775c3869a1faa95d99bd151c0857e52e18f691d1f", 44629),
}

FACTORIES = {
    "ballistics_curve_js": ballistics_curve_js,
    "delay_trail_js": delay_trail_js,
    "eq_curve_js": eq_curve_js,
    "exciter_curve_js": exciter_curve_js,
    "level_history_js": level_history_js,
    "level_meter_js": level_meter_js,
    "linear_phase_eq_display_js": linear_phase_eq_display_js,
    "loop_filter_curve_js": loop_filter_curve_js,
    "transfer_curve_js": transfer_curve_js,
    "transient_history_js": transient_history_js,
    "waveshape_curve_js": waveshape_curve_js,
}


class TestGoldenHashes:
    """Broad safety net: catches ANY output change, not just to the shared
    pieces (e.g. an accidental edit to color defaults would trip this too)."""

    def test_all_migrated_engines_match_golden_hash(self):
        mismatches = []
        for name, factory in FACTORIES.items():
            js = factory()
            golden_hash, golden_len = GOLDEN_SHA256[name]
            actual_hash = _sha256(js)
            if actual_hash != golden_hash or len(js) != golden_len:
                mismatches.append((name, len(js), golden_len, actual_hash, golden_hash))
        assert mismatches == []
