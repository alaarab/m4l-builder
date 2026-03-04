# API Reference

## device.py

Core device classes. All devices share the same builder interface.

### Device types

`AudioEffect(name, width, height, theme=None)` -- Audio effect with auto plugin~/plugout~
`Instrument(name, width, height, theme=None)` -- Instrument (no auto I/O)
`MidiEffect(name, width, height, theme=None)` -- MIDI effect (no auto I/O)

### Builder methods

`device.add_box(box_dict)` -- Add a raw box dict, returns object ID
`device.add_line(source_id, source_outlet, dest_id, dest_inlet)` -- Connect two objects
`device.add_dsp(boxes, lines)` -- Add all boxes and lines from a DSP block tuple
`device.add_newobj(id, text, *, numinlets, numoutlets, **kwargs)` -- Add a Max object by text
`device.add_subpatcher(subpatcher, id, rect, *, numinlets=1, numoutlets=1, outlettype=None)` -- Embed a Subpatcher

### UI methods

All place objects in presentation mode at `rect=[x, y, w, h]`. Any Max attribute can be passed as `**kwargs`.

`device.add_panel(id, rect, **kwargs)` -- Background panel
`device.add_dial(id, varname, rect, **kwargs)` -- live.dial rotary control
`device.add_slider(id, varname, rect, **kwargs)` -- live.slider
`device.add_toggle(id, varname, rect, **kwargs)` -- live.toggle on/off
`device.add_button(id, varname, rect, **kwargs)` -- live.button momentary
`device.add_tab(id, varname, rect, options, **kwargs)` -- live.tab selector
`device.add_menu(id, varname, rect, options, **kwargs)` -- live.menu dropdown
`device.add_number_box(id, varname, rect, **kwargs)` -- live.numbox
`device.add_comment(id, rect, text, **kwargs)` -- Static text label
`device.add_scope(id, rect, **kwargs)` -- live.scope~ oscilloscope
`device.add_meter(id, rect, **kwargs)` -- live.meter~ level meter
`device.add_live_text(id, varname, rect, **kwargs)` -- Clickable text toggle
`device.add_fpic(id, rect, **kwargs)` -- Image display
`device.add_live_gain(id, varname, rect, **kwargs)` -- Gain fader with metering
`device.add_multislider(id, rect, **kwargs)` -- Multi-value slider array
`device.add_jsui(id, rect, *, js_code, js_filename=None, numinlets=1, numoutlets=0, **kwargs)` -- Custom JS canvas
`device.add_adsrui(id, rect, **kwargs)` -- ADSR envelope editor
`device.add_live_drop(id, rect, **kwargs)` -- Drag-and-drop file target
`device.add_bpatcher(id, rect, patcher_name, **kwargs)` -- Embedded sub-patcher
`device.add_swatch(id, rect, **kwargs)` -- Color swatch
`device.add_textedit(id, rect, **kwargs)` -- Editable text field
`device.add_live_step(id, rect, **kwargs)` -- Step sequencer
`device.add_live_grid(id, rect, **kwargs)` -- Toggleable cell grid
`device.add_live_line(id, rect, **kwargs)` -- Divider line
`device.add_live_arrows(id, rect, **kwargs)` -- Arrow navigation buttons
`device.add_rslider(id, rect, **kwargs)` -- Range slider (two handles)
`device.add_kslider(id, rect, **kwargs)` -- Piano keyboard
`device.add_textbutton(id, rect, text="Button", **kwargs)` -- Text button (no parameter)
`device.add_umenu(id, rect, **kwargs)` -- Dropdown (no parameter)
`device.add_radiogroup(id, rect, **kwargs)` -- Radio button group
`device.add_nodes(id, rect, **kwargs)` -- XY node editor
`device.add_matrixctrl(id, rect, **kwargs)` -- Matrix grid control
`device.add_ubutton(id, rect, **kwargs)` -- Invisible click zone
`device.add_nslider(id, rect, **kwargs)` -- Staff notation display

### Wiring and validation

