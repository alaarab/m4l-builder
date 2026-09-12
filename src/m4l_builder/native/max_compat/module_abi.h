// Narrow 64-bit Max SDK ABI for isolated original-module probes.
// Derived from Cycling '74 max-sdk-base (see module_host.md and SDK license).
// Do not confuse these public headers with the private device's C++ state.
#pragma once
#include <cstddef>
#include <cstdint>
extern "C" {
typedef intptr_t t_atom_long;
typedef uintptr_t t_atom_ulong;
typedef double t_atom_float;
typedef intptr_t t_ptr_int;
typedef void *t_ptr;
typedef t_atom_long t_max_err;
typedef struct _symbol { char *s_name; struct _object *s_thing; } t_symbol;
enum { A_NOTHING=0, A_LONG, A_FLOAT, A_SYM, A_OBJ, A_DEFLONG, A_DEFFLOAT,
       A_DEFSYM, A_GIMME, A_CANT, A_SEMI, A_COMMA, A_DOLLAR, A_DOLLARSYM,
       A_GIMMEBACK, A_DEFER=0x41, A_USURP=0x42, A_DEFER_LOW=0x43, A_USURP_LOW=0x44 };
typedef struct _atom {
    short a_type;
    union { t_atom_long w_long; t_atom_float w_float; t_symbol *w_sym; struct _object *w_obj; } a_w;
} t_atom;
typedef void *(*t_method)(void *);
typedef struct _messlist { t_symbol *m_sym; t_method m_fun; char m_type[8]; } t_messlist;
typedef struct _object {
    t_messlist *o_messlist;
    t_ptr_int o_magic;
    void *o_inlet;
    void *o_outlet;
} t_object;
typedef struct _pxobject {
    t_object z_ob;
    long z_in;
    void *z_proxy;
    long z_disabled;
    short z_count;
    short z_misc;
} t_pxobject;
typedef void (*t_perfroutine64)(t_object *, t_object *, double **, long, double **, long, long, long, void *);
}
static_assert(sizeof(void *) == 8 && sizeof(long) == 8, "This probe requires the 64-bit Unix Max ABI");
static_assert(sizeof(t_max_err) == 8 && sizeof(t_atom) == 16 && offsetof(t_atom, a_w) == 8, "Max atom ABI");
static_assert(sizeof(t_object) == 32 && offsetof(t_object, o_magic) == 8, "Max object ABI");
static_assert(sizeof(t_pxobject) == 64 && offsetof(t_pxobject, z_count) == 56 && offsetof(t_pxobject, z_misc) == 58, "MSP object ABI");
