# AMXD Corpus Report

- Root: `/Users/squidbot/Music/Ableton/Factory Packs/M4L Building Tools`
- Files scanned: `138`
- Parsed successfully: `138`
- Parse errors: `0`
- Device types: `{"audio_effect": 86, "instrument": 11, "midi_effect": 41}`
- Source lanes: `{"factory": 138}`
- Bridge-enabled files: `0`
- Files with helper patterns: `0`
- Files with recipe patterns: `0`
- Files with generic motifs: `68`
- Files with named-bus networks: `17`
- Files with cross-scope named-bus networks: `6`
- Files with semantic Live API helper recoveries: `0`
- Files with Live API helper opportunities: `0`
- Files with controller-shell candidates: `0`
- Files with behavior hints: `0`
- Files with mapping-behavior traces: `45`
- Files with embedded-ui shell candidates: `49`
- Files with named-bus router candidates: `3`
- Files with init-dispatch candidates: `13`
- Files with state-bundle router candidates: `7`
- Files with presentation widget clusters: `115`
- Files with poly-shell candidates: `8`
- Files with poly-shell bank candidates: `0`
- Files with poly-editor bank candidates: `0`
- Files with mapping semantic candidates: `0`
- Files with mapping-workflow candidates: `0`
- Files with sample-buffer candidates: `0`
- Files with gen-processing candidates: `0`
- Files with embedded sample-buffer candidates: `0`
- Files with embedded gen-processing candidates: `0`
- Files with first-party API rig candidates: `21`
- Files with first-party abstraction-host candidates: `21`
- Files with building-block candidates: `26`
- Files with embedded patchers: `82`
- Files with embedded helper patterns: `1`
- Files with embedded recipes: `0`
- Files with embedded motifs: `45`
- Files missing sidecars: `72`
- Avg boxes / lines: `54.46` / `28.2`
- Avg controls / displays: `7.94` / `4.2`
- Avg embedded patchers: `3.32`
- Avg embedded patterns / recipes / motifs: `0.01` / `0` / `1.7`

## Top Patterns

- None

## Top Recipes

- None

## Top Motifs

- `embedded_patcher`: `183`
- `scheduler_chain`: `22`
- `named_bus`: `9`
- `state_bundle`: `7`
- `live_api_component`: `3`

## Top Motif Signatures

- `embedded_patcher:subpatcher`: `99`
- `embedded_patcher:bpatcher`: `72`
- `scheduler_chain:init_chain`: `14`
- `embedded_patcher:poly`: `8`
- `named_bus:signal`: `6`
- `scheduler_chain:timed_dispatch`: `6`
- `embedded_patcher:pfft`: `4`
- `state_bundle:bundle_pack`: `4`
- `named_bus:message`: `3`
- `state_bundle:bundle_fanout`: `3`

## Top Maxclasses

- `comment`: `3759`
- `newobj`: `1282`
- `live.dial`: `335`
- `message`: `213`
- `live.numbox`: `184`
- `panel`: `184`
- `live.text`: `182`
- `number`: `174`
- `live.menu`: `154`
- `live.toolbar`: `136`

## Top Object Names

- `comment`: `3759`
- `message`: `213`
- `patcher`: `191`
- `p`: `99`
- `plugout~`: `97`
- `plugin~`: `86`
- `*~`: `50`
- `midiin`: `42`
- `midiout`: `42`
- `noteout`: `32`

## Top Control Maxclasses

- `live.dial`: `335`
- `live.numbox`: `184`
- `live.text`: `182`
- `live.menu`: `154`
- `live.button`: `117`
- `live.gain~`: `45`
- `live.slider`: `31`
- `live.tab`: `20`
- `newobj`: `19`
- `live.grid`: `5`

## Top Control Unitstyles

- `0`: `210`
- `2`: `102`
- `4`: `100`
- `1`: `77`
- `5`: `74`
- `3`: `50`
- `6`: `26`
- `8`: `24`
- `7`: `16`
- `10`: `2`

## Top Display Roles

- `widgets`: `408`
- `monitors`: `100`
- `embedded_patchers`: `72`
- `custom_ui`: `0`
- `labels`: `0`

## Top Embedded Patcher Host Kinds

