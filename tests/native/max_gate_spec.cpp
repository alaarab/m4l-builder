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
struct Rec{int outlet;Message m;};
struct Log{std::vector<Rec> r;Log(){r.reserve(64);}static void trace(void* c,int,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(l.r.size()<l.r.capacity());l.r.push_back({outlet,m});}};
static void drain(Runtime& rt){std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;assert(allocations==0);}
static Definition gate(double outlets,double initial){Definition d;d.op=Op::gate;d.arguments={outlets,initial};return d;}
int main(){
    // gate 2 1: initially outlet 1 (index 0) open; closes on 0; any message
    // shape passes through unchanged; selection 2 routes to the second outlet.
    {Log log;Symbols sy;const Symbol go=sy.intern("go");Runtime rt(std::vector<Definition>{gate(2,1)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,1,Message::integer(7)));{Message a=Message::anything(go);a.count=1;a.atoms[0]=Atom::real(1.5);assert(rt.send(0,1,a));}
     assert(rt.send(0,0,Message::integer(0)));assert(rt.send(0,1,Message::integer(8)));
     assert(rt.send(0,0,Message::integer(2)));assert(rt.send(0,1,Message{}));
     drain(rt);assert(!rt.faulted());
     assert(log.r.size()==3);
     assert(log.r[0].outlet==0 && log.r[0].m.atoms[0].value.integer==7);
     assert(log.r[1].outlet==0 && log.r[1].m.kind==Message::Kind::anything && log.r[1].m.selector==go);
     assert(log.r[2].outlet==1 && log.r[2].m.kind==Message::Kind::bang);}
    // gate 1 0: closed until opened; a float selection truncates.
    {Log log;Symbols sy;Runtime rt(std::vector<Definition>{gate(1,0)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,1,Message::integer(1)));assert(rt.send(0,0,Message::number(1.9)));assert(rt.send(0,1,Message::integer(2)));
     drain(rt);assert(!rt.faulted());assert(log.r.size()==1 && log.r[0].m.atoms[0].value.integer==2);}
    // Measured in Live 12.4.5: a selection above the outlet count clamps to
    // the top outlet. Negatives fault; bad preparation arguments are rejected.
    {Log log;Symbols sy;Runtime rt(std::vector<Definition>{gate(2,0)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,0,Message::integer(5)));assert(rt.send(0,1,Message{}));drain(rt);assert(!rt.faulted());
     assert(log.r.size()==1 && log.r[0].outlet==1);
     assert(rt.send(0,0,Message::integer(-1)));drain(rt);assert(rt.faulted());
     for(auto bad:{gate(0,0),gate(2,3),gate(300,0)}){bool f=false;try{Runtime r2(std::vector<Definition>{bad},std::vector<Edge>{},48000);}catch(const std::invalid_argument&){f=true;}assert(f);}}
    std::cout<<"PASS: gate selection/close/pass-through of any message shape, initial state, float truncation, above-range CLAMP (measured in Live), negative fault, preparation rejection, no render allocations. Zero-selection close is documented, not measured.\n";
}
