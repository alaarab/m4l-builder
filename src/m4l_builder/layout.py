"""Context manager-based layout containers for placing UI elements."""


class _LayoutContainer:
    """Mixin providing proxy add_* methods that auto-compute rects."""

    def _next_rect(self, width=None, height=None):
        raise NotImplementedError

    # Pattern A: (id, rect, **kw)
    def add_panel(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_panel(id, rect, **kw)

    def add_scope(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_scope(id, rect, **kw)

    def add_meter(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_meter(id, rect, **kw)

    def add_fpic(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_fpic(id, rect, **kw)

    def add_multislider(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_multislider(id, rect, **kw)

    def add_adsrui(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_adsrui(id, rect, **kw)

    def add_live_drop(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_drop(id, rect, **kw)

    def add_swatch(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_swatch(id, rect, **kw)

    def add_textedit(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_textedit(id, rect, **kw)

    def add_live_step(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_step(id, rect, **kw)

    def add_live_grid(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_grid(id, rect, **kw)

    def add_live_line(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_line(id, rect, **kw)

    def add_live_arrows(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_arrows(id, rect, **kw)

    def add_rslider(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_rslider(id, rect, **kw)

    def add_kslider(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_kslider(id, rect, **kw)

    def add_nodes(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_nodes(id, rect, **kw)

    def add_matrixctrl(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_matrixctrl(id, rect, **kw)

    def add_ubutton(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_ubutton(id, rect, **kw)

    def add_nslider(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_nslider(id, rect, **kw)

    # Pattern G: same as A
    def add_umenu(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_umenu(id, rect, **kw)

    def add_radiogroup(self, id, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_radiogroup(id, rect, **kw)

    # Pattern B: (id, varname, rect, **kw)
    def add_dial(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_dial(id, varname, rect, **kw)

    def add_toggle(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_toggle(id, varname, rect, **kw)

    def add_slider(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_slider(id, varname, rect, **kw)

    def add_button(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_button(id, varname, rect, **kw)

    def add_number_box(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_number_box(id, varname, rect, **kw)

    def add_live_text(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_text(id, varname, rect, **kw)

    def add_live_gain(self, id, varname, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_live_gain(id, varname, rect, **kw)

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

    # bpatcher: (id, rect, patcher_name, **kw)
    def add_bpatcher(self, id, patcher_name, *, width=None, height=None, **kw):
        rect = self._next_rect(width, height)
        return self._device.add_bpatcher(id, rect, patcher_name, **kw)


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

    def _next_rect(self, width=None, height=None):
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

    def _next_rect(self, width=None, height=None):
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

    def _next_rect(self, width=None, height=None):
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
