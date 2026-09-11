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
struct Log{std::vector<Message> r;Log(){r.reserve(64);}static void trace(void* c,int,int outlet,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(outlet==0);assert(l.r.size()<l.r.capacity());l.r.push_back(m);}};
static void drain(Runtime& rt){std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;assert(allocations==0);}
int main(){
    // Integer change: an initial 0 swallows a leading 0, repeats are silent,
    // and floats are truncated before comparison.
    {Definition d;d.op=Op::change;Log log;Symbols sy;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,Log::trace,&log);
     for(auto m:{Message::integer(0),Message::integer(1),Message::integer(1),Message::number(1.9),Message::integer(2),Message::integer(2)}){assert(rt.send(0,0,m));}
     drain(rt);assert(!rt.faulted());
     assert(log.r.size()==2);assert(log.r[0].atoms[0].type==Atom::Type::integer && log.r[0].atoms[0].value.integer==1);assert(log.r[1].atoms[0].value.integer==2);}
    // Float change keeps fractional differences.
    {Definition d;d.op=Op::change;d.atoms={Atom::real(0.)};Log log;Symbols sy;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,Log::trace,&log);
     for(auto m:{Message::number(0.),Message::number(120.),Message::number(120.),Message::number(120.5)}){assert(rt.send(0,0,m));}
     drain(rt);assert(!rt.faulted());
     assert(log.r.size()==2);assert(log.r[0].atoms[0].type==Atom::Type::floating && log.r[0].atoms[0].value.floating==120.);assert(log.r[1].atoms[0].value.floating==120.5);}
    // Non-numbers fault; two arguments are rejected at preparation.
    {Definition d;d.op=Op::change;Symbols sy;const Symbol x=sy.intern("x");Log log;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,Log::trace,&log);
     assert(rt.send(0,0,Message::anything(x)));drain(rt);assert(rt.faulted());
     bool failed=false;Definition bad;bad.op=Op::change;bad.atoms={Atom::integral(0),Atom::integral(1)};
     try{Runtime r2(std::vector<Definition>{bad},std::vector<Edge>{},48000);}catch(const std::invalid_argument&){failed=true;}assert(failed);}
    std::cout<<"PASS: change int/float typing from argument, initial-value swallow, repeat suppression, truncation, fault on symbol, argument rejection, no render allocations. Max oracle comparison NOT run.\n";
}
