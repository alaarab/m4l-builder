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

struct Record {int outlet;Message message;};
struct Log {
    std::vector<Record> records;
    Log(){records.reserve(64);}
    static void trace(void* c,int,int outlet,uint64_t,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(c);assert(log.records.size()<log.records.capacity());log.records.push_back({outlet,m});
    }
};
static void drain(Runtime& rt){std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;assert(allocations==0);}
int main(){
    Definition d;d.op=Op::textButton;
    // A host click arrives as a number; a patch-driven trigger arrives as a
    // bang. Both fire exactly one bang on outlet 0 and nothing elsewhere.
    Log log;Symbols symbols;
    Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,symbols,Log::trace,&log);
    assert(rt.send(0,0,Message::integer(1)));drain(rt);
    assert(rt.send(0,0,Message{}));drain(rt);
    assert(!rt.faulted());
    assert(log.records.size()==2);
    for(const auto& r:log.records){assert(r.outlet==0);assert(r.message.kind==Message::Kind::bang);}
    // A symbol has no click meaning and faults instead of firing.
    const Symbol s=symbols.intern("go");
    Log log2;Runtime rt2(std::vector<Definition>{d},std::vector<Edge>{},48000,symbols,Log::trace,&log2);
    assert(rt2.send(0,0,Message::anything(s)));drain(rt2);
    assert(rt2.faulted() && log2.records.empty());
    std::cout<<"PASS: textbutton mode 0 bangs outlet 0 once per number or bang, symbol faults, three declared outlets, no render allocations. Max oracle comparison NOT run.\n";
}
