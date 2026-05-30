# Roadmap / TODO

Tracked open work. Items in the first group are built structurally but need
validation **inside Ableton Live 12**, which CI cannot do — load a generated
device in Live to confirm behavior before relying on it.

## Needs Ableton Live validation

- **MIDI Generator note emission.** The `MidiGenerator` device type and the
  `midi_tool_io` scaffold ship today, but a generator that actually *emits*
  notes must construct a notes dictionary (`pitch` / `start_time` / `duration`,
  see [midi_tools.md](midi_tools.md)) and send it to `live.miditool.out`. The
  likely approach is Max `dict` / `dict.pack` objects or an embedded `v8`/`js`
  script. Open-source reference generators are *frozen* (`.amxd` patcher
  encrypted), so the mechanism must be confirmed in Live rather than
  reverse-engineered. A pure-Python notes-dictionary builder helper would make
  this ergonomic.
- **MPE per-note expression helpers.** Blocks for per-note channel routing,
  per-note pitch bend (±48 st), channel pressure, and slide (CC74). The objects
  are easy to emit; the per-note routing behavior needs a Live check.

## Quality / infra

- **Dependabot alert (1 moderate, dev-only).** Surfaced once a lockfile was
  added; the shipped package still has zero runtime dependencies, so end users
  are unaffected. Identify the package from the repo's security tab and pin or
  patch it (`uv lock --upgrade <pkg>`).
- **mypy backlog (2 modules).** `_reverse_legacy` (large legacy module) and
  `livemcp_bridge` (relies on `Device.add_*` methods attached dynamically via
  `setattr`, invisible to mypy) remain excluded in `pyproject.toml`.
- **ruff `UP031`.** The printf-style → `str.format` rewrites are deferred
  because `%`-with-tuple semantics are behavior-sensitive; enable with manual
  review.
- **Large legacy functions.** A few functions in `_reverse_legacy.py` (e.g.
  `_detect_live_api_helper_matches` ~580 lines, `_live_api_helper_call_from_snapshot`
  ~460) and `corpus_analysis.py` remain large; decompose them incrementally with
  the reverse/corpus test suites as the safety net. (`dsp` was split into a
  categorized package; the JS-string generators in `engines/` and
  `livemcp_bridge.py` are intentionally template-shaped and left as-is.)

## Nice to have

- **Baked step-sequence data.** Verify the `.maxpat` embedded-`coll` data format
  so richer baked patterns (custom step sequences, sample maps) become possible
  without `loadbang` init-order fragility.
- **More device coverage in examples** as new capabilities land.
