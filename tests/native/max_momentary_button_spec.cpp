#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
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
struct Rec{int outlet;Message m;uint64_t t;};
struct Log{std::vector<Rec> r;Log(){r.reserve(64);}static void trace(void* c,int,int outlet,uint64_t t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(l.r.size()<l.r.capacity());l.r.push_back({outlet,m,t});}};
static void render(Runtime& rt,int frames){std::array<float,64> l{},r{};rendering=true;while(frames>0){int n=std::min(frames,64);rt.render(nullptr,nullptr,l.data(),r.data(),n);frames-=n;}rendering=false;assert(allocations==0);}
int main(){
    Symbols sy;const Symbol a=sy.intern("Tap"),b=sy.intern("Tap"),v1=sy.intern("val1"),v2=sy.intern("val2");
    Definition d;d.op=Op::dial;d.parameterType=2;d.controlKind=3;d.minimum=0;d.maximum=1;d.parameterLabels={v1,v2};d.textLabels={a,b};d.presentation=true;
    Log log;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,Log::trace,&log);
    // A press bangs outlet 0 and stores 1; the flash timer then silently
    // returns the stored value to 0 with no further output, DSP off throughout.
    assert(rt.send(0,0,Message{}));render(rt,64);
    assert(rt.parameterValue(0)==1.);
    const size_t after=log.r.size();assert(after>=1);
    bool bang=false;for(const auto& e:log.r)if(e.outlet==0 && e.m.kind==Message::Kind::bang)bang=true;assert(bang);
    render(rt,int(std::ceil(kButtonFlashMs*48000./1000.))+64);
    assert(rt.parameterValue(0)==0.);
    assert(log.r.size()==after);           // reset emitted nothing
    // A second press after the flash bangs again.
    assert(rt.send(0,0,Message{}));render(rt,64);
    assert(rt.parameterValue(0)==1.);assert(log.r.size()>after);
    assert(!rt.faulted());
    std::cout<<"PASS: live.text button mode bangs on press, stores 1, resets to 0 silently after the flash with DSP off, re-presses after the flash. Flash interval "<<kButtonFlashMs<<" ms is an UNMEASURED default.\n";
}
