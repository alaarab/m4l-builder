#include "../../src/m4l_builder/native/max_compat/runtime.hpp"
#include <cassert>
#include <cstdlib>
#include <string>
#include <vector>
using namespace m4l::maxcompat;
// A device that pages its controls routes its mode controls through
// [pak]/[unpack]/[expr] and back into those same controls as `active 0/1`
// (Adjacent Utility). `active` greys a control out: the control never answers
// it with a value, so that cord carries nothing back and the ring is not a
// synchronous loop. A cord that does carry the control's value back into it
// still is one, and `active` into an object where it means something else -
// snapshot~ - is not covered by this exception either.
static Definition control(Symbols& sy) {
    Definition dial;dial.op=Op::dial;dial.minimum=0;dial.maximum=1;dial.presentation=true;(void)sy;
    return dial;
}
static std::vector<Definition> ring(Symbols& sy,const char* closing) {
    Definition pak;pak.op=Op::pak;pak.atoms={Atom::integral(0),Atom::integral(0)};
    Definition unpack;unpack.op=Op::unpack;unpack.atoms={Atom::integral(0),Atom::integral(0)};
    unpack.formats={Format::integer,Format::integer};
    Definition expr;expr.op=Op::expression;expr.expression="$i1 == 0";expr.arguments={1};
    Definition prep;prep.op=Op::prepend;prep.atoms={Atom::named(sy.intern(closing))};
    return {control(sy),pak,unpack,expr,prep};
}
// live.dial -> pak -> unpack -> expr -> prepend <closing> -> live.dial
static std::vector<Edge> cords() { return {{0,0,1,0},{1,0,2,0},{2,0,3,0},{3,0,4,0},{4,0,0,0}}; }
// The symbols must be the ones the definitions were interned in.
static bool rejected(Symbols& sy,std::vector<Definition> nodes,std::vector<Edge> edges) {
    try { Runtime rt(std::move(nodes),std::move(edges),48000,sy,nullptr,nullptr); }
    catch(const std::invalid_argument& e) { return std::string(e.what()).find("Feedback")!=std::string::npos; }
    return false;
}
int main(){
    {
        // `active` closing the ring: accepted, and the graph runs.
        Symbols sy;Runtime rt(ring(sy,"active"),cords(),48000,sy,nullptr,nullptr);
        assert(!rt.faulted());
        assert(rt.send(0,0,Message::integer(1)));
        assert(!rt.faulted());
    }
    {
        // `hidden` is the same kind of UI state.
        Symbols sy;Runtime rt(ring(sy,"hidden"),cords(),48000,sy,nullptr,nullptr);
        assert(!rt.faulted());
    }
    {
        // The same ring carrying the control's own value back into it is a
        // real synchronous loop and stays rejected.
        Symbols sy;
        assert(rejected(sy,ring(sy,"active"),{{0,0,1,0},{1,0,2,0},{2,0,3,0},{3,0,0,0}}));
    }
    {
        // A prepend of anything else still closes the loop: the exception is
        // the named UI attributes, not prepend.
        Symbols sy;
        assert(rejected(sy,ring(sy,"set_value"),cords()));
    }
    {
        // The destination must be a presentation control. The same `active`
        // cord into a plain object is not covered.
        Symbols sy;auto nodes=ring(sy,"active");nodes[0].presentation=false;
        assert(rejected(sy,std::move(nodes),cords()));
    }
    return 0;
}
