#ifndef M4L_BUILDER_LIVE_BUNDLE_INSTANCE_H
#define M4L_BUILDER_LIVE_BUNDLE_INSTANCE_H

#include "bundle_abi.h"
#include "parameter_state.h"
#include <array>
#include <limits>
#include <stdexcept>

namespace m4l_builder::live_compat {

// Original instrument-bundle owner, not replacement DSP or device approval.
// Setup/destruction require a quiescent control thread. enqueueMidi/process and
// applyParameterChanges
// share ONE serialized processing owner; UI threads need an external queue.
// The caller must retain the original module's code until destruction finishes.
// Actual original callback allocation/locking needs its own runtime audit.
class BundleInstance {
public:
    BundleInstance(const BundleAPI& api, const ParameterValue* values,
                   std::size_t count, std::size_t expectedParameterCount,
                   std::int64_t sampleRate)
        : api_(api), renderAPI_(api) {
        if (!api_.create || !api_.destroy || !api_.setSampleRate ||
            !api_.getInfo || !api_.calc || !api_.setParameter || !api_.reset)
            throw std::invalid_argument("Incomplete original bundle API");
        if (sampleRate < 8000 || sampleRate > 192000)
            throw std::invalid_argument("Original bundle sample rate is outside the host contract");
        if (validateParameterState(values, count, expectedParameterCount) != ParameterStateStatus::ok)
            throw std::invalid_argument("Original bundle requires a complete finite parameter bank");

        // Own the complete validated bank before any foreign callback. Preserve
        // setter order and retain the immutable supplied values by native index;
        // these values are not claimed to be original getter readbacks.
        std::array<ParameterValue, maximumParameterStateSize> setup{};
        for (std::size_t i = 0; i < count; ++i) {
            setup[i] = values[i];
            initialValues_[static_cast<std::size_t>(values[i].index)] = values[i].value;
        }
        parameterCount_ = expectedParameterCount;
        renderAPI_.calc = &callOriginal;
        OriginalFPEnvironment environment;
        try {
            instance_ = api_.create();
            if (!instance_) throw std::runtime_error("Original bundle creation returned null");
            if (applyParameterState(api_.setParameter, instance_, setup.data(), count,
                                    expectedParameterCount) != ParameterStateStatus::ok)
                throw std::runtime_error("Original bundle parameter initialization failed");
            // Observed SetSampleRateU: zero rejects; CalcA has DIFFERENT status
            // semantics and normal zero must never become a processing failure.
            if (!api_.setSampleRate(instance_, sampleRate))
                throw std::runtime_error("Original bundle sample-rate initialization failed");
            api_.reset(instance_);
        } catch (const std::exception&) {
            destroyOriginal();
            throw;
        } catch (...) {
            destroyOriginal();
            throw std::runtime_error("Original bundle initialization threw a non-standard exception");
        }
    }

    ~BundleInstance() noexcept { destroyOriginal(); }
    BundleInstance(const BundleInstance&) = delete;
    BundleInstance& operator=(const BundleInstance&) = delete;
    BundleInstance(BundleInstance&&) = delete;
    BundleInstance& operator=(BundleInstance&&) = delete;

    // One serialized processing owner, never the UI thread. The caller must
    // independently establish source domains and the original setter's realtime
    // safety. Validate/copy the ENTIRE ordered packet before calling foreign
    // code; coupled parameters cannot partially apply because a later input is
    // invalid. A throwing original setter faults this instance permanently.
    // parameterValue() still reports the immutable initialized bank, not a
    // mutable original getter. The host owns acknowledged current state.
    bool applyParameterChanges(const ParameterValue* values, std::size_t count) noexcept {
        if (faulted()) return false;
        if (!values || !count || count > parameterCount_)
            return fail("Invalid original bundle parameter packet");
        std::array<ParameterValue, maximumParameterStateSize> changes{};
        std::array<bool, maximumParameterStateSize> seen{};
        for (std::size_t i = 0; i < count; ++i) {
            const auto value = values[i];
            if (value.index < 0 || static_cast<std::size_t>(value.index) >= parameterCount_ ||
                !std::isfinite(value.value) || seen[static_cast<std::size_t>(value.index)])
                return fail("Invalid original bundle parameter index or value");
            seen[static_cast<std::size_t>(value.index)] = true;
            changes[i] = value;
        }
        OriginalFPEnvironment environment;
        try {
            for (std::size_t i = 0; i < count; ++i)
                api_.setParameter(instance_, changes[i].index, changes[i].value);
        } catch (...) {
            return fail("Original bundle parameter update threw an exception");
        }
        return true;
    }

    bool enqueueMidi(std::int64_t sampleOffset, std::uint8_t status,
                     std::uint8_t data1, std::uint8_t data2) noexcept {
        if (faulted()) return false;
        if (sampleOffset < 0 || sampleOffset >= maximumFrames ||
            status < 0x80 || status >= 0xf0 || data1 > 127 || data2 > 127)
            return fail("Invalid original bundle MIDI event");
        if (eventCount_ == events_.size())
            return fail("Original bundle MIDI queue overflow");
        // Stable insertion keeps simultaneous messages in caller order.
        std::size_t at = eventCount_;
        while (at && events_[at - 1].sampleOffset > sampleOffset) {
            events_[at] = events_[at - 1];
            --at;
        }
        events_[at] = MidiEvent{sampleOffset, status, data1, data2, {}};
        ++eventCount_;
        return true;
    }

