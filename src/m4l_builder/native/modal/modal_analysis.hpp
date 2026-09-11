// Copyright (c) 2026 m4l-builder contributors. MIT license.
// Offline modal estimation. Never call from an audio callback.
#pragma once
#include "modal_core.hpp"
#include <complex>
#include <string>
#include <vector>
#include <numeric>

namespace m4l::modal {
struct Analysis {
    Model model;
    bool ok=false;
    std::string message;
    double clipped=0, duration=0;
};
inline void fft(std::vector<std::complex<double>> &a) {
    const size_t n=a.size();
    for(size_t i=1,j=0;i<n;++i) {
        size_t bit=n>>1;
        for(;j&bit;bit>>=1) j^=bit;
        j^=bit;
        if(i<j) std::swap(a[i],a[j]);
    }
    for(size_t len=2;len<=n;len<<=1) {
        const std::complex<double> wlen=std::polar(1.0,-2*pi/len);
        for(size_t i=0;i<n;i+=len) {
            std::complex<double> w=1;
            for(size_t j=0;j<len/2;++j) {
                const auto u=a[i+j],v=a[i+j+len/2]*w;
                a[i+j]=u+v; a[i+j+len/2]=u-v; w*=wlen;
            }
        }
    }
}
inline Analysis analyze(const std::vector<float> &interleaved,int channels,double sr) {
    Analysis result;
    if(channels<1 || channels>2 || sr<22050 || sr>192000 || !std::isfinite(sr)) {
        result.message="Use mono or stereo audio at 22.05–192 kHz"; return result;
    }
    const size_t total=interleaved.size()/channels;
    result.duration=double(total)/sr;
    if(total<size_t(sr*.08)) { result.message="Recording too short: use at least 80 ms"; return result; }
    double peak=0; size_t peakAt=0,clipped=0;
    for(size_t i=0;i<total;++i) for(int c=0;c<channels;++c) {
        const double v=std::abs(interleaved[i*channels+c]);
        if(!std::isfinite(v)) {result.message="Recording contains invalid samples"; return result;}
        if(v>peak) {peak=v;peakAt=i;}
        clipped+=v>=.9999;
    }
    result.clipped=double(clipped)/(total*channels);
    if(peak<1e-5) { result.message="No usable audio: keep the previous body"; return result; }
    size_t onset=0;
    while(onset<peakAt && std::max(std::abs(interleaved[onset*channels]),
          std::abs(interleaved[onset*channels+channels-1]))<peak*.03) ++onset;
    // Bounded analysis and a power-of-two window around 0.34 seconds. Short
    // recordings are zero padded, not described as having equivalent resolution.
    size_t n=1;
    while(n<size_t(sr*.34)) n*=2;
    const size_t hop=n/4, end=std::min(total,onset+size_t(sr*8));
    const size_t frames=std::max<size_t>(1,(end-onset>n)?1+(end-onset-n)/hop:1);
    std::vector<std::vector<double>> spectra;
    std::vector<double> average(n/2),window(n);
    for(size_t i=0;i<n;++i) window[i]=.5-.5*std::cos(2*pi*i/(n-1));
    for(size_t f=0;f<frames;++f) {
        std::vector<std::complex<double>> l(n),r(n);
        for(size_t i=0;i<n;++i) {
            const size_t at=onset+f*hop+i;
            if(at<end) { l[i]=interleaved[at*channels]*window[i];
                r[i]=interleaved[at*channels+channels-1]*window[i]; }
        }
        fft(l); fft(r);
        std::vector<double> power(n/2);
        for(size_t i=0;i<n/2;++i) {
            power[i]=std::norm(l[i])+std::norm(r[i]);
            // Early decay spectrum preserves quiet fast-decaying modes; later
            // windows are for independent T60 fitting, not peak selection.
            if(f<3) average[i]+=power[i]/std::min<size_t>(frames,3);
        }
        spectra.push_back(std::move(power));
    }
    // A second, shorter window finds modes which die during the long window's
    // fade-in. Zero padding keeps both spectra on the same frequency grid.
    std::vector<std::complex<double>> attackL(n),attackR(n);
    const size_t shortN=n/4;
    for(size_t i=0;i<shortN && onset+i<end;++i) {
        const double w=.5-.5*std::cos(2*pi*i/(shortN-1));
        attackL[i]=interleaved[(onset+i)*channels]*w;
        attackR[i]=interleaved[(onset+i)*channels+channels-1]*w;
    }
    fft(attackL);fft(attackR);
    const int low=std::max(2,int(35*n/sr)), high=std::min(int(n/2)-2,int(18000*n/sr));
    double top=0,totalPower=0,logSum=0;
    for(int i=low;i<high;++i) {top=std::max(top,average[i]); totalPower+=average[i];
        logSum+=std::log(std::max(average[i],1e-25));}
    const double flatness=std::exp(logSum/(high-low))/std::max(1e-25,totalPower/(high-low));
    std::vector<double> shortPower(n/2),importance(n/2);
    double shortTop=1e-25;
    for(int i=low;i<high;++i) {
        shortPower[i]=std::norm(attackL[i])+std::norm(attackR[i]);
        shortTop=std::max(shortTop,shortPower[i]);
    }
    std::vector<int> peaks;
    for(int resolution=0;resolution<2;++resolution) {
        const auto &spectrum=resolution?shortPower:average;
        const double maximum=resolution?shortTop:top;
        for(int i=low;i<high;++i) if(spectrum[i]>spectrum[i-1] && spectrum[i]>=spectrum[i+1] &&
            spectrum[i]>maximum*.0004) {
            double floor=0;int bins=0;
            for(int j=std::max(low,i-12);j<=std::min(high,i+12);++j)
                if(std::abs(j-i)>(resolution?4:2)) {floor+=spectrum[j];++bins;}
            if(spectrum[i]>5*floor/std::max(1,bins)) {
                // Refine the short-window candidate on the long-window spectrum.
                int k=i;
                if(resolution) for(int j=std::max(low,i-2);j<=std::min(high,i+2);++j)
                    if(average[j]>average[k]) k=j;
                importance[k]=std::max(importance[k],spectrum[i]/maximum);
                peaks.push_back(k);
            }
        }
    }
    std::sort(peaks.begin(),peaks.end(),[&](int a,int b){return importance[a]>importance[b];});
    std::vector<int> chosen;
    for(int p:peaks) {
        bool separated=true;
        for(int q:chosen) if(std::abs(p-q)<3) separated=false;
        if(separated) chosen.push_back(p);
        if(chosen.size()==modes) break;
    }
    std::sort(chosen.begin(),chosen.end());
    if(chosen.empty() || flatness>.4) {
        result.message="No stable resonances found; try an isolated ringing sound"; return result;
    }
    auto &model=result.model;
    model.count=int(chosen.size()); model.attack=clamp(double(peakAt-onset)/sr,.0002,.2);
    double gainSum=0; int fits=0;
    for(size_t m=0;m<chosen.size();++m) {
        const int k=chosen[m]; auto &mode=model.mode[m];
        const double a=std::log(std::max(average[k-1],1e-25)),
                     b=std::log(std::max(average[k],1e-25)),
                     c=std::log(std::max(average[k+1],1e-25));
        const double delta=clamp(.5*(a-c)/(a-2*b+c),-.5,.5);
        const double frequency=(k+delta)*sr/n;
        if(m==0) model.anchor=frequency;
        mode.ratio=frequency/model.anchor;
        double sx=0,sy=0,sxx=0,sxy=0; int count=0;
        const double first=spectra[0][k];
        for(size_t f=0;f<frames;++f) {
            const double p=spectra[f][k];
            if(p<first*1e-5 || p>first*1.6) continue;
            const double x=double(f*hop)/sr,y=.5*std::log(std::max(p,1e-25));
            sx+=x;sy+=y;sxx+=x*x;sxy+=x*y;++count;
        }
        const double den=count*sxx-sx*sx;
        const double slope=den>1e-12?(count*sxy-sx*sy)/den:0;
        if(count>=3 && slope<-.115) {mode.t60=clamp(-6.90775527898/slope,.015,60);++fits;}
        else mode.t60=clamp(result.duration*1.5,.15,6);
        // Correct the window's attenuation of a decaying mode. Otherwise short
        // resonances become much too quiet in the reconstructed instrument.
        std::complex<double> projectionL=0,projectionR=0;
        double normalization=0;
        for(size_t i=0;i<n && onset+i<end;++i) {
            const auto oscillator=std::polar(window[i],-2*pi*frequency*i/sr);
            projectionL+=double(interleaved[(onset+i)*channels])*oscillator;
            projectionR+=double(interleaved[(onset+i)*channels+channels-1])*oscillator;
            normalization+=window[i]*std::exp(-6.90775527898*i/(sr*mode.t60));
        }
        const double pl=std::abs(projectionL),pr=std::abs(projectionR);
        mode.gain=std::sqrt(pl*pl+pr*pr)/std::max(1e-12,normalization);
        gainSum+=mode.gain;
        mode.pan=clamp(4*std::atan2(pr,pl)/pi-1,-1,1);
        mode.phase=channels==2?std::arg(projectionR*std::conj(projectionL)):0;
    }
    for(int i=0;i<model.count;++i) model.mode[i].gain/=std::max(1e-12,gainSum);
    model.noise=clamp(std::sqrt(flatness)*2,0,1);
    model.confidence=clamp((1-std::sqrt(flatness))*(.55+.45*double(fits)/model.count)*
                          (result.clipped>.005?.65:1),0,1);
    result.ok=model.valid();
    result.message=result.clipped>.005?"Captured; source clips, try a quieter recording":
                   fits<model.count/2?"Captured; short or sustained source, decay is approximate":
                   "Captured: resonances and decay estimated";
    return result;
}
} // namespace m4l::modal
