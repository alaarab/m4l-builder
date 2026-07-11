"""Surface layout engine (UI Foundations v2) — pure-Python rect/graph tests."""

import pytest

from m4l_builder import AudioEffect
from m4l_builder import native_sizes as ns
from m4l_builder.surface import BAND_Y, Surface, SurfaceError
from m4l_builder.theme import ACCENTS, GRAPHITE


def _device():
    # width=1 placeholder: Surface.finalize() derives + assigns the real width.
    return AudioEffect("surftest", width=1, height=168, theme=GRAPHITE)


def _box(device, box_id):
    for entry in device.boxes:
        box = entry.get("box", {})
        if box.get("id") == box_id:
            return box
    raise AssertionError(f"no box {box_id!r}")


def _presentation_boxes(device):
    out = []
    for entry in device.boxes:
        box = entry.get("box", {})
        if box.get("presentation") and box.get("presentation_rect"):
            out.append(box)
    return out


class TestWidthDerivation:
    def test_hero_plus_sections_width(self):
        d = _device()
        s = Surface(d, accent="pressure")
        s.hero("h", width=300)
        sec2 = s.section("a", "ONE", cols=2)
        sec4 = s.section("b", "TWO", cols=4)
        w = s.finalize()
        # margin + hero + gap + sec2 + gap + sec4 + margin
        exp_sec2 = 16 + 1 * ns.COL_PITCH + ns.CELL_W
        exp_sec4 = 16 + 3 * ns.COL_PITCH + ns.CELL_W
        assert sec2.width == exp_sec2 and sec4.width == exp_sec4
        assert w == 8 + 300 + 6 + exp_sec2 + 6 + exp_sec4 + 8
        assert d.width == w

    def test_finalize_patches_bg_panel_and_is_idempotent(self):
        d = _device()
        s = Surface(d, accent="strip")
        s.section("a", None, cols=2)
        w1 = s.finalize()
        assert _box(d, "surf_bg")["presentation_rect"] == [0, 0, w1, 168]
        assert s.finalize() == w1  # idempotent
        with pytest.raises(SurfaceError):
            s.section("late", None, cols=1)

    def test_width_collapse_defaults_to_derived_width(self):
        d = _device()
        s = Surface(d, accent="strip")
        s.section("a", None, cols=3)
        w = s.finalize()
        d.add_width_collapse(mini_width=120, rect=[12, 1, 42, 9])
        full_msg = _box(d, "width_collapse_msgfull")
        assert full_msg["text"] == f"setwidth {w}"


class TestCompositionRules:
    def test_more_than_max_rows_raises(self):
        s = Surface(_device(), accent="pressure")
        with pytest.raises(SurfaceError):
            s.section("a", None, cols=2, rows=ns.MAX_VALUE_ROWS + 1)

    def test_overfill_raises(self):
        s = Surface(_device(), accent="pressure")
        sec = s.section("a", None, cols=1, rows=2)
        sec.dial("P1")
        sec.dial("P2")
        with pytest.raises(SurfaceError):
            sec.dial("P3")

    def test_pinned_cell_collision_raises(self):
        s = Surface(_device(), accent="pressure")
        sec = s.section("a", None, cols=2, rows=2)
        sec.dial("P1", at=(0, 0))
        with pytest.raises(SurfaceError):
            sec.dial("P2", at=(0, 0))


