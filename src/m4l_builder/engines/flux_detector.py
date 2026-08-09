"""flux_detector -- THE onset detector, shared verbatim by both canvases.

performance_canvas.py (the inline Shard brain = playback truth) and
slice_overview.py (the flyout editor, which independently re-detects the
same grid) MUST run byte-identical detection or their grids silently
diverge at non-default SENS (2026-08-09 pitfall). This module is the single
source: both engines embed FLUX_DETECTOR_JS unmodified.

Algorithm (measured winner, 2026-08-09, scratch flux_proto.py sweep):
  centred 1024-pt spectral flux on the existing 512/256 frame grid.
  - frame i covers samples [i*256 - 256, i*256 + 768), zero-padded at the
    edges. CENTRING IS LOAD-BEARING: start-aligning the longer window
    doubles the early bias (-5.6 -> -11.6 ms) and costs a true positive.
  - periodic Hann, magnitudes scaled 2/512, half-wave-rectified positive
    bin differences summed / 513.
  - the adaptive-threshold chain (local mean +/-8 frames, geometric SENS
    curve, min-spacing, 63-cap) is unchanged except two constants rescaled
    to the new flux units: floor 0.0008 -> 3.874e-05 and the SENS curve
    multiplied by 0.53 so sens=30 keeps its slice count on real material.
  Measured vs the old RMS amplitude flux: 16/16 true onsets on every probe
  at every SENS (was 13-15/16), sustained-pad false onsets 63 -> 16, the
  110 Hz phase-beating trap 63 -> 4, median timing 4-7 ms early (was 8).
"""

