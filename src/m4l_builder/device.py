"""High-level Device API for building M4L devices."""

import os

from .constants import DEVICE_TYPE_CODES
from .container import write_amxd, build_amxd
from .dsp import stereo_io
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

    def add_box(self, box_dict: dict) -> str:
        """Add a raw box dict and return its object ID."""
        self.boxes.append(box_dict)
        return box_dict["box"]["id"]

    def add_line(self, source_id: str, source_outlet: int,
                 dest_id: str, dest_inlet: int):
        self.lines.append(patchline(source_id, source_outlet, dest_id, dest_inlet))

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
                with open(js_path, "w") as f:
                    f.write(code)
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
