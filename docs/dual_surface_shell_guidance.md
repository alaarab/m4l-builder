# Dual-Surface Shell Guidance

This document defines the shared shell pattern for devices that need both a
compact chain identity and a richer expanded editor.

Use it for flagship instruments and any effect whose compact surface should
preserve a strong performance identity while deferring deeper editing to an
expanded view.

Primary candidate in this repo:

- `plugins/granular_sampler/README.md`

Future likely candidates:

- advanced sampler or scrubber lanes
- wavetable or spectral instruments
- analyzer-backed editor devices with a clear macro surface

## Core Rule

Compact and expanded views must feel like the same device solving the same job.

Expanded view can add depth. It cannot replace the product identity.

## Surface Roles

### Compact Surface

The compact surface is for:

- device identity
- the fastest musical action
- one-glance active state
- macro controls that are safe and useful during playback

The compact surface is not for:

- dense editor controls
- full metadata panels
- duplicate deep controls that conflict with the expanded editor

### Expanded Surface

The expanded surface is for:

- the hero editor
- contextual selected-object controls
- metadata and utility panels
- deeper routing, display, or modulation controls

The expanded surface must keep the compact surface recognizable. It should feel
like the compact view unfolded, not like a different product.

## Required Shell Decisions

Every dual-surface lane must define:

- the compact hero
- the expanded hero
- what state is shared visibly in both surfaces
- what controls exist only in expanded view
- what controls exist only in compact view
- what contextual editor appears in expanded view
- what happens when no source or selection exists

## Shared State

These states should generally be visible in both surfaces when they affect
audio or musical intent:

- source loaded vs empty
- main playback or tone mode
- output or mix state
- major warning state
- selected zone or region summary when relevant

These can be expanded-only if the compact surface remains clear:

- metadata details
- advanced modulation configuration
- detailed editor-only utilities
- precision readouts that do not affect first-glance understanding

## Compact Surface Rules

- One control or gesture must feel central.
- No more than one row of secondary utilities should compete with the main
  action.
- The surface must remain understandable at normal Ableton chain-view scale.
- Any preview display must support the compact interaction rather than only
  advertise the deeper editor.

For sample instruments specifically:

- compact should expose source identity, zone summary, and the most musical
  grain or playback controls
- compact should not attempt full waveform editing

## Expanded Surface Rules

- There must be one hero editor, usually a waveform, graph, or performance
  surface.
- Contextual editing rails should sit beside or below that editor without
  challenging it for attention.
- Metadata and utility panels should be visually quieter than the hero editor.
- Empty-state behavior must remain legible; the expanded surface cannot look
  broken before content is loaded.

## Transition Rules

The move from compact to expanded should preserve:

- current source
- selected region or object
- main playhead or focus location when meaningful
- key macro control state

The move from expanded to compact should preserve:

- the most useful summary of current focus
- the central performance control
- obvious indication that the deeper editor still exists

## Validation

Dual-surface validation must test:

- whether compact view is useful without opening the editor
- whether expanded view explains itself immediately
- whether current selection survives the transition
- whether compact and expanded surfaces ever disagree about active state
- whether the compact surface still feels intentional after the editor grows

## Granular Sampler Translation

The Granular Sampler lane should use this shell pattern as follows:

- compact: playable macro grain instrument
- expanded: waveform-driven sample and region editor
- shared state: source loaded, region summary, position summary, grain macro
  state
- expanded-only: waveform region editing, source metadata, deeper grain
  distribution controls

See:

- `plugins/granular_sampler/ui_shell_spec.md`
