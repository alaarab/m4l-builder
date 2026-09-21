#pragma once
// Experimental shared Max graph runtime. No device names, hashes or DSP ports.
// Typed message objects, bounded timed/deferred dispatch and the existing basic
// audio operators. Preparation still rejects unsupported graphs and DSP loops.
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <functional>
#include <stdexcept>
#include <vector>
#include "message.hpp"
#include "routing.hpp"
#include "spectral.hpp"
#include "loudness.hpp"
#include "fzero.hpp"
#include "../modal/modal_core.hpp"
#include "gen_graph.hpp"
#include "signal_selector.hpp"
#include "signal_snapshot.hpp"
#include "signal_record.hpp"
#include "buffer_transform.hpp"
#include "dsp_state.hpp"
#include "expression.hpp"

namespace m4l::maxcompat {
enum class Op : int { input, output, multiply, add, subtract, signal, line, dbtoa, pack, dial, meter, decoration,
    trigger, route, prepend, append, integer, floating, loadbang, loadmess, message, deferlow, delay,
    controlAdd, controlSubtract, controlMultiply, controlDivide, reverseSubtract, select, pak, boundary, gen, namedSend, namedReceive, external, buffer, signalSelector, signalSnapshot, signalRecord, dspState, expression, unpack, controlModulo, clip, scale, adStatus, textButton, uButton, plugSync, change, gate, compareEqual, compareUnequal, compareGreater, compareLess, compareGreaterEqual, compareLessEqual, counter, speedlim, peakAmp, controlMaximum, controlMinimum, transport, zlRegister, reverseSubtractSignal, averageSignal, conditional, zlLength, zlGroup, listFunnel, spray, liveRemote, uzi, modalExternal, midiIn, inert, onePole, sprintf, atodb, squareRoot, pfft, fftIn, fftOut, poke, cartopol, clipSignal, polyIn, polyOut, indexSignal, randomInt, pipe, metro, translate, accum, reverseDivide, split, stripNote, switchGate, noteIn, ctlIn, cpuClock, coll, bufferInfo, mpeParse, adsr, tapIn, tapOut, randSignal, scope, filterCoeff, biquad, divideSignal, absSignal, sendSignal, receiveSignal, loudness, midiToolIn, midiToolOut, overdrive, degrade, tanhSignal, polyUp, peek, functionCurve, fzero, liveDrop };
enum class Format : int { bang, integer, floating, list, symbol, anything, constant };
constexpr double kButtonFlashMs=100.;   // live.text button-mode flash after a bang message: MEASURED 102-114 ms (Live, September 11)
struct SpectralDefinition;
struct Definition {
    Op op = Op::decoration;
    std::vector<double> arguments;
    std::vector<bool> integers;
    double initial = 0, minimum = 0, maximum = 1;
    bool initialize = false;
    double parameterExponent=1;
    int parameterSteps=0;
    int parameterType=0; // Max float, integer, enum
    int controlKind=0; // numeric control, menu, text toggle, text button
    std::vector<Symbol> parameterLabels;
    std::array<Symbol,2> textLabels{};
    std::vector<Atom> atoms;
    std::vector<Format> formats;
    std::vector<int> substitutions;
    std::vector<int> separators;
    std::shared_ptr<const m4l::gen::GraphDefinition> genGraph;
    int genInputs=0,genOutputs=0;
    bool presentation=false;
    std::string expression;
    // pfft~: the spectral subpatch compiled as its own graph.
    std::shared_ptr<const SpectralDefinition> spectral;
};
struct Edge { int source, outlet, destination, inlet; };
struct SpectralDefinition { std::vector<Definition> definitions; std::vector<Edge> edges; int size=0,overlap=0,inlets=0,outlets=0; };
class Runtime {
public:
    struct ExternalEvent { int node=0, inlet=0; uint64_t sample=0; Message message; };
private:
    struct SpectralHost;
    struct Node {
        Definition definition;
        // pfft~ host, and for fftin~/fftout~ inside a spectral subpatch the
        // frame slot this node reads/writes. poke~ holds its buffer table.
        std::unique_ptr<SpectralHost> spectral;int spectralSlot=-1;
        // poly~ voice muting: a muted node is skipped in render (outputs 0,
        // state frozen); messages still reach it, as in Max.
        bool muted=false;
        // random: xorshift64* state (Max's generator is not matched; the
        // contract is a uniform int in [0, range) and 'seed N').
        uint64_t rng=0x9E3779B97F4A7C15ull;
        // MIDI parsers (notein/ctlin): running status and pending data byte.
        int midiStatus=0,midiData=-1;
        // coll: bounded entry pool (index, atoms) sorted by index on demand.
        struct CollEntry { int64_t index=0; int count=0; std::array<Atom,32> atoms{}; };
        std::vector<CollEntry> entries;int entryCount=0;
        // tapout~: the tapin~ node whose ring it reads (resolved from the cord).
        int tapSource=-1;
        // receive~: the send~ node (same name) whose sample it repeats.
        int sendSource=-1;
        std::unique_ptr<LoudnessMeter> loudness;
        std::unique_ptr<FZero> fzero;
        // function: breakpoints (x, y, curve of the segment ending here), x-sorted.
        struct Breakpoint { double x=0,y=0,curve=0; };
        std::vector<Breakpoint> points;
        // biquad~: x[n-1], x[n-2], y[n-1], y[n-2]; filtercoeff~: type and resample counter.
        double bqX1=0,bqX2=0,bqY1=0,bqY2=0;int filterType=0;uint64_t coeffCounter=0;
        // scope~/spectroscope~: a frame of display values published under a
        // seqlock (odd while the renderer writes) for the host to draw.
        std::vector<float> frame,frameWork;std::unique_ptr<std::atomic<uint32_t>> frameSeq;size_t frameFill=0,frameCount=0;
        std::unique_ptr<FFT> spectralFFT;std::vector<double> fftRe,fftIm;
        std::shared_ptr<m4l::gen::Table> pokeTable;
        std::array<double, 64> values{};
        std::vector<double> output;
        std::vector<std::vector<Edge>> signalInputs;
        std::unique_ptr<m4l::gen::Graph> gen;
        std::unique_ptr<SignalSelector> selector;
        std::unique_ptr<SignalSnapshot> snapshot;
        std::unique_ptr<SignalRecord> recorder;
        std::unique_ptr<DSPState> dspState;
        std::unique_ptr<Expression> expression;
        // m4l.modal~ external bound to the app's own modal engine.
        std::unique_ptr<m4l::modal::Engine> modal;uint64_t modalMeterDue=0;
        // average~: window ring buffer and running sum of |x|.
        std::vector<double> ring;size_t ringIndex=0;double ringSum=0;
        std::array<double,64> genValues{};
        std::vector<Edge> messages;
        double target = 0, step = 0, time = 0, peak = 0;
        uint64_t remaining = 0;
        std::array<Atom,Message::capacity> stored{};
        std::array<int,Message::capacity> substitutions{};
        std::array<int,Message::capacity> separators{};
        int storedCount=0;
        bool delayActive=false;
        // speedlim: the most recent message held back until the interval elapses.
        Message pending;bool hasOutput=false;uint64_t lastOutput=0;
        // zl.reg: the held list.
        Message held;bool hasHeld=false;
        bool signalOutlet=false;
        uint64_t due=0, serial=0;
    };
    static constexpr size_t kTapMinimumDelay=64;
    struct Command { int node = 0, inlet = 0; Message message; };
    // Spectral frames exchanged with an enclosing pfft~ host: one slot per
    // fftin~ (filled before each frame render) and per fftout~ (read after).
    struct FrameIO { int port=0; SpectralWindow window=SpectralWindow::hanning; std::vector<double> real,imag; };
    std::vector<FrameIO> spectralIn_,spectralOut_;
    int frameIndex_=0;
public:
    std::vector<FrameIO>& spectralInputs() noexcept {return spectralIn_;}
    std::vector<FrameIO>& spectralOutputs() noexcept {return spectralOut_;}
private:
    // pfft~: ONE instance of the spectral subpatch (its own Runtime) fired
    // every hop, so per-bin gen~ History sees every frame (MEASURED in Live:
    // a frame counter read 174 at 2 s and 346 at 4 s = SR/hop, not /4). Frames are
    // windowed per fftin~/fftout~ object, the inverse is scaled by 1/N and
    // overlap-add is normalised per sample by the synthesis window's own
    // squared overlap sum, so a matched-window passthrough is exactly unity
    // (MEASURED in Live 12.4.5: unity at overlap 2 and 4). Latency is one
    // frame (MEASURED: size, not size-hop). MEASURED (max4liveplugins bin
    // dump, 1 kHz into 2048/4): the default window is the PERIODIC HANN
    // 0.5-0.5cos(2*pi*n/N) and fftin~ emits the RAW unnormalised DFT sum
    // (bins 44..49 = 13.25/103.58/451.21/416.45/71.56/11.26, digit-exact
    // against numpy rfft of the hann-windowed tone).
    struct SpectralHost {
        int size=0,overlap=0,hop=0,inlets=0,outlets=0;
        uint64_t time=0;
        FFT fft;
        // poly~ up N mode: `size` is the factor. Max's resampling filters,
        // MEASURED September 11 (peer captures of the interpolator inside the
        // voice, the decimator via a click~ inside the voice, and the
        // pass-through composite, all reproduced to 1.5e-8): a 4-section
        // polyphase-allpass half-band IIR, r^2 = {0.0520373, 0.4378391} on
        // the direct branch and {0.2013989, 0.7739094} on the delayed branch;
        // interpolation repeats each input sample (zero-order hold) through
        // it, decimation keeps the odd output phase. up 4 is two cascaded
        // stages (measured to 3e-4); the matching two-stage decimation is
        // the symmetric assumption (UNMEASURED beyond up 2).
        bool resampled=false;
        struct HalfBand {
            struct Section { double c; double x1=0,x2=0,y1=0,y2=0; };
            Section direct[2]{{0.0520373},{0.4378391}},delayed[2]{{0.2013989},{0.7739094}};
            double held=0;   // the delayed branch's z^-1
            static double allpass(Section& s,double x) noexcept {
                const double y=s.c*(x-s.y2)+s.x2;
                s.x2=s.x1;s.x1=x;s.y2=s.y1;s.y1=y;return y;
            }
            double process(double x) noexcept {
                const double a=allpass(direct[1],allpass(direct[0],x));
                const double b=allpass(delayed[1],allpass(delayed[0],x));
                const double y=0.5*(a+held);held=b;return y;
            }
        };
        std::vector<std::vector<HalfBand>> upStages,downStages;   // [port][stage]
        std::vector<std::unique_ptr<Runtime>> copies;
        std::vector<std::vector<double>> inRing,outRing;   // [inlet][size], [outlet][size]
        std::vector<std::vector<double>> windows;           // by SpectralWindow index (built on demand)
        std::vector<std::vector<double>> synthesisNorm;     // by SpectralWindow index: 1/sum of squared overlaps
        std::vector<double> re,im;
        std::vector<float> scratchL,scratchR;
        SpectralHost(int size_,int overlap_,int inlets_,int outlets_,bool resampled_=false):size(size_),overlap(overlap_),hop(size_/overlap_),inlets(inlets_),outlets(outlets_),fft(resampled_?16:size_t(size_)),resampled(resampled_) {
            inRing.assign(size_t(inlets),std::vector<double>(size_t(size),0.));
            outRing.assign(size_t(outlets),std::vector<double>(size_t(size),0.));
            windows.resize(5);synthesisNorm.resize(5);
            re.assign(size_t(size),0.);im.assign(size_t(size),0.);
            scratchL.assign(size_t(std::max(size,16)),0.f);scratchR.assign(size_t(std::max(size,16)),0.f);
            if(resampled) {
                int stages=0;for(int f=size;f>1;f>>=1)++stages;
                upStages.assign(size_t(inlets),std::vector<HalfBand>(size_t(stages)));
                downStages.assign(size_t(outlets),std::vector<HalfBand>(size_t(stages)));
            }
        }
        // Interpolate one base-rate sample into `size` oversampled samples:
        // each stage holds its input twice and filters (zero-order hold).
        void interpolate(std::vector<HalfBand>& stages,double x,double* out) noexcept {
            double buffer[16];buffer[0]=x;int count=1;
            for(auto& stage:stages) {
                double next[16];
                for(int i=0;i<count;++i) {next[2*i]=stage.process(buffer[i]);next[2*i+1]=stage.process(buffer[i]);}
                count*=2;for(int i=0;i<count;++i)buffer[i]=next[i];
            }
            for(int i=0;i<count;++i)out[i]=buffer[i];
        }
        // Decimate `size` oversampled samples to one: each stage filters and
        // keeps the odd phase (measured), innermost stage first.
        double decimate(std::vector<HalfBand>& stages,const double* in) noexcept {
            double buffer[16];int count=size;for(int i=0;i<count;++i)buffer[i]=in[i];
            for(auto it=stages.rbegin();it!=stages.rend();++it) {
                double next[16];
                for(int i=0;i<count;i+=2) {(void)it->process(buffer[i]);next[i/2]=it->process(buffer[i+1]);}
                count/=2;for(int i=0;i<count;++i)buffer[i]=next[i];
            }
            return buffer[0];
        }
        // One host sample at the base rate: zero-stuff and lowpass each inlet
        // into `factor` frames, run the subpatch once over them, lowpass the
        // outputs and keep the frame aligned with this sample.
        void processResampled(const double* inputs,double* outputs) noexcept {
            auto& child=*copies[0];
            for(int i=0;i<inlets;++i) {
                auto* io=childInput(child,i);double frames[16];
                interpolate(upStages[size_t(i)],inputs[i],frames);
                if(io)for(int k=0;k<size;++k)io->real[size_t(k)]=frames[k];
            }
            child.render(nullptr,nullptr,scratchL.data(),scratchR.data(),size);
            for(int o=0;o<outlets;++o) {
                const auto* io=childOutput(child,o);double frames[16];
                for(int k=0;k<size;++k)frames[k]=io?io->real[size_t(k)]:0.;
                outputs[o]=decimate(downStages[size_t(o)],frames);
            }
        }
        static FrameIO* childInput(Runtime& child,int port) noexcept {for(auto& io:child.spectralInputs())if(io.port==port)return &io;return nullptr;}
        static const FrameIO* childOutput(Runtime& child,int port) noexcept {for(auto& io:child.spectralOutputs())if(io.port==port)return &io;return nullptr;}
        const std::vector<double>& window(SpectralWindow w) {
            auto& table=windows[size_t(w)];
            if(table.empty())table=spectralWindowTable(w,size_t(size));
            return table;
        }
        const std::vector<double>& normalization(SpectralWindow w) {
            auto& table=synthesisNorm[size_t(w)];
            if(table.empty()) {
                const auto& ws=window(w);table.assign(size_t(size),0.);
                for(int n=0;n<size;++n) {
                    double sum=0;for(int k=0;k<overlap;++k) {const double v=ws[size_t((n+k*hop)%size)];sum+=v*v;}
                    table[size_t(n)]=sum>1e-12?1./sum:0.;
                }
            }
            return table;
        }
        void prepare() {for(auto& w:{SpectralWindow::square,SpectralWindow::triangle,SpectralWindow::hanning,SpectralWindow::hamming,SpectralWindow::blackman}) {(void)window(w);(void)normalization(w);}}
        // One host sample: emit the overlap-added output first, then push the
        // input and, on a hop boundary, fire the next copy on the frame that
        // ends with this sample. Emission of frame contribution n happens at
        // time t+1+n, i.e. one frame of latency.
        void process(const double* inputs,double* outputs) noexcept {
            const size_t pos=size_t(time%uint64_t(size));
            for(int o=0;o<outlets;++o) {outputs[o]=outRing[size_t(o)][pos];outRing[size_t(o)][pos]=0;}
            for(int i=0;i<inlets;++i)inRing[size_t(i)][pos]=inputs[i];
            ++time;
            if(time%uint64_t(hop)==0)fire(0);
        }
        void fire(size_t copy) noexcept {
            auto& child=*copies[copy];
            const size_t base=size_t(time%uint64_t(size));   // ring index of the oldest frame sample (time t-size+1)
            for(auto& port:child.spectralInputs()) {
                const auto& wa=windows[size_t(port.window)];const auto& ring=inRing[size_t(port.port)];
                for(int n=0;n<size;++n) {re[size_t(n)]=ring[(base+size_t(n))%size_t(size)]*wa[size_t(n)];im[size_t(n)]=0;}
                fft.transform(re.data(),im.data(),false);
                std::copy(re.begin(),re.end(),port.real.begin());std::copy(im.begin(),im.end(),port.imag.begin());
            }
            child.render(nullptr,nullptr,scratchL.data(),scratchR.data(),size);
            for(auto& port:child.spectralOutputs()) {
                std::copy(port.real.begin(),port.real.end(),re.begin());std::copy(port.imag.begin(),port.imag.end(),im.begin());
                fft.transform(re.data(),im.data(),true);
                const auto& ws=windows[size_t(port.window)];const auto& norm=synthesisNorm[size_t(port.window)];auto& out=outRing[size_t(port.port)];
                for(int n=0;n<size;++n)out[(base+size_t(n))%size_t(size)]+=re[size_t(n)]*ws[size_t(n)]*norm[size_t(n)];
            }
        }
        bool faulted() const noexcept {for(const auto& c:copies)if(c->faulted())return true;return false;}
    };
    std::vector<Node> nodes_;
    std::vector<int> schedule_;
    std::array<Command, 256> queue_{};
    std::vector<Command> restoreQueue_;   // saved controls awaiting initialize()
    // Separate queues preserve single-producer ownership: session parameter
    // commands originate on render, whereas external replies come from control.
    // Script event/reply rings scale with the graph (256 .. 4096 slots) so a
    // large device's initialization burst (Shard: ~2000 objects feeding ten
    // scripts) is not lost before the host drains it. Sized at construction.
    std::vector<ExternalEvent> externalEvents_;
    std::vector<Command> externalReplies_;
    std::atomic<unsigned> eventWrite_{0}, eventRead_{0}, replyWrite_{0}, replyRead_{0};
    std::atomic<unsigned> write_{0}, read_{0}, rejected_{0};
    std::atomic<bool> fault_{false};
    // Published by the owning session when its bypass command is committed.
    std::atomic<bool> deviceEnabled_{true};
    Symbol mappedSymbol_=0;   // live.remote~ status selector
    Symbol modalStatus_=0,modalMeter_=0,modalModel_=0,modalUnsupported_=0;   // m4l.modal~ outlet selectors
    Symbol functionPoints_=0,functionSetcurve_=0;   // function: host point publication / setcurve selector
    Symbol dropPath_=0,dropLegend_=0,dropClear_=0;   // live.drop: host path publication, legend attribute, clear
    uint64_t instanceBase_=0;   // '---' namespace for host-side name resolution
    // Host transport for plugsync~. Written by the host before each block,
    // read once per block on the audio thread; beats advance within the block.
    std::atomic<bool> transportPlaying_{false};
    std::atomic<double> transportTempo_{120},transportBeat_{0};
    // Node budget: Orbit expands to 960 objects.
    std::array<std::atomic<double>, 4096> meters_{};
    std::array<std::atomic<double>, 4096> parameterValues_{};
    std::vector<int> parameterNodes_;
    // Prepared live.remote~ node indices. The owning session uses this
    // immutable list to allocate its cross-device bridge before rendering.
    std::vector<int> liveRemoteNodes_;
    double sampleRate_;
    int budget_ = 0;
    Symbols symbols_;
    std::shared_ptr<RoutingDomain> routing_;
    size_t routingMember_=SIZE_MAX;
    std::vector<int> parameterOrder_;
    bool initialized_=false;
    bool dspActive_=false,hasPlugSync_=false,hasPeakAmp_=false,hasModal_=false,hasMidiIn_=false;
    std::vector<int> midiInNodes_;
    bool audioDispatch_=false;
    int budgetPerBlock_=4096;
    int* dispatchBudget_=&budget_;
    static bool receiveNamed(void* context,int node,const Message& message,int depth,int* budget) noexcept {
        auto& runtime=*static_cast<Runtime*>(context);
        if(runtime.fault_)return false;
        if(depth>64) {runtime.fault_=true;*budget=-1;return false;}
        int* previous=runtime.dispatchBudget_;runtime.dispatchBudget_=budget;
        runtime.emit(node,message,depth);
        runtime.dispatchBudget_=previous;return !runtime.fault_;
    }
    uint64_t sampleTime_=0, serial_=0, nextDue_=UINT64_MAX;
    struct Deferred { int source=0; Message message; };
    std::array<Deferred,256> deferred_{};
    unsigned deferredRead_=0,deferredWrite_=0;
    std::atomic<bool> deferredPending_{false};
public:
    using Trace=void(*)(void*,int,int,uint64_t,const Message&) noexcept;
private:
    Trace trace_=nullptr;
    void* traceContext_=nullptr;
    static bool signalOutput(Op op) noexcept {
        return op == Op::input || op == Op::multiply || op == Op::add || op == Op::subtract || op == Op::reverseSubtractSignal || op == Op::averageSignal || op == Op::onePole || op == Op::modalExternal || op == Op::signal || op == Op::line || op == Op::gen || op == Op::signalSelector || op == Op::signalRecord || op == Op::pfft || op == Op::fftIn || op == Op::cartopol || op == Op::clipSignal || op == Op::polyIn || op == Op::polyOut || op == Op::indexSignal || op == Op::adsr || op == Op::tapIn || op == Op::tapOut || op == Op::randSignal || op == Op::filterCoeff || op == Op::biquad || op == Op::divideSignal || op == Op::absSignal || op == Op::sendSignal || op == Op::receiveSignal || op == Op::overdrive || op == Op::degrade || op == Op::tanhSignal || op == Op::polyUp;
    }
    // sprintf: each definition atom is one whitespace-separated token of the
    // format and arguments[i] codes that token: 0 literal word (interned at
    // construction), 1 integer conversion (%d %i %u), 2 %s, 3+P float
    // conversion with P decimals (%f %.Pf). Max re-parses the formatted text
    // into atoms unless 'symout' is given, so literal words stay symbols,
    // numbers stay numbers and no symbol is created at run time. Tokens that
    // mix text and a conversion, symout and other conversions are rejected by
    // the compiler because they would need transient symbols.
    static int sprintfConversions(const Definition& d) noexcept {
        int count=0;for(double code:d.arguments) if(code!=0)++count;return count;
    }
    static int inletCount(const Definition& d) noexcept {
        switch (d.op) {
            case Op::external: return int(d.arguments[0]);
            case Op::sprintf: return std::max(1,sprintfConversions(d));
            case Op::inert: return d.arguments.size()>1?int(d.arguments[1]):int(d.arguments[0]);   // [outlets] (ports mirror) or [outlets, inlets]
            case Op::midiToolIn: return 0;
            case Op::midiToolOut: return 1;
            case Op::pfft: return d.spectral?d.spectral->inlets:0;
            case Op::fftIn: return 1;
            case Op::fftOut: return 2;
            case Op::poke: return 3;
            case Op::cartopol: return 2;
            case Op::clipSignal: return 3;
            case Op::indexSignal: return 2;
            case Op::randomInt: case Op::pipe: case Op::metro: case Op::stripNote: return 2;
            case Op::accum: case Op::split: return 3;
            case Op::switchGate: return int(d.arguments[0])+1;
            case Op::noteIn: case Op::ctlIn: return 1;
            case Op::bufferInfo: case Op::mpeParse: return 1;
            case Op::adsr: return 5;
            case Op::tapIn: return 1;
            case Op::tapOut: return std::max(1,int(d.arguments.size()));
            case Op::randSignal: return 1;
            case Op::scope: return 2;
            case Op::filterCoeff: return 3;
            case Op::biquad: return 6;
            case Op::divideSignal: return 2;
            case Op::absSignal: case Op::sendSignal: return 1;
            case Op::receiveSignal: return 1;
            case Op::loudness: return std::max(1,int(d.arguments[0]));
            case Op::overdrive: return 2;
            case Op::degrade: return 3;
            case Op::tanhSignal: return 1;
            case Op::polyUp: return d.spectral?d.spectral->inlets:0;
            case Op::peek: return 3;
            case Op::functionCurve: return 2;
            case Op::fzero: return 1;
            case Op::signalSelector: return int(d.arguments[0])+1;
            case Op::signalSnapshot: return 2;
            case Op::signalRecord: return int(d.arguments[0])+2;
            case Op::expression: return int(d.arguments[0]);
            case Op::conditional: return int(d.arguments[0]);
            case Op::gen:return std::max(1,d.genInputs);
            case Op::decoration: return d.presentation?1:0;
            case Op::input: case Op::namedReceive: return 0;
            case Op::output: case Op::multiply: case Op::add: case Op::subtract: case Op::reverseSubtractSignal: case Op::line: case Op::modalExternal: case Op::onePole: return 2;
            case Op::pack: case Op::pak: return int(d.atoms.empty() ? d.arguments.size() : d.atoms.size());
            case Op::integer: case Op::floating: case Op::delay: case Op::message:
            case Op::controlAdd: case Op::controlSubtract: case Op::controlMultiply: case Op::controlDivide: case Op::reverseSubtract: case Op::controlModulo: return 2;
            case Op::compareEqual: case Op::compareUnequal: case Op::compareGreater: case Op::compareLess: case Op::compareGreaterEqual: case Op::compareLessEqual: case Op::controlMaximum: case Op::controlMinimum: return 2;
            case Op::clip: return 3;
            case Op::gate: return 2;
            case Op::counter: return 5;
            case Op::speedlim: case Op::transport: case Op::zlRegister: case Op::zlLength: case Op::zlGroup: case Op::liveRemote: case Op::uzi: return 2;
            case Op::scale: return 5;
            case Op::route: case Op::select: return d.atoms.size()==1 ? 2:1;
            default: return 1;
        }
    }
    static int outletCount(const Definition& d) noexcept {
        const auto op=d.op;
        switch (op) {
            case Op::external: return int(d.arguments[1]);
            case Op::gen:return d.genOutputs;
            case Op::pfft: return d.spectral?d.spectral->outlets:0;
            case Op::fftIn: return 3;
            case Op::fftOut: case Op::poke: return 0;
            case Op::cartopol: return 2;
            case Op::input: return 2;
            case Op::dial: return d.controlKind==1?3:2;
            case Op::buffer: return 2;
            case Op::dspState: return 4;
            // Line completion bang and meter messages
            // are not supported yet: reject connected outlets at preparation.
            case Op::output: case Op::meter: case Op::decoration: case Op::namedSend: return 0;
            case Op::textButton: return 3;
            case Op::adStatus: return 2;
            case Op::uButton: return 4;
            case Op::plugSync: return 9;
            case Op::change: return 3;
            case Op::controlMaximum: case Op::controlMinimum: return 2;   // value, winning-inlet index
            case Op::transport: return 9;
            case Op::zlRegister: case Op::zlLength: case Op::zlGroup: return 2;
            case Op::uzi: return 3;
            case Op::modalExternal: return 3;   // stereo signal + messages
            case Op::split: case Op::stripNote: return 2;
            case Op::noteIn: return 3;
            case Op::ctlIn: return d.arguments.empty()?3:2;
            case Op::coll: return 4;
            case Op::bufferInfo: case Op::mpeParse: return 10;
            case Op::adsr: return 4;
            case Op::tapOut: return std::max(1,int(d.arguments.size()));
            case Op::scope: return d.arguments.empty() || d.arguments[0]==0?0:1;   // scope~ has none; spectroscope~ one (unmodelled)
            case Op::filterCoeff: return 5;
            case Op::loudness: return 6;
            case Op::polyUp: return d.spectral?d.spectral->outlets:0;
            case Op::peek: return 1;
            case Op::functionCurve: return 4;
            case Op::liveDrop: return 2;   // pathname, file type code (type code UNMEASURED, never emitted)
            case Op::fzero: return 3;
            case Op::sendSignal: return 1;   // hidden link outlet for the receive~ pairing; the compiler never cords it
            case Op::inert: return int(d.arguments[0]);   // [outlets, inlets]
            case Op::midiToolIn: return 2;
            case Op::midiToolOut: return 0;
            case Op::counter: return 4;
            case Op::gate: return int(d.arguments.empty()?1:d.arguments[0]);
            case Op::spray: return int(d.arguments[0]);
            case Op::trigger: case Op::unpack: return int(d.formats.size());
            case Op::route: case Op::select: return int(d.atoms.size()+1);
            default: return 1;
        }
    }
    static bool signalInput(Op op) noexcept {
        return op == Op::output || op == Op::multiply || op == Op::add || op == Op::subtract || op == Op::reverseSubtractSignal || op == Op::meter || op == Op::boundary || op == Op::gen || op == Op::signalSelector || op == Op::signalSnapshot || op == Op::signalRecord || op == Op::dspState || op == Op::plugSync || op == Op::peakAmp || op == Op::averageSignal || op == Op::onePole || op == Op::liveRemote || op == Op::modalExternal || op == Op::pfft || op == Op::fftOut || op == Op::poke || op == Op::cartopol || op == Op::clipSignal || op == Op::polyIn || op == Op::polyOut || op == Op::indexSignal || op == Op::tapIn || op == Op::tapOut || op == Op::scope || op == Op::filterCoeff || op == Op::biquad || op == Op::divideSignal || op == Op::absSignal || op == Op::sendSignal || op == Op::receiveSignal || op == Op::loudness || op == Op::overdrive || op == Op::degrade || op == Op::tanhSignal || op == Op::polyUp || op == Op::fzero;
    }
    static bool numericColdInlet(Op op,int inlet) noexcept {
        if(inlet==0)return false;
        return op==Op::integer || op==Op::floating || op==Op::pack || op==Op::message ||
            op==Op::route || op==Op::select || op==Op::controlModulo || op==Op::clip || op==Op::scale || (op>=Op::compareEqual && op<=Op::compareLessEqual) || op==Op::controlMaximum || op==Op::controlMinimum || (op>=Op::controlAdd && op<=Op::reverseSubtract) ||
            // Settings inlets of the sequencer/signal objects: they store and never emit.
            op==Op::metro || op==Op::pipe || op==Op::randomInt || op==Op::accum || op==Op::split || op==Op::stripNote || op==Op::adsr || op==Op::clipSignal || op==Op::onePole || op==Op::indexSignal || op==Op::poke || op==Op::reverseDivide || op==Op::speedlim || op==Op::zlGroup;
    }
    void emit(int source, const Message& message, int depth,int outlet=0) noexcept {
        if(!message.valid(symbols_.size())) {
            const bool before=fault_.load(std::memory_order_relaxed);
            faultBecause("emitted message failed validation (atom count/type or symbol table)");
            if(!before)attributeFault(source,outlet,int(message.kind),message.selector,true);
            return;
        }
        if(trace_) trace_(traceContext_,source,outlet,sampleTime_,message);
        for (const auto& edge : nodes_[source].messages) if(edge.outlet==outlet) deliver(edge.destination, edge.inlet, message, depth + 1);
    }
    // function: insert or replace the point at x (keeps x order); bounded to
    // the reserved 256 points, never allocating in render.
    static void functionAdd(Node& n,double x,double y,double curve) noexcept {
        if(!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(curve))return;
        auto it=std::lower_bound(n.points.begin(),n.points.end(),x,[](const Node::Breakpoint& p,double v){return p.x<v;});
        if(it!=n.points.end() && it->x==x) {it->y=y;it->curve=curve;return;}
        if(n.points.size()>=256)return;
        n.points.insert(it,Node::Breakpoint{x,y,curve});
    }
    // function classic curve (mode 1, classic_curve 1), MEASURED on Max 9
    // September 11: y = y0 + (y1-y0)·(exp(k·u)-1)/(exp(k)-1), residual 3e-16
    // at 47 curve values; k(c) is odd (k(-c) = -k(c)) and has no closed form,
    // so it is the measured table, linearly interpolated between samples
    // (MEASURED smooth at 0.005 steps). c >= 0.995 is k = 45.768, a real
    // curve rather than a step.
    static double functionCurveK(double c) noexcept {
        // 0.05 steps to 0.9 (linear interpolation error 0.015%), 0.005 steps
        // above (4.4% otherwise); k saturates at c = 0.995.
        static constexpr double cs[]={0,0.01,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,
            0.9,0.905,0.91,0.915,0.92,0.925,0.93,0.935,0.94,0.945,0.95,0.955,0.96,0.965,0.97,0.975,0.98,0.985,0.99,0.995};
        static constexpr double ks[]={0,0.174294,0.402787,0.616841,0.819865,1.028014,1.249570,1.491184,1.759665,2.062972,2.411139,2.817463,3.300292,3.885929,4.613702,5.545334,6.783734,8.514392,11.109240,
            15.439795,16.038016,16.679245,17.368303,18.110756,18.913074,19.782809,20.728847,21.761699,22.893906,24.140544,25.519899,27.054377,28.771725,30.706726,32.903585,35.419343,38.328906,41.732632,45.768146};
        constexpr size_t count=sizeof(cs)/sizeof(cs[0]);
        const double a=std::min(std::fabs(c),0.995);
        size_t i=1;while(i<count-1 && cs[i]<a)++i;
        const double k=ks[i-1]+(ks[i]-ks[i-1])*(a-cs[i-1])/(cs[i]-cs[i-1]);
        return c<0?-k:k;
    }
    static double functionWarp(double t,double curve) noexcept {
        if(curve==0)return t;
        const double k=functionCurveK(curve);
        return (std::exp(k*t)-1)/(std::exp(k)-1);
    }
    // y at x: linear between breakpoints, or the measured classic curve when
    // the segment's curve parameter is non-zero (stored on the segment's
    // destination point, as Max's dump shows).
    static double functionValue(const Node& n,double x) noexcept {
        // Refpage: an X outside the first or last breakpoint yields 0.
        if(n.points.empty() || !std::isfinite(x))return 0;
        if(x<n.points.front().x || x>n.points.back().x)return 0;
        if(x==n.points.front().x)return n.points.front().y;
        if(x==n.points.back().x)return n.points.back().y;
        for(size_t i=1;i<n.points.size();++i) {
            const auto& a=n.points[i-1];const auto& b=n.points[i];
            if(x>b.x)continue;
            const double t=b.x>a.x?(x-a.x)/(b.x-a.x):1;
            // Mode 0 (linear) carries no curve information (refpage).
            return a.y+(b.y-a.y)*functionWarp(t,n.definition.arguments[3]!=0?b.curve:0);
        }
        return n.points.back().y;
    }
    // function: every change to the point list (message or host touch edit)
    // is published to the host as 'points <total> <offset> x y c ...' chunks
    // on the control queue, so the drawn curve and the collected blob follow
    // the object's state rather than the box's saved points.
    void functionPublish(int index) noexcept {
        const auto& n=nodes_[index];
        constexpr int perChunk=(Message::capacity-2)/3;
        const int total=int(n.points.size());
        for(int offset=0;offset<total || (total==0 && offset==0);offset+=perChunk) {
            Message out=Message::anything(functionPoints_);
            out.atoms[0]=Atom::integral(total);out.atoms[1]=Atom::integral(offset);int count=2;
            for(int i=offset;i<total && i<offset+perChunk;++i) {
                out.atoms[size_t(count++)]=Atom::real(n.points[size_t(i)].x);
                out.atoms[size_t(count++)]=Atom::real(n.points[size_t(i)].y);
                out.atoms[size_t(count++)]=Atom::real(n.points[size_t(i)].curve);
            }
            out.count=count;queueExternal(index,0,out);
            if(total==0)break;
        }
    }
    // filtercoeff~ types: 0 lowpass, 1 highpass, 2 bandpass, 3 bandstop,
    // 4 peaknotch, 5 lowshelf, 6 highshelf, 7 allpass, 8 off (unity). RBJ
    // cookbook with Q and A = sqrt(linear gain); outputs a0 a1 a2 b1 b2 in
    // Max's biquad~ convention (normalised by the cookbook's a0).
    void filterCoefficients(Node& n) const noexcept {
        const double f=std::min(std::max(n.values[0],1.),sampleRate_*0.49),g=std::max(n.values[1],1e-6),q=std::max(n.values[2],1e-3);
        const double w=2*M_PI*f/sampleRate_,c=std::cos(w),sn=std::sin(w),alpha=sn/(2*q),A=std::sqrt(g),beta=std::sqrt(A)/q;
        double b0=1,b1=0,b2=0,a0=1,a1=0,a2=0;
        switch(n.filterType) {
            case 0:b0=(1-c)/2;b1=1-c;b2=(1-c)/2;a0=1+alpha;a1=-2*c;a2=1-alpha;break;
            case 1:b0=(1+c)/2;b1=-(1+c);b2=(1+c)/2;a0=1+alpha;a1=-2*c;a2=1-alpha;break;
            case 2:b0=alpha;b1=0;b2=-alpha;a0=1+alpha;a1=-2*c;a2=1-alpha;break;
            case 3:b0=1;b1=-2*c;b2=1;a0=1+alpha;a1=-2*c;a2=1-alpha;break;
            case 4:b0=1+alpha*A;b1=-2*c;b2=1-alpha*A;a0=1+alpha/A;a1=-2*c;a2=1-alpha/A;break;
            case 5:b0=A*((A+1)-(A-1)*c+beta*sn);b1=2*A*((A-1)-(A+1)*c);b2=A*((A+1)-(A-1)*c-beta*sn);a0=(A+1)+(A-1)*c+beta*sn;a1=-2*((A-1)+(A+1)*c);a2=(A+1)+(A-1)*c-beta*sn;break;
            case 6:b0=A*((A+1)+(A-1)*c+beta*sn);b1=-2*A*((A-1)+(A+1)*c);b2=A*((A+1)+(A-1)*c-beta*sn);a0=(A+1)-(A-1)*c+beta*sn;a1=2*((A-1)-(A+1)*c);a2=(A+1)-(A-1)*c-beta*sn;break;
            case 7:b0=1-alpha;b1=-2*c;b2=1+alpha;a0=1+alpha;a1=-2*c;a2=1-alpha;break;
            default:break;
        }
        n.output[0]=b0/a0;n.output[1]=b1/a0;n.output[2]=b2/a0;n.output[3]=a1/a0;n.output[4]=a2/a0;
    }
    // Outlined emit helpers: at -O0 every Message temporary in control()
    // owned its own 2 KB stack slot (134 KB per frame), and a five-deep
    // control->emit->deliver chain overflowed the 512 KB cooperative-thread
    // stack once Message::capacity grew to 128. Each helper holds the one
    // temporary in its own short-lived frame instead.
    void emitSingle(int source,Atom a,int depth,int outlet=0) noexcept { emit(source,Message::single(a),depth,outlet); }
    void emitNumber(int source,double v,int depth,int outlet=0) noexcept { emit(source,Message::number(v),depth,outlet); }
    void emitInteger(int source,int64_t v,int depth,int outlet=0) noexcept { emit(source,Message::integer(v),depth,outlet); }
    void emitSequence(int source,const Atom* values,int n,int depth,int outlet=0) noexcept { emit(source,Message::sequence(values,n),depth,outlet); }
    void emitBang(int source,int depth,int outlet=0) noexcept { emit(source,Message{},depth,outlet); }
    void nextDelay() noexcept {
        nextDue_=UINT64_MAX;
        for(const auto& n:nodes_) if(n.delayActive) nextDue_=std::min(nextDue_,n.due);
    }
    bool converted(Atom a,Atom::Type type,Atom& result) noexcept {
        bool valid=true; result=a.converted(type,valid); if(!valid) fault_=true;return valid;
    }
    // Heavy control cases are outlined so control() itself keeps a small
    // frame: each holds Message/Atom-array locals that only need stack
    // while that case runs. control() sits on every message hop, so its
    // frame size multiplies by the dispatch depth (up to 64).
    __attribute__((noinline)) bool controlDial(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        bool output=true,update=false,raw=false;
        double value=n.values[0];
        bool numericText=false,buttonBang=false;
        const bool text=d.controlKind>=2,button=d.controlKind==3;
        if(m.isNumber()) {
            value=m.atoms[0].number();update=true;numericText=text;
            if(button) {buttonBang=std::trunc(value)!=0;output=buttonBang;}
        }
        else if(m.kind==Message::Kind::bang) {
            if(text) {value=button?1:(value==0?1:0);update=true;numericText=true;buttonBang=button;}
        }
        else if(m.kind==Message::Kind::list) return true;
        else if(m.kind==Message::Kind::symbol || (m.kind==Message::Kind::anything &&
                (m.selector==sym::symbol || symbols_.name(m.selector)=="setsymbol"))) {
            if(m.count!=1 || m.atoms[0].type!=Atom::Type::symbol) return true;
            const auto label=m.atoms[0].value.symbol;
            if(!text && d.parameterLabels.empty())return true;
            auto begin=text?d.textLabels.data():d.parameterLabels.data();
            const auto end=begin+(text?2:d.parameterLabels.size());
            if(begin==end)return true;
            const auto match=std::find(begin,end,label);if(match==end)return true;
            value=double(match-begin);update=true;
            output=m.kind==Message::Kind::symbol || m.selector==sym::symbol;
            buttonBang=button && output && value!=0;
            if(button && value==0)output=false;
        }
        else if(m.kind==Message::Kind::anything) {
            if(m.selector==sym::set || m.selector==sym::assign || m.selector==sym::rawfloat) {
                if(m.count!=1 || !m.atoms[0].numeric()) {fault_=true;return true;}
                value=m.atoms[0].number();update=true;raw=m.selector==sym::rawfloat;output=m.selector!=sym::set;
                numericText=text && !raw && (!button || m.selector==sym::assign);
                if(button && m.selector==sym::assign) {buttonBang=std::trunc(value)!=0;output=buttonBang;}
            } else if(m.selector==sym::init) {value=d.initial;update=true;numericText=text;output=!button;}
            else if(m.selector!=sym::outputvalue) {fault_=true;return true;}
            else buttonBang=button;
        } else {fault_=true;return true;}
        double normalized=d.maximum>d.minimum?std::pow(std::clamp((value-d.minimum)/(d.maximum-d.minimum),0.,1.),1./d.parameterExponent):0;
        if(update) {
            if(raw)normalized=std::clamp(value,0.,1.);
            if(d.parameterSteps>1)normalized=std::round(normalized*(d.parameterSteps-1))/(d.parameterSteps-1);
            n.values[0]=numericText ? (value!=0?1:0) : d.minimum+(d.maximum-d.minimum)*std::pow(normalized,d.parameterExponent);
            if(d.parameterType!=0) {
                n.values[0]=std::clamp(std::round(n.values[0]),d.minimum,d.maximum);
                normalized=d.maximum>d.minimum?std::pow((n.values[0]-d.minimum)/(d.maximum-d.minimum),1./d.parameterExponent):0;
            }
        }
        if(output) {
            if(d.controlKind==1) {
                emitNumber(index,normalized,depth,2);
                emit(index,Message::anything(d.parameterLabels[size_t(n.values[0])]),depth,1);
            } else if(text) {
                const auto label=raw?d.parameterLabels[size_t(n.values[0])]:d.textLabels[button?0:size_t(n.values[0])];
                emit(index,Message::anything(label),depth,1);
            } else emitNumber(index,normalized,depth,1);
            if(buttonBang) {
                emitBang(index,depth);
                // Flash interval MEASURED at ~100 ms (Live, September 11). A
                // press inside the flash re-arms it.
                n.delayActive=true;n.due=sampleTime_+uint64_t(std::ceil(kButtonFlashMs*sampleRate_/1000.));n.serial=serial_++;nextDelay();
            }
            else emit(index,d.parameterType==0?Message::number(n.values[0]):Message::integer(int64_t(n.values[0])),depth);
        }
        return true;
    }
    __attribute__((noinline)) bool controlTrigger(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        for(int outlet=int(d.formats.size())-1;outlet>=0;--outlet) {
            Message out;
            switch(d.formats[outlet]) {
                case Format::bang: break;
                case Format::anything: out=m;break;
                case Format::constant: out=Message::sequence(&d.atoms[outlet],1);break;
                case Format::integer: case Format::floating: {
                    Atom a;
                    if(!converted((m.isNumber() || m.kind==Message::Kind::list) && m.count>0 ? m.atoms[0]:Atom::integral(0),d.formats[outlet]==Format::integer?Atom::Type::integer:Atom::Type::floating,a)) return true;
                    out=Message::single(a);break;
                }
                case Format::symbol:
                    if(m.isNumber()) out=Message::anything(sym::empty);
                    else if(m.kind==Message::Kind::list) {out=m;out.kind=Message::Kind::anything;out.selector=sym::empty;}
                    else out=m;
                    break;
                case Format::list:
                    out=m;break;
            }
            emit(index,out,depth,outlet);
        }
        return true;
        return true;
    }
    __attribute__((noinline)) bool controlUnpack(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Max distributes a list across typed outlets right to left and
        // only for the elements actually received; longer lists ignore
        // the remainder. A lone number behaves as a one-element list.
        if(!m.isNumber() && m.kind!=Message::Kind::list) {fault_=true;return true;}
        const int count=std::min(m.count,int(d.formats.size()));
        for(int outlet=count-1;outlet>=0;--outlet) {
            if(!m.atoms[outlet].numeric()) {fault_=true;return true;}
            Atom a;
            if(!converted(m.atoms[outlet],d.formats[outlet]==Format::integer?Atom::Type::integer:Atom::Type::floating,a)) return true;
            emitSingle(index,a,depth,outlet);
        }
        return true;
    }
    __attribute__((noinline)) bool controlRoute(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        if(inlet==1) {
            if(m.count!=1) {fault_=true;return true;}n.stored[0]=m.atoms[0];return true;
        }
        bool matched=false;
        for(int i=0;i<n.storedCount;++i) {
            const auto key=n.stored[i];bool match=false,keep=false;
            if(key.type==Atom::Type::symbol) {
                if(d.op==Op::route && (key.value.symbol==sym::integer || key.value.symbol==sym::floating || key.value.symbol==sym::list || key.value.symbol==sym::bang || key.value.symbol==sym::symbol)) {
                    match=key.value.symbol==m.selector;keep=true;
                } else if(m.kind==Message::Kind::anything) match=key.value.symbol==m.selector;
                else if(d.op==Op::select && m.kind==Message::Kind::symbol) match=m.count>0 && key.equals(m.atoms[0]);
            } else if(m.isNumber() || m.kind==Message::Kind::list) match=m.count>0 && key.equals(m.atoms[0]);
            if(match) {
                Message out;
                if(d.op==Op::route) {
                    if(keep) out=m.kind==Message::Kind::symbol ? Message::sequence(m.atoms.data(),m.count):m;
                    else if(m.kind==Message::Kind::anything) out=Message::sequence(m.atoms.data(),m.count);
                    else out=Message::sequence(m.atoms.data()+1,m.count-1);
                }
                emit(index,out,depth,i);matched=true;if(d.op==Op::select)return true;
            }
        }
        if(!matched)emit(index,m,depth,n.storedCount);return true;
        return true;
    }
    __attribute__((noinline)) bool controlPrependAppend(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        if(d.op==Op::append && m.kind==Message::Kind::bang)return true;
        if(m.kind==Message::Kind::anything && m.selector==sym::set) {
            n.storedCount=m.count;std::copy(m.atoms.begin(),m.atoms.begin()+m.count,n.stored.begin());return true;
        }
        std::array<Atom,Message::capacity> data{};int length=m.dataAtoms(data.data());
        if(m.kind==Message::Kind::bang) {length=1;data[0]=Atom::named(sym::bang);}
        if(length<0 || length+n.storedCount>Message::capacity) {fault_=true;return true;}
        std::array<Atom,Message::capacity> values{};
        if(d.op==Op::prepend) {
            std::copy(n.stored.begin(),n.stored.begin()+n.storedCount,values.begin());std::copy(data.begin(),data.begin()+length,values.begin()+n.storedCount);
        } else {
            std::copy(data.begin(),data.begin()+length,values.begin());std::copy(n.stored.begin(),n.stored.begin()+n.storedCount,values.begin()+length);
        }
        emitSequence(index,values.data(),length+n.storedCount,depth);return true;
        return true;
    }
    __attribute__((noinline)) bool controlMessage(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        const bool set=inlet==0 && m.kind==Message::Kind::anything && m.selector==sym::set;
        const bool append=inlet==0 && m.kind==Message::Kind::anything && m.selector==sym::append;
        const bool prepend=inlet==0 && m.kind==Message::Kind::anything && m.selector==sym::prepend;
        const bool setargs=inlet==0 && m.kind==Message::Kind::anything && m.selector==sym::setargs;
        if(inlet==1 || set || append || prepend) {
            std::array<Atom,Message::capacity> data{};
            int count=m.dataAtoms(data.data());
            if(set || append || prepend) {count=m.count;std::copy(m.atoms.begin(),m.atoms.begin()+count,data.begin());}
            else if(m.kind==Message::Kind::bang) {count=1;data[0]=Atom::named(sym::bang);}
            else if(m.kind==Message::Kind::symbol) {count=2;data[0]=Atom::named(sym::symbol);data[1]=m.atoms[0];}
            const int retained=append || prepend ? n.storedCount:0;
            if(count<0 || count+retained>Message::capacity) {fault_=true;return true;}
            if(prepend)for(int i=n.storedCount-1;i>=0;--i) {
                n.stored[i+count]=n.stored[i];n.substitutions[i+count]=n.substitutions[i];n.separators[i+count]=n.separators[i];
            }
            const int offset=append?n.storedCount:0;
            for(int i=0;i<count;++i) {
                const int position=offset+i;const auto a=data[i];
                n.stored[position]=a;n.substitutions[position]=-1;n.separators[position]=0;
                if(a.type==Atom::Type::symbol) {
                    n.substitutions[position]=symbols_.substitution(a.value.symbol);
                    if(n.substitutions[position]>=0)n.stored[position]=Atom::integral(0);
                    if(a.value.symbol==sym::comma)n.separators[position]=1;
                    if(a.value.symbol==sym::semicolon)n.separators[position]=2;
                }
            }
            n.storedCount=count+retained;
            return true;
        }
        auto result=n.stored;
        if(m.kind!=Message::Kind::bang) {
            std::array<Atom,Message::capacity> data{};int length=m.dataAtoms(data.data());
            if(setargs) {length=m.count;std::copy(m.atoms.begin(),m.atoms.begin()+length,data.begin());}
            if(length<0) {fault_=true;return true;}
            for(int i=0;i<n.storedCount;++i) if(n.substitutions[i]>=0 && n.substitutions[i]<length)result[i]=data[n.substitutions[i]];
            n.stored=result;
        }
        if(setargs)return true;
        // Freeze this dispatch's contents: downstream cold-inlet edits
        // must not replace the remaining clauses while they are sent.
        const auto separators=n.separators;const int count=n.storedCount;
        bool named=false,needsTarget=false;Symbol target=sym::empty;int begin=0;
        for(int end=0;end<=count && !fault_;++end)if(end==count || separators[end]) {
            if(end>begin && needsTarget) {
                if(result[begin].type!=Atom::Type::symbol) {fault_=true;return true;}
                target=result[begin++].value.symbol;needsTarget=false;
            }
            if(end>begin) {
                auto out=Message::sequence(result.data()+begin,end-begin);
                if(out.kind==Message::Kind::list && out.count==0) {}
                else {
                    if(out.kind==Message::Kind::anything && (out.selector==sym::integer || out.selector==sym::floating)) {
                        if(out.count!=1 || !out.atoms[0].numeric()) {fault_=true;return true;}
                        Atom value;if(!converted(out.atoms[0],out.selector==sym::integer?Atom::Type::integer:Atom::Type::floating,value))return true;
                        out=Message::single(value);
                    }
                    if(named) {
                        if(symbols_.name(target)=="max" || !routing_->broadcast(routingMember_,target,out,depth,dispatchBudget_))fault_=true;
                    } else emit(index,out,depth);
                }
            }
            if(end<count && separators[end]==2) {named=true;needsTarget=true;}
            begin=end+1;
        }
        return true;
    }
    __attribute__((noinline)) bool controlTransport(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Measured in Live 12.4.5 (bare transport, banged, 120 BPM):
        //   0 bars 1-based, 1 beat in bar 1-based, 2 ticks in beat 0..480,
        //   3 480 ticks per beat, 4 tempo, 6 running, 7 total elapsed TICKS
        //   (not ms). MEASURED September 11 (playing, 132 BPM, 4/4): outlet 5
        //   is the time signature as a list ('4 4'); outlet 8 emits nothing on
        //   a bang. Bars and the signature assume 4/4 — the host has no meter.
        if(inlet!=0 || m.kind!=Message::Kind::bang) {fault_=true;return true;}
        const bool playing=transportPlaying_.load(std::memory_order_acquire);
        const double tempo=transportTempo_.load(std::memory_order_relaxed),beat=transportBeat_.load(std::memory_order_relaxed);
        const double whole=std::floor(beat);
        emitNumber(index,beat*480.,depth,7);
        emitSingle(index,Atom::integral(playing?1:0),depth,6);
        {Atom signature[2]={Atom::integral(4),Atom::integral(4)};emitSequence(index,signature,2,depth,5);}
        emitNumber(index,tempo,depth,4);
        emitNumber(index,480.,depth,3);
        emitNumber(index,(beat-whole)*480.,depth,2);
        emitSingle(index,Atom::integral(int64_t(std::fmod(whole,4.))+1),depth,1);
        emitSingle(index,Atom::integral(int64_t(whole/4.)+1),depth,0);
        return true;
    }
    __attribute__((noinline)) bool controlSpray(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // [index value ...]: the first atom minus the offset selects the
        // outlet, the remaining atoms are sent there. An index outside
        // the outlet range is dropped silently, as in Max.
        if(m.kind!=Message::Kind::list || m.count<2 || !m.atoms[0].numeric()) {fault_=true;return true;}
        Atom slot;if(!converted(m.atoms[0],Atom::Type::integer,slot))return true;
        const int64_t outlet=slot.value.integer-int64_t(d.arguments[1]);
        if(outlet<0 || outlet>=int64_t(d.arguments[0]))return true;
        emitSequence(index,&m.atoms[1],m.count-1,depth,int(outlet));
        return true;
    }
    __attribute__((noinline)) bool controlLiveRemote(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Right inlet: 'id <n>'. id 0 releases and reports 'mapped 0'
        // when a mapping was held (reporting on change only is NOT
        // measured). A non-zero id is forwarded to the host, which
        // decides whether the target exists in this session. The left
        // inlet carries the normalized controlling value. The owning session
        // installs the target and consumes the render-owned signal sample;
        // while unmapped the value remains inert.
        if(inlet==1) {
            if(m.kind!=Message::Kind::anything || symbols_.name(m.selector)!="id" || m.count!=1 || !m.atoms[0].numeric()) {fault_=true;return true;}
            Atom target;if(!converted(m.atoms[0],Atom::Type::integer,target))return true;
            if(target.value.integer==0) {
                if(n.hasHeld) {n.hasHeld=false;Message out=Message::anything(mappedSymbol_);out.count=1;out.atoms[0]=Atom::integral(0);emit(index,out,depth,0);}
                return true;
            }
            queueExternal(index,inlet,m);return true;
        }
        if(!m.isNumber() && m.kind!=Message::Kind::floating) {fault_=true;return true;}
        return true;
    }
    __attribute__((noinline)) bool controlModalExternal(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Same message surface as modal_max.cpp: an int is a raw MIDI
        // byte; param/model/note/mpe/panic drive the engine. capture and
        // analyze need a buffer/thread host and report a status instead.
        auto& engine=*n.modal;
        auto number=[&](int i){return i<m.count?m.atoms[size_t(i)].number():0.;};
        if(m.kind==Message::Kind::integer) {engine.midi(int(m.atoms[0].value.integer));return true;}
        if(m.kind!=Message::Kind::anything) {fault_=true;return true;}
        const auto& sel=symbols_.name(m.selector);
        if(sel=="param" && m.count==2) engine.set(int(number(0)),number(1));
        else if(sel=="note" && m.count>=2) engine.note(int(number(0)),int(number(1)),m.count>2?int(number(2)):1);
        else if(sel=="mpe" && m.count==1) engine.mpe=number(0)!=0;
        else if(sel=="panic") engine.clear();
        else if(sel=="model" && m.count==6+m4l::modal::modes*5) {
            m4l::modal::Model model;model.anchor=number(1);model.attack=number(2);model.noise=number(3);model.confidence=number(4);model.count=int(number(5));
            for(int i=0;i<m4l::modal::modes;++i) model.mode[i]={number(6+i*5),number(7+i*5),number(8+i*5),number(9+i*5),number(10+i*5)};
            const int slot=int(number(0));
            if(slot>=0 && slot<2 && model.valid()) engine.setModel(slot,model);
            else {fault_=true;return true;}
        }
        else if(sel=="capture" || sel=="analyze") {
            // Not hosted: report through the status outlet like the
            // external does, rather than dropping the request silently.
            Message out=Message::anything(modalStatus_);out.count=2;out.atoms[0]=Atom::integral(int64_t(number(sel=="capture"?0:1)));
            out.atoms[1]=Atom::named(modalUnsupported_);emit(index,out,depth,2);
        }
        else {fault_=true;return true;}
        return true;
    }
    __attribute__((noinline)) bool controlUzi(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Fires count times: per iteration the index (outlet 2) then a
        // bang (outlet 0), right to left; a bang on outlet 1 when done.
        // Index starts at the offset (1 by default). An int at the left
        // inlet sets the count and fires; the right inlet only sets.
        // pause/resume/break are not modelled. Each iteration costs
        // dispatch budget, which bounds runaway counts.
        if(inlet==1) {
            if(!m.isNumber()) {fault_=true;return true;}
            Atom v;if(!converted(m.atoms[0],Atom::Type::integer,v))return true;
            if(v.value.integer<0) {fault_=true;return true;}n.stored[0]=v;return true;
        }
        if(m.isNumber()) {Atom v;if(!converted(m.atoms[0],Atom::Type::integer,v))return true;if(v.value.integer<0) {fault_=true;return true;}n.stored[0]=v;}
        else if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
        const int64_t count=n.stored[0].value.integer,offset=n.stored[1].value.integer;
        for(int64_t i=0;i<count && !fault_;++i) {
            emitSingle(index,Atom::integral(offset+i),depth,2);
            emitBang(index,depth,0);
        }
        if(!fault_)emitBang(index,depth,1);
        return true;
    }
    // sprintf: store the incoming atoms into their slots (a list in the left
    // inlet spreads left to right), then on a left-inlet message format each
    // token and emit the re-parsed atoms. Float conversions are rendered with
    // snprintf and parsed back so "%.2f" of 0.5 emits the float 0.5, and
    // "%.0f" of 12.4 emits the int 12, as Max's re-parse does. Whether a
    // live.comment then shows "0.5" or "0.50" is a host text-formatting
    // question, NOT measured in Live yet (labelled in phren).
    __attribute__((noinline)) bool controlSprintf(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;
        const int slots=std::max(1,sprintfConversions(d));
        if(inlet<0 || inlet>=slots) {fault_=true;return true;}
        if(m.kind!=Message::Kind::bang) {
            std::array<Atom,Message::capacity> atoms{};const int count=m.dataAtoms(atoms.data());
            if(count<0) {fault_=true;return true;}
            int slot=inlet;
            for(int i=0;i<count && slot<slots;++i,++slot)n.stored[size_t(slot)]=atoms[size_t(i)];
            if(inlet!=0)return true;
        }
        std::array<Atom,Message::capacity> out{};int produced=0,slot=0;
        for(size_t i=0;i<d.atoms.size();++i) {
            const int code=int(d.arguments[i]);
            if(code==0) {out[size_t(produced++)]=d.atoms[i];continue;}
            const Atom value=n.stored[size_t(slot++)];
            if(code==2) {out[size_t(produced++)]=value;continue;} // %s: symbols pass, numbers re-parse to numbers
            if(value.type==Atom::Type::symbol) {fault_=true;return true;} // %d/%f of a symbol: Max prints 0? unmeasured, refuse
            if(code==1) {
                const double v=std::trunc(value.number());
                if(!std::isfinite(v) || std::abs(v)>=9223372036854775808.) {fault_=true;return true;}
                out[size_t(produced++)]=Atom::integral(int64_t(v));continue;
            }
            const int precision=code-3;
            char text[64];
            if(!std::isfinite(value.number())) {fault_=true;return true;} // "inf"/"nan" would be transient symbols
            const int written=std::snprintf(text,sizeof(text),"%.*f",precision,value.number());
            if(written<=0 || written>=int(sizeof(text))) {fault_=true;return true;}
            if(precision==0) out[size_t(produced++)]=Atom::integral(int64_t(std::strtoll(text,nullptr,10)));
            else out[size_t(produced++)]=Atom::real(std::strtod(text,nullptr));
        }
        emitSequence(index,out.data(),produced,depth,0);
        return true;
    }
    // metro: interval in ms, or a note value (values[1]!=0) whose length in
    // beats is arguments[0]. Note-value metros follow the session transport:
    // they fire only while it plays (MEASURED in Live 12.4.5: zero bangs over
    // 6 s stopped, continuous while playing; September 11: metro 4n at 120 BPM
    // ticks every ~500 ms, one quarter note, and emits nothing stopped). The
    // beat-grid phase of the first tick is not measured.
    uint64_t metroNextDue(const Node& n) const noexcept {
        if(n.values[1]==0) return sampleTime_+std::max<uint64_t>(1,uint64_t(std::llround(n.time*sampleRate_/1000.)));
        const double tempo=transportTempo_.load(std::memory_order_relaxed),beat=transportBeat_.load(std::memory_order_relaxed);
        const double step=n.time; const double next=(std::floor(beat/step+1e-9)+1)*step;
        const double samples=(next-beat)*60./std::max(1.,tempo)*sampleRate_;
        return sampleTime_+std::max<uint64_t>(1,uint64_t(std::ceil(samples)));
    }
    void armMetro(Node& n,uint64_t due) noexcept {n.delayActive=true;n.due=due;n.serial=serial_++;nextDelay();}
    static bool noteValueBeats(const std::string& name,double& beats) noexcept {
        struct Entry {const char* name;double beats;};
        static const Entry table[]={{"1n",4},{"2n",2},{"4n",1},{"8n",0.5},{"16n",0.25},{"32n",0.125},{"64n",0.0625},{"128n",0.03125},
            {"2nd",3},{"4nd",1.5},{"8nd",0.75},{"16nd",0.375},{"32nd",0.1875},{"2nt",4./3},{"4nt",2./3},{"8nt",1./3},{"16nt",1./6},{"32nt",1./12}};
        for(const auto& e:table) if(name==e.name) {beats=e.beats;return true;}
        return false;
    }
    __attribute__((noinline)) bool controlMetro(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index];(void)depth;
        if(inlet==1) {
            if(m.isNumber()) {const double ms=m.atoms[0].number();if(!(ms>0) || ms>3600000) {fault_=true;return true;}n.time=ms;n.values[1]=0;return true;}
            if(m.kind==Message::Kind::anything && m.count==0) {double beats;if(!noteValueBeats(symbols_.name(m.selector),beats)) {fault_=true;return true;}n.time=beats;n.values[1]=1;return true;}
            fault_=true;return true;
        }
        bool stop=false;
        if(m.kind==Message::Kind::bang) {}
        else if(m.isNumber()) stop=m.atoms[0].number()==0;
        else if(m.kind==Message::Kind::anything && m.count==0) {const auto& sel=symbols_.name(m.selector);if(sel=="stop")stop=true;else {fault_=true;return true;}}
        else {fault_=true;return true;}
        if(stop) {n.delayActive=false;n.values[2]=0;nextDelay();return true;}
        n.values[2]=1;
        if(n.values[1]==0) {emitBang(index,depth,0);armMetro(n,metroNextDue(n));}
        else armMetro(n,transportPlaying_.load(std::memory_order_acquire)?metroNextDue(n):sampleTime_+64);
        return true;
    }
    __attribute__((noinline)) bool controlPipe(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index];const auto& d=n.definition;(void)depth;
        if(inlet==1) {if(!m.isNumber()) {fault_=true;return true;}const double ms=m.atoms[0].number();if(ms<0 || ms>3600000) {fault_=true;return true;}n.time=ms;return true;}
        Atom value;
        if(m.isNumber()) {if(!converted(m.atoms[0],d.atoms.empty() || d.atoms[0].type==Atom::Type::integer?Atom::Type::integer:Atom::Type::floating,value))return true;n.stored[0]=value;}
        else if(m.kind==Message::Kind::bang) value=n.stored[0];
        else {fault_=true;return true;}
        // Queue (value, due) pairs from slot 2 on; slot 0 remembers the last value.
        if(n.storedCount<2)n.storedCount=2;
        if(n.storedCount+2>int(Message::capacity)) {fault_=true;return true;}
        const uint64_t due=sampleTime_+uint64_t(std::ceil(n.time*sampleRate_/1000.));
        n.stored[size_t(n.storedCount++)]=value;n.stored[size_t(n.storedCount++)]=Atom::integral(int64_t(due));
        if(!n.delayActive || due<n.due)armMetro(n,due);
        return true;
    }
    // Fires the earliest queued pipe value; called from the due dispatch.
    void firePipe(int index) noexcept {
        auto& n=nodes_[index];
        int best=-1;for(int i=2;i+1<n.storedCount;i+=2) if(best<0 || n.stored[size_t(i)+1].value.integer<n.stored[size_t(best)+1].value.integer)best=i;
        if(best<0)return;
        const Atom value=n.stored[size_t(best)];
        for(int i=best;i+2<n.storedCount;++i)n.stored[size_t(i)]=n.stored[size_t(i)+2];
        n.storedCount-=2;
        emitSingle(index,value,0,0);
        int next=-1;for(int i=2;i+1<n.storedCount;i+=2) if(next<0 || n.stored[size_t(i)+1].value.integer<n.stored[size_t(next)+1].value.integer)next=i;
        if(next>=0)armMetro(n,uint64_t(n.stored[size_t(next)+1].value.integer));
    }
    __attribute__((noinline)) bool controlColl(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index];(void)inlet;
        auto find=[&](int64_t key)->int {for(int i=0;i<n.entryCount;++i)if(n.entries[size_t(i)].index==key)return i;return -1;};
        auto emitEntry=[&](const Node::CollEntry& e) {
            emitInteger(index,e.index,depth,1);
            // Refpage: a stored single symbol is output as "symbol <name>".
            if(e.count==1 && e.atoms[0].type==Atom::Type::symbol) {Message out=Message::anything(sym::symbol);out.count=1;out.atoms[0]=e.atoms[0];emit(index,out,depth,0);}
            else emitSequence(index,e.atoms.data(),e.count,depth,0);
        };
        if(m.kind==Message::Kind::bang) {fault_=true;return true;}   // 'next' semantics not modelled
        if(m.isNumber()) {
            const int at=find(int64_t(std::trunc(m.atoms[0].number())));
            if(at>=0)emitEntry(n.entries[size_t(at)]);   // a missing address: the refpage is silent; nothing is output (unmeasured)
            return true;
        }
        if(m.kind==Message::Kind::list) {
            // "index data...": store (replace) at that integer index, no output.
            if(m.count<2 || !m.atoms[0].numeric() || m.count-1>32) {faultBecause("coll list store needs a numeric address and 1..32 atoms");return true;}
            const int64_t key=int64_t(std::trunc(m.atoms[0].number()));
            int at=find(key);
            if(at<0) {if(n.entryCount>=int(n.entries.size())) {fault_=true;return true;}at=n.entryCount++;n.entries[size_t(at)].index=key;}
            auto& e=n.entries[size_t(at)];e.count=m.count-1;std::copy(m.atoms.begin()+1,m.atoms.begin()+m.count,e.atoms.begin());
            return true;
        }
        if(m.kind!=Message::Kind::anything) {fault_=true;return true;}
        const auto& sel=symbols_.name(m.selector);
        if(sel=="clear" && m.count==0) {n.entryCount=0;return true;}
        if(sel=="remove" && m.count==1 && m.atoms[0].numeric()) {
            const int at=find(int64_t(std::trunc(m.atoms[0].number())));
            if(at>=0) {for(int i=at;i+1<n.entryCount;++i)n.entries[size_t(i)]=n.entries[size_t(i)+1];--n.entryCount;}
            return true;
        }
        if(sel=="dump" && m.count==0) {
            // Max 9 refpage: addresses out outlet 1 and messages out outlet 0
            // "in the order in which they are stored", then a bang on outlet
            // 3 (the 4th) when the dump completes.
            for(int i=0;i<n.entryCount && !fault_;++i)emitEntry(n.entries[size_t(i)]);
            emitBang(index,depth,3);return true;
        }
        if(sel=="store" && m.count>=2 && m.atoms[0].numeric()) {
            Message list=Message::sequence(m.atoms.data(),m.count);return controlColl(index,inlet,list,depth);
        }
        fault_=true;return true;   // read/write/sort/next/nth etc. need support
    }
    __attribute__((noinline)) bool controlListFunnel(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Emits one [index value] list per element, first to last, with
        // the optional offset added to the index. MEASURED in Live 12.4.5
        // (max4liveplugins batch4 probe): 10 20 30 -> (0 10) (1 20) (2 30),
        // 0-based, left to right.
        std::array<Atom,Message::capacity> atoms{};const int count=m.dataAtoms(atoms.data());
        if(count<0) {fault_=true;return true;}
        const int64_t offset=d.arguments.empty()?0:int64_t(d.arguments[0]);
        for(int i=0;i<count && !fault_;++i) {
            Atom pair[2]={Atom::integral(offset+i),atoms[size_t(i)]};
            emitSequence(index,pair,2,depth,0);
        }
        return true;
    }
    __attribute__((noinline)) bool controlZlGroup(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;(void)n;(void)d;(void)inlet;
        // Collects incoming atoms and outputs a list once the group size
        // is reached; bang flushes whatever is collected. Right inlet
        // sets the size. MEASURED in Live 12.4.5: a partial group (2 of 3)
        // flushes on bang as a 2-element list. Behaviour on a new size
        // message while partially filled is still unmeasured.
        if(inlet==1) {
            if(!m.isNumber()) {fault_=true;return true;}
            Atom v;if(!converted(m.atoms[0],Atom::Type::integer,v))return true;
            if(v.value.integer<1 || v.value.integer>Message::capacity) {fault_=true;return true;}
            n.stored[0]=v;return true;
        }
        // stored[0] is the group size; stored[1..] are the collected atoms.
        const int size=int(n.stored[0].value.integer);
        if(m.kind==Message::Kind::bang) {
            if(n.storedCount>1) {emitSequence(index,&n.stored[1],n.storedCount-1,depth,0);n.storedCount=1;}
            return true;
        }
        std::array<Atom,Message::capacity> atoms{};const int count=m.dataAtoms(atoms.data());
        if(count<0) {fault_=true;return true;}
        for(int i=0;i<count;++i) {
            if(n.storedCount>=int(Message::capacity)) {fault_=true;return true;}
            n.stored[size_t(n.storedCount++)]=atoms[size_t(i)];
            if(n.storedCount-1>=size) {emitSequence(index,&n.stored[1],n.storedCount-1,depth,0);n.storedCount=1;}
        }
        return true;
    }
    bool control(int index,int inlet,const Message& m,int depth) noexcept {
        auto& n=nodes_[index]; const auto& d=n.definition;
        if(d.presentation && m.kind==Message::Kind::anything) {
            const auto& selector=symbols_.name(m.selector);
            if(selector.size()>=5 && selector.compare(selector.size()-5,5,"color")==0) {
                queueExternal(index,inlet,m);return true;
            }
            // 'set <text>' replaces a comment's displayed text; the host owns
            // the string, so it travels the same control queue as colours.
            if(d.op==Op::decoration && m.selector==sym::set) {queueExternal(index,inlet,m);return true;}
            // 'active 0/1' greys a control out (host-drawn state, no output).
            if(selector=="active" && m.count==1 && m.atoms[0].numeric()) {queueExternal(index,inlet,m);return true;}
        }
        switch(d.op) {
            case Op::expression: {
                Atom result;bool produced=false;
                if(!n.expression->receive(inlet,m,result,produced))fault_=true;
                else if(produced)emitSingle(index,result,depth);
                return true;
            }
            case Op::conditional: {
                Atom result;bool produced=false;
                if(!n.expression->receive(inlet,m,result,produced)) {fault_=true;return true;}
                if(!produced)return true;
                const bool truth=result.number()!=0;
                if(truth)emitSingle(index,d.integers.size()>0 && d.integers[0]?Atom::integral(int64_t(d.arguments[1])):Atom::real(d.arguments[1]),depth);
                else if(d.arguments[2]!=0)emitSingle(index,d.integers.size()>1 && d.integers[1]?Atom::integral(int64_t(d.arguments[3])):Atom::real(d.arguments[3]),depth);
                return true;
            }
            case Op::dspState:
                if(m.kind==Message::Kind::bang)
                    n.dspState->bang([&](int outlet,const Message& value){emit(index,value,depth,outlet);});
                else fault_=true;
                return true;
            case Op::signalRecord:
                if(inlet!=0) {fault_=true;return true;}
                if(m.isNumber())n.recorder->record(m.atoms[0].number());
                else if(m.kind==Message::Kind::anything) {
                    const auto& name=symbols_.name(m.selector);
                    if(m.count==1 && m.atoms[0].numeric() && (name=="loop" || name=="append")) {
                        const bool enabled=std::trunc(m.atoms[0].number())!=0;
                        if(name=="loop")n.recorder->loop(enabled);else n.recorder->append(enabled);
                    } else if(name=="reset" && m.count==0)n.recorder->reset();
                    else fault_=true; // Dynamic bindings/ranges need vector ownership transactions.
                } else fault_=true;
                return true;
            case Op::signalSnapshot:
                if(m.kind==Message::Kind::bang && inlet==0)emitNumber(index,n.snapshot->bang(audioDispatch_,int(sampleTime_%64)),depth);
                else if(m.isNumber()) {
                    if(inlet==0)n.snapshot->active(std::trunc(m.atoms[0].number())!=0);
                    else if(!n.snapshot->interval(m.atoms[0].number()))fault_=true;
                } else if(m.kind==Message::Kind::anything) {
                    const auto& name=symbols_.name(m.selector);
                    if(m.count==0 && (name=="start" || name=="stop"))n.snapshot->active(name=="start");
                    else if(m.count==1 && m.atoms[0].numeric()) {
                        const auto value=m.atoms[0].number();
                        if(name=="interval") {if(!n.snapshot->interval(value))fault_=true;}
                        else if(name=="sampleinterval") {if(!n.snapshot->sampleInterval(std::trunc(value)))fault_=true;}
                        else if(name=="active")n.snapshot->active(std::trunc(value)!=0);
                        else if(name=="offset")n.snapshot->offset(value);
                        else fault_=true;
                    } else fault_=true;
                } else fault_=true;
                return true;
            case Op::signalSelector:
                if(inlet!=0) {
                    if(m.isNumber())n.values[inlet]=m.atoms[0].number();else fault_=true;
                } else if(m.isNumber())n.selector->select(m.atoms[0].number(),sampleTime_!=0);
                else if(m.kind==Message::Kind::bang)n.selector->next(sampleTime_!=0);
                else if(m.kind==Message::Kind::anything) {
                    const auto& name=symbols_.name(m.selector);
                    if(name=="next" && m.count==0)n.selector->next(sampleTime_!=0);
                    else if((name=="ramp" || name=="ramptime") && m.count==1 && m.atoms[0].numeric()) {
                        if(!n.selector->ramp(m.atoms[0].number()))fault_=true;
                    } else if(name=="stepmode" && m.count==1 && m.atoms[0].numeric())n.selector->step(std::trunc(m.atoms[0].number())!=0);
                    else fault_=true;
                } else fault_=true;
                return true;
            case Op::buffer: {
                auto& table=*routing_->buffers().at(symbols_.name(d.atoms[0].value.symbol));
                if(m.kind==Message::Kind::anything && symbols_.name(m.selector)=="clear" && m.count==0)table.clear();
                else if(!initialized_ && m.kind==Message::Kind::anything && symbols_.name(m.selector)=="fill" && m.count==1 && m.atoms[0].numeric()) {
                    if(!fillPreparedBuffer(table,m.atoms[0].number()))fault_=true;
                } else if(!initialized_ && m.kind==Message::Kind::anything && symbols_.name(m.selector)=="apply" && m.count==1 && m.atoms[0].type==Atom::Type::symbol && symbols_.name(m.atoms[0].value.symbol)=="hanning") {
                    hanningPreparedBuffer(table);
                } else if(m.kind==Message::Kind::anything && symbols_.name(m.selector)=="sizeinsamps" && m.count==1 && m.atoms[0].numeric()) {
                    // The compiler folds a static sizeinsamps into the
                    // declaration (then this is a no-op); otherwise the table
                    // resizes within its reserved words, keeping its channel
                    // count (1 when still unallocated, as Max does).
                    const double frames=std::trunc(m.atoms[0].number());
                    if(frames<0 || frames>4194304)fault_=true;
                    else if(frames!=double(table.frames()) || table.channels()==0) {
                        if(!table.resize(size_t(frames),std::max<size_t>(1,table.channels())))fault_=true;
                    }
                } else if(m.kind==Message::Kind::anything && m.count>=1 && m.atoms[0].type==Atom::Type::symbol &&
                          (symbols_.name(m.selector)=="replace" || symbols_.name(m.selector)=="read" || symbols_.name(m.selector)=="import")) {
                    // File loading is a host transaction (decode, resize, fill,
                    // then the left outlet bangs); an unresolvable path is Max's
                    // "buffer~: can't open" console error, not a stop.
                    queueExternal(index,inlet,m);
                } else fault_=true; // Live transforms and other file messages require host transactions.
                return true;
            }
            case Op::external: queueExternal(index,inlet,m); return true;
            case Op::namedSend:
                if(!routing_->broadcast(routingMember_,d.atoms[0].value.symbol,m,depth,dispatchBudget_))fault_=true;
                return true;
            case Op::gen:
                if(m.isNumber())n.values[inlet]=m.atoms[0].number();
                else if(m.kind==Message::Kind::anything) {
                    const auto& name=symbols_.name(m.selector);
                    if(name=="reset" && m.count==0)n.gen->reset();
                    else if(m.count==1 && m.atoms[0].type==Atom::Type::symbol) {
                        if(!n.gen->bindBuffer(name,symbols_.name(m.atoms[0].value.symbol)))fault_=true;
                    } else if(m.count!=1 || !m.atoms[0].numeric() || !n.gen->set(name,m.atoms[0].number()))fault_=true;
                } else fault_=true;
                return true;
            case Op::dial: return controlDial(index,inlet,m,depth);
            case Op::boundary: emit(index,m,depth);return true;
            case Op::trigger: return controlTrigger(index,inlet,m,depth);
            case Op::unpack: return controlUnpack(index,inlet,m,depth);
            case Op::route: case Op::select: return controlRoute(index,inlet,m,depth);
            case Op::prepend: case Op::append: return controlPrependAppend(index,inlet,m,depth);
            case Op::integer: case Op::floating: {
                // MEASURED (Live, September 11): a list '3 4' stores and outputs
                // its first element; a symbol posts an error and emits nothing.
                const bool set=m.kind==Message::Kind::anything && m.selector==sym::set;
                if(m.kind==Message::Kind::anything && !set)return true;
                if(m.kind==Message::Kind::symbol)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!(m.isNumber() || m.kind==Message::Kind::list || set) || m.count==0 || !m.atoms[0].numeric()) {fault_=true;return true;}
                    if(!converted(m.atoms[0],d.op==Op::integer?Atom::Type::integer:Atom::Type::floating,n.stored[0])) return true;
                }
                if(inlet==0 && !set) emitSingle(index,n.stored[0],depth);return true;
            }
            case Op::loadbang: emitBang(index,depth);return true;
            case Op::loadmess: emitSequence(index,n.stored.data(),n.storedCount,depth);return true;
            case Op::message: return controlMessage(index,inlet,m,depth);
            case Op::deferlow: {
                const auto next=(deferredWrite_+1)%deferred_.size();
                if(next==deferredRead_) {fault_=true;return true;}
                deferred_[deferredWrite_]={index,m};deferredWrite_=unsigned(next);
                deferredPending_.store(true,std::memory_order_release);return true;
            }
            case Op::delay:
                if(m.kind==Message::Kind::anything && m.selector==sym::stop && inlet==0) {n.delayActive=false;nextDelay();return true;}
                if(m.kind==Message::Kind::anything || m.kind==Message::Kind::symbol) {
                    // Refpage: any other message is a time in a Max time format
                    // (a note value sets the delay time and does not bang).
                    // Anything else is Max's "bad time" console error: ignored
                    // (Shard sends 'analyze' into a [del] and Live carries on).
                    const int at=m.kind==Message::Kind::symbol?0:-1;
                    const std::string& text=at==0?symbols_.name(m.atoms[0].value.symbol):symbols_.name(m.selector);
                    double beats=0;
                    if(m.count==(at==0?1:0) && noteValueBeats(text,beats)) n.time=beats*60000./std::max(1.,transportTempo_.load(std::memory_order_relaxed));
                    return true;
                }
                if(m.isNumber()) n.time=std::max(0.,m.atoms[0].number());
                else if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                if(n.time>3600000.) {fault_=true;return true;}
                if(inlet==0) {n.delayActive=true;n.due=sampleTime_+uint64_t(std::ceil(n.time*sampleRate_/1000.));n.serial=serial_++;nextDelay();}
                return true;
            case Op::controlAdd: case Op::controlSubtract: case Op::controlMultiply: case Op::controlDivide: case Op::reverseSubtract: {
                if(m.kind==Message::Kind::list)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!m.numeric() || m.count<1 || m.count>2-inlet) {fault_=true;return true;}
                    for(int i=0;i<m.count;++i) if(!converted(m.atoms[i],n.stored[1].type,n.stored[inlet+i])) return true;
                }
                if(inlet==0) {
                    if(n.stored[1].type==Atom::Type::integer) {
                        const int64_t a=n.stored[0].value.integer,b=n.stored[1].value.integer;int64_t result=0;bool overflow=false;
                        if(d.op==Op::controlAdd) overflow=__builtin_add_overflow(a,b,&result);
                        if(d.op==Op::controlSubtract) overflow=__builtin_sub_overflow(a,b,&result);
                        if(d.op==Op::reverseSubtract) overflow=__builtin_sub_overflow(b,a,&result);
                        if(d.op==Op::controlMultiply) overflow=__builtin_mul_overflow(a,b,&result);
                        if(d.op==Op::controlDivide) {
                            if(a==INT64_MIN && b== -1) overflow=true;
                            else result=b==0?a:a/b;
                        }
                        if(overflow) {fault_=true;return true;}
                        emitInteger(index,result,depth);return true;
                    }
                    const double a=n.stored[0].number(),b=n.stored[1].number();double result=0;
                    if(d.op==Op::controlAdd) result=a+b;
                    if(d.op==Op::controlSubtract) result=a-b;
                    if(d.op==Op::reverseSubtract) result=b-a;
                    if(d.op==Op::controlMultiply) result=a*b;
                    if(d.op==Op::controlDivide) result=b==0?a:a/b;
                    Atom out;if(!converted(Atom::real(result),n.stored[1].type,out))return true;
                    emitSingle(index,out,depth);
                }
                return true;
            }
            case Op::compareEqual: case Op::compareUnequal: case Op::compareGreater: case Op::compareLess: case Op::compareGreaterEqual: case Op::compareLessEqual: {
                // Same inlet discipline as the arithmetic family: the argument
                // fixes int-versus-float comparison, the right inlet is cold,
                // and the result is always an int 0/1.
                if(m.kind==Message::Kind::list)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!m.numeric() || m.count<1 || m.count>2-inlet) {fault_=true;return true;}
                    for(int i=0;i<m.count;++i) if(!converted(m.atoms[i],n.stored[1].type,n.stored[inlet+i])) return true;
                }
                if(inlet==0) {
                    bool r=false;
                    if(n.stored[1].type==Atom::Type::integer) {
                        const int64_t a=n.stored[0].value.integer,b=n.stored[1].value.integer;
                        switch(d.op){case Op::compareEqual:r=a==b;break;case Op::compareUnequal:r=a!=b;break;case Op::compareGreater:r=a>b;break;
                            case Op::compareLess:r=a<b;break;case Op::compareGreaterEqual:r=a>=b;break;default:r=a<=b;}
                    } else {
                        const double a=n.stored[0].number(),b=n.stored[1].number();
                        switch(d.op){case Op::compareEqual:r=a==b;break;case Op::compareUnequal:r=a!=b;break;case Op::compareGreater:r=a>b;break;
                            case Op::compareLess:r=a<b;break;case Op::compareGreaterEqual:r=a>=b;break;default:r=a<=b;}
                    }
                    emitSingle(index,Atom::integral(r?1:0),depth);
                }
                return true;
            }
            case Op::controlMaximum: case Op::controlMinimum: {
                // Same inlet discipline as the arithmetic family; the result
                // keeps the argument's numeric type.
                if(m.kind==Message::Kind::list)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!m.numeric() || m.count<1 || m.count>2-inlet) {fault_=true;return true;}
                    for(int i=0;i<m.count;++i) if(!converted(m.atoms[i],n.stored[1].type,n.stored[inlet+i])) return true;
                }
                if(inlet==0) {
                    const bool pickLeft=n.stored[1].type==Atom::Type::integer
                        ?(d.op==Op::controlMaximum?n.stored[0].value.integer>=n.stored[1].value.integer:n.stored[0].value.integer<=n.stored[1].value.integer)
                        :(d.op==Op::controlMaximum?n.stored[0].number()>=n.stored[1].number():n.stored[0].number()<=n.stored[1].number());
                    emitSingle(index,pickLeft?n.stored[0]:n.stored[1],depth);
                }
                return true;
            }
            case Op::controlModulo: {
                // Max's control modulo is integer only. A zero divisor reports
                // an arithmetic error and still yields zero, matching the
                // captured expr behaviour rather than faulting the graph.
                if(m.kind==Message::Kind::list)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!m.numeric() || m.count<1 || m.count>2-inlet) {fault_=true;return true;}
                    for(int i=0;i<m.count;++i) if(!converted(m.atoms[i],Atom::Type::integer,n.stored[inlet+i])) return true;
                }
                if(inlet==0) {
                    const int64_t a=n.stored[0].value.integer,b=n.stored[1].value.integer;
                    const int64_t result=(b==0 || (a==INT64_MIN && b==-1))?0:a%b;
                    emitSingle(index,Atom::integral(result),depth);
                }
                return true;
            }
            case Op::clip: {
                if(m.kind==Message::Kind::list)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!m.numeric() || m.count<1 || m.count>3-inlet) {fault_=true;return true;}
                    for(int i=0;i<m.count;++i) if(!converted(m.atoms[i],n.stored[0].type,n.stored[inlet+i])) return true;
                }
                if(inlet==0) {
                    const double low=n.stored[1].number(),high=n.stored[2].number(),x=n.stored[0].number();
                    Atom out;
                    if(!converted(Atom::real(x<low?low:x>high?high:x),n.stored[0].type,out))return true;
                    emitSingle(index,out,depth);
                }
                return true;
            }
            case Op::scale: {
                // Only the four-argument linear mapping is prepared; the
                // exponential form is rejected before reaching the runtime.
                if(m.kind==Message::Kind::list)return true;
                if(m.kind!=Message::Kind::bang) {
                    if(!m.numeric() || m.count<1 || m.count>5-inlet) {fault_=true;return true;}
                    for(int i=0;i<m.count;++i) if(!converted(m.atoms[i],Atom::Type::floating,n.stored[inlet+i])) return true;
                }
                if(inlet==0) {
                    const double x=n.stored[0].number(),inLow=n.stored[1].number(),inHigh=n.stored[2].number();
                    const double outLow=n.stored[3].number(),outHigh=n.stored[4].number();
                    const double span=inHigh-inLow;
                    const double y=span==0?outLow:outLow+(x-inLow)*(outHigh-outLow)/span;
                    if(!std::isfinite(y)) {fault_=true;return true;}
                    emitSingle(index,Atom::real(y),depth);
                }
                return true;
            }
            case Op::textButton: case Op::uButton:
                // Mode 0 is a momentary button: it bangs on click and carries
                // no stored value. The host drives it with a number because the
                // kernel has no bang command; either form triggers once.
                if(m.kind!=Message::Kind::bang && !m.isNumber()) {fault_=true;return true;}
                emitBang(index,depth,0);
                return true;
            case Op::change: {
                // bang re-outputs the stored value (Max reference: "bang sends
                // the current value out the left outlet"; NOT yet measured).
                if(m.kind==Message::Kind::bang && inlet==0) {emitSingle(index,n.stored[0],depth,0);return true;}
                if(m.kind==Message::Kind::anything && m.selector==sym::set && m.count==1 && m.atoms[0].numeric() && inlet==0) {
                    Atom next;if(!converted(m.atoms[0],n.stored[0].type,next))return true;n.stored[0]=next;return true;   // set: store silently
                }
                if(m.kind!=Message::Kind::integer && m.kind!=Message::Kind::floating) {fault_=true;return true;}
                Atom next;if(!converted(m.atoms[0],n.stored[0].type,next))return true;
                const bool same=next.type==Atom::Type::integer?next.value.integer==n.stored[0].value.integer:next.value.floating==n.stored[0].value.floating;
                if(same)return true;
                n.stored[0]=next;emitSingle(index,next,depth,0);
                return true;
            }
            case Op::speedlim: {
                // Passes a message immediately when the interval since the
                // last output has elapsed; otherwise holds the MOST RECENT one
                // and emits it when the interval ends. Right inlet sets the
                // interval in milliseconds. Latest-wins is the assumed Max
                // behaviour and is not yet measured.
                if(inlet==1) {
                    if(!m.isNumber()) {fault_=true;return true;}
                    const double t=m.atoms[0].number();if(!std::isfinite(t) || t<0 || t>3600000.) {fault_=true;return true;}
                    n.time=t;return true;
                }
                const uint64_t interval=uint64_t(std::ceil(n.time*sampleRate_/1000.));
                if(!n.hasOutput || sampleTime_>=n.lastOutput+interval) {
                    n.hasOutput=true;n.lastOutput=sampleTime_;
                    if(n.delayActive) {n.delayActive=false;nextDelay();}
                    emit(index,m,depth,0);return true;
                }
                n.pending=m;
                if(!n.delayActive) {n.delayActive=true;n.due=n.lastOutput+interval;n.serial=serial_++;nextDelay();}
                return true;
            }
            case Op::counter: {
                // Measured in Live 12.4.5 ([counter 1 4] under [uzi 6] gives
                // 1 2 3 4 1 2): a bang outputs the current count, then
                // increments, wrapping to the minimum on the bang AFTER the
                // maximum. Inlet 4 sets the maximum without output.
                if(inlet==4) {
                    if(!m.isNumber()) {fault_=true;return true;}
                    Atom v;if(!converted(m.atoms[0],Atom::Type::integer,v))return true;
                    if(v.value.integer<n.stored[1].value.integer) {fault_=true;return true;}
                    n.stored[2]=v;return true;
                }
                if(inlet!=0) {fault_=true;return true;}
                // Refpage: 'set N' / 'goto N' set the count with no output (it
                // is sent on the next bang); the corpus (Shard) uses 'set 0'.
                if(m.kind==Message::Kind::anything && (m.selector==sym::set || symbols_.name(m.selector)=="goto") && m.count==1 && m.atoms[0].numeric()) {
                    Atom v;if(!converted(m.atoms[0],Atom::Type::integer,v))return true;
                    n.stored[0]=v;return true;
                }
                if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                const int64_t count=n.stored[0].value.integer;
                emitSingle(index,Atom::integral(count),depth,0);
                n.stored[0]=Atom::integral(count>=n.stored[2].value.integer?n.stored[1].value.integer:count+1);
                return true;
            }
            case Op::gate: {
                // Left inlet selects the open outlet (0 closes); the right
                // inlet is passed through it.
                if(inlet==0) {
                    if(!m.isNumber()) {fault_=true;return true;}
                    Atom sel;if(!converted(m.atoms[0],Atom::Type::integer,sel))return true;
                    const int64_t outlets=int64_t(d.arguments.empty()?1:d.arguments[0]);
                    // Measured in Live 12.4.5: a selection above the outlet
                    // count clamps to the top outlet. Zero closing is documented
                    // but not yet measured; negatives stay a fault.
                    if(sel.value.integer<0) {fault_=true;return true;}
                    n.stored[0]=Atom::integral(std::min(sel.value.integer,outlets));return true;
                }
                const int64_t open=n.stored[0].value.integer;
                if(open>0)emit(index,m,depth,int(open-1));
                return true;
            }
            case Op::peakAmp:
                // MEASURED in Live: a bang reports the running peak (0.50 for a
                // 0.5-amplitude cycle~) as an extra report; the interval timer
                // keeps its grid (September 11: next automatic report stayed on
                // the old grid). Whether the bang resets the peak accumulator
                // is refpage wording ("since the previous report"), unmeasured.
                if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                emitNumber(index,n.target,depth,0);n.target=0;
                return true;
            case Op::transport: return controlTransport(index,inlet,m,depth);
            case Op::spray: return controlSpray(index,inlet,m,depth);
            case Op::liveRemote: return controlLiveRemote(index,inlet,m,depth);
            case Op::liveDrop: {
                // live.drop (refpage): 'set <path>' stores the path silently
                // (Live restores it with the device), 'bang' sends the stored
                // path out the left outlet, 'clear' forgets it; a file dropped
                // on the zone (the host's sample chooser here) arrives as the
                // bare path symbol and is stored and sent. The path travels as
                // a one-atom symbol message (form UNMEASURED). Every change is
                // published to the host as 'path <symbol>' so the song keeps
                // it like Live's saved parameter; 'legend <text>' is display.
                if(inlet!=0) {fault_=true;return true;}
                auto publish=[&]{Message out=Message::anything(dropPath_);out.count=n.hasHeld?1:0;if(n.hasHeld)out.atoms[0]=n.held.atoms[0];queueExternal(index,0,out);};
                if(m.kind==Message::Kind::bang) {if(n.hasHeld)emit(index,n.held,depth,0);return true;}
                if(m.kind==Message::Kind::anything && m.selector==sym::set) {
                    if(m.count==0) {n.hasHeld=false;publish();return true;}
                    if(m.count!=1 || m.atoms[0].type!=Atom::Type::symbol) {fault_=true;return true;}
                    n.held=Message::symbol(m.atoms[0].value.symbol);n.hasHeld=true;publish();return true;
                }
                if(m.kind==Message::Kind::anything && m.selector==dropClear_ && m.count==0) {n.hasHeld=false;publish();return true;}
                if(m.kind==Message::Kind::anything && m.selector==dropLegend_) {queueExternal(index,inlet,m);return true;}
                if(m.kind==Message::Kind::symbol && m.count==1) {n.held=m;n.hasHeld=true;publish();emit(index,n.held,depth,0);return true;}
                if(m.kind==Message::Kind::anything && m.count==0) {n.held=Message::symbol(m.selector);n.hasHeld=true;publish();emit(index,n.held,depth,0);return true;}
                fault_=true;return true;
            }
            case Op::inert: return true;   // accepted, never answered
            case Op::midiToolIn: case Op::midiToolOut: return true;   // host-driven ports (notes editor); the graph never routes them
            case Op::midiIn:
                // A byte injected by the host passes straight to the outlet.
                if(m.kind!=Message::Kind::integer) {fault_=true;return true;}
                emit(index,m,depth,0);return true;
            case Op::modalExternal: return controlModalExternal(index,inlet,m,depth);
            case Op::uzi: return controlUzi(index,inlet,m,depth);
            case Op::listFunnel: return controlListFunnel(index,inlet,m,depth);
            case Op::sprintf: return controlSprintf(index,inlet,m,depth);
            case Op::zlLength: {
                // Outputs the atom count of the incoming list (a lone number is
                // a one-element list; a bare symbol/anything counts its atoms
                // plus the selector). Right inlet is unused here.
                if(inlet!=0)return true;
                int64_t length=m.count;
                if(m.kind==Message::Kind::anything && m.selector!=sym::empty)length+=1;
                if(m.kind==Message::Kind::bang)length=0;
                emitSingle(index,Atom::integral(length),depth,0);
                return true;
            }
            case Op::zlGroup: return controlZlGroup(index,inlet,m,depth);
            case Op::zlRegister: {
                // Measured in Live: a bare int in the left inlet STORES AND
                // OUTPUTS; a bang outputs the held message. The right inlet
                // stores silently. Only an int was measured on the left; lists
                // and symbols are treated the same way, labelled unmeasured.
                if(inlet==1) {n.held=m;n.hasHeld=true;return true;}
                if(m.kind==Message::Kind::bang) {if(n.hasHeld)emit(index,n.held,depth,0);return true;}
                n.held=m;n.hasHeld=true;emit(index,m,depth,0);return true;
            }
            case Op::pfft: case Op::fftIn: case Op::fftOut:
                fault_=true;return true;   // message inlets of pfft~ ('in N') are not modelled
            case Op::polyIn: {
                // poly~ messages land on in~ 1: only 'mute <voice> <state>' for
                // the single voice (0 = all) is modelled; the voice's nodes
                // stop rendering and output silence while muted.
                if(d.arguments.size()<2 || m.kind!=Message::Kind::anything || symbols_.name(m.selector)!="mute" || m.count!=2 || !m.atoms[0].numeric() || !m.atoms[1].numeric()) {fault_=true;return true;}
                const double voice=std::trunc(m.atoms[0].number());
                if(voice!=0 && voice!=1) {fault_=true;return true;}
                const bool muted=std::trunc(m.atoms[1].number())!=0;
                for(size_t i=1;i<d.arguments.size();++i)nodes_[size_t(d.arguments[i])].muted=muted;
                return true;
            }
            case Op::polyOut: fault_=true;return true;
            case Op::metro: return controlMetro(index,inlet,m,depth);
            case Op::pipe: return controlPipe(index,inlet,m,depth);
            case Op::coll: return controlColl(index,inlet,m,depth);
            case Op::randomInt: {
                // bang -> uniform int in [0, range); 'seed N' reseeds (0 = from
                // the sample clock); right inlet sets the range. The generator
                // is xorshift64*, not Max's: sequences will differ.
                if(inlet==1) {if(!m.isNumber()) {fault_=true;return true;}n.values[1]=std::max(1.,std::trunc(m.atoms[0].number()));return true;}
                if(m.kind==Message::Kind::anything && symbols_.name(m.selector)=="seed" && m.count==1 && m.atoms[0].numeric()) {
                    const int64_t seed=int64_t(std::trunc(m.atoms[0].number()));
                    n.rng=(seed==0?uint64_t(sampleTime_)+0x9E3779B97F4A7C15ull:uint64_t(seed))|1ull;return true;
                }
                if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                uint64_t x=n.rng;x^=x>>12;x^=x<<25;x^=x>>27;n.rng=x;
                const uint64_t r=x*0x2545F4914F6CDD1Dull;
                emitInteger(index,int64_t(r%uint64_t(std::max(1.,n.values[1]))),depth);return true;
            }
            case Op::translate: {
                // translate notevalues ms: note value symbol -> ms at the
                // session tempo. Other unit pairs need support.
                if(symbols_.name(d.atoms[0].value.symbol)!="notevalues" || symbols_.name(d.atoms[1].value.symbol)!="ms") {fault_=true;return true;}
                double beats;
                if(m.kind!=Message::Kind::anything || m.count!=0 || !noteValueBeats(symbols_.name(m.selector),beats)) {fault_=true;return true;}
                emitNumber(index,beats*60000./std::max(1.,transportTempo_.load(std::memory_order_relaxed)),depth);return true;
            }
            case Op::accum: {
                // Left: number sets, bang outputs, 'set N' sets; middle adds;
                // right multiplies (Max reference; the corpus uses set/add/bang).
                const bool integral=n.stored[0].type==Atom::Type::integer;
                auto number=[&](const Atom& a){return a.number();};
                if(inlet==0) {
                    if(m.kind==Message::Kind::bang) {emitSingle(index,n.stored[0],depth);return true;}
                    if(m.isNumber()) {Atom v;if(!converted(m.atoms[0],n.stored[0].type,v))return true;n.stored[0]=v;return true;}
                    if(m.kind==Message::Kind::anything && m.selector==sym::set && m.count==1 && m.atoms[0].numeric()) {Atom v;if(!converted(m.atoms[0],n.stored[0].type,v))return true;n.stored[0]=v;return true;}
                    fault_=true;return true;
                }
                if(!m.isNumber()) {fault_=true;return true;}
                const double result=inlet==1?number(n.stored[0])+m.atoms[0].number():number(n.stored[0])*m.atoms[0].number();
                Atom v;if(!converted(Atom::real(result),integral?Atom::Type::integer:Atom::Type::floating,v))return true;n.stored[0]=v;return true;
            }
            case Op::reverseDivide: {
                if(inlet==1) {if(!m.isNumber()) {fault_=true;return true;}Atom v;if(!converted(m.atoms[0],n.stored[1].type,v))return true;n.stored[1]=v;return true;}
                if(!m.isNumber()) {fault_=true;return true;}
                Atom a;if(!converted(m.atoms[0],n.stored[1].type,a))return true;
                if(n.stored[1].type==Atom::Type::integer) {
                    const int64_t x=a.value.integer,y=n.stored[1].value.integer;
                    emitInteger(index,x==0?y:y/x,depth);return true;   // zero divisor mirrors the measured [/] rule
                }
                const double x=a.number(),y=n.stored[1].number();
                emitNumber(index,x==0?y:y/x,depth);return true;
            }
            case Op::split: {
                // In [low, high] -> outlet 0, else outlet 1; right inlets set the bounds.
                if(inlet>0) {if(!m.isNumber()) {fault_=true;return true;}Atom v;if(!converted(m.atoms[0],n.stored[size_t(inlet)].type,v))return true;n.stored[size_t(inlet)]=v;return true;}
                if(!m.isNumber()) {fault_=true;return true;}   // list distribution across inlets is not modelled
                const double x=m.atoms[0].number();
                emitSingle(index,m.atoms[0],depth,x>=n.stored[1].number() && x<=n.stored[2].number()?0:1);return true;
            }
            case Op::stripNote: {
                // Note in the left inlet with the stored velocity: zero velocity
                // is dropped, otherwise velocity (outlet 1) then note (outlet 0).
                if(!m.isNumber()) {fault_=true;return true;}
                if(inlet==1) {n.values[1]=m.atoms[0].number();return true;}
                if(n.values[1]==0)return true;
                emitInteger(index,int64_t(std::trunc(n.values[1])),depth,1);
                emitInteger(index,int64_t(std::trunc(m.atoms[0].number())),depth,0);return true;
            }
            case Op::switchGate: {
                // Inlet 0 selects the open input (1..n, 0 closed); a message at
                // the open input passes through unchanged, others are dropped.
                if(inlet==0) {
                    if(!m.isNumber()) {fault_=true;return true;}
                    const double sel=std::trunc(m.atoms[0].number());
                    if(sel<0 || sel>d.arguments[0]) {fault_=true;return true;}
                    n.values[0]=sel;return true;
                }
                if(double(inlet)==n.values[0])emit(index,m,depth,0);
                return true;
            }
            case Op::noteIn: case Op::ctlIn: {
                // Byte-wise MIDI parser (running status). notein: channel,
                // velocity, note (right to left); ctlin N: channel, value for
                // controller N; bare ctlin: channel, controller, value.
                if(!m.isNumber()) {fault_=true;return true;}
                const int byte=int(std::trunc(m.atoms[0].number()));
                if(byte<0 || byte>255) {fault_=true;return true;}
                if(byte>=0xF8)return true;                       // realtime
                if(byte>=0x80) {n.midiStatus=byte<0xF0?byte:0;n.midiData=-1;return true;}
                if(!n.midiStatus)return true;
                const int kind=n.midiStatus&0xF0,channel=(n.midiStatus&0x0F)+1;
                if(kind==0xC0 || kind==0xD0)return true;         // one-byte messages, not modelled here
                if(n.midiData<0) {n.midiData=byte;return true;}
                const int data1=n.midiData,data2=byte;n.midiData=-1;
                if(d.op==Op::noteIn) {
                    if(kind!=0x90 && kind!=0x80)return true;
                    const int velocity=kind==0x80?0:data2;
                    emitInteger(index,channel,depth,2);emitInteger(index,velocity,depth,1);emitInteger(index,data1,depth,0);
                    return true;
                }
                if(kind!=0xB0)return true;
                if(!d.arguments.empty()) {
                    if(data1!=int(d.arguments[0]))return true;
                    emitInteger(index,channel,depth,1);emitInteger(index,data2,depth,0);return true;
                }
                emitInteger(index,channel,depth,2);emitInteger(index,data1,depth,1);emitInteger(index,data2,depth,0);return true;
            }
            case Op::bufferInfo: {
                // bang: outlets right to left. No file is ever loaded here, so
                // the filename/path outlets (7, 9) and the instrument list (1)
                // stay silent (undocumented for an unallocated buffer); loop
                // points report 0, total ms and channels the table, sr ours.
                if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                const auto& table=*n.pokeTable;
                emitInteger(index,int64_t(table.channels()),depth,8);
                emitNumber(index,double(table.frames())*1000./sampleRate_,depth,6);
                for(int o=5;o>=2;--o)emitNumber(index,0.,depth,o);
                emitNumber(index,sampleRate_,depth,0);return true;
            }
            case Op::mpeParse: {
                // Byte-wise parser: note on/off -> outlet 0 (pitch velocity),
                // poly pressure -> 1 (key value), CC -> 2 (number value),
                // program -> 3, aftertouch -> 4, pitch bend -> 5 (hires 1:
                // float -1..1, else 0-16383 int), voice number -> 6 (the
                // channel's member index, -1 for the manager channel 1), zone
                // first channel -> 7 (1), zone index -> 8 (0). The mpeevent
                // outlet 9 and multi-zone layouts are not modelled.
                if(!m.isNumber()) {fault_=true;return true;}
                const int byte=int(std::trunc(m.atoms[0].number()));
                if(byte<0 || byte>255) {fault_=true;return true;}
                if(byte>=0xF8)return true;
                if(byte>=0x80) {n.midiStatus=byte<0xF0?byte:0;n.midiData=-1;return true;}
                if(!n.midiStatus)return true;
                const int kind=n.midiStatus&0xF0,channel=(n.midiStatus&0x0F)+1;
                const bool oneByte=kind==0xC0 || kind==0xD0;
                if(!oneByte && n.midiData<0) {n.midiData=byte;return true;}
                const int data1=oneByte?byte:n.midiData,data2=oneByte?0:byte;n.midiData=-1;
                auto context=[&](){emitInteger(index,0,depth,8);emitInteger(index,1,depth,7);emitInteger(index,channel==1?-1:channel-2,depth,6);};
                Atom pair[2];
                switch(kind) {
                    case 0x90: case 0x80: context();pair[0]=Atom::integral(data1);pair[1]=Atom::integral(kind==0x80?0:data2);emitSequence(index,pair,2,depth,0);break;
                    case 0xA0: context();pair[0]=Atom::integral(data1);pair[1]=Atom::integral(data2);emitSequence(index,pair,2,depth,1);break;
                    case 0xB0: context();pair[0]=Atom::integral(data1);pair[1]=Atom::integral(data2);emitSequence(index,pair,2,depth,2);break;
                    case 0xC0: context();emitInteger(index,data1,depth,3);break;
                    case 0xD0: context();emitInteger(index,data1,depth,4);break;
                    case 0xE0: {
                        context();const int raw=data1|(data2<<7);
                        if(!d.arguments.empty() && d.arguments[0]==1)emitNumber(index,(raw-8192)/8192.,depth,5);
                        else emitInteger(index,raw,depth,5);
                        break;
                    }
                    default:break;
                }
                return true;
            }
            case Op::adsr: {
                // Trigger (inlet 0): nonzero starts the attack from the current
                // level, 0 releases from the current level over the full
                // release time; inlets 1-4 set attack/decay ms, sustain level,
                // release ms. All segments LINEAR (MEASURED in Live 12.4.5:
                // live.adsr~ 200 200 0.5 300 fits +1/200 ms, -0.5/200 ms and
                // -0.5/300 ms with 1e-8 residuals).
                if(!m.isNumber()) {fault_=true;return true;}
                const double v=m.atoms[0].number();
                if(inlet>=1 && inlet<=4) {
                    if(v<0 || (inlet==3 && v>1) || v>3600000) {fault_=true;return true;}
                    n.values[size_t(inlet)]=v;return true;
                }
                if(v!=0) {n.values[5]=1;n.target=1;n.remaining=std::max<uint64_t>(1,uint64_t(std::llround(n.values[1]*sampleRate_/1000.)));n.step=(1-n.values[0])/double(n.remaining);}
                else if(n.values[5]!=0) {n.values[5]=4;n.target=0;n.remaining=std::max<uint64_t>(1,uint64_t(std::llround(n.values[4]*sampleRate_/1000.)));n.step=(0-n.values[0])/double(n.remaining);}
                return true;
            }
            case Op::tapOut:
                if(!m.isNumber() || inlet<0 || size_t(inlet)>=d.arguments.size()) {fault_=true;return true;}
                n.values[size_t(inlet)]=std::max(0.,m.atoms[0].number());return true;
            case Op::tapIn: fault_=true;return true;   // 'clear' and resizing are not modelled
            case Op::peek: {
                if(inlet==2 && m.isNumber()) {const double c=std::trunc(m.atoms[0].number());if(c<1 || c>double(n.pokeTable->channels())) {fault_=true;return true;}n.values[2]=c-1;return true;}
                if(inlet==1 && m.isNumber()) {n.values[1]=m.atoms[0].number();return true;}
                if(inlet!=0) {fault_=true;return true;}
                // MEASURED (Max 9, September 11): the peek~ object truncates
                // the index and CLAMPS it to 0..frames-1 for reads and writes
                // (-1 and 128 land on cells 0 and 127; 126.6 -> 126). Gen's
                // peek()/sample() return 0 out of range instead.
                auto clampedIndex=[&](double raw){
                    if(!std::isfinite(raw))return -1.;
                    const double last=double(n.pokeTable->frames())-1;
                    return last<0?-1.:std::min(std::max(std::trunc(raw),0.),last);
                };
                const double channel=std::min(n.values[2],std::max(0.,double(n.pokeTable->channels())-1));
                if(m.kind==Message::Kind::list && m.count>=2 && m.atoms[0].numeric() && m.atoms[1].numeric()) {
                    n.pokeTable->poke(m.atoms[1].number(),clampedIndex(m.atoms[0].number()),channel);return true;
                }
                if(m.isNumber()) {emitNumber(index,n.pokeTable->peek(clampedIndex(m.atoms[0].number()),channel),depth,0);return true;}
                fault_=true;return true;
            }
            case Op::functionCurve: {
                // Refpage: float x -> outlet 0 y; 'x y' list adds a point,
                // 'index x y [curve]' modifies one (0-based, ignored when the
                // index does not exist); clear [indices...]; setcurve N c
                // (segments numbered from 1); nth i; xyc x y c; set x y ...;
                // bang -> outlet 1 gets the first Y as a float, then 'y dt'
                // pairs (mode 0, line~) or 'y dt curve' triples (mode 1,
                // curve~); dump -> outlet 2 one list per point; listdump ->
                // outlet 2 one flat x y list. The right outlet bangs only when
                // a mouse edit completes: the host's touch editor sends the
                // same messages at inlet -1 and a bang there marks completion.
                // 'index x y' re-sorts by x (MEASURED: a point moved past its
                // neighbour changes index; clear 0 2 keeps points 1 and 3).
                // Every point change is published to the host.
                const bool ui=inlet<0;
                if(inlet==1) {if(m.isNumber()) {n.values[1]=m.atoms[0].number();return true;}fault_=true;return true;}
                if(ui && m.kind==Message::Kind::bang) {emitBang(index,depth,3);return true;}
                if(m.isNumber()) {emitNumber(index,functionValue(n,m.atoms[0].number()),depth,0);return true;}
                const bool curve=d.arguments[3]!=0;
                if(m.kind==Message::Kind::list) {
                    for(int i=0;i<m.count;++i)if(!m.atoms[i].numeric()) {fault_=true;return true;}
                    if(m.count==2) {functionAdd(n,m.atoms[0].number(),m.atoms[1].number(),0);functionPublish(index);return true;}
                    if(m.count==3 || (m.count==4 && curve)) {
                        const double at=m.atoms[0].number();
                        if(at<0 || at>=double(n.points.size()) || std::trunc(at)!=at)return true;
                        auto& p=n.points[size_t(at)];
                        if(!std::isfinite(m.atoms[1].number()) || !std::isfinite(m.atoms[2].number()))return true;
                        p.x=m.atoms[1].number();p.y=m.atoms[2].number();
                        if(m.count==4 && std::isfinite(m.atoms[3].number()))p.curve=std::min(std::max(m.atoms[3].number(),-1.),1.);
                        std::stable_sort(n.points.begin(),n.points.end(),[](const Node::Breakpoint& a,const Node::Breakpoint& b){return a.x<b.x;});
                        functionPublish(index);return true;
                    }
                    fault_=true;return true;
                }
                if(m.kind==Message::Kind::bang) {
                    if(n.points.empty())return true;
                    emitNumber(index,n.points.front().y,depth,1);
                    std::array<Atom,Message::capacity> list{};int count=0;
                    for(size_t i=1;i<n.points.size();++i) {
                        const auto& p=n.points[i];if(count+(curve?3:2)>int(Message::capacity))break;
                        list[size_t(count++)]=Atom::real(p.y);list[size_t(count++)]=Atom::real(p.x-n.points[i-1].x);
                        if(curve)list[size_t(count++)]=Atom::real(p.curve);
                    }
                    if(count)emitSequence(index,list.data(),count,depth,1);
                    return true;
                }
                if(m.kind!=Message::Kind::anything) {fault_=true;return true;}
                const auto& sel=symbols_.name(m.selector);
                if(m.selector==sym::clear) {
                    if(m.count==0) {n.points.clear();functionPublish(index);return true;}
                    // clear <indices...>: 0-based points, removed together so
                    // later indices stay valid whatever their order.
                    std::array<bool,256> drop{};
                    for(int i=0;i<m.count;++i) {
                        if(!m.atoms[i].numeric()) {fault_=true;return true;}
                        const double at=m.atoms[i].number();
                        if(at>=0 && at<double(n.points.size()) && std::trunc(at)==at)drop[size_t(at)]=true;
                    }
                    size_t kept=0;
                    for(size_t i=0;i<n.points.size();++i)if(!drop[i])n.points[kept++]=n.points[i];
                    n.points.resize(kept);functionPublish(index);return true;
                }
                if(m.selector==sym::nth && m.count==1 && m.atoms[0].numeric()) {
                    const double at=m.atoms[0].number();
                    if(at>=0 && at<double(n.points.size()) && std::trunc(at)==at)emitNumber(index,n.points[size_t(at)].y,depth,0);
                    return true;
                }
                if(sel=="dump" && m.count==0) {
                    for(const auto& p:n.points) {
                        Atom list[3]={Atom::real(p.x),Atom::real(p.y),Atom::real(p.curve)};
                        emitSequence(index,list,curve?3:2,depth,2);
                    }
                    return true;
                }
                if(sel=="listdump" && m.count==0) {
                    std::array<Atom,Message::capacity> list{};int count=0;
                    for(const auto& p:n.points) {if(count+2>int(Message::capacity)) {fault_=true;return true;}list[size_t(count++)]=Atom::real(p.x);list[size_t(count++)]=Atom::real(p.y);}
                    if(count)emitSequence(index,list.data(),count,depth,2);
                    return true;
                }
                if(m.selector==functionSetcurve_ && m.count==2 && m.atoms[0].numeric() && m.atoms[1].numeric()) {
                    const int segment=int(std::trunc(m.atoms[0].number()));
                    if(segment>=1 && size_t(segment)<n.points.size()) {n.points[size_t(segment)].curve=std::min(std::max(m.atoms[1].number(),-1.),1.);functionPublish(index);}
                    return true;
                }
                if(sel=="add" && m.count>=2 && m.atoms[0].numeric() && m.atoms[1].numeric()) {functionAdd(n,m.atoms[0].number(),m.atoms[1].number(),0);functionPublish(index);return true;}
                if(sel=="xyc" && m.count==3 && m.atoms[0].numeric() && m.atoms[1].numeric() && m.atoms[2].numeric()) {
                    functionAdd(n,m.atoms[0].number(),m.atoms[1].number(),std::min(std::max(m.atoms[2].number(),-1.),1.));functionPublish(index);return true;
                }
                if(m.selector==sym::set && m.count>=2 && m.count%2==0) {
                    // set x y ...: MEASURED (Max 9, September 11): pairs are
                    // consumed positionally, points beyond the pairs stay,
                    // values round-trip through 32-bit float, and the list is
                    // NOT re-sorted (duplicate x coexist), unlike 'index x y'.
                    for(int i=0;i<m.count;++i)if(!m.atoms[i].numeric()) {fault_=true;return true;}
                    for(size_t i=0;i<n.points.size() && int(2*i+1)<m.count;++i) {
                        const double x=double(float(m.atoms[2*i].number())),y=double(float(m.atoms[2*i+1].number()));
                        if(std::isfinite(x) && std::isfinite(y)) {n.points[i].x=x;n.points[i].y=y;}
                    }
                    functionPublish(index);return true;
                }
                fault_=true;return true;
            }
            case Op::overdrive:
                if(!m.isNumber() || inlet!=1 || !(m.atoms[0].number()>0)) {fault_=true;return true;}
                n.values[1]=m.atoms[0].number();return true;
            case Op::degrade:
                if(!m.isNumber() || inlet<1 || inlet>2) {fault_=true;return true;}
                n.values[size_t(inlet)]=m.atoms[0].number();return true;
            case Op::tanhSignal: case Op::polyUp: fault_=true;return true;
            case Op::filterCoeff: {
                if(m.isNumber() && inlet>=0 && inlet<3) {n.values[size_t(inlet)]=m.atoms[0].number();n.coeffCounter=0;return true;}
                if(inlet!=0 || m.kind!=Message::Kind::anything) {fault_=true;return true;}
                const auto& sel=symbols_.name(m.selector);
                static const char* types[]={"lowpass","highpass","bandpass","bandstop","peaknotch","lowshelf","highshelf","allpass","off"};
                for(int t=0;t<9;++t)if(sel==types[t] && m.count==0) {n.filterType=t;n.coeffCounter=0;return true;}
                if(sel=="resamp" && m.count==1 && m.atoms[0].numeric()) {
                    const double r=std::trunc(m.atoms[0].number());if(r<1 || r>65536) {fault_=true;return true;}
                    n.definition.arguments[1]=r;n.coeffCounter=0;return true;
                }
                fault_=true;return true;
            }
            case Op::biquad:
                if(m.kind==Message::Kind::anything && symbols_.name(m.selector)=="clear" && m.count==0 && inlet==0) {n.bqX1=n.bqX2=n.bqY1=n.bqY2=0;return true;}
                if(m.isNumber() && inlet>=1 && inlet<=5) {n.values[size_t(inlet)]=m.atoms[0].number();return true;}
                if(m.kind==Message::Kind::list && inlet==0 && m.count==5) {for(int k=0;k<5;++k)n.values[size_t(k)+1]=m.atoms[k].number();return true;}
                fault_=true;return true;
            case Op::divideSignal:
                if(!m.isNumber() || inlet!=1) {fault_=true;return true;}
                n.values[1]=m.atoms[0].number();return true;
            case Op::absSignal: case Op::sendSignal: case Op::receiveSignal: fault_=true;return true;
            case Op::loudness:
                if(inlet==0 && m.kind==Message::Kind::anything && symbols_.name(m.selector)=="reset" && m.count==0) {n.loudness->reset();return true;}
                fault_=true;return true;
            case Op::scope: fault_=true;return true;   // scope attribute messages need support
            case Op::fzero: {
                // Attribute messages (the external's setters); freqmax below
                // freqmin posts an error in Max and falls back to sr / 5 here.
                if(inlet!=0 || m.kind!=Message::Kind::anything || m.count!=1 || !m.atoms[0].numeric()) {fault_=true;return true;}
                const auto& sel=symbols_.name(m.selector);const double v=m.atoms[0].number();
                bool valid;const int64_t whole=m.atoms[0].converted(Atom::Type::integer,valid=true).value.integer;
                if(!valid) {fault_=true;return true;}
                if(sel=="threshold")n.fzero->setThreshold(v);
                else if(sel=="freqmin")n.fzero->setFreqMin(whole);
                else if(sel=="freqmax")n.fzero->setFreqMax(whole);
                else if(sel=="size")n.fzero->setSize(whole);
                else if(sel=="period")n.fzero->setPeriod(whole);
                else if(sel=="onsetpitch")n.fzero->setOnsetPitch(v);
                else if(sel=="onsetamp")n.fzero->setOnsetAmp(v);
                else if(sel=="onsetperiod")n.fzero->setOnsetPeriod(whole);
                else if(sel=="onsetlist")n.fzero->setOnsetList(whole!=0);
                else if(sel=="quiet")n.fzero->setQuiet(whole!=0);
                else {fault_=true;return true;}
                return true;
            }
            case Op::randSignal:
                if(inlet!=0 || !m.isNumber() || !(m.atoms[0].number()>0)) {fault_=true;return true;}
                n.values[1]=m.atoms[0].number();return true;
            case Op::cpuClock: {
                // Milliseconds on a monotonic clock (Max reports CPU time since
                // launch); the corpus only uses it as a random seed source.
                if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                const auto now=std::chrono::steady_clock::now().time_since_epoch();
                emitNumber(index,double(std::chrono::duration_cast<std::chrono::microseconds>(now).count())/1000.,depth);return true;
            }
            case Op::indexSignal:
                if(inlet==1 && m.isNumber()) {
                    const double channel=std::trunc(m.atoms[0].number());
                    if(channel<1 || channel>64) {fault_=true;return true;}
                    n.values[1]=channel-1;return true;
                }
                fault_=true;return true;
            case Op::poke:
                if(inlet==2 && m.isNumber()) {
                    const double channel=std::trunc(m.atoms[0].number());
                    if(channel<1 || channel>double(n.pokeTable->channels())) {fault_=true;return true;}
                    n.values[2]=channel-1;return true;
                }
                if(inlet==1 && m.isNumber()) {n.values[1]=m.atoms[0].number();return true;}
                fault_=true;return true;
            case Op::clipSignal:
                if(inlet==0 || !m.isNumber()) {fault_=true;return true;}
                n.values[size_t(inlet)]=m.atoms[0].number();return true;
            case Op::onePole:
                if(inlet!=1 || !m.isNumber()) {fault_=true;return true;}
                {
                    const double fc=m.atoms[0].number();
                    if(!std::isfinite(fc) || fc<0 || fc>sampleRate_*0.5) {fault_=true;return true;}
                    n.values[1]=fc;n.step=std::exp(-2*M_PI*fc/sampleRate_);
                }
                return true;
            case Op::adStatus: {
                // The prepared property is the host sample rate; Max reports it
                // on bang and whenever the driver changes it. The right outlet
                // lists the driver's available values (a menu source); this
                // host offers exactly one rate, so the list has one entry.
                if(m.kind!=Message::Kind::bang) {fault_=true;return true;}
                Atom one=Atom::integral(int64_t(sampleRate_));
                emitSequence(index,&one,1,depth,1);
                emitSingle(index,Atom::integral(int64_t(sampleRate_)),depth);
                return true;
            }
            default:return false;
        }
    }
    // One renderer/control owner writes a first-fault record exactly once.
    // Publish its location LAST: diagnostic readers may run concurrently with
    // audio and cannot use fault_ (which trips before attribution) as a fence.
    // -1: no record; -2: final output mix; -3: host render contract.
    static_assert(std::atomic<int>::is_always_lock_free,"Fault publication must be lock-free");
    std::atomic<int> faultNode_{-1};
    int faultInlet_=-1,faultKind_=-1;Symbol faultSelector_=0;
    bool faultOutlet_=false;
    const char* faultReason_=nullptr;   // set at a few fault sites for diagnostics
    void faultBecause(const char* why) noexcept {if(!fault_.load(std::memory_order_relaxed))faultReason_=why;fault_=true;}
    void attributeFault(int node,int port,int kind,Symbol selector=0,bool outlet=false) noexcept {
        if(faultNode_.load(std::memory_order_relaxed)!=-1)return;
        faultInlet_=port;faultKind_=kind;faultSelector_=selector;faultOutlet_=outlet;
        faultNode_.store(node,std::memory_order_release);
    }
    void deliver(int index, int inlet, Message message, int depth) noexcept {
        const bool before=fault_.load(std::memory_order_relaxed);
        deliverInner(index,inlet,message,depth);
        if(!before && fault_.load(std::memory_order_relaxed))attributeFault(index,inlet,int(message.kind),message.selector);
    }
    void deliverInner(int index, int inlet, Message message, int depth) noexcept {
        if (--*dispatchBudget_ < 0 || depth > 64) { fault_.store(true, std::memory_order_relaxed); return; }
        auto& n = nodes_[index]; const auto& d = n.definition;
        if(control(index,inlet,message,depth)) return;
        if(d.op!=Op::pack && d.op!=Op::pak && !message.numeric()) {fault_=true;return;}
        switch (d.op) {
            case Op::dbtoa:
                if (message.count > 1) { fault_ = true; return; }
                if (message.count) n.values[0] = std::pow(10., message.atoms[0].number() / 20.);
                if (!std::isfinite(n.values[0])) { fault_ = true; return; }
                emitNumber(index,n.values[0], depth); break;
            case Op::atodb:
                // [atodb] control object: 20*log10(x). The corpus clamps its
                // input positive first (maximum 1e-10); what Max emits for
                // x <= 0 is NOT measured, so that case faults visibly.
                if (message.count > 1) { fault_ = true; return; }
                if (message.count) n.values[0] = message.atoms[0].number();
                if (!(n.values[0] > 0) || !std::isfinite(n.values[0])) { fault_ = true; return; }
                emitNumber(index,20.*std::log10(n.values[0]), depth); break;
            case Op::squareRoot:
                // [sqrt] control object; negative input is unmeasured and faults.
                if (message.count > 1) { fault_ = true; return; }
                if (message.count) n.values[0] = message.atoms[0].number();
                if (n.values[0] < 0 || !std::isfinite(n.values[0])) { fault_ = true; return; }
                emitNumber(index,std::sqrt(n.values[0]), depth); break;
            case Op::pack: case Op::pak: {
                if(message.kind==Message::Kind::anything && message.selector==sym::send) {fault_=true;return;}
                if(message.kind==Message::Kind::anything && message.selector==sym::nth) {
                    if(message.count!=1 || !message.atoms[0].numeric()) {fault_=true;return;}
                    Atom slot;if(!converted(message.atoms[0],Atom::Type::integer,slot))return;
                    if(slot.value.integer>=1 && slot.value.integer<=n.storedCount) emitSequence(index,&n.stored[size_t(slot.value.integer)-1],1,depth);
                    return;
                }
                const bool set=message.kind==Message::Kind::anything && message.selector==sym::set;
                std::array<Atom,Message::capacity> atoms{};int count=message.dataAtoms(atoms.data());
                if(set) {count=message.count;atoms=message.atoms;}
                if(count<0) {fault_=true;return;}
                for(int i=0;i<std::min(count,n.storedCount-inlet);++i)
                    if(!converted(atoms[i],n.stored[inlet+i].type,n.stored[inlet+i])) return;
                if((inlet==0 || d.op==Op::pak) && !set) {
                    emitSequence(index,n.stored.data(),n.storedCount,depth);
                }
                break;
            }
            case Op::line: {
                // float: ramp over the right-inlet time; "target time" pairs
                // are consecutive segments; an odd list (3+ atoms) first jumps
                // to its leading value (Max's line~ list contract). Queued
                // segments wait in stored[] and start as each one completes.
                if (message.count == 0 || (inlet == 1 && message.count > 1) || message.count > Message::capacity) { fault_ = true; return; }
                if (inlet == 1) { n.time = std::max(0., message.atoms[0].number()); break; }
                int first = 0;
                if (message.count >= 3 && message.count % 2 == 1) { n.values[0] = message.atoms[0].number(); first = 1; }
                n.storedCount = 0; n.values[3] = 0;
                auto segment = [&](double target, double ms) {
                    if (!std::isfinite(ms) || ms < 0 || ms > 3600000.) { fault_ = true; return; }
                    n.time = 0; n.target = target;
                    n.remaining = uint64_t(std::llround(ms * sampleRate_ / 1000.));
                    if (!n.remaining) n.values[0] = n.target;
                    else n.step = (n.target - n.values[0]) / double(n.remaining);
                };
                if (message.count == 1) { segment(message.atoms[0].number(), n.time); break; }
                if ((message.count - first) % 2 != 0) { fault_ = true; return; }
                segment(message.atoms[size_t(first)].number(), std::max(0., message.atoms[size_t(first) + 1].number()));
                for (int i = first + 2; i + 1 < message.count; i += 2) {
                    n.stored[size_t(n.storedCount++)] = Atom::real(message.atoms[size_t(i)].number());
                    n.stored[size_t(n.storedCount++)] = Atom::real(std::max(0., message.atoms[size_t(i) + 1].number()));
                }
                break;
            }
            case Op::signal:
                if (message.count != 1) { fault_ = true; return; }
                n.values[inlet] = message.atoms[0].number(); break;
            case Op::multiply: case Op::add: case Op::subtract: case Op::reverseSubtractSignal: {
                if (message.count != 1) { fault_ = true; return; }
                const bool leftSignal=!n.signalInputs[0].empty(),rightSignal=!n.signalInputs[1].empty();
                if(leftSignal && rightSignal) break;
                // Actual Max 9: with one connected signal, a number at either
                // inlet updates the other (constant) operand. Boundary messages
                // must retain this behavior even on a signal-carrying cord.
                const int target=leftSignal?1:rightSignal?0:inlet;
                n.values[target]=message.atoms[0].number();break;
            }
            default: fault_ = true; break;
        }
    }
    double input(const Node& node, int inlet) const noexcept {
        const auto& edges = node.signalInputs[inlet];
        if (edges.empty()) return node.values[inlet];
        double sum = 0;
        for (const auto& edge : edges) sum += nodes_[edge.source].output[edge.outlet];
        return sum;
    }