FLUX_DETECTOR_JS = """\
// FLUX-DETECTOR-BEGIN (single source: engines/flux_detector.py -- do NOT
// edit in one canvas without the other; both embed this block verbatim)
var FLUX_FFT = 1024;
var FLUX_BINS = 513;
var flux_win_tab = null;

function flux_window() {
    if (flux_win_tab) return flux_win_tab;
    var w = [], n;
    for (n = 0; n < FLUX_FFT; n++) {
        w[n] = 0.5 - 0.5 * Math.cos((6.283185307179586 * n) / FLUX_FFT);
    }
    flux_win_tab = w;
    return w;
}

function flux_fft_mag(re, im, out) {
    // iterative radix-2 complex FFT (re/im clobbered); out receives the
    // first FLUX_BINS magnitudes scaled by 2/512 (the periodic-Hann sum).
    var n = FLUX_FFT, i, j, k, half, step;
    j = 0;
    for (i = 1; i < n; i++) {
        var bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j |= bit;
        if (i < j) {
            var tr = re[i]; re[i] = re[j]; re[j] = tr;
            var ti = im[i]; im[i] = im[j]; im[j] = ti;
        }
    }
    for (step = 2; step <= n; step <<= 1) {
        half = step >> 1;
        var ang = -6.283185307179586 / step;
        var wr = Math.cos(ang), wi = Math.sin(ang);
        for (i = 0; i < n; i += step) {
            var cr = 1.0, ci = 0.0;
            for (j = 0; j < half; j++) {
                var a = i + j, b = a + half;
                var xr = re[b] * cr - im[b] * ci;
                var xi = re[b] * ci + im[b] * cr;
                re[b] = re[a] - xr; im[b] = im[a] - xi;
                re[a] += xr; im[a] += xi;
                var ncr = cr * wr - ci * wi;
                ci = cr * wi + ci * wr;
                cr = ncr;
            }
        }
    }
    for (k = 0; k < FLUX_BINS; k++) {
        out[k] = Math.sqrt(re[k] * re[k] + im[k] * im[k]) * 0.00390625;
    }
}

function flux_frame_mono(buf, ch_count, start, frame_count) {
    // centred window: the 512-grid frame at start reads [start-256,
    // start+768), zero-padded where it runs off the buffer. Bulk peek per
    // channel (a per-sample loop is ~8x slower for the same result).
    var lo = start - 256, i, c;
    var seg = [];
    for (i = 0; i < FLUX_FFT; i++) seg[i] = 0.0;
    var a = lo > 0 ? lo : 0;
    var b = (lo + FLUX_FFT) < frame_count ? (lo + FLUX_FFT) : frame_count;
    if (b <= a) return seg;
    for (c = 1; c <= ch_count; c++) {
        var got = 0;
        var chunk = buf.peek(c, a, b - a);
        if (chunk instanceof Array) {
            for (i = 0; i < chunk.length; i++) seg[a - lo + i] += chunk[i];
            got = chunk.length;
        }
        if (got < b - a) {
            // no (or short) bulk peek in this environment -- per-sample
            for (i = a + got; i < b; i++) seg[i - lo] += buf.peek(c, i);
        }
    }
    if (ch_count > 1) {
        for (i = 0; i < FLUX_FFT; i++) seg[i] /= ch_count;
    }
    return seg;
}

function compute_onsets() {
    var frame_count = buffer_frames();
    if (frame_count <= 0) return compute_grid();
    var buf, ch_count;
    try {
        buf = new Buffer(BUFFER_NAME);
        ch_count = buf.channelcount();
    } catch (e) {
        return compute_grid();
    }
    if (!ch_count || ch_count <= 0) ch_count = 1;
    var win = flux_window();
    var re = [], im = [], mag = [], prev = [], flux = [];
    var w = 0, start, i, kb;
    for (start = 0; start + RMS_WIN <= frame_count; start += RMS_HOP) {
        var seg = flux_frame_mono(buf, ch_count, start, frame_count);
        for (i = 0; i < FLUX_FFT; i++) { re[i] = seg[i] * win[i]; im[i] = 0.0; }
        flux_fft_mag(re, im, mag);
        if (w === 0) {
            flux[0] = 0.0;
        } else {
            var acc = 0.0;
            for (kb = 0; kb < FLUX_BINS; kb++) {
                var db = mag[kb] - prev[kb];
                if (db > 0.0) acc += db;
            }
            flux[w] = acc / FLUX_BINS;
        }
        var swap = prev; prev = mag; mag = swap;
        w++;
    }
    if (flux.length < 3) return compute_grid();
    // geometric SENS curve (measured 2026-08-03), rescaled by 0.53 so the
    // sens=30 default keeps its slice count in the new spectral-flux units
    var mult = 0.53 * 6.0 * Math.pow(0.25 / 6.0, sensitivity / 100.0);
    var lwin = 8;
    var floor_thr = 0.00003874;
    var min_hops = Math.floor((min_spacing_ms / 1000.0 * sample_rate) / RMS_HOP);
    if (min_hops < 1) min_hops = 1;
    var onsets = [];
    var last_idx = -1000000;
    for (i = 1; i < flux.length - 1; i++) {
        var lo2 = i - lwin; if (lo2 < 0) lo2 = 0;
        var hi2 = i + lwin; if (hi2 > flux.length - 1) hi2 = flux.length - 1;
        var sum = 0.0, c2 = 0, j2;
        for (j2 = lo2; j2 <= hi2; j2++) { sum += flux[j2]; c2++; }
        var local_mean = c2 > 0 ? sum / c2 : 0.0;
        var thr = local_mean * mult + floor_thr;
        if (flux[i] > thr && flux[i] >= flux[i - 1] && flux[i] > flux[i + 1]) {
            if (i - last_idx >= min_hops) {
                onsets.push({ pos: (i * RMS_HOP) / frame_count, str: flux[i] });
                last_idx = i;
            }
        }
    }
    if (onsets.length > 63) {
        onsets.sort(function (a2, b2) { return b2.str - a2.str; });
        onsets = onsets.slice(0, 63);
    }
    onsets.sort(function (a2, b2) { return a2.pos - b2.pos; });
    var bounds = [0.0];
    for (i = 0; i < onsets.length; i++) {
        var p = clamp(onsets[i].pos, 0.0, 1.0);
        if (p > 0.0005 && p < 0.9995) bounds.push(p);
    }
    bounds.push(1.0);
    return bounds;
}
// FLUX-DETECTOR-END
"""
