# Changelog

## [Unreleased]

### Added

- `m4l` command line (console script, also `python -m m4l_builder`): `new`
  scaffolds a build script for an audio, MIDI or instrument device, `build`
  runs a script with an optional `--out` redirect, `watch` rebuilds into the
  User Library on save and prints what changed, `lint` runs graph, box and
  GenExpr lint without writing, and `inspect` summarises an `.amxd`.
- `m4l preview` and `m4l_builder.preview.render_svg`: draw a device's
  presentation view as a stdlib-only SVG (theme colours, native controls at
  their initial values, jsui/v8ui as labelled placeholders). The README and
  docs gallery show the six examples, kept in sync by a golden test.
- `m4l import DEVICE.amxd` (and `m4l_builder.importer`): writes a readable
  `build.py` that rebuilds an existing device, frozen or not. Controls become
  `add_dial` / `add_menu` / ... calls, objects `add_newobj`, patch cords
  `add_line`; gen~ code, scripts, subpatchers, banks and the theme carry
  across. Each call is checked against the source box, boxes with no library
  call stay raw with a TODO, and the command confirms the rebuilt device is
  identical. Guide: `docs/importing.md`.
- Offline audio render (`m4l_builder.render`, `m4l render`): runs a device's
  `plugin~` to `plugout~` path (gen~ codeboxes via `gen_sim`, MSP arithmetic,
  and the parameter controls feeding them) on a WAV or generated signal and
  writes the result as a WAV. Parameters are set by name. Checks for tests:
  `check_not_dry` (catches a gen~ that passes audio through untouched),
  `check_identity`, `check_silent`, `check_finite`, and `audit()` to run them
  all; `summarize` gives RMS, peak and coarse band levels. Anything the
  renderer can't run raises `RenderError` naming the box.
- `gen_sim` runs more of the library's own snippets: `Data` with positional
  `peek`/`poke`/`dim`/`channels`, `change()`, compound assignment (`+=` and
  friends), and, marked approximate in `GenKernel.approximations` (refused
  with `strict=True`), `noise()` and cubic `Delay` reads.
  `tools/gen_sim_coverage.py` lists which snippets run.

### Fixed

- `gen_sim`'s `fold()` returned its input unchanged; it now reflects into the
  range like gen's. Unknown names, unparseable expressions and arithmetic
  errors (a division by zero) now raise `UnsupportedKernel` naming the sample,
  instead of a raw Python exception.

## [0.8.0] — 2026-11-26

The first published release since 0.7.0. `pyproject.toml` has said 0.8.0
since 2026-05-30, but nothing was tagged or published until now, so this
entry covers everything since 0.7.0.

### Compatibility

- Require Python 3.10+ for standalone device authoring. This library does not run
  inside Ableton's bundled Python; the new minimum permits current development
  and build tooling, including mypy 2 and pytest 9. No runtime dependencies added.

### Added

**Live 12 MIDI Tools**

