#include "../../src/m4l_builder/native/max_compat/gen_graph.hpp"
#include <array>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p)noexcept{::operator delete(p);}
using namespace m4l::gen;
int main(int argc,char** argv){
    assert(argc==5);std::ifstream file(argv[1]);double rate;size_t frames;file>>rate>>frames;assert(file && frames==2048);
    struct Sample{std::array<double,4> input;std::array<double,8> output;};
    std::vector<Sample> samples(frames);for(auto& s:samples){for(auto& v:s.input)file>>v;for(auto& v:s.output)file>>v;}assert(file);
    const std::string code="genstate_osc(x){return phasor(x);}History held(0);out1=change(in1);out2=phasor(in2,in3);out3=change(3);out4=phasor(0.1);if(in4){held=change(in1);}out5=held;out6=phasor(in2);out7=genstate_osc(in2);out8=genstate_osc(in2*0.5);";
    Expression original(code,rate),independent(code,rate);std::array<double,64> output{};
    double maximum=0;
    for(int repeat=0;repeat<2;++repeat){
        callback=true;original.reset();callback=false;
        for(size_t frame=0;frame<frames;++frame){
            callback=true;assert(original.process(samples[frame].input.data(),output.data()));callback=false;
            for(size_t channel=0;channel<8;++channel){
                const double delta=std::abs(double(float(output[channel]))-samples[frame].output[channel]);maximum=std::max(maximum,delta);
                if(delta>1e-7){std::cerr<<"Mismatch frame "<<frame<<" channel "<<channel<<" actual "<<output[channel]<<" expected "<<samples[frame].output[channel]<<"\n";return 1;}
                if(channel==0 || channel==2 || channel==4)assert(delta==0);
            }
        }
    }
    assert(independent.process(samples[0].input.data(),output.data()));
    for(size_t c=0;c<8;++c)assert(std::abs(double(float(output[c]))-samples[0].output[c])<1e-7);
    // Prepared call sites and instances remain isolated at each engine rate;
    // resets clear operator state and negative/high rates remain wrapped.
    for(double sr:{44100.,48000.,96000.}){
        Expression e("out1=phasor(in1,in2);out2=change(in3);",sr);double in[3]={sr*.25,0,1};
        for(int n=0;n<20;++n){callback=true;assert(e.process(in,output.data()));callback=false;assert(output[0]==double((n+1)%4)*.25 && output[1]==(n==0?1:0));}
        in[0]=-sr*2.25;in[1]=1;in[2]=-1;callback=true;assert(e.process(in,output.data()));callback=false;assert(output[0]==.75 && output[1]==-1);
        callback=true;e.reset();callback=false;in[0]=sr*.25;in[1]=0;in[2]=1;assert(e.process(in,output.data()) && output[0]==.25 && output[1]==1);
    }
    for(const char* code:{"out1=change();","out1=change(in1,in2);","out1=phasor();","out1=phasor(in1,in2,in3);"}){
        bool rejected=false;try{Expression invalid(code,rate);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    }
    std::ifstream mods(argv[2]);size_t modFrames;mods>>modFrames;assert(mods && modFrames==2048);
    Expression mod("r=in1%in2;out1=r;out2=r==round(r);",48000);
    for(size_t n=0;n<modFrames;++n){
        double in[2],expected[2];mods>>in[0]>>in[1]>>expected[0]>>expected[1];assert(mods);
        callback=true;assert(mod.process(in,output.data()));callback=false;
        if(double(float(output[0]))!=expected[0] || output[1]!=expected[1]){
            std::cerr.precision(17);std::cerr<<"Remainder mismatch "<<n<<" input "<<in[0]<<","<<in[1]<<" actual "<<output[0]<<","<<output[1]<<" expected "<<expected[0]<<","<<expected[1]<<"\n";return 1;
        }
    }
    double excessive[2]={1e30,1};callback=true;assert(!mod.process(excessive,output.data()));callback=false;
    assert(output[0]==0 && output[1]==0);
    std::ifstream graphFile(argv[3]);double graphRate;size_t graphFrames;
    graphFile>>graphRate>>graphFrames;assert(graphFile && graphFrames==2048);
    auto port=[](NodeDefinition::Kind kind,int index){NodeDefinition n;n.kind=kind;n.port=index;return n;};
    auto operation=[](std::string name,std::vector<std::string> args=std::vector<std::string>{}){
        NodeDefinition n;n.kind=NodeDefinition::Kind::operation;n.operation=std::move(name);n.arguments=std::move(args);return n;
    };
    GraphDefinition definition;
    definition.nodes={port(NodeDefinition::Kind::input,0),port(NodeDefinition::Kind::input,1),port(NodeDefinition::Kind::input,2),
        operation("change"),operation("phasor"),operation("phasor",{"110"}),
        port(NodeDefinition::Kind::output,0),port(NodeDefinition::Kind::output,1),port(NodeDefinition::Kind::output,2)};
    definition.edges={{0,0,3,0},{1,0,4,0},{2,0,4,1},{2,0,5,0},{3,0,6,0},{4,0,7,0},{5,0,8,0}};
    Graph graph(definition,graphRate);
    for(size_t frame=0;frame<graphFrames;++frame){
        double in[3],expected[3];for(auto& v:in)graphFile>>v;for(auto& v:expected)graphFile>>v;assert(graphFile);
        callback=true;assert(graph.process(in,output.data()));callback=false;
        assert(double(float(output[0]))==expected[0]);
        for(size_t c=1;c<3;++c)assert(std::abs(double(float(output[c]))-expected[c])<1e-7);
    }
    auto invalid=definition;invalid.edges.push_back({0,0,5,1});
    bool rejected=false;try{Graph wrongConstructorInlet(invalid,graphRate);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    std::ifstream constants(argv[4]);size_t constantFrames;constants>>constantFrames;assert(constants && constantFrames==2048);
    Expression constantMod("out1=in1%6;out2=out1==round(out1);out3=in1%13;out4=out3==round(out3);out5=in1%97;out6=out5==round(out5);",48000);
    for(size_t n=0;n<constantFrames;++n){
        double in[1],expected[6];constants>>in[0];for(auto& v:expected)constants>>v;assert(constants);
        callback=true;assert(constantMod.process(in,output.data()));callback=false;
        for(size_t c=0;c<6;++c)assert(double(float(output[c]))==expected[c]);
    }
    assert(allocations==0);
    std::cout<<"PASS: 16384 original Max operator samples plus reset repeat, 4096 exact dynamic and 12288 exact constant remainder/value-comparison samples, 6144 graph/constructor samples, constant change folding, signed/reset phasor, conditional and function-call state, independent instances, three rates, zero callback allocations; maximum float PCM error "<<maximum<<"\n";
}
