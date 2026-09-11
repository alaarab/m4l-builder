// filtercoeff~ -> biquad~ (RBJ cookbook coefficients, Max's biquad~ sign
// convention), /~, abs~ and send~/receive~ pairing. The cookbook is a stated
// model; Max's filtergraph~ formulas are NOT yet measured.
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
static double rms(const std::vector<double>& y,size_t from){double s=0;for(size_t i=from;i<y.size();++i)s+=y[i]*y[i];return std::sqrt(s/double(y.size()-from));}
int main(){
    const double sr=44100;
    Symbols sy;const Symbol bus=sy.intern("bus"),lowpass=sy.intern("lowpass"),clear=sy.intern("clear");
    Definition in;in.op=Op::input;
    Definition fc;fc.op=Op::filterCoeff;fc.arguments={1,1};   // highpass, every sample
    Definition bq;bq.op=Op::biquad;
    Definition send;send.op=Op::sendSignal;send.atoms={Atom::named(bus)};
    Definition recv;recv.op=Op::receiveSignal;recv.atoms={Atom::named(bus)};
    Definition ab;ab.op=Op::absSignal;Definition dv;dv.op=Op::divideSignal;dv.arguments={};
    Definition out;out.op=Op::output;
    // input -> biquad (coeffs from filtercoeff~) -> send~ ; receive~ -> abs~ -> /~ (by 2) -> output L ; biquad -> output R
    Runtime rt(std::vector<Definition>{in,fc,bq,send,recv,ab,dv,out},
        std::vector<Edge>{{0,0,2,0},{1,0,2,1},{1,1,2,2},{1,2,2,3},{1,3,2,4},{1,4,2,5},{2,0,3,0},{4,0,5,0},{5,0,6,0},{6,0,7,0},{2,0,7,1}},sr,sy);
    rt.setDSPActive(true);
    assert(rt.send(1,0,Message::number(1000)));assert(rt.send(1,1,Message::number(1)));assert(rt.send(1,2,Message::number(0.7071)));assert(rt.send(6,1,Message::number(2)));
    std::array<float,64> l{},r{},ol{},orr{};std::vector<double> left,right;uint64_t t=0;
    auto run=[&](double hz,int blocks){left.clear();right.clear();for(int b=0;b<blocks;++b){for(int i=0;i<64;++i)l[size_t(i)]=float(std::sin(2*M_PI*hz*double(t++)/sr));rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);for(int i=0;i<64;++i){left.push_back(ol[size_t(i)]);right.push_back(orr[size_t(i)]);}}};
    // Highpass at 1 kHz: 100 Hz is attenuated by ~40 dB, 10 kHz passes near unity.
    run(100,200);const double low=rms(right,4096);
    run(10000,200);const double high=rms(right,4096);
    std::cout<<"hp 100 Hz "<<low<<" 10 kHz "<<high<<"\n";
    assert(low<0.02 && std::abs(high-0.7071)<0.03);
    // receive~ repeats send~; abs~ then /~ 2: left equals |right|/2.
    for(size_t i=0;i<left.size();++i)assert(std::abs(left[i]-std::abs(right[i])/2)<1e-6);
    // Switching type by message: lowpass now passes 100 Hz.
    assert(rt.send(1,0,Message::anything(lowpass)));assert(rt.send(2,0,Message::anything(clear)));run(100,200);
    assert(std::abs(rms(right,4096)-0.7071)<0.03);
    assert(!rt.faulted());
    // Live 12.4.5 capture (max4liveplugins): [filtercoeff~ peaknotch] freq 1000, gain 2 (linear), Q 1 at 44.1 k.
    Definition pk;pk.op=Op::filterCoeff;pk.arguments={4,1};Definition o2;o2.op=Op::output;
    Runtime r2(std::vector<Definition>{pk,o2},std::vector<Edge>{},sr,sy);r2.setDSPActive(true);
    assert(r2.send(0,0,Message::number(1000)));assert(r2.send(0,1,Message::number(2)));assert(r2.send(0,2,Message::number(1)));
    rendering=true;r2.render(nullptr,nullptr,ol.data(),orr.data(),64);rendering=false;
    const double live[5]={1.0478028,-1.8850982,0.8565918,-1.8850982,0.9043945};
    for(int k=0;k<5;++k){const double v=r2.debugOutput(0,k);assert(std::abs(v-live[k])<2e-7);}
    std::cout<<"PASS: filtercoeff~ highpass/lowpass through biquad~, Live peaknotch coefficient row, send~/receive~ bus, abs~, /~, zero render allocations\n";
    return 0;
}
