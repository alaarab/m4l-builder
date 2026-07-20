"""Recipes: layout — split out of recipes.py; re-exported by m4l_builder.recipes."""

from .stages import stage_result


def two_panel_strip(device, id_prefix, *, main_width=174, side_width=56, height=167,
                    gap=2, bgcolor=None, side_bgcolor=None, border=1,
                    bordercolor=None, rounded=0):
    """Two-panel channel-strip SHELL — a premium channel-strip grammar: a wide MAIN
    panel for the primary controls + a narrow SIDE column for toggles/meters.

    Geometry is grounded in measured premium-device proportions: main panel ``[0,0,174,167]`` + side
    panel ``[176,0,55,167]`` (gap 2). The device width should be
    ``main_width + gap + side_width`` (231 by default). Fill the panels with
    :func:`dial_label_cell` cells, a DSP module via
    ``device.add_bpatcher_module`` (F3), side-column toggles, etc.; re-tint the
    whole frame at runtime with ``device.add_theme_bus`` (B1).

    Build-time ``bgcolor`` / ``side_bgcolor`` are placeholders (the theme bus wins
    when ``follow_live``). Returns a StageResult whose mapping carries the panel ids
    plus the content rects the caller lays out into: ``main_rect`` / ``side_rect``
    (the panels) and ``main_content`` / ``side_content`` (inset by 4 px).
    """
    p = id_prefix
    bgcolor = bgcolor or [0.16, 0.16, 0.17, 1.0]
    side_bgcolor = side_bgcolor or [0.12, 0.12, 0.13, 1.0]
    inset = 4
    side_x = main_width + gap
    main_rect = [0, 0, main_width, height]
    side_rect = [side_x, 0, side_width, height]

    main_id = device.add_panel(f"{p}_main_panel", main_rect, bgcolor=bgcolor,
                               border=border, bordercolor=bordercolor, rounded=rounded)
    side_id = device.add_panel(f"{p}_side_panel", side_rect, bgcolor=side_bgcolor,
                               border=border, bordercolor=bordercolor, rounded=rounded)

    return stage_result(
        {
            "main_panel": main_id,
            "side_panel": side_id,
            "main_rect": main_rect,
            "side_rect": side_rect,
            "main_content": [inset, inset, main_width - 2 * inset, height - 2 * inset],
            "side_content": [side_x + inset, inset, side_width - 2 * inset,
                             height - 2 * inset],
            "total_width": side_x + side_width,
            "height": height,
        },
        name="two_panel_strip",
    )


def dial_label_cell(device, id_prefix, param_name, rect, *, label=None,
                    min_val=0.0, max_val=100.0, initial=0.0, unitstyle=1,
                    label_h=14, gap=1, **dial_kwargs):
    """A dial with a caption directly below it — a premium channel-strip control cell.

    ``rect`` is the DIAL's ``[x, y, w, h]``; a ``live.comment`` label is placed just
    below (``label`` text, defaulting to ``param_name``). The dial shows its live
    value in Live's native readout. Extra ``dial_kwargs`` pass through to
    ``device.add_dial`` (e.g. ``annotation_name``, ``units``). Returns a StageResult
    with ``dial`` and ``label`` ids and the cell's overall ``rect``.
    """
    p = id_prefix
    text = label or param_name
    # The caption is the comment BELOW; force showname=0 so the dial does not ALSO
    # draw its parameter name inside the knob (the factory default is showname=1) and
    # double the label. Caller can still override via dial_kwargs.
    dial_id = device.add_dial(
        f"{p}_dial", param_name, rect, min_val=min_val, max_val=max_val,
        initial=initial, unitstyle=unitstyle,
        showname=dial_kwargs.pop("showname", 0),
        annotation_name=dial_kwargs.pop("annotation_name", text), **dial_kwargs,
    )
    lx, ly = rect[0], rect[1] + rect[3] + gap
    label_id = device.add_comment(f"{p}_label", [lx, ly, rect[2], label_h], text)

    return stage_result(
        {
            "dial": dial_id,
            "label": label_id,
            "rect": [rect[0], rect[1], rect[2], rect[3] + gap + label_h],
        },
        name="dial_label_cell",
        params={param_name: device.parameter(dial_id)},
    )


def dial_value_cell(device, id_prefix, param_name, dial_rect, *, label=None,
                    min_val=0.0, max_val=100.0, initial=0.0, unitstyle=1,
                    accent=None, fill=None, label_color=None,
                    label_h=10, label_gap=1, label_fontsize=7.5,
                    label_fontname="Ableton Sans Medium", appearance=0,
                    **dial_kwargs):
    """The premium channel-strip atomic control cell: an uppercase caption
    ABOVE a native ``live.dial`` whose OWN persistent value reads out BELOW the knob.

    Grounded in measured premium-device proportions: its dials are 41x35, ``showname=0``, with an accent
    ring (``activedialcolor``) + grey value arc (``activefgdialcolor``) and rely on
    the native value display (``shownumber=1`` — the Max ``live.dial`` reference:
    "shownumber toggles the display of the parameter value"). NO ``paint_control``:
    a render-only painter fills the dial rect and HIDES that native value (the dim,
    value-less knobs we shipped). ``dial_rect`` is the DIAL's ``[x, y, w, h]``; the
    caption is placed just above it.

    ``accent`` -> ``activedialcolor`` (the lit ring, the device accent); ``fill`` ->
    ``activefgdialcolor`` (the value arc; defaults to a neutral grey like premium channel-strip devices).
    Extra ``dial_kwargs`` pass through to ``device.add_dial`` (``parameter_exponent``,
    ``annotation_name`` …). Returns a StageResult with ``dial``/``label`` ids, the
    overall cell ``rect`` and the param.
    """
    p = id_prefix
    text = label if label is not None else param_name
    lx = dial_rect[0]
    ly = dial_rect[1] - label_h - label_gap
    cap_kwargs = dict(fontsize=label_fontsize, fontname=label_fontname, justification=1)
    if label_color is not None:
        cap_kwargs["textcolor"] = list(label_color)
    label_id = device.add_comment(
        f"{p}_cap", [lx, ly, dial_rect[2], label_h], text, **cap_kwargs,
    )
    dk = dict(showname=0, shownumber=1, appearance=appearance)
    dk["activedialcolor"] = list(accent) if accent is not None else None
    dk["activefgdialcolor"] = list(fill) if fill is not None else [0.59, 0.59, 0.59, 1.0]
    dk = {k: v for k, v in dk.items() if v is not None}
    dk.update(dial_kwargs)
    annotation = dk.pop("annotation_name", text)
    dial_id = device.add_dial(
        f"{p}_dial", param_name, dial_rect, min_val=min_val, max_val=max_val,
        initial=initial, unitstyle=unitstyle, annotation_name=annotation, **dk,
    )
    return stage_result(
        {
            "dial": dial_id,
            "label": label_id,
            "rect": [lx, ly, dial_rect[2], (dial_rect[1] + dial_rect[3]) - ly],
        },
        name="dial_value_cell",
        params={param_name: device.parameter(dial_id)},
    )


def stacked_panels(device, id_prefix, tab_param, panel_ids, *, rect, labels=None,
                   ghost=False, x=30, y=400):
    """Tabbed panel sections (C6): a ``live.tab`` selects which of N pre-added
    panels is shown, swapping them IN PLACE via ``thispatcher`` script show/hide.

    ``panel_ids`` are the scripting names (``varname``) of the panels the caller
    already added at the SAME content rect (e.g. ``add_bpatcher_module`` modules or
    panels). On every tab change the recipe hides ALL panels then shows the selected
    one (a ``t i b`` fork fires the hide bang first, then the show index), so exactly
    one panel is visible. ``ghost=True`` makes the tab strip itself invisible
    (alpha-0) — a hidden selector you drive from elsewhere. ``rect`` is the tab
    strip's ``[x,y,w,h]``. Returns ``{tab, content_rect}``.

    NOTE: the script show/hide wiring is structurally grounded in the framework's
    flyout mechanism; the actual swap is Live-verified when a device first uses it.
    """
    p = id_prefix
    labels = list(labels or [str(i + 1) for i in range(len(panel_ids))])
    tab_kwargs = {}
    if ghost:
        clear = [0.0, 0.0, 0.0, 0.0]
        tab_kwargs = dict(bgcolor=clear, bgoncolor=clear,
                          textcolor=clear, textoncolor=clear)
    tab_id = device.add_tab(f"{p}_tab", tab_param, rect, options=labels, **tab_kwargs)

    fork = device.add_newobj(
        f"{p}_fork", "t i b", numinlets=1, numoutlets=2,
        outlettype=["int", "bang"], patching_rect=[x, y, 50, 20],
    )
    sel = device.add_newobj(
        f"{p}_sel", "sel " + " ".join(str(i) for i in range(len(panel_ids))),
        numinlets=1, numoutlets=len(panel_ids) + 1,
        outlettype=["bang"] * len(panel_ids) + [""],
        patching_rect=[x, y + 30, 160, 20],
    )
    thisp = device.add_newobj(
        f"{p}_thisp", "thispatcher", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 130, 80, 20],
    )
    device.add_line(tab_id, 0, fork, 0)
    device.add_line(fork, 0, sel, 0)            # index (fires 2nd) -> show selected
    for i, pid in enumerate(panel_ids):
        hide_msg = device.add_newobj(
            f"{p}_hide{i}", f"script hide {pid}", numinlets=2, numoutlets=1,
            maxclass="message", patching_rect=[x + 200, y + 30 + i * 22, 120, 18],
        )
        device.add_line(fork, 1, hide_msg, 0)   # hide bang (fires 1st) -> hide all
        device.add_line(hide_msg, 0, thisp, 0)
        show_msg = device.add_newobj(
            f"{p}_show{i}", f"script show {pid}", numinlets=2, numoutlets=1,
            maxclass="message", patching_rect=[x + i * 70, y + 70, 90, 18],
        )
        device.add_line(sel, i, show_msg, 0)
        device.add_line(show_msg, 0, thisp, 0)

    return stage_result(
        {"tab": tab_id, "content_rect": list(rect)},
        name="stacked_panels",
        params={tab_param: device.parameter(tab_id)},
    )


