#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <thread>

static thread_local bool rendering=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n) {if(rendering)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n) {return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;

int main() {
    Definition input;input.op=Op::input;
    Definition output;output.op=Op::output;
    Definition external;external.op=Op::external;external.arguments={2,2};
    Definition multiply;multiply.op=Op::multiply;multiply.arguments={0};
    for(double rate:{44100.,48000.,96000.}) {
        auto runtime=std::make_unique<Runtime>(std::vector<Definition>{input,output,external,multiply},
            std::vector<Edge>{{0,0,3,0},{2,1,3,1},{3,0,1,0}},rate);
        Runtime::ExternalEvent event;
        assert(runtime->popExternal(event) && event.node==2 && event.inlet==-1);
        assert(!runtime->popExternal(event));
        float in=0.5f,l=0,r=0;
        for(int i=0;i<2000;++i) {
            assert(runtime->send(2,1,Message::number(double(i)/4000)));
            rendering=true;runtime->render(&in,nullptr,&l,&r,1);rendering=false;
            assert(runtime->popExternal(event) && event.inlet==1 && event.sample==uint64_t(i));
            assert(event.message.atoms[0].number()==double(i)/4000);
            assert(runtime->externalOutput(2,1,event.message));
            rendering=true;runtime->render(nullptr,nullptr,nullptr,nullptr,0);rendering=false;
        }
        assert(!runtime->faulted() && allocations==0);
        for(int i=0;i<255;++i)assert(runtime->externalOutput(2,1,Message::number(0.25)));
        assert(!runtime->externalOutput(2,1,Message::number(1)));
        assert(!runtime->externalOutput(2,2,Message::number(1)));
        assert(!runtime->externalOutput(3,0,Message::number(1)));
        runtime->render(&in,nullptr,&l,&r,1);assert(l==0.125f);
        for(int i=0;i<255;++i)assert(runtime->send(2,0,Message::integer(i)));
        runtime->render(nullptr,nullptr,nullptr,nullptr,0);
        assert(runtime->send(2,0,Message::integer(256)));
        runtime->render(nullptr,nullptr,nullptr,nullptr,0);
        assert(runtime->faulted()); // Never silently drop a script input.
    }
    // A control UI feeds a parameter whose silent setter feeds the UI back.
    // External queues break synchronous recursion; DSP still sees the value.
    Definition dial;dial.op=Op::dial;dial.minimum=0;dial.maximum=1;
    auto feedback=std::make_unique<Runtime>(std::vector<Definition>{external,dial},std::vector<Edge>{{0,0,1,0},{1,0,0,0}},48000.);
    Runtime::ExternalEvent event;while(feedback->popExternal(event)){}
    assert(feedback->externalOutput(0,0,Message::number(.75)));
    rendering=true;feedback->render(nullptr,nullptr,nullptr,nullptr,0);rendering=false;
    assert(feedback->popExternal(event) && event.node==0 && event.message.atoms[0].number()==.75);
    assert(!feedback->popExternal(event) && !feedback->faulted() && allocations==0);
    Definition deferred;deferred.op=Op::deferlow;
    auto pipeline=std::make_unique<Runtime>(std::vector<Definition>{external,deferred,deferred,external},
        std::vector<Edge>{{0,0,1,0},{1,0,2,0},{2,0,3,1}},48000.);
    assert(pipeline->controlWorkPending());
    while(pipeline->popExternal(event)){}
    assert(!pipeline->controlWorkPending());
    assert(pipeline->externalOutput(0,0,Message::number(.75)));
    for(int pass=0;pass<3;++pass) {
        assert(pipeline->controlWorkPending());
        rendering=true;pipeline->render(nullptr,nullptr,nullptr,nullptr,0);rendering=false;
        if(pass<2)assert(!pipeline->popExternal(event));
    }
    assert(pipeline->popExternal(event) && event.node==3 && event.inlet==1 && event.message.atoms[0].number()==.75);
    assert(!pipeline->controlWorkPending() && !pipeline->faulted() && allocations==0);
    // Native presentation attributes must use the same bounded deferred queue
    // as scripts. They cannot alter the widget's musical parameter or PCM.
    Symbols colors;const auto color=colors.intern("activefgdialcolor");
    Definition ui=dial;ui.presentation=true;ui.initial=.625;
    Definition meter;meter.op=Op::meter;meter.presentation=true;
    Definition panel;panel.op=Op::decoration;panel.presentation=true;
    auto presentation=std::make_unique<Runtime>(std::vector<Definition>{input,output,external,ui,meter,panel},
        std::vector<Edge>{{0,0,1,0},{0,1,1,1},{0,0,4,0},{2,0,3,0},{2,0,4,0},{2,0,5,0}},48000,colors);
    while(presentation->popExternal(event)){}
    auto rgba=Message::list({Atom::real(-.25),Atom::real(1.25),Atom::real(.375),Atom::real(.75)});
    rgba.kind=Message::Kind::anything;rgba.selector=color;
    float left=.25f,right=-.375f,outL=0,outR=0;
    for(int i=0;i<2000;++i) {
        assert(presentation->externalOutput(2,0,rgba));
        rendering=true;presentation->render(&left,&right,&outL,&outR,1);rendering=false;
        assert(outL==left && outR==right);
        for(int node:{3,4,5}) {
            assert(presentation->popExternal(event) && event.node==node && event.inlet==0);
            assert(event.sample==uint64_t(i) && event.message.selector==color && event.message.count==4);
            for(int c=0;c<4;++c)assert(event.message.atoms[c].number()==rgba.atoms[c].number());
        }
        assert(!presentation->popExternal(event) && !presentation->faulted());
    }
    // Attribute bursts cannot silently lose changes when the UI stops draining.
    for(int i=0;i<86;++i)assert(presentation->externalOutput(2,0,rgba));
    rendering=true;presentation->render(nullptr,nullptr,nullptr,nullptr,0);rendering=false;
    assert(presentation->faulted() && allocations==0);
    std::cout<<"External control queues: 6000 timed script events and 6000 RGBA events, bounded overflow, native meter/decoration routing, unchanged PCM, deferred idle detection, zero render allocations\n";
}
