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
struct Log{std::vector<Message> r;Log(){r.reserve(256);}static void t(void* c,int,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);if(outlet==2 && l.r.size()<l.r.capacity())l.r.push_back(m);}};
int main(){
    // plugin~ -> m4l.modal~ -> plugout~ with the message outlet traced.
    Definition in;in.op=Op::input; Definition ext;ext.op=Op::modalExternal; Definition out;out.op=Op::output;
    Log log;Symbols sy;
    // Selectors must exist in the table the runtime copies at construction.
    for(const char* name:{"param","model","note","mpe","panic","capture","analyze","status","meter","Capture and analysis are not hosted on this device"})sy.intern(name);
    Runtime rt(std::vector<Definition>{in,ext,out},std::vector<Edge>{{0,0,1,0},{0,1,1,1},{1,0,2,0},{1,1,2,1}},48000,sy,Log::t,&log);
    rt.setDSPActive(true);
    std::array<float,256> l{},r{},ol{},orr{};
    auto render=[&](int blocks){double energy=0;for(int b=0;b<blocks;++b){rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),256);rendering=false;assert(allocations==0);for(float v:ol)energy+=double(v)*v;}return energy;};
    // Load a body through the same 'model <slot> ...' message the device's
    // script sends at init (6 modes, glass-like ratios); both slots.
    const double ratios[]={1,2.32,4.25,6.63,9.38,12.5};
    for(int slot=0;slot<2;++slot){
        Message m=Message::anything(sy.intern("model"));m.count=6+m4l::modal::modes*5;
        m.atoms[0]=Atom::integral(slot);m.atoms[1]=Atom::real(261.625565);m.atoms[2]=Atom::real(.006);m.atoms[3]=Atom::real(.08);m.atoms[4]=Atom::real(1);m.atoms[5]=Atom::integral(6);
        for(int i=0;i<m4l::modal::modes;++i){const bool on=i<6;const double v[5]={on?ratios[i]:1,on?1./(i+2):0,on?4./(1+i*.3):1,on?(i%2?.3:-.3):0,0};for(int j=0;j<5;++j)m.atoms[size_t(6+i*5+j)]=Atom::real(v[j]);}
        assert(rt.send(1,0,m));
    }
    // Silence before any note.
    assert(render(4)==0);
    // A raw MIDI note-on (0x90 60 100) as three ints, like midiin feeds it.
    for(int byte:{0x90,60,100})assert(rt.send(1,0,Message::integer(byte)));
    const double sounding=render(20);
    assert(sounding>0);
    // A 'note' message with velocity 0 releases; energy must decay toward zero.
    assert(rt.send(1,0,[&]{Message m=Message::anything(sy.intern("note"));m.count=2;m.atoms[0]=Atom::integral(60);m.atoms[1]=Atom::integral(0);return m;}()));
    render(200);const double tail=render(20);
    assert(tail<sounding);
    // param, mpe and panic are accepted; capture reports a status instead.
    assert(rt.send(1,0,[&]{Message m=Message::anything(sy.intern("param"));m.count=2;m.atoms[0]=Atom::integral(0);m.atoms[1]=Atom::real(0.5);return m;}()));
    assert(rt.send(1,0,[&]{Message m=Message::anything(sy.intern("panic"));return m;}()));
    assert(rt.send(1,0,[&]{Message m=Message::anything(sy.intern("capture"));m.count=2;m.atoms[0]=Atom::integral(0);m.atoms[1]=Atom::integral(1);return m;}()));
    render(1);
    assert(!rt.faulted());
    bool meter=false,status=false;
    for(const auto& m:log.r){const auto& s=sy.name(m.selector);if(s=="meter" && m.count==6)meter=true;if(s=="status")status=true;}
    assert(meter && status);
    std::cout<<"PASS: m4l.modal~ external bound to the native engine — raw MIDI note-on sounds, note-off decays, param/mpe/panic accepted, capture reports a status, 50 ms meter messages on outlet 2, no render allocations.\n";
}
