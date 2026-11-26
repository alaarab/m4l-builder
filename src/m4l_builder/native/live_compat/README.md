# Original Live bundle boundary

`bundle_abi.h` describes the observed LP64 ARM64 C interface of the original
Analog-family bundles shipped in Live's `App-Resources/Devices/Mac` directory.
It contains no original binary bytes and no replacement synthesis code.

Creation, destruction, loading, sample-rate changes and parameter setup belong
off the audio callback. `render` validates bounded, ordered sample-offset MIDI
and buffers before calling the original `CalcA`. Invalid input returns an explicit
error without altering audio or invoking the plugin. An original zero status is
not treated as a failed render. The original callback still needs allocation and
locking audits; a small host wrapper does not prove callback safety.

The two transport doubles retain neutral field-offset names until their original
Live semantic mapping is established. Parameter indices, units, defaults and
Live state bindings are also separate device-specific evidence. Do not infer
full device compatibility from seven matching export names or a constructor.

Separate, private bundle probes exercise the installed binaries and retain
original-versus-Simulator audio, metadata and real-time observations.
Those probes must verify compatible entry-point code/ABI before adding another
bundle. This boundary does not register any device as ready in the app and does
not establish physical-phone operation, the complete Live wrapper or ALS parity.

## Observed Live transport boundary

The current boundary supersedes the initial unnamed two-double timing fixture.
Original Live forwards a 48-byte record: playing at 0, beat at 8 and BPM at 16;
the remaining two doubles and byte have deliberately unregistered semantics.
The audited four AAS instrument entry points consume the first 24 bytes.
Invalid/nonfinite timing is rejected before calling original code, while
negative beat positions are valid.

On Apple ARM64, the callback runs with Live's observed flush-to-zero setting
and restores the caller's FPCR/FPSR afterward. The original instrument caller
initializes activity from the presence of MIDI; this is not registration of
Corpus's distinct effect interface. Portable fake-callback tests do not
authorize original bundle loading on other architectures.

A separate original clock oracle verifies beat/BPM arithmetic against pinned
original Analog instructions on macOS and Simulator. Complete transport, preset
and device fidelity are not implied. Shared ABI tests and zero observed render
allocation/lock events cannot override failed original-device checks.
