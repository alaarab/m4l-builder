# Ableton UI Reference Matrix

This matrix ties the Ableton reference order to concrete lessons and repo
translation targets.

Use it to decide which reference device should inform a given sprint or lane.

## Reference Order

1. `EQ Eight`
2. `Spectrum`
3. `Auto Filter`
4. `Utility`
5. `Glue Compressor`
6. `Simpler`
7. `Wavetable`
8. `Echo`

## Matrix

| Reference | Product Role | Primary UI Lessons | Strongest Repo Translation |
| --- | --- | --- | --- |
| `EQ Eight` | fast mix EQ | graph-first editing, selected-band clarity, contextual rails | `Parametric EQ`, `Linear Phase EQ` |
| `Spectrum` | measurement tool | analyzer truth, low-chrome hierarchy, explicit smoothing semantics | `Spectrum Analyzer`, EQ overlays |
| `Auto Filter` | performance filter | one central gesture, readable modulation, musical control density | `Ladder Filter` |
| `Utility` | compact utility | chain-view discipline, compact identity, obvious state | all flagship compact surfaces |
| `Glue Compressor` | bus dynamics tool | threshold-centric hierarchy, gain-reduction visibility, focused utility state | compressor lanes, meter and reduction displays |
| `Simpler` | dual-surface instrument | compact-vs-editor split, waveform-led editing, sample identity | `Granular Sampler`, future sampler lanes |
| `Wavetable` | complex synth editor | layered editing without chaos, macro vs deep editor separation, modulation visibility | wavetable and spectral editor lanes |
| `Echo` | creative delay | multi-mode depth with calm hierarchy, character controls, spatial feedback readability | delay and modulation-heavy effect lanes |

## Translation Rules

- Do not copy visual styling only. Copy interaction logic.
- The reference device should sharpen one product question at a time.
- If two references disagree, choose the one that matches the repo lane’s
  product role.

## Current Repo Mapping

### Parametric EQ

- first reference: `EQ Eight`
- supporting reference: `Spectrum`

### Linear Phase EQ

- first reference: `EQ Eight`
- supporting reference: `Spectrum`

### Spectrum Analyzer

- first reference: `Spectrum`
- supporting reference: `EQ Eight` for overlay behavior

### Ladder Filter

- first reference: `Auto Filter`
- supporting reference: `Utility` for compact restraint

### Granular Sampler

- first reference: `Simpler`
- supporting reference: `Utility` for compact clarity

## When To Introduce The Later References

- `Glue Compressor`: when gain-reduction visibility and dynamics-product
  hierarchy become a real repo lane, or when meter semantics need a stronger
  benchmark
- `Simpler`: during dual-surface shell work and waveform-editor decisions
- `Wavetable`: when a lane needs deep editor density without losing coherence
- `Echo`: when a lane needs richer multi-mode or spatial feedback UI