    bool process(float* left, float* right, int frames, const TimeInfo& time) noexcept {
        if (faulted()) return false;
        if (!validOutputRange(left, right, frames))
            return fail("Invalid original bundle output buffers or frame count");

        // This registered boundary hosts instruments, not Corpus's distinct
        // effect ABI. Zeroed scratch also prevents stale partial instrument
        // outputs. Invalid input or output never partially publishes a block.
        prepareScratch(leftScratch_, frames);
        prepareScratch(rightScratch_, frames);
        const auto result = render(renderAPI_, this, frames, leftScratch_.data() + 1,
                                   rightScratch_.data() + 1, events_.data(),
                                   static_cast<std::int64_t>(eventCount_), time);
        if (result.status != RenderStatus::calledOriginal)
            return fail("Original bundle render input was rejected");
        if (faulted()) return false;
        if (!validGuards(leftScratch_, frames) || !validGuards(rightScratch_, frames))
            return fail("Original bundle output guard was overwritten");
        for (int i = 0; i < frames; ++i)
            if (!std::isfinite(leftScratch_[static_cast<std::size_t>(i) + 1]) ||
                !std::isfinite(rightScratch_[static_cast<std::size_t>(i) + 1]))
                return fail("Original bundle produced non-finite audio");
        for (int i = 0; i < frames; ++i) {
            left[i] = leftScratch_[static_cast<std::size_t>(i) + 1];
            right[i] = rightScratch_[static_cast<std::size_t>(i) + 1];
        }
        eventCount_ = 0;
        return true;
    }

    bool faulted() const noexcept { return faultReason_ != nullptr; }
    const char* faultReason() const noexcept { return faultReason_ ? faultReason_ : ""; }
    std::size_t parameterCount() const noexcept { return parameterCount_; }
    float parameterValue(std::size_t index) const noexcept {
        return index < parameterCount_ ? initialValues_[index] : std::numeric_limits<float>::quiet_NaN();
    }

private:
    static constexpr int maximumFrames = 512;
    static constexpr float guardValue = 12345.125f;
    using Scratch = std::array<float, maximumFrames + 2>;
    BundleAPI api_, renderAPI_;
    void* instance_ = nullptr;
    std::array<float, maximumParameterStateSize> initialValues_{};
    std::array<MidiEvent, 1024> events_{};
    Scratch leftScratch_{}, rightScratch_{};
    std::size_t parameterCount_ = 0, eventCount_ = 0;
    const char* faultReason_ = nullptr;

    bool fail(const char* reason) noexcept {
        if (!faultReason_) faultReason_ = reason;
        return false;
    }

    static bool validOutputRange(float* left, float* right, int frames) noexcept {
        if (!left || !right || frames < 1 || frames > maximumFrames) return false;
        const auto a = reinterpret_cast<std::uintptr_t>(left);
        const auto b = reinterpret_cast<std::uintptr_t>(right);
        const auto bytes = static_cast<std::uintptr_t>(frames) * sizeof(float);
        const auto maximum = std::numeric_limits<std::uintptr_t>::max();
        if (a % alignof(float) || b % alignof(float) || a > maximum - bytes || b > maximum - bytes)
            return false;
        return a + bytes <= b || b + bytes <= a;
    }

    static void prepareScratch(Scratch& scratch, int frames) noexcept {
        scratch.fill(guardValue);
        for (int i = 0; i < frames; ++i) scratch[static_cast<std::size_t>(i) + 1] = 0;
    }

    static bool validGuards(const Scratch& scratch, int frames) noexcept {
        if (scratch[0] != guardValue) return false;
        for (std::size_t i = static_cast<std::size_t>(frames) + 1; i < scratch.size(); ++i)
            if (scratch[i] != guardValue) return false;
        return true;
    }

    static std::int64_t callOriginal(void* opaque, std::int64_t frames,
                                    float* left, float* right, std::int64_t count,
                                    const MidiEvent* events, const TimeInfo* time,
                                    std::int32_t* activity) noexcept {
        auto& self = *static_cast<BundleInstance*>(opaque);
        try {
            return self.api_.calc(self.instance_, frames, left, right, count, events, time, activity);
        } catch (...) {
            // Existing render() is noexcept, so contain a foreign exception
            // before it crosses that boundary. Failure containment is not a
            // claim that a throwing foreign callback is realtime-safe.
            self.fail("Original bundle render threw an exception");
            return 0;
        }
    }

    void destroyOriginal() noexcept {
        if (!instance_) return;
        void* dying = instance_;
        instance_ = nullptr;
        OriginalFPEnvironment environment;
        try { api_.destroy(dying); }
        catch (...) { fail("Original bundle destructor threw an exception"); }
    }
};

} // namespace m4l_builder::live_compat
#endif
