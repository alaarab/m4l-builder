// Spectral support for pfft~: a power-of-two complex FFT with tables built
// at construction (no allocation while rendering) and the five fftin~/fftout~
// window shapes. Windows follow their textbook periodic definitions; the
// default (hanning, periodic) and fftin~'s raw unnormalised sum are MEASURED
// in Live 12.4.5 (see runtime.hpp pfft~).
#pragma once
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>
namespace m4l::maxcompat {
class FFT {
    size_t size_=0;int bits_=0;
    std::vector<size_t> reversed_;
    std::vector<double> cos_,sin_;
public:
    explicit FFT(size_t size):size_(size) {
        if(size<2 || size>65536 || (size&(size-1)))throw std::invalid_argument("FFT size must be a power of two between 2 and 65536");
        while((size_t(1)<<bits_)<size)++bits_;
        reversed_.resize(size);
        for(size_t i=0;i<size;++i) {size_t r=0;for(int b=0;b<bits_;++b)if(i&(size_t(1)<<b))r|=size_t(1)<<(bits_-1-b);reversed_[i]=r;}
        cos_.resize(size/2);sin_.resize(size/2);
        for(size_t k=0;k<size/2;++k) {const double a=-2*M_PI*double(k)/double(size);cos_[k]=std::cos(a);sin_[k]=std::sin(a);}
    }
    size_t size() const noexcept {return size_;}
    // In-place radix-2. inverse=true conjugates the twiddles and scales by 1/N,
    // so forward(inverse(x)) == x.
    void transform(double* re,double* im,bool inverse) const noexcept {
        const size_t n=size_;
        for(size_t i=0;i<n;++i) {const size_t j=reversed_[i];if(j>i) {std::swap(re[i],re[j]);std::swap(im[i],im[j]);}}
        for(size_t len=2;len<=n;len<<=1) {
            const size_t half=len>>1,step=n/len;
            for(size_t start=0;start<n;start+=len) {
                for(size_t k=0;k<half;++k) {
                    const double wr=cos_[k*step],wi=inverse?-sin_[k*step]:sin_[k*step];
                    const size_t a=start+k,b=a+half;
                    const double xr=re[b]*wr-im[b]*wi,xi=re[b]*wi+im[b]*wr;
                    re[b]=re[a]-xr;im[b]=im[a]-xi;re[a]+=xr;im[a]+=xi;
                }
            }
        }
        if(inverse) {const double scale=1./double(n);for(size_t i=0;i<n;++i) {re[i]*=scale;im[i]*=scale;}}
    }
};
enum class SpectralWindow : int { square=0, triangle=1, hanning=2, hamming=3, blackman=4 };
inline bool spectralWindow(const std::string& name,SpectralWindow& out) noexcept {
    if(name=="square")out=SpectralWindow::square;
    else if(name=="triangle")out=SpectralWindow::triangle;
    else if(name=="hanning")out=SpectralWindow::hanning;
    else if(name=="hamming")out=SpectralWindow::hamming;
    else if(name=="blackman")out=SpectralWindow::blackman;
    else return false;
    return true;
}
inline std::vector<double> spectralWindowTable(SpectralWindow window,size_t size) {
    std::vector<double> w(size,1.);
    const double n=double(size);
    for(size_t i=0;i<size;++i) {
        const double x=double(i);
        switch(window) {
            case SpectralWindow::square:w[i]=1;break;
            case SpectralWindow::triangle:w[i]=1-std::abs(2*x/n-1);break;
            case SpectralWindow::hanning:w[i]=0.5-0.5*std::cos(2*M_PI*x/n);break;
            case SpectralWindow::hamming:w[i]=0.54-0.46*std::cos(2*M_PI*x/n);break;
            case SpectralWindow::blackman:w[i]=0.42-0.5*std::cos(2*M_PI*x/n)+0.08*std::cos(4*M_PI*x/n);break;
        }
    }
    return w;
}
}
