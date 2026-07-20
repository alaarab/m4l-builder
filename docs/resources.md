# Resources

Curated, authoritative sources for the technologies `m4l-builder` sits on top of. If a Max object, attribute, or behavior in these docs is unclear, the primary references below are the source of truth.

## Official — Max & Max for Live

| Source | What it's for |
|--------|---------------|
| [Cycling '74 — Max documentation](https://docs.cycling74.com/) | The canonical reference for every Max/MSP object, attribute, and message. When this site says an object takes a given inlet or attribute, that page is the authority. |
| [Cycling '74](https://cycling74.com/) | Makers of Max. Articles, forums, and the Max download. |
| [Ableton — Max for Live](https://www.ableton.com/en/live/max-for-live/) | Overview of Max for Live: what it is and how devices load into Live. |
| [Ableton — Live manual](https://www.ableton.com/en/manual/) | The Live reference manual, including the Max for Live chapter (device formats, the User Library, freezing). |

!!! note "Object reference"
    The [DSP & UI catalog](catalog.md) lists the building blocks this library ships. For the underlying Max objects each block wires together (`biquad~`, `live.dial`, `plugin~`, etc.), search the [Cycling '74 docs](https://docs.cycling74.com/).

## Learning Max, MSP & DSP

| Source | What it's for |
|--------|---------------|
| [Cycling '74 — Max documentation](https://docs.cycling74.com/) | Includes the "Max", "MSP", and "Jitter" tutorials — start here to learn the patching model itself. |
| [Julius O. Smith — online DSP books (CCRMA, Stanford)](https://ccrma.stanford.edu/~jos/) | The standard free references for digital filters, physical modeling, and spectral audio processing — useful when you want to understand *why* a DSP block is wired the way it is. |
| [musicdsp.org](https://www.musicdsp.org/) | A long-running archive of audio DSP algorithms and code snippets. |

## This project

| Source | What it's for |
|--------|---------------|
| [GitHub — alaarab/m4l-builder](https://github.com/alaarab/m4l-builder) | Source, issues, and the example scripts under `examples/`. |
| [PyPI — m4l-builder](https://pypi.org/project/m4l-builder/) | Released versions; `pip install m4l-builder`. |
| [API reference](api.md) | Every public class and function in the library. |
| [Reverse engineering](reverse_engineering.md) | Read an existing `.amxd` back into Python with `from_amxd`. |
| [LiveMCP bridge](livemcp_max_bridge.md) | Drive a built device live in Ableton from an MCP client. |

## File format background

A `.amxd` is a small binary header followed by a Max patcher (`.maxpat`) JSON document. `m4l-builder` constructs that JSON — boxes (objects), lines (patch cords), and presentation-mode rectangles — and writes the wrapper. You don't edit the format by hand; the [API reference](api.md) and [Getting started](getting_started.md) cover the Python surface, and [Reverse engineering](reverse_engineering.md) shows the round trip back from an existing device.
