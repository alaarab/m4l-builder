#include "live_compat/bundle_instance.h"
#include <array>
#include <cassert>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <new>
#include <type_traits>
using namespace m4l_builder::live_compat;

static bool auditAllocations = false;
static std::size_t allocations = 0;
void* operator new(std::size_t bytes) {
    if (auditAllocations) ++allocations;
    if (void* value = std::malloc(bytes ? bytes : 1)) return value;
    throw std::bad_alloc();
}
void operator delete(void* value) noexcept { std::free(value); }
void* operator new[](std::size_t bytes) { return ::operator new(bytes); }
void operator delete[](void* value) noexcept { ::operator delete(value); }
void operator delete(void* value, std::size_t) noexcept { ::operator delete(value); }
void operator delete[](void* value, std::size_t) noexcept { ::operator delete(value); }

struct Engine { int marker = 1234; };
enum class Failure { none, createNull, createThrow, setterThrow, rateReject, rateThrow,
                     resetThrow, nonfinite, leadingGuard, trailingGuard, renderThrow, updateThrow };
struct Probe {
    int creates = 0, destroys = 0, setters = 0, rates = 0, resets = 0, renders = 0;
    int live = 0, orderCount = 0;
    std::array<int, 4096> order{};
    std::array<float, 1024> values{};
    std::array<MidiEvent, 1024> received{};
    std::int64_t eventCount = 0, rate = 0, result = 0;
    TimeInfo time{};
    Failure failure = Failure::none;
    ParameterValue* mutateSource = nullptr;
    bool destroyThrows = false;
} probe;

