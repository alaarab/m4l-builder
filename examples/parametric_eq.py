"""Parametric EQ — Pro-Q style 8-band parametric equalizer.

Hero device showcasing the eq_curve jsui engine with interactive draggable
nodes. 8 fully parametric bands using filtercoeff~ + biquad~ for true
parametric EQ quality. Supports Peak/LShelf/HShelf/LP/HP/Notch/BP types.

Layout (500×280):
  Top 60%: Interactive EQ curve display (jsui) — draggable band nodes,
           mouse wheel Q, shift+drag fine-tune, cmd+drag lock gain,
           hover tooltips
  Bottom 40%: 8 band columns (Freq/Gain/Q tiny dials + type menu + enable)
              + Output section

DSP signal flow (filtercoeff~ + biquad~ per band):
  Each band: filtercoeff~ type -> biquad~ in series
  filtercoeff~ generates 5 biquad coefficients (a0,a1,a2,b1,b2) at signal rate
  biquad~ applies the filter: y[n] = a0*x[n] + a1*x[n-1] + a2*x[n-2] - b1*y[n-1] - b2*y[n-2]

  Signal chain:
    plugin~ L -> biquad~_b0_l -> biquad~_b1_l -> ... -> biquad~_b7_l -> out_gain_l -> plugout~ L
    plugin~ R -> biquad~_b0_r -> biquad~_b1_r -> ... -> biquad~_b7_r -> out_gain_r -> plugout~ R

  Each filtercoeff~ receives:
    inlet 0: frequency (Hz)
    inlet 1: gain (LINEAR via dbtoa, NOT dB)
    inlet 2: Q (resonance/bandwidth)
  And outputs 5 signal-rate coefficients to biquad~ inlets 1-5.

  When band is disabled: filtercoeff~ type set to "off" -> passthrough coefficients

CRITICAL RULES:
  - No sig~ — floats sent directly to signal inlets
  - filtercoeff~ gain is LINEAR not dB — always use dbtoa
  - Send "resamp 1" to each filtercoeff~ for smooth sweeps
  - *~ with no arg defaults to 0 — always use *~ 1. or *~ 0.
  - Panels: background:1
  - presentation_rect values must be whole integers
"""

import os
from m4l_builder import AudioEffect, MIDNIGHT
from m4l_builder.engines.eq_curve import eq_curve_js, EQ_CURVE_INLETS, EQ_CURVE_OUTLETS

# ---------------------------------------------------------------------------
# Device setup
# ---------------------------------------------------------------------------
device = AudioEffect("Parametric EQ", width=500, height=280, theme=MIDNIGHT)

# ---------------------------------------------------------------------------
# Colors (MIDNIGHT theme)
# ---------------------------------------------------------------------------
BG        = [0.07, 0.07, 0.08, 1.0]
SURFACE   = [0.10, 0.10, 0.11, 1.0]
TEXT      = [0.88, 0.88, 0.88, 1.0]
TEXT_DIM  = [0.50, 0.50, 0.52, 1.0]
ACCENT    = [0.45, 0.75, 0.65, 1.0]

# Per-band accent colors matching jsui BAND_COLORS
BAND_COLORS = [
    [0.90, 0.35, 0.35, 1.0],  # 1: red
    [0.90, 0.65, 0.25, 1.0],  # 2: orange
    [0.85, 0.85, 0.30, 1.0],  # 3: yellow
    [0.35, 0.80, 0.45, 1.0],  # 4: green
    [0.35, 0.75, 0.85, 1.0],  # 5: cyan
    [0.40, 0.55, 0.90, 1.0],  # 6: blue
    [0.65, 0.45, 0.85, 1.0],  # 7: purple
    [0.85, 0.45, 0.65, 1.0],  # 8: pink
]

NUM_BANDS = 8

