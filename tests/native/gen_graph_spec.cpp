#include "../../src/m4l_builder/native/max_compat/gen_graph.hpp"
#include <cassert>
#include <iostream>
#include <new>
#include <limits>
static thread_local bool callback=false;
static thread_local unsigned allocations=0;
void* operator new(std::size_t n){if(callback)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept{::operator delete(p);}
using namespace m4l::gen;
NodeDefinition node(NodeDefinition::Kind kind,int port=0,std::string code={}) {NodeDefinition n;n.kind=kind;n.port=port;n.code=std::move(code);return n;}
GraphDefinition expression(std::string code,int ins=2,int outs=2) {
    GraphDefinition d;d.nodes.push_back(node(NodeDefinition::Kind::expression,0,std::move(code)));
    for(int i=0;i<ins;++i) {d.nodes.push_back(node(NodeDefinition::Kind::input,i));d.edges.push_back({int(d.nodes.size()-1),0,0,i});}
    for(int i=0;i<outs;++i) {d.nodes.push_back(node(NodeDefinition::Kind::output,i));d.edges.push_back({0,i,int(d.nodes.size()-1),0});}
    return d;
}
void reject(const GraphDefinition& d) {bool rejected=false;try {Graph bad(d,48000);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);}
int main() {
    auto d=expression("modvalue(x){x=x*0.5;return x;}out1=modvalue(in1);out2=modvalue(in2);");
    GraphDefinition parent;auto child=node(NodeDefinition::Kind::nested);child.nested=std::make_shared<GraphDefinition>(d);
    auto constant=node(NodeDefinition::Kind::operation);constant.operation="3.";
    parent.nodes={child,constant,node(NodeDefinition::Kind::input),node(NodeDefinition::Kind::output),node(NodeDefinition::Kind::output,1)};
    parent.edges={{1,0,0,0},{2,0,0,1},{0,0,3,0},{0,1,4,0}};
    Graph graph(parent,48000);double input[64]={3},output[64]={};
    callback=true;assert(graph.process(input,output));callback=false;
    assert(allocations==0 && output[0]==1 && output[1]==1.5);

    auto parameter=expression("modvalue(x){x=x*0.5;return x;}Param p(3);History h(3);out1=modvalue(p);out2=modvalue(h);",0);
    Graph root(parameter,48000);assert(root.process(input,output) && output[0]==1.5 && output[1]==1.5);
    assert(root.set("p",3.5));assert(root.process(input,output) && output[0]==1.75);root.reset();
    child.nested=std::make_shared<GraphDefinition>(parameter);GraphDefinition nested;
    nested.nodes={child,node(NodeDefinition::Kind::output),node(NodeDefinition::Kind::output,1)};nested.edges={{0,0,1,0},{0,1,2,0}};
    Graph privateParam(nested,48000);assert(!privateParam.set("p",3.5));assert(privateParam.process(input,output) && output[0]==1 && output[1]==1.5);

    auto history=node(NodeDefinition::Kind::history);auto add=node(NodeDefinition::Kind::operation);add.operation="+";
    GraphDefinition feedback;feedback.nodes={node(NodeDefinition::Kind::input),history,add,node(NodeDefinition::Kind::output)};
    feedback.edges={{0,0,2,0},{1,0,2,1},{2,0,1,0},{2,0,3,0}};
    Graph first(feedback,48000),second(feedback,48000);input[0]=.25;
    for(int i=1;i<=1024;++i) {callback=true;assert(first.process(input,output));callback=false;assert(output[0]==i*.25);}
    assert(second.process(input,output) && output[0]==.25);first.reset();assert(first.process(input,output) && output[0]==.25);
    assert(allocations==0);

    auto multiply=node(NodeDefinition::Kind::operation);multiply.operation="*";multiply.arguments={"0.5"};
    GraphDefinition arg;arg.nodes={node(NodeDefinition::Kind::input),multiply,node(NodeDefinition::Kind::output)};arg.edges={{0,0,1,0},{1,0,2,0}};
    Graph argument(arg,48000);input[0]=.5;assert(argument.process(input,output) && output[0]==.25);
    arg.edges.push_back({0,0,1,1});reject(arg); // A constructor argument removes the right inlet.
    auto duplicate=feedback;duplicate.edges.push_back({0,0,2,0});reject(duplicate);
    auto cycle=feedback;cycle.nodes[1]=add;reject(cycle);
    auto conflict=expression("Param p(1);out1=p;",0,1);
    conflict.nodes.push_back(node(NodeDefinition::Kind::expression,0,"Param p(2);out1=p;"));reject(conflict);

    auto delay=node(NodeDefinition::Kind::operation);delay.operation="delay";delay.arguments={"8","2"};
    auto taps=node(NodeDefinition::Kind::expression,0,"out1=2;out2=2.25;");
    GraphDefinition echoes;echoes.nodes={node(NodeDefinition::Kind::input),delay,taps,node(NodeDefinition::Kind::output),node(NodeDefinition::Kind::output,1)};
    echoes.edges={{0,0,1,0},{2,0,1,1},{2,1,1,2},{1,0,3,0},{1,1,4,0}};
    Graph delayed(echoes,48000),isolated(echoes,48000);
    for(int n=0;n<64;++n) {
        input[0]=n==0?1:0;callback=true;assert(delayed.process(input,output));callback=false;
        assert(output[0]==(n==2?1:0) && output[1]==(n==2?.75:(n==3?.25:0)));
    }
    input[0]=1;assert(isolated.process(input,output) && output[0]==0 && output[1]==0);
    callback=true;delayed.reset();assert(delayed.process(input,output));callback=false;assert(output[0]==0);
    auto invalidDelay=echoes;invalidDelay.nodes[1].arguments={"8","2","@interp","cosine"};reject(invalidDelay);
    invalidDelay.nodes[1].arguments={"8","2","@feedback","2"};reject(invalidDelay);
    invalidDelay.nodes[1].arguments={"4194305"};reject(invalidDelay);
    delay.arguments={"8"};taps.code="out1=2;";
    GraphDefinition loop;loop.nodes={node(NodeDefinition::Kind::input),add,delay,taps,node(NodeDefinition::Kind::output)};
    loop.edges={{0,0,1,0},{2,0,1,1},{1,0,2,0},{3,0,2,1},{1,0,4,0}};
    Graph delayFeedback(loop,48000);input[0]=.25;
    for(int n=0;n<128;++n) {callback=true;assert(delayFeedback.process(input,output));callback=false;assert(output[0]==(n/2+1)*.25);}
    loop.nodes[2].arguments={"8","@feedback","0"};reject(loop);
    input[0]=std::numeric_limits<double>::infinity();assert(!delayed.process(input,output) && output[0]==0);
    assert(allocations==0);

    // Nested programs share one sample-work budget; a tree cannot multiply it.
    auto work=expression("x=0;for(i=0;i<3500;i+=1){x+=in1;}out1=x;",1,1);
    Graph one(work,48000);input[0]=.001;assert(one.process(input,output));
    GraphDefinition expensive;auto a=node(NodeDefinition::Kind::nested);a.nested=std::make_shared<GraphDefinition>(work);
    expensive.nodes={node(NodeDefinition::Kind::input),a,a,a,node(NodeDefinition::Kind::output)};
    expensive.edges={{0,0,1,0},{1,0,2,0},{2,0,3,0},{3,0,4,0}};
    Graph bounded(expensive,48000);callback=true;assert(!bounded.process(input,output));callback=false;
    assert(output[0]==0 && allocations==0);
    {   // A codebox that reads no inN still has one inlet: a cord from [in 1]
        // into it is accepted and ignored (Gravity's parameter codebox).
        GraphDefinition g;g.nodes.push_back(node(NodeDefinition::Kind::expression,0,"Param k(2); out1=k*3;"));
        g.nodes.push_back(node(NodeDefinition::Kind::input,0));g.edges.push_back({1,0,0,0});
        g.nodes.push_back(node(NodeDefinition::Kind::output,0));g.edges.push_back({0,0,2,0});
        Graph ok(g,48000);double in=5,out=0;
        assert(ok.process(&in,&out));assert(out==6);
        GraphDefinition second=g;second.edges.push_back({1,0,0,1});reject(second); // a second inlet does not exist
    }
    std::cout<<"PASS: inferred constants across nested graphs, scoped parameters, independent history/reset, constructor arity, rejected cycles/aliases, aggregate work budget, zero callback allocations.\n";
}
