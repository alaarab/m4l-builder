# Changelog

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
