#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <memory>
#include <new>

static thread_local bool rendering=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n) {if(rendering)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
using namespace m4l::maxcompat;
struct Record {const char* test;int node,outlet;uint64_t time;Message message;};
struct Log {
    const char* test="";std::vector<Record> records;
    Log(){records.reserve(4096);}
    static void trace(void* context,int node,int outlet,uint64_t time,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(context);assert(log.records.size()<log.records.capacity());
        log.records.push_back({log.test,node,outlet,time,m});
    }
};
void process(Runtime& rt,int frames=0) {
    std::array<float,257> l{},r{};rendering=true;
    if(frames==0)rt.render(nullptr,nullptr,l.data(),r.data(),0);
    while(frames>0){const int n=std::min(frames,257);rt.render(nullptr,nullptr,l.data(),r.data(),n);frames-=n;}
    rendering=false;assert(allocations==0);
}
Message anything(Symbol selector,std::initializer_list<Atom> atoms={}) {
    auto m=Message::list(atoms);m.kind=Message::Kind::anything;m.selector=selector;return m;
}
Definition node(Op op,std::initializer_list<Atom> atoms={}) {Definition d;d.op=op;d.atoms=atoms;return d;}
void jsonAtom(const Atom& a,const Symbols& symbols) {
    if(a.type==Atom::Type::integer)std::cout<<a.value.integer;
    else if(a.type==Atom::Type::floating)std::cout<<std::setprecision(17)<<a.value.floating;
    else std::cout<<std::quoted(symbols.name(a.value.symbol));
}
int main() {
    Symbols symbols;const Symbol alpha=symbols.intern("alpha"),beta=symbols.intern("beta"),gamma=symbols.intern("gamma"),a=symbols.intern("a"),freq=symbols.intern("freq"),gain=symbols.intern("gain"),placeholder=symbols.intern("$1");
    auto trigger=node(Op::trigger,{Atom{},Atom{},Atom{},Atom{},Atom{},Atom::named(a)});
    trigger.formats={Format::bang,Format::integer,Format::floating,Format::list,Format::symbol,Format::constant};
    auto route=node(Op::route,{Atom::named(alpha),Atom::named(beta),Atom::integral(3),Atom::named(sym::integer),Atom::named(sym::floating),Atom::named(sym::list),Atom::named(sym::bang),Atom::named(sym::symbol)});
    auto pack=node(Op::pack,{Atom::integral(0),Atom::real(0),Atom::named(sym::empty)});
    auto duplicate=node(Op::route,{Atom::named(alpha),Atom::named(alpha),Atom::integral(3),Atom::integral(3),Atom::named(sym::integer),Atom::named(sym::list)});
    Log golden;
    auto select=node(Op::select,{Atom::named(alpha),Atom::named(alpha),Atom::integral(3)});
    auto pak=pack;pak.op=Op::pak;
    std::vector<Definition> goldenNodes={trigger,route,pack,duplicate,select,node(Op::prepend,{Atom::named(freq)}),node(Op::append,{Atom::integral(2)}),node(Op::integer,{Atom::integral(4)}),node(Op::controlDivide,{Atom::integral(0)}),node(Op::controlDivide,{Atom::integral(2)}),node(Op::message),node(Op::pack,{Atom::named(sym::empty),Atom::real(0)}),pak};
    for(auto op:{Op::controlAdd,Op::controlSubtract,Op::controlMultiply,Op::controlDivide,Op::reverseSubtract}) {
        goldenNodes.push_back(node(op,{Atom::integral(2)}));goldenNodes.push_back(node(op,{Atom::real(.5)}));
    }
    auto rt=std::make_unique<Runtime>(goldenNodes,std::vector<Edge>{},48000,symbols,Log::trace,&golden);
    auto run=[&](const char* name,int target,const Message& m){golden.test=name;assert(rt->send(target,0,m));process(*rt);assert(!rt->faulted());};
    run("trigger.bang",0,{});run("trigger.int",0,Message::integer(7));run("trigger.float",0,Message::number(7.75));
    run("trigger.list",0,Message::list({Atom::integral(3),Atom::real(2.5),Atom::named(alpha)}));
    run("trigger.anything",0,anything(alpha,{Atom::integral(3),Atom::real(2.5)}));run("trigger.symbol",0,Message::symbol(alpha));
    run("route.alpha",1,anything(alpha,{Atom::integral(3),Atom::real(2.5)}));run("route.alpha.empty",1,anything(alpha));
    run("route.int",1,Message::integer(3));run("route.float",1,Message::number(3.5));
    run("route.list",1,Message::list({Atom::integral(3),Atom::real(2.5)}));run("route.symbol",1,Message::symbol(alpha));run("route.reject",1,anything(gamma,{Atom::integral(9)}));
    run("pack.list",2,Message::list({Atom::real(2.9),Atom::real(3.5),Atom::named(alpha),Atom::integral(7)}));
    run("pack.set",2,anything(sym::set,{Atom::integral(8),Atom::real(6.5),Atom::named(beta)}));run("pack.bang",2,{});
    run("route.duplicate.symbol",3,anything(alpha,{Atom::integral(9)}));run("route.duplicate.number",3,Message::integer(3));run("route.duplicate.list",3,Message::list({Atom::integral(3),Atom::integral(8)}));
    run("select.symbol",4,Message::symbol(alpha));run("select.anything",4,anything(alpha,{Atom::integral(8)}));run("select.int",4,Message::integer(3));run("select.list",4,Message::list({Atom::integral(3),Atom::integral(8)}));
    run("prepend.float",5,Message::number(3.5));run("prepend.bang",5,{});run("prepend.anything",5,anything(alpha,{Atom::integral(8)}));
    run("append.float",6,Message::number(3.5));run("append.bang",6,{});run("append.anything",6,anything(alpha,{Atom::integral(8)}));
    run("integer.bang",7,{});run("integer.float",7,Message::number(7.9));run("integer.list",7,Message::list({Atom::integral(3),Atom::integral(8)}));run("integer.set",7,anything(sym::set,{Atom::real(9.9)}));run("integer.afterset",7,{});run("division.zero",8,Message::integer(5));
    run("division.two",9,Message::integer(7));run("division.list",9,Message::list({Atom::integral(8),Atom::integral(3)}));run("division.afterlist",9,{});
    assert(rt->send(9,1,Message::integer(0)));process(*rt);run("division.coldzero",9,Message::integer(9));
    assert(rt->send(10,0,anything(sym::set,{Atom::named(gain),Atom::named(placeholder),Atom::integral(20)})));process(*rt);
    run("message.float",10,Message::number(0.5));run("message.bang",10,{});run("message.symbol",10,anything(alpha,{Atom::real(0.2)}));run("message.clear",10,anything(sym::clear));run("message.afterclear",10,{});
    run("pack.nth1",2,anything(sym::nth,{Atom::integral(1)}));run("pack.nth0",2,anything(sym::nth,{Atom::integral(0)}));run("pack.nth2",2,anything(sym::nth,{Atom::integral(2)}));run("pack.nth4",2,anything(sym::nth,{Atom::integral(4)}));run("pack.nth3",2,anything(sym::nth,{Atom::integral(3)}));run("pack.symbolfirst",11,Message::symbol(alpha));
    run("pak.list",12,Message::list({Atom::real(2.9),Atom::real(3.5),Atom::named(alpha)}));golden.test="pak.cold";assert(rt->send(12,1,Message::number(4.9)));process(*rt);
    run("pak.set",12,anything(sym::set,{Atom::integral(8),Atom::real(6.5),Atom::named(beta)}));run("pak.bang",12,{});
    const char* mathCases[]={"arithmetic.add.integer","arithmetic.add.float","arithmetic.subtract.integer","arithmetic.subtract.float","arithmetic.multiply.integer","arithmetic.multiply.float","arithmetic.divide.integer","arithmetic.divide.float","arithmetic.reverse.integer","arithmetic.reverse.float"};
    for(int i=0;i<10;++i)run(mathCases[i],13+i,Message::number(3.75));
    // Exact integer identity, conversion boundaries, hot/cold state and arithmetic.
    {
        Log log;auto integer=node(Op::integer);auto add=node(Op::controlAdd,{Atom::integral(1)});
        auto h=std::make_unique<Runtime>(std::vector<Definition>{integer,add},std::vector<Edge>{{0,0,1,0}},48000,symbols,Log::trace,&log);
        assert(h->send(0,1,Message::integer(9007199254740993LL)));process(*h);assert(log.records.empty());
        assert(h->send(0,0,{}));process(*h);assert(log.records.size()==2);
        assert(log.records[0].message.atoms[0].value.integer==9007199254740993LL);
        assert(log.records[1].message.atoms[0].value.integer==9007199254740994LL);
        assert(!Atom::integral(9007199254740993LL).equals(Atom::real(9007199254740992.)));
        assert(h->send(0,0,Message::number(9223372036854775808.)));process(*h);assert(h->faulted());
    }
    // Timer replacement/cancel, cold-inlet edits and exact unaligned sample time.
    for(double rate:{44100.,48000.,96000.}) {
        Log log;auto d=node(Op::delay);d.arguments={10};
        auto h=std::make_unique<Runtime>(std::vector<Definition>{d},std::vector<Edge>{},rate,symbols,Log::trace,&log);
        assert(h->send(0,0,{}));process(*h,100);
        assert(h->send(0,1,Message::number(20)));process(*h,int(rate*.01)-100);
        assert(log.records.empty());process(*h,1);assert(log.records.size()==1 && log.records[0].time==uint64_t(rate*.01));
        assert(h->send(0,0,{}));process(*h,100);assert(h->send(0,0,{}));process(*h,int(rate*.02));
        assert(log.records.size()==1);process(*h,1);assert(log.records.size()==2);
        assert(h->send(0,0,{}));assert(h->send(0,0,anything(sym::stop)));process(*h,int(rate));assert(log.records.size()==2);
    }
    // Low-priority feedback advances only one service turn at a time, in FIFO.
    {
        Log log;auto d=node(Op::deferlow);
        auto h=std::make_unique<Runtime>(std::vector<Definition>{d},std::vector<Edge>{{0,0,0,0}},48000,symbols,Log::trace,&log);
        assert(h->send(0,0,Message::integer(1)));assert(h->send(0,0,Message::integer(2)));process(*h);assert(log.records.empty());
        process(*h);assert(log.records.size()==2 && log.records[0].message.atoms[0].value.integer==1 && log.records[1].message.atoms[0].value.integer==2);
        process(*h);assert(log.records.size()==4 && !h->faulted());
    }
    // Actual Max flat-patcher initialization probe emits last serialized first.
    {
        Log log;std::vector<Definition> defs;
        for(int i=0;i<8;++i)defs.push_back(node(Op::loadmess,{Atom::integral(i)}));
        auto h=std::make_unique<Runtime>(defs,std::vector<Edge>{},48000,symbols,Log::trace,&log);
        assert(log.records.size()==8);
        for(int i=0;i<8;++i)assert(log.records[i].message.atoms[0].value.integer==7-i);
    }
    // Instantaneous timer cycles fault within budget instead of hanging audio.
    {
        auto h=std::make_unique<Runtime>(std::vector<Definition>{node(Op::delay)},std::vector<Edge>{{0,0,0,0}},48000);
        assert(h->send(0,0,{}));process(*h,1);assert(h->faulted());
    }
    // Expanded atom payloads must not turn deep synchronous graphs into an
    // unbounded stack traversal. The explicit depth guard also covers fan-out.
    for(int count:{64,66}) {
        auto passthrough=node(Op::trigger,{Atom{}});passthrough.formats={Format::list};
        std::vector<Definition> definitions(size_t(count),passthrough);std::vector<Edge> edges;
        for(int i=0;i<count-1;++i)edges.push_back({i,0,i+1,0});
        auto h=std::make_unique<Runtime>(definitions,edges,48000);
        assert(h->send(0,0,Message::integer(1)));process(*h);
        assert(h->faulted()==(count==66));
    }
    // Encode after rendering; the callback never formats JSON or allocates.
    std::cout<<"{\"events\":[";bool comma=false;
    for(const auto& e:golden.records) {
        if(comma)std::cout<<',';comma=true;
        std::cout<<"{\"test\":"<<std::quoted(e.test)<<",\"outlet\":"<<(e.node==2?10:e.node==9?15:e.node==10?16:e.node>=5?e.node+7:e.outlet)<<",\"selector\":"<<std::quoted(symbols.name(e.message.selector))<<",\"args\":[";
        for(int i=0;i<e.message.count;++i){if(i)std::cout<<',';jsonAtom(e.message.atoms[i],symbols);}std::cout<<"]}";
    }
    std::cout<<"],\"nativeChecks\":\"Int64 identity/overflow, cold state, delay replace/cancel at44.1/48/96k, deferred FIFO feedback, runaway containment, no callback allocations PASS\"}\n";
}
