# Original selector~ reference

Captured from the installed Max 9 ARM64 selector~ external on 2026-09-10 in
isolated silent patches. Source patches, original module disassembly, capture
configuration, completion witnesses and restore readbacks are retained under
`~/.phren/objectstudio/reference/all68-runtime-20260910/`.

ObjectStudio's `tools/collect_selector_reference.py` regenerates this fixture
and `Tests/Fixtures/Original Selector Max.fixture` from the same 10 certified
captures. It excludes the explicitly marked overlapping exploratory captures.

40 cases cover 20,480 stereo samples: normal and stepped signal selection,
half-millisecond independent ramps, interruptions, mute, negative/fractional/
out-of-range selections, constructor initialization, next, and the no-argument
default at actual 44.1, 48 and 96 kHz. The 44.1 kHz cases match exactly. Across
all rates, seven near-zero cancellation results differ by at most 4.86e-16;
the comparison tolerance is 1e-14. Both stereo channels must agree, and the
native test checks zero allocations during dispatch/render.

This is object-level evidence, not complete AMXD compatibility. Live lifecycle,
DSP restart, host scheduling and arbitrary connected objects remain separate
obligations. Selector ports above 63 remain rejected by the prepared runtime's
current 64-inlet budget.
