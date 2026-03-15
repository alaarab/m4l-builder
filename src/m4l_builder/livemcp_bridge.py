"""Reusable LiveMCP bridge helpers for bridge-enabled Max for Live devices.

The bridge runtime lives inside the generated .amxd itself:

- ``node.script`` exposes a localhost TCP JSON-lines server.
- ``js`` performs patcher inspection and mutation via Max's native JS APIs.

This matches the selected-device bridge model validated in LiveMCP.
"""

from __future__ import annotations

import json
from typing import Optional

from .device import AudioEffect, Device


BRIDGE_PROTOCOL_VERSION = 1
DEFAULT_BRIDGE_PORT = 9881

BRIDGE_RUNTIME_FILENAME = "livemcp_bridge_runtime.js"
BRIDGE_SERVER_FILENAME = "livemcp_bridge_server.js"
BRIDGE_SCHEMA_FILENAME = "livemcp_bridge_schema.json"

BRIDGE_CAPABILITIES = {
    "selected_device": True,
    "patcher_read": True,
    "patcher_write": True,
    "window_control": True,
    "save": True,
}

OBJECT_ATTR_ALLOWLIST = [
    "annotation",
    "hint",
    "text",
]

BOX_ATTR_ALLOWLIST = [
    "background",
    "bgcolor",
    "border",
    "fontface",
    "fontname",
    "fontsize",
    "hidden",
    "ignoreclick",
    "patching_rect",
    "presentation",
    "presentation_rect",
    "rounded",
    "textcolor",
    "varname",
]

DISALLOWED_CREATE_CLASSES = [
    "js",
    "jsui",
    "mxj",
    "node.script",
    "shell",
    "v8",
    "v8ui",
]

BRIDGE_COMMANDS = {
    "get_max_bridge_info": "Transport-level health check handled by node.script.",
    "find_device_session": "Validate that the selected Live device matches this bridge device.",
    "show_editor": "Select this device in Live and ask Max to front the patcher window.",
    "get_current_patcher": "Return patcher metadata and line/box counts for the current patcher.",
    "list_boxes": "List boxes in the current patcher with ids, classes, rects, and attrs.",
    "get_box_attrs": "Return allowlisted object and box attrs for one box.",
    "set_box_attrs": "Set safe object and box attrs such as text or presentation_rect.",
    "create_box": "Create a new box using patcher.newdefault with an explicit class and args.",
    "connect_boxes": "Create a patchcord between two boxes.",
    "disconnect_boxes": "Delete a patchcord between two boxes.",
    "delete_box": "Delete a box by bridge id.",
    "set_presentation_rect": "Update one box's presentation rect and force presentation membership.",
    "set_presentation_mode": "Enter or exit presentation mode for the current patcher.",
    "save_device": "Save the current device via the patcher write message.",
}


def bridge_schema(port: int = DEFAULT_BRIDGE_PORT) -> dict:
    """Return the bridge transport schema used by LiveMCP."""
    return {
        "protocol_version": BRIDGE_PROTOCOL_VERSION,
        "session_mode": "selected-device-server",
        "transport": "tcp-json-lines",
        "host": "127.0.0.1",
        "port": port,
        "local_only": True,
        "capabilities": dict(BRIDGE_CAPABILITIES),
        "commands": dict(BRIDGE_COMMANDS),
        "object_attr_allowlist": list(OBJECT_ATTR_ALLOWLIST),
        "box_attr_allowlist": list(BOX_ATTR_ALLOWLIST),
        "disallowed_create_classes": list(DISALLOWED_CREATE_CLASSES),
    }


def _existing_box_ids(device: Device) -> set[str]:
    return {box["box"]["id"] for box in device.boxes}


def _require_bridge_id_space(device: Device, prefix: str) -> dict[str, str]:
    ids = {
        "accent": f"{prefix}_accent",
        "thisdevice": f"{prefix}_thisdevice",
        "defer": f"{prefix}_defer",
        "runtime": f"{prefix}_runtime",
        "server": f"{prefix}_server",
        "target": f"{prefix}_target",
        "title": f"{prefix}_title",
        "subtitle": f"{prefix}_subtitle",
        "hint": f"{prefix}_hint",
        "bg": f"{prefix}_bg",
    }
    existing = _existing_box_ids(device)
    collisions = sorted(value for value in ids.values() if value in existing)
    if collisions:
        raise ValueError(
            "LiveMCP bridge ids already exist on this device: %s" % ", ".join(collisions)
        )
    return ids


def _mix_color(base: list[float], other: list[float], amount: float) -> list[float]:
    amount = max(0.0, min(1.0, amount))
    return [
        base[0] + (other[0] - base[0]) * amount,
        base[1] + (other[1] - base[1]) * amount,
        base[2] + (other[2] - base[2]) * amount,
        base[3] + (other[3] - base[3]) * amount,
    ]


def _bridge_palette(device: Device) -> dict[str, list[float]]:
    if device.theme:
        bg = list(getattr(device.theme, "surface", [0.09, 0.11, 0.12, 1.0]))
        accent = list(getattr(device.theme, "accent", [0.62, 0.84, 0.56, 1.0]))
        text = list(getattr(device.theme, "text", [0.93, 0.95, 0.94, 1.0]))
        text_dim = list(getattr(device.theme, "text_dim", [0.48, 0.58, 0.56, 1.0]))
    else:
        bg = [0.09, 0.11, 0.12, 1.0]
        accent = [0.62, 0.84, 0.56, 1.0]
        text = [0.93, 0.95, 0.94, 1.0]
        text_dim = [0.48, 0.58, 0.56, 1.0]

    return {
        "bg": bg,
        "border": _mix_color(bg, accent, 0.24),
        "accent": accent,
        "title": text,
        "target": _mix_color(text, accent, 0.16),
        "subtitle": text_dim,
        "hint": _mix_color(text_dim, bg, 0.18),
    }


