# Ableton UI Teardown: EQ Eight

## Metadata

- Reference device: `EQ Eight`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: Weeks 1-2
- Why this device is in scope: primary benchmark for graph-first EQ editing,
  selected-band behavior, and contextual control rails

## Product Role

- Fast mix tool with high edit speed and strong visual feedback
- Product role is obvious because the graph is the main decision surface and
  the device foregrounds band editing over decorative chrome

## Hero Surface

- The frequency-response graph is the primary editing surface
- It earns that role because it combines selection, frequency placement, and
  tonal shape in one place
- Direct edits are centered around band selection and shape adjustment

## Always Visible Vs Contextual

- Always visible: graph, core band state, essential mode or analyzer context
- Contextual: deeper selected-band behavior and type-dependent editing
- Utility controls should support the graph rather than compete with it

## Selection Model

- Selection is central to the product feel
- The selected band must remain obvious while the graph stays readable
- Repo translation: `Parametric EQ` and `Linear Phase EQ` should keep moving
  toward one canonical selected-band rail rather than mixed graph plus strip
  plus duplicate-widget editing

## Compact Legibility

- Even when reduced, the device still communicates “EQ” through the graph-led
  layout
- Repo translation: compact view should preserve identity and a single fast
  edit, not try to expose every band equally

## State Encoding

- Selected, enabled, and special listening or routing states must not blur
- Repo translation: selected-band color, chip state, and contextual editor
  state must never drift

## Motion, Analyzer, And Meter Behavior

- Analyzer behavior matters only if it supports the graph instead of visually
  drowning it
- Repo translation: analyzer overlays in both EQ lanes should stay semantically
  explicit and visually secondary

## What To Steal

- Pattern to adopt in this repo: unquestioned graph-first editing
- Pattern to adapt rather than copy: selected-band contextual editing because
  the repo has distinct fast and precision EQ roles
- Pattern to avoid: equally loud secondary surfaces that make the graph feel
  optional

## Repo Translation

- Target repo lane: `Parametric EQ` first, then `Linear Phase EQ`
- What should change first in that lane: strengthen the selected-band rail as
  the one canonical editor
- What should stay different because the product role is different: linear
  phase should remain more explicit about quality, latency, and listen state
