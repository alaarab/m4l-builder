"""Tests for the layout system (Row, Column, Grid, nesting)."""

import pytest

from m4l_builder import AudioEffect, MidiEffect, WARM, Row, Column, Grid


def _find_box(device, box_id):
    """Find a box by its ID in the device's boxes list."""
    for b in device.boxes:
        if b["box"]["id"] == box_id:
            return b["box"]
    raise KeyError(f"No box with id={box_id!r}")


def _rect(device, box_id):
    """Get presentation_rect for a box by ID."""
    return _find_box(device, box_id)["presentation_rect"]


# ---------------------------------------------------------------------------
# Row tests
# ---------------------------------------------------------------------------

class TestRow:
    def test_first_item_at_origin(self):
        d = AudioEffect("T", 400, 200)
        with d.row(10, 30, spacing=8, height=70) as row:
            row.add_dial("d1", "D1", width=50)
        assert _rect(d, "d1") == [10, 30, 50, 70]

    def test_cursor_advances(self):
        d = AudioEffect("T", 400, 200)
        with d.row(10, 30, spacing=8, height=70) as row:
            row.add_dial("d1", "D1", width=50)
            row.add_dial("d2", "D2", width=50)
        assert _rect(d, "d2") == [68, 30, 50, 70]

    def test_three_items(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=10, height=40) as row:
            row.add_dial("d1", "D1", width=30)
            row.add_dial("d2", "D2", width=30)
            row.add_dial("d3", "D3", width=30)
        assert _rect(d, "d1") == [0, 0, 30, 40]
        assert _rect(d, "d2") == [40, 0, 30, 40]
        assert _rect(d, "d3") == [80, 0, 30, 40]

    def test_used_width(self):
        d = AudioEffect("T", 400, 200)
        with d.row(10, 30, spacing=8, height=70) as row:
            row.add_dial("d1", "D1", width=50)
            row.add_dial("d2", "D2", width=50)
            assert row.used_width == 108  # 50+8+50

    def test_used_width_empty(self):
        d = AudioEffect("T", 400, 200)
        with d.row(10, 30, spacing=8) as row:
            assert row.used_width == 0

    def test_used_width_single_item(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=8) as row:
            row.add_dial("d1", "D1", width=60)
            assert row.used_width == 60

    def test_used_height_from_default(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, height=70) as row:
            assert row.used_height == 70

    def test_used_height_no_default(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0) as row:
            assert row.used_height == 0

    def test_per_item_width_override(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.row(10, 30, spacing=8) as row:
            row.add_dial("d1", "D1", width=50, height=70)
            row.add_panel("p1", width=100, height=70)
        assert _rect(d, "p1") == [68, 30, 100, 70]

    def test_per_item_height_override(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=50) as row:
            row.add_dial("d1", "D1", width=40, height=80)
        assert _rect(d, "d1") == [0, 0, 40, 80]

    def test_default_width_used_when_no_override(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, width=60, height=40) as row:
            row.add_dial("d1", "D1")
            row.add_dial("d2", "D2")
        assert _rect(d, "d1") == [0, 0, 60, 40]
        assert _rect(d, "d2") == [64, 0, 60, 40]

    def test_context_manager_returns_self(self):
        d = AudioEffect("T", 400, 200)
        r = d.row(0, 0)
        with r as ctx:
            assert ctx is r

    def test_mixed_widths(self):
        d = AudioEffect("T", 400, 200)
        with d.row(5, 5, spacing=5, height=30) as row:
            row.add_dial("d1", "D1", width=20)
            row.add_dial("d2", "D2", width=40)
            row.add_dial("d3", "D3", width=10)
        assert _rect(d, "d1") == [5, 5, 20, 30]
        assert _rect(d, "d2") == [30, 5, 40, 30]
        assert _rect(d, "d3") == [75, 5, 10, 30]


# ---------------------------------------------------------------------------
# Column tests
# ---------------------------------------------------------------------------

class TestColumn:
    def test_first_item_at_origin(self):
        d = AudioEffect("T", 400, 200)
        with d.column(10, 20, spacing=4, width=100) as col:
            col.add_comment("c1", "Hello", height=16)
        assert _rect(d, "c1") == [10, 20, 100, 16]

    def test_cursor_advances_vertically(self):
        d = AudioEffect("T", 400, 200)
        with d.column(10, 20, spacing=4, width=100) as col:
            col.add_comment("c1", "Hello", height=16)
            col.add_comment("c2", "World", height=16)
        assert _rect(d, "c1") == [10, 20, 100, 16]
        assert _rect(d, "c2") == [10, 40, 100, 16]

    def test_used_height(self):
        d = AudioEffect("T", 400, 200)
        with d.column(0, 0, spacing=4, width=50) as col:
            col.add_dial("d1", "D1", height=30)
            col.add_dial("d2", "D2", height=30)
            assert col.used_height == 64  # 30+4+30

    def test_used_height_empty(self):
        d = AudioEffect("T", 400, 200)
        with d.column(0, 0) as col:
            assert col.used_height == 0

    def test_used_width_from_default(self):
        d = AudioEffect("T", 400, 200)
        with d.column(0, 0, width=120) as col:
            assert col.used_width == 120

    def test_used_width_no_default(self):
        d = AudioEffect("T", 400, 200)
        with d.column(0, 0) as col:
            assert col.used_width == 0

    def test_per_item_height_override(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.column(0, 0, spacing=4, width=80) as col:
            col.add_panel("p1", height=20)
            col.add_panel("p2", height=40)
        assert _rect(d, "p1") == [0, 0, 80, 20]
        assert _rect(d, "p2") == [0, 24, 80, 40]

    def test_default_height_used(self):
        d = AudioEffect("T", 400, 200)
        with d.column(0, 0, spacing=2, width=60, height=25) as col:
            col.add_dial("d1", "D1")
            col.add_dial("d2", "D2")
        assert _rect(d, "d1") == [0, 0, 60, 25]
        assert _rect(d, "d2") == [0, 27, 60, 25]

    def test_context_manager_returns_self(self):
        d = AudioEffect("T", 400, 200)
        c = d.column(0, 0)
        with c as ctx:
            assert ctx is c


# ---------------------------------------------------------------------------
# Grid tests
# ---------------------------------------------------------------------------

class TestGrid:
    def test_first_item_at_origin(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(10, 20, cols=3, col_width=40, row_height=40) as grid:
            grid.add_dial("d1", "D1")
        assert _rect(d, "d1") == [10, 20, 40, 40]

    def test_items_fill_left_to_right(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=3, col_width=30, row_height=30, spacing_x=5) as grid:
            grid.add_dial("d1", "D1")
            grid.add_dial("d2", "D2")
            grid.add_dial("d3", "D3")
        assert _rect(d, "d1") == [0, 0, 30, 30]
        assert _rect(d, "d2") == [35, 0, 30, 30]
        assert _rect(d, "d3") == [70, 0, 30, 30]

    def test_wraps_at_cols(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(10, 30, cols=4, col_width=40, row_height=80, spacing_x=4, spacing_y=4) as grid:
            for i in range(5):
                grid.add_slider(f"s{i}", f"S{i}")
        # 5th item should wrap to second row, first column
        assert _rect(d, "s4")[0] == 10
        assert _rect(d, "s4")[1] == 30 + 80 + 4

    def test_full_row_then_wrap(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=2, col_width=50, row_height=50, spacing_x=10, spacing_y=10) as grid:
            grid.add_dial("d1", "D1")
            grid.add_dial("d2", "D2")
            grid.add_dial("d3", "D3")
        assert _rect(d, "d1") == [0, 0, 50, 50]
        assert _rect(d, "d2") == [60, 0, 50, 50]
        assert _rect(d, "d3") == [0, 60, 50, 50]

    def test_used_width(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=3, col_width=40, row_height=40, spacing_x=5) as grid:
            grid.add_dial("d1", "D1")
            grid.add_dial("d2", "D2")
            assert grid.used_width == 85  # 40+5+40

    def test_used_width_full_row(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=3, col_width=40, row_height=40, spacing_x=5) as grid:
            for i in range(4):
                grid.add_dial(f"d{i}", f"D{i}")
            # 4 items, cols=3 -> full first row, 1 in second
            assert grid.used_width == 130  # 3*(40) + 2*(5)

    def test_used_height_single_row(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=4, col_width=30, row_height=30, spacing_y=5) as grid:
            grid.add_dial("d1", "D1")
            grid.add_dial("d2", "D2")
            assert grid.used_height == 30

    def test_used_height_two_rows(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=2, col_width=30, row_height=30, spacing_y=5) as grid:
            for i in range(3):
                grid.add_dial(f"d{i}", f"D{i}")
            assert grid.used_height == 65  # 30+5+30

    def test_used_height_exact_fill(self):
        d = AudioEffect("T", 400, 200)
        with d.grid(0, 0, cols=2, col_width=30, row_height=30, spacing_y=5) as grid:
            for i in range(4):
                grid.add_dial(f"d{i}", f"D{i}")
            # 4 items, cols=2 -> 2 full rows, current_col=0, current_row=2
            assert grid.used_height == 65  # 30+5+30

    def test_context_manager_returns_self(self):
        d = AudioEffect("T", 400, 200)
        g = d.grid(0, 0, cols=2, col_width=30, row_height=30)
        with g as ctx:
            assert ctx is g


# ---------------------------------------------------------------------------
# Nested container tests
# ---------------------------------------------------------------------------

class TestNestedContainers:
    def test_row_inside_column(self):
        d = AudioEffect("T", 400, 200)
        with d.column(10, 30, spacing=4, width=200) as col:
            col.add_comment("title", "FILTER", height=16)
            with col.row(spacing=8, height=70) as row:
                row.add_dial("d1", "Freq", width=50)
                row.add_dial("d2", "Res", width=50)
            col.add_slider("s1", "Mix", height=20)
        # title at y=30
        assert _rect(d, "title") == [10, 30, 200, 16]
        # row starts at y=30+16+4=50
        assert _rect(d, "d1") == [10, 50, 50, 70]
        assert _rect(d, "d2") == [68, 50, 50, 70]
        # slider at y=50+70+4=124
        assert _rect(d, "s1") == [10, 124, 200, 20]

    def test_column_inside_row(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.row(0, 0, spacing=10, height=60) as row:
            with row.column(spacing=2, width=40) as col:
                col.add_dial("d1", "A", height=28)
                col.add_dial("d2", "B", height=28)
            row.add_panel("p1", width=80, height=60)
        # column items
        assert _rect(d, "d1") == [0, 0, 40, 28]
        assert _rect(d, "d2") == [0, 30, 40, 28]
        # panel after column: x = 0 + 40 + 10 = 50
        assert _rect(d, "p1") == [50, 0, 80, 60]

    def test_nested_row_advances_parent_cursor(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.column(0, 0, spacing=4, width=100) as col:
            with col.row(spacing=4, height=30) as row:
                row.add_dial("d1", "D1", width=40)
            # After the row exits, column cursor should have advanced
            col.add_panel("p1", height=20)
        # row height=30, spacing=4, so panel at y=34
        assert _rect(d, "p1") == [0, 34, 100, 20]

    def test_nested_column_advances_parent_cursor(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=8) as row:
            with row.column(spacing=2, width=50) as col:
                col.add_dial("d1", "D1", height=30)
            row.add_dial("d2", "D2", width=40, height=30)
        # column width=50, spacing=8, so d2 at x=58
        assert _rect(d, "d2") == [58, 0, 40, 30]

    def test_deeply_nested(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.column(0, 0, spacing=4, width=200) as col:
            with col.row(spacing=8, height=50) as row:
                with row.column(spacing=2, width=30) as inner_col:
                    inner_col.add_dial("d1", "A", height=22)
                    inner_col.add_dial("d2", "B", height=22)
                row.add_panel("p1", width=60, height=50)
        assert _rect(d, "d1") == [0, 0, 30, 22]
        assert _rect(d, "d2") == [0, 24, 30, 22]
        # panel after inner column: x = 0 + 30 + 8 = 38
        assert _rect(d, "p1") == [38, 0, 60, 50]


# ---------------------------------------------------------------------------
# Proxy method tests
# ---------------------------------------------------------------------------

class TestProxyMethods:
    def test_pattern_a_panel(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.row(0, 0, spacing=4, height=40) as row:
            row.add_panel("p1", width=80)
        assert _rect(d, "p1") == [0, 0, 80, 40]

    def test_pattern_a_scope(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_scope("sc1", width=100)
        assert _rect(d, "sc1") == [0, 0, 100, 60]

    def test_pattern_a_meter(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=80) as row:
            row.add_meter("m1", width=20)
        assert _rect(d, "m1") == [0, 0, 20, 80]

    def test_pattern_a_fpic(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=40) as row:
            row.add_fpic("f1", width=50)
        assert _rect(d, "f1") == [0, 0, 50, 40]

    def test_pattern_a_multislider(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_multislider("ms1", width=100)
        assert _rect(d, "ms1") == [0, 0, 100, 60]

    def test_pattern_a_adsrui(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_adsrui("adsr1", width=120)
        assert _rect(d, "adsr1") == [0, 0, 120, 60]

    def test_pattern_a_live_drop(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=40) as row:
            row.add_live_drop("ld1", width=80)
        assert _rect(d, "ld1") == [0, 0, 80, 40]

    def test_pattern_a_swatch(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=40) as row:
            row.add_swatch("sw1", width=50)
        assert _rect(d, "sw1") == [0, 0, 50, 40]

    def test_pattern_a_textedit(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_textedit("te1", width=100)
        assert _rect(d, "te1") == [0, 0, 100, 20]

    def test_pattern_a_live_step(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=80) as row:
            row.add_live_step("ls1", width=200)
        assert _rect(d, "ls1") == [0, 0, 200, 80]

    def test_pattern_a_live_grid(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=80) as row:
            row.add_live_grid("lg1", width=200)
        assert _rect(d, "lg1") == [0, 0, 200, 80]

    def test_pattern_a_live_line(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=40) as row:
            row.add_live_line("ll1", width=200)
        assert _rect(d, "ll1") == [0, 0, 200, 40]

    def test_pattern_a_live_arrows(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_live_arrows("la1", width=20)
        assert _rect(d, "la1") == [0, 0, 20, 20]

    def test_pattern_a_rslider(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=40) as row:
            row.add_rslider("rs1", width=100)
        assert _rect(d, "rs1") == [0, 0, 100, 40]

    def test_pattern_a_kslider(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_kslider("ks1", width=200)
        assert _rect(d, "ks1") == [0, 0, 200, 60]

    def test_pattern_a_nodes(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_nodes("n1", width=100)
        assert _rect(d, "n1") == [0, 0, 100, 60]

    def test_pattern_a_matrixctrl(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_matrixctrl("mx1", width=100)
        assert _rect(d, "mx1") == [0, 0, 100, 60]

    def test_pattern_a_ubutton(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=30) as row:
            row.add_ubutton("ub1", width=40)
        assert _rect(d, "ub1") == [0, 0, 40, 30]

    def test_pattern_a_nslider(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_nslider("ns1", width=50)
        assert _rect(d, "ns1") == [0, 0, 50, 60]

    def test_pattern_g_umenu(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_umenu("um1", width=100)
        assert _rect(d, "um1") == [0, 0, 100, 20]

    def test_pattern_g_radiogroup(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=60) as row:
            row.add_radiogroup("rg1", width=40)
        assert _rect(d, "rg1") == [0, 0, 40, 60]

    def test_pattern_b_dial(self):
        d = AudioEffect("T", 400, 200)
        with d.column(0, 0, spacing=4, width=50) as col:
            col.add_dial("d1", "Freq", height=50)
        assert _rect(d, "d1") == [0, 0, 50, 50]

    def test_pattern_b_toggle(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_toggle("t1", "Toggle1", width=20)
        assert _rect(d, "t1") == [0, 0, 20, 20]

    def test_pattern_b_slider(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_slider("sl1", "Slider1", width=100)
        assert _rect(d, "sl1") == [0, 0, 100, 20]

    def test_pattern_b_button(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_button("b1", "Button1", width=20)
        assert _rect(d, "b1") == [0, 0, 20, 20]

    def test_pattern_b_number_box(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_number_box("nb1", "NumBox", width=50)
        assert _rect(d, "nb1") == [0, 0, 50, 20]

    def test_pattern_b_live_text(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_live_text("lt1", "LText", width=60)
        assert _rect(d, "lt1") == [0, 0, 60, 20]

    def test_pattern_b_live_gain(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=100) as row:
            row.add_live_gain("lg1", "LGain", width=30)
        assert _rect(d, "lg1") == [0, 0, 30, 100]

    def test_pattern_c_comment(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=16) as row:
            row.add_comment("c1", "Hello World", width=80)
        assert _rect(d, "c1") == [0, 0, 80, 16]

    def test_pattern_d_menu(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=20) as row:
            row.add_menu("m1", "MenuVar", ["A", "B", "C"], width=80)
        assert _rect(d, "m1") == [0, 0, 80, 20]

    def test_pattern_d_tab(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=24) as row:
            row.add_tab("t1", "TabVar", ["Tab1", "Tab2"], width=120)
        assert _rect(d, "t1") == [0, 0, 120, 24]

    def test_pattern_e_textbutton(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=24) as row:
            row.add_textbutton("tb1", "Click Me", width=80)
        assert _rect(d, "tb1") == [0, 0, 80, 24]

    def test_pattern_e_textbutton_default_text(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=24) as row:
            row.add_textbutton("tb1", width=80)
        box = _find_box(d, "tb1")
        assert box["presentation_rect"] == [0, 0, 80, 24]

    def test_pattern_f_jsui(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=80) as row:
            row.add_jsui("js1", js_code="// test js", width=200, validate_contract=False)
        assert _rect(d, "js1") == [0, 0, 200, 80]

    def test_bpatcher(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=100) as row:
            row.add_bpatcher("bp1", "my_patcher", width=150)
        assert _rect(d, "bp1") == [0, 0, 150, 100]

    def test_kwargs_passthrough(self):
        d = AudioEffect("T", 400, 200)
        with d.row(0, 0, spacing=4, height=50) as row:
            row.add_dial("d1", "D1", width=50, min_val=20, max_val=20000, unitstyle=3)
        box = _find_box(d, "d1")
        assert box["presentation_rect"] == [0, 0, 50, 50]

    def test_theme_passthrough(self):
        d = AudioEffect("T", 400, 200, theme=WARM)
        with d.row(0, 0, spacing=4, height=50) as row:
            row.add_dial("d1", "D1", width=50)
        # Just check it got placed without error (theme injection happens in Device)
        assert _rect(d, "d1") == [0, 0, 50, 50]


# ---------------------------------------------------------------------------
# Device method tests
# ---------------------------------------------------------------------------

class TestDeviceMethods:
    def test_device_has_row_method(self):
        d = AudioEffect("T", 400, 200)
        assert hasattr(d, "row")

    def test_device_has_column_method(self):
        d = AudioEffect("T", 400, 200)
        assert hasattr(d, "column")

    def test_device_has_grid_method(self):
        d = AudioEffect("T", 400, 200)
        assert hasattr(d, "grid")

    def test_midi_effect_has_layout_methods(self):
        d = MidiEffect("T", 400, 200)
        assert hasattr(d, "row")
        assert hasattr(d, "column")
        assert hasattr(d, "grid")

    def test_device_row_returns_row(self):
        d = AudioEffect("T", 400, 200)
        r = d.row(0, 0)
        assert isinstance(r, Row)

    def test_device_column_returns_column(self):
        d = AudioEffect("T", 400, 200)
        c = d.column(0, 0)
        assert isinstance(c, Column)

    def test_device_grid_returns_grid(self):
        d = AudioEffect("T", 400, 200)
        g = d.grid(0, 0, cols=3, col_width=40, row_height=40)
        assert isinstance(g, Grid)

    def test_device_row_spacing_kwarg(self):
        d = AudioEffect("T", 400, 200)
        with d.row(10, 20, spacing=12, height=50) as row:
            row.add_dial("d1", "D1", width=30)
            row.add_dial("d2", "D2", width=30)
        assert _rect(d, "d2") == [52, 20, 30, 50]  # 10+30+12=52

    def test_device_column_spacing_kwarg(self):
        d = AudioEffect("T", 400, 200)
        with d.column(5, 10, spacing=6, width=40) as col:
            col.add_dial("d1", "D1", height=20)
            col.add_dial("d2", "D2", height=20)
        assert _rect(d, "d2") == [5, 36, 40, 20]  # 10+20+6=36


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------

class TestImports:
    def test_row_importable_from_package(self):
        from m4l_builder import Row
        assert Row is not None

    def test_column_importable_from_package(self):
        from m4l_builder import Column
        assert Column is not None

    def test_grid_importable_from_package(self):
        from m4l_builder import Grid
        assert Grid is not None
