#include "../../src/m4l_builder/native/max_compat/genexpr.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::gen;
int main(int argc,char** argv) {
    assert(argc==2);std::ifstream reference(argv[1]);assert(reference.good());
    Noise n(std::array<uint64_t,4>{1,2,3,4});double expected;unsigned count=0;
    while(reference>>expected){assert(n.next()==expected);++count;}assert(count==256);
    // Multiple call sites share the graph stream, branches consume only when
    // executed, and reset does not rewind the global Gen noise sequence.
    auto stream=std::make_shared<Noise>(12345);Noise oracle(12345);
    Expression a("History held(0);if(in1){held=noise();}out1=held;out2=noise();",48000,{},false,{},8388608,true,nullptr,8388608,stream);
    Expression b("out1=noise();",48000,{},false,{},8388608,true,nullptr,8388608,stream);
    assert(!a.outputInfo(1).constant && !a.outputInfo(1).integer);
    double input[1]{},out[2]{},held=0;
    for(int i=0;i<10000;++i){
        input[0]=i%3==0;if(input[0])held=oracle.next();double next=oracle.next();
        callback=true;assert(a.process(input,out));callback=false;
        assert(out[0]==held && out[1]==next);
        next=oracle.next();callback=true;assert(b.process(input,out));callback=false;assert(out[0]==next);
        if(i%100==0){callback=true;a.reset();callback=false;held=0;}
    }
    Noise first(42),second(43);double sum=0,square=0;bool differs=false;
    callback=true;
    for(int i=0;i<100000;++i){const double v=first.next();assert(v>=-1 && v<1);sum+=v;square+=v*v;differs|=v!=second.next();}
    callback=false;assert(differs && std::abs(sum/100000)<.01 && std::abs(square/100000-1./3)<.01);
    for(const char* source:{"out1=noise(1);","out1=noise(in1);"}) {
        bool rejected=false;try{Expression bad(source,48000);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    }
    bool rejected=false;try{Noise bad(std::array<uint64_t,4>{});}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    assert(allocations==0);std::cout<<"PASS: 256 upstream reference values, conditional/shared stream, reset continuity, independent seeds, bounds, moments, no callback allocation.\n";
}
