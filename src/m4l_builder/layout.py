"""Context manager-based layout containers for placing UI elements."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from . import ui

if TYPE_CHECKING:
    from typing import Concatenate

    from typing_extensions import ParamSpec

    from .ui_registry import VarnameWidgetMethod, WidgetMethod

    _P = ParamSpec("_P")


def snap_rect(rect):
    """Snap a rect to whole-integer pixels (Ableton's whole-pixel
    convention): fractional ``presentation_rect`` coordinates
    render blurry / off-grid in Live. Rounds each component; int-valued
    floats collapse to ints so emitted JSON stays clean."""
    return [int(round(v)) for v in rect]


def inset_rect(
    rect,
    *,
    pad=0,
    pad_x=None,
    pad_y=None,
    left=None,
    top=None,
    right=None,
    bottom=None,
):
    """Return an inset rect while preserving non-negative width/height."""
    x, y, w, h = rect
    pad_x = pad if pad_x is None else pad_x
    pad_y = pad if pad_y is None else pad_y
    left = pad_x if left is None else left
    right = pad_x if right is None else right
    top = pad_y if top is None else top
    bottom = pad_y if bottom is None else bottom
    inner_w = max(0, w - left - right)
    inner_h = max(0, h - top - bottom)
    return [x + left, y + top, inner_w, inner_h]


def _make_simple_proxy(widget_name):
    def method(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return getattr(self._device, f"add_{widget_name}")(id, rect, **kw)

    method.__name__ = f"add_{widget_name}"
    method.__qualname__ = f"_LayoutContainer.add_{widget_name}"
    method.__doc__ = f"Add a `{widget_name}` widget at the next layout slot."
    return method


def _make_varname_proxy(widget_name):
    def method(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return getattr(self._device, f"add_{widget_name}")(id, varname, rect, **kw)

    method.__name__ = f"add_{widget_name}"
    method.__qualname__ = f"_LayoutContainer.add_{widget_name}"
    method.__doc__ = f"Add a `{widget_name}` widget at the next layout slot."
    return method


# Proxy declarations are typed after the ui.py factory (minus ``rect``, which
# the container computes); ``width``/``height`` ride in the factory's
# ``**kwargs``. Names are collected in declaration order for the tables below.
_simple_proxy_names: list[str] = []
_varname_proxy_names: list[str] = []


def _layout_widget(factory: Callable[Concatenate[str, list, _P], dict]) -> WidgetMethod[_P]:
    """Proxy for a device wrapper shaped (id, rect, **kw)."""
    _simple_proxy_names.append(factory.__name__)
    return _make_simple_proxy(factory.__name__)  # type: ignore[return-value]


def _layout_varname_widget(
    factory: Callable[Concatenate[str, str, list, _P], dict],
) -> VarnameWidgetMethod[_P]:
    """Proxy for a device wrapper shaped (id, varname, rect, **kw)."""
    _varname_proxy_names.append(factory.__name__)
    return _make_varname_proxy(factory.__name__)  # type: ignore[return-value]


class _LayoutContainer:
    """Mixin providing proxy add_* methods that auto-compute rects."""

    def _next_rect(self, width=None, height=None, span=None):
        raise NotImplementedError

    def slot(
        self,
        *,
        width=None,
        height=None,
        span=None,
        pad=0,
        pad_x=None,
        pad_y=None,
        left=None,
        top=None,
        right=None,
        bottom=None,
    ):
        rect = self._next_rect(width, height, span=span)
        if any(value is not None for value in (pad_x, pad_y, left, top, right, bottom)) or pad:
            return snap_rect(inset_rect(
                rect,
                pad=pad,
                pad_x=pad_x,
                pad_y=pad_y,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            ))
        return snap_rect(rect)

    # Proxies whose shape is uniform — (id, rect, **kw) or (id, varname,
    # rect, **kw) — are declared from their factory; only widgets with
    # unique signatures are defined inline.
    add_panel = _layout_widget(ui.panel)
    add_scope = _layout_widget(ui.scope)
    add_plot = _layout_widget(ui.plot)
    add_filtergraph = _layout_widget(ui.filtergraph)
    add_function = _layout_widget(ui.function)
    add_waveform = _layout_widget(ui.waveform)
    add_spectrumdraw = _layout_widget(ui.spectrumdraw)
    add_meter = _layout_widget(ui.meter)
    add_fpic = _layout_widget(ui.fpic)
    add_pictctrl = _layout_widget(ui.pictctrl)
    add_multislider = _layout_widget(ui.multislider)
    add_adsrui = _layout_widget(ui.adsrui)
    add_live_drop = _layout_widget(ui.live_drop)
    add_swatch = _layout_widget(ui.swatch)
    add_textedit = _layout_widget(ui.textedit)
    add_live_step = _layout_widget(ui.live_step)
    add_live_grid = _layout_widget(ui.live_grid)
    add_live_line = _layout_widget(ui.live_line)
    add_live_arrows = _layout_widget(ui.live_arrows)
    add_rslider = _layout_widget(ui.rslider)
    add_kslider = _layout_widget(ui.kslider)
    add_nodes = _layout_widget(ui.nodes)
    add_matrixctrl = _layout_widget(ui.matrixctrl)
    add_ubutton = _layout_widget(ui.ubutton)
    add_nslider = _layout_widget(ui.nslider)
    add_umenu = _layout_widget(ui.umenu)
    add_radiogroup = _layout_widget(ui.radiogroup)
    add_dial = _layout_varname_widget(ui.dial)
    add_toggle = _layout_varname_widget(ui.toggle)
    add_slider = _layout_varname_widget(ui.slider)
    add_button = _layout_varname_widget(ui.button)
    add_number_box = _layout_varname_widget(ui.number_box)
    add_live_text = _layout_varname_widget(ui.live_text)
    add_live_gain = _layout_varname_widget(ui.live_gain)

    # Pattern C: (id, rect, text, **kw)
    def add_comment(self, id, text, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_comment(id, rect, text, **kw)

    # Pattern D: (id, varname, rect, options, **kw)
    def add_menu(self, id, varname, options, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_menu(id, varname, rect, options, **kw)

    def add_tab(self, id, varname, options, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_tab(id, varname, rect, options, **kw)

    # Pattern E: (id, rect, text, **kw)
    def add_textbutton(self, id, text="Button", *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_textbutton(id, rect, text, **kw)

    # Pattern F: (id, rect, **kw) with js_code kwarg
    def add_jsui(self, id, *, js_code, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_jsui(id, rect, js_code=js_code, **kw)

    def add_v8ui(self, id, *, js_code, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_v8ui(id, rect, js_code=js_code, **kw)

    # bpatcher: (id, rect, patcher_name, **kw)
    def add_bpatcher(self, id, patcher_name, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_bpatcher(id, rect, patcher_name, **kw)


_SIMPLE_PROXY_WIDGETS = tuple(_simple_proxy_names)
_VARNAME_PROXY_WIDGETS = tuple(_varname_proxy_names)


class Row(_LayoutContainer):
    """Horizontal layout container. Cursor advances left to right."""

    def __init__(self, device, x, y, *, spacing=8, height=None, width=None):
        self._device = device
        self._x = x
        self._y = y
        self._spacing = spacing
        self._default_height = height
        self._default_width = width
        self._cursor_x = x
        self._items = 0

    def __enter__(self) -> Row:
        return self

    def __exit__(self, *args):
        pass

    @property
    def used_width(self):
        if self._items == 0:
            return 0
        return self._cursor_x - self._x - self._spacing

    @property
    def used_height(self):
        return self._default_height or 0

    def _next_rect(self, width=None, height=None, span=None):
        w = width or self._default_width or 50
        h = height or self._default_height or 50
        rect = [self._cursor_x, self._y, w, h]
        self._cursor_x += w + self._spacing
        self._items += 1
        return snap_rect(rect)

    def column(self, *, spacing=4, width=None, height=None):
        return _NestedColumn(self._device, self, self._cursor_x, self._y,
                             spacing=spacing, width=width, height=height)


class Column(_LayoutContainer):
    """Vertical layout container. Cursor advances top to bottom."""

    def __init__(self, device, x, y, *, spacing=4, width=None, height=None):
        self._device = device
        self._x = x
        self._y = y
        self._spacing = spacing
        self._default_width = width
        self._default_height = height
        self._cursor_y = y
        self._items = 0

    def __enter__(self) -> Column:
        return self

    def __exit__(self, *args):
        pass

    @property
    def used_width(self):
        return self._default_width or 0

    @property
    def used_height(self):
        if self._items == 0:
            return 0
        return self._cursor_y - self._y - self._spacing

    def _next_rect(self, width=None, height=None, span=None):
        w = width or self._default_width or 50
        h = height or self._default_height or 50
        rect = [self._x, self._cursor_y, w, h]
        self._cursor_y += h + self._spacing
        self._items += 1
        return snap_rect(rect)

    def row(self, *, spacing=8, height=None, width=None):
        return _NestedRow(self._device, self, self._x, self._cursor_y,
                          spacing=spacing, height=height, width=width)


class Grid(_LayoutContainer):
    """Grid layout. Fills left-to-right, wraps to next row at `cols`."""

    def __init__(self, device, x, y, *, cols, col_width, row_height,
                 spacing_x=4, spacing_y=4):
        self._device = device
        self._x = x
        self._y = y
        self._cols = cols
        self._col_width = col_width
        self._row_height = row_height
        self._spacing_x = spacing_x
        self._spacing_y = spacing_y
        self._current_col = 0
        self._current_row = 0
        self._items = 0

    def __enter__(self) -> Grid:
        return self

    def __exit__(self, *args):
        pass

    @property
    def used_width(self):
        if self._items == 0:
            return 0
        actual_cols = min(self._items, self._cols)
        return actual_cols * self._col_width + (actual_cols - 1) * self._spacing_x

    @property
    def used_height(self):
        if self._items == 0:
            return 0
        total_rows = self._current_row + (1 if self._current_col > 0 else 0)
        if total_rows == 0:
            # All items fit exactly in completed rows
            total_rows = self._current_row
        return total_rows * self._row_height + (total_rows - 1) * self._spacing_y

    def _next_rect(self, width=None, height=None, span=None):
        col = self._current_col
        row = self._current_row
        x = self._x + col * (self._col_width + self._spacing_x)
        y = self._y + row * (self._row_height + self._spacing_y)
        w = width or self._col_width
        h = height or self._row_height
        rect = [x, y, w, h]
        self._current_col += 1
        if self._current_col >= self._cols:
            self._current_col = 0
            self._current_row += 1
        self._items += 1
        return snap_rect(rect)


class Columns(_LayoutContainer):
    """Span-based horizontal layout for 12-col style shells."""

    def __init__(self, device, x, y, *, width, cols=12.0, height=None):
        if cols <= 0:
            raise ValueError(f"cols must be > 0, got {cols}")
        if width <= 0:
            raise ValueError(f"width must be > 0, got {width}")
        self._device = device
        self._x = x
        self._y = y
        self._width = float(width)
        self._cols = float(cols)
        self._default_height = height
        self._cursor_cols = 0.0
        self._items = 0

    def __enter__(self) -> Columns:
        return self

    def __exit__(self, *args):
        pass

    @property
    def unit_width(self):
        return self._width / self._cols

    @property
    def used_width(self):
        return self._cursor_cols * self.unit_width

    @property
    def used_height(self):
        return self._default_height or 0

    @property
    def used_cols(self):
        return self._cursor_cols

    @property
    def remaining_cols(self):
        return max(0.0, self._cols - self._cursor_cols)

    def _normalize_span(self, width=None, span=None):
        if span is not None and width is not None:
            raise ValueError("pass either width or span, not both")
        if span is None:
            if width is None:
                span = 1.0
            else:
                span = float(width) / self.unit_width
        span = float(span)
        if span <= 0:
            raise ValueError(f"span must be > 0, got {span}")
        if self._cursor_cols + span > self._cols + 1e-9:
            raise ValueError(
                f"span overflow: used {self._cursor_cols}, requested {span}, total {self._cols}"
            )
        return span

    def _next_rect(self, width=None, height=None, span=None):
        span = self._normalize_span(width=width, span=span)
        w = float(width) if width is not None else span * self.unit_width
        h = height or self._default_height or 50
        rect = [round(self._x + self.used_width, 4), self._y, round(w, 4), h]
        self._cursor_cols += span
        self._items += 1
        return snap_rect(rect)


class _NestedRow(Row):
    """A Row nested inside a Column. Advances the parent cursor on exit."""

    def __init__(self, device, parent_col, x, y, **kw):
        super().__init__(device, x, y, **kw)
        self._parent = parent_col

    def __exit__(self, *args):
        h = self._default_height or self.used_height
        self._parent._cursor_y += h + self._parent._spacing
        self._parent._items += 1


class _NestedColumn(Column):
    """A Column nested inside a Row. Advances the parent cursor on exit."""

    def __init__(self, device, parent_row, x, y, **kw):
        super().__init__(device, x, y, **kw)
        self._parent = parent_row

    def __exit__(self, *args):
        w = self._default_width or self.used_width
        self._parent._cursor_x += w + self._parent._spacing
        self._parent._items += 1
