# Cross-Device JEWELS SYNTHESIS — what makes the downloaded plugins premium

Distilled from the 9 forensic `studies/<device>/TEARDOWN.md` reports (Rainbow, Chiral,
Superberry, stranular, Roulette, Particle-Reverb, SliceShuffler J74, LFO Cluster+PNoise,
AS Console suite). Ranked by **how many devices independently use the technique** (recurrence =
validated) × leverage for our kit. Each jewel: the mechanism, who uses it, the kit gap, the build action.

---

## TIER 1 — recurs across MANY devices = build these first

### J1. Runtime THEME BUS (`live.colors` fan-out) + bypass "zombie" dimming  ⭐ the #1 "first-party" cue
**Used by:** Chiral, Superberry, Roulette, Particle, AS Console (5/9). Multiple reports flag it as
"the framework's #1 missing capability."
**Mechanism:** `live.thisdevice → t <named zones> → live.colors (self-loop) → route <zone> →
prepend <attr> → s ---bus`; consumers `r ---bus → route <zone> → <control attr>`. The named zones
are Live's theme slots (`lcd_control_fg` = accent, `lcd_bg`, `surface_bg`, `control_fg`,
`lcd_control_fg_zombie`, `assignment_text_bg`). **Bypass dim** = `r ---devicestate → sel 0 1 →
[accent message | zombie-grey message]`; Chiral's trick = emit BOTH simultaneously with
complementary alphas (`!- 1.`) so enable/bypass is an alpha crossfade, no RGB lerp.
**Why premium:** the device recolors to ANY Ableton theme (dark/light/custom) and greys on bypass —
exactly like a stock device. One palette change repaints the whole device live; theming is data, not code.
**Kit gap:** we have `engines/live_theme.py` (`live_colors_bus`/`live_theme_receiver`) but devices
don't wire it. **Build:** `Device.add_theme_bus(specs)` that emits the producer + auto-wires receivers
into each native control's accent/bg attrs + the `---devicestate → zombie` gate. (Was jewel B1-part2.)

### J2. TRANSPARENT-native-over-art compositing (alpha-0 control attrs)  ⭐ branded graphics + free automation
**Used by:** SliceShuffler (waveform~ over live.grid), Roulette (multislider/matrixctrl over jsui),
Particle (mask-frame punch-through), AS Console (stacked bpatchers/tabs/fpic reveal) (4/9).
**Mechanism:** draw the art FIRST (jsui OR a stock `live.grid`/`waveform~`), then stack the
interactive native control(s) on the SAME rect LAST (= on top), with ALL color attrs **alpha 0**
(`bgcolor`/`gridcolor`/`selectioncolor`/...) + `ignoreclick 1` where it's display-only. Z-order = box
order. **Ghost-layer reveal:** a second transparent copy on a different buffer, revealed by raising one
alpha, zero re-layout. Mask-frame variant (Particle): a bg jsui punches black holes where each native
widget sits so native chrome vanishes and custom art shows through.
**Why premium:** pixel-perfect custom face WITH free Live automation/undo/MIDI-map/preset on the real
native param. **Kit gap:** documented now (`ui_inputs_reference.md` "native-compositing hero"); no
recipe. **Build:** `add_overlay_control(native, art_rect, alpha0_attrs)` + a `native_composite(grid|wave, overlays)` recipe.

### J3. gen~ → named `buffer~` → jsui VISUALIZER BUS (zero-wiring DSP↔UI)  ⭐ the keystone for live displays
**Used by:** stranular (keystone — 100 grains), Superberry (4-ch scope), LFO (gen computes display
geometry), Particle (out3 publishes wet signal for the spectrum) (4/9).
**Mechanism:** gen declares `Buffer ---name`; a `counter`-gated control-rate block `poke`s the trace /
per-particle x,y,r,alpha (even the polar coords) into it; the jsui `new Buffer(name).peek()` in
`paint()`, banged by a `qmetro 40 @active 1`. **The GUI physically cannot desync from DSP — it reads
the same memory.** The DSP can compute the DISPLAY GEOMETRY (arcCos/arcSin), the jsui just renders.
**Kit gap:** `add_compiled_display` exists for stock scopes, but not the gen→buffer→jsui custom-viz bus.
**Build:** `add_buffer_scope(name, samps, paint_js)` → `buffer~ ---name` + gen poke stub + peek paint loop.

