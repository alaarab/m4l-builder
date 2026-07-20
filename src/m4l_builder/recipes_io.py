"""Recipes: io — split out of recipes.py; re-exported by m4l_builder.recipes."""

from .stages import stage_result

_API_ROUTING_JS = """\
/* apirouting.js - Live IO routing chooser driver (API-routing pattern,
   Live-proven in Pocket Delay).
   Args: 1 = audio_inputs|audio_outputs, 2 = io index (0 = plugin~ 1 2,
   1 = plugin~ 3 4, ...). Outlet 0 -> type menu, outlet 1 -> channel menu. */
this.autowatch = 1;
this.outlets = 2;
var initInpName = this.jsarguments[1] || "audio_inputs";
var initInpIndex = this.jsarguments[2] || 0;
var noCallback = false, apiInit = false, initNoCB = false;
var ioName, ioIndex, idIndex, device, tas, ioObj;

function anything() {
    if (noCallback) return;
    var params = arrayfromargs(arguments).slice();
    if (messagename === "setTrack") { routing.setTrack(params[0]); return; }
    if (messagename === "setChannel") { routing.setChannel(params[0]); return; }
    if (messagename === "resetRouting") { routing.resetRouting(); return; }
}

var initTask = null, initTries = 0;

function initialize(inpName, inpIndex) {
    ioName = inpName || initInpName;
    ioIndex = (inpIndex !== undefined && inpIndex !== null) ? inpIndex : initInpIndex;
    idIndex = (+ioIndex) * 2 + 1;
    initTries = 0;
    attemptInit();
}

function attemptInit() {
    /* LiveAPI is NOT ready at the instant live.thisdevice bangs on an
       API-driven insert (the documented hot-load trap) - guard + Task
       retry until the device resolves. */
    initNoCB = true;
    device = new LiveAPI(deviceChanged, "live_set this_device");
    if (!device || +device.id === 0
            || device.children.indexOf(ioName) === -1) {
        initTries += 1;
        if (initTries < 12) {
            if (!initTask) initTask = new Task(attemptInit);
            initTask.schedule(250);
        }
        return;
    }
    initNoCB = false;
    /* Seed synchronously: the property-observer initial fire proved
       unreliable for midi_inputs on hot-loaded devices (T13b) while a
       direct get() returns the port ids immediately. The observer stays
       armed for hot routing changes. */
    var ids = device.get(ioName);
    if (ids && ids.length > idIndex && ids[idIndex]) {
        ioObj = new LiveAPI(execDefered, "id " + ids[idIndex]);
        ioObj.property = "routing_type";
        apiInit = true;
        execDefered();
    }
    device.property = ioName;
}

function deviceChanged(arg1) {
    if (initNoCB) return;
    var ioIdsList = arg1.slice(1);
    if (idIndex < 0 || ioIdsList.length <= idIndex) return;
    ioObj = new LiveAPI(execDefered, "id " + ioIdsList[idIndex]);
    ioObj.property = "routing_type";
    apiInit = true;
    execDefered();
}

function execDefered() {
    if (!apiInit) return;
    if (ioObj.id == 0) return;
    if (!tas) tas = new Task(routing.routingChanged, routing);
    tas.schedule();
}

var routing = {
    routingChanged: function () {
        this.updateLists();
        setMenu(0, this.getNames("available_routing_types"),
                this.getIndex("routing_type"));
        setMenu(1, this.getNames("available_routing_channels"),
                this.getIndex("routing_channel"));
    },
    getIndex: function (apiProperty) {
        return this.getNames("available_" + apiProperty + "s")
            .indexOf(this.getApiObj(apiProperty).display_name);
    },
    getNames: function (apiProperty) {
        var tmp = [];
        for (var i in this[apiProperty])
            tmp.push(this[apiProperty][i].display_name || " ");
        return tmp;
    },
    updateLists: function () {
        var propNames = ["available_routing_types", "available_routing_channels"];
        for (var i in propNames)
            this[propNames[i]] = this.getApiObj(propNames[i]);
    },
    getApiObj: function (apiProperty) {
        return JSON.parse(ioObj.get(apiProperty))[apiProperty]
            || { display_name: "" };
    },
    setApiRouting: function (apiProperty, index) {
        ioObj.set(apiProperty,
                  { identifier: this["available_" + apiProperty + "s"][index].identifier });
    },
    resetRouting: function () {
        this.setTrack(this.getNames("available_routing_types").length - 1);
    },
    setTrack: function (index) { if (!apiInit) return; this.setApiRouting("routing_type", index); },
    setChannel: function (index) { if (!apiInit) return; this.setApiRouting("routing_channel", index); }
};

function setMenu(port, list, value) {
    var output = list.slice();
    while (output.length < 2) output.push(" ");
    noCallback = true;
    outlet(port, "_parameter_range", output);
    noCallback = false;
    outlet(port, "ignoreclick", list.length < 2 ? 1 : 0);
    if (value || value === 0) outlet(port, "set", value);
}
setMenu.local = 1;
"""


