# Linear-Phase EQ UI

This is the design target for the shipped v1 `Linear-Phase EQ` device.

The goal is not "Parametric EQ but with more controls". The goal is a device
that feels deliberate for mastering and precision work:

- large graph first
- selected-band editing second
- analyzer and quality mode always visible
- latency and processing state made explicit

## Product Role

Use this device when the user wants:

- a familiar EQ graph
- linear-phase processing as a first-class feature
- precise, slower, mastering-style moves
- analyzer-backed decisions

Do not use this layout for the crossover device. The crossover remains a
separate routing tool.

## Layout

The original mockup was drawn larger for hierarchy work, but the shipped Max for
Live device has to fit the standard compact device footprint. Treat the
structure below as proportional guidance, not a literal pixel target.

```text
+--------------------------------------------------------------------------------------+
| LINEAR-PHASE EQ          QUALITY [SHORT] [MEDIUM] [HIGH]   ANALYZER [OFF PRE POST]    |
| Mastering-grade EQ       RANGE [3 6 12 30]   COLLISION [ON]   LATENCY 85.3 ms         |
+--------------------------------------------------------------------------------------+
|                                                                                      |
|   +------------------------------------------------------------------------------+   |
|   |                                                                              |   |
|   |                                 HERO GRAPH                                   |   |
|   |                     analyzer + nodes + curve + HUD                           |   |
|   |                                                                              |   |
|   |                                                                              |   |
|   |                                                                              |   |
|   |                                                                              |   |
|   +------------------------------------------------------------------------------+   |
|                                                                      OUTPUT GAIN     |
|                                                                      BYPASS          |
+--------------------------------------------------------------------------------------+
| BAND 4  Peak      FREQ 2.50 kHz      GAIN +2.5 dB      Q 1.20      STATUS Enabled    |
| TYPE [Peak v]     SLOPE [12 24 48]   ENABLE [ON]       SOLO [OFF]                   |
+--------------------------------------------------------------------------------------+
| B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | + ADD BAND                                |
+--------------------------------------------------------------------------------------+
```

## Regions

### 1. Top Bar

Purpose: quality selection, analyzer state, and session context.

Required controls:

- `Quality`
  - `Short`
  - `Medium`
  - `High`
- `Analyzer`
  - `Off`
  - `Pre`
  - `Post`
- `Range`
  - `3`
  - `6`
  - `12`
  - `30`
- `Collision`
  - on/off for label overlap handling
- visible latency readout derived from the active FFT size and sample rate

This bar should feel informational and surgical, not decorative.

### 2. Hero Graph

Purpose: this is the main editing surface.

Required behavior:

- graph dominates the device
- analyzer sits inside the graph, not in a separate box
- selected band draws guide lines and HUD
- graph supports:
  - drag
  - wheel for Q
  - double-click empty graph to add band
  - delete/disable band
  - direct selection

If the graph is weak, the whole device will feel fake.

### 3. Right Utility Rail

Purpose: mix/output functions that should not clutter the graph.

Required controls:

- output gain
- bypass

This should be narrow and secondary.

### 4. Selected-Band Detail Strip

Purpose: the graph chooses the band, this strip gives exact control.

Required controls:

- band number and type
- frequency
- gain
- Q
- slope
- enable/solo

Slope is only meaningful for low-cut and high-cut bands in v1. Other band types
leave the slope control visually present but operationally ignored.

### 5. Band Chips Row

Purpose: fast navigation and band identity.

Requirements:

- eight fixed band chips
- colored by band color
- chip state shows enabled/disabled and selected focus
- plus button for add band

This row should feel like fast access, not a second control panel.

## Visual Direction

This should look more like a mastering tool than a general utility:

- dark graphite base
- cool cyan analyzer
- clean white composite curve
- saturated band colors for nodes only
- soft bordered panels, not heavy boxes
- small typography in the top bar
- bigger readable labels in the selected-band strip

## Design Tokens

Suggested colors:

- background: `#0d0e11`
- surface: `#13161a`
- surface-alt: `#171b20`
- border: `#2b3138`
- text: `#edf1f7`
- text-dim: `#8c95a1`
- analyzer: `#3dd8ff`
- curve: `#f2f5fb`

Band accents:

- red, orange, yellow, green, cyan, blue, violet, magenta

## Interaction Notes

- The selected band should always have a strong visual focus state.
- Analyzer state must be obvious at a glance.
- The active quality mode must visibly communicate that latency exists.
- Band detail strip should update immediately when the graph selection changes.
- The bottom row should make it obvious which bands are active and which one is selected.
- Graph interaction should be validated in Live itself, not inferred from
  screenshots of generated patch data.

## Live QA Gate

Use `LiveMCP` as the default verification loop for this device.

Required checks before treating graph work as done:

- load a fresh instance in Ableton Live after rebuilding, so js sidecar changes
  are not masked by stale device state
- start real playback and confirm the device is passing signal
- verify node creation, selection, dragging, wheel-Q changes, and deletion in
  the actual device view
- verify the analyzer is visibly useful behind the nodes, not just technically
  connected
- verify startup state in Live: neutral graph, no misleading forced selection,
  and controls synced to what the graph shows

For this device, pytest coverage is necessary but not sufficient. Visual and
interaction regressions must be caught with `LiveMCP`-driven Live QA.

## Build Order

1. Match this layout structurally.
2. Match the graph proportions and top bar.
3. Add the selected-band strip.
4. Add band chips.
5. Only then refine spacing, type, and colors.
