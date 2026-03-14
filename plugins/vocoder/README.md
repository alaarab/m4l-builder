# Vocoder

## Summary

`Vocoder` should be the flagship carrier/modulator spectral lane in this repo.

It is the sound-design and performance product that turns the repo's existing
filter-bank, detector, and spectral-display work into a recognizable instrument
or effect instead of a hidden DSP primitive.

## Problem

The library already exposes core vocoder-adjacent DSP, but there is no product
lane that turns those building blocks into a coherent device.

Current gaps:

- `vocoder()` exists in [`src/m4l_builder/dsp.py`](../../src/m4l_builder/dsp.py)
  but is not wrapped in a flagship device
- the repo has spectral display work, but not a carrier/modulator product with
  strong routing and performance controls
- there is no clear lane yet between classic channel vocoder behavior and more
  experimental spectral morph ideas

So this device exists to establish:

1. a serious classical vocoder product lane
2. a home for spectral performance UI
3. a bridge toward later spectral-morph or freeze variants

## Why This Exists

This lane is valuable because it is meaningfully different from the EQ and
compressor-heavy backlog.

It proves the repo can ship:

- strong sound-design devices, not only mix tools
- routing-aware products with internal and external sources
- spectral displays that are not just analyzers

If it lands well, it becomes one of the clearest examples that
`m4l-builder` can support iconic Max-for-Live style instruments and effects.

## Design Goals

- feel like a real performance vocoder, not only a filter-bank demo
- support internal carrier generation and external carrier routing
- make the carrier/modulator relationship visually obvious
- expose the important shaping controls without overwhelming the first version
- leave room for a later spectral-morph fork without bloating v1

## Non-Goals

- solving every spectral-processing problem in one device
- making v1 depend on a full phase-vocoder engine
- pretending a dense, unreadable control panel is more professional
- shipping a spectral morph workstation before the classic vocoder lane feels
  finished

## Core Method

Recommended v1 architecture:

- classical multiband filter-bank vocoder
- envelope followers on analysis bands
- carrier synthesis or external carrier routing
- per-band level shaping and final summed output

That fits the current repo surface best because:

- the existing `vocoder()` primitive already models filter-bank behavior
- it keeps latency and interaction simpler than a full STFT morph product
- it creates a strong base for later spectral enhancements

The later `Spectral Morph` lane can build on this product family rather than
replace it.

## Signal Flow / Algorithm

Recommended v1 signal flow:

`modulator input -> analysis bandpass bank -> envelope followers`

`carrier source -> synthesis bandpass bank -> per-band amplitude shaping by modulator envelopes -> summed output`

Recommended primary controls:

- `Bands`
- `Formant` or spectral tilt
- `Release`
- `Unvoiced` / noise support
- `Sensitivity` or detector drive
- `Carrier` source selection
- `Mix` / output shaping

Carrier options:

- external carrier input
- internal noise
- internal bright synth or pulse-like carrier later

## Why The Technical Claim Is Valid

Calling this `Vocoder` is valid if:

- one signal is analyzed for spectral envelope
- another signal is shaped by that envelope
- the user experiences banded spectral transfer, not just ring mod or filtering

If the carrier and modulator roles are not explicit, or if the band structure is
too loose to perceive, the product claim gets fuzzy.

## UI Model

The UI should be routing-first and visually spectral.

Recommended v1 layout:

- carrier / modulator source controls at the top
- a large central spectral band display
- shaping controls below or beside the display
- output / mix controls at the edge

The display should show:

- per-band activity
- carrier vs modulator contribution
- currently emphasized or selected ranges if editing is added later

Existing display groundwork already exists in
[`src/m4l_builder/engines/spectral_vocoder_display.py`](../../src/m4l_builder/engines/spectral_vocoder_display.py).

## Builder Dependencies / Framework Gaps

This lane already has a partial foundation:

- `vocoder()` in [`src/m4l_builder/dsp.py`](../../src/m4l_builder/dsp.py)
- `spectral_vocoder_display_js()` in
  [`src/m4l_builder/engines/spectral_vocoder_display.py`](../../src/m4l_builder/engines/spectral_vocoder_display.py)
- spectral crossover and STFT helpers for future expansion

Missing product pieces:

- stronger carrier-source architecture
- better source routing and gain staging
- clearer state model for band count / display updates
- a decision on whether stereo is true stereo, linked stereo, or mono-sum in v1

## Validation

Automated validation should catch:

- band-count defaults
- source-routing defaults
- emitted patch structure for carrier and modulator paths
- display state payload stability

In-Live validation should catch:

- whether speech intelligibility is credible
- whether internal carriers are musically useful
- whether release and formant controls produce audible, controllable changes
- whether the display makes routing and spectral action easier to understand

## Future Work

- spectral freeze or hold
- formant-shift / warp modes
- STFT-based spectral morph sibling device
- MIDI-playable internal carrier path
- per-band emphasis editing
