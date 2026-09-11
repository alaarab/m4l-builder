#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
struct Event {std::string operation;int object,outlet;std::string type;double value;};
struct Capture {
    std::vector<Event> reference;size_t cursor=0;const char* operation="";
    static void trace(void* context,int node,int outlet,uint64_t,const Message& message) noexcept {
        auto& c=*static_cast<Capture*>(context);assert(c.cursor<c.reference.size());
        const auto& e=c.reference[c.cursor++];assert(e.operation==c.operation && e.object==node && e.outlet==outlet && message.count==1);
        assert(message.atoms[0].type==(e.type=="int"?Atom::Type::integer:Atom::Type::floating));
        assert(message.atoms[0].number()==e.value);
    }
};
int main(int argc,char** argv){
    assert(argc==2);std::ifstream input(argv[1]);double rate;int vector,io;input>>rate>>vector>>io;assert(input && vector==64);
    Capture c;Event event;while(input>>event.operation>>event.object>>event.outlet>>event.type>>event.value)c.reference.push_back(event);
    assert(c.reference.size()==32);
    Definition state;state.op=Op::dspState;
    Definition zero;zero.op=Op::signal;zero.arguments={0};
    Runtime runtime({state,state,zero},{{2,0,1,0}},rate,{},Capture::trace,&c,{}, {},io);
    auto bang=[&](const char* operation){c.operation=operation;for(int node:{0,1}){assert(runtime.send(node,0,Message{}));runtime.render(nullptr,nullptr,nullptr,nullptr,0);}};
    callback=true;
    bang("off.bang");c.operation="on.automatic";assert(runtime.setDSPActive(true));
    assert(runtime.setDSPActive(true)); // No duplicate on notification.
    bang("on.bang");runtime.setDeviceEnabled(false);runtime.setDeviceEnabled(true);
    c.operation="off.automatic";assert(runtime.setDSPActive(false));assert(runtime.setDSPActive(false));
    bang("off.bang.after");callback=false;
    assert(c.cursor==32 && !runtime.faulted());
    // Lifecycle messages drive actual sample output through original cords.
    Definition signal;signal.op=Op::signal;signal.arguments={-1};Definition output;output.op=Op::output;
    Runtime feedback({state,signal,signal,output},{{0,1,1,0},{0,0,2,0},{1,0,3,0},{2,0,3,1}},48000,{},nullptr,nullptr,{}, {},128);
    std::array<float,128> left{},right{};
    callback=true;assert(feedback.setDSPActive(true));feedback.render(nullptr,nullptr,left.data(),right.data(),128);
    for(size_t i=0;i<left.size();++i){assert(left[i]==48000 && right[i]==1);}
    feedback.setDeviceEnabled(false);feedback.render(nullptr,nullptr,left.data(),right.data(),128);
    assert(right[0]==1); // Graph-only adapter does not own bypass routing.
    assert(feedback.setDSPActive(false));feedback.render(nullptr,nullptr,left.data(),right.data(),128);
    for(float value:right)assert(value==0);
    assert(feedback.setDSPActive(true));feedback.render(nullptr,nullptr,left.data(),right.data(),128);
    assert(right[0]==1 && !feedback.faulted());callback=false;
    for(int badIO:{0,-1,65537}){bool rejected=false;try{Runtime bad({state},{},48000,{},nullptr,nullptr,{}, {},badIO);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);}
    assert(allocations==0);
    std::cout<<"PASS: full runtime matches all 32 captured Max messages, typed reverse object/outlet ordering, engine restart, bypass independence, original-cord PCM feedback, invalid I/O rejection and zero callback allocations.\n";
}