`device.wire_chain(obj_ids, outlet=0, inlet=0)` -- Connect objects end-to-end in a chain
`device.validate()` -- Check for duplicate IDs, broken connections, orphan boxes. Returns list of warning strings.
`device.assign_parameter_bank(varname, bank, position)` -- Map a parameter to Push bank layout

### Serialization

`device.to_json(indent=2)` -- Serialize patcher to JSON string
`device.to_patcher()` -- Build the full patcher dict
`device.to_bytes()` -- Build .amxd binary in memory
`device.build(output_path)` -- Write .amxd file (and any JS files). Returns bytes written.

### Round-trip

`Device.from_amxd(path)` -- Class method. Parse a .amxd file into a Device (AudioEffect, Instrument, or MidiEffect based on type code). Works on `AudioEffect.from_amxd()` too.

### Layout shortcuts

`device.row(x, y, *, spacing=8, height=None, width=None)` -- Returns a Row context manager
`device.column(x, y, *, spacing=4, width=None, height=None)` -- Returns a Column context manager
`device.grid(x, y, *, cols, col_width, row_height, spacing_x=4, spacing_y=4)` -- Returns a Grid context manager

---

## dsp.py

All functions return `(boxes, lines)` tuples unless noted. Add with `device.add_dsp(boxes, lines)`.

### I/O

`stereo_io(plugin_id="obj-plugin", plugout_id="obj-plugout")` -- plugin~/plugout~ pair

### Gain and mixing

`gain_stage(id_prefix)` -- Stereo *~ pair for gain control
`dry_wet_mix(id_prefix)` -- Dry/wet crossfade with wet/dry *~ multipliers
`signal_divide(id_prefix)` -- Stereo signal splitter
`auto_gain(id_prefix)` -- Automatic gain compensation

### Filters

`highpass_filter(id_prefix)` -- Stereo SVF highpass
`lowpass_filter(id_prefix)` -- Stereo SVF lowpass
`bandpass_filter(id_prefix)` -- Stereo SVF bandpass
`notch_filter(id_prefix)` -- Stereo SVF notch
`onepole_filter(id_prefix, freq=1000.)` -- Simple onepole~ pair
`highshelf_filter(id_prefix, freq=3000., gain_db=0.)` -- Biquad high shelf
`lowshelf_filter(id_prefix, freq=300., gain_db=0.)` -- Biquad low shelf
`tilt_eq(id_prefix, freq=1000.)` -- Tilt EQ (low shelf + high shelf)
`crossover_3band(id_prefix)` -- 3-band frequency crossover
`peaking_eq(id_prefix, *, freq=1000, gain_db=0, q=1)` -- Parametric peaking EQ band
`allpass_filter(id_prefix, *, freq=1000, q=0.707)` -- Stereo allpass

### Saturation

`saturation(id_prefix, mode)` -- Stereo saturation. Modes: "tanh", "overdrive", "clip", "degrade"

### Dynamics

`compressor(id_prefix)` -- Stereo compressor with threshold/ratio/attack/release
`limiter(id_prefix)` -- Brick-wall limiter
`envelope_follower(id_prefix, attack_ms=10, release_ms=100)` -- Stereo envelope follower
`lookahead_envelope_follower(id_prefix, lookahead_ms=5)` -- Envelope follower with lookahead delay
`gate_expander(id_prefix)` -- Gate/expander
`sidechain_detect(id_prefix)` -- Sidechain detection chain
`multiband_compressor(id_prefix)` -- Multiband compressor (uses crossover_3band)

### Delay

`delay_line(id_prefix, max_delay_ms=5000)` -- tapin~/tapout~ pair
`feedback_delay(id_prefix, max_delay_ms=5000)` -- Delay with feedback loop and saturation

### Reverb

`reverb_network(id_prefix, num_combs=4, num_allpasses=2)` -- Schroeder-style reverb
`fdn_reverb(id_prefix, num_delays=8)` -- Feedback delay network reverb
`convolver(id_prefix, ir_buffer="ir_buf")` -- IR convolution via buffir~

### Modulation

`lfo(id_prefix, waveform="sine")` -- LFO with cycle~ or phasor~. Waveforms: "sine", "saw", "square", "triangle"
`tremolo(id_prefix, waveform="sine")` -- LFO-modulated amplitude
`transport_lfo(id_prefix, division="1/4", waveform="sine")` -- Tempo-synced LFO
`morphing_lfo(id_prefix)` -- LFO with morphable waveform shape

