// Copyright (c) 2026 m4l-builder contributors. MIT license.
// Standalone, allocation-free audio engine. No Max dependencies in this file.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace m4l::modal {
constexpr double pi = 3.14159265358979323846;
constexpr int modes = 24;
constexpr int voices = 8;
inline double clamp(double x, double lo, double hi) {
    return std::isfinite(x) ? std::max(lo, std::min(hi, x)) : lo;
}
inline double mix(double a, double b, double x) { return a + (b-a)*x; }
inline double logmix(double a, double b, double x) {
    return std::exp(mix(std::log(std::max(1e-9,a)), std::log(std::max(1e-9,b)), x));
}
struct Mode { double ratio=1, gain=0, t60=1, pan=0, phase=0; };
struct Model {
    std::array<Mode,modes> mode{};
    int count=0;
    double anchor=220, attack=.006, noise=.08, confidence=1;
    bool valid() const {
        if (count<1 || count>modes || !std::isfinite(anchor) || anchor<20 || anchor>20000)
            return false;
        for (int i=0;i<modes;++i) {
            const auto &m=mode[i];
            if (!std::isfinite(m.ratio) || m.ratio<.02 || m.ratio>512 ||
                !std::isfinite(m.gain) || m.gain<0 || m.gain>2 ||
                !std::isfinite(m.t60) || m.t60<.015 || m.t60>60 ||
                !std::isfinite(m.pan) || std::abs(m.pan)>1 ||
                !std::isfinite(m.phase) || std::abs(m.phase)>2*pi) return false;
        }
        return std::isfinite(attack) && attack>=.0002 && attack<=.2 &&
               std::isfinite(noise) && noise>=0 && noise<=1 &&
               std::isfinite(confidence) && confidence>=0 && confidence<=1;
    }
};
// Rotating both quadratures by the same orthogonal matrix exchanges energy.
// ||A'||^2+||B'||^2 == ||A||^2+||B||^2 independently of frequency/damping.
inline void couple(double &ar,double &ai,double &br,double &bi,double c,double s) {
    const double r=ar, i=ai;
    ar=c*r-s*br; ai=c*i-s*bi;
    br=s*r+c*br; bi=s*i+c*bi;
}
struct Resonator {
    double re=0, im=0, c=1, s=0, radius=0, weight=0, left=.7071, right=.7071;
    double phasec=1, phases=0;
    void step(double input) {
        const double r=re;
        re=radius*(c*r-s*im)+input*weight;
        im=radius*(s*r+c*im);
        if (std::abs(re)+std::abs(im)<1e-25) re=im=0;
    }
};
enum Param { Morph, Coupling, Hardness, Position, Decay, Damping, Bow, Breath,
             Texture, Width, Balance, Gain, Tune, Release, Input, Pressure,
             Count };
constexpr std::array<double,Count> defaults{
    0,.18,.45,.29,1,.25,0,0,.08,.75,.42,-12,0,2,0,0};
constexpr std::array<double,Count> minima{
    0,0,0,0,.15,0,0,0,0,0,0,-60,-24,.05,0,0};
constexpr std::array<double,Count> maxima{
    1,1,1,1,8,1,1,1,1,1,1,6,24,12,1,1};
