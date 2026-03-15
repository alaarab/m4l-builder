"""Super Slicer Prototype — generative sample slicing instrument.

This is an original Max for Live instrument inspired by the workflow of
Virtual Riot's Super Slicer rack and the UI grammar of Granulator III /
Simpler-style sample tools:

- drop a source sample into a buffer
- define a movable scan region
- chop the region into slices and phrase-length steps
- move through those slices with sequential, random, or jumpy motion
- add chop, glitch, pitch drift, pitch envelope, autopan, filtering, drive,
  and wet/dry blending

The build intentionally focuses on a strong first-playable instrument rather
than a literal rack clone.
"""

from pathlib import Path
from shutil import copy2

from m4l_builder import Instrument, Theme, device_output_path
from m4l_builder.dsp import dry_wet_mix, lowpass_filter, saturation
from m4l_builder.engines.slice_overview import (
    SLICE_OVERVIEW_INLETS,
    SLICE_OVERVIEW_OUTLETS,
    slice_overview_js,
)
from m4l_builder.engines.slice_pattern_display import (
    SLICE_PATTERN_DISPLAY_INLETS,
    SLICE_PATTERN_DISPLAY_OUTLETS,
    slice_pattern_display_js,
)
from m4l_builder.parameters import ParameterSpec


WIDTH = 696
HEIGHT = 424
DEMO_SOURCE_PATH = Path(
    "/Users/squidbot/Desktop/VR Super-Slicer/Samples/115_Emin_SequencedComposite2.wav"
)
DEMO_SAMPLE_PATH = Path("/Users/squidbot/Music/Ableton/SuperSlicerDemo.wav")
if DEMO_SOURCE_PATH.exists():
    DEMO_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DEMO_SAMPLE_PATH.exists():
        copy2(DEMO_SOURCE_PATH, DEMO_SAMPLE_PATH)
HAS_DEMO_SAMPLE = DEMO_SAMPLE_PATH.exists()

SLICER_THEME = Theme.custom(
    bg=[0.055, 0.060, 0.068, 1.0],
    surface=[0.095, 0.104, 0.118, 1.0],
    section=[0.135, 0.145, 0.162, 1.0],
    text=[0.92, 0.92, 0.90, 1.0],
    text_dim=[0.56, 0.58, 0.62, 1.0],
    accent=[0.90, 0.67, 0.28, 1.0],
    tab_bg=[0.135, 0.145, 0.162, 1.0],
    tab_bg_on=[0.90, 0.67, 0.28, 1.0],
    tab_text=[0.72, 0.74, 0.78, 1.0],
    tab_text_on=[0.10, 0.10, 0.12, 1.0],
)

device = Instrument(
    "Super Slicer Prototype",
    width=WIDTH,
    height=HEIGHT,
    theme=SLICER_THEME,
)


def add_message(dev, box_id, text, rect):
    """Add a Max message box."""
    return dev.add_box({
        "box": {
            "id": box_id,
            "maxclass": "message",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "text": text,
            "patching_rect": rect,
        }
    })


# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT], bgcolor=SLICER_THEME.bg)
device.add_panel("hero_panel", [12, 12, 472, 156],
                 bgcolor=SLICER_THEME.surface, rounded=8)
device.add_panel("side_panel", [492, 12, 192, 156],
                 bgcolor=SLICER_THEME.surface, rounded=8)
device.add_panel("ctrl_panel", [12, 176, 672, 236],
                 bgcolor=SLICER_THEME.surface, rounded=8)

device.add_comment("hero_title", [20, 18, 220, 12], "SLICE SURFACE",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_comment("hero_hint", [256, 18, 136, 12], "CLICK TO MOVE POSITION",
                   fontsize=8.0, justification=2, textcolor=SLICER_THEME.text_dim)
device.add_comment("dir_lbl", [400, 18, 24, 12], "DIR",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_menu(
    "dir_menu",
    "Direction",
    [424, 14, 52, 18],
    options=["FWD", "ALT", "REV"],
    annotation_name="Slice direction mode",
)

device.add_jsui(
    "slice_surface",
    [16, 32, 464, 84],
    js_code=slice_overview_js(
        bg_color="0.05, 0.055, 0.060, 1.0",
        grid_color="0.19, 0.20, 0.22, 0.92",
        wave_color="0.54, 0.63, 0.76, 0.44",
        region_fill="0.90, 0.67, 0.28, 0.14",
        region_line="0.90, 0.67, 0.28, 0.88",
        playhead_color="0.98, 0.95, 0.82, 0.94",
        text_color="0.74, 0.76, 0.80, 0.92",
    ),
    numinlets=SLICE_OVERVIEW_INLETS,
    numoutlets=SLICE_OVERVIEW_OUTLETS,
)
device.add_comment("pattern_title", [20, 122, 140, 10], "PATTERN LANE",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_comment("pattern_hint", [42, 122, 438, 10], "DRAG SLICE  CTRL PITCH  OPT DIR  CMD+OPT GATE  SHF+OPT RATCH  CMD ERASE  SHIFT CLEAR",
                   fontsize=8.0, justification=2, textcolor=SLICER_THEME.text_dim)
device.add_jsui(
    "pattern_lane",
    [16, 132, 464, 26],
    js_code=slice_pattern_display_js(
        bg_color="0.05, 0.055, 0.060, 1.0",
        grid_color="0.18, 0.19, 0.21, 1.0",
        bar_color="0.90, 0.67, 0.28, 1.0",
        chopped_color="0.34, 0.37, 0.42, 1.0",
        glitch_color="0.98, 0.95, 0.82, 1.0",
        playhead_color="0.54, 0.63, 0.76, 0.22",
        text_color="0.72, 0.74, 0.78, 0.92",
    ),
    numinlets=SLICE_PATTERN_DISPLAY_INLETS,
    numoutlets=SLICE_PATTERN_DISPLAY_OUTLETS,
    outlettype=[""],
)

device.add_comment("source_title", [504, 18, 96, 12], "SOURCE",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_live_drop("sample_drop", [504, 32, 110, 28],
                     bgcolor=SLICER_THEME.section,
                     bordercolor=SLICER_THEME.accent,
                     textcolor=SLICER_THEME.text)
if HAS_DEMO_SAMPLE:
    device.add_live_text(
        "demo_btn",
        "Demo",
        [620, 32, 52, 28],
        text_on="DEMO",
        text_off="DEMO",
        mode=1,
        rounded=4.0,
        bgcolor=SLICER_THEME.section,
        bgoncolor=SLICER_THEME.accent,
        textcolor=SLICER_THEME.text,
        textoncolor=SLICER_THEME.bg,
        annotation_name="Load the built-in Super Slicer demo sample",
    )
    device.add_comment("source_hint", [504, 64, 168, 20],
                       "Drop your own sample or tap DEMO",
                       fontsize=8.0, textcolor=SLICER_THEME.text_dim)
else:
    device.add_comment("source_hint", [504, 64, 168, 20],
                       "Drop a loop, phrase, texture, or vocal",
                       fontsize=8.0, textcolor=SLICER_THEME.text_dim)

device.add_comment("mode_title", [504, 88, 72, 10], "MOTION",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_tab("mode_tab", "Mode", [504, 100, 104, 22],
               options=["RUN", "RND", "PAT", "JMP"],
               rounded=3.0, spacing_x=1.0)

device.add_comment("rate_title", [616, 88, 56, 10], "RATE",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_tab("rate_tab", "Rate", [616, 100, 56, 22],
               options=["1/4", "1/8", "1/16", "1/32"],
               rounded=3.0, spacing_x=1.0)

device.add_comment("slice_readout_lbl", [616, 18, 56, 10], "SLICE",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_number_box("slice_readout", "Slice", [616, 30, 56, 18],
                      min_val=0.0, max_val=63.0,
                      shortname="Slice",
                      annotation_name="Current active slice")

device.add_comment("seed_title", [504, 124, 72, 10], "RESEED",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
seed_btn_y = 138
seed_btn_w = 36
seed_btn_gap = 6
seed_btn_bg = SLICER_THEME.section
seed_btn_on = SLICER_THEME.accent
seed_btn_text_on = SLICER_THEME.bg
for idx, (btn_id, text) in enumerate([
    ("pattern_seed_btn", "PAT"),
    ("pitch_seed_btn", "PIT"),
    ("chop_seed_btn", "CHP"),
    ("glitch_seed_btn", "GLT"),
]):
    x = 504 + idx * (seed_btn_w + seed_btn_gap)
    device.add_live_text(
        btn_id,
        text,
        [x, seed_btn_y, seed_btn_w, 18],
        text_on=text,
        text_off=text,
        mode=1,
        rounded=3.0,
        bgcolor=seed_btn_bg,
        bgoncolor=seed_btn_on,
        textcolor=SLICER_THEME.text,
        textoncolor=seed_btn_text_on,
        annotation_name=f"Re-roll {text} module seed",
    )

ROW1_Y = 190
ROW2_Y = 262
ROW3_Y = 334
LABEL1_Y = 246
LABEL2_Y = 318
LABEL3_Y = 390
DIAL_W = 52
DIAL_H = 52
X0 = 18
STRIDE = 74

row1_controls = [
    ("position_dial", "Position", 0.0, 100.0, 12.0, 5, "SCAN"),
    ("region_dial", "Region", 5.0, 100.0, 32.0, 5, "REGION"),
    ("slices_dial", "Slices", 4.0, 32.0, 16.0, 0, "SLICES"),
    ("steps_dial", "Steps", 1.0, 32.0, 16.0, 0, "STEPS"),
    ("distance_dial", "Distance", 1.0, 8.0, 1.0, 0, "DIST"),
    ("jump_dial", "Jump", 0.0, 100.0, 32.0, 5, "JUMP"),
    ("chop_dial", "Chop", 0.0, 100.0, 0.0, 5, "CHOP"),
    ("glitch_dial", "Glitch", 0.0, 100.0, 0.0, 5, "GLITCH"),
]

row2_controls = [
    ("jitter_dial", "Jitter", 0.0, 100.0, 10.0, 5, "JITTER"),
    ("pitch_dial", "Pitch", 0.0, 12.0, 3.0, 7, "PITCH"),
    ("pitch_env_dial", "Pitch Env", 0.0, 24.0, 6.0, 7, "P ENV"),
    ("decay_dial", "Decay", 12.0, 220.0, 72.0, 0, "DECAY"),
    ("pan_dial", "Pan", -100.0, 100.0, 0.0, 5, "PAN"),
    ("filter_dial", "Filter", 80.0, 18000.0, 9600.0, 3, "FILTER"),
    ("drive_dial", "Drive", 0.0, 100.0, 24.0, 5, "DRIVE"),
    ("mix_dial", "Mix", 0.0, 100.0, 72.0, 5, "MIX"),
]

row3_controls = [
    ("poly_dial", "Poly", 1.0, 4.0, 1.0, 0, "POLY"),
    ("spread_dial", "Spread", 1.0, 8.0, 1.0, 0, "SPREAD"),
    ("bias_dial", "Bias", -100.0, 100.0, 0.0, 5, "BIAS"),
    ("arp_dial", "Arp", 0.0, 100.0, 22.0, 5, "ARP"),
    ("free_rate_dial", "Free Rate", 40.0, 600.0, 125.0, 0, "FREE"),
    ("wander_dial", "Wander", 0.0, 100.0, 18.0, 5, "WANDER"),
]

for row_y, label_y, controls in [
    (ROW1_Y, LABEL1_Y, row1_controls),
    (ROW2_Y, LABEL2_Y, row2_controls),
    (ROW3_Y, LABEL3_Y, row3_controls),
]:
    for index, (box_id, name, minimum, maximum, initial, unitstyle, label) in enumerate(controls):
        x = X0 + index * STRIDE
        exponent = 3.0 if box_id == "filter_dial" else 1.0
        device.add_dial(
            box_id,
            name,
            [x, row_y, DIAL_W, DIAL_H],
            min_val=minimum,
            max_val=maximum,
            initial=initial,
            unitstyle=unitstyle,
            parameter_exponent=exponent,
            appearance=1,
            annotation_name=name,
        )
        device.add_comment(f"{box_id}_lbl", [x, label_y, DIAL_W, 10], label,
                           fontsize=8.0, justification=1, textcolor=SLICER_THEME.text_dim)

device.add_live_gain("output_gain", "Output", [632, 190, 36, 210],
                     min_val=-24.0, max_val=6.0, initial=0.0,
                     orientation=1, shortname="Out")

sync_x = X0 + 6 * STRIDE
device.add_comment("sync_lbl", [sync_x, ROW3_Y, 52, 10], "SYNC",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_live_text(
    "sync_btn",
    "Sync",
    [sync_x, ROW3_Y + 16, 52, 22],
    text_on="SYNC",
    text_off="FREE",
    mode=0,
    rounded=4.0,
    bgcolor=SLICER_THEME.section,
    bgoncolor=SLICER_THEME.accent,
    textcolor=SLICER_THEME.text,
    textoncolor=SLICER_THEME.bg,
    parameter=ParameterSpec.enumerated(
        "Sync",
        ["FREE", "SYNC"],
        initial=1,
        initial_enable=True,
    ),
    annotation_name="Sync slice stepping to host transport",
)

reroll_x = X0 + 7 * STRIDE
device.add_comment("reroll_lbl", [reroll_x, ROW3_Y, 64, 10], "ALL",
                   fontsize=8.0, textcolor=SLICER_THEME.text_dim)
device.add_live_text(
    "reroll_btn",
    "All",
    [reroll_x, ROW3_Y + 16, 64, 22],
    text_on="ALL",
    text_off="ALL",
    mode=1,
    rounded=4.0,
    bgcolor=SLICER_THEME.section,
    bgoncolor=SLICER_THEME.accent,
    textcolor=SLICER_THEME.text,
    textoncolor=SLICER_THEME.bg,
    annotation_name="Re-roll all seeded pattern generators",
)


# =========================================================================
# Playback / control core
# =========================================================================

device.add_newobj("notein", "notein", numinlets=1, numoutlets=3,
                  outlettype=["int", "int", "int"], patching_rect=[860, 20, 52, 20])

device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[1500, 760, 60, 20])

device.add_newobj("loadbang", "loadbang", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[760, 20, 60, 20])
device.add_newobj("transport", "transport", numinlets=1, numoutlets=7,
                  outlettype=["int", "", "float", "float", "float", "", "int"],
                  patching_rect=[760, 52, 76, 20])
device.add_newobj("bpm_store", "f 120.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[760, 84, 48, 20])

device.add_newobj("note_store", "f 36", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[860, 20, 44, 20])
device.add_newobj("vel_gt", "> 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[860, 52, 36, 20])
device.add_newobj("gate_sel", "sel 1 0", numinlets=1, numoutlets=3,
                  outlettype=["bang", "bang", ""], patching_rect=[860, 84, 58, 20])

device.add_newobj("metro", "metro 125", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[940, 84, 56, 20])
device.add_newobj("step_trig", "t b b b b b b b", numinlets=1, numoutlets=7,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang"],
                  patching_rect=[940, 116, 118, 20])
device.add_newobj("counter", "counter 0 127", numinlets=4, numoutlets=3,
                  outlettype=["int", "int", "int"], patching_rect=[940, 148, 76, 20])

device.add_newobj("rand_slice", "random 2048", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1080, 116, 72, 20])
device.add_newobj("rand_jitter", "random 2000", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1080, 148, 72, 20])
device.add_newobj(
    "rand_pitch",
    "expr abs((($i1 * (($i2 % 13) + 5)) + ($i2 * 29) + ($i1 * $i1 * 3)) % 2000)",
    numinlets=2, numoutlets=1, outlettype=["int"],
    patching_rect=[1080, 180, 312, 20],
)
device.add_newobj(
    "rand_chop",
    "expr abs((($i1 * (($i2 % 19) + 3)) + ($i2 * 17)) % 1000)",
    numinlets=2, numoutlets=1, outlettype=["int"],
    patching_rect=[1160, 116, 248, 20],
)
device.add_newobj(
    "rand_glitch",
    "expr abs((($i1 * (($i2 % 11) + 5)) + ($i2 * 23) + ($i1 * $i1 * 7)) % 1000)",
    numinlets=2, numoutlets=1, outlettype=["int"],
    patching_rect=[1160, 148, 324, 20],
)
device.add_newobj("rand_pan", "random 2000", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1160, 180, 72, 20])
device.add_newobj("reroll_sel", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1240, 20, 42, 20])
device.add_newobj("pattern_seed_sel", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1240, 52, 42, 20])
device.add_newobj("pitch_seed_sel", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1240, 84, 42, 20])
device.add_newobj("chop_seed_sel", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1240, 116, 42, 20])
device.add_newobj("glitch_seed_sel", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1240, 148, 42, 20])
device.add_newobj("seed_trig", "t b b b b", numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", "bang"],
                  patching_rect=[1290, 20, 94, 20])
device.add_newobj("pattern_seed_rand", "random 997", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1392, 20, 72, 20])
device.add_newobj("chop_seed_rand", "random 991", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1392, 52, 72, 20])
device.add_newobj("glitch_seed_rand", "random 983", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1392, 84, 72, 20])
device.add_newobj("pitch_seed_rand", "random 977", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1392, 116, 72, 20])
device.add_newobj("pattern_seed_store", "i 11", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1472, 20, 42, 20])
device.add_newobj("chop_seed_store", "i 37", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1472, 52, 42, 20])
device.add_newobj("glitch_seed_store", "i 53", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1472, 84, 42, 20])
device.add_newobj("pitch_seed_store", "i 79", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1472, 116, 42, 20])

