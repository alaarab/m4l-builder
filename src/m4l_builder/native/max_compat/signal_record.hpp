#pragma once
#include "gen_buffer.hpp"
#include <array>
#include <algorithm>
#include <stdexcept>

namespace m4l::maxcompat {
// Prepared record~ writer with a fixed MSP vector boundary, independent of the
// host callback size. Signal readback of its buffer needs whole-vector graph
// ordering; the routing/Gen preparation checks reject that dependency for now.
// Original Max restarts its input-vector offset at a loop wrap. Preserve that
// observed behavior rather than substituting a conventional circular writer.
class SignalRecord {
    m4l::gen::Table* buffer_;
    size_t channels_,position_=0,start_=0,end_;
    bool recording_=false,loop_=false,append_=false;
    std::vector<std::array<double,64>> input_;
    std::array<double,64> sync_{};
    size_t vectorPosition_=0,vectorStart_=0;
    int phase_=0,first_=0,second_=0;
    void beginVector() noexcept {
        first_=second_=0;
        if(!recording_) {sync_.fill(0);return;}
        if(position_<start_)position_=start_;
        const double scale=1./double(end_-start_-1);
        if(position_>=end_) {
            if(!loop_) {
                for(int i=0;i<64;++i)sync_[i]=std::min(1.,double(position_-start_+size_t(i))*scale);
                return;
            }
            position_=start_;
        }
        vectorPosition_=position_;vectorStart_=start_;
        first_=int(std::min(size_t(64),end_-position_));
        second_=loop_?64-first_:0;
        position_+=size_t(first_);
        if(second_)position_=start_+size_t(second_);
        for(int i=0;i<64;++i) {
            const auto frame=second_ && i>=first_?start_+size_t(i-first_):vectorPosition_-start_+size_t(i);
            sync_[i]=std::min(1.,double(frame)*scale);
        }
    }
public:
    SignalRecord(m4l::gen::Table& buffer,size_t channels)
        : buffer_(&buffer),channels_(channels),end_(buffer.frames()) {
        if(channels<1 || channels>62 || buffer.frames()<64)throw std::invalid_argument("record~ needs prepared channels and at least one vector of storage");
        input_.resize(channels);
    }
    void record(double flag) noexcept {
        recording_=std::trunc(flag)!=0;
        if(recording_ && !append_)position_=0;
    }
    void loop(bool enabled) noexcept {loop_=enabled;}
    void append(bool enabled) noexcept {append_=enabled;}
    bool range(size_t start,size_t end) noexcept {
        if(start>=end || end>buffer_->frames() || end-start<64)return false;
        start_=start;end_=end;return true;
    }
    void reset() noexcept {start_=0;end_=buffer_->frames();}
    int channels() const noexcept {return int(channels_);}
    double processSample(const double* input) noexcept {
        if(phase_==0)beginVector();
        for(size_t ch=0;ch<channels_;++ch)input_[ch][phase_]=input[ch];
        if(phase_<first_+second_) {
            const bool wrapped=phase_>=first_;
            const int source=wrapped?phase_-first_:phase_;
            const size_t target=wrapped?vectorStart_+size_t(source):vectorPosition_+size_t(source);
            for(size_t ch=0;ch<buffer_->channels();++ch)
                buffer_->poke(ch<channels_?input_[ch][source]:0,double(target),double(ch));
        }
        const double value=sync_[phase_];phase_=(phase_+1)%64;return value;
    }
    bool process(const double* const* input,double* sync,int frames) noexcept {
        if(frames<0 || (frames && (!input || !sync)))return false;
        for(size_t ch=0;ch<channels_;++ch)if(frames && !input[ch])return false;
        std::array<double,62> values{};
        for(int i=0;i<frames;++i) {
            for(size_t ch=0;ch<channels_;++ch)values[ch]=input[ch][i];
            sync[i]=processSample(values.data());
        }
        return true;
    }
};
}
