# Parametric EQ

## Summary

`Parametric EQ` is the fast, graph-driven, minimum-phase EQ lane in this repo.
It is the main mix-oriented counterpart to the slower `Linear Phase EQ`.

The device combines an interactive analyzer-backed graph with eight cascaded
stereo biquad stages so it feels like a real flagship EQ product instead of a
simple utility patch.

## Problem

The plugin is trying to solve a different problem than the linear-phase device:

- provide a responsive everyday EQ for mixing work
- keep latency low enough that the EQ feels immediate
- make graph-based node editing a first-class workflow
- prove that `m4l-builder` can support a serious flagship UI instead of only
  racks of disconnected utility widgets

This is the EQ for speed, feel, and direct manipulation, not for phase-neutral
mastering moves.

## Why This Exists

This plugin was the main proving ground for several builder capabilities:

- the `eq_curve` `jsui` engine
- integrated analyzer-backed graph editing
- synchronization between graph gestures and patcher controls
- a flagship minimum-phase EQ lane distinct from the FFT-based linear-phase
  product

It was also a place to learn where generated Max patches stop
feeling like "assembled objects" and start feeling like a real product.

## Design Goals

- fast, low-latency EQ for mixing
- direct graph editing with visible nodes and analyzer support
- eight bands with familiar EQ types
- smooth parameter changes without zipper noise or coefficient clicks
- a layout that feels deliberate, not like a generic builder demo

## Non-Goals

- linear phase
- mastering-first latency tolerance
- dynamic EQ
- mid/side editing in the current version
- pretending the UI is finished when the EQ lane clearly wants a better
  selected-band control model

## Core Method

The core method is classic minimum-phase EQ:

- each band is an IIR biquad stage
- each stereo channel runs through the eight bands in series
- `filtercoeff~` computes the coefficients
- `biquad~` applies the filter

This is intentionally different from the `Linear Phase EQ` approach. Here the
device embraces the normal speed, efficiency, and phase behavior of IIR EQ.

## Signal Flow / Algorithm

Per channel, the signal path is:

`plugin~ -> biquad~ band 1 -> biquad~ band 2 -> ... -> biquad~ band 8 -> output gain -> plugout~`

Each band works like this:

1. Frequency, gain, Q, type, and enable state are stored as UI parameters.
2. Frequency, gain, and Q are smoothed through `pack` + `line~` over 20 ms.
3. Gain is converted from dB to linear before `filtercoeff~` because
   `filtercoeff~` expects linear gain, not dB.
4. `filtercoeff~` generates the five biquad coefficients at signal rate.
5. `biquad~` applies the resulting filter section.
6. Disabled bands switch `filtercoeff~` to `off`, producing passthrough
   behavior.

Important implementation details:

- `resamp 1` is sent to each `filtercoeff~` so sweeps are smoother
- no `sig~` objects are used for the parameter-to-signal path
- smoothing is one of the most important anti-click measures in the device

The analyzer path is separate from the main audio path and can be switched
between `OFF`, `PRE`, and `POST`.

## Why The Technical Claim Is Valid

This device is a parametric EQ in the conventional minimum-phase sense because:

- each band exposes the normal parametric controls:
  - frequency
  - gain
  - Q
  - type
- the filter sections are implemented as IIR biquads
- the device does not attempt to remove or linearize the phase rotation that
  naturally comes with those IIR sections

So the technical claim is:

- yes, it is a real parametric EQ
- no, it is not linear phase

That distinction is important because the project now has separate EQ lanes for
those two jobs.

## Alternatives Considered

### 1. FFT-domain linear-phase EQ

That is the route used by the repo's `Linear Phase EQ`.

Pros:

- phase-neutral spectral shaping
- quality tiers can expose precision vs latency directly

Cons:

- significantly higher latency
- more block-processing tradeoffs
- worse fit for a fast mix EQ

That is why this device stays minimum phase. The point here is immediacy.

### 2. FIR convolution-based linear-phase EQ

A direct FIR-convolution route is also possible, but it has the same core
problem for this product lane: more latency and more cost than a responsive
mix-first EQ wants.

### 3. Current IIR path

The chosen path is the standard Max route for this kind of device:

- `filtercoeff~` computes the coefficients
- `biquad~` applies them
- short `line~` ramps keep coefficient changes from clicking

That is not the most phase-neutral path. It is the right path when speed and
responsiveness matter more than phase preservation.

## UI Model

The current UI is built around:

- a top bar for focus, analyzer mode, and display range
- a large hero graph with draggable nodes and integrated analyzer
- a lower band-card area for the eight bands plus output and meters

Current interaction priorities:

- drag nodes for frequency and gain
- mouse wheel for Q
- graph-backed visual decision making
- focus-band selection from the top bar

Known direction:

- the backlog now explicitly moves this device toward an EQ Eight-style
  selected-band column with real contextual knobs
- the current bottom band-card arrangement works, but it is not the final UI
  target for the flagship EQ lane

## Parameter Semantics

- `Analyzer Mode` changes analyzer source and display state, not the EQ
  topology itself.
- `Display Range` changes graph scaling only.
- `Focus Band` is a UI focus concept used for editing and display sync.
- Some band types use the controls differently:
  - shelves and peaks use gain meaningfully
  - cut and special filter types may make gain less relevant or effectively
    ignored
- `Bypass` is device-level, while each band also has its own enable state.

## Tradeoffs And Limitations

- minimum-phase EQ means audible phase rotation is part of the design
- eight serial bands are efficient and flexible, but still impose interaction
  and UI complexity
- the analyzer is a visual aid, not proof that the audio path is correct
- the current UI still spreads editing between graph, focus tab, and band cards
  more than a final flagship design should
- it does not yet implement dynamic EQ, M/S EQ, or the richer selected-band
  control rail that the backlog now calls for

## Validation

Automated validation should catch:

- emitted patch structure
- analyzer object and source wiring
- graph engine support
- required control defaults

In-Live validation should catch:

- node drag behavior
- wheel-Q behavior
- analyzer usefulness in real playback
- focus-band synchronization
- coefficient smoothing behavior during fast sweeps
- whether the UI still feels graph-first instead of card-first

## References

- Implementation: [`plugins/parametric_eq/build.py`](./build.py)
- Cycling '74 `filtercoeff~`: [https://docs.cycling74.com/reference/filtercoeff~/](https://docs.cycling74.com/reference/filtercoeff~/)
- Cycling '74 `biquad~`: [https://docs.cycling74.com/reference/biquad~/](https://docs.cycling74.com/reference/biquad~/)
- Repo UI engine: [`src/m4l_builder/engines/eq_curve.py`](../../src/m4l_builder/engines/eq_curve.py)

## Future Work

- replace the current static lower editing emphasis with a proper selected-band
  control column
- add analyzer overlay improvements
- add dynamic EQ mode per band
- add M/S and other higher-end workflow features
- keep clarifying how this device differs from both EQ Eight-style UX and the
  project's own `Linear Phase EQ`
