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

struct Log {
    std::vector<Message> records;
    Log(){records.reserve(256);}
    static void trace(void* context,int,int,uint64_t,const Message& m) noexcept {
        auto& log=*static_cast<Log*>(context);assert(log.records.size()<log.records.capacity());
        log.records.push_back(m);
    }
};
static Definition node(Op op,std::initializer_list<Atom> atoms={}) {Definition d;d.op=op;d.atoms=atoms;return d;}
static void drain(Runtime& rt) {
    std::array<float,64> l{},r{};rendering=true;
    rt.render(nullptr,nullptr,l.data(),r.data(),64);
    rendering=false;assert(allocations==0);
}
static Log run(const Definition& d,std::initializer_list<std::pair<int,Message>> sends,double rate=48000) {
    static Log log;log.records.clear();
    Symbols symbols;
    Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},rate,symbols,Log::trace,&log);
    for(const auto& s:sends) assert(rt.send(0,s.first,s.second));   // pair = (inlet, message) on the single node
    drain(rt);assert(!rt.faulted());
    return log;
}
int main() {
    // clip clamps to its prepared bounds and keeps the declared numeric type.
    {
        auto d=node(Op::clip,{Atom::integral(0),Atom::integral(15)});
        auto log=run(d,{{0,Message::integer(99)},{0,Message::integer(-4)},{0,Message::integer(7)}});
        assert(log.records.size()==3);
        assert(log.records[0].atoms[0].type==Atom::Type::integer && log.records[0].atoms[0].value.integer==15);
        assert(log.records[1].atoms[0].value.integer==0);
        assert(log.records[2].atoms[0].value.integer==7);
    }
    // Float bounds keep float output and clamp without rounding.
    {
        auto d=node(Op::clip,{Atom::real(20.),Atom::real(8000.)});
        auto log=run(d,{{0,Message::number(12345.5)},{0,Message::number(19.25)},{0,Message::number(440.5)}});
        assert(log.records.size()==3);
        assert(log.records[0].atoms[0].type==Atom::Type::floating && log.records[0].atoms[0].value.floating==8000.);
        assert(log.records[1].atoms[0].value.floating==20.);
        assert(log.records[2].atoms[0].value.floating==440.5);
    }
    // Control modulo is integer arithmetic; a zero divisor yields zero rather
    // than faulting, matching the captured expr behaviour.
    {
        auto d=node(Op::controlModulo,{Atom::integral(4)});
        auto log=run(d,{{0,Message::integer(7)},{0,Message::integer(-7)},{0,Message::integer(8)}});
        assert(log.records.size()==3);
        assert(log.records[0].atoms[0].value.integer==3);
        assert(log.records[1].atoms[0].value.integer==-3);
        assert(log.records[2].atoms[0].value.integer==0);
    }
    {
        auto d=node(Op::controlModulo,{Atom::integral(0)});
        auto log=run(d,{{0,Message::integer(9)}});
        assert(log.records.size()==1 && log.records[0].atoms[0].value.integer==0);
    }
    // scale maps the prepared input span onto the output span linearly, and a
    // degenerate input span reports the output low bound instead of dividing.
    {
        auto d=node(Op::scale,{Atom::real(0.),Atom::real(100.),Atom::real(0.),Atom::real(1.5)});
        auto log=run(d,{{0,Message::number(0.)},{0,Message::number(100.)},{0,Message::number(50.)},{0,Message::number(200.)}});
        assert(log.records.size()==4);
        assert(log.records[0].atoms[0].value.floating==0.);
        assert(log.records[1].atoms[0].value.floating==1.5);
        assert(log.records[2].atoms[0].value.floating==0.75);
        // Max does not clamp: input beyond the declared span extrapolates.
        assert(log.records[3].atoms[0].value.floating==3.);
    }
    {
        auto d=node(Op::scale,{Atom::real(5.),Atom::real(5.),Atom::real(2.),Atom::real(9.)});
        auto log=run(d,{{0,Message::number(5.)}});
        assert(log.records.size()==1 && log.records[0].atoms[0].value.floating==2.);
    }
    // adstatus reports the host sample rate on bang, at the prepared rate.
    for(double rate:{44100.,48000.,96000.}) {
        auto log=run(node(Op::adStatus),{{0,Message{}}},rate);
        assert(log.records.size()==1);
        assert(log.records[0].atoms[0].type==Atom::Type::integer);
        assert(log.records[0].atoms[0].value.integer==int64_t(rate));
    }
    // Preparation rejects what the runtime does not model.
    {
        auto reject=[](const Definition& d){
            bool failed=false;
            try {Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000);}
            catch(const std::invalid_argument&){failed=true;}
            return failed;
        };
        assert(reject(node(Op::controlModulo,{Atom::real(4.)})));
        assert(reject(node(Op::clip,{Atom::integral(15),Atom::integral(0)})));
        assert(reject(node(Op::clip,{Atom::integral(0),Atom::real(15.)})));
        assert(reject(node(Op::clip,{Atom::integral(0)})));
        assert(reject(node(Op::scale,{Atom::real(0.),Atom::real(1.)})));
        assert(reject(node(Op::adStatus,{Atom::integral(1)})));
    }
    std::cout<<"PASS: clip int/float clamping, integer modulo incl. zero divisor, linear scale with extrapolation and degenerate span, adstatus sample rate at 44.1/48/96k, preparation rejection, no render allocations. Max oracle comparison NOT run.\n";
}
// Comparison family appended: int/float typing from the argument, cold right
// inlet, int 0/1 result.
static int compare_tests() {
    auto run2=[](Op op,std::initializer_list<Atom> atoms,std::initializer_list<std::pair<int,Message>> sends){
        Definition d;d.op=op;d.atoms=atoms;return run(d,sends);};
    {auto log=run2(Op::compareEqual,{Atom::integral(3)},{{0,Message::integer(3)},{0,Message::integer(4)},{0,Message::number(3.7)}});
     assert(log.records.size()==3);assert(log.records[0].atoms[0].value.integer==1);assert(log.records[1].atoms[0].value.integer==0);assert(log.records[2].atoms[0].value.integer==1);}
    {auto log=run2(Op::compareGreater,{Atom::real(0.5)},{{0,Message::number(0.75)},{1,Message::number(0.9)},{0,Message::number(0.75)}});
     assert(log.records.size()==2);assert(log.records[0].atoms[0].value.integer==1);assert(log.records[1].atoms[0].value.integer==0);}
    {auto log=run2(Op::compareLessEqual,{},{{0,Message::integer(0)},{0,Message::integer(1)}});
     assert(log.records.size()==2);assert(log.records[0].atoms[0].value.integer==1);assert(log.records[1].atoms[0].value.integer==0);}
    return 0;
}
static const int compare_ran=compare_tests();
static int maxmin_tests() {
    auto run2=[](Op op,std::initializer_list<Atom> atoms,std::initializer_list<std::pair<int,Message>> sends){Definition d;d.op=op;d.atoms=atoms;return run(d,sends);};
    {auto log=run2(Op::controlMaximum,{Atom::real(0.)},{{0,Message::number(-3.5)},{0,Message::number(2.25)},{1,Message::number(5.)},{0,Message::number(2.25)}});
     assert(log.records.size()==3);assert(log.records[0].atoms[0].value.floating==0.);assert(log.records[1].atoms[0].value.floating==2.25);assert(log.records[2].atoms[0].value.floating==5.);}
    {auto log=run2(Op::controlMinimum,{Atom::integral(10)},{{0,Message::integer(12)},{0,Message::number(3.9)}});
     assert(log.records.size()==2);assert(log.records[0].atoms[0].type==Atom::Type::integer && log.records[0].atoms[0].value.integer==10);assert(log.records[1].atoms[0].value.integer==3);}
    return 0;
}
static const int maxmin_ran=maxmin_tests();
// !-~ appended: right minus left, constant operand from the argument.
static int reverse_subtract_signal_tests() {
    Definition in;in.op=Op::input; Definition rs;rs.op=Op::reverseSubtractSignal;rs.arguments={1.}; Definition out;out.op=Op::output;
    Symbols sy;Runtime rt(std::vector<Definition>{in,rs,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},48000,sy);
    rt.setDSPActive(true);
    std::array<float,64> l{},r{},ol{},orr{};l.fill(0.25f);r.fill(0.25f);
    rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;assert(allocations==0);
    assert(std::abs(ol[63]-0.75)<1e-6);
    assert(rt.send(1,1,Message::number(2.)));rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;
    assert(std::abs(ol[63]-1.75)<1e-6);assert(!rt.faulted());
    return 0;
}
static const int reverse_subtract_ran=reverse_subtract_signal_tests();
// average~ appended: sliding mean of |x| over the window, incremental sum.
static int average_signal_tests() {
    Definition in;in.op=Op::input; Definition av;av.op=Op::averageSignal;av.arguments={4}; Definition out;out.op=Op::output;
    Symbols sy;Runtime rt(std::vector<Definition>{in,av,out},std::vector<Edge>{{0,0,1,0},{1,0,2,0},{1,0,2,1}},48000,sy);
    rt.setDSPActive(true);
    std::array<float,8> l{},r{},ol{},orr{};
    for(size_t i=0;i<8;++i)l[i]=(i%2?-1.f:1.f)*float(i+1);   // |x| = 1..8
    rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),8);rendering=false;assert(allocations==0);
    // window 4: sample 3 -> (1+2+3+4)/4 = 2.5 ; sample 7 -> (5+6+7+8)/4 = 6.5 ; before the window fills, zeros count.
    assert(std::abs(ol[0]-0.25)<1e-6 && std::abs(ol[3]-2.5)<1e-6 && std::abs(ol[7]-6.5)<1e-6);
    bool f=false;Definition bad;bad.op=Op::averageSignal;bad.arguments={0};try{Runtime r2(std::vector<Definition>{bad},std::vector<Edge>{},48000);}catch(const std::invalid_argument&){f=true;}assert(f);
    return 0;
}
static const int average_ran=average_signal_tests();
// if appended: the corpus form 'if $f1 > $f2 * 1.5 then 1' — no else, cold right inlet.
static int conditional_tests() {
    Definition d;d.op=Op::conditional;d.expression="$f1 > $f2 * 1.5";d.arguments={2,1,0,0};d.integers={true,false};
    auto log=run(d,{{1,Message::number(2.)},{0,Message::number(3.5)},{0,Message::number(2.5)},{0,Message::number(4.)}});
    // 3.5 > 3 -> 1 ; 2.5 > 3 false, no else -> nothing ; 4 > 3 -> 1
    assert(log.records.size()==2);
    assert(log.records[0].atoms[0].type==Atom::Type::integer && log.records[0].atoms[0].value.integer==1);
    Definition e=d;e.arguments={2,1,1,7};e.integers={true,true};
    auto log2=run(e,{{1,Message::number(2.)},{0,Message::number(1.)}});
    assert(log2.records.size()==1 && log2.records[0].atoms[0].value.integer==7);
    return 0;
}
static const int conditional_ran=conditional_tests();
// zl len / zl group appended.
static int zl_tests() {
    Definition len;len.op=Op::zlLength;
    auto log=run(len,{{0,Message::list({Atom::integral(1),Atom::integral(2),Atom::integral(3)})},{0,Message::integer(9)},{0,Message{}}});
    assert(log.records.size()==3 && log.records[0].atoms[0].value.integer==3 && log.records[1].atoms[0].value.integer==1 && log.records[2].atoms[0].value.integer==0);
    Definition g;g.op=Op::zlGroup;g.arguments={3};
    auto lg=run(g,{{0,Message::integer(1)},{0,Message::integer(2)},{0,Message::list({Atom::integral(3),Atom::integral(4)})},{0,Message{}}});
    // 1,2 held; list 3,4 completes [1 2 3] and holds 4; bang flushes [4]
    assert(lg.records.size()==2 && lg.records[0].count==3 && lg.records[0].atoms[2].value.integer==3 && lg.records[1].count==1 && lg.records[1].atoms[0].value.integer==4);
    return 0;
}
static const int zl_ran=zl_tests();
// listfunnel appended.
static int listfunnel_tests() {
    Definition d;d.op=Op::listFunnel;d.arguments={1};
    auto log=run(d,{{0,Message::list({Atom::real(0.5),Atom::integral(7)})},{0,Message::integer(3)}});
    assert(log.records.size()==3);
    assert(log.records[0].count==2 && log.records[0].atoms[0].value.integer==1 && log.records[0].atoms[1].value.floating==0.5);
    assert(log.records[1].atoms[0].value.integer==2 && log.records[1].atoms[1].value.integer==7);
    assert(log.records[2].atoms[0].value.integer==1 && log.records[2].atoms[1].value.integer==3);
    return 0;
}
static const int listfunnel_ran=listfunnel_tests();
// spray appended: routes [index value] to outlet index-offset; out of range is dropped.
static int spray_tests() {
    struct L{std::vector<std::pair<int,Message>> r;static void t(void* c,int,int o,uint64_t,const Message& m) noexcept{static_cast<L*>(c)->r.emplace_back(o,m);}} l;l.r.reserve(8);
    Definition d;d.op=Op::spray;d.arguments={3,1};Symbols sy;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,L::t,&l);
    assert(rt.send(0,0,Message::list({Atom::integral(2),Atom::real(0.5)})));
    assert(rt.send(0,0,Message::list({Atom::integral(9),Atom::integral(1)})));
    assert(rt.send(0,0,Message::list({Atom::integral(1),Atom::integral(4),Atom::integral(5)})));
    std::array<float,64> a{},b{};rendering=true;rt.render(nullptr,nullptr,a.data(),b.data(),64);rendering=false;assert(allocations==0);assert(!rt.faulted());
    assert(l.r.size()==2 && l.r[0].first==1 && l.r[0].second.atoms[0].value.floating==0.5 && l.r[1].first==0 && l.r[1].second.count==2);
    return 0;
}
static const int spray_ran=spray_tests();
// uzi appended: index (outlet 2) then bang (outlet 0) per iteration, done bang on outlet 1.
static int uzi_tests() {
    struct L{std::vector<std::pair<int,Message>> r;static void t(void* c,int,int o,uint64_t,const Message& m) noexcept{static_cast<L*>(c)->r.emplace_back(o,m);}} l;l.r.reserve(32);
    Definition d;d.op=Op::uzi;d.arguments={3,1};Symbols sy;Runtime rt(std::vector<Definition>{d},std::vector<Edge>{},48000,sy,L::t,&l);
    assert(rt.send(0,0,Message{}));std::array<float,64> a{},b{};rendering=true;rt.render(nullptr,nullptr,a.data(),b.data(),64);rendering=false;assert(allocations==0);assert(!rt.faulted());
    assert(l.r.size()==7);
    assert(l.r[0].first==2 && l.r[0].second.atoms[0].value.integer==1 && l.r[1].first==0 && l.r[1].second.kind==Message::Kind::bang);
    assert(l.r[4].first==2 && l.r[4].second.atoms[0].value.integer==3 && l.r[6].first==1);
    l.r.clear();assert(rt.send(0,0,Message::integer(2)));rendering=true;rt.render(nullptr,nullptr,a.data(),b.data(),64);rendering=false;   // int sets and fires
    assert(l.r.size()==5 && l.r[2].second.atoms[0].value.integer==2);
    Definition z;z.op=Op::uzi;z.arguments={65,0};L l2;l2.r.reserve(200);Runtime r2(std::vector<Definition>{z},std::vector<Edge>{},48000,sy,L::t,&l2);
    assert(r2.send(0,0,Message{}));rendering=true;r2.render(nullptr,nullptr,a.data(),b.data(),64);rendering=false;
    assert(l2.r.size()==131 && l2.r[0].second.atoms[0].value.integer==0 && l2.r[128].second.atoms[0].value.integer==64);
    return 0;
}
static const int uzi_ran=uzi_tests();
// atodb / sqrt control objects appended: 20*log10(x) and sqrt(x) as floats.
// The corpus clamps both inputs positive (maximum 1e-10) first; Max's output
// for x <= 0 (atodb) and x < 0 (sqrt) is NOT measured, so those fault visibly.
static int atodb_sqrt_tests() {
    Definition a;a.op=Op::atodb;Definition q;q.op=Op::squareRoot;
    auto la=run(a,{{0,Message::number(1)},{0,Message::number(0.5)},{0,Message::integer(10)}});
    assert(la.records.size()==3 && la.records[0].atoms[0].type==Atom::Type::floating && la.records[0].atoms[0].value.floating==0);
    assert(std::abs(la.records[1].atoms[0].value.floating-20*std::log10(0.5))<1e-12 && std::abs(la.records[2].atoms[0].value.floating-20)<1e-12);
    auto lq=run(q,{{0,Message::integer(4)},{0,Message::number(2.25)}});
    assert(lq.records.size()==2 && lq.records[0].atoms[0].type==Atom::Type::floating && lq.records[0].atoms[0].value.floating==2 && lq.records[1].atoms[0].value.floating==1.5);
    Symbols sy;Runtime bad(std::vector<Definition>{a},std::vector<Edge>{},48000,sy);
    assert(bad.send(0,0,Message::number(0)));std::array<float,64> x{},y{};rendering=true;bad.render(nullptr,nullptr,x.data(),y.data(),64);rendering=false;assert(bad.faulted());
    Runtime neg(std::vector<Definition>{q},std::vector<Edge>{},48000,sy);
    assert(neg.send(0,0,Message::number(-1)));rendering=true;neg.render(nullptr,nullptr,x.data(),y.data(),64);rendering=false;assert(neg.faulted());
    return 0;
}
static const int atodb_sqrt_ran=atodb_sqrt_tests();
