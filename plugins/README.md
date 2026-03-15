# Plugins

This directory is now a transition mirror.

Canonical plugin development is moving to the separate private repo:

- `/Users/squidbot/Projects/Max4LivePlugins`

Current policy:

- `src/m4l_builder/`: reusable framework code
- `examples/`: lightweight examples and compatibility wrappers
- `plugins/`: temporary mirror while `m4l-builder` hands plugin ownership off
  to `Max4LivePlugins`

The wrappers in `examples/` now prefer the external `Max4LivePlugins` repo
first, then fall back to this local mirror if the external repo is unavailable.

For UI-focused flagship work inside this mirror, use the shared docs in
`docs/`:

- `docs/ableton_ui_playbook.md`
- `docs/ableton_ui_review_checklist.md`
- `docs/ableton_ui_90_day_sprint.md`
- `docs/dual_surface_shell_guidance.md`
