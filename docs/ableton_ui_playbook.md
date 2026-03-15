# Ableton UI Playbook

This document is the shared UI standard for flagship Max for Live work in this
repo.

Use it to design, review, and validate devices that should feel recognizably
Ableton-native. It does not replace per-device design docs in
`plugins/<lane>/README.md`. It standardizes the cross-device patterns those
lanes should share.

For how the current builder actually constructs UI internally, see
`docs/ableton_ui_construction_internals.md`.

## Scope

This playbook is for devices where UI quality is part of the product claim:

- graph-first EQs
- analyzers and meter-driven tools
- performance filters and modulation effects
- dual-surface sampler or instrument lanes
- other devices where direct manipulation, compact legibility, and state
  clarity matter more than raw control count

Current flagship lanes:

- `plugins/parametric_eq/README.md`
- `plugins/linear_phase_eq/README.md`
- `plugins/spectrum_analyzer/README.md`
- `plugins/ladder_filter/README.md`
- `plugins/granular_sampler/README.md`

## Sequence Correction

This repo did not start from a finished Ableton UI theory and then implement it
cleanly.

The actual sequence was:

1. build useful custom graph and interaction tools
2. discover that some of them already felt good
3. study Ableton devices more deliberately to understand what the surrounding
   control grammar and internals were still missing

That matters because the playbook should standardize and refine the current
strengths. It should not pretend the existing flagship work came from a fully
settled framework.

## Core Rule

Each device must have one obvious editing story.

That story is expressed through:

- one primary editing surface
- one coherent selected-object model when multiple objects are editable
- one compact-vs-expanded behavior model
- one consistent system for showing active, selected, bypassed, listened, or
  analyzer-driven state

If the UI requires the user to infer which surface is primary, the device is
not ready.

## Product Role

Start every flagship lane by naming the product role before discussing layout.

Use one of these roles:

- Fast mix tool: immediate, low-latency, graph-first or knob-first, low chrome
- Precision tool: slower, more explicit, more informational, strong state
  readouts
- Measurement tool: truth-first display, subdued chrome, controls framed around
  interpretation rather than sound design
- Performance effect: gesture-first, obvious central control, visual motion
  must support playability
- Dual-surface instrument: compact chain identity plus expanded edit surface

Product role must determine:

- what stays visible at all times
- what becomes contextual
- how much latency, analyzer, routing, or modulation state must be surfaced
- whether the hero surface is a graph, display, large macro control, or
  compact strip

## Primary Editing Surface

Flagship devices must have one hero surface that owns first glance and fastest
edits.

Rules:

- The hero surface must be visually dominant without relying on loud colors.
- The hero surface must support real work, not decorative display only.
- Secondary rails must support the hero surface, not compete with it.
- The chain view must preserve the device identity even when the hero surface
  is reduced.

Typical mappings:

- EQs: graph is primary, selected-band rail is secondary
- Analyzer: spectrum plot is primary, controls are top-row utilities
- Filter: response surface or cutoff-focused control is primary
- Dual-surface instrument: compact view shows identity and performance state;
  expanded view owns deep editing

Anti-patterns:

- graph plus equally loud banks of generic widgets
- a bottom strip that becomes the real editor even though the graph looks like
  the main tool
- duplicated controls where no one surface is canonical

## Selected-Object Editing Model

Any device with editable objects must make selection explicit.

Editable objects include:

- EQ bands
- filter nodes
- modulation lanes
- grain markers
- sequencer steps
- sample regions

Rules:

- Selection must always be visible.
- Selection color and selection location must agree.
- There must be one canonical contextual editor for the selected object.
- Duplicate controls must be disabled or clearly secondary, not silently live.
- Type-dependent controls must become relevant without forcing the user to
  relearn the layout.

For EQ-style devices specifically:

- graph, chip row, selected-band rail, and parameter state must never drift
- irrelevant parameters should be visually deemphasized or made inert
- selection should survive short navigation hops unless the model explicitly
  says otherwise
- if a graph is already the fastest editing surface, support rails must clarify
  it rather than duplicate it

## Compact Vs Expanded Behavior

Flagship devices must define how they behave in both compact chain view and
expanded detail view.

Compact view should preserve:

