"""D4 viz bus: gen emitters + jsui base + device wiring."""

from m4l_builder import AudioEffect, find_v8ui_contract_issues
from m4l_builder.engines.buffer_viz import buffer_viz_js
from m4l_builder.gen_stateful import viz_declares, viz_poke_block
from m4l_builder.theme import GRAPHITE


def _box(device, box_id):
    for entry in device.boxes:
        box = entry.get("box", {})
        if box.get("id") == box_id:
            return box
    raise AssertionError(f"no box {box_id!r}")


class TestGenEmitters:
    def test_viz_declares_are_pure_declarations(self):
        decl = viz_declares("buf_a", "buf_b")
        assert "Buffer buf_a;" in decl and "Buffer buf_b;" in decl
        assert "History his_guiCout(0);" in decl
        # no executable statements (no assignment outside decls)
        assert "=" not in decl.replace("(0)", "")

    def test_viz_poke_block_is_counter_gated(self):
        block = viz_poke_block("poke(buf_a, 1, 0, 0);", refresh_ms=40.0)
        assert "wrap(his_guiCout + 1, 0, mstosamps(40.0))" in block
        assert "if (his_guiCout == 1)" in block
        assert "poke(buf_a, 1, 0, 0);" in block


class TestBufferVizJs:
    def test_contract_and_binding(self):
        js = buffer_viz_js(
            draw="var f = frames.demo; if (f) { }",
            buffers=[("demo", 64, 1)])
        assert find_v8ui_contract_issues(js) == []
        assert 'VIZ_KEYS = ["demo"]' in js
        assert "function set_buffers()" in js
        assert "new Buffer(name)" in js
        assert "poll_task.interval = 33" in js


class TestAddVizBus:
    def test_wiring(self):
        d = AudioEffect("viz", width=300, height=168, theme=GRAPHITE)
        d.add_newobj("g", "gen~ demo", numinlets=1, numoutlets=1,
                     outlettype=["signal"], patching_rect=[10, 400, 90, 20])
        d.add_v8ui("hero", [8, 8, 200, 152],
                   js_code=buffer_viz_js(draw="", buffers=[("demo", 64, 1)]),
                   js_filename="viz_demo_v1.js")
        ids = d.add_viz_bus([("buf_demo", 64, 1)], gen_box_id="g",
                            viz_box_id="hero")
        assert _box(d, ids["buffers"][0])["text"] == "buffer~ ---buf_demo -1 1 @samps 64"
        assert _box(d, ids["rebind"])["text"] == "buf_demo ---buf_demo"
        assert _box(d, ids["names"])["text"] == "set_buffers ---buf_demo"
        lines = [ln["patchline"] for ln in d.lines]
        assert any(pl["source"][0] == ids["rebind"] and pl["destination"][0] == "g"
                   for pl in lines)
        assert any(pl["source"][0] == ids["names"] and pl["destination"][0] == "hero"
                   for pl in lines)
        # right-first: rebind on t outlet 1, names on outlet 0
        assert any(pl["source"] == ["vizbus_t", 1] and pl["destination"][0] == ids["rebind"]
                   for pl in lines)
