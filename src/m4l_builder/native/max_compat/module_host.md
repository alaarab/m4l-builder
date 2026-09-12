# Original Max-module probe host

Named consumer: Object Studio's `Native/DrumCellHost` desktop probe. Shared
implementation lives here, not in an app-local DSP fork. This code is not linked
into the iOS app and does not implement the full Max runtime.

## Scope

- LP64 public Max object, MSP object, atom and method ABI.
- Original scalar/array attribute callback dispatch, typed fallback storage,
  bounds checks, clip filters and constructor attribute arguments.
- Fixed-capacity deferred queue; control-thread `defer` is immediate.
- A single offline DSP registration and immutable named sample buffers.
- Original module callsite-derived scheduler offset validity/out-parameter ABI.
- Explicit supported common-symbol slots; the remaining table is null.

The adapter must compile DSP before rebinding the sample and capture the first
triggered block. Do not write private device state to force initialization.
No installed binary, original preset, sample or existing AMXD is modified.

## Limits

This remains a single-instance, process-lifetime research host. Class metadata
presentation attributes, full common symbols, patcher context, dynamic buffers,
all scheduling/thread semantics and many Max APIs are incomplete. Unsupported
method calls and bounded deferred-queue overflow increment a diagnostic counter;
missing imports still fail loading. Symbol coverage alone is NOT hostability.

The original DSP may still perform operations forbidden on a phone audio thread.
A successful desktop capture is neither proof of real-time safety nor permission
to enable stock devices in Object Studio. Full native-device controls/state,
sound equivalence, racks, standalone physical-phone processing and ALS reopening
in Live remain separate acceptance requirements.

## Checks and sources

`uv run pytest tests/test_native_module_host.py -q` exercises public host
contracts with a synthetic object, not Ableton-device sound.

Public ABI references:
- https://github.com/Cycling74/max-sdk-base/blob/main/c74support/max-includes/ext_mess.h
- https://github.com/Cycling74/max-sdk-base/blob/main/c74support/max-includes/ext_obex.h
- https://github.com/Cycling74/max-sdk-base/blob/main/c74support/max-includes/max_types.h
- https://github.com/Cycling74/max-sdk-base/blob/main/c74support/msp-includes/z_dsp.h
- https://github.com/Cycling74/max-sdk-base/blob/main/c74support/max-includes/commonsyms.h

Supported common-symbol indices were generated from the SDK on 2026-09-11.
See `MAX_SDK_LICENSE.md`. SDK layout compatibility does not prove every installed
module uses the same private class or data layout.

## Independent contexts and Simulator consumer

Object Studio now uses `module_host.h` in its six-original-instance Simulator
probe. `host_call_dsp64` builds an ordered callback list for each original root;
`host_get_perform_context` obtains its stable control-thread handle, and
`host_run_context` dispatches directly without registry lookup. Recompilation
replaces the callback list. Object destruction retires its context and cancels
its own deferred work. Consumers must stop dispatch before recompiling/freeing;
a freed context cannot be used. Calls remain serialized on one host thread.
The old `host_run_perform` helper addresses only the last compiled context and
exists for the original single-instance diagnostic loader.

Original Drum Cell executes with this host on arm64 iOS Simulator. This is not
real-time safety: an interposed six-instance workload observes allocations,
frees and locks in both original rendering and MIDI delivery. Integration must
keep that work off the audio callback; do not enable devices from these probes.
Exact evidence and the original code/data provenance receipt are under
`~/.phren/objectstudio/reference/drumcell-ios-20260911-oWmlug/`.

## Original stock-module probe extension (2026-09-11)

`host_compile_dsp64` accepts explicit inlet-then-outlet connection flags and
checks them against signal ports registered through `z_dsp_setup`/`outlet_new`.
Audio, sidechain, control and envelope ports must not be conflated. Original
registered attribute/method names, typed scalar readback and whole-package
fileusage collection are available to the generic private probe. `str_tr` uses
the public SDK's untranslated-label behavior. `fileusage_addpackage` implements
standalone dependency reporting, not package loading; nonnull subfolder atomarrays
and unknown collector handles are explicitly unsupported.

Fixed the exact MSP ABI: `float sys_getsr(void)`, not double. The wrong return
register contents corrupted original constructors, hidden at 48 kHz by processor
recreation. The original Auto Filter constructor's `fcvt d0, s0` after this call
and Cycling74's public `z_dsp.h` establish the signature. New native regressions
cover this type, 44.1/48 kHz values, effect connection flags, unchanged independent
contexts and package-report behavior. Full `make check` passes.

Object Studio's private probes now execute original Auto Filter, mono Compressor
plus envelope, Saturator DSP and Drift at 44.1/48 kHz. Effect-module platform
captures match exactly; Drift inter-process variation remains unverified. These
are not complete stock devices or a physical-phone/runtime integration. All
host operations remain serialized. Probe render observations do not authorize
calling locking MIDI methods or allocating Drum Cell processing on an audio
callback. The source-backed audit must actually intercept nonzero render calls.
