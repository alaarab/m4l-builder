"""Pre-wired DSP combo recipes for common M4L patterns.

Each recipe takes a device instance and parameters, then adds a complete
pre-wired section using device.add_dsp(), device.add_newobj(), device.add_dial(),
and device.add_line(). Returns a dict of important IDs for further wiring.
"""

from .dsp import (notein as dsp_notein, delay_line, param_smooth,
                   convolver, dry_wet_mix, sidechain_routing, compressor,
                   lfo, spectral_gate, spectral_gate_subpatcher,
                   arpeggiator, pitch_quantize, grain_cloud, buffer_load,
                   poly_voices, velocity_curve, transport_lfo,
                   midi_learn_chain, macromap)
from .engines.sidechain_display import sidechain_display_js, SIDECHAIN_DISPLAY_INLETS
from .engines.spectral_display import spectral_display_js, SPECTRAL_DISPLAY_INLETS
from .stages import stage_result


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

    scale_id = device.add_newobj(
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

    display_id = device.add_jsui(
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
