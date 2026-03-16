"""Probability Gate -- 16 vertical bars ARE the rhythm.

Each bar's height = probability (0-100%) that step fires. Shape rhythm
by adjusting bar heights. Tempo-synced via live.beat~, with density
scaling and swing control.

Signal flow:
  live.beat~ -> counter 0 15 -> fetch Nth probability from multislider
  -> random 100 -> compare against (prob * density/100)
  -> if pass: noteout 60 127, delayed note-off after 50ms
"""

from m4l_builder import MidiEffect, MIDNIGHT, device_output_path

WIDTH = 380
HEIGHT = 220

BG = [0.04, 0.04, 0.05, 1.0]
SURFACE = [0.09, 0.09, 0.10, 1.0]

device = MidiEffect("Probability Gate", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], bgcolor=BG)

# Hero: probability bars fill ~70% of height (154px of 220px)
device.add_multislider("steps_prob", [6, 6, 368, 154],
                       size=16, min_val=0.0, max_val=100.0,
                       setstyle=0,
                       orientation=0,
                       bgcolor=[0.04, 0.04, 0.05, 1.0],
                       slidercolor=MIDNIGHT.accent)

# Controls panel below
device.add_panel("ctrl_panel", [6, 166, 368, 48], bgcolor=SURFACE, rounded=4)

# Fire indicator — lights teal when a step fires
device.add_live_text("fire_ind", "GATE", [310, 172, 58, 16],
                     shortname="Gate",
                     text="GATE",
                     fontsize=9.0,
                     textcolor=MIDNIGHT.text_dim,
                     bgcolor=SURFACE,
                     bgoncolor=MIDNIGHT.accent,
                     textcolor_on=[0.04, 0.04, 0.05, 1.0])

# Section labels
device.add_comment("lbl_steps", [14, 172, 60, 10], "STEPS",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_rate", [100, 172, 50, 10], "RATE",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_dens", [178, 168, 50, 10], "DENSITY",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)
device.add_comment("lbl_swing", [246, 168, 50, 10], "SWING",
                   fontsize=8.0, textcolor=MIDNIGHT.text_dim)

# Controls row
device.add_tab("steps_count", "Steps", [14, 184, 78, 22],
               options=["8", "16"])

device.add_menu("rate", "Rate", [100, 184, 68, 22],
                options=["1/4", "1/8", "1/16", "1/32"])

device.add_dial("density", "Density", [178, 166, 60, 48],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, shortname="Dens",
                annotation_name="Density")

device.add_dial("swing", "Swing", [246, 166, 60, 48],
                min_val=0.0, max_val=50.0, initial=0.0,
                unitstyle=5, shortname="Swng",
                annotation_name="Swing Amount")

# =========================================================================
# DSP / Control objects
# =========================================================================

device.add_newobj("notein", "notein", numinlets=1, numoutlets=3,
                  outlettype=["int", "int", "int"],
                  patching_rect=[30, 30, 50, 20])
device.add_newobj("noteout", "noteout", numinlets=3, numoutlets=0,
                  patching_rect=[30, 60, 55, 20])

device.add_line("notein", 0, "noteout", 0)
device.add_line("notein", 1, "noteout", 1)
device.add_line("notein", 2, "noteout", 2)

device.add_newobj("on_gate", "gate", numinlets=2, numoutlets=1,
                  outlettype=[""],
                  patching_rect=[200, 60, 40, 20])

device.add_newobj("beat", "live.beat~ @sync 2", numinlets=1, numoutlets=4,
                  outlettype=["signal", "", "", "bang"],
                  patching_rect=[200, 90, 120, 20])

device.add_newobj("rate_add", "+ 1", numinlets=2, numoutlets=1,
                  outlettype=["int"],
                  patching_rect=[200, 120, 35, 20])

device.add_box({
    "box": {
        "id": "sync_msg",
        "maxclass": "message",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "text": "sync $1",
        "patching_rect": [200, 150, 50, 20],
    }
})

