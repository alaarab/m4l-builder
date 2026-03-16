"""8-step MIDI note sequencer — MidiEffect example.

Demonstrates: MidiEffect class, add_slider (pitch per step), add_toggle (step on/off),
tempo-synced metro driven by transport, counter for step indexing.

Signal flow:
  transport -> loadbang on load to poll BPM
  metro (ms from BPM + division) -> counter 0 7 -> sel 0 1 2 3 4 5 6 7
  sel outlet N -> gate (step N active?) -> makenote -> noteout

Step controls:
  8x live.slider (vertical, MIDI notes 36-84) — pitch per step
  8x live.toggle — on/off gate per step

Global controls:
  gate_dial: note length 10-100% of step duration
  vel_dial:  velocity 1-127
  div_tab:   clock division (1/4, 1/8, 1/16, 1/32)
"""

from m4l_builder import MidiEffect, MIDNIGHT, device_output_path

WIDTH = 460
HEIGHT = 230

# Slightly deeper background than standard MIDNIGHT
BG = [0.04, 0.04, 0.05, 1.0]
SURFACE = [0.09, 0.09, 0.10, 1.0]

device = MidiEffect("Step Sequencer", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], bgcolor=BG)

# Step grid panel — 80% of height
device.add_panel("steps_panel", [6, 6, 362, 184], bgcolor=SURFACE, rounded=4)

# Controls panel on the right
device.add_panel("ctrl_panel", [374, 6, 80, 218], bgcolor=SURFACE, rounded=4)

# Labels above grid sections
device.add_comment("lbl_pitch", [14, 12, 50, 10], "PITCH",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_gate", [14, 134, 50, 10], "GATE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)

# 8 pitch sliders — tall, takes most of the panel height
SLIDER_Y = 22
SLIDER_W = 32
SLIDER_H = 104
TOGGLE_Y = 138
TOGGLE_W = 32
TOGGLE_H = 24
X_START = 14
X_STRIDE = 44

for i in range(8):
    x = X_START + i * X_STRIDE
    device.add_slider(
        f"pitch_{i}", f"Pitch {i+1}", [x, SLIDER_Y, SLIDER_W, SLIDER_H],
        min_val=36.0, max_val=84.0, initial=60.0,
        unitstyle=8,
        orientation=1,
        shortname=f"P{i+1}",
        bgcolor=[0.06, 0.06, 0.07, 1.0],
        activebgcolor=MIDNIGHT.accent,
    )
    device.add_toggle(
        f"step_{i}", f"Step {i+1}", [x, TOGGLE_Y, TOGGLE_W, TOGGLE_H],
        shortname=f"S{i+1}",
        labels=("off", "on"),
    )

# Step number labels
for i in range(8):
    x = X_START + i * X_STRIDE + 10
    device.add_comment(f"lbl_step_{i}", [x, 166, 20, 10], str(i + 1),
                       fontsize=8.0, textcolor=MIDNIGHT.text_dim)

