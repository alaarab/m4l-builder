"""lom_mapper — the E2/E3 runtime click-to-map target picker (LiveAPI js).

The corpus signature feature (lfo-cluster's ``js js_LOM_mapping_3.0 #1 #2 #3``):
a per-slot script that arms Live's ``live_set view`` selected_parameter
observer, guards against mapping the device's own mapping controls, reads the
picked parameter's real range and labels, and hands the LOM id to the
retargetable sink (``dsp.live.retargetable_param_sink`` — ``zl.reg`` →
``gate 2 1`` → ``t b l`` → ``deferlow`` → sink RIGHT inlet).

Ships as a plain non-UI ``v8`` box (the modern ``js``): register the source as
a device asset and add ``v8 <filename> #1`` inside the slot component — ``#1``
becomes ``jsarguments[1]`` (the slot index) at load, exactly the corpus
instancing scheme.

Message contract (inlet 0):
  ``map 0|1``      arm/disarm the selected-parameter observer (MAP button)
  ``unmap``        detach: emits ``id 0`` + clears the status readouts
  ``setid <n>``    attach directly by LOM id (persistence/restore hook)
  ``settarget <track> <device> <param>``
                   attach by path indices — the headless-proof path
  ``announce <i>`` cross-slot broadcast: another slot armed; disarm if not me

Outlet 0 (sink bus): ``id <n>`` lists only — wire to the sink's ``zl.reg``.
Outlet 1 (status route bus): ``mapped 0|1``, ``min <f>``, ``max <f>``,
``pname set <sym…>``, ``dname set <sym…>``, ``path <sym…>``, ``flash 0|1``
(armed blink state), ``announce <i>`` (wire via ``prepend announce`` to the
``---mapSelected``-style broadcast send).
"""

from __future__ import annotations

DEFAULT_SELF_MAP_GUARD = "Map|Min|Max|Depth|Bipolar"


def lom_mapper_js(*, self_map_guard: str = DEFAULT_SELF_MAP_GUARD,
                  debounce_ms: int = 20) -> str:
    """Source for the per-slot ``v8`` mapper script.

    ``self_map_guard``: regex of OWN-device parameter names that must refuse
    mapping (the corpus footgun guard — arming MAP selects the Map param
    itself, and mapping a slot to its own Depth dial feeds back).
    ``debounce_ms``: the corpus 20ms Task debounce on selection changes.
    """
    return f"""// lom_mapper — E2/E3 click-to-map target picker (lfo-cluster verbatim discipline)
autowatch = 0;
inlets = 1;
outlets = 2;

var SLOT = (jsarguments.length > 1) ? jsarguments[1] : 1;
var GUARD = new RegExp({_js_str(self_map_guard)});
var DEBOUNCE_MS = {int(debounce_ms)};

var armed = 0;
var target_id = 0;
var pending_id = -1;
var observer = null;
var debounce_task = null;

function dequote(s) {{
    return ("" + s).replace(/^"|"$/g, "");
}}

function status(/* ... */) {{
    var a = arrayfromargs(arguments);
    outlet(1, a);
}}

function announce_self() {{
    status("announce", SLOT);
}}

// ---- MAP arm/disarm --------------------------------------------------------
function map(on) {{
    if (on) {{
        armed = 1;
        announce_self();
        if (observer === null) {{
            observer = new LiveAPI(on_selected_param, "live_set view");
            observer.property = "selected_parameter";
        }}
        status("flash", 1);
    }} else {{
        disarm();
    }}
}}

function disarm() {{
    armed = 0;
    release_observer();
    status("flash", 0);
}}

function release_observer() {{
    if (observer !== null) {{
        observer.property = "";
        observer = null;
    }}
}}

// Cross-slot exclusivity: another slot armed -> stand down (corpus ---mapSelected).
function announce(i) {{
    if (i != SLOT && armed) disarm();
}}

// ---- selection observer (debounced, corpus 20ms Task) ----------------------
function on_selected_param(args) {{
    if (!armed) return;
    var a = arrayfromargs(args);
    // callback shape: ["selected_parameter", "id", <n>]
    var id = 0;
    for (var i = 0; i < a.length - 1; i++) {{
        if (a[i] === "id") id = parseInt(a[i + 1]);
    }}
    if (!id) return;               // empty selection at arm time — ignore
    pending_id = id;
    if (debounce_task === null) debounce_task = new Task(commit_pending);
    debounce_task.cancel();
    debounce_task.schedule(DEBOUNCE_MS);
}}

function commit_pending() {{
    var id = pending_id;
    pending_id = -1;
    if (!armed || !id || id < 0) return;
    if (attach(id)) disarm();      // successful pick completes the map gesture
}}

// ---- attach paths -----------------------------------------------------------
function setid(id) {{
    id = parseInt(id);
    if (!id) {{ unmap(); return; }}
    attach(id);
}}

function settarget(trk, dev, par) {{
    if (parseInt(trk) < 0) {{ unmap(); return; }}   // settarget -1 … = release
    var p = new LiveAPI(null, "live_set tracks " + parseInt(trk) +
        " devices " + parseInt(dev) + " parameters " + parseInt(par));
    if (!p || p.id == 0) {{
        status("pname", "set", "not found");
        return;
    }}
    attach(parseInt(p.id));
}}

function attach(id) {{
    var p = new LiveAPI(null, "id " + id);
    if (!p || p.id == 0) return 0;
    if (p.type != "DeviceParameter") return 0;
    var dev = new LiveAPI(null, dequote(p.path) + " canonical_parent");
    // self-map guard: refuse this device's own mapping controls
    var self_dev = new LiveAPI(null, "this_device");
    if (dev && self_dev && dev.id == self_dev.id) {{
        var pname = "" + p.get("name");
        if (GUARD.test(pname)) return 0;
    }}
    target_id = id;
    // LiveAPI get() returns ARRAYS — unwrap before outlet (a nested array
    // inside the status list does not flatten; the range never arrives)
    var mn = p.get("min");
    var mx = p.get("max");
    status("min", (mn instanceof Array) ? mn[0] : mn);
    status("max", (mx instanceof Array) ? mx[0] : mx);
    status("pname", "set", "" + p.get("name"));
    status("dname", "set", friendly_device_name(dev, p));
    status("path", dequote(p.path));
    status("mapped", 1);
    outlet(0, "id", id);
    return 1;
}}

function friendly_device_name(dev, p) {{
    var name = dev ? ("" + dev.get("name")) : "";
    var root = ("" + dequote(p.path)).split(" ")[1] || "";
    if (root === "return_tracks") return name || "Return Track";
    if (root === "master_track") return name || "Master Track";
    if (!name || name === "0.") return "Track";
    return name;
}}

// ---- detach ------------------------------------------------------------------
function unmap() {{
    target_id = 0;
    disarm();
    status("pname", "set", "\\u2014");
    status("dname", "set", "");
    status("path", "none");
    status("mapped", 0);
    outlet(0, "id", 0);
}}

// Forced-unmap detect: the sink's `route mapped -> sel 0` fires this when the
// host releases the mapping (target deleted / re-mapped elsewhere).
function extunmap() {{
    if (target_id) unmap();
}}
"""


def _js_str(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
