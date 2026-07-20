"""Tests for the GenExpr static linter (m4l_builder.gen_lint)."""
from m4l_builder.gen_lint import find_function_defs, lint_genexpr


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


# --- find_function_defs: the external-.gendsp silent-function tripwire ---------


def test_fn_defs_simple_definition_is_found():
    assert find_function_defs("mysat(x) { return tanh(x); }\nout1 = mysat(in1);") \
        == ["mysat"]


def test_fn_defs_multiline_def_with_nested_braces():
    code = (
        "chaos_voice(data_ph, idx,\n"
        "            rt, src) {\n"
        "    if (src < 0.5) {\n"
        "        v = 0;\n"
        "    } else {\n"
        "        v = 1;\n"
        "    }\n"
        "    return v;\n"
        "}\n"
        "out1 = chaos_voice(d, 0, rate, s);"
    )
    assert find_function_defs(code) == ["chaos_voice"]


def test_fn_defs_multiple_defs_in_source_order_deduped():
    code = (
        "allpass(x, g, d1, d2) { d1.write(x); return x; }\n"
        "lowpass_12(sig, cf, q) { return sig; }\n"
        "allpass(x, g, d1, d2) { return x; }\n"   # dup name reported once
        "out1 = lowpass_12(allpass(in1, 0.5, a, b), 800, 0.7);"
    )
    assert find_function_defs(code) == ["allpass", "lowpass_12"]


def test_fn_defs_declarations_do_not_match():
    # Param/History/Buffer/Data/Delay decls are `Type name(args);` — no `{`.
    code = (
        "Param threshold(-18., min=-60., max=0.);\n"
        "History env(-90.);\n"
        'Buffer buf_win("hann");\n'
        "Data data_st(8, 6);\n"
        "Delay dl_l(1024);\n"
        "out1 = in1;"
    )
    assert find_function_defs(code) == []


def test_fn_defs_calls_and_plain_statements_do_not_match():
    code = (
        "poke(data, in1, 0, widx);\n"
        "y = clamp(in1, -1., 1.);\n"
        "out1 = mix(in1, y, 0.5);"
    )
    assert find_function_defs(code) == []


def test_fn_defs_control_flow_blocks_do_not_match():
    code = (
        "if (in1 > 0.5) {\n"
        "    y = 1;\n"
        "} else if (in1 < -0.5) {\n"
        "    y = -1;\n"
        "}\n"
        "for (i = 0; i < 4; i += 1) {\n"
        "    y = y * 0.5;\n"
        "}\n"
        "while (y > 1) { y -= 1; }\n"
        "out1 = y;"
    )
    assert find_function_defs(code) == []


def test_fn_defs_inside_function_bodies_are_not_depth0():
    # the nested if-block opener inside the body must not re-trigger; only the
    # single depth-0 def is reported.
    code = (
        "op(freq, fb, trig) {\n"
        "    if (trig) { fbk = 0; }\n"
        "    return fbk;\n"
        "}\n"
        "out1 = op(440, 0.2, 0);"
    )
    assert find_function_defs(code) == ["op"]


def test_fn_defs_ignores_comments_and_strings():
    code = (
        "// fake(x) { in a comment }\n"
        "/* other(y) {\n   block comment\n} */\n"
        'osc = cycle(ph, index = "phase");\n'
        "out1 = osc;"
    )
    assert find_function_defs(code) == []


def test_fn_defs_expression_position_call_is_not_a_def():
    # RHS call followed by an (invalid but conceivable) brace must not match:
    # the identifier sits after '=' (expression position).
    assert find_function_defs("y = weird(x) {") == []


def test_flags_declaration_after_statement():
    from m4l_builder.gen_lint import lint_genexpr
    bad = ("Param a(1.);\n"
           "x = in1 * a;\n"
           "Param b(2.);\n"        # T31: silently kills the kernel in Live
           "out1 = x * b;\n")
    from m4l_builder.gen_lint import lint_param_order
    assert lint_genexpr(bad, 1, 1) == []      # structural lint stays quiet
    issues = lint_param_order(bad)
    assert any("Param declaration after executable code" in i for i in issues)
    # mid-code History is Live-proven fine (Expansion / Plate Reverb)
    ok = ("Param a(1.);\n"
          "x = in1 * a;\n"
          "History h(0.);\n"
          "h = h + 0.1 * (x - h);\n"
          "out1 = h;\n")
    assert lint_genexpr(ok, 1, 1) == []


def test_hoisted_declarations_clean():
    from m4l_builder.gen_lint import lint_genexpr
    good = ("Param a(1.); Param b(2.);\n"
            "History h(0.);\n"
            "h = h + 0.1 * (in1 - h);\n"
            "out1 = h * a * b;\n")
    from m4l_builder.gen_lint import lint_param_order
    assert lint_genexpr(good, 1, 1) == []
    assert lint_param_order(good) == []


def test_denormal_advisory_flags_one_pole_without_fixdenorm():
    from m4l_builder.gen_lint import lint_denormals
    code = ("History lp(0.);\n"
            "lp = lp + 0.001 * (in1 - lp);\n"
            "out1 = lp;\n")
    issues = lint_denormals(code)
    assert issues and "lp" in issues[0]


def test_denormal_advisory_quiet_with_fixdenorm():
    from m4l_builder.gen_lint import lint_denormals
    code = ("History lp(0.);\n"
            "lp = fixdenorm(lp + 0.001 * (in1 - lp));\n"
            "out1 = lp;\n")
    assert lint_denormals(code) == []
