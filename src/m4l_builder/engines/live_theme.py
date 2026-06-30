"""Runtime ``live.colors`` theme bus — re-tints native controls from the user's
actual Live skin, live (including on a light/dark theme switch).

THE #1 most-cited jewel from the commercial corpus (13 of 15 devices use
``live.colors``; AS_Console_1.02 alone has 19 instances). Premium devices never
bake colors at build time — they read the user's Live theme at load and broadcast
each color over a device-scoped ``---`` send bus, so every control tracks the skin.

Verified wiring (traced from SABROI AS Console, the real pattern — more nuanced
than a single route-dump): per color,

    live.thisdevice[0] (loadbang) ─┐
                                   ├─► message "<skin_token>" ─► live.colors[0]
    live.colors[1] (theme change) ─┘
    live.colors[0] ─► route <skin_token> ─► prepend <attr> ─► s ---<bus>

and each control subscribes with ``r ---<bus> -> control[inlet]`` (live.* objects
accept ``<attr> R G B A`` color-setting messages).

These are box/line generators (the engine convention): they return ``(boxes,
lines)`` for ``device.add_dsp(boxes, lines)``. NOTE: structurally verified against
the real device; a Live-verify that it actually re-tints on a skin change is a
queued follow-up.
"""

from ..objects import newobj, patchline

# Live theme skin-slot names exposed by live.colors (seen across the corpus).
LIVE_SKIN = (
    "lcd_control_fg",        # the LCD lit-digit / control foreground
    "lcd_control_fg_zombie",  # the dimmed (bypassed/zombie) foreground
    "lcd_bg",                # LCD readout field background
    "assignment_text_bg",
    "control_fg",
    "control_fg_zombie",
    "surface_bg",            # device panel background
    "control_selection",
)


def live_colors_bus(specs, *, id_prefix="ltheme", x=20, y=20):
    """Generate the runtime theme-bus DISTRIBUTOR.

    ``specs``: list of ``(skin_token, attr, bus)`` triples — broadcast the Live
    theme color named ``skin_token`` over ``s ---<bus>`` as an ``<attr> R G B A``
    message, (re-)sent on device load AND whenever the user changes the Live theme.
    Controls subscribe via :func:`live_theme_receiver`.

    One shared ``live.thisdevice`` + ``live.colors``; one query message + route +
    prepend + send per spec. Returns ``(boxes, lines)``.
    """
    p = id_prefix
    thisdev, colors = f"{p}_thisdev", f"{p}_colors"
    boxes = [
        newobj(thisdev, "live.thisdevice", numinlets=1, numoutlets=3,
               outlettype=["bang", "", ""], patching_rect=[x, y, 90, 20]),
        newobj(colors, "live.colors", numinlets=1, numoutlets=2,
               outlettype=["", ""], patching_rect=[x, y + 30, 70, 20]),
    ]
    lines = []
    yy = y + 70
    for i, (token, attr, bus) in enumerate(specs):
        msg, rt = f"{p}_q{i}", f"{p}_rt{i}"
        pre, snd = f"{p}_pre{i}", f"{p}_s{i}"
        cx = x + i * 120
        boxes += [
            newobj(msg, token, numinlets=2, numoutlets=1, maxclass="message",
                   patching_rect=[cx, yy, 80, 18]),
            newobj(rt, f"route {token}", numinlets=1, numoutlets=2,
                   outlettype=["", ""], patching_rect=[cx, yy + 30, 80, 20]),
            newobj(pre, f"prepend {attr}", numinlets=1, numoutlets=1,
                   outlettype=[""], patching_rect=[cx, yy + 60, 110, 20]),
            newobj(snd, f"s ---{bus}", numinlets=1, numoutlets=0,
                   patching_rect=[cx, yy + 90, 80, 20]),
        ]
        lines += [
            patchline(thisdev, 0, msg, 0),   # loadbang -> query
            patchline(colors, 1, msg, 0),    # theme-change bang -> re-query
            patchline(msg, 0, colors, 0),    # query the named color
            patchline(colors, 0, rt, 0),     # color out -> route (filters by token)
            patchline(rt, 0, pre, 0),        # stripped RGBA -> prepend attr
            patchline(pre, 0, snd, 0),       # "<attr> R G B A" -> send bus
        ]
    return boxes, lines


