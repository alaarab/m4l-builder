#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>
// peek~ object index handling, MEASURED on Max 9 (September 11, peer probe
// peek_write.csv): the index is truncated toward zero and clamped to
// 0..frames-1 for both writes and reads (-2/-1/-0.5/0.5 -> cell 0, 126.6 ->
// 126, 127.5/128/200 -> cell 127); nothing is rejected. Gen's peek()/sample()
// differ (0 out of range) and are covered by gen_buffer_spec.
using namespace m4l::maxcompat;
struct Rec{int node,outlet;Message m;};
struct Log{std::vector<Rec> r;static void trace(void* c,int node,int outlet,uint64_t,const Message& m) noexcept{static_cast<Log*>(c)->r.push_back({node,outlet,m});}};
int main(){
    auto domain=std::make_shared<RoutingDomain>();
    Symbols symbols;const auto name=symbols.intern("cells");
    Definition storage;storage.op=Op::buffer;storage.arguments={128,1};storage.atoms={Atom::named(name)};
    Definition peek;peek.op=Op::peek;peek.atoms={Atom::named(name)};peek.arguments={1};
    Log log;
    Runtime rt(std::vector<Definition>{storage,peek},std::vector<Edge>{},44100,symbols,Log::trace,&log,std::vector<int>{},domain);
    domain->prepare();rt.initialize();
    std::array<float,64> l{},r{};
    auto write=[&](double index,double value){Message m;m.kind=Message::Kind::list;m.selector=sym::list;m.count=2;m.atoms[0]=Atom::real(index);m.atoms[1]=Atom::real(value);assert(rt.send(1,0,m));rt.render(nullptr,nullptr,l.data(),r.data(),64);};
    auto read=[&](double index){log.r.clear();assert(rt.send(1,0,Message::number(index)));rt.render(nullptr,nullptr,l.data(),r.data(),64);assert(log.r.size()==1 && log.r[0].outlet==0);return log.r[0].m.atoms[0].number();};
    auto table=domain->buffers().at("cells");
    // Writes: each marker in isolation against a cleared buffer, as measured.
    const double cases[][2]={{-2,0},{-1,0},{-0.5,0},{0,0},{0.5,0},{63.5,63},{126.4,126},{126.6,126},{127,127},{127.5,127},{128,127},{200,127}};
    for(const auto& c:cases) {
        table->clear();write(c[0],1);
        for(size_t i=0;i<128;++i)assert(table->peek(double(i),0)==(double(i)==c[1]?1:0));
    }
    // Reads on a ramp where cell k holds k+1.
    table->clear();for(size_t i=0;i<128;++i)table->poke(double(i+1),double(i),0);
    assert(read(-2)==1 && read(-1)==1 && read(-0.5)==1 && read(0)==1 && read(0.5)==1);
    assert(read(63.5)==64 && read(126.9)==127);
    assert(read(127)==128 && read(127.5)==128 && read(128)==128 && read(200)==128);
    assert(!rt.faulted());
    {
        // MEASURED: buffer~ names are global across devices; a second device
        // declaring the same plain name (same size) shares the storage.
        auto shared=std::make_shared<RoutingDomain>();
        Symbols a,b;const auto na=a.intern("scope"),nb=b.intern("scope");
        Definition da;da.op=Op::buffer;da.arguments={64,1};da.atoms={Atom::named(na)};
        Definition db;db.op=Op::buffer;db.arguments={64,1};db.atoms={Atom::named(nb)};
        Runtime first(std::vector<Definition>{da},std::vector<Edge>{},44100,a,nullptr,nullptr,std::vector<int>{},shared);
        Runtime second(std::vector<Definition>{db},std::vector<Edge>{},44100,b,nullptr,nullptr,std::vector<int>{},shared);
        shared->prepare();first.initialize();second.initialize();
        first.externalBufferForWriting("scope")->poke(0.5,3,0);
        assert(second.externalBuffer("scope")->peek(3,0)==0.5);
        // MEASURED: the first declaration fixes the size; a later different or
        // unsized declaration binds to it unchanged (200 then 400 -> 200 ms;
        // 400 then 200 -> 400 ms; unsized after sized -> untouched).
        Definition dc;dc.op=Op::buffer;dc.arguments={32,1};dc.atoms={Atom::named(nb)};
        Definition du;du.op=Op::buffer;du.arguments={0,0};du.atoms={Atom::named(nb)};
        auto other=std::make_shared<RoutingDomain>();
        Runtime x(std::vector<Definition>{db},std::vector<Edge>{},44100,b,nullptr,nullptr,std::vector<int>{},other);
        Runtime y(std::vector<Definition>{dc},std::vector<Edge>{},44100,b,nullptr,nullptr,std::vector<int>{},other);
        Runtime z(std::vector<Definition>{du},std::vector<Edge>{},44100,b,nullptr,nullptr,std::vector<int>{},other);
        other->prepare();x.initialize();y.initialize();z.initialize();
        assert(other->buffers().at("scope")->frames()==64 && y.externalBuffer("scope")->frames()==64 && z.externalBuffer("scope")->frames()==64);
        auto reversed=std::make_shared<RoutingDomain>();
        Runtime y2(std::vector<Definition>{dc},std::vector<Edge>{},44100,b,nullptr,nullptr,std::vector<int>{},reversed);
        Runtime x2(std::vector<Definition>{db},std::vector<Edge>{},44100,b,nullptr,nullptr,std::vector<int>{},reversed);
        reversed->prepare();assert(reversed->buffers().at("scope")->frames()==32);
    }
    std::cout<<"PASS: peek~ truncates and clamps its index to 0..frames-1 for writes and reads (12 measured write cases, 11 measured reads); same-named buffer~ across devices shares storage with the first declaration's size (measured)\n";
}