### J4. `jspainterfile` — repaint a NATIVE control in place  ⭐ the Fors UI thesis
**Used by:** Superberry (67×), Chiral, AS Console (livedial_override) (3/9, but Superberry leans on it
totally). **Mechanism:** attach a render-only mgraphics `.js` to a stock `live.dial`/`numbox`/`tab`/
`toggle` via the `jspainterfile` attribute; the native object stays the param host (automation/MIDI/
undo/Push/A-B), the `.js` only `paint()`s — reading `box.getvalueof()` + `box.getattr("_parameter_range"
/"_parameter_unitstyle"/"active")` + custom theme attrs. **Half the boxes of a v8ui+hidden-dial, and the
drawer IS the param.** Pair with a shared painter kernel (`remap` + `unit_style` ms/Hz/dB/%/pan + `draw_text`).
**Kit gap:** `paint_control` plumbing exists (`engines/painters.py`), but our painters are dim/thin and
the unit-readout kernel isn't shipped. **Build:** finish `engines/painters/_lib.js` (auto-unit readout) +
better lcd_dial; expose `unitstyle` on painters. ⚠️ Superberry caveat: painters read a RUNTIME
`_parameter_range` Live computes — don't store `parameter_range` on disk.

---

## TIER 2 — strong, recurs in 2-3 devices

### J5. The "ALWAYS-MOVING", CPU-gated animation
**Used by:** LFO (Task@40 redraw only while mapped), stranular (grains breathe), Chiral (jitter LED),
Particle. A `Task interval=40` (~25 fps) calls `redraw()` ONLY while active/mapped; stops dead when idle
(premium feel + CPU discipline). Color flips amber(+)/cyan(−) on bipolar sign so sign is legible w/o text.

### J6. MAP-TO-HOST-PARAMETER modulator archetype
**Used by:** LFO pair (THE archetype), SliceShuffler (click-to-map). Arm `live_set view
selected_parameter` observer → resolve clicked param id → read runtime min/max/name → **self-map guard
by id-compare** (`zl compare id 0`, NOT path-string) → debounce 20 ms → route to **`live.modulate~`
(bipolar/modern) vs `live.remote~` (absolute/legacy)** + depth window + `downsamp~` lag. Write back
without a `set` (`param.value=v; param.clip()`) to dodge feedback. **Kit gap:** the central UX of modern
modulators, missing. **Build:** `map_to_selected_parameter` recipe (was jewel E2).

### J7. ONE RGB → N control-color attrs at tiered alphas (themeable knob from one color)
**Used by:** Roulette (`p lcd-knob`: 1 RGB → 9 `live.dial` attrs at hand-tuned alphas — activedialcolor
1.0, activefgdialcolor 0.5, fgdialcolor 0.25, …), SliceShuffler ("FabFilter face": `bordercolor [1,1,1,0.2]`
hairline + `panelcolor [0,0,0,0.2]` recess + one accent on every native control = inset/beveled with no
images). **Build:** a `themed_dial(accent)` / `themed_control(accent)` helper fanning one accent to the
attr set at the corpus alphas; feed it from the theme bus (J1).

---

## TIER 3 — the DENSE-NATIVE GRAMMAR (AS Console — the reference faceplate)

### J8. The AS Console premium-faceplate recipe (100% native, ZERO jsui) — exact values
1. **Two-tier chassis:** near-black center card `panel bgcolor [0.098,0.098,0.098,1]` rounded 6, grey
   rails `[0.561,0.561,0.561,1]` rounded 6, all 167px tall, flat `mode 0`. *("patch" → "faceplate".)*
