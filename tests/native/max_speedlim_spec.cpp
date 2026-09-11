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
struct Rec{uint64_t t;int64_t v;};
struct Log{std::vector<Rec> r;Log(){r.reserve(64);}static void trace(void* c,int,int outlet,uint64_t t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(outlet==0);assert(l.r.size()<l.r.capacity());l.r.push_back({t,m.atoms[0].value.integer});}};
static void render(Runtime& rt,int frames){std::array<float,64> l{},r{};rendering=true;while(frames>0){int n=std::min(frames,64);rt.render(nullptr,nullptr,l.data(),r.data(),n);frames-=n;}rendering=false;assert(allocations==0);}
int main(){
    // speedlim 10 at 48k: interval = 480 samples. First message passes at
    // once; a burst inside the window collapses to the LAST value, emitted
    // exactly when the window ends; a later message after that passes again.
    Definition d;d.op=Op::speedlim;d.arguments={10};
    Log log;Symbols sy;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,Log::trace,&log);
    assert(rt.send(0,0,Message::integer(1)));render(rt,64);            // t=0 emit 1
    assert(rt.send(0,0,Message::integer(2)));render(rt,64);            // t=64 held
    assert(rt.send(0,0,Message::integer(3)));render(rt,64);            // t=128 held, replaces 2
    render(rt,480);                                                     // window ends at t=480
    assert(rt.send(0,0,Message::integer(4)));render(rt,64);            // t=768: > 480+480? no: last output 480, so held until 960
    render(rt,320);
    assert(!rt.faulted());
    assert(log.r.size()==3);
    assert(log.r[0].v==1 && log.r[0].t==0);
    assert(log.r[1].v==3 && log.r[1].t==480);
    assert(log.r[2].v==4 && log.r[2].t==960);
    // Right inlet changes the interval; non-numbers there fault.
    assert(rt.send(0,1,Message::integer(0)));render(rt,64);
    assert(rt.send(0,0,Message::integer(5)));assert(rt.send(0,0,Message::integer(6)));render(rt,64);
    assert(log.r.size()==5 && log.r[3].v==5 && log.r[4].v==6);
    assert(rt.send(0,1,Message{}));render(rt,64);assert(rt.faulted());
    std::cout<<"PASS: speedlim immediate pass, in-window burst collapses to latest and fires at window end, re-arms after, zero interval passes all, right-inlet interval, fault on bad interval, no render allocations. Latest-wins NOT measured against Max.\n";
}
