"""poly_mod_engine — the merged Orbit modulator core (#76: Orbit + Entropy)."""

from m4l_builder.gen_lint import lint_genexpr
from m4l_builder.gen_stateful import poly_mod_engine


def test_composes_clean_for_eight_lanes():
    code = poly_mod_engine(voices=8)
    assert lint_genexpr(code, 1, 16) == []


def test_per_lane_source_selects_between_both_families():
    code = poly_mod_engine(voices=8)
    for i in range(1, 9):
        # ONLY the selected family computes (real if/else — gen ternaries
        # are eager); the other family's state holds and resumes on switch
        assert f"if (source_{i} < 3.5) {{" in code
        assert (f"v_{i} = lfo_voice(data_ph, data_sh, data_dr, {i - 1},"
                in code)
        assert (f"v_{i} = chaos_voice(data_phc, data_st, data_out, {i - 1},"
                in code)
        assert f"vl_{i}" not in code and f"vc_{i}" not in code
        # source spans the 10-entry union menu
        assert f"Param source_{i}(0.0, min=0.0, max=9.0);" in code
    # the two families keep SEPARATE state blocks (no Data clash)
    assert "Data data_ph(8);" in code and "Data data_phc(8);" in code
    # Entropy's identity globals ride along; LFO lanes simply ignore them
    assert "Param entropy(50.0, min=0.0, max=100.0);" in code
    assert "Param tame(0.0, min=0.0, max=100.0);" in code


def test_keeps_the_shared_uplink_and_viz_contract():
    code = poly_mod_engine(voices=8)
    # REMOTE natives then MODULATE raws (2*voices outs)
    assert "out8 = tmin_8 + (tmax_8 - tmin_8) *" in code
    assert "out16 = vv_8;" in code
    # [value, source, depth, on] GUI frames — the chaos_lanes hero contract
    assert "poke(buf_orbit_gui, source_1, 1, 0);" in code
    assert "poke(buf_orbit_gui, on_8, 31, 0);" in code
