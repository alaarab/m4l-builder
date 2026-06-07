# m4l-builder

[![PyPI version](https://img.shields.io/pypi/v/m4l-builder.svg)](https://pypi.org/project/m4l-builder/)
[![Tests](https://img.shields.io/github/actions/workflow/status/alaarab/m4l-builder/tests.yml?label=tests)](https://github.com/alaarab/m4l-builder/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://pypi.org/project/m4l-builder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Build Max for Live devices in Python.** Write a script, emit a `.amxd` file straight to your Ableton User Library. No Max GUI required — everything is version-controllable, scriptable, and reproducible, with **zero runtime dependencies** (pure standard library).

---

## Why m4l-builder

Max for Live devices are normally authored by hand in the Max patcher GUI, which makes them hard to version, diff, review, or generate programmatically. `m4l-builder` treats a device as **code**:

- **Scriptable** — generate whole families of devices from a loop, a config, or a spec.
- **Version-controllable** — a device is a Python script; `git diff` shows real changes.
- **Reproducible** — the same script always emits the same `.amxd`.
- **No GUI, no runtime deps** — pure Python stdlib; runs in CI.
- **Batteries included** — 100+ DSP blocks, a UI widget library, jsui visual engines, themes, and reverse-engineering tools to round-trip existing devices.

## Install

```bash
pip install m4l-builder
```

Requires Python 3.9+. To build the actual `.amxd` into your User Library you also need Ableton Live 10.1+ with Max for Live.

## Quick start

```python
from m4l_builder import AudioEffect, WARM, device_output_path

device = AudioEffect("My Gain", width=150, height=110, theme=WARM)

# A dial in presentation mode
device.add_panel("bg", [0, 0, 150, 110])
device.add_dial("gain", "Gain", [10, 6, 50, 90],
                min_val=-70.0, max_val=6.0, initial=0.0,
                unitstyle=4, annotation_name="Gain")

# Signal path: stereo in -> gain -> stereo out, with smoothing
device.add_newobj("mul_l", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
device.add_newobj("mul_r", "*~ 1.", numinlets=2, numoutlets=1, outlettype=["signal"])
device.add_newobj("db2a", "dbtoa")
device.add_newobj("ln", "line~", numinlets=2, numoutlets=2, outlettype=["signal", "bang"])

device.add_line("obj-plugin", 0, "mul_l", 0)     # stereo in (auto plugin~)
device.add_line("obj-plugin", 1, "mul_r", 0)
device.add_line("mul_l", 0, "obj-plugout", 0)     # stereo out (auto plugout~)
device.add_line("mul_r", 0, "obj-plugout", 1)
device.add_line("gain", 0, "db2a", 0)             # dial -> dB->amp -> smooth -> gain
device.add_line("db2a", 0, "ln", 0)
device.add_line("ln", 0, "mul_l", 1)
device.add_line("ln", 0, "mul_r", 1)

device.build(device_output_path("My Gain"))
```

Restart Ableton (or refresh the browser) and the device appears in your User Library.

→ Walk through this step by step in **[Getting started](getting_started.md)**.

## What's in the box

| Area | What you get |
|------|--------------|
| **Device types** | `AudioEffect`, `Instrument`, `MidiEffect`, plus Live 12 MIDI Tools (`MidiTransformation`, `MidiGenerator`) |
| **DSP blocks** | 100+ composable blocks: filters, dynamics, delay/reverb, modulation, synthesis, spectral, MIDI, generative — see the **[catalog](catalog.md)** |
| **UI widgets** | Dials, sliders, toggles, menus, panels, scopes, meters, text, and more — all placed in presentation mode |
| **Visual engines** | jsui-based vector displays: filter response, parametric EQ nodes, ADSR, spectrum, waveform |
| **Themes** | `MIDNIGHT`, `WARM`, `COOL`, `LIGHT` presets, or a custom `Theme` |
| **Reverse engineering** | Read an existing `.amxd` back into a Python model with `from_amxd` for round-trip editing |
| **LiveMCP bridge** | Embed a bridge so an MCP client can drive the device live in Ableton |

## Where to go next

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting started](getting_started.md)** — build your first device end to end.
- :material-book-open-variant: **[DSP & UI catalog](catalog.md)** — browse every building block.
- :material-piano: **[MIDI Tools](midi_tools.md)** — Live 12 Generators & Transformations.
- :material-api: **[API reference](api.md)** — every public class and function.
- :material-backup-restore: **[Reverse engineering](reverse_engineering.md)** — round-trip existing devices.
- :material-link-variant: **[Resources](resources.md)** — Max/MSP and Max for Live sources.

</div>

## License

MIT © Ala Arab. See [LICENSE](https://github.com/alaarab/m4l-builder/blob/main/LICENSE).
