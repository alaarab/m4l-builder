"""Native sizing tiers measured from the commercial corpus."""

from m4l_builder import native_sizes as ns


def test_premium_tiers_present_and_correct():
    assert ns.DIAL_COMPACT == (41, 35)   # the corpus workhorse (38/82 dials)
    assert ns.DIAL_RAIL == (41, 48)
    assert ns.DIAL_LCD == (51, 63)
    assert ns.NUMBOX_MINI == (17, 15)
    assert ns.VSLIDER_NATIVE == (22, 113)
    assert ns.TAB_BAR_H == 20
    assert ns.TEXT_ICON == (15, 15)


def test_knob_row_fit_spreads_to_width_with_margins():
    rects = ns.knob_row_fit(0, 24, 3, 174)
    assert len(rects) == 3
    assert rects[0][0] == ns.FRAME_MARGIN              # left margin
    assert rects[-1][0] + rects[-1][2] == 174 - ns.FRAME_MARGIN  # right margin
    assert all(r[2:] == [41, 35] for r in rects)       # DIAL_COMPACT default


def test_knob_row_fit_single_knob():
    rects = ns.knob_row_fit(0, 0, 1, 100)
    assert rects == [[ns.FRAME_MARGIN, 0, 41, 35]]


def test_knob_row_defaults_to_dial_compact():
    # knob_row must default to the premium DIAL_COMPACT (41x35), matching knob_row_fit
    # — not the deprecated DIAL (44,47) guess.
    rects = ns.knob_row(10, 20, 3)
    assert all(r[2:] == [41, 35] for r in rects)
    assert rects[0][:2] == [10, 20]
    assert rects[1][0] - rects[0][0] == ns.KNOB_PITCH   # spacing unchanged


def test_knob_row_size_override():
    rects = ns.knob_row(0, 0, 2, size=ns.DIAL_HERO)
    assert all(r[2:] == [48, 50] for r in rects)


def test_knob_column_fits_four_without_overlap():
    cells = ns.knob_column(360, 6, 4)
    assert len(cells) == 4
    for lbl, dial in cells:
        assert lbl[2] == 40 and lbl[3] == ns.KNOB_LABEL_H   # caption rect
        assert dial[0] == lbl[0]                            # dial under its label
    # each cell's dial must END at or before the NEXT cell's label (the Pressure
    # collision was the dial value overflowing into the label below).
    for i in range(3):
        dial_bottom = cells[i][1][1] + cells[i][1][3]
        next_label_top = cells[i + 1][0][1]
        assert dial_bottom <= next_label_top
    # the whole column stays within the device band (6 + 156 = 162 < 168)
    last_dial = cells[-1][1]
    assert last_dial[1] + last_dial[3] <= 6 + ns.DENSE_COL_H


def test_toggle_column_cells_within_band_and_no_overlap():
    cells = ns.toggle_column(492, 6, 4)
    assert len(cells) == 4
    for lbl, btn in cells:
        assert lbl[2] == 48 and btn[2] == 48          # wider for ACTIVE/BYPASSED text
        assert 14 <= btn[3] <= 18
    for i in range(3):
        assert cells[i][1][1] + cells[i][1][3] <= cells[i + 1][0][1]
    assert cells[-1][1][1] + cells[-1][1][3] <= 6 + ns.DENSE_COL_H


# ── Surface cell-grammar tokens (Phase 1, UI Foundations v2) ─────────────────

def test_value_cell_height_invariant():
    # A persistent-value cell = caption + gap + DIAL_COMPACT (value renders
    # INSIDE the dial rect via shownumber=1, so the dial height is the cell floor).
    assert ns.VALUE_CELL_H == ns.CAPTION_H + ns.CAPTION_GAP + ns.DIAL_COMPACT[1]


def test_max_value_rows_fit_dense_band_with_header():
    # 3 persistent-value rows + a section header must fit the 156px column band;
    # 4 rows must NOT (that is the valuepopup-era layout we retired).
    assert ns.MAX_VALUE_ROWS * ns.VALUE_CELL_H + ns.SECTION_HEADER_H <= ns.DENSE_COL_H
    assert (ns.MAX_VALUE_ROWS + 1) * ns.VALUE_CELL_H > ns.DENSE_COL_H


def test_col_pitch_clears_cell_width_dial():
    # Columns at COL_PITCH must not overlap 41-wide dials (>= 4px gutter... the
    # corpus gap is ~7 on a 41-wide dial at pitch 48).
    assert ns.COL_PITCH >= ns.DIAL_COMPACT[0] + 4
    assert ns.CELL_W >= ns.DIAL_COMPACT[0]


def test_park_rect_is_far_off_canvas():
    x, y, w, h = ns.PARK_RECT
    assert x >= 900 and y >= 900 and w <= 1 and h <= 1


def test_alpha_tiers_descend_from_opaque():
    assert ns.ALPHA_TIERS[0] == 1.0
    assert list(ns.ALPHA_TIERS) == sorted(ns.ALPHA_TIERS, reverse=True)


def test_typography_tokens():
    assert ns.CAPTION_FONTSIZE == 7.5
    assert ns.HEADER_FONTSIZE == ns.LABEL_FONTSIZE_PRIMARY == 9.5
    assert ns.FONTNAME == "Ableton Sans Medium"