def bypass_wrapper(device, id_prefix, *, toggle, wet_source, dry_source=None,
                   audio_out="obj-plugout", channels=(("l", 0), ("r", 1)),
                   sel_x=110, y=300, ch_dx=200, add1_x=420):
    """Hard-bypass N parallel signal paths (stereo L/R by default) with ONE
    shared latching toggle: a ``selector~ 2 1`` per channel picks WET (inlet 1)
    or DRY (inlet 2), driven by a ``+ 1`` shim off the toggle (Max's
    ``selector~`` control inlet is 1-indexed, so toggle 0/1 -> control 1/2).
    This exact shape — ``+ 1`` feeding N ``selector~ 2 1``s — was hand-wired
    identically across five audio-effect devices' bypass stages.

    ``toggle`` is an EXISTING box id (the device's own bypass button/param;
    this recipe does not build one — every real adopter already has its
    toggle from elsewhere in its layout). ``wet_source`` / ``dry_source`` are
    ``(channel_label, channel_index) -> (box_id, outlet)`` callables selecting
    each channel's feed; ``dry_source`` defaults to the device's raw input
    (``obj-plugin`` at ``channel_index``) — pass your own when the dry tap
    isn't the raw input (e.g. a lookahead-delayed tap). Each channel's
    selector output is wired to ``audio_out`` at its channel index. Returns a
    StageResult with the per-channel ``selector`` ids (keyed by channel label)
    and the ``shim`` (``+ 1``) id.

    NOTE: this owns one contiguous per-channel loop + a trailing shim, so it
    only fits devices whose selector creation isn't interleaved with OTHER,
    unrelated per-channel box creation (m4l_builder's boxes/lines are plain
    insertion-ordered lists — reproducing a different interleaving would
    require either reordering output or bolting injection hooks onto this
    recipe for one-off callers, neither of which is worth it here).
    """
    p = id_prefix
    dry_source = dry_source or (lambda ch, ci: ("obj-plugin", ci))
    sel_ids = {}
    for ch, ci in channels:
        sel_id = f"{p}_sel_{ch}"
        sel_ids[ch] = sel_id
        device.add_newobj(sel_id, "selector~ 2 1", numinlets=3, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[sel_x + ci * ch_dx, y, 80, 20])
        wsrc, wout = wet_source(ch, ci)
        device.add_line(wsrc, wout, sel_id, 1)
        dsrc, dout = dry_source(ch, ci)
        device.add_line(dsrc, dout, sel_id, 2)
    for ch, ci in channels:
        device.add_line(sel_ids[ch], 0, audio_out, ci)
    shim_id = f"{p}_add1"
    device.add_newobj(shim_id, "+ 1", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[add1_x, y, 40, 20])
    device.add_line(toggle, 0, shim_id, 0)
    for ch, _ci in channels:
        device.add_line(shim_id, 0, sel_ids[ch], 0)

    return stage_result({"selector": sel_ids, "shim": shim_id}, name="bypass_wrapper")


def switchable_bank(device, id_prefix, options, *, tab_param=None, tab_rect=None,
                    x=30, y=30):
    """A/B / multi-algorithm signal bank (F4): a ``selector~ N 1`` whose active
    input is chosen by a ``live.tab`` parameter, with a ``+ 1`` shim (the tab is
    0-indexed, ``selector~`` is 1-indexed; 0 = silence).

    ``options`` are the tab labels (one per bank input). Wire each candidate signal
    into ``in_0 .. in_{N-1}``; ``audio_out`` carries the selected one. Returns the
    tab + selector ids and the per-input + output ports.
    """
    p = id_prefix
    n = len(options)
    tab_param = tab_param or f"{p}_select"
    tab_id = device.add_tab(f"{p}_tab", tab_param, tab_rect or [x, y, 40 * n, 18],
                            options=list(options))
    shim = device.add_newobj(
        f"{p}_shim", "+ 1", numinlets=2, numoutlets=1, outlettype=[""],
        patching_rect=[x, y + 30, 50, 20],
    )
    sel = device.add_newobj(
        f"{p}_sel", f"selector~ {n} 1", numinlets=n + 1, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 60, 30 + 30 * n, 20],
    )
    device.add_line(tab_id, 0, shim, 0)
    device.add_line(shim, 0, sel, 0)

    ports = {f"in_{i}": device.box(sel).inlet(i + 1) for i in range(n)}
    ports["audio_out"] = device.box(sel).outlet(0)
    return stage_result(
        {"tab": tab_id, "selector": sel},
        name="switchable_bank",
        params={tab_param: device.parameter(tab_id)},
        ports=ports,
    )


