"""Validate demo -- shows device.validate() catching common issues.

Builds a device with intentional problems (duplicate ID, bad patchline ref),
prints the warnings, then builds it correctly and exports to .amxd.
"""

import os
from m4l_builder import AudioEffect, device_output_path

# --- Part 1: Build a broken device on purpose ---
bad = AudioEffect("Validate Demo", width=200, height=100)

# Duplicate ID: two boxes named "gain"
bad.add_newobj("gain", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 100, 40, 20])
bad.add_newobj("gain", "*~ 1.", numinlets=2, numoutlets=1,
               outlettype=["signal"], patching_rect=[80, 100, 40, 20])

# Patchline referencing a nonexistent object
bad.add_line("obj-plugin", 0, "gain", 0)
bad.add_line("ghost_obj", 0, "obj-plugout", 0)

warnings = bad.validate()
print("=== Broken device warnings ===")
for w in warnings:
    print(f"  - {w}")
print(f"  Total: {len(warnings)} warnings\n")

# --- Part 2: Build it correctly ---
good = AudioEffect("Validate Demo", width=200, height=100)

good.add_newobj("gain_l", "*~ 1.", numinlets=2, numoutlets=1,
                outlettype=["signal"], patching_rect=[30, 100, 40, 20])
good.add_newobj("gain_r", "*~ 1.", numinlets=2, numoutlets=1,
                outlettype=["signal"], patching_rect=[80, 100, 40, 20])

good.add_line("obj-plugin", 0, "gain_l", 0)
good.add_line("obj-plugin", 1, "gain_r", 0)
good.add_line("gain_l", 0, "obj-plugout", 0)
good.add_line("gain_r", 0, "obj-plugout", 1)

warnings = good.validate()
print("=== Corrected device warnings ===")
if not warnings:
    print("  None -- device is clean!")
print()

# --- Part 3: Show JSON output ---
json_str = good.to_json()
print("=== Patcher JSON (first 500 chars) ===")
print(json_str[:500])
print("...\n")

# --- Part 4: Write to .amxd ---
output = device_output_path("Validate Demo")
written = good.build(output)
print(f"Built {written} bytes -> {output}")
