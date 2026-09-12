// Isolated original-Max-module probe host. Shared by Object Studio's macOS and
// Simulator probes; NOT the app's complete Max runtime or a full stock device.
// Uses public SDK layouts and callbacks, never private device-state offsets.
#include "module_abi.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <map>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cstdarg>
#include <string>
#include <unordered_map>
#include <vector>

extern "C" {
static const char *g_phase = "init";
static bool g_rendering = false;
static unsigned long g_unsupported = 0;
unsigned long host_unsupported_calls(void) { return g_unsupported; }
void host_phase(const char *p){ g_phase = p; fprintf(stderr,"=== phase: %s ===\n", p); }

// ---- symbols -------------------------------------------------------------
using SymbolMap = std::map<std::string, t_symbol *, std::less<>>;
static SymbolMap *g_syms;
t_symbol *gensym(const char *s) {
    if (!g_syms) { if (g_rendering) { ++g_unsupported; return nullptr; } g_syms = new SymbolMap(); }
    const char *name = s ? s : "";
    auto found = g_syms->find(name);
    if (found != g_syms->end()) return found->second;
    if (g_rendering) { ++g_unsupported; return nullptr; }
    auto *slot = (t_symbol *)calloc(1, sizeof(t_symbol));
    if (!slot) return nullptr;
    slot->s_name = strdup(name);
    (*g_syms)[name] = slot;
    return slot;
}
t_symbol *gensym_tr(const char *s) { return gensym(s); }          // translation: identity here
// Matches the SDK's NO_TRANSLATION_SUPPORT behavior, not a localization engine.
char *str_tr(const char *s) { return const_cast<char *>(s); }

// SDK table indices, not a guessed prefix. Only explicitly supported selectors
// are populated; other fields remain null. This is NOT full commonsyms support.
struct t_common_symbols_table { long version; t_symbol *entries[1454]; };
static t_common_symbols_table *g_common;
void common_symbols_init(void) {
    if (g_common || g_rendering) return;
    g_common = (t_common_symbols_table *)calloc(1, sizeof(t_common_symbols_table));
    if (!g_common) return;
    g_common->version = 500;
#define HOST_COMMON(index, name) g_common->entries[index] = gensym(name);
#include "module_common_symbols.inc"
#undef HOST_COMMON
}
t_common_symbols_table *common_symbols_gettable(void) { common_symbols_init(); return g_common; }

// ---- class / method / attr ----------------------------------------------
struct Method { t_symbol *name; t_method fn; long *argtypes; };
struct Attr {
    t_symbol *name; std::string type; size_t offset;
    t_method get = nullptr, set = nullptr;
    bool array = false, usemin = false, usemax = false;
    long capacity = 1, offsetcount = -1;
    double minimum = 0, maximum = 0;
};
static std::unordered_map<void *, Attr *> g_attributes;
typedef struct _maxclass {
    std::string name;
    t_method newmethod, freemethod;
    size_t size;
    std::vector<Method> methods;
    std::vector<Attr *> attrs;
    std::vector<t_messlist> messages;
} t_maxclass;

static std::unordered_map<std::string, t_maxclass *> *g_classes;
static std::unordered_map<void *, t_maxclass *> g_instances;
struct HostSignalPorts { long inputs = 0, outputs = 0; };
static std::unordered_map<void *, HostSignalPorts> g_signal_ports;

void *class_new(const char *name, t_method mnew, t_method mfree, long size, t_method /*menu*/, ...) {
    auto *c = new t_maxclass();
    c->name = name; c->newmethod = mnew; c->freemethod = mfree; c->size = (size_t)size;
    if (!g_classes) g_classes = new std::unordered_map<std::string, t_maxclass *>();
    (*g_classes)[name] = c;
    return c;
}
t_max_err class_register(t_symbol *, void *cptr) {
    auto *c = (t_maxclass *)cptr;
    c->messages.resize(c->methods.size() + 2);
    c->messages[0].m_sym = reinterpret_cast<t_symbol *>(c);
    for (size_t i = 0; i < c->methods.size(); ++i) {
        c->messages[i + 1].m_sym = c->methods[i].name;
        c->messages[i + 1].m_fun = c->methods[i].fn;
    }
    return 0;
}
t_max_err class_dspinit(void * /*c*/) { return 0; }

t_max_err class_addmethod(void *cptr, t_method m, const char *name, ...) {
    auto *c = (t_maxclass *)cptr;
    c->methods.push_back({ gensym(name), m, nullptr });
    return 0;
}

// attr_offset_new(name, type, flags, get, set, offset)
void *attr_offset_new(const char *name, const t_symbol *type, long /*flags*/,
                      t_method get, t_method set, long offset) {
    auto *a = new Attr();
    a->name = gensym(name);
    a->type = type ? ((t_symbol *)type)->s_name : "float64";
    a->offset = (size_t)offset;
    a->get = get; a->set = set;
    g_attributes[a] = a;
    return a;
}
void *attr_offset_array_new(const char *name, const t_symbol *type, long size, long flags,
                            t_method get, t_method set, long offsetcount, long offset) {
    auto *a = (Attr *)attr_offset_new(name, type, flags, get, set, offset);
    a->array = true; a->capacity = size; a->offsetcount = offsetcount;
    return a;
}
t_max_err class_addattr(void *cptr, void *attr) {
    auto *c = (t_maxclass *)cptr; auto *a = (Attr *)attr;
    c->attrs.push_back(a);
    return 0;
}
t_max_err class_attr_addattr_parse(void * /*c*/, const char * /*attrname*/, const char * /*attrname2*/,
                                   const t_symbol * /*type*/, long /*flags*/, const char * /*parsestr*/) { return 0; }
t_max_err class_attr_addattr_format(void * /*c*/, const char * /*a*/, const char * /*a2*/,
                                    const t_symbol * /*t*/, long /*f*/, const char * /*fmt*/, ...) { return 0; }
void *class_attr_get(void *cptr, t_symbol *name) {
    if (!cptr) return nullptr;
    for (auto *a : ((t_maxclass *)cptr)->attrs) if (a->name == name) return a;
    return nullptr;
}
t_max_err attr_addfilter_clip(void *attr, double min, double max, long usemin, long usemax) {
    if (!attr) return -2;
    auto *a = (Attr *)attr;
    a->minimum = min; a->maximum = max; a->usemin = usemin; a->usemax = usemax;
    return 0;
}
t_max_err object_attr_setvalueof(void *, t_symbol *, long, t_atom *);
long attr_args_offset(short argc, t_atom *argv) {
    if (argc <= 0 || !argv) return 0;
    for (short i = 0; i < argc; ++i)
        if (argv[i].a_type == A_SYM && argv[i].a_w.w_sym && argv[i].a_w.w_sym->s_name[0] == '@') return i;
    return argc;
}
void attr_args_process(void *x, short argc, t_atom *argv) {
    for (long i = attr_args_offset(argc, argv); i < argc;) {
        long end = i + 1;
        while (end < argc && !(argv[end].a_type == A_SYM && argv[end].a_w.w_sym && argv[end].a_w.w_sym->s_name[0] == '@')) ++end;
        if (object_attr_setvalueof(x, gensym(argv[i].a_w.w_sym->s_name + 1), end - i - 1, argv + i + 1)) ++g_unsupported;
        i = end;
    }
}

// ---- objects -------------------------------------------------------------
void host_forget_perform(void *object);
void host_cancel_deferred(void *object);
void *object_alloc(void *cptr) {
    auto *c = (t_maxclass *)cptr;
    if (g_rendering || !c || c->size < sizeof(t_object) || c->messages.empty()) { ++g_unsupported; return nullptr; }
    auto *o = (t_object *)calloc(1, c->size);
    if (!o) return nullptr;
    o->o_messlist = c->messages.data() + 1;
    o->o_magic = 1758379419L;
    g_instances[o] = c;
    return o;
}
void object_free(void *o) {
    if (!o) return;
    if (g_rendering) { ++g_unsupported; return; }
    auto it = g_instances.find(o);
    if (it != g_instances.end()) {
        auto freeMethod = it->second->freemethod;
        if (freeMethod) ((void (*)(void *))freeMethod)(o);
        g_instances.erase(o);
        g_signal_ports.erase(o);
    }
    host_forget_perform(o);
    host_cancel_deferred(o);
    free(o);
}
void *object_class(void *o) {
    auto it = g_instances.find(o);
    return it == g_instances.end() ? nullptr : it->second;
}
void object_error(t_object * /*x*/, const char *fmt, ...) {
    if (g_rendering) { ++g_unsupported; return; }
    va_list ap; va_start(ap, fmt); fprintf(stderr, "[original module object_error] "); vfprintf(stderr, fmt, ap); fprintf(stderr, "\n"); va_end(ap);
}
void *object_method_imp(void *x, void *sym, void *p1, void *p2, void *p3, void *p4, void *p5, void *p6, void *p7, void *p8) {
    auto attribute = g_attributes.find(x);
    if (attribute != g_attributes.end() && sym == gensym("setmethod")) {
        // CLASS_ATTR_ACCESSORS installs original callbacks after creation.
        if (p1 == gensym("get")) { attribute->second->get = (t_method)p2; return nullptr; }
        if (p1 == gensym("set")) { attribute->second->set = (t_method)p2; return nullptr; }
    }
    auto *c = (t_maxclass *)object_class(x);
    if (c) for (auto &m : c->methods) if (m.name == sym)
        return ((void *(*)(void *, void *, void *, void *, void *, void *, void *, void *, void *))m.fn)(x,p1,p2,p3,p4,p5,p6,p7,p8);
    ++g_unsupported;
    if (!g_rendering) fprintf(stderr, "unsupported object_method: %s\n", sym ? ((t_symbol *)sym)->s_name : "<null>");
    return nullptr;
}
long proxy_getinlet(t_object *) { return 0; }

static Attr *find_attr(t_object *x, t_symbol *s) {
    return (Attr *)class_attr_get(object_class(x), s);
}
double atom_getfloat(const t_atom *);
t_atom_long atom_getlong(const t_atom *);
static size_t attr_width(const Attr &a) {
    if (a.type == "float32" || a.type == "int") return 4;
    if (a.type == "float64" || a.type == "double" || a.type == "long" || a.type == "int64") return 8;
    if (a.type == "char") return 1;
    if (a.type == "symbol" || a.type == "sym" || a.type == "object" || a.type == "pointer") return sizeof(void *);
    if (a.type == "atom") return sizeof(t_atom);
    return 0;
}
static bool attr_range(void *x, Attr &a, long count) {
    auto *c = (t_maxclass *)object_class(x);
    size_t width = attr_width(a);
    return c && width && count >= 0 && count <= 64 && count <= a.capacity &&
        a.offset <= c->size && size_t(count) <= (c->size - a.offset) / width;
}
t_max_err object_attr_setvalueof(void *x, t_symbol *s, long argc, t_atom *argv) {
    auto *a = find_attr((t_object *)x, s);
    if (g_rendering || !a || !argv || argc <= 0 || argc > 64) return -1;
    std::array<t_atom, 64> values{};
    std::copy_n(argv, argc, values.data());
    for (long i = 0; i < argc; ++i) if (values[i].a_type == A_FLOAT || values[i].a_type == A_LONG) {
        double v = atom_getfloat(&values[i]);
        if (!std::isfinite(v)) return -1;
        double clipped = a->usemin ? std::max(v, a->minimum) : v;
        if (a->usemax) clipped = std::min(clipped, a->maximum);
        if (clipped != v) { values[i].a_type = A_FLOAT; values[i].a_w.w_float = clipped; }
    }
    if (a->set) return ((t_max_err (*)(void *, void *, long, t_atom *))a->set)(x, a, argc, values.data());
    if (!attr_range(x, *a, argc) || (!a->array && argc != 1)) return -1;
    auto *c = (t_maxclass *)object_class(x);
    if (a->array && (a->offsetcount < 0 || size_t(a->offsetcount) > c->size - sizeof(long))) return -1;
    // Validate every element before any raw storage is changed.
    for (long i = 0; i < argc; ++i) {
        const auto &v = values[i];
        if (a->type == "atom") continue;
        if (a->type == "symbol" || a->type == "sym") { if (v.a_type != A_SYM) return -1; continue; }
        if (a->type == "object" || a->type == "pointer") { if (v.a_type != A_OBJ) return -1; continue; }
        if (v.a_type != A_LONG && v.a_type != A_FLOAT) return -1;
        long double n = v.a_type == A_LONG ? (long double)v.a_w.w_long : (long double)v.a_w.w_float;
        if ((a->type == "long" || a->type == "int64") && v.a_type == A_FLOAT && (n < -0x1p63L || n >= 0x1p63L)) return -1;
        if (a->type == "int" && (n < INT32_MIN || n > INT32_MAX)) return -1;
        if (a->type == "char" && (n < -128 || n > 127)) return -1;
        if (a->type == "float32" && std::fabs(n) > std::numeric_limits<float>::max()) return -1;
    }
    for (long i = 0; i < argc; ++i) {
        char *p = (char *)x + a->offset + size_t(i) * attr_width(*a);
        const auto &v = values[i];
        if (a->type == "float32") *(float *)p = (float)atom_getfloat(&v);
        else if (a->type == "float64" || a->type == "double") *(double *)p = atom_getfloat(&v);
        else if (a->type == "long" || a->type == "int64") *(int64_t *)p = atom_getlong(&v);
        else if (a->type == "int") *(int32_t *)p = (int32_t)atom_getlong(&v);
        else if (a->type == "char") *(int8_t *)p = (int8_t)atom_getlong(&v);
        else if (a->type == "symbol" || a->type == "sym") *(t_symbol **)p = v.a_w.w_sym;
        else if (a->type == "atom") *(t_atom *)p = v;
        else *(void **)p = v.a_w.w_obj;
    }
    if (a->array) *(long *)((char *)x + a->offsetcount) = argc;
    return 0;
}
t_max_err object_attr_setfloat(void *x, t_symbol *s, double v) {
    t_atom a{}; a.a_type = A_FLOAT; a.a_w.w_float = v;
    return object_attr_setvalueof(x, s, 1, &a);
}
t_max_err object_attr_setlong(void *x, t_symbol *s, t_atom_long v) {
    t_atom a{}; a.a_type = A_LONG; a.a_w.w_long = v;
    return object_attr_setvalueof(x, s, 1, &a);
}
t_max_err object_attr_setdouble_array(void *x, t_symbol *s, long argc, double *values) {
    if (!values || argc <= 0 || argc > 64) return -1;
    std::array<t_atom, 64> atoms{};
    for (long i = 0; i < argc; ++i) { atoms[i].a_type = A_FLOAT; atoms[i].a_w.w_float = values[i]; }
    return object_attr_setvalueof(x, s, argc, atoms.data());
}
t_max_err object_attr_getvalueof(void *x, t_symbol *s, long *argc, t_atom **argv) {
    auto *a = find_attr((t_object *)x, s);
    if (g_rendering || !a || !argc || !argv) return -1;
    if (a->get) return ((t_max_err (*)(void *, void *, long *, t_atom **))a->get)(x, a, argc, argv);
    long count = 1;
    if (a->array) {
        auto *c = (t_maxclass *)object_class(x);
        if (a->offsetcount < 0 || size_t(a->offsetcount) > c->size - sizeof(long)) return -1;
        count = *(long *)((char *)x + a->offsetcount);
    }
    if (!attr_range(x, *a, count)) return -1;
    if (!*argv || *argc < count) {
        auto *allocated = (t_atom *)realloc(*argv, sizeof(t_atom) * size_t(std::max(1L, count)));
        if (!allocated) return -4;
        *argv = allocated;
    }
    *argc = count;
    for (long i = 0; i < count; ++i) {
        auto &v = (*argv)[i]; v = {};
        char *p = (char *)x + a->offset + size_t(i) * attr_width(*a);
        if (a->type == "float32" || a->type == "float64" || a->type == "double") {
            v.a_type = A_FLOAT; v.a_w.w_float = a->type == "float32" ? *(float *)p : *(double *)p;
        } else if (a->type == "symbol" || a->type == "sym") { v.a_type = A_SYM; v.a_w.w_sym = *(t_symbol **)p; }
        else if (a->type == "atom") v = *(t_atom *)p;
        else if (a->type == "object" || a->type == "pointer") { v.a_type = A_OBJ; v.a_w.w_obj = *(t_object **)p; }
        else { v.a_type = A_LONG; v.a_w.w_long = a->type == "char" ? *(int8_t *)p : a->type == "int" ? *(int32_t *)p : *(int64_t *)p; }
    }
    return 0;
}
double object_attr_getfloat(void *x, t_symbol *s) {
    long count = 0; t_atom *values = nullptr;
    t_max_err error = object_attr_getvalueof(x, s, &count, &values);
    double result = !error && count > 0 ? atom_getfloat(values) : 0;
    free(values);
    return result;
}
t_max_err object_attr_setdisabled(void *, t_symbol *, long) { return 0; }

// ---- atoms ---------------------------------------------------------------
double atom_getfloat(const t_atom *a) { return !a ? 0 : a->a_type == A_FLOAT ? a->a_w.w_float : a->a_type == A_LONG ? (double)a->a_w.w_long : 0; }
t_atom_long atom_getlong(const t_atom *a) { return !a ? 0 : a->a_type == A_LONG ? a->a_w.w_long : a->a_type == A_FLOAT ? (t_atom_long)a->a_w.w_float : 0; }
t_symbol *atom_getsym(const t_atom *a) { return (a && a->a_type == A_SYM) ? a->a_w.w_sym : gensym(""); }

// ---- misc host ------------------------------------------------------------
long maxversion(void) { return 0x0900; }   // Max 9
void maxlogger_log(void * /*x*/, int /*level*/, const char * /*domain*/, const char * /*fmt*/, ...) {}
// A bounded queue avoids heap activity if an original perform defers work.
// Normal control-thread defer() is immediate, as specified by the SDK.
struct Deferred { void *x; t_method fn; t_symbol *s; short argc; std::array<t_atom, 32> argv; };
static std::array<Deferred, 64> g_deferred{};
static size_t g_deferred_head = 0, g_deferred_size = 0;
void host_cancel_deferred(void *object) {
    size_t retained = 0;
    for (size_t index = 0; index < g_deferred_size; ++index) {
        const auto entry = g_deferred[(g_deferred_head + index) % g_deferred.size()];
        if (entry.x != object) {
            g_deferred[(g_deferred_head + retained++) % g_deferred.size()] = entry;
        }
    }
    g_deferred_size = retained;
}
void *defer_low(void *x, t_method fn, t_symbol *s, short argc, t_atom *argv) {
    if (!fn || argc < 0 || argc > 32 || (argc && !argv) || g_deferred_size == g_deferred.size()) { ++g_unsupported; return nullptr; }
    auto &d = g_deferred[(g_deferred_head + g_deferred_size++) % g_deferred.size()];
    d.x = x; d.fn = fn; d.s = s; d.argc = argc;
    if (argc) std::copy_n(argv, argc, d.argv.data());
    return nullptr;
}
void *defer(void *x, t_method fn, t_symbol *s, short argc, t_atom *argv) {
    if (g_rendering) return defer_low(x, fn, s, argc, argv);
    if (!fn || argc < 0 || (argc && !argv)) { ++g_unsupported; return nullptr; }
    ((void (*)(void *, t_symbol *, short, t_atom *))fn)(x, s, argc, argv);
    return nullptr;
}
void host_drain_deferred(void) {
    size_t budget = 4096;
    while (g_deferred_size && budget--) {
        auto d = g_deferred[g_deferred_head];
        g_deferred_head = (g_deferred_head + 1) % g_deferred.size(); --g_deferred_size;
        ((void (*)(void *, t_symbol *, short, t_atom *))d.fn)(d.x, d.s, d.argc, d.argv.data());
    }
    if (g_deferred_size) ++g_unsupported;
}

// ---- MSP dsp -------------------------------------------------------------
static double g_sr = 44100.0;
// The public MSP ABI returns float even on LP64/ARM64. Returning double puts
// different bits in s0, corrupting original constructors before their dsp64.
float sys_getsr(void) { return static_cast<float>(g_sr); }
void z_dsp_setup(t_pxobject *x, long nsignals) {
    if (g_rendering || !x || nsignals < 0 || nsignals > 64) { ++g_unsupported; return; }
    x->z_in = 0; x->z_proxy = nullptr; x->z_disabled = 0;
    x->z_count = (short)nsignals; x->z_misc = 0;
    g_signal_ports[x].inputs = nsignals;
}
void z_dsp_free(t_pxobject *x) { host_forget_perform(x); }
static double g_audio_offset = 0;
void *scheduler_fromobject(t_object *) { return &g_audio_offset; }
// Private API signature established by the original module's callsite.
// Validity is returned in the integer register; the offset is an out parameter.
long scheduler_getaudiooffset(void *scheduler, double *offset) {
    if (scheduler != &g_audio_offset || !offset) return 0;
    *offset = g_audio_offset; return 1;
}
void host_set_audio_offset(double offset) { g_audio_offset = offset; }

// Preserve each compiled instance's ordered callbacks. Registration allocates
// only during compilation; dispatch does not search a map or allocate storage.
struct HostPerformCall { t_object *object; t_perfroutine64 function; void *user; };
struct host_perform_context {
    std::vector<HostPerformCall> calls;
    long maximumFrames = 0, inputs = 0, outputs = 0;
};
static std::unordered_map<void *, host_perform_context> g_perform_contexts;
static host_perform_context *g_compiling_context = nullptr, *g_last_context = nullptr;
void host_forget_perform(void *object) {
    auto found = g_perform_contexts.find(object);
    if (found == g_perform_contexts.end()) return;
    if (g_last_context == &found->second) g_last_context = nullptr;
    g_perform_contexts.erase(found);
}
void dsp_add64(void * /*dsp64*/, t_object *x, t_perfroutine64 f, long flags, void *userparam) {
    if (g_rendering || !g_compiling_context || !x || !f || flags) { ++g_unsupported; return; }
    g_compiling_context->calls.push_back({x, f, userparam});
}
host_perform_context *host_get_perform_context(t_object *object) {
    if (g_rendering) { ++g_unsupported; return nullptr; }
    auto found = g_perform_contexts.find(object);
    return found == g_perform_contexts.end() || found->second.calls.empty() ? nullptr : &found->second;
}
int host_run_context(host_perform_context *context, double **ins, long numins,
                     double **outs, long numouts, long frames) {
    if (g_rendering || !context || context->calls.empty() || frames < 0 ||
        frames > context->maximumFrames || numins != context->inputs ||
        numouts != context->outputs ||
        (numins && !ins) || (numouts && !outs)) return 0;
    for (long index = 0; index < numins; ++index) if (!ins[index]) return 0;
    for (long index = 0; index < numouts; ++index) if (!outs[index]) return 0;
    struct RenderScope { RenderScope() { g_rendering = true; } ~RenderScope() { g_rendering = false; } } scope;
    try {
        for (const auto &call : context->calls)
            call.function(call.object, nullptr, ins, numins, outs, numouts, frames, 0, call.user);
    } catch (...) { ++g_unsupported; return 0; }
    return 1;
}
void *outlet_new(void *x, const char *type) {
    if (g_rendering) { ++g_unsupported; return nullptr; }
    if (type && !strcmp(type, "signal")) ++g_signal_ports[x].outputs;
    static long slot = 1;
    return reinterpret_cast<void *>(slot++);
}

// ---- buffer API ----------------------------------------------------------
// A t_buffer_ref points at a named buffer holding interleaved-by-channel sample
// data. The host installs the loaded sample before dsp.
struct HostBuffer { long frames = 0, channels = 0; double sr = 44100; float *samples = nullptr; };
struct t_buffer_ref_impl { t_symbol *name; HostBuffer *buf; };
static std::unordered_map<std::string, HostBuffer *> g_buffers;

HostBuffer *host_buffer_set(const char *name, long frames, long channels, double sr, const float *interleaved) {
    if (g_rendering || frames <= 0 || channels <= 0 || channels > 64 || !interleaved || !std::isfinite(sr) || sr <= 0 || size_t(frames) > SIZE_MAX / sizeof(float) / size_t(channels) || g_buffers.count(name)) return nullptr;
    auto *b = new HostBuffer(); b->frames = frames; b->channels = channels; b->sr = sr;
    b->samples = (float *)malloc(sizeof(float) * frames * channels);
    if (!b->samples) { delete b; return nullptr; }
    memcpy(b->samples, interleaved, sizeof(float) * frames * channels);
    g_buffers[name] = b; return b;
}
void host_set_sr(double sr) { g_sr = sr; }

void *buffer_ref_new(t_object * /*x*/, t_symbol *name) {
    auto *r = (t_buffer_ref_impl *)calloc(1, sizeof(t_buffer_ref_impl));
    r->name = name ? name : gensym("");
    auto it = g_buffers.find(r->name->s_name); r->buf = it == g_buffers.end() ? nullptr : it->second;
    return r;
}
void buffer_ref_set(void *ref, t_symbol *name) {
    if (g_rendering || !ref) { ++g_unsupported; return; }
    auto *r = (t_buffer_ref_impl *)ref; r->name = name;
    auto it = g_buffers.find(name ? name->s_name : ""); r->buf = it == g_buffers.end() ? nullptr : it->second;
}
void *buffer_ref_getobject(void *ref) { auto *r = (t_buffer_ref_impl *)ref; return r ? r->buf : nullptr; }
t_max_err buffer_ref_notify(void *, t_symbol *, t_symbol *, void *, void *) { return 0; }
void *buffer_view(void * /*buffer_obj*/) { return nullptr; }
long buffer_getframecount(void *b) { return b ? ((HostBuffer *)b)->frames : 0; }
long buffer_getchannelcount(void *b) { return b ? ((HostBuffer *)b)->channels : 0; }
double buffer_getsamplerate(void *b) { return b ? ((HostBuffer *)b)->sr : g_sr; }
float *buffer_locksamples(void *b) { return b ? ((HostBuffer *)b)->samples : nullptr; }
void buffer_unlocksamples(void * /*b*/) {}

// ---- host helpers used by the loader (not Max symbols) -------------------
t_maxclass *host_get_class(const char *name) {
    if (!g_classes) return nullptr; auto it = g_classes->find(name); return it == g_classes->end() ? nullptr : it->second;
}
size_t host_attr_count(t_maxclass *c) { return c->attrs.size(); }
const char *host_attr_name(t_maxclass *c, size_t index) {
    return c && index < c->attrs.size() ? c->attrs[index]->name->s_name : nullptr;
}
const char *host_attr_type(t_maxclass *c, size_t index) {
    return c && index < c->attrs.size() ? c->attrs[index]->type.c_str() : nullptr;
}
size_t host_method_count(t_maxclass *c) { return c ? c->methods.size() : 0; }
const char *host_method_name(t_maxclass *c, size_t index) {
    return c && index < c->methods.size() ? c->methods[index].name->s_name : nullptr;
}
long host_signal_inlet_count(t_object *x) {
    auto found = g_signal_ports.find(x);
    return found == g_signal_ports.end() ? -1 : found->second.inputs;
}
long host_signal_outlet_count(t_object *x) {
    auto found = g_signal_ports.find(x);
    return found == g_signal_ports.end() ? -1 : found->second.outputs;
}
t_method host_get_method(t_object *x, const char *name) {
    auto *c = (t_maxclass *)object_class(x); t_symbol *s = gensym(name);
    if (!c) return nullptr;
    for (auto &m : c->methods) if (m.name == s) return m.fn;
    return nullptr;
}
void host_run_perform(double **ins, long numins, double **outs, long numouts, long frames) {
    if (!host_run_context(g_last_context, ins, numins, outs, numouts, frames)) ++g_unsupported;
}
t_max_err host_set_attr(t_object *x, const char *name, double v) { return object_attr_setfloat(x, gensym(name), v); }
t_max_err host_get_numeric_attr(t_object *x, const char *name, double *value) {
    if (!value) return -1;
    long count = 0;
    t_atom *atoms = nullptr;
    auto error = object_attr_getvalueof(x, gensym(name), &count, &atoms);
    if (!error && (count != 1 || !atoms || (atoms[0].a_type != A_LONG && atoms[0].a_type != A_FLOAT))) error = -1;
    if (!error) {
        double candidate = atom_getfloat(atoms);
        if (!std::isfinite(candidate)) error = -1;
        else *value = candidate;
    }
    free(atoms);
    return error;
}

// SDK fileusage is standalone/collective dependency reporting, NOT a package
// loader. Only registered collector handles and whole-package reports are
// supported. Atomarray subfolder filtering is explicitly unsupported.
struct t_atomarray;
struct host_fileusage_context { std::vector<std::string> packages; };
static std::unordered_map<void *, host_fileusage_context *> g_fileusage;
host_fileusage_context *host_fileusage_new(void) {
    if (g_rendering) { ++g_unsupported; return nullptr; }
    auto *context = new host_fileusage_context();
    g_fileusage[context] = context;
    return context;
}
void fileusage_addpackage(void *w, const char *name, t_atomarray *subfoldernames) {
    auto found = g_fileusage.find(w);
    if (g_rendering || found == g_fileusage.end() || !name || !*name || subfoldernames) {
        ++g_unsupported;
        return;
    }
    auto &packages = found->second->packages;
    if (std::find(packages.begin(), packages.end(), name) == packages.end()) packages.emplace_back(name);
}
int host_collect_fileusage(t_object *x, host_fileusage_context *context) {
    if (g_rendering || !g_fileusage.count(context)) { ++g_unsupported; return 0; }
    auto method = host_get_method(x, "fileusage");
    if (!method) return 0;
    auto before = g_unsupported;
    ((void (*)(t_object *, void *))method)(x, context);
    return before == g_unsupported;
}
size_t host_fileusage_count(host_fileusage_context *context) {
    return g_fileusage.count(context) ? context->packages.size() : 0;
}
const char *host_fileusage_package(host_fileusage_context *context, size_t index) {
    return g_fileusage.count(context) && index < context->packages.size() ? context->packages[index].c_str() : nullptr;
}
void host_fileusage_free(host_fileusage_context *context) {
    if (g_rendering) { ++g_unsupported; return; }
    if (g_fileusage.erase(context)) delete context;
}

} // extern "C"

