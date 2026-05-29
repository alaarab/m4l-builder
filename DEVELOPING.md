# Developing m4l-builder

Local setup, project layout, and the tooling that runs in CI.

## Prerequisites

- Python 3.9+ (CI tests 3.9–3.13)
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
  reverse*.py        Reverse-engineering of existing .amxd files
  corpus_*.py        Device-corpus mining and analysis
  _exports.py        Explicit public-name lists consumed by __init__.py
tests/               pytest suite (mirrors the modules above)
tools/               CLI helper scripts (corpus mining, reports)
docs/                API reference and Ableton UI playbooks
```

## How a build works

`Device.build()` assembles a Max patcher dict, which `container.build_amxd()`
serializes into the binary `.amxd` format (a 32-byte `ampf` header followed by
the null-terminated JSON patcher). See the docstring at the top of
`container.py` for the exact byte layout.

## Tooling configuration

All tool config lives in `pyproject.toml`:

- **ruff** — a conservative starter rule set (`E`, `F`, `W`, `B`). `E501`
  (line length), import sorting (`I`), and `pyupgrade` (`UP`) are intentionally
  deferred to keep diffs focused; they can be enabled in a dedicated cleanup
  pass. Facade re-export modules are allow-listed via `per-file-ignores`.
- **pytest / coverage** — `testpaths = ["tests"]`; a `slow` marker is
  registered for opt-in slow tests.
- **mypy** — pinned `<2` (mypy 2.x dropped Python 3.9 support). It gates the
  whole package **except** a documented backlog of legacy modules listed under
  `[[tool.mypy.overrides]]` with `ignore_errors = true`.

### Shrinking the mypy backlog (the ratchet)

To bring an excluded module under the gate:

```bash
# See the real errors for a module (bypassing the overrides):
uv run mypy src/m4l_builder/<module>.py --config-file=/dev/null \
  --ignore-missing-imports --implicit-optional --python-version 3.9
```

Fix the errors, remove the module from the `[[tool.mypy.overrides]]` `module`
list, and confirm `uv run mypy` stays green. Never *add* a module to that list
to silence new errors — fix the code instead.

## Building & publishing

```bash
uv build                              # builds sdist + wheel into dist/
uv publish --token <pypi-token>       # or set UV_PUBLISH_TOKEN
```

The `py.typed` marker ships in the wheel so downstream users get inline types.