# Default band presets: freq, type_index
# Types: 0=Peak, 1=LShelf, 2=HShelf, 3=LP, 4=HP, 5=Notch, 6=BP
BAND_DEFAULTS = [
    (30.0,    4),   # Band 1: HP 30 Hz
    (80.0,    1),   # Band 2: Low Shelf 80 Hz
    (250.0,   0),   # Band 3: Peak 250 Hz
    (800.0,   0),   # Band 4: Peak 800 Hz
    (2500.0,  0),   # Band 5: Peak 2.5 kHz
    (6000.0,  0),   # Band 6: Peak 6 kHz
    (10000.0, 2),   # Band 7: High Shelf 10 kHz
    (18000.0, 3),   # Band 8: LP 18 kHz
]

# filtercoeff~ type names for each menu index
FILTERCOEFF_TYPES = ["peaknotch", "lowshelf", "highshelf", "lowpass", "highpass",
                     "bandstop", "bandpass"]

TYPE_OPTIONS = ["Peak", "LShelf", "HShelf", "LP", "HP", "Notch", "BP"]

# ---------------------------------------------------------------------------
# UI — Background & title
# ---------------------------------------------------------------------------
device.add_panel("bg", [0, 0, 500, 280])

device.add_comment("title", [8, 4, 160, 16], "PARAMETRIC EQ",
                   fontname="Ableton Sans Bold", fontsize=13.0,
                   textcolor=TEXT)

# ---------------------------------------------------------------------------
# UI — EQ Curve jsui display (dominant hero element, top ~57%)
# ---------------------------------------------------------------------------
device.add_jsui(
    "eq_display",
    [6, 20, 488, 148],
    js_code=eq_curve_js(
        bg_color="0.05, 0.05, 0.06, 1.0",
        composite_color="0.85, 0.88, 0.92, 1.0",
        fill_color="0.45, 0.75, 0.65, 0.10",
        grid_color="0.18, 0.18, 0.20, 0.6",
        text_color="0.45, 0.45, 0.47, 1.0",
        zero_line_color="0.30, 0.30, 0.32, 0.9",
    ),
    numinlets=EQ_CURVE_INLETS,
    numoutlets=EQ_CURVE_OUTLETS,
    outlettype=[""] * EQ_CURVE_OUTLETS,
    patching_rect=[10, 30, 488, 148],
)

# ---------------------------------------------------------------------------
# UI — Section panel for bands (bottom ~40%)
# ---------------------------------------------------------------------------
device.add_panel("bands_bg", [6, 170, 488, 106],
                 bgcolor=SURFACE, rounded=4)

# ---------------------------------------------------------------------------
# UI — 8 Band columns + Output section
# Each band column is ~54px wide. 8 bands = 432px + output section 56px
# ---------------------------------------------------------------------------
BAND_X = [8, 62, 116, 170, 224, 278, 332, 386]
BAND_W = 52
OUT_X = 444

# Output section
device.add_comment("lbl_out", [OUT_X, 172, 48, 10], "OUTPUT",
                   textcolor=TEXT_DIM, fontsize=7.0)
device.add_dial("out_gain", "Out Gain", [OUT_X, 183, 44, 50],
                min_val=-24.0, max_val=24.0, initial=0.0,
                unitstyle=4, appearance=1,
                activedialcolor=ACCENT,
                annotation_name="Output Gain")
device.add_toggle("bypass_toggle", "Bypass",
                  [OUT_X + 8, 238, 28, 28],
                  activebgoncolor=[0.75, 0.30, 0.30, 1.0],
                  shortname="Bypass",
                  labels=("Active", "Bypass"))
device.add_comment("lbl_bypass", [OUT_X + 4, 268, 40, 9], "BYPASS",
                   textcolor=TEXT_DIM, fontsize=6.5)

