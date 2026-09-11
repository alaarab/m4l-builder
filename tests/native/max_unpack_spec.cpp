#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <memory>
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
    Log(){records.reserve(256);}
    static void trace(void* context,int,int outlet,uint64_t,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(context);assert(log.records.size()<log.records.capacity());
        log.records.push_back({outlet,m});
    }
};
static Definition unpackNode(std::initializer_list<Format> formats) {
    Definition d;d.op=Op::unpack;d.formats=formats;
    for(size_t i=0;i<formats.size();++i)d.atoms.push_back(Atom::integral(0));
    return d;
}
static void drain(Runtime& rt) {
    std::array<float,64> l{},r{};rendering=true;
    rt.render(nullptr,nullptr,l.data(),r.data(),64);
    rendering=false;assert(allocations==0);
}
int main() {
    // Default unpack is two integer outlets; elements leave right to left.
    {
        Log log;Symbols symbols;
        Runtime rt(std::vector<Definition>{unpackNode({Format::integer,Format::integer})},std::vector<Edge>{},48000,symbols,Log::trace,&log);
        assert(rt.send(0,0,Message::list({Atom::integral(11),Atom::integral(22)})));
        drain(rt);assert(!rt.faulted());
        assert(log.records.size()==2);
        assert(log.records[0].outlet==1 && log.records[0].message.atoms[0].value.integer==22);
        assert(log.records[1].outlet==0 && log.records[1].message.atoms[0].value.integer==11);
    }
    // Declared argument types convert rather than pass through: a float into an
    // integer outlet truncates, an integer into a float outlet promotes.
    {
        Log log;Symbols symbols;
        Runtime rt(std::vector<Definition>{unpackNode({Format::integer,Format::floating})},std::vector<Edge>{},48000,symbols,Log::trace,&log);
        assert(rt.send(0,0,Message::list({Atom::real(7.9),Atom::integral(3)})));
        drain(rt);assert(!rt.faulted());
        assert(log.records.size()==2);
        assert(log.records[0].outlet==1 && log.records[0].message.atoms[0].type==Atom::Type::floating);
        assert(log.records[0].message.atoms[0].value.floating==3.);
        assert(log.records[1].outlet==0 && log.records[1].message.atoms[0].type==Atom::Type::integer);
        assert(log.records[1].message.atoms[0].value.integer==7);
    }
    // A short list only drives the outlets it reached; the rest stay silent.
    // A long list ignores the remainder instead of faulting.
    {
        Log log;Symbols symbols;
        Runtime rt(std::vector<Definition>{unpackNode({Format::integer,Format::integer,Format::integer})},std::vector<Edge>{},48000,symbols,Log::trace,&log);
        assert(rt.send(0,0,Message::list({Atom::integral(5),Atom::integral(6)})));
        drain(rt);
        assert(log.records.size()==2 && log.records[0].outlet==1 && log.records[1].outlet==0);
        log.records.clear();
        assert(rt.send(0,0,Message::list({Atom::integral(1),Atom::integral(2),Atom::integral(3),Atom::integral(4)})));
        drain(rt);assert(!rt.faulted());
        assert(log.records.size()==3 && log.records[0].outlet==2);
        assert(log.records[0].message.atoms[0].value.integer==3);
    }
    // A lone number behaves as a one-element list and drives only outlet 0.
    {
        Log log;Symbols symbols;
        Runtime rt(std::vector<Definition>{unpackNode({Format::integer,Format::integer})},std::vector<Edge>{},48000,symbols,Log::trace,&log);
        assert(rt.send(0,0,Message::integer(42)));
        drain(rt);assert(!rt.faulted());
        assert(log.records.size()==1 && log.records[0].outlet==0);
        assert(log.records[0].message.atoms[0].value.integer==42);
    }
    // A symbol element has no numeric conversion and must fault rather than
    // silently reaching a numeric outlet as zero.
    {
        Log log;Symbols symbols;const Symbol name=symbols.intern("alpha");
        Runtime rt(std::vector<Definition>{unpackNode({Format::integer,Format::integer})},std::vector<Edge>{},48000,symbols,Log::trace,&log);
        Message m=Message::list({Atom::integral(1),Atom::named(name)});
        assert(rt.send(0,0,m));drain(rt);
        assert(rt.faulted());
    }
    // Preparation rejects what the runtime cannot model: fewer than two
    // outlets, and symbol-typed outlets.
    {
        bool failed=false;
        try {Runtime rt(std::vector<Definition>{unpackNode({Format::integer})},std::vector<Edge>{},48000);}
        catch(const std::invalid_argument&){failed=true;}
        assert(failed);
        failed=false;
        try {Runtime rt(std::vector<Definition>{unpackNode({Format::integer,Format::symbol})},std::vector<Edge>{},48000);}
        catch(const std::invalid_argument&){failed=true;}
        assert(failed);
    }
    std::cout<<"PASS: unpack right-to-left order, declared int/float conversion, short and long lists, lone number, symbol fault, preparation rejection, no render allocations. Max oracle comparison NOT run.\n";
}
