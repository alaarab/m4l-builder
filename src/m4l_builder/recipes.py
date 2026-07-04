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

    transport_id = device.add_newobj(
        f"{p}_transport", "transport", numinlets=1, numoutlets=7,
        outlettype=["int", "", "float", "float", "float", "", "int"],
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
        outlettype=["", ""], patching_rect=[x, y + 30, 60, 20],
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
        outlettype=["", "", ""], patching_rect=[x + 160, y + 30, 60, 20])
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
                       settle_ms=600, x=600, y=520,
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

    drop_id = device.add_box(live_drop(
        f"{p}_drop", drop_rect,
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
        f"{p}_thisp", "thispatcher", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[x, y + 130, 80, 20],
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
                             reveal=False):
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
        ic_code = shape_icon_js(shapes=list(source_glyphs), accent=acc)
        ic_fname = js_sidecar_name("shape_icon.js", ic_code)
        device.register_asset(ic_fname, ic_code, asset_type="TEXT",
                              category="js")
        sub.add_box({"box": {
            "id": "slot_shape_ui", "maxclass": "jsui",
            "jsui_maxclass": "jsui", "filename": ic_fname,
            "numinlets": 1, "numoutlets": 1, "outlettype": [""],
            "parameter_enable": 0, "presentation": 1,
            "presentation_rect": [1, 1, 15, 15],
            "patching_rect": [1, 200, 15, 15]}})
        MAP_X, PNAME_X, DEP_X, MIN_X, MAX_X, BI_X = 18, 46, 114, 148, 178, 208
    else:
        MAP_X, PNAME_X, DEP_X, MIN_X, MAX_X, BI_X = 0, 31, 96, 135, 174, 213
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
    # (consumers scale by 0.01 — poly_lfo_engine does it inside gen)
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
    # ---- cross-slot exclusivity: announce goes UP the outlet; the parent
    # fans it back into every slot's inlet 0 (js ignores its own index)
    sub.add_newobj("slot_prep_ann", "prepend announce", numinlets=1,
                   numoutlets=1, outlettype=[""],
                   patching_rect=[30, 460, 120, 20])
    sub.add_line("slot_route", 7, "slot_prep_ann", 0)
    sub.add_line("slot_prep_ann", 0, "slot_out", 0)

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
        sub.add_newobj("slot_this", "thispatcher", numinlets=1, numoutlets=1,
                       outlettype=[""], patching_rect=[4, 650, 80, 20])
        sub.add_line("slot_in", 0, "slot_lanes_route", 0)
        sub.add_line("slot_lanes_route", 0, "slot_lanes_cmp", 0)
        sub.add_line("slot_lanes_cmp", 0, "slot_hide_msg", 0)
        sub.add_line("slot_hide_msg", 0, "slot_this", 0)

    ids = {"js": "slot_js", "map": "slot_map", "readout": "slot_pname",
           "sink_reg": "slot_sink_reg", "remote": "slot_sink_remote",
           "modulate": "slot_sink_mod", "rect": [0, 0, width, height]}
    if source_enum:
        ids["source"] = "slot_source"
    return (sub, ids)
