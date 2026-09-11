#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
static bool callback=false;static size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;
int main(int argc,char** argv) {
    assert(argc==2);std::ifstream reference(argv[1]);assert(reference);
    int cases;reference>>cases;size_t samples=0,exact=0;double worst=0;
    for(int c=0;c<cases;++c) {
        double rate,ramp;int count,initial,step,signal,commands,frames;
        reference>>rate>>count>>initial>>ramp>>step>>signal>>commands>>frames;
        Definition sig;sig.op=Op::signal;
        Definition selector;selector.op=Op::signalSelector;selector.arguments={double(count),double(initial),ramp,double(step)};
        Definition output;output.op=Op::output;
        std::vector<Edge> edges={{1,0,3,1},{3,0,4,0},{3,0,4,1}};
        if(count==2)edges.push_back({2,0,3,2});
        if(signal)edges.push_back({0,0,3,0});
        Runtime runtime({sig,sig,sig,selector,output},edges,rate);
        for(int i=0;i<commands;++i) {
            int kind;double value;reference>>kind>>value;
            assert(runtime.send(3,0,kind?Message{}:Message::number(value)));
        }
        for(int i=0;i<frames;++i) {
            double control,a,b,want;reference>>control>>a>>b>>want;
            assert(reference);
            callback=true;
            assert(runtime.send(0,0,Message::number(control)));
            assert(runtime.send(1,0,Message::number(a)));
            assert(runtime.send(2,0,Message::number(b)));
            float l,r;runtime.render(nullptr,nullptr,&l,&r,1);
            callback=false;
            const auto error=std::abs(double(l)-float(want));worst=std::max(worst,error);
            if(l==float(want))++exact;
            if(error>1e-14 || r!=l || runtime.faulted()) {
                std::cerr<<"Case "<<c<<" frame "<<i<<": "<<l<<" expected "<<want<<"\n";return 1;
            }
            ++samples;
        }
    }
    // Native plan validation must reject malformed dynamic-port definitions
    // before allocation or patch-cord access.
    for(const auto& args:std::vector<std::vector<double>>{{},{0,0,0,0},{64,0,0,0},{2,3,0,0},{2,0,-1,0},{2,0,0,2}}) {
        Definition d;d.op=Op::signalSelector;d.arguments=args;bool rejected=false;
        try{Runtime runtime({d},{},48000);}catch(const std::invalid_argument&){rejected=true;}
        assert(rejected);
    }
    assert(allocations==0);
    std::cout<<"PASS "<<cases<<" Max reference cases, "<<samples<<" stereo samples, "<<exact<<" exact, max absolute error "<<worst<<"; zero callback allocations\n";
}