def _add_compact_bridge_ui(device: Device, ids: dict[str, str], port: int) -> None:
    palette = _bridge_palette(device)
    text_x = 22
    text_width = max(int(device.width) - text_x - 10, 100)

    device.add_panel(
        ids["bg"],
        [0, 0, device.width, device.height],
        bgcolor=palette["bg"],
        border=1,
        bordercolor=palette["border"],
        rounded=12,
        background=1,
        varname=ids["bg"],
    )
    device.add_panel(
        ids["accent"],
        [10, 10, 4, max(int(device.height) - 20, 24)],
        bgcolor=palette["accent"],
        rounded=2,
        background=1,
        varname=ids["accent"],
    )
    device.add_comment(
        ids["title"],
        [text_x, 9, text_width, 15],
        "LiveMCP Bridge",
        fontsize=12.0,
        fontface=1,
        textcolor=palette["title"],
        varname=ids["title"],
    )
    device.add_comment(
        ids["target"],
        [text_x, 27, text_width, 14],
        "Ready for patch edits.",
        fontsize=10.5,
        textcolor=palette["target"],
        varname=ids["target"],
    )
    device.add_comment(
        ids["subtitle"],
        [text_x, 42, text_width, 12],
        "selected-device server",
        fontsize=9.0,
        textcolor=palette["subtitle"],
        varname=ids["subtitle"],
    )
    device.add_comment(
        ids["hint"],
        [text_x, 54, text_width, 10],
        "127.0.0.1:%d / local only" % port,
        fontsize=8.5,
        textcolor=palette["hint"],
        varname=ids["hint"],
    )


def enable_livemcp_bridge(
    device: Device,
    *,
    port: int = DEFAULT_BRIDGE_PORT,
    prefix: str = "livemcp_bridge",
    include_ui: bool = False,
    include_demo_ui: Optional[bool] = None,
) -> dict:
    """Attach the LiveMCP bridge runtime to an existing device.

    The generated device remains local-only and controller-oriented. The bridge
    sidecars are written next to the .amxd during ``device.build()``.
    """
    if include_demo_ui is not None:
        include_ui = include_demo_ui

    ids = _require_bridge_id_space(device, prefix)
    bridge_y = max(int(device.height) + 60, 240)

    if include_ui:
        _add_compact_bridge_ui(device, ids, port)

    device.add_newobj(
        ids["thisdevice"],
        "live.thisdevice",
        numinlets=1,
        numoutlets=2,
        outlettype=["bang", ""],
        patching_rect=[30, bridge_y, 90, 20],
        varname=ids["thisdevice"],
    )
    device.add_newobj(
        ids["defer"],
        "deferlow",
        numinlets=1,
        numoutlets=1,
        outlettype=[""],
        patching_rect=[130, bridge_y, 52, 20],
        varname=ids["defer"],
    )
    device.add_newobj(
        ids["runtime"],
        "js %s" % BRIDGE_RUNTIME_FILENAME,
        numinlets=1,
        numoutlets=1,
        outlettype=[""],
        patching_rect=[200, bridge_y, 160, 20],
        varname=ids["runtime"],
    )
    device.add_newobj(
        ids["server"],
        "node.script %s @autostart 1 @watch 0" % BRIDGE_SERVER_FILENAME,
        numinlets=1,
        numoutlets=1,
        outlettype=[""],
        patching_rect=[380, bridge_y, 220, 20],
        varname=ids["server"],
    )

    device.add_line(ids["thisdevice"], 0, ids["defer"], 0)
    device.add_line(ids["defer"], 0, ids["runtime"], 0)
    device.add_line(ids["server"], 0, ids["runtime"], 0)
    device.add_line(ids["runtime"], 0, ids["server"], 0)

    device.add_support_file(BRIDGE_RUNTIME_FILENAME, bridge_runtime_js())
    device.add_support_file(BRIDGE_SERVER_FILENAME, bridge_server_js(port=port))
    device.add_support_file(
        BRIDGE_SCHEMA_FILENAME,
        json.dumps(bridge_schema(port=port), indent=2),
        file_type="JSON",
    )
    return {
        "port": port,
        "bridge_ids": ids,
        "runtime_filename": BRIDGE_RUNTIME_FILENAME,
        "server_filename": BRIDGE_SERVER_FILENAME,
        "schema_filename": BRIDGE_SCHEMA_FILENAME,
    }


def build_livemcp_bridge_demo(
    name: str = "LiveMCP Bridge Demo",
    width: int = 220,
    height: int = 68,
    port: int = DEFAULT_BRIDGE_PORT,
) -> AudioEffect:
    """Build a small reference device with the bridge embedded."""
    device = AudioEffect(name, width=width, height=height)
    enable_livemcp_bridge(
        device,
        port=port,
        prefix="bridge_demo",
        include_ui=True,
    )
    return device


