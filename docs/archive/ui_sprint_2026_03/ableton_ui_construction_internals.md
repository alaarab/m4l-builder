# Ableton UI Construction Internals

This document explains how UI is actually built in this repo.

It exists because the current flagship devices did not emerge from a mature
Ableton UI framework. The graph-heavy tools were built first, and some of them
already feel good. The point of the current sprint is to understand why those
parts work, make the missing internals legible, and standardize the rest of the
control grammar around them.

## Current Construction Stack

The UI stack has five layers.

### 1. Raw presentation-object factories

File:

- `src/m4l_builder/ui.py`

This is the lowest real UI layer in the public builder API.

It creates raw Max box dicts for:

- Live parameter controls such as `live.dial`, `live.toggle`, `live.tab`,
  `live.menu`, `live.numbox`, `live.slider`, `live.button`, and `live.text`
- display or utility widgets such as `live.comment`, `live.scope~`,
  `live.meter~`, `multislider`, `swatch`, `textedit`, `matrixctrl`,
  `live.step`, `live.grid`, and `nodes`
- custom script-backed surfaces such as `jsui` and `v8ui`

Important internal fact:

- this layer is still mostly a thin box factory
- it knows how to write `presentation_rect`, `parameter_enable`, and
  `saved_attribute_attributes`
- it does not know product role, contextual-editor semantics, section meaning,
  or selected-object behavior

### 2. Device wrapper and theme injection

File:

- `src/m4l_builder/device.py`

`Device.add_*` methods mostly forward into `ui.py` and inject theme defaults.

This layer is useful, but it is still shallow:

- colors can be inherited from the theme
- `jsui` and `v8ui` sidecar files are registered automatically
- parameter-bank metadata can be assigned later

What it does not do:

- define semantic control groups
- define compact vs expanded role
- define selected-object editors
- prevent duplicate live control surfaces from drifting apart

### 3. Geometric layout helpers

File:

- `src/m4l_builder/layout.py`

`Row`, `Column`, and `Grid` solve placement. They do not solve UI meaning.

That distinction matters.

The current layout system is good for:

- spacing controls quickly
- reducing manual `presentation_rect` repetition
- building regular grids and strips

The current layout system does not yet express:

- hero surface vs support rail
- section frame vs utility strip
- compact shell vs expanded shell
- selected-object editor vs navigation surface

So the repo has geometry helpers, not a semantic Ableton layout system yet.

### 4. Script-backed custom surfaces

Files:

- `src/m4l_builder/engines/`
- per-plugin JS sidecars in `Max4LivePlugins/plugins/*`

This is where the repo is strongest.

The graph and display layer already supports:

- draggable EQ nodes
- spectrum and waveform displays
- XY and grid interaction
- selected-band editor surfaces
- custom chip rows and visual state surfaces

Why these often feel better than the stock control layer:

- they were built as one direct interaction surface
- they carry a stronger product role than a row of generic widgets
- state encoding and drawing live in one place instead of being scattered
  across many small controls

This is why the graph work can feel genuinely good even while the surrounding
control grammar still feels unfinished.

### 5. Plugin-local state and routing shells

Files:

- `Max4LivePlugins/plugins/*/build.py`
- plugin-specific JS state coordinators and sidecars

This is where most flagship UI behavior is actually decided right now.

Typical pattern:

1. create visible controls and displays
2. create hidden proxy controls when needed
3. create `route ...`, `pak`, `prepend`, `pack`, `int`, `gate`, and `message`
   objects for synchronization
4. fan state into the graph, chips, selected-object editor, and parameter
   controls
5. route UI gestures back into parameter-bearing controls

This works, but it is hand-built per device.

That means:

- the repo already has capability
- the repo does not yet have one shared abstraction for contextual editing

## UI Element Families

The repo currently mixes several kinds of UI elements. Treating them as one
category makes the internals harder to reason about.

### A. Parameter-bearing Live controls

Examples:

- `live.dial`
- `live.toggle`
- `live.tab`
- `live.menu`
- `live.numbox`
- `live.slider`
- `live.button`
- `live.text`
- `live.gain~`

These matter because they create real device parameters through
`saved_attribute_attributes.valueof`.

This is the part of the build that determines:

- parameter name
- range
- unit style
- enum values
- initial value
- automation identity

Current weakness:

- this metadata is still specified one control at a time
- the repo does not yet have a first-class parameter spec object that can drive
  both UI construction and product-level review

