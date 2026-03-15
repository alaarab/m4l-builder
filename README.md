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

## Flagship UI workflow

For Ableton-style flagship device work, the repo now includes a shared UI
practice and review set:

- [docs/ableton_ui_playbook.md](docs/ableton_ui_playbook.md): shared UI rules
  for primary surfaces, contextual editing, compact behavior, and analyzer
  semantics
- [docs/ableton_ui_review_checklist.md](docs/ableton_ui_review_checklist.md):
  weekly scoring rubric
- [docs/ableton_ui_90_day_sprint.md](docs/ableton_ui_90_day_sprint.md): the
  execution guide for the 12-week Ableton UI sprint
- [docs/ableton_ui_baseline_audit.md](docs/ableton_ui_baseline_audit.md):
  starting assessment of the current flagship lanes
- [docs/ableton_ui_tracker.md](docs/ableton_ui_tracker.md): week-by-week sprint
  status and artifact tracking
- [docs/ableton_ui_scoreboard.md](docs/ableton_ui_scoreboard.md): conservative
  baseline scoring for current flagship lanes
- [docs/ableton_ui_reference_matrix.md](docs/ableton_ui_reference_matrix.md):
  reference-device order and repo translation map
- [docs/ui_validation/README.md](docs/ui_validation/README.md): validation-note
  workflow for in-Live review

This sits on top of the existing plugin design docs in `plugins/*/README.md`.

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

### Reverse engineering snapshots

You can also capture a low-level snapshot from an `.amxd` and emit a starter
Python rebuild script:

```python
from m4l_builder import (
    snapshot_from_amxd,
    extract_snapshot_knowledge,
    generate_python_from_snapshot,
    generate_builder_python_from_snapshot,
    generate_optimized_python_from_snapshot,
    generate_semantic_python_from_snapshot,
)

snapshot = snapshot_from_amxd("path/to/device.amxd")
knowledge = extract_snapshot_knowledge(snapshot)
exact_source = generate_python_from_snapshot(snapshot)
builder_source = generate_builder_python_from_snapshot(snapshot)
optimized_source = generate_optimized_python_from_snapshot(snapshot)
semantic_source = generate_semantic_python_from_snapshot(snapshot)
```

This is fidelity-first: the exact generator preserves the patcher structure and
recovered sidecars, the builder generator emits nicer `add_*` style code when
the snapshot is recognized, the optimized generator can collapse known
`m4l-builder` DSP blocks back into helper calls like `param_smooth(...)` or
`delay_line(...)`, `transport_lfo(...)`, and similar helpers, and larger
recognized stages back into recipe calls like `gain_controlled_stage(...)`,
`dry_wet_stage(...)`, `tempo_synced_delay(...)`, `midi_note_gate(...)`, or
`transport_sync_lfo_recipe(...)`. The semantic generator sits one level above
that exact-safe path: it can also normalize safe non-canonical Live API
clusters into helper calls while leaving manual-review cases expanded.
The builder path also rebuilds common UI/support-file
objects semantically, including `jsui`, `v8ui`, `bpatcher`, `fpic`,
`multislider`, `textbutton`, `umenu`, `radiogroup`, `live.step`, `live.grid`,
`kslider`, and related display widgets, while the optimized path only collapses
to helper/recipe calls when the recognized structure is safe to regenerate.
The reverse analysis also exposes generic Max motifs from external devices, such
as named send/receive buses, Live API control clusters, and embedded patcher
hosts, so corpus mining is useful even when a device was not built with
`m4l-builder`.
It now also detects non-LiveAPI controller structures that dominate public
devices: dispatcher clusters (`route` / `sel` / `gate` / `switch` with trigger
fan-out), scheduler chains (`loadbang`, `deferlow`, timed dispatch), and
state-bundle/list utilities (`pack`, `pak`, `unpack`, `zl*`).
For deeper devices, the motif layer now also detects advanced sample/granular
pipelines such as `sample_buffer_toolchain` (for `buffer~`, `info~`, `peek~`,
`live.drop`, and related file/visualization shells) and
`gen_processing_core` (for `gen~` plus attached buffer/trigger/routing
structure), which makes devices like Granulator III much less opaque at the
embedded-patcher level.
Those motifs also feed semantic grouping now: extracted subpatchers can be
lifted as `sample_file_handling_shell`, `sample_visualization_shell`,
`sample_playback_shell`, or `buffered_gen_capture_shell` instead of staying as
anonymous raw object clusters.
Live API motifs now also classify small controller archetypes such as
`parameter_probe`, `tempo_observer`, `transport_state_observer`,
`device_active_state`, and `track_management`, which makes public-device mining
much more actionable than raw operator counts alone.
The optimized rebuild path now collapses canonical `live.path` /
`live.object` / `live.observer` / `live.thisdevice` structures back into
semantic helpers like `live_object_path(...)`, `live_parameter_probe(...)`,
`live_observer(...)`, `live_state_observer(...)`, `live_set_control(...)`,
`live_thisdevice(...)`, and `device_active_state(...)` when the emitted helper
boxes match the source
exactly. `live_observer(...)` now also supports the direct
`live.path -> live.observer` topology used by many external devices, plus
property-message binding in both topologies for semantic rewrites.
`live_parameter_probe(...)` now also supports object-only parameter probes with
optional `route` fan-out and `t ...` trigger wrappers, which lets the reverse
path recover common external-device `live.object -> route` probe clusters
instead of leaving them as opaque raw boxes.
`device_active_state(...)` now preserves both the normal
`prepend active -> live.thisdevice` toggle path and external variants that feed
`live.thisdevice` outlet state back into `prepend active`, which moved another
external controller motif out of manual-review territory.
`live_state_observer(...)` captures the initialized direct-observer controller
shape used by external devices such as MoireArp: `live.thisdevice -> t b b ->
live.path/property -> live.observer -> t i i -> sel 0`.
See [docs/reverse_engineering.md](docs/reverse_engineering.md).

