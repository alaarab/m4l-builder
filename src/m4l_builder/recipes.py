"""Pre-wired DSP combo recipes for common M4L patterns.

Each recipe takes a device instance and parameters, then adds a complete
pre-wired section using device.add_dsp(), device.add_newobj(), device.add_dial(),
and device.add_line(). Returns a dict of important IDs for further wiring.
"""

from .dsp import (
    arpeggiator,
    compressor,
    convolver,
    delay_line,
    euclidean_rhythm,
    grain_cloud,
    lfo,
    macromap,
    midi_learn_chain,
    noteout,
    param_smooth,
    pitch_quantize,
    poly_voices,
    probability_gate,
    random_note,
    sidechain_routing,
    spectral_gate,
    transport_lfo,
    velocity_curve,
)
from .dsp import notein as dsp_notein
from .engines.sidechain_display import SIDECHAIN_DISPLAY_INLETS, sidechain_display_js
from .engines.spectral_display import SPECTRAL_DISPLAY_INLETS, spectral_display_js
from .stages import stage_result
from .ui import live_drop


def gain_controlled_stage(device, id_prefix, dial_rect, x=30, y=30):
    """Add a gain-controlled stage: live.dial -> dbtoa -> *~ gain cell.

    The dial outputs dB values, dbtoa converts to linear amplitude,
    and *~ applies the gain to whatever signal is wired into its inlet 0.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        dial_rect: [x, y, w, h] for the dial in presentation mode.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "dial" and "gain" (the *~ object ID).
    """
    p = id_prefix

    dial_id = device.add_dial(
        f"{p}_dial", f"{p}_gain", dial_rect,
        min_val=-70.0, max_val=6.0, initial=0.0,
        unitstyle=4, annotation_name=f"{p} Gain",
    )

    dbtoa_id = device.add_newobj(
        f"{p}_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[x, y, 50, 20],
    )

    smooth_boxes, smooth_lines = param_smooth(f"{p}_smooth")
    device.add_dsp(smooth_boxes, smooth_lines)

    gain_id = device.add_newobj(
        f"{p}_gain", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 90, 40, 20],
    )

    # Wiring: dial -> dbtoa -> pack -> line~ -> *~ inlet 1
    device.add_line(dial_id, 0, dbtoa_id, 0)
    device.add_line(dbtoa_id, 0, f"{p}_smooth_pack", 0)
    device.add_line(f"{p}_smooth_line", 0, gain_id, 1)

    return stage_result(
        {"dial": dial_id, "gain": gain_id},
        name="gain_controlled_stage",
        params={"gain": device.parameter(dial_id)},
        ports={
            "audio_in": gain_id.inlet(0),
            "audio_out": gain_id.outlet(0),
            "control_out": dial_id.outlet(0),
        },
    )


def parametric_eq_band_backend(
    device,
    band_index,
    *,
    loadbang_id,
    default_freq,
    default_type_name,
    filter_types,
    default_motion_rate=0.25,
    coeff_x_base=100,
    coeff_x_step=60,
    coeff_y=350,
    biquad_y=400,
    right_channel_y_offset=200,
    control_x=1100,
    control_y_base=350,
    control_y_step=30,
    type_x=700,
    enable_x=900,
):
    """Add one stereo parametric EQ band backend with smoothing and retriggers.

    This recipe assumes the surrounding device already provides the canonical
    per-band controls and state fanout objects named like `freq_b0`, `gain_b0`,
    `q_b0`, `type_b0`, `on_b0`, `motion_b0`, and `pak_b0`.
    """
    i = band_index
    coeff_x = coeff_x_base + i * coeff_x_step
    control_y = control_y_base + i * control_y_step

    coeff_id = device.add_newobj(
        f"fc_b{i}",
        f"filtercoeff~ {default_type_name}",
        numinlets=3, numoutlets=5,
        outlettype=["signal", "signal", "signal", "signal", "signal"],
        patching_rect=[coeff_x, coeff_y, 80, 20],
    )
    resamp_id = device.add_box({
        "box": {
            "id": f"msg_resamp_b{i}",
            "maxclass": "message",
            "text": "resamp 1",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [coeff_x, coeff_y - 30, 60, 20],
        }
    })
    device.add_line(loadbang_id, 0, resamp_id, 0)
    device.add_line(resamp_id, 0, coeff_id, 0)

    biquads = {}
    for channel, y_offset in (("l", 0), ("r", right_channel_y_offset)):
        biquad_id = device.add_newobj(
            f"bq_b{i}_{channel}",
            "biquad~",
            numinlets=6, numoutlets=1,
            outlettype=["signal"],
            patching_rect=[coeff_x, biquad_y + y_offset, 50, 20],
        )
        biquads[channel] = biquad_id
        for coeff_index in range(5):
            device.add_line(coeff_id, coeff_index, biquad_id, coeff_index + 1)

    freq_pack_id = device.add_newobj(
        f"pk_freq_b{i}",
        f"pack f {default_freq} 20",
        numinlets=2, numoutlets=1,
        outlettype=[""],
        patching_rect=[control_x, control_y, 80, 20],
    )
    freq_line_id = device.add_newobj(
        f"ln_freq_b{i}",
        "line~",
        numinlets=2, numoutlets=2,
        outlettype=["signal", "bang"],
        patching_rect=[control_x + 90, control_y, 40, 20],
    )
    freq_store_id = device.add_newobj(
        f"freq_store_b{i}",
        f"float {default_freq}",
        numinlets=2, numoutlets=1,
        outlettype=["float"],
        patching_rect=[control_x - 2, control_y - 24, 76, 20],
    )
    device.add_line(freq_pack_id, 0, freq_line_id, 0)
    device.add_line(freq_store_id, 0, coeff_id, 0)

    motion_lfo_id = device.add_newobj(
        f"motion_lfo_b{i}",
        f"cycle~ {default_motion_rate}",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[control_x + 140, control_y, 58, 20],
    )
    motion_depth_mul_id = device.add_newobj(
        f"motion_depth_mul_b{i}",
        "expr~ pow(2., $v1 * $f2)",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[control_x + 206, control_y, 48, 20],
    )
    motion_freq_mul_id = device.add_newobj(
        f"motion_freq_mul_b{i}",
        "*~ 1.",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[control_x + 262, control_y, 48, 20],
    )
    motion_depth_expr_id = device.add_newobj(
        f"motion_depth_expr_b{i}",
        "expr ($f2 > 0.5) ? (($f1 / 100.) * 1.25 * cos($f3 * 0.0174533)) : 0.",
        numinlets=3, numoutlets=1,
        outlettype=[""],
        patching_rect=[control_x + 318, control_y, 120, 20],
    )
    device.add_line(freq_line_id, 0, motion_freq_mul_id, 0)
    device.add_line(motion_lfo_id, 0, motion_depth_mul_id, 0)
    device.add_line(motion_depth_mul_id, 0, motion_freq_mul_id, 1)
    device.add_line(motion_freq_mul_id, 0, coeff_id, 0)

    gain_pack_id = device.add_newobj(
        f"pk_gain_db_b{i}",
        "pack f 0. 20",
        numinlets=2, numoutlets=1,
        outlettype=[""],
        patching_rect=[control_x, control_y + 40, 80, 20],
    )
    gain_line_id = device.add_newobj(
        f"ln_gain_db_b{i}",
        "line~",
        numinlets=2, numoutlets=2,
        outlettype=["signal", "bang"],
        patching_rect=[control_x + 90, control_y + 40, 40, 20],
    )
    motion_gain_depth_expr_id = device.add_newobj(
        f"motion_gain_depth_expr_b{i}",
        "expr ($f2 > 0.5) ? (($f1 / 100.) * 12. * sin($f3 * 0.0174533)) : 0.",
        numinlets=3, numoutlets=1,
        outlettype=[""],
        patching_rect=[control_x + 140, control_y + 40, 120, 20],
    )
    motion_gain_mul_id = device.add_newobj(
        f"motion_gain_mul_b{i}",
        "*~ 0.",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[control_x + 268, control_y + 40, 44, 20],
    )
    motion_gain_sum_id = device.add_newobj(
        f"motion_gain_sum_b{i}",
        "+~ 0.",
        numinlets=2, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[control_x + 320, control_y + 40, 44, 20],
    )
    gain_dbtoa_sig_id = device.add_newobj(
        f"gain_dbtoa_sig_b{i}",
        "expr~ pow(10., $v1 * 0.05)",
        numinlets=1, numoutlets=1,
        outlettype=["signal"],
        patching_rect=[control_x + 372, control_y + 40, 92, 20],
    )
    gain_recalc_id = device.add_newobj(
        f"gain_recalc_trig_b{i}",
        "t b f",
        numinlets=1, numoutlets=2,
        outlettype=["bang", "float"],
        patching_rect=[control_x + 468, control_y + 40, 44, 20],
    )
    gain_dbtoa_ctrl_id = device.add_newobj(
        f"gain_dbtoa_ctrl_b{i}",
        "dbtoa",
        numinlets=1, numoutlets=1,
        outlettype=["float"],
        patching_rect=[control_x + 518, control_y + 40, 44, 20],
    )
    device.add_line(gain_pack_id, 0, gain_line_id, 0)
    device.add_line(gain_line_id, 0, motion_gain_sum_id, 0)
    device.add_line(motion_lfo_id, 0, motion_gain_mul_id, 0)
    device.add_line(motion_gain_mul_id, 0, motion_gain_sum_id, 1)
    device.add_line(motion_gain_sum_id, 0, gain_dbtoa_sig_id, 0)
    device.add_line(gain_dbtoa_sig_id, 0, coeff_id, 1)

    q_pack_id = device.add_newobj(
        f"pk_q_b{i}",
        "pack f 1. 20",
        numinlets=2, numoutlets=1,
        outlettype=[""],
        patching_rect=[control_x, control_y + 80, 80, 20],
    )
    q_line_id = device.add_newobj(
        f"ln_q_b{i}",
        "line~",
        numinlets=2, numoutlets=2,
        outlettype=["signal", "bang"],
        patching_rect=[control_x + 90, control_y + 80, 40, 20],
    )
    q_recalc_id = device.add_newobj(
        f"q_recalc_trig_b{i}",
        "t b f",
        numinlets=1, numoutlets=2,
        outlettype=["bang", "float"],
        patching_rect=[control_x + 136, control_y + 80, 44, 20],
    )
    device.add_line(q_pack_id, 0, q_line_id, 0)
    device.add_line(q_line_id, 0, coeff_id, 2)

    type_sel_id = device.add_newobj(
        f"type_sel_b{i}",
        "select 0 1 2 3 4 5 6 7",
        numinlets=1, numoutlets=9,
        outlettype=["bang", "bang", "bang", "bang", "bang", "bang", "bang", "bang", ""],
        patching_rect=[type_x, control_y, 140, 20],
    )
    for type_index, type_name in enumerate(filter_types):
        type_msg_id = device.add_box({
            "box": {
                "id": f"msg_type_{type_index}_b{i}",
                "maxclass": "message",
                "text": type_name,
                "numinlets": 2,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [type_x + type_index * 65, control_y + 30, 60, 20],
            }
        })
        device.add_line(type_sel_id, type_index, type_msg_id, 0)
        device.add_line(type_msg_id, 0, coeff_id, 0)

    on_sel_id = device.add_newobj(
        f"on_sel_b{i}",
        "select 0 1",
        numinlets=1, numoutlets=3,
        outlettype=["bang", "bang", ""],
        patching_rect=[enable_x, control_y, 60, 20],
    )
    off_id = device.add_box({
        "box": {
            "id": f"msg_off_b{i}",
            "maxclass": "message",
            "text": "off",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [enable_x, control_y + 30, 30, 20],
        }
    })
    on_bang_id = device.add_newobj(
        f"on_bang_b{i}",
        "t b",
        numinlets=1, numoutlets=1,
        outlettype=["bang"],
        patching_rect=[enable_x + 40, control_y + 30, 30, 20],
    )
    device.add_line(on_sel_id, 0, off_id, 0)
    device.add_line(off_id, 0, coeff_id, 0)
    device.add_line(on_sel_id, 1, on_bang_id, 0)
    device.add_line(on_bang_id, 0, f"type_b{i}", 0)

    device.add_line(f"freq_b{i}", 0, f"pak_b{i}", 1)
    device.add_line(f"freq_b{i}", 0, freq_pack_id, 0)
    device.add_line(f"freq_b{i}", 0, freq_store_id, 1)

    device.add_line(f"gain_b{i}", 0, f"pak_b{i}", 2)
    device.add_line(f"gain_b{i}", 0, gain_pack_id, 0)
    device.add_line(f"gain_b{i}", 0, gain_recalc_id, 0)
    device.add_line(gain_recalc_id, 0, freq_store_id, 0)
    device.add_line(gain_recalc_id, 1, gain_dbtoa_ctrl_id, 0)
    device.add_line(gain_dbtoa_ctrl_id, 0, coeff_id, 1)

    device.add_line(f"q_b{i}", 0, f"pak_b{i}", 3)
    device.add_line(f"q_b{i}", 0, q_pack_id, 0)
    device.add_line(f"q_b{i}", 0, q_recalc_id, 0)
    device.add_line(q_recalc_id, 0, freq_store_id, 0)
    device.add_line(q_recalc_id, 1, coeff_id, 2)

    device.add_line(f"type_b{i}", 0, f"pak_b{i}", 4)
    device.add_line(f"type_b{i}", 0, type_sel_id, 0)

    device.add_line(f"on_b{i}", 0, f"pak_b{i}", 5)
    device.add_line(f"on_b{i}", 0, on_sel_id, 0)
    device.add_line(f"motion_b{i}", 0, f"pak_b{i}", 6)
    device.add_line(f"dynamic_b{i}", 0, f"pak_b{i}", 7)
    device.add_line(f"dynamic_amt_b{i}", 0, f"pak_b{i}", 8)
    device.add_line(f"motion_rate_b{i}", 0, f"pak_b{i}", 9)
    device.add_line(f"motion_depth_b{i}", 0, f"pak_b{i}", 10)
    device.add_line(f"motion_direction_b{i}", 0, f"pak_b{i}", 11)

    device.add_line(f"motion_rate_b{i}", 0, motion_lfo_id, 0)
    device.add_line(f"motion_depth_b{i}", 0, motion_depth_expr_id, 0)
    device.add_line(f"motion_b{i}", 0, motion_depth_expr_id, 1)
    device.add_line(f"motion_direction_b{i}", 0, motion_depth_expr_id, 2)
    device.add_line(motion_depth_expr_id, 0, motion_depth_mul_id, 1)

    device.add_line(f"motion_depth_b{i}", 0, motion_gain_depth_expr_id, 0)
    device.add_line(f"motion_b{i}", 0, motion_gain_depth_expr_id, 1)
    device.add_line(f"motion_direction_b{i}", 0, motion_gain_depth_expr_id, 2)
    device.add_line(motion_gain_depth_expr_id, 0, motion_gain_mul_id, 1)

    return stage_result(
        {
            "coeff": coeff_id,
            "resamp": resamp_id,
            "biquad_l": biquads["l"],
            "biquad_r": biquads["r"],
            "freq_store": freq_store_id,
            "gain_recalc": gain_recalc_id,
            "q_recalc": q_recalc_id,
        },
        name="parametric_eq_band_backend",
        ports={
            "audio_in_l": biquads["l"].inlet(0),
            "audio_out_l": biquads["l"].outlet(0),
            "audio_in_r": biquads["r"].inlet(0),
            "audio_out_r": biquads["r"].outlet(0),
        },
        metadata={"band_index": band_index},
    )


def dry_wet_stage(device, id_prefix, dial_rect, x=30, y=30):
    """Add a dry/wet crossfade stage: live.dial (0-100) -> scaled mix.

    The dial outputs 0-100 percent, multiplied by 0.01 to get 0.0-1.0.
    A trigger fans the value to wet gain and an inverter for dry gain.
    Wire dry signal into {prefix}_dry_gain inlet 0,
    wet signal into {prefix}_wet_gain inlet 0,
    then sum {prefix}_dry_gain and {prefix}_wet_gain outputs.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        dial_rect: [x, y, w, h] for the dial in presentation mode.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "dial", "wet_gain", "dry_gain".
    """
    p = id_prefix

    dial_id = device.add_dial(
        f"{p}_dial", f"{p}_mix", dial_rect,
        min_val=0.0, max_val=100.0, initial=50.0,
        unitstyle=5, annotation_name=f"{p} Dry/Wet",
    )

    device.add_newobj(
        f"{p}_scale", "*~ 0.01", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y, 55, 20],
    )

    trig_id = device.add_newobj(
        f"{p}_trig", "t f f", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 30, 40, 20],
    )

    wet_smooth_boxes, wet_smooth_lines = param_smooth(f"{p}_wet_smooth")
    device.add_dsp(wet_smooth_boxes, wet_smooth_lines)

    dry_smooth_boxes, dry_smooth_lines = param_smooth(f"{p}_dry_smooth")
    device.add_dsp(dry_smooth_boxes, dry_smooth_lines)

    # !-~ 1. gives (1 - mix) for the dry side
    inv_id = device.add_newobj(
        f"{p}_inv", "!-~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 80, y + 30, 45, 20],
    )

    wet_gain_id = device.add_newobj(
        f"{p}_wet_gain", "*~ 0.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 90, 40, 20],
    )

    dry_gain_id = device.add_newobj(
        f"{p}_dry_gain", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 80, y + 90, 40, 20],
    )

    # Wiring: dial -> trig; trig fans to wet smooth and dry inverter
    # t f f fires outlet 1 first (dry/inv), then outlet 0 (wet)
    device.add_line(dial_id, 0, trig_id, 0)
    device.add_line(trig_id, 0, f"{p}_wet_smooth_pack", 0)
    device.add_line(f"{p}_wet_smooth_line", 0, wet_gain_id, 1)
    device.add_line(trig_id, 1, inv_id, 0)
    device.add_line(inv_id, 0, f"{p}_dry_smooth_pack", 0)
    device.add_line(f"{p}_dry_smooth_line", 0, dry_gain_id, 1)

    return stage_result(
        {"dial": dial_id, "wet_gain": wet_gain_id, "dry_gain": dry_gain_id},
        name="dry_wet_stage",
        params={"mix": device.parameter(dial_id)},
        ports={
            "wet_in": wet_gain_id.inlet(0),
            "dry_in": dry_gain_id.inlet(0),
            "wet_out": wet_gain_id.outlet(0),
            "dry_out": dry_gain_id.outlet(0),
        },
    )


def stereo_width_stage(device, id_prefix, dial_rect, x=30, y=30):
    """Add a mid/side stereo width control.

    A `width` dial scales the side (L-R) component: 0.0 collapses the image to
    mono, 1.0 leaves it unchanged, and up to 2.0 widens it. The signal is
    decomposed into mid = (L+R)/2 and side = (L-R)/2, the side is scaled by the
    smoothed width, then recombined as L = mid + side, R = mid - side.

    Wire the left/right inputs into the `audio_in_l`/`audio_in_r` ports and take
    the processed pair from `audio_out_l`/`audio_out_r`.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        dial_rect: [x, y, w, h] for the dial in presentation mode.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "dial", "in_l", "in_r", "mid", "side", "left", "right".
    """
    p = id_prefix

    dial_id = device.add_dial(
        f"{p}_dial", f"{p}_width", dial_rect,
        min_val=0.0, max_val=2.0, initial=1.0,
        unitstyle=0, annotation_name=f"{p} Width",
    )

    # Input fan: each channel feeds both the sum and difference objects.
    in_l_id = device.add_newobj(
        f"{p}_in_l", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y, 40, 20],
    )
    in_r_id = device.add_newobj(
        f"{p}_in_r", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 60, y, 40, 20],
    )

    # mid = (L + R) * 0.5 ; side = (L - R) * 0.5
    sum_id = device.add_newobj(
        f"{p}_sum", "+~", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 40, 40, 20],
    )
    diff_id = device.add_newobj(
        f"{p}_diff", "-~", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 60, y + 40, 40, 20],
    )
    mid_id = device.add_newobj(
        f"{p}_mid", "*~ 0.5", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 70, 40, 20],
    )
    side_id = device.add_newobj(
        f"{p}_side", "*~ 0.5", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 60, y + 70, 40, 20],
    )

    # Smooth the width dial, then scale the side component by it.
    smooth_boxes, smooth_lines = param_smooth(f"{p}_smooth")
    device.add_dsp(smooth_boxes, smooth_lines)
    side_gain_id = device.add_newobj(
        f"{p}_side_gain", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 60, y + 110, 40, 20],
    )

    # Recombine: L = mid + side_scaled ; R = mid - side_scaled
    left_id = device.add_newobj(
        f"{p}_left", "+~", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 150, 40, 20],
    )
    right_id = device.add_newobj(
        f"{p}_right", "-~", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 60, y + 150, 40, 20],
    )

    # Wiring: fan inputs into sum/diff
    device.add_line(in_l_id, 0, sum_id, 0)
    device.add_line(in_r_id, 0, sum_id, 1)
    device.add_line(in_l_id, 0, diff_id, 0)
    device.add_line(in_r_id, 0, diff_id, 1)
    # halve to get mid/side
    device.add_line(sum_id, 0, mid_id, 0)
    device.add_line(diff_id, 0, side_id, 0)
    # scale side by smoothed width
    device.add_line(side_id, 0, side_gain_id, 0)
    device.add_line(dial_id, 0, f"{p}_smooth_pack", 0)
    device.add_line(f"{p}_smooth_line", 0, side_gain_id, 1)
    # recombine into L/R
    device.add_line(mid_id, 0, left_id, 0)
    device.add_line(side_gain_id, 0, left_id, 1)
    device.add_line(mid_id, 0, right_id, 0)
    device.add_line(side_gain_id, 0, right_id, 1)

    return stage_result(
        {
            "dial": dial_id,
            "in_l": in_l_id,
            "in_r": in_r_id,
            "mid": mid_id,
            "side": side_id,
            "left": left_id,
            "right": right_id,
        },
        name="stereo_width_stage",
        params={"width": device.parameter(dial_id)},
        ports={
            "audio_in_l": in_l_id.inlet(0),
            "audio_in_r": in_r_id.inlet(0),
            "audio_out_l": left_id.outlet(0),
            "audio_out_r": right_id.outlet(0),
            "control_out": dial_id.outlet(0),
        },
    )


def tempo_synced_delay(device, id_prefix, time_dial_rect, feedback_dial_rect,
                       x=30, y=30):
    """Add a tempo-synced delay: two dials + tapin~/tapout~ with transport.

    Delay time dial controls the base delay in ms. Feedback dial controls
    how much of the output feeds back into the input (0-95%).
    Transport object provides BPM for tempo sync calculations.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        time_dial_rect: [x, y, w, h] for the time dial in presentation mode.
        feedback_dial_rect: [x, y, w, h] for the feedback dial.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "time_dial", "feedback_dial", "tapin", "tapout".
    """
    p = id_prefix

    time_dial_id = device.add_dial(
        f"{p}_time_dial", f"{p}_time", time_dial_rect,
        min_val=1.0, max_val=5000.0, initial=375.0,
        unitstyle=2, annotation_name=f"{p} Delay Time",
    )

    fb_dial_id = device.add_dial(
        f"{p}_fb_dial", f"{p}_feedback", feedback_dial_rect,
        min_val=0.0, max_val=95.0, initial=40.0,
        unitstyle=5, annotation_name=f"{p} Feedback",
    )

    delay_boxes, delay_lines = delay_line(f"{p}_delay", max_delay_ms=5000)
    device.add_dsp(delay_boxes, delay_lines)
    tapin_id = f"{p}_delay_tapin"
    tapout_id = f"{p}_delay_tapout"

    # [transport] is 2-in/9-out (bar, beat, units, resolution, tempo, timesig
    # list, state, raw ticks, clock sources) — the maxdiff-validated shape.
    transport_id = device.add_newobj(
        f"{p}_transport", "transport", numinlets=2, numoutlets=9,
        outlettype=["int", "int", "float", "float", "float", "", "int",
                    "float", ""],
        patching_rect=[x + 200, y, 70, 20],
    )

    loadbang_id = device.add_newobj(
        f"{p}_loadbang", "loadbang", numinlets=1, numoutlets=1,
        outlettype=["bang"], patching_rect=[x + 200, y - 30, 55, 20],
    )

    time_smooth_boxes, time_smooth_lines = param_smooth(f"{p}_time_smooth")
    device.add_dsp(time_smooth_boxes, time_smooth_lines)

    fb_scale_id = device.add_newobj(
        f"{p}_fb_scale", "scale 0. 95. 0. 0.95", numinlets=6, numoutlets=1,
        outlettype=[""], patching_rect=[x + 100, y + 60, 120, 20],
    )

    fb_smooth_boxes, fb_smooth_lines = param_smooth(f"{p}_fb_smooth")
    device.add_dsp(fb_smooth_boxes, fb_smooth_lines)

    fb_mul_id = device.add_newobj(
        f"{p}_fb_mul", "*~ 0.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 120, 40, 20],
    )

    sum_id = device.add_newobj(
        f"{p}_sum", "+~", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 150, 30, 20],
    )

    # Wiring: time dial -> smooth -> tapout~ delay time
    device.add_line(time_dial_id, 0, f"{p}_time_smooth_pack", 0)
    device.add_line(f"{p}_time_smooth_line", 0, tapout_id, 1)

    # Wiring: feedback dial -> scale -> smooth -> fb_mul inlet 1
    device.add_line(fb_dial_id, 0, fb_scale_id, 0)
    device.add_line(fb_scale_id, 0, f"{p}_fb_smooth_pack", 0)
    device.add_line(f"{p}_fb_smooth_line", 0, fb_mul_id, 1)

    # Wiring: tapout -> fb_mul -> sum inlet 1 (feedback loop)
    device.add_line(tapout_id, 0, fb_mul_id, 0)
    device.add_line(fb_mul_id, 0, sum_id, 1)

    # Wiring: sum -> tapin (input goes to sum inlet 0 externally)
    device.add_line(sum_id, 0, tapin_id, 0)

    # Wiring: loadbang -> transport
    device.add_line(loadbang_id, 0, transport_id, 0)

    return stage_result(
        {
            "time_dial": time_dial_id,
            "feedback_dial": fb_dial_id,
            "tapin": tapin_id,
            "tapout": tapout_id,
        },
        name="tempo_synced_delay",
        params={
            "time": device.parameter(time_dial_id),
            "feedback": device.parameter(fb_dial_id),
        },
        ports={
            "audio_in": device.box(tapin_id).inlet(0),
            "audio_out": device.box(tapout_id).outlet(0),
            "feedback_return": device.box(sum_id).inlet(1),
        },
    )


def midi_note_gate(device, id_prefix, x=30, y=30):
    """Add a MIDI note input stage: notein -> unpack -> stripnote -> kslider.

    Receives MIDI notes and unpacks pitch and velocity. stripnote filters
    out note-off messages. kslider provides a visual keyboard display.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "notein", "pitch", "velocity".
    """
    p = id_prefix

    notein_boxes, notein_lines = dsp_notein(p)
    device.add_dsp(notein_boxes, notein_lines)
    notein_id = f"{p}_notein"

    # stripnote passes pitch/velocity only when velocity > 0
    stripnote_id = device.add_newobj(
        f"{p}_stripnote", "stripnote", numinlets=2, numoutlets=2,
        outlettype=["int", "int"], patching_rect=[x, y + 30, 60, 20],
    )

    kslider_id = device.add_kslider(
        f"{p}_kslider", [x, y + 60, 200, 40],
    )

    device.add_line(notein_id, 0, stripnote_id, 0)
    device.add_line(notein_id, 1, stripnote_id, 1)
    device.add_line(stripnote_id, 0, kslider_id, 0)

    return stage_result(
        {
            "notein": notein_id,
            "pitch": stripnote_id,      # outlet 0
            "velocity": stripnote_id,   # outlet 1
        },
        name="midi_note_gate",
        ports={
            "note_in": device.box(notein_id).outlet(0),
            "pitch_out": stripnote_id.outlet(0),
            "velocity_out": stripnote_id.outlet(1),
        },
    )


def convolver_controlled_stage(device, id_prefix, dial_rect, x=30, y=30):
    """Add a convolver with dry/wet mix controlled by a dial.

    Creates a convolve~ for the impulse response and a dry/wet crossfade.
    The dial controls the wet amount (0-100%).

    Wire audio into {prefix}_conv inlet 0 and {prefix}_dry_gain inlet 0.
    Output by summing {prefix}_wet_gain and {prefix}_dry_gain outputs.

    Returns:
        dict with keys "dial", "convolver", "wet".
    """
    p = id_prefix

    conv_boxes, conv_lines = convolver(f"{p}_conv", ir_buffer=f"{p}_ir")
    device.add_dsp(conv_boxes, conv_lines)
    conv_id = f"{p}_conv_conv"

    dial_id = device.add_dial(
        f"{p}_dial", f"{p}_wet", dial_rect,
        min_val=0.0, max_val=100.0, initial=50.0,
        unitstyle=5, annotation_name=f"{p} Wet",
    )

    trig_id = device.add_newobj(
        f"{p}_trig", "t f f", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y, 40, 20],
    )

    wet_smooth_boxes, wet_smooth_lines = param_smooth(f"{p}_wet_smooth")
    device.add_dsp(wet_smooth_boxes, wet_smooth_lines)

    dry_smooth_boxes, dry_smooth_lines = param_smooth(f"{p}_dry_smooth")
    device.add_dsp(dry_smooth_boxes, dry_smooth_lines)

    inv_id = device.add_newobj(
        f"{p}_inv", "!-~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 80, y + 30, 45, 20],
    )

    wet_gain_id = device.add_newobj(
        f"{p}_wet_gain", "*~ 0.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 60, 40, 20],
    )

    dry_gain_id = device.add_newobj(
        f"{p}_dry_gain", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 80, y + 60, 40, 20],
    )

    # dial -> trig; trig fans to wet smooth and dry inverter
    device.add_line(dial_id, 0, trig_id, 0)
    device.add_line(trig_id, 0, f"{p}_wet_smooth_pack", 0)
    device.add_line(f"{p}_wet_smooth_line", 0, wet_gain_id, 1)
    device.add_line(trig_id, 1, inv_id, 0)
    device.add_line(inv_id, 0, f"{p}_dry_smooth_pack", 0)
    device.add_line(f"{p}_dry_smooth_line", 0, dry_gain_id, 1)

    # convolver output -> wet gain
    device.add_line(conv_id, 0, wet_gain_id, 0)

    return stage_result(
        {"dial": dial_id, "convolver": conv_id, "wet": wet_gain_id},
        name="convolver_controlled_stage",
        params={"wet": device.parameter(dial_id)},
        ports={
            "audio_in": device.box(conv_id).inlet(0),
            "wet_in": wet_gain_id.inlet(0),
            "wet_out": wet_gain_id.outlet(0),
            "dry_in": dry_gain_id.inlet(0),
            "dry_out": dry_gain_id.outlet(0),
        },
    )


