"""Low-level patcher/JSON generation for M4L devices.

Builds the complete patcher dict structure that gets serialized into the
.amxd container's JSON payload.
"""

import time

from .constants import AMXD_TYPE, DEFAULT_APPVERSION


def build_patcher(boxes: list, lines: list, *,
                  name: str = "m4l_device",
                  width: float = 400.0,
                  height: float = 170.0,
                  device_type: str = "audio_effect") -> dict:
    """Build a complete M4L patcher dict.

    Args:
        boxes: List of box dicts (each with a "box" key).
        lines: List of patchline dicts (each with a "patchline" key).
        name: Device name.
        width: Presentation width in pixels.
        height: Presentation height in pixels.
        device_type: One of "audio_effect", "instrument", "midi_effect".

    Returns:
        Complete patcher dict ready for JSON serialization and .amxd container.
    """
    # Max epoch: seconds since 1970-01-01 (same as Unix time)
    now = int(time.time())

    return {
        "patcher": {
            "fileversion": 1,
            "appversion": DEFAULT_APPVERSION,
            "classnamespace": "box",
            "rect": [100.0, 100.0, 900.0, 700.0],
            "openrect": [0.0, 0.0, width, height],
            "bglocked": 0,
            "openinpresentation": 1,
            "default_fontface": 0,
            "default_fontname": "Ableton Sans Medium",
            "default_fontsize": 10.0,
            "gridonopen": 1,
            "gridsize": [8.0, 8.0],
            "gridsnaponopen": 1,
            "objectsnaponopen": 1,
            "statusbarvisible": 2,
            "toolbarvisible": 1,
            "lefttoolbarpinned": 0,
            "toptoolbarpinned": 0,
            "righttoolbarpinned": 0,
            "bottomtoolbarpinned": 0,
            "toolbars_unpinned_last_save": 0,
            "tallnewobj": 0,
            "boxanimatetime": 200,
            "enablehscroll": 1,
            "enablevscroll": 1,
            "devicewidth": width,
            "description": "",
            "digest": "",
            "tags": "",
            "style": "",
            "subpatcher_template": "",
            "autosave": 0,
            "boxes": boxes,
            "lines": lines,
            "dependency_cache": [],
            "latency": 0,
            "project": {
                "version": 1,
                "creationdate": now,
                "modificationdate": now,
                "viewrect": [0.0, 0.0, 300.0, 500.0],
                "autoorganize": 1,
                "hideprojectwindow": 1,
                "showdependencies": 1,
                "autolocalize": 0,
                "contents": {
                    "patchers": {},
                },
                "layout": {},
                "searchpath": {},
                "detailsvisible": 0,
                "amxdtype": AMXD_TYPE.get(device_type, AMXD_TYPE["audio_effect"]),
                "readonly": 0,
                "devpathtype": 0,
                "devpath": ".",
                "sortmode": 0,
                "viewmode": 0,
            },
            "parameters": {
                "parameterbanks": {
                    "0": {
                        "index": 0,
                        "name": "",
                        "parameters": [],
                    }
                },
            },
        }
    }
