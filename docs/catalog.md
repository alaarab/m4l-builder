# Catalog

A browsable index of the public building blocks. Regenerate with `uv run python tools/build_catalog.py`.

## DSP blocks (109)

| Name | Summary |
|------|---------|
| `adsr_envelope` | Create a live.adsr~ envelope generator. |
| `aftertouch_in` | Receive MIDI channel aftertouch, output 0-127. |
| `allpass_filter` | Create an allpass filter using filtercoeff~ and biquad~. |
| `analog_oscillator_bank` | Multiple phasor~ oscillators with per-voice detuning for unison thickness. |
| `arpeggiator` | Create an arpeggiator using arpeggiate and makenote. |
| `auto_gain` | RMS-based auto loudness normalization. |
| `bandpass_filter` | Create a stereo band-pass filter using svf~. |
| `bank_select_in` | Receive MIDI bank select (CC 0 MSB + CC 32 LSB), output combined bank number. |
| `bitcrusher` | Bit depth and sample rate reduction. |
| `buffer_load` | Create a buffer~ for wavetable storage. |
| `chord` | Transpose MIDI pitch into a chord using + objects for each interval. |
| `coll_store` | Create a coll object for indexed data storage. |
| `comb_resonator` | Create N parallel comb~ filters summed to a single output. |
| `compressor` | Create a log-domain stereo compressor. |
| `convolver` | Convolve a signal with an impulse response stored in a buffer~. |
| `crossover_3band` | Create a 3-band crossover using two cross~ objects. |
| `ctlin` | Receive MIDI continuous controller messages. |
| `ctlout` | Send MIDI continuous controller messages. |
| `cv_recorder` | Record and playback CV to a table object. |
| `cv_smooth_lag` | Extended CV smoothing with selectable mode. |
| `dc_block` | Create a stereo DC blocking filter. |
| `delay_line` | Create a tapin~/tapout~ delay line pair. |
| `dict_store` | Create a dict object for key-value data storage. |
| `dry_wet_mix` | Create a stereo dry/wet crossfade stage (0.0-1.0 mix control). |
| `envelope_follower` | Create an envelope follower: abs~ -> slide~. |
| `euclidean_rhythm` | Generate a Euclidean rhythm: `pulses` hits spread evenly over `steps`. |
| `fdn_reverb` | Feedback delay network reverb with prime delay times. |
| `feedback_delay` | Create a delay line with tanh~ saturation and onepole~ filtering in the feedback path. |
| `gain_stage` | Create a stereo *~ gain stage (left and right channels). |
| `gate_expander` | Stereo noise gate with threshold detection. |
| `gen_codebox` | Create a gen~ object with embedded codebox code. |
| `grain_cloud` | Granular cloud using groove~ for multi-voice playback. |
| `groove_player` | Create a buffer~ + groove~ pair for sample playback. |
| `highpass_filter` | Create a stereo high-pass filter using svf~. |
| `highshelf_filter` | Create a stereo high-shelf EQ filter using biquad~. |
| `lfo` | Create a unipolar LFO (0-1 output) with depth scaling. |
| `lfsr_generator` | Linear feedback shift register for pseudo-random sequences. |
| `limiter` | Create a stereo brickwall limiter. |
| `live_param_signal` | Create a live.param~ object that outputs a parameter value as signal. |
| `live_remote` | Create a live.remote~ object for sample-accurate parameter control. |
| `loadbang` | Create a loadbang object that fires a bang on device load. |
| `lookahead_envelope_follower` | Lookahead envelope follower: delays the signal while detecting envelope ahead. |
| `lowpass_filter` | Create a stereo low-pass filter using svf~. |
| `lowshelf_filter` | Create a stereo low-shelf EQ filter using biquad~. |
| `macro_modulation_matrix` | N sources x N targets modulation matrix with per-cell gain. |
| `macromap` | Maps a device parameter to a Live macro knob. |
| `matrix_mixer` | NxN gain routing matrix. |
| `mc_collapse` | Collapse N-channel MC signal to stereo using mc.unpack~ and summing. |
| `mc_expand` | Expand stereo to N-channel using mc.pack~. |
| `mc_gain_stage` | Multichannel gain control using mc.gain~. |
| `mc_mixer` | Sum multiple MC streams using mc.mix~. |
| `mc_selector` | Switch between MC signal paths using mc.selector~. |
| `midi_channel_filter` | Route MIDI input to a specific channel. |
| `midi_clock_in` | Detect incoming MIDI clock and output BPM as a float. |
| `midi_clock_out` | Send MIDI clock (24 ppqn) synced to Live transport. |
| `midi_learn_chain` | MIDI learn chain: captures next incoming CC and routes it to a named send. |
| `midi_thru` | Raw MIDI byte passthrough (midiin -> midiout). |
| `sysex_out` | Send MIDI system exclusive via sxformat -> midiout. |
| `midi_tool_io` | Create the live.miditool.in / live.miditool.out pair for a MIDI Tool. |
| `modwheel_in` | Receive MIDI mod wheel (CC 1), output 0-127. |
| `morphing_lfo` | LFO blending between sine, triangle, square, and saw shapes. |
| `ms_encode_decode` | Create Mid/Side encode and decode stages. |
| `multiband_compressor` | 3-band mono compressor using crossover_3band and compressor blocks. |
| `noise_source` | Create a noise generator. |
| `notch_filter` | Create a stereo notch filter using svf~. |
| `note_expression_decode` | Decode MIDI note expression: pitch, velocity, channel, aftertouch, pitchbend. |
| `notein` | Receive MIDI note messages (pitch, velocity, channel). |
| `noteout` | Send MIDI note messages. |
| `onepole_filter` | Create a stereo one-pole low-pass filter (onepole~, 2 inlets: signal, cutoff Hz). |
| `param_smooth` | Smooth a control signal using pack + line~. |
| `pattr_system` | Create an autopattr + pattrstorage pair for parameter save/recall. |
| `peaking_eq` | Create a parametric peaking EQ band using filtercoeff~ and biquad~. |
| `phase_vocoder_subpatcher` | Return the pfft~ subpatcher dict for a phase vocoder. |
| `pitch_quantize` | Quantize MIDI pitch to a musical scale using the scale Max object. |
| `pitchbend_in` | Receive MIDI pitchbend and scale to semitone range. |
| `poly_voices` | Polyphonic voice allocator using poly~. |
| `probability_gate` | Probabilistic gate: pass an incoming bang only some fraction of the time. |
| `program_change_in` | Receive MIDI program change messages. |
| `quantize_time` | Snap time to beat grid using transport quantize. |
| `random_note` | Generate a random MIDI note number in [low, high] on each incoming bang. |
| `random_walk` | Brownian motion smooth random CV signal. |
| `receive_msg` | Create a receive object for message-domain routing without patch cords. |
| `receive_signal` | Create a receive~ object for signal-domain routing without patch cords. |
| `reverb_network` | Schroeder reverb network with parallel combs and series allpasses. |
| `sample_and_hold` | Sample-and-hold modulation source. |
| `sample_and_hold_triggered` | Sample-and-hold with external trigger signal. |
| `saturation` | Create a stereo saturation stage. |
| `scale_range` | Create a scale object to map an input range to an output range. |
| `selector` | Create a selector~ for switching between signal inputs. |
| `send_msg` | Create a send object for message-domain routing without patch cords. |
| `send_signal` | Create a send~ object for signal-domain routing without patch cords. |
| `sidechain_detect` | Mono envelope follower for sidechain signal detection. |
| `sidechain_routing` | Route external audio as sidechain via second plugin~ input. |
| `signal_divide` | Create a signal-rate division block. |
| `spectral_crossover` | Spectral crossover using pfft~ pointing to spectral_crossover_sub.maxpat. |
| `spectral_crossover_subpatcher` | Return the pfft~ subpatcher dict for spectral band splitting. |
| `spectral_gate` | Spectral gate using pfft~ pointing to spectral_gate_sub.maxpat. |
| `spectral_gate_subpatcher` | Return a dict representing the pfft~ subpatcher JSON for spectral gating. |
| `spectrum_band_extract` | Extract a frequency band using cascaded highpass + lowpass filters. |
| `stereo_io` | Create plugin~ and plugout~ pair for audio I/O. |
| `stft_phase_vocoder` | Phase vocoder using pfft~ for time-stretch/pitch-shift. |
| `tempo_sync` | Read Live transport tempo and compute a time value for a given beat division. |
| `tilt_eq` | Create a stereo tilt EQ using onepole~ as a crossover. |
| `transport_lfo` | LFO synced to Live transport tempo. |
| `transpose` | Transpose MIDI pitch by semitones with 0-127 clamping. |
| `tremolo` | Create a tremolo effect: LFO amplitude modulation. |
| `velocity_curve` | Remap MIDI velocity with a curve function. |
| `vocoder` | N-band vocoder: carrier analysis + modulator filtering. |
| `wavetable_osc` | Create a wavetable~ oscillator. |
| `xfade_matrix` | N-input crossfade matrix. |

