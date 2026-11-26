# Offline render

A gen~ codebox that fails to compile in Live doesn't raise an error. The device
loads, the meters move, and the audio comes out exactly as it went in. The
same goes for a parameter that never reaches the DSP. `m4l_builder.render`
runs a device's audio path in Python, without Live, so you can hear what the
DSP does and assert that it actually processes.

```python
from m4l_builder.render import audit, check_not_dry, render

result = render(device, "noise", params={"Width": 1.0}, out="wide.wav")
assert check_not_dry(result), check_not_dry(result).detail

# or the whole battery, in a test:
report = audit(device, engaged={"Width": 1.0}, bypass={"Width": 0.5})
assert report, str(report)
```

From the command line it's [`m4l render`](cli.md#m4l-render).

## What gets rendered

`render(source, signal, ...)` takes a `Device` or the path of a built `.amxd`
(loose, with its `.gendsp` files next to it, or frozen). It traces the audio
path backwards from `plugout~` and runs:

| On the path | How |
|---|---|
| `plugin~` | the input signal |
| `gen~` with an embedded or `.gendsp` patcher | its codebox, run by `gen_sim`; the patcher must be one codebox wired to `in N` / `out N` objects (what `Device.embed_gendsp` and `Device.add_gendsp` build). Direct `in` to `out` wires pass audio through. |
| `*~ +~ -~ /~ !-~ !/~` | with an argument, a signal, or a control value on the right inlet |
| `line~`, `sig~` | a control value turned into a signal |
| `live.dial`, `live.numbox`, `live.slider`, `live.toggle`, `live.tab`, `live.menu`, `live.text` | the parameter's value (outlet 0) |
| `pack`/`pak`, `prepend`/`append`, `t f`, `f`, `dbtoa`, `atodb`, `+ - * / !- !/` with an argument, `scale` (four arguments), `loadmess` | evaluated once, on the parameter values |

A `prepend NAME` message into a `gen~` sets that gen `Param`, which is how
`Device.bind_gen_param` wires a dial to the DSP.

Anything else on the path (an MSP object the renderer doesn't model, a gen
operator `gen_sim` doesn't simulate, a feedback loop with no delay, a `gen~`
with a flat `code` attribute that Max would ignore) raises `RenderError`
naming the box. An unsupported device is never reported as passing.

Two things are approximate, and are listed in `result.notes` whenever they
apply:

- `line~` holds its target from the first sample. The short ramp Live plays
  when a parameter changes is not rendered.
- gen constructs `gen_sim` only approximates: `noise()` (a seeded Python
  generator, statistically the same but not sample-identical to gen's) and
  `Delay` reads with `interp="cubic"` (4-point Lagrange, not checked against
  gen's own kernel). Pass `strict=True` to refuse them instead.

`result.notes` also says when a parameter you set doesn't reach the audio
path, and when a value was outside the parameter's range and got clamped.

## Parameters

`params` takes names as you'd see them: a Live parameter's long name, short
name, varname or box id. Enum parameters (`live.tab`, `live.menu`) also take
their labels. A gen `Param` can be set directly as `BOX.param`, or just
`param` when only one gen~ declares it. A directly set gen Param wins over
whatever the patch sends it. Parameters you don't set keep their initial
values, as they would when the device loads. An unknown name raises
`RenderError` listing the names the device has.

## Signals and WAV files

`signal` is a WAV path, one of `"sine"`, `"noise"`, `"impulse"`, `"silence"`,
or a list of channels (lists of floats). Generated signals take `seconds`,
`level_db` (peak dBFS, default -6), `freq` (sine) and `seed` (noise). Sine and
noise differ between channels, so a width or panning effect has side content
to act on; a mono WAV feeds both `plugin~` channels.

`read_wav` reads PCM (8 to 32-bit) and 32/64-bit float WAVs. `write_wav` and
`result.write()` write 16 or 24-bit PCM and return how many samples had to be
clipped. Levels in the summary come from the float output, before clipping.

## Checks

Each check returns a `Check` that is truthy when it passes and carries a
`detail` string.

| Check | Passes when |
|---|---|
| `check_not_dry(result)` | on at least one channel, output minus input is no more than 60 dB below the input |
| `check_identity(result, tolerance=1e-6)` | every output sample equals the input |
| `check_silent(result, floor_db=-120)` | the output peak stays under the floor (render silence) |
| `check_finite(result)` | no NaN or infinity in the output |

`audit(device, engaged=..., bypass=...)` renders the device five or six times
and returns the checks as one report: not dry with `engaged` parameters, silent
in gives silent out, no NaN/Inf with full-scale noise, sine and impulse, and
(when you pass `bypass`) identity with `bypass` parameters.

`summarize(channels, samplerate)`, or `result.summary()` for both sides,
reports per channel the RMS and peak in dBFS, a count of NaN/Inf samples, and
the mean power of six coarse bands (dBFS, where a full-scale sine reads -3)
from Hann-windowed FFT frames.

## Which gen snippets run

`gen_sim` covers most of the library's own snippets. To see the current list:

```bash
uv run python tools/gen_sim_coverage.py
```

It prints each function in `gen_snippets`, `gen_character` and `gen_stateful`
as `renders`, `renders (approximate: ...)`, or `refused:` with the reason
(a `Buffer`, a `for` loop, `phasor()`, a brace-less `if`).
