"""Preset management objects for Max for Live devices."""

from .objects import newobj, patchline


def preset_manager(id_prefix: str, num_presets: int = 8) -> tuple:
    """Create a Max 'preset' object with a umenu for slot selection.

    The umenu populates with `num_presets` slots. Selecting a slot recalls that
    preset from the preset object.
    """
    p = id_prefix
    boxes = [
        newobj(f"{p}_preset", "preset", numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[30, 150, 60, 20]),
        newobj(f"{p}_menu", f"umenu {' '.join(str(i + 1) for i in range(num_presets))}",
               numinlets=1, numoutlets=3,
               outlettype=["", "", ""],
               patching_rect=[30, 120, 100, 20]),
    ]
    lines = [
        patchline(f"{p}_menu", 0, f"{p}_preset", 0),
    ]
    return (boxes, lines)


def add_preset_buttons(device, x: int, y: int, num_presets: int = 8) -> list:
    """Add save/load/prev/next buttons wired to a preset object on `device`.

    Adds the preset object itself plus four control buttons. Returns a list of
    all added box IDs.
    """
    preset_id = device.add_newobj(
        "preset_mgr", "preset",
        numinlets=1, numoutlets=3,
        patching_rect=[x, y + 40, 60, 20],
    )

    btn_w, btn_h = 40, 20
    gap = 5
    buttons = [("preset_save", "save"), ("preset_load", "load"),
               ("preset_prev", "prev"), ("preset_next", "next")]

    btn_ids = []
    for idx, (bid, label) in enumerate(buttons):
        btn_id = device.add_button(bid, label,
                                   [x + idx * (btn_w + gap), y, btn_w, btn_h])
        device.add_line(btn_id, 0, preset_id, 0)
        btn_ids.append(btn_id)

    return [preset_id] + btn_ids
