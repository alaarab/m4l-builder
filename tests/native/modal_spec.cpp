#include "modal_core.hpp"
#include "modal_analysis.hpp"
#include <cassert>
#include <iostream>
#include <chrono>
#include <fstream>
#include <cstdlib>
#include <new>
using namespace m4l::modal;
static bool inAudio=false;
void *operator new(std::size_t n) {if(inAudio) std::abort();if(void *p=std::malloc(n))return p;throw std::bad_alloc();}
void operator delete(void *p) noexcept {std::free(p);}
Model glass() {
    Model m;m.count=6;m.anchor=261.625565;
    const double ratios[]{1,2.32,4.25,6.63,9.48,12.82};
    for(int i=0;i<m.count;++i) m.mode[i]={ratios[i],1./(i+2),4./(1+i*.3),(i%2?.3:-.3),0};
    return m;
}
double render(Engine &e,int samples) {
    double energy=0,l=0,r=0;
    inAudio=true;
    for(int i=0;i<samples;++i) {e.process(0,0,l,r);assert(std::isfinite(l)&&std::isfinite(r));
        assert(std::abs(l)<=.966&&std::abs(r)<=.966);energy+=l*l+r*r;}
    inAudio=false;
    return energy;
}
int main() {
    // Fractional events retain identity without changing legacy MIDI behavior.
    {
        Engine e;e.prepare(48000);e.setModel(0,glass());e.setModel(1,glass());
        const auto first=e.noteEvent(60,100.25),second=e.noteEvent(60,100.75);
        assert(first && second && first!=second);
        assert(e.voice[0].velocity==100.25/127 && e.voice[1].velocity==100.75/127);
        e.releaseEvent(second);assert(e.voice[0].held && !e.voice[1].held);
        e.cc(1,64,127);e.releaseEvent(first);assert(!e.voice[0].held && e.voice[0].pedal);
        e.cc(1,64,0);assert(!e.voice[0].pedal);
        e.clear();const auto stolen=e.noteEvent(60,90);
        for(int i=0;i<voices;++i)e.noteEvent(61+i,90);
        e.releaseEvent(stolen);for(const auto& v:e.voice)assert(v.held);
        assert(e.noteEvent(60,NAN)==0 && e.noteEvent(128,100)==0);
        Engine legacy,events;legacy.prepare(48000);events.prepare(48000);
        for(auto* engine:{&legacy,&events}){engine->setModel(0,glass());engine->setModel(1,glass());}
        for(int i=0;i<24000;++i){
            if(i%3000==0){legacy.note(60+i/3000,90+i/3000);events.noteEvent(60+i/3000,90+i/3000);}
            if(i%3000==2000){legacy.note(60+i/3000,0);events.noteEvent(60+i/3000,0);}
            double al,ar,bl,br;legacy.process(0,0,al,ar);events.process(0,0,bl,br);
            assert(al==bl && ar==br);
        }
    }
    double worst=0;
    for(int i=0;i<10000;++i) {
        double ar=std::sin(i*.34),ai=std::cos(i*.82),br=std::cos(i*.32),bi=std::sin(i*.67);
        const double before=ar*ar+ai*ai+br*br+bi*bi;
        couple(ar,ai,br,bi,std::cos(i*.007),std::sin(i*.007));
        worst=std::max(worst,std::abs(ar*ar+ai*ai+br*br+bi*bi-before));
    }
    assert(worst<3e-15);
    // Resonance estimation is checked against independent damped sinusoids.
    double freqError=0,decayError=0;
    for(double sr:{44100.,48000.,96000.}) {
        const double frequencies[]{233.7,543.1,1001.9};
        const double t60[]{2.4,1.5,.85};
        std::vector<float> audio(size_t(sr*3)*2);
        for(size_t i=0;i<audio.size()/2;++i) {
            const double t=double(i)/sr;
            for(int k=0;k<3;++k) {
                const double v=.35/(k+1)*std::sin(2*pi*frequencies[k]*t)*std::exp(-6.90775527898*t/t60[k]);
                audio[2*i]+=float(v);audio[2*i+1]+=float(v*(k==1?.6:1));
            }
        }
        const auto a=analyze(audio,2,sr);
        assert(a.ok && a.model.count==3);
        for(int i=0;i<3;++i) {
            const double f=a.model.mode[i].ratio*a.model.anchor;
            freqError=std::max(freqError,std::abs(1200*std::log2(f/frequencies[i])));
            decayError=std::max(decayError,std::abs(a.model.mode[i].t60/t60[i]-1));
        }
        Engine e;e.prepare(sr);e.setModel(0,glass());e.setModel(1,glass());
        e.note(60,100);assert(render(e,int(sr*.5))>.001);
        assert(e.energyB>1e-8); // Body B is never directly struck.
        e.note(60,0);render(e,int(sr*8));assert(e.active==0);
        e.clear();e.cc(1,64,127);e.note(60,100);e.note(60,0);render(e,256);
        bool pedal=false;for(auto &v:e.voice) pedal|=v.pedal;assert(pedal);
        e.cc(1,64,0);for(auto &v:e.voice) assert(!v.pedal);
        e.clear();e.midi(0x92);e.midi(60);e.midi(100);e.midi(64);e.midi(90);
        render(e,256);assert(e.active==2);
        // Running status, realtime interleaving and independent pressure.
        e.midi(0xD2);e.midi(248);e.midi(99);assert(e.channel[2].pressure>0.7);
        assert(e.channel[1].pressure==0);
        e.midi(0xE2);e.midi(127);e.midi(127);assert(e.channel[2].bend>.99);
        e.clear();e.set(Coupling,0);e.param[Coupling]=0;e.note(60,127);
        render(e,int(sr*.1));assert(e.energyB==0);
        // A burst before the next audio vector retains the eight newest notes.
        e.clear();for(int i=0;i<12;++i)e.note(48+i,100);
        for(const auto &v:e.voice)assert(v.note>=52 && v.note<=59);
        e.clear();e.note(60,100);e.note(60,100);e.note(60,0);
        int held=0;for(const auto &v:e.voice)held+=v.held;assert(held==1);
        e.note(60,0);for(const auto &v:e.voice)assert(!v.held);
        // MPE master and member pedals combine, rather than cancelling each other.
        e.clear();e.mpe=true;e.cc(1,64,127);e.cc(3,64,127);e.note(60,100,3);e.note(60,0,3);
        e.cc(1,64,0);bool memberHeld=false;for(const auto &v:e.voice)memberHeld|=v.pedal;assert(memberHeld);
        e.cc(3,64,0);for(const auto &v:e.voice)assert(!v.pedal);
        // Member bend changes only its voice, while master bend affects both.
        e.clear();e.note(60,100,2);e.note(60,100,3);render(e,64);
        const double untouched=e.voice[0].body[0][0].c;
        e.expression(3,0,.25);render(e,64);
        assert(e.voice[0].body[0][0].c==untouched);
        assert(e.voice[1].body[0][0].c!=untouched);
        e.clear();e.note(60,100,1);e.expression(1,0,.5);render(e,64);
        const double masterFrequency=std::acos(e.voice[0].body[0][0].c)*sr/(2*pi);
        assert(std::abs(masterFrequency-440*std::pow(2.,(61-69)/12.))<1e-6);
        // Frequency edits approach their destination while stored energy rings.
        Model edited=glass();edited.mode[0].ratio=2;
        e.setModel(0,edited);render(e,32);
        assert(e.model[0].mode[0].ratio>1 && e.model[0].mode[0].ratio<1.1);
        render(e,int(sr*.4));assert(e.model[0].mode[0].ratio>1.999);
        e.setModel(0,glass());render(e,int(sr*.4));
        // Every control and note range at extremes while eight voices steal.
        for(int round=0;round<80;++round) {
            for(int p=0;p<Count;++p)e.set(p,round%2?maxima[p]:minima[p]);
            for(int note=0;note<12;++note)e.note((round*7+note*9)%128,127,1+note%15);
            render(e,512);assert(e.active<=voices);
        }
        Model invalid=glass();invalid.mode[0].ratio=std::nan("");assert(!e.setModel(0,invalid));
        // Captured rises caused by beating must not cancel keyboard strikes.
        for(int pitch:{48,60,72}) {
            Engine soft;soft.prepare(sr);Model slow=glass();slow.attack=.08;
            soft.setModel(0,slow);soft.setModel(1,slow);soft.note(pitch,100);
            assert(render(soft,int(sr*.3))>1);
        }
        std::vector<float> silence(48000);assert(!analyze(silence,1,sr).ok);
        audio[12]=std::nanf("");assert(!analyze(audio,2,sr).ok);
    }
    assert(freqError<3);assert(decayError<.08);
    // A shorter body used to lose its fourth, fast-decaying mode in analysis.
    {
        const double f[]{181.3,499.7,980.4,1618.2},d[]{.72,.52,.31,.21};
        std::vector<float> wood(48000*2);
        for(size_t i=0;i<wood.size();++i)for(int k=0;k<4;++k)
            wood[i]+=float(.4/(k+1)*std::sin(2*pi*f[k]*i/48000)*std::exp(-6.90775527898*i/(48000*d[k])));
        auto a=analyze(wood,1,48000);assert(a.ok && a.model.count==4);
        for(int k=0;k<4;++k)assert(std::abs(a.model.mode[k].t60/d[k]-1)<.05);
        const double ratio=a.model.mode[0].gain/a.model.mode[3].gain;
        assert(std::abs(ratio-4)<.1); // decay compensation also restores relative level
    }
    Engine bench;bench.prepare(48000);bench.setModel(0,glass());bench.setModel(1,glass());
    for(int i=0;i<voices;++i)bench.note(48+i*3,100);
    const auto start=std::chrono::steady_clock::now();render(bench,48000*3);
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::cout<<"{\"coupling_energy_error\":"<<worst<<",\"frequency_error_cents\":"<<freqError
        <<",\"decay_relative_error\":"<<decayError<<",\"render_3s_seconds\":"<<seconds<<"}\n";
}
