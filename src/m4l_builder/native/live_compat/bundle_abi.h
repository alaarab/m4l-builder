#ifndef M4L_BUILDER_LIVE_BUNDLE_ABI_H
#define M4L_BUILDER_LIVE_BUNDLE_ABI_H

// Experimental, observed Apple ARM64 LP64 ABI for original Live AAS bundles.
// This is a host boundary, not replacement DSP or a complete Live device.
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace m4l_builder::live_compat {

struct MidiEvent {
    int64_t sampleOffset;
    uint8_t status, data1, data2;
    uint8_t reserved[5];
};
struct TimeInfo {
    int32_t playing;
    int32_t reserved;
    // Live OThirdPartyDeviceProcessor::UpdateTimeInfo forwards these unchanged
    // to CalcA. Analog's original clock advances beat + tempo*frames/(60*rate).
    double beat, tempo;
    // Live also supplies this tail. The four audited AAS instrument entry
    // points consume only the first 24 bytes; tail semantics remain unregistered.
    double field24 = 0, field32 = 0;
    uint8_t flag40 = 0;
    uint8_t reserved41[7]{};
};
static_assert(sizeof(MidiEvent) == 16 && offsetof(MidiEvent, status) == 8);
static_assert(sizeof(TimeInfo) == 48 && offsetof(TimeInfo, beat) == 8);
static_assert(offsetof(TimeInfo, tempo) == 16 && offsetof(TimeInfo, field24) == 24);
static_assert(offsetof(TimeInfo, field32) == 32 && offsetof(TimeInfo, flag40) == 40);

// The observed Live ARM64 call boundary enables flush-to-zero and restores
// both control and exception-status registers afterward. Never change the
// caller's floating-point environment permanently. No libc/TLS calls here.
class OriginalFPEnvironment {
#if defined(__APPLE__) && defined(__aarch64__)
    uint64_t control_, status_;
#endif
public:
    OriginalFPEnvironment() noexcept {
#if defined(__APPLE__) && defined(__aarch64__)
        asm volatile("mrs %0, fpcr" : "=r"(control_));
        asm volatile("mrs %0, fpsr" : "=r"(status_));
        const uint64_t flushing = control_ | (uint64_t(1) << 24);
        asm volatile("msr fpcr, %0" : : "r"(flushing) : "memory");
#endif
    }
    ~OriginalFPEnvironment() noexcept {
#if defined(__APPLE__) && defined(__aarch64__)
        asm volatile("msr fpcr, %0" : : "r"(control_) : "memory");
        asm volatile("msr fpsr, %0" : : "r"(status_) : "memory");
#endif
    }
    OriginalFPEnvironment(const OriginalFPEnvironment&) = delete;
    OriginalFPEnvironment& operator=(const OriginalFPEnvironment&) = delete;
};

struct BundleAPI {
    void* (*create)();
    void (*destroy)(void*);
    int32_t (*setSampleRate)(void*, int64_t);
    int32_t (*getInfo)(int32_t, void*, int64_t);
    int64_t (*calc)(void*, int64_t, float*, float*, int64_t,
                    const MidiEvent*, const TimeInfo*, int32_t*);
    void (*setParameter)(void*, int64_t, float);
    void (*reset)(void*);
};

enum class RenderStatus { calledOriginal, invalidArguments };
struct RenderResult {
    RenderStatus status;
    int64_t originalStatus;
    int32_t originalSleepFlag;
};

// No allocations, locks, file access or logging in this boundary. Whether the
// ORIGINAL callback obeys those constraints requires a separate runtime audit.
inline RenderResult render(const BundleAPI& api, void* instance, int64_t frames,
                           float* left, float* right, const MidiEvent* events,
                           int64_t eventCount, const TimeInfo& time) noexcept {
    if (!api.calc || !instance || !left || !right || left == right || frames < 1 || frames > 512 ||
        eventCount < 0 || eventCount > 1024 || (eventCount && !events) ||
        (time.playing != 0 && time.playing != 1) || !std::isfinite(time.beat) ||
        !std::isfinite(time.tempo) || time.tempo <= 0 || !std::isfinite(time.field24) ||
        !std::isfinite(time.field32) || time.flag40 > 1) return {RenderStatus::invalidArguments, 0, 0};
    int64_t previous = -1;
    for (int64_t i = 0; i < eventCount; ++i) {
        const auto& event = events[i];
        // Only bounded MIDI 1 channel messages are registered by this adapter.
        // SysEx, clock and other message families are not silently truncated.
        if (event.sampleOffset < previous || event.sampleOffset < 0 || event.sampleOffset >= frames ||
            event.status < 0x80 || event.status >= 0xf0 || event.data1 > 127 || event.data2 > 127)
            return {RenderStatus::invalidArguments, 0, 0};
        previous = event.sampleOffset;
    }
    // Live's instrument caller initializes the in/out activity flag from the
    // presence of MIDI. Corpus's distinct stateful effect ABI is not registered.
    int32_t sleep = eventCount != 0;
    OriginalFPEnvironment environment;
    const auto status = api.calc(instance, frames, left, right, eventCount, events, &time, &sleep);
    // CalcA's zero/nonzero result is an original processing-status flag, NOT
    // a success boolean. Never turn normal zero into bypass or an error.
    return {RenderStatus::calledOriginal, status, sleep};
}

} // namespace m4l_builder::live_compat
#endif
