#pragma once
#include "genexpr.hpp"
#include "gen_delay.hpp"
#include <memory>
#include <sstream>
#include <iomanip>

namespace m4l::gen {
struct GraphDefinition;
struct NodeDefinition {
    enum class Kind { input, output, expression, operation, history, nested };
    Kind kind=Kind::expression;
    int port=0;
    std::string code,operation,name;
    std::vector<std::string> arguments;
    double initial=0;
    std::shared_ptr<const GraphDefinition> nested;
};
struct Edge {int source,outlet,destination,inlet;};
struct GraphDefinition {
    std::vector<NodeDefinition> nodes;
    std::vector<Edge> edges;
    std::vector<std::pair<std::string,double>> overrides;
};
class Graph {
    struct PreparationBudget {size_t nodes=0,sourceBytes=0,registers=0,instructions=0,delaySamples=0,tableSamples=0;std::shared_ptr<Noise> noise=std::make_shared<Noise>();};
    struct Node {
        NodeDefinition definition;
        std::unique_ptr<Expression> expression;
        std::unique_ptr<Graph> nested;
        std::unique_ptr<Delay> delay;
        Interpolation interpolation=Interpolation::linear;
        bool feedback=true;
        std::vector<std::vector<Edge>> sources;
        std::vector<double> defaults,outputs;
        std::vector<ValueInfo> outputInfo;
        std::string source;
        double history=0;
    };
    std::vector<Node> nodes_;
    std::vector<int> schedule_;
    std::array<double,64> inputs_{};
    int inputCount_=0,outputCount_=0;
    std::vector<ValueInfo> outputInfo_;
    std::map<std::string,double> parameterDefaults_;
    bool fault_=false;
    const BufferRegistry* buffers_=nullptr;
    static double number(const std::string& value) {
        char* end=nullptr;const double result=std::strtod(value.c_str(),&end);
        if(end==value.c_str() || *end || !std::isfinite(result))throw std::invalid_argument("Gen operator requires a finite numeric argument");
        return result;
    }
    static std::string operation(const NodeDefinition& definition,std::vector<double>& defaults) {
        const auto& name=definition.operation;const auto& args=definition.arguments;
        if(name=="noise") {
            if(!args.empty())throw std::invalid_argument("Gen noise requires no arguments");
            defaults={};return "out1=noise();";
        }
        if(name=="change") {
            if(!args.empty())throw std::invalid_argument("Gen change initialization attributes need support");
            defaults={0};return "out1=change(in1);";
        }
        if(name=="phasor") {
            if(args.size()>1)throw std::invalid_argument("Gen phasor phase attributes need support");
            if(args.empty()){defaults={0,0};return "out1=phasor(in1,in2);";}
            number(args[0]);defaults={0};return "out1=phasor(("+args[0]+"),in1);";
        }
        const std::map<std::string,std::string> binary={{"+","in1+in2"},{"-","in1-in2"},{"*","in1*in2"},{"/","in1/in2"},
            {"!-","in2-in1"},{"!/","in2/in1"},{"%","in1%in2"},{"<","in1<in2"},{"<=","in1<=in2"},
            {">","in1>in2"},{">=","in1>=in2"},{"==","in1==in2"},{"!=","in1!=in2"},
            {"min","min(in1,in2)"},{"minimum","min(in1,in2)"},{"max","max(in1,in2)"},{"maximum","max(in1,in2)"},{"pow","pow(in1,in2)"}};
        if(auto found=binary.find(name);found!=binary.end()) {
            if(args.size()>1)throw std::invalid_argument("Unsupported Gen binary operator arguments");
            std::string code=found->second;
            if(args.empty())defaults={0,0};
            else {number(args[0]);defaults={0};size_t at=0;while((at=code.find("in2",at))!=std::string::npos) {code.replace(at,3,"("+args[0]+")");at+=args[0].size()+2;}}
            return "out1="+code+";";
        }
        const std::vector<std::string> unary={"abs","sqrt","exp","log","sin","cos","tan","tanh","floor","ceil","round","trunc","dbtoa","atodb","mstosamps","sampstoms"};
        if(std::find(unary.begin(),unary.end(),name)!=unary.end()) {
            if(!args.empty())throw std::invalid_argument("Unsupported Gen unary operator arguments");
            defaults={0};return "out1="+name+"(in1);";
        }
        if(name=="clip" || name=="clamp" || name=="mix") {
            if(args.size()>3)throw std::invalid_argument("Unsupported Gen ternary operator arguments");
            for(const auto& arg:args)number(arg);
            std::string a="in1",b="in2",c="in3";
            if(args.empty())defaults=name=="mix"?std::vector<double>{0,1,.5}:std::vector<double>{0,0,1};
            else if(args.size()==1) {c="("+args[0]+")";defaults={0,name=="mix"?1.:0.};}
            else if(args.size()==2) {
                if(name=="mix") {a="("+args[0]+")";b="("+args[1]+")";c="in1";defaults={.5};}
                else {b="("+args[0]+")";c="("+args[1]+")";defaults={0};}
            } else {a="("+args[0]+")";b="("+args[1]+")";c="("+args[2]+")";}
            return "out1="+name+"("+a+","+b+","+c+");";
        }
        if(name=="slide") {
            if(!args.empty() && args.size()!=2)throw std::invalid_argument("Gen slide requires zero or two arguments");
            std::string up="in2",down="in3";defaults={0,1,1};
            if(args.size()==2) {number(args[0]);number(args[1]);up="("+args[0]+")";down="("+args[1]+")";defaults={0};}
            return "out1=slide(in1,"+up+","+down+");";
        }
        if(name=="dcblock") {
            if(!args.empty())throw std::invalid_argument("Unsupported dcblock arguments");
            defaults={0};return "History x(0),y(0); v=in1-x+y*0.9997; x=in1; y=v; out1=v;";
        }
        if(name=="param" || name=="Param") {
            if(args.empty())throw std::invalid_argument("Unnamed Gen parameter");
            std::string code="Param "+args[0]+"(";size_t i=1;
            if(i<args.size() && args[i][0]!='@') {number(args[i]);code+=args[i++];}else code+="0";
            while(i<args.size()) {
                const auto key=args[i++];if(i>=args.size() || (key!="@min" && key!="@max"))throw std::invalid_argument("Unsupported Gen parameter attribute");
                number(args[i]);code+=","+key.substr(1)+"="+args[i++];
            }
            return code+"); out1="+args[0]+";";
        }
        if(!args.empty())throw std::invalid_argument("Gen operator not implemented: "+name);
        number(name);return "out1="+name+";";
    }
    double input(const Node& n,size_t inlet) const noexcept {
        const auto& edges=n.sources[inlet];if(edges.empty())return n.defaults[inlet];
        return nodes_[edges[0].source].outputs[edges[0].outlet];
    }
    void specialize(const std::vector<ValueInfo>& inputInfo,double rate,bool root,PreparationBudget& budget) {
        for(int index:schedule_) {
            auto& n=nodes_[index];
            if(n.definition.kind==NodeDefinition::Kind::input)n.outputInfo[0]=size_t(n.definition.port)<inputInfo.size()?inputInfo[n.definition.port]:ValueInfo{};
            else if(n.definition.kind==NodeDefinition::Kind::history || n.delay)std::fill(n.outputInfo.begin(),n.outputInfo.end(),ValueInfo{});
            else {
                std::vector<ValueInfo> values;
                for(size_t i=0;i<n.sources.size();++i) {
                    const auto& edges=n.sources[i];values.push_back(edges.empty()?ValueInfo::literal(n.defaults[i]):nodes_[edges[0].source].outputInfo[edges[0].outlet]);
                }
                if(n.expression) {
                    n.expression=std::make_unique<Expression>(n.source,rate,values,!root,parameterDefaults_,n.expression->delaySamples(),true,buffers_,n.expression->tableSamples(),budget.noise);
                    budget.registers+=n.expression->registerCount();budget.instructions+=n.expression->instructionCount();
                    if(budget.registers>262144 || budget.instructions>262144)throw std::invalid_argument("Gen aggregate instruction/register budget exceeded");
                    for(size_t i=0;i<n.outputs.size();++i)n.outputInfo[i]=n.expression->outputInfo(int(i));
                } else if(n.nested) {
                    n.nested->specialize(values,rate,false,budget);n.outputInfo=n.nested->outputInfo_;
                } else if(n.definition.kind==NodeDefinition::Kind::output)outputInfo_[n.definition.port]=values[0];
            }
        }
        // Codebox Params alias a graph-local name. Conflicting declarations
        // require Max's precedence rules before this runtime can accept them.
        std::map<std::string,Expression::Parameter> parameters;
        for(const auto& n:nodes_)if(n.expression)for(const auto& p:n.expression->parameters()) {
            auto old=parameters.find(p.name);
            if(old!=parameters.end() && (old->second.initial!=p.initial || old->second.minimum!=p.minimum || old->second.maximum!=p.maximum))
                throw std::invalid_argument("Conflicting Gen parameter declarations need verified precedence: "+p.name);
            parameters.emplace(p.name,p);
        }
        for(const auto& p:parameterDefaults_)if(!parameters.count(p.first))throw std::invalid_argument("Unresolved local Gen parameter override: "+p.first);
    }
public:
    Graph(const GraphDefinition& definition,double rate,unsigned depth=0,std::shared_ptr<PreparationBudget> budget={},const BufferRegistry* buffers=nullptr):buffers_(buffers) {
        if(!std::isfinite(rate) || rate<8000 || rate>384000)throw std::invalid_argument("Invalid Gen sample rate");
        if(!budget)budget=std::make_shared<PreparationBudget>();
        if(depth>16 || definition.nodes.empty() || definition.nodes.size()>4096 || definition.edges.size()>16384)
            throw std::invalid_argument("Gen graph exceeds preparation budget");
        for(const auto& d:definition.nodes) {
            if(++budget->nodes>8192)throw std::invalid_argument("Gen aggregate node budget exceeded");
            Node n;n.definition=d;
            size_t inlets=0,outlets=1;
            if(d.kind==NodeDefinition::Kind::input || d.kind==NodeDefinition::Kind::output) {
                if(d.port<0 || d.port>=64)throw std::invalid_argument("Invalid Gen graph port");
                if(d.kind==NodeDefinition::Kind::input)inputCount_=std::max(inputCount_,d.port+1);
                else {outputCount_=std::max(outputCount_,d.port+1);inlets=1;outlets=0;}
            } else if(d.kind==NodeDefinition::Kind::history) {
                if(!std::isfinite(d.initial))throw std::invalid_argument("Invalid Gen history value");
                n.history=d.initial;inlets=1;
            } else if(d.kind==NodeDefinition::Kind::nested) {
                if(!d.nested)throw std::invalid_argument("Missing Gen subpatch");
                n.nested=std::make_unique<Graph>(*d.nested,rate,depth+1,budget,buffers_);inlets=n.nested->inputs();outlets=n.nested->outputs();
            } else if(d.kind==NodeDefinition::Kind::operation && d.operation=="delay") {
                const auto& args=d.arguments;size_t at=0;double size=rate,taps=1;
                if(at<args.size() && args[at][0]!='@') {size=args[at]=="samplerate"?rate:number(args[at]);++at;}
                if(at<args.size() && args[at][0]!='@')taps=number(args[at++]);
                if(size<1 || size>4194304 || std::trunc(size)!=size || taps<1 || taps>63 || std::trunc(taps)!=taps)throw std::invalid_argument("Invalid Gen delay size/taps");
                while(at<args.size()) {
                    const auto key=args[at++];if(at==args.size())throw std::invalid_argument("Missing Gen delay attribute value");
                    const auto value=args[at++];
                    if(key=="@interp")n.interpolation=delayInterpolation(value);
                    else if(key=="@feedback") {if(value!="0" && value!="1")throw std::invalid_argument("Invalid Gen delay feedback");n.feedback=value=="1";}
                    else if(key!="@name")throw std::invalid_argument("Unsupported Gen delay attribute: "+key);
                }
                budget->delaySamples+=Delay::storageFor(size_t(size));
                if(budget->delaySamples>8388608)throw std::invalid_argument("Gen aggregate delay memory budget exceeded");
                n.delay=std::make_unique<Delay>(size_t(size));
                inlets=size_t(taps)+1;outlets=size_t(taps);
            } else if(d.kind==NodeDefinition::Kind::expression || d.kind==NodeDefinition::Kind::operation) {
                n.source=d.kind==NodeDefinition::Kind::expression?d.code:operation(d,n.defaults);
                budget->sourceBytes+=n.source.size();if(budget->sourceBytes>8*1024*1024)throw std::invalid_argument("Gen aggregate source budget exceeded");
                n.expression=std::make_unique<Expression>(n.source,rate,std::vector<ValueInfo>{},false,std::map<std::string,double>{},8388608-budget->delaySamples,false,buffers_,8388608-budget->tableSamples,budget->noise);
                budget->delaySamples+=n.expression->delaySamples();budget->tableSamples+=n.expression->tableSamples();inlets=n.expression->inputs();outlets=n.expression->outputs();
                // A codebox always shows at least one inlet (Gravity's parameter
                // codebox reads no inN yet is patched from [in 1]); the unused
                // cord is accepted and its value ignored.
                if(d.kind==NodeDefinition::Kind::expression)inlets=std::max<size_t>(inlets,1);
            } else throw std::invalid_argument("Invalid Gen node kind");
            if(inlets>64 || outlets>64)throw std::invalid_argument("Gen node port budget exceeded");
            n.sources.resize(inlets);n.defaults.resize(inlets,0);n.outputs.resize(outlets,0);n.outputInfo.resize(outlets);nodes_.push_back(std::move(n));
        }
        if(!outputCount_)throw std::invalid_argument("No Gen graph output");
        std::vector<bool> outputPorts(outputCount_);
        for(const auto& n:nodes_)if(n.definition.kind==NodeDefinition::Kind::output) {
            if(outputPorts[n.definition.port])throw std::invalid_argument("Duplicate Gen output ports need verified merge semantics");
            outputPorts[n.definition.port]=true;
        }
        std::vector<int> degrees(nodes_.size());std::vector<std::vector<int>> downstream(nodes_.size());
        for(const auto& e:definition.edges) {
            if(e.source<0 || e.destination<0 || size_t(e.source)>=nodes_.size() || size_t(e.destination)>=nodes_.size() || e.outlet<0 || e.inlet<0 ||
               size_t(e.outlet)>=nodes_[e.source].outputs.size() || size_t(e.inlet)>=nodes_[e.destination].sources.size())throw std::invalid_argument("Invalid Gen graph cord");
            auto& sources=nodes_[e.destination].sources[e.inlet];
            if(!sources.empty())throw std::invalid_argument("Multiple Gen cords into one inlet need verified routing semantics");
            sources.push_back(e);
            const auto& dst=nodes_[e.destination];
            if(dst.definition.kind!=NodeDefinition::Kind::history && !(dst.delay && dst.feedback && e.inlet==0)) {++degrees[e.destination];downstream[e.source].push_back(e.destination);}
        }
        for(size_t i=0;i<degrees.size();++i)if(!degrees[i])schedule_.push_back(int(i));
        for(size_t i=0;i<schedule_.size();++i)for(int dst:downstream[schedule_[i]])if(--degrees[dst]==0)schedule_.push_back(dst);
        if(schedule_.size()!=nodes_.size())throw std::invalid_argument("Gen feedback requires a History or supported delay");
        outputInfo_.resize(outputCount_,ValueInfo::literal(0));
        for(const auto& p:definition.overrides) {
            if(!std::isfinite(p.second) || !parameterDefaults_.emplace(p).second)throw std::invalid_argument("Invalid or duplicate Gen parameter override");
        }
        if(!depth)specialize(std::vector<ValueInfo>(inputCount_),rate,true,*budget);
    }
    void prepareBuffers() {
        for(auto& node:nodes_) {if(node.expression)node.expression->prepareBuffers();if(node.nested)node.nested->prepareBuffers();}
    }
    bool bindBuffer(const std::string& name,const std::string& target) noexcept {
        std::shared_ptr<Table> table;
        if(buffers_) {auto found=buffers_->find(target);if(found!=buffers_->end())table=found->second;}
        bool found=false;for(auto& node:nodes_)if(node.expression)found=node.expression->bindBuffer(name,table) || found;
        return found;
    }
    int inputs() const noexcept {return inputCount_;}
    int outputs() const noexcept {return outputCount_;}
    bool set(const std::string& name,double value) noexcept {
        if(!std::isfinite(value))return false;
        bool found=false;
        for(auto& n:nodes_) {
            if(n.expression)found=n.expression->set(name,value)||found;
            if(n.definition.kind==NodeDefinition::Kind::history && n.definition.name==name) {n.history=value;found=true;}
        }
        return found;
    }
    void reset() noexcept {
        for(auto& n:nodes_) {if(n.expression)n.expression->reset();if(n.nested)n.nested->reset();if(n.delay)n.delay->reset();n.history=n.definition.initial;}
        fault_=false;
    }
    bool process(const double* values,double* result,unsigned* sharedBudget=nullptr,unsigned* sharedBulkBudget=nullptr) noexcept {
        unsigned localBudget=65536;unsigned& budget=sharedBudget?*sharedBudget:localBudget;
        unsigned localBulkBudget=1048576;unsigned& bulkBudget=sharedBulkBudget?*sharedBulkBudget:localBulkBudget;
        std::fill(result,result+outputCount_,0);if(fault_)return false;
        for(auto& n:nodes_)if(n.definition.kind==NodeDefinition::Kind::history)n.outputs[0]=n.history;
        for(int index:schedule_) {
            if(!budget) {fault_=true;break;}--budget;
            auto& n=nodes_[index];
            if(n.definition.kind==NodeDefinition::Kind::input)n.outputs[0]=values[n.definition.port];
            else if(n.definition.kind==NodeDefinition::Kind::output)result[n.definition.port]+=input(n,0);
            else if(n.delay) {
                if(!n.feedback) {
                    const auto value=input(n,0);if(!std::isfinite(value)) {fault_=true;break;}n.delay->write(value);
                }
                for(size_t tap=0;tap<n.outputs.size();++tap) {
                    const auto time=input(n,tap+1);if(!std::isfinite(time)) {fault_=true;break;}
                    n.outputs[tap]=n.delay->read(time,n.interpolation);
                }
                if(fault_)break;
            }
            else if(n.expression || n.nested) {
                for(size_t i=0;i<n.sources.size();++i)inputs_[i]=input(n,i);
                if(!(n.expression?n.expression->process(inputs_.data(),n.outputs.data(),&budget,&bulkBudget):n.nested->process(inputs_.data(),n.outputs.data(),&budget,&bulkBudget))) {fault_=true;break;}
            }
        }
        for(auto& n:nodes_)if(n.definition.kind==NodeDefinition::Kind::history) {
            n.history=input(n,0);if(std::fpclassify(n.history)==FP_SUBNORMAL)n.history=0;
        }
        for(auto& n:nodes_)if(n.delay) {
            if(n.feedback) {const auto value=input(n,0);if(!std::isfinite(value))fault_=true;else n.delay->write(value);}
            n.delay->advance();
        }
        for(int i=0;i<outputCount_;++i)if(!std::isfinite(result[i]))fault_=true;
        if(fault_)std::fill(result,result+outputCount_,0);return !fault_;
    }
};
} // namespace m4l::gen
