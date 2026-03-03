# m4l-builder

Programmatically build Max for Live devices in Python.

## Overview

m4l-builder generates fully functional Max for Live (.amxd) devices without the Max GUI. Define UI, wire DSP, and export a binary .amxd that loads directly into Ableton Live.

- **Max patching in code** -- version-controllable, reproducible, scriptable
- **No Max license required** to generate devices -- only Ableton Live + Max for Live to run them
- **28 composable DSP blocks** -- filters, delays, saturators, compressor, limiter, LFOs, and more
- **21 UI components** -- dials, sliders, menus, scopes, meters, ADSR, JSUI, and more
- **Theme system** -- 4 built-in themes with automatic color injection into all UI components
- **kwargs passthrough** -- any Max attribute can be set on any UI component

## Quick Start

```bash
git clone https://github.com/alaarab/m4l-builder.git
cd m4l-builder
pip install -e .
```

### Minimal Example

```python
from m4l_builder import AudioEffect, device_output_path
from m4l_builder.theme import WARM

device = AudioEffect("Simple Gain", width=150, height=110, theme=WARM)

device.add_panel("bg", [0, 0, 150, 110])
device.add_comment("title", [6, 5, 50, 14], "GAIN", fontsize=12.0)
device.add_dial("gain", "Gain", [10, 22, 50, 75],
                min_val=-70.0, max_val=6.0, initial=0.0,
                unitstyle=4, annotation_name="Output Gain")

# DSP: plugin~ -> dbtoa -> line~ -> *~ -> plugout~
gain_l = device.add_newobj("gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                           outlettype=["signal"])
gain_r = device.add_newobj("gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                           outlettype=["signal"])
device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1, outlettype=[""])
device.add_newobj("gain_pk", "pack f 20", numinlets=2, numoutlets=1, outlettype=[""])
device.add_newobj("gain_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"])

device.add_line("obj-plugin", 0, "gain_l", 0)
device.add_line("obj-plugin", 1, "gain_r", 0)
device.add_line("gain_l", 0, "obj-plugout", 0)
device.add_line("gain_r", 0, "obj-plugout", 1)
device.add_line("gain", 0, "db2a", 0)
device.add_line("db2a", 0, "gain_pk", 0)
device.add_line("gain_pk", 0, "gain_ln", 0)
device.add_line("gain_ln", 0, "gain_l", 1)
device.add_line("gain_ln", 0, "gain_r", 1)

device.build(device_output_path("Simple Gain"))
```

## Device Types

```python
from m4l_builder import AudioEffect, Instrument, MidiEffect

device = AudioEffect("My Effect", width=300, height=170)   # auto plugin~/plugout~
device = Instrument("My Synth", width=400, height=200)     # no auto I/O
device = MidiEffect("My MIDI Tool", width=200, height=100) # MIDI only, no audio
```

## UI Components (21)

All UI functions place objects in presentation mode at the specified `rect`. kwargs passthrough lets you set any Max attribute directly.

| Function | Component | Description |
|----------|-----------|-------------|
| `add_panel` | panel | Background panel (auto `background:1`) |
| `add_dial` | live.dial | Rotary dial with Live parameter storage |
| `add_slider` | live.slider | Linear slider (vertical/horizontal) |
| `add_toggle` | live.toggle | On/off toggle |
| `add_button` | live.button | Momentary bang button |
| `add_tab` | live.tab | Tab bar selector |
| `add_menu` | live.menu | Dropdown menu |
| `add_number_box` | live.numbox | Numeric entry/display |
| `add_comment` | comment | Static text label |
| `add_scope` | live.scope~ | Signal oscilloscope |
| `add_meter` | live.meter~ | Level meter (auto theme colors) |
| `add_live_text` | live.text | Clickable text button/toggle |
| `add_fpic` | fpic | Image display |
| `add_live_gain` | live.gain~ | Gain fader with built-in metering |
| `add_multislider` | multislider | Multi-value slider array |
| `add_jsui` | jsui | JavaScript UI for custom drawing |
| `add_adsrui` | live.adsrui | ADSR envelope editor with drag handles |
| `add_live_drop` | live.drop | Drag-and-drop file target |
| `add_bpatcher` | bpatcher | Embeddable sub-patcher |
| `add_swatch` | swatch | Color picker/display |
| `add_textedit` | textedit | Editable text field |

## DSP Building Blocks (28)

Every DSP function returns `(boxes, lines)`. Add to a device with:

```python
boxes, lines = gain_stage("my_gain")
for b in boxes: device.add_box(b)
for l in lines: device.lines.append(l)
```

| Category | Functions |
|----------|-----------|
| **I/O** | `stereo_io` |
| **Gain/Mixing** | `gain_stage`, `dry_wet_mix`, `signal_divide` |
| **Filters** | `highpass_filter`, `lowpass_filter`, `bandpass_filter`, `notch_filter`, `onepole_filter`, `highshelf_filter`, `lowshelf_filter`, `tilt_eq`, `crossover_3band` |
| **Saturation** | `saturation` (tanh/overdrive/clip/degrade modes) |
| **Dynamics** | `envelope_follower`, `compressor`, `limiter` |
| **Delay** | `delay_line`, `feedback_delay` |
| **Modulation** | `lfo` (sine/saw/square/triangle), `tremolo` |
| **Stereo** | `ms_encode_decode`, `dc_block` |
| **Routing** | `selector` |
| **Resonance** | `comb_resonator` |
| **Utility** | `param_smooth`, `noise_source`, `tempo_sync` |

## Theme System

Four built-in themes provide coordinated colors for backgrounds, text, and accents. Pass a theme to the device constructor and all UI components inherit its colors automatically.

```python
from m4l_builder.theme import MIDNIGHT, WARM, COOL, LIGHT

device = AudioEffect("My Effect", width=400, height=200, theme=MIDNIGHT)
```

| Theme | Accent | Character |
|-------|--------|-----------|
| `MIDNIGHT` | Teal | Dark, cool, modern |
| `WARM` | Orange | Dark, warm, analog feel |
| `COOL` | Blue | Dark, clean, precise |
| `LIGHT` | Blue | Light background, high contrast |

Each `Theme` dataclass provides: `bg`, `surface`, `section` (background layers), `text`, `text_dim` (typography), `accent` (active/selected color), plus derived `dial_color`, `needle_color`, `tab_*`, `meter_*`, and `scope_*` colors. Meters and scopes auto-inherit theme colors. Uses Ableton Sans fonts by default.

## Example Devices (20)

The `examples/` directory contains complete, buildable devices:

| # | File | Device | Type | Theme | Description |
|---|------|--------|------|-------|-------------|
| 1 | `simple_gain.py` | Simple Gain | Audio | WARM | Minimal starter -- single gain dial |
| 2 | `stereo_filter.py` | Stereo Filter | Audio | COOL | HP/LP/BP/Notch SVF filter |
| 3 | `stereo_utility.py` | Stereo Utility | Audio | COOL | Gain (dB), pan, width (M/S), phase |
| 4 | `simple_compressor.py` | Simple Compressor | Audio | MIDNIGHT | Log-domain compressor with GR meter |
| 5 | `multiband_imager.py` | Multiband Imager | Audio | COOL | 3-band crossover with per-band width |
| 6 | `transient_shaper.py` | Transient Shaper | Audio | WARM | Attack/sustain shaping with output protection |
| 7 | `tape_degradation.py` | Tape Degradation | Audio | WARM | Saturation, wow/flutter, noise, rolloff |
| 8 | `stereo_delay.py` | Stereo Delay | Audio | MIDNIGHT | L/R delay with tanh feedback saturation |
| 9 | `midside_suite.py` | Mid/Side Suite | Audio | COOL | M/S processing with tilt EQ and saturation |
| 10 | `multiband_saturator.py` | Multiband Saturator | Audio | WARM | 3-band with tanh/overdrive/clip modes |
| 11 | `rhythmic_gate.py` | Rhythmic Gate | Audio | WARM | LFO-driven gate with 4 waveforms |
| 12 | `auto_filter.py` | Auto Filter | Audio | MIDNIGHT | Envelope follower + LFO modulated filter |
| 13 | `comb_bank.py` | Comb Resonator | Audio | MIDNIGHT | Tuned comb bank with note display |
| 14 | `lofi_processor.py` | LoFi Processor | Audio | WARM | Bitcrusher + sample rate reduction |
| 15 | `parametric_eq.py` | Parametric EQ | Audio | -- | JSUI custom EQ curve display |
| 16 | `expression_control.py` | Expression Control | MIDI | MIDNIGHT | 8 macro knobs outputting MIDI CC |
| 17 | `macro_randomizer.py` | Macro Randomizer | Audio | COOL | 7 randomizable outputs with auto/trigger |
| 18 | `step_sequencer.py` | Step Sequencer | MIDI | COOL | 8-step MIDI sequencer with sliders |
| 19 | `drone_synth.py` | Drone Synth | Instrument | MIDNIGHT | 4-voice drone with live.gain~ |
| 20 | `reverb.py` | Algorithmic Reverb | Audio | LIGHT | Schroeder reverb with room types |

Build any example:

```bash
uv run python examples/stereo_delay.py
```

## Output Path

`device_output_path()` auto-detects your Ableton User Library on macOS, Windows, and WSL. It scans common drive locations (D:, C:, /mnt/d, /mnt/c) and creates the correct subdirectory for the device type.

Override with the `M4L_USER_LIBRARY` environment variable:

```bash
export M4L_USER_LIBRARY="/path/to/your/User Library"
```

## Testing

1050+ tests across 9 test files:

```bash
uv run pytest tests/ -v
```

| Test File | Coverage |
|-----------|----------|
| `test_objects.py` | `newobj` and `patchline` dict structure |
| `test_ui.py` | All 21 UI element creators and properties |
| `test_dsp.py` | All 28 DSP building blocks return correct boxes/lines |
| `test_patcher.py` | Patcher dict generation and device type mapping |
| `test_container.py` | .amxd binary format: ampf header, type codes, JSON payload |
| `test_device.py` | Device class hierarchy, builder methods, theme injection |
| `test_theme.py` | Theme dataclass, color derivation, meter/scope colors, preset themes |
| `test_engines.py` | Engine/processing modules |
| `test_examples.py` | Integration: builds all 20 examples, verifies valid .amxd output |

## .amxd Binary Format

```
Offset  Size  Content
------  ----  -------
0       4     Magic: "ampf"
4       4     Version: uint32 LE = 4
8       4     Type: "aaaa" (audio), "iiii" (instrument), "mmmm" (MIDI)
12      4     Section: "meta"
16      4     Metadata length (uint32 LE)
20      4     Metadata payload
24      4     Section: "ptch"
28      4     JSON length (uint32 LE, includes null terminator)
32+     N     JSON patcher data, null-terminated
```

## Recommended Tools

**[LiveMCP](https://github.com/alaarab/livemcp)** -- Control Ableton Live via the Model Context Protocol. Load devices, trigger clips, adjust mixer settings. Pairs with m4l-builder for a fully code-driven production workflow.

## License

MIT
