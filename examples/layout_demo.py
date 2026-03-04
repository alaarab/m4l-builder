"""Layout demo -- same device built with layout helpers vs manual rects."""
from m4l_builder import AudioEffect, WARM, device_output_path

# === Version with layout helpers ===
device = AudioEffect("Layout Demo", width=300, height=130, theme=WARM)
device.add_panel("bg", [0, 0, 300, 130])

with device.column(10, 10, spacing=4, width=280) as col:
    col.add_comment("title", "LAYOUT DEMO", height=16)
    with col.row(spacing=8, height=90) as row:
        row.add_dial("freq", "Freq", width=50, min_val=20, max_val=20000, unitstyle=3)
        row.add_dial("res", "Res", width=50, min_val=0, max_val=100, unitstyle=5)
        row.add_dial("gain", "Gain", width=50, min_val=-24, max_val=24, unitstyle=4)
        row.add_dial("mix", "Mix", width=50, min_val=0, max_val=100, unitstyle=5)

output = device_output_path("Layout Demo")
written = device.build(output)
print(f"Built {written} bytes -> {output}")