device.add_newobj("mode_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[760, 148, 36, 20])
device.add_newobj("rate_sel", "sel 0 1 2 3", numinlets=1, numoutlets=5,
                  outlettype=["bang", "bang", "bang", "bang", ""],
                  patching_rect=[760, 180, 88, 20])
device.add_newobj("div_q", "f 1.0", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[760, 212, 44, 20])
device.add_newobj("div_8", "f 0.5", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[808, 212, 44, 20])
device.add_newobj("div_16", "f 0.25", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[856, 212, 48, 20])
device.add_newobj("div_32", "f 0.125", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[908, 212, 52, 20])
device.add_newobj("div_store", "f 0.25", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[968, 212, 48, 20])
device.add_newobj("step_ms_pair", "pak f f", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[1024, 212, 60, 20])
device.add_newobj("step_ms_expr", "expr 60000. / max(1.\\, $f1) * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1090, 212, 178, 20])
device.add_newobj("step_interval_pack", "pak i f f", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[1274, 212, 72, 20])
device.add_newobj("step_interval_expr", "expr if($i1 > 0\\, $f2\\, $f3)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1352, 212, 174, 20])

device.add_newobj("sample_buf", "buffer~ slicebuf 60000", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[760, 280, 132, 20])
device.add_newobj("sample_info", "info~ slicebuf", numinlets=1, numoutlets=9,
                  outlettype=["", "", "", "", "", "", "", "", ""],
                  patching_rect=[760, 312, 96, 20])
device.add_newobj("sample_ms_store", "f 10000.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[760, 344, 60, 20])
device.add_newobj("drop_trig", "t b l", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[900, 280, 44, 20])
device.add_newobj("drop_prep", "prepend replace", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[952, 280, 92, 20])
device.add_newobj("drop_wait", "delay 120", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[900, 312, 64, 20])
if HAS_DEMO_SAMPLE:
    device.add_newobj("demo_sel", "sel 1", numinlets=1, numoutlets=2,
                      outlettype=["bang", ""], patching_rect=[900, 344, 42, 20])
    add_message(
        device,
        "demo_read_msg",
        "replace {}".format(str(DEMO_SAMPLE_PATH)),
        [952, 344, 288, 18],
    )
add_message(device, "loaded_msg", "1", [972, 312, 28, 18])
add_message(device, "stop_msg", "stop", [1008, 84, 36, 18])
add_message(device, "loop_msg", "loop 1", [1050, 312, 44, 18])
add_message(device, "startloop_msg", "startloop", [1050, 344, 60, 18])

device.add_newobj("slices_store", "i 16", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[760, 392, 40, 20])
device.add_newobj("steps_store", "i 16", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[808, 392, 40, 20])
device.add_newobj("distance_store", "i 1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[856, 392, 40, 20])

device.add_newobj("region_ms_pair", "pak f f", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[760, 424, 60, 20])
device.add_newobj("region_ms_expr", "expr max(20.\\, $f1 * ($f2 / 100.))",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[828, 424, 186, 20])
device.add_newobj("region_start_trip", "pak f f f", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[760, 456, 76, 20])
device.add_newobj(
    "region_start_expr",
    "expr max(0.\\, ($f1 - ($f1 * ($f2 / 100.))) * ($f3 / 100.))",
    numinlets=3, numoutlets=1, outlettype=["float"],
    patching_rect=[844, 456, 224, 20],
)
device.add_newobj("scan_seq_expr", "expr if($f2 <= 1.\\, 0.\\, (($i1 / ($f2 - 1.)) * 2.) - 1.)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1076, 424, 228, 20])
device.add_newobj(
    "scan_pat_expr",
    "expr (abs((($i1 * (($i2 % 7) + 3)) + ($i2 * 13) + ($i1 * $i1 * 5)) % 2000) / 999.5) - 1.",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1076, 456, 368, 20],
)
device.add_newobj("scan_rand_norm_expr", "expr ($f1 / 1023.5) - 1.",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1452, 424, 140, 20])
device.add_newobj("scan_jump_expr", "expr max(-1.\\, min(1.\\, $f1 + (($f2 / 100.) * $f3)))",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1452, 456, 240, 20])
device.add_newobj("scan_mode_expr", "expr if($i1 == 0\\, $f2\\, if($i1 == 1\\, $f3\\, if($i1 == 2\\, $f4\\, $f5)))",
                  numinlets=5, numoutlets=1, outlettype=["float"],
                  patching_rect=[1700, 440, 266, 20])
device.add_newobj("scan_range_expr", "expr max(0.\\, ($f1 - $f2) * ($f3 / 100.) * 0.5)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1076, 488, 242, 20])
device.add_newobj("scan_offset_expr", "expr $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1326, 488, 108, 20])
device.add_newobj("region_start_final_expr",
                  "expr max(0.\\, min(max(0.\\, $f2 - $f3)\\, $f1 + $f4))",
                  numinlets=4, numoutlets=1, outlettype=["float"],
                  patching_rect=[1442, 488, 262, 20])
device.add_newobj("slice_ms_pair", "pak f i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[760, 488, 60, 20])
device.add_newobj("slice_ms_expr", "expr max(10.\\, $f1 / max(1\\, $i2))",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[828, 488, 184, 20])
device.add_newobj("step_phase_expr", "expr $i1 % max(1\\, $i2)",
                  numinlets=2, numoutlets=1, outlettype=["int"],
                  patching_rect=[1020, 488, 156, 20])
device.add_newobj("step_index_trig", "t i i i i i", numinlets=1, numoutlets=5,
                  outlettype=["int", "int", "int", "int", "int"], patching_rect=[1184, 488, 82, 20])

device.add_newobj(
    "index_expr",
    (
        "expr if($i4 == 0\\, "
        "(($i1 * max(1\\, $i2)) % max(1\\, $i3))\\, "
        "if($i4 == 1\\, "
        "($i5 % max(1\\, $i3))\\, "
        "if($i4 == 2\\, "
        "((($i1 * ((($i6 % 5) + 1) * max(1\\, $i2))) + (($i1 * $i1) * (($i6 % 3) + 1)) + ($i6 % max(1\\, $i3))) % max(1\\, $i3))\\, "
        "(((($i1 * max(1\\, $i2)) % max(1\\, $i3)) + int(($f7 / 100.) * ($i5 % max(1\\, $i3)))) % max(1\\, $i3)))))"
    ),
    numinlets=7, numoutlets=1, outlettype=["int"],
    patching_rect=[760, 520, 544, 20],
)
device.add_newobj("index_trig", "t b i", numinlets=1, numoutlets=2,
                  outlettype=["bang", "int"], patching_rect=[760, 552, 44, 20])
device.add_newobj("index_fire_trig", "t b b b b", numinlets=1, numoutlets=4,
                  outlettype=["bang", "bang", "bang", "bang"],
                  patching_rect=[812, 552, 76, 20])
device.add_newobj("glitch_main_dir_expr", "expr if((($i1 + $i2) % 4) < 2\\, 1\\, -1)",
                  numinlets=2, numoutlets=1, outlettype=["int"],
                  patching_rect=[1246, 488, 224, 20])
device.add_newobj(
    "glitch_main_shift_expr",
    "expr if($f2 < 36.\\, 0\\, if($i1 < ($f2 * 1.2)\\, $i2\\, if($i1 < ($f2 * 2.1)\\, $i2 * -2\\, if($i1 < ($f2 * 3.0)\\, $i2 * 3\\, 0))))",
    numinlets=3, numoutlets=1, outlettype=["int"],
    patching_rect=[1478, 488, 480, 20],
)
device.add_newobj(
    "index_final_expr",
    "expr (((($i1 + $i2) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3))",
    numinlets=3, numoutlets=1, outlettype=["int"],
    patching_rect=[1312, 520, 338, 20],
)
device.add_newobj("step_phase_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1608, 488, 36, 20])
device.add_newobj("index_lock_dispatch", "t b b i", numinlets=1, numoutlets=3,
                  outlettype=["bang", "bang", "int"], patching_rect=[1652, 488, 54, 20])
device.add_newobj("index_locked_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1714, 488, 36, 20])
device.add_newobj("step_lock_wrap_expr",
                  "expr (((($i1 % max(1\\, $i2)) + max(1\\, $i2)) % max(1\\, $i2)))",
                  numinlets=2, numoutlets=1, outlettype=["int"],
                  patching_rect=[1758, 488, 254, 20])
device.add_newobj("step_lock_coll", "coll #0_slicer_locks @embed 1",
                  numinlets=2, numoutlets=2, outlettype=["", ""],
                  patching_rect=[2020, 488, 154, 20])
device.add_newobj(
    "step_lock_route",
    "route lock unlock clear dirlock dirunlock dirclear pitchlock pitchunlock pitchclear gatelock gateunlock gateclear ratchetlock ratchetunlock ratchetclear",
    numinlets=1, numoutlets=16,
    outlettype=["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    patching_rect=[2020, 520, 820, 20],
)
device.add_newobj("step_lock_remove", "prepend remove", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2020, 552, 102, 20])
add_message(device, "step_lock_clear_msg", "clear", [2166, 552, 38, 18])
device.add_newobj("step_dir_lock_coll", "coll #0_slicer_dir_locks @embed 1",
                  numinlets=2, numoutlets=2, outlettype=["", ""],
                  patching_rect=[2212, 552, 174, 20])
device.add_newobj("step_dir_lock_remove", "prepend remove", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2394, 552, 102, 20])
add_message(device, "step_dir_lock_clear_msg", "clear", [2504, 552, 38, 18])
device.add_newobj("step_pitch_lock_coll", "coll #0_slicer_pitch_locks @embed 1",
                  numinlets=2, numoutlets=2, outlettype=["", ""],
                  patching_rect=[2548, 552, 190, 20])
device.add_newobj("step_pitch_lock_remove", "prepend remove", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2746, 552, 102, 20])
add_message(device, "step_pitch_lock_clear_msg", "clear", [2856, 552, 38, 18])
device.add_newobj("step_gate_lock_coll", "coll #0_slicer_gate_locks @embed 1",
                  numinlets=2, numoutlets=2, outlettype=["", ""],
                  patching_rect=[2902, 552, 182, 20])
device.add_newobj("step_gate_lock_remove", "prepend remove", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[3092, 552, 102, 20])
add_message(device, "step_gate_lock_clear_msg", "clear", [3202, 552, 38, 18])
device.add_newobj("step_ratchet_lock_coll", "coll #0_slicer_ratchet_locks @embed 1",
                  numinlets=2, numoutlets=2, outlettype=["", ""],
                  patching_rect=[3248, 552, 198, 20])
device.add_newobj("step_ratchet_lock_remove", "prepend remove", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[3454, 552, 102, 20])
add_message(device, "step_ratchet_lock_clear_msg", "clear", [3564, 552, 38, 18])
device.add_newobj("pattern_lock_refresh_bang", "t b", numinlets=1, numoutlets=1,
                  outlettype=["bang"], patching_rect=[2212, 488, 30, 20])
device.add_newobj("pattern_lock_refresh_delay", "delay 1", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[2250, 488, 54, 20])
device.add_newobj("pattern_lock_refresh_trig", "t b b b b b b", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang"], patching_rect=[2312, 488, 108, 20])
device.add_newobj("pattern_lock_uzi", "uzi 32", numinlets=2, numoutlets=3,
                  outlettype=["bang", "int", "bang"], patching_rect=[2362, 488, 46, 20])
device.add_newobj("pattern_lock_step_expr", "expr $i1 - 1", numinlets=1, numoutlets=1,
                  outlettype=["int"], patching_rect=[2416, 488, 84, 20])
device.add_newobj("pattern_lock_step_limit_expr",
                  "expr if($i1 < max(1\\, $i2)\\, $i1\\, -1)",
                  numinlets=2, numoutlets=1, outlettype=["int"],
                  patching_rect=[2508, 488, 206, 20])
device.add_newobj("pattern_lock_skip_sel", "sel -1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[2722, 488, 42, 20])
device.add_newobj("pattern_lock_query_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[2772, 488, 38, 20])
device.add_newobj("pattern_lock_step_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2818, 488, 36, 20])
device.add_newobj("pattern_lock_value_trig", "t b i", numinlets=1, numoutlets=2,
                  outlettype=["bang", "int"], patching_rect=[2862, 488, 38, 20])
device.add_newobj("pattern_lock_pack", "pack i i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[2908, 488, 50, 20])
device.add_newobj("pattern_lock_set", "prepend set", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2966, 488, 82, 20])
add_message(device, "pattern_lock_sync_clear_msg", "clear", [3056, 488, 38, 18])
device.add_newobj("pattern_dir_query_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[2772, 520, 38, 20])
device.add_newobj("pattern_dir_step_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2818, 520, 36, 20])
device.add_newobj("pattern_dir_value_trig", "t b i", numinlets=1, numoutlets=2,
                  outlettype=["bang", "int"], patching_rect=[2862, 520, 38, 20])
device.add_newobj("pattern_dir_pack", "pack i i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[2908, 520, 50, 20])
device.add_newobj("pattern_dir_set", "prepend dirset", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2966, 520, 98, 20])
add_message(device, "pattern_dir_sync_clear_msg", "dirclear", [3072, 520, 52, 18])
device.add_newobj("pattern_pitch_query_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[2772, 552, 38, 20])
device.add_newobj("pattern_pitch_step_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2818, 552, 36, 20])
device.add_newobj("pattern_pitch_value_trig", "t b i", numinlets=1, numoutlets=2,
                  outlettype=["bang", "int"], patching_rect=[2862, 552, 38, 20])
device.add_newobj("pattern_pitch_pack", "pack i i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[2908, 552, 50, 20])
device.add_newobj("pattern_pitch_set", "prepend pitchset", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2966, 552, 108, 20])
add_message(device, "pattern_pitch_sync_clear_msg", "pitchclear", [3082, 552, 62, 18])
device.add_newobj("pattern_gate_query_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[2772, 584, 38, 20])
device.add_newobj("pattern_gate_step_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2818, 584, 36, 20])
device.add_newobj("pattern_gate_value_trig", "t b i", numinlets=1, numoutlets=2,
                  outlettype=["bang", "int"], patching_rect=[2862, 584, 38, 20])
device.add_newobj("pattern_gate_pack", "pack i i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[2908, 584, 50, 20])
device.add_newobj("pattern_gate_set", "prepend gateset", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2966, 584, 104, 20])
add_message(device, "pattern_gate_sync_clear_msg", "gateclear", [3078, 584, 58, 18])
device.add_newobj("pattern_ratchet_query_trig", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["int", "int"], patching_rect=[2772, 616, 38, 20])
device.add_newobj("pattern_ratchet_step_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2818, 616, 36, 20])
device.add_newobj("pattern_ratchet_value_trig", "t b i", numinlets=1, numoutlets=2,
                  outlettype=["bang", "int"], patching_rect=[2862, 616, 38, 20])
device.add_newobj("pattern_ratchet_pack", "pack i i", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[2908, 616, 50, 20])
device.add_newobj("pattern_ratchet_set", "prepend ratchetset", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[2966, 616, 122, 20])
add_message(device, "pattern_ratchet_sync_clear_msg", "ratchetclear", [3096, 616, 76, 18])
device.add_newobj("dir_alt_expr", "expr if((($i1 + $i2) % 2) == 0\\, 1.\\, -1.)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1608, 520, 228, 20])
device.add_newobj("dir_sign_expr", "expr if($i1 == 0\\, 1.\\, if($i1 == 1\\, $f2\\, -1.))",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1608, 552, 248, 20])
device.add_newobj("step_dir_lock_query_trig", "t i b", numinlets=1, numoutlets=2,
                  outlettype=["int", "bang"], patching_rect=[1864, 520, 38, 20])
add_message(device, "dir_lock_default_msg", "0", [1910, 520, 20, 18])
device.add_newobj("dir_lock_mode_store", "i 0", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[1938, 520, 36, 20])
device.add_newobj("dir_sign_final_expr",
                  "expr if($i2 == 0\\, $f1\\, if($i2 > 0\\, 1.\\, -1.))",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1982, 520, 252, 20])
device.add_newobj("step_pitch_lock_query_trig", "t i b", numinlets=1, numoutlets=2,
                  outlettype=["int", "bang"], patching_rect=[2242, 520, 38, 20])
add_message(device, "pitch_lock_default_msg", "999", [2288, 520, 30, 18])
device.add_newobj("pitch_lock_store", "i 999", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2326, 520, 42, 20])
device.add_newobj("step_gate_lock_query_trig", "t i b", numinlets=1, numoutlets=2,
                  outlettype=["int", "bang"], patching_rect=[2376, 520, 38, 20])
add_message(device, "gate_lock_default_msg", "-1", [2422, 520, 24, 18])
device.add_newobj("gate_lock_store", "i -1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2454, 520, 36, 20])
device.add_newobj("step_ratchet_lock_query_trig", "t i b", numinlets=1, numoutlets=2,
                  outlettype=["int", "bang"], patching_rect=[2498, 520, 38, 20])
add_message(device, "ratchet_lock_default_msg", "-1", [2544, 520, 24, 18])
device.add_newobj("ratchet_lock_store", "i -1", numinlets=2, numoutlets=1,
                  outlettype=["int"], patching_rect=[2576, 520, 36, 20])

device.add_newobj("jitter_norm_expr", "expr ($f1 / 999.5) - 1.",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1204, 424, 132, 20])
device.add_newobj(
    "jitter_ms_expr",
    "expr ($f1 * ($f2 / 100.) * 0.45) * $f3",
    numinlets=3, numoutlets=1, outlettype=["float"],
    patching_rect=[1204, 456, 188, 20],
)
device.add_newobj(
    "slice_start_expr",
    "expr max(0.\\, $f2 + ($i1 * $f3) + $f4)",
    numinlets=4, numoutlets=1, outlettype=["float"],
    patching_rect=[760, 584, 212, 20],
)
device.add_newobj(
    "effective_slice_ms_expr",
    "expr max(8.\\, $f2 * if($i1 < ($f3 * 10.)\\, max(0.15\\, 1. - ($f3 / 120.))\\, 1.))",
    numinlets=3, numoutlets=1, outlettype=["float"],
    patching_rect=[980, 584, 304, 20],
)
device.add_newobj("launch_pos_expr", "expr if($f3 < 0.\\, max(0.\\, $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[760, 616, 248, 20])
device.add_newobj("launch_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1016, 616, 42, 20])
device.add_newobj(
    "glitch_count_expr",
    "expr if($f2 < 50.\\, 0\\, if($i1 < ($f2 * 2.2)\\, 3\\, if($i1 < ($f2 * 5.5)\\, 2\\, if($i1 < ($f2 * 9.)\\, 1\\, 0))))",
    numinlets=2, numoutlets=1, outlettype=["int"],
    patching_rect=[980, 552, 336, 20],
)
device.add_newobj("glitch_count_final_expr", "expr if($i2 < 0\\, $i1\\, $i2)",
                  numinlets=2, numoutlets=1, outlettype=["int"],
                  patching_rect=[1324, 488, 186, 20])
device.add_newobj("ratchet_gate_a_expr", "expr if($i1 >= 1\\, 1\\, 0)",
                  numinlets=1, numoutlets=1, outlettype=["int"],
                  patching_rect=[1324, 520, 148, 20])
device.add_newobj("ratchet_gate_b_expr", "expr if($i1 >= 2\\, 1\\, 0)",
                  numinlets=1, numoutlets=1, outlettype=["int"],
                  patching_rect=[1324, 552, 148, 20])
device.add_newobj("ratchet_gate_c_expr", "expr if($i1 >= 3\\, 1\\, 0)",
                  numinlets=1, numoutlets=1, outlettype=["int"],
                  patching_rect=[1324, 584, 148, 20])
device.add_newobj("ratchet_sel_a", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1480, 520, 42, 20])
device.add_newobj("ratchet_sel_b", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1480, 552, 42, 20])
device.add_newobj("ratchet_sel_c", "sel 1", numinlets=1, numoutlets=2,
                  outlettype=["bang", ""], patching_rect=[1480, 584, 42, 20])
device.add_newobj("ratchet_dir_expr", "expr if((($i1 + $i2) % 4) < 2\\, 1\\, -1)",
                  numinlets=2, numoutlets=1, outlettype=["int"],
                  patching_rect=[1324, 616, 224, 20])
device.add_newobj("ratchet_a_shift_expr", "expr $i1",
                  numinlets=1, numoutlets=1, outlettype=["int"],
                  patching_rect=[1556, 616, 76, 20])
device.add_newobj("ratchet_b_shift_expr", "expr $i1 * -2",
                  numinlets=1, numoutlets=1, outlettype=["int"],
                  patching_rect=[1556, 648, 96, 20])
device.add_newobj("ratchet_c_shift_expr", "expr $i1 * 3",
                  numinlets=1, numoutlets=1, outlettype=["int"],
                  patching_rect=[1556, 680, 88, 20])
device.add_newobj("ratchet_delay_a_expr", "expr max(12.\\, $f1 * 0.333)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1530, 520, 168, 20])
device.add_newobj("ratchet_delay_b_expr", "expr max(18.\\, $f1 * 0.666)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1530, 552, 168, 20])
device.add_newobj("ratchet_delay_c_expr", "expr max(10.\\, $f1 * 0.5)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1530, 584, 160, 20])
device.add_newobj("ratchet_delay_a", "delay 0", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[1706, 520, 56, 20])
device.add_newobj("ratchet_delay_b", "delay 0", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[1706, 552, 56, 20])
device.add_newobj("ratchet_delay_c", "delay 0", numinlets=2, numoutlets=1,
                  outlettype=["bang"], patching_rect=[1706, 584, 56, 20])
device.add_newobj("ratchet_trig_a", "t b b b b b b", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang"],
                  patching_rect=[1770, 520, 98, 20])
device.add_newobj("ratchet_trig_b", "t b b b b b b", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang"],
                  patching_rect=[1770, 552, 98, 20])
device.add_newobj("ratchet_trig_c", "t b b b b b b", numinlets=1, numoutlets=6,
                  outlettype=["bang", "bang", "bang", "bang", "bang", "bang"],
                  patching_rect=[1770, 584, 98, 20])
device.add_newobj(
    "slice_end_expr",
    "expr min($f3\\, $f1 + max(10.\\, $f2))",
    numinlets=3, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 584, 188, 20],
)
device.add_newobj(
    "ratchet_a_start_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.28))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 712, 470, 20],
)
device.add_newobj(
    "ratchet_b_start_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.52))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 744, 470, 20],
)
device.add_newobj(
    "ratchet_c_start_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.76))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 776, 470, 20],
)
device.add_newobj("ratchet_a_launch_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1292, 800, 276, 20])
device.add_newobj("ratchet_b_launch_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1576, 800, 276, 20])
device.add_newobj("ratchet_c_launch_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1860, 800, 276, 20])
device.add_newobj("ratchet_a_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 712, 42, 20])
device.add_newobj("ratchet_b_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 744, 42, 20])
device.add_newobj("ratchet_c_store", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 776, 42, 20])
device.add_newobj(
    "ratchet_a_start_2_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.28))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 808, 470, 20],
)
device.add_newobj(
    "ratchet_b_start_2_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.52))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 840, 470, 20],
)
device.add_newobj(
    "ratchet_c_start_2_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.76))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 872, 470, 20],
)
device.add_newobj("ratchet_a_launch_2_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1292, 896, 276, 20])
device.add_newobj("ratchet_b_launch_2_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1576, 896, 276, 20])
device.add_newobj("ratchet_c_launch_2_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1860, 896, 276, 20])
device.add_newobj("ratchet_a_store_2", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 808, 42, 20])
device.add_newobj("ratchet_b_store_2", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 840, 42, 20])
device.add_newobj("ratchet_c_store_2", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 872, 42, 20])
device.add_newobj(
    "ratchet_a_start_3_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.28))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 904, 470, 20],
)
device.add_newobj(
    "ratchet_b_start_3_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.52))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 936, 470, 20],
)
device.add_newobj(
    "ratchet_c_start_3_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.76))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 968, 470, 20],
)
device.add_newobj("ratchet_a_launch_3_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1292, 992, 276, 20])
device.add_newobj("ratchet_b_launch_3_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1576, 992, 276, 20])
device.add_newobj("ratchet_c_launch_3_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1860, 992, 276, 20])
device.add_newobj("ratchet_a_store_3", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 904, 42, 20])
device.add_newobj("ratchet_b_store_3", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 936, 42, 20])
device.add_newobj("ratchet_c_store_3", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 968, 42, 20])
device.add_newobj(
    "ratchet_a_start_4_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.28))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 1000, 470, 20],
)
device.add_newobj(
    "ratchet_b_start_4_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.52))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 1032, 470, 20],
)
device.add_newobj(
    "ratchet_c_start_4_expr",
    "expr max(0.\\, $f2 + ((((($i1 + $i5) % max(1\\, $i3)) + max(1\\, $i3)) % max(1\\, $i3)) * $f4) + max(2.\\, $f6 * 0.76))",
    numinlets=6, numoutlets=1, outlettype=["float"],
    patching_rect=[1292, 1064, 470, 20],
)
device.add_newobj("ratchet_a_launch_4_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1292, 1088, 276, 20])
device.add_newobj("ratchet_b_launch_4_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1576, 1088, 276, 20])
device.add_newobj("ratchet_c_launch_4_expr", "expr if($f3 < 0.\\, max(0.\\, $f1 + $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1860, 1088, 276, 20])
device.add_newobj("ratchet_a_store_4", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 1000, 42, 20])
device.add_newobj("ratchet_b_store_4", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 1032, 42, 20])
device.add_newobj("ratchet_c_store_4", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1770, 1064, 42, 20])

device.add_newobj("voice2_index_expr", "expr ($i1 + max(1\\, $i2)) % max(1\\, $i3)",
                  numinlets=3, numoutlets=1, outlettype=["int"],
                  patching_rect=[760, 616, 210, 20])
device.add_newobj("voice3_index_expr", "expr ($i1 + (2 * max(1\\, $i2))) % max(1\\, $i3)",
                  numinlets=3, numoutlets=1, outlettype=["int"],
                  patching_rect=[760, 648, 240, 20])
device.add_newobj("voice4_index_expr", "expr ($i1 + (3 * max(1\\, $i2))) % max(1\\, $i3)",
                  numinlets=3, numoutlets=1, outlettype=["int"],
                  patching_rect=[760, 680, 240, 20])
device.add_newobj("slice_start_2_expr", "expr max(0.\\, $f2 + ($i1 * $f3) + $f4)",
                  numinlets=4, numoutlets=1, outlettype=["float"],
                  patching_rect=[1008, 616, 212, 20])
device.add_newobj("slice_start_3_expr", "expr max(0.\\, $f2 + ($i1 * $f3) + $f4)",
                  numinlets=4, numoutlets=1, outlettype=["float"],
                  patching_rect=[1008, 648, 212, 20])
device.add_newobj("slice_start_4_expr", "expr max(0.\\, $f2 + ($i1 * $f3) + $f4)",
                  numinlets=4, numoutlets=1, outlettype=["float"],
                  patching_rect=[1008, 680, 212, 20])
device.add_newobj("slice_end_2_expr", "expr min($f3\\, $f1 + max(10.\\, $f2))",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1228, 616, 188, 20])
device.add_newobj("slice_end_3_expr", "expr min($f3\\, $f1 + max(10.\\, $f2))",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1228, 648, 188, 20])
device.add_newobj("slice_end_4_expr", "expr min($f3\\, $f1 + max(10.\\, $f2))",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1228, 680, 188, 20])
device.add_newobj("launch_pos_2_expr", "expr if($f3 < 0.\\, max(0.\\, $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1424, 616, 248, 20])
device.add_newobj("launch_pos_3_expr", "expr if($f3 < 0.\\, max(0.\\, $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1424, 648, 248, 20])
device.add_newobj("launch_pos_4_expr", "expr if($f3 < 0.\\, max(0.\\, $f2 - 1.)\\, $f1)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1424, 680, 248, 20])
device.add_newobj("launch_store_2", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1680, 616, 42, 20])
device.add_newobj("launch_store_3", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1680, 648, 42, 20])
device.add_newobj("launch_store_4", "f 0.", numinlets=2, numoutlets=1,
                  outlettype=["float"], patching_rect=[1680, 680, 42, 20])

device.add_newobj("voice1_gain_expr", "expr 1. / sqrt(max(1.\\, $f1))",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[760, 712, 180, 20])
device.add_newobj("voice2_gain_expr", "expr if($f1 >= 2.\\, 1. / sqrt(max(1.\\, $f1))\\, 0.)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[948, 712, 244, 20])
device.add_newobj("voice3_gain_expr", "expr if($f1 >= 3.\\, 1. / sqrt(max(1.\\, $f1))\\, 0.)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1200, 712, 244, 20])
device.add_newobj("voice4_gain_expr", "expr if($f1 >= 4.\\, 1. / sqrt(max(1.\\, $f1))\\, 0.)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1452, 712, 244, 20])

device.add_newobj(
    "pitch_rand_expr",
    (
        "expr (if($f3 > 0. && (($f1 / 999.5) - 1.) < 0.\\, "
        "((($f1 / 999.5) - 1.) * (1. - ($f3 / 100.)))\\, "
        "if($f3 < 0. && (($f1 / 999.5) - 1.) > 0.\\, "
        "((($f1 / 999.5) - 1.) * (1. + ($f3 / 100.)))\\, "
        "(($f1 / 999.5) - 1.)))) * $f2"
    ),
    numinlets=3, numoutlets=1, outlettype=["float"],
    patching_rect=[1204, 520, 404, 20],
)
device.add_newobj(
    "arp_index_expr",
    "expr abs((($i1 * (($i2 % 5) + 2)) + ($i2 * 11) + (($i1 % 3) * 7)) % 8)",
    numinlets=2, numoutlets=1, outlettype=["int"],
    patching_rect=[1204, 552, 288, 20],
)
device.add_newobj("arp_sign_expr", "expr if((($i1 + $i2) % 4) < 2\\, 1.\\, -1.)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1500, 552, 204, 20])
device.add_newobj(
    "arp_semitone_expr",
    (
        "expr if($i1 == 0\\, 0.\\, if($i1 == 1\\, 3.\\, if($i1 == 2\\, 7.\\, "
        "if($i1 == 3\\, 10.\\, if($i1 == 4\\, 12.\\, if($i1 == 5\\, 15.\\, "
        "if($i1 == 6\\, 19.\\, 24.)))))))"
    ),
    numinlets=1, numoutlets=1, outlettype=["float"],
    patching_rect=[1204, 584, 388, 20],
)
device.add_newobj("arp_amount_expr", "expr $f1 * $f2 * ($f3 / 100.)",
                  numinlets=3, numoutlets=1, outlettype=["float"],
                  patching_rect=[1204, 616, 186, 20])
device.add_newobj("pitch_total_expr", "expr $f1 + $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1398, 616, 100, 20])
device.add_newobj("pitch_lock_final_expr",
                  "expr if(abs($f2) > 99.\\, $f1\\, $f2)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1506, 616, 176, 20])
device.add_newobj("ratio_expr", "expr pow(2.\\, (($f2 - 36. + $f1) / 12.))",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1690, 616, 196, 20])
device.add_newobj("pitch_env_mul_expr", "expr pow(2.\\, ($f1 / 12.))",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1204, 648, 164, 20])
device.add_newobj("pitch_env_start_expr", "expr $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1374, 648, 120, 20])
device.add_newobj("speed_env_pack", "pack f f f", numinlets=3, numoutlets=1,
                  outlettype=[""], patching_rect=[1204, 680, 70, 20])
add_message(device, "speed_env_msg", "$1, $2 $3", [1282, 680, 82, 18])
device.add_newobj("ratio_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[1372, 680, 40, 20])
device.add_newobj("voice_detune_width_expr", "expr max(0.\\, (($f1 - 1.) / 7.) * 0.36)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1418, 680, 240, 20])
device.add_newobj(
    "voice1_detune_expr",
    "expr if($f1 <= 1.\\, 0.\\, if($f1 <= 2.\\, -0.5 * $f2\\, if($f1 <= 3.\\, -0.82 * $f2\\, -1. * $f2)))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1664, 648, 360, 20],
)
device.add_newobj(
    "voice2_detune_expr",
    "expr if($f1 <= 1.\\, 0.\\, if($f1 <= 2.\\, 0.5 * $f2\\, if($f1 <= 3.\\, 0.\\, -0.33 * $f2)))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1664, 680, 354, 20],
)
device.add_newobj(
    "voice3_detune_expr",
    "expr if($f1 <= 2.\\, 0.\\, if($f1 <= 3.\\, 0.82 * $f2\\, 0.33 * $f2))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1664, 712, 294, 20],
)
device.add_newobj("voice4_detune_expr", "expr if($f1 <= 3.\\, 0.\\, 1. * $f2)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1664, 744, 218, 20])
device.add_newobj("voice1_detune_ratio_expr", "expr pow(2.\\, ($f1 / 12.))",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 648, 184, 20])
device.add_newobj("voice2_detune_ratio_expr", "expr pow(2.\\, ($f1 / 12.))",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 680, 184, 20])
device.add_newobj("voice3_detune_ratio_expr", "expr pow(2.\\, ($f1 / 12.))",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 712, 184, 20])
device.add_newobj("voice4_detune_ratio_expr", "expr pow(2.\\, ($f1 / 12.))",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 744, 184, 20])
device.add_newobj("voice1_rate_dir_expr", "expr $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 776, 116, 20])
device.add_newobj("voice2_rate_dir_expr", "expr $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 808, 116, 20])
device.add_newobj("voice3_rate_dir_expr", "expr $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 840, 116, 20])
device.add_newobj("voice4_rate_dir_expr", "expr $f1 * $f2",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1890, 872, 116, 20])
device.add_newobj("voice_rate_mul_1", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[2082, 648, 60, 20])
device.add_newobj("voice_rate_mul_2", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[2082, 680, 60, 20])
device.add_newobj("voice_rate_mul_3", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[2082, 712, 60, 20])
device.add_newobj("voice_rate_mul_4", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[2082, 744, 60, 20])

device.add_newobj("env_decay_expr", "expr max(12.\\, $f1 * 0.88)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1204, 712, 164, 20])
add_message(device, "env_msg", "0, 1 3, 0 $1 4", [1374, 712, 98, 18])
device.add_newobj("env_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[1478, 712, 40, 20])

device.add_newobj("chop_gate_expr", "expr if($f2 <= 0.01\\, 1.\\, if($i1 < ($f2 * 10.)\\, 0.\\, 1.))",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1204, 744, 290, 20])
device.add_newobj("chop_gate_final_expr", "expr if($f2 < 0.\\, $f1\\, $f2)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1502, 744, 188, 20])
device.add_newobj("chop_pack", "pack f 4", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[1204, 776, 62, 20])
device.add_newobj("chop_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[1272, 776, 40, 20])
device.add_newobj("chop_init", "loadmess 1.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[1320, 776, 74, 20])

device.add_newobj("groove", "groove~ slicebuf 1", numinlets=4, numoutlets=3,
                  outlettype=["signal", "", ""], patching_rect=[760, 776, 112, 20])
device.add_newobj("groove_2", "groove~ slicebuf 1", numinlets=4, numoutlets=3,
                  outlettype=["signal", "", ""], patching_rect=[760, 808, 112, 20])
device.add_newobj("groove_3", "groove~ slicebuf 1", numinlets=4, numoutlets=3,
                  outlettype=["signal", "", ""], patching_rect=[760, 840, 112, 20])
device.add_newobj("groove_4", "groove~ slicebuf 1", numinlets=4, numoutlets=3,
                  outlettype=["signal", "", ""], patching_rect=[760, 872, 112, 20])
device.add_newobj("amp_mul", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[880, 776, 48, 20])
device.add_newobj("amp_mul_2", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[880, 808, 48, 20])
device.add_newobj("amp_mul_3", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[880, 840, 48, 20])
device.add_newobj("amp_mul_4", "*~ 0.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[880, 872, 48, 20])
device.add_newobj("voice_gain_1", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[936, 776, 56, 20])
device.add_newobj("voice_gain_2", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[936, 808, 56, 20])
device.add_newobj("voice_gain_3", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[936, 840, 56, 20])
device.add_newobj("voice_gain_4", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[936, 872, 56, 20])
device.add_newobj("voice_width_expr", "expr max(0.\\, (($f1 - 1.) / 7.) * 0.92)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1000, 744, 214, 20])
device.add_newobj(
    "voice1_pos_expr",
    "expr if($f1 <= 1.\\, 0.\\, if($f1 <= 2.\\, -0.46 * $f2\\, if($f1 <= 3.\\, -0.74 * $f2\\, -0.92 * $f2)))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1222, 744, 360, 20],
)
device.add_newobj(
    "voice2_pos_expr",
    "expr if($f1 <= 1.\\, 0.\\, if($f1 <= 2.\\, 0.46 * $f2\\, if($f1 <= 3.\\, 0.\\, -0.30 * $f2)))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1222, 776, 348, 20],
)
device.add_newobj(
    "voice3_pos_expr",
    "expr if($f1 <= 2.\\, 0.\\, if($f1 <= 3.\\, 0.74 * $f2\\, 0.30 * $f2))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[1222, 808, 282, 20],
)
device.add_newobj("voice4_pos_expr", "expr if($f1 <= 3.\\, 0.\\, 0.92 * $f2)",
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[1222, 840, 216, 20])
device.add_newobj("voice1_l_gain_expr", "expr cos(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1590, 744, 172, 20])
device.add_newobj("voice1_r_gain_expr", "expr sin(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1768, 744, 172, 20])
device.add_newobj("voice2_l_gain_expr", "expr cos(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1590, 776, 172, 20])
device.add_newobj("voice2_r_gain_expr", "expr sin(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1768, 776, 172, 20])
device.add_newobj("voice3_l_gain_expr", "expr cos(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1590, 808, 172, 20])
device.add_newobj("voice3_r_gain_expr", "expr sin(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1768, 808, 172, 20])
device.add_newobj("voice4_l_gain_expr", "expr cos(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1590, 840, 172, 20])
device.add_newobj("voice4_r_gain_expr", "expr sin(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1768, 840, 172, 20])
device.add_newobj("voice1_l_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 776, 56, 20])
device.add_newobj("voice1_r_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1062, 776, 56, 20])
device.add_newobj("voice2_l_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 808, 56, 20])
device.add_newobj("voice2_r_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1062, 808, 56, 20])
device.add_newobj("voice3_l_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 840, 56, 20])
device.add_newobj("voice3_r_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1062, 840, 56, 20])
device.add_newobj("voice4_l_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 872, 56, 20])
device.add_newobj("voice4_r_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1062, 872, 56, 20])
device.add_newobj("voice_sum_a", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 800, 38, 20])
device.add_newobj("voice_sum_b", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 848, 38, 20])
device.add_newobj("voice_sum", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1046, 824, 38, 20])
device.add_newobj("step_gate_mul", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1090, 824, 58, 20])
device.add_newobj("voice_sum_l_a", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1126, 800, 38, 20])
device.add_newobj("voice_sum_l_b", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1126, 848, 38, 20])
device.add_newobj("voice_sum_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1172, 824, 38, 20])
device.add_newobj("voice_sum_r_a", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1220, 800, 38, 20])
device.add_newobj("voice_sum_r_b", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1220, 848, 38, 20])
device.add_newobj("voice_sum_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1266, 824, 38, 20])
device.add_newobj("step_gate_mul_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1312, 808, 58, 20])
device.add_newobj("step_gate_mul_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1378, 808, 58, 20])

device.add_newobj(
    "pan_amount_expr",
    (
        "expr max(-0.92\\, min(0.92\\, (($f2 / 100.) * 0.72) + "
        "((($f1 / 999.5) - 1.) * (0.25 + (0.75 * (1. - abs($f2 / 100.)))))))"
    ),
                  numinlets=2, numoutlets=1, outlettype=["float"],
                  patching_rect=[760, 648, 388, 20],
)
device.add_newobj("pan_l_expr", "expr cos(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1156, 648, 172, 20])
device.add_newobj("pan_r_expr", "expr sin(($f1 + 1.) * 0.78539816339)",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[1156, 680, 172, 20])
device.add_newobj("pan_l_pack", "pack f 12", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[1266, 648, 62, 20])
device.add_newobj("pan_r_pack", "pack f 12", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[1266, 680, 62, 20])
device.add_newobj("pan_l_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[1334, 648, 40, 20])
device.add_newobj("pan_r_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[1334, 680, 40, 20])
device.add_newobj("pan_init_l", "loadmess 1.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[1382, 648, 74, 20])
device.add_newobj("pan_init_r", "loadmess 1.", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[1382, 680, 74, 20])
device.add_newobj("pan_mul_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1000, 616, 58, 20])
device.add_newobj("pan_mul_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[1066, 616, 58, 20])

lp_boxes, lp_lines = lowpass_filter("tone")
device.add_dsp(lp_boxes, lp_lines)
device.add_newobj("filter_pack", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[1128, 616, 60, 20])
device.add_newobj("filter_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[1194, 616, 40, 20])
device.add_newobj("res_load", "loadmess 0.2", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[1240, 616, 74, 20])

device.add_newobj("drive_scale", "scale 0. 100. 1. 4.", numinlets=6, numoutlets=1,
                  outlettype=["float"], patching_rect=[760, 784, 132, 20])
device.add_newobj("drive_pack", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[898, 784, 60, 20])
device.add_newobj("drive_line", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[964, 784, 40, 20])
device.add_newobj("predrive_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[760, 816, 48, 20])
device.add_newobj("predrive_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[814, 816, 48, 20])

sat_boxes, sat_lines = saturation("sat", "tanh")
device.add_dsp(sat_boxes, sat_lines)

mix_boxes, mix_lines = dry_wet_mix(
    "mix",
    wet_source_l=("sat_l", 0), wet_source_r=("sat_r", 0),
    dry_source_l=("pan_mul_l", 0), dry_source_r=("pan_mul_r", 0),
)
device.add_dsp(mix_boxes, mix_lines)


# =========================================================================
# Display helpers
# =========================================================================

device.add_newobj("pos_from_js", "scale 0. 1. 0. 100.", numinlets=6, numoutlets=1,
                  outlettype=["float"], patching_rect=[520, 280, 138, 20])
device.add_newobj("display_pair", "pak f f", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[520, 312, 60, 20])
device.add_newobj(
    "display_start_expr",
    "expr if($f2 <= 0.\\, 0.\\, max(0.\\, min(1.\\, $f1 / $f2)))",
    numinlets=2, numoutlets=1, outlettype=["float"],
    patching_rect=[588, 312, 182, 20],
)
device.add_newobj(
    "display_end_expr",
    "expr if($f3 <= 0.\\, 1.\\, max(0.\\, min(1.\\, ($f1 + $f2) / $f3)))",
    numinlets=3, numoutlets=1, outlettype=["float"],
    patching_rect=[520, 344, 232, 20],
)
device.add_newobj("playhead_pack", "pak f f i i f", numinlets=5, numoutlets=1,
                  outlettype=[""], patching_rect=[520, 376, 88, 20])
device.add_newobj(
    "playhead_expr",
    "expr if($f5 <= 0.\\, 0.\\, max(0.\\, min(1.\\, ($f1 + (($i3 / max(1\\, $i4)) * $f2)) / $f5)))",
    numinlets=5, numoutlets=1, outlettype=["float"],
    patching_rect=[614, 376, 336, 20],
)


# =========================================================================
# Wiring
# =========================================================================

# Initialization and source loading
device.add_line("loadbang", 0, "transport", 0)
device.add_line("loadbang", 0, "sample_ms_store", 0)
device.add_line("loadbang", 0, "div_store", 0)
device.add_line("loadbang", 0, "slices_store", 0)
device.add_line("loadbang", 0, "steps_store", 0)
device.add_line("loadbang", 0, "pattern_lock_refresh_bang", 0)
device.add_line("loadbang", 0, "distance_store", 0)
device.add_line("loadbang", 0, "mode_store", 0)
device.add_line("loadbang", 0, "seed_trig", 0)
for control_id in [
    "position_dial", "region_dial", "slices_dial", "steps_dial", "distance_dial",
    "jump_dial", "chop_dial", "glitch_dial", "jitter_dial", "pitch_dial",
    "pitch_env_dial", "decay_dial", "pan_dial", "poly_dial", "spread_dial",
    "bias_dial", "arp_dial", "free_rate_dial", "wander_dial",
    "filter_dial", "drive_dial", "dir_menu",
    "mix_dial", "mode_tab", "rate_tab", "sync_btn",
]:
    device.add_line("loadbang", 0, control_id, 0)
device.add_line("reroll_btn", 0, "reroll_sel", 0)
device.add_line("pattern_seed_btn", 0, "pattern_seed_sel", 0)
device.add_line("pitch_seed_btn", 0, "pitch_seed_sel", 0)
device.add_line("chop_seed_btn", 0, "chop_seed_sel", 0)
device.add_line("glitch_seed_btn", 0, "glitch_seed_sel", 0)
device.add_line("reroll_sel", 0, "seed_trig", 0)
device.add_line("pattern_seed_sel", 0, "pattern_seed_rand", 0)
device.add_line("pitch_seed_sel", 0, "pitch_seed_rand", 0)
device.add_line("chop_seed_sel", 0, "chop_seed_rand", 0)
device.add_line("glitch_seed_sel", 0, "glitch_seed_rand", 0)
device.add_line("seed_trig", 3, "pattern_seed_rand", 0)
device.add_line("seed_trig", 2, "chop_seed_rand", 0)
device.add_line("seed_trig", 1, "glitch_seed_rand", 0)
device.add_line("seed_trig", 0, "pitch_seed_rand", 0)
device.add_line("pattern_seed_rand", 0, "pattern_seed_store", 0)
device.add_line("chop_seed_rand", 0, "chop_seed_store", 0)
device.add_line("glitch_seed_rand", 0, "glitch_seed_store", 0)
device.add_line("pitch_seed_rand", 0, "pitch_seed_store", 0)

device.add_line("sample_drop", 0, "drop_trig", 0)
device.add_line("drop_trig", 1, "drop_prep", 0)
device.add_line("drop_prep", 0, "sample_buf", 0)
device.add_line("drop_trig", 0, "drop_wait", 0)
if HAS_DEMO_SAMPLE:
    device.add_line("demo_btn", 0, "demo_sel", 0)
    device.add_line("demo_sel", 0, "demo_read_msg", 0)
    device.add_line("demo_read_msg", 0, "sample_buf", 0)
    device.add_line("demo_sel", 0, "drop_wait", 0)
device.add_line("drop_wait", 0, "sample_info", 0)
device.add_line("drop_wait", 0, "loaded_msg", 0)
device.add_line("loaded_msg", 0, "slice_surface", 0)
device.add_line("drop_wait", 0, "loop_msg", 0)
device.add_line("loop_msg", 0, "groove", 0)
device.add_line("loop_msg", 0, "groove_2", 0)
device.add_line("loop_msg", 0, "groove_3", 0)
device.add_line("loop_msg", 0, "groove_4", 0)
device.add_line("sample_info", 6, "sample_ms_store", 0)

# MIDI gate and tempo
device.add_line("notein", 0, "note_store", 0)
device.add_line("notein", 1, "vel_gt", 0)
device.add_line("vel_gt", 0, "metro", 0)
device.add_line("vel_gt", 0, "gate_sel", 0)
device.add_line("gate_sel", 0, "step_trig", 0)
device.add_line("gate_sel", 1, "stop_msg", 0)
device.add_line("stop_msg", 0, "groove", 0)
device.add_line("stop_msg", 0, "groove_2", 0)
device.add_line("stop_msg", 0, "groove_3", 0)
device.add_line("stop_msg", 0, "groove_4", 0)
device.add_line("stop_msg", 0, "ratchet_delay_a", 0)
device.add_line("stop_msg", 0, "ratchet_delay_b", 0)
device.add_line("stop_msg", 0, "ratchet_delay_c", 0)

device.add_line("transport", 4, "bpm_store", 0)
device.add_line("bpm_store", 0, "step_ms_pair", 0)
device.add_line("rate_tab", 0, "rate_sel", 0)
device.add_line("rate_sel", 0, "div_q", 0)
device.add_line("rate_sel", 1, "div_8", 0)
device.add_line("rate_sel", 2, "div_16", 0)
device.add_line("rate_sel", 3, "div_32", 0)
for div_id in ["div_q", "div_8", "div_16", "div_32"]:
    device.add_line(div_id, 0, "div_store", 0)
device.add_line("div_store", 0, "step_ms_pair", 1)
device.add_line("step_ms_pair", 0, "step_ms_expr", 0)
device.add_line("sync_btn", 0, "step_interval_pack", 0)
device.add_line("step_ms_expr", 0, "step_interval_pack", 1)
device.add_line("free_rate_dial", 0, "step_interval_pack", 2)
device.add_line("step_interval_pack", 0, "step_interval_expr", 0)
device.add_line("step_interval_expr", 0, "metro", 1)

# Core control broadcasts
device.add_line("mode_tab", 0, "mode_store", 0)
device.add_line("mode_store", 0, "index_expr", 3)
device.add_line("mode_store", 0, "pattern_lane", 3)
device.add_line("slices_dial", 0, "slices_store", 0)
device.add_line("slices_store", 0, "slice_ms_pair", 1)
device.add_line("slices_store", 0, "index_expr", 2)
device.add_line("slices_store", 0, "slice_surface", 4)
device.add_line("slices_store", 0, "playhead_pack", 3)
device.add_line("slices_store", 0, "pattern_lane", 1)
device.add_line("steps_dial", 0, "steps_store", 0)
device.add_line("steps_store", 0, "step_phase_expr", 1)
device.add_line("steps_store", 0, "pattern_lane", 0)
device.add_line("steps_store", 0, "pattern_lock_refresh_bang", 0)
device.add_line("distance_dial", 0, "distance_store", 0)
device.add_line("distance_store", 0, "index_expr", 1)
device.add_line("distance_store", 0, "pattern_lane", 2)
device.add_line("pattern_seed_store", 0, "index_expr", 5)
device.add_line("pattern_seed_store", 0, "pattern_lane", 5)
device.add_line("jump_dial", 0, "index_expr", 6)
device.add_line("jump_dial", 0, "pattern_lane", 4)
device.add_line("spread_dial", 0, "voice2_index_expr", 1)
device.add_line("spread_dial", 0, "voice3_index_expr", 1)
device.add_line("spread_dial", 0, "voice4_index_expr", 1)
device.add_line("spread_dial", 0, "voice_width_expr", 0)
device.add_line("spread_dial", 0, "voice_detune_width_expr", 0)
device.add_line("poly_dial", 0, "voice1_gain_expr", 0)
device.add_line("poly_dial", 0, "voice2_gain_expr", 0)
device.add_line("poly_dial", 0, "voice3_gain_expr", 0)
device.add_line("poly_dial", 0, "voice4_gain_expr", 0)
device.add_line("poly_dial", 0, "voice1_pos_expr", 0)
device.add_line("poly_dial", 0, "voice2_pos_expr", 0)
device.add_line("poly_dial", 0, "voice3_pos_expr", 0)
device.add_line("poly_dial", 0, "voice4_pos_expr", 0)
device.add_line("poly_dial", 0, "voice1_detune_expr", 0)
device.add_line("poly_dial", 0, "voice2_detune_expr", 0)
device.add_line("poly_dial", 0, "voice3_detune_expr", 0)
device.add_line("poly_dial", 0, "voice4_detune_expr", 0)
device.add_line("voice_width_expr", 0, "voice1_pos_expr", 1)
device.add_line("voice_width_expr", 0, "voice2_pos_expr", 1)
device.add_line("voice_width_expr", 0, "voice3_pos_expr", 1)
device.add_line("voice_width_expr", 0, "voice4_pos_expr", 1)
device.add_line("voice_detune_width_expr", 0, "voice1_detune_expr", 1)
device.add_line("voice_detune_width_expr", 0, "voice2_detune_expr", 1)
device.add_line("voice_detune_width_expr", 0, "voice3_detune_expr", 1)
device.add_line("voice_detune_width_expr", 0, "voice4_detune_expr", 1)
device.add_line("voice1_pos_expr", 0, "voice1_l_gain_expr", 0)
device.add_line("voice1_pos_expr", 0, "voice1_r_gain_expr", 0)
device.add_line("voice2_pos_expr", 0, "voice2_l_gain_expr", 0)
device.add_line("voice2_pos_expr", 0, "voice2_r_gain_expr", 0)
device.add_line("voice3_pos_expr", 0, "voice3_l_gain_expr", 0)
device.add_line("voice3_pos_expr", 0, "voice3_r_gain_expr", 0)
device.add_line("voice4_pos_expr", 0, "voice4_l_gain_expr", 0)
device.add_line("voice4_pos_expr", 0, "voice4_r_gain_expr", 0)
device.add_line("voice1_detune_expr", 0, "voice1_detune_ratio_expr", 0)
device.add_line("voice2_detune_expr", 0, "voice2_detune_ratio_expr", 0)
device.add_line("voice3_detune_expr", 0, "voice3_detune_ratio_expr", 0)
device.add_line("voice4_detune_expr", 0, "voice4_detune_ratio_expr", 0)

# Region math and display state
device.add_line("sample_ms_store", 0, "region_ms_pair", 0)
device.add_line("region_dial", 0, "region_ms_pair", 1)
device.add_line("region_ms_pair", 0, "region_ms_expr", 0)
device.add_line("region_ms_expr", 0, "slice_ms_pair", 0)

device.add_line("sample_ms_store", 0, "region_start_trip", 0)
device.add_line("region_dial", 0, "region_start_trip", 1)
device.add_line("position_dial", 0, "region_start_trip", 2)
device.add_line("region_start_trip", 0, "region_start_expr", 0)
device.add_line("step_phase_expr", 0, "scan_seq_expr", 0)
device.add_line("steps_store", 0, "scan_seq_expr", 1)
device.add_line("step_phase_expr", 0, "scan_pat_expr", 0)
device.add_line("pattern_seed_store", 0, "scan_pat_expr", 1)
device.add_line("rand_slice", 0, "scan_rand_norm_expr", 0)
device.add_line("scan_seq_expr", 0, "scan_jump_expr", 0)
device.add_line("jump_dial", 0, "scan_jump_expr", 1)
device.add_line("scan_rand_norm_expr", 0, "scan_jump_expr", 2)
device.add_line("mode_store", 0, "scan_mode_expr", 0)
device.add_line("scan_seq_expr", 0, "scan_mode_expr", 1)
device.add_line("scan_rand_norm_expr", 0, "scan_mode_expr", 2)
device.add_line("scan_pat_expr", 0, "scan_mode_expr", 3)
device.add_line("scan_jump_expr", 0, "scan_mode_expr", 4)
device.add_line("sample_ms_store", 0, "scan_range_expr", 0)
device.add_line("region_ms_expr", 0, "scan_range_expr", 1)
device.add_line("wander_dial", 0, "scan_range_expr", 2)
device.add_line("scan_mode_expr", 0, "scan_offset_expr", 0)
device.add_line("scan_range_expr", 0, "scan_offset_expr", 1)
device.add_line("region_start_expr", 0, "region_start_final_expr", 0)
device.add_line("sample_ms_store", 0, "region_start_final_expr", 1)
device.add_line("region_ms_expr", 0, "region_start_final_expr", 2)
device.add_line("scan_offset_expr", 0, "region_start_final_expr", 3)

device.add_line("slice_ms_pair", 0, "slice_ms_expr", 0)

device.add_line("slice_surface", 0, "pos_from_js", 0)
device.add_line("pos_from_js", 0, "position_dial", 0)
device.add_line("region_start_final_expr", 0, "display_pair", 0)
device.add_line("sample_ms_store", 0, "display_pair", 1)
device.add_line("display_pair", 0, "display_start_expr", 0)
device.add_line("region_start_final_expr", 0, "display_end_expr", 0)
device.add_line("region_ms_expr", 0, "display_end_expr", 1)
device.add_line("sample_ms_store", 0, "display_end_expr", 2)
device.add_line("display_start_expr", 0, "slice_surface", 1)
device.add_line("display_end_expr", 0, "slice_surface", 2)
device.add_line("region_start_final_expr", 0, "playhead_pack", 0)
device.add_line("region_ms_expr", 0, "playhead_pack", 1)
device.add_line("playhead_pack", 0, "playhead_expr", 0)
device.add_line("playhead_expr", 0, "slice_surface", 3)

# Step generation
device.add_line("metro", 0, "step_trig", 0)
device.add_line("step_trig", 6, "rand_slice", 0)
device.add_line("step_trig", 5, "rand_jitter", 0)
device.add_line("step_trig", 1, "rand_pan", 0)
device.add_line("step_trig", 0, "counter", 0)

device.add_line("counter", 0, "step_phase_expr", 0)
device.add_line("step_phase_expr", 0, "step_index_trig", 0)
device.add_line("step_phase_expr", 0, "rand_pitch", 0)
device.add_line("step_phase_expr", 0, "rand_chop", 0)
device.add_line("pitch_seed_store", 0, "rand_pitch", 1)
device.add_line("chop_seed_store", 0, "rand_chop", 1)
device.add_line("glitch_seed_store", 0, "rand_glitch", 1)
device.add_line("step_phase_expr", 0, "pattern_lane", 10)
device.add_line("arp_dial", 0, "pattern_lane", 11)
device.add_line("pitch_seed_store", 0, "pattern_lane", 12)
device.add_line("dir_menu", 0, "pattern_lane", 13)
device.add_line("chop_dial", 0, "pattern_lane", 6)
device.add_line("chop_seed_store", 0, "pattern_lane", 7)
device.add_line("glitch_dial", 0, "pattern_lane", 8)
device.add_line("glitch_seed_store", 0, "pattern_lane", 9)
device.add_line("pattern_lane", 0, "step_lock_route", 0)
device.add_line("step_lock_route", 0, "step_lock_coll", 0)
device.add_line("step_lock_route", 1, "step_lock_remove", 0)
device.add_line("step_lock_remove", 0, "step_lock_coll", 0)
device.add_line("step_lock_route", 2, "step_lock_clear_msg", 0)
device.add_line("step_lock_clear_msg", 0, "step_lock_coll", 0)
device.add_line("step_lock_route", 3, "step_dir_lock_coll", 0)
device.add_line("step_lock_route", 4, "step_dir_lock_remove", 0)
device.add_line("step_dir_lock_remove", 0, "step_dir_lock_coll", 0)
device.add_line("step_lock_route", 5, "step_dir_lock_clear_msg", 0)
device.add_line("step_dir_lock_clear_msg", 0, "step_dir_lock_coll", 0)
device.add_line("step_lock_route", 6, "step_pitch_lock_coll", 0)
device.add_line("step_lock_route", 7, "step_pitch_lock_remove", 0)
device.add_line("step_pitch_lock_remove", 0, "step_pitch_lock_coll", 0)
device.add_line("step_lock_route", 8, "step_pitch_lock_clear_msg", 0)
device.add_line("step_pitch_lock_clear_msg", 0, "step_pitch_lock_coll", 0)
device.add_line("step_lock_route", 9, "step_gate_lock_coll", 0)
device.add_line("step_lock_route", 10, "step_gate_lock_remove", 0)
device.add_line("step_gate_lock_remove", 0, "step_gate_lock_coll", 0)
device.add_line("step_lock_route", 11, "step_gate_lock_clear_msg", 0)
device.add_line("step_gate_lock_clear_msg", 0, "step_gate_lock_coll", 0)
device.add_line("step_lock_route", 12, "step_ratchet_lock_coll", 0)
device.add_line("step_lock_route", 13, "step_ratchet_lock_remove", 0)
device.add_line("step_ratchet_lock_remove", 0, "step_ratchet_lock_coll", 0)
device.add_line("step_lock_route", 14, "step_ratchet_lock_clear_msg", 0)
device.add_line("step_ratchet_lock_clear_msg", 0, "step_ratchet_lock_coll", 0)
device.add_line("step_lock_route", 0, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 1, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 2, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 3, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 4, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 5, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 6, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 7, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 8, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 9, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 10, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 11, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 12, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 13, "pattern_lock_refresh_bang", 0)
device.add_line("step_lock_route", 14, "pattern_lock_refresh_bang", 0)
device.add_line("pattern_lock_refresh_bang", 0, "pattern_lock_refresh_delay", 0)
device.add_line("pattern_lock_refresh_delay", 0, "pattern_lock_refresh_trig", 0)
device.add_line("pattern_lock_refresh_trig", 5, "pattern_lock_sync_clear_msg", 0)
device.add_line("pattern_lock_refresh_trig", 4, "pattern_dir_sync_clear_msg", 0)
device.add_line("pattern_lock_refresh_trig", 3, "pattern_pitch_sync_clear_msg", 0)
device.add_line("pattern_lock_refresh_trig", 2, "pattern_gate_sync_clear_msg", 0)
device.add_line("pattern_lock_refresh_trig", 1, "pattern_ratchet_sync_clear_msg", 0)
device.add_line("pattern_lock_sync_clear_msg", 0, "pattern_lane", 14)
device.add_line("pattern_dir_sync_clear_msg", 0, "pattern_lane", 14)
device.add_line("pattern_pitch_sync_clear_msg", 0, "pattern_lane", 14)
device.add_line("pattern_gate_sync_clear_msg", 0, "pattern_lane", 14)
device.add_line("pattern_ratchet_sync_clear_msg", 0, "pattern_lane", 14)
device.add_line("pattern_lock_refresh_trig", 0, "pattern_lock_uzi", 0)
device.add_line("pattern_lock_uzi", 1, "pattern_lock_step_expr", 0)
device.add_line("pattern_lock_step_expr", 0, "pattern_lock_step_limit_expr", 0)
device.add_line("steps_store", 0, "pattern_lock_step_limit_expr", 1)
device.add_line("pattern_lock_step_limit_expr", 0, "pattern_lock_skip_sel", 0)
device.add_line("pattern_lock_skip_sel", 1, "pattern_lock_query_trig", 0)
device.add_line("pattern_lock_skip_sel", 1, "pattern_dir_query_trig", 0)
device.add_line("pattern_lock_skip_sel", 1, "pattern_pitch_query_trig", 0)
device.add_line("pattern_lock_skip_sel", 1, "pattern_gate_query_trig", 0)
device.add_line("pattern_lock_skip_sel", 1, "pattern_ratchet_query_trig", 0)
device.add_line("pattern_lock_query_trig", 1, "pattern_lock_step_store", 1)
device.add_line("pattern_lock_query_trig", 0, "step_lock_coll", 0)
device.add_line("step_lock_coll", 0, "pattern_lock_value_trig", 0)
device.add_line("pattern_lock_value_trig", 1, "pattern_lock_pack", 1)
device.add_line("pattern_lock_value_trig", 0, "pattern_lock_step_store", 0)
device.add_line("pattern_lock_step_store", 0, "pattern_lock_pack", 0)
device.add_line("pattern_lock_pack", 0, "pattern_lock_set", 0)
device.add_line("pattern_lock_set", 0, "pattern_lane", 14)
device.add_line("pattern_dir_query_trig", 1, "pattern_dir_step_store", 1)
device.add_line("pattern_dir_query_trig", 0, "step_dir_lock_coll", 0)
device.add_line("step_dir_lock_coll", 0, "pattern_dir_value_trig", 0)
device.add_line("pattern_dir_value_trig", 1, "pattern_dir_pack", 1)
device.add_line("pattern_dir_value_trig", 0, "pattern_dir_step_store", 0)
device.add_line("pattern_dir_step_store", 0, "pattern_dir_pack", 0)
device.add_line("pattern_dir_pack", 0, "pattern_dir_set", 0)
device.add_line("pattern_dir_set", 0, "pattern_lane", 14)
device.add_line("pattern_pitch_query_trig", 1, "pattern_pitch_step_store", 1)
device.add_line("pattern_pitch_query_trig", 0, "step_pitch_lock_coll", 0)
device.add_line("step_pitch_lock_coll", 0, "pattern_pitch_value_trig", 0)
device.add_line("pattern_pitch_value_trig", 1, "pattern_pitch_pack", 1)
device.add_line("pattern_pitch_value_trig", 0, "pattern_pitch_step_store", 0)
device.add_line("pattern_pitch_step_store", 0, "pattern_pitch_pack", 0)
device.add_line("pattern_pitch_pack", 0, "pattern_pitch_set", 0)
device.add_line("pattern_pitch_set", 0, "pattern_lane", 14)
device.add_line("pattern_gate_query_trig", 1, "pattern_gate_step_store", 1)
device.add_line("pattern_gate_query_trig", 0, "step_gate_lock_coll", 0)
device.add_line("step_gate_lock_coll", 0, "pattern_gate_value_trig", 0)
device.add_line("pattern_gate_value_trig", 1, "pattern_gate_pack", 1)
device.add_line("pattern_gate_value_trig", 0, "pattern_gate_step_store", 0)
device.add_line("pattern_gate_step_store", 0, "pattern_gate_pack", 0)
device.add_line("pattern_gate_pack", 0, "pattern_gate_set", 0)
device.add_line("pattern_gate_set", 0, "pattern_lane", 14)
device.add_line("pattern_ratchet_query_trig", 1, "pattern_ratchet_step_store", 1)
device.add_line("pattern_ratchet_query_trig", 0, "step_ratchet_lock_coll", 0)
device.add_line("step_ratchet_lock_coll", 0, "pattern_ratchet_value_trig", 0)
device.add_line("pattern_ratchet_value_trig", 1, "pattern_ratchet_pack", 1)
device.add_line("pattern_ratchet_value_trig", 0, "pattern_ratchet_step_store", 0)
device.add_line("pattern_ratchet_step_store", 0, "pattern_ratchet_pack", 0)
device.add_line("pattern_ratchet_pack", 0, "pattern_ratchet_set", 0)
device.add_line("pattern_ratchet_set", 0, "pattern_lane", 14)
device.add_line("step_index_trig", 0, "index_expr", 0)
device.add_line("step_index_trig", 1, "rand_glitch", 0)
device.add_line("step_index_trig", 2, "glitch_main_dir_expr", 0)
device.add_line("step_index_trig", 3, "step_phase_store", 1)
device.add_line("step_index_trig", 4, "step_dir_lock_query_trig", 0)
device.add_line("step_index_trig", 4, "step_pitch_lock_query_trig", 0)
device.add_line("step_index_trig", 4, "step_gate_lock_query_trig", 0)
device.add_line("step_index_trig", 4, "step_ratchet_lock_query_trig", 0)
device.add_line("rand_slice", 0, "index_expr", 4)
device.add_line("index_expr", 0, "index_final_expr", 0)
device.add_line("index_final_expr", 0, "index_lock_dispatch", 0)
device.add_line("index_lock_dispatch", 2, "index_locked_store", 1)
device.add_line("index_lock_dispatch", 1, "step_phase_store", 0)
device.add_line("index_lock_dispatch", 0, "index_locked_store", 0)
device.add_line("step_phase_store", 0, "step_lock_coll", 0)
device.add_line("step_lock_coll", 0, "step_lock_wrap_expr", 0)
device.add_line("slices_store", 0, "step_lock_wrap_expr", 1)
device.add_line("step_lock_wrap_expr", 0, "index_locked_store", 1)
device.add_line("index_trig", 0, "index_fire_trig", 0)
device.add_line("index_trig", 1, "slice_readout", 0)
device.add_line("index_trig", 1, "slice_start_expr", 0)
device.add_line("index_trig", 1, "voice2_index_expr", 0)
device.add_line("index_trig", 1, "voice3_index_expr", 0)
device.add_line("index_trig", 1, "voice4_index_expr", 0)
device.add_line("index_trig", 1, "playhead_pack", 2)
device.add_line("index_fire_trig", 3, "launch_store", 0)
device.add_line("index_fire_trig", 2, "launch_store_2", 0)
device.add_line("index_fire_trig", 1, "launch_store_3", 0)
device.add_line("index_fire_trig", 0, "launch_store_4", 0)

# Jitter, glitch, and slice timing
device.add_line("rand_jitter", 0, "jitter_norm_expr", 0)
device.add_line("jitter_norm_expr", 0, "jitter_ms_expr", 0)
device.add_line("jitter_dial", 0, "jitter_ms_expr", 1)
device.add_line("slice_ms_expr", 0, "jitter_ms_expr", 2)
device.add_line("region_start_final_expr", 0, "slice_start_expr", 1)
device.add_line("slice_ms_expr", 0, "slice_start_expr", 2)
device.add_line("jitter_ms_expr", 0, "slice_start_expr", 3)
device.add_line("slice_start_expr", 0, "launch_pos_expr", 0)

device.add_line("rand_glitch", 0, "effective_slice_ms_expr", 0)
device.add_line("rand_glitch", 0, "glitch_count_expr", 0)
device.add_line("rand_glitch", 0, "glitch_main_shift_expr", 0)
device.add_line("slice_ms_expr", 0, "effective_slice_ms_expr", 1)
device.add_line("glitch_dial", 0, "effective_slice_ms_expr", 2)
device.add_line("glitch_dial", 0, "glitch_count_expr", 1)
device.add_line("glitch_dial", 0, "glitch_main_shift_expr", 1)
device.add_line("glitch_count_expr", 0, "glitch_count_final_expr", 0)
device.add_line("ratchet_lock_store", 0, "glitch_count_final_expr", 1)
device.add_line("glitch_count_final_expr", 0, "ratchet_gate_a_expr", 0)
device.add_line("glitch_count_final_expr", 0, "ratchet_gate_b_expr", 0)
device.add_line("glitch_count_final_expr", 0, "ratchet_gate_c_expr", 0)
device.add_line("glitch_seed_store", 0, "glitch_main_dir_expr", 1)
device.add_line("glitch_main_dir_expr", 0, "glitch_main_shift_expr", 2)
device.add_line("glitch_main_shift_expr", 0, "index_final_expr", 1)
device.add_line("slices_store", 0, "index_final_expr", 2)
device.add_line("index_locked_store", 0, "index_trig", 0)
device.add_line("step_phase_expr", 0, "dir_alt_expr", 0)
device.add_line("pitch_seed_store", 0, "dir_alt_expr", 1)
device.add_line("dir_menu", 0, "dir_sign_expr", 0)
device.add_line("dir_alt_expr", 0, "dir_sign_expr", 1)
device.add_line("dir_sign_expr", 0, "dir_sign_final_expr", 0)
device.add_line("step_dir_lock_query_trig", 1, "dir_lock_default_msg", 0)
device.add_line("dir_lock_default_msg", 0, "dir_lock_mode_store", 1)
device.add_line("step_dir_lock_query_trig", 0, "step_dir_lock_coll", 0)
device.add_line("step_dir_lock_coll", 0, "dir_lock_mode_store", 1)
device.add_line("dir_lock_mode_store", 0, "dir_sign_final_expr", 1)
device.add_line("step_pitch_lock_query_trig", 1, "pitch_lock_default_msg", 0)
device.add_line("pitch_lock_default_msg", 0, "pitch_lock_store", 1)
device.add_line("step_pitch_lock_query_trig", 0, "step_pitch_lock_coll", 0)
device.add_line("step_pitch_lock_coll", 0, "pitch_lock_store", 1)
device.add_line("step_gate_lock_query_trig", 1, "gate_lock_default_msg", 0)
device.add_line("gate_lock_default_msg", 0, "gate_lock_store", 1)
device.add_line("step_gate_lock_query_trig", 0, "step_gate_lock_coll", 0)
device.add_line("step_gate_lock_coll", 0, "gate_lock_store", 1)
device.add_line("step_ratchet_lock_query_trig", 1, "ratchet_lock_default_msg", 0)
device.add_line("ratchet_lock_default_msg", 0, "ratchet_lock_store", 1)
device.add_line("step_ratchet_lock_query_trig", 0, "step_ratchet_lock_coll", 0)
device.add_line("step_ratchet_lock_coll", 0, "ratchet_lock_store", 1)
device.add_line("step_phase_expr", 0, "ratchet_dir_expr", 0)
device.add_line("glitch_seed_store", 0, "ratchet_dir_expr", 1)
device.add_line("ratchet_dir_expr", 0, "ratchet_a_shift_expr", 0)
device.add_line("ratchet_dir_expr", 0, "ratchet_b_shift_expr", 0)
device.add_line("ratchet_dir_expr", 0, "ratchet_c_shift_expr", 0)
device.add_line("ratchet_gate_a_expr", 0, "ratchet_sel_a", 0)
device.add_line("ratchet_gate_b_expr", 0, "ratchet_sel_b", 0)
device.add_line("ratchet_gate_c_expr", 0, "ratchet_sel_c", 0)
device.add_line("step_interval_expr", 0, "ratchet_delay_a_expr", 0)
device.add_line("step_interval_expr", 0, "ratchet_delay_b_expr", 0)
device.add_line("step_interval_expr", 0, "ratchet_delay_c_expr", 0)
device.add_line("ratchet_delay_a_expr", 0, "ratchet_delay_a", 1)
device.add_line("ratchet_delay_b_expr", 0, "ratchet_delay_b", 1)
device.add_line("ratchet_delay_c_expr", 0, "ratchet_delay_c", 1)
device.add_line("ratchet_sel_a", 0, "ratchet_delay_a", 0)
device.add_line("ratchet_sel_b", 0, "ratchet_delay_b", 0)
device.add_line("ratchet_sel_c", 0, "ratchet_delay_c", 0)
device.add_line("ratchet_delay_a", 0, "ratchet_trig_a", 0)
device.add_line("ratchet_delay_b", 0, "ratchet_trig_b", 0)
device.add_line("ratchet_delay_c", 0, "ratchet_trig_c", 0)
device.add_line("ratchet_trig_a", 5, "speed_env_msg", 0)
device.add_line("ratchet_trig_a", 4, "env_msg", 0)
device.add_line("ratchet_trig_a", 3, "ratchet_a_store", 0)
device.add_line("ratchet_trig_a", 2, "ratchet_a_store_2", 0)
device.add_line("ratchet_trig_a", 1, "ratchet_a_store_3", 0)
device.add_line("ratchet_trig_a", 0, "ratchet_a_store_4", 0)
device.add_line("ratchet_trig_b", 5, "speed_env_msg", 0)
device.add_line("ratchet_trig_b", 4, "env_msg", 0)
device.add_line("ratchet_trig_b", 3, "ratchet_b_store", 0)
device.add_line("ratchet_trig_b", 2, "ratchet_b_store_2", 0)
device.add_line("ratchet_trig_b", 1, "ratchet_b_store_3", 0)
device.add_line("ratchet_trig_b", 0, "ratchet_b_store_4", 0)
device.add_line("ratchet_trig_c", 5, "speed_env_msg", 0)
device.add_line("ratchet_trig_c", 4, "env_msg", 0)
device.add_line("ratchet_trig_c", 3, "ratchet_c_store", 0)
device.add_line("ratchet_trig_c", 2, "ratchet_c_store_2", 0)
device.add_line("ratchet_trig_c", 1, "ratchet_c_store_3", 0)
device.add_line("ratchet_trig_c", 0, "ratchet_c_store_4", 0)
device.add_line("effective_slice_ms_expr", 0, "env_decay_expr", 0)
device.add_line("env_decay_expr", 0, "env_msg", 0)
device.add_line("env_msg", 0, "env_line", 0)
device.add_line("slice_start_expr", 0, "slice_end_expr", 0)
device.add_line("effective_slice_ms_expr", 0, "slice_end_expr", 1)
device.add_line("sample_ms_store", 0, "slice_end_expr", 2)
device.add_line("slice_end_expr", 0, "launch_pos_expr", 1)
device.add_line("dir_sign_final_expr", 0, "launch_pos_expr", 2)
device.add_line("launch_pos_expr", 0, "launch_store", 1)
device.add_line("launch_store", 0, "groove", 0)
device.add_line("slice_start_expr", 0, "groove", 1)
device.add_line("slice_end_expr", 0, "groove", 2)
device.add_line("index_trig", 1, "ratchet_a_start_expr", 0)
device.add_line("index_trig", 1, "ratchet_b_start_expr", 0)
device.add_line("index_trig", 1, "ratchet_c_start_expr", 0)
device.add_line("region_start_final_expr", 0, "ratchet_a_start_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_b_start_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_c_start_expr", 1)
device.add_line("slices_store", 0, "ratchet_a_start_expr", 2)
device.add_line("slices_store", 0, "ratchet_b_start_expr", 2)
device.add_line("slices_store", 0, "ratchet_c_start_expr", 2)
device.add_line("slice_ms_expr", 0, "ratchet_a_start_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_b_start_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_c_start_expr", 3)
device.add_line("ratchet_a_shift_expr", 0, "ratchet_a_start_expr", 4)
device.add_line("ratchet_b_shift_expr", 0, "ratchet_b_start_expr", 4)
device.add_line("ratchet_c_shift_expr", 0, "ratchet_c_start_expr", 4)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_start_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_start_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_start_expr", 5)
device.add_line("ratchet_a_start_expr", 0, "ratchet_a_launch_expr", 0)
device.add_line("ratchet_b_start_expr", 0, "ratchet_b_launch_expr", 0)
device.add_line("ratchet_c_start_expr", 0, "ratchet_c_launch_expr", 0)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_launch_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_launch_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_launch_expr", 1)
device.add_line("dir_sign_final_expr", 0, "ratchet_a_launch_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_b_launch_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_c_launch_expr", 2)
device.add_line("ratchet_a_launch_expr", 0, "ratchet_a_store", 1)
device.add_line("ratchet_b_launch_expr", 0, "ratchet_b_store", 1)
device.add_line("ratchet_c_launch_expr", 0, "ratchet_c_store", 1)
device.add_line("ratchet_a_store", 0, "groove", 0)
device.add_line("ratchet_b_store", 0, "groove", 0)
device.add_line("ratchet_c_store", 0, "groove", 0)
device.add_line("slices_store", 0, "voice2_index_expr", 2)
device.add_line("slices_store", 0, "voice3_index_expr", 2)
device.add_line("slices_store", 0, "voice4_index_expr", 2)
device.add_line("sample_ms_store", 0, "playhead_pack", 4)
device.add_line("voice2_index_expr", 0, "slice_start_2_expr", 0)
device.add_line("voice3_index_expr", 0, "slice_start_3_expr", 0)
device.add_line("voice4_index_expr", 0, "slice_start_4_expr", 0)
device.add_line("region_start_final_expr", 0, "slice_start_2_expr", 1)
device.add_line("region_start_final_expr", 0, "slice_start_3_expr", 1)
device.add_line("region_start_final_expr", 0, "slice_start_4_expr", 1)
device.add_line("slice_ms_expr", 0, "slice_start_2_expr", 2)
device.add_line("slice_ms_expr", 0, "slice_start_3_expr", 2)
device.add_line("slice_ms_expr", 0, "slice_start_4_expr", 2)
device.add_line("jitter_ms_expr", 0, "slice_start_2_expr", 3)
device.add_line("jitter_ms_expr", 0, "slice_start_3_expr", 3)
device.add_line("jitter_ms_expr", 0, "slice_start_4_expr", 3)
device.add_line("slice_start_2_expr", 0, "slice_end_2_expr", 0)
device.add_line("slice_start_3_expr", 0, "slice_end_3_expr", 0)
device.add_line("slice_start_4_expr", 0, "slice_end_4_expr", 0)
device.add_line("effective_slice_ms_expr", 0, "slice_end_2_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "slice_end_3_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "slice_end_4_expr", 1)
device.add_line("sample_ms_store", 0, "slice_end_2_expr", 2)
device.add_line("sample_ms_store", 0, "slice_end_3_expr", 2)
device.add_line("sample_ms_store", 0, "slice_end_4_expr", 2)
device.add_line("slice_start_2_expr", 0, "launch_pos_2_expr", 0)
device.add_line("slice_start_3_expr", 0, "launch_pos_3_expr", 0)
device.add_line("slice_start_4_expr", 0, "launch_pos_4_expr", 0)
device.add_line("slice_end_2_expr", 0, "launch_pos_2_expr", 1)
device.add_line("slice_end_3_expr", 0, "launch_pos_3_expr", 1)
device.add_line("slice_end_4_expr", 0, "launch_pos_4_expr", 1)
device.add_line("dir_sign_final_expr", 0, "launch_pos_2_expr", 2)
device.add_line("dir_sign_final_expr", 0, "launch_pos_3_expr", 2)
device.add_line("dir_sign_final_expr", 0, "launch_pos_4_expr", 2)
device.add_line("launch_pos_2_expr", 0, "launch_store_2", 1)
device.add_line("launch_pos_3_expr", 0, "launch_store_3", 1)
device.add_line("launch_pos_4_expr", 0, "launch_store_4", 1)
device.add_line("launch_store_2", 0, "groove_2", 0)
device.add_line("launch_store_3", 0, "groove_3", 0)
device.add_line("launch_store_4", 0, "groove_4", 0)
device.add_line("slice_start_2_expr", 0, "groove_2", 1)
device.add_line("slice_start_3_expr", 0, "groove_3", 1)
device.add_line("slice_start_4_expr", 0, "groove_4", 1)
device.add_line("slice_end_2_expr", 0, "groove_2", 2)
device.add_line("slice_end_3_expr", 0, "groove_3", 2)
device.add_line("slice_end_4_expr", 0, "groove_4", 2)
device.add_line("voice2_index_expr", 0, "ratchet_a_start_2_expr", 0)
device.add_line("voice2_index_expr", 0, "ratchet_b_start_2_expr", 0)
device.add_line("voice2_index_expr", 0, "ratchet_c_start_2_expr", 0)
device.add_line("region_start_final_expr", 0, "ratchet_a_start_2_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_b_start_2_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_c_start_2_expr", 1)
device.add_line("slices_store", 0, "ratchet_a_start_2_expr", 2)
device.add_line("slices_store", 0, "ratchet_b_start_2_expr", 2)
device.add_line("slices_store", 0, "ratchet_c_start_2_expr", 2)
device.add_line("slice_ms_expr", 0, "ratchet_a_start_2_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_b_start_2_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_c_start_2_expr", 3)
device.add_line("ratchet_a_shift_expr", 0, "ratchet_a_start_2_expr", 4)
device.add_line("ratchet_b_shift_expr", 0, "ratchet_b_start_2_expr", 4)
device.add_line("ratchet_c_shift_expr", 0, "ratchet_c_start_2_expr", 4)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_start_2_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_start_2_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_start_2_expr", 5)
device.add_line("ratchet_a_start_2_expr", 0, "ratchet_a_launch_2_expr", 0)
device.add_line("ratchet_b_start_2_expr", 0, "ratchet_b_launch_2_expr", 0)
device.add_line("ratchet_c_start_2_expr", 0, "ratchet_c_launch_2_expr", 0)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_launch_2_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_launch_2_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_launch_2_expr", 1)
device.add_line("dir_sign_final_expr", 0, "ratchet_a_launch_2_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_b_launch_2_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_c_launch_2_expr", 2)
device.add_line("ratchet_a_launch_2_expr", 0, "ratchet_a_store_2", 1)
device.add_line("ratchet_b_launch_2_expr", 0, "ratchet_b_store_2", 1)
device.add_line("ratchet_c_launch_2_expr", 0, "ratchet_c_store_2", 1)
device.add_line("ratchet_a_store_2", 0, "groove_2", 0)
device.add_line("ratchet_b_store_2", 0, "groove_2", 0)
device.add_line("ratchet_c_store_2", 0, "groove_2", 0)
device.add_line("voice3_index_expr", 0, "ratchet_a_start_3_expr", 0)
device.add_line("voice3_index_expr", 0, "ratchet_b_start_3_expr", 0)
device.add_line("voice3_index_expr", 0, "ratchet_c_start_3_expr", 0)
device.add_line("region_start_final_expr", 0, "ratchet_a_start_3_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_b_start_3_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_c_start_3_expr", 1)
device.add_line("slices_store", 0, "ratchet_a_start_3_expr", 2)
device.add_line("slices_store", 0, "ratchet_b_start_3_expr", 2)
device.add_line("slices_store", 0, "ratchet_c_start_3_expr", 2)
device.add_line("slice_ms_expr", 0, "ratchet_a_start_3_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_b_start_3_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_c_start_3_expr", 3)
device.add_line("ratchet_a_shift_expr", 0, "ratchet_a_start_3_expr", 4)
device.add_line("ratchet_b_shift_expr", 0, "ratchet_b_start_3_expr", 4)
device.add_line("ratchet_c_shift_expr", 0, "ratchet_c_start_3_expr", 4)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_start_3_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_start_3_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_start_3_expr", 5)
device.add_line("ratchet_a_start_3_expr", 0, "ratchet_a_launch_3_expr", 0)
device.add_line("ratchet_b_start_3_expr", 0, "ratchet_b_launch_3_expr", 0)
device.add_line("ratchet_c_start_3_expr", 0, "ratchet_c_launch_3_expr", 0)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_launch_3_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_launch_3_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_launch_3_expr", 1)
device.add_line("dir_sign_final_expr", 0, "ratchet_a_launch_3_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_b_launch_3_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_c_launch_3_expr", 2)
device.add_line("ratchet_a_launch_3_expr", 0, "ratchet_a_store_3", 1)
device.add_line("ratchet_b_launch_3_expr", 0, "ratchet_b_store_3", 1)
device.add_line("ratchet_c_launch_3_expr", 0, "ratchet_c_store_3", 1)
device.add_line("ratchet_a_store_3", 0, "groove_3", 0)
device.add_line("ratchet_b_store_3", 0, "groove_3", 0)
device.add_line("ratchet_c_store_3", 0, "groove_3", 0)
device.add_line("voice4_index_expr", 0, "ratchet_a_start_4_expr", 0)
device.add_line("voice4_index_expr", 0, "ratchet_b_start_4_expr", 0)
device.add_line("voice4_index_expr", 0, "ratchet_c_start_4_expr", 0)
device.add_line("region_start_final_expr", 0, "ratchet_a_start_4_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_b_start_4_expr", 1)
device.add_line("region_start_final_expr", 0, "ratchet_c_start_4_expr", 1)
device.add_line("slices_store", 0, "ratchet_a_start_4_expr", 2)
device.add_line("slices_store", 0, "ratchet_b_start_4_expr", 2)
device.add_line("slices_store", 0, "ratchet_c_start_4_expr", 2)
device.add_line("slice_ms_expr", 0, "ratchet_a_start_4_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_b_start_4_expr", 3)
device.add_line("slice_ms_expr", 0, "ratchet_c_start_4_expr", 3)
device.add_line("ratchet_a_shift_expr", 0, "ratchet_a_start_4_expr", 4)
device.add_line("ratchet_b_shift_expr", 0, "ratchet_b_start_4_expr", 4)
device.add_line("ratchet_c_shift_expr", 0, "ratchet_c_start_4_expr", 4)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_start_4_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_start_4_expr", 5)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_start_4_expr", 5)
device.add_line("ratchet_a_start_4_expr", 0, "ratchet_a_launch_4_expr", 0)
device.add_line("ratchet_b_start_4_expr", 0, "ratchet_b_launch_4_expr", 0)
device.add_line("ratchet_c_start_4_expr", 0, "ratchet_c_launch_4_expr", 0)
device.add_line("effective_slice_ms_expr", 0, "ratchet_a_launch_4_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_b_launch_4_expr", 1)
device.add_line("effective_slice_ms_expr", 0, "ratchet_c_launch_4_expr", 1)
device.add_line("dir_sign_final_expr", 0, "ratchet_a_launch_4_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_b_launch_4_expr", 2)
device.add_line("dir_sign_final_expr", 0, "ratchet_c_launch_4_expr", 2)
device.add_line("ratchet_a_launch_4_expr", 0, "ratchet_a_store_4", 1)
device.add_line("ratchet_b_launch_4_expr", 0, "ratchet_b_store_4", 1)
device.add_line("ratchet_c_launch_4_expr", 0, "ratchet_c_store_4", 1)
device.add_line("ratchet_a_store_4", 0, "groove_4", 0)
device.add_line("ratchet_b_store_4", 0, "groove_4", 0)
device.add_line("ratchet_c_store_4", 0, "groove_4", 0)

# Pitch randomization and pitch envelope
device.add_line("rand_pitch", 0, "pitch_rand_expr", 0)
device.add_line("pitch_dial", 0, "pitch_rand_expr", 1)
device.add_line("bias_dial", 0, "pitch_rand_expr", 2)
device.add_line("step_phase_expr", 0, "arp_index_expr", 0)
device.add_line("pitch_seed_store", 0, "arp_index_expr", 1)
device.add_line("step_phase_expr", 0, "arp_sign_expr", 0)
device.add_line("pitch_seed_store", 0, "arp_sign_expr", 1)
device.add_line("arp_index_expr", 0, "arp_semitone_expr", 0)
device.add_line("arp_semitone_expr", 0, "arp_amount_expr", 0)
device.add_line("arp_sign_expr", 0, "arp_amount_expr", 1)
device.add_line("arp_dial", 0, "arp_amount_expr", 2)
device.add_line("pitch_rand_expr", 0, "pitch_total_expr", 0)
device.add_line("arp_amount_expr", 0, "pitch_total_expr", 1)
device.add_line("pitch_total_expr", 0, "pitch_lock_final_expr", 0)
device.add_line("pitch_lock_store", 0, "pitch_lock_final_expr", 1)
device.add_line("pitch_lock_final_expr", 0, "ratio_expr", 0)
device.add_line("note_store", 0, "ratio_expr", 1)
device.add_line("pitch_env_dial", 0, "pitch_env_mul_expr", 0)
device.add_line("ratio_expr", 0, "pitch_env_start_expr", 0)
device.add_line("pitch_env_mul_expr", 0, "pitch_env_start_expr", 1)
device.add_line("pitch_env_start_expr", 0, "speed_env_pack", 0)
device.add_line("ratio_expr", 0, "speed_env_pack", 1)
device.add_line("decay_dial", 0, "speed_env_pack", 2)
device.add_line("speed_env_pack", 0, "speed_env_msg", 0)
device.add_line("speed_env_msg", 0, "ratio_line", 0)
device.add_line("ratio_line", 0, "voice_rate_mul_1", 0)
device.add_line("ratio_line", 0, "voice_rate_mul_2", 0)
device.add_line("ratio_line", 0, "voice_rate_mul_3", 0)
device.add_line("ratio_line", 0, "voice_rate_mul_4", 0)
device.add_line("voice1_detune_ratio_expr", 0, "voice1_rate_dir_expr", 0)
device.add_line("voice2_detune_ratio_expr", 0, "voice2_rate_dir_expr", 0)
device.add_line("voice3_detune_ratio_expr", 0, "voice3_rate_dir_expr", 0)
device.add_line("voice4_detune_ratio_expr", 0, "voice4_rate_dir_expr", 0)
device.add_line("dir_sign_final_expr", 0, "voice1_rate_dir_expr", 1)
device.add_line("dir_sign_final_expr", 0, "voice2_rate_dir_expr", 1)
device.add_line("dir_sign_final_expr", 0, "voice3_rate_dir_expr", 1)
device.add_line("dir_sign_final_expr", 0, "voice4_rate_dir_expr", 1)
device.add_line("voice1_rate_dir_expr", 0, "voice_rate_mul_1", 1)
device.add_line("voice2_rate_dir_expr", 0, "voice_rate_mul_2", 1)
device.add_line("voice3_rate_dir_expr", 0, "voice_rate_mul_3", 1)
device.add_line("voice4_rate_dir_expr", 0, "voice_rate_mul_4", 1)
device.add_line("voice_rate_mul_1", 0, "groove", 0)
device.add_line("voice_rate_mul_2", 0, "groove_2", 0)
device.add_line("voice_rate_mul_3", 0, "groove_3", 0)
device.add_line("voice_rate_mul_4", 0, "groove_4", 0)

# Chop and autopan
device.add_line("rand_chop", 0, "chop_gate_expr", 0)
device.add_line("chop_dial", 0, "chop_gate_expr", 1)
device.add_line("chop_gate_expr", 0, "chop_gate_final_expr", 0)
device.add_line("gate_lock_store", 0, "chop_gate_final_expr", 1)
device.add_line("chop_gate_final_expr", 0, "chop_pack", 0)
device.add_line("chop_pack", 0, "chop_line", 0)
device.add_line("chop_init", 0, "chop_line", 0)

device.add_line("rand_pan", 0, "pan_amount_expr", 0)
device.add_line("pan_dial", 0, "pan_amount_expr", 1)
device.add_line("pan_amount_expr", 0, "pan_l_expr", 0)
device.add_line("pan_amount_expr", 0, "pan_r_expr", 0)
device.add_line("pan_l_expr", 0, "pan_l_pack", 0)
device.add_line("pan_r_expr", 0, "pan_r_pack", 0)
device.add_line("pan_l_pack", 0, "pan_l_line", 0)
device.add_line("pan_r_pack", 0, "pan_r_line", 0)
device.add_line("pan_init_l", 0, "pan_l_line", 0)
device.add_line("pan_init_r", 0, "pan_r_line", 0)

# Audio path
device.add_line("groove", 0, "amp_mul", 0)
device.add_line("groove_2", 0, "amp_mul_2", 0)
device.add_line("groove_3", 0, "amp_mul_3", 0)
device.add_line("groove_4", 0, "amp_mul_4", 0)
device.add_line("env_line", 0, "amp_mul", 1)
device.add_line("env_line", 0, "amp_mul_2", 1)
device.add_line("env_line", 0, "amp_mul_3", 1)
device.add_line("env_line", 0, "amp_mul_4", 1)
device.add_line("amp_mul", 0, "voice_gain_1", 0)
device.add_line("amp_mul_2", 0, "voice_gain_2", 0)
device.add_line("amp_mul_3", 0, "voice_gain_3", 0)
device.add_line("amp_mul_4", 0, "voice_gain_4", 0)
device.add_line("voice1_gain_expr", 0, "voice_gain_1", 1)
device.add_line("voice2_gain_expr", 0, "voice_gain_2", 1)
device.add_line("voice3_gain_expr", 0, "voice_gain_3", 1)
device.add_line("voice4_gain_expr", 0, "voice_gain_4", 1)
device.add_line("voice_gain_1", 0, "voice1_l_mul", 0)
device.add_line("voice_gain_1", 0, "voice1_r_mul", 0)
device.add_line("voice_gain_2", 0, "voice2_l_mul", 0)
device.add_line("voice_gain_2", 0, "voice2_r_mul", 0)
device.add_line("voice_gain_3", 0, "voice3_l_mul", 0)
device.add_line("voice_gain_3", 0, "voice3_r_mul", 0)
device.add_line("voice_gain_4", 0, "voice4_l_mul", 0)
device.add_line("voice_gain_4", 0, "voice4_r_mul", 0)
device.add_line("voice1_l_gain_expr", 0, "voice1_l_mul", 1)
device.add_line("voice1_r_gain_expr", 0, "voice1_r_mul", 1)
device.add_line("voice2_l_gain_expr", 0, "voice2_l_mul", 1)
device.add_line("voice2_r_gain_expr", 0, "voice2_r_mul", 1)
device.add_line("voice3_l_gain_expr", 0, "voice3_l_mul", 1)
device.add_line("voice3_r_gain_expr", 0, "voice3_r_mul", 1)
device.add_line("voice4_l_gain_expr", 0, "voice4_l_mul", 1)
device.add_line("voice4_r_gain_expr", 0, "voice4_r_mul", 1)
device.add_line("voice1_l_mul", 0, "voice_sum_l_a", 0)
device.add_line("voice2_l_mul", 0, "voice_sum_l_a", 1)
device.add_line("voice3_l_mul", 0, "voice_sum_l_b", 0)
device.add_line("voice4_l_mul", 0, "voice_sum_l_b", 1)
device.add_line("voice_sum_l_a", 0, "voice_sum_l", 0)
device.add_line("voice_sum_l_b", 0, "voice_sum_l", 1)
device.add_line("voice1_r_mul", 0, "voice_sum_r_a", 0)
device.add_line("voice2_r_mul", 0, "voice_sum_r_a", 1)
device.add_line("voice3_r_mul", 0, "voice_sum_r_b", 0)
device.add_line("voice4_r_mul", 0, "voice_sum_r_b", 1)
device.add_line("voice_sum_r_a", 0, "voice_sum_r", 0)
device.add_line("voice_sum_r_b", 0, "voice_sum_r", 1)
device.add_line("voice_sum_l", 0, "step_gate_mul_l", 0)
device.add_line("voice_sum_r", 0, "step_gate_mul_r", 0)
device.add_line("chop_line", 0, "step_gate_mul_l", 1)
device.add_line("chop_line", 0, "step_gate_mul_r", 1)

device.add_line("step_gate_mul_l", 0, "pan_mul_l", 0)
device.add_line("step_gate_mul_r", 0, "pan_mul_r", 0)
device.add_line("pan_l_line", 0, "pan_mul_l", 1)
device.add_line("pan_r_line", 0, "pan_mul_r", 1)

device.add_line("pan_mul_l", 0, "tone_l", 0)
device.add_line("pan_mul_r", 0, "tone_r", 0)
device.add_line("filter_dial", 0, "filter_pack", 0)
device.add_line("filter_pack", 0, "filter_line", 0)
device.add_line("filter_line", 0, "tone_l", 1)
device.add_line("filter_line", 0, "tone_r", 1)
device.add_line("res_load", 0, "tone_l", 2)
device.add_line("res_load", 0, "tone_r", 2)

device.add_line("tone_out_l", 0, "predrive_l", 0)
device.add_line("tone_out_r", 0, "predrive_r", 0)
device.add_line("drive_dial", 0, "drive_scale", 0)
device.add_line("drive_scale", 0, "drive_pack", 0)
device.add_line("drive_pack", 0, "drive_line", 0)
device.add_line("drive_line", 0, "predrive_l", 1)
device.add_line("drive_line", 0, "predrive_r", 1)

device.add_line("predrive_l", 0, "sat_l", 0)
device.add_line("predrive_r", 0, "sat_r", 0)
device.add_line("mix_dial", 0, "mix_mix_in", 0)

device.add_line("mix_out_l", 0, "output_gain", 0)
device.add_line("mix_out_r", 0, "output_gain", 1)
device.add_line("output_gain", 0, "plugout", 0)
device.add_line("output_gain", 1, "plugout", 1)


# =========================================================================
# Build
# =========================================================================

output = device_output_path("Super Slicer Prototype", device_type="instrument")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
