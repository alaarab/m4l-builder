# tools/

Repo-maintenance scripts. Run each with `uv run python tools/<script>.py` from the repo root, unless noted otherwise.

## Doc generators

Regenerate these after adding, renaming, or removing public DSP blocks, recipes, UI widgets, themes, or engines — they introspect the installed package directly, so the docs never hand-drift.

| Script | Regenerates |
|--------|-------------|
| `build_catalog.py` | `uv run python tools/build_catalog.py` -> `docs/catalog.md` (full auto-generated index of DSP blocks, recipes, UI widgets, themes, engines) |
| `build_palette.py` | `uv run python tools/build_palette.py` -> `docs/palette.md` (curated, composition-oriented tour of the kit) |

## Corpus mining & reverse-engineering reports

Not part of this repo. The reverse/corpus report builders (`mine_amxd_corpus.py`,
`build_family_report.py`, `build_corpus_fixture.py`, ...) were removed with the
reverse/corpus code.
