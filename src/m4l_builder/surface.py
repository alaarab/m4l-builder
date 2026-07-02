"""Surface — the semantic device-faceplate layout engine (UI Foundations v2).

The corpus audit found the kit had the right *primitives* (``dial_value_cell``,
``knob_column``, the theme bus) but 16 of 17 devices still hand-wrote every
label+dial rect — and drifted (8 dial sizes, 3 value-display strategies, hover
values, stale widths). ``Surface`` owns that rect math. A device author
declares hero displays and labeled sections of cells; the engine computes every
rect from the :mod:`native_sizes` cell grammar, derives the final device width
from content (no more stale ``full_width``/dead zones), and wires the hybrid
brand-accent theme bus (baked accent while enabled, Live "zombie" grey on
bypass — corpus P1) into every dial it placed.

Composition rules it enforces at build time (:class:`SurfaceError`):

* persistent values ALWAYS (corpus P2) — every dial is a
  :func:`~m4l_builder.recipes.dial_value_cell`; the hover-``valuepopup``
  value-less knob is not expressible;
* at most :data:`~m4l_builder.native_sizes.MAX_VALUE_ROWS` dial rows per
  section — a 4th persistent-value row provably overflows the 156px band;
* sections cannot over-fill (cols x rows is the capacity).

Typical use (immediate-mode; boxes are emitted at declaration so interleaved
``add_line`` wiring keeps working; call :meth:`Surface.finalize` last)::

    device = AudioEffect(NAME, width=1, height=168, theme=GRAPHITE)
    s = Surface(device, accent="pressure")
    hero = s.hero("xfer", width=300)
    hero.v8ui(js_code=DISPLAY_JS, js_filename=DISPLAY_FILENAME)
    gc = s.section("gc", "COMP", cols=2)
    gc.dial("Threshold", "THRESH", min_val=-60, max_val=0, initial=0,
            unitstyle=UNITSTYLE_DB)
    ...
    WIDTH = s.finalize()          # derives + assigns device.width
    device.add_width_collapse(mini_width=370, rect=[12, 1, 42, 9])
"""

from __future__ import annotations

import re
from typing import Any

from . import native_sizes as ns
from .parameters import ParameterSpec
from .recipes import dial_value_cell
from .theme import ACCENTS, GRAPHITE, Theme

# Top of the content band: hero frames and section cards run BAND_Y..BAND_Y+156
# inside the 168px device (the fleet's graph_frame [8, 6, w, 156] convention).
BAND_Y = 6
# Dark text on a lit accent button (was TEXT_ON_DARK, copied per device).
TEXT_ON_ACCENT = [0.05, 0.06, 0.07, 1.0]
# Height of the control row of a toggle/menu/numbox cell (below its caption).
SHORT_CTRL_H = 16


class SurfaceError(ValueError):
    """A Surface composition rule was violated (raised at build time)."""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "p"


class HeroSlot:
    """A hero-display slot (corpus P10): a recessed screen panel on the card.

    ``rect`` is the inset content rect — pass it to ``add_compiled_display`` /
    ``add_jsui`` for bespoke content, or call :meth:`v8ui` for the common case.
    ``frame_rect`` is the outer screen panel.
    """

    def __init__(self, surface: Surface, id_prefix: str,
                 frame_rect: list, content_rect: list):
        self.surface = surface
        self.id = id_prefix
        self.frame_rect = frame_rect
        self.rect = content_rect

    def v8ui(self, *, js_code: str, js_filename: str | None = None,
             id: str | None = None, numinlets: int = 1, numoutlets: int = 0,
             **kwargs: Any) -> str:
        """Add a ``v8ui`` filling the hero content rect. Returns the box id."""
        return self.surface.device.add_v8ui(
            id or f"{self.id}_ui", list(self.rect), js_code=js_code,
            js_filename=js_filename, numinlets=numinlets, numoutlets=numoutlets,
            **kwargs,
        )


