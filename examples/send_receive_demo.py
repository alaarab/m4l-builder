"""Send/receive demo -- clean cross-routing with send~/receive~.

Stereo audio effect with parallel dry and wet paths routed via send~/receive~.
Also uses send/receive for a message-domain parameter reset, and loadbang
to initialize gain to 0 dB on device load.
"""

from m4l_builder import (AudioEffect, device_output_path,
                          send_signal, receive_signal,
                          send_msg, receive_msg, loadbang)

device = AudioEffect("Send Receive Demo", width=200, height=100)

# --- Dry path: plugin~ -> send~ dry_l / dry_r ---
device.add_dsp(*send_signal("dry_l", "dry_l"))
device.add_dsp(*send_signal("dry_r", "dry_r"))
device.add_line("obj-plugin", 0, "dry_l_send", 0)
device.add_line("obj-plugin", 1, "dry_r_send", 0)

# --- Wet path: plugin~ -> *~ wet_gain -> send~ wet_l / wet_r ---
device.add_newobj("wet_gain_l", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 120, 50, 20])
device.add_newobj("wet_gain_r", "*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 120, 50, 20])
device.add_dsp(*send_signal("wet_l", "wet_l"))
device.add_dsp(*send_signal("wet_r", "wet_r"))

device.add_line("obj-plugin", 0, "wet_gain_l", 0)
device.add_line("obj-plugin", 1, "wet_gain_r", 0)
device.add_line("wet_gain_l", 0, "wet_l_send", 0)
device.add_line("wet_gain_r", 0, "wet_r_send", 0)

# --- Receive and merge both paths to plugout~ ---
device.add_dsp(*receive_signal("rcv_dry_l", "dry_l"))
device.add_dsp(*receive_signal("rcv_dry_r", "dry_r"))
device.add_dsp(*receive_signal("rcv_wet_l", "wet_l"))
device.add_dsp(*receive_signal("rcv_wet_r", "wet_r"))

# Mix: dry + wet per channel
device.add_newobj("mix_l", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 200, 40, 20])
device.add_newobj("mix_r", "+~", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[90, 200, 40, 20])

device.add_line("rcv_dry_l_receive", 0, "mix_l", 0)
device.add_line("rcv_wet_l_receive", 0, "mix_l", 1)
device.add_line("rcv_dry_r_receive", 0, "mix_r", 0)
device.add_line("rcv_wet_r_receive", 0, "mix_r", 1)
device.add_line("mix_l", 0, "obj-plugout", 0)
device.add_line("mix_r", 0, "obj-plugout", 1)

# --- Loadbang: set output gain to 0 dB (= 1.0 linear) on load ---
device.add_dsp(*loadbang("init"))
device.add_newobj("init_msg", "message", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[30, 260, 50, 20])
# loadbang triggers the message box (which could set a gain param)
device.add_line("init_loadbang", 0, "init_msg", 0)

# --- Message-domain send/receive for parameter reset ---
device.add_dsp(*send_msg("reset_tx", "param_reset"))
device.add_dsp(*receive_msg("reset_rx", "param_reset"))
device.add_line("init_msg", 0, "reset_tx_send", 0)

output = device_output_path("Send Receive Demo", subfolder="_Examples")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
