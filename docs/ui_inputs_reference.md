# M4L Inputs & UI Reference (mastery loop)
> **Theme naming note (T37):** examples below cite RUPTURE (a distinct-accent2 palette) for the two-hue mechanics; the shipping fleet standard is **GRAPHITE** with per-device accent overrides — both live in `theme.py PALETTES` and behave identically here.


Authoritative catalog of every Max-for-Live control/input + premium-UI rule for the
m4l-builder kit. Grounded in the **synced Max docs** (LiveMCP `search_docs` /
`get_docs_chunk`; raw HTML at `~/.cache/livemcp/docs/raw/cycling74-max-docs/`) and
phren memory — **never guess attributes; look them up here or in the docs.**

> Worked through by the "M4L inputs & UI mastery" loop (cron `7,27,47 * * * *`). Each
> run documents one topic + fixes one concrete issue. Status legend: ✅ mastered ·
> TODO todo · 🔬 investigating.

## ⭐ THE premium-control method — the Surface layout engine (native persistent-value cells)

**Current law (UI Foundations v2, 2026-07; supersedes the earlier "reuse extracted
painters" thesis):** the fleet's premium default is `m4l_builder.surface.Surface` —
hero slot(s) + untitled section cards of **native `dial_value_cell`s** (caption above,
bare 41×35 `DIAL_COMPACT` dial, its own persistent `shownumber=1` value), width
DERIVED from content at `finalize()`, and the hybrid brand-dim theme bus (baked
accent while enabled → Live-skin zombie grey on a Device-On bypass; Live-proven via
the Device-On-param `live.observer`, the only reliable runtime source). See
`docs/ui_premium_playbook.md` for the API walkthrough and migration discipline.

Corrections to the old text kept here for the record:
- The extraction workflow lives at `Max4LivePlugins/_assets/extracted/` (built by
  `_assets/extract_all.py` from the owned downloads) — **study-only, never shipped**;
  the old `research/extracted/` path never existed in this repo. Devices ship
  ORIGINAL painters only (`engines/painters.py`).
- `paint_control` (`jspainterfile`) remains Live-proven (Nimbus) but is the path for
  a genuinely bespoke ONE-OFF control, **not** the default knob — painters hide the
  native value readout, which is the corpus's #1 legibility rule (P2).

## Core principle — native-first, custom for what native can't draw

**Native controls (`live.dial` / `live.tab` / `live.toggle` / `live.slider` /
`live.numbox` / `live.menu`), sized small + laid out densely, are the premium DEFAULT**
(validated against Rupture 2.0, which is native). Reserve the **custom v8ui kit** for
what native genuinely cannot do: hero curves, drag-curve nodes, XY pads, animated
displays (LFO / spinning reel), glyph pickers, glass panels. The mistake to avoid:
over-engineering custom v8ui for ordinary knobs/menus, **and** sizing either too large.
Compact sizing + dense layout is what reads as premium — native or custom.

## ✅ Premium device LAYOUT grammar (AS Console / Rainbow / Chiral — JSON ground truth)

What reads as "a real device" is the LAYOUT, not bespoke knobs. Verified from the three
reference devices' patcher JSON:

- **ONE coherent dark base.** A single dark rounded `panel` fills the device — AS Console
  `[0.098]³` rnd 6, Rainbow `[0.157]³` rnd 4, Chiral `[0.059]³` rnd 4. Not many nested boxes.
- **Displays are drawn DIRECTLY on the dark base** (a `jsui`/`spectroscope~`/`scope~`), or
  on a *gently* recessed screen only slightly darker than the base. ⛔ **NEVER a near-black
  box on a lighter panel** — that hard "black box" is the #1 amateur tell (the old Strip).
- **Group CONTROLS on subtly *lighter* raised tiles**, not darker ones (Rainbow control
  cells `[0.529]`, Chiral side columns `[0.204]`). Light-on-dark = raised; dark-on-light = wrong.
- **Sections split by thin `live.line` dividers** (AS Console uses 75 of them) — structure
  without heavy boxes.
- **Tabs are transparent, text-only**: `live.tab` `bgcolor`/`bgoncolor` **alpha 0**, grey
  text → **accent** selected text (AS Console `textoncolor=[1.0,0.694,0.0]` orange). No filled pill.
- **No redundant internal title** — Live's device title bar already names it; an internal
  "STRIP" comment top-left reads as garbage. Use the space for content.
- **One vivid accent** (AS Console/Rainbow orange, Chiral cyan), on dial rings + the live
  trace; everything else muted-dark. Density (small controls packed on an 8px grid) + a
  value under every knob + a real graph is the premium signal.
- **Live spectrum behind a curve** = the Rainbow EQ look: stock `spectroscope~`
  (`device.add_compiled_ui`/`add_compiled_display`) BEHIND a transparent overlay that draws
  the grid + curve. Proven on Parametric EQ V2 and Strip v8. NEVER the non-stock `spectrumdraw~`.
- **Usefulness > prettiness:** add a display/meter/button ONLY where it shows useful info
  for THAT device (gain-stage meters on a strip, GR meter on a comp, transfer curve on a
  saturator). Do NOT put an EQ/spectrum on a device that doesn't need it.

## Sizing / "which knob needs what" (rule of thumb)

- **Standard knob** (drive, tone, freq, send): `live.dial` ~36–46 px, `appearance 0`
  (round), label above (comment) + value below (`shownumber 1`, `showname 0`).
- **Dry/Wet, Mix, Amount (0–100)**: `live.dial`, **`needlemode 1` (Unipolar)** so the
  arc fills from **0**, not center. (Auto-applied by the kit — see below.)
- **Pan / bipolar (−X..X)**: `live.dial`, **`needlemode 2` (Bipolar)**, fills from center.
- **Panel/section knob** (grouped in a titled panel): `appearance 2` (Panel) + a
  `panelcolor` — ONLY for that look; it draws a box and shifts value text (don't use
  for a plain dry/wet — it overlaps neighbors).
- **Tiny inline value**: `appearance 1` (Tiny) or a `live.numbox`.

## ✅ NATIVE SIZING (MEASURED — re-censused across 193 official Ableton/C74 .amxd devices)

Ground truth — the W×H (px) Ableton actually uses (the **mode** of every presentation_rect, with
its count). **Use these as defaults; native M4L is DENSE and SMALL.** Re-measured 2026-06 across
the full official M4L Factory Packs (193 devices, via `extract_frozen_amxd` on the bundled
abstractions) — a bigger dataset than the earlier 81-device pass; it CONFIRMS the dial and refines
the rest.

| Control        | **Native W×H (mode)** | n | notes |
|----------------|------------------------|----|-------|
| `live.dial` knob | **44×47** | 119 (×54) | THE standard knob; secondary 51×36 / 47×36 (wide-short); label+value baked in |
| `live.numbox`  | **39×15** | 170 (×75) | was 44 — corrected; H is ALWAYS 15. often `appearance 1` (LCD) |
| `live.text`    | **20×12** | 214 (×60) | the dominant is a SQUARE-ish icon/label cell; 40×15 for a wider button |
| `live.menu`    | **43×15** | 19 | NARROW + short; H ALWAYS 15 (some wide ~167 for long labels) |
| `live.slider` (V) | **21×97** | 8 | vertical fader |
| `live.tab`     | ~43–100 × **15–17** | 6 | width grows with segments |
| `live.toggle`  | **11×11** | 4 | tiny square |
| `live.button`  | **8×8** | 9 (×7) | tiny trigger dot (also 15×15) |
| fontsize       | **10** (the live.* default) | — | renders small at these sizes |

**Baked into the kit:** `m4l_builder.native_sizes` exposes these as constants
(`ns.DIAL_COMPACT`, `ns.MENU`, `ns.NUMBOX`, `ns.TOGGLE`, `ns.TEXT`, `ns.BUTTON`,
`ns.VSLIDER`, `KNOB_PITCH=48`) + helpers `ns.knob_row(x0, y, n)` / `ns.col(x, y0, n)`. Use
them as the default rect sizes — `add_dial(id, name, [x, y, *ns.DIAL_COMPACT], ...)`. Both
`knob_row` and `knob_row_fit` now default to **`DIAL_COMPACT` (41×35)** — the premium
workhorse; the legacy `ns.DIAL=(44,47)` is an un-grounded guess (steer-away). Dogfooded in
`plugins/uikit_gallery`. **This is the native-correct sizing source of truth.**

### ✅ Two density REGIMES — when each (the per-density rule)

There are TWO valid size regimes; pick by the look you want:

- **OFFICIAL-NATIVE (spacious)** — the table above (dial **44×47**, numbox **39×15**). Matches
  Ableton's stock devices. Use for a utility / "feels built-in" device, or when the device sits
  next to stock devices and should not look out of place. Constants: `ns.DIAL`, `ns.NUMBOX`, …
- **PREMIUM-COMPACT (dense boutique)** — measured from the 15 downloaded COMMERCIAL devices (dial
  **41×35** `DIAL_COMPACT`, `NUMBOX_WIDE=50×15`, `VSLIDER_NATIVE=22×113`, `TAB_BAR_H=20`,
  `ROW_PITCH_TIGHT=17`). Denser + flatter; matches the downloaded boutique devices (Rupture/AS
  Console). Use for a flagship/character device where dense, tightly-packed controls read as
  premium. Constants: `ns.DIAL_COMPACT`, `ns.DIAL_RAIL`, `ns.NUMBOX_WIDE`, `ns.knob_row_fit(...)`.

Within a regime, the size TIERS are: **tiny** (toggle 11×11, button 8×8, LED 10×10) → **row**
(numbox/menu/text H=15, the single-row controls) → **knob** (dial 44×47 or compact 41×35) →
**hero** (DIAL_HERO 48×50 / DIAL_BIG 56×56, a full-width tab bar, a scope/spectrum display).
Don't mix regimes in one device — choose one and size every control from it.

---

## ✅ live.dial  (the knob)

`live.dial` = circular slider, a real automatable Live parameter.

- **`appearance` [int] 0**: display style. `0 = Vertical` (round knob, **default**),
  `1 = Tiny`, `2 = Panel` (adds a `panelcolor` box — sectioned look; shifts the value
  text, can overlap), `3 = Large`.
  - ⚠️ **`appearance` is the knob-SIZE lever, and the sizes are NEAR-FIXED — they do
    NOT scale with the rect (Live-measured 2026-06):** `0 = Vertical` draws a **small**
    knob (~21px ⌀) and **stays ~21px even in a tall/wide rect** (extra rect = padding,
    not a bigger knob — the "knob looks small + padded" complaint). `3 = Large` draws a
    **big** knob (~30px ⌀, ≈ Ableton EQ Eight's native dial) and **stays big even in a
    smaller rect** (a too-small rect just clips/crowds it). There is **NO medium**
    between them. So: pick the SIZE with `appearance` (0 small / 3 large), then size the
    RECT only to fit `label + that knob + value`; don't expect the rect to tune the knob
    diameter. To hit a size *between* 21 and 30 you must draw a custom v8ui knob — stock
    `live.dial` can't. With `appearance=3`, 3 cells of `label(9)+knob(30)+value(10)`≈49px
    only just fit a 152px column — give the value↔next-label gap real room or labels
    collide.
- **`needlemode` [int] 0** (Max ≥ 8.6) — **FILL ORIGIN**, the thing that controls
  "starts at 0 vs middle":
  - `0 = Automatic` (**default — fills from CENTER even on a 0..100 range**; this is the
    bug that made dry/wet look wrong).
  - `1 = Unipolar` → arc fills from the **minimum / 0**.
  - `2 = Bipolar` → arc fills from the **center**.
  - **Kit fix (ui.py `dial()`):** `needlemode` auto = `2 if min<0<max else 1`, overridable.
  - ✅ **THE arc-color rule (DEFINITIVE — Dial Color Lab Live A/B 2026-06, verified at
    appearance 0 AND 3):** the value arc has TWO segments, each its OWN attribute —
    **`activedialcolor` = the FILLED segment** (min→value unipolar, center→value bipolar),
    the bright value indicator — and **`activefgdialcolor` = the UNFILLED REMAINDER**
    (value→max), the track behind it. (`dialcolor`/`fgdialcolor` are the same two at
    active=0 / bypassed.) So accent on **`activedialcolor`** gives the bright-fill knob (this
    is the kit default); keep `activefgdialcolor` dim for the dark track. There is **NO
    needlemode "flip"** — `activedialcolor` is the filled/active arc for BOTH polarities
    (bipolar just starts the fill at center). The old "all blue at 0, emptying as you scroll"
    symptom came from putting accent on `activefgdialcolor` (the REMAINDER): at center a
    bipolar dial is ALL remainder, so it reads all-accent, then the dim filled arc grows out.
  - ⛔ **`dial_fill` token DECISION (task Q1, 2026-06): REJECTED.** The proposed token
    (`activefgdialcolor`→accent + `activedialcolor`→dim track) is **backwards** — the Lab A/B
    shows it makes a DIM filled value + a BRIGHT empty remainder (the inverse of a Pro-Q
    knob). The kit already ships the correct bright-fill/dark-track premium knob via the
    default `activedialcolor`=accent. No token needed.
- **Color anatomy (doc-verified — THREE pairs, each split by the active state):**
  - `dialcolor` / `activedialcolor` — the **FILLED value arc** (min→value), the bright
    indicator (active=0 / active=1). Lab A/B 2026-06 — NOT "the ring/track" as once written.
  - `fgdialcolor` / `activefgdialcolor` (≥ 8.0) — the **UNFILLED REMAINDER arc** (value→max),
    the track behind the fill (active=0 / active=1). Max's "foreground dial color" — but it
    is the remainder, NOT the filled value; keep it dim.
  - `needlecolor` / `activeneedlecolor` — the **needle/pointer** line.
  - `tricolor` — the **reset-triangle marker** (shown when `triangle=1`; clicking it
    restores the dial's initial value). `bordercolor` / `focusbordercolor` = box border.
  - ✅ **AS Console ground truth (1.02) + Lab A/B 2026-06:** accent on **`activedialcolor`**
    (the FILLED arc) + a neutral-grey **`activefgdialcolor`** (the remainder track). AS
    Console's 24 dials: `activedialcolor=[1.0,0.694,0.0]` (orange fill) +
    `activefgdialcolor=[0.588]×3` (grey track), `showname 0`, 41×35. The kit's
    `recipes.dial_value_cell` follows this — `accent → activedialcolor` (filled value),
    `activefgdialcolor` grey (track): the premium bright-fill / dark-track knob.
  - ✅ **ONE convention, not two — the AS Console AND the EQ Eight / Pro-Q knob are the SAME
    mapping** (accent on the filled `activedialcolor`; they differ only in how dark the
    remainder track is). ⚠️ **CORRECTION (Lab A/B 2026-06):** the earlier "(b) EQ Eight =
    accent on `activefgdialcolor` + dim `activedialcolor`" recipe was BACKWARDS — that dims
    the filled value and brightens the empty remainder. To match EQ Eight's cyan, set
    `activedialcolor`=cyan (the fill) + a dim `activefgdialcolor`, NOT the reverse. **Para EQ
    (#21) shipped the reversed recipe (`activefgdialcolor`=cyan) — RE-CHECK its dials.** The
    kit default (`dial_value_cell`) is already correct: `accent → activedialcolor`.
  - ⛔ **PITFALL — a `parameter_enable=0` dial shows NO value (even with `shownumber 1`)**
    (Live-confirmed 2026-06). A non-parameter `live.dial` renders the knob + arc but the
    value text stays BLANK (same as a non-param `live.numbox`). So a "follow-the-selection"
    PROXY dial cannot show its value as a non-param — make it a REAL param (then gate the
    edit path with `live.thisdevice` so the restored value can't stomp the target on load),
    or render the value text separately.
  - ⛔ **PITFALL — do NOT `paint_control` a live.dial you want a value on.** A render-only
    `jspainterfile`/v8ui painter FILLS the dial rect and HIDES the native `shownumber`
    value AND the arc — this is exactly what made the old Strip's painted dials read dim
    and value-less. For premium NATIVE dials: no painter, `shownumber 1`, accent ring.
    Reserve painters for a genuinely bespoke one-off control, not the default knob.
- **`triangle` [int] 0**: toggles the reset-triangle marker (when `1`, clicking it restores
  the dial's initial value). **Max default `0` (hidden), and the premium norm — corpus census
  2026-06: 83/85 dials leave it absent (=0), only 2 set `1`, ZERO premium devices show it.**
  The kit now **defaults `triangle 0`** to match (was `1`, which drew the stray reset-arrow
  above every knob — the "white arrows at the top of the knob" flagged on Para EQ). Pass
  `triangle 1` + a themed `tricolor` only for the rare device that genuinely wants the marker.
  **Fleet re-audit 2026-06: every device keeps it off** (4 explicit `triangle 0`, none `1`, no
  device sets `tricolor`), so the reset affordance is **double-click** (e.g. Para EQ's
  `reset_band_at`), never a marker. NB there is **no auto `tricolor`→needle_color mapping** in
  `dial()` — `tricolor` is an opt-in kwarg (default unset); a stale Q1 note assumed one that never
  existed, so the "confirm the tricolor reset-triangle" follow-up is moot (the triangle is off).
- **`panelcolor` [4 floats]**: only used when `appearance = 2` (Panel).
- **`showname` / `shownumber` [int]**: draw the param name / value. **LABEL DECISION RULE
  (Live-verified 2026-06):**
  - **Matched label** (caption the SAME font + size as the value — the EQ-Eight look) → use
    the dial's OWN `showname 1`, NOT a separate comment. `fontsize` is a WHOLE-OBJECT attr
    (Max docs: *"Sets the object's font size (in points)"*), so the name and value always
    render in the identical font; `showname` natively stacks **name → knob → value**. Give
    the rect ~50px tall (appearance 0 small knob) so the name sits clearly ABOVE the knob
    with a gap, not on it. Trade-off: name + value SHARE one `textcolor` (you can't grey the
    caption while brightening the value). This is the Para EQ V2 left column (Freq/Gain/Q).
  - **Independent label** (caption a DIFFERENT size/colour from the value — e.g. small grey
    uppercase over a brighter value) → `showname 0` + a separate `live.comment` above,
    `shownumber 1` for the value below. ⚠️ **A `live.comment` renders VISIBLY SMALLER than a
    `live.dial`'s name/value text at the SAME nominal `fontsize`** (different font metrics) —
    so equal `fontsize` does NOT make them match; size the comment up deliberately, or accept
    the smaller grey caption as the intended look.
  - **Ground truth:** AS_Console_1.02's 24 dials are `showname 0` + `shownumber 1` (default)
    and carry **ZERO `live.comment`s** — their captions come from a **backdrop graphic**
    (fpic/jsui), not comments. The kit's `dial_value_cell` approximates that backdrop with a
    small comment caption (`label_fontsize 7.5`); for a value-matching caption instead, pass
    `showname 1` and omit the comment. `dial_label_cell` must pass `showname 0` (else the
    dial draws its name INSIDE the knob, doubling the comment caption it places below).
- **`valuepopup` [int] 0** + **`valuepopuplabel` [int] 0** (doc-grounded): `valuepopup 1`
  floats the current value in a **popup caption on hover/drag** — the premium feedback for a
  **COMPACT dial that has no room for a persistent `shownumber`** (and the EQ-node drag feel).
  `valuepopuplabel` sources the caption's label: `0 None / 1 Hint / 2 Scripting Name /
  3 Long Name`. Now first-class kwargs on the kit's `dial()`. Use it when you drop the
  persistent value to save space; keep `shownumber 1` + no popup when the value is always shown.
- **`textjustification` [int]**: `0 left / 1 center / 2 right` — alignment of the dial's
  name/value text.
- **`unitstyle` [int]**: 0 int, 1 float, 2 time(ms), 3 Hz, 4 dB, 5 percent (DEFAULT), 6 pan,
  7 semitones, 8 MIDI, **9 Custom**, 10 native. A bipolar non-% param (e.g. −12..12 semis)
  must NOT inherit 5 → pass 1/native.
- ✅ **DISPLAYED DECIMALS / units ARE controllable (doc-grounded — corrects an earlier "not
  settable" note):** use **`unitstyle = 9` (Custom)** + the parameter's **`units`**
  (`_parameter_units`) string. A plain symbol (e.g. `"Harmonic(s)"`) appends to the native
  value; a **sprintf format** gives full control of the number — `units="%0.2f dB"` →
  `"0.00 dB"`, `"%.1f Hz"`, etc. This is how to match EQ Eight's 2-decimal gain (`0.00 dB`)
  on a stock `live.dial`. (`_parameter_steps` quantizes the range into N positions — that
  changes RESOLUTION, not just display, so don't use steps to force decimals.)

## ✅ THE native-control color rule (applies to ALL live.* widgets)

M4L controls are **`active = 1` ALWAYS** — Live does NOT auto-grey an M4L device's custom UI
on bypass. ⚠️ **Empirically verified (2026-06, enable_device off + pixel-diff): an enabled vs
bypassed Pressure is 0.0-pixel-diff IDENTICAL** — native controls AND jsui both stay full
brightness when the device is disabled. So the colors you actually SEE are ALWAYS the
**`active*`** attributes — theme those. The bare attrs are a fallback shown ONLY if the device
explicitly drives a control's `active` to 0 (e.g. a manual bypass-dim gate, below); they are NOT
shown automatically on bypass (so "bare = bypassed" is a misnomer for M4L — but theming the
`active*` is still exactly right, since that is what renders).
**The `active` attribute — the mechanism (synced live.dial maxref):** *"active [int] : 1.
When the active attribute is set to 0, the mouse action does not cause output AND the inactive
colors are used."* So `active 0` does TWO things to a control: makes it non-interactive AND
switches it to its bare/inactive colours. That is the ONLY lever that shows the inactive
colours. ⇒ A bypass-zombie gate that fans `active 0` to every control (off `live.thisdevice`
outlet 1) DOES grey the natives — **but only if their inactive/bare colours are set to a DIM
value**; if you mirrored them equal to the `active*` colours (the kit default), `active 0`
renders identical and nothing greys. (`ignoreclick 1` is the separate "pass mouse clicks
through" toggle — for a transparent overlay, not for greying.)

| You want to color…        | Use (always renders)    | Bare attr (only if active=0) |
|---------------------------|-------------------------|---------------------------|
| selected tab / toggle ON  | **`activebgoncolor`**   | `bgoncolor`               |
| unselected / OFF bg       | **`activebgcolor`**     | `bgcolor`                 |
| **numbox** slider-fill (appearance 2) | **`activeslidercolor`** | — (no bare twin) |
| dial arc                  | **`activedialcolor`**   | `dialcolor`               |

**This was the amber-tab bug:** setting `bgoncolor=cyan` colored the selection only when
bypassed; the live (active) selection needs **`activebgoncolor=cyan`** (+ `activebgcolor`
for the unselected fill). Theme the `active*` attrs.

> ⚠️ **The rule above is the COMMON case, NOT universal — every live.* object has its OWN
> colour model and several break it.** Verified across the synced docs + corpus (one run per
> control). Use this cheat-sheet; do NOT copy one control's colour signature onto another (that
> caused the tab→menu, numbox-text, and slider-fill bugs):
>
> | control | fill / "on" you SEE | text | notes / traps |
> |---|---|---|---|
> | **live.dial** | `activedialcolor` (FILLED value arc — accent here), `activefgdialcolor` (remainder track — dim) | — | NO bipolar flip (Lab A/B 2026-06); `triangle 0` = no reset arrow |
> | **live.tab** | bg+`activebg*` twins | `textcolor`/`textoncolor` **+ `inactive*` twins** | TEXT has NO active twin; `activetextoncolor`=0 corpus (bug) |
> | **live.text** | bg+`activebg*` twins | `textcolor`+`activetextcolor`; on-text = **`activetextoncolor`** only | NO bare `textoncolor` |
> | **live.menu** | body=`activebgcolor`; highlight=**`hltcolor`** | **bare `textcolor`** + `hlttextcolor` | NO `bgoncolor`/`textoncolor`/active-text |
> | **live.numbox** | body=`activebgcolor`; slider-mode=`activeslidercolor`; LCD=`lcd*` | **bare `textcolor`** | colours are APPEARANCE-gated; no bare `bgcolor` |
> | **live.slider** | **bare `slidercolor`** (NO active twin) | **bare `textcolor`** | NO `appearance` attr at all |
> | **live.button** | bg+`activebg*` twins (mirrored) | — | corpus border is alpha-0 (borderless) |
> | **live.toggle** | `activebgoncolor` (ON) | — | OFF-box left Live-default (don't hide it) |
> | **live.meter~/gain~** | **INVERTED: lit = bare `cold/warm/hot/overloadcolor`** | `textcolor` (gain~) | unlit twins only for cold/warm (`inactive*`) |
> | **textbutton** (classic) | bare `bgcolor`/`bgoncolor` | bare | Toggle on-bg needs `usebgoncolor 1` |
> | **live.step/grid** | solid: `stepcolor`/`stepcolor2`/borders | — | alpha-WASH attrs (zebra/hover/amount) can't be token-mapped |

## ✅ Runtime THEME BUS (`live.colors`) + bypass "zombie" dim — the #1 corpus jewel

Corpus-grounded (13 of 15 downloaded devices use `live.colors`; AS Console has 19 instances; all 9
TEARDOWN.md reports flag it). Not in the synced Max docs — grounded from the corpus + `engines/
live_theme.py`. **Premium devices never bake colors at build time** — they read the user's actual Live
skin at load + on every theme change and broadcast it so every native control tracks the skin
(dark/light/custom). This is the single biggest "looks like a first-party Ableton device" cue.

**The color bus** (verified from AS Console / Roulette / Chiral):
```
live.thisdevice[0] (loadbang) ─┐
                               ├─► message "<skin_token>" ─► live.colors[0]
live.colors[1] (theme change) ─┘
live.colors[0] ─► route <skin_token> ─► prepend <attr> ─► s ---<bus>      // distributor
r ---<bus> ─► control[inlet]                                              // each control subscribes
```
`live.*` controls accept `"<attr> R G B A"` color-setting messages, so the receiver just re-sends the
broadcast color into the control. One palette change repaints the whole device live; theming is data.
**Skin slots** (`LIVE_SKIN`): `lcd_control_fg` (the ACCENT), `lcd_control_fg_zombie` (the dimmed/bypass
accent), `lcd_bg`, `surface_bg`, `control_fg`, `assignment_text_bg`, `control_selection`. Fan ONE slot
to many attrs at tiered alphas for a full look (Roulette's `p lcd-knob`: `lcd_control_fg` →
`activedialcolor`@1.0, `activefgdialcolor`@0.5, `fgdialcolor`@0.25, `textcolor`@0.5, `tricolor`@1.0 …).

**`live.thisdevice` — the device-lifecycle object (3 outlets, synced-maxref-verified).** Declare
`numoutlets=3, outlettype=["bang","int","int"]` (the kit's `live_thisdevice` helper defaults to
this — correct):
- **outlet 0 (bang)** = LOADBANG: fires once after the device + LiveAPI are ready. Stage ALL
  startup off it — LiveAPI observers, DSP-state/SR reports, deferred init, load-time UI hides.
  Every kit device wires outlet 0 for this (verified). NB it is NOT the right one for the
  enabled state — that was the old wrong guess.
- **outlet 1 (int 1/0)** = ENABLED / DISABLED (the device Activator / bypass). This is the ONLY
  signal that the device is bypassed — Live does NOT auto-grey M4L UI (0.0-pixel-diff verified),
  so outlet 1 is what drives the **bypass-zombie dim** below, and it is also what makes a
  control's `inactive*`/bare colours actually render (by driving its `active` to 0). Without
  wiring outlet 1, an M4L device looks identical bypassed vs active.
- **outlet 2 (int 1/0)** = PREVIEW-mode enabled/disabled (rarely needed).

**Bypass "zombie" dim** (greys the device when bypassed, like a stock device). ✅ **CONFIRMED
NEEDED, not redundant (empirically, 2026-06):** Live does NOT dim an M4L device's UI on bypass
at all (enabled vs bypassed = 0.0 pixel-diff), so to get the stock "greys when off" look you
MUST wire it yourself. Mechanism:
`live.thisdevice <state> ─► s ---devicestate ─► r ---devicestate ─► sel 0 1 ─► [accent msg | zombie-grey
msg]`. Chiral emits BOTH simultaneously with complementary alphas (`!- 1.`) so enable/bypass is an
alpha crossfade. ✅ **STATE OUTLET RESOLVED (synced live.thisdevice maxref):** the enabled/disabled
(bypass) bang comes from the **MIDDLE outlet (outlet 1)** — *"sent from the middle outlet when the Device
is enabled or disabled"* (1=enabled, 0=disabled). NOT outlet 0 (leftmost = init/loadbang) and NOT outlet 2
(rightmost = PREVIEW-mode enabled/disabled). So wire `live.thisdevice` **outlet 1** → `sel 0 1` → the
accent/zombie crossfade. ⚠️ **CORRECTION (empirical, supersedes an earlier note that said "natives
auto-dim"):** NOTHING auto-dims on bypass — native controls AND jsui are both 0.0-pixel identical — so
the gate must dim BOTH. **TWO BUILD APPROACHES (a user look-decision):**
- **(A) Control-grey (the Ableton-native look):** fan `active 0/1` (off outlet 1) to EVERY live.*
  control's inlet → each goes non-interactive + switches to its inactive colours. REQUIRES those
  inactive/bare colours be set DIM (un-mirror them — the kit default mirrors `bare = active*`, so
  `active 0` would render IDENTICAL and nothing greys). Plus a SEPARATE dim for the jsui displays
  (no `active` attr). Most faithful; most wiring + an inactive-colour retheme.
- **(B) Overlay-darken (simplest):** ONE foreground `jsui`/`v8ui` over `[0,0,W,H]`, `border 0`,
  `ignoreclick 1` (clicks pass through), painting a transparent rect whose alpha is 0 when enabled
  and ~0.4 dark when bypassed — driven straight from outlet 1. Dims EVERYTHING uniformly in one
  element (a darkening film, not Ableton's desaturate); no per-control wiring, no colour retheme.
- **DECISION NEEDED before building** (A native-look-but-heavy vs B simple-darken vs none); do not
  auto-add to shipping devices until chosen.

**Kit status:** `engines/live_theme.py` ships `live_colors_bus(specs)` + `live_theme_receiver(bus, target)`
(the color bus — structurally verified, Live-verify queued). MISSING: the bypass-zombie gate + a turn-key
`Device.add_theme_bus(specs)` that auto-wires receivers into every control. **When:** use for EVERY
device. A custom v8ui can read the same bus (`r ---<bus>` → a `set_<attr>` handler) so jsui art themes too.

## ✅ live.tab  (segmented selector / enum param)

- **Fill — BG has `active*` twins:** `activebgoncolor` (selected, active) · `activebgcolor`
  (unselected, active) · `bgoncolor`/`bgcolor` (the bypassed twins). Premium devices set BOTH
  twins (corpus census 2026-06: 17/28 each) so the fill themes in either device state.
- **Text — pairs with `inactive*` twins, NOT `active*`:** `textoncolor` = selected-tab text
  (enabled) **+ `inactivetextoncolor`** = the same when the device is bypassed (corpus 20/28);
  `textcolor` = unselected-tab text **+ `inactivetextoffcolor`** when bypassed (9/28). ⚠️ **No
  `activetextoncolor`/`activetextcolor` in the premium vocabulary — the corpus sets `activetextoncolor`
  0/28.** The kit's `tab()` mirrors `textoncolor→inactivetextoncolor` and `textcolor→inactivetextoffcolor`
  (it previously mirrored to the bogus `activetextoncolor`, leaving bypassed selected-tab text un-themed).
- `spacing_x` [float]: gap between segments (default ~6). `rounded` [float]: corner.
- ⚠️ **`multiline` [int] — Max default is `1`, and that STACKS the segments.** Doc
  (live.tab.maxref): *"allows multiple lines of text in a tab; when set you can resize to
  create multi-column displays."* So in a compact cell live.tab wraps its segments into a
  multi-row grid instead of one horizontal strip — a 2-option tab in a ~64×16 cell renders
  **FREE over SYNC vertically** (Live-verified on echotide, 2026-06). A premium segmented
  selector is a single horizontal row, so **the kit now defaults `multiline=0`** (segments
  side-by-side, "width grows with segments"). Pass `multiline=1` ONLY for a deliberate
  multi-row/column tab. This is why the "width grows with segments" sizing rule only holds at
  `multiline=0`. **Fleet audit (2026-06):** flipping the kit default to 0 is safe across all 6
  tab-using devices — only echotide's 2-segment 64px tab was actually stacking; the wide tabs
  (crossover 162px/4, sear 272px/4, uikit 172px/3) already rendered as one row under
  `multiline=1` (enough width), and linear_phase_eq's 3 tabs are `HIDDEN_RECT` — so none of
  their looks change. Stacking only bites a SHORT (≥~16px tall) NARROW tab with ≤2 segments.
  **Live-verified** (2026-06): the still-shipped (multiline=1) Linear Phase Crossover renders its
  4-segment `LISTEN` tab (162px/4 = 40px/seg) as a clean horizontal SUM·LOW·MID·HIGH row — so the
  default flip is confirmed safe; the wide devices need no rebuild to stay correct.
- Enum param 0..N-1; the kit's `add_tab(options=[...])` registers it. Prefer over a
  dropdown when ≤4 options and there's horizontal room.

**Enum-selector decision (tab vs menu vs umenu vs radiogroup):**
- **`live.tab`** — shows ALL options at once, one click to any (most discoverable). Best for
  **≤4 segments** with horizontal room (≈40 px/seg). The premium default for a small enum
  (M/S mode, slope, a 2–3 style switch). Selected-segment colour = `activebgoncolor` (theme it).
- **`live.menu`** — a dropdown showing only the current value; one click + pick. Best for **many
  options** or a **tight width** where a tab won't fit. Saves as a parameter. (A 3-option enum in
  a cramped strip can go either way — a tab is more discoverable if it fits; a menu if it doesn't.)
- **`umenu`** — NON-parameter; in the corpus almost always a styled read-only readout (`set`-driven,
  `ignoreclick`), not an interactive selector. Don't use it for a savable enum — use `live.menu`.
- **`radiogroup`** — ⊘ plain-Max, unthemed, **0** M4L corpus. Never in a device; use `tab`/`menu`.

## ✅ live.slider / rslider  (fader)

- `orientation` [int] 0: `0 = Vertical` (default), `1 = Horizontal`.
- `relative` [int] **1**: mouse mode. `0 = Absolute` (click jumps the fill to the
  pointer), `1 = Relative` (**default** — drag keeps relative position; the premium feel).
- **Fill color = bare `slidercolor` (doc-verified — live.slider has NO `activeslidercolor`,
  NO active twin at all).** This is the key gotcha: unlike `live.dial`/`live.tab` (active\*
  twins) and unlike `live.numbox` (which DOES have `activeslidercolor`), the slider's
  `slidercolor` is the fill you see in every state. The registry previously mapped the
  non-existent `activeslidercolor` → sliders rendered Live-grey; **fixed → maps the real
  `slidercolor → dial_color`.**
- **`textcolor` = the value-readout text** (doc-confirmed: *"Sets the display color for the
  live.slider object's text"*; set by 14/14 corpus AS-Console sliders). The registry now maps
  `textcolor → text` (was unmapped → digits rendered Live-default).
- `tricolor`/`trioncolor`/`tribordercolor`: the mod/automation triangle (shown only when the
  param is modulated) — left to Live's modulation colour, not token-mapped. `modulationcolor`,
  `focusbordercolor` round out the borders.
- ⚠️ **live.slider has NO `appearance` attribute** (doc-confirmed — unlike `live.dial`/
  `live.numbox`); its look is set by `orientation` + `relative` + the colours above, nothing else.
- Native slider is fine for level/amount; the custom v8ui slider only earns its place
  for a bespoke handle/track look. Keep the slider OFF the device-view bottom edge — a
  12px track at y~140 clips in Live.

## ✅ live.numbox  (numeric entry)

- ⚠️ **numbox `appearance` is a DIFFERENT enum from the dial's** (doc-grounded — don't assume
  they share values): **0=Default, 1=Triangle, 2=Slider, 3=Bipolar, 4=LCD**. (The dial's is
  0=Vertical/1=Tiny/2=Panel/3=Large — so e.g. `appearance=2` is a *Slider*-fill numbox, NOT a
  panel; `appearance=3` is a *Bipolar* center-fill readout.)
- **`appearance=4` = LCD — the DOMINANT premium numbox look** (corpus: 98 of 142 numboxes).
  Borderless glowing digit: `lcdcolor` (lit digit), `lcdbgcolor` (dark readout field),
  `inactivelcdcolor` (dim/unlit segments). `appearance=2` (Slider) draws `activeslidercolor`
  as a value-fill bar behind the digits. Now first-class
  kwargs on `number_box()`; the registry themes the lcd colors from `Theme.lcd_on/lcd_bg/
  lcd_off` (lit=accent, field=darker-than-bg, off=dim).
- **`number_box()` now DEFAULTS to `appearance=4` (LCD) (fix 2026-06).** Previously the default
  was unset → Max's plain mode, so the registry's themed `lcd*` colours were **DEAD** (they
  only paint at appearance 4) — every kit numbox was a plain box wearing LCD theming it never
  showed. The corpus is 69% LCD (98/142) and all 5 fleet numboxes are value readouts (Out
  Gain, Output Gain, Slices, Refresh, Range…) — the exact LCD use case — so LCD-by-default is
  the right premium default and brings the lcd theming to life. Pass `appearance=0` for a plain
  box. (Manifests on REBUILD; installed `.amxd`s unchanged until then — Live-verify the LCD
  digits on the next numbox-device rebuild.)
- `unitstyle` same enum as the dial. The compact native number — prefer over the custom
  stepper/readout unless you need −/+ buttons or a drawn bar.
- **COLOUR MODEL (doc + corpus-grounded, 142 corpus numboxes) — MODE-specific, each colour
  renders ONLY in its `appearance`:** body bg = **`activebgcolor`** (the visible active=1
  body for the non-LCD modes 0/1/3; corpus 30, and **bare `bgcolor` is NEVER used — 0**),
  value text = **bare `textcolor`** (41; NO `activetextcolor` twin — like live.menu, unlike
  live.text/tab), slider-fill (`appearance=2`) = `activeslidercolor`, LCD (`appearance=4`) =
  `lcdcolor`/`lcdbgcolor`/`inactivelcdcolor`, triangle (`appearance=1`) = `tricolor`/`tricolor2`
  + `activetricolor`/`activetricolor2` (the active twins go accent when value ≠ initial).
  There is NO `bgoncolor`/`textoncolor` (numbox has no on/off state).
- **Theming:** registry maps `activebgcolor→surface` (non-LCD body), `textcolor→text`,
  `activeslidercolor→dial_color`, and the lcd trio — all unconditionally (off-mode colours
  are ignored, so it's harmless; 17 corpus numboxes set `activebgcolor` AND lcd together).

## ✅ live.toggle  (on/off)

- ON fill = **`activebgoncolor`** (active) / `bgoncolor` (bypassed); OFF = `activebgcolor`
  / `bgcolor`. `outputmode` [int]: toggle vs button (momentary) behavior. `bordercolor`.
- ⚠️ **toggle vs `live.text` — pick by whether the control needs a LABEL.** `live.toggle` is a
  bare ~12×13 checkbox: use it only for a tiny inline on/off whose meaning is obvious from
  context. For ANY on/off that benefits from a word (Bypass, HP On, Mono, M/S, AN) use
  **`live.text`** (off/on labels, `mode=1` to latch) — that is the PREMIUM corpus norm
  (AS_Console_EQ builds its entire utility strip from labelled `live.text`; J74's toggles are
  2-value enum `live.text`). Both are real automatable params; the difference is the label.

## ✅ live.text  (text button / toggle hybrid)

Automatable enum param (stores 0/1). **Full active-twin object** — doc-verified attrs:
- `mode` [int] 1: `0 = Button` (momentary), `1 = Toggle` (latching). **The kit factory now
  DEFAULTS `mode=1` (fix 2026-06)** — matching the native maxref default AND every real use.
  It previously FORCED `mode=0`, so all 48 fleet toggles (bypass/freeze/M-S/on-off) shipped
  MOMENTARY: they un-latched on release, rejected Live-API `set` (`bad arguments for message
  set`) and broke loadbang defaults. **Live-verified the fix** (rebuilt Mono Maker → its BASS
  MONO toggle now latches `ON` with a persistent accent fill AND a LOM `set 0→1` holds; the
  corpus is 0/113 explicit `mode=1` because they ride the native default). Pass `mode=0`
  explicitly for a genuine momentary action button. `transition` [int]: when the bang fires —
  0 Zero→One, 1 One→Zero, 2 Both.
- `outputmode` [int] 0 (toggle mode only): `0 = Mouse down` (default), `1 = Mouse up`
  (cleaner — a drag-off cancels). Now exposed as a kwarg on `live_text()`.
- `appearance` [int] 0: `0 = Default` (text in box), `1 = Label` (square button + text to
  the right), `2 = LCD` (`lcdcolor`/`lcdbgcolor`/`labeltextcolor`).
- `text` / `texton` [symbol]: the OFF / ON labels (the factory uses `text_off`/`text_on`).
- ⚠️ **enum value labels: `live.text` does NOT surface `parameter_enum` to Live's value display**
  (Live-confirmed). The factory emits `parameter_type=2` + `parameter_enum=[text_off,text_on]`, and
  the fix this run added the missing **`parameter_mmin=0`/`parameter_mmax=1`** (every one of 166
  corpus enum params has `parameter_mmax` = `len(enum)-1`; `live.text` was the only enum control
  not setting min/max, unlike `menu()`/`tab()` — a real structural gap, now closed). BUT even with
  byte-identical `valueof`, Live shows the **`live.toggle`/`live.tab`** value label (`"ON"`, `"SINE"`)
  while **`live.text` shows the placeholder `"val2"`** in the LOM/automation readout — proven by
  loading drift (`Stereo` live.toggle → `"ON"`, `Shape` live.tab → `"SINE"`) next to Mono Maker
  (`Mono` live.text → `"val2"`), all three carrying the same `parameter_enum=['OFF','ON']`+`mmax`.
  So it is a **maxclass behaviour**, not a missing attr. The device-UI BUTTON still shows OFF/ON
  (the user sees the right thing); only the automation-lane/LOM display is generic. **For an on/off
  whose AUTOMATION readout must be meaningful, use `live.toggle` + `parameter_enum` + a `comment`
  label (drift's `Stereo` pattern), not `live.text`.**
- **Colors follow the active\* rule**: the ON fill you see is `activebgoncolor` (mirror of
  `bgoncolor`), OFF fill `activebgcolor`, text `activetextcolor` / `activetextoncolor`.
  The factory MIRRORS each bare color to its `active*` twin (it set only the bare/bypassed
  ones before, so a themed `live.text` rendered Live-default); the registry themes it
  (`bgcolor→surface`, `bgoncolor→accent`, `textcolor→text`).
- ⚠️ **ON-state text is the EXCEPTION — there is NO bare `textoncolor` on live.text**
  (synced-doc-verified: live.text exposes `textcolor`/`activetextcolor`, `textoffcolor`,
  and `activetextoncolor`, but no `textoncolor`). So the on-label colour lives ONLY in
  `activetextoncolor`; the kit's `live_text(textoncolor=…)` sets just that (it previously
  also wrote a bare `textoncolor`, a no-op Max ignored). NB this differs from `live.tab`,
  whose text uses `inactive*` twins (no active text twins) — each live.* object has its
  OWN colour state model; don't generalise one to another.
- Good for a labeled mode button where `live.toggle` is too plain.

## ✅ live.menu  (dropdown enum selector)

`live.menu` = dropdown backed by an automatable Enum param; visible items = labels,
stored/automated value = the **index** (0..N-1). `add_menu(options=[...])` registers it
(`parameter_type=2`, min 0, max N-1, initial 0). Verified in the gallery: themed body +
`Mode` param 0..3 → "WARM".
- ⚠️ **live.menu has its OWN colour model — it does NOT share live.tab's** (NO synced doc
  for live.menu; grounded on 25 corpus menus, e.g. Roulette). Real attrs: **`activebgcolor`**
  (the menu BODY you see, active=1; bare `bgcolor` = bypassed body), **bare `textcolor`** (item
  text — NO `activetextcolor` twin), **`hltcolor`** (the HIGHLIGHTED item's bg in the open list)
  + **`hlttextcolor`** (its text), `tricolor` (dropdown triangle), `bordercolor`/`focusbordercolor`,
  and `lcdcolor`/`lcdbgcolor`/`inactivelcdcolor` for the LCD look. **There is NO
  `bgoncolor`/`textoncolor`/`activetextoncolor`** (those are live.tab/live.text vocabulary).
- The kit's `menu()` keeps a uniform signature but ROUTES to the real attrs: `bgcolor`→
  `bgcolor`+`activebgcolor`, `textcolor`→ bare `textcolor`, `bgoncolor`→ **`hltcolor`**,
  `textoncolor`→ **`hlttextcolor`** (it previously emitted live.tab's `bgoncolor`/`activetext*`,
  which live.menu ignores, so the highlight went un-themed). **Theme-injection fix (2026-06):** the
  registry mapping fed only `bgoncolor`→`tab_bg_on` and `textcolor`/`bgcolor`, so the highlighted
  item got the accent BG but its TEXT (`hlttextcolor`) stayed Live-default — often illegible on the
  accent. Added **`textoncolor`→`tab_text_on`** so the highlight TEXT themes too, matching the
  selected `live.tab` (which already maps all four) and the corpus (6/25 menus set `hlttextcolor`).
  Verified by diffing the kit's *emitted* menu attrs against the 25 corpus menus: kit was missing
  `hlttextcolor`/`lcd*`/`tricolor`/`bordercolor`; the closed (visible) menu look is unchanged — the
  themed highlight only shows when the dropdown is open — so no Live-verify needed.
- **`appearance` — checked, NO kit-default change warranted (unlike numbox).** Corpus menu
  `appearance` splits ~50/50: **None=12, appearance=1=13** (and all 7 lcd-themed menus are at
  appearance 1, so 1 is the LCD-style menu mode). Because it is NOT a clear plurality (numbox was
  69% at LCD), and the kit's default-appearance menu already renders themed (body `activebgcolor`,
  `textcolor`, `hlt*` — Live-verified rendering fine in UIKit Gallery), leaving the menu default
  unset is correct. The LCD menu (`appearance=1` + `lcdcolor`/`lcdbgcolor`/`inactivelcdcolor`) is an
  available opt-in via kwargs, not the default.
- **Use when** >4 options or long labels or tight width (one compact box); prefer `live.tab`
  for ≤4 short modes with room. `shortname` IS threaded. No `unitstyle` (Enum has no unit).

## ✅ umenu  (non-parameter dropdown — in practice a styled READOUT)

`umenu` (core Max, NOT `live.*`) outputs the selected **int index** on outlet 0 and is
**NOT automatable or saved** — for an enum *parameter* use `live.menu` instead. But the
corpus tells a surprising story: across **26 `umenu` instances, ALL have
`parameter_enable=0`**, and **25/26 set `ignoreclick=1` + `arrow=0` + `allowdrag=0`** with a
`bgfillcolor` fill and centered text (`textjustification=1` on 12). So premium devices use
`umenu` almost exclusively as a **non-interactive STYLED VALUE READOUT** — a filled "LCD
label" whose text is set programmatically by sending `set <index>` (or the int) into it — NOT
as a picker. `add_umenu(..., display=True)` applies the verified preset (`ignoreclick=1,
arrow=0, allowdrag=0`).
- ⚠️ **The RENDERED fill is `bgfillcolor`, NOT bare `bgcolor`** (the modern Max "Color" attr
  overrides it). Corpus-measured: **25/25 umenus use `bgfillcolor_type "color"` (a FLAT fill)
  with `bgfillcolor_color` == `bgcolor`** — `bgfillcolor_color1/_color2/_angle` are stored but
  UNUSED at type `color` (it is NOT a rendered gradient, despite the stored stops). **Fix
  (2026-06):** `umenu()` now MIRRORS a themed `bgcolor` into `bgfillcolor_type:"color"` +
  `bgfillcolor_color` automatically — previously the kit set only `bgcolor`, so a themed
  readout drew Max's DEFAULT fill and ignored the accent. Pass explicit `bgfillcolor_*` kwargs
  (e.g. `_type "gradient"` + `_color1`/`_color2`) to override for a real gradient.
- Theme injects `bgcolor→tab_bg` (now also flows to `bgfillcolor_color`), `textcolor→tab_text`
  (no on-state — it's a readout). **Use when** you want a themed text/enum readout you drive
  from logic; use `live.menu` for an interactive automatable enum, `live.tab` for ≤4 modes.

## ✅ button family (live.button · textbutton · ubutton)

THREE 'button' variations — pick by need:
- **live.button** (momentary trigger, AUTOMATABLE param): the default trigger. Doc-verified
  active twins → bgcolor (idle) + bgoncolor (the flash) are mirrored to active*
  so the live state themes. Verified: Trigger param 0/1, themed dark idle. Use for any
  bang/trigger you want automatable (freeze, reset, tap).
- **textbutton** (LABELED button, NO param, core Max → NO active twins; bare colors ARE the
  live ones): text/texton, mode (0 button / 1 toggle / 2 bang). Themed via bare
  bgcolor/bgoncolor/textcolor (theme injects them). ⚠️ **In Toggle mode (mode=1) the
  `bgoncolor` on-state bg only PERSISTS when `usebgoncolor=1`** (Max default 0 → a latched
  toggle shows its on-LABEL but never its on-COLOUR). The kit's `textbutton()` now auto-sets
  `usebgoncolor=1` whenever a toggle is given a `bgoncolor` (Button mode flashes it briefly,
  no flag needed). Use for a labeled mode/action button that drives patcher logic (not a param).
- **ubutton** (INVISIBLE click-zone over graphics) — now VERIFIED from the official M4L corpus
  (43 instances / 14 devices, 100% consistent). 1 inlet / **4 outlets**
  `["bang", "bang", "", "int"]`: outlet 0 bangs on mouse-UP (release inside), outlet 1 bangs on
  mouse-DOWN, outlet 3 is the `int` button state (1 down / 0 up). (The old stub had outlet 1 as
  `""` — wrong.) Its ONE color is `hltcolor` (the highlight flash drawn on click; otherwise
  transparent); `handoff` forwards clicks to a partner ubutton. Themed `hltcolor → accent`. Use
  to make an `fpic` / drawn region clickable (graphic button, clickable logo, jsui hotspot); for
  a visible automatable trigger use `live.button`, for a labelled action use `textbutton`.

## ✅ matrixctrl  (grid of toggle cells — routing / mod matrix / step row)

`matrixctrl` = a `rows`×`columns` grid of on/off cells. Measured (7 corpus instances):
`rows`/`columns` always set (norm **2×4**, one **1×16** step row); **`autosize=1` on 6/7**
(the Max default — cells auto-fit the rect, so you size the *box* not the cells); **6/7 are
`ignoreclick=1` DISPLAYS** driven by the patch (showing a step pattern / routing state),
NOT interactive. The interactive one is a 1×16 step row that's a **Blob parameter**:
`parameter_enable=1` + `parameter_type=3` stores the WHOLE grid as one automatable/saved
list (`parameter_longname='trigs'`), `outlettype=['list','list']`. Cell colors: **`color`**
= ON/lit cell (→accent), **`elementcolor`** = OFF cell, **`bgcolor`** = backdrop — all
alpha-0 in the saved file when a `live.colors` bus injects them at runtime. `verticalmargin`
spaces rows. Kit: `add_matrixctrl(rows=, columns=, autosize=1, ignoreclick=, color=,
elementcolor=, bgcolor=)`; theme injects `color→accent, elementcolor→section, bgcolor→bg`.
**Use when** you need a compact multi-cell on/off grid; for one multi-value strip use
`multislider`/`live.step`; for a single enum use `live.tab`/`live.menu`.

## ✅ multislider  (strip of N bars — multi-band meter / GR display / step editor)

`multislider` draws N bars in a strip. Measured (5 corpus instances): `slidercolor`
(the bars) + `bgcolor` (5/5); **4/5 are non-interactive DISPLAYS** — `ignoreclick=1` +
`ghostbar=1` (a faint full-range outline behind each bar) + `thickness`, fed a list into
the right inlet. The `setminmax` ranges are dB: **`[-70,0]`** (a multi-band LEVEL meter)
and **`[-24,24]`** (a bipolar GAIN-REDUCTION display, with `signed=1`). So premium devices
use multislider mostly as a multi-bar METER / spectrum-bars / GR readout, NOT an editor.
The interactive case (1/5) is a Blob PARAMETER: `parameter_enable=1` + `settype` stores all
bars as ONE saved/automatable list (same Blob `parameter_type=3` idea as matrixctrl).
`setstyle` 0=bar/1=line/2=point. Kit: `add_multislider(size=, display=True, ghostbar=,
ignoreclick=, thickness=, signed=, slidercolor=, bgcolor=, setminmax=)`; theme injects
`slidercolor→accent, bgcolor→bg`. **Use when** you need N live bars (meter/GR/spectrum);
for one on/off grid use `matrixctrl`, for a single value use `live.slider`.

## ✅ live.step / live.grid  (Blob-param multi-value SEQUENCERS)

**NOT in the synced Max docs** — grounded in MEASURED corpus device JSON (verify-don't-
trust), like `live.line`. Both are **Blob parameters** (`parameter_enable=1` +
`parameter_type=3` + `parameter_invisible=1`): the ENTIRE pattern saves/automates as ONE
list — same family as `matrixctrl` / `multislider`. The step/grid count lives INSIDE that
Blob, NOT in a count attribute (the old `nstep`/`nseq`/`loop_start`/`loop_end` stub attrs
were **hallucinated** — removed this run; no real corpus box has them).

**live.step** (4 corpus instances — SliceShuffler's Mod / Pan / Direction / Slice lanes):
a multi-lane piano-roll step editor. **1 inlet / 5 outlets** (pitch, velocity, duration,
extra1, extra2 lane data). Lanes are toggled by `pitch_active` / `velocity_active` /
`duration_active` / `extra2_active` (corpus disables all but the one editable lane);
`extra1` is ranged via `extra1_min` / `extra1_max` / `extra1_signed` (e.g. Pan = −50..50
signed). `mode` selects the shown lane (corpus = 4). Colors are TWO-SHADE gradients:
`stepcolor`/`stepcolor2` (the step bars), `bgcolor`/`bgcolor2` (backdrop), `blackkeycolor`
(pitch-row black keys), `bordercolor`/`loopbordercolor`; `loopruler`/`unitruler` (0 = hide
the rulers), `extra_thickness`, `fontname` (Arial Bold). Theme injects
`stepcolor→accent, stepcolor2→accent2, bgcolor→bg, bordercolor→panel_border` (all solid).

**live.grid** (2 corpus instances — Roulette 12×12 PitchMap, SliceShuffler 32×32 Sequencer):
a monome-style cell sequencer. **2 inlets / 6 outlets** (the old 1/4 stub was WRONG).
`rows`/`columns` = visible grid; `maxrows`/`maxcolumns` = resizable cap; `direction` =
play-direction mode; `marker_horizontal`/`marker_vertical` = guide lines; `rounded`/
`spacing` = cell shape; `link` = link lanes. Colors: `stepcolor` (the lit cell — Roulette
orange, SliceShuffler magenta), `bgstepcolor`/`bgstepcolor2` (unlit-cell two-shade bg),
`bordercolor`/`bordercolor2`, `hbgcolor` (playhead-column highlight), `directioncolor`
(the direction-arrow strip), `amountcolor`/`freezecolor`. Theme injects
`stepcolor→accent, bgstepcolor→section, bordercolor→panel_border, bordercolor2→panel_border,
directioncolor→accent2`.
- ⚠️ **SOLID vs ALPHA-WASH — only the solid (alpha=1.0) attrs are token-mapped.** The premium
  sequencer look leans on ALPHA-FADED washes a solid theme token CANNOT express: the zebra
  (`bgstepcolor` white@0.05 / `bgstepcolor2` white@0.10), the hover (`hbgcolor` accent@0.35),
  the amount overlay (`amountcolor` dim-accent@0.64), `freezecolor` white@0.25. Token-mapping
  those to a SOLID colour paints the whole cell (a solid-accent `hbgcolor` would cover the
  step). So the registry maps ONLY the solid attrs (`stepcolor`/`stepcolor2`=accent/accent2,
  `directioncolor`=accent2, `bgstepcolor`=section, both borders); set the alpha-wash attrs
  per-device with explicit RGBA. (`live.step` is mostly solid — `stepcolor`/`stepcolor2`/
  `bgcolor2`/`blackkeycolor`/borders are alpha=1.0; only `bgcolor` is a black@0.05 wash.)

**Kit:** `add_live_step(...)` / `add_live_grid(...)` emit corpus-faithful boxes (display
mode by default; pass `parameter_enable=1` only when you ALSO wire the `parameter_initial`
Blob — full Blob-param automation is a separate, future step). **Use when** you need an
interactive multi-step pattern editor: `live.step` for per-step value LANES
(pitch/vel/prob/pan), `live.grid` for an X/Y cell pattern (note map / trigger grid); for a
read-only multi-bar meter use `multislider`, for an on/off routing grid use `matrixctrl`.

**Live-VERIFIED** (SequencerProbe, 2026-06): both render with their corrected I/O (grid 2-in/6-out,
step 1-in/5-out) and NO load error — `live.grid` draws its full cell matrix + the direction-arrow
strip, `live.step` its step lane. Two-accent theming visibly confirmed on the grid: cells render
`stepcolor→accent` (cyan) and the direction strip `directioncolor→accent2` (pink) under RUPTURE.

## ✅ live.scope~  (waveform / signal display)

A DISPLAY object (not a parameter) — 2 signal inlets (X, and Y for X/Y mode), 0 outlets.
Grounded in the real-device corpus (SEAR uses it as a small waveform hero, 108×20).
- **Colors are the BARE attrs** (display, like the meter — there is NO active twin):
  `bgcolor` (background), `linecolor` (the trace — the color you always see),
  `gridcolor` (grid lines). **Fix this run:** the registry mapped a non-existent
  `activelinecolor` (themed traces stayed Live-default) → corrected to theme the real
  `bgcolor → scope_bgcolor`, `linecolor → scope_color`, `gridcolor → grid_color`.
- `calccount` = samples per pixel (zoom); `mode` X/Y vs time; `range` = the amplitude
  window. Keep it small (SEAR: 108×20) as an accent waveform, not a full-width hero.
- **Z-ORDER GOTCHA** (from testing.md): `scope~` (compiled) renders ABOVE a v8ui, but
  `spectroscope~` renders BELOW — so a transparent v8ui overlay works on a spectroscope
  but is occluded over a scope. Plan overlays accordingly.
- **When native vs custom:** native `live.scope~` for a quick honest waveform/level
  trace; hand-draw a v8ui only for a stylised/circular/filled waveform the object can't do.

## ✅ unitstyle — parameter value display (cross-cutting, ALL param controls)

`unitstyle` (Inspector "Unit Style") sets how a `live.dial`/`live.numbox`/`live.slider`/
`live.gain~` displays its stored value. It is a **display-only** property — it does NOT
change the parameter's min/max/range, only the units shown in the value text + Live's
automation lane. Verified enum (from the `live.dial`/`live.numbox`/`live.slider` maxref;
deciBel=4 anchored by the `live.gain~` finding). Named constants live in `constants.py`
(`UNITSTYLE_*`) and the factory defaults now use them (no magic ints):

| # | constant | displays | use for |
|---|----------|----------|---------|
| 0 | `UNITSTYLE_INT`     | integer values | step counts, voices, semitone counts shown whole |
| 1 | `UNITSTYLE_FLOAT`   | floating-point | generic unitless value (the neutral default) |
| 2 | `UNITSTYLE_TIME`    | milliseconds (ms) | delay/attack/release/LFO time |
| 3 | `UNITSTYLE_HZ`      | frequency (Hz/kHz) | filter cutoff, LFO rate, tone — pair with `parameter_exponent≈3` |
| 4 | `UNITSTYLE_DB`      | loudness (dB) | gain/trim/threshold — `live.gain~` hardcodes this |
| 5 | `UNITSTYLE_PERCENT` | percentage | dry/wet, mix, depth, amount (the `dial()` default) |
| 6 | `UNITSTYLE_PAN`     | Left/Right | pan / stereo position |
| 7 | `UNITSTYLE_SEMITONE`| steps (st) | pitch/transpose |
| 8 | `UNITSTYLE_MIDI`    | pitch from MIDI note number | note pickers |
| 9 | `UNITSTYLE_CUSTOM`  | custom (needs `customunits`) | bespoke labels (e.g. "x", ratios) |
| 10| `UNITSTYLE_NATIVE`  | floating-point (native) | when Live should pick |

**Factory defaults (now constant-named, values unchanged):** `dial` = PERCENT (knobs are
usually mix/amount), `number_box` = FLOAT, `slider` = FLOAT, `live_gain` = DB.
**THE FOOT-GUN:** a knob built for Hz/dB/time but left at the default will silently show
"%". Always pass the matching `unitstyle=UNITSTYLE_*` for non-percentage params (a 0–20 Hz
Rate dial at the default renders "12.5%", not "2.5 Hz"). unitstyle is independent of
`parameter_exponent` (log taper) — set both for a frequency knob.

## ✅ live.gain~ / live.meter~  (fader + meter / level meter)

Verified from the `live.gain~` maxref (`~/.cache/livemcp/docs/raw/.../live-gain-*.html`).
`live.meter~` is NOT in the synced docs, so treat the `live.gain~` color model as
authoritative for both — and the corpus confirms it: AS_Console's `live.meter~` sets
`inactivecoldcolor`/`inactivewarmcolor` too, so the unlit-segment attrs apply to BOTH.

**The INVERTED color rule (the gotcha).** Unlike `live.dial`/`live.tab` (where the `active*`
twin is what you SEE at active=1), the meter's LIT segments are the **bare** attrs:

| attr | what it colors | when seen |
|------|----------------|-----------|
| `coldcolor`     | Cold (low) signal segment      | LIT (active, signal present) |
| `warmcolor`     | Warm (mid) signal segment      | LIT |
| `hotcolor`      | "Warning" (high) segment       | LIT |
| `overloadcolor` | Overload (clip) segment        | LIT |
| `inactivecoldcolor` / `inactivewarmcolor` | the Cold/Warm segment when **idle / no signal** (the dark unlit track) | `live.gain~` only — no `inactivehot`/`inactiveoverload` exist |
| `slidercolor`   | the recessed background rail (gain~ = "slider background") | always — **now themed on the meter too** |
| `textcolor`     | name + value text              | always |
| `tricolor` / `trioncolor` | the drag-triangle handle (unfocused / focused) | always |
| `tribordercolor`| triangle border (unfocused)    | always |

So the registry maps the BARE attrs → `meter_cold/warm/hot/over` tokens (correct).
There are NO `activehot`/`activeoverload` attrs; `activecoldcolor`/`activewarmcolor`
appear in the attr index but are undocumented duplicates — do not rely on them.

**`slidercolor` fix (2026-06):** the meter's recessed BACKGROUND rail (`slidercolor`,
gain~ maxref = "the slider background color") was un-themed on the kit `meter` (it was
only on `live_gain`), so the channel behind the segments was Live-default grey. The corpus
`live.meter~` (AS_Console, 2/2) sets it dark **`[0.098,0.098,0.098,1]`** — measurably the
**`surface`** token (≈0.1), NOT the accent — so the registry now maps `meter slidercolor →
surface`. (It only takes effect when a metering device is REBUILT; installed `.amxd`s are
unchanged until then — 6 devices use the meter, so Live-verify the rail on the next rebuild.)

**`live.gain~` essentials:** parameter (Float, `unitstyle=4` = dB); `min/max` default
-70..+6 dB, init 0; `orientation` 0=Vertical (default) / 1=Horizontal; 2 signal inlets,
**5 outlets** `["signal","signal","","float","list"]` (out 3 = gain float, out 4 = the
peak-level list, rate set by the `interval`/`min` 10ms–2s message). `live.meter~` is the
display-only sibling (1 inlet, 1 outlet = peak value).

**Premium usage:** lit segments use the theme `meter_*` tokens; the idle track now themes
automatically — the registry maps `inactivecoldcolor`/`inactivewarmcolor` → `text_dim`
(corpus AS_Console sets them to a mid-grey ~0.5, so the unlit rail reads as a consistent dim
strip instead of Live-default grey — fixed this run, for both `meter` and `live_gain`); the
drag handle themes via `tricolor`/`trioncolor` → accent. Use
`live.gain~` for an output trim with visual feedback; bare `live.meter~` for a read-only
level display next to a custom fader.
- ⛔ **WHEN to add a meter — and when NOT to (user-directed rule, 2026-06).** Do NOT add a
  per-device **output LEVEL meter**: Live already shows the signal level **between every
  device** in the chain, so a device's own output-level bar is redundant wasted space — which
  is exactly why the stock Live devices omit one. ONLY add metering that Live does NOT show:
  **gain-reduction (GR)** for a comp/limiter, **True-Peak / LUFS** loudness readouts (numbers,
  not a level bar), a **spectrum/scope**, or a **correlation/phase** meter. (Applied: the output
  level-meter bars were stripped from Ceiling / Heat / Sheen; Ceiling's TP+LUFS readouts stayed.)
  A `live.gain~` is fine when its METER is incidental to an output-GAIN *fader* you actually want.

**When native vs custom:** native `live.gain~`/`live.meter~` is the premium default
(real ballistics, dB ticks, automatable) — do NOT hand-draw a meter in v8ui unless you
need a non-standard shape (circular/radial) or a histogram the native object can't do.

## ✅ live.drop  (file / sample drop target — IO intake)

DOC-grounded (live.drop maxref; **0 corpus instances**, so the synced doc is the sole
ground truth — a prior 'ScratchBacker/Mosaique 2-outlet' grounding in the kit was
**fabricated** and was removed). Drag a file from Live's browser / Finder / Max file browser
onto it; the **absolute pathname** is sent out its **single** outlet as one quoted symbol.
Route it through `prepend read` into a `buffer~` / `sfplay~` / `jit.movie` to actually load.

- **`decodemode`** [int] (default ENABLED): the signature attr. ON → Live decodes non-PCM
  drops (`.mp3`/`.mp4`/`.mov`/`.flac`…) to extracted audio and the outlet reports a TEMP
  decoded-file path. Set **0** to pass the ORIGINAL file path (movies for `jit.movie`, or
  raw data Live can't/shouldn't decode).
- **`legend`** [symbol] (default `Drop Something Here!`): the prompt text in the display area.
- **Colors (doc-verified):** `color` = the box **OUTLINE** (NOT a fill — live.drop has **no
  bgcolor**), `textcolor` = display text, `bordercolor` / `focusbordercolor` = border
  (unfocused / focused). `textjustification` aligns the text. Supports a `jspainterfile`
  painter for a fully custom look (it's in the attr list).
- **Messages:** `set <path>` stores an initial filepath (persists / reported on init — how a
  device remembers its loaded sample), `clear` clears it, `bang` re-outputs the current path.
- **Kit:** `add_live_drop(...)` (numoutlets **1**, the prior 2 was the fabrication); theme
  injects `color`/`bordercolor → panel_border`, `textcolor → text`, `focusbordercolor →
  accent` (the focus ring pops).
- **When native vs custom:** native `live.drop` is THE way to take a file/sample into a device
  (granular source, IR/convolution loader, wavetable import). Overlay it transparently
  (alpha-0 colors) on a waveform hero so the whole display is the drop zone (see `recipes`
  sample-loader stage). Don't hand-roll drag handling in v8ui — only live.drop receives
  Live-browser drags.

## ✅ swatch  (colour picker / display — utility)

MEASURED from the official M4L corpus (1 instance; absent from synced docs and the downloaded
corpus). A clickable colour field that outputs the chosen colour. **3 inlets / 2 outlets**
`["", "float"]` (the prior stub's 1-in / 4-out was guessed and wrong) — outlet 0 emits the colour
(list), outlet 1 a float. No styling box attrs: its displayed colour IS its runtime VALUE (set by
a message), so there is nothing to theme. Measured attrs: `compatibility` (a Max compatibility-mode
flag), `parameter_enable` (corpus 0). **Niche for audio** — use for a colour-pick utility or a
user-themeable accent control; for a normal value use a `live.*` control.

## ✅ Premium SPECTRUM rendering — constant-Q smoothing (the Rainbow / Pro-Q look)

Live-verified (2026-06, vs Rainbow + Pro-Q + EQ8 on a sustained chord; Rainbow `display.js`
read as ground truth — see `research/amxd_corpus/studies/Rainbow/SPECTRUM_GRID_EQ_MECHANICS.md`).
A spectrum looking "fucked up" — sharp needles, blocky wide lows, jagged "grass" highs — starts
from ONE root cause: **plotting raw LINEAR FFT bins on a LOG-frequency axis.** An FFT gives
evenly-spaced bins (~23 Hz @ 2048/48k); a log axis makes each octave equal width, so:
- **Lows:** 20–100 Hz is a big slice of screen but holds only ~4 bins → blocky/wide/low-def.
- **Highs:** 5 k–20 k is a thin slice holding ~thousands of bins → dense jagged grass.
- A tonal source's partials become needles on top.

**The fix — MAX-per-pixel-COLUMN rebin (NOT constant-Q averaging).** This is what Rainbow,
Ableton Spectrum and EQ8 actually do (verified). For each integer pixel COLUMN, forward-map
every FFT bin to its column (`round(freqToPos(binF))`) and keep the **single loudest bin** in
that column; interpolate the sparse low columns between filled neighbours. NO frequency
averaging, NO mean blend, NO octave band.
- ⛔ **REVERSAL of the old advice below:** an earlier constant-Q / fractional-octave rebin
  (`peak*0.8 + mean*0.2`, widen the band, spatial+temporal Avg, +4.5 dB tilt) was tried and the
  user rejected it — it read as a **smeared "blob"** that lost EQ8/Pro-Q detail. **Do NOT
  octave-average a hero spectrum.** Max-per-column keeps lows smooth (≤1 bin/col → a line
  between bins) and highs honest (many bins/col → the max rides the partials).
- **NO display tilt by default** (`slope = 0`). Tilt lifts the empty noise floor into a fake
  rising diagonal and was reverted; only add it if a device explicitly wants SPAN-style balance.
- **Two smoothness levers are DSP-side, not averaging** (the real reason Rainbow looks smooth):
  1. **FFT size.** 2048 (Rainbow, `fftSize=2048` + `overlap=4`) blurs a chord's harmonics into a
     smooth hump; 4096 resolves each harmonic as a razor spike → a GRASSY COMB. **Use 2048 for a
     Rainbow-smooth look** (4096 only if you specifically need finer low-freq resolution and
     accept the grass). Halving the FFT runs the analyzer ~+6 dB hotter — re-trim.
  2. **Per-column fall-clip (Rainbow's anti-grass secret).** Each column rises instantly but may
     FALL only ~2 dB/display-frame (`spectDClipDown`), so columns BETWEEN harmonics decay slowly
     from their neighbour instead of plunging to the floor → the envelope stays smooth. (A plain
     `disp*0.82 + v*0.18` release does NOT do this — it settles each gap to the floor = grass.)
- **VERTICAL FILL — ceiling at 0 dBFS, not +12.** A spectrum that "sits squished at the middle /
  body cut off / only the tops of the needles show" almost always has its dB ceiling above 0
  (e.g. `MAX_DB=+12` reserves headroom real audio never reaches). Set the top of the dB map to
  **0 dBFS** (our Spectrum Analyzer: `-78..0`) and trim so the loud low-mids land in the upper
  third. Rainbow uses `-90..+18` but its FFT runs hot enough to reach it.
- **Render STYLE = a thin full-alpha LINE (~1.1 px) carrying the shape + a LIGHT, FLAT fill**
  (Rainbow `spectFill = [1,1,1,0.05]` — a 5% white whisper, NOT a gradient and NOT a saturated
  blob). Build the polyline → close to just BELOW the floor (`bottom+2`, off-screen) →
  `path_roundcorners(4)` → `stroke_preserve` the line → `fill` the wash. A heavy/gradient fill
  reads crude; the line + whisper reads "airy/pro."

**Two kit renderers — when each:**
- **`spectroscope~`** (compiled, `device.add_compiled_ui` / `add_compiled_display`): stock,
  cheap, portable, great as a quick spectrum BACKDROP behind an EQ curve. BUT its rendering
  is FIXED — its lows look wide/blocky and you can't reshape it. Good enough behind a busy
  curve; not for a hero spectrum.
- **`fft_analyzer` buffer + v8ui draw** (`engines/fft_analyzer.py` → `buffer~`, polled by a
  jsui that does the MAX-per-pixel-column rebin above; `plugins/spectrum_analyzer`
  `update_analyzer_from_fft`, and `engines/eq_curve.py` for the EQ graph's built-in spectrum):
  full control → smooth Rainbow-grade curve, **and** it can add note-peak labels,
  LUFS/True-Peak/correlation, pre/post overlay. PREFER this for any premium/hero spectrum;
  converge devices onto the one renderer + FFT (2048/overlap-4) rather than 3 different ones.
- Max **caches a v8ui by `js_filename`** — bump the filename on ANY draw change or you'll see
  the stale compile.
- ⚠️ **Named `buffer~` COLLISION on duplication (Live-verified 2026-06):** `fft_analyzer.py` names
  its analyzer buffer `f"{id_prefix}_specbuf"` — a FIXED, GLOBAL name. `buffer~` names are global
  across the Max app, so TWO instances of the same device (after `duplicate_track`, or two copies in
  a Set) bind the SAME buffer; deleting one leaves the survivor's analyzer **DEAD** (spectrum blank
  though audio is loud / output meter ~0.85). **Reload the device to recover.** Proper fix (tracked):
  per-instance-unique name like Rainbow's `DEVICE_UNIQUE_ID+name` (a `#0` prefix or a
  `live.thisdevice`/LOM-derived suffix). Symptom signature: loud meter + totally empty analyzer = a
  dead/again-unfed buffer, not a render bug.
- ⚠️ **`send`/`receive` need the `---` LOCAL prefix (same collision class, 2026-06).** A bare
  `s name`/`r name` is GLOBAL across the whole Live set, so two instances of a device cross-talk
  (one's data bleeds into the other's processing AND its UI display). M4L's per-instance namespace is
  the **`---` prefix**: `s ---name` / `r ---name` is local to that device instance. Fleet-audited all
  33 devices with the official-checklist `nonlocal-send` rule — only **linear_phase_crossover** had
  bare sends (`lps_low_bin`/`lps_high_bin`, the FFT-bin pair feeding its monitor display); FIXED by
  `---`-prefixing both the `s` and `r` sides (intra-device routing preserved, instances isolated).
  The `checklist/nonlocal-send` rule is opt-in (`final_checklist_issues`), so run it periodically:
  build each device → `final_checklist_issues(d.boxes)`. The theme/UI buses already use `---`.

## ✅ mgraphics.path_roundcorners(radius) — round an angular v8ui path into a curve

Native mgraphics method (Max JS API, doc-confirmed): **`path_roundcorners(radius: number)`** —
*"Round the corners of the current path … to the radius provided, or as close as possible
depending on the path's angle."* Build the path (`move_to`/`line_to`/…), then call
`mgraphics.path_roundcorners(r)` **before** `stroke`/`fill`/`stroke_preserve` and every corner
is rounded. This turns a polyline of straight `line_to` segments into a smooth ORGANIC curve —
the cure for the "straight lines / angular" look on ANY v8ui spectrum, EQ curve, envelope, or
transfer graph. Cheap, native, no manual bezier math. Rainbow uses `path_roundcorners(4)` on its
spectrum (display.js `displayNormal`: build path → close to floor → `path_roundcorners(4)` →
`stroke_preserve` + `fill`); Live-verified in our Spectrum Analyzer at radius 4.

## ✅ Native-compositing hero — a premium display with ZERO jsui (SliceShuffler J74)

A premium "data-inside-data" hero can be built ENTIRELY from STOCK native objects stacked on
ONE rect — no jsui/v8ui/`paint()`/compile step. Code-verified from SliceShuffler J74 (the whole
device has zero jsui): its "waveform inside the 32-step sequencer" hero = 5 native boxes on one
~795×285 rect:
- a themed **`live.grid`** at the BOTTOM of the z-stack (the sequencer matrix);
- **4 `waveform~` overlays** stacked ON TOP, each with **`bgcolor` alpha 0** (the grid shows
  through), **`gridcolor` alpha 0** (no double-grid), **`selectioncolor` alpha 0**, and
  **`ignoreclick 1`** (so clicks fall through to the `live.grid` beneath);
- a border-only **`panel`** (fill alpha ~0.01) as a glass frame contributing only its accent border.

**Z-order = box order** (earlier box = further back): add the grid first, the `waveform~` overlays
last so they draw in front. **GHOST-LAYER trick:** keep a SECOND `waveform~` pair on the same
rect/buffer-sizing but pointed at a different buffer (e.g. the un-processed original) with
**`waveformcolor` alpha 0** (invisible); reveal it by raising one alpha — no re-layout — and a
`live.menu` toggles which is foregrounded.

**When vs custom v8ui:** prefer native-compositing for ANY "trace/scope/grid/meter composite"
where a stock `waveform~`/`live.grid`/`live.meter~`/`filtergraph~`/`scope~` already renders the
data — it's cheaper, fully themed, portable (all stock, no externals), and interactive for free.
Reserve custom v8ui for shapes native objects can't draw (bespoke curves, XY pads, particle
clouds, animated reels).

### ⚠️ Compiled display OVER an interactive v8ui = it EATS the clicks (Live-verified, 2026-06)

Z-order has teeth, not just looks: a COMPILED Max display (`spectroscope~`, `scope~`, `waveform~`,
`meter~`, `filtergraph~`) renders ABOVE a `jsui`/`v8ui` **regardless of patcher box order**, AND
it CAPTURES the pointer in its rect — so a v8ui beneath it stops receiving clicks/drags **even when
the compiled object is invisible** (`fgcolor` alpha 0). Symptom: *"the controls around the graph
work, but the graph itself is dead — can't grab the nodes."* Cost a real debugging session on
Parametric EQ V2: a leftover `spectroscope~` sized to the EQ's inner plot rect and `script show`n
in the FULL view silently blocked EVERY node click; it was pure dead weight once the `eq_display`
v8ui drew its own spectrum (`external_spectrum=False`). Removing it (box + `script show/hide` msgs
+ signal feed) restored interaction.

**Rules:**
- An interactive v8ui (EQ curve, XY pad, draggable nodes) must have its clickable rect FREE of any
  compiled UI object on top. Put the compiled spectrum/scope STRICTLY BEHIND it (add it FIRST, keep
  it within the v8ui's *non-interactive* margins) — or draw the data INSIDE the v8ui and drop the
  compiled object entirely (the Para EQ now does the latter: max-per-column spectrum in the jsui).
- `ignoreclick 1` lets clicks fall THROUGH a compiled overlay. It is a **universal Common Box
  Attribute** (`[int]`, grounded 2026-06) — present in EVERY object's refpage boilerplate, even
  non-UI objects like `pak`, so it is syntactically valid on `spectroscope~`/`scope~`/`waveform~`
  alike (it will set without error). What varies is the BEHAVIOR: click pass-through is
  **corpus-proven for `waveform~` over a `live.grid`** (SliceShuffler, above) — the right tool for a
  NON-interactive compiled DISPLAY stacked on an interactive NATIVE control — but is **unverified for
  `spectroscope~`** (the object itself is absent from the synced docs). So don't TRUST it to free an
  interactive v8ui sitting under a `spectroscope~`; go behind or remove (or Live-verify first).
- Debug heuristic: if "clicks work everywhere EXCEPT over one rectangle," a compiled UI object is
  covering exactly that rectangle.

**Fleet audit (2026-06)** — every device with a compiled scope + a graph v8ui:
- **Parametric EQ V2** — was BROKEN (the `spectroscope~` over the EQ plot ate all node clicks);
  FIXED by removing it (the v8ui draws its own spectrum). ✓
- **Linear Phase EQ V2** — clean: its `spectroscope~` was already removed (RC-8, CPU). ✓
- **Strip** — a LATENT version of the same trap, VISUAL not click (`tone_display` has
  `ignoreclick 1`, so no interaction is blocked): the `tone_scope` spectrum renders ABOVE the
  `tone_display` v8ui, so the amber tilt curve sits BEHIND the spectrum, not on top as the code
  comment claimed. FIXED + Live-verified (2026-06): dropped `SPEC_FG` alpha **0.7 → 0.32** so the
  amber curve + grid read clearly through the now-faint spectrum backdrop (confirmed with a
  Tilt-+5 curve over a live signal). When a v8ui overlay MUST sit visually in front of a compiled
  display, either keep the compiled object SEMI-TRANSPARENT (this) or draw the data in the v8ui.

## ⚠️ jsui vs v8ui — the default `border 1` box (Live-verified + corpus-grounded, 2026-06)

A bare **`jsui` defaults to `border 1`** — a 1px box OUTLINE drawn at the box edge ON TOP of
whatever the JS paints. For a **transparent overlay** (a jsui that paints no opaque background — a
selected-band knob strip, a logo, an icon, a custom control) that outline renders as a **stray empty
rounded-rectangle around the control**. **`v8ui` does NOT draw this** (identical box attrs, only
`maxclass` differs) — which is exactly why `device.add_custom_knob` uses **v8ui**, not jsui (*"the
v8ui blends seamlessly instead of showing an opaque object box"*).

- **Symptom:** a faint box hugging a jsui's rect that no `add_panel` accounts for. It moves WITH the
  jsui if you relocate the control (the tell it's the object, not a panel). Cost a long Para EQ
  debug: the *"black box around the knobs"* was NOT `left_strip_frame` (already hidden) and NOT the
  JS (`SHOW_FRAME=0`) — it was the jsui's own `border 1`.
- **Why some jsui never show it:** ones that PAINT an opaque background (drift `hero`, knocker
  `scope`) cover the inside; the 1px edge still draws but reads as an intentional framed display.
- **Fix:** set **`border=0`** on the jsui box. Grounded: `Chiral.json` ships `"border":0` on its
  jsui. **The kit `jsui()` factory now defaults `border=0`** (2026-06) — a device that wants a
  visible frame passes `border=1` (kwargs win). Latent until each device is rebuilt; at-risk display
  jsui (shard/pocket_delay/linear_phase_crossover) all sit inside panels, so losing the redundant
  edge is safe.
- **Decision:** interactive custom control → **v8ui** (pointer-aware, no border, blends). Pure
  display drawn by JS → jsui with `border=0` (lighter than v8ui). Never leave a transparent jsui on
  the default border.
- ⚠️ **v8ui DRAG = `onpointermove`/`onpointerup`, NOT `ondrag` (fix 2026-06).** jsui's continuous-
  drag callback **`ondrag` is NEVER called on a v8ui box** — `onclick` (mouse-down) still fires, so a
  v8ui control built with jsui-style `ondrag` is **click-only, the puck/value won't drag** (the
  "can't move the dots" pitfall). On v8ui, `onpointermove(x,y,but,…)` fires on EVERY move (guard the
  drag with `if (but === 0) return;` so HOVER moves are ignored) and `onpointerup` ends the drag.
  **Found + fixed 5 kit controls that were emitting `ondrag` on a v8ui box** — `add_custom_knob`,
  `add_custom_slider`, `add_custom_stepper`, `add_custom_readout` (all in `engines/ui_kit.py`) and
  `add_xy_pad` (`engines/ui_xy_pad.py`); all were undraggable (e.g. drift's custom knobs). Renamed
  `ondrag`→`onpointermove` (the existing `but===0` guard already handles hover/release). The proven
  reference is `delay_trail`/`ui_curve_node`, which already use `onpointermove` (jsui engines —
  `eq_curve`, `eq_band_column`, `xy_pad` — correctly keep `ondrag`). The `paint()` is unchanged so
  the LOOK is identical (drag-behaviour only); takes effect on each device's next rebuild.
- ⚠️ **A JS fix does NOT deploy until the sidecar FILENAME changes** — Max caches `.js`/`v8ui`
  sidecars BY NAME for the whole Live session, so a rebuild that re-emits the same filename serves
  the STALE cached JS (the drag fix would never take). The custom controls use a STATIC version
  suffix (`{id}_knob_v2.js` etc.), so the drag fix required a manual bump: `knob v2→v3`,
  `slider`/`stepper`/`readout`/`xypad` `v1→v2` (`device.py`). Deployed + Live-verified: rebuilt
  drift (+ uikit demos) → `Drift.amxd` now references `*_knob_v3.js`, the on-disk sidecar contains
  `onpointermove` / no `ondrag`, and drift's 6 custom knobs render correctly.
- ✅ **NOW AUTOMATIC — content-addressed JS sidecars (2026-06).** `add_v8ui`/`add_jsui` take
  `content_address=True`, which folds a `blake2b` hash of `js_code` into the sidecar name
  (`{stem}_{hash}.js`, via `js_sidecar_name` in `engines/design_system.py` — the JS mirror of
  `gendsp_support_name`). **All 11 kit custom-control methods** (`add_custom_knob`/`slider`/`stepper`/
  `readout`/`toggle`/`cycle`/`glyph`/`segment`/`curve_node`, `add_xy_pad`, `add_glass_panel_bg`) now
  set it, so any JS engine edit auto-renames the sidecar → Max reloads fresh with **no manual `_vN`
  bump ever** (the stale-JS-cache failure class is closed, like the gen~ side). The `_vN` suffixes
  and `version_tag()` fold are retired. Default is OFF so a fixed `js_filename` you assert in a test
  stays exact. Takes effect on each device's next rebuild (JS content unchanged → drag still works).
- **Debug tip:** a rebuilt `.amxd` is greppable via `strings` (it's an `ampf` container w/ embedded
  patcher JSON) — extract a box's `presentation_rect`/attrs directly to see what shipped instead of
  guessing about Live/Max caches.

## ✅ Modifier keys on an interactive v8ui graph (the Pro-Q / EQ8 node-edit scheme)

A draggable-node graph (EQ curve, XY pad, transfer curve) is the premium reason to reach for a v8ui
over native controls — but it only feels pro if it honours the **modifier keys** the engineer's
muscle memory expects from Pro-Q / EQ Eight. Grounded two ways:

- **Reading modifiers off the v8ui `PointerEvent`** (Max JS API `PointerEvent` doc — these are the
  CORRECT property names, NOT the DOM `metaKey`/`optionKey`, which are dead on a v8ui event):
  - `pointerevent.shiftKey` — Shift
  - `pointerevent.altKey` — Alt / Option
  - `pointerevent.commandKey` — **Cmd on Mac, Ctrl on Win** (Max extension)
  - `pointerevent.contextModifier` — right-click or Ctrl-click on Mac (the context-menu modifier)
  - `pointerevent.capsLock` — caps-lock state
  Every pointer event (down AND move) carries the current modifier state, so read it FRESH inside
  `onpointermove` (don't latch it at press) — holding/releasing Shift mid-drag must change the feel
  live. The kit wraps these in `pointer_shift_key()`/`pointer_option_key()`/`pointer_command_key()`
  helpers (in `eq_curve.py`) that fall back to the positional jsui-callback args, so the SAME engine
  works under both the v8ui `onpointer*` path and the legacy jsui `onclick`/`ondrag` path.
- **The canonical premium mapping** (FabFilter Pro-Q help — `fabfilter.com/help/pro-q/using/eqdisplay`,
  and EQ Eight agrees): the authoritative grounding when a phren note disagrees (one did — it had
  Cmd=axis-lock / Alt=solo, both WRONG). For node dragging:

  | gesture | does | kit `eq_curve` status |
  |---|---|---|
  | plain drag | freq + gain | ✅ |
  | **Shift + drag / wheel** | fine-tune (~6.7× here) | ✅ |
  | **Cmd/Ctrl + drag (vertical)** | adjust Q | ✅ |
  | **Alt + drag** | **constrain to one axis** (horizontal=freq, vertical=gain/Q) | ✅ (2026-06) |
  | **Alt + click** a node | toggle band **bypass** (NOT solo) | ✅ |
  | wheel / Shift+wheel | Q / fine Q | ✅ |
  | Cmd+Alt+click | change shape; **Alt+Shift+click** = change slope | ⬜ backlog |
  | Alt+wheel / Cmd+wheel | dynamic range / gain | ⬜ backlog |

- ⚠️ **EQ8 ≠ Pro-Q on Alt — they CONFLICT (Ableton manual, grounded 2026-06):** Ableton's own EQ
  Eight uses **Alt/Option + drag = Q** (its ONLY drag modifier; plain drag = freq+gain), and exposes
  band "solo" through **Audition mode** (the headphone icon — *"clicking and holding a filter dot lets
  you hear only that filter's effect"*), NOT a modifier-click. So a device cannot honour BOTH muscle
  memories on Alt: Pro-Q wants **Alt=constrain + Cmd=Q**, EQ8 wants **Alt=Q**. The kit follows
  **Pro-Q** (a deliberate product choice, not a bug) — pick ONE house convention and document it on
  the device. (This also explains the bogus "Alt+click=solo" phren note that misled an earlier pass:
  solo is an EQ8 *Audition-mode* feature, never a Pro-Q modifier-click.)
- **Click-vs-drag disambiguation (the key pattern):** Alt is BOTH a click action (bypass) and a drag
  action (constrain). Resolve by **arming a drag on Alt-press WITHOUT firing the click action**, then
  on `onpointerup` fire the discrete action **only if the press never travelled** (`alt_moved` stays
  0); any travel means it was a constrain-drag, so suppress the toggle. Same shape for any
  modifier that means one thing as a tap and another as a drag.
- **Test without a mouse:** the `tests/test_js_behavior.py` harness EXECUTES the engine JS and drives
  `onpointerdown`/`onpointermove`/`onpointerup` with `{x,y,buttons,altKey,…}` events — so gesture +
  modifier logic is unit-tested headlessly (LiveMCP can't synthesize a modifier-drag). Add a case per
  gesture; assert the emitted band params + that a constrain-drag does NOT toggle bypass.
- ⚠️ **Edge-label collision (node caption vs axis scale):** when a draggable node reaches a plot edge
  its number/value caption competes with the axis scale labels for the same pixels. Observed on Para
  EQ (2026-06): a band dragged to the far RIGHT (~19 kHz) parks ON the right-edge dB scale — the node
  occludes the `-36` label and its "4" number crowds the `-24`/`-36` zone. Premium fix (Pro-Q does
  this): (a) FLIP the node caption to the INNER side when it's within ~caption-width of an edge, and
  (b) dim or skip the axis label a node currently overlaps. Draw-only (mgraphics layout) so the
  gesture test harness can't catch it — Live-eyeball a node parked at each edge.
- ⚠️ **Filled response curve must plot EVERY point — never skip below-floor points then close to the
  baseline (the "phantom-boost" bug):** a filled EQ/transfer curve closes its path with
  `line_to(x_last, zero_y)`. If the point loop SKIPS points whose dB is below the display floor (e.g.
  nulling them via a `curve_db_is_visible` gate), the fill connects the LAST visible point straight to
  the 0 dB baseline at the far edge — drawing a phantom rising lobe. **User-found on Para EQ (2026-06):
  a low-pass dragged far left rolled off then the FILL climbed back to 0 dB on the right, reading as a
  high-boost that wasn't in the audio.** Fix: CLAMP each composite point to the display floor and plot
  ALL of them (so the FILL pins along the bottom across the stopband). **But DECOUPLE the stroke from
  the fill:** the bright outline should GAP where the curve is at/below the floor (a per-point `vis`
  flag) so the line drops and EXITS through the bottom — a line glued along the very bottom edge reads
  as a hard artifact (user-flagged 2026-06; fill pins, stroke gaps). **Fleet audit: the bug
  was UNIQUE to `eq_curve.py`'s composite** (read-verified 2026-06): `linear_phase_eq_display` pushes
  every point with a deep `GRAPH_FLOOR=-180`; `filter_curve` + `loop_filter_curve` CLAMP db inside
  their `db_to_y` (to `[MIN_DB,MAX_DB]` / `[-24,9]`); `crossover_display` draws band REGIONS not a
  magnitude curve; `peaking_eq_display` (currently UNUSED by any device) clamps db in its response loop
  (`if (db < MIN_GAIN) db = MIN_GAIN; …`) BEFORE `gain_to_y`, so its unclamped `gain_to_y` is only ever
  fed in-range values — no gap.
  All immune; only `eq_curve` skipped-then-closed. Draw-only, so not unit-testable — eyeball an
  LP/HP/deep-notch parked at each extreme.

## ⚠️ spectrumdraw~  (multi-trace spectrum — needs a BUNDLED external, does NOT render bare)

MEASURED from the official M4L corpus (4 instances, 100% consistent; absent from synced docs and
the downloaded corpus). The multi-trace FFT spectrum graph. **4 signal inlets / 1 outlet** (`[""]`)
— feed up to 4 signals to OVERLAY 4 spectra (input vs output, L / R, with / without sidechain).

> ⚠️ **LIVE-VERIFIED GOTCHA (DisplayProbe, 2026-06):** `spectrumdraw~` is a **compiled external
> (`spectrumdraw~.mxo`) that is NOT in the stock Max install** — it ships ONLY bundled inside
> specific Ableton devices (Convolution Reverb bundles `spectrumdraw~.mxo`/`.mxe64`). A bare
> `spectrumdraw~` box loads with NO error but renders the striped **classname placeholder** (the
> external can't be found) — confirmed even with the full official attr set + signal fed in. So
> `add_spectrumdraw` is only usable if you ALSO bundle the proprietary external (dubious). **For a
> spectrum in the kit, use `spectroscope~` (stock) or the compiled `fft_analyzer` / jsui display
> instead.** (Contrast `waveform~`, whose `.mxo` IS stock, so it renders bare.) The attrs below
> remain corpus-accurate for the rare case you do bundle the external.

- **`amprange`** [lo, hi] dB (corpus `[-80, 10]`). **`ampgrid`** / **`amplabels`** /
  **`freqgrid`** / **`freqlabels`** toggle the grids + labels.
- **Per-trace:** `color` / `color2` / `color3` / `color4` + `thickness` / `thickness2` /
  `thickness3` / `thickness4` — one color + width per overlaid spectrum.
- **Analysis:** `octavesmooth` (fractional-octave smoothing, corpus ~1/6), `timesmooth`
  [attack, release] ms, `fftsize` (index), `mode`, `curvestyle`, `mousemode`.
- **Kit:** `add_spectrumdraw(amprange=, color=, octavesmooth=, freqgrid=, …)`; theme injects
  `color→accent`, `color2→accent2` (the comparison trace), `bgcolor→scope_bgcolor`.
- **When native vs custom:** because `spectrumdraw~`'s external isn't stock (see the gotcha above),
  the kit's REAL spectrum solution is `spectroscope~` (stock) via `device.add_compiled_ui(...)` /
  `graph.spectrum_kwargs()` — NOT `spectrumdraw~`. **Live-VERIFIED (2026-06):** fed white noise
  through the shipped Parametric EQ V2 and its `spectroscope~` renders a live spectrum behind the
  EQ curve — so the recommended alternative is confirmed working end-to-end. Use `waveform~` /
  `live.scope~` for a time-domain trace, `filtergraph~` for a filter response.

### ✅ External-availability audit (2026-06) — spectrumdraw~ is the ONLY landmine

Triggered by the spectrumdraw~ gotcha: every kit widget whose maxclass is a compiled external was
checked against the stock Max externals folder
(`…/Ableton Live 12 Suite.app/…/Max/.../C74/externals`). **Result — all clear except one:**
`scope~`, `spectroscope~`, `meter~`, `filtergraph~`, `plot~`, `waveform~`, `live.gain~`,
`live.meter~`, `function`, `nodes`, `multislider`, `matrixctrl`, `pictctrl`, `swatch`, `kslider`,
`nslider` all have a **stock `.mxo`** → they render in a bare device. The `live.*` controls
(`live.dial`/`live.tab`/`live.text`/`live.scope~`…) are **built into the Max app** (no `.mxo`
file) → also always available. **`spectrumdraw~` is the SOLE kit maxclass with no stock external**
(ships only bundled inside Convolution Reverb). So no other widget carries the spectrumdraw~ risk.
RULE: a non-`live.*` `~` object is only safe if its `.mxo` is in that stock folder; re-run this
check before adding any new compiled object to the kit.

## ✅ waveform~  (buffer~ audio display + drag-to-select region)

MEASURED from the official M4L corpus (7 instances, 100% consistent; absent from synced docs and
the downloaded corpus). Draws the audio in a named `buffer~` and (unless `ignoreclick`) lets the
user drag-select a region. **5 inlets / 6 outlets** `["float","float","float","float","list",""]` —
the float outlets emit the selection bounds (start / end) as you drag; outlet 4 is a list.

- **`buffername`** (required): the `buffer~` to display.
- **Colors:** `waveformcolor` (the trace), `selectioncolor` (the drag-selection highlight),
  `bgcolor`, `gridcolor`, `bordercolor`, `linecolor`, `labelbgcolor` / `labeltextcolor` (corpus
  saves them alpha-0 — runtime-skinned).
- **Display toggles:** `labels`, `ruler` (time ruler), `vticks`. `ignoreclick` 1 = display-only
  (no selection); `allowdrag` / `setmode` control drag behaviour.
- **Kit:** `add_waveform(buffername=, waveformcolor=, selectioncolor=, ruler=, ignoreclick=, …)`;
  theme injects `waveformcolor→accent`, `selectioncolor→accent2`, `bgcolor→scope_bgcolor`,
  `gridcolor→grid_color`.
- **When native vs custom:** `waveform~` is THE buffer display + region picker (sample / granular
  front-end). For a live signal trace use `live.scope~`; for a spectrum use `spectroscope~`; for a
  static drawn curve use `function`. Hand-roll a v8ui waveform only for a stylised non-standard
  render the object can't do.

## ✅ live.adsrui  (ADSR envelope editor)

MEASURED from the official M4L corpus (2 instances, identical; absent from synced docs and the
downloaded corpus). The native A / D / (S) / R envelope editor — drag the handles to shape it.
**10 inlets / 10 outlets, all UNTYPED** (`[""]*10`); the prior kit stub's 1-in / 4-out 'float'
outlets were guessed and WRONG (it did already emit the right maxclass `live.adsrui`).

- **Per-stage TIME AXES (ms):** `attack_domain` / `decay_domain` / `release_domain` [lo, hi]
  (corpus attack `[0, 60000]`, decay `[10, 60000]`, release `[10, 30000]`). Live values:
  `attack_time` / `decay_time` / `release_time` (ms).
- **Extra handles:** `enable_initial` / `enable_peak` / `enable_final` [int] (corpus all 0 — a
  plain ADSR; enable them for an initial / peak / final level handle).
- **Behaviour:** `outputmode`, `show_slopehandles` (curve/slope handles), `tethering`.
- **Colors (the `active*` set — bare twins are the runtime skin):** `activebgcolor` (display bg,
  corpus alpha-0, bound to a `themecolor` expression at runtime), `activelinecolor` (envelope
  line), `activehandlecolor` (drag handles). Themed `activebgcolor → scope_bgcolor`,
  `activelinecolor → accent`, `activehandlecolor → accent`. (Saved with `themecolor.*`
  expressions in `saved_attribute_attributes` — the runtime live.colors binding.)
- **When native vs custom:** use `live.adsrui` for a real ADSR shaper (canonical Live envelope
  look + drag); for an arbitrary multi-breakpoint / transfer curve use `function`.

## ✅ filtergraph~  (EQ / filter-response editor → biquad coefficients)

MEASURED from the official M4L corpus (11 instances, 100% consistent; absent from the synced docs
AND the downloaded corpus). The COMPILED native filter editor: drag the curve to design a filter,
and outlet 0 emits the coefficient **list** for `biquad~` / `cascade~` — so it is BOTH the UI AND
the coefficient source. **8 inlets / 7 outlets** `["list","float","float","float","float","list","int"]`
(the prior stub defaulted to 1/1 — wrong).

- **`domain`** [lo, hi]: X-axis frequency range (corpus `[20.0, 22050.0]` Hz).
- **`value_range` → `range`** [lo, hi]: Y-axis gain (LINEAR amplitude, e.g. `[0.0725, 4.0]`); set
  `dbdisplay 1` to label it in dB.
- **`nfilters`** [int]: filter count. **`setfilter`** [list] `[idx, type, bypass, …, freq, gain, Q]`
  defines a band. **`logmarkers`** [list]: the log-spaced freq grid (corpus `[50, 500, 5000]`).
- **Colors:** `bgcolor`, **`markercolor`** (the freq GRID — NOT `gridcolor`, which was a dead guess
  in the registry), `curvecolor` (response curve), `hcurvecolor` (highlighted curve),
  `bwidthcolor`/`hbwidthcolor` (bandwidth fill), `fgcolor`, `textcolor`. `parameter_enable` is 0
  (a coefficient source, not a Live param). Themed `bgcolor→scope_bgcolor`,
  `markercolor→grid_color`, `curvecolor→accent`, `hcurvecolor→accent2`.
- **When native vs custom:** `filtergraph~` is THE native EQ/filter editor — it gives you the drag
  UI AND the biquad coeffs for free. Use a `v8ui` drag-curve only for a NON-filter arbitrary curve
  (use `function` for a transfer / velocity curve).

## ✅ Two-accent theming — accent vs accent2 (which control, which state)

VERIFIED end-to-end (Live screenshot, RUPTURE cyan/pink: the selected tab rendered pink while
the dial arcs were cyan). `accent` = the PRIMARY draw (dial arcs, slider fills, value bars,
meters); `accent2` = the SELECTION / active-highlight hue. In a single-accent theme
`accent2 == accent` (set in `Theme.__post_init__`), so these are visually identical and only a
distinct-accent2 palette (RUPTURE, AMBER, NEON, STRANULAR…) shows the second hue. Mechanism:
`Theme.tab_bg_on` / `tab_text_on` derive from `accent2`, and the factories MIRROR
`bgoncolor → activebgoncolor` so the LIVE (active=1) selection themes, not just the bypassed
state (the amber-tab bug).

| Control | primary fill → `accent` | selection / highlight → `accent2` |
|---------|-------------------------|-----------------------------------|
| `live.tab` | unselected seg = `tab_bg` | **selected seg `bgoncolor → tab_bg_on`** ✓ |
| `live.menu` | body = `tab_bg` | **highlighted item `bgoncolor → tab_bg_on`** ✓ (was `accent`) |
| `live.grid` | lit cell `stepcolor → accent` | direction strip `directioncolor → accent2` ✓ |
| `live.step` | step bars `stepcolor → accent` | second-lane `stepcolor2 → accent2` ✓ |
| `live.arrows` | arrows `arrowcolor → accent` | press flash `blinkcolor → accent2` ✓ |
| `filtergraph~` | response curve `curvecolor → accent` | highlighted curve `hcurvecolor → accent2` ✓ |
| `waveform~` | wave `waveformcolor → accent` | selection region `selectioncolor → accent2` ✓ |
| `spectrumdraw` | main trace `color → accent` | comparison trace `color2 → accent2` ✓ |
| `live.dial` / `live.slider` | arc / fill → `accent` | — (no selection state) |
| `live.toggle` / `button` / `live.text` | ON fill `bgoncolor → accent` | — (binary on/off is a PRIMARY fill, not one-of-N) |
| `meter` / `live.gain~` | lit segs → `meter_*` | — |

**Rule:** `accent2` is the SECONDARY hue. Theme a control's secondary cue to it in exactly
two cases: **(a) a ONE-OF-N selection / active cue** (tab/menu/grid-direction/arrows selected
state) or **(b) a SECONDARY DATA SERIES** (a comparison trace, highlighted curve, selection
region, or a second value lane — `color2`/`hcurvecolor`/`selectioncolor`/`stepcolor2`). A
binary on/off or the PRIMARY value fill stays on **accent**. Map only that one cue — never the
whole control — to `accent2`; single-accent themes set `accent2 == accent` so they collapse to one hue.

## ✅ live.arrows  (direction-arrow control — rotate / nudge / step)

DOC-VERIFIED (live.arrows maxref) + 1 corpus instance (SliceShuffler's "rotate cell sequence").
1 inlet / 1 outlet (`[""]`). On click it sends the **symbol** `left` / `up` / `down` / `right`
(NOT a number) — wire those to your own increment / rotate / nudge logic.

- **Which arrows show:** `uparrow` / `downarrow` / `leftarrow` / `rightarrow` [int, default 1].
  A vertical up/down stepper = `leftarrow 0` + `rightarrow 0`; a horizontal pair =
  `uparrow 0` + `downarrow 0`; a full 4-way pad = all 1.
- **Colors (doc-verified, NO `active*` twins):** `arrowcolor` (the arrows), `blinkcolor` (the
  press flash) + `blinktime` [ms, default 150], `bordercolor`, `textcolor`, `color` (object
  color). `textjustification` aligns text. ⚠️ `arrowbgcolor` does NOT exist (a removed
  fabrication). Supports a `jspainterfile` painter; `parameter_enable` opt-in.
- **Kit:** `add_live_arrows(uparrow=, downarrow=, leftarrow=, rightarrow=, arrowcolor=,
  blinkcolor=, blinktime=, …)`; theme injects `arrowcolor→accent`, `blinkcolor→accent2`,
  `textcolor→text`, `bordercolor→panel_border`.
- **When native vs custom:** use live.arrows for a compact rotate / nudge / step trigger
  (sequence rotate, octave up/down, preset prev/next). For a value you set directly use
  `live.numbox` / `live.dial`; for one-of-N use `live.tab`.

## ✅ function  (breakpoint / envelope / transfer-curve editor)

NOT in the synced Max docs — MEASURED from the corpus (20 instances: Chiral & Superberry
transfer curves). The native curve editor. **1 inlet / 4 outlets** `["float","","","bang"]`:
send an x into the inlet → the curve's y at that x comes out outlet 0 (outlet 3 bangs on
finish). In the corpus it is used as an **invisible curve-DATA store** (patching layer, no
presentation, `parameter_enable 0`): you bake a shape and the DSP reads y-values from it.

- **`points` → `addpoints_with_curve`**: the breakpoint list, flat `[x, y, flags, curve, …]`
  per node — `curve` is the per-segment tension (0 = linear, ± curves the segment).
- **`domain`** [float]: the X-axis max / input range (corpus 1.0 or 100.0).
- **`value_range` → `range`** [min, max]: the Y-axis output range (e.g. `[0, 8]`).
- **`mode`** [int] (corpus 1) + **`classic_curve`** [int] (1 = classic interpolation).
- **`parameter_enable`** [int]: opt-in (corpus all 0 — a patch-internal store, not a Live param).
- **Kit:** `add_function(points=, domain=, value_range=, mode=, classic_curve=, presentation=)`.
  Defaults to a VISIBLE editor (`presentation=1`, so it places in a layout); pass
  `presentation=0` for the corpus-style invisible data store. **Live-VERIFIED** (EditorsProbe,
  2026-06): a visible `function` renders its breakpoint curve + handles correctly. Its display
  colors aren't corpus-grounded, so pass them via `**kwargs` if you want them themed.
- **When native vs custom:** `function` is THE native way to define a drawn curve — velocity /
  transfer / response curves, a custom envelope feeding gen~, a wave-shaper. Far cheaper than a
  hand-drawn `v8ui` drag-curve. Use a `v8ui` drag-node only for a multi-param curve `function`
  can't express (e.g. an EQ with frequency AND Q per node).

## ✅ textedit  (editable text / numeric entry field)

NOT in the synced Max docs — MEASURED from the corpus (4 instances, Roulette / SliceShuffler,
small numeric entry fields like a "StepsNum 32" box). 1 inlet / **4 outlets**;
**`outlettype ['', 'int', '', '']`** — the int is on outlet **1** (the prior stub's
int-on-outlet-3 was wrong). On Enter the typed text/number is reported (outlet 0 = symbol/list,
outlet 1 = int when numeric).

- **`text`** [symbol]: the initial / stored string (corpus '0', '127').
- **`keymode`** [int] (1): key-handling mode. **`tabmode`** [int] (0): tab behaviour.
- **`textjustification`** [int] (1 = center). **`border`** / **`rounded`** [float] (corpus 0 —
  flat, borderless). **`bgcolor`** (corpus alpha-0 / transparent — themed at runtime),
  **`textcolor`** (corpus colored, e.g. orange).
- **`parameter_enable=1`** makes textedit a **Blob parameter** (`parameter_type 3`) that SAVES
  its text with the device (Roulette stores its value this way) — pass it only when you also
  wire the saved-attr blob.
- **Kit:** `add_textedit(text=, keymode=, tabmode=, textjustification=, border=, rounded=,
  parameter_enable=)`; theme injects `textcolor → text`, `bgcolor → section`.
- **When native vs custom:** use textedit when the user must TYPE a string / number; for a plain
  automatable numeric parameter prefer `live.numbox` (drag + LCD look).

## ✅ pictctrl  (image-filmstrip control — custom knob / button / slider)

MEASURED from the official M4L corpus (17 instances, 100% consistent; absent from synced docs and
the downloaded corpus). Displays one frame of a sprite image and outputs the frame **index** as an
`int`. 1 inlet / 1 outlet (`["int"]`).

- **`name`**: the sprite file (a filmstrip — e.g. a 68-frame vertical strip). **`frames`**: the
  frame count. The control shows frame = value (0..frames-1).
- **`mode`**: interaction (button / toggle / slider-drag). **`trackvertical`** 1 = frames stack
  VERTICALLY (drag up/down to change). **`clickedimage`** / **`inactiveimage`**: use the clicked /
  inactive sub-images in the sprite. `active` / `parameter_enable` opt-in (corpus all 0).
- Requires bundling the sprite `name` as an asset (embed it like `fpic`). No themeable colors —
  the look IS the art, so it is not themed.
- **When native vs custom — IMPORTANT:** pictctrl is the OLD way to get a custom-looking control
  (ship a pre-rendered filmstrip). **Prefer a `jspainterfile` painter on a native control** (the
  premium-control method at the top of this doc) — it is themeable, automatable, and needs no art.
  Reach for `pictctrl` ONLY when you already have a ready-made sprite filmstrip to drop in unchanged.

## ✅ fpic  (picture display — logo / backdrop / SVG state graphic)

NOT in the synced Max docs — MEASURED from the corpus (35 instances; the most-used widget
that was still un-mastered). Core Max picture object: **1 inlet / 1 outlet** (`jit_matrix`),
`pic` = the image file. The corpus is almost entirely **`.svg`** (vector — crisp at any device
scale) and reveals the premium patterns the prior stub omitted:

- **`embed`** [int] (17/35): bundle the image DATA inside the patcher → a self-contained device
  with no external file to ship. Pair with the kit's asset/freeze bundling so the `pic` is
  actually present at build.
- **`forceaspect`** [int] (33/35): preserve aspect ratio; with `autofit 1` (34/35) the image
  scales to the box without distorting.
- **`hidden`** [int] (23/35): THE state-graphic trick — stack N fpics (`algo1.svg`…`algo8.svg`
  + `*Off.svg`), all `hidden 1`, and let the patch reveal the one matching the current state
  (AS Console's switchable algorithm diagrams; also on/off button glyphs). `background 1` (1/35)
  drops it to the bg layer.
- No color attrs — fpic is **not themed**.
- **Kit:** `add_fpic(pic=, autofit=, forceaspect=, embed=, hidden=, background=)`. **Use for** a
  logo, a textured/material backdrop, or switchable diagram/glyph graphics; for a drawn
  gradient/panel use `panel` / a `v8ui` painter (those CAN be themed); for a clickable image
  region wrap it with `ubutton`.

## Backlog (the loop fills these in)

> **Integration source:** the `harden-all-widgets` blitz produced proposed fixes + doc
> sections for all 26 remaining widgets, saved at `docs/_widget_hardening_specs.json`.
> **VERIFY, don't trust** — agents hallucinate: e.g. the blitz claimed `add_menu` drops
> `shortname` (FALSE — the code already passes it) but correctly flagged `live.arrows`'
> `arrowbgcolor` as a non-existent attribute. So each loop tick: pick ONE widget from the
> specs, **confirm every claim against the cached Max doc** (`~/.cache/livemcp/docs/raw`)
> AND the real factory code, apply only the verified parts, gate-check, **Live-verify in a
> gallery device** (build → load → screenshot → `get_device_parameters`), then mark ✅.
> Already done & verified: `live_arrows` (removed dead `arrowbgcolor`, added real color attrs).

- ✅ **umenu** — DONE (see "umenu" section). NON-parameter (outputs int index); corpus uses it
  almost only as a styled READ-ONLY gradient readout (`display=True`: ignoreclick/arrow/allowdrag),
  driven by `set`. Hardened: `umenu(display=, arrow=, ignoreclick=, bgcolor=, textcolor=, …)` +
  theme_mapping `bgcolor→tab_bg, textcolor→tab_text`. Interactive enum → `live.menu`.
- ✅ **ubutton** — DONE (see button-family section). Grounded from the OFFICIAL M4L corpus
  (M4L Building Tools / Essentials packs, 43 instances) since it is absent from the synced docs
  AND the downloaded corpus: fixed outlettype to `["bang","bang","","int"]` (outlet 1 = down-bang),
  added `hltcolor` (click flash) + `handoff`, theme `hltcolor → accent`.
- ✅ **multislider** — DONE (see "multislider" section). Strip of N bars; corpus uses it mostly
  as a non-interactive multi-bar meter/GR DISPLAY (`display=True`: ghostbar+ignoreclick, dB
  setminmax, signed for bipolar). Hardened + theme_mapping `slidercolor→accent, bgcolor→bg`.
- ✅ **live.grid / live.step** — DONE (see "live.step / live.grid" section). Blob-param
  multi-value sequencers (corpus-measured; absent from synced docs). Removed the
  hallucinated `nstep`/`nseq`/`loop_start`/`loop_end` stub attrs; FIXED `live.grid` I/O to
  the real **2 inlets / 6 outlets** (was 1/4); added measured color kwargs + theme_mapping
  (`stepcolor→accent`, grid `directioncolor→accent2`).
- ✅ **function** — DONE (see "function" section). The native breakpoint/envelope/transfer-curve
  editor — was a complete GAP (20 corpus instances, no factory). Built `add_function(points=,
  domain=, value_range=, mode=, classic_curve=, presentation=)`: 1 inlet / **4 outlets**
  (`['float','','','bang']`), corpus curve attrs grounded; defaults to a visible editor,
  `presentation=0` for the invisible data store. Registered in registry + layout proxy.
  **Live-VERIFIED** (EditorsProbe, 2026-06) alongside `filtergraph~` + `live.adsrui` — all three
  graph editors render correctly (curve / response / envelope + handles), no load error.
- ✅ **live.gain~ / meter** — DONE (see "live.gain~ / live.meter~" section below).
- ✅ **matrixctrl** — DONE (see "matrixctrl" section). rows×columns toggle grid; corpus norm
  2×4, `autosize=1`, mostly `ignoreclick=1` displays; the interactive one is a Blob param
  (`parameter_type=3`, whole grid saved). Hardened: `matrixctrl(autosize=1, ignoreclick=,
  color=, elementcolor=, bgcolor=)` + theme_mapping `color→accent, elementcolor→section, bgcolor→bg`.
- ⊘ **kslider / nslider** — keyboard / notation inputs: **0 corpus instances** and absent from
  the synced docs → can't ground without guessing; skip (revisit only if a device needs them).
- ✅ **panels + comment text layout** — DONE. `panel()` sets `background:1` → it renders
  BEHIND controls automatically (z-order safe); still add panels before controls.
  `live.comment` (the label) WRAPS text to multiple lines inside its rect (≈ one line
  per `fontsize+3` of height) and only CLIPS when the text needs more lines than the
  height permits — so size BOTH axes: width ≥ ~0.5·fontsize·chars *for a single line*,
  OR a narrower width + height ≥ `(fontsize+3)·lines` to wrap deliberately. For a
  DELIBERATE multi-line info/credit block, set `comment(..., linecount=N)` explicitly
  (corpus uses 3 and 5) rather than relying on height alone; `comment(..., fontface=N)`
  picks the weight (0 regular / 1 bold / 2 italic / 3 bold-italic) — both are now
  first-class kit params (were kwargs-only). Verified:
  `drift "foot"` (92×28, 58 chars, fs 6) reads fine because 28px fits the ~2 wrapped
  lines — it is NOT clipped. `justification` 0=left/1=center/2=right. The "panel overlapping
  text" was NOT `add_panel` — it was a **dial `appearance=2` (Panel)** drawing its own
  `panelcolor` box and pushing the value text into the neighbor below; use Panel only for
  intentionally-grouped knobs with extra height, never a plain dry/wet. Fix this run:
  `tab()` now mirrors bg/on/text colors to their `active*` twins (selected tab themes
  right by default).
- ✅ **two-accent theming of native controls** — DONE. MEASURED: corpus tabs carry full
  `bgcolor`/`bgoncolor` + `activebgcolor`/`activebgoncolor` (17 each) but the SAVED values are
  alpha-0 placeholders — the runtime `live.colors` skin bus drives selection at load (so the
  corpus selection color = Live's skin slot, not a baked second accent). For our BUILD-TIME
  Theme the premium convention is **accent = primary draw (dials, bars, value arcs); accent2 =
  the SELECTED/active state** (Rupture pink-on-cyan). Implemented by deriving `Theme.tab_bg_on`
  (the selected-tab bgoncolor) from **accent2** instead of accent. Backward-compatible: single-
  accent themes set `accent2 == accent` in `__post_init__`, so they're visually unchanged; a
  distinct-accent2 theme (RUPTURE, AMBER, STRANULAR, NEON, …) now renders the selected tab in
  the second hue. The factory mirrors `bgoncolor` → `activebgoncolor`, so the active twin tracks
  it. Rule: map only SELECTION states to accent2 (selected tab, active highlight); keep the
  primary fill on accent.
- ✅ **sizing tables** — DONE (see "Sizing tables" section below).

---

## Sizing tables (px) — verified compact defaults for a 168-tall device

Premium = compact + dense (Rupture). These are the verified working sizes from Drift /
uikit_compare / uikit_lab. Width is the CELL (control + its label/value).

**Knobs (`live.dial`, label above via comment + value below `shownumber 1`):**

| Density        | rect W×H | native_sizes const | notes |
|----------------|----------|--------------------|-------|
| **workhorse**  | **41×35** | `DIAL_COMPACT` | **38 of 82 corpus dials — the premium default** |
| tall rail      | 41×48    | `DIAL_RAIL`    | taller labelled rail dial (corpus: 7) |
| tiny           | 54×36    | `DIAL_TINY`    | wide-short, appearance=1 (5) |
| LCD-stacked    | 51×63    | `DIAL_LCD`     | tall LCD readout, appearance=3 (5) |

> **MEASURED across the 15-device commercial corpus** (own count of `presentation_rect`).
> The old `DIAL=(44,47)` was a guess and is NOT how premium devices size knobs (it's not
> even in the corpus top-6 — confirms "too tall/chunky"). Prefer **`DIAL_COMPACT=(41,35)`**.
> Other verified tiers: `NUMBOX=(44,15)` (primary, 53×) + `NUMBOX_MINI=(17,15)`,
> `VSLIDER_NATIVE=(22,113)` (wider than the old 18,110), `TAB_BAR_H=20` (full-width mode
> bar — taller than 16), `TEXT_ICON=(15,15)` (square glyph/icon live.text), `LED_DOT=(10,10)`.
> Use `knob_row_fit(x0, y, n, width)` to spread a knob aisle to a panel width (DIAL_COMPACT).

> ⚠️ **DENSE VERTICAL KNOB COLUMN (Rainbow look) — the 4-high rule.** A knob column fits
> **4 knobs ONLY without a persistent value** in a 168px device: each cell is
> `label(8) + knob(~21) + value(~10) ≈ 40px`, so 4 = 160px and the `live.dial` value text
> OVERFLOWS the short cell into the label below it (the Pressure collision). FIX: set
> `shownumber=0` + `valuepopup=1` (+ `valuepopuplabel=3`) on each dial → value-on-hover, each
> cell is just label+knob, 4 fit clean. With an always-on `shownumber` value a column caps at
> **~3** (taller cells). Use `ns.knob_column(x, y0, n)` → `(label_rect, dial_rect)` cells sized
> for this; it bakes the pitch + non-overlap. This repacked Pressure (688→550px, 2 loose rows +
> a scattered rail → 3 vertical knob columns of 4 + a clean toggle column).
>
> **THE DENSE CONTROL-CARD pattern** (the fix for a wide, loose device — Pressure/Snap):
> displays on the LEFT, then a single SURFACE card holding **2–3 `ns.knob_column` knob columns**
> (logically grouped, e.g. Gain / Time / Out) **+ one `ns.toggle_column`** (mode/auto/look/bypass
> as labelled `live.text`), each column 4-high with `valuepopup` dials. Column pitch ≈ 44–46px;
> a card of 3 knob cols + 1 toggle col ≈ 190px wide. This replaces the anti-pattern of 2 loose
> dial rows + a scattered right rail, and shrinks the device ~20–25%. Reuse it to tighten the
> other still-wide new-batch devices (heat 744, echotide 718, snap 706) once the value-display
> choice (hover vs always-on) is confirmed.

**Other controls:**

| Control                | W × H        | rule |
|------------------------|--------------|------|
| h-slider (`live.slider`) | 80–120 × ≥24 | needs label-top + track; <24 tall clips |
| v-slider               | 20–26 × 60–120 | travel = height; keep ≤ ~120 (don't be "too tall") |
| toggle (native/LED)    | 16–18 sq (+label) | dot/box + label to the right |
| tab (segment)          | (≈40/seg) × 15–18 | ≤4 segments; else use a menu |
| numbox                 | 48–64 × 15–18 | compact native number |
| stepper (custom)       | ≥48 × 16 | needs two buttons + a readable value |
| readout (custom)       | ≥70 × 13–16 | single-row label+value |
| section caption (comment) | fit-text × 9–10 | fontsize 6–6.5 |
| device title (comment) | — × 12 | fontsize 8–9 |

**Frame margins:** keep control cells ≥4–6 px inside the panel border (a control's bg
fill or a `panel`'s frame line gets cut/overlapped otherwise). Device height ceiling is
**168** (taller clips in Live's device view — Live shows only ~169px regardless of the
authored height).

> **Fleet height audit (2026-06)** — grepped every device's `AudioEffect(height=…)`. All ≤168
> EXCEPT **Linear Phase Crossover = 214** → its bottom ~45px was CLIPPED + unreachable (the
> LOW/MID/HIGH trim value labels, the monitor tab's bottom, the whole monitor hint). **FIXED +
> Live-verified** (condensed to 168: display 94→72px, control band moved up y132→108 + compacted
> 74→56px — all dial values + the LISTEN tab + hint now render). **Rule for the build: never author height > 168**;
> if the content doesn't fit, condense (smaller cells, drop hints) — don't just raise the height,
> Live won't show it. Audit new devices with `grep AudioEffect.*height plugins/*/build.py`.

> **NOW ENFORCED IN THE KIT (2026-06).** The 168 ceiling is no longer a manual grep — it is a
> build lint. `Device.lint()` emits a **`device-height-over-ceiling`** issue (severity
> **warning**, NOT a wiring error) when a CHAIN device (`audio_effect` / `instrument` /
> `midi_effect`) authors `height > DEVICE_H (168)`. Because it is warning-severity and not a
> wiring code, it is **silent on a default `validate=None` build** (only wiring errors raise
> there) and **surfaces under `device.to_bytes(validate="warn")` / `build(validate="warn")`** —
> so it nags when you lint but never blocks a normal build. **MIDI Tools** (`note_transformation`
> / `note_generator`) render in a different UI and are **exempt** (not grounded to the 168 row).
>
> **The clone-parity EXCEPTION — `allow_tall=True`.** "Never author height > 168" governs
> ORIGINAL designs. A faithful **1:1 reproduction** of a taller commercial original legitimately
> exceeds it to match the source's verbatim rects — **SEAR=190** mirrors its original (and
> inherits the original's own bottom-clip). Such a clone passes
> `AudioEffect(..., allow_tall=True)` to opt out of the lint, rather than condensing (which would
> break the structural A/B match). Re-audit 2026-06: fleet clean — every chain device ≤168 EXCEPT
> SEAR=190 (intentional `allow_tall` clone). Rule of thumb: condense your own devices to ≤168;
> reach for `allow_tall` ONLY when reproducing a taller source 1:1.

> **PER-CONTROL clip lint — `control-clipped` (2026-06).** The 168 ceiling is necessary but not
> sufficient: a device can be ≤168 yet still place a dial at `y=150,h=30` (bottom **180**) so it
> is half-cut. `Device.lint()` now also flags a **FUNCTIONAL control whose `presentation_rect`
> straddles a device edge** (partly inside, partly past `width`/`height`) — same warning
> severity, same silent-on-default / surfaces-under-`validate="warn"` behavior. Two layout idioms
> are deliberately EXCLUDED (empirically false-positive-free across the whole 33-device fleet):
> (1) **fully off-canvas controls are PARKED, not clipped** — the corpus hides a still-functional
> `live.dial`/`live.menu` (an automatable probe/param) by parking it far out at ~`(900, 900)`;
> a box entirely outside `0..width × 0..height` is intentional and skipped. (2) **a background
> `panel` routinely full-bleeds past the bottom/right edge by design** (so no gap shows at the
> frame) — decoration maxclasses (`panel`/comment/divider/image, the `_DECORATION_MAXCLASSES`
> set) are skipped; a clipped label/rule is cosmetic, not an unreachable control. Net: the lint
> fires only on the real "I can see half my knob" bug. Fleet re-audit: **0** clipped functional
> controls (the only raw over-edge hits were full-bleed `bg` panels in parametric_eq /
> linear_phase_eq and a 2px proof-device comment — all correctly excluded).

---

## Coverage matrix — the "EVERYTHING" checklist (35 builder widgets)

Goal: every M4L control/UI object is a first-class builder helper with CORRECT defaults
(fill/needlemode, active* colors), theming, sizing, and when-to-use docs. ✅ mastered ·
🔬 partial · ⊘ not M4L vocabulary (real Max object, 0 corpus everywhere — steer-away docstring) ·
TODO not yet hardened.

> **STATUS (2026-06): the per-widget pass is COMPLETE — no `TODO` widgets remain.** Every builder
> control is ✅ mastered, or ⊘/🔬 with a verified steer-away (`radiogroup`, `nodes`, `kslider`/
> `nslider`, `plot~`, `spectrumdraw~` — all real Max objects that are NOT M4L vocabulary / not stock
> / ungrounded). Future loop runs should now advance the **cross-cutting UI CONCERNS**, not hunt for
> widgets: control SIZING small-vs-large + WHEN each, native-vs-custom decision rules, two-accent
> theming depth, panel+comment text-overlay/clipping, z-order/compositing pitfalls, and APPLYING
> these correctly across the device fleet (audit each device against the rules).

**Parameter controls (automatable):**
- ✅ `dial` (knob) · ✅ `tab` · ✅ `toggle` · ✅ `slider` (live.slider) · ✅ `number_box` · ✅ `live_text`
  · ⊘ `rslider` (plain-Max range slider — UNGROUNDED: no synced maxref, **0** corpus, **0**
  Factory-Pack, **0** kit usage; not a Live parameter, `min`/`max` unverified. Use `slider` or a
  custom v8ui range bar. Steer-away docstring added)
- ✅ `menu` · ✅ `umenu` (non-param readout) · ✅ `button` · ✅ `textbutton` · ✅ `ubutton`
  · ✅ `pictctrl` (image filmstrip) · ⊘ `radiogroup` (plain-Max, unthemed, **0** Factory-Pack
  corpus — use `tab`/`menu`; helper kept with a steer-away docstring for non-Live patches)

**Multi-value / sequencer / envelope:**
- ✅ `multislider` · ✅ `live_grid` · ✅ `live_step` · ✅ `matrixctrl` · ✅ `function` (curve
  editor) · ✅ `adsrui` (live.adsrui envelope) · ⊘ `nodes` (ungrounded, **0** corpus everywhere —
  use `function`/`filtergraph~`/v8ui XY pad) · ⊘ `kslider`/`nslider` (0 corpus, not in
  docs) · ✅ `live_arrows`

**Displays / meters / graphs:**
- ✅ `meter` · ✅ `live_gain` (fader+meter) · ✅ `scope` (live.scope~) · ✅ `waveform~` (buffer)
  · ⚠️ `spectrumdraw~` (external not stock — use `spectroscope~`/`fft_analyzer`)
  · 🔬 `plot~` (ungrounded: absent from synced docs + **0** corpus → attrs unverified; prefer
  `scope~`/`function`/`filtergraph~`/v8ui) · ✅ `filtergraph~` · ✅ `swatch` (color)

**Structure / decoration / IO:**
- ✅ `comment` · ✅ `panel` · ✅ `live_line` (divider) · ✅ `fpic` (image) · ✅ `bpatcher`
  · ✅ `textedit` · ✅ `live_drop` (file drop)

> **bpatcher module** (F3): `device.add_bpatcher_module(subpatcher, id, rect, name=…,
> numinlets=, numoutlets=, outlettype=)` embeds a `Subpatcher` as a VISIBLE bpatcher whose
> presentation view renders inside the device (`embed:1`, `presentation:1`,
> `viewvisibility:1`) — the premium self-contained DSP+UI module pattern (AS Console).
> Use `Subpatcher.to_presentation_patcher_dict()` (sets the inner `openinpresentation:1`).
> Contrast `add_subpatcher` = an invisible `p name` box. `bpatcher()` (external `.maxpat`
> ref) is for non-embedded reuse.

> **`live.line`** (divider/separator): a non-parameter decoration. Its ONLY style attr is
> `linecolor` (verified across the corpus: 40 uses, no thickness/orientation attrs —
> orientation is implicit from the rect aspect: wide rect → horizontal rule, tall → vertical;
> 1 inlet, 0 outlets). Not in the synced Max docs, so grounded in real-device usage (AS
> Console modules use 5 each as section rules ~174×6). Registry now themes
> `linecolor → panel_border` (subtle); was Live-default. Use it for section separators
> inside a panel — cheaper/cleaner than drawing a v8ui line.

> **DECORATION vs FUNCTIONAL — the `orphan-box` lint rule (2026-06).** The pure-decoration UI
> objects — **`panel`** (background), **`live.comment`** (label), **`live.line`** (divider),
> **`fpic`** (image) — carry no signal/data and are **NEVER patched**: they sit unconnected *by
> design*. (Measured: `panel` and `live.comment` report **1 nominal inlet + 0 outlets**, so a
> "skip if 0-in-AND-0-out" test would MISS them — the skip must be by maxclass.) The build's
> `orphan-box` lint now SKIPS these maxclasses (`_DECORATION_MAXCLASSES` in `validation.py`):
> flagging a box that can *never* be connected is noise that buries a genuinely unwired
> FUNCTIONAL box (a `newobj`/`message` you forgot to patch). So a surviving `orphan-box` warning
> is now a real signal — SEAR went from **5** decoration false-positives to **0**. When adding a
> new pure-decoration maxclass, extend that set. (Functional UI controls — `live.dial`/`tab`/
> `numbox`/meters/jsui heroes — keep real I/O and stay in the check; an unwired one is a real bug.)

**Cross-cutting (apply to all):**
- ✅ native vs custom decision rule · ✅ active* color rule · ✅ two-accent theming via theme inject
  (Live-verified; see "Two-accent theming" table) · ✅ per-density sizing tables (193-device census +
  the two-regime rule) · ✅ unitstyle correctness per param type
- ✅ **ATTR-GROUNDING AUDIT (2026-06)** — programmatically diffed every kit control's *emitted* box
  attrs against its synced maxref (minus a common-box allowlist). **11/11** maxref-backed controls
  (`live.dial`/`tab`/`slider`/`numbox`/`toggle`/`text`/`button`/`gain~`/`drop`/`arrows`/`line`) emit
  **ZERO** hallucinated/silently-ignored attrs — the "never guess attributes" discipline holds across
  the doc-grounded surface. The only non-grounded factory is `rslider` (plain-Max, reclassified ⊘).
- ✅ **DEFAULT-VALUE AUDIT (2026-06)** — the complement: diffed each control's kit-emitted *default*
  int/float values against the maxref *defaults* (the class of bug `live.text mode` was). Result:
  the ONLY buggy mismatch was `live.text mode` (kit 0 vs maxref 1 — FIXED). The other deltas are all
  intentional and correct: `presentation=1` (REQUIRED for the M4L device view; maxref default 0 is
  the patcher case), dial `needlemode=1` (the kit drives fill-origin explicitly to stay in lockstep
  with its bipolar arc-colour flip — renders identically to Automatic for a unipolar range), and
  numbox `appearance=4` (the deliberate LCD premium default). So kit control defaults are clean.
- ✅ **`live.text mode=1` fix DEPLOYED fleet-wide (2026-06)** — rebuilt all **15** devices that use
  `add_live_text` (UI-only change, gen~/DSP untouched → no stale-cache risk); confirmed via `.amxd`
  parse that every toggle now carries `mode=1` (e.g. Ceiling's `bypass_toggle`/`tp_toggle`/… all 1).
  The rebuilds also carry the verified numbox-LCD + meter-rail fixes. Each change TYPE was
  individually Live-verified in prior ticks (UIKit Gallery numbox, Strip meter, Mono Maker toggle).

---

## Native vs custom — decision table (when each)

Default to NATIVE. Reach for a CUSTOM v8ui control only when the right column applies.

| Need                     | Native (default)            | Custom v8ui (only if…) |
|--------------------------|-----------------------------|------------------------|
| knob (any scalar param)  | `live.dial` (+needlemode)   | bespoke arc/glow/glyph identity, or a knob that drives a hero |
| on/off — LABELED (Bypass, HP On, M/S) | **`live.text`** (off/on labels; the PREMIUM corpus norm — AS_Console_EQ's utility strip, J74's toggles; `mode=1` to latch) | bespoke glyph/LED toggle |
| on/off — bare inline     | `live.toggle` (tiny ~12×13 checkbox, no label) | an LED-dot/inline micro-toggle look |
| pick 1 of N (≤4)         | `live.tab`                  | mode GLYPHS (∿ ⊓ ∧), or a 1-cell cycle/stepper to save space |
| pick 1 of N (>4)         | `live.menu`/`umenu`         | rarely |
| fader / level            | `live.slider` / `live.gain~`| custom track/handle styling only |
| numeric entry            | `live.numbox`               | drag-value readout or −/+ stepper UX |
| 2 params at once (X/Y)   | — (none native)             | **always custom** `add_xy_pad` |
| draggable curve/EQ node  | `filtergraph~` (filters)    | **custom** `add_drag_curve_node` for arbitrary 2-param graphs |
| envelope editor          | `live.adsr~`/`adsrui`        | custom only for non-ADSR/multi-breakpoint |
| spectrum / scope / meter | `spectroscope~`/`scope~`/`meter` (compiled) | v8ui overlay for grid/labels/curve on top |
| animated hero (LFO, reel)| — (none native)             | **always custom** v8ui (phasor→snapshot→draw) |
| background / panel       | `panel` (flat) + comment    | `glass_panel_bg` / `panel_bg_js` for gradient/material/noise |

Rule of thumb: **native for the controls, custom for the centerpiece.** A premium device
is mostly native controls sized compact + ONE custom hero, in a two-accent palette.

## Surface layout engine — API reference (UI Foundations v2)

`m4l_builder.surface.Surface` owns ALL faceplate rect math. Immediate-mode with a
finalize pass; slots flow left→right in the 156px band (BAND_Y=6) of a 168px device.

```python
Surface(device, *, accent=<ACCENTS key | RGBA>, accent2=None, theme=GRAPHITE,
        height=168, margin=8, gap=6, follow_live=True)
  .hero(id, *, width, recess=True) -> HeroSlot     # recessed screen (scope_bgcolor,
                                                   # 1px panel_border, rounded 4);
                                                   # .rect = 2px-inset content rect
  .section(id, title=None, *, cols, rows<=3,       # untitled card by default (user
           material="card"|"rail",                 # sign-off: headers are opt-in);
           col_pitch=COL_PITCH, pad=8) -> Section  # >3 rows RAISES (P2 fit rule)
  .probe(id, param_name, **dial_kw) -> id          # hidden param at PARK_RECT
  .finalize() -> width                             # derives device.width, patches the
                                                   # bg panel, emits the brand-dim bus
Section.dial(param, label=None, *, min_val, max_val, initial, unitstyle,
             at=(col,row)|None, accent2=False, **dial_kw) -> StageResult
Section.toggle(param, label=None, *, on, off, initial=0, shortname=None, **kw) -> id
Section.menu(param, options, label=None, **kw) -> id
Section.numbox_lcd(param, label=None, *, ...) -> id
Section.slot_rect(at=None) -> [x, y, CELL_W, VALUE_CELL_H]   # claim a cell for
Section.blank()                                              # bespoke content
```

Cell math (tokens in `native_sizes`): `VALUE_CELL_H = CAPTION_H(10) + gap(1) +
DIAL_COMPACT[1](35) = 46`; **`MAX_VALUE_ROWS = 3`** — a 4th persistent-value row
provably overflows the band (the old `knob_column` n=4 layout only ever fit by
hiding the value, which Surface forbids). Cells fill **column-major**; captions are
7.5pt "Ableton Sans Medium" `text_dim`; section id prefixes the generated box ids
(`{sect}_{param_slug}_dial` / `_btn` / `_menu` / `_cap`).

Theme bus: `finalize()` emits one `live_brand_dim` bus per accent (`---surfacc`,
`---surfacc2`) fanned from a single receiver to every dial the engine placed.
Bespoke-layout devices call `device.add_brand_dim(rgba, [ids], bus=...)` directly
(one call per accent color). Live-proven facts baked into `live_brand_dim`:
`live.thisdevice`'s middle outlet reports enable state at LOAD ONLY; LOM
`Device.is_active` is get-only; **`DeviceParameter.value` on `this_device
parameters 0` is the reliable observe source** (fires on attach + every toggle);
`t i i` coerces the observer's float for `sel`.

Hero z-order caveat: a COMPILED display (`spectroscope~`/`scope~`) renders ABOVE
any v8ui regardless of box order — keep compiled fills semi-transparent or draw
the spectrum inside the v8ui.

Layout lint (`validation.layout_issues`, in every `Device.lint()`):
`control-overlap` / `dead-zone` (>=40px empty band) / `width-mismatch` (warnings) +
`setwidth-mismatch` (ERROR — a width-collapse FULL wider than the layout).
