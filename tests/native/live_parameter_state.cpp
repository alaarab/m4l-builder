#include "../../src/m4l_builder/native/live_compat/parameter_state.h"

#include <array>
#include <cassert>
#include <limits>
#include <stdexcept>

namespace compat = m4l_builder::live_compat;
using Status = compat::ParameterStateStatus;

struct Sink {
    std::size_t calls = 0;
    std::array<compat::ParameterValue, compat::maximumParameterStateSize> received{};
};

static void capture(void* instance, std::int64_t index, float value) {
    auto& sink = *static_cast<Sink*>(instance);
    assert(sink.calls < sink.received.size());
    sink.received[sink.calls++] = {index, value};
}

static void foreignFailure(void*, std::int64_t, float) {
    throw std::runtime_error("original setter failure");
}

int main() {
    Sink sink;
    std::array<compat::ParameterValue, 3> values{{{2, 48.f}, {0, -1.f}, {1, 0.5f}}};
    static_assert(noexcept(compat::validateParameterState(nullptr, 0, 0)));
    auto validate = [&] { return compat::validateParameterState(values.data(), values.size(), 3); };
    auto apply = [&] { return compat::applyParameterState(capture, &sink, values.data(), values.size(), 3); };
    assert(validate() == Status::ok);
    assert(apply() == Status::ok);
    assert(sink.calls == 3);
    for (std::size_t i = 0; i < values.size(); ++i) {
        assert(sink.received[i].index == values[i].index);
        assert(sink.received[i].value == values[i].value);
    }

    // Invalid final entries cannot partially replace the first two parameters.
    for (const auto invalid : {std::numeric_limits<float>::quiet_NaN(),
                               std::numeric_limits<float>::infinity(),
                               -std::numeric_limits<float>::infinity()}) {
        values.back().value = invalid;
        assert(apply() == Status::nonFiniteValue);
        assert(sink.calls == 3);
    }
    values.back().value = 0.5f;
    for (const std::int64_t invalid :
         {std::int64_t{-1}, std::int64_t{3}, std::int64_t{1024},
          std::numeric_limits<std::int64_t>::max()}) {
        values.back().index = invalid;
        assert(apply() == Status::invalidIndex);
        assert(sink.calls == 3);
    }
    values.back().index = 0;
    assert(apply() == Status::duplicateIndex);
    assert(sink.calls == 3);
    values.back().index = 1;

    assert(compat::applyParameterState(capture, &sink, values.data(), 2, 3) == Status::incompleteState);
    assert(compat::applyParameterState(capture, &sink, nullptr, 3, 3) == Status::missingStorage);
    assert(compat::validateParameterState(nullptr, 0, 3) == Status::incompleteState);
    assert(compat::validateParameterState(nullptr, 0, 0) == Status::invalidParameterCount);
    assert(compat::validateParameterState(nullptr, 1025, 1025) == Status::invalidParameterCount);
    assert(compat::validateParameterState(nullptr, 1025, 3) == Status::invalidParameterCount);
    assert(compat::applyParameterState(capture, nullptr, values.data(), 3, 3) == Status::missingInstance);
    assert(compat::applyParameterState(nullptr, &sink, values.data(), 3, 3) == Status::missingSetter);
    assert(sink.calls == 3);

    std::array<compat::ParameterValue, compat::maximumParameterStateSize> maximum{};
    for (std::size_t i = 0; i < maximum.size(); ++i) {
        maximum[i] = {static_cast<std::int64_t>(maximum.size() - 1 - i), static_cast<float>(i)};
    }
    Sink large;
    assert(compat::applyParameterState(capture, &large, maximum.data(), maximum.size(),
                                       maximum.size()) == Status::ok);
    assert(large.calls == maximum.size());
    assert(large.received.front().index == 1023);
    assert(large.received.back().index == 0);

    bool propagated = false;
    try {
        compat::applyParameterState(foreignFailure, &sink, values.data(), 3, 3);
    } catch (const std::runtime_error&) {
        propagated = true;
    }
    assert(propagated);
}