## UI widgets (49)

| Name | Summary |
|------|---------|
| `Theme` | Coordinated color theme for M4L devices. |
| `adsrui` | Create a live.adsrui ADSR envelope editor. |
| `bpatcher` | Create a bpatcher embeddable sub-patcher. |
| `button` | Create a live.button (momentary trigger, parameter-enabled for automation). |
| `comment` | Create a live.comment label. |
| `dial` | Create a live.dial with parameter storage. |
| `fpic` | Create an fpic image display. |
| `grain_display_js` | Return JavaScript source for a granular display (Max jsui). |
| `grid_sequencer_display_js` | Return JavaScript source for a 2D grid sequencer display (Max jsui). |
| `jsui` | Create a jsui display for custom vector graphics via Max's mgraphics (Cairo) API. |
| `kslider` | Create a kslider piano keyboard display. |
| `live_arrows` | Create a live.arrows direction arrow buttons. |
| `live_drop` | Create a live.drop drag-and-drop file target. |
| `live_gain` | Create a live.gain~ fader with built-in meter. |
| `live_grid` | Create a live.grid toggleable cell grid. |
| `live_line` | Create a live.line visual divider. |
| `live_step` | Create a live.step step sequencer UI. |
| `live_text` | Create a live.text styled button/toggle. |
| `matrixctrl` | Create a matrixctrl grid matrix control. |
| `menu` | Create a live.menu dropdown selector. |
| `meter` | Create a live.meter~ level meter. |
| `multislider` | Create a multislider bar/step display. |
| `nodes` | Create a nodes XY node editor with draggable points. |
| `nslider` | Create an nslider staff notation display. |
| `number_box` | Create a live.numbox numeric display with parameter storage. |
| `panel` | Create a panel background element. |
| `peaking_eq_display_js` | Return JavaScript source for a peaking EQ band display (Max jsui). |
| `piano_roll_js` | Return JavaScript source for a piano roll display (Max jsui). |
| `radiogroup` | Create a radiogroup vertical radio buttons. |
| `resonance_bank_display_js` | Return JavaScript source for a resonance bank display (Max jsui). |
| `rslider` | Create an rslider range slider with two handles. |
| `scope` | Create a live.scope~ display. |
| `sidechain_display_js` | Return JavaScript source for a sidechain envelope display (Max jsui). |
| `slider` | Create a live.slider with parameter storage. |
| `spectral_display_js` | Return JavaScript source for a spectral bin display (Max jsui). |
| `spectral_vocoder_display_js` | Return JavaScript source for a spectral vocoder band display (Max jsui). |
| `step_grid_display_js` | Return JavaScript source for a step sequencer grid display (Max jsui). |
| `swatch` | Create a swatch color picker/display. |
| `tab` | Create a live.tab selector. |
| `textbutton` | Create a textbutton text button (no parameter storage). |
| `textedit` | Create a textedit editable text field for user text input. |
| `toggle` | Create a live.toggle with parameter storage. |
| `ubutton` | Create a ubutton invisible click zone. |
| `umenu` | Create a umenu dropdown menu (no parameter storage). |
| `v8ui` | Create a v8ui display for modern pointer-aware custom UI rendering. |
| `velocity_curve_display_js` | Return JavaScript source for a velocity curve display (Max jsui). |
| `wavetable_display_js` | Return JavaScript source for a wavetable display (Max jsui). |
| `wavetable_editor_js` | Return JavaScript source for an interactive wavetable editor (Max jsui). |
| `xy_pad_js` | Return JavaScript source for an XY pad control (Max jsui). |

