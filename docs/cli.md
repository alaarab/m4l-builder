# Command line

Installing m4l-builder adds an `m4l` command (also available as
`python -m m4l_builder`). It runs your build scripts for you, rebuilds them on
save, checks them without writing anything, and summarises a built `.amxd`.

```bash
m4l new "My Gain" --type audio     # scaffold my_gain/build.py
m4l build my_gain/build.py         # build it
m4l watch my_gain/build.py         # rebuild into the User Library on every save
m4l lint my_gain/build.py          # validate without writing
m4l inspect "My Gain.amxd"         # type, size, parameters, box counts
```

## What counts as a build script

Any Python file that makes a `Device` and calls `device.build(path)`, the way
every script in [`examples/`](https://github.com/alaarab/m4l-builder/tree/main/examples)
does. The CLI runs the script as `__main__` and intercepts each
`device.build(...)` call, so it can redirect the write (`build --out`), send it
to the User Library (`watch`) or skip it entirely (`lint`). A script that only
defines a top-level `device` or a `build_device()` function works too.

Scripts run with their own folder first on `sys.path`, so they can import
helper modules that sit next to them.

## `m4l new`

```bash
m4l new NAME [--type audio|midi|instrument] [--out PATH] [--force]
```

Writes a runnable build script, by default `<name>/build.py` (`"My Gain"`
becomes `my_gain/build.py`). Each type starts from a small working device:

| `--type` | Device | Starts with |
|---|---|---|
| `audio` (default) | `AudioEffect` | a smoothed gain dial on the stereo signal |
| `midi` | `MidiEffect` | a `midiin` to `midiout` pass-through |
| `instrument` | `Instrument` | a sine voice with an ADSR envelope and a level dial |

Every scaffold lints clean. `new` never overwrites a file unless you pass
`--force`.

## `m4l build`

```bash
m4l build SCRIPT [--out PATH]
```

Runs the script and prints where each device went. Without `--out`, devices
are written where the script asks; a script that never calls `build()` is
written to the User Library. `--out` redirects the write:

- `--out dist/` keeps each build's own file name inside `dist/`.
- `--out "Release.amxd"` writes a single device to that file (an error if the
  script builds more than one).

## `m4l watch`

```bash
m4l watch SCRIPT [--out PATH] [--interval SECONDS]
```

Checks the script's modification time (every 0.5 s by default) and rebuilds
it on every save, straight into your Ableton User Library
(`device_output_path`, which honours `M4L_USER_LIBRARY`). After each build it
prints what changed:

```text
watching my_gain/build.py (Ctrl-C to stop)
[14:02:11] built My Gain -> ~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/My Gain.amxd
           first build: 9 boxes, 9 lines, 1 parameter(s)
[14:03:40] built My Gain -> ~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/My Gain.amxd
           + boxes: drive
           + parameter: Drive
           bytes: 6,605 -> 7,412
```

A script that raises prints the error and the watch carries on, so a
half-typed edit doesn't end the session. Only the script file itself is
watched; restart the watch after editing a helper module it imports.

## `m4l lint`

```bash
m4l lint SCRIPT|DEVICE.amxd [--strict]
```

Builds the device in memory (nothing is written) and runs the library's checks:

- **graph validation**: unknown patchline endpoints, out-of-range inlets and
  outlets, duplicate ids, unreachable controls, layout warnings
  (`Device.lint`);
- **box lint**: inlet/outlet declarations compared against the vendored Max
  object dataset;
- **GenExpr lint**: every gen~ codebox, embedded or in a `.gendsp` file,
  checked for unassigned outputs, out-of-range `in`/`out` indexes and
  multi-line ternaries;
- **jsui coverage**: messages routed to a jsui/v8ui script that defines no
  handler for them.

It exits 1 when any error is found, or with `--strict` when any warning is.

## `m4l inspect`

```bash
m4l inspect DEVICE.amxd [--json]
```

```text
My Gain  (audio_effect, 150 x 110 px)
  file        My Gain.amxd  (6,605 bytes)
  boxes       9 (2 in presentation), 9 patch lines
  maxclasses  newobj 7, live.dial 1, panel 1
  objects     *~ 2, dbtoa 1, line~ 1, pack 1, plugin~ 1, plugout~ 1
  parameters  1
    - Gain (float: -70.0 .. 6.0, initial 0.0)
```

`--json` prints the same summary as JSON for scripts and CI.
