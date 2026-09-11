#include "../../src/m4l_builder/native/max_compat/dsp_state.hpp"
#include <array>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
#include <vector>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
struct Event {std::string operation;int object,outlet;std::string type;double value;};
int main(int argc,char** argv){
    assert(argc==2);std::ifstream input(argv[1]);double rate;int vector,io;input>>rate>>vector>>io;assert(input);
    std::vector<Event> reference;Event row;
    while(input>>row.operation>>row.object>>row.outlet>>row.type>>row.value)reference.push_back(row);
    assert(reference.size()==32);
    std::array<DSPState,2> subjects{DSPState(rate,io,vector),DSPState(rate,io,vector)};
    size_t cursor=0;
    auto perform=[&](const char* operation,int object,int action){
        auto emit=[&](int outlet,const Message& message)noexcept{
            assert(cursor<reference.size());const auto& expected=reference[cursor++];
            assert(expected.operation==operation && expected.object==object && expected.outlet==outlet);
            assert(message.count==1);
            const auto& atom=message.atoms[0];
            if(expected.type=="int"){assert(atom.type==Atom::Type::integer);assert(double(atom.value.integer)==expected.value);}
            else {assert(atom.type==Atom::Type::floating);assert(atom.value.floating==expected.value);}
        };
        callback=true;
        if(action<0)subjects[object].bang(emit);else subjects[object].setActive(action!=0,emit);
        callback=false;
    };
    for(int object:{0,1})perform("off.bang",object,-1);
    for(int object:{1,0})perform("on.automatic",object,1);
    for(int object:{0,1})perform("on.bang",object,-1);
    for(int object:{1,0})perform("off.automatic",object,0);
    for(int object:{0,1})perform("off.bang.after",object,-1);
    assert(cursor==reference.size());
    for(double preparedRate:{44100.,48000.,96000.})for(int preparedIO:{64,128,256,512}){
        DSPState state(preparedRate,preparedIO);std::array<double,4> output{};size_t count=0;
        auto emit=[&](int outlet,const Message& message)noexcept{++count;const auto& a=message.atoms[0];output[outlet]=a.type==Atom::Type::integer?double(a.value.integer):a.value.floating;};
        callback=true;state.bang(emit);assert(count==4 && output[0]==0 && output[1]==preparedRate && output[2]==preparedIO && output[3]==preparedIO);
        state.setActive(true,emit);assert(count==8 && output[0]==1 && output[2]==64);
        state.setActive(false,emit);assert(count==12 && output[0]==0);state.bang(emit);assert(count==12);callback=false;
    }
    for(const auto& config:std::array<std::array<double,3>,4>{{{0,128,64},{48000,0,64},{48000,128,0},{48000,65537,64}}}){
        bool rejected=false;try{DSPState invalid(config[0],int(config[1]),int(config[2]));}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    }
    assert(allocations==0);
    std::cout<<"PASS: 32 exact original Max DSP-state messages, typed reverse outlet order, initial/off/on distinction, independent objects, prepared rates/vectors, no callback allocation. Host integration remains separate.\n";
}
