#include "../../src/m4l_builder/native/max_compat/genexpr.hpp"
#include <cassert>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <new>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using m4l::gen::Expression;
int main(int argc,char** argv) {
    const std::string source="accumulate(x) { History z(0); z = z + x; return z; } Param gain(0.5, min=0, max=1); a = accumulate(in1); b = accumulate(in2); if (in3 > 0) { out1 = a*gain; } else { out1 = b*gain; } out2 = b;";
    Expression a(source,48000),b(source,48000);
    std::array<double,64> input{},output{};input[0]=1;input[1]=2;input[2]=1;
    for(int i=1;i<=32;++i) {callback=true;assert(a.process(input.data(),output.data()));callback=false;assert(allocations==0);assert(output[0]==i*.5 && output[1]==i*2);}
    assert(b.process(input.data(),output.data()) && output[0]==.5 && output[1]==2);
    a.reset();assert(a.set("gain",2));assert(a.process(input.data(),output.data()) && output[0]==1 && output[1]==2);
    Expression loop("x=1; for(i=0; i<in1; i+=1) { x*=2; } out1=x;",48000);
    input[0]=8;assert(loop.process(input.data(),output.data()) && output[0]==256);
    input[0]=1e100;callback=true;assert(!loop.process(input.data(),output.data()));callback=false;assert(output[0]==0 && allocations==0);
    const std::string coercion="modvalue(x){x=x*0.5;return x;}out1=modvalue(in1);out2=modvalue(in2);";
    Expression constants(coercion,48000,{m4l::gen::ValueInfo::literal(3),m4l::gen::ValueInfo::literal(3.1)}),signals(coercion,48000);
    input[0]=3;input[1]=3.1;
    assert(constants.process(input.data(),output.data()) && output[0]==1 && output[1]==1.55);
    assert(signals.process(input.data(),output.data()) && output[0]==1.5 && output[1]==1.55);
    Expression folded("modvalue(x){x=x*0.5;return x;}out1=modvalue(1.5+1.5);out2=modvalue(-3.);",48000);
    assert(folded.process(input.data(),output.data()) && output[0]==1 && output[1]==-1);
    Expression local("x=1;x=0.5;out1=x;out2=1/2;",48000);
    assert(local.process(input.data(),output.data()) && output[0]==.5 && output[1]==.5);
    Expression scopes("modvalue(x){x=x*0.5;return x;}Param p(3);History h(3);out1=modvalue(p);out2=modvalue(h);",48000,{},true);
    assert(scopes.process(input.data(),output.data()) && output[0]==1 && output[1]==1.5 && !scopes.set("p",3.1));
    Expression branch("f(x){if(x>.5){return x*2;}else if(x<0){return -1;}else{return .25;}}out1=f(in1);out2=f(in2);",48000);
    input[0]=.7;input[1]=-.2;assert(branch.process(input.data(),output.data()) && output[0]==1.4 && output[1]==-1);
    Expression partial("f(x){if(x>.5){return x;}}out1=f(in1);out2=f(in2);",48000);
    assert(partial.process(input.data(),output.data()) && output[0]==.7 && output[1]==0);
    Expression amplitude("out1=atodb(in1);out2=atodb(in2);",48000);
    Expression dynamicWrap("out1=wrap(0.5,in1,in2);",48000);
    assert(!dynamicWrap.outputInfo(0).constant && !dynamicWrap.outputInfo(0).integer);
    input[0]=1;input[1]=2;assert(dynamicWrap.process(input.data(),output.data()) && output[0]==1.5);
    input[0]=0;input[1]=1;assert(dynamicWrap.process(input.data(),output.data()) && output[0]==0.5);
    // Current Max's MSP_ON_CLANG fixdenorm is an identity, including tiny
    // values. Normalized actual-Max captures cover the arithmetic around it.
    Expression denormal("out1=fixdenorm(in1);out2=fixdenorm(in2);",48000);
    for(double value:{0.,0x1p-1022,0x1p-1023,0x1p-1074}) {
        input[0]=value;input[1]=-value;callback=true;
        assert(denormal.process(input.data(),output.data()) && output[0]==value && output[1]==-value);
        callback=false;
    }
    input[0]=0;input[1]=-.1;assert(amplitude.process(input.data(),output.data()) && output[0]==-999 && output[1]==-999);
    input[0]=.1;input[1]=1e-60;assert(amplitude.process(input.data(),output.data()) && output[0]==-20 && output[1]==-1200);
    const std::string delayed="f(x){Delay d(8);a=d.read(2.25);d.write(x);return a;}out1=f(in1);out2=f(in2);";
    Expression delay(delayed,48000),independent(delayed,48000);
    for(int n=0;n<32;++n) {
        input[0]=n==0?1:0;input[1]=n==0?2:0;callback=true;
        assert(delay.process(input.data(),output.data()));callback=false;
        const double expected=n==2?.75:(n==3?.25:0);assert(output[0]==expected && output[1]==expected*2);
    }
    input[0]=input[1]=1;assert(independent.process(input.data(),output.data()) && output[0]==0 && output[1]==0);
    callback=true;delay.reset();assert(delay.process(input.data(),output.data()));callback=false;assert(output[0]==0 && output[1]==0);
    Expression ordering("Delay d(8);out1=d.read(in2);d.write(in1);out2=d.read(in2,interp=\"none\");",48000);
    input[0]=1;input[1]=0;assert(ordering.process(input.data(),output.data()) && output[0]==0 && output[1]==1);
    input[0]=2;assert(ordering.process(input.data(),output.data()) && output[0]==1 && output[1]==2);
    Expression sparse("Delay d(8);if(in2){d.write(in1);}out1=d.read(2);out2=in2;",48000);
    input[0]=1;input[1]=1;for(int n=0;n<32;++n)assert(sparse.process(input.data(),output.data()));
    callback=true;sparse.reset();input[1]=0;
    for(int n=0;n<64;++n) {assert(sparse.process(input.data(),output.data()));assert(output[0]==0);}
    callback=false;assert(allocations==0);
    Expression slew("out1=slide(in1,4,2);out2=slide(in2,2,4);",48000);
    input[0]=input[1]=1;assert(slew.process(input.data(),output.data()) && output[0]==.25 && output[1]==.5);
    input[0]=input[1]=0;assert(slew.process(input.data(),output.data()) && output[0]==.125 && output[1]==.375);
    Expression constantSlew("out1=slide(.65,512,512);out2=slide(.65,in1,in1);",48000);
    input[0]=512;assert(constantSlew.process(input.data(),output.data()) && output[0]==.65 && output[1]==.65/512);
    bool memoryRejected=false;try {Expression huge("Delay a(8),b(2);out1=a.read(1);",48000,{},false,{},8);}catch(const std::invalid_argument&){memoryRejected=true;}assert(memoryRejected);
    for(const std::string invalid:{"out1=missing;","out1=external(in1);","f(x){return f(x);} out1=f(in1);","out1 = 1; garbage","History x(0); History x(1); out1=x;","out65 = in1;",
        "modvalue(x){if(x){return 1;}return 0.5;}out1=modvalue(in1);",
        "History x(1,min=0);out1=x;","f(x){return x;x=2;}out1=f(in1);",
        "Delay d(8);out1=d.write(in1);","Delay d(8);d.write(in1)+1;out1=in1;",
        "Delay d(8);out1=d.read(1,interp=\"cosine\");","Delay d(8);out1=d.read(1,interp=\"spline\");",
        "Delay d(in1);out1=d.read(1);","Delay d(8);History d(0);out1=in1;",
        "Delay d(8);d=1;out1=in1;","Delay d(8);f(x){return d.read(x);}out1=f(in1);",
        "out1=1e60;","modvalue(x,x){return x;}out1=modvalue(1,2);",
        "modvalue(x){x*=0.5;return x;}x=3;for(i=0;i<in1;i+=1){x*=2;}out1=modvalue(x);"}) {
        bool rejected=false;try{Expression bad(invalid,48000);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
    }
    if(argc>1) {
        for(int i=1;i<argc;++i) {
            std::ifstream file(argv[i]);const std::string text((std::istreambuf_iterator<char>(file)),{});
            Expression original(text,48000);
            input.fill(.25);for(int sample=0;sample<512;++sample) {callback=true;assert(original.process(input.data(),output.data()));callback=false;}
            std::cout<<argv[i]<<": "<<original.inputs()<<" inputs, "<<original.outputs()<<" outputs, "<<original.parameters().size()<<" parameters, final "<<std::setprecision(17)<<output[0]<<"\n";
        }
    }
    assert(allocations==0);std::cout<<"PASS: functions, branch/state, call-site and instance isolation, parameter clamp/reset, bounded loops, invalid code, no callback allocations.\n";
}
