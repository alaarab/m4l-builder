"""Orbit kit: poly_lfo_engine codebox + polar_cluster hero + Surface.reserve."""

from m4l_builder import AudioEffect, find_v8ui_contract_issues
from m4l_builder.engines.polar_cluster import polar_cluster_js
from m4l_builder.gen_lint import lint_genexpr
from m4l_builder.gen_stateful import poly_lfo_engine
from m4l_builder.surface import Surface
from m4l_builder.theme import ACCENTS


def test_poly_lfo_engine_lints():
    code = poly_lfo_engine(voices=4)
    assert lint_genexpr(code, 1, 8) == []


def test_poly_lfo_engine_shape():
    code = poly_lfo_engine(voices=4)
    # function def FIRST (house rule), then Params, then decls before statements
    assert code.index("lfo_voice(") < code.index("Param rate")
    assert code.index("Param rate") < code.index("Data data_ph(4);")
    # both out families per voice + the cluster fold + target scaling
    for i in range(1, 5):
        assert f"out{i} = tmin_{i} + (tmax_{i} - tmin_{i})" in code
        assert f"out{4 + i} = vv_{i};" in code
        # percent params (slot numboxes read "100 %"), scaled 0.01 in-body
        assert f"Param depth_{i}(100.0, min=0.0, max=100.0);" in code
        assert f"d_{i} = depth_{i} * 0.01;" in code
    assert "fold(offset + bias * 0, 0, 1)" in code
    # v2: per-lane shape (no shared menu) + lanes reveal count
    for i in range(1, 5):
        assert f"Param shape_{i}(0.0, min=0.0, max=5.0);" in code
    assert "Param shape(" not in code
    assert "Param lanes(4.0, min=1.0, max=4.0);" in code
    # GUI tick pokes [value, shape, depth, windowed] per lane + lanes tail
    # (the chaos_lanes lane-stack hero contract)
    assert "Buffer buf_orbit_gui;" in code
    assert "poke(buf_orbit_gui, v_1, 0, 0);" in code
    assert "poke(buf_orbit_gui, shape_1, 1, 0);" in code
    assert "poke(buf_orbit_gui, lanes, 16, 0);" in code


def test_polar_cluster_js_contract():
    js = polar_cluster_js(voices=4)
    assert find_v8ui_contract_issues(js) == []
    assert "VOICES = 4" in js
    assert '"orbit"' in js and "16" in js   # 4*voices samps buffer binding


def test_surface_reserve_advances_width():
    device = AudioEffect("Reserve Test", width=1, height=168)
    surf = Surface(device, accent=ACCENTS["strip"])
    x0 = surf.reserve(344)
    x1 = surf.reserve(50)
    assert x1 == x0 + 344 + surf.gap
    width = surf.finalize()
    assert width == x1 + 50 + surf.margin