# Per-band UI elements
for i, bx in enumerate(BAND_X):
    bc = BAND_COLORS[i]
    lbl = str(i + 1)
    default_freq, default_type = BAND_DEFAULTS[i]

    # Band number + colored indicator
    device.add_comment(f"lbl_b{i}", [bx, 172, 28, 9], f"B{lbl}",
                       textcolor=bc, fontsize=7.0,
                       fontname="Ableton Sans Bold")

    # Type menu (compact)
    device.add_menu(f"type_b{i}", f"Type B{lbl}",
                    [bx, 182, BAND_W, 14],
                    options=TYPE_OPTIONS,
                    shortname=f"Typ{lbl}",
                    patching_rect=[700 + i * 10, 200, BAND_W, 14])

    # Freq dial — tiny
    device.add_dial(f"freq_b{i}", f"Freq B{lbl}",
                    [bx, 198, 24, 34],
                    min_val=20.0, max_val=20000.0, initial=default_freq,
                    unitstyle=3, appearance=1, parameter_exponent=3.0,
                    activedialcolor=bc,
                    annotation_name=f"Band {lbl} Frequency")

    # Gain dial — tiny
    device.add_dial(f"gain_b{i}", f"Gain B{lbl}",
                    [bx + 26, 198, 24, 34],
                    min_val=-30.0, max_val=30.0, initial=0.0,
                    unitstyle=4, appearance=1,
                    activedialcolor=bc,
                    annotation_name=f"Band {lbl} Gain dB")

    # Q dial — tiny (hidden label, compact)
    device.add_dial(f"q_b{i}", f"Q B{lbl}",
                    [bx + 14, 234, 24, 34],
                    min_val=0.1, max_val=30.0, initial=1.0,
                    unitstyle=1, appearance=1,
                    activedialcolor=bc,
                    annotation_name=f"Band {lbl} Q")

    # Enable toggle — small, band color accent
    device.add_toggle(f"on_b{i}", f"On B{lbl}",
                      [bx + 18, 268, 14, 10],
                      activebgoncolor=bc,
                      shortname=f"On{lbl}")

# ---------------------------------------------------------------------------
# DSP — Init: loadbang -> "set_num_bands 8" message + resamp 1 messages
# ---------------------------------------------------------------------------
device.add_newobj("lb_init", "loadbang",
                  numinlets=0, numoutlets=1,
                  outlettype=["bang"],
                  patching_rect=[10, 200, 70, 20])

# Message to tell jsui about band count
device.add_box({
    "box": {
        "id": "msg_num_bands",
        "maxclass": "message",
        "text": "set_num_bands 8",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [10, 225, 120, 20],
    }
})

device.add_line("lb_init", 0, "msg_num_bands", 0)
device.add_line("msg_num_bands", 0, "eq_display", 0)

# ---------------------------------------------------------------------------
# DSP — Per-band jsui messaging using pak + prepend
#
# pak (all-hot): ANY inlet change triggers full list output.
# pak i freq gain q type enabled -> prepend set_band -> eq_display
# ---------------------------------------------------------------------------
for i in range(NUM_BANDS):
    lbl = str(i + 1)
    default_freq, default_type = BAND_DEFAULTS[i]

    # pak: 6 inlets, all hot. Initial: band_idx, freq, gain, q, type, on
    device.add_newobj(
        f"pak_b{i}",
        f"pak {i} {default_freq} 0. 1. {default_type} 1",
        numinlets=6, numoutlets=1,
        outlettype=[""],
        patching_rect=[800, 200 + i * 40, 200, 20]
    )

    # prepend set_band
    device.add_newobj(
        f"prepend_b{i}",
        "prepend set_band",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[800, 225 + i * 40, 120, 20]
    )

    # pak -> prepend -> eq_display
    device.add_line(f"pak_b{i}", 0, f"prepend_b{i}", 0)
    device.add_line(f"prepend_b{i}", 0, "eq_display", 0)

# ---------------------------------------------------------------------------
# DSP — Per-band filtercoeff~ + biquad~ (true parametric EQ)
#
# Architecture: per-band filtercoeff~ generates 5 biquad coefficients
# at signal rate -> connects to biquad~ inlets 1-5.
# biquad~ inlet 0 receives audio from previous stage.
# Bands cascade in series: plugin~ -> biquad~_b0 -> biquad~_b1 -> ... -> out
#
# filtercoeff~ inlets:
#   0: frequency (Hz) - float
#   1: gain (LINEAR) - float via dbtoa
#   2: Q (resonance) - float
#
# filtercoeff~ outlets (all signal):
#   0: a0, 1: a1, 2: a2, 3: b1, 4: b2
#
# biquad~ inlets:
#   0: signal input
#   1: a0, 2: a1, 3: a2, 4: b1, 5: b2
# ---------------------------------------------------------------------------

