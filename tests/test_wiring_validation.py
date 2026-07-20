"""Wiring-integrity validation: outlet/inlet index bounds + selector~ range
(it191, scan #5). Max silently drops out-of-range patchlines; these turn that
silent-failure class into a build error."""
from m4l_builder.validation import lint_graph


def _box(box_id, numinlets, numoutlets, text="x"):
    return {"box": {"id": box_id, "maxclass": "newobj", "text": text,
                    "numinlets": numinlets, "numoutlets": numoutlets}}


def _line(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def _codes(boxes, lines):
    return {i.code for i in lint_graph(boxes, lines)}


def test_outlet_index_out_of_range_flagged():
    codes = _codes([_box("a", 1, 1), _box("b", 2, 1)], [_line("a", 2, "b", 0)])
    assert "outlet-index-out-of-range" in codes


def test_inlet_index_out_of_range_flagged():
    codes = _codes([_box("a", 1, 1), _box("b", 2, 1)], [_line("a", 0, "b", 5)])
    assert "inlet-index-out-of-range" in codes


def test_in_range_indices_ok():
    codes = _codes([_box("a", 1, 2), _box("b", 3, 1)], [_line("a", 1, "b", 2)])
    assert "outlet-index-out-of-range" not in codes
    assert "inlet-index-out-of-range" not in codes


def test_selector_initial_out_of_range_flagged():
    codes = _codes([_box("s", 3, 1, text="selector~ 2 5")], [])
    assert "selector-initial-out-of-range" in codes


def test_selector_initial_in_range_ok():
    codes = _codes([_box("s", 3, 1, text="selector~ 2 1")], [])
    assert "selector-initial-out-of-range" not in codes


def test_expr_ternary_flagged():
    # `?:` is a silent parse-error in Max expr -> dead object (shipped in Shard).
    codes = _codes([_box("e", 2, 1, text="expr ($f1 > 0.5) ? 1. : 0.")], [])
    assert "expr-ternary" in codes


def test_expr_tilde_ternary_flagged():
    # whole expr family shares the ternary-less parser.
    codes = _codes([_box("e", 1, 1, text="expr~ $v1 > 0. ? $v1 : 0.")], [])
    assert "expr-ternary" in codes


def test_expr_branchless_ok():
    # the correct rewrite: (cond)*a + (cond==0)*b — no `?`.
    codes = _codes([_box("e", 2, 1,
                         text="expr ($f1 > 0.5)*1. + ($f1 <= 0.5)*0.")], [])
    assert "expr-ternary" not in codes


def test_question_mark_outside_expr_family_ok():
    # a `?` in a non-expr object (e.g. a message/comment) is not an expr ternary.
    codes = _codes([_box("m", 2, 1, text="prepend set is it loaded?")], [])
    assert "expr-ternary" not in codes