If you already captured a live bridge-enabled device through LiveMCP, you can
also normalize that data with `snapshot_from_bridge_payload(...)` and feed it
into the same pipeline.

You can also mine a whole directory of external `.amxd` files into a structured
corpus report:

```python
from m4l_builder import analyze_amxd_corpus, corpus_report_markdown

report = analyze_amxd_corpus("/path/to/amxd-corpus")
markdown = corpus_report_markdown(report)
```

That report now includes helper/recipe hits, semantic Live API helper
recoveries, non-exact Live API helper opportunities plus blocker reasons,
generic motif frequencies, object-name frequencies, control-class
distributions, display-role counts across the corpus, and a ranked
`reverse_candidates` list that surfaces which external devices are currently the
best targets for further semantic work. The report also includes
`reverse_candidate_families`, which collapses versioned variants into device
families so the queue is not dominated by duplicate builds of the same patch,
plus `reverse_candidate_family_profiles`, which aggregate motif/object signals
across those variants.

If you want to focus one semantic lane at a time, build a detailed family
profile with stable-vs-variable signals:

```python
from m4l_builder import analyze_amxd_corpus, build_reverse_candidate_family_profile

report = analyze_amxd_corpus("/path/to/amxd-corpus")
profile = build_reverse_candidate_family_profile(report, "zs-Knobbler3")
```

That family profile separates stable motif/object/archetype signals from
variant-only noise, which makes it much easier to decide what should become a
new helper or normalization rule.

Family profiles also infer `semantic_targets` and `next_work_items` from those
stable signals, so the reverse queue can move from “interesting family” to
“normalize this shell next” without re-reading the raw motif tables each time.

At the snapshot level, `extract_controller_shell_candidates(...)` now surfaces
controller-oriented semantic targets such as `controller_surface_shell` and
`sequencer_dispatch_shell`, while `extract_embedded_ui_shell_candidates(...)`
surfaces exact embedded-host shells for subpatcher and `bpatcher` boxes.
Both `generate_optimized_python_from_snapshot(...)` and
`generate_semantic_python_from_snapshot(...)` now use those candidates to call
reusable package helpers in the emitted script instead of leaving every shell
box flattened into the top-level build sequence.
The factory-first reverse lane also promotes exact shell helpers such as
`embedded_ui_shell_v2(...)`, `named_bus_router(...)`,
`init_dispatch_chain(...)`, `poly_shell(...)`, and `poly_shell_bank(...)`,
while keeping
first-party-only structures such as `first_party_api_rig`,
`first_party_abstraction_host`, and `building_block_candidate` as semantic
groupings until they prove reusable. Factory-lane mining also tracks repeated
internal `M4L.*` abstraction hosts like `M4L.bal2~` and `M4L.gain1~`, so
first-party building blocks can be decomposed into abstraction-backed clusters
before they fall back to whole-device grouping. On the current Ableton factory
pack corpus, the strongest abstraction families are `balance_shell`,
`gain_shell`, `api_internal_shell`, `envelope_follower_shell`, and
`pan_shell`, which gives the next reverse work a much clearer target than
treating every Building Tools device as a one-off block. Semantic output now
uses those family labels directly on recovered first-party abstraction groups,
so devices like `Max BalanceStereo`, `Max GainStereo`, and `Max PanStereo` read
as `balance_shell`, `gain_shell`, and `pan_shell` instead of one generic
factory-host bucket.