### Stereo

`ms_encode_decode(id_prefix)` -- Mid/side encoder and decoder pair
`dc_block(id_prefix)` -- Stereo DC offset removal (biquad~)

### Routing

`selector(id_prefix, num_inputs, initial=1)` -- selector~ for switching between signal sources
`send_signal(id_prefix, name)` -- send~ named signal bus
`receive_signal(id_prefix, name)` -- receive~ named signal bus
`send_msg(id_prefix, name)` -- send named message bus
`receive_msg(id_prefix, name)` -- receive named message bus
`sidechain_routing(id_prefix)` -- Sidechain signal routing
`xfade_matrix(id_prefix, sources=4)` -- Crossfade matrix mixer
`matrix_mixer(id_prefix, inputs=4, outputs=4)` -- NxN matrix mixer

### MIDI

`notein(id_prefix, channel=0)`, `noteout(id_prefix, channel=0)` -- MIDI note I/O (0 = omni)
`ctlin(id_prefix, cc=None, channel=0)`, `ctlout(id_prefix, cc=1, channel=1)` -- MIDI CC I/O
`velocity_curve(id_prefix, curve="linear")` -- Velocity mapping. Curves: "linear", "exponential", "logarithmic", "scurve"
`transpose(id_prefix, semitones=0)` -- MIDI transpose
`midi_thru(id_prefix)` -- Pass-through MIDI pipe
`arpeggiator(id_prefix, mode="up")` -- Arpeggiator. Modes: "up", "down", "updown", "random"
`chord(id_prefix, intervals=None)` -- Chord generator from intervals list
`pitch_quantize(id_prefix, scale="chromatic")` -- Quantize pitch to scale
`pitchbend_in(id_prefix, semitones=2)`, `modwheel_in(id_prefix)`, `aftertouch_in(id_prefix)` -- Performance input
`midi_learn_chain(id_prefix, param_name)` -- MIDI learn for a parameter
`midi_channel_filter(id_prefix, channel=1)` -- Filter MIDI by channel
`program_change_in(id_prefix, channel=0)`, `bank_select_in(id_prefix, channel=0)` -- Program/bank select
`midi_clock_out(id_prefix)`, `midi_clock_in(id_prefix)` -- MIDI clock I/O
`note_expression_decode(id_prefix)` -- MPE note expression

### Synthesis

`wavetable_osc(id_prefix)` -- Wavetable oscillator with buffer~
`buffer_load(id_prefix, buffer_name, size=1024)` -- Buffer allocation and loading
`noise_source(id_prefix, color="white")` -- Noise generator. Colors: "white", "pink"
`analog_oscillator_bank(id_prefix, num_oscs=4)` -- Multi-oscillator bank
`adsr_envelope(id_prefix, *, attack_ms=10, decay_ms=100, sustain=0.7, release_ms=300)` -- ADSR envelope generator
`poly_voices(id_prefix, num_voices=4)` -- Polyphonic voice allocation
`grain_cloud(id_prefix, buffer_name, num_grains=8)` -- Granular synthesis cloud
`comb_resonator(id_prefix, num_voices=4)` -- Tuned comb filter bank

### Spectral

`spectral_gate(id_prefix, threshold=0.01)` -- FFT spectral gate
`spectral_crossover(id_prefix, bands=4)` -- FFT spectral crossover
`vocoder(id_prefix, num_bands=16)` -- Channel vocoder
`stft_phase_vocoder(id_prefix)` -- STFT phase vocoder
`spectrum_band_extract(id_prefix, low_hz=200, high_hz=4000)` -- Extract frequency band

Subpatcher variants (return box dict, not tuple): `spectral_gate_subpatcher`, `spectral_crossover_subpatcher`, `phase_vocoder_subpatcher`

### MC (multichannel)

`mc_expand(id_prefix, channels=8)`, `mc_collapse(id_prefix, channels=8)` -- Expand/collapse MC signals

### Utility

