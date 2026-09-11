#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <thread>

static thread_local bool inRender = false;
static thread_local size_t renderAllocations = 0;
void* operator new(std::size_t size) {
    if (inRender) ++renderAllocations;
    if (void* p = std::malloc(size ? size : 1)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete[](void* p) noexcept { ::operator delete(p); }

using namespace m4l::maxcompat;
std::vector<Definition> definitions() {
    Definition input; input.op = Op::input;
    Definition output; output.op = Op::output;
    Definition dial; dial.op = Op::dial; dial.minimum = -70; dial.maximum = 6; dial.initialize = true;
    Definition db; db.op = Op::dbtoa;
    Definition pack; pack.op = Op::pack; pack.arguments = {0, 20}; pack.integers = {false, true};
    Definition line; line.op = Op::line;
    Definition multiply; multiply.op = Op::multiply; multiply.arguments = {1};
    Definition meter; meter.op = Op::meter;
    return {input, output, dial, db, pack, line, multiply, multiply, meter};
}
std::vector<Edge> edges() { return {{0,0,6,0}, {0,1,7,0}, {6,0,1,0}, {7,0,1,1}, {2,0,3,0}, {3,0,4,0}, {4,0,5,0}, {5,0,6,1}, {5,0,7,1}, {6,0,8,0}}; }
void process(Runtime& runtime, const float* l, const float* r, float* ol, float* oright, int n) {
    inRender = true; runtime.render(l, r, ol, oright, n); inRender = false;
    assert(renderAllocations == 0);
}
int main() {
    for (double sr : {44100.,48000.,96000.}) {
        Runtime first(definitions(), edges(), sr), second(definitions(), edges(), sr);
        std::vector<float> l(size_t(sr/10), .5f), r(l.size(), -.25f), ol(l.size()), outR(l.size()), chainL(l.size()), chainR(l.size());
        process(first,l.data(),r.data(),ol.data(),outR.data(),int(l.size()));
        const int ramp = int(std::llround(sr * .02));
        assert(ol[0] == 0 && ol[ramp] == .5f && outR.back() == -.25f);
        for (int i = 0; i <= ramp; ++i) assert(std::abs(ol[i] - .5 * double(i)/ramp) < 1e-7);
        assert(first.send(2,0,Message::number(-6.020599913279624)));
        process(first,l.data(),r.data(),ol.data(),outR.data(),int(l.size()));
        assert(std::abs(ol.back() - .25f) < 1e-7 && std::abs(outR.back() + .125f) < 1e-7);
        process(second,l.data(),r.data(),chainL.data(),chainR.data(),int(l.size()));
        assert(chainL.back() == .5f); // Separate device instance state.
        assert(second.send(2,0,Message::number(-6.020599913279624)));
        process(second,ol.data(),outR.data(),chainL.data(),chainR.data(),int(l.size()));
        assert(std::abs(chainL.back() - .125f) < 1e-7 && std::abs(chainR.back() + .0625f) < 1e-7);
        assert(std::abs(second.meter(8) - .5) < 1e-7); // Peak includes the transition.
        assert(!first.faulted() && !second.faulted());
    }
    // pack cold inlet changes stored time without triggering an output/ramp.
    {
        Runtime rt(definitions(), edges(), 48000);
        std::array<float, 2048> in, out, right; in.fill(1);
        process(rt,in.data(),in.data(),out.data(),right.data(),2048);
        assert(rt.send(4,1,Message::number(40.9))); // int pack slot truncates to 40 ms
        process(rt,in.data(),in.data(),out.data(),right.data(),1); assert(out[0] == 1);
        assert(rt.send(2,0,Message::number(-6.020599913279624)));
        process(rt,in.data(),in.data(),out.data(),right.data(),2048);
        assert(out[0] == 1 && std::abs(out[960]-.75f) < 1e-7 && out[1920] == .5f);
    }
    // Summed cords and right-channel routing use topology, not a fixed gain recipe.
    {
        auto defs = definitions(); auto cords = edges(); cords.push_back({0,1,6,0});
        Runtime rt(defs,cords,48000);
        std::array<float, 2048> l,r,ol,orr; l.fill(.25); r.fill(-.125);
        process(rt,l.data(),r.data(),ol.data(),orr.data(),2048);
        assert(ol.back() == .125f && orr.back() == -.125f);
    }
    // Nested boundary chains preserve signal summing, independent message
    // control, and fan-out without introducing a constant signal on cold inlets.
    for (double sr : {44100.,48000.,96000.}) {
        Definition in;in.op=Op::input;Definition out;out.op=Op::output;
        Definition port;port.op=Op::boundary;Definition gain;gain.op=Op::multiply;gain.arguments={1};
        std::vector<Definition> nodes={in,out,port,port,port,gain,port,port};
        std::vector<Edge> wires={{0,0,2,0},{0,1,2,0},{2,0,3,0},{3,0,5,0},{4,0,5,1},{5,0,6,0},{6,0,7,0},{7,0,1,0},{7,0,1,1}};
        Runtime first(nodes,wires,sr),second(nodes,wires,sr);
        std::array<float,128> l,r,a,b;l.fill(.5f);r.fill(-.125f);
        assert(first.send(4,0,Message::number(.25)));
        process(first,l.data(),r.data(),a.data(),b.data(),128);
        for(int i=0;i<128;++i)assert(a[i]==.09375f && b[i]==.09375f);
        process(second,l.data(),r.data(),a.data(),b.data(),128);
        for(int i=0;i<128;++i)assert(a[i]==.375f && b[i]==.375f);
        assert(!first.faulted() && !second.faulted());
        bool rejected=false;
        try {Runtime invalid(nodes,{{0,0,2,0},{2,0,3,0},{3,0,2,0}},sr);}catch(const std::invalid_argument&){rejected=true;}
        assert(rejected);
    }
    for(auto op:{Op::multiply,Op::add,Op::subtract}) for(int signalPort:{0,1}) {
        Definition input;input.op=Op::input;Definition output;output.op=Op::output;
        Definition boundary;boundary.op=Op::boundary;Definition arithmetic;arithmetic.op=op;arithmetic.arguments={.25};
        std::vector<Definition> nodes={input,output,boundary,arithmetic};
        std::vector<Edge> wires={{0,0,2,0},{0,1,2,0},{2,0,3,signalPort},{3,0,1,0},{3,0,1,1}};
        Runtime rt(nodes,wires,44100);
        std::array<float,64> l,r,a,b;l.fill(.5f);r.fill(-.125f);
        process(rt,l.data(),r.data(),a.data(),b.data(),64);
        const float initial=op==Op::multiply?.09375f:op==Op::add?.625f:signalPort==0?.125f:-.125f;
        assert(a[0]==initial && b[0]==initial);
        assert(rt.send(2,0,Message::number(.75)));
        process(rt,l.data(),r.data(),a.data(),b.data(),64);
        const float changed=op==Op::multiply?.28125f:op==Op::add?1.125f:signalPort==0?-.375f:.375f;
        assert(a[0]==changed && b[0]==changed);
    }
    for (auto malformed : {std::vector<Edge>{{0,9,1,0}}, std::vector<Edge>{{3,0,3,0}}, std::vector<Edge>{{0,0,3,0}}}) {
        bool threw = false; try { Runtime bad(definitions(),malformed,48000); } catch (const std::invalid_argument&) { threw = true; } assert(threw);
    }
    {
        Runtime rt(definitions(),edges(),48000);
        for (int i = 0; i < 255; ++i) assert(rt.send(2,0,Message::number(-12)));
        assert(!rt.send(2,0,Message::number(0)) && rt.rejected() == 1);
        assert(!rt.send(2,0,Message::number(NAN)));
        std::array<float,64> a{},b{}; process(rt,nullptr,nullptr,a.data(),b.data(),64);
        assert(!rt.faulted());
        std::atomic<bool> done{false};
        std::thread producer([&] { for (int i=0;i<20000;++i) while (!rt.send(2,0,Message::number(-double(i%24)))) std::this_thread::yield(); done = true; });
        while (!done) process(rt,nullptr,nullptr,a.data(),b.data(),64);
        producer.join(); assert(!rt.faulted());
    }
    std::cout << "PASS: nested boundary audio/control/summing/instance isolation, graph routing/summing, stereo, controls, cold inlets, 20/40 ms ramps at 44.1/48/96 kHz, two-instance chain/isolation, invalid graph rejection, no render allocations, queue overflow and 20,000 concurrent messages. Max audio parity remains unverified.\n";
}
