// Shard's control objects: random, pipe, metro (ms and note values), translate,
// accum, !/, split, stripnote, switch, notein/ctlin parsing, cpuclock and a
// bounded coll. Contracts follow the Max reference (labelled unmeasured where
// the runtime comments say so); random's sequence is deliberately not Max's.
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
struct Rec {int node,outlet;Message m;};
struct Log {std::vector<Rec> r;Log(){r.reserve(4096);}static void t(void* c,int node,int o,uint64_t,const Message& m) noexcept{auto& l=*static_cast<Log*>(c);assert(l.r.size()<l.r.capacity());l.r.push_back({node,o,m});}};
static void block(Runtime& rt,int n=1) {std::array<float,64> a{},b{};for(int i=0;i<n;++i){rendering=true;rt.render(nullptr,nullptr,a.data(),b.data(),64);rendering=false;assert(allocations==0);}}
static Message any(Symbol s,std::initializer_list<Atom> atoms={}) {Message m=Message::anything(s);m.count=0;for(const auto& a:atoms)m.atoms[size_t(m.count++)]=a;return m;}
int main(){
    Symbols sy;const Symbol seed=sy.intern("seed"),n16=sy.intern("16n"),n8=sy.intern("8n"),notevalues=sy.intern("notevalues"),ms=sy.intern("ms"),stop=sy.intern("stop"),
        clear=sy.intern("clear"),dump=sy.intern("dump"),remove=sy.intern("remove"),store=sy.intern("store");
    Definition rnd;rnd.op=Op::randomInt;rnd.arguments={100};
    Definition pipe;pipe.op=Op::pipe;pipe.arguments={0};pipe.atoms={Atom::integral(0)};
    Definition metroMs;metroMs.op=Op::metro;metroMs.arguments={10};
    Definition metroNv;metroNv.op=Op::metro;metroNv.arguments={0.25};metroNv.atoms={Atom::named(n16)};
    Definition tr;tr.op=Op::translate;tr.atoms={Atom::named(notevalues),Atom::named(ms)};
    Definition acc;acc.op=Op::accum;acc.arguments={0};acc.atoms={Atom::integral(0)};
    Definition rdiv;rdiv.op=Op::reverseDivide;rdiv.atoms={Atom::real(1000.)};
    Definition split;split.op=Op::split;split.atoms={Atom::integral(1),Atom::integral(127)};
    Definition strip;strip.op=Op::stripNote;
    Definition sw;sw.op=Op::switchGate;sw.arguments={4};
    Definition ni;ni.op=Op::noteIn;Definition ci;ci.op=Op::ctlIn;ci.arguments={64};
    Definition clk;clk.op=Op::cpuClock;
    Definition coll;coll.op=Op::coll;
    Log log;
    Runtime rt(std::vector<Definition>{rnd,pipe,metroMs,metroNv,tr,acc,rdiv,split,strip,sw,ni,ci,clk,coll},std::vector<Edge>{},1000*8,sy,Log::t,&log);
    rt.setTransport(true,120,0);
    auto count=[&](int node,int outlet=-1){size_t c=0;for(const auto& r:log.r)if(r.node==node && (outlet<0 || r.outlet==outlet))++c;return c;};
    auto last=[&](int node,int outlet=0)->const Message&{for(size_t i=log.r.size();i-->0;)if(log.r[i].node==node && log.r[i].outlet==outlet)return log.r[i].m;assert(false);return log.r[0].m;};
    // random: bang -> [0,100); seeded sequences repeat.
    assert(rt.send(0,0,any(seed,{Atom::integral(7)})));for(int i=0;i<20;++i)assert(rt.send(0,0,Message{}));block(rt);
    std::vector<int64_t> first;for(const auto& r:log.r)if(r.node==0){assert(r.m.atoms[0].value.integer>=0 && r.m.atoms[0].value.integer<100);first.push_back(r.m.atoms[0].value.integer);}
    assert(first.size()==20);log.r.clear();
    assert(rt.send(0,0,any(seed,{Atom::integral(7)})));for(int i=0;i<20;++i)assert(rt.send(0,0,Message{}));block(rt);
    std::vector<int64_t> second;for(const auto& r:log.r)if(r.node==0)second.push_back(r.m.atoms[0].value.integer);
    assert(first==second);log.r.clear();
    // pipe: 5 ms delay at 8 kHz = 40 samples; two values keep order.
    assert(rt.send(1,1,Message::number(5)));assert(rt.send(1,0,Message::integer(3)));assert(rt.send(1,0,Message::integer(4)));
    block(rt);assert(count(1)==2 && log.r[0].m.atoms[0].value.integer==3 && log.r[1].m.atoms[0].value.integer==4);log.r.clear();
    // metro 10 ms: immediate bang, then every 80 samples; 'stop' ends it.
    assert(rt.send(2,0,Message::integer(1)));block(rt,4);   // 256 samples: bangs at 0,80,160,240
    assert(count(2)==4);assert(rt.send(2,0,any(stop)));block(rt,4);assert(count(2)==4);log.r.clear();
    // metro 16n at 120 BPM: a 16th is 125 ms = 1000 samples; fires on the grid while playing.
    assert(rt.send(3,0,Message::integer(1)));block(rt,32);   // 2048 samples
    assert(count(3)==2);rt.setTransport(false,120,0);log.r.clear();block(rt,32);assert(count(3)==0);rt.setTransport(true,120,0);
    assert(rt.send(3,0,Message::integer(0)));log.r.clear();
    // translate notevalues ms at 120 BPM: 16n -> 125, 8n -> 250.
    assert(rt.send(4,0,any(n16)));assert(rt.send(4,0,any(n8)));block(rt);
    assert(count(4)==2 && log.r[0].m.atoms[0].value.floating==125 && log.r[1].m.atoms[0].value.floating==250);log.r.clear();
    // accum: set 5, add 3, bang -> 8; left int sets without output.
    assert(rt.send(5,0,Message::integer(5)));assert(rt.send(5,1,Message::integer(3)));assert(rt.send(5,0,Message{}));block(rt);
    assert(count(5)==1 && last(5).atoms[0].value.integer==8);log.r.clear();
    // !/ 1000.: 4 -> 250.; zero divisor mirrors the measured [/] rule (outputs the dividend).
    assert(rt.send(6,0,Message::integer(4)));assert(rt.send(6,0,Message::integer(0)));block(rt);
    assert(count(6)==2 && log.r[0].m.atoms[0].value.floating==250 && log.r[1].m.atoms[0].value.floating==1000);log.r.clear();
    // split 1 127: 60 -> outlet 0, 0 -> outlet 1, 200 -> outlet 1.
    assert(rt.send(7,0,Message::integer(60)));assert(rt.send(7,0,Message::integer(0)));assert(rt.send(7,0,Message::integer(200)));block(rt);
    assert(count(7,0)==1 && count(7,1)==2);log.r.clear();
    // stripnote: velocity 0 dropped; otherwise velocity then note.
    assert(rt.send(8,1,Message::integer(0)));assert(rt.send(8,0,Message::integer(60)));assert(rt.send(8,1,Message::integer(90)));assert(rt.send(8,0,Message::integer(62)));block(rt);
    assert(count(8)==2 && log.r[0].outlet==1 && log.r[0].m.atoms[0].value.integer==90 && log.r[1].outlet==0 && log.r[1].m.atoms[0].value.integer==62);log.r.clear();
    // switch 4: select input 2; messages at inlet 2 pass, inlet 1 dropped.
    assert(rt.send(9,0,Message::integer(2)));assert(rt.send(9,1,Message::integer(11)));assert(rt.send(9,2,Message::number(2.5)));block(rt);
    assert(count(9)==1 && last(9).atoms[0].value.floating==2.5);log.r.clear();
    // notein / ctlin 64 from the byte stream: note on ch 1, running status, CC 64.
    for(int b:{0x90,60,100,62,0,0xB0,64,127,1,5})assert(rt.midiByte(b));block(rt);
    assert(count(10)==6);   // two notes x (channel, velocity, note)
    assert(log.r[0].node==10 && log.r[0].outlet==2 && log.r[0].m.atoms[0].value.integer==1 && log.r[1].outlet==1 && log.r[1].m.atoms[0].value.integer==100 && log.r[2].outlet==0 && log.r[2].m.atoms[0].value.integer==60);
    assert(count(11)==2);   // CC 64 only: channel then value
    {const auto& v=last(11,0);assert(v.atoms[0].value.integer==127);}
    log.r.clear();
    // cpuclock: bang -> positive milliseconds, non-decreasing.
    assert(rt.send(12,0,Message{}));assert(rt.send(12,0,Message{}));block(rt);
    assert(count(12)==2 && log.r[0].m.atoms[0].value.floating>0 && log.r[1].m.atoms[0].value.floating>=log.r[0].m.atoms[0].value.floating);log.r.clear();
    // coll: store lists, recall by int (index then data), remove, dump in index order with the done bang on outlet 3, clear.
    Atom e2[3]={Atom::integral(2),Atom::real(0.5),Atom::integral(7)};Atom e1[2]={Atom::integral(1),Atom::integral(9)};
    assert(rt.send(13,0,Message::sequence(e2,3)));assert(rt.send(13,0,Message::sequence(e1,2)));assert(rt.send(13,0,Message::integer(2)));assert(rt.send(13,0,Message::integer(5)));block(rt);
    assert(count(13)==2 && log.r[0].outlet==1 && log.r[0].m.atoms[0].value.integer==2 && log.r[1].outlet==0 && log.r[1].m.count==2 && log.r[1].m.atoms[0].value.floating==0.5);log.r.clear();
    assert(rt.send(13,0,any(dump)));block(rt);
    assert(count(13)==5 && log.r[0].m.atoms[0].value.integer==2 && log.r[2].m.atoms[0].value.integer==1 && log.r[4].outlet==3 && log.r[4].m.kind==Message::Kind::bang);log.r.clear();   // storage order (refpage)
    assert(rt.send(13,0,any(remove,{Atom::integral(1)})));assert(rt.send(13,0,any(store,{Atom::integral(3),Atom::integral(1)})));assert(rt.send(13,0,any(dump)));block(rt);
    assert(count(13,1)==2 && log.r[0].m.atoms[0].value.integer==2 && log.r[2].m.atoms[0].value.integer==3);log.r.clear();
    assert(rt.send(13,0,any(clear)));assert(rt.send(13,0,any(dump)));block(rt);assert(count(13)==1 && log.r[0].outlet==3);
    assert(!rt.faulted());
    std::cout<<"PASS: random/seed, pipe order, metro ms + 16n transport grid, translate, accum, !/, split, stripnote, switch, notein/ctlin parsing, cpuclock, coll store/recall/remove/dump (storage order, done bang on outlet 3)/clear, zero render allocations\n";
    return 0;
}
// Appended: mpeparse (Max 9 refpage outlet map, hires 1 pitch bend as float),
// info~ (ten outlets, bang reports sr/total ms/channels), live.adsr~ against
// the Live capture of [live.adsr~ 0.5 0 1 5.0] (1.0 by 5 ms, 1.0 through 205 ms
// after a 200 ms gate, 0.0 by 220 ms). Segment shape is linear (unmeasured).
static int mpe_info_adsr_tests() {
    Symbols sy;const Symbol buf=sy.intern("slicebuf");
    Definition mpe;mpe.op=Op::mpeParse;mpe.arguments={1};
    Definition buffer;buffer.op=Op::buffer;buffer.atoms={Atom::named(buf)};buffer.arguments={441,2};
    Definition info;info.op=Op::bufferInfo;info.atoms={Atom::named(buf)};
    Definition env;env.op=Op::adsr;env.arguments={0.5,0,1,5.0};
    Definition out;out.op=Op::output;
    Log log;Runtime rt(std::vector<Definition>{mpe,buffer,info,env,out},std::vector<Edge>{{3,0,4,0},{3,0,4,1}},44100,sy,Log::t,&log);
    rt.setDSPActive(true);
    auto at=[&](int node,int outlet)->const Message*{for(const auto& r:log.r)if(r.node==node && r.outlet==outlet)return &r.m;return nullptr;};
    // mpeparse: note on ch 2 (voice 0), pitch bend centre+1024 on ch 2 as a float, aftertouch int on ch 1 (voice -1).
    for(int b:{0x91,60,100,0xE1,0x00,0x50,0xD0,77})assert(rt.midiByte(b));block(rt);
    {const auto* note=at(0,0);assert(note && note->kind==Message::Kind::list && note->atoms[0].value.integer==60 && note->atoms[1].value.integer==100);
     const auto* voice=at(0,6);assert(voice && voice->atoms[0].value.integer==0);
     const auto* bend=at(0,5);assert(bend && bend->atoms[0].type==Atom::Type::floating && std::abs(bend->atoms[0].value.floating-((0x50<<7)-8192)/8192.)<1e-12);
     const auto* touch=at(0,4);assert(touch && touch->atoms[0].value.integer==77);}
    log.r.clear();
    // info~: bang -> channels 2 on outlet 8, 10 ms on outlet 6, sr on outlet 0; filename outlets silent.
    assert(rt.send(2,0,Message{}));block(rt);
    {const auto* ch=at(2,8);const auto* total=at(2,6);const auto* sr=at(2,0);
     assert(ch && ch->atoms[0].value.integer==2 && total && std::abs(total->atoms[0].value.floating-10)<1e-9 && sr && sr->atoms[0].value.floating==44100 && !at(2,7) && !at(2,9));}
    // live.adsr~ 0.5 0 1 5.0: gate on, hold 200 ms, gate off; compare to the Live snapshot grid.
    std::array<float,64> l{},r{},ol{},orr{};std::vector<double> y;
    auto render=[&](int blocks){for(int i=0;i<blocks;++i){rendering=true;rt.render(l.data(),r.data(),ol.data(),orr.data(),64);rendering=false;for(float v:ol)y.push_back(v);}};
    assert(rt.send(3,0,Message::integer(1)));render(138);                // ~200.3 ms
    assert(rt.send(3,0,Message::integer(0)));render(400);
    auto ms=[&](double t){return y[size_t(t*44.1)];};
    assert(std::abs(ms(5)-1)<1e-9 && std::abs(ms(100)-1)<1e-9 && std::abs(ms(195)-1)<1e-9);
    assert(std::abs(ms(220))<1e-9 && std::abs(ms(400))<1e-9);
    // The release takes 5 ms after gate-off (~200.3 ms here), so 205 ms sits inside it (Live read 1.0 at its own 205 ms grid; unmeasured phase).
    assert(ms(203)>0 && ms(206)<0.2);
    assert(!rt.faulted());
    return 0;
}
static const int mpe_info_adsr_ran=mpe_info_adsr_tests();
