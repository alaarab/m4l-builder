# Ladder Filter

## Summary

`Ladder Filter` should be the character-first flagship filter lane in this repo.

It is the everyday modulation filter with enough weight and nonlinearity to feel
like an instrument-grade effect instead of a generic utility cutoff block.

This lane should sit between:

- the existing lightweight filter examples
- the future direct-manipulation filter UI framework
- the broader modulation lane shared with LFO, envelope follower, and sidechain
  work

## Problem

The repo already has useful filter primitives, but not yet a real filter
product with a strong sonic identity.

Current gaps:

- existing examples prove filter wiring, not flagship filter behavior
- the modulation lane is split across `Auto Filter`, `Morphing Filter`, and
  small examples instead of a single high-confidence product
- the codebase can assemble filter blocks quickly, but it does not yet expose a
  dedicated non-linear ladder-style DSP block with explicit self-oscillation
  handling

So this lane exists to answer a more serious product question:

1. can `m4l-builder` ship a genuinely musical filter product
2. can the builder support character DSP instead of only clean utility chains
3. can filter modulation become graph-first and performance-friendly

## Why This Exists

This should be the filter device people reach for first.

It matters because a believable ladder filter becomes a proving ground for:

- non-linear DSP blocks
- sidechain-aware modulation
- stereo motion and spread behavior
- direct curve editing that feels native instead of decorative

If this lane stays weak, the repo keeps looking stronger at EQ and routing than
at sound-shaping.

## Design Goals

- sound like a driven, resonant musical filter instead of a polite utility
- make cutoff and resonance feel immediate under automation and gesture control
- support direct movement by LFO, envelope follower, and later external
  sidechain
- support multiple mode families without losing the core ladder identity
- keep the UI compact enough for everyday use but expressive enough to feel
  flagship

## Non-Goals

- becoming a generic filter encyclopedia in v1
- replacing every clean SVF or cookbook filter example in the repo
- implementing every vintage ladder variant before the first strong product cut
- pretending a plain cascade of static filters is enough if the sonic result is
  not convincing

## Core Method

Recommended v1 architecture:

- pre-drive stage
- four cascaded one-pole stages
- non-linear feedback path around the ladder
- mode taps for LP / HP / BP / notch-family outputs
- post-trim / clip safety after resonance and drive interaction

This should be treated as a dedicated DSP lane, not just a wrapper around the
existing clean filter helpers.

The current repo can prototype the control topology with existing blocks in
[`src/m4l_builder/dsp.py`](../../src/m4l_builder/dsp.py), but the final product
should add a proper ladder-oriented building block so the sonic claim is real.

## Signal Flow / Algorithm

Recommended signal path:

`plugin~ -> input trim / drive -> ladder core -> mode selection -> output trim -> dry/wet / plugout~`

Modulation path:

- base cutoff
- key or note tracking later if needed
- envelope follower amount
- LFO amount / rate / shape
- optional sidechain detector later
- stereo offset / phase spread

Important behavior:

- resonance should have a deliberately managed self-oscillation range
- drive should change the filter behavior, not only the output loudness
- modulation should be smoothed enough to avoid zippering without making the
  device feel sluggish
- stereo motion should be intentional, not accidental channel mismatch

## Why The Technical Claim Is Valid

Calling this `Ladder Filter` is valid only if the device exposes:

- ladder-style cascaded poles
- a feedback behavior that produces the expected resonance character
- non-linear drive or saturation in the filter path

If the implementation is just a clean static filter bank with ladder-themed UI,
the claim is weak.

So the bar for this lane is higher than "a filter with a resonance knob."

## UI Model

The UI should feel like a performance filter, not a lab instrument.

Recommended v1 layout:

- hero curve / response surface at the top
- a strong central cutoff control
- drive, resonance, and mode as primary controls
- modulation rail for env, LFO, stereo spread, and mix
- compact meters / output trim at the edge

Recommended interaction priorities:

- drag directly on the response display for cutoff / resonance
- one-glance read of mode, drive state, and modulation depth
- obvious stereo motion when stereo spread is active
- clear visual warning when resonance enters self-oscillation territory

## Builder Dependencies / Framework Gaps

This lane depends on or benefits from:

- the direct-manipulation visualization task already queued in Cortex
- better parameter metadata for long/short names and units
- a dedicated ladder-style DSP helper beyond the current clean filter blocks
- explicit self-oscillation protection / clip-safety handling
- stronger filter-display semantics than a static curve alone

Immediate reusable primitives already exist for prototyping:

- filter and EQ blocks in [`src/m4l_builder/dsp.py`](../../src/m4l_builder/dsp.py)
- filter graph UI in
  [`src/m4l_builder/engines/filter_curve.py`](../../src/m4l_builder/engines/filter_curve.py)
- modulation helpers like `morphing_lfo` and `envelope_follower`

## UI Sprint Alignment

- Primary Ableton reference: `Auto Filter`
- Shared standards:
  - [`docs/ableton_ui_playbook.md`](../../docs/ableton_ui_playbook.md)
  - [`docs/ableton_ui_review_checklist.md`](../../docs/ableton_ui_review_checklist.md)
- Current sprint focus:
  - one obvious central cutoff or response gesture
  - performance-readable modulation state
  - warning behavior for resonance and self-oscillation that stays useful
- Planned validation note:
  - [`docs/ui_validation/week_09_ladder_filter.md`](../../docs/ui_validation/week_09_ladder_filter.md)

## Validation

Automated validation should catch:

- emitted patch structure
- mode switching defaults
- safe initial resonance and drive ranges
- parameter naming and smoothing assumptions

In-Live validation should catch:

- whether resonance actually feels ladder-like
- whether drive changes tone in a useful way
- whether self-oscillation is musical instead of broken
- whether the hero display is editing-relevant rather than ornamental
- whether stereo spread feels deliberate and controllable
- whether the compact surface still feels like a musical filter rather than a
  technical modulation panel

## Future Work

- external sidechain detector mode
- slope or model variants if the core lane proves strong
- filter-motion recording / playback gestures
- MPE or note-tracking variants for instrument use
