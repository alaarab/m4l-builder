<!-- tokens: ~2900 -->
# AGENTS.md: m4l-builder

## Project Overview

**Purpose**: Programmatically build Max for Live devices in Python. Write scripts, emit binary .amxd files directly to Ableton User Library
**Stack**: Python 3.9+, hatchling build, uv package manager, pytest, zero runtime dependencies (pure stdlib)
**Version**: 0.4.0 (on PyPI as `m4l-builder`)
**Status**: Production

Build .amxd devices without the Max GUI: version controllable, scriptable, reproducible.

Note: this is a library, not a CLI. `uvx m4l-builder --help` will not work.

## Package Location

The actual package lives under the `src/` layout:

```
src/m4l_builder/       <- importable package (NOT m4l_builder/ at the root)
```

## Workspace Boundaries

`m4l-builder` is the library/tooling repo.

Active flagship plugin product work lives in the sibling
`../Max4LivePlugins` repo on this machine, or at `MAX4LIVEPLUGINS_ROOT` if the
env var is set. When the task is about a real plugin rather than the builder
library itself, prefer working in `Max4LivePlugins/plugins/<plugin>/`.

This repo should contain zero in-repo plugin/device scripts. Migrated private
device builders live in `../Max4LivePlugins/legacy_examples/`, and canonical
product workspaces live in `../Max4LivePlugins/plugins/<plugin>/`.

## Commands

```bash
# Install (editable)
uv pip install -e .

# Test
uv run pytest tests/ -v
uv run pytest tests/ --cov=m4l_builder --cov-report=term-missing

# Build and publish to PyPI (requires token)
uv build && uv publish --token <pypi-token>
# or set UV_PUBLISH_TOKEN env var
```

No linting is configured (`.ruff_cache/` is gitignored but no ruff config exists in `pyproject.toml`).

## Build Output Paths

Devices are written to the Ableton User Library. On this machine: `/mnt/d/Music/Ableton/User Library/` (Windows D: drive via WSL). On macOS it would be `~/Music/Ableton/User Library/`.

## Project Skills

Skills in `.Codex/skills/` directory:

- `/verify`: Pre-commit gate, runs tests then builds the example suite, checks git status for .amxd artifacts
- `/test`: Run pytest with coverage options
- `/publish`: Bump version, build, and publish to PyPI

Note: `/publish` should update `CHANGELOG.md`; that file exists at the repo root.

## Architecture

```
src/m4l_builder/
├── __init__.py           # Re-exports everything: Device types, DSP, UI, theme, objects, constants
├── device.py             # Base Device class + AudioEffect, Instrument, MidiEffect
├── patcher.py            # Assembles full JSON patcher structure
├── container.py          # Wraps JSON in ampf binary header (32-byte header)
├── ui.py                 # 16 UI element creator functions (presentation mode)
├── dsp.py                # 19 DSP building blocks returning (boxes, lines) tuples
├── objects.py            # newobj() and patchline() low-level factory functions
├── constants.py          # UNITSTYLE_* constants, device type codes, defaults
├── theme.py              # Theme dataclass + 4 presets (MIDNIGHT, WARM, COOL, LIGHT)
└── engines/              # Subpackage: JS string generators for jsui visualizations
    ├── __init__.py
    ├── filter_curve.py   # filter_curve_js()
    ├── eq_curve.py       # eq_curve_js()
    ├── envelope_display.py  # envelope_display_js()
    ├── spectrum_analyzer.py # spectrum_analyzer_js()
    └── waveform_display.py  # waveform_display_js()

tests/                    # automated test suite
```

### Architecture Layers

1. **Device API** (`device.py`): top-level interface; `add_panel`, `add_dial`, `add_newobj`, `add_line`, etc.
2. **UI layer** (`ui.py`): 16 presentation-mode element constructors
3. **DSP layer** (`dsp.py`): 19 composable signal-processing blocks
4. **Engines** (`engines/`): JS string generators for jsui canvas visualizations
5. **Patcher** (`patcher.py`): assembles boxes + lines into the full JSON structure
6. **Container** (`container.py`): wraps JSON in the ampf binary format

### Device Types

```python
from m4l_builder import AudioEffect, Instrument, MidiEffect

device = AudioEffect("name", width=300, height=170)   # auto-adds plugin~ / plugout~
device = Instrument("name", width=400, height=200)    # no auto I/O
device = MidiEffect("name", width=200, height=100)    # MIDI only
```

Auto-added plugin~/plugout~ objects use reserved IDs `"obj-plugin"` and `"obj-plugout"`.

### UI Components (16)

All functions place objects in presentation mode at `rect=[x, y, w, h]`.
Device methods are `add_<name>(id, rect, ...)` wrappers around the raw functions in `ui.py`.

- `add_panel`, `add_dial`, `add_slider`, `add_toggle`, `add_button`
- `add_tab`, `add_menu`, `add_number_box`, `add_comment`
- `add_scope`, `add_meter`, `add_live_text`, `add_fpic`
- `add_live_gain`, `add_multislider`, `add_jsui`

**kwargs passthrough**: any Max attribute can be set directly on any component.

### DSP Building Blocks (19)

All DSP functions return `(boxes, lines)` tuples, designed for composition.
Add to a device with `device.add_dsp(boxes, lines)` (convenience) or individually via `device.add_box()` / `device.add_line()`.

**I/O**: `stereo_io`
**Gain/Mixing**: `gain_stage`, `dry_wet_mix`, `signal_divide`
**Filters**: `highpass_filter`, `lowpass_filter`, `onepole_filter`, `tilt_eq`, `crossover_3band`
**Saturation**: `saturation` (tanh / overdrive / clip / degrade modes)
**Dynamics**: `envelope_follower`
**Delay**: `delay_line`, `feedback_delay`
**Modulation**: `lfo`, `tremolo`
**Stereo**: `ms_encode_decode`, `dc_block`
**Routing**: `selector`
**Resonance**: `comb_resonator`