class TestCellGeometry:
    def test_cells_inside_band_and_integer_rects(self):
        d = _device()
        s = Surface(d, accent="heat")
        sec = s.section("a", "TITLE", cols=3, rows=3)
        for i in range(9):
            sec.dial(f"P{i}", min_val=0, max_val=1, initial=0)
        s.finalize()
        band_bottom = BAND_Y + s.band_h
        for box in _presentation_boxes(d):
            r = box["presentation_rect"]
            assert all(float(v) == int(v) for v in r), (box["id"], r)
            if box.get("maxclass") == "live.dial":
                assert r[1] >= BAND_Y
                assert r[1] + r[3] <= band_bottom, (box["id"], r)

    def test_column_major_fill_and_no_dial_overlap(self):
        d = _device()
        s = Surface(d, accent="heat")
        sec = s.section("a", None, cols=2, rows=3)
        r_first = sec.dial("P0")["rect"]
        r_second = sec.dial("P1")["rect"]
        r_fourth_col2 = [sec.dial(f"P{i}")["rect"] for i in (2, 3)][-1]
        # column-major: P1 sits BELOW P0 (same x), P3 starts the second column
        assert r_second[0] == r_first[0] and r_second[1] > r_first[1]
        assert r_fourth_col2[0] > r_first[0]
        # cells never intersect (rect = caption+dial extent)
        rects = [r_first, r_second, r_fourth_col2]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                x_overlap = a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                y_overlap = a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
                assert not (x_overlap and y_overlap), (a, b)

    def test_persistent_value_dial_kwargs(self):
        d = _device()
        s = Surface(d, accent="pressure")
        sec = s.section("a", None, cols=1, rows=1)
        res = sec.dial("Threshold", "THRESH", min_val=-60, max_val=0, initial=0)
        box = _box(d, res["dial"])
        assert box["shownumber"] == 1          # persistent value — the P2 rule
        assert box["showname"] == 0
        assert "valuepopup" not in box
        assert box["presentation_rect"][2:] == list(ns.DIAL_COMPACT)

    def test_probe_parks_off_canvas(self):
        d = _device()
        s = Surface(d, accent="pressure")
        s.probe("grp", "GRProbe", min_val=0, max_val=60, initial=0)
        assert _box(d, "grp")["presentation_rect"] == ns.PARK_RECT
        # DSP-driven probe dials must be Parameter-Visibility HIDDEN (2): parked
        # AND kept out of Live automation / MIDI-map / Push and the undo stack.
        vo = _box(d, "grp")["saved_attribute_attributes"]["valueof"]
        assert vo["parameter_invisible"] == 2


class TestThemeBus:
    def test_follow_live_emits_brand_dim_bus_and_receiver_fanout(self):
        d = _device()
        s = Surface(d, accent="pressure")
        sec = s.section("a", None, cols=2, rows=2)
        ids = [sec.dial(f"P{i}")["dial"] for i in range(4)]
        s.finalize()
        assert _box(d, "surfacc_rx")["text"] == "r ---surfacc"
        assert _box(d, "surfacc_dim_td")["text"] == "live.thisdevice"
        # brand accent baked into the enabled-path message
        acc = ACCENTS["pressure"]
        exp = " ".join(f"{float(c):g}" for c in acc)
        assert _box(d, "surfacc_dim_mact")["text"] == exp
        # one receiver fans to every dial
        fan = [ln for ln in d.lines
               if ln["patchline"]["source"][0] == "surfacc_rx"]
        assert {ln["patchline"]["destination"][0] for ln in fan} == set(ids)

    def test_follow_live_false_emits_no_bus(self):
        d = _device()
        s = Surface(d, accent="pressure", follow_live=False)
        sec = s.section("a", None, cols=1, rows=1)
        sec.dial("P0")
        s.finalize()
        with pytest.raises(AssertionError):
            _box(d, "surfacc_rx")

    def test_accent2_cells_get_their_own_bus(self):
        d = _device()
        s = Surface(d, accent="sheen", accent2=[0.96, 0.55, 0.22, 1.0])
        sec = s.section("a", None, cols=2, rows=1)
        sec.dial("Hi")
        sec.dial("Lo", accent2=True)
        s.finalize()
        assert _box(d, "surfacc_rx")["text"] == "r ---surfacc"
        assert _box(d, "surfacc2_rx")["text"] == "r ---surfacc2"


