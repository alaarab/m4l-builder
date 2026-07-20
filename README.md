# m4l-builder

[![PyPI version](https://img.shields.io/pypi/v/m4l-builder.svg)](https://pypi.org/project/m4l-builder/)
[![Tests](https://img.shields.io/github/actions/workflow/status/alaarab/m4l-builder/tests.yml?label=tests)](https://github.com/alaarab/m4l-builder)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://pypi.org/project/m4l-builder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Build Max for Live devices in Python. Write scripts, emit `.amxd` files straight to your Ableton User Library. No Max GUI required. Everything is version-controllable, scriptable, and reproducible. Zero runtime dependencies -- pure stdlib.

## Workspace boundaries

`m4l-builder` is a standalone library with zero runtime dependencies -- it
builds `.amxd` files on its own and has no requirement on any other repo.
This repo intentionally does not ship in-repo plugin/device scripts; it's a
framework, not a product collection.

The maintainer's own plugin products live in a private repo not published
here. If you're building your own devices with this library, there's no
required layout -- write your `build.py` scripts wherever you like and
`import m4l_builder`.

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

## Examples

Runnable scripts that build real devices live in [`examples/`](examples/); new
users should start with the step-by-step [getting started
guide](docs/getting_started.md).

```bash
uv run python examples/02_generative_midi.py   # builds a generative MIDI device
```

- [`01_gain_audio_effect.py`](examples/01_gain_audio_effect.py) — audio effect, low-level API
- [`02_generative_midi.py`](examples/02_generative_midi.py) — MIDI effect using the generative recipe
- [`03_stereo_width.py`](examples/03_stereo_width.py) — audio effect using the mid/side width recipe
- [`04_midi_transformation.py`](examples/04_midi_transformation.py) — Live 12 MIDI Tool (`MidiTransformation`) built on the `live.miditool.in`/`out` chain
- [`05_euclidean_midi.py`](examples/05_euclidean_midi.py) — MIDI effect using the Euclidean rhythm generator
- [`06_simple_synth.py`](examples/06_simple_synth.py) — `Instrument` device: oscillator through an ADSR amplitude envelope

## Key concepts

### Device types

The three classic types plus Live 12 MIDI Tools:

```python
from m4l_builder import AudioEffect, Instrument, MidiEffect
from m4l_builder import MidiTransformation, MidiGenerator  # Live 12 MIDI Tools

fx    = AudioEffect("FX", 300, 170)      # auto-adds plugin~/plugout~
synth = Instrument("Synth", 400, 200)    # no auto I/O
midi  = MidiEffect("MIDI FX", 200, 100)  # MIDI only

transform = MidiTransformation("Swing", 200, 120)  # rewrites clip notes
generator = MidiGenerator("Euclid", 200, 120)      # adds notes to a clip
```

`AudioEffect` auto-wires stereo `plugin~` / `plugout~` objects (IDs `obj-plugin`, `obj-plugout`). Instruments and MIDI effects leave I/O to you.

**MIDI Tools** (Live 12) are built around a `live.miditool.in` → processing →
`live.miditool.out` chain; use the `midi_tool_io` helper for the scaffolding.
A `MidiTransformation` rewrites the selected notes of a clip; a `MidiGenerator`
adds new notes. See the [MIDI Tools guide](docs/midi_tools.md) and
[`examples/04_midi_transformation.py`](examples/04_midi_transformation.py).

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
**Generative**: probability gate, random note, Euclidean rhythm
**MIDI Tools**: `midi_tool_io` (the `live.miditool.in/out` scaffold for Live 12 Generators/Transformations)
**Synthesis**: wavetable osc, noise, oscillator bank, ADSR, poly voices, grain cloud
**Spectral**: spectral gate, crossover, vocoder, phase vocoder
**Routing**: selector, send/receive (signal + message), matrix mixer, sidechain routing
**Utility**: param smooth, tempo sync, sample and hold, bitcrusher, coll/dict/pattr storage

100+ blocks total. Browse the [catalog](docs/catalog.md) or [docs/api.md](docs/api.md) for the full list with signatures.

### gen~ DSP primitives & verification

The DSP blocks above emit Max object graphs. For sample-accurate DSP that needs a
`gen~` codebox, `m4l-builder` provides a registry of **composable GenExpr
fragments** plus a codegen and a two-layer test harness — so the flagship plugins
compose audited primitives instead of hand-copying the same math.

**`gen_snippets`** — parameterized GenExpr fragments (each takes caller-chosen
variable names and returns a gen code string):

```python
from m4l_builder import peak_follower, soft_knee_gain_computer, dynamics_band

# detector -> soft-knee gain computer -> makeup, one reusable compressor band
GEN_CODE += dynamics_band("peak", "env", "atk", "rel",
                          "threshold", "ratio", "knee", "makeup", "gain")
```

Registry (17): `ms_encode` / `ms_decode` / `ms_width` (Mid/Side matrix),
`drive_blend` (level-matched tanh soft-clip), `peak_follower` (attack/release
detector), `isp_catmull_4x` (4× inter-sample-peak / true-peak), `kweight_coeffs_bs1770`
(ITU-R BS.1770-4 K-weight), `exp_pole` (one-pole ballistics coefficient),
`soft_knee_gain_computer` + `dynamics_band` (compressor gain path), `biquad_df1`
(Direct-Form-I biquad apply), `rbj_peaking` / `rbj_shelf` (runtime peaking-EQ /
low-high-shelf coefficients), `one_pole_coeff` / `one_pole_lp` / `one_pole_hp`
(cutoff-frequency 1st-order filter split), `exciter_harmonics` (harmonic-exciter
generator: odd tanh + even squarer, the added content).

**`build_gendsp(code, numins, numouts)`** — wraps GenExpr into a `.gendsp`
support file, and **lints at build time** (`gen_lint`): a dead/unassigned signal
out, an out-of-range `in N`/`out N` index, or the multi-line-ternary trap raise a
`ValueError` instead of silently shipping a broken device.

**`gen_sim`** — an offline simulator that runs a `gen~` kernel sample-by-sample in
pure Python, so tests assert the *audio behaviour*, not just the structure:

```python
from m4l_builder import simulate

out = simulate("History env(0.);\n" + peak_follower("in1", "env", "0.1", "0.9", "c")
               + "\nout1 = env;", {"in1": [1.0] * 5 + [0.0] * 5})
# assert attack is faster than release, no NaN, ratio=1 is transparent, ...
```

It supports History/Param/arithmetic/ternary/if-else and a pure-function table,
and **refuses** (rather than mis-evaluates) Delay/buffer/FFT kernels that need a
live render. This is how the suite proves a compressor is transparent at ratio 1
or a limiter never boosts — the "advertised-but-unwired" bug class — fully offline.

### Validating against Ableton's standards

`Device.check_guidelines()` checks a built device against the *statically
decidable* subset of Ableton's published Max for Live device conventions
(parameter naming, presentation geometry, forbidden objects, JavaScript style)
— before it is ever loaded in Live:

```python
for issue in device.check_guidelines():
    print(issue.severity, issue.code, issue.message)
```

…or over a folder of build scripts from the shell:

```bash
python -m m4l_builder.guidelines path/to/*/build.py
```

It flags **unknown / misspelled object names** — a typo like `cycl~` that would
otherwise ship as a Max `newobj: no such object` load error, reported with a
"did you mean `cycle~`?" suggestion — plus **duplicate parameter Long / Scripting
Names**, auto-indexed default names (`Gain[1]`), fractional pixel rects, and
forbidden `print`/`dac~`/`adc~`. It's **advisory** (reports, doesn't gate the
build) and it's the pre-Live static complement to a live console audit.

### Engines (jsui visualizations)

JavaScript generators for Max's jsui object. Each returns an ES5 string for mgraphics/Cairo rendering:

```python
from m4l_builder.engines import filter_curve_js

device.add_jsui("display", [10, 30, 200, 80],
                js_code=filter_curve_js(), numinlets=3)
```

Dozens of generators are available: filter curves, EQ, envelopes, spectrum, waveforms, XY pad, piano roll, step grids, grain clouds, vocoder bands, and more. See the auto-generated [catalog](docs/catalog.md) for the complete, current list of engines.

### Themes

16 built-in color themes — `AMBER`, `COBALT`, `COOL`, `FOREST`, `GRAPHITE`, `INDUSTRIAL`, `LIGHT`, `LOFI`, `MAGMA`, `MIDNIGHT`, `NEBULA`, `NEON`, `SOLAR`, `SYNTHWAVE`, `VIOLET`, `WARM` (see the [catalog](docs/catalog.md) for the current list). Pass to the device constructor and all UI elements inherit colors automatically:

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

Available recipes include `gain_controlled_stage`, `dry_wet_stage`,
`stereo_width_stage`, `generative_midi_stage`, `euclidean_sequencer_stage`,
`tempo_synced_delay`, and `midi_note_gate` — see the full list in the
[catalog](docs/catalog.md).

### Layout helpers

Automatic positioning with `Row`, `Column`, and `Grid` context managers:

```python
with device.row(10, 10, spacing=8, height=70) as r:
    r.add_dial("d1", "Param1", width=50)
    r.add_dial("d2", "Param2", width=50)
    r.add_dial("d3", "Param3", width=50)
```

### UI guidance

Beyond the widget API above, deeper UI/visual-design guidance lives in
[docs/ui_inputs_reference.md](docs/ui_inputs_reference.md) (every input
widget's full behavior), [docs/m4l_advanced_ui_techniques.md](docs/m4l_advanced_ui_techniques.md),
[docs/ui_goodies_and_graphics_pipeline.md](docs/ui_goodies_and_graphics_pipeline.md),
and [docs/ui_premium_playbook.md](docs/ui_premium_playbook.md).

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

## Reverse engineering

Capture an existing `.amxd` (yours or a third party's) into a Python rebuild
script, at increasing levels of abstraction -- from an exact structural
mirror up through a version that collapses recognized patterns back into
`m4l-builder` recipe/helper calls:

```python
from m4l_builder import snapshot_from_amxd, generate_semantic_python_from_snapshot

snapshot = snapshot_from_amxd("path/to/device.amxd")
source = generate_semantic_python_from_snapshot(snapshot)
```

The same pipeline can mine a whole directory of external devices into a
structured corpus report -- ranked rebuild candidates, motif/object
frequencies, family groupings for versioned variants, and generated
per-device fixtures (snapshot, knowledge, and all four codegen tiers) for
batch analysis:

```python
from m4l_builder import analyze_amxd_corpus, corpus_report_markdown

report = analyze_amxd_corpus("/path/to/amxd-corpus")
markdown = corpus_report_markdown(report)
```

See [docs/reverse_engineering.md](docs/reverse_engineering.md) for the full
pipeline (live-bridge snapshots, corpus mining, family/lane comparisons,
mapping-product briefs) and the `tools/` scripts that wrap it.

## LiveMCP bridge (optional)

Entirely optional: `enable_livemcp_bridge` embeds a self-contained JSON-lines
TCP bridge (pure stdlib -- no LiveMCP install required by the library itself)
inside a device's own `.amxd`, so a compatible external tool -- LiveMCP is
one -- can inspect and edit that device's patcher live in Ableton.

```python
from m4l_builder import AudioEffect, enable_livemcp_bridge, device_output_path

device = AudioEffect("Bridge Ready", width=420, height=180)
enable_livemcp_bridge(device, include_ui=True)
device.build(device_output_path("Bridge Ready"))
```

That device will write the `.amxd` plus the bridge sidecars next to it during
`build()`. The bridge is local-only and device-local: it gives LiveMCP access to
that device's patcher, not to arbitrary third-party Max devices in the set. See
[docs/livemcp_max_bridge.md](docs/livemcp_max_bridge.md) for the full contract.

## Plugin workspaces

This framework repo does not keep buildable plugin scripts in-tree -- the
maintainer's own concrete devices live in a private repo, not published.
There's no dependency on that repo (or any other) to use `m4l-builder`:
write your own `build.py` anywhere and `import m4l_builder`.

## Architecture / internals

Notes on how the library itself is organized, for anyone extending it rather
than just building devices with it.

### Engines layer

`src/m4l_builder/engines/` (68 modules) holds the jsui/v8ui JS generators
described above, plus two shared-scaffold modules that are not generators
themselves:

- [`engines/design_system.py`](src/m4l_builder/engines/design_system.py) —
  shared MGraphics drawing helpers and cursor handling that the hero displays
  embed, so a visual change lands once instead of being hand-copied. Sidecar
  `.js` filenames are content-addressed by `js_sidecar_name()` (stem + BLAKE2b
  hash of the JS source): Max caches jsui/v8ui sidecars by filename for the
  whole Live session, so editing the JS without renaming the file would
  otherwise keep serving the stale cached version.
- [`engines/interaction_core.py`](src/m4l_builder/engines/interaction_core.py)
  — the shared JS interaction scaffold (pointer-coordinate resolvers, `clamp`,
  `onresize`, plot-geometry accessors) that used to be hand-copied verbatim
  into every interactive display engine.

### `patcher_walk.py`

[`patcher_walk.py`](src/m4l_builder/patcher_walk.py) is the one shared
implementation of the box/line traversal dance (`iter_boxes`, `boxes_by_id`,
`iter_patchlines`, `unwrap_box`) that used to be hand-rolled independently
throughout the library. It accepts a live `Device`/`GraphContainer`, a raw
patcher/snapshot dict, or an already-extracted list of wrapper entries, so the
same functions serve live authoring code and reverse-engineering/corpus code
alike.

### `idioms.py` and `bridge_probe.py`

Root-level helper modules: [`idioms.py`](src/m4l_builder/idioms.py) wraps Max
wiring patterns that are easy to get subtly wrong — `expr_cond` for branchless
`expr` conditionals (Max `expr` has no ternary), plus `debounce`,
`dedupe_value`, `control_smooth`, `init_prime`, `corr_readout`, and
`assign_parameter_banks` — each one encodes a trap that previously shipped as
a real bug. [`bridge_probe.py`](src/m4l_builder/bridge_probe.py) is shared
scaffolding for devices that embed a LiveMCP bridge probe
(`register_bridge_probe_assets`, `add_bridge_probe_runtime`), factored out
after two EQ devices each hand-copied the same ~76 lines.

### Facade + introspection pattern

`m4l_builder/__init__.py` and `m4l_builder/builder/__init__.py` don't
hand-maintain their own export lists — both build their public surface from
shared metadata in [`_exports.py`](src/m4l_builder/_exports.py) and resolve
names lazily via module-level `__getattr__`/`__dir__`, so importing
`m4l_builder` doesn't eagerly load reverse-engineering or corpus-analysis
tooling.

Several large modules are themselves thin facades that re-export from a set
of split implementation modules, so existing `from m4l_builder.X import Y`
code keeps working unchanged: `recipes.py` (from `recipes_stages.py`,
`recipes_layout.py`, `recipes_widgets.py`, `recipes_io.py`), `reverse.py`
(from `reverse_snapshot.py`, `reverse_patterns.py`, `reverse_analysis.py`,
`reverse_codegen.py`), and `corpus_analysis.py` (from `_corpus_helpers.py`,
`_corpus_file.py`, `_corpus_ranking.py`, `_corpus_mapping.py`,
`_corpus_dossier.py`, `_corpus_aggregate.py`, `_corpus_markdown.py`).

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

Browse the [catalog](docs/catalog.md) for every DSP block, UI widget, recipe,
theme, and engine at a glance, or the full [API docs](docs/api.md).

## License

MIT
