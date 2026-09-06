import copy

import pytest

from m4l_builder import AudioEffect


def device_with_core(embedded):
    device = AudioEffect("Binding", 200, 168)
    device.add_newobj("control", "float", numinlets=2, numoutlets=1)
    code = "// Param fake(0);\n/* Param hidden(0); */\nParam gain(1);\nout1 = in1 * gain;"
    if embedded:
        device.embed_gendsp("core", code, 1, 1, [0, 0, 100, 20])
    else:
        device.add_gendsp("core", "core", code, 1, 1, [0, 0, 100, 20])
    return device


@pytest.mark.parametrize("embedded", [False, True])
def test_parameter_binding_preserves_graph_and_allows_display_fanout(embedded):
    device = device_with_core(embedded)
    ref = device.bind_gen_param("control", "core", "gain", id="pp_gain",
                                patching_rect=[20, 30, 90, 20], outlettype=[""])
    assert str(ref) == "pp_gain"
    assert device.boxes[-1]["box"]["text"] == "prepend gain"
    assert [(x["patchline"]["source"], x["patchline"]["destination"])
            for x in device.lines[-2:]] == [(["control", 0], ["pp_gain", 0]),
                                            (["pp_gain", 0], ["core", 0])]
    device.add_line(ref, 0, "control", 1)


@pytest.mark.parametrize("overrides,match", [
    ({"parameter": "typo"}, "Unknown GenExpr parameter"),
    ({"parameter": "fake"}, "Unknown GenExpr parameter"),
    ({"parameter": "hidden"}, "Unknown GenExpr parameter"),
    ({"target": "missing"}, "Unknown gen~ target"),
    ({"target": "control"}, "not a gen~"),
    ({"source": "missing"}, "Unknown control source"),
    ({"source_outlet": -1}, "Invalid source outlet"),
    ({"source_outlet": 1}, "Invalid source outlet"),
    ({"id": "control"}, "already exists"),
])
def test_bad_binding_fails_without_partial_graph(overrides, match):
    device = device_with_core(False)
    before = copy.deepcopy((device.boxes, device.lines))
    kwargs = dict(source="control", target="core", parameter="gain", id="pp_gain")
    kwargs.update(overrides)
    with pytest.raises(ValueError, match=match):
        device.bind_gen_param(**kwargs)
    assert (device.boxes, device.lines) == before
