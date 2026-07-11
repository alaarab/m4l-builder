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


def test_chaos_voice_sources_and_macros():
    # chaos_voice_fn body (shared with the retired poly_chaos_engine) — the
    # six sources' signatures, the chaos-threshold rho map, TAME, and guards.
    code = poly_mod_engine(voices=4)
    assert "tgt = noise() * 0.5 + 0.5;" in code                    # drift target
    assert "v = 0.5 + (n - 0.5) * (0.2 + 0.8 * ent);" in code      # S&H width by entropy
    assert "v += noise() * (0.03 + 0.35 * ent);" in code           # drunk step by entropy
    assert "r = 3.2 + 0.7995 * ent;" in code                       # logistic r map
    # rho spans the chaos threshold (24.74): default entropy is CHAOTIC
    # (14+14*ent parked Lorenz at a fixed point below ent~0.77)
    assert "rho = 22 + 7 * ent;" in code
    assert "if (noise() * 0.5 + 0.5 < 0.15 + 0.85 * ent) v = 1;" in code  # burst odds
    # TAME: rate calm, math calm, latch-and-crossfade, growing slew
    assert "rte = rt * (1 - tame) * (1 - tame);" in code
    assert "r = r - tame * max(0, r - 3.4);" in code
    assert "rho = rho - tame * max(0, rho - 10);" in code
    assert "if (tame > 0.02 && tprev <= 0.02) poke(data_out, v, idx, 1);" in code
    assert "tc = tame * tame * (3 - 2 * tame);" in code
    assert "sm += (vm - sm) * (1 - tc * 0.9995);" in code
    # stability guards: NaN reseed + state clamps
    assert "x != x" in code
    assert "clamp(lx + dx * dt, -60, 60)" in code
    assert "dt = min(0.012, rte * 6 / samplerate);" in code
