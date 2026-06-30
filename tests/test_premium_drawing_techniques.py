"""Tests for the premium drawing-techniques library + glass panel showcase.

Lives alongside tests/test_engines.py (imports mirror that module's style).
"""

from m4l_builder.engines.glass_panel_bg import (
    DS_HELPERS_JS,
    ds_helpers_js,
    glass_panel_bg_js,
)
from m4l_builder.jsui_contract import (
    find_jsui_contract_issues,
    validate_v8ui_contract,
)

# The eight reusable helpers the library must expose.
DS_HELPER_NAMES = (
    "ds_outer_shadow",
    "ds_inner_shadow",
    "ds_rim_light",
    "ds_glass_panel",
    "ds_metal_radial",
    "ds_glow_arc",
    "ds_noise_overlay",
    "ds_gradient_fill_path",
)


def test_ds_helpers_define_all_eight():
    """All eight ds_* helpers are defined as functions in the shared block."""
    js = ds_helpers_js()
    assert js is DS_HELPERS_JS
    for name in DS_HELPER_NAMES:
        assert ("function " + name + "(") in js, name


def test_ds_helpers_are_es5_clean():
    """The helpers must fold into DESIGN_SYSTEM_JS, so they carry NO forbidden ES6
    constructs (they lack the paint/init bootstrap, so test only the ES6 half)."""
    js = ds_helpers_js()
    for bad in ("`", "=>", " let ", " const ", "class "):
        assert bad not in js, bad


def test_ds_noise_overlay_is_deterministic_and_capped():
    """The noise overlay must use a seeded LCG (stable across redraws, no flicker)
    and clamp the stroke count so it stays cheap on a static background."""
    js = ds_helpers_js()
    # LCG constants prove the deterministic generator (not Math.random()).
    assert "1103515245" in js
    assert "Math.random" not in js
    # Hard cap so an over-large n can't blow up CPU on a repainting background.
    assert "n > 200 ? 200 : n" in js


def test_soft_edges_use_radial_or_stacked_alpha_not_box_gradient():
    """mgraphics has no box-gradient/blur/clip — soft edges are faked. Glow arc +
    glass sheen come from radial fills; inner/outer shadow from stacked alpha."""
    js = ds_helpers_js()
    # Glass sheen + metal cap use single-center radial fills.
    assert "pattern_create_radial" in js
    # Inner shadow stacks falling-alpha black strokes (no box-gradient available).
    assert "rectangle_rounded" in js
    # No clip/save/restore/transform/dash exist in mgraphics — never emitted.
    for forbidden in ("clip(", "save(", "restore(", "translate(", "set_dash("):
        assert forbidden not in js, forbidden


def test_glass_panel_bg_satisfies_v8ui_contract():
    """The showcase background must pass the v8ui bootstrap contract."""
    js = glass_panel_bg_js()
    assert validate_v8ui_contract(js) is js  # raises on violation
    assert find_v8ui_issues_empty(js)


def find_v8ui_issues_empty(js):
    from m4l_builder.jsui_contract import find_v8ui_contract_issues
    return find_v8ui_contract_issues(js) == []


def test_glass_panel_bg_is_also_es5_clean():
    """The showcase prepends the ES5 design-system + helper blocks; the whole file
    should still pass the stricter jsui ES5 checker (no let/const/arrow/etc.)."""
    assert find_jsui_contract_issues(glass_panel_bg_js()) == []


def test_glass_panel_bg_structure_and_helper_calls():
    """Self-paints its own gradient (no transparency reliance), is a no-pointer
    background (1 inlet / 0 outlets), and actually CALLS the premium helpers."""
    js = glass_panel_bg_js()
    assert "inlets = 1;" in js
    assert "outlets = 0;" in js
    # No pointer handlers on a background.
    for handler in ("function onclick", "function ondrag", "function ondblclick"):
        assert handler not in js, handler
    # Exercises the material/depth/texture helpers.
    assert "ds_glass_panel(" in js
    assert "ds_inner_shadow(" in js
    assert "ds_rim_light(" in js
    # Self-painted background slice (its own gradient), never transparent.
    assert "var LO = [" in js
    assert "var HI = [" in js


def test_glass_panel_bg_noise_toggle():
    """noise toggles the NOISE flag that runtime-gates the overlay call (the helper
    definition + the if (NOISE) {...} call site are always present; only the flag flips)."""
    assert "var NOISE = 1;" in glass_panel_bg_js(noise=True)
    assert "var NOISE = 0;" in glass_panel_bg_js(noise=False)


def test_glass_panel_bg_color_overrides_flow_through():
    """lo/hi/border strings land in the generated var declarations."""
    js = glass_panel_bg_js(
        lo="0.01, 0.02, 0.03, 1.0",
        hi="0.40, 0.41, 0.42, 1.0",
        border="0.5, 0.5, 0.5, 1.0",
    )
    assert "var LO = [0.01, 0.02, 0.03, 1.0];" in js
    assert "var HI = [0.40, 0.41, 0.42, 1.0];" in js
    assert "var BORDER = [0.5, 0.5, 0.5, 1.0];" in js
