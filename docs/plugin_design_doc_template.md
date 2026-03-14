# Plugin Design Doc Template

Use this for shipped plugin `.md` docs in `plugins/<plugin>/README.md`.

The goal is not marketing copy. The goal is to explain what problem the plugin
solves, why it exists, how it works, and what tradeoffs come with the chosen
approach.

## Summary

One short paragraph:

- what the plugin is
- who it is for
- whether it is a fast mix tool, precision tool, creative effect, etc.

## Problem

Explain the practical problem.

Questions to answer:

- What workflow or sound-shaping problem is this plugin trying to solve?
- Why would a user reach for this instead of a simpler tool?
- What failure mode or missing capability made the plugin worth building?

## Why This Exists

Explain the project context.

Questions to answer:

- Why was this plugin made in this repo?
- What was it trying to prove or teach?
- Was it a product lane, a framework testbed, or both?

## Design Goals

List the things the plugin must do well.

## Non-Goals

List what the plugin is intentionally not trying to be.

This keeps the implementation honest and prevents feature drift.

## Core Method

Describe the chosen technical approach in plain language before going into the
details.

Examples:

- cascaded IIR biquads
- FFT-domain magnitude shaping
- convolution
- granular playback from shared buffers
- control-signal modulation into a mapped target system

## Signal Flow / Algorithm

Explain the actual algorithm or processing path.

This section should be explicit.

If there is an algorithm, explain:

- the main stages
- what data each stage produces
- how control state becomes audio behavior
- where any tables, kernels, buffers, or state engines come from

If useful, include a numbered step list or a small ASCII signal-flow diagram.

## Why The Technical Claim Is Valid

This section must justify the name of the plugin when the name makes a
technical claim.

Examples:

- Why is it linear phase?
- Why is it minimum phase?
- Why is it multiband?
- Why is it actually sidechain-aware?
- Why is it polyphonic?

Do not hand-wave here. State what property of the algorithm makes the claim
true.

## Alternatives Considered

Explain the main alternatives and why this approach was chosen.

Questions to answer:

- What would the simpler approach have been?
- What would the lower-latency or lower-CPU approach have been?
- What would the more exact but more expensive approach have been?
- Why is the current method the right fit for this plugin instead of just "a"
  fit?

## UI Model

Explain how the UI is supposed to work and why it is organized that way.

Questions to answer:

- What is the main editing surface?
- What stays visible all the time?
- What is contextual?
- What belongs in menus or context menus instead of visible rails?

## Parameter Semantics

Explain how the main parameters behave.

This is the place to note:

- whether a control is audio-facing or UI-facing
- whether a mode changes processing or only display
- when a parameter is ignored by some band or engine types
- how quality, latency, or routing options change behavior

## Tradeoffs And Limitations

Be explicit about the costs of the chosen method.

Examples:

- latency
- pre-ringing
- CPU cost
- phase rotation
- approximation error
- visual/UI compromises
- mode-dependent limitations

## Validation

Explain how the plugin should be checked.

Include:

- automated tests that matter
- in-Live checks that matter
- what would count as a regression

## References

Link the sources that support the technical claims in the document.

Prefer:

- official docs
- implementation files in this repo
- papers or well-known technical references
- discussion threads only when they add practical nuance that the official docs
  do not cover

If the document makes a latency, filter-topology, or algorithm claim, include
the source links here.

## Future Work

List the next important improvements without pretending they already exist.
