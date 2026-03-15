# Ableton UI 90-Day Sprint

This is the working execution guide for the Ableton UI practice plan.

Budget:

- `10-15 hrs/week`
- `12 weeks`
- main workshop: this repo
- main references: Ableton Live devices

## Artifact Map

Shared docs:

- playbook: `docs/ableton_ui_playbook.md`
- construction internals: `docs/ableton_ui_construction_internals.md`
- review rubric: `docs/ableton_ui_review_checklist.md`
- teardown template: `docs/ableton_ui_teardown_template.md`
- validation template: `docs/ableton_ui_validation_template.md`
- baseline audit: `docs/ableton_ui_baseline_audit.md`
- tracker: `docs/ableton_ui_tracker.md`
- scoreboard: `docs/ableton_ui_scoreboard.md`
- reference matrix: `docs/ableton_ui_reference_matrix.md`

Per-device design docs:

- `plugins/parametric_eq/README.md`
- `plugins/linear_phase_eq/README.md`
- `plugins/spectrum_analyzer/README.md`
- `plugins/ladder_filter/README.md`
- `plugins/granular_sampler/README.md`

Validation note location:

- `docs/ui_validation/`

## Weekly Cadence

Every week:

- `2 hrs` reference teardown
- `5-7 hrs` build work
- `2 hrs` in-Live validation
- `1-2 hrs` synthesis into docs and Phren

Do not skip the synthesis step. The point is reusable judgment, not only local
device changes.

## Reference Order

Use this order and do not expand it until the earlier devices feel internalized.

1. `EQ Eight`
2. `Spectrum`
3. `Auto Filter`
4. `Utility`
5. `Compressor` or `Glue Compressor`
6. `Simpler`
7. `Wavetable`
8. `Echo`

External products are contrast references only after the Ableton reading is
stable.

## Important Framing

This sprint is not starting from zero, and it is not pretending the repo only
improved after the reference study began.

The repo already built some strong direct-manipulation graph tools before the
Ableton reference pass was formalized. The study phase exists to improve the
surrounding control grammar, parameter semantics, compact behavior, and UI
internals without losing what already feels good.

## Week-By-Week Plan

### Weeks 1-2: Mental Model

Reference targets:

- `EQ Eight`
- `Spectrum`
- `Utility`
- `Auto Filter`

Repo targets:

- `Parametric EQ`
- `Linear Phase EQ`
- analyzer lane direction
- filter lane direction

Outputs:

- baseline audit
- UI construction internals map
- first playbook draft
- review checklist
- at least two teardown notes

Success:

- explain why the current EQ lanes are close but not yet fully Ableton-native
- explain why the graph layer is ahead of the shared widget and routing grammar

### Weeks 3-4: Graph-First EQ

Reference target:

- `EQ Eight`

Repo target:

- `Parametric EQ`

Outputs:

- selected-band rail refinements
- graph-first review pass
- validation note for the EQ sprint

Success:

- graph is the unquestioned primary editor
- selected-band editing is obvious without explanation

Suggested validation note:

- `docs/ui_validation/week_03_parametric_eq.md`

### Weeks 5-6: Precision And Synchronization

Reference targets:

- `EQ Eight`
- `Spectrum`

Repo target:

- `Linear Phase EQ`

Outputs:

- stronger contextual selected-band model
- clearer quality, latency, analyzer, and listen state
- validation note for precision EQ workflow

Success:

- the device reads as a different product role than the fast EQ

Suggested validation note:

- `docs/ui_validation/week_05_linear_phase_eq.md`

### Weeks 7-8: Analyzer Trust

Reference target:

- `Spectrum`

Repo target:

- `Spectrum Analyzer`
- shared analyzer backend direction

Outputs:

- analyzer semantics pass
- shared control language for overlays and standalone analyzer
- validation note for analyzer truthfulness

Success:

- every analyzer control has a clear semantic job

Suggested validation note:

- `docs/ui_validation/week_07_spectrum_analyzer.md`

### Weeks 9-10: Performance Filter UI

Reference target:

- `Auto Filter`

Repo target:

- `Ladder Filter`

Outputs:

- performance-oriented filter UI
- stronger direct-manipulation story
- validation note for performance editing

Success:

- the device feels like an instrument-grade effect rather than a lab tool

Suggested validation note:

- `docs/ui_validation/week_09_ladder_filter.md`

### Weeks 11-12: Framework Consolidation

Reference targets:

- revisit earlier devices
- add `Simpler` as the dual-surface benchmark

Repo target:

- shared framework guidance
- dual-surface shell spec for `Granular Sampler`

Outputs:

- finalized playbook
- re-review against the rubric
- dual-surface shell guidance
- final validation note

Success:

- another engineer could pick up the docs and build a coherent flagship lane

Suggested validation note:

- `docs/ui_validation/week_11_framework_reaudit.md`

## Sprint Gates

Each major sprint must finish with:

- one updated per-device design doc
- one teardown note
- one validation note
- one rubric score
- one Phren finding if a non-obvious UI lesson was learned

## Checkpoints

- Day 30: critique Ableton-style hierarchy and selected-control models
- Day 60: build graph-first and analyzer-backed interfaces that feel coherent
  in Live
- Day 90: design a new flagship lane from product role through interaction
  model without copying surface styling only
