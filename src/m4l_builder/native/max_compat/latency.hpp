#pragma once
#include <algorithm>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace m4l::maxcompat {
// Prepared storage; variable taps and reset never allocate on the callback.
class StereoLatency {
    std::vector<float> samples_;
    size_t capacity_=0,cursor_=0,filled_=0;
public:
    void prepare(size_t capacity) {
        if(capacity>65536)throw std::invalid_argument("Latency exceeds the prepared 65536-sample path budget");
        capacity_=capacity;samples_.resize(capacity?2*(capacity+1):0);reset();
    }
    size_t capacity() const noexcept {return capacity_;}
    void reset() noexcept {cursor_=0;filled_=0;}
    void process(float left,float right,size_t delay,float& outLeft,float& outRight) noexcept {
        if(!capacity_) {outLeft=delay?0:left;outRight=delay?0:right;return;}
        samples_[cursor_*2]=left;samples_[cursor_*2+1]=right;
        if(delay>capacity_ || delay>filled_)outLeft=outRight=0;
        else {const auto read=(cursor_+capacity_+1-delay)%(capacity_+1);outLeft=samples_[read*2];outRight=samples_[read*2+1];}
        cursor_=(cursor_+1)%(capacity_+1);filled_=std::min(capacity_,filled_+1);
    }
};
}
