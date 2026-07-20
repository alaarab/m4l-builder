"""High-level Device API for building M4L devices."""

from __future__ import annotations

import json
from typing import Any

from .amxd import build_device, device_from_amxd, device_to_bytes, device_to_patcher
from .device_widgets import CompositeWidgetsMixin
from .dsp import stereo_io
from .engines.design_system import js_sidecar_name
from .gen_lint import find_function_defs
from .gen_patcher import build_gendsp, gendsp_support_name
from .gen_patcher import embed_gendsp as _embed_gendsp_box
from .graph import BoxRef, GraphContainer
from .jsui_contract import validate_jsui_contract, validate_v8ui_contract
from .layout import Column, Columns, Grid, Row
from .native_sizes import DEVICE_H
from .parameters import ParameterSpec
from .patcher_walk import iter_boxes
from .profiles import DEFAULT_PATCHER_PROFILE
from .ui import jsui, v8ui
from .ui_registry import DEVICE_WIDGET_SPECS, make_device_widget_method
from .validation import _DECORATION_MAXCLASSES, ValidationIssue, layout_issues

# Device-view height ceiling: Live's device chain shows only ~DEVICE_H px tall
# regardless of the authored height, so a taller chain device (audio_effect /
# instrument / midi_effect) silently CLIPS its bottom rows. MIDI Tools render in a
# different UI and are exempt from the ceiling check.
_CHAIN_DEVICE_TYPES = frozenset({"audio_effect", "instrument", "midi_effect"})