def io_routing_menus(device, id_prefix, *, io="midi_inputs", io_index=0,
                     type_rect, chan_rect, type_name="Source",
                     chan_name="Channel", placeholder="No Input",
                     fontsize=8.0):
    """Live IO routing chooser (catalog #54, a MIDI-From chooser; the same
    API-routing driver Live-proven on Pocket Delay's audio REF):
    two menus (type + channel) enumerating the set's routable sources for
    this device's ``io`` (``midi_inputs`` / ``audio_inputs`` /
    ``…_outputs``), observing ``routing_type`` and setting the choice back
    by identifier. Menus fill at load via ``live.thisdevice`` — the LiveAPI
    is NOT ready at loadbang (Live-verified gotcha).

    The menus are ``parameter_invisible=2`` (saved, out of automation).
    Consume the routed stream with a plain ``midiin``/``plugin~`` as usual.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec
    from .ui import menu as _menu

    p = id_prefix
    fname = js_sidecar_name("apirouting.js", _API_ROUTING_JS)
    device.register_asset(fname, _API_ROUTING_JS, asset_type="TEXT",
                          category="js")
    for mid, mname, rect, opts in (
            (f"{p}_menu_type", type_name, type_rect, [placeholder, "\u2014"]),
            (f"{p}_menu_chan", chan_name, chan_rect, ["\u2014", "\u2014 "])):
        device.add_box(_menu(
            mid, mname, list(rect), options=opts, fontsize=fontsize,
            annotation=f"Routing {mname.lower()} for this device's "
                       f"{io.replace('_', ' ')}.",
            parameter=ParameterSpec(name=mname, shortname=mname[:15],
                                    parameter_type=2, enum=list(opts),
                                    initial=[0], initial_enable=True,
                                    invisible=2)))
    js = device.add_newobj(
        f"{p}_api", f"js {fname} {io} {int(io_index)}",
        numinlets=1, numoutlets=2, outlettype=["", ""],
        patching_rect=[900, 2800, 200, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    device.add_box({"box": {
        "id": f"{p}_init", "maxclass": "message", "text": "initialize",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [900, 2770, 70, 20]}})
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 2740, 90, 20])
    st = device.add_newobj(f"{p}_set_t", "prepend setTrack", numinlets=1,
                           numoutlets=1, outlettype=[""],
                           patching_rect=[900, 2840, 110, 20])
    sc = device.add_newobj(f"{p}_set_c", "prepend setChannel", numinlets=1,
                           numoutlets=1, outlettype=[""],
                           patching_rect=[1020, 2840, 130, 20])
    device.add_line(td, 0, f"{p}_init", 0)
    device.add_line(f"{p}_init", 0, js, 0)
    device.add_line(js, 0, f"{p}_menu_type", 0)
    device.add_line(js, 1, f"{p}_menu_chan", 0)
    device.add_line(f"{p}_menu_type", 0, st, 0)
    device.add_line(f"{p}_menu_chan", 0, sc, 0)
    device.add_line(st, 0, js, 0)
    device.add_line(sc, 0, js, 0)
    return stage_result(
        {"api": f"{p}_api", "type_menu": f"{p}_menu_type",
         "chan_menu": f"{p}_menu_chan"},
        name="io_routing_menus",
        params={},
        ports={"api_in": device.box(js).inlet(0)},
    )


def midi_from(device, id_prefix, *, type_rect, chan_rect, io_index=0,
              with_midiin=True, **kwargs):
    """"MIDI From" chooser (catalog #54): :func:`io_routing_menus`
    over ``midi_inputs`` plus (by default) the ``midiin`` consumer whose
    source the chooser selects — its raw byte stream leaves on
    ``midi_raw_out``.
    """
    res = io_routing_menus(device, id_prefix, io="midi_inputs",
                           io_index=io_index, type_rect=type_rect,
                           chan_rect=chan_rect, **kwargs)
    if with_midiin:
        p = id_prefix
        mi = device.add_newobj(f"{p}_midiin", "midiin", numinlets=1,
                               numoutlets=1, outlettype=["int"],
                               patching_rect=[900, 2900, 50, 20])
        res.ports["midi_raw_out"] = device.box(mi).outlet(0)
        res["midiin"] = f"{p}_midiin"
    return res


_SCALE_AWARE_JS = """/* scale_aware.js - Live 12 set scale observer + note folder (T14, #53).
   Observes live_set root_note / scale_name / scale_intervals; outlet 0
   feeds the scale chip ("set F Minor"), outlet 1 emits `root <n>` +
   `intervals <list>` for engines, and `note <n>` messages fold to the
   nearest in-scale pitch and leave outlet 2. */
this.autowatch = 1;
this.outlets = 3;

var NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
var apiRoot = null, apiName = null, apiIvals = null;
var root = 0, scaleName = "Major", ivals = [0, 2, 4, 5, 7, 9, 11];
var retryTask = null;

function initialize() {
    apiRoot = new LiveAPI(onchange, "live_set");
    apiRoot.property = "root_note";
    apiName = new LiveAPI(onchange, "live_set");
    apiName.property = "scale_name";
    apiIvals = new LiveAPI(onchange, "live_set");
    apiIvals.property = "scale_intervals";
    refresh();
    // hot-load window: live_set get() can be unresolved at thisdevice time
    retryTask = new Task(refresh);
    retryTask.schedule(250);
}

function onchange() { refresh(); }

function refresh() {
    if (!apiRoot) return;
    var r, nm, iv;
    try {
        r = apiRoot.get("root_note");
        nm = apiName.get("scale_name");
        iv = apiIvals.get("scale_intervals");
    } catch (e) { return; }
    if (nm === null || nm === undefined) return;
    root = parseInt(r, 10) || 0;
    scaleName = ("" + nm).replace(/^"|"$/g, "");
    if (!scaleName) return;
    if (iv && iv.length) ivals = iv;
    outlet(1, ["intervals"].concat(ivals));
    outlet(1, ["root", root]);
    outlet(0, ["set", NAMES[root % 12], scaleName]);
}

function note(n) {
    var pc = ((n - root) % 12 + 12) % 12;
    var best = ivals[0], dist = 99;
    for (var i = 0; i < ivals.length; i++) {
        var d = Math.abs(ivals[i] - pc);
        if (d < dist) { dist = d; best = ivals[i]; }
    }
    outlet(2, n - pc + best);
}

function msg_int(n) { note(n); }
function msg_float(n) { note(Math.round(n)); }
"""


def scale_awareness(device, id_prefix, *, chip_rect, fontsize=8.0):
    """Live 12 scale awareness (catalog #53, Bass Lock / Chordsaus): observe
    the SET's root+scale, render a scale chip styled with Live's dedicated
    ``live_scale_awareness`` theme color, and fold notes to the scale.

    Ports: ``note_in`` (MIDI note int → folded note on ``folded_out``) and
    ``scale_out`` (``root <n>`` / ``intervals <list>`` for engines). Uses
    the Live 12 ``scale_intervals`` LOM property — no interval tables.
    """
    from .engines.design_system import js_sidecar_name

    p = id_prefix
    fname = js_sidecar_name("scale_aware.js", _SCALE_AWARE_JS)
    device.register_asset(fname, _SCALE_AWARE_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=3,
        outlettype=["", "", ""], patching_rect=[900, 3100, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    chip = {"box": {
        "id": f"{p}_chip", "maxclass": "textedit", "text": "—",
        "numinlets": 1, "numoutlets": 4,
        "outlettype": ["", "int", "", ""],
        "fontsize": float(fontsize), "fontname": "Ableton Sans Medium",
        "textcolor": [0.745, 0.596, 1.0, 1.0],
        "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0, "rounded": 0,
        "textjustification": 1, "ignoreclick": 1,
        "presentation": 1, "presentation_rect": list(chip_rect),
        "patching_rect": [900, 3140, chip_rect[2], chip_rect[3]],
        "saved_attribute_attributes": {
            "textcolor": {"expression": "themecolor.live_scale_awareness"}}}}
    device.add_box(chip)
    device.add_box({"box": {
        "id": f"{p}_init", "maxclass": "message", "text": "initialize",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [900, 3070, 70, 20]}})
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 3040, 90, 20])
    device.add_line(td, 0, f"{p}_init", 0)
    device.add_line(f"{p}_init", 0, js, 0)
    device.add_line(js, 0, f"{p}_chip", 0)
    return stage_result(
        {"js": f"{p}_js", "chip": f"{p}_chip"},
        name="scale_awareness",
        params={},
        ports={"note_in": device.box(js).inlet(0),
               "scale_out": device.box(js).outlet(1),
               "folded_out": device.box(js).outlet(2)},
    )


_RECORD_MIDI_JS = """/* record_midi.js - capture device MIDI into a session clip (T14, #55).
   `rec 1` starts collecting `ev <pitch> <velocity> <beats>` events
   (beats = transport beat time from plugsync~); `rec 0` writes them into
   this track's FIRST EMPTY session clip slot via the LOM. */
this.autowatch = 1;
this.outlets = 1;

var events = [];
var recording = false;
var startBeat = -1;

function rec(v) {
    if (v) { events = []; startBeat = -1; recording = true; return; }
    recording = false;
    writeClip();
}

function ev(pitch, velocity, beats) {
    if (!recording) return;
    if (startBeat < 0) startBeat = beats;
    events.push([pitch, beats - startBeat, velocity]);
}

function writeClip() {
    if (!events.length) { outlet(0, ["status", "empty"]); return; }
    var track = new LiveAPI(null, "live_set this_device canonical_parent");
    var nslots = parseInt(track.getcount("clip_slots"), 10);
    var slotIdx = -1;
    for (var i = 0; i < nslots; i++) {
        var slot = new LiveAPI(null,
            "live_set this_device canonical_parent clip_slots " + i);
        if (parseInt(slot.get("has_clip"), 10) === 0) { slotIdx = i; break; }
    }
    if (slotIdx < 0) { outlet(0, ["status", "no empty slot"]); return; }
    var last = events[events.length - 1][1] + 1.0;
    var len = Math.max(4.0, Math.ceil(last));
    var slotApi = new LiveAPI(null,
        "live_set this_device canonical_parent clip_slots " + slotIdx);
    slotApi.call("create_clip", len);
    var clip = new LiveAPI(null,
        "live_set this_device canonical_parent clip_slots " + slotIdx
        + " clip");
    var notes = [];
    for (var e = 0; e < events.length; e++) {
        notes.push({pitch: events[e][0], start_time: events[e][1],
                    duration: 0.25, velocity: events[e][2], mute: 0});
    }
    clip.call("add_new_notes", {notes: notes});
    clip.set("name", "Captured MIDI");
    outlet(0, ["status", "wrote", events.length, "notes to slot", slotIdx]);
}
"""


def record_midi(device, id_prefix, *, rect, accent=None):
    """Record-MIDI capture (catalog #55, Chordsaus): a red REC pill that
    collects the device's generated MIDI while lit and, on release, writes
    the take into this track's first empty session clip via the LOM
    (``create_clip`` + ``add_new_notes``) — the capture IS a real Live clip
    the user can drag anywhere.

    Feed note events into ``ev_in`` as ``ev <pitch> <velocity> <beats>``
    (beat time from ``plugsync~`` outlet 4's beat count or a ``timepoint``
    chain). ``status_out`` reports writes.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec
    from .ui import live_text

    p = id_prefix
    acc = list(accent) if accent else [0.90, 0.25, 0.25, 1.0]
    device.add_box(live_text(
        f"{p}_pill", "Record MIDI", list(rect), text_on="● REC",
        text_off="● REC", mode=1, fontsize=7.5, bgoncolor=acc,
        textcolor=[0.62, 0.62, 0.65, 1.0],
        annotation="Capture the device's generated MIDI; releasing writes "
                   "a clip into this track's first empty session slot.",
        parameter=ParameterSpec(name="Record MIDI", shortname="Rec MIDI",
                                parameter_type=2, enum=["Off", "Rec"],
                                initial=[0], initial_enable=True,
                                invisible=1)))
    fname = js_sidecar_name("record_midi.js", _RECORD_MIDI_JS)
    device.register_asset(fname, _RECORD_MIDI_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[900, 3220, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    pre = device.add_newobj(f"{p}_prer", "prepend rec", numinlets=1,
                            numoutlets=1, outlettype=[""],
                            patching_rect=[900, 3190, 90, 20])
    device.add_line(f"{p}_pill", 0, pre, 0)
    device.add_line(pre, 0, js, 0)
    return stage_result(
        {"pill": f"{p}_pill", "js": f"{p}_js"},
        name="record_midi",
        params={"Record MIDI": device.parameter(
            device.box(f"{p}_pill"))},
        ports={"ev_in": device.box(js).inlet(0),
               "status_out": device.box(js).outlet(0)},
    )


_DEVICE_PALETTE_JS = """/* device_palette.js - Spawner-class native-device inserter (T15, #51).
   `spawn <Name...>` inserts a NATIVE Live device on the selected track via
   the Live 12 LOM Track.insert_device(name, index?). `policyidx 0|1|2`
   places it Left of / Right of the selected device / Last in chain.
   `dupes 0|1` gates re-inserting a class already on the track,
   `spawnrandom` picks from the `addname`-registered list (no immediate
   repeat), `removedevice` deletes the selected device. Outlet 0 feeds a
   status chip. */
this.autowatch = 1;
this.outlets = 1;

var names = [];
var policy = 2;        // 0=Left 1=Right 2=Last
var dupes = 1;         // 1 = allow duplicates
var lastPick = -1;

function addname() {
    names.push(Array.prototype.slice.call(arguments).join(" "));
}

function clearnames() { names = []; }

function policyidx(v) { policy = Math.max(0, Math.min(2, v | 0)); }

function dupesflag(v) { dupes = v ? 1 : 0; }

/* hunt #13 (rack-aware): the selected device's path inside an Audio Effect
   Rack ends in a CHAIN-relative segment (... devices N chains K devices M).
   The old bare-index regex returned M and drove delete_device/insert_device
   on the TOP-LEVEL track, so Remove deleted a DIFFERENT device (data loss)
   and Left/Right mis-placed. selectedDeviceRef() returns the device's REAL
   container path + index; Remove deletes from that container, Left/Right
   insert into it (chain inserts fall back to end-of-track with an honest
   status if the LOM refuses). */
function selectedDeviceRef() {
    var dev = new LiveAPI(null, "live_set view selected_track view selected_device");
    if (!dev || dev.id == 0) return null;
    var path = ("" + dev.path).replace(/"/g, "");
    var m = path.match(/^(.*) devices (\\d+)$/);
    if (!m) return null;
    return { container: m[1], index: parseInt(m[2], 10),
             nested: / chains \\d+$/.test(m[1]) };
}

function classOnContainer(apiPath, name) {
    var c = new LiveAPI(null, apiPath);
    if (!c || c.id == 0) return false;
    var n = parseInt(c.getcount("devices"), 10) || 0;
    for (var i = 0; i < n; i++) {
        var d = new LiveAPI(null, apiPath + " devices " + i);
        var cls = ("" + d.get("class_display_name")).replace(/"/g, "");
        if (cls === name) return true;
        /* rack devices: walk every chain so DUP sees nested copies too */
        var cn = parseInt(d.getcount("chains"), 10) || 0;
        for (var k = 0; k < cn; k++) {
            if (classOnContainer(apiPath + " devices " + i + " chains " + k,
                                 name)) return true;
        }
    }
    return false;
}

function onTrack(track, name) {
    return classOnContainer("live_set view selected_track", name);
}

function doSpawn(name) {
    var track = new LiveAPI(null, "live_set view selected_track");
    if (!track || track.id == 0) { status("no track"); return; }
    if (!dupes && onTrack(track, name)) { status(name + " already here"); return; }
    var ref = (policy !== 2) ? selectedDeviceRef() : null;
    if (ref && ref.index >= 0) {
        var idx = ref.index + (policy === 1 ? 1 : 0);
        if (ref.nested) {
            /* chain-relative insert next to the nested selection */
            try {
                var chain = new LiveAPI(null, ref.container);
                chain.call("insert_device", name, idx);
                status("+ " + name);
                return;
            } catch (e) { /* chain refused - fall through to track-last */ }
            try { track.call("insert_device", name); }
            catch (e2) { status("failed: " + name); return; }
            status("+ " + name + " (rack: placed last)");
            return;
        }
        try { track.call("insert_device", name, idx); }
        catch (e3) { status("failed: " + name); return; }
        status("+ " + name);
        return;
    }
    try { track.call("insert_device", name); }
    catch (e4) { status("failed: " + name); return; }
    status("+ " + name);
}

function spawn() {
    doSpawn(Array.prototype.slice.call(arguments).join(" "));
}

function spawnrandom() {
    if (!names.length) { status("no palette"); return; }
    var i = Math.floor(Math.random() * names.length);
    if (names.length > 1 && i === lastPick) i = (i + 1) % names.length;
    lastPick = i;
    doSpawn(names[i]);
}

function removedevice() {
    var ref = selectedDeviceRef();
    if (!ref || ref.index < 0) { status("none selected"); return; }
    /* delete from the device's REAL container (track OR rack chain) - the
       old top-level delete_device with a chain-relative index destroyed a
       different device entirely */
    var container = new LiveAPI(null, ref.container);
    try { container.call("delete_device", ref.index); status("removed"); }
    catch (e) { status("remove failed"); }
}

function status(s) { outlet(0, ["set"].concat(("" + s).split(" "))); }
"""


def device_palette(device, id_prefix, *, names, rect, columns=3,
                   policy_tab=None, status_rect=None, accent=None,
                   gap=2, fontsize=6.5):
    """Spawner-class native-device palette (catalog #51, Spawner v1.08).

    A grid of ``textbutton`` chips over ``rect`` — clicking one inserts that
    NATIVE Live device on the *selected* track via the Live 12 LOM
    ``Track.insert_device`` (Max for Live devices/plug-ins can't be inserted
    this way). Insertion position follows the policy (0 Left of the selected
    device / 1 Right of it / 2 Last), wired from ``policy_tab`` (a live.tab
    box id emitting 0..2) when given. Extra verbs on ``ctl_in``:
    ``spawnrandom`` (dice — no immediate repeat), ``removedevice`` (delete
    the selected device — corpus remove.maxpat), ``dupesflag 0|1`` (block
    re-inserting a class already on the track).

    The name list is registered into the js at load time (live.thisdevice →
    trigger → one ``addname`` message PER name), so ``spawnrandom`` knows the
    palette without re-parsing the UI.
    """
    from .engines.design_system import js_sidecar_name
    from .ui import textbutton

    p = id_prefix
    acc = list(accent) if accent else [1.0, 0.5, 0.24, 1.0]
    fname = js_sidecar_name("device_palette.js", _DEVICE_PALETTE_JS)
    device.register_asset(fname, _DEVICE_PALETTE_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[900, 3600, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})

    x0, y0, w, h = rect
    rows = -(-len(names) // columns)
    bw = (w - gap * (columns - 1)) / columns
    bh = (h - gap * (rows - 1)) / rows
    for i, name in enumerate(names):
        r, c = divmod(i, columns)
        brect = [x0 + c * (bw + gap), y0 + r * (bh + gap),
                 bw, bh]
        device.add_box(textbutton(
            f"{p}_b{i}", brect, name, mode=0, fontsize=fontsize,
            bgcolor=[0.16, 0.17, 0.20, 1.0], bgoncolor=acc,
            textcolor=[0.78, 0.79, 0.82, 1.0],
            annotation_name=name,
            annotation=f"Insert Live's native {name} on the selected track "
                       "(placement follows the position policy).",
            patching_rect=[900 + (i % 8) * 130, 3630 + (i // 8) * 60,
                           110, 20]))
        device.add_box({"box": {
            "id": f"{p}_m{i}", "maxclass": "message",
            "text": f"spawn {name}", "numinlets": 2, "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [900 + (i % 8) * 130, 3630 + (i // 8) * 60 + 26,
                              110, 20]}})
        device.add_line(f"{p}_b{i}", 0, f"{p}_m{i}", 0)
        device.add_line(f"{p}_m{i}", 0, js, 0)

    # register the palette into the js for spawnrandom. ONE message per name,
    # sequenced by a trigger — comma-chained message text does NOT survive an
    # authored-JSON load (the Orbit DRAW lesson: chrome batches go invisible /
    # escaped commas load as literal tokens), so the old single comma-joined
    # addname chain silently registered NOTHING.
    nt = device.add_newobj(f"{p}_nt", "t " + " ".join(["b"] * len(names)),
                           numinlets=1, numoutlets=len(names),
                           outlettype=["bang"] * len(names),
                           patching_rect=[900, 3570, 220, 20])
    for i, name in enumerate(names):
        device.add_box({"box": {
            "id": f"{p}_n{i}", "maxclass": "message",
            "text": f"addname {name}", "numinlets": 2, "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [900 + (i % 8) * 130,
                              3600 + (i // 8) * 60, 110, 20]}})
        device.add_line(nt, i, f"{p}_n{i}", 0)
        device.add_line(f"{p}_n{i}", 0, js, 0)
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 3540, 90, 20])
    device.add_line(td, 0, nt, 0)

    if policy_tab is not None:
        pol = device.add_newobj(f"{p}_pol", "prepend policyidx",
                                numinlets=1, numoutlets=1, outlettype=[""],
                                patching_rect=[1140, 3570, 110, 20])
        device.add_line(policy_tab, 0, pol, 0)
        device.add_line(pol, 0, js, 0)

    result_boxes = {"js": f"{p}_js"}
    if status_rect is not None:
        device.add_box({"box": {
            "id": f"{p}_status", "maxclass": "textedit", "text": "—",
            "numinlets": 1, "numoutlets": 4,
            "outlettype": ["", "int", "", ""], "fontsize": 6.5,
            "fontname": "Ableton Sans Medium",
            "textcolor": [0.55, 0.56, 0.60, 1.0],
            "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0,
            "ignoreclick": 1, "presentation": 1,
            "presentation_rect": list(status_rect),
            "patching_rect": [900, 3660, status_rect[2], status_rect[3]]}})
        device.add_line(js, 0, f"{p}_status", 0)
        result_boxes["status"] = f"{p}_status"

    return stage_result(
        result_boxes,
        name="device_palette",
        params={},
        ports={"ctl_in": device.box(js).inlet(0),
               "status_out": device.box(js).outlet(0)},
    )


_SAMPLE_EXPORT_JS = """/* sample_export.js - buffer~ -> wav on disk (T15, #56 out-half).
   `save` emits `writewave <dir>/<stem>_NNN.wav` for the wired buffer~
   (outlet 0) + a status line (outlet 1). `setdir <path...>` (re)targets
   the folder — args are re-joined so paths with spaces survive. True
   OS-level drag-out needs the 3rd-party `11dragfiles` external
   (corpus: Random Sample Picker); the portable stock path is saving into
   the User Library so the file appears in Live's browser to drag from. */
this.autowatch = 1;
this.outlets = 2;

var dir = "";
var stem = "export";
var count = 0;

function setdir() {
    dir = Array.prototype.slice.call(arguments).join(" ");
}

function setstem(s) { stem = "" + s; }

function save() {
    if (!dir) { outlet(1, ["set", "no", "folder", "set"]); return; }
    count += 1;
    var n = ("00" + count).slice(-3);
    var path = dir + "/" + stem + "_" + n + ".wav";
    outlet(0, ["writewave", path]);
    outlet(1, ["set", "saved", stem + "_" + n + ".wav"]);
}
"""


def sample_export(device, id_prefix, buffer_box_id, *, rect,
                  default_dir=None, stem="export", status_rect=None,
                  accent=None):
    """Save the contents of an existing ``buffer~`` to a ``.wav`` on disk
    (catalog #56, out-half). One SAVE click = one numbered file
    (``<stem>_001.wav`` …) written via ``buffer~``'s stock ``writewave``.

    The corpus does true OS drag-out with the 3rd-party
    ``11dragfiles`` external (Random Sample Picker v2.0: path → ``prepend
    drag`` → ``11dragfiles``) — a binary external the portable kit won't
    embed. Point ``default_dir`` at a User Library folder instead and the
    export lands in Live's browser, which drags anywhere.

    Wire your own path source into ``dir_in`` (e.g. an ``opendialog fold``)
    to retarget at runtime.
    """
    from .engines.design_system import js_sidecar_name
    from .ui import textbutton

    p = id_prefix
    acc = list(accent) if accent else [0.35, 0.78, 0.62, 1.0]
    fname = js_sidecar_name("sample_export.js", _SAMPLE_EXPORT_JS)
    device.register_asset(fname, _SAMPLE_EXPORT_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[1300, 3600, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    device.add_box(textbutton(
        f"{p}_save", list(rect), "⬇ SAVE", mode=0, fontsize=7.0,
        bgcolor=[0.16, 0.17, 0.20, 1.0], bgoncolor=acc,
        textcolor=[0.78, 0.79, 0.82, 1.0],
        patching_rect=[1300, 3540, 90, 20]))
    device.add_box({"box": {
        "id": f"{p}_savem", "maxclass": "message", "text": "save",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [1300, 3570, 60, 20]}})
    device.add_line(f"{p}_save", 0, f"{p}_savem", 0)
    device.add_line(f"{p}_savem", 0, js, 0)
    device.add_line(js, 0, buffer_box_id, 0)

    if stem != "export":
        device.add_box({"box": {
            "id": f"{p}_stem", "maxclass": "message",
            "text": f"setstem {stem}", "numinlets": 2, "numoutlets": 1,
            "outlettype": [""], "patching_rect": [1450, 3510, 110, 20]}})

    if default_dir is not None:
        device.add_box({"box": {
            "id": f"{p}_dir", "maxclass": "message",
            "text": f"setdir {default_dir}", "numinlets": 2,
            "numoutlets": 1, "outlettype": [""],
            "patching_rect": [1300, 3510, 140, 20]}})
        td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                               numoutlets=3, outlettype=["bang", "int", "int"],
                               patching_rect=[1300, 3480, 90, 20])
        device.add_line(td, 0, f"{p}_dir", 0)
        device.add_line(f"{p}_dir", 0, js, 0)
        if stem != "export":
            device.add_line(td, 0, f"{p}_stem", 0)
            device.add_line(f"{p}_stem", 0, js, 0)

    result_boxes = {"js": f"{p}_js", "save": f"{p}_save"}
    if status_rect is not None:
        device.add_box({"box": {
            "id": f"{p}_status", "maxclass": "textedit", "text": "—",
            "numinlets": 1, "numoutlets": 4,
            "outlettype": ["", "int", "", ""], "fontsize": 6.0,
            "fontname": "Ableton Sans Medium",
            "textcolor": [0.55, 0.56, 0.60, 1.0],
            "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0,
            "ignoreclick": 1, "presentation": 1,
            "presentation_rect": list(status_rect),
            "patching_rect": [1300, 3660, status_rect[2],
                              status_rect[3]]}})
        device.add_line(js, 1, f"{p}_status", 0)
        result_boxes["status"] = f"{p}_status"

    return stage_result(
        result_boxes,
        name="sample_export",
        params={},
        ports={"dir_in": device.box(js).inlet(0),
               "write_out": device.box(js).outlet(0),
               "status_out": device.box(js).outlet(1)},
    )


def sample_lfo(device, id_prefix, *, key, rate_rect, samps=None,
               rate_min=0.02, rate_max=20.0, rate_initial=1.0,
               unipolar=False, accent=None):
    """Use an audio buffer as the LFO *shape* (catalog #56):
    ``phasor~`` at the Rate param sweeps ``wave~ <key>`` so whatever the
    buffer holds — a dropped sample, a rendered curve — IS the modulation
    waveform.

    Creates the ``buffer~ <key>`` when ``samps`` is given (pair the box id
    in the result with :func:`sample_drop_target` for drop-in); pass
    ``samps=None`` to reference a buffer another stage owns. ``sig_out``
    is the raw bipolar shape signal (audio samples are already ±1);
    ``unipolar=True`` remaps to 0..1 (``*~ 0.5`` → ``+~ 0.5``) for
    depth-style consumers. ``phase_out`` drives :func:`progress_tick`.
    """
    from .ui import dial

    p = id_prefix
    boxes = {}
    if samps is not None:
        device.add_newobj(f"{p}_buf", f"buffer~ {key} @samps {int(samps)}",
                          numinlets=1, numoutlets=2,
                          outlettype=["float", "bang"],
                          patching_rect=[1600, 3480, 170, 20])
        boxes["buffer"] = f"{p}_buf"
    device.add_box(dial(
        f"{p}_rate", "Rate", list(rate_rect), min_val=float(rate_min),
        max_val=float(rate_max), initial=float(rate_initial),
        unitstyle=3, parameter_exponent=3.0,
        activedialcolor=list(accent) if accent else None))
    device.add_newobj(f"{p}_phasor", "phasor~ 1.", numinlets=2,
                      numoutlets=1, outlettype=["signal"],
                      patching_rect=[1600, 3540, 80, 20])
    device.add_line(f"{p}_rate", 0, f"{p}_phasor", 0)
    device.add_newobj(f"{p}_wave", f"wave~ {key}", numinlets=3,
                      numoutlets=1, outlettype=["signal"],
                      patching_rect=[1600, 3570, 100, 20])
    device.add_line(f"{p}_phasor", 0, f"{p}_wave", 0)
    out_box = f"{p}_wave"
    if unipolar:
        device.add_newobj(f"{p}_half", "*~ 0.5", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[1600, 3600, 60, 20])
        device.add_newobj(f"{p}_lift", "+~ 0.5", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[1600, 3630, 60, 20])
        device.add_line(f"{p}_wave", 0, f"{p}_half", 0)
        device.add_line(f"{p}_half", 0, f"{p}_lift", 0)
        out_box = f"{p}_lift"
    boxes.update({"rate": f"{p}_rate", "wave": f"{p}_wave"})
    return stage_result(
        boxes,
        name="sample_lfo",
        params={"Rate": device.parameter(device.box(f"{p}_rate"))},
        ports={"sig_out": device.box(out_box).outlet(0),
               "phase_out": device.box(f"{p}_phasor").outlet(0)},
    )


_REGION_TRANSLATE_JS = """/* region_translate.js - slide every presentation box whose origin is
   at-or-beyond a start point (a region-translate primitive, T16 #57). `setUiPos
   <startX> <startY> <newX> <newY>` translates the region by (new-start);
   the corpus idempotence guard (a box must sit EXACTLY at the start
   origin) prevents double-moves when toggles re-fire. Outlet 0 reports
   `moved <n>` / `skipped`. */
this.autowatch = 1;
this.outlets = 1;

function setUiPos(startX, startY, newX, newY) {
    var obj = this.patcher.firstobject;
    var closestX = 100000, closestY = 100000;
    while (obj != null) {
        if (obj.getboxattr("presentation") == 1) {
            var r = obj.getboxattr("presentation_rect");
            if (r[0] >= startX && r[1] >= startY) {
                closestX = Math.min(r[0] - startX, closestX);
                closestY = Math.min(r[1] - startY, closestY);
            }
        }
        obj = obj.nextobject;
    }
    if (closestX != 0 || closestY != 0) { outlet(0, ["skipped"]); return; }
    obj = this.patcher.firstobject;
    var n = 0;
    while (obj != null) {
        if (obj.getboxattr("presentation") == 1) {
            var r = obj.getboxattr("presentation_rect");
            if (r[0] >= startX && r[1] >= startY) {
                obj.setboxattr("presentation_rect",
                    [r[0] + newX - startX, r[1] + newY - startY,
                     r[2], r[3]]);
                n++;
            }
        }
        obj = obj.nextobject;
    }
    outlet(0, ["moved", n]);
}
"""


def region_translate(device, id_prefix):
    """The region-translate primitive (catalog #57):
    a js whose ``setUiPos <startX> <startY> <newX> <newY>`` message slides
    EVERY presentation box at-or-beyond the start origin by the delta —
    reflowing panels without naming each box. The corpus guard (some box
    must sit exactly at the start origin) makes repeated sends idempotent,
    so author the sliding region with one box anchored AT the origin —
    the minimum x-offset AND y-offset across matching boxes must each be
    zero, so the anchor box must sit at the start point in BOTH axes.
    """
    from .engines.design_system import js_sidecar_name

    p = id_prefix
    fname = js_sidecar_name("region_translate.js", _REGION_TRANSLATE_JS)
    device.register_asset(fname, _REGION_TRANSLATE_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[900, 3900, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    return stage_result(
        {"js": f"{p}_js"},
        name="region_translate",
        params={},
        ports={"move_in": device.box(js).inlet(0),
               "status_out": device.box(js).outlet(0)},
    )


def expandable_column(device, id_prefix, *, arrow_rect, base_width,
                      column_width, param_name="Panel",
                      accent="0.30, 0.80, 0.84"):
    """Right-side expandable column (catalog #57, the Spawner settings
    column). Author the device at FULL width (``base_width +
    column_width``) with the column content at ``x >= base_width``; this
    stage adds the ▸/◂ arrow (an expand/collapse glyph cycle bound to a
    hidden automatable enum ``param_name``) and the ``setwidth`` pair into
    ``live.thisdevice`` — Live clips the column when narrow (width does
    not reflow), which IS the reveal.

    A load re-fire bangs the hidden ``live.tab`` (bang-safe, unlike
    live.text toggles) so a fresh insert opens at ``base_width`` and a
    saved-Open device restores wide. Keep the arrow inside ``base_width``.
    """
    p = id_prefix
    full = int(base_width + column_width)
    device.add_cycle_button(f"{p}_arrow", param_name, list(arrow_rect),
                            glyphs=["expand", "collapse"],
                            option_labels=["Closed", "Open"],
                            accent=accent, initial=0)
    tab = f"{p}_arrow_tab"
    device.add_newobj(f"{p}_sel", "sel 0 1", numinlets=1, numoutlets=3,
                      outlettype=["bang", "bang", ""],
                      patching_rect=[900, 3960, 60, 20])
    device.add_box({"box": {
        "id": f"{p}_wbase", "maxclass": "message",
        "text": f"setwidth {int(base_width)}", "numinlets": 2,
        "numoutlets": 1, "outlettype": [""],
        "patching_rect": [900, 3990, 110, 20]}})
    device.add_box({"box": {
        "id": f"{p}_wfull", "maxclass": "message",
        "text": f"setwidth {full}", "numinlets": 2, "numoutlets": 1,
        "outlettype": [""], "patching_rect": [1020, 3990, 110, 20]}})
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 4020, 90, 20])
    device.add_line(tab, 0, f"{p}_sel", 0)
    device.add_line(f"{p}_sel", 0, f"{p}_wbase", 0)
    device.add_line(f"{p}_sel", 1, f"{p}_wfull", 0)
    device.add_line(f"{p}_wbase", 0, td, 0)
    device.add_line(f"{p}_wfull", 0, td, 0)
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[1140, 3960, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, tab, 0)
    return stage_result(
        {"arrow": f"{p}_arrow", "tab": tab},
        name="expandable_column",
        params={param_name: device.parameter(device.box(tab))},
        ports={"state_out": device.box(tab).outlet(0)},
    )


def header_strip(device, id_prefix, *, title, title_w, chips=(), y=3,
                 x=8, gap=6, height=11, text_color=None, dim_color=None,
                 fontsize=7.5, version=None, version_w=24):
    """Collapsed-face header discipline (catalog #58): the top strip
    carries the device's ESSENTIAL live state — title plus set-able
    readout chips — packed LEFT so it stays readable at MINI width
    (width-collapse clips the right edge; it does not reflow).

    ``chips``: list of ``(width, initial_text)``. Each becomes a
    transparent ``textedit`` fed by ready ``set …`` messages on the
    returned ``chip<i>_in`` ports (mapping summaries, mode names, gain
    readouts — a modulation grammar).
    """
    p = id_prefix
    tc = list(text_color) if text_color else [0.78, 0.79, 0.82, 1.0]
    dc = list(dim_color) if dim_color else [0.55, 0.56, 0.60, 1.0]
    device.add_comment(f"{p}_title", [x, y, title_w, height], title,
                       textcolor=tc, fontsize=fontsize,
                       fontname="Ableton Sans Medium")
    ports = {}
    cx = x + title_w + gap
    if version is not None:
        # catalog #61: every corpus device titles itself "Name vN.N" — the
        # version lives on the face, dim, right after the title
        device.add_comment(f"{p}_ver", [cx - gap + 1, y, version_w, height],
                           f"v{version}", textcolor=dc,
                           fontsize=float(fontsize) - 1.5,
                           fontname="Ableton Sans Medium")
        cx += version_w
    for i, (cw, initial) in enumerate(chips):
        device.add_box({"box": {
            "id": f"{p}_chip{i}", "maxclass": "textedit",
            "text": str(initial), "numinlets": 1, "numoutlets": 4,
            "outlettype": ["", "int", "", ""], "fontsize": float(fontsize) - 1,
            "fontname": "Ableton Sans Medium", "textcolor": dc,
            "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0, "rounded": 0,
            "ignoreclick": 1, "presentation": 1,
            "presentation_rect": [cx, y + 1, cw, height - 1],
            "patching_rect": [900 + i * 130, 4080, cw, height]}})
        ports[f"chip{i}_in"] = device.box(f"{p}_chip{i}").inlet(0)
        cx += cw + gap
    return stage_result(
        {"title": f"{p}_title"},
        name="header_strip",
        params={},
        ports=ports,
    )


def icon_rail(device, id_prefix, *, icons, rect, param_name="Page",
              labels=None, manage=None, accent="0.30, 0.80, 0.84"):
    """Left icon-rail page tabs (catalog #59, the viewhide bus):
    a slim VERTICAL glyph radio (one icon per page, accent highlight on
    the selected cell) bound to a hidden automatable ``live.tab`` enum.

    ``manage``: dict of ``{parent_box_varname: 0-based_page_index}`` —
    every managed box is hidden whenever its page isn't selected, via the
    Live-proven parent-side ``script sendbox <vn> hidden $1`` →
    ``thispatcher`` path, with a load re-broadcast (bang the tab —
    bang-safe) so restored sets hide their off-page boxes.
    """
    from .engines.ui_kit import custom_glyph_selector_js
    from .parameters import ParameterSpec

    p = id_prefix
    labels = list(labels) if labels else [i.upper() for i in icons]
    spec = ParameterSpec.enumerated(param_name, labels, initial=0,
                                    initial_enable=True)
    device.add_tab(f"{p}_tab", param_name,
                   [rect[0], rect[1], 40, 18], options=labels,
                   parameter=spec, presentation=0,
                   patching_rect=[900, 4140, 40, 18])
    device.add_v8ui(
        f"{p}_rail", list(rect),
        js_code=custom_glyph_selector_js(glyphs=list(icons), accent=accent,
                                         vertical=True),
        js_filename=f"{p}_iconrail.js", content_address=True,
        numinlets=1, numoutlets=1, outlettype=["int"],
        background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
        border=0, bordercolor=[0.0, 0.0, 0.0, 0.0], varname=f"{p}_rail")
    device.add_line(f"{p}_rail", 0, f"{p}_tab", 0)
    seti = device.add_newobj(f"{p}_seti", "prepend set_index", numinlets=1,
                             numoutlets=1, outlettype=[""],
                             patching_rect=[900, 4170, 110, 20])
    device.add_line(f"{p}_tab", 0, seti, 0)
    device.add_line(seti, 0, f"{p}_rail", 0)
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 4110, 90, 20])
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[1000, 4110, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, f"{p}_tab", 0)
    if manage:
        thisp = device.add_newobj(f"{p}_this", "thispatcher", numinlets=1,
                                  numoutlets=2, outlettype=["", ""],
                                  patching_rect=[1240, 4140, 80, 20])
        for mi, (vn, page) in enumerate(sorted(manage.items())):
            if " " in vn:
                raise ValueError(
                    f"icon_rail: managed varname {vn!r} contains a space "
                    "— script sendbox silently no-ops")
            ex = device.add_newobj(
                f"{p}_mx{mi}", f"expr $i1 != {int(page)}", numinlets=1,
                numoutlets=1, outlettype=[""],
                patching_rect=[1060, 4140 + 30 * mi, 120, 20])
            device.add_box({"box": {
                "id": f"{p}_mm{mi}", "maxclass": "message",
                "text": f"script sendbox {vn} hidden $1",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [1190, 4140 + 30 * mi, 200, 20]}})
            device.add_line(f"{p}_tab", 0, ex, 0)
            device.add_line(ex, 0, f"{p}_mm{mi}", 0)
            device.add_line(f"{p}_mm{mi}", 0, thisp, 0)
    return stage_result(
        {"rail": f"{p}_rail", "tab": f"{p}_tab"},
        name="icon_rail",
        params={param_name: device.parameter(device.box(f"{p}_tab"))},
        ports={"page_out": device.box(f"{p}_tab").outlet(0)},
    )


def stereo_mode(device, id_prefix, *, rect, gen_box, param_name="Mode",
                gen_param="msmode", fontsize=6.8):
    """STEREO / MID / SIDE processing-mode selector (catalog Q50, the
    linear-phase-crossover / Parametric-EQ pattern as one contract).

    The DSP side embeds the M/S matrix in its gen~ (inline the
    :func:`~m4l_builder.gen_snippets.ms_mode_split` /
    :func:`~m4l_builder.gen_snippets.ms_mode_merge` law with a single
    ``{gen_param}`` Param — STEREO must stay byte-identical); this recipe
    is the UI half: the automatable enum menu + ``prepend {gen_param}``
    into ``gen_box``.
    """
    from .parameters import ParameterSpec
    from .ui import menu as _menu

    p = id_prefix
    device.add_box(_menu(
        f"{p}_menu", param_name, list(rect),
        options=["STEREO", "MID", "SIDE"], fontsize=fontsize,
        annotation_name="Processing mode (Stereo / Mid only / Side only)",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2,
                                enum=["STEREO", "MID", "SIDE"],
                                initial=[0], initial_enable=True)))
    pp = device.add_newobj(f"{p}_pp", f"prepend {gen_param}", numinlets=1,
                           numoutlets=1, outlettype=[""],
                           patching_rect=[900, 4400, 110, 20])
    device.add_line(f"{p}_menu", 0, pp, 0)
    device.add_line(pp, 0, gen_box, 0)
    return stage_result(
        {"menu": f"{p}_menu"},
        name="stereo_mode",
        params={param_name: device.parameter(device.box(f"{p}_menu"))},
        ports={"mode_out": device.box(f"{p}_menu").outlet(0)},
    )


def buffer_viewport(device, id_prefix, buffer_name, *, rect,
                    accent=None, bg=None, setmode=1, outmode=4,
                    zoom_rect=None, full_rect=None, fontsize=6.8):
    """Zoom/scrub/select ``buffer~`` viewport (catalog Q2, the
    BufferViewport framework piece — pairs with T11's waveform layers).

    The native ``waveform~`` carries the working set (doc-verified inlet/
    outlet order — outlets 0/1 are the DISPLAY window, 2/3 the SELECTION):

    - **select** — drag on the wave (``setmode`` 1, the I-beam; 3 = Move
      scrub/zoom gesture, 2 = Loop, 4 = Draw); the bounds stream out the
      ``sel_start`` / ``sel_end`` ports in ms (``outmode`` is the INT
      enum 0 none / 1 down / 2 up / 3 downup / 4 continuous — 4 streams
      live during the drag).
    - **zoom** — the ``{p}_zoom`` chip reads the LAST selection out of two
      silent ``float`` stores and drives the display start/length inlets
      (0/1); ``{p}_full`` resets to the whole buffer.

    The display window is view state, not a Live parameter — zooming never
    dirties the set. Feed ``sel_start``/``sel_end`` to a chip or a player.
    """
    from .ui import textbutton as _textbutton
    from .ui import waveform as _waveform

    p = id_prefix
    acc = list(accent) if accent else [0.55, 0.85, 0.95, 1.0]
    sel = [acc[0], acc[1], acc[2], 0.30]
    bgc = list(bg) if bg else [0.05, 0.055, 0.062, 1.0]
    device.add_box(_waveform(
        f"{p}_wave", list(rect), buffername=buffer_name,
        waveformcolor=acc, selectioncolor=sel, bgcolor=bgc,
        gridcolor=[0.16, 0.17, 0.19, 1.0],
        bordercolor=[0.16, 0.17, 0.19, 1.0],
        setmode=setmode, outmode=outmode))
    # silent selection stores (right inlet = set, no output); selection
    # bounds emit from outlets 2/3 (0/1 are the display window)
    device.add_newobj(f"{p}_fs", "f", numinlets=2, numoutlets=1,
                      outlettype=["float"],
                      patching_rect=[900, 4470, 40, 20])
    device.add_newobj(f"{p}_fe", "f", numinlets=2, numoutlets=1,
                      outlettype=["float"],
                      patching_rect=[950, 4470, 40, 20])
    device.add_line(f"{p}_wave", 2, f"{p}_fs", 1)
    device.add_line(f"{p}_wave", 3, f"{p}_fe", 1)
    # ZOOM: right bang first -> start (display start + expr cold), then
    # end -> expr hot -> length
    zr = list(zoom_rect) if zoom_rect else [rect[0], rect[1] + rect[3] + 3,
                                            40, 12]
    fr = list(full_rect) if full_rect else [zr[0] + zr[2] + 4, zr[1],
                                            40, 12]
    device.add_box(_textbutton(f"{p}_zoom", zr, "ZOOM",
                               fontsize=fontsize, mode=0))
    device.add_box(_textbutton(f"{p}_full", fr, "FULL",
                               fontsize=fontsize, mode=0))
    device.add_newobj(f"{p}_zt", "t b b", numinlets=1, numoutlets=2,
                      outlettype=["bang", "bang"],
                      patching_rect=[900, 4500, 50, 20])
    device.add_newobj(f"{p}_len", "expr $f1 - $f2", numinlets=2,
                      numoutlets=1, outlettype=[""],
                      patching_rect=[900, 4530, 90, 20])
    device.add_line(f"{p}_zoom", 0, f"{p}_zt", 0)
    device.add_line(f"{p}_zt", 1, f"{p}_fs", 0)
    device.add_line(f"{p}_zt", 0, f"{p}_fe", 0)
    device.add_line(f"{p}_fs", 0, f"{p}_len", 1)
    device.add_line(f"{p}_fs", 0, f"{p}_wave", 0)
    device.add_line(f"{p}_fe", 0, f"{p}_len", 0)
    device.add_line(f"{p}_len", 0, f"{p}_wave", 1)
    # FULL: display start 0, display length = clamped-to-buffer huge
    device.add_newobj(f"{p}_ft", "t b b", numinlets=1, numoutlets=2,
                      outlettype=["bang", "bang"],
                      patching_rect=[1000, 4500, 50, 20])
    device.add_box({"box": {
        "id": f"{p}_m0", "maxclass": "message", "text": "0.",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [1000, 4530, 30, 20]}})
    device.add_box({"box": {
        "id": f"{p}_mbig", "maxclass": "message", "text": "1000000000.",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [1040, 4530, 80, 20]}})
    device.add_line(f"{p}_full", 0, f"{p}_ft", 0)
    device.add_line(f"{p}_ft", 1, f"{p}_mbig", 0)
    device.add_line(f"{p}_ft", 0, f"{p}_m0", 0)
    device.add_line(f"{p}_mbig", 0, f"{p}_wave", 1)
    device.add_line(f"{p}_m0", 0, f"{p}_wave", 0)
    return stage_result(
        {"waveform": f"{p}_wave", "zoom": f"{p}_zoom", "full": f"{p}_full"},
        name="buffer_viewport",
        params={},
        ports={
            "sel_start": device.box(f"{p}_wave").outlet(2),
            "sel_end": device.box(f"{p}_wave").outlet(3),
            "disp_start_in": device.box(f"{p}_wave").inlet(0),
            "disp_len_in": device.box(f"{p}_wave").inlet(1),
        },
    )


def meter_feed(device, id_prefix, target_id, *, sources, held_ms=None,
               selector="levels", target_inlet=0, patch_x=40, patch_y=290):
    """The ``pak -> prepend levels -> display`` meter/history feed (hunt #98).

    Every level meter and GR/level history in the fleet hand-wired the same
    glue: per-channel capture, a ``pak``, a ``prepend levels``, and a line
    into the display. This recipe owns that shape so the channel order and
    the held-peak capture policy can't be mis-wired per device.

    ``sources`` is a list of ``(box_id, outlet)`` per pak slot, or ``None``
    to leave a slot at the pak's ``0.`` default (loudness_meter's fixed-zero
    GR slot). ``held_ms`` wraps each source in ``peakamp~ <held_ms>`` — the
    HELD max since the last report; a ``snapshot~`` reads one instant and
    under-reads every transient between frames (the #48/#101 class). Pass
    ``None`` when the sources are already control-rate floats.

    Returns ``{"holds": [per-source peakamp~ ids], "pak": id,
    "prepend": id}`` — wire extra consumers (dB readouts) off ``holds``.
    """
    n = len(sources)
    pak_id = f"{id_prefix}_pak"
    pp_id = f"{id_prefix}_prepend"
    holds = []
    device.add_newobj(pak_id, "pak " + " ".join(["0."] * n),
                      numinlets=n, numoutlets=1, outlettype=[""],
                      patching_rect=[patch_x, patch_y + 60, 120, 20])
    device.add_newobj(pp_id, f"prepend {selector}", numinlets=1, numoutlets=1,
                      outlettype=[""],
                      patching_rect=[patch_x, patch_y + 90, 110, 20])
    for i, src in enumerate(sources):
        if src is None:
            continue
        src_id, src_out = src
        if held_ms is not None:
            hold_id = f"{id_prefix}_hold{i}"
            device.add_newobj(hold_id, f"peakamp~ {held_ms}", numinlets=1,
                              numoutlets=1, outlettype=["float"],
                              patching_rect=[patch_x + i * 90, patch_y, 80, 20])
            device.add_line(src_id, src_out, hold_id, 0)
            device.add_line(hold_id, 0, pak_id, i)
            holds.append(hold_id)
        else:
            device.add_line(src_id, src_out, pak_id, i)
    device.add_line(pak_id, 0, pp_id, 0)
    device.add_line(pp_id, 0, target_id, target_inlet)
    return stage_result(
        {"holds": holds, "pak": pak_id, "prepend": pp_id},
        name="meter_feed",
        params={},
        ports={},
    )
