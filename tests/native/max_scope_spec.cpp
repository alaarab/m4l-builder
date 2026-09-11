// scope~ (X/Y point frames) and spectroscope~ (hann magnitude frames) publish
// display data under a seqlock for the host renderer. Point reduction (the
// current sample every calccount) and the 2/N magnitude scale follow the
// runtime's stated model; neither is measured against Max's drawing.
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
    Definition in;in.op=Op::input;Definition sc;sc.op=Op::scope;sc.arguments={0,4,8,1024,50};   // 4 points, one every 8 samples
    Definition sp;sp.op=Op::scope;sp.arguments={1,128,256,64,8};                                  // spectroscope~ 64-point FFT every 8 ms (64 samples)
    Definition out;out.op=Op::output;
    Symbols sy;Runtime rt(std::vector<Definition>{in,sc,sp,out},std::vector<Edge>{{0,0,1,0},{0,1,1,1},{0,0,2,0},{0,0,3,0},{0,1,3,1}},sr,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};
    for(int i=0;i<64;++i){l[size_t(i)]=float(i);r[size_t(i)]=float(-i);}
    rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);
    std::array<float,64> frame{};
    // Two frames fit in 64 samples; the latest (points at samples 39, 47, 55, 63) is published.
    assert(rt.scopeFrame(1,frame.data(),frame.size())==8);
    assert(frame[0]==39 && frame[1]==-39 && frame[2]==47 && frame[3]==-47 && frame[6]==63 && frame[7]==-63);
    // Spectroscope: a 1 kHz tone at 8 kHz over a 64-point FFT lands on bin 8 with amplitude ~1 (2/N scaling, hann coherent gain 0.5 -> 0.5).
    for(int b=0;b<8;++b){for(int i=0;i<64;++i){l[size_t(i)]=float(std::sin(2*M_PI*1000*double(b*64+i)/sr));}rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;}
    assert(rt.scopeFrame(2,frame.data(),frame.size())==32);
    int peak=0;for(int i=1;i<32;++i)if(frame[size_t(i)]>frame[size_t(peak)])peak=i;
    assert(peak==8 && std::abs(frame[8]-0.5)<0.02);
    assert(rt.scopeFrame(0,frame.data(),frame.size())==0);   // not a scope
    assert(!rt.faulted());
    std::cout<<"PASS: scope~ point frames, spectroscope~ hann magnitude frames, seqlock reads, zero render allocations\n";
    return 0;
}
