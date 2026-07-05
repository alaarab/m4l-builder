"""graph_core — the ONE shared EQ-graph math core (T25/Q53).

Every EQ display engine drew its own ``freq_to_x``/``x_to_freq``/
``biquad_coeffs``/``response_db`` — five drifting copies, one of which
(peaking_eq_display) faked the response with a Lorentzian bump instead of
the true RBJ biquad magnitude. This module holds the CANONICAL copies
(extracted verbatim from eq_curve, the flagship implementation).

The functions reference host-defined globals: ``MIN_FREQ`` / ``MAX_FREQ``
/ ``MIN_Q`` / ``MAX_Q``, ``sample_rate``, the ``TYPE_*`` constants and the
plot-geometry globals ``freq_to_x`` uses. Engines with a different type
vocabulary alias theirs first (linear_phase: ``var TYPE_LOWPASS =
TYPE_HIGHCUT; var TYPE_HIGHPASS = TYPE_LOWCUT;`` — a low-CUT is a
high-PASS, the bodies were always consistent).
"""

GRAPH_CORE_JS = r"""
function freq_to_x(f) {
    var norm = (Math.log(clamp(f, MIN_FREQ, MAX_FREQ)) - LOG_MIN) / LOG_RANGE;
    return plot_left() + norm * plot_w();
}

function x_to_freq(x) {
    var norm = (x - plot_left()) / plot_w();
    norm = clamp(norm, 0, 1);
    return Math.exp(LOG_MIN + norm * LOG_RANGE);
}

function biquad_coeffs(type, freq, gain, q) {
    var sr = clamp(sample_rate, 22050.0, 384000.0);
    var fc = clamp(freq, MIN_FREQ, Math.min(MAX_FREQ, sr * 0.49));
    var Q = clamp(q, MIN_Q, MAX_Q);
    var w0 = 2.0 * Math.PI * fc / sr;
    var cosw0 = Math.cos(w0);
    var sinw0 = Math.sin(w0);
    var alpha = sinw0 / (2.0 * Q);
    var A = Math.pow(10.0, gain / 40.0);
    var shelf_s = clamp(Q, 0.1, 4.0);
    var shelf_alpha = sinw0 * 0.5 * Math.sqrt((A + 1.0 / A) * (1.0 / shelf_s - 1.0) + 2.0);
    var two_sqrt_A_alpha = 2.0 * Math.sqrt(A) * shelf_alpha;
    var b0, b1, b2, a0, a1, a2;

    switch (type) {
        case TYPE_PEAK:
            b0 = 1.0 + alpha * A;
            b1 = -2.0 * cosw0;
            b2 = 1.0 - alpha * A;
            a0 = 1.0 + alpha / A;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha / A;
            break;

        case TYPE_LOSHELF:
            b0 = A * ((A + 1.0) - (A - 1.0) * cosw0 + two_sqrt_A_alpha);
            b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosw0);
            b2 = A * ((A + 1.0) - (A - 1.0) * cosw0 - two_sqrt_A_alpha);
            a0 = (A + 1.0) + (A - 1.0) * cosw0 + two_sqrt_A_alpha;
            a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosw0);
            a2 = (A + 1.0) + (A - 1.0) * cosw0 - two_sqrt_A_alpha;
            break;

        case TYPE_HISHELF:
            b0 = A * ((A + 1.0) + (A - 1.0) * cosw0 + two_sqrt_A_alpha);
            b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw0);
            b2 = A * ((A + 1.0) + (A - 1.0) * cosw0 - two_sqrt_A_alpha);
            a0 = (A + 1.0) - (A - 1.0) * cosw0 + two_sqrt_A_alpha;
            a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw0);
            a2 = (A + 1.0) - (A - 1.0) * cosw0 - two_sqrt_A_alpha;
            break;

        case TYPE_LOWPASS:
            b0 = (1.0 - cosw0) * 0.5;
            b1 = 1.0 - cosw0;
            b2 = (1.0 - cosw0) * 0.5;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;

        case TYPE_HIGHPASS:
            b0 = (1.0 + cosw0) * 0.5;
            b1 = -(1.0 + cosw0);
            b2 = (1.0 + cosw0) * 0.5;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;

        case TYPE_NOTCH:
            b0 = 1.0;
            b1 = -2.0 * cosw0;
            b2 = 1.0;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;

        case TYPE_BANDPASS:
            b0 = alpha;
            b1 = 0.0;
            b2 = -alpha;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;

        case TYPE_ALLPASS:
            b0 = 1.0 - alpha;
            b1 = -2.0 * cosw0;
            b2 = 1.0 + alpha;
            a0 = 1.0 + alpha;
            a1 = -2.0 * cosw0;
            a2 = 1.0 - alpha;
            break;

        default:
            return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0];
    }

    if (Math.abs(a0) < 1.0e-12) return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0];
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

function response_db(coeffs, freq) {
    var sr = clamp(sample_rate, 22050.0, 384000.0);
    var fc = clamp(freq, MIN_FREQ, Math.min(MAX_FREQ, sr * 0.49));
    var w = 2.0 * Math.PI * fc / sr;
    var c1 = Math.cos(w);
    var s1 = Math.sin(w);
    var c2 = Math.cos(2.0 * w);
    var s2 = Math.sin(2.0 * w);

    var b0 = coeffs[0];
    var b1 = coeffs[1];
    var b2 = coeffs[2];
    var a0 = coeffs[3];
    var a1 = coeffs[4];
    var a2 = coeffs[5];

    var nr = b0 + b1 * c1 + b2 * c2;
    var ni = -b1 * s1 - b2 * s2;
    var dr = a0 + a1 * c1 + a2 * c2;
    var di = -a1 * s1 - a2 * s2;

    var num = nr * nr + ni * ni;
    var den = dr * dr + di * di;
    var mag = num / Math.max(den, 1.0e-20);
    var db = 10.0 * safe_log10(mag);
    if (db < DISPLAY_FLOOR) db = DISPLAY_FLOOR;
    if (db > MAX_GAIN) db = MAX_GAIN;
    return db;
}
"""


def graph_core_js() -> str:
    """Return the shared graph-math JS block (see module docstring)."""
    return GRAPH_CORE_JS
