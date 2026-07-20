# Catalog

A browsable index of the public building blocks. Regenerate with `uv run python tools/build_catalog.py`.

## DSP blocks (119)

| Name | Summary |
|------|---------|
| `adsr_envelope` | Create a live.adsr~ envelope generator. |
| `aftertouch_in` | Receive MIDI channel aftertouch, output 0-127. |
| `allpass_filter` | Create an allpass filter using filtercoeff~ and biquad~. |
| `analog_oscillator_bank` | Multiple phasor~ oscillators with per-voice detuning for unison thickness. |
| `arpeggiator` | Create an arpeggiator using arpeggiate and makenote. |
| `auto_gain` | RMS-based makeup gain toward a target level. |
| `bandpass_filter` | Create a stereo band-pass filter using svf~. |
| `bank_select_in` | Receive MIDI bank select (CC 0 MSB + CC 32 LSB), output combined bank number. |
| `bitcrusher` | Bit depth and sample rate reduction. |
| `buffer_load` | Create a buffer~ for wavetable storage. |
| `cc_mapper_lane` | DSP for one MIDI CC mapper lane (route / learn / emit). |
| `cc_mapper_lane_mpe_lines` | Patchlines from a CC lane into an :func:`mpe_io_chain`. |
| `cc_mapper_lane_ui_lines` | Patchlines from lane UI controls into :func:`cc_mapper_lane`. |
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
| `live_modulate` | Create a live.modulate~ object — Live's grey modulation-ring output path. |
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
| `midi_tool_io` | Create the live.miditool.in / live.miditool.out pair for a MIDI Tool. |
| `modwheel_in` | Receive MIDI mod wheel (CC 1), output 0-127. |
| `morphing_lfo` | LFO blending between sine, triangle, square, and saw shapes. |
| `mpe_io_chain` | MPE MIDI I/O: midiin → mpeparse → gate/mpeformat → midiout. |
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
| `retargetable_param_sink` | The verbatim multi-target retarget sink: one ``id <n>`` stream drives |
| `reverb_network` | Schroeder reverb network with parallel combs and series allpasses. |
| `sample_and_hold` | Sample-and-hold modulation source. |
| `sample_and_hold_triggered` | Sample-and-hold with external trigger signal. |
| `saturation` | Create a stereo saturation stage. |
| `scale_range` | Create a scale object to map an input range to an output range. |
| `selector` | Create a selector~ for switching between signal inputs. |
| `send_msg` | Create a send object for message-domain routing without patch cords. |
| `send_signal` | Create a send~ object for signal-domain routing without patch cords. |
| `sidechain_detect` | Mono envelope follower for sidechain signal detection. |
| `sidechain_routing` | Route external audio as sidechain via a second plugin~ stereo pair. |
| `signal_divide` | Create a signal-rate division block. |
| `slice_pool` | Round-robin pool of ``num_voices`` ``slice_voice`` players, summed. |
| `slice_reader_gendsp` | ``(filename, content)`` of the shared Hermite slice reader (hunt #102). |
| `slice_voice` | One-shot buffer-subregion player with a de-click envelope. |
| `spectral_crossover` | Spectral crossover using pfft~ pointing to spectral_crossover_sub.maxpat. |
| `spectral_crossover_subpatcher` | Return the pfft~ subpatcher dict for spectral band splitting. |
| `spectral_gate` | Spectral gate using pfft~ pointing to spectral_gate_sub.maxpat. |
| `spectral_gate_subpatcher` | Return a dict representing the pfft~ subpatcher JSON for spectral gating. |
| `spectrum_band_extract` | Extract a frequency band using cascaded highpass + lowpass filters. |
| `stereo_io` | Create plugin~ and plugout~ pair for audio I/O. |
| `stft_phase_vocoder` | Phase vocoder using pfft~ for time-stretch/pitch-shift. |
| `sysex_out` | Send MIDI system exclusive via sxformat -> midiout. |
| `tempo_sync` | Read Live transport tempo and compute a time value for a given beat division. |
| `tilt_eq` | Create a stereo tilt EQ using onepole~ as a crossover. |
| `transport_lfo` | LFO synced to Live transport tempo. |
| `transpose` | Transpose MIDI pitch by semitones with 0-127 clamping. |
| `tremolo` | Create a tremolo effect: LFO amplitude modulation. |
| `velocity_curve` | Remap MIDI velocity with a curve function. |
| `vocoder` | N-band vocoder: carrier analysis + modulator filtering. |
| `wavetable_osc` | Create a wavetable~ oscillator. |
| `xfade_matrix` | N-input crossfade matrix. |

## UI widgets (43)

| Name | Summary |
|------|---------|
| `Theme` | Coordinated color theme for M4L devices. |
| `adsrui` | Create a ``live.adsrui`` ADSR envelope editor. |
| `alpha` | Return a copy of an RGB(A) color with its alpha replaced by ``value``. |
| `bpatcher` | Create a bpatcher embeddable sub-patcher. |
| `button` | Create a live.button (momentary trigger, parameter-enabled for automation). |
| `comment` | Create a live.comment label. |
| `derive_palette` | Derive a premium TWO-accent dark :class:`Theme` from a single accent (B2). |
| `dial` | Create a live.dial with parameter storage. |
| `fpic` | Create an ``fpic`` picture display (logo / background / SVG state graphic). |
| `js_color` | Format an RGBA color list as a ``"r, g, b, a"`` string for jsui/v8ui kwargs. |
| `jsui` | Create a jsui display for custom vector graphics via Max's mgraphics (Cairo) API. |
| `kslider` | Create a kslider piano keyboard display. |
| `live_arrows` | Create a ``live.arrows`` direction-arrow control. |
| `live_drop` | Create a ``live.drop`` file/sample drop target. |
| `live_gain` | Create a live.gain~ fader with built-in meter. |
| `live_grid` | Create a ``live.grid`` monome-style cell sequencer. |
| `live_line` | Create a live.line visual divider. |
| `live_step` | Create a ``live.step`` multi-lane step sequencer. |
| `live_text` | Create a live.text styled button/toggle. |
| `matrixctrl` | Create a ``matrixctrl`` — a ``rows``×``columns`` grid of toggle cells (routing |
| `menu` | Create a live.menu dropdown enum selector (automatable Enum param). |
| `meter` | Create a live.meter~ level meter. |
| `multislider` | Create a ``multislider`` — a strip of N bars (a multi-band meter / GR display |
| `nodes` | Create a ``nodes`` XY node editor (draggable circular nodes in a 2D field). |
| `nslider` | Create an nslider staff notation display. |
| `number_box` | Create a live.numbox numeric display with parameter storage. |
| `panel` | Create a panel background element. |
| `radiogroup` | Create a radiogroup (plain-Max radio buttons / checkboxes). |
| `rslider` | Create an rslider range slider (two handles selecting a min..max range). |
| `scope` | Create a live.scope~ display. |
| `sidechain_display_js` | Return JavaScript source for a sidechain envelope display (Max jsui). |
| `slider` | Create a live.slider with parameter storage. |
| `spectral_display_js` | Return JavaScript source for a spectral bin display (Max jsui). |
| `swatch` | Create a ``swatch`` colour picker / display. |
| `tab` | Create a live.tab selector. |
| `textbutton` | Create a textbutton text button (classic Max, NO Live parameter storage — |
| `textedit` | Create a ``textedit`` editable text / numeric entry field. |
| `toggle` | Create a live.toggle with parameter storage. |
| `ubutton` | Create a ``ubutton`` — an invisible click zone over graphics. |
| `umenu` | Create a ``umenu`` — a NON-parameter dropdown: it outputs the selected int |
| `v8ui` | Create a v8ui display for modern pointer-aware custom UI rendering. |
| `wavetable_display_js` | Return JavaScript source for a wavetable display (Max jsui). |
| `xy_pad_js` | Return JavaScript source for an XY pad control (Max jsui). |

## Recipes (30)

| Name | Summary |
|------|---------|
| `ModuleSpec` | Pre-mount description of a reusable graph module. |
| `Stage` | Base class for reusable graph stages. |
| `StageResult` | Mapping-compatible stage result with semantic metadata. |
| `arpeggio_quantized_stage` | Add an arpeggiator followed by pitch quantization. |
| `bypass_wrapper` | Hard-bypass N parallel signal paths (stereo L/R by default) with ONE |
| `convolver_controlled_stage` | Add a convolver with dry/wet mix controlled by a dial. |
| `dial_label_cell` | A dial with a caption directly below it — a premium channel-strip control cell. |
| `dry_wet_stage` | Add a dry/wet crossfade stage: live.dial (0-100) -> scaled mix. |
| `euclidean_sequencer_stage` | Add a Euclidean rhythm MIDI sequencer. |
| `gain_controlled_stage` | Add a gain-controlled stage: live.dial -> dbtoa -> *~ gain cell. |
| `generative_midi_stage` | Add a self-contained generative MIDI note generator. |
| `grain_playback_controlled` | Add a granular playback stage with position, size, and density dials. |
| `lfo_matrix_distribute` | Fan one LFO output to multiple depth-scaled targets. |
| `mc_poly_spine` | Add the modern ``mc.*`` polyphony spine — the poly~-free voice allocator |
| `midi_learn_macro_assignment` | Add a MIDI learn chain with macro mappings for multiple targets. |
| `midi_note_gate` | Add a MIDI note input stage: notein -> unpack -> stripnote -> kslider. |
| `module_from_block` | Lift a legacy `(boxes, lines)` helper into the module abstraction. |
| `mount_module` | Mount a module onto a graph and return a stage-style result. |
| `parametric_eq_band_backend` | Add one stereo parametric EQ band backend with smoothing and retriggers. |
| `poly_midi_gate` | Add a polyphonic MIDI input stage: notein -> velocity curve -> poly~. |
| `sample_drop_target` | Add a drag-and-drop audio sample intake over ``drop_rect``. |
| `sidechain_compressor_recipe` | Add a sidechain compressor with threshold and ratio dials. |
| `spectral_gate_stage` | Add a spectral gate with threshold dial and spectral display. |
| `stacked_panels` | Tabbed panel sections (C6): a ``live.tab`` selects which of N pre-added |
| `stage_result` | Convenience constructor for StageResult. |
| `stereo_width_stage` | Add a mid/side stereo width control. |
| `switchable_bank` | A/B / multi-algorithm signal bank (F4): a ``selector~ N 1`` whose active |
| `tempo_synced_delay` | Add a tempo-synced delay: two dials + tapin~/tapout~ with transport. |
| `transport_sync_lfo_recipe` | Add a transport-synced LFO with depth dial and division menu. |
| `two_panel_strip` | Two-panel channel-strip SHELL — the classic channel-strip grammar: a wide MAIN |

## Themes (16)

`AMBER`, `COBALT`, `COOL`, `FOREST`, `GRAPHITE`, `INDUSTRIAL`, `LIGHT`, `LOFI`, `MAGMA`, `MIDNIGHT`, `NEBULA`, `NEON`, `SOLAR`, `SYNTHWAVE`, `VIOLET`, `WARM`

## Engines (67)

JavaScript (jsui) visualization generators.

| Module | Generators |
|--------|------------|
| `arc_knob_cluster` | `arc_knob_cluster_js` |
| `ballistics_curve` | `ballistics_curve_js` |
| `band_chip_row` | `band_chip_row_js` |
| `buffer_viz` | `buffer_viz_js`, `multi_lane_thumbnail_js`, `waveform_layers_js` |
| `chaos_lanes` | `chaos_lanes_js` |
| `compressor_display` | `compressor_display_js` |
| `crossover_display` | `crossover_display_js` |
| `curve_editor` | `curve_editor_js` |
| `delay_trail` | `delay_trail_js` |
| `design_system` | `design_system_js`, `js_sidecar_name`, `version_tag` |
| `energy_history` | `energy_history_inlets`, `energy_history_js` |
| `envelope_display` | `envelope_display_js` |
| `envelope_editor` | `envelope_editor_js` |
| `eq_band_column` | `eq_band_column_js` |
| `eq_curve` | `eq_curve_js` |
| `exciter_curve` | `exciter_curve_js` |
| `fft_analyzer` | `fft_analyzer_dsp`, `fft_analyzer_kernel` |
| `filter_curve` | `filter_curve_js` |
| `glass_panel_bg` | `ds_helpers_js`, `glass_panel_bg_js` |
| `goniometer_graticule` | `goniometer_graticule_js` |
| `grain_cloud` | `grain_cloud_js` |
| `grain_display` | `grain_display_js` |
| `graph_core` | `graph_core_js` |
| `grid_sequencer_display` | `grid_sequencer_display_js` |
| `icon_overlay` | `icon_overlay_js` |
| `integrated_lufs` | `integrated_lufs_js` |
| `interaction_core` | `plot_geometry_long_js`, `plot_geometry_short_js` |
| `level_history` | `level_history_js` |
| `level_meter` | `level_meter_js` |
| `lfo_display` | `lfo_display_js` |
| `linear_phase_eq_display` | `linear_phase_eq_display_js` |
| `live_theme` | `live_brand_dim`, `live_colors_bus`, `live_theme_receiver`, `live_theme_state_dim` |
| `lom_mapper` | `lom_mapper_js` |
| `loop_filter_curve` | `loop_filter_curve_js` |
| `painters` | `lcd_dial_painter_js`, `lcd_panel_painter_js`, `lcd_slider_painter_js` |
| `peaking_eq_display` | `peaking_eq_display_js` |
| `performance_canvas` | `performance_canvas_js` |
| `piano_roll` | `piano_roll_js` |
| `resonance_bank_display` | `resonance_bank_display_js` |
| `seed_history` | `seed_history_js` |
| `settings_bar` | `settings_bar_js` |
| `shape_icon` | `shape_icon_js` |
| `sidechain_display` | `follower_cluster_js`, `sidechain_display_js` |
| `slice_overview` | `slice_overview_js` |
| `slice_pattern_display` | `slice_pattern_display_js` |
| `sonogram_overlay` | `sonogram_overlay_js` |
| `spectral_display` | `spectral_display_js` |
| `spectral_vocoder_display` | `spectral_vocoder_display_js` |
| `spectrum_analyzer` | `spectrum_analyzer_dsp`, `spectrum_analyzer_js` |
| `step_bars` | `step_bars_js` |
| `step_grid_display` | `step_grid_display_js` |
| `transfer_curve` | `transfer_curve_js` |
| `transient_history` | `transient_history_js` |
| `ui_curve_node` | `drag_curve_node_js` |
| `ui_icons` | `ui_icons_js` |
| `ui_interaction` | `draggable_node_js`, `edit_overlay_js`, `modifier_drag_js`, `tooltip_js`, `ui_interaction_js` |
| `ui_kit` | `custom_cycle_js`, `custom_glyph_selector_js`, `custom_knob_js`, `custom_readout_js`, `custom_segment_js`, `custom_slider_js`, `custom_stepper_js`, `custom_toggle_js`, `panel_bg_js` |
| `ui_motion` | `glow_js`, `tween_js`, `ui_motion_js` |
| `ui_xy_pad` | `custom_xy_pad_js` |
| `unit_format` | `unitstyle_readout_js` |
| `value_readout` | `value_readout_js` |
| `velocity_curve_display` | `velocity_curve_display_js` |
| `waveform_display` | `waveform_display_dsp`, `waveform_display_js` |
| `waveshape_curve` | `waveshape_curve_js` |
| `wavetable_display` | `wavetable_display_js` |
| `wavetable_editor` | `wavetable_editor_js` |
| `xy_pad` | `xy_pad_js` |
