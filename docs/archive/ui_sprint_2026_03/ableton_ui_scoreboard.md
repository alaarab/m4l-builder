# Ableton UI Scoreboard

This scoreboard is the shared baseline score view for flagship UI lanes.

Important:

- These are static repo judgments unless a note explicitly says otherwise.
- They are not substitutes for real in-Live validation.
- Use them to prioritize work, not to claim polished product quality early.

Reference rubric:

- `docs/ableton_ui_review_checklist.md`

## Evidence Classes

- `built`: a visible lane exists and can be judged structurally
- `hybrid`: partial implementation plus strong design docs
- `spec`: design-doc or shell-spec level only

## Current Baseline

| Lane | Evidence | Baseline Score | Confidence | Main Reason |
| --- | --- | --- | --- | --- |
| `Parametric EQ` | `built` | `25/40` | `medium` | strong graph-first identity, but contextual editing and compact story still lag |
| `Linear Phase EQ` | `built` | `26/40` | `medium` | strong product-role clarity, but selected-band strip and chip/editor sync are not final |
| `Spectrum Analyzer` | `hybrid` | `pending` | `low` | analyzer semantics are well specified, but the flagship standalone UI is not mature enough to score honestly |
| `Ladder Filter` | `hybrid` | `pending` | `low` | performance-oriented UI direction is clear, but there is not yet enough visible product behavior for a real score |
| `Granular Sampler` | `spec` | `pending` | `low` | the shell model is now explicit, but the lane is still primarily a product spec and shell plan |

## Lane Notes

### Parametric EQ

Static baseline breakdown:

- Hierarchy And First Glance: `4/5`
- Edit Speed: `3/5`
- Selection And Contextual Editing: `3/5`
- Compact Legibility: `2/5`
- State Clarity: `3/5`
- Analyzer And Meter Trust: `3/5`
- Parameter Grouping: `4/5`
- Native Feel: `3/5`

Immediate next move:

- make the selected-band rail the canonical editor and reduce card-first
  fallback

### Linear Phase EQ

Static baseline breakdown:

- Hierarchy And First Glance: `4/5`
- Edit Speed: `3/5`
- Selection And Contextual Editing: `3/5`
- Compact Legibility: `2/5`
- State Clarity: `4/5`
- Analyzer And Meter Trust: `3/5`
- Parameter Grouping: `4/5`
- Native Feel: `3/5`

Immediate next move:

- replace the selected-band strip with the intended contextual column and
  tighten graph, chip, and selected-band anti-drift behavior

### Spectrum Analyzer

Scoring gate before assigning a numeric baseline:

- standalone analyzer surface exists visibly enough to judge hierarchy
- control semantics are wired, not only specified
- one validation pass compares it against Ableton `Spectrum`

### Ladder Filter

Scoring gate before assigning a numeric baseline:

- one obvious central tone-shaping surface exists
- modulation and warning state are visible enough to judge
- at least one compact-view pass has been reviewed

### Granular Sampler

Scoring gate before assigning a numeric baseline:

- compact surface exists as a playable macro identity
- expanded waveform editor exists as the canonical region editor
- cross-surface state can be judged in one validation pass

## Updating Rules

Update this scoreboard when:

- a planned validation note becomes `complete`
- a built lane materially changes its primary editing model
- a spec or hybrid lane crosses the scoring gate into visible product form

Do not upgrade scores based only on better prose or stronger intentions.
