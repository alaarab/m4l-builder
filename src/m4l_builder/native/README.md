# Native modal building blocks

This package builds and freezes source-addressed Max externals. The modal engine
and analyzer are standalone C++17; only the adapter includes the Max SDK. Product
UI, presets and interaction belong in the product repository.

```python
from m4l_builder.native.external import NativeInstrument, modal_external

device = NativeInstrument("My Instrument", width=400, height=168)
external_name = device.add_external(modal_external())
device.add_newobj("engine", external_name, numinlets=2, numoutlets=3,
                 outlettype=["signal", "signal", ""])
# Connect plugin~ / MIDI, plugout~, native parameters and model state here.
device.build("/explicit/output/My Instrument.amxd", freeze=True)
```

Creating a factory or registering the external does not compile anything. An
unfrozen build copies the complete `.mxo`; a frozen build embeds its signed
bundle, executable and plist using Max's native freeze representation. Source
manifests are embedded separately for fingerprints and inspection.

Compilation currently targets universal macOS 11+ (arm64 and x86_64). Install
Apple's command-line tools and point `MAX_SDK_ROOT` to a checkout of
`https://github.com/Cycling74/max-sdk-base` at commit
`c03a2922a2a8ff149165a1e2ea134e9321d6e202`. The default SDK path is
`~/.cache/m4l-builder/max-sdk-base`; compilation does not download it. Override
the compiled cache with `M4L_NATIVE_CACHE`. SDK revision, source, builder, compiler
and header identity invalidate the appropriate caches. A file lock prevents
concurrent builds from racing to publish the same bundle.

## Engine

`modal/modal_core.hpp` exposes `m4l::modal::Model` and `Engine`:

```cpp
Engine engine;
engine.prepare(48000);
Model body;
body.count = 1;
body.anchor = 261.625565;
body.mode[0] = {1, .5, 3, 0, 0}; // ratio, gain, T60 seconds, pan, phase radians
engine.setModel(0, body);
engine.setModel(1, body);
engine.set(Coupling, .2);
engine.note(60, 100, 1);
double left, right;
engine.process(0, 0, left, right);
```

There are eight voices and up to 24 modes in each of two bodies. Models validate
all slots; unused slots have zero gain. Set models and controls on the audio
thread, or marshal them through the adapter. `setModel` preserves ringing energy
while its coefficients approach the destination. `prepare`/`clear` clear voices
without deleting the models. `midi(byte)` parses running status and channel
expression; `note(pitch, 0, channel)` releases the oldest held matching note.

The coupling operator is orthogonal in both quadratures. It exchanges modal
state energy without generating it. Bow, breath, strikes and input excitation
supply energy explicitly. Output includes DC rejection and a linked sample-peak
guard. This is a designed modal instrument, not a calibrated geometry solver or
a true-peak mastering limiter.

## Analysis

`modal/modal_analysis.hpp` exposes
`analyze(interleaved_float_vector, channels, sample_rate)`. Run it off the audio
thread. The result contains `ok`, a validated `model`, and a user-facing `message`.
It estimates modal peaks, decay, relative gains, stereo pan/phase, source rise and
noise. The lowest selected resonance becomes the editable anchor; it need not be
a musical fundamental. Confidence is a heuristic, not a calibrated probability.

Inputs must be finite, mono or stereo, 22.05–192 kHz, and at least 80 ms. Analysis
uses at most eight seconds. Unusable audio fails transactionally; callers retain
their last model. Fast-decaying modes use a short-window candidate analysis in
addition to the longer frequency analysis.

## Max adapter protocol

The external has two signal inputs, two signal outputs, and one message output.
The first inlet also accepts raw MIDI bytes and the following messages:

| Message | Arguments |
| --- | --- |
| `param` | Index, value in engine units |
| `model` | Slot, anchor, attack, noise, confidence, count, then 24 groups of five mode values |
| `note` | Pitch, velocity (zero releases), channel 1–16 |
| `mpe` | 0/1; members bend ±48 semitones, master ±2 |
| `capture` | Slot 0/1, start 1 or stop 0 |
| `analyze` | `buffer~` name, destination slot |
| `panic` | Clear voices |

Parameter indices: Morph 0, Coupling 1, Hardness 2, Position 3, Decay 4, Damping 5,
Bow 6, Breath 7, Texture 8, Width 9, Balance 10, Gain 11, Tune 12, Release 13,
Input 14, Pressure 15. Normalized controls use 0–1; Decay is a multiplier, Gain is
dB, Tune is semitones and Release is seconds. See `minima`, `maxima`, `defaults`
in the header for the precise contract.

Output messages are `model` with the same model payload, `status slot message`,
and `meter peak voices energyA energyB inputPeak captureSeconds`. Meter messages
are delivered on a 50 ms clock. Audio processing avoids allocation, mutexes,
logging and Max object calls. Queued control work is bounded per vector; queue
overflow requests a voice clear. Analysis runs on a joined worker thread.

## State and verification

The product controller should store models, originals and selection in a native
blob parameter. For a `pattr` newobj, put `parameter_enable: 1` in
`saved_object_attributes` so Max enables the parameter before applying its saved
metadata. Putting only `@parameter_enable 1` in the object text produced readable
state that disappeared on actual Live duplication. Foundry's controller uses
`getvalueof`, `setvalueof` and `notifyclients` with a versioned JSON payload.

`tests/native/modal_spec.cpp` verifies independent acoustic fixtures, passivity,
finite bounded output, expression, sustain, voice stealing and audio allocation.
`tests/test_native_modal.py` covers factory purity, native packaging, fingerprints
and concurrent builds. Live recordings and physical UI checks belong to each
product's acceptance process; a passing standalone test does not establish them.
