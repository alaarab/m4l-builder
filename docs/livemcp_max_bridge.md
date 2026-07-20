# LiveMCP Max Bridge

`m4l-builder` can embed the LiveMCP bridge directly into devices you build.

That means your own `.amxd` can host the same local Max bridge runtime that
LiveMCP talks to, instead of relying on a separate "global" bridge device.

## Recommended API

Use `enable_livemcp_bridge(device)` on the device you are already building:

```python
from m4l_builder import AudioEffect, enable_livemcp_bridge

device = AudioEffect("My Bridge Device", width=420, height=180)
enable_livemcp_bridge(device, include_ui=True)
device.build("My Bridge Device.amxd")
```

For a compact reference device with the bridge badge already laid out:

```python
from m4l_builder import build_livemcp_bridge_demo

device = build_livemcp_bridge_demo()
device.build("LiveMCP Bridge Demo.amxd")
```

## What gets embedded

The helper adds four internal Max objects to your device:

- `live.thisdevice`
- `deferlow`
- `js livemcp_bridge_runtime.js`
- `node.script livemcp_bridge_server.js @autostart 1 @watch 0`

It also writes three sidecar files next to the `.amxd` during `build()`:

- `livemcp_bridge_runtime.js`
- `livemcp_bridge_server.js`
- `livemcp_bridge_schema.json`

If you opt into the reference UI, it renders as a compact badge rather than a
large control panel.

## Contract

This helper matches the LiveMCP-selected-device bridge contract:

- Host: `127.0.0.1`
- Port: `9881`
- Framing: newline-delimited JSON
- Session mode: `selected-device-server`

Supported bridge commands:

- `get_max_bridge_info`
- `find_device_session`
- `show_editor`
- `get_current_patcher`
- `list_boxes`
- `get_box_attrs`
- `set_box_attrs`
- `create_box`
- `connect_boxes`
- `disconnect_boxes`
- `delete_box`
- `set_presentation_rect`
- `set_presentation_mode`
- `save_device`

## Important limitation

This does not make one bridge-enabled device a universal gateway for every Max
device in the set.

The bridge lives inside the device you embed it into. LiveMCP can control that
device because that device hosts the bridge runtime.

So:

- your own bridge-enabled devices: yes
- arbitrary third-party M4L devices without the bridge: no
- VST/AU plugins: no

## Practical note

The LiveMCP runtime currently expects the default port `9881`, and the bridge is
selected-device oriented. In practice, that means one active bridge-enabled
device at a time is the reliable v1 workflow.
