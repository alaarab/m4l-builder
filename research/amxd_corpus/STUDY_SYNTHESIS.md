# m4l-builder Integration Backlog — Master Synthesis

Deep study of 16 commercial Max for Live devices (Fors, Incandescent Rainbow, J74, SABROI "Console" suite, and boutique granular/modulator devices), cross-referenced against the current `src/m4l_builder/` framework. This document is the prioritized integration backlog: what m4l-builder must add to generate devices that read and behave as first-party, FabFilter-grade Ableton instruments and effects.

---

## Executive Summary

Across all 16 devices, premium quality converges on a small set of architectural moves the framework does **not** currently express. Four of them recur in nearly every device and together account for most of the "reads as native / reads as commercial" gap:

1. **Runtime `live.colors` theme bus.** Premium devices never bake colors at build time. They read the user's actual Live skin at load (`live.thisdevice → live.colors → route → prepend <attr> → s ---bus`), broadcast it over device-scoped `---` send/receive, and re-tint every native control and jsui live — including an active/zombie dim on bypass. `grep live.colors src/` = 0. This is the single most-cited gap (8+ devices) and the biggest "looks native in any skin" multiplier.

2. **`jspainterfile` on a native control.** The lightest, most-correct custom-knob path: one stock `live.dial`/`live.numbox`/`live.tab` keeps full native Live behaviour (automation, MIDI-map, undo, modulation, banking) while a render-only mgraphics `.js` painter draws it. One box, no hidden second param, no z-order. Appears in 5 of 16 studies; `grep jspainterfile src/` = 0. Replaces the framework's heavier two-box v8ui-over-hidden-dial `add_custom_knob`.

3. **The whole DSP engine in ONE gen~/mc.gen~ codebox, backed by Data/Buffer/Delay state.** Every premium DSP device collapses its engine into one hand-written codebox (Chiral 8-voice MPE polysynth, stranular 100-voice granular scheduler, Particle-Reverb algorithmic reverb, Superberry 16-voice super-saw). `gen_snippets.py` is effect-only and stateless: it has **zero** uses of `Data`, `Buffer`, `Delay`, `poke(`, or `peek(` (verified). A Data/Buffer/Delay stateful-engine kit unlocks an entire device class the framework cannot build today: granular, looper, freeze, sampler, polysynth, algorithmic reverb.

4. **Live-native parameter persistence + rich parameter metadata.** Premium devices ship `parameter_initial_enable:1` + `parameter_initial` on every param and lean 100% on Live's snapshot/automation/A-B store — pattrstorage appears in **zero** of them. They also fill `parameter_annotation_name` + `parameter_info` (hover help) and `parameter_units` + `unitstyle:9` (custom readouts) on nearly every control. The framework drops `annotation_name` silently and cannot emit `parameter_info` or custom units at all.

Two **confirmed defects** must be fixed first because they silently break correctness:
- `amxd.py:16` `_parameter_banks_payload` emits banks as a **list-of-dicts** (`{index,name,visible}`); Live/Push expect a flat 8-element list of param LONGNAME strings with `-` placeholders. Verified by reading the source. Every multi-param device's Push banks are wrong today.
- `parameter_annotation_name` lands as a bare box attribute and is dropped from `valueof` (flagged in AS_Console_Width). Hover help never appears.

