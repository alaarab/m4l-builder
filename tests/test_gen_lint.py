"""Tests for the GenExpr static linter (m4l_builder.gen_lint)."""
from m4l_builder.gen_lint import lint_genexpr


def test_clean_code_has_no_issues():
    assert lint_genexpr("out1 = in1 * 0.5;\nout2 = in2;", 2, 2) == []


def test_flags_dead_output():
    issues = lint_genexpr("out1 = in1;", 1, 3)
    assert any("out2" in i for i in issues)
    assert any("out3" in i for i in issues)
    assert not any("out1 declared" in i for i in issues)


def test_flags_input_index_past_numins():
    issues = lint_genexpr("out1 = in1 + in3;", 2, 1)
    assert any("in3" in i and "numins=2" in i for i in issues)


def test_flags_output_index_past_numouts():
    issues = lint_genexpr("out1 = in1;\nout4 = in1;", 2, 2)
    assert any("out4" in i for i in issues)


def test_flags_multiline_ternary():
    issues = lint_genexpr("out1 = a > b ?\n   x : y;", 1, 1)
    assert any("ternary" in i for i in issues)


def test_ignores_io_tokens_in_comments():
    # in9 / out9 mentioned only in comments must not trip the index checks
    code = "// conceptually uses in9 and out9\n/* out9 */\nout1 = in1;"
    assert lint_genexpr(code, 1, 1) == []


def test_word_boundaries_on_out_assignment():
    # 'fout1' / 'rout1' are NOT an assignment of out1, so out1 is still dead
    issues = lint_genexpr("fout1 = 3.;\nrout1 = 2.;", 1, 1)
    assert any("out1 declared" in i for i in issues)


def test_passthrough_template_all_outs_flagged():
    # an empty (passthrough) codebox leaves every declared out dead
    issues = lint_genexpr("", 2, 2)
    assert sum("declared" in i for i in issues) == 2
