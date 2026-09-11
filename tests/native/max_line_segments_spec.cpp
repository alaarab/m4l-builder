// line~ list contract (Max reference): "target time" pairs are consecutive
// segments; an odd list of three or more atoms first jumps to its leading
// value (Linear Phase EQ V2 sends "x 1. 20" and "0. 30"). A single float
// ramps over the right-inlet time. Segment timing itself is the existing
// rounded-sample model; the pair/odd parsing is the documented contract,
// NOT a Live capture.
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
int main(){
    Definition line;line.op=Op::line;Definition out;out.op=Op::output;
    Symbols sy;Runtime rt(std::vector<Definition>{line,out},std::vector<Edge>{{0,0,1,0},{0,0,1,1}},8000,sy);   // 8 kHz: 8 samples per ms
    rt.setDSPActive(true);
    std::array<float,64> ol{},orr{};std::vector<double> y;
    auto run=[&](int blocks){for(int b=0;b<blocks;++b){rendering=true;rt.render(nullptr,nullptr,ol.data(),orr.data(),64);rendering=false;assert(allocations==0);for(float v:ol)y.push_back(v);}};
    // "0.5 1. 20": jump to 0.5, then ramp to 1 over 20 samples.
    Atom a[3]={Atom::real(0.5),Atom::real(1.),Atom::integral(20)};
    assert(rt.send(0,0,Message::sequence(a,3)));run(4);
    assert(y[0]==0.5 && std::abs(y[80]-0.75)<1e-9 && std::abs(y[160]-1)<1e-9 && y[200]==1);
    // "0. 30 1. 10": two consecutive segments.
    y.clear();Atom b[4]={Atom::real(0.),Atom::integral(30),Atom::real(1.),Atom::integral(10)};
    assert(rt.send(0,0,Message::sequence(b,4)));run(6);
    assert(std::abs(y[120]-0.5)<1e-9 && std::abs(y[240]-0)<1e-9 && std::abs(y[280]-0.5)<1e-9 && std::abs(y[320]-1)<1e-9 && y[383]==1);
    // A lone float ramps over the right-inlet time.
    y.clear();assert(rt.send(0,1,Message::integer(10)));assert(rt.send(0,0,Message::number(0.)));run(2);
    assert(std::abs(y[40]-0.5)<1e-9 && y[80]==0);
    // An even-length remainder that is not pairs faults visibly.
    Atom c[2]={Atom::real(1.),Atom::real(1.)};Atom d[5]={Atom::real(0),Atom::real(1),Atom::real(2),Atom::real(3),Atom::real(4)};(void)c;
    assert(!rt.faulted());assert(rt.send(0,0,Message::sequence(d,5)));run(1);assert(!rt.faulted());   // odd 5: jump + two pairs
    Atom e[4]={Atom::real(0),Atom::real(1),Atom::real(2),Atom::real(3)};assert(rt.send(0,0,Message::sequence(e,4)));run(1);assert(!rt.faulted());
    std::cout<<"PASS: line~ jump+segment lists, consecutive pairs, single-float ramp time, zero render allocations\n";
    return 0;
}
