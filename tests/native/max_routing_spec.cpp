#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
struct Capture {
    std::array<Message,512> events{};size_t count=0;
    static void receive(void* context,int source,int,uint64_t,const Message& m) noexcept {
        if(source!=0)return;auto& self=*static_cast<Capture*>(context);assert(self.count<self.events.size());self.events[self.count++]=m;
    }
};
Definition named(Op op,Symbol name) {Definition d;d.op=op;d.atoms={Atom::named(name)};return d;}
int main() {
    auto domain=std::make_shared<RoutingDomain>();Symbols a,b;
    a.intern("only-sender");const auto channelA=a.intern("bus"),payloadA=a.intern("payload");
    const auto channelB=b.intern("bus");b.intern("only-receiver");
    Capture capture;
    Runtime sender({named(Op::namedSend,channelA)}, {},48000,a,nullptr,nullptr,{},domain);
    auto receiver=std::make_unique<Runtime>(std::vector<Definition>{named(Op::namedReceive,channelB)},std::vector<Edge>{},48000,b,Capture::receive,&capture,std::vector<int>{},domain);
    domain->prepare();sender.initialize();receiver->initialize();
    auto message=Message::anything(payloadA);message.count=3;message.atoms[0]=Atom::integral(9007199254740993LL);message.atoms[1]=Atom::real(.25);message.atoms[2]=Atom::named(payloadA);
    assert(sender.send(0,0,message));float l[8]{},r[8]{};callback=true;sender.render(nullptr,nullptr,l,r,0);callback=false;
    assert(capture.count==1 && receiver->symbols().name(capture.events[0].selector)=="payload");
    assert(capture.events[0].atoms[0].value.integer==9007199254740993LL && capture.events[0].atoms[1].value.floating==.25);
    assert(receiver->symbols().name(capture.events[0].atoms[2].value.symbol)=="payload");
    assert(!receiver->send(0,0,Message{})); // A named receive has no inlet.
    assert(sender.send(0,0,Message::anything(sym::set)));callback=true;sender.render(nullptr,nullptr,l,r,0);callback=false;
    assert(capture.count==2 && capture.events[1].selector==sym::set); // set is forwarded, never a sender rename.
    receiver.reset();assert(sender.send(0,0,Message::number(3)));callback=true;sender.render(nullptr,nullptr,l,r,0);callback=false;
    assert(!sender.faulted() && capture.count==2);

    // A receiver in a later-created graph exists before the sender's loadmess.
    auto startup=std::make_shared<RoutingDomain>();Symbols names;auto bus=names.intern("startup");
    Definition load;load.op=Op::loadmess;load.atoms={Atom::integral(37)};
    Runtime source({load,named(Op::namedSend,bus)},{{0,0,1,0}},48000,names,nullptr,nullptr,{},startup);
    Capture loaded;Runtime sink({named(Op::namedReceive,bus)}, {},48000,names,Capture::receive,&loaded,{},startup);
    startup->prepare();source.initialize();sink.initialize();assert(loaded.count==1 && loaded.events[0].atoms[0].value.integer==37);

    // Cross-graph feedback shares the initiating dispatch budget and depth.
    auto looping=std::make_shared<RoutingDomain>();auto x=names.intern("x"),y=names.intern("y");
    Runtime first({named(Op::namedReceive,x),named(Op::namedSend,y)},{{0,0,1,0}},48000,names,nullptr,nullptr,{},looping);
    Runtime second({named(Op::namedReceive,y),named(Op::namedSend,x)},{{0,0,1,0}},48000,names,nullptr,nullptr,{},looping);
    looping->prepare();first.initialize();second.initialize();assert(first.send(1,0,Message::integer(1)));
    callback=true;first.render(nullptr,nullptr,l,r,8);callback=false;
    assert(first.faulted() && second.faulted());for(auto value:l)assert(value==0);
    assert(allocations==0);
    std::cout<<"PASS: named cross-graph delivery, exact Int64/symbol translation, later-created receivers at initialization, detach, no receive inlet, sender set forwarding, bounded cross-graph recursion, zero callback allocations.\n";
}
