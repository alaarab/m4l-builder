# Getting started

Build your first Max for Live device in Python. No Max GUI required — you write
a script, it emits an `.amxd` you can load straight into Ableton.

## Install

```bash
uv sync --group dev          # for development of this repo
# or, to use the package elsewhere:
pip install m4l-builder
```

## The shape of a device

Every device follows the same three steps:

1. **Create** a device of one of the three types.
2. **Add** UI widgets, DSP objects, and the wiring between them.
3. **Build** it to an `.amxd` file.

```python
from m4l_builder import AudioEffect, Instrument, MidiEffect

fx    = AudioEffect("FX", 300, 170)      # auto-adds stereo plugin~/plugout~
synth = Instrument("Synth", 400, 200)    # no auto I/O
midi  = MidiEffect("MIDI FX", 200, 100)  # MIDI only
```

## Your first device: a gain effect

```python
from m4l_builder import AudioEffect, WARM, device_output_path

device = AudioEffect("My Gain", width=150, height=110, theme=WARM)

# A background panel and a gain dial (presentation-mode rect [x, y, w, h]).
device.add_panel("bg", [0, 0, 150, 110])
device.add_dial("gain", "Gain", [10, 6, 50, 90],
                min_val=-70.0, max_val=6.0, initial=0.0,
                unitstyle=4, annotation_name="Gain")

# Raw Max objects. AudioEffect already added `obj-plugin` / `obj-plugout`.
device.add_newobj("mul_l", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
device.add_newobj("mul_r", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1, outlettype=[""])

# Wire it up: dial -> dbtoa -> gain cells, audio in -> gain -> audio out.
device.add_line("gain", 0, "db2a", 0)
device.add_line("db2a", 0, "mul_l", 1)
device.add_line("db2a", 0, "mul_r", 1)
device.add_line("obj-plugin", 0, "mul_l", 0)
device.add_line("obj-plugin", 1, "mul_r", 0)
device.add_line("mul_l", 0, "obj-plugout", 0)
device.add_line("mul_r", 0, "obj-plugout", 1)

device.build(device_output_path("My Gain"))
```

`device_output_path("My Gain")` resolves to your Ableton User Library, so the
device shows up after you refresh Live's browser. The complete, runnable version
is [`examples/01_gain_audio_effect.py`](../examples/01_gain_audio_effect.py).

## Skip the boilerplate with recipes

Recipes are pre-wired sections you drop onto a device. For example, a complete
generative MIDI note generator is a few lines:

```python
from m4l_builder import MidiEffect, COOL
from m4l_builder.recipes import generative_midi_stage

device = MidiEffect("Sparkle", 200, 140, theme=COOL)
device.add_panel("bg", [0, 0, 200, 140])
generative_midi_stage(device, "gen",
                      rate_rect=[24, 40, 56, 56],
                      density_rect=[110, 40, 56, 56],
                      low=48, high=72, scale="minor")
device.build(device_output_path("Sparkle"))
```

DSP blocks return `(boxes, lines)` tuples you compose with `add_dsp`:

```python
from m4l_builder import gain_stage
boxes, lines = gain_stage("gain")
device.add_dsp(boxes, lines)
```

## Where to go next

- **[examples/](../examples/)** — four runnable devices you can build today,
  including a Live 12 MIDI Tool.
- **[catalog.md](catalog.md)** — a browsable index of every DSP block, UI
  widget, recipe, theme, and engine.
- **[midi_tools.md](midi_tools.md)** — build Live 12 MIDI Generators and
  Transformations.
- **[api.md](api.md)** — the detailed API reference.
- **[reverse_engineering.md](reverse_engineering.md)** — read an existing
  `.amxd` back into Python.
