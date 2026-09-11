// loudness~: BS.1770-4 K-weighted measurement. The standard's own check: a
// 997 Hz sine at -20 dBFS (amplitude 0.1) in one channel reads -23.0 LUFS
// (momentary, short-term and integrated) within 0.1 LU; true peak -20 dBTP.
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
struct Rec {int outlet;double v;};
struct Log {std::vector<Rec> r;Log(){r.reserve(8192);}static void t(void* c,int,int o,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(l.r.size()<l.r.capacity());l.r.push_back({o,m.atoms[0].number()});}};
int main(){
    const double sr=48000;
    Definition in;in.op=Op::input;Definition lm;lm.op=Op::loudness;lm.arguments={2,100};Definition out;out.op=Op::output;
    Symbols sy;Log log;Runtime rt(std::vector<Definition>{in,lm,out},std::vector<Edge>{{0,0,1,0},{0,1,1,1},{0,0,2,0},{0,1,2,1}},sr,sy,Log::t,&log);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};uint64_t t=0;
    for(int b=0;b<3750;++b){for(int i=0;i<64;++i){l[size_t(i)]=float(0.1*std::sin(2*M_PI*997*double(t++)/sr));}rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);}   // 5 s
    auto last=[&](int outlet)->double{for(size_t i=log.r.size();i-->0;)if(log.r[i].outlet==outlet)return log.r[i].v;return NAN;};
    std::cout<<"momentary "<<last(0)<<" short "<<last(1)<<" integrated "<<last(2)<<" range "<<last(3)<<" peak "<<last(5)<<"\n";
    assert(std::abs(last(0)+23)<0.1 && std::abs(last(1)+23)<0.1 && std::abs(last(2)+23)<0.1);
    assert(std::abs(last(5)+20)<0.1 && last(3)<0.5);
    assert(!rt.faulted());
    std::cout<<"PASS: loudness~ BS.1770 -23 LUFS check tone, true peak -20 dBTP, zero render allocations\n";
    return 0;
}