- `embedded`: `349`
- `subpatcher`: `108`
- `bpatcher`: `1`

## Top Embedded Patterns

- `selector`: `1`

## Top Embedded Recipes

- None

## Top Embedded Motifs

- `controller_dispatch`: `69`
- `state_bundle`: `49`
- `live_api_component`: `40`
- `embedded_patcher`: `32`
- `named_bus`: `23`
- `scheduler_chain`: `22`

## Top Live API Path Targets

- `live_set view detail_clip`: `1`

## Top Live API Properties

- None

## Top Live API Get Targets

- None

## Top Live API Set Targets

- None

## Top Live API Call Targets

- None

## Top Live API Archetypes

- None

## Top Named Bus Networks

- `---ClipID`: `2`
- `---DeviceParameterID`: `2`
- `--->live.grid`: `1`
- `---ApplicationID`: `1`
- `---ApplicationViewID`: `1`
- `---ClipSlotID`: `1`
- `---CombL`: `1`
- `---CombR`: `1`
- `---CuePointID`: `1`
- `---DelL`: `1`

## Top Cross-Scope Named Bus Networks

- `---ClipID`: `2`
- `---ClipSlotID`: `1`
- `---SceneID`: `1`
- `---SongID`: `1`
- `---TrackID`: `1`

## Top Live API Helper Recoveries

- None

## Top Live API Normalization Levels

- None

## Top Live API Helper Opportunities

- None

## Top Live API Helper Opportunity Blockers

- None

## Top Controller Shell Candidates

- None

## Top Behavior Hints

- None

## Top Mapping Behavior Traces

- `periodic_modulation_core`: `25`
- `trigger_source_cluster`: `13`
- `parameter_target_scan`: `9`
- `random_value_generation`: `4`
- `lane_update_paths`: `1`

## Top Embedded UI Shell Candidates

- `embedded_ui_shell_v2`: `171`

## Top Named Bus Router Candidates

- `named_bus_router`: `9`

## Top Init Dispatch Candidates

- `init_dispatch_chain`: `14`

## Top State Bundle Router Candidates

- `state_bundle_router`: `7`

## Top Presentation Widget Cluster Candidates

- `presentation_widget_cluster`: `119`

## Top Poly Shell Candidates

- `poly_shell`: `8`

## Top Poly Shell Bank Candidates

- None

## Top Poly Editor Bank Candidates

- None

## Top Mapping Semantic Candidates

- None

## Top Mapping Workflow Candidates

- None

## Top Sample Buffer Candidates

- None

## Top Gen Processing Candidates

- None

## Top Embedded Sample Buffer Candidates

- None

## Top Embedded Gen Processing Candidates

- None

## Top First-Party API Rig Candidates

- `first_party_api_rig`: `21`

## Top First-Party Abstraction Host Candidates

- `M4L.bal2~`: `10`
- `M4L.envfol~`: `3`
- `M4L.api.ChangeTrackVolume`: `2`
- `M4L.api.DeviceParameter`: `2`
- `M4L.bal1~`: `2`
- `M4L.vdelay~`: `2`
- `M4L.api.FireSelectedClip`: `1`
- `M4L.api.FireSelectedScene`: `1`
- `M4L.api.SelectNextTrack`: `1`
- `M4L.api.SelectPreviousTrack`: `1`

## Top First-Party Abstraction Host Families

- `balance_shell`: `10`
- `api_internal_shell`: `8`
- `gain_shell`: `4`
- `envelope_follower_shell`: `3`
- `pan_shell`: `2`
- `variable_delay_shell`: `2`
- `mid_side_shell`: `1`

## Top Building Block Candidates

- `Max ANotePlayer`: `1`
- `Max AutoPanner`: `1`
- `Max BalanceDualMono`: `1`
- `Max BalanceStereo`: `1`
- `Max Chorus`: `1`
- `Max CombFilter`: `1`
- `Max CutHacker`: `1`
- `Max Degrader`: `1`
- `Max DelayLine`: `1`
- `Max EqParametric1`: `1`

## Top Embedded Live API Path Targets

- `this_device`: `3`
- `live_set view selected_parameter`: `1`

## Top Embedded Live API Properties