- `MidiTransformation` and `MidiGenerator` device types (`.amxd` device-type
  codes `natt` / `nagg`, byte-verified against Live 12's own MIDI Tool files),
  with round-trip read-back via `device_from_amxd`.
- `midi_tool_io` block: the `live.miditool.in` / `live.miditool.out` scaffold.
- `docs/midi_tools.md` guide.
- `NoteEvent` / `notes_dict` (new `notes` module): pure-Python builders for
  the Live 12 MIDI Tool notes dictionary (`{"notes": [...]}`), with range
  validation and JSON-ready output. Structure-building only — sending the
  dict to `live.miditool.out` still needs Live-side wiring (see roadmap).

**Device authoring**

- `gen_sim` runs user-defined gen functions (state per call site, `Delay`
  arguments, two-value returns), `Param` declarations with `min`/`max`, `Delay`
  sizes that use `samplerate`, and the `mstosamps`/`sampstoms`, `pi`/`twopi`/
  `halfpi` and `minimum`/`maximum` builtins.
- `add_newobj` / `newobj`: `numinlets`, `numoutlets` and `outlettype` are now
  optional and inferred from the object text (`m4l_builder.object_io`).
  Argument rules cover pack/pak/unpack, route/routepass, sel/select,
  trigger, gate/gate~, switch, selector~, join/unjoin, spray, funnel,
  int/float/signal math, send/receive, expr/if/sprintf and mc.pack~/unpack~;
  other objects use the vendored maxdiff dataset (bare, or with arguments
  for objects whose shape doesn't depend on them). Unknown or
  context-dependent objects raise `UnknownObjectIO`. Explicit values always
  win and existing calls build byte-identical output.
- `Device.bind_gen_param`: validated control -> prepend -> gen~ wiring for
  embedded and registered external GenExpr cores.
- `gen_snippets.peak_hold`: constant-duration peak decay across sample rates.
- Content fingerprints for comparing installed patchers and assets with current
  factories, plus shared device-directory discovery including MIDI Tools.
- Build validation now checks custom UI handlers from the canonical asset registry,
  including nested patchers, and runs the same checks in default/error policies.
  Required scripts are checked for byte, file, frozen and unfrozen output.
- Build output is staged before replacement and rolled back on write failures.
  Freezing fails on missing dependencies by default (`allow_missing=True` is an
  explicit opt-out); exporting an already-frozen input now copies it to the
  requested destination.
- `sysex_out` recipe: send MIDI system exclusive messages via `sxformat` -> `midiout`,
  with optional auto 0xF0/0xF7 framing and per-byte dynamic inlets.
- `cc_mapper_lane` (+ `_ui_lines` / `_mpe_lines` wiring helpers) and `mpe_io_chain`:
  building blocks for MPE-aware MIDI CC mapper devices.
- `message()` object factory (message-box counterpart to `newobj()`).
- **Device freezing for portability** (`m4l_builder.freeze`): build self-contained
  `.amxd` files that embed every dependency (jsui `.js`, `gen~` `.gendsp`/`.genjit`,
  `.maxpat` abstractions, images) inside the device — so a single file works on
  another computer instead of rendering blank UIs / dead DSP when its loose
  sidecars are missing. `assemble_frozen_amxd`, `device_to_frozen_bytes`,
  `freeze_amxd_file` (freeze an already-built device in place/to a copy), plus
  `Device.build(out, freeze=True)` / `Device.to_bytes(freeze=True)`. The binary
  freeze footer (`mx@c` header + `dlst`/`dire` directory, `meta=7`) is
  conformance-tested byte-for-byte against an independent reference parser.
  Max's "Freeze Device" is GUI-only (no message/API/CLI), so the writer
  reproduces it directly.
- `sample_drop_target` recipe: a drag-and-drop audio sample intake using
  `live.drop` (which accepts drags from BOTH the Live browser AND the Finder —
  `dropfile` only catches Finder drops, the usual reason sample-drop "doesn't
  work" inside Live). Wires `live.drop -> t b l -> prepend replace -> buffer~`
  with a settle delay that exposes a reliable "loaded" bang for redraw/analysis.
- `gen_snippets` harmonic-exciter foundation: `one_pole_coeff` (cutoff-frequency
  `1 - exp(-2*pi*f/fs)` coefficient), `one_pole_lp` / `one_pole_hp` (the shared
  1st-order low-/high-pass split), and `exciter_harmonics` (the harmonic-exciter
  generator — a level-matched odd `tanh` shaper plus an even squarer, returning
  the *added* content). All behaviourally null-tested via `gen_sim`; the
  registry is now 17 primitives. Composed by the new `Sheen` harmonic exciter.
- `engines/exciter_curve.py` (`exciter_curve_js`): a harmonic-exciter-style hero —
  a log-frequency band-lift envelope with draggable LOW/HIGH handles (drag X =
  tune, Y = amount) and a live output glow.

**Generative building blocks**

- `probability_gate`, `random_note`, and `euclidean_rhythm` DSP blocks.
- `generative_midi_stage`, `euclidean_sequencer_stage`, and `stereo_width_stage`
  recipes.

**Docs & examples**

- Six runnable example devices (`examples/`) covering every device category,
  guarded by `tests/test_examples.py`.
- `docs/getting_started.md`, a generated `docs/catalog.md`, `docs/roadmap.md`,
  plus `CONTRIBUTING.md` / `DEVELOPING.md`.

### Fixed

- Newobj inlet/outlet declarations that didn't match what Max 9 saves now
  use the inferred shape (checked against Max 9 help patches): `loadbang`,
  `midiin` and `noise~` get their inlet, `route`/`sel`/`select` an inlet per
  argument, `cycle~` one outlet, `midiparse` eight, and `pack f 0. 20`,
  `adsr~`, `autopattr`, `counter`, `timer`, `snapshot~`, `line~`, `rect~`
  and `tri~` their full inlets/outlets and outlet types. Built output
  changes for `dsp.loadbang`, `pattr_system`, `envelope_follower`, `lfo`,
  `sample_and_hold`, `random_walk`, `noise_source`, `xfade_matrix`,
  `midi_learn_chain`, `midi_clock_in`, `midi_channel_filter`,
  `live_brand_dim`, `live_theme_state_dim`, `add_flyout`,
  `add_width_collapse`, `expandable_column`, `modulator_slot_component`,
  `settings_sidebar` and `parametric_eq_band_backend`.
- `midi_clock_in` now works. It read `select 248` from midiparse's note
  outlet instead of the raw `midiin` bytes, timed on counter's underflow
  flag instead of the per-quarter-note carry, and computed `ms * 0.06`
  instead of BPM. It now goes midiin -> `select 248` -> `counter 0 23` carry
  -> `sel 1` -> `t b b` -> `timer` -> `/ 1000.` -> `!/ 60.`, and the unused
  midiparse box is gone. The output is still `{prefix}_bpm_scale` outlet 0.
- `sysex_out` byte validation: out-of-range values used to wrap silently
  (`256 -> 0`, `-1 -> 255`); they now raise, and body bytes are checked to be
  7-bit (only the 0xF0/0xF7 framing may exceed 127).
- `device_output_path` now knows the Live 12 MIDI Tool device types
  (`note_transformation`, `note_generator`) and resolves them to the
  `MIDI Tools/Max Transformations|Max Generators` folders at the User Library
  root. Unknown device types now raise `ValueError` instead of silently
  landing in the Audio Effects folder.

### Changed

- GitHub Actions CI: lint, type-check and a pytest matrix on Python 3.10–3.14.
- Configured ruff and mypy in `pyproject.toml`; added a `py.typed` marker;
  modernized type annotations (PEP 585/604).
- Reimplemented the stateful gen primitives (`lowpass_12_fn`,
  `highpass_12_fn`, `allpass_fn`, `svf_fn`, `tanh_approx_fn`, `op_fn`,
  `qpow_fn`, `fade_env_fn`, `ramp_env_fn`, `lfo_osc_fn`, `granular_voice_fn`,
  `freeze_capture_block`, `viz_poke_block`, `ms_width_equal_power`,
  `modulated_allpass_reverb`) with the same names and signatures. Behaviour
  notes: `svf_fn` no longer needs `tanh_approx_fn`; `ramp_env_fn` takes its
  per-cycle random draw from `rnd_t` (-1..1); `lfo_osc_fn` reads one shape per
  buffer channel; `ms_width_equal_power` uses a sine/cosine law (mono is
  `(L+R)/sqrt(2)`); `modulated_allpass_reverb` declares its own Params. Their
  tests check behaviour (frequency response, energy, decay, timing) in
  `gen_sim`.
- CI now enforces an 85% coverage floor (`fail_under` in pyproject;
  measured 87% when added).
- The uniform layout-container proxies are generated from name tables
  instead of 28 hand-copied methods (no API change), with exhaustive proxy
  smoke tests and a Device-widget parity test.
- `Device.add_*` widget methods and the layout-container proxies are declared
  in the class body with their ui.py factory's real signature, so mypy and
  IDEs check their arguments (runtime wrappers unchanged; output identical).
- `from m4l_builder import X` is statically typed: `__init__` carries a
  TYPE_CHECKING import block generated by `tools/gen_root_type_imports.py`
  (runtime loading stays lazy).
- mypy is fully gated: no `ignore_errors` overrides remain (`device_widgets`
  and `livemcp_bridge` now type-check) and `implicit_optional` is off.
- Hardened `.amxd` serialization errors and bridge color-mixing validation.

### Removed

- The `.amxd` analysis and code-generation API and its root exports.
  `Device.from_amxd` and the LiveMCP bridge stay.
- Untracked scratch files and stale notes; generated artifacts are now
  gitignored.
- Dead helpers: `ParameterSpec.with_bank`, `constants.DEFAULT_BG_COLOR`,
  `constants.DEFAULT_ACCENT_COLOR`, `gen_character.HALF_PI`.

## [0.7.0] — 2026-03-04

### Added

**New JS Engines**
- `lfo_display_js()` — animated LFO waveform with sweeping playhead; inlets: shape, phase, depth
- `compressor_display_js()` — transfer curve with live gain-reduction dot riding the curve; inlets: threshold, ratio, gr
- `xy_trail_display_js()` — XY pad with 32-point fading circular buffer trail

**New Devices**
- `probability_gate.py` — 16-step MIDI gate with per-step probability bars (multislider), tempo-synced via live.beat~
- `morphing_filter.py` — large XY pad (cutoff × resonance) with filter type tab and Lissajous LFO auto-movement
- `glue_compressor.py` — VCA-style bus compressor with transfer curve display, stepped ratio tab, auto-gain toggle
- `parallel_compressor.py` — NY-style parallel fattener with blend control and dry/wet meters

### Changed

**Bug Fix**
- `ui.py`: `parameter_enum` now emits a JSON array instead of a space-joined string in all 5 places (`tab`, `toggle`, `menu`, `button`, `live_text`). Fixes tabs/menus showing "0"/"1" index labels instead of option text in Ableton.

**Visual Improvements — all 46 example devices**
- Titles removed from all plugins (device name appears in Ableton's browser; in-plugin titles are redundant noise)
- `simple_compressor`: upgraded with compressor transfer curve + live GR dot via `compressor_display_js`
- `rhythmic_gate`: upgraded with LFO waveform preview via `lfo_display_js`
- `auto_filter`: filter display now 51% of device height; live Hz readout prominent
- `multiband_saturator`: switched to MIDNIGHT theme; scope at top; darker background
- `comb_bank`: bigger scope, primary tuning dials wider
- `lofi_processor`: scope at 35% of height, primary controls more prominent
- `midside_suite`: MIDNIGHT theme; M/S section panels with teal/blue visual separators
- `stereo_delay`: scope at top showing output waveform; larger L/R time dials
- `analog_supersaw`: oscilloscope at top wired to output; MIDNIGHT theme; better layout
- `step_sequencer`: step grid takes 80% of height; division tab; live step number display
- `midi_arpeggiator`: kslider piano display showing active notes; mode as full-width tab
- `probability_gate`: multislider at 70% of height; GATE flash indicator; teal bars
- `midi_chord`: chord type as tab (MAJ/MIN/DIM/AUG/SUS2/SUS4); kslider showing chord shape

**Code Quality**
- `dsp.py`: moved `import math` from inside `_biquad_shelf()` to top-level imports
- Humanize pass across all 46 examples: removed restating-the-code comments, "We use..." voice, redundant section headers

## [0.6.0] — 2026-03-04

### Added

**Recipes (#91-#100)**
- `convolver_controlled_stage` — convolver + wet/dry dial
- `sidechain_compressor_recipe` — sidechain_routing + compressor + display + 2 dials
- `lfo_matrix_distribute` — one LFO fanned to N depth targets
- `spectral_gate_stage` — pfft~ gate + threshold dial + spectral display
- `arpeggio_quantized_stage` — arpeggiator + pitch_quantize chain
- `grain_playback_controlled` — grain_cloud + buffer + position/size/density dials
- `poly_midi_gate` — notein + velocity_curve + poly_voices
- `transport_sync_lfo_recipe` — transport LFO + depth dial + division umenu
- `midi_learn_macro_assignment` — midi_learn_chain + N macromap instances

**Documentation (#101-#103)**
- `README.md` — install, quick start, key concepts, examples table
- `docs/api.md` — full API reference across all 13 modules
- `examples/from_amxd_demo.py` — round-trip: build → write → read back → modify → write

**gen~ codebox (#104-#105)**
- `gen_codebox(id_prefix, gen_code, numinlets, numoutlets)` — embed gen~ DSP code directly
- `examples/gen_codebox_demo.py` — soft clipper + one-pole lowpass via gen~

**Themes (#106)**
- `LOFI` — muted warm amber, brown-grey bg
- `SYNTHWAVE` — neon cyan on near-black purple
- `INDUSTRIAL` — vivid orange on neutral dark grey

**MC multichannel (#107-#110)**
- `mc_gain_stage` — mc.gain~ per-channel gain
- `mc_mixer` — mc.mix~ for summing MC streams
- `mc_selector` — mc.selector~ for switching MC paths
- `examples/mc_demo.py` — stereo → 4ch expand → gain → collapse

**Examples**
- `examples/recipe_cookbook.py` — "Production Chain" device using 4 recipes: gain stage, sidechain comp, LFO matrix, dry/wet

## [0.5.1] — 2026-03-04

### Changed
- Extracted `_svf_filter`, `_signal_sum_chain`, `_biquad_shelf` helpers in dsp.py — removes ~150 lines of duplication across filter/sum/shelf groups
- Added `ValueError` guards to 13 DSP functions with unbounded count params (`comb_resonator`, `fdn_reverb`, `vocoder`, `grain_cloud`, `mc_expand/collapse`, `analog_oscillator_bank`, `poly_voices`, `matrix_mixer`, `macro_modulation_matrix`, `xfade_matrix`, `bitcrusher`, `reverb_network`) and `device.assign_parameter_bank`
- Removed unused `fade_time` parameter from `spectral_gate`
- Fixed `sample_and_hold` noise~ numinlets (0, not 1)
- Added type annotations to 12 DSP functions missing them
- Humanize pass: removed restate comments in `device.py` and `recipes.py`, rewrote 3 docstrings
- Creative pass: beat grouping gridlines in `grid_sequencer_display`, level reference lines in `spectral_vocoder_display`, beat emphasis in `piano_roll`

## [0.5.0] — 2026-03-04

### Added

**Device methods**
- `device.validate()` — static analysis returning list of warnings (duplicate IDs, bad patchlines, missing plugin~/plugout~, orphan boxes)
- `device.to_json(indent=2)` — patcher dict as formatted JSON string for inspection/diffing
- `device.wire_chain(obj_ids, outlet, inlet)` — wire a list of IDs in series
- `device.assign_parameter_bank(varname, bank, position)` — Push/controller bank layout
- `device.from_amxd(path)` classmethod — parse an existing .amxd back to a Device

**DSP blocks**
- `send_signal` / `receive_signal` — send~/receive~ signal routing without patch cords
- `send_msg` / `receive_msg` — message-domain routing
- `loadbang` — fires bang on device load for initialization
- `scale_range` — range mapping with optional exponential curve
- `groove_player` — buffer~ + groove~ sample playback pair
- `coll_store` / `dict_store` — persistent indexed and key-value data storage
- `pattr_system` — autopattr + pattrstorage for full parameter save/recall
- `midi_channel_filter` — route MIDI from a specific channel

**Subpatcher system**
- `Subpatcher` class — mini-Device builder that embeds into a parent via `device.add_subpatcher()`

**Recipe system**
- `gain_controlled_stage` — live.dial + dbtoa + param_smooth + *~ in one call
- `dry_wet_stage` — dial + wet/dry gain pair with inverter
- `tempo_synced_delay` — two dials + tapin~/tapout~ + transport
- `midi_note_gate` — notein + stripnote + kslider display

**Examples**
- `validate_demo.py` — shows validate() catching errors and to_json() output
- `send_receive_demo.py` — stereo device with parallel paths via send~/receive~

## [0.4.0] — 2026-03-03

### Added

**DSP blocks (#50-61, #66-69)**
- `auto_gain` — RMS-based loudness normalization with soft-knee makeup gain
- `midi_clock_out` — send MIDI clock (24 ppqn) + start/stop synced to Live transport
- `macromap` — map a device parameter to one of Live's 8 macro knobs
- `stft_phase_vocoder` — time-stretch / pitch-shift via pfft~ phase vocoder
- `spectrum_band_extract` — lightweight band extraction with cascaded biquad filters
- `morphing_lfo` — LFO that blends between sine/triangle/square/saw via a blend param
- `midi_clock_in` — detect incoming MIDI clock, output BPM and phase
- `sidechain_routing` — route a second plugin~ input as a sidechain signal
- `random_walk` — Brownian-motion CV: noise~ + slide~ + clamping
- `matrix_mixer` — NxN audio routing with per-cell gain
- `cv_recorder` — record/playback CV to a buffer
- `quantize_time` — snap beat values to a grid via transport quantize
- `macro_modulation_matrix` — NxN modulation matrix routing sources to targets
- `analog_oscillator_bank` — supersaw-style unison oscillator bank with detuning
- `lfsr_generator` — linear feedback shift register for deterministic pseudo-random sequences
- `cv_smooth_lag` — extended CV smoothing with exponential or linear modes

**Engine visualizations**
- `grid_sequencer_display_js` — 2D piano-roll style XY sequencer grid (#62)
- `wavetable_editor_js` — interactive draw-to-edit wavetable surface (#70)
- `spectral_vocoder_display_js` — carrier + modulator band display for vocoder (#71)

**Examples**
- `hardware_sync.py` — MIDI clock out + clock in with BPM display
- `morphing_lfo_demo.py` — morphing LFO driving filter, tremolo, and reverb with auto_gain
- `modulation_matrix_demo.py` — macro_modulation_matrix wiring macros to 4 targets
- `analog_supersaw.py` — full supersaw synth instrument using analog_oscillator_bank

### Changed

- `device.add_dsp(boxes, lines)` — convenience method to add a DSP block in one call
- `live_api.py` — extracted shared `_live_path_pair()` helper (no API change)
- `macro_modulation_matrix` and `matrix_mixer` share `_nxn_signal_sum()` helper internally
- `cv_smooth_lag` now raises `ValueError` for unknown mode strings

## [0.3.0] — 2026-03-03

### Added

**Layout system**
- `Row`, `Column`, `Grid` layout helpers for auto-positioning UI elements

**Theme API**
- `Theme` dataclass with `from_accent()` and `custom()` factory methods
- Built-in presets: `MIDNIGHT`, `WARM`, `COOL`, `LIGHT`, `FOREST`, `VIOLET`, `SOLAR`
- Theme injection into all `add_*` device methods

**New UI components**
- `adsrui`, `live_drop`, `bpatcher`, `swatch`, `textedit`
- `live_step`, `live_grid`, `live_line`, `live_arrows`
- `rslider`, `kslider`, `textbutton`, `umenu`, `radiogroup`
- `nodes`, `matrixctrl`, `ubutton`, `nslider`

**DSP blocks**
- `param_smooth`, `bandpass_filter`, `notch_filter`, `highshelf_filter`, `lowshelf_filter`
- `compressor`, `limiter`, `noise_source`, `tempo_sync`
- `live_remote`, `live_param_signal`, `adsr_envelope`, `peaking_eq`, `allpass_filter`
- `gate_expander`, `sidechain_detect`, `sample_and_hold`
- `multiband_compressor`, `reverb_network`
- `transport_lfo`, `pitchbend_in`, `modwheel_in`, `aftertouch_in`
- `xfade_matrix`, `midi_learn_chain`, `convolver`
- `program_change_in`, `bank_select_in`, `sample_and_hold_triggered`, `bitcrusher`
- `spectral_crossover`, `spectral_crossover_subpatcher`, `grain_cloud`

**MIDI DSP blocks**
- `notein`, `noteout`, `ctlin`, `ctlout`, `velocity_curve`, `transpose`, `midi_thru`
- `wavetable_osc`, `buffer_load`, `arpeggiator`, `chord`, `pitch_quantize`
- `lookahead_envelope_follower`, `fdn_reverb`
- `spectral_gate`, `spectral_gate_subpatcher`, `vocoder`
- `mc_expand`, `mc_collapse`, `note_expression_decode`
- `poly_voices` — polyphonic voice manager

**Engine visualizations (jsui JS generators)**
- `velocity_curve_display_js` — velocity mapping curve editor
- `wavetable_display_js` — read-only waveform viewer
- `resonance_bank_display_js` — resonator band level display
- `sidechain_display_js` — sidechain envelope + gain reduction overlay
- `spectral_display_js` — FFT spectrum bars
- `peaking_eq_display_js` — parametric EQ with draggable nodes
- `step_grid_display_js` — 1D step sequencer grid with velocity
- `grain_display_js` — granular playhead position + waveform
- `grid_sequencer_display_js` — 2D piano-roll style sequencer grid (#62)
- `wavetable_editor_js` — interactive draw-to-edit wavetable (#70)
- `spectral_vocoder_display_js` — carrier/modulator band display for vocoder (#71)

**Live API layer**
- `live_object_path`, `live_observer`, `live_set_control`

**Preset system**
- `preset_manager`, `add_preset_buttons` — save/recall parameter snapshots

**Examples (17 total)**
- `simple_gain`, `stereo_filter`, `stereo_utility`, `simple_compressor`
- `multiband_imager`, `transient_shaper`, `tape_degradation`, `stereo_delay`
- `midside_suite`, `multiband_saturator`, `rhythmic_gate`, `auto_filter`
- `comb_bank`, `lofi_processor`, `parametric_eq`, `expression_control`, `macro_randomizer`
- Additional: `wavetable_synth`, `arpeggiator_midi`, `chord_generator`, `pitch_quantizer`
- Additional: `granular_looper`, `fdn_reverb_device`, `transport_modulation`
- Additional: `expressive_midi`, `convolution_reverb`, `live_api_demo`
- Additional: `polyphonic_synth`, `preset_manager_demo`

## [0.2.0]

### Added
- `xy_pad_js` engine — interactive XY pad control
- `piano_roll_js` engine — piano roll note grid display
- Extended DSP library: `saturation`, `ms_encode_decode`, `dc_block`, `selector`
- `crossover_3band`, `comb_resonator`, `tremolo`, `envelope_follower`
- `filter_curve_js`, `eq_curve_js`, `envelope_display_js`, `spectrum_analyzer_js`, `waveform_display_js`
- Paths helper: `user_library`, `device_output_path`
- All base DSP building blocks: `stereo_io`, `gain_stage`, `dry_wet_mix`
- Highpass, lowpass, onepole filters; delay lines; LFO; tilt EQ

## [0.1.0]

### Added
- Initial release
- Core `Device`, `AudioEffect`, `Instrument`, `MidiEffect` classes
- Binary `.amxd` writer (`build_amxd`, `write_amxd`) with correct ampf header
- 16 UI element creators: `panel`, `dial`, `slider`, `toggle`, `button`, `tab`, `menu`,
  `number_box`, `comment`, `scope`, `meter`, `live_text`, `fpic`, `live_gain`,
  `multislider`, `jsui`
- `newobj`, `patchline` low-level object factories
- `UNITSTYLE_*` constants