## Recipes (23)

| Name | Summary |
|------|---------|
| `ModuleSpec` | Pre-mount description of a reusable graph module. |
| `Stage` | Base class for reusable graph stages. |
| `StageResult` | Mapping-compatible stage result with semantic metadata. |
| `arpeggio_quantized_stage` | Add an arpeggiator followed by pitch quantization. |
| `convolver_controlled_stage` | Add a convolver with dry/wet mix controlled by a dial. |
| `dry_wet_stage` | Add a dry/wet crossfade stage: live.dial (0-100) -> scaled mix. |
| `euclidean_sequencer_stage` | Add a Euclidean rhythm MIDI sequencer. |
| `gain_controlled_stage` | Add a gain-controlled stage: live.dial -> dbtoa -> *~ gain cell. |
| `generative_midi_stage` | Add a self-contained generative MIDI note generator. |
| `grain_playback_controlled` | Add a granular playback stage with position, size, and density dials. |
| `lfo_matrix_distribute` | Fan one LFO output to multiple depth-scaled targets. |
| `midi_learn_macro_assignment` | Add a MIDI learn chain with macro mappings for multiple targets. |
| `midi_note_gate` | Add a MIDI note input stage: notein -> unpack -> stripnote -> kslider. |
| `module_from_block` | Lift a legacy `(boxes, lines)` helper into the module abstraction. |
| `mount_module` | Mount a module onto a graph and return a stage-style result. |
| `parametric_eq_band_backend` | Add one stereo parametric EQ band backend with smoothing and retriggers. |
| `poly_midi_gate` | Add a polyphonic MIDI input stage: notein -> velocity curve -> poly~. |
| `sidechain_compressor_recipe` | Add a sidechain compressor with threshold and ratio dials. |
| `spectral_gate_stage` | Add a spectral gate with threshold dial and spectral display. |
| `stage_result` | Convenience constructor for StageResult. |
| `stereo_width_stage` | Add a mid/side stereo width control. |
| `tempo_synced_delay` | Add a tempo-synced delay: two dials + tapin~/tapout~ with transport. |
| `transport_sync_lfo_recipe` | Add a transport-synced LFO with depth dial and division menu. |