- `sends`: `3`
- `loop_end`: `1`
- `loop_start`: `1`
- `looping`: `1`
- `name`: `1`
- `playing_status`: `1`

## Top Embedded Live API Get Targets

- `mixer_device`: `3`
- `name`: `3`
- `parameters`: `3`
- `value`: `3`
- `class_name`: `2`
- `is_quantized`: `2`
- `max`: `2`
- `min`: `2`
- `default_value`: `1`
- `is_enabled`: `1`

## Top Embedded Live API Set Targets

- None

## Top Embedded Live API Call Targets

- None

## Top Embedded Live API Archetypes

- `parameter_probe`: `5`

## Top Source Lanes

- `factory`: `138`

## Top Source Families

- `M4L Building Tools`: `138`

## Top Pack Names

- `M4L Building Tools`: `138`

## Top Pack Sections

- `M4L Building Tools / Lesson Devices`: `70`
- `M4L Building Tools / Building Blocks`: `26`
- `M4L Building Tools / API`: `21`
- `M4L Building Tools / Tools`: `21`

## Top Missing Sidecars

- `M4L.chooser.js`: `28`
- `M4L.Chooser.maxpat`: `15`
- `M4L.SignalToLiveParam.maxpat`: `13`
- `live.property.maxpat`: `13`
- `M4L.bal2~.maxpat`: `10`
- `live.function.maxpat`: `10`
- `M4L.vdelay~.maxpat`: `5`
- `M4L.dl.vdelay~.maxpat`: `4`
- `M4L.envfol~.maxpat`: `3`
- `M4L.fm.FMvoice~.maxpat`: `3`

## Top Error Types

- None

## Top Errors

- None

## Largest Devices By Boxes

- `Max SignalViewers.amxd`: `144` boxes (`audio_effect`)
- `Max SignalAnalyzer.amxd`: `141` boxes (`audio_effect`)
- `Max Api SendsXnodes.amxd`: `138` boxes (`audio_effect`)
- `Max Api SendsPan.amxd`: `133` boxes (`audio_effect`)
- `Max CutKiller.amxd`: `129` boxes (`audio_effect`)
- `Max Api SendsRand.amxd`: `118` boxes (`audio_effect`)
- `Max Api CtrlImproBeat.amxd`: `117` boxes (`audio_effect`)
- `M4L.bg.15.AllTogether.amxd`: `111` boxes (`midi_effect`)
- `Max ImproBeat.amxd`: `111` boxes (`midi_effect`)
- `Max EqGraphic31.amxd`: `109` boxes (`audio_effect`)

## Largest Devices By Lines

- `Max Api SendsPan.amxd`: `116` lines (`audio_effect`)
- `Max Api SendsXnodes.amxd`: `94` lines (`audio_effect`)
- `Max CutKiller.amxd`: `81` lines (`audio_effect`)
- `Max SignalViewers.amxd`: `81` lines (`audio_effect`)
- `Max SignalAnalyzer.amxd`: `76` lines (`audio_effect`)
- `M4L.fm.10.TotalRandom.amxd`: `71` lines (`instrument`)
- `Max Api SendsRand.amxd`: `65` lines (`audio_effect`)
- `Max Compressor.amxd`: `64` lines (`audio_effect`)
- `Max PitchScaler.amxd`: `64` lines (`midi_effect`)
- `Max Api CtrlImproBeat.amxd`: `62` lines (`audio_effect`)

## Top Reverse Candidates

