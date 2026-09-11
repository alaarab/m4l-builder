"""Stereo linear-phase low-pass kernel for the Split device.

The consumer forms High = delayed input - Low in the time domain. This retains
DC/Nyquist and guarantees unity reconstruction even during cutoff automation.
Only Low uses the STFT; the dry delay must match the measured pfft~ latency.
Control receivers must use Max for Live's device-local ``---`` namespace.
"""

import json

from ..gen_patcher import embed_gendsp
from ..objects import newobj, patchline

FFT_SIZE = 4096
OVERLAP = 4


def lowpass_kernel(*, namespace: str = "---split", fft_size: int = FFT_SIZE) -> str:
    """Return a stereo pfft~ patcher; outputs are Low L, Low R.

    ``<namespace>-cutoff`` receives Hz; ``<namespace>-sr`` receives host Hz.
    A raised-cosine transition is sampled at FFT bin frequencies. Cutoff is
    latched at each frame boundary so one frame never contains mixed settings.
    """
    if not namespace.startswith("---") or any(c.isspace() for c in namespace):
        raise ValueError("A device-local --- namespace is required")
    if fft_size < 256 or fft_size & (fft_size - 1):
        raise ValueError("fft_size must be a power of two >= 256")
    code = f"""
Param cutoff(250);
Param sr(48000);
History held(250);
History rate(48000);
held = in1 == 0 ? clamp(cutoff, 40, 16000) : held;
rate = in1 == 0 ? max(sr, 8000) : rate;
hz = in1 * rate / {fft_size};
width = min(held * 0.9, max(held * 0.5, 2 * rate / {fft_size}));
position = clamp((hz - held + width) / (2 * width), 0, 1);
out1 = 0.5 + 0.5 * cos(position * pi);
"""
    boxes = [embed_gendsp(code, numins=1, numouts=1, box_id="mask")]
    lines = []

    def add(id, text, ni=1, no=1):
        boxes.append(newobj(id, text, numinlets=ni, numoutlets=no,
                            outlettype=["signal"] * no,
                            patching_rect=[40, 40 + len(boxes) * 28, 150, 20]))

    def wire(src, so, dst, di):
        lines.append(patchline(src, so, dst, di))

    for param, receiver in (("cutoff", "cutoff"), ("sr", "sr")):
        add(f"r_{param}", f"r {namespace}-{receiver}")
        add(f"p_{param}", f"prepend {param}")
        wire(f"r_{param}", 0, f"p_{param}", 0)
        wire(f"p_{param}", 0, "mask", 0)
    for ch in (1, 2):
        add(f"in{ch}", f"fftin~ {ch}", no=3)
        add(f"out{ch}", f"fftout~ {ch}", ni=2, no=0)
        for part in (0, 1):
            id = f"mul{ch}_{part}"
            add(id, "*~", ni=2)
            wire(f"in{ch}", part, id, 0)
            wire("mask", 0, id, 1)
            wire(id, 0, f"out{ch}", part)
    wire("in1", 2, "mask", 0)
    return json.dumps({"patcher": {
        "fileversion": 1, "classnamespace": "box",
        "rect": [0, 0, 700, 700], "boxes": boxes, "lines": lines,
    }}, indent=2)


def complementary_mixer_code(*, latency: int = FFT_SIZE) -> str:
    """Gen: inputs dry L/R, Low L/R; outputs processed L/R.

    Parameters: low/high (dB), sl/sh (solo), ml/mh (mute), output (0 sum,
    1 low, 2 high), vector (host MSP signal-vector size, normally 64 in Live).
    pfft~ delays N-vector samples; delay Low by vector to align it with N-sample
    dry. Live impulse tests caught a 64-sample mismatch without this correction.
    Equal gain targets keep the reconstruction identity intact.
    The 5 ms gain ramp is sample-rate independent and reaches exact zero/unity.
    """
    if latency < 1:
        raise ValueError("latency must be positive")
    return f"""
Param low(0);
Param high(0);
Param sl(0);
Param sh(0);
Param ml(0);
Param mh(0);
Param output(0);
Param vector(64);
History gl(1);
History gh(1);
Delay dl({latency + 1});
Delay dr({latency + 1});
Delay alignl({latency});
Delay alignr({latency});
dryl = dl.read({latency});
dryr = dr.read({latency});
dl.write(in1);
dr.write(in2);
low_l = alignl.read(clamp(vector, 1, {latency - 1}));
low_r = alignr.read(clamp(vector, 1, {latency - 1}));
alignl.write(in3);
alignr.write(in4);
anysolo = (sl + sh) > 0.5;
tl = dbtoa(low) * (ml < 0.5) * (!anysolo || sl > 0.5) * (output != 2);
th = dbtoa(high) * (mh < 0.5) * (!anysolo || sh > 0.5) * (output != 1);
step = 1 / max(1, samplerate * 0.005);
gl = gl + clamp(tl - gl, -step, step);
gh = gh + clamp(th - gh, -step, step);
out1 = low_l * gl + (dryl - low_l) * gh;
out2 = low_r * gl + (dryr - low_r) * gh;
"""