# Always-on: gate_on is implicitly always 1 — the toggle was removed in favor
# of the fire indicator showing activity. Wire beat directly.
device.add_newobj("always_on", "i 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[200, 45, 30, 20])

device.add_line("rate", 0, "rate_add", 0)
device.add_line("rate_add", 0, "sync_msg", 0)
device.add_line("sync_msg", 0, "beat", 0)

device.add_line("always_on", 0, "on_gate", 0)
device.add_line("beat", 3, "on_gate", 1)

device.add_newobj("steps_sel", "sel 0 1", numinlets=1, numoutlets=3,
                  outlettype=["bang", "bang", ""],
                  patching_rect=[300, 60, 55, 20])

device.add_newobj("max_8", "i 7", numinlets=2, numoutlets=1,
                  outlettype=["int"],
                  patching_rect=[300, 90, 30, 20])
device.add_newobj("max_16", "i 15", numinlets=2, numoutlets=1,
                  outlettype=["int"],
                  patching_rect=[340, 90, 35, 20])

device.add_line("steps_count", 0, "steps_sel", 0)
device.add_line("steps_sel", 0, "max_8", 0)
device.add_line("steps_sel", 1, "max_16", 0)

device.add_newobj("counter", "counter 0 15", numinlets=4, numoutlets=3,
                  outlettype=["int", "int", "int"],
                  patching_rect=[300, 130, 75, 20])

device.add_line("max_8", 0, "counter", 3)
device.add_line("max_16", 0, "counter", 3)
device.add_line("on_gate", 0, "counter", 0)

# =========================================================================
# Probability lookup
# =========================================================================

device.add_box({
    "box": {
        "id": "fetch_msg",
        "maxclass": "message",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "text": "fetch $1",
        "patching_rect": [300, 160, 55, 20],
    }
})

device.add_line("counter", 0, "fetch_msg", 0)
device.add_line("fetch_msg", 0, "steps_prob", 0)

# =========================================================================
# Probability comparison
# =========================================================================

device.add_newobj("dens_scale", "* 0.01", numinlets=2, numoutlets=1,
                  outlettype=["float"],
                  patching_rect=[400, 160, 50, 20])
device.add_newobj("dens_mul", "*", numinlets=2, numoutlets=1,
                  outlettype=["float"],
                  patching_rect=[400, 190, 30, 20])

device.add_line("density", 0, "dens_scale", 0)
device.add_line("dens_scale", 0, "dens_mul", 1)

device.add_newobj("prob_trig", "t f b", numinlets=1, numoutlets=2,
                  outlettype=["", "bang"],
                  patching_rect=[400, 100, 40, 20])

device.add_line("steps_prob", 0, "prob_trig", 0)
device.add_line("prob_trig", 0, "dens_mul", 0)

device.add_newobj("random", "random 100", numinlets=2, numoutlets=1,
                  outlettype=["int"],
                  patching_rect=[450, 130, 65, 20])

device.add_line("prob_trig", 1, "random", 0)

device.add_newobj("compare", "<", numinlets=2, numoutlets=1,
                  outlettype=["int"],
                  patching_rect=[450, 190, 25, 20])

device.add_line("dens_mul", 0, "compare", 1)
device.add_line("random", 0, "compare", 0)

device.add_newobj("fire_sel", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""],
                  patching_rect=[450, 220, 40, 20])

device.add_line("compare", 0, "fire_sel", 0)

# =========================================================================
# Note output
# =========================================================================

device.add_newobj("makenote", "makenote 60 127 50", numinlets=3, numoutlets=2,
                  outlettype=["int", "int"],
                  patching_rect=[450, 260, 100, 20])

device.add_newobj("gen_noteout", "noteout", numinlets=3, numoutlets=0,
                  patching_rect=[450, 300, 55, 20])

device.add_line("fire_sel", 0, "makenote", 0)
device.add_line("makenote", 0, "gen_noteout", 0)
device.add_line("makenote", 1, "gen_noteout", 1)

# fire_sel bang -> fire indicator (bang drives live.text on state briefly)
device.add_line("fire_sel", 0, "fire_ind", 0)

# =========================================================================
# Initial values
# =========================================================================

device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"],
                  patching_rect=[500, 30, 55, 20])

device.add_box({
    "box": {
        "id": "init_pattern",
        "maxclass": "message",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "text": "75 50 100 25 60 80 40 90 50 70 30 100 60 45 85 55",
        "patching_rect": [500, 60, 200, 20],
    }
})

device.add_line("loadbang", 0, "init_pattern", 0)
device.add_line("init_pattern", 0, "steps_prob", 0)

# Trigger always_on on load
device.add_line("loadbang", 0, "always_on", 0)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Probability Gate", device_type="midi_effect", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