- `Max Api SendsXnodes.amxd`: score `216.0` (audio_effect) -- 18 generic motifs, 60 embedded patchers
- `Max Api SendsPan.amxd`: score `186.0` (audio_effect) -- 12 generic motifs, 54 embedded patchers
- `Max Api SendsRand.amxd`: score `176.75` (audio_effect) -- 12 generic motifs, 51 embedded patchers, 1 missing sidecars
- `Max Api DeviceExplorer.amxd`: score `66.5` (audio_effect) -- 2 generic motifs, 21 embedded patchers, 2 missing sidecars
- `M4L.fm.10.TotalRandom.amxd`: score `57.25` (instrument) -- 12 generic motifs, 10 embedded patchers, 1 scheduler hits, 1 state-bundle hits, 1 missing sidecars
- `Max Api DeviceAnimator.amxd`: score `39.5` (audio_effect) -- 18 generic motifs, 2 embedded patchers, 11 missing sidecars
- `Max DopplerPan.amxd`: score `35.0` (audio_effect) -- 7 generic motifs, 7 embedded patchers
- `Max MidiGran.amxd`: score `33.75` (midi_effect) -- 8 generic motifs, 5 embedded patchers, 1 scheduler hits, 1 state-bundle hits, 3 missing sidecars
- `M4L.dl.11.FilterDelay.amxd`: score `31.75` (audio_effect) -- 4 generic motifs, 8 embedded patchers, 1 missing sidecars
- `M4L.dl.13.Harmonizer.amxd`: score `31.5` (audio_effect) -- 4 generic motifs, 8 embedded patchers, 2 missing sidecars

## Top Reverse Candidate Families

- `Max Api SendsXnodes`: best score `216.0`, `1` variant(s), best file `Max Api SendsXnodes.amxd` -- 18 generic motifs, 60 embedded patchers
- `Max Api SendsPan`: best score `186.0`, `1` variant(s), best file `Max Api SendsPan.amxd` -- 12 generic motifs, 54 embedded patchers
- `Max Api SendsRand`: best score `176.75`, `1` variant(s), best file `Max Api SendsRand.amxd` -- 12 generic motifs, 51 embedded patchers, 1 missing sidecars
- `Max Api DeviceExplorer`: best score `66.5`, `1` variant(s), best file `Max Api DeviceExplorer.amxd` -- 2 generic motifs, 21 embedded patchers, 2 missing sidecars
- `M4L.fm.10.TotalRandom`: best score `57.25`, `1` variant(s), best file `M4L.fm.10.TotalRandom.amxd` -- 12 generic motifs, 10 embedded patchers, 1 scheduler hits, 1 state-bundle hits, 1 missing sidecars
- `Max Api DeviceAnimator`: best score `39.5`, `1` variant(s), best file `Max Api DeviceAnimator.amxd` -- 18 generic motifs, 2 embedded patchers, 11 missing sidecars
- `Max DopplerPan`: best score `35.0`, `1` variant(s), best file `Max DopplerPan.amxd` -- 7 generic motifs, 7 embedded patchers
- `Max MidiGran`: best score `33.75`, `1` variant(s), best file `Max MidiGran.amxd` -- 8 generic motifs, 5 embedded patchers, 1 scheduler hits, 1 state-bundle hits, 3 missing sidecars
- `M4L.dl.11.FilterDelay`: best score `31.75`, `1` variant(s), best file `M4L.dl.11.FilterDelay.amxd` -- 4 generic motifs, 8 embedded patchers, 1 missing sidecars
- `M4L.dl.13.Harmonizer`: best score `31.5`, `1` variant(s), best file `M4L.dl.13.Harmonizer.amxd` -- 4 generic motifs, 8 embedded patchers, 2 missing sidecars

## Top Reverse Candidate Family Profiles

- `Max Api SendsXnodes`: best score `216.0`, `1` variant(s), embedded patchers `60`, missing sidecars `0` -- top motifs embedded_patcher:subpatcher:18
- `Max Api SendsPan`: best score `186.0`, `1` variant(s), embedded patchers `54`, missing sidecars `0` -- top motifs embedded_patcher:subpatcher:12
- `Max Api SendsRand`: best score `176.75`, `1` variant(s), embedded patchers `51`, missing sidecars `1` -- top motifs embedded_patcher:subpatcher:12
- `Max Api DeviceExplorer`: best score `66.5`, `1` variant(s), embedded patchers `21`, missing sidecars `2` -- top motifs embedded_patcher:bpatcher:2
- `Max Api DeviceAnimator`: best score `39.5`, `1` variant(s), embedded patchers `2`, missing sidecars `11` -- top motifs embedded_patcher:bpatcher:18

## Source Lane Profiles

- `factory`: `138` file(s), avg boxes `54.46`, avg lines `28.2`, motifs `embedded_patcher:bpatcher, embedded_patcher:subpatcher, scheduler_chain:init_chain`
