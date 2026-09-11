#pragma once
#include "message.hpp"
#include "gen_buffer.hpp"
#include <memory>

namespace m4l::maxcompat {
// One prepared session owns a routing domain. Symbols are translated between
// original graph tables before dispatch; no interning, allocation or locking is
// allowed after prepare(). All dispatch runs on the owning render thread.
class RoutingDomain {
public:
    using Delivery=bool(*)(void*,int,const Message&,int,int*) noexcept;
    struct Receiver {int node;Symbol name;};
private:
    struct Member {
        Symbols* symbols;
        void* context;
        Delivery deliver;
        std::vector<Receiver> receivers;
        std::vector<Symbol> toGlobal,fromGlobal;
    };
    struct Target {size_t member;int node;};
    std::vector<std::unique_ptr<Member>> members_;
    std::vector<std::vector<Target>> channels_;
    bool prepared_=false;
    m4l::gen::BufferRegistry buffers_;
    size_t bufferSamples_=0;
    std::vector<std::string> recordBuffers_;
public:
    const m4l::gen::BufferRegistry& buffers() const noexcept {return buffers_;}
    void declareRecordBuffer(const std::string& name) {
        if(prepared_)throw std::invalid_argument("record~ buffers must be prepared before playback");
        recordBuffers_.push_back(name);
    }
    // An unsized buffer~ reserves this many samples so a script's
    // sizeinsamps can allocate it later without reallocating under DSP.
    static constexpr size_t kUnsizedReserve=65536;
    void declareBuffer(const std::string& name,size_t frames,size_t channels,size_t requestedReserve=0) {
        const size_t reserve=std::max((frames==0 && channels==0)?kUnsizedReserve:size_t(0),requestedReserve);
        if(prepared_ || frames>4194304 || (channels==0 && frames!=0) || channels>64 || std::max(frames*channels,reserve)>8388608-bufferSamples_)
            throw std::invalid_argument("Session buffer~ preparation/memory budget exceeded");
        // MEASURED (Max 9, September 11): buffer~ names are global, so two
        // devices (or two instances of one) declaring the same plain name
        // share one storage and the last writer wins. The first declaration
        // in load order (here: track/device order) fixes the size; a later
        // declaration with another size, or an unsized one, binds to the
        // existing buffer unchanged, silently (no resize, no clear, no error).
        if(buffers_.count(name))return;
        buffers_.emplace(name,std::make_shared<m4l::gen::Table>(frames,channels,true,reserve));bufferSamples_+=std::max(frames*channels,reserve);
    }
    size_t attach(Symbols& symbols,void* context,Delivery deliver,std::vector<Receiver> receivers) {
        if(prepared_ || members_.size()>=4096)throw std::invalid_argument("Routing domain must be rebuilt before adding graphs");
        auto member=std::make_unique<Member>();member->symbols=&symbols;member->context=context;member->deliver=deliver;member->receivers=std::move(receivers);
        members_.push_back(std::move(member));return members_.size()-1;
    }
    void detach(size_t member) noexcept {if(member<members_.size())members_[member].reset();}
    void prepare() {
        if(prepared_)return;
        for(const auto& name:recordBuffers_) {
            const auto found=buffers_.find(name);
            if(found==buffers_.end() || found->second->frames()<64)
                throw std::invalid_argument("record~ needs a collected buffer with at least 64 samples");
            found->second->declareVectorWriter();
        }
        Symbols global;
        for(const auto& member:members_)if(member)for(size_t i=0;i<member->symbols->size();++i)global.intern(member->symbols->name(Symbol(i)));
        size_t count=0;for(const auto& member:members_)if(member)++count;
        if(count && global.size()>4194304/count)throw std::invalid_argument("Routing translation memory budget exceeded");
        channels_.resize(global.size());
        for(size_t index=0;index<members_.size();++index)if(auto& member=members_[index]) {
            member->fromGlobal.reserve(global.size());
            for(size_t i=0;i<global.size();++i)member->fromGlobal.push_back(member->symbols->intern(global.name(Symbol(i))));
            member->toGlobal.reserve(member->symbols->size());
            for(size_t i=0;i<member->symbols->size();++i)member->toGlobal.push_back(global.intern(member->symbols->name(Symbol(i))));
            for(const auto& receiver:member->receivers) {
                if(receiver.name>=member->toGlobal.size() || receiver.node<0)throw std::invalid_argument("Invalid named receiver");
                channels_[member->toGlobal[receiver.name]].push_back({index,receiver.node});
            }
        }
        prepared_=true;
    }
    bool prepared() const noexcept {return prepared_;}
    bool broadcast(size_t sender,Symbol name,const Message& message,int depth,int* budget) noexcept {
        if(!prepared_ || sender>=members_.size() || !members_[sender] || !budget || depth>64)return false;
        const auto& origin=*members_[sender];
        if(name>=origin.toGlobal.size() || !message.valid(origin.toGlobal.size()))return false;
        const auto channel=origin.toGlobal[name];
        for(const auto& target:channels_[channel])if(const auto& member=members_[target.member]) {
            if(--*budget<0)return false;
            Message translated=message;translated.selector=member->fromGlobal[origin.toGlobal[message.selector]];
            for(int i=0;i<message.count;++i)if(message.atoms[i].type==Atom::Type::symbol)
                translated.atoms[i]=Atom::named(member->fromGlobal[origin.toGlobal[message.atoms[i].value.symbol]]);
            if(!member->deliver(member->context,target.node,translated,depth+1,budget))return false;
            if(*budget<0)return false;
        }
        return true;
    }
};
} // namespace m4l::maxcompat
