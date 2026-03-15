# Reverse Engineering

`m4l-builder` now has a first-stage reverse-engineering pipeline for pulling
patcher structure back into Python.

This is intentionally low-level and fidelity-first. The goal is to preserve the
exact patcher and sidecars first, then layer pattern recognition and
high-level rewrites on top later.

## Current flow

```python
from m4l_builder import (
    extract_snapshot_knowledge,
    snapshot_from_amxd,
    generate_builder_python_from_snapshot,
    generate_optimized_python_from_snapshot,
    generate_semantic_python_from_snapshot,
    generate_python_from_snapshot,
)

snapshot = snapshot_from_amxd("My Device.amxd")
knowledge = extract_snapshot_knowledge(snapshot)
exact_source = generate_python_from_snapshot(snapshot)
builder_source = generate_builder_python_from_snapshot(snapshot)
optimized_source = generate_optimized_python_from_snapshot(snapshot)
semantic_source = generate_semantic_python_from_snapshot(snapshot)
```

What you get today:

- a normalized snapshot with boxes, lines, dependencies, parameter banks, and
  recovered sidecar files
- a starter Python rebuild script that writes the exact patcher JSON back out
- a hybrid builder-style Python generator that emits `AudioEffect` /
  `add_*` / `add_line` calls where the snapshot is understood, and falls back
  to raw `add_box(...)` where it is not
- semantic builder regeneration for common UI/support-file-backed objects such
  as `jsui`, `v8ui`, `bpatcher`, `fpic`, `multislider`, `textbutton`, `umenu`,
  `radiogroup`, `live.step`, `live.grid`, `kslider`, and other supported
  display widgets
- an optimized generator that can fold recognized `m4l-builder` DSP helpers
  back into calls like `param_smooth(...)`, `delay_line(...)`, `transport_lfo(...)`,
  `gain_stage(...)`, `highpass_filter(...)`, `feedback_delay(...)`, and similar
  blocks when the geometry and structure match, and can prefer higher-level recipes such as
  `gain_controlled_stage(...)`, `dry_wet_stage(...)`, `tempo_synced_delay(...)`,
  `midi_note_gate(...)`, and `transport_sync_lfo_recipe(...)` when the full
  staged structure is safe to rebuild; recognized-but-unsafe structures stay
  expanded instead of being guessed into recipe calls
- a semantic generator that preserves the optimized path's exact-safe
  helper/recipe collapsing but also normalizes safe non-canonical Live API
  clusters into helper calls; manual-review Live API clusters stay expanded and
  are annotated in the generated source
- sidecar re-emission when the source files could be recovered
- a first analysis pass with UI, parameter, bridge, and audio-I/O detection
- detected generic Max motifs such as named send/receive buses, Live API
  control clusters, and embedded patcher hosts
- Live API motif semantics and archetypes such as `parameter_probe`,
  `tempo_observer`, `transport_state_observer`, `device_active_state`, and
  `track_management`
- canonical Live API clusters can be re-emitted as semantic helpers such as
  `live_object_path(...)`, `live_parameter_probe(...)`, `live_observer(...)`,
  `live_state_observer(...)`, `live_set_control(...)`, `live_thisdevice(...)`,
  and `device_active_state(...)` when their box/line subsets match exactly; `live_observer(...)` supports both the older
  `live.path -> live.object -> live.observer` shape and the more common direct
  `live.path -> live.observer` shape, and the semantic path can also recover
  property-message binding in either topology; `live_parameter_probe(...)` can
  now also recover object-only external probe clusters that use `route ...`
  fan-out and `t ...` trigger wrappers, while `device_active_state(...)` can
  recover both toggle-style and `live.thisdevice outlet -> prepend active`
  controller variants, and `live_state_observer(...)` can recover initialized
  direct-observer state chains such as `live.thisdevice -> t b b ->
  live.path/property -> live.observer -> t i i -> sel 0`
- non-canonical Live API clusters are tracked as helper opportunities with
  blocker reasons so corpus mining can still say "this wants to be
  `live_observer(...)`" or "`live_thisdevice(...)`" even when exact recovery is
  not safe yet
- a structured knowledge manifest with controls, displays, sidecars, bridge
  state, display-role groupings, audio routing, recognized helper blocks,
  recognized recipe blocks, generic motifs, Live API helper recoveries,
  Live API helper opportunities, and explicit lossiness metadata/notes
- extracted embedded patchers as real nested snapshots via
  `extract_embedded_patcher_snapshots(snapshot)` so buried subpatchers can be
  run back through the same reverse pipeline directly
- detected helper patterns with parameters and helperization eligibility
- detected recipe patterns with parameters and recipeization eligibility
- extracted parameter specs with ranges, enums, initials, and unit styles

## Live bridge snapshots

You can also normalize data captured from the LiveMCP Max bridge:

```python
from m4l_builder import snapshot_from_bridge_payload

snapshot = snapshot_from_bridge_payload(
    current_patcher=current_patcher_payload,
    boxes=list_patcher_boxes_payload["boxes"],
    box_attrs=box_attrs_by_id,
    selected_device=selected_device_payload,
    patchlines=optional_patchlines,
)
```