public:
    Runtime(const std::vector<Definition>& definitions, const std::vector<Edge>& edges, double sampleRate,Symbols symbols=Symbols(),Trace trace=nullptr,void* context=nullptr,
            const std::vector<int>& parameterOrder={},std::shared_ptr<RoutingDomain> routing={},int ioVector=64)
        : sampleRate_(sampleRate),symbols_(std::move(symbols)),routing_(routing?routing:std::make_shared<RoutingDomain>()),parameterOrder_(parameterOrder),trace_(trace),traceContext_(context) {
        if (!std::isfinite(sampleRate) || sampleRate < 8000 || sampleRate > 384000 || definitions.empty() || definitions.size() > 4096 || edges.size() > 16384 || ioVector<1 || ioVector>65536)
            throw std::invalid_argument("Unsupported graph size or sample rate");
        externalEvents_.resize(std::clamp<size_t>(definitions.size()*4,256,4096));
        // Per-block message dispatch budget: 4096 hops covers ordinary devices;
        // a 2000-object sequencer's script bursts need proportionally more.
        // Runaway feedback is still bounded (depth 64 and this cap).
        budgetPerBlock_=int(std::clamp<size_t>(4096+definitions.size()*64,4096,262144));
        externalReplies_.resize(std::clamp<size_t>(definitions.size()*2,256,2048));
        static_assert(std::atomic<unsigned>::is_always_lock_free && std::atomic<double>::is_always_lock_free);
        for (auto& meter : meters_) meter.store(0., std::memory_order_relaxed);
        for (auto& value : parameterValues_) value.store(0., std::memory_order_relaxed);
        size_t bufferSamples=0;
        for(const auto& d:definitions)if(d.op==Op::buffer) {
            if(d.atoms.size()!=1 || !d.atoms[0].valid(symbols_.size()) || d.atoms[0].type!=Atom::Type::symbol ||
               symbols_.name(d.atoms[0].value.symbol).empty() || d.arguments.size()<2 || d.arguments.size()>4 ||
               !std::isfinite(d.arguments[0]) || !std::isfinite(d.arguments[1]) || d.arguments[1]<0 || d.arguments[1]>64 || std::trunc(d.arguments[1])!=d.arguments[1] ||
               (d.arguments.size()>=3 && d.arguments[2]!=1 && d.arguments[2]!=0) ||
               (d.arguments.size()==4 && (!std::isfinite(d.arguments[3]) || d.arguments[3]<0 || d.arguments[3]>4194304 || std::trunc(d.arguments[3])!=d.arguments[3])))
                throw std::invalid_argument("Invalid prepared buffer~ dimensions/name");
            // A third argument marks milliseconds; the legacy two-argument
            // plan stores samples. Actual Max rounds positive half-samples up.
            const double frames=(d.arguments.size()>=3 && d.arguments[2]==1)?std::floor(std::max(0.,d.arguments[0])*sampleRate*.001+.5):d.arguments[0];
            if(!std::isfinite(frames) || frames<0 || frames>4194304 || std::trunc(frames)!=frames || (frames!=0 && d.arguments[1]==0))
                throw std::invalid_argument("Invalid prepared buffer~ sample budget");
            // A fourth argument reserves words for sound files the patch loads
            // into this buffer (replace/read/import) without reallocating under DSP.
            const size_t reserve=d.arguments.size()==4?size_t(d.arguments[3]):0;
            const size_t count=std::max(size_t(frames)*size_t(d.arguments[1]),reserve);
            if(count>8388608-bufferSamples)throw std::invalid_argument("Graph buffer~ memory budget exceeded");bufferSamples+=count;
            routing_->declareBuffer(symbols_.name(d.atoms[0].value.symbol),size_t(frames),size_t(d.arguments[1]),reserve);
        }
        for (const auto& definition : definitions) {
            if (int(definition.op) < 0 || int(definition.op) > int(Op::liveDrop) || definition.arguments.size() > Message::capacity || definition.atoms.size()>Message::capacity ||
                !std::isfinite(definition.initial) || !std::isfinite(definition.minimum) || !std::isfinite(definition.maximum) || definition.minimum > definition.maximum)
                throw std::invalid_argument("Invalid node definition");
            for (double a : definition.arguments) if (!std::isfinite(a)) throw std::invalid_argument("Non-finite argument");
            if(definition.op==Op::dspState && (!definition.arguments.empty() || !definition.atoms.empty()))
                throw std::invalid_argument("Unsupported dspstate~ constructor arguments");
            if(definition.op==Op::signalSnapshot && (definition.arguments.size()!=3 || definition.arguments[0]<0 || definition.arguments[0]>3600000 ||
                definition.arguments[1]<0 || definition.arguments[1]>63 || std::trunc(definition.arguments[1])!=definition.arguments[1] ||
                (definition.arguments[2]!=0 && definition.arguments[2]!=1)))
                throw std::invalid_argument("Invalid snapshot~ interval/offset/active definition");
            if(definition.op==Op::signalSelector && (definition.arguments.size()!=4 ||
                definition.arguments[0]<1 || definition.arguments[0]>63 || std::trunc(definition.arguments[0])!=definition.arguments[0] ||
                definition.arguments[1]<0 || definition.arguments[1]>definition.arguments[0] || std::trunc(definition.arguments[1])!=definition.arguments[1] ||
                definition.arguments[2]<0 || definition.arguments[2]>3600000 ||
                (definition.arguments[3]!=0 && definition.arguments[3]!=1)))
                throw std::invalid_argument("Invalid selector~ port/selection/ramp definition");
            if(definition.op==Op::external && (definition.arguments.size()!=2 ||
                definition.arguments[0]<0 || definition.arguments[0]>64 || std::trunc(definition.arguments[0])!=definition.arguments[0] ||
                definition.arguments[1]<0 || definition.arguments[1]>64 || std::trunc(definition.arguments[1])!=definition.arguments[1]))
                throw std::invalid_argument("Invalid external control ports");
            if(!std::isfinite(definition.parameterExponent) || definition.parameterExponent<=0 || definition.parameterSteps<0 || definition.parameterSteps==1 || definition.parameterSteps>65536)
                throw std::invalid_argument("Unsupported parameter exponent or steps");
            if(definition.presentation && definition.op!=Op::dial && definition.op!=Op::meter && definition.op!=Op::decoration && definition.op!=Op::textButton && definition.op!=Op::uButton && definition.op!=Op::message && definition.op!=Op::inert && definition.op!=Op::scope && definition.op!=Op::functionCurve && definition.op!=Op::liveDrop)
                throw std::invalid_argument("Presentation attribute target must be a native UI object");
            if(definition.parameterType<0 || definition.parameterType>2 || definition.controlKind<0 || definition.controlKind>3 ||
               definition.parameterLabels.size()>4096 || (definition.controlKind!=0 && (definition.op!=Op::dial || definition.parameterType!=2)))
                throw std::invalid_argument("Invalid original control/parameter kind");
            // Momentary buttons reset their stored state on a flash timer; the
            // interval is scheduled through the same delay path as speedlim so
            // it also fires with DSP stopped, since render() keeps running.
            if(definition.parameterType!=0 && (std::trunc(definition.minimum)!=definition.minimum || std::trunc(definition.maximum)!=definition.maximum ||
                    definition.minimum < -9007199254740991. || definition.maximum > 9007199254740991.))
                throw std::invalid_argument("Integer parameter bounds must be exact integers");
            if(definition.parameterType==2 && (definition.minimum!=0 || definition.parameterLabels.empty() || definition.maximum!=double(definition.parameterLabels.size()-1)))
                throw std::invalid_argument("Invalid parameter enum labels/range");
            for(auto label:definition.parameterLabels)if(label>=symbols_.size())throw std::invalid_argument("Invalid prepared parameter label");
            if(definition.controlKind>=2 && (definition.maximum!=1 || definition.textLabels[0]>=symbols_.size() || definition.textLabels[1]>=symbols_.size()))
                throw std::invalid_argument("Invalid text control state/labels");
            for(const auto& atom:definition.atoms) if(!atom.valid(symbols_.size())) throw std::invalid_argument("Invalid literal atom");
            if(definition.op==Op::signalRecord) {
                if(definition.arguments.size()!=3 || definition.arguments[0]<1 || definition.arguments[0]>62 || std::trunc(definition.arguments[0])!=definition.arguments[0] ||
                   (definition.arguments[1]!=0 && definition.arguments[1]!=1) || (definition.arguments[2]!=0 && definition.arguments[2]!=1) ||
                   definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol || symbols_.name(definition.atoms[0].value.symbol).empty())
                    throw std::invalid_argument("Invalid record~ buffer/channel/loop/append definition");
                routing_->declareRecordBuffer(symbols_.name(definition.atoms[0].value.symbol));
            }
            if ((definition.op == Op::pack || definition.op==Op::pak) && definition.atoms.empty() && (definition.arguments.empty() || definition.integers.size() != definition.arguments.size()))
                throw std::invalid_argument("Invalid pack types");
            if(definition.op==Op::trigger && (definition.formats.empty() || definition.formats.size()>Message::capacity || definition.atoms.size()!=definition.formats.size())) throw std::invalid_argument("Invalid trigger formats");
            for(auto format:definition.formats) if(int(format)<0 || int(format)>int(Format::constant)) throw std::invalid_argument("Invalid trigger format");
            if(definition.op==Op::unpack && (definition.formats.size()<2 || definition.formats.size()>Message::capacity))
                throw std::invalid_argument("Invalid unpack outlets");
            for(auto format:definition.formats)
                if(definition.op==Op::unpack && format!=Format::integer && format!=Format::floating)
                    throw std::invalid_argument("unpack symbol outlets are not supported");
            if((definition.op==Op::route || definition.op==Op::select) && definition.atoms.empty()) throw std::invalid_argument("Missing route/select keys");
            if(!definition.substitutions.empty() && (definition.op!=Op::message || definition.substitutions.size()!=definition.atoms.size())) throw std::invalid_argument("Invalid message substitutions");
            for(int slot:definition.substitutions) if(slot< -1 || slot>=Message::capacity) throw std::invalid_argument("Invalid message placeholder");
            if(!definition.separators.empty() && (definition.op!=Op::message || definition.separators.size()!=definition.atoms.size()))throw std::invalid_argument("Invalid message separators");
            for(int separator:definition.separators)if(separator<0 || separator>2)throw std::invalid_argument("Invalid message separator kind");
            if((definition.op==Op::namedSend || definition.op==Op::namedReceive) &&
               (definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol || symbols_.name(definition.atoms[0].value.symbol).empty()))
                throw std::invalid_argument("Named routing requires one nonempty prepared symbol");
            Node node; node.definition = definition;
            if(definition.op==Op::expression){
                node.expression=std::make_unique<Expression>(definition.expression);
                if(definition.arguments.size()!=1 || definition.arguments[0]!=node.expression->inlets() || !definition.atoms.empty())
                    throw std::invalid_argument("Invalid expr inlet definition");
            }
            if(definition.op==Op::conditional) {
                // if <expr> then <number> [else <number>]: the condition is a Max
                // expr; arguments are [inlets, then, hasElse, else]. Only literal
                // numeric branches are prepared; message branches are rejected.
                if(definition.arguments.size()!=4 || definition.expression.empty())throw std::invalid_argument("Invalid if definition");
                node.expression=std::make_unique<Expression>(definition.expression);
                if(node.expression->inlets()>int(definition.arguments[0]))throw std::invalid_argument("if inlet count disagrees with its condition");
            }
            if(definition.op==Op::dspState)node.dspState=std::make_unique<DSPState>(sampleRate,ioVector);
            if(definition.op==Op::signalSnapshot)node.snapshot=std::make_unique<SignalSnapshot>(definition.arguments[0],int(definition.arguments[1]),definition.arguments[2]!=0,sampleRate);
            if(definition.op==Op::pfft) {
                const auto& spec=definition.spectral;
                if(!spec || spec->size<16 || spec->size>65536 || (spec->size&(spec->size-1)) || spec->overlap<1 || spec->overlap>32 ||
                   spec->size%spec->overlap!=0 || spec->inlets<1 || spec->inlets>8 || spec->outlets<0 || spec->outlets>8 || spec->definitions.empty())
                    throw std::invalid_argument("pfft~ needs a power-of-two frame size, an overlap that divides it and 1-8 inlets/0-8 outlets");
                node.spectral=std::make_unique<SpectralHost>(spec->size,spec->overlap,spec->inlets,spec->outlets);
                node.spectral->prepare();
                for(int copy=0;copy<1;++copy) {   // one shared instance (MEASURED), not one per overlap
                    auto child=std::make_unique<Runtime>(spec->definitions,spec->edges,sampleRate,symbols_,nullptr,nullptr,std::vector<int>{},routing_,spec->size);
                    for(const auto& port:child->spectralInputs())if(port.port<0 || port.port>=spec->inlets)throw std::invalid_argument("fftin~ inlet exceeds the pfft~ inlet count");
                    for(const auto& port:child->spectralOutputs())if(port.port<0 || port.port>=spec->outlets)throw std::invalid_argument("fftout~ outlet exceeds the pfft~ outlet count");
                    for(const auto& d:spec->definitions)if(d.op==Op::pfft || d.op==Op::input || d.op==Op::output || d.op==Op::dial)
                        throw std::invalid_argument("Nested pfft~, plugin~/plugout~ or parameters inside a spectral subpatch need support");
                    node.spectral->copies.push_back(std::move(child));
                }
            }
            if(definition.op==Op::polyIn || definition.op==Op::polyOut) {
                // Inside an oversampled poly~ the ports read/write host frames
                // (ioVector = factor); inline they are plain pass-throughs.
                FrameIO io;io.port=int(definition.arguments[0]);io.real.assign(size_t(ioVector),0.);io.imag.clear();
                auto& slots=definition.op==Op::polyIn?spectralIn_:spectralOut_;
                node.spectralSlot=int(slots.size());slots.push_back(std::move(io));
            }
            if(definition.op==Op::fftIn || definition.op==Op::fftOut) {
                // arguments: [port (0-based), window]; frames are ioVector long
                // because the enclosing host renders one frame per call.
                if(definition.arguments.size()!=2 || definition.arguments[0]<0 || definition.arguments[0]>7 || definition.arguments[1]<0 || definition.arguments[1]>4)
                    throw std::invalid_argument("fftin~/fftout~ need a port index and a window");
                FrameIO io;io.port=int(definition.arguments[0]);io.window=SpectralWindow(int(definition.arguments[1]));
                io.real.assign(size_t(ioVector),0.);io.imag.assign(size_t(ioVector),0.);
                auto& slots=definition.op==Op::fftIn?spectralIn_:spectralOut_;
                node.spectralSlot=int(slots.size());slots.push_back(std::move(io));
            }
            if(definition.op==Op::poke) {
                // poke~ <buffer> [channel]: channel is 1-based like peek~'s
                // argument (default 1); UNMEASURED beyond the documentation.
                if(definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol || definition.arguments.size()>1)
                    throw std::invalid_argument("poke~ needs a buffer name and at most a channel");
                const double channel=definition.arguments.empty()?1:definition.arguments[0];
                if(channel<1 || channel>64 || std::trunc(channel)!=channel)throw std::invalid_argument("poke~ channel out of range");
                const auto found=routing_->buffers().find(symbols_.name(definition.atoms[0].value.symbol));
                if(found==routing_->buffers().end())throw std::invalid_argument("poke~ buffer is not declared in this device");
                node.pokeTable=found->second;node.values[2]=channel-1;
            }
            if(definition.op==Op::polyIn || definition.op==Op::polyOut) {
                // in~/out~ <n>: arguments [port-1, group members...]. Only in~ 1
                // (port 0) may carry a mute group.
                if(definition.arguments.empty() || definition.arguments[0]<0 || definition.arguments[0]>15 || std::trunc(definition.arguments[0])!=definition.arguments[0])
                    throw std::invalid_argument("in~/out~ need a port index");
                if(definition.arguments.size()>1 && (definition.op!=Op::polyIn || definition.arguments[0]!=0))throw std::invalid_argument("Only in~ 1 owns a poly~ mute group");
                for(size_t i=1;i<definition.arguments.size();++i)
                    if(definition.arguments[i]<0 || definition.arguments[i]>=double(definitions.size()) || std::trunc(definition.arguments[i])!=definition.arguments[i])
                        throw std::invalid_argument("poly~ mute group index out of range");
            }
            if(definition.op==Op::indexSignal) {
                // index~ <buffer> [channel]: sample at the truncated signal
                // index, no interpolation, 0 outside the buffer. The channel
                // argument is taken as 1-based like peek~/poke~ (doc-only).
                if(definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol || definition.arguments.size()>1)
                    throw std::invalid_argument("index~ needs a buffer name and at most a channel");
                const double channel=definition.arguments.empty()?1:definition.arguments[0];
                if(channel<1 || channel>64 || std::trunc(channel)!=channel)throw std::invalid_argument("index~ channel out of range");
                const auto found=routing_->buffers().find(symbols_.name(definition.atoms[0].value.symbol));
                if(found==routing_->buffers().end())throw std::invalid_argument("index~ buffer is not declared in this device");
                node.pokeTable=found->second;node.values[1]=channel-1;
            }
            if(definition.op==Op::randomInt) {
                if(definition.arguments.size()>1 || (definition.arguments.size()==1 && (definition.arguments[0]<0 || definition.arguments[0]>2147483647 || std::trunc(definition.arguments[0])!=definition.arguments[0])))
                    throw std::invalid_argument("random needs an integer range");
                node.values[1]=definition.arguments.empty()?1:definition.arguments[0];
                node.rng^=uint64_t(nodes_.size()+1)*0x9E3779B97F4A7C15ull;
            }
            if(definition.op==Op::pipe) {
                // pipe [delay]: one numeric delay argument (its type fixes the
                // output type); scheduling uses the runtime's delay clock.
                if(definition.arguments.size()>1 || (definition.arguments.size()==1 && (definition.arguments[0]<0 || definition.arguments[0]>3600000)))
                    throw std::invalid_argument("pipe needs at most one delay in ms");
                node.time=definition.arguments.empty()?0:definition.arguments[0];
            }
            if(definition.op==Op::metro) {
                // metro <ms> or metro <notevalue>: atoms[0] symbol = note value
                // (arguments[0] = its length in beats), else arguments[0] = ms.
                if(definition.arguments.size()!=1 || definition.arguments[0]<=0 || definition.arguments[0]>3600000)throw std::invalid_argument("metro needs a positive interval");
                node.time=definition.arguments[0];node.values[1]=definition.atoms.empty()?0:1;
            }
            if(definition.op==Op::translate) {
                if(definition.atoms.size()!=2)throw std::invalid_argument("translate needs source and destination units");
            }
            if(definition.op==Op::accum) {
                if(definition.arguments.size()>1)throw std::invalid_argument("accum takes at most an initial value");
                node.stored[0]=definition.atoms.empty()?Atom::integral(0):definition.atoms[0];
            }
            if(definition.op==Op::reverseDivide) {
                if(definition.atoms.size()!=1 || definition.atoms[0].type==Atom::Type::symbol)throw std::invalid_argument("!/ needs a numeric argument");
                node.stored[1]=definition.atoms[0];
            }
            if(definition.op==Op::split) {
                if(definition.atoms.size()!=2 || definition.atoms[0].type==Atom::Type::symbol || definition.atoms[1].type==Atom::Type::symbol)throw std::invalid_argument("split needs low and high arguments");
            }
            if(definition.op==Op::switchGate) {
                if(definition.arguments.size()<1 || definition.arguments.size()>2 || definition.arguments[0]<1 || definition.arguments[0]>32 || std::trunc(definition.arguments[0])!=definition.arguments[0])
                    throw std::invalid_argument("switch needs an inlet count of 1..32");
                node.values[0]=definition.arguments.size()==2?definition.arguments[1]:0;
            }
            if(definition.op==Op::ctlIn) {
                if(definition.arguments.size()>2 || (definition.arguments.size()>=1 && (definition.arguments[0]<0 || definition.arguments[0]>127)))throw std::invalid_argument("ctlin controller out of range");
                if(definition.arguments.size()==2)throw std::invalid_argument("ctlin channel filter needs support");
            }
            if(definition.op==Op::noteIn && !definition.arguments.empty())throw std::invalid_argument("notein channel filter needs support");
            if(definition.op==Op::noteIn || definition.op==Op::ctlIn || definition.op==Op::mpeParse) {hasMidiIn_=true;midiInNodes_.push_back(int(nodes_.size()));}
            if(definition.op==Op::mpeParse) {
                // mpeparse [@hires N]: arguments [hires]; only 0 and 1 are modelled.
                if(definition.arguments.size()>1 || (definition.arguments.size()==1 && definition.arguments[0]!=0 && definition.arguments[0]!=1))throw std::invalid_argument("mpeparse hires mode needs support");
            }
            if(definition.op==Op::bufferInfo) {
                if(definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol)throw std::invalid_argument("info~ needs a buffer name");
                const auto found=routing_->buffers().find(symbols_.name(definition.atoms[0].value.symbol));
                if(found==routing_->buffers().end())throw std::invalid_argument("info~ buffer is not declared in this device");
                node.pokeTable=found->second;
            }
            if(definition.op==Op::adsr) {
                // live.adsr~ <attack ms> <decay ms> <sustain 0-1> <release ms>
                // (MEASURED in Live: ms arguments, sustain a level, trigger 1/0).
                if(definition.arguments.size()!=4 || definition.arguments[0]<0 || definition.arguments[1]<0 || definition.arguments[2]<0 || definition.arguments[2]>1 || definition.arguments[3]<0)
                    throw std::invalid_argument("live.adsr~ needs attack, decay, sustain level and release");
                for(int i=0;i<4;++i)node.values[size_t(i)+1]=definition.arguments[size_t(i)];
                node.values[5]=0;   // stage: 0 idle, 1 attack, 2 decay, 3 sustain, 4 release
            }
            if(definition.op==Op::coll) {
                // coll [name]: a bounded in-memory collection (no file I/O);
                // 1024 entries of up to 32 atoms, allocated here, never in render.
                if(definition.atoms.size()>1)throw std::invalid_argument("coll takes at most a name");
                node.entries.resize(1024);
            }
            if(definition.op==Op::tapIn) {
                // tapin~ <ms>: a delay line of that many milliseconds (plus one
                // vector of headroom); the outlet carries only the link.
                if(definition.arguments.size()!=1 || definition.arguments[0]<=0 || definition.arguments[0]>60000)throw std::invalid_argument("tapin~ needs a delay length in ms (0..60000)");
                node.ring.assign(size_t(std::ceil(definition.arguments[0]*sampleRate/1000.))+kTapMinimumDelay+1,0.);
            }
            if(definition.op==Op::tapOut) {
                // tapout~ <ms...>: one tap per argument; each delay comes from
                // its inlet (signal or float) and is clamped to Max's minimum
                // of one signal vector (64 samples: MEASURED, Live runs M4L at
                // sigvs 64 / iovs 64). Fractional delays truncate to whole
                // samples (MEASURED: no interpolation).
                if(definition.arguments.empty() || definition.arguments.size()>16)throw std::invalid_argument("tapout~ needs 1..16 taps");
                for(size_t i=0;i<definition.arguments.size();++i) {if(definition.arguments[i]<0)throw std::invalid_argument("tapout~ delay must be positive");node.values[i]=definition.arguments[i];}
            }
            if(definition.op==Op::randSignal) {
                // rand~ <hz>: a new uniform target in [-1, 1) every SR/hz
                // samples, linearly interpolated. Not Max's generator.
                if(definition.arguments.size()!=1 || !(definition.arguments[0]>0) || definition.arguments[0]>sampleRate)throw std::invalid_argument("rand~ needs a positive rate");
                node.values[1]=definition.arguments[0];node.rng^=uint64_t(nodes_.size()+7)*0x9E3779B97F4A7C15ull;
                node.remaining=0;node.target=0;node.values[0]=0;
            }
            if(definition.op==Op::overdrive) {
                if(definition.arguments.size()>1 || (definition.arguments.size()==1 && !(definition.arguments[0]>0)))throw std::invalid_argument("overdrive~ takes one positive drive");
                node.values[1]=definition.arguments.empty()?1:definition.arguments[0];
            }
            if(definition.op==Op::degrade) {
                if(definition.arguments.size()!=2 || definition.arguments[0]<0 || definition.arguments[0]>1 || definition.arguments[1]<1 || definition.arguments[1]>24)throw std::invalid_argument("degrade~ needs a ratio 0..1 and 1..24 bits");
                node.values[1]=definition.arguments[0];node.values[2]=definition.arguments[1];node.values[3]=0;
            }
            if(definition.op==Op::polyUp) {
                // poly~ ... up N: the subpatch runs in its own Runtime at N times
                // the sample rate between Max's measured polyphase-allpass
                // half-band resamplers (see SpectralHost::HalfBand).
                const auto& spec=definition.spectral;
                if(!spec || spec->size<2 || spec->size>8 || spec->inlets<1 || spec->inlets>8 || spec->outlets<1 || spec->outlets>8 || spec->definitions.empty())
                    throw std::invalid_argument("poly~ up needs a factor of 2..8 and 1-8 in~/out~ ports");
                node.spectral=std::make_unique<SpectralHost>(spec->size,1,spec->inlets,spec->outlets,true);
                auto child=std::make_unique<Runtime>(spec->definitions,spec->edges,sampleRate*spec->size,symbols_,nullptr,nullptr,std::vector<int>{},routing_,spec->size);
                for(const auto& d:spec->definitions)if(d.op==Op::pfft || d.op==Op::polyUp || d.op==Op::input || d.op==Op::output || d.op==Op::dial)
                    throw std::invalid_argument("Nested poly~/pfft~, plugin~/plugout~ or parameters inside an oversampled poly~ need support");
                node.spectral->copies.push_back(std::move(child));
            }
            if(definition.op==Op::peek) {
                // peek~ <buffer> [channel]: an 'index value' list writes, an
                // index alone reads (outlet 0). Channel 1-based, default 1.
                if(definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol || definition.arguments.size()>1)
                    throw std::invalid_argument("peek~ needs a buffer name and at most a channel");
                // A channel the buffer does not have clamps (MEASURED on a mono
                // buffer: peek~ m 3 and peek~ m 8 read and write channel 1;
                // clamping to the last channel of a multichannel buffer is the
                // UNMEASURED generalisation). Gen's peek()/sample() return 0 instead.
                const double channel=definition.arguments.empty()?1:definition.arguments[0];
                if(channel<1 || channel>64 || std::trunc(channel)!=channel)throw std::invalid_argument("peek~ channel out of range");
                const auto found=routing_->buffers().find(symbols_.name(definition.atoms[0].value.symbol));
                if(found==routing_->buffers().end())throw std::invalid_argument("peek~ buffer is not declared in this device");
                node.pokeTable=found->second;node.values[2]=channel-1;
            }
            if(definition.op==Op::functionCurve) {
                // function: arguments [domain, range low, range high, mode];
                // atoms carry the saved points as x y curve triples. Curve
                // shape in mode 1 follows the runtime's classic-curve model
                // (calibration against Max pending); linear when curve == 0.
                if(definition.arguments.size()!=4 || !(definition.arguments[0]>0) || definition.arguments[1]>=definition.arguments[2])throw std::invalid_argument("function needs domain, range and mode");
                if(definition.atoms.size()%3!=0 || definition.atoms.size()>3*256)throw std::invalid_argument("function points must be x y curve triples");
                node.points.reserve(256);
                for(size_t i=0;i+2<definition.atoms.size();i+=3)
                    functionAdd(node,definition.atoms[i].number(),definition.atoms[i+1].number(),definition.atoms[i+2].number());
                node.values[0]=0;
                if(!functionPoints_) {functionPoints_=symbols_.intern("points");functionSetcurve_=symbols_.intern("setcurve");}
            }
            if(definition.op==Op::liveDrop) {
                if(!definition.arguments.empty() || !definition.atoms.empty())throw std::invalid_argument("live.drop takes no constructor arguments");
                if(!dropPath_) {dropPath_=symbols_.intern("path");dropLegend_=symbols_.intern("legend");dropClear_=symbols_.intern("clear");}
                node.hasHeld=false;
            }
            if(definition.op==Op::fzero) {
                // fzero~ [@size @period @freqmin @freqmax @threshold @onsetpitch
                // @onsetamp @onsetperiod @onsetlist @quiet]: arguments carry the
                // ten attribute values in that order (defaults from the external).
                if(definition.arguments.size()!=10)throw std::invalid_argument("fzero~ needs its ten attribute values");
                const auto& a=definition.arguments;
                for(double v:a)if(!std::isfinite(v))throw std::invalid_argument("fzero~ attribute values must be finite");
                node.fzero=std::make_unique<FZero>(sampleRate,64);
                node.fzero->setSize(int64_t(a[0]));node.fzero->setPeriod(int64_t(a[1]));node.fzero->setFreqMin(int64_t(a[2]));
                if(!node.fzero->setFreqMax(int64_t(a[3])))throw std::invalid_argument("fzero~: Maximum frequency must be greater than minimum frequency.");
                node.fzero->setThreshold(a[4]);node.fzero->setOnsetPitch(a[5]);node.fzero->setOnsetAmp(a[6]);
                node.fzero->setOnsetPeriod(int64_t(a[7]));node.fzero->setOnsetList(a[8]!=0);node.fzero->setQuiet(a[9]!=0);
            }
            if(definition.op==Op::loudness) {
                // loudness~ <channels> [@interval ms]: arguments [channels, interval].
                // Outlets (Max 9 refpage): 0 momentary LUFS, 1 short-term LUFS,
                // 2 integrated LUFS, 3 loudness range LU, 4 sample peak dB,
                // 5 true peak dB (oversampling factor unstated; 4x here).
                // 'reset' clears the integrated and peak calculations only.
                // Silence reports a -120 floor rather than Max's -inf, because
                // messages here cannot carry non-finite atoms (known deviation).
                if(definition.arguments.size()!=2 || definition.arguments[0]<1 || definition.arguments[0]>8 || definition.arguments[1]<10 || definition.arguments[1]>10000)
                    throw std::invalid_argument("loudness~ needs 1..8 channels and an interval of 10..10000 ms");
                node.loudness=std::make_unique<LoudnessMeter>(sampleRate,int(definition.arguments[0]));node.loudness->reset();
                node.remaining=0;
            }
            if(definition.op==Op::filterCoeff) {
                // filtercoeff~ <type>: arguments [type index, resamp]; inlets
                // frequency, gain (LINEAR amplitude), Q (signals or floats).
                // RBJ cookbook with A = sqrt(gain), outputs normalised by a0:
                // MEASURED in Live 12.4.5 (peaknotch 1000 Hz, gain 2, Q 1 at
                // 44.1 k matches to 5e-8; treating gain as dB is 3e-2 off).
                if(definition.arguments.size()!=2 || definition.arguments[0]<0 || definition.arguments[0]>8 || definition.arguments[1]<1 || definition.arguments[1]>65536)
                    throw std::invalid_argument("filtercoeff~ needs a type and a resample count");
                node.filterType=int(definition.arguments[0]);
                node.values[0]=1000;node.values[1]=1;node.values[2]=1;   // defaults until the inlets speak (unmeasured)
            }
            if(definition.op==Op::biquad) {
                // biquad~ [a0 a1 a2 b1 b2]: y = a0 x + a1 x1 + a2 x2 - b1 y1 - b2 y2.
                if(definition.arguments.size()!=0 && definition.arguments.size()!=5)throw std::invalid_argument("biquad~ takes five coefficients or none");
                for(size_t i=0;i<5;++i)node.values[i+1]=definition.arguments.size()==5?definition.arguments[i]:(i==0?1:0);
            }
            if((definition.op==Op::sendSignal || definition.op==Op::receiveSignal) && (definition.atoms.size()!=1 || definition.atoms[0].type!=Atom::Type::symbol))
                throw std::invalid_argument("send~/receive~ need a name");
            if(definition.op==Op::scope) {
                // arguments: [mode (0 scope~, 1 spectroscope~), bufsize, calccount, fftsize, interval ms].
                // scope~: every calccount samples the CURRENT sample of each
                // inlet becomes one point (Max's per-point reduction is NOT
                // measured); bufsize points make a frame. spectroscope~: hann
                // window, raw magnitudes scaled 2/N, published every interval.
                if(definition.arguments.size()!=5)throw std::invalid_argument("scope needs mode, bufsize, calccount, fftsize and interval");
                const double mode=definition.arguments[0],bufsize=definition.arguments[1],calccount=definition.arguments[2],fftsize=definition.arguments[3],interval=definition.arguments[4];
                if((mode!=0 && mode!=1) || bufsize<1 || bufsize>4096 || calccount<1 || calccount>65536 || fftsize<16 || fftsize>16384 || (size_t(fftsize)&(size_t(fftsize)-1)) || interval<1 || interval>10000)
                    throw std::invalid_argument("scope attributes out of range");
                node.frameSeq=std::make_unique<std::atomic<uint32_t>>(0);
                if(mode==0) {node.frame.assign(size_t(bufsize)*2,0.f);node.frameWork.assign(size_t(bufsize)*2,0.f);}
                else {node.frame.assign(size_t(fftsize)/2,0.f);node.ring.assign(size_t(fftsize),0.);node.fftRe.assign(size_t(fftsize),0.);node.fftIm.assign(size_t(fftsize),0.);node.spectralFFT=std::make_unique<FFT>(size_t(fftsize));}
            }
            if(definition.op==Op::clipSignal) {
                if(definition.arguments.size()>2)throw std::invalid_argument("clip~ takes at most low and high arguments");
                node.values[1]=definition.arguments.size()>0?definition.arguments[0]:0;
                node.values[2]=definition.arguments.size()>1?definition.arguments[1]:0;
            }
            node.signalOutlet=signalOutput(definition.op);
            node.substitutions.fill(-1);std::copy(definition.substitutions.begin(),definition.substitutions.end(),node.substitutions.begin());
            std::copy(definition.separators.begin(),definition.separators.end(),node.separators.begin());
            node.storedCount=int(definition.atoms.size());std::copy(definition.atoms.begin(),definition.atoms.end(),node.stored.begin());
            if(definition.op==Op::split) {node.stored[1]=definition.atoms[0];node.stored[2]=definition.atoms[1];}   // bounds live in slots 1-2 (after the atom copy)
            if ((definition.op == Op::pack || definition.op==Op::pak) && definition.atoms.empty()) {
                node.storedCount=int(definition.arguments.size());
                for(int i=0;i<node.storedCount;++i) {
                    bool valid=true;node.stored[i]=Atom::real(definition.arguments[i]).converted(definition.integers[i]?Atom::Type::integer:Atom::Type::floating,valid);
                    if(!valid)throw std::invalid_argument("Integer argument overflows");
                }
            }
            if(definition.op==Op::integer || definition.op==Op::floating) {
                bool valid=true;node.stored[0]=(definition.atoms.empty()?Atom::integral(0):definition.atoms[0]).converted(definition.op==Op::integer?Atom::Type::integer:Atom::Type::floating,valid);
                if(!valid)throw std::invalid_argument("Invalid number state");node.storedCount=1;
            }
            if(definition.op>=Op::controlAdd && definition.op<=Op::reverseSubtract) {
                node.stored[1]=definition.atoms.empty()?Atom::integral(0):definition.atoms[0];
                if(!node.stored[1].numeric())throw std::invalid_argument("Non-numeric arithmetic argument");
                node.stored[0]=node.stored[1].type==Atom::Type::integer?Atom::integral(0):Atom::real(0);node.storedCount=2;
            }
            if((definition.op>=Op::compareEqual && definition.op<=Op::compareLessEqual) || definition.op==Op::controlMaximum || definition.op==Op::controlMinimum) {
                node.stored[1]=definition.atoms.empty()?Atom::integral(0):definition.atoms[0];
                if(!node.stored[1].numeric())throw std::invalid_argument("Non-numeric comparison argument");
                node.stored[0]=node.stored[1].type==Atom::Type::integer?Atom::integral(0):Atom::real(0);node.storedCount=2;
            }
            if(definition.op==Op::controlModulo) {
                node.stored[1]=definition.atoms.empty()?Atom::integral(0):definition.atoms[0];
                if(node.stored[1].type!=Atom::Type::integer)throw std::invalid_argument("Only integer modulo is supported");
                node.stored[0]=Atom::integral(0);node.storedCount=2;
            }
            if(definition.op==Op::clip || definition.op==Op::scale) {
                const size_t needed=definition.op==Op::clip?2u:4u;
                if(definition.atoms.size()!=needed)throw std::invalid_argument("clip/scale argument count");
                const auto type=definition.op==Op::scale?Atom::Type::floating:definition.atoms[0].type;
                node.stored[0]=type==Atom::Type::integer?Atom::integral(0):Atom::real(0);
                for(size_t i=0;i<needed;++i) {
                    if(!definition.atoms[i].numeric())throw std::invalid_argument("Non-numeric clip/scale argument");
                    if(definition.op==Op::clip && definition.atoms[i].type!=type)throw std::invalid_argument("Mixed clip bound types");
                    node.stored[i+1]=definition.op==Op::scale?Atom::real(definition.atoms[i].number()):definition.atoms[i];
                }
                if(definition.op==Op::clip && node.stored[1].number()>node.stored[2].number())throw std::invalid_argument("Inverted clip bounds");
                node.storedCount=int(needed)+1;
            }
            if(definition.op==Op::peakAmp) {
                if(definition.arguments.size()!=1 || !std::isfinite(definition.arguments[0]) || definition.arguments[0]<=0 || definition.arguments[0]>60000.)
                    throw std::invalid_argument("peakamp~ needs a positive interval in milliseconds");
                node.time=definition.arguments[0];hasPeakAmp_=true;
            }
            if(definition.op==Op::transport && (!definition.arguments.empty() || !definition.atoms.empty()))
                throw std::invalid_argument("transport arguments need support");
            if(definition.op==Op::averageSignal) {
                // average~ <window> absolute: only the absolute mode is modelled.
                if(definition.arguments.size()!=1 || definition.arguments[0]<1 || definition.arguments[0]>1048576 || std::trunc(definition.arguments[0])!=definition.arguments[0])
                    throw std::invalid_argument("average~ needs an integer window of 1..1048576 samples");
                node.ring.assign(size_t(definition.arguments[0]),0.);
            }
            if(definition.op==Op::onePole) {
                // onepole~ <fc>: MEASURED in Live 12.4.5 (max4liveplugins batch4
                // probe, step via line~, tau within 0.1%): a1 = exp(-2*pi*fc/SR),
                // y = (1-a1)*x + a1*y1. The frequency is fixed at construction;
                // the right inlet accepts a float to change it.
                // No argument: MEASURED (Live, September 11) a bare onepole~
                // reaches 0.9876 of a unit step after 700 ms, i.e. a1 =
                // 0.99985783 -> fc = 0.998 Hz: the default is 1 Hz, not 0.
                if(definition.arguments.size()>1 || (definition.arguments.size()==1 && (!std::isfinite(definition.arguments[0]) || definition.arguments[0]<0 || definition.arguments[0]>sampleRate*0.5)))
                    throw std::invalid_argument("onepole~ needs at most one cutoff frequency in 0..Nyquist");
                const double fc=definition.arguments.empty()?1:definition.arguments[0];
                node.values[1]=fc;node.step=std::exp(-2*M_PI*fc/sampleRate);
            }
            if(definition.op==Op::sprintf) {
                if(definition.atoms.empty() || definition.atoms.size()!=definition.arguments.size() || definition.atoms.size()>Message::capacity)
                    throw std::invalid_argument("sprintf format tokens and slot codes disagree");
                for(size_t i=0;i<definition.atoms.size();++i) {
                    const double code=definition.arguments[i];
                    if(std::trunc(code)!=code || code<0 || code>3+32)throw std::invalid_argument("sprintf conversion needs support");
                    if(code==0 && definition.atoms[i].type!=Atom::Type::symbol)throw std::invalid_argument("sprintf literal token must be a symbol");
                }
                if(sprintfConversions(definition)>32)throw std::invalid_argument("sprintf conversion count exceeds budget");
                // Slots start empty (0); stored[] holds one Atom per slot.
                for(auto& a:node.stored)a=Atom::integral(0);
                node.storedCount=sprintfConversions(definition);
            }
            if(definition.op==Op::zlGroup) {
                if(definition.arguments.size()!=1 || definition.arguments[0]<1 || definition.arguments[0]>Message::capacity)
                    throw std::invalid_argument("zl group size must be 1..capacity");
                node.stored[0]=Atom::integral(int64_t(definition.arguments[0]));node.storedCount=1;   // group size; collected atoms follow
            }
            if(definition.op==Op::speedlim) {
                if(definition.arguments.size()>1)throw std::invalid_argument("speedlim takes one interval");
                node.time=definition.arguments.empty()?0:definition.arguments[0];
                if(!std::isfinite(node.time) || node.time<0 || node.time>3600000.)throw std::invalid_argument("Invalid speedlim interval");
            }
            if(definition.op==Op::counter) {
                // arguments: [direction] minimum maximum, prepared by the
                // compiler. stored[0]=count, stored[1]=minimum, stored[2]=maximum.
                if(definition.arguments.size()!=3 || definition.arguments[0]!=0 || definition.arguments[1]>definition.arguments[2])
                    throw std::invalid_argument("Only an upward counter with minimum<=maximum is supported");
                node.stored[0]=Atom::integral(int64_t(definition.arguments[1]));node.stored[1]=node.stored[0];
                node.stored[2]=Atom::integral(int64_t(definition.arguments[2]));node.storedCount=3;
            }
            if(definition.op==Op::liveRemote) {
                if(!definition.arguments.empty() || !definition.atoms.empty())throw std::invalid_argument("live.remote~ arguments need support");
                if(!mappedSymbol_)mappedSymbol_=symbols_.intern("mapped");
            }
            if(definition.op==Op::inert) {
                // Objects whose only sources are host facilities the phone
                // lacks (file drop, file dialog, pattr storage): their outlets
                // exist for the cords but never fire, and input is dropped.
                // arguments: [outlets] or [outlets, inlets] (a dead js/expr keeps its saved port counts).
                if(definition.arguments.empty() || definition.arguments.size()>2 || definition.arguments[0]<0 || definition.arguments[0]>32 || (definition.arguments.size()==2 && (definition.arguments[1]<0 || definition.arguments[1]>32)))throw std::invalid_argument("inert outlet count");
            }
            if(definition.op==Op::midiIn) {
                if(!definition.arguments.empty() || !definition.atoms.empty())throw std::invalid_argument("midiin takes no arguments");
                hasMidiIn_=true;midiInNodes_.push_back(int(nodes_.size()));
            }
            if(definition.op==Op::modalExternal) {
                if(!definition.arguments.empty() || !definition.atoms.empty())throw std::invalid_argument("modal external takes no arguments");
                node.modal=std::make_unique<m4l::modal::Engine>();node.modal->prepare(sampleRate);hasModal_=true;
                if(!modalStatus_) {modalStatus_=symbols_.intern("status");modalMeter_=symbols_.intern("meter");modalModel_=symbols_.intern("model");modalUnsupported_=symbols_.intern("Capture and analysis are not hosted on this device");}
            }
            if(definition.op==Op::uzi) {
                // uzi [count] [offset]: stored[0]=count, stored[1]=index offset.
                if(definition.arguments.size()!=2 || definition.arguments[0]<0 || definition.arguments[0]>1048576)throw std::invalid_argument("uzi count must be 0..1048576");
                node.stored[0]=Atom::integral(int64_t(definition.arguments[0]));node.stored[1]=Atom::integral(int64_t(definition.arguments[1]));node.storedCount=2;
            }
            if(definition.op==Op::spray) {
                // spray <outlets> [offset]: arguments prepared by the compiler.
                if(definition.arguments.size()!=2 || definition.arguments[0]<1 || definition.arguments[0]>128)
                    throw std::invalid_argument("spray needs 1..128 outlets");
            }
            if(definition.op==Op::gate) {
                const int outlets=definition.arguments.empty()?1:int(definition.arguments[0]);
                const int initial=definition.arguments.size()>1?int(definition.arguments[1]):0;
                if(definition.arguments.size()>2 || outlets<1 || outlets>128 || initial<0 || initial>outlets)
                    throw std::invalid_argument("Invalid gate outlet count or initial state");
                node.stored[0]=Atom::integral(initial);node.storedCount=1;
            }
            if(definition.op==Op::change) {
                // No argument means integers; a float argument means floats.
                // The argument is also the initial comparison value, so an
                // initial 0 followed by an input 0 produces no output, as in Max.
                if(definition.atoms.size()>1)throw std::invalid_argument("change takes at most one argument");
                node.stored[0]=definition.atoms.empty()?Atom::integral(0):definition.atoms[0];
                if(!node.stored[0].numeric())throw std::invalid_argument("Non-numeric change argument");
                node.storedCount=1;
            }
            if(definition.op==Op::plugSync){if(!definition.atoms.empty() || !definition.arguments.empty())throw std::invalid_argument("plugsync~ takes no arguments");hasPlugSync_=true;}
            if(definition.op==Op::adStatus && (!definition.atoms.empty() || !definition.arguments.empty()))
                throw std::invalid_argument("Only the prepared adstatus property is supported");
            if(definition.op==Op::delay) node.time=definition.arguments.empty()?0:definition.arguments[0];
            if (definition.op == Op::multiply || definition.op == Op::add || definition.op == Op::subtract || definition.op == Op::reverseSubtractSignal)
                node.values[1] = definition.arguments.empty() ? 0 : definition.arguments[0];
            else node.values[0] = definition.arguments.empty() ? definition.initial : definition.arguments[0];
            if(definition.op==Op::dial && definition.parameterType!=0)node.values[0]=std::clamp(std::round(node.values[0]),definition.minimum,definition.maximum);
            if(definition.op==Op::gen) {
                if(!definition.genGraph)throw std::invalid_argument("Missing original Gen graph");
                node.gen=std::make_unique<m4l::gen::Graph>(*definition.genGraph,sampleRate,0,nullptr,&routing_->buffers());
                node.definition.genInputs=node.gen->inputs();node.definition.genOutputs=node.gen->outputs();
            }
            node.output.resize(definition.op==Op::gen?node.definition.genOutputs:std::max(2,definition.op==Op::fftIn || definition.op==Op::pfft || definition.op==Op::tapOut || definition.op==Op::filterCoeff || definition.op==Op::polyUp?outletCount(definition):2),0);
            node.signalInputs.resize(definition.op==Op::gen?std::max(1,node.definition.genInputs):(definition.op==Op::signalSelector || definition.op==Op::signalRecord || definition.op==Op::pfft || definition.op==Op::poke || definition.op==Op::clipSignal || definition.op==Op::indexSignal || definition.op==Op::tapOut || definition.op==Op::biquad || definition.op==Op::filterCoeff || definition.op==Op::loudness || definition.op==Op::degrade || definition.op==Op::polyUp)?std::max(1,inletCount(definition)):2);
            if(definition.op==Op::signalRecord)node.values.fill(0);
            nodes_.push_back(std::move(node));
            if(definition.op==Op::dial) parameterNodes_.push_back(int(nodes_.size()-1));
            if(definition.op==Op::liveRemote) liveRemoteNodes_.push_back(int(nodes_.size()-1));
        }
        std::vector<int> degrees(nodes_.size());
        std::vector<std::vector<int>> downstream(nodes_.size());
        // Patcher inlets/outlets preserve both messages and signals. Infer
        // connected signal paths through any number of boundaries, before
        // assigning DSP edges. A control-only boundary must not introduce a
        // zero-valued signal connection that masks a downstream numeric inlet.
        for (const auto& e : edges)
            if(e.source<0 || e.destination<0 || size_t(e.source)>=nodes_.size() || size_t(e.destination)>=nodes_.size())
                throw std::invalid_argument("Invalid boundary endpoint");
        bool changed=true;
        while(changed) {
            changed=false;
            for(const auto& e:edges) if(nodes_[e.source].signalOutlet && nodes_[e.destination].definition.op==Op::boundary && !nodes_[e.destination].signalOutlet) {
                nodes_[e.destination].signalOutlet=true;changed=true;
            }
        }
        // send~/receive~: pair by name inside this graph; a receive~ repeats
        // its send~'s current sample, so the pair is a scheduling edge.
        std::vector<Edge> edgesWithBuses(edges);
        for(size_t r=0;r<nodes_.size();++r)if(nodes_[r].definition.op==Op::receiveSignal) {
            const Symbol name=nodes_[r].definition.atoms[0].value.symbol;int found=-1;
            for(size_t sIdx=0;sIdx<nodes_.size();++sIdx)if(nodes_[sIdx].definition.op==Op::sendSignal && nodes_[sIdx].definition.atoms[0].value.symbol==name) {
                if(found>=0)throw std::invalid_argument("send~ name used twice in one device");found=int(sIdx);
            }
            if(found<0)throw std::invalid_argument("receive~ "+symbols_.name(name)+" has no send~ in this device (cross-device buses need support)");
            nodes_[r].sendSource=found;edgesWithBuses.push_back({found,0,int(r),0});
        }
        std::vector<char> gateSetOnly(nodes_.size(),0);
        for(size_t i=0;i<nodes_.size();++i)if(nodes_[i].definition.op==Op::gate) {
            bool any=false,all=true;
            for(const auto& e:edges)if(e.destination==int(i) && e.inlet==1 && e.source>=0 && size_t(e.source)<nodes_.size()) {
                any=true;const auto& sd=nodes_[size_t(e.source)].definition;
                const bool staticSet=(sd.op==Op::message || sd.op==Op::prepend) && !sd.atoms.empty() && sd.atoms[0].type==Atom::Type::symbol && symbols_.name(sd.atoms[0].value.symbol)=="set";
                all=all && staticSet;
            }
            gateSetOnly[i]=any && all;
        }
        // A message box holding one static number whose value, followed through
        // value-preserving objects, ends only in cold inlets, routing inlets or
        // mismatched [sel] keys cannot re-trigger a loop synchronously. Orbit's
        // auto-map counter: [sel 1] -> [t b b] -> [i] -> [+ 1] -> [> 8] -> [sel 1]
        // -> [0( -> live.text (toggle, emits 0) -> [sel 1] misses, so the ring
        // ends there in Max as well. Content is static only when nothing can
        // 'set' the box: no right-inlet cord and only number/bang producers on
        // the left. Keys are static only when [sel] has no right-inlet cord.
        auto inletSources=[&](int node,int inlet,auto&& accept)->bool {
            for(const auto& x:edgesWithBuses)if(x.destination==node && x.inlet==inlet && !accept(x))return false;
            return true;
        };
        auto messageStatic=[&](int node)->bool {
            const auto& d=nodes_[size_t(node)].definition;
            if(d.op!=Op::message || d.atoms.size()!=1 || !d.atoms[0].numeric())return false;
            for(int sub:d.substitutions)if(sub>=0)return false;
            if(!inletSources(node,1,[](const Edge&){return false;}))return false;
            return inletSources(node,0,[&](const Edge& x){
                const Op o=nodes_[size_t(x.source)].definition.op;
                return !nodes_[size_t(x.source)].signalOutlet && (o==Op::select || o==Op::trigger || o==Op::dial || o==Op::loadbang || o==Op::delay || o==Op::deferlow || o==Op::metro ||
                    o==Op::integer || o==Op::floating || o==Op::counter || o==Op::change || o==Op::speedlim || o==Op::uButton || o==Op::textButton ||
                    (o>=Op::compareEqual && o<=Op::compareLessEqual) || (o>=Op::controlAdd && o<=Op::reverseSubtract));
            });
        };
        std::function<bool(int,int,Atom,int)> constantDies=[&](int node,int inlet,Atom value,int depth)->bool {
            if(depth>32)return false;
            const auto& d=nodes_[size_t(node)].definition;const Op op=d.op;
            if(nodes_[size_t(node)].signalOutlet)return false;
            if(numericColdInlet(op,inlet))return true;
            if((op==Op::gate || op==Op::switchGate) && inlet==0)return true;
            auto follow=[&](int outlet,Atom v)->bool {
                for(const auto& x:edgesWithBuses)if(x.source==node && x.outlet==outlet && !constantDies(x.destination,x.inlet,v,depth+1))return false;
                return true;
            };
            if(op==Op::dial && d.controlKind==2 && inlet==0) {
                // Toggle mode: a number sets and emits 0/1 (refpage); the text
                // outlet carries a symbol whose consumers are not followed.
                for(const auto& x:edgesWithBuses)if(x.source==node && x.outlet!=0)return false;
                return follow(0,Atom::integral(value.number()!=0?1:0));
            }
            if(op==Op::select && inlet==0) {
                if(!inletSources(node,1,[](const Edge&){return false;}))return false;
                for(const auto& key:d.atoms)if(key.equals(value))return false;
                return follow(int(d.atoms.size()),value);
            }
            if(op==Op::message && inlet==0)return messageStatic(node) && follow(0,d.atoms[0]);
            return false;
        };
        for (const auto& e : edgesWithBuses) {
            if (e.source < 0 || e.destination < 0 || size_t(e.source) >= nodes_.size() || size_t(e.destination) >= nodes_.size() ||
                e.outlet < 0 || e.outlet >= outletCount(nodes_[e.source].definition) || e.inlet < 0 || e.inlet >= inletCount(nodes_[e.destination].definition))
                throw std::invalid_argument("Unsupported or invalid patch cord port (node "+std::to_string(e.source)+" op "+std::to_string(size_t(e.source)<nodes_.size()?int(nodes_[size_t(e.source)].definition.op):-1)+" outlet "+std::to_string(e.outlet)+" -> node "+std::to_string(e.destination)+" op "+std::to_string(size_t(e.destination)<nodes_.size()?int(nodes_[size_t(e.destination)].definition.op):-1)+" inlet "+std::to_string(e.inlet)+")");
            const auto src = nodes_[e.source].definition.op, dst = nodes_[e.destination].definition.op;
            const bool messageOutlet=src==Op::modalExternal && e.outlet==2;
            const bool tapLink=src==Op::tapIn && dst==Op::tapOut;
            if (nodes_[e.source].signalOutlet && !messageOutlet) {
                if(dst==Op::signalSnapshot && e.inlet!=0)throw std::invalid_argument("snapshot~ interval inlet does not accept signals");

                if(dst==Op::signalRecord && e.inlet>=int(nodes_[e.destination].definition.arguments[0]))throw std::invalid_argument("record~ loop points do not accept signals");
                if (!signalInput(dst) || size_t(e.inlet)>=nodes_[e.destination].signalInputs.size()) throw std::invalid_argument("Unsupported signal-to-message connection");
                if(!tapLink)nodes_[e.destination].signalInputs[e.inlet].push_back(e);   // the tapin~ link is resolved separately, not summed as a delay time
                if(src==Op::boundary && dst!=Op::output && dst!=Op::meter) nodes_[e.source].messages.push_back(e);
            } else {
                if (dst == Op::output || (dst == Op::meter && !nodes_[e.destination].definition.presentation)) throw std::invalid_argument("Unsupported message destination");
                nodes_[e.source].messages.push_back(e);
            }
            // A signal cord into live.remote~/peakamp~ never produces a
            // synchronous message (their outlets answer id messages or a
            // timer), so it does not close a feedback loop: Gravity's gen~ ->
            // live.remote~ -> route -> prepend -> gen~ ring is legal.
            if(tapLink) {
                if(e.inlet!=0)throw std::invalid_argument("tapin~ must connect to tapout~'s left inlet");
                if(nodes_[e.destination].tapSource>=0 && nodes_[e.destination].tapSource!=e.source)throw std::invalid_argument("tapout~ reads one tapin~");
                nodes_[e.destination].tapSource=e.source;
            }
            // A tapout~ reads samples its tapin~ wrote at least one vector ago,
            // so the link (and any loop through it) is not a synchronous edge.
            // function's right outlet bangs only when a mouse edit completes
            // (refpage), never in answer to a message: Orbit's redraw ring
            // (function -> uzi -> expr -> function) is not a synchronous loop.
            const bool signalSink=(nodes_[e.source].signalOutlet && (dst==Op::liveRemote || dst==Op::peakAmp)) || tapLink || (src==Op::functionCurve && e.outlet==3);
            // A message box whose selector is a colour attribute (its text is
            // static, so this is known here) only restyles a presentation
            // object; the widget never answers it, so the cord is not a
            // synchronous hop either. Gravity's slot rows route 'rowcolor'
            // into 'lcdcolor $1 $2 $3 $4' -> live.numbox -> prepend -> outlet.
            bool attributeOnly=false;
            if((src==Op::message || src==Op::prepend) && !nodes_[e.source].definition.atoms.empty()
               && nodes_[e.source].definition.atoms[0].type==Atom::Type::symbol) {
                const auto& selector=symbols_.name(nodes_[e.source].definition.atoms[0].value.symbol);
                const bool colour=selector.size()>=5 && selector.compare(selector.size()-5,5,"color")==0;
                // 'set' into a control stores silently (no output): not a hop.
                const bool silentSet=dst==Op::dial || dst==Op::accum || dst==Op::integer || dst==Op::floating || dst==Op::message || dst==Op::pack || dst==Op::counter || dst==Op::zlRegister;
                attributeOnly=(nodes_[e.destination].definition.presentation && colour) || (silentSet && selector=="set");
            }
            // A gate whose data inlet only ever carries static 'set' messages
            // forwards nothing a control answers, so gate -> dial is not a hop
            // either (Shard's [prepend set] -> [gate] -> [live.dial] mirrors).
            if(src==Op::gate && dst==Op::dial && gateSetOnly[size_t(e.source)])attributeOnly=true;
            if(src==Op::message && !attributeOnly && !nodes_[e.source].signalOutlet && messageStatic(e.source)
               && constantDies(e.destination,e.inlet,nodes_[e.source].definition.atoms[0],0))attributeOnly=true;
            // gate/switch control inlets only change routing state; nothing is
            // emitted, so a trigger closing its own gate is not a loop.
            if((dst==Op::gate || dst==Op::switchGate) && e.inlet==0 && !nodes_[e.source].signalOutlet)attributeOnly=true;
            if(src!=Op::delay && src!=Op::deferlow && src!=Op::external && src!=Op::signalSnapshot && !signalSink && !attributeOnly && (nodes_[e.source].signalOutlet || !numericColdInlet(dst,e.inlet))) {
                ++degrees[e.destination]; downstream[e.source].push_back(e.destination);
            }
        }
        for(const auto& n:nodes_)if(n.definition.op==Op::tapOut && n.tapSource<0)throw std::invalid_argument("tapout~ needs a tapin~ connected to its left inlet");
        for(auto& n:nodes_) if((n.definition.op==Op::multiply || n.definition.op==Op::add || n.definition.op==Op::subtract)
                && n.signalInputs[0].empty() && !n.signalInputs[1].empty())
            n.values[0]=n.definition.arguments.empty()?0:n.definition.arguments[0];
        for(auto& n:nodes_)if(n.definition.op==Op::signalSelector) {
            const auto& a=n.definition.arguments;
            n.selector=std::make_unique<SignalSelector>(int(a[0]),int(a[1]),a[2],a[3]!=0,sampleRate_,!n.signalInputs[0].empty());
            n.values[0]=0;
        }
        // Synchronous loops remain invalid; delayed/deferred feedback is allowed
        // and bounded by separate queues and a per-service dispatch budget.
        for (size_t i = 0; i < degrees.size(); ++i) if (!degrees[i]) schedule_.push_back(int(i));
        for (size_t i = 0; i < schedule_.size(); ++i)
            for (int dst : downstream[schedule_[i]]) if (--degrees[dst] == 0) schedule_.push_back(dst);
        if (schedule_.size() != nodes_.size()) {
            // Walk one actual cycle (node index / op) so a rejected device
            // names the loop that needs a break object, not every node that
            // merely sits downstream of it.
            std::vector<int> state(nodes_.size(),0),stack;std::string detail;
            std::function<bool(int)> visit=[&](int v)->bool {
                state[v]=1;stack.push_back(v);
                for(int w:downstream[v]) {
                    if(degrees[w]<=0)continue;
                    if(state[w]==1) {
                        auto it=std::find(stack.begin(),stack.end(),w);
                        for(;it!=stack.end();++it)detail+=(detail.empty()?"":" -> ")+std::to_string(*it)+"/op"+std::to_string(int(nodes_[*it].definition.op));
                        return true;
                    }
                    if(state[w]==0 && visit(w))return true;
                }
                stack.pop_back();state[v]=2;return false;
            };
            for(size_t i=0;i<nodes_.size() && detail.empty();++i)if(degrees[i]>0 && state[i]==0)visit(int(i));
            throw std::invalid_argument("Feedback requires a scheduler/delay implementation (cycle " + detail + ")");
        }
        std::vector<RoutingDomain::Receiver> receivers;
        for(size_t i=0;i<nodes_.size();++i)if(nodes_[i].definition.op==Op::namedReceive)receivers.push_back({int(i),nodes_[i].definition.atoms[0].value.symbol});
        routingMember_=routing_->attach(symbols_,this,receiveNamed,std::move(receivers));
        if(!routing) {routing_->prepare();initialize();}
    }
    ~Runtime() {routing_->detach(routingMember_);}
    void initialize() {
        if(initialized_)return;
        if(!routing_->prepared())throw std::invalid_argument("Prepare routing before device initialization");
        for(auto& node:nodes_)if(node.definition.op==Op::signalRecord) {
            const auto& d=node.definition;
            node.recorder=std::make_unique<SignalRecord>(*routing_->buffers().at(symbols_.name(d.atoms[0].value.symbol)),size_t(d.arguments[0]));
            node.recorder->loop(d.arguments[1]!=0);node.recorder->append(d.arguments[2]!=0);
        }
        for(auto& node:nodes_)if(node.gen)node.gen->prepareBuffers();
        for(auto& node:nodes_)if(node.spectral)for(auto& copy:node.spectral->copies)copy->initialize();
        budget_ = budgetPerBlock_;
        if(parameterOrder_.empty()) {
            for (size_t i = 0; i < nodes_.size(); ++i)
                if (nodes_[i].definition.op == Op::dial && nodes_[i].definition.initialize)
                    deliver(int(i), 0, Message::number(nodes_[i].definition.initial), 0);
        } else {
            std::vector<bool> seen(nodes_.size());
            for(int i:parameterOrder_) {
                if(i<0 || size_t(i)>=nodes_.size() || seen[i] || nodes_[i].definition.op!=Op::dial || !nodes_[i].definition.initialize)
                    throw std::invalid_argument("Invalid parameter initialization order");
                seen[i]=true;
            }
            for(size_t i=0;i<nodes_.size();++i) if(nodes_[i].definition.op==Op::dial && nodes_[i].definition.initialize && !seen[i])
                throw std::invalid_argument("Incomplete parameter initialization order");
            for(int i:parameterOrder_) deliver(i,0,Message::number(nodes_[i].definition.initial),0);
        }
        // Flat-patcher Max 9 oracle: reverse serialized object order. Scrambling
        // screen positions leaves this order unchanged; reversing boxes flips it.
        for(int i=int(nodes_.size())-1;i>=0;--i) {
            if(nodes_[i].definition.op==Op::loadbang || nodes_[i].definition.op==Op::loadmess) deliver(i,0,Message{},0);
            else if(nodes_[i].definition.op==Op::external) queueExternal(i,-1,Message{});
        }
        // Live restores the device's saved controls after its load sequence
        // (measured: one burst, after loadbang, before live.thisdevice). A
        // restored set can be larger than the control queue (Shard: 622
        // parameters), so it has its own unbounded control-thread list
        // delivered here in order.
        for(const auto& r:restoreQueue_)deliver(r.node,r.inlet,r.message,0);
        restoreQueue_.clear();restoreQueue_.shrink_to_fit();
        if (fault_) {
            throw std::invalid_argument("Unsupported initialization messages ("+faultDescription()+")");
        }
        for(int i:parameterNodes_) parameterValues_[i].store(nodes_[i].values[0]);
        initialized_=true;
    }
    // Control-thread lookup after graph preparation. External table samples
    // are atomic words; the registry and dimensions remain immutable in render.
    // Host access by the name a script or the host uses: a '---' prefix
    // resolves to this instance's namespace exactly as the patch's does.
    void setInstanceBase(uint64_t base) noexcept { instanceBase_=base; }
    std::string instanceName(const std::string& name) const {
        return name.compare(0,3,"---")==0 ? std::to_string(instanceBase_)+name.substr(3) : name;
    }
    std::shared_ptr<const m4l::gen::Table> externalBuffer(const std::string& name) const {
        const auto found=routing_->buffers().find(instanceName(name));
        return found==routing_->buffers().end()?nullptr:found->second;
    }
    // Control-thread writes (JS Buffer.poke): each sample is one atomic word,
    // so the renderer sees a coherent old or new value; a run of samples is
    // not transactional, exactly like the reads.
    std::shared_ptr<m4l::gen::Table> externalBufferForWriting(const std::string& name) const {
        const auto found=routing_->buffers().find(instanceName(name));
        return found==routing_->buffers().end()?nullptr:found->second;
    }
    double sampleRate() const noexcept { return sampleRate_; }
    // Renderer ownership is required, just as for render(). The host settles
    // resulting script replies before starting its audio callback. Neither song
    // play/stop nor device bypass changes the DSP engine's lifecycle.
    bool setDSPActive(bool active) noexcept {
        if(!initialized_){fault_=true;return false;}
        if(active==dspActive_)return !fault_;
        dspActive_=active;budget_=budgetPerBlock_;
        for(auto& node:nodes_)if(node.spectral)for(auto& copy:node.spectral->copies)if(!copy->setDSPActive(active))fault_=true;
        for(int i=int(nodes_.size())-1;i>=0 && !fault_;--i)if(nodes_[i].dspState)
            nodes_[i].dspState->setActive(active,[&](int outlet,const Message& value){emit(i,value,0,outlet);});
        return !fault_;
    }
    void setDeviceEnabled(bool enabled) noexcept { deviceEnabled_.store(enabled,std::memory_order_release); }
    // MIDI from the host: each byte is delivered to every midiin node's outlet
    // through the ordinary control queue, so it is sample-block accurate.
    bool midiByte(int byte) noexcept {
        if(byte<0 || byte>255 || !hasMidiIn_) return false;
        bool ok=true;for(int i:midiInNodes_) ok=send(i,0,Message::integer(byte)) && ok;return ok;
    }
    bool acceptsMIDI() const noexcept { return hasMidiIn_; }
    // Render-thread MIDI (a host sequencer feeding the device from inside its
    // own callback): delivered immediately, ahead of this block's control
    // queue, so it never shares the single-producer queue with the UI thread.
    bool midiByteNow(int byte) noexcept {
        if(byte<0 || byte>255 || !hasMidiIn_ || !initialized_) return false;
        budget_=budgetPerBlock_;
        for(int i:midiInNodes_) deliver(i,0,Message::integer(byte),0);
        return !fault_.load(std::memory_order_relaxed);
    }
    void setTransport(bool playing,double tempo,double beat) noexcept {
        if(!std::isfinite(tempo) || tempo<=0 || !std::isfinite(beat) || beat<0)return;
        transportTempo_.store(tempo,std::memory_order_relaxed);transportBeat_.store(beat,std::memory_order_relaxed);
        transportPlaying_.store(playing,std::memory_order_release);
    }
    bool deviceEnabled() const noexcept { return deviceEnabled_.load(std::memory_order_acquire); }
    // One producer (UI/control), one consumer (render). Render-owned state is
    // never mutated by the UI. A rejected command is explicitly reported.
    // Control thread only: a saved control/text to restore. Before
    // initialize() it is kept aside and delivered at the end of the load
    // sequence; afterwards (an offline owner such as preflight) it is
    // delivered immediately. Never touches the realtime queue.
    bool restore(int node, int inlet, Message message) {
        if (node < 0 || size_t(node) >= nodes_.size() || inlet < 0 || inlet >= inletCount(nodes_[node].definition) || !message.valid(symbols_.size())) return false;
        if(!initialized_) {restoreQueue_.push_back({node,inlet,message});return true;}
        deliver(node,inlet,message,0);return !fault_.load(std::memory_order_relaxed);
    }
    bool send(int node, int inlet, Message message) noexcept {
        // Inlet -1 is the object's own touch surface (function only): the
        // host's edits arrive there so completion can bang the mouse outlet.
        if (node < 0 || size_t(node) >= nodes_.size() || inlet < (nodes_[node].definition.op==Op::functionCurve ? -1 : 0) || inlet >= inletCount(nodes_[node].definition) || !message.valid(symbols_.size())) { ++rejected_; return false; }
        const unsigned write = write_.load(std::memory_order_relaxed), next = (write + 1) % queue_.size();
        if (next == read_.load(std::memory_order_acquire)) { ++rejected_; return false; }
        queue_[write] = {node, inlet, message}; write_.store(next, std::memory_order_release); return true;
    }
    // Pending low-priority native work must also settle before device-ready or
    // a completed UI transaction. An empty script event queue alone is not idle.
    bool controlWorkPending() const noexcept {
        return deferredPending_.load(std::memory_order_acquire) ||
            read_.load(std::memory_order_acquire)!=write_.load(std::memory_order_acquire) ||
            replyRead_.load(std::memory_order_acquire)!=replyWrite_.load(std::memory_order_acquire) ||
            eventRead_.load(std::memory_order_acquire)!=eventWrite_.load(std::memory_order_acquire);
    }
    // Control thread only. No script execution, allocation or locks in render.
    bool popExternal(ExternalEvent& event) noexcept {
        const auto read=eventRead_.load(std::memory_order_relaxed);
        if(read==eventWrite_.load(std::memory_order_acquire))return false;
        event=externalEvents_[read];eventRead_.store((read+1)%externalEvents_.size(),std::memory_order_release);return true;
    }
    bool externalOutput(int node,int outlet,const Message& message) noexcept {
        if(node<0 || size_t(node)>=nodes_.size() || (nodes_[node].definition.op!=Op::external && nodes_[node].definition.op!=Op::buffer) ||
            outlet<0 || outlet>=outletCount(nodes_[node].definition) || !message.valid(symbols_.size()))return false;
        const unsigned write=replyWrite_.load(std::memory_order_relaxed),next=(write+1)%externalReplies_.size();
        if(next==replyRead_.load(std::memory_order_acquire))return false;
        externalReplies_[write]={node,outlet,message};replyWrite_.store(next,std::memory_order_release);return true;
    }