# Step counter — shows current playhead position
device.add_comment("lbl_step_pos", [14, 182, 30, 10], "STEP",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_number_box("step_display", "Step", [48, 180, 30, 14],
                      min_val=0, max_val=7,
                      shortname="Pos",
                      annotation_name="Current sequencer step")

# Global controls
CTRL_X = 382
device.add_comment("lbl_gate_c", [CTRL_X, 12, 64, 10], "GATE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_dial("gate_dial", "Gate", [CTRL_X - 2, 22, 68, 70],
                min_val=10.0, max_val=100.0, initial=50.0,
                unitstyle=5, appearance=1,
                shortname="Gate",
                annotation_name="Note gate length as percent of step duration")

device.add_comment("lbl_vel_c", [CTRL_X, 96, 64, 10], "VEL",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_dial("vel_dial", "Vel", [CTRL_X - 2, 106, 68, 70],
                min_val=1.0, max_val=127.0, initial=100.0,
                unitstyle=0, appearance=1,
                shortname="Vel",
                annotation_name="Note velocity (1-127)")

device.add_comment("lbl_div", [CTRL_X, 182, 64, 10], "DIV",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_tab("div_menu", "Division", [CTRL_X - 2, 192, 68, 26],
               options=["1/4", "1/8", "1/16", "1/32"],
               shortname="Div")

# =========================================================================
# DSP / Control objects
# =========================================================================

device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[30, 30, 55, 20])
device.add_newobj("transport", "transport", numinlets=1, numoutlets=7,
                  outlettype=["int", "", "float", "float", "float", "", "int"],
                  patching_rect=[30, 60, 70, 20])

device.add_newobj("bpm_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 90, 35, 20])

device.add_newobj("div_sel", "sel 0 1 2 3", numinlets=1, numoutlets=5,
                  outlettype=["bang", "bang", "bang", "bang", ""],
                  patching_rect=[30, 130, 80, 20])

device.add_newobj("div_f0", "f 1.0",   numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 160, 40, 20])
device.add_newobj("div_f1", "f 0.5",   numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[80, 160, 40, 20])
device.add_newobj("div_f2", "f 0.25",  numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[130, 160, 45, 20])
device.add_newobj("div_f3", "f 0.125", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[185, 160, 50, 20])

device.add_newobj("div_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[120, 130, 35, 20])

device.add_newobj("step_expr", "expr 60000. / $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 130, 130, 20])

device.add_newobj("bpm_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[30, 90, 40, 20])

device.add_newobj("metro", "metro 500", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[350, 90, 55, 20])

device.add_newobj("metro_gate", "sel 0 1", numinlets=1, numoutlets=3,
                  outlettype=["bang", "bang", ""],
                  patching_rect=[350, 60, 55, 20])

device.add_newobj("counter", "counter 0 7", numinlets=4, numoutlets=3,
                  outlettype=["int", "int", "int"],
                  patching_rect=[350, 120, 70, 20])

device.add_newobj("step_sel", "sel 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["bang", "bang", "bang", "bang",
                               "bang", "bang", "bang", "bang", ""],
                  patching_rect=[350, 150, 150, 20])

device.add_newobj("gate_scale", "* 0.01", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[500, 130, 55, 20])
device.add_newobj("gate_ms_mul", "* 500.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[560, 130, 55, 20])
device.add_newobj("gate_pct_store", "f 50.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[500, 110, 40, 20])
device.add_newobj("step_ms_store", "f 500.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[560, 110, 40, 20])

device.add_newobj("makenote", "makenote 60 100 500", numinlets=3, numoutlets=2,
                  outlettype=["int", "int"],
                  patching_rect=[350, 200, 110, 20])

device.add_newobj("noteout", "noteout", numinlets=3, numoutlets=0,
                  patching_rect=[350, 240, 50, 20])

device.add_newobj("vel_store", "i 100", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[440, 200, 40, 20])

for i in range(8):
    device.add_newobj(f"sv_gate_{i}", "f 0", numinlets=2, numoutlets=1,
                      outlettype=["float"], patching_rect=[500 + i * 60, 155, 40, 20])
    device.add_newobj(f"sv_eq_{i}", "== 1", numinlets=2, numoutlets=1,
                      outlettype=["int"], patching_rect=[500 + i * 60, 175, 35, 20])
    device.add_newobj(f"sv_sel_{i}", "sel 1", numinlets=1, numoutlets=2,
                      outlettype=["bang", ""], patching_rect=[500 + i * 60, 195, 40, 20])
    device.add_newobj(f"sv_pitch_{i}", "f 60", numinlets=2, numoutlets=1,
                      outlettype=["float"], patching_rect=[500 + i * 60, 215, 35, 20])

# =========================================================================
# Connections
# =========================================================================

device.add_line("loadbang", 0, "transport", 0)
device.add_line("transport", 0, "metro_gate", 0)
device.add_line("transport", 4, "bpm_trig", 0)

device.add_line("bpm_trig", 1, "bpm_store", 1)
device.add_line("bpm_trig", 0, "div_store", 0)
device.add_line("bpm_store", 0, "step_expr", 0)
device.add_line("div_store", 0, "step_expr", 1)

device.add_line("metro_gate", 0, "metro", 0)
device.add_line("metro_gate", 1, "metro", 0)
device.add_line("transport", 0, "metro_gate", 0)

device.add_line("div_menu", 0, "div_sel", 0)
device.add_line("div_sel", 0, "div_f0", 0)
device.add_line("div_sel", 1, "div_f1", 0)
device.add_line("div_sel", 2, "div_f2", 0)
device.add_line("div_sel", 3, "div_f3", 0)

for fi, fname in enumerate(["div_f0", "div_f1", "div_f2", "div_f3"]):
    device.add_line(fname, 0, "div_store", 1)
    device.add_line(fname, 0, "step_expr", 1)

device.add_line("step_expr", 0, "metro", 1)
device.add_line("step_expr", 0, "step_ms_store", 1)

device.add_line("metro_gate", 0, "metro", 0)
device.add_line("metro_gate", 1, "metro", 0)
device.add_line("metro", 0, "counter", 0)
device.add_line("counter", 0, "step_sel", 0)

# Counter output also drives the step position display
device.add_line("counter", 0, "step_display", 0)

device.add_line("vel_dial", 0, "vel_store", 1)
device.add_line("gate_dial", 0, "gate_pct_store", 1)

for i in range(8):
    device.add_line("step_sel", i, f"sv_gate_{i}", 0)
    device.add_line(f"step_{i}", 0, f"sv_gate_{i}", 1)
    device.add_line(f"sv_gate_{i}", 0, f"sv_eq_{i}", 0)
    device.add_line(f"sv_eq_{i}", 0, f"sv_sel_{i}", 0)
    device.add_line(f"sv_sel_{i}", 0, f"sv_pitch_{i}", 0)
    device.add_line(f"pitch_{i}", 0, f"sv_pitch_{i}", 1)
    device.add_line(f"sv_pitch_{i}", 0, "makenote", 0)

device.add_line("vel_store", 0, "makenote", 1)

device.add_line("step_ms_store", 0, "gate_ms_mul", 0)
device.add_line("gate_pct_store", 0, "gate_scale", 0)
device.add_line("gate_scale", 0, "gate_ms_mul", 1)
device.add_line("gate_ms_mul", 0, "makenote", 2)

device.add_line("makenote", 0, "noteout", 0)
device.add_line("makenote", 1, "noteout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Step Sequencer", device_type="midi_effect", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
