"""Recipes: widgets — split out of recipes.py; re-exported by m4l_builder.recipes."""

from .stages import stage_result

_HEADER_CAPTIONS = {"source": "SRC", "map": "MAP", "target": "TARGET",
                    "depth": "DEPTH", "min": "MIN", "max": "MAX",
                    "bipolar": "±", "mode": "R M", "add": "+",
                    "bar": "", "unmap": "✗", "ratio": "×"}


def modulator_header_row(device, id_prefix, *, at, columns, dim_color=None,
                         fontsize=5.8, captions=None):
    """ONE shared caption strip above a stacked modulator-slot column
    (catalog #17: the ``±`` / ``R M`` table grammar).

    ``at`` is the on-face ``[x, y]`` where the FIRST stamped slot row starts;
    captions are laid out from the ``columns`` map the slot returns in
    ``ids["columns"]`` (each value an ``(x, w)`` pair relative to the row), so
    header and rows stay aligned however the slot was configured
    (icon / mode_switch / add_chip all shift the geometry).
    """
    x0, y0 = at
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    texts = dict(_HEADER_CAPTIONS)
    if captions:
        texts.update(captions)
    made = []
    for key, (cx, cw) in sorted(columns.items(), key=lambda kv: kv[1][0]):
        text = texts.get(key, key.upper())
        if not text:            # self-evident columns (e.g. the value bar)
            continue
        cid = f"{id_prefix}_h_{key}"
        device.add_comment(cid, [x0 + cx, y0 - 9, max(cw, 16), 8],
                           text, textcolor=dim, fontsize=fontsize)
        made.append(cid)
    return stage_result({"captions": made}, name="modulator_header_row",
                        params={}, ports={})


def mapping_summary_chip(device, id_prefix, *, rect, accent,
                         text_color=None, dim_color=None, fontsize=7.5):
    """Title-strip mapping summary (catalog #22 + #26): a one-line chip that
    mirrors a slot's mapping state anywhere on the face — including the 16px
    title zone, so a COLLAPSED device still reads its mapping.

    Layout: ``[dot] Param-name    device-name`` — the dot lights accent while
    mapped; unmapped shows a dim ``—``. Build the slot with
    ``uplink_pname=True`` / ``uplink_dname=True`` and fan the parent-side
    uplink through ``route pname dname mapped`` into this stage's
    ``pname_in`` / ``dname_in`` / ``mapped_in`` ports (multi-word names
    arrive as atom lists; ``prepend set`` renders them verbatim).
    """
    from .ui import textedit

    p = id_prefix
    x, y, w, h = rect
    tx = list(text_color) if text_color else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    acc = list(accent)

    pw = int((w - 7) * 0.55)
    device.add_box({"box": {
        "id": f"{p}_dot", "maxclass": "live.line", "justification": 1,
        "numinlets": 1, "numoutlets": 0, "linecolor": dim,
        "presentation": 1, "presentation_rect": [x, y + h // 2 - 2, 4, 4],
        "patching_rect": [820, 1700, 4, 4]}})
    device.add_box(textedit(
        f"{p}_txt", [x + 7, y, pw, h], text="—", fontsize=fontsize,
        textcolor=tx, bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    device.add_box(textedit(
        f"{p}_dev", [x + 9 + pw, y, w - pw - 9, h], text="",
        fontsize=fontsize - 0.5, textcolor=dim,
        bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=2, ignoreclick=1))
    # NOTE the mapper js already emits ``pname set <name>`` / ``dname set
    # <name>`` — after the parent's ``route pname dname`` the payload is a
    # ready-made textedit ``set`` message, so it feeds the fields DIRECTLY
    # (adding another ``prepend set`` double-wraps and corrupts it).
    # mapped 0/1 -> dot color + clear-to-dash on unmap
    device.add_newobj(f"{p}_msel", "sel 1 0", numinlets=3, numoutlets=3,
                      outlettype=["bang", "bang", ""],
                      patching_rect=[960, 1700, 60, 20])
    on_txt = "linecolor {} {} {} 1.".format(*[round(c, 3) for c in acc[:3]])
    off_txt = "linecolor {} {} {} 1.".format(*[round(c, 3) for c in dim[:3]])
    device.add_box({"box": {
        "id": f"{p}_c_on", "maxclass": "message", "text": on_txt,
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1730, 150, 20]}})
    device.add_box({"box": {
        "id": f"{p}_c_off", "maxclass": "message", "text": off_txt,
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1760, 150, 20]}})
    device.add_box({"box": {
        "id": f"{p}_clr_p", "maxclass": "message", "text": "set —",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1790, 60, 20]}})
    device.add_box({"box": {
        "id": f"{p}_clr_d", "maxclass": "message", "text": "set",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1820, 50, 20]}})
    device.add_line(f"{p}_msel", 0, f"{p}_c_on", 0)
    device.add_line(f"{p}_msel", 1, f"{p}_c_off", 0)
    device.add_line(f"{p}_msel", 1, f"{p}_clr_p", 0)
    device.add_line(f"{p}_msel", 1, f"{p}_clr_d", 0)
    device.add_line(f"{p}_c_on", 0, f"{p}_dot", 0)
    device.add_line(f"{p}_c_off", 0, f"{p}_dot", 0)
    device.add_line(f"{p}_clr_p", 0, f"{p}_txt", 0)
    device.add_line(f"{p}_clr_d", 0, f"{p}_dev", 0)
    return stage_result(
        {"text": f"{p}_txt", "device_text": f"{p}_dev", "dot": f"{p}_dot"},
        name="mapping_summary_chip",
        params={},
        ports={"pname_in": device.box(f"{p}_txt").inlet(0),
               "dname_in": device.box(f"{p}_dev").inlet(0),
               "mapped_in": device.box(f"{p}_msel").inlet(0)},
    )