### B. Presentation-only or mostly-display controls

Examples:

- `live.comment`
- `live.scope~`
- `live.meter~`
- `panel`
- `fpic`

These help hierarchy and feedback, but they are not the real editing model.

These elements become a problem when they start visually competing with the
actual editor surface.

### C. Generic Max widgets

Examples:

- `multislider`
- `matrixctrl`
- `umenu`
- `textbutton`
- `nodes`
- `live.step`
- `live.grid`

These are useful when Live-native controls are too limited, but they do not
automatically carry Ableton-native semantics. They need stronger framing from
the surrounding layout and state model.

### D. Custom `jsui` and `v8ui` surfaces

Examples:

- EQ graph displays
- analyzer plots
- selected-band columns
- chip rows

These are often the hero surfaces in flagship devices.

They are also where the repo currently gets the most product identity per line
of code.

### E. Live API and controller-side internals

Files:

- `src/m4l_builder/live_api.py`
- `src/m4l_builder/controller_shells.py`
- `src/m4l_builder/livemcp_bridge.py`
- `src/m4l_builder/reverse.py`

These are not normal presentation widgets, but they matter for UI internals.

They support:

- observing Live state
- mapping controllers
- editing patcher attributes from LiveMCP
- reverse-lifting existing devices into reusable abstractions

This is relevant because future UI standardization should not stop at drawing.
It should also be informed by how state, controllers, and extracted patterns
move through the patch.

## Why The Graphs Felt Good

The current direct-manip graph work is not an accident.

It feels good because it already has several properties that the rest of the UI
still lacks:

- one obvious hero surface
- direct edit feedback at the point of interaction
- reduced dependence on generic widgets
- stronger local state encoding
- tighter visual identity

In other words, the graph work reached a product-level interaction model before
the shared widget framework did.

## Where The Current Confusion Comes From

The repo exposes a lot of capability, but not enough semantics.

The confusing part is not that the builder cannot create UI elements.

The confusing part is that the framework currently leaves these decisions to
each device:

- which surface is canonical
- which control is only a proxy
- which controls are real parameters vs local UI mirrors
- how selected-object state is synchronized
- where compact behavior stops and expanded behavior begins
- how parameter metadata maps back to product tasks

That is why a device can have a strong graph and still feel internally noisy.

## Current Structural Gaps

These are the main framework gaps behind the “UI elements and internals” issue.

### Missing parameter-spec layer

The library can emit parameter-bearing controls, but it does not yet provide a
first-class semantic parameter description that can drive:

- control creation
- selected-object editors
- compact mirrors
- parameter-bank naming
- tests for metadata correctness

### Missing contextual-editor abstraction

Contextual editors are currently hand-rolled in plugin code.

The repo needs a stronger shared model for:

- selection source
- selected-object state fan-out
- canonical editor designation
- navigation surfaces such as chip rows
- disabled or hidden secondary mirrors

### Layout is geometric, not semantic

`Row`, `Column`, and `Grid` make box placement easier, but they do not express
UI meaning. A semantic layer is still missing for sections such as:

- hero graph
- utility strip
- compact shell
- selected-object rail
- detail panel

### Theme injection is shallow

Themes help with consistency, but they only inject local color defaults.

They do not yet enforce:

- state color grammar
- hierarchy defaults
- compact-view emphasis
- warning-state behavior

### Plugin-local routing still carries too much UI policy

A lot of real UI behavior currently lives inside explicit patcher routing in
`Max4LivePlugins/plugins/*/build.py`.

That is normal for advanced devices, but it also means the shared API has not
absorbed the repeated parts yet.

## What The Sprint Should Improve

The goal is not to replace custom surfaces with generic controls.

The goal is to make the whole stack as coherent as the best graph surfaces
already are.

Priority order:

1. preserve the strong graph/direct-manip interaction layer
2. reduce duplicated live contextual editors
3. make navigation and selection surfaces more explicit
4. raise parameter metadata to a more semantic layer
5. introduce semantic layout patterns above `Row`, `Column`, and `Grid`

## Practical Read For New Work

If you are designing a flagship device now:

- use custom surfaces for the real editing story
- use Live controls where real parameter identity matters
- treat layout helpers as geometry tools, not product semantics
- assume plugin-local state routing is part of the product until the framework
  absorbs it
- do not mistake “the library can emit this widget” for “the repo has a shared
  interaction model for this job”
