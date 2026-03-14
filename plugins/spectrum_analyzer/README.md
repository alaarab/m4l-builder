# Spectrum Analyzer

## Summary

`Spectrum Analyzer` should become the standalone measurement/display device for
this repo and the shared analyzer technology source for the EQ family.

This is not just a utility meter. It is the analyzer product lane that should
establish the FFT backend, averaging model, peak-hold behavior, and display
language used later behind `Parametric EQ` and `Linear Phase EQ`.

## Problem

The repo currently has analyzer visuals, but not yet a flagship analyzer
architecture.

The practical gaps are:

- the current reusable analyzer helper uses a `reson~` filter bank plus
  `peakamp~`, which is serviceable for lightweight overlays but is not the same
  thing as a real FFT spectrum analyzer
- the EQs need a background analyzer that feels closer to Ableton's own devices
- a future standalone analyzer should expose controls users already expect:
  block size, refresh, averaging, peak/max hold, graph style, and channel view

So this device exists to solve two problems at once:

1. build a proper analyzer product
2. create a better shared backend for the EQ overlays

## Why This Exists

This plugin should be treated as shared infrastructure disguised as a product.

It would prove:

- that `m4l-builder` can support a reusable FFT-analysis backend
- that a standalone measurement device and the EQ overlays can share the same
  analyzer data path
- that analyzer UI can be productized instead of bolted on as a side feature

This matters because the EQ line already depends on analyzer quality for trust.
If the analyzer is weak, the EQs feel weaker than they actually are.

## Design Goals

- match the feel of Ableton's `Spectrum` and `EQ Eight` analyzer workflow
- use a real FFT/STFT analysis path, not only a resonant filter-bank
  approximation
- make the backend reusable for both standalone and EQ-overlay use
- support explicit controls for resolution and smoothing
- keep the display fast enough for constant use behind an EQ graph
- allow subdued overlay rendering in EQ mode and richer controls in standalone
  mode

## Non-Goals

- replacing every meter/scope tool in the repo
- sonogram or spectrogram history in v1
- mastering-lab calibration claims
- phase scope, goniometer, loudness, or correlation features in the same first
  device
- pretending `spectroscope~` alone is sufficient for a flagship analyzer

## Core Method

The recommended method is a dedicated FFT analysis backend that computes
magnitude spectra from short audio windows, applies user-controlled temporal
averaging and peak hold, remaps the result to a log-frequency display, and
ships a compact list to a JSUI renderer.

That means:

- tap the audio without changing the audible path
- analyze it in the frequency domain
- separate analysis resolution from display smoothing
- reuse the same output format in the standalone analyzer and the EQ overlays

## Signal Flow / Algorithm

Recommended v1 architecture:

1. Source selection:
   - `L`
   - `R`
   - `Stereo Sum`
   - optional later: `Mid`, `Side`
2. Window/block selection:
   - user-facing block choices similar to Ableton `Spectrum`
   - larger blocks improve frequency resolution and worsen visual lag
3. FFT analysis:
   - use a dedicated FFT/STFT path rather than the current `reson~` filter bank
   - likely a `pfft~` support patch or equivalent FFT scaffold, because it
     exposes FFT window size and hop information clearly and matches future
     spectral work in the repo
4. Magnitude extraction:
   - convert real/imaginary FFT bins to magnitude
   - convert to dB for display
5. Averaging / peak handling:
   - short-term smoothing for the main trace
   - optional peak or max hold layer
   - refresh/update control independent from raw FFT size
6. Display remap:
   - remap FFT bins to a log-frequency display
   - optionally apply display weighting/tilt later if needed
7. JSUI render modes:
   - filled analyzer graph
   - line mode
   - peak/max markers
   - overlay mode with subdued alpha for EQ backgrounds

### Recommended Shared Architecture

The standalone plugin and EQ overlays should share:

- the same FFT-analysis backend
- the same output list format
- the same smoothing and hold semantics

Only the presentation should differ:

- standalone analyzer: full controls and larger graph
- EQ overlay: same data, fewer controls, subdued rendering behind the curves

## Why The Technical Claim Is Valid

If this device is called `Spectrum Analyzer`, the displayed spectrum should
come from FFT-derived magnitude data, not only from a bank of tuned filters.

That distinction matters because:

- a filter-bank approximation gives "energy by band" behavior
- an FFT analyzer gives actual spectral-bin magnitude over a chosen analysis
  window
- Ableton's own `Spectrum` device is explicitly built around resolution,
  refresh, average, and graph controls that make sense in an FFT analysis model

So the analyzer claim is valid only if the visible graph is derived from a real
frequency-domain analysis path.

## Alternatives Considered

### 1. Keep the current `reson~` + `peakamp~` helper

Pros:

- simple
- cheap to wire
- fine for lightweight generic overlays

Cons:

- not a true FFT analyzer
- weaker control over resolution vs smoothing
- not the right foundation for a flagship analyzer product

This should remain a fallback helper, not the final analyzer architecture.

### 2. Use `spectroscope~` directly as the full product

Pros:

