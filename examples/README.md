# Examples

Runnable scripts that build real `.amxd` devices. Each writes to a local
`build/` folder so it works even without Ableton installed; in real use you'd
write straight into your User Library with `device_output_path("Name")`.

```bash
uv run python examples/01_gain_audio_effect.py
# wrote .../examples/build/My Gain.amxd
```

| Script | Device type | Shows |
|--------|-------------|-------|
| `01_gain_audio_effect.py` | Audio effect | Low-level API: panel, dial, raw Max objects, wiring |
| `02_generative_midi.py` | MIDI effect | The `generative_midi_stage` recipe (probabilistic, scale-quantized note generator) |
| `03_stereo_width.py` | Audio effect | The `stereo_width_stage` recipe (mid/side width control) |
| `04_midi_transformation.py` | MIDI Tool | A Live 12 MIDI Transformation via the `midi_tool_io` scaffold |

To use a device in Ableton, copy the generated `.amxd` into your User Library
(or build with `device_output_path("Name")`) and refresh Live's browser.

New here? Follow the step-by-step [getting started guide](../docs/getting_started.md).
