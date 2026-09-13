#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <thread>

static thread_local bool inCallback=false;
static thread_local size_t allocations=0,deallocations=0;
void* operator new(std::size_t n) {if(inCallback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t n) {return ::operator new(n);}
void operator delete(void* p) noexcept {if(inCallback && p)++deallocations;std::free(p);}
void operator delete[](void* p) noexcept {::operator delete(p);}
void operator delete(void* p,std::size_t) noexcept {::operator delete(p);}
void operator delete[](void* p,std::size_t) noexcept {::operator delete(p);}
void* operator new(std::size_t n,std::align_val_t alignment) {
    if(inCallback)++allocations;void* p=nullptr;
    if(posix_memalign(&p,size_t(alignment),n?n:1)==0)return p;throw std::bad_alloc();
}
void* operator new[](std::size_t n,std::align_val_t alignment) {return ::operator new(n,alignment);}
void operator delete(void* p,std::align_val_t) noexcept {::operator delete(p);}
void operator delete[](void* p,std::align_val_t) noexcept {::operator delete(p);}
void operator delete(void* p,std::size_t,std::align_val_t) noexcept {::operator delete(p);}
void operator delete[](void* p,std::size_t,std::align_val_t) noexcept {::operator delete(p);}

using namespace m4l::maxcompat;
static unsigned failures=0;
static void check(bool value,const char* why) {if(!value){++failures;std::fprintf(stderr,"FAIL: %s\n",why);}}
static Definition signal(double value) {Definition d;d.op=Op::signal;d.arguments={value};return d;}
static Definition output() {Definition d;d.op=Op::output;return d;}

int main() {
    // Positive allocation/free controls execute through volatile pointers, so
    // optimization cannot remove the calls being audited.
    void* (*volatile allocate)(size_t)=::operator new;
    void (*volatile release)(void*) noexcept=::operator delete;
    inCallback=true;void* probe=allocate(33);release(probe);inCallback=false;
    check(allocations==1 && deallocations==1,"callback audit positive controls");
    allocations=deallocations=0;
    for(double rate:{32000.,44100.,48000.,96000.}) {
        // Intermediate output sums may exceed float range and cancel. Preserve
        // the final mixed-output validation boundary and its existing audio.
        Runtime cancel({signal(1e300),output(),signal(-1e300),output()},
            {{0,0,1,0},{0,0,1,1},{2,0,3,0},{2,0,3,1}},rate);
        std::array<float,64> left{},right{};
        inCallback=true;cancel.render(nullptr,nullptr,left.data(),right.data(),64);inCallback=false;
        check(!cancel.faulted(),"finite cancellation must not become a new fault");
        for(size_t i=0;i<left.size();++i)check(left[i]==0 && right[i]==0,"cancellation remains exact silence");
        for(double value:{1e300,1e308}) {
            Runtime overflow({signal(value),output(),signal(value),output()},
                {{0,0,1,0},{0,0,1,1},{2,0,3,0},{2,0,3,1}},rate);
            inCallback=true;overflow.render(nullptr,nullptr,left.data(),right.data(),64);inCallback=false;
            const auto description=overflow.faultDescription();
            std::printf("%.0f Hz mixed output: %s\n",rate,description.c_str());
            check(overflow.faulted(),"out-of-range/nonfinite final output must fault");
            check(description.find("mixed stereo output")!=std::string::npos,"mixed output boundary must be attributed");
            check(description.find("node 1")!=std::string::npos && description.find("node 3")!=std::string::npos,
                  "mixed output attribution must identify both sinks without inventing an upstream cause");
            for(size_t i=0;i<left.size();++i)check(left[i]==0 && right[i]==0,"invalid output remains muted");
        }
    }
    check(allocations==0 && deallocations==0,"render faults cannot allocate or free");

    {
        auto graph=std::make_shared<m4l::gen::GraphDefinition>();
        m4l::gen::NodeDefinition input,code,out;
        input.kind=m4l::gen::NodeDefinition::Kind::input;
        code.code="out1=exp(in1);";out.kind=m4l::gen::NodeDefinition::Kind::output;
        graph->nodes={input,code,out};graph->edges={{0,0,1,0},{1,0,2,0}};
        Definition gen;gen.op=Op::gen;gen.genGraph=graph;
        Runtime runtime({signal(1000),gen,output()},{{0,0,1,0},{1,0,2,0},{1,0,2,1}},48000);
        std::array<float,64> l{},r{};
        inCallback=true;runtime.render(nullptr,nullptr,l.data(),r.data(),64);inCallback=false;
        const auto first=runtime.faultDescription();
        check(runtime.faulted() && first.find("node 1")!=std::string::npos && first.find("during signal rendering")!=std::string::npos,
              "Gen signal faults name the render node");
        inCallback=true;runtime.render(nullptr,nullptr,nullptr,nullptr,-1);inCallback=false;
        check(runtime.faultDescription()==first,"later host errors cannot overwrite the first fault");
    }
    {
        Definition input;input.op=Op::input;
        Definition snapshot;snapshot.op=Op::signalSnapshot;snapshot.arguments={1,0,1};
        Runtime runtime({input,snapshot,output()},{{0,0,1,0}},48000);
        std::array<float,128> inputValues{},l{},r{};inputValues.fill(std::numeric_limits<float>::infinity());
        inCallback=true;runtime.render(inputValues.data(),nullptr,l.data(),r.data(),128);inCallback=false;
        const auto why=runtime.faultDescription();
        check(runtime.faulted() && why.find("node 1")!=std::string::npos && why.find("outlet 0")!=std::string::npos,
              "invalid snapshot messages name the originating outlet");
    }
    {
        Runtime runtime({signal(0),output()},{{0,0,1,0}},48000);
        inCallback=true;runtime.render(nullptr,nullptr,nullptr,nullptr,1);inCallback=false;
        check(runtime.faulted() && runtime.faultDescription().find("host render contract")!=std::string::npos,
              "invalid host buffers report the host contract, not an arbitrary device node");
    }
    check(allocations==0 && deallocations==0,"signal/outlet/host fault publication cannot allocate or free");

    // Exercise control-thread diagnostic reads while the renderer publishes a
    // node fault. TSan must see coherent, race-free first-fault publication.
    for(int pass=0;pass<64;++pass) {
        Definition db;db.op=Op::dbtoa;
        Runtime runtime({db,signal(0),output()},{{0,0,1,0},{1,0,2,0},{1,0,2,1}},48000);
        check(runtime.send(0,0,Message::number(1e300)),"prepare overflow message");
        std::atomic<bool> start{false},done{false};std::atomic<size_t> callbackAllocations{0},callbackFrees{0};
        std::thread renderer([&]{
            while(!start.load(std::memory_order_acquire))std::this_thread::yield();
            std::array<float,64> l{},r{};inCallback=true;
            runtime.render(nullptr,nullptr,l.data(),r.data(),64);inCallback=false;
            callbackAllocations=allocations;callbackFrees=deallocations;
            done.store(true,std::memory_order_release);
        });
        start.store(true,std::memory_order_release);
        do {auto description=runtime.faultDescription();(void)description;} while(!done.load(std::memory_order_acquire));
        renderer.join();
        const auto description=runtime.faultDescription();
        check(runtime.faulted() && description.find("node 0")!=std::string::npos && description.find("message kind")!=std::string::npos,
              "first message fault keeps its node and message attribution");
        check(callbackAllocations==0 && callbackFrees==0,"concurrent fault publication cannot allocate or free");
    }
    std::printf("%s: mixed-output boundary, cancellation, 64 concurrent diagnostic reads, callback audit; %u failures\n",failures?"FAIL":"PASS",failures);
    return failures?1:0;
}
