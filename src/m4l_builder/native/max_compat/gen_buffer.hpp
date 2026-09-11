#pragma once
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace m4l::gen {
// Max buffer~ stores float samples; Gen Data stores doubles. Allocate and bind
// off the audio thread. External samples use lock-free words so host-side meter
// readers never race DSP writes. A snapshot is not a transaction across frames.
class Table {
    // frames/channels are atomic so a control-thread resize (buffer~
    // sizeinsamps from a script) is coherent for the renderer: storage is
    // reserved once at declaration (`capacity_` samples) and never
    // reallocated; a reader that sees the new size indexes the same words.
    std::atomic<size_t> frames_,channels_;
    size_t capacity_=0;
    std::vector<double> data_;
    std::unique_ptr<std::atomic<uint32_t>[]> external_;
    bool vectorWriter_=false;
public:
    static_assert(std::atomic<uint32_t>::is_always_lock_free && std::atomic<size_t>::is_always_lock_free);
    // An unsized external buffer~ (0 frames, 0 channels: Max's unallocated
    // default) reserves `reserve` samples so a later sizeinsamps can fill it.
    Table(size_t frames,size_t channels,bool external,size_t reserve=0):frames_(frames),channels_(channels) {
        if((channels==0 && frames!=0) || channels>64 || frames>4194304 || frames*channels>8388608 || reserve>8388608)
            throw std::invalid_argument("Gen table exceeds sample/channel budget");
        capacity_=std::max(frames*channels,external?reserve:size_t(0));
        if(external)external_=std::make_unique<std::atomic<uint32_t>[]>(capacity_?capacity_:1);
        else data_.resize(frames*channels);
        clear();
    }
    size_t frames() const noexcept {return frames_.load(std::memory_order_acquire);}
    size_t channels() const noexcept {return channels_.load(std::memory_order_acquire);}
    size_t capacity() const noexcept {return capacity_;}
    // Control-thread resize within the reserved words; contents are cleared
    // like Max's sizeinsamps. Fails visibly beyond the reservation, for a
    // non-external table, or when an MSP vector writer owns the table.
    bool resize(size_t frames,size_t channels) noexcept {
        if(!external_ || vectorWriter_ || channels==0 || channels>64 || frames>4194304 || frames*channels>capacity_)return false;
        frames_.store(0,std::memory_order_release);
        for(size_t i=0;i<capacity_;++i)external_[i].store(0,std::memory_order_relaxed);
        channels_.store(channels,std::memory_order_release);frames_.store(frames,std::memory_order_release);
        return true;
    }
    // Immutable after routing preparation. A scalar Gen reader cannot observe
    // the same buffer as an MSP vector writer without an explicit vector order.
    // Several record~ writers may share one buffer (MEASURED September 11: two
    // Heat instances write both tracks' audio into the one global heat_scope
    // buffer); each writes its vector in the session's render order, so the
    // last writer of a region wins exactly as Max's DSP chain order does.
    void declareVectorWriter() { vectorWriter_=true; }
    bool hasVectorWriter() const noexcept {return vectorWriter_;}
    void clear() noexcept {
        const size_t count=frames()*channels();
        if(external_)for(size_t i=0;i<count;++i)external_[i].store(0,std::memory_order_relaxed);
        else std::fill(data_.begin(),data_.end(),0);
    }
    double peek(double frame,double channel) const noexcept {
        // Gen's channel inlet truncates toward zero; the sample position check
        // precedes conversion, so negative sample fractions stay out of range.
        channel=std::trunc(channel);
        const size_t frames=this->frames(),channels=this->channels();
        if(!std::isfinite(frame) || !std::isfinite(channel) || frame<0 || frame>=frames || channel<0 || channel>=channels)return 0;
        const size_t index=size_t(frame)*channels+size_t(channel);
        if(!external_)return data_[index];
        if(index>=capacity_)return 0;
        const uint32_t bits=external_[index].load(std::memory_order_relaxed);float value;
        std::memcpy(&value,&bits,sizeof(value));return value;
    }
    void poke(double value,double frame,double channel) noexcept {
        channel=std::trunc(channel);
        const size_t frames=this->frames(),channels=this->channels();
        if(!std::isfinite(frame) || !std::isfinite(channel) || frame<0 || frame>=frames || channel<0 || channel>=channels)return;
        const size_t index=size_t(frame)*channels+size_t(channel);
        if(!external_)data_[index]=value;
        else {if(index>=capacity_)return;const float sample=float(value);uint32_t bits;std::memcpy(&bits,&sample,sizeof(bits));external_[index].store(bits,std::memory_order_relaxed);}
    }
};
using BufferRegistry=std::map<std::string,std::shared_ptr<Table>>;
}
