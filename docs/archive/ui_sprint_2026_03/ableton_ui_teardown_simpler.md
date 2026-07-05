# Ableton UI Teardown: Simpler

## Metadata

- Reference device: `Simpler`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: Weeks 11-12 and dual-surface study
- Why this device is in scope: primary benchmark for dual-surface instrument
  behavior, waveform-led editing, and sample identity

## Product Role

- Dual-surface instrument
- The product role is obvious because compact use and deep sample editing feel
  like two views of one instrument rather than separate products

## Hero Surface

- In expanded mode, the waveform editor is the hero surface
- In compact use, the identity is preserved through playable controls and clear
  source state
- Direct edits center on source, region, and playback behavior

## Always Visible Vs Contextual

- Always visible: source identity, core playback or tone behavior, compact
  performance affordances
- Contextual: region editing, source metadata, and deeper sample operations
- Repo translation: `Granular Sampler` should treat waveform editing as the hero
  editor and macro grain feel as the compact identity

## Selection Model

- Selection is tied to region, source, or edit focus rather than abstract UI
  state
- Repo translation: the expanded editor must own region editing; compact view
  should summarize it instead of competing with it

## Compact Legibility

- Compact still feels like a sample instrument, not an empty stub
- Repo translation: dual-surface lanes must preserve musical usefulness without
  opening the editor

## State Encoding

- Loaded source, active zone, and playback mode are all legible without dense
  chrome
- Repo translation: compact and expanded surfaces must agree on source and
  region state at all times

## Motion, Analyzer, And Meter Behavior

- Waveform motion and playhead feedback support editing directly
- Repo translation: waveform and scrub visuals in the repo should be editing
  tools, not ambient motion

## What To Steal

- Pattern to adopt in this repo: one-instrument, two-surface coherence
- Pattern to adapt rather than copy: waveform-led editing tailored to granular
  performance rather than only sample playback
- Pattern to avoid: making compact and expanded views feel like separate
  products

## Repo Translation

- Target repo lane: `Granular Sampler`
- What should change first in that lane: preserve strong compact identity while
  letting the waveform editor own region work
- What should stay different because the product role is different: the repo’s
  granular lane should foreground grain macros more than a traditional sampler
