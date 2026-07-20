# Distortion & saturation references (for Heat + a future distortion plugin)

Research mined from the leading distortion/saturation plugins, split into **engine
(sound)** concepts and **UI/visual** goodies, then mapped to our Heat saturator
and a possible new graphics-first distortion device. Companion to
`ui_goodies_and_graphics_pipeline.md`.

> A well-regarded **Max for Live** distortion device (Ableton Live Suite 11+
> era) pairs **algorithmic + waveshaping modes** spanning subtle coloration to
> "extremely trashy," aimed at industrial techno / experimental breakbeat sound
> design. Notable that a well-regarded M4L peer pairs an *algorithmic* path
> with a *waveshaping* path — validates Heat's direction and the dual-engine
> idea below.

---

## A. Engine / sound concepts (the DSP)

### A motion-first, bipolar distortion standout
- **Bipolar / multi-polar shaping**: the positive and negative halves of the
  waveform get **independent** distortion engines. A **Blend** knob sets the
  transition point between the +/- engines; **Hard/Soft Mode** sets how they
  cross-blend. (Heat's per-ZONE split is a cousin — bipolar is the +/- axis
  instead of the lo/mid/hi axis.)
- **30 modes in families**: waveshape, wavefold, noise, bit-depth, sample-rate.
  Each stage blends + has stereo/MS modes; "animated, not static."
- Morphing filter (20+ types, continuous morph) + feedback path.
- Multiband support added in a later version.

### A dual-engine distortion plugin with flexible routing
- **Two distortion engines**, 11 models: Bit Inverter, Bit Crusher, Wavefolder,
  Rectifier, Waveshaper, Transformer, Force, Tape, Tube, Germanium, Transistor.
- **5 routing modes**: serial, parallel, stereo, **mid/side**, **band-split**.
- Hidden "Advanced" panel for deep sound design.

### A curve-centric waveshaper plugin
- **65+ shaping curves** (subtle waveshape → aggressive wavefold), a **dual-
  waveform engine** that BLENDS two distortion characters, and an **LFO assignable
  to drive / gain / bias / the modifier-mix between curves**.

### Other reference plugins
- A multi-algorithm workhorse: 60+ algorithms, **multiband waveshaper**, multi-module chain.
- A dual-waveshaper option: two waveshapers with editable curves + 2 LFOs + envelope follower + filter.
- A free, minimal waveshaper baseline.

### Distilled concept list (what to consider for our engines)
- **Bias** (push the operating point for even harmonics) — Heat HAS this.
- **Bipolar +/- separate shaping** — Heat does NOT (per-zone instead).
- **Mode families**: waveshape ✓(7 chars) · wavefold ✓(FOLD) · bitcrush ✓(CRUSH) ·
  rectify ✗ · sample-rate-reduce ✗ · noise-inject ✗ · transformer/tube/tape ~.
- **Curve MORPH** — continuously blend between two transfer shapes (seen in curve-centric waveshapers).
- **Dual engine + routing** (serial/parallel/MS/band-split).
- **Modulation**: LFO + envelope-follower + drawable curves → drive/bias/mix.
- **Oversampling** to tame alias (Heat has 2x; the graphics-first push wants more).

---

## B. UI / visual goodies (the look + interaction)

- **Oscilloscope hero that shows BOTH the transfer curve AND the live output
  waveform** in real time (the motion-first standout above). This is the single
  best visual idea here — and Heat already draws the transfer curve + live IO
  dots, so overlaying the live output waveform is a natural, high-impact upgrade.
- **The bipolar Blend as a draggable red line** in the scope marking the +/-
  transition point (the motion-first standout) — direct, legible, draggable.
- **Play view (macros) vs Advanced view (full modulation)** — progressive
  disclosure; we already do FULL/MINI/pop-out, so a "macro" face fits.
- **Drawable / preset / randomizable modulation curves** (the motion-first
  standout: 50+ presets, editable, random; the curve-centric waveshaper's LFO).
  A drawable curve editor is itself an interactive hero.
- **Drag-drop modulation routing** — color-coded arrowheads dragged onto target
  params (the motion-first standout). A clean mod-matrix UX.
- **Mode-family browser** — folders of distortion modes with a shape preview each.
- **Per-character circuit color/identity** (the dual-engine router's Tube/Tape/
  Germanium each have a look) — Heat's per-mode color swatches already lean
  this way.

---

## C. Apply to HEAT (our saturator) — prioritised

1. **Live output-waveform overlay on the hero** (the motion-first standout's
   oscilloscope). Heat streams `io_level`/env via `snapshot~`; stream a short
   output ring/scope and draw it over the transfer curve. Highest visual ROI,
   on-brand. *(visual + the audio is already there)*
2. **Bipolar mode** — let the +/- halves use different characters (or a Blend
   transition). A new axis of Heat's "paint the wave" idea; the hero shows the
   split. *(engine + visual)*
3. **More mode families** — add RECTIFY, SAMPLE-RATE-REDUCE, NOISE-INJECT to the
   7 characters (gen~ inline math; mirror in `waveshape_curve.py`).
4. **Curve MORPH** — a single knob that blends between two characters' transfer
   curves (the curve-centric waveshaper's modifier-mix); the hero crossfades the
   drawn curve.
5. **A simple modulation lane** — LFO/envelope → drive or bias, drawn moving on
   the hero (Heat already has the env follower for the IO dots).

## D. A future graphics-first distortion plugin
- Multiband (lo/mid/hi) bipolar distortion with a big **oscilloscope hero**
  (transfer curve + live output + the bipolar blend line), a **drawable
  modulation-curve** editor as a second hero, a **mode-family browser**, and
  Play/Advanced faces. The graphic (the moving waveform being mangled) IS the
  product — exactly the "graphics create unique experiences" bet.

---

*Sources:* Public product pages, reviews, and technique deep-dives for several
leading distortion/saturation plugins (both Max for Live and standalone), plus
marketplace and press roundups of the category.
