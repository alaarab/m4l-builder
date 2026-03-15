"""Tests for corpus manifesting and local fixture generation."""

from pathlib import Path

import m4l_builder.corpus_fixture as corpus_fixture_module

from m4l_builder import (
    AudioEffect,
    build_corpus_manifest,
    classify_corpus_source_metadata,
    load_corpus_manifest,
    param_smooth,
    run_corpus_fixture,
    select_corpus_manifest_entries,
    write_corpus_manifest,
)


class TestCorpusFixture:
    def test_build_corpus_manifest_adds_hashes_categories_and_stable_sample(self, tmp_path):
        smooth = AudioEffect("Smooth FX", 220, 100)
        smooth.add_dsp(*param_smooth("smooth"))
        smooth.build(str(tmp_path / "Smooth FX.amxd"))

        plain = AudioEffect("Plain FX", 220, 100)
        plain.build(str(tmp_path / "Plain FX.amxd"))

        (tmp_path / "broken.amxd").write_text("not an amxd", encoding="utf-8")

        manifest = build_corpus_manifest(str(tmp_path), stable_sample_size=2)

        assert manifest["corpus"]["file_count"] == 3
        assert len(manifest["sample_sets"]["stable"]) == 2
        assert manifest["sample_sets"]["errors"] == ["broken.amxd"]

        smooth_entry = next(
            entry for entry in manifest["entries"] if entry["relative_path"] == "Smooth FX.amxd"
        )
        assert len(smooth_entry["sha256"]) == 64
        assert smooth_entry["size_bytes"] > 0
        assert "status:ok" in smooth_entry["categories"]
        assert "device_type:audio_effect" in smooth_entry["categories"]
        assert "has_patterns" in smooth_entry["categories"]

        error_entry = next(
            entry for entry in manifest["entries"] if entry["relative_path"] == "broken.amxd"
        )
        assert error_entry["status"] == "error"
        assert "status:error" in error_entry["categories"]
        assert any(note.startswith("parse_error:") for note in error_entry["dependency_notes"])

        manifest_path = tmp_path / "manifest.json"
        write_corpus_manifest(manifest, str(manifest_path))
        loaded = load_corpus_manifest(str(manifest_path))

        assert loaded["sample_sets"]["stable"] == manifest["sample_sets"]["stable"]

    def test_build_corpus_manifest_tracks_factory_lane_metadata(self, tmp_path):
        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "API"
        factory_root.mkdir(parents=True)
        fx = AudioEffect("Factory API", 220, 100)
        fx.add_dsp(*param_smooth("mod"))
        output = factory_root / "Max Api DeviceExplorer.amxd"
        fx.build(str(output))

        manifest = build_corpus_manifest(str(tmp_path), stable_sample_size=1)
        entry = next(
            item for item in manifest["entries"] if item["relative_path"].endswith("Max Api DeviceExplorer.amxd")
        )

        assert entry["source_lane"] == "factory"
        assert entry["source_family"] == "M4L Building Tools"
        assert entry["pack_name"] == "M4L Building Tools"
        assert entry["pack_section"] == "API"
        assert "source_lane:factory" in entry["categories"]
        assert "pack_name:M4L Building Tools" in entry["categories"]
        assert "pack_section:M4L Building Tools / API" in entry["categories"]

    def test_select_corpus_manifest_entries_supports_sample_sets_and_categories(self, tmp_path):
        patterned = AudioEffect("Patterned", 220, 100)
        patterned.add_dsp(*param_smooth("mod"))
        patterned.build(str(tmp_path / "Patterned.amxd"))

        plain = AudioEffect("Plain", 220, 100)
        plain.build(str(tmp_path / "Plain.amxd"))

        manifest = build_corpus_manifest(str(tmp_path), stable_sample_size=1)

        stable = select_corpus_manifest_entries(manifest, selection="stable")
        assert len(stable) == 1

        pattern_entries = select_corpus_manifest_entries(manifest, selection="category:has_patterns")
        assert [entry["relative_path"] for entry in pattern_entries] == ["Patterned.amxd"]

        family_entries = select_corpus_manifest_entries(manifest, selection="family:Patterned")
        assert [entry["relative_path"] for entry in family_entries] == ["Patterned.amxd"]

        ok_entries = select_corpus_manifest_entries(manifest, selection="ok")
        assert len(ok_entries) == 2

    def test_select_corpus_manifest_entries_supports_lane_and_pack_filters(self, tmp_path):
        public_fx = AudioEffect("Public", 220, 100)
        public_fx.build(str(tmp_path / "Public.amxd"))

        factory_root = tmp_path / "Factory Packs" / "M4L Building Tools" / "Building Blocks" / "Max Audio Effect"
        factory_root.mkdir(parents=True)
        factory_fx = AudioEffect("Factory", 220, 100)
        factory_fx.build(str(factory_root / "Max DelayLine.amxd"))

        manifest = build_corpus_manifest(str(tmp_path), stable_sample_size=1)

        factory_entries = select_corpus_manifest_entries(manifest, selection="lane:factory")
        assert [entry["relative_path"] for entry in factory_entries] == [
            "Factory Packs/M4L Building Tools/Building Blocks/Max Audio Effect/Max DelayLine.amxd"
        ]

        pack_entries = select_corpus_manifest_entries(manifest, selection="pack:M4L Building Tools")
        assert [entry["relative_path"] for entry in pack_entries] == [
            "Factory Packs/M4L Building Tools/Building Blocks/Max Audio Effect/Max DelayLine.amxd"
        ]

        section_entries = select_corpus_manifest_entries(
            manifest,
            selection="pack_section:M4L Building Tools / Building Blocks",
        )
        assert [entry["relative_path"] for entry in section_entries] == [
            "Factory Packs/M4L Building Tools/Building Blocks/Max Audio Effect/Max DelayLine.amxd"
        ]

    def test_run_corpus_fixture_writes_snapshot_knowledge_and_scripts(self, tmp_path):
        fx = AudioEffect("Fixture FX", 220, 100)
        fx.add_dsp(*param_smooth("fixture"))
        fx.build(str(tmp_path / "Fixture FX.amxd"))

        fixture_dir = tmp_path / "fixture"
        results = run_corpus_fixture(
            str(tmp_path),
            str(fixture_dir),
            selection="stable",
            stable_sample_size=1,
        )

        assert results["selected_count"] == 1
        item = results["items"][0]
        artifact_paths = {name: Path(path) for name, path in item["artifacts"].items()}

        assert artifact_paths["snapshot"].exists()
        assert artifact_paths["knowledge"].exists()
        assert artifact_paths["exact"].exists()
        assert artifact_paths["builder"].exists()
        assert artifact_paths["optimized"].exists()
        assert artifact_paths["semantic"].exists()
        assert item["script_lengths"]["semantic"] > 0
        assert item["script_lengths"]["exact"] > 0
        assert "AudioEffect(" in artifact_paths["semantic"].read_text(encoding="utf-8")

    def test_run_corpus_fixture_records_per_mode_failures_without_aborting(self, tmp_path, monkeypatch):
        fx = AudioEffect("Fixture FX", 220, 100)
        fx.add_dsp(*param_smooth("fixture"))
        fx.build(str(tmp_path / "Fixture FX.amxd"))

        original_builder = corpus_fixture_module._GENERATOR_MAP["builder"]

        def boom(_: str) -> str:
            raise ValueError("builder broke")

        monkeypatch.setitem(corpus_fixture_module._GENERATOR_MAP, "builder", boom)
        try:
            results = run_corpus_fixture(
                str(tmp_path),
                str(tmp_path / "fixture"),
                selection="stable",
                stable_sample_size=1,
            )
        finally:
            monkeypatch.setitem(corpus_fixture_module._GENERATOR_MAP, "builder", original_builder)

        item = results["items"][0]
        assert results["fixture_partial_count"] == 1
        assert item["fixture_status"] == "partial"
        assert "builder" in item["mode_errors"]
        assert Path(item["artifacts"]["snapshot"]).exists()
        assert "builder" not in item["artifacts"]

    def test_classify_corpus_source_metadata_detects_factory_and_site_leads(self):
        factory = classify_corpus_source_metadata(
            "/tmp/Factory Packs/M4L Building Tools/API/Max Api DeviceExplorer.amxd"
        )
        assert factory["source_lane"] == "factory"
        assert factory["pack_name"] == "M4L Building Tools"
        assert factory["pack_section"] == "API"

        site_lead = classify_corpus_source_metadata(
            "/tmp/maxforlivedevices/free/SomeDevice.amxd"
        )
        assert site_lead["source_lane"] == "site_leads"
        assert site_lead["source_family"] == "maxforlivedevices"
