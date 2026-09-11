// Copyright (c) 2026 m4l-builder contributors. MIT license.
#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"
#include "ext_buffer.h"
#include "modal_analysis.hpp"
#include <atomic>
#include <mutex>
#include <thread>
#include <memory>
#ifndef M4L_EXTERNAL_NAME
#define M4L_EXTERNAL_NAME "m4l.modal~"
#endif
using namespace m4l::modal;
struct Event { int type=0,a=0,b=0,c=0; double value=0; Model model; };
// Multiple message threads serialize producers only. The audio thread consumes
// without acquiring a mutex, allocating, logging or calling the Max object API.
struct Queue {
    std::array<Event,256> items{};
    std::atomic<unsigned> read{0},write{0};
    std::mutex producers;
    bool push(const Event &e) {
        std::lock_guard<std::mutex> lock(producers);
        const unsigned w=write.load(std::memory_order_relaxed),next=(w+1)&255;
        if(next==read.load(std::memory_order_acquire)) return false;
        items[w]=e;write.store(next,std::memory_order_release);return true;
    }
    bool pop(Event &e) {
        const unsigned r=read.load(std::memory_order_relaxed);
        if(r==write.load(std::memory_order_acquire)) return false;
        e=items[r];read.store((r+1)&255,std::memory_order_release);return true;
    }
};
struct Impl {
    Engine engine;
    Queue queue;
    std::atomic<bool> panic{false},busy{false},ready{false},captureCancelled{false};
    std::atomic<int> capturing{0},captureSlot{0},voiceCount{0};
    std::atomic<long> captured{0};
    std::atomic<double> peak{0},inPeak{0},ea{0},eb{0},rate{48000};
    std::vector<float> capture=std::vector<float>(192000*8*2);
    std::thread worker;
    Analysis result;
    int resultSlot=0;
};
struct Object { t_pxobject ob; Impl *impl; void *messages; void *clock; };
static t_class *klass=nullptr;
static void sendStatus(Object *x,int slot,const char *message) {
    t_atom a[2];atom_setlong(a,slot);atom_setsym(a+1,gensym(message));
    outlet_anything(x->messages,gensym("status"),2,a);
}
static void enqueue(Object *x,const Event &e) {
    if(!x->impl->queue.push(e)) x->impl->panic.store(true);
}
static void emitModel(Object *x,int slot,const Model &m) {
    t_atom a[7+modes*5];
    atom_setlong(a,slot);atom_setfloat(a+1,m.anchor);atom_setfloat(a+2,m.attack);
    atom_setfloat(a+3,m.noise);atom_setfloat(a+4,m.confidence);atom_setlong(a+5,m.count);
    for(int i=0;i<modes;++i) {
        const auto &v=m.mode[i];const double vals[]{v.ratio,v.gain,v.t60,v.pan,v.phase};
        for(int j=0;j<5;++j) atom_setfloat(a+6+i*5+j,vals[j]);
    }
    outlet_anything(x->messages,gensym("model"),6+modes*5,a);
}
static void startAnalysis(Object *x,std::vector<float> audio,int channels,double rate,int slot) {
    auto *p=x->impl;
    if(p->worker.joinable()) p->worker.join();
    p->busy=true;p->resultSlot=slot;
    sendStatus(x,slot,"Analyzing resonances…");
    p->worker=std::thread([p,audio=std::move(audio),channels,rate]() {
        try {p->result=analyze(audio,channels,rate);}
        catch(...) {p->result=Analysis{};p->result.message="Analysis failed; previous body retained";}
        p->ready.store(true,std::memory_order_release);
    });
}
static void poll(Object *x) {
    auto *p=x->impl;
    if(p->captureCancelled.exchange(false))
        sendStatus(x,p->captureSlot.load(),"Audio engine changed; capture cancelled, previous body retained");
    if(p->capturing.load(std::memory_order_acquire)==2 && !p->busy.load()) {
        const long n=p->captured.load();
        std::vector<float> audio(p->capture.begin(),p->capture.begin()+n*2);
        p->busy=true;p->capturing.store(0);
        startAnalysis(x,std::move(audio),2,p->rate.load(),p->captureSlot.load());
    }
    if(p->ready.load(std::memory_order_acquire)) {
        if(p->worker.joinable()) p->worker.join();
        if(p->result.ok) {
            Event e;e.type=2;e.a=p->resultSlot;e.model=p->result.model;enqueue(x,e);
            emitModel(x,p->resultSlot,p->result.model);
        }
        sendStatus(x,p->resultSlot,p->result.message.c_str());
        p->ready=false;p->busy=false;
    }
    t_atom a[6];const double v[]{p->peak.exchange(0),double(p->voiceCount.load()),
        p->ea.load(),p->eb.load(),p->inPeak.exchange(0),p->captured.load()/p->rate.load()};
    for(int i=0;i<6;++i) atom_setfloat(a+i,v[i]);
    outlet_anything(x->messages,gensym("meter"),6,a);
    clock_fdelay(x->clock,50);
}
static void perform(Object *x,t_object *,double **ins,long,double **outs,long,long n,long,void *) {
    auto *p=x->impl; Event e;
    const bool panic=p->panic.exchange(false);
    // Bound message work per vector even if a producer keeps feeding the queue.
    for(size_t consumed=0;consumed<p->queue.items.size() && p->queue.pop(e);++consumed) {
        if(e.type==1) p->engine.set(e.a,e.value);
        if(e.type==2) p->engine.setModel(e.a,e.model);
        if(e.type==3) p->engine.note(e.a,e.b,e.c);
        if(e.type==4) p->engine.midi(e.a);
        if(e.type==5) p->engine.mpe=e.a!=0;
        if(e.type==6) {
            if(e.b) {p->captured=0;p->captureSlot=e.a;p->capturing=1;}
            else if(p->capturing==1) p->capturing.store(2,std::memory_order_release);
        }
    }
    // Clear after draining: a full queue may have dropped a note-off while
    // retaining its note-on. Clearing first would allow that voice to hang.
    if(panic) p->engine.clear();
    double peak=p->peak.load(),inPeak=p->inPeak.load();
    long captured=p->captured.load();
    const long cap=std::min<long>(long(p->engine.sr*8),long(p->capture.size()/2));
    for(long i=0;i<n;++i) {
        if(p->capturing.load(std::memory_order_relaxed)==1 && captured<cap) {
            p->capture[captured*2]=float(ins[0][i]);p->capture[captured*2+1]=float(ins[1][i]);
            if(++captured==cap) {p->captured=captured;p->capturing.store(2,std::memory_order_release);}
        }
        inPeak=std::max({inPeak,std::abs(ins[0][i]),std::abs(ins[1][i])});
        p->engine.process(ins[0][i],ins[1][i],outs[0][i],outs[1][i]);
        peak=std::max(peak,p->engine.peak);
    }
    p->captured=captured;p->peak=peak;p->inPeak=inPeak;
    p->voiceCount=p->engine.active;p->ea=p->engine.energyA;p->eb=p->engine.energyB;
}
static void dsp(Object *x,t_object *dsp64,short *,double rate,long,long) {
    if(x->impl->capturing.exchange(0)) x->impl->captureCancelled=true;
    x->impl->engine.prepare(rate);x->impl->rate=rate;
    object_method(dsp64,gensym("dsp_add64"),x,perform,0,nullptr);
}
static void integer(Object *x,long value) {Event e;e.type=4;e.a=int(value);enqueue(x,e);}
static void message(Object *x,t_symbol *s,long argc,t_atom *argv) {
    const auto number=[&](int i){return i<argc?atom_getfloat(argv+i):0.;};
    Event e;
    if(s==gensym("param") && argc==2) {e.type=1;e.a=int(number(0));e.value=number(1);enqueue(x,e);}
    else if(s==gensym("model") && argc==6+modes*5) {
        e.type=2;e.a=int(number(0));e.model.anchor=number(1);e.model.attack=number(2);
        e.model.noise=number(3);e.model.confidence=number(4);e.model.count=int(number(5));
        for(int i=0;i<modes;++i) e.model.mode[i]={number(6+i*5),number(7+i*5),
            number(8+i*5),number(9+i*5),number(10+i*5)};
        if(e.a>=0 && e.a<2 && e.model.valid()) enqueue(x,e);
        else sendStatus(x,e.a,"Invalid model; previous body retained");
    } else if(s==gensym("note") && argc>=2) {
        e.type=3;e.a=int(number(0));e.b=int(number(1));e.c=argc>2?int(number(2)):1;enqueue(x,e);
    } else if(s==gensym("mpe") && argc==1) {e.type=5;e.a=int(number(0));enqueue(x,e);}
    else if(s==gensym("panic")) x->impl->panic=true;
    else if(s==gensym("capture") && argc==2) {
        if(x->impl->busy || (number(1) && x->impl->capturing)) {
            sendStatus(x,int(number(0)),"Finish the current capture first");return;
        }
        e.type=6;e.a=int(clamp(number(0),0,1));e.b=number(1)!=0;enqueue(x,e);
        sendStatus(x,e.a,e.b?"Recording input — stop or wait 8 seconds":"Finishing capture…");
    }
}
static void analyzeBuffer(Object *x,t_symbol *,long argc,t_atom *argv) {
    if(argc!=2 || atom_gettype(argv)!=A_SYM) return;
    const int slot=int(clamp(atom_getlong(argv+1),0,1));
    if(x->impl->busy || x->impl->capturing) {sendStatus(x,slot,"Finish the current capture first");return;}
    t_buffer_ref *ref=buffer_ref_new((t_object*)x,atom_getsym(argv));
    t_buffer_obj *buffer=buffer_ref_getobject(ref);
    if(!buffer) {object_free(ref);sendStatus(x,slot,"Audio buffer is unavailable");return;}
    const long channels=buffer_getchannelcount(buffer),frames=buffer_getframecount(buffer);
    const double rate=buffer_getsamplerate(buffer);
    if(channels<1 || channels>2 || rate<22050 || rate>192000 || frames<1) {
        object_free(ref);sendStatus(x,slot,"Load a mono or stereo audio file");return;
    }
    const long count=std::min<long>(frames,long(rate*8));
    std::vector<float> audio(count*channels);
    float *samples=buffer_locksamples(buffer);
    if(!samples) {object_free(ref);sendStatus(x,slot,"Audio is still loading");return;}
    std::copy(samples,samples+count*channels,audio.begin());
    buffer_unlocksamples(buffer);object_free(ref);
    startAnalysis(x,std::move(audio),int(channels),rate,slot);
}
static void analyzeDeferred(Object *x,t_symbol *s,long argc,t_atom *argv) {
    defer_low(x,(method)analyzeBuffer,s,argc,argv);
}
static void destroy(Object *x) {
    dsp_free((t_pxobject*)x);clock_unset(x->clock);object_free(x->clock);
    if(x->impl->worker.joinable()) x->impl->worker.join();
    delete x->impl;
}
static void *create(t_symbol *,long,t_atom *) {
    auto *x=(Object*)object_alloc(klass);if(!x) return nullptr;
    x->impl=new Impl;
    dsp_setup((t_pxobject*)x,2);
    x->ob.z_misc |= Z_NO_INPLACE;
    x->messages=outlet_new(x,nullptr);outlet_new(x,"signal");outlet_new(x,"signal");
    x->clock=clock_new(x,(method)poll);clock_fdelay(x->clock,100);
    return x;
}
extern "C" void C74_EXPORT ext_main(void *) {
    t_class *c=class_new(M4L_EXTERNAL_NAME,(method)create,(method)destroy,sizeof(Object),nullptr,A_GIMME,0);
    class_addmethod(c,(method)dsp,"dsp64",A_CANT,0);
    class_addmethod(c,(method)integer,"int",A_LONG,0);
    for(const char *name:{"param","model","note","mpe","panic","capture"})
        class_addmethod(c,(method)message,name,A_GIMME,0);
    class_addmethod(c,(method)analyzeDeferred,"analyze",A_GIMME,0);
    class_dspinit(c);class_register(CLASS_BOX,c);klass=c;
}