_LANE_ROTATOR_JS = """// lane_rotator — recompute the full matrix~ crosspoint grid (T06, #23/#24)
// Stateful on purpose: `rot <n>` / `mono <0|1>` each recompute with the
// cached other, so update ORDER never matters (params restore in any order,
// and banging a live.text toggle would FLIP it — never bang toggles).
autowatch = 1;
inlets = 1;
outlets = 1;

var N = parseInt(jsarguments[1] || 2, 10);
var R = 0;
var M = 0;

function grid() {
    var j, src;
    for (j = 0; j < N; j++) {
        src = M ? 0 : ((j + R) % N + N) % N;
        for (var i = 0; i < N; i++) {
            outlet(0, [i, j, (i === src) ? 1.0 : 0.0]);
        }
    }
}

function rot(v) { R = Math.round(v); grid(); }

function mono(v) { M = v ? 1 : 0; grid(); }
"""


def lane_rotator(device, id_prefix, *, n, accent=None, rotate_rect=None,
                 mono_rect=None, ramp_ms=20):
    """Rotate / Mono lane routing (catalog #23 + #24).

    A ``matrix~ n n 0.`` sits between the engine's lane signals and the
    mapping rows: ``Rotate k`` feeds row ``j`` from lane ``(j+k) % n``;
    ``Mono`` collapses every row onto lane 0. A tiny js recomputes the FULL
    n×n crosspoint grid on every change (matrix~ crosspoints persist, so
    partial updates would leave stale connections).

    Ports: ``lane_in_<k>`` (matrix~ signal inlets) and ``row_out_<k>``
    (matrix~ signal outlets) — wire lanes in, rows out. Params: ``Rotate``
    (int 0..n-1) + ``Mono`` (toggle), both automatable.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec

    p = id_prefix
    if n < 2:
        raise ValueError("lane_rotator: n must be >= 2")
    acc = list(accent) if accent else [0.85, 0.87, 0.89, 1.0]

    code = _LANE_ROTATOR_JS
    fname = js_sidecar_name("lane_rotator.js", code)
    device.register_asset(fname, code, asset_type="TEXT", category="js")

    mx = device.add_newobj(
        f"{p}_mx", f"matrix~ {n} {n} 0. @ramp {int(ramp_ms)}",
        numinlets=n + 1, numoutlets=n + 1,
        outlettype=["signal"] * n + [""],
        patching_rect=[600, 2000, 60 + 26 * n, 22])
    device.add_number_box(
        f"{p}_rot", "Rotate", rotate_rect or [900, 900, 1, 1],
        min_val=0.0, max_val=float(n - 1), initial=0.0, lcdcolor=acc,
        parameter=ParameterSpec(name="Rotate", shortname="Rotate",
                                parameter_type=1, minimum=0, maximum=n - 1,
                                initial=[0], initial_enable=True))
    device.add_live_text(
        f"{p}_mono", "Mono", mono_rect or [900, 900, 1, 1],
        text_on="MONO", text_off="MONO", mode=1, fontsize=7.0,
        annotation="Collapse every row onto lane 1's output.",
        parameter=ParameterSpec(name="Mono", shortname="Mono",
                                parameter_type=2, enum=["OFF", "ON"],
                                initial=[0], initial_enable=True))
    js = device.add_newobj(
        f"{p}_js", f"js {fname} {n}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[600, 1970, 160, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    pre_r = device.add_newobj(f"{p}_pre_r", "prepend rot", numinlets=1,
                              numoutlets=1, outlettype=[""],
                              patching_rect=[600, 1940, 80, 20])
    pre_m = device.add_newobj(f"{p}_pre_m", "prepend mono", numinlets=1,
                              numoutlets=1, outlettype=[""],
                              patching_rect=[690, 1940, 90, 20])
    device.add_line(f"{p}_rot", 0, pre_r, 0)
    device.add_line(f"{p}_mono", 0, pre_m, 0)
    device.add_line(pre_r, 0, js, 0)
    device.add_line(pre_m, 0, js, 0)
    device.add_line(js, 0, mx, 0)
    # matrix~ crosspoints all start at 0 and live params do NOT reliably
    # re-emit initials at load — bang the ROTATE numbox (bang on live.numbox
    # re-OUTPUTS; never bang a live.text toggle, that FLIPS it) so the grid
    # computes at every load. Mono/Rotate changes recompute statefully.
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[600, 1880, 90, 20])
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[600, 1910, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, f"{p}_rot", 0)
    ports = {}
    for k in range(n):
        ports[f"lane_in_{k}"] = device.box(mx).inlet(k)
        ports[f"row_out_{k}"] = device.box(mx).outlet(k)
    return stage_result(
        {"matrix": f"{p}_mx", "rotate": f"{p}_rot", "mono": f"{p}_mono"},
        name="lane_rotator",
        params={"Rotate": device.parameter(device.box(f"{p}_rot")),
                "Mono": device.parameter(device.box(f"{p}_mono"))},
        ports=ports,
    )


def page_selector(device, id_prefix, *, at, n_pages, rows_per_page,
                  accent=None, cell=14, param_name="Page", manage=None):
    """Vertical page selector for stacked mapping rows (catalog #25).

    A slim vertical ``live.tab`` (one dot-cell per page, automatable enum
    ``param_name``). Rows are 1-based: page ``k`` shows rows
    ``k*rows_per_page+1 .. (k+1)*rows_per_page``.

    ``manage``: dict of ``{parent_box_varname: 1-based_row_index}`` — the
    hiding path: the parent computes each managed box's hidden state and
    delivers it via ``script sendbox <varname> hidden $1`` through a
    parent-side thispatcher (the exact mode_stack mechanism). This is the
    only supported page-hiding path — a thispatcher INSIDE a stamped bpatcher
    does NOT hide the containing box (Live-verified failure), which is why the
    slot-side ``pages=`` broadcast (and this stage's old ``pagewin_out`` port)
    were removed.
    """
    from .parameters import ParameterSpec
    from .ui import tab

    p = id_prefix
    x, y = at
    labels = [str(k + 1) for k in range(n_pages)]
    device.add_box(tab(
        f"{p}_tab", param_name, [x, y, cell, cell * n_pages],
        options=labels, fontsize=6.5, multiline=1,
        num_lines_presentation=n_pages, num_lines_patching=n_pages,
        spacing_x=1.0, spacing_y=1.0,
        annotation="Mapping page — rows swap in groups at the same rect.",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2, enum=list(labels),
                                initial=[0], initial_enable=True)))
    # re-broadcast at load so freshly-restored pages re-hide their off rows
    # (the manage= exprs below listen to the tab)
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[840, 1880, 90, 20])
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[840, 1910, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, f"{p}_tab", 0)
    if manage:
        thisp = device.add_newobj(f"{p}_this", "thispatcher", numinlets=1,
                                  numoutlets=2, outlettype=["", ""],
                                  patching_rect=[1000, 2060, 80, 20])
        r = int(rows_per_page)
        for mi, (vn, idx) in enumerate(sorted(manage.items())):
            if " " in vn:
                raise ValueError(
                    f"page_selector: managed varname {vn!r} contains a "
                    "space — script sendbox silently no-ops")
            i0 = int(idx) - 1
            ex = device.add_newobj(
                f"{p}_mx{mi}",
                f"expr ({i0} < $i1 * {r}) || ({i0} > ($i1 * {r} + {r - 1}))",
                numinlets=1, numoutlets=1, outlettype=[""],
                patching_rect=[1000, 1940 + 30 * mi, 230, 20])
            device.add_box({"box": {
                "id": f"{p}_mm{mi}", "maxclass": "message",
                "text": f"script sendbox {vn} hidden $1",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [1240, 1940 + 30 * mi, 200, 20]}})
            device.add_line(f"{p}_tab", 0, ex, 0)
            device.add_line(ex, 0, f"{p}_mm{mi}", 0)
            device.add_line(f"{p}_mm{mi}", 0, thisp, 0)
    return stage_result(
        {"tab": f"{p}_tab"},
        name="page_selector",
        params={param_name: device.parameter(device.box(f"{p}_tab"))},
    )


def takeover_menu(device, id_prefix, *, rect, policies=("Latest", "Hold",
                                                        "Pickup"),
                  param_name="Takeover", accent=None):
    """Takeover policy menu (catalog #27, Chordsaus): how an incoming
    control merges with mapped/engine values. The recipe is the CONTRACT
    layer — an automatable enum + a ``policy_out`` port; the semantics are
    engine-side (wire ``policy_out`` into whatever merges your sources).
    Pair with :func:`randomize_matrix` ``variation=True`` for Chordsaus'
    Random-Variation half of the panel.
    """
    from .parameters import ParameterSpec
    from .ui import menu as _menu

    p = id_prefix
    device.add_box(_menu(
        f"{p}_menu", param_name, list(rect), options=list(policies),
        fontsize=8.0,
        annotation="How incoming control input merges with the mapped "
                   "value: Latest wins / Hold until release / Pickup on "
                   "value cross.",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2, enum=list(policies),
                                initial=[0], initial_enable=True)))
    return stage_result(
        {"menu": f"{p}_menu"},
        name="takeover_menu",
        params={param_name: device.parameter(device.box(f"{p}_menu"))},
        ports={"policy_out": device.box(f"{p}_menu").outlet(0)},
    )


def mod_source_matrix(device, id_prefix, *, rect, sources, n_targets,
                      param_name="Mod Matrix", accent=None, dim_color=None):
    """Mod-source routing matrix (catalog #28, Chordsaus): ``sources`` ×
    ``n_targets`` grid of toggle cells — MPE dimensions (or any control
    streams) as routable mod sources per target.

    Persistence rides the CORPUS-PROVEN path: the ``matrixctrl`` itself is a
    Blob parameter (``parameter_type=3`` stores the whole grid with the
    set). Cell edits stream out ``cells_out`` as ``<col> <row> <val>`` for
    the engine's routing (e.g. a ``router``/``matrix~`` recompute); source
    captions render down the left edge.
    """
    from .parameters import ParameterSpec
    from .ui import matrixctrl as _mc

    p = id_prefix
    n_src = len(sources)
    if n_src < 1 or n_targets < 1:
        raise ValueError("mod_source_matrix: need >=1 sources and targets")
    if n_src * int(n_targets) > 64:
        raise ValueError("mod_source_matrix: grid larger than 64 cells")
    x, y, w, h = rect
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    cap_w = 34
    grid_rect = [x + cap_w, y, w - cap_w, h]
    row_h = h / float(n_src)
    for si, name in enumerate(sources):
        device.add_comment(f"{p}_cap{si}",
                           [x, y + int(si * row_h) + 2, cap_w - 2, 8],
                           str(name), textcolor=dim, fontsize=5.8)
    spec = ParameterSpec(name=param_name, shortname=param_name,
                         parameter_type=3, initial_enable=None)
    box = _mc(f"{p}_mc", grid_rect, rows=n_src, columns=int(n_targets),
              parameter_enable=1,
              saved_attribute_attributes=spec.to_saved_attributes())
    if accent:
        box["box"]["color"] = list(accent)
    device.add_box(box)
    return stage_result(
        {"matrix": f"{p}_mc", "captions": [f"{p}_cap{i}"
                                           for i in range(n_src)]},
        name="mod_source_matrix",
        params={param_name: device.parameter(device.box(f"{p}_mc"))},
        ports={"cells_out": device.box(f"{p}_mc").outlet(0),
               "cells_in": device.box(f"{p}_mc").inlet(0)},
    )


_CHIP_KINDS = {
    "unit_hz_note": ("Hz", "♪", ["Hz", "Note"],
                     "Rate unit — free Hz or tempo-synced note divisions."),
    "log_lin": ("LIN", "LOG", ["Lin", "Log"],
                "Scale mode for the paired control's response curve."),
    "x10": ("×1", "×10", ["x1", "x10"],
            "Range multiplier — scales the paired knob's range by 10."),
    "retrig": ("R", "R", ["Free", "Retrig"],
               "Retrigger — restart the generator's phase on each trigger."),
    "hold": ("HOLD", "HOLD", ["Off", "Hold"],
             "Hold — freeze the current output value while lit."),
    "auto": ("A", "A", ["Manual", "Auto"],
             "Auto — the paired control follows the signal; moving it "
             "manually takes over."),
}


def standard_chip(device, id_prefix, kind, rect, *, param_name=None,
                  accent=None, dim_color=None, fontsize=6.5):
    """The micro-chip vocabulary as one factory (catalog #31 #32
    #33 #37): tiny 2-state ``live.text`` chips with STANDARD semantics —
    ``unit_hz_note`` (f/Hz vs ♪ unit mode), ``log_lin``, ``x10`` (range
    multiplier — its ``factor_out`` port emits 1 or 10 for the engine),
    ``retrig`` (R), ``hold``, ``auto`` (A). One spelling fleet-wide instead
    of per-device one-offs; annotations ship the Info-View text.
    """
    from .parameters import ParameterSpec
    from .ui import live_text

    if kind not in _CHIP_KINDS:
        raise ValueError(
            f"standard_chip: unknown kind {kind!r} — one of "
            f"{sorted(_CHIP_KINDS)}")
    off, on, enum, annotation = _CHIP_KINDS[kind]
    p = id_prefix
    name = param_name or f"{p} {kind}"
    acc = list(accent) if accent else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    device.add_box(live_text(
        f"{p}_chip", name, list(rect), text_on=on, text_off=off, mode=1,
        fontsize=fontsize, bgoncolor=acc, textcolor=dim,
        annotation=annotation,
        parameter=ParameterSpec(name=name, shortname=name[:15],
                                parameter_type=2, enum=list(enum),
                                initial=[0], initial_enable=True)))
    ports = {"value_out": device.box(f"{p}_chip").outlet(0)}
    if kind == "x10":
        fac = device.add_newobj(f"{p}_fac", "expr int(pow(10\\, $i1))",
                                numinlets=1, numoutlets=1, outlettype=[""],
                                patching_rect=[700, 2200, 140, 20])
        device.add_line(f"{p}_chip", 0, fac, 0)
        ports["factor_out"] = device.box(fac).outlet(0)
    return stage_result(
        {"chip": f"{p}_chip"},
        name="standard_chip",
        params={name: device.parameter(device.box(f"{p}_chip"))},
        ports=ports,
    )


_PARAM_LINK_JS = """// param_link — linked/opposing dual-value pair (T09, catalog #34;
// generalizes gma-clp_keymod's paramGroups). Modes: mirror (linked values
// move by the SAME delta) / oppose (maximizer workflow: inverse delta).
// An `updating` guard kills setvalueof re-entry feedback.
autowatch = 1;
inlets = 1;
outlets = 0;

var VN_A = "" + jsarguments[1];
var VN_B = "" + jsarguments[2];
var MODE = ("" + jsarguments[3]) === "oppose" ? -1 : 1;

var linked = 0;
var vals = {};
var updating = false;

function link(v) { linked = v ? 1 : 0; }

function a(v) { _moved(VN_A, VN_B, v); }

function b(v) { _moved(VN_B, VN_A, v); }

function _moved(src, dst, v) {
    if (updating) { vals[src] = v; return; }
    var prev = (src in vals) ? vals[src] : v;
    vals[src] = v;
    if (!linked) return;
    var delta = (v - prev) * MODE;
    if (delta === 0) return;
    var box = this.patcher.getnamed(dst);
    if (!box) return;
    var cur = parseFloat(box.getvalueof());
    updating = true;
    try { box.setvalueof(cur + delta); vals[dst] = cur + delta; }
    catch (e) {}
    updating = false;
}
"""


def param_link(device, id_prefix, *, a, b, mode="mirror", link_rect,
               accent=None, dim_color=None, param_name=None):
    """Linked dual-value pair with a ⇄ chain chip (catalog #34) — and, with ``mode="oppose"``, an inverse-link "maximizer
    workflow" (moving one param applies the INVERSE delta to its partner).

    ``a`` / ``b``: space-free VARNAMES of two existing param controls. While
    the chip is lit, moving either applies the (mirrored or opposed) delta
    to the other through ``setvalueof`` with a re-entry guard — Live sees
    ordinary edits on both.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec

    p = id_prefix
    for vn in (a, b):
        if " " in vn:
            raise ValueError(f"param_link: varname {vn!r} contains a space "
                             "(patcher.getnamed addressing)")
    if mode not in ("mirror", "oppose"):
        raise ValueError("param_link: mode must be 'mirror' or 'oppose'")
    acc = list(accent) if accent else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    name = param_name or f"{a}·{b} Link"
    glyph = "⇄" if mode == "mirror" else "⇅"
    device.add_live_text(
        f"{p}_chip", name, list(link_rect), text_on=glyph, text_off=glyph,
        mode=1, fontsize=8.0, bgoncolor=acc, textcolor=dim,
        annotation=("Link — both values move together." if mode == "mirror"
                    else "Opposing link — raising one lowers the other by "
                         "the same amount (maximizer workflow)."),
        parameter=ParameterSpec(name=name, shortname="Link",
                                parameter_type=2, enum=["Off", "On"],
                                initial=[0], initial_enable=True))
    fname = js_sidecar_name("param_link.js", _PARAM_LINK_JS)
    device.register_asset(fname, _PARAM_LINK_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname} {a} {b} {mode}", numinlets=1, numoutlets=0,
        patching_rect=[700, 2300, 220, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    for tag, vn in (("a", a), ("b", b)):
        pre = device.add_newobj(f"{p}_pre_{tag}", f"prepend {tag}",
                                numinlets=1, numoutlets=1, outlettype=[""],
                                patching_rect=[700, 2230 + (0 if tag == "a"
                                                            else 30), 90, 20])
        device.add_line(vn, 0, pre, 0)
        device.add_line(pre, 0, js, 0)
    prel = device.add_newobj(f"{p}_pre_l", "prepend link", numinlets=1,
                             numoutlets=1, outlettype=[""],
                             patching_rect=[700, 2200, 90, 20])
    device.add_line(f"{p}_chip", 0, prel, 0)
    device.add_line(prel, 0, js, 0)
    return stage_result(
        {"chip": f"{p}_chip", "js": f"{p}_js"},
        name="param_link",
        params={name: device.parameter(device.box(f"{p}_chip"))},
        ports={},
    )


def dim_steppers(device, id_prefix, *, dims, at, cell_w=34, gap=4,
                 accent="0.30, 0.80, 0.84"):
    """Compact multi-dimension stepper cluster (catalog #38, Liquid Mask
    "X 3 Y 1 Z 1 W 1"): one :meth:`add_custom_stepper` per dim in a row.
    ``dims``: list of ``(letter, vmin, vmax, initial)``.
    """
    p = id_prefix
    x, y = at
    made = []
    params = {}
    for i, (letter, vmin, vmax, init) in enumerate(dims):
        sid = f"{p}_{letter.lower()}"
        device.add_custom_stepper(
            sid, str(letter), [x + i * (cell_w + gap), y, cell_w, 15],
            vmin=float(vmin), vmax=float(vmax), initial=float(init),
            step=1.0, decimals=0, label=str(letter), accent=accent)
        made.append(sid)
        params[str(letter)] = device.parameter(str(letter))
    return stage_result({"steppers": made}, name="dim_steppers",
                        params=params, ports={})


def ghost_label(device, id_prefix, *, rect, text, accent, dim_color=None,
                fontsize=9.0):
    """Ghosted state label (catalog #39, Live Stretch "Reverse Stretch"):
    the label sits dimmed until the mode ENGAGES, then lights in accent —
    state-as-typography. Corpus mechanism (Prob v1.1 Thru/Blocked): TWO
    same-rect comments swapped via parent-side ``script sendbox <id>
    hidden`` (the Live-proven bus). Wire an int 0/1 into ``state_in``.
    """
    p = id_prefix
    dim = list(dim_color) if dim_color else [0.42, 0.44, 0.47, 1.0]
    device.add_comment(f"{p}_off", list(rect), text, textcolor=dim,
                       fontsize=fontsize)
    device.boxes[-1]["box"]["varname"] = f"{p}_off"
    device.add_comment(f"{p}_on", list(rect), text, textcolor=list(accent),
                       fontsize=fontsize)
    device.boxes[-1]["box"]["varname"] = f"{p}_on"
    device.boxes[-1]["box"]["hidden"] = 1
    tt = device.add_newobj(f"{p}_t", "t i i", numinlets=1, numoutlets=2,
                           outlettype=["int", "int"],
                           patching_rect=[700, 2400, 40, 20])
    inv = device.add_newobj(f"{p}_inv", "!- 1", numinlets=2, numoutlets=1,
                            outlettype=["int"],
                            patching_rect=[760, 2430, 40, 20])
    device.add_box({"box": {
        "id": f"{p}_m_on", "maxclass": "message",
        "text": f"script sendbox {p}_on hidden $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [700, 2460, 190, 20]}})
    device.add_box({"box": {
        "id": f"{p}_m_off", "maxclass": "message",
        "text": f"script sendbox {p}_off hidden $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [700, 2490, 190, 20]}})
    thisp = device.add_newobj(f"{p}_this", "thispatcher", numinlets=1,
                              numoutlets=2, outlettype=["", ""],
                              patching_rect=[700, 2520, 80, 20])
    device.add_line(tt, 1, inv, 0)          # right first: on-label hidden=!s
    device.add_line(inv, 0, f"{p}_m_on", 0)
    device.add_line(tt, 0, f"{p}_m_off", 0)  # off-label hidden=s
    device.add_line(f"{p}_m_on", 0, thisp, 0)
    device.add_line(f"{p}_m_off", 0, thisp, 0)
    return stage_result(
        {"on": f"{p}_on", "off": f"{p}_off"},
        name="ghost_label",
        params={},
        ports={"state_in": device.box(tt).inlet(0)},
    )


def mode_pill(device, id_prefix, *, rect, modes, param_name="Mode",
              accent="0.30, 0.80, 0.84", dim_color=None):
    """Mode pill whose icon IS the behavior (catalog #36 — "◠ Pump
    Mode"): a glyph selector where each mode's icon is a transfer-curve /
    response glyph from the shared bank (``lowpass`` ``bell`` ``fold`` …),
    with the current mode's LABEL rendered beside it. ``modes``: list of
    ``(label, glyph_name)``.

    Composition: :meth:`Device.add_mode_glyph_selector` (glyph row bound to
    a hidden automatable tab) + a label textedit that follows the selection
    (fed ready-made ``set <label>`` messages).
    """
    p = id_prefix
    x, y, w, h = rect
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    glyph_w = min(len(modes) * (h + 2), w - 34)
    sel_id = device.add_mode_glyph_selector(
        f"{p}_sel", param_name, [x, y, glyph_w, h],
        glyphs=[g for (_l, g) in modes],
        option_labels=[lbl for (lbl, _g) in modes],
        accent=accent)
    from .ui import textedit
    device.add_box(textedit(
        f"{p}_lbl", [x + glyph_w + 4, y + 2, w - glyph_w - 4, h - 2],
        text=str(modes[0][0]), fontsize=7.5, textcolor=dim,
        bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    for mi, (label, _g) in enumerate(modes):
        sel = device.add_newobj(f"{p}_s{mi}", f"select {mi}", numinlets=2,
                                numoutlets=2, outlettype=["bang", ""],
                                patching_rect=[700, 2560 + mi * 30, 60, 20])
        device.add_box({"box": {
            "id": f"{p}_m{mi}", "maxclass": "message", "text": f"set {label}",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [780, 2560 + mi * 30, 100, 20]}})
        device.add_line(sel_id, 0, sel, 0)
        device.add_line(sel, 0, f"{p}_m{mi}", 0)
        device.add_line(f"{p}_m{mi}", 0, f"{p}_lbl", 0)
    return stage_result(
        {"selector": sel_id, "label": f"{p}_lbl"},
        name="mode_pill",
        params={param_name: device.parameter(device.box(sel_id))
                if device.parameter(device.box(sel_id)) else None},
        ports={},
    )


def display_header(device, id_prefix, *, rect, title, accent,
                   gain=False, gain_name="Out Gain", mute_name="Mute",
                   text_color=None, dim_color=None):
    """Graph-header output strip (catalog #35): a MUTE pill and an
    inline gain-dB LCD fused into a display's ~15px title row. Ports:
    ``mute_out`` (0/1) and ``gain_out`` (dB float) for the engine's output
    stage. All in one strip so the graph keeps every vertical pixel.
    """
    from .parameters import ParameterSpec
    from .ui import live_text, number_box, textedit

    p = id_prefix
    x, y, w, h = rect
    tx = list(text_color) if text_color else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    acc = list(accent)
    device.add_box(live_text(
        f"{p}_mute", mute_name, [x, y + 1, 26, h - 2], text_on="M",
        text_off="M", mode=1, fontsize=7.0, bgoncolor=acc, textcolor=dim,
        annotation="Mute this display's output.",
        parameter=ParameterSpec(name=mute_name, shortname="Mute",
                                parameter_type=2, enum=["Off", "Mute"],
                                initial=[0], initial_enable=True)))
    gain_w = 46 if gain else 0
    device.add_box(textedit(
        f"{p}_title", [x + 30, y + 2, w - 34 - gain_w, h - 4],
        text=str(title), fontsize=7.5, textcolor=tx,
        bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    ports = {"mute_out": device.box(f"{p}_mute").outlet(0)}
    if gain:
        device.add_box(number_box(
            f"{p}_gain", gain_name, [x + w - gain_w, y + 1, gain_w, h - 2],
            min_val=-24.0, max_val=12.0, initial=0.0, lcdcolor=acc,
            parameter=ParameterSpec(name=gain_name, shortname="Gain",
                                    minimum=-24.0, maximum=12.0,
                                    initial=0.0, initial_enable=True,
                                    units="%.1f dB", unitstyle=9)))
        ports["gain_out"] = device.box(f"{p}_gain").outlet(0)
    return stage_result(
        {"mute": f"{p}_mute", "title": f"{p}_title"},
        name="display_header",
        params={mute_name: device.parameter(device.box(f"{p}_mute"))},
        ports=ports,
    )


def hero_readout(device, id_prefix, *, rect, accent, fontsize=34.0,
                 initial="—"):
    """Giant hero READOUT (catalog #41, Bass Lock "G0"): the value IS the
    hero — 34px+ display type on a transparent field. Feed ready-made
    ``set <text…>`` messages into ``text_in`` (corpus alternative for pure
    numerics: a giant ``appearance=4`` live.numbox, Prob v1.1).
    """
    from .ui import textedit

    p = id_prefix
    device.add_box(textedit(
        f"{p}_txt", list(rect), text=str(initial), fontsize=float(fontsize),
        textcolor=list(accent), bgcolor=[0.0, 0.0, 0.0, 0.0], border=0,
        rounded=0, textjustification=1, ignoreclick=1))
    return stage_result(
        {"text": f"{p}_txt"},
        name="hero_readout",
        params={},
        ports={"text_in": device.box(f"{p}_txt").inlet(0)},
    )


_NOTE_HZ_JS = """// note_hz — Hz -> "C#0 · 34.6 Hz" dual readout feed (T10, catalog #42)
autowatch = 1;
inlets = 1;
outlets = 2;   // 0: "set <note> · <hz> Hz" (dual)   1: "set <note>" (hero)

var NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function msg_float(hz) {
    if (hz <= 0) return;
    var midi = 69.0 + 12.0 * Math.log(hz / 440.0) / Math.LN2;
    var n = Math.round(midi);
    var name = NAMES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 2);
    var hztxt = (hz >= 100 ? hz.toFixed(0) : hz.toFixed(1));
    outlet(1, ["set", name]);
    outlet(0, ["set", name, "\\u00b7", hztxt, "Hz"]);
}

function msg_int(v) { msg_float(v); }
"""


def note_hz_readout(device, id_prefix, *, rect, accent, text_color=None,
                    fontsize=8.0):
    """Live note+Hz dual readout (catalog #42, a note+Hz readout): feed a
    frequency into ``hz_in`` and the strip shows note-name · Hz; the
    ``hero_feed`` outlet carries a ready ``set <note>`` for a paired
    :func:`hero_readout`.
    """
    from .engines.design_system import js_sidecar_name
    from .ui import textedit

    p = id_prefix
    tx = list(text_color) if text_color else list(accent)
    fname = js_sidecar_name("note_hz.js", _NOTE_HZ_JS)
    device.register_asset(fname, _NOTE_HZ_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[700, 2700, 120, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    device.add_box(textedit(
        f"{p}_txt", list(rect), text="—", fontsize=float(fontsize),
        textcolor=tx, bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=1, ignoreclick=1))
    device.add_line(js, 0, f"{p}_txt", 0)
    return stage_result(
        {"text": f"{p}_txt", "js": f"{p}_js"},
        name="note_hz_readout",
        params={},
        ports={"hz_in": device.box(js).inlet(0),
               "hero_feed": device.box(js).outlet(1)},
    )


_PROGRESS_TICK_JS = """// progress_tick — phase dash under a display (T10, catalog #43)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 0;

var phase = 0.0;
var COL = [ACCENT];
var BGC = [0.05, 0.06, 0.09, 1.0];

function msg_float(v) {
    phase = Math.max(0, Math.min(1, v));
    mgraphics.redraw();
}

function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1];
    mgraphics.set_source_rgba(BGC);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();
    mgraphics.set_source_rgba(COL);
    var x = phase * (w - 6);
    mgraphics.rectangle(x, 0, 6, h);
    mgraphics.fill();
}
"""


def progress_tick(device, id_prefix, *, rect, accent):
    """LFO-phase progress tick (catalog #43): a tiny dash sweeping
    a 3-4px strip under a display. Feed phase 0..1 floats into ``phase_in``
    at UI rate (e.g. ``phasor~ → snapshot~ 50``).
    """
    from .engines.design_system import js_sidecar_name

    p = id_prefix
    acc = ", ".join(f"{float(c):.4g}" for c in list(accent)[:4])
    code = _PROGRESS_TICK_JS.replace("ACCENT", acc)
    fname = js_sidecar_name("progress_tick.js", code)
    device.register_asset(fname, code, asset_type="TEXT", category="js")
    device.add_box({"box": {
        "id": f"{p}_ui", "maxclass": "jsui", "filename": fname,
        "jsui_maxclass": "jsui",
        "numinlets": 1, "numoutlets": 1, "outlettype": [""],
        "parameter_enable": 0, "border": 0,
        "presentation": 1, "presentation_rect": list(rect),
        "patching_rect": [700, 2760, rect[2], rect[3]]}})
    return stage_result(
        {"tick": f"{p}_ui"},
        name="progress_tick",
        params={},
        ports={"phase_in": device.box(f"{p}_ui").inlet(0)},
    )
