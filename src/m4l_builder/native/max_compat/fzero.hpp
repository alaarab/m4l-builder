// fzero~ fundamental estimator, modelled from the arm64 external shipped with
// Max 9.0.10 (read-only inspection of fzero~.mxo, no code copied): every
// analysis period the object takes the last `size` samples, reports silence
// when the peak (|min| or max, an else-if scan, anything above 10000 reads
// as 0) is at or below `threshold`, and otherwise tries two estimators.
//
// 1. YIN on the half-rate data (window 128, lags 1..127, cumulative mean
//    normalised difference, first dip below 0.1 that is a local minimum,
//    parabolic refinement). A result inside [freqmin, freqmax] wins outright.
// 2. Otherwise a four-level peak-spacing search: each level halves the
//    sample rate, scans backwards for maxima above mean + 0.75 (max - mean)
//    and minima below mean + 0.75 (min - mean) with a refractory time of
//    sr / freqmax samples (at that level), a mean-crossing re-arm and at most
//    16 of each; builds the spacings between neighbouring, next-but-one and
//    next-but-two peaks; picks the spacing with the most support (support
//    counts spacings within delta ABOVE the candidate: the external masks the
//    sign bit instead of taking an absolute value), demanding support beyond
//    a quarter of the periods the window could hold, breaking ties towards a
//    doubled spacing or the previous period; averages the supporting spacings
//    (from the second entry on: the external starts its average one element
//    late, and the stale slot it reads past the end is modelled as never
//    matching); and accepts a level whose mode spacing is half the previous
//    level's within delta. Later levels overwrite the pitch, including with 0.
// Outputs (right to left): an onset (bang, or `pitch amplitude` with
// onsetlist) when the amplitude rises by more than onsetamp over the last
// onset or the pitch moves by more than onsetpitch semitones (cents from
// log2f, half-up) after onsetperiod samples; the peak amplitude; the pitch
// when it reaches freqmin (a lower estimate posts to the console instead,
// and 0 emits nothing). Silence emits 0 on both float outlets and forgets
// the last onset amplitude. Max analyses on its scheduler thread; here the
// analysis runs at the vector boundary that completes a period.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>
namespace m4l::maxcompat {
class FZero {
public:
    struct Tick {
        bool silence=false;
        bool onset=false;double onsetPitch=0,onsetAmplitude=0;
        double amplitude=0;
        bool pitchOutput=false;double pitch=0;   // pitchOutput false: nothing on the pitch outlet
    };
    static constexpr int kRing=4096,kMaxSize=4096;
    explicit FZero(double sampleRate,int vectorSize=64) noexcept : sr_(int64_t(sampleRate)),vector_(vectorSize) {
        ring_.assign(kRing,0);
        level_[1].assign(2048,0);level_[2].assign(1024,0);level_[3].assign(512,0);level_[4].assign(256,0);
        distances_.assign(256,0);
    }
    // Attributes (the external's setters): size and period round up to a
    // power of two (size at least the vector size, at most 4096), freqmax is
    // capped at sr / 5 and must exceed freqmin, onsetpitch keeps a cents copy.
    void setSize(int64_t v) noexcept {
        if(v>kMaxSize) {size_=kMaxSize;return;}
        v=std::max<int64_t>(v,vector_);size_=powerOfTwoCeiling(v);
    }
    void setPeriod(int64_t v) noexcept {period_=powerOfTwoCeiling(v);}
    void setFreqMin(int64_t v) noexcept {freqMin_=v;}
    bool setFreqMax(int64_t v) noexcept {
        const int64_t limit=int64_t(double(sr_)*0.2);
        freqMax_=v;
        if(v>limit) {freqMax_=limit;return true;}
        if(v==0 || v<freqMin_) {freqMax_=limit;return false;}   // the external posts an error
        return true;
    }
    void setThreshold(double v) noexcept {threshold_=v;}
    void setOnsetPitch(double v) noexcept {onsetPitch_=v;onsetCents_=int64_t(v*100.);}
    void setOnsetAmp(double v) noexcept {onsetAmp_=v;}
    void setOnsetPeriod(int64_t v) noexcept {onsetPeriod_=powerOfTwoCeiling(v);}
    void setOnsetList(bool v) noexcept {onsetList_=v;}
    void setQuiet(bool v) noexcept {quiet_=v;}
    int64_t size() const noexcept {return size_;}
    int64_t period() const noexcept {return period_;}
    // One sample into the ring; `due` after each full vector tells whether an
    // analysis is scheduled (the external's counter, reset on firing).
    void push(double x) noexcept {ring_[size_t(write_)]=x;write_=(write_+1)&(kRing-1);}
    bool due() noexcept {counter_+=vector_;if(period_>counter_)return false;counter_=0;return true;}
    Tick tick() noexcept {
        Tick out;
        const int prevPeriod=lastPitch_!=0?saturate(double(sr_)/lastPitch_):0;
        pitch_=0;
        onsetCountdown_-=period_;
        const int w=write_;const int size=int(size_);
        double maxValue=-100000.,minValue=100000.,sum=0;
        for(int i=-size;i<0;++i) {
            const double s=ring_[size_t((w+i)&(kRing-1))];
            if(s>maxValue)maxValue=s;else if(s<minValue)minValue=s;
            sum+=s;
        }
        double amplitude=std::fmax(std::fabs(minValue),maxValue);
        if(amplitude>10000.)amplitude=0;
        if(amplitude<=threshold_) {
            lastOnsetAmplitude_=0;
            out.silence=true;out.amplitude=0;out.pitchOutput=true;out.pitch=0;
            lastPitch_=0;return out;
        }
        const int start=(w-size)&(kRing-1);
        const double mean=sum/double(size);
        const double minThreshold=std::fma(minValue-mean,0.75,mean),maxThreshold=std::fma(maxValue-mean,0.75,mean);
        int countMax[5]={},countMin[5]={};
        float modeDistance[5]={};
        bool accepted=false;
        for(int level=1;level<5 && !accepted;++level) {
            const int n=int(size_>>level);
            auto& data=level_[level];
            if(level==1) {
                for(int i=0;i<n;++i)data[size_t(i)]=(ring_[size_t((start+2*i)&(kRing-1))]+ring_[size_t((start+2*i+1)&(kRing-1))])*0.5;
                double yin=0;
                if(yinEstimate(yin)) {
                    if(yin>=double(freqMin_) && yin<=double(freqMax_)) {pitch_=yin;accepted=true;break;}
                }
            } else {
                const auto& previous=level_[level-1];
                for(int i=0;i<n;++i)data[size_t(i)]=(previous[size_t(2*i)]+previous[size_t(2*i+1)])*0.5;
            }
            int delta=freqMax_!=0?int(int32_t(sr_/freqMax_)>>level):1;
            if(delta<1)delta=1;
            countMax[level]=countMin[level]=0;
            if(n-2<0)continue;
            scanPeaks(data.data(),n,level,delta,mean,minThreshold,maxThreshold,countMax[level],countMin[level]);
            if(countMax[level]<2 || countMin[level]<2)continue;
            const int count=buildDistances(level,countMax[level],countMin[level]);
            modeDistance[level]=0;
            float best=0;
            if(count>=1) {
                const int prevPeriodLevel=int(int32_t(prevPeriod)>>level);
                best=selectDistance(count,n,delta,prevPeriodLevel);
                if(best!=0) {
                    float total=0;int supporters=0;
                    for(int j=1;j<count;++j) {
                        const float d=float(distances_[size_t(j)]);
                        if(double(std::fabs(best-d))>double(delta))continue;
                        total+=d;++supporters;
                    }
                    modeDistance[level]=total/float(supporters);
                }
            }
            const float previousMode=modeDistance[level-1];
            if(previousMode==0)continue;
            if(countMax[level-1]<2 || countMin[level-1]<2)continue;
            const float doubled=modeDistance[level]+modeDistance[level];
            if(double(std::fabs(previousMode-doubled))>double(delta)) {pitch_=0;continue;}
            pitch_=double(float(sr_)/previousMode)/std::ldexp(1.,level-1);
        }
        const double pitch=pitch_;
        if(onsetCountdown_<0 && pitch>=double(freqMin_) && pitch<=double(freqMax_)) {
            bool onset=(amplitude-lastOnsetAmplitude_)>onsetAmp_;
            if(!onset) {
                int64_t cents;
                if(lastOnsetPitch_>0) {
                    const float ratio=std::log2(float(pitch/lastOnsetPitch_));
                    cents=int64_t(std::floor(std::fma(double(std::fabs(ratio)),1200.,0.5)));
                } else cents=99999;
                onset=cents>onsetCents_;
            }
            if(onset) {
                out.onset=true;out.onsetPitch=pitch;out.onsetAmplitude=amplitude;
                lastOnsetAmplitude_=amplitude;lastOnsetPitch_=pitch;onsetCountdown_=onsetPeriod_;
            }
        }
        out.amplitude=amplitude;
        if(pitch>=double(freqMin_)) {out.pitchOutput=true;out.pitch=pitch;}
        lastPitch_=pitch;
        return out;
    }
    bool onsetList() const noexcept {return onsetList_;}
private:
    static int64_t powerOfTwoCeiling(int64_t v) noexcept {
        if(v>0 && (v&(v-1))==0)return v;
        int64_t x=v-1;x|=x>>1;x|=x>>2;x|=x>>4;x|=x>>8;x|=x>>16;return x+1;
    }
    static int saturate(double v) noexcept {
        if(!(v==v))return 0;
        if(v>=2147483647.)return 2147483647;if(v<=-2147483648.)return -2147483647-1;
        return int(v);
    }
    // YIN on the half-rate buffer: the difference sums accumulate in four
    // two-lane fused accumulators like the external's vector loop.
    bool yinEstimate(double& pitch) noexcept {
        const auto& d=level_[1];
        double cumulative=0;
        for(int lag=1;lag<128;++lag) {
            double acc[8]={};
            for(int i=0;i<128;i+=8)for(int k=0;k<8;++k) {const double diff=d[size_t(i+k)]-d[size_t(i+k+lag)];acc[k]=std::fma(diff,diff,acc[k]);}
            double lane0=acc[0],lane1=acc[1];
            lane0=acc[2]+lane0;lane1=acc[3]+lane1;
            lane0=acc[4]+lane0;lane1=acc[5]+lane1;
            lane0=acc[6]+lane0;lane1=acc[7]+lane1;
            const double sumDiff=lane0+lane1;
            cumulative=sumDiff+cumulative;
            cmnd_[size_t(lag)]=sumDiff*double(lag)/cumulative;
            if(lag<5)continue;
            const int t=lag-3;
            if(!(cmnd_[size_t(t)]<0.1) || !(cmnd_[size_t(t)]<cmnd_[size_t(t+1)]))continue;
            double estimate=0;
            if(lag<=126) {
                const double a=cmnd_[size_t(t)],b=cmnd_[size_t(t+1)],c=cmnd_[size_t(t-1)];
                const double numerator=(b-c)*0.5,denominator=(a+a)-(b+c);
                const double position=double(t)+numerator/denominator;
                estimate=double(sr_>>1)/position;
            }
            pitch=estimate;return true;
        }
        pitch=0;return false;
    }
    void scanPeaks(const double* data,int n,int level,int delta,double mean,double minThreshold,double maxThreshold,int& countMax,int& countMin) noexcept {
        int* maxs=maxs_[level];int* mins=mins_[level];
        int state=(data[n-1]-data[n-2]<=0)?-1:1;
        bool armed=true;int refractory=0;int i=n-1;
        while(true) {
            const double diff=data[i-1]-data[i],value=data[i];
            bool recorded=false;
            if(state>=0) {
                if(diff<0) {
                    state=-1;
                    if(armed && value>=maxThreshold && refractory==0) {maxs[++countMax]=i;recorded=true;refractory=delta;}
                }
            } else if(diff>0) {
                state=1;
                if(armed && value<=minThreshold && refractory==0) {mins[++countMin]=i;recorded=true;refractory=delta;}
            }
            if(recorded)armed=false;
            if(countMax>15)i=0;else if(countMin>=16)i=0;
            bool rearm=armed;
            if(!armed) {
                if(state>=1)rearm=data[i]>=mean;else rearm=data[i]<=mean;
            }
            if(rearm) {
                armed=true;if(refractory)--refractory;
                if(--i<=0)return;
            } else {
                armed=false;if(refractory)--refractory;
                if(--i<=0)return;
            }
        }
    }
    int buildDistances(int level,int countMax,int countMin) noexcept {
        const int* maxs=maxs_[level];const int* mins=mins_[level];int count=0;
        for(int k=1;k<countMax;++k)distances_[size_t(count++)]=maxs[k]-maxs[k+1];
        for(int k=1;k<countMin;++k)distances_[size_t(count++)]=mins[k]-mins[k+1];
        if(countMax>=3)for(int k=1;k<countMax-1;++k)distances_[size_t(count++)]=maxs[k]-maxs[k+2];
        if(countMin>=3)for(int k=1;k<countMin-1;++k)distances_[size_t(count++)]=mins[k]-mins[k+2];
        if(countMax>=4)for(int k=1;k<countMax-2;++k)distances_[size_t(count++)]=maxs[k]-maxs[k+3];
        if(countMin>=4)for(int k=1;k<countMin-2;++k)distances_[size_t(count++)]=mins[k]-mins[k+3];
        return count;
    }
    float selectDistance(int count,int n,int delta,int prevPeriod) noexcept {
        float best=0;int bestSupport=1;
        for(int c=0;c<count;++c) {
            const int32_t v=distances_[size_t(c)];
            int support=0;
            for(int j=0;j<count;++j) {
                const int32_t masked=int32_t(uint32_t(distances_[size_t(j)]-v)&0x7fffffffu);
                if(masked<=delta)++support;
            }
            if(support>=bestSupport) {
                const int32_t periods=v!=0?int32_t(n/v):0;
                if(double(periods)*0.25>=double(support))continue;   // too little support for the window; nothing else applies
                if(support>bestSupport) {bestSupport=support;best=float(v);continue;}
                if(prevPeriod==0) {
                    const double current=double(best);
                    if(current*1.95<double(v) && current*2.05>double(v))best=float(v);
                } else {
                    const int32_t masked=int32_t(uint32_t(v-prevPeriod)&0x7fffffffu);
                    if(masked<delta)best=float(v);
                }
            } else if(support==bestSupport-1 && prevPeriod!=0) {
                if(v-prevPeriod<delta)best=float(v);
            }
        }
        return best;
    }
    int64_t sr_;int vector_;
    int64_t size_=2048,period_=256,freqMin_=20,freqMax_=2500,onsetCents_=80,onsetPeriod_=1024;
    double threshold_=0.1,onsetPitch_=0.8,onsetAmp_=0.1;
    bool onsetList_=false,quiet_=false;
    std::vector<double> ring_;int write_=0;int64_t counter_=0;
    std::array<std::vector<double>,5> level_;
    double cmnd_[128]={};
    int maxs_[5][17]={},mins_[5][17]={};
    std::vector<int32_t> distances_;
    double pitch_=0,lastPitch_=0,lastOnsetAmplitude_=0,lastOnsetPitch_=0;
    int64_t onsetCountdown_=0;
};
}
