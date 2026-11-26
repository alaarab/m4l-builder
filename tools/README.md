# tools/

Repo-maintenance scripts. Run each with `uv run python tools/<script>.py` from the repo root, unless noted otherwise.

## Doc generators

Regenerate these after adding, renaming, or removing public DSP blocks, recipes, UI widgets, themes, or engines — they introspect the installed package directly, so the docs never hand-drift.

| Script | Regenerates |
|--------|-------------|
| `build_catalog.py` | `uv run python tools/build_catalog.py` -> `docs/catalog.md` (full auto-generated index of DSP blocks, recipes, UI widgets, themes, engines) |
| `build_palette.py` | `uv run python tools/build_palette.py` -> `docs/palette.md` (curated, composition-oriented tour of the kit) |

## Reports

| Script | Prints |
|--------|--------|
| `gen_sim_coverage.py` | `uv run python tools/gen_sim_coverage.py` -> a markdown table of which `gen_snippets` / `gen_character` / `gen_stateful` functions the offline simulator runs, runs approximately, or refuses (and why) |
