# Bring an existing device

`m4l import` turns a `.amxd` you already have into a `build.py` that rebuilds
it with m4l-builder. Use it to move a device you made in Max into code, or to
start a new device from an old one.

```bash
m4l import "My Gain.amxd"
```

```text
created my_gain/build.py
AudioEffect, theme WARM: 9 boxes, 9 patch lines
round-trip: the script rebuilds an identical device (box IDs aside)
next:   m4l build my_gain/build.py    (or: m4l watch my_gain/build.py)
```

From there it is an ordinary build script: `m4l build`, `m4l watch` and
`m4l lint` all work on it (see the [command line guide](cli.md)).

```bash
m4l import DEVICE.amxd [--out PATH] [--force] [--no-check]
```

- `--out` is the script path, or a folder to write `build.py` into. The
  default is `<name>/build.py`.
- Support files (scripts, `.gendsp` files) are written next to the script.
- Nothing is overwritten unless you pass `--force`.
- `--no-check` skips the round-trip check described below.

## What you get

Importing the gain device from `examples/01_gain_audio_effect.py` gives back
nearly the script it was built from:

```python
from m4l_builder import WARM, AudioEffect, device_output_path

NAME = "My Gain"


def build_device() -> AudioEffect:
    device = AudioEffect(NAME, width=150, height=110, theme=WARM)

    device.add_panel("bg", [0, 0, 150, 110])
    device.add_dial("gain", "Gain", [10, 6, 50, 90], min_val=-70.0, max_val=6.0, initial=0.0,
                    unitstyle=4, annotation_name="Gain")

    device.add_newobj("mul_l", "*~ 1.")
    device.add_newobj("mul_r", "*~ 1.")
    device.add_newobj("db2a", "dbtoa")
    device.add_newobj("pk", "pack f 20")
    device.add_newobj("ln", "line~")

    device.add_line("obj-plugin", 0, "mul_l", 0)
    ...
    return device


if __name__ == "__main__":
    path = device_output_path(NAME, "audio_effect")
    build_device().build(path)
    print("wrote", path)
```

| In the device | In the script |
|---|---|
| Device type | `AudioEffect`, `Instrument`, `MidiEffect`, `MidiTransformation` or `MidiGenerator` |
| Width and height | constructor arguments (`allow_tall=True` when taller than Live's device view). A device Max saved with no width (Live sizes it) gets its content width |
| Colours that match a built-in theme | `theme=WARM` (or whichever matches best); otherwise explicit colours |
| `live.dial`, `live.slider`, `live.numbox`, `live.toggle`, `live.button`, `live.text`, `live.menu`, `live.tab`, `live.gain~` | `add_dial`, `add_slider`, `add_number_box`, ... with their range, initial value, unit style and presentation rect |
| `panel`, `live.comment`, `live.meter~`, `live.scope~`, `live.line` | `add_panel`, `add_comment`, `add_meter`, `add_scope`, `add_live_line` |
| Objects and message boxes | `add_newobj` and `add_box(message(...))` |
| Patch cords | `add_line`, keeping `order` and `midpoints` |
| `gen~` with an embedded codebox | `embed_gendsp(...)`, with the GenExpr in a constant at the top of the script |
| `gen~ name` with a `.gendsp` file | `add_gendsp(...)` when the file came from m4l-builder; otherwise `add_support_file` plus the `gen~` object |
| `jsui` / `v8ui` | `add_jsui` / `add_v8ui`, reading the script from the file beside `build.py` |
| `js` / `v8` objects | `register_asset` for the script plus the object |
| A `p name` subpatcher built with `Subpatcher` | a `Subpatcher` block with its own `add_newobj` / `add_line` calls |
| Push parameter banks, latency, MPE | `assign_parameter_bank`, `device.latency`, `device.is_mpe` |

Recipes and composite helpers (`add_custom_knob`, `add_xy_pad`,
`generative_midi_stage`, ...) come back as the boxes they are made of: a
custom knob becomes its `v8ui` plus the hidden `live.dial` that stores its
parameter. The device is the same; fold them back into the helper call by
hand if you want the shorter form.

Box IDs are readable. Max's own `obj-12` style IDs become names taken from
the box: its object text (`mul`, `dbtoa`, `grit` for `gen~ grit`), its
parameter (`drive`) or its label text. IDs someone already chose are kept.

## How it stays exact

Every call is checked before it is written. The importer runs the call it is
about to write, compares the box it makes with the box in your device, and
adds only the arguments needed to make them match. That is why most calls
carry so few arguments: anything the helper or the theme already gets right is
left out.

The library's helpers fill in a few attributes Max leaves unset, such as a
font on every object or hover text on every dial. When the source device has
none, the script removes them again at the end of `build_device()`:

```python
    # The source leaves these attributes unset; drop the values add_* fills in.
    _unset(device, ["fontname", "fontsize"], "dbtoa", "mul", "mul_2", "grit")
```

A box that no helper can reproduce is written as a raw `add_box({...})` dict
with a comment saying why, so nothing is ever dropped:

```python
    # TODO(m4l import): kept raw -- no add_* helper for 'number'
    device.add_box({"box": {
        "id": "number",
        "maxclass": "number",
        ...
    }})
```

The usual reasons a box stays raw:

- **No helper for that object**: Max's plain `comment`, `number`, `flonum`,
  `toggle`, `bpatcher` and other non-Live UI objects.
- **gen~ patchers saved by Max**: their patcher settings differ from what
  `embed_gendsp` writes. The GenExpr still goes into a readable constant.
- **Subpatchers saved by Max**: same reason; the subpatcher is kept whole.
- **A control whose scripting name differs from its parameter name**: the
  helpers always set both to the same value.
- **A missing script**: a `jsui` whose `.js` file was neither inside the device
  nor next to it.

Search the script for `TODO(m4l import)` to find them all. The command also
lists them when it runs.

## Support files

A frozen device carries its scripts and `.gendsp` files inside it, so the
import finds everything, including bundled files the device doesn't list as
dependencies. For a device that isn't frozen, keep its files in the same
folder as the `.amxd`. Files found in neither place are listed as missing,
marked with a TODO in the script, and the round-trip check fails until you
copy them in. A dependency name that points outside the device's folder (an
absolute path or `../`) is never read.

## The round-trip check

After writing the script, `m4l import` runs it and compares the device it
builds with the one you imported:

- every box with all of its attributes, including embedded gen~ patchers and
  subpatchers (box IDs may differ);
- every patch cord, by the boxes it connects;
- device type, size, latency, MPE flag, Push banks and the list of support
  files, and the contents of each support file.

Settings Max writes again on every save are not compared: timestamps, window
positions, the patcher's default font and its parameter index. Neither are
empty Push banks (Max saves an empty bank 0 by default; the library only
writes banks that hold parameters), nor the width of a device Max left for
Live to size. If anything
else differs, the command lists it and exits 1.

## From Python

```python
from m4l_builder.importer import check_import, import_amxd

result = import_amxd("My Gain.amxd")
result.write("my_gain/build.py")        # the script and its support files
print(result.raw_boxes)                 # boxes kept as raw dicts, with reasons
print(check_import(result.source, "my_gain/build.py"))   # [] when identical
```
