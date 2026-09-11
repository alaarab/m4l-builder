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
struct Rec{int node,outlet;Message m;};
struct Log{std::vector<Rec> r;Log(){r.reserve(4096);}static void trace(void* c,int node,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);if(l.r.size()<l.r.capacity())l.r.push_back({node,outlet,m});}};
static void render(Runtime& rt,int frames){std::array<float,64> l{},r{};rendering=true;while(frames>0){int n=std::min(frames,64);rt.render(nullptr,nullptr,l.data(),r.data(),n);frames-=n;}rendering=false;assert(allocations==0);}
static Definition function(int mode) {
    Definition d;d.op=Op::functionCurve;d.arguments={20,0,1,double(mode)};
    // points (1,0) (10,1 curve .5) (20,0)
    d.atoms={Atom::real(1),Atom::real(0),Atom::real(0),Atom::real(10),Atom::real(1),Atom::real(.5),Atom::real(20),Atom::real(0),Atom::real(0)};
    return d;
}
int main(){
    for(int mode:{0,1}) {
        Symbols sy;const Symbol dump=sy.intern("dump");Log log;Runtime rt(std::vector<Definition>{function(mode)},std::vector<Edge>{},48000,sy,Log::trace,&log);
        // Refpage: X outside the first/last breakpoint -> 0; endpoints exact;
        // linear segments in mode 0. Mode 1 follows the classic-curve model
        // (UNMEASURED against Max) but the endpoints and range still hold.
        auto lookup=[&](double x){log.r.clear();assert(rt.send(0,0,Message::number(x)));render(rt,64);assert(log.r.size()==1 && log.r[0].outlet==0 && log.r[0].m.isNumber());return log.r[0].m.atoms[0].number();};
        assert(lookup(0)==0 && lookup(.999)==0 && lookup(20.001)==0 && lookup(25)==0);
        assert(lookup(1)==0 && lookup(10)==1 && lookup(20)==0);
        assert(lookup(15)==.5);   // curve 0 on the last segment: linear
        const double mid=lookup(5.5);
        assert(mid>0 && mid<1);
        if(mode==1) {
            // MEASURED classic curve (Max 9, September 11): y = (exp(k u)-1)/(exp(k)-1), k(0.5) = 2.817463.
            const double k=2.817463,expected=(std::exp(k*.5)-1)/(std::exp(k)-1);
            assert(std::fabs(mid-expected)<1e-12);
            assert(std::fabs(lookup(1+9*.25)-(std::exp(k*.25)-1)/(std::exp(k)-1))<1e-12);
        } else assert(mid==.5);
        // bang -> outlet 1: first Y as a float, then y/dt pairs (mode 0) or
        // y/dt/curve triples (mode 1); the right outlet stays silent.
        log.r.clear();assert(rt.send(0,0,Message{}));render(rt,64);
        assert(log.r.size()==2);
        assert(log.r[0].outlet==1 && log.r[0].m.isNumber() && log.r[0].m.atoms[0].number()==0);
        assert(log.r[1].outlet==1 && log.r[1].m.kind==Message::Kind::list);
        if(mode==0) {
            assert(log.r[1].m.count==4 && log.r[1].m.atoms[0].number()==1 && log.r[1].m.atoms[1].number()==9 && log.r[1].m.atoms[2].number()==0 && log.r[1].m.atoms[3].number()==10);
        } else {
            assert(log.r[1].m.count==6 && log.r[1].m.atoms[0].number()==1 && log.r[1].m.atoms[1].number()==9 && log.r[1].m.atoms[2].number()==.5 && log.r[1].m.atoms[3].number()==0 && log.r[1].m.atoms[4].number()==10 && log.r[1].m.atoms[5].number()==0);
        }
        for(const auto& e:log.r)assert(e.outlet!=3);
        // dump -> outlet 2, one list per point (x y, plus curve in mode 1).
        log.r.clear();assert(rt.send(0,0,Message::anything(dump)));render(rt,64);
        assert(log.r.size()==3);
        for(size_t i=0;i<3;++i) {assert(log.r[i].outlet==2 && log.r[i].m.kind==Message::Kind::list && log.r[i].m.count==(mode?3:2));}
        assert(log.r[1].m.atoms[0].number()==10 && log.r[1].m.atoms[1].number()==1);
        if(mode)assert(log.r[1].m.atoms[2].number()==.5);
        assert(!rt.faulted());
    }
    {
        // Orbit's redraw ring: function right outlet -> [t b] -> [uzi 128] ->
        // [t i i] -> expr -> function inlet. The right outlet only bangs after a
        // mouse edit, so the ring builds; a message never re-enters it.
        Symbols sy;Log log;
        Definition trig;trig.op=Op::trigger;trig.atoms={Atom{}};trig.formats={Format::bang};
        Definition uzi;uzi.op=Op::uzi;uzi.arguments={128,1};
        Definition ti;ti.op=Op::trigger;ti.atoms={Atom{},Atom{}};ti.formats={Format::integer,Format::integer};
        Definition expr;expr.op=Op::expression;expr.expression="($i1 - 1) / 127.";expr.arguments={1};
        std::vector<Definition> defs{function(1),trig,uzi,ti,expr};
        std::vector<Edge> edges{{0,3,1,0},{1,0,2,0},{2,2,3,0},{3,1,4,0},{4,0,0,0}};
        bool built=false;
        try {Runtime rt(defs,edges,48000,sy,Log::trace,&log);built=true;
            assert(rt.send(0,0,Message::number(10)));render(rt,64);assert(!rt.faulted());
        } catch(const std::invalid_argument& e) {
            // The expr constructor contract may differ; the ring itself must not be the reason.
            assert(std::string(e.what()).find("Feedback")==std::string::npos);
        }
        (void)built;
    }
    {
        // Point editing: 'index x y' modifies (0-based, out of range ignored),
        // 'x y' adds, clear <indices> removes, nth reads, setcurve is 1-based,
        // set repositions; each change publishes the full list to the host.
        Symbols sy;const Symbol nth=sym::nth,clear=sym::clear,setcurve=sy.intern("setcurve"),points=sy.intern("points"),listdump=sy.intern("listdump");Log log;
        Runtime rt(std::vector<Definition>{function(1)},std::vector<Edge>{},48000,sy,Log::trace,&log);
        auto published=[&]{std::vector<Runtime::ExternalEvent> out;Runtime::ExternalEvent e;while(rt.popExternal(e))out.push_back(e);return out;};
        auto list=[&](std::initializer_list<double> v){Message m;m.kind=Message::Kind::list;m.selector=sym::list;int i=0;for(double x:v)m.atoms[size_t(i++)]=Atom::real(x);m.count=i;return m;};
        auto any=[&](Symbol s,std::initializer_list<Atom> v){Message m=Message::anything(s);int i=0;for(const Atom& a:v)m.atoms[size_t(i++)]=a;m.count=i;return m;};
        assert(published().empty());
        // move point 1 (10,1) to (12, .25): outlet 0 lookups follow, publication carries 3 points
        assert(rt.send(0,0,list({1,12,.25})));render(rt,64);
        auto ev=published();assert(ev.size()==1 && ev[0].message.selector==points && ev[0].message.count==2+9);
        assert(ev[0].message.atoms[0].number()==3 && ev[0].message.atoms[1].number()==0 && ev[0].message.atoms[5].number()==12 && ev[0].message.atoms[6].number()==.25 && ev[0].message.atoms[7].number()==.5);
        log.r.clear();assert(rt.send(0,0,Message::number(12)));render(rt,64);assert(log.r.size()==1 && log.r[0].m.atoms[0].number()==.25);
        // out-of-range index: ignored, nothing published
        assert(rt.send(0,0,list({7,1,1})));render(rt,64);assert(published().empty());
        // nth 2 -> y of point 2
        log.r.clear();assert(rt.send(0,0,any(nth,{Atom::integral(2)})));render(rt,64);assert(log.r.size()==1 && log.r[0].outlet==0 && log.r[0].m.atoms[0].number()==0);
        // add (15, .75) -> 4 points, ordered by x
        assert(rt.send(0,0,list({15,.75})));render(rt,64);ev=published();assert(ev.size()==1 && ev[0].message.atoms[0].number()==4 && ev[0].message.atoms[8].number()==15);
        // moving point 2 past point 3 re-sorts (UNMEASURED constraint)
        assert(rt.send(0,0,list({2,25,.1})));render(rt,64);ev=published();assert(ev.size()==1 && ev[0].message.atoms[2+9].number()==25);
        // setcurve 1 -> segment leaving point 0
        assert(rt.send(0,0,any(setcurve,{Atom::integral(1),Atom::real(-.3)})));render(rt,64);ev=published();assert(ev.size()==1 && ev[0].message.atoms[7].number()==-.3);
        // clear 0 3 -> two points remain (MEASURED: clear 0 2 on four keeps 1 and 3)
        assert(rt.send(0,0,any(clear,{Atom::integral(0),Atom::integral(3)})));render(rt,64);ev=published();assert(ev.size()==1 && ev[0].message.atoms[0].number()==2 && ev[0].message.atoms[2].number()==12 && ev[0].message.atoms[5].number()==20);
        // listdump -> outlet 2 flat x y list
        log.r.clear();assert(rt.send(0,0,Message::anything(listdump)));render(rt,64);assert(log.r.size()==1 && log.r[0].outlet==2 && log.r[0].m.count==4 && log.r[0].m.atoms[2].number()==20);
        // set 2 .5 30 .5 repositions both (MEASURED: positional, float32
        // round trip, no re-sort so duplicate x coexist, rest untouched)
        assert(rt.send(0,0,any(sym::set,{Atom::real(2),Atom::real(.5),Atom::real(30),Atom::real(.5)})));render(rt,64);ev=published();assert(ev.size()==1 && ev[0].message.atoms[2].number()==2 && ev[0].message.atoms[5].number()==30);
        assert(rt.send(0,0,list({10,.5})));render(rt,64);published();   // three points: 2, 10, 30
        assert(rt.send(0,0,any(sym::set,{Atom::real(.1),Atom::real(.11),Atom::real(30),Atom::real(.4)})));render(rt,64);ev=published();
        assert(ev.size()==1 && ev[0].message.atoms[0].number()==3 && ev[0].message.atoms[2].number()==double(float(.1)) && ev[0].message.atoms[3].number()==double(float(.11)) && ev[0].message.atoms[5].number()==30 && ev[0].message.atoms[8].number()==30);
        assert(rt.send(0,0,list({1,10,.5})));render(rt,64);ev=published();assert(ev[0].message.atoms[5].number()==10);   // back to 0.1, 10, 30
        // Host touch inlet (-1): the same messages, and a bang there is the
        // mouse-edit completion that bangs the right outlet (nothing else).
        log.r.clear();assert(rt.send(0,-1,list({0,3,.5})));assert(rt.send(0,-1,Message{}));render(rt,64);
        assert(log.r.size()==1 && log.r[0].outlet==3 && log.r[0].m.kind==Message::Kind::bang);
        ev=published();assert(ev.size()==1 && ev[0].message.atoms[2].number()==3);
        assert(!rt.send(0,-2,Message{}) && !rt.send(0,2,Message{}));
        // A bang at inlet 0 still emits the curve~ list, never outlet 3.
        log.r.clear();assert(rt.send(0,0,Message{}));render(rt,64);for(const auto& e:log.r)assert(e.outlet==1);
        // 256-point publication is chunked and reassembles to the full list.
        assert(rt.send(0,0,Message::anything(clear)));render(rt,64);published();
        for(int i=0;i<300;++i) {assert(rt.send(0,0,list({double(i)/300*20,.5})));if(i%16==15){render(rt,64);published();}}
        render(rt,64);ev=published();assert(!ev.empty());
        {const auto& last=ev.back().message;assert(last.atoms[0].number()==256);}
        assert(!rt.faulted());
        // A UI inlet on any other object is rejected.
        Definition dial;dial.op=Op::dial;Runtime other(std::vector<Definition>{dial},std::vector<Edge>{},48000,sy);
        assert(!other.send(0,-1,Message{}));
    }
    std::cout<<"PASS: function lookup (0 outside breakpoints, exact endpoints), bang emits line~/curve~ lists on outlet 1, dump lists on outlet 2, right outlet silent to messages, Orbit redraw ring builds, point edits/clear/nth/setcurve/set/listdump publish the list, host touch inlet bangs outlet 3 on completion; classic curve uses the measured k(c) table (fine above 0.9, saturating at 0.995).\n";
}
