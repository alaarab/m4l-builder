"""Node-based behavioral harness for jsui/v8ui engine JavaScript.

Runs generated engine JS under Node with a mocked Max environment so
interaction logic (pointer handlers, message handlers, outlet emissions)
is testable headless — no Ableton, no screen.

Usage:
    result = run_jsui(eq_curve_js(), '''
        set_band(0, 1000, 6, 1, 0, 1);
        onpointerdown({x: freq_to_x(1000), y: gain_to_y(6), buttons: 1});
        dump({selected: selected_band});
    ''', size=(660, 152))
    assert result.outlets == [...]
    assert result.state["selected"] == 0

The driver runs in the same scope as the engine code, so it can call any
engine function (including internal helpers like freq_to_x) directly.
`dump(obj)` records arbitrary state; every `outlet(...)` call is captured
as [outlet_index, ...args].
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass

NODE = shutil.which("node") or "/opt/homebrew/bin/node"

_PRELUDE = """\
// --- Max jsui environment mock (m4l-builder js_harness) ---
var __captured = { outlets: [], state: null, posts: [] };

var mgraphics = new Proxy({
    size: [__WIDTH__, __HEIGHT__],
    relative_coords: 0,
    autofill: 0,
}, {
    get: function (target, prop) {
        if (prop in target) return target[prop];
        if (prop === "pattern_create_linear" || prop === "pattern_create_radial") {
            return function () {
                return new Proxy({}, { get: function () { return function () {}; } });
            };
        }
        return function () {};
    },
    set: function (target, prop, value) { target[prop] = value; return true; }
});

var inlets = 1;
var outlets = 1;
var inlet = 0;
var messagename = "";

function outlet() {
    __captured.outlets.push(Array.prototype.slice.call(arguments));
}

function post() {
    __captured.posts.push(Array.prototype.slice.call(arguments).join(" "));
}
function error() { post.apply(null, arguments); }
function cpost() {}

function arrayfromargs(args) { return Array.prototype.slice.call(args); }

function Task(fn) {
    this.fn = fn;
    this.interval = 0;
}
Task.prototype.schedule = function () {};
Task.prototype.repeat = function () {};
Task.prototype.cancel = function () {};

function Buffer() {
    this.peek = function () { return []; };
    this.poke = function () {};
    this.framecount = function () { return 0; };
}

function messnamed() {}

function dump(obj) { __captured.state = obj; }

// --- engine code under test ---
__ENGINE__

// --- test driver ---
__DRIVER__

// --- emit results ---
console.log(JSON.stringify(__captured));
"""


@dataclass
class JsRunResult:
    outlets: list
    state: dict | None
    posts: list
    raw: dict


def node_available() -> bool:
    return bool(NODE and shutil.which(NODE) or NODE == "/opt/homebrew/bin/node" and shutil.os.path.exists(NODE))


def run_jsui(engine_js: str, driver_js: str, *, size=(660, 152), timeout=20) -> JsRunResult:
    """Run engine JS + driver under Node; return captured outlets/state."""
    script = (
        _PRELUDE
        .replace("__WIDTH__", str(size[0]))
        .replace("__HEIGHT__", str(size[1]))
        .replace("__ENGINE__", engine_js)
        .replace("__DRIVER__", driver_js)
    )
    proc = subprocess.run(
        [NODE, "--stack-size=4096", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node failed:\n{proc.stderr[-3000:]}")
    line = proc.stdout.strip().splitlines()[-1]
    raw = json.loads(line)
    return JsRunResult(
        outlets=raw.get("outlets", []),
        state=raw.get("state"),
        posts=raw.get("posts", []),
        raw=raw,
    )
