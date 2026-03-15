# Ableton UI Baseline Audit

This audit is the starting point for the 90-day Ableton UI sprint.

It explains, in repo language, why the current flagship lanes are promising but
not yet fully Ableton-native.

## Current Strengths

The repo already has several real strengths:

- product-role separation is strong in the docs
  - `Parametric EQ` is framed as the fast graph-driven lane
  - `Linear Phase EQ` is framed as the slower precision lane
  - `Spectrum Analyzer` is framed as shared infrastructure plus product
  - `Ladder Filter` is framed as a performance-oriented character lane
- graph-first UI work is already real rather than aspirational
- selected-band and chip-row concepts already exist in the EQ lanes
- analyzer behavior is treated as part of trust, not decoration
- the plugin lanes already use design-doc style README files instead of leaving
  intent implicit in code

These are not beginner problems. They are the problems of a repo that already
knows what a flagship lane should feel like.

## Why The EQ Lanes Are Close But Not Yet Native

The current EQ lanes are close because:

- the graph already feels like the natural hero surface
- the devices already distinguish fast mix EQ from precision linear-phase EQ
- analyzer-backed interaction is treated as core product behavior
- hidden duplicate parameters are already being disabled in the build tests

They are not yet fully Ableton-native because the shared UI model is still
incomplete:

- the selected-band rail is the intended model, but not yet the clear canonical
  editor everywhere
- graph, chip, and contextual controls still need a stricter anti-drift rule
- compact-vs-expanded behavior is not yet standardized across flagship lanes
- analyzer semantics are directionally correct but not yet unified behind one
  shared language
- the layout system has useful primitives, but not yet the stronger semantic
  section/rail/surface patterns the backlog calls for

In short: the repo already has good devices, but the repo-level UI grammar is
not finalized yet.

## Reference Mapping

### EQ Eight -> Parametric EQ And Linear Phase EQ

Reference lessons:

- graph-first editing must be unquestioned
- selection must stay obvious
- contextual controls should feel faster than generic widget racks
- a selected-band editor should explain itself through placement and state, not
  through user memory

Repo implication:

- `Parametric EQ` should keep moving away from bottom-card-first editing
- `Linear Phase EQ` should keep its precision identity while strengthening the
  contextual editor

### Spectrum -> Spectrum Analyzer And EQ Overlays

Reference lessons:

- analyzer trust comes from semantics, not only nice drawing
- source, averaging, refresh, and hold state must be explicit
- the graph should look calm even when the data is busy

Repo implication:

- the standalone analyzer lane should define the shared analyzer contract
- EQ overlays should reuse the same semantic model with lighter presentation

### Auto Filter -> Ladder Filter

Reference lessons:

- performance effects need one obvious central gesture
- modulation must be readable without turning the UI into a dashboard
- warning states should feel deliberate and useful

Repo implication:

- `Ladder Filter` should prioritize central cutoff or response editing,
  performance modulation, and self-oscillation risk communication

### Utility -> Compact-Legibility Benchmark

Reference lessons:

- compact devices still communicate identity instantly
- state is obvious even with very little chrome
- small controls can still feel productized when hierarchy is disciplined

Repo implication:

- every flagship lane needs a stronger compact-view story

## Current Repo Gaps

These gaps are already visible across the roadmap:

- no canonical cross-device UI playbook existed before this sprint
- no shared weekly scoring rubric existed
- no standard validation-note format existed
- no repo-level default for compact-vs-expanded shell behavior existed
- no shared analyzer semantics doc existed
- no shared rule existed for when contextual controls supersede generic rails

## Priority Order

This is the right order for the 90-day sprint:

1. tighten the EQ selected-band model
2. standardize analyzer trust and semantics
3. build the performance filter interaction model
4. consolidate the shared framework and dual-surface guidance

This order matches the current backlog and existing repo maturity.

## Definition Of Progress

Progress should not be measured by more controls or more custom drawing.

Progress means:

- fewer duplicated editing surfaces
- clearer product-role differences
- stronger compact legibility
- more trustworthy analyzer and meter semantics
- faster editing from the primary surface
- less explanation required for selection and state

## Immediate Next Actions

- use the playbook as the review standard for all flagship lanes
- score the next EQ changes with the shared checklist
- require a validation note for each major sprint in `docs/ui_validation/`
- record non-obvious UI lessons in Cortex as they appear
