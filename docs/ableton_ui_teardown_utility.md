# Ableton UI Teardown: Utility

## Metadata

- Reference device: `Utility`
- Date: 2026-03-15
- Reviewer: Codex
- Sprint week: Weeks 1-2
- Why this device is in scope: compact-view benchmark for obvious state,
  disciplined hierarchy, and low-chrome clarity

## Product Role

- Fast utility tool
- The product role is obvious because the device reads immediately and does not
  pretend to be more complex than it is

## Hero Surface

- There is no large graph hero; the hero is compact legibility itself
- It earns that role by making the primary controls and states obvious without
  visual drama
- Direct edits are immediate and unsurprising

## Always Visible Vs Contextual

- Always visible: the controls that change the core job of the device
- Contextual: little to none
- Repo translation: compact flagship views should learn from this restraint
  even when the expanded view is more complex

## Selection Model

- Selection is minimal because the product does not depend on editing many
  objects
- Repo translation: if a flagship lane has a complex expanded editor, its
  compact state should still feel Utility-level clear

## Compact Legibility

- This is the main lesson: compact does not need to feel cramped or vague
- Repo translation: chain view should communicate identity, key state, and one
  fast action without exposing all deep controls

## State Encoding

- Active states are obvious because the device does not overload one indicator
  with several meanings
- Repo translation: selected, enabled, bypassed, and monitoring states should
  stay semantically separate in larger flagship lanes too

## Motion, Analyzer, And Meter Behavior

- Minimal motion keeps the device calm and readable
- Repo translation: analyzers, meters, or animated overlays in larger devices
  should preserve the same calm baseline

## What To Steal

- Pattern to adopt in this repo: disciplined compact hierarchy
- Pattern to adapt rather than copy: low-chrome readability in chain view
- Pattern to avoid: trying to preserve full expanded functionality in compact
  mode

## Repo Translation

- Target repo lane: all flagship lanes, especially EQs and future dual-surface
  devices
- What should change first in that lane: define the minimum compact identity
- What should stay different because the product role is different: expanded
  views can stay richer as long as compact views stay disciplined