## Themes (10)

`COOL`, `FOREST`, `INDUSTRIAL`, `LIGHT`, `LOFI`, `MIDNIGHT`, `SOLAR`, `SYNTHWAVE`, `VIOLET`, `WARM`

## Engines (26)

JavaScript (jsui) visualization generators.

| Module | Generators |
|--------|------------|
| `compressor_display` | `compressor_display_js` |
| `crossover_display` | `crossover_display_js` |
| `envelope_display` | `envelope_display_js` |
| `eq_band_column` | `eq_band_column_js` |
| `eq_curve` | `eq_curve_js` |
| `filter_curve` | `filter_curve_js` |
| `grain_display` | `grain_display_js` |
| `grid_sequencer_display` | `grid_sequencer_display_js` |
| `lfo_display` | `lfo_display_js` |
| `linear_phase_eq_display` | `linear_phase_eq_display_js` |
| `peaking_eq_display` | `peaking_eq_display_js` |
| `piano_roll` | `piano_roll_js` |
| `resonance_bank_display` | `resonance_bank_display_js` |
| `sidechain_display` | `sidechain_display_js` |
| `slice_overview` | `slice_overview_js` |
| `slice_pattern_display` | `slice_pattern_display_js` |
| `spectral_display` | `spectral_display_js` |
| `spectral_vocoder_display` | `spectral_vocoder_display_js` |
| `spectrum_analyzer` | `spectrum_analyzer_dsp`, `spectrum_analyzer_js` |
| `step_grid_display` | `step_grid_display_js` |
| `velocity_curve_display` | `velocity_curve_display_js` |
| `waveform_display` | `waveform_display_dsp`, `waveform_display_js` |
| `wavetable_display` | `wavetable_display_js` |
| `wavetable_editor` | `wavetable_editor_js` |
| `xy_pad` | `xy_pad_js` |
| `xy_trail_display` | `xy_trail_display_js` |
