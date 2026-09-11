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
struct Trace {
    std::array<std::array<double,512>,4> values{};std::array<int,4> counts{};
    static void receive(void* p,int node,int outlet,uint64_t sample,const Message& m) noexcept {
        if(node<1 || node>4)return;
        auto& t=*static_cast<Trace*>(p);assert(outlet==0 && m.kind==Message::Kind::floating);
        assert(sample%64==0);const int i=node-1;
        assert(t.counts[i]<512);t.values[i][t.counts[i]++]=m.atoms[0].number();
    }
};
int main(int argc,char** argv) {
    assert(argc==2);std::ifstream f(argv[1]);assert(f);int cases;f>>cases;size_t compared=0;
    for(int c=0;c<cases;++c) {
        double rate;int frames;f>>rate>>frames;
        std::array<double,4> intervals;for(auto& interval:intervals)f>>interval;
        std::array<std::vector<double>,4> reference;
        for(auto& events:reference){int n;f>>n;events.resize(n);for(auto& v:events)f>>v;}
        std::vector<float> expected(frames);for(auto& v:expected)f>>v;assert(f);
        Definition input;input.op=Op::input;
        Definition hold;hold.op=Op::signal;hold.arguments={-1};
        Definition output;output.op=Op::output;
        std::vector<Definition> definitions={input};
        for(auto interval:intervals){Definition d;d.op=Op::signalSnapshot;d.arguments={interval,0,1};definitions.push_back(d);}
        definitions.push_back(hold);definitions.push_back(output);
        std::vector<Edge> edges={{0,0,1,0},{0,0,2,0},{0,0,3,0},{0,0,4,0},{3,0,5,0},{5,0,6,0},{5,0,6,1}};
        // Different host callback sizes must retain the original MSP vector
        // boundaries, report values and signal feedback delay.
        for(int chunk:{1,31,64,127,256}) {
            Trace trace;Runtime runtime(definitions,edges,rate,{},Trace::receive,&trace);
            std::array<float,256> input{},l{},r{};
            for(int base=0;base<frames;base+=chunk) {
                const int n=std::min(chunk,frames-base);for(int i=0;i<n;++i)input[i]=float(base+i);
                callback=true;runtime.render(input.data(),nullptr,l.data(),r.data(),n);callback=false;
                assert(!runtime.faulted());
                for(int i=0;i<n;++i)if(l[i]!=expected[base+i] || l[i]!=r[i]) {
                    std::cerr<<"Case "<<c<<" callback "<<chunk<<" frame "<<base+i<<" got "<<l[i]<<" expected "<<expected[base+i]<<"\n";return 1;
                }
            }
            for(int i=0;i<4;++i) {
                assert(trace.counts[i]>=reference[i].size());
                for(size_t j=0;j<reference[i].size();++j)if(trace.values[i][j]!=reference[i][j]) {
                    std::cerr<<"Case "<<c<<" stream "<<i<<" event "<<j<<" got "<<trace.values[i][j]<<" expected "<<reference[i][j]<<"\n";return 1;
                }
                compared+=reference[i].size();
            }
        }
    }
    assert(allocations==0);
    std::cout<<"PASS "<<cases<<" Max snapshot captures, "<<compared<<" exact report values, five callback sizes, exact feedback PCM; zero callback allocations\n";
}
