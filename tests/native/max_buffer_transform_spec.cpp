#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p)noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
int main(int argc,char** argv){
    assert(argc==2);std::ifstream file(argv[1]);int cases;file>>cases;assert(file && cases==20);
    size_t checked=0;
    for(int test=0;test<cases;++test){
        int frames,channels;double value;file>>frames>>channels>>value;
        std::vector<std::vector<double>> before(channels,std::vector<double>(frames)),after=before;
        for(auto* phase:{&before,&after})for(auto& channel:*phase)for(auto& sample:channel)file>>sample;assert(file);
        for(double rate:{44100.,48000.,96000.}){
            Symbols symbols;const auto name=symbols.intern("window"),fill=symbols.intern("fill"),apply=symbols.intern("apply"),hanning=symbols.intern("hanning");
            Definition buffer;buffer.op=Op::buffer;buffer.arguments={double(frames),double(channels)};buffer.atoms={Atom::named(name)};
            Definition set;set.op=Op::loadmess;set.atoms={Atom::named(fill),Atom::real(value)};
            Definition window;window.op=Op::loadmess;window.atoms={Atom::named(apply),Atom::named(hanning)};
            Runtime filled({buffer,set},{{1,0,0,0}},rate,symbols);
            // Native load order is reverse serialized order: fill, then apply.
            Runtime shaped({buffer,window,set},{{1,0,0,0},{2,0,0,0}},rate,symbols);
            const auto a=filled.externalBuffer("window"),b=shaped.externalBuffer("window");assert(a && b);
            for(int ch=0;ch<channels;++ch)for(int n=0;n<frames;++n){
                assert(a->peek(n,ch)==before[ch][n]);
                if(b->peek(n,ch)!=after[ch][n]){std::cerr<<"Hanning mismatch "<<test<<" "<<n<<" "<<b->peek(n,ch)<<" "<<after[ch][n]<<"\n";return 1;}
                checked+=2;
            }
            auto change=Message::anything(fill);change.count=1;change.atoms[0]=Atom::real(.125);
            assert(shaped.send(0,0,change));
            float zero[1]={},output[1]={};callback=true;shaped.render(zero,zero,output,output,0);callback=false;
            assert(shaped.faulted()); // Never run a whole-buffer transform in DSP.
            for(int ch=0;ch<channels;++ch)for(int n=0;n<frames;++n)assert(b->peek(n,ch)==after[ch][n]);
        }
    }
    m4l::gen::Table empty(0,0,true);assert(fillPreparedBuffer(empty,1));hanningPreparedBuffer(empty);
    assert(!fillPreparedBuffer(empty,1e100));assert(allocations==0);
    std::cout<<"PASS: "<<checked<<" exact original Max fill/Hanning values at three rates, preparation order, periodic window endpoints, mono/stereo, live-transform containment, no callback allocations\n";
}
