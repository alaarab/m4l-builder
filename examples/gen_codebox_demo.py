"""Gen Codebox Demo -- inline gen~ DSP in Max for Live.

Shows two gen~ codeboxes doing sample-level DSP:
  1. Soft clipper: tanh saturation with a drive knob
  2. One-pole lowpass: simple history-based feedback filter

Each gen~ block receives audio from plugin~ and passes it to plugout~.
The signal chain is serial: plugin~ -> soft clip -> lowpass -> plugout~.
"""

from m4l_builder import AudioEffect, MIDNIGHT, gen_codebox, device_output_path

device = AudioEffect("Gen Codebox Demo", width=280, height=130, theme=MIDNIGHT)

# Background panel
device.add_panel("bg", [0, 0, 280, 130], bgcolor=MIDNIGHT.bg)

# Section labels
device.add_comment("lbl_clip", [12, 6, 110, 16], text="Soft Clip",
                   textcolor=MIDNIGHT.text)
device.add_comment("lbl_lp", [152, 6, 110, 16], text="Lowpass",
                   textcolor=MIDNIGHT.text)

# Drive dial for the soft clipper (1.0 = clean, 10.0 = heavy saturation)
device.add_dial("drive", "Drive", [20, 26, 50, 70],
                min_val=1.0, max_val=10.0, initial=1.0,
                unitstyle=1, appearance=0)

# Cutoff dial for the one-pole lowpass (0.0 = dark, 1.0 = open)
device.add_dial("cutoff", "Cutoff", [160, 26, 50, 70],
                min_val=0.01, max_val=1.0, initial=0.7,
                unitstyle=1, appearance=0)

# -- DSP: gen~ soft clipper --
# in1 = audio, in2 = drive amount
# tanh(x * drive) gives smooth saturation
soft_clip_code = """\
out1 = tanh(in1 * in2);
"""
clip_boxes, clip_lines = gen_codebox("clip", soft_clip_code,
                                     numinlets=2, numoutlets=1)
device.add_dsp(clip_boxes, clip_lines)

# -- DSP: gen~ one-pole lowpass --
# in1 = audio, in2 = coefficient (0-1, higher = brighter)
# Uses History for single-sample feedback
lowpass_code = """\
History prev(0);
coeff = in2;
out1 = prev + coeff * (in1 - prev);
prev = out1;
"""
lp_boxes, lp_lines = gen_codebox("lp", lowpass_code,
                                  numinlets=2, numoutlets=1)
device.add_dsp(lp_boxes, lp_lines)

# Parameter smoothing for drive: pack f 20 -> line~
device.add_newobj("drive_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 60, 60, 20])
device.add_newobj("drive_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 90, 40, 20])

# Parameter smoothing for cutoff: pack f 20 -> line~
device.add_newobj("cut_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[300, 60, 60, 20])
device.add_newobj("cut_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[300, 90, 40, 20])

# Signal chain: plugin~ -> soft clip -> lowpass -> plugout~
device.add_line("obj-plugin", 0, "clip_gen", 0)   # L into clipper
device.add_line("obj-plugin", 1, "clip_gen", 0)   # R summed to mono for demo
device.add_line("clip_gen", 0, "lp_gen", 0)        # clipper -> lowpass
device.add_line("lp_gen", 0, "obj-plugout", 0)     # lowpass -> out L
device.add_line("lp_gen", 0, "obj-plugout", 1)     # lowpass -> out R (mono spread)

# Drive dial -> pack -> line~ -> gen~ inlet 1
device.add_line("drive", 0, "drive_pk", 0)
device.add_line("drive_pk", 0, "drive_ln", 0)
device.add_line("drive_ln", 0, "clip_gen", 1)

# Cutoff dial -> pack -> line~ -> gen~ inlet 1
device.add_line("cutoff", 0, "cut_pk", 0)
device.add_line("cut_pk", 0, "cut_ln", 0)
device.add_line("cut_ln", 0, "lp_gen", 1)

# Possible third gen~ use: a waveshaper with Param for user-tunable curve,
# or a ring modulator using sin(counter * freq) for amplitude modulation.
# gen~ can do anything at sample rate: bitcrushers, phasers, custom envelopes.

output = device_output_path("Gen Codebox Demo", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