- official Max object
- already exposes useful visual attributes like `logfreq`, `logamp`, `domain`,
  `range`, `interval`, and sonogram/spectrogram modes
- fast way to get something on screen

Cons:

- control model does not match Ableton `Spectrum` closely enough on its own
- harder to unify with custom EQ overlay styling and shared JS behavior
- less ownership over peak hold, overlay alpha, and product-specific UI

This is a good baseline reference and maybe part of a prototype, but not the
final flagship path.

### 3. Dedicated FFT backend plus custom JSUI renderer

Pros:

- best fit for matching Ableton-style analyzer behavior
- reusable between standalone and EQ overlays
- complete control over averaging, hold behavior, channel views, and display
  styling

Cons:

- more implementation work
- more parameters and QA surface
- more opportunities to make visual smoothing lie if the semantics are sloppy

This is the recommended path.

## UI Model

The standalone analyzer should follow the logic of Ableton `Spectrum`:

- top-row utility controls
- one large graph as the primary surface
- minimal chrome around the display

Suggested v1 controls:

- `Block`
- `Refresh`
- `Avg`
- `Max`
- `Graph`
- `Channel`

Suggested display behavior:

- main filled/line spectrum trace
- peak or max-hold trace
- frequency and level readout on hover
- optional freeze later, but not required in the first cut

### EQ Reuse Plan

The EQs should not implement their own separate analyzer backend.

Instead:

- build the standalone analyzer backend first
- feed the same list format into the EQ graph engine
- expose fewer controls in EQ mode
- keep the overlay visually secondary to the filter curves

For the EQ overlays specifically:

- `Parametric EQ` should get a richer analyzer overlay with optional pre/post
  source and better smoothing than the current helper
- `Linear Phase EQ` should reuse the same backend but keep analyzer alpha lower
  and avoid fighting with the graph labels, chip row, and latency messaging

## Parameter Semantics

- `Block` changes FFT window size or equivalent analysis size.
  It should change frequency resolution and visual lag, not the audible signal
  path.
- `Refresh` changes how often the UI updates.
  It should not be confused with FFT size.
- `Avg` changes temporal smoothing of the visible trace.
  Higher averaging is steadier but less responsive.
- `Max` controls peak or max-hold visibility and/or hold time.
- `Graph` changes display style, not the analysis math itself.
- `Channel` changes the tapped analysis source.

## Tradeoffs And Limitations

- larger FFT blocks improve low-frequency readability but add display lag
- stronger averaging makes the graph prettier but less truthful for fast
  transients
- peak/max hold helps readability but can make a stale display feel "hotter"
  than the live signal
- log-frequency remapping improves usability but requires deliberate bin
  interpolation or grouping choices
- a custom analyzer will need more QA than the stock `spectroscope~` object

## Validation

Automated checks should eventually verify:

- support files are emitted
- analyzer control defaults are wired
- block-size changes update backend config
- display messages are shaped correctly for standalone and overlay use

In-Live validation should verify:

- comparison against Ableton `Spectrum` on sine, pink noise, white noise, and
  swept-sine material
- EQ overlay alignment against the same input signal
- expected low-frequency readability at larger block sizes
- peak/max behavior under transient material
- refresh and averaging behavior that feels stable without becoming misleading

## References

- Ableton `Spectrum` manual section:
  [https://www.ableton.com/en/manual/live-audio-effect-reference/#spectrum](https://www.ableton.com/en/manual/live-audio-effect-reference/#spectrum)
- Ableton `EQ Eight` manual section:
  [https://www.ableton.com/en/manual/live-audio-effect-reference/#eq-eight](https://www.ableton.com/en/manual/live-audio-effect-reference/#eq-eight)
- Cycling '74 `spectroscope~`:
  [https://docs.cycling74.com/reference/spectroscope~/](https://docs.cycling74.com/reference/spectroscope~/)
- Cycling '74 `fft~`:
  [https://docs.cycling74.com/reference/fft~/](https://docs.cycling74.com/reference/fft~/)
- Cycling '74 `pfft~`:
  [https://docs.cycling74.com/reference/pfft~/](https://docs.cycling74.com/reference/pfft~/)
- Cycling '74 `cartopol~`:
  [https://docs.cycling74.com/reference/cartopol~/](https://docs.cycling74.com/reference/cartopol~/)
- Cycling '74 `framesnap~`:
  [https://docs.cycling74.com/reference/framesnap~/](https://docs.cycling74.com/reference/framesnap~/)
- Current repo analyzer helper:
  [`src/m4l_builder/engines/spectrum_analyzer.py`](../../src/m4l_builder/engines/spectrum_analyzer.py)
- Current EQ lineup notes:
  [`docs/eq_lineup.md`](../../docs/eq_lineup.md)

## Future Work

- add a true spectrogram / sonogram mode
- add Mid/Side and stereo-difference views
- add freeze and delta modes
- add analyzer calibration/tilt options if the visual feel needs it after
  direct comparison with Ableton `Spectrum`
- replace the current EQ filter-bank analyzer helper with this backend once the
  standalone analyzer path is validated