static void expectFP() {
#if defined(__APPLE__) && defined(__aarch64__)
    std::uint64_t control;
    asm volatile("mrs %0, fpcr" : "=r"(control));
    assert(control & (std::uint64_t(1) << 24));
    std::uint64_t status;
    asm volatile("mrs %0, fpsr" : "=r"(status));
    status |= 1;
    asm volatile("msr fpsr, %0" : : "r"(status) : "memory");
#endif
}
static void* create() {
    expectFP(); ++probe.creates; probe.order[probe.orderCount++] = -1;
    if (probe.mutateSource) probe.mutateSource[0].value = 999;
    if (probe.failure == Failure::createThrow) throw 7;
    if (probe.failure == Failure::createNull) return nullptr;
    ++probe.live; return new Engine;
}
static void destroy(void* object) {
    expectFP(); assert(static_cast<Engine*>(object)->marker == 1234);
    ++probe.destroys; --probe.live; delete static_cast<Engine*>(object);
    if (probe.destroyThrows) throw 9;
}
static void setParameter(void* object, std::int64_t index, float value) {
    expectFP(); assert(static_cast<Engine*>(object)->marker == 1234);
    ++probe.setters; probe.order[probe.orderCount++] = static_cast<int>(index);
    probe.values[static_cast<std::size_t>(index)] = value;
    if (probe.failure == Failure::setterThrow && probe.setters == 2) throw 8;
    if (probe.failure == Failure::updateThrow && probe.setters == 5) throw 13;
}
static std::int32_t setRate(void*, std::int64_t rate) {
    expectFP(); ++probe.rates; probe.rate = rate; probe.order[probe.orderCount++] = -2;
    if (probe.failure == Failure::rateThrow) throw 10;
    return probe.failure == Failure::rateReject ? 0 : 1;
}
static void reset(void*) {
    expectFP(); ++probe.resets; probe.order[probe.orderCount++] = -3;
    if (probe.failure == Failure::resetThrow) throw 11;
}
static std::int32_t info(std::int32_t, void*, std::int64_t) { return 1; }
static std::int64_t calc(void* object, std::int64_t frames, float* left, float* right,
                         std::int64_t count, const MidiEvent* events,
                         const TimeInfo* time, std::int32_t* activity) {
    expectFP(); assert(static_cast<Engine*>(object)->marker == 1234);
    ++probe.renders; probe.eventCount = count; probe.time = *time;
    assert(*activity == (count != 0));
    for (std::int64_t i = 0; i < count; ++i) {
        probe.received[static_cast<std::size_t>(i)] = events[i];
        if (i) assert(events[i - 1].sampleOffset <= events[i].sampleOffset);
        for (auto byte : events[i].reserved) assert(byte == 0);
    }
    for (std::int64_t i = 0; i < frames; ++i) {
        assert(left[i] == 0 && right[i] == 0);
        left[i] = 0.25f; right[i] = -0.5f;
    }
    switch (probe.failure) {
        case Failure::nonfinite: right[frames - 1] = std::numeric_limits<float>::infinity(); break;
        case Failure::leadingGuard: left[-1] = 0; break;
        case Failure::trailingGuard: right[frames] = 0; break;
        case Failure::renderThrow: throw 12;
        default: break;
    }
    *activity = 7;
    return probe.result;
}
static BundleAPI api() { return {create, destroy, setRate, info, calc, setParameter, reset}; }
static const ParameterValue bank[] = {{2, 0.75f}, {0, -0.5f}, {1, 0.125f}};
static const TimeInfo validTime{1, 0, -1.25, 127.5, 0.25, -0.5, 1, {}};
static void clear() { assert(probe.live == 0); probe = Probe{}; }
static void assertNoForeign() {
    assert(probe.creates == 0 && probe.destroys == 0 && probe.setters == 0 &&
           probe.rates == 0 && probe.resets == 0 && probe.renders == 0);
}
template<class Callback> static void invalidSetup(Callback callback) {
    clear(); bool rejected = false;
    try { callback(); } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected); assertNoForeign();
}
static void testSetupValidation() {
    for (int missing = 0; missing < 7; ++missing) {
        auto broken = api();
        switch (missing) {
            case 0: broken.create = nullptr; break;
            case 1: broken.destroy = nullptr; break;
            case 2: broken.setSampleRate = nullptr; break;
            case 3: broken.getInfo = nullptr; break;
            case 4: broken.calc = nullptr; break;
            case 5: broken.setParameter = nullptr; break;
            case 6: broken.reset = nullptr; break;
        }
        invalidSetup([&] { BundleInstance instance(broken, bank, 3, 3, 48000); });
    }
    invalidSetup([] { BundleInstance instance(api(), bank, 3, 3, 7999); });
    invalidSetup([] { BundleInstance instance(api(), bank, 3, 3, 192001); });
    invalidSetup([] { BundleInstance instance(api(), nullptr, 3, 3, 48000); });
    invalidSetup([] { BundleInstance instance(api(), bank, 2, 3, 48000); });
    invalidSetup([] { BundleInstance instance(api(), bank, 3, 0, 48000); });
    invalidSetup([] { BundleInstance instance(api(), bank, 3, 1025, 48000); });
    invalidSetup([] { BundleInstance instance(api(), bank, 1025, 3, 48000); });
    for (int defect = 0; defect < 4; ++defect) {
        std::array<ParameterValue, 3> invalid{{bank[0], bank[1], bank[2]}};
        if (defect == 0) invalid[2].index = 0;
        if (defect == 1) invalid[2].index = -1;
        if (defect == 2) invalid[2].index = 3;
        if (defect == 3) invalid[2].value = std::numeric_limits<float>::quiet_NaN();
        invalidSetup([&] { BundleInstance instance(api(), invalid.data(), invalid.size(), 3, 48000); });
    }
}
static void testSetupOrderOwnershipAndCleanup() {
    clear();
    auto suppliedAPI = api();
    std::array<ParameterValue, 3> source{{bank[0], bank[1], bank[2]}};
    probe.mutateSource = source.data();
    {
        BundleInstance instance(suppliedAPI, source.data(), source.size(), 3, 48000);
        suppliedAPI.calc = nullptr;
        assert(source[0].value == 999 && instance.parameterCount() == 3);
        assert(instance.parameterValue(0) == -0.5f && instance.parameterValue(1) == 0.125f &&
               instance.parameterValue(2) == 0.75f && std::isnan(instance.parameterValue(3)));
        assert(!instance.faulted() && !*instance.faultReason());
        assert(probe.values[2] == 0.75f);
        const int expected[] = {-1, 2, 0, 1, -2, -3};
        assert(probe.orderCount == 6 && probe.rate == 48000);
        for (int i = 0; i < 6; ++i) assert(probe.order[i] == expected[i]);
        std::array<float, 64> left{}, right{};
        assert(instance.process(left.data(), right.data(), 64, validTime));
    }
    assert(probe.destroys == 1 && probe.live == 0);
    for (auto failure : {Failure::createNull, Failure::createThrow, Failure::setterThrow,
                         Failure::rateReject, Failure::rateThrow, Failure::resetThrow}) {
        clear(); probe.failure = failure;
        bool rejected = false;
        try { BundleInstance instance(api(), bank, 3, 3, 48000); }
        catch (const std::runtime_error&) { rejected = true; }
        assert(rejected && probe.creates == 1 && probe.live == 0);
        const bool created = failure != Failure::createNull && failure != Failure::createThrow;
        assert(probe.destroys == int(created));
    }
    clear(); probe.failure = Failure::rateReject; probe.destroyThrows = true;
    bool rejected = false;
    try { BundleInstance instance(api(), bank, 3, 3, 48000); }
    catch (const std::runtime_error&) { rejected = true; }
    assert(rejected && probe.destroys == 1 && probe.live == 0);
    clear(); probe.destroyThrows = true;
    { BundleInstance instance(api(), bank, 3, 3, 48000); }
    assert(probe.destroys == 1 && probe.live == 0);
    clear();
    std::array<ParameterValue, maximumParameterStateSize> full{};
    for (std::size_t i = 0; i < full.size(); ++i)
        full[i] = {static_cast<std::int64_t>(full.size() - 1 - i), static_cast<float>(i)};
    {
        BundleInstance instance(api(), full.data(), full.size(), full.size(), 192000);
        assert(instance.parameterCount() == 1024 && probe.setters == 1024);
        assert(instance.parameterValue(0) == 1023);
    }
    clear(); { BundleInstance instance(api(), bank, 3, 3, 8000); }
}
static void testMidiAndOriginalStatus() {
    clear();
    BundleInstance instance(api(), bank, 3, 3, 48000);
    std::array<float, 514> left{}, right{};
    left.fill(91); right.fill(92);
    assert(instance.enqueueMidi(63, 0x82, 60, 31));
    assert(instance.enqueueMidi(0, 0x92, 60, 100));
    assert(instance.enqueueMidi(17, 0xe2, 1, 65));
    assert(instance.enqueueMidi(17, 0xb2, 64, 127));
    assert(instance.process(left.data(), right.data(), 64, validTime));
    assert(probe.eventCount == 4 && probe.received[0].status == 0x92);
    assert(probe.received[1].sampleOffset == 17 && probe.received[1].status == 0xe2);
    assert(probe.received[2].status == 0xb2 && probe.received[3].sampleOffset == 63);
    assert(probe.received[3].data2 == 31);
    assert(probe.time.beat == validTime.beat && probe.time.tempo == validTime.tempo &&
           probe.time.field24 == validTime.field24 && probe.time.field32 == validTime.field32 &&
           probe.time.flag40 == 1);
    assert(left[63] == 0.25f && right[63] == -0.5f && left[64] == 91 && right[64] == 92);
    for (auto status : {std::int64_t(0), std::int64_t(1), std::int64_t(-1),
                        std::numeric_limits<std::int64_t>::min()}) {
        probe.result = status;
        assert(instance.process(left.data(), right.data(), 1, validTime));
        assert(probe.eventCount == 0 && !instance.faulted());
    }
    assert(instance.enqueueMidi(511, 0x9f, 127, 127));
    assert(instance.process(left.data(), right.data(), 512, validTime));
    assert(probe.received[0].sampleOffset == 511 && probe.received[0].status == 0x9f);
}
static void testRejectedProcessAndStickyFaults() {
    for (int defect = 0; defect < 15; ++defect) {
        clear();
        BundleInstance instance(api(), bank, 3, 3, 48000);
        std::array<float, 1024> left{}, right{};
        left.fill(91); right.fill(92);
        auto* l = left.data(); auto* r = right.data(); int frames = 64;
        auto time = validTime;
        switch (defect) {
            case 0: l = nullptr; break;
            case 1: r = nullptr; break;
            case 2: r = l; break;
            case 3: r = l + 1; break;
            case 4: frames = 0; break;
            case 5: frames = 513; break;
            case 6: time.playing = 2; break;
            case 7: time.beat = std::numeric_limits<double>::infinity(); break;
            case 8: time.tempo = 0; break;
            case 9: time.tempo = std::numeric_limits<double>::quiet_NaN(); break;
            case 10: time.field24 = std::numeric_limits<double>::quiet_NaN(); break;
            case 11: time.field32 = std::numeric_limits<double>::infinity(); break;
            case 12: time.flag40 = 2; break;
            case 13: assert(instance.enqueueMidi(64, 0x90, 60, 100)); break;
            case 14: l = reinterpret_cast<float*>(reinterpret_cast<unsigned char*>(l) + 1); break;
        }
        assert(!instance.process(l, r, frames, time) && instance.faulted() && *instance.faultReason());
        const char* reason = instance.faultReason();
        assert(probe.renders == 0);
        assert(!instance.process(left.data(), right.data(), 64, validTime));
        assert(!instance.enqueueMidi(0, 0x90, 60, 100));
        assert(reason == instance.faultReason() && probe.renders == 0);
        for (auto value : left) assert(value == 91);
        for (auto value : right) assert(value == 92);
    }
    for (int defect = 0; defect < 6; ++defect) {
        clear(); BundleInstance instance(api(), bank, 3, 3, 48000);
        const bool accepted = defect == 0 ? instance.enqueueMidi(-1, 0x90, 60, 100) :
            defect == 1 ? instance.enqueueMidi(512, 0x90, 60, 100) :
            defect == 2 ? instance.enqueueMidi(0, 0x70, 60, 100) :
            defect == 3 ? instance.enqueueMidi(0, 0xf0, 60, 100) :
            defect == 4 ? instance.enqueueMidi(0, 0x90, 128, 100) :
                          instance.enqueueMidi(0, 0x90, 60, 128);
        assert(!accepted && instance.faulted() && probe.renders == 0);
    }
    clear();
    {
        BundleInstance instance(api(), bank, 3, 3, 48000);
        for (int i = 0; i < 1024; ++i) assert(instance.enqueueMidi(i % 64, 0x90, 60, 100));
        std::array<float, 64> left{}, right{};
        assert(instance.process(left.data(), right.data(), 64, validTime) && probe.eventCount == 1024);
    }
    clear();
    {
        BundleInstance instance(api(), bank, 3, 3, 48000);
        for (int i = 0; i < 1024; ++i) assert(instance.enqueueMidi(0, 0x90, 60, 100));
        assert(!instance.enqueueMidi(0, 0x90, 60, 100));
        std::array<float, 64> left{}, right{}; left.fill(91); right.fill(92);
        assert(!instance.process(left.data(), right.data(), 64, validTime) && probe.renders == 0);
        for (auto value : left) assert(value == 91);
        for (auto value : right) assert(value == 92);
    }
}
static void testOriginalOutputFailureContainment() {
    for (auto failure : {Failure::nonfinite, Failure::leadingGuard, Failure::trailingGuard, Failure::renderThrow}) {
        clear();
        BundleInstance instance(api(), bank, 3, 3, 48000);
        probe.failure = failure;
        std::array<float, 64> left{}, right{}; left.fill(91); right.fill(92);
        assert(!instance.process(left.data(), right.data(), 64, validTime));
        assert(instance.faulted() && *instance.faultReason() && probe.renders == 1);
        for (auto value : left) assert(value == 91);
        for (auto value : right) assert(value == 92);
        assert(!instance.process(left.data(), right.data(), 64, validTime) && probe.renders == 1);
    }
}
static void testProcessingAllocationsAndFP() {
    clear();
    BundleInstance instance(api(), bank, 3, 3, 48000);
    std::array<float, 512> left{}, right{};
    auto volatile allocate = static_cast<void* (*)(std::size_t)>(&::operator new);
    auditAllocations = true;
    void* positive = allocate(32); ::operator delete(positive);
    auditAllocations = false;
    assert(allocations > 0);
    const auto before = allocations;
#if defined(__APPLE__) && defined(__aarch64__)
    std::uint64_t controlBefore, statusBefore, controlAfter, statusAfter;
    asm volatile("mrs %0, fpcr" : "=r"(controlBefore));
    asm volatile("mrs %0, fpsr" : "=r"(statusBefore));
#endif
    auditAllocations = true;
    for (int block = 0; block < 1000; ++block) {
        // Exact dyadic inputs keep the test's own arithmetic from setting FPSR.
        const ParameterValue changes[]={{2,float(block)/1024},{0,-.25f}};
        assert(instance.applyParameterChanges(changes,2));
        assert(instance.enqueueMidi(17, block % 2 ? 0x80 : 0x90, 60, 100));
        assert(instance.enqueueMidi(0, 0xb0, 1, 64));
        assert(instance.process(left.data(), right.data(), 512, validTime));
    }
    auditAllocations = false;
    assert(allocations == before && probe.renders == 1000);
#if defined(__APPLE__) && defined(__aarch64__)
    asm volatile("mrs %0, fpcr" : "=r"(controlAfter));
    asm volatile("mrs %0, fpsr" : "=r"(statusAfter));
    assert(controlBefore == controlAfter && statusBefore == statusAfter);
#endif
}
static void testParameterPackets() {
    for(int defect=0;defect<6;++defect) {
        clear();BundleInstance instance(api(),bank,3,3,48000);
        ParameterValue changes[]={{2,.5f},{0,.75f}};const ParameterValue* values=changes;size_t count=2;
        if(defect==0)values=nullptr;
        if(defect==1)count=0;
        if(defect==2)count=4;
        if(defect==3)changes[1].index=3;
        if(defect==4)changes[1].index=2;
        if(defect==5)changes[1].value=std::numeric_limits<float>::quiet_NaN();
        assert(!instance.applyParameterChanges(values,count));assert(instance.faulted());
        assert(probe.setters==3 && probe.values[2]==.75f && probe.values[0]==-.5f);
        assert(!instance.applyParameterChanges(bank,3) && probe.setters==3);
    }
    clear();
    {
        BundleInstance instance(api(),bank,3,3,48000);
        const ParameterValue changes[]={{2,.5f},{0,.75f}};
        assert(instance.applyParameterChanges(changes,2));
        assert(probe.setters==5 && probe.order[6]==2 && probe.order[7]==0);
        assert(probe.values[2]==.5f && probe.values[0]==.75f);
        assert(instance.parameterValue(2)==.75f && instance.parameterValue(0)==-.5f);
    }
    clear();
    {
        BundleInstance instance(api(),bank,3,3,48000);probe.failure=Failure::updateThrow;
        const ParameterValue changes[]={{2,.5f},{0,.75f}};
        assert(!instance.applyParameterChanges(changes,2));assert(instance.faulted());
        assert(probe.setters==5 && std::strstr(instance.faultReason(),"parameter update"));
        std::array<float,64> left{},right{};
        assert(!instance.process(left.data(),right.data(),64,validTime));assert(probe.renders==0);
    }
}
int main() {
    static_assert(!std::is_copy_constructible_v<BundleInstance>);
    static_assert(!std::is_move_constructible_v<BundleInstance>);
    static_assert(noexcept(std::declval<BundleInstance&>().enqueueMidi(0, 0x90, 60, 100)));
    static_assert(noexcept(std::declval<BundleInstance&>().process(nullptr, nullptr, 64, validTime)));
    static_assert(noexcept(std::declval<BundleInstance&>().applyParameterChanges(nullptr,0)));
    testSetupValidation();
    testSetupOrderOwnershipAndCleanup();
    testMidiAndOriginalStatus();
    testRejectedProcessAndStickyFaults();
    testOriginalOutputFailureContainment();
    testProcessingAllocationsAndFP();
    testParameterPackets();
    assert(probe.live == 0);
    std::puts("{\"passed\":true,\"synthetic_callbacks_only\":true,\"steady_render_blocks\":1000,\"observed_cpp_callback_allocations\":0,\"original_device_parity\":false}");
}
