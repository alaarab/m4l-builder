#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <map>
#include <new>
#include <vector>
static thread_local bool rendering=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n) {if(rendering)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;
struct Log{std::map<int,Message> byOutlet;std::vector<int> order;static void trace(void* c,int,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);if(l.order.size()<l.order.capacity()){l.order.push_back(outlet);l.byOutlet[outlet]=m;}}};
static void drain(Runtime& rt){std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;}
int main(){
    // The measured Live row: 55426.96 total ticks at 120 BPM reconciles to bar
    // 29, beat 4, 226.96 ticks in. Feed that beat position and check every
    // modelled outlet against the measurement.
    Definition d;d.op=Op::transport;Log log;log.order.reserve(16);Symbols sy;
    Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,Log::trace,&log);
    rt.setTransport(true,120,55426.96/480.);
    assert(rt.send(0,0,Message{}));drain(rt);assert(!rt.faulted());
    assert(log.byOutlet[0].atoms[0].value.integer==29);
    assert(log.byOutlet[1].atoms[0].value.integer==4);
    assert(std::abs(log.byOutlet[2].atoms[0].value.floating-226.96)<1e-6);
    assert(log.byOutlet[3].atoms[0].value.floating==480.);
    assert(log.byOutlet[4].atoms[0].value.floating==120.);
    assert(log.byOutlet[6].atoms[0].value.integer==1);
    assert(std::abs(log.byOutlet[7].atoms[0].value.floating-55426.96)<1e-6);
    // MEASURED September 11: outlet 5 is the time signature list ('4 4'), outlet 8 emits nothing.
    assert(log.byOutlet[5].kind==Message::Kind::list && log.byOutlet[5].count==2 && log.byOutlet[5].atoms[0].value.integer==4 && log.byOutlet[5].atoms[1].value.integer==4);
    assert((log.order==std::vector<int>{7,6,5,4,3,2,1,0}));   // right to left, nothing from 8
    // Stopped: running flag 0 (measured by loading the probe stopped).
    log.order.clear();rt.setTransport(false,120,0);assert(rt.send(0,0,Message{}));drain(rt);
    assert(log.byOutlet[6].atoms[0].value.integer==0 && log.byOutlet[0].atoms[0].value.integer==1);
    // zl.reg: int stores and outputs (measured), bang re-outputs, right inlet stores silently.
    Definition z;z.op=Op::zlRegister;Log zl;zl.order.reserve(16);
    Runtime rz(std::vector<Definition>{z},std::vector<Edge>{},48000,sy,Log::trace,&zl);
    assert(rz.send(0,0,Message::integer(7)));drain(rz);assert(zl.order.size()==1 && zl.byOutlet[0].atoms[0].value.integer==7);
    assert(rz.send(0,0,Message{}));drain(rz);assert(zl.order.size()==2 && zl.byOutlet[0].atoms[0].value.integer==7);
    assert(rz.send(0,1,Message::integer(9)));drain(rz);assert(zl.order.size()==2);
    assert(rz.send(0,0,Message{}));drain(rz);assert(zl.order.size()==3 && zl.byOutlet[0].atoms[0].value.integer==9);
    assert(!rz.faulted());
    // [int] / [float] given junk (MEASURED): a list outputs its first element, a symbol nothing.
    Definition di;di.op=Op::integer;Log li;li.order.reserve(8);Runtime ri(std::vector<Definition>{di},std::vector<Edge>{},48000,sy,Log::trace,&li);
    Message lst;lst.kind=Message::Kind::list;lst.selector=sym::list;lst.count=2;lst.atoms[0]=Atom::integral(3);lst.atoms[1]=Atom::integral(4);
    assert(ri.send(0,0,lst));drain(ri);assert(li.order.size()==1 && li.byOutlet[0].atoms[0].value.integer==3);
    Symbol foo=sy.intern("foo");Runtime ri2(std::vector<Definition>{di},std::vector<Edge>{},48000,sy,Log::trace,&li);
    assert(ri2.send(0,0,Message::anything(foo)));drain(ri2);assert(li.order.size()==1 && !ri2.faulted());
    std::cout<<"PASS: transport reproduces the measured Live row (bar 29, beat 4, 226.96 ticks, 480, 120 BPM, running, 55426.96 total ticks) right to left, stopped flag; zl.reg int store-and-output (measured), bang, silent right inlet. Outlet 5 time signature, outlet 8 silent, int/float list-first-element and symbol-silence (measured); non-int zl.reg inputs unmeasured.\n";
}
