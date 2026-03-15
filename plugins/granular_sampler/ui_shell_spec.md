# Granular Sampler UI Shell Spec

This spec defines the dual-surface shell for the Granular Sampler lane.

It is intentionally product-level and UI-first. It does not lock the final DSP
implementation.

## Product Role

`Granular Sampler` should behave like a playable sample instrument first and a
deep granular editor second.

That means:

- compact view must already feel useful and musical
- expanded view must unlock waveform editing and region control without turning
  the product into a utility patch

## Surface Split

### Compact Surface

Purpose:

- immediate playability
- source identity
- one-glance zone summary
- macro grain shaping

Compact hero:

- a small source preview or zone summary panel

Compact primary controls:

- `Position`
- `Size`
- `Density`
- `Spray`
- `Pitch`
- `Mix` or output

Compact persistent states:

- sample loaded vs empty
- current region summary
- playback mode summary
- obvious warning when no source is loaded

Compact exclusions:

- no full waveform editor
- no dense metadata pane
- no duplicate deep region controls

### Expanded Surface

Purpose:

- waveform-driven sample editing
- region and loop definition
- scrub interaction
- deeper grain distribution and motion behavior

Expanded hero:

- waveform editor with visible region start, end, and current position

Expanded secondary rails:

- selected-region or playback-context rail
- source metadata and intake panel
- deeper grain motion and distribution controls

Expanded persistent states:

- loaded source identity
- selected region
- current playback position or scrub focus
- main compact macros

## Canonical Editors

There must be one canonical editor for each task:

- source and region editing: waveform surface
- macro grain feel: compact-visible macro controls
- deeper grain distribution: expanded secondary rail

Avoid:

- putting equal editing power into waveform, macro strip, and metadata panels
- duplicating region controls in several disconnected places

## Empty-State Behavior

When no sample is loaded:

- compact view should show a clear empty-source state and still expose a
  meaningful load action
- expanded view should show the waveform area as an intentional empty editor,
  not a broken graph
- deep grain controls should be visually muted until a source exists

## Transition Behavior

Opening the expanded editor should preserve:

- current source
- current region summary
- current playback position or latest scrub focus if available
- macro values from compact view

Returning to compact view should preserve:

- the loaded-source identity
- the current region summary
- the core macro control state

## Validation Targets

Compact validation:

- user can understand whether a source is loaded within three seconds
- user can make one expressive macro change without opening the editor
- compact controls still feel musical after the expanded editor exists

Expanded validation:

- user can find the editable region immediately
- user can scrub or reposition without searching for the active focus
- waveform, region markers, and macro state remain synchronized

Cross-surface validation:

- compact and expanded surfaces agree about source and region state
- no duplicated deep control becomes a drift source
- the expanded editor feels like the compact device unfolded, not replaced

## Immediate Repo Implications

- this lane should be the first consumer of `docs/dual_surface_shell_guidance.md`
- validation notes for this lane should explicitly score compact usefulness
  against expanded clarity
- the eventual implementation should treat waveform editing as the hero surface
  and grain macros as the compact identity, not the other way around