for i in range(NUM_BANDS):
    default_freq, default_type = BAND_DEFAULTS[i]
    fc_type = FILTERCOEFF_TYPES[default_type]

    # One filtercoeff~ per band (shared L+R — coefficients are the same)
    device.add_newobj(
        f"fc_b{i}",
        f"filtercoeff~ {fc_type}",
        numinlets=3, numoutlets=5,
        outlettype=["signal", "signal", "signal", "signal", "signal"],
        patching_rect=[100 + i * 60, 350, 80, 20]
    )

    # "resamp 1" message for smooth coefficient updates
    device.add_box({
        "box": {
            "id": f"msg_resamp_b{i}",
            "maxclass": "message",
            "text": "resamp 1",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [100 + i * 60, 320, 60, 20],
        }
    })
    device.add_line("lb_init", 0, f"msg_resamp_b{i}", 0)
    device.add_line(f"msg_resamp_b{i}", 0, f"fc_b{i}", 0)

    # Two biquad~ per band (one per channel)
    for ch in ["l", "r"]:
        y_off = 0 if ch == "l" else 200
        device.add_newobj(
            f"bq_b{i}_{ch}",
            "biquad~",
            numinlets=6, numoutlets=1,
            outlettype=["signal"],
            patching_rect=[100 + i * 60, 400 + y_off, 50, 20]
        )

        # Connect filtercoeff~ outlets 0-4 -> biquad~ inlets 1-5
        for c in range(5):
            device.add_line(f"fc_b{i}", c, f"bq_b{i}_{ch}", c + 1)

    # Gain conversion: dB -> linear via dbtoa
    # gain_dial outputs dB -> dbtoa -> filtercoeff~ inlet 1
    device.add_newobj(
        f"dbtoa_b{i}",
        "dbtoa",
        numinlets=1, numoutlets=1,
        outlettype=[""],
        patching_rect=[600, 350 + i * 30, 50, 20]
    )

    # Type switching: menu index -> filtercoeff~ type message
    # Route the type menu output to select the right type name
    device.add_newobj(
        f"type_sel_b{i}",
        "select 0 1 2 3 4 5 6",
        numinlets=1, numoutlets=8,
        outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang", ""],
        patching_rect=[700, 350 + i * 30, 140, 20]
    )

    # Message boxes for each filter type
    for ti, tname in enumerate(FILTERCOEFF_TYPES):
        device.add_box({
            "box": {
                "id": f"msg_type_{ti}_b{i}",
                "maxclass": "message",
                "text": tname,
                "numinlets": 2,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [700 + ti * 65, 380 + i * 30, 60, 20],
            }
        })
        # select outlet -> type message -> filtercoeff~
        device.add_line(f"type_sel_b{i}", ti, f"msg_type_{ti}_b{i}", 0)
        device.add_line(f"msg_type_{ti}_b{i}", 0, f"fc_b{i}", 0)

    # Enable/disable: when OFF, send "off" to filtercoeff~ (passthrough)
    # when ON, send the current type back
    # Use a gate: on_toggle -> gate -> type message replay
    # Simpler: use select 0 1 on the toggle output
    device.add_newobj(
        f"on_sel_b{i}",
        "select 0 1",
        numinlets=1, numoutlets=3,
        outlettype=["bang", "bang", ""],
        patching_rect=[900, 350 + i * 30, 60, 20]
    )
    # When OFF (0): send "off" to filtercoeff~
    device.add_box({
        "box": {
            "id": f"msg_off_b{i}",
            "maxclass": "message",
            "text": "off",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [900, 380 + i * 30, 30, 20],
        }
    })
    # When ON (1): resend current type via a trigger chain
    # We'll bang the type menu to re-output its current value
    device.add_newobj(
        f"on_bang_b{i}",
        "t b",
        numinlets=1, numoutlets=1,
        outlettype=["bang"],
        patching_rect=[940, 380 + i * 30, 30, 20]
    )

    device.add_line(f"on_sel_b{i}", 0, f"msg_off_b{i}", 0)     # OFF -> "off" msg
    device.add_line(f"msg_off_b{i}", 0, f"fc_b{i}", 0)          # "off" -> filtercoeff~
    device.add_line(f"on_sel_b{i}", 1, f"on_bang_b{i}", 0)      # ON -> bang
    device.add_line(f"on_bang_b{i}", 0, f"type_b{i}", 0)        # bang -> type menu re-output

