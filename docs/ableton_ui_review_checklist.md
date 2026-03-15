# Ableton UI Review Checklist

Use this checklist once per week and at the end of every major UI sprint.

Score each category from `1` to `5`.

- `1`: broken or misleading
- `2`: usable but clearly off-target
- `3`: competent
- `4`: strong and mostly native-feeling
- `5`: flagship-level

## Scored Categories

### 1. Hierarchy And First Glance

- Is the hero surface obvious in under three seconds?
- Does the eye land on the right place first?
- Are section surfaces and labels supporting the hierarchy instead of fighting
  it?

Score: `__/5`

### 2. Edit Speed

- Can the fastest common edit happen from the primary surface?
- Is there any slower widget path competing with the intended workflow?
- Does the UI feel faster than a raw control rack?

Score: `__/5`

### 3. Selection And Contextual Editing

- Is selection always visible?
- Do graph, chip, selected-object rail, and parameter state stay synchronized?
- Are contextual controls canonical rather than duplicated?

Score: `__/5`

### 4. Compact Legibility

- Does the chain view preserve device identity?
- Are critical states still readable at normal Ableton zoom and distance?
- Does compact mode show the right fast-access controls?

Score: `__/5`

### 5. State Clarity

- Can the user distinguish selected, enabled, bypassed, listened, and warning
  states?
- Are audio-affecting states more legible than display-only states?
- Does any color or indicator have conflicting meanings nearby?

Score: `__/5`

### 6. Analyzer And Meter Trust

- Is the analyzer or meter visually useful without stealing attention?
- Are source, smoothing, refresh, and hold semantics clear?
- Does overlay behavior support the main editing task?

Score: `__/5`

### 7. Parameter Grouping

- Are banks grouped by product tasks rather than implementation details?
- Are names consistent between visual objects and parameter rails?
- Are hidden duplicates disabled?

Score: `__/5`

### 8. Native Feel

- Does the device feel like one product instead of a builder demo?
- Is the chrome restrained?
- Does the interaction language feel closer to Live than to raw Max?

Score: `__/5`

## Structural Gate

Mark `yes` only if the condition is unambiguously true.

- One obvious primary editing surface: `yes / no`
- One canonical selected-object editing model: `yes / no`
- Compact and expanded surfaces agree: `yes / no`
- Visualization layers support editing, not decoration: `yes / no`
- Product role is legible from the UI itself: `yes / no`

## In-Live Gate

Run these during real playback.

- One fast change completed without hesitation: `pass / fail`
- One precise change completed without opening patch internals: `pass / fail`
- One exploratory change completed without losing track of active state:
  `pass / fail`
- No drift between graph, chip, selected-object, and parameter state:
  `pass / fail`
- Display remains readable at normal viewing distance: `pass / fail`

## Notes

- Strongest part:
- Weakest part:
- Most Ableton-native behavior:
- Most un-Ableton behavior:
- Immediate next change:

## Decision

- Overall score: `__/40`
- Result: `ship / iterate / redesign`
