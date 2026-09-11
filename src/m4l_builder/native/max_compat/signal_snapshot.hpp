#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace m4l::maxcompat {
// snapshot~ samples inside each 64-frame MSP vector, then dispatches those
// values before the next vector. Dispatching immediately changes feedback DSP.
// Fractional intervals retain their phase across vectors without rounding the
// entire interval to an integer number of samples.
class SignalSnapshot {
    double samplesPerMillisecond_, interval_=0, requestedInterval_=0, phase_=0, held_=0;
    int offset_=0, count_=0;
    bool active_=true, requestedActive_=true, restart_=false;
    std::array<double,64> vector_{}, previous_{}, reports_{};
public:
    SignalSnapshot(double milliseconds,int offset,bool active,double sampleRate)
        : samplesPerMillisecond_(sampleRate*.001),offset_(std::clamp(offset,0,63)),active_(active),requestedActive_(active) {
        if(!interval(milliseconds))throw std::invalid_argument("Invalid snapshot~ interval");
    }
    bool interval(double milliseconds) noexcept {
        if(!std::isfinite(milliseconds) || milliseconds<0 || milliseconds>3600000)return false;
        requestedInterval_=(milliseconds!=0 && milliseconds<.25?.25:milliseconds)*samplesPerMillisecond_;
        restart_=true;return true;
    }
    bool sampleInterval(double samples) noexcept {
        if(!std::isfinite(samples) || samples<1 || samples>1382400000)return false;
        requestedInterval_=samples;restart_=true;return true;
    }
    void active(bool enabled) noexcept {requestedActive_=enabled;}
    void offset(double value) noexcept {offset_=value<=0?0:value>=63?63:int(value);}
    double bang(bool audioThread,int position) const noexcept {
        return offset_==0 && audioThread?previous_[position]:held_;
    }
    template<class Emit> void dispatch(Emit emit) noexcept {
        const int count=count_;count_=0;
        for(int i=0;i<count;++i)emit(reports_[i]);
    }
    void process(double input,int position) noexcept {
        if(position==0) {
            active_=requestedActive_;
            if(restart_) {interval_=requestedInterval_;phase_=0;restart_=false;}
        }
        vector_[position]=input;
        if(active_ && interval_!=0 && phase_<64 && int(phase_)==position) {
            reports_[count_++]=input;phase_+=interval_;
        }
        if(position==63) {
            held_=vector_[offset_];previous_=vector_;
            if(active_ && interval_!=0)phase_-=64;
        }
    }
};
}
