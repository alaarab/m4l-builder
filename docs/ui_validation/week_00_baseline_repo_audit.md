# Week 00 Baseline Repo Audit

- Device lane: shared repo audit
- Sprint week: 00
- Build or commit: working tree baseline
- Reviewer: Codex
- Validation date: 2026-03-15
- Status: `in-progress`

## Sprint Goal

Establish the pre-sprint UI baseline before deeper in-Live device work begins.

This note is a repo audit, not an Ableton playback session. It exists to lock
the starting judgment for the 90-day sprint.

## Assets

- Chain-view screenshot: not captured
- Expanded-view screenshot: not captured
- Optional focused crop or video: not captured

## Chain View Readability

Static repo judgment:

- the flagship lanes document the need for strong compact identity, but compact
  behavior is not yet standardized across devices
- `Utility` is the reference benchmark the repo should keep in mind for compact
  legibility

## Expanded View Readability

Static repo judgment:

- the EQ lanes already center the graph as the hero surface
- the graph and node interaction layer is the clearest current strength
- the selected-band model is present but still described as unfinished in the
  product docs
- analyzer and precision state are documented as important, which is a strong
  sign that the repo is thinking at product level rather than widget level
- the weaker area is the surrounding control construction and state plumbing,
  not the existence of a graph surface

## Interaction Scenarios

### Fast Change

- Task: not run in Live
- Result: pending in-Live validation
- Friction: unknown until playback session

### Precise Change

- Task: not run in Live
- Result: pending in-Live validation
- Friction: unknown until playback session

### Exploratory Change

- Task: not run in Live
- Result: pending in-Live validation
- Friction: unknown until playback session

## State Drift Check

- Graph and selected-object rail agree: `unknown`
- Chip row or quick-nav state agrees: `unknown`
- Parameter state agrees: `unknown`
- Display-only states are distinguishable from audio states: `partially`
- Control construction semantics are documented: `baseline no`, now tracked in
  `docs/ableton_ui_construction_internals.md`

## Analyzer And Meter Check

Static repo judgment:

- analyzer trust is correctly treated as a semantic problem, not only a drawing
  problem
- the shared analyzer contract is still a framework gap

## Ableton-Native Score

Use `docs/ableton_ui_review_checklist.md`.

- Overall score: `24/40`
- Strongest category: `Hierarchy and product-role clarity`
- Weakest category: `Compact legibility and shared contextual-editing model`

## Decision

- Iterate

## Next Changes

- Highest-value follow-up: finalize the selected-band contextual editing model
  in the EQ lanes
- One thing to keep: graph-first product framing
- One thing to remove or simplify: duplicated or competing editing surfaces and
  the routing that keeps them artificially in sync
