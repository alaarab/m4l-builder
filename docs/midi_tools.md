# MIDI Tools (Live 12)

Live 12 added **MIDI Tools** — devices that run inside the clip editor to
create or rewrite notes. There are two kinds:

- **MIDI Generator** (`MidiGenerator`) — *adds* new notes to a clip.
- **MIDI Transformation** (`MidiTransformation`) — *rewrites* the selected notes.

m4l-builder emits both as first-class `.amxd` device types. The format isn't
well documented publicly; the device-type codes and `amxdtype` values below were
reverse-engineered from shipping Live 12 devices and are byte-verified.

## Building one

A MIDI Tool is built around a `live.miditool.in` → processing → `live.miditool.out`
chain. The `midi_tool_io` helper creates that scaffolding:

```python
from m4l_builder import MidiTransformation, device_output_path, midi_tool_io

device = MidiTransformation("Passthrough", 200, 120)
device.add_dsp(*midi_tool_io("mt"))
device.add_line("mt_in", 0, "mt_out", 0)   # notes pass straight through
device.build(device_output_path("Passthrough", "note_transformation"))
```

That bare `mt_in[0] → mt_out[0]` connection is a valid (no-op) transformation.
Insert your note processing between them to actually change the clip. See
[`examples/04_midi_transformation.py`](https://github.com/alaarab/m4l-builder/blob/main/examples/04_midi_transformation.py).

## The `live.miditool.in` / `live.miditool.out` contract

`midi_tool_io` creates two objects:

- **`{prefix}_in`** (`live.miditool.in`) — outlet 0: the **notes dictionary**;
  outlet 1: the **context dictionary** (grid interval, time selection, scale,
  root note). It emits a snapshot of the clip's notes when an apply cycle runs.
- **`{prefix}_out`** (`live.miditool.out`) — inlet 0: send the processed notes
  dictionary back. For a Generator the notes are added; for a Transformation
  they replace the selection.

### Notes dictionary

```jsonc
{
  "notes": [
    {
      "pitch": 60,          // MIDI note 0-127 (required)
      "start_time": 0.0,    // beats from clip start (required)
      "duration": 1.0,      // length in beats (required)
      "velocity": 100.0,    // optional
      "probability": 1.0,   // optional, 0-1
      "velocity_deviation": 0.0,
      "release_velocity": 64.0,
      "mute": 0
    }
  ]
}
```

Process this dictionary with `dict`/`dict.pack`/`zl` objects or a `v8`/`js`
script between `mt_in` outlet 0 and `mt_out` inlet 0. (A pure-Python helper for
constructing note dictionaries is on the roadmap; for now a generator builds the
dict with Max `dict` objects or an embedded script.)

## Where Live loads them

Save the `.amxd` under your User Library:

- Generators → `MIDI Tools/Max Generators/`
- Transformations → `MIDI Tools/Max Transformations/`

Then refresh Live's browser; the tool appears in the clip editor's MIDI Tools.

## Format reference (verified)

| Type | Class | Header code (bytes 8-11) | `project.amxdtype` |
|------|-------|--------------------------|--------------------|
| MIDI Transformation | `MidiTransformation` | `natt` | `1851880564` (big-endian `"natt"`) |
| MIDI Generator | `MidiGenerator` | `nagg` | `1851877223` (big-endian `"nagg"`) |

`device_from_amxd` reads both back into the correct class, so you can round-trip
and reverse-engineer existing MIDI Tools with `snapshot_from_amxd`.