def live_theme_receiver(bus, target_id, *, inlet=0, id_prefix="ltheme_rx", x=20, y=20):
    """Generate ``r ---<bus> -> target_id[inlet]`` so a control re-tints live.

    Returns ``(boxes, lines)``.
    """
    rid = f"{id_prefix}_{bus}"
    boxes = [
        newobj(rid, f"r ---{bus}", numinlets=0, numoutlets=1,
               outlettype=[""], patching_rect=[x, y, 80, 20]),
    ]
    lines = [patchline(rid, 0, target_id, inlet)]
    return boxes, lines


def live_theme_state_dim(bus, *, attrs=("activedialcolor",),
                         active_token="lcd_control_fg",
                         zombie_token="lcd_control_fg_zombie",
                         id_prefix="ltdim", x=20, y=20):
    """Generate the bypass "zombie" DIM distributor — broadcasts the Live ACTIVE
    accent over ``s ---<bus>`` while the device is enabled, and the DIMMED accent
    when it is bypassed, so every control on ``bus`` greys out on bypass like a
    stock device (the second half of the J1 theme jewel).

    Grounded in the ``live.thisdevice`` Max reference: the **middle outlet (1)**
    sends ``1``/``0`` when the device is enabled/disabled. That selects which skin
    token is (re-)queried from ``live.colors``:

        live.thisdevice[1] (enabled 1/0) -> sel 1 0
            ├─1(enabled)  -> message "<active_token>"  ┐
            └─0(bypassed) -> message "<zombie_token>"  ┘ -> live.colors[0]
        live.colors[0] -> route <active_token> <zombie_token>
                        -> (either) -> prepend <attr> -> s ---<bus>   (per attr)

    ``attrs`` is the list of control color attributes to drive from the one accent
    (e.g. ``("activedialcolor", "activefgdialcolor")`` for a dial). Controls subscribe
    with :func:`live_theme_receiver`. Returns ``(boxes, lines)``.
    """
    p = id_prefix
    td, sl, m_a, m_z, col, rt = (f"{p}_td", f"{p}_sel", f"{p}_mact",
                                 f"{p}_mzomb", f"{p}_col", f"{p}_rt")
    boxes = [
        newobj(td, "live.thisdevice", numinlets=1, numoutlets=3,
               outlettype=["bang", "", ""], patching_rect=[x, y, 90, 20]),
        newobj(sl, "sel 1 0", numinlets=1, numoutlets=3,
               outlettype=["bang", "bang", ""], patching_rect=[x, y + 30, 60, 20]),
        newobj(m_a, active_token, numinlets=2, numoutlets=1, maxclass="message",
               patching_rect=[x, y + 60, 120, 18]),
        newobj(m_z, zombie_token, numinlets=2, numoutlets=1, maxclass="message",
               patching_rect=[x + 130, y + 60, 140, 18]),
        newobj(col, "live.colors", numinlets=1, numoutlets=2,
               outlettype=["", ""], patching_rect=[x, y + 90, 70, 20]),
        newobj(rt, f"route {active_token} {zombie_token}", numinlets=1,
               numoutlets=3, outlettype=["", "", ""], patching_rect=[x, y + 120, 210, 20]),
    ]
    lines = [
        patchline(td, 1, sl, 0),       # MIDDLE outlet = device enabled/disabled (1/0)
        patchline(sl, 0, m_a, 0),      # 1 -> query the active accent
        patchline(sl, 1, m_z, 0),      # 0 -> query the dimmed (zombie) accent
        patchline(m_a, 0, col, 0),
        patchline(m_z, 0, col, 0),
        patchline(col, 0, rt, 0),      # color out -> route (filters by token)
    ]
    for k, attr in enumerate(attrs):
        pre, snd = f"{p}_pre{k}", f"{p}_s{k}"
        boxes += [
            newobj(pre, f"prepend {attr}", numinlets=1, numoutlets=1,
                   outlettype=[""], patching_rect=[x, y + 150 + k * 30, 120, 20]),
            newobj(snd, f"s ---{bus}", numinlets=1, numoutlets=0,
                   patching_rect=[x, y + 180 + k * 30, 80, 20]),
        ]
        lines += [
            patchline(rt, 0, pre, 0),  # active-token color -> this attr
            patchline(rt, 1, pre, 0),  # zombie-token color -> same attr
            patchline(pre, 0, snd, 0),
        ]
    return boxes, lines
