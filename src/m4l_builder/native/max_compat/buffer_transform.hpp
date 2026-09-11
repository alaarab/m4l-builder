#pragma once
#include "gen_buffer.hpp"

namespace m4l::maxcompat {
// Preparation-thread operations. Do not perform a whole-buffer transform in
// the audio callback. Runtime messages after preparation remain gated until
// a host transaction can preserve their scheduling and buffer ownership.
inline bool fillPreparedBuffer(m4l::gen::Table& table,double value) noexcept {
    if(!std::isfinite(value) || !std::isfinite(float(value)))return false;
    for(size_t frame=0;frame<table.frames();++frame)
        for(size_t channel=0;channel<table.channels();++channel)table.poke(value,double(frame),double(channel));
    return true;
}
inline void hanningPreparedBuffer(m4l::gen::Table& table) noexcept {
    // Original Max applies a periodic window over interleaved samples. Stereo
    // channels therefore have a half-frame offset, not identical windows.
    constexpr double tau=6.283185307179586476925286766559;
    const size_t count=table.frames()*table.channels();
    for(size_t frame=0;frame<table.frames();++frame) {
        for(size_t channel=0;channel<table.channels();++channel) {
            const double scale=0.5-0.5*std::cos(tau*double(frame*table.channels()+channel)/double(count));
            table.poke(table.peek(double(frame),double(channel))*scale,double(frame),double(channel));
        }
    }
}
}
