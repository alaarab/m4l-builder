#pragma once
#include "message.hpp"
#include <cmath>
#include <stdexcept>

namespace m4l::maxcompat {
// DSP lifecycle is separate from song transport and device bypass. The host
// supplies its actual prepared rate and I/O vector; the Max graph uses 64-frame
// signal vectors. Mutate only under the owning renderer's control barrier.
class DSPState {
    double rate_;
    int ioVector_,signalVector_;
    enum class Phase { uncompiled, running, stopped } phase_=Phase::uncompiled;
    template<class Emit> void output(Emit&& emit) const noexcept {
        // Original Max order/type: I/O int, signal-vector int, rate float, on int.
        emit(3,Message::integer(ioVector_));
        emit(2,Message::integer(phase_==Phase::uncompiled?ioVector_:signalVector_));
        emit(1,Message::number(rate_));
        emit(0,Message::integer(phase_==Phase::running?1:0));
    }
public:
    DSPState(double rate,int ioVector,int signalVector=64):rate_(rate),ioVector_(ioVector),signalVector_(signalVector) {
        if(!std::isfinite(rate) || rate<8000 || rate>384000 || ioVector<1 || ioVector>65536 || signalVector<1 || signalVector>65536)
            throw std::invalid_argument("Invalid prepared DSP configuration");
    }
    bool active() const noexcept {return phase_==Phase::running;}
    template<class Emit> void bang(Emit&& emit) const noexcept {
        // A never-compiled object reports the I/O vector in both vector outlets.
        // After DSP stops it reports the stop automatically, then ignores bang.
        if(phase_!=Phase::stopped)output(emit);
    }
    template<class Emit> void setActive(bool active,Emit&& emit) noexcept {
        if(active==this->active())return;
        phase_=active?Phase::running:Phase::stopped;output(emit);
    }
};
}
