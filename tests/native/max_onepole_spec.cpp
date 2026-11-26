// onepole~: MEASURED in Live 12.4.5 / Max 9.0.10 by the batch4
// probe (line~ step into [onepole~ 100], snapshot~ at 1/3/10/30/100 ms):
// 0.0 / 0.62584 / 0.99542 / 1.0 / 1.0 at 44.1 kHz, tau = 1.5900 ms against the
// textbook 1/(2*pi*100) = 1.5915 ms. That fixes a1 = exp(-2*pi*fc/SR) and
// y = (1-a1)*x + a1*y1. The probe's fitted step start was 1.437 ms after its
// trigger; this spec drives the step from sample 0 and checks the same
// response at the same offsets relative to the step.
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
    const double sr=44100;
    Definition in;in.op=Op::input; Definition op;op.op=Op::onePole;op.arguments={100}; Definition out;out.op=Op::output;
    Symbols sy;
    Runtime rt(std::vector<Definition>{in,op,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},sr,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};
    std::vector<double> y;y.reserve(8192);
    // Unit step from sample 0, rendered as float blocks (the host path).
    for(int b=0;b<80;++b){l.fill(1.f);r.fill(0.f);rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);for(float v:ol)y.push_back(v);}
    const double a1=std::exp(-2*M_PI*100/sr);
    // Closed form of the recurrence for a unit step: y[n] = 1 - a1^(n+1).
    for(size_t n=0;n<y.size();n+=97)assert(std::abs(y[n]-(1-std::pow(a1,double(n+1))))<2e-6);
    // Live's readings, each taken (t - 1.437 ms) after the step began. The
    // 1.437 ms origin is itself fitted from two readings, so the comparison
    // is held to 1%; the exact identity above is the a1 assertion.
    struct R{double ms,value;} readings[]={{3,0.62584},{10,0.99542},{30,1.0},{100,1.0}};
    for(const auto& rd:readings){
        const size_t n=size_t(std::llround((rd.ms-1.437)*sr/1000.));assert(n<y.size());
        std::cout<<rd.ms<<" ms: model "<<y[n]<<" live "<<rd.value<<"\n";
        assert(std::abs(y[n]-rd.value)<1e-2);
    }
    // Right inlet float retunes the cutoff; a signal there is not modelled.
    assert(rt.send(1,1,Message::number(1000)));
    assert(!rt.faulted());
    {
        // MEASURED (Live, September 11): a bare onepole~ passes 0.98759 of a
        // unit step after 700 ms (a1 = 0.99985783, fc = 0.998 Hz): the default
        // cutoff is 1 Hz, not 0.
        Definition bare=op;bare.arguments={};
        Runtime b(std::vector<Definition>{in,bare,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},44100,sy);
        b.setDSPActive(true);
        std::array<float,64> one{},l{},r{};one.fill(1);double last=0;
        for(int t=0;t<int(44100*0.7);t+=64){b.render(one.data(),one.data(),l.data(),r.data(),64);last=l[63];}
        std::cout<<"bare onepole~ 700 ms: model "<<last<<" live 0.98759\n";
        assert(std::abs(last-0.98759)<2e-3 && !b.faulted());
        bool rejected=false;try{Definition bad=op;bad.arguments={1,2};Runtime c(std::vector<Definition>{in,bad,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},sr,sy);}catch(const std::invalid_argument&){rejected=true;}
        assert(rejected);
    }
    std::cout<<"PASS: onepole~ matches the measured Live step response (a1=exp(-2*pi*fc/SR)), closed-form recurrence, cutoff retune, measured 1 Hz bare default, argument validation, zero render allocations\n";
    return 0;
}