The reverse lane can also now collapse repeated `poly~` editor shells into a
single `poly_shell_bank(...)` helper when a device exposes the same voice-edit
host repeatedly with numbered bus wiring. On the semantic side, those exact
banks can be lifted one step further into a `poly_editor_bank` grouping. That
pattern now lands on devices like `[dnksaus] Rnd Gen v2.2`, where the old
output emitted nine separate `poly_shell(...)` calls and the new output emits
one grouped bank in optimized mode and one `poly_editor_bank` semantic group in
semantic mode.

The knowledge manifest can also now expose behavior-level hints from that same
structure. For devices like `Rnd Gen`, the reverse layer can infer summaries
such as `multi_lane_mapping_bank`, `manual_or_midi_trigger_mode`,
`mapping_session_controller`, and the combined `mapped_random_control_device`
hint even when the deepest sidecar logic is still missing.

The knowledge manifest also now includes `named_bus_networks`, which groups
same-name send/receive fabrics across the root patcher and any embedded
subpatchers that expose their internals.

The corpus report also now carries `source_lane_profiles`, so factory packs,
public internet corpora, and site-lead discovery lanes can be compared without
manually splitting the dataset first:

```python
from m4l_builder import analyze_amxd_corpus, source_lane_profiles_markdown

report = analyze_amxd_corpus("/path/to/amxd-corpus")
markdown = source_lane_profiles_markdown(report["source_lane_profiles"])
```

If you keep public and factory corpora in separate roots, compare them
directly:

```python
from m4l_builder import analyze_amxd_corpus, build_corpus_comparison, corpus_comparison_markdown

comparison = build_corpus_comparison({
    "public": analyze_amxd_corpus("/path/to/public-corpus"),
    "factory": analyze_amxd_corpus("/path/to/factory-packs"),
})
markdown = corpus_comparison_markdown(comparison)
```

And for a fixed proof set, you can build reference-device dossiers that measure
raw `add_box(...)` fallback, helper-call recovery, and overall structural lift
across semantic generation:

```python
from m4l_builder import build_reference_device_dossiers

dossiers = build_reference_device_dossiers([
    "/path/to/Max DelayLine.amxd",
    "/path/to/Poly Vocoder.amxd",
])
```

For local research batches, the repo also ships a helper script:

```bash
uv run python tools/mine_amxd_corpus.py /path/to/amxd-corpus
```

To turn a local corpus into a reusable reverse-engineering fixture set, build a
manifest plus per-device snapshot/codegen artifacts:

```python
from m4l_builder import build_corpus_manifest, run_corpus_fixture

manifest = build_corpus_manifest("/path/to/amxd-corpus", stable_sample_size=12)
results = run_corpus_fixture(manifest, "/tmp/amxd-fixture", selection="stable")
```

That fixture writes, for each selected device:

- `snapshot.json`
- `knowledge.json`
- fidelity-first `exact.py`
- builder-style `builder.py`
- exact-safe `optimized.py`
- rewrite-oriented `semantic.py`

If one generation mode fails on a particular external device, the fixture run
keeps going and records the per-mode error instead of aborting the whole batch.

There is also a repo helper script for this:

```bash
uv run python tools/build_corpus_fixture.py /path/to/amxd-corpus /tmp/amxd-fixture
```

Selections can target whole families as well as sample sets, for example
`--selection family:zs-Knobbler3`. They can also target the new lane/pack
metadata, for example `--selection lane:factory`,
`--selection pack:M4L Building Tools`, or
`--selection pack_section:M4L Building Tools / API`.

For a focused family dossier, the repo also ships:

```bash
uv run python tools/build_family_report.py /path/to/amxd-corpus zs-Knobbler3
```

There are also dedicated helpers for lane comparison and fixed proof sets:

```bash
uv run python tools/build_source_lane_report.py /path/to/amxd-corpus /tmp/lane-report.md
uv run python tools/build_corpus_comparison_report.py /tmp/comparison.md public=/path/to/public-corpus factory=/path/to/factory-packs
uv run python tools/build_reference_dossiers.py /tmp/reference-dossiers.md /path/to/Max\ DelayLine.amxd
```

### LiveMCP bridge embedding

If you want a device to expose its own native Max editing bridge to LiveMCP,
embed the bridge directly into that device:

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
| `livemcp_bridge_demo.py` | Compact reference device with embedded LiveMCP bridge |
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