# ---------------------------------------------------------------------------
# DSP — Parameter routing
# Each parameter goes to BOTH the DSP chain AND the pak for jsui update.
# ---------------------------------------------------------------------------
for i in range(NUM_BANDS):
    # freq -> pak inlet 1 AND filtercoeff~ inlet 0 (frequency Hz)
    device.add_line(f"freq_b{i}", 0, f"pak_b{i}", 1)
    device.add_line(f"freq_b{i}", 0, f"fc_b{i}", 0)

    # gain -> pak inlet 2 AND dbtoa -> filtercoeff~ inlet 1 (linear gain)
    device.add_line(f"gain_b{i}", 0, f"pak_b{i}", 2)
    device.add_line(f"gain_b{i}", 0, f"dbtoa_b{i}", 0)
    device.add_line(f"dbtoa_b{i}", 0, f"fc_b{i}", 1)

    # q -> pak inlet 3 AND filtercoeff~ inlet 2 (Q)
    device.add_line(f"q_b{i}", 0, f"pak_b{i}", 3)
    device.add_line(f"q_b{i}", 0, f"fc_b{i}", 2)

    # type -> pak inlet 4 AND type_sel for filtercoeff~ type switching
    device.add_line(f"type_b{i}", 0, f"pak_b{i}", 4)
    device.add_line(f"type_b{i}", 0, f"type_sel_b{i}", 0)

    # on -> pak inlet 5 AND on_sel for enable/disable
    device.add_line(f"on_b{i}", 0, f"pak_b{i}", 5)
    device.add_line(f"on_b{i}", 0, f"on_sel_b{i}", 0)

# ---------------------------------------------------------------------------
# DSP — Audio signal cascade: plugin~ -> biquad~_b0 -> biquad~_b1 -> ... -> out
# ---------------------------------------------------------------------------
for ch in ["l", "r"]:
    ch_idx = 0 if ch == "l" else 1

    # plugin~ -> first biquad~
    device.add_line("obj-plugin", ch_idx, f"bq_b0_{ch}", 0)

    # Chain biquad~ stages in series
    for i in range(NUM_BANDS - 1):
        device.add_line(f"bq_b{i}_{ch}", 0, f"bq_b{i+1}_{ch}", 0)

# ---------------------------------------------------------------------------
# DSP — Output gain stage
# out_gain dial (dB) -> dbtoa -> t f f -> *~ L, *~ R
# ---------------------------------------------------------------------------
device.add_newobj("out_dbtoa", "dbtoa",
                  numinlets=1, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[600, 600, 50, 20])

device.add_newobj("out_trig", "t f f",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[600, 625, 50, 20])

