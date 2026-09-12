// Reject malformed render buffers before dispatching an original module.
#include "../../src/m4l_builder/native/max_compat/module_host.cpp"
#include <cassert>

struct PortProbe {
    t_pxobject header;
    long inputs, outputs;
    int calls;
};
static void performPorts(t_object *object, t_object *, double **inputs, long ni,
                         double **outputs, long no, long frames, long, void *) {
    auto *probe = reinterpret_cast<PortProbe *>(object);
    ++probe->calls;
    assert(ni == probe->inputs && no == probe->outputs);
    for (long channel = 0; channel < no; ++channel)
        for (long frame = 0; frame < frames; ++frame)
            outputs[channel][frame] = ni ? inputs[channel % ni][frame] : 0.25;
}
static void compilePorts(t_object *object, t_object *, short *, double, long, long) {
    dsp_add64(nullptr, object, performPorts, 0, nullptr);
}
static PortProbe *createPorts(void *klass, long inputs, long outputs) {
    auto *probe = static_cast<PortProbe *>(object_alloc(klass));
    probe->inputs = inputs;
    probe->outputs = outputs;
    z_dsp_setup(&probe->header, inputs);
    for (long channel = 0; channel < outputs; ++channel) outlet_new(probe, "signal");
    return probe;
}

int main() {
    auto *klass = class_new("port-probe", nullptr, nullptr, sizeof(PortProbe), nullptr, 0);
    class_addmethod(klass, reinterpret_cast<t_method>(compilePorts), "dsp64", A_CANT, 0);
    class_register(gensym("box"), klass);
    auto *effect = createPorts(klass, 2, 2);
    // An unconnected inlet still has a signal buffer in Max's perform ABI.
    const short connections[] = {1, 0, 1, 1};
    assert(host_compile_dsp64(reinterpret_cast<t_object *>(effect), 48000, 4, connections, 4));
    auto *context = host_get_perform_context(reinterpret_cast<t_object *>(effect));
    double left[] = {1, 2, 3, 4}, right[] = {0, 0, 0, 0};
    double outL[4]{}, outR[4]{};
    double *inputs[] = {left, right, left}, *outputs[] = {outL, outR, outL};
    auto reject = [&](double **ins, long ni, double **outs, long no) {
        const int before = effect->calls;
        std::fill_n(outL, 4, -7.0);
        std::fill_n(outR, 4, -9.0);
        assert(!host_run_context(context, ins, ni, outs, no, 4));
        assert(effect->calls == before);
        for (double value : outL) assert(value == -7.0);
        for (double value : outR) assert(value == -9.0);
    };
    reject(nullptr, 0, outputs, 2);
    reject(inputs, 1, outputs, 2);
    reject(inputs, 3, outputs, 2);
    reject(inputs, 2, nullptr, 0);
    reject(inputs, 2, outputs, 1);
    reject(inputs, 2, outputs, 3);
    reject(nullptr, 2, outputs, 2);
    reject(inputs, 2, nullptr, 2);
    double *missingChannel[] = {left, nullptr};
    reject(missingChannel, 2, outputs, 2);
    reject(inputs, 2, missingChannel, 2);
    assert(host_run_context(context, inputs, 2, outputs, 2, 4));
    assert(effect->calls == 1);
    for (int frame = 0; frame < 4; ++frame) {
        assert(outL[frame] == left[frame]);
        assert(outR[frame] == right[frame]);
    }
    // Recompilation updates the channel contract without moving the context.
    effect->inputs = 1;
    z_dsp_setup(&effect->header, 1);
    const short reconnected[] = {1, 1, 1};
    assert(host_compile_dsp64(reinterpret_cast<t_object *>(effect), 44100, 4, reconnected, 3));
    assert(context == host_get_perform_context(reinterpret_cast<t_object *>(effect)));
    reject(inputs, 2, outputs, 2);
    assert(host_run_context(context, inputs, 1, outputs, 2, 4));
    assert(effect->calls == 2);
    for (int frame = 0; frame < 4; ++frame) assert(outR[frame] == left[frame]);

    // Genuine zero-input generators and zero-output sinks remain valid.
    auto *generator = createPorts(klass, 0, 2);
    const short stereo[] = {1, 1};
    assert(host_compile_dsp64(reinterpret_cast<t_object *>(generator), 48000, 4, stereo, 2));
    auto *generatorContext = host_get_perform_context(reinterpret_cast<t_object *>(generator));
    assert(host_run_context(generatorContext, nullptr, 0, outputs, 2, 4));
    for (double value : outL) assert(value == 0.25);
    for (double value : outR) assert(value == 0.25);
    auto *sink = createPorts(klass, 1, 0);
    const short mono[] = {1};
    assert(host_compile_dsp64(reinterpret_cast<t_object *>(sink), 48000, 4, mono, 1));
    assert(host_run_context(host_get_perform_context(reinterpret_cast<t_object *>(sink)),
                            inputs, 1, nullptr, 0, 4));
    assert(generator->calls == 1 && sink->calls == 1);
    object_free(effect);
    object_free(generator);
    object_free(sink);
    assert(host_unsupported_calls() == 0);
    puts("Compiled render port contracts: PASS");
}
