// pfft~ against Live 12.4.5 captures (max4liveplugins probes):
//  * bare [fftin~ 1] -> [fftout~ 1] passthrough at 2048/4 and 2048/2 is unity
//    and delayed by one frame (size, not size-hop);
//  * [cycle~ 1000] into 2048/4 with [fftin~ 1] -> [cartopol~] -> [poke~] gives
//    bins 44..49 = 13.2456 103.5768 451.2097 416.4506 71.5603 11.2583 and
//    bin 0 = 0.00093: periodic hann analysis window, raw unnormalised sum.
// One subpatch instance sees every frame (MEASURED: 172 frames per 2 s at 2048/4, 44.1 k).
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
static std::shared_ptr<SpectralDefinition> passthrough(int size,int overlap) {
    auto spec=std::make_shared<SpectralDefinition>();spec->size=size;spec->overlap=overlap;spec->inlets=1;spec->outlets=1;
    Definition in;in.op=Op::fftIn;in.arguments={0,double(SpectralWindow::hanning)};
    Definition out;out.op=Op::fftOut;out.arguments={0,double(SpectralWindow::hanning)};
    spec->definitions={in,out};spec->edges={{0,0,1,0},{0,1,1,1}};
    return spec;
}
static void step_test(int overlap) {
    const double sr=44100;const int size=2048;
    Definition in;in.op=Op::input;Definition p;p.op=Op::pfft;p.spectral=passthrough(size,overlap);Definition out;out.op=Op::output;
    Symbols sy;Runtime rt(std::vector<Definition>{in,p,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},sr,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};std::vector<double> y;y.reserve(16384);
    for(int b=0;b<160;++b) {l.fill(1.f);r.fill(0.f);rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);for(float v:ol)y.push_back(v);}
    assert(!rt.faulted());
    // Live snapshots (ms): 40 -> ~2e-4 (still inside the first frame), 60 -> 0.9998, 120/200 -> 1.0
    auto at=[&](double ms){return y[size_t(ms*sr/1000.)];};
    std::cout<<"overlap "<<overlap<<": 40ms "<<at(40)<<" 60ms "<<at(60)<<" 120ms "<<at(120)<<" 200ms "<<at(200)<<"\n";
    assert(std::abs(at(40))<1e-3 && std::abs(at(60)-1)<1e-3 && std::abs(at(120)-1)<1e-6 && std::abs(at(200)-1)<1e-6);
    // One frame of latency exactly: nothing before sample `size`, unity from the first fully overlapped sample on.
    for(int i=0;i<size;++i)assert(std::abs(y[size_t(i)])<1e-9 || i>=size-1);
    for(size_t i=size_t(2*size);i<y.size();++i)assert(std::abs(y[i]-1)<1e-9);
}
static void bin_test() {
    const double sr=44100;const int size=2048;
    auto spec=std::make_shared<SpectralDefinition>();spec->size=size;spec->overlap=4;spec->inlets=1;spec->outlets=1;
    Symbols sy;const Symbol buf=sy.intern("dump");
    Definition in;in.op=Op::fftIn;in.arguments={0,double(SpectralWindow::hanning)};
    Definition cp;cp.op=Op::cartopol;
    Definition pk;pk.op=Op::poke;pk.atoms={Atom::named(buf)};
    Definition out;out.op=Op::fftOut;out.arguments={0,double(SpectralWindow::hanning)};
    spec->definitions={in,cp,pk,out};spec->edges={{0,0,1,0},{0,1,1,1},{1,0,2,0},{0,2,2,1},{0,0,3,0},{0,1,3,1}};
    Definition buffer;buffer.op=Op::buffer;buffer.atoms={Atom::named(buf)};buffer.arguments={double(size),1};
    Definition pin;pin.op=Op::input;Definition p;p.op=Op::pfft;p.spectral=spec;Definition pout;pout.op=Op::output;
    Runtime rt(std::vector<Definition>{buffer,pin,p,pout},std::vector<Edge>{{1,0,2,0},{2,0,3,0},{2,0,3,1}},sr,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};uint64_t t=0;
    for(int b=0;b<200;++b) {for(int i=0;i<64;++i){l[size_t(i)]=float(std::cos(2*M_PI*1000*double(t++)/sr));}r.fill(0.f);rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);}
    assert(!rt.faulted());
    auto table=rt.externalBuffer("dump");assert(table);
    const double live[]={13.2456,103.5768,451.2097,416.4506,71.5603,11.2583};
    for(int k=0;k<6;++k) {
        const double v=table->peek(44+k,0);std::cout<<"bin "<<44+k<<": "<<v<<" live "<<live[k]<<"\n";
        // The Live tone's phase at frame start is unknown; magnitudes of a
        // hann-windowed steady tone are phase-invariant to ~1e-2 here.
        assert(std::abs(v-live[k])<1e-3*live[k]+1e-3);
    }
    assert(table->peek(1024,0)<1e-6 && table->peek(0,0)<0.01);
}
// poly~ single-voice wrapper: in~ 1 owns the mute group; 'mute 1 1' silences
// and freezes the voice (here the pfft~ inside it), 'mute 1 0' resumes.
static void poly_mute_test() {
    const double sr=44100;
    Definition in;in.op=Op::input;
    Definition pin;pin.op=Op::polyIn;pin.arguments={0,3,4};   // port 0, group = pfft (3) and out~ (4)
    Definition p;p.op=Op::pfft;p.spectral=passthrough(256,4);
    Definition pout;pout.op=Op::polyOut;pout.arguments={0};
    Definition out;out.op=Op::output;
    // indices: 0 input, 1 out~? keep order: 0 input, 1 polyIn, 2 output, 3 pfft, 4 polyOut
    Symbols sy;const Symbol muteSym=sy.intern("mute"),targetSym=sy.intern("target");   // interned before construction
    Runtime rt(std::vector<Definition>{in,pin,out,p,pout},std::vector<Edge>{{0,0,1,0},{1,0,3,0},{3,0,4,0},{4,0,2,0},{4,0,2,1}},sr,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};
    auto run=[&](int blocks){double last=0;for(int b=0;b<blocks;++b){l.fill(1.f);r.fill(0.f);rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;last=ol[63];}return last;};
    assert(std::abs(run(20)-1)<1e-9);
    Message m=Message::anything(muteSym);m.count=2;m.atoms[0]=Atom::integral(1);m.atoms[1]=Atom::integral(1);
    assert(rt.send(1,0,m));
    assert(run(4)==0);
    m.atoms[1]=Atom::integral(0);assert(rt.send(1,0,m));
    assert(std::abs(run(20)-1)<1e-9);assert(!rt.faulted());
    Message bad=Message::anything(targetSym);bad.count=1;bad.atoms[0]=Atom::integral(1);
    assert(rt.send(1,0,bad));run(1);assert(rt.faulted());
}
int main() {
    step_test(4);step_test(2);bin_test();poly_mute_test();
    // Construction rejects a non-power-of-two frame and an overlap that does not divide it.
    bool rejected=false;
    try{Definition in;in.op=Op::input;Definition p;p.op=Op::pfft;p.spectral=passthrough(1000,4);Definition out;out.op=Op::output;Symbols sy;Runtime r(std::vector<Definition>{in,p,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0}},44100,sy);}catch(const std::invalid_argument&){rejected=true;}
    assert(rejected);
    std::cout<<"PASS: pfft~ unity/one-frame-latency passthrough at overlap 4 and 2, hann raw-sum bin magnitudes against Live, poke~/cartopol~ inside the frame, zero render allocations\n";
    return 0;
}