def sidechain_compressor_recipe(device, id_prefix, threshold_rect,
                                ratio_rect, x=30, y=30):
    """Add a sidechain compressor with threshold and ratio dials.

    Creates sidechain routing (plugin~ with external input), a compressor,
    and a jsui sidechain display. Two dials control threshold and ratio.

    Returns:
        dict with keys "threshold_dial", "ratio_dial", "sidechain", "compressor".
    """
    p = id_prefix

    sc_boxes, sc_lines = sidechain_routing(f"{p}_sc")
    device.add_dsp(sc_boxes, sc_lines)
    sc_id = f"{p}_sc_plugin"

    comp_boxes, comp_lines = compressor(f"{p}_comp")
    device.add_dsp(comp_boxes, comp_lines)

    device.add_jsui(
        f"{p}_display", [x, y + 120, 120, 60],
        js_code=sidechain_display_js(),
        numinlets=SIDECHAIN_DISPLAY_INLETS,
    )

    threshold_dial_id = device.add_dial(
        f"{p}_thresh_dial", f"{p}_threshold", threshold_rect,
        min_val=-60.0, max_val=0.0, initial=-20.0,
        unitstyle=4, annotation_name=f"{p} Threshold",
    )

    ratio_dial_id = device.add_dial(
        f"{p}_ratio_dial", f"{p}_ratio", ratio_rect,
        min_val=1.0, max_val=20.0, initial=4.0,
        unitstyle=1, annotation_name=f"{p} Ratio",
    )

    # threshold dial -> compressor threshold inlets (both channels)
    device.add_line(threshold_dial_id, 0, f"{p}_comp_thresh_l", 1)
    device.add_line(threshold_dial_id, 0, f"{p}_comp_thresh_r", 1)

    # ratio dial -> compressor ratio inlets (both channels)
    device.add_line(ratio_dial_id, 0, f"{p}_comp_ratio_l", 1)
    device.add_line(ratio_dial_id, 0, f"{p}_comp_ratio_r", 1)

    return stage_result(
        {
            "threshold_dial": threshold_dial_id,
            "ratio_dial": ratio_dial_id,
            "sidechain": sc_id,
            "compressor": f"{p}_comp_out_l",
        },
        name="sidechain_compressor_recipe",
        params={
            "threshold": device.parameter(threshold_dial_id),
            "ratio": device.parameter(ratio_dial_id),
        },
        ports={
            "sidechain_in": device.box(sc_id).outlet(0),
            "audio_out": device.box(f"{p}_comp_out_l").outlet(0),
        },
    )


def lfo_matrix_distribute(device, id_prefix, targets=4, x=30, y=30):
    """Fan one LFO output to multiple depth-scaled targets.

    Creates a single LFO and N *~ depth cells, each with its own dial
    (0-100%). Useful for modulating several parameters from one source.

    Returns:
        dict with keys "lfo" and "depth_dials" (list of dial IDs).
    """
    p = id_prefix

    lfo_boxes, lfo_lines = lfo(f"{p}_lfo")
    device.add_dsp(lfo_boxes, lfo_lines)
    lfo_out = f"{p}_lfo_depth"

    depth_dials = []
    for i in range(targets):
        dial_id = device.add_dial(
            f"{p}_depth_{i}_dial", f"{p}_depth_{i}", [x + i * 50, y, 40, 40],
            min_val=0.0, max_val=100.0, initial=50.0,
            unitstyle=5, annotation_name=f"{p} Depth {i}",
        )

        scale_id = device.add_newobj(
            f"{p}_depth_{i}_scale", "*~ 0.01", numinlets=2, numoutlets=1,
            outlettype=["signal"], patching_rect=[x + i * 80, y + 60, 55, 20],
        )

        mul_id = device.add_newobj(
            f"{p}_depth_{i}_mul", "*~", numinlets=2, numoutlets=1,
            outlettype=["signal"],
            patching_rect=[x + i * 80, y + 90, 30, 20],
        )

        device.add_line(lfo_out, 0, mul_id, 0)
        device.add_line(dial_id, 0, scale_id, 0)
        device.add_line(scale_id, 0, mul_id, 1)

        depth_dials.append(dial_id)

    return stage_result(
        {"lfo": lfo_out, "depth_dials": depth_dials},
        name="lfo_matrix_distribute",
        params={
            f"depth_{i}": device.parameter(dial_id)
            for i, dial_id in enumerate(depth_dials)
        },
        ports={
            "lfo_out": device.box(lfo_out).outlet(0),
        },
    )


def spectral_gate_stage(device, id_prefix, threshold_rect, x=30, y=30):
    """Add a spectral gate with threshold dial and spectral display.

    Creates a pfft~-based spectral gate, its subpatcher data, a threshold
    dial, and a jsui spectral display.

    Wire audio into {prefix}_gate_pfft inlet 0.
    Output from {prefix}_gate_pfft outlet 0.

    Returns:
        dict with keys "threshold_dial", "gate", "display".
    """
    p = id_prefix

    gate_boxes, gate_lines = spectral_gate(f"{p}_gate")
    device.add_dsp(gate_boxes, gate_lines)
    gate_id = f"{p}_gate_pfft"

    threshold_dial_id = device.add_dial(
        f"{p}_thresh_dial", f"{p}_threshold", threshold_rect,
        min_val=0.0, max_val=1.0, initial=0.01,
        unitstyle=1, annotation_name=f"{p} Threshold",
    )

    display_id = device.add_jsui(
        f"{p}_display", [x, y + 60, 120, 60],
        js_code=spectral_display_js(),
        numinlets=SPECTRAL_DISPLAY_INLETS,
    )

    # threshold dial -> pfft~ inlet 1
    device.add_line(threshold_dial_id, 0, gate_id, 1)

    return stage_result(
        {
            "threshold_dial": threshold_dial_id,
            "gate": gate_id,
            "display": display_id,
        },
        name="spectral_gate_stage",
        params={"threshold": device.parameter(threshold_dial_id)},
        ports={
            "audio_in": device.box(gate_id).inlet(0),
            "audio_out": device.box(gate_id).outlet(0),
        },
        assets=[f"{p}_gate_sub"],
    )


def arpeggio_quantized_stage(device, id_prefix, x=30, y=30):
    """Add an arpeggiator followed by pitch quantization.

    Creates an arpeggiator (up mode) wired into a pitch quantizer (chromatic).
    Wire chord notes into {prefix}_arp_arp inlet 0.
    Output quantized pitch from {prefix}_quant_scale outlet 0.

    Returns:
        dict with keys "arpeggiator" and "quantizer".
    """
    p = id_prefix

    arp_boxes, arp_lines = arpeggiator(f"{p}_arp")
    device.add_dsp(arp_boxes, arp_lines)
    arp_id = f"{p}_arp_arp"

    quant_boxes, quant_lines = pitch_quantize(f"{p}_quant")
    device.add_dsp(quant_boxes, quant_lines)
    quant_id = f"{p}_quant_scale"

    # arpeggiator pitch output -> quantizer
    device.add_line(f"{p}_arp_make", 0, quant_id, 0)

    return stage_result(
        {"arpeggiator": arp_id, "quantizer": quant_id},
        name="arpeggio_quantized_stage",
        ports={
            "note_in": device.box(arp_id).inlet(0),
            "pitch_out": device.box(quant_id).outlet(0),
        },
    )


def grain_playback_controlled(device, id_prefix, buf_name, x=30, y=30):
    """Add a granular playback stage with position, size, and density dials.

    Creates a grain cloud with its buffer and three control dials.
    Position controls playback position in the buffer (0-100%).
    Size controls grain size. Density controls grain firing rate.

    Returns:
        dict with keys "grain" and "buffer".
    """
    p = id_prefix

    grain_boxes, grain_lines = grain_cloud(f"{p}_grain", buf_name)
    device.add_dsp(grain_boxes, grain_lines)
    grain_id = f"{p}_grain_buf"
    buf_id = f"{p}_grain_buf"

    pos_dial_id = device.add_dial(
        f"{p}_pos_dial", f"{p}_position", [x, y, 40, 40],
        min_val=0.0, max_val=100.0, initial=0.0,
        unitstyle=5, annotation_name=f"{p} Position",
    )

    size_dial_id = device.add_dial(
        f"{p}_size_dial", f"{p}_size", [x + 50, y, 40, 40],
        min_val=1.0, max_val=500.0, initial=50.0,
        unitstyle=2, annotation_name=f"{p} Size",
    )

    density_dial_id = device.add_dial(
        f"{p}_density_dial", f"{p}_density", [x + 100, y, 40, 40],
        min_val=1.0, max_val=100.0, initial=20.0,
        unitstyle=1, annotation_name=f"{p} Density",
    )

    return stage_result(
        {"grain": grain_id, "buffer": buf_id},
        name="grain_playback_controlled",
        params={
            "position": device.parameter(pos_dial_id),
            "size": device.parameter(size_dial_id),
            "density": device.parameter(density_dial_id),
        },
        ports={
            "buffer": device.box(buf_id).outlet(0),
            "grain_out": device.box(grain_id).outlet(0),
        },
    )


def poly_midi_gate(device, id_prefix, x=30, y=30):
    """Add a polyphonic MIDI input stage: notein -> velocity curve -> poly~.

    Creates a notein for MIDI, a velocity curve for shaping, and a poly~
    voice allocator. Wire poly~ output to your synth voice subpatcher.

    Returns:
        dict with keys "voices", "velocity_curve", "notein".
    """
    p = id_prefix

    notein_boxes, notein_lines = dsp_notein(f"{p}_note")
    device.add_dsp(notein_boxes, notein_lines)
    notein_id = f"{p}_note_notein"

    vel_boxes, vel_lines = velocity_curve(f"{p}_vel")
    device.add_dsp(vel_boxes, vel_lines)
    vel_id = f"{p}_vel_clip"

    poly_boxes, poly_lines = poly_voices(f"{p}_poly")
    device.add_dsp(poly_boxes, poly_lines)
    poly_id = f"{p}_poly_poly"

    # notein pitch -> poly inlet 0
    device.add_line(notein_id, 0, poly_id, 0)
    # notein velocity -> velocity curve -> poly inlet 1
    device.add_line(notein_id, 1, vel_id, 0)
    device.add_line(vel_id, 0, poly_id, 1)

    return stage_result(
        {
            "voices": poly_id,
            "velocity_curve": vel_id,
            "notein": notein_id,
        },
        name="poly_midi_gate",
        ports={
            "note_in": device.box(notein_id).outlet(0),
            "velocity_in": device.box(notein_id).outlet(1),
            "voice_out": device.box(poly_id).outlet(0),
        },
    )


def mc_poly_spine(device, id_prefix, *, voices=16, gen_name=None, gen_inlets=2,
                  mpe=False, steal=True, autogain=False, x=30, y=30):
    """Add the modern ``mc.*`` polyphony spine — the poly~-free voice allocator
    that Superberry (``@voices 16``) and Chiral (``@mpemode 1 @voices 8 @steal 1``)
    both use. Topology + port indices are VERBATIM from those devices.

    Builds and wires::

        midiin -> midiparse[7] -> mc.noteallocator~ @voices N [@mpemode 1] [@steal 1]
        mc.noteallocator~[0] (note list) -> unpack -> pitch mc.target -> mc.gen~[1]
        mc.noteallocator~[5] (voice index) -> pitch mc.target[1]
        mc.click~ @chans N -> mc.gen~[0]                  (per-voice trigger)
        mc.gen~[0] -> mc.noteallocator~[0]                (voice-active feedback / steal)
        mc.gen~[1] -> mc.mixdown~ 1 [@autogain 0] -> mc.unpack~ 1   (summed audio)

    The per-voice DSP is supplied as a ``.gendsp`` (``gen_name``, built with
    :func:`m4l_builder.gen_patcher.build_gendsp`) loaded by ``mc.gen~``; that gen
    voice should read its trigger on ``in 1`` and pitch on ``in 2``, and write its
    audio on ``out 1`` and a voice-active flag on ``out 2`` (the steal feedback).
    Attach further per-voice controls (velocity, MPE pressure/slide) with extra
    ``mc.target`` objects fed by the exposed ``note_out`` / ``voice_index_out``
    ports.

    Args:
        voices: polyphony (``@voices``/``@chans``).
        gen_name: basename of the ``.gendsp`` the ``mc.gen~`` loads (None = bare).
        gen_inlets: inlet count of the gen voice (>=2: trigger + pitch).
        mpe: emit ``@mpemode 1`` on the noteallocator (Chiral path).
        steal: emit ``@steal 1`` (voice stealing).
        autogain: ``@autogain 1`` on the mixdown (default 0, like Superberry).

    Returns:
        StageResult with the spine IDs and ports (``note_out``, ``voice_index_out``,
        ``trigger_out``, ``audio_out``, ``gen``).
    """
    p = id_prefix
    na_attrs = f"@voices {voices}"
    if mpe:
        na_attrs = f"@mpemode 1 {na_attrs}"
    if steal:
        na_attrs += " @steal 1"
    gen_text = f"mc.gen~ {gen_name} @chans {voices}" if gen_name else f"mc.gen~ @chans {voices}"

    midiin_id = device.add_newobj(
        f"{p}_midiin", "midiin", numinlets=1, numoutlets=1,
        outlettype=["int"], patching_rect=[x, y, 60, 20],
    )
    midiparse_id = device.add_newobj(
        f"{p}_midiparse", "midiparse", numinlets=1, numoutlets=8,
        outlettype=["", "", "", "int", "int", "", "int", ""],
        patching_rect=[x, y + 30, 120, 20],
    )
    na_id = device.add_newobj(
        f"{p}_noteallocator", f"mc.noteallocator~ {na_attrs}",
        numinlets=1, numoutlets=6,
        outlettype=["list", "list", "int", "int", "int", "int"],
        patching_rect=[x, y + 60, 180, 20],
    )
    unpack_id = device.add_newobj(
        f"{p}_note_unpack", "unpack 0 0", numinlets=1, numoutlets=2,
        outlettype=["int", "int"], patching_rect=[x, y + 90, 70, 20],
    )
    pitch_target_id = device.add_newobj(
        f"{p}_pitch_target", "mc.target", numinlets=2, numoutlets=2,
        outlettype=["setvalue", "int"], patching_rect=[x, y + 120, 70, 20],
    )
    click_id = device.add_newobj(
        f"{p}_click", f"mc.click~ @chans {voices}", numinlets=1, numoutlets=1,
        outlettype=["multichannelsignal"], patching_rect=[x + 200, y + 90, 120, 20],
    )
    gen_id = device.add_newobj(
        f"{p}_gen", gen_text, numinlets=max(2, gen_inlets), numoutlets=2,
        outlettype=["multichannelsignal", "multichannelsignal"],
        patching_rect=[x, y + 160, 200, 20],
    )
    mixdown_id = device.add_newobj(
        f"{p}_mixdown", f"mc.mixdown~ 1 @autogain {1 if autogain else 0}",
        numinlets=2, numoutlets=1, outlettype=["multichannelsignal"],
        patching_rect=[x, y + 200, 160, 20],
    )
    unpack_audio_id = device.add_newobj(
        f"{p}_audio_unpack", "mc.unpack~ 1", numinlets=1, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 230, 100, 20],
    )

    # MIDI front end -> allocator (raw MIDI on midiparse outlet 7, verbatim).
    device.add_line(midiin_id, 0, midiparse_id, 0)
    device.add_line(midiparse_id, 7, na_id, 0)
    # note list -> unpack pitch -> pitch target (value) ; voice index -> target right.
    device.add_line(na_id, 0, unpack_id, 0)
    device.add_line(unpack_id, 0, pitch_target_id, 0)
    device.add_line(na_id, 5, pitch_target_id, 1)
    device.add_line(pitch_target_id, 0, gen_id, 1)
    # per-voice trigger.
    device.add_line(click_id, 0, gen_id, 0)
    # voice-active feedback (gen outlet 0 -> allocator inlet 0) — enables stealing.
    device.add_line(gen_id, 0, na_id, 0)
    # summed audio path.
    device.add_line(gen_id, 1, mixdown_id, 0)
    device.add_line(mixdown_id, 0, unpack_audio_id, 0)

    return stage_result(
        {
            "noteallocator": na_id,
            "click": click_id,
            "gen": gen_id,
            "mixdown": mixdown_id,
            "audio_unpack": unpack_audio_id,
        },
        name="mc_poly_spine",
        ports={
            "note_out": device.box(na_id).outlet(0),
            "voice_index_out": device.box(na_id).outlet(5),
            "trigger_out": device.box(click_id).outlet(0),
            "audio_out": device.box(unpack_audio_id).outlet(0),
            "gen": device.box(gen_id).outlet(1),
        },
    )


def transport_sync_lfo_recipe(device, id_prefix, x=30, y=30):
    """Add a transport-synced LFO with depth dial and division menu.

    Creates a transport LFO, a depth dial (0-100%), and a umenu for
    selecting beat division (1/4, 1/8, 1/16, 1/32).

    Returns:
        dict with keys "lfo", "depth_dial", "division_menu".
    """
    p = id_prefix

    lfo_boxes, lfo_lines = transport_lfo(f"{p}_lfo")
    device.add_dsp(lfo_boxes, lfo_lines)
    lfo_id = f"{p}_lfo_osc"

    depth_dial_id = device.add_dial(
        f"{p}_depth_dial", f"{p}_depth", [x, y, 40, 40],
        min_val=0.0, max_val=100.0, initial=50.0,
        unitstyle=5, annotation_name=f"{p} Depth",
    )

    depth_mul_id = device.add_newobj(
        f"{p}_depth_mul", "*~ 0.01", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 60, 55, 20],
    )

    menu_id = device.add_umenu(
        f"{p}_div_menu", [x + 60, y, 60, 20],
        items=["1/4", "1/8", "1/16", "1/32"],
    )

    device.add_line(depth_dial_id, 0, depth_mul_id, 0)
    device.add_line(lfo_id, 0, depth_mul_id, 1)

    return stage_result(
        {
            "lfo": lfo_id,
            "depth_dial": depth_dial_id,
            "division_menu": menu_id,
        },
        name="transport_sync_lfo_recipe",
        params={"depth": device.parameter(depth_dial_id)},
        ports={
            "lfo_out": device.box(depth_mul_id).outlet(0),
            "division_select": menu_id.outlet(0),
        },
    )


def beat_phase_gate(device, id_prefix="bpg", *, x=30, y=30):
    """Transport beat-phase source (Q3 framework recipe) built on
    ``plugsync~`` — the M4L-native transport reporter (scheduler-rate, no
    LiveAPI round-trip; corpus precedent: Roulette / Superberry).

    Derives four message-rate signals every tempo-synced device builds on:

    * ``phase``        — beat phase 0..1 (0 = the beat), straight off
                         plugsync~ outlet 3
    * ``gate``         — ONE bang exactly when the beat-in-bar increments
    * ``running``      — transport running 0/1 (drive a "SYNC OFF" cue;
                         plugsync~ holds stale values while stopped)
    * ``tempo``        — BPM float (replaces the heavier live.observer
                         chain when a device only needs tempo)
    * ``half_beat_ms`` — 30000/BPM, the classic swing unit: multiply by a
                         swing amount + your off-beat mask downstream

    plugsync~ outlet map — LIVE-PROBED 2026-07-03 (tools/probe_plugsync.py;
    the Max-docs/corpus-inferred map was WRONG — outlet 5 is tempo, not
    beats): 0 running(int) · 1 elapsed ms(int) · 2 beat-in-bar(int, 1-based)
    · 3 BEAT PHASE 0..1(float) · 4 [bar beat unit] list · 5 tempo BPM(float)
    · 6/7 large tick/sample counters · 8 bar number(int).

    Returns a stage_result whose ports expose ``phase`` / ``gate`` /
    ``running`` / ``tempo`` / ``half_beat_ms``.
    """
    p = id_prefix
    sync_id = device.add_newobj(
        f"{p}_sync", "plugsync~", numinlets=1, numoutlets=9,
        outlettype=["int", "int", "int", "float", "list",
                    "float", "float", "int", "int"],
        patching_rect=[x, y, 120, 22])
    # Beat gate: bang once per beat — the 1-based beat-in-bar (outlet 2)
    # changes exactly at each beat crossing (change -> t b dedupes).
    change_id = device.add_newobj(
        f"{p}_change", "change", numinlets=1, numoutlets=3,
        outlettype=["", "int", "int"], patching_rect=[x + 160, y + 30, 60, 20])
    gate_id = device.add_newobj(
        f"{p}_gate", "t b", numinlets=1, numoutlets=1,
        outlettype=["bang"], patching_rect=[x + 160, y + 60, 40, 20])
    device.add_line(sync_id, 2, change_id, 0)
    device.add_line(change_id, 0, gate_id, 0)
    # Swing unit: half a beat in ms at the current tempo.
    halfbeat_id = device.add_newobj(
        f"{p}_halfbeat", "expr 30000. / $f1", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[x + 280, y + 30, 110, 20])
    device.add_line(sync_id, 5, halfbeat_id, 0)
    return stage_result(
        {
            "sync": sync_id,
            "gate": gate_id,
            "halfbeat": halfbeat_id,
        },
        name="beat_phase_gate",
        ports={
            "phase": device.box(f"{p}_sync").outlet(3),
            "gate": device.box(f"{p}_gate").outlet(0),
            "running": device.box(f"{p}_sync").outlet(0),
            "tempo": device.box(f"{p}_sync").outlet(5),
            "half_beat_ms": device.box(f"{p}_halfbeat").outlet(0),
        },
    )


def midi_learn_macro_assignment(device, id_prefix, num_targets=4, x=30, y=30):
    """Add a MIDI learn chain with macro mappings for multiple targets.

    Creates a midi_learn_chain and N macromap instances, one per target.
    Each macromap connects the learned parameter to a Live macro knob.

    Returns:
        dict with keys "learn_chain" and "macromaps" (list of IDs).
    """
    p = id_prefix

    learn_boxes, learn_lines = midi_learn_chain(f"{p}_learn", f"{p}_param")
    device.add_dsp(learn_boxes, learn_lines)
    learn_id = f"{p}_learn_ctlin"

    macro_ids = []
    for i in range(num_targets):
        mm_boxes, mm_lines = macromap(f"{p}_mm_{i}", f"{p}_target_{i}",
                                      macro_num=i + 1)
        device.add_dsp(mm_boxes, mm_lines)
        macro_ids.append(f"{p}_mm_{i}_remote")

    return stage_result(
        {"learn_chain": learn_id, "macromaps": macro_ids},
        name="midi_learn_macro_assignment",
        ports={
            "learn_in": device.box(learn_id).outlet(0),
        },
    )


def generative_midi_stage(device, id_prefix, rate_rect, density_rect, *,
                          x=30, y=30, low=48, high=72, scale="major"):
    """Add a self-contained generative MIDI note generator.

    A metro (rate dial, ms) drives a probability gate (density dial, %); on each
    hit a random pitch in [low, high] is drawn, quantized to `scale`, and played
    through makenote -> noteout. The {prefix}_enable toggle starts/stops the
    clock. Drop this into a MidiEffect or Instrument device.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        rate_rect: [x, y, w, h] for the rate dial (presentation mode).
        density_rect: [x, y, w, h] for the density dial (presentation mode).
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.
        low, high: Inclusive MIDI pitch range for generated notes.
        scale: Scale for pitch_quantize (chromatic/major/minor/pentatonic/dorian).

    Returns:
        dict with keys "enable", "rate", "density", "metro", "make", "noteout".
    """
    p = id_prefix

    enable_id = device.add_toggle(
        f"{p}_enable", f"{p}_enable",
        [rate_rect[0], rate_rect[1] - 24, 20, 20],
    )
    rate_id = device.add_dial(
        f"{p}_rate", f"{p}_rate", rate_rect,
        min_val=20.0, max_val=1000.0, initial=250.0,
        unitstyle=0, annotation_name=f"{p} Rate",
    )
    density_id = device.add_dial(
        f"{p}_density", f"{p}_density", density_rect,
        min_val=0.0, max_val=100.0, initial=70.0,
        unitstyle=5, annotation_name=f"{p} Density",
    )

    metro_id = device.add_newobj(
        f"{p}_metro", "metro 250", numinlets=2, numoutlets=1,
        outlettype=["bang"], patching_rect=[x, y, 70, 20],
    )
    # density% (0-100) -> 0-1000 threshold for the probability gate
    dens_scale_id = device.add_newobj(
        f"{p}_dens", "* 10", numinlets=2, numoutlets=1,
        outlettype=["int"], patching_rect=[x + 180, y, 50, 20],
    )

    gate_boxes, gate_lines = probability_gate(f"{p}_gate", probability=0.7)
    device.add_dsp(gate_boxes, gate_lines)
    note_boxes, note_lines = random_note(f"{p}_note", low=low, high=high)
    device.add_dsp(note_boxes, note_lines)
    quant_boxes, quant_lines = pitch_quantize(f"{p}_quant", scale=scale)
    device.add_dsp(quant_boxes, quant_lines)
    out_boxes, out_lines = noteout(f"{p}_out")
    device.add_dsp(out_boxes, out_lines)

    make_id = device.add_newobj(
        f"{p}_make", "makenote 100 200", numinlets=3, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 240, 100, 20],
    )

    # Clock + density control
    device.add_line(enable_id, 0, metro_id, 0)
    device.add_line(rate_id, 0, metro_id, 1)
    device.add_line(density_id, 0, dens_scale_id, 0)
    device.add_line(dens_scale_id, 0, f"{p}_gate_thresh", 1)
    # Generative chain: clock -> gate -> random pitch -> quantize -> makenote -> noteout
    device.add_line(metro_id, 0, f"{p}_gate_gate", 0)
    device.add_line(f"{p}_gate_sel", 0, f"{p}_note_rand", 0)
    device.add_line(f"{p}_note_offset", 0, f"{p}_quant_scale", 0)
    device.add_line(f"{p}_quant_scale", 0, make_id, 0)
    device.add_line(make_id, 0, f"{p}_out_noteout", 0)
    device.add_line(make_id, 1, f"{p}_out_noteout", 1)

    return stage_result(
        {
            "enable": enable_id,
            "rate": rate_id,
            "density": density_id,
            "metro": metro_id,
            "make": make_id,
            "noteout": f"{p}_out_noteout",
        },
        name="generative_midi_stage",
        params={"rate": device.parameter(rate_id), "density": device.parameter(density_id)},
    )


def euclidean_sequencer_stage(device, id_prefix, rate_rect, *, steps=16, pulses=4,
                              note=60, x=30, y=30):
    """Add a Euclidean rhythm MIDI sequencer.

    Wraps `euclidean_rhythm` into a complete stage: an enable toggle and a
    step-time dial drive `pulses` hits spread over `steps`, each firing a fixed
    `note` through makenote -> noteout. Drop into a MidiEffect or Instrument.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        rate_rect: [x, y, w, h] for the step-time dial (presentation mode).
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.
        steps, pulses: Euclidean pattern parameters (pulses hits over steps).
        note: MIDI pitch fired on each hit.

    Returns:
        dict with keys "enable", "rate", "hit", "make", "noteout".
    """
    p = id_prefix
    enable_id = device.add_toggle(
        f"{p}_enable", f"{p}_enable", [rate_rect[0], rate_rect[1] - 24, 20, 20]
    )
    rate_id = device.add_dial(
        f"{p}_rate", f"{p}_rate", rate_rect,
        min_val=30.0, max_val=500.0, initial=125.0,
        unitstyle=0, annotation_name=f"{p} Step ms",
    )

    device.add_dsp(*euclidean_rhythm(f"{p}_euc", steps=steps, pulses=pulses))
    device.add_newobj(f"{p}_note", f"t {note}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[x, y + 150, 50, 20])
    make_id = device.add_newobj(
        f"{p}_make", "makenote 100 200", numinlets=3, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 180, 100, 20],
    )
    device.add_dsp(*noteout(f"{p}_out"))

    device.add_line(enable_id, 0, f"{p}_euc_metro", 0)
    device.add_line(rate_id, 0, f"{p}_euc_metro", 1)
    device.add_line(f"{p}_euc_hit", 0, f"{p}_note", 0)
    device.add_line(f"{p}_note", 0, make_id, 0)
    device.add_line(make_id, 0, f"{p}_out_noteout", 0)
    device.add_line(make_id, 1, f"{p}_out_noteout", 1)

    return stage_result(
        {
            "enable": enable_id,
            "rate": rate_id,
            "hit": f"{p}_euc_hit",
            "make": make_id,
            "noteout": f"{p}_out_noteout",
        },
        name="euclidean_sequencer_stage",
        params={"rate": device.parameter(rate_id)},
    )


