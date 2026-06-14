# UI goodies & the "really good graphics" pipeline

A living research file: inspiration mined from the reference plugins + how pros
actually generate high-quality plugin graphics, mapped to (a) concrete upgrades
for our existing 7 flagships and (b) ideas for upcoming plugins. Graphics are a
differentiator — this is the backlog that turns "works" into "looks expensive."

Companion: `m4l_advanced_ui_techniques.md` (the v8ui API + MGraphics shape
toolbox + Ableton production rules). This file is the *what to build* / *where to
steal from*; that one is the *how it's wired*.

---

## A. How people generate REALLY good graphics

The short version: **pros render vector, not bitmap, and they design the vector
in a real design tool.** Resolution-independent vector scales to any size / DPI
without blur — that crisp, "expensive" look is mostly resolution independence +
restraint, not fancy effects.

1. **Vector all the way down.** FabFilter/Pro-Q-class UIs are GPU-accelerated
   vector renderers (JUCE + OpenGL, or NanoVG — "a vector API that translates to
   a 3D backend"; scaling is just a size-ratio, CPU stays flat). **Our equivalent
   is MGraphics** — already a vector context Max composites on the GPU. So we
   already have the right engine; the gap is *using it like a designer would*.
2. **Design static art in Figma → export clean SVG → `svg_render`.** The pro
   pipeline for logos/icons/badges/knob skins:
   - Design in Figma (vector).
   - **Outline all strokes** (convert stroke→fill) and **flatten booleans**
     (Union/Subtract/…→ one compound path) before export — Figma's raw SVG export
     is ~70% production-ready; outlining + flattening removes artifacts. A cleanup
     plugin (e.g. "SVG Export"/SVGO) closes the rest.
   - In the v8ui: `var svg = new MGraphicsSVG(file); mgraphics.svg_render(svg, x, y, w, h, opacity)`
     — or pass a raw SVG string. **`svg_render` avoids the graininess of scaling**
     (it re-rasterises per size). Use `mapcolor()` to recolor SVG paths so icons
     **follow the Live theme** instead of being baked.
   - Figma only exports SVG at 1x, but SVG is resolution-free — scale via the
     destination w/h in `svg_render`. No @2x bitmap dance needed.
3. **Fake depth the cheap, classy way.** JUCE/NanoVG even lack good shadows out
   of the box; everyone fakes them. Our levers (all MGraphics, no assets):
   - **Soft shadows / glows** = a radial-gradient fill offset under the element
     (we ship node glows via `pattern_create_radial` — same trick for drop
     shadows: dark radial, +2px down).
   - **Bevels / "lit from above"** = a 1px lighter stroke on the top edge + 1px
     darker on the bottom, or a vertical linear gradient fill.
   - **Glass** = a low-alpha white linear gradient (top→transparent) over a panel.
4. **Layer + cache.** Render the static scaffold (grid, labels, frame, gradients)
   ONCE to an offscreen `new MGraphics(w,h)` / `push_group()` Pattern, then blit it
   each frame; only redraw the live layer (curve, dots, meters). This is the real
   fix for the LP-EQ "spectrum stutter" and buys headroom for richer art.
5. **Restraint + consistency = the expensive look.** The 2025 trend is *fewer*
   knobs, flatter, less skeuomorphic, with strong visual feedback. Whole-pixel
   sizing (no blur), one type family (Ableton Sans), a tight palette, generous
   spacing, and balanced margins do more than any single effect.
6. **Buy/commission the hard art.** Pros buy vector knob/fader/meter kits or
   commission a designer; the dev wires them via SVG. Worth it for a hero knob.

Tools seen in the wild: Figma (+ SVG-cleanup plugins), the Estevan Carlos Benson
"Simple Interaction and Motion in Max/MSP" course (jsui+Figma), HTML-Canvas-style
JS drawing ports. Bookmarked, not yet mined deeply.

---

## B. Goodies worth stealing (reference plugins)

### Pro-Q 4 (Dec 2024) — the EQ gold standard
- **EQ Sketch** — draw the whole curve freehand in ONE gesture; the plugin fits
  bands (low cut / bells / shelf) to your stroke. A marquee interactivity feature.
- **Spectrum Grab** — grab a peak directly in the live analyzer to create/adjust a
  band there. Direct manipulation of the spectrum itself, not the curve.
- **Multi-band selection + edit**; **collision detection** (overlapping bands
  highlighted — we already have analyzer collision in the LP engine).
- **Character modes** — circuit-modelled saturation (Subtle/Warm) baked into an EQ.
- Pre-EQ / Post-EQ / **external** spectrum; display ranges 3/6/12/30 dB; tilt;
  freeze; per-band mid/side; dynamic EQ with attack/release + sidechain filtering.
- **Retina, GPU, resizable, full-screen** (our pop-out is the spiritual cousin).

### Pro-C 3 — compressor displays (for Pressure / Ceiling)
- **Live knee display** — the white transfer curve **turns green up to the current
  input level** in real time. A gorgeous, cheap-to-add "where am I on the curve"
  cue (we already stream env/GR probes — just color the curve up to the live x).
- **Level history** — input (dark) + output (light) waveforms with the **gain-
  reduction as a red line on top**; toggle to hide.
- **Click a peak read-out to reset it**; LUFS / EBU R128 metering per channel.
- **Compact mode** — hide the displays, show only meters (we do FULL/MINI).

### General UX trends (2025)
- Multiple views for novice vs expert (we have FULL / MINI / pop-out).
- Strong visual feedback on every action; tooltips/hover readouts (we have these).
- Simplify: fewer visible knobs, progressive disclosure.

---

## C. Apply to EXISTING heroes (prioritised)

1. **Spectrum Grab on the EQs** — click/drag a peak in the analyzer behind the
   curve to spawn a band at that freq/gain. We already draw the live spectrum and
   own the node-create path (double-click-add); this just adds a hit-test on the
   analyzer region. High wow, medium effort. *(Para + LP)*
2. **Live transfer-curve highlight on Ceiling / Pressure** — color the transfer/
   knee curve green up to the current input level using the existing env probe.
   Low effort, high polish. *(Ceiling, Pressure)*
3. **EQ Sketch** — freehand-draw a curve, fit bands to it. The flagship feature;
   bigger build (stroke capture → band fitting). *(Para + LP)*
4. **SVG rail icons** — replace hand-drawn glyphs (bypass, M/S, phase, freeze) with
   `svg_render` + `mapcolor` so they're crisp at any size and theme-following.
   Broadly applicable; nothing to freeze (ship strings). *(all 7)*
5. **Soft drop shadows** under nodes/panels via offset radial gradients (reuse the
   glow helper) for subtle depth. *(all heroes)*
6. **Offscreen-cache the static grid/labels** — perf + headroom for richer art;
   fixes the LP spectrum stutter. *(all heroes, LP first)*
7. **Click-to-reset peak-hold** read-outs on the Spectrum Analyzer + meters.

## D. Upcoming-plugin concepts (graphics as the hook)

- **Spectral/visual-first effects** where the graphic IS the instrument: paint
  spectral gain (brush on a spectrogram), draw an automation/LFO shape, an X/Y
  morph pad between states (Echotide's pad pattern, scaled up).
- **Isometric / 3D-ish meters** (the Cycling '74 "Bumps" idea) — an isometric
  level/where transforms (`rotate`/`scale`/`set_matrix`) sell depth cheaply.
- **A shared visual identity kit** — one MGraphics "design system" module (panel
  styles, gradient recipes, glow/shadow helpers, type scale, SVG icon set) reused
  across every device so the suite looks like a family. This is the single highest-
  leverage graphics investment: build it once in the engine, every plugin inherits.

---

*Sources:* FabFilter Pro-Q 4 product page; FabFilter Pro-C 3 "Displays and
metering" help; Cycling '74 "Custom UI Objects with JavaScript" + jsui SVG forum;
CDM "jsui + Figma"; KVR/JUCE NanoVG vector-UI threads; Figma SVG-export guides;
"Knobs and Nodes" (Massey U. study of audio-plugin UI).
