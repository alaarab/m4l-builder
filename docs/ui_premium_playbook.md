# Premium M4L UI Playbook — build devices that look like the downloads

> Written after measuring the UI of the commercial devices we cloned (Superberry,
> Chiral, AS Console, stranular, Particle Reverb, Rainbow, Roulette). The point of
> this doc: my first authored devices (Channel Strip, Halo) used **bare `add_dial` +
> one flat `add_panel` + plain `add_comment`** — the *primitive* path — and looked
> cheap. The downloads never do that. This is the grammar they actually use, mapped
> to the kit primitives that already exist (I just wasn't using them).

## What the downloads actually do (MEASURED, per device)

| Device | The premium engine | Counts |
|--------|--------------------|--------|
| **Superberry** | custom-PAINTED native controls + 2 scope heroes | 34 `jspainterfile`, 14 dial, 11 `live.line`, 2 jsui (lfoscope, superscope), `<Monospaced>` LCD numbers |
| **Chiral** | painted controls + a big wave hero + lots of jsui | 11 `jspainterfile`, **9 jsui**, 13 `live.line`, wave_display 250×91 hero |
| **AS Console** | **fpic image assets** + bpatcher modules + dense dividers | **33 `fpic`**, **14 `bpatcher`**, **75 `live.line`**, 19 `live.tab`, 24 dial |
| **Rainbow** | **17 bpatcher modules** + 9 big spectral jsui displays | 17 `bpatcher`, 9 jsui (448×131 displays), 12 panel |
| **Roulette** | **gradient fills** + a grid + a notes hero | 24 gradient `bgfillcolor`, live.grid, jsui hero |
| **stranular** | bpatcher modules + jsui grain displays | 6 `bpatcher`, 4 jsui |

**The throughline:** every premium device has (1) a **jsui/v8ui HERO visualization**,
(2) **custom-drawn controls** (painted `jspainterfile`, baked `fpic`, or v8ui), (3) a
**non-flat background**, (4) **structural `live.line` dividers** carving sections, (5)
**monospaced LCD-style numeric readouts**. My devices had zero of these.

## The 6 non-negotiables — a device is NOT done without all six

1. **A HERO display.** The centerpiece visualization, top or center, ≥ ~40% of width.
   It is what makes a device read as "designed," not a control rack. Pick the one that
   *shows the DSP*: a filter/EQ device → `filter_curve`/`eq_curve`; comp → `transfer_curve`
   + `level_history`; reverb → a decay/size bloom or `energy_history`; LFO/mod → `lfo_display`;
   granular → `grain_display`; saturator → `waveshape_curve`/`transfer_curve`. The kit ships
   **35+** of these in `engines/`. Feed it the live param values (control `_dial` outlet → hero inlet).
2. **Custom-painted controls — NEVER bare `add_dial`.** Use `add_custom_knob` (v8ui knob ⇄
   hidden `live.dial`, with `**Theme.knob_bg_args(H)`), `add_custom_toggle`, `add_custom_segment`,
   `add_cycle_button` (glyphs). For a native control that must stay native, paint it with
   `paint_control(box_id, "x.js", painter_js=...)` (the Superberry `jspainterfile` route).
3. **A gradient / material background — NEVER a single flat `add_panel`.** Use a full-device
   `add_v8ui("bg", [0,0,W,H], js_code=panel_bg_js(**Theme.panel_bg_kwargs()), background=1,
   ignoreclick=1)`. Add framed sub-panels with `border=1, rounded=6` for sections.
4. **Structural dividers + sections.** Carve the face with `live.line` dividers and framed
   panels (AS Console uses 75 lines). Group controls into labelled sections, not one row.
5. **Monospaced LCD readouts.** Numeric values in `<Monospaced>` (or the `add_draggable_readout`
   LCD) — the gradient-filled "lit digit" look, not plain Ableton text. `add_custom_knob` bakes
   a readout into the knob; use `unitstyle` + `decimals` + the `fmtUnit` formatter for kHz/dB/%.
6. **Two-accent theme, applied.** `AudioEffect(..., theme=RUPTURE)` (or AMBER/STRANULAR). Primary
   accent = the value arcs/dials; **accent2 = selection/secondary** (`A2 = theme.accent2_str()`),
   used for a second control aisle / the hero playhead / selected states.

## Download technique → kit primitive (use these, they already exist)

| Download technique | Kit primitive |
|--------------------|---------------|
| jsui hero (scope/wave/spectrum/curve) | `engines/<x>_display.py` / `<x>_curve.py` (35+) via `add_jsui`/`add_v8ui` |
| painted knob (`jspainterfile`) | `add_custom_knob(id, label, rect, vmin, vmax, initial, unit, decimals, accent, **knob_bg)` |
| painted toggle / glyph button | `add_custom_toggle`, `add_cycle_button`, `add_custom_segment` |
| paint a NATIVE control | `Device.paint_control` + `engines/painters.py` |
| `fpic` knob/background image | `Asset(...)` + `add_fpic` (`usepicture`/SVG) |
| gradient material panel | `panel_bg_js(**Theme.panel_bg_kwargs())` in a `background=1` v8ui |
| bpatcher DSP+UI module | `Device.add_bpatcher_module(subpatcher, ...)` (F3) |
| `live.line` dividers | `add_live_line` (thin theme-dim lines between sections) |
| LCD numeric readout | `add_draggable_readout` / `<Monospaced>` numbox / the in-knob readout |
| runtime Live-skin retint | `Device.add_theme_bus` (B1) |

## Composition recipe (the layout grammar the downloads use)

```
[ gradient v8ui background, full device ]
  TITLE (Ableton Sans Bold) + subtitle (dim)        ← top-left
  ┌─ HERO jsui ─────────────┐   ┌─ section panel ──┐
  │  the DSP visualization   │   │ custom knobs in   │   ← framed, rounded
  │  (fed by the params)     │   │ a labelled grid   │
  └──────────────────────────┘   └───────────────────┘
  live.line dividers between sections; LCD readouts under/in each knob
  two-accent: aisle A = accent, aisle B = accent2
```

## The hard gate (run before calling any device "done")

- [ ] Has a **hero jsui** ≥ ~40% width, wired to live params?
- [ ] **Zero bare `add_dial`** in presentation — all knobs are `add_custom_knob`/painted?
- [ ] Background is a **gradient v8ui**, not a single flat panel?
- [ ] At least a few **`live.line` dividers** / framed sub-panels carving sections?
- [ ] Numeric readouts are **LCD/monospaced**, not plain comments?
- [ ] `theme=` passed, **accent2 used** somewhere (selection/second aisle)?
- [ ] **Live A/B**: screenshot next to a download — does it read as the same tier?

## Anti-patterns (exactly what made Channel Strip/Halo look cheap)

- ❌ `add_dial` for every knob (stock Ableton knob look).
- ❌ One flat `add_panel(bgcolor=BG)` as the whole background.
- ❌ `add_comment` value labels instead of LCD readouts.
- ❌ **No hero display at all** — the single biggest tell.
- ❌ One undivided row of knobs — no sections, no dividers, no chrome.
- ❌ Two-accent palette imported but only the primary accent used.