def sample_drop_target(device, id_prefix, buffer_box_id, drop_rect, *,
                       settle_ms=600, x=600, y=520, param_name=None,
                       textcolor=None, bgcolor=None, bordercolor=None):
    """Add a drag-and-drop audio sample intake over ``drop_rect``.

    Uses ``live.drop`` (NOT ``dropfile``) so the target accepts samples dragged
    from BOTH Ableton's own browser AND the Finder. ``dropfile`` only catches
    Finder drops, which is the usual reason "drag a sample onto the device"
    silently fails inside Live.

    The dropped file path is sent to the *existing* ``buffer~`` (box id
    ``buffer_box_id``) via ``prepend replace``. ``buffer~`` reads
    asynchronously and its own read-complete bang fires before the samples are
    in memory, so a ``delay {settle_ms}`` gives the reliable "now it's loaded"
    bang on ``{prefix}_loaded`` outlet 0 — wire that to your display/analysis
    redraw.

    Place a ``buffer~ <name>`` in the device yourself (DSP recipes such as
    ``slice_pool`` own the shared buffer) and pass its box id here.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        buffer_box_id: Box id of the existing ``buffer~`` to load into.
        drop_rect: [x, y, w, h] presentation rect for the (transparent) drop
            target — overlay it on the hero/waveform display.
        settle_ms: Delay after a drop before the "loaded" bang fires.
        x, y: Patching-canvas offset for the (off-presentation) plumbing.
        textcolor, bgcolor, bordercolor: optional ``live.drop`` colors.

    Returns:
        StageResult with ids ``{"drop", "trig", "replace", "loaded"}``. Wire
        ``loaded`` outlet 0 to your redraw/analysis trigger(s).
    """
    p = id_prefix

    # param_name registers the drop as a stored Blob parameter (widget-
    # hardening spec): the dropped path survives save/reload + duplicate and
    # re-reports on init, so the buffer refills without user action.
    drop_id = device.add_box(live_drop(
        f"{p}_drop", drop_rect, param_name=param_name,
        patching_rect=[x, y, 120, 28],
        textcolor=textcolor, bgcolor=bgcolor, bordercolor=bordercolor,
    ))
    trig_id = device.add_newobj(
        f"{p}_trig", "t b l", numinlets=1, numoutlets=2,
        outlettype=["bang", ""], patching_rect=[x, y + 34, 60, 20],
    )
    replace_id = device.add_newobj(
        f"{p}_replace", "prepend replace", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[x + 70, y + 34, 130, 20],
    )
    loaded_id = device.add_newobj(
        f"{p}_loaded", f"delay {settle_ms}", numinlets=2, numoutlets=1,
        outlettype=["bang"], patching_rect=[x, y + 64, 80, 20],
    )

    # live.drop path -> split: path replaces the buffer, bang starts the settle.
    device.add_line(drop_id, 0, trig_id, 0)
    device.add_line(trig_id, 1, replace_id, 0)
    device.add_line(replace_id, 0, buffer_box_id, 0)
    device.add_line(trig_id, 0, loaded_id, 0)

    return stage_result(
        {
            "drop": drop_id,
            "trig": trig_id,
            "replace": replace_id,
            "loaded": loaded_id,
        },
        name="sample_drop_target",
    )


def two_panel_strip(device, id_prefix, *, main_width=174, side_width=56, height=167,
                    gap=2, bgcolor=None, side_bgcolor=None, border=1,
                    bordercolor=None, rounded=0):
    """Two-panel channel-strip SHELL — the SABROI AS Console grammar: a wide MAIN
    panel for the primary controls + a narrow SIDE column for toggles/meters.

    Geometry is grounded in AS_Console_Norm: main panel ``[0,0,174,167]`` + side
    panel ``[176,0,55,167]`` (gap 2). The device width should be
    ``main_width + gap + side_width`` (231 by default). Fill the panels with
    :func:`dial_label_cell` cells, a DSP module via
    ``device.add_bpatcher_module`` (F3), side-column toggles, etc.; re-tint the
    whole frame at runtime with ``device.add_theme_bus`` (B1).

    Build-time ``bgcolor`` / ``side_bgcolor`` are placeholders (the theme bus wins
    when ``follow_live``). Returns a StageResult whose mapping carries the panel ids
    plus the content rects the caller lays out into: ``main_rect`` / ``side_rect``
    (the panels) and ``main_content`` / ``side_content`` (inset by 4 px).
    """
    p = id_prefix
    bgcolor = bgcolor or [0.16, 0.16, 0.17, 1.0]
    side_bgcolor = side_bgcolor or [0.12, 0.12, 0.13, 1.0]
    inset = 4
    side_x = main_width + gap
    main_rect = [0, 0, main_width, height]
    side_rect = [side_x, 0, side_width, height]

    main_id = device.add_panel(f"{p}_main_panel", main_rect, bgcolor=bgcolor,
                               border=border, bordercolor=bordercolor, rounded=rounded)
    side_id = device.add_panel(f"{p}_side_panel", side_rect, bgcolor=side_bgcolor,
                               border=border, bordercolor=bordercolor, rounded=rounded)

    return stage_result(
        {
            "main_panel": main_id,
            "side_panel": side_id,
            "main_rect": main_rect,
            "side_rect": side_rect,
            "main_content": [inset, inset, main_width - 2 * inset, height - 2 * inset],
            "side_content": [side_x + inset, inset, side_width - 2 * inset,
                             height - 2 * inset],
            "total_width": side_x + side_width,
            "height": height,
        },
        name="two_panel_strip",
    )


def dial_label_cell(device, id_prefix, param_name, rect, *, label=None,
                    min_val=0.0, max_val=100.0, initial=0.0, unitstyle=1,
                    label_h=14, gap=1, **dial_kwargs):
    """A dial with a caption directly below it — the AS Console control cell.

    ``rect`` is the DIAL's ``[x, y, w, h]``; a ``live.comment`` label is placed just
    below (``label`` text, defaulting to ``param_name``). The dial shows its live
    value in Live's native readout. Extra ``dial_kwargs`` pass through to
    ``device.add_dial`` (e.g. ``annotation_name``, ``units``). Returns a StageResult
    with ``dial`` and ``label`` ids and the cell's overall ``rect``.
    """
    p = id_prefix
    text = label or param_name
    # The caption is the comment BELOW; force showname=0 so the dial does not ALSO
    # draw its parameter name inside the knob (the factory default is showname=1) and
    # double the label. Caller can still override via dial_kwargs.
    dial_id = device.add_dial(
        f"{p}_dial", param_name, rect, min_val=min_val, max_val=max_val,
        initial=initial, unitstyle=unitstyle,
        showname=dial_kwargs.pop("showname", 0),
        annotation_name=dial_kwargs.pop("annotation_name", text), **dial_kwargs,
    )
    lx, ly = rect[0], rect[1] + rect[3] + gap
    label_id = device.add_comment(f"{p}_label", [lx, ly, rect[2], label_h], text)

    return stage_result(
        {
            "dial": dial_id,
            "label": label_id,
            "rect": [rect[0], rect[1], rect[2], rect[3] + gap + label_h],
        },
        name="dial_label_cell",
        params={param_name: device.parameter(dial_id)},
    )


def dial_value_cell(device, id_prefix, param_name, dial_rect, *, label=None,
                    min_val=0.0, max_val=100.0, initial=0.0, unitstyle=1,
                    accent=None, fill=None, label_color=None,
                    label_h=10, label_gap=1, label_fontsize=7.5,
                    label_fontname="Ableton Sans Medium", appearance=0,
                    **dial_kwargs):
    """The AS Console / Rainbow / Chiral atomic control cell: an uppercase caption
    ABOVE a native ``live.dial`` whose OWN persistent value reads out BELOW the knob.

    Grounded in AS_Console_1.02: its dials are 41x35, ``showname=0``, with an accent
    ring (``activedialcolor``) + grey value arc (``activefgdialcolor``) and rely on
    the native value display (``shownumber=1`` — the Max ``live.dial`` reference:
    "shownumber toggles the display of the parameter value"). NO ``paint_control``:
    a render-only painter fills the dial rect and HIDES that native value (the dim,
    value-less knobs we shipped). ``dial_rect`` is the DIAL's ``[x, y, w, h]``; the
    caption is placed just above it.

    ``accent`` -> ``activedialcolor`` (the lit ring, the device accent); ``fill`` ->
    ``activefgdialcolor`` (the value arc; defaults to a neutral grey like AS Console).
    Extra ``dial_kwargs`` pass through to ``device.add_dial`` (``parameter_exponent``,
    ``annotation_name`` …). Returns a StageResult with ``dial``/``label`` ids, the
    overall cell ``rect`` and the param.
    """
    p = id_prefix
    text = label if label is not None else param_name
    lx = dial_rect[0]
    ly = dial_rect[1] - label_h - label_gap
    cap_kwargs = dict(fontsize=label_fontsize, fontname=label_fontname, justification=1)
    if label_color is not None:
        cap_kwargs["textcolor"] = list(label_color)
    label_id = device.add_comment(
        f"{p}_cap", [lx, ly, dial_rect[2], label_h], text, **cap_kwargs,
    )
    dk = dict(showname=0, shownumber=1, appearance=appearance)
    dk["activedialcolor"] = list(accent) if accent is not None else None
    dk["activefgdialcolor"] = list(fill) if fill is not None else [0.59, 0.59, 0.59, 1.0]
    dk = {k: v for k, v in dk.items() if v is not None}
    dk.update(dial_kwargs)
    annotation = dk.pop("annotation_name", text)
    dial_id = device.add_dial(
        f"{p}_dial", param_name, dial_rect, min_val=min_val, max_val=max_val,
        initial=initial, unitstyle=unitstyle, annotation_name=annotation, **dk,
    )
    return stage_result(
        {
            "dial": dial_id,
            "label": label_id,
            "rect": [lx, ly, dial_rect[2], (dial_rect[1] + dial_rect[3]) - ly],
        },
        name="dial_value_cell",
        params={param_name: device.parameter(dial_id)},
    )


def stacked_panels(device, id_prefix, tab_param, panel_ids, *, rect, labels=None,
                   ghost=False, x=30, y=400):
    """Tabbed panel sections (C6): a ``live.tab`` selects which of N pre-added
    panels is shown, swapping them IN PLACE via ``thispatcher`` script show/hide.

    ``panel_ids`` are the scripting names (``varname``) of the panels the caller
    already added at the SAME content rect (e.g. ``add_bpatcher_module`` modules or
    panels). On every tab change the recipe hides ALL panels then shows the selected
    one (a ``t i b`` fork fires the hide bang first, then the show index), so exactly
    one panel is visible. ``ghost=True`` makes the tab strip itself invisible
    (alpha-0) — a hidden selector you drive from elsewhere. ``rect`` is the tab
    strip's ``[x,y,w,h]``. Returns ``{tab, content_rect}``.

    NOTE: the script show/hide wiring is structurally grounded in the framework's
    flyout mechanism; the actual swap is Live-verified when a device first uses it.
    """
    p = id_prefix
    labels = list(labels or [str(i + 1) for i in range(len(panel_ids))])
    tab_kwargs = {}
    if ghost:
        clear = [0.0, 0.0, 0.0, 0.0]
        tab_kwargs = dict(bgcolor=clear, bgoncolor=clear,
                          textcolor=clear, textoncolor=clear)
    tab_id = device.add_tab(f"{p}_tab", tab_param, rect, options=labels, **tab_kwargs)

    fork = device.add_newobj(
        f"{p}_fork", "t i b", numinlets=1, numoutlets=2,
        outlettype=["int", "bang"], patching_rect=[x, y, 50, 20],
    )
    sel = device.add_newobj(
        f"{p}_sel", "sel " + " ".join(str(i) for i in range(len(panel_ids))),
        numinlets=1, numoutlets=len(panel_ids) + 1,
        outlettype=["bang"] * len(panel_ids) + [""],
        patching_rect=[x, y + 30, 160, 20],
    )
    thisp = device.add_newobj(
        f"{p}_thisp", "thispatcher", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 130, 80, 20],
    )
    device.add_line(tab_id, 0, fork, 0)
    device.add_line(fork, 0, sel, 0)            # index (fires 2nd) -> show selected
    for i, pid in enumerate(panel_ids):
        hide_msg = device.add_newobj(
            f"{p}_hide{i}", f"script hide {pid}", numinlets=2, numoutlets=1,
            maxclass="message", patching_rect=[x + 200, y + 30 + i * 22, 120, 18],
        )
        device.add_line(fork, 1, hide_msg, 0)   # hide bang (fires 1st) -> hide all
        device.add_line(hide_msg, 0, thisp, 0)
        show_msg = device.add_newobj(
            f"{p}_show{i}", f"script show {pid}", numinlets=2, numoutlets=1,
            maxclass="message", patching_rect=[x + i * 70, y + 70, 90, 18],
        )
        device.add_line(sel, i, show_msg, 0)
        device.add_line(show_msg, 0, thisp, 0)

    return stage_result(
        {"tab": tab_id, "content_rect": list(rect)},
        name="stacked_panels",
        params={tab_param: device.parameter(tab_id)},
    )


def bypass_wrapper(device, id_prefix, *, label="Bypass", button_rect=None,
                   x=30, y=30):
    """Hard-bypass a DSP stage with a latching toggle (F4) — a ``selector~ 2 1``
    crossfade-free switch between the DRY (bypass) and WET (processed) paths.

    Wire the unprocessed signal into the ``dry_in`` port and your processed signal
    into ``wet_in``; ``audio_out`` carries whichever the toggle selects (toggle OFF
    = processed/wet, ON = dry/bypass). The toggle is a first-class ``live.text``
    parameter (so the bypass state automates + saves). Returns the toggle/selector
    ids and ``dry_in`` / ``wet_in`` / ``audio_out`` ports.
    """
    p = id_prefix
    btn = device.add_live_text(f"{p}_bypass", label, button_rect or [x, y, 50, 16],
                               mode=1)
    # toggle 0 (active) -> selector control 2 (wet) ; toggle 1 (bypass) -> 1 (dry)
    inv = device.add_newobj(
        f"{p}_inv", "expr 2-$i1", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[x, y + 30, 70, 20],
    )
    sel = device.add_newobj(
        f"{p}_sel", "selector~ 2 1", numinlets=3, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 60, 90, 20],
    )
    device.add_line(btn, 0, inv, 0)
    device.add_line(inv, 0, sel, 0)

    return stage_result(
        {"bypass": btn, "selector": sel},
        name="bypass_wrapper",
        params={f"{p}_bypass": device.parameter(btn)},
        ports={
            "dry_in": device.box(sel).inlet(1),
            "wet_in": device.box(sel).inlet(2),
            "audio_out": device.box(sel).outlet(0),
        },
    )


def switchable_bank(device, id_prefix, options, *, tab_param=None, tab_rect=None,
                    x=30, y=30):
    """A/B / multi-algorithm signal bank (F4): a ``selector~ N 1`` whose active
    input is chosen by a ``live.tab`` parameter, with a ``+ 1`` shim (the tab is
    0-indexed, ``selector~`` is 1-indexed; 0 = silence).

    ``options`` are the tab labels (one per bank input). Wire each candidate signal
    into ``in_0 .. in_{N-1}``; ``audio_out`` carries the selected one. Returns the
    tab + selector ids and the per-input + output ports.
    """
    p = id_prefix
    n = len(options)
    tab_param = tab_param or f"{p}_select"
    tab_id = device.add_tab(f"{p}_tab", tab_param, tab_rect or [x, y, 40 * n, 18],
                            options=list(options))
    shim = device.add_newobj(
        f"{p}_shim", "+ 1", numinlets=2, numoutlets=1, outlettype=[""],
        patching_rect=[x, y + 30, 50, 20],
    )
    sel = device.add_newobj(
        f"{p}_sel", f"selector~ {n} 1", numinlets=n + 1, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 60, 30 + 30 * n, 20],
    )
    device.add_line(tab_id, 0, shim, 0)
    device.add_line(shim, 0, sel, 0)

    ports = {f"in_{i}": device.box(sel).inlet(i + 1) for i in range(n)}
    ports["audio_out"] = device.box(sel).outlet(0)
    return stage_result(
        {"tab": tab_id, "selector": sel},
        name="switchable_bank",
        params={tab_param: device.parameter(tab_id)},
        ports=ports,
    )


