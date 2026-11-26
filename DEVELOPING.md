# Developing m4l-builder

Local setup, project layout, and the tooling that runs in CI.

## Prerequisites

- Python 3.10+ (CI tests 3.10–3.14)
- [`uv`](https://docs.astral.sh/uv/) for environment and dependency management

## Setup

```bash
uv sync --group dev
```

This creates a virtual environment, installs the project in editable mode, and
installs the dev tools (pytest, pytest-cov, ruff, mypy). The lockfile
(`uv.lock`) is committed; CI installs from it for reproducible runs.

## Everyday commands

```bash
uv run pytest                                   # full suite
uv run pytest tests/test_dsp.py -k reverb -v    # focused run
uv run pytest --cov=m4l_builder --cov-report=term-missing

uv run ruff check src tests                     # lint
uv run ruff check src tests --fix               # auto-fix

uv run mypy                                      # type-check
```

## Project layout

```
src/m4l_builder/
  device.py          High-level Device / AudioEffect / Instrument / MidiEffect API
  container.py       Binary .amxd container encoding (ampf header + JSON patcher)
  graph.py           Shared graph primitives + typed BoxRef handles
  ui.py  dsp.py       UI widgets and DSP building blocks
  recipes.py         Pre-wired DSP/UI combos
  theme.py           Color themes
  engines/           JavaScript (jsui) visualization generators
  builder/           Public authoring namespace (core, ui, dsp, live, recipes)
  _exports.py        Explicit public-name lists consumed by __init__.py
tests/               pytest suite (mirrors the modules above)
tools/               Doc generators and repo-maintenance scripts
docs/                API reference and Ableton UI playbooks
```

## How a build works

`Device.build()` assembles a Max patcher dict, which `container.build_amxd()`
serializes into the binary `.amxd` format (a 32-byte `ampf` header followed by
the null-terminated JSON patcher). See the docstring at the top of
`container.py` for the exact byte layout.

## Tooling configuration

All tool config lives in `pyproject.toml`:

- **ruff** — `E`, `F`, `W`, `B`, import sorting (`I`), and `pyupgrade` (`UP`),
  targeting Python 3.10. Long generated literals (`E501`) and behavior-sensitive
  printf rewrites (`UP031`) remain deferred. Facade re-exports are allow-listed.
- **pytest / coverage** — `testpaths = ["tests"]`; the complete suite runs in CI
  with an 85% branch coverage floor. A `slow` marker is registered.
- **mypy** — current 2.x, targeting Python 3.10, gates every package module.
  Fix type errors rather than introducing exclusions or weakening the gate.

The package is a standalone authoring library, not an Ableton control-surface
script running inside Live's bundled Python. Python 3.10 is the minimum needed
by current build and development tooling. The docs dependency Markdown 3.11
requires Python 3.11+, so Python 3.10 resolves its latest compatible 3.10.3;
newer interpreters use 3.11.

CI runs on GitHub-hosted `ubuntu-latest` runners. Documentation builds on
PRs and deploys to <https://alaarab.github.io/m4l-builder/> on every push to
`main` that touches `docs/`, `mkdocs.yml` or the Docs workflow (or by a manual
workflow dispatch).

## Building & publishing

```bash
uv build                              # builds sdist + wheel into dist/
uv publish --token <pypi-token>       # or set UV_PUBLISH_TOKEN
```

The `py.typed` marker ships in the wheel so downstream users get inline types.
