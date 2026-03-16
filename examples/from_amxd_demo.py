"""Round-trip demo: build a device, read it back, modify it, write again.

Shows AudioEffect.from_amxd() for reading existing .amxd files and adding
new controls on top of them.
"""

import os
import tempfile
from m4l_builder import AudioEffect, WARM, device_output_path

# --- Step 1: Build a simple gain device ---

device = AudioEffect("Round Trip Gain", width=150, height=110, theme=WARM)

device.add_panel("bg", [0, 0, 150, 110])
device.add_dial("gain", "Gain", [10, 6, 50, 90],
                min_val=-70.0, max_val=6.0, initial=0.0,
                unitstyle=4, annotation_name="Gain")

device.add_newobj("mul_l", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[30, 100, 40, 20])
device.add_newobj("mul_r", "*~ 1.", numinlets=2, numoutlets=1,
                  outlettype=["signal"], patching_rect=[150, 100, 40, 20])
device.add_newobj("db2a", "dbtoa", numinlets=1, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 80, 50, 20])
device.add_newobj("pk", "pack f 20", numinlets=2, numoutlets=1,
                  outlettype=[""], patching_rect=[200, 110, 60, 20])
device.add_newobj("ln", "line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", "bang"], patching_rect=[200, 140, 40, 20])

device.add_line("obj-plugin", 0, "mul_l", 0)
device.add_line("obj-plugin", 1, "mul_r", 0)
device.add_line("mul_l", 0, "obj-plugout", 0)
device.add_line("mul_r", 0, "obj-plugout", 1)
device.add_line("gain", 0, "db2a", 0)
device.add_line("db2a", 0, "pk", 0)
device.add_line("pk", 0, "ln", 0)
device.add_line("ln", 0, "mul_l", 1)
device.add_line("ln", 0, "mul_r", 1)

# Write the first version to a temp file
tmp_dir = tempfile.mkdtemp()
first_path = os.path.join(tmp_dir, "Round Trip Gain.amxd")
written = device.build(first_path)

print("=== Step 1: Built initial device ===")
print(f"  Boxes: {len(device.boxes)}")
print(f"  Lines: {len(device.lines)}")
print(f"  Bytes: {written}")
print(f"  Path:  {first_path}")

# --- Step 2: Read it back with from_amxd ---

loaded = AudioEffect.from_amxd(first_path)

print()
print("=== Step 2: Read back with from_amxd ===")
print(f"  Boxes: {len(loaded.boxes)}")
print(f"  Lines: {len(loaded.lines)}")
print(f"  Device type: {loaded.device_type}")
print(f"  Width: {loaded.width}, Height: {loaded.height}")

# --- Step 3: Add a second dial and write a new file ---

loaded.width = 250  # widen to fit the new control

loaded.add_dial("pan", "Pan", [110, 6, 50, 90],
                min_val=-100.0, max_val=100.0, initial=0.0,
                unitstyle=6, annotation_name="Pan")

second_path = os.path.join(tmp_dir, "Round Trip Gain v2.amxd")
written2 = loaded.build(second_path)

print()
print("=== Step 3: Added pan dial, wrote v2 ===")
print(f"  Boxes: {len(loaded.boxes)}")
print(f"  Lines: {len(loaded.lines)}")
print(f"  Bytes: {written2}")
print(f"  Path:  {second_path}")

# Also write to User Library for actual use in Ableton
output = device_output_path("Round Trip Gain", subfolder="_Examples")
device.build(output)
print()
print(f"User Library copy: {output}")

# Cleanup temp files
os.unlink(first_path)
os.unlink(second_path)
os.rmdir(tmp_dir)
print("Temp files cleaned up.")
