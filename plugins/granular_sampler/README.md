# Granular Sampler

## Summary

`Granular Sampler` should be the sample-editor and scrub-performance lane in
this repo: a dual-surface granular instrument that feels closer to
Simpler-style sample interaction than to a loose collection of grain knobs.

The current repo already has granular ingredients. This product should turn them
into a real instrument.

## Problem

The repo can already demonstrate granular playback, but not yet a serious sample
instrument workflow.

Current gaps:

- [`examples/granular_looper.py`](../../examples/granular_looper.py) proves the
  family but still behaves like a small demo
- there is no dedicated product lane for waveform interaction, region editing,
  and scrub-based grain control
- the framework has grain and waveform engines, but not yet a flagship device
  that forces compact-vs-editor UI decisions

So this lane exists to answer:

1. can the repo support a real sample-editing instrument workflow
2. can the builder grow a strong dual-surface shell pattern
3. can waveform interaction become first-class instead of ornamental

## Why This Exists

This should be one of the most important framework-stressing products in the
repo.

It matters because it pushes on:

- buffer and file workflows
- waveform displays
- sample region editing
- compact vs expanded device presentation
- modulation tied to spatial interaction instead of only dials

If the repo can make this lane feel good, it is a much stronger case that
`m4l-builder` can support flagship instruments, not only effects.

## Design Goals

- feel like a playable sample instrument first, granular processor second
- make region selection and scrub position visually obvious
- allow expressive control of grain size, density, spray, pitch, and motion
- support both imported samples and live-captured material
- separate compact performance mode from deeper editor mode

## Non-Goals

- becoming a full Sampler replacement in v1
- adding full warp modes, slicing, multisample mapping, and spectral granulation
  all at once
- shipping a granular instrument with no meaningful waveform interaction

## Core Method

Recommended v1 architecture:

- RAM-backed sample source using `buffer~`
- sample intake through file drop and optionally live record
- a grain playback engine based on the existing `grain_cloud` path
- waveform display and draggable region editing
- modulation and randomization around a clear playback zone

The current repo already has the right foundations for this:

- `grain_cloud()` in [`src/m4l_builder/dsp.py`](../../src/m4l_builder/dsp.py)
- grain-oriented display in
  [`src/m4l_builder/engines/grain_display.py`](../../src/m4l_builder/engines/grain_display.py)
- waveform-oriented display in
  [`src/m4l_builder/engines/waveform_display.py`](../../src/m4l_builder/engines/waveform_display.py)

## Signal Flow / Algorithm

Recommended conceptual path:

`sample source -> region selection -> grain position generator -> grain cloud voices -> per-grain envelope / pitch / spread -> output stage`

Primary playback controls:

- `Start`
- `End`
- `Position`
- `Size`
- `Density`
- `Spray`
- `Pitch`
- `Direction`
- `Mix` or output level

Sample-source controls:

- file load / drop
- optional record into buffer
- one-shot vs loop region behavior

Recommended v1 behavior:

- visual region selection
- scrub or playhead interaction on the waveform
- stable live performance without needing the editor open all the time

## Why The Technical Claim Is Valid

Calling this `Granular Sampler` is valid if:

- the source is a real editable sample region
- playback is formed by repeated grain events or overlapping grain voices
- region, size, density, and position are central to the experience

If the device is only a rate-controlled looper with some jitter, the claim is
too weak.

## UI Model

This lane should be explicitly dual-surface.

Compact surface:

- performance controls
- immediate grain feel
- macro-level modulation and output

Expanded editor:

- waveform view
- region and loop markers
- scrub / playhead interaction
- sample intake / metadata
- deeper grain distribution controls

This is the clearest candidate in the repo for the queued dual-surface shell
task in Phren.

Reference shell spec:

- [`ui_shell_spec.md`](./ui_shell_spec.md)
- [`docs/dual_surface_shell_guidance.md`](../../docs/dual_surface_shell_guidance.md)

## Builder Dependencies / Framework Gaps

This lane depends on:

- waveform scrubber engine work
- better buffer/file handling helpers
- compact-vs-expanded shell support
- stronger parameter metadata for editor-only vs macro controls

The current queue already contains related pieces:

- waveform scrubber engine
- buffer / groove helpers
- granular scrubber device ideas
- direct-manipulation visualization work

So this product should consolidate those ideas into a single flagship lane
instead of keeping them fragmented.

## UI Sprint Alignment

- Primary Ableton reference: `Simpler`
- Shared standards:
  - [`docs/ableton_ui_playbook.md`](../../docs/ableton_ui_playbook.md)
  - [`docs/dual_surface_shell_guidance.md`](../../docs/dual_surface_shell_guidance.md)
  - [`docs/ableton_ui_review_checklist.md`](../../docs/ableton_ui_review_checklist.md)
- Current sprint focus:
  - compact playable identity vs expanded waveform editor
  - one canonical waveform-driven region editor
  - clear cross-surface state sharing
- Planned validation note:
  - [`docs/ui_validation/week_11_framework_reaudit.md`](../../docs/ui_validation/week_11_framework_reaudit.md)

## Validation

Automated validation should catch:

- buffer/source object defaults
- safe behavior when no sample is loaded
- emitted patch structure for grain voice counts
- editor state payload shape

In-Live validation should catch:

- whether waveform interaction feels fast and obvious
- whether compact mode remains useful after editor features are added
- whether grain density and spray are musical over a practical range
- whether loop and region edits stay synchronized with playback
- whether compact and expanded surfaces feel like one instrument instead of two
  unrelated views

## Future Work

- record-to-buffer live capture
- reverse and ping-pong region travel
- spectral or formant granulation variants
- slice-aware zone jumping
- per-note sample position for keyboard performance
