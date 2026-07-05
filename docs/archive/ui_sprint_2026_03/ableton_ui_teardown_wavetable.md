# Ableton UI Teardown: Wavetable

## Metadata

- Reference device: `Wavetable`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: later reference set
- Why this device is in scope: benchmark for deep editor density, macro-vs-deep
  separation, and modulation visibility in a complex synth

## Product Role

- Deep synthesis editor with playable identity
- The product role is obvious because the device supports rich editing without
  losing its macro-level orientation

## Hero Surface

- The main synthesis display and central tone-shaping zones combine into the
  hero interaction area
- It earns that role because the user needs both immediate identity and access
  to deeper editor layers
- Direct edits revolve around oscillator shape, motion, and modulation results

## Always Visible Vs Contextual

- Always visible: core synthesis identity, major macro behavior, and key mode
  state
- Contextual: deeper editor details and specialized modulation shaping
- Repo translation: deep editor lanes must separate macro identity from edit
  density rather than presenting everything with equal weight

## Selection Model

- Selection is often about which oscillator, module, or modulation target is
  being shaped
- Repo translation: if a repo lane becomes editor-dense, it needs a stronger
  contextual focus model rather than more panels

## Compact Legibility

- Even a deep device still needs a readable top-level story
- Repo translation: complex future instrument lanes should prove compact
  identity before adding more editor layers

## State Encoding

- Modulation and mode state must stay legible without flattening the hierarchy
- Repo translation: modulation visibility should support editing rather than
  making every lane look equally active

## Motion, Analyzer, And Meter Behavior

- Motion should reinforce synthesis structure, not become ornamental clutter
- Repo translation: editor visuals should clarify where the user is operating
  and what changed

## What To Steal

- Pattern to adopt in this repo: disciplined separation between macro identity
  and deep editor density
- Pattern to adapt rather than copy: contextual module focus for future complex
  synth or spectral lanes
- Pattern to avoid: layering advanced editing everywhere without one stable
  top-level story

## Repo Translation

- Target repo lane: future wavetable, spectral, or deep-editor instrument lanes
- What should change first in that lane: define the macro identity before the
  deep editor grows
- What should stay different because the product role is different: smaller
  flagship effects should remain calmer and more task-focused
