# Ableton UI Teardown: Glue Compressor

## Metadata

- Reference device: `Glue Compressor`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: later reference set
- Why this device is in scope: benchmark for focused dynamics UI, gain-reduction
  visibility, and threshold-centric hierarchy

## Product Role

- Precision-but-fast dynamics tool
- The product role is obvious because the core compression action and resulting
  gain reduction stay visually central

## Hero Surface

- The transfer or reduction display and threshold-centric control zone form the
  hero interaction area
- It earns that role because compression must be judged through action and
  response, not only parameter names
- Direct edits revolve around threshold, ratio, timing, and the visible result

## Always Visible Vs Contextual

- Always visible: compression action, threshold-led control cluster, key mode
  state
- Contextual: deeper routing or sidechain refinements if present
- Repo translation: compressor-family devices should not hide the actual
  compression story behind generic dynamics widgets

## Selection Model

- Selection is less about objects and more about keeping the signal-action story
  legible
- Repo translation: when a device has no selected-object model, the UI still
  needs a canonical “what is being shaped right now” story

## Compact Legibility

- The device remains understandable because the central compression idea
  survives reduction
- Repo translation: dynamics lanes should preserve action visibility in compact
  view, not only parameter labels

## State Encoding

- Reduction, makeup, mode, and bypass states need to be semantically separate
- Repo translation: meter or reduction overlays should never blur active audio
  state with decorative animation

## Motion, Analyzer, And Meter Behavior

- Motion should confirm gain reduction clearly without becoming a visual event
- Repo translation: any reduction or detector display in the repo should stay
  decision-supportive and calm

## What To Steal

- Pattern to adopt in this repo: threshold-centric hierarchy with visible action
- Pattern to adapt rather than copy: focused reduction display tuned for each
  compressor product role
- Pattern to avoid: compressor UI that makes the result less visible than the
  controls causing it

## Repo Translation

- Target repo lane: future compressor and sidechain-compressor work
- What should change first in that lane: make the signal action immediately
  readable
- What should stay different because the product role is different: sidechain
  lanes may need stronger detector or routing context than bus compression