A second tier of structural primitives recurs widely: the MC poly-voice spine (`mc.noteallocator~ → mc.click~ → mc.gen~ → mc.mixdown~`, replacing the older poly~ path), the gen~→named-buffer~→jsui visualizer bus (animate 100 grains at 25fps with zero patchcord traffic), the LOM click-to-map engine (turns any device into a Live-native macro/modulator that targets other plugins), transparent-native-over-jsui composition, stacked/gated views to fit dense UIs into 168px, and a corpus-measured native-sizing catalog (the framework's `DIAL=(44,47)` is consistently too tall; the workhorse is `DIAL_COMPACT=(41,35)`).

The backlog below is ordered by priority then effort. P0 items are correctness fixes and the four convergent primitives; P1 adds the structural device-class unlocks; P2/P3 add polish, craft vocabulary, and shared infrastructure.

---

## Backlog by Theme

### A. Correctness fixes (do first — confirmed defects)

**A1 — Fix the parameterbanks payload shape.** Rewrite `amxd.py:16` `_parameter_banks_payload` to emit each bank as a fixed 8-element list of param LONGNAME strings indexed by position, `-` for gaps, paired with a `live.banks` box; fix the `profiles.py` seed template to the same 8-slot shape. Confirmed list-of-dicts bug by reading source. *Devices: Chiral, Superberry, Rainbow, SliceShuffler, all AS_Console. Priority: high. Effort: small.*

**A2 — Fix the dropped `parameter_annotation_name` / add `parameter_info`.** Emit `parameter_annotation_name` and `parameter_info` inside the param's `valueof` (not as loose box attrs); the existing `annotation_name` kwarg currently lands as a bare box attr and is silently dropped. *Devices: AS_Console_Width (confirmed), Superberry 47/48, Rainbow 60 sites, every Chiral cell. Priority: high. Effort: small.*

---

### B. Theme & color (runtime live.colors)

**B1 — Runtime `live.colors` theme-bus generator.** Add `engines/live_theme.py` + `Theme.follow_live` flag emitting `live.thisdevice → live.colors → route <skin_tokens> → prepend <attr> $2 $3 $4 $5 → s ---<token>`, with active/zombie gating off the device-enable outlet (`r ---devicestate → sel 0 1`). Make every ui factory and jsui paint engine emit `r ---<token>` receivers + `set_lcdcolor`/`set_lcdbgcolor` setters instead of static RGBA; write saved colors as alpha-0 placeholders. Port the skin-token map (surface_bg, lcd_bg, lcd_control_fg, lcd_control_fg_zombie, control_fg, value_arc). The #1 most-cited gap. *Devices: all AS_Console, Superberry, Chiral, Rainbow, Roulette, lfo-cluster, lfo-pnoise. Priority: high. Effort: large.*

**B2 — HSL theme-derivation module.** Port `hslToRgb`/`rgbToHsl` into `theme.py` + a JS prologue, plus `derive_palette(base_accent, role_accents)` implementing hue-preserve/SL-borrow: `hslToRgb(roleHue, min(userS,0.7), (userL+roleL)/2)`. The mechanism behind "one user color tints the whole device harmoniously." 0 hits in src. *Devices: Rainbow. Priority: medium. Effort: medium.*

**B3 — Two-accent semantic palette presets + active-only dial theming.** Ship a CYAN/AMBER preset (accent `[0.427,0.831,1]`, accent2 `[1,0.706,0.196]`, milky text `[0.965,0.976,0.894]`, zombie grey, near-black bg `[0.078,0.078,0.078]`), a 4-accent stranular variant, and a convention that sets only `active*` dial colors with structural colors bound to `themecolor.*` expressions while the brand accent stays hard-coded. *Devices: Chiral, stranular, lfo-cluster, Particle-Reverb, Superberry. Priority: medium. Effort: small.*

---

### C. Premium controls (jspainterfile, LCD, overlays, native sizing)

**C1 — `jspainterfile` support on `ui.dial()`/`ui.numbox()` + painter library.** Emit ONE native control with a `jspainterfile <file>` attribute + asset bundling via `assets.py`/freeze; ship `engines/painters/` of render-only ES5 painters (lcd_dial, lcd_dial_bipolar, lcd_fader, lcd_bar, lcd_readout, glyph_toggle, glyph_tab) that read `box.getvalueof()` + `box.getattr('_parameter_range/_exponent/_type/_unitstyle')` and never store a value or use inlets/outlets. Re-apply the painter on skin change off the theme bus. Lint: painter-mode requires `getvalueof`, forbids outlets/setvalueof. Keep `add_custom_knob` only for gradient/glow bodies a native host can't render. 0 hits in src. *Devices: Chiral (whole UI), Superberry (~30 painters), Particle-Reverb, all AS_Console. Priority: high. Effort: large.*

**C2 — `appearance=4` LCD numbox/text as a first-class mode.** Document appearance 4 in `ui.py`; add `lcdcolor`/`lcdbgcolor`/`inactivelcdcolor` as named kwargs on `ui.numbox()`/`ui.live_text()`; add `lcd_numbox(role)` + `Theme.lcd_on/lcd_off/lcd_bg` tokens with role_colors (time=blue/level=gold/tone=teal). Unlocks the borderless glowing-digit readout that defines the premium look; reachable only via raw kwargs today (`grep lcdcolor ui.py` = 0). *Devices: Superberry, Chiral, Roulette, stranular, lfo-pnoise, lfo-cluster, Particle-Reverb, AS_Width/Norm. Priority: high. Effort: medium.*

**C3 — The `unitstyle_readout` self-formatter mixin.** A single shared ES5 helper emitting the verbatim `switch(box.getattr('_parameter_unitstyle'))` formatter (case 2 ms↔s, 3 Hz↔kHz, 4 dB w/ -inf, 5 %, 6 Pan L/C/R, 7 ±st) + a `text_measure()`-centered `draw_text()` that reads box fontname/fontface; consumed by `custom_knob_js`, `value_readout_js`, and the C1 painters instead of a baked unit/decimals. Highest perceived-quality-per-line win. *Devices: Chiral, Superberry, Particle-Reverb. Priority: high. Effort: small.*

**C4 — Overhaul `native_sizes.py` with measured premium tiers.** Add `DIAL_COMPACT=(41,35)` (the AS-suite workhorse, 19+ instances), `DIAL_TINY=(54,36)` appearance 1, `DIAL_LCD=(51,63)` appearance 3, `DIAL_RAIL=(41,48)`, `DIAL_LABELLED=(44,65)`; `NUMBOX_LCD=(40,17)`, `NUMBOX_MINI=(17,15)`, `NUMBOX_HERO=(72,23)`; `VSLIDER=(22,113)`, `METER_FADER=(35,163)`; `TAB_H=20` + full-width mode-switch; `TEXT split=(24,15)`, `TEXT_ICON=(25,25)`, `ICON_TOGGLE=(38,23)`, `LED_DOT=(10,10)`. Change primary `LABEL_FONTSIZE` to 9.5 (keep 7.0 as `_TINY`), default label font to Ableton Sans Medium, add `ROW_PITCH_TIGHT=17` and a width-derived `knob_row_fit(x0,y,n,width,margin=6)`. *Devices: all 16 (universally flagged). Priority: high. Effort: medium.*

**C5 — Transparent-native-over-jsui composition.** `device.add_overlay_control(jsui_engine, native_class, rect)` placing a native control with all chrome colors alpha-0 but `parameter_enable:1` exactly over a jsui canvas (input + persistence + MIDI-map free, branded graphics on top); plus alpha-0 `live.text` hit-zones for arbitrary click regions over art; plus the 3-layer bg/interactive/overlay variant with `ignoreclick:1` on non-gesture layers. *Devices: Roulette, Chiral, Superberry, Particle-Reverb, SliceShuffler. Priority: medium. Effort: medium.*

**C6 — Stacked / gated view primitives.** `recipes.stacked_panels(tab_param, panels)` placing N full-bleed bpatchers/sub-panels at one rect with visibility gated by a `live.tab` (the universal way to stay within 168px), plus `add_ghost_tab(rect, labels)` — a fully transparent live.tab carrying param + selection state with custom comments/`live.line` underlines as the visible look. *Devices: Chiral, AS_Komp, AS_Width, AS_EQ, lfo-pnoise. Priority: medium. Effort: medium.*

**C7 — SVG-icon controls + glyph buttons.** Thread `usepicture`/`pictures`/`remapsvgcolors` through `ui.tab()` for theme-tinted waveform/glyph selectors, add `ui.svg_logo()` (live.text @pictures @remapsvgcolors 1, parameter_invisible:2, theme lcdcolor) and `ui.glyph_button()`/`add_icon_toggle(glyph, accent)` (single-unicode-char live.text, appearance 2). *Devices: lfo-cluster, Superberry, Rainbow, stranular, AS_EQ. Priority: medium. Effort: medium.*

**C8 — Two-panel channel-strip shell + dense-layout helpers.** `recipes.two_panel_strip(dark_w, rail_w, gutter=2, rounded=6)` (devicewidth=0, dark DSP panel + grey rail, per-panel label recolor), a value-below-dial cell helper (DIAL_COMPACT + comment@9.5 + numbox below), and `tab_band(x,y,w,n)` full-width stretched tab. Reproduces the AS_Console / SEAR dense grids. *Devices: all AS_Console, SEAR. Priority: low. Effort: medium.*

---

### D. DSP & gen~ engines

**D1 — Data/Buffer/Delay stateful-engine kit in `gen_snippets.py`.** Minimum set: `ring_buffer(name, secs, ch)` with the duplicate-sample-0 wrap-read; `voice_pool(fields, N)` (SoA Data arrays + free-slot allocator + per-sample `for(i<N)` skeleton with active-flag/counter convention); `delayline_allpass()` (Schroeder, two gen Delay taps) and `lattice_diffuse()` (Dattorro stage); `grain_window_lookup()`/`pitch_env_lookup()` with the integrating playhead. Wire through existing `build_gendsp()`. Verified: gen_snippets has 0 Data/Buffer/Delay/poke/peek today. The single highest-leverage addition — unlocks granular, looper, freeze, sampler, polysynth, reverb. *Devices: stranular, Particle-Reverb, Superberry, Chiral, lfo-cluster. Priority: high. Effort: large.*

**D2 — MC poly-voice synth spine.** Emit `mc.noteallocator~ @voices N [@mpemode 1 @steal 1] → mc.click~ @chans N → mc.gen~ @chans N → mc.mixdown~ → mc.unpack~ → plugout~` with the gen-outlet→allocator-inlet0 voice-steal feedback and `mc.target` per-voice addressing; add a `polyphony='mc'` profile flag. Structural prerequisite for any modern (MPE) polysynth; both Superberry and Chiral have zero poly~. *Devices: Superberry, Chiral. Priority: high. Effort: large.*

**D3 — Synthesis-snippet family (gen_snippets is effect-only today).** `adsr_codebox()` (crossfade-of-two-slides, sample-accurate, replaces black-box live.adsr~, 64-sample anti-click retrigger fade), `phase_feedback_op()` (phasor→cycle→PM→self-FB with `pow(0.5-norm_f,4)` anti-alias taper), `super_saw()` (JP-8000 6-op tuned irrational detune + detune→octave morph), `qpow()` wavetable-scan LFO, CZ `phase_bend()`/`hard_sync()`. *Devices: Superberry, Chiral. Priority: high. Effort: medium.*

**D4 — gen~→buffer~→jsui visualizer bus.** gen_snippets helper for a `counter(1,0,mstosamps(40))`-gated poke block writing per-voice/per-bin screen state into `---`-scoped buffers, plus a jsui base that `peek()`s them on a qmetro tick; ship `engines/grain_cloud_display.py` (per-grain arcs, alpha=window, color=reverse, over a 3-pass scope) and a `buffer_scope` helper. Animates 100 grains at 25fps with zero patchcord traffic and no GUI/DSP desync. *Devices: stranular, Particle-Reverb, lfo-cluster, Superberry, Rainbow, Chiral. Priority: high. Effort: large.*

**D5 — Morphable-nonlinearity + reverb-primitive pack.** `variable_sigmoid()` (`2/(1+exp(k*x))-1` morphing tanh↔hard-tape via one param, cascadable), `modulated_allpass_reverb()` (prime/irrational-ratio Schroeder allpass + detuned LFO reads — "reverb without an FDN"), and a Hadamard/butterfly diffusion stage. *Devices: Chiral, Superberry, Particle-Reverb. Priority: medium. Effort: medium.*

**D6 — Audio-rate mod-matrix recipes (both architectures).** `add_mod_matrix(dests, sources)` — NxM bipolar `live.numbox` cells (type 0, unitstyle 9, -100..100, initial_enable 1, shared annotation_name/info) + named-bus per-destination summing + auto one-row-per-parameterbank for Push; plus the cheaper `lfo_to_menu_destination()` — N-output gen with `if(dest==i)` gating (additive-0/multiplicative-1 neutrals) + one live.menu + one depth param. Replaces the control-rate `macro_modulation_matrix`. *Devices: Chiral (72-cell), Superberry (15-dest demux). Priority: medium. Effort: medium.*

**D7 — Equal-power / energy-preserving DSP fixes.** `ms_width_equal_power()` with the orthonormal `/sqrt(2)` constant-sum law (the current `ms_width` gain-shifting law is confirmed wrong — gets louder as it widens) + `multiband_width_stage()` + click-free polarity flip (`!- 1 → slide → dcblock`) + mono-bass maker + atan2 correlation meter; `equal_power_xfade()` + `overlap_normalize()` density AGC. *Devices: AS_Console_Width, stranular, Particle-Reverb. Priority: medium. Effort: medium.*

**D8 — CPU-discipline + seconds-parameterized smoothing.** `change()`-gated coefficient-recompute wrapper, idle DSP-sleep gate (`his_dsp` energy detector, decay-when-silent, pin-during-freeze), frequency-dependent feedback-taper, table-baker helpers; replace opaque `param_slew` with `expsmooth()` using the `expA`/`tauA` polynomial-exp pole (`z=exp(-1/(t*sr))` from smooth-time-in-seconds) + minimax sin/cos prewarp + `tanA()`. *Devices: Particle-Reverb, Superberry, AS_Console_Width, Chiral. Priority: medium. Effort: medium.*

**D9 — Spectral upgrades.** Fix `phase_vocoder_subpatcher` to real `framedelta~→frameaccum~ 1` + spectral_freeze; add a `window_buffer` generator (Hann..Flat-Top, overlap-2 guard, gain comp); generalize `pfft~` to multi-input (`fftin~ 2/3/4` sidechain); add `spectral_curve_gain(buffer)` (index~ bin-lookup of a JS-drawn curve) and a per-bin `spectral_dynamics` block (`GR=delta*(1-1/ratio)` + vectral~ + ms timing). *Devices: Rainbow. Priority: low. Effort: large.*

---

### E. Parameters, modulation & presets

**E1 — `parameter_units` custom format strings + `unitstyle:9`.** Add `parameter_units` (printf) to ParameterSpec + a UNITSTYLE map with `UNITSTYLE_CUSTOM=9` and a cookbook (`%+.1f st`, `x %.2f`, `%.3g dB`). Cheap, instantly upgrades how every device reads. *Devices: Rainbow, Chiral, all AS_Console. Priority: high. Effort: small.*

**E2 — LOM click-to-map modulation subsystem.** The biggest missing premium primitive: the framework can modulate internal DSP but cannot build a Live-native modulator that targets OTHER plugins. Ship `live_remote_write`/`live_modulate_write` + `map_to_selected_parameter` (arm `live_set view selected_parameter`, read target min/max/name + canonical_parent, self-map guard vs this_device id + `/mapping/` regex, 20ms Task debounce, feedback-safe `targetParam.value=` write with NO `set` message), optional `live.banks`; pair with a no-audio device_type (numins=1 GUI tick, numouts=2N+1) and a `js <file>` plain-external helper. Unlocks the entire macro/modulator/LFO-mapper device class. *Devices: lfo-cluster, lfo-pnoise, SliceShuffler. Priority: high. Effort: large.*

**E3 — `parameter_modulator` archetype + multi-slot mod matrix.** A `parameter_modulator(device, source, n_targets, depths)` archetype (multi-out control gen → per-target live.remote~/live.modulate~ writers → per-target depth) reusing one parameterized range-fader bpatcher per slot `{target,min,max,depth,manual,range-mode}`. *Devices: lfo-pnoise, lfo-cluster. Priority: medium. Effort: medium.*

**E4 — `parameter_exponent` cookbook + invisible/shadow params.** Bake the proven taper cookbook (Hz/time 3.0–4.0, threshold 0.5, low-floor 0.3, explicit 1.0 = linear) into presets; add `parameter_invisible:1/2` (document 0/1/2 semantics) for UI-state-as-hidden-enum persistence (no pattr), visible-labelled-dial ↔ hidden-canonical-token-menu split, and value-mirroring `[1]` copies; always emit `parameter_initial_enable:1` + `parameter_initial`; add `parameter_steps`, `parameter_modmode` (default 0), `parameter_defer:1`, `parameter_order`, `parameter_linknames`. *Devices: Superberry, Chiral, Rainbow, lfo-pnoise, lfo-cluster. Priority: medium. Effort: medium.*

**E5 — `parameter_overrides` emission.** Instantiate a parameterized abstraction once and rename/re-unit its internal params via scoped `objA::objB::objC` paths to device-level longnames — required to reuse one mod-matrix-row/EQ-band abstraction N times and satisfy Live's globally-unique-longname rule, and to surface params inside embedded bpatchers without a manual Max re-save. 0 emission today. *Devices: Chiral, lfo-pnoise, stranular, AS_Console_Pre. Priority: medium. Effort: medium.*

**E6 — Dynamic Live-banks helper.** A `live.banks` emitter + generated js section-table rewriter (8 macro slots from a 2D section×longname table), slot-0 section selector, late-bound function slots (mode-dependent names; undefined=>empty), dirty-checking. Lets a 100+ param device present 8 clean context-sensitive macros. *Devices: Rainbow. Priority: low. Effort: medium.*

**E7 — Non-automatable-state persistence helpers.** `presets.file_snapshot_io()` (.maxpresets via pattr text + savedialog/opendialog + tagged `key#key#` codec) with a `live.banks`/slot + Copy_AB/Copy_BA A/B-trigger variant; plus a private `---`-prefixed dict snapshot for mapping geometry only. Document the "lean on Live-native persistence, never pattrstorage" default. *Devices: SliceShuffler, lfo-cluster. Priority: low. Effort: medium.*

---

### F. Patch architecture & packaging

**F1 — `---` device-scoped pub/sub bus + staged init.** A named-bus registry that always `---`-scopes and threads the token into bpatcher/poly~/buffer~ load args; an init-ring recipe (`live.thisdevice → ---startBang` / `del 1 + deferlow → ---lobang/---lobang2`) instead of loadbang; a `getsystem ---osInfo → sel macintosh → s ---os` OS-detection broadcast; and the active/zombie `r ---devicestate → sel 0 1` palette swap built in. *Devices: SliceShuffler (323 s/r), AS_Console_1.02 (92 sends), stranular, lfo-pnoise. Priority: medium. Effort: medium.*

**F2 — Parametric component bank + freeze orchestration.** `Device.define_component/instance` — author one bpatcher once, stamp N times with `args=[i,...]`, auto-suffix params (`name[i]`), auto-register in the freeze `dependency_cache`, and emit `parameter_overrides` (pairs with E5). Makes multi-LFO/band/step devices maintainable (lfo-cluster: 101 params from 12 roles × 6). *Devices: lfo-cluster, stranular, Chiral. Priority: medium. Effort: medium.*

**F3 — Embedded presentation-mode bpatcher DSP module.** `Subpatcher.to_presentation_patcher_dict()` + `Device.add_bpatcher_module(builder_fn, rect, inlets, outlets, embed=1, presentation=1)` to author a VISIBLE self-contained DSP+UI module (signal inlets/outlets) and inline-embed it, reusable across a device family; pair with `recipes.tab_panel_stack()` (scripted `hidden $1` reveal) and `reorderable_chain()` (scripted connect/disconnect). Today only invisible `p` or external-file refs work. *Devices: AS_Console_Width, AS_Console_1.02. Priority: medium. Effort: large.*

**F4 — Native-only premium recipes (no jsui/gen~).** `switchable_bank()` (parallel processors → `selector~ N 1` + the `+1` tab-index shim wired L/R from one control), `bypass_wrapper()` (`selector~ 2 1` raw-vs-processed), `matrix_router` (`matrix~ N M @ramp 50` + connection-message generator + jstrigger complementary gains, replacing verbose `dry_wet_stage`), dual-rate `poly~ up 2/up 4 @resampling 1` oversampling with mute-switching, and a GR meter (`snapshot~ 50 → atodb~ → multislider` w/ ghostbar/ignoreclick/parameter_enable=0). *Devices: SEAR, Rainbow, AS_Console_1.02, AS_Console_Komp. Priority: medium. Effort: medium.*

**F5 — Shared versioned JS-module library.** `engines/jsui_lib/` bundle (Component, JSUIParameter, MouseHandler/ByOS, GlobalParam zoom-aware coord class, hover, one generated colors module from theme.py) registered as versioned Asset deps via require()/include(), plus `Device.add_js_module()`. Ends one-JS-blob-per-control duplication; the foundation the theme-bus and buffer-viz engines build on. *Devices: lfo-cluster, Particle-Reverb, stranular, Chiral. Priority: low. Effort: large.*

**F6 — mgraphics premium-drawing toolkit + native interaction layer.** Shared `ui_kit.py` primitives: `stroke_preserve_area_fill(alpha)`, `ring_glow` (draw twice: crisp + alpha-0.175 set_line_width, ×0.75 decay), `floorPos/specLine` crisp +0.5 snap, `text_path_centered`, `path_roundcorners`, `copy_path/append_path` ghost trails, transformed-pattern lit-glass gradient, `mask_frame` (punch black ignoreclick:1 holes over native widgets), `drawdashline`; plus a GlobalParam endless-drag wrapper (hidecursor + pupdate teleport, zoom-aware via `patcher.wind.location`), delta-scaled drag (~0.025–0.2/px), a 5-sample-voting axis-lock with cmd/opt multi-param routing, shift=fine, dblclick=reset, and the `_hdcolor/_hi` handle convention. Several confirmed 0-hit gaps. *Devices: Rainbow, stranular, lfo-cluster, Particle-Reverb, Chiral. Priority: low. Effort: large.*

**F7 — Parameter-state hero engine + curve/envelope editor.** `engines/param_state_hero.py` mirroring 3–6 params into one figure (radius/ring-count/glow/color via a bipolar two-accent pow-1.5 LUT) with an optional color-outlet recoloring sibling readouts; plus a polar/circular buffer-waveform option; plus a multi-handle ADSR/curve editor that outlets values via notifyclients(). *Devices: Particle-Reverb, Chiral, stranular. Priority: low. Effort: large.*
