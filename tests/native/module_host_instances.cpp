// Shared ABI/lifecycle regression, not original-device sonic conformance.
#include "../../src/m4l_builder/native/max_compat/module_host.cpp"
#include <cassert>

struct InstanceProbe { t_pxobject header; double value; int deferred; };
static t_maxclass *instanceClass;
static void *createInstance(t_symbol *, long, t_atom *) {
    auto *object = static_cast<InstanceProbe *>(object_alloc(instanceClass));
    z_dsp_setup(&object->header, 0);
    outlet_new(object, "signal");
    return object;
}
static void finishInstance(void *object) { z_dsp_free((t_pxobject *)object); }
static void performInstance(t_object *object, t_object *, double **, long, double **output,
                            long, long frames, long, void *user) {
    for (long frame = 0; frame < frames; ++frame)
        output[0][frame] += ((InstanceProbe *)object)->value * *(double *)user;
}
static double firstWeight = 1, secondWeight = 2;
static void compileInstance(t_object *object, t_object *, short *, double, long, long) {
    dsp_add64(nullptr, object, performInstance, 0, &firstWeight);
    dsp_add64(nullptr, object, performInstance, 0, &secondWeight);
}
static int deferredCalls = 0;
static void deferredInstance(void *object, t_symbol *, short, t_atom *) {
    ++((InstanceProbe *)object)->deferred; ++deferredCalls;
}

int main() {
    instanceClass = (t_maxclass *)class_new("instance-probe", (t_method)createInstance,
        (t_method)finishInstance, sizeof(InstanceProbe), nullptr, A_GIMME, 0);
    class_addmethod(instanceClass, (t_method)compileInstance, "dsp64", A_CANT, 0);
    class_register(gensym("box"), instanceClass);
    auto *a = (InstanceProbe *)host_new_instance(instanceClass);
    auto *b = (InstanceProbe *)host_new_instance(instanceClass);
    a->value = 0.25; b->value = 0.5;
    const short connections[] = {1};
    assert(host_compile_dsp64((t_object *)a, 48000, 64, connections, 1));
    auto *contextA = host_get_perform_context((t_object *)a);
    assert(host_compile_dsp64((t_object *)b, 48000, 64, connections, 1));
    auto *contextB = host_get_perform_context((t_object *)b);
    assert(contextA && contextB && contextA != contextB);
    double output[64]{}; double *channels[] = {output};
    assert(host_run_context(contextA, nullptr, 0, channels, 1, 64));
    for (double value : output) assert(value == 0.75);
    std::fill_n(output, 64, 0.0);
    assert(host_run_context(contextB, nullptr, 0, channels, 1, 64));
    for (double value : output) assert(value == 1.5);
    assert(!host_run_context(contextA, nullptr, 0, channels, 1, 65));
    assert(!host_run_context(contextA, nullptr, 1, channels, 1, 64));
    assert(host_compile_dsp64((t_object *)a, 48000, 64, connections, 1));
    assert(host_get_perform_context((t_object *)a) == contextA);
    std::fill_n(output, 64, 0.0);
    assert(host_run_context(contextA, nullptr, 0, channels, 1, 64));
    for (double value : output) assert(value == 0.75); // rebuild replaces, not appends
    defer_low(a, (t_method)deferredInstance, nullptr, 0, nullptr);
    defer_low(b, (t_method)deferredInstance, nullptr, 0, nullptr);
    defer_low(a, (t_method)deferredInstance, nullptr, 0, nullptr);
    object_free(a);
    assert(!host_get_perform_context((t_object *)a));
    host_drain_deferred();
    assert(deferredCalls == 1 && b->deferred == 1);
    std::fill_n(output, 64, 0.0);
    assert(host_run_context(contextB, nullptr, 0, channels, 1, 64));
    for (double value : output) assert(value == 1.5);
    object_free(b);
    assert(host_unsupported_calls() == 0);
    puts("Independent DSP contexts, callback order, recompile and deferred retirement: PASS");
}
