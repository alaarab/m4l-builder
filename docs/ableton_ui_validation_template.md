# Ableton UI Validation Template

Use this template after every major UI sprint.

If screenshots are available, place them in the same directory as the note and
link them from the relevant sections.

## Metadata

- Device lane:
- Sprint week:
- Build or commit:
- Reviewer:
- Validation date:
- Status: `planned / in-progress / complete`

## Sprint Goal

- What UI behavior was this sprint trying to improve?
- What should feel more Ableton-native now?

## Assets

- Chain-view screenshot:
- Expanded-view screenshot:
- Optional focused crop or video:

## Chain View Readability

- Can the device identity be understood at normal Ableton viewing distance?
- Are the most important states still visible?
- Which control is the fastest chain-view interaction?

## Expanded View Readability

- Is the hero surface obvious immediately?
- Is the selected-object editor obvious?
- Do utility controls stay secondary?

## Interaction Scenarios

### Fast Change

- Task:
- Result:
- Friction:

### Precise Change

- Task:
- Result:
- Friction:

### Exploratory Change

- Task:
- Result:
- Friction:

## State Drift Check

- Graph and selected-object rail agree: `yes / no`
- Chip row or quick-nav state agrees: `yes / no`
- Parameter state agrees: `yes / no`
- Display-only states are distinguishable from audio states: `yes / no`

## Analyzer And Meter Check

- Are analyzer or meter semantics understandable?
- Do overlays stay secondary to the editing target?
- Is any smoothing, hold, or source-routing state confusing?

## Ableton-Native Score

Use `docs/ableton_ui_review_checklist.md`.

- Overall score:
- Strongest category:
- Weakest category:

## Decision

- Ship as-is
- Iterate
- Redesign surface model

## Next Changes

- Highest-value follow-up:
- One thing to keep:
- One thing to remove or simplify:
