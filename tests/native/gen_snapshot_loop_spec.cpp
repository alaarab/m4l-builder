#include "../../src/m4l_builder/native/max_compat/genexpr.hpp"
#include "../../src/m4l_builder/native/max_compat/buffer_transform.hpp"
#include <cassert>
#include <chrono>
#include <fstream>
#include <iostream>
#include <new>
#include <sstream>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::gen;
static Expression expression(const std::string& source,bool optimize=true,const BufferRegistry* buffers=nullptr,double rate=48000) {
    return Expression(source,rate,{},false,{},8388608,true,buffers,8388608,std::make_shared<Noise>(123456),optimize);
}
static void compare(const std::string& source,size_t optimized) {
    auto fast=expression(source),slow=expression(source,false);assert(fast.snapshotLoopCount()==optimized);
    assert(slow.snapshotLoopCount()==0);
    for(int frame=0;frame<2048;++frame) {
        double input[]={std::sin(frame*.13),std::cos(frame*.19),double(frame%17)-2,double(frame%7)/2};
        double a[8]{},b[8]{};
        callback=true;assert(fast.process(input,a));assert(slow.process(input,b));callback=false;
        for(int ch=0;ch<fast.outputs();++ch)assert(a[ch]==b[ch]);
        if(frame==1000){fast.reset();slow.reset();}
    }
}
int main(int argc,char** argv) {
    assert(argc==2 || argc==4);
    const std::string source=R"GEN(
        Delay left(64);Delay right(128);Data table(32,3);
        left.write(in1);right.write(in2);limit=in3;age=77;
        for(i=-2;i<limit;i+=1){age=limit-i;poke(table,right.read(age),i,0);poke(table,left.read(age),i,2);}
        out1=peek(table,0,0);out2=peek(table,4,2);out3=i;out4=age;
        out5=peek(table,12,0);out6=left.read(2);out7=right.read(3);out8=peek(table,1,1);
    )GEN";
    compare(source,1);
    compare("Delay d(64);Data t(32,2);d.write(in1);limit=in3+in4;for(i=0;i<limit;i+=1){poke(t,d.read(3-i),i,in4);}out1=peek(t,0,0);out2=peek(t,2,1);out3=i;",1);
    compare("Delay d(64);Data t(32);d.write(in1);limit=in3;for(i=0;i<limit;i+=1){poke(t,d.read(12-i),i,0);poke(t,d.read(3-i),i,0);}out1=peek(t,0,0);out2=peek(t,2,0);",1);
    // Reject side effects and loop-carried dependencies; retain the ordinary VM.
    compare("History sum(0);Delay d(64);Data t(32);d.write(in1);for(i=0;i<8;i+=1){sum+=1;poke(t,d.read(8-i),i,0);}out1=sum;out2=peek(t,4,0);",0);
    compare("Delay d(64);Data t(32);d.write(in1);bound=8;for(i=0;i<bound;i+=1){poke(t,d.read(bound-i),i,0);bound-=1;}out1=bound;out2=peek(t,3,0);",0);
    compare("Delay d(64);Data t(32);d.write(in1);for(i=0;i<8;i+=1){poke(t,d.read(8-i),i,0);d.write(in2);}out1=peek(t,3,0);",0);
    compare("Delay d(64);Data t(32);d.write(in1);for(i=0;i<8;i+=1){poke(t,d.read(8-i)+peek(t,i-1,0),i,0);}out1=peek(t,3,0);",0);
    // Insufficient aggregate bulk work is a fault, never an unbounded fallback.
    auto bounded=expression("Delay d(64);Data t(32);for(i=0;i<32;i+=1){poke(t,d.read(32-i),i,0);}out1=peek(t,0,0);");
    double input[4]{},out[8]{};unsigned bulk=4;assert(!bounded.process(input,out,nullptr,&bulk));assert(out[0]==0);
    auto runaway=expression("value=0;for(i=0;i<1000000;i+=1){value+=in1;}out1=value;");
    assert(!runaway.process(input,out));assert(out[0]==0);
    if(argc==4) {
        std::ifstream program(argv[2]),reference(argv[3]);assert(program.good() && reference.good());
        const std::string code((std::istreambuf_iterator<char>(program)),{});auto original=expression(code,true,nullptr,44100);
        assert(original.snapshotLoopCount()>0);int frames,channels;reference>>frames>>channels;assert(frames>0 && channels<=8);
        for(int frame=0;frame<frames;++frame) {
            double values[8]{};for(int ch=0;ch<channels;++ch)reference>>values[ch];assert(reference.good());
            callback=true;assert(original.process(input,out));callback=false;
            for(int ch=0;ch<channels;++ch)if(float(out[ch])!=float(values[ch])) {
                std::cerr<<"Original snapshot mismatch frame "<<frame<<" ch "<<ch<<": native "<<out[ch]<<", Max "<<values[ch]<<"\n";return 1;
            }
        }
        std::cout<<"Original Max snapshot: "<<frames*channels<<" exact Float32 outputs.\n";
    }
    std::ifstream file(argv[1]);assert(file.good());const std::string original((std::istreambuf_iterator<char>(file)),{});
    for(double rate:{44100.,48000.,96000.}) {
        BufferRegistry buffers;
        for(const auto& [name,frames]:std::map<std::string,size_t>{{"buf_win",2048},{"buf_motes_grains",97},{"buf_motes_wave",129}})
            buffers[name]=std::make_shared<Table>(frames,1,true);
        assert(m4l::maxcompat::fillPreparedBuffer(*buffers.at("buf_win"),1));
        m4l::maxcompat::hanningPreparedBuffer(*buffers.at("buf_win"));
        auto motes=expression(original,true,&buffers,rate);motes.prepareBuffers();assert(motes.snapshotLoopCount()==1);
        assert(motes.set("mixv",100));double energy=0,tail=0;double snapshotMS=0;
        for(int frame=0;frame<int(rate*3);++frame) {
            input[0]=frame<int(rate*2)?std::sin(frame*.1)*.1:0;
            input[1]=frame<int(rate*2)?std::cos(frame*.13)*.13:0;
            const bool freeze=frame==int(rate*2);if(freeze)assert(motes.set("freezeTgt",1));
            const auto begin=freeze?std::chrono::steady_clock::now():std::chrono::steady_clock::time_point{};
            callback=true;const bool good=motes.process(input,out);callback=false;
            if(freeze)snapshotMS=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
            if(!good){std::cerr<<"Motes fault "<<rate<<" frame "<<frame<<"\n";return 1;}
            assert(std::isfinite(out[0]) && std::isfinite(out[1]));energy+=out[0]*out[0]+out[1]*out[1];
            if(frame>int(rate*2.6))tail+=out[0]*out[0]+out[1]*out[1];
        }
        assert(energy>.001 && tail>.001);
        std::cout<<"Original Motes "<<rate<<" Hz: wet energy "<<energy<<", frozen tail "<<tail<<", snapshot "<<snapshotMS<<" ms (this Mac).\n";
    }
    assert(allocations==0);std::cout<<"PASS: bounded snapshot optimization, scalar equivalence, fallback, original Motes Freeze, no callback allocations.\n";
}