private:
    void queueExternal(int node,int inlet,const Message& message) noexcept {
        const unsigned write=eventWrite_.load(std::memory_order_relaxed),next=(write+1)%externalEvents_.size();
        if(next==eventRead_.load(std::memory_order_acquire)){
            const bool before=fault_.load(std::memory_order_relaxed);
            faultBecause("script event queue full");
            if(!before)attributeFault(node,inlet,int(message.kind),message.selector);
            return;
        }
        externalEvents_[write]={node,inlet,sampleTime_,message};eventWrite_.store(next,std::memory_order_release);
    }
public:
    void render(const float* left, const float* right, float* outLeft, float* outRight, int frames) noexcept {
        if(frames<0 || (frames>0 && (!outLeft || !outRight))) {
            const bool before=fault_.load(std::memory_order_relaxed);
            faultBecause("invalid signal render buffers or frame count");if(!before)attributeFault(-3,-1,-2);return;
        }
        if(!initialized_) {
            const bool before=fault_.load(std::memory_order_relaxed);
            faultBecause("signal rendering requested before initialization");if(!before)attributeFault(-3,-1,-2);
            if(frames>0){std::fill(outLeft,outLeft+frames,0);std::fill(outRight,outRight+frames,0);}return;
        }
        budget_ = budgetPerBlock_;
        // Service only the prior low-priority batch. A deferlow encountered here
        // is guaranteed another service turn, including in a feedback loop.
        const unsigned deferredEnd=deferredWrite_;
        while(deferredRead_!=deferredEnd && !fault_) {
            const auto c=deferred_[deferredRead_];deferredRead_=(deferredRead_+1)%deferred_.size();
            emit(c.source,c.message,0);
        }
        unsigned read = read_.load(std::memory_order_relaxed);
        const unsigned write = write_.load(std::memory_order_acquire);
        while (read != write) { const auto& c = queue_[read]; deliver(c.node, c.inlet, c.message, 0); read = (read + 1) % queue_.size(); }
        read_.store(read, std::memory_order_release);
        auto reply=replyRead_.load(std::memory_order_relaxed);
        const auto end=replyWrite_.load(std::memory_order_acquire);
        while(reply!=end) {const auto& c=externalReplies_[reply];emit(c.node,c.message,0,c.inlet);reply=(reply+1)%externalReplies_.size();}
        replyRead_.store(reply,std::memory_order_release);
        deferredPending_.store(deferredRead_!=deferredWrite_,std::memory_order_release);
        for (auto& n : nodes_) n.peak = 0;
        const bool transportPlaying=transportPlaying_.load(std::memory_order_acquire);
        const double transportTempo=transportTempo_.load(std::memory_order_relaxed),transportBeat=transportBeat_.load(std::memory_order_relaxed);
        for (int frame = 0; frame < frames; ++frame) {
            frameIndex_=frame;
            audioDispatch_=true;
            if(sampleTime_%64==0)for(size_t i=0;i<nodes_.size() && !fault_;++i)if(nodes_[i].snapshot)
                nodes_[i].snapshot->dispatch([&](double value){emitNumber(int(i),value,0);});
            if(sampleTime_%64==0 && dspActive_ && hasModal_)for(size_t i=0;i<nodes_.size() && !fault_;++i)if(nodes_[i].modal && sampleTime_>=nodes_[i].modalMeterDue){
                // The external polls every 50 ms: peak, voices, energy A/B, input peak, captured seconds.
                auto& n=nodes_[i];auto& e=*n.modal;n.modalMeterDue=sampleTime_+uint64_t(sampleRate_*0.05);
                Message out=Message::anything(modalMeter_);out.count=6;
                out.atoms[0]=Atom::real(e.peak);out.atoms[1]=Atom::real(double(e.active));out.atoms[2]=Atom::real(e.energyA);
                out.atoms[3]=Atom::real(e.energyB);out.atoms[4]=Atom::real(0);out.atoms[5]=Atom::real(0);
                emit(int(i),out,0,2);e.peak=0;
            }
            if(sampleTime_%64==0 && dspActive_ && hasPeakAmp_)for(size_t i=0;i<nodes_.size() && !fault_;++i)if(nodes_[i].definition.op==Op::peakAmp){
                // Reports the peak absolute sample since the last report once
                // the interval has elapsed, then starts a new window.
                auto& n=nodes_[i];const uint64_t interval=uint64_t(std::ceil(n.time*sampleRate_/1000.));
                if(sampleTime_>=n.lastOutput+interval){n.lastOutput=sampleTime_;emitNumber(int(i),n.target,0,0);n.target=0;}
            }
            if(sampleTime_%64==0 && dspActive_ && hasPlugSync_)for(size_t i=0;i<nodes_.size() && !fault_;++i)if(nodes_[i].definition.op==Op::plugSync){
                // Every signal vector, like the original. Only the outlets the
                // collected corpus consumes are modelled: running, beat in bar,
                // beat phase and tempo. Bars are 4/4 — the host has no meter.
                const double beat=transportPlaying?transportBeat+double(frame)*transportTempo/(60.*sampleRate_):transportBeat;
                const double whole=std::floor(beat);
                emitNumber(int(i),transportTempo,0,5);
                emitNumber(int(i),beat-whole,0,3);
                emitSingle(int(i),Atom::integral(int64_t(std::fmod(whole,4.))+1),0,2);
                emitSingle(int(i),Atom::integral(transportPlaying?1:0),0,0);
            }
            while(nextDue_<=sampleTime_ && !fault_) {
                int next=-1;
                for(size_t i=0;i<nodes_.size();++i) if(nodes_[i].delayActive && nodes_[i].due<=sampleTime_ &&
                    (next<0 || nodes_[i].due<nodes_[next].due || (nodes_[i].due==nodes_[next].due && nodes_[i].serial<nodes_[next].serial))) next=int(i);
                if(next<0)break;
                nodes_[next].delayActive=false;nextDelay();
                if(--*dispatchBudget_<0) {
                    faultBecause("scheduled message budget exhausted");attributeFault(next,-1,-4);break;
                }
                if(nodes_[next].definition.op==Op::speedlim) {nodes_[next].lastOutput=sampleTime_;emit(next,nodes_[next].pending,0,0);}
                else if(nodes_[next].definition.op==Op::pipe) firePipe(next);
                else if(nodes_[next].definition.op==Op::metro) {
                    auto& mn=nodes_[next];
                    if(mn.values[1]==0) {emitBang(next,0,0);armMetro(mn,metroNextDue(mn));}
                    else if(transportPlaying_.load(std::memory_order_acquire)) {emitBang(next,0,0);armMetro(mn,metroNextDue(mn));}
                    else armMetro(mn,sampleTime_+64);   // wait for the transport
                }
                else if(nodes_[next].definition.op==Op::dial && nodes_[next].definition.controlKind==3) nodes_[next].values[0]=0;   // flash over, silent
                else emitBang(next,0);
            }
            double l = 0, r = 0;
            if (!fault_.load(std::memory_order_relaxed)) {
                for (int index : schedule_) {
                    auto& n = nodes_[index];
                    if(n.muted) {std::fill(n.output.begin(),n.output.end(),0.);continue;}
                    const bool faultedBefore=fault_.load(std::memory_order_relaxed);
                    struct RenderFaultScope { Runtime& rt;int node;bool before;~RenderFaultScope(){if(!before && rt.fault_.load(std::memory_order_relaxed))rt.attributeFault(node,-1,-2);} } renderFaultScope{*this,index,faultedBefore};
                    switch (n.definition.op) {
                        case Op::polyIn:
                            n.output[0]=(n.signalInputs[0].empty() && n.spectralSlot>=0 && size_t(frameIndex_)<spectralIn_[size_t(n.spectralSlot)].real.size())?spectralIn_[size_t(n.spectralSlot)].real[size_t(frameIndex_)]:input(n,0);break;
                        case Op::polyOut:
                            n.output[0]=input(n,0);
                            if(n.spectralSlot>=0 && size_t(frameIndex_)<spectralOut_[size_t(n.spectralSlot)].real.size())spectralOut_[size_t(n.spectralSlot)].real[size_t(frameIndex_)]=n.output[0];
                            break;
                        case Op::input:
                            // plugin~ 3 4 is the sidechain pair: Live's default
                            // "No Input" routing is silence, and no chooser exists here yet.
                            if(!n.definition.arguments.empty()) {n.output[0]=0;n.output[1]=0;break;}
                            n.output[0]=left?left[frame]:0;n.output[1]=right?right[frame]:0;break;
                        case Op::gen:
                            for(int i=0;i<n.definition.genInputs;++i)n.genValues[i]=input(n,i);
                            if(!n.gen->process(n.genValues.data(),n.output.data()))fault_=true;
                            break;
                        case Op::signalSelector:
                            for(int i=0;i<n.selector->count();++i)n.genValues[i]=input(n,i+1);
                            n.output[0]=n.selector->process(input(n,0),n.genValues.data());
                            break;
                        case Op::signalSnapshot: n.snapshot->process(input(n,0),int(sampleTime_%64));break;
                        case Op::signalRecord:
                            for(int i=0;i<n.recorder->channels();++i)n.genValues[i]=input(n,i);
                            n.output[0]=n.recorder->processSample(n.genValues.data());
                            break;
                        case Op::output: l += input(n, 0); r += input(n, 1); break;
                        case Op::multiply: n.output[0] = input(n, 0) * input(n, 1); break;
                        case Op::add: n.output[0] = input(n, 0) + input(n, 1); break;
                        case Op::subtract: n.output[0] = input(n, 0) - input(n, 1); break;
                        case Op::reverseSubtractSignal: n.output[0] = input(n, 1) - input(n, 0); break;
                        case Op::modalExternal: {
                            double outL=0,outR=0;
                            n.modal->process(input(n,0),input(n,1),outL,outR);
                            n.output[0]=outL;n.output[1]=outR;break;
                        }
                        case Op::averageSignal: {
                            // Sliding mean of |x| over the window; the sum is
                            // maintained incrementally so cost is O(1) per sample.
                            const double x = std::abs(input(n, 0));
                            n.ringSum += x - n.ring[n.ringIndex]; n.ring[n.ringIndex] = x;
                            if (++n.ringIndex == n.ring.size()) n.ringIndex = 0;
                            n.output[0] = n.ringSum / double(n.ring.size()); break;
                        }
                        case Op::onePole: {
                            // A signal at the right inlet retunes the coefficient every sample.
                            if(!n.signalInputs[1].empty()) {const double fc=std::min(std::max(input(n,1),0.),sampleRate_*0.5);n.step=std::exp(-2*M_PI*fc/sampleRate_);}
                            n.target = (1 - n.step) * input(n, 0) + n.step * n.target;
                            n.output[0] = n.target; break;
                        }
                        case Op::overdrive: {
                            // MEASURED in Live 12.4.5 (13-point sweep at drive 4, zero error):
                            // y = sign(x) * (1 - (1 - |x|)^drive) for |x| < 1, else sign(x).
                            const double x=input(n,0),drive=n.signalInputs[1].empty()?n.values[1]:input(n,1);
                            const double a=std::abs(x);
                            n.output[0]=a>=1?(x<0?-1.:1.):(x<0?-1.:1.)*(1-std::pow(1-a,drive));break;
                        }
                        case Op::degrade: {
                            // degrade~ <ratio> <bits>: bit reduction TRUNCATES
                            // (MEASURED: 0.3 -> 0.29998779296875 at 16 bits, 0.25 at 4);
                            // the sampling ratio holds a sample until the phase
                            // accumulator wraps (hold model UNMEASURED).
                            const double ratio=std::min(std::max(n.signalInputs[1].empty()?n.values[1]:input(n,1),0.),1.);
                            const double bits=std::min(std::max(n.signalInputs[2].empty()?n.values[2]:input(n,2),1.),24.);
                            n.values[3]+=ratio;
                            if(n.values[3]>=1 || ratio>=1) {n.values[3]=ratio>=1?0:n.values[3]-1;const double scale=std::pow(2.,bits);n.target=std::trunc(input(n,0)*scale)/scale;}
                            n.output[0]=n.target;break;
                        }
                        case Op::tanhSignal: n.output[0]=std::tanh(input(n,0));break;
                        case Op::polyUp: {
                            double ins[8]={},outs[8]={};
                            for(int k=0;k<n.spectral->inlets;++k)ins[k]=input(n,k);
                            n.spectral->processResampled(ins,outs);
                            for(int k=0;k<n.spectral->outlets;++k)n.output[size_t(k)]=outs[k];
                            break;
                        }
                        case Op::pfft: {
                            double ins[8]={},outs[8]={};
                            for(int k=0;k<n.spectral->inlets;++k)ins[k]=input(n,k);
                            n.spectral->process(ins,outs);
                            for(int k=0;k<n.spectral->outlets;++k)n.output[size_t(k)]=outs[k];
                            break;
                        }
                        case Op::fftIn: {
                            const auto& io=spectralIn_[size_t(n.spectralSlot)];
                            n.output[0]=io.real[size_t(frameIndex_)];n.output[1]=io.imag[size_t(frameIndex_)];n.output[2]=double(frameIndex_);break;
                        }
                        case Op::fftOut: {
                            auto& io=spectralOut_[size_t(n.spectralSlot)];
                            io.real[size_t(frameIndex_)]=input(n,0);io.imag[size_t(frameIndex_)]=input(n,1);break;
                        }
                        case Op::poke: {
                            // Writes value (inlet 0) at sample index (inlet 1,
                            // truncated) in the bound channel; out of range is dropped.
                            n.pokeTable->poke(input(n,0),std::trunc(input(n,1)),n.values[2]);break;
                        }
                        case Op::indexSignal: n.output[0]=n.pokeTable->peek(std::trunc(input(n,0)),n.values[1]);break;
                        case Op::tapIn: {
                            n.ring[n.ringIndex]=input(n,0);if(++n.ringIndex==n.ring.size())n.ringIndex=0;
                            n.output[0]=0;break;
                        }
                        case Op::absSignal: n.output[0]=std::abs(input(n,0));break;
                        case Op::loudness: {
                            double samples[8]={};const int channels=int(n.definition.arguments[0]);
                            for(int c=0;c<channels;++c)samples[c]=input(n,c);
                            n.loudness->process(samples);
                            const uint64_t interval=uint64_t(std::llround(n.definition.arguments[1]*sampleRate_/1000.));
                            if(++n.remaining>=interval && dspActive_) {
                                n.remaining=0;
                                auto floor=[](double v){return std::isfinite(v)?std::max(v,-120.):-120.;};
                                emitNumber(int(index),floor(n.loudness->truePeakDb()),0,5);
                                emitNumber(int(index),floor(n.loudness->samplePeakDb()),0,4);
                                emitNumber(int(index),floor(n.loudness->range()),0,3);
                                emitNumber(int(index),floor(n.loudness->integrated()),0,2);
                                emitNumber(int(index),floor(n.loudness->shortTerm()),0,1);
                                emitNumber(int(index),floor(n.loudness->momentary()),0,0);
                            }
                            break;
                        }
                        case Op::fzero: {
                            // The external queues each vector and analyses on the
                            // scheduler; here the analysis completes the vector that
                            // fills a period. Outlets right to left: onset, amplitude, pitch.
                            n.fzero->push(input(n,0));
                            if(sampleTime_%64==63 && n.fzero->due() && dspActive_) {
                                const auto tick=n.fzero->tick();
                                if(tick.onset) {
                                    if(n.fzero->onsetList()) {Atom list[2]={Atom::real(tick.onsetPitch),Atom::real(tick.onsetAmplitude)};emitSequence(int(index),list,2,0,2);}
                                    else emitBang(int(index),0,2);
                                }
                                emitNumber(int(index),tick.amplitude,0,1);
                                if(tick.pitchOutput)emitNumber(int(index),tick.pitch,0,0);
                            }
                            break;
                        }
                        case Op::divideSignal: {
                            // /~: a zero divisor yields 0 (Max avoids inf; unmeasured).
                            const double a=input(n,0),b=n.signalInputs[1].empty()?n.values[1]:input(n,1);
                            n.output[0]=b==0?0:a/b;break;
                        }
                        case Op::sendSignal: n.output[0]=input(n,0);break;
                        case Op::receiveSignal: n.output[0]=nodes_[size_t(n.sendSource)].output[0];break;
                        case Op::biquad: {
                            for(int k=1;k<=5;++k)if(!n.signalInputs[size_t(k)].empty())n.values[size_t(k)]=input(n,k);
                            const double x=input(n,0);
                            const double y=n.values[1]*x+n.values[2]*n.bqX1+n.values[3]*n.bqX2-n.values[4]*n.bqY1-n.values[5]*n.bqY2;
                            n.bqX2=n.bqX1;n.bqX1=x;n.bqY2=n.bqY1;n.bqY1=y;
                            n.output[0]=std::isfinite(y)?y:0;break;
                        }
                        case Op::filterCoeff: {
                            for(int k=0;k<3;++k)if(!n.signalInputs[size_t(k)].empty())n.values[size_t(k)]=input(n,k);
                            if(n.coeffCounter==0)filterCoefficients(n);
                            if(++n.coeffCounter>=uint64_t(n.definition.arguments[1]))n.coeffCounter=0;
                            break;
                        }
                        case Op::scope: {
                            if(n.definition.arguments[0]==0) {
                                const size_t calccount=size_t(n.definition.arguments[2]),bufsize=size_t(n.definition.arguments[1]);
                                if(++n.frameCount>=calccount) {
                                    n.frameCount=0;
                                    n.frameWork[n.frameFill*2]=float(input(n,0));n.frameWork[n.frameFill*2+1]=float(input(n,1));
                                    if(++n.frameFill>=bufsize) {
                                        n.frameFill=0;
                                        n.frameSeq->fetch_add(1,std::memory_order_acq_rel);
                                        std::copy(n.frameWork.begin(),n.frameWork.end(),n.frame.begin());
                                        n.frameSeq->fetch_add(1,std::memory_order_acq_rel);
                                    }
                                }
                            } else {
                                n.ring[n.ringIndex]=input(n,0);if(++n.ringIndex==n.ring.size())n.ringIndex=0;
                                const uint64_t interval=uint64_t(std::ceil(n.definition.arguments[4]*sampleRate_/1000.));
                                if(++n.frameCount>=interval) {
                                    n.frameCount=0;
                                    const size_t N=n.ring.size();
                                    for(size_t i=0;i<N;++i) {const double w=0.5-0.5*std::cos(2*M_PI*double(i)/double(N));n.fftRe[i]=n.ring[(n.ringIndex+i)%N]*w;n.fftIm[i]=0;}
                                    n.spectralFFT->transform(n.fftRe.data(),n.fftIm.data(),false);
                                    n.frameSeq->fetch_add(1,std::memory_order_acq_rel);
                                    for(size_t i=0;i<N/2;++i)n.frame[i]=float(2.*std::sqrt(n.fftRe[i]*n.fftRe[i]+n.fftIm[i]*n.fftIm[i])/double(N));
                                    n.frameSeq->fetch_add(1,std::memory_order_acq_rel);
                                }
                            }
                            break;
                        }
                        case Op::tapOut: {
                            const auto& src=nodes_[size_t(n.tapSource)];
                            for(size_t k=0;k<n.definition.arguments.size();++k) {
                                const double ms=n.signalInputs[k].empty()?n.values[k]:input(n,int(k));
                                double delay=ms*sampleRate_/1000.;
                                if(!(delay>=double(kTapMinimumDelay)))delay=double(kTapMinimumDelay);
                                const double limit=double(src.ring.size()-1);if(delay>limit)delay=limit;
                                // MEASURED (Live, September 11): a fractional
                                // delay truncates to whole samples (10.5 ms ->
                                // 463 samples at 44.1 kHz, amplitude exactly 1):
                                // no interpolation.
                                delay=std::floor(delay);
                                const double read=double(src.ringIndex)-delay;
                                const size_t size=src.ring.size();
                                const long i0=long(read)%long(size);const size_t a=size_t(i0<0?i0+long(size):i0);
                                n.output[k]=src.ring[a];
                            }
                            break;
                        }
                        case Op::randSignal: {
                            if(n.remaining==0) {
                                uint64_t x=n.rng;x^=x>>12;x^=x<<25;x^=x>>27;n.rng=x;
                                n.values[0]=n.target;n.target=double((x*0x2545F4914F6CDD1Dull)>>11)/double(1ull<<53)*2-1;
                                n.time=std::max(1.,std::round(sampleRate_/n.values[1]));n.remaining=uint64_t(n.time);n.step=(n.target-n.values[0])/n.time;
                            }
                            n.output[0]=n.values[0];n.values[0]+=n.step;--n.remaining;
                            break;
                        }
                        case Op::adsr: {
                            n.output[0]=n.values[0];
                            const int stage=int(n.values[5]);
                            if(stage==1 || stage==2 || stage==4) {
                                if(n.remaining && --n.remaining==0) {
                                    n.values[0]=n.target;
                                    if(stage==1) {n.values[5]=2;n.target=n.values[3];n.remaining=std::max<uint64_t>(1,uint64_t(std::llround(n.values[2]*sampleRate_/1000.)));n.step=(n.target-n.values[0])/double(n.remaining);}
                                    else if(stage==2)n.values[5]=3;
                                    else n.values[5]=0;
                                } else if(n.remaining)n.values[0]+=n.step;
                            }
                            break;
                        }
                        case Op::cartopol: {
                            const double re=input(n,0),imv=input(n,1);
                            n.output[0]=std::sqrt(re*re+imv*imv);n.output[1]=std::atan2(imv,re);break;
                        }
                        case Op::clipSignal: {
                            const double lo=std::min(n.values[1],n.values[2]),hi=std::max(n.values[1],n.values[2]);
                            n.output[0]=std::min(std::max(input(n,0),lo),hi);break;
                        }
                        case Op::signal: n.output[0] = n.values[0]; break;
                        case Op::liveRemote:
                            // The session consumes the most recent normalized
                            // signal once per bounded render vector. Mapping
                            // state is renderer-owned and no host callback is
                            // made from here.
                            if(n.hasHeld)n.target=input(n,0);
                            break;
                        case Op::boundary: if(n.signalOutlet) n.output[0]=input(n,0);break;
                        case Op::line:
                            n.output[0] = n.values[0];
                            if (n.remaining && --n.remaining == 0) {
                                n.values[0] = n.target;
                                // Next queued "target time" segment, if any.
                                if (int(n.values[3]) + 1 < n.storedCount) {
                                    const int head = int(n.values[3]); n.values[3] = head + 2;
                                    n.target = n.stored[size_t(head)].number();
                                    const double ms = n.stored[size_t(head) + 1].number();
                                    n.remaining = uint64_t(std::llround(ms * sampleRate_ / 1000.));
                                    if (!n.remaining) n.values[0] = n.target;
                                    else n.step = (n.target - n.values[0]) / double(n.remaining);
                                }
                            } else if (n.remaining) n.values[0] += n.step;
                            break;
                        case Op::meter: n.peak = std::max(n.peak, std::abs(input(n, 0))); break;
                        // values[0] is seeded from the interval argument; accumulate in target.
                        case Op::peakAmp: if(dspActive_) n.target = std::max(n.target, double(std::abs(input(n, 0)))); break;
                        default: break;
                    }
                }
            }
            if (!std::isfinite(l) || !std::isfinite(r) || std::abs(l) > 3.4e38 || std::abs(r) > 3.4e38) {
                const bool before=fault_.load(std::memory_order_relaxed);
                faultBecause("non-finite or out-of-range mixed stereo output");
                if(!before)attributeFault(-2,-1,-2);
                l = r = 0;
            }
            outLeft[frame] = float(l); outRight[frame] = float(r);
            ++sampleTime_;
        }
        audioDispatch_=false;
        for (size_t i = 0; i < nodes_.size(); ++i) meters_[i].store(nodes_[i].peak, std::memory_order_relaxed);
        for(int i:parameterNodes_) parameterValues_[i].store(nodes_[i].values[0]);
    }
    // A shared routing update may arrive after this graph's audio block. The
    // session publishes all parameter views again before acknowledging controls.
    void publishParameters() noexcept {for(int i:parameterNodes_)parameterValues_[i].store(nodes_[i].values[0]);}
    bool faulted() const noexcept {
        if(fault_.load(std::memory_order_relaxed))return true;
        for(const auto& node:nodes_)if(node.spectral && node.spectral->faulted())return true;
        return false;
    }
    const Symbols& symbols() const noexcept { return symbols_; }
    // Control thread, before initialize(): the id of a name the plan interned
    // (host symbols); a name the runtime lacks is refused rather than added
    // under a possibly running render.
    bool symbolFor(const std::string& name,Symbol& out) const noexcept {
        for(size_t i=0;i<symbols_.size();++i)if(symbols_.name(Symbol(i))==name) {out=Symbol(i);return true;}
        return false;
    }
    // 'setcurve' as interned for this graph's function objects (0 without one).
    Symbol functionSetcurveSymbol() const noexcept { return functionSetcurve_; }
    const std::vector<int>& parameterNodes() const noexcept { return parameterNodes_; }
    const std::vector<int>& liveRemoteNodes() const noexcept { return liveRemoteNodes_; }
    double parameterValue(int node) const noexcept { return node>=0 && size_t(node)<nodes_.size() && nodes_[node].definition.op==Op::dial ? parameterValues_[node].load() : NAN; }
    // Renderer-owned live.remote~ hooks. A host first installs the mapping on
    // the session command queue; the callback then toggles the source and
    // emits Max's mapped notification without crossing into Swift/ObjC.
    bool setLiveRemoteMappedNow(int node,bool mapped) noexcept {
        if(node<0 || size_t(node)>=nodes_.size() || nodes_[size_t(node)].definition.op!=Op::liveRemote || !initialized_)return false;
        auto& remote=nodes_[size_t(node)];
        if(remote.hasHeld==mapped)return !fault_.load(std::memory_order_relaxed);
        remote.hasHeld=mapped;
        Message out=Message::anything(mappedSymbol_);out.count=1;out.atoms[0]=Atom::integral(mapped?1:0);
        emit(node,out,0,0);
        return !fault_.load(std::memory_order_relaxed);
    }
    bool liveRemoteValue(int node,double& value) const noexcept {
        if(node<0 || size_t(node)>=nodes_.size())return false;
        const auto& remote=nodes_[size_t(node)];
        if(remote.definition.op!=Op::liveRemote || !remote.hasHeld || !std::isfinite(remote.target))return false;
        value=remote.target;return true;
    }
    // A mapped signal is normalized, like Live's remote parameter protocol.
    // Deliver rawfloat on the render owner so the target dial applies its own
    // exponent, step count and range and routes the resulting value normally.
    bool setParameterNormalizedNow(int node,double normalized) noexcept {
        if(node<0 || size_t(node)>=nodes_.size() || nodes_[size_t(node)].definition.op!=Op::dial || !std::isfinite(normalized) || !initialized_)return false;
        Message value=Message::anything(sym::rawfloat);value.count=1;value.atoms[0]=Atom::real(std::clamp(normalized,0.,1.));
        deliver(node,0,value,0);
        return !fault_.load(std::memory_order_relaxed);
    }
    unsigned rejected() const noexcept { return rejected_.load(std::memory_order_relaxed); }
    double meter(int node) const noexcept { return node >= 0 && size_t(node) < nodes_.size() ? meters_[node].load(std::memory_order_relaxed) : 0; }
    // Test hook: a node's current signal outlet value (not for hosts).
    double debugOutput(int node,int outlet) const noexcept { return node>=0 && size_t(node)<nodes_.size() && outlet>=0 && size_t(outlet)<nodes_[size_t(node)].output.size() ? nodes_[size_t(node)].output[size_t(outlet)] : 0; }
    // Control-thread read of a scope frame: returns the frame's float count
    // written into `out` (up to `capacity`), or 0 when no consistent frame
    // could be read (renderer mid-write) or the node is not a scope.
    size_t scopeFrame(int node,float* out,size_t capacity) const noexcept {
        if(node<0 || size_t(node)>=nodes_.size() || !out)return 0;
        const auto& n=nodes_[size_t(node)];
        if(n.definition.op!=Op::scope || !n.frameSeq || n.frame.empty() || n.frame.size()>capacity)return 0;
        for(int attempt=0;attempt<4;++attempt) {
            const uint32_t before=n.frameSeq->load(std::memory_order_acquire);
            if(before&1u)continue;
            std::copy(n.frame.begin(),n.frame.end(),out);
            if(n.frameSeq->load(std::memory_order_acquire)==before)return n.frame.size();
        }
        return 0;
    }
    // Control-thread diagnostic: which node first tripped the fault (message
    // kind -2 = during signal rendering), or the child pfft~ that did.
    std::string faultDescription() const {
        const int node=faultNode_.load(std::memory_order_acquire);
        if(node>=0) {
            const auto& d=nodes_[size_t(node)].definition;
            std::string why="node "+std::to_string(node)+" op "+std::to_string(int(d.op));
            if(faultKind_==-2)why+=" during signal rendering";
            else if(faultKind_==-4)why+=" during scheduled message dispatch";
            else {
                why+=(faultOutlet_?" outlet ":" inlet ")+std::to_string(faultInlet_)+" message kind "+std::to_string(faultKind_)+" selector '";
                why+=faultSelector_<symbols_.size()?symbols_.name(faultSelector_):"unprepared symbol "+std::to_string(faultSelector_);
                why+="'";
            }
            if(faultReason_)why+=std::string(": ")+faultReason_;
            return why;
        }
        if(node==-2) {
            // Only the final sum was invalid. Naming an arbitrary contributing
            // node as its cause would misdiagnose cancellation and valid routing.
            std::string why=faultReason_;why+=" (";bool first=true;
            for(size_t i=0;i<nodes_.size();++i)if(nodes_[i].definition.op==Op::output) {
                if(!first)why+=", ";first=false;why+="node "+std::to_string(i)+" op "+std::to_string(int(Op::output));
            }
            why+=")";return why;
        }
        if(node==-3)return std::string("host render contract: ")+faultReason_;
        for(size_t i=0;i<nodes_.size();++i)if(nodes_[i].spectral)for(const auto& c:nodes_[i].spectral->copies)if(c->faulted())return "pfft~ node "+std::to_string(i)+": "+c->faultDescription();
        return "unattributed";
    }
};
} // namespace m4l::maxcompat
