// tapin~/tapout~ delay line with feedback through the link, and rand~. The
// one-vector minimum delay (64 samples: Live runs M4L at sigvs 64, MEASURED)
// and whole-sample truncation of fractional delays (MEASURED September 11:
// 10.5 ms -> 463 samples at 44.1 kHz, a single sample of amplitude exactly 1).
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
    const double sr=8000;
    Definition in;in.op=Op::input;Definition tin;tin.op=Op::tapIn;tin.arguments={100};Definition tout;tout.op=Op::tapOut;tout.arguments={25};
    Definition mul;mul.op=Op::multiply;mul.arguments={0.5};Definition add;add.op=Op::add;Definition out;out.op=Op::output;
    // input -> add -> tapin ; tapin -> tapout ; tapout -> mul -> add (feedback) ; tapout -> output
    Symbols sy;Runtime rt(std::vector<Definition>{in,tin,tout,mul,add,out},
        std::vector<Edge>{{0,0,4,0},{4,0,1,0},{1,0,2,0},{2,0,3,0},{3,0,4,1},{2,0,5,0},{2,0,5,1}},sr,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};std::vector<double> y;
    auto render=[&](int blocks){for(int b=0;b<blocks;++b){rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);for(float v:ol)y.push_back(v);l.fill(0.f);}};
    l[0]=1.f;render(16);   // 1024 samples; 25 ms at 8 kHz = 200 samples
    assert(std::abs(y[200]-1)<1e-9 && std::abs(y[400]-0.5)<1e-9 && std::abs(y[600]-0.25)<1e-9);
    for(int i=0;i<200;++i)assert(y[size_t(i)]==0);
    for(int i=201;i<400;++i)assert(std::abs(y[size_t(i)])<1e-9);
    // A float below one vector clamps to 64 samples.
    assert(rt.send(2,0,Message::number(1)));y.clear();l[0]=1.f;render(4);
    assert(std::abs(y[64]-1)<1e-9 || std::abs(y[64+0]-1)<1e-9);
    assert(!rt.faulted());
    {
        // Measured Live case: tapin~ -> tapout~ 10.5 at 44.1 kHz, impulse at
        // index 10 -> a single 1.0 at index 473 (463 whole samples), no split.
        Definition tin2;tin2.op=Op::tapIn;tin2.arguments={100};Definition tout2;tout2.op=Op::tapOut;tout2.arguments={10.5};
        Runtime t(std::vector<Definition>{in,tin2,tout2,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{2,0,3,0},{2,0,3,1}},44100,sy);
        t.setDSPActive(true);std::vector<double> w;
        std::array<float,64> il{},ir{},a{},b{};il[10]=1.f;
        for(int blk=0;blk<12;++blk){rendering=true;t.render(il.data(),ir.data(),a.data(),b.data(),64);rendering=false;for(float v:a)w.push_back(v);il.fill(0.f);}
        for(size_t i=0;i<w.size();++i)assert(i==473?std::abs(w[i]-1)<1e-9:w[i]==0);
        assert(!t.faulted());
    }
    // rand~ 100 at 8 kHz: a new target every 80 samples, linear in between, within [-1,1).
    Definition rnd;rnd.op=Op::randSignal;rnd.arguments={100};Definition o2;o2.op=Op::output;
    Runtime r2(std::vector<Definition>{rnd,o2},std::vector<Edge>{{0,0,1,0},{0,0,1,1}},sr,sy);r2.setDSPActive(true);
    std::vector<double> z;for(int b=0;b<10;++b){rendering=true;r2.render(nullptr,nullptr,ol.data(),orr.data(),64);rendering=false;for(float v:ol)z.push_back(v);}
    for(double v:z)assert(v>=-1 && v<=1);
    bool linear=true;for(size_t i=2;i<160;++i)if(i%80>1 && std::abs((z[i]-z[i-1])-(z[i-1]-z[i-2]))>1e-6)linear=false;
    assert(linear);assert(!r2.faulted());
    std::cout<<"PASS: tapin~/tapout~ feedback delay (25 ms, 0.5 regeneration), one-vector minimum, measured whole-sample truncation (10.5 ms -> 463), rand~ linear segments, zero render allocations\n";
    return 0;
}
