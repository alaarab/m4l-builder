// Dirt Rig's objects: overdrive~ (MEASURED transfer curve, bit-exact at drive 4),
// degrade~ (MEASURED truncation), tanh~, and poly~ ... up 2 hosting a subpatch
// at twice the rate between half-band filters (filters UNMEASURED).
#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <new>
#include <vector>
static thread_local bool rendering=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n) {if(rendering)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;
int main(){
    Symbols sy;
    Definition in;in.op=Op::input;Definition od;od.op=Op::overdrive;od.arguments={4};Definition dg;dg.op=Op::degrade;dg.arguments={1,16};Definition out;out.op=Op::output;
    Runtime rt(std::vector<Definition>{in,od,dg,out},std::vector<Edge>{{0,0,1,0},{0,1,2,0},{1,0,3,0},{2,0,3,1}},44100,sy);rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};
    const double xs[13]={-1.5,-1.25,-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1,1.25,1.5};
    const double live[13]={-1,-1,-1,-0.99609375,-0.9375,-0.68359375,0,0.68359375,0.9375,0.99609375,1,1,1};
    for(int i=0;i<13;++i)l[size_t(i)]=float(xs[i]);
    r[0]=0.3f;
    rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);
    for(int i=0;i<13;++i)assert(std::abs(double(ol[size_t(i)])-live[i])<1e-7);
    assert(std::abs(double(orr[0])-0.29998779296875)<1e-9);   // degrade~ 1 16 of 0.3 truncates
    assert(rt.send(2,2,Message::number(4)));rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;
    assert(std::abs(double(orr[0])-0.25)<1e-9);                // degrade~ 1 4 of 0.3
    // poly~ passthrough up 2: in~ 1 -> out~ 1 at 88.2 kHz; a DC step settles to unity after the filters' few samples of latency.
    auto spec=std::make_shared<SpectralDefinition>();spec->size=2;spec->overlap=0;spec->inlets=1;spec->outlets=1;
    Definition pin;pin.op=Op::polyIn;pin.arguments={0};Definition pout;pout.op=Op::polyOut;pout.arguments={0};Definition th;th.op=Op::tanhSignal;
    spec->definitions={pin,th,pout};spec->edges={{0,0,1,0},{1,0,2,0}};
    Definition pu;pu.op=Op::polyUp;pu.spectral=spec;
    Runtime r2(std::vector<Definition>{in,pu,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},44100,sy);r2.setDSPActive(true);
    std::vector<double> y;
    for(int b=0;b<4;++b){l.fill(0.25f);rendering=true;r2.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);for(float v:ol)y.push_back(v);}
    const double expected=std::tanh(0.25);
    assert(std::abs(y[63]-expected)<1e-6 && std::abs(y[255]-expected)<1e-6);   // float32 output path
    int settled=-1;for(size_t i=0;i<y.size();++i)if(std::abs(y[i]-expected)<1e-6){settled=int(i);break;}
    std::cout<<"poly~ up 2 tanh settles at sample "<<settled<<"\n";
    assert(settled>=0 && settled<64);   // the measured IIR half-bands ring for ~50 samples
    assert(!rt.faulted() && !r2.faulted());
    {
        // MEASURED (Live, September 11, poly_up.csv): a unit impulse through a
        // pass-through poly~ up 2 voice — the first 48 samples of Max's
        // resampler chain, reproduced by the polyphase-allpass half-bands.
        static const double measured[48]={0.00190538261,0.0582132265,0.388812512,0.684431255,-0.0434454605,-0.22321561,0.246945456,-0.195670947,0.136361331,-0.0880086645,0.0529595651,-0.028970547,0.0131657124,-0.00311858999,-0.00298684766,0.00644603465,-0.00816279557,0.00875999313,-0.00866273232,0.0081580393,-0.00743694231,0.00662401319,-0.00579809258,0.00500683254,-0.00427688658,0.00362102804,-0.00304309325,0.0025413835,-0.00211097905,0.00174528535,-0.00143704365,0.00117896881,-0.000964133127,0.000786176708,-0.000639405218,0.000518814079,-0.000420067488,0.00033945209,-0.00027381687,0.000220508897,-0.000177309106,0.000142371704,-0.000114168834,9.14411648e-05,-7.31545588e-05,5.84626141e-05,-4.66746569e-05,3.72285576e-05};
        Definition pass;pass.op=Op::polyIn;pass.arguments={0};Definition passOut;passOut.op=Op::polyOut;passOut.arguments={0};
        auto ps=std::make_shared<SpectralDefinition>();ps->size=2;ps->overlap=0;ps->inlets=1;ps->outlets=1;ps->definitions={pass,passOut};ps->edges={{0,0,1,0}};
        Definition pp;pp.op=Op::polyUp;pp.spectral=ps;
        Runtime r3(std::vector<Definition>{in,pp,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},44100,sy);r3.setDSPActive(true);
        l.fill(0.f);l[0]=1.f;rendering=true;r3.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;
        double worst=0;for(int i=0;i<48;++i)worst=std::max(worst,std::abs(double(ol[i])-measured[i]));
        std::cout<<"poly~ up 2 impulse: worst deviation from Max "<<worst<<"\n";
        assert(worst<2e-6 && !r3.faulted());   // float32 output path
    }
    std::cout<<"PASS: overdrive~ Live sweep, degrade~ truncation, poly~ up 2 tanh~ at 88.2 kHz and the measured Max resampler impulse response, zero render allocations\n";
    return 0;
}
