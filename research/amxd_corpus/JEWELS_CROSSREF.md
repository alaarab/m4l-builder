# Jewels Cross-Reference (Program 2)

The hard cross-reference of all 16 device studies is **`STUDY_SYNTHESIS.md`** in this
folder — a prioritized, device-cited integration backlog. This file is the index +
the ranked jewel summary; the full per-item detail (with source devices, effort,
priority) lives in `STUDY_SYNTHESIS.md`, and each device's `studies/<device>/_DIGEST.md`.

## The 4 convergent jewels (recur in nearly every premium device)

1. **Runtime `live.colors` theme bus** — read the user's Live skin at load
   (`live.thisdevice → live.colors → route → prepend <attr> → s ---bus`) and re-tint every
   control + jsui live, incl. active/zombie bypass dim. `grep live.colors src/` = 0. Cited 8+.
   → tasks B1. Devices: all AS_Console, Superberry, Chiral, Rainbow, Roulette, both LFOs.
2. **`jspainterfile` on a NATIVE control** — one stock `live.dial/numbox/tab` keeps native
   behaviour while a render-only mgraphics `.js` painter draws it. One box, no hidden param.
   → tasks C1. Devices: Chiral (whole UI), Superberry (~30 painters), Particle-Reverb, all AS.
3. **Whole DSP engine in ONE `gen~`/`mc.gen~` codebox + Data/Buffer/Delay state** —
   `gen_snippets.py` is stateless today (0 Data/Buffer/Delay/poke/peek). Unlocks granular,
   looper, freeze, sampler, polysynth, reverb. → tasks D1/D2/D3. Devices: stranular,
   Particle-Reverb, Superberry, Chiral, lfo-cluster.
4. **Live-native param metadata + persistence** — `parameter_initial_enable`+`parameter_initial`
   everywhere, `parameter_annotation_name`+`parameter_info` hover help, `parameter_units`+
   `unitstyle:9`; zero pattrstorage. → tasks A2/E1/E4. Devices: all.

## Confirmed defects
- **A1** parameterbanks shape (list-of-dicts → flat 8-slot longname list). **FIXED.**
- **A2** `parameter_annotation_name`/`parameter_info` not emitted (no framework support).

## Second tier (widely recurring)
MC poly-voice spine (D2), `gen~→buffer~→jsui` visualizer bus (D4), LOM click-to-map
modulator (E2), transparent-native-over-jsui composition (C5), stacked/gated 168px views
(C6), corpus-measured native sizing (C4: our `DIAL=(44,47)` too tall; workhorse `(41,35)`).

Build order is tracked as `[JEWEL …]` phren tasks (project m4l-builder), priority-ordered.
