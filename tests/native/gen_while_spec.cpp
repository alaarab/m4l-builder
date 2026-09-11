#include "../../src/m4l_builder/native/max_compat/genexpr.hpp"
#include <cassert>
#include <iostream>
#include <array>
using m4l::gen::Expression;
int main(){
    Expression w("Param g(1); i=0; acc=0; while(i<5){ acc=acc+in1*i; i=i+1; } out1=acc*g;",48000);
    Expression f("Param g(1); acc=0; for(i=0;i<5;i=i+1){ acc=acc+in1*i; } out1=acc*g;",48000);
    Expression c("Param g(1); i=0; acc=0; while(i<6){ i=i+1; if(i==3) continue; acc=acc+i; } out1=acc*g;",48000);
    std::array<double,64> in{},ow{},of{},oc{};in[0]=2;
    assert(w.process(in.data(),ow.data()));assert(f.process(in.data(),of.data()));assert(c.process(in.data(),oc.data()));
    std::cout<<"while="<<ow[0]<<" for="<<of[0]<<" continue="<<oc[0]<<"\n";
    assert(ow[0]==20 && of[0]==20 && oc[0]==18);
    bool capped=false;
    try{Expression r("Param g(1); i=0; while(1){ i=i+1; } out1=i*g;",48000);std::array<double,64> o{};if(!r.process(in.data(),o.data()))capped=true;}
    catch(const std::exception& e){capped=true;std::cout<<"runaway rejected: "<<e.what()<<"\n";}
    std::cout<<(capped?"PASS: while matches for, continue skips to the condition, runaway is bounded\n":"FAIL: runaway not bounded\n");
    return capped?0:1;
}
// int()/float() conversions appended: int truncates toward zero, float passes through.
static int cast_tests(){
    Expression e("Param g(1); out1 = int(in1) * g; out2 = float(int(in1)) * 0.5 * g; out3 = int(-in1) * g;",48000);
    std::array<double,64> in{},o{};in[0]=3.75;
    assert(e.process(in.data(),o.data()));
    assert(o[0]==3 && o[1]==1.5 && o[2]==-3);
    return 0;
}
static const int cast_ran=cast_tests();
