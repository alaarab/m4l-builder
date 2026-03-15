# Linear Phase EQ

## Summary

`Linear Phase EQ` is the precision, slower, mastering-oriented EQ lane in this
repo. It is the counterpart to the fast minimum-phase `Parametric EQ` and the
routing-oriented `Linear Phase Crossover`.

This device exists for situations where EQ moves need to preserve relative
phase between frequencies, even if that means paying in latency, FFT size, and
some pre-ringing risk.

## Problem

The practical problem is straightforward:

- normal minimum-phase EQ is fast and flexible, but it rotates phase
- that phase rotation is often fine in mixing, but not always desirable for
  mastering-style tonal correction or phase-sensitive parallel work
- the project also needed a flagship EQ device that made latency and quality
  explicit instead of hiding them

So this plugin is trying to solve a different problem than the regular
parametric EQ. It is not "the same EQ but more expensive." It is a separate
processing model with a separate product role.

## Why This Exists

This plugin was built to learn and prove several things at the same time:

- that `m4l-builder` could ship a product-specific flagship UI rather than only
  utility devices
- that a graph, selected-band controls, analyzer state, and quality state could
  stay synchronized through a local JS state engine
- that the project could turn familiar EQ band concepts into an FFT-domain
  linear-phase processor instead of only generating direct `biquad~` chains

In other words, this device is both a product lane and a framework testbed.

## Design Goals

- Make linear-phase processing the first-class idea, not a hidden mode.
- Keep the main interaction graph-first and analyzer-aware.
- Expose quality and latency together so the user understands the cost.
- Preserve the familiarity of common EQ band types instead of inventing a
  strange frequency-domain control model.
- Keep the UI distinct from `Parametric EQ` and from the crossover device.

## Non-Goals

- zero latency
- minimum CPU usage
- dynamic EQ
- crossover-style band routing
- pretending this is the right EQ for every task

## Core Method

The core method is:

1. describe the desired EQ shape using familiar band models
2. turn that shape into a magnitude response table for each FFT quality tier
3. apply that magnitude table inside `pfft~` by multiplying incoming FFT bins

This is not implemented as a bank of time-domain linear-phase FIR sections per
band. Instead, the plugin computes the desired composite magnitude response and
applies it in the frequency domain.

## Signal Flow / Algorithm

The implementation currently works like this:

1. A local JS state engine tracks the eight bands, the selected band, solo
   state, quality mode, and sample rate.
2. Each band is modeled with familiar EQ-band math using biquad-style
   coefficient formulas:
   - Peak
   - LShelf
   - HShelf
   - LCut
   - HCut
   - Notch
   - BPass
3. For each quality mode, the state engine evaluates the composite response at
   each FFT bin frequency:
   - `Short`: 2048
   - `Medium`: 4096
   - `High`: 8192
4. The composite dB response is converted to linear gain and written into a
   `buffer~`.
5. The active `pfft~` kernel reads that buffer with `index~` and multiplies
   both the real and imaginary FFT components by the same real-valued gain.
6. Three prebuilt `pfft~` kernels exist at once, and the quality selector
   switches between them.
7. The UI latency readout is derived from the active FFT size and the current
   `pfft~` overlap factor. The implementation uses `pfft~ ... N 4`, so:

   `hop_size = FFT_size / 4`

   `latency_ms = (FFT_size - hop_size) / sample_rate * 1000`

At 48 kHz, the current quality tiers introduce roughly:

- `Short`: 32.0 ms
- `Medium`: 64.0 ms
- `High`: 128.0 ms

The current listen workflow is also frequency-domain. When a band is in
`LISTEN`, the state engine rebuilds the response table into an audition mask
that emphasizes the selected band region instead of leaving the full EQ curve
unchanged.

Important approximation note:

- the device evaluates the target response at FFT bin centers, not at every
  continuous frequency
- that means extremely narrow features are quantized to the current FFT
  resolution
- increasing quality improves that resolution, but it also increases latency

## Why The Technical Claim Is Valid

This device is called `Linear Phase EQ` because the audio shaping is done by
applying a real-valued magnitude response in the FFT domain rather than by
running the signal through minimum-phase IIR bands.

Why that matters:

- a normal IIR EQ changes both magnitude and phase
- this device computes the desired magnitude response and applies that
  magnitude directly to the FFT bins
- within the current `pfft~` block-processing model, that means the shaping
  stage does not add the band-dependent phase rotation you would get from
  minimum-phase IIR sections
- the real-time implementation then pays for causality with a constant system
  delay, which is the latency shown in the UI

So the important property is not "uses FFT, therefore linear phase." The
important property is "applies a magnitude-only spectral response and pays the
cost as constant delay instead of frequency-dependent phase rotation."

## Alternatives Considered

This is not the only defensible way to build a linear-phase EQ.

### 1. Cascaded IIR biquads

This is what the repo's `Parametric EQ` does.

Pros:

- very low latency
- efficient
- familiar implementation path in Max using `filtercoeff~` + `biquad~`

Cons:

- minimum-phase behavior is part of the sound
- it does not solve the "preserve relative phase" job this device exists for

### 2. Direct FIR design plus convolution

