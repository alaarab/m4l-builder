#pragma once
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <stdexcept>

namespace m4l::gen {
// xoshiro256+ 1.0 (Blackman/Vigna, public domain), with the 53-bit bipolar
// conversion and chained splitmix initialization in the installed Max Gen
// double-precision profile. No clock, allocation, lock or global RNG in next().
// Reference: https://prng.di.unimi.it/xoshiro256plus.c
class Noise {
    std::array<uint64_t,4> state_;
    static uint64_t splitmix(uint64_t seed) noexcept {
        uint64_t z=seed+UINT64_C(0x9e3779b97f4a7c15);
        z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);
        z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);
        return z^(z>>31);
    }
    static uint64_t preparationSeed() noexcept {
        static std::atomic<uint64_t> sequence{0};
        return splitmix(uint64_t(std::chrono::steady_clock::now().time_since_epoch().count()))
            + sequence.fetch_add(1,std::memory_order_relaxed);
    }
public:
    Noise():Noise(preparationSeed()) {}
    explicit Noise(uint64_t seed) noexcept {
        for(auto& word:state_)word=seed=splitmix(seed);
    }
    // Explicit state supports reference-vector conformance and deterministic
    // offline hosts without inventing a GenExpr seed argument.
    explicit Noise(std::array<uint64_t,4> state):state_(state) {
        if(!(state[0]|state[1]|state[2]|state[3]))throw std::invalid_argument("Noise state must be nonzero");
    }
    double next() noexcept {
        const uint64_t result=state_[0]+state_[3],t=state_[1]<<17;
        state_[2]^=state_[0];state_[3]^=state_[1];state_[1]^=state_[2];state_[0]^=state_[3];state_[2]^=t;
        state_[3]=(state_[3]<<45)|(state_[3]>>19);
        return double(result>>11)*0x1p-52-1.;
    }
};
} // namespace m4l::gen