class Section:
    """A labeled section card (corpus P3) holding a cols x rows grid of cells.

    Cells fill COLUMN-MAJOR (down, then right — the console-strip reading
    order); pin a cell with ``at=(col, row)``. Every dial cell is a persistent
    -value :func:`~m4l_builder.recipes.dial_value_cell` and auto-registers on
    the surface's brand-dim accent bus.
    """

    def __init__(self, surface: Surface, id_prefix: str, title: str | None,
                 *, x: int, cols: int, rows: int, col_pitch: int, pad: int,
                 material: str):
        self.surface = surface
        self.id = id_prefix
        self.cols = cols
        self.rows = rows
        self._pad = pad
        self._pitch = col_pitch
        self._x = x
        self._used: set[tuple[int, int]] = set()
        self.width = 2 * pad + (cols - 1) * col_pitch + ns.CELL_W

        theme = surface.theme
        bg = theme.surface if material == "card" else theme.section
        surface.device.add_panel(
            f"{id_prefix}_card", [x, BAND_Y, self.width, surface.band_h],
            bgcolor=list(bg), rounded=5,
        )
        header_h = ns.SECTION_HEADER_H if title else 0
        if title:
            surface.device.add_comment(
                f"{id_prefix}_hdr", [x + pad, BAND_Y + 1, self.width - 2 * pad, 12],
                title.upper(), fontsize=ns.HEADER_FONTSIZE, fontname=ns.FONTNAME,
                textcolor=list(theme.text_dim), justification=0,
            )
        # Grid: distribute `rows` VALUE_CELL_H cells evenly in the band under
        # the header; every cell type shares the grid so captions align.
        avail = surface.band_h - header_h
        rows_y0 = BAND_Y + header_h
        pitch = avail // rows
        off = (avail - rows * pitch) // 2
        self._cell_ys = [
            rows_y0 + off + i * pitch + max((pitch - ns.VALUE_CELL_H) // 2, 0)
            for i in range(rows)
        ]

    # ── grid bookkeeping ────────────────────────────────────────────────────
    def _take_slot(self, at: tuple[int, int] | None) -> tuple[int, int]:
        if at is not None:
            col, row = at
            if not (0 <= col < self.cols and 0 <= row < self.rows):
                raise SurfaceError(
                    f"section {self.id!r}: at={at} outside {self.cols}x{self.rows}")
            if at in self._used:
                raise SurfaceError(f"section {self.id!r}: cell {at} already used")
            self._used.add((col, row))
            return col, row
        for idx in range(self.cols * self.rows):
            col, row = idx // self.rows, idx % self.rows
            if (col, row) not in self._used:
                self._used.add((col, row))
                return col, row
        raise SurfaceError(
            f"section {self.id!r} is full ({self.cols}x{self.rows}); add a column "
            f"or start a new section")

    def _cell_xy(self, col: int, row: int) -> tuple[int, int]:
        return self._x + self._pad + col * self._pitch, self._cell_ys[row]

    def slot_rect(self, at: tuple[int, int] | None = None) -> list:
        """Claim a grid cell for BESPOKE content; returns its ``[x, y, w, h]``."""
        cx, cy = self._cell_xy(*self._take_slot(at))
        return [cx, cy, ns.CELL_W, ns.VALUE_CELL_H]

    def blank(self) -> None:
        """Skip the next free grid slot."""
        self._take_slot(None)

    def _caption(self, cid: str, cx: int, cy: int, text: str) -> str:
        return self.surface.device.add_comment(
            cid, [cx, cy, ns.CELL_W, ns.CAPTION_H], text.upper(),
            fontsize=ns.CAPTION_FONTSIZE, fontname=ns.FONTNAME,
            textcolor=list(self.surface.theme.text_dim), justification=1,
        )

    # ── cells ───────────────────────────────────────────────────────────────
    def dial(self, param_name: str, label: str | None = None, *,
             min_val: float = 0.0, max_val: float = 100.0, initial: float = 0.0,
             unitstyle: int = 1, at: tuple[int, int] | None = None,
             accent2: bool = False, fill: list | None = None,
             **dial_kwargs: Any):
        """A persistent-value dial cell (P2/P4). Returns the recipe StageResult
        (``["dial"]``/``["label"]``/``["rect"]`` + the param handle)."""
        col, row = self._take_slot(at)
        cx, cy = self._cell_xy(col, row)
        dial_rect = [cx + (ns.CELL_W - ns.DIAL_COMPACT[0]) // 2,
                     cy + ns.CAPTION_H + ns.CAPTION_GAP, *ns.DIAL_COMPACT]
        accent = ((self.surface.accent2 or self.surface.accent)
                  if accent2 else self.surface.accent)
        res = dial_value_cell(
            self.surface.device, f"{self.id}_{_slug(param_name)}", param_name,
            dial_rect, label=(label or param_name).upper(),
            min_val=min_val, max_val=max_val, initial=initial,
            unitstyle=unitstyle, accent=list(accent), fill=fill,
            label_h=ns.CAPTION_H, label_gap=ns.CAPTION_GAP,
            label_fontsize=ns.CAPTION_FONTSIZE,
            label_color=list(self.surface.theme.text_dim), **dial_kwargs,
        )
        targets = (self.surface._accent2_targets if accent2
                   else self.surface._accent_targets)
        targets.append(res["dial"])
        return res

    def toggle(self, param_name: str, label: str | None = None, *,
               on: str = "ON", off: str = "OFF", initial: int = 0,
               at: tuple[int, int] | None = None, **kwargs: Any) -> str:
        """A captioned 2-state ``live.text`` cell (self-documenting enum, corpus
        convention). Returns the button box id."""
        col, row = self._take_slot(at)
        cx, cy = self._cell_xy(col, row)
        p = f"{self.id}_{_slug(param_name)}"
        self._caption(f"{p}_cap", cx, cy, label or param_name)
        theme = self.surface.theme
        bkw: dict[str, Any] = dict(
            mode=1, rounded=4, fontsize=ns.CAPTION_FONTSIZE,
            bgcolor=list(theme.section), bgoncolor=list(self.surface.accent),
            textcolor=list(theme.text_dim), textoncolor=list(TEXT_ON_ACCENT),
        )
        bkw.update(kwargs)
        self.surface.device.add_live_text(  # type: ignore[attr-defined]
            f"{p}_btn", param_name,
            [cx, cy + ns.CAPTION_H + ns.CAPTION_GAP, ns.CELL_W, SHORT_CTRL_H],
            text_on=on, text_off=off,
            parameter=ParameterSpec(name=param_name, parameter_type=2,
                                    enum=[off, on], initial=[initial],
                                    initial_enable=True),
            **bkw,
        )
        return f"{p}_btn"

    def menu(self, param_name: str, options: list, label: str | None = None,
             *, initial: int = 0, at: tuple[int, int] | None = None,
             **kwargs: Any) -> str:
        """A captioned ``live.menu`` cell. Returns the menu box id."""
        col, row = self._take_slot(at)
        cx, cy = self._cell_xy(col, row)
        p = f"{self.id}_{_slug(param_name)}"
        self._caption(f"{p}_cap", cx, cy, label or param_name)
        self.surface.device.add_menu(  # type: ignore[attr-defined]
            f"{p}_menu", param_name,
            [cx, cy + ns.CAPTION_H + ns.CAPTION_GAP, ns.CELL_W, ns.MENU[1]],
            options=list(options), initial=initial, **kwargs,
        )
        return f"{p}_menu"

    def numbox_lcd(self, param_name: str, label: str | None = None, *,
                   min_val: float = 0.0, max_val: float = 100.0,
                   initial: float = 0.0, unitstyle: int = 1,
                   at: tuple[int, int] | None = None,
                   **kwargs: Any) -> str:
        """A captioned ``appearance=4`` LCD numbox cell (:data:`ns.NUMBOX_LCD`).
        Returns the numbox box id."""
        col, row = self._take_slot(at)
        cx, cy = self._cell_xy(col, row)
        p = f"{self.id}_{_slug(param_name)}"
        self._caption(f"{p}_cap", cx, cy, label or param_name)
        theme = self.surface.theme
        nkw: dict[str, Any] = dict(
            lcdcolor=list(self.surface.accent),
            lcdbgcolor=list(theme.lcd_bg) if theme.lcd_bg else None,
        )
        nkw = {k: v for k, v in nkw.items() if v is not None}
        nkw.update(kwargs)
        w, h = ns.NUMBOX_LCD
        self.surface.device.add_number_box(  # type: ignore[attr-defined]
            f"{p}_num", param_name,
            [cx + (ns.CELL_W - w) // 2, cy + ns.CAPTION_H + ns.CAPTION_GAP, w, h],
            min_val=min_val, max_val=max_val, initial=initial,
            unitstyle=unitstyle, **nkw,
        )
        return f"{p}_num"


class Surface:
    """The device faceplate composer — see the module docstring."""

    def __init__(self, device: Any, *, accent: str | list,
                 accent2: list | None = None, theme: Theme = GRAPHITE,
                 height: int = ns.DEVICE_H, margin: int = 8, gap: int = 6,
                 follow_live: bool = True, bg_id: str = "surf_bg"):
        self.device = device
        self.theme = theme
        self.accent = (list(ACCENTS[accent]) if isinstance(accent, str)
                       else list(accent))
        self.accent2 = list(accent2) if accent2 is not None else None
        self.height = height
        self.margin = margin
        self.gap = gap
        self.follow_live = follow_live
        self.band_h = height - 2 * BAND_Y
        self._x = margin
        self._has_slots = False
        self._accent_targets: list[str] = []
        self._accent2_targets: list[str] = []
        self._final_width: int | None = None
        self._bg_id = bg_id
        # Full-bleed branded bg; placeholder width patched at finalize().
        device.add_panel(bg_id, [0, 0, 4, height], bgcolor=list(theme.bg))

    # ── slots ───────────────────────────────────────────────────────────────
    def hero(self, id_prefix: str, *, width: int, recess: bool = True) -> HeroSlot:
        """A hero-display slot: recessed screen panel + inset content rect."""
        self._check_open()
        frame = [self._x, BAND_Y, width, self.band_h]
        if recess:
            self.device.add_panel(
                f"{id_prefix}_frame", list(frame),
                bgcolor=list(self.theme.scope_bgcolor or self.theme.bg),
                border=1, bordercolor=list(self.theme.panel_border or self.theme.text_dim),
                rounded=4,
            )
        content = [frame[0] + 2, frame[1] + 2, frame[2] - 4, frame[3] - 4]
        self._advance(width)
        return HeroSlot(self, id_prefix, frame, content)

    def section(self, id_prefix: str, title: str | None = None, *,
                cols: int, rows: int = ns.MAX_VALUE_ROWS,
                material: str = "card", col_pitch: int = ns.COL_PITCH,
                pad: int = 8) -> Section:
        """A labeled section card of ``cols x rows`` cells."""
        self._check_open()
        if not 1 <= rows <= ns.MAX_VALUE_ROWS:
            raise SurfaceError(
                f"section {id_prefix!r}: rows={rows} — persistent-value cells cap "
                f"at {ns.MAX_VALUE_ROWS} rows in the {self.band_h}px band (a 4th "
                f"row only ever fit by hiding the value, which Surface forbids)")
        if cols < 1:
            raise SurfaceError(f"section {id_prefix!r}: cols must be >= 1")
        if material not in ("card", "rail"):
            raise SurfaceError(f"section {id_prefix!r}: material must be card|rail")
        sect = Section(self, id_prefix, title, x=self._x, cols=cols, rows=rows,
                       col_pitch=col_pitch, pad=pad, material=material)
        self._advance(sect.width)
        return sect

    def probe(self, id: str, param_name: str, **dial_kwargs: Any) -> str:
        """A hidden diagnostic/probe param parked at :data:`ns.PARK_RECT`."""
        dial_kwargs.setdefault("showname", 0)
        dial_kwargs.setdefault("shownumber", 0)
        self.device.add_dial(  # type: ignore[attr-defined]
            id, param_name, list(ns.PARK_RECT), **dial_kwargs)
        return id

    # ── finalize ────────────────────────────────────────────────────────────
    def finalize(self) -> int:
        """Derive + assign the device width from content, patch the bg panel,
        and wire the hybrid brand-dim accent bus. Idempotent; returns width."""
        if self._final_width is not None:
            return self._final_width
        content_right = (self._x - self.gap) if self._has_slots else self._x
        width = content_right + self.margin
        self.device.width = width
        for entry in self.device.boxes:
            box = entry.get("box", {})
            if box.get("id") == self._bg_id:
                for key in ("presentation_rect", "patching_rect"):
                    if key in box:
                        box[key] = [0, 0, width, self.height]
                break
        if self.follow_live:
            if self._accent_targets:
                self._emit_dim_bus("surfacc", self.accent,
                                   self._accent_targets, x=700, y=1700)
            if self._accent2_targets:
                self._emit_dim_bus("surfacc2", self.accent2 or self.accent,
                                   self._accent2_targets, x=1040, y=1700)
        self.device.theme_follow_live = bool(self.follow_live)
        self._final_width = width
        return width

    # ── internals ───────────────────────────────────────────────────────────
    def _check_open(self) -> None:
        if self._final_width is not None:
            raise SurfaceError("Surface already finalized — add slots before "
                               "finalize()")

    def _advance(self, width: int) -> None:
        self._x += width + self.gap
        self._has_slots = True

    def _emit_dim_bus(self, bus: str, rgba: list, targets: list[str], *,
                      x: int, y: int) -> None:
        from .engines.live_theme import live_brand_dim

        boxes, lines = live_brand_dim(bus, rgba, attrs=("activedialcolor",),
                                      id_prefix=f"{bus}_dim", x=x, y=y)
        self.device.add_dsp(boxes, lines)
        rx = f"{bus}_rx"
        self.device.add_newobj(rx, f"r ---{bus}", numinlets=0, numoutlets=1,
                               outlettype=[""], patching_rect=[x, y + 300, 90, 20])
        for tid in targets:
            self.device.add_line(rx, 0, tid, 0)
