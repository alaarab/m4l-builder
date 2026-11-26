# record~ reference

Captured from Max 9.0.10 ARM64 on 2026-09-10 using Object Studio's
`tools/prepare_record_probe.py`; converted with `collect_record_reference.py`.
Original capture SHA256:
`92781a444d1b19fde813b466c33465cff6d096570e1ad016e39c54888d74c627`.
Raw source is kept outside this repo at
`reference/all68-runtime-20260910/record-traced-44100-max/max.json`.

Input left is n+1, right is -(n+1)/2. Three captures: 131-frame mono loop,
131-frame mono one-shot, and 151-frame stereo loop. Each captures 512 sync
samples and the resulting full buffer. All buffers span at least one MSP
64-frame vector. Looping within a vector repeats source samples from the start
of that vector, as confirmed in both capture and original ARM64 disassembly.

The first fixture line gives capture length and case count. Each case then
contains buffer length/channel count/loop flag, synchronization values, and one
line per recorded buffer channel. Tests exercise the whole shared graph at
three sample rates and callback sizes 1, 31, 64, 127 and 256. These frame-based
cases are sample-rate independent; the original capture rate was 44100 Hz.
Dynamic record ranges and Gen readback of the same record buffer are not
certified by this fixture.
