#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace m4l::maxcompat {
// Original selector~ routing, including independently interrupted ramps.
// Storage is prepared once; selection and sample processing never allocate.
// Max 9 ARM64 reference captures cover message and signal control. Signal
// control has separate state from the constructor/message selection: its
// previous input starts at input 1, even when the constructor selects silence.
class SignalSelector {
    struct Fade { uint64_t remaining=0; double gain=0, increment=0; };
    std::array<Fade,63> fades_{};
    int count_, selected_, signalSelected_=1, stepSelection_=0;
    int64_t previousTrigger_=0;
    double samplesPerMillisecond_, ramp_;
    bool signalControl_, stepMode_;

    static int64_t integer(double value) noexcept {
        if(std::isnan(value))return 0;
        if(value>=double(INT64_MAX))return INT64_MAX;
        if(value<=double(INT64_MIN))return INT64_MIN;
        return int64_t(value);
    }
    int clipped(int64_t value) const noexcept {return value<=0?0:value>=count_?count_:int(value);}
    void fade(int input, double target) noexcept {
        if(!input)return;
        auto& f=fades_[input-1];
        // A completed fade has no stored contribution. The departing input is
        // full level; the arriving input starts at zero unless still fading.
        if(!f.remaining)f.gain=1-target;
        f.remaining=uint64_t(ramp_*samplesPerMillisecond_);
        f.increment=f.remaining?(target-f.gain)/double(f.remaining):0;
    }
    void transition(int from,int to) noexcept {
        if(from==to)return;
        fade(from,0);fade(to,1);
    }
public:
    SignalSelector(int count,int initial,double ramp,bool step,double sampleRate,bool signalControl)
        : count_(count),selected_(initial),samplesPerMillisecond_(sampleRate*.001),ramp_(ramp),signalControl_(signalControl),stepMode_(step) {
        if(count<1 || count>63 || initial<0 || initial>count || !std::isfinite(ramp) || ramp<0 || ramp>3600000 ||
           !std::isfinite(sampleRate) || sampleRate<8000 || sampleRate>384000)
            throw std::invalid_argument("Invalid selector~ preparation");
    }
    void select(double value,bool running) noexcept {
        const int next=clipped(integer(value));
        if(running && !signalControl_ && ramp_!=0)transition(selected_,next);
        selected_=next;
    }
    void next(bool running) noexcept {select(selected_>=count_?1:selected_+1,running);}
    bool ramp(double value) noexcept {
        if(!std::isfinite(value) || value<0 || value>3600000)return false;
        ramp_=value;return true;
    }
    void step(bool enabled) noexcept {stepMode_=enabled;}
    int count() const noexcept {return count_;}
    double process(double control,const double* inputs) noexcept {
        int choice=selected_;
        if(signalControl_) {
            const auto trigger=integer(control);
            if(stepMode_) {
                if(trigger==0)stepSelection_=0;
                else if(trigger!=previousTrigger_)stepSelection_=stepSelection_>=count_?1:stepSelection_+1;
                else if(stepSelection_==0)stepSelection_=1;
                previousTrigger_=trigger;choice=stepSelection_;
            } else choice=clipped(trigger);
            transition(signalSelected_,choice);signalSelected_=choice;
        }
        double output=0;bool fading=false;
        for(int i=0;i<count_;++i) {
            auto& f=fades_[i];
            if(f.remaining) {
                fading=true;output=std::fma(f.gain,inputs[i],output);
                --f.remaining;f.gain+=f.increment;
            }
        }
        return fading?output:choice?inputs[choice-1]:0;
    }
};
}
