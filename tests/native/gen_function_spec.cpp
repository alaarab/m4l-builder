#include "../../src/m4l_builder/native/max_compat/genexpr.hpp"
#include <array>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <new>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p)noexcept{::operator delete(p);}
using namespace m4l::gen;
int main(int argc,char** argv){
    assert(argc==9);
    for(int index=1;index<argc;index+=2){
        std::ifstream source(argv[index]);std::string code((std::istreambuf_iterator<char>(source)),{});
        std::ifstream reference(argv[index+1]);double rate;size_t frames;reference>>rate>>frames;assert(reference && frames==2048);
        struct Sample{std::array<double,2> input;std::array<double,8> output;};
        std::vector<Sample> samples(frames);for(auto& s:samples){for(auto& v:s.input)reference>>v;for(auto& v:s.output)reference>>v;}assert(reference);
        Expression first(code,rate),independent(code,rate);std::array<double,64> output{};
        for(int repeat=0;repeat<2;++repeat){
            callback=true;first.reset();callback=false;
            for(size_t frame=0;frame<frames;++frame){
                callback=true;assert(first.process(samples[frame].input.data(),output.data()));callback=false;
                for(size_t c=0;c<8;++c){
                    if(double(float(output[c]))!=samples[frame].output[c]){
                        std::cerr<<argv[index]<<": frame "<<frame<<" channel "<<c<<" actual "<<output[c]<<" expected "<<samples[frame].output[c]<<"\n";return 1;
                    }
                }
            }
        }
        callback=true;assert(independent.process(samples[0].input.data(),output.data()));callback=false;
        for(size_t c=0;c<8;++c)assert(double(float(output[c]))==samples[0].output[c]);
    }
    for(const char* code:{
        "f(x){return x;}a,b=f(in1);out1=a;",
        "f(x){if(x){return x,x;}else{return x;}}out1=f(in1);",
        "f(t){t=1;return 0;}Data d(4);out1=f(d);",
        "Data d(4);out1=sin(d);",
        "f(d){return d;}Delay d(4);out1=f(d);",
        "f(x){return x,x;}a,b=f(in1)+1;out1=a;",
        "continue;out1=0;",
        "f(x){continue;return x;}for(i=0;i<2;i+=1){out1=f(in1);}",
        "Data d(8);out1=peek(d,in1,index=\"wave\");"
    }){bool rejected=false;try{Expression bad(code,48000);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);}
    assert(allocations==0);
    Expression runaway("out1=0;for(i=0;i<10;i+=1){if(i==2){continue;}out1+=i;}",48000);
    double zero[64]={};callback=true;assert(!runaway.process(zero,zero));callback=false;assert(zero[0]==0 && allocations==0);
    std::cout<<"PASS: 65536 exact original Max tuple/storage/phase/continue outputs plus reset repeats, scalar first-result selection, nested calls/loops, independent histories/tables/delays, storage mutation visibility, phase endpoints/channel offsets, Max continue semantics, runaway containment, instance isolation, unsupported arity/types, zero callback allocations\n";
}