def modulator_slot_component(device, *, accent, text_color=None,
                             dim_color=None, self_map_guard=None,
                             debounce_ms=20, width=240, height=17,
                             normalized=0, js_filename="lom_mapper.js",
                             source_enum=None, source_glyphs=None,
                             reveal=False, mode_switch=False, add_chip=False,
                             mode_colors=None, unmap_button=False,
                             value_bar=False, row_color=False,
                             uplink_pname=False, uplink_dname=False,
                             pages=False, ratio_lcd=False):
    """The E2/E3 mapping slot — ONE ``#1``-parameterized Subpatcher to stamp N
    times via :meth:`Device.add_component_rack` (the lfo-cluster slot, F2+E2).

    Presentation is the STOCK-MODULATOR ROW (Live 12 LFO / Envelope Follower:
    the whole mapping UI is one ~15px strip — Map button, target chip, inline
    percent values; knobs are for the device's own DSP only):
    ``MAP | target readout | Depth% | Min% | Max% | BI`` at ``width x height``
    (default 240x17). Stack N stamped rows in a single narrow column and put
    ONE shared caption header above the stack (the slot has no captions).

    Each stamped instance is a full click-to-map modulation lane:
      MAP (``#1 Map``) arms the ``lom_mapper`` v8 script's selected-parameter
      observer; picking a param in Live attaches the slot's retargetable sink
      (``dsp.live.retargetable_param_sink`` — live.remote~/live.modulate~ with
      the id on the RIGHT inlet via deferlow); the target's name lands in the
      readout and its native min/max uplink to the ctl bus for gen-side scaling.

    I/O (``#1`` = instance number, standalone tokens only — Live-proven:
    ``#1`` EMBEDDED mid-symbol like ``depth_#1``/``msig_r#1`` stays LITERAL).
    Everything crosses the bpatcher boundary by inlet/outlet, the
    corpus-verbatim discipline (lfo-cluster's slot feeds its sinks from inlet
    boxes and talks to the parent through outlets). Inlets by x-position:
      inlet 0: mapper messages (``settarget``/``setid``/``unmap``/``map``,
               and the parent's ``announce N`` fan-back for exclusivity);
      inlet 1: live.remote~ signal (native units unless ``normalized=1``);
      inlet 2: live.modulate~ signal (0..1 relative).
    Outlet 0 — the ctl uplink route bus, UNINDEXED keys (each stamp has its
    own outlet patchcord, so the parent knows the slot topologically):
    ``depth v``, ``umin v``, ``umax v``, ``bipolar v`` (slot params),
    ``tmin v``/``tmax v`` (target native range) and ``announce N`` (MAP armed
    — fan it back into EVERY slot's inlet 0 so the other slots stand down).

    Optional extensions (both default OFF — Orbit's call stays byte-identical):
      ``source_enum``: list of source names — adds a ``#1 Source`` ``live.menu``
        at the row start (each stamped lane picks its OWN source) plus a
        ``source v`` key on the ctl uplink bus. Row becomes
        ``SRC | MAP | target | Depth% | Min% | Max% | BI`` (width ~300).
      ``reveal``: the Rnd_Gen page idiom — the slot listens for ``lanes N`` on
        inlet 0 and HIDES ITSELF (message ``hidden $1`` to its own
        ``thispatcher``, which targets the bpatcher box in the parent) when
        ``N < #1``. Fan ``lanes <count>`` into every slot's inlet 0 alongside
        ``announce`` and a Lanes param + "+" button give the stock-LFO
        progressive reveal, all inline. (Deconstructed from
        dnksaus_Rnd_Gen_v3.0: 8 same-rect pages hidden/shown exactly this way.)

    Registers the mapper source as a device js asset (content-addressed).
    Returns ``(subpatcher, ids)``.
    """
    from .dsp import retargetable_param_sink
    from .engines.design_system import js_sidecar_name
    from .engines.lom_mapper import DEFAULT_SELF_MAP_GUARD, lom_mapper_js
    from .objects import newobj
    from .parameters import ParameterSpec
    from .subpatcher import Subpatcher
    from .ui import live_text, number_box, textedit

    guard = self_map_guard or DEFAULT_SELF_MAP_GUARD
    tx = list(text_color) if text_color else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    acc = list(accent)

    js_code = lom_mapper_js(self_map_guard=guard, debounce_ms=debounce_ms)
    fname = js_sidecar_name(js_filename, js_code)
    device.register_asset(fname, js_code, asset_type="TEXT", category="js")

    sub = Subpatcher("modslot")
    # ---- UI: ONE tight stock-modulator row (Rnd_Gen density, no headers) ----
    # When a source_enum is given the lane leads with a clickable SHAPE ICON
    # (replaces the 52px text dropdown AND the column header — the parked menu
    # stays the automatable param). Row geometry ported from
    # dnksaus_Rnd_Gen: 15-16px controls, ~222px total, self-documenting.
    icon = bool(source_enum and source_glyphs)
    if source_enum:
        from .ui import menu as _live_menu
        # The Source enum is the automatable param. In icon mode the menu is
        # PARKED offscreen and the glyph drives/reads it; else it shows inline.
        menu_rect = [900, 900, 1, 1] if icon else [0, 1, 52, 15]
        sub.add_box(_live_menu(
            "slot_source", "#1 Source", menu_rect,
            options=list(source_enum), fontsize=7.5,
            bgcolor=[0.16, 0.16, 0.18, 1.0], textcolor=tx, bgoncolor=acc,
            annotation="This lane's modulation source — each lane can run a "
                       "different generator.",
            parameter=ParameterSpec(name="#1 Source", shortname="#1 Source",
                                    minimum=0, maximum=len(source_enum) - 1,
                                    enum=list(source_enum), parameter_type=2,
                                    initial=0, initial_enable=True,
                                    linknames=1)))
    if icon:
        from .engines.shape_icon import shape_icon_js
        from .jsui_contract import validate_jsui_contract as _vjc
        # classic-jsui box: the contract rejects v8ui pointer handlers (the
        # dead-click class — the shape icon shipped unclickable once).
        ic_code = _vjc(shape_icon_js(shapes=list(source_glyphs), accent=acc))
        ic_fname = js_sidecar_name("shape_icon.js", ic_code)
        device.register_asset(ic_fname, ic_code, asset_type="TEXT",
                              category="js")
        sub.add_box({"box": {
            "id": "slot_shape_ui", "maxclass": "jsui",
            "jsui_maxclass": "jsui", "filename": ic_fname,
            "numinlets": 1, "numoutlets": 1, "outlettype": [""],
            "parameter_enable": 0, "presentation": 1, "border": 0,
            "presentation_rect": [1, 1, 15, 15],
            "patching_rect": [1, 200, 15, 15]}})
        MAP_X, PNAME_X, DEP_X, MIN_X, MAX_X, BI_X = 18, 46, 114, 148, 178, 208
    else:
        MAP_X, PNAME_X, DEP_X, MIN_X, MAX_X, BI_X = 0, 31, 96, 135, 174, 213
    # value_bar (catalog #21, Rnd Gen): a 5px live-output meter at the row's
    # LEFT edge — everything else shifts right 7px.
    if value_bar and icon:
        raise ValueError("modulator_slot_component: value_bar with "
                         "source_glyphs icon mode is not supported (both "
                         "claim the row's left edge)")
    BAR_SHIFT = 7 if value_bar else 0
    MAP_X += BAR_SHIFT
    PNAME_X += BAR_SHIFT
    DEP_X += BAR_SHIFT
    MIN_X += BAR_SHIFT
    MAX_X += BAR_SHIFT
    BI_X += BAR_SHIFT
    if value_bar:
        sub.add_box({"box": {
            "id": "slot_bar", "maxclass": "multislider", "contdata": 1,
            "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
            "parameter_enable": 0, "ignoreclick": 1, "setminmax": [0.0, 1.0],
            "slidercolor": acc, "bgcolor": [0.06, 0.06, 0.08, 1.0],
            "presentation": 1,
            "presentation_rect": [BAR_SHIFT - 7, 1, 5, 15],
            "patching_rect": [560, 200, 5, 15]}})
        sub.add_newobj("slot_bar_snap", "snapshot~ 50", numinlets=2,
                       numoutlets=1, outlettype=["float"],
                       patching_rect=[560, 170, 80, 20])
    sub.add_box(live_text(
        "slot_map", "#1 Map", [MAP_X, 1, 26, 15], text_on="MAP", text_off="MAP",
        mode=1, fontsize=7.0, bgoncolor=acc, textcolor=dim,
        annotation="When Map is on, the next Live parameter you click becomes "
                   "this lane's target.",
        parameter=ParameterSpec(name="#1 Map", shortname="#1 Map",
                                minimum=0, maximum=1, enum=["MAP", "MAP"],
                                parameter_type=2, initial=0,
                                initial_enable=True, linknames=1)))
    sub.add_box(textedit(
        "slot_pname", [PNAME_X, 2, 66, 13], text="—", fontsize=8.0,
        textcolor=tx, bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    # 0..100 ranges so unitstyle=5 reads "100 %" like the stock modulators
    # (consumers scale by 0.01 — poly_mod_engine does it inside gen)
    for nid, pname, nx, nw, init in (("slot_depth", "#1 Depth", DEP_X, 32, 100.0),
                                     ("slot_umin", "#1 Min", MIN_X, 28, 0.0),
                                     ("slot_umax", "#1 Max", MAX_X, 28, 100.0)):
        sub.add_box(number_box(
            nid, pname, [nx, 1, nw, 15], min_val=0.0, max_val=100.0,
            initial=init, unitstyle=5, lcdcolor=acc,
            parameter=ParameterSpec(name=pname, shortname=pname,
                                    minimum=0.0, maximum=100.0, initial=init,
                                    initial_enable=True, linknames=1)))
    sub.add_box(live_text(
        "slot_bipolar", "#1 Bipolar", [BI_X, 1, 15, 15], text_on="BI",
        text_off="BI", mode=1, fontsize=6.5, bgoncolor=acc, textcolor=dim,
        annotation="Bipolar — modulate above AND below the target's current "
                   "value (centred), rather than only upward.",
        parameter=ParameterSpec(name="#1 Bipolar", shortname="#1 Bipolar",
                                minimum=0, maximum=1, enum=["OFF", "ON"],
                                parameter_type=2, initial=0,
                                initial_enable=True, linknames=1)))
    # ---- optional Remote/Mod switch + "+" add chip (catalog #15/#16) --------
    # dnksaus/Live-12 grammar: orange = Remote (live.remote~ takeover, user
    # loses the dial), teal = Mod (live.modulate~ grey-ring, additive around
    # the dial). The chip drives the retarget sink's mode inlet, which
    # hot-swaps the stored id between sinks (corpus-verbatim re-emit).
    RM_X = BI_X + 17
    ADD_X = RM_X + (17 if mode_switch else 0)
    UN_X = ADD_X + (17 if add_chip else 0)
    RA_X = UN_X + (15 if unmap_button else 0)
    if ratio_lcd:
        # catalog #29 (MEQ8): mapping-with-math — a per-row multiplier LCD
        # ("x 5.04"); engines consume the `ratio v` ctl uplink and multiply
        # the lane signal before this row's sink (target = source × ratio).
        sub.add_box(number_box(
            "slot_ratio", "#1 Ratio", [RA_X, 1, 34, 15], min_val=0.01,
            max_val=100.0, initial=1.0, lcdcolor=acc,
            parameter=ParameterSpec(name="#1 Ratio", shortname="#1 Ratio",
                                    minimum=0.01, maximum=100.0,
                                    initial=1.0, initial_enable=True,
                                    exponent=3.0, linknames=1,
                                    units="x %.2f", unitstyle=9)))
    if unmap_button:
        # ✗-in-a-chip (catalog #14): NON-param clickable — a message box whose
        # click fires a second "unmap" message into the mapper js (the same
        # verb the parent's programmatic path uses).
        sub.add_box({"box": {
            "id": "slot_x", "maxclass": "message", "text": "✗",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "fontsize": 8.0, "textjustification": 1,
            "presentation": 1, "presentation_rect": [UN_X, 1, 13, 15],
            "patching_rect": [560, 260, 30, 20]}})
        sub.add_box({"box": {
            "id": "slot_x_un", "maxclass": "message", "text": "unmap",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [560, 290, 50, 20]}})
    if mode_switch:
        rm_remote, rm_mod = mode_colors or ([0.96, 0.62, 0.20, 1.0],
                                            [0.05, 0.76, 0.83, 1.0])
        sub.add_box(live_text(
            "slot_mode", "#1 RM", [RM_X, 1, 15, 15], text_on="M",
            text_off="R", mode=1, fontsize=6.5,
            bgoncolor=list(rm_mod), textcolor=list(rm_remote),
            annotation="Remote (R): this lane TAKES OVER the target — Live "
                       "shows the mapped hand. Mod (M): Live-12-style grey-"
                       "ring modulation AROUND the dial; the user keeps "
                       "control.",
            parameter=ParameterSpec(name="#1 RM", shortname="#1 RM",
                                    minimum=0, maximum=1, enum=["R", "M"],
                                    parameter_type=2, initial=0,
                                    initial_enable=True, linknames=1)))
    if add_chip:
        sub.add_box(live_text(
            "slot_addc", "#1 Add", [ADD_X, 1, 15, 15], text_on="+",
            text_off="+", mode=1, fontsize=7.5, bgoncolor=acc, textcolor=dim,
            annotation="Additive stacking — this lane SUMS with other lanes "
                       "on the same target instead of replacing them (engine-"
                       "side; consumed from the ctl uplink like Bipolar).",
            parameter=ParameterSpec(name="#1 Add", shortname="#1 Add",
                                    minimum=0, maximum=1, enum=["OFF", "ON"],
                                    parameter_type=2, initial=0,
                                    initial_enable=True, linknames=1)))
    if icon:
        # glyph <-> parked menu two-way: menu value echoes to the icon
        # (display), the icon's click emits the next index into the menu
        # (which sets the automatable param + drives the source uplink).
        sub.add_line("slot_source", 0, "slot_shape_ui", 0)
        sub.add_line("slot_shape_ui", 0, "slot_source", 0)
    # ---- mapper script + sink ----------------------------------------------
    # bpatcher inlet 0 -> js: the programmatic hook (settarget/setid/unmap
    # from the parent device — the headless-proof and preset-restore path)
    sub.add_box({"box": {
        "id": "slot_in", "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
        "outlettype": [""], "patching_rect": [4, 340, 25, 25],
        "comment": "mapper messages (settarget/setid/unmap/map)"}})
    sub.add_box(newobj(
        "slot_js", f"v8 {fname} #1", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[30, 400, 180, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0}))
    sub.add_line("slot_in", 0, "slot_js", 0)
    sink_boxes, sink_lines = retargetable_param_sink(
        "slot_sink", normalized=normalized)
    sub.add_dsp(sink_boxes, sink_lines)
    # signal delivery is by bpatcher INLET (corpus-verbatim: lfo-cluster's
    # mapping slot feeds live.remote~/live.modulate~ from inlet boxes, never
    # send~/receive~ across the bpatcher boundary) — inlet order is by
    # x-position: 0 = mapper messages, 1 = remote signal, 2 = modulate signal
    sub.add_box({"box": {
        "id": "slot_rsig_r", "maxclass": "inlet", "numinlets": 0,
        "numoutlets": 1, "outlettype": [""],
        "patching_rect": [200, 340, 25, 25],
        "comment": "remote signal (native units)"}})
    sub.add_box({"box": {
        "id": "slot_rsig_m", "maxclass": "inlet", "numinlets": 0,
        "numoutlets": 1, "outlettype": [""],
        "patching_rect": [240, 340, 25, 25],
        "comment": "modulate signal (0..1 relative)"}})
    # ---- lane enable release (hunt #61) --------------------------------------
    # `enable 0|1` from the parent (the lane On toggle): OFF routes `id 0`
    # through the sink GATE's data inlet — the same cross-detach machinery the
    # R/M mode switch uses — so the ACTIVE sink releases its target instead of
    # a Remote-mode lane pinning it at the window Min forever; ON re-bangs
    # zl.reg to re-emit the stored id down the current path (mapping restored,
    # nothing forgotten). Mode-aware for free: the gate always points at the
    # currently-selected sink.
    sub.add_newobj("slot_en_route", "route enable", numinlets=1, numoutlets=2,
                   outlettype=["", ""], patching_rect=[520, 340, 90, 20])
    sub.add_newobj("slot_en_sel", "sel 0 1", numinlets=1, numoutlets=3,
                   outlettype=["bang", "bang", ""],
                   patching_rect=[520, 365, 60, 20])
    sub.add_box({"box": {
        "id": "slot_en_id0", "maxclass": "message", "text": "id 0",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [520, 390, 40, 20]}})
    sub.add_line("slot_in", 0, "slot_en_route", 0)
    sub.add_line("slot_en_route", 0, "slot_en_sel", 0)
    sub.add_line("slot_en_sel", 0, "slot_en_id0", 0)
    sub.add_line("slot_en_id0", 0, "slot_sink_gate", 1)
    sub.add_line("slot_en_sel", 1, "slot_sink_reg", 0)

    # ---- status route bus ----------------------------------------------------
    sub.add_newobj("slot_route",
                   "route mapped min max pname dname path flash announce",
                   numinlets=1, numoutlets=9,
                   outlettype=["", "", "", "", "", "", "", "", ""],
                   patching_rect=[30, 430, 300, 20])
    sub.add_box({"box": {
        "id": "slot_seton", "maxclass": "message", "text": "set $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [330, 460, 50, 20]}})
    sub.add_box({"box": {
        "id": "slot_extunmap", "maxclass": "message", "text": "extunmap",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [30, 520, 70, 20]}})
    # ---- uplinks. Keys are UNINDEXED: `#1` embedded mid-symbol (depth_#1)
    # does NOT substitute (Live-proven — only standalone #1 tokens and
    # longname-leading #1 resolve), and no index is needed anyway: each
    # stamped slot has its own outlet patchcord, so the parent knows the
    # slot topologically and stamps literal indices at build time.
    ups = [("slot_up_depth", "prepend depth", "slot_depth", 0),
           ("slot_up_umin", "prepend umin", "slot_umin", 0),
           ("slot_up_umax", "prepend umax", "slot_umax", 0),
           ("slot_up_bip", "prepend bipolar", "slot_bipolar", 0),
           ("slot_up_tmin", "prepend tmin", "slot_route", 1),
           ("slot_up_tmax", "prepend tmax", "slot_route", 2)]
    for k, (uid, text, src, srcout) in enumerate(ups):
        sub.add_newobj(uid, text, numinlets=1, numoutlets=1, outlettype=[""],
                       patching_rect=[400, 400 + 30 * k, 130, 20])
        sub.add_line(src, srcout, uid, 0)
    # the ctl uplink leaves by OUTLET (--- does not cross the embed boundary)
    sub.add_box({"box": {
        "id": "slot_out", "maxclass": "outlet", "numinlets": 1,
        "numoutlets": 0, "patching_rect": [400, 590, 25, 25],
        "comment": "ctl uplink (depth_N/umin_N/umax_N/bipolar_N/"
                   "tmin_N/tmax_N/announce N)"}})
    for uid, _t, _s, _o in ups:
        sub.add_line(uid, 0, "slot_out", 0)
    # ---- MAP button -> js; status -> UI --------------------------------------
    sub.add_newobj("slot_prep_map", "prepend map", numinlets=1, numoutlets=1,
                   outlettype=[""], patching_rect=[30, 370, 90, 20])
    sub.add_line("slot_map", 0, "slot_prep_map", 0)
    sub.add_line("slot_prep_map", 0, "slot_js", 0)
    sub.add_line("slot_js", 0, "slot_sink_reg", 0)
    sub.add_line("slot_js", 1, "slot_route", 0)
    sub.add_line("slot_route", 3, "slot_pname", 0)      # pname -> "set <n>"
    sub.add_line("slot_route", 6, "slot_seton", 0)      # flash -> set $1
    sub.add_line("slot_seton", 0, "slot_map", 0)
    sub.add_line("slot_sink_unmapped", 0, "slot_extunmap", 0)
    sub.add_line("slot_extunmap", 0, "slot_js", 0)
    sub.add_line("slot_rsig_r", 0, "slot_sink_remote", 0)
    sub.add_line("slot_rsig_m", 0, "slot_sink_mod", 0)
    if value_bar:
        # live output meter: the remote-signal inlet doubles as the lane's
        # source level (0..1 control signal) — snapshot~ self-clocks at 50 ms
        sub.add_line("slot_rsig_r", 0, "slot_bar_snap", 0)
        sub.add_line("slot_bar_snap", 0, "slot_bar", 0)
    if unmap_button:
        sub.add_line("slot_x", 0, "slot_x_un", 0)
        sub.add_line("slot_x_un", 0, "slot_js", 0)
    if row_color:
        # catalog #19: the parent fans `rowcolor r g b a` into inlet 0 per
        # stamped lane (each stamp has its own inlet cord) — recolors the
        # MAP/BI(/R/M/+) chips' on-state and the numbox LCDs so mapping
        # identity reads by color. live.* accept attribute-set messages.
        sub.add_newobj("slot_rc_route", "route rowcolor", numinlets=1,
                       numoutlets=2, outlettype=["", ""],
                       patching_rect=[620, 340, 100, 20])
        sub.add_line("slot_in", 0, "slot_rc_route", 0)
        rc_targets = ["slot_map", "slot_bipolar"]
        if mode_switch:
            rc_targets.append("slot_mode")
        if add_chip:
            rc_targets.append("slot_addc")
        sub.add_box({"box": {
            "id": "slot_rc_on", "maxclass": "message",
            "text": "bgoncolor $1 $2 $3 $4",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [620, 370, 140, 20]}})
        sub.add_box({"box": {
            "id": "slot_rc_lcd", "maxclass": "message",
            "text": "lcdcolor $1 $2 $3 $4",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [620, 400, 140, 20]}})
        sub.add_line("slot_rc_route", 0, "slot_rc_on", 0)
        sub.add_line("slot_rc_route", 0, "slot_rc_lcd", 0)
        for t in rc_targets:
            sub.add_line("slot_rc_on", 0, t, 0)
        for t in ("slot_depth", "slot_umin", "slot_umax"):
            sub.add_line("slot_rc_lcd", 0, t, 0)
        if value_bar:
            sub.add_box({"box": {
                "id": "slot_rc_bar", "maxclass": "message",
                "text": "slidercolor $1 $2 $3 $4",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [620, 430, 150, 20]}})
            sub.add_line("slot_rc_route", 0, "slot_rc_bar", 0)
            sub.add_line("slot_rc_bar", 0, "slot_bar", 0)
    if uplink_pname or uplink_dname:
        # catalog #22/#26: mirror the mapped target/device NAMES to the
        # parent (title-strip summary chips). The uplink is the RAW js
        # status stream — its messages are already `pname set <n>` /
        # `dname set <n>` with safe selectors. Do NOT re-prefix route
        # output here: after `route`, the payload's selector is `set`,
        # which prepend consumes as its own re-config verb (message
        # silently vanishes — Live-verified trap, T05).
        sub.add_line("slot_js", 1, "slot_out", 0)
    if mode_switch:
        # chip int (0=R,1=M) -> sink mode inlet: the sink bangs its zl.reg so
        # the stored id re-attaches down the newly selected path (hot swap).
        sub.add_line("slot_mode", 0, "slot_sink_mode", 0)
        sub.add_newobj("slot_up_mode", "prepend mode", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 620, 120, 20])
        sub.add_line("slot_mode", 0, "slot_up_mode", 0)
        sub.add_line("slot_up_mode", 0, "slot_out", 0)
    if add_chip:
        sub.add_newobj("slot_up_add", "prepend add", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 650, 120, 20])
        sub.add_line("slot_addc", 0, "slot_up_add", 0)
        sub.add_line("slot_up_add", 0, "slot_out", 0)
    if ratio_lcd:
        sub.add_newobj("slot_up_ratio", "prepend ratio", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 740, 120, 20])
        sub.add_line("slot_ratio", 0, "slot_up_ratio", 0)
        sub.add_line("slot_up_ratio", 0, "slot_out", 0)
    # ---- cross-slot exclusivity: announce goes UP the outlet; the parent
    # fans it back into every slot's inlet 0 (js ignores its own index)
    sub.add_newobj("slot_prep_ann", "prepend announce", numinlets=1,
                   numoutlets=1, outlettype=[""],
                   patching_rect=[30, 460, 120, 20])
    sub.add_line("slot_route", 7, "slot_prep_ann", 0)
    sub.add_line("slot_prep_ann", 0, "slot_out", 0)
    # a clean ``mapped <0|1>`` pulse up the outlet when this slot's mapping state
    # changes — the parent chains ``mapped 1`` for Auto-Map (arm the next lane).
    sub.add_newobj("slot_prep_mapped", "prepend mapped", numinlets=1,
                   numoutlets=1, outlettype=[""], patching_rect=[30, 490, 120, 20])
    sub.add_line("slot_route", 0, "slot_prep_mapped", 0)
    sub.add_line("slot_prep_mapped", 0, "slot_out", 0)

    if source_enum:
        sub.add_newobj("slot_up_src", "prepend source", numinlets=1,
                       numoutlets=1, outlettype=[""],
                       patching_rect=[400, 590, 130, 20])
        sub.add_line("slot_source", 0, "slot_up_src", 0)
        sub.add_line("slot_up_src", 0, "slot_out", 0)
    if reveal:
        # Rnd_Gen page idiom: "lanes N" on inlet 0 -> hide self when N < #1.
        # thispatcher inside a bpatcher addresses the BPATCHER BOX in the
        # parent, so "hidden $1" hides this stamped lane in presentation.
        sub.add_newobj("slot_lanes_route", "route lanes", numinlets=1,
                       numoutlets=2, outlettype=["", ""],
                       patching_rect=[4, 560, 90, 20])
        sub.add_newobj("slot_lanes_cmp", "< #1", numinlets=2, numoutlets=1,
                       outlettype=["int"], patching_rect=[4, 590, 50, 20])
        sub.add_box({"box": {
            "id": "slot_hide_msg", "maxclass": "message", "text": "hidden $1",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [4, 620, 70, 20]}})
        sub.add_newobj("slot_this", "thispatcher", numinlets=1, numoutlets=2,
                       outlettype=["", ""], patching_rect=[4, 650, 80, 20])
        sub.add_line("slot_in", 0, "slot_lanes_route", 0)
        sub.add_line("slot_lanes_route", 0, "slot_lanes_cmp", 0)
        sub.add_line("slot_lanes_cmp", 0, "slot_hide_msg", 0)
        sub.add_line("slot_hide_msg", 0, "slot_this", 0)
    if pages:
        # catalog #25 (Rnd_Gen 8-page idiom): rows stamped at the SAME rects
        # in page groups; a `pagewin <lo> <hi>` broadcast on inlet 0 hides
        # every row whose 1-based index falls outside the window (same
        # thispatcher-hides-the-bpatcher mechanism as `reveal`).
        sub.add_newobj("slot_page_route", "route pagewin", numinlets=1,
                       numoutlets=2, outlettype=["", ""],
                       patching_rect=[120, 560, 100, 20])
        sub.add_newobj("slot_page_unp", "unpack 1 1", numinlets=1,
                       numoutlets=2, outlettype=["int", "int"],
                       patching_rect=[120, 590, 70, 20])
        sub.add_newobj("slot_page_cmp",
                       "expr (#1 - 1) < $i1 || (#1 - 1) > $i2",
                       numinlets=2, numoutlets=1, outlettype=[""],
                       patching_rect=[120, 620, 190, 20])
        sub.add_box({"box": {
            "id": "slot_page_hide", "maxclass": "message", "text": "hidden $1",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [120, 650, 70, 20]}})
        sub.add_newobj("slot_page_this", "thispatcher", numinlets=1,
                       numoutlets=2, outlettype=["", ""],
                       patching_rect=[120, 680, 80, 20])
        sub.add_line("slot_in", 0, "slot_page_route", 0)
        sub.add_line("slot_page_route", 0, "slot_page_unp", 0)
        sub.add_line("slot_page_unp", 0, "slot_page_cmp", 0)
        sub.add_line("slot_page_unp", 1, "slot_page_cmp", 1)
        sub.add_line("slot_page_cmp", 0, "slot_page_hide", 0)
        sub.add_line("slot_page_hide", 0, "slot_page_this", 0)

    ids = {"js": "slot_js", "map": "slot_map", "readout": "slot_pname",
           "sink_reg": "slot_sink_reg", "remote": "slot_sink_remote",
           "modulate": "slot_sink_mod", "rect": [0, 0, width, height]}
    # column map (x, w) for modulator_header_row caption alignment (#17)
    columns = {"map": (MAP_X, 26), "target": (PNAME_X, 66),
               "depth": (DEP_X, 32), "min": (MIN_X, 28), "max": (MAX_X, 28),
               "bipolar": (BI_X, 15)}
    if icon:
        columns["source"] = (1, 15)
    if mode_switch:
        columns["mode"] = (RM_X, 15)
        ids["mode"] = "slot_mode"
    if add_chip:
        columns["add"] = (ADD_X, 15)
        ids["add"] = "slot_addc"
    if unmap_button:
        columns["unmap"] = (UN_X, 13)
        ids["unmap"] = "slot_x"
    if ratio_lcd:
        columns["ratio"] = (RA_X, 34)
        ids["ratio"] = "slot_ratio"
    if value_bar:
        columns["bar"] = (0, 5)
        ids["bar"] = "slot_bar"
    ids["columns"] = columns
    if source_enum:
        ids["source"] = "slot_source"
    return (sub, ids)


def settings_sidebar(device, id_prefix, *, mini_width, accent, controls,
                     left_bar=18, panel_width=None, height=None,
                     param_name="Settings", label="SETTINGS",
                     panel_bgcolor=None, bar_bgcolor=None, column_bg=True,
                     bg_id="surf_bg", content_top=6, size_row=None,
                     shift_main=False):
    """A LEFT collapsible SETTINGS COLUMN behind a drawn ▶ dropdown in a thin
    left bar — the dnksaus_Rnd_Gen space-saver, FAITHFULLY: the opener sits in a
    thin bar on the LEFT edge, the settings menu slides out on the LEFT, and the
    main content (hero + mapping grid) shifts RIGHT to make room while the device
    widens (``setwidth``).

    A left ``setwidth`` reveal is impossible (Live only grows the RIGHT edge), so
    — exactly like Rnd_Gen — the column appears by REFLOW: every pre-existing
    on-canvas box is repositioned ``+panel_width`` when open, the settings column
    slides in from its parked slot, and the full-bleed background resizes. One
    automatable ``[Closed, Open]`` enum param (a parked ``live.text`` the drawn
    :func:`~m4l_builder.engines.settings_bar.settings_bar_js` bar drives + reads)
    fires the whole batch through one ``thispatcher`` + ``live.thisdevice``; a
    load-time reset forces the device closed so a saved-open set reopens clean.

    ``controls`` is the settings content, built BY the recipe so it can reflow it,
    laid out as a SINGLE COLUMN of value rows — LABEL on the left, its live value
    (a numbox by default, or a small ``kind:'dial'`` knob) on the right, the
    Rnd_Gen drawer idiom (a drawer shows + tweaks config, so the value reads
    better than a knob). Keep it to a few rows so they stay roomy. Each control is
    a dict:
    ``{"id", "name", "min", "max", "init", "unit", "kind"}`` where ``kind`` is
    ``"dial"`` (default) or ``"num"``, plus optional ``"exp"``
    (parameter_exponent) and ``"ann"`` (info text). Call AFTER the main layout is
    final; build that layout with ``Surface(margin=left_bar)`` so it starts just
    right of the bar.

    ``size_row``: host the device's WIDTH toggle inside the drawer (T18 —
    the on-face FULL/MINI button is banned): ``{"mini": <narrow device
    width>}`` (+ optional ``"param_name"``/``"label"``/``"init"``) appends a
    FULL/MINI ``live.tab`` row and replaces the fixed ``setwidth`` pair with
    a width AUTHORITY — ``pak(size, drawer)`` → ``expr base_full + size*
    (base_mini-base_full) + drawer*panel`` → ``setwidth`` — so drawer and
    size states compose. The tab is bang-safe, so load re-fires it.

    ``shift_main=True``: permanently shift every captured main-content box
    ``+left_bar`` at build time — retrofits the bar onto devices whose
    layout starts at x≈0 without touching their rects (pass mini_width =
    old width + left_bar).

    Returns a StageResult: ``button`` (parked param) / ``bar`` (jsui) ids, the
    created ``section_ids``, ``mini_width`` / ``full_width`` and the ``param``.
    """
    from .engines.design_system import js_sidecar_name
    from .engines.settings_bar import settings_bar_js
    from .jsui_contract import validate_jsui_contract
    from .parameters import ParameterSpec

    p = id_prefix
    acc = list(accent)
    dim = [0.55, 0.58, 0.61, 1.0]
    h = int(round(height if height is not None else device.height))
    lb = int(left_bar)
    # SINGLE-COLUMN cells: a small caption CENTRED on top of its value (an LCD
    # numbox by default, or a small kind:'dial' knob). This is for the SETUP
    # params; a drawer shows/tweaks config, so the VALUE reads better than a knob.
    # Keep the drawer to a few rows so caption+value never crowd.
    inset, cell_w, dial_sz, nw = 6, 40, 18, 40
    cw = int(panel_width) if panel_width else (2 * inset + cell_w)
    rows = max(1, len(controls) + (1 if size_row else 0))
    row_h = max(1, (h - content_top - 6) // rows)
    mini = int(round(mini_width))
    full = mini + cw
    park = 900
    pbg = list(panel_bgcolor) if panel_bgcolor else [0.115, 0.115, 0.125, 1.0]
    bbg = list(bar_bgcolor) if bar_bgcolor else [0.10, 0.10, 0.115, 1.0]

    # ---- 1. capture the existing on-canvas main content (to reflow) -----------
    bg_seen = False
    main: list = []                              # (varname, [x,y,w,h])
    for entry in device.boxes:
        b = entry["box"]
        if b.get("presentation") != 1:
            continue
        r = b.get("presentation_rect")
        if not r or len(r) < 4:
            continue
        if float(r[0]) >= park:
            continue                             # already parked/hidden
        if b.get("id") == bg_id:
            b["varname"] = bg_id                 # bg resizes (needs a scriptname)
            bg_seen = True
            continue
        vn = b.get("varname")
        # A `varname` with a space (native controls default it to the PARAM name,
        # e.g. "Low Vol") breaks `script sendbox <name> ...` — it parses only the
        # first token as the box name and the reflow silently no-ops. Assign a
        # space-free scripting name in that case (scripting name != param name, so
        # this is safe and doesn't touch automation).
        if not vn or " " in vn:
            bid = b.get("id", "")
            vn = bid if (bid and " " not in bid) else f"{p}_m{len(main)}"
            b["varname"] = vn
        if shift_main:
            b["presentation_rect"] = [float(r[0]) + lb, float(r[1]),
                                      float(r[2]), float(r[3])]
            r = b["presentation_rect"]
        main.append((vn, [float(v) for v in r[:4]]))

    # ---- 2. the thin LEFT bar: drawn ▾ opener + rotated label ------------------
    device.add_panel(f"{p}_bar_bg", [0, 0, lb, h], bgcolor=bbg, border=0)
    # the bar is a CLASSIC jsui box — hold its code to the jsui contract
    # (this is the gate that catches v8ui pointer-event handlers, which a
    # jsui silently never fires: the dead-opener bug).
    bar_code = validate_jsui_contract(settings_bar_js(accent=tuple(acc),
                                                      label=label))
    bar_fname = js_sidecar_name("settings_bar.js", bar_code)
    device.register_asset(bar_fname, bar_code, asset_type="TEXT", category="js")
    # border=0 + transparent bordercolor: kill Max's default black 1px jsui frame
    # (the "dark box around the left separator") — the bar's separation is a plain
    # grey vertical line, like the dividers elsewhere on the device.
    device.add_box({"box": {
        "id": f"{p}_bar", "maxclass": "jsui", "jsui_maxclass": "jsui",
        "filename": bar_fname, "numinlets": 1, "numoutlets": 1,
        "outlettype": [""], "parameter_enable": 0, "presentation": 1,
        "border": 0, "bordercolor": [0.0, 0.0, 0.0, 0.0],
        "presentation_rect": [0, 0, lb, h], "patching_rect": [40, 40, lb, h]}})
    # a grey vertical hairline at the bar's right edge (always visible, full
    # height — no top/bottom caps), replacing the old black frame. A live.line,
    # not a panel, so it renders above the backdrop and isn't a "box".
    device.add_live_line(f"{p}_sep", [lb, 0, 1, h],
                         linecolor=[0.30, 0.30, 0.32, 1.0])

    # ---- 3. the automatable enum param (parked live.text the bar drives) -------
    btn_id = device.add_live_text(
        f"{p}_toggle", param_name, [park, park, 1, 1],
        text_on="Open", text_off="Closed", mode=1,
        annotation="Show / hide the settings column (slides out on the left).",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2, enum=["Closed", "Open"],
                                initial=[0], initial_enable=True))
    device.add_line(btn_id, 0, f"{p}_bar", 0)      # param -> bar arrow display
    device.add_line(f"{p}_bar", 0, btn_id, 0)      # bar click -> param

    # ---- 4. the settings column (authored PARKED; slides in when open) ---------
    col: list = []                               # (varname, on_rect)

    def _tag(vn):
        device.boxes[-1]["box"]["varname"] = vn

    def _col(vn, on_rect):
        _tag(vn)
        col.append((vn, [float(v) for v in on_rect]))

    if column_bg:
        device.add_panel(f"{p}_panel", [park, 0, cw, h], bgcolor=pbg, border=0)
        _col(f"{p}_panel", [lb, 0, cw, h])

    section_ids = []
    for i, c in enumerate(controls):
        cy = content_top + i * row_h
        bid, name = c["id"], c["name"]
        kind = c.get("kind", "num")
        ctrl_h = 15 if kind == "num" else dial_sz
        oy = cy + max(0, (row_h - (9 + 1 + ctrl_h)) // 2)   # centre the cell
        # caption CENTRED on top
        device.add_comment(f"{bid}_cap", [park + inset, oy, cell_w, 9],
                           name.upper(), textcolor=dim, fontsize=7.0,
                           justification=1, fontname="Ableton Sans Medium")
        _col(f"{bid}_cap", [lb + inset, oy, cell_w, 9])
        # its value below — a numbox (default) or a small knob
        if kind == "num":
            nx = inset + (cell_w - nw) // 2
            device.add_number_box(bid, name, [park + nx, oy + 10, nw, 15],
                                  min_val=c["min"], max_val=c["max"],
                                  initial=c["init"], unitstyle=c["unit"],
                                  lcdcolor=acc, annotation=c.get("ann", ""))
            _col(bid, [lb + nx, oy + 10, nw, 15])
        else:
            dx = inset + (cell_w - dial_sz) // 2
            dkw = dict(min_val=c["min"], max_val=c["max"], initial=c["init"],
                       unitstyle=c["unit"], showname=0, shownumber=0,
                       activedialcolor=list(acc), annotation_name=c.get("ann", ""))
            if c.get("exp"):
                dkw["parameter_exponent"] = c["exp"]
            device.add_dial(bid, name, [park + dx, oy + 10, dial_sz, dial_sz],
                            **dkw)
            _col(bid, [lb + dx, oy + 10, dial_sz, dial_sz])
        section_ids.append(bid)

    if size_row:
        from .ui import tab as _tab
        sz_param = size_row.get("param_name", "Size")
        sz_init = int(size_row.get("init", 0))
        i = len(controls)
        cy = content_top + i * row_h
        oy = cy + max(0, (row_h - (9 + 1 + 15)) // 2)
        device.add_comment(f"{p}_size_cap", [park + inset, oy, cell_w, 9],
                           size_row.get("label", "SIZE"), textcolor=dim,
                           fontsize=7.0, justification=1,
                           fontname="Ableton Sans Medium")
        _col(f"{p}_size_cap", [lb + inset, oy, cell_w, 9])
        device.add_box(_tab(
            f"{p}_size", sz_param, [park + inset, oy + 10, cell_w, 15],
            options=["FULL", "MINI"], multiline=0,
            annotation="Device width: FULL shows everything, MINI keeps "
                       "the essentials (the face clips on the right).",
            parameter=ParameterSpec(name=sz_param, shortname=sz_param,
                                    parameter_type=2,
                                    enum=["FULL", "MINI"],
                                    initial=[sz_init],
                                    initial_enable=True)))
        _col(f"{p}_size", [lb + inset, oy + 10, cell_w, 15])
        section_ids.append(f"{p}_size")

    # ---- 5. reflow wiring: param -> sel -> closed / open message batches -------
    thisp, thisdev = f"{p}_this", f"{p}_thisdev"
    device.add_newobj(thisp, "thispatcher", numinlets=1, numoutlets=2,
                      outlettype=["", ""], patching_rect=[760, 1720, 90, 20])
    device.add_newobj(thisdev, "live.thisdevice", numinlets=1, numoutlets=3,
                      outlettype=["bang", "int", "int"], patching_rect=[520, 1600, 90, 20])
    sel = f"{p}_sel"
    device.add_newobj(sel, "sel 0 1", numinlets=1, numoutlets=3,
                      outlettype=["bang", "bang", ""], patching_rect=[700, 1630, 60, 20])
    device.add_line(btn_id, 0, sel, 0)
    ctrig, otrig = f"{p}_ctrig", f"{p}_otrig"
    device.add_newobj(ctrig, "t b", numinlets=1, numoutlets=1,
                      outlettype=["bang"], patching_rect=[700, 1660, 40, 20])
    device.add_newobj(otrig, "t b", numinlets=1, numoutlets=1,
                      outlettype=["bang"], patching_rect=[940, 1660, 40, 20])
    device.add_line(sel, 0, ctrig, 0)              # value 0 = Closed
    device.add_line(sel, 1, otrig, 0)              # value 1 = Open
    # loadbang forces the device CLOSED so a saved-open set reopens with no dead
    # zone (send 0 to the toggle -> Closed batch fires only if it was Open).
    device.add_box({"box": {"id": f"{p}_lb0", "maxclass": "message", "text": "0",
                            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                            "patching_rect": [520, 1660, 30, 20]}})
    device.add_line(thisdev, 0, f"{p}_lb0", 0)
    device.add_line(f"{p}_lb0", 0, btn_id, 0)

    counter = [0]
    yy = [1760]

    def _msg(text, x, y, trig, dest):
        mid = f"{p}_r{counter[0]}"
        counter[0] += 1
        device.add_box({"box": {"id": mid, "maxclass": "message", "text": text,
                                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                                "patching_rect": [x, y, 230, 18]}})
        device.add_line(trig, 0, mid, 0)
        device.add_line(mid, 0, dest, 0)

    def _pair(vn, closed_rect, open_rect):
        cr = " ".join(f"{v:g}" for v in closed_rect)
        orr = " ".join(f"{v:g}" for v in open_rect)
        _msg(f"script sendbox {vn} presentation_rect {cr}", 700, yy[0], ctrig, thisp)
        _msg(f"script sendbox {vn} presentation_rect {orr}", 960, yy[0], otrig, thisp)
        yy[0] += 20

    for vn, r in main:                             # main: closed=orig, open=+cw
        _pair(vn, r, [r[0] + cw, r[1], r[2], r[3]])
    for vn, on_r in col:                           # column: closed=parked, open=on
        _pair(vn, [park + (on_r[0] - lb), on_r[1], on_r[2], on_r[3]], on_r)
    if bg_seen:                                    # bg: resize with the device
        _pair(bg_id, [0, 0, mini, h], [0, 0, full, h])
    if size_row:
        # width authority: setwidth = f(size, drawer) so both states compose
        bm = int(round(size_row["mini"]))
        pk = f"{p}_wpak"
        device.add_newobj(pk, "pak 0 0", numinlets=2, numoutlets=1,
                          outlettype=[""], patching_rect=[520, 1720, 60, 20])
        ex = f"{p}_wexpr"
        device.add_newobj(
            ex, f"expr {mini} + $i1 * ({bm} - {mini}) + $i2 * {cw}",
            numinlets=2, numoutlets=1, outlettype=[""],
            patching_rect=[520, 1750, 230, 20])
        pw = f"{p}_wpre"
        device.add_newobj(pw, "prepend setwidth", numinlets=1, numoutlets=1,
                          outlettype=[""], patching_rect=[520, 1780, 110, 20])
        device.add_line(f"{p}_size", 0, pk, 0)
        device.add_line(btn_id, 0, pk, 1)
        device.add_line(pk, 0, ex, 0)
        device.add_line(ex, 0, pw, 0)
        device.add_line(pw, 0, thisdev, 0)
        # load re-fire: bang the size tab (bang-safe) so the restored size
        # reaches the authority after the drawer reset
        stb = f"{p}_stb"
        device.add_newobj(stb, "t b", numinlets=1, numoutlets=1,
                          outlettype=["bang"],
                          patching_rect=[520, 1690, 30, 20])
        device.add_line(thisdev, 0, stb, 0)
        device.add_line(stb, 0, f"{p}_size", 0)
    else:
        _msg(f"setwidth {mini}", 700, yy[0], ctrig, thisdev)
        _msg(f"setwidth {full}", 960, yy[0], otrig, thisdev)

    device.width = mini
    return stage_result(
        {
            "button": btn_id,
            "bar": f"{p}_bar",
            "section_ids": section_ids,
            "left_bar": lb,
            "panel_width": cw,
            "mini_width": mini,
            "full_width": full,
        },
        name="settings_sidebar",
        params={param_name: device.parameter(param_name),
                **({size_row.get("param_name", "Size"):
                    device.parameter(size_row.get("param_name", "Size"))}
                   if size_row else {})},
    )


def delta_listen(device, id_prefix, *, button_rect=None, x=30, y=30):
    """Δ (delta) audition — hear ONLY wet-minus-dry (dnksaus Hologram's "Delta").

    The classic saturation/EQ QA tool: what is the processor actually adding?
    Wire the processed signal into ``wet_in_l/r`` and the unprocessed signal into
    ``dry_in_l/r``; ``audio_out_l/r`` carries WET normally and (wet - dry) while
    the Δ toggle is lit. The toggle is a real automatable ``live.text`` param.
    """
    p = id_prefix
    btn = device.add_live_text(f"{p}_delta", "Delta", button_rect or [x, y, 36, 15],
                               text_on="\u0394", text_off="\u0394", mode=1)
    add = device.add_newobj(f"{p}_add", "+ 1", numinlets=2, numoutlets=1,
                            outlettype=[""], patching_rect=[x, y + 30, 45, 20])
    device.add_line(btn, 0, add, 0)
    ports = {}
    for ch in ("l", "r"):
        wet = device.add_newobj(f"{p}_wet_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[x, y + 60, 50, 20])
        dry = device.add_newobj(f"{p}_dry_{ch}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[x + 60, y + 60, 50, 20])
        sub = device.add_newobj(f"{p}_sub_{ch}", "-~", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[x, y + 90, 40, 20])
        sel = device.add_newobj(f"{p}_sel_{ch}", "selector~ 2 1", numinlets=3,
                                numoutlets=1, outlettype=["signal"],
                                patching_rect=[x, y + 120, 90, 20])
        device.add_line(add, 0, sel, 0)
        device.add_line(wet, 0, sel, 1)          # off -> wet passthrough
        device.add_line(wet, 0, sub, 0)
        device.add_line(dry, 0, sub, 1)
        device.add_line(sub, 0, sel, 2)          # on  -> wet - dry
        ports[f"wet_in_{ch}"] = device.box(wet).inlet(0)
        ports[f"dry_in_{ch}"] = device.box(dry).inlet(0)
        ports[f"audio_out_{ch}"] = device.box(sel).outlet(0)
    return stage_result(
        {"button": btn},
        name="delta_listen",
        params={f"{p}_delta": device.parameter(btn)},
        ports=ports,
    )


def latency_readout(device, id_prefix, latency_samples, *, rect,
                    fontsize=7.5, ignoreclick=1):
    """On-face "Latency: X ms" readout (dnksaus Hologram) — surface PDC honestly.

    ``latency_samples`` is the same fixed sample count the builder reported via
    ``device.latency``; the displayed ms tracks the LIVE samplerate through
    ``dspstate~`` so it is correct at 44.1/48/96 k. Rendered in a display-only
    ``message`` box (``ignoreclick`` so it is not an interactive control).
    """
    p = id_prefix
    lb = device.add_newobj(f"{p}_lb", "loadbang", numinlets=1, numoutlets=1,
                           outlettype=["bang"], patching_rect=[700, 40, 60, 20])
    dsp = device.add_newobj(f"{p}_dsp", "dspstate~", numinlets=1, numoutlets=4,
                            outlettype=["int", "float", "int", "int"],
                            patching_rect=[700, 70, 80, 20])
    ms = device.add_newobj(f"{p}_ms", f"expr {int(latency_samples)} * 1000. / $f1",
                           numinlets=1, numoutlets=1, outlettype=[""],
                           patching_rect=[700, 100, 160, 20])
    fmt = device.add_newobj(f"{p}_fmt", "sprintf set Latency: %.1f ms",
                            numinlets=1, numoutlets=1, outlettype=[""],
                            patching_rect=[700, 130, 170, 20])
    device.add_box({"box": {
        "id": f"{p}_msg", "maxclass": "message", "text": "Latency: -- ms",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "ignoreclick": ignoreclick, "fontsize": fontsize,
        "presentation": 1, "presentation_rect": list(rect),
        "patching_rect": [700, 160, 130, 20]}})
    device.add_line(lb, 0, dsp, 0)
    device.add_line(dsp, 1, ms, 0)
    device.add_line(ms, 0, fmt, 0)
    device.add_line(fmt, 0, f"{p}_msg", 0)
    return stage_result(
        {"message": f"{p}_msg"},
        name="latency_readout",
        params={},
        ports={},
    )


def report_latency(device, id_prefix, *, samples=None, ms=None,
                   extra_samples_expr=None):
    """Report the device's PDC latency to Live SAMPLERATE-CORRECTLY (the
    ``latency $1`` -> ``thispatcher`` wire, plus the static patcher ``latency``
    key as the value at load).

    The trap this closes: ``device.latency = 88`` bakes ONE samplerate's sample
    count into the patcher, so a 2 ms lookahead reported as 88 samples is only
    right at 44.1k — at 48/96/192k Live under-compensates and parallel chains
    smear. Choose the path by what the DSP actually holds constant:

    * ``samples=N`` — the delay is a FIXED SAMPLE COUNT at any samplerate
      (e.g. a fixed FIR tap count). Emits ``loadbang -> "N" -> "latency $1" ->
      thispatcher`` and sets ``device.latency = N``. Already
      samplerate-independent, so no recompute wire is needed.
    * ``ms=T`` — the delay is a FIXED TIME (e.g. ``Delay.read(samplerate *
      0.002)`` lookahead), so the sample count MUST recompute per samplerate.
      Emits ``loadbang -> dspstate~ -> expr int($f1 * T/1000 + 0.5) ->
      deferlow -> "latency $1" -> thispatcher`` — dspstate~ re-outputs on every
      DSP restart, so a samplerate change re-reports automatically (the same
      dspstate~ idiom :func:`latency_readout` uses for display). The static
      ``device.latency`` is set to the 44.1k count as the value-at-load.

    ``extra_samples_expr`` (ms path only) appends ``+ (<term>)`` to the expr —
    a constant-in-samples addend on top of the time-constant part (e.g. ``"3"``
    for a fixed decimator tail after a ms lookahead). Use a numeric literal if
    the static at-load value should include it too.

    Returns a stage whose ``samples_in`` port is the ``latency $1`` message
    inlet: a device whose latency is MODE-dependent (e.g. heat reporting 3
    samples only while 2x oversampling is on) wires its mode control through an
    ``expr``/``*`` into this port to re-report on every mode flip.
    """
    if (samples is None) == (ms is None):
        raise ValueError("report_latency: pass exactly one of samples= or ms=")
    if extra_samples_expr is not None and ms is None:
        raise ValueError("report_latency: extra_samples_expr requires the ms= path")
    p = id_prefix
    lb = device.add_newobj(f"{p}_lb", "loadbang", numinlets=1, numoutlets=1,
                           outlettype=["bang"], patching_rect=[760, 40, 60, 20])
    device.add_box({"box": {
        "id": f"{p}_msg", "maxclass": "message", "text": "latency $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [760, 130, 80, 20]}})
    thisp = device.add_newobj(f"{p}_thisp", "thispatcher",
                              numinlets=1, numoutlets=2, outlettype=["", ""],
                              patching_rect=[760, 160, 80, 20])
    device.add_line(f"{p}_msg", 0, thisp, 0)
    if samples is not None:
        device.latency = int(samples)
        device.add_box({"box": {
            "id": f"{p}_init", "maxclass": "message", "text": str(int(samples)),
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [760, 70, 50, 20]}})
        device.add_line(lb, 0, f"{p}_init", 0)
        device.add_line(f"{p}_init", 0, f"{p}_msg", 0)
    else:
        static = int(float(ms) * 44.1 + 0.5)
        if extra_samples_expr is not None:
            try:
                static += int(float(extra_samples_expr) + 0.5)
            except ValueError:
                pass  # non-literal term: static stays the time-constant part
        device.latency = static
        dsp = device.add_newobj(f"{p}_dsp", "dspstate~", numinlets=1, numoutlets=4,
                                outlettype=["int", "float", "int", "int"],
                                patching_rect=[760, 70, 80, 20])
        expr_text = f"expr int($f1 * {float(ms) * 0.001} + 0.5)"
        if extra_samples_expr is not None:
            expr_text += f" + ({extra_samples_expr})"
        ex = device.add_newobj(f"{p}_expr", expr_text,
                               numinlets=1, numoutlets=1, outlettype=[""],
                               patching_rect=[760, 100, 200, 20])
        defer = device.add_newobj(f"{p}_defer", "deferlow",
                                  numinlets=1, numoutlets=1, outlettype=[""],
                                  patching_rect=[880, 100, 60, 20])
        device.add_line(lb, 0, dsp, 0)
        device.add_line(dsp, 1, ex, 0)
        device.add_line(ex, 0, defer, 0)
        device.add_line(defer, 0, f"{p}_msg", 0)
    return stage_result(
        {"message": f"{p}_msg", "thispatcher": f"{p}_thisp"},
        name="report_latency",
        params={},
        ports={"samples_in": device.box(f"{p}_msg").inlet(0)},
    )


def mode_stack(device, id_prefix, *, rect, modes, param_name="Mode",
               tab_rect=None):
    """Generator MODE-STACK container (dnksaus-catalog kit item #9 — the
    Trig Mod / WaveLFO architecture): a narrow VERTICAL ``live.tab`` column
    whose automatable enum param swaps which of N pre-built editor stacks is
    visible, all sharing the SAME content rect.

    ``modes`` is a list of ``(label, [box_names...])`` — each mode owns the
    boxes (jsui editor + any companion chrome/controls) that should be visible
    ONLY in that mode; the caller builds every mode's content at the same
    coords BEFORE calling. Box names may be varnames or box ids; each must be
    SPACE-FREE (``script sendbox`` parses only the first token as the box
    name) and appear in exactly one mode. Boxes whose scripting name is unset
    or differs (native ``live.*`` controls default ``varname`` to the param
    longname — often WITH spaces) get the given name STAMPED as ``varname``
    (scripting name != param name, so automation is untouched — the
    settings_sidebar-proven rewrite).

    **Wiring — the dnksaus viewhide dataflow on the kit's Live-proven
    scripting bus:** their ``viewhide k`` abstraction is ``r ---view ->
    != k -> prepend hidden -> control box`` (Live_Stretch pages its controls
    through box-inlet ``hidden 0/1`` messages). A jsui's inlet 0 is a JS
    message dispatcher, so direct-inlet delivery would post ``no function
    hidden`` — instead the same ``!= k`` flag drives ``script sendbox <name>
    hidden $1`` messages into one ``thispatcher`` (exactly how
    :func:`settings_sidebar` moves boxes; ``sendbox`` sets BOX attributes
    without touching inlets). Per mode k one ``!= k``; per managed box one
    message box; hidden = (mode != k).

    No ``set_active`` gating is sent: none of the kit editors needs it, and
    Max only calls ``paint()`` on visible boxes — hiding IS the perf gate.

    **Initial state:** mode 0's boxes are authored visible, every other
    mode's are authored ``hidden: 1`` (correct first frame), and a
    ``live.thisdevice`` bang (NOT loadbang — kit convention for
    scripting-ready init) re-fires the tab's restored value through the
    wiring at load, so a set saved on mode 2 reopens showing mode 2.

    ``tab_rect`` defaults to a narrow column just LEFT of ``rect`` (~22px —
    Auto_Gate's "Time Mode" tab is 21px x 3 rows); the tab renders vertical
    via ``num_lines_* = len(modes)`` + ``multiline=1`` (corpus-exact).
    Returns a StageResult: ``tab`` / ``thispatcher`` / ``thisdevice`` ids,
    ``content_rect``, ``managed`` (label -> names) and the enum ``param``.
    """
    p = id_prefix
    modes = [(str(label), list(names)) for label, names in modes]
    if len(modes) < 2:
        raise ValueError("mode_stack needs at least 2 modes")
    labels = [label for label, _ in modes]

    # ---- resolve + sanitize the managed boxes ------------------------------
    by_varname = {}
    by_id = {}
    for entry in device.boxes:
        b = entry["box"]
        vn = b.get("varname")
        if vn is not None:
            by_varname.setdefault(vn, b)
        bid = b.get("id")
        if bid is not None:
            by_id.setdefault(bid, b)
    seen = {}
    for k, (label, names) in enumerate(modes):
        for name in names:
            if " " in name:
                raise ValueError(
                    f"mode_stack: managed name {name!r} contains a space — "
                    f"`script sendbox` parses only the first token as the box "
                    f"name; pass the box id and the recipe stamps it"
                )
            if name in seen:
                raise ValueError(
                    f"mode_stack: {name!r} appears in modes "
                    f"{seen[name]!r} and {label!r}; a box may belong to "
                    f"exactly one mode (leave shared chrome unmanaged)"
                )
            seen[name] = label
            box = by_varname.get(name) or by_id.get(name)
            if box is None:
                raise ValueError(
                    f"mode_stack: no box with varname or id {name!r} — build "
                    f"every mode's content before calling"
                )
            if box.get("varname") != name:
                box["varname"] = name          # stamp a space-free script name
            if k > 0:
                box["hidden"] = 1              # authored initial: mode 0 shows

    # ---- the vertical mode tab (the automatable enum param) ----------------
    n = len(modes)
    if tab_rect is None:
        tab_rect = [rect[0] - 22, rect[1], 22, 16 * n]
    tab = device.add_tab(f"{p}_tab", param_name, list(tab_rect),
                         options=labels, multiline=1,
                         num_lines_presentation=n, num_lines_patching=n)

    # ---- visibility wiring: tab -> != k -> sendbox hidden -> thispatcher ---
    thisp = f"{p}_thisp"
    device.add_newobj(thisp, "thispatcher", numinlets=1, numoutlets=2,
                      outlettype=["", ""], patching_rect=[900, 1740, 90, 20])
    counter = 0
    for k, (_label, names) in enumerate(modes):
        ne = f"{p}_ne{k}"
        device.add_newobj(ne, f"!= {k}", numinlets=2, numoutlets=1,
                          outlettype=["int"],
                          patching_rect=[900 + 260 * k, 1640, 40, 20])
        device.add_line(tab, 0, ne, 0)
        for name in names:
            mid = f"{p}_h{counter}"
            counter += 1
            device.add_box({"box": {
                "id": mid, "maxclass": "message",
                "text": f"script sendbox {name} hidden $1",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [900 + 260 * k, 1670 + 22 * counter,
                                  240, 18]}})
            device.add_line(ne, 0, mid, 0)
            device.add_line(mid, 0, thisp, 0)

    # ---- load-time re-sync: live.thisdevice bang -> the tab re-outputs its
    # restored value (NOT loadbang: scripting isn't ready at loadbang).
    thisdev = f"{p}_thisdev"
    device.add_newobj(thisdev, "live.thisdevice", numinlets=1, numoutlets=3,
                      outlettype=["bang", "int", "int"],
                      patching_rect=[900, 1580, 90, 20])
    init = f"{p}_init"
    device.add_newobj(init, "t b", numinlets=1, numoutlets=1,
                      outlettype=["bang"], patching_rect=[900, 1610, 40, 20])
    device.add_line(thisdev, 0, init, 0)
    device.add_line(init, 0, tab, 0)

    return stage_result(
        {
            "tab": tab,
            "thispatcher": thisp,
            "thisdevice": thisdev,
            "content_rect": list(rect),
            "managed": {label: list(names) for label, names in modes},
        },
        name="mode_stack",
        params={param_name: device.parameter(tab)},
    )


def randomize_matrix(device, id_prefix, *, rect, targets, columns=4,
                     chip_h=15, gap=2, labels=None, seed=True,
                     variation=False):
    """Per-param RANDOMIZE page (dnksaus Auto Gate) — catalog #11 + #12.

    Every entry in ``targets`` (box ids/refs of NATIVE param controls already
    on the device) gets an enable chip; the RND button rolls a fresh random
    value into each ENABLED target's inlet — through the control, so Live
    sees an ordinary value change (undoable, automation-recordable). ALL /
    NONE quick-set the chips. Chip states are stored-only params
    (``Rnd <target longname>``, ``parameter_invisible=1``): saved with the
    set, absent from automation menus.

    Value generation is derived from each target's registered
    :class:`ParameterSpec` at BUILD time: enum/stepped/integer params get
    ``random <n_values>`` (+ offset); continuous params get
    ``random 10001 -> scale 0 10000 <min> <max>`` (uniform across the range).
    ``random`` objects are seeded at load from ``cpuclock`` (+k per lane so
    lanes decorrelate) — the Max-8-safe equivalent of dnksaus' v8
    ``Date.now()`` seed idiom; without it every load replays one sequence.
    No ``---disarm`` guard (corpus Tempo Scale Setter) is used: unlike a
    set-level tempo/scale roll, device-param randomize is a plain undoable
    edit.

    Layout: ``rect`` hosts a header row (RND / ALL / NONE message buttons,
    non-param by design — automating "randomize" from a clip is a footgun)
    and a ``columns``-wide chip grid growing downward; size ``rect`` for
    ``1 + ceil(len(targets)/columns)`` rows of ``chip_h + gap``.

    ``variation=True`` (catalog #27, Chordsaus "Random Variation %"): adds a
    ``Rnd Var`` % param to the header and rolls each enabled target AROUND
    ITS CURRENT VALUE (± var% of its range, clipped) instead of uniformly
    across the range — humanize-style nudging. Each target's last value is
    tracked from its own outlet; stepped targets round after the clip.
    """
    from .parameters import ParameterSpec

    p = id_prefix
    if not targets:
        raise ValueError("randomize_matrix: targets must be non-empty")
    tgt_ids = [str(t) for t in targets]
    if len(set(tgt_ids)) != len(tgt_ids):
        raise ValueError("randomize_matrix: duplicate targets")
    specs = []
    for t in tgt_ids:
        spec = device.parameter(device.box(t))
        if spec is None:
            raise ValueError(
                f"randomize_matrix: {t!r} has no registered parameter spec")
        specs.append(spec)
    labels = labels or {}

    x, y, w, _h = rect
    px, py = 700, 1700          # patching-side plumbing column

    # ---- header row: RND / ALL / NONE (message boxes: clickable, non-param) --
    n_hdr = 4 if variation else 3
    bw = (w - (n_hdr - 1) * gap) / float(n_hdr)
    hdr = []
    for i, (bid, txt) in enumerate(
            [(f"{p}_rnd", "RND"), (f"{p}_all", "ALL"), (f"{p}_none", "NONE")]):
        device.add_box({"box": {
            "id": bid, "maxclass": "message", "text": txt,
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "fontsize": 8.0, "textjustification": 1,
            "presentation": 1,
            "presentation_rect": [x + i * (bw + gap), y, bw, chip_h],
            "patching_rect": [px + i * 90, py, 60, 20]}})
        hdr.append(bid)
    trig = device.add_newobj(f"{p}_trig", "t b", numinlets=1, numoutlets=1,
                             outlettype=["bang"],
                             patching_rect=[px, py + 30, 40, 20])
    device.add_line(f"{p}_rnd", 0, trig, 0)
    all_int = device.add_newobj(f"{p}_all_i", "t 1", numinlets=1, numoutlets=1,
                                outlettype=["int"],
                                patching_rect=[px + 90, py + 30, 30, 20])
    none_int = device.add_newobj(f"{p}_none_i", "t 0", numinlets=1,
                                 numoutlets=1, outlettype=["int"],
                                 patching_rect=[px + 180, py + 30, 30, 20])
    device.add_line(f"{p}_all", 0, all_int, 0)
    device.add_line(f"{p}_none", 0, none_int, 0)
    if variation:
        from .parameters import ParameterSpec as _PS
        device.add_number_box(
            f"{p}_var", "Rnd Var", [x + 3 * (bw + gap), y, bw, chip_h],
            min_val=0.0, max_val=100.0, initial=15.0,
            parameter=_PS(name="Rnd Var", shortname="Rnd Var",
                          minimum=0.0, maximum=100.0, initial=15.0,
                          initial_enable=True, units="%ld %", unitstyle=9))
        var_td = device.add_newobj(f"{p}_var_td", "live.thisdevice",
                                   numinlets=1, numoutlets=3,
                                   outlettype=["bang", "int", "int"],
                                   patching_rect=[px + 380, py, 90, 20])
        var_tb = device.add_newobj(f"{p}_var_tb", "t b", numinlets=1,
                                   numoutlets=1, outlettype=["bang"],
                                   patching_rect=[px + 380, py + 30, 30, 20])
        device.add_line(var_td, 0, var_tb, 0)
        device.add_line(var_tb, 0, f"{p}_var", 0)

    # ---- seed clock (one per matrix; per-lane +k decorrelates) ---------------
    if seed:
        lb = device.add_newobj(f"{p}_seed_lb", "loadbang", numinlets=1,
                               numoutlets=1, outlettype=["bang"],
                               patching_rect=[px + 280, py, 60, 20])
        clk = device.add_newobj(f"{p}_seed_clk", "cpuclock", numinlets=1,
                                numoutlets=1, outlettype=["float"],
                                patching_rect=[px + 280, py + 30, 60, 20])
        device.add_line(lb, 0, clk, 0)

    chip_w = (w - (columns - 1) * gap) / float(columns)
    params = {}
    chips = []
    for k, (tid, spec) in enumerate(zip(tgt_ids, specs)):
        row, col = divmod(k, columns)
        cy = y + (chip_h + gap) * (row + 1)
        cx = x + col * (chip_w + gap)
        label = labels.get(tid) or spec.shortname or spec.name
        chip = device.add_live_text(
            f"{p}_chip{k}", f"Rnd {spec.name}",
            [cx, cy, chip_w, chip_h],
            text_on=label, text_off=label, mode=1, fontsize=8.0,
            annotation=f"Include '{spec.name}' when RND rolls new values.",
            parameter=ParameterSpec(
                name=f"Rnd {spec.name}", shortname=label[:15] or "Rnd",
                parameter_type=2, enum=["off", "on"], initial=[1],
                initial_enable=True, invisible=1))
        chips.append(chip)
        gate = device.add_newobj(f"{p}_gate{k}", "gate", numinlets=2,
                                 numoutlets=1, outlettype=[""],
                                 patching_rect=[px + k * 90, py + 70, 40, 20])
        device.add_line(chip, 0, gate, 0)          # chip state -> gate control
        device.add_line(trig, 0, gate, 1)          # RND bang   -> gate data
        device.add_line(all_int, 0, chip, 0)
        device.add_line(none_int, 0, chip, 0)

        # value generator from the target's spec
        is_enum = spec.enum is not None
        stepped = (spec.steps is not None or spec.integer_like or is_enum
                   or spec.parameter_type == 1)
        lo = 0.0 if spec.minimum is None else float(spec.minimum)
        hi = float(len(spec.enum) - 1) if is_enum and spec.maximum is None \
            else (1.0 if spec.maximum is None else float(spec.maximum))
        if variation:
            # roll AROUND the current value: cur + rand(-1..1)·(var%·range)
            rng = hi - lo
            cur = device.add_newobj(f"{p}_cur{k}", "f", numinlets=2,
                                    numoutlets=1, outlettype=["float"],
                                    patching_rect=[px + k * 90, py + 160, 30, 20])
            device.add_line(tid, 0, cur, 1)          # track target's value
            tbb = device.add_newobj(f"{p}_tb{k}", "t b b", numinlets=1,
                                    numoutlets=2,
                                    outlettype=["bang", "bang"],
                                    patching_rect=[px + k * 90, py + 70, 50, 20])
            device.add_line(gate, 0, tbb, 0)
            rnd = device.add_newobj(f"{p}_val{k}", "random 10001",
                                    numinlets=2, numoutlets=1,
                                    outlettype=["int"],
                                    patching_rect=[px + k * 90, py + 100, 80, 20])
            sc = device.add_newobj(f"{p}_sc{k}", "scale 0 10000 -1. 1.",
                                   numinlets=6, numoutlets=1, outlettype=[""],
                                   patching_rect=[px + k * 90, py + 130, 130, 20])
            spread = device.add_newobj(f"{p}_sp{k}", "* 0.", numinlets=2,
                                       numoutlets=1, outlettype=["float"],
                                       patching_rect=[px + k * 90, py + 160, 40, 20])
            vfrac = device.add_newobj(f"{p}_vf{k}", f"* {rng / 100.0:.6g}",
                                      numinlets=2, numoutlets=1,
                                      outlettype=["float"],
                                      patching_rect=[px + 380, py + 70 + k * 30, 60, 20])
            device.add_line(f"{p}_var", 0, vfrac, 0)
            device.add_line(vfrac, 0, spread, 1)
            addc = device.add_newobj(f"{p}_ad{k}", "+ 0.", numinlets=2,
                                     numoutlets=1, outlettype=["float"],
                                     patching_rect=[px + k * 90, py + 190, 40, 20])
            device.add_line(cur, 0, addc, 1)
            clip = device.add_newobj(f"{p}_cl{k}",
                                     f"clip {lo:.6g} {hi:.6g}",
                                     numinlets=3, numoutlets=1,
                                     outlettype=[""],
                                     patching_rect=[px + k * 90, py + 220, 90, 20])
            # right bang FIRST: pull current into the adder's cold inlet
            device.add_line(tbb, 1, cur, 0)
            device.add_line(tbb, 0, rnd, 0)
            device.add_line(rnd, 0, sc, 0)
            device.add_line(sc, 0, spread, 0)
            device.add_line(spread, 0, addc, 0)
            device.add_line(addc, 0, clip, 0)
            src = clip
            if stepped:
                rr = device.add_newobj(f"{p}_rd{k}", "expr round($f1)",
                                       numinlets=1, numoutlets=1,
                                       outlettype=[""],
                                       patching_rect=[px + k * 90, py + 250, 100, 20])
                device.add_line(clip, 0, rr, 0)
                src = rr
            device.add_line(src, 0, tid, 0)
            if seed:
                sd = device.add_newobj(f"{p}_sd{k}", f"expr int($f1) + {k}",
                                       numinlets=1, numoutlets=1,
                                       outlettype=[""],
                                       patching_rect=[px + 280, py + 70 + k * 30, 110, 20])
                pre = device.add_newobj(f"{p}_ps{k}", "prepend seed",
                                        numinlets=1, numoutlets=1,
                                        outlettype=[""],
                                        patching_rect=[px + 400, py + 70 + k * 30, 90, 20])
                device.add_line(clk, 0, sd, 0)
                device.add_line(sd, 0, pre, 0)
                device.add_line(pre, 0, rnd, 0)
            params[f"Rnd {spec.name}"] = device.parameter(chip)
            continue
        if stepped:
            n_values = (len(spec.enum) if is_enum
                        else (spec.steps if spec.steps
                              else int(round(hi - lo)) + 1))
            rnd = device.add_newobj(f"{p}_val{k}", f"random {int(n_values)}",
                                    numinlets=2, numoutlets=1,
                                    outlettype=["int"],
                                    patching_rect=[px + k * 90, py + 100, 80, 20])
            src = rnd
            if lo:
                off = device.add_newobj(f"{p}_off{k}", f"+ {int(lo)}",
                                        numinlets=2, numoutlets=1,
                                        outlettype=["int"],
                                        patching_rect=[px + k * 90, py + 130, 50, 20])
                device.add_line(rnd, 0, off, 0)
                src = off
        else:
            rnd = device.add_newobj(f"{p}_val{k}", "random 10001",
                                    numinlets=2, numoutlets=1,
                                    outlettype=["int"],
                                    patching_rect=[px + k * 90, py + 100, 80, 20])
            def _f(v):
                s = f"{v:.6g}"
                return s if ("." in s or "e" in s) else s + "."
            sc = device.add_newobj(f"{p}_sc{k}",
                                   f"scale 0 10000 {_f(lo)} {_f(hi)}",
                                   numinlets=6, numoutlets=1, outlettype=[""],
                                   patching_rect=[px + k * 90, py + 130, 130, 20])
            device.add_line(rnd, 0, sc, 0)
            src = sc
        device.add_line(gate, 0, rnd, 0)
        device.add_line(src, 0, tid, 0)
        if seed:
            sd = device.add_newobj(f"{p}_sd{k}", f"expr int($f1) + {k}",
                                   numinlets=1, numoutlets=1, outlettype=[""],
                                   patching_rect=[px + 280, py + 70 + k * 30, 110, 20])
            pre = device.add_newobj(f"{p}_ps{k}", "prepend seed",
                                    numinlets=1, numoutlets=1, outlettype=[""],
                                    patching_rect=[px + 400, py + 70 + k * 30, 90, 20])
            device.add_line(clk, 0, sd, 0)
            device.add_line(sd, 0, pre, 0)
            device.add_line(pre, 0, rnd, 0)
        params[f"Rnd {spec.name}"] = device.parameter(chip)

    return stage_result(
        {"rnd": f"{p}_rnd", "all": f"{p}_all", "none": f"{p}_none",
         "chips": chips},
        name="randomize_matrix",
        params=params,
        ports={"trigger_in": device.box(trig).inlet(0)},
    )


_HEADER_CAPTIONS = {"source": "SRC", "map": "MAP", "target": "TARGET",
                    "depth": "DEPTH", "min": "MIN", "max": "MAX",
                    "bipolar": "±", "mode": "R M", "add": "+",
                    "bar": "", "unmap": "✗", "ratio": "×"}


def modulator_header_row(device, id_prefix, *, at, columns, dim_color=None,
                         fontsize=5.8, captions=None):
    """ONE shared caption strip above a stacked modulator-slot column
    (catalog #17: the ``±`` / ``R M`` table grammar).

    ``at`` is the on-face ``[x, y]`` where the FIRST stamped slot row starts;
    captions are laid out from the ``columns`` map the slot returns in
    ``ids["columns"]`` (each value an ``(x, w)`` pair relative to the row), so
    header and rows stay aligned however the slot was configured
    (icon / mode_switch / add_chip all shift the geometry).
    """
    x0, y0 = at
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    texts = dict(_HEADER_CAPTIONS)
    if captions:
        texts.update(captions)
    made = []
    for key, (cx, cw) in sorted(columns.items(), key=lambda kv: kv[1][0]):
        text = texts.get(key, key.upper())
        if not text:            # self-evident columns (e.g. the value bar)
            continue
        cid = f"{id_prefix}_h_{key}"
        device.add_comment(cid, [x0 + cx, y0 - 9, max(cw, 16), 8],
                           text, textcolor=dim, fontsize=fontsize)
        made.append(cid)
    return stage_result({"captions": made}, name="modulator_header_row",
                        params={}, ports={})


def mapping_summary_chip(device, id_prefix, *, rect, accent,
                         text_color=None, dim_color=None, fontsize=7.5):
    """Title-strip mapping summary (catalog #22 + #26): a one-line chip that
    mirrors a slot's mapping state anywhere on the face — including the 16px
    title zone, so a COLLAPSED device still reads its mapping.

    Layout: ``[dot] Param-name    device-name`` — the dot lights accent while
    mapped; unmapped shows a dim ``—``. Build the slot with
    ``uplink_pname=True`` / ``uplink_dname=True`` and fan the parent-side
    uplink through ``route pname dname mapped`` into this stage's
    ``pname_in`` / ``dname_in`` / ``mapped_in`` ports (multi-word names
    arrive as atom lists; ``prepend set`` renders them verbatim).
    """
    from .ui import textedit

    p = id_prefix
    x, y, w, h = rect
    tx = list(text_color) if text_color else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    acc = list(accent)

    pw = int((w - 7) * 0.55)
    device.add_box({"box": {
        "id": f"{p}_dot", "maxclass": "live.line", "justification": 1,
        "numinlets": 1, "numoutlets": 0, "linecolor": dim,
        "presentation": 1, "presentation_rect": [x, y + h // 2 - 2, 4, 4],
        "patching_rect": [820, 1700, 4, 4]}})
    device.add_box(textedit(
        f"{p}_txt", [x + 7, y, pw, h], text="—", fontsize=fontsize,
        textcolor=tx, bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    device.add_box(textedit(
        f"{p}_dev", [x + 9 + pw, y, w - pw - 9, h], text="",
        fontsize=fontsize - 0.5, textcolor=dim,
        bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=2, ignoreclick=1))
    # NOTE the mapper js already emits ``pname set <name>`` / ``dname set
    # <name>`` — after the parent's ``route pname dname`` the payload is a
    # ready-made textedit ``set`` message, so it feeds the fields DIRECTLY
    # (adding another ``prepend set`` double-wraps and corrupts it).
    # mapped 0/1 -> dot color + clear-to-dash on unmap
    device.add_newobj(f"{p}_msel", "sel 1 0", numinlets=3, numoutlets=3,
                      outlettype=["bang", "bang", ""],
                      patching_rect=[960, 1700, 60, 20])
    on_txt = "linecolor {} {} {} 1.".format(*[round(c, 3) for c in acc[:3]])
    off_txt = "linecolor {} {} {} 1.".format(*[round(c, 3) for c in dim[:3]])
    device.add_box({"box": {
        "id": f"{p}_c_on", "maxclass": "message", "text": on_txt,
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1730, 150, 20]}})
    device.add_box({"box": {
        "id": f"{p}_c_off", "maxclass": "message", "text": off_txt,
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1760, 150, 20]}})
    device.add_box({"box": {
        "id": f"{p}_clr_p", "maxclass": "message", "text": "set —",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1790, 60, 20]}})
    device.add_box({"box": {
        "id": f"{p}_clr_d", "maxclass": "message", "text": "set",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [960, 1820, 50, 20]}})
    device.add_line(f"{p}_msel", 0, f"{p}_c_on", 0)
    device.add_line(f"{p}_msel", 1, f"{p}_c_off", 0)
    device.add_line(f"{p}_msel", 1, f"{p}_clr_p", 0)
    device.add_line(f"{p}_msel", 1, f"{p}_clr_d", 0)
    device.add_line(f"{p}_c_on", 0, f"{p}_dot", 0)
    device.add_line(f"{p}_c_off", 0, f"{p}_dot", 0)
    device.add_line(f"{p}_clr_p", 0, f"{p}_txt", 0)
    device.add_line(f"{p}_clr_d", 0, f"{p}_dev", 0)
    return stage_result(
        {"text": f"{p}_txt", "device_text": f"{p}_dev", "dot": f"{p}_dot"},
        name="mapping_summary_chip",
        params={},
        ports={"pname_in": device.box(f"{p}_txt").inlet(0),
               "dname_in": device.box(f"{p}_dev").inlet(0),
               "mapped_in": device.box(f"{p}_msel").inlet(0)},
    )


_LANE_ROTATOR_JS = """// lane_rotator — recompute the full matrix~ crosspoint grid (T06, #23/#24)
// Stateful on purpose: `rot <n>` / `mono <0|1>` each recompute with the
// cached other, so update ORDER never matters (params restore in any order,
// and banging a live.text toggle would FLIP it — never bang toggles).
autowatch = 1;
inlets = 1;
outlets = 1;

var N = parseInt(jsarguments[1] || 2, 10);
var R = 0;
var M = 0;

function grid() {
    var j, src;
    for (j = 0; j < N; j++) {
        src = M ? 0 : ((j + R) % N + N) % N;
        for (var i = 0; i < N; i++) {
            outlet(0, [i, j, (i === src) ? 1.0 : 0.0]);
        }
    }
}

function rot(v) { R = Math.round(v); grid(); }

function mono(v) { M = v ? 1 : 0; grid(); }
"""


def lane_rotator(device, id_prefix, *, n, accent=None, rotate_rect=None,
                 mono_rect=None, ramp_ms=20):
    """Rotate / Mono lane routing (catalog #23 + #24, Multi Shaper).

    A ``matrix~ n n 0.`` sits between the engine's lane signals and the
    mapping rows: ``Rotate k`` feeds row ``j`` from lane ``(j+k) % n``;
    ``Mono`` collapses every row onto lane 0. A tiny js recomputes the FULL
    n×n crosspoint grid on every change (matrix~ crosspoints persist, so
    partial updates would leave stale connections).

    Ports: ``lane_in_<k>`` (matrix~ signal inlets) and ``row_out_<k>``
    (matrix~ signal outlets) — wire lanes in, rows out. Params: ``Rotate``
    (int 0..n-1) + ``Mono`` (toggle), both automatable.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec

    p = id_prefix
    if n < 2:
        raise ValueError("lane_rotator: n must be >= 2")
    acc = list(accent) if accent else [0.85, 0.87, 0.89, 1.0]

    code = _LANE_ROTATOR_JS
    fname = js_sidecar_name("lane_rotator.js", code)
    device.register_asset(fname, code, asset_type="TEXT", category="js")

    mx = device.add_newobj(
        f"{p}_mx", f"matrix~ {n} {n} 0. @ramp {int(ramp_ms)}",
        numinlets=n + 1, numoutlets=n + 1,
        outlettype=["signal"] * n + [""],
        patching_rect=[600, 2000, 60 + 26 * n, 22])
    device.add_number_box(
        f"{p}_rot", "Rotate", rotate_rect or [900, 900, 1, 1],
        min_val=0.0, max_val=float(n - 1), initial=0.0, lcdcolor=acc,
        parameter=ParameterSpec(name="Rotate", shortname="Rotate",
                                parameter_type=1, minimum=0, maximum=n - 1,
                                initial=[0], initial_enable=True))
    device.add_live_text(
        f"{p}_mono", "Mono", mono_rect or [900, 900, 1, 1],
        text_on="MONO", text_off="MONO", mode=1, fontsize=7.0,
        annotation="Collapse every row onto lane 1's output.",
        parameter=ParameterSpec(name="Mono", shortname="Mono",
                                parameter_type=2, enum=["OFF", "ON"],
                                initial=[0], initial_enable=True))
    js = device.add_newobj(
        f"{p}_js", f"js {fname} {n}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[600, 1970, 160, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    pre_r = device.add_newobj(f"{p}_pre_r", "prepend rot", numinlets=1,
                              numoutlets=1, outlettype=[""],
                              patching_rect=[600, 1940, 80, 20])
    pre_m = device.add_newobj(f"{p}_pre_m", "prepend mono", numinlets=1,
                              numoutlets=1, outlettype=[""],
                              patching_rect=[690, 1940, 90, 20])
    device.add_line(f"{p}_rot", 0, pre_r, 0)
    device.add_line(f"{p}_mono", 0, pre_m, 0)
    device.add_line(pre_r, 0, js, 0)
    device.add_line(pre_m, 0, js, 0)
    device.add_line(js, 0, mx, 0)
    # matrix~ crosspoints all start at 0 and live params do NOT reliably
    # re-emit initials at load — bang the ROTATE numbox (bang on live.numbox
    # re-OUTPUTS; never bang a live.text toggle, that FLIPS it) so the grid
    # computes at every load. Mono/Rotate changes recompute statefully.
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[600, 1880, 90, 20])
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[600, 1910, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, f"{p}_rot", 0)
    ports = {}
    for k in range(n):
        ports[f"lane_in_{k}"] = device.box(mx).inlet(k)
        ports[f"row_out_{k}"] = device.box(mx).outlet(k)
    return stage_result(
        {"matrix": f"{p}_mx", "rotate": f"{p}_rot", "mono": f"{p}_mono"},
        name="lane_rotator",
        params={"Rotate": device.parameter(device.box(f"{p}_rot")),
                "Mono": device.parameter(device.box(f"{p}_mono"))},
        ports=ports,
    )


def page_selector(device, id_prefix, *, at, n_pages, rows_per_page,
                  accent=None, cell=14, param_name="Page", manage=None):
    """Vertical page selector for stacked mapping rows (catalog #25).

    A slim vertical ``live.tab`` (one dot-cell per page, automatable enum
    ``param_name``) that broadcasts ``pagewin <lo> <hi>`` — build the slot
    with ``pages=True`` and fan this stage's ``pagewin_out`` port into every
    stamped row's inlet 0 (alongside ``announce``/``lanes``). Rows are
    1-based: page ``k`` shows rows ``k*rows_per_page+1 ..
    (k+1)*rows_per_page``.

    ``manage``: dict of ``{parent_box_varname: 1-based_row_index}`` — the
    LIVE-PROVEN hiding path: the parent computes each managed box's hidden
    state and delivers it via ``script sendbox <varname> hidden $1`` through
    a parent-side thispatcher (the exact mode_stack mechanism). Prefer this
    over the slot-side ``pages=`` broadcast: a thispatcher INSIDE a stamped
    bpatcher does NOT hide the containing box (Live-verified failure).
    """
    from .parameters import ParameterSpec
    from .ui import tab

    p = id_prefix
    x, y = at
    labels = [str(k + 1) for k in range(n_pages)]
    device.add_box(tab(
        f"{p}_tab", param_name, [x, y, cell, cell * n_pages],
        options=labels, fontsize=6.5, multiline=1,
        num_lines_presentation=n_pages, num_lines_patching=n_pages,
        spacing_x=1.0, spacing_y=1.0,
        annotation="Mapping page — rows swap in groups at the same rect.",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2, enum=list(labels),
                                initial=[0], initial_enable=True)))
    # ORDER-SAFE window compute: t i i guarantees hi lands in the pak's
    # COLD inlet before lo fires the HOT one (bare fan-out from one `* N`
    # races and broadcasts a stale hi).
    tt = device.add_newobj(f"{p}_t", "t i i", numinlets=1, numoutlets=2,
                           outlettype=["int", "int"],
                           patching_rect=[840, 1940, 50, 20])
    lo = device.add_newobj(f"{p}_lo", f"* {int(rows_per_page)}",
                           numinlets=2, numoutlets=1, outlettype=["int"],
                           patching_rect=[820, 1970, 50, 20])
    lo2 = device.add_newobj(f"{p}_lo2", f"* {int(rows_per_page)}",
                            numinlets=2, numoutlets=1, outlettype=["int"],
                            patching_rect=[890, 1970, 50, 20])
    hi = device.add_newobj(f"{p}_hi", f"+ {int(rows_per_page) - 1}",
                           numinlets=2, numoutlets=1, outlettype=["int"],
                           patching_rect=[890, 2000, 50, 20])
    pk = device.add_newobj(f"{p}_pk", "pak 0 0", numinlets=2, numoutlets=1,
                           outlettype=[""], patching_rect=[840, 2030, 60, 20])
    pre = device.add_newobj(f"{p}_pre", "prepend pagewin", numinlets=1,
                            numoutlets=1, outlettype=[""],
                            patching_rect=[840, 2060, 110, 20])
    device.add_line(f"{p}_tab", 0, tt, 0)
    device.add_line(tt, 1, lo2, 0)      # right first: hi -> pak cold
    device.add_line(lo2, 0, hi, 0)
    device.add_line(hi, 0, pk, 1)
    device.add_line(tt, 0, lo, 0)       # then lo -> pak hot fires
    device.add_line(lo, 0, pk, 0)
    device.add_line(pk, 0, pre, 0)
    # re-broadcast at load so freshly-restored pages hide their off rows
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[840, 1880, 90, 20])
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[840, 1910, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, f"{p}_tab", 0)
    if manage:
        thisp = device.add_newobj(f"{p}_this", "thispatcher", numinlets=1,
                                  numoutlets=2, outlettype=["", ""],
                                  patching_rect=[1000, 2060, 80, 20])
        r = int(rows_per_page)
        for mi, (vn, idx) in enumerate(sorted(manage.items())):
            if " " in vn:
                raise ValueError(
                    f"page_selector: managed varname {vn!r} contains a "
                    "space — script sendbox silently no-ops")
            i0 = int(idx) - 1
            ex = device.add_newobj(
                f"{p}_mx{mi}",
                f"expr ({i0} < $i1 * {r}) || ({i0} > ($i1 * {r} + {r - 1}))",
                numinlets=1, numoutlets=1, outlettype=[""],
                patching_rect=[1000, 1940 + 30 * mi, 230, 20])
            device.add_box({"box": {
                "id": f"{p}_mm{mi}", "maxclass": "message",
                "text": f"script sendbox {vn} hidden $1",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [1240, 1940 + 30 * mi, 200, 20]}})
            device.add_line(f"{p}_tab", 0, ex, 0)
            device.add_line(ex, 0, f"{p}_mm{mi}", 0)
            device.add_line(f"{p}_mm{mi}", 0, thisp, 0)
    return stage_result(
        {"tab": f"{p}_tab"},
        name="page_selector",
        params={param_name: device.parameter(device.box(f"{p}_tab"))},
        ports={"pagewin_out": device.box(pre).outlet(0)},
    )


def takeover_menu(device, id_prefix, *, rect, policies=("Latest", "Hold",
                                                        "Pickup"),
                  param_name="Takeover", accent=None):
    """Takeover policy menu (catalog #27, Chordsaus): how an incoming
    control merges with mapped/engine values. The recipe is the CONTRACT
    layer — an automatable enum + a ``policy_out`` port; the semantics are
    engine-side (wire ``policy_out`` into whatever merges your sources).
    Pair with :func:`randomize_matrix` ``variation=True`` for Chordsaus'
    Random-Variation half of the panel.
    """
    from .parameters import ParameterSpec
    from .ui import menu as _menu

    p = id_prefix
    device.add_box(_menu(
        f"{p}_menu", param_name, list(rect), options=list(policies),
        fontsize=8.0,
        annotation="How incoming control input merges with the mapped "
                   "value: Latest wins / Hold until release / Pickup on "
                   "value cross.",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2, enum=list(policies),
                                initial=[0], initial_enable=True)))
    return stage_result(
        {"menu": f"{p}_menu"},
        name="takeover_menu",
        params={param_name: device.parameter(device.box(f"{p}_menu"))},
        ports={"policy_out": device.box(f"{p}_menu").outlet(0)},
    )


def mod_source_matrix(device, id_prefix, *, rect, sources, n_targets,
                      param_name="Mod Matrix", accent=None, dim_color=None):
    """Mod-source routing matrix (catalog #28, Chordsaus): ``sources`` ×
    ``n_targets`` grid of toggle cells — MPE dimensions (or any control
    streams) as routable mod sources per target.

    Persistence rides the CORPUS-PROVEN path: the ``matrixctrl`` itself is a
    Blob parameter (``parameter_type=3`` stores the whole grid with the
    set). Cell edits stream out ``cells_out`` as ``<col> <row> <val>`` for
    the engine's routing (e.g. a ``router``/``matrix~`` recompute); source
    captions render down the left edge.
    """
    from .parameters import ParameterSpec
    from .ui import matrixctrl as _mc

    p = id_prefix
    n_src = len(sources)
    if n_src < 1 or n_targets < 1:
        raise ValueError("mod_source_matrix: need >=1 sources and targets")
    if n_src * int(n_targets) > 64:
        raise ValueError("mod_source_matrix: grid larger than 64 cells")
    x, y, w, h = rect
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    cap_w = 34
    grid_rect = [x + cap_w, y, w - cap_w, h]
    row_h = h / float(n_src)
    for si, name in enumerate(sources):
        device.add_comment(f"{p}_cap{si}",
                           [x, y + int(si * row_h) + 2, cap_w - 2, 8],
                           str(name), textcolor=dim, fontsize=5.8)
    spec = ParameterSpec(name=param_name, shortname=param_name,
                         parameter_type=3, initial_enable=None)
    box = _mc(f"{p}_mc", grid_rect, rows=n_src, columns=int(n_targets),
              parameter_enable=1,
              saved_attribute_attributes=spec.to_saved_attributes())
    if accent:
        box["box"]["color"] = list(accent)
    device.add_box(box)
    return stage_result(
        {"matrix": f"{p}_mc", "captions": [f"{p}_cap{i}"
                                           for i in range(n_src)]},
        name="mod_source_matrix",
        params={param_name: device.parameter(device.box(f"{p}_mc"))},
        ports={"cells_out": device.box(f"{p}_mc").outlet(0),
               "cells_in": device.box(f"{p}_mc").inlet(0)},
    )


_CHIP_KINDS = {
    "unit_hz_note": ("Hz", "♪", ["Hz", "Note"],
                     "Rate unit — free Hz or tempo-synced note divisions."),
    "log_lin": ("LIN", "LOG", ["Lin", "Log"],
                "Scale mode for the paired control's response curve."),
    "x10": ("×1", "×10", ["x1", "x10"],
            "Range multiplier — scales the paired knob's range by 10."),
    "retrig": ("R", "R", ["Free", "Retrig"],
               "Retrigger — restart the generator's phase on each trigger."),
    "hold": ("HOLD", "HOLD", ["Off", "Hold"],
             "Hold — freeze the current output value while lit."),
    "auto": ("A", "A", ["Manual", "Auto"],
             "Auto — the paired control follows the signal; moving it "
             "manually takes over."),
}


def standard_chip(device, id_prefix, kind, rect, *, param_name=None,
                  accent=None, dim_color=None, fontsize=6.5):
    """The dnksaus micro-chip vocabulary as one factory (catalog #31 #32
    #33 #37): tiny 2-state ``live.text`` chips with STANDARD semantics —
    ``unit_hz_note`` (f/Hz vs ♪ unit mode), ``log_lin``, ``x10`` (range
    multiplier — its ``factor_out`` port emits 1 or 10 for the engine),
    ``retrig`` (R), ``hold``, ``auto`` (A). One spelling fleet-wide instead
    of per-device one-offs; annotations ship the Info-View text.
    """
    from .parameters import ParameterSpec
    from .ui import live_text

    if kind not in _CHIP_KINDS:
        raise ValueError(
            f"standard_chip: unknown kind {kind!r} — one of "
            f"{sorted(_CHIP_KINDS)}")
    off, on, enum, annotation = _CHIP_KINDS[kind]
    p = id_prefix
    name = param_name or f"{p} {kind}"
    acc = list(accent) if accent else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    device.add_box(live_text(
        f"{p}_chip", name, list(rect), text_on=on, text_off=off, mode=1,
        fontsize=fontsize, bgoncolor=acc, textcolor=dim,
        annotation=annotation,
        parameter=ParameterSpec(name=name, shortname=name[:15],
                                parameter_type=2, enum=list(enum),
                                initial=[0], initial_enable=True)))
    ports = {"value_out": device.box(f"{p}_chip").outlet(0)}
    if kind == "x10":
        fac = device.add_newobj(f"{p}_fac", "expr int(pow(10\\, $i1))",
                                numinlets=1, numoutlets=1, outlettype=[""],
                                patching_rect=[700, 2200, 140, 20])
        device.add_line(f"{p}_chip", 0, fac, 0)
        ports["factor_out"] = device.box(fac).outlet(0)
    return stage_result(
        {"chip": f"{p}_chip"},
        name="standard_chip",
        params={name: device.parameter(device.box(f"{p}_chip"))},
        ports=ports,
    )


_PARAM_LINK_JS = """// param_link — linked/opposing dual-value pair (T09, catalog #34;
// generalizes gma-clp_keymod's paramGroups). Modes: mirror (linked values
// move by the SAME delta) / oppose (maximizer workflow: inverse delta).
// An `updating` guard kills setvalueof re-entry feedback.
autowatch = 1;
inlets = 1;
outlets = 0;

var VN_A = "" + jsarguments[1];
var VN_B = "" + jsarguments[2];
var MODE = ("" + jsarguments[3]) === "oppose" ? -1 : 1;

var linked = 0;
var vals = {};
var updating = false;

function link(v) { linked = v ? 1 : 0; }

function a(v) { _moved(VN_A, VN_B, v); }

function b(v) { _moved(VN_B, VN_A, v); }

function _moved(src, dst, v) {
    if (updating) { vals[src] = v; return; }
    var prev = (src in vals) ? vals[src] : v;
    vals[src] = v;
    if (!linked) return;
    var delta = (v - prev) * MODE;
    if (delta === 0) return;
    var box = this.patcher.getnamed(dst);
    if (!box) return;
    var cur = parseFloat(box.getvalueof());
    updating = true;
    try { box.setvalueof(cur + delta); vals[dst] = cur + delta; }
    catch (e) {}
    updating = false;
}
"""


def param_link(device, id_prefix, *, a, b, mode="mirror", link_rect,
               accent=None, dim_color=None, param_name=None):
    """Linked dual-value pair with a ⇄ chain chip (catalog #34, Inc Steps /
    Trig Mod) — and, with ``mode="oppose"``, the GMaudio-Clipper "maximizer
    workflow" (moving one param applies the INVERSE delta to its partner).

    ``a`` / ``b``: space-free VARNAMES of two existing param controls. While
    the chip is lit, moving either applies the (mirrored or opposed) delta
    to the other through ``setvalueof`` with a re-entry guard — Live sees
    ordinary edits on both.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec

    p = id_prefix
    for vn in (a, b):
        if " " in vn:
            raise ValueError(f"param_link: varname {vn!r} contains a space "
                             "(patcher.getnamed addressing)")
    if mode not in ("mirror", "oppose"):
        raise ValueError("param_link: mode must be 'mirror' or 'oppose'")
    acc = list(accent) if accent else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    name = param_name or f"{a}·{b} Link"
    glyph = "⇄" if mode == "mirror" else "⇅"
    device.add_live_text(
        f"{p}_chip", name, list(link_rect), text_on=glyph, text_off=glyph,
        mode=1, fontsize=8.0, bgoncolor=acc, textcolor=dim,
        annotation=("Link — both values move together." if mode == "mirror"
                    else "Opposing link — raising one lowers the other by "
                         "the same amount (maximizer workflow)."),
        parameter=ParameterSpec(name=name, shortname="Link",
                                parameter_type=2, enum=["Off", "On"],
                                initial=[0], initial_enable=True))
    fname = js_sidecar_name("param_link.js", _PARAM_LINK_JS)
    device.register_asset(fname, _PARAM_LINK_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname} {a} {b} {mode}", numinlets=1, numoutlets=0,
        patching_rect=[700, 2300, 220, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    for tag, vn in (("a", a), ("b", b)):
        pre = device.add_newobj(f"{p}_pre_{tag}", f"prepend {tag}",
                                numinlets=1, numoutlets=1, outlettype=[""],
                                patching_rect=[700, 2230 + (0 if tag == "a"
                                                            else 30), 90, 20])
        device.add_line(vn, 0, pre, 0)
        device.add_line(pre, 0, js, 0)
    prel = device.add_newobj(f"{p}_pre_l", "prepend link", numinlets=1,
                             numoutlets=1, outlettype=[""],
                             patching_rect=[700, 2200, 90, 20])
    device.add_line(f"{p}_chip", 0, prel, 0)
    device.add_line(prel, 0, js, 0)
    return stage_result(
        {"chip": f"{p}_chip", "js": f"{p}_js"},
        name="param_link",
        params={name: device.parameter(device.box(f"{p}_chip"))},
        ports={},
    )


def dim_steppers(device, id_prefix, *, dims, at, cell_w=34, gap=4,
                 accent="0.30, 0.80, 0.84"):
    """Compact multi-dimension stepper cluster (catalog #38, Liquid Mask
    "X 3 Y 1 Z 1 W 1"): one :meth:`add_custom_stepper` per dim in a row.
    ``dims``: list of ``(letter, vmin, vmax, initial)``.
    """
    p = id_prefix
    x, y = at
    made = []
    params = {}
    for i, (letter, vmin, vmax, init) in enumerate(dims):
        sid = f"{p}_{letter.lower()}"
        device.add_custom_stepper(
            sid, str(letter), [x + i * (cell_w + gap), y, cell_w, 15],
            vmin=float(vmin), vmax=float(vmax), initial=float(init),
            step=1.0, decimals=0, label=str(letter), accent=accent)
        made.append(sid)
        params[str(letter)] = device.parameter(str(letter))
    return stage_result({"steppers": made}, name="dim_steppers",
                        params=params, ports={})


def ghost_label(device, id_prefix, *, rect, text, accent, dim_color=None,
                fontsize=9.0):
    """Ghosted state label (catalog #39, Live Stretch "Reverse Stretch"):
    the label sits dimmed until the mode ENGAGES, then lights in accent —
    state-as-typography. Corpus mechanism (Prob v1.1 Thru/Blocked): TWO
    same-rect comments swapped via parent-side ``script sendbox <id>
    hidden`` (the Live-proven bus). Wire an int 0/1 into ``state_in``.
    """
    p = id_prefix
    dim = list(dim_color) if dim_color else [0.42, 0.44, 0.47, 1.0]
    device.add_comment(f"{p}_off", list(rect), text, textcolor=dim,
                       fontsize=fontsize)
    device.boxes[-1]["box"]["varname"] = f"{p}_off"
    device.add_comment(f"{p}_on", list(rect), text, textcolor=list(accent),
                       fontsize=fontsize)
    device.boxes[-1]["box"]["varname"] = f"{p}_on"
    device.boxes[-1]["box"]["hidden"] = 1
    tt = device.add_newobj(f"{p}_t", "t i i", numinlets=1, numoutlets=2,
                           outlettype=["int", "int"],
                           patching_rect=[700, 2400, 40, 20])
    inv = device.add_newobj(f"{p}_inv", "!- 1", numinlets=2, numoutlets=1,
                            outlettype=["int"],
                            patching_rect=[760, 2430, 40, 20])
    device.add_box({"box": {
        "id": f"{p}_m_on", "maxclass": "message",
        "text": f"script sendbox {p}_on hidden $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [700, 2460, 190, 20]}})
    device.add_box({"box": {
        "id": f"{p}_m_off", "maxclass": "message",
        "text": f"script sendbox {p}_off hidden $1",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [700, 2490, 190, 20]}})
    thisp = device.add_newobj(f"{p}_this", "thispatcher", numinlets=1,
                              numoutlets=2, outlettype=["", ""],
                              patching_rect=[700, 2520, 80, 20])
    device.add_line(tt, 1, inv, 0)          # right first: on-label hidden=!s
    device.add_line(inv, 0, f"{p}_m_on", 0)
    device.add_line(tt, 0, f"{p}_m_off", 0)  # off-label hidden=s
    device.add_line(f"{p}_m_on", 0, thisp, 0)
    device.add_line(f"{p}_m_off", 0, thisp, 0)
    return stage_result(
        {"on": f"{p}_on", "off": f"{p}_off"},
        name="ghost_label",
        params={},
        ports={"state_in": device.box(tt).inlet(0)},
    )


def mode_pill(device, id_prefix, *, rect, modes, param_name="Mode",
              accent="0.30, 0.80, 0.84", dim_color=None):
    """Mode pill whose icon IS the behavior (catalog #36, Clix "◠ Pump
    Mode"): a glyph selector where each mode's icon is a transfer-curve /
    response glyph from the shared bank (``lowpass`` ``bell`` ``fold`` …),
    with the current mode's LABEL rendered beside it. ``modes``: list of
    ``(label, glyph_name)``.

    Composition: :meth:`Device.add_mode_glyph_selector` (glyph row bound to
    a hidden automatable tab) + a label textedit that follows the selection
    (fed ready-made ``set <label>`` messages).
    """
    p = id_prefix
    x, y, w, h = rect
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    glyph_w = min(len(modes) * (h + 2), w - 34)
    sel_id = device.add_mode_glyph_selector(
        f"{p}_sel", param_name, [x, y, glyph_w, h],
        glyphs=[g for (_l, g) in modes],
        option_labels=[lbl for (lbl, _g) in modes],
        accent=accent)
    from .ui import textedit
    device.add_box(textedit(
        f"{p}_lbl", [x + glyph_w + 4, y + 2, w - glyph_w - 4, h - 2],
        text=str(modes[0][0]), fontsize=7.5, textcolor=dim,
        bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    for mi, (label, _g) in enumerate(modes):
        sel = device.add_newobj(f"{p}_s{mi}", f"select {mi}", numinlets=2,
                                numoutlets=2, outlettype=["bang", ""],
                                patching_rect=[700, 2560 + mi * 30, 60, 20])
        device.add_box({"box": {
            "id": f"{p}_m{mi}", "maxclass": "message", "text": f"set {label}",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [780, 2560 + mi * 30, 100, 20]}})
        device.add_line(sel_id, 0, sel, 0)
        device.add_line(sel, 0, f"{p}_m{mi}", 0)
        device.add_line(f"{p}_m{mi}", 0, f"{p}_lbl", 0)
    return stage_result(
        {"selector": sel_id, "label": f"{p}_lbl"},
        name="mode_pill",
        params={param_name: device.parameter(device.box(sel_id))
                if device.parameter(device.box(sel_id)) else None},
        ports={},
    )


def display_header(device, id_prefix, *, rect, title, accent,
                   gain=False, gain_name="Out Gain", mute_name="Mute",
                   text_color=None, dim_color=None):
    """Graph-header output strip (catalog #35, Trig Mod): a MUTE pill and an
    inline gain-dB LCD fused into a display's ~15px title row. Ports:
    ``mute_out`` (0/1) and ``gain_out`` (dB float) for the engine's output
    stage. All in one strip so the graph keeps every vertical pixel.
    """
    from .parameters import ParameterSpec
    from .ui import live_text, number_box, textedit

    p = id_prefix
    x, y, w, h = rect
    tx = list(text_color) if text_color else [0.85, 0.87, 0.89, 1.0]
    dim = list(dim_color) if dim_color else [0.55, 0.58, 0.61, 1.0]
    acc = list(accent)
    device.add_box(live_text(
        f"{p}_mute", mute_name, [x, y + 1, 26, h - 2], text_on="M",
        text_off="M", mode=1, fontsize=7.0, bgoncolor=acc, textcolor=dim,
        annotation="Mute this display's output.",
        parameter=ParameterSpec(name=mute_name, shortname="Mute",
                                parameter_type=2, enum=["Off", "Mute"],
                                initial=[0], initial_enable=True)))
    gain_w = 46 if gain else 0
    device.add_box(textedit(
        f"{p}_title", [x + 30, y + 2, w - 34 - gain_w, h - 4],
        text=str(title), fontsize=7.5, textcolor=tx,
        bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=0, ignoreclick=1))
    ports = {"mute_out": device.box(f"{p}_mute").outlet(0)}
    if gain:
        device.add_box(number_box(
            f"{p}_gain", gain_name, [x + w - gain_w, y + 1, gain_w, h - 2],
            min_val=-24.0, max_val=12.0, initial=0.0, lcdcolor=acc,
            parameter=ParameterSpec(name=gain_name, shortname="Gain",
                                    minimum=-24.0, maximum=12.0,
                                    initial=0.0, initial_enable=True,
                                    units="%.1f dB", unitstyle=9)))
        ports["gain_out"] = device.box(f"{p}_gain").outlet(0)
    return stage_result(
        {"mute": f"{p}_mute", "title": f"{p}_title"},
        name="display_header",
        params={mute_name: device.parameter(device.box(f"{p}_mute"))},
        ports=ports,
    )


def hero_readout(device, id_prefix, *, rect, accent, fontsize=34.0,
                 initial="—"):
    """Giant hero READOUT (catalog #41, Bass Lock "G0"): the value IS the
    hero — 34px+ display type on a transparent field. Feed ready-made
    ``set <text…>`` messages into ``text_in`` (corpus alternative for pure
    numerics: a giant ``appearance=4`` live.numbox, Prob v1.1).
    """
    from .ui import textedit

    p = id_prefix
    device.add_box(textedit(
        f"{p}_txt", list(rect), text=str(initial), fontsize=float(fontsize),
        textcolor=list(accent), bgcolor=[0.0, 0.0, 0.0, 0.0], border=0,
        rounded=0, textjustification=1, ignoreclick=1))
    return stage_result(
        {"text": f"{p}_txt"},
        name="hero_readout",
        params={},
        ports={"text_in": device.box(f"{p}_txt").inlet(0)},
    )


_NOTE_HZ_JS = """// note_hz — Hz -> "C#0 · 34.6 Hz" dual readout feed (T10, catalog #42)
autowatch = 1;
inlets = 1;
outlets = 2;   // 0: "set <note> · <hz> Hz" (dual)   1: "set <note>" (hero)

var NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function msg_float(hz) {
    if (hz <= 0) return;
    var midi = 69.0 + 12.0 * Math.log(hz / 440.0) / Math.LN2;
    var n = Math.round(midi);
    var name = NAMES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 2);
    var hztxt = (hz >= 100 ? hz.toFixed(0) : hz.toFixed(1));
    outlet(1, ["set", name]);
    outlet(0, ["set", name, "\\u00b7", hztxt, "Hz"]);
}

function msg_int(v) { msg_float(v); }
"""


def note_hz_readout(device, id_prefix, *, rect, accent, text_color=None,
                    fontsize=8.0):
    """Live note+Hz dual readout (catalog #42, dnkFM "C#0 34.6 Hz"): feed a
    frequency into ``hz_in`` and the strip shows note-name · Hz; the
    ``hero_feed`` outlet carries a ready ``set <note>`` for a paired
    :func:`hero_readout`.
    """
    from .engines.design_system import js_sidecar_name
    from .ui import textedit

    p = id_prefix
    tx = list(text_color) if text_color else list(accent)
    fname = js_sidecar_name("note_hz.js", _NOTE_HZ_JS)
    device.register_asset(fname, _NOTE_HZ_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[700, 2700, 120, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    device.add_box(textedit(
        f"{p}_txt", list(rect), text="—", fontsize=float(fontsize),
        textcolor=tx, bgcolor=[0.0, 0.0, 0.0, 0.0], border=0, rounded=0,
        textjustification=1, ignoreclick=1))
    device.add_line(js, 0, f"{p}_txt", 0)
    return stage_result(
        {"text": f"{p}_txt", "js": f"{p}_js"},
        name="note_hz_readout",
        params={},
        ports={"hz_in": device.box(js).inlet(0),
               "hero_feed": device.box(js).outlet(1)},
    )


_PROGRESS_TICK_JS = """// progress_tick — phase dash under a display (T10, catalog #43, WaveLFO)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
inlets = 1;
outlets = 0;

var phase = 0.0;
var COL = [ACCENT];
var BGC = [0.05, 0.06, 0.09, 1.0];

function msg_float(v) {
    phase = Math.max(0, Math.min(1, v));
    mgraphics.redraw();
}

function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1];
    mgraphics.set_source_rgba(BGC);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();
    mgraphics.set_source_rgba(COL);
    var x = phase * (w - 6);
    mgraphics.rectangle(x, 0, 6, h);
    mgraphics.fill();
}
"""


def progress_tick(device, id_prefix, *, rect, accent):
    """LFO-phase progress tick (catalog #43, WaveLFO): a tiny dash sweeping
    a 3-4px strip under a display. Feed phase 0..1 floats into ``phase_in``
    at UI rate (e.g. ``phasor~ → snapshot~ 50``).
    """
    from .engines.design_system import js_sidecar_name

    p = id_prefix
    acc = ", ".join(f"{float(c):.4g}" for c in list(accent)[:4])
    code = _PROGRESS_TICK_JS.replace("ACCENT", acc)
    fname = js_sidecar_name("progress_tick.js", code)
    device.register_asset(fname, code, asset_type="TEXT", category="js")
    device.add_box({"box": {
        "id": f"{p}_ui", "maxclass": "jsui", "filename": fname,
        "jsui_maxclass": "jsui",
        "numinlets": 1, "numoutlets": 1, "outlettype": [""],
        "parameter_enable": 0, "border": 0,
        "presentation": 1, "presentation_rect": list(rect),
        "patching_rect": [700, 2760, rect[2], rect[3]]}})
    return stage_result(
        {"tick": f"{p}_ui"},
        name="progress_tick",
        params={},
        ports={"phase_in": device.box(f"{p}_ui").inlet(0)},
    )


_API_ROUTING_JS = """\
/* apirouting.js - Live IO routing chooser driver (Rainbow apiRouting.js
   pattern, Live-proven in Pocket Delay).
   Args: 1 = audio_inputs|audio_outputs, 2 = io index (0 = plugin~ 1 2,
   1 = plugin~ 3 4, ...). Outlet 0 -> type menu, outlet 1 -> channel menu. */
this.autowatch = 1;
this.outlets = 2;
var initInpName = this.jsarguments[1] || "audio_inputs";
var initInpIndex = this.jsarguments[2] || 0;
var noCallback = false, apiInit = false, initNoCB = false;
var ioName, ioIndex, idIndex, device, tas, ioObj;

function anything() {
    if (noCallback) return;
    var params = arrayfromargs(arguments).slice();
    if (messagename === "setTrack") { routing.setTrack(params[0]); return; }
    if (messagename === "setChannel") { routing.setChannel(params[0]); return; }
    if (messagename === "resetRouting") { routing.resetRouting(); return; }
}

var initTask = null, initTries = 0;

function initialize(inpName, inpIndex) {
    ioName = inpName || initInpName;
    ioIndex = (inpIndex !== undefined && inpIndex !== null) ? inpIndex : initInpIndex;
    idIndex = (+ioIndex) * 2 + 1;
    initTries = 0;
    attemptInit();
}

function attemptInit() {
    /* LiveAPI is NOT ready at the instant live.thisdevice bangs on an
       API-driven insert (the documented hot-load trap) - guard + Task
       retry until the device resolves. */
    initNoCB = true;
    device = new LiveAPI(deviceChanged, "live_set this_device");
    if (!device || +device.id === 0
            || device.children.indexOf(ioName) === -1) {
        initTries += 1;
        if (initTries < 12) {
            if (!initTask) initTask = new Task(attemptInit);
            initTask.schedule(250);
        }
        return;
    }
    initNoCB = false;
    /* Seed synchronously: the property-observer initial fire proved
       unreliable for midi_inputs on hot-loaded devices (T13b) while a
       direct get() returns the port ids immediately. The observer stays
       armed for hot routing changes. */
    var ids = device.get(ioName);
    if (ids && ids.length > idIndex && ids[idIndex]) {
        ioObj = new LiveAPI(execDefered, "id " + ids[idIndex]);
        ioObj.property = "routing_type";
        apiInit = true;
        execDefered();
    }
    device.property = ioName;
}

function deviceChanged(arg1) {
    if (initNoCB) return;
    var ioIdsList = arg1.slice(1);
    if (idIndex < 0 || ioIdsList.length <= idIndex) return;
    ioObj = new LiveAPI(execDefered, "id " + ioIdsList[idIndex]);
    ioObj.property = "routing_type";
    apiInit = true;
    execDefered();
}

function execDefered() {
    if (!apiInit) return;
    if (ioObj.id == 0) return;
    if (!tas) tas = new Task(routing.routingChanged, routing);
    tas.schedule();
}

var routing = {
    routingChanged: function () {
        this.updateLists();
        setMenu(0, this.getNames("available_routing_types"),
                this.getIndex("routing_type"));
        setMenu(1, this.getNames("available_routing_channels"),
                this.getIndex("routing_channel"));
    },
    getIndex: function (apiProperty) {
        return this.getNames("available_" + apiProperty + "s")
            .indexOf(this.getApiObj(apiProperty).display_name);
    },
    getNames: function (apiProperty) {
        var tmp = [];
        for (var i in this[apiProperty])
            tmp.push(this[apiProperty][i].display_name || " ");
        return tmp;
    },
    updateLists: function () {
        var propNames = ["available_routing_types", "available_routing_channels"];
        for (var i in propNames)
            this[propNames[i]] = this.getApiObj(propNames[i]);
    },
    getApiObj: function (apiProperty) {
        return JSON.parse(ioObj.get(apiProperty))[apiProperty]
            || { display_name: "" };
    },
    setApiRouting: function (apiProperty, index) {
        ioObj.set(apiProperty,
                  { identifier: this["available_" + apiProperty + "s"][index].identifier });
    },
    resetRouting: function () {
        this.setTrack(this.getNames("available_routing_types").length - 1);
    },
    setTrack: function (index) { if (!apiInit) return; this.setApiRouting("routing_type", index); },
    setChannel: function (index) { if (!apiInit) return; this.setApiRouting("routing_channel", index); }
};

function setMenu(port, list, value) {
    var output = list.slice();
    while (output.length < 2) output.push(" ");
    noCallback = true;
    outlet(port, "_parameter_range", output);
    noCallback = false;
    outlet(port, "ignoreclick", list.length < 2 ? 1 : 0);
    if (value || value === 0) outlet(port, "set", value);
}
setMenu.local = 1;
"""


def io_routing_menus(device, id_prefix, *, io="midi_inputs", io_index=0,
                     type_rect, chan_rect, type_name="Source",
                     chan_name="Channel", placeholder="No Input",
                     fontsize=8.0):
    """Live IO routing chooser (catalog #54, dnkFM "MIDI From"; the same
    Rainbow apiRouting driver Live-proven on Pocket Delay's audio REF):
    two menus (type + channel) enumerating the set's routable sources for
    this device's ``io`` (``midi_inputs`` / ``audio_inputs`` /
    ``…_outputs``), observing ``routing_type`` and setting the choice back
    by identifier. Menus fill at load via ``live.thisdevice`` — the LiveAPI
    is NOT ready at loadbang (Live-verified gotcha).

    The menus are ``parameter_invisible=2`` (saved, out of automation).
    Consume the routed stream with a plain ``midiin``/``plugin~`` as usual.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec
    from .ui import menu as _menu

    p = id_prefix
    fname = js_sidecar_name("apirouting.js", _API_ROUTING_JS)
    device.register_asset(fname, _API_ROUTING_JS, asset_type="TEXT",
                          category="js")
    for mid, mname, rect, opts in (
            (f"{p}_menu_type", type_name, type_rect, [placeholder, "\u2014"]),
            (f"{p}_menu_chan", chan_name, chan_rect, ["\u2014", "\u2014 "])):
        device.add_box(_menu(
            mid, mname, list(rect), options=opts, fontsize=fontsize,
            annotation=f"Routing {mname.lower()} for this device's "
                       f"{io.replace('_', ' ')}.",
            parameter=ParameterSpec(name=mname, shortname=mname[:15],
                                    parameter_type=2, enum=list(opts),
                                    initial=[0], initial_enable=True,
                                    invisible=2)))
    js = device.add_newobj(
        f"{p}_api", f"js {fname} {io} {int(io_index)}",
        numinlets=1, numoutlets=2, outlettype=["", ""],
        patching_rect=[900, 2800, 200, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    device.add_box({"box": {
        "id": f"{p}_init", "maxclass": "message", "text": "initialize",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [900, 2770, 70, 20]}})
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 2740, 90, 20])
    st = device.add_newobj(f"{p}_set_t", "prepend setTrack", numinlets=1,
                           numoutlets=1, outlettype=[""],
                           patching_rect=[900, 2840, 110, 20])
    sc = device.add_newobj(f"{p}_set_c", "prepend setChannel", numinlets=1,
                           numoutlets=1, outlettype=[""],
                           patching_rect=[1020, 2840, 130, 20])
    device.add_line(td, 0, f"{p}_init", 0)
    device.add_line(f"{p}_init", 0, js, 0)
    device.add_line(js, 0, f"{p}_menu_type", 0)
    device.add_line(js, 1, f"{p}_menu_chan", 0)
    device.add_line(f"{p}_menu_type", 0, st, 0)
    device.add_line(f"{p}_menu_chan", 0, sc, 0)
    device.add_line(st, 0, js, 0)
    device.add_line(sc, 0, js, 0)
    return stage_result(
        {"api": f"{p}_api", "type_menu": f"{p}_menu_type",
         "chan_menu": f"{p}_menu_chan"},
        name="io_routing_menus",
        params={},
        ports={"api_in": device.box(js).inlet(0)},
    )


def midi_from(device, id_prefix, *, type_rect, chan_rect, io_index=0,
              with_midiin=True, **kwargs):
    """"MIDI From" chooser (catalog #54, dnkFM): :func:`io_routing_menus`
    over ``midi_inputs`` plus (by default) the ``midiin`` consumer whose
    source the chooser selects — its raw byte stream leaves on
    ``midi_raw_out``.
    """
    res = io_routing_menus(device, id_prefix, io="midi_inputs",
                           io_index=io_index, type_rect=type_rect,
                           chan_rect=chan_rect, **kwargs)
    if with_midiin:
        p = id_prefix
        mi = device.add_newobj(f"{p}_midiin", "midiin", numinlets=1,
                               numoutlets=1, outlettype=["int"],
                               patching_rect=[900, 2900, 50, 20])
        res.ports["midi_raw_out"] = device.box(mi).outlet(0)
        res["midiin"] = f"{p}_midiin"
    return res


_SCALE_AWARE_JS = """/* scale_aware.js - Live 12 set scale observer + note folder (T14, #53).
   Observes live_set root_note / scale_name / scale_intervals; outlet 0
   feeds the scale chip ("set F Minor"), outlet 1 emits `root <n>` +
   `intervals <list>` for engines, and `note <n>` messages fold to the
   nearest in-scale pitch and leave outlet 2. */
this.autowatch = 1;
this.outlets = 3;

var NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
var apiRoot = null, apiName = null, apiIvals = null;
var root = 0, scaleName = "Major", ivals = [0, 2, 4, 5, 7, 9, 11];
var retryTask = null;

function initialize() {
    apiRoot = new LiveAPI(onchange, "live_set");
    apiRoot.property = "root_note";
    apiName = new LiveAPI(onchange, "live_set");
    apiName.property = "scale_name";
    apiIvals = new LiveAPI(onchange, "live_set");
    apiIvals.property = "scale_intervals";
    refresh();
    // hot-load window: live_set get() can be unresolved at thisdevice time
    retryTask = new Task(refresh);
    retryTask.schedule(250);
}

function onchange() { refresh(); }

function refresh() {
    if (!apiRoot) return;
    var r, nm, iv;
    try {
        r = apiRoot.get("root_note");
        nm = apiName.get("scale_name");
        iv = apiIvals.get("scale_intervals");
    } catch (e) { return; }
    if (nm === null || nm === undefined) return;
    root = parseInt(r, 10) || 0;
    scaleName = ("" + nm).replace(/^"|"$/g, "");
    if (!scaleName) return;
    if (iv && iv.length) ivals = iv;
    outlet(1, ["intervals"].concat(ivals));
    outlet(1, ["root", root]);
    outlet(0, ["set", NAMES[root % 12], scaleName]);
}

function note(n) {
    var pc = ((n - root) % 12 + 12) % 12;
    var best = ivals[0], dist = 99;
    for (var i = 0; i < ivals.length; i++) {
        var d = Math.abs(ivals[i] - pc);
        if (d < dist) { dist = d; best = ivals[i]; }
    }
    outlet(2, n - pc + best);
}

function msg_int(n) { note(n); }
function msg_float(n) { note(Math.round(n)); }
"""


def scale_awareness(device, id_prefix, *, chip_rect, fontsize=8.0):
    """Live 12 scale awareness (catalog #53, Bass Lock / Chordsaus): observe
    the SET's root+scale, render a scale chip styled with Live's dedicated
    ``live_scale_awareness`` theme color, and fold notes to the scale.

    Ports: ``note_in`` (MIDI note int → folded note on ``folded_out``) and
    ``scale_out`` (``root <n>`` / ``intervals <list>`` for engines). Uses
    the Live 12 ``scale_intervals`` LOM property — no interval tables.
    """
    from .engines.design_system import js_sidecar_name

    p = id_prefix
    fname = js_sidecar_name("scale_aware.js", _SCALE_AWARE_JS)
    device.register_asset(fname, _SCALE_AWARE_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=3,
        outlettype=["", "", ""], patching_rect=[900, 3100, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    chip = {"box": {
        "id": f"{p}_chip", "maxclass": "textedit", "text": "—",
        "numinlets": 1, "numoutlets": 4,
        "outlettype": ["", "int", "", ""],
        "fontsize": float(fontsize), "fontname": "Ableton Sans Medium",
        "textcolor": [0.745, 0.596, 1.0, 1.0],
        "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0, "rounded": 0,
        "textjustification": 1, "ignoreclick": 1,
        "presentation": 1, "presentation_rect": list(chip_rect),
        "patching_rect": [900, 3140, chip_rect[2], chip_rect[3]],
        "saved_attribute_attributes": {
            "textcolor": {"expression": "themecolor.live_scale_awareness"}}}}
    device.add_box(chip)
    device.add_box({"box": {
        "id": f"{p}_init", "maxclass": "message", "text": "initialize",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [900, 3070, 70, 20]}})
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 3040, 90, 20])
    device.add_line(td, 0, f"{p}_init", 0)
    device.add_line(f"{p}_init", 0, js, 0)
    device.add_line(js, 0, f"{p}_chip", 0)
    return stage_result(
        {"js": f"{p}_js", "chip": f"{p}_chip"},
        name="scale_awareness",
        params={},
        ports={"note_in": device.box(js).inlet(0),
               "scale_out": device.box(js).outlet(1),
               "folded_out": device.box(js).outlet(2)},
    )


_RECORD_MIDI_JS = """/* record_midi.js - capture device MIDI into a session clip (T14, #55).
   `rec 1` starts collecting `ev <pitch> <velocity> <beats>` events
   (beats = transport beat time from plugsync~); `rec 0` writes them into
   this track's FIRST EMPTY session clip slot via the LOM. */
this.autowatch = 1;
this.outlets = 1;

var events = [];
var recording = false;
var startBeat = -1;

function rec(v) {
    if (v) { events = []; startBeat = -1; recording = true; return; }
    recording = false;
    writeClip();
}

function ev(pitch, velocity, beats) {
    if (!recording) return;
    if (startBeat < 0) startBeat = beats;
    events.push([pitch, beats - startBeat, velocity]);
}

function writeClip() {
    if (!events.length) { outlet(0, ["status", "empty"]); return; }
    var track = new LiveAPI(null, "live_set this_device canonical_parent");
    var nslots = parseInt(track.getcount("clip_slots"), 10);
    var slotIdx = -1;
    for (var i = 0; i < nslots; i++) {
        var slot = new LiveAPI(null,
            "live_set this_device canonical_parent clip_slots " + i);
        if (parseInt(slot.get("has_clip"), 10) === 0) { slotIdx = i; break; }
    }
    if (slotIdx < 0) { outlet(0, ["status", "no empty slot"]); return; }
    var last = events[events.length - 1][1] + 1.0;
    var len = Math.max(4.0, Math.ceil(last));
    var slotApi = new LiveAPI(null,
        "live_set this_device canonical_parent clip_slots " + slotIdx);
    slotApi.call("create_clip", len);
    var clip = new LiveAPI(null,
        "live_set this_device canonical_parent clip_slots " + slotIdx
        + " clip");
    var notes = [];
    for (var e = 0; e < events.length; e++) {
        notes.push({pitch: events[e][0], start_time: events[e][1],
                    duration: 0.25, velocity: events[e][2], mute: 0});
    }
    clip.call("add_new_notes", {notes: notes});
    clip.set("name", "Captured MIDI");
    outlet(0, ["status", "wrote", events.length, "notes to slot", slotIdx]);
}
"""


def record_midi(device, id_prefix, *, rect, accent=None):
    """Record-MIDI capture (catalog #55, Chordsaus): a red REC pill that
    collects the device's generated MIDI while lit and, on release, writes
    the take into this track's first empty session clip via the LOM
    (``create_clip`` + ``add_new_notes``) — the capture IS a real Live clip
    the user can drag anywhere.

    Feed note events into ``ev_in`` as ``ev <pitch> <velocity> <beats>``
    (beat time from ``plugsync~`` outlet 4's beat count or a ``timepoint``
    chain). ``status_out`` reports writes.
    """
    from .engines.design_system import js_sidecar_name
    from .parameters import ParameterSpec
    from .ui import live_text

    p = id_prefix
    acc = list(accent) if accent else [0.90, 0.25, 0.25, 1.0]
    device.add_box(live_text(
        f"{p}_pill", "Record MIDI", list(rect), text_on="● REC",
        text_off="● REC", mode=1, fontsize=7.5, bgoncolor=acc,
        textcolor=[0.62, 0.62, 0.65, 1.0],
        annotation="Capture the device's generated MIDI; releasing writes "
                   "a clip into this track's first empty session slot.",
        parameter=ParameterSpec(name="Record MIDI", shortname="Rec MIDI",
                                parameter_type=2, enum=["Off", "Rec"],
                                initial=[0], initial_enable=True,
                                invisible=1)))
    fname = js_sidecar_name("record_midi.js", _RECORD_MIDI_JS)
    device.register_asset(fname, _RECORD_MIDI_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[900, 3220, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    pre = device.add_newobj(f"{p}_prer", "prepend rec", numinlets=1,
                            numoutlets=1, outlettype=[""],
                            patching_rect=[900, 3190, 90, 20])
    device.add_line(f"{p}_pill", 0, pre, 0)
    device.add_line(pre, 0, js, 0)
    return stage_result(
        {"pill": f"{p}_pill", "js": f"{p}_js"},
        name="record_midi",
        params={"Record MIDI": device.parameter(
            device.box(f"{p}_pill"))},
        ports={"ev_in": device.box(js).inlet(0),
               "status_out": device.box(js).outlet(0)},
    )


_DEVICE_PALETTE_JS = """/* device_palette.js - Spawner-class native-device inserter (T15, #51).
   `spawn <Name...>` inserts a NATIVE Live device on the selected track via
   the Live 12 LOM Track.insert_device(name, index?). `policyidx 0|1|2`
   places it Left of / Right of the selected device / Last in chain.
   `dupes 0|1` gates re-inserting a class already on the track,
   `spawnrandom` picks from the `addname`-registered list (no immediate
   repeat), `removedevice` deletes the selected device. Outlet 0 feeds a
   status chip. */
this.autowatch = 1;
this.outlets = 1;

var names = [];
var policy = 2;        // 0=Left 1=Right 2=Last
var dupes = 1;         // 1 = allow duplicates
var lastPick = -1;

function addname() {
    names.push(Array.prototype.slice.call(arguments).join(" "));
}

function clearnames() { names = []; }

function policyidx(v) { policy = Math.max(0, Math.min(2, v | 0)); }

function dupesflag(v) { dupes = v ? 1 : 0; }

/* hunt #13 (rack-aware): the selected device's path inside an Audio Effect
   Rack ends in a CHAIN-relative segment (... devices N chains K devices M).
   The old bare-index regex returned M and drove delete_device/insert_device
   on the TOP-LEVEL track, so Remove deleted a DIFFERENT device (data loss)
   and Left/Right mis-placed. selectedDeviceRef() returns the device's REAL
   container path + index; Remove deletes from that container, Left/Right
   insert into it (chain inserts fall back to end-of-track with an honest
   status if the LOM refuses). */
function selectedDeviceRef() {
    var dev = new LiveAPI(null, "live_set view selected_track view selected_device");
    if (!dev || dev.id == 0) return null;
    var path = ("" + dev.path).replace(/"/g, "");
    var m = path.match(/^(.*) devices (\\d+)$/);
    if (!m) return null;
    return { container: m[1], index: parseInt(m[2], 10),
             nested: / chains \\d+$/.test(m[1]) };
}

function classOnContainer(apiPath, name) {
    var c = new LiveAPI(null, apiPath);
    if (!c || c.id == 0) return false;
    var n = parseInt(c.getcount("devices"), 10) || 0;
    for (var i = 0; i < n; i++) {
        var d = new LiveAPI(null, apiPath + " devices " + i);
        var cls = ("" + d.get("class_display_name")).replace(/"/g, "");
        if (cls === name) return true;
        /* rack devices: walk every chain so DUP sees nested copies too */
        var cn = parseInt(d.getcount("chains"), 10) || 0;
        for (var k = 0; k < cn; k++) {
            if (classOnContainer(apiPath + " devices " + i + " chains " + k,
                                 name)) return true;
        }
    }
    return false;
}

function onTrack(track, name) {
    return classOnContainer("live_set view selected_track", name);
}

function doSpawn(name) {
    var track = new LiveAPI(null, "live_set view selected_track");
    if (!track || track.id == 0) { status("no track"); return; }
    if (!dupes && onTrack(track, name)) { status(name + " already here"); return; }
    var ref = (policy !== 2) ? selectedDeviceRef() : null;
    if (ref && ref.index >= 0) {
        var idx = ref.index + (policy === 1 ? 1 : 0);
        if (ref.nested) {
            /* chain-relative insert next to the nested selection */
            try {
                var chain = new LiveAPI(null, ref.container);
                chain.call("insert_device", name, idx);
                status("+ " + name);
                return;
            } catch (e) { /* chain refused - fall through to track-last */ }
            try { track.call("insert_device", name); }
            catch (e2) { status("failed: " + name); return; }
            status("+ " + name + " (rack: placed last)");
            return;
        }
        try { track.call("insert_device", name, idx); }
        catch (e3) { status("failed: " + name); return; }
        status("+ " + name);
        return;
    }
    try { track.call("insert_device", name); }
    catch (e4) { status("failed: " + name); return; }
    status("+ " + name);
}

function spawn() {
    doSpawn(Array.prototype.slice.call(arguments).join(" "));
}

function spawnrandom() {
    if (!names.length) { status("no palette"); return; }
    var i = Math.floor(Math.random() * names.length);
    if (names.length > 1 && i === lastPick) i = (i + 1) % names.length;
    lastPick = i;
    doSpawn(names[i]);
}

function removedevice() {
    var ref = selectedDeviceRef();
    if (!ref || ref.index < 0) { status("none selected"); return; }
    /* delete from the device's REAL container (track OR rack chain) - the
       old top-level delete_device with a chain-relative index destroyed a
       different device entirely */
    var container = new LiveAPI(null, ref.container);
    try { container.call("delete_device", ref.index); status("removed"); }
    catch (e) { status("remove failed"); }
}

function status(s) { outlet(0, ["set"].concat(("" + s).split(" "))); }
"""


def device_palette(device, id_prefix, *, names, rect, columns=3,
                   policy_tab=None, status_rect=None, accent=None,
                   gap=2, fontsize=6.5):
    """Spawner-class native-device palette (catalog #51, Spawner v1.08).

    A grid of ``textbutton`` chips over ``rect`` — clicking one inserts that
    NATIVE Live device on the *selected* track via the Live 12 LOM
    ``Track.insert_device`` (Max for Live devices/plug-ins can't be inserted
    this way). Insertion position follows the policy (0 Left of the selected
    device / 1 Right of it / 2 Last), wired from ``policy_tab`` (a live.tab
    box id emitting 0..2) when given. Extra verbs on ``ctl_in``:
    ``spawnrandom`` (dice — no immediate repeat), ``removedevice`` (delete
    the selected device — corpus remove.maxpat), ``dupesflag 0|1`` (block
    re-inserting a class already on the track).

    The name list is registered into the js at load time (live.thisdevice →
    trigger → one ``addname`` message PER name), so ``spawnrandom`` knows the
    palette without re-parsing the UI.
    """
    from .engines.design_system import js_sidecar_name
    from .ui import textbutton

    p = id_prefix
    acc = list(accent) if accent else [1.0, 0.5, 0.24, 1.0]
    fname = js_sidecar_name("device_palette.js", _DEVICE_PALETTE_JS)
    device.register_asset(fname, _DEVICE_PALETTE_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[900, 3600, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})

    x0, y0, w, h = rect
    rows = -(-len(names) // columns)
    bw = (w - gap * (columns - 1)) / columns
    bh = (h - gap * (rows - 1)) / rows
    for i, name in enumerate(names):
        r, c = divmod(i, columns)
        brect = [x0 + c * (bw + gap), y0 + r * (bh + gap),
                 bw, bh]
        device.add_box(textbutton(
            f"{p}_b{i}", brect, name, mode=0, fontsize=fontsize,
            bgcolor=[0.16, 0.17, 0.20, 1.0], bgoncolor=acc,
            textcolor=[0.78, 0.79, 0.82, 1.0],
            annotation_name=name,
            annotation=f"Insert Live's native {name} on the selected track "
                       "(placement follows the position policy).",
            patching_rect=[900 + (i % 8) * 130, 3630 + (i // 8) * 60,
                           110, 20]))
        device.add_box({"box": {
            "id": f"{p}_m{i}", "maxclass": "message",
            "text": f"spawn {name}", "numinlets": 2, "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [900 + (i % 8) * 130, 3630 + (i // 8) * 60 + 26,
                              110, 20]}})
        device.add_line(f"{p}_b{i}", 0, f"{p}_m{i}", 0)
        device.add_line(f"{p}_m{i}", 0, js, 0)

    # register the palette into the js for spawnrandom. ONE message per name,
    # sequenced by a trigger — comma-chained message text does NOT survive an
    # authored-JSON load (the Orbit DRAW lesson: chrome batches go invisible /
    # escaped commas load as literal tokens), so the old single comma-joined
    # addname chain silently registered NOTHING.
    nt = device.add_newobj(f"{p}_nt", "t " + " ".join(["b"] * len(names)),
                           numinlets=1, numoutlets=len(names),
                           outlettype=["bang"] * len(names),
                           patching_rect=[900, 3570, 220, 20])
    for i, name in enumerate(names):
        device.add_box({"box": {
            "id": f"{p}_n{i}", "maxclass": "message",
            "text": f"addname {name}", "numinlets": 2, "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [900 + (i % 8) * 130,
                              3600 + (i // 8) * 60, 110, 20]}})
        device.add_line(nt, i, f"{p}_n{i}", 0)
        device.add_line(f"{p}_n{i}", 0, js, 0)
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 3540, 90, 20])
    device.add_line(td, 0, nt, 0)

    if policy_tab is not None:
        pol = device.add_newobj(f"{p}_pol", "prepend policyidx",
                                numinlets=1, numoutlets=1, outlettype=[""],
                                patching_rect=[1140, 3570, 110, 20])
        device.add_line(policy_tab, 0, pol, 0)
        device.add_line(pol, 0, js, 0)

    result_boxes = {"js": f"{p}_js"}
    if status_rect is not None:
        device.add_box({"box": {
            "id": f"{p}_status", "maxclass": "textedit", "text": "—",
            "numinlets": 1, "numoutlets": 4,
            "outlettype": ["", "int", "", ""], "fontsize": 6.5,
            "fontname": "Ableton Sans Medium",
            "textcolor": [0.55, 0.56, 0.60, 1.0],
            "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0,
            "ignoreclick": 1, "presentation": 1,
            "presentation_rect": list(status_rect),
            "patching_rect": [900, 3660, status_rect[2], status_rect[3]]}})
        device.add_line(js, 0, f"{p}_status", 0)
        result_boxes["status"] = f"{p}_status"

    return stage_result(
        result_boxes,
        name="device_palette",
        params={},
        ports={"ctl_in": device.box(js).inlet(0),
               "status_out": device.box(js).outlet(0)},
    )


_SAMPLE_EXPORT_JS = """/* sample_export.js - buffer~ -> wav on disk (T15, #56 out-half).
   `save` emits `writewave <dir>/<stem>_NNN.wav` for the wired buffer~
   (outlet 0) + a status line (outlet 1). `setdir <path...>` (re)targets
   the folder — args are re-joined so paths with spaces survive. True
   OS-level drag-out needs the 3rd-party 11olsen `11dragfiles` external
   (corpus: Random Sample Picker); the portable stock path is saving into
   the User Library so the file appears in Live's browser to drag from. */
this.autowatch = 1;
this.outlets = 2;

var dir = "";
var stem = "export";
var count = 0;

function setdir() {
    dir = Array.prototype.slice.call(arguments).join(" ");
}

function setstem(s) { stem = "" + s; }

function save() {
    if (!dir) { outlet(1, ["set", "no", "folder", "set"]); return; }
    count += 1;
    var n = ("00" + count).slice(-3);
    var path = dir + "/" + stem + "_" + n + ".wav";
    outlet(0, ["writewave", path]);
    outlet(1, ["set", "saved", stem + "_" + n + ".wav"]);
}
"""


def sample_export(device, id_prefix, buffer_box_id, *, rect,
                  default_dir=None, stem="export", status_rect=None,
                  accent=None):
    """Save the contents of an existing ``buffer~`` to a ``.wav`` on disk
    (catalog #56, out-half). One SAVE click = one numbered file
    (``<stem>_001.wav`` …) written via ``buffer~``'s stock ``writewave``.

    The dnksaus corpus does true OS drag-out with the 3rd-party 11olsen
    ``11dragfiles`` external (Random Sample Picker v2.0: path → ``prepend
    drag`` → ``11dragfiles``) — a binary external the portable kit won't
    embed. Point ``default_dir`` at a User Library folder instead and the
    export lands in Live's browser, which drags anywhere.

    Wire your own path source into ``dir_in`` (e.g. an ``opendialog fold``)
    to retarget at runtime.
    """
    from .engines.design_system import js_sidecar_name
    from .ui import textbutton

    p = id_prefix
    acc = list(accent) if accent else [0.35, 0.78, 0.62, 1.0]
    fname = js_sidecar_name("sample_export.js", _SAMPLE_EXPORT_JS)
    device.register_asset(fname, _SAMPLE_EXPORT_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[1300, 3600, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    device.add_box(textbutton(
        f"{p}_save", list(rect), "⬇ SAVE", mode=0, fontsize=7.0,
        bgcolor=[0.16, 0.17, 0.20, 1.0], bgoncolor=acc,
        textcolor=[0.78, 0.79, 0.82, 1.0],
        patching_rect=[1300, 3540, 90, 20]))
    device.add_box({"box": {
        "id": f"{p}_savem", "maxclass": "message", "text": "save",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [1300, 3570, 60, 20]}})
    device.add_line(f"{p}_save", 0, f"{p}_savem", 0)
    device.add_line(f"{p}_savem", 0, js, 0)
    device.add_line(js, 0, buffer_box_id, 0)

    if stem != "export":
        device.add_box({"box": {
            "id": f"{p}_stem", "maxclass": "message",
            "text": f"setstem {stem}", "numinlets": 2, "numoutlets": 1,
            "outlettype": [""], "patching_rect": [1450, 3510, 110, 20]}})

    if default_dir is not None:
        device.add_box({"box": {
            "id": f"{p}_dir", "maxclass": "message",
            "text": f"setdir {default_dir}", "numinlets": 2,
            "numoutlets": 1, "outlettype": [""],
            "patching_rect": [1300, 3510, 140, 20]}})
        td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                               numoutlets=3, outlettype=["bang", "int", "int"],
                               patching_rect=[1300, 3480, 90, 20])
        device.add_line(td, 0, f"{p}_dir", 0)
        device.add_line(f"{p}_dir", 0, js, 0)
        if stem != "export":
            device.add_line(td, 0, f"{p}_stem", 0)
            device.add_line(f"{p}_stem", 0, js, 0)

    result_boxes = {"js": f"{p}_js", "save": f"{p}_save"}
    if status_rect is not None:
        device.add_box({"box": {
            "id": f"{p}_status", "maxclass": "textedit", "text": "—",
            "numinlets": 1, "numoutlets": 4,
            "outlettype": ["", "int", "", ""], "fontsize": 6.0,
            "fontname": "Ableton Sans Medium",
            "textcolor": [0.55, 0.56, 0.60, 1.0],
            "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0,
            "ignoreclick": 1, "presentation": 1,
            "presentation_rect": list(status_rect),
            "patching_rect": [1300, 3660, status_rect[2],
                              status_rect[3]]}})
        device.add_line(js, 1, f"{p}_status", 0)
        result_boxes["status"] = f"{p}_status"

    return stage_result(
        result_boxes,
        name="sample_export",
        params={},
        ports={"dir_in": device.box(js).inlet(0),
               "write_out": device.box(js).outlet(0),
               "status_out": device.box(js).outlet(1)},
    )


def sample_lfo(device, id_prefix, *, key, rate_rect, samps=None,
               rate_min=0.02, rate_max=20.0, rate_initial=1.0,
               unipolar=False, accent=None):
    """Use an audio buffer as the LFO *shape* (catalog #56, WaveLFO v2.1):
    ``phasor~`` at the Rate param sweeps ``wave~ <key>`` so whatever the
    buffer holds — a dropped sample, a rendered curve — IS the modulation
    waveform.

    Creates the ``buffer~ <key>`` when ``samps`` is given (pair the box id
    in the result with :func:`sample_drop_target` for drop-in); pass
    ``samps=None`` to reference a buffer another stage owns. ``sig_out``
    is the raw bipolar shape signal (audio samples are already ±1);
    ``unipolar=True`` remaps to 0..1 (``*~ 0.5`` → ``+~ 0.5``) for
    depth-style consumers. ``phase_out`` drives :func:`progress_tick`.
    """
    from .ui import dial

    p = id_prefix
    boxes = {}
    if samps is not None:
        device.add_newobj(f"{p}_buf", f"buffer~ {key} @samps {int(samps)}",
                          numinlets=1, numoutlets=2,
                          outlettype=["float", "bang"],
                          patching_rect=[1600, 3480, 170, 20])
        boxes["buffer"] = f"{p}_buf"
    device.add_box(dial(
        f"{p}_rate", "Rate", list(rate_rect), min_val=float(rate_min),
        max_val=float(rate_max), initial=float(rate_initial),
        unitstyle=3, parameter_exponent=3.0,
        activedialcolor=list(accent) if accent else None))
    device.add_newobj(f"{p}_phasor", "phasor~ 1.", numinlets=2,
                      numoutlets=1, outlettype=["signal"],
                      patching_rect=[1600, 3540, 80, 20])
    device.add_line(f"{p}_rate", 0, f"{p}_phasor", 0)
    device.add_newobj(f"{p}_wave", f"wave~ {key}", numinlets=3,
                      numoutlets=1, outlettype=["signal"],
                      patching_rect=[1600, 3570, 100, 20])
    device.add_line(f"{p}_phasor", 0, f"{p}_wave", 0)
    out_box = f"{p}_wave"
    if unipolar:
        device.add_newobj(f"{p}_half", "*~ 0.5", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[1600, 3600, 60, 20])
        device.add_newobj(f"{p}_lift", "+~ 0.5", numinlets=2, numoutlets=1,
                          outlettype=["signal"],
                          patching_rect=[1600, 3630, 60, 20])
        device.add_line(f"{p}_wave", 0, f"{p}_half", 0)
        device.add_line(f"{p}_half", 0, f"{p}_lift", 0)
        out_box = f"{p}_lift"
    boxes.update({"rate": f"{p}_rate", "wave": f"{p}_wave"})
    return stage_result(
        boxes,
        name="sample_lfo",
        params={"Rate": device.parameter(device.box(f"{p}_rate"))},
        ports={"sig_out": device.box(out_box).outlet(0),
               "phase_out": device.box(f"{p}_phasor").outlet(0)},
    )


_REGION_TRANSLATE_JS = """/* region_translate.js - slide every presentation box whose origin is
   at-or-beyond a start point (dnksaus moveUi.js, T16 #57). `setUiPos
   <startX> <startY> <newX> <newY>` translates the region by (new-start);
   the corpus idempotence guard (a box must sit EXACTLY at the start
   origin) prevents double-moves when toggles re-fire. Outlet 0 reports
   `moved <n>` / `skipped`. */
this.autowatch = 1;
this.outlets = 1;

function setUiPos(startX, startY, newX, newY) {
    var obj = this.patcher.firstobject;
    var closestX = 100000, closestY = 100000;
    while (obj != null) {
        if (obj.getboxattr("presentation") == 1) {
            var r = obj.getboxattr("presentation_rect");
            if (r[0] >= startX && r[1] >= startY) {
                closestX = Math.min(r[0] - startX, closestX);
                closestY = Math.min(r[1] - startY, closestY);
            }
        }
        obj = obj.nextobject;
    }
    if (closestX != 0 || closestY != 0) { outlet(0, ["skipped"]); return; }
    obj = this.patcher.firstobject;
    var n = 0;
    while (obj != null) {
        if (obj.getboxattr("presentation") == 1) {
            var r = obj.getboxattr("presentation_rect");
            if (r[0] >= startX && r[1] >= startY) {
                obj.setboxattr("presentation_rect",
                    [r[0] + newX - startX, r[1] + newY - startY,
                     r[2], r[3]]);
                n++;
            }
        }
        obj = obj.nextobject;
    }
    outlet(0, ["moved", n]);
}
"""


def region_translate(device, id_prefix):
    """The dnksaus ``moveUi.js`` region-translate primitive (catalog #57):
    a js whose ``setUiPos <startX> <startY> <newX> <newY>`` message slides
    EVERY presentation box at-or-beyond the start origin by the delta —
    reflowing panels without naming each box. The corpus guard (some box
    must sit exactly at the start origin) makes repeated sends idempotent,
    so author the sliding region with one box anchored AT the origin —
    the minimum x-offset AND y-offset across matching boxes must each be
    zero, so the anchor box must sit at the start point in BOTH axes.
    """
    from .engines.design_system import js_sidecar_name

    p = id_prefix
    fname = js_sidecar_name("region_translate.js", _REGION_TRANSLATE_JS)
    device.register_asset(fname, _REGION_TRANSLATE_JS, asset_type="TEXT",
                          category="js")
    js = device.add_newobj(
        f"{p}_js", f"js {fname}", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[900, 3900, 140, 20],
        saved_object_attributes={"filename": fname, "parameter_enable": 0})
    return stage_result(
        {"js": f"{p}_js"},
        name="region_translate",
        params={},
        ports={"move_in": device.box(js).inlet(0),
               "status_out": device.box(js).outlet(0)},
    )


def expandable_column(device, id_prefix, *, arrow_rect, base_width,
                      column_width, param_name="Panel",
                      accent="0.30, 0.80, 0.84"):
    """Right-side expandable column (catalog #57, the Spawner settings
    column). Author the device at FULL width (``base_width +
    column_width``) with the column content at ``x >= base_width``; this
    stage adds the ▸/◂ arrow (an expand/collapse glyph cycle bound to a
    hidden automatable enum ``param_name``) and the ``setwidth`` pair into
    ``live.thisdevice`` — Live clips the column when narrow (width does
    not reflow), which IS the reveal.

    A load re-fire bangs the hidden ``live.tab`` (bang-safe, unlike
    live.text toggles) so a fresh insert opens at ``base_width`` and a
    saved-Open device restores wide. Keep the arrow inside ``base_width``.
    """
    p = id_prefix
    full = int(base_width + column_width)
    device.add_cycle_button(f"{p}_arrow", param_name, list(arrow_rect),
                            glyphs=["expand", "collapse"],
                            option_labels=["Closed", "Open"],
                            accent=accent, initial=0)
    tab = f"{p}_arrow_tab"
    device.add_newobj(f"{p}_sel", "sel 0 1", numinlets=1, numoutlets=3,
                      outlettype=["bang", "bang", ""],
                      patching_rect=[900, 3960, 60, 20])
    device.add_box({"box": {
        "id": f"{p}_wbase", "maxclass": "message",
        "text": f"setwidth {int(base_width)}", "numinlets": 2,
        "numoutlets": 1, "outlettype": [""],
        "patching_rect": [900, 3990, 110, 20]}})
    device.add_box({"box": {
        "id": f"{p}_wfull", "maxclass": "message",
        "text": f"setwidth {full}", "numinlets": 2, "numoutlets": 1,
        "outlettype": [""], "patching_rect": [1020, 3990, 110, 20]}})
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 4020, 90, 20])
    device.add_line(tab, 0, f"{p}_sel", 0)
    device.add_line(f"{p}_sel", 0, f"{p}_wbase", 0)
    device.add_line(f"{p}_sel", 1, f"{p}_wfull", 0)
    device.add_line(f"{p}_wbase", 0, td, 0)
    device.add_line(f"{p}_wfull", 0, td, 0)
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[1140, 3960, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, tab, 0)
    return stage_result(
        {"arrow": f"{p}_arrow", "tab": tab},
        name="expandable_column",
        params={param_name: device.parameter(device.box(tab))},
        ports={"state_out": device.box(tab).outlet(0)},
    )


def header_strip(device, id_prefix, *, title, title_w, chips=(), y=3,
                 x=8, gap=6, height=11, text_color=None, dim_color=None,
                 fontsize=7.5, version=None, version_w=24):
    """Collapsed-face header discipline (catalog #58): the top strip
    carries the device's ESSENTIAL live state — title plus set-able
    readout chips — packed LEFT so it stays readable at MINI width
    (width-collapse clips the right edge; it does not reflow).

    ``chips``: list of ``(width, initial_text)``. Each becomes a
    transparent ``textedit`` fed by ready ``set …`` messages on the
    returned ``chip<i>_in`` ports (mapping summaries, mode names, gain
    readouts — the Trig Mod grammar).
    """
    p = id_prefix
    tc = list(text_color) if text_color else [0.78, 0.79, 0.82, 1.0]
    dc = list(dim_color) if dim_color else [0.55, 0.56, 0.60, 1.0]
    device.add_comment(f"{p}_title", [x, y, title_w, height], title,
                       textcolor=tc, fontsize=fontsize,
                       fontname="Ableton Sans Medium")
    ports = {}
    cx = x + title_w + gap
    if version is not None:
        # catalog #61: every corpus device titles itself "Name vN.N" — the
        # version lives on the face, dim, right after the title
        device.add_comment(f"{p}_ver", [cx - gap + 1, y, version_w, height],
                           f"v{version}", textcolor=dc,
                           fontsize=float(fontsize) - 1.5,
                           fontname="Ableton Sans Medium")
        cx += version_w
    for i, (cw, initial) in enumerate(chips):
        device.add_box({"box": {
            "id": f"{p}_chip{i}", "maxclass": "textedit",
            "text": str(initial), "numinlets": 1, "numoutlets": 4,
            "outlettype": ["", "int", "", ""], "fontsize": float(fontsize) - 1,
            "fontname": "Ableton Sans Medium", "textcolor": dc,
            "bgcolor": [0.0, 0.0, 0.0, 0.0], "border": 0, "rounded": 0,
            "ignoreclick": 1, "presentation": 1,
            "presentation_rect": [cx, y + 1, cw, height - 1],
            "patching_rect": [900 + i * 130, 4080, cw, height]}})
        ports[f"chip{i}_in"] = device.box(f"{p}_chip{i}").inlet(0)
        cx += cw + gap
    return stage_result(
        {"title": f"{p}_title"},
        name="header_strip",
        params={},
        ports=ports,
    )


def icon_rail(device, id_prefix, *, icons, rect, param_name="Page",
              labels=None, manage=None, accent="0.30, 0.80, 0.84"):
    """Left icon-rail page tabs (catalog #59, the dnksaus viewhide bus):
    a slim VERTICAL glyph radio (one icon per page, accent highlight on
    the selected cell) bound to a hidden automatable ``live.tab`` enum.

    ``manage``: dict of ``{parent_box_varname: 0-based_page_index}`` —
    every managed box is hidden whenever its page isn't selected, via the
    Live-proven parent-side ``script sendbox <vn> hidden $1`` →
    ``thispatcher`` path, with a load re-broadcast (bang the tab —
    bang-safe) so restored sets hide their off-page boxes.
    """
    from .engines.ui_kit import custom_glyph_selector_js
    from .parameters import ParameterSpec

    p = id_prefix
    labels = list(labels) if labels else [i.upper() for i in icons]
    spec = ParameterSpec.enumerated(param_name, labels, initial=0,
                                    initial_enable=True)
    device.add_tab(f"{p}_tab", param_name,
                   [rect[0], rect[1], 40, 18], options=labels,
                   parameter=spec, presentation=0,
                   patching_rect=[900, 4140, 40, 18])
    device.add_v8ui(
        f"{p}_rail", list(rect),
        js_code=custom_glyph_selector_js(glyphs=list(icons), accent=accent,
                                         vertical=True),
        js_filename=f"{p}_iconrail.js", content_address=True,
        numinlets=1, numoutlets=1, outlettype=["int"],
        background=0, ignoreclick=0, bgcolor=[0.0, 0.0, 0.0, 0.0],
        border=0, bordercolor=[0.0, 0.0, 0.0, 0.0], varname=f"{p}_rail")
    device.add_line(f"{p}_rail", 0, f"{p}_tab", 0)
    seti = device.add_newobj(f"{p}_seti", "prepend set_index", numinlets=1,
                             numoutlets=1, outlettype=[""],
                             patching_rect=[900, 4170, 110, 20])
    device.add_line(f"{p}_tab", 0, seti, 0)
    device.add_line(seti, 0, f"{p}_rail", 0)
    td = device.add_newobj(f"{p}_td", "live.thisdevice", numinlets=1,
                           numoutlets=3, outlettype=["bang", "int", "int"],
                           patching_rect=[900, 4110, 90, 20])
    tb = device.add_newobj(f"{p}_tb", "t b", numinlets=1, numoutlets=1,
                           outlettype=["bang"],
                           patching_rect=[1000, 4110, 30, 20])
    device.add_line(td, 0, tb, 0)
    device.add_line(tb, 0, f"{p}_tab", 0)
    if manage:
        thisp = device.add_newobj(f"{p}_this", "thispatcher", numinlets=1,
                                  numoutlets=2, outlettype=["", ""],
                                  patching_rect=[1240, 4140, 80, 20])
        for mi, (vn, page) in enumerate(sorted(manage.items())):
            if " " in vn:
                raise ValueError(
                    f"icon_rail: managed varname {vn!r} contains a space "
                    "— script sendbox silently no-ops")
            ex = device.add_newobj(
                f"{p}_mx{mi}", f"expr $i1 != {int(page)}", numinlets=1,
                numoutlets=1, outlettype=[""],
                patching_rect=[1060, 4140 + 30 * mi, 120, 20])
            device.add_box({"box": {
                "id": f"{p}_mm{mi}", "maxclass": "message",
                "text": f"script sendbox {vn} hidden $1",
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [1190, 4140 + 30 * mi, 200, 20]}})
            device.add_line(f"{p}_tab", 0, ex, 0)
            device.add_line(ex, 0, f"{p}_mm{mi}", 0)
            device.add_line(f"{p}_mm{mi}", 0, thisp, 0)
    return stage_result(
        {"rail": f"{p}_rail", "tab": f"{p}_tab"},
        name="icon_rail",
        params={param_name: device.parameter(device.box(f"{p}_tab"))},
        ports={"page_out": device.box(f"{p}_tab").outlet(0)},
    )


def stereo_mode(device, id_prefix, *, rect, gen_box, param_name="Mode",
                gen_param="msmode", fontsize=6.8):
    """STEREO / MID / SIDE processing-mode selector (catalog Q50, the
    linear-phase-crossover / Parametric-EQ pattern as one contract).

    The DSP side embeds the M/S matrix in its gen~ (inline the
    :func:`~m4l_builder.gen_snippets.ms_mode_split` /
    :func:`~m4l_builder.gen_snippets.ms_mode_merge` law with a single
    ``{gen_param}`` Param — STEREO must stay byte-identical); this recipe
    is the UI half: the automatable enum menu + ``prepend {gen_param}``
    into ``gen_box``.
    """
    from .parameters import ParameterSpec
    from .ui import menu as _menu

    p = id_prefix
    device.add_box(_menu(
        f"{p}_menu", param_name, list(rect),
        options=["STEREO", "MID", "SIDE"], fontsize=fontsize,
        annotation_name="Processing mode (Stereo / Mid only / Side only)",
        parameter=ParameterSpec(name=param_name, shortname=param_name,
                                parameter_type=2,
                                enum=["STEREO", "MID", "SIDE"],
                                initial=[0], initial_enable=True)))
    pp = device.add_newobj(f"{p}_pp", f"prepend {gen_param}", numinlets=1,
                           numoutlets=1, outlettype=[""],
                           patching_rect=[900, 4400, 110, 20])
    device.add_line(f"{p}_menu", 0, pp, 0)
    device.add_line(pp, 0, gen_box, 0)
    return stage_result(
        {"menu": f"{p}_menu"},
        name="stereo_mode",
        params={param_name: device.parameter(device.box(f"{p}_menu"))},
        ports={"mode_out": device.box(f"{p}_menu").outlet(0)},
    )


def buffer_viewport(device, id_prefix, buffer_name, *, rect,
                    accent=None, bg=None, setmode=1, outmode=4,
                    zoom_rect=None, full_rect=None, fontsize=6.8):
    """Zoom/scrub/select ``buffer~`` viewport (catalog Q2, the
    BufferViewport framework piece — pairs with T11's waveform layers).

    The native ``waveform~`` carries the working set (doc-verified inlet/
    outlet order — outlets 0/1 are the DISPLAY window, 2/3 the SELECTION):

    - **select** — drag on the wave (``setmode`` 1, the I-beam; 3 = Move
      scrub/zoom gesture, 2 = Loop, 4 = Draw); the bounds stream out the
      ``sel_start`` / ``sel_end`` ports in ms (``outmode`` is the INT
      enum 0 none / 1 down / 2 up / 3 downup / 4 continuous — 4 streams
      live during the drag).
    - **zoom** — the ``{p}_zoom`` chip reads the LAST selection out of two
      silent ``float`` stores and drives the display start/length inlets
      (0/1); ``{p}_full`` resets to the whole buffer.

    The display window is view state, not a Live parameter — zooming never
    dirties the set. Feed ``sel_start``/``sel_end`` to a chip or a player.
    """
    from .ui import textbutton as _textbutton
    from .ui import waveform as _waveform

    p = id_prefix
    acc = list(accent) if accent else [0.55, 0.85, 0.95, 1.0]
    sel = [acc[0], acc[1], acc[2], 0.30]
    bgc = list(bg) if bg else [0.05, 0.055, 0.062, 1.0]
    device.add_box(_waveform(
        f"{p}_wave", list(rect), buffername=buffer_name,
        waveformcolor=acc, selectioncolor=sel, bgcolor=bgc,
        gridcolor=[0.16, 0.17, 0.19, 1.0],
        bordercolor=[0.16, 0.17, 0.19, 1.0],
        setmode=setmode, outmode=outmode))
    # silent selection stores (right inlet = set, no output); selection
    # bounds emit from outlets 2/3 (0/1 are the display window)
    device.add_newobj(f"{p}_fs", "f", numinlets=2, numoutlets=1,
                      outlettype=["float"],
                      patching_rect=[900, 4470, 40, 20])
    device.add_newobj(f"{p}_fe", "f", numinlets=2, numoutlets=1,
                      outlettype=["float"],
                      patching_rect=[950, 4470, 40, 20])
    device.add_line(f"{p}_wave", 2, f"{p}_fs", 1)
    device.add_line(f"{p}_wave", 3, f"{p}_fe", 1)
    # ZOOM: right bang first -> start (display start + expr cold), then
    # end -> expr hot -> length
    zr = list(zoom_rect) if zoom_rect else [rect[0], rect[1] + rect[3] + 3,
                                            40, 12]
    fr = list(full_rect) if full_rect else [zr[0] + zr[2] + 4, zr[1],
                                            40, 12]
    device.add_box(_textbutton(f"{p}_zoom", zr, "ZOOM",
                               fontsize=fontsize, mode=0))
    device.add_box(_textbutton(f"{p}_full", fr, "FULL",
                               fontsize=fontsize, mode=0))
    device.add_newobj(f"{p}_zt", "t b b", numinlets=1, numoutlets=2,
                      outlettype=["bang", "bang"],
                      patching_rect=[900, 4500, 50, 20])
    device.add_newobj(f"{p}_len", "expr $f1 - $f2", numinlets=2,
                      numoutlets=1, outlettype=[""],
                      patching_rect=[900, 4530, 90, 20])
    device.add_line(f"{p}_zoom", 0, f"{p}_zt", 0)
    device.add_line(f"{p}_zt", 1, f"{p}_fs", 0)
    device.add_line(f"{p}_zt", 0, f"{p}_fe", 0)
    device.add_line(f"{p}_fs", 0, f"{p}_len", 1)
    device.add_line(f"{p}_fs", 0, f"{p}_wave", 0)
    device.add_line(f"{p}_fe", 0, f"{p}_len", 0)
    device.add_line(f"{p}_len", 0, f"{p}_wave", 1)
    # FULL: display start 0, display length = clamped-to-buffer huge
    device.add_newobj(f"{p}_ft", "t b b", numinlets=1, numoutlets=2,
                      outlettype=["bang", "bang"],
                      patching_rect=[1000, 4500, 50, 20])
    device.add_box({"box": {
        "id": f"{p}_m0", "maxclass": "message", "text": "0.",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [1000, 4530, 30, 20]}})
    device.add_box({"box": {
        "id": f"{p}_mbig", "maxclass": "message", "text": "1000000000.",
        "numinlets": 2, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [1040, 4530, 80, 20]}})
    device.add_line(f"{p}_full", 0, f"{p}_ft", 0)
    device.add_line(f"{p}_ft", 1, f"{p}_mbig", 0)
    device.add_line(f"{p}_ft", 0, f"{p}_m0", 0)
    device.add_line(f"{p}_mbig", 0, f"{p}_wave", 1)
    device.add_line(f"{p}_m0", 0, f"{p}_wave", 0)
    return stage_result(
        {"waveform": f"{p}_wave", "zoom": f"{p}_zoom", "full": f"{p}_full"},
        name="buffer_viewport",
        params={},
        ports={
            "sel_start": device.box(f"{p}_wave").outlet(2),
            "sel_end": device.box(f"{p}_wave").outlet(3),
            "disp_start_in": device.box(f"{p}_wave").inlet(0),
            "disp_len_in": device.box(f"{p}_wave").inlet(1),
        },
    )