`param_smooth(id_prefix, smooth_ms=20)` -- Parameter smoothing via pack/line~
`tempo_sync(id_prefix, division=1.0)` -- Transport-synced timing
`loadbang(id_prefix)` -- loadbang object
`scale_range(id_prefix, in_lo=0., in_hi=1., out_lo=0., out_hi=1.)` -- Value scaling
`groove_player(id_prefix, buf_name)` -- groove~ buffer player
`sample_and_hold(id_prefix)`, `sample_and_hold_triggered(id_prefix)` -- Sample and hold (basic / with trigger)
`bitcrusher(id_prefix, bits=8)` -- Bit depth reduction
`coll_store(id_prefix, name)`, `dict_store(id_prefix, name)`, `pattr_system(id_prefix)` -- Data storage (coll / dict / pattrstorage)
`random_walk(id_prefix, step_size=0.01)` -- Random walk generator
`cv_recorder(id_prefix, buffer_size=4410)`, `cv_smooth_lag(id_prefix, lag_ms=50)` -- CV record and smooth
`quantize_time(id_prefix, division="1/16")` -- Time quantization
`macromap(id_prefix, param_name, macro_num=1)`, `macro_modulation_matrix(id_prefix, sources=4, targets=8)` -- Macro mapping
`lfsr_generator(id_prefix, poly_order=8)` -- Linear feedback shift register
`live_remote(id_prefix)`, `live_param_signal(id_prefix)` -- Live API remote control and parameter-to-signal

---

## recipes.py

Higher-level combos that wire multiple DSP blocks and UI elements together. Each takes a device instance and returns a dict of IDs.

`gain_controlled_stage(device, id_prefix, dial_rect, x=30, y=30)` -- Dial -> dbtoa -> *~ gain cell. Returns `{"dial", "gain"}`.
`dry_wet_stage(device, id_prefix, dial_rect, x=30, y=30)` -- 0-100% crossfade. Returns `{"dial", "wet_gain", "dry_gain"}`.
`tempo_synced_delay(device, id_prefix, time_dial_rect, feedback_dial_rect, x=30, y=30)` -- Time + feedback dials with tapin~/tapout~. Returns `{"time_dial", "feedback_dial", "tapin", "tapout"}`.
`midi_note_gate(device, id_prefix, x=30, y=30)` -- notein -> stripnote -> kslider. Returns `{"notein", "pitch", "velocity"}`.

---

## engines/

JavaScript generators for Max's jsui object. Each returns an ES5 string. Max uses SpiderMonkey, so no ES6+ features.

### Visualization generators

`filter_curve_js()` -- Single filter frequency response curve
`eq_curve_js()` -- Multi-band parametric EQ with draggable nodes
`envelope_display_js()` -- ADSR envelope shape visualization
`spectrum_analyzer_js()` -- Real-time frequency spectrum
`waveform_display_js()` -- Waveform / oscilloscope display
`xy_pad_js()` -- 2D XY control pad
`piano_roll_js()` -- Piano roll note display
`velocity_curve_display_js()` -- Velocity mapping curve
`wavetable_display_js()` -- Wavetable waveform viewer
`resonance_bank_display_js()` -- Resonance frequency bank
`sidechain_display_js()` -- Sidechain gain reduction
`spectral_display_js()` -- Spectral analysis view
`peaking_eq_display_js()` -- Peaking EQ band curve
`step_grid_display_js()` -- Step sequencer grid
`grain_display_js()` -- Granular cloud visualization
`grid_sequencer_display_js()` -- Grid-based sequencer
`wavetable_editor_js()` -- Wavetable drawing editor
`spectral_vocoder_display_js()` -- Vocoder band visualization

Each engine module also exports `*_INLETS` and `*_OUTLETS` constants (e.g. `XY_PAD_INLETS`, `XY_PAD_OUTLETS`) for setting up jsui inlet/outlet counts.

---

## theme.py

`Theme(bg, surface, section, text, text_dim, accent, fontname="Ableton Sans Medium", ...)` -- Dataclass. RGBA lists `[r, g, b, a]` with 0.0-1.0 values. Derived colors (dial, needle, tab, meter, scope) auto-compute from base colors in `__post_init__`.

