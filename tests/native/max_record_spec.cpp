#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
static bool callback=false;static size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
int main(int argc,char** argv) {
    assert(argc==2);std::ifstream reference(argv[1]);assert(reference);
    int frames,cases;reference>>frames>>cases;
    for(int c=0;c<cases;++c) {
        int length,channels,loop;reference>>length>>channels>>loop;
        std::vector<float> expected(frames);for(auto& x:expected)reference>>x;
        std::vector<std::vector<float>> pcm(channels,std::vector<float>(length));
        for(auto& channel:pcm)for(auto& x:channel)reference>>x;assert(reference);
        m4l::gen::Table buffer(length,channels,true);m4l::maxcompat::SignalRecord record(buffer,channels);
        record.loop(loop);record.record(1);
        std::array<double,64> left{},right{},sync{};std::array<const double*,2> source={left.data(),right.data()};
        for(int base=0;base<frames;base+=64) {
            for(int i=0;i<64;++i){left[i]=base+i+1;right[i]=-(base+i+1)*.5;}
            callback=true;record.process(source.data(),sync.data(),64);callback=false;
            for(int i=0;i<64;++i)if(float(sync[i])!=expected[base+i]) {
                std::cerr<<"Sync case "<<c<<" frame "<<base+i<<" got "<<sync[i]<<" expected "<<expected[base+i]<<"\n";return 1;
            }
        }
        for(int ch=0;ch<channels;++ch)for(int i=0;i<length;++i)if(buffer.peek(i,ch)!=pcm[ch][i]) {
            std::cerr<<"Buffer case "<<c<<" channel "<<ch<<" frame "<<i<<" got "<<buffer.peek(i,ch)<<" expected "<<pcm[ch][i]<<"\n";return 1;
        }
        using namespace m4l::maxcompat;
        for(double rate:{44100.,48000.,96000.})for(int block:{1,31,64,127,256}) {
            Symbols symbols;const auto name=symbols.intern("recording");
            Definition storage;storage.op=Op::buffer;storage.atoms={Atom::named(name)};storage.arguments={double(length),double(channels)};
            Definition sourceNode;sourceNode.op=Op::input;
            Definition recorder;recorder.op=Op::signalRecord;recorder.atoms={Atom::named(name)};recorder.arguments={double(channels),double(loop),0};
            Definition output;output.op=Op::output;
            std::vector<Edge> edges={{1,0,2,0},{2,0,3,0},{2,0,3,1}};if(channels==2)edges.push_back({1,1,2,1});
            Runtime runtime({storage,sourceNode,recorder,output},edges,rate,std::move(symbols));
            assert(runtime.send(2,0,Message::integer(1)));
            std::array<float,256> inL{},inR{},outL{},outR{};
            for(int base=0;base<frames;base+=block) {
                int count=std::min(block,frames-base);
                for(int i=0;i<count;++i){inL[i]=base+i+1;inR[i]=-(base+i+1)*.5;}
                callback=true;runtime.render(inL.data(),inR.data(),outL.data(),outR.data(),count);callback=false;
                assert(!runtime.faulted());
                for(int i=0;i<count;++i)assert(outL[i]==expected[base+i] && outR[i]==outL[i]);
            }
            const auto actual=runtime.externalBuffer("recording");assert(actual);
            for(int ch=0;ch<channels;++ch)for(int i=0;i<length;++i)assert(actual->peek(i,ch)==pcm[ch][i]);
        }
    }
    // A later graph may declare the record buffer. Scalar Gen access to that
    // same table must fail before playback in either member order, and a
    // dynamic rebind must not sneak around the preparation check.
    using namespace m4l::maxcompat;
    for(bool writerFirst:{false,true}) {
        auto domain=std::make_shared<RoutingDomain>();
        auto graph=std::make_shared<m4l::gen::GraphDefinition>();
        m4l::gen::NodeDefinition expr;expr.code="Buffer recorded;out1=peek(recorded,0);";
        m4l::gen::NodeDefinition out;out.kind=m4l::gen::NodeDefinition::Kind::output;
        graph->nodes={expr,out};graph->edges={{0,0,1,0}};
        Definition gen;gen.op=Op::gen;gen.genGraph=graph;
        Symbols symbols;const auto name=symbols.intern("recorded");
        Definition storage;storage.op=Op::buffer;storage.arguments={128,1};storage.atoms={Atom::named(name)};
        Definition recorder;recorder.op=Op::signalRecord;recorder.arguments={1,1,0};recorder.atoms={Atom::named(name)};
        std::unique_ptr<Runtime> reader,writer;
        auto makeReader=[&]{reader=std::make_unique<Runtime>(std::vector<Definition>{gen},std::vector<Edge>{},48000,Symbols{},nullptr,nullptr,std::vector<int>{},domain);};
        auto makeWriter=[&]{writer=std::make_unique<Runtime>(std::vector<Definition>{storage,recorder},std::vector<Edge>{},48000,symbols,nullptr,nullptr,std::vector<int>{},domain);};
        if(writerFirst){makeWriter();makeReader();}else{makeReader();makeWriter();}
        domain->prepare();writer->initialize();
        bool rejected=false;try{reader->initialize();}catch(const std::invalid_argument&){rejected=true;}assert(rejected);
        float invalidLeft=1,invalidRight=1;
        callback=true;reader->render(nullptr,nullptr,&invalidLeft,&invalidRight,1);callback=false;
        assert(reader->faulted() && invalidLeft==0 && invalidRight==0);
        m4l::gen::Expression other("Buffer bus;out1=peek(bus,0);",48000);
        assert(!other.bindBuffer("bus",domain->buffers().at("recorded")));
    }
    {
        // MEASURED (September 11): two devices recording into one global
        // buffer~ (two Heats) both land in it; each writes its vector in the
        // session's render order, so the later writer's samples win where the
        // heads overlap. Device A records +1 then device B records -1 over the
        // same region: the buffer holds B's samples.
        using namespace m4l::maxcompat;
        auto domain=std::make_shared<RoutingDomain>();
        auto make=[&](Symbols& sy,bool declare){
            const auto name=sy.intern("scope");
            std::vector<Definition> defs;std::vector<Edge> edges;
            if(declare){Definition storage;storage.op=Op::buffer;storage.atoms={Atom::named(name)};storage.arguments={128,1};defs.push_back(storage);}
            Definition in;in.op=Op::input;Definition rec;rec.op=Op::signalRecord;rec.atoms={Atom::named(name)};rec.arguments={1,1,0};Definition out;out.op=Op::output;
            const int base=int(defs.size());defs.push_back(in);defs.push_back(rec);defs.push_back(out);
            edges={{base,0,base+1,0},{base+1,0,base+2,0},{base+1,0,base+2,1}};
            return std::make_unique<Runtime>(defs,edges,48000,sy,nullptr,nullptr,std::vector<int>{},domain);
        };
        Symbols sa,sb;auto a=make(sa,true);auto b=make(sb,true);
        domain->prepare();a->initialize();b->initialize();
        assert(a->send(2,0,Message::integer(1)) && b->send(2,0,Message::integer(1)));
        std::array<float,64> plus{},minus{},oL{},oR{};plus.fill(1);minus.fill(-1);
        callback=true;a->render(plus.data(),plus.data(),oL.data(),oR.data(),64);b->render(minus.data(),minus.data(),oL.data(),oR.data(),64);callback=false;
        assert(!a->faulted() && !b->faulted());
        const auto table=domain->buffers().at("scope");
        for(int i=0;i<64;++i)assert(table->peek(i,0)==-1);
        for(int i=64;i<128;++i)assert(table->peek(i,0)==0);
        // A third vector from A alone: A's head continues at 64 and B's stays put.
        callback=true;a->render(plus.data(),plus.data(),oL.data(),oR.data(),64);callback=false;
        for(int i=0;i<64;++i)assert(table->peek(i,0)==-1);
        for(int i=64;i<128;++i)assert(table->peek(i,0)==1);
    }
    assert(allocations==0);
    std::cout<<"PASS original Max record~ "<<cases<<" cases: exact graph sync and mono/stereo buffer PCM at 3 rates/5 callback sizes, prepared shared-buffer ownership, two record~ writers on one global buffer in render order, zero callback allocations\n";
}
