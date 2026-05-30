# Contributing to m4l-builder

Thanks for your interest in improving **m4l-builder**! This guide covers the
basics; see [DEVELOPING.md](DEVELOPING.md) for the full local setup and the
internals.

## Quick start

```bash
# 1. Install the dev environment (editable project + pytest, ruff, mypy)
uv sync --group dev

# 2. Make your change, then run the checks the CI runs
uv run ruff check src tests
uv run mypy
uv run pytest
```

All three must pass before a change is merged. CI
(`.github/workflows/tests.yml`) runs the same checks across Python 3.9–3.13.

## Ground rules

- **Zero runtime dependencies.** The library builds `.amxd` files using only
  the Python standard library. Do not add runtime dependencies; dev-only tools
  go in the `[dependency-groups] dev` table in `pyproject.toml`.
- **Tests for behavior changes.** New features and bug fixes should come with a
  test. Match the existing style in `tests/` (module docstring, `pytest`,
  class-based `TestXxx`). Bug fixes are most valuable as a regression test that
  fails before the fix and passes after.
- **Keep the public API stable.** Public names are re-exported through the
  facade modules (`authoring.py`, `reverse.py`, …) and listed in `_exports.py`.
  If you change them, update `_exports.py` and the `tests/test_architecture.py`
  import contract.
- **Type new code.** New modules are type-checked by mypy. A documented backlog
  of legacy modules is temporarily excluded (see the `[[tool.mypy.overrides]]`
  list in `pyproject.toml`); shrink that list rather than growing it.

## What to work on

See the [roadmap](docs/roadmap.md) for tracked open work, including items that
need validation inside Ableton Live.

## Commit & PR conventions

- Write imperative, descriptive commit subjects (e.g. "Add FDN reverb recipe"),
  matching the existing history.
- Keep commits focused; separate mechanical cleanups from behavior changes.
- Open a PR against `main`; CI must be green.

## Reporting bugs

Open an issue with a minimal Python snippet that reproduces the problem and the
observed vs expected `.amxd` behavior. If it involves an existing device,
attach the `.amxd` (or the script that builds it).
