# Advanced Max for Live UI & interaction techniques

Research notes for pushing the flagship devices past "works" into "feels like a
commercial plugin." Sourced from the Cycling '74 Max JS API docs, Ableton's
official *Max for Live Production Guidelines*, and live verification in Ableton
12.4 on this machine. Each entry tags whether we **USE**, **DON'T USE**, or have
a **VERIFIED** runtime fact about it.

> Companion: `~/.claude/projects/-Users-squidbot/memory/m4l-live-runtime-pitfalls.md`
> (read-only here) holds the older hard-won runtime gotchas. This doc adds the
> v8ui interaction surface and the parameter-visibility findings.

---

## 1. The v8ui / jsui interaction API (jsthis)

Source: <https://docs.cycling74.com/apiref/js/jsthis/>. These are methods/handlers
you define on the global `this` inside a `v8ui` (or legacy `jsui`) script. The
**pointer** events (`onpointer*`) are v8-only and carry a `PointerEvent`; the
**legacy** events (`onclick`/`ondrag`/`onidle`/`onwheel`) pass plain numeric
`x, y, button, mod1, shift, caps, opt, mod2` — i.e. **clean object-space
coordinates as direct arguments**, no `pointerevent.x` resolver needed.

| Handler | What it gives you | Our usage |
|---|---|---|
| `paint()` | custom draw via MGraphics | **USE** (every hero) |
| `onclick(x,y,button,mod1,shift,caps,opt,mod2,pe?)` | initial click, clean x/y | **USE** (via onpointerdown mostly) |
| `ondblclick(...)` | double-click, clean x/y | **USE** (reset/add gestures) |
| `ondrag(x,y,button,...)` | drag, clean x/y, button=0 on release | partial — we use onpointermove + a resolver |
| `onidle(x,y,button,...)` | **mouse-over / hover, clean x/y, button=0** | **DON'T USE** — opportunity (see §2) |
| `onidleout(x,y,...)` | **mouse leaves object bounds** | **DON'T USE** — opportunity (hover cleanup) |
| `onwheel(x,y,scrollx,scrolly,...)` | wheel with object x/y | partial (Q-on-node); synth wheel is inert in Live (pitfall) |
| `onkeydown(keycode,char,updown,mods...)` → return 1 to consume | **keyboard, v8-only** | **DON'T USE** — opportunity (see §3) |
| `onfocus()` / `onblur()` | gained/lost keyboard focus | **DON'T USE** — needed for §3 |
| `onpointerenter/leave(pe)` | pointer enter/leave (v8-only) | **DON'T USE** |
| `hittest(x,y)` → return 0 to make transparent | filter/clip mouse regions | **DON'T USE** — opportunity (click-through dead zones) |
| `setcursor(n)` | **set the mouse cursor over the object** | **DON'T USE** — opportunity (see §4) |
| `setgrow(n)` | grow/resize behaviour | n/a |
| `this.patcher.newobject(...)` | **create Max objects from JS at runtime** | **DON'T USE** — heavy; for dynamic UI |
| `declareattribute(name, {...})` / `save()`+`embedmessage()` | embed non-param JS state in the patcher | **DON'T USE** — we use hidden live.* hosts |
| PointerEvent `.pressure`, `.tilt`, `.rotation` | pen/tablet input | **DON'T USE** — niche |

Key correction to our pitfalls note: the `pointerevent.x === undefined` trap that
forced the `pointer_x/pointer_y` resolver is **only** on the `onpointer*` events.
The **legacy** `onclick/ondrag/onidle/onwheel` handlers receive `x, y` as real
numbers in object space — so for hover/click logic they are simpler and safer.

---

## 2. Robust hover via `onidle` / `onidleout` (opportunity)

Our hover crosshairs (both EQs, Spectrum) ride `onpointermove` + the coordinate
resolver, and they have no clean "mouse left the plot" signal (the crosshair can
linger at its last spot). `onidle(x,y,...)` delivers passive hover with clean
object-space coordinates, and `onidleout(...)` fires when the cursor exits — the
exact pair for: draw a live hover crosshair in `onidle`, clear it in `onidleout`.
Not yet live-verified in the M4L v8ui runtime (many handlers behave differently
in Live than in Max standalone / the Node harness) — verify before adopting.

---

## 3. Keyboard control on a focused hero (opportunity, v8-only)

`onkeydown(keycode, textchar, updown, mod1, shift, caps, opt, mod2)` returns
nonzero to consume the key. With `onfocus`/`onblur` to track focus, a hero could
support FabFilter-style keyboard editing: arrow keys nudge the selected EQ
node's gain/freq, Delete removes a band, number keys set band type, Esc
deselects. This is a genuinely new interaction modality (no hero uses the
keyboard today). Caveats: needs the v8 engine; synthetic key events are hard to
drive in our harness, so verification is manual; mind that consuming keys can
steal Live shortcuts while focused.

---

## 4. `setcursor(n)` — pointer cursors over draggable elements (opportunity)

