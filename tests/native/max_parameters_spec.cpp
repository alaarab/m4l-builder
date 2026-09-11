#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;
struct Capture {
    struct Event {int dial,phase,outlet;double value;};
    std::array<Event,128> events{};size_t count=0;int phase=-1;
    static void trace(void* data,int source,int outlet,uint64_t,const Message& message) noexcept {
        auto& self=*static_cast<Capture*>(data);if(self.phase<0)return;
        assert(self.count<self.events.size() && message.kind==Message::Kind::floating && message.count==1);
        self.events[self.count++]={source,self.phase,source*2+outlet,message.atoms[0].number()};
    }
};
Message method(Symbol name,double value){auto m=Message::anything(name);m.count=1;m.atoms[0]=Atom::real(value);return m;}
int main(){
    std::vector<Definition> definitions(4);
    for(auto& d:definitions){d.op=Op::dial;d.minimum=0;d.maximum=1;d.initial=.5;d.initialize=true;}
    definitions[1].maximum=100;definitions[1].parameterExponent=2;
    definitions[2].parameterSteps=4;definitions[3]=definitions[1];definitions[3].parameterSteps=4;
    Capture capture;Runtime runtime(definitions,{},48000,Symbols(),Capture::trace,&capture);
    auto list=Message::number(.2);list.kind=Message::Kind::list;list.selector=sym::list;list.count=2;list.atoms[1]=Atom::real(.8);
    const std::array<Message,11> messages={Message::number(.25),method(sym::set,.75),Message{},Message::number(2),Message::number(-1),
        method(sym::rawfloat,.5),Message::anything(sym::outputvalue),Message::anything(sym::init),method(sym::assign,.625),Message{},list};
    std::array<double,44> states{};
    for(int dial=0;dial<4;++dial)for(int phase=0;phase<11;++phase){
        capture.phase=phase;assert(runtime.send(dial,0,messages[phase]));
        callback=true;runtime.render(nullptr,nullptr,nullptr,nullptr,0);callback=false;
        assert(!runtime.faulted() && allocations==0);states[dial*11+phase]=runtime.parameterValue(dial);
    }
    assert(capture.count==72);
    struct Cold {
        std::array<int,16> values{};size_t count=0;
        static void trace(void* data,int node,int,uint64_t,const Message& m) noexcept {
            if(node!=3)return;auto& c=*static_cast<Cold*>(data);assert(c.count<c.values.size());c.values[c.count++]=int(m.atoms[0].number());
        }
    } cold;
    Definition state;state.op=Op::integer;state.atoms={Atom::integral(0)};
    Definition flip;flip.op=Op::reverseSubtract;flip.atoms={Atom::integral(1)};
    Definition copy;copy.op=Op::trigger;copy.formats={Format::integer,Format::integer};copy.atoms={Atom::integral(0),Atom::integral(0)};
    Definition boundary;boundary.op=Op::boundary;
    const std::vector<Definition> nodes={state,flip,copy,boundary};
    Runtime feedback(nodes,{{0,0,1,0},{1,0,2,0},{2,1,0,1},{2,0,3,0}},48000,Symbols(),Cold::trace,&cold);
    for(int i=0;i<16;++i){assert(feedback.send(0,0,Message{}));callback=true;feedback.render(nullptr,nullptr,nullptr,nullptr,0);callback=false;assert(!feedback.faulted());}
    assert(cold.count==16 && allocations==0);
    bool rejected=false;try{Runtime invalid(nodes,{{0,0,1,0},{1,0,2,0},{2,1,0,0}},48000);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    std::cout<<std::setprecision(17)<<"{\"events\":[";
    for(size_t i=0;i<capture.count;++i){const auto& e=capture.events[i];if(i)std::cout<<',';
        std::cout<<"{\"test\":\"dial"<<e.dial<<'.'<<e.phase<<"\",\"outlet\":"<<e.outlet<<",\"selector\":\"float\",\"value\":"<<e.value<<'}';}
    std::cout<<"],\"state\":[";
    for(int i=0;i<44;++i){if(i)std::cout<<',';std::cout<<"{\"test\":\"dial"<<i/11<<'.'<<i%11<<"\",\"value\":["<<states[i]<<"]}";}
    std::cout<<"],\"coldFeedback\":[";
    for(size_t i=0;i<cold.count;++i){if(i)std::cout<<',';std::cout<<cold.values[i];}
    std::cout<<"],\"callbackAllocations\":"<<allocations<<"}\n";
}