Another linear-phase route is to design a symmetric FIR kernel directly and
convolve with it. In Max terms, [`buffir~`](https://docs.cycling74.com/reference/buffir~/)
is the most obvious official FIR object, and its docs explicitly describe it
as a finite impulse response filter that reads coefficients from a buffer.

Pros:

- conceptually direct
- very clear relationship between FIR design and linear-phase behavior
- good fit for fixed or shorter FIR responses

Cons:

- coefficient management becomes awkward when the EQ curve is continuously
  rebuilt from eight interactive bands
- `buffir~` is documented as supporting up to 4096 coefficients, which is not
  the same design space as arbitrarily long interactive FIR responses

### 3. FFT-domain block filtering

This is the route the current device takes using `pfft~`.

Pros:

- it matches an interactive graph-driven EQ where the composite response is
  redrawn often
- quality tiers map naturally to FFT size, latency, and frequency resolution
- longer effective responses are more practical than a naive time-domain FIR
  path

Cons:

- latency is structural, not incidental
- resolution is quantized to the current FFT size
- STFT-style processing brings windowing/block tradeoffs, not just "free FIR"

So is this the best way? Not universally. It is the best fit for this specific
plugin if the priorities are:

- interactive spectral shaping from familiar EQ bands
- explicit quality tiers
- mastering-style tolerance for latency

If the priority is low-latency mixing, the `Parametric EQ` route is better. If
the priority is a fixed FIR or a shorter static linear-phase filter, direct FIR
convolution is a credible alternative.

## UI Model

The current device is organized around:

- a hero graph as the main editing surface
- explicit quality and analyzer controls in the top area
- a selected-band strip
- a band-chip row for quick navigation

The design target is documented in
[`docs/linear_phase_eq_ui.md`](../../docs/linear_phase_eq_ui.md).

Current interaction model:

- graph interaction is primary
- quality and analyzer state are always visible
- the chip row is navigation, not deep editing
- the selected-band controls are currently a compact strip

Known direction:

- the backlog is intentionally moving this toward an EQ Eight-style selected
  band control column with real contextual knobs
- the bottom strip is not the intended final flagship interaction model

## Parameter Semantics

- `Quality` changes FFT size, latency, and frequency resolution.
- `Analyzer` switches analyzer state and source visibility, not the core EQ
  algorithm itself.
- `LISTEN` is not a harmless visual toggle; it changes the active response
  table into an audition mask.
- Cut slopes matter only for the cut band families.
- Band enable/disable changes the active response table, not just UI state.

## Tradeoffs And Limitations

- latency is unavoidable and is currently tied to both FFT size and the
  `pfft~` overlap setting
- pre-ringing is a real possibility for sharp or aggressive moves
- frequency resolution and latency are coupled
- the target curve is sampled onto FFT bins, so the response is an
  approximation of the continuous ideal band model
- quality switching is not free because it depends on separate FFT kernels and
  response tables
- the current selected-band strip is serviceable but not yet the intended
  flagship control model
- this is not the device to reach for when fast, low-latency mix moves matter
  more than phase behavior

## UI Sprint Alignment

- Primary Ableton references: `EQ Eight`, `Spectrum`
- Shared standards:
  - [`docs/ableton_ui_playbook.md`](../../docs/ableton_ui_playbook.md)
  - [`docs/ableton_ui_review_checklist.md`](../../docs/ableton_ui_review_checklist.md)
- Current sprint focus:
  - contextual selected-band column instead of the compact strip as the final
    editor
  - stronger graph, chip, and selected-band sync
  - clearer quality, latency, analyzer, and listen state
- Planned validation note:
  - [`docs/ui_validation/week_05_linear_phase_eq.md`](../../docs/ui_validation/week_05_linear_phase_eq.md)

## Validation

Automated validation already checks important structural details:

- required support files are emitted
- analyzer objects exist and are wired
- quality and analyzer controls initialize correctly
- JS display/state support functions are present

That is necessary but not sufficient.

In-Live validation should confirm:

- signal actually passes through all quality tiers
- latency readout matches the expected quality mode
- graph, chip row, and selected-band controls stay synchronized
- `LISTEN` behaves like a useful audition workflow rather than a fake toggle
- analyzer visibility is useful behind the graph, not just technically present
- latency readout matches the actual `pfft~` overlap-delay behavior
- the selected-band editor reads as precision-first rather than utility-strip
  editing

## References

- Implementation: [`plugins/linear_phase_eq/build.py`](./build.py)
- UI design target: [`docs/linear_phase_eq_ui.md`](../../docs/linear_phase_eq_ui.md)
- Cycling '74 `pfft~`: [https://docs.cycling74.com/reference/pfft~/](https://docs.cycling74.com/reference/pfft~/)
- Cycling '74 `fftin~`: [https://docs.cycling74.com/reference/fftin~/](https://docs.cycling74.com/reference/fftin~/)
- Cycling '74 `fftout~`: [https://docs.cycling74.com/reference/fftout~/](https://docs.cycling74.com/reference/fftout~/)
- Cycling '74 `buffir~`: [https://docs.cycling74.com/reference/buffir~/](https://docs.cycling74.com/reference/buffir~/)
- SciPy `firwin2` linear-phase FIR design reference: [https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.firwin2.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.firwin2.html)

## Future Work

- replace the current bottom selected-band strip with a contextual knob column
- tighten graph/chip/selected-band synchronization edge cases
- make the analyzer and audition workflows feel more deliberate
- document and verify the exact audible behavior of quality switching in Live
- add the structured `.md` design-doc standard across other flagship devices