def bridge_runtime_js() -> str:
    """Return the Max ``js`` bridge runtime."""
    return r'''
autowatch = 1;
inlets = 1;
outlets = 1;

var BRIDGE_SESSION_PREFIX = "livemcp-session-";
var OBJECT_ATTR_ALLOWLIST = {
    "annotation": true,
    "hint": true,
    "text": true
};
var BOX_ATTR_ALLOWLIST = {
    "background": true,
    "bgcolor": true,
    "border": true,
    "fontface": true,
    "fontname": true,
    "fontsize": true,
    "hidden": true,
    "ignoreclick": true,
    "patching_rect": true,
    "presentation": true,
    "presentation_rect": true,
    "rounded": true,
    "textcolor": true,
    "varname": true
};
var DISALLOWED_CREATE_CLASSES = {
    "js": true,
    "jsui": true,
    "mxj": true,
    "node.script": true,
    "shell": true,
    "v8": true,
    "v8ui": true
};
var CAPABILITIES = {
    "selected_device": true,
    "patcher_read": true,
    "patcher_write": true,
    "window_control": true,
    "save": true
};

var bridgeIds = [];
var nextBridgeId = 1;
var presentationModeState = null;

function bang() {
    initializeBridge();
}

function anything() {
    // The runtime only responds to bridge_request_json messages from node.script.
}

function bridge_request_json(payloadText) {
    var request;
    var response;

    try {
        request = JSON.parse(String(payloadText || "{}"));
        response = handleRequest(request);
    } catch (err) {
        response = errorEnvelope(
            request && request.id ? request.id : null,
            err.code || "max/bridge-runtime-failure",
            err.message,
            err.details || {}
        );
    }

    outlet(0, "bridge_response_json", JSON.stringify(response));
}

function initializeBridge() {
    refreshBridgeIds();
    if (presentationModeState === null) {
        var openInPresentation = safePatcherAttr("openinpresentation");
        if (openInPresentation !== null && openInPresentation !== undefined) {
            presentationModeState = toInt(openInPresentation) === 1;
        }
    }
}

function handleRequest(request) {
    var command = String(request.command || "");
    var params = request.params || {};
    var requestId = request.id || null;

    initializeBridge();

    if (command === "find_device_session") {
        return okEnvelope(requestId, findDeviceSession(params));
    }
    if (command === "show_editor") {
        return okEnvelope(requestId, showEditor(params));
    }
    if (command === "get_current_patcher") {
        return okEnvelope(requestId, getCurrentPatcher(params));
    }
    if (command === "list_boxes") {
        return okEnvelope(requestId, listBoxesResult(params));
    }
    if (command === "get_box_attrs") {
        return okEnvelope(requestId, getBoxAttrs(params));
    }
    if (command === "set_box_attrs") {
        return okEnvelope(requestId, setBoxAttrs(params));
    }
    if (command === "create_box") {
        return okEnvelope(requestId, createBox(params));
    }
    if (command === "connect_boxes") {
        return okEnvelope(requestId, connectBoxes(params));
    }
    if (command === "disconnect_boxes") {
        return okEnvelope(requestId, disconnectBoxes(params));
    }
    if (command === "delete_box") {
        return okEnvelope(requestId, deleteBox(params));
    }
    if (command === "set_presentation_rect") {
        return okEnvelope(requestId, setPresentationRect(params));
    }
    if (command === "set_presentation_mode") {
        return okEnvelope(requestId, setPresentationMode(params));
    }
    if (command === "save_device") {
        return okEnvelope(requestId, saveDevice(params));
    }

    return errorEnvelope(
        requestId,
        "max/unknown-command",
        "Unsupported bridge command.",
        { "command": command }
    );
}

function findDeviceSession(params) {
    var info = selectedDeviceInfo();
    var requestedSession = params.bridge_session_id;
    var requestedFingerprint = params.device_fingerprint || null;
    var sessionId;

    if (!info.this_device || !info.this_device.is_m4l) {
        throw bridgeError(
            "max/not-max-device",
            "This device is not running as a Max for Live device.",
            {
                "this_device": info.this_device,
                "selected_device": info.selected_device
            }
        );
    }

    sessionId = bridgeSessionId(info.this_device);
    if (requestedSession && String(requestedSession) !== sessionId) {
        throw bridgeError(
            "max/device-mismatch",
            "bridge_session_id does not match the active selected bridge device.",
            {
                "expected_bridge_session_id": sessionId,
                "received_bridge_session_id": requestedSession
            }
        );
    }
    if (requestedFingerprint && !fingerprintsMatch(info.this_device, requestedFingerprint)) {
        throw bridgeError(
            "max/device-mismatch",
            "Requested device does not match the active bridge device.",
            {
                "expected_device_fingerprint": info.this_device,
                "received_device_fingerprint": requestedFingerprint,
                "selected_device": info.selected_device
            }
        );
    }

    return {
        "bridge_session_id": sessionId,
        "device_fingerprint": info.this_device,
        "capabilities": cloneObject(CAPABILITIES)
    };
}

function showEditor(params) {
    var session = validateActiveSession(params);
    trySelectThisDevice();
    try {
        this.patcher.message("front");
    } catch (_err) {
        // Some patchers rely on wind.visible instead.
    }
    try {
        if (this.patcher.wind) {
            this.patcher.wind.visible = 1;
        }
    } catch (_windErr) {
        // Ignore visibility setter failures.
    }
    return {
        "bridge_session_id": session.bridge_session_id,
        "opened": true,
        "selected_device": session.device_fingerprint
    };
}

function getCurrentPatcher(params) {
    var session = validateActiveSession(params);
    return {
        "bridge_session_id": session.bridge_session_id,
        "selected_device": session.device_fingerprint,
        "name": safeValue(this.patcher.name),
        "filepath": safeValue(this.patcher.filepath),
        "dirty": safeBooleanPatcherAttr("dirty"),
        "locked": safeBooleanPatcherAttr("bglocked"),
        "window_visible": safeWindowVisible(),
        "presentation_mode": presentationModeState === true,
        "box_count": listBoxes().length,
        "patchline_count": listPatchlines().length,
        "capabilities": cloneObject(CAPABILITIES)
    };
}

function listBoxesResult(params) {
    var session = validateActiveSession(params);
    return {
        "bridge_session_id": session.bridge_session_id,
        "boxes": listBoxes()
    };
}

function getBoxAttrs(params) {
    var session = validateActiveSession(params);
    var boxId = requireString(params.box_id, "box_id");
    var obj = resolveBox(boxId);
    if (!obj) {
        throw bridgeError("max/box-not-found", "Unknown box id.", { "box_id": boxId });
    }
    return {
        "bridge_session_id": session.bridge_session_id,
        "box_id": ensureBridgeId(obj),
        "object_attrs": collectAttrs(obj, false),
        "box_attrs": collectAttrs(obj, true)
    };
}

function setBoxAttrs(params) {
    var session = validateActiveSession(params);
    var boxId = requireString(params.box_id, "box_id");
    var objectAttrs = params.object_attrs || {};
    var boxAttrs = params.box_attrs || {};
    var obj = resolveBox(boxId);
    var key;

    if (!obj) {
        throw bridgeError("max/box-not-found", "Unknown box id.", { "box_id": boxId });
    }

    for (key in objectAttrs) {
        if (!objectAttrs.hasOwnProperty(key)) {
            continue;
        }
        if (!OBJECT_ATTR_ALLOWLIST[key]) {
            throw bridgeError(
                "max/unsupported-attr",
                "Unsupported object attribute.",
                { "attr": key }
            );
        }
        setObjectAttr(obj, key, objectAttrs[key]);
    }

    for (key in boxAttrs) {
        if (!boxAttrs.hasOwnProperty(key)) {
            continue;
        }
        if (!BOX_ATTR_ALLOWLIST[key]) {
            throw bridgeError(
                "max/unsupported-attr",
                "Unsupported box attribute.",
                { "attr": key }
            );
        }
        validateAttrValue(key, boxAttrs[key]);
        obj.setboxattr(key, boxAttrs[key]);
    }

    markDirty();
    return {
        "bridge_session_id": session.bridge_session_id,
        "box_id": ensureBridgeId(obj),
        "object_attrs": collectAttrs(obj, false),
        "box_attrs": collectAttrs(obj, true)
    };
}

function createBox(params) {
    var session = validateActiveSession(params);
    var classname = requireString(params.classname, "classname");
    var left = requireNumber(params.left, "left");
    var top = requireNumber(params.top, "top");
    var args = params.args || [];
    var objectAttrs = params.object_attrs || {};
    var boxAttrs = params.box_attrs || {};
    var createArgs;
    var obj;

    if (DISALLOWED_CREATE_CLASSES[classname]) {
        throw bridgeError(
            "max/patcher-not-editable",
            "Creating this class is not allowed through the bridge.",
            { "classname": classname }
        );
    }
    if (!(args instanceof Array)) {
        throw bridgeError("max/invalid-params", "args must be an array.", {});
    }

    createArgs = [left, top, classname].concat(args);
    obj = this.patcher.newdefault.apply(this.patcher, createArgs);

    if (boxAttrs.patching_rect) {
        validateAttrValue("patching_rect", boxAttrs.patching_rect);
        obj.setboxattr("patching_rect", boxAttrs.patching_rect);
    }

    if (params.object_attrs || params.box_attrs) {
        setBoxAttrs({
            "bridge_session_id": session.bridge_session_id,
            "box_id": ensureBridgeId(obj),
            "object_attrs": objectAttrs,
            "box_attrs": boxAttrs
        });
    }

    markDirty();
    return {
        "bridge_session_id": session.bridge_session_id,
        "box": boxSummary(obj)
    };
}

function connectBoxes(params) {
    var session = validateActiveSession(params);
    var fromBox = resolveRequiredBox(params.from_box_id);
    var toBox = resolveRequiredBox(params.to_box_id);
    var outlet = requireInt(params.outlet, "outlet");
    var inlet = requireInt(params.inlet, "inlet");
    var hidden = !!params.hidden;

    if (hidden) {
        this.patcher.hiddenconnect(fromBox, outlet, toBox, inlet);
    } else {
        this.patcher.connect(fromBox, outlet, toBox, inlet);
    }

    markDirty();
    return {
        "bridge_session_id": session.bridge_session_id,
        "created": true,
        "patchline": {
            "from_box_id": ensureBridgeId(fromBox),
            "outlet": outlet,
            "to_box_id": ensureBridgeId(toBox),
            "inlet": inlet,
            "hidden": hidden
        }
    };
}

function disconnectBoxes(params) {
    var session = validateActiveSession(params);
    var fromBox = resolveRequiredBox(params.from_box_id);
    var toBox = resolveRequiredBox(params.to_box_id);
    var outlet = requireInt(params.outlet, "outlet");
    var inlet = requireInt(params.inlet, "inlet");

    this.patcher.disconnect(fromBox, outlet, toBox, inlet);
    markDirty();
    return {
        "bridge_session_id": session.bridge_session_id,
        "deleted": true,
        "patchline": {
            "from_box_id": ensureBridgeId(fromBox),
            "outlet": outlet,
            "to_box_id": ensureBridgeId(toBox),
            "inlet": inlet
        }
    };
}

function deleteBox(params) {
    var session = validateActiveSession(params);
    var boxId = requireString(params.box_id, "box_id");
    var obj = resolveBox(boxId);
    if (!obj) {
        throw bridgeError("max/box-not-found", "Unknown box id.", { "box_id": boxId });
    }
    removeStoredBoxId(boxId, obj);
    try {
        this.patcher.remove(obj);
    } catch (_err) {
        try {
            obj.remove();
        } catch (_innerErr) {
            throw bridgeError(
                "max/patcher-not-editable",
                "Could not remove box from patcher.",
                { "box_id": boxId }
            );
        }
    }
    markDirty();
    return {
        "bridge_session_id": session.bridge_session_id,
        "deleted": true,
        "box_id": boxId
    };
}

function setPresentationRect(params) {
    var session = validateActiveSession(params);
    var boxId = requireString(params.box_id, "box_id");
    var presentationRect = params.presentation_rect;
    var obj = resolveBox(boxId);

    if (!obj) {
        throw bridgeError("max/box-not-found", "Unknown box id.", { "box_id": boxId });
    }
    validateAttrValue("presentation_rect", presentationRect);
    obj.setboxattr("presentation", 1);
    obj.setboxattr("presentation_rect", presentationRect);
    markDirty();
    return {
        "bridge_session_id": session.bridge_session_id,
        "box_id": boxId,
        "presentation_rect": normalizeValue(presentationRect)
    };
}

function setPresentationMode(params) {
    var session = validateActiveSession(params);
    var enabled = !!params.enabled;
    var value = enabled ? 1 : 0;

    try {
        this.patcher.message("presentation", value);
    } catch (_err) {
        // Ignore message failures on patchers without an editor window.
    }
    try {
        this.patcher.setattr("openinpresentation", value);
    } catch (_setErr) {
        // Some Max versions do not expose this setter.
    }

    presentationModeState = enabled;
    return {
        "bridge_session_id": session.bridge_session_id,
        "presentation_mode": enabled
    };
}

function saveDevice(params) {
    var session = validateActiveSession(params);
    if (!safeValue(this.patcher.filepath)) {
        throw bridgeError(
            "max/save-requires-path",
            "Device has no current file path and cannot be saved non-interactively.",
            {}
        );
    }
    this.patcher.message("write");
    return {
        "bridge_session_id": session.bridge_session_id,
        "saved": true,
        "filepath": safeValue(this.patcher.filepath)
    };
}

function listBoxes() {
    var boxes = [];
    var obj = this.patcher.firstobject;
    while (obj) {
        boxes.push(boxSummary(obj));
        obj = obj.nextobject;
    }
    return boxes;
}

function listPatchlines() {
    var lines = [];
    var seen = {};
    var obj = this.patcher.firstobject;
    while (obj) {
        collectPatchlinesFromObject(obj, lines, seen);
        obj = obj.nextobject;
    }
    return lines;
}

function boxSummary(obj) {
    return {
        "box_id": ensureBridgeId(obj),
        "maxclass": safeValue(obj.maxclass),
        "varname": safeBoxAttr(obj, "varname"),
        "boxtext": readBoxText(obj),
        "rect": readRect(obj, "patching_rect"),
        "presentation_rect": readRect(obj, "presentation_rect"),
        "hidden": toBoolean(safeBoxAttr(obj, "hidden")),
        "background": toBoolean(safeBoxAttr(obj, "background"))
    };
}

function collectPatchlinesFromObject(obj, lines, seen) {
    var outputs;
    var i;
    var connection;
    var dst;
    var key;
    try {
        outputs = obj.patchcords.outputs || [];
    } catch (_err) {
        outputs = [];
    }
    for (i = 0; i < outputs.length; i++) {
        connection = outputs[i];
        dst = connection.dstobject;
        if (!dst) {
            continue;
        }
        key = [
            ensureBridgeId(obj),
            toInt(connection.outlet),
            ensureBridgeId(dst),
            toInt(connection.inlet)
        ].join(":");
        if (seen[key]) {
            continue;
        }
        seen[key] = true;
        lines.push({
            "from_box_id": ensureBridgeId(obj),
            "outlet": toInt(connection.outlet),
            "to_box_id": ensureBridgeId(dst),
            "inlet": toInt(connection.inlet)
        });
    }
}

function selectedDeviceInfo() {
    var thisDevice = resolveDeviceFingerprint(liveApi("this_device"));
    var selectedDevice = resolveDeviceFingerprint(liveApi("live_set view selected_device"));
    return {
        "this_device": thisDevice,
        "selected_device": selectedDevice,
        "selected_device_is_this_device": fingerprintsMatch(thisDevice, selectedDevice)
    };
}

function resolveDeviceFingerprint(api) {
    var path;
    var trackInfo;
    var className;
    var apiType;
    if (!api || !api.id) {
        return null;
    }
    path = normalizeLivePath(safeValue(api.path));
    trackInfo = parseTrackScope(path);
    className = liveGet(api, "class_name");
    apiType = safeValue(api.type);
    return {
        "device_id": api.id,
        "live_path": path,
        "track_scope": trackInfo.track_scope,
        "track_index": trackInfo.track_index,
        "track_name": trackNameForPath(trackInfo.track_path),
        "device_index": trackInfo.device_index,
        "device_name": liveGet(api, "name"),
        "class_name": className || apiType,
        "device_type": apiType,
        "is_m4l": isM4LDevice(apiType, className)
    };
}

function parseTrackScope(path) {
    var value = String(path || "");
    var match;
    if (!value) {
        return {
            "track_scope": null,
            "track_index": null,
            "track_path": null,
            "device_index": null
        };
    }
    match = value.match(/^live_set tracks (\d+) devices (\d+)$/);
    if (match) {
        return {
            "track_scope": "track",
            "track_index": toInt(match[1]),
            "track_path": "live_set tracks " + match[1],
            "device_index": toInt(match[2])
        };
    }
    match = value.match(/^live_set return_tracks (\d+) devices (\d+)$/);
    if (match) {
        return {
            "track_scope": "return",
            "track_index": toInt(match[1]),
            "track_path": "live_set return_tracks " + match[1],
            "device_index": toInt(match[2])
        };
    }
    match = value.match(/^live_set master_track devices (\d+)$/);
    if (match) {
        return {
            "track_scope": "master",
            "track_index": null,
            "track_path": "live_set master_track",
            "device_index": toInt(match[1])
        };
    }
    return {
        "track_scope": "unknown",
        "track_index": null,
        "track_path": null,
        "device_index": null
    };
}

function trackNameForPath(trackPath) {
    var api;
    if (!trackPath) {
        return null;
    }
    api = liveApi(trackPath);
    return liveGet(api, "name");
}

function isM4LDevice(apiType, className) {
    var typeValue = String(apiType || "");
    var classValue = String(className || "");
    return typeValue === "MaxDevice" || /^MxDevice/.test(typeValue) || /^MxDevice/.test(classValue);
}

function bridgeSessionId(deviceFingerprint) {
    var deviceId = deviceFingerprint && deviceFingerprint.device_id;
    if (deviceId) {
        return BRIDGE_SESSION_PREFIX + deviceId;
    }
    return BRIDGE_SESSION_PREFIX + "unknown";
}

function validateActiveSession(params) {
    return findDeviceSession(params || {});
}

function fingerprintsMatch(left, right) {
    if (!left || !right) {
        return false;
    }
    if (left.device_id && right.device_id) {
        return String(left.device_id) === String(right.device_id);
    }
    if (left.live_path && right.live_path) {
        return String(left.live_path) === String(right.live_path);
    }
    return false;
}

function resolveRequiredBox(boxId) {
    var value = requireString(boxId, "box_id");
    var obj = resolveBox(value);
    if (!obj) {
        throw bridgeError("max/box-not-found", "Unknown box id.", { "box_id": value });
    }
    return obj;
}

function ensureBridgeId(obj) {
    var existing = findStoredIdForObject(obj);
    var varname = safeBoxAttr(obj, "varname");
    if (varname) {
        updateStoredBoxId(obj, existing, varname);
        return varname;
    }
    if (existing) {
        return existing;
    }
    existing = "bridge_anon_" + nextBridgeId;
    nextBridgeId += 1;
    bridgeIds.push({ "id": existing, "obj": obj });
    return existing;
}

function refreshBridgeIds() {
    var obj = this.patcher.firstobject;
    while (obj) {
        ensureBridgeId(obj);
        obj = obj.nextobject;
    }
}

function resolveBox(boxId) {
    var i;
    refreshBridgeIds();
    for (i = 0; i < bridgeIds.length; i++) {
        if (bridgeIds[i].id === boxId) {
            return bridgeIds[i].obj;
        }
    }
    return null;
}

function findStoredIdForObject(obj) {
    var i;
    for (i = 0; i < bridgeIds.length; i++) {
        if (bridgeIds[i].obj === obj) {
            return bridgeIds[i].id;
        }
    }
    return null;
}

function updateStoredBoxId(obj, oldId, newId) {
    var i;
    for (i = 0; i < bridgeIds.length; i++) {
        if (bridgeIds[i].obj === obj || bridgeIds[i].id === oldId) {
            bridgeIds[i].id = newId;
            bridgeIds[i].obj = obj;
            return;
        }
    }
    bridgeIds.push({ "id": newId, "obj": obj });
}

function removeStoredBoxId(boxId, obj) {
    var filtered = [];
    var i;
    for (i = 0; i < bridgeIds.length; i++) {
        if (bridgeIds[i].id === boxId) {
            continue;
        }
        if (obj && bridgeIds[i].obj === obj) {
            continue;
        }
        filtered.push(bridgeIds[i]);
    }
    bridgeIds = filtered;
}

function setObjectAttr(obj, name, value) {
    if (name === "text") {
        try {
            obj.setattr(name, value);
            return;
        } catch (_err) {
            try {
                obj.message("text", value);
                return;
            } catch (_innerErr) {
                throw bridgeError(
                    "max/unsupported-attr",
                    "Could not set object text through the bridge.",
                    { "attr": name }
                );
            }
        }
    }
    try {
        obj.setattr(name, value);
    } catch (_setErr) {
        throw bridgeError(
            "max/unsupported-attr",
            "Could not set object attribute through the bridge.",
            { "attr": name }
        );
    }
}

function collectAttrs(obj, boxAttrs) {
    var getter = boxAttrs ? "getboxattr" : "getattr";
    var nameGetter = boxAttrs ? "getboxattrnames" : "getattrnames";
    var result = {};
    var names;
    var i;
    var value;

    try {
        names = obj[nameGetter]();
    } catch (_err) {
        names = [];
    }

    for (i = 0; i < names.length; i++) {
        try {
            value = normalizeValue(obj[getter](names[i]));
        } catch (_innerErr) {
            continue;
        }
        if (value !== null && value !== undefined) {
            result[names[i]] = value;
        }
    }

    return result;
}

function readBoxText(obj) {
    if (obj.boxtext !== undefined && obj.boxtext !== null) {
        return safeValue(obj.boxtext);
    }
    try {
        return safeValue(obj.getattr("text"));
    } catch (_err) {
        return null;
    }
}

function readRect(obj, attrName) {
    var rect = safeBoxAttr(obj, attrName);
    if (rect === null || rect === undefined) {
        return null;
    }
    return normalizeValue(rect);
}

function safePatcherAttr(name) {
    try {
        return normalizeValue(this.patcher.getattr(name));
    } catch (_err) {
        return null;
    }
}

function safeBooleanPatcherAttr(name) {
    var value = safePatcherAttr(name);
    if (value === null || value === undefined) {
        return false;
    }
    return toBoolean(value);
}

function safeWindowVisible() {
    try {
        if (this.patcher.wind) {
            return toBoolean(this.patcher.wind.visible);
        }
    } catch (_err) {
        // Ignore missing window access.
    }
    return false;
}

function safeBoxAttr(obj, name) {
    try {
        return normalizeValue(obj.getboxattr(name));
    } catch (_err) {
        return null;
    }
}

function normalizeValue(value) {
    var i;
    var copy;
    if (value === undefined || value === null) {
        return null;
    }
    if (typeof value === "number" || typeof value === "string" || typeof value === "boolean") {
        return value;
    }
    if (value instanceof Array) {
        copy = [];
        for (i = 0; i < value.length; i++) {
            copy.push(normalizeValue(value[i]));
        }
        return copy;
    }
    if (typeof value.length === "number") {
        copy = [];
        for (i = 0; i < value.length; i++) {
            copy.push(normalizeValue(value[i]));
        }
        return copy;
    }
    return safeValue(String(value));
}

function normalizeLivePath(value) {
    var text = safeValue(value);
    if (typeof text === "string" && text.length >= 2 && text.charAt(0) === "\"" && text.charAt(text.length - 1) === "\"") {
        return text.substring(1, text.length - 1);
    }
    return text;
}

function cloneObject(source) {
    return JSON.parse(JSON.stringify(source));
}

function safeValue(value) {
    if (value === undefined || value === null) {
        return null;
    }
    return value;
}

function toInt(value) {
    var parsed = parseInt(value, 10);
    if (isNaN(parsed)) {
        return 0;
    }
    return parsed;
}

function toBoolean(value) {
    if (value === true || value === 1 || value === "1") {
        return true;
    }
    return false;
}

function requireString(value, name) {
    if (typeof value !== "string" || value.length === 0) {
        throw bridgeError("max/invalid-params", name + " must be a non-empty string.", {});
    }
    return value;
}

function requireNumber(value, name) {
    var parsed = Number(value);
    if (isNaN(parsed)) {
        throw bridgeError("max/invalid-params", name + " must be numeric.", {});
    }
    return parsed;
}

function requireInt(value, name) {
    var parsed = parseInt(value, 10);
    if (isNaN(parsed)) {
        throw bridgeError("max/invalid-params", name + " must be an integer.", {});
    }
    return parsed;
}

function validateAttrValue(name, value) {
    if (name === "patching_rect" || name === "presentation_rect") {
        if (!(value instanceof Array) || value.length !== 4) {
            throw bridgeError(
                "max/invalid-params",
                name + " must be a four-element array.",
                { "attr": name }
            );
        }
    }
}

function markDirty() {
    try {
        this.patcher.message("dirty");
    } catch (_err) {
        // Ignore patchers that do not expose this message.
    }
}

function liveApi(path) {
    try {
        return new LiveAPI(path);
    } catch (_err) {
        return null;
    }
}

function liveGet(api, propertyName) {
    var raw;
    if (!api) {
        return null;
    }
    try {
        raw = api.get(propertyName);
    } catch (_err) {
        return null;
    }
    if (raw instanceof Array && raw.length > 0) {
        if (raw[0] === propertyName) {
            if (raw.length === 2) {
                return normalizeValue(raw[1]);
            }
            return normalizeValue(raw.slice(1));
        }
        if (raw.length === 1) {
            return normalizeValue(raw[0]);
        }
        return normalizeValue(raw);
    }
    return normalizeValue(raw);
}

function trySelectThisDevice() {
    var thisDevice = liveApi("this_device");
    var liveSetView = liveApi("live_set view");
    if (!thisDevice || !liveSetView || !thisDevice.id) {
        return false;
    }
    try {
        liveSetView.call("select_device", "id " + thisDevice.id);
        return true;
    } catch (_err) {
        return false;
    }
}

function okEnvelope(id, result) {
    return {
        "id": id,
        "status": "success",
        "result": result || {}
    };
}

function errorEnvelope(id, code, message, details) {
    return {
        "id": id,
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details || {}
        }
    };
}

function bridgeError(code, message, details) {
    var err = new Error(message);
    err.code = code;
    err.details = details || {};
    return err;
}
'''.strip() + "\n"


