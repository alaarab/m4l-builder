"""High-level Device API for building M4L devices."""

import json
import os
import struct

from .constants import DEVICE_TYPE_CODES
from .container import write_amxd, build_amxd
from .dsp import stereo_io
from .layout import Row, Column, Grid
from .objects import newobj, patchline
from .patcher import build_patcher
from .ui import (panel, dial, tab, toggle, comment, scope, meter, menu,
                 number_box, slider, button, live_text, fpic, live_gain,
                 multislider, jsui, adsrui, live_drop, bpatcher, swatch,
                 textedit, live_step, live_grid, live_line, live_arrows,
                 rslider, kslider, textbutton, umenu, radiogroup, nodes,
                 matrixctrl, ubutton, nslider)


class Device:
    """Base class for M4L devices.

    Provides a builder-style API for adding objects, UI elements, and
    connections, then serializing to a .amxd file.
    """

    def __init__(self, name: str, width: float, height: float,
                 device_type: str = "audio_effect", theme=None):
        self.name = name
        self.width = width
        self.height = height
        self.device_type = device_type
        self.theme = theme
        self.boxes = []
        self.lines = []
        self._js_files = {}  # {filename: js_code_string}
        self._param_banks = {}  # {varname: (bank, position)}

    def add_box(self, box_dict: dict) -> str:
        """Add a raw box dict and return its object ID."""
        self.boxes.append(box_dict)
        return box_dict["box"]["id"]

    def add_line(self, source_id: str, source_outlet: int,
                 dest_id: str, dest_inlet: int):
        self.lines.append(patchline(source_id, source_outlet, dest_id, dest_inlet))

    def add_dsp(self, boxes: list, lines: list):
        """Add all boxes and lines from a DSP block tuple to this device."""
        for box in boxes:
            self.add_box(box)
        for line in lines:
            self.lines.append(line)

    def _inject_theme(self, kwargs, mapping):
        """Inject theme defaults for keys not already in kwargs.

        mapping is a dict of {kwarg_name: theme_attribute_name}.
        """
        if not self.theme:
            return
        for kwarg_key, theme_attr in mapping.items():
            if kwarg_key not in kwargs:
                val = getattr(self.theme, theme_attr, None)
                if val is not None:
                    kwargs[kwarg_key] = val

    def add_panel(self, id: str, rect: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "bgcolor": "bg",
        })
        return self.add_box(panel(id, rect, **kwargs))

    def add_dial(self, id: str, varname: str, rect: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "activedialcolor": "dial_color",
            "activeneedlecolor": "needle_color",
        })
        return self.add_box(dial(id, varname, rect, **kwargs))

    def add_tab(self, id: str, varname: str, rect: list, options: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "bgcolor": "tab_bg",
            "bgoncolor": "tab_bg_on",
            "textcolor": "tab_text",
            "textoncolor": "tab_text_on",
        })
        return self.add_box(tab(id, varname, rect, options=options, **kwargs))

    def add_toggle(self, id: str, varname: str, rect: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "activebgoncolor": "accent",
        })
        return self.add_box(toggle(id, varname, rect, **kwargs))

    def add_comment(self, id: str, rect: list, text: str, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "textcolor": "text",
            "fontname": "fontname",
        })
        return self.add_box(comment(id, rect, text, **kwargs))

    def add_scope(self, id: str, rect: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "bgcolor": "scope_bgcolor",
            "activelinecolor": "scope_color",
        })
        return self.add_box(scope(id, rect, **kwargs))

    def add_meter(self, id: str, rect: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "coldcolor": "meter_cold",
            "warmcolor": "meter_warm",
            "hotcolor": "meter_hot",
            "overloadcolor": "meter_over",
        })
        return self.add_box(meter(id, rect, **kwargs))

    def add_menu(self, id: str, varname: str, rect: list, options: list, **kwargs) -> str:
        return self.add_box(menu(id, varname, rect, options=options, **kwargs))

    def add_number_box(self, id: str, varname: str, rect: list, **kwargs) -> str:
        return self.add_box(number_box(id, varname, rect, **kwargs))

    def add_slider(self, id: str, varname: str, rect: list, **kwargs) -> str:
        return self.add_box(slider(id, varname, rect, **kwargs))

    def add_button(self, id: str, varname: str, rect: list, **kwargs) -> str:
        return self.add_box(button(id, varname, rect, **kwargs))

    def add_live_text(self, id: str, varname: str, rect: list, **kwargs) -> str:
        return self.add_box(live_text(id, varname, rect, **kwargs))

    def add_fpic(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(fpic(id, rect, **kwargs))

    def add_live_gain(self, id: str, varname: str, rect: list, **kwargs) -> str:
        return self.add_box(live_gain(id, varname, rect, **kwargs))

    def add_multislider(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(multislider(id, rect, **kwargs))

    def add_jsui(self, id: str, rect: list, *, js_code: str,
                 js_filename: str = None, numinlets: int = 1,
                 numoutlets: int = 0, **kwargs) -> str:
        """Add a jsui with embedded JavaScript code for custom vector graphics.

        The JS code is written alongside the .amxd file during build().
        jsui uses Max's mgraphics (Cairo) API for rendering filter curves,
        EQ displays, envelope shapes, spectrum analyzers, etc.

        Args:
            id: Unique object ID.
            rect: [x, y, width, height] in presentation view.
            js_code: JavaScript source code string.
            js_filename: Output filename (defaults to {id}.js).
            numinlets: Number of inlets for parameter data.
            numoutlets: Number of outlets for sending data back.
        """
        if js_filename is None:
            js_filename = f"{id}.js"
        self._js_files[js_filename] = js_code
        return self.add_box(jsui(id, rect, js_filename=js_filename,
                                 numinlets=numinlets, numoutlets=numoutlets,
                                 **kwargs))

    def add_adsrui(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(adsrui(id, rect, **kwargs))

    def add_live_drop(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(live_drop(id, rect, **kwargs))

    def add_bpatcher(self, id: str, rect: list, patcher_name: str, **kwargs) -> str:
        return self.add_box(bpatcher(id, rect, patcher_name, **kwargs))

    def add_swatch(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(swatch(id, rect, **kwargs))

    def add_textedit(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(textedit(id, rect, **kwargs))

    def add_live_step(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(live_step(id, rect, **kwargs))

    def add_live_grid(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(live_grid(id, rect, **kwargs))

    def add_live_line(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(live_line(id, rect, **kwargs))

    def add_live_arrows(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(live_arrows(id, rect, **kwargs))

    def add_rslider(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(rslider(id, rect, **kwargs))

    def add_kslider(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(kslider(id, rect, **kwargs))

    def add_textbutton(self, id: str, rect: list, text: str = "Button", **kwargs) -> str:
        return self.add_box(textbutton(id, rect, text, **kwargs))

    def add_umenu(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(umenu(id, rect, **kwargs))

    def add_radiogroup(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(radiogroup(id, rect, **kwargs))

    def add_nodes(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(nodes(id, rect, **kwargs))

    def add_matrixctrl(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(matrixctrl(id, rect, **kwargs))

    def add_ubutton(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(ubutton(id, rect, **kwargs))

    def add_nslider(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(nslider(id, rect, **kwargs))

    def add_newobj(self, id: str, text: str, *, numinlets: int, numoutlets: int,
                   **kwargs) -> str:
        return self.add_box(newobj(id, text, numinlets=numinlets,
                                   numoutlets=numoutlets, **kwargs))

    def add_subpatcher(self, subpatcher, id: str, rect: list, *,
                       numinlets: int = 1, numoutlets: int = 1,
                       outlettype: list = None) -> str:
        """Add a Subpatcher as an embedded patcher box and return its ID."""
        box_dict = subpatcher.to_box(id, rect, numinlets=numinlets,
                                     numoutlets=numoutlets,
                                     outlettype=outlettype)
        return self.add_box(box_dict)

    def row(self, x, y, *, spacing=8, height=None, width=None):
        return Row(self, x, y, spacing=spacing, height=height, width=width)

    def column(self, x, y, *, spacing=4, width=None, height=None):
        return Column(self, x, y, spacing=spacing, width=width, height=height)

    def grid(self, x, y, *, cols, col_width, row_height, spacing_x=4, spacing_y=4):
        return Grid(self, x, y, cols=cols, col_width=col_width,
                    row_height=row_height, spacing_x=spacing_x,
                    spacing_y=spacing_y)

    def to_json(self, indent: int = 2) -> str:
        """Serialize the device patcher structure to a JSON string."""
        return json.dumps(self.to_patcher(), indent=indent)

    def wire_chain(self, obj_ids: list, outlet: int = 0, inlet: int = 0):
        """Connect objects end-to-end, each output feeding the next input."""
        for i in range(len(obj_ids) - 1):
            self.add_line(obj_ids[i], outlet, obj_ids[i + 1], inlet)

    def validate(self) -> list:
        """Check the device for common problems. Returns a list of warning strings."""
        warnings = []

        seen_ids = {}
        for box in self.boxes:
            box_id = box["box"]["id"]
            if box_id in seen_ids:
                warnings.append(f"Duplicate box ID: {box_id}")
            seen_ids[box_id] = True

        for line in self.lines:
            pl = line["patchline"]
            src = pl["source"][0]
            dst = pl["destination"][0]
            if src not in seen_ids:
                warnings.append(f"Patchline references unknown source: {src}")
            if dst not in seen_ids:
                warnings.append(f"Patchline references unknown destination: {dst}")

        if self.device_type == "audio_effect":
            if "obj-plugin" not in seen_ids:
                warnings.append("AudioEffect missing obj-plugin")
            if "obj-plugout" not in seen_ids:
                warnings.append("AudioEffect missing obj-plugout")

        connected = set()
        for line in self.lines:
            pl = line["patchline"]
            connected.add(pl["source"][0])
            connected.add(pl["destination"][0])
        for box_id in seen_ids:
            if box_id not in connected:
                warnings.append(f"Orphan box (no connections): {box_id}")

        return warnings

    def assign_parameter_bank(self, varname: str, bank: int, position: int):
        """Map a parameter into Push's bank layout for hardware control."""
        if bank < 0:
            raise ValueError(f"bank must be >= 0, got {bank}")
        if position < 0:
            raise ValueError(f"position must be >= 0, got {position}")
        self._param_banks[varname] = (bank, position)

    @classmethod
    def from_amxd(cls, path: str):
        """Parse a .amxd file back into a Device instance."""
        with open(path, "rb") as f:
            data = f.read()

        # Read type code at offset 8-11
        type_code = data[8:12]
        type_map = {
            b"aaaa": "audio_effect",
            b"iiii": "instrument",
            b"mmmm": "midi_effect",
        }
        device_type = type_map.get(type_code, "audio_effect")

        # Read metadata length at offset 16-19, skip to JSON
        meta_len = struct.unpack_from("<I", data, 16)[0]
        # JSON starts after: 20 + meta_len (metadata) + 4 (ptch tag) + 4 (json len)
        json_offset = 20 + meta_len + 8
        json_bytes = data[json_offset:].rstrip(b"\x00").rstrip(b"\n")
        patcher_dict = json.loads(json_bytes)

        patcher = patcher_dict["patcher"]
        width = patcher.get("devicewidth", patcher.get("openrect", [0, 0, 400, 170])[2])
        height = patcher.get("openrect", [0, 0, 400, 170])[3]

        # Pick the right subclass
        subclass_map = {
            "audio_effect": AudioEffect,
            "instrument": Instrument,
            "midi_effect": MidiEffect,
        }
        klass = subclass_map.get(device_type, Device)

        if klass is Device:
            device = Device("Untitled", width, height, device_type=device_type)
        else:
            device = klass("Untitled", width, height)

        # For AudioEffect, the constructor already added plugin~/plugout~.
        # Clear them so we load from the file instead.
        if klass is AudioEffect:
            device.boxes.clear()
            device.lines.clear()

        for box in patcher.get("boxes", []):
            device.boxes.append(box)
        for line in patcher.get("lines", []):
            device.lines.append(line)

        return device

    def to_patcher(self) -> dict:
        patcher = build_patcher(
            self.boxes, self.lines,
            name=self.name,
            width=self.width,
            height=self.height,
            device_type=self.device_type,
        )
        # Add JS file dependencies so Max knows about them
        for js_name in self._js_files:
            patcher["patcher"]["dependency_cache"].append({
                "name": js_name,
                "type": "TEXT",
                "implicit": 1,
            })
        # Populate parameter banks from assign_parameter_bank() calls
        if self._param_banks:
            banks = {}
            for varname, (bank, position) in self._param_banks.items():
                bank_key = str(bank)
                if bank_key not in banks:
                    banks[bank_key] = {
                        "index": bank,
                        "name": "",
                        "parameters": [],
                    }
                banks[bank_key]["parameters"].append({
                    "index": position,
                    "name": varname,
                    "visible": 1,
                })
            patcher["patcher"]["parameters"]["parameterbanks"] = banks
        return patcher

    def to_bytes(self) -> bytes:
        """Build the .amxd binary in memory."""
        type_code = DEVICE_TYPE_CODES[self.device_type]
        return build_amxd(self.to_patcher(), type_code)

    def build(self, output_path: str) -> int:
        """Build and write the .amxd file. Returns bytes written.

        Also writes any embedded JS files alongside the .amxd for jsui objects.
        """
        type_code = DEVICE_TYPE_CODES[self.device_type]
        result = write_amxd(self.to_patcher(), output_path, type_code)
        # Write JS files alongside the .amxd
        if self._js_files:
            output_dir = os.path.dirname(output_path)
            for filename, code in self._js_files.items():
                js_path = os.path.join(output_dir, filename)
                try:
                    with open(js_path, "w") as f:
                        f.write(code)
                except IOError as e:
                    raise IOError(f"Cannot write JS file {js_path}: {e}") from e
        return result


class AudioEffect(Device):
    """Audio effect device with plugin~/plugout~ auto-added."""

    def __init__(self, name: str, width: float, height: float, theme=None):
        super().__init__(name, width, height, device_type="audio_effect", theme=theme)
        # Auto-add stereo I/O
        boxes, lines = stereo_io()
        for b in boxes:
            self.boxes.append(b)
        for l in lines:
            self.lines.append(l)


class Instrument(Device):
    """Instrument device."""

    def __init__(self, name: str, width: float, height: float, theme=None):
        super().__init__(name, width, height, device_type="instrument", theme=theme)


class MidiEffect(Device):
    """MIDI effect device."""

    def __init__(self, name: str, width: float, height: float, theme=None):
        super().__init__(name, width, height, device_type="midi_effect", theme=theme)
