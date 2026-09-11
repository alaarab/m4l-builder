#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <iostream>
#include <new>
#include <thread>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::gen;
int main() {
    for(double rate:{44100.,48000.,96000.}) {
        BufferRegistry registry;
        registry["a"]=std::make_shared<Table>(5,2,true);
        registry["b"]=std::make_shared<Table>(8,1,true);
        const std::string code="Buffer bus(\"a\");prior=peek(bus,in1,in2);poke(bus,prior+in3,in1,in2);out1=prior;out2=peek(bus,in1,in2);out3=dim(bus);out4=channels(bus);";
        Expression external(code,rate,{},false,{},8388608,true,&registry);
        Expression data("Data bus(5,2);prior=peek(bus,in1,in2);poke(bus,prior+in3,in1,in2);out1=prior;out2=peek(bus,in1,in2);",rate);
        double inputs[3]={0,0,.100000001},values[4]{};
        double expected=0;
        for(int n=0;n<4096;++n) {
            callback=true;assert(data.process(inputs,values));callback=false;
            assert(values[0]==expected);expected+=inputs[2];assert(values[1]==expected);
        }
        float floatExpected=0;
        for(int n=0;n<4096;++n) {
            callback=true;assert(external.process(inputs,values));callback=false;
            assert(values[0]==floatExpected);floatExpected=float(double(floatExpected)+inputs[2]);assert(values[1]==floatExpected);
            assert(values[2]==5 && values[3]==2);
        }
        callback=true;data.reset();assert(data.process(inputs,values));callback=false;assert(values[0]==0);
        // Buffer rebind/reset must not erase the external buffer or allocate.
        callback=true;assert(external.bindBuffer("bus",registry.at("b")));assert(external.process(inputs,values));callback=false;
        assert(values[0]==0 && values[2]==8 && values[3]==1);
        callback=true;external.reset();assert(external.process(inputs,values));callback=false;assert(values[0]==floatExpected && values[2]==5);
        callback=true;assert(external.bindBuffer("bus",nullptr));assert(external.process(inputs,values));callback=false;
        assert(values[0]==0 && values[1]==0 && values[2]==0 && values[3]==0);
    }
    Table table(5,2,true);table.poke(.25,0,0);table.poke(.75,0,1);
    // Default buffer~ has no allocated channels; Gen metadata/indexing must
    // distinguish it from an empty but explicitly mono buffer.
    for(size_t channels:{size_t(0),size_t(1),size_t(2)}) {
        BufferRegistry empty;empty["empty"]=std::make_shared<Table>(0,channels,true);
        Expression reader("Buffer b(\"empty\");out1=peek(b,0);out2=dim(b);out3=channels(b);",48000,{},false,{},8388608,true,&empty);
        double values[3]{};callback=true;assert(reader.process(nullptr,values));callback=false;
        assert(values[0]==0 && values[1]==0 && values[2]==double(channels));
    }
    for(double position:{-1.,-.99,-.5,-.0001,5.,1e300,double(NAN)})assert(table.peek(position,0)==0);
    assert(table.peek(.99,0)==.25 && table.peek(0,-.99)==.25 && table.peek(0,-1)==0 && table.peek(0,1.99)==.75);
    table.poke(2,-.99,0);assert(table.peek(0,0)==.25);
    table.poke(.5,0,-.5);assert(table.peek(0,0)==.5);
    // Host meter reads and audio writes share no mutable non-atomic sample.
    std::atomic<bool> done{false};
    std::thread reader([&]{while(!done.load()) {const auto value=table.peek(1,0);assert(std::isfinite(value) && value>=0 && value<=1);}});
    callback=true;for(int n=0;n<100000;++n)table.poke(double(n%2),1,0);callback=false;done=true;reader.join();
    // A session-wide named bus declared by a later device must resolve before
    // rendering. Instance-prefixed names are distinct keys in the same domain.
    {
        using namespace m4l::maxcompat;
        auto domain=std::make_shared<RoutingDomain>();
        auto definition=std::make_shared<GraphDefinition>();
        NodeDefinition expression;expression.code="Buffer shared;out1=peek(shared,0);";
        NodeDefinition output;output.kind=NodeDefinition::Kind::output;
        definition->nodes={expression,output};definition->edges={{0,0,1,0}};
        Definition gen;gen.op=Op::gen;gen.genGraph=definition;
        Definition out;out.op=Op::output;
        Runtime consumer({gen,out},{{0,0,1,0}},48000,Symbols{},nullptr,nullptr,{},domain);
        Symbols symbols;const auto name=symbols.intern("shared");
        Definition storage;storage.op=Op::buffer;storage.arguments={8,1};storage.atoms={Atom::named(name)};
        Runtime producer({storage,out},{},48000,std::move(symbols),nullptr,nullptr,{},domain);
        domain->prepare();consumer.initialize();producer.initialize();
        domain->buffers().at("shared")->poke(.375,0,0);
        float left=0,right=0;callback=true;consumer.render(nullptr,nullptr,&left,&right,1);callback=false;
        assert(left==.375 && right==0 && !consumer.faulted());
    }
    for(const std::string invalid:{"Data b(8);History b(0);out1=1;", "Data b(8);b=1;out1=1;",
        "Buffer b;out1=peek(b,0,0,interp=\"linear\");","Data b(in1);out1=1;", "Data b(8);out1=poke(b,1,0);"}) {
        bool rejected=false;try {Expression bad(invalid,48000);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    }
    assert(allocations==0);
    {
        // sample: linear interpolation, phase default spans frames-1 like the
        // measured peek phase mapping (sample's own mapping UNMEASURED),
        // samples index mode, zero out of range, channel truncation.
        Expression sampled("Data tab(4,2);for(i=0;i<4;i+=1){poke(tab,i+1,i,0);poke(tab,10*(i+1),i,1);}"
                           "out1=sample(tab,in1,0);out2=sample(tab,in1*3,in2,index=\"samples\");out3=sample(tab,in1,1,index=\"phase\");",48000);
        double inputs[2]={0,0},values[3]{};
        auto run=[&](double phase,double channel){inputs[0]=phase;inputs[1]=channel;callback=true;assert(sampled.process(inputs,values));callback=false;};
        run(0,0);assert(values[0]==1 && values[1]==1 && values[2]==10);
        run(1,0);assert(values[0]==4 && values[1]==4 && values[2]==40);
        run(.5,1);assert(values[0]==2.5 && values[1]==25 && values[2]==25);
        run(1./3,1.9);assert(std::abs(values[0]-2)<1e-12 && std::abs(values[1]-20)<1e-12);
        run(1.5,0);assert(values[0]==0 && values[1]==0 && values[2]==0);
        // Each neighbour is bound-checked independently (UNMEASURED): a
        // position just below 0 fades in from zero rather than reading 0.
        run(-.25,0);assert(values[0]==.25 && values[1]==.25);
        run(-1./3-1e-3,0);assert(values[0]==0 && values[1]==0);
        run(.5,2);assert(values[1]==0);
        run(2./3+1e-9,0);assert(std::abs(values[0]-3)<1e-6);
    }
    std::cout<<"PASS: Gen Data/Buffer precision, default indexing, sample interpolation, rebinding/reset/unbound storage, concurrent host reads, three rates, no render allocations.\n";
}
