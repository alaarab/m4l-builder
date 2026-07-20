# tools/

Repo-maintenance and corpus-analysis scripts. Run each with `uv run python tools/<script>.py` from the repo root, unless noted otherwise.

## Doc generators

Regenerate these after adding, renaming, or removing public DSP blocks, recipes, UI widgets, themes, or engines — they introspect the installed package directly, so the docs never hand-drift.

| Script | Regenerates |
|--------|-------------|
| `build_catalog.py` | `uv run python tools/build_catalog.py` -> `docs/catalog.md` (full auto-generated index of DSP blocks, recipes, UI widgets, themes, engines) |
| `build_palette.py` | `uv run python tools/build_palette.py` -> `docs/palette.md` (curated, composition-oriented tour of the kit) |

## Corpus mining & reverse-engineering reports

Analyze external `.amxd` corpora (mined devices) and turn the extracted structure into markdown reports. See `docs/reverse_engineering.md`.

| Script | Description |
|--------|-------------|
| `mine_amxd_corpus.py` | Mine a directory of `.amxd` files into a reusable JSON + markdown report. |
| `build_family_report.py` | Build a focused reverse-engineering report for one external AMXD family. |
| `build_reference_dossiers.py` | Build reference-device semantic-lifting dossiers for one or more AMXDs. |
| `build_source_lane_report.py` | Build a lane-comparison markdown report for a local AMXD corpus. |
| `build_corpus_comparison_report.py` | Build a comparison markdown report across multiple corpus roots. |
| `build_corpus_fixture.py` | Build a local reverse/codegen fixture from an external AMXD corpus. |
| `build_mapping_lane_report.py` | Build a mapping/modulation lane markdown report for a local AMXD corpus. |
| `build_mapping_product_brief.py` | Build a mapping/modulation product brief for one AMXD device. |
| `build_mapping_product_briefs.py` | Build mapping/modulation product briefs for a local AMXD corpus. |