class TestOtherCells:
    def test_toggle_menu_numbox_cells_build(self):
        d = _device()
        s = Surface(d, accent="aurora")
        sec = s.section("a", "RAIL", cols=1, rows=3, material="rail")
        tid = sec.toggle("Freeze", on="FREEZE", off="OFF")
        mid = sec.menu("Filter", ["LP", "HP", "BP"])
        nid = sec.numbox_lcd("Amount", min_val=0, max_val=100, initial=50)
        assert _box(d, tid)["maxclass"] == "live.text"
        assert _box(d, mid)["maxclass"] == "live.menu"
        nbox = _box(d, nid)
        assert nbox["presentation_rect"][2:] == list(ns.NUMBOX_LCD)

    def test_device_builds_to_bytes(self):
        # end-to-end: the composed patcher serializes without validation errors
        d = _device()
        s = Surface(d, accent="pressure")
        h = s.hero("h", width=200)
        assert h.rect[2] == 196
        sec = s.section("a", "COMP", cols=2)
        sec.dial("Threshold", min_val=-60, max_val=0, initial=0)
        sec.toggle("Bypass")
        s.finalize()
        data = d.to_bytes()
        assert len(data) > 1000


class TestLayoutLint:
    def test_surface_device_lints_clean(self):
        d = _device()
        s = Surface(d, accent="pressure")
        s.hero("h", width=200)
        sec = s.section("a", "COMP", cols=3)
        for i in range(6):
            sec.dial(f"P{i}")
        s.finalize()
        codes = {i.code for i in d.lint()}
        assert "control-overlap" not in codes
        assert "dead-zone" not in codes
        assert "width-mismatch" not in codes
        assert "setwidth-mismatch" not in codes

    def test_dead_zone_and_width_mismatch_detected(self):
        d = _device()
        s = Surface(d, accent="pressure")
        sec = s.section("a", None, cols=2)
        sec.dial("P0")
        s.finalize()
        d.width = d.width + 160          # simulate the stale-width bug class
        codes = {i.code for i in d.lint()}
        assert "dead-zone" in codes and "width-mismatch" in codes

    def test_setwidth_wider_than_device_is_error(self):
        d = _device()
        s = Surface(d, accent="pressure")
        sec = s.section("a", None, cols=2)
        sec.dial("P0")
        w = s.finalize()
        d.add_width_collapse(full_width=w + 138, mini_width=100,
                             rect=[12, 1, 42, 9])
        issues = [i for i in d.lint() if i.code == "setwidth-mismatch"]
        assert issues and issues[0].severity == "error"

    def test_overlapping_dials_detected(self):
        d = AudioEffect("overlap", width=200, height=168, theme=GRAPHITE)
        d.add_dial("a", "PA", [20, 20, 41, 35], min_val=0, max_val=1, initial=0)
        d.add_dial("b", "PB", [30, 30, 41, 35], min_val=0, max_val=1, initial=0)
        codes = {i.code for i in d.lint()}
        assert "control-overlap" in codes


class TestBrandDimHelper:
    def test_add_brand_dim_wires_bus_and_fanout(self):
        d = AudioEffect("bd", width=300, height=168, theme=GRAPHITE)
        d.add_dial("a", "PA", [20, 20, 41, 35], min_val=0, max_val=1, initial=0)
        d.add_dial("b", "PB", [80, 20, 41, 35], min_val=0, max_val=1, initial=0)
        bus = d.add_brand_dim([0.9, 0.5, 0.1, 1.0], ["a", "b"])
        assert bus == "brandacc"
        assert _box(d, "brandacc_rx")["text"] == "r ---brandacc"
        assert _box(d, "brandacc_dim_mact")["text"] == "0.9 0.5 0.1 1"
        fan = {ln["patchline"]["destination"][0] for ln in d.lines
               if ln["patchline"]["source"][0] == "brandacc_rx"}
        assert fan == {"a", "b"}


def test_surface_reserve_advances_width():
    device = AudioEffect("Reserve Test", width=1, height=168)
    surf = Surface(device, accent=ACCENTS["strip"])
    x0 = surf.reserve(344)
    x1 = surf.reserve(50)
    assert x1 == x0 + 344 + surf.gap
    width = surf.finalize()
    assert width == x1 + 50 + surf.margin
