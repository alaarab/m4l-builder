"""Entropy kit: poly_chaos_engine codebox (Orbit spine + chaos sources)."""

from m4l_builder.gen_lint import lint_genexpr
from m4l_builder.gen_stateful import poly_chaos_engine


def test_poly_chaos_engine_lints():
    code = poly_chaos_engine(voices=4)
    assert lint_genexpr(code, 1, 8) == []


def test_poly_chaos_engine_shape():
    code = poly_chaos_engine(voices=4)
    # function def FIRST (house rule), then Params, then decls before statements
    assert code.index("chaos_voice(") < code.index("Param rate")
    assert code.index("Param rate") < code.index("Data data_ph(4);")
    # chaos state rows: value/drift-target/logistic-x/lorenz-xyz + out/latch/tame-prev
    assert "Data data_st(4, 6);" in code
    assert "Data data_out(4, 3);" in code
    # both out families per voice + the cluster fold + target scaling (Orbit contract)
    for i in range(1, 5):
        assert f"out{i} = tmin_{i} + (tmax_{i} - tmin_{i})" in code
        assert f"out{4 + i} = vv_{i};" in code
        assert f"Param depth_{i}(100.0, min=0.0, max=100.0);" in code
    assert "fold(offset + bias * 0, 0, 1)" in code
    # GUI tick pokes [value, source, depth, windowed] per lane + lanes tail
    # (the chaos_lanes lane-stack hero contract)
    assert "Buffer buf_entropy_gui;" in code
    assert "poke(buf_entropy_gui, v_1, 0, 0);" in code
    assert "poke(buf_entropy_gui, source_1, 1, 0);" in code
    assert "poke(buf_entropy_gui, vv_4, 15, 0);" in code
    assert "poke(buf_entropy_gui, lanes, 16, 0);" in code


def test_per_lane_sources():
    code = poly_chaos_engine(voices=8)
    # v2: SOURCE is per-lane (the device's whole point); no global source param
    assert "Param source(" not in code
    for i in (1, 4, 8):
        assert f"Param source_{i}(0.0, min=0.0, max=5.0);" in code
        assert f"source_{i}, ent_s, tame_s);" in code
    # lanes count is a gen param poked into the viz tail slot for hero dimming
    assert "Param lanes(8.0, min=1.0, max=8.0);" in code
    assert "poke(buf_entropy_gui, lanes, 32, 0);" in code


def test_chaos_sources_and_macros():
    code = poly_chaos_engine(voices=4)
    # the six sources' signatures
    assert "tgt = noise() * 0.5 + 0.5;" in code                    # drift target
    assert "v = 0.5 + (n - 0.5) * (0.2 + 0.8 * ent);" in code      # S&H width by entropy
    assert "v += noise() * (0.03 + 0.35 * ent);" in code           # drunk step by entropy
    assert "r = 3.2 + 0.7995 * ent;" in code                       # logistic r map
    assert "rho = 14 + 14 * ent;" in code                          # lorenz rho map
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
