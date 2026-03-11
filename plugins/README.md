# Plugins

This directory is now a transition mirror.

Canonical plugin development is moving to the separate private repo:

- `~/Projects/the device repo`

Current policy:

- `src/m4l_builder/`: reusable framework code
- `examples/`: lightweight examples and compatibility wrappers
- `plugins/`: temporary mirror while `m4l-builder` hands plugin ownership off
  to `the device repo`

The wrappers in `examples/` now prefer the external `the device repo` repo
first, then fall back to this local mirror if the external repo is unavailable.
