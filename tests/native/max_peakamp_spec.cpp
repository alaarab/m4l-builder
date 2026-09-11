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
struct Rec{uint64_t t;double v;};
struct Log{std::vector<Rec> r;Log(){r.reserve(256);}static void trace(void* c,int,int outlet,uint64_t t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(outlet==0);assert(l.r.size()<l.r.capacity());l.r.push_back({t,m.atoms[0].value.floating});}};
int main(){
    // plugin~ -> peakamp~ 10 (480 samples at 48k) -> plugout~. Feed a burst
    // whose peak sits mid-window and check each report is that window's peak.
    Definition in;in.op=Op::input; Definition pa;pa.op=Op::peakAmp;pa.arguments={10}; Definition out;out.op=Op::output;
    Log log;Symbols sy;
    Runtime rt(std::vector<Definition>{in,pa,out},std::vector<Edge>{{0,0,1,0},{0,0,2,0},{0,1,2,1}},48000,sy,Log::trace,&log);
    std::array<float,64> l{},r{},ol{},orr{};
    auto block=[&](float peakAt,int idx){l.fill(0.f);r.fill(0.f);if(idx>=0)l[size_t(idx)]=peakAt;rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);};
    // DSP off: silent, and nothing accumulates toward the first report.
    block(0.9f,3);assert(log.r.empty());
    rt.setDSPActive(true);
    // Reports land on the first 64-sample vector boundary at or after the
    // interval, so a 480-sample window reports at 512, then 1024.
    block(0.5f,10);block(-0.8f,20);for(int i=0;i<6;++i)block(0.f,-1);
    // Window 2: a single 0.25 -> reports 0.25 at t=960.
    block(0.25f,5);for(int i=0;i<7;++i)block(0.f,-1);
    assert(!rt.faulted());
    assert(log.r.size()>=2);
    assert(log.r[0].t==512 && std::abs(log.r[0].v-0.8)<1e-6);
    assert(log.r[1].t==1024 && std::abs(log.r[1].v-0.25)<1e-6);
    // Measured: a bang reports the running peak at once. Feed 0.6 then bang
    // mid-window; the report is 0.6 and the next interval report restarts.
    log.r.clear();block(0.6f,7);
    {rendering=true;assert(rt.send(1,0,Message{}));rt.render(l.data(),r.data(),ol.data(),orr.data(),0);rendering=false;}
    assert(log.r.size()==1 && std::abs(log.r[0].v-0.6)<1e-6);
    // Preparation refuses a missing or non-positive interval.
    for(auto args:{std::vector<double>{},std::vector<double>{0},std::vector<double>{-5}}){bool f=false;Definition d;d.op=Op::peakAmp;d.arguments=args;try{Runtime r2(std::vector<Definition>{d},std::vector<Edge>{},48000);}catch(const std::invalid_argument&){f=true;}assert(f);}
    std::cout<<"PASS: peakamp~ silent with DSP off, per-interval peak absolute amplitude with window reset at 48k, interval validation, no render allocations. Reports quantise to the 64-sample vector; bang report MEASURED (0.50 on a 0.5 cycle~); whether bang restarts the window is NOT measured.\n";
}