class Device(CompositeWidgetsMixin, GraphContainer):
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
        allow_tall: bool = False,
    ):
        super().__init__()
        self.name = name
        self.width = width
        self.height = height
        self.device_type = device_type
        self.theme = theme
        # Opt out of the device-view height-ceiling lint (DEVICE_H). Set True only
        # for a taller custom layout (e.g. 190px),
        # which reproduces the source's rects verbatim and accepts its clipping.
        self.allow_tall = allow_tall
        # Defined Latency (samples) reported to Live for plugin delay
        # compensation — the patcher-level "latency" key.
        self.latency = 0
        # Declare MPE support to Live — the patcher-level "is_mpe" key. When
        # True, Live delivers per-note MPE data (member-channel notes, bend,
        # pressure, CC74) to the device instead of folding it to one channel
        # (patcher.maxref: "a Max for Live device will receive MPE data from
        # Live"; Granulator III ships is_mpe: 1).
        self.is_mpe = False
        self.profile = profile or DEFAULT_PATCHER_PROFILE
        self._js_files: dict[Any, Any] = {}
        self._param_banks: dict[Any, Any] = {}
        self._param_bank_names: dict[Any, Any] = {}
        self._support_files: dict[Any, Any] = {}

    def lint(self, *, device_type: str = None):
        """Graph lint + device-level layout rules (height ceiling + clipped controls).

        Appends WARNING-severity issues (not wiring errors, so default
        ``validate=None`` builds stay silent; they surface under
        ``validate="warn"``/``"error"``):

        * ``device-height-over-ceiling`` — a chain device authored taller than
          Live's ~``DEVICE_H``px device view, so its bottom rows are clipped +
          unreachable (Live-verified: Linear Phase Crossover=214 lost ~45px).
          ``allow_tall=True`` (a faithful clone of a taller original) opts out.
        * ``control-clipped`` — a FUNCTIONAL control whose ``presentation_rect``
          straddles a device edge (partly visible, partly cut). The complement to
          the height rule: a device can be ≤168 yet still place a dial at y=150,h=30
          (bottom 180) so it is half-cut. Decoration (``panel`` full-bleed
          backgrounds, labels, dividers) and FULLY off-canvas boxes (the parked /
          hidden ~(900,900) probe idiom) are excluded — empirically false-positive
          -free across the 33-device fleet.
        * :func:`~m4l_builder.validation.layout_issues` — ``control-overlap`` /
          ``dead-zone`` / ``width-mismatch`` (warnings) + ``setwidth-mismatch``
          (error): the space-utilization rules from the corpus audit (a FULL
          collapse wider than the layout, >=40px dead bands, stale widths).
        """
        issues = list(super().lint(device_type=device_type))
        effective_type = device_type or self.device_type
        if (
            not self.allow_tall
            and effective_type in _CHAIN_DEVICE_TYPES
            and self.height > DEVICE_H
        ):
            clipped = self.height - DEVICE_H
            issues.append(ValidationIssue(
                code="device-height-over-ceiling",
                message=(
                    f"authored height {self.height:g} exceeds Live's ~{DEVICE_H}px "
                    f"device-view ceiling; the bottom ~{clipped:g}px will be CLIPPED "
                    f"and unreachable. Condense to <= {DEVICE_H}, or pass "
                    f"allow_tall=True for a faithful clone of a taller original."
                ),
                severity="warning",
            ))
        issues.extend(self._clipped_control_issues())
        issues.extend(layout_issues(self.boxes, self.width, self.height))
        return issues

    def check_guidelines(self) -> list:
        """Static Ableton production-standards report for this device (advisory).

        Checks the built patcher against the decidable subset of Ableton's own
        published Max for Live standards (unknown/misspelled object names,
        duplicate parameter Long/Scripting Names, auto-indexed default names,
        fractional pixel rects, forbidden print/dac~/adc~, non-local
        send/receive). Returns :class:`ValidationIssue`s; never raises, never
        gates the build. The pre-Live complement to the live console audit. See
        :mod:`m4l_builder.guidelines`.
        """
        from .guidelines import check_guidelines
        return check_guidelines(self)

    def _clipped_control_issues(self) -> list:
        """WARNING for each functional control partly off a device edge.

        Flags a presentation control only when its rect INTERSECTS the visible
        ``width``×``height`` area AND spills past an edge — a partial clip (the
        "I can see half my knob" bug). A box fully outside the canvas is treated as
        intentionally parked/hidden (the corpus ~(900,900) idiom) and skipped, as is
        any decoration maxclass (a ``panel`` background routinely full-bleeds past
        the edge by design; a clipped label/divider is cosmetic, not an unreachable
        control).
        """
        out: list = []
        w_dev, h_dev = float(self.width), float(self.height)
        for payload in iter_boxes(self):
            if payload.get("presentation") != 1:
                continue
            if payload.get("maxclass") in _DECORATION_MAXCLASSES:
                continue
            rect = payload.get("presentation_rect")
            if not rect or len(rect) < 4:
                continue
            try:
                x, y, w, h = (float(v) for v in rect[:4])
            except (TypeError, ValueError):
                continue
            if x >= w_dev or y >= h_dev or x + w <= 0 or y + h <= 0:
                continue  # fully off-canvas → intentionally parked/hidden
            sides = []
            if y + h > h_dev + 0.5:
                sides.append("bottom")
            if x + w > w_dev + 0.5:
                sides.append("right")
            if x < -0.5:
                sides.append("left")
            if y < -0.5:
                sides.append("top")
            if sides:
                out.append(ValidationIssue(
                    code="control-clipped",
                    message=(
                        f"control ({payload.get('maxclass')}) runs past the device "
                        f"{'/'.join(sides)} edge — presentation_rect "
                        f"[{x:g}, {y:g}, {w:g}, {h:g}] vs {w_dev:g}x{h_dev:g}; it is "
                        f"partly clipped/unreachable. Move it fully inside the frame."
                    ),
                    severity="warning",
                    box_id=payload.get("id"),
                ))
        return out

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
        content_address: bool = False,
        static: bool = False,
        **kwargs,
    ) -> str:
        """Add a jsui with embedded JavaScript code for custom vector graphics.

        ``content_address=True`` folds a hash of ``js_code`` into the sidecar
        filename so a JS edit auto-busts Max's by-name sidecar cache (no manual bump).
        ``static=True`` marks a read-only display (legend art) that paints once —
        the contract's redraw-hook requirement is waived.
        """
        if validate_contract:
            validate_jsui_contract(js_code, static=static)
        js_filename = js_filename or f"{id}.js"
        if content_address:
            js_filename = js_sidecar_name(js_filename, js_code)
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
        content_address: bool = False,
        **kwargs,
    ) -> str:
        """Add a v8ui with embedded JavaScript code for pointer-aware custom UI.

        validate_contract checks the shared mgraphics bootstrap (init/paint/redraw)
        without imposing jsui's ES5 restriction — v8ui runs on V8 and ES6+ is
        intended. Pass validate_contract=False to bypass.

        content_address=True folds a hash of ``js_code`` into the sidecar filename
        (``{stem}_{hash}.js``) so editing the JS auto-renames it and Max reloads the
        new snippet — no manual ``_vN`` bump (Max caches sidecars by name). The kit's
        custom controls set it; a fixed ``js_filename`` you assert in a test should not.
        """
        if validate_contract:
            validate_v8ui_contract(js_code)
        js_filename = js_filename or f"{id}.js"
        if content_address:
            js_filename = js_sidecar_name(js_filename, js_code)
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



    @staticmethod
    def _panel_slice(rect, bg_hi, bg_lo, device_height, inset):
        """The ``(bg_top, bg_bot)`` ``"r, g, b"`` strings for a control at ``rect``:
        the slice of the device panel gradient (``bg_hi`` top → ``bg_lo`` bottom)
        spanning the control's vertical extent, so its self-painted background
        blends seamlessly with the panel (no opaque v8ui object box). Returns
        ``(None, None)`` when the gradient/geometry isn't supplied."""
        if bg_hi is None or bg_lo is None or not device_height:
            return None, None
        span = max(1.0, float(device_height) - 2.0 * inset)

        def _slice(py):
            f = max(0.0, min(1.0, (py - inset) / span))
            return ", ".join(f"{bg_hi[i] + (bg_lo[i] - bg_hi[i]) * f:.4f}" for i in range(3))

        return _slice(rect[1]), _slice(rect[1] + rect[3])















    def add_support_file(self, filename: str, content: str, file_type: str = "TEXT") -> str:
        """Register an auxiliary file to write alongside the .amxd build."""
        self.register_asset(filename, content, asset_type=file_type, category="support")
        return filename

    def add_gendsp(
        self,
        id: str,
        stem: str,
        code: str,
        numins: int,
        numouts: int,
        rect: list,
        *,
        lint: bool = True,
        codebox_h: float = 560.0,
        patcher_h: float = 660.0,
        **newobj_kwargs,
    ) -> BoxRef:
        """Turn-key EXTERNAL ``gen~`` core: build the ``.gendsp``, register it under
        a CONTENT-ADDRESSED filename, and wire the ``gen~ <stem>_<hash>`` object —
        all in one call, so the support-file name and the ``gen~`` reference can
        never desync.

        Replaces the copy-pasted ``GEN_FILENAME = "core_vNN.gendsp"`` +
        ``add_support_file(GEN_FILENAME, build_gendsp(...))`` + ``gen~
        GEN_FILENAME[:-7]`` triple every DSP plugin carried. The manual ``_vNN``
        bump (needed because Max caches a compiled ``gen~`` by *filename*) is gone:
        the suffix is a hash of ``code`` via
        :func:`m4l_builder.gen_patcher.gendsp_support_name`, so editing the DSP
        auto-renames the file and Live always recompiles fresh — see that helper
        for the stale-gen-cache failure class this closes.

        ``rect`` is the ``gen~`` box ``patching_rect``; ``numins``/``numouts`` size
        the codebox AND the object's inlets/outlets (outlets default to ``signal``).
        Extra ``newobj_kwargs`` pass through to :meth:`add_newobj`. Returns the
        ``gen~`` :class:`~m4l_builder.graph.BoxRef`.

        REFUSES function-bearing gen source: Live's gen compiler SILENCES a
        codebox loaded from an external ``.gendsp`` when the code defines any
        depth-0 ``name(args){...}`` function (Live-verified, ZZGenFuncEmbed —
        the fleet's silent-device trap). Use :meth:`embed_gendsp` for the
        ``gen_stateful`` function kit; keep this path for fully inlined code.
        """
        fn_defs = find_function_defs(code)
        if fn_defs:
            raise ValueError(
                f"add_gendsp({stem!r}): gen source defines function(s) "
                f"{', '.join(fn_defs)} at depth 0. An EXTERNAL .gendsp support "
                "file SILENCES any codebox that defines a function (Live-verified "
                "— see gen_patcher.embed_gendsp). Use Device.embed_gendsp(...) "
                "instead, which embeds the gen patcher inline and compiles fine."
            )
        content = build_gendsp(
            code, numins, numouts, lint=lint, codebox_h=codebox_h, patcher_h=patcher_h,
        )
        filename = gendsp_support_name(stem, code)
        self.add_support_file(filename, content)
        newobj_kwargs.setdefault("outlettype", ["signal"] * numouts)
        newobj_kwargs.setdefault("patching_rect", rect)
        return self.add_newobj(
            id, f"gen~ {filename[: -len('.gendsp')]}",
            numinlets=max(1, numins), numoutlets=numouts, **newobj_kwargs,
        )

    def embed_gendsp(
        self,
        id: str,
        code: str,
        numins: int,
        numouts: int,
        rect: list,
        *,
        lint: bool = True,
        codebox_h: float = 560.0,
        patcher_h: float = 660.0,
        **box_kwargs,
    ) -> BoxRef:
        """Turn-key EMBEDDED ``gen~`` core: the gen patcher is serialized INLINE
        in the ``gen~`` box (an embedded-structure pattern) instead of shipped as
        an external ``.gendsp`` support file.

        This is the REQUIRED path for gen source that defines functions
        (``gen_stateful``'s voice/reverb/filter kits): an embedded codebox MAY
        define ``name(args){...}`` functions and still compile + pass audio,
        while the external path :meth:`add_gendsp` takes silences them
        (Live-verified, ZZGenFuncEmbed — output meter 0.737 embedded vs 0.0
        external). Same call shape as :meth:`add_gendsp` minus ``stem`` (there
        is no support file, hence no content-addressed filename). Extra
        ``box_kwargs`` merge into the box dict (e.g. ``varname``). Returns the
        ``gen~`` :class:`~m4l_builder.graph.BoxRef`.
        """
        box_dict = _embed_gendsp_box(
            code, numins, numouts, box_id=id, patching_rect=list(rect),
            lint=lint, codebox_h=codebox_h, patcher_h=patcher_h,
        )
        box_dict["box"].update(box_kwargs)
        return self.add_box(box_dict)

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







    def paint_control(self, box_id, painter_filename: str, *, painter_js: str = None):
        """Attach a render-only ``jspainterfile`` painter to a NATIVE control (C1).

        Sets ``jspainterfile`` on the box ``box_id`` (a ``live.dial`` / ``live.numbox``
        / ``toggle`` …) so the control keeps full native behaviour + parameter
        storage while the ``.js`` paints it — the corpus pattern (seen across premium
        devices). When ``painter_js`` is given it is bundled alongside the device
        as a TEXT asset under ``painter_filename`` (via ``register_asset``); pass a
        painter from :mod:`m4l_builder.engines.painters` (e.g.
        :func:`lcd_panel_painter_js`). Returns ``painter_filename``.

        The control box must already exist (create it with ``add_dial`` /
        ``add_draggable_readout`` / etc. first). Raises ``KeyError`` if not found.
        """
        target = str(box_id)
        for box in iter_boxes(self):
            if box.get("id") == target:
                box["jspainterfile"] = painter_filename
                break
        else:
            raise KeyError(f"paint_control: no box with id {target!r}")

        if painter_js is not None:
            self.register_asset(painter_filename, painter_js, asset_type="TEXT")
        return painter_filename




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

    def to_bytes(self, *, validate=None, freeze: bool = False) -> bytes:
        """Build the .amxd binary in memory.

        When ``freeze`` is True, dependencies (jsui scripts, gen~ patchers,
        support files) are embedded inside the .amxd so the single file is
        self-contained and portable to other machines.
        """
        if freeze:
            from .freeze import device_to_frozen_bytes

            return device_to_frozen_bytes(self, validate=validate)
        return device_to_bytes(self, validate=validate)

    def build(self, output_path: str, *, validate=None, freeze: bool = False) -> int:
        """Build and write the .amxd file. Returns bytes written.

        When ``freeze`` is True, the written .amxd is self-contained (all
        dependencies embedded) and no sidecar files are emitted.
        """
        if freeze:
            from pathlib import Path

            data = self.to_bytes(validate=validate, freeze=True)
            Path(output_path).write_bytes(data)
            return len(data)
        return build_device(self, output_path, validate=validate)


