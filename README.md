# m4l-builder

[![PyPI version](https://img.shields.io/pypi/v/m4l-builder.svg)](https://pypi.org/project/m4l-builder/)
[![Tests](https://img.shields.io/github/actions/workflow/status/alaarab/m4l-builder/tests.yml?label=tests)](https://github.com/alaarab/m4l-builder)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://pypi.org/project/m4l-builder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Build Max for Live devices in Python. Write scripts, emit `.amxd` files straight to your Ableton User Library. No Max GUI required. Everything is version-controllable, scriptable, and reproducible. Zero runtime dependencies -- pure stdlib.

## Install

```bash
pip install m4l-builder
```

## Quick start

```python
from m4l_builder import AudioEffect, WARM, device_output_path

device = AudioEffect("My Gain", width=150, height=110, theme=WARM)

device.add_panel("bg", [0, 0, 150, 110])
device.add_dial("gain", "Gain", [10, 6, 50, 90],
                min_val=-70.0, max_val=6.0, initial=0.0,
                unitstyle=4, annotation_name="Gain")

device.add_newobj("mul_l", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
device.add_newobj("mul_r", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1, outlettype=[""])
device.add_newobj("pk", "pack f 20", numinlets=2, numoutlets=1, outlettype=[""])
device.add_newobj("ln", "line~", numinlets=2, numoutlets=2, outlettype=["signal", "bang"])

device.add_line("obj-plugin", 0, "mul_l", 0)   # stereo in
device.add_line("obj-plugin", 1, "mul_r", 0)
device.add_line("mul_l", 0, "obj-plugout", 0)   # stereo out
device.add_line("mul_r", 0, "obj-plugout", 1)
device.add_line("gain", 0, "db2a", 0)           # dial -> dbtoa -> smooth -> gain
device.add_line("db2a", 0, "pk", 0)
device.add_line("pk", 0, "ln", 0)
device.add_line("ln", 0, "mul_l", 1)
device.add_line("ln", 0, "mul_r", 1)

device.build(device_output_path("My Gain"))
```

Restart Ableton (or refresh the browser) and your device shows up in the User Library.

## Key concepts

### Device types

Three device types, matching what Ableton expects:

```python
from m4l_builder import AudioEffect, Instrument, MidiEffect

fx    = AudioEffect("FX", 300, 170)      # auto-adds plugin~/plugout~
synth = Instrument("Synth", 400, 200)    # no auto I/O
midi  = MidiEffect("MIDI FX", 200, 100)  # MIDI only
```

`AudioEffect` auto-wires stereo `plugin~` / `plugout~` objects (IDs `obj-plugin`, `obj-plugout`). Instruments and MIDI effects leave I/O to you.

### DSP blocks

All DSP functions return `(boxes, lines)` tuples. Compose them with `add_dsp`:

```python
from m4l_builder import gain_stage, highpass_filter

boxes, lines = gain_stage("gain")
device.add_dsp(boxes, lines)
```

**Filters**: highpass, lowpass, bandpass, notch, onepole, shelves, tilt EQ, 3-band crossover, peaking EQ, allpass
**Dynamics**: compressor, limiter, envelope follower, gate/expander, sidechain detect, multiband compressor
**Delay/Reverb**: delay line, feedback delay, reverb network, FDN reverb, convolver
**Modulation**: LFO (4 waveforms), tremolo, transport LFO, morphing LFO
**MIDI**: notein/out, ctlin/out, velocity curve, transpose, arpeggiator, chord, pitch quantize, midi learn
**Synthesis**: wavetable osc, noise, oscillator bank, ADSR, poly voices, grain cloud
**Spectral**: spectral gate, crossover, vocoder, phase vocoder
**Routing**: selector, send/receive (signal + message), matrix mixer, sidechain routing
**Utility**: param smooth, tempo sync, sample and hold, bitcrusher, coll/dict/pattr storage

90+ blocks total. See [docs/api.md](docs/api.md) for the full list with signatures.

### Engines (jsui visualizations)

JavaScript generators for Max's jsui object. Each returns an ES5 string for mgraphics/Cairo rendering:

```python
from m4l_builder.engines import filter_curve_js

device.add_jsui("display", [10, 30, 200, 80],
                js_code=filter_curve_js(), numinlets=3)
```

18 generators available: filter curves, EQ, envelopes, spectrum, waveforms, XY pad, piano roll, step grids, grain clouds, vocoder bands, and more.

### Themes

Seven built-in color themes. Pass to the device constructor and all UI elements inherit colors automatically:

```python
from m4l_builder import AudioEffect, MIDNIGHT, WARM, COOL, LIGHT, FOREST, VIOLET, SOLAR

device = AudioEffect("FX", 300, 170, theme=MIDNIGHT)
```

Build a theme from just an accent color:

```python
from m4l_builder import Theme
my_theme = Theme.from_accent([0.8, 0.3, 0.1, 1.0])
```

### Recipes

Pre-wired DSP combos for common patterns. They add objects to a device and return IDs for further wiring:

```python
from m4l_builder import gain_controlled_stage, dry_wet_stage

ids = gain_controlled_stage(device, "out", [10, 10, 50, 70])
# ids["gain"] is the *~ you wire into your signal chain
```

Available: `gain_controlled_stage`, `dry_wet_stage`, `tempo_synced_delay`, `midi_note_gate`.

### Layout helpers

Automatic positioning with `Row`, `Column`, and `Grid` context managers:

```python
with device.row(10, 10, spacing=8, height=70) as r:
    r.add_dial("d1", "Param1", width=50)
    r.add_dial("d2", "Param2", width=50)
    r.add_dial("d3", "Param3", width=50)
```

### Subpatchers

Nested patchers for organizing signal chains:

```python
from m4l_builder import Subpatcher

sub = Subpatcher("processor")
sub.add_newobj("in", "inlet~", numinlets=1, numoutlets=1)
sub.add_newobj("out", "outlet~", numinlets=1, numoutlets=1)
sub.add_line("in", 0, "out", 0)
device.add_subpatcher(sub, "proc_box", [30, 100, 80, 20])
```

### Round-trip editing with from_amxd

Read an existing `.amxd` back into a Device, modify it, write it out:

```python
device = AudioEffect.from_amxd("path/to/effect.amxd")
device.add_dial("new_knob", "NewParam", [10, 10, 50, 70])
device.build("path/to/modified.amxd")
```

## Examples

40+ examples in `examples/`. A few highlights:

| File | What it builds |
|------|---------------|
| `simple_gain.py` | Minimal starter, single gain dial |
| `stereo_delay.py` | L/R delay with feedback saturation |
| `simple_compressor.py` | Threshold, ratio, attack/release |
| `parametric_eq.py` | JSUI custom EQ curve display |
| `poly_synth.py` | Polyphonic synth with wavetable |
| `midi_arpeggiator.py` | MIDI arpeggiator |
| `from_amxd_demo.py` | Round-trip: build, read back, modify |

```bash
uv run python examples/simple_gain.py           # run one
for f in examples/*.py; do uv run python "$f"; done  # build all
```

## Development

```bash
git clone https://github.com/alaarab/m4l-builder.git
cd m4l-builder
uv pip install -e .

# Tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=m4l_builder --cov-report=term-missing
```

## API reference

Full API docs at [docs/api.md](docs/api.md).

## License

MIT
