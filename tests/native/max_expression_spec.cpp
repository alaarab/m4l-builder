#include "../../src/m4l_builder/native/max_compat/expression.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <new>
static thread_local bool callback=false;
static thread_local size_t allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::maxcompat;
int main(int argc,char** argv){
    assert(argc==2);std::ifstream input(argv[1]);int cases;input>>cases;assert(cases>0 && cases<1000);int reports=0,rejected=0,expectedReports=0,expectedRejected=0;
    for(int c=0;c<cases;++c){
        std::string source;int supported,steps;input>>std::quoted(source)>>supported>>steps;assert(input);
        if(!supported)++expectedRejected;
        std::unique_ptr<Expression> subject;
        try{subject=std::make_unique<Expression>(source);}catch(const std::invalid_argument&){assert(!supported);++rejected;}
        assert(bool(subject)==bool(supported));
        for(int step=0;step<steps;++step){
            int inlet,count,type;std::string selector,value;input>>inlet>>selector>>count;
            Message message;message.count=count;
            message.kind=selector=="bang"?Message::Kind::bang:selector=="list"?Message::Kind::list:selector=="int"?Message::Kind::integer:Message::Kind::floating;
            for(int i=0;i<count;++i){double a;input>>a;message.atoms[i]=selector=="int"?Atom::integral(int64_t(a)):Atom::real(a);}
            input>>type>>value;assert(input);if(type!=-1)++expectedReports;if(!subject)continue;
            Atom result;bool produced=false;
            callback=true;const bool valid=subject->receive(inlet,message,result,produced);callback=false;
            assert(valid && produced==(type!=-1));if(!produced)continue;++reports;
            const double expected=std::stod(value),actual=result.number();
            const bool numericMatch=std::isnan(expected)?std::isnan(actual):std::isinf(expected)?actual==expected:std::abs(actual-expected)<=1e-13*std::max(1.,std::abs(expected));
            if(result.type!=(type==0?Atom::Type::integer:Atom::Type::floating) || !numericMatch){
                std::cerr<<"Case "<<c<<" step "<<step<<" "<<source<<" expected type="<<type<<" value="<<value<<" got type="<<int(result.type)<<" value="<<std::setprecision(17)<<actual<<"\n";return 1;
            }
        }
    }
    assert(reports==expectedReports && rejected==expectedRejected && allocations==0);
    // Preparation limits and unsupported syntax cannot slip into callbacks.
    for(const char* source:{"$f10","$s1","$f1 ? 1 : 0","sin($f1)","min(1)","1;2","$i1 + $f1"}){
        bool failed=false;try{Expression invalid(source);}catch(const std::invalid_argument&){failed=true;}assert(failed);
    }
    Expression wrapping("$i1+1");Atom result;bool emitted;
    callback=true;assert(wrapping.receive(0,Message::integer(INT64_MAX),result,emitted));callback=false;
    assert(emitted && result.type==Atom::Type::integer && result.value.integer==INT64_MIN);
    std::cout<<"PASS: "<<reports<<" original Max typed expr reports across "<<cases<<" cases, "<<rejected<<" original syntax rejections, hot/cold/list state, integer division, chosen-operand min/max types, math domain results, preparation bounds and zero callback allocations. Large integer reference values passed through Max JS double capture.\n";
}
