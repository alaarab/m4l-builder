#include "live_compat/bundle_abi.h"
#include <array>
#include <cassert>
#include <limits>
using namespace m4l_builder::live_compat;
static int calls = 0;
static int64_t calc(void*, int64_t n, float* l, float* r, int64_t count,
                    const MidiEvent* events, const TimeInfo* time, int32_t* sleep) {
    ++calls;
    assert(count == 1 && events[0].sampleOffset == 17);
    assert(time->beat == -1.25 && time->tempo == 120. && *sleep == 1);
#if defined(__APPLE__) && defined(__aarch64__)
    uint64_t control, status;
    asm volatile("mrs %0, fpcr" : "=r"(control));
    asm volatile("mrs %0, fpsr" : "=r"(status));
    assert(control & (uint64_t(1) << 24));
    status |= 1;
    asm volatile("msr fpsr, %0" : : "r"(status) : "memory");
#endif
    for (int64_t i = 0; i < n; ++i) { l[i] = 0.25f; r[i] = -0.5f; }
    *sleep = 1;
    return 0;
}
int main() {
    BundleAPI api{}; api.calc = calc;
    std::array<float, 64> l{}, r{};
    int instance = 0;
    TimeInfo time{1, 0, -1.25, 120.};
    MidiEvent note{17, 0x90, 60, 100, {}};
#if defined(__APPLE__) && defined(__aarch64__)
    uint64_t controlBefore, statusBefore;
    asm volatile("mrs %0, fpcr" : "=r"(controlBefore));
    asm volatile("mrs %0, fpsr" : "=r"(statusBefore));
#endif
    auto result = render(api, &instance, 64, l.data(), r.data(), &note, 1, time);
#if defined(__APPLE__) && defined(__aarch64__)
    uint64_t controlAfter, statusAfter;
    asm volatile("mrs %0, fpcr" : "=r"(controlAfter));
    asm volatile("mrs %0, fpsr" : "=r"(statusAfter));
    assert(controlBefore == controlAfter && statusBefore == statusAfter);
#endif
    assert(result.status == RenderStatus::calledOriginal && result.originalStatus == 0);
    assert(result.originalSleepFlag == 1 && calls == 1 && l[63] == 0.25f && r[63] == -0.5f);
    auto rejected = [&](int64_t frames, const MidiEvent* events, int64_t count) {
        const auto value = render(api, &instance, frames, l.data(), r.data(), events, count, time);
        assert(value.status == RenderStatus::invalidArguments && calls == 1);
        assert(l[0] == 0.25f && r[0] == -0.5f);
    };
    rejected(0, &note, 1); rejected(513, &note, 1); rejected(64, nullptr, 1);
    rejected(64, &note, -1); rejected(64, &note, 1025);
    note.sampleOffset = 64; rejected(64, &note, 1);
    note.sampleOffset = -1; rejected(64, &note, 1);
    note.sampleOffset = 17; note.status = 0xf0; rejected(64, &note, 1);
    note.status = 0x90; note.data1 = 128; rejected(64, &note, 1);
    note.data1 = 60; note.data2 = 128; rejected(64, &note, 1);
    note.data2 = 100;
    const MidiEvent reversed[] = {{20, 0x90, 60, 100, {}}, {17, 0x80, 60, 0, {}}};
    rejected(64, reversed, 2);
    time.beat = std::numeric_limits<double>::quiet_NaN(); rejected(64, &note, 1);
    time.beat = -1.25; time.playing = 2; rejected(64, &note, 1);
    time.playing = 1; time.tempo = 0; rejected(64, &note, 1);
    time.tempo = -1; rejected(64, &note, 1);
    time.tempo = std::numeric_limits<double>::infinity(); rejected(64, &note, 1);
    time.tempo = 120.; time.field24 = std::numeric_limits<double>::quiet_NaN(); rejected(64, &note, 1);
    time.field24 = 0; time.field32 = std::numeric_limits<double>::infinity(); rejected(64, &note, 1);
    time.field32 = 0; time.flag40 = 2; rejected(64, &note, 1);
    return 0;
}
