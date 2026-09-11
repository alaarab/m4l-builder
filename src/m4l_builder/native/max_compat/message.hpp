#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <initializer_list>
#include <stdexcept>
#include <string>
#include <vector>

namespace m4l::maxcompat {
using Symbol = uint32_t;
// IDs are stable across prepared graphs. Additional symbols are interned before
// rendering; no string lookup or interning is performed by the audio callback.
namespace sym {
constexpr Symbol empty=0, bang=1, integer=2, floating=3, list=4, symbol=5,
    set=6, stop=7, clear=8, nth=9, send=10, assign=11, init=12, outputvalue=13, rawfloat=14,
    append=15,prepend=16,setargs=17,comma=18,semicolon=19;
}
class Symbols {
    std::vector<std::string> names_{"", "bang", "int", "float", "list", "symbol", "set", "stop", "clear", "nth", "send", "assign", "init", "outputvalue", "rawfloat", "append", "prepend", "setargs", ",", ";"};
    std::vector<int> substitutions_=std::vector<int>(20,-1);
public:
    Symbol intern(const std::string& name) {
        if(name.size()>4096) throw std::invalid_argument("Symbol exceeds preparation budget");
        for(size_t i=0;i<names_.size();++i) if(names_[i]==name) return Symbol(i);
        if(names_.size()>=65536) throw std::invalid_argument("Symbol table exceeds preparation budget");
        int slot=-1;
        if(name.size()>=2 && name.size()<=3 && name[0]=='$') {
            int value=0;bool digits=true;
            for(size_t i=1;i<name.size();++i){digits=digits && name[i]>='0' && name[i]<='9';value=value*10+(name[i]-'0');}
            if(digits && value>=1 && value<=64)slot=value-1;
        }
        names_.push_back(name);substitutions_.push_back(slot);return Symbol(names_.size()-1);
    }
    size_t size() const noexcept { return names_.size(); }
    const std::string& name(Symbol id) const { return names_.at(id); }
    int substitution(Symbol id) const noexcept {return id<substitutions_.size()?substitutions_[id]:-1;}
};
struct Atom {
    enum class Type : uint8_t { integer, floating, symbol };
    Type type=Type::integer;
    union { int64_t integer; double floating; Symbol symbol; } value{0};
    static Atom integral(int64_t v) noexcept { Atom a; a.value.integer=v; return a; }
    static Atom real(double v) noexcept { Atom a; a.type=Type::floating; a.value.floating=v; return a; }
    static Atom named(Symbol v) noexcept { Atom a; a.type=Type::symbol; a.value.symbol=v; return a; }
    bool numeric() const noexcept { return type!=Type::symbol; }
    double number() const noexcept { return type==Type::integer ? double(value.integer) : type==Type::floating ? value.floating : 0.; }
    bool valid(size_t symbols) const noexcept {
        return type==Type::integer || (type==Type::floating && std::isfinite(value.floating)) || (type==Type::symbol && value.symbol<symbols);
    }
    Atom converted(Type target, bool& valid) const noexcept {
        if(target==type) return *this;
        if(target==Type::symbol) return named(sym::empty);
        if(target==Type::floating) return real(number());
        const double n=number();
        if(!std::isfinite(n) || n < -9223372036854775808. || n >= 9223372036854775808.) { valid=false; return integral(0); }
        return integral(int64_t(n));
    }
    bool equals(const Atom& b) const noexcept {
        if(type==Type::symbol || b.type==Type::symbol) return type==b.type && value.symbol==b.value.symbol;
        if(type==Type::integer && b.type==Type::integer) return value.integer==b.value.integer;
        // Do not round a 64-bit integer to double before comparing mixed types.
        if(type!=b.type) {
            const Atom& f=type==Type::floating ? *this:b;
            const Atom& i=type==Type::integer ? *this:b;
            return f.value.floating>=-9223372036854775808. && f.value.floating<9223372036854775808.
                && std::trunc(f.value.floating)==f.value.floating && int64_t(f.value.floating)==i.value.integer;
        }
        return value.floating==b.value.floating;
    }
};
struct Message {
    // 128: an m4l.modal~ 'model' message carries 6 + 24 modes * 5 = 126 atoms.
    static constexpr int capacity=128;
    enum class Kind : uint8_t { bang, integer, floating, list, symbol, anything };
    Kind kind=Kind::bang;
    Symbol selector=sym::bang;
    int count=0;
    std::array<Atom,capacity> atoms{};
    static Message single(Atom a) noexcept {
        Message m; m.count=1; m.atoms[0]=a;
        m.kind=a.type==Atom::Type::integer ? Kind::integer : a.type==Atom::Type::floating ? Kind::floating : Kind::symbol;
        m.selector=a.type==Atom::Type::integer ? sym::integer : a.type==Atom::Type::floating ? sym::floating : sym::symbol;
        return m;
    }
    static Message number(double n) noexcept { return single(Atom::real(n)); }
    static Message integer(int64_t n) noexcept { return single(Atom::integral(n)); }
    static Message symbol(Symbol s) noexcept { return single(Atom::named(s)); }
    static Message list(std::initializer_list<Atom> values) {
        if(values.size()>capacity) throw std::invalid_argument("Message exceeds capacity");
        Message m; m.kind=Kind::list; m.selector=sym::list; m.count=int(values.size());
        std::copy(values.begin(),values.end(),m.atoms.begin());return m;
    }
    static Message anything(Symbol s) noexcept { Message m; m.kind=Kind::anything; m.selector=s; return m; }
    bool isNumber() const noexcept { return kind==Kind::integer || kind==Kind::floating; }
    bool numeric() const noexcept {
        if(kind==Kind::symbol || kind==Kind::anything) return false;
        for(int i=0;i<count;++i) if(!atoms[i].numeric()) return false;
        return true;
    }
    bool valid(size_t symbols) const noexcept {
        if(int(kind)>int(Kind::anything) || count<0 || count>capacity || selector>=symbols) return false;
        for(int i=0;i<count;++i) if(!atoms[i].valid(symbols)) return false;
        switch(kind) {
            case Kind::bang: return count==0 && selector==sym::bang;
            case Kind::integer: return count==1 && selector==sym::integer && atoms[0].type==Atom::Type::integer;
            case Kind::floating: return count==1 && selector==sym::floating && atoms[0].type==Atom::Type::floating;
            case Kind::symbol: return count==1 && selector==sym::symbol && atoms[0].type==Atom::Type::symbol;
            case Kind::list: return selector==sym::list;
            case Kind::anything: return true;
        }
        return false;
    }
    // Normalize an atom sequence at an object outlet. A leading symbol becomes
    // its selector; explicit 'list' preserves a single-element list's type.
    static Message sequence(const Atom* values,int n) noexcept {
        Message m;
        if(n<=0) return m;
        if(n>capacity) { m.count=capacity+1; return m; }
        if(values[0].type==Atom::Type::symbol) {
            const Symbol s=values[0].value.symbol;
            if(s==sym::bang && n==1) return m;
            if(s==sym::list) { m.kind=Kind::list; m.selector=sym::list; }
            else if(s==sym::symbol && n==2 && values[1].type==Atom::Type::symbol) return symbol(values[1].value.symbol);
            else { m.kind=Kind::anything; m.selector=s; }
            m.count=n-1; std::copy(values+1,values+n,m.atoms.begin());
        } else if(n==1) return single(values[0]);
        else { m.kind=Kind::list; m.selector=sym::list; m.count=n;std::copy(values,values+n,m.atoms.begin()); }
        return m;
    }
    // Include an anything selector when an object treats the whole message as
    // list data (pack/prepend/etc.). Bang has no data atoms.
    int dataAtoms(Atom* destination,int room=capacity) const noexcept {
        const int prefix=kind==Kind::anything ? 1:0;
        if(count+prefix>room) return -1;
        if(prefix) destination[0]=Atom::named(selector);
        std::copy(atoms.begin(),atoms.begin()+count,destination+prefix);return count+prefix;
    }
};
} // namespace m4l::maxcompat
