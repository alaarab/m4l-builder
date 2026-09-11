#pragma once
// Original GenExpr is prepared into bounded instructions, never native machine
// code or a device-specific port. Rendering owns all state and allocates nothing.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <map>
#include <memory>
#include "gen_delay.hpp"
#include "gen_buffer.hpp"
#include "gen_noise.hpp"
#include "gen_mod.hpp"
#include <stdexcept>
#include <string>
#include <vector>

namespace m4l::gen {
// Gen folds whole-valued constants to integers, including literals written 3.
// Function arguments retain that inferred type when assigned inside the body.
// Audio inputs and History remain floating point even when their value is 3.
struct ValueInfo {
    bool constant=false,integer=false;
    double value=0;
    bool ambiguous=false;
    static ValueInfo literal(double value) {return {true,std::trunc(value)==value,value};}
    static ValueInfo merge(ValueInfo a,ValueInfo b) {
        if(a.constant && b.constant && a.value==b.value)return a;
        return {false,a.integer && b.integer,0,a.ambiguous || b.ambiguous};
    }
};
class Expression {
    enum class Op { move, moveInteger, add, sub, mul, div, mod, neg, logicalNot, less, lessEqual,
        greater, greaterEqual, equal, unequal, logicalAnd, logicalOr, choose,
        absolute, minimum, maximum, power, squareRoot, exponential, logarithm,
        sine, cosine, tangent, hyperbolicTangent, arcSine, arcCosine, arcTangent, arcTangent2, hyperbolicSine, hyperbolicCosine, logarithm10, logarithm2, exponential2, fold, floor, ceil, round, trunc,
        clip, mix, dbtoa, atodb, mstosamps, sampstoms, jump, jumpZero, delayRead, delayWrite, tableRead, tableWrite, tableDim, tableChannels, wrap, noise, change, phasor, modConstant, tableReadPhase, snapshotLoop, tableSample, tableSamplePhase };
    struct Instruction { Op op; int dst=0,a=0,b=0,c=0; };
    struct Variable { int reg; bool writable=true,fixedInteger=false,fixedFloating=false,ambiguousArgument=false; };
    struct State { int reg; double initial,value; };
public:
    struct Parameter { std::string name; int reg; double initial,minimum,maximum,value; };
private:
    std::vector<Instruction> code_;
    struct SnapshotCopy {int table,delay,offset,channel;Interpolation interpolation;};
    struct SnapshotLoop {int index,limit;std::vector<SnapshotCopy> copies;};
    std::vector<SnapshotLoop> snapshotLoops_;
    bool optimizeSnapshots_=true;
    std::vector<double> initial_,registers_;
    std::vector<ValueInfo> info_,inputInfo_;
    bool constantParameters_=false;
    std::map<std::string,double> parameterDefaults_;
    std::vector<State> histories_;
    // Operator-local storage is independent at every prepared call site. It
    // changes only when the instruction executes, including conditional calls.
    std::vector<double> operatorStates_;
    std::vector<std::unique_ptr<Delay>> delays_;
    std::shared_ptr<Noise> noise_;
    struct TableReference {std::string name,binding;std::shared_ptr<Table> table,initial;bool internal=false;};
    std::vector<TableReference> tables_;
    const BufferRegistry* buffers_=nullptr;
    size_t tableSamples_=0,tableBudget_=8388608;
    size_t delaySamples_=0,delayBudget_=8388608;
    bool prepareDelayStorage_=true;
    std::vector<Parameter> parameters_;
    std::array<int,64> inputs_{},outputs_{};
    int inputCount_=0,outputCount_=0;
    double rate_;
    bool fault_=false;
    static double calculate(Op op,double a,double b,double c,double rate) noexcept {
        switch(op) {
            case Op::move:return a;case Op::moveInteger:return std::trunc(a);
            case Op::add:return a+b;case Op::sub:return a-b;case Op::mul:return a*b;
            case Op::div:return b==0?0:a/b;case Op::mod:return remainder(a,b);
            case Op::modConstant:return constantRemainder(a,b,c);
            case Op::neg:return -a;case Op::logicalNot:return a==0;
            case Op::less:return a<b;case Op::lessEqual:return a<=b;
            case Op::greater:return a>b;case Op::greaterEqual:return a>=b;
            case Op::equal:return a==b;case Op::unequal:return a!=b;
            case Op::logicalAnd:return a!=0 && b!=0;case Op::logicalOr:return a!=0 || b!=0;
            case Op::choose:return a!=0?b:c;case Op::absolute:return std::abs(a);
            case Op::minimum:return std::min(a,b);case Op::maximum:return std::max(a,b);
            case Op::power:return std::pow(a,b);case Op::squareRoot:return std::sqrt(a);
            case Op::exponential:return std::exp(a);case Op::logarithm:return std::log(a);
            case Op::sine:return std::sin(a);case Op::cosine:return std::cos(a);
            case Op::tangent:return std::tan(a);case Op::hyperbolicTangent:return std::tanh(a);
            // Inverse/hyperbolic trig go straight to libm like gen~'s genlib
            // (asin/acos/atan/atan2/sinh/cosh are plain std calls there);
            // out-of-domain asin/acos yield NaN in both.
            case Op::arcSine:return std::asin(a);case Op::arcCosine:return std::acos(a);
            case Op::arcTangent:return std::atan(a);case Op::arcTangent2:return std::atan2(a,b);
            case Op::hyperbolicSine:return std::sinh(a);case Op::hyperbolicCosine:return std::cosh(a);
            case Op::logarithm10:return std::log10(a);case Op::logarithm2:return std::log2(a);case Op::exponential2:return std::exp2(a);
            case Op::floor:return std::floor(a);case Op::ceil:return std::ceil(a);
            case Op::round:return std::round(a);case Op::trunc:return std::trunc(a);
            case Op::clip:return std::min(std::max(a,std::min(b,c)),std::max(b,c));
            case Op::wrap: {
                const double lo=std::min(b,c),hi=std::max(b,c),range=hi-lo;
                if(a>=lo && a<hi)return a;
                if(range<=1e-9)return lo;
                return a-range*std::floor((a-lo)/range);
            }
            case Op::fold: {
                // genlib_ops.h fold(): reflect out-of-range values back into
                // [lo, hi], flipping on odd wrap counts.
                if(b==c)return b;
                const double lo=std::min(b,c),hi=std::max(b,c),range=hi-lo;double v=a;long wraps=0;
                if(v>=hi) {v-=range;if(v>=hi) {wraps=long((v-lo)/range);v-=range*double(wraps);}++wraps;}
                else if(v<lo) {v+=range;if(v<lo) {wraps=long((v-lo)/range)-1;v-=range*double(wraps);}--wraps;}
                if(wraps&1)v=hi+lo-v;
                return v;
            }
            case Op::mix:return a+(b-a)*c;
            case Op::dbtoa:return std::pow(10.,a*.05);case Op::atodb:return a<=0?-999:20*std::log10(a);
            case Op::mstosamps:return a*rate*.001;case Op::sampstoms:return a*1000/rate;
            case Op::jump:case Op::jumpZero:case Op::delayRead:case Op::delayWrite:case Op::tableRead:case Op::tableReadPhase:case Op::tableSample:case Op::tableSamplePhase:case Op::tableWrite:case Op::tableDim:case Op::tableChannels:case Op::noise:case Op::change:case Op::phasor:case Op::snapshotLoop:return 0;
        }
        return 0;
    }
    static bool identifier(const std::string& s) {
        return !s.empty() && ((s[0]>='a' && s[0]<='z') || (s[0]>='A' && s[0]<='Z') || s[0]=='_');
    }
    static std::vector<std::string> tokens(const std::string& text) {
        if(text.size()>1024*1024) throw std::invalid_argument("GenExpr source exceeds preparation budget");
        std::vector<std::string> result;
        for(size_t i=0;i<text.size();) {
            const auto ch=text[i];
            if(ch==' ' || ch=='\n' || ch=='\r' || ch=='\t') {++i;continue;}
            if(text.compare(i,2,"//")==0) {const auto end=text.find('\n',i+2);i=end==std::string::npos?text.size():end;continue;}
            if(text.compare(i,2,"/*")==0) {const auto end=text.find("*/",i+2);if(end==std::string::npos)throw std::invalid_argument("Unterminated GenExpr comment");i=end+2;continue;}
            const auto start=i;
            if((ch>='0' && ch<='9') || (ch=='.' && i+1<text.size() && text[i+1]>='0' && text[i+1]<='9')) {
                char* end=nullptr;const double value=std::strtod(text.c_str()+i,&end);
                if(!std::isfinite(value) || end==text.c_str()+i)throw std::invalid_argument("Invalid GenExpr number");
                if(std::abs(value)>9007199254740991.)throw std::invalid_argument("Large Gen numeric literals need verified constant semantics");
                i=size_t(end-text.c_str());
            } else if(ch=='"') {
                ++i;
                while(i<text.size() && text[i]!='"') {
                    if(text[i]=='\\' || text[i]=='\n' || text[i]=='\r')throw std::invalid_argument("Unsupported GenExpr string escape");
                    ++i;
                }
                if(i==text.size())throw std::invalid_argument("Unterminated GenExpr string");
                ++i;
            } else if(identifier(std::string(1,ch))) {
                while(i<text.size() && (identifier(std::string(1,text[i])) || (text[i]>='0' && text[i]<='9')))++i;
            } else {
                ++i;
                if(i<text.size()) {
                    const auto pair=text.substr(start,2);
                    if(pair=="<=" || pair==">=" || pair=="==" || pair=="!=" || pair=="&&" || pair=="||" || pair=="+=" || pair=="-=" || pair=="*=" || pair=="/=")++i;
                }
            }
            result.push_back(text.substr(start,i-start));
            if(result.size()>65536)throw std::invalid_argument("GenExpr token budget exceeded");
        }
        result.push_back("");return result;
    }
    class Compiler {
        Expression& out;
        std::vector<std::string> source;
        size_t pos=0,end=0;
        using Scope=std::map<std::string,Variable>;
        Scope scope;
        std::map<std::string,int> delayScope,tableScope;
        struct Function { std::vector<std::string> arguments;size_t begin,end; };
        std::map<std::string,Function> functions;
        std::vector<std::string> callStack;
        std::vector<size_t> returns;
        std::vector<std::vector<size_t>> continueJumps;
        enum class ArgumentKind { number, delay, table };
        struct Argument { ArgumentKind kind=ArgumentKind::number;int slot=0; };
        std::vector<int> resultRegisters;
        size_t resultArity=0;
        int resultRegister=-1,expressionDepth=0,statementDepth=0;
        [[noreturn]] void fail(const std::string& why) const {throw std::invalid_argument("GenExpr: "+why+" near token "+std::to_string(pos)+" ("+source[std::min(pos,source.size()-1)]+")");}
        bool take(const std::string& value) {if(pos<end && source[pos]==value){++pos;return true;}return false;}
        void expect(const std::string& value) {if(!take(value))fail("expected "+value);}
        std::string name() {if(pos>=end || !identifier(source[pos]))fail("expected identifier");return source[pos++];}
        int reg(double value=0,ValueInfo info={}) {
            if(out.initial_.size()>=16384)fail("register budget exceeded");
            out.initial_.push_back(value);out.info_.push_back(info);return int(out.initial_.size()-1);
        }
        size_t instruction(Op op,int dst=0,int a=0,int b=0,int c=0) {
            if(out.code_.size()>=16384)fail("instruction budget exceeded");
            if(op==Op::noise || op==Op::change || op==Op::phasor || op==Op::delayRead || op==Op::tableRead || op==Op::tableReadPhase || op==Op::tableSample || op==Op::tableSamplePhase || op==Op::tableDim || op==Op::tableChannels)out.info_[dst]={};
            else if(op!=Op::jump && op!=Op::jumpZero && op!=Op::delayWrite && op!=Op::tableWrite) {
                const int arity=(op==Op::clip || op==Op::mix || op==Op::choose || op==Op::wrap || op==Op::fold || op==Op::modConstant)?3:
                    (op==Op::add || op==Op::sub || op==Op::mul || op==Op::div || op==Op::mod ||
                     (op>=Op::less && op<=Op::logicalOr) || op==Op::minimum || op==Op::maximum || op==Op::power || op==Op::arcTangent2)?2:1;
                const auto x=out.info_[a],y=out.info_[b],z=out.info_[c];ValueInfo info;
                if(x.constant && (arity<2 || y.constant) && (arity<3 || z.constant)) {
                    const auto value=calculate(op,x.value,y.value,z.value,out.rate_);
                    if(std::isfinite(value))info=ValueInfo::literal(value);
                } else if(op==Op::move)info=x;
                else if(op==Op::moveInteger || op==Op::logicalNot || (op>=Op::less && op<=Op::logicalOr))info.integer=true;
                else if(op==Op::choose)info=ValueInfo::merge(y,z);
                else if(op==Op::neg || op==Op::absolute)info.integer=x.integer;
                else if(op==Op::add || op==Op::sub || op==Op::mul || op==Op::minimum || op==Op::maximum)info.integer=x.integer && y.integer;
                if(op==Op::move || op==Op::add || op==Op::sub || op==Op::mul || op==Op::minimum || op==Op::maximum || op==Op::neg || op==Op::absolute || op==Op::choose)
                    info.ambiguous=x.ambiguous || (arity>1 && y.ambiguous) || (arity>2 && z.ambiguous);
                out.info_[dst]=info;
            }
            out.code_.push_back({op,dst,a,b,c});return out.code_.size()-1;
        }
        int unary(Op op,int a) {const int dst=reg();instruction(op,dst,a);return dst;}
        int binary(Op op,int a,int b) {
            const int dst=reg();
            if(op==Op::mod && out.info_[b].constant) {
                const double divisor=std::abs(out.info_[b].value);
                const double reciprocal=divisor>std::numeric_limits<double>::epsilon()?1/divisor:0;
                const int inverse=reg(reciprocal,ValueInfo::literal(reciprocal));
                instruction(Op::modConstant,dst,a,b,inverse);
            } else instruction(op,dst,a,b);
            return dst;
        }
        int port(const std::string& value,const std::string& prefix) {
            if(value==prefix)return 0;
            if(value.compare(0,prefix.size(),prefix)!=0)return -1;
            const auto suffix=value.substr(prefix.size());
            if(suffix.empty() || suffix.find_first_not_of("0123456789")!=std::string::npos)return -1;
            if(suffix.size()>2)fail("port budget exceeded");
            const int n=std::stoi(suffix);if(n<1 || n>64)fail("invalid port");return n-1;
        }
        int variable(const std::string& key,bool writing=false) {
            if(delayScope.count(key) || tableScope.count(key))fail("Storage reference is not a numeric value: "+key);
            auto found=scope.find(key);
            if(found!=scope.end()) {if(writing && !found->second.writable)fail("assignment to read-only value "+key);return found->second.reg;}
            if(!writing) {
                const std::map<std::string,double> constants={{"pi",3.14159265358979323846},{"twopi",6.28318530717958647692},{"halfpi",1.57079632679489661923},{"samplerate",out.rate_},{"true",1},{"false",0}};
                auto c=constants.find(key);if(c!=constants.end()) {const int r=reg(c->second,ValueInfo::literal(c->second));scope[key]={r,false};return r;}
                const int input=port(key,"in");
                if(input>=0 && callStack.empty()) {
                    if(out.inputs_[input]<0)out.inputs_[input]=reg(0,size_t(input)<out.inputInfo_.size()?out.inputInfo_[input]:ValueInfo{});
                    out.inputCount_=std::max(out.inputCount_,input+1);scope[key]={out.inputs_[input],false};return out.inputs_[input];
                }
                fail("undefined value "+key);
            }
            if(port(key,"in")>=0 || key=="samplerate" || key=="pi" || key=="twopi" || key=="halfpi")fail("assignment to reserved value");
            int r=reg();scope[key]={r,true};
            const int output=port(key,"out");
            if(output>=0) {
                if(!callStack.empty())fail("function must return its output");
                if(out.outputs_[output]>=0)r=out.outputs_[output];else out.outputs_[output]=r;
                scope[key]={r,true};out.outputCount_=std::max(out.outputCount_,output+1);
            }
            return r;
        }
        std::vector<int> call(const std::string& key,const std::vector<Argument>& supplied) {
            if(functions.count(key))return userCall(key,supplied);
            std::vector<int> args;
            for(const auto& argument:supplied) {
                if(argument.kind!=ArgumentKind::number)fail("storage argument to numeric operator "+key);
                args.push_back(argument.slot);
            }
            if(key=="change" || key=="phasor") {
                if(args.empty() || args.size()>(key=="change"?1u:2u))fail("wrong arguments for "+key);
                // Max removes the derivative of a compile-time constant,
                // including its otherwise observable first-sample transition.
                if(key=="change" && out.info_[args[0]].constant)return {reg(0,ValueInfo::literal(0))};
                const int state=int(out.operatorStates_.size());out.operatorStates_.push_back(0);
                const int result=reg();
                if(key=="change")instruction(Op::change,result,args[0],0,state);
                else instruction(Op::phasor,result,args[0],args.size()==2?args[1]:reg(0,ValueInfo::literal(0)),state);
                return {result};
            }
            if(key=="noise") {
                if(!args.empty())fail("noise requires no arguments");
                if(!out.noise_)out.noise_=std::make_shared<Noise>();
                const int result=reg();instruction(Op::noise,result);return {result};
            }
            if(key=="slide") {
                if(args.size()!=3)fail("slide requires input, up and down");
                if(out.info_[args[0]].constant && out.info_[args[1]].constant && out.info_[args[2]].constant)return {args[0]};
                const int state=reg();out.histories_.push_back({state,0,0});
                const int greater=binary(Op::greater,args[0],state),direction=reg();
                instruction(Op::choose,direction,greater,args[1],args[2]);
                const int divisor=binary(Op::maximum,reg(1,ValueInfo::literal(1)),direction);
                const int delta=binary(Op::div,binary(Op::sub,args[0],state),divisor);
                const int result=binary(Op::add,state,delta);instruction(Op::move,state,result);
                out.info_[state]={};out.info_[result]={};return {result};
            }
            if(key=="fixdenorm") {
                if(args.size()!=1)fail("wrong arguments for fixdenorm");
                // The installed Max MSP_ON_CLANG profile defines
                // GENLIB_NO_DENORM_TEST: this operation preserves its input.
                // Amplified normal/subnormal Max captures verify this path.
                // Do not substitute the standalone-export flushing macro.
                return {args[0]};
            }
            const std::map<std::string,std::pair<Op,int>> builtins={
                {"abs",{Op::absolute,1}},{"min",{Op::minimum,2}},{"minimum",{Op::minimum,2}},
                {"max",{Op::maximum,2}},{"maximum",{Op::maximum,2}},{"pow",{Op::power,2}},
                {"sqrt",{Op::squareRoot,1}},{"exp",{Op::exponential,1}},{"log",{Op::logarithm,1}},
                {"sin",{Op::sine,1}},{"cos",{Op::cosine,1}},{"tan",{Op::tangent,1}},{"tanh",{Op::hyperbolicTangent,1}},
                {"asin",{Op::arcSine,1}},{"acos",{Op::arcCosine,1}},{"atan",{Op::arcTangent,1}},{"atan2",{Op::arcTangent2,2}},{"sinh",{Op::hyperbolicSine,1}},{"cosh",{Op::hyperbolicCosine,1}},
                {"log10",{Op::logarithm10,1}},{"log2",{Op::logarithm2,1}},{"exp2",{Op::exponential2,1}},
                {"floor",{Op::floor,1}},{"ceil",{Op::ceil,1}},{"round",{Op::round,1}},{"trunc",{Op::trunc,1}},
                {"clip",{Op::clip,3}},{"clamp",{Op::clip,3}},{"mix",{Op::mix,3}},{"wrap",{Op::wrap,3}},{"fold",{Op::fold,3}},
                {"dbtoa",{Op::dbtoa,1}},{"atodb",{Op::atodb,1}},{"mstosamps",{Op::mstosamps,1}},{"sampstoms",{Op::sampstoms,1}}};
            // Gen's int()/float() conversions: int truncates and types the
            // result as integer for downstream inference; float clears it.
            if(key=="int" || key=="float") {
                if(args.size()!=1)fail("wrong arguments for "+key);
                const int r=reg();instruction(key=="int"?Op::moveInteger:Op::move,r,args[0]);
                if(key=="float")out.info_[r].integer=false;
                return {r};
            }
            auto builtin=builtins.find(key);
            if(builtin!=builtins.end()) {
                if(int(args.size())!=builtin->second.second)fail("wrong arguments for "+key);
                const int r=reg();instruction(builtin->second.first,r,args[0],args.size()>1?args[1]:0,args.size()>2?args[2]:0);return {r};
            }
            fail("unsupported function/operator "+key);
        }
        std::vector<int> userCall(const std::string& key,const std::vector<Argument>& args) {
            auto f=functions.find(key);if(f==functions.end())fail("unsupported function/operator "+key);
            if(f->second.arguments.size()!=args.size())fail("wrong arguments for "+key);
            if(callStack.size()>=16 || std::find(callStack.begin(),callStack.end(),key)!=callStack.end())fail("recursive function");
            auto oldDelayScope=std::move(delayScope);delayScope={};
            auto oldTableScope=std::move(tableScope);tableScope={};
            auto oldScope=std::move(scope);auto oldReturns=std::move(returns);const auto oldPos=pos,oldEnd=end;const int oldResult=resultRegister;
            auto oldResults=std::move(resultRegisters);const auto oldArity=resultArity;
            auto oldContinues=std::move(continueJumps);continueJumps={};
            scope={};returns={};callStack.push_back(key);resultRegister=reg();resultRegisters={resultRegister};resultArity=0;
            for(size_t i=0;i<args.size();++i) {
                const auto& argument=args[i];const auto& name=f->second.arguments[i];
                if(argument.kind==ArgumentKind::delay)delayScope[name]=argument.slot;
                else if(argument.kind==ArgumentKind::table)tableScope[name]=argument.slot;
                else {
                    const int r=reg();const bool integer=out.info_[argument.slot].integer;
                    scope[name]={r,true,integer,!integer,out.info_[argument.slot].ambiguous};instruction(Op::move,r,argument.slot);
                }
            }
            pos=f->second.begin;end=f->second.end;
            while(pos<end)statement(statementEnd(pos)==end);
            if(returns.empty())fail("function has no return");
            for(auto jump:returns)out.code_[jump].b=int(out.code_.size());
            const auto result=resultRegisters;
            callStack.pop_back();tableScope=std::move(oldTableScope);delayScope=std::move(oldDelayScope);scope=std::move(oldScope);returns=std::move(oldReturns);pos=oldPos;end=oldEnd;resultRegister=oldResult;
            resultRegisters=std::move(oldResults);resultArity=oldArity;
            continueJumps=std::move(oldContinues);
            return result;
        }
        std::vector<Argument> arguments() {
            std::vector<Argument> args;
            if(!take(")")) {
                do {
                    if(args.size()>=64)fail("argument budget exceeded");
                    const bool standalone=pos+1<end && (source[pos+1]=="," || source[pos+1]==")");
                    auto delay=delayScope.find(source[pos]),table=tableScope.find(source[pos]);
                    if(standalone && delay!=delayScope.end()) {args.push_back({ArgumentKind::delay,delay->second});++pos;}
                    else if(standalone && table!=tableScope.end()) {args.push_back({ArgumentKind::table,table->second});++pos;}
                    else args.push_back({ArgumentKind::number,expression()});
                } while(take(","));
                expect(")");
            }
            return args;
        }
        int delayMethod(const std::string& key,bool allowVoid) {
            const auto found=delayScope.find(key);if(found==delayScope.end())fail("unresolved Delay: "+key);
            const auto method=name();expect("(");const int value=expression();
            Interpolation interpolation=Interpolation::linear;
            if(take(",")) {
                if(method!="read" || name()!="interp")fail("unsupported Delay method attribute");
                expect("=");
                if(pos>=end || source[pos].size()<2 || source[pos].front()!='"' || source[pos].back()!='"')fail("Delay interp must be a quoted name");
                interpolation=delayInterpolation(source[pos].substr(1,source[pos].size()-2));++pos;
            }
            expect(")");
            if(method=="read") {const int result=reg();instruction(Op::delayRead,result,value,found->second,int(interpolation));return result;}
            if(method=="write") {
                if(!allowVoid)fail("Delay.write has no numeric result");
                instruction(Op::delayWrite,0,value,found->second);return -1;
            }
            fail("unsupported Delay method: "+method);
        }
        int tableCall(const std::string& key,bool allowVoid) {
            const auto reference=name();auto found=tableScope.find(reference);
            if(found==tableScope.end())fail("unresolved table: "+reference);
            if(key=="dim" || key=="channels") {
                expect(")");const int result=reg();instruction(key=="dim"?Op::tableDim:Op::tableChannels,result,found->second);return result;
            }
            expect(",");const int first=expression();int index=first,channel=reg(0,ValueInfo::literal(0));
            if(key=="poke") {expect(",");index=expression();}
            // sample defaults to phase indexing (refpage); peek to samples.
            bool phase=key=="sample",hasChannel=false,hasIndex=false;
            while(take(",")) {
                if(pos+1<end && source[pos+1]=="=") {
                    const auto attribute=name();expect("=");
                    if((key!="peek" && key!="sample") || attribute!="index" || hasIndex)fail("unsupported or repeated table attribute "+attribute);
                    hasIndex=true;
                    if(take("\"phase\""))phase=true;
                    else if(take("\"samples\""))phase=false;
                    else fail("unsupported table index mode");
                } else {
                    if(hasChannel || hasIndex)fail("unexpected table channel argument");
                    channel=expression();hasChannel=true;
                }
            }
            expect(")");
            if(key=="poke") {
                if(!allowVoid)fail("poke has no numeric result");
                instruction(Op::tableWrite,found->second,first,index,channel);return -1;
            }
            const int result=reg();
            if(key=="sample")instruction(phase?Op::tableSamplePhase:Op::tableSample,result,index,channel,found->second);
            else instruction(phase?Op::tableReadPhase:Op::tableRead,result,index,channel,found->second);
            return result;
        }
        void tableDeclaration(bool internal) {
            do {
                const auto key=name();if(scope.count(key) || delayScope.count(key) || tableScope.count(key))fail("duplicate declaration "+key);
                std::shared_ptr<Table> table;std::string binding=key;
                if(internal) {
                    expect("(");const int size=expression();int channels=reg(1,ValueInfo::literal(1));
                    if(take(","))channels=expression();expect(")");
                    if(!out.info_[size].constant || !out.info_[channels].constant)fail("Data dimensions must be preparation-time constants");
                    const double frames=out.info_[size].value,count=out.info_[channels].value;
                    if(frames<1 || frames>4194304 || count<1 || count>64 || std::trunc(frames)!=frames || std::trunc(count)!=count)fail("invalid Data dimensions");
                    const size_t samples=size_t(frames)*size_t(count);
                    if(samples>out.tableBudget_-out.tableSamples_)fail("Data aggregate sample budget exceeded");
                    out.tableSamples_+=samples;
                    if(out.prepareDelayStorage_)table=std::make_shared<Table>(size_t(frames),size_t(count),false);
                } else {
                    if(take("(")) {
                        if(pos>=end || source[pos].size()<2 || source[pos].front()!='"' || source[pos].back()!='"')fail("Buffer binding must be a quoted name");
                        binding=source[pos].substr(1,source[pos].size()-2);++pos;expect(")");
                    }
                    if(out.buffers_) {auto found=out.buffers_->find(binding);if(found!=out.buffers_->end())table=found->second;}
                }
                tableScope[key]=int(out.tables_.size());out.tables_.push_back({key,binding,table,table,internal});
            } while(take(","));expect(";");
        }
        int expression(int precedence=0,bool allowVoid=false) {
            if(++expressionDepth>64)fail("expression nesting budget exceeded");
            int left;
            if(take("-"))left=unary(Op::neg,expression(8));
            else if(take("+"))left=expression(8);
            else if(take("!"))left=unary(Op::logicalNot,expression(8));
            else if(take("(")) {left=expression();expect(")");}
            else if(pos<end && identifier(source[pos])) {
                const auto key=name();
                if(take("."))left=delayMethod(key,allowVoid);
                else if(take("(")) {
                    if(key=="peek" || key=="poke" || key=="sample" || key=="dim" || key=="channels")left=tableCall(key,allowVoid);
                    else {
                        left=call(key,arguments()).front();
                    }
                } else left=variable(key);
            } else {
                if(pos>=end)fail("missing expression");
                char* tail=nullptr;double value=std::strtod(source[pos].c_str(),&tail);
                if(tail==source[pos].c_str() || *tail || !std::isfinite(value))fail("invalid expression");
                ++pos;left=reg(value,ValueInfo::literal(value));
            }
            const std::map<std::string,std::pair<int,Op>> ops={{"||",{1,Op::logicalOr}},{"&&",{2,Op::logicalAnd}},
                {"==",{3,Op::equal}},{"!=",{3,Op::unequal}},{"<",{4,Op::less}},{"<=",{4,Op::lessEqual}},
                {">",{4,Op::greater}},{">=",{4,Op::greaterEqual}},{"+",{5,Op::add}},{"-",{5,Op::sub}},
                {"*",{6,Op::mul}},{"/",{6,Op::div}},{"%",{6,Op::mod}}};
            while(pos<end) {
                auto op=ops.find(source[pos]);if(op==ops.end() || op->second.first<precedence)break;
                if(left<0)fail("Delay.write has no numeric result");
                ++pos;const int right=expression(op->second.first+1);left=binary(op->second.second,left,right);
            }
            if(precedence==0 && take("?")) {if(left<0)fail("Delay.write has no numeric result");const int yes=expression();expect(":");const int no=expression();const int r=reg();instruction(Op::choose,r,left,yes,no);left=r;}
            --expressionDepth;return left;
        }
        double literal() {
            bool neg=take("-");take("+");
            if(pos>=end)fail("missing declaration value");
            char* tail=nullptr;const double n=std::strtod(source[pos].c_str(),&tail);
            if(tail==source[pos].c_str() || *tail || !std::isfinite(n))fail("non-literal declaration needs support");
            ++pos;return neg?-n:n;
        }
        void delayDeclaration() {
            do {
                const auto key=name();if(scope.count(key) || delayScope.count(key) || tableScope.count(key))fail("duplicate declaration "+key);
                double maximum=out.rate_;
                if(take("(")) {
                    const int value=expression();expect(")");
                    if(!out.info_[value].constant)fail("Delay size must be a preparation-time constant");
                    maximum=out.info_[value].value;
                }
                if(maximum<1 || maximum>4194304 || std::trunc(maximum)!=maximum)fail("invalid Delay size");
                const auto samples=Delay::storageFor(size_t(maximum));
                if(samples>out.delayBudget_-out.delaySamples_)fail("Delay aggregate sample budget exceeded");
                out.delaySamples_+=samples;
                delayScope[key]=int(out.delays_.size());
                out.delays_.push_back(out.prepareDelayStorage_?std::make_unique<Delay>(size_t(maximum)):nullptr);
            } while(take(","));expect(";");
        }
        void declaration(bool parameter) {
            do {
                const auto key=name();if(scope.count(key) || delayScope.count(key) || tableScope.count(key))fail("duplicate declaration "+key);
                double initial=0,minimum=-1e300,maximum=1e300;
                if(take("(")) {
                    initial=literal();
                    while(take(",")) {if(!parameter)fail("History attributes need support");const auto attr=name();expect("=");const double value=literal();if(attr=="min")minimum=value;else if(attr=="max")maximum=value;else fail("unsupported parameter attribute "+attr);}
                    expect(")");
                }
                const int r=reg(initial);
                if(parameter) {
                    if(!callStack.empty() || minimum>maximum)fail("invalid parameter declaration");
                    if(auto value=out.parameterDefaults_.find(key);value!=out.parameterDefaults_.end())initial=value->second;
                    initial=std::clamp(initial,minimum,maximum);
                    out.parameters_.push_back({key,r,initial,minimum,maximum,initial});scope[key]={r,false};
                    out.info_[r]=out.constantParameters_?ValueInfo::literal(initial):ValueInfo{};
                } else {out.histories_.push_back({r,initial,initial});scope[key]={r,true,false,true};}
            } while(take(","));expect(";");
        }
        void assignment() {
            const auto key=name();
            if(take(",")) {
                std::vector<std::string> names={key};
                do {
                    if(names.size()>=64)fail("assignment output budget exceeded");
                    names.push_back(name());
                } while(take(","));
                expect("=");const auto function=name();expect("(");
                const auto values=call(function,arguments());
                if(values.size()<names.size())fail("function returns fewer values than assignment destinations");
                for(size_t i=0;i<names.size();++i)storeAssignment(names[i],values[i]);
                return;
            }
            if(pos>=end)fail("missing assignment");
            const auto op=source[pos++];
            if(op!="=" && op!="+=" && op!="-=" && op!="*=" && op!="/=")fail("unsupported assignment "+op);
            const int previous=op=="="?-1:variable(key);
            int value=expression();
            if(previous>=0)value=binary(op=="+="?Op::add:op=="-="?Op::sub:op=="*="?Op::mul:Op::div,previous,value);
            storeAssignment(key,value);
        }
        void storeAssignment(const std::string& key,int value) {
            const int destination=variable(key,true);
            const auto target=scope.at(key);
            if(target.ambiguousArgument)fail("function argument type after a loop needs verified inference");
            instruction(target.fixedInteger?Op::moveInteger:Op::move,destination,value);
            if(target.fixedFloating)out.info_[destination].integer=false;
        }
        void optimizeSnapshotLoop(size_t start,size_t branch,size_t increment,size_t back) {
            // Recognize data movement in the prepared IR, independent of source
            // names or device identity. All other loops keep the interpreter's
            // normal watchdog. No branches, delay writes, table reads, mutable
            // bounds or loop-carried arithmetic are eligible.
            if(!out.optimizeSnapshots_ || branch!=start+1 || back!=increment+2)return;
            const auto condition=out.code_[start],add=out.code_[increment],assign=out.code_[increment+1];
            if(condition.op!=Op::less || add.op!=Op::add || add.a!=condition.a ||
               (assign.op!=Op::move && assign.op!=Op::moveInteger) || assign.dst!=condition.a || assign.a!=add.dst ||
               !out.info_[add.b].constant || out.info_[add.b].value!=1)return;
            const int index=condition.a,limit=condition.b;
            std::vector<bool> changed(out.initial_.size());
            for(size_t at=branch+1;at<increment;++at) {
                const auto& op=out.code_[at];
                if(op.op!=Op::tableWrite)changed[op.dst]=true;
            }
            if(changed[index] || changed[limit] || changed[add.b] || limit==index)return;
            struct Alias {int kind=0,offset=-1,delay=-1;Interpolation interpolation=Interpolation::linear;};
            std::vector<Alias> aliases(out.initial_.size());
            SnapshotLoop loop{index,limit,{}};
            for(size_t at=branch+1;at<increment;++at) {
                const auto& op=out.code_[at];
                if(op.op==Op::sub && op.b==index && op.a!=index && !changed[op.a])aliases[op.dst]={1,op.a};
                else if(op.op==Op::move && aliases[op.a].kind)aliases[op.dst]=aliases[op.a];
                else if(op.op==Op::delayRead && aliases[op.a].kind==1)
                    aliases[op.dst]={2,aliases[op.a].offset,op.b,Interpolation(op.c)};
                else if(op.op==Op::tableWrite && op.b==index && op.c!=index && !changed[op.c] && aliases[op.a].kind==2) {
                    const auto a=aliases[op.a];loop.copies.push_back({op.dst,a.delay,a.offset,op.c,a.interpolation});
                } else return;
            }
            if(loop.copies.empty() || loop.copies.size()>8)return;
            out.code_[start].op=Op::snapshotLoop;out.code_[start].c=int(out.snapshotLoops_.size());
            out.snapshotLoops_.push_back(std::move(loop));
        }
        size_t statementEnd(size_t start,unsigned depth=0) const {
            if(depth>64)fail("statement lookahead nesting budget exceeded");
            if(start>=end)return end;
            if(source[start]=="if" || source[start]=="for" || source[start]=="while") {
                size_t at=start+1;int parens=0;
                for(;at<end;++at) {
                    if(source[at]=="(")++parens;
                    if(source[at]==")" && --parens==0) {++at;break;}
                }
                at=statementEnd(at,depth+1);
                if(source[start]=="if" && at<end && source[at]=="else")at=statementEnd(at+1,depth+1);
                return at;
            }
            size_t at=start;int braces=0,parens=0;
            for(;at<end;++at) {
                if(source[at]=="{")++braces;
                if(source[at]=="}") {if(--braces==0)return at+1;}
                if(source[at]=="(")++parens;if(source[at]==")")--parens;
                if(!braces && !parens && source[at]==";")return at+1;
            }
            return at;
        }
        void statement(bool terminalReturn=false) {
            if(++statementDepth>64)fail("statement nesting budget exceeded");
            if(take(";")) {}
            else if(take("{")) {
                const auto close=statementEnd(pos-1)-1;
                while(pos<end && source[pos]!="}")statement(terminalReturn && statementEnd(pos)==close);
                expect("}");
            }
            else if(take("Delay"))delayDeclaration();
            else if(take("Data"))tableDeclaration(true);
            else if(take("Buffer"))tableDeclaration(false);
            else if(take("History"))declaration(false);
            else if(take("Param"))declaration(true);
            else if(take("if")) {
                expect("(");const int condition=expression();expect(")");
                const auto branch=instruction(Op::jumpZero,0,condition);
                const auto before=out.info_;
                statement(terminalReturn);const auto yes=out.info_;const auto done=instruction(Op::jump);out.code_[branch].b=int(out.code_.size());
                for(size_t i=0;i<out.info_.size();++i)out.info_[i]=i<before.size()?before[i]:ValueInfo::literal(0);
                if(take("else"))statement(terminalReturn);out.code_[done].b=int(out.code_.size());
                for(size_t i=0;i<out.info_.size();++i)out.info_[i]=ValueInfo::merge(i<yes.size()?yes[i]:ValueInfo::literal(0),out.info_[i]);
            } else if(take("for")) {
                expect("(");assignment();expect(";");const auto start=out.code_.size();
                size_t closeParen=pos;int parens=0;
                for(;closeParen<end;++closeParen) {
                    if(source[closeParen]=="(")++parens;
                    if(source[closeParen]==")") {if(!parens)break;--parens;}
                }
                if(closeParen==end)fail("unterminated for header");
                const size_t bodyEnd=statementEnd(closeParen+1);std::vector<int> mutated;
                for(size_t at=pos;at+1<bodyEnd;++at)if(source[at+1]=="=" || source[at+1]=="+=" || source[at+1]=="-=" || source[at+1]=="*=" || source[at+1]=="/=") {
                    auto variable=scope.find(source[at]);if(variable==scope.end())continue;
                    const auto v=variable->second;
                    if(!v.fixedInteger && !v.fixedFloating) {out.info_[v.reg]={false,false,0,true};mutated.push_back(v.reg);}
                }
                const int condition=expression();expect(";");const size_t increment=pos;
                pos=closeParen;const size_t close=pos;expect(")");const auto branch=instruction(Op::jumpZero,0,condition);
                continueJumps.emplace_back();statement();
                // Installed Max Gen continue jumps to the condition, skipping
                // the for increment. The bounded original probe yields 43,
                // whereas C-style increment-first continuation yields 40.
                for(const auto jump:continueJumps.back())out.code_[jump].b=int(start);
                continueJumps.pop_back();
                const size_t after=pos,incrementCode=out.code_.size();pos=increment;assignment();if(pos!=close)fail("invalid loop increment");pos=after;
                const auto back=instruction(Op::jump,0,0,int(start));out.code_[branch].b=int(out.code_.size());
                optimizeSnapshotLoop(start,branch,incrementCode,back);
                for(int r:mutated)out.info_[r]={false,false,0,true};
            } else if(take("while")) {
                // A for loop without initialiser or increment: continue jumps
                // to the condition, and the interpreter's instruction cap
                // bounds a runaway loop exactly as it does for 'for'.
                expect("(");const auto start=out.code_.size();
                size_t closeParen=pos;int parens=0;
                for(;closeParen<end;++closeParen) {
                    if(source[closeParen]=="(")++parens;
                    if(source[closeParen]==")") {if(!parens)break;--parens;}
                }
                if(closeParen==end)fail("unterminated while header");
                const size_t bodyEnd=statementEnd(closeParen+1);std::vector<int> mutated;
                for(size_t at=closeParen+1;at+1<bodyEnd;++at)if(source[at+1]=="=" || source[at+1]=="+=" || source[at+1]=="-=" || source[at+1]=="*=" || source[at+1]=="/=") {
                    auto variable=scope.find(source[at]);if(variable==scope.end())continue;
                    const auto v=variable->second;
                    if(!v.fixedInteger && !v.fixedFloating) {out.info_[v.reg]={false,false,0,true};mutated.push_back(v.reg);}
                }
                const int condition=expression();expect(")");const auto branch=instruction(Op::jumpZero,0,condition);
                continueJumps.emplace_back();statement();
                for(const auto jump:continueJumps.back())out.code_[jump].b=int(start);
                continueJumps.pop_back();
                instruction(Op::jump,0,0,int(start));out.code_[branch].b=int(out.code_.size());
                for(int r:mutated)out.info_[r]={false,false,0,true};
            } else if(take("continue")) {
                if(continueJumps.empty())fail("continue outside loop");
                expect(";");continueJumps.back().push_back(instruction(Op::jump));
            } else if(take("return")) {
                if(resultRegister<0)fail("return outside function");
                std::vector<int> values;
                do {
                    if(values.size()>=64)fail("function output budget exceeded");
                    values.push_back(expression());
                } while(take(","));expect(";");
                if(resultArity && resultArity!=values.size())fail("inconsistent function return count");
                resultArity=values.size();while(resultRegisters.size()<values.size())resultRegisters.push_back(reg());
                for(size_t i=0;i<values.size();++i)instruction(Op::move,resultRegisters[i],values[i]);
                if(!terminalReturn)fail("non-terminal return needs verified Gen semantics");
                returns.push_back(instruction(Op::jump));
            } else if(pos+1<end && identifier(source[pos]) && (source[pos+1]=="," || source[pos+1]=="=" || source[pos+1]=="+=" || source[pos+1]=="-=" || source[pos+1]=="*=" || source[pos+1]=="/=")) {
                assignment();if(pos<end)expect(";");
            } else {
                const int value=expression(0,true);if(value>=0)instruction(Op::move,variable("out1",true),value);if(pos<end)expect(";");
            }
            --statementDepth;
        }
    public:
        Compiler(Expression& target,const std::string& text):out(target),source(tokens(text)) {
            end=source.size()-1;
            // Function definitions are preparation-time declarations. Their
            // bodies are expanded per call site, giving History independent state.
            std::vector<std::pair<size_t,size_t>> spans;
            int depth=0;
            for(size_t i=0;i<end;++i) {
                if(depth==0 && identifier(source[i]) && i+1<end && source[i+1]=="(" && source[i]!="if" && source[i]!="for" && source[i]!="while") {
                    size_t j=i+2;int parens=1;
                    while(j<end && parens) {if(source[j]=="(")++parens;if(source[j]==")")--parens;++j;}
                    if(j<end && source[j]=="{") {
                        Function function;for(size_t k=i+2;k+1<j;++k) {
                            if((k-i-2)%2==0) {if(!identifier(source[k]) || std::find(function.arguments.begin(),function.arguments.end(),source[k])!=function.arguments.end())fail("invalid or duplicate function argument");function.arguments.push_back(source[k]);}
                            else if(source[k]!=",")fail("invalid function signature");
                        }
                        function.begin=j+1;int braces=1;size_t k=j+1;
                        while(k<end && braces) {if(source[k]=="{")++braces;if(source[k]=="}")--braces;++k;}
                        if(braces)fail("unterminated function");function.end=k-1;
                        if(!functions.emplace(source[i],function).second)fail("duplicate function");
                        spans.push_back({i,k});i=k-1;continue;
                    }
                }
                if(source[i]=="{")++depth;if(source[i]=="}")--depth;
            }
            while(pos<end) {
                auto span=std::find_if(spans.begin(),spans.end(),[&](auto range){return range.first==pos;});
                if(span!=spans.end())pos=span->second;else statement();
            }
            if(out.outputCount_==0)fail("no output");
        }
    };
public:
    Expression(const std::string& text,double rate,std::vector<ValueInfo> inputs={},bool constantParameters=false,
               std::map<std::string,double> defaults={},size_t delayBudget=8388608,bool prepareDelayStorage=true,const BufferRegistry* buffers=nullptr,size_t tableBudget=8388608,std::shared_ptr<Noise> noise={},bool optimizeSnapshots=true):optimizeSnapshots_(optimizeSnapshots),noise_(std::move(noise)),buffers_(buffers),tableBudget_(tableBudget),inputInfo_(std::move(inputs)),constantParameters_(constantParameters),parameterDefaults_(std::move(defaults)),delayBudget_(delayBudget),prepareDelayStorage_(prepareDelayStorage),rate_(rate) {
        if(!std::isfinite(rate) || rate<8000 || rate>384000)throw std::invalid_argument("Invalid Gen sample rate");
        inputs_.fill(-1);outputs_.fill(-1);Compiler compiler(*this,text);registers_=initial_;
    }
    int inputs() const noexcept {return inputCount_;}
    int outputs() const noexcept {return outputCount_;}
    size_t delaySamples() const noexcept {return delaySamples_;}
    size_t tableSamples() const noexcept {return tableSamples_;}
    void prepareBuffers() {
        for(auto& reference:tables_)if(!reference.internal) {
            auto found=buffers_?buffers_->find(reference.binding):BufferRegistry::const_iterator{};
            reference.table=reference.initial=buffers_ && found!=buffers_->end()?found->second:nullptr;
            if(reference.table && reference.table->hasVectorWriter())
                throw std::invalid_argument("record~ and Gen buffer access need whole-vector graph scheduling");
        }
    }
    bool bindBuffer(const std::string& name,std::shared_ptr<Table> table) noexcept {
        if(table && table->hasVectorWriter())return false;
        bool found=false;for(auto& reference:tables_)if(!reference.internal && reference.name==name) {reference.table=table;found=true;}return found;
    }
    size_t instructionCount() const noexcept {return code_.size();}
    size_t snapshotLoopCount() const noexcept {return snapshotLoops_.size();}
    size_t registerCount() const noexcept {return initial_.size();}
    ValueInfo outputInfo(int port) const {return outputs_[port]<0?ValueInfo::literal(0):info_[outputs_[port]];}
    const std::vector<Parameter>& parameters() const noexcept {return parameters_;}
    bool set(const std::string& name,double value) noexcept {
        if(constantParameters_ || !std::isfinite(value))return false;
        for(auto& p:parameters_)if(p.name==name) {p.value=std::clamp(value,p.minimum,p.maximum);return true;}
        return false;
    }
    void reset() noexcept {for(auto& reference:tables_)if(reference.internal && reference.table)reference.table->clear();else if(!reference.internal)reference.table=reference.initial;for(auto& delay:delays_)if(delay)delay->reset();for(auto& s:histories_)s.value=s.initial;std::fill(operatorStates_.begin(),operatorStates_.end(),0);for(auto& p:parameters_)p.value=p.initial;fault_=false;}
    bool process(const double* inputs,double* outputs,unsigned* sharedBudget=nullptr,unsigned* sharedBulkBudget=nullptr) noexcept {
        if(fault_ || !prepareDelayStorage_) {std::fill(outputs,outputs+outputCount_,0);return false;}
        std::copy(initial_.begin(),initial_.end(),registers_.begin());
        for(const auto& s:histories_)registers_[s.reg]=s.value;
        for(const auto& p:parameters_)registers_[p.reg]=p.value;
        for(int i=0;i<inputCount_;++i)if(inputs_[i]>=0)registers_[inputs_[i]]=inputs[i];
        unsigned localBudget=65536;unsigned& budget=sharedBudget?*sharedBudget:localBudget;
        unsigned localBulkBudget=1048576;unsigned& bulkBudget=sharedBulkBudget?*sharedBulkBudget:localBulkBudget;
        for(size_t pc=0;pc<code_.size();) {
            if(!budget) {fault_=true;break;}--budget;
            const auto& op=code_[pc++];
            if(op.op==Op::jump) {pc=size_t(op.b);continue;}
            if(op.op==Op::jumpZero) {if(registers_[op.a]==0)pc=size_t(op.b);continue;}
            if(op.op==Op::snapshotLoop) {
                const auto& loop=snapshotLoops_[op.c];double& index=registers_[loop.index];const double limit=registers_[loop.limit];
                bool eligible=std::isfinite(index) && std::isfinite(limit) && std::abs(index)<0x1p52 && std::abs(limit)<0x1p52 &&
                    index==std::trunc(index) && limit==std::trunc(limit);
                for(const auto& copy:loop.copies)eligible=eligible && std::isfinite(registers_[copy.offset]) &&
                    std::abs(registers_[copy.offset])<0x1p52 && std::isfinite(registers_[copy.channel]);
                if(eligible && limit-index>1) {
                    // Keep one scalar iteration so every temporary, user local,
                    // increment and final condition retains its exact semantics.
                    const double count=limit-index-1,total=count*double(loop.copies.size());
                    if(total>bulkBudget) {fault_=true;break;}bulkBudget-=unsigned(total);
                    const double last=limit-1;
                    for(;index<last;index+=1)for(const auto& copy:loop.copies) {
                        const auto& table=tables_[copy.table].table;
                        const double value=delays_[copy.delay]->read(registers_[copy.offset]-index,copy.interpolation);
                        if(table)table->poke(value,index,registers_[copy.channel]);
                    }
                }
                registers_[op.dst]=index<limit;continue;
            }
            if(op.op==Op::noise) {registers_[op.dst]=noise_->next();continue;}
            if(op.op==Op::change) {
                const double value=registers_[op.a],delta=value-operatorStates_[op.c];
                operatorStates_[op.c]=value;registers_[op.dst]=double(delta>0)-double(delta<0);continue;
            }
            if(op.op==Op::phasor) {
                auto& phase=operatorStates_[op.c];if(registers_[op.b]!=0)phase=0;
                const double increment=registers_[op.a]*(1./rate_);
                phase=calculate(Op::wrap,phase+increment,0,1,rate_);registers_[op.dst]=phase;continue;
            }
            if(op.op==Op::delayRead || op.op==Op::delayWrite) {
                const double value=registers_[op.a];
                if(!std::isfinite(value)) {fault_=true;break;}
                if(op.op==Op::delayWrite)delays_[op.b]->write(value);
                else registers_[op.dst]=delays_[op.b]->read(value,Interpolation(op.c));
                continue;
            }
            if(op.op==Op::tableDim || op.op==Op::tableChannels) {
                const auto& table=tables_[op.a].table;registers_[op.dst]=table?(op.op==Op::tableDim?table->frames():table->channels()):0;continue;
            }
            if(op.op==Op::tableRead) {const auto& table=tables_[op.c].table;registers_[op.dst]=table?table->peek(registers_[op.a],registers_[op.b]):0;continue;}
            if(op.op==Op::tableReadPhase) {const auto& table=tables_[op.c].table;registers_[op.dst]=table && table->frames()?table->peek(registers_[op.a]*double(table->frames()-1),registers_[op.b]):0;continue;}
            if(op.op==Op::tableSample || op.op==Op::tableSamplePhase) {
                // Refpage: linear interpolation, boundmode/channelmode ignore
                // (zero out of range). Phase spans the table like the measured
                // peek phase mapping; sample's own mapping and its
                // out-of-range neighbour reads are UNMEASURED.
                const auto& table=tables_[op.c].table;double position=registers_[op.a];
                if(!table || !table->frames() || !std::isfinite(position)) {registers_[op.dst]=0;continue;}
                if(op.op==Op::tableSamplePhase)position*=double(table->frames()-1);
                const double whole=std::floor(position),fraction=position-whole;
                const double a=table->peek(whole,registers_[op.b]),b=fraction>0?table->peek(whole+1,registers_[op.b]):a;
                registers_[op.dst]=a+(b-a)*fraction;continue;
            }
            if(op.op==Op::tableWrite) {const auto& table=tables_[op.dst].table;if(table)table->poke(registers_[op.a],registers_[op.b],registers_[op.c]);continue;}
            const double a=registers_[op.a],b=registers_[op.b],c=registers_[op.c];
            // Keep the implemented integer domain exact; never invoke an
            // out-of-range C++ integer cast on an audio callback.
            if(op.op==Op::moveInteger && (!std::isfinite(a) || std::abs(a)>9007199254740991.)) {fault_=true;break;}
            const double result=calculate(op.op,a,b,c,rate_);
            registers_[op.dst]=result;
        }
        for(auto& delay:delays_)delay->advance();
        for(auto& s:histories_) {s.value=registers_[s.reg];if(std::fpclassify(s.value)==FP_SUBNORMAL)s.value=0;}
        for(int i=0;i<outputCount_;++i) {outputs[i]=outputs_[i]<0?0:registers_[outputs_[i]];if(!std::isfinite(outputs[i]))fault_=true;}
        if(fault_)std::fill(outputs,outputs+outputCount_,0);
        return !fault_;
    }
};
} // namespace m4l::gen