def bridge_server_js(port: int = DEFAULT_BRIDGE_PORT) -> str:
    """Return the Node for Max transport server."""
    schema = bridge_schema(port=port)
    code = r'''
const net = require("net");
const maxApi = require("max-api");

const HOST = "127.0.0.1";
const PORT = __DEFAULT_PORT__;
const BRIDGE_PROTOCOL_VERSION = __BRIDGE_PROTOCOL_VERSION__;
const CAPABILITIES = __CAPABILITIES__;
const BRIDGE_COMMANDS = __BRIDGE_COMMANDS__;

let server = null;
const pending = new Map();

function success(id, result) {
  return {
    id,
    status: "success",
    result: result || {},
  };
}

function failure(id, code, message, details) {
  return {
    id,
    status: "error",
    error: {
      code,
      message,
      details: details || {},
    },
  };
}

function sendJson(socket, payload) {
  try {
    socket.write(JSON.stringify(payload) + "\n");
  } catch (_err) {
    // Ignore writes to closed sockets.
  }
}

function validateRequest(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return failure(null, "max/invalid-request", "Request must be a JSON object.", {});
  }
  if (payload.id === undefined || payload.id === null) {
    return failure(null, "max/invalid-request", "Request must include an id.", {});
  }
  if (typeof payload.type !== "string" || !payload.type.length) {
    return failure(payload.id, "max/invalid-request", "Request must include a type.", {});
  }
  if (!BRIDGE_COMMANDS[payload.type]) {
    return failure(payload.id, "max/unknown-command", "Unsupported bridge command.", {
      command: payload.type,
    });
  }
  if (payload.params !== undefined && (typeof payload.params !== "object" || Array.isArray(payload.params))) {
    return failure(payload.id, "max/invalid-request", "params must be an object when present.", {});
  }
  return null;
}

async function forwardToRuntime(payload, socket) {
  const requestId = payload.id;
  const pendingKey = String(requestId);
  const timeout = setTimeout(() => {
    const pendingItem = pending.get(pendingKey);
    if (!pendingItem) {
      return;
    }
    sendJson(
      pendingItem.socket,
      failure(
        pendingItem.requestId,
        "max/bridge-timeout",
        "Timed out waiting for Max bridge response.",
        {}
      )
    );
    pending.delete(pendingKey);
  }, 10000);

  pending.set(pendingKey, {
    socket,
    timeout,
    requestId,
  });

  maxApi.outlet("bridge_request_json", JSON.stringify({
    id: requestId,
    command: payload.type,
    params: payload.params || {},
  }));
}

async function handleSocketMessage(line, socket) {
  let payload;
  let validationError;

  if (!line.trim()) {
    return;
  }

  try {
    payload = JSON.parse(line);
  } catch (_err) {
    sendJson(
      socket,
      failure(null, "max/invalid-json", "Could not parse JSON request.", {})
    );
    return;
  }

  validationError = validateRequest(payload);
  if (validationError) {
    sendJson(socket, validationError);
    return;
  }

  if (payload.type === "get_max_bridge_info") {
    sendJson(
      socket,
      success(payload.id, {
        reachable: true,
        protocol_version: BRIDGE_PROTOCOL_VERSION,
        session_mode: "selected-device-server",
        transport: "tcp-json-lines",
        host: HOST,
        port: PORT,
        capabilities: CAPABILITIES,
        schema: __SCHEMA__
      })
    );
    return;
  }

  try {
    await forwardToRuntime(payload, socket);
  } catch (err) {
    sendJson(
      socket,
      failure(payload.id, "max/bridge-forward-failed", err.message, {})
    );
  }
}

function attachSocket(socket) {
  let buffer = "";

  socket.setEncoding("utf8");

  socket.on("data", async (chunk) => {
    const parts = (buffer + chunk).split(/\r?\n/);
    buffer = parts.pop();
    for (const line of parts) {
      await handleSocketMessage(line, socket);
    }
  });

  socket.on("close", () => {
    for (const [requestId, pendingItem] of pending.entries()) {
      if (pendingItem.socket === socket) {
        clearTimeout(pendingItem.timeout);
        pending.delete(requestId);
      }
    }
  });
}

function startServer() {
  if (server) {
    return;
  }

  server = net.createServer(attachSocket);
  server.on("error", (err) => {
    maxApi.post("[livemcp_bridge] server error: " + err.message);
  });
  server.listen(PORT, HOST, () => {
    maxApi.post("[livemcp_bridge] listening on " + HOST + ":" + PORT);
  });
}

function stopServer() {
  if (!server) {
    return;
  }
  server.close();
  server = null;
}

maxApi.addHandler("bridge_response_json", (payloadText) => {
  let payload;
  let key;
  let pendingItem;

  try {
    payload = JSON.parse(String(payloadText || "{}"));
  } catch (err) {
    maxApi.post("[livemcp_bridge] invalid response json: " + err.message);
    return;
  }

  key = String(payload.id);
  pendingItem = pending.get(key);

  if (!pendingItem) {
    return;
  }

  clearTimeout(pendingItem.timeout);
  pending.delete(key);

  if (payload.id !== pendingItem.requestId) {
    payload.id = pendingItem.requestId;
  }
  sendJson(pendingItem.socket, payload);
});

maxApi.addHandler("shutdown", () => {
  stopServer();
});

startServer();
'''
    code = code.replace("__DEFAULT_PORT__", str(port))
    code = code.replace("__BRIDGE_PROTOCOL_VERSION__", str(BRIDGE_PROTOCOL_VERSION))
    code = code.replace("__CAPABILITIES__", json.dumps(BRIDGE_CAPABILITIES, sort_keys=True))
    code = code.replace("__BRIDGE_COMMANDS__", json.dumps(BRIDGE_COMMANDS, sort_keys=True))
    code = code.replace("__SCHEMA__", json.dumps(schema, sort_keys=True))
    return code.strip() + "\n"


__all__ = [
    "BRIDGE_PROTOCOL_VERSION",
    "DEFAULT_BRIDGE_PORT",
    "BRIDGE_RUNTIME_FILENAME",
    "BRIDGE_SERVER_FILENAME",
    "BRIDGE_SCHEMA_FILENAME",
    "BRIDGE_CAPABILITIES",
    "OBJECT_ATTR_ALLOWLIST",
    "BOX_ATTR_ALLOWLIST",
    "DISALLOWED_CREATE_CLASSES",
    "BRIDGE_COMMANDS",
    "bridge_schema",
    "bridge_runtime_js",
    "bridge_server_js",
    "enable_livemcp_bridge",
    "build_livemcp_bridge_demo",
]
