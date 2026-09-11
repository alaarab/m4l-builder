#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace m4l::gen {
enum class Interpolation { linear, step, cubic };
inline Interpolation delayInterpolation(const std::string& name) {
    if(name=="linear")return Interpolation::linear;
    if(name=="none" || name=="step")return Interpolation::step;
    if(name=="cubic")return Interpolation::cubic;
    throw std::invalid_argument("Gen delay interpolation needs verified support: "+name);
}
class Delay {
    struct Sample {double value=0;uint64_t generation=0;};
    std::vector<Sample> data_;
    size_t cursor_=0,maximum_=0;
    uint64_t generation_=1;
    bool written_=false;
    double sample(size_t age) const noexcept {
        const auto& cell=data_[(cursor_-age)&(data_.size()-1)];
        return cell.generation==generation_?cell.value:0;
    }
public:
    static size_t storageFor(size_t maximum) {
        if(!maximum || maximum>4194304)throw std::invalid_argument("Gen delay exceeds the prepared sample budget");
        size_t size=1;while(size<maximum)size*=2;return size;
    }
    explicit Delay(size_t maximum):data_(storageFor(maximum)),maximum_(maximum) {}
    size_t storageSamples() const noexcept {return data_.size();}
    void reset() noexcept {
        cursor_=0;written_=false;
        // Invalidate unwritten cells without clearing a large audio buffer on
        // the callback. Conditional writes must not resurrect pre-reset audio.
        if(++generation_==0) {for(auto& cell:data_)cell.generation=0;generation_=1;}
    }
    void write(double value) noexcept {
        data_[cursor_]={std::fpclassify(value)==FP_SUBNORMAL?0:value,generation_};written_=true;
    }
    double read(double time,Interpolation mode=Interpolation::linear) const noexcept {
        if(!std::isfinite(time))return 0;
        if(mode==Interpolation::cubic) {
            // Max's four-point cubic has one sample of compensation and
            // reads forward from floor(size+reader-delay). This is Lagrange
            // interpolation, not the deprecated fastcubic/Catmull-Rom modes.
            const double delay=std::min(std::max(time,written_?1.:2.),double(maximum_));
            const double position=double(data_.size()+cursor_)-delay;
            const size_t index=size_t(position),age=cursor_-index;
            const double a=position-double(index),a1=1+a,aa=a*a1,b=1-a,b1=2-a,bb=b*b1;
            return sample(age)*(-.1666667*bb*a)+sample(age-1)*(.5*bb*a1)
                +sample(age-2)*(.5*aa*b1)+sample(age-3)*(-.1666667*aa*b);
        }
        const double delay=std::clamp(time,written_?0.:1.,double(maximum_));
        if(mode==Interpolation::step)return sample(size_t(std::ceil(delay-.5)));
        const auto age=size_t(std::floor(delay));double fraction=delay-double(age);
        const double first=sample(age),second=sample(age+1);
        return first+(second-first)*fraction;
    }
    void advance() noexcept {
        cursor_=(cursor_+1)&(data_.size()-1);written_=false;
    }
};
} // namespace m4l::gen
