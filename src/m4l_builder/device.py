"""High-level Device API for building M4L devices."""

import json
import os
import struct
import warnings

from .constants import DEVICE_TYPE_CODES
from .container import write_amxd, build_amxd
from .dsp import stereo_io
from .graph import GraphContainer
from .layout import Row, Column, Grid
from .parameters import ParameterSpec
from .patcher import build_patcher
from .profiles import DEFAULT_PATCHER_PROFILE
from .ui import (panel, dial, tab, toggle, comment, scope, meter, menu,
                 number_box, slider, button, live_text, fpic, live_gain,
                 multislider, jsui, v8ui, adsrui, live_drop, bpatcher, swatch,
                 textedit, live_step, live_grid, live_line, live_arrows,
                 rslider, kslider, textbutton, umenu, radiogroup, nodes,
                 matrixctrl, ubutton, nslider)
from .validation import BuildValidationError, format_validation_issues


class Device(GraphContainer):
    """Base class for M4L devices.

    Provides a builder-style API for adding objects, UI elements, and
    connections, then serializing to a .amxd file.
    """

    def __init__(self, name: str, width: float, height: float,
                 device_type: str = "audio_effect", theme=None, profile=None):
        super().__init__()
        self.name = name
        self.width = width
        self.height = height
        self.device_type = device_type
        self.theme = theme
        self.profile = profile or DEFAULT_PATCHER_PROFILE
        self._js_files = {}  # {filename: js_code_string}
        self._param_banks = {}  # {varname: (bank, position)}
        self._param_bank_names = {}  # {bank: name}
        self._support_files = {}  # {filename: {"content": str, "type": str}}

    def register_parameter(self, spec, *, box_id: str = None):
        """Register parameter specs and keep bank metadata synchronized."""
        stored = super().register_parameter(spec, box_id=box_id)
        if stored.name in self._param_banks:
            bank, position = self._param_banks[stored.name]
            stored.bank = bank
            stored.position = position
            stored.bank_name = self._param_bank_names.get(bank, stored.bank_name)
        elif stored.bank is not None and stored.position is not None:
            self._param_banks[stored.name] = (stored.bank, stored.position)
            if stored.bank_name is not None:
                self._param_bank_names[stored.bank] = stored.bank_name
        return stored

    def register_asset(
        self,
        filename: str,
        content,
        *,
        asset_type: str = "TEXT",
        category: str = "support",
        encoding: str = "utf-8",
    ):
        """Register a sidecar asset and keep legacy mirrors synchronized."""
        stored = super().register_asset(
            filename,
            content,
            asset_type=asset_type,
            category=category,
            encoding=encoding,
        )
        if category == "js":
            self._js_files[filename] = content
            self._support_files.pop(filename, None)
        else:
            self._support_files[filename] = {
                "content": content,
                "type": asset_type,
            }
            self._js_files.pop(filename, None)
        return stored

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

    def _parameter_arg_spec(self, varname, kwargs):
        """Extract a first-class parameter spec from wrapper args when present."""
        parameter = kwargs.get("parameter")
        if isinstance(parameter, ParameterSpec):
            return parameter
        if isinstance(varname, ParameterSpec):
            return varname
        return None

    def _register_parameter_arg(self, box_ref, varname, kwargs):
        """Re-register explicit ParameterSpecs so bank metadata survives wrapper calls."""
        spec = self._parameter_arg_spec(varname, kwargs)
        if spec is not None:
            self.register_parameter(spec, box_id=str(box_ref))

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
        ref = self.add_box(dial(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_tab(self, id: str, varname: str, rect: list, options: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "bgcolor": "tab_bg",
            "bgoncolor": "tab_bg_on",
            "textcolor": "tab_text",
            "textoncolor": "tab_text_on",
        })
        ref = self.add_box(tab(id, varname, rect, options=options, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_toggle(self, id: str, varname: str, rect: list, **kwargs) -> str:
        self._inject_theme(kwargs, {
            "activebgoncolor": "accent",
        })
        ref = self.add_box(toggle(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

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
        ref = self.add_box(menu(id, varname, rect, options=options, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_number_box(self, id: str, varname: str, rect: list, **kwargs) -> str:
        ref = self.add_box(number_box(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_slider(self, id: str, varname: str, rect: list, **kwargs) -> str:
        ref = self.add_box(slider(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_button(self, id: str, varname: str, rect: list, **kwargs) -> str:
        ref = self.add_box(button(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_live_text(self, id: str, varname: str, rect: list, **kwargs) -> str:
        ref = self.add_box(live_text(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

    def add_fpic(self, id: str, rect: list, **kwargs) -> str:
        return self.add_box(fpic(id, rect, **kwargs))

    def add_live_gain(self, id: str, varname: str, rect: list, **kwargs) -> str:
        ref = self.add_box(live_gain(id, varname, rect, **kwargs))
        self._register_parameter_arg(ref, varname, kwargs)
        return ref

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
        self.register_asset(js_filename, js_code, asset_type="TEXT", category="js")
        return self.add_box(jsui(id, rect, js_filename=js_filename,
                                 numinlets=numinlets, numoutlets=numoutlets,
                                 **kwargs))

    def add_v8ui(self, id: str, rect: list, *, js_code: str,
                 js_filename: str = None, numinlets: int = 1,
                 numoutlets: int = 0, **kwargs) -> str:
        """Add a v8ui with embedded JavaScript code for pointer-aware custom UI."""
        if js_filename is None:
            js_filename = f"{id}.js"
        self.register_asset(js_filename, js_code, asset_type="TEXT", category="js")
        return self.add_box(v8ui(id, rect, js_filename=js_filename,
                                 numinlets=numinlets, numoutlets=numoutlets,
                                 **kwargs))

    def add_support_file(self, filename: str, content: str,
                         file_type: str = "TEXT") -> str:
        """Register an auxiliary file to write alongside the .amxd build."""
        self.register_asset(filename, content, asset_type=file_type, category="support")
        return filename

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

    def add_newobj(self, id: str = None, text: str = "", *, numinlets: int, numoutlets: int,
                   **kwargs) -> str:
        return super().add_newobj(id, text, numinlets=numinlets,
                                  numoutlets=numoutlets, **kwargs)

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

    def validate(self) -> list:
        """Check the device for common problems. Returns a list of warning strings."""
        return super().validate()

    def assign_parameter_bank(self, varname, bank: int, position: int,
                              bank_name: str = None):
        """Map a parameter into Push's bank layout for hardware control."""
        if bank < 0:
            raise ValueError(f"bank must be >= 0, got {bank}")
        if position < 0:
            raise ValueError(f"position must be >= 0, got {position}")
        param_name = self._resolve_parameter_name(varname)
        self._param_banks[param_name] = (bank, position)
        if bank_name is not None:
            self._param_bank_names[bank] = bank_name
        spec = self.parameter(param_name)
        if spec is not None:
            spec.bank = bank
            spec.position = position
            if bank_name is not None:
                spec.bank_name = bank_name

    def set_parameter_bank_name(self, bank: int, name: str):
        """Set a human-readable label for a parameter bank."""
        if bank < 0:
            raise ValueError(f"bank must be >= 0, got {bank}")
        self._param_bank_names[bank] = name
        for spec in self._parameter_specs.values():
            if spec.bank == bank:
                spec.bank_name = name

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
            device._assets.clear()
            device._parameter_specs.clear()
            device._box_parameters.clear()
            device._reserved_ids.clear()

        for box in patcher.get("boxes", []):
            device.add_box(box)
        for line in patcher.get("lines", []):
            device.lines.append(line)
        for bank_key, bank_data in patcher.get("parameters", {}).get("parameterbanks", {}).items():
            bank_index = int(bank_key)
            bank_name = bank_data.get("name") or None
            if bank_name is not None:
                device.set_parameter_bank_name(bank_index, bank_name)
            for entry in bank_data.get("parameters", []):
                name = entry.get("name")
                if name is None:
                    continue
                device.assign_parameter_bank(
                    name,
                    bank=bank_index,
                    position=entry.get("index", 0),
                    bank_name=bank_name,
                )

        return device

    def to_patcher(self, *, profile=None) -> dict:
        effective_profile = profile or self.profile
        patcher = build_patcher(
            self.boxes, self.lines,
            name=self.name,
            width=self.width,
            height=self.height,
            device_type=self.device_type,
            profile=effective_profile,
        )
        patcher["patcher"]["dependency_cache"] = [
            asset.dependency_entry() for asset in self.assets()
        ]
        # Populate parameter banks from assign_parameter_bank() calls
        if self._param_banks:
            banks = {}
            for varname, (bank, position) in self._param_banks.items():
                bank_key = str(bank)
                if bank_key not in banks:
                    banks[bank_key] = {
                        "index": bank,
                        "name": self._param_bank_names.get(bank, ""),
                        "parameters": [],
                    }
                spec = self.parameter(varname)
                banks[bank_key]["parameters"].append({
                    "index": position,
                    "name": varname,
                    "visible": 1 if spec is None else spec.visible,
                })
            patcher["patcher"]["parameters"]["parameterbanks"] = banks
        return patcher

    def to_bytes(self, *, validate=None) -> bytes:
        """Build the .amxd binary in memory."""
        self._apply_validation_policy(validate)
        type_code = DEVICE_TYPE_CODES[self.device_type]
        return build_amxd(self.to_patcher(), type_code)

    def build(self, output_path: str, *, validate=None) -> int:
        """Build and write the .amxd file. Returns bytes written.

        Also writes any embedded JS files alongside the .amxd for jsui objects.
        """
        self._apply_validation_policy(validate)
        type_code = DEVICE_TYPE_CODES[self.device_type]
        result = write_amxd(self.to_patcher(), output_path, type_code)
        output_dir = os.path.dirname(output_path)
        for asset in self.assets():
            try:
                asset.write_to(output_dir)
            except OSError as e:
                raise IOError(
                    f"Cannot write sidecar file {os.path.join(output_dir, asset.filename)}: {e}"
                ) from e
        return result

    def _apply_validation_policy(self, policy):
        if policy in (None, False):
            return
        if policy not in {"warn", "error"}:
            raise ValueError("validate must be one of None, 'warn', or 'error'")

        issues = self.lint(device_type=self.device_type)
        if not issues:
            return

        error_issues = [issue for issue in issues if issue.severity == "error"]
        warning_issues = [issue for issue in issues if issue.severity != "error"]

        if policy == "warn":
            warnings.warn(format_validation_issues(issues), stacklevel=3)
            return

        if error_issues:
            raise BuildValidationError(error_issues, warnings=warning_issues)
        if warning_issues:
            warnings.warn(format_validation_issues(warning_issues), stacklevel=3)


class AudioEffect(Device):
    """Audio effect device with plugin~/plugout~ auto-added."""

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None):
        super().__init__(
            name,
            width,
            height,
            device_type="audio_effect",
            theme=theme,
            profile=profile,
        )
        # Auto-add stereo I/O
        boxes, lines = stereo_io()
        self.add_dsp(boxes, lines)


class Instrument(Device):
    """Instrument device."""

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None):
        super().__init__(
            name,
            width,
            height,
            device_type="instrument",
            theme=theme,
            profile=profile,
        )


class MidiEffect(Device):
    """MIDI effect device."""

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None):
        super().__init__(
            name,
            width,
            height,
            device_type="midi_effect",
            theme=theme,
            profile=profile,
        )
