// Public ABI/callback regression, NOT an original-device fidelity test.
#include "../../src/m4l_builder/native/max_compat/module_host.cpp"
#include <cassert>

struct Probe { t_pxobject header; double storage; long integer; long count; double values[2]; int setterCalls; };
static t_maxclass *probeClass;
static bool destroyed = false;
static void *createProbe(t_symbol *s, long, t_atom *) {
    assert(s == gensym("shared-host-probe"));
    return object_alloc(probeClass);
}
static void destroyProbe(void *) { destroyed = true; }
static t_max_err setGain(Probe *p, void *, long count, t_atom *values) {
    if (count != 1) return -1;
    p->storage = 2 * atom_getfloat(values); ++p->setterCalls; return 0;
}
static t_max_err getGain(Probe *p, void *, long *count, t_atom **values) {
    if (!*values) *values = (t_atom *)calloc(1, sizeof(t_atom));
    *count = 1; (*values)[0].a_type = A_FLOAT; (*values)[0].a_w.w_float = p->storage / 2; return 0;
}
static void *eight(void *, void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h) {
    return (void *)((uintptr_t)a+(uintptr_t)b+(uintptr_t)c+(uintptr_t)d+(uintptr_t)e+(uintptr_t)f+(uintptr_t)g+(uintptr_t)h);
}
static void later(Probe *p, t_symbol *, short count, t_atom *values) {
    assert(count == 1); p->integer += atom_getlong(values);
}
int main() {
    static_assert(offsetof(Probe, storage) == 64, "Device payload follows real MSP header");
    t_atom poisoned; memset(&poisoned, 0xa5, sizeof(poisoned));
    poisoned.a_type = A_FLOAT; poisoned.a_w.w_float = 7.75;
    assert(atom_getfloat(&poisoned) == 7.75 && atom_getlong(&poisoned) == 7);
    probeClass = (t_maxclass *)class_new("shared-host-probe", (t_method)createProbe, (t_method)destroyProbe, sizeof(Probe), nullptr, A_GIMME, 0);
    class_addmethod(probeClass, (t_method)eight, "eight", A_CANT, 0);
    void *gain = attr_offset_new("gain", gensym("float64"), 0, nullptr, nullptr, offsetof(Probe, storage));
    assert(attr_addfilter_clip(gain, 0, 1, 1, 1) == 0);
    class_addattr(probeClass, gain);
    void *registeredGain = class_attr_get(probeClass, gensym("gain"));
    object_method_imp(registeredGain, gensym("setmethod"), gensym("get"), (void *)getGain, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr);
    object_method_imp(registeredGain, gensym("setmethod"), gensym("set"), (void *)setGain, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr);
    class_addattr(probeClass, attr_offset_new("integer", gensym("long"), 0, nullptr, nullptr, offsetof(Probe, integer)));
    class_addattr(probeClass, attr_offset_array_new("array", gensym("float64"), 2, 0, nullptr, nullptr, offsetof(Probe, count), offsetof(Probe, values)));
    class_addattr(probeClass, attr_offset_new("invalid", gensym("long"), 0, nullptr, nullptr, sizeof(Probe) + 8));
    class_register(gensym("box"), probeClass);
    auto *p = (Probe *)host_new_instance(probeClass);
    assert(p && p->header.z_ob.o_magic == 1758379419L);
    assert((void *)p->header.z_ob.o_messlist[-1].m_sym == probeClass);
    p->storage = 99; z_dsp_setup(&p->header, 1);
    assert(p->storage == 99 && p->header.z_count == 1 && p->header.z_in == 0);
    assert(host_set_attr((t_object *)p, "gain", 0.25) == 0);
    assert(p->storage == 0.5 && p->setterCalls == 1);
    assert(object_attr_getfloat(p, gensym("gain")) == 0.25);
    assert(host_set_attr((t_object *)p, "gain", 10) == 0 && p->storage == 2);
    assert(object_attr_setlong(p, gensym("integer"), (t_atom_long)1 << 40) == 0 && p->integer == ((long)1 << 40));
    assert(object_attr_setlong(p, gensym("invalid"), 3) != 0);
    assert(object_attr_setlong(p, gensym("missing"), 3) != 0);
    double array[] = {0.125, 0.875};
    assert(object_attr_setdouble_array(p, gensym("array"), 2, array) == 0);
    long count = 0; t_atom *values = nullptr;
    assert(object_attr_getvalueof(p, gensym("array"), &count, &values) == 0);
    assert(count == 2 && atom_getfloat(values) == 0.125 && atom_getfloat(values+1) == 0.875); free(values);
    t_atom args[3]{};
    args[0].a_type = A_SYM; args[0].a_w.w_sym = gensym("positional");
    args[1].a_type = A_SYM; args[1].a_w.w_sym = gensym("@gain");
    args[2].a_type = A_FLOAT; args[2].a_w.w_float = 0.75;
    assert(attr_args_offset(3, args) == 1); attr_args_process(p, 3, args);
    assert(p->storage == 1.5);
    assert((uintptr_t)object_method_imp(p, gensym("eight"), (void *)1, (void *)2, (void *)3, (void *)4, (void *)5, (void *)6, (void *)7, (void *)8) == 36);
    t_atom amount{}; amount.a_type = A_LONG; amount.a_w.w_long = 2; p->integer = 0;
    defer(p, (t_method)later, nullptr, 1, &amount); assert(p->integer == 2);
    defer_low(p, (t_method)later, nullptr, 1, &amount);
    amount.a_w.w_long = 99; assert(p->integer == 2);
    host_drain_deferred(); assert(p->integer == 4);
    host_set_audio_offset(17.25); double offset = -1;
    assert(scheduler_getaudiooffset(scheduler_fromobject((t_object *)p), &offset) == 1 && offset == 17.25);
    assert(scheduler_getaudiooffset(nullptr, &offset) == 0);
    common_symbols_init(); assert(g_common->entries[666] == gensym("int"));
    object_free(p); assert(destroyed && host_unsupported_calls() == 0);
    puts("Max module host ABI, callbacks, arrays, constructor args, defer, timestamp and lifecycle: PASS");
}