device.add_newobj("out_mul_l", "*~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 620, 40, 20])

device.add_newobj("out_mul_r", "*~ 1.",
                  numinlets=2, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[200, 620, 40, 20])

device.add_line("out_gain", 0, "out_dbtoa", 0)
device.add_line("out_dbtoa", 0, "out_trig", 0)
device.add_line("out_trig", 0, "out_mul_l", 1)
device.add_line("out_trig", 1, "out_mul_r", 1)

# Last biquad~ -> output gain multiplier
device.add_line(f"bq_b{NUM_BANDS-1}_l", 0, "out_mul_l", 0)
device.add_line(f"bq_b{NUM_BANDS-1}_r", 0, "out_mul_r", 0)

# ---------------------------------------------------------------------------
# DSP — Bypass: selector~ 2 1 (1=processed, 2=dry)
# bypass_toggle 0=not bypassed (processed), 1=bypassed (dry)
# toggle output: 0 -> +1 -> selector 1 (processed)
#                1 -> +1 -> selector 2 (dry)
# ---------------------------------------------------------------------------
device.add_newobj("bypass_add1", "+ 1",
                  numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[600, 660, 40, 20])

device.add_newobj("bypass_trig", "t i i",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[600, 685, 50, 20])

device.add_newobj("bypass_sel_l", "selector~ 2 1",
                  numinlets=3, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[100, 700, 80, 20])

device.add_newobj("bypass_sel_r", "selector~ 2 1",
                  numinlets=3, numoutlets=1,
                  outlettype=["signal"],
                  patching_rect=[200, 700, 80, 20])

device.add_line("bypass_toggle", 0, "bypass_add1", 0)
device.add_line("bypass_add1", 0, "bypass_trig", 0)
device.add_line("bypass_trig", 0, "bypass_sel_l", 0)
device.add_line("bypass_trig", 1, "bypass_sel_r", 0)

# Processed -> selector inlet 1
device.add_line("out_mul_l", 0, "bypass_sel_l", 1)
device.add_line("out_mul_r", 0, "bypass_sel_r", 1)

# Dry -> selector inlet 2
device.add_line("obj-plugin", 0, "bypass_sel_l", 2)
device.add_line("obj-plugin", 1, "bypass_sel_r", 2)

# Selector -> plugout~
device.add_line("bypass_sel_l", 0, "obj-plugout", 0)
device.add_line("bypass_sel_r", 0, "obj-plugout", 1)

# ---------------------------------------------------------------------------
# DSP — jsui drag output -> update freq/gain/Q dials (bidirectional)
# eq_display outlet 0: "selected_band N" — for future use
# eq_display outlet 1: "band_freq N freq" — route to freq_bi dial
# eq_display outlet 2: "band_gain N gain" — route to gain_bi dial
# eq_display outlet 3: "band_q N q" — route to q_bi dial
#
# Route chain: outlet -> route band_freq -> route 0 1 2 3 4 5 6 7 -> dial
# ---------------------------------------------------------------------------
# Freq routing from jsui drag
device.add_newobj("route_freq", "route band_freq",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[10, 780, 100, 20])
device.add_newobj("route_freq_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[10, 805, 200, 20])
device.add_line("eq_display", 1, "route_freq", 0)
device.add_line("route_freq", 0, "route_freq_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_freq_idx", i, f"freq_b{i}", 0)

# Gain routing from jsui drag
device.add_newobj("route_gain", "route band_gain",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[220, 780, 100, 20])
device.add_newobj("route_gain_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[220, 805, 200, 20])
device.add_line("eq_display", 2, "route_gain", 0)
device.add_line("route_gain", 0, "route_gain_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_gain_idx", i, f"gain_b{i}", 0)

# Q routing from jsui mouse wheel
device.add_newobj("route_q", "route band_q",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""],
                  patching_rect=[430, 780, 80, 20])
device.add_newobj("route_q_idx", "route 0 1 2 3 4 5 6 7",
                  numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[430, 805, 200, 20])
device.add_line("eq_display", 3, "route_q", 0)
device.add_line("route_q", 0, "route_q_idx", 0)
for i in range(NUM_BANDS):
    device.add_line("route_q_idx", i, f"q_b{i}", 0)

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
output = os.path.expanduser(
    "~/Music/Ableton/User Library/Presets/Audio Effects/"
    "Max Audio Effect/Parametric EQ.amxd"
)
os.makedirs(os.path.dirname(output), exist_ok=True)
written = device.build(output)
print(f"Built {written} bytes -> {output}")
