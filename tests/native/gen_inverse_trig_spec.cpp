// Inverse and hyperbolic trig in GenExpr: asin/acos/atan/atan2/sinh/cosh.
// Heat's wave shaper uses 0.63661977 * asin(sin(x * w)) (a triangle fold).
// Values are compared against libm directly: gen~'s genlib evaluates these
// through the same std calls, so this is a libm-identity check, not a Max
// capture.
#include "../../src/m4l_builder/native/max_compat/genexpr.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
#include <array>
using m4l::gen::Expression;
int main(){
    Expression e("Param g(1); out1 = 0.63661977 * asin(sin(in1 * 1.5)) * g; out2 = acos(in1 * 0.5) * g; out3 = atan(in1) * g; out4 = atan2(in1, 2.0) * g; out5 = sinh(in1) * g; out6 = cosh(in1) * g;",48000);
    std::array<double,64> in{},o{};
    const double xs[]={-2.0,-1.0,-0.25,0,0.5,1.0,1.75,2.0}; // acos(x*0.5) stays in domain
    int checked=0;
    for(double x:xs){
        in[0]=x;assert(e.process(in.data(),o.data()));
        assert(o[0]==0.63661977*std::asin(std::sin(x*1.5)));
        assert(o[1]==std::acos(x*0.5));
        assert(o[2]==std::atan(x));
        assert(o[3]==std::atan2(x,2.0));
        assert(o[4]==std::sinh(x));
        assert(o[5]==std::cosh(x));
        ++checked;
    }
    // log10/log2/exp2 (Unmask's per-bin dB): libm identity as well.
    Expression l("Param g(1); out1 = log10(in1) * g; out2 = log2(in1) * g; out3 = exp2(in1) * g;",48000);
    in[0]=8;assert(l.process(in.data(),o.data()));assert(o[0]==std::log10(8.) && o[1]==3 && o[2]==256);
    // fold (genlib_ops.h): reflects into [lo, hi]; 1.3 -> 0.7, -0.2 -> 0.2, 2.5 -> 0.5 in [0, 1].
    Expression f("Param g(1); out1 = fold(in1, 0, 1) * g;",48000);
    for(auto pr:{std::pair<double,double>{1.3,0.7},{-0.2,0.2},{2.5,0.5},{0.4,0.4},{1.0,1.0}}) {in[0]=pr.first;assert(f.process(in.data(),o.data()));assert(std::abs(o[0]-pr.second)<1e-12);}
    // Domain edge: asin(1.5) is NaN; the existing non-finite-output policy
    // faults the expression rather than letting NaN into the audio graph.
    Expression n("Param g(1); out1 = asin(in1) * g;",48000);
    in[0]=1.5;assert(!n.process(in.data(),o.data()));
    // Wrong arity is rejected at compile time.
    bool rejected=false;try{Expression b("out1 = atan2(in1);",48000);}catch(const std::exception&){rejected=true;}
    assert(rejected);
    std::cout<<"PASS: "<<checked<<" inputs match libm for asin/acos/atan/atan2/sinh/cosh (+log10/log2/exp2, fold), out-of-domain NaN faults per policy, arity checked\n";
    return 0;
}
