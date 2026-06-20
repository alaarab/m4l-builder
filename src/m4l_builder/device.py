"""High-level Device API for building M4L devices."""

from __future__ import annotations

import json
from typing import Any

from .amxd import build_device, device_from_amxd, device_to_bytes, device_to_patcher
from .dsp import stereo_io
from .graph import BoxRef, GraphContainer
from .jsui_contract import validate_jsui_contract, validate_v8ui_contract
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
        # Defined Latency (samples) reported to Live for plugin delay
        # compensation — the patcher-level "latency" key.
        self.latency = 0
        self.profile = profile or DEFAULT_PATCHER_PROFILE
        self._js_files: dict[Any, Any] = {}
        self._param_banks: dict[Any, Any] = {}
        self._param_bank_names: dict[Any, Any] = {}
        self._support_files: dict[Any, Any] = {}

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
        validate_contract: bool = True,
        **kwargs,
    ) -> str:
        """Add a v8ui with embedded JavaScript code for pointer-aware custom UI.

        validate_contract checks the shared mgraphics bootstrap (init/paint/redraw)
        without imposing jsui's ES5 restriction — v8ui runs on V8 and ES6+ is
        intended. Pass validate_contract=False to bypass.
        """
        if validate_contract:
            validate_v8ui_contract(js_code)
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
    ) -> BoxRef:
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

    def add_flyout(
        self,
        content,
        *,
        expand_rect: list,
        param_name: str = "Expand",
        button_id: str = "flyout_expand",
        text_on: str = "EXPAND",
        text_off: str = "EXPAND",
        show_send: str = None,
        hide_send: str = None,
        window_flags: str = "float grow",
        box_rect: list = None,
        button_kwargs: dict = None,
    ) -> str:
        """Add an expandable fly-out window (the M4L "fly-out" pattern).

        `content` is a Subpatcher holding the big UI — build it with a profile
        that sets ``subpatch_openinpresentation=1`` and your window rect
        (``subpatch_rect`` = [left, top, width, height]), and put a big jsui in
        it (jsui renders reliably; presentation panels/comments do not). This
        method injects the open/close/floating plumbing into `content` and adds
        an EXPAND live.text param toggle to the main view that shows/hides a
        resizable floating window.

        The window opens via the subpatcher's own ``[thispatcher] front``
        (``[pcontrol] open`` silently fails in M4L). NOTE: the window only
        opens when Live is the frontmost app. Returns the subpatcher box id.
        """
        # Prefix with --- so the send/receive names are scoped to THIS device
        # instance (the patcher hierarchy), not global across every device in the
        # Live set — otherwise two instances would open each other's windows.
        show_send = "---" + (show_send or f"{content.name}_show")
        hide_send = "---" + (hide_send or f"{content.name}_hide")

        def _msg(container, mid, text, rect):
            container.add_box({"box": {
                "id": mid, "maxclass": "message", "text": text,
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": rect}})

        # --- Plumbing inside the content subpatcher (hidden in patching view) ---
        content.add_newobj("_fly_this", "thispatcher", numinlets=1, numoutlets=1,
                           outlettype=[""], patching_rect=[40, 380, 70, 20])
        content.add_newobj("_fly_rshow", f"r {show_send}", numinlets=0, numoutlets=1,
                           outlettype=["bang"], patching_rect=[40, 300, 90, 20])
        content.add_newobj("_fly_rhide", f"r {hide_send}", numinlets=0, numoutlets=1,
                           outlettype=["bang"], patching_rect=[200, 300, 90, 20])
        _msg(content, "_fly_front", "front", [40, 330, 50, 20])
        _msg(content, "_fly_wclose", "wclose", [200, 330, 60, 20])
        content.add_line("_fly_rshow", 0, "_fly_front", 0)
        content.add_line("_fly_rhide", 0, "_fly_wclose", 0)
        content.add_line("_fly_front", 0, "_fly_this", 0)
        content.add_line("_fly_wclose", 0, "_fly_this", 0)
        # floating + resizable, set on load (flags before exec)
        content.add_newobj("_fly_lb", "loadbang", numinlets=0, numoutlets=1,
                           outlettype=["bang"], patching_rect=[40, 410, 60, 20])
        content.add_newobj("_fly_trig", "t b b", numinlets=1, numoutlets=2,
                           outlettype=["bang", "bang"], patching_rect=[40, 440, 50, 20])
        _msg(content, "_fly_flags", f"window flags {window_flags}", [40, 470, 200, 20])
        _msg(content, "_fly_exec", "window exec", [260, 470, 110, 20])
        content.add_line("_fly_lb", 0, "_fly_trig", 0)
        content.add_line("_fly_trig", 1, "_fly_flags", 0)
        content.add_line("_fly_trig", 0, "_fly_exec", 0)
        content.add_line("_fly_flags", 0, "_fly_this", 0)
        content.add_line("_fly_exec", 0, "_fly_this", 0)

        # --- Main view: EXPAND param toggle -> sel -> send show/hide ---
        bkw = {"text_on": text_on, "text_off": text_off, "rounded": 4,
               "fontsize": 7.5, "mode": 1}
        if button_kwargs:
            bkw.update(button_kwargs)
        self.add_live_text(button_id, param_name, expand_rect,
                           parameter=ParameterSpec(
                               name=param_name, parameter_type=2,
                               enum=["HIDE", "SHOW"], initial=[0],
                               initial_enable=True),
                           **bkw)
        self.add_newobj(f"{button_id}_sel", "sel 1 0", numinlets=1, numoutlets=3,
                        outlettype=["bang", "bang", ""], patching_rect=[700, 1400, 60, 20])
        self.add_newobj(f"{button_id}_sshow", f"s {show_send}", numinlets=1,
                        numoutlets=0, patching_rect=[700, 1430, 90, 20])
        self.add_newobj(f"{button_id}_shide", f"s {hide_send}", numinlets=1,
                        numoutlets=0, patching_rect=[800, 1430, 90, 20])
        self.add_line(button_id, 0, f"{button_id}_sel", 0)
        self.add_line(f"{button_id}_sel", 0, f"{button_id}_sshow", 0)
        self.add_line(f"{button_id}_sel", 1, f"{button_id}_shide", 0)

        return self.add_subpatcher(content, f"{button_id}_sp",
                                   box_rect or [700, 1460, 90, 22],
                                   numinlets=0, numoutlets=0)

    def add_width_collapse(
        self,
        *,
        full_width: int,
        mini_width: int,
        rect: list,
        param_name: str = "Size",
        button_id: str = "width_collapse",
        text_full: str = "FULL",
        text_mini: str = "MINI",
        button_kwargs: dict = None,
    ) -> str:
        """Add a FULL/MINI width-collapse toggle (runtime device resize).

        Sends ``setwidth <px>`` to ``[live.thisdevice]`` so Live narrows the
        inline device strip to ``mini_width`` (essentials only) or expands it to
        ``full_width``. Only WIDTH resizes at runtime — Live fixes the height at
        169px. The toggle is a real Live param (enum ``[text_full, text_mini]``,
        FULL=0 default) so it's automatable + recalled with the set.

        PLACE THE BUTTON ON THE LEFT: a MINI width clips the right side off (it
        does not reflow), so the toggle must sit inside ``mini_width`` to stay
        clickable, and the device's essentials should live on the left.

        Returns the toggle button id.
        """
        bkw = {"text_on": text_mini, "text_off": text_full, "rounded": 4,
               "fontsize": 7.5, "mode": 1}
        if button_kwargs:
            bkw.update(button_kwargs)
        self.add_live_text(button_id, param_name, rect,
                           parameter=ParameterSpec(
                               name=param_name, parameter_type=2,
                               enum=[text_full, text_mini], initial=[0],
                               initial_enable=True),
                           **bkw)
        self.add_newobj(f"{button_id}_thisdev", "live.thisdevice", numinlets=1,
                        numoutlets=3, outlettype=["bang", "", ""],
                        patching_rect=[700, 1500, 90, 20])
        self.add_newobj(f"{button_id}_sel", "sel 0 1", numinlets=1, numoutlets=3,
                        outlettype=["bang", "bang", ""],
                        patching_rect=[700, 1530, 60, 20])

        def _setwidth_msg(mid, w, x):
            self.add_box({"box": {
                "id": mid, "maxclass": "message", "text": f"setwidth {w}",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [x, 1560, 110, 20]}})

        _setwidth_msg(f"{button_id}_msgfull", full_width, 700)
        _setwidth_msg(f"{button_id}_msgmini", mini_width, 820)
        self.add_line(button_id, 0, f"{button_id}_sel", 0)
        self.add_line(f"{button_id}_sel", 0, f"{button_id}_msgfull", 0)  # 0 = FULL
        self.add_line(f"{button_id}_sel", 1, f"{button_id}_msgmini", 0)  # 1 = MINI
        self.add_line(f"{button_id}_msgfull", 0, f"{button_id}_thisdev", 0)
        self.add_line(f"{button_id}_msgmini", 0, f"{button_id}_thisdev", 0)
        return button_id

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


class MidiTransformation(Device):
    """Live 12 MIDI Transformation device (a MIDI Tool).

    Rewrites the selected notes of a clip. Build the patcher around a
    ``live.miditool.in`` -> processing -> ``live.miditool.out`` chain (see
    ``midi_tool_io``). No audio/MIDI I/O is auto-added.
    """

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None):
        super().__init__(
            name,
            width,
            height,
            device_type="note_transformation",
            theme=theme,
            profile=profile,
        )


class MidiGenerator(Device):
    """Live 12 MIDI Generator device (a MIDI Tool).

    Adds new notes to a clip. Build the patcher around a ``live.miditool.in``
    -> processing -> ``live.miditool.out`` chain (see ``midi_tool_io``). No
    audio/MIDI I/O is auto-added.
    """

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None):
        super().__init__(
            name,
            width,
            height,
            device_type="note_generator",
            theme=theme,
            profile=profile,
        )


for _widget_name, _widget_spec in DEVICE_WIDGET_SPECS.items():
    setattr(Device, f"add_{_widget_name}", make_device_widget_method(_widget_name, _widget_spec))

del _widget_name
del _widget_spec
