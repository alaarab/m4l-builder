#pragma once

#include "module_abi.h"
#include <stddef.h>

// Private original-module hosting API, not the complete shared Max runtime.
// All calls belong to one serialized host thread. In particular, this does not
// make original module allocation or locking safe on an audio callback.
// Obtain a render context after DSP compilation, outside rendering. Its address
// remains stable on recompilation and expires when its original object is freed.
// The caller must stop rendering before recompiling or freeing an instance.
#ifdef __cplusplus
extern "C" {
#endif
struct t_maxclass;
struct host_perform_context;
struct t_maxclass *host_get_class(const char *name);
size_t host_attr_count(struct t_maxclass *klass);
const char *host_attr_name(struct t_maxclass *klass, size_t index);
const char *host_attr_type(struct t_maxclass *klass, size_t index);
size_t host_method_count(struct t_maxclass *klass);
const char *host_method_name(struct t_maxclass *klass, size_t index);
void *host_new_instance(struct t_maxclass *klass);
void host_set_sr(double rate);
void *host_buffer_set(const char *name, long frames, long channels, double rate,
                      const float *interleaved);
void host_call_dsp64(t_object *object, double rate, long maximum_frames);
// Max count[] lists all signal inlets followed by all signal outlets. A zero
// means disconnected. This is connection metadata, not a sidechain router.
long host_signal_inlet_count(t_object *object);
long host_signal_outlet_count(t_object *object);
int host_compile_dsp64(t_object *object, double rate, long maximum_frames,
                       const short *connections, size_t connection_count);
struct host_perform_context *host_get_perform_context(t_object *object);
int host_run_context(struct host_perform_context *context, double **inputs,
                     long input_count, double **outputs, long output_count,
                     long frames);
void host_send_int(t_object *object, long value);
void host_send_set(t_object *object, const char *buffer_name);
void host_notify(t_object *object, const char *buffer_name, const char *message);
t_max_err host_set_attr(t_object *object, const char *name, double value);
t_max_err host_get_numeric_attr(t_object *object, const char *name, double *value);
struct host_fileusage_context;
struct host_fileusage_context *host_fileusage_new(void);
int host_collect_fileusage(t_object *object, struct host_fileusage_context *context);
size_t host_fileusage_count(struct host_fileusage_context *context);
const char *host_fileusage_package(struct host_fileusage_context *context, size_t index);
void host_fileusage_free(struct host_fileusage_context *context);
void host_set_audio_offset(double offset);
void host_drain_deferred(void);
unsigned long host_unsupported_calls(void);
void object_free(void *object);
#ifdef __cplusplus
}
#endif
