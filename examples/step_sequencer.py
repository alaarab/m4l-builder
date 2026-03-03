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
  div_menu:  clock division (1/4, 1/8, 1/16, 1/32)
"""

from m4l_builder import MidiEffect, COOL, device_output_path

WIDTH = 400
HEIGHT = 180
device = MidiEffect("Step Sequencer", width=WIDTH, height=HEIGHT, theme=COOL)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])

device.add_comment("title", [8, 5, 100, 16], "STEP SEQ",
                   fontname="Ableton Sans Bold", fontsize=12.0)

# Section labels
device.add_comment("lbl_pitch", [8, 20, 50, 12], "PITCH",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])
device.add_comment("lbl_gate", [8, 100, 50, 12], "GATE",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

# 8 pitch sliders (vertical, MIDI notes 36-84)
# Each slider is 36px wide with 4px gap = 40px stride, starting at x=8
SLIDER_Y = 28
SLIDER_W = 28
SLIDER_H = 65
TOGGLE_Y = 112
TOGGLE_W = 28
TOGGLE_H = 20
X_START = 8
X_STRIDE = 40

for i in range(8):
    x = X_START + i * X_STRIDE
    device.add_slider(
        f"pitch_{i}", f"Pitch {i+1}", [x, SLIDER_Y, SLIDER_W, SLIDER_H],
        min_val=36.0, max_val=84.0, initial=60.0,
        unitstyle=8,     # MIDI note display
        orientation=1,   # vertical
        shortname=f"P{i+1}",
    )
    device.add_toggle(
        f"step_{i}", f"Step {i+1}", [x, TOGGLE_Y, TOGGLE_W, TOGGLE_H],
        shortname=f"S{i+1}",
        labels=("off", "on"),
    )

# Step number labels below toggles
for i in range(8):
    x = X_START + i * X_STRIDE + 8
    device.add_comment(f"lbl_step_{i}", [x, 135, 20, 12], str(i + 1),
                       fontsize=8.0, textcolor=[0.35, 0.60, 0.90, 0.5])

# Global controls section (right side)
CTRL_X = 330
device.add_comment("lbl_ctrl", [CTRL_X, 20, 60, 12], "GLOBAL",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.6])

device.add_dial("gate_dial", "Gate", [CTRL_X, 30, 45, 60],
                min_val=10.0, max_val=100.0, initial=50.0,
                unitstyle=5, appearance=1,
                shortname="Gate",
                annotation_name="Note gate length as percent of step duration")

device.add_dial("vel_dial", "Vel", [CTRL_X + 20, 100, 45, 60],
                min_val=1.0, max_val=127.0, initial=100.0,
                unitstyle=0, appearance=1,
                shortname="Vel",
                annotation_name="Note velocity (1-127)")

device.add_comment("lbl_div", [CTRL_X, 152, 60, 12], "DIVISION",
                   fontsize=9.0, textcolor=[0.35, 0.60, 0.90, 0.5])
device.add_menu("div_menu", "Division", [CTRL_X - 20, 163, 85, 16],
                options=["1/4", "1/8", "1/16", "1/32"],
                shortname="Div")

# =========================================================================
# DSP / Control objects
# =========================================================================

# Transport and BPM
device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[30, 30, 55, 20])
device.add_newobj("transport", "transport", numinlets=1, numoutlets=7,
                  outlettype=["int", "", "float", "float", "float", "", "int"],
                  patching_rect=[30, 60, 70, 20])

# BPM storage — holds tempo for recalculation
device.add_newobj("bpm_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[30, 90, 35, 20])

# Division selector: maps menu index (0-3) to beat fractions
# 1/4=1.0, 1/8=0.5, 1/16=0.25, 1/32=0.125
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

# Holds the current division fraction so BPM changes can recalculate
device.add_newobj("div_store", "f", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[120, 130, 35, 20])

# expr: step_ms = 60000 / BPM * beat_fraction
# inlet 0 = BPM, inlet 1 = beat fraction
device.add_newobj("step_expr", "expr 60000. / $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[200, 130, 130, 20])

# trigger to sequence: BPM → store, then feed expr
device.add_newobj("bpm_trig", "t f f", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[30, 90, 40, 20])

# metro: driven by computed step_ms
device.add_newobj("metro", "metro 500", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[350, 90, 55, 20])

# start/stop metro with transport (transport outlet 0 = running int 0/1)
device.add_newobj("metro_gate", "sel 0 1", numinlets=1, numoutlets=3,
                  outlettype=["bang", "bang", ""],
                  patching_rect=[350, 60, 55, 20])

# counter 0 7: counts 0-7, wraps back to 0
device.add_newobj("counter", "counter 0 7", numinlets=4, numoutlets=3,
                  outlettype=["int", "int", "int"],
                  patching_rect=[350, 120, 70, 20])

# sel to route counter output to step gates
device.add_newobj("step_sel", "sel 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["bang", "bang", "bang", "bang",
                               "bang", "bang", "bang", "bang", ""],
                  patching_rect=[350, 150, 150, 20])

# Per-step: gate check → retrieve pitch → makenote → noteout
# Each step uses: step_N toggle (gate), pitch_N slider value, global vel + gate%
# We use "route" logic: each sel outlet N fires a bang, we need to:
#   1. Check if step N toggle is on (int2float trick: bang → step_N value via send/receive)
#   2. Get pitch from slider N
#   3. Trigger makenote with vel + duration

# gate duration: gate_dial 10-100% of step_ms
# duration_ms = step_ms * (gate_dial / 100)
device.add_newobj("gate_scale", "* 0.01", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[500, 130, 55, 20])
device.add_newobj("gate_ms_mul", "* 500.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[560, 130, 55, 20])
device.add_newobj("gate_pct_store", "f 50.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[500, 110, 40, 20])
device.add_newobj("step_ms_store", "f 500.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[560, 110, 40, 20])

# One makenote for the whole sequencer; pitch and vel are set before each trigger
device.add_newobj("makenote", "makenote 60 100 500", numinlets=3, numoutlets=2,
                  outlettype=["int", "int"],
                  patching_rect=[350, 200, 110, 20])

device.add_newobj("noteout", "noteout", numinlets=3, numoutlets=0,
                  patching_rect=[350, 240, 50, 20])

# Velocity store
device.add_newobj("vel_store", "i 100", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[440, 200, 40, 20])

# Per-step objects: for each step we need:
#   - A "bang" from sel → trigger for the step
#   - Check toggle value: bangval of step_N toggle
#   - If on: read pitch slider value, pack pitch+vel, trigger makenote
# Use "if $i1 == 1 then bang" pattern with "gate" object (message gate)

for i in range(8):
    # route: sel bang → gate object controlled by step toggle value
    # We use: bang → getvalue of step_N toggle → if == 1, proceed
    # Simple approach: bangval the toggle, then sel 1 to gate the pitch
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

# Transport polling: loadbang → transport; transport outlet 0 = run state
device.add_line("loadbang", 0, "transport", 0)
device.add_line("transport", 0, "metro_gate", 0)
device.add_line("transport", 4, "bpm_trig", 0)   # outlet 4 = tempo float

# BPM trigger: outlet 1 fires first (stores BPM), outlet 0 fires second (bangs div_store)
device.add_line("bpm_trig", 1, "bpm_store", 1)   # right inlet sets stored value
device.add_line("bpm_trig", 0, "div_store", 0)   # bang div_store → feed expr inlet 1
device.add_line("bpm_store", 0, "step_expr", 0)
device.add_line("div_store", 0, "step_expr", 1)

# metro start/stop: sel 0=stop, sel 1=start
device.add_line("metro_gate", 0, "metro", 0)   # outlet 0 = "0" → send stop message
device.add_line("metro_gate", 1, "metro", 0)   # outlet 1 = "1" → send start message
# Actually wire stop/start messages via bang:
# sel 0 outlet → "stop", sel 1 outlet → "bang" (start)
# We'll use a simpler approach: transport outlet 0 int directly
device.add_line("transport", 0, "metro_gate", 0)

# Division menu → div_sel → beat fractions → div_store + step_expr
device.add_line("div_menu", 0, "div_sel", 0)
device.add_line("div_sel", 0, "div_f0", 0)
device.add_line("div_sel", 1, "div_f1", 0)
device.add_line("div_sel", 2, "div_f2", 0)
device.add_line("div_sel", 3, "div_f3", 0)

for fi, fname in enumerate(["div_f0", "div_f1", "div_f2", "div_f3"]):
    device.add_line(fname, 0, "div_store", 1)   # update stored fraction
    device.add_line(fname, 0, "step_expr", 1)   # update expr denominator

# step_expr → metro period (inlet 1) and stores
device.add_line("step_expr", 0, "metro", 1)
device.add_line("step_expr", 0, "step_ms_store", 1)

# metro → counter → step_sel
device.add_line("metro_gate", 0, "metro", 0)
device.add_line("metro_gate", 1, "metro", 0)
device.add_line("metro", 0, "counter", 0)   # bang inlet = count
device.add_line("counter", 0, "step_sel", 0)

# Velocity dial → vel_store
device.add_line("vel_dial", 0, "vel_store", 1)

# gate_dial → gate_pct_store
device.add_line("gate_dial", 0, "gate_pct_store", 1)

# Per-step wiring: step_sel outlet N → sv_gate_N → check toggle → read pitch → makenote
for i in range(8):
    # sel outlet N fires bang → trigger gate float read
    device.add_line("step_sel", i, f"sv_gate_{i}", 0)    # bang retrieves stored toggle val
    # toggle outlet feeds the gate float (toggled is sent on change; we store it)
    device.add_line(f"step_{i}", 0, f"sv_gate_{i}", 1)   # right inlet = set stored value
    device.add_line(f"sv_gate_{i}", 0, f"sv_eq_{i}", 0)
    device.add_line(f"sv_eq_{i}", 0, f"sv_sel_{i}", 0)
    # sel 1 outlet 0 = match → bang to fire pitch
    device.add_line(f"sv_sel_{i}", 0, f"sv_pitch_{i}", 0)  # bang retrieves pitch
    # pitch slider feeds the stored float value
    device.add_line(f"pitch_{i}", 0, f"sv_pitch_{i}", 1)   # right inlet = set value
    # pitch float → makenote inlet 0 (pitch)
    device.add_line(f"sv_pitch_{i}", 0, "makenote", 0)

# vel_store → makenote inlet 1
device.add_line("vel_store", 0, "makenote", 1)

# gate duration: step_ms_store * gate_pct_store / 100
device.add_line("step_ms_store", 0, "gate_ms_mul", 0)
device.add_line("gate_pct_store", 0, "gate_scale", 0)
device.add_line("gate_scale", 0, "gate_ms_mul", 1)
device.add_line("gate_ms_mul", 0, "makenote", 2)

# makenote → noteout
device.add_line("makenote", 0, "noteout", 0)
device.add_line("makenote", 1, "noteout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Step Sequencer", device_type="midi_effect")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
