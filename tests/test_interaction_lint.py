"""Interaction-arc lint: dead-live-text + stranded-control (both build-gating)."""

from m4l_builder.amxd import WIRING_INTEGRITY_CODES
from m4l_builder.validation import layout_issues


def _box(**payload):
    return {"box": payload}


def _codes(issues):
    return {i.code for i in issues}


def test_dead_live_text_flags_visible_enable0():
    boxes = [_box(id="btn", maxclass="live.text", presentation=1,
                  presentation_rect=[10, 10, 50, 15], parameter_enable=0)]
    issues = layout_issues(boxes, 300, 168)
    dead = [i for i in issues if i.code == "dead-live-text"]
    assert len(dead) == 1 and dead[0].severity == "error"


def test_dead_live_text_ignores_parked_and_mirrors():
    boxes = [
        # parked at HIDDEN_RECT — deliberate
        _box(id="parked", maxclass="live.text", presentation=1,
             presentation_rect=[900, 900, 1, 1], parameter_enable=0),
        # declared display-only mirror
        _box(id="mirror", maxclass="live.text", presentation=1,
             presentation_rect=[10, 30, 50, 15], parameter_enable=0,
             ignoreclick=1),
        # real param — fine
        _box(id="real", maxclass="live.text", presentation=1,
             presentation_rect=[10, 50, 50, 15], parameter_enable=1),
    ]
    assert "dead-live-text" not in _codes(layout_issues(boxes, 300, 168))


def test_stranded_control_flags_edge_to_park_band():
    boxes = [_box(id="ms_menu", maxclass="live.menu", presentation=1,
                  presentation_rect=[780, 140, 88, 16])]  # 760-wide device
    issues = layout_issues(boxes, 760, 168)
    stranded = [i for i in issues if i.code == "stranded-control"]
    assert len(stranded) == 1 and stranded[0].severity == "error"


def test_stranded_control_ignores_parking_band_and_onscreen():
    boxes = [
        _box(id="parked", maxclass="live.menu", presentation=1,
             presentation_rect=[1100, 8, 88, 16]),      # >=900: parked rail
        _box(id="onscreen", maxclass="live.menu", presentation=1,
             presentation_rect=[420, 152, 52, 15]),
        _box(id="display", maxclass="panel", presentation=1,
             presentation_rect=[800, 8, 60, 16]),        # not interactive
    ]
    assert "stranded-control" not in _codes(layout_issues(boxes, 760, 168))


def test_settings_sidebar_reveal_region_is_reachable():
    # A settings_sidebar setwidths WIDER than the closed width to reveal a
    # populated column — controls in [width, setwidth] are reachable, not
    # stranded, and the wider setwidth is legitimate (region is populated).
    boxes = [
        _box(id="toggle", maxclass="live.text", presentation=1,
             presentation_rect=[3, 2, 14, 14], parameter_enable=1),
        _box(id="reveal", maxclass="message",
             text="setwidth 567"),                          # open -> full
        _box(id="reveal_mini", maxclass="message",
             text="setwidth 503"),                          # closed -> mini
        # a control living in the revealed column (past the 503 closed edge)
        _box(id="side_num", maxclass="live.numbox", presentation=1,
             presentation_rect=[511, 28, 52, 17]),
    ]
    codes = _codes(layout_issues(boxes, 503, 168))
    assert "stranded-control" not in codes
    assert "setwidth-mismatch" not in codes


def test_setwidth_into_empty_region_still_flags_dead_zone():
    # The Pressure-688 bug must still gate: setwidth wider than the layout with
    # NOTHING in the revealed region is a runtime dead zone.
    boxes = [
        _box(id="onscreen", maxclass="live.dial", presentation=1,
             presentation_rect=[20, 20, 41, 35]),
        _box(id="stale_full", maxclass="message", text="setwidth 688"),
    ]
    issues = layout_issues(boxes, 550, 168)
    mismatch = [i for i in issues if i.code == "setwidth-mismatch"]
    assert len(mismatch) == 1 and mismatch[0].severity == "error"


def test_both_codes_gate_builds():
    assert "dead-live-text" in WIRING_INTEGRITY_CODES
    assert "stranded-control" in WIRING_INTEGRITY_CODES
