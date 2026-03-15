# Ableton UI Sprint Tracker

This tracker keeps the 90-day Ableton UI sprint attached to concrete repo
artifacts.

Use it alongside:

- `docs/ableton_ui_90_day_sprint.md`
- `docs/ableton_ui_playbook.md`
- `docs/ableton_ui_scoreboard.md`
- `docs/ui_validation/README.md`

## Status Legend

- `complete`: artifact exists and the intended review work is finished
- `in-progress`: artifact exists but the Live-side validation or synthesis is
  still incomplete
- `planned`: placeholder exists, work not yet run
- `missing`: no artifact yet

## Sprint Progress

| Window | Focus | Reference Devices | Repo Targets | Required Artifacts | Current Status |
| --- | --- | --- | --- | --- | --- |
| Week 00 | Baseline audit | n/a | Shared repo baseline | `docs/ableton_ui_baseline_audit.md`, `docs/ui_validation/week_00_baseline_repo_audit.md` | `in-progress` |
| Weeks 01-02 | Mental model | `EQ Eight`, `Spectrum`, `Auto Filter`, `Utility` | `Parametric EQ`, `Linear Phase EQ`, analyzer lane, filter lane | four teardown notes, playbook draft, review checklist | `in-progress` |
| Weeks 03-04 | Graph-first EQ | `EQ Eight` | `Parametric EQ` | `docs/ui_validation/week_03_parametric_eq.md` | `planned` |
| Weeks 05-06 | Precision EQ | `EQ Eight`, `Spectrum` | `Linear Phase EQ` | `docs/ui_validation/week_05_linear_phase_eq.md` | `planned` |
| Weeks 07-08 | Analyzer trust | `Spectrum` | `Spectrum Analyzer` | `docs/ui_validation/week_07_spectrum_analyzer.md` | `planned` |
| Weeks 09-10 | Performance filter UI | `Auto Filter` | `Ladder Filter` | `docs/ui_validation/week_09_ladder_filter.md` | `planned` |
| Weeks 11-12 | Framework consolidation | revisit set, add `Simpler` | shared framework, `Granular Sampler` shell | `docs/ui_validation/week_11_framework_reaudit.md` | `planned` |
| Later references | advanced study set | `Glue Compressor`, `Wavetable`, `Echo` | future dynamics, deep-editor, and creative-effect lanes | teardown notes and repo translations | `in-progress` |

## Artifact Checklist

### Shared Standards

- `complete`: `docs/ableton_ui_playbook.md`
- `complete`: `docs/ableton_ui_review_checklist.md`
- `complete`: `docs/ableton_ui_90_day_sprint.md`
- `complete`: `docs/dual_surface_shell_guidance.md`
- `complete`: `docs/ableton_ui_teardown_template.md`
- `complete`: `docs/ableton_ui_validation_template.md`

### Baseline Notes

- `complete`: `docs/ableton_ui_baseline_audit.md`
- `in-progress`: `docs/ui_validation/week_00_baseline_repo_audit.md`

### Reference Teardowns

- `complete`: `docs/ableton_ui_teardown_eq_eight.md`
- `complete`: `docs/ableton_ui_teardown_spectrum.md`
- `complete`: `docs/ableton_ui_teardown_auto_filter.md`
- `complete`: `docs/ableton_ui_teardown_utility.md`
- `complete`: `docs/ableton_ui_teardown_glue_compressor.md`
- `complete`: `docs/ableton_ui_teardown_simpler.md`
- `complete`: `docs/ableton_ui_teardown_wavetable.md`
- `complete`: `docs/ableton_ui_teardown_echo.md`

### Reference Mapping

- `complete`: `docs/ableton_ui_reference_matrix.md`

### Planned Validation Notes

- `planned`: `docs/ui_validation/week_03_parametric_eq.md`
- `planned`: `docs/ui_validation/week_05_linear_phase_eq.md`
- `planned`: `docs/ui_validation/week_07_spectrum_analyzer.md`
- `planned`: `docs/ui_validation/week_09_ladder_filter.md`
- `planned`: `docs/ui_validation/week_11_framework_reaudit.md`

### Dual-Surface Work

- `complete`: `docs/dual_surface_shell_guidance.md`
- `complete`: `plugins/granular_sampler/ui_shell_spec.md`

## Next Repo Moves

1. Run the first real in-Live EQ validation and replace placeholder metadata in
   `docs/ui_validation/week_03_parametric_eq.md`.
2. Attach a current rubric score to `Parametric EQ` and `Linear Phase EQ` using
   `docs/ableton_ui_scoreboard.md`.
3. Keep the analyzer and ladder lanes unscored until they have enough visible
   UI to review honestly.