### Factory methods

`Theme.from_accent(accent, bg=None, surface=None)` -- Build a dark theme around an accent color
`Theme.custom(**overrides)` -- Start from MIDNIGHT defaults and override fields

### Presets

`MIDNIGHT` -- Teal accent, dark neutral background
`WARM` -- Orange accent, warm dark background
`COOL` -- Blue accent, cool dark background
`LIGHT` -- Blue accent, light background
`FOREST` -- Green accent, green-tinted dark background
`VIOLET` -- Purple accent, violet-tinted dark background
`SOLAR` -- Gold accent, warm dark background

### Helper

`theme.meter_kwargs()` -- Returns dict of meter color kwargs for manual use

---

## layout.py

Context managers for automatic UI positioning.

`Row(device, x, y, *, spacing=8, height=None, width=None)` -- Horizontal layout. Cursor moves left to right. Supports all `add_*` methods with automatic rect calculation.
`Column(device, x, y, *, spacing=4, width=None, height=None)` -- Vertical layout. Cursor moves top to bottom.
`Grid(device, x, y, *, cols, col_width, row_height, spacing_x=4, spacing_y=4)` -- Grid layout. Fills left to right, wraps at `cols`.

All three support `used_width` and `used_height` properties. Row supports nested `.column()`, Column supports nested `.row()`.

Access via device shortcuts: `device.row(...)`, `device.column(...)`, `device.grid(...)`.

---

## live_api.py

Max for Live Live API integration.

`live_object_path(id_prefix, path="live_set")` -- live.path + live.object pair for getting/setting properties. Returns `(boxes, lines)`.
`live_observer(id_prefix, path="live_set", prop="tempo")` -- Watch a Live property and output on change. Returns `(boxes, lines)`.
`live_set_control(id_prefix, path="live_set", prop="tempo")` -- Send set messages to a Live property. Returns `(boxes, lines)`.

---

## presets.py

Preset management for Max devices.

`preset_manager(id_prefix, num_presets=8)` -- preset object + umenu for slot selection. Returns `(boxes, lines)`.
`add_preset_buttons(device, x, y, num_presets=8)` -- Adds save/load/prev/next buttons wired to a preset object. Returns list of box IDs.

---

## subpatcher.py

`Subpatcher(name="subpatch")` -- Nested patcher container. Same interface as Device for adding objects:

`sub.add_box(box_dict)` -- Add raw box dict
`sub.add_line(source_id, source_outlet, dest_id, dest_inlet)` -- Connect objects
`sub.add_dsp(boxes, lines)` -- Add DSP block
`sub.add_newobj(id, text, *, numinlets, numoutlets, **kwargs)` -- Add Max object
`sub.to_patcher_dict()` -- Return inner patcher dict
`sub.to_box(id, rect, *, numinlets=1, numoutlets=1, outlettype=None)` -- Return box dict for embedding in a device

---

## paths.py

`user_library()` -- Path to Ableton User Library. Checks `M4L_USER_LIBRARY` env var, then auto-detects (macOS, Windows, WSL).
`device_output_path(name, device_type="audio_effect")` -- Full .amxd output path. Creates parent dirs automatically.

---

## objects.py

`newobj(id, text, *, numinlets, numoutlets, **kwargs)` -- Create a box dict for any Max object
`patchline(source_id, source_outlet, dest_id, dest_inlet)` -- Create a patchline dict

---

## constants.py

Unit styles for live.dial/live.slider: `UNITSTYLE_INT`, `UNITSTYLE_FLOAT`, `UNITSTYLE_TIME`, `UNITSTYLE_HZ`, `UNITSTYLE_DB`, `UNITSTYLE_PERCENT`, `UNITSTYLE_PAN`, `UNITSTYLE_SEMITONE`, `UNITSTYLE_MIDI`, `UNITSTYLE_CUSTOM`, `UNITSTYLE_NATIVE`

Type codes: `AUDIO_EFFECT`, `INSTRUMENT`, `MIDI_EFFECT`, `DEVICE_TYPE_CODES`, `DEFAULT_APPVERSION`