struct Channel { double bend=0, pressure=0, timbre=.5; bool sustain=false; };
struct ExcitationFollower {
    double low=0, fast=0, slow=0;
    double tonal=0, breath=0, transient=0;
    void process(double input,double sr) {
        low+=(1-std::exp(-2*pi*1600/sr))*(input-low);
        const double high=input-low;
        fast+=(1-std::exp(-1/(sr*.002)))*(std::abs(high)-fast);
        slow+=(1-std::exp(-1/(sr*.035)))*(std::abs(high)-slow);
        tonal=low;breath=high;
        transient=std::max(0.,fast-slow*1.5);
    }
};
// First-order antiderivative antialiasing of a bounded, odd bow friction curve.
inline double bowFriction(double current,double previous) {
    if(std::abs(current-previous)<1e-8) {
        const double middle=(current+previous)*.5;
        return middle/(1+150*middle*middle);
    }
    return (std::log1p(150*current*current)-std::log1p(150*previous*previous)) /
           (300*(current-previous));
}
struct Voice {
    std::array<std::array<Resonator,modes>,2> body{};
    int note=-1,channel=1,age=0;
    uint64_t started=0;
    bool held=false,pedal=false;
    double velocity=0, strike=0, attack=.006, pressure=0;
    double env=0, energy=0, lastL=0,lastR=0,stealL=0,stealR=0;
    double noiseLow=0, excitationLow=0, previousVelocity=0;
    uint32_t random=0x1a2b3c4d;
    double noise() { random^=random<<13; random^=random>>17; random^=random<<5;
        return double(random)/2147483648.0-1; }
};
class Engine {
public:
    std::array<Model,2> model{};
    std::array<Model,2> destination{};
    std::array<bool,2> hasModel{false,false};
    std::array<Voice,voices> voice{};
    std::array<Channel,16> channel{};
    std::array<double,Count> target=defaults, param=defaults;
    double sr=48000, bendRange=48, peak=0, energyA=0, energyB=0;
    bool mpe=false;
    ExcitationFollower inputFollower;
    int active=0;
    void prepare(double rate) {
        sr=clamp(rate,22050,192000); clear(); tick=0;
    }
    void clear() {
        for(auto &v:voice) v=Voice{};
        for(auto &c:channel) c=Channel{};
        dcL=dcR=prevL=prevR=0; gainEnvelope=1; active=0;inputFollower=ExcitationFollower{};
    }
    bool setModel(int slot,const Model &m) {
        if (slot<0 || slot>1 || !m.valid()) return false;
        destination[slot]=m;
        if(!hasModel[slot]) {model[slot]=m;hasModel[slot]=true;}
        tick=0; return true;
    }
    void set(int p,double value) {
        if (p>=0 && p<Count && std::isfinite(value)) target[p]=clamp(value,minima[p],maxima[p]);
    }
    void note(int pitch,int velocity,int ch=1) { (void)noteEvent(pitch,velocity,ch); }
    // Event identity permits precise release of overlapping notes. The legacy
    // integer MIDI entry point retains the exact original synthesis path.
    uint64_t noteEvent(int pitch,double velocity,int ch=1) {
        if (pitch<0 || pitch>127 || ch<1 || ch>16 || !std::isfinite(velocity)) return 0;
        if (velocity<=0) {
            Voice *released=nullptr;
            for(auto &v:voice) if(v.note==pitch && v.channel==ch && v.held &&
                (!released || v.started<released->started)) released=&v;
            if(released) {released->held=false;released->pedal=channel[ch-1].sustain || (mpe && channel[0].sustain);}
            return 0;
        }
        Voice *chosen=nullptr;
        for(auto &v:voice) if(v.note<0) {chosen=&v; break;}
        if(!chosen) {
            chosen=&voice[0];
            for(auto &v:voice) if((!v.held && chosen->held) ||
                (v.held==chosen->held && (v.energy<chosen->energy ||
                  (std::abs(v.energy-chosen->energy)<1e-16 && v.started<chosen->started)))) chosen=&v;
        }
        const double oldL=chosen->lastL, oldR=chosen->lastR;
        *chosen=Voice{};
        auto &v=*chosen; v.note=pitch; v.channel=ch; v.held=true;
        v.velocity=clamp(velocity/127.0,0,1); v.stealL=oldL; v.stealR=oldR;
        v.attack=clamp(mix(model[0].attack,.0008,param[Hardness])*
                      mix(1.4,.6,v.velocity),.0005,.15);
        // A measured rise can include beating between partials. Letting that
        // become several periods of a unipolar strike cancels the played note.
        // Scale the longest contact to pitch, retaining a soft, audible attack.
        const double fundamental=440*std::pow(2.,(pitch-69+param[Tune])/12.);
        v.attack=std::max(2/sr,std::min(v.attack,.75/fundamental));
        v.started=++serial;v.random^=uint32_t(serial)*2654435761U;
        update(v); tick=0; return v.started;
    }
    void releaseEvent(uint64_t token) {
        if(!token) return;
        for(auto &v:voice) if(v.started==token && v.held) {
            v.held=false;v.pedal=channel[v.channel-1].sustain || (mpe && channel[0].sustain);
            return;
        }
    }
    void expression(int ch,int kind,double value) {
        if(ch<1 || ch>16) return;
        auto &c=channel[ch-1];
        if(kind==0) c.bend=clamp(value,-1,1);
        if(kind==1) c.pressure=clamp(value,0,1);
        if(kind==2) c.timbre=clamp(value,0,1);
        tick=0;
    }
    void cc(int ch,int number,int value) {
        if(ch<1 || ch>16) return;
        if(number==74) expression(ch,2,value/127.0);
        if(number==1 || number==2) expression(ch,1,value/127.0);
        if(number==64) {
            channel[ch-1].sustain=value>=64;
            if(value<64) for(auto &v:voice) if(v.channel==ch || (mpe && ch==1))
                v.pedal=channel[v.channel-1].sustain || (mpe && channel[0].sustain);
        }
        if(number==120) clear();
        if(number==123) for(auto &v:voice) if(v.channel==ch || (mpe && ch==1)) {
            v.held=false; v.pedal=channel[v.channel-1].sustain || (mpe && channel[0].sustain);
        }
    }
    void polyPressure(int pitch,int ch,double value) {
        for(auto &v:voice) if(v.note==pitch && v.channel==ch) v.pressure=clamp(value,0,1);
    }
    void midi(int byte) {
        if(byte<0 || byte>255 || byte>=248) return;
        if(byte>=128) { status=(byte<240)?byte:0; used=0; return; }
        if(!status) return;
        data[used++]=byte;
        const int kind=status&240, ch=(status&15)+1;
        if(used<((kind==192 || kind==208)?1:2)) return;
        used=0;
        if(kind==144) note(data[0],data[1],ch);
        if(kind==128) note(data[0],0,ch);
        if(kind==160) polyPressure(data[0],ch,data[1]/127.0);
        if(kind==176) cc(ch,data[0],data[1]);
        if(kind==208) expression(ch,1,data[0]/127.0);
        if(kind==224) expression(ch,0,((data[1]*128+data[0])-8192)/8192.0);
    }
    void process(double inputL,double inputR,double &left,double &right) {
        if(tick==0) {
            const double smooth=1-std::exp(-32/(sr*.012));
            for(int p=0;p<Count;++p) param[p]+=smooth*(target[p]-param[p]);
            const double materialSmooth=1-std::exp(-32/(sr*.045));
            for(int body=0;body<2;++body) if(hasModel[body]) {
                auto &current=model[body];const auto &next=destination[body];
                current.count=std::max(current.count,next.count);
                current.attack=mix(current.attack,next.attack,materialSmooth);
                current.noise=mix(current.noise,next.noise,materialSmooth);
                for(int i=0;i<modes;++i) {
                    auto &a=current.mode[i];const auto &b=next.mode[i];
                    a.ratio=logmix(a.ratio,b.ratio,materialSmooth);
                    a.gain=mix(a.gain,b.gain,materialSmooth);
                    a.t60=logmix(a.t60,b.t60,materialSmooth);
                    a.pan=mix(a.pan,b.pan,materialSmooth);
                    // Take the short path across the -pi/pi phase boundary.
                    a.phase+=std::remainder(b.phase-a.phase,2*pi)*materialSmooth;
                }
            }
            for(auto &v:voice) if(v.note>=0) update(v);
            const double theta=param[Coupling]*180/sr;
            couplingC=std::cos(theta); couplingS=std::sin(theta);
            outGain=std::pow(10,param[Gain]/20); dcPole=std::exp(-2*pi*5/sr);
        }
        tick=(tick+1)&31;
        left=right=0; active=0; energyA=energyB=0;
        const double external=clamp((inputL+inputR)*.5,-4,4)*param[Input];
        inputFollower.process(external,sr);
        for(auto &v:voice) {
            if(v.note<0) continue;
            ++active; ++v.age;
            const auto &ch=channel[v.channel-1];
            const double pressure=std::max({ch.pressure,v.pressure,param[Pressure],
                                           mpe?channel[0].pressure:0.});
            const double envTarget=(v.held || v.pedal)?1:0;
            v.env+=(1-std::exp(-1/(sr*.015)))*(envTarget-v.env);
            double hit=0;
            if(v.strike<v.attack) {
                const double x=v.strike/v.attack;
                hit=(1-std::cos(2*pi*x))*.5/(sr*v.attack)*8*v.velocity;
                v.strike+=1/sr;
            }
            double velocity=0;
            for(const auto &r:v.body[0]) velocity+=r.re*r.weight;
            const double noise=v.noise();
            v.noiseLow+=.14*(noise-v.noiseLow);
            // Bounded negative damping supplies energy at the physical port.
            // ADAA reduces aliasing from the nonlinear friction characteristic.
            const double bow=param[Bow]*v.env*(.2+.8*pressure);
            const double friction=bowFriction(velocity,v.previousVelocity)*bow*80/sr;
            v.previousVelocity=velocity;
            const double air=(noise-v.noiseLow)*param[Breath]*v.env*
                             (.25+.75*pressure)*.0025*std::sqrt(48000/sr);
            const double grain=hit*noise*param[Texture]*mix(.2,1,model[0].noise);
            // Sustained lower-band input, high-band air and consonant-like
            // onsets excite separate aspects. This is not phoneme recognition.
            const double audioExcitation=(inputFollower.tonal*.004+
                inputFollower.breath*.002+inputFollower.transient*.018)*v.env;
            const double excitation=hit+friction+air+grain+audioExcitation;
            v.excitationLow+=mix(.06,.95,param[Hardness])*(excitation-v.excitationLow);
            double l=0,r=0,eA=0,eB=0;
            for(int i=0;i<modes;++i) {
                auto &a=v.body[0][i]; auto &b=v.body[1][i];
                a.step(v.excitationLow); b.step(0);
                if(i<model[1].count && (i<model[0].count || param[Morph]>0))
                    couple(a.re,a.im,b.re,b.im,couplingC,couplingS);
                l+=a.re*a.left*(1-param[Balance])+b.re*b.left*param[Balance];
                r+=(a.re*a.phasec-a.im*a.phases)*a.right*(1-param[Balance])+
                   (b.re*b.phasec-b.im*b.phases)*b.right*param[Balance];
                eA+=a.re*a.re+a.im*a.im; eB+=b.re*b.re+b.im*b.im;
            }
            v.energy=eA+eB; energyA+=eA; energyB+=eB;
            l+=v.stealL; r+=v.stealR;
            v.stealL*=.99; v.stealR*=.99; v.lastL=l; v.lastR=r;
            left+=l; right+=r;
            if(v.energy<1e-17 && !v.held && !v.pedal && v.env<1e-5) v.note=-1;
        }
        left*=outGain*3; right*=outGain*3;
        // 5 Hz DC rejection and linked instantaneous protection. No normal-level
        // waveshaping. The protection ceiling is not a true-peak limiter claim.
        const double dl=left-prevL+dcPole*dcL, dr=right-prevR+dcPole*dcR;
        prevL=left; prevR=right; dcL=dl; dcR=dr;
        const double p=std::max(std::abs(dl),std::abs(dr));
        const double desired=p>.965 ? .965/p : 1;
        gainEnvelope=desired<gainEnvelope?desired:gainEnvelope+(1-gainEnvelope)*.0002;
        left=dl*gainEnvelope; right=dr*gainEnvelope;
        if(!std::isfinite(left) || !std::isfinite(right)) { clear(); left=right=0; }
        peak=std::max(std::abs(left),std::abs(right));
    }
private:
    int tick=0,status=0,used=0,data[2]{};
    uint64_t serial=0;
    double couplingC=1,couplingS=0,outGain=.25,dcPole=.9993;
    double dcL=0,dcR=0,prevL=0,prevR=0,gainEnvelope=1;
    void update(Voice &v) {
        const auto &ch=channel[v.channel-1];
        const double bend=ch.bend*(mpe && v.channel!=1?bendRange:2)+
                          (mpe && v.channel!=1?channel[0].bend*2:0);
        const double fundamental=440*std::pow(2,(v.note-69+param[Tune]+bend)/12);
        const double pressure=std::max({ch.pressure,v.pressure,param[Pressure],
                                       mpe?channel[0].pressure:0.});
        for(int body=0;body<2;++body) for(int i=0;i<modes;++i) {
            auto &r=v.body[body][i];
            const auto &a=model[body].mode[i]; const auto &b=model[1].mode[i];
            const double morph=body==0?param[Morph]:0;
            const double ratio=logmix(a.ratio,b.ratio,morph);
            const double frequency=fundamental*ratio;
            const double fade=clamp((.46*sr-frequency)/(.06*sr),0,1);
            const double angle=2*pi*std::min(frequency,.46*sr)/sr;
            r.c=std::cos(angle); r.s=std::sin(angle);
            double decay=logmix(a.t60,b.t60,morph)*param[Decay];
            decay/=1+param[Damping]*(ratio*.5+pressure*8);
            if(!v.held && !v.pedal) decay=std::min(decay,param[Release]);
            r.radius=std::exp(-6.90775527898/(sr*clamp(decay,.015,120)));
            // Smoothly suppress unrepresentable modes, including stored energy.
            if(fade<=0) r.radius=std::min(r.radius,.98);
            const double contact=clamp(param[Position]+(ch.timbre-.5)*.3,0,1);
            const double shape=std::sin(pi*(i+1)*(.04+.92*contact));
            const double participation=std::sqrt(mix(a.gain,b.gain,morph));
            r.weight=participation*shape*fade;
            const double pan=clamp(mix(a.pan,b.pan,morph)*param[Width],-1,1);
            r.left=std::cos((pan+1)*pi/4)*fade*participation;
            r.right=std::sin((pan+1)*pi/4)*fade*participation;
            const double phase=mix(a.phase,b.phase,morph)*param[Width];
            r.phasec=std::cos(phase); r.phases=std::sin(phase);
        }
    }
};
} // namespace m4l::modal
