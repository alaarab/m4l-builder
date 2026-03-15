# Mapping / Modulation Family Notes

This note captures the current product-level read of the mapping/modulation
family lane after pressure-testing five concrete devices:

- `[dnksaus] Rnd Gen v2.2`
- `Macro Randomizer`
- `Expression Control`
- `Device Randomizer`
- `LFO MIDI`

The point is not to preserve every box-level detail. The point is to answer the
questions that matter when designing a better device on purpose.

The repo now exposes that same logic programmatically through
`build_mapping_product_briefs(...)` and `mapping_product_briefs_markdown(...)`,
so this note is no longer just hand-written interpretation. It is the prose
shape the corpus/report layer is trying to produce automatically.

One important qualifier: broad corpora are still heuristic pressure, not the
final truth for this lane. Low-level traces like periodic engines or parameter
API shells show up in lots of non-mapper devices, so product-level categories
should be validated against a focused proof set before they are treated as
stable design references.

## Stable semantic ladder

Current progression from lower-level structure to higher-level product meaning:

- `poly_editor_bank`
  - repeated editor shells with shared lane wiring
- `mapping_workflow_shell`
  - repeated editor bank plus explicit trigger/session shells
- `mapped_modulation_bank`
  - multiple modulation lanes exposed as one bank
- `lfo_modulation_source`
  - periodic waveform-based modulation source with sync/time-mode structure
- `device_parameter_randomizer`
  - selected-device parameter scanner plus triggered randomization workflow
- `random_modulation_mapper`
  - modulation bank plus explicit trigger sources and randomization logic
- `triggered_parameter_mapper`
  - mapping workflow plus trigger routing plus session lifecycle

## Proof set

### `[dnksaus] Rnd Gen v2.2`

- Behavior hints:
  - `mapped_random_control_device`
  - `mapping_session_controller`
  - `manual_or_midi_trigger_mode`
  - `multi_lane_mapping_bank`
  - `dynamic_panel_relayout`
- Mapping behavior traces:
  - `modulation_output_bank`
  - `trigger_source_cluster`
  - `mapping_session_lifecycle`
  - `lane_update_paths`
  - `hidden_mapping_engine`
- Semantic candidates:
  - `mapped_modulation_bank`
  - `random_modulation_mapper`
  - `triggered_parameter_mapper`

### `Macro Randomizer`

- Behavior hints:
  - none required
- Mapping behavior traces:
  - `modulation_output_bank`
  - `trigger_source_cluster`
  - `random_value_generation`
  - `lane_update_paths`
- Semantic candidates:
  - `mapped_modulation_bank`
  - `random_modulation_mapper`

### `Expression Control`

- Behavior hints:
  - none required
- Mapping behavior traces:
  - `modulation_output_bank`
  - `lane_update_paths`
- Semantic candidates:
  - `mapped_modulation_bank`

### `Device Randomizer`

- Behavior hints:
  - none required
- Mapping behavior traces:
  - `parameter_target_scan`
  - `trigger_source_cluster`
  - `periodic_modulation_core`
- Semantic candidates:
  - `device_parameter_randomizer`

### `LFO MIDI`

- Behavior hints:
  - none required
- Mapping behavior traces:
  - `periodic_modulation_core`
  - `trigger_source_cluster`
- Semantic candidates:
  - `lfo_modulation_source`

## What those devices are actually closer to

### `Rnd Gen`

Closer to:

- a mapper with random mode
- an `Expression Control` descendant with target assignment and trigger/session
  management

Not especially close to:

- a synth
- an LFO device
- a Shaper-like envelope tool

Its distinguishing idea is that the random source is tied to a mapping workflow
and lane/session state, not just free-running modulation output.

### `Macro Randomizer`

Closer to:

- a random modulation bank
- a triggerable/clockable source of output values

Not especially close to:

- a true mapper
- a parameter-assignment workflow

Its main job is generating fresh values for a fixed bank of outputs.

### `Expression Control`

Closer to:

- a manual modulation bank
- a clean set of exposed output controls

Not especially close to:

- a random generator
- a mapping session device

Its main job is exposing stable lanes, not deciding values or assigning targets.

### `Device Randomizer`

Closer to:

- a selected-device parameter randomizer
- a triggerable “scramble this device’s parameters” controller

Not especially close to:

- a plain modulation bank
- an LFO source
- a target-assignment mapper like `Rnd Gen`

Its main job is discovering parameters on the current device and applying
randomized value updates under explicit trigger/control rules.

### `LFO MIDI`

Closer to:

- an LFO modulation source
- a periodic waveform generator with sync/time-mode behavior

Not especially close to:

- a mapper
- a parameter randomizer
- a bank of manually exposed outputs like `Expression Control`

Its main job is generating periodic modulation with waveform/time controls, not
scanning or assigning target parameters.

## Controls needed to recreate this family cleanly

If the goal is to build a better descendant rather than clone every patch, the
core control set is:

- lane count
- target assignment per lane
- lane enable / lock / clear
- trigger mode:
  - manual
  - MIDI-triggered
  - auto/clocked
- randomization range / depth
- randomization shape or mode
- smoothing or slew
- probability / chance
- mapping-session controls:
  - start map
  - done map
  - clear map
  - refresh local state

The details can change, but that control surface is the actual product.

For `Device Randomizer` specifically, the essential layer also includes:

- selected-device scope
- parameter include / exclude rules
- settings store / recall

For `LFO MIDI`, the essential layer also includes:

- waveform selection
- tempo-sync / time mode
- hold / retrigger
- smoothing / jitter

## Essential vs accidental complexity

Essential:

- multiple lanes
- some notion of output or mapped target per lane
- trigger sources
- value generation or transformation
- per-lane update path
- target/session state when the device is a mapper

Accidental:

- raw repeated `poly~` editor plumbing
- bus naming details like `---m1..9`
- UI scripting for panel movement
- duplicated low-level send/receive routing
- whichever hidden sidecars happen to implement the current internal engine

That accidental layer matters for exact reverse engineering, but it should not
drive a cleaner successor design.

## Current promotion decision

Promoted as stable semantic candidates:

- `mapped_modulation_bank`
  - stable across `Rnd Gen`, `Macro Randomizer`, and `Expression Control`
- `lfo_modulation_source`
  - stable on waveform/time-driven modulation devices such as `LFO MIDI`
- `device_parameter_randomizer`
  - stable on selected-device scan-and-randomize controllers such as
    `Device Randomizer`
- `random_modulation_mapper`
  - stable across `Rnd Gen` and `Macro Randomizer`
- `triggered_parameter_mapper`
  - currently strongest on `Rnd Gen`; keep treating it as a higher-level
    semantic grouping, not a public package helper

## Design implication

If asked to build a better version of `Rnd Gen`, the right starting point is
not “reverse every hidden sidecar first.” It is:

1. start from a `mapped_modulation_bank`
2. add a `random_modulation_mapper` layer
3. add `triggered_parameter_mapper` behavior only where target assignment and
   session state are actually needed