- device identity
- one glanceable state summary
- the fastest one or two edits
- critical audio-affecting states such as bypass, listen, analyzer source,
  drive, or quality when those states define the product role

Expanded view should add:

- contextual editing rails
- deeper analyzer or routing controls
- full direct-manipulation surface
- precision readouts when the device role needs them

Rules:

- Compact and expanded surfaces must feel like the same device.
- Expanded view cannot require a different mental model.
- Compact view must not expose deep controls that conflict with expanded
  contextual controls.
- Dual-surface instruments should declare which tasks belong to each surface.

## Visual Hierarchy

Ableton-native hierarchy is dense but calm.

Rules:

- Use surfaces and contrast before using more color.
- Headings should orient, not shout.
- Text scales should clearly separate hero labels, utility labels, and small
  technical readouts.
- Meters and analyzers should read quickly without becoming the dominant color
  event.
- Borders and section frames should organize space, not simulate skeuomorphic
  panels.

Hierarchy order:

1. hero surface
2. selected-object rail or utility rail
3. global state controls
4. monitoring elements such as meters or analyzer overlays
5. small labels and technical readouts

## State Encoding

The UI must encode state consistently across devices.

State types:

- selected
- enabled or disabled
- bypassed
- listen or solo
- analyzer source or mode
- quality or latency class
- warning states such as clipping or self-oscillation risk

Rules:

- Selected is not the same as enabled.
- Audio-affecting states must be more legible than display-only states.
- Warning states should feel rare and intentional.
- If one color means “selected,” do not reuse it for unrelated “armed” or
  “enabled” meaning in the same local area.
- When a state changes processing and not only display, the control and the
  readout should both make that clear.

## Analyzer And Meter Semantics

Measurement UI must stay truthful.

Rules:

- Separate analysis truth from display smoothing.
- Make pre/post or source-routing state explicit.
- Analyzer overlays must remain visually secondary to the main edit target.
- Meter behavior should support decisions, not decorate dead space.
- Peak or hold layers should never imply live activity when they are stale.

Shared analyzer language across devices should define:

- source selection
- block or resolution
- refresh
- averaging
- hold or max behavior
- overlay alpha or display priority

## Direct Manipulation

Direct manipulation must feel intentional and learnable.

Rules:

- Drag behavior must match the visual model.
- Fine-edit modifiers must be stable across devices.
- Hover or focus affordances should reveal editability without constant motion.
- The display must confirm what changed while the gesture is in progress.
- Direct manipulation should replace slow widget travel, not mirror it.

Direct-manipulation checklist:

- Is the hit target obvious?
- Does the dragged object stay visually anchored?
- Is the active object still obvious during the gesture?
- Is there a predictable fine-adjust path?
- Does the result land in the contextual editor without drift?

## Parameter Naming And Grouping

Parameters must be grouped by product task, not implementation plumbing.

Rules:

- Bank names should describe user tasks.
- Long and short names should stay semantically aligned.
- Display-only controls must not pretend to be audio-facing.
- Hidden duplicates must be disabled, not silently exposed.
- Contextual controls should share naming patterns with the objects they edit.

Default grouping patterns:

- `Global`: device-wide output, analyzer, range, mode, quality
- `Object Core`: frequency, gain, Q, enable, type
- `Object Motion`: rate, depth, direction, modulation amount
- `Monitoring`: source, averaging, hold, graph mode

## Repo Practice Loop

Every major UI sprint must leave these artifacts behind:

- updated per-device design doc in `plugins/<lane>/README.md`
- one weekly teardown note created from
  `docs/ableton_ui_teardown_template.md`
- one validation note created from
  `docs/ableton_ui_validation_template.md`
- updated findings in Phren when a non-obvious pattern becomes clear

Use `docs/ableton_ui_review_checklist.md` as the common weekly gate.

## Definition Of Done For A Flagship UI Sprint

Do not call a sprint complete unless all of these are true:

- one surface is obviously primary
- selected-object editing is contextual and canonical
- compact and expanded states do not fight each other
- analyzer and meter behavior are semantically clear
- parameter grouping reflects product tasks
- in-Live validation confirms fast, precise, and exploratory edits all work
- the device feels more like one product than a collection of widgets