def modulator_slot_component(device, *, accent, text_color=None,
                             dim_color=None, self_map_guard=None,
                             debounce_ms=20, width=240, height=17,
                             normalized=0, js_filename="lom_mapper.js",
                             source_enum=None, source_glyphs=None,
                             reveal=False, mode_switch=False, add_chip=False,
                             mode_colors=None, unmap_button=False,
                             value_bar=False, row_color=False,
                             uplink_pname=False, uplink_dname=False,
                             ratio_lcd=False):
    """The E2/E3 mapping slot — ONE ``#1``-parameterized Subpatcher to stamp N
    times via :meth:`Device.add_component_rack` (the measured slot pattern, F2+E2).

    Presentation is the STOCK-MODULATOR ROW (Live 12 LFO / Envelope Follower:
    the whole mapping UI is one ~15px strip — Map button, target chip, inline
    percent values; knobs are for the device's own DSP only):
    ``MAP | target readout | Depth% | Min% | Max% | BI`` at ``width x height``
    (default 240x17). Stack N stamped rows in a single narrow column and put
    ONE shared caption header above the stack (the slot has no captions).

    Each stamped instance is a full click-to-map modulation lane:
      MAP (``#1 Map``) arms the ``lom_mapper`` v8 script's selected-parameter
      observer; picking a param in Live attaches the slot's retargetable sink
      (``dsp.live.retargetable_param_sink`` — live.remote~/live.modulate~ with
      the id on the RIGHT inlet via deferlow); the target's name lands in the
      readout and its native min/max uplink to the ctl bus for gen-side scaling.

    I/O (``#1`` = instance number, standalone tokens only — Live-proven:
    ``#1`` EMBEDDED mid-symbol like ``depth_#1``/``msig_r#1`` stays LITERAL).
    Everything crosses the bpatcher boundary by inlet/outlet, the
    corpus-verbatim discipline (this pattern's slot feeds its sinks from inlet
    boxes and talks to the parent through outlets). Inlets by x-position:
      inlet 0: mapper messages (``settarget``/``setid``/``unmap``/``map``,
               and the parent's ``announce N`` fan-back for exclusivity);
      inlet 1: live.remote~ signal (native units unless ``normalized=1``);
      inlet 2: live.modulate~ signal (0..1 relative).
    Outlet 0 — the ctl uplink route bus, UNINDEXED keys (each stamp has its
    own outlet patchcord, so the parent knows the slot topologically):
    ``depth v``, ``umin v``, ``umax v``, ``bipolar v`` (slot params),
    ``tmin v``/``tmax v`` (target native range) and ``announce N`` (MAP armed
    — fan it back into EVERY slot's inlet 0 so the other slots stand down).

    Optional extensions (both default OFF — Orbit's call stays byte-identical):
      ``source_enum``: list of source names — adds a ``#1 Source`` ``live.menu``
        at the row start (each stamped lane picks its OWN source) plus a
        ``source v`` key on the ctl uplink bus. Row becomes
        ``SRC | MAP | target | Depth% | Min% | Max% | BI`` (width ~300).
      ``reveal``: the reveal page idiom — the slot listens for ``lanes N`` on
        inlet 0 and HIDES ITSELF (message ``hidden $1`` to its own
        ``thispatcher``, which targets the bpatcher box in the parent) when
        ``N < #1``. Fan ``lanes <count>`` into every slot's inlet 0 alongside
        ``announce`` and a Lanes param + "+" button give the stock-LFO
        progressive reveal, all inline. (Deconstructed from
        a randomizer: 8 same-rect pages hidden/shown exactly this way.)

    Registers the mapper source as a device js asset (content-addressed).
    Returns ``(subpatcher, ids)``.
    """
    from .dsp import retargetable_param_sink
    from .engines.design_system import js_sidecar_name
    from .engines.lom_mapper import DEFAULT_SELF_MAP_GUARD, lom_mapper_js
    from .objects import newobj
    from .parameters import ParameterSpec
    from .subpatcher import Subpatcher
    from .ui import live_text, number_box, textedit

    guard = self_map_guard or DEFAULT_SELF_MAP_GUARD
    tx = list(text_color) if text_color else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    acc = list(accent)

    js_code = lom_mapper_js(self_map_guard=guard, debounce_ms=debounce_ms)
    fname = js_sidecar_name(js_filename, js_code)
    device.register_asset(fname, js_code, asset_type="TEXT", category="js")

    sub = Subpatcher("modslot")
    # ---- UI: ONE tight stock-modulator row (compact density, no headers) ----
    # When a source_enum is given the lane leads with a clickable SHAPE ICON
    # (replaces the 52px text dropdown AND the column header — the parked menu
    # stays the automatable param). Row geometry ported from
    # the randomizer: 15-16px controls, ~222px total, self-documenting.
    icon = bool(source_enum and source_glyphs)
    if source_enum:
        from .ui import menu as _live_menu
        # The Source enum is the automatable param. In icon mode the menu is
        # PARKED offscreen and the glyph drives/reads it; else it shows inline.
        menu_rect = [900, 900, 1, 1] if icon else [0, 1, 52, 15]
        sub.add_box(_live_menu(
            "slot_source", "#1 Source", menu_rect,
            options=list(source_enum), fontsize=7.5,
            bgcolor=[0.16, 0.16, 0.18, 1.0], textcolor=tx, bgoncolor=acc,
            annotation="This lane's modulation source — each lane can run a "
                       "different generator.",
            parameter=ParameterSpec(name="#1 Source", shortname="#1 Source",
                                    minimum=0, maximum=len(source_enum) - 1,
                                    enum=list(source_enum), parameter_type=2,
                                    initial=0, initial_enable=True,
                                    linknames=1)))
    if icon:
        from .engines.shape_icon import shape_icon_js
        from .jsui_contract import validate_jsui_contract as _vjc
        # classic-jsui box: the contract rejects v8ui pointer handlers (the
        # dead-click class — the shape icon shipped unclickable once).
        ic_code = _vjc(shape_icon_js(shapes=list(source_glyphs), accent=acc))
        ic_fname = js_sidecar_name("shape_icon.js", ic_code)
        device.register_asset(ic_fname, ic_code, asset_type="TEXT",
                              category="js")
        sub.add_box({"box": {
            "id": "slot_shape_ui", "maxclass": "jsui",
            "jsui_maxclass": "jsui", "filename": ic_fname,
            "numinlets": 1, "numoutlets": 1, "outlettype": [""],
            "parameter_enable": 0, "presentation": 1, "border": 0,
            "presentation_rect": [1, 1, 15, 15],
            "patching_rect": [1, 200, 15, 15]}})
        MAP_X, PNAME_X, DEP_X, MIN_X, MAX_X, BI_X = 18, 46, 114, 148, 178, 208
    else:
        MAP_X, PNAME_X, DEP_X, MIN_X, MAX_X, BI_X = 0, 31, 96, 135, 174, 213
    # value_bar (catalog #21, Rnd Gen): a 5px live-output meter at the row's
    # LEFT edge — everything else shifts right 7px.
    if value_bar and icon:
        raise ValueError("modulator_slot_component: value_bar with "
                         "source_glyphs icon mode is not supported (both "
                         "claim the row's left edge)")
    BAR_SHIFT = 7 if value_bar else 0
    MAP_X += BAR_SHIFT
    PNAME_X += BAR_SHIFT
    DEP_X += BAR_SHIFT
    MIN_X += BAR_SHIFT
    MAX_X += BAR_SHIFT
    BI_X += BAR_SHIFT
    if value_bar:
        sub.add_box({"box": {
            "id": "slot_bar", "maxclass": "multislider", "contdata": 1,
            "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
            "parameter_enable": 0, "ignoreclick": 1, "setminmax": [0.0, 1.0],
            "slidercolor": acc, "bgcolor": [0.06, 0.06, 0.08, 1.0],
            "presentation": 1,
            "presentation_rect": [BAR_SHIFT - 7, 1, 5, 15],
            "patching_rect": [560, 200, 5, 15]}})
        sub.add_newobj("slot_bar_snap", "snapshot~ 50", numinlets=2,
                       numoutlets=1, outlettype=["float"],
                       patching_rect=[560, 170, 80, 20])
    sub.add_box(live_text(
        "slot_map", "#1 Map", [MAP_X, 1, 26, 15], text_on="MAP", text_off="MAP",
        mode=1, fontsize=7.0, bgoncolor=acc, textcolor=dim,
        annotation="When Map is on, the next Live parameter you click becomes "
                   "this lane's target.",
        parameter=ParameterSpec(name="#1 Map", shortname="#1 Map",
                                minimum=0, maximum=1, enum=["MAP", "MAP"],
                                parameter_type=2, initial=0,
                                initial_enable=True, linknames=1)))
    sub.add_box(textedit(
        "slot_pname", [PNAME_X, 2, 66, 13], text="—", fontsize=8.0,
        textcolor=tx, bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    # 0..100 ranges so unitstyle=5 reads "100 %" like the stock modulators
    # (consumers scale by 0.01 — poly_mod_engine does it inside gen)
    for nid, pname, nx, nw, init in (("slot_depth", "#1 Depth", DEP_X, 32, 100.0),
                                     ("slot_umin", "#1 Min", MIN_X, 28, 0.0),
                                     ("slot_umax", "#1 Max", MAX_X, 28, 100.0)):
        sub.add_box(number_box(
            nid, pname, [nx, 1, nw, 15], min_val=0.0, max_val=100.0,
            initial=init, unitstyle=5, lcdcolor=acc,
            parameter=ParameterSpec(name=pname, shortname=pname,
                                    minimum=0.0, maximum=100.0, initial=init,
                                    initial_enable=True, linknames=1)))
    sub.add_box(live_text(
        "slot_bipolar", "#1 Bipolar", [BI_X, 1, 15, 15], text_on="BI",
        text_off="BI", mode=1, fontsize=6.5, bgoncolor=acc, textcolor=dim,
        annotation="Bipolar — modulate above AND below the target's current "
                   "value (centred), rather than only upward.",
        parameter=ParameterSpec(name="#1 Bipolar", shortname="#1 Bipolar",
                                minimum=0, maximum=1, enum=["OFF", "ON"],
                                parameter_type=2, initial=0,
                                initial_enable=True, linknames=1)))
    # ---- optional Remote/Mod switch + "+" add chip (catalog #15/#16) --------
    # corpus/Live-12 grammar: orange = Remote (live.remote~ takeover, user
    # loses the dial), teal = Mod (live.modulate~ grey-ring, additive around
    # the dial). The chip drives the retarget sink's mode inlet, which
    # hot-swaps the stored id between sinks (corpus-verbatim re-emit).
    RM_X = BI_X + 17
    ADD_X = RM_X + (17 if mode_switch else 0)
    UN_X = ADD_X + (17 if add_chip else 0)
    RA_X = UN_X + (15 if unmap_button else 0)
    if ratio_lcd:
        # catalog #29 (MEQ8): mapping-with-math — a per-row multiplier LCD
        # ("x 5.04"); engines consume the `ratio v` ctl uplink and multiply
        # the lane signal before this row's sink (target = source × ratio).
        sub.add_box(number_box(
            "slot_ratio", "#1 Ratio", [RA_X, 1, 34, 15], min_val=0.01,
            max_val=100.0, initial=1.0, lcdcolor=acc,
            parameter=ParameterSpec(name="#1 Ratio", shortname="#1 Ratio",
                                    minimum=0.01, maximum=100.0,
                                    initial=1.0, initial_enable=True,
                                    exponent=3.0, linknames=1,
                                    units="x %.2f", unitstyle=9)))
    if unmap_button:
        # ✗-in-a-chip (catalog #14): NON-param clickable — a message box whose
        # click fires a second "unmap" message into the mapper js (the same
        # verb the parent's programmatic path uses).
        sub.add_box({"box": {
            "id": "slot_x", "maxclass": "message", "text": "✗",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "fontsize": 8.0, "textjustification": 1,
            "presentation": 1, "presentation_rect": [UN_X, 1, 13, 15],
            "patching_rect": [560, 260, 30, 20]}})
        sub.add_box({"box": {
            "id": "slot_x_un", "maxclass": "message", "text": "unmap",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [560, 290, 50, 20]}})
    if mode_switch:
        rm_remote, rm_mod = mode_colors or ([0.96, 0.62, 0.20, 1.0],
                                            [0.05, 0.76, 0.83, 1.0])
        sub.add_box(live_text(
            "slot_mode", "#1 RM", [RM_X, 1, 15, 15], text_on="M",
            text_off="R", mode=1, fontsize=6.5,
            bgoncolor=list(rm_mod), textcolor=list(rm_remote),
            annotation="Remote (R): this lane TAKES OVER the target — Live "
                       "shows the mapped hand. Mod (M): Live-12-style grey-"
                       "ring modulation AROUND the dial; the user keeps "
                       "control.",
            parameter=ParameterSpec(name="#1 RM", shortname="#1 RM",
                                    minimum=0, maximum=1, enum=["R", "M"],
                                    parameter_type=2, initial=0,
                                    initial_enable=True, linknames=1)))
    if add_chip:
        sub.add_box(live_text(
            "slot_addc", "#1 Add", [ADD_X, 1, 15, 15], text_on="+",
            text_off="+", mode=1, fontsize=7.5, bgoncolor=acc, textcolor=dim,
            annotation="Additive stacking — this lane SUMS with other lanes "
                       "on the same target instead of replacing them (engine-"
                       "side; consumed from the ctl uplink like Bipolar).",
            parameter=ParameterSpec(name="#1 Add", shortname="#1 Add",
                                    minimum=0, maximum=1, enum=["OFF", "ON"],
                                    parameter_type=2, initial=0,
                                    initial_enable=True, linknames=1)))
    if icon:
        # glyph <-> parked menu two-way: menu value echoes to the icon
        # (display), the icon's click emits the next index into the menu
        # (which sets the automatable param + drives the source uplink).
        sub.add_line("slot_source", 0, "slot_shape_ui", 0)
        sub.add_line("slot_shape_ui", 0, "slot_source", 0)
    # ---- mapper script + sink ----------------------------------------------
    # bpatcher inlet 0 -> js: the programmatic hook (settarget/setid/unmap
    # from the parent device — the headless-proof and preset-restore path)
    sub.add_box({"box": {
        "id": "slot_in", "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
        "outlettype": [""], "patching_rect": [4, 340, 25, 25],
        "comment": "mapper messages (settarget/setid/unmap/map)"}})
    sub.add_box(newobj(
        "slot_js", f"v8 {fname} #1", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[30, 400, 180, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0}))
    # slot_in fans out to several taps (enable/rowcolor/lanes/page routes) that
    # own those selectors; gate the v8 tap so only the mapper messages it
    # actually handles reach it. route's reject outlet (2) passes the whole
    # original message through, so map/unmap/setid/settarget/announce/extunmap
    # dispatch is unchanged; "enable"/"rowcolor" no longer hit the js (they are
    # already handled by slot_en_route/slot_rc_route) -> no "no function" errors.
    sub.add_newobj("slot_js_gate", "route enable rowcolor", numinlets=1,
                   numoutlets=3, outlettype=["", "", ""],
                   patching_rect=[220, 370, 140, 20])
    sub.add_line("slot_in", 0, "slot_js_gate", 0)
    sub.add_line("slot_js_gate", 2, "slot_js", 0)
    sink_boxes, sink_lines = retargetable_param_sink(
        "slot_sink", normalized=normalized)
    sub.add_dsp(sink_boxes, sink_lines)
    # signal delivery is by bpatcher INLET (corpus-verbatim: the
    # mapping slot feeds live.remote~/live.modulate~ from inlet boxes, never
    # send~/receive~ across the bpatcher boundary) — inlet order is by
    # x-position: 0 = mapper messages, 1 = remote signal, 2 = modulate signal
    sub.add_box({"box": {
        "id": "slot_rsig_r", "maxclass": "inlet", "numinlets": 0,
        "numoutlets": 1, "outlettype": [""],
        "patching_rect": [200, 340, 25, 25],
        "comment": "remote signal (native units)"}})
    sub.add_box({"box": {
        "id": "slot_rsig_m", "maxclass": "inlet", "numinlets": 0,
        "numoutlets": 1, "outlettype": [""],
        "patching_rect": [240, 340, 25, 25],
        "comment": "modulate signal (0..1 relative)"}})
    # ---- lane enable release (hunt #61) --------------------------------------
    # `enable 0|1` from the parent (the lane On toggle): OFF routes `id 0`
    # through the sink GATE's data inlet — the same cross-detach machinery the
    # R/M mode switch uses — so the ACTIVE sink releases its target instead of
    # a Remote-mode lane pinning it at the window Min forever; ON re-bangs
    # zl.reg to re-emit the stored id down the current path (mapping restored,
    # nothing forgotten). Mode-aware for free: the gate always points at the
    # currently-selected sink.
    sub.add_newobj("slot_en_route", "route enable", numinlets=1, numoutlets=2,
                   outlettype=["", ""], patching_rect=[520, 340, 90, 20])
    sub.add_newobj("slot_en_sel", "sel 0 1", numinlets=1, numoutlets=3,
                   outlettype=["bang", "bang", ""],
                   patching_rect=[520, 365, 60, 20])
    sub.add_box({"box": {
        "id": "slot_en_id0", "maxclass": "message", "text": "id 0",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [520, 390, 40, 20]}})
    sub.add_line("slot_in", 0, "slot_en_route", 0)
    sub.add_line("slot_en_route", 0, "slot_en_sel", 0)
    sub.add_line("slot_en_sel", 0, "slot_en_id0", 0)
    sub.add_line("slot_en_id0", 0, "slot_sink_gate", 1)
    sub.add_line("slot_en_sel", 1, "slot_sink_reg", 0)

    # ---- status route bus ----------------------------------------------------
    sub.add_newobj("slot_route",
                   "route mapped min max pname dname path flash announce",
                   numinlets=1, numoutlets=9,
                   outlettype=["", "", "", "", "", "", "", "", ""],
                   patching_rect=[30, 430, 300, 20])
    sub.add_box({"box": {
        "id": "slot_seton", "maxclass": "message", "text": "set $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [330, 460, 50, 20]}})
    sub.add_box({"box": {
        "id": "slot_extunmap", "maxclass": "message", "text": "extunmap",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [30, 520, 70, 20]}})
    # ---- uplinks. Keys are UNINDEXED: `#1` embedded mid-symbol (depth_#1)
    # does NOT substitute (Live-proven — only standalone #1 tokens and
    # longname-leading #1 resolve), and no index is needed anyway: each
    # stamped slot has its own outlet patchcord, so the parent knows the
    # slot topologically and stamps literal indices at build time.
    ups = [("slot_up_depth", "prepend depth", "slot_depth", 0),
           ("slot_up_umin", "prepend umin", "slot_umin", 0),
           ("slot_up_umax", "prepend umax", "slot_umax", 0),
           ("slot_up_bip", "prepend bipolar", "slot_bipolar", 0),
           ("slot_up_tmin", "prepend tmin", "slot_route", 1),
           ("slot_up_tmax", "prepend tmax", "slot_route", 2)]
    for k, (uid, text, src, srcout) in enumerate(ups):
        sub.add_newobj(uid, text, numinlets=1, numoutlets=1, outlettype=[""],
                       patching_rect=[400, 400 + 30 * k, 130, 20])
        sub.add_line(src, srcout, uid, 0)
    # the ctl uplink leaves by OUTLET (--- does not cross the embed boundary)
    sub.add_box({"box": {
        "id": "slot_out", "maxclass": "outlet", "numinlets": 1,
        "numoutlets": 0, "patching_rect": [400, 590, 25, 25],
        "comment": "ctl uplink (depth_N/umin_N/umax_N/bipolar_N/"
                   "tmin_N/tmax_N/announce N)"}})
    for uid, _t, _s, _o in ups:
        sub.add_line(uid, 0, "slot_out", 0)
    # ---- MAP button -> js; status -> UI --------------------------------------
    sub.add_newobj("slot_prep_map", "prepend map", numinlets=1, numoutlets=1,
                   outlettype=[""], patching_rect=[30, 370, 90, 20])
    sub.add_line("slot_map", 0, "slot_prep_map", 0)
    sub.add_line("slot_prep_map", 0, "slot_js", 0)
    sub.add_line("slot_js", 0, "slot_sink_reg", 0)
    sub.add_line("slot_js", 1, "slot_route", 0)
    sub.add_line("slot_route", 3, "slot_pname", 0)      # pname -> "set <n>"
    sub.add_line("slot_route", 6, "slot_seton", 0)      # flash -> set $1
    sub.add_line("slot_seton", 0, "slot_map", 0)
    sub.add_line("slot_sink_unmapped", 0, "slot_extunmap", 0)
    sub.add_line("slot_extunmap", 0, "slot_js", 0)
    sub.add_line("slot_rsig_r", 0, "slot_sink_remote", 0)
    sub.add_line("slot_rsig_m", 0, "slot_sink_mod", 0)
    if value_bar:
        # live output meter: the remote-signal inlet doubles as the lane's
        # source level (0..1 control signal) — snapshot~ self-clocks at 50 ms
        sub.add_line("slot_rsig_r", 0, "slot_bar_snap", 0)
        sub.add_line("slot_bar_snap", 0, "slot_bar", 0)
    if unmap_button:
        sub.add_line("slot_x", 0, "slot_x_un", 0)
        sub.add_line("slot_x_un", 0, "slot_js", 0)
    if row_color:
        # catalog #19: the parent fans `rowcolor r g b a` into inlet 0 per
        # stamped lane (each stamp has its own inlet cord) — recolors the
        # MAP/BI(/R/M/+) chips' on-state and the numbox LCDs so mapping
        # identity reads by color. live.* accept attribute-set messages.
        sub.add_newobj("slot_rc_route", "route rowcolor", numinlets=1,
                       numoutlets=2, outlettype=["", ""],
                       patching_rect=[620, 340, 100, 20])
        sub.add_line("slot_in", 0, "slot_rc_route", 0)
        rc_targets = ["slot_map", "slot_bipolar"]
        if mode_switch:
            rc_targets.append("slot_mode")
        if add_chip:
            rc_targets.append("slot_addc")
        sub.add_box({"box": {
            "id": "slot_rc_on", "maxclass": "message",
            "text": "bgoncolor $1 $2 $3 $4",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [620, 370, 140, 20]}})
        sub.add_box({"box": {
            "id": "slot_rc_lcd", "maxclass": "message",
            "text": "lcdcolor $1 $2 $3 $4",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [620, 400, 140, 20]}})
        sub.add_line("slot_rc_route", 0, "slot_rc_on", 0)
        sub.add_line("slot_rc_route", 0, "slot_rc_lcd", 0)
        for t in rc_targets:
            sub.add_line("slot_rc_on", 0, t, 0)
        for t in ("slot_depth", "slot_umin", "slot_umax"):
            sub.add_line("slot_rc_lcd", 0, t, 0)
        if value_bar:
            sub.add_box({"box": {
                "id": "slot_rc_bar", "maxclass": "message",
                "text": "slidercolor $1 $2 $3 $4",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [620, 430, 150, 20]}})
            sub.add_line("slot_rc_route", 0, "slot_rc_bar", 0)
            sub.add_line("slot_rc_bar", 0, "slot_bar", 0)
    if uplink_pname or uplink_dname:
        # catalog #22/#26: mirror the mapped target/device NAMES to the
        # parent (title-strip summary chips). The uplink is the RAW js
        # status stream — its messages are already `pname set <n>` /
        # `dname set <n>` with safe selectors. Do NOT re-prefix route
        # output here: after `route`, the payload's selector is `set`,
        # which prepend consumes as its own re-config verb (message
        # silently vanishes — Live-verified trap, T05).
        sub.add_line("slot_js", 1, "slot_out", 0)
    if mode_switch:
        # chip int (0=R,1=M) -> sink mode inlet: the sink bangs its zl.reg so
        # the stored id re-attaches down the newly selected path (hot swap).
        sub.add_line("slot_mode", 0, "slot_sink_mode", 0)
        sub.add_newobj("slot_up_mode", "prepend mode", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 620, 120, 20])
        sub.add_line("slot_mode", 0, "slot_up_mode", 0)
        sub.add_line("slot_up_mode", 0, "slot_out", 0)
    if add_chip:
        sub.add_newobj("slot_up_add", "prepend add", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 650, 120, 20])
        sub.add_line("slot_addc", 0, "slot_up_add", 0)
        sub.add_line("slot_up_add", 0, "slot_out", 0)
    if ratio_lcd:
        sub.add_newobj("slot_up_ratio", "prepend ratio", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 740, 120, 20])
        sub.add_line("slot_ratio", 0, "slot_up_ratio", 0)
        sub.add_line("slot_up_ratio", 0, "slot_out", 0)
    # ---- cross-slot exclusivity: announce goes UP the outlet; the parent
    # fans it back into every slot's inlet 0 (js ignores its own index)
    sub.add_newobj("slot_prep_ann", "prepend announce", numinlets=1,
                   numoutlets=1, outlettype=[""],
                   patching_rect=[30, 460, 120, 20])
    sub.add_line("slot_route", 7, "slot_prep_ann", 0)
    sub.add_line("slot_prep_ann", 0, "slot_out", 0)
    # a clean ``mapped <0|1>`` pulse up the outlet when this slot's mapping state
    # changes — the parent chains ``mapped 1`` for Auto-Map (arm the next lane).
    sub.add_newobj("slot_prep_mapped", "prepend mapped", numinlets=1,
                   numoutlets=1, outlettype=[""], patching_rect=[30, 490, 120, 20])
    sub.add_line("slot_route", 0, "slot_prep_mapped", 0)
    sub.add_line("slot_prep_mapped", 0, "slot_out", 0)

    if source_enum:
        sub.add_newobj("slot_up_src", "prepend source", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 590, 130, 20])
        sub.add_line("slot_source", 0, "slot_up_src", 0)
        sub.add_line("slot_up_src", 0, "slot_out", 0)
    if reveal:
        # reveal page idiom: "lanes N" on inlet 0 -> hide self when N < #1.
        # thispatcher inside a bpatcher addresses the BPATCHER BOX in the
        # parent, so "hidden $1" hides this stamped lane in presentation.
        sub.add_newobj("slot_lanes_route", "route lanes", numinlets=1,
                       numoutlets=2, outlettype=["", ""],
                       patching_rect=[4, 560, 90, 20])
        sub.add_newobj("slot_lanes_cmp", "< #1", numinlets=2, numoutlets=1,
                       outlettype=["int"], patching_rect=[4, 590, 50, 20])
        sub.add_box({"box": {
            "id": "slot_hide_msg", "maxclass": "message", "text": "hidden $1",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [4, 620, 70, 20]}})
        sub.add_newobj("slot_this", "thispatcher", numinlets=1, numoutlets=2,
                       outlettype=["", ""], patching_rect=[4, 650, 80, 20])
        sub.add_line("slot_in", 0, "slot_lanes_route", 0)
        sub.add_line("slot_lanes_route", 0, "slot_lanes_cmp", 0)
        sub.add_line("slot_lanes_cmp", 0, "slot_hide_msg", 0)
        sub.add_line("slot_hide_msg", 0, "slot_this", 0)

    ids = {"js": "slot_js", "map": "slot_map", "readout": "slot_pname",
           "sink_reg": "slot_sink_reg", "remote": "slot_sink_remote",
           "modulate": "slot_sink_mod", "rect": [0, 0, width, height]}
    # column map (x, w) for modulator_header_row caption alignment (#17)
    columns = {"map": (MAP_X, 26), "target": (PNAME_X, 66),
               "depth": (DEP_X, 32), "min": (MIN_X, 28), "max": (MAX_X, 28),
               "bipolar": (BI_X, 15)}
    if icon:
        columns["source"] = (1, 15)
    if mode_switch:
        columns["mode"] = (RM_X, 15)
        ids["mode"] = "slot_mode"
    if add_chip:
        columns["add"] = (ADD_X, 15)
        ids["add"] = "slot_addc"
    if unmap_button:
        columns["unmap"] = (UN_X, 13)
        ids["unmap"] = "slot_x"
    if ratio_lcd:
        columns["ratio"] = (RA_X, 34)
        ids["ratio"] = "slot_ratio"
    if value_bar:
        columns["bar"] = (0, 5)
        ids["bar"] = "slot_bar"
    ids["columns"] = columns
    if source_enum:
        ids["source"] = "slot_source"
    return (sub, ids)


def settings_sidebar(device, id_prefix, *, mini_width, accent, controls,
                     left_bar=18, panel_width=None, height=None,
                     param_name="Settings", label="SETTINGS",
                     panel_bgcolor=None, bar_bgcolor=None, column_bg=True,
                     bg_id="surf_bg", content_top=6, size_row=None,
                     shift_main=False):
    """A LEFT collapsible SETTINGS COLUMN behind a drawn ▶ dropdown in a thin
    left bar — the randomizer's space-saver, FAITHFULLY: the opener sits in a
    thin bar on the LEFT edge, the settings menu slides out on the LEFT, and the
    main content (hero + mapping grid) shifts RIGHT to make room while the device
    widens (``setwidth``).

    A left ``setwidth`` reveal is impossible (Live only grows the RIGHT edge), so
    — the column appears by REFLOW: every pre-existing
    on-canvas box is repositioned ``+panel_width`` when open, the settings column
    slides in from its parked slot, and the full-bleed background resizes. One
    automatable ``[Closed, Open]`` enum param (a parked ``live.text`` the drawn
    :func:`~m4l_builder.engines.settings_bar.settings_bar_js` bar drives + reads)
    fires the whole batch through one ``thispatcher`` + ``live.thisdevice``; a
    load-time reset forces the device closed so a saved-open set reopens clean.

    ``controls`` is the settings content, built BY the recipe so it can reflow it,
    laid out as a SINGLE COLUMN of value rows — LABEL on the left, its live value
    (a numbox by default, or a small ``kind:'dial'`` knob) on the right, the
    a drawer idiom (a drawer shows + tweaks config, so the value reads
    better than a knob). Keep it to a few rows so they stay roomy. Each control is
    a dict:
    ``{"id", "name", "min", "max", "init", "unit", "kind"}`` where ``kind`` is
    ``"dial"`` (default) or ``"num"``, plus optional ``"exp"``
    (parameter_exponent) and ``"ann"`` (info text). Call AFTER the main layout is
    final; build that layout with ``Surface(margin=left_bar)`` so it starts just
    right of the bar.

    ``size_row``: host the device's WIDTH toggle inside the drawer (T18 —
    the on-face FULL/MINI button is banned): ``{"mini": <narrow device
    width>}`` (+ optional ``"param_name"``/``"label"``/``"init"``) appends a
    FULL/MINI ``live.tab`` row and replaces the fixed ``setwidth`` pair with
    a width AUTHORITY — ``pak(size, drawer)`` → ``expr base_full + size*
    (base_mini-base_full) + drawer*panel`` → ``setwidth`` — so drawer and
    size states compose. The tab is bang-safe, so load re-fires it.

    ``shift_main=True``: permanently shift every captured main-content box
    ``+left_bar`` at build time — retrofits the bar onto devices whose
    layout starts at x≈0 without touching their rects (pass mini_width =
    old width + left_bar).

    Returns a StageResult: ``button`` (parked param) / ``bar`` (jsui) ids, the
    created ``section_ids``, ``mini_width`` / ``full_width`` and the ``param``.
    """
    from .engines.design_system import js_sidecar_name
    from .engines.settings_bar import settings_bar_js
    from .jsui_contract import validate_jsui_contract
    from .parameters import ParameterSpec

    p = id_prefix
    acc = list(accent)
    dim = [0.55, 0.58, 0.61, 1.0]
    h = int(round(height if height is not None else device.height))
    lb = int(left_bar)
    # SINGLE-COLUMN cells: a small caption CENTRED on top of its value (an LCD
    # numbox by default, or a small kind:'dial' knob). This is for the SETUP
    # params; a drawer shows/tweaks config, so the VALUE reads better than a knob.
    # Keep the drawer to a few rows so caption+value never crowd.
    inset, cell_w, dial_sz, nw = 6, 40, 18, 40
    cw = int(panel_width) if panel_width else (2 * inset + cell_w)
    rows = max(1, len(controls) + (1 if size_row else 0))
    row_h = max(1, (h - content_top - 6) // rows)
    mini = int(round(mini_width))
    full = mini + cw
    park = 900
    pbg = list(panel_bgcolor) if panel_bgcolor else [0.115, 0.115, 0.125, 1.0]
    bbg = list(bar_bgcolor) if bar_bgcolor else [0.10, 0.10, 0.115, 1.0]

    # ---- 1. capture the existing on-canvas main content (to reflow) -----------
    bg_seen = False
    main: list = []                              # (varname, [x,y,w,h])
    for entry in device.boxes:
        b = entry["box"]
        if b.get("presentation") != 1:
            continue
        r = b.get("presentation_rect")
        if not r or len(r) < 4:
            continue
        if float(r[0]) >= park:
            continue                             # already parked/hidden
        if b.get("id") == bg_id:
            b["varname"] = bg_id                 # bg resizes (needs a scriptname)
            bg_seen = True
            continue
        vn = b.get("varname")
        # A `varname` with a space (native controls default it to the PARAM name,
        # e.g. "Low Vol") breaks `script sendbox <name> ...` — it parses only the
        # first token as the box name and the reflow silently no-ops. Assign a
        # space-free scripting name in that case (scripting name != param name, so
        # this is safe and doesn't touch automation).
        if not vn or " " in vn:
            bid = b.get("id", "")
            vn = bid if (bid and " " not in bid) else f"{p}_m{len(main)}"
            b["varname"] = vn
        if shift_main:
            b["presentation_rect"] = [float(r[0]) + lb, float(r[1]),
                                      float(r[2]), float(r[3])]
            r = b["presentation_rect"]
        main.append((vn, [float(v) for v in r[:4]]))

    # ---- 2. the thin LEFT bar: drawn ▾ opener + rotated label ------------------
    device.add_panel(f"{p}_bar_bg", [0, 0, lb, h], bgcolor=bbg, border=0)
    # the bar is a CLASSIC jsui box — hold its code to the jsui contract
    # (this is the gate that catches v8ui pointer-event handlers, which a
    # jsui silently never fires: the dead-opener bug).
    bar_code = validate_jsui_contract(settings_bar_js(accent=tuple(acc),
                                                      label=label))
    bar_fname = js_sidecar_name("settings_bar.js", bar_code)
    device.register_asset(bar_fname, bar_code, asset_type="TEXT", category="js")
    # border=0 + transparent bordercolor: kill Max's default black 1px jsui frame
    # (the "dark box around the left separator") — the bar's separation is a plain
    # grey vertical line, like the dividers elsewhere on the device.
    device.add_box({"box": {
        "id": f"{p}_bar", "maxclass": "jsui", "jsui_maxclass": "jsui",
        "filename": bar_fname, "numinlets": 1, "numoutlets": 1,
        "outlettype": [""], "parameter_enable": 0, "presentation": 1,
        "border": 0, "bordercolor": [0.0, 0.0, 0.0, 0.0],
        "presentation_rect": [0, 0, lb, h], "patching_rect": [40, 40, lb, h]}})
    # a grey vertical hairline at the bar's right edge (always visible, full
    # height — no top/bottom caps), replacing the old black frame. A live.line,
    # not a panel, so it renders above the backdrop and isn't a "box".
    device.add_live_line(f"{p}_sep", [lb, 0, 1, h],
                         linecolor=[0.30, 0.30, 0.32, 1.0])

    # ---- 3. the automatable enum param (parked live.text the bar drives) -------
    btn_id = device.add_live_text(
        f"{p}_toggle", param_name, [park, park, 1, 1],
        text_on="Open", text_off="Closed", mode=1,
        annotation="Show / hide the settings column (slides out on the left).",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2, enum=["Closed", "Open"],
                                initial=[0], initial_enable=True))
    device.add_line(btn_id, 0, f"{p}_bar", 0)      # param -> bar arrow display
    device.add_line(f"{p}_bar", 0, btn_id, 0)      # bar click -> param

    # ---- 4. the settings column (authored PARKED; slides in when open) ---------
    col: list = []                               # (varname, on_rect)

    def _tag(vn):
        device.boxes[-1]["box"]["varname"] = vn

    def _col(vn, on_rect):
        _tag(vn)
        col.append((vn, [float(v) for v in on_rect]))

    if column_bg:
        device.add_panel(f"{p}_panel", [park, 0, cw, h], bgcolor=pbg, border=0)
        _col(f"{p}_panel", [lb, 0, cw, h])

    section_ids = []
    for i, c in enumerate(controls):
        cy = content_top + i * row_h
        bid, name = c["id"], c["name"]
        kind = c.get("kind", "num")
        ctrl_h = 15 if kind == "num" else dial_sz
        oy = cy + max(0, (row_h - (9 + 1 + ctrl_h)) // 2)   # centre the cell
        # caption CENTRED on top
        device.add_comment(f"{bid}_cap", [park + inset, oy, cell_w, 9],
                           name.upper(), textcolor=dim, fontsize=7.0,
                           justification=1, fontname="Ableton Sans Medium")
        _col(f"{bid}_cap", [lb + inset, oy, cell_w, 9])
        # its value below — a numbox (default) or a small knob
        if kind == "num":
            nx = inset + (cell_w - nw) // 2
            device.add_number_box(bid, name, [park + nx, oy + 10, nw, 15],
                                  min_val=c["min"], max_val=c["max"],
                                  initial=c["init"], unitstyle=c["unit"],
                                  lcdcolor=acc, annotation=c.get("ann", ""))
            _col(bid, [lb + nx, oy + 10, nw, 15])
        else:
            dx = inset + (cell_w - dial_sz) // 2
            dkw = dict(min_val=c["min"], max_val=c["max"], initial=c["init"],
                       unitstyle=c["unit"], showname=0, shownumber=0,
                       activedialcolor=list(acc), annotation_name=c.get("ann", ""))
            if c.get("exp"):
                dkw["parameter_exponent"] = c["exp"]
            device.add_dial(bid, name, [park + dx, oy + 10, dial_sz, dial_sz],
                            **dkw)
            _col(bid, [lb + dx, oy + 10, dial_sz, dial_sz])
        section_ids.append(bid)

    if size_row:
        from .ui import tab as _tab
        sz_param = size_row.get("param_name", "Size")
        sz_init = int(size_row.get("init", 0))
        i = len(controls)
        cy = content_top + i * row_h
        oy = cy + max(0, (row_h - (9 + 1 + 15)) // 2)
        device.add_comment(f"{p}_size_cap", [park + inset, oy, cell_w, 9],
                           size_row.get("label", "SIZE"), textcolor=dim,
                           fontsize=7.0, justification=1,
                           fontname="Ableton Sans Medium")
        _col(f"{p}_size_cap", [lb + inset, oy, cell_w, 9])
        device.add_box(_tab(
            f"{p}_size", sz_param, [park + inset, oy + 10, cell_w, 15],
            options=["FULL", "MINI"], multiline=0,
            annotation="Device width: FULL shows everything, MINI keeps "
                       "the essentials (the face clips on the right).",
            parameter=ParameterSpec(name=sz_param, shortname=sz_param,
                                    parameter_type=2,
                                    enum=["FULL", "MINI"],
                                    initial=[sz_init],
                                    initial_enable=True)))
        _col(f"{p}_size", [lb + inset, oy + 10, cell_w, 15])
        section_ids.append(f"{p}_size")

    # ---- 5. reflow wiring: param -> sel -> closed / open message batches -------
    thisp, thisdev = f"{p}_this", f"{p}_thisdev"
    device.add_newobj(thisp, "thispatcher", numinlets=1, numoutlets=2,
                      outlettype=["", ""], patching_rect=[760, 1720, 90, 20])
    device.add_newobj(thisdev, "live.thisdevice", numinlets=1, numoutlets=3,
                      outlettype=["bang", "int", "int"], patching_rect=[520, 1600, 90, 20])
    sel = f"{p}_sel"
    device.add_newobj(sel, "sel 0 1", numinlets=1, numoutlets=3,
                      outlettype=["bang", "bang", ""], patching_rect=[700, 1630, 60, 20])
    device.add_line(btn_id, 0, sel, 0)
    ctrig, otrig = f"{p}_ctrig", f"{p}_otrig"
    device.add_newobj(ctrig, "t b", numinlets=1, numoutlets=1,
                      outlettype=["bang"], patching_rect=[700, 1660, 40, 20])
    device.add_newobj(otrig, "t b", numinlets=1, numoutlets=1,
                      outlettype=["bang"], patching_rect=[940, 1660, 40, 20])
    device.add_line(sel, 0, ctrig, 0)              # value 0 = Closed
    device.add_line(sel, 1, otrig, 0)              # value 1 = Open
    # loadbang forces the device CLOSED so a saved-open set reopens with no dead
    # zone (send 0 to the toggle -> Closed batch fires only if it was Open).
    device.add_box({"box": {"id": f"{p}_lb0", "maxclass": "message", "text": "0",
                            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                            "patching_rect": [520, 1660, 30, 20]}})
    device.add_line(thisdev, 0, f"{p}_lb0", 0)
    device.add_line(f"{p}_lb0", 0, btn_id, 0)

    counter = [0]
    yy = [1760]

    def _msg(text, x, y, trig, dest):
        mid = f"{p}_r{counter[0]}"
        counter[0] += 1
        device.add_box({"box": {"id": mid, "maxclass": "message", "text": text,
                                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                                "patching_rect": [x, y, 230, 18]}})
        device.add_line(trig, 0, mid, 0)
        device.add_line(mid, 0, dest, 0)

    def _pair(vn, closed_rect, open_rect):
        cr = " ".join(f"{v:g}" for v in closed_rect)
        orr = " ".join(f"{v:g}" for v in open_rect)
        _msg(f"script sendbox {vn} presentation_rect {cr}", 700, yy[0], ctrig, thisp)
        _msg(f"script sendbox {vn} presentation_rect {orr}", 960, yy[0], otrig, thisp)
        yy[0] += 20

    for vn, r in main:                             # main: closed=orig, open=+cw
        _pair(vn, r, [r[0] + cw, r[1], r[2], r[3]])
    for vn, on_r in col:                           # column: closed=parked, open=on
        _pair(vn, [park + (on_r[0] - lb), on_r[1], on_r[2], on_r[3]], on_r)
    if bg_seen:                                    # bg: resize with the device
        _pair(bg_id, [0, 0, mini, h], [0, 0, full, h])
    if size_row:
        # width authority: setwidth = f(size, drawer) so both states compose
        bm = int(round(size_row["mini"]))
        pk = f"{p}_wpak"
        device.add_newobj(pk, "pak 0 0", numinlets=2, numoutlets=1,
                          outlettype=[""], patching_rect=[520, 1720, 60, 20])
        ex = f"{p}_wexpr"
        device.add_newobj(
            ex, f"expr {mini} + $i1 * ({bm} - {mini}) + $i2 * {cw}",
            numinlets=2, numoutlets=1, outlettype=[""],
            patching_rect=[520, 1750, 230, 20])
        pw = f"{p}_wpre"
        device.add_newobj(pw, "prepend setwidth", numinlets=1, numoutlets=1,
                          outlettype=[""], patching_rect=[520, 1780, 110, 20])
        device.add_line(f"{p}_size", 0, pk, 0)
        device.add_line(btn_id, 0, pk, 1)
        device.add_line(pk, 0, ex, 0)
        device.add_line(ex, 0, pw, 0)
        device.add_line(pw, 0, thisdev, 0)
        # load re-fire: bang the size tab (bang-safe) so the restored size
        # reaches the authority after the drawer reset
        stb = f"{p}_stb"
        device.add_newobj(stb, "t b", numinlets=1, numoutlets=1,
                          outlettype=["bang"],
                          patching_rect=[520, 1690, 30, 20])
        device.add_line(thisdev, 0, stb, 0)
        device.add_line(stb, 0, f"{p}_size", 0)
    else:
        _msg(f"setwidth {mini}", 700, yy[0], ctrig, thisdev)
        _msg(f"setwidth {full}", 960, yy[0], otrig, thisdev)

    device.width = mini
    return stage_result(
        {
            "button": btn_id,
            "bar": f"{p}_bar",
            "section_ids": section_ids,
            "left_bar": lb,
            "panel_width": cw,
            "mini_width": mini,
            "full_width": full,
        },
        name="settings_sidebar",
        params={param_name: device.parameter(param_name),
                **({size_row.get("param_name", "Size"):
                    device.parameter(size_row.get("param_name", "Size"))}
                   if size_row else {})},
    )


def delta_listen(device, id_prefix, *, button_rect=None, x=30, y=30):
    """Δ (delta) audition — hear ONLY wet-minus-dry (a delay device's "Delta").

    The classic saturation/EQ QA tool: what is the processor actually adding?
    Wire the processed signal into ``wet_in_l/r`` and the unprocessed signal into
    ``dry_in_l/r``; ``audio_out_l/r`` carries WET normally and (wet - dry) while
    the Δ toggle is lit. The toggle is a real automatable ``live.text`` param.
    """
    p = id_prefix
    btn = device.add_live_text(f"{p}_delta", "Delta", button_rect or [x, y, 36, 15],
                               text_on="\u0394", text_off="\u0394", mode=1)
    add = device.add_newobj(f"{p}_add", "+ 1", numinlets=2, numoutlets=1,
                            outlettype=[""], patching_rect=[x, y + 30, 45, 20])
    device.add_line(btn, 0, add, 0)
    ports = {}
    for ch in ("l", "r"):
        wet = device.add_newobj(f"{p}_wet_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[x, y + 60, 50, 20])
        dry = device.add_newobj(f"{p}_dry_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[x + 60, y + 60, 50, 20])
        sub = device.add_newobj(f"{p}_sub_{ch}", "-~", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[x, y + 90, 40, 20])
        sel = device.add_newobj(f"{p}_sel_{ch}", "selector~ 2 1", numinlets=3,
                                numoutlets=1, outlettype=["signal"],
                                patching_rect=[x, y + 120, 90, 20])
        device.add_line(add, 0, sel, 0)
        device.add_line(wet, 0, sel, 1)          # off -> wet passthrough
        device.add_line(wet, 0, sub, 0)
        device.add_line(dry, 0, sub, 1)
        device.add_line(sub, 0, sel, 2)          # on  -> wet - dry
        ports[f"wet_in_{ch}"] = device.box(wet).inlet(0)
        ports[f"dry_in_{ch}"] = device.box(dry).inlet(0)
        ports[f"audio_out_{ch}"] = device.box(sel).outlet(0)
    return stage_result(
        {"button": btn},
        name="delta_listen",
        params={f"{p}_delta": device.parameter(btn)},
        ports=ports,
    )


def latency_readout(device, id_prefix, latency_samples, *, rect,
                    fontsize=7.5, ignoreclick=1):
    """On-face "Latency: X ms" readout (a delay device) — surface PDC honestly.

    ``latency_samples`` is the same fixed sample count the builder reported via
    ``device.latency``; the displayed ms tracks the LIVE samplerate through
    ``dspstate~`` so it is correct at 44.1/48/96 k. Rendered in a display-only
    ``message`` box (``ignoreclick`` so it is not an interactive control).
    """
    p = id_prefix
    lb = device.add_newobj(f"{p}_lb", "loadbang", numinlets=1, numoutlets=1,
                           outlettype=["bang"], patching_rect=[700, 40, 60, 20])
    dsp = device.add_newobj(f"{p}_dsp", "dspstate~", numinlets=1, numoutlets=4,
                            outlettype=["int", "float", "int", "int"],
                            patching_rect=[700, 70, 80, 20])
    ms = device.add_newobj(f"{p}_ms", f"expr {int(latency_samples)} * 1000. / $f1",
                           numinlets=1, numoutlets=1, outlettype=[""],
                           patching_rect=[700, 100, 160, 20])
    fmt = device.add_newobj(f"{p}_fmt", "sprintf set Latency: %.1f ms",
                            numinlets=1, numoutlets=1, outlettype=[""],
                            patching_rect=[700, 130, 170, 20])
    device.add_box({"box": {
        "id": f"{p}_msg", "maxclass": "message", "text": "Latency: -- ms",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "ignoreclick": ignoreclick, "fontsize": fontsize,
        "presentation": 1, "presentation_rect": list(rect),
        "patching_rect": [700, 160, 130, 20]}})
    device.add_line(lb, 0, dsp, 0)
    device.add_line(dsp, 1, ms, 0)
    device.add_line(ms, 0, fmt, 0)
    device.add_line(fmt, 0, f"{p}_msg", 0)
    return stage_result(
        {"message": f"{p}_msg"},
        name="latency_readout",
        params={},
        ports={},
    )


def report_latency(device, id_prefix, *, samples=None, ms=None,
                   extra_samples_expr=None):
    """Report the device's PDC latency to Live SAMPLERATE-CORRECTLY (the
    ``latency $1`` -> ``thispatcher`` wire, plus the static patcher ``latency``
    key as the value at load).

    The trap this closes: ``device.latency = 88`` bakes ONE samplerate's sample
    count into the patcher, so a 2 ms lookahead reported as 88 samples is only
    right at 44.1k — at 48/96/192k Live under-compensates and parallel chains
    smear. Choose the path by what the DSP actually holds constant:

    * ``samples=N`` — the delay is a FIXED SAMPLE COUNT at any samplerate
      (e.g. a fixed FIR tap count). Emits ``loadbang -> "N" -> "latency $1" ->
      thispatcher`` and sets ``device.latency = N``. Already
      samplerate-independent, so no recompute wire is needed.
    * ``ms=T`` — the delay is a FIXED TIME (e.g. ``Delay.read(samplerate *
      0.002)`` lookahead), so the sample count MUST recompute per samplerate.
      Emits ``loadbang -> dspstate~ -> expr int($f1 * T/1000 + 0.5) ->
      deferlow -> "latency $1" -> thispatcher`` — dspstate~ re-outputs on every
      DSP restart, so a samplerate change re-reports automatically (the same
      dspstate~ idiom :func:`latency_readout` uses for display). The static
      ``device.latency`` is set to the 44.1k count as the value-at-load.

    ``extra_samples_expr`` (ms path only) appends ``+ (<term>)`` to the expr —
    a constant-in-samples addend on top of the time-constant part (e.g. ``"3"``
    for a fixed decimator tail after a ms lookahead). Use a numeric literal if
    the static at-load value should include it too.

    Returns a stage whose ``samples_in`` port is the ``latency $1`` message
    inlet: a device whose latency is MODE-dependent (e.g. heat reporting 3
    samples only while 2x oversampling is on) wires its mode control through an
    ``expr``/``*`` into this port to re-report on every mode flip.
    """
    if (samples is None) == (ms is None):
        raise ValueError("report_latency: pass exactly one of samples= or ms=")
    if extra_samples_expr is not None and ms is None:
        raise ValueError("report_latency: extra_samples_expr requires the ms= path")
    p = id_prefix
    lb = device.add_newobj(f"{p}_lb", "loadbang", numinlets=1, numoutlets=1,
                           outlettype=["bang"], patching_rect=[760, 40, 60, 20])
    device.add_box({"box": {
        "id": f"{p}_msg", "maxclass": "message", "text": "latency $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [760, 130, 80, 20]}})
    thisp = device.add_newobj(f"{p}_thisp", "thispatcher",
                              numinlets=1, numoutlets=2, outlettype=["", ""],
                              patching_rect=[760, 160, 80, 20])
    device.add_line(f"{p}_msg", 0, thisp, 0)
    if samples is not None:
        device.latency = int(samples)
        device.add_box({"box": {
            "id": f"{p}_init", "maxclass": "message", "text": str(int(samples)),
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [760, 70, 50, 20]}})
        device.add_line(lb, 0, f"{p}_init", 0)
        device.add_line(f"{p}_init", 0, f"{p}_msg", 0)
    else:
        static = int(float(ms) * 44.1 + 0.5)
        if extra_samples_expr is not None:
            try:
                static += int(float(extra_samples_expr) + 0.5)
            except ValueError:
                pass  # non-literal term: static stays the time-constant part
        device.latency = static
        dsp = device.add_newobj(f"{p}_dsp", "dspstate~", numinlets=1, numoutlets=4,
                                outlettype=["int", "float", "int", "int"],
                                patching_rect=[760, 70, 80, 20])
        expr_text = f"expr int($f1 * {float(ms) * 0.001} + 0.5)"
        if extra_samples_expr is not None:
            expr_text += f" + ({extra_samples_expr})"
        ex = device.add_newobj(f"{p}_expr", expr_text,
                               numinlets=1, numoutlets=1, outlettype=[""],
                               patching_rect=[760, 100, 200, 20])
        defer = device.add_newobj(f"{p}_defer", "deferlow",
                                  numinlets=1, numoutlets=1, outlettype=[""],
                                  patching_rect=[880, 100, 60, 20])
        device.add_line(lb, 0, dsp, 0)
        device.add_line(dsp, 1, ex, 0)
        device.add_line(ex, 0, defer, 0)
        device.add_line(defer, 0, f"{p}_msg", 0)
    return stage_result(
        {"message": f"{p}_msg", "thispatcher": f"{p}_thisp"},
        name="report_latency",
        params={},
        ports={"samples_in": device.box(f"{p}_msg").inlet(0)},
    )


def mode_stack(device, id_prefix, *, rect, modes, param_name="Mode",
               tab_rect=None):
    """Generator MODE-STACK container (catalog kit item #9 — the
    a modulation-lane architecture): a narrow VERTICAL ``live.tab`` column
    whose automatable enum param swaps which of N pre-built editor stacks is
    visible, all sharing the SAME content rect.

    ``modes`` is a list of ``(label, [box_names...])`` — each mode owns the
    boxes (jsui editor + any companion chrome/controls) that should be visible
    ONLY in that mode; the caller builds every mode's content at the same
    coords BEFORE calling. Box names may be varnames or box ids; each must be
    SPACE-FREE (``script sendbox`` parses only the first token as the box
    name) and appear in exactly one mode. Boxes whose scripting name is unset
    or differs (native ``live.*`` controls default ``varname`` to the param
    longname — often WITH spaces) get the given name STAMPED as ``varname``
    (scripting name != param name, so automation is untouched — the
    settings_sidebar-proven rewrite).

    **Wiring — the viewhide dataflow on the kit's Live-proven
    scripting bus:** their ``viewhide k`` abstraction is ``r ---view ->
    != k -> prepend hidden -> control box`` (Live_Stretch pages its controls
    through box-inlet ``hidden 0/1`` messages). A jsui's inlet 0 is a JS
    message dispatcher, so direct-inlet delivery would post ``no function
    hidden`` — instead the same ``!= k`` flag drives ``script sendbox <name>
    hidden $1`` messages into one ``thispatcher`` (exactly how
    :func:`settings_sidebar` moves boxes; ``sendbox`` sets BOX attributes
    without touching inlets). Per mode k one ``!= k``; per managed box one
    message box; hidden = (mode != k).

    No ``set_active`` gating is sent: none of the kit editors needs it, and
    Max only calls ``paint()`` on visible boxes — hiding IS the perf gate.

    **Initial state:** mode 0's boxes are authored visible, every other
    mode's are authored ``hidden: 1`` (correct first frame), and a
    ``live.thisdevice`` bang (NOT loadbang — kit convention for
    scripting-ready init) re-fires the tab's restored value through the
    wiring at load, so a set saved on mode 2 reopens showing mode 2.

    ``tab_rect`` defaults to a narrow column just LEFT of ``rect`` (~22px —
    Auto_Gate's "Time Mode" tab is 21px x 3 rows); the tab renders vertical
    via ``num_lines_* = len(modes)`` + ``multiline=1`` (corpus-exact).
    Returns a StageResult: ``tab`` / ``thispatcher`` / ``thisdevice`` ids,
    ``content_rect``, ``managed`` (label -> names) and the enum ``param``.
    """
    p = id_prefix
    modes = [(str(label), list(names)) for label, names in modes]
    if len(modes) < 2:
        raise ValueError("mode_stack needs at least 2 modes")
    labels = [label for label, _ in modes]

    # ---- resolve + sanitize the managed boxes ------------------------------
    by_varname = {}
    by_id = {}
    for entry in device.boxes:
        b = entry["box"]
        vn = b.get("varname")
        if vn is not None:
            by_varname.setdefault(vn, b)
        bid = b.get("id")
        if bid is not None:
            by_id.setdefault(bid, b)
    seen = {}
    for k, (label, names) in enumerate(modes):
        for name in names:
            if " " in name:
                raise ValueError(
                    f"mode_stack: managed name {name!r} contains a space — "
                    f"`script sendbox` parses only the first token as the box "
                    f"name; pass the box id and the recipe stamps it"
                )
            if name in seen:
                raise ValueError(
                    f"mode_stack: {name!r} appears in modes "
                    f"{seen[name]!r} and {label!r}; a box may belong to "
                    f"exactly one mode (leave shared chrome unmanaged)"
                )
            seen[name] = label
            box = by_varname.get(name) or by_id.get(name)
            if box is None:
                raise ValueError(
                    f"mode_stack: no box with varname or id {name!r} — build "
                    f"every mode's content before calling"
                )
            if box.get("varname") != name:
                box["varname"] = name          # stamp a space-free script name
            if k > 0:
                box["hidden"] = 1              # authored initial: mode 0 shows

    # ---- the vertical mode tab (the automatable enum param) ----------------
    n = len(modes)
    if tab_rect is None:
        tab_rect = [rect[0] - 22, rect[1], 22, 16 * n]
    tab = device.add_tab(f"{p}_tab", param_name, list(tab_rect),
                         options=labels, multiline=1,
                         num_lines_presentation=n, num_lines_patching=n)

    # ---- visibility wiring: tab -> != k -> sendbox hidden -> thispatcher ---
    thisp = f"{p}_thisp"
    device.add_newobj(thisp, "thispatcher", numinlets=1, numoutlets=2,
                      outlettype=["", ""], patching_rect=[900, 1740, 90, 20])
    counter = 0
    for k, (_label, names) in enumerate(modes):
        ne = f"{p}_ne{k}"
        device.add_newobj(ne, f"!= {k}", numinlets=2, numoutlets=1,
                          outlettype=["int"],
                          patching_rect=[900 + 260 * k, 1640, 40, 20])
        device.add_line(tab, 0, ne, 0)
        for name in names:
            mid = f"{p}_h{counter}"
            counter += 1
            device.add_box({"box": {
                "id": mid, "maxclass": "message",
                "text": f"script sendbox {name} hidden $1",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [900 + 260 * k, 1670 + 22 * counter,
                                  240, 18]}})
            device.add_line(ne, 0, mid, 0)
            device.add_line(mid, 0, thisp, 0)

    # ---- load-time re-sync: live.thisdevice bang -> the tab re-outputs its
    # restored value (NOT loadbang: scripting isn't ready at loadbang).
    thisdev = f"{p}_thisdev"
    device.add_newobj(thisdev, "live.thisdevice", numinlets=1, numoutlets=3,
                      outlettype=["bang", "int", "int"],
                      patching_rect=[900, 1580, 90, 20])
    init = f"{p}_init"
    device.add_newobj(init, "t b", numinlets=1, numoutlets=1,
                      outlettype=["bang"], patching_rect=[900, 1610, 40, 20])
    device.add_line(thisdev, 0, init, 0)
    device.add_line(init, 0, tab, 0)

    return stage_result(
        {
            "tab": tab,
            "thispatcher": thisp,
            "thisdevice": thisdev,
            "content_rect": list(rect),
            "managed": {label: list(names) for label, names in modes},
        },
        name="mode_stack",
        params={param_name: device.parameter(tab)},
    )


def randomize_matrix(device, id_prefix, *, rect, targets, columns=4,
                     chip_h=15, gap=2, labels=None, seed=True,
                     variation=False):
    """Per-param RANDOMIZE page (an Auto-Gate device) — catalog #11 + #12.

    Every entry in ``targets`` (box ids/refs of NATIVE param controls already
    on the device) gets an enable chip; the RND button rolls a fresh random
    value into each ENABLED target's inlet — through the control, so Live
    sees an ordinary value change (undoable, automation-recordable). ALL /
    NONE quick-set the chips. Chip states are stored-only params
    (``Rnd <target longname>``, ``parameter_invisible=1``): saved with the
    set, absent from automation menus.

    Value generation is derived from each target's registered
    :class:`ParameterSpec` at BUILD time: enum/stepped/integer params get
    ``random <n_values>`` (+ offset); continuous params get
    ``random 10001 -> scale 0 10000 <min> <max>`` (uniform across the range).
    ``random`` objects are seeded at load from ``cpuclock`` (+k per lane so
    lanes decorrelate) — the Max-8-safe equivalent of a v8
    ``Date.now()`` seed idiom; without it every load replays one sequence.
    No ``---disarm`` guard (corpus Tempo Scale Setter) is used: unlike a
    set-level tempo/scale roll, device-param randomize is a plain undoable
    edit.

    Layout: ``rect`` hosts a header row (RND / ALL / NONE message buttons,
    non-param by design — automating "randomize" from a clip is a footgun)
    and a ``columns``-wide chip grid growing downward; size ``rect`` for
    ``1 + ceil(len(targets)/columns)`` rows of ``chip_h + gap``.

    ``variation=True`` (catalog #27, Chordsaus "Random Variation %"): adds a
    ``Rnd Var`` % param to the header and rolls each enabled target AROUND
    ITS CURRENT VALUE (± var% of its range, clipped) instead of uniformly
    across the range — humanize-style nudging. Each target's last value is
    tracked from its own outlet; stepped targets round after the clip.
    """
    from .parameters import ParameterSpec

    p = id_prefix
    if not targets:
        raise ValueError("randomize_matrix: targets must be non-empty")
    tgt_ids = [str(t) for t in targets]
    if len(set(tgt_ids)) != len(tgt_ids):
        raise ValueError("randomize_matrix: duplicate targets")
    specs = []
    for t in tgt_ids:
        spec = device.parameter(device.box(t))
        if spec is None:
            raise ValueError(
                f"randomize_matrix: {t!r} has no registered parameter spec")
        specs.append(spec)
    labels = labels or {}

    x, y, w, _h = rect
    px, py = 700, 1700          # patching-side plumbing column

    # ---- header row: RND / ALL / NONE (message boxes: clickable, non-param) --
    n_hdr = 4 if variation else 3
    bw = (w - (n_hdr - 1) * gap) / float(n_hdr)
    hdr = []
    for i, (bid, txt) in enumerate(
            [(f"{p}_rnd", "RND"), (f"{p}_all", "ALL"), (f"{p}_none", "NONE")]):
        device.add_box({"box": {
            "id": bid, "maxclass": "message", "text": txt,
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "fontsize": 8.0, "textjustification": 1,
            "presentation": 1,
            "presentation_rect": [x + i * (bw + gap), y, bw, chip_h],
            "patching_rect": [px + i * 90, py, 60, 20]}})
        hdr.append(bid)
    trig = device.add_newobj(f"{p}_trig", "t b", numinlets=1, numoutlets=1,
                             outlettype=["bang"],
                             patching_rect=[px, py + 30, 40, 20])
    device.add_line(f"{p}_rnd", 0, trig, 0)
    all_int = device.add_newobj(f"{p}_all_i", "t 1", numinlets=1, numoutlets=1,
                                outlettype=["int"],
                                patching_rect=[px + 90, py + 30, 30, 20])
    none_int = device.add_newobj(f"{p}_none_i", "t 0", numinlets=1,
                                 numoutlets=1, outlettype=["int"],
                                 patching_rect=[px + 180, py + 30, 30, 20])
    device.add_line(f"{p}_all", 0, all_int, 0)
    device.add_line(f"{p}_none", 0, none_int, 0)
    if variation:
        from .parameters import ParameterSpec as _PS
        device.add_number_box(
            f"{p}_var", "Rnd Var", [x + 3 * (bw + gap), y, bw, chip_h],
            min_val=0.0, max_val=100.0, initial=15.0,
            parameter=_PS(name="Rnd Var", shortname="Rnd Var",
                          minimum=0.0, maximum=100.0, initial=15.0,
                          initial_enable=True, units="%ld %", unitstyle=9))
        var_td = device.add_newobj(f"{p}_var_td", "live.thisdevice",
                                   numinlets=1, numoutlets=3,
                                   outlettype=["bang", "int", "int"],
                                   patching_rect=[px + 380, py, 90, 20])
        var_tb = device.add_newobj(f"{p}_var_tb", "t b", numinlets=1,
                                   numoutlets=1, outlettype=["bang"],
                                   patching_rect=[px + 380, py + 30, 30, 20])
        device.add_line(var_td, 0, var_tb, 0)
        device.add_line(var_tb, 0, f"{p}_var", 0)

    # ---- seed clock (one per matrix; per-lane +k decorrelates) ---------------
    if seed:
        lb = device.add_newobj(f"{p}_seed_lb", "loadbang", numinlets=1,
                               numoutlets=1, outlettype=["bang"],
                               patching_rect=[px + 280, py, 60, 20])
        clk = device.add_newobj(f"{p}_seed_clk", "cpuclock", numinlets=1,
                                numoutlets=1, outlettype=["float"],
                                patching_rect=[px + 280, py + 30, 60, 20])
        device.add_line(lb, 0, clk, 0)

    chip_w = (w - (columns - 1) * gap) / float(columns)
    params = {}
    chips = []
    for k, (tid, spec) in enumerate(zip(tgt_ids, specs)):
        row, col = divmod(k, columns)
        cy = y + (chip_h + gap) * (row + 1)
        cx = x + col * (chip_w + gap)
        label = labels.get(tid) or spec.shortname or spec.name
        chip = device.add_live_text(
            f"{p}_chip{k}", f"Rnd {spec.name}",
            [cx, cy, chip_w, chip_h],
            text_on=label, text_off=label, mode=1, fontsize=8.0,
            annotation=f"Include '{spec.name}' when RND rolls new values.",
            parameter=ParameterSpec(
                name=f"Rnd {spec.name}", shortname=label[:15] or "Rnd",
                parameter_type=2, enum=["off", "on"], initial=[1],
                initial_enable=True, invisible=1))
        chips.append(chip)
        gate = device.add_newobj(f"{p}_gate{k}", "gate", numinlets=2,
                                 numoutlets=1, outlettype=[""],
                                 patching_rect=[px + k * 90, py + 70, 40, 20])
        device.add_line(chip, 0, gate, 0)          # chip state -> gate control
        device.add_line(trig, 0, gate, 1)          # RND bang   -> gate data
        device.add_line(all_int, 0, chip, 0)
        device.add_line(none_int, 0, chip, 0)

        # value generator from the target's spec
        is_enum = spec.enum is not None
        stepped = (spec.steps is not None or spec.integer_like or is_enum
                   or spec.parameter_type == 1)
        lo = 0.0 if spec.minimum is None else float(spec.minimum)
        hi = float(len(spec.enum) - 1) if is_enum and spec.maximum is None \
            else (1.0 if spec.maximum is None else float(spec.maximum))
        if variation:
            # roll AROUND the current value: cur + rand(-1..1)·(var%·range)
            rng = hi - lo
            cur = device.add_newobj(f"{p}_cur{k}", "f", numinlets=2,
                                    numoutlets=1, outlettype=["float"],
                                    patching_rect=[px + k * 90, py + 160, 30, 20])
            device.add_line(tid, 0, cur, 1)          # track target's value
            tbb = device.add_newobj(f"{p}_tb{k}", "t b b", numinlets=1,
                                    numoutlets=2,
                                    outlettype=["bang", "bang"],
                                    patching_rect=[px + k * 90, py + 70, 50, 20])
            device.add_line(gate, 0, tbb, 0)
            rnd = device.add_newobj(f"{p}_val{k}", "random 10001",
                                    numinlets=2, numoutlets=1,
                                    outlettype=["int"],
                                    patching_rect=[px + k * 90, py + 100, 80, 20])
            sc = device.add_newobj(f"{p}_sc{k}", "scale 0 10000 -1. 1.",
                                   numinlets=6, numoutlets=1, outlettype=[""],
                                   patching_rect=[px + k * 90, py + 130, 130, 20])
            spread = device.add_newobj(f"{p}_sp{k}", "* 0.", numinlets=2,
                                       numoutlets=1, outlettype=["float"],
                                       patching_rect=[px + k * 90, py + 160, 40, 20])
            vfrac = device.add_newobj(f"{p}_vf{k}", f"* {rng / 100.0:.6g}",
                                      numinlets=2, numoutlets=1,
                                      outlettype=["float"],
                                      patching_rect=[px + 380, py + 70 + k * 30, 60, 20])
            device.add_line(f"{p}_var", 0, vfrac, 0)
            device.add_line(vfrac, 0, spread, 1)
            addc = device.add_newobj(f"{p}_ad{k}", "+ 0.", numinlets=2,
                                     numoutlets=1, outlettype=["float"],
                                     patching_rect=[px + k * 90, py + 190, 40, 20])
            device.add_line(cur, 0, addc, 1)
            clip = device.add_newobj(f"{p}_cl{k}",
                                     f"clip {lo:.6g} {hi:.6g}",
                                     numinlets=3, numoutlets=1,
                                     outlettype=[""],
                                     patching_rect=[px + k * 90, py + 220, 90, 20])
            # right bang FIRST: pull current into the adder's cold inlet
            device.add_line(tbb, 1, cur, 0)
            device.add_line(tbb, 0, rnd, 0)
            device.add_line(rnd, 0, sc, 0)
            device.add_line(sc, 0, spread, 0)
            device.add_line(spread, 0, addc, 0)
            device.add_line(addc, 0, clip, 0)
            src = clip
            if stepped:
                rr = device.add_newobj(f"{p}_rd{k}", "expr round($f1)",
                                       numinlets=1, numoutlets=1,
                                       outlettype=[""],
                                       patching_rect=[px + k * 90, py + 250, 100, 20])
                device.add_line(clip, 0, rr, 0)
                src = rr
            device.add_line(src, 0, tid, 0)
            if seed:
                sd = device.add_newobj(f"{p}_sd{k}", f"expr int($f1) + {k}",
                                       numinlets=1, numoutlets=1,
                                       outlettype=[""],
                                       patching_rect=[px + 280, py + 70 + k * 30, 110, 20])
                pre = device.add_newobj(f"{p}_ps{k}", "prepend seed",
                                        numinlets=1, numoutlets=1,
                                        outlettype=[""],
                                        patching_rect=[px + 400, py + 70 + k * 30, 90, 20])
                device.add_line(clk, 0, sd, 0)
                device.add_line(sd, 0, pre, 0)
                device.add_line(pre, 0, rnd, 0)
            params[f"Rnd {spec.name}"] = device.parameter(chip)
            continue
        if stepped:
            n_values = (len(spec.enum) if is_enum
                        else (spec.steps if spec.steps
                              else int(round(hi - lo)) + 1))
            rnd = device.add_newobj(f"{p}_val{k}", f"random {int(n_values)}",
                                    numinlets=2, numoutlets=1,
                                    outlettype=["int"],
                                    patching_rect=[px + k * 90, py + 100, 80, 20])
            src = rnd
            if lo:
                off = device.add_newobj(f"{p}_off{k}", f"+ {int(lo)}",
                                        numinlets=2, numoutlets=1,
                                        outlettype=["int"],
                                        patching_rect=[px + k * 90, py + 130, 50, 20])
                device.add_line(rnd, 0, off, 0)
                src = off
        else:
            rnd = device.add_newobj(f"{p}_val{k}", "random 10001",
                                    numinlets=2, numoutlets=1,
                                    outlettype=["int"],
                                    patching_rect=[px + k * 90, py + 100, 80, 20])
            def _f(v):
                s = f"{v:.6g}"
                return s if ("." in s or "e" in s) else s + "."
            sc = device.add_newobj(f"{p}_sc{k}",
                                   f"scale 0 10000 {_f(lo)} {_f(hi)}",
                                   numinlets=6, numoutlets=1, outlettype=[""],
                                   patching_rect=[px + k * 90, py + 130, 130, 20])
            device.add_line(rnd, 0, sc, 0)
            src = sc
        device.add_line(gate, 0, rnd, 0)
        device.add_line(src, 0, tid, 0)
        if seed:
            sd = device.add_newobj(f"{p}_sd{k}", f"expr int($f1) + {k}",
                                   numinlets=1, numoutlets=1, outlettype=[""],
                                   patching_rect=[px + 280, py + 70 + k * 30, 110, 20])
            pre = device.add_newobj(f"{p}_ps{k}", "prepend seed",
                                    numinlets=1, numoutlets=1, outlettype=[""],
                                    patching_rect=[px + 400, py + 70 + k * 30, 90, 20])
            device.add_line(clk, 0, sd, 0)
            device.add_line(sd, 0, pre, 0)
            device.add_line(pre, 0, rnd, 0)
        params[f"Rnd {spec.name}"] = device.parameter(chip)

    return stage_result(
        {"rnd": f"{p}_rnd", "all": f"{p}_all", "none": f"{p}_none",
         "chips": chips},
        name="randomize_matrix",
        params=params,
        ports={"trigger_in": device.box(trig).inlet(0)},
    )
