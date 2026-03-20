"""High-level Device API for building M4L devices."""

from __future__ import annotations

import json

from .amxd import build_device, device_from_amxd, device_to_bytes, device_to_patcher
from .dsp import stereo_io
from .graph import GraphContainer
from .jsui_contract import validate_jsui_contract
from .layout import Column, Columns, Grid, Row
from .parameters import ParameterSpec
from .profiles import DEFAULT_PATCHER_PROFILE
from .ui import jsui, v8ui
from .ui_registry import DEVICE_WIDGET_SPECS, make_device_widget_method


class Device(GraphContainer):
    """Base class for M4L devices.

    Provides a builder-style API for adding objects, UI elements, and
    connections, then serializing to a `.amxd` file.
    """

    def __init__(
        self,
        name: str,
        width: float,
        height: float,
        device_type: str = "audio_effect",
        theme=None,
        profile=None,
    ):
        super().__init__()
        self.name = name
        self.width = width
        self.height = height
        self.device_type = device_type
        self.theme = theme
        self.profile = profile or DEFAULT_PATCHER_PROFILE
        self._js_files = {}
        self._param_banks = {}
        self._param_bank_names = {}
        self._support_files = {}

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
        """Inject theme defaults for keys not already in kwargs."""
        if not self.theme:
            return
        for kwarg_key, theme_attr in mapping.items():
            if kwarg_key not in kwargs:
                value = getattr(self.theme, theme_attr, None)
                if value is not None:
                    kwargs[kwarg_key] = value

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

    def add_jsui(
        self,
        id: str,
        rect: list,
        *,
        js_code: str,
        js_filename: str = None,
        numinlets: int = 1,
        numoutlets: int = 0,
        validate_contract: bool = True,
        **kwargs,
    ) -> str:
        """Add a jsui with embedded JavaScript code for custom vector graphics."""
        if validate_contract:
            validate_jsui_contract(js_code)
        js_filename = js_filename or f"{id}.js"
        self.register_asset(js_filename, js_code, asset_type="TEXT", category="js")
        return self.add_box(
            jsui(
                id,
                rect,
                js_filename=js_filename,
                numinlets=numinlets,
                numoutlets=numoutlets,
                **kwargs,
            )
        )

    def add_v8ui(
        self,
        id: str,
        rect: list,
        *,
        js_code: str,
        js_filename: str = None,
        numinlets: int = 1,
        numoutlets: int = 0,
        **kwargs,
    ) -> str:
        """Add a v8ui with embedded JavaScript code for pointer-aware custom UI."""
        js_filename = js_filename or f"{id}.js"
        self.register_asset(js_filename, js_code, asset_type="TEXT", category="js")
        return self.add_box(
            v8ui(
                id,
                rect,
                js_filename=js_filename,
                numinlets=numinlets,
                numoutlets=numoutlets,
                **kwargs,
            )
        )

    def add_support_file(self, filename: str, content: str, file_type: str = "TEXT") -> str:
        """Register an auxiliary file to write alongside the .amxd build."""
        self.register_asset(filename, content, asset_type=file_type, category="support")
        return filename

    def add_newobj(
        self,
        id: str = None,
        text: str = "",
        *,
        numinlets: int,
        numoutlets: int,
        **kwargs,
    ) -> str:
        return super().add_newobj(id, text, numinlets=numinlets, numoutlets=numoutlets, **kwargs)

    def add_subpatcher(
        self,
        subpatcher,
        id: str,
        rect: list,
        *,
        numinlets: int = 1,
        numoutlets: int = 1,
        outlettype: list = None,
    ) -> str:
        """Add a Subpatcher as an embedded patcher box and return its ID."""
        box_dict = subpatcher.to_box(
            id,
            rect,
            numinlets=numinlets,
            numoutlets=numoutlets,
            outlettype=outlettype,
        )
        return self.add_box(box_dict)

    def row(self, x, y, *, spacing=8, height=None, width=None):
        return Row(self, x, y, spacing=spacing, height=height, width=width)

    def column(self, x, y, *, spacing=4, width=None, height=None):
        return Column(self, x, y, spacing=spacing, width=width, height=height)

    def grid(self, x, y, *, cols, col_width, row_height, spacing_x=4, spacing_y=4):
        return Grid(
            self,
            x,
            y,
            cols=cols,
            col_width=col_width,
            row_height=row_height,
            spacing_x=spacing_x,
            spacing_y=spacing_y,
        )

    def columns(self, x, y, *, width, cols=12.0, height=None):
        return Columns(self, x, y, width=width, cols=cols, height=height)

    def to_json(self, indent: int = 2) -> str:
        """Serialize the device patcher structure to a JSON string."""
        return json.dumps(self.to_patcher(), indent=indent)

    def validate(self) -> list:
        """Check the device for common problems. Returns a list of warning strings."""
        return super().validate()

    def assign_parameter_bank(self, varname, bank: int, position: int, bank_name: str = None):
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
        return device_from_amxd(path)

    def to_patcher(self, *, profile=None) -> dict:
        return device_to_patcher(self, profile=profile)

    def to_bytes(self, *, validate=None) -> bytes:
        """Build the .amxd binary in memory."""
        return device_to_bytes(self, validate=validate)

    def build(self, output_path: str, *, validate=None) -> int:
        """Build and write the .amxd file. Returns bytes written."""
        return build_device(self, output_path, validate=validate)


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


for _widget_name, _widget_spec in DEVICE_WIDGET_SPECS.items():
    setattr(Device, f"add_{_widget_name}", make_device_widget_method(_widget_name, _widget_spec))

del _widget_name
del _widget_spec
