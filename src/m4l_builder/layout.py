"""Context manager-based layout containers for placing UI elements."""


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
            return inset_rect(
                rect,
                pad=pad,
                pad_x=pad_x,
                pad_y=pad_y,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )
        return rect

    # Proxies whose shape is uniform — (id, rect, **kw) or (id, varname,
    # rect, **kw) — are generated below the class body; only widgets with
    # unique signatures are defined inline.

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


# Widgets whose device wrapper takes (id, rect, **kw).
_SIMPLE_PROXY_WIDGETS = (
    "panel",
    "scope",
    "plot",
    "filtergraph",
    "meter",
    "fpic",
    "multislider",
    "adsrui",
    "live_drop",
    "swatch",
    "textedit",
    "live_step",
    "live_grid",
    "live_line",
    "live_arrows",
    "rslider",
    "kslider",
    "nodes",
    "matrixctrl",
    "ubutton",
    "nslider",
    "umenu",
    "radiogroup",
)

# Widgets whose device wrapper takes (id, varname, rect, **kw).
_VARNAME_PROXY_WIDGETS = (
    "dial",
    "toggle",
    "slider",
    "button",
    "number_box",
    "live_text",
    "live_gain",
)


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


for _widget_name in _SIMPLE_PROXY_WIDGETS:
    setattr(_LayoutContainer, f"add_{_widget_name}", _make_simple_proxy(_widget_name))
for _widget_name in _VARNAME_PROXY_WIDGETS:
    setattr(_LayoutContainer, f"add_{_widget_name}", _make_varname_proxy(_widget_name))
del _widget_name


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

    def __enter__(self):
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
        return rect

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

    def __enter__(self):
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
        return rect

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

    def __enter__(self):
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
        return rect


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

    def __enter__(self):
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
        return rect


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
