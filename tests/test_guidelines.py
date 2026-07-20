"""Ableton production-standards linter (m4l_builder.guidelines)."""
from m4l_builder import AudioEffect
from m4l_builder.guidelines import (
    _edit_distance_le_1,
    check_guidelines,
    js_style_issues,
    parameter_name_issues,
    unknown_object_issues,
)


class TestEditDistance:
    def test_equal_and_within_one(self):
        assert _edit_distance_le_1("cycle~", "cycle~")      # 0
        assert _edit_distance_le_1("cycl~", "cycle~")       # insertion
        assert _edit_distance_le_1("cyclee~", "cycle~")     # deletion
        assert _edit_distance_le_1("cycla~", "cycle~")      # substitution

    def test_over_one(self):
        assert not _edit_distance_le_1("cyc~", "cycle~")    # 2 deletions
        assert not _edit_distance_le_1("scope~", "cycle~")  # far
        assert not _edit_distance_le_1("metro", "cycle~")


class TestUnknownObject:
    def _dev_with(self, obj_text):
        d = AudioEffect("UT", width=200, height=120)
        d.add_newobj("x", obj_text, numinlets=1, numoutlets=1, outlettype=["signal"])
        return d

    def test_typo_is_flagged_with_suggestion(self):
        issues = unknown_object_issues(self._dev_with("cycl~").boxes)
        codes = [i.code for i in issues]
        assert "guidelines/unknown-object" in codes
        assert any("cycle~" in i.message for i in issues)   # correct suggestion

    def test_known_object_is_clean(self):
        assert unknown_object_issues(self._dev_with("cycle~").boxes) == []

    def test_allowlisted_new_object_is_clean(self):
        # loudness~ postdates the maxdiff dataset but is a real Max 9 object.
        assert unknown_object_issues(self._dev_with("loudness~").boxes) == []

    def test_argful_object_is_skipped(self):
        # a bare-name-only check: creation args mean we don't second-guess the name
        assert unknown_object_issues(self._dev_with("zl len 4").boxes) == []


class TestParameterNames:
    def test_duplicate_longname_flagged(self):
        d = AudioEffect("UT", width=200, height=120)
        d.add_dial("a", "Tone", [10, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
        d.add_dial("b", "Tone", [60, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
        codes = [i.code for i in parameter_name_issues(d.boxes)]
        assert "guidelines/duplicate-longname" in codes

    def test_auto_indexed_name_flagged(self):
        d = AudioEffect("UT", width=200, height=120)
        d.add_dial("a", "Gain[1]", [10, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
        codes = [i.code for i in parameter_name_issues(d.boxes)]
        assert "guidelines/auto-indexed-name" in codes

    def test_distinct_names_clean(self):
        d = AudioEffect("UT", width=200, height=120)
        d.add_dial("a", "Drive Tone", [10, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
        d.add_dial("b", "Filter Tone", [60, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
        assert parameter_name_issues(d.boxes) == []


class TestJsStyle:
    def test_missing_use_strict_and_newline(self):
        codes = [i.code for i in js_style_issues("var x = 1;")]
        assert "guidelines/js-no-use-strict" in codes
        assert "guidelines/js-no-trailing-newline" in codes

    def test_clean_js(self):
        assert js_style_issues('"use strict";\nvar x = 1;\n') == []

    def test_trailing_space_flagged(self):
        codes = [i.code for i in js_style_issues('"use strict";\nvar x = 1; \n')]
        assert "guidelines/js-trailing-space" in codes


class TestCheckGuidelines:
    def test_clean_device_is_clean(self):
        d = AudioEffect("Clean", width=200, height=120)
        d.add_dial("gain", "Gain", [10, 10, 40, 40], min_val=0.0, max_val=1.0, initial=0.5)
        d.add_newobj("mul", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
        assert d.check_guidelines() == []

    def test_device_method_matches_module(self):
        d = AudioEffect("UT", width=200, height=120)
        d.add_newobj("x", "cycl~", numinlets=1, numoutlets=1, outlettype=["signal"])
        assert [i.code for i in d.check_guidelines()] == [
            i.code for i in check_guidelines(d)]
        assert any(i.code == "guidelines/unknown-object" for i in d.check_guidelines())
