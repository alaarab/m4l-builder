// ITU-R BS.1770-4 / EBU R128 loudness measurement for loudness~: K-weighted
// mean square per channel, momentary (400 ms) and short-term (3 s) windows,
// gated integrated loudness (-70 LUFS absolute, -10 LU relative), loudness
// range per EBU Tech 3342 (-20 LU relative gate, 10th..95th percentile of
// short-term values) and 4x-oversampled true peak. The K-filter prototypes
// (BS.1770 high shelf f0 1681.974 Hz, +3.99984 dB, Q 0.7071752 and high-pass
// f0 38.13547 Hz, Q 0.5003270) reproduce the standard's 48 kHz coefficients
// exactly; the standard's own 997 Hz / -20 dBFS check reads -23.0 LUFS.
// Which outlet Max's loudness~ assigns to each quantity is the runtime's
// stated model; the page has not been read yet.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <vector>
namespace m4l::maxcompat {
class LoudnessMeter {
    struct Biquad { double b0=1,b1=0,b2=0,a1=0,a2=0,x1=0,x2=0,y1=0,y2=0;
        double process(double x) noexcept {const double y=b0*x+b1*x1+b2*x2-a1*y1-a2*y2;x2=x1;x1=x;y2=y1;y1=y;return y;}
        void clear() noexcept {x1=x2=y1=y2=0;} };
    struct Channel { Biquad shelf,highpass; std::array<double,4> oversample{}; double peak=0,samplePeak=0; };
    int channels_;
    std::vector<Channel> channel_;
    size_t blockSamples_=0,hop_=0,fill_=0;          // 100 ms blocks; momentary = 4 blocks, short-term = 30
    std::vector<double> blockSum_;                   // running sum of K-weighted squares over the current 100 ms block (all channels)
    std::vector<double> blocks_;                     // history of 100 ms block mean squares (ring of 30)
    size_t blockWrite_=0,blockCount_=0;
    std::vector<double> momentaryHistory_,shortTermHistory_;   // gated candidates for integrated / LRA (bounded)
    double truePeak_=0,samplePeak_=0;
    // BS.1770-4 K-weighting from the analog prototypes (the form libebur128
    // uses); at 48 kHz these reproduce the standard's published coefficients
    // to 1e-14. Stage 2 keeps the standard's unnormalised b = {1, -2, 1}.
    static void design(Biquad& q,double rate,double f0,double gainDb,double Q,bool shelf) noexcept {
        const double K=std::tan(M_PI*f0/rate),a0=1+K/Q+K*K;
        if(shelf) {
            const double Vh=std::pow(10.,gainDb/20.),Vb=std::pow(Vh,0.4996667741545416);
            q.b0=(Vh+Vb*K/Q+K*K)/a0;q.b1=2*(K*K-Vh)/a0;q.b2=(Vh-Vb*K/Q+K*K)/a0;
        } else {q.b0=1;q.b1=-2;q.b2=1;}
        q.a1=2*(K*K-1)/a0;q.a2=(1-K/Q+K*K)/a0;
    }
public:
    LoudnessMeter(double rate,int channels):channels_(channels) {
        channel_.resize(size_t(channels));
        for(auto& ch:channel_) {design(ch.shelf,rate,1681.974450955533,3.999843853973347,0.7071752369554196,true);design(ch.highpass,rate,38.13547087602444,0,0.5003270373238773,false);}
        blockSamples_=size_t(std::llround(rate*0.1));hop_=blockSamples_;
        blocks_.assign(30,0.);momentaryHistory_.reserve(1<<16);shortTermHistory_.reserve(1<<16);
    }
    // Max's reset clears the integrated loudness and peak calculations only
    // (refpage); momentary and short-term keep running.
    void reset() noexcept {
        for(auto& ch:channel_) {ch.peak=0;ch.samplePeak=0;}
        momentaryHistory_.clear();shortTermHistory_.clear();truePeak_=0;samplePeak_=0;
        if(blockSum_.empty())blockSum_.assign(1,0.);
    }
    // One sample per channel. Returns true when a 100 ms block completed
    // (measurements refresh at that point).
    bool process(const double* samples) noexcept {
        if(blockSum_.empty())blockSum_.assign(1,0.);
        double sum=0;
        for(int c=0;c<channels_;++c) {
            auto& ch=channel_[size_t(c)];
            const double x=samples[c];
            ch.samplePeak=std::max(ch.samplePeak,std::abs(x));
            // True peak: 4x oversampling by a short windowed-sinc-like 4-phase interpolation of the last four samples.
            ch.oversample={ch.oversample[1],ch.oversample[2],ch.oversample[3],x};
            const double* o=ch.oversample.data();
            for(int p=0;p<4;++p) {
                const double t=p/4.;
                // Catmull-Rom between o[1] and o[2] (bounded, allocation-free stand-in for the standard's FIR).
                const double v=0.5*((2*o[1])+(-o[0]+o[2])*t+(2*o[0]-5*o[1]+4*o[2]-o[3])*t*t+(-o[0]+3*o[1]-3*o[2]+o[3])*t*t*t);
                ch.peak=std::max(ch.peak,std::abs(v));
            }
            const double k=ch.highpass.process(ch.shelf.process(x));
            sum+=k*k;
        }
        blockSum_[0]+=sum;
        if(++fill_>=blockSamples_) {
            fill_=0;
            const double mean=blockSum_[0]/double(blockSamples_);blockSum_[0]=0;
            blocks_[blockWrite_]=mean;blockWrite_=(blockWrite_+1)%blocks_.size();if(blockCount_<blocks_.size())++blockCount_;
            // Momentary (last 4 blocks) enters the integrated gate; short-term (30) the LRA gate.
            if(blockCount_>=4 && momentaryHistory_.size()<momentaryHistory_.capacity())momentaryHistory_.push_back(window(4));
            if(blockCount_>=30 && shortTermHistory_.size()<shortTermHistory_.capacity())shortTermHistory_.push_back(window(30));
            truePeak_=0;samplePeak_=0;for(const auto& ch:channel_) {truePeak_=std::max(truePeak_,ch.peak);samplePeak_=std::max(samplePeak_,ch.samplePeak);}
            return true;
        }
        return false;
    }
    static double lufs(double meanSquare) noexcept {return meanSquare>0?-0.691+10*std::log10(meanSquare):-HUGE_VAL;}
    double window(size_t blocks) const noexcept {
        if(blockCount_<blocks)return 0;double s=0;
        for(size_t i=0;i<blocks;++i)s+=blocks_[(blockWrite_+blocks_.size()-1-i)%blocks_.size()];
        return s/double(blocks);
    }
    double momentary() const noexcept {return lufs(window(std::min<size_t>(4,std::max<size_t>(1,blockCount_))));}
    double shortTerm() const noexcept {return lufs(window(std::min<size_t>(30,std::max<size_t>(1,blockCount_))));}
    double integrated() const noexcept {
        double sum=0;size_t count=0;
        for(double m:momentaryHistory_)if(lufs(m)>-70) {sum+=m;++count;}
        if(!count)return -HUGE_VAL;
        const double relative=lufs(sum/double(count))-10;sum=0;count=0;
        for(double m:momentaryHistory_)if(lufs(m)>-70 && lufs(m)>relative) {sum+=m;++count;}
        return count?lufs(sum/double(count)):-HUGE_VAL;
    }
    double range() const noexcept {
        std::array<double,4096> values{};size_t n=0;double sum=0;size_t count=0;
        for(double m:shortTermHistory_)if(lufs(m)>-70) {sum+=m;++count;}
        if(!count)return 0;
        const double relative=lufs(sum/double(count))-20;
        for(size_t i=shortTermHistory_.size();i-->0 && n<values.size();) {const double l=lufs(shortTermHistory_[i]);if(l>-70 && l>relative)values[n++]=l;}
        if(n<2)return 0;
        std::sort(values.begin(),values.begin()+long(n));
        const double lo=values[size_t(std::floor(0.10*double(n-1)))],hi=values[size_t(std::floor(0.95*double(n-1)))];
        return hi-lo;
    }
    double truePeakDb() const noexcept {return truePeak_>0?20*std::log10(truePeak_):-HUGE_VAL;}
    double samplePeakDb() const noexcept {return samplePeak_>0?20*std::log10(samplePeak_):-HUGE_VAL;}
};
}