class AudioEffect(Device):
    """Audio effect device with plugin~/plugout~ auto-added."""

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None,
                 allow_tall: bool = False):
        super().__init__(
            name,
            width,
            height,
            device_type="audio_effect",
            theme=theme,
            profile=profile,
            allow_tall=allow_tall,
        )
        boxes, lines = stereo_io()
        self.add_dsp(boxes, lines)


class Instrument(Device):
    """Instrument device."""

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None,
                 allow_tall: bool = False):
        super().__init__(
            name,
            width,
            height,
            device_type="instrument",
            theme=theme,
            profile=profile,
            allow_tall=allow_tall,
        )


class MidiEffect(Device):
    """MIDI effect device."""

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None,
                 allow_tall: bool = False):
        super().__init__(
            name,
            width,
            height,
            device_type="midi_effect",
            theme=theme,
            profile=profile,
            allow_tall=allow_tall,
        )


class MidiTransformation(Device):
    """Live 12 MIDI Transformation device (a MIDI Tool).

    Rewrites the selected notes of a clip. Build the patcher around a
    ``live.miditool.in`` -> processing -> ``live.miditool.out`` chain (see
    ``midi_tool_io``). No audio/MIDI I/O is auto-added.
    """

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None,
                 allow_tall: bool = False):
        super().__init__(
            name,
            width,
            height,
            device_type="note_transformation",
            theme=theme,
            profile=profile,
            allow_tall=allow_tall,
        )


class MidiGenerator(Device):
    """Live 12 MIDI Generator device (a MIDI Tool).

    Adds new notes to a clip. Build the patcher around a ``live.miditool.in``
    -> processing -> ``live.miditool.out`` chain (see ``midi_tool_io``). No
    audio/MIDI I/O is auto-added.
    """

    def __init__(self, name: str, width: float, height: float, theme=None, profile=None,
                 allow_tall: bool = False):
        super().__init__(
            name,
            width,
            height,
            device_type="note_generator",
            theme=theme,
            profile=profile,
            allow_tall=allow_tall,
        )


for _widget_name, _widget_spec in DEVICE_WIDGET_SPECS.items():
    setattr(Device, f"add_{_widget_name}", make_device_widget_method(_widget_name, _widget_spec))

del _widget_name
del _widget_spec