### Low-Level Object Factories (`objects.py`)

```python
from m4l_builder import newobj, patchline

box  = newobj("obj-1", "plugin~", numinlets=2, numoutlets=2,
              outlettype=["signal", "signal"])
line = patchline("obj-1", 0, "obj-2", 0)
```

Use these when DSP blocks don't cover a required Max object.
`device.add_newobj(...)` is the device-level wrapper around `newobj()`.

### Constants (`constants.py`)

```python
from m4l_builder.constants import (
    UNITSTYLE_INT, UNITSTYLE_FLOAT, UNITSTYLE_TIME, UNITSTYLE_HZ,
    UNITSTYLE_DB, UNITSTYLE_PERCENT, UNITSTYLE_PAN, UNITSTYLE_SEMITONE,
    UNITSTYLE_MIDI, UNITSTYLE_CUSTOM, UNITSTYLE_NATIVE,
)
```

Also exports: `AUDIO_EFFECT`, `INSTRUMENT`, `MIDI_EFFECT` (binary type codes),
`AMXD_TYPE`, `DEVICE_TYPE_CODES`, `DEFAULT_APPVERSION`, default colors.

### Engines: jsui JS Generators (`engines/`)

Each engine function returns an ES5 JavaScript string for Max's jsui object
(mgraphics/Cairo vector graphics). Max uses SpiderMonkey, ES5 only, no ES6+.

```python
from m4l_builder.engines import filter_curve_js

device.add_jsui("filter_display", [10, 30, 200, 80],
                js_code=filter_curve_js(), numinlets=3)
```

Available generators:
- `filter_curve_js()`: single filter response curve
- `eq_curve_js()`: multi-band parametric EQ curve with draggable nodes
- `envelope_display_js()`: ADSR envelope shape
- `spectrum_analyzer_js()`: frequency spectrum analyzer
- `waveform_display_js()`: waveform / oscilloscope display

### Theme System

```python
from m4l_builder.theme import MIDNIGHT, WARM, COOL, LIGHT

device = AudioEffect("My Effect", width=400, height=200, theme=MIDNIGHT)
```

Themes provide: `bg`, `surface`, `section`, `text`, `text_dim`, `accent`, plus derived colors for dials, needles, tabs.
Pass `theme=` to the device constructor; all `add_*` calls inherit colors automatically.

## .amxd Binary Format

```
Offset  Content
------  -------
0-3     Magic: "ampf"
4-7     Version: 4 (uint32 LE)
8-11    Type: "aaaa" (audio) | "iiii" (instrument) | "mmmm" (MIDI)
12-15   Section: "meta"
16-19   Metadata length (uint32 LE)
20-23   Metadata payload
24-27   Section: "ptch"
28-31   JSON length (uint32 LE, includes null terminator)
32+     JSON patcher data, null-terminated
```

Header is 32 bytes. JSON follows immediately.

## Testing

Automated tests cover the framework modules plus smoke builds that write real
`.amxd` files. No pytest markers config: `"not slow"` marker in `/test` skill
is not registered.

```
test_objects.py    :newobj, patchline factory functions
test_ui.py         :All 16 UI element creators
test_dsp.py        :DSP blocks return correct (boxes, lines) tuples
test_patcher.py    :Patcher dict generation and structure
test_container.py  :Binary format (ampf header) validation
test_device.py     :Device class hierarchy, theme injection, add_* methods
test_theme.py      :Theme dataclass, presets
test_engines.py    :JS generator outputs
test_layout.py     :Row/Column/Grid layout helpers
test_live_api.py   :live_object_path, live_observer, live_set_control
test_presets.py    :preset_manager, add_preset_buttons
test_build_smoke.py:Integration: inline smoke builds for audio, instrument, and MIDI devices
```

## Legacy Device Scripts

Legacy private device builders that used to live in this repo were migrated to
`../Max4LivePlugins/legacy_examples/`. This repo should not regain a local
`examples/` plugin surface.

## Installation in Ableton

Built devices are placed in:
```
~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/
```

Restart Ableton or refresh the browser to see new devices. Instrument and MIDI Effect types would go in their respective subdirectories.

## Key Conventions

1. **Package path**:Source is at `src/m4l_builder/`, not `m4l_builder/` at the repo root
2. **Python version**:Requires Python 3.9+ (not 3.10+)
3. **DSP composition**:DSP functions return `(boxes, lines)` tuples; use `device.add_dsp(boxes, lines)` to add in one call
4. **kwargs passthrough**:Any Max attribute can be set on any UI or object call
5. **ES5 only in engines**:Max's SpiderMonkey does not support ES6+; no arrow functions, let/const, template literals
6. **Reserved IDs**:`"obj-plugin"` and `"obj-plugout"` are used by AudioEffect automatically; do not reuse them
7. **Binary artifacts**:Do not commit .amxd files (they are build outputs)
8. **Theme injection**:Pass theme to the device constructor; all UI inherits colors automatically
9. **Workspace boundary**:Real plugin/device builders belong in `../Max4LivePlugins`, not this repo
10. **CHANGELOG exists**:`CHANGELOG.md` is at project root
11. **AGENTS.md is repo-local**:Tracked at the repo root; hatchling excludes it via `[tool.hatch.build] exclude`

## Recommended Tools

**[LiveMCP](https://github.com/alaarab/livemcp)**:Control Ableton Live via MCP. Load devices, trigger clips, adjust mixer. Pairs with m4l-builder for a code-driven production workflow.
