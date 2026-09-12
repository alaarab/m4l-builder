#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace m4l_builder::live_compat {

// Control/setup-thread transport only. This does not deserialize an ALS/ADV,
// recreate an engine, or establish any complete-device compatibility.
struct ParameterValue {
    std::int64_t index;
    float value;
};

inline constexpr std::size_t maximumParameterStateSize = 1024;

enum class ParameterStateStatus {
    ok,
    invalidParameterCount,
    incompleteState,
    missingStorage,
    invalidIndex,
    duplicateIndex,
    nonFiniteValue,
    missingInstance,
    missingSetter,
};

// A complete initialization bank must cover every index exactly once. Check
// the entire bank before invoking foreign code or changing any engine state.
// Per-parameter ranges and conversions must come from a separately verified
// original model; they cannot be inferred from this structural validation.
inline ParameterStateStatus validateParameterState(
    const ParameterValue* values,
    std::size_t count,
    std::size_t expectedParameterCount) noexcept {
    if (expectedParameterCount == 0 ||
        expectedParameterCount > maximumParameterStateSize ||
        count > maximumParameterStateSize) {
        return ParameterStateStatus::invalidParameterCount;
    }
    if (count != expectedParameterCount) {
        return ParameterStateStatus::incompleteState;
    }
    if (!values) {
        return ParameterStateStatus::missingStorage;
    }
    std::array<bool, maximumParameterStateSize> seen{};
    for (std::size_t i = 0; i < count; ++i) {
        const auto& parameter = values[i];
        if (parameter.index < 0 ||
            static_cast<std::uint64_t>(parameter.index) >= expectedParameterCount) {
            return ParameterStateStatus::invalidIndex;
        }
        if (!std::isfinite(parameter.value)) {
            return ParameterStateStatus::nonFiniteValue;
        }
        const auto index = static_cast<std::size_t>(parameter.index);
        if (seen[index]) {
            return ParameterStateStatus::duplicateIndex;
        }
        seen[index] = true;
    }
    return ParameterStateStatus::ok;
}

using ParameterSetter = void (*)(void*, std::int64_t, float);

// Call only on the control/setup thread with a quiescent engine and immutable
// input storage, before its sample-rate/reset initialization. Original setters
// may allocate. Validation rejection makes no setter calls. The original void
// ABI has no error return or rollback; foreign exceptions are not swallowed.
inline ParameterStateStatus applyParameterState(
    ParameterSetter setter,
    void* instance,
    const ParameterValue* values,
    std::size_t count,
    std::size_t expectedParameterCount) {
    const auto status = validateParameterState(values, count, expectedParameterCount);
    if (status != ParameterStateStatus::ok) {
        return status;
    }
    if (!instance) {
        return ParameterStateStatus::missingInstance;
    }
    if (!setter) {
        return ParameterStateStatus::missingSetter;
    }
    for (std::size_t i = 0; i < count; ++i) {
        setter(instance, values[i].index, values[i].value);
    }
    return ParameterStateStatus::ok;
}

}  // namespace m4l_builder::live_compat

