#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
int main(){
    for(double rate:{44100.,48000.,96000.}){
        Definition state;state.op=Op::dspState;Definition expr;expr.op=Op::expression;expr.expression="int($f1 * 0.02 + 0.5) + (3)";expr.arguments={1};
        Definition input;input.op=Op::input;Definition output;output.op=Op::output;Definition observe;observe.op=Op::external;observe.arguments={1,0};
        Runtime runtime({state,expr,input,output,observe},{{0,1,1,0},{1,0,4,0},{2,0,3,0},{2,1,3,1}},rate);
        Runtime::ExternalEvent event;assert(runtime.popExternal(event) && event.inlet==-1);assert(!runtime.popExternal(event));
        std::array<float,256> in{},left{},right{};for(size_t i=0;i<in.size();++i)in[i]=float(i)/1024;
        callback=true;
        for(bool active:{true,false,true}){
            assert(runtime.setDSPActive(active));assert(runtime.popExternal(event));assert(event.node==4 && event.message.kind==Message::Kind::integer);
            assert(event.message.atoms[0].value.integer==int64_t(rate*.02+.5)+3);assert(!runtime.popExternal(event));
            runtime.render(in.data(),in.data(),left.data(),right.data(),256);assert(left==in && right==in);
        }
        callback=false;assert(!runtime.faulted());
        expr.expression="$f1 + $f2";expr.arguments={1};bool rejected=false;
        try{Runtime invalid({expr},{},rate);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    }
    assert(allocations==0);
    std::cout<<"PASS: original DSP-state/expr latency cords at three rates, typed lifecycle output, untouched stereo PCM, malformed port rejection and zero render allocations.\n";
}
