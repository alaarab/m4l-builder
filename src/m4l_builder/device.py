"""High-level Device API for building M4L devices."""

from __future__ import annotations

import json
from typing import Any

from .amxd import build_device, device_from_amxd, device_to_bytes, device_to_patcher
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
from .profiles import DEFAULT_PATCHER_PROFILE
from .ui import jsui, v8ui
from .ui_registry import DEVICE_WIDGET_SPECS, make_device_widget_method
from .validation import _DECORATION_MAXCLASSES, ValidationIssue, layout_issues

# Device-view height ceiling: Live's device chain shows only ~DEVICE_H px tall
# regardless of the authored height, so a taller chain device (audio_effect /
# instrument / midi_effect) silently CLIPS its bottom rows. MIDI Tools render in a
# different UI and are exempt from the ceiling check.
_CHAIN_DEVICE_TYPES = frozenset({"audio_effect", "instrument", "midi_effect"})


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
        allow_tall: bool = False,
    ):
        super().__init__()
        self.name = name
        self.width = width
        self.height = height
        self.device_type = device_type
        self.theme = theme
        # Opt out of the device-view height-ceiling lint (DEVICE_H). Set True only
        # for a faithful clone of a taller commercial original (e.g. SEAR=190),
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
        for box in self.boxes:
            payload = box.get("box", {})
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

    def add_compiled_display(
        self,
        base_id: str,
        maxclass: str,
        rect: list,
        *,
        overlay_js: str,
        overlay_filename: str,
        attrs: dict = None,
        signal_src=None,
        gate_src: tuple = None,
        inset: tuple = (0, 0, 0, 0),
        scope_numinlets: int = 2,
        scope_numoutlets: int = 1,
        scope_outlettype: list = None,
        scope_patching_rect: list = None,
        overlay_inlets: int = 1,
        overlay_outlets: int = 0,
        overlay_outlettype: list = None,
        overlay_patching_rect: list = None,
        overlay_behind: bool = False,
        overlay_bgcolor: list = None,
        overlay_content_address: bool = False,
        varname: str = None,
        validate_contract: bool = True,
    ) -> tuple:
        """Layer a native compiled-Max display together with a ``v8ui`` overlay.

        The keystone recipe proven by Parametric EQ V2: a native compiled object
        (``spectroscope~``, ``scope~`` …) renders the dense realtime fill in C++
        (smoother + cheaper than jsui, and portable — it ships with Max), while a
        ``v8ui`` supplies the grid, labels, curve and pointer interaction. An
        optional CPU ``gate_src`` and an ``inset`` (so the compiled rect lands
        inside the overlay's axis margins) round it out.

        Z-ORDER (Live-verified 2026-06 — see docs/ui_inputs_reference.md "Compiled
        display OVER an interactive v8ui EATS the clicks"): EVERY compiled Max
        display (``spectroscope~``, ``scope~``, ``waveform~``, ``meter~``,
        ``filtergraph~``) renders ABOVE a ``v8ui`` **regardless of patcher box
        order** AND captures the pointer in its rect — so a v8ui beneath it stops
        receiving clicks even when the compiled object is invisible. (The earlier
        "``spectroscope~`` renders BELOW" claim was wrong — the Parametric EQ V2
        node-click bug disproved it.) Consequences:

          • INTERACTIVE overlay (draggable EQ nodes / XY pad): its clickable rect
            must be FREE of any compiled object — draw the data INSIDE the v8ui and
            drop the compiled object (what Parametric EQ V2 does), or remove it. Do
            NOT rely on ``ignoreclick`` for ``spectroscope~``: it is a valid
            *universal* box attr (Common Box Attributes, ``[int]``), but click
            pass-through is corpus-proven only for ``waveform~``.
          • NON-interactive graticule-behind-fill look: set ``overlay_behind=True``
            — the overlay is added FIRST (behind) and draws its own opaque
            ``overlay_bgcolor`` while the compiled object stays transparent (pass a
            transparent ``bgcolor`` in ``attrs``) so the graticule reads through the
            fill. (Two boxes sharing the EXACT same rect z-fight — keep a small
            ``inset`` so the rects differ.)

        Args:
            base_id: the overlay's id; the compiled box is ``f"{base_id}_scope"``.
            maxclass, rect, attrs, signal_src, gate_src: forwarded to
                :meth:`add_compiled_ui` (``rect`` minus ``inset`` becomes the
                compiled box's presentation rect). ``scope_numinlets`` sets the
                compiled box's inlet count — e.g. ``2`` for a ``scope~`` X-Y
                goniometer fed ``signal_src=[(x, 0), (y, 0)]``.
            overlay_js, overlay_filename: the v8ui's code + cached filename.
                Pass ``overlay_content_address=True`` to fold a content hash
                into the filename (auto cache-bust; retires manual ``_vN`` bumps).
            inset: ``(left, top, right, bottom)`` px to shrink the compiled rect
                inside the overlay so the C++ fill aligns with the overlay's plot.
            overlay_behind: put the v8ui BEHIND the compiled object (for ``scope~``).
            overlay_bgcolor: the v8ui's background (default transparent; pass an
                opaque color when ``overlay_behind`` so it backs the compiled object).

        Returns ``(compiled_ref, overlay_ref)``.
        """
        il, it, ir, ib = inset
        scope_rect = [rect[0] + il, rect[1] + it, rect[2] - il - ir, rect[3] - it - ib]

        def _add_compiled():
            return self.add_compiled_ui(
                f"{base_id}_scope",
                maxclass,
                scope_rect,
                attrs=attrs,
                varname=f"{base_id}_scope",
                numinlets=scope_numinlets,
                numoutlets=scope_numoutlets,
                outlettype=scope_outlettype,
                patching_rect=scope_patching_rect,
                signal_src=signal_src,
                gate_src=gate_src,
            )

        def _add_overlay():
            return self.add_v8ui(
                base_id,
                rect,
                js_code=overlay_js,
                js_filename=overlay_filename,
                content_address=overlay_content_address,
                numinlets=overlay_inlets,
                numoutlets=overlay_outlets,
                outlettype=overlay_outlettype if overlay_outlettype is not None else [""] * overlay_outlets,
                patching_rect=overlay_patching_rect or [rect[0], rect[1], rect[2], rect[3]],
                background=0,
                ignoreclick=0,
                bgcolor=overlay_bgcolor if overlay_bgcolor is not None else [0.0, 0.0, 0.0, 0.0],
                varname=varname or base_id,
                validate_contract=validate_contract,
            )

        # Earlier-added box sits further back. front overlay → compiled first;
        # behind overlay → overlay first.
        if overlay_behind:
            overlay = _add_overlay()
            compiled = _add_compiled()
        else:
            compiled = _add_compiled()
            overlay = _add_overlay()
        return compiled, overlay

    def add_custom_knob(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        vmin: float = 0.0,
        vmax: float = 100.0,
        initial: float = None,
        unit: str = "",
        decimals: int = 1,
        accent: str = "0.30, 0.80, 0.84",
        exponent: float = 1.0,
        shortname: str = None,
        js_filename: str = None,
        varname: str = None,
        unitstyle: int = 1,
        bipolar: bool = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM hand-drawn knob (v8ui) bound to a HIDDEN automatable param.

        The v8ui DRAWS the knob (arc track + glowing value arc + indicator + lit
        body) and handles the vertical pointer drag (Shift = fine, double-click =
        reset); a 1×1 ``live.dial`` hidden BEHIND it (covered by the opaque knob
        body) holds the automatable Live parameter — size/position don't affect
        param registration. Drag the drawing → the param moves (and records
        automation); automate the param → the knob redraws. One call replaces the
        generic stock-``live.dial`` look. Returns the v8ui box id.

        ``param_name`` is the automatable Live parameter name; ``accent`` is an
        ``"r, g, b"`` string for the value arc; ``exponent`` log-scales the param
        (e.g. ``3.0`` for frequency).

        ``bipolar`` makes the value arc grow from 12-o'clock (pan-style); ``None``
        auto-enables it when the range straddles zero (``vmin<0<vmax``). Pass the
        device panel gradient (``bg_hi`` top color, ``bg_lo`` bottom color, both
        ``[r,g,b]``) plus ``device_height``/``inset`` and the knob paints the
        matching gradient SLICE as its own background — no opaque object box where
        the drawing leaves the rect empty (the knob blends into the panel).
        """
        from .engines.ui_kit import custom_knob_js

        initial = vmin if initial is None else initial
        if bipolar is None:
            bipolar = vmin < 0.0 < vmax
        # Per-knob background = the slice of the device panel gradient (bg_hi at the
        # panel top → bg_lo at the bottom) spanning THIS knob's vertical extent, so
        # the v8ui blends seamlessly instead of showing an opaque object box.
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        dial_id = f"{id}_dial"
        # Hidden automatable param: a live.dial NOT in presentation (presentation=0)
        # so it never renders in the device UI, but stays a registered Live
        # parameter (registration is via parameter_enable + saved attrs, not
        # presentation). It lives only in the patching view.
        self.add_dial(  # type: ignore[attr-defined]
            dial_id, param_name, [rect[0], rect[1], 30, 30],
            min_val=vmin, max_val=vmax, initial=initial,
            parameter_exponent=exponent, showname=0, shownumber=0,
            shortname=shortname, presentation=0, unitstyle=unitstyle,
            patching_rect=[40, 600, 30, 30],
        )
        # Custom drawing on top (captures the pointer; transparent bg).
        self.add_v8ui(
            id, rect,
            js_code=custom_knob_js(
                label=(shortname or param_name).upper(), accent=accent,
                vmin=vmin, vmax=vmax, initial=initial, unit=unit, decimals=decimals,
                bg_top=bg_top, bg_bot=bg_bot, bipolar=bipolar,
            ),
            js_filename=js_filename or f"{id}_knob.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["float"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        # Wire: v8ui drag → dial (sets the param); dial value → v8ui (redraws).
        self.add_line(id, 0, dial_id, 0)
        setv_id = f"{id}_setv"
        self.add_newobj(setv_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        # outlet 0 = the value in DISPLAY units (outlet 1 is normalized 0..1).
        self.add_line(dial_id, 0, setv_id, 0)
        self.add_line(setv_id, 0, id, 0)
        return id

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

    def add_custom_toggle(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        label: str = "",
        on_label: str = "ON",
        off_label: str = "OFF",
        accent: str = "0.30, 0.80, 0.84",
        initial: int = 0,
        shortname: str = None,
        js_filename: str = None,
        varname: str = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM hand-drawn pill toggle (v8ui) bound to a HIDDEN automatable
        ``live.toggle``. Click flips it (records automation); automation redraws it.
        Same recipe as :meth:`add_custom_knob`. Returns the v8ui box id."""
        from .engines.ui_kit import custom_toggle_js
        from .parameters import ParameterSpec

        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        tog_id = f"{id}_tog"
        # The hidden param's STORED initial must match the v8ui's initial draw, or
        # the toggle shows ON while the param reads OFF on load. A first-class spec
        # is authoritative for the initial value.
        spec = ParameterSpec.enumerated(
            param_name, (off_label, on_label), shortname=shortname,
            initial=1 if initial else 0, initial_enable=True)
        self.add_toggle(  # type: ignore[attr-defined]
            tog_id, param_name, [rect[0], rect[1], 20, 20], parameter=spec,
            presentation=0, patching_rect=[40, 640, 20, 20],
        )
        self.add_v8ui(
            id, rect,
            js_code=custom_toggle_js(
                label=label, accent=accent,
                initial=initial, bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_toggle.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["int"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        self.add_line(id, 0, tog_id, 0)
        setv_id = f"{id}_setv"
        self.add_newobj(setv_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(tog_id, 0, setv_id, 0)
        self.add_line(setv_id, 0, id, 0)
        return id

    def add_custom_segment(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        options: list,
        accent: str = "0.30, 0.80, 0.84",
        label: str = "",
        initial: int = 0,
        js_filename: str = None,
        varname: str = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM hand-drawn segmented selector / tab bar (v8ui) bound to a
        HIDDEN automatable ``live.tab`` whose enum is ``options``. Clicking a
        segment selects it (records automation); automation redraws the selection.
        Returns the v8ui box id."""
        from .engines.ui_kit import custom_segment_js
        from .parameters import ParameterSpec

        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        tab_id = f"{id}_tab"
        spec = ParameterSpec.enumerated(
            param_name, options, initial=int(initial), initial_enable=True)
        self.add_tab(  # type: ignore[attr-defined]
            tab_id, param_name, [rect[0], rect[1], 40, 18], options=options,
            parameter=spec, presentation=0, patching_rect=[40, 660, 40, 18],
        )
        self.add_v8ui(
            id, rect,
            js_code=custom_segment_js(
                options=options, accent=accent, label=label, initial=initial,
                bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_seg.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["int"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        self.add_line(id, 0, tab_id, 0)
        seti_id = f"{id}_seti"
        self.add_newobj(seti_id, "prepend set_index", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(tab_id, 0, seti_id, 0)
        self.add_line(seti_id, 0, id, 0)
        return id

    def add_mode_glyph_selector(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        glyphs: list,
        option_labels: list = None,
        accent: str = "0.30, 0.80, 0.84",
        label: str = "",
        initial: int = 0,
        js_filename: str = None,
        varname: str = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a compact row of hand-drawn GLYPH buttons (Rupture's mode-glyphs)
        bound to a HIDDEN automatable ``live.tab``. ``glyphs`` are icon names (see
        ``engines.ui_icons.ICON_NAMES``); ``option_labels`` names the enum values
        in Live's automation lane (defaults to the glyph names, upper-cased).
        Returns the v8ui box id."""
        from .engines.ui_kit import custom_glyph_selector_js
        from .parameters import ParameterSpec

        labels = option_labels or [g.upper() for g in glyphs]
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        tab_id = f"{id}_tab"
        spec = ParameterSpec.enumerated(
            param_name, labels, initial=int(initial), initial_enable=True)
        self.add_tab(  # type: ignore[attr-defined]
            tab_id, param_name, [rect[0], rect[1], 40, 18], options=labels,
            parameter=spec, presentation=0, patching_rect=[40, 680, 40, 18],
        )
        self.add_v8ui(
            id, rect,
            js_code=custom_glyph_selector_js(
                glyphs=glyphs, accent=accent, label=label, initial=initial,
                bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_glyphsel.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["int"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        self.add_line(id, 0, tab_id, 0)
        seti_id = f"{id}_seti"
        self.add_newobj(seti_id, "prepend set_index", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(tab_id, 0, seti_id, 0)
        self.add_line(seti_id, 0, id, 0)
        return id

    def add_cycle_button(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        options: list = None,
        glyphs: list = None,
        option_labels: list = None,
        accent: str = "0.30, 0.80, 0.84",
        label: str = "",
        initial: int = 0,
        js_filename: str = None,
        varname: str = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a COMPACT cycle / select button (one cell that steps through options
        on click) bound to a HIDDEN automatable ``live.tab``. Pass ``glyphs`` (icon
        names) for a glyph-cycle or ``options`` (text) for a text-cycle;
        ``option_labels`` names the enum in Live's automation lane. Click = next,
        Shift-click = previous. Returns the v8ui box id."""
        from .engines.ui_kit import custom_cycle_js
        from .parameters import ParameterSpec

        if glyphs is not None:
            enum_labels = option_labels or [g.upper() for g in glyphs]
        else:
            enum_labels = option_labels or list(options or [])
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        tab_id = f"{id}_tab"
        spec = ParameterSpec.enumerated(
            param_name, enum_labels, initial=int(initial), initial_enable=True)
        self.add_tab(  # type: ignore[attr-defined]
            tab_id, param_name, [rect[0], rect[1], 40, 18], options=enum_labels,
            parameter=spec, presentation=0, patching_rect=[40, 700, 40, 18],
        )
        self.add_v8ui(
            id, rect,
            js_code=custom_cycle_js(
                options=options, glyphs=glyphs, accent=accent, label=label,
                initial=initial, bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_cycle.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["int"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        self.add_line(id, 0, tab_id, 0)
        seti_id = f"{id}_seti"
        self.add_newobj(seti_id, "prepend set_index", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(tab_id, 0, seti_id, 0)
        self.add_line(seti_id, 0, id, 0)
        return id

    def add_custom_slider(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        vmin: float = 0.0,
        vmax: float = 100.0,
        initial: float = None,
        unit: str = "",
        decimals: int = 1,
        accent: str = "0.30, 0.80, 0.84",
        orientation: int = 0,
        exponent: float = 1.0,
        shortname: str = None,
        js_filename: str = None,
        varname: str = None,
        unitstyle: int = 1,
        bipolar: bool = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM hand-drawn fader (v8ui) bound to a HIDDEN automatable param.

        The v8ui DRAWS the fader (recessed track + accent fill + handle cap + value
        readout) and handles the pointer with ABSOLUTE positioning (click/drag the
        track and the handle JUMPS to and tracks the cursor — FabFilter behavior;
        Shift = fine, double-click = reset). A 30×30 ``live.dial`` hidden BEHIND it
        (``presentation=0``, never renders) holds the automatable Live parameter:
        drag the drawing → the param moves (and records automation); automate the
        param → the fader redraws. Same recipe as :meth:`add_custom_knob`. Returns
        the v8ui box id.

        ``param_name`` is the automatable Live parameter name; ``accent`` is an
        ``"r, g, b"`` string for the fill/handle indicator; ``exponent`` log-scales
        the param. ``orientation`` 0 = vertical (handle up = max), 1 = horizontal
        (handle right = max).

        ``bipolar`` makes the fill grow from the value=0 detent pixel (gain/pan
        style) with a center tick; ``None`` auto-enables it when the range straddles
        zero (``vmin<0<vmax``). Pass the device panel gradient (``bg_hi`` top,
        ``bg_lo`` bottom, both ``[r,g,b]``) plus ``device_height``/``inset`` and the
        fader paints the matching gradient SLICE as its own background — no opaque
        object box where the drawing leaves the rect empty (it blends into the panel).
        """
        from .engines.ui_kit import custom_slider_js

        initial = vmin if initial is None else initial
        if bipolar is None:
            bipolar = vmin < 0.0 < vmax
        # Per-control background = the slice of the device panel gradient (bg_hi at
        # the panel top → bg_lo at the bottom) spanning THIS control's vertical
        # extent, so the v8ui blends seamlessly instead of showing an opaque box.
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        dial_id = f"{id}_dial"
        # Hidden automatable param: a live.dial NOT in presentation (presentation=0)
        # so it never renders in the device UI, but stays a registered Live
        # parameter. Its STORED initial (min/max/initial) must match the v8ui's
        # initial draw or it loads desynced (same gotcha as the knob). It lives only
        # in the patching view; y=720 keeps it clear of the knob/toggle/tab stack.
        self.add_dial(  # type: ignore[attr-defined]
            dial_id, param_name, [rect[0], rect[1], 30, 30],
            min_val=vmin, max_val=vmax, initial=initial,
            parameter_exponent=exponent, showname=0, shownumber=0,
            shortname=shortname, presentation=0, unitstyle=unitstyle,
            patching_rect=[40, 720, 30, 30],
        )
        # Custom drawing on top (captures the pointer; transparent v8ui bg, but it
        # self-paints the gradient slice so there's no black object box).
        self.add_v8ui(
            id, rect,
            js_code=custom_slider_js(
                label=(shortname or param_name).upper(), accent=accent,
                vmin=vmin, vmax=vmax, initial=initial, unit=unit, decimals=decimals,
                orientation=orientation, bg_top=bg_top, bg_bot=bg_bot, bipolar=bipolar,
            ),
            js_filename=js_filename or f"{id}_slider.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["float"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        # Wire: v8ui drag → dial (sets the param, records automation); dial value →
        # v8ui (redraws). Use dial outlet 0 (DISPLAY units), not outlet 1 (normalized).
        self.add_line(id, 0, dial_id, 0)
        setv_id = f"{id}_setv"
        self.add_newobj(setv_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(dial_id, 0, setv_id, 0)
        self.add_line(setv_id, 0, id, 0)
        return id

    def add_custom_stepper(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        vmin: float = 0.0,
        vmax: float = 100.0,
        initial: float = None,
        step: float = 1.0,
        fine_step: float = None,
        unit: str = "",
        decimals: int = 0,
        label: str = "",
        accent: str = "0.30, 0.80, 0.84",
        scrub: bool = True,
        shortname: str = None,
        js_filename: str = None,
        varname: str = None,
        unitstyle: int = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM hand-drawn +/- numeric stepper (v8ui) bound to a HIDDEN
        automatable ``live.dial``. Click ``-`` / ``+`` to step by ``step`` (Shift =
        ``fine_step``), drag the value field vertically to scrub, double-click
        resets to ``initial``. Same hidden-param recipe and seamless panel-slice
        background as :meth:`add_custom_knob`. The right control for discrete /
        integer params (octave, voices, semitones, taps) and for fine numeric
        entry where a knob is imprecise. Keep ``rect`` ≥48px wide so two buttons +
        a readable number fit. Returns the v8ui box id.

        For INTEGER params pass ``decimals=0`` (``unitstyle`` then defaults to 2 =
        Live's "Int" readout); for floats keep ``decimals>=1`` (``unitstyle``
        defaults to 1 = Live's "Float"). ``fine_step`` defaults to ``step`` for
        ints and ``step/10`` for floats. Pass the device panel gradient
        (``bg_hi``/``bg_lo`` ``[r,g,b]`` + ``device_height``/``inset``) — e.g. via
        ``**theme.knob_bg_args(device_height)`` — and the stepper paints the
        matching gradient SLICE as its own background (no opaque object box).
        """
        from .engines.ui_kit import custom_stepper_js

        initial = vmin if initial is None else initial
        if unitstyle is None:
            unitstyle = 2 if int(decimals) == 0 else 1
        # Per-control background = the slice of the device panel gradient spanning
        # THIS control's vertical extent, so the v8ui blends seamlessly instead of
        # showing an opaque object box.
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        dial_id = f"{id}_dial"
        # Hidden automatable param: a live.dial NOT in presentation (presentation=0)
        # so it never renders in the device UI, but stays a registered Live
        # parameter. A stepped numeric range is continuous-with-step, so live.dial
        # (not live.tab) is correct; the v8ui owns the step grid.
        self.add_dial(  # type: ignore[attr-defined]
            dial_id, param_name, [rect[0], rect[1], 30, 30],
            min_val=vmin, max_val=vmax, initial=initial,
            showname=0, shownumber=0, shortname=shortname,
            presentation=0, unitstyle=unitstyle,
            patching_rect=[40, 720, 30, 30],
        )
        # Custom drawing on top (captures the pointer; transparent bg).
        self.add_v8ui(
            id, rect,
            js_code=custom_stepper_js(
                label=label, accent=accent,
                vmin=vmin, vmax=vmax, initial=initial, step=step,
                fine_step=fine_step, unit=unit, decimals=decimals, scrub=scrub,
                bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_stepper.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["float"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        # Wire: v8ui step/scrub → dial (sets the param + records automation);
        # dial value → v8ui (redraws). outlet 0 = DISPLAY units (outlet 1 = norm).
        self.add_line(id, 0, dial_id, 0)
        setv_id = f"{id}_setv"
        self.add_newobj(setv_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(dial_id, 0, setv_id, 0)
        self.add_line(setv_id, 0, id, 0)
        return id

    def add_draggable_readout(
        self,
        id: str,
        param_name: str,
        rect: list,
        *,
        vmin: float = 0.0,
        vmax: float = 100.0,
        initial: float = None,
        unit: str = "",
        decimals: int = 1,
        accent: str = "0.30, 0.80, 0.84",
        exponent: float = 1.0,
        shortname: str = None,
        label: str = None,
        show_bar: bool = True,
        align: str = "right",
        js_filename: str = None,
        varname: str = None,
        unitstyle: int = 1,
        bipolar: bool = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM draggable numeric readout (v8ui) bound to a HIDDEN
        automatable ``live.dial`` — the premium alternative to a visible
        ``live.numbox``.

        The v8ui DRAWS a flat value cell (framed track + small top-left label + a
        big bright value + an optional accent position bar) and handles the
        vertical pointer drag (Shift = fine, double-click = reset to ``initial``);
        a 1×1 ``live.dial`` hidden BEHIND it (``presentation=0``) holds the
        automatable Live parameter. Drag the drawing → the param moves (and records
        automation); automate the param → the readout redraws. Same v8ui⇄hidden-dial
        recipe as :meth:`add_custom_knob`. Returns the v8ui box id.

        ``param_name`` is the automatable Live parameter name; ``accent`` is an
        ``"r, g, b"`` string for the fill bar; ``exponent`` log-scales the param
        (keep ``1.0`` for linear dB/ms/%/semitone readouts — the v8ui drags in
        LINEAR param units, so a non-unit exponent makes the drag feel and the
        dial's stored value diverge). ``unitstyle`` defaults to FLOAT so Live's own
        readout shows the raw number (not a bogus ``'%'``).

        ``bipolar`` draws the fill bar from center (pan-style); ``None`` auto-enables
        it when the range straddles zero (``vmin<0<vmax``). Pass the device panel
        gradient (``bg_hi`` top color, ``bg_lo`` bottom color, both ``[r,g,b]``) plus
        ``device_height``/``inset`` and the readout paints the matching gradient
        SLICE as its own background — no opaque object box (it blends into the panel).
        """
        from .engines.ui_kit import custom_readout_js

        initial = vmin if initial is None else initial
        if bipolar is None:
            bipolar = vmin < 0.0 < vmax
        # Per-control background = the slice of the device panel gradient spanning
        # THIS control's vertical extent, so the v8ui blends seamlessly instead of
        # showing an opaque object box.
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        dial_id = f"{id}_dial"
        # Hidden automatable param: a live.dial NOT in presentation (presentation=0)
        # so it never renders in the device UI, but stays a registered, automatable
        # Live parameter. It lives only in the patching view.
        self.add_dial(  # type: ignore[attr-defined]
            dial_id, param_name, [rect[0], rect[1], 30, 30],
            min_val=vmin, max_val=vmax, initial=initial,
            parameter_exponent=exponent, showname=0, shownumber=0,
            shortname=shortname, presentation=0, unitstyle=unitstyle,
            patching_rect=[40, 720, 30, 30],
        )
        # Custom drawing on top (captures the pointer; transparent box bg, the v8ui
        # self-paints the panel-gradient slice).
        self.add_v8ui(
            id, rect,
            js_code=custom_readout_js(
                label=(label or shortname or param_name).upper(), accent=accent,
                vmin=vmin, vmax=vmax, initial=initial, unit=unit, decimals=decimals,
                bg_top=bg_top, bg_bot=bg_bot, bipolar=bipolar,
                show_bar=show_bar, align=align,
            ),
            js_filename=js_filename or f"{id}_readout.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=["float"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        # Wire: v8ui drag → dial (sets the param); dial value → v8ui (redraws).
        self.add_line(id, 0, dial_id, 0)
        setv_id = f"{id}_setv"
        self.add_newobj(setv_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        # outlet 0 = the value in DISPLAY units (outlet 1 is normalized 0..1).
        self.add_line(dial_id, 0, setv_id, 0)
        self.add_line(setv_id, 0, id, 0)
        return id

    def add_drag_curve_node(
        self,
        id: str,
        param_x: str,
        param_y: str,
        rect: list,
        *,
        vmin_x: float = 20.0,
        vmax_x: float = 20000.0,
        initial_x: float = None,
        unit_x: str = "Hz",
        decimals_x: int = 0,
        exponent_x: float = 3.0,
        unitstyle_x: int = 3,        # constants.UNITSTYLE_HZ
        vmin_y: float = -15.0,
        vmax_y: float = 15.0,
        initial_y: float = None,
        unit_y: str = "dB",
        decimals_y: int = 1,
        exponent_y: float = 1.0,
        unitstyle_y: int = 4,        # constants.UNITSTYLE_DB
        label_x: str = None,
        label_y: str = None,
        accent: str = "0.30, 0.80, 0.84",
        draw_curve: bool = True,
        shortname_x: str = None,
        shortname_y: str = None,
        js_filename: str = None,
        varname: str = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM draggable curve node (v8ui) bound to TWO HIDDEN automatable
        params (FabFilter Pro-Q band / compressor threshold-ratio dot / filter
        freq-reso node). The v8ui DRAWS a graph + node and handles the pointer:
        horizontal drag drives ``param_x``, vertical drag drives ``param_y`` (Shift =
        fine, Cmd = lock to horizontal, Opt = lock to vertical, double-click resets
        BOTH axes). It is :meth:`add_custom_knob` doubled onto two axes — TWO 1×1
        ``live.dial`` params hidden BEHIND it (``presentation=0``) hold the
        automatable Live parameters; drag the drawing → the params move (and record
        automation); automate either param → only that axis of the node redraws.
        Returns the v8ui box id.

        ``param_x``/``param_y`` are the automatable Live parameter names; ``accent``
        is an ``"r, g, b"`` string for the node/curve. ``exponent_x``/``exponent_y``
        log-scale an axis (e.g. ``3.0`` for frequency) — the SAME exponent is threaded
        into both the hidden dial and the v8ui so the drawn node matches Live's
        readout. ``unitstyle_x``/``unitstyle_y`` (``constants.UNITSTYLE_*``) make
        Live read the right unit (Hz/dB) not a bogus '%'. ``draw_curve`` draws a
        symmetric bell through the node (EQ-band look); ``False`` draws a bare
        crosshair (XY-pad look).

        Pass the device panel gradient (``bg_hi`` top color, ``bg_lo`` bottom color,
        both ``[r,g,b]``) plus ``device_height``/``inset`` and the node paints the
        matching gradient SLICE as its own background — no opaque object box where the
        drawing leaves the rect empty (the node blends into the panel).
        """
        from .engines.ui_curve_node import drag_curve_node_js

        initial_x = vmin_x if initial_x is None else initial_x
        initial_y = vmin_y if initial_y is None else initial_y
        # Per-control background = the slice of the device panel gradient (bg_hi at the
        # panel top → bg_lo at the bottom) spanning THIS control's vertical extent, so
        # the v8ui blends seamlessly instead of showing an opaque object box.
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        dialx_id = f"{id}_dialx"
        dialy_id = f"{id}_dialy"
        # Hidden automatable params: two live.dials NOT in presentation (presentation=0)
        # so they never render in the device UI, but stay registered Live parameters.
        # The SAME exponent/unitstyle as the v8ui's axis keeps the drawn node aligned
        # with Live's readout. outlet 0 = display-units value (outlet 1 is normalized).
        self.add_dial(  # type: ignore[attr-defined]
            dialx_id, param_x, [rect[0], rect[1], 30, 30],
            min_val=vmin_x, max_val=vmax_x, initial=initial_x,
            parameter_exponent=exponent_x, showname=0, shownumber=0,
            shortname=shortname_x, presentation=0, unitstyle=unitstyle_x,
            patching_rect=[40, 600, 30, 30],
        )
        self.add_dial(  # type: ignore[attr-defined]
            dialy_id, param_y, [rect[0], rect[1], 30, 30],
            min_val=vmin_y, max_val=vmax_y, initial=initial_y,
            parameter_exponent=exponent_y, showname=0, shownumber=0,
            shortname=shortname_y, presentation=0, unitstyle=unitstyle_y,
            patching_rect=[80, 600, 30, 30],
        )
        # Custom drawing on top (captures the pointer; transparent bg, no object box).
        # FIRST kit control with 2 outlets / 2 hidden params: outlettype must be
        # ["float", "float"] and the two patch lines below must be index-exact.
        self.add_v8ui(
            id, rect,
            js_code=drag_curve_node_js(
                label_x=(label_x or shortname_x or param_x).upper(),
                vmin_x=vmin_x, vmax_x=vmax_x, initial_x=initial_x,
                unit_x=unit_x, decimals_x=decimals_x, exponent_x=exponent_x,
                label_y=(label_y or shortname_y or param_y).upper(),
                vmin_y=vmin_y, vmax_y=vmax_y, initial_y=initial_y,
                unit_y=unit_y, decimals_y=decimals_y, exponent_y=exponent_y,
                accent=accent, draw_curve=draw_curve, bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_curvenode.js", content_address=True,
            numinlets=1, numoutlets=2, outlettype=["float", "float"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        # Wire: v8ui drag → dials (sets the params); dial values → v8ui (redraws).
        # outlet 0 of v8ui = X value → dialx; outlet 1 = Y value → dialy.
        self.add_line(id, 0, dialx_id, 0)
        self.add_line(id, 1, dialy_id, 0)
        # dial X value (display units) → "prepend set_value_x" → v8ui inlet 0.
        setvx_id = f"{id}_setvx"
        self.add_newobj(setvx_id, "prepend set_value_x", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 120, 20])
        self.add_line(dialx_id, 0, setvx_id, 0)
        self.add_line(setvx_id, 0, id, 0)
        # dial Y value (display units) → "prepend set_value_y" → v8ui inlet 0.
        setvy_id = f"{id}_setvy"
        self.add_newobj(setvy_id, "prepend set_value_y", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 224, 120, 20])
        self.add_line(dialy_id, 0, setvy_id, 0)
        self.add_line(setvy_id, 0, id, 0)
        return id

    def add_xy_pad(
        self,
        id: str,
        param_x: str,
        param_y: str,
        rect: list,
        *,
        vminx: float = 0.0,
        vmaxx: float = 1.0,
        initialx: float = None,
        vminy: float = 0.0,
        vmaxy: float = 1.0,
        initialy: float = None,
        unitx: str = "",
        unity: str = "",
        decimals: int = 2,
        label_x: str = None,
        label_y: str = None,
        accent: str = "0.30, 0.80, 0.84",
        accent2: str = None,
        exponent_x: float = 1.0,
        exponent_y: float = 1.0,
        unitstyle: int = 1,
        bipolar_x: bool = None,
        bipolar_y: bool = None,
        short_x: str = None,
        short_y: str = None,
        show_readout: bool = True,
        js_filename: str = None,
        varname: str = None,
        bg_hi: list = None,
        bg_lo: list = None,
        device_height: float = None,
        inset: float = 4.0,
    ) -> str:
        """Add a PREMIUM hand-drawn 2D XY pad (v8ui) bound to TWO HIDDEN automatable
        ``live.dial`` params (X + Y). The v8ui DRAWS the pad (recessed plot well +
        grid + crosshair + glowing puck + value readouts) and owns the pointer
        (click = jump-to-cursor, Shift-drag = fine, double-click = reset both); two
        1x1 ``live.dial`` objects hidden BEHIND it (presentation=0) hold the
        automatable Live params. Drag the puck -> BOTH params move and record
        automation; automate either -> the puck redraws. This is
        :meth:`add_custom_knob` DOUBLED. Returns the v8ui box id.

        ``param_x``/``param_y`` are the automatable Live parameter names;
        ``accent`` is the X-axis / puck accent ``"r, g, b"`` string and ``accent2``
        tints the Y crosshair (defaults to ``accent``). The Y axis is screen-
        INVERTED (top of the pad = max Y). ``bipolar_x``/``bipolar_y`` (``None`` =
        auto when the range straddles zero) draw a centered origin crosshair for
        pan-style axes. Pass the device panel gradient (``bg_hi``/``bg_lo`` each
        ``[r,g,b]``) plus ``device_height``/``inset`` and the pad paints the
        matching gradient SLICE as its own background -- no opaque object box (use
        ``Theme.knob_bg_args(device_height)`` to supply them).
        """
        from .engines.ui_xy_pad import custom_xy_pad_js
        from .parameters import ParameterSpec  # noqa: F401  (kept parallel to siblings)

        initialx = vminx if initialx is None else initialx
        initialy = vminy if initialy is None else initialy
        if bipolar_x is None:
            bipolar_x = vminx < 0.0 < vmaxx
        if bipolar_y is None:
            bipolar_y = vminy < 0.0 < vmaxy
        accent2 = accent if accent2 is None else accent2
        # Per-pad background = the slice of the device panel gradient spanning THIS
        # pad's vertical extent, so the v8ui blends seamlessly (no opaque box).
        bg_top, bg_bot = self._panel_slice(rect, bg_hi, bg_lo, device_height, inset)
        # --- Hidden automatable params: two live.dials NOT in presentation
        # (presentation=0) so they never render, but stay registered Live params.
        dialx_id = f"{id}_dialx"
        dialy_id = f"{id}_dialy"
        self.add_dial(  # type: ignore[attr-defined]
            dialx_id, param_x, [rect[0], rect[1], 30, 30],
            min_val=vminx, max_val=vmaxx, initial=initialx,
            parameter_exponent=exponent_x, showname=0, shownumber=0,
            shortname=short_x, presentation=0, unitstyle=unitstyle,
            patching_rect=[40, 600, 30, 30],
        )
        self.add_dial(  # type: ignore[attr-defined]
            dialy_id, param_y, [rect[0], rect[1], 30, 30],
            min_val=vminy, max_val=vmaxy, initial=initialy,
            parameter_exponent=exponent_y, showname=0, shownumber=0,
            shortname=short_y, presentation=0, unitstyle=unitstyle,
            patching_rect=[40, 640, 30, 30],
        )
        # --- Custom drawing on top: 2 inlets (X/Y feedback) / 2 outlets (X/Y).
        self.add_v8ui(
            id, rect,
            js_code=custom_xy_pad_js(
                label_x=(label_x or short_x or param_x).upper(),
                label_y=(label_y or short_y or param_y).upper(),
                accent=accent, accent2=accent2,
                vminx=vminx, vmaxx=vmaxx, initialx=initialx,
                vminy=vminy, vmaxy=vmaxy, initialy=initialy,
                unitx=unitx, unity=unity, decimals=decimals,
                bipolar_x=bipolar_x, bipolar_y=bipolar_y,
                show_readout=show_readout, bg_top=bg_top, bg_bot=bg_bot,
            ),
            js_filename=js_filename or f"{id}_xypad.js", content_address=True,
            numinlets=2, numoutlets=2, outlettype=["float", "float"],
            background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        # --- SET path: v8ui outlet 0 -> X dial, outlet 1 -> Y dial
        # (user drag records BOTH automation lanes).
        self.add_line(id, 0, dialx_id, 0)
        self.add_line(id, 1, dialy_id, 0)
        # --- DRAW path X: dialx outlet 0 (display units) -> set_value -> v8ui inlet 0.
        setvx_id = f"{id}_setvx"
        self.add_newobj(setvx_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 200, 110, 20])
        self.add_line(dialx_id, 0, setvx_id, 0)
        self.add_line(setvx_id, 0, id, 0)
        # --- DRAW path Y: dialy outlet 0 -> set_value -> v8ui inlet 1 (separate box
        # so X never bleeds into the Y feedback inlet).
        setvy_id = f"{id}_setvy"
        self.add_newobj(setvy_id, "prepend set_value", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[rect[0], rect[1] + 240, 110, 20])
        self.add_line(dialy_id, 0, setvy_id, 0)
        self.add_line(setvy_id, 0, id, 1)
        return id

    def add_envelope_editor(
        self,
        id: str,
        rect: list,
        *,
        params: tuple = ("Attack", "Decay", "Sustain", "Release"),
        shortnames: tuple = None,
        max_attack_ms: float = 2000.0,
        max_decay_ms: float = 4000.0,
        max_release_ms: float = 8000.0,
        initial: tuple = (10.0, 200.0, 0.7, 400.0),
        unitstyles: tuple = None,
        accent: str = "0.36, 0.92, 0.96, 1.0",
        bg: str = "0.05, 0.05, 0.06, 1.0",
        sustain_frac: float = 0.16,
        js_filename: str = None,
        varname: str = None,
    ) -> str:
        """Add a DRAGGABLE ADSR envelope editor (jsui) bound to FOUR HIDDEN
        automatable ``live.dial`` params (dnksaus-catalog kit engine #1 — the
        Auto Gate / dnkFM envelope-editor look).

        The jsui DRAWS the envelope (accent polyline + under-curve fill + dim
        grid + square nodes + an A/D/S/R value row) and owns the pointer via
        the proven jsui ``onclick``/``ondrag`` idiom: dragging a node emits
        ONLY that node's value(s) — attack peak → attack ms, decay knee →
        decay ms + sustain, plateau → sustain, release end → release ms. Four
        1×1 ``live.dial`` objects hidden BEHIND it (``presentation=0``, the
        :meth:`add_custom_knob` recipe ×4) hold the automatable Live params.
        Drag a node → its param moves (and records automation); automate a
        param → the curve redraws WITHOUT re-emitting (no echo). This is
        :meth:`add_custom_knob` QUADRUPLED onto one graph. Returns the jsui
        box id; the dials are ``f"{id}_dial0"``..``f"{id}_dial3"``.

        ``params`` are the four Live parameter longnames (attack, decay,
        sustain, release — in that order); ``shortnames``/``unitstyles``
        follow the same order (unitstyles default to TIME/TIME/FLOAT/TIME so
        Live reads ms/ms/float/ms). Ranges: attack ``0..max_attack_ms``,
        decay ``0..max_decay_ms``, sustain ``0..1``, release
        ``0..max_release_ms``. ``initial`` seeds BOTH the params and the
        first paint so the curve is honest on load. ``accent``/``bg`` are
        RGBA strings; ``sustain_frac`` is the fixed plateau fraction.
        """
        from .constants import UNITSTYLE_FLOAT, UNITSTYLE_TIME
        from .engines.envelope_editor import envelope_editor_js

        if len(params) != 4:
            raise ValueError("params must name exactly (attack, decay, sustain, release)")
        if len(initial) != 4:
            raise ValueError("initial must be (attack_ms, decay_ms, sustain, release_ms)")
        if unitstyles is None:
            unitstyles = (UNITSTYLE_TIME, UNITSTYLE_TIME, UNITSTYLE_FLOAT, UNITSTYLE_TIME)
        if shortnames is None:
            shortnames = (None, None, None, None)
        maxes = (max_attack_ms, max_decay_ms, 1.0, max_release_ms)

        # --- FOUR hidden automatable params: live.dials NOT in presentation
        # (presentation=0) so they never render in the device UI, but stay
        # registered Live parameters. outlet 0 = the value in DISPLAY units.
        dial_ids = []
        for i in range(4):
            dial_id = f"{id}_dial{i}"
            self.add_dial(  # type: ignore[attr-defined]
                dial_id, params[i], [rect[0], rect[1], 30, 30],
                min_val=0.0, max_val=maxes[i], initial=initial[i],
                showname=0, shownumber=0, shortname=shortnames[i],
                presentation=0, unitstyle=unitstyles[i],
                patching_rect=[40 + 44 * i, 600, 30, 30],
            )
            dial_ids.append(dial_id)

        # --- the draggable graph (jsui: ES5 engine, validated on add).
        self.add_jsui(
            id, rect,
            js_code=envelope_editor_js(
                accent=accent, bg=bg,
                max_attack_ms=max_attack_ms, max_decay_ms=max_decay_ms,
                max_release_ms=max_release_ms,
                init_attack_ms=initial[0], init_decay_ms=initial[1],
                init_sustain=initial[2], init_release_ms=initial[3],
                sustain_frac=sustain_frac,
            ),
            js_filename=js_filename or f"{id}_envedit.js", content_address=True,
            numinlets=4, numoutlets=4,
            outlettype=["float", "float", "float", "float"],
            varname=varname or id,
        )
        # --- 8 wires. Drag path: jsui outlet i -> dial i (records automation).
        # Draw path: dial i outlet 0 (display units) -> jsui inlet i (msg_float
        # dispatches on the inlet index and never re-emits, so no echo loop).
        for i, dial_id in enumerate(dial_ids):
            self.add_line(id, i, dial_id, 0)
            self.add_line(dial_id, 0, id, i)
        return id

    def add_curve_editor(
        self,
        id: str,
        rect: list,
        *,
        state_param: str = "Curve",
        max_points: int = 16,
        init_points: tuple = ((0.0, 0.0), (1.0, 1.0)),
        init_tension: float = 0.0,
        init_grid: int = 4,
        init_snap: int = 0,
        accent: str = "0.36, 0.92, 0.96, 1.0",
        bg: str = "0.05, 0.05, 0.06, 1.0",
        stored_only: bool = True,
        js_filename: str = None,
        varname: str = None,
    ) -> str:
        """Add a GENERAL BREAKPOINT CURVE EDITOR (jsui) whose points/tension/
        grid/snap persist through hidden ``live.dial`` parameter hosts
        (dnksaus-catalog kit engines #2-#6 — the Multi Shaper core widget).

        The jsui owns the pointer (click empty = add point, drag = move with
        neighbor-clamped x, double-click = delete, endpoints undeletable) and
        emits the full ``points x0 y0 ...`` list (normalized 0..1) on ANY
        edit — that list is the persistence payload. Tension (0..100 cosine
        blend), grid divisions, and snap arrive as ``set_*`` messages from
        their own hidden automatable params. See
        :mod:`m4l_builder.engines.curve_editor` for the full engine contract.

        **Persistence choice (investigated, honest):** a parameter-enabled
        ``pattr`` blob is the OBVIOUS store and it is a PROVEN TRAP — it
        accepts the blob but never re-delivers it across track duplication in
        Live 12.4 (kit pitfalls file, headless-counter proven). The kit's
        duplication-safe pattern is per-value hidden ``live.*`` parameter
        hosts (Parametric EQ precedent), which is ALSO exactly how dnksaus
        ships editor state (their devices carry dozens of
        ``parameter_invisible: 1`` stored-only scalar params and rebuild the
        curve display from them at load — never a blob). So: ``1 + 2*max_points``
        hidden ``live.dial`` hosts (``{id}_count`` + ``{id}_p{k}x/y``, longnames
        ``"{state_param} Points"`` / ``"{state_param} P{k} X"``…). With
        ``stored_only=True`` (default) they are marked Stored-Only
        (``parameter_invisible=1``): saved with the set and restored on
        load/duplication, but hidden from Live's automation chooser and undo
        history. Pass ``stored_only=False`` to make every point coordinate a
        normal automatable param (the exact Parametric-EQ-proven visibility)
        if live QA ever faults stored-only restore.

        **Save path:** jsui ``points`` list -> ``route points`` ->
        ``t l l`` -> (right, fires first) ``listfunnel`` -> ``spray`` fanning
        each coordinate into its dial; (left, fires last) ``zl len -> / 2`` ->
        the count dial. **Restore path:** Live restores/initializes each param
        -> the dial outputs -> a ``pak`` (creation args = the initial state, so
        params that never fire still contribute correct defaults) -> ``prepend
        set_all`` -> the jsui, which rebuilds the breakpoints without
        re-emitting; the engine ignores ``set_all`` mid-drag so the echo of our
        own edits can never fight a live gesture, and the cascade's final fire
        always carries the complete state regardless of restore order.

        ``init_points`` are normalized ``(x, y)`` pairs — 2..max_points of
        them, first x MUST be 0.0 and last x MUST be 1.0 (the undeletable
        endpoints). They seed the param initials AND the pak defaults; the
        engine's first paint shows the two endpoints until the params fire
        (immediately, at load). Tension/Grid/Snap params stay normal
        automatable params (they are musical controls, not state slots).
        Returns the jsui box id; the hosts are ``f"{id}_count"``,
        ``f"{id}_p{{k}}x"``/``f"{id}_p{{k}}y"`` (k = 1..max_points),
        ``f"{id}_tension"``, ``f"{id}_grid"``, ``f"{id}_snap"``.
        """
        from .constants import UNITSTYLE_FLOAT, UNITSTYLE_INT, UNITSTYLE_PERCENT
        from .engines.curve_editor import curve_editor_js
        from .parameters import PARAM_VIS_STORED_ONLY

        max_points = int(max_points)
        if not 2 <= max_points <= 32:
            raise ValueError(f"max_points must be 2..32, got {max_points}")
        points = [(float(x), float(y)) for x, y in init_points]
        if not 2 <= len(points) <= max_points:
            raise ValueError(
                f"init_points needs 2..{max_points} points, got {len(points)}"
            )
        if points[0][0] != 0.0 or points[-1][0] != 1.0:
            raise ValueError("init_points must start at x=0.0 and end at x=1.0")
        if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in points):
            raise ValueError("init_points coordinates must be normalized 0..1")

        vis = PARAM_VIS_STORED_ONLY if stored_only else None

        # --- the editor jsui (ES5 engine, validated on add): 1 inlet / 1 outlet.
        self.add_jsui(
            id, rect,
            js_code=curve_editor_js(
                accent=accent, bg=bg, max_points=max_points,
                init_y0=points[0][1], init_y1=points[-1][1],
                init_tension=init_tension, init_grid=init_grid,
                init_snap=init_snap,
            ),
            js_filename=js_filename or f"{id}_curveedit.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=[""],
            varname=varname or id,
        )

        # --- hidden STATE hosts: count + per-point X/Y (presentation=0 keeps
        # them off the face; stored-only keeps them out of the automation UI).
        count_id = f"{id}_count"
        self.add_dial(  # type: ignore[attr-defined]
            count_id, f"{state_param} Points", [rect[0], rect[1], 30, 30],
            min_val=2.0, max_val=float(max_points), initial=float(len(points)),
            showname=0, shownumber=0, presentation=0,
            unitstyle=UNITSTYLE_INT, steps=max_points - 1, invisible=vis,
            patching_rect=[40, 560, 30, 30],
        )
        coord_ids = []
        for k in range(1, max_points + 1):
            px, py = points[k - 1] if k <= len(points) else (0.0, 0.0)
            for axis, val in (("x", px), ("y", py)):
                coord_id = f"{id}_p{k}{axis}"
                self.add_dial(  # type: ignore[attr-defined]
                    coord_id, f"{state_param} P{k} {axis.upper()}",
                    [rect[0], rect[1], 30, 30],
                    min_val=0.0, max_val=1.0, initial=val,
                    showname=0, shownumber=0, presentation=0,
                    unitstyle=UNITSTYLE_FLOAT, invisible=vis,
                    patching_rect=[40 + 34 * ((k - 1) % 16),
                                   640 + (36 if axis == "y" else 0)
                                   + 90 * ((k - 1) // 16), 30, 30],
                )
                coord_ids.append(coord_id)

        # --- automatable CONTROL params: tension / grid / snap.
        control_specs = (
            (f"{id}_tension", f"{state_param} Tension", 0.0, 100.0,
             float(init_tension), UNITSTYLE_PERCENT, None, "set_tension"),
            (f"{id}_grid", f"{state_param} Grid", 1.0, 32.0,
             float(init_grid), UNITSTYLE_INT, 32, "set_grid"),
            (f"{id}_snap", f"{state_param} Snap", 0.0, 1.0,
             float(bool(init_snap)), UNITSTYLE_INT, 2, "set_snap"),
        )
        for i, (cid, longname, vmin, vmax, vinit, ustyle, steps, msg) in enumerate(
                control_specs):
            self.add_dial(  # type: ignore[attr-defined]
                cid, longname, [rect[0], rect[1], 30, 30],
                min_val=vmin, max_val=vmax, initial=vinit,
                showname=0, shownumber=0, presentation=0,
                unitstyle=ustyle, steps=steps,
                patching_rect=[640 + 44 * i, 560, 30, 30],
            )
            prep_id = f"{cid}_prep"
            self.add_newobj(prep_id, f"prepend {msg}", numinlets=1, numoutlets=1,
                            outlettype=[""],
                            patching_rect=[640 + 44 * i, 600, 120, 20])
            self.add_line(cid, 0, prep_id, 0)
            self.add_line(prep_id, 0, id, 0)

        # --- SAVE path: points list -> per-coordinate dials + the count dial.
        # `t l l` fires right-to-left, so the coordinates land FIRST and the
        # count LAST — every intermediate pak fire is masked by a count that
        # only grows/shrinks once the coords are already consistent.
        route_id = f"{id}_route"
        self.add_newobj(route_id, "route points", numinlets=2, numoutlets=2,
                        outlettype=["", ""], patching_rect=[40, 460, 90, 20])
        split_id = f"{id}_split"
        self.add_newobj(split_id, "t l l", numinlets=1, numoutlets=2,
                        outlettype=["", ""], patching_rect=[40, 490, 50, 20])
        len_id = f"{id}_len"
        self.add_newobj(len_id, "zl len", numinlets=2, numoutlets=2,
                        outlettype=["", ""], patching_rect=[40, 520, 50, 20])
        half_id = f"{id}_half"
        self.add_newobj(half_id, "/ 2", numinlets=2, numoutlets=1,
                        outlettype=["int"], patching_rect=[100, 520, 32, 20])
        funnel_id = f"{id}_funnel"
        # listfunnel emits "index value" pairs (base 0, matching spray's default
        # offset); outlettype ["list"] is the corpus-measured declaration
        # (Roulette ships `listfunnel 1` + `spray 12` with exactly this shape).
        self.add_newobj(funnel_id, "listfunnel", numinlets=1, numoutlets=1,
                        outlettype=["list"], patching_rect=[160, 520, 70, 20])
        spray_id = f"{id}_spray"
        self.add_newobj(spray_id, f"spray {2 * max_points}", numinlets=1,
                        numoutlets=2 * max_points,
                        outlettype=[""] * (2 * max_points),
                        patching_rect=[40, 600, 550, 20])
        self.add_line(id, 0, route_id, 0)
        self.add_line(route_id, 0, split_id, 0)
        self.add_line(split_id, 1, funnel_id, 0)
        self.add_line(split_id, 0, len_id, 0)
        self.add_line(len_id, 0, half_id, 0)
        self.add_line(half_id, 0, count_id, 0)
        self.add_line(funnel_id, 0, spray_id, 0)
        for j, coord_id in enumerate(coord_ids):
            self.add_line(spray_id, j, coord_id, 0)

        # --- RESTORE path: every host output re-fires the pak; its creation
        # args ARE the initial state, so silent params still contribute.
        pak_args = [str(len(points))]
        for k in range(1, max_points + 1):
            px, py = points[k - 1] if k <= len(points) else (0.0, 0.0)
            pak_args.append(repr(px))
            pak_args.append(repr(py))
        pak_id = f"{id}_pak"
        self.add_newobj(pak_id, "pak " + " ".join(pak_args),
                        numinlets=1 + 2 * max_points, numoutlets=1,
                        outlettype=[""], patching_rect=[40, 740, 550, 20])
        setall_id = f"{id}_setall"
        self.add_newobj(setall_id, "prepend set_all", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[40, 770, 110, 20])
        self.add_line(count_id, 0, pak_id, 0)
        for j, coord_id in enumerate(coord_ids):
            self.add_line(coord_id, 0, pak_id, j + 1)
        self.add_line(pak_id, 0, setall_id, 0)
        self.add_line(setall_id, 0, id, 0)
        return id

    def add_step_bars(
        self,
        id: str,
        rect: list,
        *,
        state_param: str = "Steps",
        max_steps: int = 16,
        init_steps: int = 8,
        init_values: tuple = None,
        init_value: float = 1.0,
        reset_value: float = 0.0,
        init_link: int = 0,
        steps_rect: list = None,
        link_rect: list = None,
        link_labels: tuple = ("Off", "Link"),
        accent: str = "0.36, 0.92, 0.96, 1.0",
        bg: str = "0.05, 0.05, 0.06, 1.0",
        stored_only: bool = True,
        js_filename: str = None,
        varname: str = None,
    ) -> str:
        """Add a STEP-BAR LANE EDITOR (jsui) whose bar values persist through
        hidden ``live.dial`` parameter hosts (dnksaus-catalog kit engines
        #7-#8 — the Auto Gate / Trig Rnd step lane + value-link chip).

        The jsui owns the pointer (click sets the bar under the cursor,
        drag PAINTS values across every bar the pointer crosses, Cmd/Alt-click
        resets a bar to ``reset_value``) and emits ``values v0 v1 ...``
        (normalized 0..1, active steps only) on ANY edit — that list is the
        persistence payload — plus a ``step i v`` per-bar stream for cheap
        real-time consumers. See :mod:`m4l_builder.engines.step_bars` for the
        full engine contract.

        **Persistence:** the exact :meth:`add_curve_editor` recipe (per-value
        hidden ``live.*`` parameter hosts, NOT a pattr blob — the proven
        duplication trap): ``1 + max_steps`` hidden ``live.dial`` hosts
        (``{id}_steps`` count + ``{id}_s{k}`` values, longnames
        ``"{state_param} N"`` / ``"{state_param} S{k}"``), Stored-Only by
        default (``stored_only=False`` makes every slot automatable). Save
        path: jsui ``values`` list -> ``route values`` -> ``t l l`` ->
        (right, fires first) ``listfunnel`` -> ``spray`` into the value dials;
        (left, fires last) ``zl len`` -> the count dial (one atom per step, so
        the length IS the count). Restore path: hosts -> ``pak`` (creation
        args = the initials, so silent params still contribute) -> ``prepend
        set_all`` -> the jsui, which rebuilds without re-emitting and ignores
        the cascade mid-drag.

        **Native automatable params:** ``STEPS`` (``{id}_num``, a
        ``live.numbox``, int 2..max_steps, longname ``"{state_param} Count"``)
        drives ``set_steps`` (display re-quantizes, slot values preserved) AND
        feeds the hidden count host directly — without that sync wire a STEPS
        change with no bar edit would leave a stale stored count and the
        reload lane would depend on param-restore order. ``LINK``
        (``{id}_link``, a ``live.text`` toggle, longname
        ``"{state_param} Link"``) drives ``set_link`` — the engine only
        DISPLAYS the link chip (glyph + lane tint); wire the semantic (e.g.
        ganged lanes) downstream of the same param. Both are parked off the
        face by default (``presentation=0``); pass ``steps_rect`` /
        ``link_rect`` to place them visibly. ``set_playhead`` stays unwired —
        send it straight to the jsui inlet from a future sequencer clock.

        ``init_values`` seeds the leading slots (rest fill with
        ``init_value``); the initials seed the params, the pak defaults AND
        the engine's first paint, so the lane is honest before any value
        arrives. Returns the jsui box id; the hosts are ``f"{id}_steps"`` and
        ``f"{id}_s{{k}}"`` (k = 1..max_steps).
        """
        from .constants import UNITSTYLE_FLOAT, UNITSTYLE_INT
        from .engines.step_bars import step_bars_js
        from .parameters import PARAM_VIS_STORED_ONLY, ParameterSpec

        max_steps = int(max_steps)
        if not 2 <= max_steps <= 32:
            raise ValueError(f"max_steps must be 2..32, got {max_steps}")
        init_steps = int(init_steps)
        if not 2 <= init_steps <= max_steps:
            raise ValueError(
                f"init_steps must be 2..{max_steps}, got {init_steps}"
            )
        seeds = [float(v) for v in (init_values or ())]
        if len(seeds) > max_steps:
            raise ValueError(
                f"init_values holds {len(seeds)} values, max_steps is {max_steps}"
            )
        if any(not 0.0 <= v <= 1.0 for v in seeds):
            raise ValueError("init_values must be normalized 0..1")
        if not 0.0 <= float(init_value) <= 1.0:
            raise ValueError(f"init_value must be 0..1, got {init_value}")
        slots = seeds + [float(init_value)] * (max_steps - len(seeds))

        vis = PARAM_VIS_STORED_ONLY if stored_only else None

        # --- the editor jsui (ES5 engine, validated on add): 1 inlet / 1 outlet.
        self.add_jsui(
            id, rect,
            js_code=step_bars_js(
                accent=accent, bg=bg, max_steps=max_steps,
                init_steps=init_steps, init_values=slots,
                reset_value=reset_value, init_link=init_link,
            ),
            js_filename=js_filename or f"{id}_stepbars.js", content_address=True,
            numinlets=1, numoutlets=1, outlettype=[""],
            varname=varname or id,
        )

        # --- hidden STATE hosts: count + per-step value (presentation=0 keeps
        # them off the face; stored-only keeps them out of the automation UI).
        count_id = f"{id}_steps"
        self.add_dial(  # type: ignore[attr-defined]
            count_id, f"{state_param} N", [rect[0], rect[1], 30, 30],
            min_val=2.0, max_val=float(max_steps), initial=float(init_steps),
            showname=0, shownumber=0, presentation=0,
            unitstyle=UNITSTYLE_INT, steps=max_steps - 1, invisible=vis,
            patching_rect=[40, 560, 30, 30],
        )
        slot_ids = []
        for k in range(1, max_steps + 1):
            slot_id = f"{id}_s{k}"
            self.add_dial(  # type: ignore[attr-defined]
                slot_id, f"{state_param} S{k}", [rect[0], rect[1], 30, 30],
                min_val=0.0, max_val=1.0, initial=slots[k - 1],
                showname=0, shownumber=0, presentation=0,
                unitstyle=UNITSTYLE_FLOAT, invisible=vis,
                patching_rect=[40 + 34 * ((k - 1) % 16),
                               640 + 90 * ((k - 1) // 16), 30, 30],
            )
            slot_ids.append(slot_id)

        # --- native automatable params: STEPS numbox + LINK toggle.
        num_id = f"{id}_num"
        num_kwargs = {}
        if steps_rect is None:
            steps_rect = [rect[0], rect[1], 40, 15]
            num_kwargs["presentation"] = 0
        self.add_number_box(  # type: ignore[attr-defined]
            num_id, f"{state_param} Count", steps_rect,
            min_val=2.0, max_val=float(max_steps), initial=float(init_steps),
            unitstyle=UNITSTYLE_INT,
            patching_rect=[640, 560, 40, 15], **num_kwargs,
        )
        num_prep = f"{num_id}_prep"
        self.add_newobj(num_prep, "prepend set_steps", numinlets=1,
                        numoutlets=1, outlettype=[""],
                        patching_rect=[640, 600, 110, 20])
        self.add_line(num_id, 0, num_prep, 0)
        self.add_line(num_prep, 0, id, 0)
        # the sync wire: STEPS -> count host, so the stored count can never go
        # stale when the count changes without a bar edit (see docstring).
        self.add_line(num_id, 0, count_id, 0)

        link_id = f"{id}_link"
        link_kwargs = {}
        if link_rect is None:
            link_rect = [rect[0], rect[1], 40, 15]
            link_kwargs["presentation"] = 0
        self.add_live_text(  # type: ignore[attr-defined]
            link_id, f"{state_param} Link", link_rect,
            text_off=str(link_labels[0]), text_on=str(link_labels[1]), mode=1,
            patching_rect=[700, 560, 40, 15],
            parameter=ParameterSpec(
                name=f"{state_param} Link", shortname="Link",
                parameter_type=2, enum=[str(x) for x in link_labels],
                initial=[int(bool(init_link))], initial_enable=True),
            **link_kwargs,
        )
        link_prep = f"{link_id}_prep"
        self.add_newobj(link_prep, "prepend set_link", numinlets=1,
                        numoutlets=1, outlettype=[""],
                        patching_rect=[700, 600, 100, 20])
        self.add_line(link_id, 0, link_prep, 0)
        self.add_line(link_prep, 0, id, 0)

        # --- SAVE path: values list -> per-slot dials + the count dial.
        # `t l l` fires right-to-left, so the slots land FIRST and the count
        # LAST; the `step i v` stream falls out route's unmatched outlet.
        route_id = f"{id}_route"
        self.add_newobj(route_id, "route values", numinlets=2, numoutlets=2,
                        outlettype=["", ""], patching_rect=[40, 460, 90, 20])
        split_id = f"{id}_split"
        self.add_newobj(split_id, "t l l", numinlets=1, numoutlets=2,
                        outlettype=["", ""], patching_rect=[40, 490, 50, 20])
        len_id = f"{id}_len"
        self.add_newobj(len_id, "zl len", numinlets=2, numoutlets=2,
                        outlettype=["", ""], patching_rect=[40, 520, 50, 20])
        funnel_id = f"{id}_funnel"
        self.add_newobj(funnel_id, "listfunnel", numinlets=1, numoutlets=1,
                        outlettype=["list"], patching_rect=[160, 520, 70, 20])
        spray_id = f"{id}_spray"
        self.add_newobj(spray_id, f"spray {max_steps}", numinlets=1,
                        numoutlets=max_steps, outlettype=[""] * max_steps,
                        patching_rect=[40, 600, 550, 20])
        self.add_line(id, 0, route_id, 0)
        self.add_line(route_id, 0, split_id, 0)
        self.add_line(split_id, 1, funnel_id, 0)
        self.add_line(split_id, 0, len_id, 0)
        self.add_line(len_id, 0, count_id, 0)
        self.add_line(funnel_id, 0, spray_id, 0)
        for j, slot_id in enumerate(slot_ids):
            self.add_line(spray_id, j, slot_id, 0)

        # --- RESTORE path: every host output re-fires the pak; its creation
        # args ARE the initial state, so silent params still contribute.
        pak_args = [str(init_steps)] + [repr(v) for v in slots]
        pak_id = f"{id}_pak"
        self.add_newobj(pak_id, "pak " + " ".join(pak_args),
                        numinlets=1 + max_steps, numoutlets=1,
                        outlettype=[""], patching_rect=[40, 740, 550, 20])
        setall_id = f"{id}_setall"
        self.add_newobj(setall_id, "prepend set_all", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[40, 770, 110, 20])
        self.add_line(count_id, 0, pak_id, 0)
        for j, slot_id in enumerate(slot_ids):
            self.add_line(slot_id, 0, pak_id, j + 1)
        self.add_line(pak_id, 0, setall_id, 0)
        self.add_line(setall_id, 0, id, 0)
        return id

    def add_arc_knob_cluster(
        self,
        id: str,
        rect: list,
        knobs: list,
        *,
        accent: str = "0.36, 0.87, 0.99",
        cols: int = 2,
        radius: float = 14.0,
        drag_px: float = 90.0,
        host_park: tuple = (900, 900, 1, 1),
        js_filename: str = None,
        varname: str = None,
    ) -> dict:
        """Add an interactive ARC-KNOB CLUSTER — a bespoke premium control grid
        (v8ui) backed by parked ``live.dial`` param hosts, so drag/automation/
        MIDI-map/preset-recall all behave like native dials while the face shows
        the custom glowing arc-knobs. See
        :mod:`m4l_builder.engines.arc_knob_cluster`.

        ``knobs``: list of dicts — ``key`` (the outlet selector + ``set_``
        suffix + host id suffix), ``label`` (uppercase caption), ``min``,
        ``max``, optional ``init`` (defaults to ``min``), ``signed`` (leading
        ``+`` on positive display), ``name`` (Live parameter longname; defaults
        to ``label`` title-cased) and ``unitstyle`` (host dial unit; defaults to
        float).

        Wiring per knob: v8ui outlet -> ``route <keys...>`` -> the parked host
        (single source of truth), and the host -> ``prepend set_<key>`` -> the
        v8ui for visual sync. Returns ``{key: host_box_id}`` so the caller wires
        each host outlet to its target (a gen~ param, etc.).
        """
        from .constants import UNITSTYLE_FLOAT
        from .engines.arc_knob_cluster import (
            ARC_KNOB_CLUSTER_INLETS,
            ARC_KNOB_CLUSTER_OUTLETS,
            arc_knob_cluster_js,
        )

        self.add_v8ui(  # type: ignore[attr-defined]
            id, rect,
            js_code=arc_knob_cluster_js(
                knobs, accent=accent, cols=cols, radius=radius, drag_px=drag_px),
            js_filename=js_filename or f"{id}_arcknobs.js", content_address=True,
            numinlets=ARC_KNOB_CLUSTER_INLETS, numoutlets=ARC_KNOB_CLUSTER_OUTLETS,
            outlettype=[""], background=0, ignoreclick=0,
            bgcolor=[0.0, 0.0, 0.0, 0.0], varname=varname or id,
        )

        keys = [k["key"] for k in knobs]
        route_id = f"{id}_route"
        self.add_newobj(route_id, "route " + " ".join(keys), numinlets=1,
                        numoutlets=len(keys) + 1, outlettype=[""] * (len(keys) + 1),
                        patching_rect=[rect[0], 700, 70 + 40 * len(keys), 20])
        self.add_line(id, 0, route_id, 0)

        hosts = {}
        for i, k in enumerate(knobs):
            key = k["key"]
            hid = f"{id}_{key}"
            name = k.get("name") or str(k["label"]).title()
            self.add_dial(  # type: ignore[attr-defined]
                hid, name, list(host_park),
                min_val=float(k["min"]), max_val=float(k["max"]),
                initial=float(k.get("init", k["min"])),
                unitstyle=k.get("unitstyle", UNITSTYLE_FLOAT),
                showname=0, shownumber=0, presentation=0,
                patching_rect=[900, 300 + i * 34, 30, 30],
            )
            self.add_line(route_id, i, hid, 0)             # gesture -> host
            sync_id = f"{id}_sync_{key}"
            self.add_newobj(sync_id, f"prepend set_{key}", numinlets=1,
                            numoutlets=1, outlettype=[""],
                            patching_rect=[rect[0] + 220, 300 + i * 34, 130, 20])
            self.add_line(hid, 0, sync_id, 0)              # host -> v8ui sync
            self.add_line(sync_id, 0, id, 0)
            hosts[key] = hid
        return hosts

    def add_glass_panel_bg(
        self,
        id: str,
        rect: list,
        *,
        theme=None,
        lo: str = None,
        hi: str = None,
        border: str = None,
        radius: float = 8.0,
        inset: float = 4.0,
        noise: bool = True,
        js_filename: str = None,
        varname: str = None,
    ) -> str:
        """Add a SHOWCASE frosted-glass device background (v8ui) that exercises the
        premium drawing techniques (``ds_glass_panel`` + ``ds_inner_shadow`` +
        deterministic ``ds_noise_overlay`` + ``ds_rim_light``).

        A non-interactive, full-device background plate — like ``panel_bg`` but with
        real material depth. No pointer, no param (1 inlet / 0 outlets). Pass a
        ``theme`` to inherit its panel gradient/border, or override with ``lo``/
        ``hi``/``border`` ``"r, g, b[, a]"`` strings. ``noise`` adds a subtle, STABLE
        (seeded) texture — safe here because a background repaints rarely (never put
        the noise overlay on an animated control). Mirrors the ``add_v8ui`` contract:
        ``border=0`` + transparent ``bordercolor`` (so Max draws no black object box)
        and the plate self-paints its own gradient (transparent v8ui does not
        composite over lower layers in M4L). Returns the v8ui box id.
        """
        from .engines.glass_panel_bg import glass_panel_bg_js

        # Inherit the palette's panel material when a theme is supplied, else fall
        # back to the engine defaults (same convention as panel_bg_kwargs()).
        kw = {}
        if theme is not None:
            pk = theme.panel_bg_kwargs()
            kw["lo"] = lo if lo is not None else pk["lo"]
            kw["hi"] = hi if hi is not None else pk["hi"]
            kw["border"] = border if border is not None else pk["border"]
        else:
            if lo is not None:
                kw["lo"] = lo
            if hi is not None:
                kw["hi"] = hi
            if border is not None:
                kw["border"] = border

        self.add_v8ui(
            id, rect,
            js_code=glass_panel_bg_js(
                radius=radius, inset=inset, noise=noise, **kw,
            ),
            # content_address hashes the JS into the filename so ANY change (incl. the
            # shared ds_* design-system helpers) auto-busts Max's by-name sidecar cache —
            # no manual version bump. (Cache trap; supersedes the old version_tag fold.)
            js_filename=js_filename or f"{id}_glassbg.js", content_address=True,
            numinlets=1, numoutlets=0,
            background=1, ignoreclick=1, bgcolor=[0.0, 0.0, 0.0, 0.0],
            border=0, bordercolor=[0.0, 0.0, 0.0, 0.0],
            varname=varname or id,
        )
        return id

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
        in the ``gen~`` box (the Particle-Reverb structure) instead of shipped as
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

    def add_bpatcher_module(
        self,
        subpatcher,
        id: str,
        rect: list,
        *,
        name: str = "module",
        numinlets: int = 1,
        numoutlets: int = 1,
        outlettype: list = None,
        patching_rect: list = None,
        args: list = None,
    ):
        """Embed a Subpatcher as a VISIBLE bpatcher module (DSP + UI shown).

        ``args`` become the bpatcher arguments — Max substitutes ``#1``/``#2``
        placeholders inside the embedded patcher (object text AND param
        longnames) at load, which is how one component stamps into N uniquely
        named instances (see :meth:`add_component_rack`).

        Unlike ``add_subpatcher`` (an invisible ``p name`` box), this embeds the
        sub-patch as a ``bpatcher`` whose PRESENTATION view renders inside the
        device — the premium pattern for a self-contained DSP+UI module (e.g. a
        channel-strip processor, as in SABROI AS Console). ``embed=1`` bakes the
        sub-patch into the .amxd. Box attrs match the real devices.
        """
        box = {
            "id": id,
            "maxclass": "bpatcher",
            "name": name,
            "embed": 1,
            "numinlets": numinlets,
            "numoutlets": numoutlets,
            "patcher": subpatcher.to_presentation_patcher_dict(),
            "patching_rect": patching_rect or [700, 2400, rect[2], rect[3]],
            "presentation": 1,
            "presentation_rect": rect,
            "viewvisibility": 1,
            "bgmode": 0,
            "border": 0,
            "clickthrough": 0,
            "enablehscroll": 0,
            "enablevscroll": 0,
            "lockeddragscroll": 0,
            "offset": [0.0, 0.0],
        }
        if outlettype:
            box["outlettype"] = outlettype
        if args:
            box["args"] = list(args)
        return self.add_box({"box": box})

    def add_component_rack(
        self,
        component,
        count: int,
        *,
        rects: list,
        id_prefix: str = "comp",
        args=None,
        name: str = "component",
        numinlets: int = 1,
        numoutlets: int = 1,
        outlettype: list = None,
    ) -> list:
        """Stamp ONE Subpatcher component ``count`` times as embedded bpatchers —
        the corpus P11 rack (GROUNDED in lfo-cluster: six ``bpatcher args=[i]``
        of one component whose param longnames embed ``#1``; NO
        parameter_overrides — Max's ``#1`` substitution IS the mechanism).

        Author the component ONCE with placeholder param names
        (``ParameterSpec(name="#1 Rate", linknames=1)``); instance ``i``'s param
        resolves to ``"1 Rate"``, ``"2 Rate"``, … — unique, automatable,
        recallable Live params. ``args`` maps an instance index (0-based) to its
        bpatcher args; default ``[i + 1]``. ``rects`` are the per-instance
        presentation rects. Returns the bpatcher box ids.

        Live-proven (UIKit Rack): 3 stamps of one 2-param component -> six
        unique automatable params ('1 Rate' ... '3 Amount'), independent per
        instance. CAVEAT: ``#1`` substitutes in param longnames and object
        ARGUMENTS, but NOT in comment text inside an embedded bpatcher — drive
        instance captions from the arg (e.g. a message to a comment) if needed.
        """
        if len(rects) != count:
            raise ValueError(f"add_component_rack: {count} instances need "
                             f"{count} rects, got {len(rects)}")
        arg_fn = args or (lambda i: [i + 1])
        ids = []
        for i in range(count):
            bid = f"{id_prefix}_{i + 1}"
            self.add_bpatcher_module(
                component, bid, list(rects[i]), name=name,
                numinlets=numinlets, numoutlets=numoutlets,
                outlettype=outlettype,
                patching_rect=[700, 2400 + i * 40, rects[i][2], rects[i][3]],
                args=list(arg_fn(i)),
            )
            ids.append(bid)
        return ids

    def add_viz_bus(
        self,
        buffers,
        *,
        gen_box_id: str,
        viz_box_id: str,
        set_msg: str = "set_buffers",
        id_prefix: str = "vizbus",
        x: int = 700,
        y: int = 2600,
    ) -> dict:
        """Wire the D4 gen->named-buffer->jsui viz bus (the corpus keystone for
        live displays; stranular-verbatim contract).

        ``buffers``: list of ``(name, samps, channels)``. For each, adds a
        ``buffer~ ---<name> -1 <chans> @samps <samps>`` box. Then ONE
        ``live.thisdevice -> deferlow -> t b b`` fires, right-first:
        (1) the gen REBIND message ``<n1> ---<n1>, <n2> ---<n2>, ...`` into
        ``gen_box_id`` inlet 0 — gen's bare ``Buffer <n>;`` decls bind to the
        ``---``-resolved buffer~ objects (grounded in stranular's top patcher);
        (2) ``<set_msg> ---<n1> ---<n2> ...`` into ``viz_box_id`` inlet 0 —
        delivers the resolved names to the buffer_viz jsui and starts its poll
        Task (``---`` substitutes in message-box text at load).

        Returns the created box ids.
        """
        p = id_prefix
        for i, (name, samps, chans) in enumerate(buffers):
            self.add_newobj(
                f"{p}_buf{i}", f"buffer~ ---{name} -1 {int(chans)} @samps {int(samps)}",
                numinlets=1, numoutlets=2, outlettype=["float", "bang"],
                patching_rect=[x + i * 190, y, 180, 20])
        rebind_text = ", ".join(f"{name} ---{name}" for name, _s, _c in buffers)
        names_text = f"{set_msg} " + " ".join(f"---{name}" for name, _s, _c in buffers)
        self.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1, numoutlets=3,
                        outlettype=["bang", "int", "int"],
                        patching_rect=[x, y + 30, 90, 20])
        self.add_newobj(f"{p}_dl", "deferlow", numinlets=1, numoutlets=1,
                        outlettype=[""], patching_rect=[x, y + 60, 60, 20])
        self.add_newobj(f"{p}_t", "t b b", numinlets=1, numoutlets=2,
                        outlettype=["bang", "bang"],
                        patching_rect=[x, y + 90, 50, 20])
        self.add_box({"box": {
            "id": f"{p}_rebind", "maxclass": "message", "text": rebind_text,
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [x, y + 120, 260, 20]}})
        self.add_box({"box": {
            "id": f"{p}_names", "maxclass": "message", "text": names_text,
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [x + 280, y + 120, 260, 20]}})
        self.add_line(f"{p}_td", 0, f"{p}_dl", 0)
        self.add_line(f"{p}_dl", 0, f"{p}_t", 0)
        self.add_line(f"{p}_t", 1, f"{p}_rebind", 0)   # right first: rebind gen
        self.add_line(f"{p}_t", 0, f"{p}_names", 0)    # then arm the jsui poll
        self.add_line(f"{p}_rebind", 0, gen_box_id, 0)
        self.add_line(f"{p}_names", 0, viz_box_id, 0)
        return {
            "buffers": [f"{p}_buf{i}" for i in range(len(buffers))],
            "rebind": f"{p}_rebind", "names": f"{p}_names",
            "thisdevice": f"{p}_td",
        }

    def add_theme_bus(
        self,
        specs,
        *,
        targets=None,
        follow_live: bool = True,
        id_prefix: str = "ltheme",
        x: int = 20,
        y: int = 20,
    ):
        """Wire the runtime ``live.colors`` theme bus (B1) into this device so every
        native control re-tints from the user's actual Live skin — on load AND on a
        light/dark theme switch. The #1 corpus jewel (13/15 devices use it); premium
        devices never bake colors at build time.

        ``specs``: list of ``(skin_token, attr, bus)`` triples — broadcast the Live
        color named ``skin_token`` (see :data:`engines.live_theme.LIVE_SKIN`) over
        ``s ---<bus>`` as an ``<attr> R G B A`` message. Builds ONE shared
        ``live.thisdevice`` + ``live.colors`` distributor.

        ``targets``: optional dict ``{bus: [control_id | (control_id, inlet), ...]}``
        — auto-subscribe each listed native control via ``r ---<bus>`` (a
        :func:`engines.live_theme.live_theme_receiver` per control), so it tracks the
        skin with no per-control build-time color.

        ``follow_live`` is recorded on ``self.theme_follow_live`` so a theme pass can
        honor it (alpha-0 saved colors → the bus wins). Returns a dict with the
        ``colors`` / ``thisdevice`` box ids and the broadcast ``buses``.
        """
        from .engines.live_theme import live_colors_bus, live_theme_receiver

        boxes, lines = live_colors_bus(specs, id_prefix=id_prefix, x=x, y=y)
        self.add_dsp(boxes, lines)

        if targets:
            ry = y + 200
            for bus, ctrls in targets.items():
                for j, ctrl in enumerate(ctrls):
                    cid, inlet = ctrl if isinstance(ctrl, tuple) else (ctrl, 0)
                    rx_boxes, rx_lines = live_theme_receiver(
                        bus, cid, inlet=inlet,
                        id_prefix=f"{id_prefix}_rx{bus}_{j}", x=x, y=ry,
                    )
                    self.add_dsp(rx_boxes, rx_lines)
                    ry += 30

        self.theme_follow_live = bool(follow_live)
        return {
            "colors": f"{id_prefix}_colors",
            "thisdevice": f"{id_prefix}_thisdev",
            "buses": [bus for (_token, _attr, bus) in specs],
        }

    def add_theme_bus_dim(
        self,
        bus,
        *,
        attrs=("activedialcolor",),
        targets=None,
        active_token="lcd_control_fg",
        zombie_token="lcd_control_fg_zombie",
        id_prefix: str = "ltdim",
        x: int = 320,
        y: int = 20,
    ):
        """Wire the bypass "zombie" DIM gate (the second half of the J1 theme jewel):
        controls on ``bus`` carry the Live ACTIVE accent while the device is enabled
        and the DIMMED accent when bypassed, so the whole device greys out on bypass
        like a stock device. Grounded in the ``live.thisdevice`` middle outlet
        (doc: "1 or 0 when the Device is enabled or disabled").

        ``attrs``: the control color attributes the accent drives (e.g.
        ``("activedialcolor", "activefgdialcolor")`` for a dial). ``targets``:
        optional ``[control_id | (control_id, inlet), ...]`` to auto-subscribe via
        ``r ---<bus>``. Returns the ``thisdevice`` box id + the ``bus``.
        """
        from .engines.live_theme import live_theme_receiver, live_theme_state_dim

        boxes, lines = live_theme_state_dim(
            bus, attrs=attrs, active_token=active_token, zombie_token=zombie_token,
            id_prefix=id_prefix, x=x, y=y,
        )
        self.add_dsp(boxes, lines)
        if targets:
            ry = y + 230
            for j, ctrl in enumerate(targets):
                cid, inlet = ctrl if isinstance(ctrl, tuple) else (ctrl, 0)
                rx_boxes, rx_lines = live_theme_receiver(
                    bus, cid, inlet=inlet, id_prefix=f"{id_prefix}_rx{j}", x=x, y=ry,
                )
                self.add_dsp(rx_boxes, rx_lines)
                ry += 30
        return {"thisdevice": f"{id_prefix}_td", "bus": bus}

    def add_brand_dim(
        self,
        brand_rgba,
        targets,
        *,
        bus: str = "brandacc",
        attrs=("activedialcolor",),
        x: int = 700,
        y: int = 2000,
    ) -> str:
        """Wire the HYBRID brand-dim theme bus (the Surface default) into a
        BESPOKE-layout device: while enabled every target keeps the baked brand
        accent; on a Device-On bypass they all grey to the user's Live-skin
        "zombie" color (Live-proven on Strip v9 — the Device-On param observer
        is the only reliable runtime source; see
        :func:`engines.live_theme.live_brand_dim`).

        ``targets``: control box ids (fanned from ONE ``r ---<bus>`` receiver).
        Call once per accent color (distinct ``bus`` per call) on multi-accent
        devices. Returns the bus name.
        """
        from .engines.live_theme import live_brand_dim

        boxes, lines = live_brand_dim(bus, brand_rgba, attrs=attrs,
                                      id_prefix=f"{bus}_dim", x=x, y=y)
        self.add_dsp(boxes, lines)
        rx = f"{bus}_rx"
        self.add_newobj(rx, f"r ---{bus}", numinlets=0, numoutlets=1,
                        outlettype=[""], patching_rect=[x, y + 320, 90, 20])
        for tid in targets:
            self.add_line(rx, 0, tid, 0)
        return bus

    def paint_control(self, box_id, painter_filename: str, *, painter_js: str = None):
        """Attach a render-only ``jspainterfile`` painter to a NATIVE control (C1).

        Sets ``jspainterfile`` on the box ``box_id`` (a ``live.dial`` / ``live.numbox``
        / ``toggle`` …) so the control keeps full native behaviour + parameter
        storage while the ``.js`` paints it — the corpus pattern (Superberry/Chiral/
        AS Console). When ``painter_js`` is given it is bundled alongside the device
        as a TEXT asset under ``painter_filename`` (via ``register_asset``); pass a
        painter from :mod:`m4l_builder.engines.painters` (e.g.
        :func:`lcd_panel_painter_js`). Returns ``painter_filename``.

        The control box must already exist (create it with ``add_dial`` /
        ``add_draggable_readout`` / etc. first). Raises ``KeyError`` if not found.
        """
        target = str(box_id)
        for entry in self.boxes:
            box = entry.get("box", {})
            if box.get("id") == target:
                box["jspainterfile"] = painter_filename
                break
        else:
            raise KeyError(f"paint_control: no box with id {target!r}")

        if painter_js is not None:
            self.register_asset(painter_filename, painter_js, asset_type="TEXT")
        return painter_filename

    def add_init_ring(self, stages=("startBang",), *, defer: bool = True,
                      id_prefix: str = "initring", x: int = 20, y: int = 20):
        """Device-scoped staged init ring (F1): on load, ``live.thisdevice`` fires a
        (deferred) bang that broadcasts each stage over its ``---<name>`` bus IN
        ORDER, so subsystems initialise deterministically — each subscribes with
        ``r ---<name>``. The ``---`` prefix scopes the bus to THIS device instance
        (not global across the Live set).

        ``stages`` is the ordered list of bus names (``stages[0]`` fires first).
        ``defer=True`` routes the load bang through ``deferlow`` (low-priority queue,
        after the patch finishes loading — the Ableton-recommended init timing, so a
        ``loadbang`` race can't read half-built state). Returns
        ``{thisdevice, deferlow, stages}``.
        """
        p = id_prefix
        thisdev = self.add_newobj(
            f"{p}_thisdev", "live.thisdevice", numinlets=1, numoutlets=3,
            outlettype=["bang", "int", "int"], patching_rect=[x, y, 90, 20],
        )
        head, head_outlet, defer_id = thisdev, 0, None
        if defer:
            defer_id = self.add_newobj(
                f"{p}_defer", "deferlow", numinlets=1, numoutlets=1,
                outlettype=[""], patching_rect=[x, y + 30, 70, 20],
            )
            self.add_line(thisdev, 0, defer_id, 0)
            head, head_outlet = defer_id, 0

        stage_list = list(stages)
        trig = self.add_newobj(
            f"{p}_seq", "t " + " ".join(["b"] * len(stage_list)),
            numinlets=1, numoutlets=len(stage_list),
            outlettype=["bang"] * len(stage_list), patching_rect=[x, y + 60, 130, 20],
        )
        self.add_line(head, head_outlet, trig, 0)
        for i, stage in enumerate(stage_list):
            # t fires right-to-left, so stages[0] hangs off the RIGHTMOST outlet.
            outlet = len(stage_list) - 1 - i
            snd = self.add_newobj(
                f"{p}_s{i}", f"s ---{stage}", numinlets=1, numoutlets=0,
                patching_rect=[x + i * 100, y + 90, 90, 20],
            )
            self.add_line(trig, outlet, snd, 0)

        return {
            "thisdevice": f"{p}_thisdev",
            "deferlow": defer_id,
            "stages": stage_list,
        }

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
        content.add_newobj("_fly_this", "thispatcher", numinlets=1, numoutlets=2,
                           outlettype=["", ""], patching_rect=[40, 380, 70, 20])
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
        content.add_newobj("_fly_lb", "loadbang", numinlets=1, numoutlets=1,
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
        self.add_live_text(button_id, param_name, expand_rect,  # type: ignore[attr-defined]  # generated via setattr below
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
        mini_width: int,
        rect: list,
        full_width: int = None,
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

        ``full_width`` DEFAULTS to the current ``device.width`` (rounded) — call
        this AFTER the layout is final (e.g. after ``Surface.finalize()``). A
        stale hand-typed ``full_width`` is how Pressure shipped a 688px FULL on
        a 550px layout (~148px dead zone); deriving it kills that bug class.

        PLACE THE BUTTON ON THE LEFT: a MINI width clips the right side off (it
        does not reflow), so the toggle must sit inside ``mini_width`` to stay
        clickable, and the device's essentials should live on the left.

        Returns the toggle button id.
        """
        if full_width is None:
            full_width = round(self.width)
        bkw = {"text_on": text_mini, "text_off": text_full, "rounded": 4,
               "fontsize": 7.5, "mode": 1}
        if button_kwargs:
            bkw.update(button_kwargs)
        self.add_live_text(button_id, param_name, rect,  # type: ignore[attr-defined]  # generated via setattr below
                           parameter=ParameterSpec(
                               name=param_name, parameter_type=2,
                               enum=[text_full, text_mini], initial=[0],
                               initial_enable=True),
                           **bkw)
        self.add_newobj(f"{button_id}_thisdev", "live.thisdevice", numinlets=1,
                        numoutlets=3, outlettype=["bang", "int", "int"],
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
