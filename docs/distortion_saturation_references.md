# Distortion & saturation ideas (for Heat + a future distortion plugin)

Distortion/saturation design ideas, split into **engine (sound)** concepts and
**UI/visual** goodies, then mapped to our Heat saturator and a possible new
graphics-first distortion device. Companion to
`ui_goodies_and_graphics_pipeline.md`.

> Pairing **algorithmic + waveshaping modes** spans subtle coloration to
> extremely trashy, which suits industrial techno / experimental breakbeat sound
> design. An *algorithmic* path alongside a *waveshaping* path is Heat's
> direction and the dual-engine idea below.

---

## A. Engine / sound concepts (the DSP)

### Bipolar, motion-first shaping
- **Bipolar / multi-polar shaping**: the positive and negative halves of the
  waveform get **independent** distortion engines. A **Blend** knob sets the
  transition point between the +/- engines; **Hard/Soft Mode** sets how they
  cross-blend. (Heat's per-ZONE split is a cousin — bipolar is the +/- axis
  instead of the lo/mid/hi axis.)
- **Modes in families**: waveshape, wavefold, noise, bit-depth, sample-rate.
  Each stage blends + has stereo/MS modes; animated, not static.
- Morphing filter (many types, continuous morph) + feedback path.
- Multiband support.

### Dual engines with flexible routing
- **Two distortion engines**, each picking a model: bit inverter, bit crusher, wavefolder,
  rectifier, waveshaper, transformer, tape, tube, germanium, transistor.
- **5 routing modes**: serial, parallel, stereo, **mid/side**, **band-split**.
- Hidden "Advanced" panel for deep sound design.

### Curve-centric waveshaping
- **A large curve library** (subtle waveshape → aggressive wavefold), a **dual-
  waveform engine** that BLENDS two distortion characters, and an **LFO assignable
  to drive / gain / bias / the modifier-mix between curves**.

### Other directions
- A multi-algorithm workhorse: many algorithms, a **multiband waveshaper**, a multi-module chain.
- A dual-waveshaper option: two waveshapers with editable curves + 2 LFOs + envelope follower + filter.
- A minimal waveshaper baseline.

### Distilled concept list (what to consider for our engines)
- **Bias** (push the operating point for even harmonics) — Heat HAS this.
- **Bipolar +/- separate shaping** — Heat does NOT (per-zone instead).
- **Mode families**: waveshape ✓(7 chars) · wavefold ✓(FOLD) · bitcrush ✓(CRUSH) ·
  rectify ✗ · sample-rate-reduce ✗ · noise-inject ✗ · transformer/tube/tape ~.
- **Curve MORPH** — continuously blend between two transfer shapes.
- **Dual engine + routing** (serial/parallel/MS/band-split).
- **Modulation**: LFO + envelope-follower + drawable curves → drive/bias/mix.
- **Oversampling** to tame alias (Heat has 2x; the graphics-first push wants more).

---

## B. UI / visual goodies (the look + interaction)

- **Oscilloscope hero that shows BOTH the transfer curve AND the live output
  waveform** in real time. This is the single best visual idea here — and Heat already draws the transfer curve + live IO
  dots, so overlaying the live output waveform is a natural, high-impact upgrade.
- **The bipolar Blend as a draggable red line** in the scope marking the +/-
  transition point — direct, legible, draggable.
- **Play view (macros) vs Advanced view (full modulation)** — progressive
  disclosure; we already do FULL/MINI/pop-out, so a "macro" face fits.
- **Drawable / preset / randomizable modulation curves**. A drawable curve
  editor is itself an interactive hero.
- **Drag-drop modulation routing** — color-coded arrowheads dragged onto target
  params. A clean mod-matrix UX.
- **Mode-family browser** — folders of distortion modes with a shape preview each.
- **Per-character circuit color/identity** (e.g. Tube/Tape/Germanium each get
  a look) — Heat's per-mode color swatches already lean this way.

---

## C. Apply to HEAT (our saturator) — prioritised

1. **Live output-waveform overlay on the hero** (an oscilloscope). Heat streams
   `io_level`/env via `snapshot~`; stream a short output ring/scope and draw it
   over the transfer curve. Highest visual ROI,
   on-brand. *(visual + the audio is already there)*
2. **Bipolar mode** — let the +/- halves use different characters (or a Blend
   transition). A new axis of Heat's "paint the wave" idea; the hero shows the
   split. *(engine + visual)*
3. **More mode families** — add RECTIFY, SAMPLE-RATE-REDUCE, NOISE-INJECT to the
   7 characters (gen~ inline math; mirror in `waveshape_curve.py`).
4. **Curve MORPH** — a single knob that blends between two characters' transfer
   curves; the hero crossfades the drawn curve.
5. **A simple modulation lane** — LFO/envelope → drive or bias, drawn moving on
   the hero (Heat already has the env follower for the IO dots).

## D. A future graphics-first distortion plugin
- Multiband (lo/mid/hi) bipolar distortion with a big **oscilloscope hero**
  (transfer curve + live output + the bipolar blend line), a **drawable
  modulation-curve** editor as a second hero, a **mode-family browser**, and
  Play/Advanced faces. The graphic (the moving waveform being mangled) IS the
  product — exactly the "graphics create unique experiences" bet.