extern "C" void *host_new_instance(t_maxclass *c) {
    // Class new is A_GIMME: new(t_symbol *s, long argc, t_atom *argv).
    typedef void *(*newfn)(t_symbol *, long, t_atom *);
    return ((newfn)c->newmethod)(gensym(c->name.c_str()), 0, nullptr);
}

// Loader-facing trigger/dsp helpers.
extern "C" {
void host_send_int(t_object *x, long n) {
    t_method m = host_get_method(x, "int");
    if (m) ((void (*)(t_object *, t_atom_long))m)(x, (t_atom_long)n);
}
void host_notify(t_object *x, const char *bufname, const char *msg) {
    t_method m = host_get_method(x, "notify");   // notify(x, s, msg, sender, data)
    if (!m) { fprintf(stderr, "no notify method\n"); return; }
    auto it = g_buffers.find(bufname); void *bufobj = it == g_buffers.end() ? nullptr : it->second;
    ((void (*)(t_object *, t_symbol *, t_symbol *, void *, void *))m)(x, gensym(bufname), gensym(msg), bufobj, nullptr);
}
void host_send_set(t_object *x, const char *bufname) {
    t_method m = host_get_method(x, "set");   // A_GIMME: set(x, sel, argc, argv)
    if (!m) { fprintf(stderr, "no set method\n"); return; }
    t_atom a{}; a.a_type = A_SYM; a.a_w.w_sym = gensym(bufname);
    ((void (*)(t_object *, t_symbol *, long, t_atom *))m)(x, gensym("set"), 1, &a);
}
int host_compile_dsp64(t_object *x, double sr, long maxvec, const short *connections, size_t connectionCount) {
    if (g_rendering || g_compiling_context || !x || !std::isfinite(sr) || sr <= 0 || maxvec <= 0) {
        ++g_unsupported; return 0;
    }
    const long inputs = host_signal_inlet_count(x), outputs = host_signal_outlet_count(x);
    if (!connections || connectionCount > 64 || inputs < 0 || outputs < 0 ||
        connectionCount < size_t(inputs + outputs)) { ++g_unsupported; return 0; }
    std::array<short, 64> count{};
    for (size_t i = 0; i < connectionCount; ++i) {
        if (connections[i] != 0 && connections[i] != 1) { ++g_unsupported; return 0; }
        count[i] = connections[i];
    }
    auto &context = g_perform_contexts[x];
    context.calls.clear(); context.maximumFrames = maxvec;
    // Preserve the full signal-port ABI, including disconnected inlets. Render
    // validation uses only this compiled data, never a registry lookup.
    context.inputs = inputs; context.outputs = outputs;
    g_last_context = &context;
    t_method m = host_get_method(x, "dsp64");
    if (!m) { fprintf(stderr, "no dsp64 method\n"); ++g_unsupported; return 0; }
    g_sr = sr;
    struct CompileScope {
        explicit CompileScope(host_perform_context *value) { g_compiling_context = value; }
        ~CompileScope() { g_compiling_context = nullptr; }
    } scope(&context);
    ((void (*)(t_object *, t_object *, short *, double, long, long))m)(x, nullptr, count.data(), sr, maxvec, 0);
    return !context.calls.empty();
}
void host_call_dsp64(t_object *x, double sr, long maxvec) {
    const short count[8] = { 0, 1, 1, 0, 0, 0, 0, 0 };
    (void)host_compile_dsp64(x, sr, maxvec, count, 8);
}
int host_has_perform(void) { return g_last_context && !g_last_context->calls.empty(); }
}
extern "C" void host_dump_attr_types(t_maxclass *c) {
    for (auto *a : c->attrs) fprintf(stderr, "attr %-14s type=%-8s off=0x%zx get=%d set=%d\n", a->name->s_name, a->type.c_str(), a->offset, a->get != nullptr, a->set != nullptr);
}
