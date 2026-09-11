// sprintf without symout: the formatted text is re-parsed into atoms, so the
// literal words of the format are the only symbols and they are interned at
// construction. Corpus forms: "sprintf CORR %.2f", "sprintf %.1f dB",
// "sprintf set %.1f LU", "sprintf set FOUND %d". The re-parse rule (numbers
// become numbers, "%.0f" yields an int) is Max's documented behaviour, not
// yet a Live capture; how a live.comment then renders 0.5 vs 0.50 is a
// separate host-side question, labelled unmeasured.
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
    std::vector<Record> records;Log(){records.reserve(256);}
    static void trace(void* context,int,int outlet,uint64_t,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(context);assert(log.records.size()<log.records.capacity());log.records.push_back({outlet,m});
    }
};
static void drain(Runtime& rt) {std::array<float,64> l{},r{};rendering=true;rt.render(nullptr,nullptr,l.data(),r.data(),64);rendering=false;assert(allocations==0);}
// tokens: pairs of (text, code). code 0 literal, 1 %d, 2 %s, 3+P %.Pf
static Definition sprintfNode(Symbols& sy,std::vector<std::pair<std::string,int>> tokens) {
    Definition d;d.op=Op::sprintf;
    for(const auto& t:tokens) {d.atoms.push_back(Atom::named(sy.intern(t.first)));d.arguments.push_back(t.second);}
    return d;
}
int main() {
    Symbols sy;
    const Symbol corr=sy.intern("CORR"),dB=sy.intern("dB"),LU=sy.intern("LU"),FOUND=sy.intern("FOUND");
    Definition a=sprintfNode(sy,{{"CORR",0},{"%.2f",3+2}});
    Definition b=sprintfNode(sy,{{"%.1f",3+1},{"dB",0}});
    Definition c=sprintfNode(sy,{{"set",0},{"%.1f",3+1},{"LU",0}});
    Definition e=sprintfNode(sy,{{"set",0},{"FOUND",0},{"%d",1}});
    Definition two=sprintfNode(sy,{{"%d",1},{"%.0f",3+0},{"%s",2}});
    Log log;
    Runtime rt(std::vector<Definition>{a,b,c,e,two},std::vector<Edge>{},48000,sy,Log::trace,&log);
    // CORR %.2f of 0.5 -> "CORR 0.50" -> anything CORR with the float 0.5
    assert(rt.send(0,0,Message::number(0.5)));drain(rt);
    assert(log.records.size()==1);{const auto& m=log.records[0].message;assert(m.kind==Message::Kind::anything && m.selector==corr && m.count==1 && m.atoms[0].type==Atom::Type::floating && m.atoms[0].value.floating==0.5);}
    // %.1f dB of -0.25 -> "-0.2 dB" (printf rounding, half to even here) -> list -0.2 dB
    assert(rt.send(1,0,Message::number(-0.25)));drain(rt);
    assert(log.records.size()==2);{const auto& m=log.records[1].message;assert(m.kind==Message::Kind::list && m.count==2 && m.atoms[0].value.floating==-0.2 && m.atoms[1].type==Atom::Type::symbol && m.atoms[1].value.symbol==dB);}
    // set %.1f LU of -70 -> set -70.0 LU: 'set' selector, float -70, LU
    assert(rt.send(2,0,Message::integer(-70)));drain(rt);
    assert(log.records.size()==3);{const auto& m=log.records[2].message;assert(m.kind==Message::Kind::anything && m.selector==sym::set && m.count==2 && m.atoms[0].type==Atom::Type::floating && m.atoms[0].value.floating==-70 && m.atoms[1].value.symbol==LU);}
    // set FOUND %d of 3.9 -> set FOUND 3 (truncation)
    assert(rt.send(3,0,Message::number(3.9)));drain(rt);
    assert(log.records.size()==4);{const auto& m=log.records[3].message;assert(m.selector==sym::set && m.count==2 && m.atoms[0].value.symbol==FOUND && m.atoms[1].type==Atom::Type::integer && m.atoms[1].value.integer==3);}
    // Three slots: right inlets store cold; a list in the left inlet spreads;
    // bang re-emits the stored slots; "%.0f" of 12.4 re-parses as int 12.
    assert(rt.send(4,2,Message::symbol(dB)));drain(rt);assert(log.records.size()==4);
    assert(rt.send(4,1,Message::number(12.4)));drain(rt);assert(log.records.size()==4);
    assert(rt.send(4,0,Message::integer(7)));drain(rt);
    assert(log.records.size()==5);{const auto& m=log.records[4].message;assert(m.kind==Message::Kind::list && m.count==3 && m.atoms[0].value.integer==7 && m.atoms[1].type==Atom::Type::integer && m.atoms[1].value.integer==12 && m.atoms[2].value.symbol==dB);}
    Message spread=Message::sequence(std::array<Atom,3>{Atom::integral(1),Atom::real(2.6),Atom::named(LU)}.data(),3);
    assert(rt.send(4,0,spread));drain(rt);
    assert(log.records.size()==6);{const auto& m=log.records[5].message;assert(m.count==3 && m.atoms[0].value.integer==1 && m.atoms[1].value.integer==3 && m.atoms[2].value.symbol==LU);}
    assert(rt.send(4,0,Message{}));drain(rt);
    assert(log.records.size()==7);{const auto& m=log.records[6].message;assert(m.count==3 && m.atoms[0].value.integer==1 && m.atoms[1].value.integer==3 && m.atoms[2].value.symbol==LU);}
    assert(!rt.faulted());
    // A symbol into a numeric conversion is refused visibly (unmeasured in Max).
    assert(rt.send(0,0,Message::symbol(dB)));drain(rt);assert(rt.faulted());
    // Construction rejects a slot code the runtime does not model.
    bool rejected=false;try{Definition bad=sprintfNode(sy,{{"%x",9}});bad.arguments={99};Runtime r(std::vector<Definition>{bad},std::vector<Edge>{},48000,sy);}catch(const std::invalid_argument&){rejected=true;}
    assert(rejected);
    std::cout<<"PASS: sprintf re-parsed output (float/int/literal/%s), cold slots, list spread, bang re-emit, visible refusals, zero render allocations\n";
    return 0;
}
