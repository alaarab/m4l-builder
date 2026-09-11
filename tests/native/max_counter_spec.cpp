#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
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
struct Log{std::vector<int64_t> v;Log(){v.reserve(64);}static void trace(void* c,int,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(outlet==0);assert(l.v.size()<l.v.capacity());l.v.push_back(m.atoms[0].value.integer);}};
static void drain(Runtime& rt){std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;assert(allocations==0);}
static Definition counter(double lo,double hi){Definition d;d.op=Op::counter;d.arguments={0,lo,hi};return d;}
int main(){
    // The measured sequence: [counter 1 4] under six bangs -> 1 2 3 4 1 2.
    {Log log;Symbols sy;Runtime rt(std::vector<Definition>{counter(1,4)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     for(int i=0;i<6;++i)assert(rt.send(0,0,Message{}));drain(rt);assert(!rt.faulted());
     assert((log.v==std::vector<int64_t>{1,2,3,4,1,2}));}
    // Inlet 4 raises the maximum silently; a lower maximum than the minimum faults.
    {Log log;Symbols sy;Runtime rt(std::vector<Definition>{counter(0,1)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,4,Message::integer(2)));for(int i=0;i<4;++i)assert(rt.send(0,0,Message{}));drain(rt);assert(!rt.faulted());
     assert((log.v==std::vector<int64_t>{0,1,2,0}));
     assert(rt.send(0,4,Message::integer(-5)));drain(rt);assert(rt.faulted());}
    // 'set N' / 'goto N' set the count without output; the next bang sends it (refpage; Shard uses set 0).
    {Log log;Symbols sy;const Symbol gt=sy.intern("goto");Runtime rt(std::vector<Definition>{counter(0,9)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,0,Message{}));assert(rt.send(0,0,Message{}));
     Message set=Message::anything(sym::set);set.count=1;set.atoms[0]=Atom::integral(7);assert(rt.send(0,0,set));
     assert(rt.send(0,0,Message{}));Message go=Message::anything(gt);go.count=1;go.atoms[0]=Atom::integral(0);assert(rt.send(0,0,go));assert(rt.send(0,0,Message{}));
     drain(rt);assert(!rt.faulted());assert((log.v==std::vector<int64_t>{0,1,7,0}));}
    // Non-bang at the count inlet and unsupported directions are refused.
    {Log log;Symbols sy;Runtime rt(std::vector<Definition>{counter(0,3)},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,0,Message::integer(2)));drain(rt);assert(rt.faulted());
     bool f=false;Definition d;d.op=Op::counter;d.arguments={1,0,3};try{Runtime r2(std::vector<Definition>{d},std::vector<Edge>{},48000);}catch(const std::invalid_argument&){f=true;}assert(f);}
    // Measured gate clamping: [gate 2] selected 5 routes to the top outlet.
    {struct L{std::vector<int> o;static void t(void* c,int,int outlet,uint64_t,const Message&) noexcept{static_cast<L*>(c)->o.push_back(outlet);}} l;l.o.reserve(8);
     Definition g;g.op=Op::gate;g.arguments={2,0};Symbols sy;Runtime rt(std::vector<Definition>{g},std::vector<Edge>{},48000,sy,L::t,&l);
     assert(rt.send(0,0,Message::integer(5)));assert(rt.send(0,1,Message{}));drain(rt);assert(!rt.faulted());assert(l.o.size()==1 && l.o[0]==1);}
    std::cout<<"PASS: counter output-then-increment with wrap after maximum (measured 1 2 3 4 1 2), inlet-4 maximum, set/goto without output, refusals; gate clamps above range (measured). Zero-selection close and bare-counter default maximum remain unmeasured.\n";
}
