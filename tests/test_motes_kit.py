"""Motes kit: freeze capture block + grain_cloud hero contract."""

from m4l_builder import find_v8ui_contract_issues
from m4l_builder.engines.grain_cloud import grain_cloud_js
from m4l_builder.gen_stateful import freeze_capture_block


def test_freeze_capture_block_verbatim_shape():
    blk = freeze_capture_block()
    # rising-edge detect + TIME-REVERSED copy of both lines (Particle verbatim)
    assert "change(freezeTgt > 0.5)" in blk
    assert "fz_idx = freezeSamps - fz_i;" in blk
    assert "poke(data_freeze, delaySigR.read(fz_idx), fz_i, 0);" in blk
    assert "poke(data_freeze, delaySigL.read(fz_idx), fz_i, 1);" in blk
    # equal-power seam over the slewed ramp
    assert "freezeG = sqrt(his_freezeRamp);" in blk
    assert "invFreezeG = sqrt(1 - his_freezeRamp);" in blk
    assert "mstosamps(400.0)" in blk


def test_grain_cloud_js_contract():
    js = grain_cloud_js(n_grains=32, bins=128)
    assert find_v8ui_contract_issues(js) == []
    assert "N_GRAINS = 32" in js and "BINS = 128" in js
    # buffer bindings: grains (3n+1) then wave (bins+1), positional order
    assert '"grains", "wave"' in js
    assert "97" in js and "129" in js