This uses the same snapshot schema, but it is not exact in the same way as an
`.amxd` import. It reconstructs a patcher from bridge-visible state and marks
the snapshot as fidelity-limited.

## Corpus mining

You can mine a whole local research corpus of `.amxd` files and turn it into
aggregate reverse-engineering data:

```python
from m4l_builder import analyze_amxd_corpus, corpus_report_markdown

report = analyze_amxd_corpus("/path/to/amxd-corpus")
markdown = corpus_report_markdown(report)
```

That report includes:

- parse success/error counts
- device-type distribution
- top recognized helper patterns
- top recognized recipes
- top recognized generic motifs
- top controller-dispatch, scheduler, and state-bundle motif signatures
- top named-bus networks and cross-scope named-bus fabrics
- top semantic Live API helper recoveries
- top Live API helper opportunities and blocker reasons
- top controller-shell normalization candidates
- top Live API archetypes, targets, and properties
- top maxclasses across the corpus
- top object names across `newobj` usage
- top control classes, unit styles, and display roles
- top missing sidecars
- top reverse candidates for further semantic work
- top reverse-candidate families so versioned duplicates collapse into one lane
- top reverse-candidate family profiles with aggregated motif/object signals
- largest successfully parsed devices

To focus one semantic lane at a time, build a detailed family profile:

```python
from m4l_builder import (
    analyze_amxd_corpus,
    build_reverse_candidate_family_profile,
    family_profile_markdown,
)

report = analyze_amxd_corpus("/path/to/amxd-corpus")
profile = build_reverse_candidate_family_profile(report, "zs-Knobbler3")
markdown = family_profile_markdown(profile)
```

That profile separates stable family signals from variant-only noise, which is
useful when deciding whether a recurring structure deserves a new helper,
recipe, or normalization pass. It also infers `semantic_targets` and
`next_work_items` from those stable signals so family mining feeds directly
into the reverse roadmap.

At the per-device level, `extract_controller_shell_candidates(snapshot)` now
surfaces normalization-worthy controller structures such as
`controller_surface_shell` and `sequencer_dispatch_shell` alongside the more
exact Live API helper candidates. `extract_embedded_ui_shell_candidates(snapshot)`
also surfaces exact-safe embedded host shells for root `subpatcher` and
`bpatcher` boxes. The optimized and semantic codegen paths now consume those
candidates too, rewriting recognized shells into reusable
`controller_surface_shell(...)`, `sequencer_dispatch_shell(...)`, and
`embedded_ui_shell(...)` helper calls instead of leaving every shell object
flattened at the top level.

For ad hoc local mining, there is also a helper script in the repo:

```bash
uv run python tools/mine_amxd_corpus.py /path/to/amxd-corpus
```

If you want a stable local research subset rather than just one aggregate
report, build a corpus manifest and fixture set:

```python
from m4l_builder import build_corpus_manifest, run_corpus_fixture

manifest = build_corpus_manifest("/path/to/amxd-corpus", stable_sample_size=12)
results = run_corpus_fixture(manifest, "/tmp/amxd-fixture", selection="stable")
```

The manifest records hashes, categories, dependency notes, and a deterministic
`stable` sample set. The fixture run materializes per-device `snapshot.json`,
`knowledge.json`, and generated `exact.py`, `builder.py`, `optimized.py`, and
`semantic.py` scripts for the selected subset. If one generation mode fails on
an external device, the fixture still succeeds overall and records the
per-device mode error instead of aborting the whole batch.

There is also a convenience script:

```bash
uv run python tools/build_corpus_fixture.py /path/to/amxd-corpus /tmp/amxd-fixture
```

The fixture selector also supports family-level targeting, for example
`family:zs-Knobbler3`, so you can materialize only one public-device lane at a
time.

There is also a focused family-report helper in the repo:

```bash
uv run python tools/build_family_report.py /path/to/amxd-corpus zs-Knobbler3
```

## Important limitation

The exact generator is not yet "nice" `m4l-builder` code. It is a fidelity-first
starter rebuild script built around `write_amxd(...)` and the captured patcher
dict.

The builder generator is nicer, but still only partly semantic. The optimized
generator goes further for known `m4l-builder` helper blocks, but anything it
cannot prove safely still falls back to raw box dicts rather than guessing.
The semantic generator takes the next step for Live API clusters only: it can
normalize safe non-canonical helper opportunities, but it is not a universal
"make this patch beautiful" pass yet.

That is deliberate.

## Current non-goals

- perfect semantic recovery for arbitrary third-party `.amxd` devices
- LiveMCP repo changes as part of the reverse-engineering path here
- web builder or sharing-product implementation inside this sprint

This gives us a reliable foundation for the next layers:

- bridge snapshot export from live bridge-enabled devices
- structural pattern recognition
- high-level code rewriting into `AudioEffect`, `add_dial`, DSP helpers,
  recipes, and layout builders
- round-trip diffing to prove fidelity