`this.box.setcursor(n)` sets the OS cursor while the mouse is over the v8ui.
Commercial EQs change the cursor to a move/resize glyph over a node and a
crosshair over the curve — a cheap, high-perceived-quality polish that applies
to **every** interactive hero. The numeric cursor enum is **not** cleanly
published by Cycling '74; determine it empirically in Live (it's small, ~0..15)
and pin the values once confirmed. Verify visually with `screencapture -C`
(the `-C` flag composites the cursor into the capture; our window-id capture
helpers do **not** include it). Call from `onidle`/`onpointermove` after a
hit-test: cursor = move-glyph over a node, crosshair over the plot, default
elsewhere.

---

## 5. Floating pop-out editor (SHIPPED — the pattern that started this)

A resizable floating window holding a full-size mirror of the hero, escaping
Live's ~169px device strip. Mechanism: `device.add_flyout(subpatcher, ...)` →
an `EXPAND` live.text → `[s/r]` → `[thispatcher] front` opens a real floating
window (`window flags float grow`); the subpatcher is fed the same inlet-0 data
via instance-scoped `---` sends, and its gesture outlets relay back through the
same routers (no-echo). VERIFIED on the Parametric EQ pop-out (it112): node
drag, double-click-reset, and double-click-add on the 1000px window all drive
the real params. Gotchas: the window only opens while **Live is frontmost**;
Ableton's guidelines say always enable **floating** mode (we do) so opening it
doesn't kick Live out of full-screen. Capture it with `tools/cap_win.py`
(targets the Live-owned window named `[<subpatch>_bigview]`).

---

## 6. Ableton's M4L production guidelines — compliance checklist

Distilled from the official *Max for Live Production Guidelines*. ✅ = we follow,
⚠️ = audit / opportunity.

- ✅ Versioned filenames for changed JS/`.gendsp` (session cache pitfall).
- ✅ `live.text` "Mouse Up" output (mode=1 toggles).
- ✅ Defined latency for PDC; fresh-insert defaults in `parameter_initial`.
- ✅ Theme-following colours; ≤168px device height.
- ⚠️ **Pixel-perfect sizing**: keep widget rects on whole pixels (blur on
  non-retina). Worth a sweep of the `presentation_rect`s.
- ⚠️ **Console cleanliness**: a shippable device should post nothing to the Max
  window. Our probe `js` / metros should stay quiet.
- ⚠️ **Hidden/diagnostic params** (see §7): metro-fed "Automated and Stored"
  params flood Live's undo history — the guidelines call this out explicitly.
- ⚠️ **Freeze before distribution** (consolidates `.gendsp`/`.js`/buffers).
- ⚠️ **Balanced margins**: leftmost element as far from the left edge as the
  rightmost is from the right.
- ⚠️ **Don't change a `live.*` parameter Long Name** in an update — Live keys
  recall by Long Name; renaming breaks existing sets.

---

## 7. Parameter visibility (`parameter_invisible`) — NEW framework capability + VERIFIED finding

Max's "Parameter Visibility" inspector setting maps to the `parameter_invisible`
key inside `saved_attribute_attributes.valueof`:

| value | mode | stored? | automatable? | **in Live API `device.parameters`?** |
|------:|------|:---:|:---:|:---:|
| 0 (default) | Automated and Stored | yes | yes | **YES** |
| 1 | Stored Only | yes | no | **NO** |
| 2 | Hidden | no | no | **NO** |

**VERIFIED LIVE (it113):** setting EqSpecProbe to `parameter_invisible` = 1 **or**
2 made it **disappear from `get_device_parameters`** (param count 83→82). Only the
default (0) is enumerated by the Live Object Model. Consequences:

- The **headless DSP-probe pattern** (expose an internal value as a hidden
  `live.dial`, read it via `get_device_parameters`) **requires** the probe stay at
  visibility 0. You cannot hide a probe from automation/undo *and* read it via the
  API — it's one or the other. Probe dials therefore stay visible (they're a
  dev/QA affordance); for a shipping build, gate them off or set them Hidden
  (accepting they're no longer API-readable).
- For genuine **internal state hosts** that are restored via patcher echo (not via
  the Live API) but must persist across save/duplicate — e.g. the LP EQ's packed
  band-state dials — **Stored Only (1)** is the correct setting: it still persists
  but leaves no automation clutter or undo flood. (Switching those needs a fresh
  duplication-safety re-verification before adoption — queued, not done here.)

**Framework support added:** `ParameterSpec(invisible=…)` and `dial(..., invisible=…)`
now emit `parameter_invisible`, with named constants
`PARAM_VIS_AUTOMATED_AND_STORED` / `PARAM_VIS_STORED_ONLY` / `PARAM_VIS_HIDDEN`
(parameters.py). Default behaviour is unchanged (key omitted → visibility 0).

---

## Prioritised opportunities (for future iterations)

1. **`setcursor` hover cursors** on every interactive hero (§4) — highest polish/effort ratio; pin the enum live first.
2. **`onidle`/`onidleout` hover** (§2) — robustness + auto-clear; verify the handlers fire in Live's v8ui.
3. **Keyboard nudge/delete on a focused hero** (§3) — a new modality; manual verification.
4. **Stored-Only for internal state hosts** (§7) — declutters automation lanes + fixes undo flood; re-run duplication safety.
5. **Pixel-perfect + balanced-margin sweep** (§6) — quick visual-quality pass.
