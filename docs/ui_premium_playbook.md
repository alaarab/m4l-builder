# Premium M4L UI Playbook — the Surface era

> **Rewritten 2026-07 (UI Foundations v2).** The first edition of this doc preached
> "NEVER bare `add_dial` — paint every knob." That thesis was tried and **reversed**:
> painted knobs produced dim, value-less controls, while the corpus's actual workhorse
> (premium channel-strip and EQ devices' rails) is a **bare native `live.dial` with an accent
> ring and its own persistent value**, laid out on a disciplined grid. The kit now
> encodes that grammar as the **Surface layout engine** (`m4l_builder.surface`), and
> the whole flagship fleet ships on it. This doc is the current law; the old edition's
> paint-first advice is superseded.

## The corpus principles the fleet now encodes

Distilled from a 16-device commercial teardown corpus:

- **P2 — the value of every parameter is always legible.** Persistent native value
  under/in each knob (`shownumber=1`). Hover-only `valuepopup` knobs are the
  "amateur" tell and are not expressible through Surface.
- **P3/P4 — grouped sections; caption above, bare dial, value below.** Uppercase
  7.5pt caption over a 41×35 `DIAL_COMPACT` dial on a card. Section grouping comes
  from the card chrome itself; **section header titles are OFF by default**
  (user sign-off 2026-07: "mixed on labels") and opt-in per device.
- **P5 — one disciplined accent** (occasionally a second, semantic one), tiered by
  alpha, from the shared `theme.ACCENTS` registry. Never a rainbow.
- **P10 — a hero display anchors the layout,** fed by DSP probes, in a recessed
  screen panel on the left.
- **P1 — the device reads first-party on bypass.** The **hybrid brand-dim bus**:
  baked brand accent while enabled, the user's Live-skin zombie grey when bypassed.
  Live-proven (Strip v9): the ONLY reliable runtime source is a `live.observer` on
  the Device-On parameter — `live.thisdevice`'s enable outlet fires at load only,
  and `Device.is_active` is get-only.
- **P14 — premium = restraint + coherence,** not spectacle. Flat line-art, good
  typography, exact grids. Bespoke hierarchies (Ceiling's big INPUT lever, Pocket
  Delay's bipolar hero knob, Shard's slicer deck) are kept, not flattened —
  coherence is not uniformity.

## The default path: Surface

```python
from m4l_builder.surface import Surface
from m4l_builder.theme import GRAPHITE

device = AudioEffect(NAME, width=1, height=168, theme=GRAPHITE)  # width derived
surf = Surface(device, accent="pressure")          # ACCENTS key or RGBA
hero = surf.hero("graph", width=348)               # recessed screen; hero.rect inside
device.add_v8ui("display", list(hero.rect), ...)   # or hero.v8ui(...)
card = surf.section("comp", None, cols=3)          # untitled card, cols x <=3 rows
thresh = card.dial("Threshold", "THRESH", min_val=-60, max_val=0, initial=0,
                   unitstyle=UNITSTYLE_DB)["dial"] # persistent-value cell
card.toggle("Bypass", on="BYPASSED", off="ACTIVE", shortname="Bypass")
card.menu("Filter", ["LP", "HP", "BP"])
surf.probe("gr_probe", "GRProbe", ...)             # parked diagnostic param
WIDTH = surf.finalize()                            # derives device.width, wires the
                                                   # brand-dim bus, patches the bg
device.add_width_collapse(mini_width=370, rect=[12, 1, 42, 9])  # FULL = derived
```

What Surface owns so you never hand-write it again:

| Concern | How |
|---|---|
| Rect math / pitches / margins | `native_sizes` cell grammar (CELL_W 44, COL_PITCH 48, VALUE_CELL_H 46) |
| Persistent values | every dial is a `recipes.dial_value_cell` (`shownumber=1`) |
| The 3-row rule | >3 persistent-value rows per 156px band **raises** (`SurfaceError`) |
| Device width | **derived from content** at `finalize()` — stale-width dead zones are unrepresentable |
| Bypass dim | one `live_brand_dim` bus per accent, fanned from a single receiver |
| Layout QA | `validation.layout_issues` in `Device.lint()`: control-overlap, dead-zone, width-mismatch, `setwidth`-mismatch (error) |

**Bespoke-layout devices** (deliberate hierarchies that should NOT be gridded) skip
Surface and call `device.add_brand_dim(ACCENT, [dial_ids...])` directly for the dim.
Known exclusions: Parametric/Linear-Phase EQ keep **per-band color systems** a
single-accent bus would clobber (a per-band dim awaits the F2 component bank);
painter-drawn dials (Nimbus) and dial-less meters have no applicable targets.

## Migration discipline (Live-proven across 9 devices)

1. Snapshot the shipping `.amxd`, rewrite ONLY the UI block onto Surface, capture
   `Section.dial(...)["dial"]` ids into the old variable names so DSP wiring loops
   just switch from string literals to variables.
2. **Longname gate**: `tools/longname_snapshot.py old.amxd new.amxd` must be
   identical — `parameter_longname` is the ONLY save-set identity; rects/colors/ids
   are free to change.
3. Run BOTH gates: the kit gate (`ruff` + `mypy` + `pytest` in m4l-builder) AND the
   devices suite (`uv run --project ~/Projects/m4l-builder python -m pytest tests -q`
   in Max4LivePlugins).
4. Live-verify: load on a throwaway track, meter > 0, hero animating, and a REAL
   power-button click for the dim (LiveMCP's `enable_device` is a phantom — it
   reports success without flipping Device On).
5. Re-freeze the curated dist **in the same change** (explicit UL paths — the
   no-arg freeze grabs every experiment).

## When custom drawing is still right

- **Heroes** and DSP visualizations: jsui/v8ui, always (the 35+ `engines/` displays).
- **A genuinely bespoke one-off control** (Nimbus's painter dial): `paint_control`
  (`jspainterfile`) — one painter per archetype, never the default knob path.
- Compiled displays (`spectroscope~`/`scope~`) via `add_compiled_display` /
  `Theme.scope_kwargs()` — remember a compiled box renders ABOVE any v8ui.

## The hard gate (before calling a device "done")

- [ ] Hero display wired to live DSP (probe-fed, not GUI state)?
- [ ] Every visible parameter shows a persistent value?
- [ ] Layout via Surface — or a justified bespoke hierarchy + `add_brand_dim`?
- [ ] One accent from `ACCENTS` (plus at most one semantic secondary)?
- [ ] Longname gate identical; both test gates green; layout lint clean?
- [ ] Live: audio passing, dim greys on a real power click, values legible?
- [ ] Curated dist re-frozen in the same change?
