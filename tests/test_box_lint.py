"""T35/Q15: dataset-backed box lint (vendored Ableton maxdiff datasets)."""


class TestBoxLint:
    def test_spec_lookup_and_alias(self):
        from m4l_builder.box_lint import known_object_spec
        lb = known_object_spec("loadbang")
        assert lb["numinlets"] == 1 and lb["numoutlets"] == 1
        # aliases resolve to the canonical object
        from m4l_builder.vendor.maxdiff import object_aliases
        alias, target = next(iter(object_aliases.items()))
        if known_object_spec(target):
            assert known_object_spec(alias) == known_object_spec(target)

    def test_flags_wrong_shape(self):
        from m4l_builder.box_lint import lint_box
        bad = {"id": "x", "maxclass": "newobj", "text": "loadbang",
               "numinlets": 0, "numoutlets": 1, "outlettype": ["bang"]}
        issues = lint_box(bad)
        assert any("numinlets=0" in i for i in issues)

    def test_skips_argful_and_script_arity(self):
        from m4l_builder.box_lint import lint_box
        assert lint_box({"id": "t", "maxclass": "newobj", "text": "t b b",
                         "numinlets": 1, "numoutlets": 99}) == []
        assert lint_box({"id": "g", "maxclass": "newobj", "text": "gen~",
                         "numinlets": 9, "numoutlets": 9}) == []
        assert lint_box({"id": "j", "maxclass": "jsui",
                         "numinlets": 5, "numoutlets": 5}) == []

    def test_kit_emitters_dataset_clean(self):
        from m4l_builder import AudioEffect
        from m4l_builder.box_lint import lint_boxes
        d = AudioEffect("bl", width=200, height=168)
        assert lint_boxes(d.boxes) == []

    def test_redundant_patcher_fields(self):
        from m4l_builder.box_lint import redundant_patcher_fields
        from m4l_builder.vendor.maxdiff import default_patcher
        probe = {"gridsize": list(default_patcher["gridsize"]),
                 "boxes": [], "rect": [0, 0, 1, 1]}
        assert "gridsize" in redundant_patcher_fields(probe)
        assert "boxes" not in redundant_patcher_fields(probe)
