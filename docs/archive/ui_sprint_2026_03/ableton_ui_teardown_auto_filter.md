# Ableton UI Teardown: Auto Filter

## Metadata

- Reference device: `Auto Filter`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: Weeks 1-2
- Why this device is in scope: primary benchmark for performance-oriented
  filter UI, modulation visibility, and one-glance musical control

## Product Role

- Performance effect with direct sound-shaping focus
- The product role is obvious because cutoff, resonance, and modulation feel
  central rather than buried in utility chrome

## Hero Surface

- The filter display and core filter controls form the hero interaction area
- It earns that role because the user is expected to shape tone quickly and
  musically
- Direct edits revolve around cutoff, resonance, mode, and modulation amount

## Always Visible Vs Contextual

- Always visible: core tone controls and the display that explains them
- Contextual: deeper modulation behavior and specialized routing or sidechain
  details
- Repo translation: `Ladder Filter` should preserve one obvious central gesture
  even when more modulation features are added

## Selection Model

- Selection is less about discrete objects and more about keeping the active
  modulation story legible
- Repo translation: if multiple modulation sources are present, the device
  should still feel like one filter, not a dashboard of modulators

## Compact Legibility

- The device identity survives reduction because the central filter job remains
  obvious
- Repo translation: `Ladder Filter` compact view should prioritize the tone
  gesture and one or two modulation cues

## State Encoding

- Drive, resonance, and warning states need to feel deliberate
- Repo translation: self-oscillation risk or performance modulation depth
  should read clearly without turning the device into a warning panel

## Motion, Analyzer, And Meter Behavior

- Motion should support musical playability, not visual spectacle
- Repo translation: stereo motion, env amount, and LFO depth should confirm
  behavior without overwhelming the primary filter gesture

## What To Steal

- Pattern to adopt in this repo: performance-first central control model
- Pattern to adapt rather than copy: modulation visibility tuned for the repo’s
  specific ladder sound and future stereo motion
- Pattern to avoid: technically dense filter UI that loses its musical center

## Repo Translation

- Target repo lane: `Ladder Filter`
- What should change first in that lane: define one strong central tone-shaping
  surface
- What should stay different because the product role is different: the repo’s
  ladder lane should retain its stronger character and self-oscillation story
