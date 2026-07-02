"""Motes kit: granular + freeze codebox and the grain_cloud hero contract."""

from m4l_builder import find_v8ui_contract_issues
from m4l_builder.engines.grain_cloud import grain_cloud_js
from m4l_builder.gen_patcher import build_gendsp
from m4l_builder.gen_stateful import (
    compose_gen_code,
    freeze_capture_block,
    granular_voice_fn,
    viz_declares,
    viz_poke_block,
)


def test_motes_codebox_with_granular_freeze_and_viz_passes_gen_lint():
    # the Motes composition: delay lines -> freeze capture -> granular_vp -> viz tick
    code = compose_gen_code(
        functions=[granular_voice_fn()],
        params=[("size", 60.0), ("density", 25.0), ("pitch", 0.0), ("spray", 0.0),
                ("position", 0.0), ("width", 100.0), ("freezeTgt", 0.0)],
        body=(
            "Data data_param(32, 6);\nData data_freeze(384000, 2);\n"
            "Delay delaySigL(samplerate * 10);\nDelay delaySigR(samplerate * 10);\n"
            "Buffer buf_win;\n" + viz_declares("buf_grains")
            + "\nHistory his_freezeRamp(0);\n"
            "delaySigL.write(in1);\ndelaySigR.write(in2);\n"
            "freezeSamps = min(samplerate * 2., 384000.);\n" + freeze_capture_block()
            + "\noutGR, outGL = granular_vp(32, buf_win, data_param, delaySigR, delaySigL, "
            "size, mstosamps(position), 1000 / density, freezeG, invFreezeG, data_freeze, "
            "width * 0.01, pitch, spray);\nout1 = outGL;\nout2 = outGR;\n"
            + viz_poke_block("poke(buf_grains, his_freezeRamp, 0, 0);")
        ),
    )
    assert "dsp.gen" in build_gendsp(code, 2, 2)


def test_grain_cloud_js_contract():
    js = grain_cloud_js(n_grains=32, bins=128)
    assert find_v8ui_contract_issues(js) == []
    assert "N_GRAINS = 32" in js and "BINS = 128" in js
    # buffer bindings: grains (3n+1) then wave (bins+1), positional order
    assert '"grains", "wave"' in js
    assert "97" in js and "129" in js
