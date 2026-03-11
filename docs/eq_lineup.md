# EQ Lineup

This project should treat tonal EQ, linear-phase crossover work, and eventual
linear-phase mastering EQ as separate products.

## Why Separate Them

`Parametric EQ` and a linear-phase band splitter solve different problems.

- A regular parametric EQ is for tonal shaping, resonance control, carving, and
  mix decisions that need a fast graph, analyzer, and per-band editing.
- A linear-phase crossover is for splitting audio into bands that will be
  processed differently and then recombined without the relative phase rotation
  of minimum-phase crossover filters.
- A future linear-phase mastering EQ is for corrective or mastering work where
  latency is acceptable and the user wants a familiar EQ interface with a
  processing-mode choice.

Trying to force all three into one first device will produce the wrong UI.

## Product Roles

### 1. Parametric EQ

Primary job: flagship mix EQ.

Current direction:

- Pro-Q / EQ Eight style graph
- analyzer-backed interaction
- direct graph band creation and deletion
- multiple filter types
- fast editing workflow

Future requirements:

- selected-band detail strip
- more filter shapes
- per-band stereo placement
- dynamic EQ
- spectral dynamics
- larger/resizable editing surface

### 2. Linear-Phase Crossover

Primary job: phase-safe multiband routing and recombination.

Current direction:

- two crossover frequencies
- low/mid/high trims
- band audition
- complementary FFT masks inside `pfft~`

UI priority:

- make split points obvious
- make latency and recombination behavior obvious
- keep controls minimal

This device should not pretend to be a full parametric EQ. It is a crossover
and routing utility.

### 3. Linear-Phase EQ

Primary job: familiar EQ moves with a linear-phase processing option.

Current direction:

- dedicated `linear_phase_eq.py` example with its own graph engine
- separate from `Parametric EQ` and `Linear-Phase Crossover`
- fixed quality modes (`Short`, `Medium`, `High`) with explicit latency
- selected-band strip + band chips + FFT response-table backend

Suggested scope:

- keep tightening the compact M4L layout until it feels deliberate in Live
- improve audition workflow and chip/strip edge cases
- constrain expectations around latency and ringing
- keep analyzer and node workflow aligned with the flagship EQ where it helps

This is the closest product to a "Pro-Q with linear-phase mode" target.

Verification rule:

- treat `LiveMCP` as the default QA path for EQ UI work
- do not sign off on graph, analyzer, or node-interaction changes from tests
  alone
- always verify a fresh Live load, active playback, and visible node/analyzer
  behavior in the device view

## Decision

As of March 10, 2026, the recommended path is:

1. Keep building `Parametric EQ` as the flagship regular EQ.
2. Keep `Linear-Phase Crossover` as a dedicated splitting tool.
3. Add a separate `Linear-Phase EQ` later instead of forcing crossover logic
   into the flagship EQ UI.

## User Workflow

The expected workflow becomes simple:

- Need tone shaping: use `Parametric EQ`
- Need clean band splitting for separate processing: use `Linear-Phase Crossover`
- Need mastering-style linear-phase EQ moves: use the future `Linear-Phase EQ`
