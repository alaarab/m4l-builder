#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
static bool callback=false;static size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
struct Log {
    std::array<Message,128> events{};size_t count=0;
    static void trace(void* context,int,int,uint64_t,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(context);assert(log.count<log.events.size());log.events[log.count++]=m;
    }
};
static void flush(Runtime& r){callback=true;r.render(nullptr,nullptr,nullptr,nullptr,0);callback=false;}
static Message command(Symbol selector,std::initializer_list<Atom> args){auto m=Message::list(args);m.kind=Message::Kind::anything;m.selector=selector;return m;}
int main(){
    Symbols symbols;const auto first=symbols.intern("first"),second=symbols.intern("second"),bus=symbols.intern("bus"),max=symbols.intern("max");
    Definition message;message.op=Op::message;
    message.atoms={Atom::named(first),Atom{},Atom{},Atom::named(sym::comma),Atom::named(second),Atom{}};
    message.substitutions={-1,0,1,-1,-1,1};message.separators={0,0,0,1,0,0};
    Log log;auto runtime=std::make_unique<Runtime>(std::vector<Definition>{message},std::vector<Edge>{},48000,symbols,Log::trace,&log);
    assert(runtime->send(0,0,Message::list({Atom::integral(9007199254740993LL),Atom::real(.5)})));flush(*runtime);
    assert(log.count==2 && log.events[0].atoms[0].value.integer==9007199254740993LL);
    assert(runtime->send(0,0,Message::integer(9)));flush(*runtime);
    assert(log.count==4 && log.events[2].atoms[0].value.integer==9 && log.events[2].atoms[1].number()==.5 && log.events[3].atoms[0].number()==.5);
    assert(runtime->send(0,0,command(sym::setargs,{Atom::integral(6),Atom::integral(7)})));flush(*runtime);assert(log.count==4);
    assert(runtime->send(0,0,{}));flush(*runtime);assert(log.count==6 && log.events[4].atoms[0].number()==6 && log.events[4].atoms[1].number()==7);
    // Cold-inlet set is literal text, whereas the hot-inlet set edits contents.
    assert(runtime->send(0,1,command(sym::set,{Atom::named(first),Atom::integral(3)})));flush(*runtime);assert(log.count==6);
    assert(runtime->send(0,0,{}));flush(*runtime);assert(log.events[6].selector==sym::set && log.events[6].atoms[1].number()==3);
    assert(runtime->send(0,0,command(sym::set,{})));flush(*runtime);
    assert(runtime->send(0,0,{}));flush(*runtime);assert(log.count==7);
    assert(runtime->send(0,0,command(sym::set,{Atom::named(first),Atom::integral(1)})));flush(*runtime);
    assert(runtime->send(0,0,command(sym::append,{Atom::named(sym::comma),Atom::named(second),Atom::integral(2)})));flush(*runtime);
    assert(runtime->send(0,0,command(sym::prepend,{Atom::named(sym::bang),Atom::named(sym::comma)})));flush(*runtime);
    assert(runtime->send(0,0,{}));flush(*runtime);assert(log.count==10 && log.events[7].kind==Message::Kind::bang && log.events[8].selector==first && log.events[9].selector==second);
    // Semicolon routing retains its receiver across commas; state stays local.
    Definition receive;receive.op=Op::namedReceive;receive.atoms={Atom::named(bus)};
    Definition send;send.op=Op::message;send.atoms={Atom::named(sym::semicolon),Atom::named(bus),Atom::integral(7),Atom::named(sym::comma),Atom::integral(8)};send.separators={2,0,0,1,0};
    Log named;auto routes=std::make_unique<Runtime>(std::vector<Definition>{send,receive},std::vector<Edge>{},48000,symbols,Log::trace,&named);
    assert(routes->send(0,0,{}));flush(*routes);assert(named.count==2 && named.events[0].atoms[0].number()==7 && named.events[1].atoms[0].number()==8);
    // Host/system services cannot silently disappear as unmatched named buses.
    assert(routes->send(0,0,command(sym::set,{Atom::named(sym::semicolon),Atom::named(max),Atom::named(sym::bang)})));flush(*routes);
    assert(routes->send(0,0,{}));flush(*routes);assert(routes->faulted());
    auto loop=std::make_unique<Runtime>(std::vector<Definition>{send,receive},std::vector<Edge>{{1,0,0,0}},48000,symbols);
    assert(loop->send(0,0,{}));flush(*loop);assert(loop->faulted());
    // Overflow must fault before copying outside bounded message storage.
    Message full;full.kind=Message::Kind::anything;full.selector=sym::set;full.count=Message::capacity;
    for(auto& a:full.atoms)a=Atom::integral(1);
    assert(runtime->send(0,0,full));flush(*runtime);assert(!runtime->faulted());
    assert(runtime->send(0,0,command(sym::append,{Atom::integral(2)})));flush(*runtime);assert(runtime->faulted());
    bool rejected=false;message.separators[0]=3;
    try{Runtime bad({message},{},48000,symbols);}catch(const std::invalid_argument&){rejected=true;}
    assert(rejected && allocations==0);
    std::cout<<"PASS: compound order/substitution retention, exact Int64, cold literal set, append/prepend/setargs, empty output, named routing, feedback/system/overflow containment and zero callback allocations.\n";
}
