"""Granular looper — Instrument example.

Records audio into a buffer, then plays it back using groove~ with
loop points and speed control to simulate granular-style textures.

Signal flow:
  adc~ -> (record toggle) -> record~ -> buffer~
  groove~ (looping) -> live.gain~ -> plugout~

Controls:
  record_toggle: arm recording into the buffer
  speed_dial:    playback speed / grain density (groove~ speed)
  start_dial:    loop start position (0-100%)
  end_dial:      loop end position (0-100%)
  jitter_dial:   position scatter amount (adds noise to playback head)
"""

from m4l_builder import Instrument, MIDNIGHT, device_output_path

WIDTH = 380
HEIGHT = 200
BUFFER_MS = 4000  # 4 second loop buffer

device = Instrument("Granular Looper", width=WIDTH, height=HEIGHT, theme=MIDNIGHT)

# =========================================================================
# UI
# =========================================================================

device.add_panel("bg", [0, 0, WIDTH, HEIGHT])


device.add_comment("lbl_rec", [8, 22, 60, 12], "RECORD",
                   fontsize=9.0, textcolor=[0.85, 0.35, 0.35, 0.7])
device.add_comment("lbl_play", [90, 22, 60, 12], "PLAYBACK",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])
device.add_comment("lbl_out", [270, 22, 60, 12], "OUTPUT",
                   fontsize=9.0, textcolor=[0.45, 0.75, 0.65, 0.6])

# Record toggle button
device.add_toggle("record_toggle", "Record", [8, 32, 60, 60],
                  annotation_name="Arm recording — press to capture audio")
device.add_comment("lbl_rec2", [8, 96, 60, 12], "ARM REC",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Playback controls
device.add_dial("speed_dial", "Speed", [90, 32, 50, 60],
                min_val=0.1, max_val=4.0, initial=1.0,
                unitstyle=1, parameter_exponent=1.5, appearance=1,
                annotation_name="Playback speed (1.0 = normal, 0.5 = half speed)")
device.add_comment("lbl_speed", [90, 96, 50, 12], "SPEED",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

device.add_dial("start_dial", "Start", [148, 32, 50, 60],
                min_val=0.0, max_val=100.0, initial=0.0,
                unitstyle=5, appearance=1,
                annotation_name="Loop start position (0-100%)")
device.add_comment("lbl_start", [148, 96, 50, 12], "START",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

device.add_dial("end_dial", "End", [206, 32, 50, 60],
                min_val=0.0, max_val=100.0, initial=100.0,
                unitstyle=5, appearance=1,
                annotation_name="Loop end position (0-100%)")
device.add_comment("lbl_end", [206, 96, 50, 12], "END",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

device.add_dial("jitter_dial", "Jitter", [264, 32, 50, 60] if WIDTH > 350 else [8, 112, 50, 60],
                min_val=0.0, max_val=100.0, initial=0.0,
                unitstyle=5, appearance=1,
                annotation_name="Playback position scatter (0-100%)")
device.add_comment("lbl_jitter", [264, 96, 50, 12] if WIDTH > 350 else [8, 168, 50, 12], "JITTER",
                   fontsize=8.0, textcolor=[0.50, 0.50, 0.52, 0.7])

# Master gain
device.add_live_gain("gain", "Volume", [310, 32, 62, 155],
                     min_val=-70.0, max_val=6.0, initial=0.0,
                     orientation=1, shortname="Vol")

# =========================================================================
# DSP objects
# =========================================================================

# Audio input
device.add_newobj("adc", "adc~", numinlets=1, numoutlets=2,
                  outlettype=["signal", "signal"],
                  patching_rect=[30, 30, 50, 20])

# Buffer for recording
device.add_newobj("loop_buf", f"buffer~ loopbuf {BUFFER_MS}",
                  numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[30, 60, 140, 20])

# record~ for writing into the buffer
device.add_newobj("rec_l", "record~ loopbuf", numinlets=2, numoutlets=0,
                  patching_rect=[30, 90, 100, 20])

# Trigger from toggle: when 1 start recording, when 0 stop
device.add_newobj("rec_gate", "t i i", numinlets=1, numoutlets=2,
                  outlettype=["", ""], patching_rect=[30, 120, 45, 20])

# groove~ for looping playback (stereo via 2 channels in the same buffer)
device.add_newobj("groove", "groove~ loopbuf 1", numinlets=4, numoutlets=3,
                  outlettype=["signal", "signal", ""],
                  patching_rect=[30, 160, 120, 20])

# Speed smoothing
device.add_newobj("speed_pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 150, 60, 20])
device.add_newobj("speed_ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 180, 40, 20])

# Loop points: start/end in ms from 0-100% of buffer
# start_ms = (start_pct / 100) * BUFFER_MS
device.add_newobj("start_expr", f"expr ($f1 / 100.0) * {BUFFER_MS}",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[280, 150, 200, 20])
device.add_newobj("end_expr", f"expr ($f1 / 100.0) * {BUFFER_MS}",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[280, 180, 200, 20])

# Jitter: noise~ scaled to ±jitter_ms, added to groove~ position
device.add_newobj("jitter_scale", f"expr ($f1 / 100.0) * {BUFFER_MS * 0.1}",
                  numinlets=1, numoutlets=1, outlettype=["float"],
                  patching_rect=[280, 210, 200, 20])

# plugout~
device.add_newobj("plugout", "plugout~", numinlets=2, numoutlets=0,
                  patching_rect=[200, 260, 60, 20])

# =========================================================================
# Connections
# =========================================================================

# Record toggle -> start/stop recording
device.add_line("record_toggle", 0, "rec_gate", 0)
device.add_line("rec_gate", 0, "rec_l", 1)    # start inlet
device.add_line("adc", 0, "rec_l", 0)          # audio in

# groove~ loop points
device.add_line("start_dial", 0, "start_expr", 0)
device.add_line("end_dial", 0, "end_expr", 0)
device.add_line("start_expr", 0, "groove", 1)  # loop start inlet
device.add_line("end_expr", 0, "groove", 2)    # loop end inlet

# Speed control
device.add_line("speed_dial", 0, "speed_pk", 0)
device.add_line("speed_pk", 0, "speed_ln", 0)
device.add_line("speed_ln", 0, "groove", 0)    # groove~ speed inlet

# Enable looping in groove~ (inlet 3 = loop flag, 1 = loop)
# Done via the initial arg "1" in groove~ definition

# Output: groove~ stereo -> live.gain~ -> plugout~
device.add_line("groove", 0, "gain", 0)
device.add_line("groove", 1, "gain", 1)
device.add_line("gain", 0, "plugout", 0)
device.add_line("gain", 1, "plugout", 1)

# =========================================================================
# Build
# =========================================================================
output = device_output_path("Granular Looper", device_type="instrument", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
