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


def test_state_dim_uses_the_param_observer_not_thisdevice_middle_outlet():
    """The dim must track a runtime Activator click, not only the load state.

    This asserted ``live.thisdevice`` outlet 1 until 2026-08-01, on the strength
    of the Max reference wording. That outlet fires at LOAD ONLY, so the dim
    never actually happened when the user toggled the device — the test was
    locking in the bug. The Device-On parameter observer is the Live-verified
    source (Strip v9, 2026-07-01) and is what ``live_brand_dim`` has always used.
    """
    boxes, lines = live_theme_state_dim(
        "accent", attrs=("activedialcolor", "activefgdialcolor"), id_prefix="ltdim")
    texts = _texts(boxes)
    assert "live.observer" in texts and "live.path" in texts
    assert "path this_device parameters 0" in texts
    assert "sel 1 0" in texts
    assert "lcd_control_fg" in texts             # active accent query
    assert "lcd_control_fg_zombie" in texts      # dimmed (zombie) accent query
    assert "route lcd_control_fg lcd_control_fg_zombie" in texts
    assert "prepend activedialcolor" in texts and "prepend activefgdialcolor" in texts
    assert texts.count("s ---accent") == 2       # one send per attr
    ls = _lineset(lines)
    assert ("obs", 0, "t", 0) in ls              # observer -> t i i (float coercion)
    assert ("t", 0, "sel", 0) in ls              # coerced state -> selector
    assert ("td", 1, "sel", 0) not in ls         # NOT the load-only middle outlet
    assert ("sel", 0, "mact", 0) in ls           # 1 -> active accent
    assert ("sel", 1, "mzomb", 0) in ls          # 0 -> zombie accent
    assert ("rt", 0, "pre0", 0) in ls and ("rt", 1, "pre0", 0) in ls  # both tokens -> attr


def test_bypass_state_broadcasts_a_named_selector():
    """jsui inlet 0 is a message dispatcher — a bare int would hit msg_int."""
    from m4l_builder.engines.live_theme import live_bypass_state

    boxes, lines = live_bypass_state("devicestate", id_prefix="bypst")
    texts = _texts(boxes)
    assert "live.observer" in texts              # runtime-correct source
    assert "prepend set_device_active" in texts
    assert "s ---devicestate" in texts
    ls = _lineset(lines)
    assert ("t", 0, "pre", 0) in ls
    assert ("pre", 0, "s", 0) in ls


def test_device_add_bypass_dim_fans_to_every_target():
    from m4l_builder import AudioEffect
    from m4l_builder.engines.live_theme import BYPASS_DIM_JS

    # A minimal but CONTRACT-VALID v8ui — BYPASS_DIM_JS is a fragment to paste
    # into a real display script, not a standalone one.
    stub = ("mgraphics.init();\nmgraphics.relative_coords = 0;\n"
            "mgraphics.autofill = 0;\n"
            "function paint() { mgraphics.redraw(); }\n" + BYPASS_DIM_JS)
    dev = AudioEffect("byp", width=200, height=120)
    for name in ("disp_a", "disp_b"):
        dev.add_v8ui(name, [10, 10, 60, 40], js_code=stub,
                     js_filename=f"{name}.js")
    bus = dev.add_bypass_dim(["disp_a", "disp_b"])
    assert bus == "devicestate"
    texts = [b["box"].get("text", "") for b in dev.boxes]
    assert "r ---devicestate" in texts
    assert "prepend set_device_active" in texts
    fanned = {ln["patchline"]["destination"][0] for ln in dev.lines
              if ln["patchline"]["source"][0] == "bypdim_rx"}
    assert fanned == {"disp_a", "disp_b"}


def test_bypass_dim_js_handler_name_matches_the_default_selector():
    """The JS drop-in has to answer the message the bus actually sends."""
    from m4l_builder.engines.live_theme import BYPASS_DIM_JS

    assert "function set_device_active(" in BYPASS_DIM_JS
    assert "function bypass_alpha(" in BYPASS_DIM_JS


def test_device_add_theme_bus_dim_wires_receiver():
    from m4l_builder import AudioEffect

    dev = AudioEffect("test", width=200, height=120)
    dev.add_dial("d", "Amt", [10, 10, 41, 35])
    res = dev.add_theme_bus_dim("accent", attrs=("activedialcolor",), targets=["d"])
    texts = [b["box"].get("text", "") for b in dev.boxes]
    assert "sel 1 0" in texts
    assert "r ---accent" in texts                # control auto-subscribed
    assert res["bus"] == "accent"
