// Exact effect connection metadata and standalone package-report contracts.
#include "../../src/m4l_builder/native/max_compat/module_host.cpp"
#include <cassert>
#include <type_traits>

static_assert(std::is_same<decltype(sys_getsr()), float>::value,
              "Max MSP sys_getsr returns float, not double, including on ARM64");

struct Effect { t_pxobject header; double gain; };
static t_maxclass *effectClass;
static void *create(t_symbol *, long, t_atom *) {
    auto *x = static_cast<Effect *>(object_alloc(effectClass));
    z_dsp_setup(&x->header, 2);
    outlet_new(x, "signal");
    outlet_new(x, "signal");
    x->gain = 0.5;
    return x;
}
static void perform(t_object *object, t_object *, double **inputs, long ni,
                    double **outputs, long no, long frames, long, void *) {
    assert(ni == 2 && no == 2);
    auto *x = reinterpret_cast<Effect *>(object);
    for (long c = 0; c < no; ++c)
        for (long f = 0; f < frames; ++f) outputs[c][f] = inputs[c][f] * x->gain;
}
static void compile(t_object *x, t_object *dsp, short *connections, double, long, long) {
    assert(connections[0] == 1 && connections[1] == 0);
    assert(connections[2] == 1 && connections[3] == 1);
    dsp_add64(dsp, x, reinterpret_cast<t_perfroutine64>(perform), 0, nullptr);
}
static void fileusage(t_object *, void *collector) {
    fileusage_addpackage(collector, "ableton-dsp", nullptr);
    fileusage_addpackage(collector, "ableton-dsp", nullptr);
}
int main() {
    host_set_sr(44100);
    assert(sys_getsr() == 44100.0f);
    host_set_sr(48000);
    assert(sys_getsr() == 48000.0f);
    effectClass = static_cast<t_maxclass *>(class_new("test.effect", reinterpret_cast<t_method>(create), nullptr,
        sizeof(Effect), nullptr, A_GIMME, 0));
    class_addmethod(effectClass, reinterpret_cast<t_method>(compile), "dsp64", A_CANT, 0);
    class_addmethod(effectClass, reinterpret_cast<t_method>(fileusage), "fileusage", A_CANT, 0);
    class_addattr(effectClass, attr_offset_new("gain", gensym("float64"), 0, nullptr, nullptr, offsetof(Effect, gain)));
    class_register(gensym("box"), effectClass);
    auto *x = static_cast<t_object *>(host_new_instance(effectClass));
    assert(host_signal_inlet_count(x) == 2 && host_signal_outlet_count(x) == 2);
    assert(host_method_count(effectClass) == 2 && !strcmp(host_method_name(effectClass, 0), "dsp64"));
    assert(!strcmp(host_attr_name(effectClass, 0), "gain") && !strcmp(host_attr_type(effectClass, 0), "float64"));
    assert(!host_attr_name(effectClass, 1));
    double gain = -1;
    assert(!host_get_numeric_attr(x, "gain", &gain) && gain == 0.5);
    assert(!host_set_attr(x, "gain", 0.25));
    assert(!host_get_numeric_attr(x, "gain", &gain) && gain == 0.25);
    assert(host_get_numeric_attr(x, "missing", &gain) && gain == 0.25);
    short connections[] = {1, 0, 1, 1};
    assert(host_compile_dsp64(x, 48000, 4, connections, 4));
    double left[] = {1, 2, 3, 4}, right[] = {4, 3, 2, 1}, outL[4]{}, outR[4]{};
    double *inputs[] = {left, right}, *outputs[] = {outL, outR};
    auto *context = host_get_perform_context(x);
    assert(host_run_context(context, inputs, 2, outputs, 2, 4));
    assert(outL[0] == 0.25 && outR[0] == 1);
    auto *collector = host_fileusage_new();
    assert(host_collect_fileusage(x, collector));
    assert(host_fileusage_count(collector) == 1 && !strcmp(host_fileusage_package(collector, 0), "ableton-dsp"));
    assert(!host_fileusage_package(collector, 1));
    assert(!host_unsupported_calls());
    assert(!host_compile_dsp64(x, 48000, 4, connections, 3));
    short invalid[] = {1, 2, 1, 1};
    assert(!host_compile_dsp64(x, 48000, 4, invalid, 4));
    fileusage_addpackage(collector, "ableton-dsp", reinterpret_cast<t_atomarray *>(1));
    fileusage_addpackage(reinterpret_cast<void *>(1), "ableton-dsp", nullptr);
    assert(host_unsupported_calls() == 4);
    assert(host_get_perform_context(x) == context);
    const char *label = "Filter";
    assert(str_tr(label) == label);
    host_fileusage_free(collector);
    object_free(x);
    puts("original stock module host contracts passed");
}
