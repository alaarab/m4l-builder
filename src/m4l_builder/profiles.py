"""Shared patcher/build profiles for devices and subpatchers."""

from __future__ import annotations

from dataclasses import dataclass, field
import time

from .constants import AMXD_TYPE, DEFAULT_APPVERSION


@dataclass
class PatcherProfile:
    """Profile describing Max patcher defaults for generated devices."""

    appversion: dict = field(default_factory=lambda: DEFAULT_APPVERSION.copy())
    device_rect: list = field(default_factory=lambda: [100.0, 100.0, 900.0, 700.0])
    subpatch_rect: list = field(default_factory=lambda: [0, 0, 400, 300])
    project_viewrect: list = field(default_factory=lambda: [0.0, 0.0, 300.0, 500.0])
    default_fontface: int = 0
    default_fontname: str = "Ableton Sans Medium"
    default_fontsize: float = 10.0
    gridsize: list = field(default_factory=lambda: [8.0, 8.0])
    boxanimatetime: int = 200
    toolbarvisible: int = 1
    statusbarvisible: int = 2
    device_openinpresentation: int = 1
    subpatch_openinpresentation: int = 0
    gridonopen: int = 1
    gridsnaponopen: int = 1
    objectsnaponopen: int = 1
    enablehscroll: int = 1
    enablevscroll: int = 1
    autoorganize: int = 1
    hideprojectwindow: int = 1
    showdependencies: int = 1
    autolocalize: int = 0

    def build_device_patcher(
        self,
        boxes: list,
        lines: list,
        *,
        width: float,
        height: float,
        device_type: str,
    ) -> dict:
        """Build the root patcher payload for a device."""
        now = int(time.time())
        return {
            "patcher": {
                "fileversion": 1,
                "appversion": self.appversion.copy(),
                "classnamespace": "box",
                "rect": list(self.device_rect),
                "openrect": [0.0, 0.0, width, height],
                "bglocked": 0,
                "openinpresentation": self.device_openinpresentation,
                "default_fontface": self.default_fontface,
                "default_fontname": self.default_fontname,
                "default_fontsize": self.default_fontsize,
                "gridonopen": self.gridonopen,
                "gridsize": list(self.gridsize),
                "gridsnaponopen": self.gridsnaponopen,
                "objectsnaponopen": self.objectsnaponopen,
                "statusbarvisible": self.statusbarvisible,
                "toolbarvisible": self.toolbarvisible,
                "lefttoolbarpinned": 0,
                "toptoolbarpinned": 0,
                "righttoolbarpinned": 0,
                "bottomtoolbarpinned": 0,
                "toolbars_unpinned_last_save": 0,
                "tallnewobj": 0,
                "boxanimatetime": self.boxanimatetime,
                "enablehscroll": self.enablehscroll,
                "enablevscroll": self.enablevscroll,
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
                    "viewrect": list(self.project_viewrect),
                    "autoorganize": self.autoorganize,
                    "hideprojectwindow": self.hideprojectwindow,
                    "showdependencies": self.showdependencies,
                    "autolocalize": self.autolocalize,
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

    def build_subpatcher_patcher(self, boxes: list, lines: list) -> dict:
        """Build the nested patcher payload for a subpatcher."""
        return {
            "fileversion": 1,
            "appversion": self.appversion.copy(),
            "rect": list(self.subpatch_rect),
            "bglocked": 0,
            "openinpresentation": self.subpatch_openinpresentation,
            "boxes": list(boxes),
            "lines": list(lines),
        }


DEFAULT_PATCHER_PROFILE = PatcherProfile()
