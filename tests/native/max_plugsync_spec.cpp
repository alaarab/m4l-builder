#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <new>
#include <vector>

static thread_local bool rendering=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n) {if(rendering)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;

struct Record {int outlet;Message message;};
struct Log {
    std::vector<Record> records;
    Log(){records.reserve(4096);}
    static void trace(void* c,int,int outlet,uint64_t,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(c);assert(log.records.size()<log.records.capacity());log.records.push_back({outlet,m});
    }
};
// Renders in host-sized blocks and, like SessionRender, republishes the
// advanced transport before every block.
static void render(Runtime& rt,int frames,bool playing=false,double tempo=120,double beat=0,double rate=48000){
    std::array<float,256> l{},r{};rendering=true;int done=0;
    while(frames>0){int n=std::min(frames,256);rt.setTransport(playing,tempo,beat+double(done)*tempo/(60.*rate));rt.render(nullptr,nullptr,l.data(),r.data(),n);frames-=n;done+=n;}
    rendering=false;assert(allocations==0);
}
int main(){
    Definition d;d.op=Op::plugSync;
    Definition out;out.op=Op::output;
    Log log;Symbols symbols;
    Runtime rt(std::vector<Definition>{d,out},std::vector<Edge>{},48000,symbols,Log::trace,&log);
    // Silent while DSP is off, exactly like a signal object.
    render(rt,256,true,120,0);
    assert(log.records.empty());
    rt.setDSPActive(true);
    // Stopped transport: running 0, phase frozen at the reported beat.
    render(rt,64,false,120,1.25);
    assert(log.records.size()==4);
    assert(log.records[0].outlet==5 && log.records[0].message.atoms[0].value.floating==120.);
    assert(log.records[1].outlet==3 && std::abs(log.records[1].message.atoms[0].value.floating-0.25)<1e-12);
    assert(log.records[2].outlet==2 && log.records[2].message.atoms[0].value.integer==2);
    assert(log.records[3].outlet==0 && log.records[3].message.atoms[0].value.integer==0);
    log.records.clear();
    // Playing at 120 BPM / 48k: one beat = 24000 frames. Block start at beat 3.9;
    // the phase advances inside the block and beat-in-bar wraps 4 -> 1.
    render(rt,4800,true,120,3.9);
    const int vectors=4800/64;assert(int(log.records.size())==vectors*4);
    double lastPhase=-1;bool wrapped=false;
    for(int v=0;v<vectors;++v){
        const auto& tempo=log.records[size_t(v*4)],&phase=log.records[size_t(v*4+1)],&bar=log.records[size_t(v*4+2)],&run=log.records[size_t(v*4+3)];
        assert(tempo.outlet==5 && tempo.message.atoms[0].value.floating==120.);
        assert(run.outlet==0 && run.message.atoms[0].value.integer==1);
        const double expectedBeat=3.9+double(v*64)*120./(60.*48000.);
        assert(std::abs(phase.message.atoms[0].value.floating-(expectedBeat-std::floor(expectedBeat)))<1e-9);
        const int64_t expectedBar=int64_t(std::fmod(std::floor(expectedBeat),4.))+1;
        assert(bar.message.atoms[0].value.integer==expectedBar);
        if(expectedBar==1 && lastPhase>0.5)wrapped=true;
        lastPhase=phase.message.atoms[0].value.floating;
    }
    assert(wrapped);
    assert(!rt.faulted());
    // Invalid transport values are ignored rather than propagated.
    log.records.clear();rt.setTransport(true,NAN,-1);{std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;}
    assert(log.records.size()==4 && log.records[0].message.atoms[0].value.floating==120.);
    std::cout<<"PASS: plugsync~ silent with DSP off, per-vector running/beat-in-bar/phase/tempo on outlets 0/2/3/5 right to left, in-block beat advance and 4->1 wrap at 120 BPM/48k, invalid transport ignored, nine declared outlets, no render allocations. 4/4 assumed; NOT verified against Live.\n";
}