2. **Ghost tabs:** `live.tab` with ALL bg/border attrs `alpha 0`, `textcolor` grey
   `[0.549,…,1]` → `textoncolor` amber `[1.0,0.694,0.0,1]`, row 20px. Selection = text-color flip only.
3. **Native themed dial:** `live.dial 41×35`, `showname 0`, `activedialcolor [1.0,0.694,0,1]` amber ring +
   grey `activefgdialcolor`/`activeneedlecolor`/`textcolor [0.588,…,1]`, label = separate comment above
   (Ableton Sans Medium 9.5). **The dial profile to standardize on.**
4. **LCD numbox strips:** `live.numbox appearance 4`, 15px, `lcdbgcolor`/`bordercolor` alpha 0 (chrome
   reads as printed on the panel) — 28 of 38 numboxes use it. Rail values use `appearance 2`.
5. **Divider grid:** 75× `live.line` (uncolored = thin grey) fencing every group + one amber accent rule.
6. **ONE accent, used 67×:** `#FFB100 = [1.0,0.694117647058824,0.0,1]`. Never a second hue.
**Kit status:** `dial_value_cell`, `native_sizes` (DIAL_COMPACT 41×35), `stacked_panels` (tabs) exist and
already shipped on Strip v6+. The gaps: the **ghost-tab styling**, the **appearance-4 numbox strip**
recipe, the **divider grid** helper, and wiring it all to the **theme bus (J1)** so the accent is the host's.

### J9. Modular composition — stacked embedded bpatchers + tab/hide reveal + runtime reorder
**Used by:** AS Console (the channel-strip spine), SliceShuffler. Mount N `embed:1` bpatchers at one
identical slot rect, stable `varname`s; a tab param fans to `script sendbox {var} hidden $1` to reveal one;
precomputed `script connect/disconnect` macro sets reorder the serial chain. Also the "stack 8
differently-ordered tabs / 9 fpic icons at one rect, un-hide the matching one" reveal idiom. **Kit:**
`add_bpatcher_module` + `stacked_panels` exist; add the reorder-macro layer for a true reorderable strip.

---

## TIER 4 — DSP jewels (gen) worth a kit pass (secondary to UI for now)
- **One-codebox flagship DSP:** Particle = full Dattorro reverb + granular front-end in 615 lines;
  stranular = 100-voice grain engine in one GenExpr over `Data`/`Buffer` (no `poly~`/`groove~`).
- **`Data`-array poly engine** (SoA voice table + wrap-counter allocator + `i%2` parity channel +
  phase-inversion decorrelation) — stranular, Particle, LFO. Replaces `poly~`.
- **Reversed-buffer FREEZE = source swap** (snapshot to `Data`, grains re-read it, equal-power ramp-WAV
  crossfade) — stranular, Particle.
- **`change()`-gated, one-pole-smoothed biquad recompute** — Particle. Zipper-free at near-zero CPU.
- **Branch-free mod-enable** (`out = modParam * lfo`, 0 = off) — LFO, Superberry. No CPU cliff toggling lanes.
- **Baked LUTs as `.wav`** for transcendentals (smootherstep, grain window, morph banks) read by
  `index="phase"` — stranular, LFO, Particle. Ship the curve, don't evaluate per sample.
- **One-hot LFO→destination demux** (one menu + one depth, neutral 0 additive / 1 multiplicative) —
  Superberry. Replaces an N-cell mod matrix.

---

## The headline (for the UI uplift)
The recurring "looks like a real Ableton device" multipliers, in order: **(1) the runtime theme bus +
bypass zombie-dim (J1)** — most-flagged gap; **(2) the AS Console dense-native grammar (J8)** — already
partly shipped, finish ghost-tabs + numbox strips + dividers; **(3) transparent-native compositing (J2)**
for branded displays; **(4) the gen→buffer→jsui viz bus (J3)** for live heroes; **(5) jspainterfile (J4)**
where a native control needs a bespoke face. None of the premium devices "paint everything" — they use
**native controls, themed and composited**, and reserve custom drawing for what native can't do.
