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
struct Rec{int node,outlet;Message m;};
struct Log{std::vector<Rec> r;Log(){r.reserve(4096);}static void trace(void* c,int node,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);if(l.r.size()<l.r.capacity())l.r.push_back({node,outlet,m});}};
static void render(Runtime& rt,int frames){std::array<float,64> l{},r{};rendering=true;while(frames>0){int n=std::min(frames,64);rt.render(nullptr,nullptr,l.data(),r.data(),n);frames-=n;}rendering=false;assert(allocations==0);}
// Orbit's auto-map ring: live.text (toggle) -> [sel 1] -> [t b b] -> [i] -> [+ 1]
// -> [> 8] -> [sel 1] -> [0( -> live.text. The constant 0 re-enters the toggle,
// emits 0 and misses [sel 1], so the ring ends in Max; a ring whose constant
// re-matches the key is a true synchronous loop and stays rejected.
static std::vector<Definition> ring(Symbols& sy,int64_t off) {
    const Symbol on=sy.intern("ON"),offText=sy.intern("OFF"),bang=sy.intern("b");
    Definition text;text.op=Op::dial;text.parameterType=2;text.controlKind=2;text.minimum=0;text.maximum=1;text.parameterLabels={offText,on};text.textLabels={offText,on};text.presentation=true;
    Definition sel;sel.op=Op::select;sel.atoms={Atom::integral(1)};
    Definition trig;trig.op=Op::trigger;trig.atoms={Atom{},Atom{}};trig.formats={Format::bang,Format::bang};(void)bang;
    Definition integer;integer.op=Op::integer;integer.atoms={Atom::integral(1)};
    Definition plus;plus.op=Op::controlAdd;plus.arguments={1};
    Definition greater;greater.op=Op::compareGreater;greater.arguments={8};
    Definition done;done.op=Op::select;done.atoms={Atom::integral(1)};
    Definition message;message.op=Op::message;message.atoms={Atom::integral(off)};
    Definition reset;reset.op=Op::message;reset.atoms={Atom::integral(1)};
    return {text,sel,trig,integer,plus,greater,done,message,reset};
}
static std::vector<Edge> cords() {
    return {{0,0,1,0},{1,0,2,0},{2,0,3,0},{2,1,8,0},{8,0,3,1},{3,0,4,0},{4,0,3,1},{4,0,5,0},{5,0,6,0},{6,0,7,0},{7,0,0,0},{1,1,8,0}};
}
int main(){
    {
        Symbols sy;Log log;Runtime rt(ring(sy,0),cords(),48000,sy,Log::trace,&log);
        // Press: the toggle emits 1, the counter runs 1..9, [> 8] fires 1 once,
        // [0( switches the toggle off and the ring ends; no fault, no runaway.
        assert(rt.send(0,0,Message::integer(1)));render(rt,64);
        assert(!rt.faulted());
        assert(rt.parameterValue(0)==0.);
        size_t doneFires=0,textZero=0;
        for(const auto& e:log.r) {if(e.node==6 && e.outlet==0)++doneFires;if(e.node==0 && e.outlet==0 && e.m.isNumber() && e.m.atoms[0].number()==0)++textZero;}
        assert(doneFires==1 && textZero==1);
    }
    {
        // The same ring closing with [1( re-matches [sel 1]: rejected as a
        // synchronous loop naming the cycle, never run.
        Symbols sy;bool rejected=false;
        try {Runtime rt(ring(sy,1),cords(),48000,sy,nullptr,nullptr);} catch(const std::invalid_argument& e) {rejected=std::string(e.what()).find("Feedback")!=std::string::npos;}
        assert(rejected);
    }
    {
        // A right-inlet cord into the closing message box makes its content
        // dynamic: rejected too.
        Symbols sy;bool rejected=false;auto edges=cords();edges.push_back({5,0,7,1});
        try {Runtime rt(ring(sy,0),edges,48000,sy,nullptr,nullptr);} catch(const std::invalid_argument& e) {rejected=std::string(e.what()).find("Feedback")!=std::string::npos;}
        assert(rejected);
    }
    std::cout<<"PASS: static-number message ring through a live.text toggle and mismatched [sel] key terminates (Orbit auto-map), re-matching key and dynamic message content stay rejected.\n";
}
