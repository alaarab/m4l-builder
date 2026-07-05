# Ableton UI Teardown: Spectrum

## Metadata

- Reference device: `Spectrum`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: Weeks 1-2
- Why this device is in scope: primary benchmark for analyzer truth,
  measurement controls, and low-chrome display hierarchy

## Product Role

- Measurement tool
- The product role is obvious because the graph is the product and the controls
  are framed around interpretation rather than sound shaping

## Hero Surface

- The spectrum plot is the primary surface
- It earns that role because the device exists to expose trustworthy
  frequency-domain information
- Direct edits are about analysis behavior, not audio processing

## Always Visible Vs Contextual

- Always visible: plot, essential analysis state, and key display controls
- Contextual: deeper display tuning, if any
- Utility controls should sit above or around the graph without visually
  outweighing it

## Selection Model

- Selection is less important than source and display-state clarity
- Repo translation: analyzer lanes should treat source, averaging, refresh, and
  hold semantics as first-class state rather than optional labels

## Compact Legibility

- The device still reads clearly when reduced because the graph remains the
  identity anchor
- Repo translation: standalone analyzer and EQ overlays should inherit this
  calm, legible display hierarchy

## State Encoding

- The important distinction is between live truth, smoothed truth, and held
  history
- Repo translation: analyzer overlays should explicitly separate analysis math
  from display smoothing

## Motion, Analyzer, And Meter Behavior

- The graph can move continuously without becoming visually noisy because the
  chrome stays restrained
- Repo translation: the shared analyzer backend should define one clear control
  language for block, refresh, averaging, hold, and source routing

## What To Steal

- Pattern to adopt in this repo: measurement-first hierarchy
- Pattern to adapt rather than copy: shared analyzer semantics that work both
  standalone and as subdued EQ overlays
- Pattern to avoid: analyzer visuals that look impressive but hide what the
  controls actually mean

## Repo Translation

- Target repo lane: `Spectrum Analyzer`, then the EQ overlays
- What should change first in that lane: define the shared analyzer contract
- What should stay different because the product role is different: EQ overlays
  must stay secondary to the filter curve
