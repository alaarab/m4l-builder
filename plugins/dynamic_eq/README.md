# Dynamic EQ

## Summary

`Dynamic EQ` should be the premium extension of the existing parametric EQ lane:
an everyday minimum-phase EQ where each band can move between static shaping and
threshold-driven dynamic correction.

This is not a separate replacement for `Parametric EQ`.
It is the "surgical but musical" lane that builds directly on the graph,
selected-band editing, and analyzer work already underway.

## Problem

The repo has a strong direction for static EQ, but the next meaningful step is
adaptive behavior per band.

Current gaps:

- the parametric lane can already express graph-first band editing, but not
  per-band dynamic reaction
- the compressor and sidechain lanes have detector concepts, but not yet banded
  EQ-specific dynamics
- the current analyzer and selected-band work is valuable, but the highest-value
  follow-up is a product that uses that surface for real corrective workflow

So this lane exists to answer:

1. can the repo support per-band detector logic without collapsing into a clumsy
   multiband compressor UI
2. can the selected-band column become a true contextual editor
3. can the graph show dynamic behavior in a way that helps instead of distracting

## Why This Exists

This is the premium EQ lane for modern mixing work.

It matters because it pulls together several ongoing framework investments:

- analyzer backend
- selected-band contextual controls
- parameter metadata
- band-level state synchronization

If those investments stop at static EQ, the repo leaves a lot of product value
on the table.

## Design Goals

- keep the speed and familiarity of `Parametric EQ`
- allow any band to switch between static and dynamic behavior
- make dynamic settings feel like an extension of band editing, not a separate
  processor bolted onto the side
- visualize gain reduction and detector behavior clearly enough to build trust
- preserve a graph-first workflow while making the selected-band rail more
  useful than the graph alone

## Non-Goals

- becoming a mastering-first linear-phase product
- turning into a full multiband compressor in disguise
- forcing every band into dynamic mode by default
- overloading v1 with external sidechain, M/S, and every detector topology at
  once

## Core Method

Recommended v1 architecture:

- reuse the existing minimum-phase serial biquad EQ path from the parametric
  lane
- add per-band detector logic that measures band energy and drives dynamic gain
  reduction or expansion around the selected static curve
- keep the EQ topology minimum phase and responsive

In practical terms:

- each band still owns frequency, gain, Q, type, and enable state
- dynamic mode adds threshold, range, attack, release, and detector amount
- the band's effective gain becomes the result of static gain plus dynamic
  correction

The underlying audio path should still feel like a fast mix EQ, not a
block-processed mastering processor.

## Signal Flow / Algorithm

Recommended conceptual band flow:

`input -> band detector tap -> detector smoothing -> dynamic gain decision -> filtercoeff~ / biquad~ band -> next band`

Per-band dynamic behavior:

- `Threshold`: when correction begins
- `Range`: maximum upward or downward move
- `Attack`: how quickly the band responds
- `Release`: how quickly it recovers
- `Mode`: cut-first in v1, optional boost/expand later

Recommended v1 product scope:

- downward dynamic gain per band
- internal detector based on the band region itself
- graph indication of live gain movement

Later extensions:

- external sidechain detector source
- split-band detector audition
- M/S-aware dynamic modes

## Why The Technical Claim Is Valid

Calling this `Dynamic EQ` is valid if:

- the audio path is still an EQ, not a disguised crossover compressor
- band movement is threshold-dependent and time-dependent
- the user can define static tonal intent and dynamic correction range

If the product only sweeps filter gains manually or uses crude automation, the
claim is weak.

## UI Model

The UI should inherit the parametric lane's graph-first identity.

Recommended v1 layout:

- analyzer-backed hero graph
- node-based band editing
- selected-band detail rail that changes when dynamic mode is enabled
- compact indicators for threshold activity and live gain reduction

Recommended selected-band control sets:

- static mode: freq, gain, Q, type, slope where relevant
- dynamic mode: threshold, range, attack, release, plus a simple detector or
  mode switch

Graph behavior:

- the static target curve remains visible
- dynamic movement should read as activity around that curve, not replace it
- selected/hovered band activity should be emphasized more than all-band noise

## Builder Dependencies / Framework Gaps

This lane depends on:

- the ongoing parametric EQ selected-band work
- the analyzer backend task already queued in Cortex
- stronger parameter metadata and visibility controls
- a clean jsui contract for graph + state synchronization

Existing repo pieces already support the concept:

- the parametric EQ product brief in
  [`plugins/parametric_eq/README.md`](../parametric_eq/README.md)
- filter and detector primitives in
  [`src/m4l_builder/dsp.py`](../../src/m4l_builder/dsp.py)
- EQ-graph engines in
  [`src/m4l_builder/engines/eq_curve.py`](../../src/m4l_builder/engines/eq_curve.py)
  and
  [`src/m4l_builder/engines/eq_band_column.py`](../../src/m4l_builder/engines/eq_band_column.py)

## Validation

Automated validation should catch:

- band defaults and dynamic-mode defaults
- expected parameter export and state synchronization
- graph engine support for dynamic-state payloads
- stable emitted patch structure for detector and band routing

In-Live validation should catch:

- whether the band response feels smooth under fast transients
- whether threshold and range are understandable without reading docs
- whether the graph tells the truth about dynamic movement
- whether the selected-band rail is actually faster than editing everything from
  the graph alone

## Future Work

- external sidechain mode
- upward dynamic mode / expansion behavior
- M/S dynamic operation
- detector audition and listen workflows
- analyzer-informed auto-focus or solo helpers
