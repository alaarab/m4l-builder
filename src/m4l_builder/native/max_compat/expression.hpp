#pragma once
// Prepared numeric Max expr evaluation. Original expressions stay data; no
// device-specific programs, audio-thread parsing, allocation or script engine.
#include "message.hpp"
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <string_view>

namespace m4l::maxcompat {
class Expression {
    enum class Op { literal,input,negate,logicalNot,add,subtract,multiply,divide,modulo,
        less,lessEqual,greater,greaterEqual,equal,notEqual,logicalAnd,logicalOr,
        integer,floating,absolute,minimum,maximum,round,floor,ceil,sqrt,exp,log,log10,pow };
    struct Instruction {Op op;Atom value{};int input=0;};
    std::vector<Instruction> code_;
    std::array<Atom,512> stack_{};
    std::array<Atom,9> inputs_{};
    std::array<int,9> types_{};
    int inlets_=1;
    uint64_t arithmeticWarnings_=0;
    std::string source_;
    size_t at_=0;
    void space(){while(at_<source_.size() && std::isspace(static_cast<unsigned char>(source_[at_])))++at_;}
    bool take(std::string_view token){space();if(source_.compare(at_,token.size(),token)!=0)return false;at_+=token.size();return true;}
    [[noreturn]] void reject() const {throw std::invalid_argument("Unsupported or malformed numeric expr near character "+std::to_string(at_));}
    void emit(Op op,Atom a={},int input=0){if(code_.size()>=512)reject();code_.push_back({op,a,input});}
    void primary(int depth){
        if(depth>64)reject();space();if(at_==source_.size())reject();
        if(take("+")){primary(depth+1);return;}
        if(take("-")){primary(depth+1);emit(Op::negate);return;}
        if(take("!")){primary(depth+1);emit(Op::logicalNot);return;}
        if(take("(")){expression(1,depth+1);if(!take(")"))reject();return;}
        if(take("$")){
            if(at_+1>=source_.size() || (source_[at_]!='i' && source_[at_]!='f'))reject();
            const int type=source_[at_++]=='i'?1:2;const char digit=source_[at_++];
            if(digit<'1' || digit>'9')reject();const int index=digit-'1';
            if(types_[index] && types_[index]!=type)reject();types_[index]=type;
            inputs_[index]=type==1?Atom::integral(0):Atom::real(0);inlets_=std::max(inlets_,index+1);emit(Op::input,{},index);return;
        }
        if(std::isdigit(static_cast<unsigned char>(source_[at_])) || source_[at_]=='.'){
            const size_t start=at_;char* end=nullptr;const double value=std::strtod(source_.c_str()+at_,&end);
            at_=size_t(end-source_.c_str());if(at_==start || !std::isfinite(value))reject();
            const auto token=source_.substr(start,at_-start);
            if(token.find_first_of(".eE")!=std::string::npos)emit(Op::literal,Atom::real(value));
            else {size_t used=0;try{const auto integer=std::stoll(token,&used);if(used!=token.size())reject();emit(Op::literal,Atom::integral(integer));}catch(const std::exception&){reject();}}
            return;
        }
        const size_t start=at_;while(at_<source_.size() && (std::isalnum(static_cast<unsigned char>(source_[at_])) || source_[at_]=='_'))++at_;
        if(at_==start)reject();const auto name=source_.substr(start,at_-start);
        Op op;int count=1;
        if(name=="int")op=Op::integer;else if(name=="float")op=Op::floating;
        else if(name=="abs")op=Op::absolute;else if(name=="round")op=Op::round;else if(name=="floor")op=Op::floor;
        else if(name=="ceil")op=Op::ceil;else if(name=="sqrt")op=Op::sqrt;else if(name=="exp")op=Op::exp;
        else if(name=="log")op=Op::log;else if(name=="log10")op=Op::log10;
        else if(name=="min"){op=Op::minimum;count=2;}else if(name=="max"){op=Op::maximum;count=2;}
        else if(name=="pow"){op=Op::pow;count=2;}else reject();
        if(!take("("))reject();expression(1,depth+1);
        if(count==2){if(!take(","))reject();expression(1,depth+1);}
        if(!take(")"))reject();emit(op);
    }
    void expression(int minimum,int depth){
        if(depth>64)reject();primary(depth+1);
        struct Binary {std::string_view token;Op op;int precedence;};
        static constexpr Binary operators[]={{"||",Op::logicalOr,1},{"&&",Op::logicalAnd,2},
            {"==",Op::equal,3},{"!=",Op::notEqual,3},{"<=",Op::lessEqual,4},{">=",Op::greaterEqual,4},
            {"<",Op::less,4},{">",Op::greater,4},{"+",Op::add,5},{"-",Op::subtract,5},
            {"*",Op::multiply,6},{"/",Op::divide,6},{"%",Op::modulo,6}};
        while(true){space();const Binary* next=nullptr;
            for(const auto& candidate:operators)if(source_.compare(at_,candidate.token.size(),candidate.token)==0){next=&candidate;break;}
            if(!next || next->precedence<minimum)return;
            at_+=next->token.size();expression(next->precedence+1,depth+1);emit(next->op);
        }
    }
    static int64_t bits(uint64_t value) noexcept {int64_t result;std::memcpy(&result,&value,sizeof(result));return result;}
    Atom binary(Op op,Atom a,Atom b,bool& valid) noexcept {
        const bool integers=a.type==Atom::Type::integer && b.type==Atom::Type::integer;
        const int64_t i=integers?a.value.integer:0,j=integers?b.value.integer:0;const double x=a.number(),y=b.number();
        const bool less=integers?i<j:x<y, greater=integers?i>j:x>y;
        switch(op){
            case Op::minimum:return less?a:b;case Op::maximum:return greater?a:b;
            case Op::less:return Atom::integral(less);case Op::greater:return Atom::integral(greater);
            case Op::lessEqual:return Atom::integral(integers?i<=j:x<=y);case Op::greaterEqual:return Atom::integral(integers?i>=j:x>=y);
            case Op::equal:return Atom::integral(integers?i==j:x==y);case Op::notEqual:return Atom::integral(integers?i!=j:x!=y);
            case Op::logicalAnd:return Atom::integral(x!=0 && y!=0);case Op::logicalOr:return Atom::integral(x!=0 || y!=0);
            case Op::add:return integers?Atom::integral(bits(uint64_t(i)+uint64_t(j))):Atom::real(x+y);
            case Op::subtract:return integers?Atom::integral(bits(uint64_t(i)-uint64_t(j))):Atom::real(x-y);
            case Op::multiply:return integers?Atom::integral(bits(uint64_t(i)*uint64_t(j))):Atom::real(x*y);
            case Op::divide:
                // Max substitutes one for a zero denominator. Integer math
                // also reports an error; it still produces the numerator.
                if(y==0 && integers)++arithmeticWarnings_;
                if(integers){const int64_t denominator=j?j:1;return Atom::integral(i==INT64_MIN && denominator==-1?INT64_MIN:i/denominator);}
                return Atom::real(x/(y==0?1:y));
            case Op::modulo:
                if(!integers){valid=false;return {};}
                if(j==0){++arithmeticWarnings_;return Atom::integral(0);}
                return Atom::integral(i==INT64_MIN && j==-1?0:i%j);
            case Op::pow:return Atom::real(std::pow(x,y));
            default:valid=false;return {};
        }
    }
    Atom evaluate(bool& valid) noexcept {
        size_t size=0;
        for(const auto& instruction:code_){const auto op=instruction.op;
            if(op==Op::literal){stack_[size++]=instruction.value;continue;}
            if(op==Op::input){stack_[size++]=inputs_[instruction.input];continue;}
            const bool two=(op>=Op::add && op<=Op::logicalOr) || op==Op::minimum || op==Op::maximum || op==Op::pow;
            if(size<(two?2u:1u)){valid=false;return {};}
            if(two){const Atom b=stack_[--size];stack_[size-1]=binary(op,stack_[size-1],b,valid);continue;}
            Atom& a=stack_[size-1];const double x=a.number();
            switch(op){
                case Op::negate:a=a.type==Atom::Type::integer?Atom::integral(bits(0-uint64_t(a.value.integer))):Atom::real(-x);break;
                case Op::logicalNot:a=Atom::integral(x==0);break;
                case Op::integer:a=a.converted(Atom::Type::integer,valid);break;
                case Op::floating:a=Atom::real(x);break;
                case Op::absolute:a=a.type==Atom::Type::integer?Atom::integral(a.value.integer<0?bits(0-uint64_t(a.value.integer)):a.value.integer):Atom::real(std::abs(x));break;
                case Op::round:a=Atom::real(std::round(x));break;case Op::floor:a=Atom::real(std::floor(x));break;
                case Op::ceil:a=Atom::real(std::ceil(x));break;case Op::sqrt:a=Atom::real(std::sqrt(x));break;
                case Op::exp:a=Atom::real(std::exp(x));break;case Op::log:a=Atom::real(std::log(x));break;case Op::log10:a=Atom::real(std::log10(x));break;
                default:valid=false;return {};
            }
        }
        if(size!=1)valid=false;return stack_[0];
    }
public:
    explicit Expression(std::string source):source_(std::move(source)) {
        if(source_.empty() || source_.size()>4096)reject();expression(1,0);space();if(at_!=source_.size())reject();
    }
    int inlets() const noexcept {return inlets_;}
    uint64_t arithmeticWarnings() const noexcept {return arithmeticWarnings_;}
    bool receive(int inlet,const Message& message,Atom& result,bool& produced) noexcept {
        produced=false;if(inlet<0 || inlet>=inlets_)return false;
        bool valid=true;
        if(message.kind==Message::Kind::bang){if(inlet!=0)return false;}
        else {
            if(!message.numeric() || (!message.isNumber() && message.kind!=Message::Kind::list) || (inlet!=0 && message.count!=1))return false;
            for(int i=0;i<std::min(message.count,inlets_-inlet);++i){
                const int slot=inlet+i;
                inputs_[slot]=message.atoms[i].converted(types_[slot]==2?Atom::Type::floating:Atom::Type::integer,valid);
            }
        }
        if(!valid)return false;
        if(inlet==0){result=evaluate(valid);produced=valid;}
        return valid;
    }
};
}
