"""Runtime live.colors theme-bus generator (B1)."""

from m4l_builder.engines.live_theme import (
    LIVE_SKIN,
    live_colors_bus,
    live_theme_receiver,
    live_theme_state_dim,
)


def _texts(boxes):
    return [b["box"]["text"] for b in boxes]


def _lineset(lines):
    return {
        (lin["patchline"]["source"][0].split("_")[-1],
         lin["patchline"]["source"][1],
         lin["patchline"]["destination"][0].split("_")[-1],
         lin["patchline"]["destination"][1])
        for lin in lines
    }


def test_bus_emits_thisdevice_colors_route_prepend_send():
    boxes, lines = live_colors_bus([("lcd_control_fg", "activedialcolor", "dialcol")])
    texts = _texts(boxes)
    assert "live.thisdevice" in texts
    assert "live.colors" in texts
    assert "lcd_control_fg" in texts            # the query message
    assert "route lcd_control_fg" in texts
    assert "prepend activedialcolor" in texts
    assert "s ---dialcol" in texts


def test_bus_wiring_loadbang_and_themechange_requery():
    boxes, lines = live_colors_bus([("lcd_bg", "lcdbgcolor", "bg")])
    ls = _lineset(lines)
    # loadbang (thisdevice[0]) -> query message[0]
    assert ("thisdev", 0, "q0", 0) in ls
    # theme-change (colors[1]) -> re-query message[0]
    assert ("colors", 1, "q0", 0) in ls
    # query message -> colors[0]
    assert ("q0", 0, "colors", 0) in ls
    # colors[0] -> route -> prepend -> send
    assert ("colors", 0, "rt0", 0) in ls
    assert ("rt0", 0, "pre0", 0) in ls
    assert ("pre0", 0, "s0", 0) in ls


def test_bus_one_shared_source_many_specs():
    specs = [("lcd_control_fg", "activedialcolor", "dialcol"),
             ("lcd_bg", "lcdbgcolor", "bg"),
             ("surface_bg", "bgfillcolor", "panel")]
    boxes, lines = live_colors_bus(specs)
    texts = _texts(boxes)
    assert texts.count("live.thisdevice") == 1   # shared
    assert texts.count("live.colors") == 1       # shared
    assert texts.count("live.colors") == 1
    assert sum(t.startswith("route ") for t in texts) == 3
    assert sum(t.startswith("s ---") for t in texts) == 3


def test_receiver_subscribes_control_to_bus():
    boxes, lines = live_theme_receiver("dialcol", "obj-mydial", inlet=0)
    assert boxes[0]["box"]["text"] == "r ---dialcol"
    pl = lines[0]["patchline"]
    assert pl["source"][0].endswith("dialcol")
    assert pl["destination"] == ["obj-mydial", 0]


def test_live_skin_tokens_present():
    assert "lcd_control_fg" in LIVE_SKIN
    assert "lcd_bg" in LIVE_SKIN


def test_state_dim_uses_thisdevice_middle_outlet_and_both_tokens():
    boxes, lines = live_theme_state_dim(
        "accent", attrs=("activedialcolor", "activefgdialcolor"), id_prefix="ltdim")
    texts = _texts(boxes)
    assert "live.thisdevice" in texts and "sel 1 0" in texts
    assert "lcd_control_fg" in texts             # active accent query
    assert "lcd_control_fg_zombie" in texts      # dimmed (zombie) accent query
    assert "route lcd_control_fg lcd_control_fg_zombie" in texts
    assert "prepend activedialcolor" in texts and "prepend activefgdialcolor" in texts
    assert texts.count("s ---accent") == 2       # one send per attr
    ls = _lineset(lines)
    assert ("td", 1, "sel", 0) in ls             # MIDDLE outlet (1) = enabled/disabled
    assert ("sel", 0, "mact", 0) in ls           # 1 -> active accent
    assert ("sel", 1, "mzomb", 0) in ls          # 0 -> zombie accent
    assert ("rt", 0, "pre0", 0) in ls and ("rt", 1, "pre0", 0) in ls  # both tokens -> attr


def test_device_add_theme_bus_dim_wires_receiver():
    from m4l_builder import AudioEffect

    dev = AudioEffect("test", width=200, height=120)
    dev.add_dial("d", "Amt", [10, 10, 41, 35])
    res = dev.add_theme_bus_dim("accent", attrs=("activedialcolor",), targets=["d"])
    texts = [b["box"].get("text", "") for b in dev.boxes]
    assert "sel 1 0" in texts
    assert "r ---accent" in texts                # control auto-subscribed
    assert res["bus"] == "accent"
